import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import List, Dict, Any, Optional, Tuple
import datetime
import os
import glob
import logging

logger = logging.getLogger(__name__)

class ParquetReader:
    """Interface for reading sentiment data from Parquet files."""
    
    def __init__(self, data_dir: str = "/home/jonat/WSL_RT_Sentiment/data/output"):
        """
        Initialize the Parquet reader.
        
        Args:
            data_dir: Directory containing Parquet files
        """
        self.data_dir = data_dir
        
    def _get_parquet_files(self) -> List[str]:
        """
        Get all Parquet files in the data directory.
        
        Returns:
            List of file paths
        """
        return glob.glob(os.path.join(self.data_dir, "*.parquet"))
        
    def read_ticker_data(self, ticker: str, start_date: Optional[datetime.datetime] = None,
                        end_date: Optional[datetime.datetime] = None) -> pd.DataFrame:
        """
        Read sentiment data for a specific ticker.
        
        Args:
            ticker: Ticker symbol
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with sentiment data
        """
        ticker = ticker.upper()
        ticker_file = os.path.join(self.data_dir, f"{ticker.lower()}_sentiment.parquet")
        multi_ticker_file = os.path.join(self.data_dir, "multi_ticker_sentiment.parquet")
        
        dfs = []
        
        # Try ticker-specific file first
        if os.path.exists(ticker_file):
            try:
                df = pd.read_parquet(ticker_file)
                dfs.append(df)
            except Exception as e:
                logger.error(f"Error reading {ticker_file}: {e}")
                
        # Then try the multi-ticker file
        if os.path.exists(multi_ticker_file):
            try:
                # Use PyArrow for more efficient filtering
                table = pq.read_table(multi_ticker_file)
                ticker_filter = pa.compute.equal(table['ticker'], ticker)
                filtered_table = table.filter(ticker_filter)
                
                if filtered_table.num_rows > 0:
                    df = filtered_table.to_pandas()
                    dfs.append(df)
                    
            except Exception as e:
                logger.error(f"Error reading {multi_ticker_file} for {ticker}: {e}")
                
        # Combine all dataframes
        if not dfs:
            return pd.DataFrame()  # Empty DataFrame if no data found
            
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Apply date filters if provided
        if start_date is not None:
            combined_df = combined_df[combined_df['timestamp'] >= start_date]
            
        if end_date is not None:
            combined_df = combined_df[combined_df['timestamp'] <= end_date]
            
        # Sort by timestamp
        combined_df = combined_df.sort_values('timestamp')
        
        return combined_df
        
    def get_all_tickers(self) -> List[str]:
        """
        Get a list of all tickers in the Parquet files.
        
        Returns:
            List of ticker symbols
        """
        tickers = set()
        
        # Check ticker-specific files
        for file_path in glob.glob(os.path.join(self.data_dir, "*_sentiment.parquet")):
            file_name = os.path.basename(file_path)
            if file_name.endswith("_sentiment.parquet") and file_name != "multi_ticker_sentiment.parquet":
                ticker = file_name.replace("_sentiment.parquet", "").upper()
                tickers.add(ticker)
                
        # Check multi-ticker file
        multi_ticker_file = os.path.join(self.data_dir, "multi_ticker_sentiment.parquet")
        if os.path.exists(multi_ticker_file):
            try:
                table = pq.read_table(multi_ticker_file, columns=['ticker'])
                ticker_column = table['ticker']
                unique_tickers = pd.Series(ticker_column.to_numpy()).unique()
                tickers.update(unique_tickers)
            except Exception as e:
                logger.error(f"Error reading tickers from {multi_ticker_file}: {e}")
                
        return sorted(list(tickers))
        
    def get_latest_events(self, ticker: Optional[str] = None, 
                         limit: int = 100, 
                         hours: Optional[int] = None) -> pd.DataFrame:
        """
        Get the latest sentiment events.
        
        Args:
            ticker: Optional ticker filter
            limit: Maximum number of events to return
            hours: Only include events from the last N hours
            
        Returns:
            DataFrame with sentiment events
        """
        now = datetime.datetime.now()
        start_date = now - datetime.timedelta(hours=hours) if hours else None
        
        if ticker:
            # Get data for specific ticker
            df = self.read_ticker_data(ticker, start_date=start_date)
        else:
            # Get data for all tickers
            dfs = []
            for file_path in self._get_parquet_files():
                try:
                    df = pd.read_parquet(file_path)
                    dfs.append(df)
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
                    
            if not dfs:
                return pd.DataFrame()
                
            df = pd.concat(dfs, ignore_index=True)
            
            # Apply date filter if provided
            if start_date:
                df = df[df['timestamp'] >= start_date]
                
        # Sort by timestamp (most recent first) and limit results
        df = df.sort_values('timestamp', ascending=False).head(limit)
        
        return df