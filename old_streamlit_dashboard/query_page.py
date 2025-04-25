#!/usr/bin/env python3
"""
Query Page for RT Sentiment Dashboard
This module provides advanced query functionality against the PostgreSQL database
"""
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psycopg2
import base64
import json

# Configuration
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "sentiment")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres") 
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

# Connect to PostgreSQL
def get_postgres_conn():
    """Create a connection to PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            port=POSTGRES_PORT
        )
        return conn
    except Exception as e:
        st.error(f"Error connecting to PostgreSQL: {e}")
        return None

# Get available filter options
def get_filter_options():
    """Get available options for filter dropdowns"""
    try:
        conn = get_postgres_conn()
        if not conn:
            return {}, {}, {}
        
        # Get unique tickers
        tickers = []
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT ticker FROM sentiment_results ORDER BY ticker")
            ticker_results = cur.fetchall()
            tickers = [t[0] for t in ticker_results]
        
        # Get unique sources
        sources = []
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT source FROM sentiment_results ORDER BY source")
            source_results = cur.fetchall()
            sources = [s[0] for s in source_results]
        
        # Get unique models
        models = []
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT model FROM sentiment_results ORDER BY model")
            model_results = cur.fetchall()
            models = [m[0] for m in model_results]
        
        return tickers, sources, models
    
    except Exception as e:
        st.error(f"Error getting filter options: {e}")
        return [], [], []
    
    finally:
        if conn:
            conn.close()

# Execute custom SQL query
def execute_query(query, params=None):
    """Execute a custom SQL query against the database"""
    try:
        conn = get_postgres_conn()
        if not conn:
            return None
        
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cur.description]
            
            # Fetch results
            results = cur.fetchall()
            
            # Convert to DataFrame
            if results:
                df = pd.DataFrame(results, columns=columns)
                return df
            else:
                return pd.DataFrame(columns=columns)
    
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None
    
    finally:
        if conn:
            conn.close()

# Predefined queries
PREDEFINED_QUERIES = {
    "top_positive_tickers": {
        "name": "Top 10 Positive Sentiment Tickers",
        "query": """
            SELECT 
                ticker, 
                AVG(sentiment) as avg_sentiment,
                COUNT(*) as event_count,
                AVG(confidence) as avg_confidence
            FROM sentiment_results
            WHERE timestamp > NOW() - INTERVAL '1 week'
            GROUP BY ticker
            HAVING COUNT(*) > 5
            ORDER BY avg_sentiment DESC
            LIMIT 10
        """,
        "description": "Tickers with the highest average sentiment in the last week (minimum 5 events)"
    },
    "top_negative_tickers": {
        "name": "Top 10 Negative Sentiment Tickers",
        "query": """
            SELECT 
                ticker, 
                AVG(sentiment) as avg_sentiment,
                COUNT(*) as event_count,
                AVG(confidence) as avg_confidence
            FROM sentiment_results
            WHERE timestamp > NOW() - INTERVAL '1 week'
            GROUP BY ticker
            HAVING COUNT(*) > 5
            ORDER BY avg_sentiment ASC
            LIMIT 10
        """,
        "description": "Tickers with the lowest average sentiment in the last week (minimum 5 events)"
    },
    "sentiment_by_source": {
        "name": "Sentiment by Source Type",
        "query": """
            SELECT 
                source,
                AVG(sentiment) as avg_sentiment,
                COUNT(*) as event_count,
                AVG(confidence) as avg_confidence
            FROM sentiment_results
            WHERE timestamp > NOW() - INTERVAL '1 month'
            GROUP BY source
            ORDER BY avg_sentiment DESC
        """,
        "description": "Average sentiment score by data source type over the last month"
    },
    "top_mentioned_tickers": {
        "name": "Most Mentioned Tickers",
        "query": """
            SELECT 
                ticker,
                COUNT(*) as mention_count,
                AVG(sentiment) as avg_sentiment
            FROM sentiment_results
            WHERE timestamp > NOW() - INTERVAL '1 week'
            GROUP BY ticker
            ORDER BY mention_count DESC
            LIMIT 20
        """,
        "description": "Tickers with the most mentions in the last week"
    },
    "sentiment_volatility": {
        "name": "Tickers with Highest Sentiment Volatility",
        "query": """
            SELECT 
                ticker,
                STDDEV(sentiment) as sentiment_stddev,
                AVG(sentiment) as avg_sentiment,
                COUNT(*) as event_count
            FROM sentiment_results
            WHERE timestamp > NOW() - INTERVAL '1 week'
            GROUP BY ticker
            HAVING COUNT(*) > 5
            ORDER BY sentiment_stddev DESC
            LIMIT 10
        """,
        "description": "Tickers with the most volatile sentiment scores (highest standard deviation)"
    },
    "hourly_sentiment_trend": {
        "name": "Hourly Sentiment Trend (All Tickers)",
        "query": """
            SELECT 
                date_trunc('hour', timestamp) as hour,
                AVG(sentiment) as avg_sentiment,
                COUNT(*) as event_count
            FROM sentiment_results
            WHERE timestamp > NOW() - INTERVAL '2 days'
            GROUP BY hour
            ORDER BY hour
        """,
        "description": "Average sentiment score by hour over the last 2 days"
    },
    "ticker_sentiment_comparison": {
        "name": "Sentiment Comparison for Top Tickers",
        "query": """
            WITH top_tickers AS (
                SELECT ticker
                FROM sentiment_results
                GROUP BY ticker
                ORDER BY COUNT(*) DESC
                LIMIT 5
            )
            SELECT 
                ticker,
                source,
                AVG(sentiment) as avg_sentiment,
                COUNT(*) as event_count
            FROM sentiment_results
            WHERE ticker IN (SELECT ticker FROM top_tickers)
            AND timestamp > NOW() - INTERVAL '1 week'
            GROUP BY ticker, source
            ORDER BY ticker, avg_sentiment DESC
        """,
        "description": "Compare sentiment across different sources for the most popular tickers"
    }
}

# Custom query templates
def get_query_templates():
    """Get a list of query templates with placeholders"""
    templates = [
        {
            "name": "Ticker Performance Over Time",
            "template": """
                SELECT 
                    date_trunc('{interval}', timestamp) as time_bucket,
                    AVG(sentiment) as avg_sentiment,
                    COUNT(*) as event_count
                FROM sentiment_results
                WHERE ticker = '{ticker}'
                AND timestamp > NOW() - INTERVAL '{timeframe}'
                GROUP BY time_bucket
                ORDER BY time_bucket
            """,
            "parameters": {
                "ticker": {"type": "ticker", "description": "Ticker symbol"},
                "interval": {"type": "select", "options": ["hour", "day", "week"], "description": "Time grouping interval"},
                "timeframe": {"type": "select", "options": ["1 day", "1 week", "1 month", "3 months"], "description": "Analysis timeframe"}
            },
            "description": "Track sentiment for a specific ticker over time"
        },
        {
            "name": "Source Comparison",
            "template": """
                SELECT 
                    source,
                    ticker,
                    AVG(sentiment) as avg_sentiment,
                    COUNT(*) as event_count
                FROM sentiment_results
                WHERE ticker IN ('{ticker1}', '{ticker2}')
                AND timestamp > NOW() - INTERVAL '{timeframe}'
                GROUP BY source, ticker
                ORDER BY source, avg_sentiment DESC
            """,
            "parameters": {
                "ticker1": {"type": "ticker", "description": "First ticker symbol"},
                "ticker2": {"type": "ticker", "description": "Second ticker symbol"},
                "timeframe": {"type": "select", "options": ["1 day", "1 week", "1 month", "3 months"], "description": "Analysis timeframe"}
            },
            "description": "Compare sentiment between two tickers across different sources"
        },
        {
            "name": "Sentiment Distribution",
            "template": """
                WITH bins AS (
                    SELECT 
                        ticker,
                        CASE
                            WHEN sentiment < -0.7 THEN 'Very Negative'
                            WHEN sentiment < -0.3 THEN 'Negative'
                            WHEN sentiment < 0.3 THEN 'Neutral'
                            WHEN sentiment < 0.7 THEN 'Positive'
                            ELSE 'Very Positive'
                        END AS sentiment_category
                    FROM sentiment_results
                    WHERE ticker = '{ticker}'
                    AND timestamp > NOW() - INTERVAL '{timeframe}'
                )
                SELECT
                    sentiment_category,
                    COUNT(*) as count
                FROM bins
                GROUP BY sentiment_category
                ORDER BY 
                    CASE sentiment_category
                        WHEN 'Very Negative' THEN 1
                        WHEN 'Negative' THEN 2
                        WHEN 'Neutral' THEN 3
                        WHEN 'Positive' THEN 4
                        WHEN 'Very Positive' THEN 5
                    END
            """,
            "parameters": {
                "ticker": {"type": "ticker", "description": "Ticker symbol"},
                "timeframe": {"type": "select", "options": ["1 day", "1 week", "1 month", "3 months"], "description": "Analysis timeframe"}
            },
            "description": "Show distribution of sentiment categories for a specific ticker"
        }
    ]
    
    return templates

# Visualize query results
def visualize_results(df, query_name):
    """Create appropriate visualizations based on query results and query type"""
    if df is None or df.empty:
        st.warning("No data available to visualize")
        return
    
    # Check columns to determine appropriate visualization
    columns = df.columns.tolist()
    
    # Time series visualization
    if 'hour' in columns or 'time_bucket' in columns:
        time_col = 'hour' if 'hour' in columns else 'time_bucket'
        
        fig = go.Figure()
        
        # Add sentiment line
        if 'avg_sentiment' in columns:
            fig.add_trace(go.Scatter(
                x=df[time_col],
                y=df['avg_sentiment'],
                mode='lines+markers',
                name='Average Sentiment',
                line=dict(color='#4CAF50', width=3),
                marker=dict(size=8),
                hovertemplate='%{x}<br>Sentiment: %{y:.2f}'
            ))
        
        # Add event count bars if available
        if 'event_count' in columns:
            fig.add_trace(go.Bar(
                x=df[time_col],
                y=df['event_count'],
                name='Event Count',
                marker=dict(color='rgba(33, 150, 243, 0.3)'),
                hovertemplate='%{x}<br>Count: %{y}',
                yaxis='y2'
            ))
        
        # Update layout
        fig.update_layout(
            title=f"{query_name}",
            xaxis_title="Time",
            yaxis=dict(
                title="Average Sentiment",
                range=[-1, 1],
                titlefont=dict(color="#4CAF50"),
                tickfont=dict(color="#4CAF50")
            ),
            yaxis2=dict(
                title="Event Count",
                titlefont=dict(color="#2196F3"),
                tickfont=dict(color="#2196F3"),
                anchor="x",
                overlaying="y",
                side="right"
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=60, b=20),
            height=500,
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Bar chart for comparisons
    elif ('ticker' in columns and 'avg_sentiment' in columns) or ('source' in columns and 'avg_sentiment' in columns):
        # Determine x-axis
        x_col = 'ticker' if 'ticker' in columns else 'source'
        
        if 'source' in columns and 'ticker' in columns:
            # Create grouped bar chart for comparisons
            fig = px.bar(
                df,
                x=x_col,
                y='avg_sentiment',
                color='source' if x_col == 'ticker' else 'ticker',
                barmode='group',
                color_continuous_scale='RdYlGn',
                labels={'avg_sentiment': 'Average Sentiment', x_col: x_col.title()},
                title=query_name,
                hover_data=['event_count'] if 'event_count' in columns else None
            )
        else:
            # Standard bar chart
            fig = px.bar(
                df,
                x=x_col,
                y='avg_sentiment',
                color='avg_sentiment',
                color_continuous_scale='RdYlGn',
                labels={'avg_sentiment': 'Average Sentiment', x_col: x_col.title()},
                title=query_name,
                hover_data=['event_count'] if 'event_count' in columns else None
            )
        
        # Add event count line if available
        if 'event_count' in columns:
            fig.add_trace(
                go.Scatter(
                    x=df[x_col],
                    y=df['event_count'],
                    mode='lines+markers',
                    name='Event Count',
                    yaxis='y2'
                )
            )
            
            fig.update_layout(
                yaxis2=dict(
                    title="Event Count",
                    overlaying="y",
                    side="right"
                )
            )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Pie chart for distributions
    elif 'sentiment_category' in columns and 'count' in columns:
        fig = px.pie(
            df,
            values='count',
            names='sentiment_category',
            title=query_name,
            color='sentiment_category',
            color_discrete_map={
                'Very Negative': '#d32f2f',
                'Negative': '#ff5722',
                'Neutral': '#ffeb3b',
                'Positive': '#8bc34a',
                'Very Positive': '#4caf50'
            }
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Default visualization for other types of queries
    else:
        # Display as regular dataframe
        st.dataframe(df, use_container_width=True)
        
        # Try to create a sensible default visualization based on columns
        if len(df) > 0:
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            
            if len(numeric_cols) > 0 and len(df.columns) > 1:
                # Try to create a bar chart with the first column as x and first numeric as y
                x_col = df.columns[0]
                y_col = numeric_cols[0]
                
                fig = px.bar(
                    df,
                    x=x_col,
                    y=y_col,
                    title=f"{query_name} - {y_col} by {x_col}",
                    labels={y_col: y_col.replace('_', ' ').title(), x_col: x_col.replace('_', ' ').title()}
                )
                
                st.plotly_chart(fig, use_container_width=True)

# Main function for query page
def main():
    st.title("Sentiment Query Tool")
    
    # Check database connection
    conn = get_postgres_conn()
    if not conn:
        st.error("⚠️ Could not connect to PostgreSQL database")
        st.info("Please check your database configuration and make sure PostgreSQL is running.")
        return
    conn.close()
    
    # Get filter options
    tickers, sources, models = get_filter_options()
    
    # Create tabs
    tabs = st.tabs([
        "📊 Predefined Queries", 
        "🔍 Custom Queries", 
        "📝 SQL Editor"
    ])
    
    # Predefined Queries Tab
    with tabs[0]:
        st.header("Predefined Queries")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Query selection
            selected_query = st.selectbox(
                "Select Query",
                options=list(PREDEFINED_QUERIES.keys()),
                format_func=lambda x: PREDEFINED_QUERIES[x]["name"]
            )
            
            # Show query details
            st.markdown(f"**Description**: {PREDEFINED_QUERIES[selected_query]['description']}")
            
            with st.expander("View SQL"):
                st.code(PREDEFINED_QUERIES[selected_query]["query"], language="sql")
            
            # Execute button
            if st.button("Execute Query", key="predefined_execute"):
                with st.spinner("Executing query..."):
                    # Execute the selected query
                    df = execute_query(PREDEFINED_QUERIES[selected_query]["query"])
                    
                    if df is not None and not df.empty:
                        # Store in session state
                        st.session_state.predefined_results = df
                        st.session_state.predefined_query_name = PREDEFINED_QUERIES[selected_query]["name"]
                    else:
                        st.warning("No results found for this query")
        
        with col2:
            # Results area
            if 'predefined_results' in st.session_state and not st.session_state.predefined_results.empty:
                st.subheader(f"Results: {st.session_state.predefined_query_name}")
                
                # Visualize the results
                visualize_results(st.session_state.predefined_results, st.session_state.predefined_query_name)
                
                # Show raw data
                with st.expander("View Raw Data"):
                    st.dataframe(st.session_state.predefined_results, use_container_width=True)
                
                # Download options
                col_a, col_b = st.columns(2)
                
                with col_a:
                    # CSV download
                    csv = st.session_state.predefined_results.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="query_results.csv" class="download-button">Download CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
                
                with col_b:
                    # JSON download
                    json_str = st.session_state.predefined_results.to_json(orient='records', date_format='iso')
                    b64_json = base64.b64encode(json_str.encode()).decode()
                    href_json = f'<a href="data:application/json;base64,{b64_json}" download="query_results.json" class="download-button">Download JSON</a>'
                    st.markdown(href_json, unsafe_allow_html=True)
            else:
                st.info("Select a query from the left and click 'Execute Query' to see results here")
    
    # Custom Queries Tab
    with tabs[1]:
        st.header("Custom Query Templates")
        
        # Get query templates
        templates = get_query_templates()
        
        # Template selection
        selected_template = st.selectbox(
            "Select Template",
            options=range(len(templates)),
            format_func=lambda i: templates[i]["name"]
        )
        
        template = templates[selected_template]
        
        st.markdown(f"**Description**: {template['description']}")
        
        # Parameter inputs
        st.subheader("Parameters")
        
        # Initialize parameter values dict
        param_values = {}
        
        # Create input fields for each parameter
        for param_name, param_info in template["parameters"].items():
            if param_info["type"] == "ticker":
                param_values[param_name] = st.selectbox(
                    param_info["description"],
                    options=tickers,
                    key=f"param_{param_name}"
                )
            elif param_info["type"] == "select":
                param_values[param_name] = st.selectbox(
                    param_info["description"],
                    options=param_info["options"],
                    key=f"param_{param_name}"
                )
        
        # Preview the query
        with st.expander("Preview Query"):
            # Format the query template with parameter values
            formatted_query = template["template"].format(**param_values)
            st.code(formatted_query, language="sql")