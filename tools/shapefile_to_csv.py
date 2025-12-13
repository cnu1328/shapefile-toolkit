"""
Tool for converting shapefiles to CSV format.
"""

import os
import streamlit as st
from typing import Optional
from core.base_tool import BaseTool
from core.utils_io import get_gdf_from_upload, create_temp_directory, save_gdf_as_csv


class ShapefileToCSVTool(BaseTool):
    """
    Tool for exporting shapefile attributes to CSV format.
    
    Features:
    - Upload shapefile ZIP
    - Select output separator
    - Choose which columns to export
    - Optional geometry export as WKT
    """
    
    @property
    def name(self) -> str:
        return "Shapefile to CSV"
    
    @property
    def description(self) -> str:
        return "Export shapefile attributes to CSV format with customizable separators and column selection."
    
    @property
    def icon(self) -> str:
        return "📊"
    
    def render_ui(self) -> None:
        """Render the Streamlit UI for this tool."""
        st.header(f"{self.icon} {self.name}")
        st.markdown(self.description)
        st.divider()
        
        # Initialize session state for this tool
        if 'csv_tool_gdf' not in st.session_state:
            st.session_state.csv_tool_gdf = None
            st.session_state.csv_tool_filename = None
            st.session_state.csv_tool_attr_columns = []
        
        # File upload section
        st.subheader("📁 Step 1: Upload Shapefile")
        uploaded_file = st.file_uploader(
            "Upload a ZIP file containing your shapefile",
            type=['zip'],
            help="The ZIP should contain .shp, .shx, .dbf, and optionally .prj files",
            key="csv_upload"
        )
        
        # Process uploaded file only when it changes
        if uploaded_file is not None:
            # Check if this is a new file
            if st.session_state.csv_tool_filename != uploaded_file.name:
                with st.spinner("Loading shapefile..."):
                    with create_temp_directory() as temp_dir:
                        gdf, message = get_gdf_from_upload(uploaded_file, temp_dir)
                        
                        if gdf is None:
                            st.error(f"❌ {message}")
                            st.session_state.csv_tool_gdf = None
                            st.session_state.csv_tool_filename = None
                            return
                        
                        # Store in session state
                        st.session_state.csv_tool_gdf = gdf
                        st.session_state.csv_tool_filename = uploaded_file.name
                        st.session_state.csv_tool_attr_columns = [col for col in gdf.columns if col != 'geometry']
                        
                        st.success(f"✅ {message}")
            
            # Use GeoDataFrame from session state
            gdf = st.session_state.csv_tool_gdf
            attr_columns = st.session_state.csv_tool_attr_columns
            
            if gdf is None:
                return
            
            # Show preview
            st.subheader("📋 Data Preview")
            
            if not attr_columns:
                st.warning("⚠️ No attribute columns found in the shapefile.")
                return
            
            # Show preview table
            preview_df = gdf[attr_columns].head(10)
            st.dataframe(preview_df, use_container_width=True)
            st.caption(f"Showing first 10 of {len(gdf)} features")
            
            # Configuration section
            st.subheader("⚙️ Step 2: Configure Export Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Separator selection
                separator_options = {
                    "Comma (,)": ",",
                    "Semicolon (;)": ";",
                    "Pipe (|)": "|",
                    "Tab": "\t",
                    "Custom": "custom"
                }
                
                separator_choice = st.selectbox(
                    "Output Separator",
                    options=list(separator_options.keys()),
                    index=0,
                    key="csv_separator_choice"
                )
                
                if separator_choice == "Custom":
                    custom_separator = st.text_input(
                        "Enter custom separator",
                        value=",",
                        max_chars=5,
                        key="csv_custom_separator"
                    )
                    separator = custom_separator
                else:
                    separator = separator_options[separator_choice]
            
            with col2:
                # Geometry option
                include_geometry = st.checkbox(
                    "Include geometry as WKT",
                    value=False,
                    help="Add a geometry column with Well-Known Text representation",
                    key="csv_include_geom"
                )
            
            # Column selection
            st.markdown("**Select Columns to Export**")
            
            col_select_all = st.checkbox("Select All Columns", value=True, key="csv_select_all")
            
            if col_select_all:
                selected_columns = attr_columns
            else:
                selected_columns = st.multiselect(
                    "Choose columns",
                    options=attr_columns,
                    default=attr_columns,
                    key="csv_column_select"
                )
            
            if not selected_columns:
                st.warning("⚠️ Please select at least one column to export.")
                return
            
            st.info(f"📌 {len(selected_columns)} column(s) selected")
            
            # Export section
            st.subheader("💾 Step 3: Export to CSV")
            
            if st.button("🚀 Generate CSV", type="primary", use_container_width=True, key="csv_generate_btn"):
                try:
                    with st.spinner("Generating CSV file..."):
                        # Create output CSV
                        with create_temp_directory() as output_dir:
                            csv_path = os.path.join(output_dir, "exported_attributes.csv")
                            
                            save_gdf_as_csv(
                                gdf,
                                csv_path,
                                separator=separator,
                                columns=selected_columns,
                                include_geometry=include_geometry
                            )
                            
                            # Read the CSV for download
                            with open(csv_path, 'rb') as f:
                                csv_data = f.read()
                            
                            st.success("✅ CSV file generated successfully!")
                            
                            # Download button
                            st.download_button(
                                label="⬇️ Download CSV",
                                data=csv_data,
                                file_name="shapefile_export.csv",
                                mime="text/csv",
                                use_container_width=True,
                                key="csv_download_btn"
                            )
                            
                            # Summary
                            st.info(f"""
                            **Export Summary:**
                            - Features exported: {len(gdf)}
                            - Columns exported: {len(selected_columns)}
                            - Separator: {repr(separator)}
                            - Geometry included: {'Yes' if include_geometry else 'No'}
                            """)
                
                except Exception as e:
                    st.error(f"❌ Error generating CSV: {str(e)}")
        
        else:
            # Clear session state when no file is uploaded
            if st.session_state.csv_tool_gdf is not None:
                st.session_state.csv_tool_gdf = None
                st.session_state.csv_tool_filename = None
                st.session_state.csv_tool_attr_columns = []
