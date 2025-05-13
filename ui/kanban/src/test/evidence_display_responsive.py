"""
Evidence Display Responsiveness Test

This script tests the responsiveness of the evidence UI components
with different terminal sizes and configurations.
"""
import os
import sys
import time
import logging
from typing import List, Tuple, Dict, Any
from rich.console import Console

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.models.evidence_schema import EvidenceSchema, EvidenceCategory, EvidenceRelevance
from src.models.relationship_models import RelationshipRegistry, RelationshipType, RelationshipStrength
from src.ui.display import console, print_success, print_error, print_info
from src.ui.graph_visualizer import GraphVisualizer
from src.ui.evidence_comparison import EvidenceComparison
from src.ui.accessibility import accessibility_manager
from src.ui.syntax_highlighting import syntax_highlighter

# Configure logger
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_evidence() -> List[EvidenceSchema]:
    """
    Create test evidence items.
    
    Returns:
        List of test evidence items
    """
    # Create sample evidence items of different sizes
    evidence1 = EvidenceSchema(
        title="Small Evidence Item",
        description="This is a small evidence item with minimal content.",
        category=EvidenceCategory.REQUIREMENT,
        relevance_score=EvidenceRelevance.MEDIUM,
    )
    
    evidence2 = EvidenceSchema(
        title="Medium Evidence Item with Tags and Metadata",
        description="This is a medium-sized evidence item with more content, including tags and metadata.",
        category=EvidenceCategory.DESIGN,
        subcategory="Architecture",
        relevance_score=EvidenceRelevance.HIGH,
        tags=["design", "architecture", "system"],
        metadata={
            "version": "1.0",
            "author": "Test User",
            "approved": True,
            "comments": "This is a test comment"
        }
    )
    
    # Create a large evidence item with long description
    long_description = """
    This is a large evidence item with a very long description that spans multiple paragraphs.
    
    It contains detailed information about a design decision, including the context,
    alternatives considered, and the reasoning behind the decision.
    
    The purpose of this evidence item is to test how the UI components handle large
    content and ensure that they remain responsive and usable.
    
    Additionally, this evidence item has multiple relationships with other evidence items,
    which will be used to test the relationship visualization components.
    
    It also includes code snippets, formatted text, and other complex content to
    test various UI component capabilities:
    
    ```python
    def test_function():
        # This is a test function
        print("Testing display of code snippets")
        return True
    ```
    
    And tables:
    
    | Column 1 | Column 2 | Column 3 |
    |----------|----------|----------|
    | Value 1  | Value 2  | Value 3  |
    | Value 4  | Value 5  | Value 6  |
    
    And lists:
    
    * Item 1
    * Item 2
    * Item 3
      * Subitem 1
      * Subitem 2
    
    This evidence item is designed to push the limits of the UI components
    and ensure they handle large, complex content appropriately.
    """
    
    evidence3 = EvidenceSchema(
        title="Large Evidence Item with Complex Content",
        description=long_description,
        category=EvidenceCategory.DECISION,
        subcategory="Architecture",
        relevance_score=EvidenceRelevance.CRITICAL,
        tags=["decision", "architecture", "design", "system", "complex"],
        metadata={
            "version": "2.0",
            "author": "Test User",
            "approved": True,
            "review_date": "2025-05-10",
            "reviewers": ["Reviewer 1", "Reviewer 2", "Reviewer 3"],
            "approval_status": "Approved",
            "comments": "This is a complex test case",
            "code_sample": """
            def parse_evidence(evidence_data):
                \"\"\"
                Parse evidence data from input.
                
                Args:
                    evidence_data: Raw evidence data
                    
                Returns:
                    Parsed evidence object
                \"\"\"
                # Validate input
                if not evidence_data:
                    raise ValueError("Evidence data cannot be empty")
                    
                # Parse JSON
                try:
                    parsed = json.loads(evidence_data)
                except json.JSONDecodeError:
                    raise ValueError("Invalid JSON format")
                    
                # Create evidence object
                return EvidenceSchema(**parsed)
            """
        }
    )
    
    return [evidence1, evidence2, evidence3]


def test_evidence_display_responsive() -> None:
    """
    Test the responsiveness of evidence display components.
    """
    print_info("Starting Evidence Display Responsiveness Test")
    console.print()
    
    # Create test evidence
    evidence_items = create_test_evidence()
    
    # Create a relationship registry
    registry = RelationshipRegistry()
    
    # Add relationships
    registry.register_relationship(
        evidence_items[0].id, evidence_items[1].id, 
        RelationshipType.RELATES_TO, RelationshipStrength.MODERATE
    )
    
    registry.register_relationship(
        evidence_items[0].id, evidence_items[2].id, 
        RelationshipType.DEPENDS_ON, RelationshipStrength.STRONG
    )
    
    registry.register_relationship(
        evidence_items[1].id, evidence_items[2].id, 
        RelationshipType.PART_OF, RelationshipStrength.CRITICAL
    )
    
    # Test with different terminal widths
    terminal_widths = [40, 80, 120]
    
    for width in terminal_widths:
        test_width_responsiveness(evidence_items, registry, width)
    
    # Test with different accessibility modes
    test_accessibility_modes(evidence_items, registry)
    
    print_success("Evidence Display Responsiveness Test Completed Successfully")


def test_width_responsiveness(
    evidence_items: List[EvidenceSchema], 
    registry: RelationshipRegistry, 
    width: int
) -> None:
    """
    Test UI component responsiveness at a specific terminal width.
    
    Args:
        evidence_items: Test evidence items
        registry: Relationship registry
        width: Terminal width to simulate
    """
    console.print(f"[bold]Testing with terminal width: {width}[/bold]")
    console.print()
    
    # Create a test console with fixed width
    test_console = Console(width=width)
    
    # Test graph visualizer
    visualizer = GraphVisualizer(registry, console=test_console)
    
    console.print("[bold]Testing Graph Visualizer:[/bold]")
    visualizer.render_graph(evidence_items[0].id, max_depth=1, width=width, height=10)
    console.print()
    
    # Test evidence comparison
    comparison = EvidenceComparison(console=test_console)
    
    console.print("[bold]Testing Evidence Comparison:[/bold]")
    comparison.compare(evidence_items[:2], highlight_differences=True)
    console.print()
    
    # Test syntax highlighting
    code_sample = evidence_items[2].metadata.get("code_sample", "# No code")
    
    console.print("[bold]Testing Syntax Highlighting:[/bold]")
    syntax_highlighter.highlight_content(code_sample, language="python", 
                                     title=f"Width: {width}")
    console.print()


def test_accessibility_modes(
    evidence_items: List[EvidenceSchema], 
    registry: RelationshipRegistry
) -> None:
    """
    Test UI components with different accessibility modes.
    
    Args:
        evidence_items: Test evidence items
        registry: Relationship registry
    """
    console.print("[bold]Testing Accessibility Modes[/bold]")
    console.print()
    
    # Test with high contrast mode
    console.print("[bold]Testing High Contrast Mode:[/bold]")
    accessibility_manager.toggle_high_contrast()
    
    # Test components
    visualizer = GraphVisualizer(registry, console=console, 
                             high_contrast=accessibility_manager.high_contrast)
    
    visualizer.render_graph(evidence_items[0].id, max_depth=1)
    console.print()
    
    # Reset accessibility settings
    accessibility_manager.toggle_high_contrast()
    
    # Test with screen reader mode
    console.print("[bold]Testing Screen Reader Mode:[/bold]")
    accessibility_manager.toggle_screen_reader()
    
    # Update visualizer settings
    visualizer.screen_reader_mode = accessibility_manager.screen_reader_mode
    
    visualizer.render_graph(evidence_items[0].id, max_depth=1)
    console.print()
    
    # Reset accessibility settings
    accessibility_manager.toggle_screen_reader()


if __name__ == "__main__":
    test_evidence_display_responsive()