# Evidence UI Components

This document provides an overview of the enhanced UI components implemented for the Evidence Management System in Phase 2.4.

## Overview

The Evidence UI components provide terminal-based visualization and interaction capabilities for managing evidence items. These components focus on usability, accessibility, and effective information display in a terminal environment.

## Components

### 1. Relationship Graph Visualization

The relationship graph visualization component (`graph_visualizer.py`) enables terminal-based visualization of evidence relationships using Unicode characters and colors.

Key features:
- Multiple visualization modes (circular, tree, matrix)
- Screen reader compatibility mode
- High contrast mode for accessibility
- Relationship grouping by type
- Impact analysis visualization

Example usage:
```python
from src.ui.graph_visualizer import GraphVisualizer

# Create a visualizer with a relationship registry
visualizer = GraphVisualizer(registry)

# Render a relationship graph for an evidence item
visualizer.render_graph("EV-12345", max_depth=2)

# Toggle accessibility modes
visualizer.switch_mode(high_contrast=True, screen_reader=False)
```

### 2. Evidence Comparison Display

The evidence comparison component (`evidence_comparison.py`) provides side-by-side comparison of multiple evidence items, highlighting differences and similarities.

Key features:
- Field-by-field comparison with difference highlighting
- Metadata comparison
- Timeline visualization for date fields
- List comparison with common/unique items
- High contrast mode support

Example usage:
```python
from src.ui.evidence_comparison import EvidenceComparison

# Create a comparison display
comparison = EvidenceComparison()

# Compare multiple evidence items
comparison.compare([evidence1, evidence2, evidence3], highlight_differences=True)

# Compare specific fields
comparison.compare_fields([evidence1, evidence2], "category")
```

### 3. Syntax Highlighting

The syntax highlighting component (`syntax_highlighting.py`) provides language-aware highlighting for code and structured content in evidence items.

Key features:
- Automatic language detection
- Support for multiple programming languages
- High contrast themes for accessibility
- Line numbering
- Code block extraction from markdown

Example usage:
```python
from src.ui.syntax_highlighting import syntax_highlighter

# Highlight content with auto-detection
syntax_highlighter.highlight_content(code_content)

# Highlight with specific language and title
syntax_highlighter.highlight_content(code_content, language="python", title="Authentication Module")

# Extract and highlight code blocks from markdown
syntax_highlighter.highlight_code_blocks(markdown_content)
```

### 4. Keyboard Navigation

The keyboard navigation extension (`evidence_keyboard_navigation.py`) provides enhanced keyboard shortcuts and navigation for evidence management.

Key features:
- Evidence-specific navigation context
- Tag/category filtering with keyboard commands
- Comparison mode for selecting multiple items
- Detailed view toggle
- Accessibility mode toggles

Example usage:
```python
from src.ui.evidence_keyboard_navigation import EvidenceNavigationContext
from src.ui.keyboard_shortcuts import KeyboardManager

# Create a keyboard manager
keyboard_manager = KeyboardManager()

# Create a navigation context for evidence items
context = EvidenceNavigationContext(evidence_items, keyboard_manager)

# Start navigation
keyboard_manager.start_input_thread()
```

### 5. Template-Based Evidence Creation

The template system (`evidence_templates.py`) provides standardized templates for creating different types of evidence.

Key features:
- Built-in templates for common evidence types
- Form-based creation with field validation
- Template customization and saving
- Interactive and non-interactive modes
- Tag suggestions

Example usage:
```python
from src.ui.evidence_templates import template_manager

# List available templates
template_manager.list_templates()

# Create evidence from a template
evidence = template_manager.create_evidence_from_template("bug_report", interactive=True)
```

### 6. Accessibility Features

The accessibility framework (`accessibility.py`) provides support for different accessibility needs.

Key features:
- High contrast mode
- Screen reader compatibility
- Context managers for temporary mode changes
- Adaptive rendering based on accessibility settings

Example usage:
```python
from src.ui.accessibility import accessibility_manager, HighContrastMode

# Toggle high contrast mode
accessibility_manager.toggle_high_contrast()

# Use context manager for temporary mode
with HighContrastMode(accessibility_manager, enabled=True):
    # Code that runs in high contrast mode
    pass
```

### 7. Localization Framework

The localization system (`localization.py`) provides internationalization and localization support.

Key features:
- String externalization for multiple languages
- Date/time format localization
- Language file management
- String extraction helpers
- Helper function for easy string lookup

Example usage:
```python
from src.ui.localization import localization_manager, _

# Get localized string
title = _("app.title")

# Set locale
localization_manager.set_locale("fr-FR")

# Format date according to locale
formatted_date = localization_manager.format_date(date, format_type="medium")
```

## Testing

The UI components include responsiveness testing to ensure they work effectively with different terminal sizes and configurations. The `evidence_display_responsive.py` test script validates the adaptive capabilities of all components.

Run the test with:
```bash
python -m src.test.evidence_display_responsive
```

## Demo

A demonstration module is provided to showcase all UI components. Run the demo with:
```bash
python -m src.ui.evidence_ui_demo
```

## Integration

The UI components are designed to work together cohesively. For example, the graph visualizer supports high contrast mode from the accessibility framework, and the comparison display can be used with keyboard navigation.

## Extending the Components

To add new UI components or extend existing ones:

1. Follow the established patterns for consistency
2. Support accessibility modes in all new components
3. Use the localization framework for all user-facing strings
4. Implement responsive design for different terminal sizes
5. Add tests for new functionality

## References

- [Rich Documentation](https://rich.readthedocs.io/)
- [WCAG Guidelines](https://www.w3.org/WAI/standards-guidelines/wcag/)