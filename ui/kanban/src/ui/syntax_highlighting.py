"""
Syntax Highlighting for Evidence Content.

This module provides syntax highlighting capabilities for code and other
structured content in evidence items.
"""
import logging
import re
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.box import ROUNDED, HEAVY
from rich.text import Text

from .accessibility import accessibility_manager

# Configure module logger
logger = logging.getLogger(__name__)


class SyntaxHighlighter:
    """
    Syntax highlighting for code and structured content in evidence.
    
    This class provides functionality to detect and highlight syntax
    in evidence content based on detected language.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the syntax highlighter.
        
        Args:
            console: Optional console for display
        """
        self.console = console or Console()
        
        # Common language detection patterns
        self.language_patterns = {
            "python": [r"^\s*import\s+", r"^\s*from\s+.*\s+import\s+", r"^\s*def\s+\w+\(.*\):", r"^\s*class\s+\w+.*:"],
            "javascript": [r"^\s*import\s+.*\s+from\s+", r"^\s*const\s+", r"^\s*let\s+", r"^\s*function\s+\w+\(.*\)", r"^\s*export\s+"],
            "java": [r"^\s*(public|private|protected)\s+class", r"^\s*(public|private|protected)\s+.*\s+\w+\(.*\)"],
            "typescript": [r"^\s*interface\s+\w+", r"^\s*type\s+\w+\s*="],
            "html": [r"^\s*<!DOCTYPE\s+html", r"^\s*<html", r"^\s*<head", r"^\s*<body"],
            "sql": [r"^\s*SELECT\s+.*\s+FROM", r"^\s*INSERT\s+INTO", r"^\s*UPDATE\s+.*\s+SET", r"^\s*CREATE\s+TABLE"],
            "markdown": [r"^\s*#\s+", r"^\s*##\s+", r"^\s*\*\*.*\*\*", r"^\s*-\s+"],
            "json": [r"^\s*\{.*\}$", r"^\s*\[.*\]$"],
            "yaml": [r"^\s*\w+:\s+", r"^\s*-\s+\w+:"],
            "shell": [r"^\s*#!/bin/(ba)?sh", r"^\s*export\s+\w+=", r"^\s*if\s+\[\["],
        }
        
        # High contrast themes by language
        self.high_contrast_theme_by_language = {
            "python": "stata-dark",
            "javascript": "solarized-dark",
            "java": "solarized-dark",
            "typescript": "solarized-dark",
            "html": "stata-dark",
            "sql": "xcode-dark",
            "markdown": "stata-dark",
            "json": "solarized-dark",
            "yaml": "solarized-dark",
            "shell": "xcode-dark",
            # Default for other languages
            "default": "solarized-dark"
        }
        
        # Standard themes by language
        self.standard_theme_by_language = {
            "python": "monokai",
            "javascript": "github-dark",
            "java": "github-dark",
            "typescript": "github-dark",
            "html": "default",
            "sql": "default",
            "markdown": "default",
            "json": "github-dark",
            "yaml": "default",
            "shell": "default",
            # Default for other languages
            "default": "default"
        }
        
        logger.info("Initialized syntax highlighter")
    
    def detect_language(self, content: str) -> str:
        """
        Detect the programming language of the content.
        
        Args:
            content: The text content to analyze
            
        Returns:
            Detected language or 'text' if no language detected
        """
        # Early checks for file extension markers
        file_extension_markers = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.html': 'html',
            '.sql': 'sql',
            '.md': 'markdown',
            '.json': 'json',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.sh': 'shell',
            '.java': 'java',
        }
        
        # Check if content contains filename indicators
        for ext, lang in file_extension_markers.items():
            if re.search(rf'\w+\{ext}[:\s]', content[:100]):
                return lang
        
        # Split content into lines for pattern matching
        lines = content.strip().split('\n')
        content_sample = '\n'.join(lines[:20])  # Only check first 20 lines
        
        # Check against language patterns
        matches = {}
        for language, patterns in self.language_patterns.items():
            matches[language] = 0
            for pattern in patterns:
                if re.search(pattern, content_sample, re.MULTILINE):
                    matches[language] += 1
        
        # Return the language with the most matches
        best_match = max(matches.items(), key=lambda x: x[1])
        if best_match[1] > 0:
            return best_match[0]
            
        # Check for JSON structure
        if content.strip().startswith('{') and content.strip().endswith('}'):
            try:
                # This is a simple heuristic, not actually parsing JSON
                if '"' in content or "'" in content:
                    return "json"
            except:
                pass
                
        # Default to plain text
        return "text"
    
    def highlight_content(self, 
                         content: str, 
                         language: Optional[str] = None,
                         title: Optional[str] = None,
                         line_numbers: bool = True) -> None:
        """
        Highlight and display content with syntax highlighting.
        
        Args:
            content: Content to highlight
            language: Language for highlighting (auto-detected if None)
            title: Optional title for the panel
            line_numbers: Whether to show line numbers
        """
        # Detect language if not provided
        if not language or language == "auto":
            language = self.detect_language(content)
            
        # Trim content if very long
        if len(content) > 10000:
            content = content[:10000] + "\n\n... (content truncated) ..."
            
        # Select theme based on accessibility settings
        if accessibility_manager.high_contrast:
            theme = self.high_contrast_theme_by_language.get(
                language, self.high_contrast_theme_by_language["default"]
            )
        else:
            theme = self.standard_theme_by_language.get(
                language, self.standard_theme_by_language["default"]
            )
            
        # Create syntax object
        syntax = Syntax(
            content,
            language,
            theme=theme,
            line_numbers=line_numbers,
            word_wrap=True,
            background_color="default"
        )
        
        # Display with or without panel
        if title:
            box = HEAVY if accessibility_manager.high_contrast else ROUNDED
            panel = Panel(
                syntax,
                title=title,
                border_style="blue",
                box=box
            )
            self.console.print(panel)
        else:
            self.console.print(syntax)
    
    def highlight_from_file(self, 
                           file_path: str, 
                           language: Optional[str] = None,
                           title: Optional[str] = None,
                           line_numbers: bool = True) -> None:
        """
        Load and highlight content from a file.
        
        Args:
            file_path: Path to the file to highlight
            language: Language for highlighting (auto-detected if None)
            title: Optional title for the panel
            line_numbers: Whether to show line numbers
        """
        try:
            # Determine language from file extension if not provided
            if not language:
                suffix = Path(file_path).suffix.lower()
                extension_to_language = {
                    '.py': 'python',
                    '.js': 'javascript',
                    '.ts': 'typescript',
                    '.html': 'html',
                    '.css': 'css',
                    '.sql': 'sql',
                    '.md': 'markdown',
                    '.json': 'json',
                    '.yml': 'yaml',
                    '.yaml': 'yaml',
                    '.sh': 'shell',
                    '.bash': 'shell',
                    '.java': 'java',
                    '.c': 'c',
                    '.cpp': 'cpp',
                    '.cs': 'csharp',
                    '.go': 'go',
                    '.rb': 'ruby',
                    '.php': 'php',
                    '.rs': 'rust',
                    '.swift': 'swift',
                    '.xml': 'xml',
                }
                language = extension_to_language.get(suffix, None)
            
            # Set default title to filename if not provided
            if not title:
                title = Path(file_path).name
                
            # Read and highlight content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.highlight_content(content, language, title, line_numbers)
                
        except Exception as e:
            logger.error(f"Error highlighting file {file_path}: {str(e)}")
            self.console.print(f"[bold red]Error highlighting file:[/bold red] {str(e)}")
    
    def highlight_code_blocks(self, 
                             markdown_content: str,
                             line_numbers: bool = True) -> None:
        """
        Extract and highlight code blocks from markdown content.
        
        Args:
            markdown_content: Markdown content with code blocks
            line_numbers: Whether to show line numbers
        """
        # Regular expression to find code blocks with optional language
        code_block_pattern = r"```(\w+)?\n(.*?)```"
        
        # Find all code blocks
        code_blocks = re.findall(code_block_pattern, markdown_content, re.DOTALL)
        
        if not code_blocks:
            # No code blocks found
            self.console.print("[italic]No code blocks found in content[/italic]")
            return
            
        # Process and highlight each code block
        for i, (language, code) in enumerate(code_blocks, 1):
            language = language.strip() if language else "text"
            title = f"Code Block {i}" + (f" ({language})" if language else "")
            
            self.console.print()
            self.highlight_content(code.strip(), language, title, line_numbers)
            self.console.print()


# Create a singleton instance for importing
syntax_highlighter = SyntaxHighlighter()