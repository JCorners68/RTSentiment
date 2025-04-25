#!/bin/bash
# Script to display clean metrics without HELP and TYPE comment lines

# Default to clean metrics endpoint
ENDPOINT="http://localhost:8085/metrics"
GREP_PATTERN=""
USE_CLEAN=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --raw)
            # Switch to raw metrics endpoint
            ENDPOINT="http://localhost:8081/metrics"
            USE_CLEAN=false
            shift
            ;;
        --filter=*)
            # Extract pattern after =
            GREP_PATTERN="${1#*=}"
            shift
            ;;
        --filter)
            # Next argument is the pattern
            GREP_PATTERN="$2"
            shift 2
            ;;
        *)
            # Unknown option
            echo "Unknown option: $1"
            echo "Usage: $0 [--raw] [--filter=pattern]"
            exit 1
            ;;
    esac
done

# Display header
if [ "$USE_CLEAN" = true ]; then
    echo "=== Clean Metrics (comments removed) ==="
else
    echo "=== Raw Metrics (with HELP and TYPE) ==="
fi

# Check if pattern is specified
if [ -n "$GREP_PATTERN" ]; then
    echo "Filtering for: $GREP_PATTERN"
    curl -s "$ENDPOINT" | grep "$GREP_PATTERN"
else
    # No pattern, show all metrics
    curl -s "$ENDPOINT"
fi