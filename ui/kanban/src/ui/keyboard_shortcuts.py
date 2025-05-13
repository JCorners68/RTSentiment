"""
Keyboard Shortcut System for Evidence CLI.

This module provides a keyboard shortcut system for interactive navigation
and management of evidence items in the terminal interface.
"""
import os
import sys
import logging
import threading
import select
import time
from enum import Enum
from typing import Dict, List, Set, Tuple, Optional, Any, Union, Callable
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.box import ROUNDED
from rich.table import Table
from rich.text import Text

# Configure module logger
logger = logging.getLogger(__name__)


class KeyCode:
    """Key code constants."""
    ESCAPE = b'\x1b'
    ENTER = b'\r'
    SPACE = b' '
    BACKSPACE = b'\x7f'
    TAB = b'\t'
    UP = b'\x1b[A'
    DOWN = b'\x1b[B'
    RIGHT = b'\x1b[C'
    LEFT = b'\x1b[D'
    HOME = b'\x1b[H'
    END = b'\x1b[F'
    PAGE_UP = b'\x1b[5~'
    PAGE_DOWN = b'\x1b[6~'
    DELETE = b'\x1b[3~'
    INSERT = b'\x1b[2~'
    
    # Function keys
    F1 = b'\x1bOP'
    F2 = b'\x1bOQ'
    F3 = b'\x1bOR'
    F4 = b'\x1bOS'
    F5 = b'\x1b[15~'
    F6 = b'\x1b[17~'
    F7 = b'\x1b[18~'
    F8 = b'\x1b[19~'
    F9 = b'\x1b[20~'
    F10 = b'\x1b[21~'
    F11 = b'\x1b[23~'
    F12 = b'\x1b[24~'
    
    # Control key combinations
    CTRL_A = b'\x01'
    CTRL_B = b'\x02'
    CTRL_C = b'\x03'
    CTRL_D = b'\x04'
    CTRL_E = b'\x05'
    CTRL_F = b'\x06'
    CTRL_G = b'\x07'
    CTRL_H = b'\x08'
    CTRL_I = b'\x09'
    CTRL_J = b'\x0a'
    CTRL_K = b'\x0b'
    CTRL_L = b'\x0c'
    CTRL_M = b'\x0d'
    CTRL_N = b'\x0e'
    CTRL_O = b'\x0f'
    CTRL_P = b'\x10'
    CTRL_Q = b'\x11'
    CTRL_R = b'\x12'
    CTRL_S = b'\x13'
    CTRL_T = b'\x14'
    CTRL_U = b'\x15'
    CTRL_V = b'\x16'
    CTRL_W = b'\x17'
    CTRL_X = b'\x18'
    CTRL_Y = b'\x19'
    CTRL_Z = b'\x1a'
    
    @staticmethod
    def to_string(key_code: bytes) -> str:
        """Convert a key code to a human-readable string."""
        # Map key codes to human-readable names
        key_map = {
            KeyCode.ESCAPE: "Esc",
            KeyCode.ENTER: "Enter",
            KeyCode.SPACE: "Space",
            KeyCode.BACKSPACE: "Backspace",
            KeyCode.TAB: "Tab",
            KeyCode.UP: "Up",
            KeyCode.DOWN: "Down",
            KeyCode.RIGHT: "Right",
            KeyCode.LEFT: "Left",
            KeyCode.HOME: "Home",
            KeyCode.END: "End",
            KeyCode.PAGE_UP: "Page Up",
            KeyCode.PAGE_DOWN: "Page Down",
            KeyCode.DELETE: "Delete",
            KeyCode.INSERT: "Insert",
            KeyCode.F1: "F1",
            KeyCode.F2: "F2",
            KeyCode.F3: "F3",
            KeyCode.F4: "F4",
            KeyCode.F5: "F5",
            KeyCode.F6: "F6",
            KeyCode.F7: "F7",
            KeyCode.F8: "F8",
            KeyCode.F9: "F9",
            KeyCode.F10: "F10",
            KeyCode.F11: "F11",
            KeyCode.F12: "F12",
            KeyCode.CTRL_A: "Ctrl+A",
            KeyCode.CTRL_B: "Ctrl+B",
            KeyCode.CTRL_C: "Ctrl+C",
            KeyCode.CTRL_D: "Ctrl+D",
            KeyCode.CTRL_E: "Ctrl+E",
            KeyCode.CTRL_F: "Ctrl+F",
            KeyCode.CTRL_G: "Ctrl+G",
            KeyCode.CTRL_H: "Ctrl+H",
            KeyCode.CTRL_I: "Ctrl+I",
            KeyCode.CTRL_J: "Ctrl+J",
            KeyCode.CTRL_K: "Ctrl+K",
            KeyCode.CTRL_L: "Ctrl+L",
            KeyCode.CTRL_M: "Ctrl+M",
            KeyCode.CTRL_N: "Ctrl+N",
            KeyCode.CTRL_O: "Ctrl+O",
            KeyCode.CTRL_P: "Ctrl+P",
            KeyCode.CTRL_Q: "Ctrl+Q",
            KeyCode.CTRL_R: "Ctrl+R",
            KeyCode.CTRL_S: "Ctrl+S",
            KeyCode.CTRL_T: "Ctrl+T",
            KeyCode.CTRL_U: "Ctrl+U",
            KeyCode.CTRL_V: "Ctrl+V",
            KeyCode.CTRL_W: "Ctrl+W",
            KeyCode.CTRL_X: "Ctrl+X",
            KeyCode.CTRL_Y: "Ctrl+Y",
            KeyCode.CTRL_Z: "Ctrl+Z",
        }
        
        return key_map.get(key_code, f"Unknown ({key_code!r})")


class KeyboardMode(Enum):
    """Keyboard input modes."""
    NORMAL = "normal"
    COMMAND = "command"
    SEARCH = "search"
    HELP = "help"


@dataclass
class KeyBinding:
    """Represents a key binding."""
    key: bytes
    description: str
    callback: Callable
    modes: List[KeyboardMode] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.modes is None:
            self.modes = [KeyboardMode.NORMAL]


class KeyboardManager:
    """
    Manages keyboard shortcuts and input handling.
    
    This class provides a comprehensive keyboard shortcut system for
    interactive navigation and management of evidence items.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the keyboard manager.
        
        Args:
            console: Optional Rich console instance
        """
        self.console = console or Console()
        self.bindings: Dict[bytes, KeyBinding] = {}
        self.mode = KeyboardMode.NORMAL
        self.running = False
        self.input_thread = None
        self.last_keypress = None
        self.input_queue = []
        
        # For the search/command modes
        self.current_input = ""
        self.input_callback = None
        
        # Register default bindings
        self._register_default_bindings()
        
        logger.info("Initialized keyboard manager")
    
    def _register_default_bindings(self) -> None:
        """Register default key bindings."""
        # Navigation keys
        self.register_binding(KeyCode.UP, "Move up", self._handle_up)
        self.register_binding(KeyCode.DOWN, "Move down", self._handle_down)
        self.register_binding(KeyCode.LEFT, "Move left", self._handle_left)
        self.register_binding(KeyCode.RIGHT, "Move right", self._handle_right)
        self.register_binding(KeyCode.PAGE_UP, "Page up", self._handle_page_up)
        self.register_binding(KeyCode.PAGE_DOWN, "Page down", self._handle_page_down)
        self.register_binding(KeyCode.HOME, "Go to first item", self._handle_home)
        self.register_binding(KeyCode.END, "Go to last item", self._handle_end)
        
        # Common actions
        self.register_binding(KeyCode.ENTER, "Select item", self._handle_enter)
        self.register_binding(KeyCode.ESCAPE, "Cancel/Back", self._handle_escape)
        self.register_binding(KeyCode.SPACE, "Toggle selection", self._handle_space)
        
        # Function keys
        self.register_binding(KeyCode.F1, "Show help", self._show_help)
        self.register_binding(KeyCode.F5, "Refresh", self._handle_refresh)
        self.register_binding(KeyCode.F10, "Quit", self._handle_quit)
        
        # Control keys
        self.register_binding(KeyCode.CTRL_C, "Quit", self._handle_quit)
        self.register_binding(KeyCode.CTRL_Q, "Quit", self._handle_quit)
        self.register_binding(KeyCode.CTRL_R, "Refresh", self._handle_refresh)
        self.register_binding(KeyCode.CTRL_F, "Search", self._start_search)
        self.register_binding(KeyCode.CTRL_D, "Details", self._show_details)
        self.register_binding(KeyCode.CTRL_E, "Edit", self._edit_item)
        self.register_binding(KeyCode.CTRL_X, "Delete", self._delete_item)
        self.register_binding(KeyCode.CTRL_H, "Show help", self._show_help)
        self.register_binding(KeyCode.CTRL_S, "Save", self._save_item)
        
        # Command mode
        self.register_binding(b':', "Enter command mode", self._start_command_mode, 
                             modes=[KeyboardMode.NORMAL])
    
    def register_binding(self, 
                       key: bytes, 
                       description: str, 
                       callback: Callable,
                       modes: Optional[List[KeyboardMode]] = None) -> None:
        """
        Register a key binding.
        
        Args:
            key: Key code (see KeyCode class)
            description: Human-readable description
            callback: Function to call when key is pressed
            modes: List of keyboard modes where this binding is active
        """
        binding = KeyBinding(key, description, callback, modes)
        self.bindings[key] = binding
        logger.debug(f"Registered key binding: {KeyCode.to_string(key)} - {description}")
    
    def unregister_binding(self, key: bytes) -> bool:
        """
        Unregister a key binding.
        
        Args:
            key: Key code to unregister
            
        Returns:
            True if unregistered, False if not found
        """
        if key in self.bindings:
            del self.bindings[key]
            logger.debug(f"Unregistered key binding: {KeyCode.to_string(key)}")
            return True
        return False
    
    def get_binding(self, key: bytes) -> Optional[KeyBinding]:
        """
        Get a key binding.
        
        Args:
            key: Key code to look up
            
        Returns:
            KeyBinding or None if not found
        """
        return self.bindings.get(key)
    
    def get_all_bindings(self) -> Dict[bytes, KeyBinding]:
        """
        Get all key bindings.
        
        Returns:
            Dictionary of key bindings
        """
        return self.bindings
    
    def get_bindings_for_mode(self, mode: KeyboardMode) -> Dict[bytes, KeyBinding]:
        """
        Get all key bindings for a specific mode.
        
        Args:
            mode: Keyboard mode
            
        Returns:
            Dictionary of key bindings for the mode
        """
        return {
            key: binding for key, binding in self.bindings.items()
            if mode in binding.modes
        }
    
    def set_mode(self, mode: KeyboardMode) -> None:
        """
        Set the keyboard mode.
        
        Args:
            mode: Keyboard mode to set
        """
        logger.debug(f"Changing keyboard mode: {self.mode.value} -> {mode.value}")
        self.mode = mode
    
    def read_key(self) -> Optional[bytes]:
        """
        Read a single key press.
        
        Returns:
            Key code or None if no key pressed
        """
        # Check if we have queued keys
        if self.input_queue:
            return self.input_queue.pop(0)
            
        # Try to read from stdin
        if not sys.stdin.isatty():
            return None
            
        # Check if there's data available
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if not rlist:
            return None
            
        # Read a key
        key = os.read(sys.stdin.fileno(), 10)
        self.last_keypress = key
        
        # Handle multi-byte key sequences
        if key.startswith(KeyCode.ESCAPE):
            # Read more bytes for escape sequences
            while True:
                rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
                if not rlist:
                    break
                more = os.read(sys.stdin.fileno(), 10)
                key += more
        
        return key
    
    def start_input_thread(self) -> None:
        """Start the input thread."""
        if self.input_thread is not None and self.input_thread.is_alive():
            logger.warning("Input thread is already running")
            return
            
        self.running = True
        
        def input_loop():
            """Input thread function."""
            logger.debug("Input thread started")
            
            try:
                # Save terminal settings
                import termios
                import tty
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                
                try:
                    # Set terminal to raw mode
                    tty.setraw(fd)
                    
                    # Input loop
                    while self.running:
                        # Read a key
                        key = self.read_key()
                        if key:
                            # Process the key
                            self.handle_key(key)
                            
                        # Prevent CPU spinning
                        time.sleep(0.01)
                        
                finally:
                    # Restore terminal settings
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    
            except Exception as e:
                logger.error(f"Error in input thread: {str(e)}")
                
            logger.debug("Input thread stopped")
        
        self.input_thread = threading.Thread(target=input_loop)
        self.input_thread.daemon = True
        self.input_thread.start()
        
        logger.info("Started keyboard input thread")
    
    def stop_input_thread(self) -> None:
        """Stop the input thread."""
        if not self.running:
            logger.warning("Input thread is not running")
            return
            
        self.running = False
        if self.input_thread:
            self.input_thread.join(timeout=1)
            self.input_thread = None
            
        logger.info("Stopped keyboard input thread")
    
    def handle_key(self, key: bytes) -> bool:
        """
        Handle a key press.
        
        Args:
            key: Key code
            
        Returns:
            True if key was handled, False otherwise
        """
        # Handle search/command mode
        if self.mode == KeyboardMode.SEARCH or self.mode == KeyboardMode.COMMAND:
            return self._handle_input_mode(key)
            
        # Check if we have a binding for this key in the current mode
        binding = self.get_binding(key)
        if binding and self.mode in binding.modes:
            # Call the callback
            binding.callback()
            return True
            
        # Unhandled key
        return False
    
    def _handle_input_mode(self, key: bytes) -> bool:
        """
        Handle keys in search/command mode.
        
        Args:
            key: Key code
            
        Returns:
            True if key was handled, False otherwise
        """
        # Check for special keys
        if key == KeyCode.ENTER:
            # Submit input
            if self.input_callback:
                self.input_callback(self.current_input)
            self.current_input = ""
            self.set_mode(KeyboardMode.NORMAL)
            return True
            
        elif key == KeyCode.ESCAPE:
            # Cancel input
            self.current_input = ""
            self.set_mode(KeyboardMode.NORMAL)
            return True
            
        elif key == KeyCode.BACKSPACE:
            # Delete last character
            self.current_input = self.current_input[:-1]
            self._update_input_display()
            return True
            
        elif len(key) == 1 and key.isascii():
            # Add character to input
            self.current_input += key.decode('ascii')
            self._update_input_display()
            return True
            
        # Unhandled key
        return False
    
    def _update_input_display(self) -> None:
        """Update the input display."""
        if self.mode == KeyboardMode.SEARCH:
            prompt = "Search: "
        else:  # COMMAND mode
            prompt = ": "
            
        # Clear the current line and show the prompt
        sys.stdout.write('\r' + prompt + self.current_input + ' ')
        sys.stdout.flush()
    
    def show_help(self) -> None:
        """Show keyboard shortcut help."""
        # Create a table of keyboard shortcuts
        table = Table(title="Keyboard Shortcuts", box=ROUNDED)
        table.add_column("Key", style="bold")
        table.add_column("Description")
        table.add_column("Mode", style="dim")
        
        # Add all bindings relevant to the current mode
        for key, binding in sorted(self.bindings.items(), 
                                  key=lambda x: KeyCode.to_string(x[0])):
            if self.mode in binding.modes:
                table.add_row(
                    KeyCode.to_string(key),
                    binding.description,
                    ", ".join(m.value for m in binding.modes)
                )
        
        # Show the table
        self.console.print()
        self.console.print(table)
        self.console.print()
    
    def read_line(self, prompt: str, callback: Callable[[str], None]) -> None:
        """
        Read a line of input with a prompt.
        
        Args:
            prompt: Prompt to display
            callback: Function to call with the input
        """
        self.current_input = ""
        self.input_callback = callback
        
        # Display prompt
        sys.stdout.write('\r' + prompt)
        sys.stdout.flush()
        
        # Set mode for input handling
        self.set_mode(KeyboardMode.SEARCH)
    
    def read_command(self, callback: Callable[[str], None]) -> None:
        """
        Read a command.
        
        Args:
            callback: Function to call with the command
        """
        self.current_input = ""
        self.input_callback = callback
        
        # Display prompt
        sys.stdout.write('\r: ')
        sys.stdout.flush()
        
        # Set mode for input handling
        self.set_mode(KeyboardMode.COMMAND)
    
    # Default key handlers
    def _handle_up(self) -> None:
        """Handle up key."""
        logger.debug("Up key pressed")
        
    def _handle_down(self) -> None:
        """Handle down key."""
        logger.debug("Down key pressed")
        
    def _handle_left(self) -> None:
        """Handle left key."""
        logger.debug("Left key pressed")
        
    def _handle_right(self) -> None:
        """Handle right key."""
        logger.debug("Right key pressed")
        
    def _handle_page_up(self) -> None:
        """Handle page up key."""
        logger.debug("Page Up key pressed")
        
    def _handle_page_down(self) -> None:
        """Handle page down key."""
        logger.debug("Page Down key pressed")
        
    def _handle_home(self) -> None:
        """Handle home key."""
        logger.debug("Home key pressed")
        
    def _handle_end(self) -> None:
        """Handle end key."""
        logger.debug("End key pressed")
        
    def _handle_enter(self) -> None:
        """Handle enter key."""
        logger.debug("Enter key pressed")
        
    def _handle_escape(self) -> None:
        """Handle escape key."""
        logger.debug("Escape key pressed")
        
    def _handle_space(self) -> None:
        """Handle space key."""
        logger.debug("Space key pressed")
        
    def _handle_refresh(self) -> None:
        """Handle refresh key."""
        logger.debug("Refresh key pressed")
        
    def _handle_quit(self) -> None:
        """Handle quit key."""
        logger.debug("Quit key pressed")
        self.running = False
        
    def _show_help(self) -> None:
        """Show help."""
        logger.debug("Help key pressed")
        self.show_help()
        
    def _start_search(self) -> None:
        """Start search mode."""
        logger.debug("Search key pressed")
        self.read_line("Search: ", lambda query: logger.debug(f"Search: {query}"))
        
    def _start_command_mode(self) -> None:
        """Start command mode."""
        logger.debug("Command mode key pressed")
        self.read_command(lambda cmd: logger.debug(f"Command: {cmd}"))
        
    def _show_details(self) -> None:
        """Show details."""
        logger.debug("Details key pressed")
        
    def _edit_item(self) -> None:
        """Edit item."""
        logger.debug("Edit key pressed")
        
    def _delete_item(self) -> None:
        """Delete item."""
        logger.debug("Delete key pressed")
        
    def _save_item(self) -> None:
        """Save item."""
        logger.debug("Save key pressed")


class NavigationContext:
    """Context for keyboard navigation."""
    
    def __init__(self, 
                items: List[Any],
                keyboard_manager: KeyboardManager,
                console: Optional[Console] = None):
        """
        Initialize the navigation context.
        
        Args:
            items: List of items to navigate
            keyboard_manager: Keyboard manager instance
            console: Optional Rich console instance
        """
        self.items = items
        self.keyboard_manager = keyboard_manager
        self.console = console or Console()
        
        # Navigation state
        self.current_index = 0
        self.selected_indices = set()
        self.page_size = 10
        self.page = 0
        
        # Register custom key handlers
        self._register_handlers()
        
        logger.info("Initialized navigation context")
    
    def _register_handlers(self) -> None:
        """Register custom key handlers."""
        # Override default handlers with our own
        self.keyboard_manager.bindings[KeyCode.UP].callback = self.handle_up
        self.keyboard_manager.bindings[KeyCode.DOWN].callback = self.handle_down
        self.keyboard_manager.bindings[KeyCode.PAGE_UP].callback = self.handle_page_up
        self.keyboard_manager.bindings[KeyCode.PAGE_DOWN].callback = self.handle_page_down
        self.keyboard_manager.bindings[KeyCode.HOME].callback = self.handle_home
        self.keyboard_manager.bindings[KeyCode.END].callback = self.handle_end
        self.keyboard_manager.bindings[KeyCode.SPACE].callback = self.handle_space
        
    def handle_up(self) -> None:
        """Handle up key."""
        if not self.items:
            return
            
        if self.current_index > 0:
            self.current_index -= 1
            
            # Adjust page if necessary
            if self.current_index < self.page * self.page_size:
                self.page = self.current_index // self.page_size
                
            self.refresh_display()
            
    def handle_down(self) -> None:
        """Handle down key."""
        if not self.items:
            return
            
        if self.current_index < len(self.items) - 1:
            self.current_index += 1
            
            # Adjust page if necessary
            if self.current_index >= (self.page + 1) * self.page_size:
                self.page = self.current_index // self.page_size
                
            self.refresh_display()
            
    def handle_page_up(self) -> None:
        """Handle page up key."""
        if not self.items:
            return
            
        if self.page > 0:
            self.page -= 1
            
            # Adjust current index
            self.current_index = self.page * self.page_size
            
            self.refresh_display()
            
    def handle_page_down(self) -> None:
        """Handle page down key."""
        if not self.items:
            return
            
        max_page = (len(self.items) - 1) // self.page_size
        
        if self.page < max_page:
            self.page += 1
            
            # Adjust current index
            self.current_index = min(self.page * self.page_size, len(self.items) - 1)
            
            self.refresh_display()
            
    def handle_home(self) -> None:
        """Handle home key."""
        if not self.items:
            return
            
        self.current_index = 0
        self.page = 0
        
        self.refresh_display()
        
    def handle_end(self) -> None:
        """Handle end key."""
        if not self.items:
            return
            
        self.current_index = len(self.items) - 1
        self.page = (len(self.items) - 1) // self.page_size
        
        self.refresh_display()
        
    def handle_space(self) -> None:
        """Handle space key (toggle selection)."""
        if not self.items:
            return
            
        if self.current_index in self.selected_indices:
            self.selected_indices.remove(self.current_index)
        else:
            self.selected_indices.add(self.current_index)
            
        self.refresh_display()
    
    def refresh_display(self) -> None:
        """Refresh the display."""
        # Override this in subclasses to show the current items
        pass
    
    def get_current_item(self) -> Optional[Any]:
        """
        Get the current item.
        
        Returns:
            Current item or None if no items
        """
        if not self.items:
            return None
            
        return self.items[self.current_index]
    
    def get_selected_items(self) -> List[Any]:
        """
        Get selected items.
        
        Returns:
            List of selected items
        """
        return [self.items[i] for i in self.selected_indices]
    
    def get_visible_items(self) -> List[Any]:
        """
        Get items visible on the current page.
        
        Returns:
            List of visible items
        """
        start = self.page * self.page_size
        end = min(start + self.page_size, len(self.items))
        
        return self.items[start:end]
    
    def get_page_info(self) -> Tuple[int, int, int, int]:
        """
        Get page information.
        
        Returns:
            Tuple of (page, total_pages, first_item, last_item)
        """
        if not self.items:
            return 0, 0, 0, 0
            
        total_pages = (len(self.items) - 1) // self.page_size + 1
        first_item = self.page * self.page_size + 1
        last_item = min((self.page + 1) * self.page_size, len(self.items))
        
        return self.page + 1, total_pages, first_item, last_item


# Helper function to run an interactive keyboard session
def run_interactive_session(keyboard_manager: KeyboardManager) -> None:
    """
    Run an interactive keyboard session.
    
    Args:
        keyboard_manager: Keyboard manager instance
    """
    # Start the input thread
    keyboard_manager.start_input_thread()
    
    try:
        # Show help
        keyboard_manager.show_help()
        
        # Loop until quit
        while keyboard_manager.running:
            time.sleep(0.1)
            
    finally:
        # Stop the input thread
        keyboard_manager.stop_input_thread()
