import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import os
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentiment_analyzer.data.redis_manager import RedisSentimentCache
from sentiment_analyzer.data.sp500_tracker import SP500Tracker
from sentiment_analyzer.models.sentiment_model import SentimentModel
from sentiment_analyzer.data.parquet_reader import ParquetReader

# Set page config
st.set_page_config(
    page_title="Ticker Sentiment Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def init_components():
    redis_cache = RedisSentimentCache(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=int(os.environ.get("REDIS_DB", 0))
    )
    
    sp500_tracker = SP500Tracker(
        update_interval_hours=4,  # Update every 4 hours
        top_n=10
    )
    
    sentiment_model = SentimentModel(
        redis_cache=redis_cache,
        decay_type=os.environ.get("DECAY_TYPE", "exponential"),
        decay_half_life=int(os.environ.get("DECAY_HALF_LIFE", 24)),
        max_age_hours=int(os.environ.get("MAX_AGE_HOURS", 168))
    )
    
    parquet_reader = ParquetReader(
        data_dir=os.environ.get("PARQUET_DIR", "/home/jonat/WSL_RT_Sentiment/data/output")
    )
    
    return redis_cache, sp500_tracker, sentiment_model, parquet_reader

redis_cache, sp500_tracker, sentiment_model, parquet_reader = init_components()

# Sidebar for configuration
st.sidebar.title("Configuration")

# Decay type selection
decay_type = st.sidebar.selectbox(
    "Sentiment Decay Function",
    ["exponential", "linear", "half_life"],
    index=0
)

# Half-life setting
decay_half_life = st.sidebar.slider(
    "Decay Half-Life (hours)",
    min_value=1,
    max_value=72,
    value=24,
    step=1
)

# Max age setting
max_age_hours = st.sidebar.slider(
    "Maximum Event Age (hours)",
    min_value=24,
    max_value=336,
    value=168,
    step=24
)

# Update sentiment model settings
sentiment_model.decay_type = decay_type
sentiment_model.decay_half_life = decay_half_life
sentiment_model.max_age_hours = max_age_hours

# Get top tickers
top_tickers = sp500_tracker.get_top_tickers()

# Function to get sentiment scores for tickers
def get_sentiment_data():
    sentiment_scores = {}
    
    for ticker in top_tickers:
        score = redis_cache.get_ticker_score(ticker)
        
        if score is None:
            # Calculate score if not in cache
            score = sentiment_model.calculate_sentiment_score(ticker)
            redis_cache.update_ticker_score(ticker, score)
            
        sentiment_scores[ticker] = score
        
    return sentiment_scores

# Main page content
st.title("Real-Time Ticker Sentiment Analysis")

# Top section - metrics and heatmap
st.header("Current Sentiment for Top S&P 500 Tickers")

col1, col2 = st.columns([2, 3])

with col1:
    # Show sentiment score metrics
    sentiment_data = get_sentiment_data()
    
    # Sort tickers by absolute sentiment score
    sorted_tickers = sorted(sentiment_data.items(), key=lambda x: abs(x[1]), reverse=True)
    
    # Create metrics display
    for ticker, score in sorted_tickers:
        color = "green" if score > 0 else "red" if score < 0 else "gray"
        
        # Use delta for indicating positive/negative
        delta = f"{score:.1f}" if score >= 0 else f"{score:.1f}"
        
        st.metric(
            label=f"{ticker}",
            value=f"{score:.1f}",
            delta=delta,
            delta_color="normal" if score >= 0 else "inverse"
        )

with col2:
    # Heatmap of sentiment scores
    st.subheader("Sentiment Heatmap")
    
    # Prepare data for heatmap
    heatmap_data = []
    for ticker, score in sentiment_data.items():
        category = "Bullish" if score > 33 else "Neutral" if score > -33 else "Bearish"
        abs_score = abs(score)
        intensity = min(abs_score / 100, 1.0)  # Normalize to 0-1
        
        heatmap_data.append({
            "Ticker": ticker,
            "Category": category,
            "Sentiment": score,
            "Intensity": intensity
        })
    
    heatmap_df = pd.DataFrame(heatmap_data)
    
    # Create heatmap using plotly
    fig = px.treemap(
        heatmap_df,
        path=[px.Constant("All"), "Category", "Ticker"],
        values="Intensity",
        color="Sentiment",
        color_continuous_scale=px.colors.diverging.RdBu_r,
        color_continuous_midpoint=0,
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Historical sentiment trends
st.header("Historical Sentiment Trends")

# Timeframe selection
timeframe = st.selectbox(
    "Select Timeframe",
    ["Last 24 Hours", "Last 3 Days", "Last Week", "Last Month"],
    index=1
)

# Convert timeframe to hours
if timeframe == "Last 24 Hours":
    hours = 24
elif timeframe == "Last 3 Days":
    hours = 72
elif timeframe == "Last Week":
    hours = 168
else:  # Last Month
    hours = 720

# Get historical data from Parquet files
historical_data = {}

for ticker in top_tickers:
    # Get data for the selected timeframe
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=hours)
    
    ticker_data = parquet_reader.read_ticker_data(ticker, start_date, end_date)
    
    if not ticker_data.empty:
        # Apply decay to historical data to match current calculation
        events = ticker_data.to_dict('records')
        
        # Calculate sentiment by hour
        hourly_sentiment = []
        current_time = start_date
        
        while current_time <= end_date:
            next_hour = current_time + timedelta(hours=1)
            
            # Calculate sentiment at this point in time
            point_sentiment = sentiment_model.calculate_sentiment_score(ticker, current_time)
            
            hourly_sentiment.append({
                'timestamp': current_time,
                'sentiment': point_sentiment
            })
            
            current_time = next_hour
            
        historical_data[ticker] = hourly_sentiment

# Plot historical trends
if historical_data:
    fig = go.Figure()
    
    for ticker, data in historical_data.items():
        if data:
            df = pd.DataFrame(data)
            fig.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['sentiment'],
                mode='lines',
                name=ticker
            ))
    
    fig.update_layout(
        title="Sentiment Score Over Time",
        xaxis_title="Time",
        yaxis_title="Sentiment Score",
        yaxis=dict(range=[-100, 100]),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No historical data available for the selected tickers.")

# Recent sentiment events
st.header("Recent Sentiment Events")

# Ticker selection for events
selected_ticker = st.selectbox(
    "Select Ticker",
    ["All"] + top_tickers,
    index=0
)

# Number of events to show
num_events = st.slider("Number of Events", 5, 50, 20)

# Get recent events
ticker_filter = None if selected_ticker == "All" else selected_ticker
recent_events = parquet_reader.get_latest_events(ticker_filter, limit=num_events, hours=hours)

if not recent_events.empty:
    # Format the data for display
    display_data = recent_events.copy()
    
    # Format timestamp
    display_data['timestamp'] = display_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Calculate impact for each event
    if 'impact' not in display_data.columns:
        from sentiment_analyzer.models.impact_scoring import calculate_impact
        display_data['impact'] = display_data.apply(lambda row: calculate_impact(row.to_dict()), axis=1)
    
    # Select columns to display
    display_columns = ['timestamp', 'ticker', 'sentiment', 'impact', 'source_type', 'source_name']
    if 'text' in display_data.columns:
        display_data['text_preview'] = display_data['text'].str[:100] + '...'
        display_columns.append('text_preview')
        
    # Show the data
    st.dataframe(display_data[display_columns], use_container_width=True)
else:
    st.info("No recent events found for the selected ticker.")

# About section
with st.expander("About This Dashboard"):
    st.markdown("""
    ## Real-Time Sentiment Analyzer
    
    This dashboard displays sentiment scores for the top S&P 500 tickers based on data from:
    - Financial news sources
    - Reddit discussions
    - Twitter/X mentions
    
    ### How It Works
    1. Raw data is collected from various sources and stored in Parquet files
    2. Sentiment scores are calculated with time decay and impact weighting
    3. Redis is used for real-time caching and updates
    
    ### Sentiment Score
    - Ranges from -100 (extremely negative) to +100 (extremely positive)
    - Weighted by source credibility and engagement metrics
    - Applies time decay to prioritize recent information
    
    ### Decay Functions
    - **Exponential**: Sentiment decays based on exponential formula e^(-λt)
    - **Linear**: Linear decrease in influence over time
    - **Half-life**: Influence halves after each half-life period
    """)

# Auto-refresh
if st.sidebar.checkbox("Auto Refresh", value=True):
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 10, 300, 60)
    st.sidebar.info(f"Dashboard will refresh every {refresh_interval} seconds")
    time.sleep(refresh_interval)
    st.rerun()