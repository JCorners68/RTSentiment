"""
Keyboard Navigation Extensions for Evidence UI.

This module extends the keyboard shortcut system to support
evidence-specific navigation and interaction patterns.
"""
import logging
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from rich.console import Console
from rich.text import Text

from .keyboard_shortcuts import KeyboardManager, NavigationContext, KeyCode, KeyboardMode
from .display import console, print_error, print_success, print_info, print_warning
from ..models.evidence_schema import EvidenceSchema

# Configure module logger
logger = logging.getLogger(__name__)


class EvidenceNavigationContext(NavigationContext):
    """
    Navigation context for evidence items.
    
    This class extends the basic navigation context with
    evidence-specific functionality and keyboard shortcuts.
    """
    
    def __init__(self, 
                evidence_items: List[EvidenceSchema],
                keyboard_manager: KeyboardManager,
                console: Optional[Console] = None,
                on_select: Optional[Callable[[EvidenceSchema], None]] = None,
                on_compare: Optional[Callable[[List[EvidenceSchema]], None]] = None):
        """
        Initialize the evidence navigation context.
        
        Args:
            evidence_items: List of evidence items to navigate
            keyboard_manager: Keyboard manager instance
            console: Optional console for display
            on_select: Callback for when an item is selected
            on_compare: Callback for when items are compared
        """
        super().__init__(evidence_items, keyboard_manager, console)
        
        # Additional evidence-specific state
        self.filter_category = None
        self.filter_text = None
        self.on_select = on_select
        self.on_compare = on_compare
        self.comparison_selections: Set[int] = set()
        
        # Extend keyboard bindings
        self._register_evidence_bindings()
        
        logger.info("Initialized evidence navigation context")

    def _register_evidence_bindings(self) -> None:
        """Register evidence-specific keyboard bindings."""
        # Category filtering
        self.keyboard_manager.register_binding(KeyCode.CTRL_F, "Search in title/description", self._start_text_search)
        self.keyboard_manager.register_binding(KeyCode.CTRL_C, "Filter by category", self._start_category_filter)
        
        # Detailed view
        self.keyboard_manager.register_binding(KeyCode.CTRL_D, "View evidence details", self._show_evidence_details)
        
        # Edit mode
        self.keyboard_manager.register_binding(KeyCode.CTRL_E, "Edit evidence", self._edit_evidence)
        
        # Comparison mode
        self.keyboard_manager.register_binding(KeyCode.CTRL_M, "Mark for comparison", self._toggle_comparison_mark)
        self.keyboard_manager.register_binding(KeyCode.CTRL_V, "Compare marked evidence", self._compare_evidence)
        
        # High contrast and accessibility
        self.keyboard_manager.register_binding(KeyCode.CTRL_H, "Toggle high contrast", self._toggle_high_contrast)
        self.keyboard_manager.register_binding(KeyCode.CTRL_A, "Toggle screen reader mode", self._toggle_screen_reader)
        
        # Show evidence relationships
        self.keyboard_manager.register_binding(KeyCode.CTRL_R, "Show relationships", self._show_relationships)
        
    def handle_enter(self) -> None:
        """Handle Enter key (select current evidence)."""
        if not self.items:
            return
            
        current_evidence = self.get_current_item()
        if self.on_select and current_evidence:
            self.on_select(current_evidence)
            
    def _start_text_search(self) -> None:
        """Start text search mode."""
        logger.debug("Starting text search")
        
        def apply_text_filter(query: str) -> None:
            self.filter_text = query.strip() if query.strip() else None
            self._apply_filters()
            
        self.keyboard_manager.read_line("Search: ", apply_text_filter)
        
    def _start_category_filter(self) -> None:
        """Start category filter mode."""
        logger.debug("Starting category filter")
        
        def apply_category_filter(category: str) -> None:
            self.filter_category = category.strip() if category.strip() else None
            self._apply_filters()
        
        # Get available categories
        categories = set()
        for evidence in self.items:
            categories.add(evidence.category.value)
        category_list = ", ".join(sorted(categories))
        
        self.keyboard_manager.read_line(f"Filter by category ({category_list}): ", apply_category_filter)
        
    def _show_evidence_details(self) -> None:
        """Show detailed view of current evidence."""
        if not self.items:
            return
            
        current_evidence = self.get_current_item()
        if current_evidence:
            from .display import print_evidence_details
            print_evidence_details(current_evidence.to_dict())
            
    def _edit_evidence(self) -> None:
        """Enter edit mode for current evidence."""
        if not self.items:
            return
            
        current_evidence = self.get_current_item()
        if current_evidence:
            print_info(f"Edit functionality would be implemented for evidence {current_evidence.id}")
            # In a real implementation, this would launch an editor interface
            
    def _toggle_comparison_mark(self) -> None:
        """Mark/unmark current evidence for comparison."""
        if not self.items:
            return
            
        if self.current_index in self.comparison_selections:
            self.comparison_selections.remove(self.current_index)
            print_info("Removed from comparison")
        else:
            self.comparison_selections.add(self.current_index)
            print_info("Added to comparison")
            
        self.refresh_display()
        
    def _compare_evidence(self) -> None:
        """Compare marked evidence items."""
        if len(self.comparison_selections) < 2:
            print_warning("Select at least 2 items for comparison (use Ctrl+M to mark items)")
            return
            
        # Get selected evidence items
        selected_evidence = [self.items[i] for i in self.comparison_selections]
        
        if self.on_compare:
            self.on_compare(selected_evidence)
        else:
            print_info(f"Would compare {len(selected_evidence)} evidence items")
            # In a real implementation, this would show a comparison UI
            
    def _toggle_high_contrast(self) -> None:
        """Toggle high contrast mode."""
        # This would be implemented to adjust the display
        print_info("High contrast mode toggled")
        self.refresh_display()
        
    def _toggle_screen_reader(self) -> None:
        """Toggle screen reader compatibility mode."""
        # This would be implemented to adjust the display
        print_info("Screen reader compatibility mode toggled")
        self.refresh_display()
        
    def _show_relationships(self) -> None:
        """Show relationships for current evidence."""
        if not self.items:
            return
            
        current_evidence = self.get_current_item()
        if current_evidence:
            # This would link to the relationship visualization
            print_info(f"Showing relationships for {current_evidence.id}")
            # In a real implementation, this would show the relationship graph
        
    def _apply_filters(self) -> None:
        """Apply the current filters to the evidence list."""
        # Reset the page and index
        self.page = 0
        self.current_index = 0
        
        # If we have filters, we'd apply them and update the visible list
        # This is a simplified example
        print_info("Filters applied")
        
        # In a real implementation, this would filter the evidence list
        # and update the display
        self.refresh_display()

    def refresh_display(self) -> None:
        """Refresh the evidence display."""
        # In a real implementation, this would redraw the evidence list
        print_info("Display refreshed")
        
        # For demonstration purposes, show current state
        self.console.print()
        if not self.items:
            self.console.print("[italic]No evidence items to display[/italic]")
            return
            
        current = self.get_current_item()
        if current:
            self.console.print(f"Current item: [bold]{current.id}[/bold] - {current.title}")
            
        if self.comparison_selections:
            items = [self.items[i].id for i in self.comparison_selections]
            self.console.print(f"Comparison selections: {', '.join(items)}")
            
        # Additional accessibility and filtering information
        filters = []
        if self.filter_category:
            filters.append(f"Category: {self.filter_category}")
        if self.filter_text:
            filters.append(f"Text: {self.filter_text}")
            
        if filters:
            self.console.print(f"Active filters: {', '.join(filters)}")


class EvidenceComparisonDisplay:
    """
    Evidence comparison display functionality.
    
    This class provides a rich comparison view of multiple evidence items,
    highlighting differences and similarities.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the comparison display.
        
        Args:
            console: Console for display
        """
        self.console = console or Console()
        logger.info("Initialized evidence comparison display")
        
    def compare_evidence(self, evidence_items: List[EvidenceSchema]) -> None:
        """
        Display a comparison of multiple evidence items.
        
        Args:
            evidence_items: List of evidence items to compare
        """
        if not evidence_items or len(evidence_items) < 2:
            self.console.print("[italic]Need at least two evidence items to compare[/italic]")
            return
            
        self.console.print(f"[bold]Comparing {len(evidence_items)} Evidence Items[/bold]")
        self.console.print()
        
        # Create a comparison table
        from rich.table import Table
        
        table = Table(box=None)
        table.add_column("Field", style="bold")
        
        # Add columns for each evidence item
        for evidence in evidence_items:
            table.add_column(f"{evidence.id}: {evidence.title[:20]}...")
        
        # Fields to compare
        fields_to_compare = [
            ("Category", lambda e: e.category.value),
            ("Relevance", lambda e: e.relevance_score.value),
            ("Source", lambda e: e.source),
            ("Date Collected", lambda e: e.date_collected.strftime("%Y-%m-%d")),
            ("Tags", lambda e: ", ".join(e.tags)),
            ("Attachments", lambda e: str(len(e.attachments))),
            ("Related Items", lambda e: str(len(e.related_evidence_ids)))
        ]
        
        # Add rows for each field
        for field_name, field_getter in fields_to_compare:
            row = [field_name]
            
            # Get values for each evidence item
            values = [field_getter(e) for e in evidence_items]
            
            # Check if values are different
            all_same = all(v == values[0] for v in values)
            
            for value in values:
                if all_same:
                    row.append(str(value))
                else:
                    row.append(f"[bold]{str(value)}[/bold]")
            
            table.add_row(*row)
            
        # Add description row (abbreviated)
        row = ["Description"]
        for evidence in evidence_items:
            desc = evidence.description
            if len(desc) > 100:
                desc = desc[:97] + "..."
            row.append(desc)
        table.add_row(*row)
        
        # Display the table
        self.console.print(table)
        self.console.print()
        self.console.print("[italic]Press any key to return to evidence list[/italic]")