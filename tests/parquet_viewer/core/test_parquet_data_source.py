"""
Unit tests for the ParquetDataSource class.
"""
import os
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np

from .parquet_data_source import ParquetDataSource


class TestParquetDataSource(unittest.TestCase):
    """Test cases for the ParquetDataSource class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock data path
        self.data_path = "/home/jonat/WSL_RT_Sentiment/data/output"
        
        # Patch os.path.exists to return True for the data path
        self.exists_patcher = patch('os.path.exists')
        self.mock_exists = self.exists_patcher.start()
        self.mock_exists.return_value = True
        
        # Patch glob.glob to return mock file paths
        self.glob_patcher = patch('glob.glob')
        self.mock_glob = self.glob_patcher.start()
        self.mock_glob.return_value = [
            f"{self.data_path}/aapl_sentiment.parquet",
            f"{self.data_path}/tsla_sentiment.parquet",
            f"{self.data_path}/multi_ticker_sentiment.parquet"
        ]
        
        # Patch pq.read_schema
        self.schema_patcher = patch('pyarrow.parquet.read_schema')
        self.mock_read_schema = self.schema_patcher.start()
        self.mock_read_schema.return_value = pa.schema([
            pa.field('timestamp', pa.string()),
            pa.field('ticker', pa.string()),
            pa.field('sentiment', pa.float64()),
            pa.field('confidence', pa.float64()),
            pa.field('source', pa.string()),
            pa.field('model', pa.string()),
            pa.field('article_id', pa.string()),
            pa.field('article_title', pa.string())
        ])
        
        # Initialize the ParquetDataSource
        self.data_source = ParquetDataSource(self.data_path, cache_enabled=False)
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.exists_patcher.stop()
        self.glob_patcher.stop()
        self.schema_patcher.stop()
    
    def test_init(self):
        """Test initialization of ParquetDataSource."""
        self.assertEqual(self.data_source.base_path, self.data_path)
        self.assertEqual(len(self.data_source.available_files), 3)
        self.assertEqual(len(self.data_source.schema_cache), 3)
    
    def test_get_available_tickers(self):
        """Test getting available tickers."""
        # Mock cache_manager.get to return None
        self.data_source.cache_manager.get = MagicMock(return_value=None)
        
        tickers = self.data_source.get_available_tickers()
        
        self.assertIsInstance(tickers, set)
        self.assertEqual(len(tickers), 3)
        self.assertIn('AAPL', tickers)
        self.assertIn('TSLA', tickers)
        self.assertIn('MULTI_TICKER', tickers)
    
    def test_get_schema(self):
        """Test getting schema for a file."""
        schema = self.data_source.get_schema(f"{self.data_path}/aapl_sentiment.parquet")
        
        self.assertIsNotNone(schema)
        self.assertEqual(schema.names, ['timestamp', 'ticker', 'sentiment', 'confidence', 
                                       'source', 'model', 'article_id', 'article_title'])
    
    def test_get_ticker_file(self):
        """Test getting file path for a ticker."""
        file_path = self.data_source.get_ticker_file('AAPL')
        
        self.assertEqual(file_path, f"{self.data_path}/aapl_sentiment.parquet")
        
        # Test case-insensitivity
        file_path = self.data_source.get_ticker_file('aapl')
        
        self.assertEqual(file_path, f"{self.data_path}/aapl_sentiment.parquet")
        
        # Test non-existent ticker
        file_path = self.data_source.get_ticker_file('NONEXISTENT')
        
        self.assertIsNone(file_path)
    
    @patch('pyarrow.dataset.dataset')
    def test_query_ticker(self, mock_dataset):
        """Test querying data for a ticker."""
        # Create a mock scanner and table
        mock_scanner = MagicMock()
        mock_table = MagicMock()
        
        # Create a DataFrame to return
        data = {
            'timestamp': ['2025-04-23T12:34:56'],
            'ticker': ['AAPL'],
            'sentiment': [0.8],
            'confidence': [0.9],
            'source': ['NewsScraper'],
            'model': ['finbert'],
            'article_id': ['test-id'],
            'article_title': ['Test Article']
        }
        df = pd.DataFrame(data)
        
        # Set up the mocks
        mock_scanner.filter.return_value = mock_scanner
        mock_scanner.to_table.return_value = mock_table
        mock_table.to_pandas.return_value = df
        mock_dataset.return_value.scanner.return_value = mock_scanner
        
        # Test query_ticker
        result = self.data_source.query_ticker(
            ticker='AAPL',
            start_date=datetime(2025, 4, 1),
            end_date=datetime(2025, 4, 23),
            sources=['NewsScraper'],
            sentiment_range=(0.5, 1.0),
            limit=10,
            sort_by='sentiment',
            ascending=False
        )
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result['ticker'][0], 'AAPL')
        self.assertEqual(result['sentiment'][0], 0.8)
    
    @patch('pyarrow.dataset.dataset')
    def test_query_multi_ticker(self, mock_dataset):
        """Test querying data for multiple tickers."""
        # Create a mock scanner and table
        mock_scanner = MagicMock()
        mock_table = MagicMock()
        
        # Create a DataFrame to return
        data = {
            'timestamp': ['2025-04-23T12:34:56', '2025-04-23T13:45:67'],
            'ticker': ['AAPL', 'TSLA'],
            'sentiment': [0.8, 0.6],
            'confidence': [0.9, 0.7],
            'source': ['NewsScraper', 'TwitterScraper'],
            'model': ['finbert', 'finbert'],
            'article_id': ['test-id-1', 'test-id-2'],
            'article_title': ['Test Article 1', 'Test Article 2']
        }
        df = pd.DataFrame(data)
        
        # Set up the mocks
        mock_scanner.filter.return_value = mock_scanner
        mock_scanner.to_table.return_value = mock_table
        mock_table.to_pandas.return_value = df.loc[df['ticker'] == 'AAPL']  # Return only AAPL data first time
        mock_dataset.return_value.scanner.return_value = mock_scanner
        
        # Mock query_ticker to return the appropriate data
        self.data_source.query_ticker = MagicMock(side_effect=[
            df.loc[df['ticker'] == 'AAPL'],
            df.loc[df['ticker'] == 'TSLA']
        ])
        
        # Test query_multi_ticker
        result = self.data_source.query_multi_ticker(
            tickers=['AAPL', 'TSLA'],
            start_date=datetime(2025, 4, 1),
            end_date=datetime(2025, 4, 23),
            sources=['NewsScraper', 'TwitterScraper'],
            sentiment_range=(0.5, 1.0),
            limit=10,
            sort_by='sentiment',
            ascending=False
        )
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result['ticker']), {'AAPL', 'TSLA'})
    
    @patch('pyarrow.dataset.dataset')
    def test_query_by_source(self, mock_dataset):
        """Test querying data by source."""
        # Create a mock scanner and table
        mock_scanner = MagicMock()
        mock_table = MagicMock()
        
        # Create a DataFrame to return
        data = {
            'timestamp': ['2025-04-23T12:34:56'],
            'ticker': ['AAPL'],
            'sentiment': [0.8],
            'confidence': [0.9],
            'source': ['NewsScraper'],
            'model': ['finbert'],
            'article_id': ['test-id'],
            'article_title': ['Test Article']
        }
        df = pd.DataFrame(data)
        
        # Set up the mocks
        mock_scanner.filter.return_value = mock_scanner
        mock_scanner.to_table.return_value = mock_table
        mock_table.to_pandas.return_value = df
        mock_dataset.return_value.scanner.return_value = mock_scanner
        
        # Test query_by_source
        result = self.data_source.query_by_source(
            source='NewsScraper',
            start_date=datetime(2025, 4, 1),
            end_date=datetime(2025, 4, 23),
            limit=10,
            sort_by='sentiment',
            ascending=False
        )
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result['source'][0], 'NewsScraper')
    
    @patch('pyarrow.dataset.dataset')
    def test_query_date_range(self, mock_dataset):
        """Test querying data for a date range."""
        # Create a mock scanner and table
        mock_scanner = MagicMock()
        mock_table = MagicMock()
        
        # Create a DataFrame to return
        data = {
            'timestamp': ['2025-04-23T12:34:56', '2025-04-22T13:45:67'],
            'ticker': ['AAPL', 'TSLA'],
            'sentiment': [0.8, 0.6],
            'confidence': [0.9, 0.7],
            'source': ['NewsScraper', 'TwitterScraper'],
            'model': ['finbert', 'finbert'],
            'article_id': ['test-id-1', 'test-id-2'],
            'article_title': ['Test Article 1', 'Test Article 2']
        }
        df = pd.DataFrame(data)
        
        # Set up the mocks
        mock_scanner.filter.return_value = mock_scanner
        mock_scanner.to_table.return_value = mock_table
        mock_table.to_pandas.return_value = df
        mock_dataset.return_value.scanner.return_value = mock_scanner
        
        # Test query_date_range
        result = self.data_source.query_date_range(
            start_date=datetime(2025, 4, 1),
            end_date=datetime(2025, 4, 23),
            tickers=['AAPL', 'TSLA'],
            sources=['NewsScraper', 'TwitterScraper'],
            sentiment_range=(0.5, 1.0),
            limit=10,
            sort_by='sentiment',
            ascending=False
        )
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result['ticker']), {'AAPL', 'TSLA'})
    
    def test_aggregate_sentiment_by_ticker(self):
        """Test aggregating sentiment by ticker."""
        # Create a mock DataFrame to return from query_date_range
        data = {
            'timestamp': ['2025-04-23T12:34:56', '2025-04-22T13:45:67', '2025-04-21T14:56:78'],
            'ticker': ['AAPL', 'AAPL', 'TSLA'],
            'sentiment': [0.8, 0.6, 0.7],
            'confidence': [0.9, 0.7, 0.8],
            'source': ['NewsScraper', 'TwitterScraper', 'NewsScraper'],
            'model': ['finbert', 'finbert', 'finbert'],
            'article_id': ['test-id-1', 'test-id-2', 'test-id-3'],
            'article_title': ['Test Article 1', 'Test Article 2', 'Test Article 3']
        }
        df = pd.DataFrame(data)
        
        # Mock query_date_range to return the DataFrame
        self.data_source.query_date_range = MagicMock(return_value=df)
        
        # Test aggregate_sentiment_by_ticker
        result = self.data_source.aggregate_sentiment_by_ticker(
            start_date=datetime(2025, 4, 1),
            end_date=datetime(2025, 4, 23),
            sources=['NewsScraper', 'TwitterScraper']
        )
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result['ticker']), {'AAPL', 'TSLA'})
        self.assertEqual(result.loc[result['ticker'] == 'AAPL', 'count'].iloc[0], 2)
        self.assertEqual(result.loc[result['ticker'] == 'TSLA', 'count'].iloc[0], 1)
    
    def test_aggregate_sentiment_by_source(self):
        """Test aggregating sentiment by source."""
        # Create a mock DataFrame to return from query_date_range
        data = {
            'timestamp': ['2025-04-23T12:34:56', '2025-04-22T13:45:67', '2025-04-21T14:56:78'],
            'ticker': ['AAPL', 'AAPL', 'TSLA'],
            'sentiment': [0.8, 0.6, 0.7],
            'confidence': [0.9, 0.7, 0.8],
            'source': ['NewsScraper', 'TwitterScraper', 'NewsScraper'],
            'model': ['finbert', 'finbert', 'finbert'],
            'article_id': ['test-id-1', 'test-id-2', 'test-id-3'],
            'article_title': ['Test Article 1', 'Test Article 2', 'Test Article 3']
        }
        df = pd.DataFrame(data)
        
        # Mock query_date_range to return the DataFrame
        self.data_source.query_date_range = MagicMock(return_value=df)
        
        # Test aggregate_sentiment_by_source
        result = self.data_source.aggregate_sentiment_by_source(
            start_date=datetime(2025, 4, 1),
            end_date=datetime(2025, 4, 23),
            tickers=['AAPL', 'TSLA']
        )
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result['source']), {'NewsScraper', 'TwitterScraper'})
        self.assertEqual(result.loc[result['source'] == 'NewsScraper', 'count'].iloc[0], 2)
        self.assertEqual(result.loc[result['source'] == 'TwitterScraper', 'count'].iloc[0], 1)
    
    def test_aggregate_sentiment_by_date(self):
        """Test aggregating sentiment by date."""
        # Create a mock DataFrame to return from query_date_range
        data = {
            'timestamp': pd.to_datetime(['2025-04-23T12:34:56', '2025-04-22T13:45:67', '2025-04-21T14:56:78']),
            'ticker': ['AAPL', 'AAPL', 'TSLA'],
            'sentiment': [0.8, 0.6, 0.7],
            'confidence': [0.9, 0.7, 0.8],
            'source': ['NewsScraper', 'TwitterScraper', 'NewsScraper'],
            'model': ['finbert', 'finbert', 'finbert'],
            'article_id': ['test-id-1', 'test-id-2', 'test-id-3'],
            'article_title': ['Test Article 1', 'Test Article 2', 'Test Article 3']
        }
        df = pd.DataFrame(data)
        
        # Mock query_date_range to return the DataFrame
        self.data_source.query_date_range = MagicMock(return_value=df)
        
        # Test aggregate_sentiment_by_date
        result = self.data_source.aggregate_sentiment_by_date(
            start_date=datetime(2025, 4, 1),
            end_date=datetime(2025, 4, 23),
            tickers=['AAPL', 'TSLA'],
            sources=['NewsScraper', 'TwitterScraper'],
            freq='D'
        )
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)  # One row per day
        self.assertTrue('date' in result.columns)
        self.assertTrue('count' in result.columns)
        self.assertTrue('avg_sentiment' in result.columns)
    
    def test_get_sentiment_histogram(self):
        """Test getting sentiment histogram."""
        # Create a mock DataFrame to return from query_ticker
        data = {
            'timestamp': ['2025-04-23T12:34:56', '2025-04-22T13:45:67', '2025-04-21T14:56:78'],
            'ticker': ['AAPL', 'AAPL', 'AAPL'],
            'sentiment': [0.8, 0.6, 0.7],
            'confidence': [0.9, 0.7, 0.8],
            'source': ['NewsScraper', 'TwitterScraper', 'NewsScraper'],
            'model': ['finbert', 'finbert', 'finbert'],
            'article_id': ['test-id-1', 'test-id-2', 'test-id-3'],
            'article_title': ['Test Article 1', 'Test Article 2', 'Test Article 3']
        }
        df = pd.DataFrame(data)
        
        # Mock query_ticker to return the DataFrame
        self.data_source.query_ticker = MagicMock(return_value=df)
        
        # Test get_sentiment_histogram
        result = self.data_source.get_sentiment_histogram(
            ticker='AAPL',
            start_date=datetime(2025, 4, 1),
            end_date=datetime(2025, 4, 23),
            sources=['NewsScraper', 'TwitterScraper'],
            bins=2
        )
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('bins' in result)
        self.assertTrue('counts' in result)
        self.assertTrue('total' in result)
        self.assertEqual(result['total'], 3)
        self.assertEqual(len(result['bins']), 2)
        self.assertEqual(len(result['counts']), 2)
    
    @patch('pyarrow.parquet.read_table')
    def test_execute_raw_query(self, mock_read_table):
        """Test executing a raw query."""
        # Create a mock table
        mock_table = MagicMock()
        
        # Create a DataFrame to return
        data = {
            'timestamp': ['2025-04-23T12:34:56'],
            'ticker': ['AAPL'],
            'sentiment': [0.8],
            'confidence': [0.9],
            'source': ['NewsScraper'],
            'model': ['finbert'],
            'article_id': ['test-id'],
            'article_title': ['Test Article']
        }
        df = pd.DataFrame(data)
        
        # Set up the mocks
        mock_table.to_pandas.return_value = df
        mock_read_table.return_value = mock_table
        
        # Define a query function
        def query_func(table):
            return table.to_pandas()
        
        # Test execute_raw_query
        result = self.data_source.execute_raw_query(
            query_func,
            file_paths=[f"{self.data_path}/aapl_sentiment.parquet"]
        )
        
        # Verify the result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result['ticker'][0], 'AAPL')
    
    @patch('os.path.getsize')
    @patch('os.path.getmtime')
    @patch('pyarrow.parquet.read_metadata')
    def test_get_file_stats(self, mock_read_metadata, mock_getmtime, mock_getsize):
        """Test getting file statistics."""
        # Set up the mocks
        mock_getsize.return_value = 1024
        mock_getmtime.return_value = datetime(2025, 4, 23).timestamp()
        
        mock_metadata = MagicMock()
        mock_metadata.num_rows = 100
        mock_metadata.num_row_groups = 1
        mock_read_metadata.return_value = mock_metadata
        
        # Test get_file_stats
        result = self.data_source.get_file_stats()
        
        # Verify the result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertTrue('ticker' in result[0])
        self.assertTrue('size_bytes' in result[0])
        self.assertTrue('num_rows' in result[0])
        
        # Verify ticker extraction
        self.assertEqual(result[0]['ticker'], 'AAPL')


if __name__ == '__main__':
    unittest.main()