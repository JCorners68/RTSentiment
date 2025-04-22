#!/usr/bin/env python3
"""
Data Viewer for RT Sentiment Dashboard using PostgreSQL
This module provides the database-backed data viewer functionality
"""
import os
import time
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import base64

# Configuration
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "sentiment")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres") 
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

# Data retention period in days
RETENTION_DAYS = int(os.environ.get("DATA_RETENTION_DAYS", "30"))

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

# Get sentiment data with filters
def get_sentiment_data(time_range='1d', ticker=None, source=None, model=None, 
                      sentiment_min=None, sentiment_max=None, limit=1000):
    """
    Query sentiment data from PostgreSQL with filters
    
    Parameters:
    - time_range: '1h', '1d', '1w', '1m' or 'all'
    - ticker: Filter by ticker symbol
    - source: Filter by source (e.g., 'news', 'reddit')
    - model: Filter by model (e.g., 'finbert')
    - sentiment_min: Minimum sentiment score
    - sentiment_max: Maximum sentiment score
    - limit: Maximum number of records to return
    
    Returns:
    - DataFrame with sentiment data
    """
    try:
        conn = get_postgres_conn()
        if not conn:
            return pd.DataFrame()
        
        # Build query with filters
        query = """
        SELECT 
            id,
            timestamp,
            ticker,
            sentiment,
            confidence,
            source,
            model,
            article_id,
            article_title
        FROM sentiment_results
        WHERE 1=1
        """
        
        params = []
        
        # Apply time range filter
        if time_range != 'all':
            if time_range == '1h':
                query += " AND timestamp > NOW() - INTERVAL '1 hour'"
            elif time_range == '1d':
                query += " AND timestamp > NOW() - INTERVAL '1 day'"
            elif time_range == '1w':
                query += " AND timestamp > NOW() - INTERVAL '1 week'"
            elif time_range == '1m':
                query += " AND timestamp > NOW() - INTERVAL '1 month'"
        
        # Apply ticker filter
        if ticker:
            query += " AND ticker = %s"
            params.append(ticker)
        
        # Apply source filter
        if source:
            query += " AND source = %s"
            params.append(source)
        
        # Apply model filter
        if model:
            query += " AND model = %s"
            params.append(model)
        
        # Apply sentiment range filters
        if sentiment_min is not None:
            query += " AND sentiment >= %s"
            params.append(sentiment_min)
        
        if sentiment_max is not None:
            query += " AND sentiment <= %s"
            params.append(sentiment_max)
        
        # Add order by and limit
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        # Execute query
        with conn.cursor() as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            
            # Get column names
            columns = [desc[0] for desc in cur.description]
            
            # Create DataFrame
            if results:
                df = pd.DataFrame(results, columns=columns)
                return df
            else:
                return pd.DataFrame(columns=columns)
    
    except Exception as e:
        st.error(f"Error querying data: {e}")
        return pd.DataFrame()
    
    finally:
        if conn:
            conn.close()

# Get aggregated sentiment data for visualization
def get_sentiment_aggregates(groupby='ticker', time_range='1d'):
    """
    Get aggregated sentiment data grouped by the specified field
    
    Parameters:
    - groupby: Field to group by ('ticker', 'source', 'model')
    - time_range: '1h', '1d', '1w', '1m' or 'all'
    
    Returns:
    - DataFrame with aggregated data
    """
    try:
        conn = get_postgres_conn()
        if not conn:
            return pd.DataFrame()
        
        # Validate groupby parameter
        valid_groupby = ['ticker', 'source', 'model']
        if groupby not in valid_groupby:
            groupby = 'ticker'  # Default to ticker
        
        # Build query
        query = sql.SQL("""
        SELECT 
            {groupby},
            COUNT(*) as count,
            AVG(sentiment) as avg_sentiment,
            MIN(sentiment) as min_sentiment,
            MAX(sentiment) as max_sentiment,
            AVG(confidence) as avg_confidence
        FROM sentiment_results
        WHERE 1=1
        """).format(groupby=sql.Identifier(groupby))
        
        query_str = query.as_string(conn)
        params = []
        
        # Apply time range filter
        if time_range != 'all':
            if time_range == '1h':
                query_str += " AND timestamp > NOW() - INTERVAL '1 hour'"
            elif time_range == '1d':
                query_str += " AND timestamp > NOW() - INTERVAL '1 day'"
            elif time_range == '1w':
                query_str += " AND timestamp > NOW() - INTERVAL '1 week'"
            elif time_range == '1m':
                query_str += " AND timestamp > NOW() - INTERVAL '1 month'"
        
        # Complete query with groupby and ordering
        query_str += f" GROUP BY {groupby} ORDER BY count DESC"
        
        # Execute query
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query_str, params)
            results = cur.fetchall()
            
            # Convert to DataFrame
            if results:
                df = pd.DataFrame(results)
                return df
            else:
                return pd.DataFrame(columns=[groupby, 'count', 'avg_sentiment', 
                                           'min_sentiment', 'max_sentiment', 'avg_confidence'])
    
    except Exception as e:
        st.error(f"Error getting aggregated data: {e}")
        return pd.DataFrame()
    
    finally:
        if conn:
            conn.close()

# Get sentiment trends over time
def get_sentiment_trends(ticker=None, source=None, model=None, 
                         interval='hour', time_range='1d'):
    """
    Get sentiment trends over time
    
    Parameters:
    - ticker: Filter by ticker symbol
    - source: Filter by source
    - model: Filter by model
    - interval: 'minute', 'hour', 'day'
    - time_range: '1h', '1d', '1w', '1m' or 'all'
    
    Returns:
    - DataFrame with time series data
    """
    try:
        conn = get_postgres_conn()
        if not conn:
            return pd.DataFrame()
        
        # Determine time bucket based on interval
        if interval == 'minute':
            time_bucket = "date_trunc('minute', timestamp)"
        elif interval == 'hour':
            time_bucket = "date_trunc('hour', timestamp)"
        elif interval == 'day':
            time_bucket = "date_trunc('day', timestamp)"
        else:
            time_bucket = "date_trunc('hour', timestamp)"  # Default to hour
            
        # Build query
        query = f"""
        SELECT 
            {time_bucket} as time_bucket,
            COUNT(*) as count,
            AVG(sentiment) as avg_sentiment,
            AVG(confidence) as avg_confidence
        FROM sentiment_results
        WHERE 1=1
        """
        
        params = []
        
        # Apply ticker filter
        if ticker:
            query += " AND ticker = %s"
            params.append(ticker)
        
        # Apply source filter
        if source:
            query += " AND source = %s"
            params.append(source)
        
        # Apply model filter
        if model:
            query += " AND model = %s"
            params.append(model)
        
        # Apply time range filter
        if time_range != 'all':
            if time_range == '1h':
                query += " AND timestamp > NOW() - INTERVAL '1 hour'"
            elif time_range == '1d':
                query += " AND timestamp > NOW() - INTERVAL '1 day'"
            elif time_range == '1w':
                query += " AND timestamp > NOW() - INTERVAL '1 week'"
            elif time_range == '1m':
                query += " AND timestamp > NOW() - INTERVAL '1 month'"
        
        # Complete query with groupby and ordering
        query += f" GROUP BY time_bucket ORDER BY time_bucket ASC"
        
        # Execute query
        with conn.cursor() as cur:
            cur.execute(query, params)
            results = cur.fetchall()
            
            # Get column names
            columns = [desc[0] for desc in cur.description]
            
            # Create DataFrame
            if results:
                df = pd.DataFrame(results, columns=columns)
                return df
            else:
                return pd.DataFrame(columns=columns)
    
    except Exception as e:
        st.error(f"Error getting trend data: {e}")
        return pd.DataFrame()
    
    finally:
        if conn:
            conn.close()

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

# Purge old sentiment data
def purge_old_data():
    """Purge sentiment data older than retention period"""
    try:
        conn = get_postgres_conn()
        if not conn:
            return 0
        
        # Execute delete query
        with conn.cursor() as cur:
            cur.execute(f"""
            DELETE FROM sentiment_results 
            WHERE timestamp < NOW() - INTERVAL '{RETENTION_DAYS} days'
            """)
            deleted_count = cur.rowcount
            conn.commit()
            
        return deleted_count
    
    except Exception as e:
        st.error(f"Error purging old data: {e}")
        return 0
    
    finally:
        if conn:
            conn.close()

# Get database statistics
def get_db_stats():
    """Get database statistics"""
    try:
        conn = get_postgres_conn()
        if not conn:
            return {}
        
        stats = {}
        
        # Get total record count
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sentiment_results")
            stats['total_records'] = cur.fetchone()[0]
        
        # Get record count by time period
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sentiment_results WHERE timestamp > NOW() - INTERVAL '1 hour'")
            stats['last_hour'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM sentiment_results WHERE timestamp > NOW() - INTERVAL '1 day'")
            stats['last_day'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM sentiment_results WHERE timestamp > NOW() - INTERVAL '1 week'")
            stats['last_week'] = cur.fetchone()[0]
        
        # Get ticker counts
        with conn.cursor() as cur:
            cur.execute("""
            SELECT ticker, COUNT(*) as count 
            FROM sentiment_results 
            GROUP BY ticker 
            ORDER BY count DESC 
            LIMIT 5
            """)
            stats['top_tickers'] = dict(cur.fetchall())
        
        # Get source counts
        with conn.cursor() as cur:
            cur.execute("""
            SELECT source, COUNT(*) as count 
            FROM sentiment_results 
            GROUP BY source 
            ORDER BY count DESC
            """)
            stats['sources'] = dict(cur.fetchall())
        
        # Get model counts
        with conn.cursor() as cur:
            cur.execute("""
            SELECT model, COUNT(*) as count 
            FROM sentiment_results 
            GROUP BY model 
            ORDER BY count DESC
            """)
            stats['models'] = dict(cur.fetchall())
        
        # Get average sentiment by ticker
        with conn.cursor() as cur:
            cur.execute("""
            SELECT ticker, AVG(sentiment) as avg_sentiment 
            FROM sentiment_results 
            GROUP BY ticker 
            ORDER BY avg_sentiment DESC 
            LIMIT 5
            """)
            stats['top_positive_tickers'] = dict(cur.fetchall())
            
            cur.execute("""
            SELECT ticker, AVG(sentiment) as avg_sentiment 
            FROM sentiment_results 
            GROUP BY ticker 
            ORDER BY avg_sentiment ASC 
            LIMIT 5
            """)
            stats['top_negative_tickers'] = dict(cur.fetchall())
        
        return stats
    
    except Exception as e:
        st.error(f"Error getting database statistics: {e}")
        return {}
    
    finally:
        if conn:
            conn.close()

# Main function for data viewer page
def render_data_viewer():
    """Render the data viewer page"""
    st.title("Sentiment Data Explorer")
    
    # Check database connection
    conn = get_postgres_conn()
    if not conn:
        st.error("⚠️ Could not connect to PostgreSQL database")
        st.info("Please check your database configuration and make sure PostgreSQL is running.")
        
        # Show connection settings
        with st.expander("Database Connection Settings"):
            st.code(f"""
            Host: {POSTGRES_HOST}
            Database: {POSTGRES_DB}
            Port: {POSTGRES_PORT}
            User: {POSTGRES_USER}
            Password: {'*' * len(POSTGRES_PASSWORD)}
            """)
        return
    conn.close()
    
    # Get filter options
    tickers, sources, models = get_filter_options()
    
    # Create tabs
    tabs = st.tabs([
        "📊 Dashboard", 
        "🔍 Data Browser", 
        "📈 Trends", 
        "⚙️ Administration"
    ])
    
    # Dashboard Tab
    with tabs[0]:
        st.header("Sentiment Dashboard")
        
        # Get database statistics
        stats = get_db_stats()
        
        if not stats:
            st.warning("No data available in database")
        else:
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Total Records", f"{stats['total_records']:,}")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col2:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Last Hour", f"{stats['last_hour']:,}", 
                         delta=f"{stats['last_hour']/max(1, stats['total_records'])*100:.1f}%")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col3:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Last Day", f"{stats['last_day']:,}", 
                         delta=f"{stats['last_day']/max(1, stats['total_records'])*100:.1f}%")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col4:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.metric("Last Week", f"{stats['last_week']:,}", 
                         delta=f"{stats['last_week']/max(1, stats['total_records'])*100:.1f}%")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Display charts
            st.subheader("Sentiment Distribution by Ticker")
            
            # Get aggregated data for tickers
            ticker_data = get_sentiment_aggregates(groupby='ticker', time_range='1w')
            
            if not ticker_data.empty:
                # Show ticker sentiment chart
                fig = px.bar(
                    ticker_data.head(10), 
                    x='ticker', 
                    y='avg_sentiment',
                    error_y='avg_confidence',
                    color='avg_sentiment',
                    color_continuous_scale='RdYlGn',
                    labels={'avg_sentiment': 'Average Sentiment', 'ticker': 'Ticker'},
                    title='Top 10 Tickers by Volume - Average Sentiment'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Show ticker volume
                fig2 = px.bar(
                    ticker_data.head(10),
                    x='ticker',
                    y='count',
                    color='avg_sentiment',
                    color_continuous_scale='RdYlGn',
                    labels={'count': 'Number of Mentions', 'ticker': 'Ticker'},
                    title='Top 10 Tickers by Volume - Mention Count'
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Show source distribution
            st.subheader("Data Sources")
            if 'sources' in stats:
                source_df = pd.DataFrame({
                    'source': list(stats['sources'].keys()),
                    'count': list(stats['sources'].values())
                })
                
                if not source_df.empty:
                    fig3 = px.pie(
                        source_df,
                        values='count',
                        names='source',
                        title='Distribution by Source',
                        hole=0.4
                    )
                    st.plotly_chart(fig3, use_container_width=True)
    
    # Data Browser Tab
    with tabs[1]:
        st.header("Data Browser")
        
        # Filters in sidebar or expander
        with st.expander("Filters", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                # Time range filter
                time_range = st.selectbox(
                    "Time Range",
                    options=['1h', '1d', '1w', '1m', 'all'],
                    format_func=lambda x: {
                        '1h': 'Last Hour',
                        '1d': 'Last Day',
                        '1w': 'Last Week',
                        '1m': 'Last Month',
                        'all': 'All Time'
                    }.get(x, x),
                    index=1  # Default to last day
                )
                
                # Ticker filter
                ticker_filter = st.selectbox(
                    "Ticker",
                    options=[None] + tickers,
                    format_func=lambda x: "All Tickers" if x is None else x
                )
                
                # Sentiment range
                sentiment_range = st.slider(
                    "Sentiment Range",
                    min_value=-1.0,
                    max_value=1.0,
                    value=(-1.0, 1.0),
                    step=0.1
                )
            
            with col2:
                # Source filter
                source_filter = st.selectbox(
                    "Source",
                    options=[None] + sources,
                    format_func=lambda x: "All Sources" if x is None else x
                )
                
                # Model filter
                model_filter = st.selectbox(
                    "Model",
                    options=[None] + models,
                    format_func=lambda x: "All Models" if x is None else x
                )
                
                # Limit
                limit = st.number_input(
                    "Max Records",
                    min_value=100,
                    max_value=10000,
                    value=1000,
                    step=100
                )
        
        # Get data based on filters
        df = get_sentiment_data(
            time_range=time_range,
            ticker=ticker_filter,
            source=source_filter,
            model=model_filter,
            sentiment_min=sentiment_range[0],
            sentiment_max=sentiment_range[1],
            limit=limit
        )
        
        # Display results
        if df.empty:
            st.warning("No data found matching the selected filters")
        else:
            # Summary
            st.markdown(f"Found **{len(df):,}** records")
            
            # Display data
            st.dataframe(df, use_container_width=True)
            
            # Download options
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV download
                csv = df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="sentiment_data_{time_range}.csv" class="download-button">Download CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
            
            with col2:
                # JSON download
                json_str = df.to_json(orient='records', date_format='iso')
                b64_json = base64.b64encode(json_str.encode()).decode()
                href_json = f'<a href="data:application/json;base64,{b64_json}" download="sentiment_data_{time_range}.json" class="download-button">Download JSON</a>'
                st.markdown(href_json, unsafe_allow_html=True)
    
    # Trends Tab
    with tabs[2]:
        st.header("Sentiment Trends")
        
        # Filter controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trend_ticker = st.selectbox(
                "Ticker for Trend",
                options=[None] + tickers,
                format_func=lambda x: "All Tickers" if x is None else x,
                key="trend_ticker"
            )
        
        with col2:
            trend_source = st.selectbox(
                "Source for Trend",
                options=[None] + sources,
                format_func=lambda x: "All Sources" if x is None else x,
                key="trend_source"
            )
        
        with col3:
            trend_model = st.selectbox(
                "Model for Trend",
                options=[None] + models,
                format_func=lambda x: "All Models" if x is None else x,
                key="trend_model"
            )
        
        # Time controls
        col1, col2 = st.columns(2)
        
        with col1:
            trend_interval = st.selectbox(
                "Time Interval",
                options=['minute', 'hour', 'day'],
                index=1  # Default to hour
            )
        
        with col2:
            trend_time_range = st.selectbox(
                "Time Range for Trend",
                options=['1h', '1d', '1w', '1m', 'all'],
                format_func=lambda x: {
                    '1h': 'Last Hour',
                    '1d': 'Last Day',
                    '1w': 'Last Week',
                    '1m': 'Last Month',
                    'all': 'All Time'
                }.get(x, x),
                index=1  # Default to last day
            )
        
        # Get trend data
        trend_data = get_sentiment_trends(
            ticker=trend_ticker,
            source=trend_source,
            model=trend_model,
            interval=trend_interval,
            time_range=trend_time_range
        )
        
        if trend_data.empty:
            st.warning("No trend data found matching the selected filters")
        else:
            # Display trend chart
            fig = go.Figure()
            
            # Add sentiment line
            fig.add_trace(go.Scatter(
                x=trend_data['time_bucket'],
                y=trend_data['avg_sentiment'],
                mode='lines+markers',
                name='Average Sentiment',
                line=dict(color='#4CAF50', width=3),
                marker=dict(size=8),
                hovertemplate='%{x}<br>Sentiment: %{y:.2f}'
            ))
            
            # Add count bars
            fig.add_trace(go.Bar(
                x=trend_data['time_bucket'],
                y=trend_data['count'],
                name='Event Count',
                marker=dict(color='rgba(33, 150, 243, 0.3)'),
                hovertemplate='%{x}<br>Count: %{y}',
                yaxis='y2'
            ))
            
            # Update layout
            fig.update_layout(
                title=f"Sentiment Trend over Time ({trend_interval} intervals)",
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
            
            # Display trend data
            with st.expander("Trend Data"):
                st.dataframe(trend_data)
    
    # Administration Tab
    with tabs[3]:
        st.header("Database Administration")
        
        # Data retention settings
        st.subheader("Data Retention Policy")
        
        retention = st.number_input(
            "Retention Period (days)",
            min_value=1,
            max_value=365,
            value=RETENTION_DAYS
        )
        
        if st.button("Apply Retention Policy"):
            deleted_count = purge_old_data()
            st.success(f"Successfully purged {deleted_count} records older than {RETENTION_DAYS} days")
        
        # Database stats
        st.subheader("Database Statistics")
        
        stats = get_db_stats()
        
        if stats:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Records", f"{stats['total_records']:,}")
                st.metric("Records Last Hour", f"{stats['last_hour']:,}")
            
            with col2:
                st.metric("Records Last Day", f"{stats['last_day']:,}")
                st.metric("Records Last Week", f"{stats['last_week']:,}")
            
            with col3:
                # Calculate database growth
                daily_growth = stats['last_day']
                monthly_estimate = daily_growth * 30
                
                st.metric("Estimated Daily Growth", f"{daily_growth:,}")
                st.metric("Estimated Monthly Growth", f"{monthly_estimate:,}")
        
        # Advanced operations
        st.subheader("Advanced Operations")
        
        with st.expander("Database Export"):
            st.markdown("""
            Export the entire sentiment database to CSV or JSON format.
            
            ⚠️ **Warning**: This operation may take a long time for large databases.
            """)
            
            if st.button("Export Full Database"):
                try:
                    # Get all data
                    conn = get_postgres_conn()
                    
                    if not conn:
                        st.error("Could not connect to database")
                    else:
                        with conn.cursor() as cur:
                            cur.execute("SELECT * FROM sentiment_results")
                            results = cur.fetchall()
                            
                            # Get column names
                            columns = [desc[0] for desc in cur.description]
                            
                            # Create DataFrame
                            if results:
                                full_df = pd.DataFrame(results, columns=columns)
                                
                                # Offer download options
                                csv = full_df.to_csv(index=False)
                                b64 = base64.b64encode(csv.encode()).decode()
                                href = f'<a href="data:file/csv;base64,{b64}" download="full_sentiment_db.csv" class="download-button">Download Full Database (CSV)</a>'
                                st.markdown(href, unsafe_allow_html=True)
                                
                                st.success(f"Successfully exported {len(full_df)} records")
                            else:
                                st.warning("No data found in database")
                        
                        conn.close()
                
                except Exception as e:
                    st.error(f"Error exporting database: {e}")
        
        with st.expander("Database Maintenance"):
            st.markdown("""
            Run database maintenance operations to optimize performance