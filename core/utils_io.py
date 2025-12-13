"""
Input/Output utilities for handling shapefile operations.
"""

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, List, Tuple
from contextlib import contextmanager
import geopandas as gpd
import streamlit as st


REQUIRED_SHAPEFILE_EXTENSIONS = {'.shp', '.shx', '.dbf'}
OPTIONAL_SHAPEFILE_EXTENSIONS = {'.prj', '.cpg', '.sbn', '.sbx', '.shp.xml'}


def validate_shapefile_components(file_list: List[str]) -> Tuple[bool, str]:
    """
    Validate that a list of files contains the required shapefile components.
    
    Args:
        file_list: List of filenames
        
    Returns:
        Tuple of (is_valid, message)
    """
    extensions = {Path(f).suffix.lower() for f in file_list}
    
    missing = REQUIRED_SHAPEFILE_EXTENSIONS - extensions
    
    if missing:
        return False, f"Missing required files: {', '.join(missing)}"
    
    return True, "Valid shapefile components"


def extract_shapefile_from_zip(zip_file, extract_dir: str) -> Tuple[Optional[str], str]:
    """
    Extract a shapefile from an uploaded ZIP file.
    
    Args:
        zip_file: Uploaded file object from Streamlit
        extract_dir: Directory to extract files to
        
    Returns:
        Tuple of (path_to_shp_file, message)
    """
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            
            # Filter out macOS metadata files and directories
            file_list = [f for f in file_list if not f.startswith('__MACOSX') and not f.endswith('/')]
            
            # Validate components
            is_valid, message = validate_shapefile_components(file_list)
            if not is_valid:
                return None, message
            
            # Extract all files
            zip_ref.extractall(extract_dir)
            
            # Find the .shp file
            shp_files = [f for f in file_list if f.lower().endswith('.shp')]
            
            if not shp_files:
                return None, "No .shp file found in ZIP"
            
            if len(shp_files) > 1:
                return None, f"Multiple .shp files found. Please upload a ZIP with only one shapefile."
            
            shp_path = os.path.join(extract_dir, shp_files[0])
            return shp_path, "Shapefile extracted successfully"
            
    except zipfile.BadZipFile:
        return None, "Invalid ZIP file"
    except Exception as e:
        return None, f"Error extracting ZIP: {str(e)}"


def create_shapefile_zip(gdf: gpd.GeoDataFrame, base_name: str, output_dir: str) -> str:
    """
    Save a GeoDataFrame as a shapefile and package it into a ZIP file.
    
    Args:
        gdf: GeoDataFrame to save
        base_name: Base name for the shapefile (without extension)
        output_dir: Directory to save the ZIP file
        
    Returns:
        Path to the created ZIP file
    """
    # Create a temporary directory for the shapefile components
    temp_shp_dir = os.path.join(output_dir, "temp_shp")
    os.makedirs(temp_shp_dir, exist_ok=True)
    
    # Save the shapefile
    shp_path = os.path.join(temp_shp_dir, f"{base_name}.shp")
    gdf.to_file(shp_path)
    
    # Create ZIP file
    zip_path = os.path.join(output_dir, f"{base_name}.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all shapefile components
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            file_path = os.path.join(temp_shp_dir, f"{base_name}{ext}")
            if os.path.exists(file_path):
                zipf.write(file_path, f"{base_name}{ext}")
    
    return zip_path


@contextmanager
def create_temp_directory():
    """
    Context manager for creating and cleaning up a temporary directory.
    
    Yields:
        Path to the temporary directory
    """
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        # Clean up
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass  # Best effort cleanup


def get_gdf_from_upload(uploaded_file, temp_dir: str) -> Tuple[Optional[gpd.GeoDataFrame], str]:
    """
    Convert an uploaded ZIP file to a GeoDataFrame.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        temp_dir: Temporary directory for extraction
        
    Returns:
        Tuple of (GeoDataFrame or None, message)
    """
    # Extract the shapefile
    shp_path, message = extract_shapefile_from_zip(uploaded_file, temp_dir)
    
    if shp_path is None:
        return None, message
    
    try:
        # Read the shapefile
        gdf = gpd.read_file(shp_path)
        return gdf, f"Successfully loaded {len(gdf)} features"
    except Exception as e:
        return None, f"Error reading shapefile: {str(e)}"


def save_gdf_as_csv(gdf: gpd.GeoDataFrame, output_path: str, 
                    separator: str = ',', columns: Optional[List[str]] = None,
                    include_geometry: bool = False) -> None:
    """
    Save a GeoDataFrame as a CSV file.
    
    Args:
        gdf: GeoDataFrame to save
        output_path: Path to save the CSV file
        separator: CSV separator character
        columns: List of columns to include (None = all attribute columns)
        include_geometry: Whether to include geometry as WKT
    """
    df = gdf.copy()
    
    # Select columns
    if columns is not None:
        # Keep only selected columns plus geometry if needed
        if include_geometry and 'geometry' in df.columns:
            df = df[columns + ['geometry']]
        else:
            df = df[columns]
    
    # Convert geometry to WKT if needed
    if include_geometry and 'geometry' in df.columns:
        df['geometry'] = df['geometry'].apply(lambda geom: geom.wkt if geom else None)
    else:
        # Drop geometry column
        if 'geometry' in df.columns:
            df = df.drop(columns=['geometry'])
    
    # Save to CSV
    df.to_csv(output_path, sep=separator, index=False)
