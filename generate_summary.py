#!/usr/bin/env python3
import json
import pandas as pd

def generate_summary():
    # Load the full verification report
    report_file = '/app/data/output/full_verification.json'
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    # Extract summary statistics
    stats = {
        'summary': report['summary'],
        'most_duplicated': sorted(
            [f for f in report['files'] 
             if f.get('exists', False) and 'error' not in f and f.get('rows_removed', 0) > 0],
            key=lambda x: x.get('reduction_pct', 0),
            reverse=True
        )[:20]
    }
    
    # Save summary report
    summary_file = '/app/data/output/deduplication_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f'Saved summary to {summary_file}')
    
    # Print the summary
    print("\nDeduplication Summary:")
    print(f"Total files processed: {stats['summary']['total_files_processed']}")
    print(f"Total original records: {stats['summary']['total_original_records']}")
    print(f"Total deduplicated records: {stats['summary']['total_deduplicated_records']}")
    print(f"Total records removed: {stats['summary']['total_records_removed']}")
    print(f"Overall reduction: {stats['summary']['overall_reduction_percent']:.2f}%")
    
    print("\nTop 20 Most Duplicated Files:")
    for f in stats['most_duplicated']:
        print(f"{f['file']}: {f['original_rows']} → {f['deduped_rows']} ({f['reduction_pct']:.2f}% reduction)")
    
if __name__ == '__main__':
    generate_summary()