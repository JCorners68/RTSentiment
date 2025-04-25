"""
Unit tests for the utility classes.
"""
import os
import io
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np
import pyarrow as pa

from .utils import DataFormatter, ExportManager, QueryPatterns


class TestDataFormatter(unittest.TestCase):
    """Test cases for the DataFormatter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.formatter = DataFormatter()
    
    def test_format_dataframe(self):
        """Test formatting a pandas DataFrame."""
        # Create a test DataFrame
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
        
        # Format the DataFrame
        result = self.formatter.format_dataframe(df)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('columns' in result)
        self.assertTrue('data' in result)
        self.assertTrue('index' in result)
        self.assertTrue('summary' in result)
        
        # Check columns
        self.assertEqual(result['columns'], list(data.keys()))
        
        # Check data
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(len(result['data'][0]), len(data))
        
        # Check summary
        self.assertEqual(result['summary']['row_count'], 1)
        self.assertTrue('numeric_columns' in result['summary'])
        self.assertTrue('column_types' in result['summary'])
        
        # Check sentiment column stats
        self.assertTrue('sentiment' in result['summary']['numeric_columns'])
        self.assertEqual(result['summary']['numeric_columns']['sentiment']['mean'], 0.8)
        self.assertEqual(result['summary']['numeric_columns']['sentiment']['min'], 0.8)
        self.assertEqual(result['summary']['numeric_columns']['sentiment']['max'], 0.8)
        
        # Check column types
        self.assertEqual(result['summary']['column_types']['sentiment'], 'numeric')
        self.assertEqual(result['summary']['column_types']['ticker'], 'string')
    
    def test_format_empty_dataframe(self):
        """Test formatting an empty DataFrame."""
        # Create an empty DataFrame
        df = pd.DataFrame()
        
        # Format the DataFrame
        result = self.formatter.format_dataframe(df)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertEqual(result['columns'], [])
        self.assertEqual(result['data'], [])
        self.assertEqual(result['index'], [])
        self.assertEqual(result['summary']['row_count'], 0)
    
    def test_format_dataframe_with_special_types(self):
        """Test formatting a DataFrame with special types."""
        # Create a DataFrame with special types
        data = {
            'timestamp': [datetime(2025, 4, 23, 12, 34, 56)],
            'ticker': ['AAPL'],
            'sentiment': [np.float64(0.8)],
            'confidence': [np.float32(0.9)],
            'is_positive': [np.bool_(True)],
            'tags': [np.array(['tech', 'finance'])],
        }
        df = pd.DataFrame(data)
        
        # Format the DataFrame
        result = self.formatter.format_dataframe(df)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        
        # Check data types are converted correctly
        self.assertIsInstance(result['data'][0][0], str)  # timestamp to ISO string
        self.assertIsInstance(result['data'][0][2], float)  # np.float64 to float
        self.assertIsInstance(result['data'][0][3], float)  # np.float32 to float
        self.assertIsInstance(result['data'][0][4], bool)  # np.bool_ to bool
        self.assertIsInstance(result['data'][0][5], list)  # np.array to list
    
    def test_convert_numpy_types(self):
        """Test converting numpy types to Python types."""
        # Test integer conversion
        result = self.formatter._convert_numpy_types(np.int64(10))
        self.assertIsInstance(result, int)
        self.assertEqual(result, 10)
        
        # Test float conversion
        result = self.formatter._convert_numpy_types(np.float64(10.5))
        self.assertIsInstance(result, float)
        self.assertEqual(result, 10.5)
        
        # Test boolean conversion
        result = self.formatter._convert_numpy_types(np.bool_(True))
        self.assertIsInstance(result, bool)
        self.assertEqual(result, True)
        
        # Test array conversion
        result = self.formatter._convert_numpy_types(np.array([1, 2, 3]))
        self.assertIsInstance(result, list)
        self.assertEqual(result, [1, 2, 3])
        
        # Test regular Python type (pass-through)
        result = self.formatter._convert_numpy_types("string")
        self.assertIsInstance(result, str)
        self.assertEqual(result, "string")


class TestExportManager(unittest.TestCase):
    """Test cases for the ExportManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.export_manager = ExportManager()
        
        # Create a test DataFrame
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
        self.df = pd.DataFrame(data)
    
    def test_export_csv(self):
        """Test exporting to CSV format."""
        # Export to CSV
        result = self.export_manager._export_csv(self.df)
        
        # Verify the result
        self.assertIsInstance(result, str)
        self.assertTrue('timestamp,ticker,sentiment,confidence,source,model,article_id,article_title' in result)
        self.assertTrue('2025-04-23T12:34:56,AAPL,0.8,0.9,NewsScraper,finbert,test-id,Test Article' in result)
    
    def test_export_json(self):
        """Test exporting to JSON format."""
        # Export to JSON
        result = self.export_manager._export_json(self.df)
        
        # Verify the result
        self.assertIsInstance(result, str)
        self.assertTrue('"timestamp":"2025-04-23T12:34:56"' in result)
        self.assertTrue('"ticker":"AAPL"' in result)
        self.assertTrue('"sentiment":0.8' in result)
    
    @patch('pandas.ExcelWriter')
    def test_export_excel(self, mock_excel_writer):
        """Test exporting to Excel format."""
        # Mock the ExcelWriter
        mock_writer = MagicMock()
        mock_excel_writer.return_value.__enter__.return_value = mock_writer
        
        # Export to Excel
        with patch('io.BytesIO') as mock_bytesio:
            # Mock BytesIO.getvalue
            mock_bytesio.return_value.getvalue.return_value = b'excel_data'
            
            result = self.export_manager._export_excel(self.df)
            
            # Verify the result
            self.assertEqual(result, b'excel_data')
            
            # Verify the DataFrame was written to Excel
            self.df.to_excel.assert_called_once_with(mock_writer, sheet_name='Data', index=False)
    
    @patch('pyarrow.Table.from_pandas')
    @patch('pyarrow.parquet.write_table')
    def test_export_parquet(self, mock_write_table, mock_from_pandas):
        """Test exporting to Parquet format."""
        # Mock the PyArrow Table
        mock_table = MagicMock()
        mock_from_pandas.return_value = mock_table
        
        # Export to Parquet
        with patch('io.BytesIO') as mock_bytesio:
            # Mock BytesIO.getvalue
            mock_bytesio.return_value.getvalue.return_value = b'parquet_data'
            
            result = self.export_manager._export_parquet(self.df)
            
            # Verify the result
            self.assertEqual(result, b'parquet_data')
            
            # Verify the table was written to Parquet
            mock_write_table.assert_called_once()
    
    def test_export_html(self):
        """Test exporting to HTML format."""
        # Export to HTML
        result = self.export_manager._export_html(self.df)
        
        # Verify the result
        self.assertIsInstance(result, str)
        self.assertTrue('<!DOCTYPE html>' in result)
        self.assertTrue('<title>Parquet Query Results</title>' in result)
        self.assertTrue('AAPL' in result)
        self.assertTrue('0.8' in result)
    
    def test_export_empty_dataframe(self):
        """Test exporting an empty DataFrame."""
        # Create an empty DataFrame
        empty_df = pd.DataFrame()
        
        # Test export to various formats
        csv_result = self.export_manager.export(empty_df, 'csv')
        self.assertEqual(csv_result, "")
        
        json_result = self.export_manager.export(empty_df, 'json')
        self.assertEqual(json_result, "")
        
        with patch('io.BytesIO') as mock_bytesio:
            mock_bytesio.return_value.getvalue.return_value = b''
            excel_result = self.export_manager.export(empty_df, 'excel')
            self.assertEqual(excel_result, b'')
    
    def test_export_invalid_format(self):
        """Test exporting with an invalid format."""
        # Test with an invalid format
        with self.assertRaises(ValueError):
            self.export_manager.export(self.df, 'invalid_format')


class TestQueryPatterns(unittest.TestCase):
    """Test cases for the QueryPatterns class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock query engine
        self.mock_query_engine = MagicMock()
        
        # Mock the parse_date method
        self.mock_query_engine.parse_date.side_effect = lambda date_str: datetime.fromisoformat(date_str)
    
    def test_ticker_comparison(self):
        """Test the ticker_comparison pattern."""
        # Create mock data
        data = {
            'timestamp': pd.date_range(start='2025-04-01', end='2025-04-23'),
            'ticker': ['AAPL'] * 23,
            'sentiment': [0.7] * 23,
            'confidence': [0.8] * 23
        }
        df = pd.DataFrame(data)
        
        # Mock query_engine.execute_query
        mock_result = {
            'data': {
                'columns': df.columns.tolist(),
                'data': df.values.tolist()
            }
        }
        self.mock_query_engine.execute_query.return_value = mock_result
        
        # Test ticker_comparison
        result = QueryPatterns.ticker_comparison(
            self.mock_query_engine,
            tickers=['AAPL', 'TSLA'],
            start_date='2025-04-01',
            end_date='2025-04-23',
            interval='D'
        )
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('tickers' in result)
        self.assertTrue('series' in result)
        self.assertEqual(result['tickers'], ['AAPL', 'TSLA'])
        self.assertEqual(result['start_date'], '2025-04-01T00:00:00')
        self.assertEqual(result['end_date'], '2025-04-23T00:00:00')
        
        # Verify execute_query was called correctly
        self.mock_query_engine.execute_query.assert_called()
    
    def test_source_comparison(self):
        """Test the source_comparison pattern."""
        # Create mock data
        data = {
            'timestamp': ['2025-04-01', '2025-04-01', '2025-04-02', '2025-04-02'],
            'ticker': ['AAPL', 'AAPL', 'AAPL', 'AAPL'],
            'sentiment': [0.7, 0.6, 0.8, 0.5],
            'confidence': [0.8, 0.7, 0.9, 0.6],
            'source': ['Twitter', 'Reddit', 'Twitter', 'Reddit']
        }
        df = pd.DataFrame(data)
        
        # Mock query_engine.execute_query
        mock_result = {
            'data': {
                'columns': df.columns.tolist(),
                'data': df.values.tolist()
            }
        }
        self.mock_query_engine.execute_query.return_value = mock_result
        
        # Test source_comparison
        result = QueryPatterns.source_comparison(
            self.mock_query_engine,
            sources=['Twitter', 'Reddit'],
            ticker='AAPL',
            start_date='2025-04-01',
            end_date='2025-04-23'
        )
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('sources' in result)
        self.assertTrue('comparison' in result)
        self.assertEqual(result['sources'], ['Twitter', 'Reddit'])
        self.assertEqual(result['ticker'], 'AAPL')
        
        # Verify execute_query was called correctly
        self.mock_query_engine.execute_query.assert_called_once()
    
    def test_sentiment_distribution(self):
        """Test the sentiment_distribution pattern."""
        # Create mock histogram data
        mock_hist_result = {
            'bins': [0.0, 0.5],
            'counts': [10, 20],
            'total': 30
        }
        
        # Mock query_engine.execute_query
        self.mock_query_engine.execute_query.return_value = mock_hist_result
        
        # Test sentiment_distribution
        result = QueryPatterns.sentiment_distribution(
            self.mock_query_engine,
            ticker='AAPL',
            start_date='2025-04-01',
            end_date='2025-04-23',
            sources=['Twitter', 'Reddit'],
            bins=20
        )
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertTrue('ticker' in result)
        self.assertTrue('bins' in result)
        self.assertTrue('counts' in result)
        self.assertTrue('total' in result)
        self.assertEqual(result['ticker'], 'AAPL')
        
        # Verify execute_query was called correctly
        self.mock_query_engine.execute_query.assert_called_once()


if __name__ == '__main__':
    unittest.main()