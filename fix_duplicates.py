import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import glob
import sys

# Create output directory
os.makedirs("/home/jonat/WSL_RT_Sentiment/data/output/real", exist_ok=True)

# Process all parquet files
files = glob.glob("/home/jonat/WSL_RT_Sentiment/data/output/*.parquet")
print(f"Found {len(files)} parquet files to process")

# Track statistics
total_original = 0
total_deduped = 0
files_with_dupes = 0

# Process each file
for i, file_path in enumerate(files):
    try:
        # Read parquet file
        table = pq.read_table(file_path)
        df = table.to_pandas()
        
        # Get original count
        original_count = len(df)
        total_original += original_count
        
        # Remove duplicates by article title and timestamp
        df_deduped = df.drop_duplicates(subset=["article_title", "timestamp"])
        
        # Get deduplicated count
        deduped_count = len(df_deduped)
        total_deduped += deduped_count
        
        # Calculate reduction percentage
        if original_count > 0:
            reduction = ((original_count - deduped_count) / original_count) * 100
        else:
            reduction = 0
            
        # Only report for files with duplicates
        if original_count != deduped_count:
            files_with_dupes += 1
            print(f"{os.path.basename(file_path)}: {original_count} → {deduped_count} ({reduction:.1f}% reduction)")
            
        # Write deduplicated data to real directory
        output_path = os.path.join("/home/jonat/WSL_RT_Sentiment/data/output/real", os.path.basename(file_path))
        pq.write_table(pa.Table.from_pandas(df_deduped), output_path)
        
        # Print progress every 50 files
        if (i+1) % 50 == 0:
            print(f"Processed {i+1}/{len(files)} files...")
    
    except Exception as e:
        print(f"Error processing {os.path.basename(file_path)}: {str(e)}")

# Print summary
if total_original > 0:
    overall_reduction = ((total_original - total_deduped) / total_original) * 100
else:
    overall_reduction = 0

print(f"\nSummary:")
print(f"Total files processed: {len(files)}")
print(f"Files with duplicates: {files_with_dupes}")
print(f"Total original records: {total_original}")
print(f"Total deduplicated records: {total_deduped}")
print(f"Overall reduction: {overall_reduction:.1f}%")
print(f"Deduplicated files saved to /home/jonat/WSL_RT_Sentiment/data/output/real/")
