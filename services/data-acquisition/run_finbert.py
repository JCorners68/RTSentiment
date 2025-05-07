#!/usr/bin/env python3
"""
FinBERT Sentiment Analysis Runner Script

This script provides an easy way to run the FinBERT sentiment analysis pipeline
with control over GPU/CPU usage.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add the src directory to the path so we can import modules
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import process_news
import visualize_sentiment


def validate_data_paths():
    """Validate that data directories exist and contain necessary files."""
    # Base data directory
    data_dir = Path(current_dir, "data")
    if not data_dir.exists():
        print(f"ERROR: Data directory {data_dir} does not exist")
        return False
    
    # Check for news data
    news_dir = data_dir / "news"
    if not news_dir.exists():
        print(f"ERROR: News directory {news_dir} does not exist")
        return False
    
    # Check if there are any news files
    news_files = list(news_dir.glob("*_news.csv"))
    if not news_files:
        print(f"ERROR: No news data files found in {news_dir}")
        return False
    
    print(f"Found {len(news_files)} news data files")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run FinBERT sentiment analysis pipeline with GPU/CPU control",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Device control options
    device_group = parser.add_argument_group("Device Control")
    device_group.add_argument("--cpu", action="store_true", 
                             help="Force CPU usage (even if GPU is available)")
    device_group.add_argument("--gpu", action="store_true",
                             help="Force GPU usage (will fail if GPU is not compatible)")
    
    # Pipeline control options
    pipeline_group = parser.add_argument_group("Pipeline Control")
    pipeline_group.add_argument("--skip-processing", action="store_true",
                              help="Skip sentiment processing, use existing results")
    pipeline_group.add_argument("--skip-visualization", action="store_true",
                              help="Skip visualization generation")
    pipeline_group.add_argument("--ticker", type=str, 
                              help="Process only the specified ticker (e.g., AAPL)")
    
    # Output control options
    output_group = parser.add_argument_group("Output Control")
    output_group.add_argument("--verbose", "-v", action="store_true",
                            help="Enable verbose output")
    output_group.add_argument("--debug", action="store_true",
                            help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Configure environment variables for GPU/CPU control
    if args.cpu:
        os.environ["USE_CUDA"] = "no"
        print("Forcing CPU usage for sentiment analysis")
    elif args.gpu:
        os.environ["USE_CUDA"] = "yes"
        print("Forcing GPU usage for sentiment analysis")
    else:
        os.environ["USE_CUDA"] = "auto"
        print("Automatically selecting device (GPU if compatible, otherwise CPU)")
    
    # Configure logging level
    if args.debug:
        os.environ["LOG_LEVEL"] = "DEBUG"
    elif args.verbose:
        os.environ["LOG_LEVEL"] = "INFO"
    else:
        os.environ["LOG_LEVEL"] = "INFO"
    
    # Validate data paths before starting
    if not validate_data_paths():
        return 1
    
    print("\n" + "=" * 80)
    print(" FINBERT SENTIMENT ANALYSIS PIPELINE ".center(80))
    print("=" * 80)
    
    # Run sentiment processing if not skipped
    if not args.skip_processing:
        print("\n" + "-" * 80)
        print(" PROCESSING NEWS DATA ".center(80))
        print("-" * 80)
        
        # Call process_news with appropriate arguments
        process_args = []
        if args.ticker:
            process_args.extend(["--ticker", args.ticker])
        
        try:
            # Process the news data
            processed_data = process_news.main(process_args)
            print(f"Processed {len(processed_data)} news items with sentiment analysis")
        except Exception as e:
            print(f"ERROR: Failed to process news data: {e}")
            return 1
    
    # Run visualization if not skipped
    if not args.skip_visualization:
        print("\n" + "-" * 80)
        print(" GENERATING VISUALIZATIONS ".center(80))
        print("-" * 80)
        
        # Call visualize_sentiment with appropriate arguments
        visualization_args = []
        if args.ticker:
            visualization_args.extend(["--ticker", args.ticker])
        
        try:
            # Generate visualizations
            visualize_sentiment.main(visualization_args)
            print("Visualization generation complete")
        except Exception as e:
            print(f"ERROR: Failed to generate visualizations: {e}")
            return 1
    
    print("\n" + "=" * 80)
    print(" PIPELINE COMPLETED SUCCESSFULLY ".center(80))
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())