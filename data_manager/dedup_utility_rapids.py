#!/usr/bin/env python3
"""
GPU-accelerated utility for deduplicating parquet files.

This script uses RAPIDS cuDF to efficiently deduplicate financial data in
parquet files, with significant performance improvements for large datasets.
"""

import os
import glob
import argparse
import logging
from pathlib import Path
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import RAPIDS packages, fall back to pandas if not available
try:
    import cudf
    HAVE_RAPIDS = True
    logger.info("RAPIDS cuDF loaded successfully for GPU-accelerated deduplication")
except ImportError:
    import pandas as pd
    HAVE_RAPIDS = False
    logger.info("RAPIDS not available, using pandas instead")

def deduplicate_parquet(input_path, output_path=None, columns=None, keep='first', use_gpu=True):
    """
    Deduplicate a parquet file or directory of parquet files using GPU acceleration when available.
    
    Parameters:
    -----------
    input_path : str
        Path to a parquet file or directory containing parquet files
    output_path : str, optional
        Path to save deduplicated file(s). If None, will overwrite original.
    columns : list, optional
        Columns to consider for duplication. If None, uses all columns.
    keep : {'first', 'last', False}, default 'first'
        Which duplicates to keep:
        - 'first': Keep first occurrence of duplicates
        - 'last': Keep last occurrence of duplicates
        - False: Drop all duplicates
    use_gpu : bool, default True
        Whether to use GPU acceleration via RAPIDS when available
        
    Returns:
    --------
    int: Number of duplicate rows removed
    """
    # Decide whether to use GPU based on availability and preferences
    use_gpu = use_gpu and HAVE_RAPIDS
    start_time = time.time()
    
    logger.info(f"Starting deduplication process...")
    logger.info(f"Input path: {input_path}")
    logger.info(f"Output path: {output_path if output_path else 'Same as input (overwrite)'}")
    logger.info(f"Using GPU acceleration: {use_gpu}")
    
    total_dups_removed = 0
    
    # Handle single file case
    if os.path.isfile(input_path):
        logger.info(f"Reading parquet file: {input_path}")
        
        try:
            # Use appropriate library based on GPU availability
            if use_gpu:
                df = cudf.read_parquet(input_path)
            else:
                df = pd.read_parquet(input_path)
                
            original_len = len(df)
            logger.info(f"Original dataframe has {original_len} rows")
            
            # Handle 'keep' parameter for GPU implementation
            if use_gpu and keep is False:
                # For cuDF, keep=False is not supported, so we implement it differently
                # First identify duplicates without keeping any
                size_before = len(df)
                
                # Get mask of duplicates
                dups_mask = df.duplicated(subset=columns, keep=False)
                
                # Filter out all duplicated rows
                df = df[~dups_mask]
                
                dups_removed = size_before - len(df)
            else:
                # Standard deduplication (works for both pandas and cuDF)
                df = df.drop_duplicates(subset=columns, keep=keep)
                dups_removed = original_len - len(df)
                
            logger.info(f"Found and removed {dups_removed} duplicate rows")
            
            save_path = output_path if output_path else input_path
            
            # Create directory if it doesn't exist
            if not os.path.exists(os.path.dirname(save_path)):
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
            logger.info(f"Saving deduplicated data to: {save_path}")
            df.to_parquet(save_path, index=False)
            logger.info(f"Deduplication complete. New dataframe has {len(df)} rows")
            
            return dups_removed
            
        except Exception as e:
            logger.error(f"Error processing {input_path}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    # Handle directory case
    elif os.path.isdir(input_path):
        if output_path and not os.path.exists(output_path):
            os.makedirs(output_path)
            
        parquet_files = glob.glob(os.path.join(input_path, "*.parquet"))
        logger.info(f"Found {len(parquet_files)} parquet files in directory")
        
        for file in parquet_files:
            try:
                logger.info(f"Processing file: {file}")
                
                # Use appropriate library based on GPU availability
                if use_gpu:
                    df = cudf.read_parquet(file)
                else:
                    df = pd.read_parquet(file)
                    
                original_len = len(df)
                
                # Handle 'keep' parameter for GPU implementation
                if use_gpu and keep is False:
                    # For cuDF, keep=False is not supported, so we implement it differently
                    # First identify duplicates without keeping any
                    size_before = len(df)
                    
                    # Get mask of duplicates
                    dups_mask = df.duplicated(subset=columns, keep=False)
                    
                    # Filter out all duplicated rows
                    df = df[~dups_mask]
                    
                    file_dups_removed = size_before - len(df)
                else:
                    # Standard deduplication (works for both pandas and cuDF)
                    df = df.drop_duplicates(subset=columns, keep=keep)
                    file_dups_removed = original_len - len(df)
                
                total_dups_removed += file_dups_removed
                
                if output_path:
                    filename = os.path.basename(file)
                    save_path = os.path.join(output_path, filename)
                else:
                    save_path = file
                    
                df.to_parquet(save_path, index=False)
                
                logger.info(f"Processed {file}: Removed {file_dups_removed} duplicates")
                
            except Exception as e:
                logger.error(f"Error processing {file}: {str(e)}")
                # Continue processing other files
                
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Deduplication complete. Processed {len(parquet_files)} files in {duration:.2f} seconds")
        logger.info(f"Total duplicates removed: {total_dups_removed}")
            
        return total_dups_removed
    
    else:
        logger.error(f"ERROR: Input path {input_path} is not a valid file or directory")
        raise ValueError(f"Input path {input_path} is not a valid file or directory")

def main():
    """Main entry point for command line usage."""
    parser = argparse.ArgumentParser(description="Deduplicate parquet files with GPU acceleration")
    
    parser.add_argument("input_path", help="Path to parquet file or directory of parquet files")
    parser.add_argument("--output_path", help="Output path for deduplicated files")
    parser.add_argument("--columns", nargs="+", help="Columns to consider for duplication")
    parser.add_argument("--keep", choices=['first', 'last', 'none'], default='first',
                       help="Which duplicates to keep: first, last, or none")
    parser.add_argument("--no_gpu", action="store_true", help="Disable GPU acceleration")
    
    args = parser.parse_args()
    
    # Fix for positional arguments
    if len(args.input_path.split()) > 1:
        input_parts = args.input_path.split()
        args.input_path = input_parts[0]
        if not args.output_path and len(input_parts) > 1:
            args.output_path = input_parts[1]
    
    logger.info("Arguments:")
    logger.info(f"  Input path: {args.input_path}")
    logger.info(f"  Output path: {args.output_path}")
    logger.info(f"  Columns: {args.columns}")
    logger.info(f"  Keep: {args.keep}")
    logger.info(f"  Use GPU: {not args.no_gpu}")
    
    keep_value = False if args.keep == 'none' else args.keep
    
    try:
        dups_removed = deduplicate_parquet(
            args.input_path, 
            args.output_path, 
            args.columns, 
            keep_value,
            use_gpu=not args.no_gpu
        )
        logger.info(f"Total duplicates removed: {dups_removed}")
        logger.info("Deduplication completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())