#!/usr/bin/env python3
"""
Sentiment Visualization Module

This script generates visualizations for sentiment analysis results.
"""

import os
import sys
import json
import logging
import argparse
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List, Optional, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
SENTIMENT_DATA_DIR = "/home/jonat/real_senti/data/sentiment_results"
SENTIMENT_CSV = os.path.join(SENTIMENT_DATA_DIR, "sentiment_analysis.csv")
VISUALIZATIONS_DIR = os.path.join(SENTIMENT_DATA_DIR, "visualizations")


def load_sentiment_data() -> pd.DataFrame:
    """
    Load sentiment analysis data from CSV file.
    
    Returns:
        DataFrame with sentiment data
    """
    if not os.path.exists(SENTIMENT_CSV):
        logger.error(f"Sentiment data not found: {SENTIMENT_CSV}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(SENTIMENT_CSV)
        
        # Convert datetime to proper format if it exists
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"], unit="s", errors="coerce")
        
        logger.info(f"Loaded {len(df)} sentiment records")
        return df
    except Exception as e:
        logger.error(f"Error loading sentiment data: {e}")
        return pd.DataFrame()


def setup_visualization_environment() -> None:
    """Set up the visualization environment and style."""
    # Create output directory if it doesn't exist
    os.makedirs(VISUALIZATIONS_DIR, exist_ok=True)
    
    # Set up the visualization style
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        'figure.figsize': (12, 8),
        'axes.labelsize': 14,
        'axes.titlesize': 16,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12
    })


def plot_sentiment_distribution(df: pd.DataFrame) -> str:
    """
    Plot distribution of sentiment scores.
    
    Args:
        df: DataFrame with sentiment data
    
    Returns:
        Path to the saved figure
    """
    if df.empty:
        logger.error("Empty DataFrame, cannot create distribution plot")
        return ""
    
    try:
        # Create figure
        plt.figure(figsize=(12, 8))
        
        # Plot distribution of sentiment scores
        sns.histplot(df["sentiment_score"], bins=20, kde=True)
        
        # Add vertical lines for mean and median
        plt.axvline(df["sentiment_score"].mean(), color='r', linestyle='--', 
                   label=f'Mean: {df["sentiment_score"].mean():.3f}')
        plt.axvline(df["sentiment_score"].median(), color='g', linestyle='-.', 
                   label=f'Median: {df["sentiment_score"].median():.3f}')
        
        # Add title and labels
        plt.title("Distribution of Sentiment Scores")
        plt.xlabel("Sentiment Score")
        plt.ylabel("Frequency")
        plt.legend()
        
        # Save figure
        figure_path = os.path.join(VISUALIZATIONS_DIR, "sentiment_distribution.png")
        plt.savefig(figure_path)
        plt.close()
        
        logger.info(f"Saved sentiment distribution plot to: {figure_path}")
        return figure_path
    
    except Exception as e:
        logger.error(f"Error creating sentiment distribution plot: {e}")
        return ""


def plot_sentiment_by_ticker(df: pd.DataFrame) -> str:
    """
    Plot sentiment scores by ticker.
    
    Args:
        df: DataFrame with sentiment data
    
    Returns:
        Path to the saved figure
    """
    if df.empty or "ticker" not in df.columns:
        logger.error("Missing data for ticker plot")
        return ""
    
    try:
        # Create figure
        plt.figure(figsize=(14, 8))
        
        # Plot boxplot of sentiment by ticker
        ax = sns.boxplot(x="ticker", y="sentiment_score", data=df, palette="Set3")
        
        # Add a horizontal line at 0
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # Add title and labels
        plt.title("Sentiment Distribution by Company")
        plt.xlabel("Company")
        plt.ylabel("Sentiment Score")
        
        # Add mean sentiment as text on each box
        means = df.groupby("ticker")["sentiment_score"].mean().reset_index()
        for i, row in means.iterrows():
            ax.text(
                i, 
                row["sentiment_score"] + 0.02, 
                f'{row["sentiment_score"]:.3f}', 
                horizontalalignment='center',
                size='small',
                color='black',
                weight='semibold'
            )
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        
        # Tight layout to ensure everything fits
        plt.tight_layout()
        
        # Save figure
        figure_path = os.path.join(VISUALIZATIONS_DIR, "sentiment_by_ticker.png")
        plt.savefig(figure_path)
        plt.close()
        
        logger.info(f"Saved ticker sentiment plot to: {figure_path}")
        return figure_path
    
    except Exception as e:
        logger.error(f"Error creating ticker sentiment plot: {e}")
        return ""


def plot_sentiment_over_time(df: pd.DataFrame) -> str:
    """
    Plot sentiment scores over time.
    
    Args:
        df: DataFrame with sentiment data
    
    Returns:
        Path to the saved figure
    """
    if df.empty or "datetime" not in df.columns:
        logger.error("Missing data for time series plot")
        return ""
    
    try:
        # Create a copy to avoid modifying original
        plot_df = df.copy()
        
        # Make sure datetime column is datetime type
        plot_df["datetime"] = pd.to_datetime(plot_df["datetime"], errors="coerce")
        
        # Drop rows with invalid dates
        plot_df = plot_df.dropna(subset=["datetime"])
        
        if plot_df.empty:
            logger.error("No valid datetime data for time series plot")
            return ""
        
        # Sort by date
        plot_df = plot_df.sort_values("datetime")
        
        # Create figure
        plt.figure(figsize=(14, 10))
        
        # Group by ticker and plot each
        for ticker, group in plot_df.groupby("ticker"):
            # Resample to daily frequency and take mean
            if len(group) > 50:  # Only if we have enough data points
                # Create a Series with datetime as index for easier resampling
                ticker_series = pd.Series(
                    group["sentiment_score"].values, 
                    index=group["datetime"]
                )
                
                # Resample to daily frequency
                resampled = ticker_series.resample('D').mean()
                
                # Plot the resampled data
                plt.plot(
                    resampled.index, 
                    resampled.values, 
                    marker='o', 
                    linestyle='-', 
                    label=ticker
                )
            else:
                # Not enough data for resampling, plot raw data
                plt.plot(
                    group["datetime"], 
                    group["sentiment_score"],
                    marker='o', 
                    linestyle='-', 
                    label=ticker
                )
        
        # Add a horizontal line at 0
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # Add title and labels
        plt.title("Sentiment Scores Over Time")
        plt.xlabel("Date")
        plt.ylabel("Sentiment Score")
        plt.legend(loc="best")
        
        # Format x-axis
        plt.gcf().autofmt_xdate()
        
        # Tight layout to ensure everything fits
        plt.tight_layout()
        
        # Save figure
        figure_path = os.path.join(VISUALIZATIONS_DIR, "sentiment_over_time.png")
        plt.savefig(figure_path)
        plt.close()
        
        logger.info(f"Saved time series plot to: {figure_path}")
        return figure_path
    
    except Exception as e:
        logger.error(f"Error creating time series plot: {e}")
        return ""


def plot_sentiment_by_source(df: pd.DataFrame) -> str:
    """
    Plot sentiment scores by news source.
    
    Args:
        df: DataFrame with sentiment data
    
    Returns:
        Path to the saved figure
    """
    if df.empty or "source" not in df.columns:
        logger.error("Missing data for source plot")
        return ""
    
    try:
        # Count the number of articles by source
        source_counts = df["source"].value_counts().reset_index()
        source_counts.columns = ["source", "count"]
        
        # Get mean sentiment by source
        source_sentiment = df.groupby("source")["sentiment_score"].mean().reset_index()
        
        # Join the counts and mean sentiment
        source_data = pd.merge(source_counts, source_sentiment, on="source")
        
        # Sort by count descending
        source_data = source_data.sort_values("count", ascending=False)
        
        # Take top 10 sources by count
        top_sources = source_data.head(10)
        
        # Create figure
        plt.figure(figsize=(14, 10))
        
        # Set up barplot
        ax = plt.subplot(111)
        
        # Create barplot
        bars = ax.bar(
            top_sources["source"], 
            top_sources["sentiment_score"],
            alpha=0.8
        )
        
        # Color bars by sentiment score
        for i, bar in enumerate(bars):
            score = top_sources.iloc[i]["sentiment_score"]
            if score > 0.05:
                bar.set_color('green')
            elif score < -0.05:
                bar.set_color('red')
            else:
                bar.set_color('gray')
        
        # Add count labels
        for i, bar in enumerate(bars):
            count = top_sources.iloc[i]["count"]
            ax.text(
                bar.get_x() + bar.get_width()/2,
                0.01,
                f'n={count}',
                ha='center',
                color='black',
                fontsize=10
            )
        
        # Add sentiment score labels
        for i, bar in enumerate(bars):
            score = top_sources.iloc[i]["sentiment_score"]
            height = bar.get_height()
            # Determine position based on positive or negative
            y_pos = height + 0.01 if height >= 0 else height - 0.04
            ax.text(
                bar.get_x() + bar.get_width()/2,
                y_pos,
                f'{score:.3f}',
                ha='center',
                va='bottom' if height >= 0 else 'top',
                color='black',
                fontsize=10
            )
        
        # Add zero line
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # Add title and labels
        plt.title("Average Sentiment Score by News Source (Top 10 Sources)")
        plt.xlabel("Source")
        plt.ylabel("Average Sentiment Score")
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Tight layout to ensure everything fits
        plt.tight_layout()
        
        # Save figure
        figure_path = os.path.join(VISUALIZATIONS_DIR, "sentiment_by_source.png")
        plt.savefig(figure_path)
        plt.close()
        
        logger.info(f"Saved source sentiment plot to: {figure_path}")
        return figure_path
    
    except Exception as e:
        logger.error(f"Error creating source sentiment plot: {e}")
        return ""


def plot_sentiment_heatmap(df: pd.DataFrame) -> str:
    """
    Plot a heatmap of sentiment scores by ticker and date.
    
    Args:
        df: DataFrame with sentiment data
    
    Returns:
        Path to the saved figure
    """
    if df.empty or "datetime" not in df.columns or "ticker" not in df.columns:
        logger.error("Missing data for heatmap")
        return ""
    
    try:
        # Create a copy to avoid modifying original
        plot_df = df.copy()
        
        # Make sure datetime column is datetime type
        plot_df["datetime"] = pd.to_datetime(plot_df["datetime"], errors="coerce")
        
        # Drop rows with invalid dates
        plot_df = plot_df.dropna(subset=["datetime"])
        
        if plot_df.empty:
            logger.error("No valid datetime data for heatmap")
            return ""
        
        # Extract date (drop time component)
        plot_df["date"] = plot_df["datetime"].dt.date
        
        # Calculate daily average sentiment by ticker
        pivot_df = plot_df.pivot_table(
            values="sentiment_score", 
            index="ticker", 
            columns="date", 
            aggfunc="mean"
        )
        
        # Create figure
        plt.figure(figsize=(16, 10))
        
        # Create heatmap
        ax = sns.heatmap(
            pivot_df, 
            cmap="RdBu_r",
            center=0,
            annot=False,
            fmt=".2f",
            linewidths=0.5
        )
        
        # Add title and labels
        plt.title("Daily Sentiment Scores by Company")
        plt.xlabel("Date")
        plt.ylabel("Company")
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Color bar label
        cbar = ax.collections[0].colorbar
        cbar.set_label("Sentiment Score")
        
        # Tight layout to ensure everything fits
        plt.tight_layout()
        
        # Save figure
        figure_path = os.path.join(VISUALIZATIONS_DIR, "sentiment_heatmap.png")
        plt.savefig(figure_path)
        plt.close()
        
        logger.info(f"Saved sentiment heatmap to: {figure_path}")
        return figure_path
    
    except Exception as e:
        logger.error(f"Error creating sentiment heatmap: {e}")
        return ""


def generate_all_visualizations(df: pd.DataFrame) -> List[str]:
    """
    Generate all visualizations for the sentiment data.
    
    Args:
        df: DataFrame with sentiment data
    
    Returns:
        List of paths to saved figures
    """
    figures = []
    
    # Set up visualization environment
    setup_visualization_environment()
    
    # Generate each visualization
    distribution = plot_sentiment_distribution(df)
    if distribution:
        figures.append(distribution)
    
    ticker_plot = plot_sentiment_by_ticker(df)
    if ticker_plot:
        figures.append(ticker_plot)
    
    time_plot = plot_sentiment_over_time(df)
    if time_plot:
        figures.append(time_plot)
    
    source_plot = plot_sentiment_by_source(df)
    if source_plot:
        figures.append(source_plot)
    
    heatmap = plot_sentiment_heatmap(df)
    if heatmap:
        figures.append(heatmap)
    
    return figures


def main():
    """Main function to generate visualizations for sentiment analysis data."""
    parser = argparse.ArgumentParser(
        description='Generate visualizations for sentiment analysis results.')
    
    parser.add_argument('--distribution', action='store_true', 
                        help='Generate sentiment score distribution plot')
    parser.add_argument('--ticker', action='store_true', 
                        help='Generate sentiment by ticker plot')
    parser.add_argument('--time', action='store_true', 
                        help='Generate sentiment over time plot')
    parser.add_argument('--source', action='store_true', 
                        help='Generate sentiment by source plot')
    parser.add_argument('--heatmap', action='store_true', 
                        help='Generate sentiment heatmap')
    parser.add_argument('--all', action='store_true', 
                        help='Generate all visualizations')
    
    args = parser.parse_args()
    
    # Load sentiment data
    df = load_sentiment_data()
    
    if df.empty:
        logger.error("No sentiment data available for visualization")
        return
    
    # Set up visualization environment
    setup_visualization_environment()
    
    # Generate requested visualizations
    figures = []
    
    if args.all:
        figures = generate_all_visualizations(df)
    else:
        if args.distribution:
            dist_plot = plot_sentiment_distribution(df)
            if dist_plot:
                figures.append(dist_plot)
        
        if args.ticker:
            ticker_plot = plot_sentiment_by_ticker(df)
            if ticker_plot:
                figures.append(ticker_plot)
        
        if args.time:
            time_plot = plot_sentiment_over_time(df)
            if time_plot:
                figures.append(time_plot)
        
        if args.source:
            source_plot = plot_sentiment_by_source(df)
            if source_plot:
                figures.append(source_plot)
        
        if args.heatmap:
            heatmap = plot_sentiment_heatmap(df)
            if heatmap:
                figures.append(heatmap)
    
    # If no specific visualization was requested, generate all
    if not any([args.distribution, args.ticker, args.time, args.source, args.heatmap, args.all]):
        figures = generate_all_visualizations(df)
    
    # Print summary
    if figures:
        logger.info(f"Generated {len(figures)} visualizations:")
        for fig in figures:
            logger.info(f" - {fig}")
        logger.info(f"All visualizations saved to: {VISUALIZATIONS_DIR}")
    else:
        logger.warning("No visualizations were generated")


if __name__ == "__main__":
    main()