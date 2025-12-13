"""
Base class for all shapefile tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """
    Abstract base class for all shapefile processing tools.
    
    Each tool must implement:
    - name: Display name of the tool
    - description: Short description for the UI
    - icon: Emoji or icon for visual identification
    - render_ui(): Method to render the Streamlit UI
    - process(): Method containing the business logic
    """
    
    def __init__(self):
        """Initialize the tool."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the display name of the tool."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a short description of the tool."""
        pass
    
    @property
    @abstractmethod
    def icon(self) -> str:
        """Return an emoji or icon for the tool."""
        pass
    
    @abstractmethod
    def render_ui(self) -> None:
        """
        Render the Streamlit UI for this tool.
        
        This method should:
        1. Display input widgets (file uploaders, options, etc.)
        2. Provide a process/run button
        3. Handle the processing logic
        4. Display results and download buttons
        """
        pass
    
    def get_card_info(self) -> Dict[str, Any]:
        """
        Return information for displaying this tool as a card on the homepage.
        
        Returns:
            Dict containing name, description, and icon
        """
        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
        }
