"""
Utility classes for the Parquet Query Viewer.

This module provides utility classes for data formatting, export, and
common query patterns.
"""
import os
import io
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple, Set, Iterator

import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


class DataFormatter:
    """
    A utility class for formatting query results.
    
    This class provides methods for converting pandas DataFrames and other
    data structures into standardized formats for API responses.
    """
    
    def __init__(self):
        """Initialize the DataFormatter."""
        pass
    
    def format_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Format a pandas DataFrame as a standardized dictionary.
        
        Args:
            df (pd.DataFrame): The DataFrame to format
            
        Returns:
            Dict[str, Any]: Formatted data dictionary
            
        Note:
            The result format is:
            {
                "columns": ["col1", "col2", ...],
                "data": [[row1col1, row1col2, ...], [row2col1, row2col2, ...], ...],
                "index": [idx1, idx2, ...],
                "summary": {
                    "row_count": 123,
                    "numeric_columns": {"col1": {"mean": 1.23, "min": 0.1, "max": 5.0}},
                    "column_types": {"col1": "float", "col2": "string"}
                }
            }
        """
        if df is None or df.empty:
            return {
                "columns": [],
                "data": [],
                "index": [],
                "summary": {
                    "row_count": 0,
                    "numeric_columns": {},
                    "column_types": {}
                }
            }
        
        # Convert to json-serializable format
        # This handles NaN, datetime, etc.
        columns = df.columns.tolist()
        data = []
        
        for _, row in df.iterrows():
            row_data = []
            for col in columns:
                val = row[col]
                
                # Handle special types
                if pd.isna(val):
                    val = None
                elif isinstance(val, (datetime, pd.Timestamp)):
                    val = val.isoformat()
                elif isinstance(val, np.integer):
                    val = int(val)
                elif isinstance(val, np.floating):
                    val = float(val)
                elif isinstance(val, np.bool_):
                    val = bool(val)
                elif isinstance(val, (np.ndarray, list, tuple)):
                    val = [self._convert_numpy_types(x) for x in val]
                
                row_data.append(val)
            
            data.append(row_data)
        
        # Build summary
        summary = {
            "row_count": len(df),
            "numeric_columns": {},
            "column_types": {}
        }
        
        # Include column types
        for col in columns:
            dtype = df[col].dtype
            if pd.api.types.is_numeric_dtype(dtype):
                summary["column_types"][col] = "numeric"
                
                # Include summary stats for numeric columns
                try:
                    summary["numeric_columns"][col] = {
                        "mean": float(df[col].mean()) if not df[col].isna().all() else None,
                        "min": float(df[col].min()) if not df[col].isna().all() else None,
                        "max": float(df[col].max()) if not df[col].isna().all() else None,
                        "std": float(df[col].std()) if not df[col].isna().all() and len(df) > 1 else None,
                        "null_count": int(df[col].isna().sum())
                    }
                except Exception as e:
                    logger.warning(f"Error calculating stats for column {col}: {e}")
            
            elif pd.api.types.is_datetime64_dtype(dtype):
                summary["column_types"][col] = "datetime"
            elif pd.api.types.is_bool_dtype(dtype):
                summary["column_types"][col] = "boolean"
            else:
                summary["column_types"][col] = "string"
        
        return {
            "columns": columns,
            "data": data,
            "index": df.index.tolist(),
            "summary": summary
        }
    
    def _convert_numpy_types(self, obj: Any) -> Any:
        """
        Convert numpy types to Python native types.
        
        Args:
            obj (Any): The object to convert
            
        Returns:
            Any: The converted object
        """
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj


class ExportManager:
    """
    A utility class for exporting query results to various formats.
    
    This class provides methods for exporting pandas DataFrames to
    CSV, JSON, Excel, and other formats.
    """
    
    def __init__(self):
        """Initialize the ExportManager."""
        pass
    
    def export(
        self,
        df: pd.DataFrame,
        format: str,
        file_path: Optional[str] = None
    ) -> Union[str, bytes]:
        """
        Export a DataFrame to the specified format.
        
        Args:
            df (pd.DataFrame): The DataFrame to export
            format (str): Export format (csv, json, excel, parquet, html)
            file_path (Optional[str]): Path to save the exported file
            
        Returns:
            Union[str, bytes]: The exported data as string or bytes
            
        Raises:
            ValueError: If the format is unsupported
        """
        if df is None or df.empty:
            if format.lower() in ['csv', 'json', 'html']:
                result = ""
            else:
                result = b""
                
            if file_path:
                with open(file_path, 'wb' if isinstance(result, bytes) else 'w') as f:
                    f.write(result)
            
            return result
        
        # Export based on format
        format = format.lower()
        
        if format == 'csv':
            result = self._export_csv(df, file_path)
        elif format == 'json':
            result = self._export_json(df, file_path)
        elif format == 'excel':
            result = self._export_excel(df, file_path)
        elif format == 'parquet':
            result = self._export_parquet(df, file_path)
        elif format == 'html':
            result = self._export_html(df, file_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        return result
    
    def _export_csv(
        self,
        df: pd.DataFrame,
        file_path: Optional[str] = None
    ) -> str:
        """
        Export a DataFrame to CSV format.
        
        Args:
            df (pd.DataFrame): The DataFrame to export
            file_path (Optional[str]): Path to save the CSV file
            
        Returns:
            str: The CSV data as a string
        """
        csv_data = df.to_csv(index=False)
        
        if file_path:
            try:
                with open(file_path, 'w', newline='') as f:
                    f.write(csv_data)
                logger.info(f"Exported CSV to {file_path}")
            except Exception as e:
                logger.error(f"Error saving CSV to {file_path}: {e}")
        
        return csv_data
    
    def _export_json(
        self,
        df: pd.DataFrame,
        file_path: Optional[str] = None
    ) -> str:
        """
        Export a DataFrame to JSON format.
        
        Args:
            df (pd.DataFrame): The DataFrame to export
            file_path (Optional[str]): Path to save the JSON file
            
        Returns:
            str: The JSON data as a string
        """
        # Handle NaN values and other non-serializable types
        json_data = df.to_json(orient='records', date_format='iso')
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(json_data)
                logger.info(f"Exported JSON to {file_path}")
            except Exception as e:
                logger.error(f"Error saving JSON to {file_path}: {e}")
        
        return json_data
    
    def _export_excel(
        self,
        df: pd.DataFrame,
        file_path: Optional[str] = None
    ) -> bytes:
        """
        Export a DataFrame to Excel format.
        
        Args:
            df (pd.DataFrame): The DataFrame to export
            file_path (Optional[str]): Path to save the Excel file
            
        Returns:
            bytes: The Excel data as bytes
        """
        output = io.BytesIO()
        
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Data']
                for i, col in enumerate(df.columns):
                    # Find the maximum length in the column
                    max_len = max(
                        df[col].astype(str).map(len).max(),
                        len(str(col))
                    ) + 2  # Add a little extra space
                    
                    worksheet.set_column(i, i, max_len)
        except ImportError:
            # Fall back to openpyxl if xlsxwriter is not available
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
        
        excel_data = output.getvalue()
        
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(excel_data)
                logger.info(f"Exported Excel to {file_path}")
            except Exception as e:
                logger.error(f"Error saving Excel to {file_path}: {e}")
        
        return excel_data
    
    def _export_parquet(
        self,
        df: pd.DataFrame,
        file_path: Optional[str] = None
    ) -> bytes:
        """
        Export a DataFrame to Parquet format.
        
        Args:
            df (pd.DataFrame): The DataFrame to export
            file_path (Optional[str]): Path to save the Parquet file
            
        Returns:
            bytes: The Parquet data as bytes
        """
        output = io.BytesIO()
        
        # Convert to PyArrow Table and write to Parquet
        table = pa.Table.from_pandas(df)
        pq.write_table(table, output)
        
        parquet_data = output.getvalue()
        
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(parquet_data)
                logger.info(f"Exported Parquet to {file_path}")
            except Exception as e:
                logger.error(f"Error saving Parquet to {file_path}: {e}")
        
        return parquet_data
    
    def _export_html(
        self,
        df: pd.DataFrame,
        file_path: Optional[str] = None
    ) -> str:
        """
        Export a DataFrame to HTML format.
        
        Args:
            df (pd.DataFrame): The DataFrame to export
            file_path (Optional[str]): Path to save the HTML file
            
        Returns:
            str: The HTML data as a string
        """
        # Add styling to the HTML
        styled_df = df.style.set_table_styles([
            {'selector': 'table', 'props': [('border-collapse', 'collapse'),
                                           ('width', '100%')]},
            {'selector': 'th', 'props': [('background-color', '#f2f2f2'),
                                         ('color', 'black'),
                                         ('font-weight', 'bold'),
                                         ('text-align', 'left'),
                                         ('padding', '8px'),
                                         ('border', '1px solid #ddd')]},
            {'selector': 'td', 'props': [('padding', '8px'),
                                         ('border', '1px solid #ddd')]}
        ])
        
        # Add hover effect
        styled_df = styled_df.set_table_styles([
            {'selector': 'tr:hover', 'props': [('background-color', '#e6f7ff')]}
        ], overwrite=False)
        
        # Generate HTML
        html = styled_df.to_html(index=False)
        
        # Add some basic CSS for better display
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Parquet Query Results</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 20px;
                }}
                h1 {{
                    color: #333;
                }}
                .dataframe {{
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>Parquet Query Results</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            {html}
        </body>
        </html>
        """
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(html)
                logger.info(f"Exported HTML to {file_path}")
            except Exception as e:
                logger.error(f"Error saving HTML to {file_path}: {e}")
        
        return html


class QueryPatterns:
    """
    A collection of common query patterns for the Parquet Query Viewer.
    
    This class provides methods for common query patterns that can be
    used to simplify common tasks.
    """
    
    @staticmethod
    def ticker_comparison(
        query_engine,
        tickers: List[str],
        start_date: str,
        end_date: str,
        interval: str = 'D'
    ) -> Dict[str, Any]:
        """
        Compare sentiment for multiple tickers over time.
        
        Args:
            query_engine: The QueryEngine instance
            tickers (List[str]): List of tickers to compare
            start_date (str): Start date string
            end_date (str): End date string
            interval (str): Time interval for aggregation (D=daily, W=weekly, M=monthly)
            
        Returns:
            Dict[str, Any]: Comparison results
            
        Example:
            result = QueryPatterns.ticker_comparison(
                query_engine,
                tickers=["AAPL", "MSFT", "GOOGL"],
                start_date="2025-01-01",
                end_date="2025-04-23",
                interval="W"
            )
        """
        # Parse dates
        start = query_engine.parse_date(start_date)
        end = query_engine.parse_date(end_date)
        
        if not start or not end:
            raise ValueError("Invalid date format")
        
        # Initialize results dictionary
        results = {
            "tickers": tickers,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "interval": interval,
            "series": []
        }
        
        # Process each ticker
        for ticker in tickers:
            # Query data for ticker
            query_result = query_engine.execute_query(
                "ticker",
                {
                    "ticker": ticker,
                    "start_date": start,
                    "end_date": end
                }
            )
            
            if "data" not in query_result or not query_result["data"]:
                logger.warning(f"No data found for ticker {ticker}")
                continue
            
            # Convert data to DataFrame
            df = pd.DataFrame(
                query_result["data"]["data"],
                columns=query_result["data"]["columns"]
            )
            
            # Convert timestamp to datetime
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                
                # Set timestamp as index for resampling
                df = df.set_index("timestamp")
                
                # Resample by the specified interval and calculate average sentiment
                resampled = df.resample(interval).agg({
                    "sentiment": "mean",
                    "confidence": "mean"
                }).reset_index()
                
                # Convert back to list format
                series_data = []
                for _, row in resampled.iterrows():
                    series_data.append({
                        "date": row["timestamp"].isoformat(),
                        "sentiment": float(row["sentiment"]) if not pd.isna(row["sentiment"]) else None,
                        "confidence": float(row["confidence"]) if not pd.isna(row["confidence"]) else None
                    })
                
                # Add to results
                results["series"].append({
                    "ticker": ticker,
                    "data": series_data,
                    "avg_sentiment": float(df["sentiment"].mean()) if not df["sentiment"].isna().all() else None,
                    "data_points": len(df)
                })
        
        return results
    
    @staticmethod
    def source_comparison(
        query_engine,
        sources: List[str],
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare sentiment from different sources.
        
        Args:
            query_engine: The QueryEngine instance
            sources (List[str]): List of sources to compare
            ticker (Optional[str]): Ticker to filter by
            start_date (Optional[str]): Start date string
            end_date (Optional[str]): End date string
            
        Returns:
            Dict[str, Any]: Comparison results
            
        Example:
            result = QueryPatterns.source_comparison(
                query_engine,
                sources=["Twitter", "Reddit", "NewsScraper"],
                ticker="AAPL",
                start_date="2025-01-01",
                end_date="2025-04-23"
            )
        """
        # Parse dates
        start = query_engine.parse_date(start_date) if start_date else None
        end = query_engine.parse_date(end_date) if end_date else None
        
        # Initialize results dictionary
        results = {
            "sources": sources,
            "ticker": ticker,
            "start_date": start.isoformat() if start else None,
            "end_date": end.isoformat() if end else None,
            "comparison": []
        }
        
        # Query parameters
        params = {
            "start_date": start,
            "end_date": end,
            "sources": sources
        }
        
        if ticker:
            # If ticker is specified, query for that ticker
            params["ticker"] = ticker
            query_result = query_engine.execute_query("ticker", params)
        else:
            # Otherwise, query for all data in the date range
            query_result = query_engine.execute_query("date_range", params)
        
        if "data" not in query_result or not query_result["data"]:
            logger.warning("No data found")
            return results
        
        # Convert data to DataFrame
        df = pd.DataFrame(
            query_result["data"]["data"],
            columns=query_result["data"]["columns"]
        )
        
        if df.empty or "source" not in df.columns:
            return results
        
        # Group by source and calculate statistics
        grouped = df.groupby("source").agg({
            "sentiment": ["count", "mean", "std", "min", "max"],
            "confidence": ["mean"]
        }).reset_index()
        
        # Rename columns
        grouped.columns = ["source", "count", "avg_sentiment", "std_sentiment", 
                          "min_sentiment", "max_sentiment", "avg_confidence"]
        
        # Convert to list format
        for _, row in grouped.iterrows():
            source = row["source"]
            if source in sources:
                results["comparison"].append({
                    "source": source,
                    "count": int(row["count"]),
                    "avg_sentiment": float(row["avg_sentiment"]) if not pd.isna(row["avg_sentiment"]) else None,
                    "std_sentiment": float(row["std_sentiment"]) if not pd.isna(row["std_sentiment"]) else None,
                    "min_sentiment": float(row["min_sentiment"]) if not pd.isna(row["min_sentiment"]) else None,
                    "max_sentiment": float(row["max_sentiment"]) if not pd.isna(row["max_sentiment"]) else None,
                    "avg_confidence": float(row["avg_confidence"]) if not pd.isna(row["avg_confidence"]) else None
                })
        
        return results
    
    @staticmethod
    def sentiment_distribution(
        query_engine,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sources: Optional[List[str]] = None,
        bins: int = 20
    ) -> Dict[str, Any]:
        """
        Get sentiment distribution.
        
        Args:
            query_engine: The QueryEngine instance
            ticker (Optional[str]): Ticker to filter by
            start_date (Optional[str]): Start date string
            end_date (Optional[str]): End date string
            sources (Optional[List[str]]): List of sources to include
            bins (int): Number of bins for histogram
            
        Returns:
            Dict[str, Any]: Sentiment distribution results
            
        Example:
            result = QueryPatterns.sentiment_distribution(
                query_engine,
                ticker="AAPL",
                start_date="2025-01-01",
                end_date="2025-04-23",
                bins=20
            )
        """
        # Parse dates
        start = query_engine.parse_date(start_date) if start_date else None
        end = query_engine.parse_date(end_date) if end_date else None
        
        # Query parameters
        params = {
            "start_date": start,
            "end_date": end,
            "sources": sources,
            "bins": bins
        }
        
        if ticker:
            params["ticker"] = ticker
        
        # Execute histogram query
        hist_result = query_engine.execute_query("sentiment_histogram", params)
        
        # Extract histogram data
        if "bins" in hist_result and "counts" in hist_result:
            bins = hist_result["bins"]
            counts = hist_result["counts"]
        else:
            # Fallback if histogram query failed
            query_type = "ticker" if ticker else "date_range"
            
            query_result = query_engine.execute_query(query_type, params)
            
            if "data" not in query_result or not query_result["data"]:
                logger.warning("No data found")
                return {
                    "ticker": ticker,
                    "start_date": start.isoformat() if start else None,
                    "end_date": end.isoformat() if end else None,
                    "sources": sources,
                    "bins": [],
                    "counts": [],
                    "bin_edges": [],
                    "total": 0,
                    "statistics": {}
                }
            
            # Convert data to DataFrame
            df = pd.DataFrame(
                query_result["data"]["data"],
                columns=query_result["data"]["columns"]
            )
            
            # Calculate histogram
            if "sentiment" in df.columns:
                counts, bin_edges = np.histogram(df["sentiment"].dropna(), bins=bins)
                bins = [float(edge) for edge in bin_edges[:-1]]
                counts = [int(count) for count in counts]
                
                # Calculate statistics
                stats = {
                    "mean": float(df["sentiment"].mean()) if not df["sentiment"].isna().all() else None,
                    "std": float(df["sentiment"].std()) if not df["sentiment"].isna().all() and len(df) > 1 else None,
                    "min": float(df["sentiment"].min()) if not df["sentiment"].isna().all() else None,
                    "max": float(df["sentiment"].max()) if not df["sentiment"].isna().all() else None,
                    "median": float(df["sentiment"].median()) if not df["sentiment"].isna().all() else None,
                    "count": int(df["sentiment"].count())
                }
            else:
                bins = []
                counts = []
                stats = {}
        
        # Prepare result
        result = {
            "ticker": ticker,
            "start_date": start.isoformat() if start else None,
            "end_date": end.isoformat() if end else None,
            "sources": sources,
            "bins": bins,
            "counts": counts,
            "bin_edges": [bins[0]] + [bins[-1] + (bins[1] - bins[0])] if bins else [],
            "total": sum(counts) if counts else 0,
            "statistics": stats if 'stats' in locals() else {}
        }
        
        return result