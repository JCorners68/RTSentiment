"""Base class for all subscription receivers."""
from abc import ABC, abstractmethod

class BaseReceiver(ABC):
    """Abstract base class for receivers."""
    
    @abstractmethod
    async def start(self):
        """Start the receiver process."""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the receiver process."""
        pass
