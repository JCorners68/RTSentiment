#!/usr/bin/env python3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import glob
import os

def combine_parquet_files(source_dir, output_file):
    """Combine all parquet files in a directory into a single parquet file."""
    
    # Find all parquet files
    files = glob.glob(f'{source_dir}/*.parquet')
    
    print(f'Found {len(files)} parquet files to combine')
    
    # Initialize empty list to store dataframes
    dfs = []
    total_rows = 0
    
    # Process each file
    for i, file_path in enumerate(files):
        try:
            # Read the parquet file
            table = pq.read_table(file_path)
            df = table.to_pandas()
            
            # Add the dataframe to our list
            dfs.append(df)
            total_rows += len(df)
            
            # Print progress
            if (i+1) % 50 == 0 or i == len(files) - 1:
                print(f'Processed {i+1}/{len(files)} files...')
                
        except Exception as e:
            print(f'Error processing {file_path}: {e}')
    
    # Combine all dataframes
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Create the output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write to output file
        table = pa.Table.from_pandas(combined_df)
        pq.write_table(table, output_file)
        
        print(f'Combined {len(dfs)} files with {len(combined_df)} total rows')
        print(f'Output saved to {output_file}')
    else:
        print('No valid files to combine')

if __name__ == '__main__':
    source_dir = '/app/data/output/real_clean'
    output_file = '/app/data/output/combined/all_clean_sentiment.parquet'
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    combine_parquet_files(source_dir, output_file)