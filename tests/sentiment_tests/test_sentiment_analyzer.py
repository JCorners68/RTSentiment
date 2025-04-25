"""
Tests for the sentiment analyzer
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the module to test
from sentiment_analyzer.models.sentiment_analyzer import SentimentAnalyzer

class TestSentimentAnalyzer(unittest.TestCase):
    """Test cases for SentimentAnalyzer class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = SentimentAnalyzer()
        
        # Create sample data
        self.sample_data = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'AAPL', 'GOOGL', 'AAPL', 'MSFT'],
            'sentiment': [0.8, 0.5, -0.3, 0.2, 0.9, -0.1],
            'source': ['news', 'reddit', 'twitter', 'news', 'news', 'twitter'],
            'timestamp': [
                datetime.now() - timedelta(hours=1),
                datetime.now() - timedelta(hours=2),
                datetime.now() - timedelta(hours=12),
                datetime.now() - timedelta(hours=24),
                datetime.now() - timedelta(hours=36),
                datetime.now() - timedelta(hours=48)
            ]
        })
        
    def test_time_decay(self):
        """Test time decay calculation"""
        now = datetime.now()
        
        # Test decay at various time points
        test_times = [
            now,  # Now should be 1.0
            now - timedelta(hours=self.analyzer.decay_half_life),  # Half-life should be 0.5
            now - timedelta(hours=self.analyzer.decay_half_life * 2),  # 2x half-life should be 0.25
            now - timedelta(hours=self.analyzer.max_age_hours + 1)  # Beyond max age should be 0.0
        ]
        
        expected_values = [1.0, 0.5, 0.25, 0.0]
        
        for i, test_time in enumerate(test_times):
            decay = self.analyzer.calculate_time_decay(test_time, now)
            self.assertAlmostEqual(decay, expected_values[i], delta=0.01,
                                 msg=f"Decay at {test_time} should be {expected_values[i]}")
                                 
    def test_source_weights(self):
        """Test source weighting"""
        # Test known sources
        self.assertEqual(self.analyzer.get_source_weight('news'), 1.0)
        self.assertEqual(self.analyzer.get_source_weight('reddit'), 0.7)
        self.assertEqual(self.analyzer.get_source_weight('twitter'), 0.5)
        
        # Test unknown source (should default to 1.0)
        self.assertEqual(self.analyzer.get_source_weight('unknown'), 1.0)
        
    def test_weighted_sentiment(self):
        """Test weighted sentiment calculation"""
        # Calculate weighted sentiment
        result = self.analyzer.calculate_weighted_sentiment(self.sample_data)
        
        # Check that all expected columns exist
        expected_columns = ['time_decay', 'source_weight', 'weight', 'weighted_sentiment']
        for col in expected_columns:
            self.assertIn(col, result.columns)
            
        # Check that weight calculation is correct
        # weight = time_decay * source_weight
        self.assertAlmostEqual(
            result.loc[0, 'weight'],
            result.loc[0, 'time_decay'] * result.loc[0, 'source_weight'],
            delta=0.00001
        )
        
        # Check that weighted sentiment calculation is correct
        # weighted_sentiment = sentiment * weight
        self.assertAlmostEqual(
            result.loc[0, 'weighted_sentiment'],
            result.loc[0, 'sentiment'] * result.loc[0, 'weight'],
            delta=0.00001
        )
        
    def test_aggregate_by_ticker(self):
        """Test ticker aggregation"""
        # Calculate weighted sentiment and aggregate
        weighted_df = self.analyzer.calculate_weighted_sentiment(self.sample_data)
        result = self.analyzer.aggregate_by_ticker(weighted_df)
        
        # Check that we get the expected tickers
        expected_tickers = ['AAPL', 'MSFT', 'GOOGL']
        actual_tickers = result['ticker'].tolist()
        self.assertCountEqual(actual_tickers, expected_tickers)
        
        # Check that counts are correct
        aapl_data = result[result['ticker'] == 'AAPL']
        self.assertEqual(aapl_data['count'].values[0], 3)
        
        # Check that min/max sentiment is correct
        aapl_sentiments = self.sample_data[self.sample_data['ticker'] == 'AAPL']['sentiment']
        self.assertAlmostEqual(aapl_data['min_sentiment'].values[0], min(aapl_sentiments), delta=0.00001)
        self.assertAlmostEqual(aapl_data['max_sentiment'].values[0], max(aapl_sentiments), delta=0.00001)
        
    def test_top_sentiment(self):
        """Test getting top sentiment"""
        # Calculate weighted sentiment, aggregate, and get top
        weighted_df = self.analyzer.calculate_weighted_sentiment(self.sample_data)
        aggregated_df = self.analyzer.aggregate_by_ticker(weighted_df)
        result = self.analyzer.get_top_sentiment(aggregated_df, n=2)
        
        # Should have 2 rows
        self.assertEqual(len(result), 2)
        
        # First row should have higher avg_sentiment than second
        self.assertGreater(result.iloc[0]['avg_sentiment'], result.iloc[1]['avg_sentiment'])
        
if __name__ == '__main__':
    unittest.main()