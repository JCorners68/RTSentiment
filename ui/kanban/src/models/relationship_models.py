"""
Relationship Models for the Evidence Management System.

This module provides models and utilities for enhanced relationship tracking
between evidence items and other entities, including impact analysis,
relationship strength, visualization helpers, and relationship types.
"""
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Set, Tuple
from dataclasses import dataclass
import json
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import io
from pathlib import Path


class RelationshipType(str, Enum):
    """Types of relationships that can exist between evidence items and other entities."""
    SUPPORTS = "supports"          # Evidence supports/confirms another item
    CONTRADICTS = "contradicts"    # Evidence contradicts/refutes another item
    RELATES_TO = "relates_to"      # Generic relation (default)
    DEPENDS_ON = "depends_on"      # Evidence depends on another item
    CAUSES = "causes"              # Evidence shows cause of something
    DERIVES_FROM = "derives_from"  # Evidence is derived from another item
    SUPERSEDES = "supersedes"      # Evidence replaces/updates another item
    SIMILAR_TO = "similar_to"      # Evidence is similar to another item
    CITES = "cites"                # Evidence cites/references another item
    MENTIONED_BY = "mentioned_by"  # Evidence is mentioned by another item
    PART_OF = "part_of"            # Evidence is part of a larger item


class RelationshipStrength(str, Enum):
    """Strength indicators for relationships between entities."""
    WEAK = "weak"           # Tenuous or uncertain connection
    MODERATE = "moderate"   # Reasonable but not definitive connection
    STRONG = "strong"       # Clear, direct connection
    CRITICAL = "critical"   # Essential, fundamental connection


@dataclass
class RelationshipMetadata:
    """Metadata for a relationship between two entities."""
    relationship_type: RelationshipType = RelationshipType.RELATES_TO
    strength: RelationshipStrength = RelationshipStrength.MODERATE
    description: str = ""
    created_at: datetime = None
    updated_at: datetime = None
    impact_score: int = 0  # 0-100 score indicating impact level
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "relationship_type": self.relationship_type.value,
            "strength": self.strength.value,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "impact_score": self.impact_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RelationshipMetadata':
        """Create a RelationshipMetadata instance from a dictionary."""
        # Convert string enums to enum values
        relationship_type = RelationshipType(data.get("relationship_type", RelationshipType.RELATES_TO.value))
        strength = RelationshipStrength(data.get("strength", RelationshipStrength.MODERATE.value))
        
        # Parse datetime fields
        created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else None
        updated_at = datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None
        
        return cls(
            relationship_type=relationship_type,
            strength=strength,
            description=data.get("description", ""),
            created_at=created_at,
            updated_at=updated_at,
            impact_score=data.get("impact_score", 0)
        )


class RelationshipRegistry:
    """Registry and validator for evidence relationships."""
    
    def __init__(self):
        # Dictionary to store metadata for relationships
        # Key format: "source_id:target_id"
        self.relationships: Dict[str, RelationshipMetadata] = {}
        
        # For internal storage (persistence handled by storage classes)
        self._registry_path: Optional[Path] = None
    
    def register_relationship(
        self, 
        source_id: str, 
        target_id: str,
        relationship_type: RelationshipType = RelationshipType.RELATES_TO,
        strength: RelationshipStrength = RelationshipStrength.MODERATE,
        description: str = "",
        impact_score: int = 0
    ) -> RelationshipMetadata:
        """
        Register a relationship between two entities.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            relationship_type: Type of relationship
            strength: Strength of the relationship
            description: Description of the relationship
            impact_score: Impact score (0-100)
            
        Returns:
            RelationshipMetadata object
        """
        key = f"{source_id}:{target_id}"
        metadata = RelationshipMetadata(
            relationship_type=relationship_type,
            strength=strength,
            description=description,
            impact_score=impact_score
        )
        self.relationships[key] = metadata
        return metadata
    
    def update_relationship(
        self,
        source_id: str,
        target_id: str,
        updates: Dict[str, Any]
    ) -> Optional[RelationshipMetadata]:
        """
        Update a relationship's metadata.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            updates: Dictionary of fields to update
            
        Returns:
            Updated RelationshipMetadata or None if not found
        """
        key = f"{source_id}:{target_id}"
        if key not in self.relationships:
            return None
            
        metadata = self.relationships[key]
        
        # Update relationship type if provided
        if "relationship_type" in updates:
            if isinstance(updates["relationship_type"], str):
                metadata.relationship_type = RelationshipType(updates["relationship_type"])
            else:
                metadata.relationship_type = updates["relationship_type"]
                
        # Update strength if provided
        if "strength" in updates:
            if isinstance(updates["strength"], str):
                metadata.strength = RelationshipStrength(updates["strength"])
            else:
                metadata.strength = updates["strength"]
                
        # Update description if provided
        if "description" in updates:
            metadata.description = updates["description"]
            
        # Update impact score if provided
        if "impact_score" in updates:
            metadata.impact_score = min(100, max(0, int(updates["impact_score"])))
            
        # Update timestamp
        metadata.updated_at = datetime.now()
        
        return metadata
    
    def get_relationship(self, source_id: str, target_id: str) -> Optional[RelationshipMetadata]:
        """
        Get relationship metadata between two entities.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            
        Returns:
            RelationshipMetadata object or None if not found
        """
        key = f"{source_id}:{target_id}"
        return self.relationships.get(key)
    
    def remove_relationship(self, source_id: str, target_id: str) -> bool:
        """
        Remove a relationship from the registry.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            
        Returns:
            True if removed, False if not found
        """
        key = f"{source_id}:{target_id}"
        if key in self.relationships:
            del self.relationships[key]
            return True
        return False
    
    def validate_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: Optional[RelationshipType] = None,
        strength: Optional[RelationshipStrength] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate a relationship against registry rules.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            relationship_type: Type of relationship to validate
            strength: Strength of relationship to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Can't relate to self
        if source_id == target_id:
            errors.append("Cannot create a relationship with self")
            
        # Check if specified relationship type is valid
        if relationship_type is not None and not isinstance(relationship_type, RelationshipType):
            try:
                RelationshipType(relationship_type)
            except ValueError:
                valid_types = [t.value for t in RelationshipType]
                errors.append(f"Invalid relationship type. Must be one of: {', '.join(valid_types)}")
        
        # Check if specified strength is valid
        if strength is not None and not isinstance(strength, RelationshipStrength):
            try:
                RelationshipStrength(strength)
            except ValueError:
                valid_strengths = [s.value for s in RelationshipStrength]
                errors.append(f"Invalid relationship strength. Must be one of: {', '.join(valid_strengths)}")
        
        return len(errors) == 0, errors
    
    def get_related_items(self, entity_id: str) -> Dict[str, RelationshipMetadata]:
        """
        Get all items related to the specified entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Dictionary of {target_id: metadata}
        """
        related = {}
        for key, metadata in self.relationships.items():
            source, target = key.split(":")
            if source == entity_id:
                related[target] = metadata
        return related
    
    def to_dict(self) -> Dict:
        """Convert registry to dictionary for serialization."""
        result = {}
        for key, metadata in self.relationships.items():
            result[key] = metadata.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RelationshipRegistry':
        """Create a RelationshipRegistry instance from a dictionary."""
        registry = cls()
        for key, metadata_dict in data.items():
            if ":" in key:  # Validate key format
                registry.relationships[key] = RelationshipMetadata.from_dict(metadata_dict)
        return registry


class ImpactAnalyzer:
    """
    Provides impact analysis for evidence changes and relationships.
    
    This class helps identify the cascading effects of changes to
    evidence items based on their relationships with other entities.
    """
    
    def __init__(self, registry: RelationshipRegistry):
        self.registry = registry
        
    def analyze_impact(self, evidence_id: str) -> Dict[str, Any]:
        """
        Analyze the impact of changes to an evidence item.
        
        Args:
            evidence_id: ID of the evidence item to analyze
            
        Returns:
            Dictionary with impact analysis results
        """
        # Start with direct relationships
        direct_relations = self.registry.get_related_items(evidence_id)
        
        # Calculate total impact
        total_impact_score = 0
        high_impact_items = []
        moderate_impact_items = []
        low_impact_items = []
        
        # Analyze each relationship
        for target_id, metadata in direct_relations.items():
            impact_score = metadata.impact_score
            total_impact_score += impact_score
            
            relation_impact = {
                "id": target_id,
                "relationship_type": metadata.relationship_type.value,
                "strength": metadata.strength.value,
                "impact_score": impact_score
            }
            
            # Categorize by impact level
            if impact_score >= 70:
                high_impact_items.append(relation_impact)
            elif impact_score >= 30:
                moderate_impact_items.append(relation_impact)
            else:
                low_impact_items.append(relation_impact)
        
        # Calculate average impact
        avg_impact = total_impact_score / len(direct_relations) if direct_relations else 0
        
        # Build and return analysis results
        return {
            "evidence_id": evidence_id,
            "total_relationships": len(direct_relations),
            "average_impact": avg_impact,
            "high_impact_items": high_impact_items,
            "moderate_impact_items": moderate_impact_items,
            "low_impact_items": low_impact_items,
            "total_impact_score": total_impact_score
        }
    
    def analyze_propagation(self, evidence_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Analyze how changes propagate through the relationship network.
        
        Args:
            evidence_id: ID of the evidence item to analyze
            max_depth: Maximum depth for propagation analysis
            
        Returns:
            Dictionary with propagation analysis results
        """
        # Build a graph for propagation analysis
        graph = nx.DiGraph()
        visited = set()
        pending = [(evidence_id, 0)]  # (node_id, depth)
        
        # Add edges to graph with relationship metadata
        while pending:
            node_id, depth = pending.pop(0)
            
            if node_id in visited or depth > max_depth:
                continue
                
            visited.add(node_id)
            graph.add_node(node_id)
            
            # Get direct relationships
            relations = self.registry.get_related_items(node_id)
            for target_id, metadata in relations.items():
                graph.add_node(target_id)
                graph.add_edge(
                    node_id, 
                    target_id,
                    relationship_type=metadata.relationship_type.value,
                    strength=metadata.strength.value,
                    impact_score=metadata.impact_score
                )
                
                # Continue analysis for next level
                if depth < max_depth:
                    pending.append((target_id, depth + 1))
        
        # Calculate propagation metrics
        propagation_paths = []
        total_propagated_impact = 0
        
        # Get all simple paths from the source to all reachable nodes
        for target in nx.descendants(graph, evidence_id):
            for path in nx.all_simple_paths(graph, evidence_id, target, cutoff=max_depth):
                # Calculate path impact as product of edge impact scores
                path_impact = 1.0
                path_details = []
                
                for i in range(len(path) - 1):
                    source, target = path[i], path[i+1]
                    edge_data = graph.get_edge_data(source, target)
                    impact_score = edge_data.get('impact_score', 0)
                    strength = edge_data.get('strength', RelationshipStrength.MODERATE.value)
                    rel_type = edge_data.get('relationship_type', RelationshipType.RELATES_TO.value)
                    
                    # Impact diminishes with path length (exponential decay)
                    path_impact *= (impact_score / 100) * (0.7 ** i)
                    
                    path_details.append({
                        "source": source,
                        "target": target,
                        "relationship_type": rel_type,
                        "strength": strength,
                        "impact_score": impact_score
                    })
                
                # Scale back to 0-100
                path_impact *= 100
                total_propagated_impact += path_impact
                
                propagation_paths.append({
                    "path": path,
                    "impact": path_impact,
                    "details": path_details
                })
        
        # Return propagation analysis
        return {
            "evidence_id": evidence_id,
            "max_depth": max_depth,
            "total_nodes_affected": len(visited) - 1,  # Exclude the source
            "total_propagated_impact": total_propagated_impact,
            "propagation_paths": propagation_paths
        }


class NetworkVisualizer:
    """
    Provides visualization utilities for evidence relationship networks.
    
    This class helps visualize relationships between evidence items and
    other entities as network graphs.
    """
    
    def __init__(self, registry: RelationshipRegistry):
        self.registry = registry
        
        # Visualization settings
        self.node_colors = {
            "evidence": "#4CAF50",  # Green
            "epic": "#2196F3",      # Blue
            "task": "#FF9800",      # Orange
            "other": "#9E9E9E"      # Gray
        }
        
        self.edge_colors = {
            RelationshipType.SUPPORTS.value: "#4CAF50",    # Green
            RelationshipType.CONTRADICTS.value: "#F44336", # Red
            RelationshipType.RELATES_TO.value: "#9E9E9E",  # Gray
            RelationshipType.DEPENDS_ON.value: "#2196F3",  # Blue
            RelationshipType.CAUSES.value: "#FF9800",      # Orange
            RelationshipType.DERIVES_FROM.value: "#9C27B0", # Purple
            RelationshipType.SUPERSEDES.value: "#795548",  # Brown
            RelationshipType.SIMILAR_TO.value: "#00BCD4",  # Cyan
            RelationshipType.CITES.value: "#3F51B5",       # Indigo
            RelationshipType.MENTIONED_BY.value: "#009688", # Teal
            RelationshipType.PART_OF.value: "#FF5722"      # Deep Orange
        }
        
        # Width multiplier based on relationship strength
        self.strength_width = {
            RelationshipStrength.WEAK.value: 1,
            RelationshipStrength.MODERATE.value: 2,
            RelationshipStrength.STRONG.value: 3,
            RelationshipStrength.CRITICAL.value: 4
        }
    
    def build_graph(self, center_id: str, max_depth: int = 2) -> nx.Graph:
        """
        Build a NetworkX graph for relationships centered around an entity.
        
        Args:
            center_id: ID of the central entity
            max_depth: Maximum depth of relationships to include
            
        Returns:
            NetworkX graph object
        """
        graph = nx.Graph()
        visited = set()
        pending = [(center_id, 0, "evidence")]  # (node_id, depth, node_type)
        
        # Add relationships to graph
        while pending:
            node_id, depth, node_type = pending.pop(0)
            
            if node_id in visited or depth > max_depth:
                continue
                
            visited.add(node_id)
            graph.add_node(node_id, node_type=node_type)
            
            # Get direct relationships
            relations = self.registry.get_related_items(node_id)
            for target_id, metadata in relations.items():
                # Determine target type (simplified - could be more sophisticated)
                target_type = "evidence"
                if target_id.startswith("EPIC-"):
                    target_type = "epic"
                elif target_id.startswith("TASK-"):
                    target_type = "task"
                
                graph.add_node(target_id, node_type=target_type)
                graph.add_edge(
                    node_id, 
                    target_id,
                    relationship_type=metadata.relationship_type.value,
                    strength=metadata.strength.value,
                    impact_score=metadata.impact_score
                )
                
                # Continue analysis for next level
                if depth < max_depth and target_id not in visited:
                    pending.append((target_id, depth + 1, target_type))
        
        return graph
    
    def generate_network_plot(
        self, 
        center_id: str, 
        max_depth: int = 2,
        figsize: Tuple[int, int] = (10, 8),
        show_labels: bool = True,
        output_path: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Generate a network visualization plot.
        
        Args:
            center_id: ID of the central entity
            max_depth: Maximum depth of relationships to include
            figsize: Figure size as (width, height) in inches
            show_labels: Whether to show node labels
            output_path: Optional path to save the figure
            
        Returns:
            Bytes of the PNG image if output_path is None, else None
        """
        graph = self.build_graph(center_id, max_depth)
        
        # No relationships
        if len(graph.nodes) <= 1:
            return None
        
        # Create figure and axes
        plt.figure(figsize=figsize)
        pos = nx.spring_layout(graph, seed=42)  # Consistent layout
        
        # Prepare node colors and sizes
        node_colors = [self.node_colors.get(graph.nodes[n]["node_type"], self.node_colors["other"]) for n in graph.nodes]
        node_sizes = [800 if n == center_id else 400 for n in graph.nodes]
        
        # Prepare edge colors and widths
        edge_colors = []
        edge_widths = []
        
        for u, v, data in graph.edges(data=True):
            rel_type = data.get("relationship_type", RelationshipType.RELATES_TO.value)
            strength = data.get("strength", RelationshipStrength.MODERATE.value)
            
            edge_colors.append(self.edge_colors.get(rel_type, "#9E9E9E"))
            edge_widths.append(self.strength_width.get(strength, 2))
        
        # Draw the network
        nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=node_sizes)
        
        if show_labels:
            nx.draw_networkx_labels(graph, pos, font_size=10)
            
        nx.draw_networkx_edges(
            graph, pos, width=edge_widths, edge_color=edge_colors,
            connectionstyle="arc3,rad=0.1",  # Curved edges
            arrowsize=15
        )
        
        # Add legend
        plt.title(f"Relationship Network for {center_id}")
        plt.axis("off")  # No axes
        
        # Save or return image
        if output_path:
            plt.savefig(output_path, format="png", dpi=150, bbox_inches="tight")
            plt.close()
            return None
        else:
            # Return image bytes
            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close()
            buf.seek(0)
            return buf.getvalue()
    
    def get_network_statistics(self, center_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Get statistics about the relationship network.
        
        Args:
            center_id: ID of the central entity
            max_depth: Maximum depth of relationships to include
            
        Returns:
            Dictionary with network statistics
        """
        graph = self.build_graph(center_id, max_depth)
        
        # Calculate statistics
        num_nodes = len(graph.nodes)
        num_edges = len(graph.edges)
        
        # Calculate degree distribution
        degree_distribution = {n: len(list(graph.neighbors(n))) for n in graph.nodes}
        
        # Calculate centrality measures
        betweenness_centrality = nx.betweenness_centrality(graph)
        closeness_centrality = nx.closeness_centrality(graph)
        
        # Count relationship types
        relationship_counts = {}
        for u, v, data in graph.edges(data=True):
            rel_type = data.get("relationship_type", RelationshipType.RELATES_TO.value)
            relationship_counts[rel_type] = relationship_counts.get(rel_type, 0) + 1
        
        # Return network statistics
        return {
            "center_id": center_id,
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "avg_degree": sum(degree_distribution.values()) / num_nodes if num_nodes > 0 else 0,
            "max_degree": max(degree_distribution.values()) if degree_distribution else 0,
            "node_with_max_degree": max(degree_distribution.items(), key=lambda x: x[1])[0] if degree_distribution else None,
            "most_central_node": max(betweenness_centrality.items(), key=lambda x: x[1])[0] if betweenness_centrality else None,
            "relationship_distribution": relationship_counts
        }
