import requests
import pandas as pd
from typing import List, Dict, Optional, Tuple
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SP500Tracker:
    """Tracks the top tickers in the S&P 500 by market cap or trading volume."""
    
    def __init__(self, update_interval_hours: int = 24, 
                 cache_file: str = "sp500_data.csv",
                 top_n: int = 10, metric: str = "market_cap"):
        """
        Initialize the S&P 500 tracker.
        
        Args:
            update_interval_hours: How often to update the ticker list
            cache_file: File to cache S&P 500 data
            top_n: Number of top tickers to track
            metric: Metric to rank by ('market_cap' or 'volume')
        """
        self.update_interval = update_interval_hours * 3600  # Convert to seconds
        self.cache_file = cache_file
        self.top_n = top_n
        self.metric = metric
        self.last_update_time = None
        self.sp500_tickers = []
        self.top_tickers = []
        
    def _fetch_sp500_tickers(self) -> List[str]:
        """
        Fetch the current list of S&P 500 constituents.
        
        Returns:
            List of ticker symbols
        """
        try:
            # Use pandas datareader to get S&P 500 constituents
            # This is a common approach, but requires an API key for some sources
            # For demonstration, we'll use Wikipedia as a free source
            table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
            df = table[0]
            return df['Symbol'].tolist()
            
        except Exception as e:
            logger.error(f"Error fetching S&P 500 tickers: {e}")
            # Return cached data if available
            try:
                df = pd.read_csv(self.cache_file)
                return df['Symbol'].tolist()
            except:
                # Return empty list if all fails
                return []
                
    def _get_market_data(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Get market data for a list of tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary mapping tickers to market data
        """
        market_data = {}
        
        try:
            # For demonstration, we'll use Yahoo Finance
            # Real implementation would use a proper API with credentials
            for ticker in tickers:
                try:
                    # Get data from Yahoo Finance
                    ticker_data = pd.read_csv(
                        f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={int(time.time()-86400)}&period2={int(time.time())}&interval=1d&events=history"
                    )
                    
                    if not ticker_data.empty:
                        # Get the latest row
                        latest = ticker_data.iloc[-1]
                        
                        # Store relevant data
                        market_data[ticker] = {
                            'price': latest['Close'],
                            'volume': latest['Volume'],
                            # Note: Market cap would be calculated if share count is available
                            # For now, we'll use volume as a proxy
                            'market_cap': latest['Close'] * latest['Volume']  # This is not actual market cap
                        }
                    
                except Exception as e:
                    logger.warning(f"Error getting data for {ticker}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            
        return market_data
        
    def update_top_tickers(self, force: bool = False) -> List[str]:
        """
        Update the list of top tickers if needed.
        
        Args:
            force: Force update regardless of interval
            
        Returns:
            List of top ticker symbols
        """
        current_time = datetime.now()
        
        # Check if update is needed
        if (not force and self.last_update_time is not None and 
            (current_time - self.last_update_time).total_seconds() < self.update_interval):
            return self.top_tickers
            
        # Update the ticker list
        self.sp500_tickers = self._fetch_sp500_tickers()
        
        if not self.sp500_tickers:
            logger.warning("Could not fetch S&P 500 tickers")
            return self.top_tickers if self.top_tickers else []
            
        # Get market data
        market_data = self._get_market_data(self.sp500_tickers)
        
        if not market_data:
            logger.warning("Could not fetch market data")
            return self.top_tickers if self.top_tickers else []
            
        # Create DataFrame for ranking
        df = pd.DataFrame([
            {'ticker': ticker, **data}
            for ticker, data in market_data.items()
        ])
        
        # Rank by chosen metric
        if self.metric == 'volume':
            df = df.sort_values('volume', ascending=False)
        else:  # Default to market_cap
            df = df.sort_values('market_cap', ascending=False)
            
        # Get top N tickers
        self.top_tickers = df['ticker'].head(self.top_n).tolist()
        
        # Cache the data
        df.to_csv(self.cache_file, index=False)
        
        # Update timestamp
        self.last_update_time = current_time
        
        return self.top_tickers
        
    def get_top_tickers(self) -> List[str]:
        """
        Get the current list of top tickers.
        
        Returns:
            List of top ticker symbols
        """
        # Update if needed
        if not self.top_tickers or self.last_update_time is None:
            return self.update_top_tickers()
            
        # Check if update is needed
        current_time = datetime.now()
        if (current_time - self.last_update_time).total_seconds() >= self.update_interval:
            return self.update_top_tickers()
            
        return self.top_tickers