import abc
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScraperBase(abc.ABC):
    """Abstract base class for all scrapers."""

    def __init__(self, output_base_dir: str = "data/raw"):
        """
        Initializes the scraper.

        Args:
            output_base_dir (str): The base directory to save Parquet files.
                                    Defaults to "data/raw".
        """
        load_dotenv()  # Load environment variables from .env file
        self.output_base_dir = Path(output_base_dir)
        self.source_name = self.__class__.__name__.lower().replace("scraper", "")
        logger.info(f"Initializing {self.__class__.__name__}...")

    @abc.abstractmethod
    def scrape(self) -> List[Dict]:
        """
        Abstract method to perform scraping.

        Must be implemented by subclasses. Should fetch data from the source.

        Returns:
            List[Dict]: A list of dictionaries, where each dict represents a scraped item.
                        Should include a 'timestamp' field (datetime object).
        """
        pass

    def _prepare_dataframe(self, data: List[Dict]) -> Optional[pd.DataFrame]:
        """Converts raw data list to a Pandas DataFrame and adds partitioning columns."""
        if not data:
            logger.info("No data to prepare for DataFrame.")
            return None

        df = pd.DataFrame(data)

        # Ensure a timestamp column exists and is datetime
        if 'timestamp' not in df.columns:
            logger.warning("Timestamp column missing in scraped data. Using current time.")
            df['timestamp'] = datetime.now()
        # Attempt conversion if not already datetime
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        except Exception as e:
             logger.error(f"Failed to convert timestamp column to datetime: {e}. Using NaT.")
             df['timestamp'] = pd.NaT

        # Add partitioning columns
        # Handle potential NaT in timestamp
        df['year'] = df['timestamp'].dt.year.astype('Int64') # Use nullable Int
        df['month'] = df['timestamp'].dt.month.astype('Int64')
        df['day'] = df['timestamp'].dt.day.astype('Int64')

        # Add source column for potential merging later
        df['source'] = self.source_name

        # Define standard column order (example)
        # Adjust based on common fields across scrapers
        core_columns = ['id', 'timestamp', 'source', 'author', 'text', 'url']
        partition_columns = ['year', 'month', 'day']

        # Add missing core columns with None
        for col in core_columns:
            if col not in df.columns:
                df[col] = None

        # Include all original columns plus new ones, reordering core ones
        existing_columns = [col for col in df.columns if col not in core_columns + partition_columns]
        df = df[core_columns + existing_columns + partition_columns]

        logger.info(f"Prepared DataFrame with {len(df)} rows and columns: {df.columns.tolist()}")
        return df


    def save_to_parquet(self, data: List[Dict], **kwargs):
        """
        Converts scraped data to a Pandas DataFrame and saves it as partitioned Parquet files.

        Args:
            data (List[Dict]): The list of scraped data dictionaries.
            **kwargs: Additional arguments passed to pandas.DataFrame.to_parquet().
        """
        if not data:
            logger.warning("No data provided to save_to_parquet.")
            return

        df = self._prepare_dataframe(data)
        if df is None or df.empty:
             logger.warning("DataFrame is empty after preparation, skipping save.")
             return

        output_path = self.output_base_dir / self.source_name
        partition_cols = ['year', 'month', 'day']

        # Check if partitioning columns contain NaN/NaT, as this prevents saving
        if df[partition_cols].isnull().any().any():
            logger.error(f"Cannot save to Parquet due to null values in partition columns {partition_cols}. Dropping affected rows.")
            # Option 1: Drop rows with null partition values
            df.dropna(subset=partition_cols, inplace=True)
            if df.empty:
                logger.error("DataFrame is empty after dropping rows with null partition values. Skipping save.")
                return
            # Option 2: Fill with a placeholder (e.g., 0 or a specific date) - requires careful consideration
            # df[partition_cols] = df[partition_cols].fillna(0) # Example - use with caution

        # Ensure partitioning columns are integer types if they were nullable Int64 and had no NaNs after handling
        for col in partition_cols:
            if pd.api.types.is_integer_dtype(df[col]) or pd.api.types.is_float_dtype(df[col]): # Check numeric before casting
                 # Convert nullable Int to standard int if no NaNs remain
                 if df[col].isnull().sum() == 0:
                     df[col] = df[col].astype(int)
            else:
                 logger.error(f"Partition column '{col}' is not numeric after NaN handling. Type: {df[col].dtype}. Skipping save.")
                 return

        # Define PyArrow schema explicitly for better control (optional but recommended)
        try:
            # Dynamically create schema based on DataFrame dtypes
            pyarrow_schema = pa.Schema.from_pandas(df, preserve_index=False)
            logger.info(f"Inferred PyArrow schema: {pyarrow_schema}")
        except Exception as e:
             logger.error(f"Could not create PyArrow schema from DataFrame: {e}. Saving without explicit schema.")
             pyarrow_schema = None


        try:
            logger.info(f"Saving {len(df)} rows to Parquet at {output_path} partitioned by {partition_cols}")
            df.to_parquet(
                output_path,
                engine='pyarrow',          # Use pyarrow engine
                compression='snappy',      # Common compression choice
                index=False,               # Don't write pandas index
                partition_cols=partition_cols, # Specify partitioning columns
                schema=pyarrow_schema,     # Use explicit schema if defined
                existing_data_behavior='overwrite_or_ignore', # Or 'delete_matching' based on need
                **kwargs
            )
            logger.info(f"Successfully saved data to {output_path}")
        except Exception as e:
            logger.exception(f"Failed to save data to Parquet: {e}") # Use logger.exception to include traceback

    def run(self):
        """Runs the scraper: scrapes data and saves it."""
        logger.info(f"Running {self.__class__.__name__}...")
        try:
            scraped_data = self.scrape()
            if scraped_data:
                self.save_to_parquet(scraped_data)
            else:
                logger.info("No data scraped.")
        except Exception as e:
            logger.exception(f"An error occurred during the run of {self.__class__.__name__}: {e}")
        finally:
            logger.info(f"Finished running {self.__class__.__name__}.")