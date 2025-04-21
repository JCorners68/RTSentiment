"""Base class for all web scrapers."""
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    """Abstract base class for scrapers."""
    
    @abstractmethod
    async def scrape(self):
        """Scrape data from the source."""
        pass
