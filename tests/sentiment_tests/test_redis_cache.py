import unittest
import datetime
from unittest.mock import patch, MagicMock
from sentiment_analyzer.data.redis_manager import RedisSentimentCache


class TestRedisSentimentCache(unittest.TestCase):
    
    def setUp(self):
        # Create a Redis mock
        self.redis_mock = MagicMock()
        
        # Patch the Redis client
        with patch('redis.Redis', return_value=self.redis_mock):
            self.cache = RedisSentimentCache(
                host='localhost',
                port=6379,
                db=0,
                event_expiry_seconds=3600
            )
            
    def test_serialize_deserialize_event(self):
        """Test serialization and deserialization of events."""
        # Create a test event with datetime
        now = datetime.datetime.now()
        event = {
            'ticker': 'AAPL',
            'timestamp': now,
            'sentiment': 0.75,
            'source': 'test'
        }
        
        # Serialize
        serialized = self.cache._serialize_event(event)
        
        # Should be a JSON string
        self.assertIsInstance(serialized, str)
        
        # Datetime should be converted to ISO format
        self.assertNotIn("datetime.datetime", serialized)
        self.assertIn(now.isoformat(), serialized)
        
        # Deserialize
        deserialized = self.cache._deserialize_event(serialized)
        
        # Should convert ISO timestamp back to datetime
        self.assertIsInstance(deserialized['timestamp'], datetime.datetime)
        
        # Values should match original
        self.assertEqual(deserialized['ticker'], event['ticker'])
        self.assertEqual(deserialized['sentiment'], event['sentiment'])
        self.assertEqual(deserialized['source'], event['source'])
        
    def test_add_ticker_event(self):
        """Test adding a ticker event to Redis."""
        # Create a test event
        event = {
            'ticker': 'TSLA',
            'timestamp': datetime.datetime.now(),
            'sentiment': -0.25,
            'source': 'test'
        }
        
        # Add to Redis
        self.cache.add_ticker_event('TSLA', event)
        
        # Verify ZADD was called correctly
        self.redis_mock.zadd.assert_called_once()
        
        # Verify expiry was set
        self.redis_mock.expire.assert_called_once()
        
        # Verify arguments to zadd included serialized event
        zadd_args = self.redis_mock.zadd.call_args[0]
        zadd_kwargs = self.redis_mock.zadd.call_args[1]
        
        # The first argument should be the key (events_key)
        self.assertIn("sentiment:events:TSLA", str(zadd_args) + str(zadd_kwargs))
        
    def test_get_ticker_events(self):
        """Test retrieving ticker events from Redis."""
        # Mock Redis response for ZRANGE
        serialized_event1 = self.cache._serialize_event({
            'ticker': 'AAPL',
            'timestamp': datetime.datetime.now(),
            'sentiment': 0.5
        })
        serialized_event2 = self.cache._serialize_event({
            'ticker': 'AAPL',
            'timestamp': datetime.datetime.now() - datetime.timedelta(hours=1),
            'sentiment': -0.3
        })
        
        # Mock zrange to return encoded byte strings (as Redis would)
        self.redis_mock.zrange.return_value = [
            serialized_event1.encode('utf-8'),
            serialized_event2.encode('utf-8')
        ]
        
        # Get events
        events = self.cache.get_ticker_events('AAPL')
        
        # Verify ZRANGE was called
        self.redis_mock.zrange.assert_called_once()
        
        # Should return 2 deserialized events
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['ticker'], 'AAPL')
        self.assertEqual(events[1]['ticker'], 'AAPL')
        
    def test_update_get_ticker_score(self):
        """Test updating and retrieving ticker sentiment scores."""
        # Update score
        self.cache.update_ticker_score('NVDA', 42.5)
        
        # Verify SET was called
        self.redis_mock.set.assert_called_once()
        
        # Mock GET response
        self.redis_mock.get.return_value = b'42.5'
        
        # Get score
        score = self.cache.get_ticker_score('NVDA')
        
        # Verify GET was called
        self.redis_mock.get.assert_called_once()
        
        # Should return the correct score
        self.assertEqual(score, 42.5)
        
    def test_get_all_ticker_scores(self):
        """Test retrieving all ticker scores."""
        # Mock KEYS response
        self.redis_mock.keys.return_value = [
            b'sentiment:score:AAPL',
            b'sentiment:score:MSFT',
            b'sentiment:score:GOOG'
        ]
        
        # Mock GET responses
        def mock_get(key):
            if b'AAPL' in key:
                return b'75.0'
            elif b'MSFT' in key:
                return b'30.0'
            elif b'GOOG' in key:
                return b'-20.0'
            return None
            
        self.redis_mock.get.side_effect = mock_get
        
        # Get all scores
        scores = self.cache.get_all_ticker_scores()
        
        # Verify KEYS was called
        self.redis_mock.keys.assert_called_once()
        
        # Should return correct scores for all tickers
        self.assertEqual(len(scores), 3)
        self.assertEqual(scores['AAPL'], 75.0)
        self.assertEqual(scores['MSFT'], 30.0)
        self.assertEqual(scores['GOOG'], -20.0)


if __name__ == '__main__':
    unittest.main()