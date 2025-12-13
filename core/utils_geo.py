"""
GIS-specific utilities for CRS handling, reprojection, and schema management.
"""

from typing import Dict, List, Optional, Tuple, Set
import geopandas as gpd
import pandas as pd
from pyproj import CRS


# Common EPSG codes with descriptions
COMMON_EPSG_CODES = {
    4326: "WGS 84 (GPS coordinates)",
    3857: "Web Mercator (Google Maps, OpenStreetMap)",
    32643: "WGS 84 / UTM zone 43N (India)",
    32644: "WGS 84 / UTM zone 44N (India)",
    32645: "WGS 84 / UTM zone 45N (India)",
    32646: "WGS 84 / UTM zone 46N (India)",
    2163: "US National Atlas Equal Area",
    3395: "World Mercator",
    4269: "NAD83 (North America)",
    27700: "British National Grid",
    2154: "RGF93 / Lambert-93 (France)",
    25832: "ETRS89 / UTM zone 32N (Europe)",
    3035: "ETRS89 / LAEA Europe",
}


def get_crs_info(gdf: gpd.GeoDataFrame) -> Dict[str, str]:
    """
    Extract CRS information from a GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame to extract CRS from
        
    Returns:
        Dictionary with CRS information (epsg, name, proj4)
    """
    if gdf.crs is None:
        return {
            "epsg": "Unknown",
            "name": "No CRS defined",
            "proj4": "N/A",
            "wkt": "N/A"
        }
    
    crs = gdf.crs
    
    # Try to get EPSG code
    epsg = "Unknown"
    try:
        if crs.to_epsg():
            epsg = f"EPSG:{crs.to_epsg()}"
    except Exception:
        pass
    
    # Get CRS name
    name = crs.name if hasattr(crs, 'name') else "Unknown"
    
    # Get proj4 string
    proj4 = "N/A"
    try:
        proj4 = crs.to_proj4()
    except Exception:
        pass
    
    # Get WKT (truncated)
    wkt = "N/A"
    try:
        wkt_full = crs.to_wkt()
        wkt = wkt_full[:200] + "..." if len(wkt_full) > 200 else wkt_full
    except Exception:
        pass
    
    return {
        "epsg": epsg,
        "name": name,
        "proj4": proj4,
        "wkt": wkt
    }


def reproject_gdf(gdf: gpd.GeoDataFrame, target_epsg: int) -> Tuple[Optional[gpd.GeoDataFrame], str]:
    """
    Reproject a GeoDataFrame to a target CRS.
    
    Args:
        gdf: GeoDataFrame to reproject
        target_epsg: Target EPSG code
        
    Returns:
        Tuple of (reprojected GeoDataFrame or None, message)
    """
    try:
        # Check if already in target CRS
        if gdf.crs and gdf.crs.to_epsg() == target_epsg:
            return gdf, f"Already in EPSG:{target_epsg}"
        
        # Reproject
        gdf_reprojected = gdf.to_crs(epsg=target_epsg)
        return gdf_reprojected, f"Successfully reprojected to EPSG:{target_epsg}"
        
    except Exception as e:
        return None, f"Error reprojecting: {str(e)}"


def validate_schema_compatibility(gdfs: List[gpd.GeoDataFrame]) -> Tuple[bool, str, Dict]:
    """
    Check if multiple GeoDataFrames have compatible schemas.
    
    Args:
        gdfs: List of GeoDataFrames to check
        
    Returns:
        Tuple of (are_compatible, message, schema_info)
    """
    if len(gdfs) < 2:
        return True, "Only one GeoDataFrame provided", {}
    
    # Get column sets (excluding geometry)
    column_sets = []
    for i, gdf in enumerate(gdfs):
        cols = set(gdf.columns) - {'geometry'}
        column_sets.append(cols)
    
    # Check if all have the same columns
    first_cols = column_sets[0]
    all_same = all(cols == first_cols for cols in column_sets)
    
    if all_same:
        return True, "All shapefiles have identical schemas", {}
    
    # Find differences
    all_columns = set()
    for cols in column_sets:
        all_columns.update(cols)
    
    differences = {}
    for i, cols in enumerate(column_sets):
        missing = all_columns - cols
        if missing:
            differences[f"Shapefile {i+1}"] = list(missing)
    
    message = "Schemas differ. Missing columns: " + "; ".join(
        f"{name}: {', '.join(cols)}" for name, cols in differences.items()
    )
    
    return False, message, differences


def align_schemas(gdfs: List[gpd.GeoDataFrame]) -> List[gpd.GeoDataFrame]:
    """
    Align schemas of multiple GeoDataFrames by adding missing columns with null values.
    
    Args:
        gdfs: List of GeoDataFrames to align
        
    Returns:
        List of GeoDataFrames with aligned schemas
    """
    if len(gdfs) < 2:
        return gdfs
    
    # Get all unique columns (excluding geometry)
    all_columns = set()
    for gdf in gdfs:
        all_columns.update(set(gdf.columns) - {'geometry'})
    
    all_columns = sorted(list(all_columns))
    
    # Align each GeoDataFrame
    aligned_gdfs = []
    for gdf in gdfs:
        gdf_copy = gdf.copy()
        
        # Add missing columns with None values
        for col in all_columns:
            if col not in gdf_copy.columns:
                gdf_copy[col] = None
        
        # Reorder columns to match (geometry should stay last)
        column_order = all_columns + ['geometry']
        gdf_copy = gdf_copy[column_order]
        
        aligned_gdfs.append(gdf_copy)
    
    return aligned_gdfs


def validate_crs_compatibility(gdfs: List[gpd.GeoDataFrame]) -> Tuple[bool, str, List[str]]:
    """
    Check if multiple GeoDataFrames have compatible CRS.
    
    Args:
        gdfs: List of GeoDataFrames to check
        
    Returns:
        Tuple of (are_compatible, message, list of CRS descriptions)
    """
    if len(gdfs) < 2:
        return True, "Only one GeoDataFrame provided", []
    
    crs_list = []
    for i, gdf in enumerate(gdfs):
        crs_info = get_crs_info(gdf)
        crs_list.append(f"Shapefile {i+1}: {crs_info['epsg']} - {crs_info['name']}")
    
    # Check if all have the same CRS
    first_crs = gdfs[0].crs
    all_same = all(gdf.crs == first_crs for gdf in gdfs)
    
    if all_same:
        return True, "All shapefiles have the same CRS", crs_list
    
    return False, "Shapefiles have different CRS", crs_list


def reproject_to_common_crs(gdfs: List[gpd.GeoDataFrame], target_epsg: Optional[int] = None) -> List[gpd.GeoDataFrame]:
    """
    Reproject all GeoDataFrames to a common CRS.
    
    Args:
        gdfs: List of GeoDataFrames to reproject
        target_epsg: Target EPSG code (if None, uses the CRS of the first GeoDataFrame)
        
    Returns:
        List of reprojected GeoDataFrames
    """
    if len(gdfs) < 2:
        return gdfs
    
    # Determine target CRS
    if target_epsg is None:
        target_crs = gdfs[0].crs
    else:
        target_crs = CRS.from_epsg(target_epsg)
    
    # Reproject all GeoDataFrames
    reprojected_gdfs = []
    for gdf in gdfs:
        if gdf.crs != target_crs:
            gdf_reprojected = gdf.to_crs(target_crs)
            reprojected_gdfs.append(gdf_reprojected)
        else:
            reprojected_gdfs.append(gdf)
    
    return reprojected_gdfs
