"""
Parquet data loader for sentiment data
"""
import os
import logging
import pandas as pd
import glob
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ParquetLoader:
    """
    Loads and processes sentiment data from Parquet files
    """
    def __init__(self, parquet_dir):
        """
        Initialize the Parquet loader
        
        Args:
            parquet_dir: Directory containing Parquet files
        """
        self.parquet_dir = parquet_dir
        logger.info(f"Initialized ParquetLoader with directory: {parquet_dir}")
        
    def get_available_sources(self):
        """
        Get list of available data sources based on filenames
        
        Returns:
            List of source names
        """
        pattern = os.path.join(self.parquet_dir, "*.parquet")
        files = glob.glob(pattern)
        sources = [os.path.basename(f).split('_')[0] for f in files 
                  if os.path.basename(f).endswith('_sentiment.parquet')]
        return list(set(sources))
        
    def load_recent_data(self, hours_back=24, sources=None):
        """
        Load recent sentiment data from Parquet files
        
        Args:
            hours_back: Number of hours to look back
            sources: Optional list of sources to include (None for all)
            
        Returns:
            DataFrame with combined sentiment data
        """
        # Determine time cutoff
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        logger.info(f"Loading data since {cutoff_time}")
        
        # Find all Parquet files
        pattern = os.path.join(self.parquet_dir, "*.parquet")
        all_files = glob.glob(pattern)
        logger.debug(f"Found {len(all_files)} total Parquet files")
        
        # Filter files by source if requested
        if sources:
            filtered_files = []
            for source in sources:
                source_pattern = os.path.join(self.parquet_dir, f"{source}_*.parquet")
                filtered_files.extend(glob.glob(source_pattern))
            files_to_load = filtered_files
            logger.debug(f"Filtered to {len(files_to_load)} files matching sources: {sources}")
        else:
            files_to_load = all_files
            
        # Load and combine data
        dataframes = []
        for filename in files_to_load:
            try:
                df = pd.read_parquet(filename)
                
                # Filter by timestamp if available
                if 'timestamp' in df.columns:
                    df = df[df['timestamp'] >= cutoff_time]
                
                dataframes.append(df)
                logger.debug(f"Loaded {len(df)} rows from {filename}")
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
                
        # Combine all dataframes
        if not dataframes:
            logger.warning("No data loaded")
            return pd.DataFrame()
            
        combined_df = pd.concat(dataframes, ignore_index=True)
        logger.info(f"Loaded {len(combined_df)} total rows")
        
        return combined_df
        
    def load_historical(self, start_date, end_date=None, sources=None):
        """
        Load historical sentiment data from Parquet files
        
        Args:
            start_date: Start date (datetime or string YYYY-MM-DD)
            end_date: End date (datetime or string YYYY-MM-DD) or None for today
            sources: Optional list of sources to include (None for all)
            
        Returns:
            DataFrame with combined sentiment data
        """
        # Convert string dates to datetime if needed
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        
        if end_date is None:
            end_date = datetime.now()
        elif isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)
            
        logger.info(f"Loading historical data from {start_date} to {end_date}")
        
        # Load data from historical directory
        historical_dir = os.path.join(self.parquet_dir, "historical")
        pattern = os.path.join(historical_dir, "*.json")
        all_files = glob.glob(pattern)
        
        # Filter files by date range and source
        dataframes = []
        for filename in all_files:
            basename = os.path.basename(filename)
            
            # Check if file matches requested sources
            file_source = basename.split('_')[0]
            if sources and file_source not in sources:
                continue
                
            # Extract date from filename (assuming format: source_YYYYMMDD.json)
            try:
                date_str = basename.split('_')[1].split('.')[0]
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                # Check if file is in date range
                if file_date < start_date or file_date > end_date:
                    continue
                    
                # Load the file
                try:
                    # For JSON files in historical directory
                    df = pd.read_json(filename)
                    dataframes.append(df)
                    logger.debug(f"Loaded {len(df)} rows from {filename}")
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
            except Exception as e:
                logger.warning(f"Could not parse date from filename {basename}: {e}")
                
        # Combine all dataframes
        if not dataframes:
            logger.warning("No historical data loaded")
            return pd.DataFrame()
            
        combined_df = pd.concat(dataframes, ignore_index=True)
        logger.info(f"Loaded {len(combined_df)} total historical rows")
        
        return combined_df