#!/bin/bash
# Test script for the metrics server

# Default port
PORT=8081
HOST="localhost"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      PORT="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Testing metrics server at http://$HOST:$PORT/metrics"

# Check if the server is running
if ! curl -s "http://$HOST:$PORT/metrics" > /dev/null; then
  echo "ERROR: Metrics server is not running at http://$HOST:$PORT/metrics"
  exit 1
fi

echo "✅ Metrics server is running"

# Check for our custom metrics
if ! curl -s "http://$HOST:$PORT/metrics" | grep -q "scraper_items_scraped_total"; then
  echo "ERROR: Custom metrics not found"
  exit 1
fi

echo "✅ Custom metrics are present"

# Show the metrics overview
echo "Scraper Metrics Summary:"
echo "========================"
echo "Unique Items:"
curl -s "http://$HOST:$PORT/metrics" | grep "scraper_unique_items_total" | grep -v "#"

echo "Cache Hits:"
curl -s "http://$HOST:$PORT/metrics" | grep "scraper_cache_hits_total" | grep -v "#"

echo "Errors:"
curl -s "http://$HOST:$PORT/metrics" | grep "scraper_errors_total" | grep -v "#" || echo "No errors reported."

echo "Uptime (seconds):"
curl -s "http://$HOST:$PORT/metrics" | grep "scraper_uptime_seconds" | grep -v "#"

echo "========================"
echo "All metrics available at: http://$HOST:$PORT/metrics"
echo "Test completed successfully!"