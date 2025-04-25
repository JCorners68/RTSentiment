#!/usr/bin/env python3
"""
Comprehensive test suite for the parquet_fdw implementation.
This script runs tests for all aspects of the parquet_fdw integration and
generates Markdown reports in the same directory.
"""
import os
import sys
import json
import time
import shutil
import subprocess
import datetime
import logging
import argparse
import psycopg2
import requests
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("parquet_fdw_test")

# Constants
PROJECT_ROOT = "/home/jonat/WSL_RT_Sentiment"
TEST_DIR = os.path.join(PROJECT_ROOT, "tests", "data_tests")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "output")
API_BASE_URL = "http://localhost:8001"  # API service URL

# Database connection settings
DB_SETTINGS = {
    "host": "localhost",
    "port": 5432,
    "database": "sentimentdb",
    "user": "pgadmin",
    "password": "localdev"
}

def run_command(command: str) -> Tuple[str, str, int]:
    """Run a shell command and return stdout, stderr, and return code."""
    logger.debug(f"Running command: {command}")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    return stdout, stderr, process.returncode

def connect_to_db() -> Optional[psycopg2.extensions.connection]:
    """Connect to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
            database=DB_SETTINGS["database"],
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"]
        )
        logger.info("Successfully connected to the database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

def execute_query(conn, query: str) -> Tuple[List[tuple], List[str], Optional[str]]:
    """Execute a query and return results, column names, and any error."""
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        
        # For SELECT queries, fetch results
        if query.lower().strip().startswith("select") or query.lower().strip().startswith("explain"):
            result = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            cursor.close()
            return result, column_names, None
        
        # For non-SELECT queries
        cursor.close()
        return [], [], None
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        return [], [], str(e)

def create_markdown_report(title: str, content: str, test_type: str) -> tuple[str, str]:
    """Create a Markdown report file with the given content."""
    # Get current date in YYMMDD format
    date_str = datetime.datetime.now().strftime('%y%m%d')
    
    # Find the next available sequence number
    seq_num = 1
    while True:
        filename = f"test_results_{date_str}_{seq_num}.md"
        if not os.path.exists(os.path.join(TEST_DIR, filename)):
            break
        seq_num += 1
    
    report_path = os.path.join(TEST_DIR, filename)
    
    with open(report_path, 'w') as f:
        f.write(f"# {title}\n\n")
        f.write(f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write(f"**Test type:** {test_type}\n\n")
        f.write(content)
    
    logger.info(f"Report created: {report_path}")
    return report_path, filename

def format_result_table(results: List[tuple], column_names: List[str]) -> str:
    """Format query results as a Markdown table."""
    if not results or not column_names:
        return "*No results*"
    
    # Create header
    table = "| " + " | ".join(column_names) + " |\n"
    table += "| " + " | ".join(["---"] * len(column_names)) + " |\n"
    
    # Add data rows
    for row in results:
        # Format each value to handle None and special characters
        formatted_row = []
        for val in row:
            if val is None:
                formatted_row.append("NULL")
            elif isinstance(val, str):
                # Escape pipe characters in string values
                formatted_row.append(str(val).replace("|", "\\|"))
            else:
                formatted_row.append(str(val))
        
        table += "| " + " | ".join(formatted_row) + " |\n"
    
    return table

# Test Functions
def test_build_image() -> str:
    """Test building the custom PostgreSQL Docker image."""
    report = "## 1. Building Custom PostgreSQL Docker Image\n\n"
    
    # Verify Dockerfile exists
    dockerfile_path = os.path.join(PROJECT_ROOT, "postgres.Dockerfile")
    if not os.path.exists(dockerfile_path):
        report += "❌ **FAIL**: postgres.Dockerfile not found at the expected location.\n\n"
        return report
    
    report += "✅ postgres.Dockerfile exists.\n\n"
    
    # Run docker build command
    os.chdir(PROJECT_ROOT)
    command = "docker build -f postgres.Dockerfile -t postgres_parquet_fdw:test ."
    start_time = time.time()
    stdout, stderr, return_code = run_command(command)
    end_time = time.time()
    
    # Check build success
    if return_code == 0:
        report += f"✅ **PASS**: Docker image built successfully in {end_time - start_time:.2f} seconds.\n\n"
    else:
        report += f"❌ **FAIL**: Docker image build failed with return code {return_code}.\n\n"
        report += "### Error Output\n```\n" + stderr + "\n```\n\n"
        return report
    
    # Check if parquet_fdw is installed in the image
    command = "docker run --rm postgres_parquet_fdw:test bash -c 'ls -la /usr/share/postgresql/14/extension/parquet_fdw*'"
    stdout, stderr, return_code = run_command(command)
    
    if return_code == 0 and "parquet_fdw" in stdout:
        report += "✅ **PASS**: parquet_fdw extension is installed in the image.\n\n"
        report += "### Extension Files\n```\n" + stdout + "\n```\n\n"
    else:
        report += "❌ **FAIL**: parquet_fdw extension not found in the image.\n\n"
        report += "### Command Output\n```\n" + stderr + "\n```\n\n"
    
    # Clean up test image (optional)
    # run_command("docker rmi postgres_parquet_fdw:test")
    
    return report

def test_docker_compose() -> str:
    """Test starting the application stack with Docker Compose."""
    report = "## 2. Starting Application Stack with Docker Compose\n\n"
    
    # Verify docker-compose.yml exists and contains PostgreSQL configuration
    docker_compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    if not os.path.exists(docker_compose_path):
        report += "❌ **FAIL**: docker-compose.yml not found at the expected location.\n\n"
        return report
    
    with open(docker_compose_path, 'r') as f:
        docker_compose_content = f.read()
    
    if "build:" in docker_compose_content and "dockerfile: postgres.Dockerfile" in docker_compose_content:
        report += "✅ **PASS**: docker-compose.yml contains custom PostgreSQL configuration.\n\n"
    else:
        report += "❌ **FAIL**: docker-compose.yml does not reference postgres.Dockerfile.\n\n"
    
    # Check for data volume mount
    if "./data/output:/var/lib/postgresql/data/output" in docker_compose_content:
        report += "✅ **PASS**: docker-compose.yml includes Parquet files volume mount.\n\n"
    else:
        report += "❌ **FAIL**: docker-compose.yml does not include Parquet files volume mount.\n\n"
    
    # Test docker-compose build specifically for postgres service
    os.chdir(PROJECT_ROOT)
    command = "docker-compose build postgres"
    start_time = time.time()
    stdout, stderr, return_code = run_command(command)
    end_time = time.time()
    
    if return_code == 0:
        report += f"✅ **PASS**: PostgreSQL service built successfully in {end_time - start_time:.2f} seconds.\n\n"
    else:
        report += f"❌ **FAIL**: PostgreSQL service build failed with return code {return_code}.\n\n"
        report += "### Error Output\n```\n" + stderr + "\n```\n\n"
        return report
    
    # Start the PostgreSQL service
    command = "docker-compose up -d postgres"
    start_time = time.time()
    stdout, stderr, return_code = run_command(command)
    end_time = time.time()
    
    if return_code == 0:
        report += f"✅ **PASS**: PostgreSQL service started successfully in {end_time - start_time:.2f} seconds.\n\n"
    else:
        report += f"❌ **FAIL**: PostgreSQL service start failed with return code {return_code}.\n\n"
        report += "### Error Output\n```\n" + stderr + "\n```\n\n"
        return report
    
    # Wait for PostgreSQL to be ready
    time.sleep(5)
    
    # Check PostgreSQL container health
    command = "docker-compose ps postgres"
    stdout, stderr, return_code = run_command(command)
    
    if "Up" in stdout and "unhealthy" not in stdout:
        report += "✅ **PASS**: PostgreSQL container is running.\n\n"
        report += "### Container Status\n```\n" + stdout + "\n```\n\n"
    else:
        report += "❌ **FAIL**: PostgreSQL container is not running properly.\n\n"
        report += "### Container Status\n```\n" + stdout + "\n```\n\n"
    
    return report

def test_fdw_initialization() -> str:
    """Test FDW initialization in PostgreSQL."""
    report = "## 3. Verifying FDW Initialization\n\n"
    
    # Verify init-fdw.sql exists
    init_sql_path = os.path.join(PROJECT_ROOT, "init-fdw.sql")
    if not os.path.exists(init_sql_path):
        report += "❌ **FAIL**: init-fdw.sql not found at the expected location.\n\n"
    else:
        report += "✅ **PASS**: init-fdw.sql exists.\n\n"
        
        # Check content of init-fdw.sql
        with open(init_sql_path, 'r') as f:
            init_sql_content = f.read()
        
        if "CREATE EXTENSION IF NOT EXISTS parquet_fdw" in init_sql_content:
            report += "✅ **PASS**: init-fdw.sql contains CREATE EXTENSION command.\n\n"
        else:
            report += "❌ **FAIL**: init-fdw.sql does not contain CREATE EXTENSION command.\n\n"
        
        if "CREATE SERVER" in init_sql_content and "FOREIGN DATA WRAPPER parquet_fdw" in init_sql_content:
            report += "✅ **PASS**: init-fdw.sql contains CREATE SERVER command.\n\n"
        else:
            report += "❌ **FAIL**: init-fdw.sql does not contain CREATE SERVER command.\n\n"
        
        if "CREATE FOREIGN TABLE" in init_sql_content:
            report += "✅ **PASS**: init-fdw.sql contains CREATE FOREIGN TABLE command(s).\n\n"
        else:
            report += "❌ **FAIL**: init-fdw.sql does not contain CREATE FOREIGN TABLE command.\n\n"
    
    # Connect to the database and check FDW setup
    conn = connect_to_db()
    if not conn:
        report += "❌ **FAIL**: Could not connect to the database for FDW verification.\n\n"
        return report
    
    try:
        # Check if parquet_fdw extension is installed
        results, column_names, error = execute_query(conn, "SELECT * FROM pg_extension WHERE extname = 'parquet_fdw';")
        
        if error:
            report += f"❌ **FAIL**: Error querying pg_extension: {error}\n\n"
        elif not results:
            report += "❌ **FAIL**: parquet_fdw extension is not installed in the database.\n\n"
        else:
            report += "✅ **PASS**: parquet_fdw extension is installed in the database.\n\n"
            report += "### Extension Details\n"
            report += format_result_table(results, column_names) + "\n\n"
        
        # Check if parquet_srv server exists
        results, column_names, error = execute_query(conn, "SELECT * FROM pg_foreign_server WHERE srvname = 'parquet_srv';")
        
        if error:
            report += f"❌ **FAIL**: Error querying pg_foreign_server: {error}\n\n"
        elif not results:
            report += "❌ **FAIL**: parquet_srv server is not defined in the database.\n\n"
        else:
            report += "✅ **PASS**: parquet_srv server is defined in the database.\n\n"
            report += "### Server Details\n"
            report += format_result_table(results, column_names) + "\n\n"
        
        # Check if user mapping exists
        results, column_names, error = execute_query(conn, "SELECT * FROM pg_user_mappings WHERE srvname = 'parquet_srv';")
        
        if error:
            report += f"❌ **FAIL**: Error querying pg_user_mappings: {error}\n\n"
        elif not results:
            report += "❌ **FAIL**: No user mappings exist for parquet_srv.\n\n"
        else:
            report += "✅ **PASS**: User mapping(s) exist for parquet_srv.\n\n"
            report += "### User Mapping Details\n"
            report += format_result_table(results, column_names) + "\n\n"
        
        # Check for foreign tables
        results, column_names, error = execute_query(conn, 
            """SELECT ft.ftrelid::regclass AS foreign_table, 
                      ftoptions 
               FROM pg_foreign_table ft 
               JOIN pg_class c ON c.oid = ft.ftrelid 
               JOIN pg_foreign_server fs ON fs.oid = ft.ftserver 
               WHERE fs.srvname = 'parquet_srv';""")
        
        if error:
            report += f"❌ **FAIL**: Error querying foreign tables: {error}\n\n"
        elif not results:
            report += "❌ **FAIL**: No foreign tables exist for parquet_srv.\n\n"
        else:
            report += f"✅ **PASS**: {len(results)} foreign table(s) exist for parquet_srv.\n\n"
            report += "### Foreign Table Details\n"
            report += format_result_table(results, column_names) + "\n\n"
        
        # Check all_sentiment view (if it exists)
        results, column_names, error = execute_query(conn, "SELECT pg_get_viewdef('all_sentiment'::regclass, true);")
        
        if error and "relation \"all_sentiment\" does not exist" not in str(error):
            report += f"❌ **FAIL**: Error querying all_sentiment view: {error}\n\n"
        elif error:
            report += "⚠️ **WARNING**: all_sentiment view does not exist.\n\n"
        else:
            report += "✅ **PASS**: all_sentiment view exists.\n\n"
            report += "### View Definition\n```sql\n" + results[0][0] + "\n```\n\n"
    
    finally:
        conn.close()
    
    return report

def test_fdw_core_functionality() -> str:
    """Test core functionality of the parquet_fdw."""
    report = "## 4. Testing FDW Core Functionality\n\n"
    
    # Connect to the database
    conn = connect_to_db()
    if not conn:
        report += "❌ **FAIL**: Could not connect to the database for FDW testing.\n\n"
        return report
    
    try:
        # Get list of available foreign tables
        results, column_names, error = execute_query(conn, 
            """SELECT ft.ftrelid::regclass AS foreign_table
               FROM pg_foreign_table ft 
               JOIN pg_foreign_server fs ON fs.oid = ft.ftserver 
               WHERE fs.srvname = 'parquet_srv';""")
        
        if error or not results:
            report += "❌ **FAIL**: Could not get list of foreign tables.\n\n"
            if error:
                report += f"Error: {error}\n\n"
            return report
        
        foreign_tables = [row[0] for row in results]
        report += f"Found {len(foreign_tables)} foreign tables: {', '.join(foreign_tables)}\n\n"
        
        # Test each foreign table
        for table in foreign_tables:
            report += f"### Testing Foreign Table: {table}\n\n"
            
            # Basic SELECT
            results, column_names, error = execute_query(conn, f"SELECT COUNT(*) FROM {table};")
            
            if error:
                report += f"❌ **FAIL**: Error executing COUNT query on {table}: {error}\n\n"
            else:
                count = results[0][0] if results else 0
                report += f"✅ **PASS**: Table {table} contains {count} rows.\n\n"
            
            # Get sample data
            results, column_names, error = execute_query(conn, f"SELECT * FROM {table} LIMIT 5;")
            
            if error:
                report += f"❌ **FAIL**: Error fetching sample data from {table}: {error}\n\n"
            elif not results:
                report += f"⚠️ **WARNING**: Table {table} appears to be empty.\n\n"
            else:
                report += f"✅ **PASS**: Successfully retrieved sample data from {table}.\n\n"
                report += "#### Sample Data\n"
                report += format_result_table(results, column_names) + "\n\n"
            
            # Get column information
            results, column_names, error = execute_query(conn, 
                f"""SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{table}';""")
            
            if error:
                report += f"❌ **FAIL**: Error fetching column information for {table}: {error}\n\n"
            else:
                report += f"✅ **PASS**: Retrieved column information for {table}.\n\n"
                report += "#### Column Information\n"
                report += format_result_table(results, column_names) + "\n\n"
        
        # Test queries against all_sentiment (if it exists)
        try:
            # Basic query
            results, column_names, error = execute_query(conn, "SELECT COUNT(*) FROM all_sentiment;")
            
            if error:
                report += f"❌ **FAIL**: Error executing COUNT query on all_sentiment: {error}\n\n"
            else:
                count = results[0][0] if results else 0
                report += f"✅ **PASS**: View all_sentiment contains {count} rows.\n\n"
            
            # Query with WHERE clause
            results, column_names, error = execute_query(conn, "SELECT * FROM all_sentiment WHERE ticker = 'AAPL' LIMIT 5;")
            
            if error:
                report += f"❌ **FAIL**: Error executing filtered query on all_sentiment: {error}\n\n"
            else:
                report += f"✅ **PASS**: Successfully executed filtered query on all_sentiment.\n\n"
                report += "#### Filtered Results (ticker = 'AAPL')\n"
                report += format_result_table(results, column_names) + "\n\n"
            
            # EXPLAIN ANALYZE query
            results, column_names, error = execute_query(conn, 
                "EXPLAIN ANALYZE SELECT * FROM all_sentiment WHERE ticker = 'AAPL' LIMIT 5;")
            
            if error:
                report += f"❌ **FAIL**: Error executing EXPLAIN ANALYZE: {error}\n\n"
            else:
                report += "✅ **PASS**: Successfully executed EXPLAIN ANALYZE.\n\n"
                report += "#### EXPLAIN ANALYZE Output\n```\n"
                for row in results:
                    report += row[0] + "\n"
                report += "```\n\n"
        
        except Exception as e:
            report += f"⚠️ **WARNING**: Could not test all_sentiment view: {e}\n\n"
    
    finally:
        conn.close()
    
    return report

def test_parquet_file_modification() -> str:
    """Test how FDW handles Parquet file modifications."""
    report = "## 5. Testing Parquet File Modifications\n\n"
    
    # Connect to the database
    conn = connect_to_db()
    if not conn:
        report += "❌ **FAIL**: Could not connect to the database for testing file modifications.\n\n"
        return report
    
    try:
        # Create a test Parquet file
        test_file_name = "test_modification.parquet"
        test_file_path = os.path.join(DATA_DIR, test_file_name)
        
        # Create DataFrame with test data
        test_data = {
            "timestamp": [datetime.datetime.now().isoformat() for _ in range(5)],
            "ticker": ["TEST1", "TEST2", "TEST3", "TEST4", "TEST5"],
            "sentiment": [0.5, 0.7, -0.3, 0.1, 0.9],
            "confidence": [0.8, 0.9, 0.7, 0.6, 0.95],
            "source": ["test_source" for _ in range(5)],
            "model": ["test_model" for _ in range(5)],
            "article_id": [f"test_{i}" for i in range(5)],
            "article_title": [f"Test Article {i}" for i in range(5)]
        }
        df = pd.DataFrame(test_data)
        
        # Save to Parquet
        table = pa.Table.from_pandas(df)
        pq.write_table(table, test_file_path)
        
        report += f"✅ Created test Parquet file: {test_file_name}\n\n"
        
        # Create a foreign table for the test file
        create_table_sql = f"""
        CREATE FOREIGN TABLE IF NOT EXISTS test_modification (
            timestamp TEXT,
            ticker TEXT,
            sentiment FLOAT8,
            confidence FLOAT8,
            source TEXT,
            model TEXT,
            article_id TEXT,
            article_title TEXT
        ) SERVER parquet_srv
        OPTIONS (
            filename '/var/lib/postgresql/data/output/{test_file_name}'
        );
        """
        
        _, _, error = execute_query(conn, create_table_sql)
        
        if error:
            report += f"❌ **FAIL**: Error creating foreign table: {error}\n\n"
            # Remove the test file
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
            return report
        
        report += "✅ **PASS**: Created foreign table 'test_modification'.\n\n"
        
        # Query the foreign table
        results, column_names, error = execute_query(conn, "SELECT COUNT(*) FROM test_modification;")
        
        if error:
            report += f"❌ **FAIL**: Error querying test table: {error}\n\n"
        else:
            count = results[0][0] if results else 0
            report += f"✅ **PASS**: Initial query successful. Row count: {count}\n\n"
        
        # Modify the Parquet file (add more rows)
        new_data = {
            "timestamp": [datetime.datetime.now().isoformat() for _ in range(5)],
            "ticker": ["TEST6", "TEST7", "TEST8", "TEST9", "TEST10"],
            "sentiment": [0.4, 0.6, -0.2, 0.2, 0.8],
            "confidence": [0.7, 0.8, 0.6, 0.5, 0.85],
            "source": ["test_source_mod" for _ in range(5)],
            "model": ["test_model_mod" for _ in range(5)],
            "article_id": [f"test_mod_{i}" for i in range(5)],
            "article_title": [f"Test Modified Article {i}" for i in range(5)]
        }
        new_df = pd.DataFrame(new_data)
        
        # Append to the existing file
        existing_table = pq.read_table(test_file_path)
        new_table = pa.Table.from_pandas(new_df)
        combined_table = pa.concat_tables([existing_table, new_table])
        pq.write_table(combined_table, test_file_path)
        
        report += "✅ Modified test Parquet file (added 5 rows).\n\n"
        
        # Query again to check if changes are reflected
        results, column_names, error = execute_query(conn, "SELECT COUNT(*) FROM test_modification;")
        
        if error:
            report += f"❌ **FAIL**: Error querying modified test table: {error}\n\n"
        else:
            count = results[0][0] if results else 0
            if count == 10:  # 5 original + 5 new rows
                report += f"✅ **PASS**: Changes reflected. New row count: {count}\n\n"
            else:
                report += f"❌ **FAIL**: Changes not reflected. Expected 10 rows, got {count}.\n\n"
        
        # Query the new data specifically
        results, column_names, error = execute_query(conn, 
            "SELECT * FROM test_modification WHERE source = 'test_source_mod' LIMIT 5;")
        
        if error:
            report += f"❌ **FAIL**: Error querying new data: {error}\n\n"
        elif not results:
            report += "❌ **FAIL**: Could not retrieve the newly added data.\n\n"
        else:
            report += "✅ **PASS**: Successfully retrieved newly added data.\n\n"
            report += "#### New Data\n"
            report += format_result_table(results, column_names) + "\n\n"
        
        # Clean up
        _, _, error = execute_query(conn, "DROP FOREIGN TABLE IF EXISTS test_modification;")
        if error:
            report += f"⚠️ **WARNING**: Error dropping foreign table: {error}\n\n"
        else:
            report += "✅ Dropped foreign table 'test_modification'.\n\n"
        
        # Remove the test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            report += f"✅ Removed test Parquet file: {test_file_name}\n\n"
    
    finally:
        conn.close()
    
    return report

def test_data_pipeline_parquet() -> str:
    """Test data pipeline and Parquet file generation."""
    report = "## 6. Testing Data Pipeline and Parquet File Generation\n\n"
    
    # Check for the updated BaseScraper class
    base_scraper_path = os.path.join(PROJECT_ROOT, "data_acquisition", "scrapers", "base.py")
    if not os.path.exists(base_scraper_path):
        report += "❌ **FAIL**: BaseScraper (base.py) not found at the expected location.\n\n"
        return report
    
    with open(base_scraper_path, 'r') as f:
        base_scraper_content = f.read()
    
    if "_save_to_parquet" in base_scraper_content and "import pandas as pd" in base_scraper_content:
        report += "✅ **PASS**: BaseScraper includes Parquet functionality.\n\n"
    else:
        report += "❌ **FAIL**: BaseScraper does not include Parquet functionality.\n\n"
    
    # Check for parquet_utils.py
    parquet_utils_path = os.path.join(PROJECT_ROOT, "parquet_utils.py")
    if not os.path.exists(parquet_utils_path):
        report += "❌ **FAIL**: parquet_utils.py not found at the expected location.\n\n"
    else:
        report += "✅ **PASS**: parquet_utils.py exists.\n\n"
        
        # Check parquet_utils.py functionality
        with open(parquet_utils_path, 'r') as f:
            parquet_utils_content = f.read()
        
        required_functions = [
            "calculate_weight", "deduplicate_parquet", "optimize_parquet", 
            "process_all_files", "show_schema"
        ]
        
        missing_functions = [func for func in required_functions if func not in parquet_utils_content]
        
        if missing_functions:
            report += f"❌ **FAIL**: parquet_utils.py is missing expected functions: {', '.join(missing_functions)}\n\n"
        else:
            report += "✅ **PASS**: parquet_utils.py contains all expected functions.\n\n"
    
    # Run parquet_utils.py to view schema of existing Parquet files
    os.chdir(PROJECT_ROOT)
    
    # Find an existing Parquet file
    existing_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.parquet')]
    
    if not existing_files:
        report += "⚠️ **WARNING**: No existing Parquet files found for schema inspection.\n\n"
    else:
        test_file = os.path.join(DATA_DIR, existing_files[0])
        command = f"python3 parquet_utils.py schema --file {test_file}"
        stdout, stderr, return_code = run_command(command)
        
        if return_code == 0:
            report += f"✅ **PASS**: parquet_utils.py schema command executed successfully on {existing_files[0]}.\n\n"
            report += "### Schema Output\n```\n" + stdout + "\n```\n\n"
        else:
            report += f"❌ **FAIL**: parquet_utils.py schema command failed with return code {return_code}.\n\n"
            report += "### Error Output\n```\n" + stderr + "\n```\n\n"
    
    # Check for optimize_parquet.sh
    optimize_script_path = os.path.join(PROJECT_ROOT, "cron_jobs", "optimize_parquet.sh")
    if not os.path.exists(optimize_script_path):
        report += "❌ **FAIL**: optimize_parquet.sh not found at the expected location.\n\n"
    else:
        report += "✅ **PASS**: optimize_parquet.sh exists.\n\n"
        
        # Make sure the script is executable
        if not os.access(optimize_script_path, os.X_OK):
            os.chmod(optimize_script_path, 0o755)
            report += "⚠️ **WARNING**: optimize_parquet.sh was not executable. Fixed permissions.\n\n"
        
        # Check script content
        with open(optimize_script_path, 'r') as f:
            script_content = f.read()
        
        if "parquet_utils.py process-all" in script_content:
            report += "✅ **PASS**: optimize_parquet.sh calls parquet_utils.py correctly.\n\n"
        else:
            report += "❌ **FAIL**: optimize_parquet.sh does not call parquet_utils.py correctly.\n\n"
    
    return report

def test_api_integration() -> str:
    """Test API integration with parquet_fdw."""
    report = "## 7. Testing API Integration\n\n"
    
    # Check for updated API code
    database_py_path = os.path.join(PROJECT_ROOT, "api", "database.py")
    if not os.path.exists(database_py_path):
        report += "❌ **FAIL**: database.py not found at the expected location.\n\n"
        return report
    
    with open(database_py_path, 'r') as f:
        database_py_content = f.read()
    
    if "query_sentiment_data" in database_py_content and "all_sentiment" in database_py_content:
        report += "✅ **PASS**: database.py includes FDW query functions.\n\n"
    else:
        report += "❌ **FAIL**: database.py does not include FDW query functions.\n\n"
    
    # Check routes file
    routes_py_path = os.path.join(PROJECT_ROOT, "api", "routes", "sentiment.py")
    if not os.path.exists(routes_py_path):
        report += "❌ **FAIL**: sentiment.py not found at the expected location.\n\n"
    else:
        with open(routes_py_path, 'r') as f:
            routes_py_content = f.read()
        
        if "query_sentiment_data" in routes_py_content and "get_ticker_sentiment" in routes_py_content:
            report += "✅ **PASS**: sentiment.py routes are updated to use FDW.\n\n"
        else:
            report += "❌ **FAIL**: sentiment.py routes are not updated to use FDW.\n\n"
    
    # Test API endpoints
    # First check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            report += "✅ **PASS**: API service is running and health endpoint is accessible.\n\n"
        else:
            report += f"⚠️ **WARNING**: API service health check returned status code {response.status_code}.\n\n"
    except Exception as e:
        report += f"⚠️ **WARNING**: Could not connect to API service: {e}\n\n"
        report += "API integration tests skipped. Please ensure the API service is running.\n\n"
        return report
    
    # Test ticker endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/sentiment/ticker/AAPL")
        if response.status_code == 200:
            report += "✅ **PASS**: /sentiment/ticker/AAPL endpoint returned status 200.\n\n"
            report += "### Response\n```json\n" + json.dumps(response.json(), indent=2) + "\n```\n\n"
        else:
            report += f"❌ **FAIL**: /sentiment/ticker/AAPL endpoint returned status {response.status_code}.\n\n"
            report += "### Response\n```\n" + response.text + "\n```\n\n"
    except Exception as e:
        report += f"❌ **FAIL**: Error calling /sentiment/ticker/AAPL endpoint: {e}\n\n"
    
    # Test tickers endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/sentiment/tickers")
        if response.status_code == 200:
            report += "✅ **PASS**: /sentiment/tickers endpoint returned status 200.\n\n"
            report += "### Response\n```json\n" + json.dumps(response.json(), indent=2) + "\n```\n\n"
        else:
            report += f"❌ **FAIL**: /sentiment/tickers endpoint returned status {response.status_code}.\n\n"
            report += "### Response\n```\n" + response.text + "\n```\n\n"
    except Exception as e:
        report += f"❌ **FAIL**: Error calling /sentiment/tickers endpoint: {e}\n\n"
    
    # Test top endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/sentiment/top?limit=5")
        if response.status_code == 200:
            report += "✅ **PASS**: /sentiment/top endpoint returned status 200.\n\n"
            report += "### Response\n```json\n" + json.dumps(response.json(), indent=2) + "\n```\n\n"
        else:
            report += f"❌ **FAIL**: /sentiment/top endpoint returned status {response.status_code}.\n\n"
            report += "### Response\n```\n" + response.text + "\n```\n\n"
    except Exception as e:
        report += f"❌ **FAIL**: Error calling /sentiment/top endpoint: {e}\n\n"
    
    # Test query endpoint
    try:
        query_data = {
            "start_date": (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat(),
            "end_date": datetime.datetime.now().isoformat(),
            "limit": 5
        }
        
        response = requests.post(f"{API_BASE_URL}/sentiment/query", json=query_data)
        if response.status_code == 200:
            report += "✅ **PASS**: /sentiment/query endpoint returned status 200.\n\n"
            report += "### Response\n```json\n" + json.dumps(response.json(), indent=2) + "\n```\n\n"
        else:
            report += f"❌ **FAIL**: /sentiment/query endpoint returned status {response.status_code}.\n\n"
            report += "### Response\n```\n" + response.text + "\n```\n\n"
    except Exception as e:
        report += f"❌ **FAIL**: Error calling /sentiment/query endpoint: {e}\n\n"
    
    return report

def test_performance() -> str:
    """Test performance of FDW queries."""
    report = "## 8. Performance Testing\n\n"
    
    # Connect to the database
    conn = connect_to_db()
    if not conn:
        report += "❌ **FAIL**: Could not connect to the database for performance testing.\n\n"
        return report
    
    try:
        # Get list of available tables (foreign tables + regular tables)
        results, column_names, error = execute_query(conn, 
            """SELECT table_name, table_type 
               FROM information_schema.tables 
               WHERE table_schema = 'public';""")
        
        if error:
            report += f"❌ **FAIL**: Error getting table list: {error}\n\n"
            return report
        
        tables = {row[0]: row[1] for row in results}
        report += f"Found {len(tables)} tables in public schema.\n\n"
        
        # Performance test queries
        test_queries = [
            {
                "name": "Simple COUNT(*)",
                "sql": "SELECT COUNT(*) FROM all_sentiment;"
            },
            {
                "name": "Filter by ticker",
                "sql": "SELECT COUNT(*) FROM all_sentiment WHERE ticker = 'AAPL';"
            },
            {
                "name": "Group by ticker",
                "sql": "SELECT ticker, AVG(sentiment) FROM all_sentiment GROUP BY ticker;"
            },
            {
                "name": "Complex query",
                "sql": """
                SELECT ticker, 
                       AVG(sentiment) as avg_sentiment, 
                       COUNT(*) as count,
                       MIN(timestamp) as first_seen,
                       MAX(timestamp) as last_seen
                FROM all_sentiment
                GROUP BY ticker
                HAVING COUNT(*) > 1
                ORDER BY avg_sentiment DESC;
                """
            }
        ]
        
        # Run performance tests
        report += "### Performance Test Results\n\n"
        report += "| Query | Execution Time (ms) | Rows Returned |\n"
        report += "| ----- | ------------------- | ------------- |\n"
        
        for test in test_queries:
            try:
                # Time the query execution
                start_time = time.time()
                results, column_names, error = execute_query(conn, test["sql"])
                end_time = time.time()
                
                if error:
                    report += f"| {test['name']} | ❌ ERROR | N/A |\n"
                    report += f"\nError: {error}\n\n"
                else:
                    execution_time_ms = (end_time - start_time) * 1000
                    row_count = len(results)
                    report += f"| {test['name']} | {execution_time_ms:.2f} | {row_count} |\n"
            except Exception as e:
                report += f"| {test['name']} | ❌ EXCEPTION | N/A |\n"
                report += f"\nException: {e}\n\n"
        
        report += "\n\n"
        
        # Test concurrent queries
        report += "### Concurrent Query Test\n\n"
        
        try:
            # Simple function to run a query
            def run_query():
                test_conn = psycopg2.connect(
                    host=DB_SETTINGS["host"],
                    port=DB_SETTINGS["port"],
                    database=DB_SETTINGS["database"],
                    user=DB_SETTINGS["user"],
                    password=DB_SETTINGS["password"]
                )
                cursor = test_conn.cursor()
                cursor.execute("SELECT * FROM all_sentiment LIMIT 10;")
                cursor.fetchall()
                cursor.close()
                test_conn.close()
            
            # Run 10 concurrent queries and measure time
            start_time = time.time()
            threads = []
            for _ in range(10):
                t = threading.Thread(target=run_query)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            end_time = time.time()
            total_time = end_time - start_time
            
            report += f"✅ **PASS**: Successfully ran 10 concurrent queries.\n\n"
            report += f"Total time for all queries: {total_time:.2f} seconds\n"
            report += f"Average time per query: {(total_time/10)*1000:.2f} ms\n\n"
        
        except Exception as e:
            report += f"❌ **FAIL**: Error during concurrent query test: {e}\n\n"
    
    finally:
        conn.close()
    
    return report

def test_data_integrity() -> str:
    """Test data integrity between FDW and original sources."""
    report = "## 9. Data Integrity Testing\n\n"
    
    # Connect to the database
    conn = connect_to_db()
    if not conn:
        report += "❌ **FAIL**: Could not connect to the database for data integrity testing.\n\n"
        return report
    
    try:
        # Get a list of Parquet files
        parquet_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.parquet')]
        
        if not parquet_files:
            report += "⚠️ **WARNING**: No Parquet files found in data/output directory.\n\n"
            return report
        
        report += f"Found {len(parquet_files)} Parquet files for integrity testing.\n\n"
        
        # Test a sample Parquet file
        test_file = parquet_files[0]
        test_file_path = os.path.join(DATA_DIR, test_file)
        
        report += f"### Testing Data Integrity for: {test_file}\n\n"
        
        # Read data directly from Parquet file
        try:
            parquet_table = pq.read_table(test_file_path)
            parquet_df = parquet_table.to_pandas()
            
            report += f"✅ **PASS**: Successfully read {len(parquet_df)} rows directly from Parquet file.\n\n"
            
            # Get schema information
            report += "#### Parquet File Schema\n"
            report += "| Column | Type |\n"
            report += "| ------ | ---- |\n"
            
            for field in parquet_table.schema:
                report += f"| {field.name} | {field.type} |\n"
            
            report += "\n"
            
            # Check if corresponding foreign table exists
            table_base_name = os.path.splitext(test_file)[0]
            
            results, column_names, error = execute_query(conn, 
                f"""SELECT table_name 
                   FROM information_schema.tables 
                   WHERE table_name = '{table_base_name}';""")
            
            if error or not results:
                report += f"⚠️ **WARNING**: Corresponding foreign table '{table_base_name}' not found.\n\n"
                report += "Checking all_sentiment view instead.\n\n"
                
                # Check all_sentiment view instead
                results, column_names, error = execute_query(conn, 
                    f"""SELECT * FROM all_sentiment
                       WHERE ticker = '{parquet_df['ticker'].iloc[0]}'
                       LIMIT 10;""")
                
                if error:
                    report += f"❌ **FAIL**: Error querying all_sentiment view: {error}\n\n"
                    return report
                
                # Compare sample rows
                report += f"✅ Retrieved {len(results)} rows from all_sentiment view for comparison.\n\n"
                
                # For simplicity, just compare counts
                parquet_count = len(parquet_df)
                
                results, column_names, error = execute_query(conn, 
                    f"""SELECT COUNT(*) FROM all_sentiment
                       WHERE ticker = '{parquet_df['ticker'].iloc[0]}';""")
                
                if error:
                    report += f"❌ **FAIL**: Error getting count from all_sentiment view: {error}\n\n"
                else:
                    db_count = results[0][0] if results else 0
                    
                    report += "#### Count Comparison\n"
                    report += f"- Parquet file row count: {parquet_count}\n"
                    report += f"- Database view row count: {db_count}\n\n"
                    
                    if db_count >= parquet_count:
                        report += "✅ **PASS**: Database contains at least as many rows as the Parquet file.\n\n"
                    else:
                        report += "❌ **FAIL**: Database contains fewer rows than the Parquet file.\n\n"
            
            else:
                # Query the foreign table
                results, column_names, error = execute_query(conn, f"SELECT * FROM {table_base_name} LIMIT 10;")
                
                if error:
                    report += f"❌ **FAIL**: Error querying foreign table: {error}\n\n"
                else:
                    report += f"✅ Retrieved {len(results)} rows from foreign table for comparison.\n\n"
                    
                    # For simplicity, just compare counts
                    parquet_count = len(parquet_df)
                    
                    results, column_names, error = execute_query(conn, f"SELECT COUNT(*) FROM {table_base_name};")
                    
                    if error:
                        report += f"❌ **FAIL**: Error getting count from foreign table: {error}\n\n"
                    else:
                        db_count = results[0][0] if results else 0
                        
                        report += "#### Count Comparison\n"
                        report += f"- Parquet file row count: {parquet_count}\n"
                        report += f"- Foreign table row count: {db_count}\n\n"
                        
                        if db_count == parquet_count:
                            report += "✅ **PASS**: Row counts match exactly.\n\n"
                        else:
                            report += "❌ **FAIL**: Row counts do not match.\n\n"
        
        except Exception as e:
            report += f"❌ **FAIL**: Error reading Parquet file: {e}\n\n"
    
    finally:
        conn.close()
    
    return report

def test_artifacts() -> str:
    """Verify all required artifacts are present and correct."""
    report = "## 10. Artifact and Deliverable Verification\n\n"
    
    artifacts = [
        {"name": "postgres.Dockerfile", "path": os.path.join(PROJECT_ROOT, "postgres.Dockerfile")},
        {"name": "init-fdw.sql", "path": os.path.join(PROJECT_ROOT, "init-fdw.sql")},
        {"name": "docker-compose.yml", "path": os.path.join(PROJECT_ROOT, "docker-compose.yml")},
        {"name": "BaseScraper (base.py)", "path": os.path.join(PROJECT_ROOT, "data_acquisition", "scrapers", "base.py")},
        {"name": "parquet_utils.py", "path": os.path.join(PROJECT_ROOT, "parquet_utils.py")},
        {"name": "optimize_parquet.sh", "path": os.path.join(PROJECT_ROOT, "cron_jobs", "optimize_parquet.sh")},
        {"name": "database.py (API)", "path": os.path.join(PROJECT_ROOT, "api", "database.py")},
        {"name": "sentiment.py (API routes)", "path": os.path.join(PROJECT_ROOT, "api", "routes", "sentiment.py")},
        {"name": "parquet_fdw.md (Documentation)", "path": os.path.join(PROJECT_ROOT, "Documentation", "parquet_fdw.md")},
        {"name": "data_acquisition requirements.txt", "path": os.path.join(PROJECT_ROOT, "data_acquisition", "requirements.txt")}
    ]
    
    report += "### Artifact Checklist\n\n"
    report += "| Artifact | Status | Notes |\n"
    report += "| -------- | ------ | ----- |\n"
    
    for artifact in artifacts:
        if os.path.exists(artifact["path"]):
            # Check file content for key elements
            with open(artifact["path"], 'r') as f:
                content = f.read()
            
            notes = []
            
            if "postgres.Dockerfile" in artifact["name"]:
                if "parquet_fdw" in content:
                    notes.append("Contains parquet_fdw references")
                else:
                    notes.append("Missing parquet_fdw references")
            
            elif "init-fdw.sql" in artifact["name"]:
                if "CREATE EXTENSION" in content and "parquet_fdw" in content:
                    notes.append("Contains CREATE EXTENSION commands")
                else:
                    notes.append("Missing CREATE EXTENSION commands")
            
            elif "docker-compose.yml" in artifact["name"]:
                if "postgres.Dockerfile" in content:
                    notes.append("References postgres.Dockerfile")
                else:
                    notes.append("Missing postgres.Dockerfile reference")
                
                if "/var/lib/postgresql/data/output" in content:
                    notes.append("Contains volume mount for Parquet files")
                else:
                    notes.append("Missing volume mount for Parquet files")
            
            elif "base.py" in artifact["name"]:
                if "_save_to_parquet" in content:
                    notes.append("Contains Parquet file writing functionality")
                else:
                    notes.append("Missing Parquet file writing functionality")
            
            elif "parquet_utils.py" in artifact["name"]:
                required_functions = ["deduplicate_parquet", "optimize_parquet"]
                missing = [func for func in required_functions if func not in content]
                if missing:
                    notes.append(f"Missing functions: {', '.join(missing)}")
                else:
                    notes.append("Contains required utility functions")
            
            elif "optimize_parquet.sh" in artifact["name"]:
                if "parquet_utils.py" in content:
                    notes.append("References parquet_utils.py")
                else:
                    notes.append("Missing parquet_utils.py reference")
            
            elif "database.py" in artifact["name"]:
                if "all_sentiment" in content:
                    notes.append("Contains FDW query functions")
                else:
                    notes.append("Missing FDW query functions")
            
            elif "sentiment.py" in artifact["name"]:
                if "query_sentiment_data" in content:
                    notes.append("References FDW query functions")
                else:
                    notes.append("Missing FDW query function references")
            
            elif "parquet_fdw.md" in artifact["name"]:
                if "parquet_fdw" in content and "Foreign Data Wrapper" in content:
                    notes.append("Contains FDW documentation")
                else:
                    notes.append("Missing FDW documentation")
            
            elif "requirements.txt" in artifact["name"]:
                if "pandas" in content and "pyarrow" in content:
                    notes.append("Contains pandas and pyarrow dependencies")
                else:
                    notes.append("Missing pandas and/or pyarrow dependencies")
            
            status = "✅ FOUND"
            notes_str = ", ".join(notes)
        else:
            status = "❌ MISSING"
            notes_str = ""
        
        report += f"| {artifact['name']} | {status} | {notes_str} |\n"
    
    return report

def test_documentation() -> str:
    """Review documentation for accuracy and completeness."""
    report = "## 11. Documentation Review\n\n"
    
    # Check for parquet_fdw.md
    doc_path = os.path.join(PROJECT_ROOT, "Documentation", "parquet_fdw.md")
    if not os.path.exists(doc_path):
        report += "❌ **FAIL**: parquet_fdw.md not found at the expected location.\n\n"
        return report
    
    with open(doc_path, 'r') as f:
        doc_content = f.read()
    
    # Check for key sections
    required_sections = [
        "Overview", "Architecture", "Setup", "Configuration", "Usage", "Best Practices", "Troubleshooting"
    ]
    
    report += "### Documentation Completeness\n\n"
    report += "| Section | Status | Notes |\n"
    report += "| ------- | ------ | ----- |\n"
    
    for section in required_sections:
        # Simple check - look for headings (# Section or ## Section)
        if re.search(r'#+ ' + section, doc_content, re.IGNORECASE):
            status = "✅ FOUND"
            notes = ""
        else:
            status = "❌ MISSING"
            notes = "Section not found in documentation"
        
        report += f"| {section} | {status} | {notes} |\n"
    
    # Check for code examples
    if "```" in doc_content:
        report += "\n✅ **PASS**: Documentation includes code examples.\n\n"
    else:
        report += "\n❌ **FAIL**: Documentation does not include code examples.\n\n"
    
    # Check for SQL examples
    if "```sql" in doc_content:
        report += "✅ **PASS**: Documentation includes SQL examples.\n\n"
    else:
        report += "❌ **FAIL**: Documentation does not include SQL examples.\n\n"
    
    # Check for diagrams or architecture description
    if "```mermaid" in doc_content or "![" in doc_content:
        report += "✅ **PASS**: Documentation includes diagrams or images.\n\n"
    else:
        report += "⚠️ **WARNING**: Documentation may not include diagrams or images.\n\n"
    
    # Overall assessment
    report += "### Overall Documentation Assessment\n\n"
    
    # Count issues
    missing_sections = sum(1 for section in required_sections if not re.search(r'#+ ' + section, doc_content, re.IGNORECASE))
    
    if missing_sections == 0 and "```" in doc_content and "```sql" in doc_content:
        report += "✅ **EXCELLENT**: Documentation is comprehensive, includes all required sections and code examples.\n\n"
    elif missing_sections <= 2 and "```" in doc_content:
        report += "✅ **GOOD**: Documentation covers most required sections and includes examples.\n\n"
    elif missing_sections <= 4:
        report += "⚠️ **FAIR**: Documentation is missing several key sections.\n\n"
    else:
        report += "❌ **POOR**: Documentation is significantly incomplete.\n\n"
    
    # Recommendations
    report += "### Recommendations\n\n"
    
    if missing_sections > 0:
        missing = [section for section in required_sections if not re.search(r'#+ ' + section, doc_content, re.IGNORECASE)]
        report += f"- Add the following sections: {', '.join(missing)}\n"
    
    if "```" not in doc_content:
        report += "- Add code examples\n"
    
    if "```sql" not in doc_content:
        report += "- Add SQL examples\n"
    
    if "```mermaid" not in doc_content and "![" not in doc_content:
        report += "- Add diagrams or images to illustrate the architecture\n"
    
    return report

def run_all_tests():
    """Run all test functions and generate reports."""
    # Create tests directory if it doesn't exist
    os.makedirs(TEST_DIR, exist_ok=True)
    
    # Dictionary to store report filenames
    report_files = {}
    
    # Run tests
    setup_report = test_build_image()
    _, report_files["setup"] = create_markdown_report("PostgreSQL Docker Image Build Test", setup_report, "setup")
    
    docker_report = test_docker_compose()
    _, report_files["docker"] = create_markdown_report("Docker Compose Stack Test", docker_report, "docker")
    
    fdw_init_report = test_fdw_initialization()
    _, report_files["fdw_init"] = create_markdown_report("FDW Initialization Test", fdw_init_report, "fdw_init")
    
    fdw_core_report = test_fdw_core_functionality()
    _, report_files["fdw_core"] = create_markdown_report("FDW Core Functionality Test", fdw_core_report, "fdw_core")
    
    file_mod_report = test_parquet_file_modification()
    _, report_files["file_mod"] = create_markdown_report("Parquet File Modification Test", file_mod_report, "file_mod")
    
    pipeline_report = test_data_pipeline_parquet()
    _, report_files["pipeline"] = create_markdown_report("Data Pipeline and Parquet Generation Test", pipeline_report, "pipeline")
    
    api_report = test_api_integration()
    _, report_files["api"] = create_markdown_report("API Integration Test", api_report, "api")
    
    performance_report = test_performance()
    _, report_files["performance"] = create_markdown_report("Performance Test", performance_report, "performance")
    
    integrity_report = test_data_integrity()
    _, report_files["integrity"] = create_markdown_report("Data Integrity Test", integrity_report, "integrity")
    
    artifacts_report = test_artifacts()
    _, report_files["artifacts"] = create_markdown_report("Artifact Verification", artifacts_report, "artifacts")
    
    doc_report = test_documentation()
    _, report_files["docs"] = create_markdown_report("Documentation Review", doc_report, "docs")
    
    # Create final summary report
    summary = f"""# parquet_fdw Implementation Test Summary

This report summarizes the results of comprehensive testing of the parquet_fdw implementation.

## Test Reports

1. [PostgreSQL Docker Image Build Test](./{report_files["setup"]})
2. [Docker Compose Stack Test](./{report_files["docker"]})
3. [FDW Initialization Test](./{report_files["fdw_init"]})
4. [FDW Core Functionality Test](./{report_files["fdw_core"]})
5. [Parquet File Modification Test](./{report_files["file_mod"]})
6. [Data Pipeline and Parquet Generation Test](./{report_files["pipeline"]})
7. [API Integration Test](./{report_files["api"]})
8. [Performance Test](./{report_files["performance"]})
9. [Data Integrity Test](./{report_files["integrity"]})
10. [Artifact Verification](./{report_files["artifacts"]})
11. [Documentation Review](./{report_files["docs"]})

## Conclusion

The parquet_fdw implementation has been thoroughly tested across multiple dimensions:

- Docker container builds and runtime
- FDW setup and configuration
- Query functionality and performance
- Data pipeline and Parquet file handling
- API integration and error handling
- Data integrity verification
- Artifact completeness and correctness
- Documentation quality

See individual test reports for detailed findings and recommendations.
"""
    
    _, summary_file = create_markdown_report("parquet_fdw Implementation Test Summary", summary, "summary")
    
    print(f"All tests completed. Reports saved to {TEST_DIR}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run parquet_fdw implementation tests")
    parser.add_argument("--test", choices=["all", "setup", "docker", "fdw-init", "fdw-core", 
                                         "file-mod", "pipeline", "api", "performance", 
                                         "integrity", "artifacts", "docs"], 
                      default="all", help="Specific test to run (default: all)")
    args = parser.parse_args()
    
    # Create tests directory if it doesn't exist
    os.makedirs(TEST_DIR, exist_ok=True)
    
    if args.test == "all":
        run_all_tests()
    elif args.test == "setup":
        report = test_build_image()
        create_markdown_report("PostgreSQL Docker Image Build Test", report, "setup")
    elif args.test == "docker":
        report = test_docker_compose()
        create_markdown_report("Docker Compose Stack Test", report, "docker")
    elif args.test == "fdw-init":
        report = test_fdw_initialization()
        create_markdown_report("FDW Initialization Test", report, "fdw_init")
    elif args.test == "fdw-core":
        report = test_fdw_core_functionality()
        create_markdown_report("FDW Core Functionality Test", report, "fdw_core")
    elif args.test == "file-mod":
        report = test_parquet_file_modification()
        create_markdown_report("Parquet File Modification Test", report, "file_mod")
    elif args.test == "pipeline":
        report = test_data_pipeline_parquet()
        create_markdown_report("Data Pipeline and Parquet Generation Test", report, "pipeline")
    elif args.test == "api":
        report = test_api_integration()
        create_markdown_report("API Integration Test", report, "api")
    elif args.test == "performance":
        report = test_performance()
        create_markdown_report("Performance Test", report, "performance")
    elif args.test == "integrity":
        report = test_data_integrity()
        create_markdown_report("Data Integrity Test", report, "integrity")
    elif args.test == "artifacts":
        report = test_artifacts()
        create_markdown_report("Artifact Verification", report, "artifacts")
    elif args.test == "docs":
        report = test_documentation()
        create_markdown_report("Documentation Review", report, "docs")