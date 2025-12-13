"""
Tool for adding/combining two shapefiles.
"""

import os
import streamlit as st
import geopandas as gpd
import pandas as pd
from core.base_tool import BaseTool
from core.utils_io import get_gdf_from_upload, create_temp_directory, create_shapefile_zip
from core.utils_geo import get_crs_info, reproject_gdf, align_schemas


class AddShapefilesTool(BaseTool):
    """
    Tool for adding/combining exactly two shapefiles.
    
    Features:
    - Upload exactly 2 shapefiles
    - Handle CRS differences with reprojection
    - Combine geometries and attributes (union/append)
    - Show transformation summary
    """
    
    @property
    def name(self) -> str:
        return "Add Two Shapefiles"
    
    @property
    def description(self) -> str:
        return "Combine exactly two shapefiles by appending their features, with automatic CRS handling and schema alignment."
    
    @property
    def icon(self) -> str:
        return "➕"
    
    def render_ui(self) -> None:
        """Render the Streamlit UI for this tool."""
        st.header(f"{self.icon} {self.name}")
        st.markdown(self.description)
        st.divider()
        
        # File upload section
        st.subheader("📁 Step 1: Upload Two Shapefiles")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**First Shapefile**")
            uploaded_file1 = st.file_uploader(
                "Upload first shapefile ZIP",
                type=['zip'],
                help="ZIP containing .shp, .shx, .dbf, and optionally .prj",
                key="add_upload1"
            )
        
        with col2:
            st.markdown("**Second Shapefile**")
            uploaded_file2 = st.file_uploader(
                "Upload second shapefile ZIP",
                type=['zip'],
                help="ZIP containing .shp, .shx, .dbf, and optionally .prj",
                key="add_upload2"
            )
        
        if uploaded_file1 is not None and uploaded_file2 is not None:
            with create_temp_directory() as temp_dir:
                # Load first shapefile
                st.subheader("📊 Shapefile Information")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**First Shapefile**")
                    gdf1, message1 = get_gdf_from_upload(uploaded_file1, temp_dir)
                    
                    if gdf1 is None:
                        st.error(f"❌ {message1}")
                        return
                    
                    st.success(f"✅ {message1}")
                    crs_info1 = get_crs_info(gdf1)
                    st.write(f"**CRS:** {crs_info1['epsg']}")
                    st.write(f"**Features:** {len(gdf1)}")
                    
                    attr_cols1 = [col for col in gdf1.columns if col != 'geometry']
                    st.write(f"**Columns:** {len(attr_cols1)}")
                    with st.expander("View columns"):
                        st.write(", ".join(attr_cols1))
                
                with col2:
                    st.markdown("**Second Shapefile**")
                    gdf2, message2 = get_gdf_from_upload(uploaded_file2, temp_dir)
                    
                    if gdf2 is None:
                        st.error(f"❌ {message2}")
                        return
                    
                    st.success(f"✅ {message2}")
                    crs_info2 = get_crs_info(gdf2)
                    st.write(f"**CRS:** {crs_info2['epsg']}")
                    st.write(f"**Features:** {len(gdf2)}")
                    
                    attr_cols2 = [col for col in gdf2.columns if col != 'geometry']
                    st.write(f"**Columns:** {len(attr_cols2)}")
                    with st.expander("View columns"):
                        st.write(", ".join(attr_cols2))
                
                # Check CRS compatibility
                st.subheader("🔍 Step 2: Compatibility Check")
                
                crs_match = gdf1.crs == gdf2.crs
                schema_match = set(attr_cols1) == set(attr_cols2)
                
                if crs_match:
                    st.success(f"✅ Both shapefiles have the same CRS: {crs_info1['epsg']}")
                else:
                    st.warning(f"⚠️ Different CRS detected:")
                    st.write(f"  - First: {crs_info1['epsg']} - {crs_info1['name']}")
                    st.write(f"  - Second: {crs_info2['epsg']} - {crs_info2['name']}")
                
                if schema_match:
                    st.success("✅ Both shapefiles have identical attribute schemas")
                else:
                    st.warning("⚠️ Different attribute schemas detected")
                    
                    cols1_only = set(attr_cols1) - set(attr_cols2)
                    cols2_only = set(attr_cols2) - set(attr_cols1)
                    
                    if cols1_only:
                        st.write(f"  - Only in first: {', '.join(cols1_only)}")
                    if cols2_only:
                        st.write(f"  - Only in second: {', '.join(cols2_only)}")
                
                # Configuration section
                st.subheader("⚙️ Step 3: Combination Options")
                
                # CRS handling
                if not crs_match:
                    st.markdown("**CRS Handling**")
                    crs_option = st.radio(
                        "Target CRS for combined shapefile:",
                        options=[
                            f"Use CRS from first shapefile ({crs_info1['epsg']})",
                            f"Use CRS from second shapefile ({crs_info2['epsg']})",
                            "Reproject both to WGS 84 (EPSG:4326)"
                        ],
                        index=0,
                        key="add_crs_option"
                    )
                    
                    if "first" in crs_option:
                        target_crs = gdf1.crs
                        target_epsg = gdf1.crs.to_epsg() if gdf1.crs else None
                    elif "second" in crs_option:
                        target_crs = gdf2.crs
                        target_epsg = gdf2.crs.to_epsg() if gdf2.crs else None
                    else:
                        target_crs = None
                        target_epsg = 4326
                else:
                    target_crs = gdf1.crs
                    target_epsg = None
                
                # Output format
                output_format = st.radio(
                    "Output Format",
                    options=["Shapefile (ZIP)", "GeoPackage (.gpkg)"],
                    index=0,
                    key="add_output_format"
                )
                
                # Add section
                st.subheader("➕ Step 4: Combine Shapefiles")
                
                if st.button("🚀 Combine Shapefiles", type="primary", use_container_width=True, key="add_execute_btn"):
                    try:
                        with st.spinner("Combining shapefiles..."):
                            # Reproject if needed
                            gdf1_processed = gdf1.copy()
                            gdf2_processed = gdf2.copy()
                            
                            if not crs_match:
                                if target_epsg:
                                    st.info(f"🔄 Reprojecting to EPSG:{target_epsg}...")
                                    
                                    if gdf1.crs.to_epsg() != target_epsg:
                                        gdf1_processed, msg = reproject_gdf(gdf1, target_epsg)
                                        if gdf1_processed is None:
                                            st.error(f"❌ Error reprojecting first shapefile: {msg}")
                                            return
                                    
                                    if gdf2.crs.to_epsg() != target_epsg:
                                        gdf2_processed, msg = reproject_gdf(gdf2, target_epsg)
                                        if gdf2_processed is None:
                                            st.error(f"❌ Error reprojecting second shapefile: {msg}")
                                            return
                                else:
                                    # Reproject second to match first
                                    if gdf2.crs != target_crs:
                                        gdf2_processed = gdf2.to_crs(target_crs)
                            
                            # Align schemas if needed
                            if not schema_match:
                                st.info("🔄 Aligning attribute schemas...")
                                gdf1_processed, gdf2_processed = align_schemas([gdf1_processed, gdf2_processed])
                            
                            # Combine the GeoDataFrames
                            st.info("🔄 Combining features...")
                            combined_gdf = gpd.GeoDataFrame(
                                pd.concat([gdf1_processed, gdf2_processed], ignore_index=True),
                                crs=gdf1_processed.crs
                            )
                            
                            # Create output file
                            with create_temp_directory() as output_dir:
                                if output_format == "Shapefile (ZIP)":
                                    output_path = create_shapefile_zip(
                                        combined_gdf,
                                        "combined_shapefile",
                                        output_dir
                                    )
                                    file_name = "combined_shapefile.zip"
                                    mime_type = "application/zip"
                                else:
                                    output_path = os.path.join(output_dir, "combined_shapefile.gpkg")
                                    combined_gdf.to_file(output_path, driver="GPKG")
                                    file_name = "combined_shapefile.gpkg"
                                    mime_type = "application/geopackage+sqlite3"
                                
                                # Read file for download
                                with open(output_path, 'rb') as f:
                                    output_data = f.read()
                                
                                st.success("✅ Shapefiles combined successfully!")
                                
                                # Download button
                                st.download_button(
                                    label="⬇️ Download Combined Shapefile",
                                    data=output_data,
                                    file_name=file_name,
                                    mime=mime_type,
                                    use_container_width=True,
                                    key="add_download_btn"
                                )
                                
                                # Summary
                                final_crs_info = get_crs_info(combined_gdf)
                                
                                st.info(f"""
                                **Combination Summary:**
                                - First shapefile features: {len(gdf1)}
                                - Second shapefile features: {len(gdf2)}
                                - Combined features: {len(combined_gdf)}
                                - Output CRS: {final_crs_info['epsg']} - {final_crs_info['name']}
                                - CRS transformation applied: {'Yes' if not crs_match else 'No'}
                                - Schema aligned: {'Yes' if not schema_match else 'No'}
                                """)
                    
                    except Exception as e:
                        st.error(f"❌ Error combining shapefiles: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        
        elif uploaded_file1 is not None or uploaded_file2 is not None:
            st.info("👆 Please upload both shapefiles to continue.")
        else:
            st.info("👆 Upload two shapefile ZIP files to get started.")
