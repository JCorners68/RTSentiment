#!/bin/bash
# Script to run the optimize_parquet.py script as a cron job

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}/.."

# Configure logging
LOG_DIR="./data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/optimize_parquet_$(date +%Y%m%d).log"

# Data directory
DATA_DIR="./data/output"

# Run the parquet optimization
echo "$(date): Starting Parquet optimization" >> "$LOG_FILE"
python3 parquet_utils.py process-all --dir "$DATA_DIR" --action optimize --sort-by timestamp --compression SNAPPY >> "$LOG_FILE" 2>&1

# Report status
if [ $? -eq 0 ]; then
    echo "$(date): Parquet optimization completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Parquet optimization failed with exit code $?" >> "$LOG_FILE"
fi

# Run deduplication if needed
echo "$(date): Starting Parquet deduplication" >> "$LOG_FILE"
python3 parquet_utils.py process-all --dir "$DATA_DIR" --action dedup --key-cols article_id ticker >> "$LOG_FILE" 2>&1

# Report status
if [ $? -eq 0 ]; then
    echo "$(date): Parquet deduplication completed successfully" >> "$LOG_FILE"
else
    echo "$(date): Parquet deduplication failed with exit code $?" >> "$LOG_FILE"
fi

echo "$(date): Parquet processing job completed" >> "$LOG_FILE"