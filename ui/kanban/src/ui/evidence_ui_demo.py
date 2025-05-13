"""
Evidence UI Demonstration Module.

This module provides demonstration functions to showcase the integrated
evidence UI enhancements developed in Phase 2.4.
"""
import logging
from typing import List, Dict, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..models.evidence_schema import EvidenceSchema, EvidenceCategory, EvidenceRelevance
from ..models.relationship_models import RelationshipRegistry, RelationshipType, RelationshipStrength
from .display import console, print_success, print_error, print_info
from .graph_visualizer import GraphVisualizer
from .evidence_comparison import EvidenceComparison
from .evidence_keyboard_navigation import EvidenceNavigationContext, EvidenceComparisonDisplay
from .accessibility import accessibility_manager, HighContrastMode, ScreenReaderMode
from .syntax_highlighting import syntax_highlighter
from .evidence_templates import template_manager
from .localization import localization_manager, _

# Configure module logger
logger = logging.getLogger(__name__)


def create_sample_evidence() -> List[EvidenceSchema]:
    """
    Create sample evidence items for demonstration.
    
    Returns:
        List of sample evidence items
    """
    # Create registry for relationships
    registry = RelationshipRegistry()
    
    # Create sample evidence items
    evidence1 = EvidenceSchema(
        title="User Authentication Bug",
        description="Users are occasionally being logged out unexpectedly when navigating between pages.",
        category=EvidenceCategory.BUG,
        subcategory="Frontend",
        relevance_score=EvidenceRelevance.HIGH,
        source="User Feedback",
        tags=["authentication", "frontend", "bug"]
    )
    
    evidence2 = EvidenceSchema(
        title="Authentication Service Design",
        description="Design document for the authentication service architecture, including token management and session handling.",
        category=EvidenceCategory.DESIGN,
        subcategory="Architecture",
        relevance_score=EvidenceRelevance.HIGH,
        source="Technical Documentation",
        tags=["authentication", "architecture", "design"]
    )
    
    evidence3 = EvidenceSchema(
        title="Token Refresh Implementation",
        description="Implementation of token refresh mechanism to prevent authentication timeouts.",
        category=EvidenceCategory.REQUIREMENT,
        subcategory="Functional",
        relevance_score=EvidenceRelevance.MEDIUM,
        source="Requirements Document",
        tags=["authentication", "token", "requirement"]
    )
    
    evidence4 = EvidenceSchema(
        title="Authentication End-to-End Test",
        description="Test case for end-to-end authentication flow including login, session management, and logout.",
        category=EvidenceCategory.TEST,
        subcategory="End-to-End",
        relevance_score=EvidenceRelevance.MEDIUM,
        source="Test Plan",
        tags=["authentication", "testing", "e2e"]
    )
    
    evidence5 = EvidenceSchema(
        title="Authentication Performance Results",
        description="Performance test results for the authentication service under load.",
        category=EvidenceCategory.RESULT,
        subcategory="Performance",
        relevance_score=EvidenceRelevance.LOW,
        source="Test Results",
        tags=["authentication", "performance", "results"]
    )
    
    # Add code snippet to one evidence
    code_sample = """
def validate_token(token: str) -> bool:
    \"\"\"
    Validate the authentication token.
    
    Args:
        token: The token to validate
        
    Returns:
        True if token is valid, False otherwise
    \"\"\"
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        # Check if token is expired
        if datetime.fromtimestamp(payload["exp"]) < datetime.now():
            logger.warning("Token expired")
            return False
            
        # Check if user exists
        user_id = payload.get("sub")
        if not user_id or not User.objects.filter(id=user_id).exists():
            logger.warning(f"User {user_id} not found")
            return False
            
        return True
        
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        return False
    """
    
    evidence2.metadata["code_sample"] = code_sample
    
    # Add relationships
    registry.register_relationship(
        evidence1.id, evidence2.id, 
        RelationshipType.RELATES_TO, RelationshipStrength.STRONG
    )
    
    registry.register_relationship(
        evidence1.id, evidence3.id, 
        RelationshipType.DEPENDS_ON, RelationshipStrength.CRITICAL
    )
    
    registry.register_relationship(
        evidence2.id, evidence3.id, 
        RelationshipType.PART_OF, RelationshipStrength.MODERATE
    )
    
    registry.register_relationship(
        evidence3.id, evidence4.id, 
        RelationshipType.VERIFIED_BY, RelationshipStrength.STRONG
    )
    
    registry.register_relationship(
        evidence4.id, evidence5.id, 
        RelationshipType.PRODUCES, RelationshipStrength.MODERATE
    )
    
    # Return the sample evidence items and registry
    return [evidence1, evidence2, evidence3, evidence4, evidence5], registry


def demonstrate_ui_components() -> None:
    """
    Demonstrate the evidence UI enhancements.
    
    This function showcases the various UI components developed
    for the evidence management system.
    """
    print_info(_("app.welcome"))
    console.print()
    
    # Create sample evidence
    evidence_items, registry = create_sample_evidence()
    
    console.print("[bold]Evidence UI Enhancement Demonstration[/bold]")
    console.print("This demonstration showcases the components developed for Phase 2.4.")
    console.print()
    
    # List available components
    components = [
        "1. Relationship Graph Visualization",
        "2. Evidence Comparison Display",
        "3. Syntax Highlighting for Code Evidence",
        "4. High Contrast Mode",
        "5. Template-Based Evidence Creation",
        "6. Localization Framework",
        "7. Run All Demonstrations",
        "0. Exit"
    ]
    
    for component in components:
        console.print(component)
    
    console.print()
    choice = input("Select a component to demonstrate (0-7): ")
    
    if choice == "1":
        demonstrate_relationship_visualization(evidence_items[0], registry)
    elif choice == "2":
        demonstrate_evidence_comparison(evidence_items)
    elif choice == "3":
        demonstrate_syntax_highlighting(evidence_items[1])
    elif choice == "4":
        demonstrate_high_contrast_mode(evidence_items, registry)
    elif choice == "5":
        demonstrate_template_based_creation()
    elif choice == "6":
        demonstrate_localization()
    elif choice == "7":
        run_all_demonstrations(evidence_items, registry)
    else:
        print_info("Exiting demonstration")
        

def demonstrate_relationship_visualization(evidence: EvidenceSchema, registry: RelationshipRegistry) -> None:
    """
    Demonstrate the relationship graph visualization.
    
    Args:
        evidence: Evidence item to visualize relationships for
        registry: Relationship registry
    """
    console.print()
    console.print("[bold]Relationship Graph Visualization Demonstration[/bold]")
    console.print()
    
    # Create a graph visualizer
    visualizer = GraphVisualizer(registry, console=console)
    
    # Show normal mode
    console.print("[bold]Standard Visualization Mode:[/bold]")
    visualizer.render_graph(evidence.id, max_depth=2)
    console.print()
    
    # Show relationships by type
    console.print("[bold]Relationships Grouped by Type:[/bold]")
    visualizer.render_relationships_by_type(evidence.id)
    console.print()
    
    # Show with screen reader compatibility
    console.print("[bold]Screen Reader Compatible Mode:[/bold]")
    visualizer.screen_reader_mode = True
    visualizer.render_graph(evidence.id, max_depth=2)
    console.print()
    
    print_success("Relationship visualization demonstration completed")


def demonstrate_evidence_comparison(evidence_items: List[EvidenceSchema]) -> None:
    """
    Demonstrate the evidence comparison display.
    
    Args:
        evidence_items: List of evidence items to compare
    """
    console.print()
    console.print("[bold]Evidence Comparison Display Demonstration[/bold]")
    console.print()
    
    # Create items to compare (use first 3 items)
    items_to_compare = evidence_items[:3]
    
    # Create comparison display
    comparison = EvidenceComparison(console=console)
    
    # Show basic comparison
    console.print("[bold]Basic Comparison:[/bold]")
    comparison.compare(items_to_compare, highlight_differences=True)
    console.print()
    
    # Show specific field comparison
    console.print("[bold]Field-Specific Comparison (Category):[/bold]")
    comparison.compare_fields(items_to_compare, "Category")
    console.print()
    
    # Show metadata comparison
    console.print("[bold]Metadata Comparison:[/bold]")
    comparison.compare_metadata(items_to_compare)
    console.print()
    
    print_success("Evidence comparison demonstration completed")


def demonstrate_syntax_highlighting(evidence: EvidenceSchema) -> None:
    """
    Demonstrate syntax highlighting for code evidence.
    
    Args:
        evidence: Evidence item containing code
    """
    console.print()
    console.print("[bold]Syntax Highlighting Demonstration[/bold]")
    console.print()
    
    # Get code sample from evidence metadata
    code_sample = evidence.metadata.get("code_sample", "# No code sample available")
    
    # Show standard highlighting
    console.print("[bold]Standard Highlighting:[/bold]")
    syntax_highlighter.highlight_content(code_sample, language="python", title="Token Validation Function")
    console.print()
    
    # Show with detected language
    console.print("[bold]Auto-Detected Language:[/bold]")
    syntax_highlighter.highlight_content(code_sample, language="auto", title="Auto-Detected Language")
    console.print()
    
    # Show with high contrast theme
    console.print("[bold]High Contrast Theme:[/bold]")
    with HighContrastMode(accessibility_manager, True):
        syntax_highlighter.highlight_content(code_sample, language="python", title="High Contrast Mode")
    console.print()
    
    print_success("Syntax highlighting demonstration completed")


def demonstrate_high_contrast_mode(evidence_items: List[EvidenceSchema], registry: RelationshipRegistry) -> None:
    """
    Demonstrate high contrast mode for accessibility.
    
    Args:
        evidence_items: List of evidence items
        registry: Relationship registry
    """
    console.print()
    console.print("[bold]High Contrast Mode Demonstration[/bold]")
    console.print()
    
    # Create components
    visualizer = GraphVisualizer(registry, console=console)
    comparison = EvidenceComparison(console=console)
    
    # Enable high contrast mode
    console.print("[bold]Enabling High Contrast Mode:[/bold]")
    accessibility_manager.toggle_high_contrast()
    console.print()
    
    # Show relationship visualization in high contrast
    console.print("[bold]Relationship Visualization in High Contrast:[/bold]")
    visualizer.render_graph(evidence_items[0].id, max_depth=1)
    console.print()
    
    # Show evidence comparison in high contrast
    console.print("[bold]Evidence Comparison in High Contrast:[/bold]")
    comparison.compare(evidence_items[:2], highlight_differences=True)
    console.print()
    
    # Disable high contrast mode
    accessibility_manager.toggle_high_contrast()
    print_success("High contrast mode demonstration completed")


def demonstrate_template_based_creation() -> None:
    """Demonstrate template-based evidence creation."""
    console.print()
    console.print("[bold]Template-Based Evidence Creation Demonstration[/bold]")
    console.print()
    
    # List available templates
    template_manager.list_templates()
    console.print()
    
    # Show bug report template details
    console.print("[bold]Bug Report Template Details:[/bold]")
    template = template_manager.templates.get("bug_report")
    
    if template:
        # Show template fields
        console.print(f"Name: {template.name}")
        console.print(f"Description: {template.description}")
        console.print(f"Category: {template.category.value}")
        console.print(f"Suggested Tags: {', '.join(template.suggested_tags)}")
        console.print()
        
        console.print("[bold]Fields:[/bold]")
        for field_name, field_props in template.fields.items():
            console.print(f"- {field_props.get('prompt', field_name)}")
            if field_props.get('description'):
                console.print(f"  {field_props.get('description')}")
    
    console.print()
    print_success("Template-based creation demonstration completed")
    console.print("To create evidence interactively, use template_manager.create_evidence_from_template('bug_report', interactive=True)")


def demonstrate_localization() -> None:
    """Demonstrate the localization framework."""
    console.print()
    console.print("[bold]Localization Framework Demonstration[/bold]")
    console.print()
    
    # Show available locales
    locales = localization_manager.get_available_locales()
    console.print(f"[bold]Available Locales:[/bold] {', '.join(locales)}")
    console.print()
    
    # Show string localization
    console.print("[bold]String Localization Examples:[/bold]")
    keys = ["app.title", "evidence.title", "message.success", "date.medium"]
    
    for key in keys:
        value = _(key)
        console.print(f"{key}: {value}")
    console.print()
    
    # Show date formatting
    from datetime import datetime
    now = datetime.now()
    
    console.print("[bold]Date Formatting Examples:[/bold]")
    for format_type in ["short", "medium", "long", "full"]:
        formatted = localization_manager.format_date(now, format_type)
        console.print(f"{format_type}: {formatted}")
    console.print()
    
    print_success("Localization framework demonstration completed")


def run_all_demonstrations(evidence_items: List[EvidenceSchema], registry: RelationshipRegistry) -> None:
    """
    Run all demonstrations in sequence.
    
    Args:
        evidence_items: List of evidence items
        registry: Relationship registry
    """
    demonstrate_relationship_visualization(evidence_items[0], registry)
    console.print("\n" + "-" * 50 + "\n")
    
    demonstrate_evidence_comparison(evidence_items)
    console.print("\n" + "-" * 50 + "\n")
    
    demonstrate_syntax_highlighting(evidence_items[1])
    console.print("\n" + "-" * 50 + "\n")
    
    demonstrate_high_contrast_mode(evidence_items, registry)
    console.print("\n" + "-" * 50 + "\n")
    
    demonstrate_template_based_creation()
    console.print("\n" + "-" * 50 + "\n")
    
    demonstrate_localization()
    
    print_success("All demonstrations completed successfully")


if __name__ == "__main__":
    demonstrate_ui_components()