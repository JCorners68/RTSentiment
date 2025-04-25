#!/usr/bin/env python3
"""
Dashboard interface for the Parquet Query Viewer using Streamlit.

This provides a pre-configured dashboard for viewing sentiment trends and statistics.
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
    page_title="Sentiment Dashboard",
    page_icon="📊",
    layout="wide",
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


def create_dashboard():
    """
    Create the sentiment dashboard.
    """
    st.title("Financial Sentiment Dashboard")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Dashboard Settings")
        
        # Data path input
        data_path = st.text_input(
            "Data Path",
            value=os.environ.get("SENTIMENT_DATA_PATH", os.path.join(os.getcwd(), "data/output")),
            help="Path to directory containing Parquet files",
        )
        
        try:
            # Initialize query engine
            query_engine = initialize_query_engine(data_path)
            
            # Get available tickers and sources
            tickers = query_engine.data_source.get_all_tickers()
            sources = query_engine.data_source.get_all_sources()
            date_range = query_engine.data_source.get_date_range()
            
            st.success("Connected to data source")
            
            # Date range
            min_date, max_date = date_range or (datetime.now().date() - timedelta(days=30), datetime.now().date())
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=max_date - timedelta(days=30))
            with col2:
                end_date = st.date_input("End Date", value=max_date)
            
            # Ticker selection
            top_tickers = sorted(tickers)[:5] if len(tickers) > 5 else sorted(tickers)
            selected_tickers = st.multiselect(
                "Tickers",
                options=sorted(tickers),
                default=top_tickers,
                help="Select tickers for dashboard",
            )
            
            # Source selection
            selected_sources = st.multiselect(
                "Sources",
                options=sorted(sources),
                default=sorted(sources),
                help="Select sources for dashboard",
            )
            
            # Refresh button
            refresh = st.button("Refresh Dashboard")
            
        except Exception as e:
            st.error(f"Error connecting to data source: {str(e)}")
            st.info(f"Please make sure the directory exists and contains Parquet files.")
            return
    
    # Main content area
    if 'query_engine' in locals() and (refresh or 'dashboard_data' not in st.session_state):
        # Query data for dashboard
        with st.spinner("Loading dashboard data..."):
            try:
                # Build filters for each query
                date_filter = {
                    "date_range": (
                        datetime.combine(start_date, datetime.min.time()),
                        datetime.combine(end_date, datetime.max.time())
                    )
                }
                
                # Optional filters
                if selected_tickers:
                    date_filter["ticker"] = selected_tickers
                
                if selected_sources:
                    date_filter["source"] = selected_sources
                
                # Get raw data
                raw_data = query_engine.execute_query(filters=date_filter, limit=10000)
                
                # Store in session state
                st.session_state.dashboard_data = {
                    "raw_data": raw_data
                }
            except Exception as e:
                st.error(f"Error querying data: {str(e)}")
                return
    
    # Display dashboard
    if 'dashboard_data' in st.session_state:
        data = st.session_state.dashboard_data
        raw_data = data["raw_data"]
        
        if len(raw_data) > 0:
            # Header metrics
            st.header("Overview")
            stats = calculate_sentiment_stats(raw_data)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Average Sentiment",
                    f"{stats['mean']:.2f}",
                    delta=f"{stats['mean'] - stats['median']:.2f} vs median",
                )
            with col2:
                st.metric(
                    "Positive %",
                    f"{stats['positive_pct']:.1f}%",
                )
            with col3:
                st.metric(
                    "Records Analyzed",
                    f"{len(raw_data):,}",
                )
            with col4:
                st.metric(
                    "Tickers Covered",
                    f"{len(raw_data['ticker'].unique())}",
                )
            
            # Main visualizations
            st.header("Sentiment Analysis")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Sentiment trend
                if "timestamp" in raw_data.columns:
                    # Prepare data for trend chart
                    trend_data = raw_data.copy()
                    
                    # Group by date and ticker if multiple tickers
                    if len(trend_data["ticker"].unique()) > 1:
                        # Convert to datetime if needed
                        if not pd.api.types.is_datetime64_dtype(trend_data["timestamp"]):
                            trend_data["timestamp"] = pd.to_datetime(trend_data["timestamp"])
                        
                        # Group by date and ticker
                        trend_data["date"] = trend_data["timestamp"].dt.date
                        agg_data = trend_data.groupby(["date", "ticker"])["sentiment"].mean().reset_index()
                        
                        # Convert date back to datetime for plotting
                        agg_data["date"] = pd.to_datetime(agg_data["date"])
                        
                        # Create plot
                        fig = px.line(
                            agg_data,
                            x="date",
                            y="sentiment",
                            color="ticker",
                            title="Sentiment Trend by Ticker",
                            labels={"date": "Date", "sentiment": "Sentiment Score", "ticker": "Ticker"},
                        )
                    else:
                        # Convert to datetime if needed
                        if not pd.api.types.is_datetime64_dtype(trend_data["timestamp"]):
                            trend_data["timestamp"] = pd.to_datetime(trend_data["timestamp"])
                        
                        # Group by date
                        trend_data["date"] = trend_data["timestamp"].dt.date
                        agg_data = trend_data.groupby("date")["sentiment"].mean().reset_index()
                        
                        # Convert date back to datetime for plotting
                        agg_data["date"] = pd.to_datetime(agg_data["date"])
                        
                        # Create plot
                        fig = px.line(
                            agg_data,
                            x="date",
                            y="sentiment",
                            title="Sentiment Trend Over Time",
                            labels={"date": "Date", "sentiment": "Sentiment Score"},
                        )
                    
                    # Add zero line
                    fig.add_hline(y=0, line_dash="dash", line_color="gray")
                    
                    # Update layout
                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Sentiment Score",
                        yaxis_range=[-1, 1],
                        hovermode="x unified",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No timestamp data available for trend visualization")
            
            with col2:
                # Source breakdown
                if "source" in raw_data.columns and len(raw_data["source"].unique()) > 1:
                    # Group by source
                    source_data = raw_data.groupby("source")["sentiment"].agg(["mean", "count"]).reset_index()
                    
                    # Sort by sentiment for display
                    source_data = source_data.sort_values("mean")
                    
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
                        )
                    )
                    
                    # Update layout
                    fig.update_layout(
                        title="Sentiment by Source",
                        xaxis_title="Average Sentiment Score",
                        yaxis_title="Source",
                        xaxis=dict(range=[-1, 1]),
                        height=350,
                    )
                    
                    # Add zero line
                    fig.add_vline(x=0, line_dash="dash", line_color="gray")
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No source data available for breakdown")
            
            # Second row
            col1, col2 = st.columns(2)
            
            with col1:
                # Sentiment distribution
                fig = px.histogram(
                    raw_data,
                    x="sentiment",
                    nbins=20,
                    range_x=[-1, 1],
                    title="Sentiment Distribution",
                    labels={"sentiment": "Sentiment Score"},
                    color_discrete_sequence=["#4e79a7"],
                )
                
                # Add median line
                median = raw_data["sentiment"].median()
                fig.add_vline(x=median, line_dash="dash", line_color="red", annotation_text=f"Median: {median:.2f}")
                
                # Add mean line
                mean = raw_data["sentiment"].mean()
                fig.add_vline(x=mean, line_dash="dash", line_color="green", annotation_text=f"Mean: {mean:.2f}")
                
                # Update layout
                fig.update_layout(
                    xaxis_title="Sentiment Score",
                    yaxis_title="Count",
                    height=350,
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Ticker comparison
                if len(raw_data["ticker"].unique()) > 1:
                    # Group by ticker
                    ticker_data = raw_data.groupby("ticker")["sentiment"].agg(["mean", "count"]).reset_index()
                    
                    # Sort by count and get top N
                    top_n = min(10, len(ticker_data))
                    ticker_data = ticker_data.sort_values("count", ascending=False).head(top_n)
                    
                    # Sort by sentiment for display
                    ticker_data = ticker_data.sort_values("mean")
                    
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
                        )
                    )
                    
                    # Update layout
                    fig.update_layout(
                        title=f"Top {top_n} Tickers by Volume",
                        xaxis_title="Average Sentiment Score",
                        yaxis_title="Ticker",
                        xaxis=dict(range=[-1, 1]),
                        height=350,
                    )
                    
                    # Add zero line
                    fig.add_vline(x=0, line_dash="dash", line_color="gray")
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Only one ticker selected")
            
            # Recent data table
            st.header("Recent Data")
            
            # Sort by date descending
            if "timestamp" in raw_data.columns:
                recent_data = raw_data.sort_values("timestamp", ascending=False).head(10)
                
                # Format data for display
                display_cols = ["timestamp", "ticker", "source", "sentiment"]
                if "text" in recent_data.columns:
                    display_cols.append("text")
                
                table_data = recent_data[display_cols].copy()
                
                # Format timestamp
                if "timestamp" in table_data.columns:
                    table_data["timestamp"] = table_data["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
                
                st.dataframe(table_data, use_container_width=True)
            else:
                st.info("No timestamp data available for recent data display")
        else:
            st.warning("No data available for the selected filters.")


if __name__ == "__main__":
    create_dashboard()