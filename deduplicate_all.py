#!/usr/bin/env python3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import glob
import json
import time
from datetime import datetime
import argparse

def deduplicate_parquet(file_path, output_path, verbose=True):
    """Deduplicate a parquet file based on timestamp and article_title."""
    try:
        # Extract ticker name from filename
        ticker = os.path.basename(file_path).split('_')[0]
        
        if verbose:
            print(f"Processing {ticker} from {file_path}")
        
        # Read the parquet file
        table = pq.read_table(file_path)
        df = table.to_pandas()
        
        # Check original row count
        original_count = len(df)
        
        # Get unique article title count
        unique_titles = df['article_title'].nunique()
        
        if verbose:
            print(f"  Original rows: {original_count}")
            print(f"  Unique article titles: {unique_titles}")
        
        # Only process if duplicates exist
        if unique_titles < original_count:
            # Drop duplicates based on timestamps and article titles
            df_deduped = df.drop_duplicates(subset=['timestamp', 'article_title'], keep='first')
            
            # Get deduplicated count
            deduped_count = len(df_deduped)
            
            # Calculate reduction
            rows_removed = original_count - deduped_count
            reduction_percent = (rows_removed / original_count) * 100
            
            # Create the output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write the deduplicated data to output
            table_deduped = pa.Table.from_pandas(df_deduped)
            pq.write_table(table_deduped, output_path)
            
            if verbose:
                print(f"  After deduplication - rows: {deduped_count}")
                print(f"  Removed {rows_removed} duplicates ({reduction_percent:.1f}%)")
                print(f"  Saved to: {output_path}")
            
            return {
                'file': os.path.basename(file_path),
                'ticker': ticker,
                'original': original_count,
                'deduped': deduped_count,
                'rows_removed': rows_removed,
                'reduction_percent': reduction_percent,
                'status': 'Deduplicated',
                'unique_titles': unique_titles
            }
        else:
            if verbose:
                print("  No duplicates found")
                
            return {
                'file': os.path.basename(file_path),
                'ticker': ticker,
                'original': original_count,
                'deduped': original_count,
                'rows_removed': 0,
                'reduction_percent': 0,
                'status': 'No duplicates found',
                'unique_titles': unique_titles
            }
    except Exception as e:
        if verbose:
            print(f"  Error: {e}")
        return {
            'file': os.path.basename(file_path),
            'ticker': os.path.basename(file_path).split('_')[0] if '_' in os.path.basename(file_path) else 'unknown',
            'error': str(e)
        }

def save_report(results, output_file):
    """Save detailed report to JSON file."""
    # Generate timestamp for the report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate summary statistics
    total_files = len(results)
    files_with_dupes = sum(1 for r in results if r.get('status') == 'Deduplicated')
    error_files = sum(1 for r in results if 'error' in r)
    total_original = sum(r.get('original', 0) for r in results if 'original' in r)
    total_deduped = sum(r.get('deduped', 0) for r in results if 'deduped' in r)
    total_removed = sum(r.get('rows_removed', 0) for r in results if 'rows_removed' in r)
    
    # Calculate overall reduction percentage
    overall_reduction = (total_removed / total_original * 100) if total_original > 0 else 0
    
    # Create report structure
    report = {
        'timestamp': timestamp,
        'summary': {
            'total_files_processed': total_files,
            'files_with_duplicates': files_with_dupes,
            'files_with_errors': error_files,
            'total_original_records': total_original,
            'total_deduplicated_records': total_deduped,
            'total_rows_removed': total_removed,
            'overall_reduction_percent': overall_reduction
        },
        'files': results
    }
    
    # Write report to JSON file
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {output_file}")

def batch_process(input_dir, output_dir, report_file, sort_by_size=True, limit=None, verbose=True):
    """Process all parquet files in the input directory in batches."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all parquet files in input directory (excluding subdirectories)
    files = glob.glob(f'{input_dir}/*.parquet')
    
    if sort_by_size:
        # Sort files by size (smaller files first) to process quickly first
        files.sort(key=os.path.getsize)
    
    # Apply limit if specified
    if limit and limit > 0:
        files = files[:limit]
    
    print(f'Found {len(files)} parquet files to process')
    
    # Track results
    results = []
    total_original = 0
    total_deduped = 0
    files_with_dupes = 0
    
    # Process each file
    start_time = time.time()
    for i, file_path in enumerate(files):
        filename = os.path.basename(file_path)
        output_path = os.path.join(output_dir, filename)
        
        # Process the file
        result = deduplicate_parquet(file_path, output_path, verbose)
        results.append(result)
        
        if 'error' in result:
            continue
            
        total_original += result['original']
        total_deduped += result['deduped']
        
        # Track files with duplicates
        if result['status'] == 'Deduplicated':
            files_with_dupes += 1
        
        # Print progress
        if not verbose and ((i+1) % 25 == 0 or i == len(files) - 1):
            elapsed = time.time() - start_time
            files_per_second = (i + 1) / elapsed if elapsed > 0 else 0
            print(f'Processed {i+1}/{len(files)} files... ({files_per_second:.1f} files/sec)')
    
    # Sort results by reduction percentage for display
    sorted_results = sorted([r for r in results if r.get('status') == 'Deduplicated'], 
                           key=lambda x: x['reduction_percent'], 
                           reverse=True)
    
    # Print top files with highest duplication
    print('\nTop files with duplicates:')
    for result in sorted_results[:10]:  # Show top 10
        print(f"{result['file']}: {result['original']} → {result['deduped']} " 
              f"({result['reduction_percent']:.1f}% reduction)")
    
    # Calculate overall stats
    total_reduction = ((total_original - total_deduped) / total_original) * 100 if total_original > 0 else 0
    
    # Print overall stats
    print(f'\nOverall stats:')
    print(f'Total files processed: {len(files)}')
    print(f'Files with duplicates: {files_with_dupes}')
    print(f'Total original records: {total_original}')
    print(f'Total deduplicated records: {total_deduped}')
    print(f'Records removed: {total_original - total_deduped}')
    print(f'Overall reduction: {total_reduction:.1f}%')
    print(f'Deduplicated files saved to: {output_dir}')
    print(f'Total processing time: {time.time() - start_time:.1f} seconds')
    
    # Save detailed report
    save_report(results, report_file)
    
    return results

def main():
    """Main function to parse arguments and run the deduplication process."""
    parser = argparse.ArgumentParser(description='Deduplicate parquet files based on timestamp and article_title')
    parser.add_argument('--input', '-i', default='/app/data/output', 
                        help='Input directory containing parquet files')
    parser.add_argument('--output', '-o', default='/app/data/output/deduplicated', 
                        help='Output directory for deduplicated files')
    parser.add_argument('--report', '-r', default='/app/data/output/deduplication_report.json', 
                        help='Path to save the JSON report')
    parser.add_argument('--limit', '-l', type=int, default=0,
                        help='Limit the number of files to process (0 for all)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Reduce verbosity of output')
    parser.add_argument('--sort-by-size', '-s', action='store_true',
                        help='Sort files by size (process smaller files first)')
    
    args = parser.parse_args()
    
    print(f"Starting deduplication process...")
    print(f"Input directory: {args.input}")
    print(f"Output directory: {args.output}")
    print(f"Report file: {args.report}")
    if args.limit > 0:
        print(f"Processing limit: {args.limit} files")
    
    # Start batch processing
    batch_process(
        input_dir=args.input,
        output_dir=args.output,
        report_file=args.report,
        sort_by_size=args.sort_by_size,
        limit=args.limit,
        verbose=not args.quiet
    )

if __name__ == '__main__':
    main()