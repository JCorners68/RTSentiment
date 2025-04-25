"""
Integration tests for the Parquet-based sentiment analysis pipeline.

This module tests the end-to-end functionality of the Parquet integration in the
sentiment analysis system, including:
1. ParquetReader and ParquetWriter utilities
2. Integration with the sentiment analysis pipeline
3. Performance benchmarks
4. Data quality validation
5. Load testing with simulated data
"""

import unittest
import os
import tempfile
import shutil
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import asyncio
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

# Import modules to test
from sentiment_service.utils.parquet_reader import ParquetReader
from sentiment_service.utils.data_verification import DataVerification
from sentiment_service.utils.redis_sentiment_cache import RedisSentimentCache
from sentiment_service.models.finbert import FinBertModel
from sentiment_service.models.model_factory import ModelFactory, DataSourceType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParquetWriterMock:
    """Mock class for ParquetWriter"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def write_sentiment_data(self, ticker: str, data: List[Dict[str, Any]]):
        """Write sentiment data to parquet file"""
        if not data:
            return
            
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Add timestamp if not present
        if 'timestamp' not in df.columns:
            df['timestamp'] = datetime.now().isoformat()
            
        # Ensure ticker is present and consistent
        df['ticker'] = ticker.upper()
        
        # Write to parquet file
        file_path = os.path.join(self.data_dir, f"{ticker.lower()}_sentiment.parquet")
        df.to_parquet(file_path, index=False)
        
        return file_path


class TestParquetReader(unittest.TestCase):
    """Unit tests for the ParquetReader class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Create mock data
        self.writer = ParquetWriterMock(self.test_dir)
        
        # Create test data for AAPL
        self.aapl_data = [
            {
                "timestamp": "2025-04-01T10:00:00Z",
                "ticker": "AAPL",
                "sentiment": 0.75,
                "confidence": 0.85,
                "source": "news",
                "model": "finbert",
                "article_id": "news-001",
                "article_title": "Apple reports record profits"
            },
            {
                "timestamp": "2025-04-02T11:00:00Z",
                "ticker": "AAPL",
                "sentiment": 0.65,
                "confidence": 0.75,
                "source": "reddit",
                "model": "finbert",
                "article_id": "reddit-001",
                "article_title": "AAPL looking strong"
            },
            {
                "timestamp": "2025-04-03T12:00:00Z",
                "ticker": "AAPL",
                "sentiment": -0.2,
                "confidence": 0.6,
                "source": "twitter",
                "model": "finbert",
                "article_id": "twitter-001",
                "article_title": "Apple facing supply chain issues"
            }
        ]
        
        # Create test data for TSLA
        self.tsla_data = [
            {
                "timestamp": "2025-04-01T09:00:00Z",
                "ticker": "TSLA",
                "sentiment": 0.8,
                "confidence": 0.9,
                "source": "news",
                "model": "finbert",
                "article_id": "news-002",
                "article_title": "Tesla delivers record number of vehicles"
            },
            {
                "timestamp": "2025-04-02T10:00:00Z",
                "ticker": "TSLA",
                "sentiment": -0.4,
                "confidence": 0.7,
                "source": "reddit",
                "model": "finbert",
                "article_id": "reddit-002",
                "article_title": "Concerns about Tesla production"
            }
        ]
        
        # Write test data
        self.writer.write_sentiment_data("AAPL", self.aapl_data)
        self.writer.write_sentiment_data("TSLA", self.tsla_data)
        
        # Create ParquetReader instance
        self.reader = ParquetReader(data_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_list_parquet_files(self):
        """Test listing Parquet files."""
        # Test listing all files
        all_files = self.reader._list_parquet_files()
        self.assertEqual(len(all_files), 2)
        
        # Test listing files for specific ticker
        aapl_files = self.reader._list_parquet_files("AAPL")
        self.assertEqual(len(aapl_files), 1)
        self.assertIn("aapl_sentiment.parquet", aapl_files[0])
        
        # Test listing non-existent ticker
        non_existent = self.reader._list_parquet_files("NONEXISTENT")
        self.assertEqual(len(non_existent), 0)
    
    def test_get_all_tickers(self):
        """Test getting all available tickers."""
        tickers = self.reader.get_all_tickers()
        self.assertEqual(len(tickers), 2)
        self.assertIn("AAPL", tickers)
        self.assertIn("TSLA", tickers)
    
    def test_read_ticker_data(self):
        """Test reading ticker data."""
        # Test reading AAPL data
        aapl_df = self.reader.read_ticker_data("AAPL")
        self.assertEqual(len(aapl_df), 3)
        
        # Test reading TSLA data
        tsla_df = self.reader.read_ticker_data("TSLA")
        self.assertEqual(len(tsla_df), 2)
        
        # Test reading non-existent ticker
        non_existent = self.reader.read_ticker_data("NONEXISTENT")
        self.assertTrue(non_existent.empty)
    
    def test_query(self):
        """Test querying sentiment data."""
        # Test querying specific ticker
        aapl_query = self.reader.query(tickers=["AAPL"])
        self.assertEqual(len(aapl_query), 3)
        
        # Test querying with date range
        date_query = self.reader.query(
            start_date="2025-04-02T00:00:00Z",
            end_date="2025-04-03T23:59:59Z"
        )
        self.assertEqual(len(date_query), 3)
        
        # Test querying with source filter
        source_query = self.reader.query(sources=["news"])
        self.assertEqual(len(source_query), 2)
        
        # Test querying with sentiment range
        sentiment_query = self.reader.query(min_sentiment=0.7)
        self.assertEqual(len(sentiment_query), 2)
        
        # Test querying with multiple filters
        complex_query = self.reader.query(
            tickers=["AAPL"],
            sources=["news"],
            min_sentiment=0.7
        )
        self.assertEqual(len(complex_query), 1)
    
    def test_get_latest_events(self):
        """Test getting latest events."""
        latest = self.reader.get_latest_events(limit=5)
        self.assertEqual(len(latest), 5)
        
        # Test with smaller limit
        limited = self.reader.get_latest_events(limit=2)
        self.assertEqual(len(limited), 2)
    
    def test_get_average_sentiment(self):
        """Test getting average sentiment."""
        # Test average for AAPL
        aapl_avg = self.reader.get_average_sentiment("AAPL")
        self.assertGreater(aapl_avg, 0)
        
        # Test average for TSLA
        tsla_avg = self.reader.get_average_sentiment("TSLA")
        self.assertIsInstance(tsla_avg, float)
        
        # Test average for non-existent ticker
        non_existent = self.reader.get_average_sentiment("NONEXISTENT")
        self.assertEqual(non_existent, 0.0)
    
    def test_get_sentiment_distribution(self):
        """Test getting sentiment distribution."""
        # Test distribution for AAPL
        aapl_dist = self.reader.get_sentiment_distribution("AAPL")
        self.assertIn("positive", aapl_dist)
        self.assertIn("neutral", aapl_dist)
        self.assertIn("negative", aapl_dist)
        
        # Check that positive count is correct
        self.assertEqual(aapl_dist["positive"], 2)  # 0.75 and 0.65 are positive
    
    def test_get_sentiment_by_source(self):
        """Test getting sentiment by source."""
        # Test sentiment by source for AAPL
        aapl_sources = self.reader.get_sentiment_by_source("AAPL")
        self.assertIn("news", aapl_sources)
        self.assertIn("reddit", aapl_sources)
        self.assertIn("twitter", aapl_sources)
        
        # Check source sentiment values
        self.assertGreater(aapl_sources["news"], 0)
        self.assertGreater(aapl_sources["reddit"], 0)
        self.assertLess(aapl_sources["twitter"], 0)
    
    def test_get_sentiment_trend(self):
        """Test getting sentiment trend."""
        # Test sentiment trend for AAPL
        aapl_trend = self.reader.get_sentiment_trend("AAPL")
        self.assertGreater(len(aapl_trend), 0)
        self.assertIn("timestamp", aapl_trend.columns)
        self.assertIn("sentiment", aapl_trend.columns)
    
    def test_cache_functionality(self):
        """Test caching functionality."""
        # Clear cache initially
        self.reader.clear_cache()
        
        # First query (cache miss)
        start_time = time.time()
        self.reader.query(tickers=["AAPL"])
        first_query_time = time.time() - start_time
        
        # Second query (cache hit)
        start_time = time.time()
        self.reader.query(tickers=["AAPL"])
        second_query_time = time.time() - start_time
        
        # Check metrics
        metrics = self.reader.get_metrics()
        self.assertGreater(metrics["cache_hits"], 0)
        
        # Cache hit should be faster
        self.assertLess(second_query_time, first_query_time)


class TestDataVerification(unittest.TestCase):
    """Tests for the DataVerification class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create DataVerification instance
        self.verifier = DataVerification()
        
        # Test data
        self.valid_data = {
            "timestamp": "2025-04-01T10:00:00Z",
            "ticker": "AAPL",
            "sentiment": 0.75,
            "confidence": 0.85,
            "source": "news",
            "model": "finbert",
            "article_id": "news-001",
            "article_title": "Apple reports record profits"
        }
        
        self.invalid_data = {
            "timestamp": "not-a-date",
            "ticker": 123,  # Should be string
            "sentiment": "high",  # Should be float
            "source": "news"
            # Missing required fields
        }
    
    def test_verify_required_fields(self):
        """Test verification of required fields."""
        # Test with valid data
        valid_result = self.verifier.verify_required_fields(self.valid_data)
        self.assertTrue(valid_result)
        
        # Test with invalid data
        invalid_result = self.verifier.verify_required_fields(self.invalid_data)
        self.assertFalse(invalid_result)
    
    def test_validate_data_types(self):
        """Test validation of data types."""
        # Test with valid data
        valid_result, valid_errors = self.verifier.validate_data_types(self.valid_data)
        self.assertTrue(valid_result)
        self.assertEqual(len(valid_errors), 0)
        
        # Test with invalid data
        invalid_result, invalid_errors = self.verifier.validate_data_types(self.invalid_data)
        self.assertFalse(invalid_result)
        self.assertGreater(len(invalid_errors), 0)
    
    def test_sanitize_timestamp(self):
        """Test timestamp sanitization."""
        # Test with valid ISO format
        valid_ts = "2025-04-01T10:00:00Z"
        sanitized_valid = self.verifier.sanitize_timestamp(valid_ts)
        self.assertEqual(sanitized_valid, valid_ts)
        
        # Test with invalid format but convertible date
        invalid_ts = "April 1, 2025"
        sanitized_invalid = self.verifier.sanitize_timestamp(invalid_ts)
        self.assertIsNotNone(sanitized_invalid)
        self.assertIn("T", sanitized_invalid)
        
        # Test with completely invalid date
        very_invalid_ts = "not a date at all"
        sanitized_very_invalid = self.verifier.sanitize_timestamp(very_invalid_ts)
        self.assertIsNotNone(sanitized_very_invalid)  # Should return current time
    
    def test_sanitize_ticker(self):
        """Test ticker sanitization."""
        # Test with valid ticker
        valid_ticker = "AAPL"
        sanitized_valid = self.verifier.sanitize_ticker(valid_ticker)
        self.assertEqual(sanitized_valid, "AAPL")
        
        # Test with lowercase ticker
        lower_ticker = "tsla"
        sanitized_lower = self.verifier.sanitize_ticker(lower_ticker)
        self.assertEqual(sanitized_lower, "TSLA")
        
        # Test with ticker that needs trimming
        space_ticker = " MSFT "
        sanitized_space = self.verifier.sanitize_ticker(space_ticker)
        self.assertEqual(sanitized_space, "MSFT")
        
        # Test with numeric ticker
        numeric_ticker = 123
        sanitized_numeric = self.verifier.sanitize_ticker(numeric_ticker)
        self.assertEqual(sanitized_numeric, "123")
    
    def test_sentiment_range_validation(self):
        """Test sentiment range validation."""
        # Test with sentiment in range
        in_range = 0.75
        valid_result = self.verifier.validate_sentiment_range(in_range)
        self.assertTrue(valid_result)
        
        # Test with sentiment out of range (too high)
        too_high = 1.5
        high_result = self.verifier.validate_sentiment_range(too_high)
        self.assertFalse(high_result)
        
        # Test with sentiment out of range (too low)
        too_low = -1.5
        low_result = self.verifier.validate_sentiment_range(too_low)
        self.assertFalse(low_result)
    
    def test_sanitize_record(self):
        """Test record sanitization."""
        # Create a record with issues
        problematic_record = {
            "timestamp": "April 1, 2025",
            "ticker": "aapl ",
            "sentiment": 1.5,  # Out of range
            "confidence": 0.85,
            "source": "news",
            "model": "finbert"
        }
        
        # Sanitize the record
        sanitized = self.verifier.sanitize_record(problematic_record)
        
        # Check sanitized values
        self.assertIn("T", sanitized["timestamp"])  # ISO format
        self.assertEqual(sanitized["ticker"], "AAPL")  # Uppercase and trimmed
        self.assertEqual(sanitized["sentiment"], 1.0)  # Clamped to valid range


class TestRedisCache(unittest.TestCase):
    """Tests for the Redis sentiment cache."""
    
    @classmethod
    def setUpClass(cls):
        """Set up Redis mock for testing."""
        # This is a mock implementation since we can't assume Redis is available
        cls.redis_mock = {}
        cls.redis_sets = {}
        cls.redis_expiry = {}
    
    def setUp(self):
        """Set up test environment for each test."""
        self.cache = RedisSentimentCache(host="localhost", port=6379)
        # Replace Redis client with mock implementation
        self.cache.client = self
        self.cache.is_connected = True
    
    async def get(self, key):
        """Mock Redis get."""
        return self.redis_mock.get(key)
    
    async def setex(self, key, expire, value):
        """Mock Redis setex."""
        self.redis_mock[key] = value
        self.redis_expiry[key] = time.time() + expire
    
    async def sadd(self, key, *values):
        """Mock Redis sadd."""
        if key not in self.redis_sets:
            self.redis_sets[key] = set()
        for value in values:
            self.redis_sets[key].add(value)
    
    async def smembers(self, key):
        """Mock Redis smembers."""
        return self.redis_sets.get(key, set())
    
    async def delete(self, key):
        """Mock Redis delete."""
        if key in self.redis_mock:
            del self.redis_mock[key]
        if key in self.redis_expiry:
            del self.redis_expiry[key]
    
    async def test_cache_ticker_sentiment(self):
        """Test caching ticker sentiment."""
        # Test data
        ticker = "AAPL"
        sentiment_data = {
            "ticker": ticker,
            "sentiment": "positive",
            "score": 0.75,
            "weight": 1.2,
            "count": 250,
            "model": "aggregate"
        }
        
        # Cache the data
        await self.cache.cache_ticker_sentiment(ticker, sentiment_data)
        
        # Check that data was cached
        key = self.cache._get_ticker_key(ticker)
        self.assertIn(key, self.redis_mock)
        
        # Check that ticker was added to available tickers
        self.assertIn(ticker, await self.cache.get_available_tickers())
    
    async def test_get_ticker_sentiment(self):
        """Test retrieving ticker sentiment."""
        # Test data
        ticker = "AAPL"
        sentiment_data = {
            "ticker": ticker,
            "sentiment": "positive",
            "score": 0.75,
            "weight": 1.2,
            "count": 250,
            "model": "aggregate"
        }
        
        # Cache the data
        await self.cache.cache_ticker_sentiment(ticker, sentiment_data)
        
        # Retrieve the data
        retrieved = await self.cache.get_ticker_sentiment(ticker)
        
        # Check that retrieved data matches original
        self.assertEqual(retrieved["ticker"], ticker)
        self.assertEqual(retrieved["score"], sentiment_data["score"])
    
    async def test_cache_historical_sentiment(self):
        """Test caching historical sentiment data."""
        # Test data
        ticker = "AAPL"
        timestamp = "2025-04-01T10:00:00Z"
        sentiment_data = {
            "ticker": ticker,
            "timestamp": timestamp,
            "sentiment": "positive",
            "score": 0.75,
            "source": "news",
            "count": 10,
            "model": "finbert"
        }
        
        # Cache the data
        await self.cache.cache_historical_ticker_sentiment(ticker, timestamp, sentiment_data)
        
        # Check that data was cached
        key = self.cache._get_ticker_key(ticker, timestamp)
        self.assertIn(key, self.redis_mock)
    
    async def test_batch_cache_operations(self):
        """Test batch caching operations."""
        # Test data
        ticker_sentiments = {
            "AAPL": {
                "ticker": "AAPL",
                "sentiment": "positive",
                "score": 0.75,
                "weight": 1.2,
                "count": 250,
                "model": "aggregate"
            },
            "TSLA": {
                "ticker": "TSLA",
                "sentiment": "negative",
                "score": -0.3,
                "weight": 1.0,
                "count": 150,
                "model": "aggregate"
            }
        }
        
        # Batch cache the data
        await self.cache.batch_cache_ticker_sentiments(ticker_sentiments)
        
        # Check that all data was cached
        for ticker in ticker_sentiments:
            key = self.cache._get_ticker_key(ticker)
            self.assertIn(key, self.redis_mock)
            self.assertIn(ticker, await self.cache.get_available_tickers())
    
    async def test_timerange_caching(self):
        """Test caching and retrieving timerange information."""
        # Test data
        ticker = "AAPL"
        start_date = "2025-01-01T00:00:00Z"
        end_date = "2025-04-01T00:00:00Z"
        
        # Cache timerange as available
        await self.cache.cache_parquet_timerange(ticker, start_date, end_date, available=True)
        
        # Retrieve timerange
        timerange = await self.cache.get_parquet_timerange(ticker, start_date, end_date)
        
        # Check timerange information
        self.assertIsNotNone(timerange)
        self.assertTrue(timerange["available"])
        self.assertEqual(timerange["start_date"], start_date)
        self.assertEqual(timerange["end_date"], end_date)


class TestParquetPipeline(unittest.TestCase):
    """Integration tests for the Parquet sentiment pipeline."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Create mock data
        self.writer = ParquetWriterMock(self.test_dir)
        
        # Create test data
        self.sample_data = [
            {
                "timestamp": "2025-04-01T10:00:00Z",
                "ticker": "AAPL",
                "sentiment": 0.75,
                "confidence": 0.85,
                "source": "news",
                "model": "finbert",
                "article_id": "news-001",
                "article_title": "Apple reports record profits",
                "text_snippet": "Apple Inc. reported record quarterly profits today, exceeding analyst expectations."
            },
            {
                "timestamp": "2025-04-02T11:00:00Z",
                "ticker": "TSLA",
                "sentiment": -0.4,
                "confidence": 0.7,
                "source": "reddit",
                "model": "finbert",
                "article_id": "reddit-001",
                "article_title": "Concerns about Tesla production",
                "text_snippet": "Tesla's production numbers might not meet expectations this quarter due to supply issues."
            }
        ]
        
        # Write multi-ticker data
        self.writer.write_sentiment_data("multi_ticker", self.sample_data)
        
        # Create individual ticker files
        for item in self.sample_data:
            ticker = item["ticker"]
            self.writer.write_sentiment_data(ticker, [item])
        
        # Initialize components
        self.reader = ParquetReader(data_dir=self.test_dir)
        self.verifier = DataVerification()
        
        # Set up FinBERT model
        self.model = FinBertModel()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_end_to_end_pipeline(self):
        """Test the end-to-end sentiment pipeline with Parquet data."""
        # Test retrieving data for a ticker
        aapl_data = self.reader.read_ticker_data("AAPL")
        self.assertEqual(len(aapl_data), 1)
        
        # Extract text for analysis
        text = aapl_data.iloc[0]["text_snippet"]
        self.assertIsNotNone(text)
        
        # Create model factory
        factory = ModelFactory()
        
        # Analyze sentiment
        result = asyncio.run(factory.analyze_text(text, ["AAPL"]))
        
        # Check result contains basic fields
        self.assertIsNotNone(result)
        self.assertIn("sentiment", result)
        self.assertIn("score", result)
        self.assertIn("tickers", result)
        
        # Check ticker is correct
        self.assertIn("AAPL", result["tickers"])
    
    def test_data_verification_pipeline(self):
        """Test data verification within the pipeline."""
        # Get all data
        all_data = self.reader.query()
        
        # Verify and sanitize each record
        valid_count = 0
        invalid_count = 0
        
        for _, row in all_data.iterrows():
            record = row.to_dict()
            
            # Verify required fields
            has_required = self.verifier.verify_required_fields(record)
            
            # Validate data types
            valid_types, _ = self.verifier.validate_data_types(record)
            
            # Sanitize record
            sanitized = self.verifier.sanitize_record(record)
            
            # Check if sanitized record passes validation
            sanitized_valid, _ = self.verifier.validate_data_types(sanitized)
            
            if has_required and valid_types:
                valid_count += 1
            else:
                invalid_count += 1
            
            # Sanitized record should always pass validation
            self.assertTrue(sanitized_valid)
        
        # All original test data should be valid
        self.assertEqual(invalid_count, 0)
        self.assertEqual(valid_count, len(all_data))
    
    def test_ticker_specific_analysis(self):
        """Test ticker-specific sentiment analysis."""
        # Create model factory
        factory = ModelFactory()
        
        # Analyze ticker sentiment
        result = asyncio.run(factory.analyze_ticker_sentiment("AAPL", self.reader))
        
        # Check result
        self.assertIsNotNone(result)
        self.assertIn("ticker", result)
        self.assertEqual(result["ticker"], "AAPL")
        self.assertIn("sentiment", result)
        self.assertIn("score", result)
        
        # Score should be a float
        self.assertIsInstance(result["score"], float)


class ParquetPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmarks for Parquet-based sentiment analysis."""
    
    @classmethod
    def setUpClass(cls):
        """Set up benchmark data once for all tests."""
        # Create temporary directory for benchmark data
        cls.benchmark_dir = tempfile.mkdtemp()
        
        # Create mock writer
        cls.writer = ParquetWriterMock(cls.benchmark_dir)
        
        # Generate benchmark data (larger dataset)
        cls.tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
        cls.sources = ["news", "reddit", "twitter", "sec", "blog"]
        cls.models = ["finbert", "fingpt", "bert-sentiment"]
        
        # Generate 1000 records
        cls.benchmark_data = []
        
        for i in range(1000):
            # Create random data
            ticker = np.random.choice(cls.tickers)
            source = np.random.choice(cls.sources)
            model = np.random.choice(cls.models)
            sentiment = np.random.uniform(-1, 1)
            confidence = np.random.uniform(0.5, 1.0)
            
            # Create timestamp within last 30 days
            days_ago = np.random.randint(0, 30)
            hours_ago = np.random.randint(0, 24)
            timestamp = (datetime.now() - timedelta(days=days_ago, hours=hours_ago)).isoformat()
            
            # Create record
            record = {
                "timestamp": timestamp,
                "ticker": ticker,
                "sentiment": sentiment,
                "confidence": confidence,
                "source": source,
                "model": model,
                "article_id": f"bench-{i}",
                "article_title": f"Benchmark article {i}",
                "text_snippet": f"This is a benchmark text for {ticker} with sentiment {sentiment}."
            }
            
            cls.benchmark_data.append(record)
        
        # Write benchmark data
        cls.writer.write_sentiment_data("multi_ticker", cls.benchmark_data)
        
        # Write individual ticker files
        for ticker in cls.tickers:
            ticker_data = [item for item in cls.benchmark_data if item["ticker"] == ticker]
            cls.writer.write_sentiment_data(ticker, ticker_data)
        
        # Initialize reader
        cls.reader = ParquetReader(data_dir=cls.benchmark_dir)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up benchmark data."""
        shutil.rmtree(cls.benchmark_dir)
    
    def test_benchmark_query_performance(self):
        """Benchmark query performance."""
        # Warm up cache
        self.reader.query()
        self.reader.clear_cache()
        
        # Benchmark queries
        query_times = {}
        
        # Benchmark simple ticker query
        start_time = time.time()
        self.reader.query(tickers=["AAPL"])
        query_times["ticker_query"] = time.time() - start_time
        
        # Benchmark date range query
        start_time = time.time()
        self.reader.query(
            start_date=(datetime.now() - timedelta(days=15)).isoformat(),
            end_date=datetime.now().isoformat()
        )
        query_times["date_query"] = time.time() - start_time
        
        # Benchmark source filter query
        start_time = time.time()
        self.reader.query(sources=["news"])
        query_times["source_query"] = time.time() - start_time
        
        # Benchmark complex query
        start_time = time.time()
        self.reader.query(
            tickers=["AAPL", "MSFT"],
            start_date=(datetime.now() - timedelta(days=10)).isoformat(),
            end_date=datetime.now().isoformat(),
            sources=["news", "reddit"],
            min_sentiment=0.0
        )
        query_times["complex_query"] = time.time() - start_time
        
        # Check that queries are reasonably fast
        for query_type, query_time in query_times.items():
            print(f"{query_type}: {query_time:.4f} seconds")
            self.assertLess(query_time, 1.0, f"{query_type} took too long")
    
    def test_benchmark_cache_effectiveness(self):
        """Benchmark cache effectiveness."""
        # Clear cache
        self.reader.clear_cache()
        
        # First query (cache miss)
        start_time = time.time()
        self.reader.query(tickers=["AAPL"])
        first_query_time = time.time() - start_time
        
        # Second query (cache hit)
        start_time = time.time()
        self.reader.query(tickers=["AAPL"])
        second_query_time = time.time() - start_time
        
        # Cache hit should be significantly faster
        print(f"Cache miss: {first_query_time:.4f} seconds")
        print(f"Cache hit: {second_query_time:.4f} seconds")
        print(f"Speedup: {first_query_time / max(second_query_time, 0.0001):.2f}x")
        
        self.assertLess(second_query_time, first_query_time / 2)
    
    def test_benchmark_kafka_vs_parquet(self):
        """Simulate benchmark comparing Kafka and Parquet approaches."""
        # This is a simulated benchmark since we don't have access to the actual Kafka implementation
        
        # Simulated Kafka processing time (per record)
        kafka_processing_time = 0.01  # 10ms per record
        
        # Simulated Parquet batch processing
        start_time = time.time()
        all_data = self.reader.query()
        parquet_processing_time = time.time() - start_time
        
        # Calculate simulated times for processing all records
        simulated_kafka_time = len(all_data) * kafka_processing_time
        
        print(f"Simulated Kafka time: {simulated_kafka_time:.4f} seconds")
        print(f"Actual Parquet time: {parquet_processing_time:.4f} seconds")
        print(f"Speedup: {simulated_kafka_time / max(parquet_processing_time, 0.0001):.2f}x")
        
        # Parquet should be faster for batch processing
        self.assertLess(parquet_processing_time, simulated_kafka_time)
        
        # Measure time for sentiment analysis
        factory = ModelFactory()
        
        # Time for analyzing a single text from Kafka
        single_text = "Apple reported strong quarterly earnings today."
        
        start_time = time.time()
        asyncio.run(factory.analyze_text(single_text, ["AAPL"]))
        single_analysis_time = time.time() - start_time
        
        # Extrapolate to full dataset
        simulated_full_kafka_analysis = single_analysis_time * len(all_data)
        
        # Time for analyzing ticker sentiment from Parquet
        start_time = time.time()
        asyncio.run(factory.analyze_ticker_sentiment("AAPL", self.reader))
        ticker_analysis_time = time.time() - start_time
        
        print(f"Single text analysis: {single_analysis_time:.4f} seconds")
        print(f"Simulated full Kafka analysis: {simulated_full_kafka_analysis:.4f} seconds")
        print(f"Ticker analysis from Parquet: {ticker_analysis_time:.4f} seconds")
        print(f"Speedup: {simulated_full_kafka_analysis / max(ticker_analysis_time, 0.0001):.2f}x")
        
        # Parquet-based analysis should be faster
        self.assertLess(ticker_analysis_time, simulated_full_kafka_analysis)


class TestLoadSimulation(unittest.TestCase):
    """Load testing simulations for Parquet-based sentiment analysis."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Create ParquetReader instance
        self.reader = ParquetReader(data_dir=self.test_dir)
        
        # Create DataVerification instance
        self.verifier = DataVerification()
        
        # Set up FinBERT model
        self.model = FinBertModel()
        
        # Create model factory
        self.factory = ModelFactory()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_simulated_high_frequency_queries(self):
        """Simulate high-frequency queries to test performance under load."""
        # Create mock data for testing
        writer = ParquetWriterMock(self.test_dir)
        
        # Generate test data for multiple tickers
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
        
        # Generate 100 records per ticker
        for ticker in tickers:
            ticker_data = []
            for i in range(100):
                record = {
                    "timestamp": (datetime.now() - timedelta(days=i % 30)).isoformat(),
                    "ticker": ticker,
                    "sentiment": np.random.uniform(-1, 1),
                    "confidence": np.random.uniform(0.5, 1.0),
                    "source": np.random.choice(["news", "reddit", "twitter"]),
                    "model": "finbert",
                    "article_id": f"{ticker}-{i}",
                    "article_title": f"Test article {i} for {ticker}"
                }
                ticker_data.append(record)
            
            # Write ticker data
            writer.write_sentiment_data(ticker, ticker_data)
        
        # Simulate high-frequency queries
        query_count = 100
        query_times = []
        
        for i in range(query_count):
            # Select random ticker
            ticker = np.random.choice(tickers)
            
            # Select random time range
            days_back = np.random.randint(1, 30)
            start_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            end_date = datetime.now().isoformat()
            
            # Time the query
            start_time = time.time()
            self.reader.query(
                tickers=[ticker],
                start_date=start_date,
                end_date=end_date
            )
            query_time = time.time() - start_time
            query_times.append(query_time)
        
        # Calculate statistics
        avg_time = sum(query_times) / len(query_times)
        max_time = max(query_times)
        min_time = min(query_times)
        
        print(f"Simulated {query_count} high-frequency queries:")
        print(f"Average time: {avg_time:.4f} seconds")
        print(f"Maximum time: {max_time:.4f} seconds")
        print(f"Minimum time: {min_time:.4f} seconds")
        
        # Verify performance is acceptable
        self.assertLess(avg_time, 0.1, "Average query time should be under 100ms")
        self.assertLess(max_time, 0.5, "Maximum query time should be under 500ms")
    
    def test_simulated_concurrent_requests(self):
        """Simulate concurrent requests to test thread safety."""
        # Create mock data for testing
        writer = ParquetWriterMock(self.test_dir)
        
        # Generate test data
        ticker_data = []
        for i in range(100):
            record = {
                "timestamp": (datetime.now() - timedelta(days=i % 30)).isoformat(),
                "ticker": "AAPL",
                "sentiment": np.random.uniform(-1, 1),
                "confidence": np.random.uniform(0.5, 1.0),
                "source": np.random.choice(["news", "reddit", "twitter"]),
                "model": "finbert",
                "article_id": f"AAPL-{i}",
                "article_title": f"Test article {i} for AAPL"
            }
            ticker_data.append(record)
        
        # Write ticker data
        writer.write_sentiment_data("AAPL", ticker_data)
        
        # Define a function to run in parallel
        async def concurrent_query():
            # Query data
            return self.reader.query(tickers=["AAPL"])
        
        # Run multiple concurrent requests
        async def run_concurrent_requests():
            tasks = []
            for _ in range(10):
                tasks.append(asyncio.create_task(concurrent_query()))
            
            results = await asyncio.gather(*tasks)
            return results
        
        # Run test
        results = asyncio.run(run_concurrent_requests())
        
        # Verify all requests returned data
        for df in results:
            self.assertFalse(df.empty)
            self.assertEqual(df.iloc[0]["ticker"], "AAPL")


if __name__ == "__main__":
    unittest.main()