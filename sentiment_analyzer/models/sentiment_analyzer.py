"""
Sentiment analyzer model for financial data (LEGACY VERSION)

This is a legacy implementation maintained for backward compatibility.
For new development, use sentiment_model.py instead.
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    Analyzes sentiment data with time decay and source weighting (LEGACY)
    
    Note: This class is maintained for backward compatibility.
    New code should use SentimentModel from sentiment_model.py instead.
    """
    def __init__(self, config=None):
        """
        Initialize the sentiment analyzer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.decay_type = self.config.get('decay_type', 'exponential')
        self.decay_half_life = self.config.get('decay_half_life', 24)  # hours
        self.max_age_hours = self.config.get('max_age_hours', 168)  # 7 days
        
        # Source weights (higher = more trusted/impactful)
        self.source_weights = {
            'news': 1.0,
            'reddit': 0.7, 
            'twitter': 0.5
        }
        
        # Override with config if provided
        if 'source_weights' in self.config:
            self.source_weights.update(self.config['source_weights'])
            
        logger.info(f"Initialized SentimentAnalyzer with decay: {self.decay_type}, half-life: {self.decay_half_life}h")
        
    def calculate_time_decay(self, timestamp, reference_time=None):
        """
        Calculate time decay factor based on age
        
        Args:
            timestamp: Event timestamp
            reference_time: Reference time (now if None)
            
        Returns:
            Decay factor between 0 and 1
        """
        if reference_time is None:
            reference_time = datetime.now()
            
        # Calculate age in hours
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)
            
        age_delta = reference_time - timestamp
        age_hours = age_delta.total_seconds() / 3600
        
        # Apply max age cutoff
        if age_hours > self.max_age_hours:
            return 0.0
            
        # Calculate decay factor based on selected method
        if self.decay_type == 'exponential':
            # Exponential decay: 0.5 at half-life, approaching 0 for older events
            decay_factor = 2 ** (-age_hours / self.decay_half_life)
        elif self.decay_type == 'linear':
            # Linear decay: 1.0 at now, 0.0 at max_age
            decay_factor = 1.0 - (age_hours / self.max_age_hours)
        else:
            # Default: no decay
            decay_factor = 1.0
            
        return max(0.0, min(1.0, decay_factor))
        
    def get_source_weight(self, source):
        """
        Get weight factor for a source
        
        Args:
            source: Source name string
            
        Returns:
            Weight factor (default 1.0 if source unknown)
        """
        return self.source_weights.get(source.lower(), 1.0)
        
    def calculate_weighted_sentiment(self, df):
        """
        Calculate weighted sentiment scores with time decay
        
        Args:
            df: DataFrame with sentiment data
            
        Returns:
            DataFrame with added weight and weighted_sentiment columns
        """
        # Make a copy to avoid modifying the original
        result_df = df.copy()
        
        # Calculate time decay for each row
        now = datetime.now()
        result_df['time_decay'] = result_df['timestamp'].apply(
            lambda x: self.calculate_time_decay(x, now)
        )
        
        # Apply source weighting
        result_df['source_weight'] = result_df['source'].apply(self.get_source_weight)
        
        # Calculate total weight (time decay * source weight)
        result_df['weight'] = result_df['time_decay'] * result_df['source_weight']
        
        # Calculate weighted sentiment
        result_df['weighted_sentiment'] = result_df['sentiment'] * result_df['weight']
        
        return result_df
        
    def aggregate_by_ticker(self, df):
        """
        Aggregate sentiment data by ticker
        
        Args:
            df: DataFrame with sentiment data including weighted_sentiment
            
        Returns:
            DataFrame with aggregated metrics by ticker
        """
        if df.empty:
            return pd.DataFrame()
            
        # Check if weight column exists
        if 'weight' not in df.columns:
            df = self.calculate_weighted_sentiment(df)
            
        # Group by ticker and aggregate
        agg_df = df.groupby('ticker').agg(
            count=('sentiment', 'count'),
            total_weight=('weight', 'sum'),
            sum_weighted=('weighted_sentiment', 'sum'),
            min_sentiment=('sentiment', 'min'),
            max_sentiment=('sentiment', 'max'),
            std_sentiment=('sentiment', 'std'),
            newest_timestamp=('timestamp', 'max'),
            oldest_timestamp=('timestamp', 'min')
        ).reset_index()
        
        # Calculate average weighted sentiment
        agg_df['avg_sentiment'] = agg_df['sum_weighted'] / agg_df['total_weight']
        
        # Fix NaN values that might occur if total_weight is zero
        agg_df['avg_sentiment'] = agg_df['avg_sentiment'].fillna(0)
        
        # Add volatility metric (std / range or just std if range small)
        agg_df['sentiment_range'] = agg_df['max_sentiment'] - agg_df['min_sentiment']
        agg_df['volatility'] = agg_df.apply(
            lambda x: x['std_sentiment'] if x['sentiment_range'] < 0.1 
                     else x['std_sentiment'] / x['sentiment_range'],
            axis=1
        )
        
        return agg_df
        
    def get_top_sentiment(self, df, n=10, metric='avg_sentiment'):
        """
        Get top N tickers by specified sentiment metric
        
        Args:
            df: DataFrame with sentiment data
            n: Number of top tickers to return
            metric: Metric to sort by (avg_sentiment, volatility, etc)
            
        Returns:
            DataFrame with top N tickers
        """
        # Aggregate if not already aggregated
        if 'avg_sentiment' not in df.columns:
            df = self.aggregate_by_ticker(df)
            
        if df.empty:
            return pd.DataFrame()
            
        # Sort by the specified metric (descending) and take top N
        sorted_df = df.sort_values(by=metric, ascending=False).head(n)
        
        return sorted_df