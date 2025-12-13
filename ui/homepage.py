"""
Homepage/dashboard layout for the Shapefile Toolkit.
"""

import streamlit as st
from typing import Dict, List, Any


def render_homepage(tools: List[Any]) -> None:
    """
    Render the homepage dashboard with tool cards.
    
    Args:
        tools: List of tool instances
    """
    # Hero section
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='font-size: 3rem; margin-bottom: 0.5rem;'>
                🗺️ Shapefile Toolkit
            </h1>
            <p style='font-size: 1.2rem; color: #666; margin-bottom: 2rem;'>
                GIS Utilities in Your Browser
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Introduction
    st.markdown("""
        Welcome to the **Shapefile Toolkit** – a powerful web application for performing common 
        shapefile operations without the need for desktop GIS software. Upload your shapefiles, 
        choose an operation, and download the results instantly.
        
        All processing happens in your browser session. Your data is never stored on our servers.
    """)
    
    st.divider()
    
    # Tools section
    st.subheader("🛠️ Available Tools")
    st.markdown("Select a tool below to get started:")
    
    # Create tool cards in a grid
    cols_per_row = 2
    
    for i in range(0, len(tools), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, col in enumerate(cols):
            tool_idx = i + j
            if tool_idx < len(tools):
                tool = tools[tool_idx]
                card_info = tool.get_card_info()
                
                with col:
                    render_tool_card(
                        icon=card_info['icon'],
                        name=card_info['name'],
                        description=card_info['description'],
                        tool_key=f"tool_{tool_idx}"
                    )
    
    # Footer
    st.divider()
    
    st.markdown("""
        <div style='text-align: center; padding: 2rem 0; color: #666;'>
            <p>
                <strong>Shapefile Toolkit</strong> v1.0.0<br>
                Made with ❤️ by <strong>Srinivas Dharpally</strong>
            </p>
            <p style='font-size: 0.9rem;'>
                💡 Tip: All tools support ZIP files containing shapefile components (.shp, .shx, .dbf, .prj)
            </p>
        </div>
    """, unsafe_allow_html=True)


def render_tool_card(icon: str, name: str, description: str, tool_key: str) -> None:
    """
    Render a tool card with icon, name, description, and action button.
    
    Args:
        icon: Emoji or icon for the tool
        name: Tool name
        description: Tool description
        tool_key: Unique key for the tool (used for session state)
    """
    # Card container with styling
    st.markdown(f"""
        <div style='
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 200px;
            display: flex;
            flex-direction: column;
        '>
            <div style='font-size: 3rem; margin-bottom: 0.5rem;'>{icon}</div>
            <h3 style='margin: 0.5rem 0; color: #1f1f1f;'>{name}</h3>
            <p style='color: #555; flex-grow: 1; margin-bottom: 1rem;'>{description}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Button below the card
    if st.button(f"Open {name}", key=f"btn_{tool_key}", use_container_width=True, type="primary"):
        st.session_state.selected_tool = tool_key
        st.rerun()
