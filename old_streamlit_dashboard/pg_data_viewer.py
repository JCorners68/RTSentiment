#!/usr/bin/env python3
"""
PostgreSQL Data Viewer for Real-Time Sentiment Analysis System
Direct database connection for data exploration, visualization, and maintenance
"""
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlalchemy
from sqlalchemy import create_engine, text, func, desc, asc
import time
import io
import base64

# Database configuration
DB_USER = os.environ.get("POSTGRES_USER", "pgadmin")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "localdev")
DB_HOST = os.environ.get("POSTGRES_HOST", "postgres")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "sentimentdb")

# Create database connection string
DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

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
        margin-bottom: 15px;
    }
    
    /* Database info card */
    .db-info-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 4px solid #4CAF50;
        margin-bottom: 15px;
    }
    
    /* SQL editor */
    .sql-editor {
        background-color: #272822;
        color: #f8f8f2;
        font-family: 'Courier New', monospace;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
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
    
    /* Status indicators */
    .status-success {
        color: #4CAF50;
        font-weight: bold;
    }
    
    .status-warning {
        color: #FFC107;
        font-weight: bold;
    }
    
    .status-error {
        color: #F44336;
        font-weight: bold;
    }
    
    /* Tab styling */
    .data-tabs .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e8eef1;
        border-radius: 8px 8px 0 0;
        padding: 8px 8px 0 8px;
    }
    
    .data-tabs .stTabs [data-baseweb="tab"] {
        background-color: #cfd8dc;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 16px;
        color: #455a64 !important;
        font-weight: 500;
    }
    
    .data-tabs .stTabs [aria-selected="true"] {
        background-color: #388e3c;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper Functions
@st.cache_resource(ttl=300)
def get_database_connection():
    """Create and return a database connection"""
    try:
        engine = create_engine(DB_CONNECTION_STRING)
        return engine
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

@st.cache_data(ttl=60)
def get_database_info(engine):
    """Get database stats and information"""
    try:
        with engine.connect() as conn:
            # Get table sizes
            table_sizes_query = text("""
                SELECT
                    table_name,
                    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as total_size,
                    pg_total_relation_size(quote_ident(table_name)) as size_bytes
                FROM 
                    information_schema.tables
                WHERE 
                    table_schema = 'public'
                ORDER BY 
                    pg_total_relation_size(quote_ident(table_name)) DESC
            """)
            table_sizes = pd.read_sql(table_sizes_query, conn)
            
            # Get total database size
            db_size_query = text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                       pg_database_size(current_database()) as size_bytes
            """)
            db_size = pd.read_sql(db_size_query, conn)
            
            # Get table row counts
            row_counts_query = text("""
                SELECT
                    table_name,
                    (SELECT reltuples::bigint FROM pg_class WHERE oid = (quote_ident(table_name)::regclass)) as estimated_row_count
                FROM 
                    information_schema.tables
                WHERE 
                    table_schema = 'public'
                ORDER BY 
                    estimated_row_count DESC
            """)
            row_counts = pd.read_sql(row_counts_query, conn)
            
            return {
                "table_sizes": table_sizes,
                "db_size": db_size,
                "row_counts": row_counts
            }
    except Exception as e:
        st.error(f"Error getting database info: {e}")
        return None

@st.cache_data(ttl=60)
def get_sentiment_events(engine, limit=1000, filters=None):
    """Get sentiment events with optional filters"""
    try:
        with engine.connect() as conn:
            # Base query
            query = text(f"""
                SELECT 
                    se.*,
                    array_agg(DISTINCT ts.ticker) as tickers
                FROM 
                    sentiment_events se
                LEFT JOIN 
                    ticker_sentiments ts ON se.id = ts.event_id
            """)
            
            # Add filters if provided
            where_clauses = []
            params = {}
            
            if filters:
                if filters.get('start_date'):
                    where_clauses.append("se.timestamp >= :start_date")
                    params['start_date'] = filters['start_date']
                
                if filters.get('end_date'):
                    where_clauses.append("se.timestamp <= :end_date")
                    params['end_date'] = filters['end_date']
                
                if filters.get('sources'):
                    where_clauses.append("se.source IN :sources")
                    params['sources'] = tuple(filters['sources'])
                
                if filters.get('priorities'):
                    where_clauses.append("se.priority IN :priorities")
                    params['priorities'] = tuple(filters['priorities'])
                
                if filters.get('models'):
                    where_clauses.append("se.model IN :models")
                    params['models'] = tuple(filters['models'])
                
                if filters.get('min_score') is not None:
                    where_clauses.append("se.sentiment_score >= :min_score")
                    params['min_score'] = filters['min_score']
                
                if filters.get('max_score') is not None:
                    where_clauses.append("se.sentiment_score <= :max_score")
                    params['max_score'] = filters['max_score']
                
                if filters.get('tickers'):
                    where_clauses.append("EXISTS (SELECT 1 FROM ticker_sentiments ts WHERE ts.event_id = se.id AND ts.ticker IN :tickers)")
                    params['tickers'] = tuple(filters['tickers'])
            
            # Combine where clauses if any
            if where_clauses:
                query = text(f"""
                    SELECT 
                        se.*,
                        array_agg(DISTINCT ts.ticker) as tickers
                    FROM 
                        sentiment_events se
                    LEFT JOIN 
                        ticker_sentiments ts ON se.id = ts.event_id
                    WHERE 
                        {" AND ".join(where_clauses)}
                    GROUP BY 
                        se.id
                    ORDER BY 
                        se.timestamp DESC
                    LIMIT :limit
                """)
            else:
                query = text(f"""
                    SELECT 
                        se.*,
                        array_agg(DISTINCT ts.ticker) as tickers
                    FROM 
                        sentiment_events se
                    LEFT JOIN 
                        ticker_sentiments ts ON se.id = ts.event_id
                    GROUP BY 
                        se.id
                    ORDER BY 
                        se.timestamp DESC
                    LIMIT :limit
                """)
            
            # Add limit parameter
            params['limit'] = limit
            
            # Execute query
            df = pd.read_sql(query, conn, params=params)
            return df
    except Exception as e:
        st.error(f"Error querying sentiment events: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_ticker_sentiments(engine, limit=1000, filters=None):
    """Get ticker sentiments with optional filters"""
    try:
        with engine.connect() as conn:
            # Base query
            query = text(f"""
                SELECT 
                    ts.*,
                    se.source,
                    se.priority,
                    se.model,
                    se.timestamp
                FROM 
                    ticker_sentiments ts
                JOIN 
                    sentiment_events se ON ts.event_id = se.id
            """)
            
            # Add filters if provided
            where_clauses = []
            params = {}
            
            if filters:
                if filters.get('start_date'):
                    where_clauses.append("se.timestamp >= :start_date")
                    params['start_date'] = filters['start_date']
                
                if filters.get('end_date'):
                    where_clauses.append("se.timestamp <= :end_date")
                    params['end_date'] = filters['end_date']
                
                if filters.get('sources'):
                    where_clauses.append("se.source IN :sources")
                    params['sources'] = tuple(filters['sources'])
                
                if filters.get('priorities'):
                    where_clauses.append("se.priority IN :priorities")
                    params['priorities'] = tuple(filters['priorities'])
                
                if filters.get('models'):
                    where_clauses.append("se.model IN :models")
                    params['models'] = tuple(filters['models'])
                
                if filters.get('min_score') is not None:
                    where_clauses.append("ts.sentiment_score >= :min_score")
                    params['min_score'] = filters['min_score']
                
                if filters.get('max_score') is not None:
                    where_clauses.append("ts.sentiment_score <= :max_score")
                    params['max_score'] = filters['max_score']
                
                if filters.get('tickers'):
                    where_clauses.append("ts.ticker IN :tickers")
                    params['tickers'] = tuple(filters['tickers'])
            
            # Combine where clauses if any
            if where_clauses:
                query = text(f"""
                    SELECT 
                        ts.*,
                        se.source,
                        se.priority,
                        se.model,
                        se.timestamp
                    FROM 
                        ticker_sentiments ts
                    JOIN 
                        sentiment_events se ON ts.event_id = se.id
                    WHERE 
                        {" AND ".join(where_clauses)}
                    ORDER BY 
                        se.timestamp DESC
                    LIMIT :limit
                """)
            else:
                query = text(f"""
                    SELECT 
                        ts.*,
                        se.source,
                        se.priority,
                        se.model,
                        se.timestamp
                    FROM 
                        ticker_sentiments ts
                    JOIN 
                        sentiment_events se ON ts.event_id = se.id
                    ORDER BY 
                        se.timestamp DESC
                    LIMIT :limit
                """)
            
            # Add limit parameter
            params['limit'] = limit
            
            # Execute query
            df = pd.read_sql(query, conn, params=params)
            return df
    except Exception as e:
        st.error(f"Error querying ticker sentiments: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_metadata(engine):
    """Get metadata for UI filtering"""
    try:
        with engine.connect() as conn:
            # Get distinct sources
            sources_query = text("SELECT DISTINCT source FROM sentiment_events ORDER BY source")
            sources = pd.read_sql(sources_query, conn)['source'].tolist()
            
            # Get distinct models
            models_query = text("SELECT DISTINCT model FROM sentiment_events ORDER BY model")
            models = pd.read_sql(models_query, conn)['model'].tolist()
            
            # Get distinct priorities
            priorities_query = text("SELECT DISTINCT priority FROM sentiment_events ORDER BY priority")
            priorities = pd.read_sql(priorities_query, conn)['priority'].tolist()
            
            # Get distinct tickers
            tickers_query = text("SELECT DISTINCT ticker FROM ticker_sentiments ORDER BY ticker")
            tickers = pd.read_sql(tickers_query, conn)['ticker'].tolist()
            
            return {
                'sources': sources,
                'models': models,
                'priorities': priorities,
                'tickers': tickers
            }
    except Exception as e:
        st.error(f"Error fetching metadata: {e}")
        return {
            'sources': [],
            'models': [],
            'priorities': [],
            'tickers': []
        }

def execute_maintenance(engine, query, query_name):
    """Execute a maintenance query"""
    try:
        with engine.connect() as conn:
            start_time = time.time()
            result = conn.execute(text(query))
            duration = time.time() - start_time
            conn.commit()
            return {
                'success': True,
                'query': query_name,
                'rows_affected': result.rowcount if hasattr(result, 'rowcount') else 0,
                'duration': f"{duration:.2f} seconds"
            }
    except Exception as e:
        return {
            'success': False,
            'query': query_name,
            'error': str(e)
        }

def get_ticker_sentiment_summary(engine, ticker):
    """Get sentiment summary for a specific ticker"""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    ts.ticker,
                    AVG(ts.sentiment_score) as avg_score,
                    COUNT(*) as count,
                    MIN(ts.sentiment_score) as min_score,
                    MAX(ts.sentiment_score) as max_score,
                    MIN(se.timestamp) as first_seen,
                    MAX(se.timestamp) as last_seen,
                    array_agg(DISTINCT se.source) as sources,
                    array_agg(DISTINCT se.model) as models
                FROM 
                    ticker_sentiments ts
                JOIN 
                    sentiment_events se ON ts.event_id = se.id
                WHERE 
                    ts.ticker = :ticker
                GROUP BY 
                    ts.ticker
            """)
            
            df = pd.read_sql(query, conn, params={'ticker': ticker})
            return df
    except Exception as e:
        st.error(f"Error getting ticker summary: {e}")
        return pd.DataFrame()

def execute_custom_query(engine, query_text, params=None):
    """Execute a custom SQL query"""
    try:
        with engine.connect() as conn:
            start_time = time.time()
            if query_text.lower().strip().startswith(('select', 'with')):
                # For SELECT queries, return data
                result = pd.read_sql(text(query_text), conn, params=params)
                duration = time.time() - start_time
                return {
                    'success': True,
                    'type': 'select',
                    'data': result,
                    'rows': len(result),
                    'duration': f"{duration:.2f} seconds"
                }
            else:
                # For other queries (INSERT, UPDATE, DELETE), execute and commit
                result = conn.execute(text(query_text), params)
                conn.commit()
                duration = time.time() - start_time
                return {
                    'success': True,
                    'type': 'modify',
                    'rows_affected': result.rowcount if hasattr(result, 'rowcount') else 0,
                    'duration': f"{duration:.2f} seconds"
                }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def plot_ticker_sentiment_trend(engine, ticker, days=30):
    """Plot sentiment trend for a ticker over time"""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    ts.ticker,
                    se.timestamp::date as date,
                    AVG(ts.sentiment_score) as avg_score,
                    COUNT(*) as count
                FROM 
                    ticker_sentiments ts
                JOIN 
                    sentiment_events se ON ts.event_id = se.id
                WHERE 
                    ts.ticker = :ticker
                    AND se.timestamp >= CURRENT_DATE - INTERVAL ':days days'
                GROUP BY 
                    ts.ticker, se.timestamp::date
                ORDER BY 
                    date
            """)
            
            df = pd.read_sql(query, conn, params={'ticker': ticker, 'days': days})
            
            if len(df) > 0:
                # Create trend chart
                fig = px.line(
                    df, 
                    x='date', 
                    y='avg_score',
                    title=f"{ticker} Sentiment Trend",
                    labels={'avg_score': 'Average Sentiment Score', 'date': 'Date'},
                    color_discrete_sequence=['#4CAF50']
                )
                
                # Add volume as bars
                fig.add_trace(
                    go.Bar(
                        x=df['date'],
                        y=df['count'],
                        name='Event Count',
                        yaxis='y2',
                        marker_color='rgba(33, 150, 243, 0.3)',
                        opacity=0.7
                    )
                )
                
                # Update layout for dual axis
                fig.update_layout(
                    yaxis=dict(
                        title='Sentiment Score',
                        range=[-1, 1]
                    ),
                    yaxis2=dict(
                        title='Event Count',
                        overlaying='y',
                        side='right',
                        showgrid=False
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                return fig
            else:
                return None
    except Exception as e:
        st.error(f"Error plotting ticker trend: {e}")
        return None

def generate_data_insights(engine):
    """Generate insights from the sentiment data"""
    try:
        with engine.connect() as conn:
            # Top positive tickers
            top_positive_query = text("""
                SELECT 
                    ts.ticker,
                    AVG(ts.sentiment_score) as avg_score,
                    COUNT(*) as count
                FROM 
                    ticker_sentiments ts
                JOIN 
                    sentiment_events se ON ts.event_id = se.id
                WHERE 
                    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY 
                    ts.ticker
                HAVING 
                    COUNT(*) >= 5
                ORDER BY 
                    avg_score DESC
                LIMIT 5
            """)
            top_positive = pd.read_sql(top_positive_query, conn)
            
            # Top negative tickers
            top_negative_query = text("""
                SELECT 
                    ts.ticker,
                    AVG(ts.sentiment_score) as avg_score,
                    COUNT(*) as count
                FROM 
                    ticker_sentiments ts
                JOIN 
                    sentiment_events se ON ts.event_id = se.id
                WHERE 
                    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY 
                    ts.ticker
                HAVING 
                    COUNT(*) >= 5
                ORDER BY 
                    avg_score ASC
                LIMIT 5
            """)
            top_negative = pd.read_sql(top_negative_query, conn)
            
            # Most volatile tickers (highest standard deviation)
            most_volatile_query = text("""
                SELECT 
                    ts.ticker,
                    STDDEV(ts.sentiment_score) as volatility,
                    AVG(ts.sentiment_score) as avg_score,
                    COUNT(*) as count
                FROM 
                    ticker_sentiments ts
                JOIN 
                    sentiment_events se ON ts.event_id = se.id
                WHERE 
                    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY 
                    ts.ticker
                HAVING 
                    COUNT(*) >= 5
                ORDER BY 
                    volatility DESC
                LIMIT 5
            """)
            most_volatile = pd.read_sql(most_volatile_query, conn)
            
            # Most mentioned tickers
            most_mentioned_query = text("""
                SELECT 
                    ts.ticker,
                    COUNT(*) as count,
                    AVG(ts.sentiment_score) as avg_score
                FROM 
                    ticker_sentiments ts
                JOIN 
                    sentiment_events se ON ts.event_id = se.id
                WHERE 
                    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY 
                    ts.ticker
                ORDER BY 
                    count DESC
                LIMIT 5
            """)
            most_mentioned = pd.read_sql(most_mentioned_query, conn)
            
            # Source statistics
            source_stats_query = text("""
                SELECT 
                    se.source,
                    COUNT(*) as count,
                    AVG(se.sentiment_score) as avg_score
                FROM 
                    sentiment_events se
                WHERE 
                    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY 
                    se.source
                ORDER BY 
                    count DESC
            """)
            source_stats = pd.read_sql(source_stats_query, conn)
            
            # Daily trend
            daily_trend_query = text("""
                SELECT 
                    se.timestamp::date as date,
                    COUNT(*) as count,
                    AVG(se.sentiment_score) as avg_score
                FROM 
                    sentiment_events se
                WHERE 
                    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY 
                    date
                ORDER BY 
                    date
            """)
            daily_trend = pd.read_sql(daily_trend_query, conn)
            
            return {
                'top_positive': top_positive,
                'top_negative': top_negative,
                'most_volatile': most_volatile,
                'most_mentioned': most_mentioned,
                'source_stats': source_stats,
                'daily_trend': daily_trend
            }
    except Exception as e:
        st.error(f"Error generating insights: {e}")
        return {}

def main():
    st.title("PostgreSQL Data Viewer")
    st.write("Directly connect to the database for data exploration, visualization, and maintenance")
    
    # Connect to database
    engine = get_database_connection()
    
    if not engine:
        st.error("Failed to connect to the database. Please check your connection settings.")
        return
    
    # Get metadata for filters
    metadata = get_metadata(engine)
    
    # Create tabs
    tabs = st.tabs([
        "📊 Database Overview", 
        "🔍 Data Explorer", 
        "📈 Ticker Analysis",
        "🔮 Insights",
        "🛠️ Maintenance"
    ])
    
    # Database Overview Tab
    with tabs[0]:
        st.header("Database Overview")
        
        # Get database info
        db_info = get_database_info(engine)
        
        if db_info:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Database Size", db_info['db_size']['db_size'].values[0])
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                table_count = len(db_info['table_sizes'])
                st.metric("Tables", f"{table_count}")
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col3:
                # Calculate total rows across all tables
                total_rows = db_info['row_counts']['estimated_row_count'].sum()
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Total Records", f"{total_rows:,}")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Table sizes
            st.subheader("Table Sizes")
            
            # Create bar chart for table sizes
            fig = px.bar(
                db_info['table_sizes'], 
                x='table_name', 
                y='size_bytes',
                title="Table Sizes",
                labels={'size_bytes': 'Size (bytes)', 'table_name': 'Table'},
                color_discrete_sequence=['#4CAF50']
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Row counts
            st.subheader("Row Counts")
            
            # Create bar chart for row counts
            fig2 = px.bar(
                db_info['row_counts'], 
                x='table_name', 
                y='estimated_row_count',
                title="Table Row Counts",
                labels={'estimated_row_count': 'Estimated Rows', 'table_name': 'Table'},
                color_discrete_sequence=['#2196F3']
            )
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)
            
            # Table information
            st.subheader("Table Information")
            
            # Join table sizes and row counts
            tables_df = pd.merge(
                db_info['table_sizes'],
                db_info['row_counts'],
                on='table_name'
            )
            
            # Add average row size
            tables_df['avg_row_size'] = tables_df.apply(
                lambda x: 0 if x['estimated_row_count'] == 0 else x['size_bytes'] / x['estimated_row_count'],
                axis=1
            )
            
            # Format for display
            tables_df['avg_row_size'] = tables_df['avg_row_size'].apply(lambda x: f"{x:.2f} bytes")
            
            # Reorder and rename columns
            tables_df = tables_df[['table_name', 'estimated_row_count', 'total_size', 'avg_row_size']]
            tables_df.columns = ['Table', 'Estimated Rows', 'Total Size', 'Avg Row Size']
            
            st.dataframe(tables_df, use_container_width=True)
    
    # Data Explorer Tab
    with tabs[1]:
        st.header("Data Explorer")
        
        # Create filter controls
        with st.expander("Filter Controls", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                # Date range filter
                st.write("Date Range")
                start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
                end_date = st.date_input("End Date", datetime.now())
                
                # Convert to datetime
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
                
                # Source filter
                st.write("Sources")
                selected_sources = st.multiselect("Select Sources", metadata['sources'])
                
                # Priority filter
                st.write("Priority")
                selected_priorities = st.multiselect("Select Priorities", metadata['priorities'])
            
            with col2:
                # Model filter
                st.write("Models")
                selected_models = st.multiselect("Select Models", metadata['models'])
                
                # Score range filter
                st.write("Sentiment Score Range")
                score_range = st.slider("Score Range", -1.0, 1.0, (-1.0, 1.0), 0.1)
                min_score, max_score = score_range
                
                # Ticker filter
                st.write("Tickers")
                selected_tickers = st.multiselect("Select Tickers", metadata['tickers'])
                
                # Row limit
                st.write("Limit")
                row_limit = st.number_input("Maximum Rows", 100, 10000, 1000)
        
        # Build filters
        filters = {}
        
        if start_date:
            filters['start_date'] = start_datetime
        
        if end_date:
            filters['end_date'] = end_datetime
        
        if selected_sources:
            filters['sources'] = selected_sources
        
        if selected_priorities:
            filters['priorities'] = selected_priorities
        
        if selected_models:
            filters['models'] = selected_models
        
        if min_score > -1.0:
            filters['min_score'] = min_score
        
        if max_score < 1.0:
            filters['max_score'] = max_score
        
        if selected_tickers:
            filters['tickers'] = selected_tickers
        
        # Data selection tabs
        data_tabs = st.tabs(["Sentiment Events", "Ticker Sentiments"])
        
        # Sentiment Events tab
        with data_tabs[0]:
            if st.button("Fetch Sentiment Events"):
                with st.spinner("Fetching data..."):
                    events_df = get_sentiment_events(engine, limit=row_limit, filters=filters)
                    
                    if not events_df.empty:
                        st.success(f"Found {len(events_df)} records")
                        
                        # Format tickers column to display as comma-separated list
                        events_df['tickers'] = events_df['tickers'].apply(lambda x: ', '.join(t for t in x if t) if isinstance(x, list) else x)
                        
                        # Display data
                        st.dataframe(events_df)
                        
                        # Allow download as CSV
                        csv = events_df.to_csv(index=False)
                        st.download_button(
                            label="Download as CSV",
                            data=csv,
                            file_name=f"sentiment_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                        
                        # Visualizations
                        st.subheader("Visualizations")
                        
                        # Bar charts for categorical data
                        if not events_df.empty:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Source distribution
                                source_counts = events_df['source'].value_counts().reset_index()
                                source_counts.columns = ['source', 'count']
                                
                                fig_source = px.bar(
                                    source_counts, 
                                    x='source', 
                                    y='count',
                                    title="Source Distribution",
                                    color_discrete_sequence=['#4CAF50']
                                )
                                st.plotly_chart(fig_source, use_container_width=True)
                            
                            with col2:
                                # Priority distribution
                                priority_counts = events_df['priority'].value_counts().reset_index()
                                priority_counts.columns = ['priority', 'count']
                                
                                fig_priority = px.bar(
                                    priority_counts, 
                                    x='priority', 
                                    y='count',
                                    title="Priority Distribution",
                                    color_discrete_sequence=['#2196F3']
                                )
                                st.plotly_chart(fig_priority, use_container_width=True)
                            
                            # Sentiment score histogram
                            fig_sentiment = px.histogram(
                                events_df, 
                                x='sentiment_score',
                                title="Sentiment Score Distribution",
                                nbins=20,
                                color_discrete_sequence=['#FFC107']
                            )
                            st.plotly_chart(fig_sentiment, use_container_width=True)
                            
                            # Time series
                            if 'timestamp' in events_df.columns:
                                # Convert to datetime if it's not already
                                events_df['timestamp'] = pd.to_datetime(events_df['timestamp'])
                                
                                # Group by day
                                daily_counts = events_df.resample('D', on='timestamp').size().reset_index()
                                daily_counts.columns = ['timestamp', 'count']
                                
                                fig_time = px.line(
                                    daily_counts, 
                                    x='timestamp', 
                                    y='count',
                                    title="Events Over Time",
                                    labels={'timestamp': 'Date', 'count': 'Event Count'},
                                    color_discrete_sequence=['#673AB7']
                                )
                                st.plotly_chart(fig_time, use_container_width=True)
                    else:
                        st.warning("No data found with the current filters")
        
        # Ticker Sentiments tab
        with data_tabs[1]:
            if st.button("Fetch Ticker Sentiments"):
                with st.spinner("Fetching data..."):
                    ticker_df = get_ticker_sentiments(engine, limit=row_limit, filters=filters)
                    
                    if not ticker_df.empty:
                        st.success(f"Found {len(ticker_df)} records")
                        
                        # Display data
                        st.dataframe(ticker_df)
                        
                        # Allow download as CSV
                        csv = ticker_df.to_csv(index=False)
                        st.download_button(
                            label="Download as CSV",
                            data=csv,
                            file_name=f"ticker_sentiments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                        
                        # Visualizations
                        st.subheader("Visualizations")
                        
                        # Top tickers by count
                        ticker_counts = ticker_df['ticker'].value_counts().head(10).reset_index()
                        ticker_counts.columns = ['ticker', 'count']
                        
                        fig_tickers = px.bar(
                            ticker_counts, 
                            x='ticker', 
                            y='count',
                            title="Top 10 Tickers by Mention Count",
                            color_discrete_sequence=['#4CAF50']
                        )
                        st.plotly_chart(fig_tickers, use_container_width=True)
                        
                        # Average sentiment by ticker
                        ticker_sentiments = ticker_df.groupby('ticker')['sentiment_score'].mean().reset_index()
                        ticker_sentiments = ticker_sentiments.sort_values('sentiment_score', ascending=False)
                        
                        # Take top 5 positive and top 5 negative
                        top_positive = ticker_sentiments.head(5)
                        top_negative = ticker_sentiments.tail(5)
                        top_tickers = pd.concat([top_positive, top_negative])
                        
                        fig_sentiment = px.bar(
                            top_tickers, 
                            x='ticker', 
                            y='sentiment_score',
                            title="Top Positive and Negative Tickers",
                            color='sentiment_score',
                            color_continuous_scale=['#F44336', '#FFC107', '#4CAF50']
                        )
                        st.plotly_chart(fig_sentiment, use_container_width=True)
                        
                        # Sentiment distribution
                        fig_dist = px.histogram(
                            ticker_df, 
                            x='sentiment_score',
                            title="Ticker Sentiment Score Distribution",
                            nbins=20,
                            color_discrete_sequence=['#2196F3']
                        )
                        st.plotly_chart(fig_dist, use_container_width=True)
                    else:
                        st.warning("No data found with the current filters")
    
    # Ticker Analysis Tab
    with tabs[2]:
        st.header("Ticker Analysis")
        
        selected_ticker = st.selectbox("Select Ticker for Analysis", metadata['tickers'] if metadata['tickers'] else ["No tickers found"])
        time_period = st.radio("Time Period", ["Last 30 days", "Last 90 days", "Last 180 days", "All Time"], horizontal=True)
        
        days_map = {
            "Last 30 days": 30,
            "Last 90 days": 90,
            "Last 180 days": 180,
            "All Time": 1000  # A large number to represent all time
        }
        days = days_map[time_period]
        
        if st.button("Analyze Ticker"):
            with st.spinner(f"Analyzing {selected_ticker}..."):
                summary_df = get_ticker_sentiment_summary(engine, selected_ticker)
                
                if not summary_df.empty:
                    # Display summary card
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        avg_score = summary_df['avg_score'].values[0]
                        if avg_score > 0:
                            sentiment = "Positive"
                            color = "#4CAF50"
                        elif avg_score < 0:
                            sentiment = "Negative"
                            color = "#F44336"
                        else:
                            sentiment = "Neutral"
                            color = "#FFC107"
                        
                        st.markdown(f"<h2 style='text-align: center; color: {color};'>{sentiment}</h2>", unsafe_allow_html=True)
                        st.metric("Average Score", f"{avg_score:.4f}")
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        mention_count = summary_df['count'].values[0]
                        st.metric("Mention Count", f"{mention_count:,}")
                        time_range = f"{(summary_df['last_seen'].values[0] - summary_df['first_seen'].values[0]).days + 1} days"
                        st.metric("Time Range", time_range)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                        min_score = summary_df['min_score'].values[0]
                        max_score = summary_df['max_score'].values[0]
                        st.metric("Min Score", f"{min_score:.4f}")
                        st.metric("Max Score", f"{max_score:.4f}")
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Sentiment trend
                    st.subheader("Sentiment Trend")
                    fig = plot_ticker_sentiment_trend(engine, selected_ticker, days=days)
                    
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"No data available for {selected_ticker} in the selected time period")
                    
                    # Sources
                    if 'sources' in summary_df.columns:
                        st.subheader("Sources")
                        sources = summary_df['sources'].values[0]
                        st.write(", ".join(sources) if isinstance(sources, list) else sources)
                    
                    # Models
                    if 'models' in summary_df.columns:
                        st.subheader("Models Used")
                        models = summary_df['models'].values[0]
                        st.write(", ".join(models) if isinstance(models, list) else models)
                else:
                    st.warning(f"No data found for ticker {selected_ticker}")
    
    # Insights Tab
    with tabs[3]:
        st.header("Data Insights")
        
        if st.button("Generate Insights"):
            with st.spinner("Analyzing data and generating insights..."):
                insights = generate_data_insights(engine)
                
                if insights:
                    # Top positive tickers
                    st.subheader("Top Positive Sentiment Tickers (Last 30 Days)")
                    if not insights['top_positive'].empty:
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            fig = px.bar(
                                insights['top_positive'],
                                x='ticker',
                                y='avg_score',
                                title="Top Positive Sentiment Tickers",
                                color='avg_score',
                                color_continuous_scale=['#FFC107', '#4CAF50'],
                                hover_data=['count']
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.dataframe(insights['top_positive'])
                    else:
                        st.info("No data available for top positive tickers")
                    
                    # Top negative tickers
                    st.subheader("Top Negative Sentiment Tickers (Last 30 Days)")
                    if not insights['top_negative'].empty:
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            fig = px.bar(
                                insights['top_negative'],
                                x='ticker',
                                y='avg_score',
                                title="Top Negative Sentiment Tickers",
                                color='avg_score',
                                color_continuous_scale=['#F44336', '#FFC107'],
                                hover_data=['count']
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.dataframe(insights['top_negative'])
                    else:
                        st.info("No data available for top negative tickers")
                    
                    # Most volatile tickers
                    st.subheader("Most Volatile Sentiment Tickers (Last 30 Days)")
                    if not insights['most_volatile'].empty:
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            fig = px.bar(
                                insights['most_volatile'],
                                x='ticker',
                                y='volatility',
                                title="Most Volatile Sentiment Tickers",
                                color='avg_score',
                                color_continuous_scale=['#F44336', '#FFC107', '#4CAF50'],
                                hover_data=['count']
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.dataframe(insights['most_volatile'])
                    else:
                        st.info("No data available for volatile tickers")
                    
                    # Most mentioned tickers
                    st.subheader("Most Mentioned Tickers (Last 30 Days)")
                    if not insights['most_mentioned'].empty:
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            fig = px.bar(
                                insights['most_mentioned'],
                                x='ticker',
                                y='count',
                                title="Most Mentioned Tickers",
                                color='avg_score',
                                color_continuous_scale=['#F44336', '#FFC107', '#4CAF50'],
                                hover_data=['avg_score']
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.dataframe(insights['most_mentioned'])
                    else:
                        st.info("No data available for most mentioned tickers")
                    
                    # Source statistics
                    st.subheader("Source Statistics (Last 30 Days)")
                    if not insights['source_stats'].empty:
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            fig = px.bar(
                                insights['source_stats'],
                                x='source',
                                y='count',
                                title="Event Sources",
                                color='avg_score',
                                color_continuous_scale=['#F44336', '#FFC107', '#4CAF50'],
                                hover_data=['avg_score']
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.dataframe(insights['source_stats'])
                    else:
                        st.info("No data available for source statistics")
                    
                    # Daily trend
                    st.subheader("Daily Trend (Last 30 Days)")
                    if not insights['daily_trend'].empty:
                        # Convert date to datetime if needed
                        if not pd.api.types.is_datetime64_any_dtype(insights['daily_trend']['date']):
                            insights['daily_trend']['date'] = pd.to_datetime(insights['daily_trend']['date'])
                        
                        # Create dual axis chart
                        fig = px.line(
                            insights['daily_trend'],
                            x='date',
                            y='avg_score',
                            title="Daily Sentiment Trend",
                            labels={'avg_score': 'Average Sentiment Score', 'date': 'Date'},
                            color_discrete_sequence=['#4CAF50']
                        )
                        
                        # Add volume as bars
                        fig.add_trace(
                            go.Bar(
                                x=insights['daily_trend']['date'],
                                y=insights['daily_trend']['count'],
                                name='Event Count',
                                yaxis='y2',
                                marker_color='rgba(33, 150, 243, 0.3)',
                                opacity=0.7
                            )
                        )
                        
                        # Update layout for dual axis
                        fig.update_layout(
                            yaxis=dict(
                                title='Sentiment Score',
                                range=[-1, 1]
                            ),
                            yaxis2=dict(
                                title='Event Count',
                                overlaying='y',
                                side='right',
                                showgrid=False
                            ),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            )
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No data available for daily trend")
                else:
                    st.warning("Failed to generate insights. Check database connection.")
    
    # Maintenance Tab
    with tabs[4]:
        st.header("Database Maintenance")
        
        st.warning("⚠️ Maintenance operations can modify or delete data. Use with caution!")
        
        # Maintenance operations
        st.subheader("Database Operations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown("### Data Retention")
            retention_days = st.number_input("Keep data for days", 7, 365, 90)
            
            if st.button("Delete Old Events"):
                with st.spinner("Deleting old events..."):
                    # Delete old events and their associated ticker sentiments
                    delete_query = f"""
                        WITH old_events AS (
                            SELECT id 
                            FROM sentiment_events 
                            WHERE timestamp < CURRENT_DATE - INTERVAL '{retention_days} days'
                        )
                        DELETE FROM ticker_sentiments 
                        WHERE event_id IN (SELECT id FROM old_events);
                        
                        DELETE FROM sentiment_events 
                        WHERE timestamp < CURRENT_DATE - INTERVAL '{retention_days} days';
                    """
                    
                    result = execute_maintenance(engine, delete_query, "Delete Old Events")
                    
                    if result['success']:
                        st.success(f"Successfully deleted old events. Affected {result['rows_affected']} rows. Time: {result['duration']}")
                    else:
                        st.error(f"Error deleting old events: {result.get('error', 'Unknown error')}")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            st.markdown("### Database Optimization")
            
            if st.button("Vacuum Database"):
                with st.spinner("Vacuuming database..."):
                    # VACUUM ANALYZE to reclaim space and update statistics
                    vacuum_query = "VACUUM ANALYZE;"
                    
                    result = execute_maintenance(engine, vacuum_query, "Vacuum Database")
                    
                    if result['success']:
                        st.success(f"Successfully vacuumed database. Time: {result['duration']}")
                    else:
                        st.error(f"Error vacuuming database: {result.get('error', 'Unknown error')}")
            
            if st.button("Reindex Database"):
                with st.spinner("Reindexing database..."):
                    # Reindex all tables
                    reindex_query = """
                        REINDEX TABLE sentiment_events;
                        REINDEX TABLE ticker_sentiments;
                    """
                    
                    result = execute_maintenance(engine, reindex_query, "Reindex Database")
                    
                    if result['success']:
                        st.success(f"Successfully reindexed database. Time: {result['duration']}")
                    else:
                        st.error(f"Error reindexing database: {result.get('error', 'Unknown error')}")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Custom SQL
        st.subheader("Custom SQL Query")
        st.warning("⚠️ Be careful with custom SQL queries. They can potentially damage your database if not used correctly.")
        
        sql_query = st.text_area("Enter SQL Query", height=150)
        execute_button = st.button("Execute Query")
        
        if execute_button and sql_query:
            with st.spinner("Executing query..."):
                result = execute_custom_query(engine, sql_query)
                
                if result['success']:
                    if result.get('type') == 'select':
                        st.success(f"Query executed successfully. Returned {result['rows']} rows. Time: {result['duration']}")
                        
                        if not result['data'].empty:
                            st.dataframe(result['data'])
                            
                            # Allow download as CSV
                            csv = result['data'].to_csv(index=False)
                            st.download_button(
                                label="Download Results as CSV",
                                data=csv,
                                file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                    else:
                        st.success(f"Query executed successfully. Affected {result['rows_affected']} rows. Time: {result['duration']}")
                else:
                    st.error(f"Error executing query: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()