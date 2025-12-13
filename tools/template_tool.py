"""
Template tool for adding new shapefile operations.

This is a skeleton implementation showing how to create a new tool.
Copy this file and modify it to implement your own shapefile operation.
"""

import streamlit as st
from core.base_tool import BaseTool
from core.utils_io import get_gdf_from_upload, create_temp_directory


class TemplateTool(BaseTool):
    """
    Template tool for future extensions.
    
    TODO: Implement your custom shapefile operation here.
    
    Example ideas:
    - Buffer geometries
    - Clip/intersect shapefiles
    - Dissolve by attribute
    - Spatial join
    - Attribute filter
    - Simplify geometries
    - Calculate area/length
    """
    
    @property
    def name(self) -> str:
        # TODO: Change this to your tool name
        return "Template Tool"
    
    @property
    def description(self) -> str:
        # TODO: Change this to describe your tool
        return "This is a template for creating new shapefile processing tools."
    
    @property
    def icon(self) -> str:
        # TODO: Choose an appropriate emoji icon
        return "🔧"
    
    def render_ui(self) -> None:
        """
        Render the Streamlit UI for this tool.
        
        TODO: Implement your tool's UI here.
        
        Typical structure:
        1. Header and description
        2. File upload section
        3. Configuration/options section
        4. Process button
        5. Results and download section
        """
        st.header(f"{self.icon} {self.name}")
        st.markdown(self.description)
        st.divider()
        
        # TODO: Remove this warning when implementing
        st.warning("⚠️ This is a template tool. Implement your functionality here.")
        
        # Example implementation structure:
        
        # Step 1: Upload
        st.subheader("📁 Step 1: Upload Shapefile")
        uploaded_file = st.file_uploader(
            "Upload a ZIP file containing your shapefile",
            type=['zip'],
            key="template_upload"
        )
        
        if uploaded_file is not None:
            with create_temp_directory() as temp_dir:
                gdf, message = get_gdf_from_upload(uploaded_file, temp_dir)
                
                if gdf is None:
                    st.error(f"❌ {message}")
                    return
                
                st.success(f"✅ {message}")
                
                # Step 2: Configuration
                st.subheader("⚙️ Step 2: Configure Options")
                
                # TODO: Add your configuration widgets here
                # Examples:
                # - st.slider() for numeric parameters
                # - st.selectbox() for dropdown options
                # - st.checkbox() for boolean flags
                # - st.text_input() for text parameters
                
                st.info("💡 Add your configuration options here")
                
                # Step 3: Process
                st.subheader("🚀 Step 3: Process")
                
                if st.button("Process Shapefile", type="primary", use_container_width=True):
                    try:
                        with st.spinner("Processing..."):
                            # TODO: Implement your processing logic here
                            
                            # Example workflow:
                            # 1. Process the GeoDataFrame
                            # processed_gdf = your_processing_function(gdf, parameters)
                            
                            # 2. Create output file
                            # output_path = create_shapefile_zip(processed_gdf, "output", temp_dir)
                            
                            # 3. Provide download button
                            # with open(output_path, 'rb') as f:
                            #     st.download_button(...)
                            
                            st.info("💡 Implement your processing logic here")
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        else:
            st.info("👆 Upload a shapefile ZIP file to get started.")


# ============================================================================
# EXAMPLE: Buffer Tool Implementation (commented out)
# ============================================================================
# Uncomment and modify this to create a buffer tool:

"""
class BufferTool(BaseTool):
    '''Tool for creating buffers around shapefile geometries.'''
    
    @property
    def name(self) -> str:
        return "Buffer Geometries"
    
    @property
    def description(self) -> str:
        return "Create buffer zones around shapefile features with customizable distance."
    
    @property
    def icon(self) -> str:
        return "⭕"
    
    def render_ui(self) -> None:
        st.header(f"{self.icon} {self.name}")
        st.markdown(self.description)
        st.divider()
        
        st.subheader("📁 Step 1: Upload Shapefile")
        uploaded_file = st.file_uploader(
            "Upload shapefile ZIP",
            type=['zip'],
            key="buffer_upload"
        )
        
        if uploaded_file is not None:
            with create_temp_directory() as temp_dir:
                gdf, message = get_gdf_from_upload(uploaded_file, temp_dir)
                
                if gdf is None:
                    st.error(f"❌ {message}")
                    return
                
                st.success(f"✅ {message}")
                
                st.subheader("⚙️ Step 2: Buffer Settings")
                
                buffer_distance = st.number_input(
                    "Buffer Distance",
                    min_value=0.0,
                    value=100.0,
                    step=10.0,
                    help="Distance in the units of the shapefile's CRS"
                )
                
                resolution = st.slider(
                    "Buffer Resolution",
                    min_value=4,
                    max_value=32,
                    value=16,
                    help="Number of segments per quarter circle"
                )
                
                st.subheader("🚀 Step 3: Create Buffer")
                
                if st.button("Create Buffer", type="primary", use_container_width=True):
                    try:
                        with st.spinner("Creating buffer..."):
                            # Create buffer
                            buffered_gdf = gdf.copy()
                            buffered_gdf['geometry'] = gdf.geometry.buffer(
                                buffer_distance,
                                resolution=resolution
                            )
                            
                            # Create output
                            output_path = create_shapefile_zip(
                                buffered_gdf,
                                "buffered",
                                temp_dir
                            )
                            
                            with open(output_path, 'rb') as f:
                                output_data = f.read()
                            
                            st.success("✅ Buffer created successfully!")
                            
                            st.download_button(
                                label="⬇️ Download Buffered Shapefile",
                                data=output_data,
                                file_name="buffered_shapefile.zip",
                                mime="application/zip",
                                use_container_width=True
                            )
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
"""
