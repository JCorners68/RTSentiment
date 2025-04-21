#\!/bin/bash
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Creating Data Acquisition Directory Structure${NC}"

# Create directory structure
mkdir -p data_acquisition/{scrapers,subscription,utils,tests,config,data/{cache,logs,output}}

# Create required __init__.py files
touch data_acquisition/{scrapers,subscription,utils,tests}/__init__.py

# Create placeholder files
touch data_acquisition/data/{logs,output,cache}/.gitkeep

# Create basic module templates
cat > data_acquisition/scrapers/base.py << 'INNEREOF'
"""Base class for all web scrapers."""
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    """Abstract base class for scrapers."""
    
    @abstractmethod
    async def scrape(self):
        """Scrape data from the source."""
        pass
INNEREOF

cat > data_acquisition/subscription/base.py << 'INNEREOF'
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
INNEREOF

cat > data_acquisition/utils/event_producer.py << 'INNEREOF'
"""Kafka/EventHub producer for sending events."""

class EventProducer:
    """Producer for sending events to Kafka/EventHub."""
    
    async def send(self, event, priority="standard"):
        """Send an event to the appropriate topic."""
        pass
INNEREOF

cat > data_acquisition/utils/weight_calculator.py << 'INNEREOF'
"""Utility functions for calculating event weight."""

def calculate_weight(event):
    """Calculate the weight of an event."""
    return 0.5  # Default middle weight
INNEREOF

# Create config templates
cat > data_acquisition/config/scraper_config.json << 'INNEREOF'
{
  "kafka_bootstrap_servers": "kafka:9092",
  "high_priority_topic": "sentiment-events-high",
  "standard_priority_topic": "sentiment-events-standard",
  "polling_interval": 60,
  "sources": [
    {"name": "Financial Times", "url": "https://www.ft.com"},
    {"name": "Wall Street Journal", "url": "https://www.wsj.com"}
  ],
  "platforms": [
    {"name": "Twitter", "api_endpoint": "https://api.twitter.com/2/tweets/search/recent"}
  ],
  "sites": [
    {"name": "Yahoo Finance", "url": "https://finance.yahoo.com"},
    {"name": "MarketWatch", "url": "https://www.marketwatch.com"}
  ]
}
INNEREOF

# Create .env sample
cat > data_acquisition/.env.sample << 'INNEREOF'
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
HIGH_PRIORITY_TOPIC=sentiment-events-high
STANDARD_PRIORITY_TOPIC=sentiment-events-standard
CONFIG_PATH=config/scraper_config.json
POLLING_INTERVAL=60
INNEREOF

# Create .gitignore for data_acquisition
cat > data_acquisition/.gitignore << 'INNEREOF'
.env
data/cache/*
\!data/cache/.gitkeep
data/logs/*
\!data/logs/.gitkeep
data/output/*
\!data/output/.gitkeep
__pycache__/
*.py[cod]
*$py.class
INNEREOF

# Make script executable
chmod +x /home/jonat/WSL_RT_Sentiment/scripts/create_data_dirs.sh

echo -e "${GREEN}Data Acquisition Directory Structure Created Successfully${NC}"
echo "Created directories for scrapers, subscription, utils, tests, and data"
echo "Next steps: Configure API keys and customize implementations"
