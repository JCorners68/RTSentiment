#!/usr/bin/env python3
"""
Query Interface for Sentiment Data
"""
import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Any, Optional

# Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8001")

# Page configuration
st.set_page_config(
    page_title="Sentiment Data Query",
    page_icon="🔍",
    layout="wide",
)

# Page styling
st.markdown("""
<style>
    /* Overall theme */
    .main {
        background-color: #f0f2f5;
        color: #333;
    }
    
    /* Card styling with improved shadow */
    .metric-card {
        background-color: white;
        border-radius: 8px;
        padding: 18px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        color: #333;
    }
    
    /* Charts and data displays */
    .element-container {
        background-color: white;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    
    /* Fix DataFrames styling */
    .stDataFrame {
        background-color: white;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        overflow: auto;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def fetch_metadata():
    """Fetch metadata for filtering options"""
    try:
        response = requests.get(f"{API_BASE_URL}/sentiment/metadata")
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "sources": ["news", "reddit", "twitter", "sec_filings"],
                "models": ["finbert", "fingpt", "llama4_scout"],
                "priorities": ["high", "standard"]
            }
    except Exception as e:
        st.error(f"Error fetching metadata: {e}")
        # Return some default values
        return {
            "sources": ["news", "reddit", "twitter", "sec_filings"],
            "models": ["finbert", "fingpt", "llama4_scout"],
            "priorities": ["high", "standard"]
        }

def fetch_tickers():
    """Fetch available tickers"""
    try:
        response = requests.get(f"{API_BASE_URL}/sentiment/tickers")
        if response.status_code == 200:
            return response.json()
        else:
            # Return some default tickers
            return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]
    except Exception as e:
        st.error(f"Error fetching tickers: {e}")
        # Return some default tickers
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]

def fetch_top_sentiment(limit=10, min_score=None, max_score=None, sort_by="score", order="desc"):
    """Fetch top sentiment data"""
    try:
        params = {"limit": limit, "sort_by": sort_by, "order": order}
        if min_score is not None:
            params["min_score"] = min_score
        if max_score is not None:
            params["max_score"] = max_score
            
        response = requests.get(f"{API_BASE_URL}/sentiment/top", params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching top sentiment: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"Error fetching top sentiment: {e}")
        return []

def query_sentiment_events(query_params):
    """Query sentiment events based on filters"""
    try:
        response = requests.post(f"{API_BASE_URL}/sentiment/query", json=query_params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error querying events: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"Error querying events: {e}")
        return []

def get_ticker_sentiment(ticker):
    """Get sentiment data for a specific ticker"""
    try:
        response = requests.get(f"{API_BASE_URL}/sentiment/ticker/{ticker}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching ticker sentiment: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error fetching ticker sentiment: {e}")
        return None

def analyze_custom_text(text):
    """Analyze sentiment of custom text"""
    try:
        response = requests.post(f"{API_BASE_URL}/sentiment/analyze", params={"text": text})
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error analyzing text: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error analyzing text: {e}")
        return None

# Main function
def main():
    st.title("Sentiment Data Query Interface")
    
    # Create tabs
    tabs = st.tabs(["📊 Top Performers", "🔍 Advanced Query", "📈 Ticker Analysis", "💬 Custom Text"])
    
    # Fetch metadata for filters
    metadata = fetch_metadata()
    tickers = fetch_tickers()
    
    # Top Performers Tab
    with tabs[0]:
        st.header("Top Performers by Sentiment")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Query Parameters")
            
            limit = st.slider("Number of tickers", 5, 50, 10)
            
            score_range = st.slider("Sentiment Score Range", -1.0, 1.0, (-0.2, 0.8), 0.1)
            min_score, max_score = score_range
            
            sort_options = {"Sentiment Score": "score", "Count": "count"}
            sort_by = sort_options[st.selectbox("Sort By", list(sort_options.keys()))]
            
            order_options = {"Highest First": "desc", "Lowest First": "asc"}
            order = order_options[st.selectbox("Order", list(order_options.keys()))]
            
            if st.button("Fetch Top Sentiment"):
                with st.spinner("Fetching data..."):
                    top_data = fetch_top_sentiment(
                        limit=limit, 
                        min_score=min_score, 
                        max_score=max_score, 
                        sort_by=sort_by, 
                        order=order
                    )
                    
                    if top_data:
                        st.session_state.top_data = top_data
        
        with col2:
            if 'top_data' in st.session_state and st.session_state.top_data:
                st.subheader("Results")
                
                df = pd.DataFrame(st.session_state.top_data)
                
                # Create a bar chart
                fig = px.bar(
                    df, 
                    x="ticker", 
                    y="score", 
                    color="sentiment",
                    color_discrete_map={
                        "positive": "#4CAF50",
                        "neutral": "#FFC107",
                        "negative": "#F44336"
                    },
                    hover_data=["count", "weight", "model"],
                    title="Top Tickers by Sentiment Score"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Show data table
                st.dataframe(df, use_container_width=True)
                
                # Allow CSV download
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name=f"top_sentiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Use the filters to fetch top sentiment data")
    
    # Advanced Query Tab
    with tabs[1]:
        st.header("Advanced Sentiment Query")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Query Filters")
            
            # Date range filter
            st.write("Date Range")
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
            end_date = st.date_input("End Date", datetime.now())
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Source filter
            st.write("Sources")
            selected_sources = st.multiselect("Select Sources", metadata["sources"])
            
            # Priority filter
            st.write("Priority")
            selected_priorities = st.multiselect("Select Priorities", metadata["priorities"])
            
            # Model filter
            st.write("Models")
            selected_models = st.multiselect("Select Models", metadata["models"])
            
            # Score range filter
            st.write("Sentiment Score Range")
            score_range = st.slider("Score Range", -1.0, 1.0, (-1.0, 1.0), 0.1, key="advanced_score")
            min_score, max_score = score_range
            
            # Ticker filter
            st.write("Tickers")
            selected_tickers = st.multiselect("Select Tickers", tickers)
            
            # Pagination
            st.write("Pagination")
            limit = st.number_input("Results per page", 10, 1000, 100)
            offset = st.number_input("Offset", 0, 10000, 0)
            
            # Build query params
            query_params = {
                "start_date": start_datetime.isoformat(),
                "end_date": end_datetime.isoformat(),
                "limit": limit,
                "offset": offset
            }
            
            if selected_sources:
                query_params["sources"] = selected_sources
            if selected_priorities:
                query_params["priority"] = selected_priorities
            if selected_models:
                query_params["models"] = selected_models
            if min_score > -1.0:
                query_params["min_score"] = min_score
            if max_score < 1.0:
                query_params["max_score"] = max_score
            if selected_tickers:
                query_params["tickers"] = selected_tickers
            
            # Execute query
            if st.button("Execute Query"):
                with st.spinner("Querying data..."):
                    results = query_sentiment_events(query_params)
                    
                    if results:
                        st.session_state.query_results = results
                    else:
                        st.session_state.query_results = []
        
        with col2:
            if 'query_results' in st.session_state:
                st.subheader("Query Results")
                
                if st.session_state.query_results:
                    df = pd.DataFrame(st.session_state.query_results)
                    
                    # Convert timestamp to datetime
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    # Show data table
                    st.dataframe(df, use_container_width=True)
                    
                    # Create visualizations
                    st.subheader("Visualizations")
                    
                    # Sentiment distribution
                    fig1 = px.histogram(
                        df, 
                        x="sentiment_score",
                        color="priority",
                        nbins=20,
                        title="Sentiment Score Distribution"
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                    
                    # Sources distribution
                    if 'source' in df.columns:
                        source_counts = df['source'].value_counts().reset_index()
                        source_counts.columns = ['source', 'count']
                        
                        fig2 = px.pie(
                            source_counts,
                            values='count',
                            names='source',
                            title="Event Sources Distribution"
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    # Allow CSV download
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv,
                        file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No results found for the given query parameters")
            else:
                st.info("Use the filters to query sentiment data")
    
    # Ticker Analysis Tab
    with tabs[2]:
        st.header("Ticker Sentiment Analysis")
        
        selected_ticker = st.selectbox("Select Ticker", tickers)
        
        if st.button("Analyze Ticker"):
            with st.spinner(f"Analyzing {selected_ticker}..."):
                ticker_data = get_ticker_sentiment(selected_ticker)
                
                if ticker_data:
                    st.subheader(f"Sentiment Analysis for {selected_ticker}")
                    
                    # Display in card format
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        sentiment_color = "#4CAF50" if ticker_data["sentiment"] == "positive" else "#F44336" if ticker_data["sentiment"] == "negative" else "#FFC107"
                        st.markdown(f"<h2 style='text-align: center; color: {sentiment_color};'>{ticker_data['sentiment'].upper()}</h2>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        st.metric("Sentiment Score", f"{ticker_data['score']:.4f}")
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        st.metric("Analyzed Events", ticker_data["count"])
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Visualization
                    score_data = {
                        "category": ["Score"],
                        "value": [ticker_data["score"]]
                    }
                    
                    df = pd.DataFrame(score_data)
                    fig = px.bar(
                        df,
                        x="category",
                        y="value",
                        color="value",
                        color_continuous_scale=["#F44336", "#FFC107", "#4CAF50"],
                        range_color=[-1, 1],
                        title=f"{selected_ticker} Sentiment Score",
                        height=300
                    )
                    fig.update_layout(yaxis_range=[-1, 1])
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(f"No data available for {selected_ticker}")
    
    # Custom Text Tab
    with tabs[3]:
        st.header("Custom Text Sentiment Analysis")
        
        text_input = st.text_area("Enter text to analyze", height=150)
        
        if st.button("Analyze Text") and text_input:
            with st.spinner("Analyzing text..."):
                analysis_result = analyze_custom_text(text_input)
                
                if analysis_result:
                    st.subheader("Sentiment Analysis Result")
                    
                    # Display in card format
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        sentiment_color = "#4CAF50" if analysis_result["sentiment"] == "positive" else "#F44336" if analysis_result["sentiment"] == "negative" else "#FFC107"
                        st.markdown(f"<h2 style='text-align: center; color: {sentiment_color};'>{analysis_result['sentiment'].upper()}</h2>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        st.metric("Sentiment Score", f"{analysis_result['score']:.4f}")
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        st.metric("Model Used", analysis_result["model"])
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Detected tickers
                    if analysis_result.get("tickers"):
                        st.subheader("Detected Tickers")
                        st.write(", ".join(analysis_result["tickers"]))
                    
                    # Visualization
                    score_data = {
                        "category": ["Score"],
                        "value": [analysis_result["score"]]
                    }
                    
                    df = pd.DataFrame(score_data)
                    fig = px.bar(
                        df,
                        x="category",
                        y="value",
                        color="value",
                        color_continuous_scale=["#F44336", "#FFC107", "#4CAF50"],
                        range_color=[-1, 1],
                        title="Text Sentiment Score",
                        height=300
                    )
                    fig.update_layout(yaxis_range=[-1, 1])
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error("Error analyzing text")

# Run the app
if __name__ == "__main__":
    main()