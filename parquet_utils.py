#!/usr/bin/env python3
"""
Utility script for managing Parquet files in the data pipeline.
This script provides functionality to:
1. Show schema of Parquet files
2. Deduplicate data in Parquet files
3. Optimize Parquet files for FDW queries
"""
import os
import sys
import argparse
import logging
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('parquet_utils')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Parquet file management utilities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show schema of a parquet file
  python3 parquet_utils.py schema --file data/output/aapl_sentiment.parquet
  
  # Deduplicate a parquet file
  python3 parquet_utils.py dedup --file data/output/aapl_sentiment.parquet
  
  # Optimize a parquet file for FDW queries
  python3 parquet_utils.py optimize --file data/output/aapl_sentiment.parquet --sort-by timestamp
  
  # Process all parquet files in a directory
  python3 parquet_utils.py process-all --dir data/output --action optimize
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Schema command
    schema_parser = subparsers.add_parser('schema', help='Show schema of a parquet file')
    schema_parser.add_argument('--file', type=str, required=True, help='Path to parquet file')
    
    # Dedup command
    dedup_parser = subparsers.add_parser('dedup', help='Deduplicate a parquet file')
    dedup_parser.add_argument('--file', type=str, required=True, help='Path to parquet file')
    dedup_parser.add_argument('--key-cols', type=str, nargs='+', default=['article_id', 'ticker'], 
                             help='Columns to use as the deduplication key')
    dedup_parser.add_argument('--dry-run', action='store_true', help='Only show what would be done')
    
    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Optimize a parquet file for FDW queries')
    optimize_parser.add_argument('--file', type=str, required=True, help='Path to parquet file')
    optimize_parser.add_argument('--sort-by', type=str, default='timestamp', 
                               help='Column to sort by')
    optimize_parser.add_argument('--compression', type=str, default='SNAPPY', 
                               choices=['SNAPPY', 'GZIP', 'ZSTD', 'NONE'],
                               help='Compression algorithm to use')
    optimize_parser.add_argument('--row-group-size', type=int, default=100000, 
                               help='Number of rows per row group')
    optimize_parser.add_argument('--dry-run', action='store_true', help='Only show what would be done')
    
    # Process all command
    process_all_parser = subparsers.add_parser('process-all', help='Process all parquet files in a directory')
    process_all_parser.add_argument('--dir', type=str, required=True, help='Directory containing parquet files')
    process_all_parser.add_argument('--action', type=str, required=True, 
                                  choices=['schema', 'dedup', 'optimize'],
                                  help='Action to perform on each file')
    process_all_parser.add_argument('--key-cols', type=str, nargs='+', default=['article_id', 'ticker'], 
                                  help='Columns to use as the deduplication key (for dedup action)')
    process_all_parser.add_argument('--sort-by', type=str, default='timestamp', 
                                  help='Column to sort by (for optimize action)')
    process_all_parser.add_argument('--compression', type=str, default='SNAPPY', 
                                  choices=['SNAPPY', 'GZIP', 'ZSTD', 'NONE'],
                                  help='Compression algorithm to use (for optimize action)')
    process_all_parser.add_argument('--row-group-size', type=int, default=100000, 
                                  help='Number of rows per row group (for optimize action)')
    process_all_parser.add_argument('--dry-run', action='store_true', help='Only show what would be done')
    
    return parser.parse_args()

def show_schema(file_path: str) -> None:
    """Show the schema of a parquet file."""
    try:
        logger.info(f"Reading schema from {file_path}")
        table = pq.read_table(file_path)
        schema = table.schema
        
        logger.info(f"Schema for {os.path.basename(file_path)}:")
        for i, field in enumerate(schema):
            logger.info(f"  Field {i}: {field.name} - {field.type}")
        
        # Also show basic statistics
        num_rows = table.num_rows
        num_columns = len(schema)
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        
        logger.info(f"File statistics:")
        logger.info(f"  Rows: {num_rows}")
        logger.info(f"  Columns: {num_columns}")
        logger.info(f"  Size: {size_mb:.2f} MB")
        
        # Show unique values for categorical columns (if small enough)
        for field in schema:
            if field.type in [pa.string(), pa.dictionary(pa.int32(), pa.string())]:
                col_data = table[field.name].to_pandas()
                unique_values = col_data.unique()
                if len(unique_values) < 10:  # Only show if not too many unique values
                    logger.info(f"  Unique values for {field.name}: {sorted(unique_values)}")
        
        return schema
    except Exception as e:
        logger.error(f"Error reading schema: {e}")
        return None

def deduplicate_parquet(file_path: str, key_cols: List[str] = ['article_id', 'ticker'], dry_run: bool = False) -> bool:
    """
    Deduplicate a parquet file based on specified key columns.
    
    Args:
        file_path: Path to the parquet file
        key_cols: List of column names to use as the deduplication key
        dry_run: If True, only show what would be done without making changes
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Deduplicating {file_path} based on key columns: {key_cols}")
        
        # Read the parquet file into a pandas DataFrame
        df = pd.read_parquet(file_path)
        original_rows = len(df)
        logger.info(f"Original file has {original_rows} rows")
        
        # Check if key columns exist in the DataFrame
        missing_cols = [col for col in key_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Key columns {missing_cols} not found in the file")
            return False
        
        # Check for duplicates
        duplicates = df.duplicated(subset=key_cols, keep='first')
        num_duplicates = duplicates.sum()
        
        if num_duplicates == 0:
            logger.info(f"No duplicates found based on key columns: {key_cols}")
            return True
        
        logger.info(f"Found {num_duplicates} duplicate rows ({num_duplicates/original_rows:.2%} of data)")
        
        if dry_run:
            logger.info("Dry run mode: No changes made")
            return True
        
        # Deduplicate the DataFrame
        df_deduped = df.drop_duplicates(subset=key_cols, keep='first')
        
        # Create a backup of the original file
        backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Creating backup at {backup_path}")
        os.rename(file_path, backup_path)
        
        # Write the deduplicated DataFrame back to the original file
        logger.info(f"Writing deduplicated data with {len(df_deduped)} rows")
        df_deduped.to_parquet(file_path, index=False)
        
        logger.info(f"Successfully deduplicated {file_path}")
        logger.info(f"Removed {num_duplicates} duplicate rows")
        
        return True
    except Exception as e:
        logger.error(f"Error deduplicating file: {e}")
        return False

def optimize_parquet(file_path: str, sort_by: str = 'timestamp', 
                    compression: str = 'SNAPPY', row_group_size: int = 100000,
                    dry_run: bool = False) -> bool:
    """
    Optimize a parquet file for FDW queries.
    
    Args:
        file_path: Path to the parquet file
        sort_by: Column to sort by
        compression: Compression algorithm to use
        row_group_size: Number of rows per row group
        dry_run: If True, only show what would be done without making changes
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Optimizing {file_path}")
        logger.info(f"  Sort by: {sort_by}")
        logger.info(f"  Compression: {compression}")
        logger.info(f"  Row group size: {row_group_size}")
        
        # Read the parquet file into a pandas DataFrame
        df = pd.read_parquet(file_path)
        original_rows = len(df)
        logger.info(f"Original file has {original_rows} rows")
        
        # Check if sort column exists
        if sort_by not in df.columns:
            logger.error(f"Sort column {sort_by} not found in the file")
            return False
        
        if dry_run:
            logger.info("Dry run mode: No changes made")
            return True
        
        # Create a backup of the original file
        backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Creating backup at {backup_path}")
        os.rename(file_path, backup_path)
        
        # Sort the DataFrame by the specified column
        logger.info(f"Sorting data by {sort_by}")
        df_sorted = df.sort_values(by=sort_by)
        
        # Write the optimized DataFrame back to the original file
        logger.info(f"Writing optimized data")
        df_sorted.to_parquet(
            file_path, 
            index=False,
            compression=compression,
            row_group_size=row_group_size
        )
        
        # Verify the file was written correctly
        new_size = os.path.getsize(file_path)
        old_size = os.path.getsize(backup_path)
        size_diff_pct = (new_size - old_size) / old_size * 100
        
        logger.info(f"Successfully optimized {file_path}")
        logger.info(f"Old size: {old_size/1024/1024:.2f} MB")
        logger.info(f"New size: {new_size/1024/1024:.2f} MB")
        logger.info(f"Size change: {size_diff_pct:.1f}%")
        
        return True
    except Exception as e:
        logger.error(f"Error optimizing file: {e}")
        # If something went wrong and we created a backup, try to restore it
        backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if os.path.exists(backup_path) and not os.path.exists(file_path):
            logger.info(f"Restoring from backup {backup_path}")
            os.rename(backup_path, file_path)
        return False

def process_all_files(directory: str, action: str, **kwargs) -> bool:
    """
    Process all parquet files in a directory.
    
    Args:
        directory: Directory containing parquet files
        action: Action to perform on each file (schema, dedup, optimize)
        **kwargs: Additional arguments for the action
        
    Returns:
        True if successful for all files, False otherwise
    """
    try:
        logger.info(f"Processing all parquet files in {directory}")
        
        # Find all parquet files
        parquet_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.parquet'):
                    parquet_files.append(os.path.join(root, file))
        
        if not parquet_files:
            logger.info(f"No parquet files found in {directory}")
            return True
        
        logger.info(f"Found {len(parquet_files)} parquet files")
        
        # Process each file
        success = True
        for file_path in parquet_files:
            logger.info(f"Processing {file_path}")
            
            if action == 'schema':
                result = show_schema(file_path) is not None
            elif action == 'dedup':
                result = deduplicate_parquet(
                    file_path,
                    key_cols=kwargs.get('key_cols', ['article_id', 'ticker']),
                    dry_run=kwargs.get('dry_run', False)
                )
            elif action == 'optimize':
                result = optimize_parquet(
                    file_path,
                    sort_by=kwargs.get('sort_by', 'timestamp'),
                    compression=kwargs.get('compression', 'SNAPPY'),
                    row_group_size=kwargs.get('row_group_size', 100000),
                    dry_run=kwargs.get('dry_run', False)
                )
            else:
                logger.error(f"Unknown action: {action}")
                return False
            
            success = success and result
        
        return success
    except Exception as e:
        logger.error(f"Error processing files: {e}")
        return False

def main():
    """Main function."""
    args = parse_args()
    
    if args.command == 'schema':
        show_schema(args.file)
    elif args.command == 'dedup':
        deduplicate_parquet(args.file, args.key_cols, args.dry_run)
    elif args.command == 'optimize':
        optimize_parquet(args.file, args.sort_by, args.compression, args.row_group_size, args.dry_run)
    elif args.command == 'process-all':
        process_all_files(
            args.dir,
            args.action,
            key_cols=args.key_cols,
            sort_by=args.sort_by,
            compression=args.compression,
            row_group_size=args.row_group_size,
            dry_run=args.dry_run
        )
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())