#!/usr/bin/env python3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import json
import argparse
from datetime import datetime
import glob

def analyze_file(file_path, deduplicated_dir):
    """Analyze a parquet file and its deduplicated version."""
    file_name = os.path.basename(file_path)
    deduplicated_path = os.path.join(deduplicated_dir, file_name)
    
    # Skip if deduplicated file doesn't exist
    if not os.path.exists(deduplicated_path):
        return {
            'file': file_name,
            'error': 'Deduplicated version not found',
            'exists': False
        }
    
    try:
        # Read both files
        original_table = pq.read_table(file_path)
        deduped_table = pq.read_table(deduplicated_path)
        
        original_df = original_table.to_pandas()
        deduped_df = deduped_table.to_pandas()
        
        # Get stats
        original_rows = len(original_df)
        deduped_rows = len(deduped_df)
        original_unique_titles = original_df['article_title'].nunique()
        deduped_unique_titles = deduped_df['article_title'].nunique()
        
        # Calculate reduction
        rows_removed = original_rows - deduped_rows
        reduction_pct = (rows_removed / original_rows * 100) if original_rows > 0 else 0
        
        return {
            'file': file_name,
            'original_rows': original_rows,
            'deduped_rows': deduped_rows,
            'rows_removed': rows_removed,
            'reduction_pct': reduction_pct,
            'original_unique_titles': original_unique_titles,
            'deduped_unique_titles': deduped_unique_titles,
            'exists': True
        }
    except Exception as e:
        return {
            'file': file_name,
            'error': str(e),
            'exists': True
        }

def analyze_directory(input_dir, deduplicated_dir, limit=None, sort_by_size=True):
    """Analyze all parquet files in input directory and their deduplicated versions."""
    # Get list of parquet files
    files = glob.glob(f'{input_dir}/*.parquet')
    
    # Filter out files that are in subdirectories
    files = [f for f in files if os.path.dirname(f) == input_dir]
    
    # Sort by size if requested
    if sort_by_size:
        files.sort(key=os.path.getsize, reverse=True)  # Sort by largest first
    
    # Apply limit if specified
    if limit:
        files = files[:limit]
    
    print(f"Analyzing {len(files)} parquet files...")
    
    # Process each file
    results = []
    for i, file_path in enumerate(files):
        print(f"Processing {i+1}/{len(files)}: {os.path.basename(file_path)}")
        result = analyze_file(file_path, deduplicated_dir)
        results.append(result)
    
    # Generate report
    successful_results = [r for r in results if r.get('exists', False) and 'error' not in r]
    
    if not successful_results:
        print("No successfully analyzed files found.")
        return results
    
    # Print summary statistics
    total_original = sum(r.get('original_rows', 0) for r in successful_results)
    total_deduped = sum(r.get('deduped_rows', 0) for r in successful_results)
    total_removed = sum(r.get('rows_removed', 0) for r in successful_results)
    overall_reduction = (total_removed / total_original * 100) if total_original > 0 else 0
    
    print("\nSummary Statistics:")
    print(f"Total files processed: {len(successful_results)}")
    print(f"Total original records: {total_original}")
    print(f"Total deduplicated records: {total_deduped}")
    print(f"Total records removed: {total_removed}")
    print(f"Overall reduction: {overall_reduction:.2f}%")
    
    # Print top 10 files by reduction percentage
    print("\nTop 10 files by reduction percentage:")
    for r in sorted(successful_results, key=lambda x: x.get('reduction_pct', 0), reverse=True)[:10]:
        print(f"{r['file']}: {r['original_rows']} → {r['deduped_rows']} ({r['reduction_pct']:.2f}% reduction)")
    
    return results

def save_report(results, output_file):
    """Save results to a JSON file."""
    # Calculate summary statistics
    successful_results = [r for r in results if r.get('exists', False) and 'error' not in r]
    
    total_original = sum(r.get('original_rows', 0) for r in successful_results)
    total_deduped = sum(r.get('deduped_rows', 0) for r in successful_results)
    total_removed = sum(r.get('rows_removed', 0) for r in successful_results)
    overall_reduction = (total_removed / total_original * 100) if total_original > 0 else 0
    
    # Create report
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total_files_processed': len(successful_results),
            'total_original_records': total_original,
            'total_deduplicated_records': total_deduped,
            'total_records_removed': total_removed,
            'overall_reduction_percent': overall_reduction
        },
        'files': results
    }
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Detailed report saved to: {output_file}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Check and report on parquet deduplication results')
    parser.add_argument('--input', '-i', default='/app/data/output',
                        help='Input directory containing original parquet files')
    parser.add_argument('--deduplicated', '-d', default='/app/data/output/deduplicated',
                        help='Directory containing deduplicated parquet files')
    parser.add_argument('--report', '-r', default='/app/data/output/deduplication_verification.json',
                        help='Path to save the JSON report')
    parser.add_argument('--limit', '-l', type=int, default=None,
                        help='Limit the number of files to process')
    parser.add_argument('--sort-by-size', '-s', action='store_true',
                        help='Sort files by size (largest first)')
    
    args = parser.parse_args()
    
    print(f"Starting deduplication verification...")
    print(f"Input directory: {args.input}")
    print(f"Deduplicated directory: {args.deduplicated}")
    print(f"Report file: {args.report}")
    
    # Run analysis
    results = analyze_directory(
        args.input, 
        args.deduplicated, 
        args.limit, 
        args.sort_by_size
    )
    
    # Save report
    save_report(results, args.report)

if __name__ == '__main__':
    main()