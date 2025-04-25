#!/usr/bin/env python3
"""
Command-line interface for querying Parquet files.
"""
import argparse
import logging
import os
import sys
import json
import csv
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc
import rich
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.panel import Panel
from rich.progress import Progress
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("parquet_query")

console = Console()

class ParquetQuery:
    """CLI tool for querying Parquet files."""
    
    def __init__(self, config=None):
        """
        Initialize the Parquet query tool.
        
        Args:
            config: Configuration dictionary or path to config file
        """
        # Load configuration
        self.config = self._load_config(config)
        
        # Setup paths
        self.parquet_dir = self.config.get("parquet_dir", "./data/output")
        self.export_dir = self.config.get("export_dir", "./data/exports")
        
        # Ensure directories exist
        os.makedirs(self.parquet_dir, exist_ok=True)
        os.makedirs(self.export_dir, exist_ok=True)
        
        # Cache for schema and table information
        self.schema_cache = {}
        self.table_cache = {}
        
        # Initialize available files
        self.available_files = self._get_available_files()
        
        logger.info(f"Initialized Parquet Query with {len(self.available_files)} available files")
    
    def _load_config(self, config) -> Dict[str, Any]:
        """
        Load configuration from file or dictionary.
        
        Args:
            config: Configuration dictionary or path to config file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "parquet_dir": "./data/output",
            "export_dir": "./data/exports",
            "default_limit": 100,
            "cache_schema": True,
            "pretty_print": True,
            "color_output": True,
            "date_format": "%Y-%m-%d %H:%M:%S"
        }
        
        if not config:
            return default_config
        
        if isinstance(config, str):
            # Load from file
            if os.path.exists(config):
                try:
                    with open(config, 'r') as f:
                        if config.endswith('.json'):
                            loaded_config = json.load(f)
                        else:
                            # Assume it's a Python-style config
                            import configparser
                            parser = configparser.ConfigParser()
                            parser.read(config)
                            loaded_config = {s: dict(parser.items(s)) for s in parser.sections()}
                            if 'DEFAULT' in loaded_config:
                                loaded_config.update(loaded_config.pop('DEFAULT'))
                    
                    default_config.update(loaded_config)
                except Exception as e:
                    logger.error(f"Error loading config file: {e}")
        elif isinstance(config, dict):
            # Use provided dictionary
            default_config.update(config)
        
        return default_config
    
    def _get_available_files(self) -> List[str]:
        """
        Get list of available Parquet files.
        
        Returns:
            List of Parquet file paths
        """
        files = []
        
        try:
            for root, dirs, filenames in os.walk(self.parquet_dir):
                for filename in filenames:
                    if filename.endswith('.parquet'):
                        files.append(os.path.join(root, filename))
        except Exception as e:
            logger.error(f"Error scanning for Parquet files: {e}")
        
        return files
    
    def refresh_files(self):
        """Refresh the list of available Parquet files."""
        self.available_files = self._get_available_files()
        logger.info(f"Refreshed file list: {len(self.available_files)} Parquet files available")
    
    def get_schema(self, file_path: str) -> Optional[pa.Schema]:
        """
        Get the schema for a Parquet file.
        
        Args:
            file_path: Path to the Parquet file
            
        Returns:
            PyArrow schema or None if error
        """
        if file_path in self.schema_cache:
            return self.schema_cache[file_path]
        
        try:
            schema = pq.read_schema(file_path)
            
            # Cache the schema if caching is enabled
            if self.config.get("cache_schema", True):
                self.schema_cache[file_path] = schema
            
            return schema
        except Exception as e:
            logger.error(f"Error reading schema for {file_path}: {e}")
            return None
    
    def list_tables(self) -> List[Dict[str, Any]]:
        """
        List available Parquet tables with basic information.
        
        Returns:
            List of dictionaries with table information
        """
        tables = []
        
        for file_path in self.available_files:
            table_name = os.path.basename(file_path).replace('.parquet', '')
            
            try:
                # Get file stats
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Get Parquet metadata
                metadata = pq.read_metadata(file_path)
                row_count = metadata.num_rows
                
                # Get schema
                schema = self.get_schema(file_path)
                columns = [field.name for field in schema] if schema else []
                
                tables.append({
                    "name": table_name,
                    "path": file_path,
                    "size": file_size,
                    "size_human": self._format_size(file_size),
                    "rows": row_count,
                    "columns": columns,
                    "column_count": len(columns),
                    "last_modified": file_time
                })
            except Exception as e:
                logger.error(f"Error reading metadata for {file_path}: {e}")
                tables.append({
                    "name": table_name,
                    "path": file_path,
                    "error": str(e)
                })
        
        return tables
    
    def _format_size(self, size: int) -> str:
        """
        Format file size in a human-readable format.
        
        Args:
            size: File size in bytes
            
        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024 or unit == 'TB':
                return f"{size:.2f} {unit}"
            size /= 1024
    
    def filter_data(self, table: pa.Table, filter_query: str) -> pa.Table:
        """
        Filter data using a simple query language.
        
        Args:
            table: PyArrow table
            filter_query: Filter query string (e.g., "sentiment > 0.5 AND source = 'twitter'")
            
        Returns:
            Filtered PyArrow table
        """
        if not filter_query:
            return table
        
        # Simple parsing of filter query
        # This is a basic implementation that could be extended
        
        # Split by AND/OR, preserving quoted strings
        def split_preserving_quotes(s, delimiters):
            pattern = '|'.join(map(re.escape, delimiters))
            tokens = []
            current = ''
            in_quotes = False
            
            for char in s:
                if char == '"' or char == "'":
                    in_quotes = not in_quotes
                    current += char
                elif not in_quotes and re.match(pattern, char):
                    if current.strip():
                        tokens.append(current.strip())
                    tokens.append(char)
                    current = ''
                else:
                    current += char
            
            if current.strip():
                tokens.append(current.strip())
            
            return tokens
        
        # Parse the query into a PyArrow compute expression
        try:
            # Tokenize the query
            tokens = split_preserving_quotes(filter_query, ['AND', 'OR', '(', ')'])
            
            # Process tokens to build a compute expression
            # This is simplified and would need to be expanded for a real query parser
            expressions = []
            operators = []
            
            for token in tokens:
                if token in ('AND', 'OR', '(', ')'):
                    operators.append(token)
                else:
                    # Parse condition (e.g., "sentiment > 0.5")
                    condition_match = re.match(r'(\w+)\s*([=><~!]+)\s*(.+)', token)
                    if condition_match:
                        col, op, val = condition_match.groups()
                        
                        # Clean and parse value
                        val = val.strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]  # Remove quotes
                        else:
                            # Try to convert to appropriate type
                            try:
                                if '.' in val:
                                    val = float(val)
                                else:
                                    val = int(val)
                            except ValueError:
                                pass  # Keep as string
                        
                        # Build condition
                        column = table[col]
                        if op == '=':
                            expr = pc.equal(column, val)
                        elif op == '!=':
                            expr = pc.not_equal(column, val)
                        elif op == '>':
                            expr = pc.greater(column, val)
                        elif op == '>=':
                            expr = pc.greater_equal(column, val)
                        elif op == '<':
                            expr = pc.less(column, val)
                        elif op == '<=':
                            expr = pc.less_equal(column, val)
                        elif op == '~':
                            # Contains operation (simple string contains)
                            if isinstance(val, str):
                                expr = pc.match_substring(column, val)
                            else:
                                raise ValueError(f"Invalid value for contains operation: {val}")
                        else:
                            raise ValueError(f"Unsupported operator: {op}")
                        
                        expressions.append(expr)
            
            # Combine expressions (simplified - only supports AND for now)
            if not expressions:
                return table
            
            final_expr = expressions[0]
            for i in range(1, len(expressions)):
                final_expr = pc.and_(final_expr, expressions[i])
            
            # Apply filter
            return pc.filter(table, final_expr)
        except Exception as e:
            logger.error(f"Error filtering data: {e}")
            return table
    
    def query_parquet(self, file_path: str, columns=None, filters=None, limit=None, sort_by=None, sort_ascending=True) -> Optional[pd.DataFrame]:
        """
        Query a Parquet file with optional filtering and sorting.
        
        Args:
            file_path: Path to the Parquet file
            columns: List of columns to select (default: all)
            filters: Filter condition string
            limit: Maximum number of rows to return
            sort_by: Column to sort by
            sort_ascending: Sort in ascending order if True
            
        Returns:
            Pandas DataFrame with query results or None if error
        """
        try:
            # Use PyArrow to read and filter data
            table = pq.read_table(file_path)
            
            # Apply column projection
            if columns:
                try:
                    # Handle cases where requested columns don't exist
                    existing_columns = [col for col in columns if col in table.column_names]
                    if not existing_columns:
                        logger.warning(f"None of the requested columns {columns} exist in the table")
                        return pd.DataFrame()
                    
                    table = table.select(existing_columns)
                except Exception as e:
                    logger.error(f"Error selecting columns {columns}: {e}")
            
            # Apply filters
            if filters:
                table = self.filter_data(table, filters)
            
            # Convert to pandas for easier sorting and limiting
            df = table.to_pandas()
            
            # Apply sorting
            if sort_by:
                if sort_by in df.columns:
                    df = df.sort_values(by=sort_by, ascending=sort_ascending)
                else:
                    logger.warning(f"Sort column '{sort_by}' not found, ignoring sort")
            
            # Apply limit
            if limit:
                df = df.head(limit)
            
            return df
        except Exception as e:
            logger.error(f"Error querying Parquet file {file_path}: {e}")
            return None
    
    def export_results(self, df: pd.DataFrame, format: str, output_path: str) -> bool:
        """
        Export query results to a file.
        
        Args:
            df: Pandas DataFrame with results
            format: Export format ('csv', 'json', 'parquet', 'excel')
            output_path: Path to save the exported file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Export based on format
            if format.lower() == 'csv':
                df.to_csv(output_path, index=False)
            elif format.lower() == 'json':
                df.to_json(output_path, orient='records', date_format='iso')
            elif format.lower() == 'parquet':
                df.to_parquet(output_path, index=False)
            elif format.lower() == 'excel':
                df.to_excel(output_path, index=False)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
            
            logger.info(f"Exported {len(df)} rows to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            return False
    
    def display_results(self, df: pd.DataFrame, limit=None):
        """
        Display query results in a formatted table.
        
        Args:
            df: Pandas DataFrame with results
            limit: Maximum number of rows to display
        """
        if df is None or df.empty:
            console.print("[yellow]No results found[/yellow]")
            return
        
        # Apply limit for display
        if limit and len(df) > limit:
            display_df = df.head(limit)
            console.print(f"[yellow]Showing {limit} of {len(df)} rows[/yellow]")
        else:
            display_df = df
        
        # Create a table
        table = Table(show_header=True, header_style="bold blue")
        
        # Add columns
        for column in display_df.columns:
            table.add_column(column)
        
        # Add rows
        for _, row in display_df.iterrows():
            table.add_row(*[str(val) for val in row.values])
        
        # Display the table
        console.print(table)
    
    def run_query(self, query: str) -> Optional[pd.DataFrame]:
        """
        Run a query on Parquet files.
        
        Args:
            query: SQL-like query string
            
        Returns:
            Pandas DataFrame with results or None if error
        """
        # Parse the query (simple parsing for demonstration)
        query = query.strip()
        
        # Handle special commands
        if query.lower() == 'list tables':
            tables = self.list_tables()
            if not tables:
                console.print("[yellow]No tables found[/yellow]")
                return None
            
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Table Name")
            table.add_column("Rows")
            table.add_column("Columns")
            table.add_column("Size")
            table.add_column("Last Modified")
            
            for t in tables:
                table.add_row(
                    t["name"],
                    str(t.get("rows", "N/A")),
                    str(t.get("column_count", "N/A")),
                    t.get("size_human", "N/A"),
                    t.get("last_modified", "N/A").strftime("%Y-%m-%d %H:%M:%S") if "last_modified" in t else "N/A"
                )
            
            console.print(table)
            return None
        
        if query.lower().startswith('show schema'):
            parts = query.split(maxsplit=2)
            if len(parts) != 3:
                console.print("[red]Error: Usage is 'SHOW SCHEMA table_name'[/red]")
                return None
            
            table_name = parts[2]
            file_path = None
            
            # Find the file path
            for f in self.available_files:
                if os.path.basename(f).replace('.parquet', '') == table_name:
                    file_path = f
                    break
            
            if not file_path:
                console.print(f"[red]Error: Table '{table_name}' not found[/red]")
                return None
            
            schema = self.get_schema(file_path)
            if not schema:
                console.print(f"[red]Error: Could not read schema for '{table_name}'[/red]")
                return None
            
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Field")
            table.add_column("Type")
            
            for field in schema:
                table.add_row(field.name, str(field.type))
            
            console.print(Panel(table, title=f"Schema for {table_name}"))
            return None
        
        # Parse SELECT query
        select_match = re.match(r'SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*?))?(?:\s+ORDER\s+BY\s+(.*?)(?:\s+(ASC|DESC))?)?(?:\s+LIMIT\s+(\d+))?$', query, re.IGNORECASE)
        
        if not select_match:
            console.print("[red]Error: Invalid query format. Expected: SELECT columns FROM table [WHERE conditions] [ORDER BY column [ASC|DESC]] [LIMIT n][/red]")
            return None
        
        columns_str, table_name, where_clause, order_by, order_direction, limit_str = select_match.groups()
        
        # Process columns
        if columns_str.strip() == '*':
            columns = None  # All columns
        else:
            columns = [col.strip() for col in columns_str.split(',')]
        
        # Find the file path
        file_path = None
        for f in self.available_files:
            if os.path.basename(f).replace('.parquet', '') == table_name:
                file_path = f
                break
        
        if not file_path:
            console.print(f"[red]Error: Table '{table_name}' not found[/red]")
            return None
        
        # Process limit
        limit = int(limit_str) if limit_str else self.config.get("default_limit", 100)
        
        # Process order
        sort_ascending = True if not order_direction or order_direction.upper() == 'ASC' else False
        
        # Execute the query
        with Progress() as progress:
            task = progress.add_task("[cyan]Executing query...", total=None)
            result = self.query_parquet(
                file_path=file_path,
                columns=columns,
                filters=where_clause,
                limit=limit,
                sort_by=order_by,
                sort_ascending=sort_ascending
            )
            progress.update(task, completed=100)
        
        return result
    
    def interactive_mode(self):
        """Run the CLI in interactive mode."""
        console.print(Panel.fit(
            "[bold green]Parquet Query CLI[/bold green]\n"
            "Type SQL-like queries to explore Parquet files.\n"
            "Examples:\n"
            "  [cyan]list tables[/cyan] - List available tables\n"
            "  [cyan]show schema table_name[/cyan] - Show table schema\n"
            "  [cyan]SELECT * FROM table_name LIMIT 10[/cyan] - Query a table\n"
            "  [cyan]SELECT col1, col2 FROM table_name WHERE col1 > 0.5 ORDER BY col2 DESC[/cyan]\n"
            "  [cyan]exit[/cyan] or [cyan]quit[/cyan] - Exit the CLI"
        ))
        
        while True:
            try:
                query = Prompt.ask("\n[bold green]parquet-query[/bold green]> ")
                
                if query.lower() in ('exit', 'quit', 'q'):
                    break
                
                if not query.strip():
                    continue
                
                # Execute the query
                result = self.run_query(query)
                
                # Display the results
                if result is not None:
                    self.display_results(result)
            except KeyboardInterrupt:
                console.print("\n[yellow]Query interrupted[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    def run_query_file(self, query_file: str, output_file=None, output_format='csv'):
        """
        Run queries from a file.
        
        Args:
            query_file: Path to file containing queries
            output_file: Path to save the results
            output_format: Output file format
        """
        try:
            with open(query_file, 'r') as f:
                queries = f.read().strip().split(';')
            
            results = []
            
            for i, query in enumerate(queries):
                query = query.strip()
                if not query:
                    continue
                
                console.print(f"[cyan]Executing query {i+1}/{len(queries)}:[/cyan] {query}")
                result = self.run_query(query)
                
                if result is not None:
                    self.display_results(result)
                    results.append(result)
            
            # Save results if output_file is specified
            if output_file and results:
                # Combine all results (if multiple queries)
                combined_result = pd.concat(results) if len(results) > 1 else results[0]
                
                # Export the results
                self.export_results(combined_result, output_format, output_file)
                console.print(f"[green]Results saved to {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]Error running query file: {e}[/red]")


def main():
    """Main function for CLI."""
    parser = argparse.ArgumentParser(description='Parquet Query CLI')
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--query', '-q', help='Query to execute')
    parser.add_argument('--query-file', '-f', help='File containing queries to execute')
    parser.add_argument('--output', '-o', help='Output file for query results')
    parser.add_argument('--format', default='csv', choices=['csv', 'json', 'parquet', 'excel'], help='Output format')
    parser.add_argument('--limit', type=int, help='Limit number of results')
    
    args = parser.parse_args()
    
    # Create Parquet Query instance
    config = {}
    if args.config:
        config = args.config
    if args.limit:
        config['default_limit'] = args.limit
    
    pq_cli = ParquetQuery(config)
    
    if args.query:
        # Run a single query
        result = pq_cli.run_query(args.query)
        
        if result is not None:
            pq_cli.display_results(result)
            
            if args.output:
                pq_cli.export_results(result, args.format, args.output)
                console.print(f"[green]Results saved to {args.output}[/green]")
    elif args.query_file:
        # Run queries from a file
        pq_cli.run_query_file(args.query_file, args.output, args.format)
    else:
        # Run in interactive mode
        pq_cli.interactive_mode()


if __name__ == "__main__":
    main()