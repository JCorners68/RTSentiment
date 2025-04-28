#\!/usr/bin/env python3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import glob
from collections import defaultdict
import sys

def deduplicate_parquet(file_path, output_dir):
    """Deduplicate records in a parquet file based on timestamp and article_title."""
    try:
        # Read the parquet file
        table = pq.read_table(file_path)
        df = table.to_pandas()
        
        # Check original row count
        original_count = len(df)
        
        # Drop duplicates based on timestamps and article titles
        df_deduped = df.drop_duplicates(subset=['timestamp', 'article_title'], keep='first')
        
        # Get deduplicated count
        deduped_count = len(df_deduped)
        
        # Calculate reduction
        if original_count > 0:
            reduction = ((original_count - deduped_count) / original_count) * 100
        else:
            reduction = 0
        
        # Create the output file path
        filename = os.path.basename(file_path)
        output_path = os.path.join(output_dir, filename)
        
        # Write the deduplicated data to output
        table_deduped = pa.Table.from_pandas(df_deduped)
        pq.write_table(table_deduped, output_path)
        
        return {
            'file': filename,
            'original': original_count,
            'deduped': deduped_count,
            'reduction': reduction
        }
    except Exception as e:
        return {'file': os.path.basename(file_path), 'error': str(e)}

def main():
    # Create output directory if it doesn't exist
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'data/output/deduplicated')
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all parquet files in the data/output/ticker directory
    search_dir = os.path.join(base_dir, 'data/output/ticker')
    files = glob.glob(f'{search_dir}/*.parquet')
    
    # Skip files in the deduplicated subdirectory
    files = [f for f in files if '/deduplicated/' not in f]
    
    print(f'Found {len(files)} parquet files to process')
    
    # Process each file
    results = []
    total_original = 0
    total_deduped = 0
    files_with_dupes = 0
    
    for i, file_path in enumerate(files):
        result = deduplicate_parquet(file_path, output_dir)
        
        if 'error' in result:
            print(f'Error processing {result["file"]}: {result["error"]}')
            continue
            
        total_original += result['original']
        total_deduped += result['deduped']
        
        # Track files with duplicates
        if result['original'] != result['deduped']:
            files_with_dupes += 1
            results.append(result)
        
        # Print progress
        if (i+1) % 50 == 0 or i == len(files) - 1:
            print(f'Processed {i+1}/{len(files)} files...')
    
    # Print results for files with significant duplication
    print('\nSummary of files with duplicates:')
    for result in sorted(results, key=lambda x: x['reduction'], reverse=True)[:20]:
        print(f'{result["file"]}: {result["original"]} → {result["deduped"]} ({result["reduction"]:.1f}% reduction)')
    
    # Print overall stats
    total_reduction = ((total_original - total_deduped) / total_original) * 100 if total_original > 0 else 0
    print(f'\nOverall stats:')
    print(f'Total files processed: {len(files)}')
    print(f'Files with duplicates: {files_with_dupes}')
    print(f'Total original records: {total_original}')
    print(f'Total deduplicated records: {total_deduped}')
    print(f'Overall reduction: {total_reduction:.1f}%')
    print(f'Deduplicated files saved to {output_dir}')

if __name__ == '__main__':
    main()
