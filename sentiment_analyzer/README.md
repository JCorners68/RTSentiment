# Ticker Sentiment Analyzer

Real-time sentiment analysis for top S&P 500 tickers with data visualization.

## Features

- Continuous sentiment tracking for top 10 S&P 500 tickers
- Time decay to prioritize recent data
- Impact scoring based on source credibility and engagement
- Redis caching for fast updates
- Interactive visualization dashboard

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Redis connection in config.json

## Usage

### Start the service:
```bash
python main.py --config config.json
```

### Run the dashboard:
```bash
cd sentiment_analyzer
streamlit run ui/app.py
```