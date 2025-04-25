#!/usr/bin/env python3
"""
End-to-End Simulator for Ticker Sentiment Analyzer

This script simulates the operation of the full Ticker Sentiment Analyzer system
without requiring external services like Redis. It's useful for verifying basic
functionality and data flow without full dependency installation.

The simulator:
1. Creates mock Parquet data
2. Implements an in-memory Redis mock
3. Simulates the processing of sentiment events
4. Calculates time-weighted sentiment scores
5. Outputs metrics to verify correctness

Usage:
    python e2e_simulator.py [--verbose]
"""

import sys
import os
import json
import argparse
import math
import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import decay functions directly (no external dependencies)
from sentiment_analyzer.models.decay_functions import apply_decay


class MockRedisSentimentCache:
    """Mock implementation of RedisSentimentCache that uses in-memory dictionaries."""
    
    def __init__(self):
        """Initialize the mock cache."""
        self.events = {}  # ticker -> list of events
        self.scores = {}  # ticker -> sentiment score
        
    def add_ticker_event(self, ticker: str, event: Dict[str, Any]) -> None:
        """Add a sentiment event for a ticker."""
        ticker = ticker.upper()
        if ticker not in self.events:
            self.events[ticker] = []
        self.events[ticker].append(event)
        
    def get_ticker_events(self, ticker: str) -> List[Dict[str, Any]]:
        """Get all sentiment events for a ticker."""
        ticker = ticker.upper()
        return self.events.get(ticker, [])
        
    def update_ticker_score(self, ticker: str, score: float) -> None:
        """Update the current sentiment score for a ticker."""
        ticker = ticker.upper()
        self.scores[ticker] = score
        
    def get_ticker_score(self, ticker: str) -> Optional[float]:
        """Get the current sentiment score for a ticker."""
        ticker = ticker.upper()
        return self.scores.get(ticker)
        
    def get_all_ticker_scores(self) -> Dict[str, float]:
        """Get sentiment scores for all tracked tickers."""
        return self.scores


class MockParquetReader:
    """Mock implementation of ParquetReader that uses in-memory data."""
    
    def __init__(self):
        """Initialize the mock reader with sample data."""
        self.data = {
            'AAPL': self._generate_sample_data('AAPL', 100, 0.7),
            'MSFT': self._generate_sample_data('MSFT', 80, 0.5),
            'GOOGL': self._generate_sample_data('GOOGL', 70, 0.3),
            'TSLA': self._generate_sample_data('TSLA', 120, -0.2),
            'AMZN': self._generate_sample_data('AMZN', 90, 0.1),
        }
        
    def _generate_sample_data(self, ticker: str, count: int, bias: float) -> List[Dict[str, Any]]:
        """Generate sample data for a ticker with a bias towards positive/negative sentiment."""
        now = datetime.datetime.now()
        events = []
        
        for i in range(count):
            # Random sentiment with bias
            sentiment = min(1.0, max(-1.0, (0.5 - 0.5 * math.cos(i)) + bias * 0.3))
            
            # Random time in the past (0-7 days)
            hours_ago = i % 168  # 7 days = 168 hours
            timestamp = now - datetime.timedelta(hours=hours_ago)
            
            # Random source type
            source_type = ['news', 'reddit', 'twitter'][i % 3]
            
            events.append({
                'ticker': ticker,
                'timestamp': timestamp,
                'sentiment': sentiment,
                'source_type': source_type,
                'source_name': f'mock_{source_type}',
                'content': f'Mock content for {ticker} event {i}',
                'url': f'https://example.com/{ticker}/{i}',
            })
            
        return events
        
    def read_ticker_data(self, ticker: str, 
                         start_date: Optional[datetime.datetime] = None,
                         end_date: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
        """Read sentiment data for a specific ticker with optional date filtering."""
        ticker = ticker.upper()
        events = self.data.get(ticker, [])
        
        # Apply date filters if provided
        if start_date is not None:
            events = [e for e in events if e['timestamp'] >= start_date]
            
        if end_date is not None:
            events = [e for e in events if e['timestamp'] <= end_date]
            
        return events
        
    def get_all_tickers(self) -> List[str]:
        """Get a list of all tickers."""
        return list(self.data.keys())


class MockSP500Tracker:
    """Mock implementation of SP500Tracker."""
    
    def __init__(self):
        """Initialize the mock tracker."""
        self.tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN']
        
    def get_top_tickers(self) -> List[str]:
        """Get the top tickers."""
        return self.tickers


class SentimentCalculator:
    """Implements sentiment calculation logic."""
    
    def __init__(self, decay_type: str = "exponential", 
                 decay_half_life: int = 24, max_age_hours: int = 168):
        """
        Initialize the calculator.
        
        Args:
            decay_type: Type of decay function
            decay_half_life: Half-life parameter in hours
            max_age_hours: Maximum age to consider
        """
        self.decay_type = decay_type
        self.decay_half_life = decay_half_life
        self.max_age_hours = max_age_hours
        
    def calculate_impact(self, event: Dict[str, Any]) -> float:
        """Calculate impact score for an event."""
        # Simple impact calculation based on source type
        source_weights = {
            'news': 1.5,
            'reddit': 0.8,
            'twitter': 0.5
        }
        
        source_type = event.get('source_type', '').lower()
        return source_weights.get(source_type, 1.0)
        
    def calculate_sentiment_score(self, events: List[Dict[str, Any]], 
                                  current_time: Optional[datetime.datetime] = None) -> float:
        """
        Calculate the current sentiment score for events.
        
        Args:
            events: List of sentiment events
            current_time: Time to calculate sentiment for (default is now)
            
        Returns:
            Normalized sentiment score between -100 and 100
        """
        if not events:
            return 0.0
            
        if current_time is None:
            current_time = datetime.datetime.now()
            
        total_weight = 0
        weighted_sentiment = 0
        
        for event in events:
            # Calculate age in hours
            event_time = event['timestamp']
            age_hours = (current_time - event_time).total_seconds() / 3600
            
            # Skip events older than max age
            if age_hours > self.max_age_hours:
                continue
                
            # Calculate impact
            impact = self.calculate_impact(event)
            
            # Apply decay
            decay = apply_decay(age_hours, self.decay_type, self.decay_half_life)
            
            # Calculate weight (impact * decay)
            weight = impact * decay
            
            # Add to weighted sentiment
            sentiment = event['sentiment']
            weighted_sentiment += sentiment * weight
            total_weight += weight
            
        # Normalize the final score
        if total_weight > 0:
            normalized_score = weighted_sentiment / total_weight
            # Scale to -100 to 100 range
            return max(-100, min(100, normalized_score * 100))
        else:
            return 0.0


def run_simulation(verbose: bool = False):
    """Run the end-to-end simulation."""
    # Print header
    print("=" * 80)
    print("TICKER SENTIMENT ANALYZER SIMULATION")
    print("=" * 80)
    
    # Initialize components
    print("\nInitializing components...")
    redis_cache = MockRedisSentimentCache()
    parquet_reader = MockParquetReader()
    sp500_tracker = MockSP500Tracker()
    calculator = SentimentCalculator()
    
    # Get tickers
    tickers = sp500_tracker.get_top_tickers()
    print(f"Tracking {len(tickers)} tickers: {', '.join(tickers)}")
    
    # Load historical data
    print("\nLoading historical data...")
    for ticker in tickers:
        events = parquet_reader.read_ticker_data(ticker)
        print(f"  {ticker}: {len(events)} events")
        
        if verbose:
            print(f"    First event: {events[0]['timestamp']} - {events[0]['sentiment']:.2f}")
            print(f"    Last event: {events[-1]['timestamp']} - {events[-1]['sentiment']:.2f}")
            
        # Add events to Redis cache
        for event in events:
            redis_cache.add_ticker_event(ticker, event)
    
    # Calculate sentiment scores
    print("\nCalculating sentiment scores...")
    scores = {}
    for ticker in tickers:
        # Get events from cache
        events = redis_cache.get_ticker_events(ticker)
        
        # Calculate score
        score = calculator.calculate_sentiment_score(events)
        scores[ticker] = score
        
        # Update cache
        redis_cache.update_ticker_score(ticker, score)
        
        print(f"  {ticker}: {score:.2f}")
        
    # Verify data flow
    print("\nVerifying data flow...")
    for ticker in tickers:
        cached_score = redis_cache.get_ticker_score(ticker)
        print(f"  {ticker}: Calculated={scores[ticker]:.2f}, Cached={cached_score:.2f}")
        assert abs(scores[ticker] - cached_score) < 0.001, "Score mismatch!"
        
    # Simulate time passing
    print("\nSimulating time passing (24 hours)...")
    future_time = datetime.datetime.now() + datetime.timedelta(hours=24)
    
    # Recalculate scores with time decay
    print("\nRecalculating scores with time decay...")
    new_scores = {}
    for ticker in tickers:
        events = redis_cache.get_ticker_events(ticker)
        new_score = calculator.calculate_sentiment_score(events, future_time)
        new_scores[ticker] = new_score
        redis_cache.update_ticker_score(ticker, new_score)
        
        delta = new_score - scores[ticker]
        print(f"  {ticker}: {new_score:.2f} (Δ {delta:+.2f})")
        
    # Simulate time passing significantly to see decay
    print("\nSimulating time passing (72 hours)...")
    future_time_3days = datetime.datetime.now() + datetime.timedelta(hours=72)
    
    # Recalculate scores with significant time decay
    print("\nRecalculating scores with significant time decay (72h)...")
    decay_scores = {}
    for ticker in tickers:
        events = redis_cache.get_ticker_events(ticker)
        decay_score = calculator.calculate_sentiment_score(events, future_time_3days)
        decay_scores[ticker] = decay_score
        
        delta = decay_score - scores[ticker]
        print(f"  {ticker}: {decay_score:.2f} (Δ {delta:+.2f})")
        
    # Simulate new event
    print("\nSimulating new sentiment event for AAPL...")
    new_event = {
        'ticker': 'AAPL',
        'timestamp': future_time,
        'sentiment': 0.9,  # Very positive
        'source_type': 'news',
        'source_name': 'mock_breaking_news',
        'content': 'Breaking news for AAPL!',
        'url': 'https://example.com/breaking'
    }
    
    # Add to cache
    redis_cache.add_ticker_event('AAPL', new_event)
    
    # Recalculate score
    events = redis_cache.get_ticker_events('AAPL')
    final_score = calculator.calculate_sentiment_score(events, future_time)
    redis_cache.update_ticker_score('AAPL', final_score)
    
    delta = final_score - new_scores['AAPL']
    print(f"  AAPL: {final_score:.2f} (Δ {delta:+.2f})")
    
    # Print summary
    print("\nFinal sentiment scores:")
    for ticker in tickers:
        score = redis_cache.get_ticker_score(ticker)
        print(f"  {ticker}: {score:.2f}")
        
    print("\nSimulation completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ticker Sentiment Analyzer Simulator")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    run_simulation(args.verbose)