#!/usr/bin/env python3
"""
Script to deduplicate a specific parquet file based on timestamp and article_title.

Usage:
    python3 deduplicate_file.py <parquet_file_path>
    
Example:
    python3 deduplicate_file.py data/output/aapl_sentiment.parquet
    python3 deduplicate_file.py data/output/tsla_sentiment.parquet
"""

import os
import sys
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

def deduplicate_parquet_file(input_file):
    """
    Deduplicate a specific parquet file based on timestamp and article_title.
    
    Args:
        input_file (str): Path to the parquet file
        
    Returns:
        dict: Statistics about the deduplication process
    """
    try:
        # Extract the file name
        file_name = os.path.basename(input_file)
        
        # Create output directory and path
        output_dir = os.path.join(os.path.dirname(input_file), "fixed")
        output_file = os.path.join(output_dir, file_name)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Check if input file exists
        if not os.path.exists(input_file):
            print(f"Error: Input file {input_file} does not exist")
            return None
        
        # Read the parquet file
        print(f"Reading file: {input_file}")
        table = pq.read_table(input_file)
        df = table.to_pandas()
        
        # Print file info before deduplication
        original_count = len(df)
        unique_titles = df['article_title'].nunique()
        
        print(f"Original rows: {original_count}")
        print(f"Unique article titles: {unique_titles}")
        
        if 'article_id' in df.columns:
            unique_ids = df['article_id'].nunique()
            print(f"Unique article IDs: {unique_ids}")
        
        # Show sample before deduplication
        print("\nSample data before deduplication:")
        sample_cols = ['timestamp', 'article_title']
        if 'article_id' in df.columns:
            sample_cols.append('article_id')
        print(df[sample_cols].head(3))
        
        # Deduplicate based on timestamp and article_title
        print("\nRemoving duplicates...")
        df_deduped = df.drop_duplicates(subset=['timestamp', 'article_title'], keep='first')
        
        # Print file info after deduplication
        deduped_count = len(df_deduped)
        duplicates_removed = original_count - deduped_count
        
        print(f"Deduplicated rows: {deduped_count}")
        print(f"Removed {duplicates_removed} duplicates")
        
        reduction_pct = 0
        if original_count > 0:
            reduction_pct = (duplicates_removed / original_count) * 100
            print(f"Reduction: {reduction_pct:.2f}%")
        
        # Write the deduplicated data to output
        print(f"Writing deduplicated data to {output_file}")
        table_deduped = pa.Table.from_pandas(df_deduped)
        pq.write_table(table_deduped, output_file)
        
        print(f"Deduplication complete. Deduplicated file saved to {output_file}")
        
        # Extract ticker from filename (assuming format like "aapl_sentiment.parquet")
        ticker = file_name.split('_')[0] if '_' in file_name else 'unknown'
        
        # Return stats
        return {
            "file": file_name,
            "ticker": ticker,
            "original_count": original_count,
            "deduped_count": deduped_count,
            "duplicates_removed": duplicates_removed,
            "reduction_pct": reduction_pct
        }
        
    except Exception as e:
        print(f"Error while deduplicating file: {e}")
        return None

if __name__ == "__main__":
    # Check if a file path was provided
    if len(sys.argv) < 2:
        print("Error: Please provide a parquet file path")
        print("Usage: python deduplicate_file.py <parquet_file_path>")
        print("Example: python deduplicate_file.py data/output/aapl_sentiment.parquet")
        sys.exit(1)
    
    # Get the file path from command line arguments
    file_path = sys.argv[1]
    
    print(f"Starting deduplication for {os.path.basename(file_path)}")
    result = deduplicate_parquet_file(file_path)
    
    if result:
        print("\nDeduplication Summary:")
        print(f"File: {result['file']}")
        print(f"Ticker: {result['ticker']}")
        print(f"Original rows: {result['original_count']}")
        print(f"Deduplicated rows: {result['deduped_count']}")
        print(f"Duplicates removed: {result['duplicates_removed']}")
        print(f"Reduction: {result['reduction_pct']:.2f}%")
    else:
        print("Deduplication failed. Please check the error messages above.")