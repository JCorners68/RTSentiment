"""
Evidence Comparison Display for the Kanban CLI.

This module provides functionality for comparing multiple evidence items
side by side, highlighting differences and similarities.
"""
import logging
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import Box, ROUNDED, HEAVY, MINIMAL
from rich.columns import Columns
from rich.layout import Layout
from rich.rule import Rule
from rich.syntax import Syntax

from ..models.evidence_schema import EvidenceSchema, EvidenceCategory, EvidenceRelevance
from .display import console
from .accessibility import accessibility_manager, HighContrastMode, ScreenReaderMode

# Configure module logger
logger = logging.getLogger(__name__)


class EvidenceComparison:
    """
    Evidence comparison utility for detailed side-by-side comparison.
    
    This class provides functionality to compare multiple evidence items
    and highlight their differences and similarities.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the evidence comparison.
        
        Args:
            console: Optional console for display
        """
        self.console = console or Console()
        
        # Fields to compare, in display order
        self.comparison_fields = [
            ("ID", lambda e: e.id),
            ("Title", lambda e: e.title),
            ("Category", lambda e: e.category.value),
            ("Subcategory", lambda e: e.subcategory),
            ("Date Collected", lambda e: e.date_collected.strftime('%Y-%m-%d %H:%M')),
            ("Relevance", lambda e: e.relevance_score.value),
            ("Tags", lambda e: ", ".join(e.tags) if e.tags else "None"),
            ("Source", lambda e: e.source),
            ("Attachments", lambda e: f"{len(e.attachments)} attachments"),
            ("Related Items", lambda e: f"{len(e.related_evidence_ids)} related items"),
            ("Created", lambda e: e.created_at.strftime('%Y-%m-%d %H:%M')),
            ("Updated", lambda e: e.updated_at.strftime('%Y-%m-%d %H:%M')),
        ]
        
        logger.info("Initialized evidence comparison component")
    
    def compare(self, 
               evidence_items: List[EvidenceSchema], 
               highlight_differences: bool = True,
               show_description: bool = True) -> None:
        """
        Compare multiple evidence items and display results.
        
        Args:
            evidence_items: List of evidence items to compare
            highlight_differences: Whether to highlight differences
            show_description: Whether to include descriptions
        """
        if not evidence_items:
            self.console.print("[italic]No evidence items to compare[/italic]")
            return
            
        if len(evidence_items) == 1:
            self.console.print("[italic]Need multiple items for comparison[/italic]")
            return
        
        # Create comparison table
        table = Table(
            title=f"Comparison of {len(evidence_items)} Evidence Items",
            box=HEAVY if accessibility_manager.high_contrast else ROUNDED,
            expand=True
        )
        
        # Add field column
        table.add_column("Field", style="bold")
        
        # Add columns for each evidence item
        for evidence in evidence_items:
            table.add_column(f"{evidence.id}", style="bold blue")
        
        # Add rows for each field
        for field_name, field_getter in self.comparison_fields:
            row = [field_name]
            
            # Extract field values
            values = [field_getter(e) for e in evidence_items]
            
            # Check if values differ
            all_same = len(set(str(v) for v in values)) == 1
            
            # Add value for each evidence item
            for value in values:
                if highlight_differences and not all_same:
                    # Highlight differences
                    if accessibility_manager.high_contrast:
                        row.append(f"[black on bright_yellow]{value}[/black on bright_yellow]")
                    else:
                        row.append(f"[bold yellow]{value}[/bold yellow]")
                else:
                    row.append(str(value))
            
            table.add_row(*row)
        
        # Display the table
        self.console.print()
        self.console.print(table)
        self.console.print()
        
        # Show descriptions if requested
        if show_description:
            self._show_description_comparison(evidence_items)
    
    def _show_description_comparison(self, evidence_items: List[EvidenceSchema]) -> None:
        """
        Show a comparison of descriptions.
        
        Args:
            evidence_items: List of evidence items to compare
        """
        self.console.print("[bold]Description Comparison:[/bold]")
        self.console.print()
        
        # Create columns for description panels
        panels = []
        
        for evidence in evidence_items:
            # Truncate description if very long
            description = evidence.description
            if len(description) > 500:
                description = description[:497] + "..."
                
            # Create a panel for each description
            panel = Panel(
                description,
                title=f"{evidence.id}",
                border_style="blue",
                box=HEAVY if accessibility_manager.high_contrast else ROUNDED,
                width=60
            )
            panels.append(panel)
        
        # For screen reader mode, display sequentially
        if accessibility_manager.screen_reader_mode:
            for panel in panels:
                self.console.print(panel)
                self.console.print()
        else:
            # Display in columns for side-by-side comparison
            try:
                self.console.print(Columns(panels))
            except:
                # Fallback if columns don't fit
                for panel in panels:
                    self.console.print(panel)
                    self.console.print()
    
    def compare_fields(self, 
                      evidence_items: List[EvidenceSchema], 
                      field_name: str) -> None:
        """
        Compare a specific field across evidence items.
        
        Args:
            evidence_items: List of evidence items to compare
            field_name: Name of the field to compare in detail
        """
        if not evidence_items:
            return
            
        # Find the appropriate field getter
        field_getter = None
        display_name = None
        
        for name, getter in self.comparison_fields:
            if name.lower() == field_name.lower():
                field_getter = getter
                display_name = name
                break
                
        if not field_getter:
            # Special case for description
            if field_name.lower() == "description":
                self._show_description_comparison(evidence_items)
                return
                
            # Not a standard field
            self.console.print(f"[italic]Field '{field_name}' not found for comparison[/italic]")
            return
        
        # Get values
        values = [(e.id, field_getter(e)) for e in evidence_items]
        
        # Display comparison
        self.console.print()
        self.console.print(f"[bold]Comparing {display_name}:[/bold]")
        self.console.print()
        
        # Handle different formats based on field name
        if display_name in ["Tags", "Related Items"]:
            self._compare_list_field(values, display_name)
        elif display_name in ["Date Collected", "Created", "Updated"]:
            self._compare_date_field(values, display_name)
        else:
            # Simple text comparison
            self._compare_text_field(values, display_name)
    
    def _compare_list_field(self, values: List[Tuple[str, Any]], field_name: str) -> None:
        """
        Compare a field that contains lists.
        
        Args:
            values: List of (evidence_id, field_value) tuples
            field_name: Name of the field being compared
        """
        # Extract lists from values
        lists = []
        for evidence_id, value in values:
            if field_name == "Tags":
                # Tags are already a list
                items = value.split(", ") if isinstance(value, str) else []
                lists.append((evidence_id, items))
            elif field_name == "Related Items":
                # Extract just the count number
                count = int(value.split()[0]) if isinstance(value, str) else 0
                lists.append((evidence_id, [f"Item {i+1}" for i in range(count)]))
        
        # Find unique items across all lists
        all_items = set()
        for _, items in lists:
            all_items.update(items)
        
        # Create comparison table
        table = Table(
            title=f"Comparison of {field_name}",
            box=HEAVY if accessibility_manager.high_contrast else ROUNDED
        )
        
        # Add columns
        table.add_column("Item", style="bold")
        for evidence_id, _ in lists:
            table.add_column(evidence_id, style="bold blue")
        
        # Add rows for each unique item
        for item in sorted(all_items):
            row = [item]
            for evidence_id, items in lists:
                if item in items:
                    row.append("✓")
                else:
                    row.append("")
            table.add_row(*row)
        
        self.console.print(table)
    
    def _compare_date_field(self, values: List[Tuple[str, Any]], field_name: str) -> None:
        """
        Compare a date field with timeline visualization.
        
        Args:
            values: List of (evidence_id, field_value) tuples
            field_name: Name of the field being compared
        """
        # Parse dates
        try:
            dates = []
            for evidence_id, date_str in values:
                try:
                    # Try to parse the date from the string
                    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                    dates.append((evidence_id, date))
                except:
                    # If parsing fails, skip this item
                    self.console.print(f"[italic]Could not parse date for {evidence_id}[/italic]")
            
            # If we couldn't parse any dates, just show the raw values
            if not dates:
                self._compare_text_field(values, field_name)
                return
                
            # Sort by date
            dates.sort(key=lambda x: x[1])
            
            # Calculate date range
            earliest = min(dates, key=lambda x: x[1])[1]
            latest = max(dates, key=lambda x: x[1])[1]
            
            # Display a simple timeline
            self.console.print(f"Timeline from {earliest.strftime('%Y-%m-%d %H:%M')} to {latest.strftime('%Y-%m-%d %H:%M')}")
            self.console.print()
            
            # Create a simple visual timeline
            timeline_width = 40
            
            for evidence_id, date in dates:
                # Calculate position on timeline
                if earliest == latest:
                    position = timeline_width // 2
                else:
                    delta = (date - earliest).total_seconds()
                    total_seconds = (latest - earliest).total_seconds()
                    position = int((delta / total_seconds) * timeline_width)
                
                # Create the timeline bar
                bar = "─" * position + "●" + "─" * (timeline_width - position)
                self.console.print(f"{evidence_id}: {date.strftime('%Y-%m-%d %H:%M')} [{bar}]")
            
        except Exception as e:
            # Fallback to simple text comparison if timeline fails
            logger.error(f"Error creating timeline: {str(e)}")
            self._compare_text_field(values, field_name)
    
    def _compare_text_field(self, values: List[Tuple[str, Any]], field_name: str) -> None:
        """
        Compare a simple text field.
        
        Args:
            values: List of (evidence_id, field_value) tuples
            field_name: Name of the field being compared
        """
        # Check if all values are the same
        all_values = [str(val) for _, val in values]
        all_same = len(set(all_values)) == 1
        
        if all_same:
            self.console.print(f"All evidence items have the same value: {all_values[0]}")
            return
        
        # Display each value
        for evidence_id, value in values:
            self.console.print(f"{evidence_id}: {value}")
    
    def compare_metadata(self, evidence_items: List[EvidenceSchema]) -> None:
        """
        Compare metadata fields across evidence items.
        
        Args:
            evidence_items: List of evidence items to compare
        """
        if not evidence_items:
            return
            
        # Collect all metadata keys
        all_keys = set()
        for evidence in evidence_items:
            all_keys.update(evidence.metadata.keys())
        
        if not all_keys:
            self.console.print("[italic]No metadata found in the evidence items[/italic]")
            return
            
        # Create comparison table
        table = Table(
            title="Metadata Comparison",
            box=HEAVY if accessibility_manager.high_contrast else ROUNDED
        )
        
        # Add columns
        table.add_column("Metadata Field", style="bold")
        for evidence in evidence_items:
            table.add_column(evidence.id, style="bold blue")
        
        # Add rows for each metadata key
        for key in sorted(all_keys):
            row = [key]
            
            # Get values for each evidence item
            values = []
            for evidence in evidence_items:
                if key in evidence.metadata:
                    values.append(str(evidence.metadata[key]))
                else:
                    values.append("—")
            
            # Check if values differ
            all_same = len(set(values)) == 1
            
            # Add to row
            for value in values:
                if not all_same:
                    # Highlight differences
                    if accessibility_manager.high_contrast:
                        row.append(f"[black on bright_yellow]{value}[/black on bright_yellow]")
                    else:
                        row.append(f"[bold yellow]{value}[/bold yellow]")
                else:
                    row.append(value)
            
            table.add_row(*row)
        
        self.console.print()
        self.console.print(table)
        self.console.print()


def get_comparison_styles() -> Dict[str, str]:
    """
    Get the current comparison styles based on accessibility settings.
    
    Returns:
        Dictionary of style names and values
    """
    if accessibility_manager.high_contrast:
        return {
            "same": "white on blue",
            "different": "black on bright_yellow",
            "added": "black on bright_green",
            "removed": "bright_white on red",
            "header": "bright_white on blue",
        }
    else:
        return {
            "same": "blue",
            "different": "yellow",
            "added": "green",
            "removed": "red",
            "header": "bold blue",
        }