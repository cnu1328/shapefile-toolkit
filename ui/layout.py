"""
Reusable UI layout components.
"""

import streamlit as st


def render_tool_card(icon: str, name: str, description: str, tool_key: str) -> None:
    """
    Render a styled tool card.
    
    Args:
        icon: Emoji or icon
        name: Tool name
        description: Tool description
        tool_key: Unique identifier for the tool
    """
    # This is implemented in homepage.py to keep card rendering consistent
    # Import here to avoid circular dependency
    from .homepage import render_tool_card as _render_tool_card
    _render_tool_card(icon, name, description, tool_key)


def render_header(title: str, subtitle: str = "") -> None:
    """
    Render a consistent page header.
    
    Args:
        title: Main title
        subtitle: Optional subtitle
    """
    st.markdown(f"""
        <div style='margin-bottom: 2rem;'>
            <h1 style='color: #1f1f1f; margin-bottom: 0.5rem;'>{title}</h1>
            {f"<p style='color: #666; font-size: 1.1rem;'>{subtitle}</p>" if subtitle else ""}
        </div>
    """, unsafe_allow_html=True)


def render_success_message(message: str) -> None:
    """
    Render a success message with consistent styling.
    
    Args:
        message: Success message to display
    """
    st.success(f"✅ {message}")


def render_error_message(message: str) -> None:
    """
    Render an error message with consistent styling.
    
    Args:
        message: Error message to display
    """
    st.error(f"❌ {message}")


def render_info_box(title: str, content: str, icon: str = "ℹ️") -> None:
    """
    Render an information box.
    
    Args:
        title: Box title
        content: Box content
        icon: Icon to display
    """
    st.markdown(f"""
        <div style='
            background-color: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        '>
            <div style='font-weight: bold; margin-bottom: 0.5rem;'>
                {icon} {title}
            </div>
            <div style='color: #555;'>
                {content}
            </div>
        </div>
    """, unsafe_allow_html=True)


def apply_custom_css() -> None:
    """
    Apply custom CSS styling to the Streamlit app.
    """
    st.markdown("""
        <style>
        /* Main container styling */
        .main {
            padding: 2rem;
        }
        
        /* Button styling */
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        /* File uploader styling */
        .uploadedFile {
            border-radius: 8px;
            border: 2px dashed #ccc;
        }
        
        /* Divider styling */
        hr {
            margin: 2rem 0;
            border: none;
            border-top: 2px solid #e0e0e0;
        }
        
        /* Metric styling */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: bold;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            font-weight: 500;
            border-radius: 8px;
        }
        
        /* Dataframe styling */
        .dataframe {
            border-radius: 8px;
            overflow: hidden;
        }
        
        /* Info/warning/error boxes */
        .stAlert {
            border-radius: 8px;
            border-left-width: 4px;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        /* Header styling */
        h1, h2, h3 {
            color: #1f1f1f;
        }
        
        /* Link styling */
        a {
            color: #2196f3;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        </style>
    """, unsafe_allow_html=True)
