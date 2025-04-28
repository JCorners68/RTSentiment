#!/usr/bin/env python3
import pandas as pd
import pyarrow.parquet as pq
import os
import base64
from datetime import datetime

def create_html_report(parquet_file, analysis_dir, output_file):
    """Create an HTML report summarizing sentiment analysis results."""
    
    # Read the parquet file
    table = pq.read_table(parquet_file)
    df = table.to_pandas()
    
    # Basic statistics
    stats = {
        'Record count': len(df),
        'Unique tickers': df['ticker'].nunique(),
        'Unique sources': df['source'].nunique(),
        'Date range': f"{df['timestamp'].min()} to {df['timestamp'].max()}"
    }
    
    # Read the ticker analysis files
    try:
        ticker_sentiment = pd.read_csv(f'{analysis_dir}/ticker_sentiment.csv')
        top_tickers = pd.read_csv(f'{analysis_dir}/top_tickers.csv')
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return
    
    # Function to encode images as base64 for embedding in HTML
    def img_to_base64(img_path):
        try:
            with open(img_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error reading image {img_path}: {e}")
            return ""
    
    # Encode images
    images = {
        'top_tickers': img_to_base64(f'{analysis_dir}/top_tickers.png'),
        'sources': img_to_base64(f'{analysis_dir}/sources.png'),
        'sentiment_distribution': img_to_base64(f'{analysis_dir}/sentiment_distribution.png'),
        'top_positive_sentiment': img_to_base64(f'{analysis_dir}/top_positive_sentiment.png'),
        'top_negative_sentiment': img_to_base64(f'{analysis_dir}/top_negative_sentiment.png')
    }
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sentiment Analysis Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .stats {{ display: flex; flex-wrap: wrap; margin-bottom: 20px; }}
            .stat-box {{ background-color: #f5f5f5; border-radius: 5px; padding: 15px; margin: 10px; flex: 1; min-width: 200px; }}
            .image-container {{ margin: 20px 0; }}
            img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 5px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .footer {{ margin-top: 30px; text-align: center; font-size: 0.8em; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Financial Sentiment Analysis Report</h1>
            <p>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Overview</h2>
            <div class="stats">
                <div class="stat-box">
                    <h3>Record Count</h3>
                    <p>{stats['Record count']}</p>
                </div>
                <div class="stat-box">
                    <h3>Unique Tickers</h3>
                    <p>{stats['Unique tickers']}</p>
                </div>
                <div class="stat-box">
                    <h3>Data Sources</h3>
                    <p>{stats['Unique sources']}</p>
                </div>
                <div class="stat-box">
                    <h3>Date Range</h3>
                    <p>{stats['Date range']}</p>
                </div>
            </div>
            
            <h2>Top 20 Tickers by Frequency</h2>
            <div class="image-container">
                <img src="data:image/png;base64,{images['top_tickers']}" alt="Top 20 Tickers">
            </div>
            
            <h2>Data Sources</h2>
            <div class="image-container">
                <img src="data:image/png;base64,{images['sources']}" alt="Data Sources">
            </div>
            
            <h2>Sentiment Distribution</h2>
            <div class="image-container">
                <img src="data:image/png;base64,{images['sentiment_distribution']}" alt="Sentiment Distribution">
            </div>
            
            <h2>Top 20 Tickers by Positive Sentiment</h2>
            <div class="image-container">
                <img src="data:image/png;base64,{images['top_positive_sentiment']}" alt="Top Positive Sentiment">
            </div>
            
            <h2>Bottom 20 Tickers by Sentiment</h2>
            <div class="image-container">
                <img src="data:image/png;base64,{images['top_negative_sentiment']}" alt="Top Negative Sentiment">
            </div>
            
            <h2>Ticker Sentiment Analysis</h2>
            <p>Table showing tickers with at least 5 records, sorted by average sentiment.</p>
            <table>
                <tr>
                    <th>Ticker</th>
                    <th>Average Sentiment</th>
                    <th>Record Count</th>
                </tr>
                {''.join(f"<tr><td>{row['ticker']}</td><td>{row['mean']:.4f}</td><td>{row['count']}</td></tr>" for _, row in ticker_sentiment.head(20).iterrows())}
            </table>
            
            <div class="footer">
                <p>Generated from cleaned, deduplicated parquet files. Data period: {stats['Date range']}.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Write the HTML report
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"HTML report created: {output_file}")

if __name__ == '__main__':
    parquet_file = '/app/data/output/combined/all_real_sentiment.parquet'
    analysis_dir = '/app/data/analysis'
    output_file = '/app/data/analysis/sentiment_report.html'
    
    create_html_report(parquet_file, analysis_dir, output_file)