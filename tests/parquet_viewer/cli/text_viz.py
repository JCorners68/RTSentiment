"""
Text-based visualizations for the Parquet Query Viewer CLI.

This module provides functions for creating text-based visualizations using the Rich library.
These visualizations help present sentiment data in a more intuitive way on the command line.
"""
import calendar
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn

# Initialize console for rich output
console = Console()


def display_sentiment_timeline(df: pd.DataFrame, resolution: str = "day") -> None:
    """
    Display a text-based timeline visualization of sentiment over time.
    
    Args:
        df: DataFrame with sentiment data
        resolution: Time resolution ('day', 'hour', 'week')
    """
    if df.empty:
        console.print("[yellow]No data available for timeline visualization[/yellow]")
        return
    
    # Ensure we have a timestamp column
    if "timestamp" not in df.columns:
        console.print("[yellow]Cannot create timeline: timestamp column missing[/yellow]")
        return
    
    # Group by time resolution
    if resolution == "hour":
        df["time_bucket"] = df["timestamp"].dt.floor("H")
        title = "Hourly Sentiment Timeline"
    elif resolution == "week":
        df["time_bucket"] = df["timestamp"].dt.to_period("W").dt.start_time
        title = "Weekly Sentiment Timeline"
    else:  # default to day
        df["time_bucket"] = df["timestamp"].dt.floor("D")
        title = "Daily Sentiment Timeline"
    
    # Aggregate by time bucket
    timeline_data = df.groupby("time_bucket").agg({
        "sentiment": ["mean", "count"],
        "ticker": "first"  # Just to keep track of the ticker
    }).reset_index()
    
    # Create the timeline visual
    table = Table(title=title)
    table.add_column("Time", style="cyan")
    table.add_column("Volume", style="green")
    table.add_column("Avg Sentiment", style="yellow")
    table.add_column("Timeline", width=40)
    
    max_count = timeline_data[("sentiment", "count")].max()
    
    for _, row in timeline_data.iterrows():
        # Format the time string based on resolution
        time_bucket = row["time_bucket"]
        if resolution == "hour":
            time_str = time_bucket.strftime("%Y-%m-%d %H:00")
        elif resolution == "week":
            time_str = f"Week of {time_bucket.strftime('%Y-%m-%d')}"
        else:
            time_str = time_bucket.strftime("%Y-%m-%d")
        
        # Get sentiment and count values
        sentiment = row[("sentiment", "mean")]
        count = row[("sentiment", "count")]
        
        # Create volume bar scaled to max count
        count_ratio = count / max_count if max_count > 0 else 0
        volume_bar = "█" * int(count_ratio * 10)
        if not volume_bar and count > 0:
            volume_bar = "▏"  # At least show something if count > 0
        
        # Create sentiment indicator
        sentiment_bar = _create_sentiment_bar(sentiment, width=40)
        
        # Add the row
        sentiment_color = "green" if sentiment > 0 else "red" if sentiment < 0 else "white"
        table.add_row(
            time_str,
            f"{count} {volume_bar}",
            f"[{sentiment_color}]{sentiment:.4f}[/{sentiment_color}]",
            sentiment_bar
        )
    
    # Render the timeline
    console.print(table)


def _create_sentiment_bar(sentiment: float, width: int = 40) -> str:
    """
    Create a text-based sentiment bar visualization.
    
    Args:
        sentiment: Sentiment score (-1 to 1)
        width: Width of the bar in characters
    
    Returns:
        String with formatted sentiment bar
    """
    # Scale sentiment to the width
    half_width = width // 2
    
    # Calculate the position of the marker
    marker_pos = int(sentiment * half_width) + half_width
    
    # Create the bar
    bar = [" "] * width
    
    # Add center line and scale
    mid_point = width // 2
    for i in range(width):
        if i == mid_point:
            bar[i] = "│"  # Center line
        elif (i - mid_point) % (half_width // 5) == 0:
            bar[i] = "·"  # Scale markers
    
    # Add the marker
    marker_pos = max(0, min(marker_pos, width - 1))  # Ensure it's within bounds
    
    # Convert to colored text
    result = ""
    for i in range(width):
        char = "▲" if i == marker_pos else bar[i]
        if i < mid_point:
            result += f"[red]{char}[/red]"
        elif i > mid_point:
            result += f"[green]{char}[/green]"
        else:
            result += f"[white]{char}[/white]"
    
    return result


def display_sentiment_distribution(df: pd.DataFrame, bins: int = 10) -> None:
    """
    Display a text-based histogram of sentiment distribution.
    
    Args:
        df: DataFrame with sentiment data
        bins: Number of bins for the histogram
    """
    if df.empty or "sentiment" not in df.columns:
        console.print("[yellow]No sentiment data available for distribution visualization[/yellow]")
        return
    
    # Create bins for the histogram
    sentiment_values = df["sentiment"].dropna()
    
    if len(sentiment_values) == 0:
        console.print("[yellow]No valid sentiment values for distribution[/yellow]")
        return
    
    # Compute histogram
    counts, edges = np.histogram(sentiment_values, bins=bins, range=(-1, 1))
    max_count = counts.max() if counts.max() > 0 else 1
    
    # Create visualization
    table = Table(title="Sentiment Distribution")
    table.add_column("Range", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Distribution", width=40)
    
    for i in range(len(counts)):
        start, end = edges[i], edges[i+1]
        count = counts[i]
        
        # Determine the color based on the sentiment range
        if end <= 0:
            color = "red"
        elif start >= 0:
            color = "green"
        else:
            color = "yellow"  # Spans across zero
        
        # Create the bar
        bar_length = int((count / max_count) * 40)
        bar = f"[{color}]{'█' * bar_length}[/{color}]"
        
        # Format the range
        range_str = f"{start:.2f} to {end:.2f}"
        
        table.add_row(range_str, str(count), bar)
    
    # Add summary statistics
    stats_panel = Panel(
        f"Mean: {sentiment_values.mean():.4f}  |  "
        f"Median: {sentiment_values.median():.4f}  |  "
        f"Std Dev: {sentiment_values.std():.4f}  |  "
        f"Min: {sentiment_values.min():.4f}  |  "
        f"Max: {sentiment_values.max():.4f}",
        title="Statistics",
        border_style="green"
    )
    
    console.print(table)
    console.print(stats_panel)


def display_source_distribution(df: pd.DataFrame) -> None:
    """
    Display a text-based visualization of data source distribution.
    
    Args:
        df: DataFrame with sentiment data including source column
    """
    if df.empty or "source" not in df.columns:
        console.print("[yellow]No source data available for distribution visualization[/yellow]")
        return
    
    # Count occurrences of each source
    source_counts = df["source"].value_counts()
    total_count = len(df)
    
    # Calculate average sentiment by source
    source_sentiment = df.groupby("source")["sentiment"].mean()
    
    # Create visualization
    table = Table(title="Source Distribution")
    table.add_column("Source", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Percentage", style="yellow")
    table.add_column("Avg Sentiment", style="magenta")
    table.add_column("Distribution", width=30)
    
    for source, count in source_counts.items():
        percentage = count / total_count
        sentiment = source_sentiment.get(source, 0)
        
        # Create the bar
        bar_length = int(percentage * 30)
        bar = "█" * bar_length
        
        # Determine sentiment color
        sentiment_color = "green" if sentiment > 0 else "red" if sentiment < 0 else "white"
        
        table.add_row(
            source,
            str(count),
            f"{percentage:.1%}",
            f"[{sentiment_color}]{sentiment:.4f}[/{sentiment_color}]",
            bar
        )
    
    console.print(table)


def display_sentiment_heatmap(
    ticker_data: Dict[str, pd.DataFrame],
    resolution: str = "day"
) -> None:
    """
    Display a text-based heatmap comparing sentiment across tickers over time.
    
    Args:
        ticker_data: Dictionary mapping ticker symbols to DataFrames
        resolution: Time resolution ('day', 'hour', 'week')
    """
    # Ensure we have data for at least one ticker
    if not ticker_data:
        console.print("[yellow]No data available for heatmap visualization[/yellow]")
        return
    
    # Process each ticker's data
    processed_data = {}
    
    for ticker, df in ticker_data.items():
        if df.empty or "timestamp" not in df.columns or "sentiment" not in df.columns:
            continue
        
        # Group by time resolution
        if resolution == "hour":
            df["time_bucket"] = df["timestamp"].dt.floor("H")
        elif resolution == "week":
            df["time_bucket"] = df["timestamp"].dt.to_period("W").dt.start_time
        else:  # default to day
            df["time_bucket"] = df["timestamp"].dt.floor("D")
        
        # Aggregate by time bucket
        timeline = df.groupby("time_bucket")["sentiment"].mean()
        processed_data[ticker] = timeline
    
    # Find the union of all time buckets
    all_times = set()
    for ticker_timeline in processed_data.values():
        all_times.update(ticker_timeline.index)
    
    all_times = sorted(all_times)
    
    if not all_times:
        console.print("[yellow]No valid time data for heatmap visualization[/yellow]")
        return
    
    # Create the heatmap
    table = Table(title=f"Sentiment Heatmap by {resolution.capitalize()}")
    table.add_column("Time", style="cyan")
    
    for ticker in processed_data.keys():
        table.add_column(ticker, style="green")
    
    for time_bucket in all_times:
        # Format the time string based on resolution
        if resolution == "hour":
            time_str = time_bucket.strftime("%Y-%m-%d %H:00")
        elif resolution == "week":
            time_str = f"Week of {time_bucket.strftime('%Y-%m-%d')}"
        else:
            time_str = time_bucket.strftime("%Y-%m-%d")
        
        row = [time_str]
        
        for ticker, timeline in processed_data.items():
            sentiment = timeline.get(time_bucket, None)
            
            if sentiment is None:
                cell = "—"  # No data
            else:
                # Format sentiment cell with color and intensity
                intensity = min(abs(sentiment) * 1.5, 1.0)  # Scale intensity
                char_count = int(intensity * 5)
                display_char = "▓" if char_count >= 4 else "▒" if char_count >= 2 else "░"
                
                if sentiment > 0:
                    color = "green"
                elif sentiment < 0:
                    color = "red"
                else:
                    color = "white"
                    display_char = "○"
                
                display_str = display_char * max(1, char_count)
                cell = f"[{color}]{display_str} {sentiment:.2f}[/{color}]"
            
            row.append(cell)
        
        table.add_row(*row)
    
    console.print(table)


def display_sentiment_calendar(
    df: pd.DataFrame,
    year: Optional[int] = None,
    month: Optional[int] = None
) -> None:
    """
    Display a calendar view of sentiment data.
    
    Args:
        df: DataFrame with sentiment data
        year: Year to display (default: current year)
        month: Month to display (default: current month)
    """
    if df.empty or "timestamp" not in df.columns:
        console.print("[yellow]No data available for calendar visualization[/yellow]")
        return
    
    # Set default year and month to current if not specified
    today = datetime.now()
    year = year or today.year
    month = month or today.month
    
    # Get month name and create title
    month_name = calendar.month_name[month]
    title = f"Sentiment Calendar: {month_name} {year}"
    
    # Get calendar days
    cal = calendar.monthcalendar(year, month)
    
    # Prepare sentiment data by day
    df["day"] = df["timestamp"].dt.day
    df["month"] = df["timestamp"].dt.month
    df["year"] = df["timestamp"].dt.year
    
    # Filter data for the specified month and year
    filtered_df = df[(df["month"] == month) & (df["year"] == year)]
    
    # Aggregate by day
    daily_sentiment = filtered_df.groupby("day")["sentiment"].agg(["mean", "count"])
    
    # Create the calendar visualization
    table = Table(title=title, show_header=True, header_style="bold magenta")
    
    # Add day of week headers
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        table.add_column(day, justify="center", style="cyan")
    
    # Add rows for each week
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                # Day not in this month
                row.append("")
            else:
                # Check if we have data for this day
                if day in daily_sentiment.index:
                    sentiment = daily_sentiment.loc[day, "mean"]
                    count = daily_sentiment.loc[day, "count"]
                    
                    # Determine color and symbols based on sentiment
                    if sentiment > 0.3:
                        cell = f"[green]{day}\n↑↑ {sentiment:.2f}\n({count})[/green]"
                    elif sentiment > 0:
                        cell = f"[green]{day}\n↑ {sentiment:.2f}\n({count})[/green]"
                    elif sentiment < -0.3:
                        cell = f"[red]{day}\n↓↓ {sentiment:.2f}\n({count})[/red]"
                    elif sentiment < 0:
                        cell = f"[red]{day}\n↓ {sentiment:.2f}\n({count})[/red]"
                    else:
                        cell = f"{day}\n→ {sentiment:.2f}\n({count})"
                else:
                    # No data for this day
                    cell = f"{day}\n---\n(0)"
                
                row.append(cell)
        
        table.add_row(*row)
    
    console.print(table)


def display_loading_spinner(message: str):
    """
    Display a loading spinner while a long operation is in progress.
    
    Args:
        message: Message to display alongside the spinner
    
    Returns:
        Progress object that can be used to stop the spinner
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console
    )
    progress.add_task(message, total=None)
    return progress