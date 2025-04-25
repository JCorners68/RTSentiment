#!/usr/bin/env python3
"""
Web-based interface for the Parquet Query Viewer using Streamlit.

This application provides a user-friendly interface for exploring and analyzing
sentiment data stored in Parquet files.
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date, timedelta
import json

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add the parent directory to the path to import core modules
sys.path.append(str(Path(__file__).parent.parent))
from core.parquet_data_source import ParquetDataSource
from core.query_engine import QueryEngine
from core.cache_manager import CacheManager
from core.utils import DataFormatter, ExportManager

# Configure page
st.set_page_config(
    page_title="Financial Sentiment Viewer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_resource
def initialize_query_engine(data_path: str) -> QueryEngine:
    """
    Initialize the query engine with caching.
    
    Args:
        data_path: Path to Parquet data directory
        
    Returns:
        QueryEngine instance
    """
    data_source = ParquetDataSource(data_path)
    cache_manager = CacheManager(enabled=True, max_size=1000, ttl=3600)
    return QueryEngine(data_source=data_source, cache_manager=cache_manager)


def format_sentiment(score: float) -> str:
    """
    Format a sentiment score with color and emoji.
    
    Args:
        score: Sentiment score (-1 to 1)
        
    Returns:
        Formatted string
    """
    if score > 0.5:
        return f"🟢 {score:.2f}"
    elif score > 0:
        return f"🟡 {score:.2f}"
    elif score > -0.5:
        return f"🟠 {score:.2f}"
    else:
        return f"🔴 {score:.2f}"


def get_sentiment_color(score: float) -> str:
    """
    Get color for sentiment score.
    
    Args:
        score: Sentiment score (-1 to 1)
        
    Returns:
        Hex color code
    """
    if score > 0.5:
        return "#28a745"  # Green
    elif score > 0:
        return "#ffc107"  # Yellow
    elif score > -0.5:
        return "#fd7e14"  # Orange
    else:
        return "#dc3545"  # Red


def create_sentiment_trend_chart(df: pd.DataFrame, ticker_column: Optional[str] = None) -> go.Figure:
    """
    Create a sentiment trend chart.
    
    Args:
        df: DataFrame with date and sentiment data
        ticker_column: Optional column for ticker filtering
        
    Returns:
        Plotly figure
    """
    if ticker_column and ticker_column in df.columns:
        fig = px.line(
            df,
            x="timestamp",
            y="sentiment",
            color=ticker_column,
            title="Sentiment Trend Over Time",
            labels={"timestamp": "Date", "sentiment": "Sentiment Score", ticker_column: ticker_column.capitalize()},
        )
    else:
        fig = px.line(
            df,
            x="timestamp",
            y="sentiment",
            title="Sentiment Trend Over Time",
            labels={"timestamp": "Date", "sentiment": "Sentiment Score"},
        )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    # Update layout
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Sentiment Score",
        yaxis_range=[-1, 1],
        hovermode="x unified",
    )
    
    return fig


def create_source_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a source comparison chart.
    
    Args:
        df: DataFrame with source and sentiment data
        
    Returns:
        Plotly figure
    """
    # Group by source
    source_data = df.groupby("source")["sentiment"].agg(["mean", "count"]).reset_index()
    source_data = source_data.sort_values("mean")
    
    # Create figure
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(
        go.Bar(
            y=source_data["source"],
            x=source_data["mean"],
            orientation="h",
            marker_color=[get_sentiment_color(score) for score in source_data["mean"]],
            text=[f"{score:.2f}" for score in source_data["mean"]],
            textposition="outside",
            name="Average Sentiment",
        )
    )
    
    # Update layout
    fig.update_layout(
        title="Sentiment by Source",
        xaxis_title="Average Sentiment Score",
        yaxis_title="Source",
        xaxis=dict(range=[-1, 1]),
        height=max(300, 50 * len(source_data)),
    )
    
    # Add zero line
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    
    return fig


def create_ticker_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a ticker comparison chart.
    
    Args:
        df: DataFrame with ticker and sentiment data
        
    Returns:
        Plotly figure
    """
    # Group by ticker
    ticker_data = df.groupby("ticker")["sentiment"].agg(["mean", "count"]).reset_index()
    ticker_data = ticker_data.sort_values("mean")
    
    # Limit to top 20 tickers by count
    if len(ticker_data) > 20:
        ticker_data = ticker_data.nlargest(20, "count")
    
    # Create figure
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(
        go.Bar(
            y=ticker_data["ticker"],
            x=ticker_data["mean"],
            orientation="h",
            marker_color=[get_sentiment_color(score) for score in ticker_data["mean"]],
            text=[f"{score:.2f}" for score in ticker_data["mean"]],
            textposition="outside",
            name="Average Sentiment",
        )
    )
    
    # Update layout
    fig.update_layout(
        title="Sentiment by Ticker",
        xaxis_title="Average Sentiment Score",
        yaxis_title="Ticker",
        xaxis=dict(range=[-1, 1]),
        height=max(300, 30 * len(ticker_data)),
    )
    
    # Add zero line
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    
    return fig


def create_sentiment_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a sentiment distribution histogram.
    
    Args:
        df: DataFrame with sentiment data
        
    Returns:
        Plotly figure
    """
    fig = px.histogram(
        df,
        x="sentiment",
        nbins=20,
        range_x=[-1, 1],
        title="Sentiment Distribution",
        labels={"sentiment": "Sentiment Score"},
    )
    
    # Add median line
    median = df["sentiment"].median()
    fig.add_vline(x=median, line_dash="dash", line_color="red", annotation_text=f"Median: {median:.2f}")
    
    # Add mean line
    mean = df["sentiment"].mean()
    fig.add_vline(x=mean, line_dash="dash", line_color="green", annotation_text=f"Mean: {mean:.2f}")
    
    # Update layout
    fig.update_layout(
        xaxis_title="Sentiment Score",
        yaxis_title="Count",
    )
    
    return fig


def create_heatmap(df: pd.DataFrame, x_col: str, y_col: str) -> go.Figure:
    """
    Create a heatmap for two categorical variables.
    
    Args:
        df: DataFrame with data
        x_col: Column for x-axis
        y_col: Column for y-axis
        
    Returns:
        Plotly figure
    """
    # Create pivot table
    pivot = df.pivot_table(
        index=y_col,
        columns=x_col,
        values="sentiment",
        aggfunc="mean",
    )
    
    # Create heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="RdYlGn",
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Sentiment"),
            text=[[f"{val:.2f}" for val in row] for row in pivot.values],
            texttemplate="%{text}",
        )
    )
    
    # Update layout
    fig.update_layout(
        title=f"Sentiment Heatmap: {y_col} vs {x_col}",
        xaxis_title=x_col.capitalize(),
        yaxis_title=y_col.capitalize(),
    )
    
    return fig


def calculate_sentiment_stats(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate statistics about sentiment scores.
    
    Args:
        df: DataFrame with sentiment data
        
    Returns:
        Dictionary with statistics
    """
    if df.empty or "sentiment" not in df.columns:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "positive_pct": 0.0,
            "negative_pct": 0.0,
            "neutral_pct": 0.0
        }
    
    stats = {}
    
    # Basic statistics
    stats["mean"] = df["sentiment"].mean()
    stats["median"] = df["sentiment"].median()
    stats["std"] = df["sentiment"].std()
    stats["min"] = df["sentiment"].min()
    stats["max"] = df["sentiment"].max()
    
    # Calculate percentages
    total = len(df)
    positive = (df["sentiment"] >= 0.3).sum()
    negative = (df["sentiment"] <= -0.3).sum()
    neutral = total - positive - negative
    
    stats["positive_pct"] = (positive / total) * 100 if total > 0 else 0
    stats["negative_pct"] = (negative / total) * 100 if total > 0 else 0
    stats["neutral_pct"] = (neutral / total) * 100 if total > 0 else 0
    
    return stats


def parse_date_range(date_range: str) -> tuple:
    """
    Parse a date range string.
    
    Args:
        date_range: Date range string
        
    Returns:
        Tuple of (start_date, end_date)
    """
    today = datetime.now().date()
    
    if date_range == "last-7-days":
        end_date = today
        start_date = end_date - timedelta(days=7)
    elif date_range == "last-30-days":
        end_date = today
        start_date = end_date - timedelta(days=30)
    elif date_range == "this-month":
        start_date = today.replace(day=1)
        end_date = today
    elif date_range == "last-month":
        last_month = today.month - 1
        last_month_year = today.year
        if last_month == 0:
            last_month = 12
            last_month_year -= 1
        start_date = date(last_month_year, last_month, 1)
        if last_month == 12:
            end_date = date(last_month_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(last_month_year, last_month + 1, 1) - timedelta(days=1)
    elif date_range == "year-to-date":
        start_date = date(today.year, 1, 1)
        end_date = today
    else:
        raise ValueError(f"Unsupported date range: {date_range}")
    
    return start_date, end_date


def main():
    """
    Main Streamlit application entry point.
    """
    st.title("Financial Sentiment Viewer")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Data path input
        data_path = st.text_input(
            "Data Path",
            value=os.environ.get("SENTIMENT_DATA_PATH", os.path.join(os.getcwd(), "data/output")),
            help="Path to directory containing Parquet files",
        )
        
        try:
            # Initialize query engine
            query_engine = initialize_query_engine(data_path)
            
            # Get metadata from data source
            tickers = query_engine.data_source.get_all_tickers()
            sources = query_engine.data_source.get_all_sources()
            
            st.success("Connected to data source")
            
            # Display metadata
            with st.expander("Dataset Info"):
                st.write(f"Tickers: {len(tickers)}")
                st.write(f"Sources: {len(sources)}")
                date_range = query_engine.data_source.get_date_range()
                if date_range:
                    min_date, max_date = date_range
                    st.write(f"Date Range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
            
            # Query controls
            st.header("Query Filters")
            
            # Date range selector
            date_range_option = st.selectbox(
                "Date Range",
                [
                    "Last 7 Days",
                    "Last 30 Days",
                    "This Month",
                    "Last Month",
                    "Year to Date",
                    "Custom Range",
                ],
                index=1,
            )
            
            if date_range_option == "Custom Range":
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=30))
                with col2:
                    end_date = st.date_input("End Date", value=datetime.now().date())
            else:
                # Convert to format for parse_date_range
                date_range_map = {
                    "Last 7 Days": "last-7-days",
                    "Last 30 Days": "last-30-days",
                    "This Month": "this-month",
                    "Last Month": "last-month",
                    "Year to Date": "year-to-date",
                }
                date_range_str = date_range_map[date_range_option]
                start_date, end_date = parse_date_range(date_range_str)
            
            # Ticker selector
            ticker_options = ["All"] + sorted(tickers)
            selected_tickers = st.multiselect(
                "Tickers",
                options=ticker_options,
                default=["All"],
                help="Select tickers to filter by",
            )
            
            if "All" in selected_tickers:
                tickers_filter = None
            else:
                tickers_filter = selected_tickers
            
            # Source selector
            source_options = ["All"] + sorted(sources)
            selected_sources = st.multiselect(
                "Sources",
                options=source_options,
                default=["All"],
                help="Select sources to filter by",
            )
            
            if "All" in selected_sources:
                sources_filter = None
            else:
                sources_filter = selected_sources
            
            # Sentiment range
            sentiment_range = st.slider(
                "Sentiment Range",
                min_value=-1.0,
                max_value=1.0,
                value=(-1.0, 1.0),
                step=0.1,
                help="Filter by sentiment score range",
            )
            min_sentiment, max_sentiment = sentiment_range
            
            # Text search
            text_query = st.text_input(
                "Text Search",
                "",
                help="Search for specific text in data",
            )
            
            # Limit
            limit = st.number_input(
                "Result Limit",
                min_value=1,
                max_value=10000,
                value=1000,
                step=100,
                help="Maximum number of results to return",
            )
            
            # Execute query button
            execute_query = st.button("Execute Query")
            
        except Exception as e:
            st.error(f"Error connecting to data source: {str(e)}")
            st.info(f"Please make sure the directory exists and contains Parquet files.")
            return
    
    # Main content area
    if 'query_engine' in locals() and execute_query:
        # Build filters
        filters = {
            "date_range": (
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time())
            ),
            "sentiment_range": (min_sentiment, max_sentiment),
        }
        
        if tickers_filter:
            filters["ticker"] = tickers_filter
        
        if sources_filter:
            filters["source"] = sources_filter
            
        if text_query:
            filters["text_contains"] = text_query
        
        # Execute query with progress bar
        with st.spinner("Executing query..."):
            results = query_engine.execute_query(filters=filters, limit=limit)
        
        # Display results
        st.header("Query Results")
        if isinstance(results, pd.DataFrame) and not results.empty:
            st.write(f"Found {len(results)} results")
            
            # Display data
            with st.expander("Data Preview"):
                st.dataframe(results)
            
            # Download button
            csv = results.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="sentiment_data.csv",
                mime="text/csv",
            )
            
            # Visualizations
            if "sentiment" in results.columns:
                st.header("Visualizations")
                
                # Summary statistics
                with st.expander("Summary Statistics"):
                    stats = calculate_sentiment_stats(results)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Mean Sentiment", f"{stats['mean']:.2f}")
                        st.metric("Positive %", f"{stats['positive_pct']:.1f}%")
                    with col2:
                        st.metric("Median Sentiment", f"{stats['median']:.2f}")
                        st.metric("Negative %", f"{stats['negative_pct']:.1f}%")
                    with col3:
                        st.metric("Std Dev", f"{stats['std']:.2f}")
                        st.metric("Neutral %", f"{stats['neutral_pct']:.1f}%")
                
                # Time series chart
                if "timestamp" in results.columns:
                    st.subheader("Sentiment Trend")
                    
                    # Prepare data
                    trend_data = results.copy()
                    
                    if "ticker" in results.columns and len(results["ticker"].unique()) > 1:
                        ticker_column = "ticker"
                    else:
                        ticker_column = None
                    
                    trend_chart = create_sentiment_trend_chart(trend_data, ticker_column)
                    st.plotly_chart(trend_chart, use_container_width=True)
                
                # Source comparison
                if "source" in results.columns and len(results["source"].unique()) > 1:
                    st.subheader("Source Comparison")
                    source_chart = create_source_comparison_chart(results)
                    st.plotly_chart(source_chart, use_container_width=True)
                
                # Ticker comparison
                if "ticker" in results.columns and len(results["ticker"].unique()) > 1:
                    st.subheader("Ticker Comparison")
                    ticker_chart = create_ticker_comparison_chart(results)
                    st.plotly_chart(ticker_chart, use_container_width=True)
                
                # Distribution histogram
                st.subheader("Sentiment Distribution")
                dist_chart = create_sentiment_distribution_chart(results)
                st.plotly_chart(dist_chart, use_container_width=True)
                
                # Heatmap (if applicable)
                categorical_columns = [col for col in results.columns if results[col].dtype == "object" and col not in ["text"]]
                if len(categorical_columns) >= 2:
                    st.subheader("Sentiment Heatmap")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        x_col = st.selectbox("X-Axis", categorical_columns, index=0)
                    with col2:
                        remaining_cols = [col for col in categorical_columns if col != x_col]
                        y_col = st.selectbox("Y-Axis", remaining_cols, index=0)
                    
                    # Check if we have enough data
                    if len(results[x_col].unique()) > 1 and len(results[y_col].unique()) > 1:
                        heatmap = create_heatmap(results, x_col, y_col)
                        st.plotly_chart(heatmap, use_container_width=True)
                    else:
                        st.info("Not enough unique values in selected columns for a heatmap")
                
                # Sample data table with sentiment highlights
                st.subheader("Sample Data")
                sample_data = results.sample(min(20, len(results))).copy() if len(results) > 20 else results.copy()
                
                # Select columns to display
                display_cols = ["timestamp", "ticker", "source", "sentiment"]
                if "text" in sample_data.columns:
                    display_cols.append("text")
                
                display_data = sample_data[display_cols]
                
                # Format timestamp if available
                if "timestamp" in display_data.columns:
                    display_data["timestamp"] = display_data["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
                
                # Format sentiment with color
                if "sentiment" in display_data.columns:
                    display_data["sentiment"] = display_data["sentiment"].apply(format_sentiment)
                
                st.dataframe(display_data, use_container_width=True)
            
            else:
                st.warning("No sentiment data available in the query results.")
        else:
            st.info("No results found matching the query criteria.")


if __name__ == "__main__":
    main()