"""
Hierarchical Category System for Evidence Management.

This module defines the hierarchical categorization system for evidence items,
supporting multi-level categorization with inheritance and validation.
"""
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

class CategoryLevel(str, Enum):
    """Enumeration of category hierarchy levels."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    QUATERNARY = "quaternary"

class CategoryType(str, Enum):
    """Primary evidence category types."""
    REQUIREMENT = "Requirement"
    BUG = "Bug"
    DESIGN = "Design"
    TEST = "Test"
    RESULT = "Result"
    REFERENCE = "Reference"
    USER_FEEDBACK = "User Feedback"
    DECISION = "Decision"
    OTHER = "Other"

# Hierarchical category structure
# Format: {primary_category: {secondary_category: [tertiary_categories]}}
CATEGORY_HIERARCHY = {
    CategoryType.REQUIREMENT: {
        "Functional": ["Core", "UI", "API", "Integration", "Security"],
        "Non-functional": ["Performance", "Scalability", "Usability", "Security", "Compliance"],
        "Business": ["Stakeholder", "Market", "Regulatory", "Financial"]
    },
    CategoryType.BUG: {
        "Severity": ["Critical", "High", "Medium", "Low", "Trivial"],
        "Type": ["Functional", "UI", "Performance", "Security", "Data", "Logic"]
    },
    CategoryType.DESIGN: {
        "Architecture": ["System", "Component", "Interface", "Database"],
        "UI/UX": ["Wireframe", "Mockup", "Prototype", "User Flow", "Style Guide"],
        "Technical": ["Algorithm", "Data Structure", "Pattern", "Infrastructure"]
    },
    CategoryType.TEST: {
        "Unit": ["Function", "Class", "Module"],
        "Integration": ["Component", "API", "System", "End-to-End"],
        "Performance": ["Load", "Stress", "Scalability", "Endurance"],
        "Security": ["Penetration", "Vulnerability", "Compliance"]
    },
    CategoryType.RESULT: {
        "Test": ["Passed", "Failed", "Blocked", "Skipped"],
        "Benchmark": ["Performance", "Memory", "CPU", "Network", "Storage"],
        "User": ["Feedback", "Survey", "Interview", "Usage Analytics"]
    },
    CategoryType.REFERENCE: {
        "Document": ["Specification", "Manual", "Guide", "Standard"],
        "Code": ["Example", "Library", "Framework", "Pattern"],
        "External": ["Research Paper", "Article", "Book", "Standard"]
    },
    CategoryType.USER_FEEDBACK: {
        "Source": ["Interview", "Survey", "Support", "Review", "Usage Data"],
        "Sentiment": ["Positive", "Neutral", "Negative", "Mixed"]
    },
    CategoryType.DECISION: {
        "Scope": ["Project", "Feature", "Technical", "Business"],
        "Status": ["Proposed", "Approved", "Rejected", "Deferred", "Implemented"]
    },
    CategoryType.OTHER: {
        "General": ["Note", "Idea", "Question", "Observation"]
    }
}

# Tags recommended for different category types
CATEGORY_SUGGESTED_TAGS = {
    CategoryType.REQUIREMENT: ["priority", "scope", "stakeholder", "epic"],
    CategoryType.BUG: ["regression", "blocker", "ui", "backend", "reproducible"],
    CategoryType.DESIGN: ["approved", "draft", "final", "reviewed"],
    CategoryType.TEST: ["automated", "manual", "regression", "smoke"],
    CategoryType.RESULT: ["baseline", "regression", "improvement", "degradation"],
    CategoryType.REFERENCE: ["standard", "best-practice", "example", "documentation"],
    CategoryType.USER_FEEDBACK: ["feature-request", "bug-report", "praise", "complaint"],
    CategoryType.DECISION: ["approved", "rejected", "pending", "final"],
    CategoryType.OTHER: ["followup", "question", "idea"]
}

def get_category_hierarchy() -> Dict:
    """Get the full category hierarchy structure."""
    return CATEGORY_HIERARCHY

def get_primary_categories() -> List[str]:
    """Get all primary categories as a list."""
    return [category.value for category in CategoryType]

def get_secondary_categories(primary_category: str) -> List[str]:
    """
    Get secondary categories for a given primary category.
    
    Args:
        primary_category: The primary category name
        
    Returns:
        List of secondary category names
    """
    try:
        category_type = CategoryType(primary_category)
        return list(CATEGORY_HIERARCHY[category_type].keys())
    except (ValueError, KeyError):
        return []

def get_tertiary_categories(primary_category: str, secondary_category: str) -> List[str]:
    """
    Get tertiary categories for given primary and secondary categories.
    
    Args:
        primary_category: The primary category name
        secondary_category: The secondary category name
        
    Returns:
        List of tertiary category names
    """
    try:
        category_type = CategoryType(primary_category)
        return CATEGORY_HIERARCHY[category_type].get(secondary_category, [])
    except (ValueError, KeyError):
        return []

def validate_category_path(category_path: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate if the given category path is valid in the hierarchy.
    
    Args:
        category_path: List of categories from primary to specific level
        
    Returns:
        Tuple containing:
            - Boolean indicating if the path is valid
            - Error message if invalid, None otherwise
    """
    if not category_path:
        return False, "Category path cannot be empty"
        
    if len(category_path) == 1:
        try:
            CategoryType(category_path[0])
            return True, None
        except ValueError:
            return False, f"Invalid primary category: {category_path[0]}"
    
    primary = category_path[0]
    
    try:
        category_type = CategoryType(primary)
    except ValueError:
        return False, f"Invalid primary category: {primary}"
    
    if len(category_path) >= 2:
        secondary = category_path[1]
        if secondary not in CATEGORY_HIERARCHY[category_type]:
            return False, f"Invalid secondary category '{secondary}' for primary '{primary}'"
    
    if len(category_path) >= 3:
        secondary = category_path[1]
        tertiary = category_path[2]
        if tertiary not in CATEGORY_HIERARCHY[category_type].get(secondary, []):
            return False, f"Invalid tertiary category '{tertiary}' for path '{primary}/{secondary}'"
    
    return True, None

def get_suggested_tags(category_path: List[str]) -> List[str]:
    """
    Get suggested tags based on the category path.
    
    Args:
        category_path: List of categories from primary to specific level
        
    Returns:
        List of suggested tags
    """
    if not category_path:
        return []
    
    try:
        primary = CategoryType(category_path[0])
        return CATEGORY_SUGGESTED_TAGS.get(primary, [])
    except ValueError:
        return []
