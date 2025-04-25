# Parquet Query Viewer Web UI

A web-based interface for exploring financial sentiment data stored in Parquet files, built with Streamlit.

## Features

- Interactive query builder
- Real-time data visualization
- Sentiment trend analysis
- Source and ticker comparisons
- Pre-configured dashboard views
- Data export capabilities

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure you have a directory containing Parquet files with sentiment data.

## Usage

### Interactive Query Interface

Run the interactive query application:

```bash
streamlit run app.py
```

This provides a web-based interface for exploring and analyzing sentiment data with:
- Custom date range filtering
- Ticker and source selection
- Sentiment range filtering
- Text search
- Multiple visualization options

### Dashboard View

Run the pre-configured dashboard:

```bash
streamlit run dashboard.py
```

This displays key metrics and visualizations for monitoring sentiment trends:
- Overview metrics
- Sentiment trend charts
- Source and ticker breakdowns
- Sentiment distribution analysis
- Recent data display

## Directory Structure

- `app.py`: Main Streamlit application for interactive queries
- `dashboard.py`: Pre-configured dashboard application
- `requirements.txt`: Python dependencies

## Configuration

Both applications automatically detect available tickers and sources from your Parquet files.
You can configure the data path through the UI or by setting the `SENTIMENT_DATA_PATH` environment variable.

## Data Format

The web UI expects Parquet files with the following schema:
- `timestamp`: Date and time of the sentiment record
- `ticker`: Stock ticker symbol
- `sentiment`: Sentiment score (-1 to 1)
- `source`: Source of the sentiment data (e.g., news, reddit, twitter)
- `text`: (Optional) Text content related to the sentiment

## Screenshots

### Interactive Query Interface
![Interactive Query Interface](screenshots/query_interface.png)

### Dashboard View
![Dashboard View](screenshots/dashboard_view.png)