#!/usr/bin/env python3
"""
API Service Load Test

This script performs a load test on the API service to verify
it can handle concurrent requests. It simulates multiple clients
making requests simultaneously.

Example usage:
    python api_load_test.py --host localhost --port 8001 --clients 10 --requests 100
"""

import argparse
import requests
import json
import time
import random
import asyncio
import aiohttp
import statistics
from datetime import datetime

# Sample text data for sentiment analysis
SAMPLE_TEXTS = [
    "Apple's latest quarterly results exceeded expectations with strong iPhone sales.",
    "Tesla reported significant losses in the European market this quarter.",
    "Microsoft's cloud business continues to drive strong growth for the company.",
    "Amazon's e-commerce segment saw declining sales amidst increasing competition.",
    "Google's ad revenue growth has slowed down in recent months.",
    "Netflix subscriber growth has rebounded after several quarters of decline.",
    "Facebook faces regulatory challenges in multiple markets affecting investor sentiment.",
    "Intel's new chip architecture has received positive reviews from industry analysts.",
    "AMD continues to gain market share in the semiconductor industry.",
    "Nvidia reported record revenues driven by AI chip demand."
]

# Sample ticker symbols
TICKERS = ["AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "NFLX", "META", "INTC", "AMD", "NVDA"]

async def run_health_check(session, base_url):
    """Run a health check on the API."""
    start_time = time.time()
    async with session.get(f"{base_url}/health") as response:
        duration = time.time() - start_time
        return {
            "endpoint": "/health",
            "status": response.status,
            "duration": duration
        }

async def get_ticker_sentiment(session, base_url, ticker):
    """Get sentiment for a specific ticker."""
    start_time = time.time()
    async with session.get(f"{base_url}/sentiment/ticker/{ticker}") as response:
        duration = time.time() - start_time
        return {
            "endpoint": f"/sentiment/ticker/{ticker}",
            "status": response.status,
            "duration": duration
        }

async def get_top_sentiment(session, base_url, limit=5):
    """Get top sentiment tickers."""
    start_time = time.time()
    async with session.get(f"{base_url}/sentiment/top?limit={limit}") as response:
        duration = time.time() - start_time
        return {
            "endpoint": "/sentiment/top",
            "status": response.status,
            "duration": duration
        }

async def analyze_sentiment(session, base_url, text):
    """Analyze sentiment for text."""
    start_time = time.time()
    params = {"text": text}
    async with session.post(f"{base_url}/sentiment/analyze", params=params) as response:
        duration = time.time() - start_time
        return {
            "endpoint": "/sentiment/analyze",
            "status": response.status,
            "duration": duration
        }

async def create_sentiment_event(session, base_url):
    """Create a test sentiment event."""
    ticker = random.choice(TICKERS)
    score = random.uniform(-1.0, 1.0)
    sentiment = "positive" if score > 0 else "negative" if score < 0 else "neutral"
    
    event_data = {
        "source": "load_test",
        "priority": "standard",
        "text": random.choice(SAMPLE_TEXTS),
        "model": "test_model",
        "sentiment_score": score,
        "sentiment_label": sentiment,
        "processing_time": random.uniform(0.01, 0.2),
        "event_id": f"load-test-{datetime.now().isoformat()}-{random.randint(1000, 9999)}",
        "ticker_sentiments": [{ticker: score}]
    }
    
    start_time = time.time()
    async with session.post(f"{base_url}/sentiment/event", json=event_data) as response:
        duration = time.time() - start_time
        return {
            "endpoint": "/sentiment/event",
            "status": response.status,
            "duration": duration
        }

async def query_sentiment(session, base_url):
    """Query sentiment events."""
    query_data = {
        "sources": ["load_test"],
        "limit": 10
    }
    
    start_time = time.time()
    async with session.post(f"{base_url}/sentiment/query", json=query_data) as response:
        duration = time.time() - start_time
        return {
            "endpoint": "/sentiment/query",
            "status": response.status,
            "duration": duration
        }

async def client_worker(client_id, base_url, num_requests):
    """Simulate a client making multiple requests."""
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i in range(num_requests):
            # Choose a random API endpoint to test
            endpoint_choice = random.randint(1, 6)
            
            try:
                if endpoint_choice == 1:
                    result = await run_health_check(session, base_url)
                elif endpoint_choice == 2:
                    ticker = random.choice(TICKERS)
                    result = await get_ticker_sentiment(session, base_url, ticker)
                elif endpoint_choice == 3:
                    result = await get_top_sentiment(session, base_url)
                elif endpoint_choice == 4:
                    text = random.choice(SAMPLE_TEXTS)
                    result = await analyze_sentiment(session, base_url, text)
                elif endpoint_choice == 5:
                    result = await create_sentiment_event(session, base_url)
                else:
                    result = await query_sentiment(session, base_url)
                
                result["client_id"] = client_id
                result["request_id"] = i
                results.append(result)
            except Exception as e:
                results.append({
                    "client_id": client_id,
                    "request_id": i,
                    "endpoint": f"endpoint_choice_{endpoint_choice}",
                    "error": str(e)
                })
            
            # Random delay between requests (0-100ms)
            await asyncio.sleep(random.uniform(0, 0.1))
    
    return results

async def run_load_test(base_url, num_clients, num_requests_per_client):
    """Run the load test with multiple clients."""
    print(f"Starting load test with {num_clients} clients, each making {num_requests_per_client} requests")
    print(f"Total requests: {num_clients * num_requests_per_client}")
    
    start_time = time.time()
    
    # Create client tasks
    tasks = [client_worker(i, base_url, num_requests_per_client) for i in range(num_clients)]
    
    # Run all clients concurrently
    client_results = await asyncio.gather(*tasks)
    
    # Flatten results
    all_results = [result for client_result in client_results for result in client_result]
    
    total_time = time.time() - start_time
    requests_per_second = len(all_results) / total_time
    
    # Calculate statistics
    successful_requests = [r for r in all_results if "status" in r and 200 <= r["status"] < 300]
    failed_requests = [r for r in all_results if "status" not in r or r["status"] >= 300]
    
    durations = [r["duration"] for r in all_results if "duration" in r]
    avg_duration = statistics.mean(durations) if durations else 0
    max_duration = max(durations) if durations else 0
    min_duration = min(durations) if durations else 0
    p95_duration = statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max_duration
    
    # Group by endpoint
    endpoint_stats = {}
    for result in all_results:
        if "endpoint" in result:
            endpoint = result["endpoint"]
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "count": 0,
                    "success_count": 0,
                    "fail_count": 0,
                    "durations": []
                }
            
            endpoint_stats[endpoint]["count"] += 1
            
            if "status" in result and 200 <= result["status"] < 300:
                endpoint_stats[endpoint]["success_count"] += 1
            else:
                endpoint_stats[endpoint]["fail_count"] += 1
                
            if "duration" in result:
                endpoint_stats[endpoint]["durations"].append(result["duration"])
    
    # Calculate per-endpoint statistics
    for endpoint, stats in endpoint_stats.items():
        durations = stats["durations"]
        stats["avg_duration"] = statistics.mean(durations) if durations else 0
        stats["max_duration"] = max(durations) if durations else 0
        stats["min_duration"] = min(durations) if durations else 0
        stats["p95_duration"] = statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else stats["max_duration"]
        
        # Remove raw durations to clean up output
        del stats["durations"]
    
    # Print results
    print("\n=== Load Test Results ===")
    print(f"Total test duration: {total_time:.2f} seconds")
    print(f"Requests per second: {requests_per_second:.2f}")
    print(f"Successful requests: {len(successful_requests)} ({len(successful_requests)/len(all_results)*100:.2f}%)")
    print(f"Failed requests: {len(failed_requests)} ({len(failed_requests)/len(all_results)*100:.2f}%)")
    print(f"Average request duration: {avg_duration*1000:.2f} ms")
    print(f"Min request duration: {min_duration*1000:.2f} ms")
    print(f"Max request duration: {max_duration*1000:.2f} ms")
    print(f"95th percentile duration: {p95_duration*1000:.2f} ms")
    
    print("\n=== Per-Endpoint Statistics ===")
    for endpoint, stats in endpoint_stats.items():
        print(f"\nEndpoint: {endpoint}")
        print(f"  Total requests: {stats['count']}")
        print(f"  Success rate: {stats['success_count']/stats['count']*100:.2f}%")
        print(f"  Average duration: {stats['avg_duration']*1000:.2f} ms")
        print(f"  Min duration: {stats['min_duration']*1000:.2f} ms")
        print(f"  Max duration: {stats['max_duration']*1000:.2f} ms")
        print(f"  95th percentile: {stats['p95_duration']*1000:.2f} ms")
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"load_test_results_{timestamp}.json"
    
    report = {
        "summary": {
            "total_requests": len(all_results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests)/len(all_results),
            "total_duration": total_time,
            "requests_per_second": requests_per_second,
            "avg_duration": avg_duration,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "p95_duration": p95_duration
        },
        "endpoint_stats": endpoint_stats
    }
    
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {filename}")
    
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run a load test on the API service')
    parser.add_argument('--host', default='localhost', help='API host')
    parser.add_argument('--port', default=8001, type=int, help='API port')
    parser.add_argument('--clients', default=10, type=int, help='Number of concurrent clients')
    parser.add_argument('--requests', default=100, type=int, help='Number of requests per client')
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    
    # Check if API is running
    try:
        response = requests.get(f"{base_url}/health", timeout=2)
        print(f"API service detected at {base_url}")
    except requests.exceptions.ConnectionError:
        print(f"API service not running at {base_url}. Please start it before running the load test.")
        exit(1)
    
    asyncio.run(run_load_test(base_url, args.clients, args.requests))