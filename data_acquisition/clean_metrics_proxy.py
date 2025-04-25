#!/usr/bin/env python3
"""
Proxy server that strips HELP and TYPE comments from Prometheus metrics output.
This script acts as a reverse proxy for the actual metrics endpoint but
cleans up the output for a cleaner display.
"""
import os
import re
import argparse
import logging
import requests
from flask import Flask, Response
from waitress import serve

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Start a Prometheus metrics proxy that removes HELP and TYPE comments'
    )
    parser.add_argument('--port', type=int, default=8085,
                        help='Port to expose the clean metrics proxy on (default: 8085)')
    parser.add_argument('--target', type=str, default='http://localhost:8081/metrics',
                        help='Target metrics endpoint to proxy and clean (default: http://localhost:8081/metrics)')
    return parser.parse_args()

@app.route('/metrics')
def metrics():
    """
    Proxies the metrics endpoint but removes HELP and TYPE comments.
    """
    args = app.config['args']
    try:
        # Get metrics from the original endpoint
        r = requests.get(args.target, timeout=5)
        
        if r.status_code != 200:
            logger.warning(f"Target metrics endpoint returned status {r.status_code}")
            return Response(
                f"Error fetching metrics: HTTP {r.status_code}",
                status=r.status_code,
                mimetype='text/plain'
            )
        
        # Extract metrics content
        content = r.text
        
        # Remove HELP and TYPE comments using regex
        clean_content = re.sub(r'#\s+(?:HELP|TYPE)\s+[^\n]+\n', '', content)
        
        # Return the cleaned metrics
        return Response(clean_content, mimetype='text/plain')
    
    except requests.RequestException as e:
        logger.error(f"Error fetching metrics from {args.target}: {str(e)}")
        return Response(
            f"Error fetching metrics: {str(e)}",
            status=500,
            mimetype='text/plain'
        )

def main():
    """Main function."""
    args = parse_args()
    
    # Store args in app config for access in route handlers
    app.config['args'] = args
    
    logger.info(f"Starting metrics proxy on port {args.port}")
    logger.info(f"Target metrics endpoint: {args.target}")
    
    # Start the server
    print(f"Clean metrics proxy available at http://localhost:{args.port}/metrics")
    serve(app, host='0.0.0.0', port=args.port)

if __name__ == "__main__":
    main()