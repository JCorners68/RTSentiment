#!/usr/bin/env python3
"""
Advanced Query Interface for Sentiment Analysis System
- Predefined queries with templates
- Custom SQL editor
- Visualization of query results
- Export functionality
"""
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlalchemy
from sqlalchemy import create_engine, text
import time
import io
import base64
import re
import json

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
    
    /* Query template card */
    .query-card {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .query-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* SQL editor */
    .sql-editor {
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
        font-size: 14px;
        line-height: 1.5;
        padding: 10px;
        border-radius: 5px;
        background-color: #f8f9fa;
        color: #212529;
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
    
    /* SQL syntax highlighting */
    .keyword {
        color: #0033B3;
        font-weight: bold;
    }
    .string {
        color: #067D17;
    }
    .number {
        color: #1750EB;
    }
    .comment {
        color: #8C8C8C;
        font-style: italic;
    }
    .function {
        color: #871094;
    }
    
    /* Result tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e8eef1;
        border-radius: 8px 8px 0 0;
        padding: 8px 8px 0 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #cfd8dc;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 16px;
        color: #455a64 !important;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
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
def get_table_schema(engine, table_name):
    """Get the schema for a table"""
    try:
        with engine.connect() as conn:
            query = text(f"""
                SELECT 
                    column_name, 
                    data_type, 
                    column_default,
                    is_nullable
                FROM 
                    information_schema.columns
                WHERE 
                    table_name = :table_name
                ORDER BY 
                    ordinal_position
            """)
            
            df = pd.read_sql(query, conn, params={'table_name': table_name})
            return df
    except Exception as e:
        st.error(f"Error getting table schema: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_table_names(engine):
    """Get all table names in the database"""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    table_name
                FROM 
                    information_schema.tables
                WHERE 
                    table_schema = 'public'
                ORDER BY 
                    table_name
            """)
            
            df = pd.read_sql(query, conn)
            return df['table_name'].tolist()
    except Exception as e:
        st.error(f"Error getting table names: {e}")
        return []

def execute_query(engine, query_text, params=None):
    """Execute a query and return the results"""
    try:
        with engine.connect() as conn:
            start_time = time.time()
            result = pd.read_sql(text(query_text), conn, params=params)
            duration = time.time() - start_time
            
            return {
                'success': True,
                'data': result,
                'rows': len(result),
                'duration': duration,
                'columns': result.columns.tolist()
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def highlight_sql_syntax(sql_code):
    """Add HTML syntax highlighting to SQL code"""
    # Keywords
    keywords = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL',
        'ON', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'ALL',
        'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TABLE', 'VIEW',
        'INDEX', 'TRIGGER', 'PROCEDURE', 'FUNCTION', 'AS', 'IN', 'NOT', 'AND', 'OR',
        'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL', 'TRUE', 'FALSE', 'ASC', 'DESC',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'WITH', 'DISTINCT', 'COUNT', 'SUM',
        'AVG', 'MIN', 'MAX', 'CAST', 'COALESCE', 'EXTRACT', 'DATE', 'TIMESTAMP'
    ]
    
    # Create a regex pattern that matches whole words only
    pattern = r'\b(' + '|'.join(keywords) + r')\b'
    
    # Replace keywords with highlighted version (case-insensitive)
    highlighted = re.sub(pattern, r'<span class="keyword">\1</span>', sql_code, flags=re.IGNORECASE)
    
    # Highlight strings
    highlighted = re.sub(r"'([^']*)'", r"<span class='string'>'\1'</span>", highlighted)
    
    # Highlight numbers
    highlighted = re.sub(r'\b(\d+)\b', r'<span class="number">\1</span>', highlighted)
    
    # Highlight functions
    function_pattern = r'\b([a-zA-Z0-9_]+)(?=\()'
    highlighted = re.sub(function_pattern, r'<span class="function">\1</span>', highlighted)
    
    # Highlight comments
    highlighted = re.sub(r'--(.*)$', r'<span class="comment">--\1</span>', highlighted, flags=re.MULTILINE)
    
    # Wrap in a pre tag
    return f'<pre class="sql-editor">{highlighted}</pre>'

def get_visualization_options(result):
    """Determine appropriate visualization options based on the data"""
    options = ["Data Table"]
    
    if result['rows'] == 0 or not result['data'].shape[0]:
        return options
    
    # Check if there are numeric columns for charts
    numeric_cols = result['data'].select_dtypes(include=['number']).columns.tolist()
    
    if numeric_cols:
        options.append("Bar Chart")
        options.append("Line Chart")
        options.append("Scatter Plot")
        
        # Histogram requires a numeric column
        options.append("Histogram")
        
        # If we have at least 3 numeric columns, offer 3D scatter
        if len(numeric_cols) >= 3:
            options.append("3D Scatter")
    
    # Check if there are date/time columns for time series
    datetime_cols = []
    for col in result['data'].columns:
        if pd.api.types.is_datetime64_any_dtype(result['data'][col]) or (
            isinstance(result['data'][col].iloc[0], str) and 
            bool(re.match(r'\d{4}-\d{2}-\d{2}', result['data'][col].iloc[0]))
        ):
            datetime_cols.append(col)
    
    if datetime_cols and numeric_cols:
        options.append("Time Series")
    
    # Check for categorical columns
    categorical_cols = [col for col in result['data'].columns 
                      if col not in numeric_cols and col not in datetime_cols]
    
    if categorical_cols:
        options.append("Pie Chart")
        
        if numeric_cols:
            options.append("Box Plot")
            options.append("Violin Plot")
    
    # If we have two categorical and one numeric, offer heatmap
    if len(categorical_cols) >= 2 and numeric_cols:
        options.append("Heatmap")
    
    return options

def create_visualization(result, vis_type, config):
    """Create a visualization based on the selected type and configuration"""
    try:
        df = result['data']
        
        if vis_type == "Bar Chart":
            # Bar chart requires a categorical x and numeric y
            x_col = config['x_axis']
            y_col = config['y_axis']
            color_col = config.get('color')
            
            if color_col and color_col != "None":
                fig = px.bar(
                    df, x=x_col, y=y_col, color=color_col,
                    title=f"{y_col} by {x_col}",
                    labels={x_col: x_col, y_col: y_col}
                )
            else:
                fig = px.bar(
                    df, x=x_col, y=y_col,
                    title=f"{y_col} by {x_col}",
                    labels={x_col: x_col, y_col: y_col}
                )
            
            return fig
        
        elif vis_type == "Line Chart":
            # Line chart requires an x (usually time) and numeric y
            x_col = config['x_axis']
            y_col = config['y_axis']
            color_col = config.get('color')
            
            if color_col and color_col != "None":
                fig = px.line(
                    df, x=x_col, y=y_col, color=color_col,
                    title=f"{y_col} over {x_col}",
                    labels={x_col: x_col, y_col: y_col}
                )
            else:
                fig = px.line(
                    df, x=x_col, y=y_col,
                    title=f"{y_col} over {x_col}",
                    labels={x_col: x_col, y_col: y_col}
                )
            
            return fig
        
        elif vis_type == "Scatter Plot":
            # Scatter plot requires numeric x and y
            x_col = config['x_axis']
            y_col = config['y_axis']
            color_col = config.get('color')
            size_col = config.get('size')
            
            scatter_args = {
                'x': x_col,
                'y': y_col,
                'title': f"{y_col} vs {x_col}",
                'labels': {x_col: x_col, y_col: y_col}
            }
            
            if color_col and color_col != "None":
                scatter_args['color'] = color_col
                
            if size_col and size_col != "None":
                scatter_args['size'] = size_col
                
            fig = px.scatter(df, **scatter_args)
            return fig
        
        elif vis_type == "Histogram":
            # Histogram requires a numeric column
            x_col = config['column']
            color_col = config.get('color')
            
            if color_col and color_col != "None":
                fig = px.histogram(
                    df, x=x_col, color=color_col,
                    title=f"Distribution of {x_col}",
                    labels={x_col: x_col}
                )
            else:
                fig = px.histogram(
                    df, x=x_col,
                    title=f"Distribution of {x_col}",
                    labels={x_col: x_col}
                )
            
            return fig
        
        elif vis_type == "Time Series":
            # Time series requires a date column and numeric values
            x_col = config['time_column']
            y_cols = config['value_columns']
            
            fig = go.Figure()
            
            for y_col in y_cols:
                fig.add_trace(go.Scatter(
                    x=df[x_col],
                    y=df[y_col],
                    name=y_col,
                    mode='lines+markers'
                ))
            
            fig.update_layout(
                title=f"Time Series of {', '.join(y_cols)}",
                xaxis_title=x_col,
                yaxis_title="Value",
                legend_title="Metric"
            )
            
            return fig
        
        elif vis_type == "Pie Chart":
            # Pie chart requires a categorical column and a numeric value
            names_col = config['names']
            values_col = config['values']
            
            fig = px.pie(
                df, names=names_col, values=values_col,
                title=f"{values_col} by {names_col}"
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            
            return fig
        
        elif vis_type == "Box Plot":
            # Box plot requires a categorical x and numeric y
            x_col = config['category']
            y_col = config['value']
            color_col = config.get('color')
            
            if color_col and color_col != "None":
                fig = px.box(
                    df, x=x_col, y=y_col, color=color_col,
                    title=f"Distribution of {y_col} by {x_col}",
                    labels={x_col: x_col, y_col: y_col}
                )
            else:
                fig = px.box(
                    df, x=x_col, y=y_col,
                    title=f"Distribution of {y_col} by {x_col}",
                    labels={x_col: x_col, y_col: y_col}
                )
            
            return fig
        
        elif vis_type == "Violin Plot":
            # Violin plot requires a categorical x and numeric y
            x_col = config['category']
            y_col = config['value']
            color_col = config.get('color')
            
            if color_col and color_col != "None":
                fig = px.violin(
                    df, x=x_col, y=y_col, color=color_col,
                    title=f"Distribution of {y_col} by {x_col}",
                    labels={x_col: x_col, y_col: y_col},
                    box=True
                )
            else:
                fig = px.violin(
                    df, x=x_col, y=y_col,
                    title=f"Distribution of {y_col} by {x_col}",
                    labels={x_col: x_col, y_col: y_col},
                    box=True
                )
            
            return fig
        
        elif vis_type == "3D Scatter":
            # 3D scatter requires three numeric columns
            x_col = config['x_axis']
            y_col = config['y_axis']
            z_col = config['z_axis']
            color_col = config.get('color')
            
            if color_col and color_col != "None":
                fig = px.scatter_3d(
                    df, x=x_col, y=y_col, z=z_col, color=color_col,
                    title=f"3D Scatter Plot",
                    labels={x_col: x_col, y_col: y_col, z_col: z_col}
                )
            else:
                fig = px.scatter_3d(
                    df, x=x_col, y=y_col, z=z_col,
                    title=f"3D Scatter Plot",
                    labels={x_col: x_col, y_col: y_col, z_col: z_col}
                )
            
            return fig
        
        elif vis_type == "Heatmap":
            # Heatmap requires categorical x and y with a numeric value
            x_col = config['x_axis']
            y_col = config['y_axis']
            z_col = config['value']
            
            # Create pivot table
            pivot_data = df.pivot_table(
                values=z_col,
                index=y_col,
                columns=x_col,
                aggfunc='mean'
            )
            
            fig = px.imshow(
                pivot_data,
                title=f"Heatmap of {z_col} by {x_col} and {y_col}",
                labels=dict(color=z_col),
                x=pivot_data.columns,
                y=pivot_data.index
            )
            
            return fig
        
        # Default case - return nothing
        return None
    
    except Exception as e:
        st.error(f"Error creating visualization: {e}")
        return None

# Query templates
QUERY_TEMPLATES = [
    {
        "name": "Top Positive Tickers",
        "description": "Find tickers with the highest average sentiment scores",
        "category": "Sentiment Analysis",
        "sql": """
SELECT 
    ts.ticker,
    ROUND(AVG(ts.sentiment_score)::numeric, 4) as avg_score,
    COUNT(*) as mention_count,
    MIN(se.timestamp) as first_seen,
    MAX(se.timestamp) as last_seen
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
LIMIT 10;
"""
    },
    {
        "name": "Top Negative Tickers",
        "description": "Find tickers with the lowest average sentiment scores",
        "category": "Sentiment Analysis",
        "sql": """
SELECT 
    ts.ticker,
    ROUND(AVG(ts.sentiment_score)::numeric, 4) as avg_score,
    COUNT(*) as mention_count,
    MIN(se.timestamp) as first_seen,
    MAX(se.timestamp) as last_seen
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
LIMIT 10;
"""
    },
    {
        "name": "Most Mentioned Tickers",
        "description": "Find the most frequently mentioned tickers",
        "category": "Popularity Analysis",
        "sql": """
SELECT 
    ts.ticker,
    COUNT(*) as mention_count,
    ROUND(AVG(ts.sentiment_score)::numeric, 4) as avg_score,
    MIN(se.timestamp) as first_seen,
    MAX(se.timestamp) as last_seen
FROM 
    ticker_sentiments ts
JOIN 
    sentiment_events se ON ts.event_id = se.id
WHERE 
    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    ts.ticker
ORDER BY 
    mention_count DESC
LIMIT 10;
"""
    },
    {
        "name": "Daily Sentiment Trend",
        "description": "Track average sentiment scores by day",
        "category": "Time Series",
        "sql": """
SELECT 
    se.timestamp::date as date,
    ROUND(AVG(se.sentiment_score)::numeric, 4) as avg_score,
    COUNT(*) as event_count
FROM 
    sentiment_events se
WHERE 
    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    date
ORDER BY 
    date;
"""
    },
    {
        "name": "Source Analysis",
        "description": "Compare sentiment from different sources",
        "category": "Source Analysis",
        "sql": """
SELECT 
    se.source,
    COUNT(*) as event_count,
    ROUND(AVG(se.sentiment_score)::numeric, 4) as avg_score,
    MIN(se.timestamp) as first_seen,
    MAX(se.timestamp) as last_seen
FROM 
    sentiment_events se
WHERE 
    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    se.source
ORDER BY 
    event_count DESC;
"""
    },
    {
        "name": "Model Comparison",
        "description": "Compare sentiment scores from different models",
        "category": "Model Analysis",
        "sql": """
SELECT 
    se.model,
    COUNT(*) as event_count,
    ROUND(AVG(se.sentiment_score)::numeric, 4) as avg_score,
    ROUND(STDDEV(se.sentiment_score)::numeric, 4) as score_stddev,
    ROUND(AVG(se.processing_time)::numeric, 4) as avg_processing_time
FROM 
    sentiment_events se
WHERE 
    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    se.model
ORDER BY 
    event_count DESC;
"""
    },
    {
        "name": "Sentiment Volatility",
        "description": "Find tickers with the most volatile sentiment",
        "category": "Volatility Analysis",
        "sql": """
SELECT 
    ts.ticker,
    ROUND(STDDEV(ts.sentiment_score)::numeric, 4) as sentiment_volatility,
    ROUND(AVG(ts.sentiment_score)::numeric, 4) as avg_score,
    COUNT(*) as mention_count
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
    sentiment_volatility DESC
LIMIT 10;
"""
    },
    {
        "name": "Hourly Activity Pattern",
        "description": "Analyze event distribution by hour of day",
        "category": "Time Analysis",
        "sql": """
SELECT 
    EXTRACT(HOUR FROM se.timestamp) as hour_of_day,
    COUNT(*) as event_count,
    ROUND(AVG(se.sentiment_score)::numeric, 4) as avg_score
FROM 
    sentiment_events se
WHERE 
    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    hour_of_day
ORDER BY 
    hour_of_day;
"""
    },
    {
        "name": "Priority Distribution",
        "description": "Analyze event distribution by priority",
        "category": "Event Analysis",
        "sql": """
SELECT 
    se.priority,
    COUNT(*) as event_count,
    ROUND(AVG(se.sentiment_score)::numeric, 4) as avg_score,
    ROUND(AVG(se.processing_time)::numeric, 4) as avg_processing_time
FROM 
    sentiment_events se
WHERE 
    se.timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    se.priority
ORDER BY 
    event_count DESC;
"""
    },
    {
        "name": "Recent Events",
        "description": "Show the most recent sentiment events",
        "category": "Event Monitoring",
        "sql": """
SELECT 
    se.id,
    se.event_id,
    se.timestamp,
    se.source,
    se.priority,
    se.sentiment_score,
    se.sentiment_label,
    se.model,
    se.processing_time,
    ARRAY(
        SELECT ts.ticker 
        FROM ticker_sentiments ts 
        WHERE ts.event_id = se.id
    ) as tickers
FROM 
    sentiment_events se
ORDER BY 
    se.timestamp DESC
LIMIT 50;
"""
    }
]

def main():
    st.title("Advanced Query Interface")
    st.write("Query the sentiment database with predefined templates or custom SQL")
    
    # Connect to database
    engine = get_database_connection()
    
    if not engine:
        st.error("Failed to connect to the database. Please check your connection settings.")
        return
    
    # Create tabs for query types
    tabs = st.tabs(["🔎 Query Templates", "📝 Custom SQL", "📋 Schema Explorer"])
    
    # Query Templates Tab
    with tabs[0]:
        st.header("Query Templates")
        
        # Group templates by category
        templates_by_category = {}
        for template in QUERY_TEMPLATES:
            category = template["category"]
            if category not in templates_by_category:
                templates_by_category[category] = []
            templates_by_category[category].append(template)
        
        # Display templates by category
        for category, templates in templates_by_category.items():
            st.subheader(category)
            cols = st.columns(min(3, len(templates)))
            
            for i, template in enumerate(templates):
                with cols[i % len(cols)]:
                    # Create a card for each template
                    template_id = f"template_{i}"
                    st.markdown(f"""
                        <div class="query-card" id="{template_id}">
                            <h4>{template['name']}</h4>
                            <p>{template['description']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Button to select the template
                    if st.button(f"Use {template['name']}", key=f"use_{template_id}"):
                        # Store the selected template in session state
                        st.session_state.current_query = template['sql']
                        st.session_state.query_name = template['name']
                        
                        # Execute the query
                        with st.spinner("Executing query..."):
                            result = execute_query(engine, template['sql'])
                            
                            if result['success']:
                                st.session_state.current_result = result
                                st.rerun()  # Rerun to show results
                            else:
                                st.error(f"Error executing query: {result['error']}")
        
        # Check if we have results to display
        if 'current_result' in st.session_state and 'query_name' in st.session_state:
            display_query_results(st.session_state.current_result, st.session_state.query_name, st.session_state.current_query)
    
    # Custom SQL Tab
    with tabs[1]:
        st.header("Custom SQL Editor")
        
        # SQL editor
        default_query = """
-- Enter your SQL query here
SELECT 
    se.source,
    COUNT(*) as event_count,
    ROUND(AVG(se.sentiment_score)::numeric, 4) as avg_score
FROM 
    sentiment_events se
WHERE 
    se.timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY 
    se.source
ORDER BY 
    event_count DESC;
""" if 'custom_sql' not in st.session_state else st.session_state.custom_sql
        
        # Display the SQL editor with syntax highlighting
        st.markdown(highlight_sql_syntax(default_query), unsafe_allow_html=True)
        
        # Actual textarea for editing
        custom_sql = st.text_area("Edit SQL Query", default_query, height=200, key="sql_editor", label_visibility="collapsed")
        st.session_state.custom_sql = custom_sql
        
        # Execute button
        if st.button("Execute Query"):
            with st.spinner("Executing query..."):
                result = execute_query(engine, custom_sql)
                
                if result['success']:
                    st.session_state.custom_result = result
                    st.session_state.custom_query = custom_sql
                    display_query_results(result, "Custom Query", custom_sql)
                else:
                    st.error(f"Error executing query: {result['error']}")
        
        # Show previous results if available
        elif 'custom_result' in st.session_state and 'custom_query' in st.session_state:
            display_query_results(st.session_state.custom_result, "Custom Query", st.session_state.custom_query)
    
    # Schema Explorer Tab
    with tabs[2]:
        st.header("Database Schema Explorer")
        
        # Get table names
        table_names = get_table_names(engine)
        
        if table_names:
            selected_table = st.selectbox("Select Table", table_names)
            
            if selected_table:
                # Get table schema
                schema_df = get_table_schema(engine, selected_table)
                
                if not schema_df.empty:
                    st.subheader(f"Schema for {selected_table}")
                    st.dataframe(schema_df)
                    
                    # Sample data
                    if st.button("View Sample Data"):
                        sample_query = f"SELECT * FROM {selected_table} LIMIT 10"
                        with st.spinner("Fetching sample data..."):
                            result = execute_query(engine, sample_query)
                            
                            if result['success']:
                                st.subheader(f"Sample Data for {selected_table}")
                                st.dataframe(result['data'])
                            else:
                                st.error(f"Error fetching sample data: {result['error']}")
                    
                    # Generate example queries for this table
                    st.subheader("Example Queries")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Select All")
                        example_query = f"SELECT * FROM {selected_table} LIMIT 100;"
                        st.code(example_query, language="sql")
                        
                        if st.button("Run", key=f"run_all_{selected_table}"):
                            with st.spinner("Executing query..."):
                                result = execute_query(engine, example_query)
                                
                                if result['success']:
                                    st.session_state.example_result = result
                                    st.session_state.example_query = example_query
                                    st.rerun()  # Rerun to show results
                                else:
                                    st.error(f"Error executing query: {result['error']}")
                    
                    with col2:
                        st.markdown("#### Count Records")
                        example_query = f"SELECT COUNT(*) FROM {selected_table};"
                        st.code(example_query, language="sql")
                        
                        if st.button("Run", key=f"run_count_{selected_table}"):
                            with st.spinner("Executing query..."):
                                result = execute_query(engine, example_query)
                                
                                if result['success']:
                                    st.session_state.example_result = result
                                    st.session_state.example_query = example_query
                                    st.rerun()  # Rerun to show results
                                else:
                                    st.error(f"Error executing query: {result['error']}")
                    
                    # Advanced examples based on table type
                    if selected_table == "sentiment_events":
                        st.markdown("#### Recent Events")
                        example_query = """
SELECT 
    id, event_id, timestamp, source, priority, sentiment_score, model
FROM 
    sentiment_events
ORDER BY 
    timestamp DESC
LIMIT 50;
"""
                        st.code(example_query, language="sql")
                        
                        if st.button("Run", key="run_recent_events"):
                            with st.spinner("Executing query..."):
                                result = execute_query(engine, example_query)
                                
                                if result['success']:
                                    st.session_state.example_result = result
                                    st.session_state.example_query = example_query
                                    st.rerun()  # Rerun to show results
                                else:
                                    st.error(f"Error executing query: {result['error']}")
                    
                    elif selected_table == "ticker_sentiments":
                        st.markdown("#### Top Tickers")
                        example_query = """
SELECT 
    ticker, 
    COUNT(*) as count,
    ROUND(AVG(sentiment_score)::numeric, 4) as avg_score
FROM 
    ticker_sentiments
GROUP BY 
    ticker
ORDER BY 
    count DESC
LIMIT 20;
"""
                        st.code(example_query, language="sql")
                        
                        if st.button("Run", key="run_top_tickers"):
                            with st.spinner("Executing query..."):
                                result = execute_query(engine, example_query)
                                
                                if result['success']:
                                    st.session_state.example_result = result
                                    st.session_state.example_query = example_query
                                    st.rerun()  # Rerun to show results
                                else:
                                    st.error(f"Error executing query: {result['error']}")
                
                # Show results for example queries
                if 'example_result' in st.session_state and 'example_query' in st.session_state:
                    display_query_results(st.session_state.example_result, "Example Query", st.session_state.example_query)
        else:
            st.warning("No tables found in the database.")

def display_query_results(result, query_name, query_text):
    """Display query results with visualization options"""
    if result['success']:
        st.success(f"Query executed successfully: {result['rows']} rows returned in {result['duration']:.2f} seconds.")
        
        # Create tabs for different views of the results
        result_tabs = st.tabs(["Data", "Visualize", "Export", "Query"])
        
        with result_tabs[0]:
            st.subheader(f"{query_name} Results")
            
            if not result['data'].empty:
                st.dataframe(result['data'])
                
                # Display summary statistics for numeric columns
                numeric_cols = result['data'].select_dtypes(include=['number']).columns.tolist()
                if numeric_cols:
                    with st.expander("Summary Statistics"):
                        st.dataframe(result['data'][numeric_cols].describe())
            else:
                st.info("Query executed successfully, but returned no data.")
        
        with result_tabs[1]:
            st.subheader("Visualize Results")
            
            # Check if we have data to visualize
            if not result['data'].empty:
                # Determine available visualization types
                vis_options = get_visualization_options(result)
                
                if len(vis_options) > 1:  # More than just the data table option
                    vis_type = st.selectbox("Visualization Type", vis_options)
                    
                    if vis_type != "Data Table":
                        # Configuration options based on the visualization type
                        config = {}
                        
                        columns = result['data'].columns.tolist()
                        numeric_cols = result['data'].select_dtypes(include=['number']).columns.tolist()
                        non_numeric_cols = [c for c in columns if c not in numeric_cols]
                        
                        # Detect datetime columns
                        datetime_cols = []
                        for col in columns:
                            if pd.api.types.is_datetime64_any_dtype(result['data'][col]) or (
                                isinstance(result['data'][col].iloc[0], str) and 
                                bool(re.match(r'\d{4}-\d{2}-\d{2}', str(result['data'][col].iloc[0])))
                            ):
                                datetime_cols.append(col)
                        
                        if vis_type == "Bar Chart":
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                config['x_axis'] = st.selectbox("X-Axis", non_numeric_cols)
                            
                            with col2:
                                config['y_axis'] = st.selectbox("Y-Axis", numeric_cols)
                            
                            with col3:
                                color_options = ["None"] + non_numeric_cols
                                config['color'] = st.selectbox("Color By", color_options)
                        
                        elif vis_type == "Line Chart":
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                # Prefer datetime columns for x-axis in line charts
                                x_options = datetime_cols + columns
                                config['x_axis'] = st.selectbox("X-Axis", x_options)
                            
                            with col2:
                                config['y_axis'] = st.selectbox("Y-Axis", numeric_cols)
                            
                            with col3:
                                color_options = ["None"] + non_numeric_cols
                                config['color'] = st.selectbox("Color By", color_options)
                        
                        elif vis_type == "Scatter Plot":
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                config['x_axis'] = st.selectbox("X-Axis", numeric_cols)
                            
                            with col2:
                                # Filter out the selected x-axis
                                y_options = [c for c in numeric_cols if c != config['x_axis']]
                                if y_options:
                                    config['y_axis'] = st.selectbox("Y-Axis", y_options)
                                else:
                                    config['y_axis'] = config['x_axis']
                            
                            col3, col4 = st.columns(2)
                            
                            with col3:
                                color_options = ["None"] + columns
                                config['color'] = st.selectbox("Color By", color_options)
                            
                            with col4:
                                size_options = ["None"] + numeric_cols
                                config['size'] = st.selectbox("Size By", size_options)
                        
                        elif vis_type == "Histogram":
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                config['column'] = st.selectbox("Column", numeric_cols)
                            
                            with col2:
                                color_options = ["None"] + non_numeric_cols
                                config['color'] = st.selectbox("Color By", color_options)
                        
                        elif vis_type == "Time Series":
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                config['time_column'] = st.selectbox("Time Column", datetime_cols)
                            
                            with col2:
                                config['value_columns'] = st.multiselect("Value Columns", numeric_cols, default=[numeric_cols[0]] if numeric_cols else [])
                        
                        elif vis_type == "Pie Chart":
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                config['names'] = st.selectbox("Names (Categories)", non_numeric_cols)
                            
                            with col2:
                                config['values'] = st.selectbox("Values", numeric_cols)
                        
                        elif vis_type == "Box Plot" or vis_type == "Violin Plot":
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                config['category'] = st.selectbox("Category", non_numeric_cols)
                            
                            with col2:
                                config['value'] = st.selectbox("Value", numeric_cols)
                            
                            with col3:
                                color_options = ["None"] + non_numeric_cols
                                config['color'] = st.selectbox("Color By", color_options)
                        
                        elif vis_type == "3D Scatter":
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                config['x_axis'] = st.selectbox("X-Axis", numeric_cols)
                            
                            with col2:
                                # Filter out the selected x-axis
                                y_options = [c for c in numeric_cols if c != config['x_axis']]
                                if y_options:
                                    config['y_axis'] = st.selectbox("Y-Axis", y_options)
                                else:
                                    config['y_axis'] = config['x_axis']
                            
                            with col3:
                                # Filter out the selected x and y axes
                                z_options = [c for c in numeric_cols if c != config['x_axis'] and c != config['y_axis']]
                                if z_options:
                                    config['z_axis'] = st.selectbox("Z-Axis", z_options)
                                else:
                                    config['z_axis'] = config['x_axis']
                            
                            color_options = ["None"] + columns
                            config['color'] = st.selectbox("Color By", color_options)
                        
                        elif vis_type == "Heatmap":
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                config['x_axis'] = st.selectbox("X-Axis (Categories)", non_numeric_cols)
                            
                            with col2:
                                # Filter out the selected x-axis
                                y_options = [c for c in non_numeric_cols if c != config['x_axis']]
                                if y_options:
                                    config['y_axis'] = st.selectbox("Y-Axis (Categories)", y_options)
                                else:
                                    config['y_axis'] = config['x_axis']
                            
                            with col3:
                                config['value'] = st.selectbox("Value", numeric_cols)
                        
                        # Create and display the visualization
                        if st.button("Generate Visualization"):
                            with st.spinner("Creating visualization..."):
                                fig = create_visualization(result, vis_type, config)
                                
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.warning("Could not create visualization with the selected configuration.")
                else:
                    st.info("No suitable visualizations available for this data.")
            else:
                st.info("No data to visualize.")
        
        with result_tabs[2]:
            st.subheader("Export Options")
            
            if not result['data'].empty:
                # Export as CSV
                csv = result['data'].to_csv(index=False)
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
                # Export as Excel
                try:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        result['data'].to_excel(writer, sheet_name='Results', index=False)
                    excel_data = output.getvalue()
                    st.download_button(
                        label="Download as Excel",
                        data=excel_data,
                        file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.warning(f"Excel export not available: {e}")
                
                # Export as JSON
                json_str = result['data'].to_json(date_format='iso', orient='records')
                st.download_button(
                    label="Download as JSON",
                    data=json_str,
                    file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
                
                # Copy to clipboard option
                if st.button("Copy Data to Clipboard"):
                    # Convert to markdown table for clipboard (limited rows)
                    max_rows = min(50, len(result['data']))
                    markdown_table = result['data'].head(max_rows).to_markdown()
                    
                    # Use st.code to make it copyable
                    st.code(markdown_table)
                    st.info("Table shown above can be copied to clipboard. (Limited to 50 rows)")
            else:
                st.info("No data to export.")
        
        with result_tabs[3]:
            st.subheader("Query Details")
            
            # Format the SQL
            st.markdown("#### SQL Query")
            st.markdown(highlight_sql_syntax(query_text), unsafe_allow_html=True)
            
            # Query timing
            st.markdown(f"**Execution Time:** {result['duration']:.2f} seconds")
            st.markdown(f"**Rows Returned:** {result['rows']}")
            st.markdown(f"**Columns:** {', '.join(result['columns'])}")
            
            # Save query option
            if st.button("Save Query"):
                if 'saved_queries' not in st.session_state:
                    st.session_state.saved_queries = []
                
                query_name_input = st.text_input("Enter a name for this query:", query_name)
                
                if st.button("Confirm Save"):
                    st.session_state.saved_queries.append({
                        "name": query_name_input,
                        "sql": query_text,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success(f"Query saved as '{query_name_input}'")

if __name__ == "__main__":
    main()