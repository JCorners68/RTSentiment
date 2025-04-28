# Sentiment Analysis Data Management Utilities

This directory contains utilities for managing, processing, and analyzing financial sentiment data stored in Parquet files.

## Utilities

### 1. Deduplication Utilities

#### Standard Deduplication (`dedup_utility.py`)
Removes duplicate entries from Parquet files based on specified columns.

```bash
# Basic usage
python dedup_utility.py /path/to/file.parquet --columns article_title

# Process entire directory
python dedup_utility.py /path/to/directory --output_path /path/to/output --columns article_title ticker

# Control which duplicates to keep (first, last, or none)
python dedup_utility.py /path/to/file.parquet --keep none
```

#### GPU-Accelerated Deduplication (`dedup_utility_rapids.py`)
Faster deduplication using RAPIDS cuDF when available, with automatic fallback to pandas.

```bash
# Basic usage (automatically uses GPU if available)
python dedup_utility_rapids.py /path/to/file.parquet --columns article_title

# Force CPU-only mode
python dedup_utility_rapids.py /path/to/directory --no_gpu
```

### 2. Sentiment Recalculation Utilities

#### FinBERT Sentiment Recalculation (`recalculate_sentiment_finbert.py`)
Recalculates sentiment scores using FinBERT, adding confidence scores and priority values.

```bash
# Process a file
python recalculate_sentiment_finbert.py /path/to/file.parquet

# Process a directory
python recalculate_sentiment_finbert.py /path/to/directory

# Specify output location
python recalculate_sentiment_finbert.py /path/to/directory --output_path /path/to/output

# Specify text column to analyze
python recalculate_sentiment_finbert.py /path/to/file.parquet --text_column content
```

#### GPU-Accelerated Sentiment Recalculation (`recalculate_sentiment_rapids.py`)
Faster sentiment recalculation using RAPIDS when available, with automatic fallback to pandas.

```bash
# Process a file (automatically uses GPU if available)
python recalculate_sentiment_rapids.py /path/to/file.parquet

# Force CPU-only mode
python recalculate_sentiment_rapids.py /path/to/directory --no_gpu
```

## Output Format

The sentiment recalculation utilities add or update these fields:

- `sentiment`: Score between -1 (negative) and 1 (positive)
- `sentiment_label`: Text label (positive, neutral, negative)
- `confidence`: Model confidence score (0.5-0.95)
- `priority`: Importance score calculated from sentiment strength and confidence
- `weighted_priority`: Same as priority (reserved for future weighting)

## GPU Acceleration

Both utilities automatically use GPU acceleration when RAPIDS libraries are available, providing:

- 5-10x faster parquet I/O
- Up to 50x faster deduplication for large datasets
- Vectorized sentiment scoring and priority calculation

To install RAPIDS (requires NVIDIA GPU):
```bash
# Using conda
conda install -c rapidsai -c conda-forge cudf=23.04 cuml=23.04 cupy python=3.9 cudatoolkit=11.8
```

If RAPIDS is not available, the utilities gracefully fall back to pandas/numpy.

## Implementation Notes

- Sentiment scores are generated using FinBERT (if available) or a mock implementation
- The mock implementation adds realistic variation in confidence and sentiment
- Priority values range from 0.1 to 10.0, calculated from sentiment strength and confidence
- All tools are designed to work with any parquet file in the output directory