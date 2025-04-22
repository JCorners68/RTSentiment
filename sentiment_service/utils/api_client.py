import aiohttp
import asyncio
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ApiClient:
    """Client for interacting with the API service."""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the API client.
        
        Args:
            base_url (str, optional): Base URL for the API. Defaults to environment variable.
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://api:8001")
        self.session = None
        
    async def ensure_session(self):
        """Ensure an aiohttp session exists."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def post_sentiment_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post a sentiment event to the API for database storage.
        
        Args:
            event_data (Dict[str, Any]): Event data to store
            
        Returns:
            Dict[str, Any]: Response from API
        """
        await self.ensure_session()
        url = f"{self.base_url}/sentiment/event"
        
        try:
            async with self.session.post(url, json=event_data) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    logger.error(f"Error posting event to API: {response.status} - {error_text}")
                    return {"error": f"API error: {response.status}", "details": error_text}
                
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Client error posting event to API: {str(e)}")
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error posting event to API: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}