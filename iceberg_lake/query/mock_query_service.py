#!/usr/bin/env python3
"""
Mock implementation of the DremioSentimentQueryService for testing.
"""
import os
import sys
import logging
import pandas as pd
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockSentimentQueryService:
    """
    Mock implementation of the DremioSentimentQueryService for testing.
    This service simulates querying sentiment data from Dremio without the JDBC dependency.
    """
    
    def __init__(
        self,
        catalog: str = "DREMIO",
        namespace: str = "sentiment",
        table_name: str = "sentiment_data",
    ):
        """
        Initialize the MockSentimentQueryService.
        
        Args:
            catalog: Dremio catalog name
            namespace: Dremio namespace/schema
            table_name: Dremio table name
        """
        self.catalog = catalog
        self.namespace = namespace
        self.table_name = table_name
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Initializing mock sentiment query service for {catalog}.{namespace}.{table_name}")
        
        # Seed for reproducibility
        random.seed(42)
        
        # Cached data
        self._cache = {}
        
        # Available tickers
        self.tickers = ["AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "NFLX"]
        
        # Available sources
        self.sources = ["twitter", "reddit", "news", "blogs", "financial_reports"]
        
        # Available emotions
        self.emotions = ["joy", "anger", "fear", "surprise", "disgust", "sadness", "trust", "anticipation"]
        
        # Available entities
        self.entity_types = ["PERSON", "ORG", "GPE", "PRODUCT", "EVENT", "DATE", "MONEY"]
        
        # Available aspects
        self.aspects = ["price", "product", "service", "management", "growth", "earnings", "competition"]
    
    def close(self):
        """Close the connection when done."""
        self.logger.info("Closing mock sentiment query service")
    
    def verify_driver(self) -> str:
        """
        Verify that the JDBC driver is available.
        
        Returns:
            str: Driver version information
        """
        return "Mock Dremio JDBC Driver v1.0.0"
    
    def get_sentiment(self, ticker: str, days: int = 30, limit: int = 100) -> pd.DataFrame:
        """
        Get basic sentiment data for a specific ticker.
        
        Args:
            ticker: Ticker symbol
            days: Number of days to look back
            limit: Maximum number of records to return
            
        Returns:
            pd.DataFrame: Sentiment data
        """
        cache_key = f"sentiment_{ticker}_{days}_{limit}"
        if cache_key in self._cache:
            self.logger.info(f"Using cached result for {cache_key}")
            return self._cache[cache_key]
        
        self.logger.info(f"Generating mock sentiment data for {ticker} (last {days} days)")
        
        # Generate mock data
        records = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        for _ in range(min(limit, days * 5)):  # 5 messages per day on average
            timestamp = start_date + timedelta(seconds=random.randint(0, int((end_date - start_date).total_seconds())))
            sentiment_score = random.uniform(-1.0, 1.0)
            
            record = {
                "message_id": f"{ticker}_{int(timestamp.timestamp())}",
                "event_timestamp": timestamp,
                "ingestion_timestamp": timestamp + timedelta(minutes=random.randint(1, 60)),
                "source_system": random.choice(self.sources),
                "text_content": f"Sample message about {ticker} with sentiment {sentiment_score:.2f}",
                "sentiment_score": sentiment_score,
                "sentiment_magnitude": random.uniform(0.1, 5.0),
                "primary_emotion": random.choice(self.emotions),
                "sarcasm_detection": random.choice([True, False]),
                "subjectivity_score": random.uniform(0.0, 1.0),
                "toxicity_score": random.uniform(0.0, 0.5),
                "user_intent": random.choice(["inform", "question", "opinion", "complaint", "praise"]),
                "influence_score": random.uniform(0.0, 10.0),
                "ticker": ticker,
            }
            
            # Generate emotion vector
            emotion_vector = {}
            for emotion in random.sample(self.emotions, k=random.randint(2, 5)):
                emotion_vector[emotion] = random.uniform(0.0, 1.0)
            record["emotion_intensity_vector"] = emotion_vector
            
            # Generate aspect sentiment
            aspect_sentiment = {}
            for aspect in random.sample(self.aspects, k=random.randint(1, 3)):
                aspect_sentiment[aspect] = random.uniform(-1.0, 1.0)
            record["aspect_based_sentiment"] = aspect_sentiment
            
            # Generate entities
            entities = []
            for _ in range(random.randint(0, 3)):
                entity_type = random.choice(self.entity_types)
                entity_text = f"{entity_type}_{random.randint(1, 100)}"
                entities.append({"text": entity_text, "type": entity_type})
            record["entity_recognition"] = entities
            
            records.append(record)
        
        # Create DataFrame
        df = pd.DataFrame(records)
        
        # Sort by timestamp
        df = df.sort_values("event_timestamp", ascending=False)
        
        # Cache result
        self._cache[cache_key] = df
        
        return df
    
    def get_sentiment_with_emotions(self, ticker: str, days: int = 30, limit: int = 100) -> pd.DataFrame:
        """
        Get sentiment data with emotion analysis for a specific ticker.
        
        Args:
            ticker: Ticker symbol
            days: Number of days to look back
            limit: Maximum number of records to return
            
        Returns:
            pd.DataFrame: Sentiment data with emotions
        """
        # Reuse get_sentiment and filter columns
        df = self.get_sentiment(ticker, days, limit)
        return df[["message_id", "event_timestamp", "source_system", "text_content", 
                  "sentiment_score", "primary_emotion", "emotion_intensity_vector"]]
    
    def get_sentiment_time_series(self, ticker: str, interval: str = "day", days: int = 30) -> pd.DataFrame:
        """
        Get sentiment time series data for a specific ticker.
        
        Args:
            ticker: Ticker symbol
            interval: Time interval (day, hour, week, month)
            days: Number of days to look back
            
        Returns:
            pd.DataFrame: Time series data
        """
        cache_key = f"timeseries_{ticker}_{interval}_{days}"
        if cache_key in self._cache:
            self.logger.info(f"Using cached result for {cache_key}")
            return self._cache[cache_key]
        
        self.logger.info(f"Generating mock time series data for {ticker} (last {days} days)")
        
        # Generate time buckets
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        buckets = []
        current = start_date
        
        if interval == "hour":
            delta = timedelta(hours=1)
        elif interval == "day":
            delta = timedelta(days=1)
        elif interval == "week":
            delta = timedelta(weeks=1)
        elif interval == "month":
            delta = timedelta(days=30)
        else:
            delta = timedelta(days=1)
        
        while current <= end_date:
            next_bucket = current + delta
            
            bucket = {
                "time_bucket": current.strftime("%Y-%m-%d %H:%M:%S"),
                "avg_sentiment": random.uniform(-0.5, 0.8),
                "message_count": random.randint(10, 200),
                "avg_emotion_joy": random.uniform(0.0, 1.0),
                "avg_emotion_anger": random.uniform(0.0, 1.0),
                "avg_emotion_fear": random.uniform(0.0, 1.0),
                "avg_subjectivity": random.uniform(0.3, 0.8),
                "avg_influence": random.uniform(1.0, 8.0),
                "ticker": ticker
            }
            
            buckets.append(bucket)
            current = next_bucket
        
        # Create DataFrame
        df = pd.DataFrame(buckets)
        
        # Cache result
        self._cache[cache_key] = df
        
        return df
    
    def get_entity_sentiment_analysis(self, ticker: Optional[str] = None, entity_type: Optional[str] = None, days: int = 30) -> pd.DataFrame:
        """
        Get sentiment analysis broken down by entity.
        
        Args:
            ticker: Optional ticker symbol to filter by
            entity_type: Optional entity type to filter by
            days: Number of days to look back
            
        Returns:
            pd.DataFrame: Entity sentiment data
        """
        cache_key = f"entity_sentiment_{ticker}_{entity_type}_{days}"
        if cache_key in self._cache:
            self.logger.info(f"Using cached result for {cache_key}")
            return self._cache[cache_key]
        
        self.logger.info(f"Generating mock entity sentiment data for {ticker} (last {days} days)")
        
        # Generate mock data
        records = []
        
        # Generate entities for each entity type
        entity_types = [entity_type] if entity_type else self.entity_types
        for e_type in entity_types:
            # Generate 5-10 entities per type
            for i in range(random.randint(5, 10)):
                entity_text = f"{e_type}_{i+1}"
                
                record = {
                    "entity_text": entity_text,
                    "entity_type": e_type,
                    "avg_sentiment": random.uniform(-0.7, 0.9),
                    "message_count": random.randint(5, 100),
                    "primary_emotion": random.choice(self.emotions),
                    "influence_score": random.uniform(0.0, 10.0),
                }
                
                if ticker:
                    record["ticker"] = ticker
                
                records.append(record)
        
        # Create DataFrame
        df = pd.DataFrame(records)
        
        # Sort by message count
        df = df.sort_values("message_count", ascending=False)
        
        # Cache result
        self._cache[cache_key] = df
        
        return df
    
    def get_aspect_based_sentiment(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """
        Get aspect-based sentiment analysis for a specific ticker.
        
        Args:
            ticker: Ticker symbol
            days: Number of days to look back
            
        Returns:
            pd.DataFrame: Aspect-based sentiment data
        """
        cache_key = f"aspect_sentiment_{ticker}_{days}"
        if cache_key in self._cache:
            self.logger.info(f"Using cached result for {cache_key}")
            return self._cache[cache_key]
        
        self.logger.info(f"Generating mock aspect-based sentiment data for {ticker} (last {days} days)")
        
        # Generate mock data
        records = []
        
        for aspect in self.aspects:
            record = {
                "aspect": aspect,
                "avg_sentiment": random.uniform(-0.8, 0.9),
                "message_count": random.randint(10, 150),
                "ticker": ticker
            }
            
            records.append(record)
        
        # Create DataFrame
        df = pd.DataFrame(records)
        
        # Sort by avg_sentiment
        df = df.sort_values("avg_sentiment", ascending=False)
        
        # Cache result
        self._cache[cache_key] = df
        
        return df
    
    def get_toxicity_analysis(self, min_toxicity: float = 0.5, days: int = 30) -> pd.DataFrame:
        """
        Get potentially toxic content for moderation.
        
        Args:
            min_toxicity: Minimum toxicity score
            days: Number of days to look back
            
        Returns:
            pd.DataFrame: Toxic content data
        """
        # Generate mock data
        df = pd.DataFrame([
            {
                "message_id": f"toxic_{i}",
                "text_content": f"Sample toxic message {i}",
                "toxicity_score": random.uniform(min_toxicity, 1.0),
                "source_system": random.choice(self.sources),
                "event_timestamp": datetime.now() - timedelta(days=random.randint(0, days))
            }
            for i in range(10)
        ])
        
        return df
    
    def get_intent_distribution(self, ticker: Optional[str] = None, days: int = 30) -> pd.DataFrame:
        """
        Get distribution of user intents.
        
        Args:
            ticker: Optional ticker symbol to filter by
            days: Number of days to look back
            
        Returns:
            pd.DataFrame: Intent distribution data
        """
        # Define intents
        intents = ["inform", "question", "opinion", "complaint", "praise", "request", "suggestion"]
        
        # Generate mock data
        df = pd.DataFrame([
            {
                "intent": intent,
                "message_count": random.randint(20, 500),
                "avg_sentiment": random.uniform(-0.8, 0.9),
                "avg_influence": random.uniform(1.0, 8.0)
            }
            for intent in intents
        ])
        
        if ticker:
            df["ticker"] = ticker
        
        return df
    
    def get_top_tickers_by_volume(self, days: int = 30, limit: int = 10) -> pd.DataFrame:
        """
        Get top tickers by message volume.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of tickers to return
            
        Returns:
            pd.DataFrame: Top tickers data
        """
        cache_key = f"top_tickers_{days}_{limit}"
        if cache_key in self._cache:
            self.logger.info(f"Using cached result for {cache_key}")
            return self._cache[cache_key]
        
        self.logger.info(f"Generating mock top tickers data (last {days} days)")
        
        # Generate data for all tickers plus some extras
        all_tickers = self.tickers + [f"EXTRA_{i}" for i in range(1, 6)]
        
        records = [
            {
                "ticker": ticker,
                "message_count": random.randint(100, 10000),
                "avg_sentiment": random.uniform(-0.5, 0.9),
                "avg_influence": random.uniform(1.0, 9.0),
                "primary_emotion": random.choice(self.emotions)
            }
            for ticker in all_tickers
        ]
        
        # Create DataFrame
        df = pd.DataFrame(records)
        
        # Sort by message count and limit
        df = df.sort_values("message_count", ascending=False).head(limit)
        
        # Cache result
        self._cache[cache_key] = df
        
        return df
    
    def get_source_distribution(self, days: int = 30) -> pd.DataFrame:
        """
        Get distribution of sources.
        
        Args:
            days: Number of days to look back
            
        Returns:
            pd.DataFrame: Source distribution data
        """
        cache_key = f"source_distribution_{days}"
        if cache_key in self._cache:
            self.logger.info(f"Using cached result for {cache_key}")
            return self._cache[cache_key]
        
        self.logger.info(f"Generating mock source distribution data (last {days} days)")
        
        # Generate mock data
        records = [
            {
                "source_system": source,
                "message_count": random.randint(200, 5000),
                "avg_sentiment": random.uniform(-0.4, 0.7),
                "avg_influence": random.uniform(2.0, 7.0)
            }
            for source in self.sources
        ]
        
        # Create DataFrame
        df = pd.DataFrame(records)
        
        # Sort by message count
        df = df.sort_values("message_count", ascending=False)
        
        # Cache result
        self._cache[cache_key] = df
        
        return df
        
    def get_sentiment_by_source(self, ticker: Optional[str] = None, days: int = 30) -> pd.DataFrame:
        """
        Get sentiment data broken down by source system.
        
        Args:
            ticker: Optional ticker to filter by
            days: Number of days to look back
            
        Returns:
            pd.DataFrame: Sentiment by source data
        """
        # Reuse source distribution implementation
        df = self.get_source_distribution(days)
        
        if ticker:
            df["ticker"] = ticker
            
        return df
        
    def get_top_emotions(self, ticker: Optional[str] = None, days: int = 30, limit: int = 10) -> pd.DataFrame:
        """
        Get top emotions for a ticker or across all tickers.
        
        Args:
            ticker: Optional ticker to filter by
            days: Number of days to look back
            limit: Maximum number of emotions to return
            
        Returns:
            pd.DataFrame: Top emotions data
        """
        # Generate mock data
        emotions_data = [
            {
                "emotion": emotion,
                "message_count": random.randint(50, 500),
                "avg_sentiment": random.uniform(-0.7, 0.9),
                "avg_intensity": random.uniform(0.1, 1.0)
            }
            for emotion in self.emotions
        ]
        
        df = pd.DataFrame(emotions_data)
        
        if ticker:
            df["ticker"] = ticker
            
        # Sort by count and limit
        df = df.sort_values("message_count", ascending=False).head(limit)
        
        return df
        
    def search_sentiment_data(
        self,
        keyword: Optional[str] = None,
        ticker: Optional[str] = None,
        source_system: Optional[str] = None,
        min_sentiment: Optional[float] = None,
        max_sentiment: Optional[float] = None,
        days: int = 30,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Search sentiment data with various filters.
        
        Args:
            keyword: Keyword to search in text_content
            ticker: Stock ticker symbol
            source_system: Source system identifier
            min_sentiment: Minimum sentiment score
            max_sentiment: Maximum sentiment score
            days: Number of days to look back
            limit: Maximum number of results to return
            
        Returns:
            pd.DataFrame: Search results
        """
        # Generate mock search results
        ticker_to_use = ticker or random.choice(self.tickers)
        df = self.get_sentiment(ticker_to_use, days, limit)
        
        # Apply filters
        if source_system:
            df = df[df["source_system"] == source_system]
            
        if min_sentiment is not None:
            df = df[df["sentiment_score"] >= min_sentiment]
            
        if max_sentiment is not None:
            df = df[df["sentiment_score"] <= max_sentiment]
            
        if keyword:
            df = df[df["text_content"].str.contains(keyword, case=False, na=False)]
            
        return df
        
    def get_correlations(self, ticker: str, days: int = 30) -> Dict[str, float]:
        """
        Calculate correlations between different metrics for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back
            
        Returns:
            Dict[str, float]: Correlation coefficients
        """
        # Generate mock correlation data
        return {
            "sentiment_volume": random.uniform(-0.5, 0.9),
            "sentiment_influence": random.uniform(-0.4, 0.8),
            "sentiment_toxicity": random.uniform(-0.6, 0.2),
            "sentiment_subjectivity": random.uniform(-0.3, 0.7),
            "volume_influence": random.uniform(0.1, 0.9),
            "emotion_joy_sentiment": random.uniform(0.4, 0.9),
            "emotion_anger_sentiment": random.uniform(-0.9, -0.3)
        }