"""
Terminal-based Relationship Visualization for Evidence CLI.

This module provides terminal-based visualization capabilities for
evidence relationships using ASCII/Unicode art.
"""
import logging
import math
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table
from rich.text import Text
from rich.box import HEAVY, MINIMAL, SIMPLE, ROUNDED

from ..models.relationship_models import (
    RelationshipRegistry, RelationshipType, RelationshipStrength,
    NetworkVisualizer
)
from ..models.evidence_schema import EvidenceSchema
from ..data.evidence_storage import EvidenceStorage

# Configure module logger
logger = logging.getLogger(__name__)


class TerminalNetworkVisualizer:
    """
    Terminal-based visualization for evidence relationship networks.
    
    This class renders relationship networks as ASCII/Unicode graphics
    in the terminal using Rich library components.
    """
    
    # Symbol mappings for different terminal capabilities
    SYMBOLS = {
        "basic": {
            "node": "[ ]",
            "edge": "--",
            "corner": "+",
            "vertical": "|",
            "horizontal": "-",
            "cross": "+",
            "arrow": "->",
            "strong": "==",
            "weak": "..",
        },
        "unicode": {
            "node": "●",
            "edge": "━━",
            "corner": "┏",
            "vertical": "┃",
            "horizontal": "━",
            "cross": "╋",
            "arrow": "→",
            "strong": "━━",
            "weak": "╌╌",
        },
    }
    
    # Color mappings for relationship types
    TYPE_COLORS = {
        RelationshipType.DEPENDS_ON: "red",
        RelationshipType.REQUIRED_BY: "dark_red",
        RelationshipType.PART_OF: "blue",
        RelationshipType.CONTAINS: "dark_blue",
        RelationshipType.DERIVED_FROM: "green",
        RelationshipType.SOURCE_OF: "dark_green",
        RelationshipType.ALTERNATIVE_TO: "yellow",
        RelationshipType.SUPERSEDES: "magenta",
        RelationshipType.SUPERSEDED_BY: "purple",
        RelationshipType.RELATES_TO: "cyan",
        RelationshipType.CONTRADICTS: "bright_red",
    }
    
    # Color mappings for relationship strengths
    STRENGTH_COLORS = {
        RelationshipStrength.WEAK: "dim",
        RelationshipStrength.MODERATE: "none",
        RelationshipStrength.STRONG: "bold",
        RelationshipStrength.CRITICAL: "bold red",
    }
    
    def __init__(self, 
                 registry: RelationshipRegistry,
                 evidence_storage: Optional[EvidenceStorage] = None,
                 use_unicode: bool = True,
                 console: Optional[Console] = None):
        """
        Initialize the terminal network visualizer.
        
        Args:
            registry: Relationship registry
            evidence_storage: Optional evidence storage for retrieving evidence details
            use_unicode: Whether to use unicode symbols (vs. ASCII)
            console: Optional Rich console instance
        """
        self.registry = registry
        self.evidence_storage = evidence_storage
        self.symbols = self.SYMBOLS["unicode" if use_unicode else "basic"]
        self.console = console or Console()
        
        logger.info("Initialized terminal network visualizer")
    
    def _get_entity_display_name(self, entity_id: str) -> str:
        """
        Get a display name for an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Display name for the entity
        """
        if not self.evidence_storage:
            return entity_id
            
        try:
            if entity_id.startswith("EV-"):
                evidence = self.evidence_storage.get_evidence(entity_id)
                if evidence:
                    return f"{entity_id}: {evidence.title[:30]}..."
            elif entity_id.startswith("EP-"):
                # Assume it's an epic ID
                return f"{entity_id} (Epic)"
            elif entity_id.startswith("T-"):
                # Assume it's a task ID
                return f"{entity_id} (Task)"
                
        except Exception:
            pass
            
        return entity_id
    
    def _get_color_by_type(self, rel_type: RelationshipType) -> str:
        """Get color for a relationship type."""
        return self.TYPE_COLORS.get(rel_type, "white")
    
    def _get_style_by_strength(self, strength: RelationshipStrength) -> str:
        """Get style for a relationship strength."""
        return self.STRENGTH_COLORS.get(strength, "none")
    
    def render_relationship_tree(self, 
                                root_id: str, 
                                max_depth: int = 2,
                                direction: str = "outgoing") -> None:
        """
        Render a relationship tree.
        
        Args:
            root_id: ID of the root entity
            max_depth: Maximum depth to render
            direction: 'outgoing', 'incoming', or 'both'
        """
        # Create the tree
        root_name = self._get_entity_display_name(root_id)
        tree = Tree(f"[bold]{root_name}[/bold]")
        
        # Track visited nodes to prevent cycles
        visited = {root_id}
        
        # Build the tree recursively
        self._build_tree(tree, root_id, max_depth, 1, visited, direction)
        
        # Render the tree
        self.console.print()
        self.console.print(Panel(tree, title=f"Relationship Tree for {root_id}", border_style="blue"))
        self.console.print()
    
    def _build_tree(self, 
                   tree: Tree, 
                   entity_id: str, 
                   max_depth: int,
                   current_depth: int,
                   visited: Set[str],
                   direction: str) -> None:
        """
        Build a relationship tree recursively.
        
        Args:
            tree: Rich Tree object to build
            entity_id: Current entity ID
            max_depth: Maximum depth to render
            current_depth: Current depth
            visited: Set of visited entities
            direction: 'outgoing', 'incoming', or 'both'
        """
        if current_depth > max_depth:
            return
            
        # Get relationships
        if direction in ["outgoing", "both"]:
            outgoing = self.registry.get_relationships(entity_id, "outgoing")
            for target_id, rel_data in outgoing.items():
                if target_id in visited:
                    continue
                    
                visited.add(target_id)
                rel_type = rel_data.get("type", RelationshipType.RELATES_TO)
                strength = rel_data.get("strength", RelationshipStrength.MODERATE)
                
                color = self._get_color_by_type(rel_type)
                style = self._get_style_by_strength(strength)
                
                target_name = self._get_entity_display_name(target_id)
                node_text = f"[{color}]{rel_type.value}[/{color}] → [{style}]{target_name}[/{style}]"
                
                subtree = tree.add(node_text)
                self._build_tree(subtree, target_id, max_depth, current_depth + 1, visited.copy(), direction)
        
        if direction in ["incoming", "both"]:
            incoming = self.registry.get_relationships(entity_id, "incoming")
            for source_id, rel_data in incoming.items():
                if source_id in visited:
                    continue
                    
                visited.add(source_id)
                rel_type = rel_data.get("type", RelationshipType.RELATES_TO)
                strength = rel_data.get("strength", RelationshipStrength.MODERATE)
                
                color = self._get_color_by_type(rel_type)
                style = self._get_style_by_strength(strength)
                
                source_name = self._get_entity_display_name(source_id)
                node_text = f"[{style}]{source_name}[/{style}] → [{color}]{rel_type.value}[/{color}]"
                
                subtree = tree.add(node_text)
                self._build_tree(subtree, source_id, max_depth, current_depth + 1, visited.copy(), direction)
    
    def render_relationship_matrix(self, 
                                  entity_ids: List[str],
                                  include_type: bool = True,
                                  include_strength: bool = True) -> None:
        """
        Render a relationship matrix.
        
        Args:
            entity_ids: List of entity IDs to include
            include_type: Whether to include relationship type
            include_strength: Whether to include relationship strength
        """
        # Create the table
        table = Table(title="Relationship Matrix", box=ROUNDED)
        
        # Add headers
        table.add_column("Entity", style="bold")
        for entity_id in entity_ids:
            display_name = entity_id.split('-')[1] if '-' in entity_id else entity_id
            table.add_column(display_name, style="bold")
        
        # Add rows
        for source_id in entity_ids:
            row = [self._get_entity_display_name(source_id)]
            
            for target_id in entity_ids:
                if source_id == target_id:
                    # Diagonal element
                    row.append("—")
                    continue
                
                # Check for relationship
                rel = self.registry.get_relationship(source_id, target_id)
                if not rel:
                    row.append("")
                    continue
                
                # Format cell content
                rel_type = rel.get("type", RelationshipType.RELATES_TO)
                strength = rel.get("strength", RelationshipStrength.MODERATE)
                
                cell_parts = []
                if include_type:
                    type_text = Text(rel_type.value, style=self._get_color_by_type(rel_type))
                    cell_parts.append(type_text)
                
                if include_strength and include_type:
                    cell_parts.append(Text(" "))
                
                if include_strength:
                    strength_text = Text(strength.value.lower(), style=self._get_style_by_strength(strength))
                    cell_parts.append(strength_text)
                    
                # Create the cell content
                cell = Text.assemble(*cell_parts)
                row.append(cell)
            
            table.add_row(*row)
        
        # Render the table
        self.console.print()
        self.console.print(table)
        self.console.print()
    
    def render_impact_analysis(self, entity_id: str) -> None:
        """
        Render impact analysis for an entity.
        
        Args:
            entity_id: ID of the entity to analyze
        """
        entity_name = self._get_entity_display_name(entity_id)
        
        # Get impact analysis
        network_visualizer = NetworkVisualizer(self.registry)
        impact_analysis = network_visualizer.analyze_impact(entity_id)
        
        # Create the tables
        direct_table = Table(title="Direct Impacts", box=SIMPLE)
        direct_table.add_column("Entity", style="bold")
        direct_table.add_column("Relationship", style="bold blue")
        direct_table.add_column("Impact Score", style="bold")
        
        propagation_table = Table(title="Propagation Impacts", box=SIMPLE)
        propagation_table.add_column("Entity", style="bold")
        propagation_table.add_column("Path", style="bold blue")
        propagation_table.add_column("Impact Score", style="bold")
        
        # Add direct impacts
        direct_impacts = impact_analysis.get("direct_impacts", {})
        for target_id, impact in sorted(direct_impacts.items(), key=lambda x: x[1]["impact_score"], reverse=True):
            target_name = self._get_entity_display_name(target_id)
            rel_type = impact.get("relationship_type", RelationshipType.RELATES_TO)
            impact_score = impact.get("impact_score", 0)
            
            # Determine color based on impact score
            score_color = "green"
            if impact_score >= 80:
                score_color = "red"
            elif impact_score >= 50:
                score_color = "yellow"
                
            direct_table.add_row(
                target_name,
                Text(rel_type.value, style=self._get_color_by_type(rel_type)),
                Text(str(impact_score), style=score_color)
            )
        
        # Add propagation impacts
        propagation_impacts = impact_analysis.get("propagation_impacts", {})
        for target_id, impact in sorted(propagation_impacts.items(), key=lambda x: x[1]["impact_score"], reverse=True):
            target_name = self._get_entity_display_name(target_id)
            path = impact.get("path", [])
            impact_score = impact.get("impact_score", 0)
            
            # Format path
            path_text = " → ".join([i.split('-')[1] if '-' in i else i for i in path])
            
            # Determine color based on impact score
            score_color = "green"
            if impact_score >= 80:
                score_color = "red"
            elif impact_score >= 50:
                score_color = "yellow"
                
            propagation_table.add_row(
                target_name,
                path_text,
                Text(str(impact_score), style=score_color)
            )
        
        # Render the tables
        self.console.print()
        self.console.print(Panel(
            f"[bold]Impact Analysis for {entity_name}[/bold]\n\n"
            f"This analysis shows how changes to this evidence might impact related entities.",
            title="Impact Analysis", 
            border_style="green"
        ))
        self.console.print()
        
        # Only show tables if there are impacts
        if direct_impacts:
            self.console.print(direct_table)
        else:
            self.console.print("[italic]No direct impacts found.[/italic]")
            
        self.console.print()
        
        if propagation_impacts:
            self.console.print(propagation_table)
        else:
            self.console.print("[italic]No propagation impacts found.[/italic]")
            
        self.console.print()
    
    def render_network_graph(self, 
                            root_id: str, 
                            max_depth: int = 2,
                            layout: str = "radial") -> None:
        """
        Render a network graph in the terminal.
        
        This uses Unicode box drawing characters to create a simple
        network visualization.
        
        Args:
            root_id: ID of the root entity
            max_depth: Maximum depth to render
            layout: 'radial', 'tree', or 'circle'
        """
        # Get all nodes and edges from the registry
        network = self.registry.get_network(root_id, max_depth)
        nodes = network["nodes"]
        edges = network["edges"]
        
        if not nodes:
            self.console.print("[italic]No network found for this entity.[/italic]")
            return
        
        # Determine terminal dimensions
        width, height = self.console.size
        width = width - 4  # Account for margins
        height = height - 10  # Account for headers and margins
        
        if layout == "radial":
            self._render_radial_layout(root_id, nodes, edges, width, height)
        elif layout == "tree":
            self.render_relationship_tree(root_id, max_depth)
        else:
            self._render_circle_layout(nodes, edges, width, height)
    
    def _render_radial_layout(self, 
                             root_id: str,
                             nodes: List[str],
                             edges: List[Dict[str, Any]],
                             width: int,
                             height: int) -> None:
        """
        Render a radial layout network.
        
        Args:
            root_id: ID of the central node
            nodes: List of node IDs
            edges: List of edge definitions
            width: Terminal width
            height: Terminal height
        """
        # Create a grid to represent the terminal
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Calculate center point
        center_x = width // 2
        center_y = height // 2
        
        # Place root node at center
        grid[center_y][center_x] = '●'
        
        # Calculate positions for other nodes in a radial layout
        node_positions = {root_id: (center_x, center_y)}
        
        # Count how many nodes at each distance from root
        distances = {}
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            
            if source == root_id:
                distance = 1
            elif target == root_id:
                distance = 1
            else:
                # For simplicity, assume all other nodes are at distance 2
                distance = 2
                
            if source != root_id:
                distances[source] = min(distances.get(source, float('inf')), distance)
            if target != root_id:
                distances[target] = min(distances.get(target, float('inf')), distance)
        
        # Count nodes at each distance
        nodes_at_distance = {}
        for node, distance in distances.items():
            nodes_at_distance[distance] = nodes_at_distance.get(distance, 0) + 1
        
        # Position nodes based on distance
        for distance in sorted(nodes_at_distance.keys()):
            count = nodes_at_distance[distance]
            nodes_at_this_distance = [node for node, d in distances.items() if d == distance]
            
            radius = distance * min(width, height) // 10
            
            for i, node in enumerate(nodes_at_this_distance):
                angle = 2 * math.pi * i / count
                x = int(center_x + radius * math.cos(angle))
                y = int(center_y + radius * math.sin(angle))
                
                # Ensure coordinates are within bounds
                x = max(0, min(width - 1, x))
                y = max(0, min(height - 1, y))
                
                node_positions[node] = (x, y)
                grid[y][x] = '●'
        
        # Draw edges
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            
            if source not in node_positions or target not in node_positions:
                continue
                
            source_x, source_y = node_positions[source]
            target_x, target_y = node_positions[target]
            
            # Draw a simple line
            self._draw_line(grid, source_x, source_y, target_x, target_y)
        
        # Render the grid
        self.console.print()
        
        # Create a title
        title = f"Network Graph for {self._get_entity_display_name(root_id)}"
        self.console.print(Panel(title, border_style="blue"))
        
        # Render grid as a string
        result = []
        for row in grid:
            result.append(''.join(row))
        
        self.console.print('\n'.join(result))
        
        # Add legend
        self.console.print()
        self.console.print("● = Node   — = Relationship")
        self.console.print()
    
    def _render_circle_layout(self,
                             nodes: List[str],
                             edges: List[Dict[str, Any]],
                             width: int,
                             height: int) -> None:
        """
        Render a circular layout network.
        
        Args:
            nodes: List of node IDs
            edges: List of edge definitions
            width: Terminal width
            height: Terminal height
        """
        # Create a grid to represent the terminal
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Calculate center point
        center_x = width // 2
        center_y = height // 2
        
        # Calculate radius
        radius = min(width, height) // 3
        
        # Position nodes in a circle
        node_positions = {}
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / len(nodes)
            x = int(center_x + radius * math.cos(angle))
            y = int(center_y + radius * math.sin(angle))
            
            # Ensure coordinates are within bounds
            x = max(0, min(width - 1, x))
            y = max(0, min(height - 1, y))
            
            node_positions[node] = (x, y)
            grid[y][x] = '●'
        
        # Draw edges
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            
            if source not in node_positions or target not in node_positions:
                continue
                
            source_x, source_y = node_positions[source]
            target_x, target_y = node_positions[target]
            
            # Draw a simple line
            self._draw_line(grid, source_x, source_y, target_x, target_y)
        
        # Render the grid
        self.console.print()
        
        # Create a title
        title = f"Network Graph ({len(nodes)} nodes, {len(edges)} edges)"
        self.console.print(Panel(title, border_style="blue"))
        
        # Render grid as a string
        result = []
        for row in grid:
            result.append(''.join(row))
        
        self.console.print('\n'.join(result))
        
        # Add legend
        self.console.print()
        self.console.print("● = Node   — = Relationship")
        self.console.print()
    
    def _draw_line(self, grid: List[List[str]], x0: int, y0: int, x1: int, y1: int) -> None:
        """
        Draw a line between two points using Bresenham's line algorithm.
        
        Args:
            grid: The grid to draw on
            x0, y0: Start point coordinates
            x1, y1: End point coordinates
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while x0 != x1 or y0 != y1:
            if grid[y0][x0] == ' ':
                # Only draw on empty cells
                if dx > dy:
                    grid[y0][x0] = '—'  # Horizontal line
                else:
                    grid[y0][x0] = '|'  # Vertical line
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
                
            # Check bounds
            if x0 < 0 or x0 >= len(grid[0]) or y0 < 0 or y0 >= len(grid):
                break
