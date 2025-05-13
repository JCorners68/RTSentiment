"""
Accessibility Utilities for Evidence UI.

This module provides accessibility features for the Evidence Management System,
including high contrast mode, screen reader compatibility, and keyboard navigation.
"""
import logging
from typing import Dict, List, Optional, Any, Union
from rich.console import Console
from rich.theme import Theme
from rich.style import Style
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from .display import console as default_console

# Configure module logger
logger = logging.getLogger(__name__)


class AccessibilityManager:
    """
    Manager for accessibility settings and utilities.
    
    This class provides functionality for switching between different
    accessibility modes and provides adapted rendering utilities.
    """
    
    def __init__(self, 
                 high_contrast: bool = False, 
                 screen_reader_mode: bool = False,
                 console: Optional[Console] = None):
        """
        Initialize the accessibility manager.
        
        Args:
            high_contrast: Whether to use high contrast mode
            screen_reader_mode: Whether to use screen reader compatible output
            console: Optional console instance to use
        """
        self.high_contrast = high_contrast
        self.screen_reader_mode = screen_reader_mode
        self.console = console or default_console
        
        # Define color themes for different modes
        self.themes = {
            "standard": Theme({
                "primary": "#4B8BBE",
                "success": "#69A85C",
                "warning": "#F7C325",
                "error": "#D35E60",
                "info": "#61D2DC",
                "evidence.requirement": "#4B8BBE", 
                "evidence.bug": "#D35E60",
                "evidence.design": "#61D2DC",
                "evidence.test": "#8E8EA0",
                "evidence.result": "#69A85C",
                "evidence.reference": "#F7C325",
                "evidence.decision": "#9575CD",
            }),
            "high_contrast": Theme({
                "primary": "bright_white on blue",
                "success": "bright_white on green",
                "warning": "black on yellow",
                "error": "bright_white on red",
                "info": "bright_white on cyan",
                "evidence.requirement": "bright_white on blue", 
                "evidence.bug": "bright_white on red",
                "evidence.design": "black on cyan",
                "evidence.test": "black on white",
                "evidence.result": "black on green",
                "evidence.reference": "black on yellow",
                "evidence.decision": "bright_white on magenta",
            })
        }
        
        # Apply the initial theme
        self._apply_theme()
        
        logger.info(f"Initialized accessibility manager (high_contrast={high_contrast}, screen_reader_mode={screen_reader_mode})")
    
    def _apply_theme(self) -> None:
        """Apply the appropriate theme based on current settings."""
        theme_key = "high_contrast" if self.high_contrast else "standard"
        
        # In a real implementation, this would update the console theme
        # Since we can't modify the existing console's theme directly,
        # we're just logging the change
        logger.info(f"Applied {theme_key} theme")
        
    def toggle_high_contrast(self) -> bool:
        """
        Toggle high contrast mode.
        
        Returns:
            New high contrast mode state
        """
        self.high_contrast = not self.high_contrast
        self._apply_theme()
        logger.info(f"Toggled high contrast mode: {self.high_contrast}")
        return self.high_contrast
    
    def toggle_screen_reader(self) -> bool:
        """
        Toggle screen reader compatibility mode.
        
        Returns:
            New screen reader mode state
        """
        self.screen_reader_mode = not self.screen_reader_mode
        logger.info(f"Toggled screen reader mode: {self.screen_reader_mode}")
        return self.screen_reader_mode
    
    def get_adapted_text(self, content: Union[str, Text], style: Optional[str] = None) -> Text:
        """
        Get text adapted for current accessibility settings.
        
        Args:
            content: Content to adapt
            style: Optional style to apply
            
        Returns:
            Adapted rich Text object
        """
        if isinstance(content, str):
            text = Text(content)
        else:
            text = content
            
        if style:
            # In high contrast mode, we might override certain styles
            if self.high_contrast and style in self.themes["high_contrast"].styles:
                text.stylize(self.themes["high_contrast"].styles[style])
            elif style in self.themes["standard"].styles:
                text.stylize(self.themes["standard"].styles[style])
                
        return text
    
    def print_adapted(self, content: Union[str, Text], style: Optional[str] = None) -> None:
        """
        Print content adapted for current accessibility settings.
        
        Args:
            content: Content to print
            style: Optional style to apply
        """
        text = self.get_adapted_text(content, style)
        
        # For screen readers, we might want to simplify certain formatting
        if self.screen_reader_mode:
            # Strip out certain formatting markers that screen readers might have trouble with
            # and replace with more descriptive text
            # This is a simplified example
            self.console.print(text)
        else:
            self.console.print(text)
    
    def create_accessible_table(self, title: Optional[str] = None) -> Table:
        """
        Create a table adapted for accessibility.
        
        Args:
            title: Optional table title
            
        Returns:
            Rich Table object with appropriate accessibility settings
        """
        # Use heavier borders and clearer spacing in high contrast mode
        box = "heavy" if self.high_contrast else "rounded"
        
        table = Table(title=title, box=box)
        
        # For screen readers, we might want to add additional context
        if self.screen_reader_mode and title:
            table.caption = f"End of {title} table"
            
        return table
    

class HighContrastMode:
    """
    Context manager for temporarily enabling high contrast mode.
    
    This allows code to enable high contrast mode for a specific
    block of code and automatically restore the previous setting
    when done.
    """
    
    def __init__(self, manager: AccessibilityManager, enabled: bool = True):
        """
        Initialize the context manager.
        
        Args:
            manager: Accessibility manager to use
            enabled: Whether to enable high contrast mode
        """
        self.manager = manager
        self.enabled = enabled
        self.previous_state = manager.high_contrast
        
    def __enter__(self) -> 'HighContrastMode':
        """
        Enter the context, enabling high contrast mode.
        
        Returns:
            Self for context variable
        """
        self.previous_state = self.manager.high_contrast
        self.manager.high_contrast = self.enabled
        self.manager._apply_theme()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context, restoring previous state."""
        self.manager.high_contrast = self.previous_state
        self.manager._apply_theme()
        

class ScreenReaderMode:
    """
    Context manager for temporarily enabling screen reader mode.
    
    This allows code to enable screen reader mode for a specific
    block of code and automatically restore the previous setting
    when done.
    """
    
    def __init__(self, manager: AccessibilityManager, enabled: bool = True):
        """
        Initialize the context manager.
        
        Args:
            manager: Accessibility manager to use
            enabled: Whether to enable screen reader mode
        """
        self.manager = manager
        self.enabled = enabled
        self.previous_state = manager.screen_reader_mode
        
    def __enter__(self) -> 'ScreenReaderMode':
        """
        Enter the context, enabling screen reader mode.
        
        Returns:
            Self for context variable
        """
        self.previous_state = self.manager.screen_reader_mode
        self.manager.screen_reader_mode = self.enabled
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context, restoring previous state."""
        self.manager.screen_reader_mode = self.previous_state


# Create a default accessibility manager for importing
accessibility_manager = AccessibilityManager()