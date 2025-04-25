#!/bin/bash
# Start the parquet metrics server for local testing

cd "$(dirname "$0")/.."
CURRENT_DIR=$(pwd)

python data_acquisition/parquet_metrics_server.py --port 8082 --parquet-dir "${CURRENT_DIR}/data/output" --update-interval 30