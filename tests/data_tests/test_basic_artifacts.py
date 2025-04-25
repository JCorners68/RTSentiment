#!/usr/bin/env python3
"""
Basic test script for parquet_fdw implementation that doesn't require external dependencies.
This script checks if the required files and artifacts are in place.
"""
import os
import sys
import datetime
import logging
import argparse
import re
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

def create_markdown_report(title: str, content: str, test_type: str) -> tuple[str, str]:
    """Create a Markdown report file with the given content."""
    # Get current date in YYMMDD format
    date_str = datetime.datetime.now().strftime('%y%m%d')
    
    # Create test_results directory if it doesn't exist
    results_dir = os.path.join(PROJECT_ROOT, "tests", "test_results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Find the next available sequence number
    seq_num = 1
    while True:
        filename = f"{test_type}_results_{date_str}_{seq_num}.md"
        if not os.path.exists(os.path.join(results_dir, filename)):
            break
        seq_num += 1
    
    report_path = os.path.join(results_dir, filename)
    
    with open(report_path, 'w') as f:
        f.write(f"# {title}\n\n")
        f.write(f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        f.write(f"**Test type:** {test_type}\n\n")
        f.write(content)
    
    logger.info(f"Report created: {report_path}")
    return report_path, filename

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
                    notes.append("Contains CREATE EXTENSION command")
                else:
                    notes.append("Missing CREATE EXTENSION command")
            
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

def test_docker_artifacts() -> str:
    """Test dockerfile and docker-compose configuration."""
    report = "## 1. Docker Configuration Verification\n\n"
    
    # Verify postgres.Dockerfile exists
    dockerfile_path = os.path.join(PROJECT_ROOT, "postgres.Dockerfile")
    if not os.path.exists(dockerfile_path):
        report += "❌ **FAIL**: postgres.Dockerfile not found at the expected location.\n\n"
        return report
    
    report += "✅ postgres.Dockerfile exists.\n\n"
    
    # Check dockerfile contents
    with open(dockerfile_path, 'r') as f:
        dockerfile_content = f.read()
    
    # Check for required components
    required_components = [
        ("PostgreSQL base image", "FROM postgres:14"),
        ("Build dependencies", "apt-get install"),
        ("Apache Arrow", "libarrow-dev"),
        ("Parquet library", "libparquet-dev"),
        ("parquet_fdw repo", "git clone https://github.com/adjust/parquet_fdw.git"),
        ("parquet_fdw build", "make && make install"),
        ("init-fdw.sql", "COPY init-fdw.sql /docker-entrypoint-initdb.d/")
    ]
    
    report += "### Dockerfile Component Check\n\n"
    report += "| Component | Status | Notes |\n"
    report += "| --------- | ------ | ----- |\n"
    
    for component_name, search_text in required_components:
        if search_text in dockerfile_content:
            status = "✅ FOUND"
            notes = ""
        else:
            status = "❌ MISSING"
            notes = f"Could not find '{search_text}'"
        
        report += f"| {component_name} | {status} | {notes} |\n"
    
    # Verify docker-compose.yml exists
    docker_compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    if not os.path.exists(docker_compose_path):
        report += "\n❌ **FAIL**: docker-compose.yml not found at the expected location.\n\n"
        return report
    
    report += "\n✅ docker-compose.yml exists.\n\n"
    
    # Check docker-compose.yml contents
    with open(docker_compose_path, 'r') as f:
        docker_compose_content = f.read()
    
    # Check for required components
    required_components = [
        ("postgres service", "postgres:"),
        ("custom dockerfile", "dockerfile: postgres.Dockerfile"),
        ("parquet data volume", "./data/output:/var/lib/postgresql/data/output")
    ]
    
    report += "### docker-compose.yml Component Check\n\n"
    report += "| Component | Status | Notes |\n"
    report += "| --------- | ------ | ----- |\n"
    
    for component_name, search_text in required_components:
        if search_text in docker_compose_content:
            status = "✅ FOUND"
            notes = ""
        else:
            status = "❌ MISSING"
            notes = f"Could not find '{search_text}'"
        
        report += f"| {component_name} | {status} | {notes} |\n"
    
    return report

def test_sql_init() -> str:
    """Test SQL initialization script."""
    report = "## 2. SQL Initialization Verification\n\n"
    
    # Verify init-fdw.sql exists
    init_sql_path = os.path.join(PROJECT_ROOT, "init-fdw.sql")
    if not os.path.exists(init_sql_path):
        report += "❌ **FAIL**: init-fdw.sql not found at the expected location.\n\n"
        return report
    
    report += "✅ init-fdw.sql exists.\n\n"
    
    # Check init-fdw.sql contents
    with open(init_sql_path, 'r') as f:
        init_sql_content = f.read()
    
    # Check for required SQL statements
    required_sql = [
        ("CREATE EXTENSION", "CREATE EXTENSION IF NOT EXISTS parquet_fdw"),
        ("CREATE SERVER", "CREATE SERVER IF NOT EXISTS parquet_srv FOREIGN DATA WRAPPER parquet_fdw"),
        ("CREATE USER MAPPING", "CREATE USER MAPPING IF NOT EXISTS FOR pgadmin SERVER parquet_srv"),
        ("CREATE FOREIGN TABLE", "CREATE FOREIGN TABLE IF NOT EXISTS"),
        ("Foreign table options", "OPTIONS (filename"),
        ("View definition", "CREATE OR REPLACE VIEW all_sentiment AS")
    ]
    
    report += "### SQL Component Check\n\n"
    report += "| Component | Status | Notes |\n"
    report += "| --------- | ------ | ----- |\n"
    
    for component_name, search_text in required_sql:
        if search_text in init_sql_content:
            status = "✅ FOUND"
            notes = ""
        else:
            status = "❌ MISSING"
            notes = f"Could not find '{search_text}'"
        
        report += f"| {component_name} | {status} | {notes} |\n"
    
    # Check for individual foreign tables
    foreign_tables = [
        "aapl_sentiment",
        "tsla_sentiment",
        "multi_ticker_sentiment"
    ]
    
    report += "\n### Foreign Table Check\n\n"
    report += "| Table | Status | Notes |\n"
    report += "| ----- | ------ | ----- |\n"
    
    for table in foreign_tables:
        if f"CREATE FOREIGN TABLE IF NOT EXISTS {table}" in init_sql_content:
            status = "✅ FOUND"
            notes = ""
        else:
            status = "❌ MISSING"
            notes = f"Could not find '{table}' foreign table"
        
        report += f"| {table} | {status} | {notes} |\n"
    
    return report

def test_parquet_files() -> str:
    """Check for required Parquet files."""
    report = "## 3. Parquet Files Verification\n\n"
    
    # Check for data/output directory
    if not os.path.exists(DATA_DIR):
        report += "❌ **FAIL**: data/output directory not found at the expected location.\n\n"
        return report
    
    report += "✅ data/output directory exists.\n\n"
    
    # List parquet files in directory
    parquet_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".parquet")]
    
    report += f"Found {len(parquet_files)} Parquet files in data/output directory.\n\n"
    
    # Check for required Parquet files
    required_files = [
        "aapl_sentiment.parquet",
        "tsla_sentiment.parquet",
        "multi_ticker_sentiment.parquet"
    ]
    
    report += "### Required Parquet Files Check\n\n"
    report += "| File | Status | Notes |\n"
    report += "| ---- | ------ | ----- |\n"
    
    for file in required_files:
        if file in parquet_files:
            status = "✅ FOUND"
            file_path = os.path.join(DATA_DIR, file)
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            notes = f"Size: {size_mb:.2f} MB"
        else:
            status = "❌ MISSING"
            notes = "File not found"
        
        report += f"| {file} | {status} | {notes} |\n"
    
    return report

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Basic tests for parquet_fdw implementation")
    parser.add_argument("--test", choices=["all", "artifacts", "docs", "docker", "sql", "parquet"], 
                      default="all", help="Specific test to run (default: all)")
    args = parser.parse_args()
    
    # Create test_results directory if it doesn't exist
    results_dir = os.path.join(PROJECT_ROOT, "tests", "test_results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Dictionary to store report filenames
    report_files = {}
    
    if args.test == "all" or args.test == "artifacts":
        artifacts_report = test_artifacts()
        _, report_files["artifacts"] = create_markdown_report("Artifact Verification", artifacts_report, "artifact")
        
    if args.test == "all" or args.test == "docs":
        docs_report = test_documentation()
        _, report_files["docs"] = create_markdown_report("Documentation Review", docs_report, "doc")
        
    if args.test == "all" or args.test == "docker":
        docker_report = test_docker_artifacts()
        _, report_files["docker"] = create_markdown_report("Docker Configuration Verification", docker_report, "docker")
        
    if args.test == "all" or args.test == "sql":
        sql_report = test_sql_init()
        _, report_files["sql"] = create_markdown_report("SQL Initialization Verification", sql_report, "sql")
        
    if args.test == "all" or args.test == "parquet":
        parquet_report = test_parquet_files()
        _, report_files["parquet"] = create_markdown_report("Parquet Files Verification", parquet_report, "parquet")
    
    if args.test == "all":
        # Create summary report with updated file links
        summary = f"""# parquet_fdw Implementation Test Summary

This report summarizes the results of basic testing of the parquet_fdw implementation.

## Test Reports

1. [Docker Configuration Verification](../{report_files["docker"]})
2. [SQL Initialization Verification](../{report_files["sql"]})
3. [Parquet Files Verification](../{report_files["parquet"]})
4. [Artifact Verification](../{report_files["artifacts"]})
5. [Documentation Review](../{report_files["docs"]})

## Conclusion

The basic artifacts and configurations for the parquet_fdw implementation have been verified. This includes:

- Docker configuration (Dockerfile and docker-compose.yml)
- SQL initialization scripts
- Presence of required Parquet files
- Required code components in various files
- Documentation quality and completeness

See individual test reports for detailed findings and recommendations.
"""
        create_markdown_report("parquet_fdw Implementation Test Summary", summary, "summary")
    
    print(f"All tests completed. Reports saved to {results_dir}")

if __name__ == "__main__":
    main()