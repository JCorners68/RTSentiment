#!/usr/bin/env python3

import os
import glob
import subprocess
import sys
from pathlib import Path

def main():
    # Define directories
    input_dir = "/home/jonat/WSL_RT_Sentiment/data/output"
    output_dir = "/home/jonat/WSL_RT_Sentiment/data/output/deduplicated"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all parquet files in the input directory
    parquet_files = glob.glob(os.path.join(input_dir, "*.parquet"))
    
    if not parquet_files:
        print(f"No parquet files found in {input_dir}")
        return
    
    print(f"Found {len(parquet_files)} parquet files to process")
    
    # Process each file
    total_files = len(parquet_files)
    processed_files = 0
    total_duplicates_removed = 0
    failed_files = []
    
    for file_path in parquet_files:
        file_name = os.path.basename(file_path)
        output_path = os.path.join(output_dir, file_name)
        
        print(f"Processing {file_path} ({processed_files + 1}/{total_files})...")
        
        try:
            # Run the deduplication utility
            cmd = [
                "python3", 
                "./data_manager/dedup_utility.py", 
                file_path, 
                "--output_path", output_path, 
                "--columns", "article_title"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error processing {file_path}: {result.stderr}")
                failed_files.append(file_path)
                continue
            
            # Extract number of duplicates removed from output
            for line in result.stdout.split('\n'):
                if "Total duplicates removed:" in line:
                    try:
                        dups = int(line.split(':')[1].strip())
                        total_duplicates_removed += dups
                        print(f"Removed {dups} duplicates from {file_name}")
                        break
                    except:
                        pass
            
            processed_files += 1
            
        except Exception as e:
            print(f"Exception processing {file_path}: {str(e)}")
            failed_files.append(file_path)
    
    # Print summary
    print("\nDeduplication process complete")
    print(f"Successfully processed: {processed_files}/{total_files} files")
    print(f"Total duplicates removed: {total_duplicates_removed}")
    
    if failed_files:
        print(f"Failed to process {len(failed_files)} files:")
        for f in failed_files:
            print(f"  - {f}")

if __name__ == "__main__":
    main()