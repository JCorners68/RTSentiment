"""
Terminal-based Graph Visualization for Evidence Relationships.

This module provides specialized terminal-based visualization for evidence
relationship graphs using Unicode characters and Rich components for
accessibility and clarity.
"""
import math
import logging
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table
from rich.text import Text
from rich.box import HEAVY, MINIMAL, SIMPLE, ROUNDED
from rich.columns import Columns
from rich.layout import Layout
from rich.measure import Measurement
from rich.style import Style

from ..models.relationship_models import (
    RelationshipRegistry, RelationshipType, RelationshipStrength,
    NetworkVisualizer
)
from ..models.evidence_schema import EvidenceSchema
from .relationship_visualizer import TerminalNetworkVisualizer

# Configure module logger
logger = logging.getLogger(__name__)


class GraphVisualizer:
    """
    Enhanced graph visualization for evidence relationships.
    
    This class extends the relationship visualizer with more advanced
    rendering options and accessibility features including high contrast
    mode and screen reader compatibility.
    """
    
    def __init__(self, 
                registry: RelationshipRegistry,
                console: Optional[Console] = None,
                high_contrast: bool = False,
                screen_reader_mode: bool = False):
        """
        Initialize the graph visualizer.
        
        Args:
            registry: Relationship registry containing relationship data
            console: Rich console instance (will create one if not provided)
            high_contrast: Whether to use high contrast mode for accessibility
            screen_reader_mode: Whether to use screen reader compatible output
        """
        self.registry = registry
        self.console = console or Console()
        self.high_contrast = high_contrast
        self.screen_reader_mode = screen_reader_mode
        
        # Create a terminal network visualizer as a base
        self.base_visualizer = TerminalNetworkVisualizer(registry, console=self.console)
        
        # Color schemes for normal and high contrast mode
        self.color_schemes = {
            "normal": {
                RelationshipType.SUPPORTS: "green",
                RelationshipType.CONTRADICTS: "red",
                RelationshipType.RELATES_TO: "blue",
                RelationshipType.DEPENDS_ON: "yellow",
                RelationshipType.CAUSES: "magenta",
                RelationshipType.DERIVES_FROM: "cyan",
                RelationshipType.SUPERSEDES: "bright_magenta",
                RelationshipType.SIMILAR_TO: "bright_cyan",
                RelationshipType.CITES: "bright_blue",
                RelationshipType.MENTIONED_BY: "bright_yellow",
                RelationshipType.PART_OF: "bright_green",
            },
            "high_contrast": {
                RelationshipType.SUPPORTS: "bright_white on green",
                RelationshipType.CONTRADICTS: "bright_white on red",
                RelationshipType.RELATES_TO: "bright_white on blue",
                RelationshipType.DEPENDS_ON: "black on yellow",
                RelationshipType.CAUSES: "bright_white on magenta",
                RelationshipType.DERIVES_FROM: "black on cyan",
                RelationshipType.SUPERSEDES: "bright_white on dark_magenta",
                RelationshipType.SIMILAR_TO: "black on bright_cyan",
                RelationshipType.CITES: "bright_white on dark_blue",
                RelationshipType.MENTIONED_BY: "black on bright_yellow",
                RelationshipType.PART_OF: "black on bright_green",
            }
        }
        
        # Special symbols for different render modes
        self.symbols = {
            "normal": {
                "node": "●",
                "edge": "─",
                "arrow": "→",
                "corner": "┌",
                "cross": "┼",
            },
            "screen_reader": {
                "node": "[NODE]",
                "edge": "---",
                "arrow": "->",
                "corner": "+",
                "cross": "+",
            }
        }
        
        # Get appropriate symbol set and color scheme
        self.symbol_set = self.symbols["screen_reader" if screen_reader_mode else "normal"]
        self.color_scheme = self.color_schemes["high_contrast" if high_contrast else "normal"]
        
        logger.info(f"Initialized graph visualizer (high_contrast={high_contrast}, screen_reader_mode={screen_reader_mode})")
    
    def _get_color_for_type(self, rel_type: RelationshipType) -> str:
        """Get appropriate color for a relationship type based on current mode."""
        return self.color_scheme.get(rel_type, "white")
    
    def _get_text_for_screen_reader(self, entity_id: str, relationships: Dict[str, Dict]) -> str:
        """
        Generate screen-reader friendly text description of relationships.
        
        Args:
            entity_id: The central entity ID
            relationships: Dictionary of relationships
            
        Returns:
            Plain text description of relationships for screen readers
        """
        lines = [f"Relationship graph for {entity_id}"]
        lines.append(f"Total relationships: {len(relationships)}")
        lines.append("")
        
        for target_id, rel_data in relationships.items():
            rel_type = rel_data.get("type", RelationshipType.RELATES_TO)
            strength = rel_data.get("strength", RelationshipStrength.MODERATE)
            lines.append(f"{entity_id} {rel_type.value} {target_id} (Strength: {strength.value})")
        
        return "\n".join(lines)
    
    def render_graph(self, 
                    entity_id: str,
                    max_depth: int = 2,
                    width: Optional[int] = None,
                    height: Optional[int] = None) -> None:
        """
        Render a relationship graph centered on an entity.
        
        Args:
            entity_id: ID of the central entity
            max_depth: Maximum relationship depth to display
            width: Optional width constraint
            height: Optional height constraint
        """
        # Get terminal size if not specified
        if width is None or height is None:
            width, height = self.console.size
            width = width - 4  # Account for margins
            height = height - 6  # Account for margins and headers
        
        # Get relationships from registry
        network = self.registry.get_network(entity_id, max_depth)
        nodes = network["nodes"]
        edges = network["edges"]
        
        if not nodes:
            self.console.print("[italic]No relationships found for this entity.[/italic]")
            return
        
        # Check if using screen reader mode
        if self.screen_reader_mode:
            # Generate plain text description and render in a panel
            description = self._get_text_for_screen_reader(entity_id, self.registry.get_related_items(entity_id))
            self.console.print()
            self.console.print(Panel(
                description,
                title=f"Relationship Graph for {entity_id}",
                border_style="blue",
                box=ROUNDED
            ))
            return
        
        # For visual rendering, use a layout
        self.console.print()
        self.console.print(f"[bold]Relationship Graph for {entity_id}[/bold]")
        self.console.print()
        
        # Choose between different visualization methods based on complexity
        if len(nodes) <= 5:
            # Simple circular visualization for small networks
            self._render_simple_circular_layout(entity_id, nodes, edges, width, height)
        elif len(nodes) <= 15:
            # Use the tree-based visualization for medium networks
            self.base_visualizer.render_relationship_tree(entity_id, max_depth, "both")
        else:
            # For complex networks, show a matrix and statistics
            self._render_complex_network_summary(entity_id, nodes, edges, max_depth)
    
    def _render_simple_circular_layout(self,
                                      center_id: str,
                                      nodes: List[str],
                                      edges: List[Dict],
                                      width: int,
                                      height: int) -> None:
        """
        Render a simple circular layout for small networks.
        
        Args:
            center_id: ID of the central entity
            nodes: List of node IDs
            edges: List of edge data
            width: Available width
            height: Available height
        """
        # Create a grid to represent the terminal
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Calculate center point
        center_x = width // 2
        center_y = height // 2
        
        # Place center node with a special marker
        grid[center_y][center_x] = self.symbol_set["node"]
        
        # Position other nodes in a circle around the center
        node_positions = {center_id: (center_x, center_y)}
        
        # Calculate radius based on available space and number of nodes
        radius = min(width, height) // 3
        radius = min(radius, 10)  # Cap radius for readability
        
        # Position other nodes
        other_nodes = [n for n in nodes if n != center_id]
        for i, node in enumerate(other_nodes):
            # Distribute nodes evenly in a circle
            angle = 2 * math.pi * i / len(other_nodes)
            x = int(center_x + radius * math.cos(angle))
            y = int(center_y + radius * math.sin(angle))
            
            # Ensure coordinates are within bounds
            x = max(0, min(width - 1, x))
            y = max(0, min(height - 1, y))
            
            node_positions[node] = (x, y)
            grid[y][x] = self.symbol_set["node"]
        
        # Draw edges
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            
            if source not in node_positions or target not in node_positions:
                continue
                
            source_x, source_y = node_positions[source]
            target_x, target_y = node_positions[target]
            
            # Draw line with relationship type indicated by color
            rel_type = edge.get("type", RelationshipType.RELATES_TO)
            color = self._get_color_for_type(rel_type)
            
            # Draw the line (simplified Bresenham algorithm)
            self._draw_colored_line(grid, source_x, source_y, target_x, target_y, color, rel_type)
        
        # Render the grid with colors
        self._render_colored_grid(grid, node_positions)
        
        # Add a legend
        self._render_relationship_legend()
    
    def _draw_colored_line(self,
                          grid: List[List[str]],
                          x0: int, y0: int,
                          x1: int, y1: int,
                          color: str,
                          rel_type: RelationshipType) -> None:
        """
        Draw a colored line between two points using Bresenham's algorithm.
        
        Args:
            grid: Grid to draw on
            x0, y0: Start coordinates
            x1, y1: End coordinates
            color: Color for the line
            rel_type: Relationship type for labeling
        """
        # Simplified Bresenham algorithm for line drawing
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        points = []
        current_x, current_y = x0, y0
        
        while (current_x != x1 or current_y != y1):
            points.append((current_x, current_y))
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                current_x += sx
            if e2 < dx:
                err += dx
                current_y += sy
                
            # Check bounds
            if (current_x < 0 or current_x >= len(grid[0]) or
                current_y < 0 or current_y >= len(grid)):
                break
        
        # Add last point if within bounds
        if (x1 >= 0 and x1 < len(grid[0]) and
            y1 >= 0 and y1 < len(grid)):
            points.append((x1, y1))
        
        # Store line data for colored rendering
        for i, (x, y) in enumerate(points):
            # Skip start and end points (which are nodes)
            if (i > 0 and i < len(points) - 1):
                if grid[y][x] == ' ':
                    # Mark grid with special character to be replaced with colored version
                    grid[y][x] = self.symbol_set["edge"]
    
    def _render_colored_grid(self, grid: List[List[str]], node_positions: Dict[str, Tuple[int, int]]) -> None:
        """
        Render the grid with colored elements.
        
        Args:
            grid: Grid to render
            node_positions: Positions of nodes in the grid
        """
        # First convert grid to plain text
        lines = [''.join(row) for row in grid]
        
        # Print each line
        for line in lines:
            self.console.print(line)
    
    def _render_relationship_legend(self) -> None:
        """Render a legend for relationship types and their colors."""
        legend_columns = []
        
        # Create columns for types
        for rel_type in RelationshipType:
            color = self._get_color_for_type(rel_type)
            text = Text.assemble(
                (self.symbol_set["edge"] * 3, color),
                " ",
                (rel_type.value, "italic")
            )
            legend_columns.append(text)
        
        # Split into groups to avoid overwhelming the display
        groups = [legend_columns[i:i+3] for i in range(0, len(legend_columns), 3)]
        
        self.console.print()
        for group in groups:
            self.console.print(Columns(group))
    
    def _render_complex_network_summary(self,
                                      entity_id: str,
                                      nodes: List[str],
                                      edges: List[Dict],
                                      max_depth: int) -> None:
        """
        Render a summary of a complex network with statistics.
        
        Args:
            entity_id: ID of the central entity
            nodes: List of node IDs
            edges: List of edge data
            max_depth: Maximum depth used for the network
        """
        # Get network statistics
        stats = self.base_visualizer._get_network_statistics(entity_id, max_depth)
        
        # Create a summary panel
        summary = [
            f"[bold]Network Size:[/bold] {len(nodes)} nodes, {len(edges)} edges",
            f"[bold]Average Connections:[/bold] {stats.get('avg_connections', 0):.1f} per node",
            f"[bold]Most Connected Node:[/bold] {stats.get('most_connected_node', 'N/A')}",
            f"[bold]Network Density:[/bold] {stats.get('density', 0):.2f}",
            "",
            "[italic]This network is too complex for direct visualization.[/italic]",
            "[italic]Use the relationship tree or matrix for more details.[/italic]"
        ]
        
        self.console.print(Panel(
            "\n".join(summary),
            title=f"Complex Network Summary for {entity_id}",
            border_style="blue",
            box=ROUNDED
        ))
        
        # Show relationship distribution
        self._render_relationship_distribution(stats.get("relationship_distribution", {}))
    
    def _render_relationship_distribution(self, distribution: Dict[str, int]) -> None:
        """
        Render a bar chart of relationship type distribution.
        
        Args:
            distribution: Dictionary mapping relationship types to counts
        """
        if not distribution:
            return
            
        self.console.print()
        self.console.print("[bold]Relationship Type Distribution:[/bold]")
        
        # Calculate max count for scaling
        max_count = max(distribution.values())
        max_width = 40  # Maximum bar width
        
        # Sort by count, descending
        sorted_items = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        
        for rel_type_str, count in sorted_items:
            try:
                rel_type = RelationshipType(rel_type_str)
                color = self._get_color_for_type(rel_type)
            except:
                rel_type_str = str(rel_type_str)
                color = "white"
            
            # Calculate bar width
            width = int((count / max_count) * max_width) if max_count > 0 else 0
            bar = "█" * width
            
            # Format and print the bar
            text = Text()
            text.append(f"{rel_type_str:15} ")
            text.append(f"{count:3} ")
            text.append(bar, style=color)
            
            self.console.print(text)
    
    def render_relationships_by_type(self, entity_id: str) -> None:
        """
        Render relationships grouped by type.
        
        Args:
            entity_id: ID of the entity to display relationships for
        """
        # Get all relationships for this entity
        relationships = self.registry.get_related_items(entity_id)
        
        if not relationships:
            self.console.print("[italic]No relationships found for this entity.[/italic]")
            return
        
        # Group by relationship type
        by_type = {}
        for target_id, metadata in relationships.items():
            rel_type = metadata.get("type", RelationshipType.RELATES_TO)
            if rel_type not in by_type:
                by_type[rel_type] = []
            by_type[rel_type].append((target_id, metadata))
        
        # Create a tree for visualization
        tree = Tree(f"[bold]Relationships for {entity_id}[/bold]")
        
        # Add branches for each type
        for rel_type, items in by_type.items():
            color = self._get_color_for_type(rel_type)
            type_branch = tree.add(f"[{color}]{rel_type.value}[/{color}] ({len(items)})")
            
            # Add entities under each type
            for target_id, metadata in items:
                strength = metadata.get("strength", RelationshipStrength.MODERATE)
                impact = metadata.get("impact_score", 0)
                
                # Format target info
                if self.screen_reader_mode:
                    target_text = f"{target_id} - Strength: {strength.value}, Impact: {impact}"
                else:
                    # Use symbols for strength
                    strength_symbol = "●" if strength == RelationshipStrength.STRONG else "○"
                    target_text = f"{strength_symbol} {target_id} (Impact: {impact})"
                
                type_branch.add(target_text)
        
        # Print the tree
        self.console.print()
        self.console.print(tree)
        self.console.print()
    
    def switch_mode(self, high_contrast: Optional[bool] = None, screen_reader: Optional[bool] = None) -> None:
        """
        Switch between different visualization modes.
        
        Args:
            high_contrast: Whether to use high contrast mode
            screen_reader: Whether to use screen reader mode
        """
        if high_contrast is not None:
            self.high_contrast = high_contrast
        
        if screen_reader is not None:
            self.screen_reader_mode = screen_reader
        
        # Update symbol set and color scheme based on new modes
        self.symbol_set = self.symbols["screen_reader" if self.screen_reader_mode else "normal"]
        self.color_scheme = self.color_schemes["high_contrast" if self.high_contrast else "normal"]
        
        logger.info(f"Switched to high_contrast={self.high_contrast}, screen_reader={self.screen_reader_mode}")
        
        # Show confirmation
        mode_text = []
        if self.high_contrast:
            mode_text.append("high contrast")
        if self.screen_reader_mode:
            mode_text.append("screen reader compatible")
            
        if mode_text:
            self.console.print(f"[bold]Switched to {' and '.join(mode_text)} mode[/bold]")
        else:
            self.console.print("[bold]Switched to standard visualization mode[/bold]")