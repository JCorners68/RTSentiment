#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from data_manager.dedup_utility import deduplicate_parquet

def main():
    """
    Run deduplication on all parquet files in the output directory.
    """
    input_dir = '/home/jonat/WSL_RT_Sentiment/data/output/'
    output_dir = '/home/jonat/WSL_RT_Sentiment/data/output/deduplicated/'
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    # Count total files and initialize counters
    parquet_files = [f for f in os.listdir(input_dir) if f.endswith('.parquet')]
    total_files = len(parquet_files)
    processed_files = 0
    total_duplicates_removed = 0
    
    print(f"Found {total_files} parquet files to process")
    
    # Process each file individually
    for filename in parquet_files:
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        print(f"\nProcessing file {processed_files + 1}/{total_files}: {filename}")
        
        try:
            dups_removed = deduplicate_parquet(input_path, output_path)
            total_duplicates_removed += dups_removed
            processed_files += 1
            print(f"Successfully deduplicated {filename}: Removed {dups_removed} duplicates")
        except Exception as e:
            print(f"ERROR processing {filename}: {str(e)}")
    
    # Print summary
    print("\n=== DEDUPLICATION SUMMARY ===")
    print(f"Total files processed: {processed_files}/{total_files}")
    print(f"Total duplicates removed: {total_duplicates_removed}")
    print(f"Deduplicated files saved to: {output_dir}")

if __name__ == "__main__":
    main()