"""
Unit tests for the QueryEngine class.
"""
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np

from .query_engine import QueryEngine
from .parquet_data_source import ParquetDataSource


class TestQueryEngine(unittest.TestCase):
    """Test cases for the QueryEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock ParquetDataSource
        self.mock_data_source = MagicMock(spec=ParquetDataSource)
        
        # Initialize the QueryEngine
        self.query_engine = QueryEngine(self.mock_data_source, cache_enabled=False)
    
    def test_parse_date(self):
        """Test parsing date strings."""
        # Test ISO format
        date = self.query_engine.parse_date("2025-04-23")
        self.assertEqual(date, datetime(2025, 4, 23, 0, 0, 0))
        
        # Test ISO format with time
        date = self.query_engine.parse_date("2025-04-23T12:34:56")
        self.assertEqual(date, datetime(2025, 4, 23, 12, 34, 56))
        
        # Test relative dates
        # Mock datetime.now to return a fixed date
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 4, 23, 10, 0, 0)
            
            # Test 'today'
            date = self.query_engine.parse_date("today")
            self.assertEqual(date, datetime(2025, 4, 23, 0, 0, 0))
            
            # Test 'yesterday'
            date = self.query_engine.parse_date("yesterday")
            self.assertEqual(date, datetime(2025, 4, 22, 0, 0, 0))
            
            # Test '1d'
            date = self.query_engine.parse_date("1d")
            self.assertEqual(date, datetime(2025, 4, 22, 0, 0, 0))
            
            # Test '7d'
            date = self.query_engine.parse_date("7d")
            self.assertEqual(date, datetime(2025, 4, 16, 0, 0, 0))
            
            # Test '1m'
            date = self.query_engine.parse_date("1m")
            self.assertEqual(date, datetime(2025, 3, 24, 0, 0, 0))
            
            # Test '1y'
            date = self.query_engine.parse_date("1y")
            self.assertEqual(date, datetime(2024, 4, 23, 0, 0, 0))
        
        # Test invalid date
        date = self.query_engine.parse_date("invalid_date")
        self.assertIsNone(date)
    
    def test_parse_filter_expression(self):
        """Test parsing filter expressions."""
        # Test simple expression
        filters = self.query_engine.parse_filter_expression("sentiment > 0.5")
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0], ("sentiment", ">", 0.5))
        
        # Test compound expression with AND
        filters = self.query_engine.parse_filter_expression("sentiment > 0.5 AND source = 'Twitter'")
        self.assertEqual(len(filters), 2)
        self.assertEqual(filters[0], ("sentiment", ">", 0.5))
        self.assertEqual(filters[1], ("source", "=", "Twitter"))
        
        # Test expression with string value
        filters = self.query_engine.parse_filter_expression("source = 'Twitter'")
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0], ("source", "=", "Twitter"))
        
        # Test expression with integer value
        filters = self.query_engine.parse_filter_expression("confidence = 1")
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0], ("confidence", "=", 1))
        
        # Test expression with special values
        filters = self.query_engine.parse_filter_expression("model = null")
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0], ("model", "=", None))
        
        filters = self.query_engine.parse_filter_expression("active = true")
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0], ("active", "=", True))
        
        # Test empty expression
        filters = self.query_engine.parse_filter_expression("")
        self.assertEqual(len(filters), 0)
    
    def test_execute_query_ticker(self):
        """Test executing a ticker query."""
        # Create a mock DataFrame to return
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
        
        # Mock the query_ticker method
        self.mock_data_source.query_ticker.return_value = df
        
        # Mock the format_dataframe method
        formatted_data = {
            'columns': df.columns.tolist(),
            'data': df.values.tolist(),
            'index': df.index.tolist(),
            'summary': {'row_count': 1}
        }
        self.query_engine.formatter.format_dataframe = MagicMock(return_value=formatted_data)
        
        # Test execute_query with ticker query
        result = self.query_engine.execute_query(
            query_type='ticker',
            parameters={
                'ticker': 'AAPL',
                'start_date': '2025-04-01',
                'end_date': '2025-04-23',
                'sources': ['NewsScraper'],
                'sentiment_range': (0.5, 1.0),
                'limit': 10,
                'sort_by': 'sentiment',
                'ascending': False
            }
        )
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('data' in result)
        self.assertTrue('metadata' in result)
        self.assertEqual(result['metadata']['query_type'], 'ticker')
        
        # Verify the data source was called correctly
        self.mock_data_source.query_ticker.assert_called_once()
        args, kwargs = self.mock_data_source.query_ticker.call_args
        self.assertEqual(kwargs['ticker'], 'AAPL')
        self.assertIsInstance(kwargs['start_date'], datetime)
        self.assertIsInstance(kwargs['end_date'], datetime)
        self.assertEqual(kwargs['sources'], ['NewsScraper'])
        self.assertEqual(kwargs['sentiment_range'], (0.5, 1.0))
        self.assertEqual(kwargs['limit'], 10)
        self.assertEqual(kwargs['sort_by'], 'sentiment')
        self.assertEqual(kwargs['ascending'], False)
    
    def test_execute_query_multi_ticker(self):
        """Test executing a multi-ticker query."""
        # Create a mock DataFrame to return
        data = {
            'timestamp': ['2025-04-23T12:34:56', '2025-04-22T13:45:67'],
            'ticker': ['AAPL', 'TSLA'],
            'sentiment': [0.8, 0.7],
            'confidence': [0.9, 0.8],
            'source': ['NewsScraper', 'TwitterScraper'],
            'model': ['finbert', 'finbert'],
            'article_id': ['test-id-1', 'test-id-2'],
            'article_title': ['Test Article 1', 'Test Article 2']
        }
        df = pd.DataFrame(data)
        
        # Mock the query_multi_ticker method
        self.mock_data_source.query_multi_ticker.return_value = df
        
        # Mock the format_dataframe method
        formatted_data = {
            'columns': df.columns.tolist(),
            'data': df.values.tolist(),
            'index': df.index.tolist(),
            'summary': {'row_count': 2}
        }
        self.query_engine.formatter.format_dataframe = MagicMock(return_value=formatted_data)
        
        # Test execute_query with multi_ticker query
        result = self.query_engine.execute_query(
            query_type='multi_ticker',
            parameters={
                'tickers': ['AAPL', 'TSLA'],
                'start_date': '2025-04-01',
                'end_date': '2025-04-23',
                'sources': ['NewsScraper', 'TwitterScraper'],
                'sentiment_range': (0.5, 1.0),
                'limit': 10,
                'sort_by': 'sentiment',
                'ascending': False
            }
        )
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('data' in result)
        self.assertTrue('metadata' in result)
        self.assertEqual(result['metadata']['query_type'], 'multi_ticker')
        
        # Verify the data source was called correctly
        self.mock_data_source.query_multi_ticker.assert_called_once()
        args, kwargs = self.mock_data_source.query_multi_ticker.call_args
        self.assertEqual(kwargs['tickers'], ['AAPL', 'TSLA'])
        self.assertIsInstance(kwargs['start_date'], datetime)
        self.assertIsInstance(kwargs['end_date'], datetime)
        self.assertEqual(kwargs['sources'], ['NewsScraper', 'TwitterScraper'])
        self.assertEqual(kwargs['sentiment_range'], (0.5, 1.0))
        self.assertEqual(kwargs['limit'], 10)
        self.assertEqual(kwargs['sort_by'], 'sentiment')
        self.assertEqual(kwargs['ascending'], False)
    
    def test_execute_query_date_range(self):
        """Test executing a date range query."""
        # Create a mock DataFrame to return
        data = {
            'timestamp': ['2025-04-23T12:34:56', '2025-04-22T13:45:67'],
            'ticker': ['AAPL', 'TSLA'],
            'sentiment': [0.8, 0.7],
            'confidence': [0.9, 0.8],
            'source': ['NewsScraper', 'TwitterScraper'],
            'model': ['finbert', 'finbert'],
            'article_id': ['test-id-1', 'test-id-2'],
            'article_title': ['Test Article 1', 'Test Article 2']
        }
        df = pd.DataFrame(data)
        
        # Mock the query_date_range method
        self.mock_data_source.query_date_range.return_value = df
        
        # Mock the format_dataframe method
        formatted_data = {
            'columns': df.columns.tolist(),
            'data': df.values.tolist(),
            'index': df.index.tolist(),
            'summary': {'row_count': 2}
        }
        self.query_engine.formatter.format_dataframe = MagicMock(return_value=formatted_data)
        
        # Test execute_query with date_range query
        result = self.query_engine.execute_query(
            query_type='date_range',
            parameters={
                'start_date': '2025-04-01',
                'end_date': '2025-04-23',
                'tickers': ['AAPL', 'TSLA'],
                'sources': ['NewsScraper', 'TwitterScraper'],
                'sentiment_range': (0.5, 1.0),
                'limit': 10,
                'sort_by': 'sentiment',
                'ascending': False
            }
        )
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('data' in result)
        self.assertTrue('metadata' in result)
        self.assertEqual(result['metadata']['query_type'], 'date_range')
        
        # Verify the data source was called correctly
        self.mock_data_source.query_date_range.assert_called_once()
        args, kwargs = self.mock_data_source.query_date_range.call_args
        self.assertIsInstance(kwargs['start_date'], datetime)
        self.assertIsInstance(kwargs['end_date'], datetime)
        self.assertEqual(kwargs['tickers'], ['AAPL', 'TSLA'])
        self.assertEqual(kwargs['sources'], ['NewsScraper', 'TwitterScraper'])
        self.assertEqual(kwargs['sentiment_range'], (0.5, 1.0))
        self.assertEqual(kwargs['limit'], 10)
        self.assertEqual(kwargs['sort_by'], 'sentiment')
        self.assertEqual(kwargs['ascending'], False)
    
    def test_execute_query_aggregate_by_ticker(self):
        """Test executing an aggregate by ticker query."""
        # Create a mock DataFrame to return
        data = {
            'ticker': ['AAPL', 'TSLA'],
            'count': [10, 5],
            'avg_sentiment': [0.7, 0.6],
            'min_sentiment': [0.5, 0.4],
            'max_sentiment': [0.9, 0.8],
            'std_sentiment': [0.1, 0.2]
        }
        df = pd.DataFrame(data)
        
        # Mock the aggregate_sentiment_by_ticker method
        self.mock_data_source.aggregate_sentiment_by_ticker.return_value = df
        
        # Mock the format_dataframe method
        formatted_data = {
            'columns': df.columns.tolist(),
            'data': df.values.tolist(),
            'index': df.index.tolist(),
            'summary': {'row_count': 2}
        }
        self.query_engine.formatter.format_dataframe = MagicMock(return_value=formatted_data)
        
        # Test execute_query with aggregate_by_ticker query
        result = self.query_engine.execute_query(
            query_type='aggregate_by_ticker',
            parameters={
                'start_date': '2025-04-01',
                'end_date': '2025-04-23',
                'tickers': ['AAPL', 'TSLA'],
                'sources': ['NewsScraper', 'TwitterScraper']
            }
        )
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('data' in result)
        self.assertTrue('metadata' in result)
        self.assertEqual(result['metadata']['query_type'], 'aggregate_by_ticker')
        
        # Verify the data source was called correctly
        self.mock_data_source.aggregate_sentiment_by_ticker.assert_called_once()
        args, kwargs = self.mock_data_source.aggregate_sentiment_by_ticker.call_args
        self.assertIsInstance(kwargs['start_date'], datetime)
        self.assertIsInstance(kwargs['end_date'], datetime)
        self.assertEqual(kwargs['tickers'], ['AAPL', 'TSLA'])
        self.assertEqual(kwargs['sources'], ['NewsScraper', 'TwitterScraper'])
    
    def test_execute_query_invalid_type(self):
        """Test executing an invalid query type."""
        # Test with an invalid query type
        with self.assertRaises(ValueError):
            self.query_engine.execute_query(
                query_type='invalid_type',
                parameters={}
            )
    
    def test_export_results(self):
        """Test exporting query results."""
        # Create a mock query result
        result = {
            'data': {
                'columns': ['ticker', 'sentiment', 'confidence'],
                'data': [['AAPL', 0.8, 0.9], ['TSLA', 0.7, 0.8]],
                'index': [0, 1],
                'summary': {'row_count': 2}
            },
            'metadata': {
                'query_type': 'ticker',
                'parameters': {'ticker': 'AAPL'}
            }
        }
        
        # Mock the export method
        self.query_engine.export_manager.export = MagicMock(return_value="exported_data")
        
        # Test export_results
        exported = self.query_engine.export_results(result, 'csv', 'test.csv')
        
        # Verify the result
        self.assertEqual(exported, "exported_data")
        
        # Verify the export_manager was called correctly
        self.query_engine.export_manager.export.assert_called_once()
        args, kwargs = self.query_engine.export_manager.export.call_args
        self.assertIsInstance(args[0], pd.DataFrame)
        self.assertEqual(args[1], 'csv')
        self.assertEqual(args[2], 'test.csv')
    
    def test_execute_sql_query(self):
        """Test executing an SQL query."""
        # Create a mock DataFrame to return
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
        
        # Mock the query_ticker method
        self.mock_data_source.query_ticker.return_value = df
        
        # Mock the format_dataframe method
        formatted_data = {
            'columns': df.columns.tolist(),
            'data': df.values.tolist(),
            'index': df.index.tolist(),
            'summary': {'row_count': 1}
        }
        self.query_engine.formatter.format_dataframe = MagicMock(return_value=formatted_data)
        
        # Test execute_sql_query
        result = self.query_engine.execute_sql_query(
            "SELECT * FROM aapl_sentiment WHERE sentiment > 0.5 ORDER BY sentiment DESC LIMIT 10"
        )
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('data' in result)
        self.assertTrue('metadata' in result)
        self.assertEqual(result['metadata']['query_type'], 'sql')
        
        # Verify the data source was called correctly
        self.mock_data_source.query_ticker.assert_called_once()
        args, kwargs = self.mock_data_source.query_ticker.call_args
        self.assertEqual(kwargs['ticker'], 'AAPL')
        self.assertEqual(kwargs['sort_by'], 'sentiment')
        self.assertEqual(kwargs['ascending'], False)
        self.assertEqual(kwargs['limit'], 10)
    
    def test_build_query(self):
        """Test building and executing a query from a specification."""
        # Create a mock query result
        mock_result = {
            'data': {
                'columns': ['ticker', 'sentiment', 'confidence'],
                'data': [['AAPL', 0.8, 0.9]],
                'index': [0],
                'summary': {'row_count': 1}
            },
            'metadata': {
                'query_type': 'ticker',
                'parameters': {'ticker': 'AAPL'}
            }
        }
        
        # Mock the execute_query method
        self.query_engine.execute_query = MagicMock(return_value=mock_result)
        
        # Test build_query
        result = self.query_engine.build_query({
            'query_type': 'ticker',
            'ticker': 'AAPL',
            'start_date': '2025-04-01',
            'end_date': '2025-04-23',
            'sources': ['NewsScraper'],
            'limit': 10,
            'sort': {
                'column': 'sentiment',
                'direction': 'desc'
            }
        })
        
        # Verify the result
        self.assertEqual(result, mock_result)
        
        # Verify execute_query was called correctly
        self.query_engine.execute_query.assert_called_once()
        args, kwargs = self.query_engine.execute_query.call_args
        self.assertEqual(args[0], 'ticker')
        self.assertEqual(kwargs['parameters']['ticker'], 'AAPL')
        self.assertIsInstance(kwargs['parameters']['start_date'], datetime)
        self.assertIsInstance(kwargs['parameters']['end_date'], datetime)
        self.assertEqual(kwargs['parameters']['sources'], ['NewsScraper'])
        self.assertEqual(kwargs['parameters']['limit'], 10)
        self.assertEqual(kwargs['parameters']['sort_by'], 'sentiment')
        self.assertEqual(kwargs['parameters']['ascending'], False)


if __name__ == '__main__':
    unittest.main()