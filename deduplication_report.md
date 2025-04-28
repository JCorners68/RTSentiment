# Deduplication Report - WSL_RT_Sentiment

## Summary

This report summarizes the deduplication process of sentiment data in the WSL_RT_Sentiment project. The goal was to identify and remove duplicate entries, which were primarily articles with the same title appearing multiple times with different article IDs.

## Deduplication Results

The deduplication process was highly effective, yielding the following results:

- **Original data**: 31,497 total records across 519 files
- **Deduplicated data**: 998 total records (a 96.84% reduction)
- **Files with duplicates**: 437 out of 519 files (84.2%)
- **Unique tickers**: 441

### Latest Execution (April 25, 2025)

In the most recent run of the improved deduplication process:
- **Processed files**: 442 parquet files in `/data/output/ticker/`
- **Deduplicated data**: 1,248 total records
- **Files with duplicates**: No duplicates found in this run
- **Sentiment analysis**: All sentiment scores are 0, indicating a potential issue with sentiment calculation

## Most Deduplicated Files

Several files had extremely high duplication rates:

| File | Original Rows | Deduplicated Rows | Reduction (%) |
|------|---------------|-------------------|--------------|
| multi_ticker_sentiment.parquet | 16,679 | 173 | 98.96% |
| tesla_sentiment.parquet | 521 | 21 | 95.97% |
| market_sentiment.parquet | 475 | 18 | 96.21% |
| aapl_sentiment.parquet | 443 | 19 | 95.71% |
| tsla_sentiment.parquet | 387 | 17 | 95.61% |

## Tools and Process

### Steps Taken

1. **Initial Investigation**: Determined the original files had extensive duplicates with the same article title but different IDs.

2. **Tool Development**:
   - Created `deduplicate_aacr.py` to test on a single file
   - Created `deduplicate_all.py` to process all parquet files
   - Created `check_duplication.py` to verify results
   - Created `generate_summary.py` to produce final reports

3. **Deduplication Strategy**:
   - Removed duplicates based on matching `timestamp` and `article_title`
   - Kept the first occurrence of each unique record
   - Output deduplicated files to a new directory

4. **Verification**:
   - Original files in `/data/output/` had many duplicates
   - New files in `/data/output/fixed/` have all duplicates removed
   - Generated comprehensive JSON reports with detailed statistics

5. **Analysis**:
   - Analyzed the patterns of duplication across the dataset
   - Identified files with the highest duplication rates
   - Confirmed the effectiveness of the deduplication strategy

## Key Findings

- The largest file (multi_ticker_sentiment.parquet) had 98.96% duplication
- Nearly all ticker-specific files showed 90%+ duplication rates
- Duplication was consistent across the dataset, suggesting a systematic issue
- The data comes primarily from a single source: RedditScraper
- The date range covers 2025-02-01 to 2025-04-26

### New Findings (April 25, 2025)

- In the latest run, no duplicates were detected in the `/data/output/ticker/` directory files
- This suggests either:
  1. The data has already been deduplicated, or 
  2. This dataset was generated with duplication prevention mechanisms
- **Critical issue**: All sentiment scores in the current dataset are 0
- The combined deduplicated data has been saved to `/data/output/combined_recalculated/all_clean_sentiment.parquet`
- Analysis visualizations have been generated in `/tmp/clean_analysis/`

## Recommendations

1. **Data Pipeline Improvements**:
   - Implement deduplication as part of the data ingestion process
   - Add validation to prevent duplicate entries in new data
   - Set up monitoring to alert on unusual duplication patterns

2. **Data Quality Checks**:
   - Implement regular data quality checks to detect duplicates
   - Add integrity constraints at the database level
   - Create automated tests to verify data uniqueness

3. **Source Diversity**:
   - Investigate why the RedditScraper produces so many duplicates
   - Implement better source-specific deduplication logic
   - Consider adding additional data sources for robustness

4. **Sentiment Analysis Improvements** (New - April 25, 2025):
   - Investigate and fix the issue with all sentiment scores being 0
   - Recalculate sentiment using a properly functioning model
   - Implement data quality checks specifically for sentiment scores
   - Add sentiment validation to ensure scores are properly distributed

## Files Created

- **deduplicate_aacr.py**: Single file deduplication script
- **deduplicate_all.py**: Process all parquet files
- **check_duplication.py**: Verify deduplication results
- **generate_summary.py**: Create summary reports
- **/data/output/fixed/**: Directory containing all deduplicated files
- **/data/output/verification.json**: Detailed verification report
- **/data/output/full_verification.json**: Comprehensive report with statistics

### New Files (April 25, 2025)

- **deduplicate_parquet.py**: Enhanced deduplication script with improved path handling
- **combine_parquet.py**: Combines deduplicated files into a single dataset
- **analyze_clean_sentiment.py**: Generates analysis and visualizations for cleaned data
- **/data/output/deduplicated/**: Directory containing deduplicated files from latest run
- **/data/output/combined_recalculated/all_clean_sentiment.parquet**: Combined dataset
- **/tmp/clean_analysis/**: Analysis visualizations and CSV reports

## Conclusion

The deduplication process successfully removed duplicate entries, reducing the dataset by 96.84%. The multi_ticker_sentiment.parquet file alone was reduced from 16,679 rows to just 173 rows, demonstrating the severity of the duplication issue.

The high duplication rate indicates a significant data quality issue that should be addressed in the data collection and processing pipeline. By implementing the recommendations in this report, the project can prevent similar issues in the future and maintain higher data quality standards.

### Updated Conclusion (April 25, 2025)

The latest execution of the deduplication process found no duplicates in the current data, suggesting that previous deduplication efforts may have been successful or that the data generation process has been improved.

However, a critical issue was identified: all sentiment scores in the current dataset are 0. This indicates a fundamental problem with the sentiment analysis component of the data pipeline that requires immediate attention.

Future work should focus on:
1. Maintaining the deduplication mechanisms to prevent duplicates at the source
2. Fixing the sentiment analysis component to ensure accurate and meaningful sentiment scores
3. Establishing data quality checks for both duplication and sentiment score validation
4. Implementing a recalculation of sentiment scores for the existing cleaned data

By addressing these issues, the project can build a more reliable and insightful sentiment analysis system that provides accurate financial market intelligence.

## Sentiment Calculation Fix

During our investigation of the zero sentiment scores issue, we found that the system has a dedicated `recalculate_sentiment_finbert.py` utility in the `data_manager` directory. This utility is specifically designed to recalculate sentiment scores using the FinBERT model.

To fix the sentiment scores:

1. Run the recalculation utility targeting the deduplicated data:
   ```bash
   source venv/bin/activate
   cd data_manager
   python recalculate_sentiment_finbert.py ../data/output/combined_recalculated/all_clean_sentiment.parquet
   ```

2. Verify that the sentiment scores have been properly calculated
3. Re-run the analysis scripts on the recalculated data

This approach will address the sentiment calculation issue while maintaining the benefits of the deduplication process.