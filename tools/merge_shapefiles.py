"""
Tool for merging multiple shapefiles into one.
"""

import os
import streamlit as st
import geopandas as gpd
from typing import List
from core.base_tool import BaseTool
from core.utils_io import get_gdf_from_upload, create_temp_directory, create_shapefile_zip
from core.utils_geo import (
    validate_crs_compatibility,
    validate_schema_compatibility,
    align_schemas,
    reproject_to_common_crs,
    get_crs_info
)


class MergeShapefilesTool(BaseTool):
    """
    Tool for merging multiple shapefiles into a single shapefile.
    
    Features:
    - Upload 2 or more shapefiles
    - Validate CRS and schema compatibility
    - Auto-align schemas and reproject if needed
    - Merge into single output
    """
    
    @property
    def name(self) -> str:
        return "Merge Shapefiles"
    
    @property
    def description(self) -> str:
        return "Combine multiple shapefiles into a single shapefile with automatic schema alignment and CRS handling."
    
    @property
    def icon(self) -> str:
        return "🔗"
    
    def render_ui(self) -> None:
        """Render the Streamlit UI for this tool."""
        st.header(f"{self.icon} {self.name}")
        st.markdown(self.description)
        st.divider()
        
        # File upload section
        st.subheader("📁 Step 1: Upload Shapefiles")
        st.info("💡 Upload 2 or more shapefile ZIP files to merge them together.")
        
        uploaded_files = st.file_uploader(
            "Upload shapefile ZIP files",
            type=['zip'],
            accept_multiple_files=True,
            help="Each ZIP should contain .shp, .shx, .dbf, and optionally .prj files",
            key="merge_upload"
        )
        
        if uploaded_files and len(uploaded_files) >= 2:
            # Load all shapefiles
            gdfs = []
            gdf_names = []
            
            with create_temp_directory() as temp_dir:
                st.subheader("📊 Loading Shapefiles")
                
                for i, uploaded_file in enumerate(uploaded_files):
                    with st.expander(f"📄 {uploaded_file.name}", expanded=False):
                        gdf, message = get_gdf_from_upload(uploaded_file, temp_dir)
                        
                        if gdf is None:
                            st.error(f"❌ {message}")
                            return
                        
                        st.success(f"✅ {message}")
                        
                        # Show CRS info
                        crs_info = get_crs_info(gdf)
                        st.write(f"**CRS:** {crs_info['epsg']} - {crs_info['name']}")
                        st.write(f"**Columns:** {', '.join([col for col in gdf.columns if col != 'geometry'])}")
                        
                        gdfs.append(gdf)
                        gdf_names.append(uploaded_file.name)
                
                if len(gdfs) < 2:
                    st.warning("⚠️ Please upload at least 2 shapefiles to merge.")
                    return
                
                # Validation section
                st.subheader("🔍 Step 2: Validation")
                
                # Check CRS compatibility
                crs_compatible, crs_message, crs_list = validate_crs_compatibility(gdfs)
                
                if crs_compatible:
                    st.success(f"✅ {crs_message}")
                else:
                    st.warning(f"⚠️ {crs_message}")
                    for crs_desc in crs_list:
                        st.write(f"  - {crs_desc}")
                
                # Check schema compatibility
                schema_compatible, schema_message, schema_diff = validate_schema_compatibility(gdfs)
                
                if schema_compatible:
                    st.success(f"✅ {schema_message}")
                else:
                    st.warning(f"⚠️ {schema_message}")
                
                # Configuration section
                st.subheader("⚙️ Step 3: Merge Options")
                
                # CRS handling
                if not crs_compatible:
                    st.markdown("**CRS Handling**")
                    reproject_option = st.radio(
                        "How to handle different CRS?",
                        options=[
                            "Use CRS from first shapefile",
                            "Use CRS from last shapefile",
                            "Reproject all to WGS 84 (EPSG:4326)"
                        ],
                        index=0,
                        key="merge_crs_option"
                    )
                    
                    if "first" in reproject_option:
                        target_epsg = gdfs[0].crs.to_epsg() if gdfs[0].crs else None
                    elif "last" in reproject_option:
                        target_epsg = gdfs[-1].crs.to_epsg() if gdfs[-1].crs else None
                    else:
                        target_epsg = 4326
                else:
                    target_epsg = None
                
                # Schema handling
                if not schema_compatible:
                    st.markdown("**Schema Handling**")
                    align_schema = st.checkbox(
                        "Automatically align schemas (add missing columns with null values)",
                        value=True,
                        key="merge_align_schema"
                    )
                else:
                    align_schema = False
                
                # Output format
                output_format = st.radio(
                    "Output Format",
                    options=["Shapefile (ZIP)", "GeoPackage (.gpkg)"],
                    index=0,
                    key="merge_output_format"
                )
                
                # Merge section
                st.subheader("🔀 Step 4: Merge Shapefiles")
                
                if st.button("🚀 Merge Shapefiles", type="primary", use_container_width=True, key="merge_execute_btn"):
                    try:
                        with st.spinner("Merging shapefiles..."):
                            # Reproject if needed
                            if target_epsg:
                                st.info(f"🔄 Reprojecting all shapefiles to EPSG:{target_epsg}...")
                                gdfs = reproject_to_common_crs(gdfs, target_epsg)
                            
                            # Align schemas if needed
                            if align_schema:
                                st.info("🔄 Aligning schemas...")
                                gdfs = align_schemas(gdfs)
                            
                            # Merge all GeoDataFrames
                            st.info("🔄 Merging geometries and attributes...")
                            merged_gdf = gpd.GeoDataFrame(
                                pd.concat(gdfs, ignore_index=True),
                                crs=gdfs[0].crs
                            )
                            
                            # Create output file
                            with create_temp_directory() as output_dir:
                                if output_format == "Shapefile (ZIP)":
                                    output_path = create_shapefile_zip(
                                        merged_gdf,
                                        "merged_shapefile",
                                        output_dir
                                    )
                                    file_name = "merged_shapefile.zip"
                                    mime_type = "application/zip"
                                else:
                                    output_path = os.path.join(output_dir, "merged_shapefile.gpkg")
                                    merged_gdf.to_file(output_path, driver="GPKG")
                                    file_name = "merged_shapefile.gpkg"
                                    mime_type = "application/geopackage+sqlite3"
                                
                                # Read file for download
                                with open(output_path, 'rb') as f:
                                    output_data = f.read()
                                
                                st.success("✅ Shapefiles merged successfully!")
                                
                                # Download button
                                st.download_button(
                                    label="⬇️ Download Merged Shapefile",
                                    data=output_data,
                                    file_name=file_name,
                                    mime=mime_type,
                                    use_container_width=True,
                                    key="merge_download_btn"
                                )
                                
                                # Summary
                                input_counts = [len(gdf) for gdf in gdfs]
                                crs_info = get_crs_info(merged_gdf)
                                
                                st.info(f"""
                                **Merge Summary:**
                                - Input shapefiles: {len(gdfs)}
                                - Input feature counts: {', '.join(map(str, input_counts))}
                                - Output features: {len(merged_gdf)}
                                - Output CRS: {crs_info['epsg']} - {crs_info['name']}
                                - Schema aligned: {'Yes' if align_schema else 'No'}
                                - Reprojected: {'Yes' if target_epsg else 'No'}
                                """)
                    
                    except Exception as e:
                        st.error(f"❌ Error merging shapefiles: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        
        elif uploaded_files and len(uploaded_files) < 2:
            st.warning("⚠️ Please upload at least 2 shapefile ZIP files to merge.")
        else:
            st.info("👆 Upload 2 or more shapefile ZIP files to get started.")


import pandas as pd
