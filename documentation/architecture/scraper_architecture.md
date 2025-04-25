# Scraper Architecture

This document outlines the architecture of the data acquisition scrapers using Mermaid diagrams.

## Installation Requirements

Before running the scrapers, you need to install the following dependencies:

```bash
# For production usage (not in virtual environment)
python3 -m pip install -r data_acquisition/requirements.txt

# For production usage (in virtual environment)
pip install -r data_acquisition/requirements.txt

# For test scripts (in virtual environment)
pip install -r tests/requirements.txt

# For test scripts (not in virtual environment)
python3 -m pip install -r tests/requirements.txt
```

## Overall Data Flow

```mermaid
flowchart TB
    subgraph "Data Acquisition Layer"
        NS[News Scraper]
        RS[Reddit Scraper]
        EP[Event Producer]
        
        NS -- "Articles" --> EP
        RS -- "Reddit posts" --> EP
    end
    
    subgraph "Event Ingestion Layer"
        HP[High Priority Topic]
        SP[Standard Priority Topic]
        
        EP -- "Important events" --> HP
        EP -- "Regular events" --> SP
    end
    
    subgraph "Processing Layer"
        HC[High Priority Consumer]
        SC[Standard Priority Consumer]
        SA[Sentiment Analysis]
        
        HP --> HC
        SP --> SC
        HC --> SA
        SC --> SA
    end
    
    subgraph "Storage Layer"
        DB[(PostgreSQL)]
        Cache[(Redis Cache)]
        
        SA --> DB
        SA --> Cache
    end
    
    subgraph "API Layer"
        API[REST API]
        WS[WebSocket]
        
        DB <--> API
        Cache <--> API
        Cache <--> WS
    end
    
    UI[Flutter UI] <--> API
    UI <--> WS
```

## News Scraper Architecture

```mermaid
flowchart TD
    Config[Configuration]
    
    subgraph "News Scraper"
        Init[Initialize]
        Fetch[Fetch Articles]
        Process[Process Content]
        Extract[Extract Tickers]
        Publish[Publish to Kafka]
        
        Init --> Fetch
        Fetch --> Process
        Process --> Extract
        Extract --> Weight[Calculate Weight]
        Weight --> Publish
    end
    
    subgraph "External Sources"
        API1[Financial News API]
        API2[Market News API]
        RSS[RSS Feeds]
        
        Fetch --> API1
        Fetch --> API2
        Fetch --> RSS
    end
    
    subgraph "Event Producer"
        Serialize[Serialize Event]
        Route[Route to Topic]
        Send[Send to Kafka]
        
        Publish --> Serialize
        Serialize --> Route
        Route --> Send
    end
    
    Config --> Init
    
    classDef system fill:#f9f,stroke:#333,stroke-width:1px
    classDef external fill:#bbf,stroke:#33f,stroke-width:1px
    
    class Init,Fetch,Process,Extract,Weight,Publish system
    class API1,API2,RSS external
```

## Reddit Scraper Architecture

```mermaid
flowchart TD
    Config[Configuration]
    
    subgraph "Reddit Scraper"
        Init[Initialize]
        Auth[Authenticate]
        Fetch[Fetch Subreddits]
        Process[Process Posts]
        Extract[Extract Tickers]
        Filter[Filter Posts]
        Publish[Publish to Kafka]
        
        Init --> Auth
        Auth --> Fetch
        Fetch --> Process
        Process --> Extract
        Extract --> Filter
        Filter --> Weight[Calculate Weight]
        Weight --> Publish
    end
    
    subgraph "Reddit Data"
        WSB[r/wallstreetbets]
        INV[r/investing]
        STK[r/stocks]
        
        Fetch --> WSB
        Fetch --> INV
        Fetch --> STK
    end
    
    subgraph "Event Producer"
        Serialize[Serialize Event]
        Route[Route to Topic]
        Send[Send to Kafka]
        
        Publish --> Serialize
        Serialize --> Route
        Route --> Send
    end
    
    Config --> Init
    
    classDef system fill:#f9f,stroke:#333,stroke-width:1px
    classDef external fill:#bbf,stroke:#33f,stroke-width:1px
    
    class Init,Auth,Fetch,Process,Extract,Filter,Weight,Publish system
    class WSB,INV,STK external
```

## Components and Interfaces

```mermaid
classDiagram
    class BaseScraper {
        <<abstract>>
        +producer: EventProducer
        +config: Dict
        +name: string
        +scrape() List~Dict~
        +process_data(data: List~Dict~)
        +start()
        +stop()
    }
    
    class NewsScraper {
        +sources: List~string~
        +api_keys: Dict~string, string~
        +interval: int
        +fetch_articles() List~Dict~
        +extract_tickers(text: string) List~string~
        +scrape() List~Dict~
        +process_data(data: List~Dict~)
        +start()
        +stop()
    }
    
    class RedditScraper {
        +subreddits: List~string~
        +client_id: string
        +client_secret: string
        +auth_token: string
        +interval: int
        +_get_auth_token()
        +_fetch_subreddit(subreddit: string) List~Dict~
        +_process_posts(posts: List~Dict~) List~Dict~
        +_extract_tickers(text: string) List~string~
        +scrape() List~Dict~
        +process_data(data: List~Dict~)
        +start()
        +stop()
    }
    
    class EventProducer {
        +bootstrap_servers: string
        +high_priority_topic: string
        +standard_priority_topic: string
        +producer: KafkaProducer
        +connected: bool
        +_connect()
        +_reconnect(delay: int)
        +send(event: Dict, priority: string) bool
        +close()
    }
    
    class WeightCalculator {
        +calculate_weight(event: Dict) float
    }
    
    BaseScraper <|-- NewsScraper
    BaseScraper <|-- RedditScraper
    NewsScraper --> EventProducer
    RedditScraper --> EventProducer
    NewsScraper --> WeightCalculator
    RedditScraper --> WeightCalculator
```

## Scraper Initialization Sequence

```mermaid
sequenceDiagram
    participant Main as Main Process
    participant Config as Configuration
    participant NS as News Scraper
    participant RS as Reddit Scraper
    participant EP as Event Producer
    participant Kafka as Kafka

    Main->>Config: Load configuration
    Main->>EP: Initialize
    EP->>Kafka: Attempt connection
    Kafka-->>EP: Connection established
    
    Main->>NS: Initialize with config
    Main->>RS: Initialize with config
    
    Main->>NS: Start scraper
    activate NS
    Note over NS: Start periodic task
    
    Main->>RS: Start scraper
    activate RS
    Note over RS: Start periodic task
    
    loop Every news_polling_interval
        NS->>NS: Scrape news sources
        NS->>EP: Send events
        EP->>Kafka: Publish to appropriate topic
    end
    
    loop Every reddit_polling_interval
        RS->>RS: Scrape subreddits
        RS->>EP: Send events
        EP->>Kafka: Publish to appropriate topic
    end
```