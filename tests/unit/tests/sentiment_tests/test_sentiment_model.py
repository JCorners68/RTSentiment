import unittest
import datetime
from unittest.mock import MagicMock, patch

from sentiment_analyzer.models.sentiment_model import SentimentModel
from sentiment_analyzer.data.redis_manager import RedisSentimentCache


class TestSentimentModel(unittest.TestCase):
    
    def setUp(self):
        self.redis_cache = MagicMock(spec=RedisSentimentCache)
        self.model = SentimentModel(self.redis_cache, decay_type="exponential", decay_half_life=24)
        
    def test_calculate_sentiment_score_empty(self):
        """Test sentiment calculation with no events."""
        self.redis_cache.get_ticker_events.return_value = []
        
        score = self.model.calculate_sentiment_score("AAPL")
        
        self.assertEqual(score, 0.0)
        self.redis_cache.get_ticker_events.assert_called_once_with("AAPL")
        
    def test_calculate_sentiment_score_with_events(self):
        """Test sentiment calculation with sample events."""
        now = datetime.datetime.now()
        test_events = [
            {
                'ticker': 'AAPL',
                'timestamp': now - datetime.timedelta(hours=1),
                'sentiment': 0.8,
                'source_type': 'news',
                'source_name': 'reuters'
            },
            {
                'ticker': 'AAPL',
                'timestamp': now - datetime.timedelta(hours=10),
                'sentiment': -0.3,
                'source_type': 'reddit',
                'source_name': 'wallstreetbets'
            }
        ]
        
        self.redis_cache.get_ticker_events.return_value = test_events
        
        with patch('sentiment_analyzer.models.impact_scoring.calculate_impact') as mock_impact:
            # Configure the mock to return a fixed impact score
            mock_impact.return_value = 0.75
            
            score = self.model.calculate_sentiment_score("AAPL", now)
            
            # Verify the score is calculated correctly
            self.assertNotEqual(score, 0.0)
            self.redis_cache.get_ticker_events.assert_called_once_with("AAPL")
            mock_impact.assert_called()
            
    def test_update_sentiment(self):
        """Test updating sentiment with a new event."""
        event = {
            'ticker': 'TSLA',
            'timestamp': datetime.datetime.now(),
            'sentiment': 0.5,
            'source_type': 'twitter',
            'source_name': 'verified'
        }
        
        # Mock calculate_sentiment_score to return a fixed value
        self.model.calculate_sentiment_score = MagicMock(return_value=42.0)
        
        self.model.update_sentiment(event)
        
        # Verify the event was added to Redis and the score was updated
        self.redis_cache.add_ticker_event.assert_called_once_with('TSLA', event)
        self.model.calculate_sentiment_score.assert_called_once_with('TSLA')
        self.redis_cache.update_ticker_score.assert_called_once_with('TSLA', 42.0)
        
    def test_get_top_tickers_sentiment(self):
        """Test getting sentiment for top tickers."""
        tickers = ['AAPL', 'MSFT', 'GOOG']
        
        # Mock calculate_sentiment_score to return different values for each ticker
        self.model.calculate_sentiment_score = MagicMock(side_effect=[75.0, 30.0, -20.0])
        
        result = self.model.get_top_tickers_sentiment(tickers)
        
        # Verify the result contains the expected values
        expected = {'AAPL': 75.0, 'MSFT': 30.0, 'GOOG': -20.0}
        self.assertEqual(result, expected)
        
        # Verify calculate_sentiment_score was called for each ticker
        self.assertEqual(self.model.calculate_sentiment_score.call_count, 3)


if __name__ == '__main__':
    unittest.main()