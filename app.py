"""
Shapefile Toolkit - Main Streamlit Application

A production-ready web application for performing common shapefile operations.
"""

import streamlit as st
from typing import Dict, Any

# Import tools
from tools import (
    ShapefileToCSVTool,
    MergeShapefilesTool,
    AddShapefilesTool,
    ReprojectShapefileTool,
)

# Import UI components
from ui.homepage import render_homepage
from ui.layout import apply_custom_css


# ============================================================================
# Configuration
# ============================================================================

st.set_page_config(
    page_title="Shapefile Toolkit",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': """
            # Shapefile Toolkit
            
            A powerful web application for performing common shapefile operations.
            
            **Version:** 1.0.0
            
            Built with Streamlit, GeoPandas, and ❤️
        """
    }
)


# ============================================================================
# Tool Registry
# ============================================================================

class ToolRegistry:
    """
    Singleton registry for managing tool instances.
    """
    _instance = None
    _tools = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._tools = {}
        return cls._instance
    
    def register_tool(self, key: str, tool: Any) -> None:
        """Register a tool instance."""
        self._tools[key] = tool
    
    def get_tool(self, key: str) -> Any:
        """Get a tool instance by key."""
        return self._tools.get(key)
    
    def get_all_tools(self) -> Dict[str, Any]:
        """Get all registered tools."""
        return self._tools
    
    def get_tools_list(self) -> list:
        """Get list of all tool instances."""
        return list(self._tools.values())


def initialize_tools() -> ToolRegistry:
    """
    Initialize and register all tools.
    
    Returns:
        ToolRegistry instance with all tools registered
    """
    registry = ToolRegistry()
    
    # Register all tools
    registry.register_tool("tool_0", ShapefileToCSVTool())
    registry.register_tool("tool_1", MergeShapefilesTool())
    registry.register_tool("tool_2", AddShapefilesTool())
    registry.register_tool("tool_3", ReprojectShapefileTool())
    
    # Note: TemplateTool is not registered as it's just a template
    # To add it, uncomment the following line:
    # from tools.template_tool import TemplateTool
    # registry.register_tool("tool_4", TemplateTool())
    
    return registry


# ============================================================================
# Session State Management
# ============================================================================

def initialize_session_state() -> None:
    """Initialize session state variables."""
    if 'selected_tool' not in st.session_state:
        st.session_state.selected_tool = None


# ============================================================================
# Sidebar Navigation
# ============================================================================

def render_sidebar(registry: ToolRegistry) -> None:
    """
    Render the sidebar navigation.
    
    Args:
        registry: ToolRegistry instance
    """
    with st.sidebar:
        st.markdown("## 🗺️ Shapefile Toolkit")
        st.markdown("---")
        
        # Home button
        if st.button("🏠 Home", use_container_width=True, type="secondary"):
            st.session_state.selected_tool = None
            st.rerun()
        
        st.markdown("### 🛠️ Tools")
        
        # Tool navigation buttons
        tools = registry.get_all_tools()
        for key, tool in tools.items():
            card_info = tool.get_card_info()
            button_label = f"{card_info['icon']} {card_info['name']}"
            
            # Highlight selected tool
            button_type = "primary" if st.session_state.selected_tool == key else "secondary"
            
            if st.button(button_label, key=f"nav_{key}", use_container_width=True, type=button_type):
                st.session_state.selected_tool = key
                st.rerun()
        
        st.markdown("---")
        
        # Info section
        st.markdown("""
            ### ℹ️ About
            
            **Shapefile Toolkit** helps you perform common GIS operations on shapefiles directly in your browser.
            
            **Features:**
            - 📊 Export to CSV
            - 🔗 Merge shapefiles
            - ➕ Combine shapefiles
            - 🌐 Reproject CRS
            
            **Privacy:** All processing happens in your browser. Your data is never stored.
        """)
        
        st.markdown("---")
        st.caption("Version 1.0.0")


# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main application entry point."""
    
    # Apply custom CSS
    apply_custom_css()
    
    # Initialize session state
    initialize_session_state()
    
    # Initialize tools
    registry = initialize_tools()
    
    # Render sidebar
    render_sidebar(registry)
    
    # Main content area
    selected_tool_key = st.session_state.selected_tool
    
    if selected_tool_key is None:
        # Show homepage
        render_homepage(registry.get_tools_list())
    else:
        # Show selected tool
        tool = registry.get_tool(selected_tool_key)
        
        if tool is not None:
            # Render the tool's UI
            tool.render_ui()
            
            # Back to home button at the bottom
            st.divider()
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("⬅️ Back to Home", use_container_width=True):
                    st.session_state.selected_tool = None
                    st.rerun()
        else:
            st.error("Tool not found!")
            if st.button("Go to Home"):
                st.session_state.selected_tool = None
                st.rerun()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    main()
