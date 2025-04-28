# Real vs. Simulated Data

## Definitions

### Real Data
Real data refers to data collected from legitimate internet sources. This includes:
- News articles scraped from financial news websites
- Reddit posts from financial subreddits
- Twitter/X posts (if implemented)
- SEC filings and announcements

Real data is essential for accurate sentiment analysis as it represents actual market sentiment. It is stored in:
```
/data/output/real/           # Processed real data in Parquet format
/data/cache/real_data/       # Cached real data in JSON format
```

### Simulated Data
Simulated data refers to artificially generated data that mimics the structure of real data but does not contain genuine content. This includes:
- Test data with placeholder content
- Training data with synthetic examples
- Development samples for testing system functionality

Simulated data is only used for testing and development purposes and should never be used for production sentiment analysis. It is stored in:
```
/data_sim/output/            # Processed simulated data in Parquet format
/data_sim/cache/             # Cached simulated data in JSON format
```

## User Preferences

**IMPORTANT**: By default, only real data should be used in production workflows. Simulated data is strictly for development and testing purposes.

The user prefers:
- Only real data from actual internet sources for sentiment analysis
- No simulated/fake data in production pipelines
- Clear separation between real and simulated data in the file system

Simulated data should only be used when:
- Explicitly requested by the user
- During initial development before real data sources are available
- For unit testing where controlled data is required

All scrapers should be configured to collect genuine data from authorized sources, following appropriate rate limits and terms of service.

## Implementation Notes

The system ensures a clean separation between real and simulated data through:
1. Separate directory structures for real vs. simulated data
2. Clear logging to indicate which data source is being used
3. Configuration flags to explicitly enable simulated data when needed

Metrics and dashboards should clearly indicate when simulated data is being used to prevent confusion.