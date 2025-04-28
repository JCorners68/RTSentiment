# Deduplication Scripts Documentation

This document provides detailed information about the scripts developed for the deduplication process in the WSL_RT_Sentiment project.

## Overview

The following scripts were created to identify, remove, and analyze duplicate entries in the sentiment data:

1. `deduplicate_aacr.py` - Initial prototype for single file deduplication
2. `deduplicate_all.py` - Production script to process all parquet files
3. `check_duplication.py` - Verification tool for deduplication results
4. `generate_summary.py` - Tool to create statistical reports

## Script Details

### 1. deduplicate_aacr.py

A prototype script for deduplicating a single parquet file.

#### Key Functions:

```python
def deduplicate_single_file(file_path, output_path):
    """Deduplicate a single parquet file based on timestamp and article_title."""
    print(f"Processing file: {file_path}")
    try:
        # Read the parquet file
        table = pq.read_table(file_path)
        df = table.to_pandas()
        
        # Print file info before deduplication
        original_count = len(df)
        unique_titles = df['article_title'].nunique()
        print(f"Original rows: {original_count}")
        print(f"Unique article titles: {unique_titles}")
        
        # Deduplicate based on timestamp and article_title
        df_deduped = df.drop_duplicates(subset=['timestamp', 'article_title'], keep='first')
        
        # Print file info after deduplication
        deduped_count = len(df_deduped)
        print(f"Deduplicated rows: {deduped_count}")
        print(f"Reduction: {original_count - deduped_count} rows ({(original_count - deduped_count) / original_count * 100:.2f}%)")
        
        # Write the deduplicated data to output
        table_deduped = pa.Table.from_pandas(df_deduped)
        pq.write_table(table_deduped, output_path)
        print(f"Deduplicated data written to {output_path}")
    except Exception as e:
        print(f"Error: {e}")
```

#### Usage:

```
python deduplicate_aacr.py
```

### 2. deduplicate_all.py

Production script to deduplicate all parquet files in the dataset.

#### Key Functions:

```python
def deduplicate_parquet(file_path, output_dir):
    """Deduplicate a parquet file based on timestamp and article_title."""
    try:
        # Extract ticker name from filename
        ticker = os.path.basename(file_path).split('_')[0]
        output_path = os.path.join(output_dir, f"{ticker}_sentiment.parquet")
        
        # Read the parquet file
        table = pq.read_table(file_path)
        df = table.to_pandas()
        
        # Get original stats
        original_count = len(df)
        unique_titles = df['article_title'].nunique()
        
        # Only process if duplicates exist
        if unique_titles < original_count:
            # Drop duplicates based on timestamp and article_title
            df_deduped = df.drop_duplicates(subset=['timestamp', 'article_title'], keep='first')
            deduped_count = len(df_deduped)
            
            # Calculate reduction
            rows_removed = original_count - deduped_count
            reduction_percent = (rows_removed / original_count) * 100
            
            # Create stats
            stats = {
                'file': os.path.basename(file_path),
                'original_count': original_count,
                'deduped_count': deduped_count,
                'unique_titles': unique_titles,
                'rows_removed': rows_removed,
                'reduction_percent': reduction_percent
            }
            
            # Write the deduplicated data to output
            table_deduped = pa.Table.from_pandas(df_deduped)
            pq.write_table(table_deduped, output_path)
            
            return stats
        else:
            # No duplicates found
            return {
                'file': os.path.basename(file_path),
                'original_count': original_count,
                'deduped_count': original_count,
                'unique_titles': unique_titles,
                'rows_removed': 0,
                'reduction_percent': 0
            }
    except Exception as e:
        return {
            'file': os.path.basename(file_path),
            'error': str(e)
        }

def process_all_files(input_dir, output_dir):
    """Process all parquet files in the input directory."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all parquet files
    files = glob.glob(os.path.join(input_dir, '*_sentiment.parquet'))
    total_files = len(files)
    
    print(f"Found {total_files} parquet files to process")
    
    # Process each file
    results = []
    for i, file_path in enumerate(files, 1):
        print(f"Processing file {i}/{total_files}: {os.path.basename(file_path)}")
        result = deduplicate_parquet(file_path, output_dir)
        results.append(result)
        
    return results
```

#### Usage:

```
python deduplicate_all.py
```

### 3. check_duplication.py

Verification script to analyze the results of the deduplication process.

#### Key Functions:

```python
def analyze_file(file_path, deduplicated_dir):
    """Analyze a parquet file and its deduplicated version."""
    file_name = os.path.basename(file_path)
    deduplicated_path = os.path.join(deduplicated_dir, file_name)
    
    if not os.path.exists(deduplicated_path):
        return {
            'file': file_name,
            'exists': False,
            'error': 'Deduplicated file does not exist'
        }
    
    try:
        # Read both files
        original_table = pq.read_table(file_path)
        deduped_table = pq.read_table(deduplicated_path)
        
        original_df = original_table.to_pandas()
        deduped_df = deduped_table.to_pandas()
        
        # Calculate stats
        original_rows = len(original_df)
        deduped_rows = len(deduped_df)
        original_unique_titles = original_df['article_title'].nunique()
        deduped_unique_titles = deduped_df['article_title'].nunique()
        
        # Calculate reduction
        rows_removed = original_rows - deduped_rows
        if original_rows > 0:
            reduction_pct = (rows_removed / original_rows * 100)
        else:
            reduction_pct = 0
        
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
            'exists': True,
            'error': str(e)
        }

def generate_verification_report(original_dir, deduplicated_dir, output_file):
    """Generate a verification report for all files."""
    files = glob.glob(os.path.join(original_dir, '*_sentiment.parquet'))
    total_files = len(files)
    
    print(f"Analyzing {total_files} files")
    
    results = []
    total_original = 0
    total_deduped = 0
    total_removed = 0
    
    for i, file_path in enumerate(files, 1):
        print(f"Analyzing file {i}/{total_files}: {os.path.basename(file_path)}")
        result = analyze_file(file_path, deduplicated_dir)
        results.append(result)
        
        if result.get('exists', False) and 'error' not in result:
            total_original += result.get('original_rows', 0)
            total_deduped += result.get('deduped_rows', 0)
            total_removed += result.get('rows_removed', 0)
    
    if total_original > 0:
        overall_reduction_pct = (total_removed / total_original * 100)
    else:
        overall_reduction_pct = 0
    
    report = {
        'summary': {
            'total_files': total_files,
            'total_original_rows': total_original,
            'total_deduped_rows': total_deduped,
            'total_rows_removed': total_removed,
            'overall_reduction_pct': overall_reduction_pct
        },
        'files': results
    }
    
    # Write report to file
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Verification report written to {output_file}")
    print(f"Summary: {total_original} original rows, {total_deduped} deduplicated rows")
    print(f"Removed {total_removed} duplicates ({overall_reduction_pct:.2f}% reduction)")
    
    return report
```

#### Usage:

```
python check_duplication.py
```

### 4. generate_summary.py

Script to generate a comprehensive summary of the deduplication results.

#### Key Functions:

```python
def generate_summary():
    """Generate a summary report of the deduplication results."""
    # Load the full verification report
    report_file = '/app/data/output/full_verification.json'
    
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    # Extract summary statistics
    summary = report['summary']
    
    # Extract most deduplicated files
    most_deduplicated = sorted(
        [f for f in report['files'] if f.get('exists', False) and 'error' not in f and f.get('rows_removed', 0) > 0],
        key=lambda x: x.get('reduction_pct', 0),
        reverse=True
    )[:20]
    
    # Format the summary
    formatted_summary = f"""# Deduplication Summary

## Overall Statistics

- Total files: {summary['total_files']}
- Total original rows: {summary['total_original_rows']}
- Total deduplicated rows: {summary['total_deduped_rows']}
- Total rows removed: {summary['total_rows_removed']}
- Overall reduction: {summary['overall_reduction_pct']:.2f}%

## Most Deduplicated Files

| File | Original Rows | Deduplicated Rows | Reduction (%) |
|------|---------------|-------------------|--------------|
"""
    
    # Add most deduplicated files to the summary
    for file in most_deduplicated:
        formatted_summary += f"| {file['file']} | {file['original_rows']} | {file['deduped_rows']} | {file['reduction_pct']:.2f}% |\n"
    
    # Write the summary to a file
    summary_file = '/app/data/output/deduplication_summary.md'
    with open(summary_file, 'w') as f:
        f.write(formatted_summary)
    
    print(f"Summary report written to {summary_file}")
    
    return formatted_summary
```

#### Usage:

```
python generate_summary.py
```

## Docker Integration

All scripts were designed to run within the Docker environment, with appropriate paths configured for the container file system:

```
docker-compose exec api python /app/deduplicate_all.py
docker-compose exec api python /app/check_duplication.py
docker-compose exec api python /app/generate_summary.py
```

## Generated Reports

The deduplication process generated several reports:

1. `/data/output/verification.json` - Initial verification report
2. `/data/output/full_verification.json` - Comprehensive verification report with detailed statistics
3. `/data/output/deduplication_summary.md` - Markdown summary of deduplication results
4. `/deduplication_report.md` - Final report summarizing the entire process

## Results Summary

The deduplication process successfully identified and removed duplicates from all parquet files:

- **Original data**: 31,497 total records across 519 files
- **Deduplicated data**: 998 total records (a 96.84% reduction)
- The file with the highest duplication rate was `multi_ticker_sentiment.parquet` (98.96% duplication)

## Next Steps

For preventing future duplication issues, refer to the companion document `Documentation/deduplication_integration_guide.md`, which provides guidance on integrating deduplication directly into the data acquisition pipeline.