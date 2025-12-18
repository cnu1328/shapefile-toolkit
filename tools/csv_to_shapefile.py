"""
Tool for converting CSV files to Shapefile format.
"""

import os
import sys
import csv
import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely import wkt, wkb
from shapely.geometry import Point, LineString, Polygon
from typing import Optional, Tuple
from core.base_tool import BaseTool
from core.utils_io import create_temp_directory, create_shapefile_zip
from core.utils_geo import COMMON_EPSG_CODES

# Increase CSV field size limit to maximum to handle large cells (e.g., long WKT geometries)
# This prevents "field larger than field limit" errors
csv.field_size_limit(sys.maxsize)


class CSVToShapefileTool(BaseTool):
    """
    Tool for converting CSV files to Shapefile format.
    
    Features:
    - Upload CSV file
    - Detect geometry columns (WKT, lat/lon, coordinates)
    - Support Point, LineString, Polygon geometries
    - Select CRS
    - Handle various geometry formats
    """
    
    @property
    def name(self) -> str:
        return "CSV to Shapefile"
    
    @property
    def description(self) -> str:
        return "Convert CSV files with geometry data to Shapefile format. Supports WKT, lat/lon coordinates, and various geometry types."
    
    @property
    def icon(self) -> str:
        return "🗺️"
    
    def detect_geometry_columns(self, df: pd.DataFrame) -> dict:
        """
        Detect potential geometry columns in the dataframe.
        
        Returns:
            Dictionary with detected column types
        """
        results = {
            'wkt_candidates': [],
            'wkb_candidates': [],
            'lat_candidates': [],
            'lon_candidates': [],
            'x_candidates': [],
            'y_candidates': [],
            'geometry_candidates': []
        }
        
        for col in df.columns:
            col_lower = col.lower()
            
            if any(keyword in col_lower for keyword in ['wkt', 'geometry', 'geom', 'shape']):
                results['wkt_candidates'].append(col)
            
            # Check for WKB columns
            if any(keyword in col_lower for keyword in ['wkb', 'bin_geom', 'binary']):
                results['wkb_candidates'].append(col)
            
            # Check for latitude columns
            if any(keyword in col_lower for keyword in ['lat', 'latitude', 'y']):
                results['lat_candidates'].append(col)
            
            # Check for longitude columns
            if any(keyword in col_lower for keyword in ['lon', 'long', 'longitude', 'x']):
                results['lon_candidates'].append(col)
            
            # Check for X coordinate columns
            if col_lower in ['x', 'x_coord', 'xcoord', 'easting']:
                results['x_candidates'].append(col)
            
            # Check for Y coordinate columns
            if col_lower in ['y', 'y_coord', 'ycoord', 'northing']:
                results['y_candidates'].append(col)
        
        return results
    
    def parse_wkt_geometry(self, wkt_string: str) -> Optional[object]:
        """
        Parse WKT string to shapely geometry.
        
        Args:
            wkt_string: WKT string
            
        Returns:
            Shapely geometry object or None
        """
        try:
            return wkt.loads(str(wkt_string))
        except Exception:
            return None

    def parse_wkb_geometry(self, wkb_val: str) -> Optional[object]:
        """
        Parse WKB / EWKB hex string to shapely geometry.
        
        Args:
            wkb_val: Hex string representation of WKB
            
        Returns:
            Shapely geometry object or None
        """
        try:
            if not isinstance(wkb_val, str) or not wkb_val.strip():
                return None
                
            clean_wkb = wkb_val.strip()
            # Remove any '0x' prefix if present from some DB exports
            if clean_wkb.lower().startswith('0x'):
                clean_wkb = clean_wkb[2:]
            
            # WKB hex strings are common. 
            # Some formats like PostGIS EWKB are also hex strings.
            # shapely.wkb.loads handles both if they are valid WKB hex.
            return wkb.loads(bytes.fromhex(clean_wkb))
        except Exception:
            return None
    
    def create_point_from_coords(self, lon: float, lat: float) -> Optional[Point]:
        """
        Create Point geometry from coordinates.
        
        Args:
            lon: Longitude or X coordinate
            lat: Latitude or Y coordinate
            
        Returns:
            Point geometry or None
        """
        try:
            lon_val = float(lon)
            lat_val = float(lat)
            return Point(lon_val, lat_val)
        except (ValueError, TypeError):
            return None
    
    def auto_detect_geometry(self, df: pd.DataFrame) -> dict:
        """
        Intelligently detect geometry by analyzing actual column content.
        
        Returns:
            Dictionary with detection results:
            {
                'method': 'wkt' | 'wkb' | 'latlon' | 'xy' | 'none',
                'wkt_column': column name or None,
                'wkb_column': column name or None,
                'lat_column': column name or None,
                'lon_column': column name or None,
                'confidence': 'high' | 'medium' | 'low',
                'message': description
            }
        """
        result = {
            'method': 'none',
            'wkt_column': None,
            'wkb_column': None,
            'lat_column': None,
            'lon_column': None,
            'x_column': None,
            'y_column': None,
            'confidence': 'low',
            'message': 'No geometry detected'
        }
        
        # First, detect potential columns by name
        detected = self.detect_geometry_columns(df)
        
        # Strategy 1: Check for WKT columns by validating content
        for col in df.columns:
            # Sample first few non-null values
            sample = df[col].dropna().head(10)
            if len(sample) == 0:
                continue
            
            # Try to parse as WKT
            wkt_success = 0
            for val in sample:
                val_str = str(val).strip()
                # Check if it looks like WKT
                if any(geom_type in val_str.upper() for geom_type in 
                       ['POINT', 'LINESTRING', 'POLYGON', 'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON']):
                    if self.parse_wkt_geometry(val_str) is not None:
                        wkt_success += 1
            
            # If most samples parse successfully as WKT
            if wkt_success >= len(sample) * 0.7:  # 70% success rate
                result['method'] = 'wkt'
                result['wkt_column'] = col
                result['confidence'] = 'high' if wkt_success == len(sample) else 'medium'
                result['message'] = f"Detected WKT geometry in column '{col}'"
                return result
        
        # Strategy 2: Check for WKB columns by validating content
        for col in df.columns:
            # Sample first few non-null values
            sample = df[col].dropna().head(10)
            if len(sample) == 0:
                continue
            
            # Try to parse as WKB
            wkb_success = 0
            for val in sample:
                if self.parse_wkb_geometry(val) is not None:
                    wkb_success += 1
            
            # If most samples parse successfully as WKB
            if wkb_success >= len(sample) * 0.7:  # 70% success rate
                result['method'] = 'wkb'
                result['wkb_column'] = col
                result['confidence'] = 'high' if wkb_success == len(sample) else 'medium'
                result['message'] = f"Detected WKB/EWKB geometry in column '{col}'"
                return result
        
        # Strategy 3: Check for lat/lon pairs by validating numeric ranges
        if detected['lat_candidates'] and detected['lon_candidates']:
            for lat_col in detected['lat_candidates']:
                for lon_col in detected['lon_candidates']:
                    if lat_col == lon_col:
                        continue
                    
                    # Sample values
                    sample_lat = df[lat_col].dropna().head(10)
                    sample_lon = df[lon_col].dropna().head(10)
                    
                    if len(sample_lat) == 0 or len(sample_lon) == 0:
                        continue
                    
                    # Check if values are numeric and in valid lat/lon ranges
                    try:
                        lat_vals = pd.to_numeric(sample_lat, errors='coerce')
                        lon_vals = pd.to_numeric(sample_lon, errors='coerce')
                        
                        # Check if values are in valid ranges
                        lat_valid = ((lat_vals >= -90) & (lat_vals <= 90)).sum()
                        lon_valid = ((lon_vals >= -180) & (lon_vals <= 180)).sum()
                        
                        if lat_valid >= len(lat_vals) * 0.8 and lon_valid >= len(lon_vals) * 0.8:
                            result['method'] = 'latlon'
                            result['lat_column'] = lat_col
                            result['lon_column'] = lon_col
                            result['confidence'] = 'high'
                            result['message'] = f"Detected lat/lon in columns '{lat_col}' and '{lon_col}'"
                            return result
                    except:
                        continue
        
        # Strategy 3: Check for X/Y coordinates (any numeric columns)
        if detected['x_candidates'] and detected['y_candidates']:
            for x_col in detected['x_candidates']:
                for y_col in detected['y_candidates']:
                    if x_col == y_col:
                        continue
                    
                    # Sample values
                    sample_x = df[x_col].dropna().head(10)
                    sample_y = df[y_col].dropna().head(10)
                    
                    if len(sample_x) == 0 or len(sample_y) == 0:
                        continue
                    
                    # Check if values are numeric
                    try:
                        x_vals = pd.to_numeric(sample_x, errors='coerce')
                        y_vals = pd.to_numeric(sample_y, errors='coerce')
                        
                        if x_vals.notna().sum() >= len(x_vals) * 0.8 and y_vals.notna().sum() >= len(y_vals) * 0.8:
                            result['method'] = 'xy'
                            result['x_column'] = x_col
                            result['y_column'] = y_col
                            result['confidence'] = 'medium'
                            result['message'] = f"Detected X/Y coordinates in columns '{x_col}' and '{y_col}'"
                            return result
                    except:
                        continue
        
        return result
    
    def render_ui(self) -> None:
        """Render the Streamlit UI for this tool."""
        st.header(f"{self.icon} {self.name}")
        st.markdown(self.description)
        st.divider()
        
        # Initialize session state
        if 'csv_shp_tool_df' not in st.session_state:
            st.session_state.csv_shp_tool_df = None
            st.session_state.csv_shp_tool_filename = None
            st.session_state.csv_shp_tool_columns = []
        
        # File upload section
        st.subheader("📁 Step 1: Upload CSV File")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Upload a CSV file with geometry data",
                type=['csv', 'txt'],
                help="CSV file should contain geometry information (WKT, lat/lon, or coordinates)",
                key="csv_shp_upload"
            )
        
        with col2:
            separator_options = {
                "Comma (,)": ",",
                "Semicolon (;)": ";",
                "Pipe (|)": "|",
                "Tab": "\t",
                "Custom": "custom"
            }
            
            separator_choice = st.selectbox(
                "CSV Separator",
                options=list(separator_options.keys()),
                index=0,
                key="csv_shp_separator_choice"
            )
            
            if separator_choice == "Custom":
                custom_separator = st.text_input(
                    "Enter custom separator",
                    value=",",
                    max_chars=5,
                    help="Enter 1-5 characters for custom separator",
                    key="csv_shp_custom_separator"
                )
                separator = custom_separator
            else:
                separator = separator_options[separator_choice]
        
        if uploaded_file is not None:
            # Check if this is a new file or separator changed
            current_separator_key = f"{uploaded_file.name}_{separator}"
            if 'csv_shp_tool_separator_key' not in st.session_state:
                st.session_state.csv_shp_tool_separator_key = None
            
            if st.session_state.csv_shp_tool_separator_key != current_separator_key:
                with st.spinner("Loading CSV file..."):
                    try:
                        # Read CSV with increased field size limit and error handling
                        # engine='python' is more flexible for large/complex CSV files
                        # quotechar='"' handles multi-line cells within quotes
                        df = pd.read_csv(
                            uploaded_file, 
                            sep=separator,
                            engine='python',  # More flexible parser
                            on_bad_lines='warn',  # Warn but continue on bad lines
                            encoding='utf-8',  # Try UTF-8 first
                            quotechar='"',  # Handle quoted fields (important for multi-line cells)
                            doublequote=True,  # Handle escaped quotes ("" becomes ")
                            skipinitialspace=True  # Skip spaces after delimiter
                        )
                        
                        if df.empty:
                            st.error("❌ CSV file is empty.")
                            return
                        
                        # Check for single column issue (likely wrong separator)
                        if len(df.columns) == 1 and df.shape[0] > 0:
                            col_name = df.columns[0]
                            # Check if common separators exist in the column name or first row
                            potential_seps = {'#': 'Custom', ';': 'Semicolon (;)', '|': 'Pipe (|)', '\t': 'Tab'}
                            
                            found_sep = None
                            for sep_char, sep_name in potential_seps.items():
                                if sep_char in col_name or sep_char in str(df.iloc[0, 0]):
                                    found_sep = (sep_char, sep_name)
                                    break
                            
                            if found_sep:
                                st.warning(f"⚠️ It looks like the file uses '{found_sep[0]}' as a separator, but currently separated by '{separator}'.")
                                if st.button(f"Click to reload with '{found_sep[0]}' separator", key="csv_shp_fix_sep"):
                                    # This triggers restart with manual intervention, but we can guide the user
                                    st.info(f"Please select '{found_sep[1]}' in the separator dropdown above (or Custom -> {found_sep[0]}).")
                        
                        # Store in session state
                        st.session_state.csv_shp_tool_df = df
                        st.session_state.csv_shp_tool_filename = uploaded_file.name
                        st.session_state.csv_shp_tool_columns = list(df.columns)
                        st.session_state.csv_shp_tool_separator_key = current_separator_key
                        
                        # Run auto-detection
                        st.session_state.csv_shp_auto_detect = self.auto_detect_geometry(df)
                        
                        st.success(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns")
                    
                    except UnicodeDecodeError:
                        # Try different encoding
                        try:
                            df = pd.read_csv(
                                uploaded_file, 
                                sep=separator,
                                engine='python',
                                on_bad_lines='warn',
                                encoding='latin-1',  # Fallback encoding
                                quotechar='"',  # Handle quoted fields
                                doublequote=True,  # Handle escaped quotes
                                skipinitialspace=True  # Skip spaces after delimiter
                            )
                            
                            st.session_state.csv_shp_tool_df = df
                            st.session_state.csv_shp_tool_filename = uploaded_file.name
                            st.session_state.csv_shp_tool_columns = list(df.columns)
                            st.session_state.csv_shp_tool_separator_key = current_separator_key
                            
                            # Run auto-detection
                            st.session_state.csv_shp_auto_detect = self.auto_detect_geometry(df)
                            
                            st.success(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns")
                            st.info("ℹ️ File loaded with latin-1 encoding")
                        except Exception as e2:
                            st.error(f"❌ Encoding error: {str(e2)}")
                            st.info("💡 Try saving your CSV with UTF-8 encoding")
                            return
                    
                    except Exception as e:
                        error_msg = str(e)
                        st.error(f"❌ Error reading CSV file: {error_msg}")
                        
                        # Provide specific help based on error type
                        if "field larger than field limit" in error_msg.lower():
                            st.warning("⚠️ CSV contains very large cells. The tool has been configured to handle this, but the error persists.")
                            st.info("💡 Try: 1) Check if the file is corrupted, 2) Try a different separator")
                        elif "separator" in error_msg.lower() or "delimiter" in error_msg.lower():
                            st.info("💡 Try selecting a different separator from the dropdown")
                        else:
                            st.info("💡 Suggestions: 1) Check file format, 2) Try different separator, 3) Verify file is not corrupted")
                        return
            
            # Use cached data
            df = st.session_state.csv_shp_tool_df
            columns = st.session_state.csv_shp_tool_columns
            
            if df is None:
                return
            
            # Show preview
            st.subheader("📋 Data Preview")
            st.dataframe(df.head(10))
            st.caption(f"Showing first 10 of {len(df)} rows")
            
            # Detect geometry columns
            detected = self.detect_geometry_columns(df)

            # Retrieve auto-detected settings
            auto_detect = st.session_state.get('csv_shp_auto_detect', {
                'method': 'none', 'confidence': 'low'
            })
            
            # Determine default method index
            method_map = {
                'wkt': 0,
                'wkb': 1,
                'latlon': 2,
                'xy': 3,
                'none': 0
            }
            default_method_index = method_map.get(auto_detect['method'], 0)
            
            # Geometry configuration
            st.subheader("🌐 Step 2: Configure Geometry")
            
            # If high confidence, show what we found
            if auto_detect['confidence'] == 'high':
                st.info(f"✨ {auto_detect['message']}")
            
            geometry_method = st.radio(
                "How is geometry stored in your CSV?",
                options=[
                    "WKT (Well-Known Text) format",
                    "WKB / EWKB (Well-Known Binary)",
                    "Latitude/Longitude columns",
                    "X/Y coordinate columns"
                ],
                index=default_method_index,
                key="csv_shp_geom_method"
            )
            
            gdf = None
            
            if geometry_method == "WKT (Well-Known Text) format":
                # Determine default column
                wkt_col_index = 0
                if auto_detect['method'] == 'wkt' and auto_detect['wkt_column'] in columns:
                    wkt_col_index = columns.index(auto_detect['wkt_column'])
                elif detected['wkt_candidates'] and detected['wkt_candidates'][0] in columns:
                    wkt_col_index = columns.index(detected['wkt_candidates'][0])
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    wkt_column = st.selectbox(
                        "Column containing WKT geometry",
                        options=columns,
                        index=wkt_col_index,
                        key="csv_shp_wkt_col"
                    )
                with col2:
                    st.write("") # Spacer
                    st.write("") # Spacer
                    parse_btn = st.button("🔄 Parse", key="csv_shp_parse_wkt_manual")
                
                # Show sample values
                with st.expander("View sample geometry values"):
                    st.write(df[wkt_column].head(5).tolist())

                # Auto-parse if high confidence and not yet parsed
                should_auto_parse = (
                    auto_detect['method'] == 'wkt' and 
                    auto_detect['confidence'] == 'high' and 
                    st.session_state.get('csv_shp_tool_gdf') is None
                )
                
                if parse_btn or should_auto_parse or (st.session_state.get('csv_shp_tool_gdf') is not None):
                    # logic to process
                    if parse_btn or should_auto_parse:
                        with st.spinner("Parsing WKT geometries..."):
                            try:
                                geometries = df[wkt_column].apply(self.parse_wkt_geometry)
                                
                                # Check for parsing errors
                                null_count = geometries.isna().sum()
                                if null_count > 0:
                                    st.warning(f"⚠️ {null_count} rows have invalid WKT geometry and will be skipped.")
                                
                                # Create GeoDataFrame
                                valid_mask = geometries.notna()
                                if valid_mask.sum() == 0:
                                    st.error("❌ No valid geometries found.")
                                else:
                                    gdf = gpd.GeoDataFrame(
                                        df[valid_mask],
                                        geometry=geometries[valid_mask],
                                        crs="EPSG:4326"  # Default, user can change
                                    )
                                    
                                    # Detect geometry types
                                    geom_types = gdf.geometry.geom_type.unique()
                                    st.success(f"✅ Parsed {len(gdf)} geometries. Types: {', '.join(geom_types)}")
                                    
                                    # Store in session state
                                    st.session_state.csv_shp_tool_gdf = gdf
                            
                            except Exception as e:
                                st.error(f"❌ Error parsing WKT: {str(e)}")
            
            elif geometry_method == "WKB / EWKB (Well-Known Binary)":
                # Determine default column
                wkb_col_index = 0
                if auto_detect['method'] == 'wkb' and auto_detect['wkb_column'] in columns:
                    wkb_col_index = columns.index(auto_detect['wkb_column'])
                elif detected['wkb_candidates'] and detected['wkb_candidates'][0] in columns:
                    wkb_col_index = columns.index(detected['wkb_candidates'][0])
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    wkb_column = st.selectbox(
                        "Column containing WKB / EWKB hex geometry",
                        options=columns,
                        index=wkb_col_index,
                        key="csv_shp_wkb_col"
                    )
                with col2:
                    st.write("") # Spacer
                    st.write("") # Spacer
                    parse_wkb_btn = st.button("🔄 Parse", key="csv_shp_parse_wkb_manual")
                
                # Show sample values
                with st.expander("View sample hex values"):
                    st.write(df[wkb_column].head(5).tolist())

                # Auto-parse if high confidence and not yet parsed
                should_auto_parse_wkb = (
                    auto_detect['method'] == 'wkb' and 
                    auto_detect['confidence'] == 'high' and 
                    st.session_state.get('csv_shp_tool_gdf') is None
                )
                
                if parse_wkb_btn or should_auto_parse_wkb or (st.session_state.get('csv_shp_tool_gdf') is not None):
                    if parse_wkb_btn or should_auto_parse_wkb:
                        with st.spinner("Parsing WKB geometries..."):
                            try:
                                geometries = df[wkb_column].apply(self.parse_wkb_geometry)
                                
                                null_count = geometries.isna().sum()
                                if null_count > 0:
                                    st.warning(f"⚠️ {null_count} rows have invalid WKB geometry and will be skipped.")
                                
                                valid_mask = geometries.notna()
                                if valid_mask.sum() == 0:
                                    st.error("❌ No valid WKB geometries found.")
                                else:
                                    gdf = gpd.GeoDataFrame(
                                        df[valid_mask],
                                        geometry=geometries[valid_mask],
                                        crs="EPSG:4326"
                                    )
                                    geom_types = gdf.geometry.geom_type.unique()
                                    st.success(f"✅ Parsed {len(gdf)} geometries. Types: {', '.join(geom_types)}")
                                    st.session_state.csv_shp_tool_gdf = gdf
                            except Exception as e:
                                st.error(f"❌ Error parsing WKB: {str(e)}")
            
            elif geometry_method == "Latitude/Longitude columns":
                # Determine default columns
                lat_index = 0
                lon_index = 0
                
                if auto_detect['method'] == 'latlon':
                    if auto_detect['lat_column'] in columns:
                        lat_index = columns.index(auto_detect['lat_column'])
                    if auto_detect['lon_column'] in columns:
                        lon_index = columns.index(auto_detect['lon_column'])
                elif detected['lat_candidates'] and detected['lon_candidates']:
                    if detected['lat_candidates'][0] in columns:
                        lat_index = columns.index(detected['lat_candidates'][0])
                    if detected['lon_candidates'][0] in columns:
                        lon_index = columns.index(detected['lon_candidates'][0])

                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    lat_column = st.selectbox(
                        "Latitude column",
                        options=columns,
                        index=lat_index,
                        key="csv_shp_lat_col"
                    )
                
                with col2:
                    lon_column = st.selectbox(
                        "Longitude column",
                        options=columns,
                        index=lon_index,
                        key="csv_shp_lon_col"
                    )
                
                with col3:
                    st.write("") # Spacer
                    st.write("") # Spacer
                    create_btn = st.button("🔄 Create", key="csv_shp_create_points")
                
                # Show sample values
                with st.expander("View sample coordinate values"):
                    st.write(df[[lat_column, lon_column]].head(5))

                # Auto-create if high confidence
                should_auto_create = (
                    auto_detect['method'] == 'latlon' and 
                    auto_detect['confidence'] == 'high' and 
                    st.session_state.get('csv_shp_tool_gdf') is None
                )
                
                if create_btn or should_auto_create or (st.session_state.get('csv_shp_tool_gdf') is not None):
                    if create_btn or should_auto_create:
                        with st.spinner("Creating point geometries..."):
                            try:
                                geometries = df.apply(
                                    lambda row: self.create_point_from_coords(row[lon_column], row[lat_column]),
                                    axis=1
                                )
                                
                                # Check for parsing errors
                                null_count = geometries.isna().sum()
                                if null_count > 0:
                                    st.warning(f"⚠️ {null_count} rows have invalid coordinates and will be skipped.")
                                
                                # Create GeoDataFrame
                                valid_mask = geometries.notna()
                                if valid_mask.sum() == 0:
                                    st.error("❌ No valid coordinates found.")
                                else:
                                    gdf = gpd.GeoDataFrame(
                                        df[valid_mask],
                                        geometry=geometries[valid_mask],
                                        crs="EPSG:4326"  # WGS84 for lat/lon
                                    )
                                    
                                    st.success(f"✅ Created {len(gdf)} point geometries")
                                    
                                    # Store in session state
                                    st.session_state.csv_shp_tool_gdf = gdf
                            
                            except Exception as e:
                                st.error(f"❌ Error creating points: {str(e)}")

            else:  # X/Y coordinates
                # Defaults
                x_index = 0
                y_index = 0
                
                if auto_detect['method'] == 'xy':
                    if auto_detect['x_column'] in columns:
                        x_index = columns.index(auto_detect['x_column'])
                    if auto_detect['y_column'] in columns:
                        y_index = columns.index(auto_detect['y_column'])
                elif detected['x_candidates'] and detected['y_candidates']:
                    if detected['x_candidates'][0] in columns:
                        x_index = columns.index(detected['x_candidates'][0])
                    if detected['y_candidates'][0] in columns:
                        y_index = columns.index(detected['y_candidates'][0])
                        
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    x_column = st.selectbox(
                        "X coordinate column",
                        options=columns,
                        index=x_index,
                        key="csv_shp_x_col"
                    )
                
                with col2:
                    y_column = st.selectbox(
                        "Y coordinate column",
                        options=columns,
                        index=y_index,
                        key="csv_shp_y_col"
                    )
                
                with col3:
                    st.write("") 
                    st.write("")
                    create_xy_btn = st.button("🔄 Create", key="csv_shp_create_xy_points")
                
                # Show sample values
                with st.expander("View sample coordinate values"):
                    st.write(df[[x_column, y_column]].head(5))

                # Auto-create if medium/high confidence
                should_auto_create_xy = (
                    auto_detect['method'] == 'xy' and 
                    auto_detect['confidence'] in ['high', 'medium'] and 
                    st.session_state.get('csv_shp_tool_gdf') is None
                )

                if create_xy_btn or should_auto_create_xy or (st.session_state.get('csv_shp_tool_gdf') is not None):
                    if create_xy_btn or should_auto_create_xy:
                        with st.spinner("Creating point geometries..."):
                            try:
                                geometries = df.apply(
                                    lambda row: self.create_point_from_coords(row[x_column], row[y_column]),
                                    axis=1
                                )
                                
                                null_count = geometries.isna().sum()
                                if null_count > 0:
                                    st.warning(f"⚠️ {null_count} rows have invalid coordinates and will be skipped.")
                                
                                valid_mask = geometries.notna()
                                if valid_mask.sum() == 0:
                                    st.error("❌ No valid coordinates found.")
                                else:
                                    gdf = gpd.GeoDataFrame(
                                        df[valid_mask],
                                        geometry=geometries[valid_mask],
                                        crs="EPSG:4326"  # Default
                                    )
                                    
                                    st.success(f"✅ Created {len(gdf)} point geometries")
                                    st.warning("⚠️ Default CRS set to EPSG:4326. Please select the correct CRS below.")
                                    
                                    st.session_state.csv_shp_tool_gdf = gdf
                            
                            except Exception as e:
                                st.error(f"❌ Error creating points: {str(e)}")
            
            # If GeoDataFrame was created
            if 'csv_shp_tool_gdf' in st.session_state and st.session_state.csv_shp_tool_gdf is not None:
                gdf = st.session_state.csv_shp_tool_gdf
                
                st.divider()
                
                # CRS selection
                st.subheader("🌍 Step 3: Select Coordinate Reference System")
                
                crs_method = st.radio(
                    "CRS Selection",
                    options=["Choose from common EPSG codes", "Enter custom EPSG code"],
                    index=0,
                    key="csv_shp_crs_method"
                )
                
                if crs_method == "Choose from common EPSG codes":
                    epsg_options = [f"{code} - {desc}" for code, desc in COMMON_EPSG_CODES.items()]
                    selected_option = st.selectbox(
                        "Select CRS",
                        options=epsg_options,
                        index=0,
                        key="csv_shp_epsg_select"
                    )
                    target_epsg = int(selected_option.split(" - ")[0])
                else:
                    target_epsg = st.number_input(
                        "Enter EPSG code",
                        min_value=1,
                        max_value=99999,
                        value=4326,
                        step=1,
                        key="csv_shp_custom_epsg"
                    )
                
                # Update CRS
                gdf = gdf.set_crs(f"EPSG:{target_epsg}", allow_override=True)
                
                # Output options
                st.subheader("💾 Step 4: Export to Shapefile")
                
                output_format = st.radio(
                    "Output Format",
                    options=["Shapefile (ZIP)", "GeoPackage (.gpkg)"],
                    index=0,
                    key="csv_shp_output_format"
                )
                
                if st.button("🚀 Convert to Shapefile", type="primary", use_container_width=True, key="csv_shp_convert_btn"):
                    try:
                        with st.spinner("Creating shapefile..."):
                            with create_temp_directory() as output_dir:
                                if output_format == "Shapefile (ZIP)":
                                    output_path = create_shapefile_zip(
                                        gdf,
                                        "converted_shapefile",
                                        output_dir
                                    )
                                    file_name = "converted_shapefile.zip"
                                    mime_type = "application/zip"
                                else:
                                    output_path = os.path.join(output_dir, "converted_shapefile.gpkg")
                                    gdf.to_file(output_path, driver="GPKG")
                                    file_name = "converted_shapefile.gpkg"
                                    mime_type = "application/geopackage+sqlite3"
                                
                                # Read file for download
                                with open(output_path, 'rb') as f:
                                    output_data = f.read()
                                
                                st.success("✅ Shapefile created successfully!")
                                
                                # Download button
                                st.download_button(
                                    label="⬇️ Download Shapefile",
                                    data=output_data,
                                    file_name=file_name,
                                    mime=mime_type,
                                    use_container_width=True,
                                    key="csv_shp_download_btn"
                                )
                                
                                # Summary
                                geom_types = gdf.geometry.geom_type.value_counts().to_dict()
                                geom_summary = ", ".join([f"{count} {gtype}" for gtype, count in geom_types.items()])
                                
                                st.info(f"""
                                **Conversion Summary:**
                                - Features created: {len(gdf)}
                                - Geometry types: {geom_summary}
                                - CRS: EPSG:{target_epsg}
                                - Attributes: {len(gdf.columns) - 1} columns
                                """)
                    
                    except Exception as e:
                        st.error(f"❌ Error creating shapefile: {str(e)}")
                        import traceback
                        with st.expander("View error details"):
                            st.code(traceback.format_exc())
        
        else:
            # Clear session state
            if st.session_state.csv_shp_tool_filename is not None:
                st.session_state.csv_shp_tool_df = None
                st.session_state.csv_shp_tool_filename = None
                st.session_state.csv_shp_tool_columns = []
                if 'csv_shp_tool_gdf' in st.session_state:
                    del st.session_state.csv_shp_tool_gdf
