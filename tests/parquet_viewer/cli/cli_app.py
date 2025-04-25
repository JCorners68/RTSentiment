#!/usr/bin/env python3
"""
Command Line Interface for the Parquet Query Viewer.

This is the main entry point for the CLI application. It provides both
interactive and command-line query modes for exploring Parquet data.
"""
import argparse
import configparser
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text

from ..core.parquet_data_source import ParquetDataSource
from ..core.query_engine import QueryEngine
from ..core.cache_manager import CacheManager
from ..core.utils import DataFormatter, ExportManager
from .commands import (
    list_tickers,
    list_sources,
    show_schema,
    analyze_ticker,
    compare_tickers,
    export_data,
    search_text,
    show_cache_stats,
    show_recent_trends
)
from .text_viz import (
    display_sentiment_timeline,
    display_sentiment_distribution,
    display_sentiment_calendar,
    display_loading_spinner
)


# Initialize console for rich output
console = Console()


def main():
    """Main entry point for the CLI application."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Parquet Query Viewer CLI")
    
    # Configuration options
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--data-dir", help="Directory containing Parquet files")
    parser.add_argument("--cache-size", type=int, help="Maximum cache size in items")
    parser.add_argument("--cache-ttl", type=int, help="Cache TTL in seconds")
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--interactive", action="store_true", help="Start in interactive mode")
    mode_group.add_argument("--query", help="Execute a query and exit")
    
    # Query options
    parser.add_argument("--ticker", help="Filter by ticker symbol")
    parser.add_argument("--source", help="Filter by data source")
    parser.add_argument("--days", type=int, default=30, help="Number of days to look back")
    parser.add_argument("--sentiment", choices=["positive", "negative", "neutral", "all"], 
                        help="Filter by sentiment type")
    parser.add_argument("--contains", help="Filter text containing this string")
    
    # Action commands
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("--list-tickers", action="store_true", help="List available tickers")
    action_group.add_argument("--list-sources", action="store_true", help="List available data sources")
    action_group.add_argument("--schema", action="store_true", help="Show Parquet schema")
    action_group.add_argument("--analyze", help="Analyze a specific ticker")
    action_group.add_argument("--compare", help="Compare multiple tickers (comma-separated)")
    action_group.add_argument("--trending", action="store_true", help="Show trending tickers")
    action_group.add_argument("--search", help="Search for text in messages")
    
    # Output options
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--format", choices=["csv", "json", "excel"], default="csv", 
                        help="Output format for export")
    parser.add_argument("--no-viz", action="store_true", help="Disable visualizations")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command-line arguments
    if args.data_dir:
        config["data"]["directory"] = args.data_dir
    if args.cache_size:
        config["cache"]["max_size"] = str(args.cache_size)
    if args.cache_ttl:
        config["cache"]["ttl"] = str(args.cache_ttl)
    
    # Initialize components
    try:
        data_source = initialize_data_source(config)
        cache_manager = initialize_cache_manager(config)
        query_engine = initialize_query_engine(data_source, cache_manager)
    except Exception as e:
        console.print(f"[red]Error initializing system: {str(e)}[/red]")
        sys.exit(1)
    
    # Determine mode
    if args.interactive:
        interactive_mode(data_source, query_engine, cache_manager)
    elif args.list_tickers:
        list_tickers(data_source)
    elif args.list_sources:
        list_sources(data_source)
    elif args.schema:
        show_schema(data_source)
    elif args.analyze:
        analyze_ticker(
            query_engine,
            args.analyze,
            days=args.days,
            sources=[args.source] if args.source else None,
            visualize=not args.no_viz
        )
    elif args.compare:
        tickers = [t.strip() for t in args.compare.split(",")]
        compare_tickers(
            query_engine,
            tickers,
            days=args.days,
            visualize=not args.no_viz
        )
    elif args.trending:
        show_recent_trends(query_engine, days=args.days)
    elif args.search:
        search_text(
            query_engine,
            args.search,
            days=args.days,
            ticker=args.ticker
        )
    elif args.query or args.ticker or args.source or args.contains:
        # Build query filters
        filters = build_filters_from_args(args)
        
        # Execute query and display results
        results = query_engine.execute_query(filters=filters)
        
        if args.output:
            # Export results
            export_data(query_engine, args.output, args.format, filters)
        else:
            # Display results
            display_results(results, limit=50)
    else:
        # Default to interactive mode if no specific action
        interactive_mode(data_source, query_engine, cache_manager)


def load_config(config_path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """
    Load configuration from a file or use defaults.
    
    Args:
        config_path: Path to config file
    
    Returns:
        Dictionary with configuration values
    """
    # Default configuration
    default_config = {
        "data": {
            "directory": os.path.join(os.getcwd(), "data/output"),
            "default_lookback_days": "30"
        },
        "cache": {
            "enabled": "true",
            "max_size": "1000",
            "ttl": "3600"  # 1 hour in seconds
        },
        "display": {
            "max_rows": "50",
            "visualizations": "true"
        }
    }
    
    # Create a ConfigParser and set defaults
    config = configparser.ConfigParser()
    
    for section, options in default_config.items():
        config[section] = {}
        for key, value in options.items():
            config[section][key] = value
    
    # Load from file if provided
    if config_path:
        try:
            config.read(config_path)
            console.print(f"[green]Loaded configuration from {config_path}[/green]")
        except Exception as e:
            console.print(f"[yellow]Error loading config from {config_path}: {str(e)}[/yellow]")
            console.print("[yellow]Using default configuration[/yellow]")
    
    # Convert ConfigParser to dict
    result = {}
    for section in config.sections():
        result[section] = dict(config[section])
    
    return result


def initialize_data_source(config: Dict[str, Dict[str, str]]) -> ParquetDataSource:
    """
    Initialize the ParquetDataSource.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Initialized ParquetDataSource
    """
    data_dir = config["data"]["directory"]
    
    # Check if directory exists
    if not os.path.isdir(data_dir):
        raise ValueError(f"Data directory not found: {data_dir}")
    
    # Initialize data source
    with display_loading_spinner("Initializing data source..."):
        data_source = ParquetDataSource(data_dir)
    
    console.print(f"[green]Initialized ParquetDataSource with {len(data_source.get_all_tickers())} tickers[/green]")
    return data_source


def initialize_cache_manager(config: Dict[str, Dict[str, str]]) -> CacheManager:
    """
    Initialize the CacheManager.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Initialized CacheManager
    """
    enabled = config["cache"].get("enabled", "true").lower() == "true"
    max_size = int(config["cache"].get("max_size", "1000"))
    ttl = int(config["cache"].get("ttl", "3600"))
    
    cache_manager = CacheManager(
        enabled=enabled,
        max_size=max_size,
        ttl=ttl
    )
    
    console.print(f"[green]Initialized CacheManager (enabled={enabled}, max_size={max_size}, ttl={ttl}s)[/green]")
    return cache_manager


def initialize_query_engine(
    data_source: ParquetDataSource,
    cache_manager: CacheManager
) -> QueryEngine:
    """
    Initialize the QueryEngine.
    
    Args:
        data_source: ParquetDataSource instance
        cache_manager: CacheManager instance
    
    Returns:
        Initialized QueryEngine
    """
    query_engine = QueryEngine(
        data_source=data_source,
        cache_manager=cache_manager
    )
    
    console.print("[green]Initialized QueryEngine[/green]")
    return query_engine


def build_filters_from_args(args) -> Dict[str, Any]:
    """
    Build query filters from command-line arguments.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Dictionary with query filters
    """
    filters = {}
    
    # Ticker filter
    if args.ticker:
        filters["ticker"] = args.ticker
    
    # Source filter
    if args.source:
        filters["source"] = args.source
    
    # Date range filter
    if args.days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        filters["date_range"] = (start_date, end_date)
    
    # Sentiment filter
    if args.sentiment:
        if args.sentiment == "positive":
            filters["sentiment_range"] = (0.01, 1.0)
        elif args.sentiment == "negative":
            filters["sentiment_range"] = (-1.0, -0.01)
        elif args.sentiment == "neutral":
            filters["sentiment_range"] = (-0.01, 0.01)
    
    # Text contains filter
    if args.contains:
        filters["text_contains"] = args.contains
    
    return filters


def interactive_mode(
    data_source: ParquetDataSource,
    query_engine: QueryEngine,
    cache_manager: CacheManager
) -> None:
    """
    Run the CLI in interactive mode.
    
    Args:
        data_source: ParquetDataSource instance
        query_engine: QueryEngine instance
        cache_manager: CacheManager instance
    """
    console.print(Panel(
        "[bold]Welcome to the Parquet Query Viewer CLI[/bold]\n\n"
        "This tool allows you to explore sentiment data stored in Parquet files.\n"
        "Type 'help' to see available commands or 'exit' to quit.",
        title="Interactive Mode",
        border_style="green"
    ))
    
    while True:
        try:
            # Get command from user
            command = Prompt.ask("[bold cyan]pqv>[/bold cyan]").strip().lower()
            
            if command in ("exit", "quit", "q"):
                break
            elif command in ("help", "?", "h"):
                display_help()
            elif command in ("tickers", "list-tickers", "lt"):
                list_tickers(data_source)
            elif command in ("sources", "list-sources", "ls"):
                list_sources(data_source)
            elif command in ("schema", "show-schema", "s"):
                show_schema(data_source)
            elif command in ("trending", "trend", "tr"):
                days = Prompt.ask("Number of days to look back", default="7")
                show_recent_trends(query_engine, days=int(days))
            elif command in ("cache", "cache-stats", "cs"):
                show_cache_stats(cache_manager)
            elif command.startswith("analyze ") or command.startswith("a "):
                # Extract ticker from command
                parts = command.split(" ", 1)
                if len(parts) > 1 and parts[1]:
                    ticker = parts[1].strip().upper()
                    days = Prompt.ask("Number of days to look back", default="30")
                    source = Prompt.ask("Filter by source (leave empty for all)")
                    sources = [source] if source else None
                    analyze_ticker(query_engine, ticker, days=int(days), sources=sources)
                else:
                    console.print("[yellow]Please specify a ticker to analyze[/yellow]")
            elif command.startswith("compare ") or command.startswith("c "):
                # Extract tickers from command
                parts = command.split(" ", 1)
                if len(parts) > 1 and parts[1]:
                    tickers_str = parts[1].strip().upper()
                    tickers = [t.strip() for t in tickers_str.split(",")]
                    if tickers:
                        days = Prompt.ask("Number of days to look back", default="30")
                        compare_tickers(query_engine, tickers, days=int(days))
                    else:
                        console.print("[yellow]Please specify tickers to compare[/yellow]")
                else:
                    console.print("[yellow]Please specify tickers to compare[/yellow]")
            elif command.startswith("search ") or command.startswith("find "):
                # Extract search text from command
                parts = command.split(" ", 1)
                if len(parts) > 1 and parts[1]:
                    search_term = parts[1].strip()
                    days = Prompt.ask("Number of days to look back", default="30")
                    ticker = Prompt.ask("Filter by ticker (leave empty for all)")
                    ticker = ticker if ticker else None
                    search_text(query_engine, search_term, days=int(days), ticker=ticker)
                else:
                    console.print("[yellow]Please specify text to search for[/yellow]")
            elif command.startswith("query ") or command.startswith("q "):
                # Parse and execute a custom query
                query_str = command.split(" ", 1)[1].strip()
                filters = parse_query_string(query_str)
                
                if filters:
                    results = query_engine.execute_query(filters=filters)
                    display_results(results)
                    
                    if not results.empty and Confirm.ask("Export results?"):
                        output_path = Prompt.ask("Output file path")
                        format_str = Prompt.ask("Format", choices=["csv", "json", "excel"], default="csv")
                        export_data(query_engine, output_path, format_str, filters)
                else:
                    console.print("[yellow]Invalid query format[/yellow]")
            elif command.startswith("export ") or command.startswith("e "):
                # Extract export parameters
                parts = command.split(" ", 1)
                if len(parts) > 1 and parts[1]:
                    output_path = parts[1].strip()
                    format_str = Prompt.ask("Format", choices=["csv", "json", "excel"], default="csv")
                    
                    # Build export filters
                    ticker = Prompt.ask("Filter by ticker (leave empty for all)")
                    source = Prompt.ask("Filter by source (leave empty for all)")
                    days = Prompt.ask("Number of days to look back", default="30")
                    
                    filters = {}
                    if ticker:
                        filters["ticker"] = ticker
                    if source:
                        filters["source"] = source
                    
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=int(days))
                    filters["date_range"] = (start_date, end_date)
                    
                    export_data(query_engine, output_path, format_str, filters)
                else:
                    console.print("[yellow]Please specify an output path[/yellow]")
            elif command.startswith("calendar ") or command.startswith("cal "):
                # Extract ticker for calendar view
                parts = command.split(" ", 1)
                if len(parts) > 1 and parts[1]:
                    ticker = parts[1].strip().upper()
                    year = Prompt.ask("Year", default=str(datetime.now().year))
                    month = Prompt.ask("Month (1-12)", default=str(datetime.now().month))
                    
                    # Query data for this ticker
                    filters = {"ticker": ticker}
                    results = query_engine.execute_query(filters=filters)
                    
                    if not results.empty:
                        display_sentiment_calendar(results, year=int(year), month=int(month))
                    else:
                        console.print(f"[yellow]No data found for ticker {ticker}[/yellow]")
                else:
                    console.print("[yellow]Please specify a ticker for the calendar view[/yellow]")
            else:
                console.print("[yellow]Unknown command. Type 'help' to see available commands.[/yellow]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


def display_help() -> None:
    """Display help information for the interactive mode."""
    help_panel = Panel(
        "\n[bold]Available Commands:[/bold]\n\n"
        "  [cyan]help, ?, h[/cyan]                  Show this help message\n"
        "  [cyan]exit, quit, q[/cyan]               Exit the application\n"
        "  [cyan]tickers, list-tickers, lt[/cyan]   List available tickers\n"
        "  [cyan]sources, list-sources, ls[/cyan]   List available data sources\n"
        "  [cyan]schema, show-schema, s[/cyan]      Show Parquet file schema\n"
        "  [cyan]trending, trend, tr[/cyan]         Show trending tickers\n"
        "  [cyan]cache, cache-stats, cs[/cyan]      Show cache statistics\n"
        "  [cyan]analyze TICKER, a TICKER[/cyan]    Analyze sentiment for a ticker\n"
        "  [cyan]compare T1,T2,.., c T1,T2,..[/cyan] Compare multiple tickers\n"
        "  [cyan]search TEXT, find TEXT[/cyan]      Search for text in messages\n"
        "  [cyan]query EXPR, q EXPR[/cyan]          Execute a custom query\n"
        "  [cyan]export PATH, e PATH[/cyan]         Export data to a file\n"
        "  [cyan]calendar TICKER, cal TICKER[/cyan] Show calendar view for a ticker\n\n"
        "[bold]Query Expression Format:[/bold]\n"
        "  ticker=AAPL source=reddit days=30 sentiment=positive text=\"earnings\"\n"
        "  Multiple values: ticker=AAPL,MSFT,GOOGL\n\n"
        "[bold]Examples:[/bold]\n"
        "  [cyan]analyze AAPL[/cyan]                Analyze AAPL sentiment\n"
        "  [cyan]compare AAPL,MSFT,GOOGL[/cyan]     Compare multiple tickers\n"
        "  [cyan]search \"earnings report\"[/cyan]    Find messages with this text\n"
        "  [cyan]q ticker=AAPL days=7[/cyan]        Query AAPL data for last 7 days\n",
        title="Parquet Query Viewer Help",
        border_style="green"
    )
    
    console.print(help_panel)


def parse_query_string(query_str: str) -> Dict[str, Any]:
    """
    Parse a query string into filter parameters.
    
    Args:
        query_str: Query string in format "param1=value1 param2=value2"
    
    Returns:
        Dictionary with query filters
    """
    filters = {}
    
    # Extract quoted strings first to handle spaces
    quoted_texts = re.findall(r'"([^"]*)"', query_str)
    for i, text in enumerate(quoted_texts):
        query_str = query_str.replace(f'"{text}"', f'__QUOTED_TEXT_{i}__', 1)
    
    # Split by spaces not inside quotes
    parts = query_str.split()
    
    for part in parts:
        if "=" not in part:
            continue
            
        param, value = part.split("=", 1)
        param = param.lower().strip()
        
        # Restore quoted texts
        for i, text in enumerate(quoted_texts):
            value = value.replace(f'__QUOTED_TEXT_{i}__', text)
        
        if param == "ticker":
            if "," in value:
                filters["ticker"] = [t.strip().upper() for t in value.split(",")]
            else:
                filters["ticker"] = value.strip().upper()
        elif param == "source":
            if "," in value:
                filters["source"] = [s.strip() for s in value.split(",")]
            else:
                filters["source"] = value.strip()
        elif param == "days":
            try:
                days = int(value)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                filters["date_range"] = (start_date, end_date)
            except ValueError:
                pass
        elif param == "sentiment":
            if value.lower() == "positive":
                filters["sentiment_range"] = (0.01, 1.0)
            elif value.lower() == "negative":
                filters["sentiment_range"] = (-1.0, -0.01)
            elif value.lower() == "neutral":
                filters["sentiment_range"] = (-0.01, 0.01)
            elif ":" in value:
                try:
                    min_val, max_val = value.split(":", 1)
                    filters["sentiment_range"] = (float(min_val), float(max_val))
                except ValueError:
                    pass
        elif param == "text":
            filters["text_contains"] = value
    
    return filters


def display_results(df: pd.DataFrame, limit: int = 50) -> None:
    """
    Display query results in a formatted table.
    
    Args:
        df: DataFrame with results
        limit: Maximum number of rows to display
    """
    if df.empty:
        console.print("[yellow]No results found matching the query criteria[/yellow]")
        return
    
    # Limit rows for display
    display_df = df.head(limit) if len(df) > limit else df
    
    # Create table
    table = Table(title=f"Query Results ({len(df)} records found, showing {len(display_df)})")
    
    # Determine columns to show based on what's in the DataFrame
    display_columns = []
    
    priority_columns = ["timestamp", "ticker", "source", "sentiment", "text"]
    for col in priority_columns:
        if col in df.columns:
            display_columns.append(col)
    
    # Add remaining columns (up to a reasonable limit)
    max_columns = 8
    for col in df.columns:
        if col not in display_columns and len(display_columns) < max_columns:
            display_columns.append(col)
    
    # Add columns to table
    column_styles = {
        "timestamp": "cyan",
        "ticker": "green",
        "source": "magenta",
        "sentiment": "yellow",
        "text": "white"
    }
    
    for col in display_columns:
        width = 20 if col == "text" else None
        style = column_styles.get(col, "white")
        table.add_column(col, style=style, width=width)
    
    # Add data rows
    for _, row in display_df.iterrows():
        row_data = []
        
        for col in display_columns:
            value = row.get(col, "")
            
            # Format timestamp
            if col == "timestamp" and hasattr(value, "strftime"):
                value = value.strftime("%Y-%m-%d %H:%M")
            
            # Format sentiment with color
            elif col == "sentiment":
                color = "green" if value > 0 else "red" if value < 0 else "white"
                value = f"[{color}]{value:.4f}[/{color}]"
            
            # Format text (truncate if too long)
            elif col == "text" and isinstance(value, str) and len(value) > 60:
                value = value[:57] + "..."
            
            row_data.append(str(value))
        
        table.add_row(*row_data)
    
    console.print(table)
    
    # Show warning if truncated
    if len(df) > limit:
        console.print(f"[yellow]Showing {limit} of {len(df)} results. Use export to save all results.[/yellow]")
    
    # Show quick stats
    display_stats(df)


def display_stats(df: pd.DataFrame) -> None:
    """
    Display statistics about the query results.
    
    Args:
        df: DataFrame with results
    """
    if "sentiment" not in df.columns:
        return
    
    # Calculate statistics
    stats = {
        "Mean Sentiment": df["sentiment"].mean(),
        "Median Sentiment": df["sentiment"].median(),
        "Std Dev": df["sentiment"].std(),
        "Min": df["sentiment"].min(),
        "Max": df["sentiment"].max(),
        "Total Records": len(df),
        "Positive %": len(df[df["sentiment"] > 0]) / len(df) * 100,
        "Negative %": len(df[df["sentiment"] < 0]) / len(df) * 100,
        "Neutral %": len(df[df["sentiment"] == 0]) / len(df) * 100
    }
    
    # Source distribution if available
    if "source" in df.columns:
        source_counts = df["source"].value_counts()
        top_source = source_counts.index[0] if not source_counts.empty else "N/A"
        stats["Top Source"] = f"{top_source} ({source_counts.iloc[0]} records)"
    
    # Create stats panel
    stats_text = " | ".join([
        f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}"
        for k, v in stats.items()
    ])
    
    console.print(Panel(stats_text, title="Summary Statistics", border_style="cyan"))


def parse_date_range(date_range_str: str) -> Tuple[datetime, datetime]:
    """
    Parse a date range string into start and end dates.
    
    Args:
        date_range_str: String representing a date range
    
    Returns:
        Tuple of (start_date, end_date)
    
    Supported formats:
    - "30d" or "30 days": Last 30 days
    - "12h" or "12 hours": Last 12 hours 
    - "6w" or "6 weeks": Last 6 weeks
    - "YYYY-MM-DD:YYYY-MM-DD": Specific date range
    """
    now = datetime.now()
    
    # Check for relative time format
    days_match = re.match(r"^(\d+)(?:\s*)?d(?:ays?)?$", date_range_str)
    hours_match = re.match(r"^(\d+)(?:\s*)?h(?:ours?)?$", date_range_str)
    weeks_match = re.match(r"^(\d+)(?:\s*)?w(?:eeks?)?$", date_range_str)
    
    if days_match:
        days = int(days_match.group(1))
        return now - timedelta(days=days), now
    elif hours_match:
        hours = int(hours_match.group(1))
        return now - timedelta(hours=hours), now
    elif weeks_match:
        weeks = int(weeks_match.group(1))
        return now - timedelta(weeks=weeks), now
    
    # Check for absolute date range
    date_range_parts = date_range_str.split(":")
    if len(date_range_parts) == 2:
        try:
            start_date = datetime.strptime(date_range_parts[0], "%Y-%m-%d")
            end_date = datetime.strptime(date_range_parts[1], "%Y-%m-%d")
            # Set end date to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59)
            return start_date, end_date
        except ValueError:
            pass
    
    # Default to last 30 days
    return now - timedelta(days=30), now


def format_sentiment_score(score: float) -> str:
    """
    Format a sentiment score with color based on value.
    
    Args:
        score: Sentiment score (-1 to 1)
    
    Returns:
        Formatted string with color
    """
    if score > 0.5:
        return f"[bright_green]{score:.4f}[/bright_green]"
    elif score > 0:
        return f"[green]{score:.4f}[/green]"
    elif score < -0.5:
        return f"[bright_red]{score:.4f}[/bright_red]"
    elif score < 0:
        return f"[red]{score:.4f}[/red]"
    else:
        return f"[white]{score:.4f}[/white]"


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)