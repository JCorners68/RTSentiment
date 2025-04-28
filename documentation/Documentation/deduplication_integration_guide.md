# Deduplication Integration Guide

This document provides technical guidance for integrating deduplication into the WSL_RT_Sentiment data acquisition pipeline to prevent future duplication issues.

## Overview

Based on the findings from our deduplication effort, approximately 96.84% of the data consisted of duplicates. This guide outlines how to implement prevention measures at various stages of the data pipeline.

## Integration Points

### 1. Scraper Level Integration

The duplication appears to originate in the data collection process, particularly in the RedditScraper. Implement these changes in the scraper modules:

```python
# In data_acquisition/scrapers/base.py

class BaseScraper:
    def __init__(self):
        # Add a deduplication cache
        self.seen_articles = set()
        self.cache_manager = CacheManager()
        
    def is_duplicate(self, timestamp, article_title):
        """Check if an article is a duplicate based on timestamp and title."""
        key = f"{timestamp}_{article_title}"
        if key in self.seen_articles:
            return True
        
        # Also check persistent cache
        if self.cache_manager.exists(key):
            return True
            
        # Not a duplicate, add to cache
        self.seen_articles.add(key)
        self.cache_manager.add(key)
        return False
        
    def process_article(self, article):
        """Process an article with deduplication."""
        if self.is_duplicate(article['timestamp'], article['article_title']):
            # Skip duplicates
            return None
        
        # Process the non-duplicate article
        return article
```

### 2. Cache Manager Implementation

Create a persistent cache to track seen articles across scraper runs:

```python
# In data_acquisition/utils/cache_manager.py

import json
import os
import hashlib

class CacheManager:
    def __init__(self, cache_dir='/app/data/cache/deduplication'):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize source-specific caches
        self.cache_files = {
            'news': os.path.join(self.cache_dir, 'news_hashes.json'),
            'reddit': os.path.join(self.cache_dir, 'reddit_hashes.json')
        }
        
        # Load existing caches
        self.caches = {}
        for source, file_path in self.cache_files.items():
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    self.caches[source] = set(json.load(f))
            else:
                self.caches[source] = set()
    
    def _get_hash(self, key):
        """Generate a hash for a key to save space."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def exists(self, key, source='reddit'):
        """Check if a key exists in the cache."""
        return self._get_hash(key) in self.caches.get(source, set())
    
    def add(self, key, source='reddit'):
        """Add a key to the cache."""
        if source not in self.caches:
            self.caches[source] = set()
        
        self.caches[source].add(self._get_hash(key))
        self._save_cache(source)
    
    def _save_cache(self, source):
        """Save the cache to disk."""
        with open(self.cache_files[source], 'w') as f:
            json.dump(list(self.caches[source]), f)
```

### 3. Data Processing Pipeline

Modify the data processing function in `data_acquisition/main.py`:

```python
def process_scraped_data(data, ticker=None):
    """Process scraped data with deduplication."""
    # Convert to DataFrame for easier processing
    df = pd.DataFrame(data)
    
    if not df.empty:
        # Check for duplicates within this batch
        df_deduped = df.drop_duplicates(subset=['timestamp', 'article_title'], keep='first')
        
        # Log duplicate count
        dupes_found = len(df) - len(df_deduped)
        if dupes_found > 0:
            logger.warning(f"Found {dupes_found} duplicates in batch for ticker {ticker}")
        
        # Continue with the deduplicated data
        return df_deduped.to_dict('records')
    
    return data
```

### 4. Parquet Output Integration

Add deduplication checks before writing to parquet:

```python
# In data_acquisition/main.py or relevant file

def write_to_parquet(data, ticker):
    """Write data to parquet with deduplication."""
    output_file = f"/app/data/output/{ticker}_sentiment.parquet"
    
    # Convert to DataFrame
    new_df = pd.DataFrame(data)
    
    # Check if file exists
    if os.path.exists(output_file):
        # Read existing data
        existing_table = pq.read_table(output_file)
        existing_df = existing_table.to_pandas()
        
        # Combine with new data
        combined_df = pd.concat([existing_df, new_df])
        
        # Deduplicate the combined data
        deduplicated_df = combined_df.drop_duplicates(
            subset=['timestamp', 'article_title'], 
            keep='first'
        )
        
        # Log deduplication stats
        dupes_removed = len(combined_df) - len(deduplicated_df)
        if dupes_removed > 0:
            logger.info(f"Removed {dupes_removed} duplicates when writing to {ticker}_sentiment.parquet")
        
        # Write deduplicated data
        table = pa.Table.from_pandas(deduplicated_df)
        pq.write_table(table, output_file)
    else:
        # No existing file, just write new data (already deduplicated above)
        table = pa.Table.from_pandas(new_df)
        pq.write_table(table, output_file)
```

## Monitoring Deduplication

Add metrics to track deduplication rates:

```python
# In data_acquisition/metrics.py

# Add deduplication metrics
DEDUPLICATION_COUNTER = Counter(
    'sentiment_deduplication_total', 
    'Number of duplicate articles detected and removed',
    ['source', 'ticker']
)

DEDUPLICATION_RATIO = Gauge(
    'sentiment_deduplication_ratio',
    'Ratio of duplicates to total articles',
    ['source', 'ticker']
)

# Update these metrics in the relevant processing functions:
def update_deduplication_metrics(source, ticker, total_count, duplicate_count):
    """Update deduplication metrics."""
    DEDUPLICATION_COUNTER.labels(source=source, ticker=ticker).inc(duplicate_count)
    
    if total_count > 0:
        ratio = duplicate_count / total_count
        DEDUPLICATION_RATIO.labels(source=source, ticker=ticker).set(ratio)
```

## Testing the Deduplication

Create a test script to verify the deduplication is working:

```python
# tests/test_deduplication.py

import pytest
from data_acquisition.utils.cache_manager import CacheManager
from data_acquisition.scrapers.base import BaseScraper

def test_duplicate_detection():
    """Test that duplicates are correctly detected."""
    scraper = BaseScraper()
    
    # First article should not be a duplicate
    assert not scraper.is_duplicate("2025-01-01", "Test Article")
    
    # Same article should now be detected as a duplicate
    assert scraper.is_duplicate("2025-01-01", "Test Article")
    
    # Different article should not be a duplicate
    assert not scraper.is_duplicate("2025-01-01", "Different Article")
    
    # Different timestamp but same title should not be a duplicate
    # (this is a design decision, could be changed)
    assert not scraper.is_duplicate("2025-01-02", "Test Article")

def test_cache_persistence():
    """Test that the cache persists between instances."""
    cache = CacheManager()
    
    # Add a test key
    test_key = "test_timestamp_test_title"
    cache.add(test_key)
    
    # Create a new instance
    new_cache = CacheManager()
    
    # Key should still exist
    assert new_cache.exists(test_key)
```

## Implementation Checklist

1. [ ] Add `CacheManager` class to `data_acquisition/utils/cache_manager.py`
2. [ ] Update `BaseScraper` in `data_acquisition/scrapers/base.py`
3. [ ] Modify data processing in `data_acquisition/main.py`
4. [ ] Add deduplication metrics to `data_acquisition/metrics.py`
5. [ ] Create tests in `tests/test_deduplication.py`
6. [ ] Update Docker configuration to persist cache volumes
7. [ ] Add documentation about deduplication to README

## Docker Configuration Updates

Update `docker-compose.yml` to persist the deduplication cache:

```yaml
services:
  data_acquisition:
    # Existing configuration...
    volumes:
      - ./data:/app/data
      - ./data/cache/deduplication:/app/data/cache/deduplication
```

## Conclusion

By implementing deduplication at multiple levels of the data pipeline, we can prevent the accumulation of duplicate data that previously affected 96.84% of our dataset. The approach uses both in-memory and persistent caching to ensure duplicates are caught both within batches and across multiple runs.

Regular monitoring of the deduplication metrics will help identify any issues with the data sources or scraping processes that might be causing systematic duplication.