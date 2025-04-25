"""
Web-based Parquet query viewer using Streamlit.
"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cli.parquet_query import ParquetQuery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("parquet_web")

# Configure page
st.set_page_config(
    page_title="Parquet Query Viewer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Create CSS for theming
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #0066cc;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #4d4d4d;
        margin-bottom: 1rem;
    }
    .metadata-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .query-container {
        background-color: #f9f9f9;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #ddd;
        margin-bottom: 1rem;
    }
    .results-header {
        font-size: 1.2rem;
        font-weight: bold;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .metric-container {
        background-color: #e6f3ff;
        padding: 0.7rem;
        border-radius: 0.3rem;
        text-align: center;
    }
    .footer {
        text-align: center;
        margin-top: 2rem;
        color: #666;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_parquet_query(config=None):
    """
    Initialize the ParquetQuery instance.
    
    Args:
        config: Configuration dictionary or path
        
    Returns:
        ParquetQuery instance
    """
    return ParquetQuery(config)

@st.cache_data
def get_available_tables(pq_instance):
    """
    Get available tables.
    
    Args:
        pq_instance: ParquetQuery instance
        
    Returns:
        List of table information dictionaries
    """
    pq_instance.refresh_files()
    return pq_instance.list_tables()

@st.cache_data
def get_table_schema(pq_instance, file_path):
    """
    Get schema for a table.
    
    Args:
        pq_instance: ParquetQuery instance
        file_path: Path to the Parquet file
        
    Returns:
        PyArrow schema or None
    """
    return pq_instance.get_schema(file_path)

@st.cache_data
def run_query(pq_instance, file_path, columns, filters, limit, sort_by, sort_ascending):
    """
    Run a query on a Parquet file.
    
    Args:
        pq_instance: ParquetQuery instance
        file_path: Path to the Parquet file
        columns: List of columns to select
        filters: Filter condition string
        limit: Maximum number of rows to return
        sort_by: Column to sort by
        sort_ascending: Sort in ascending order if True
        
    Returns:
        Pandas DataFrame with query results
    """
    return pq_instance.query_parquet(
        file_path=file_path,
        columns=columns,
        filters=filters,
        limit=limit,
        sort_by=sort_by,
        sort_ascending=sort_ascending
    )

@st.cache_data
def generate_summary_stats(df):
    """
    Generate summary statistics for a DataFrame.
    
    Args:
        df: Pandas DataFrame
        
    Returns:
        Dictionary of summary statistics
    """
    summary = {}
    
    try:
        summary["row_count"] = len(df)
        summary["column_count"] = len(df.columns)
        
        # Identify column types
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        text_cols = df.select_dtypes(include=['object']).columns.tolist()
        date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        
        # Summary for numeric columns
        if numeric_cols:
            summary["numeric_columns"] = numeric_cols
            summary["numeric_stats"] = df[numeric_cols].describe().to_dict()
        
        # Summary for text columns
        if text_cols:
            summary["text_columns"] = text_cols
            text_stats = {}
            for col in text_cols:
                non_null_values = df[col].dropna()
                text_stats[col] = {
                    "unique_count": non_null_values.nunique(),
                    "most_common": non_null_values.value_counts().head(5).to_dict() if not non_null_values.empty else {}
                }
            summary["text_stats"] = text_stats
        
        # Summary for date columns
        if date_cols:
            summary["date_columns"] = date_cols
            date_stats = {}
            for col in date_cols:
                non_null_values = df[col].dropna()
                if not non_null_values.empty:
                    date_stats[col] = {
                        "min": non_null_values.min(),
                        "max": non_null_values.max(),
                        "range_days": (non_null_values.max() - non_null_values.min()).days
                    }
            summary["date_stats"] = date_stats
    except Exception as e:
        logger.error(f"Error generating summary stats: {e}")
        summary["error"] = str(e)
    
    return summary

def main():
    """Main function for the Streamlit app."""
    # Initialize the ParquetQuery instance
    pq_instance = get_parquet_query()
    
    # Display header
    st.markdown('<h1 class="main-header">Parquet Query Viewer</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.header("Settings")
    
    # Navigation
    page = st.sidebar.radio("Navigation", ["Home", "Query Builder", "Data Visualization", "Schema Browser"])
    
    if page == "Home":
        show_home_page(pq_instance)
    elif page == "Query Builder":
        show_query_builder(pq_instance)
    elif page == "Data Visualization":
        show_data_visualization(pq_instance)
    elif page == "Schema Browser":
        show_schema_browser(pq_instance)
    
    # Footer
    st.markdown('<div class="footer">Parquet Query Viewer | Real-Time Sentiment Analysis System</div>', unsafe_allow_html=True)

def show_home_page(pq_instance):
    """
    Display the home page.
    
    Args:
        pq_instance: ParquetQuery instance
    """
    # Description
    st.markdown("""
    Welcome to the **Parquet Query Viewer** for the Real-Time Sentiment Analysis System.
    
    This tool allows you to:
    - Explore Parquet files containing sentiment data
    - Query data using SQL-like syntax
    - Visualize sentiment trends and patterns
    - Analyze data across different time periods and tickers
    
    Use the navigation on the left to access different features.
    """)
    
    # Display available tables
    st.markdown('<h2 class="sub-header">Available Data Files</h2>', unsafe_allow_html=True)
    
    # Get table information
    tables = get_available_tables(pq_instance)
    
    # Display tables in a grid
    col1, col2, col3 = st.columns(3)
    
    for i, table in enumerate(tables):
        col = [col1, col2, col3][i % 3]
        
        with col:
            with st.expander(table["name"]):
                st.markdown(f"**Rows:** {table.get('rows', 'N/A')}")
                st.markdown(f"**Columns:** {table.get('column_count', 'N/A')}")
                st.markdown(f"**Size:** {table.get('size_human', 'N/A')}")
                last_modified = table.get("last_modified", "N/A")
                if isinstance(last_modified, datetime):
                    st.markdown(f"**Last Modified:** {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    st.markdown(f"**Last Modified:** {last_modified}")
                if "columns" in table:
                    st.markdown("**Columns:**")
                    st.text(", ".join(table["columns"]))
    
    # System overview
    st.markdown('<h2 class="sub-header">System Overview</h2>', unsafe_allow_html=True)
    
    # Example sentiment summary
    col1, col2, col3, col4 = st.columns(4)
    
    # Get example data for metrics
    try:
        # Try to get some sample data for metrics
        sample_file = tables[0]["path"] if tables else None
        if sample_file:
            sample_data = run_query(pq_instance, sample_file, None, None, 1000, None, True)
            
            if "sentiment" in sample_data.columns:
                avg_sentiment = sample_data["sentiment"].mean()
                pos_count = (sample_data["sentiment"] > 0).sum()
                neg_count = (sample_data["sentiment"] < 0).sum()
                neutral_count = (sample_data["sentiment"] == 0).sum()
                
                col1.metric("Avg. Sentiment", f"{avg_sentiment:.2f}")
                col2.metric("Positive", pos_count)
                col3.metric("Negative", neg_count)
                col4.metric("Neutral", neutral_count)
            else:
                # Fallback if no sentiment column
                col1.metric("Total Files", len(tables))
                col2.metric("Total Rows", sum(table.get("rows", 0) for table in tables))
                col3.metric("Avg Rows/File", int(sum(table.get("rows", 0) for table in tables) / len(tables)) if tables else 0)
                col4.metric("Last Update", tables[0].get("last_modified").strftime("%Y-%m-%d") if tables and "last_modified" in tables[0] else "N/A")
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        col1.metric("Total Files", len(tables))
        col2.metric("Data Types", "Sentiment Analysis")
        col3.metric("Status", "Active")
        col4.metric("Last Update", datetime.now().strftime("%Y-%m-%d"))
    
    # Recent news
    st.markdown('<h2 class="sub-header">Sample Data Preview</h2>', unsafe_allow_html=True)
    
    try:
        # Try to get some sample data for preview
        sample_file = tables[0]["path"] if tables else None
        if sample_file:
            sample_data = run_query(pq_instance, sample_file, None, None, 5, "timestamp", False)
            st.dataframe(sample_data)
        else:
            st.info("No data files available for preview")
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        st.error(f"Error generating preview: {e}")

def show_query_builder(pq_instance):
    """
    Display the query builder page.
    
    Args:
        pq_instance: ParquetQuery instance
    """
    st.markdown('<h2 class="sub-header">Query Builder</h2>', unsafe_allow_html=True)
    
    # Get table information
    tables = get_available_tables(pq_instance)
    table_names = [table["name"] for table in tables]
    
    # Query builder
    with st.container():
        st.markdown('<div class="query-container">', unsafe_allow_html=True)
        
        # Select table
        selected_table = st.selectbox("Select Table", table_names)
        
        # Get selected table info
        selected_table_info = next((t for t in tables if t["name"] == selected_table), None)
        
        if selected_table_info:
            file_path = selected_table_info["path"]
            
            # Get schema
            schema = get_table_schema(pq_instance, file_path)
            
            if schema:
                # Get columns
                columns = [field.name for field in schema]
                
                # Column selection
                selected_columns = st.multiselect("Select Columns", columns, default=columns)
                
                # Filters
                st.markdown("### Filters")
                
                # Simple filter builder
                filter_enabled = st.checkbox("Enable Filters")
                
                filters = None
                if filter_enabled:
                    col1, col2, col3 = st.columns(3)
                    
                    filter_column = col1.selectbox("Column", columns)
                    filter_op = col2.selectbox("Operator", ["=", ">", "<", ">=", "<=", "!=", "~"])
                    filter_value = col3.text_input("Value")
                    
                    # Advanced filter option
                    advanced_filter = st.checkbox("Use Advanced Filter")
                    
                    if advanced_filter:
                        filters = st.text_area("Filter Expression", "")
                    else:
                        # Build filter string
                        if filter_column and filter_op and filter_value:
                            # Format value based on column type
                            column_type = next((field.type for field in schema if field.name == filter_column), None)
                            if column_type and pa.types.is_string(column_type):
                                # String needs quotes
                                filter_value = f"'{filter_value}'"
                            
                            filters = f"{filter_column} {filter_op} {filter_value}"
                
                # Sorting
                st.markdown("### Sorting")
                
                col1, col2 = st.columns(2)
                sort_column = col1.selectbox("Sort By", ["None"] + columns)
                sort_order = col2.selectbox("Order", ["Ascending", "Descending"])
                
                # Limit
                limit = st.slider("Result Limit", min_value=1, max_value=10000, value=100)
                
                # Execute query button
                query_button = st.button("Execute Query")
                
                if query_button:
                    # Prepare query parameters
                    query_columns = selected_columns if selected_columns else None
                    sort_by = sort_column if sort_column != "None" else None
                    sort_ascending = sort_order == "Ascending"
                    
                    # Execute query
                    with st.spinner("Executing query..."):
                        result = run_query(
                            pq_instance=pq_instance,
                            file_path=file_path,
                            columns=query_columns,
                            filters=filters,
                            limit=limit,
                            sort_by=sort_by,
                            sort_ascending=sort_ascending
                        )
                    
                    # Store result in session state
                    st.session_state.query_result = result
                    
                    # Generate summary statistics
                    st.session_state.summary_stats = generate_summary_stats(result)
            else:
                st.error(f"Could not read schema for {selected_table}")
        else:
            st.error("No table selected")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display results if available
    if "query_result" in st.session_state:
        result = st.session_state.query_result
        
        st.markdown('<h2 class="results-header">Query Results</h2>', unsafe_allow_html=True)
        
        # Results tabs
        tabs = st.tabs(["Data", "Summary", "SQL Equivalent"])
        
        with tabs[0]:
            # Display result count
            st.info(f"Found {len(result)} rows")
            
            # Display data table
            st.dataframe(result)
            
            # Export options
            st.markdown("### Export Options")
            col1, col2 = st.columns(2)
            
            export_format = col1.selectbox("Export Format", ["CSV", "JSON", "Excel"])
            
            if col2.button("Export Data"):
                # Prepare for export
                if export_format == "CSV":
                    csv = result.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"{selected_table}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                elif export_format == "JSON":
                    json_data = result.to_json(orient="records", date_format="iso")
                    st.download_button(
                        label="Download JSON",
                        data=json_data,
                        file_name=f"{selected_table}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                elif export_format == "Excel":
                    # Convert to Excel
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        result.to_excel(writer, sheet_name="Data", index=False)
                    excel_data = output.getvalue()
                    st.download_button(
                        label="Download Excel",
                        data=excel_data,
                        file_name=f"{selected_table}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        with tabs[1]:
            if "summary_stats" in st.session_state:
                summary = st.session_state.summary_stats
                
                # Basic stats
                st.markdown("### Basic Statistics")
                col1, col2 = st.columns(2)
                col1.metric("Total Rows", summary.get("row_count", 0))
                col2.metric("Total Columns", summary.get("column_count", 0))
                
                # Numeric column stats
                if "numeric_columns" in summary and summary["numeric_columns"]:
                    st.markdown("### Numeric Columns")
                    
                    # Select a numeric column for detailed stats
                    numeric_col = st.selectbox("Select Column", summary["numeric_columns"])
                    
                    if numeric_col in summary.get("numeric_stats", {}):
                        # Display stats for the selected column
                        stats = summary["numeric_stats"][numeric_col]
                        
                        # Create metrics
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Mean", f"{stats.get('mean', 0):.2f}")
                        col2.metric("Std Dev", f"{stats.get('std', 0):.2f}")
                        col3.metric("Min", f"{stats.get('min', 0):.2f}")
                        col4.metric("Max", f"{stats.get('max', 0):.2f}")
                        
                        # Create a histogram
                        if numeric_col in result.columns:
                            fig = px.histogram(result, x=numeric_col, title=f"Distribution of {numeric_col}")
                            st.plotly_chart(fig, use_container_width=True)
                
                # Text column stats
                if "text_columns" in summary and summary["text_columns"]:
                    st.markdown("### Text Columns")
                    
                    # Select a text column for detailed stats
                    text_col = st.selectbox("Select Text Column", summary["text_columns"])
                    
                    if text_col in summary.get("text_stats", {}):
                        # Display stats for the selected column
                        stats = summary["text_stats"][text_col]
                        
                        # Create metrics
                        st.metric("Unique Values", stats.get("unique_count", 0))
                        
                        # Display most common values
                        st.markdown("#### Most Common Values")
                        
                        most_common = stats.get("most_common", {})
                        if most_common:
                            # Create bar chart
                            fig = px.bar(
                                x=list(most_common.keys()),
                                y=list(most_common.values()),
                                title=f"Most Common Values in {text_col}"
                            )
                            fig.update_layout(xaxis_title=text_col, yaxis_title="Count")
                            st.plotly_chart(fig, use_container_width=True)
        
        with tabs[2]:
            # Build equivalent SQL query
            sql = "SELECT "
            
            # Columns
            if "query_columns" in locals() and query_columns:
                sql += ", ".join(query_columns)
            else:
                sql += "*"
            
            # From
            sql += f" FROM {selected_table}"
            
            # Where
            if "filters" in locals() and filters:
                sql += f" WHERE {filters}"
            
            # Order by
            if "sort_by" in locals() and sort_by:
                sql += f" ORDER BY {sort_by} {'ASC' if sort_ascending else 'DESC'}"
            
            # Limit
            if "limit" in locals():
                sql += f" LIMIT {limit}"
            
            # Display SQL
            st.code(sql, language="sql")

def show_data_visualization(pq_instance):
    """
    Display the data visualization page.
    
    Args:
        pq_instance: ParquetQuery instance
    """
    st.markdown('<h2 class="sub-header">Data Visualization</h2>', unsafe_allow_html=True)
    
    # Get table information
    tables = get_available_tables(pq_instance)
    table_names = [table["name"] for table in tables]
    
    # Visualization options
    with st.container():
        st.markdown("### Select Data Source")
        
        # Select table
        selected_table = st.selectbox("Table", table_names, key="viz_table")
        
        # Get selected table info
        selected_table_info = next((t for t in tables if t["name"] == selected_table), None)
        
        if selected_table_info:
            file_path = selected_table_info["path"]
            
            # Get schema
            schema = get_table_schema(pq_instance, file_path)
            
            if schema:
                # Get columns
                columns = [field.name for field in schema]
                
                # Load data
                data_load_state = st.text("Loading data...")
                data = run_query(pq_instance, file_path, None, None, 10000, None, True)
                data_load_state.text("Data loaded!")
                
                # Chart type selection
                st.markdown("### Chart Type")
                chart_type = st.selectbox(
                    "Select Visualization Type",
                    ["Time Series", "Histogram", "Scatter Plot", "Bar Chart", "Box Plot", "Heatmap"]
                )
                
                # Chart options based on type
                if chart_type == "Time Series":
                    # Look for timestamp column
                    timestamp_col = next((col for col in columns if col.lower() in ["timestamp", "date", "time", "datetime"]), columns[0])
                    
                    # Configuration
                    st.markdown("### Configure Chart")
                    col1, col2 = st.columns(2)
                    
                    x_axis = col1.selectbox("X-Axis (Time)", columns, index=columns.index(timestamp_col) if timestamp_col in columns else 0)
                    y_axis = col2.selectbox("Y-Axis (Metric)", [col for col in columns if col != x_axis])
                    
                    # Optional group by
                    use_group = st.checkbox("Group By")
                    group_col = None
                    if use_group:
                        group_candidates = [col for col in columns if col not in [x_axis, y_axis]]
                        if group_candidates:
                            group_col = st.selectbox("Group By Column", group_candidates)
                    
                    # Generate chart
                    try:
                        # Convert timestamp if needed
                        if "timestamp" in data.columns and pd.api.types.is_object_dtype(data["timestamp"]):
                            data["timestamp"] = pd.to_datetime(data["timestamp"])
                        
                        # Create the chart
                        if group_col:
                            fig = px.line(data, x=x_axis, y=y_axis, color=group_col, title=f"{y_axis} Over Time by {group_col}")
                        else:
                            fig = px.line(data, x=x_axis, y=y_axis, title=f"{y_axis} Over Time")
                        
                        fig.update_layout(xaxis_title=x_axis, yaxis_title=y_axis)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating chart: {e}")
                
                elif chart_type == "Histogram":
                    # Configuration
                    st.markdown("### Configure Chart")
                    
                    # Find numeric columns
                    numeric_cols = [col for col in columns if data[col].dtype.kind in 'ifc']
                    
                    if numeric_cols:
                        metric = st.selectbox("Value", numeric_cols)
                        bins = st.slider("Number of Bins", min_value=5, max_value=100, value=20)
                        
                        # Generate chart
                        try:
                            fig = px.histogram(data, x=metric, nbins=bins, title=f"Distribution of {metric}")
                            fig.update_layout(xaxis_title=metric, yaxis_title="Count")
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error creating chart: {e}")
                    else:
                        st.warning("No numeric columns available for histogram")
                
                elif chart_type == "Scatter Plot":
                    # Configuration
                    st.markdown("### Configure Chart")
                    
                    # Find numeric columns
                    numeric_cols = [col for col in columns if data[col].dtype.kind in 'ifc']
                    
                    if len(numeric_cols) >= 2:
                        col1, col2, col3 = st.columns(3)
                        
                        x_axis = col1.selectbox("X-Axis", numeric_cols)
                        y_axis = col2.selectbox("Y-Axis", [col for col in numeric_cols if col != x_axis])
                        
                        # Optional color by
                        use_color = st.checkbox("Color By")
                        color_col = None
                        if use_color:
                            color_candidates = [col for col in columns if col not in [x_axis, y_axis]]
                            if color_candidates:
                                color_col = col3.selectbox("Color By Column", color_candidates)
                        
                        # Generate chart
                        try:
                            if color_col:
                                fig = px.scatter(data, x=x_axis, y=y_axis, color=color_col, title=f"{y_axis} vs {x_axis} by {color_col}")
                            else:
                                fig = px.scatter(data, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                            
                            fig.update_layout(xaxis_title=x_axis, yaxis_title=y_axis)
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error creating chart: {e}")
                    else:
                        st.warning("Need at least 2 numeric columns for scatter plot")
                
                elif chart_type == "Bar Chart":
                    # Configuration
                    st.markdown("### Configure Chart")
                    
                    col1, col2 = st.columns(2)
                    
                    # Find categorical columns
                    categorical_cols = [col for col in columns if data[col].dtype.kind not in 'ifc' or data[col].nunique() < 50]
                    
                    if categorical_cols:
                        category = col1.selectbox("Category", categorical_cols)
                        
                        # Find numeric columns
                        numeric_cols = [col for col in columns if data[col].dtype.kind in 'ifc']
                        
                        if numeric_cols:
                            metric = col2.selectbox("Value", numeric_cols)
                            
                            # Aggregation method
                            agg_method = st.selectbox("Aggregation", ["Sum", "Average", "Count", "Min", "Max"])
                            
                            # Generate chart
                            try:
                                # Aggregate data
                                agg_map = {
                                    "Sum": "sum",
                                    "Average": "mean",
                                    "Count": "count",
                                    "Min": "min",
                                    "Max": "max"
                                }
                                
                                agg_data = data.groupby(category)[metric].agg(agg_map[agg_method]).reset_index()
                                
                                # Sort by value
                                sort_by = st.radio("Sort By", ["Value (Descending)", "Value (Ascending)", "Category"])
                                
                                if sort_by == "Value (Descending)":
                                    agg_data = agg_data.sort_values(metric, ascending=False)
                                elif sort_by == "Value (Ascending)":
                                    agg_data = agg_data.sort_values(metric, ascending=True)
                                
                                # Limit number of bars
                                max_bars = st.slider("Maximum Bars", min_value=5, max_value=50, value=15)
                                if len(agg_data) > max_bars:
                                    agg_data = agg_data.head(max_bars)
                                
                                # Create chart
                                fig = px.bar(
                                    agg_data,
                                    x=category,
                                    y=metric,
                                    title=f"{agg_method} of {metric} by {category}"
                                )
                                
                                fig.update_layout(xaxis_title=category, yaxis_title=f"{agg_method} of {metric}")
                                st.plotly_chart(fig, use_container_width=True)
                            except Exception as e:
                                st.error(f"Error creating chart: {e}")
                        else:
                            st.warning("No numeric columns available for bar chart values")
                    else:
                        st.warning("No categorical columns available for bar chart categories")
                
                elif chart_type == "Box Plot":
                    # Configuration
                    st.markdown("### Configure Chart")
                    
                    col1, col2 = st.columns(2)
                    
                    # Find categorical columns
                    categorical_cols = [col for col in columns if data[col].dtype.kind not in 'ifc' or data[col].nunique() < 20]
                    
                    # Find numeric columns
                    numeric_cols = [col for col in columns if data[col].dtype.kind in 'ifc']
                    
                    if categorical_cols and numeric_cols:
                        category = col1.selectbox("Category", categorical_cols)
                        metric = col2.selectbox("Value", numeric_cols)
                        
                        # Generate chart
                        try:
                            fig = px.box(
                                data,
                                x=category,
                                y=metric,
                                title=f"Distribution of {metric} by {category}"
                            )
                            
                            fig.update_layout(xaxis_title=category, yaxis_title=metric)
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error creating chart: {e}")
                    else:
                        if not categorical_cols:
                            st.warning("No categorical columns available for box plot categories")
                        if not numeric_cols:
                            st.warning("No numeric columns available for box plot values")
                
                elif chart_type == "Heatmap":
                    # Configuration
                    st.markdown("### Configure Chart")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    # Find categorical columns
                    categorical_cols = [col for col in columns if data[col].dtype.kind not in 'ifc' or data[col].nunique() < 50]
                    
                    # Find numeric columns
                    numeric_cols = [col for col in columns if data[col].dtype.kind in 'ifc']
                    
                    if len(categorical_cols) >= 2 and numeric_cols:
                        x_axis = col1.selectbox("X-Axis", categorical_cols)
                        y_axis = col2.selectbox("Y-Axis", [col for col in categorical_cols if col != x_axis])
                        metric = col3.selectbox("Value", numeric_cols)
                        
                        # Aggregation method
                        agg_method = st.selectbox("Aggregation Method", ["Sum", "Average", "Count", "Min", "Max"])
                        
                        # Generate chart
                        try:
                            # Aggregate data
                            agg_map = {
                                "Sum": "sum",
                                "Average": "mean",
                                "Count": "count",
                                "Min": "min",
                                "Max": "max"
                            }
                            
                            # Create pivot table
                            pivot_data = data.pivot_table(
                                values=metric,
                                index=y_axis,
                                columns=x_axis,
                                aggfunc=agg_map[agg_method]
                            )
                            
                            # Create heatmap
                            fig = px.imshow(
                                pivot_data,
                                title=f"{agg_method} of {metric} by {x_axis} and {y_axis}",
                                labels=dict(x=x_axis, y=y_axis, color=f"{agg_method} of {metric}")
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error creating chart: {e}")
                    else:
                        if len(categorical_cols) < 2:
                            st.warning("Need at least 2 categorical columns for heatmap axes")
                        if not numeric_cols:
                            st.warning("No numeric columns available for heatmap values")
            else:
                st.error(f"Could not read schema for {selected_table}")
        else:
            st.error("No table selected")

def show_schema_browser(pq_instance):
    """
    Display the schema browser page.
    
    Args:
        pq_instance: ParquetQuery instance
    """
    st.markdown('<h2 class="sub-header">Schema Browser</h2>', unsafe_allow_html=True)
    
    # Get table information
    tables = get_available_tables(pq_instance)
    
    # Sidebar for table selection
    selected_table = st.sidebar.selectbox("Select Table", [table["name"] for table in tables])
    
    # Get selected table info
    selected_table_info = next((t for t in tables if t["name"] == selected_table), None)
    
    if selected_table_info:
        file_path = selected_table_info["path"]
        
        # Display table metadata
        st.markdown('<div class="metadata-container">', unsafe_allow_html=True)
        st.markdown(f"### Table: {selected_table}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Rows", selected_table_info.get("rows", "N/A"))
        col2.metric("Columns", selected_table_info.get("column_count", "N/A"))
        col3.metric("Size", selected_table_info.get("size_human", "N/A"))
        
        st.markdown(f"**Path:** `{file_path}`")
        
        last_modified = selected_table_info.get("last_modified", "N/A")
        if isinstance(last_modified, datetime):
            st.markdown(f"**Last Modified:** {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.markdown(f"**Last Modified:** {last_modified}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Get schema
        schema = get_table_schema(pq_instance, file_path)
        
        if schema:
            # Display schema
            st.markdown("### Schema")
            
            # Create a table for schema display
            schema_table = []
            for field in schema:
                schema_table.append({
                    "Field": field.name,
                    "Type": str(field.type),
                    "Nullable": "Yes" if field.nullable else "No"
                })
            
            st.table(schema_table)
            
            # Sample data
            st.markdown("### Sample Data")
            
            try:
                sample_data = run_query(pq_instance, file_path, None, None, 5, None, True)
                st.dataframe(sample_data)
            except Exception as e:
                st.error(f"Error reading sample data: {e}")
            
            # Additional schema information
            try:
                # Get Parquet metadata
                metadata = pq.read_metadata(file_path)
                
                st.markdown("### File Metadata")
                
                meta_data = {
                    "Created By": metadata.created_by if hasattr(metadata, "created_by") else "Unknown",
                    "Num Row Groups": metadata.num_row_groups,
                    "Num Rows": metadata.num_rows,
                    "Format Version": f"{metadata.format_version}"
                }
                
                st.json(meta_data)
                
                # Row group information
                st.markdown("### Row Groups")
                
                row_groups = []
                for i in range(metadata.num_row_groups):
                    rg = metadata.row_group(i)
                    row_groups.append({
                        "Row Group": i,
                        "Num Rows": rg.num_rows,
                        "Total Bytes": rg.total_byte_size,
                        "Compressed Size": f"{rg.total_compressed_size} bytes"
                    })
                
                st.table(row_groups)
            except Exception as e:
                st.error(f"Error reading metadata: {e}")
        else:
            st.error(f"Could not read schema for {selected_table}")
    else:
        st.error("No table selected")


if __name__ == "__main__":
    main()