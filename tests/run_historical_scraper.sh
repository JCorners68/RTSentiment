#!/bin/bash
# Script to run the historical scraper with metrics enabled

# Default settings
START_DATE=$(date -d '30 days ago' '+%Y-%m-%d')
END_DATE=$(date '+%Y-%m-%d')
SOURCE="news"
METRICS_PORT=8081
NO_METRICS=0
NO_DEDUP=0
RESET_DEDUP=0

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --start-date)
      START_DATE="$2"
      shift 2
      ;;
    --end-date)
      END_DATE="$2"
      shift 2
      ;;
    --source)
      SOURCE="$2"
      shift 2
      ;;
    --metrics-port)
      METRICS_PORT="$2"
      shift 2
      ;;
    --no-metrics)
      NO_METRICS=1
      shift
      ;;
    --no-dedup)
      NO_DEDUP=1
      shift
      ;;
    --reset-dedup)
      RESET_DEDUP=1
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --start-date DATE   Start date for scraping (YYYY-MM-DD, default: 30 days ago)"
      echo "  --end-date DATE     End date for scraping (YYYY-MM-DD, default: today)"
      echo "  --source TYPE       Source to scrape (news or reddit, default: news)"
      echo "  --metrics-port PORT Port for Prometheus metrics (default: 8081)"
      echo "  --no-metrics        Disable metrics collection"
      echo "  --no-dedup          Disable deduplication"
      echo "  --reset-dedup       Reset deduplication history"
      echo "  --help              Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Historical Scraper Runner"
echo "========================="
echo "Start Date: $START_DATE"
echo "End Date:   $END_DATE"
echo "Source:     $SOURCE"
echo "Metrics:    $([ $NO_METRICS -eq 0 ] && echo "Enabled (port $METRICS_PORT)" || echo "Disabled")"
echo "Dedup:      $([ $NO_DEDUP -eq 0 ] && echo "Enabled" || echo "Disabled")"
echo "Reset Dedup: $([ $RESET_DEDUP -eq 0 ] && echo "No" || echo "Yes")"
echo "========================="

# Build the command
CMD="cd /home/jonat/WSL_RT_Sentiment && python3 -m tests.data_tests.scrape_history --start_date $START_DATE --end_date $END_DATE --source $SOURCE"

# Add optional flags
if [ $NO_METRICS -eq 1 ]; then
  CMD+=" --no-metrics"
else
  CMD+=" --metrics-port $METRICS_PORT"
fi

if [ $NO_DEDUP -eq 1 ]; then
  CMD+=" --no-dedup"
fi

if [ $RESET_DEDUP -eq 1 ]; then
  CMD+=" --reset-dedup"
fi

# Run the command
echo "Running: $CMD"
echo "------------------------"
eval $CMD