#!/bin/bash
# Run tests for the parquet metrics server

cd "$(dirname "$0")/.."
python -m pytest tests/test_parquet_metrics.py -v