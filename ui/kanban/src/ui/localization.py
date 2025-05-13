"""
Localization Framework for Evidence UI.

This module provides internationalization and localization capabilities
for the evidence management system's user interface.
"""
import logging
import os
import json
import re
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import locale
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from .display import console, print_info, print_error, print_warning

# Configure module logger
logger = logging.getLogger(__name__)


class LocalizationManager:
    """
    Manager for text localization and internationalization.
    
    This class provides functionality for loading, managing, and
    displaying localized text in different languages.
    """
    
    def __init__(self, 
                locale_dir: Optional[str] = None,
                default_locale: str = "en-US",
                console: Optional[Console] = None):
        """
        Initialize the localization manager.
        
        Args:
            locale_dir: Directory containing locale files
            default_locale: Default locale to use
            console: Optional console for display
        """
        self.console = console or Console()
        self.locale_dir = locale_dir or os.path.join(os.path.dirname(__file__), "..", "..", "locales")
        self.default_locale = default_locale
        self.current_locale = default_locale
        self.translations: Dict[str, Dict[str, str]] = {}
        
        # Create locale directory if it doesn't exist
        os.makedirs(self.locale_dir, exist_ok=True)
        
        # Load the default locale
        self._initialize_default_locale()
        
        # Try to detect and load the system locale
        self._detect_system_locale()
        
        # Load all available locales
        self.load_locales()
        
        logger.info(f"Initialized localization manager (current_locale={self.current_locale})")
    
    def _initialize_default_locale(self) -> None:
        """Initialize the default locale with English strings."""
        # English strings for the evidence system
        self.translations["en-US"] = {
            # General UI
            "app.title": "Evidence Management System",
            "app.welcome": "Welcome to the Evidence Management System",
            "app.exit": "Exiting...",
            
            # Commands
            "command.help": "Show help",
            "command.exit": "Exit",
            "command.back": "Go back",
            "command.cancel": "Cancel",
            "command.save": "Save",
            "command.delete": "Delete",
            "command.edit": "Edit",
            "command.view": "View",
            "command.search": "Search",
            "command.filter": "Filter",
            "command.sort": "Sort",
            "command.create": "Create",
            "command.import": "Import",
            "command.export": "Export",
            
            # Evidence fields
            "evidence.id": "ID",
            "evidence.title": "Title",
            "evidence.description": "Description",
            "evidence.category": "Category",
            "evidence.subcategory": "Subcategory",
            "evidence.relevance": "Relevance",
            "evidence.date_collected": "Date Collected",
            "evidence.tags": "Tags",
            "evidence.source": "Source",
            "evidence.created_at": "Created At",
            "evidence.updated_at": "Updated At",
            "evidence.created_by": "Created By",
            "evidence.attachments": "Attachments",
            "evidence.relationships": "Relationships",
            
            # Categories
            "category.requirement": "Requirement",
            "category.bug": "Bug",
            "category.design": "Design",
            "category.test": "Test",
            "category.result": "Result",
            "category.reference": "Reference",
            "category.user_feedback": "User Feedback",
            "category.decision": "Decision",
            "category.other": "Other",
            
            # Relevance levels
            "relevance.low": "Low",
            "relevance.medium": "Medium",
            "relevance.high": "High",
            "relevance.critical": "Critical",
            
            # Messages
            "message.success": "Success",
            "message.error": "Error",
            "message.warning": "Warning",
            "message.info": "Information",
            "message.confirm": "Are you sure?",
            "message.yes": "Yes",
            "message.no": "No",
            "message.loading": "Loading...",
            "message.processing": "Processing...",
            "message.saving": "Saving...",
            "message.deleting": "Deleting...",
            "message.searching": "Searching...",
            "message.no_results": "No results found",
            "message.invalid_input": "Invalid input",
            "message.required_field": "This field is required",
            
            # Specific pages
            "page.evidence_list": "Evidence List",
            "page.evidence_details": "Evidence Details",
            "page.evidence_create": "Create Evidence",
            "page.evidence_edit": "Edit Evidence",
            "page.evidence_search": "Search Evidence",
            "page.evidence_compare": "Compare Evidence",
            "page.attachments": "Attachments",
            "page.relationships": "Relationships",
            
            # Accessibility
            "accessibility.high_contrast": "High Contrast Mode",
            "accessibility.screen_reader": "Screen Reader Mode",
            "accessibility.keyboard_navigation": "Keyboard Navigation",
            
            # Help text
            "help.evidence_create": "Create a new evidence item.",
            "help.evidence_edit": "Edit an existing evidence item.",
            "help.evidence_search": "Search for evidence items.",
            "help.evidence_compare": "Compare multiple evidence items.",
            "help.keyboard_shortcuts": "Keyboard Shortcuts",
            
            # Templates
            "template.title": "Evidence Templates",
            "template.select": "Select Template",
            "template.create": "Create Template",
            "template.edit": "Edit Template",
            "template.delete": "Delete Template",
            "template.saved": "Template saved successfully",
            "template.deleted": "Template deleted successfully",
            "template.error": "Error working with template",
            
            # Date formats
            "date.short": "%Y-%m-%d",
            "date.medium": "%b %d, %Y",
            "date.long": "%B %d, %Y",
            "date.full": "%A, %B %d, %Y",
            "date.time": "%H:%M:%S",
            "date.datetime": "%Y-%m-%d %H:%M:%S",
        }
        
        # Save the default locale
        self._save_locale("en-US", self.translations["en-US"])
    
    def _detect_system_locale(self) -> None:
        """Attempt to detect and use the system locale."""
        try:
            # Get system locale
            system_locale, _ = locale.getdefaultlocale()
            
            if system_locale:
                # Convert to standard format
                lang_code = system_locale.replace('_', '-')
                
                # Check if we have a direct match
                if os.path.exists(os.path.join(self.locale_dir, f"{lang_code}.json")):
                    self.current_locale = lang_code
                    return
                    
                # Try language code only (e.g., 'en' for 'en-US')
                lang_only = lang_code.split('-')[0]
                
                # Check if we have any locale with this language
                for filename in os.listdir(self.locale_dir):
                    if filename.startswith(f"{lang_only}-") and filename.endswith(".json"):
                        self.current_locale = os.path.splitext(filename)[0]
                        return
                        
        except Exception as e:
            logger.warning(f"Error detecting system locale: {str(e)}")
    
    def _save_locale(self, locale_code: str, translations: Dict[str, str]) -> bool:
        """
        Save a locale file.
        
        Args:
            locale_code: Locale code (e.g., 'en-US')
            translations: Dictionary of string keys and translations
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.locale_dir, f"{locale_code}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved locale file: {locale_code}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving locale file {locale_code}: {str(e)}")
            return False
    
    def load_locales(self) -> None:
        """Load all available locale files."""
        try:
            # Find all locale files
            for filename in os.listdir(self.locale_dir):
                if filename.endswith('.json'):
                    locale_code = os.path.splitext(filename)[0]
                    
                    try:
                        # Skip if already loaded
                        if locale_code in self.translations:
                            continue
                            
                        file_path = os.path.join(self.locale_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            self.translations[locale_code] = json.load(f)
                            
                        logger.info(f"Loaded locale: {locale_code}")
                        
                    except Exception as e:
                        logger.error(f"Error loading locale {locale_code}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error loading locales: {str(e)}")
    
    def get_available_locales(self) -> List[str]:
        """
        Get a list of available locales.
        
        Returns:
            List of locale codes
        """
        return list(self.translations.keys())
    
    def set_locale(self, locale_code: str) -> bool:
        """
        Set the current locale.
        
        Args:
            locale_code: Locale code to set
            
        Returns:
            True if successful, False if locale not found
        """
        if locale_code in self.translations:
            self.current_locale = locale_code
            logger.info(f"Set locale to: {locale_code}")
            return True
            
        logger.warning(f"Locale not found: {locale_code}")
        return False
    
    def get_string(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Get a localized string by key.
        
        Args:
            key: String key to look up
            default: Default value if key not found
            **kwargs: Format arguments for string interpolation
            
        Returns:
            Localized string
        """
        # Try current locale
        translations = self.translations.get(self.current_locale, {})
        if key in translations:
            string = translations[key]
        else:
            # Fall back to default locale
            default_translations = self.translations.get(self.default_locale, {})
            string = default_translations.get(key, default or key)
            
        # Format with provided arguments
        if kwargs:
            try:
                return string.format(**kwargs)
            except:
                return string
        
        return string
    
    def get_date_format(self, format_type: str = "medium") -> str:
        """
        Get a localized date format string.
        
        Args:
            format_type: Type of date format ('short', 'medium', 'long', 'full')
            
        Returns:
            Date format string
        """
        key = f"date.{format_type}"
        return self.get_string(key)
    
    def format_date(self, date: datetime, format_type: str = "medium") -> str:
        """
        Format a date using the current locale's format.
        
        Args:
            date: Date to format
            format_type: Type of date format ('short', 'medium', 'long', 'full')
            
        Returns:
            Formatted date string
        """
        date_format = self.get_date_format(format_type)
        try:
            return date.strftime(date_format)
        except:
            # Fall back to ISO format
            return date.isoformat()
    
    def extract_strings(self, file_path: str) -> Dict[str, str]:
        """
        Extract strings from a Python file for localization.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary of string keys and values
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for strings in the format: _("string")
            pattern = r'_\("([^"]*)"\)'
            matches = re.findall(pattern, content)
            
            # Convert to dictionary
            result = {}
            for i, string in enumerate(matches):
                # Generate a key based on the filename and index
                filename = os.path.basename(file_path)
                base_name = os.path.splitext(filename)[0]
                key = f"{base_name}.string{i}"
                result[key] = string
                
            return result
            
        except Exception as e:
            logger.error(f"Error extracting strings from {file_path}: {str(e)}")
            return {}
    
    def generate_language_file(self, locale_code: str, base_language: str = "en-US") -> bool:
        """
        Generate a new language file based on another language.
        
        Args:
            locale_code: New locale code
            base_language: Base language to copy strings from
            
        Returns:
            True if successful, False otherwise
        """
        if locale_code in self.translations:
            print_warning(f"Locale {locale_code} already exists. Use update_language_file instead.")
            return False
            
        if base_language not in self.translations:
            print_error(f"Base language {base_language} not found.")
            return False
            
        try:
            # Copy translations from base language
            new_translations = self.translations[base_language].copy()
            
            # Save new language file
            if self._save_locale(locale_code, new_translations):
                # Load the new language
                self.translations[locale_code] = new_translations
                print_info(f"Created new language file: {locale_code}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error generating language file {locale_code}: {str(e)}")
            print_error(f"Error generating language file: {str(e)}")
            return False
    
    def update_language_file(self, locale_code: str, base_language: str = "en-US") -> bool:
        """
        Update a language file with missing strings from another language.
        
        Args:
            locale_code: Locale code to update
            base_language: Base language to get missing strings from
            
        Returns:
            True if successful, False otherwise
        """
        if locale_code not in self.translations:
            print_warning(f"Locale {locale_code} not found. Use generate_language_file instead.")
            return False
            
        if base_language not in self.translations:
            print_error(f"Base language {base_language} not found.")
            return False
            
        try:
            # Get existing translations
            existing = self.translations[locale_code]
            
            # Get base translations
            base = self.translations[base_language]
            
            # Add missing keys
            updated = False
            for key, value in base.items():
                if key not in existing:
                    existing[key] = value
                    updated = True
                    
            if not updated:
                print_info(f"No missing strings found in {locale_code}.")
                return True
                
            # Save updated language file
            if self._save_locale(locale_code, existing):
                print_info(f"Updated language file: {locale_code}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error updating language file {locale_code}: {str(e)}")
            print_error(f"Error updating language file: {str(e)}")
            return False
    
    def display_locale_info(self, locale_code: Optional[str] = None) -> None:
        """
        Display information about a locale.
        
        Args:
            locale_code: Locale code to display (current locale if None)
        """
        if locale_code is None:
            locale_code = self.current_locale
            
        if locale_code not in self.translations:
            print_error(f"Locale not found: {locale_code}")
            return
            
        translations = self.translations[locale_code]
        
        # Display locale information
        self.console.print()
        self.console.print(f"[bold]Locale:[/bold] {locale_code}")
        self.console.print(f"[bold]String count:[/bold] {len(translations)}")
        
        # Display a sample of strings
        sample_keys = [
            "app.title",
            "page.evidence_list",
            "message.success",
            "date.medium"
        ]
        
        table = Table(title="Sample Strings", box="rounded")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        
        for key in sample_keys:
            if key in translations:
                table.add_row(key, translations[key])
                
        self.console.print(table)
        self.console.print()
    
    def list_missing_strings(self, locale_code: str, base_language: str = "en-US") -> None:
        """
        List strings missing from a locale compared to another language.
        
        Args:
            locale_code: Locale code to check
            base_language: Base language to compare against
        """
        if locale_code not in self.translations:
            print_error(f"Locale not found: {locale_code}")
            return
            
        if base_language not in self.translations:
            print_error(f"Base language {base_language} not found.")
            return
            
        # Get translations
        locale_strings = self.translations[locale_code]
        base_strings = self.translations[base_language]
        
        # Find missing strings
        missing = []
        for key in base_strings:
            if key not in locale_strings:
                missing.append((key, base_strings[key]))
                
        if not missing:
            print_info(f"No missing strings found in {locale_code}.")
            return
            
        # Display missing strings
        self.console.print()
        self.console.print(f"[bold]Missing strings in {locale_code}:[/bold] {len(missing)}")
        
        table = Table(box="rounded")
        table.add_column("Key", style="bold")
        table.add_column("Base Value")
        
        for key, value in missing:
            table.add_row(key, value)
            
        self.console.print(table)
        self.console.print()


# Initialize a default localization manager
localization_manager = LocalizationManager()

# Helper function for string lookup
def _(key: str, default: Optional[str] = None, **kwargs) -> str:
    """
    Get a localized string by key.
    
    Args:
        key: String key to look up
        default: Default value if key not found
        **kwargs: Format arguments for string interpolation
        
    Returns:
        Localized string
    """
    return localization_manager.get_string(key, default, **kwargs)