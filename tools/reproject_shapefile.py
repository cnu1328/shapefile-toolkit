"""
Tool for reprojecting shapefiles to different coordinate reference systems.
"""

import os
import streamlit as st
from core.base_tool import BaseTool
from core.utils_io import get_gdf_from_upload, create_temp_directory, create_shapefile_zip
from core.utils_geo import get_crs_info, reproject_gdf, COMMON_EPSG_CODES


class ReprojectShapefileTool(BaseTool):
    """
    Tool for reprojecting shapefiles to different CRS.
    
    Features:
    - Upload shapefile
    - Display current CRS information
    - Select target CRS from common options or custom EPSG
    - Reproject and download
    """
    
    @property
    def name(self) -> str:
        return "Reproject Shapefile"
    
    @property
    def description(self) -> str:
        return "Transform shapefile coordinates to a different coordinate reference system (CRS) with support for common EPSG codes."
    
    @property
    def icon(self) -> str:
        return "🌐"
    
    def render_ui(self) -> None:
        """Render the Streamlit UI for this tool."""
        st.header(f"{self.icon} {self.name}")
        st.markdown(self.description)
        st.divider()
        
        # File upload section
        st.subheader("📁 Step 1: Upload Shapefile")
        uploaded_file = st.file_uploader(
            "Upload a ZIP file containing your shapefile",
            type=['zip'],
            help="The ZIP should contain .shp, .shx, .dbf, and optionally .prj files",
            key="reproject_upload"
        )
        
        if uploaded_file is not None:
            with create_temp_directory() as temp_dir:
                # Load the shapefile
                gdf, message = get_gdf_from_upload(uploaded_file, temp_dir)
                
                if gdf is None:
                    st.error(f"❌ {message}")
                    return
                
                st.success(f"✅ {message}")
                
                # Display current CRS
                st.subheader("📍 Current CRS Information")
                
                crs_info = get_crs_info(gdf)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("EPSG Code", crs_info['epsg'])
                    st.write(f"**Name:** {crs_info['name']}")
                
                with col2:
                    if crs_info['proj4'] != "N/A":
                        with st.expander("View Proj4 String"):
                            st.code(crs_info['proj4'], language=None)
                
                # Target CRS selection
                st.subheader("🎯 Step 2: Select Target CRS")
                
                # CRS selection method
                selection_method = st.radio(
                    "How would you like to specify the target CRS?",
                    options=["Choose from common EPSG codes", "Enter custom EPSG code"],
                    index=0,
                    key="reproject_selection_method"
                )
                
                target_epsg = None
                
                if selection_method == "Choose from common EPSG codes":
                    # Create options list
                    epsg_options = [f"{code} - {desc}" for code, desc in COMMON_EPSG_CODES.items()]
                    
                    selected_option = st.selectbox(
                        "Select target CRS",
                        options=epsg_options,
                        index=0,
                        key="reproject_epsg_select"
                    )
                    
                    # Extract EPSG code
                    target_epsg = int(selected_option.split(" - ")[0])
                    
                    # Show description
                    st.info(f"📌 {COMMON_EPSG_CODES[target_epsg]}")
                
                else:
                    # Custom EPSG input
                    custom_epsg = st.number_input(
                        "Enter EPSG code",
                        min_value=1,
                        max_value=99999,
                        value=4326,
                        step=1,
                        help="Enter a valid EPSG code (e.g., 4326 for WGS 84)",
                        key="reproject_custom_epsg"
                    )
                    
                    target_epsg = custom_epsg
                    
                    # Try to get description
                    if target_epsg in COMMON_EPSG_CODES:
                        st.info(f"📌 {COMMON_EPSG_CODES[target_epsg]}")
                    else:
                        st.info(f"📌 Custom EPSG code: {target_epsg}")
                
                # Check if already in target CRS
                current_epsg = gdf.crs.to_epsg() if gdf.crs else None
                
                if current_epsg == target_epsg:
                    st.warning(f"⚠️ The shapefile is already in EPSG:{target_epsg}")
                
                # Output format
                st.subheader("⚙️ Step 3: Output Options")
                
                output_format = st.radio(
                    "Output Format",
                    options=["Shapefile (ZIP)", "GeoPackage (.gpkg)"],
                    index=0,
                    key="reproject_output_format"
                )
                
                # Reproject section
                st.subheader("🔄 Step 4: Reproject")
                
                if st.button("🚀 Reproject Shapefile", type="primary", use_container_width=True, key="reproject_execute_btn"):
                    if current_epsg == target_epsg:
                        st.info("ℹ️ No reprojection needed. Downloading original shapefile...")
                        reprojected_gdf = gdf
                    else:
                        try:
                            with st.spinner(f"Reprojecting to EPSG:{target_epsg}..."):
                                reprojected_gdf, reproject_message = reproject_gdf(gdf, target_epsg)
                                
                                if reprojected_gdf is None:
                                    st.error(f"❌ {reproject_message}")
                                    return
                                
                                st.success(f"✅ {reproject_message}")
                        
                        except Exception as e:
                            st.error(f"❌ Error during reprojection: {str(e)}")
                            return
                    
                    # Create output file
                    try:
                        with create_temp_directory() as output_dir:
                            if output_format == "Shapefile (ZIP)":
                                output_path = create_shapefile_zip(
                                    reprojected_gdf,
                                    f"reprojected_epsg{target_epsg}",
                                    output_dir
                                )
                                file_name = f"reprojected_epsg{target_epsg}.zip"
                                mime_type = "application/zip"
                            else:
                                output_path = os.path.join(output_dir, f"reprojected_epsg{target_epsg}.gpkg")
                                reprojected_gdf.to_file(output_path, driver="GPKG")
                                file_name = f"reprojected_epsg{target_epsg}.gpkg"
                                mime_type = "application/geopackage+sqlite3"
                            
                            # Read file for download
                            with open(output_path, 'rb') as f:
                                output_data = f.read()
                            
                            st.success("✅ Output file created successfully!")
                            
                            # Download button
                            st.download_button(
                                label="⬇️ Download Reprojected Shapefile",
                                data=output_data,
                                file_name=file_name,
                                mime=mime_type,
                                use_container_width=True,
                                key="reproject_download_btn"
                            )
                            
                            # Summary
                            new_crs_info = get_crs_info(reprojected_gdf)
                            
                            st.info(f"""
                            **Reprojection Summary:**
                            - Original CRS: {crs_info['epsg']} - {crs_info['name']}
                            - Target CRS: {new_crs_info['epsg']} - {new_crs_info['name']}
                            - Features: {len(reprojected_gdf)}
                            - Transformation: {'Applied' if current_epsg != target_epsg else 'Not needed'}
                            """)
                    
                    except Exception as e:
                        st.error(f"❌ Error creating output file: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        
        else:
            st.info("👆 Upload a shapefile ZIP file to get started.")
