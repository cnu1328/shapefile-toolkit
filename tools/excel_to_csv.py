"""
Tool for converting Excel files to CSV format.
"""

import os
import streamlit as st
import pandas as pd
from typing import Optional, List, Tuple
from core.base_tool import BaseTool
from core.utils_io import create_temp_directory


class ExcelToCSVTool(BaseTool):
    """
    Tool for converting Excel sheets to CSV format.
    
    Features:
    - Upload Excel file (.xlsx, .xls)
    - Select specific sheet to convert
    - Customizable separator
    - Handle edge cases (empty sheets, merged cells, formulas)
    """
    
    @property
    def name(self) -> str:
        return "Excel to CSV"
    
    @property
    def description(self) -> str:
        return "Convert Excel spreadsheets to CSV format with sheet selection and customizable separators."
    
    @property
    def icon(self) -> str:
        return "📑"
    
    def render_ui(self) -> None:
        """Render the Streamlit UI for this tool."""
        st.header(f"{self.icon} {self.name}")
        st.markdown(self.description)
        st.divider()
        
        # Initialize session state
        if 'excel_tool_file' not in st.session_state:
            st.session_state.excel_tool_file = None
            st.session_state.excel_tool_filename = None
            st.session_state.excel_tool_sheets = {}
            st.session_state.excel_tool_sheet_names = []
        
        # File upload section
        st.subheader("📁 Step 1: Upload Excel File")
        uploaded_file = st.file_uploader(
            "Upload an Excel file (.xlsx or .xls)",
            type=['xlsx', 'xls'],
            help="Upload your Excel workbook",
            key="excel_upload"
        )
        
        if uploaded_file is not None:
            # Check if this is a new file
            if st.session_state.excel_tool_filename != uploaded_file.name:
                with st.spinner("Loading Excel file..."):
                    try:
                        # Read all sheets
                        excel_file = pd.ExcelFile(uploaded_file)
                        sheet_names = excel_file.sheet_names
                        
                        if not sheet_names:
                            st.error("❌ No sheets found in the Excel file.")
                            return
                        
                        # Load all sheets into session state
                        sheets_data = {}
                        for sheet_name in sheet_names:
                            try:
                                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                                sheets_data[sheet_name] = df
                            except Exception as e:
                                sheets_data[sheet_name] = None
                                st.warning(f"⚠️ Could not read sheet '{sheet_name}': {str(e)}")
                        
                        # Store in session state
                        st.session_state.excel_tool_sheets = sheets_data
                        st.session_state.excel_tool_sheet_names = sheet_names
                        st.session_state.excel_tool_filename = uploaded_file.name
                        
                        st.success(f"✅ Loaded Excel file with {len(sheet_names)} sheet(s)")
                    
                    except Exception as e:
                        st.error(f"❌ Error reading Excel file: {str(e)}")
                        st.session_state.excel_tool_file = None
                        st.session_state.excel_tool_filename = None
                        return
            
            # Use cached data
            sheets_data = st.session_state.excel_tool_sheets
            sheet_names = st.session_state.excel_tool_sheet_names
            
            if not sheet_names:
                return
            
            # Sheet information
            st.subheader("📊 Available Sheets")
            
            # Display sheet info
            sheet_info_data = []
            for sheet_name in sheet_names:
                df = sheets_data.get(sheet_name)
                if df is not None:
                    rows, cols = df.shape
                    status = "✅ Ready"
                    sheet_info_data.append({
                        "Sheet Name": sheet_name,
                        "Rows": rows,
                        "Columns": cols,
                        "Status": status
                    })
                else:
                    sheet_info_data.append({
                        "Sheet Name": sheet_name,
                        "Rows": "N/A",
                        "Columns": "N/A",
                        "Status": "❌ Error"
                    })
            
            info_df = pd.DataFrame(sheet_info_data)
            st.dataframe(info_df, use_container_width=True, hide_index=True)
            
            # Sheet selection
            st.subheader("⚙️ Step 2: Select Sheet and Options")
            
            # Filter out sheets that couldn't be read
            valid_sheets = [name for name in sheet_names if sheets_data.get(name) is not None]
            
            if not valid_sheets:
                st.error("❌ No valid sheets available for conversion.")
                return
            
            selected_sheet = st.selectbox(
                "Select sheet to convert",
                options=valid_sheets,
                key="excel_sheet_select"
            )
            
            # Get selected sheet data
            selected_df = sheets_data[selected_sheet]
            
            # Check if sheet is empty
            if selected_df.empty:
                st.warning(f"⚠️ Sheet '{selected_sheet}' is empty (no data to convert).")
                return
            
            # Show preview
            st.markdown("**Data Preview**")
            st.dataframe(selected_df.head(10), use_container_width=True)
            st.caption(f"Showing first 10 of {len(selected_df)} rows, {len(selected_df.columns)} columns")
            
            # Configuration
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
                    key="excel_separator_choice"
                )
                
                if separator_choice == "Custom":
                    custom_separator = st.text_input(
                        "Enter custom separator",
                        value=",",
                        max_chars=5,
                        key="excel_custom_separator"
                    )
                    separator = custom_separator
                else:
                    separator = separator_options[separator_choice]
            
            with col2:
                # Additional options
                include_index = st.checkbox(
                    "Include row index",
                    value=False,
                    help="Add a column with row numbers",
                    key="excel_include_index"
                )
                
                handle_nan = st.selectbox(
                    "Handle empty cells",
                    options=["Leave empty", "Replace with 'NULL'", "Replace with '0'"],
                    index=0,
                    key="excel_handle_nan"
                )
            
            # Export section
            st.subheader("💾 Step 3: Convert to CSV")
            
            if st.button("🚀 Convert to CSV", type="primary", use_container_width=True, key="excel_convert_btn"):
                try:
                    with st.spinner("Converting to CSV..."):
                        # Prepare dataframe
                        export_df = selected_df.copy()
                        
                        # Handle NaN values
                        if handle_nan == "Replace with 'NULL'":
                            export_df = export_df.fillna('NULL')
                        elif handle_nan == "Replace with '0'":
                            export_df = export_df.fillna(0)
                        
                        # Convert to CSV
                        csv_data = export_df.to_csv(
                            sep=separator,
                            index=include_index,
                            encoding='utf-8'
                        )
                        
                        st.success("✅ CSV file generated successfully!")
                        
                        # Download button
                        safe_sheet_name = selected_sheet.replace(' ', '_').replace('/', '_')
                        file_name = f"{safe_sheet_name}.csv"
                        
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv_data,
                            file_name=file_name,
                            mime="text/csv",
                            use_container_width=True,
                            key="excel_download_btn"
                        )
                        
                        # Summary
                        st.info(f"""
                        **Conversion Summary:**
                        - Sheet: {selected_sheet}
                        - Rows exported: {len(export_df)}
                        - Columns exported: {len(export_df.columns)}
                        - Separator: {repr(separator)}
                        - Index included: {'Yes' if include_index else 'No'}
                        - Empty cells: {handle_nan}
                        """)
                
                except Exception as e:
                    st.error(f"❌ Error converting to CSV: {str(e)}")
                    import traceback
                    with st.expander("View error details"):
                        st.code(traceback.format_exc())
        
        else:
            # Clear session state when no file is uploaded
            if st.session_state.excel_tool_filename is not None:
                st.session_state.excel_tool_file = None
                st.session_state.excel_tool_filename = None
                st.session_state.excel_tool_sheets = {}
                st.session_state.excel_tool_sheet_names = []
