"""
Commands for the Parquet Query Viewer CLI.

This module contains the implementations of various commands available in the CLI.
Each command is implemented as a function that takes appropriate arguments and
performs the corresponding operation using the query engine.
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..core.parquet_data_source import ParquetDataSource
from ..core.query_engine import QueryEngine
from ..core.cache_manager import CacheManager
from .text_viz import (
    display_sentiment_timeline,
    display_sentiment_distribution,
    display_source_distribution,
    display_sentiment_heatmap
)


# Initialize console for rich output
console = Console()


def list_tickers(data_source: ParquetDataSource, limit: int = 20) -> None:
    """
    List all available tickers in the data source.
    
    Args:
        data_source: The ParquetDataSource to query
        limit: Maximum number of tickers to display
    """
    tickers = data_source.get_all_tickers()
    
    table = Table(title="Available Tickers")
    table.add_column("Ticker", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Avg Sentiment", style="yellow")
    
    # Sort tickers by count (descending)
    ticker_stats = []
    for ticker in tickers:
        count = data_source.get_ticker_count(ticker)
        avg_sentiment = data_source.get_ticker_avg_sentiment(ticker)
        ticker_stats.append((ticker, count, avg_sentiment))
    
    ticker_stats.sort(key=lambda x: x[1], reverse=True)
    
    for ticker, count, avg_sentiment in ticker_stats[:limit]:
        sentiment_color = "green" if avg_sentiment > 0 else "red"
        table.add_row(
            ticker,
            str(count),
            f"[{sentiment_color}]{avg_sentiment:.4f}[/{sentiment_color}]"
        )
    
    console.print(table)
    console.print(f"Showing {min(limit, len(ticker_stats))} of {len(ticker_stats)} tickers")


def list_sources(data_source: ParquetDataSource) -> None:
    """
    List all available data sources and their statistics.
    
    Args:
        data_source: The ParquetDataSource to query
    """
    sources = data_source.get_all_sources()
    
    table = Table(title="Available Data Sources")
    table.add_column("Source", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Date Range", style="yellow")
    table.add_column("Avg Sentiment", style="magenta")
    
    for source in sources:
        count = data_source.get_source_count(source)
        date_range = data_source.get_source_date_range(source)
        avg_sentiment = data_source.get_source_avg_sentiment(source)
        
        date_str = f"{date_range[0]} to {date_range[1]}" if date_range else "N/A"
        sentiment_color = "green" if avg_sentiment > 0 else "red"
        
        table.add_row(
            source,
            str(count),
            date_str,
            f"[{sentiment_color}]{avg_sentiment:.4f}[/{sentiment_color}]"
        )
    
    console.print(table)


def show_schema(data_source: ParquetDataSource) -> None:
    """
    Display the schema of the Parquet files.
    
    Args:
        data_source: The ParquetDataSource to query
    """
    schema = data_source.get_schema()
    
    table = Table(title="Parquet Schema")
    table.add_column("Field", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Description", style="yellow")
    
    # Descriptions for common fields
    field_descriptions = {
        "ticker": "Stock ticker symbol",
        "timestamp": "Time when message was created",
        "text": "Content of the message",
        "sentiment": "Sentiment score (-1 to 1)",
        "source": "Data source (reddit, twitter, news, etc.)",
        "url": "Source URL if available",
        "author": "Author of the message",
        "followers": "Number of followers (for social media)",
        "likes": "Number of likes/upvotes",
        "comments": "Number of comments/replies",
        "title": "Title of article or post",
        "created_at": "Creation time in source system"
    }
    
    for field_name, field_type in schema.items():
        description = field_descriptions.get(field_name.lower(), "")
        table.add_row(field_name, str(field_type), description)
    
    console.print(table)


def analyze_ticker(
    query_engine: QueryEngine,
    ticker: str,
    days: int = 30,
    sources: Optional[List[str]] = None,
    visualize: bool = True
) -> None:
    """
    Analyze sentiment for a specific ticker.
    
    Args:
        query_engine: The QueryEngine to use for queries
        ticker: The ticker symbol to analyze
        days: Number of days to look back
        sources: List of data sources to include (None for all)
        visualize: Whether to display visualizations
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Execute query
    filters = {
        "ticker": ticker,
        "date_range": (start_date, end_date)
    }
    
    if sources:
        filters["source"] = sources
    
    results = query_engine.execute_query(filters=filters)
    
    if results.empty:
        console.print(f"[yellow]No data found for ticker {ticker} in the last {days} days[/yellow]")
        return
    
    # Show basic statistics
    _display_ticker_stats(ticker, results)
    
    # Show visualizations if requested
    if visualize:
        console.print("\n[bold]Sentiment Timeline:[/bold]")
        display_sentiment_timeline(results)
        
        console.print("\n[bold]Sentiment Distribution:[/bold]")
        display_sentiment_distribution(results)
        
        console.print("\n[bold]Source Distribution:[/bold]")
        display_source_distribution(results)


def _display_ticker_stats(ticker: str, df: pd.DataFrame) -> None:
    """
    Display basic statistics for a ticker.
    
    Args:
        ticker: The ticker symbol
        df: DataFrame with results
    """
    # Calculate statistics
    total_mentions = len(df)
    avg_sentiment = df["sentiment"].mean()
    positive_count = len(df[df["sentiment"] > 0])
    negative_count = len(df[df["sentiment"] < 0])
    neutral_count = len(df[df["sentiment"] == 0])
    
    # Get sources distribution
    source_counts = df["source"].value_counts().to_dict()
    
    # Create a table for the statistics
    table = Table(title=f"Sentiment Analysis for {ticker}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Mentions", str(total_mentions))
    
    sentiment_color = "green" if avg_sentiment > 0 else "red"
    table.add_row(
        "Average Sentiment",
        f"[{sentiment_color}]{avg_sentiment:.4f}[/{sentiment_color}]"
    )
    
    table.add_row("Positive Mentions", f"[green]{positive_count} ({positive_count/total_mentions:.1%})[/green]")
    table.add_row("Negative Mentions", f"[red]{negative_count} ({negative_count/total_mentions:.1%})[/red]")
    table.add_row("Neutral Mentions", f"{neutral_count} ({neutral_count/total_mentions:.1%})")
    
    console.print(table)
    
    # Create a table for source distribution
    sources_table = Table(title="Source Distribution")
    sources_table.add_column("Source", style="cyan")
    sources_table.add_column("Count", style="green")
    sources_table.add_column("Percentage", style="yellow")
    
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        sources_table.add_row(
            source,
            str(count),
            f"{count/total_mentions:.1%}"
        )
    
    console.print(sources_table)


def compare_tickers(
    query_engine: QueryEngine,
    tickers: List[str],
    days: int = 30,
    visualize: bool = True
) -> None:
    """
    Compare sentiment for multiple tickers.
    
    Args:
        query_engine: The QueryEngine to use for queries
        tickers: List of ticker symbols to compare
        days: Number of days to look back
        visualize: Whether to display visualizations
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Create a table for comparative statistics
    table = Table(title=f"Ticker Comparison (Last {days} days)")
    table.add_column("Ticker", style="cyan")
    table.add_column("Mentions", style="green")
    table.add_column("Avg Sentiment", style="yellow")
    table.add_column("Positive %", style="green")
    table.add_column("Negative %", style="red")
    table.add_column("Sources", style="magenta")
    
    # Collect data for all tickers
    ticker_data = {}
    
    for ticker in tickers:
        filters = {
            "ticker": ticker,
            "date_range": (start_date, end_date)
        }
        
        results = query_engine.execute_query(filters=filters)
        
        if results.empty:
            table.add_row(ticker, "0", "N/A", "N/A", "N/A", "N/A")
            continue
        
        # Calculate statistics
        total_mentions = len(results)
        avg_sentiment = results["sentiment"].mean()
        positive_count = len(results[results["sentiment"] > 0])
        negative_count = len(results[results["sentiment"] < 0])
        
        # Get top sources
        source_counts = results["source"].value_counts()
        top_sources = ", ".join(source_counts.index[:3])
        
        # Store data for visualization
        ticker_data[ticker] = results
        
        # Add to table
        sentiment_color = "green" if avg_sentiment > 0 else "red"
        table.add_row(
            ticker,
            str(total_mentions),
            f"[{sentiment_color}]{avg_sentiment:.4f}[/{sentiment_color}]",
            f"{positive_count/total_mentions:.1%}",
            f"{negative_count/total_mentions:.1%}",
            top_sources
        )
    
    console.print(table)
    
    # Show visualization if requested and we have data
    if visualize and ticker_data:
        # Display sentiment heatmap
        console.print("\n[bold]Sentiment Comparison Heatmap:[/bold]")
        display_sentiment_heatmap(ticker_data)


def export_data(
    query_engine: QueryEngine,
    output_path: str,
    format: str = "csv",
    filters: Optional[Dict[str, Any]] = None
) -> None:
    """
    Export query results to a file.
    
    Args:
        query_engine: The QueryEngine to use for queries
        output_path: File path to save results
        format: Output format (csv, json, excel)
        filters: Query filters to apply
    """
    if filters is None:
        filters = {}
    
    # Execute query with filters
    results = query_engine.execute_query(filters=filters)
    
    if results.empty:
        console.print("[yellow]No data to export based on the specified filters[/yellow]")
        return
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Export based on format
    try:
        if format.lower() == "csv":
            results.to_csv(output_path, index=False)
        elif format.lower() == "json":
            results.to_json(output_path, orient="records", date_format="iso")
        elif format.lower() == "excel":
            results.to_excel(output_path, index=False)
        else:
            console.print(f"[red]Unsupported export format: {format}[/red]")
            return
        
        console.print(f"[green]Successfully exported {len(results)} records to {output_path}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error exporting data: {str(e)}[/red]")


def search_text(
    query_engine: QueryEngine,
    text: str,
    days: int = 30,
    ticker: Optional[str] = None
) -> None:
    """
    Search for text in message content.
    
    Args:
        query_engine: The QueryEngine to use for queries
        text: Text to search for
        days: Number of days to look back
        ticker: Optional ticker to filter by
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Build filters
    filters = {
        "text_contains": text,
        "date_range": (start_date, end_date)
    }
    
    if ticker:
        filters["ticker"] = ticker
    
    # Execute query
    results = query_engine.execute_query(filters=filters)
    
    if results.empty:
        console.print(f"[yellow]No results found for '{text}' in the last {days} days[/yellow]")
        return
    
    # Display results
    table = Table(title=f"Search Results for '{text}'")
    table.add_column("Date", style="cyan", width=20)
    table.add_column("Ticker", style="green", width=10)
    table.add_column("Source", style="magenta", width=15)
    table.add_column("Sentiment", width=10)
    table.add_column("Text", width=60)
    
    for _, row in results.iterrows():
        date_str = row.get("timestamp", "").strftime("%Y-%m-%d %H:%M") if "timestamp" in row else "N/A"
        ticker_str = row.get("ticker", "N/A")
        source_str = row.get("source", "N/A")
        sentiment = row.get("sentiment", 0)
        text_content = row.get("text", "")
        
        # Truncate long messages
        if len(text_content) > 60:
            text_content = text_content[:57] + "..."
        
        # Highlight the search text
        highlighted_text = Text(text_content)
        highlighted_text.highlight_words([text], "bold yellow")
        
        # Apply color based on sentiment
        sentiment_color = "green" if sentiment > 0 else "red" if sentiment < 0 else "white"
        sentiment_text = f"[{sentiment_color}]{sentiment:.4f}[/{sentiment_color}]"
        
        table.add_row(date_str, ticker_str, source_str, sentiment_text, highlighted_text)
    
    console.print(table)
    console.print(f"Found {len(results)} matches")


def show_cache_stats(cache_manager: CacheManager) -> None:
    """
    Display statistics about the query cache.
    
    Args:
        cache_manager: The CacheManager to query
    """
    stats = cache_manager.get_stats()
    
    table = Table(title="Cache Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Cache Size", f"{stats['size']} items")
    table.add_row("Cache Hits", str(stats["hits"]))
    table.add_row("Cache Misses", str(stats["misses"]))
    table.add_row("Hit Ratio", f"{stats['hit_ratio']:.2%}")
    table.add_row("Memory Usage", f"{stats['memory_usage'] / (1024*1024):.2f} MB")
    table.add_row("Cache Lifetime", f"{stats['avg_lifetime']:.2f} seconds")
    
    console.print(table)


def show_recent_trends(query_engine: QueryEngine, days: int = 7, limit: int = 10) -> None:
    """
    Show recent trending tickers by sentiment volume.
    
    Args:
        query_engine: The QueryEngine to use for queries
        days: Number of days to look back
        limit: Maximum number of tickers to display
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get trending tickers data
    trending = query_engine.get_trending_tickers(
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    if not trending:
        console.print(f"[yellow]No trending tickers found in the last {days} days[/yellow]")
        return
    
    # Display trending tickers
    table = Table(title=f"Trending Tickers (Last {days} days)")
    table.add_column("Rank", style="cyan", width=5)
    table.add_column("Ticker", style="green", width=10)
    table.add_column("Mentions", style="yellow", width=10)
    table.add_column("Change", width=10)
    table.add_column("Avg Sentiment", width=15)
    table.add_column("Trending", width=10)
    
    for i, (ticker, data) in enumerate(trending.items(), 1):
        mentions = data["mentions"]
        prev_mentions = data["prev_mentions"]
        sentiment = data["avg_sentiment"]
        trend = data["trend"]
        
        # Calculate change
        if prev_mentions > 0:
            change_pct = (mentions - prev_mentions) / prev_mentions * 100
            change_str = f"{change_pct:+.1f}%"
            change_color = "green" if change_pct > 0 else "red"
            change_display = f"[{change_color}]{change_str}[/{change_color}]"
        else:
            change_display = "New"
        
        # Format sentiment
        sentiment_color = "green" if sentiment > 0 else "red" if sentiment < 0 else "white"
        sentiment_display = f"[{sentiment_color}]{sentiment:.4f}[/{sentiment_color}]"
        
        # Format trend indicator
        trend_display = "↑" if trend > 0 else "↓" if trend < 0 else "→"
        trend_color = "green" if trend > 0 else "red" if trend < 0 else "yellow"
        
        table.add_row(
            str(i),
            ticker,
            str(mentions),
            change_display,
            sentiment_display,
            f"[{trend_color}]{trend_display}[/{trend_color}]"
        )
    
    console.print(table)