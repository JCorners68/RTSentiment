#!/usr/bin/env python3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Load the deduplicated file
deduped_path = '/app/data/output/aacr_deduped.parquet'
df = pq.read_table(deduped_path).to_pandas()

# Print summary info
print(f"Total rows in deduplicated file: {len(df)}")
print(f"Unique article titles: {df['article_title'].nunique()}")

# Print the first row
print("\nFirst row:")
print(df[['timestamp', 'ticker', 'article_id', 'article_title']].iloc[0])