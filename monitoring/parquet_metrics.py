#!/usr/bin/env python3
"""
Prometheus metrics for Parquet operations in the RTSentiment system.

This module defines and exports Prometheus metrics for monitoring Parquet file
operations, processing efficiency, data quality, and storage utilization. It
includes a standalone HTTP server and integrates with the RTSentiment system's
monitoring infrastructure.
"""

import argparse
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

from prometheus_client import start_http_server, Counter, Gauge, Histogram, Summary
from prometheus_client.exposition import generate_latest
from prometheus_client.registry import REGISTRY, CollectorRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("parquet_metrics")

# Define Prometheus metrics

# File operation metrics
PARQUET_READS = Counter(
    'parquet_reads_total', 
    'Total number of Parquet file reads',
    ['ticker', 'operation']
)

PARQUET_WRITES = Counter(
    'parquet_writes_total', 
    'Total number of Parquet file writes',
    ['ticker', 'operation']
)

READ_DURATION = Histogram(
    'parquet_read_duration_seconds', 
    'Duration of Parquet file read operations',
    ['ticker', 'operation'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

WRITE_DURATION = Histogram(
    'parquet_write_duration_seconds', 
    'Duration of Parquet file write operations',
    ['ticker', 'operation'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

QUERY_DURATION = Histogram(
    'parquet_query_duration_seconds', 
    'Duration of Parquet query operations',
    ['query_type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# Data volume metrics
FILE_SIZE = Gauge(
    'parquet_file_size_bytes', 
    'Size of Parquet files in bytes',
    ['ticker']
)

RECORD_COUNT = Gauge(
    'parquet_record_count', 
    'Number of records in Parquet files',
    ['ticker']
)

TOTAL_STORAGE = Gauge(
    'parquet_total_storage_bytes', 
    'Total storage used by all Parquet files in bytes'
)

# Data quality metrics
DATA_QUALITY_ISSUES = Counter(
    'parquet_data_quality_issues_total', 
    'Number of data quality issues detected',
    ['ticker', 'issue_type']
)

MISSING_VALUES = Gauge(
    'parquet_missing_values', 
    'Number of missing values in Parquet files',
    ['ticker', 'column']
)

SENTIMENT_DISTRIBUTION = Gauge(
    'parquet_sentiment_distribution', 
    'Distribution of sentiment values in Parquet files',
    ['ticker', 'sentiment_category']
)

# Processing efficiency metrics
CACHE_HITS = Counter(
    'parquet_cache_hits_total', 
    'Number of cache hits for Parquet data',
    ['ticker']
)

CACHE_MISSES = Counter(
    'parquet_cache_misses_total', 
    'Number of cache misses for Parquet data',
    ['ticker']
)

PROCESSING_EFFICIENCY = Gauge(
    'parquet_processing_efficiency', 
    'Efficiency metric for Parquet data processing (higher is better)',
    ['ticker', 'operation']
)

# Resource utilization
CPU_USAGE = Gauge(
    'parquet_cpu_usage', 
    'CPU usage during Parquet operations',
    ['operation']
)

MEMORY_USAGE = Gauge(
    'parquet_memory_usage_bytes', 
    'Memory usage during Parquet operations',
    ['operation']
)

# Maintenance metrics
LAST_COMPACTION = Gauge(
    'parquet_last_compaction_timestamp', 
    'Timestamp of last compaction operation',
    ['ticker']
)

COMPACTION_DURATION = Histogram(
    'parquet_compaction_duration_seconds', 
    'Duration of compaction operations',
    ['ticker'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0]
)

OPTIMIZATION_SAVINGS = Gauge(
    'parquet_optimization_storage_savings_bytes', 
    'Storage space saved through optimization operations',
    ['ticker']
)


class ParquetMetricsCollector:
    """
    Collects and reports metrics for Parquet operations.
    
    This class scans Parquet files in the specified directory and collects
    metrics about file sizes, record counts, data quality, and more.
    """
    
    def __init__(self, data_dir: str = None, scan_interval: int = 300):
        """
        Initialize the collector.
        
        Args:
            data_dir: Directory containing Parquet files
            scan_interval: Interval between scans in seconds
        """
        # Set default data directory if not provided
        if data_dir is None:
            self.data_dir = os.path.join(os.getcwd(), "data", "output")
        else:
            self.data_dir = data_dir
            
        self.scan_interval = scan_interval
        self.last_scan_time = 0
        self.ticker_files = {}
        self.metadata_cache = {}
        
        logger.info(f"Initialized ParquetMetricsCollector with data directory: {self.data_dir}")
    
    def scan_directory(self) -> None:
        """
        Scan the data directory for Parquet files and collect metrics.
        """
        current_time = time.time()
        
        # Only scan if scan interval has elapsed
        if current_time - self.last_scan_time < self.scan_interval:
            return
            
        self.last_scan_time = current_time
        logger.info(f"Scanning directory: {self.data_dir}")
        
        try:
            # Reset the ticker files mapping
            self.ticker_files = {}
            
            # Scan for Parquet files
            total_size = 0
            
            for file in os.listdir(self.data_dir):
                if file.endswith("_sentiment.parquet"):
                    file_path = os.path.join(self.data_dir, file)
                    ticker = file.split("_sentiment.parquet")[0].upper()
                    
                    if ticker == "MULTI":
                        ticker = "multi_ticker"
                    
                    self.ticker_files[ticker] = file_path
                    
                    # Get file size
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    
                    # Record file size metric
                    FILE_SIZE.labels(ticker=ticker).set(file_size)
                    
                    # Collect additional metrics
                    self._collect_file_metrics(ticker, file_path)
            
            # Record total storage metric
            TOTAL_STORAGE.set(total_size)
            
            logger.info(f"Scan complete. Found {len(self.ticker_files)} Parquet files.")
        
        except Exception as e:
            logger.error(f"Error scanning directory: {e}")
    
    def _collect_file_metrics(self, ticker: str, file_path: str) -> None:
        """
        Collect metrics for a specific Parquet file.
        
        Args:
            ticker: Ticker symbol
            file_path: Path to Parquet file
        """
        try:
            # Read Parquet metadata
            start_time = time.time()
            metadata = pq.read_metadata(file_path)
            read_time = time.time() - start_time
            
            # Record read duration
            READ_DURATION.labels(ticker=ticker, operation="metadata").observe(read_time)
            PARQUET_READS.labels(ticker=ticker, operation="metadata").inc()
            
            # Record row count
            row_count = metadata.num_rows
            RECORD_COUNT.labels(ticker=ticker).set(row_count)
            
            # Check if we need to read full file for more detailed metrics
            if ticker not in self.metadata_cache or current_time - self.metadata_cache.get(ticker, {}).get("timestamp", 0) > self.scan_interval * 2:
                self._collect_detailed_metrics(ticker, file_path)
        
        except Exception as e:
            logger.error(f"Error collecting metrics for {ticker}: {e}")
            DATA_QUALITY_ISSUES.labels(ticker=ticker, issue_type="metadata_read_error").inc()
    
    def _collect_detailed_metrics(self, ticker: str, file_path: str) -> None:
        """
        Collect detailed metrics requiring full file reading.
        
        Args:
            ticker: Ticker symbol
            file_path: Path to Parquet file
        """
        try:
            # Read Parquet table
            start_time = time.time()
            table = pq.read_table(file_path)
            read_time = time.time() - start_time
            
            # Record read duration
            READ_DURATION.labels(ticker=ticker, operation="full_read").observe(read_time)
            PARQUET_READS.labels(ticker=ticker, operation="full_read").inc()
            
            # Get column names
            columns = table.column_names
            
            # Check for missing values
            for column in columns:
                if column in table.schema.names:
                    column_data = table.column(column)
                    null_count = column_data.null_count
                    MISSING_VALUES.labels(ticker=ticker, column=column).set(null_count)
            
            # Analyze sentiment distribution if present
            if "sentiment" in columns:
                sentiment_column = table.column("sentiment")
                sentiment_values = sentiment_column.to_pandas()
                
                # Count sentiment categories
                positive_count = len(sentiment_values[sentiment_values > 0.3])
                negative_count = len(sentiment_values[sentiment_values < -0.3])
                neutral_count = len(sentiment_values) - positive_count - negative_count
                
                SENTIMENT_DISTRIBUTION.labels(ticker=ticker, sentiment_category="positive").set(positive_count)
                SENTIMENT_DISTRIBUTION.labels(ticker=ticker, sentiment_category="negative").set(negative_count)
                SENTIMENT_DISTRIBUTION.labels(ticker=ticker, sentiment_category="neutral").set(neutral_count)
            
            # Store metadata in cache
            self.metadata_cache[ticker] = {
                "timestamp": time.time(),
                "columns": columns,
                "row_count": table.num_rows
            }
            
            # Record processing efficiency
            processing_rate = table.num_rows / max(read_time, 0.001)  # rows per second
            PROCESSING_EFFICIENCY.labels(ticker=ticker, operation="read").set(processing_rate)
            
        except Exception as e:
            logger.error(f"Error collecting detailed metrics for {ticker}: {e}")
            DATA_QUALITY_ISSUES.labels(ticker=ticker, issue_type="detailed_analysis_error").inc()
    
    def track_read_operation(self, ticker: str, operation: str, duration: float, records_read: int) -> None:
        """
        Track a read operation for metrics.
        
        Args:
            ticker: Ticker symbol
            operation: Type of read operation
            duration: Duration in seconds
            records_read: Number of records read
        """
        READ_DURATION.labels(ticker=ticker, operation=operation).observe(duration)
        PARQUET_READS.labels(ticker=ticker, operation=operation).inc()
        
        # Calculate and record processing efficiency
        if duration > 0:
            processing_rate = records_read / duration  # records per second
            PROCESSING_EFFICIENCY.labels(ticker=ticker, operation=operation).set(processing_rate)
    
    def track_write_operation(self, ticker: str, operation: str, duration: float, records_written: int) -> None:
        """
        Track a write operation for metrics.
        
        Args:
            ticker: Ticker symbol
            operation: Type of write operation
            duration: Duration in seconds
            records_written: Number of records written
        """
        WRITE_DURATION.labels(ticker=ticker, operation=operation).observe(duration)
        PARQUET_WRITES.labels(ticker=ticker, operation=operation).inc()
        
        # Calculate and record processing efficiency
        if duration > 0:
            processing_rate = records_written / duration  # records per second
            PROCESSING_EFFICIENCY.labels(ticker=ticker, operation=operation).set(processing_rate)
    
    def track_query_operation(self, query_type: str, duration: float) -> None:
        """
        Track a query operation for metrics.
        
        Args:
            query_type: Type of query
            duration: Duration in seconds
        """
        QUERY_DURATION.labels(query_type=query_type).observe(duration)
    
    def track_cache_hit(self, ticker: str) -> None:
        """
        Track a cache hit.
        
        Args:
            ticker: Ticker symbol
        """
        CACHE_HITS.labels(ticker=ticker).inc()
    
    def track_cache_miss(self, ticker: str) -> None:
        """
        Track a cache miss.
        
        Args:
            ticker: Ticker symbol
        """
        CACHE_MISSES.labels(ticker=ticker).inc()
    
    def track_data_quality_issue(self, ticker: str, issue_type: str) -> None:
        """
        Track a data quality issue.
        
        Args:
            ticker: Ticker symbol
            issue_type: Type of quality issue
        """
        DATA_QUALITY_ISSUES.labels(ticker=ticker, issue_type=issue_type).inc()
    
    def track_compaction(self, ticker: str, duration: float, storage_savings: int) -> None:
        """
        Track a compaction operation.
        
        Args:
            ticker: Ticker symbol
            duration: Duration in seconds
            storage_savings: Bytes saved
        """
        COMPACTION_DURATION.labels(ticker=ticker).observe(duration)
        LAST_COMPACTION.labels(ticker=ticker).set(time.time())
        OPTIMIZATION_SAVINGS.labels(ticker=ticker).set(storage_savings)
    
    def run_metrics_server(self, port: int = 8082) -> None:
        """
        Run a metrics server for Prometheus to scrape.
        
        Args:
            port: Port to listen on
        """
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
        
        try:
            while True:
                # Scan for metrics
                self.scan_directory()
                
                # Sleep for a bit
                time.sleep(min(60, self.scan_interval / 2))
        except KeyboardInterrupt:
            logger.info("Stopping metrics server")


def create_parquet_dashboard() -> Dict[str, Any]:
    """
    Create a Grafana dashboard configuration for Parquet metrics.
    
    This is a programmatic representation of the Grafana dashboard.
    The actual JSON will be saved to a file.
    
    Returns:
        Dict containing the Grafana dashboard configuration
    """
    dashboard = {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": "-- Grafana --",
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard"
                }
            ]
        },
        "editable": True,
        "gnetId": None,
        "graphTooltip": 0,
        "id": None,
        "links": [],
        "panels": [
            # Header row
            {
                "gridPos": {
                    "h": 1,
                    "w": 24,
                    "x": 0,
                    "y": 0
                },
                "id": 1,
                "title": "Parquet Operations",
                "type": "row"
            },
            # Read Operations panel
            {
                "aliasColors": {},
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 0,
                    "y": 1
                },
                "hiddenSeries": False,
                "id": 2,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "rate(parquet_reads_total[5m])",
                        "legendFormat": "{{ticker}} - {{operation}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Parquet Read Operations",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "ops",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            # Write Operations panel
            {
                "aliasColors": {},
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 12,
                    "y": 1
                },
                "hiddenSeries": False,
                "id": 3,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "rate(parquet_writes_total[5m])",
                        "legendFormat": "{{ticker}} - {{operation}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Parquet Write Operations",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "ops",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            # Operation Duration panels
            {
                "aliasColors": {},
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 0,
                    "y": 9
                },
                "hiddenSeries": False,
                "id": 4,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "rate(parquet_read_duration_seconds_sum[5m]) / rate(parquet_read_duration_seconds_count[5m])",
                        "legendFormat": "{{ticker}} - {{operation}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Average Read Duration",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "s",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            {
                "aliasColors": {},
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 12,
                    "y": 9
                },
                "hiddenSeries": False,
                "id": 5,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "rate(parquet_write_duration_seconds_sum[5m]) / rate(parquet_write_duration_seconds_count[5m])",
                        "legendFormat": "{{ticker}} - {{operation}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Average Write Duration",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "s",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            # Data Volume row
            {
                "gridPos": {
                    "h": 1,
                    "w": 24,
                    "x": 0,
                    "y": 17
                },
                "id": 6,
                "title": "Data Volume",
                "type": "row"
            },
            # File Size panel
            {
                "datasource": "Prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {
                            "mode": "thresholds"
                        },
                        "mappings": [],
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {
                                    "color": "green",
                                    "value": None
                                },
                                {
                                    "color": "red",
                                    "value": 1073741824
                                }
                            ]
                        },
                        "unit": "bytes"
                    },
                    "overrides": []
                },
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 0,
                    "y": 18
                },
                "id": 7,
                "options": {
                    "displayMode": "gradient",
                    "orientation": "horizontal",
                    "reduceOptions": {
                        "calcs": [
                            "lastNotNull"
                        ],
                        "fields": "",
                        "values": False
                    },
                    "showUnfilled": True,
                    "text": {}
                },
                "pluginVersion": "7.4.0",
                "targets": [
                    {
                        "expr": "parquet_file_size_bytes",
                        "instant": True,
                        "legendFormat": "{{ticker}}",
                        "refId": "A"
                    }
                ],
                "title": "File Sizes",
                "type": "bargauge"
            },
            # Record Count panel
            {
                "datasource": "Prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {
                            "mode": "thresholds"
                        },
                        "mappings": [],
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {
                                    "color": "green",
                                    "value": None
                                },
                                {
                                    "color": "yellow",
                                    "value": 100000
                                },
                                {
                                    "color": "red",
                                    "value": 1000000
                                }
                            ]
                        },
                        "unit": "short"
                    },
                    "overrides": []
                },
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 12,
                    "y": 18
                },
                "id": 8,
                "options": {
                    "displayMode": "gradient",
                    "orientation": "horizontal",
                    "reduceOptions": {
                        "calcs": [
                            "lastNotNull"
                        ],
                        "fields": "",
                        "values": False
                    },
                    "showUnfilled": True,
                    "text": {}
                },
                "pluginVersion": "7.4.0",
                "targets": [
                    {
                        "expr": "parquet_record_count",
                        "instant": True,
                        "legendFormat": "{{ticker}}",
                        "refId": "A"
                    }
                ],
                "title": "Record Counts",
                "type": "bargauge"
            },
            # Total Storage panel
            {
                "datasource": "Prometheus",
                "fieldConfig": {
                    "defaults": {
                        "color": {
                            "mode": "thresholds"
                        },
                        "mappings": [],
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {
                                    "color": "green",
                                    "value": None
                                },
                                {
                                    "color": "yellow",
                                    "value": 10737418240
                                },
                                {
                                    "color": "red",
                                    "value": 53687091200
                                }
                            ]
                        },
                        "unit": "bytes"
                    },
                    "overrides": []
                },
                "gridPos": {
                    "h": 8,
                    "w": 24,
                    "x": 0,
                    "y": 26
                },
                "id": 9,
                "options": {
                    "orientation": "auto",
                    "reduceOptions": {
                        "calcs": [
                            "lastNotNull"
                        ],
                        "fields": "",
                        "values": False
                    },
                    "showThresholdLabels": False,
                    "showThresholdMarkers": True,
                    "text": {}
                },
                "pluginVersion": "7.4.0",
                "targets": [
                    {
                        "expr": "parquet_total_storage_bytes",
                        "instant": True,
                        "legendFormat": "Total Storage",
                        "refId": "A"
                    }
                ],
                "title": "Total Parquet Storage",
                "type": "gauge"
            },
            # Data Quality row
            {
                "gridPos": {
                    "h": 1,
                    "w": 24,
                    "x": 0,
                    "y": 34
                },
                "id": 10,
                "title": "Data Quality",
                "type": "row"
            },
            # Data Quality Issues panel
            {
                "aliasColors": {},
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 0,
                    "y": 35
                },
                "hiddenSeries": False,
                "id": 11,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "rate(parquet_data_quality_issues_total[5m])",
                        "legendFormat": "{{ticker}} - {{issue_type}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Data Quality Issues",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            # Missing Values panel
            {
                "aliasColors": {},
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 12,
                    "y": 35
                },
                "hiddenSeries": False,
                "id": 12,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "parquet_missing_values",
                        "legendFormat": "{{ticker}} - {{column}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Missing Values",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            # Sentiment Distribution panel
            {
                "aliasColors": {
                    "negative": "red",
                    "neutral": "blue",
                    "positive": "green"
                },
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 24,
                    "x": 0,
                    "y": 43
                },
                "hiddenSeries": False,
                "id": 13,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": True,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "sum by(sentiment_category) (parquet_sentiment_distribution)",
                        "legendFormat": "{{sentiment_category}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Sentiment Distribution",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            # Cache and Efficiency row
            {
                "gridPos": {
                    "h": 1,
                    "w": 24,
                    "x": 0,
                    "y": 51
                },
                "id": 14,
                "title": "Cache and Efficiency",
                "type": "row"
            },
            # Cache Performance panel
            {
                "aliasColors": {
                    "Cache Hits": "green",
                    "Cache Misses": "red"
                },
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 0,
                    "y": 52
                },
                "hiddenSeries": False,
                "id": 15,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "sum(rate(parquet_cache_hits_total[5m]))",
                        "legendFormat": "Cache Hits",
                        "refId": "A"
                    },
                    {
                        "expr": "sum(rate(parquet_cache_misses_total[5m]))",
                        "legendFormat": "Cache Misses",
                        "refId": "B"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Cache Performance",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "ops",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            # Processing Efficiency panel
            {
                "aliasColors": {},
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 12,
                    "y": 52
                },
                "hiddenSeries": False,
                "id": 16,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "parquet_processing_efficiency",
                        "legendFormat": "{{ticker}} - {{operation}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Processing Efficiency (records/second)",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            # Maintenance row
            {
                "gridPos": {
                    "h": 1,
                    "w": 24,
                    "x": 0,
                    "y": 60
                },
                "id": 17,
                "title": "Maintenance",
                "type": "row"
            },
            # Compaction Duration panel
            {
                "aliasColors": {},
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 0,
                    "y": 61
                },
                "hiddenSeries": False,
                "id": 18,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "rate(parquet_compaction_duration_seconds_sum[5m]) / rate(parquet_compaction_duration_seconds_count[5m])",
                        "legendFormat": "{{ticker}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Compaction Duration",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "s",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            },
            # Optimization Savings panel
            {
                "aliasColors": {},
                "bars": False,
                "dashLength": 10,
                "dashes": False,
                "datasource": "Prometheus",
                "fill": 1,
                "fillGradient": 0,
                "gridPos": {
                    "h": 8,
                    "w": 12,
                    "x": 12,
                    "y": 61
                },
                "hiddenSeries": False,
                "id": 19,
                "legend": {
                    "avg": False,
                    "current": False,
                    "max": False,
                    "min": False,
                    "show": True,
                    "total": False,
                    "values": False
                },
                "lines": True,
                "linewidth": 1,
                "nullPointMode": "null",
                "options": {
                    "dataLinks": []
                },
                "percentage": False,
                "pointradius": 2,
                "points": False,
                "renderer": "flot",
                "seriesOverrides": [],
                "spaceLength": 10,
                "stack": False,
                "steppedLine": False,
                "targets": [
                    {
                        "expr": "parquet_optimization_storage_savings_bytes",
                        "legendFormat": "{{ticker}}",
                        "refId": "A"
                    }
                ],
                "thresholds": [],
                "timeFrom": None,
                "timeRegions": [],
                "timeShift": None,
                "title": "Optimization Storage Savings",
                "tooltip": {
                    "shared": True,
                    "sort": 0,
                    "value_type": "individual"
                },
                "type": "graph",
                "xaxis": {
                    "buckets": None,
                    "mode": "time",
                    "name": None,
                    "show": True,
                    "values": []
                },
                "yaxes": [
                    {
                        "format": "bytes",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    },
                    {
                        "format": "short",
                        "label": None,
                        "logBase": 1,
                        "max": None,
                        "min": None,
                        "show": True
                    }
                ],
                "yaxis": {
                    "align": False,
                    "alignLevel": None
                }
            }
        ],
        "refresh": "10s",
        "schemaVersion": 26,
        "style": "dark",
        "tags": [
            "parquet",
            "sentiment",
            "storage"
        ],
        "templating": {
            "list": []
        },
        "time": {
            "from": "now-6h",
            "to": "now"
        },
        "timepicker": {
            "refresh_intervals": [
                "5s",
                "10s",
                "30s",
                "1m",
                "5m",
                "15m",
                "30m",
                "1h",
                "2h",
                "1d"
            ]
        },
        "timezone": "",
        "title": "Parquet Pipeline",
        "uid": "parquet-pipeline",
        "version": 1
    }
    
    return dashboard


def main():
    """Main function to run the metrics collector server."""
    parser = argparse.ArgumentParser(description='Parquet Metrics Collector')
    parser.add_argument('--port', type=int, default=8082, help='Port to run metrics server on')
    parser.add_argument('--data-dir', type=str, default=None, help='Directory containing Parquet files')
    parser.add_argument('--scan-interval', type=int, default=300, help='Interval between scans in seconds')
    parser.add_argument('--create-dashboard', action='store_true', help='Create Grafana dashboard JSON')
    parser.add_argument('--dashboard-path', type=str, default='monitoring/grafana/dashboards/parquet_pipeline.json', 
                        help='Path to save dashboard JSON')
    
    args = parser.parse_args()
    
    if args.create_dashboard:
        # Create and save dashboard JSON
        dashboard = create_parquet_dashboard()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(args.dashboard_path), exist_ok=True)
        
        # Save dashboard JSON
        with open(args.dashboard_path, 'w') as f:
            import json
            json.dump(dashboard, f, indent=2)
            
        logger.info(f"Dashboard JSON saved to {args.dashboard_path}")
        return
    
    # Create and run metrics collector
    collector = ParquetMetricsCollector(
        data_dir=args.data_dir,
        scan_interval=args.scan_interval
    )
    
    collector.run_metrics_server(port=args.port)


if __name__ == "__main__":
    main()