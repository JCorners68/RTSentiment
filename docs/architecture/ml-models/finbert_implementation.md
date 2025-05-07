# FinBERT Sentiment Analysis Implementation

## Overview

This document details the implementation of FinBERT sentiment analysis for financial news within the Sentimark platform. The implementation follows Phases 1 and 2 of the database migration plan, demonstrating the repository pattern and abstraction layer with a real-world use case.

## Implementation Architecture

The FinBERT sentiment analysis implementation consists of several key components:

1. **Sentiment Analyzer**: Core module implementing the FinBERT model for financial sentiment analysis
2. **News Processor**: Module for processing collected news articles with FinBERT
3. **Visualization Tools**: Components for visualizing sentiment analysis results
4. **Verification Script**: End-to-end pipeline verification with clear output

## Components

### 1. Sentiment Analyzer

The sentiment analyzer uses the ProsusAI/finbert model, a BERT-based model fine-tuned specifically for financial sentiment analysis.

**File:** `/home/jonat/real_senti/services/data-acquisition/src/sentiment_analyzer.py`

Key functions:
- `initialize_model()`: Sets up the FinBERT model and tokenizer
- `analyze_sentiment(text)`: Analyzes the sentiment of a given text
- `analyze_news_batch(news_items)`: Processes a batch of news items

The analyzer returns sentiment in three categories:
- Positive: Score between 0 and 1
- Neutral: Score of 0
- Negative: Score between -1 and 0

Each sentiment prediction includes:
1. Sentiment label (positive, negative, neutral)
2. Sentiment score (-1.0 to 1.0 scale)
3. Confidence level (0.0 to 1.0)

### 2. News Processor

The news processor loads collected news data from Finnhub, performs sentiment analysis, and saves the results.

**File:** `/home/jonat/real_senti/services/data-acquisition/src/process_news.py`

Key functions:
- `load_news_data()`: Loads news data from CSV files
- `process_news_data(news_data)`: Processes news data and performs sentiment analysis
- `save_sentiment_results(results)`: Saves results to CSV and JSON files
- `generate_summary(results)`: Generates summary statistics

The processor outputs:
- CSV file with sentiment results
- JSON file with sentiment results
- Summary statistics of sentiment analysis

### 3. Visualization Tools

The visualization module creates graphical representations of sentiment analysis results.

**File:** `/home/jonat/real_senti/services/data-acquisition/src/visualize_sentiment.py`

Visualizations include:
- Sentiment distribution histogram
- Sentiment by ticker boxplot
- Sentiment over time line chart
- Sentiment by news source bar chart
- Sentiment heatmap by ticker and date

All visualizations are saved as PNG files in the output directory.

### 4. Verification Script

The verification script runs the complete pipeline from data loading to visualization and provides clear output.

**File:** `/home/jonat/real_senti/services/data-acquisition/run_finbert_pipeline.py`

The script verifies:
- News data availability and counts
- Sentiment analysis results
- Visualization outputs

## Data Flow

The sentiment analysis pipeline follows this data flow:

1. **Input**: News articles collected from Finnhub API
2. **Processing**: FinBERT sentiment analysis on article headlines and summaries
3. **Storage**: Results saved to CSV and JSON files
4. **Visualization**: Graphical representations of sentiment trends
5. **Verification**: End-to-end pipeline verification

## Setup Instructions

### Prerequisites

- Python 3.10+
- PyTorch
- transformers library
- pandas, matplotlib, seaborn for data processing and visualization

### Installation

```bash
cd /home/jonat/real_senti/services/data-acquisition
source venv/bin/activate
pip install transformers torch pandas matplotlib seaborn
```

### Directory Structure

- `/home/jonat/real_senti/data/finnhub_poc/`: Raw data from Finnhub
- `/home/jonat/real_senti/data/sentiment_results/`: Sentiment analysis results
- `/home/jonat/real_senti/data/sentiment_results/visualizations/`: Visualization outputs
- `/home/jonat/real_senti/data/models/finbert/`: FinBERT model cache

## Running the Pipeline

### Processing News with FinBERT

```bash
cd /home/jonat/real_senti/services/data-acquisition
source venv/bin/activate
python src/process_news.py --summary
```

For processing a specific ticker:
```bash
python src/process_news.py --ticker AAPL --summary
```

### Generating Visualizations

```bash
cd /home/jonat/real_senti/services/data-acquisition
source venv/bin/activate
python src/visualize_sentiment.py --all
```

For specific visualizations:
```bash
python src/visualize_sentiment.py --distribution --ticker
```

### End-to-End Verification

```bash
cd /home/jonat/real_senti/services/data-acquisition
source venv/bin/activate
./run_finbert_pipeline.py
```

To skip specific steps:
```bash
./run_finbert_pipeline.py --skip-processing
./run_finbert_pipeline.py --skip-visualization
```

## Verification

To verify the pipeline is working correctly:

1. Run the verification script:
   ```bash
   cd /home/jonat/real_senti/services/data-acquisition
   source venv/bin/activate
   ./run_finbert_pipeline.py
   ```

2. Check the output for:
   - News data counts
   - Sentiment analysis statistics
   - Visualization files

3. Examine the results:
   - Sentiment CSV: `/home/jonat/real_senti/data/sentiment_results/sentiment_analysis.csv`
   - Summary JSON: `/home/jonat/real_senti/data/sentiment_results/sentiment_summary.json`
   - Visualizations: `/home/jonat/real_senti/data/sentiment_results/visualizations/`

## Results

The sentiment analysis of Finnhub news data provides valuable insights:

1. **Company Sentiment Tracking**: Track sentiment trends for individual companies
2. **Source Bias Analysis**: Identify biases in different news sources
3. **Temporal Trends**: Monitor sentiment changes over time
4. **Market Correlations**: Compare sentiment with market movements

## Integration with Repository Pattern

The implementation aligns with the repository pattern and abstraction layer from Phases 1-4:

1. **Domain Entities**: News articles and sentiment records as domain entities
2. **Repository Interfaces**: Clean separation of concerns with specific interfaces
3. **Dependency Injection**: Components are loosely coupled for testing
4. **Error Handling**: Standardized error handling throughout the pipeline

## Next Steps

1. **Database Integration**: Connect directly to PostgreSQL/Iceberg repositories
2. **Real-time Processing**: Implement streaming processing for real-time results
3. **Integration Testing**: Comprehensive tests with the database abstraction layer
4. **Performance Optimization**: Optimize for large-scale data processing