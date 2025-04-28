#!/usr/bin/env python3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os

def deduplicate_single_file(file_path, output_path):
    """Deduplicate a single parquet file based on timestamp and article_title."""
    
    print(f"Processing file: {file_path}")
    
    try:
        # Read the parquet file
        table = pq.read_table(file_path)
        df = table.to_pandas()
        
        # Print file info before deduplication
        print(f"Original rows: {len(df)}")
        print(f"Unique article titles: {df['article_title'].nunique()}")
        print(f"Unique article IDs: {df['article_id'].nunique()}")
        
        # Get a sample
        print("\nSample before deduplication:")
        print(df[['timestamp', 'ticker', 'article_id', 'article_title']].head(3))
        
        # Deduplicate based on timestamp and article_title
        df_deduped = df.drop_duplicates(subset=['timestamp', 'article_title'], keep='first')
        
        # Print info after deduplication
        print(f"\nAfter deduplication - rows: {len(df_deduped)}")
        print(f"Reduction: {len(df) - len(df_deduped)} rows removed ({((len(df) - len(df_deduped)) / len(df) * 100):.1f}%)")
        
        # Create the output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write the deduplicated data to output
        table_deduped = pa.Table.from_pandas(df_deduped)
        pq.write_table(table_deduped, output_path)
        
        print(f"Deduplicated file saved to: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    # Path for aacr_sentiment.parquet (when running in Docker)
    input_file = '/app/data/output/aacr_sentiment.parquet'
    output_file = '/app/data/output/aacr_deduped.parquet'
    
    # Make sure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Process the file
    deduplicate_single_file(input_file, output_file)