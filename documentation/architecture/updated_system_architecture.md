# Updated System Architecture

The following diagram shows the overall system architecture with the new Flutter dashboard integration.

```mermaid
graph TD
    %% Data Sources
    subgraph "Data Acquisition"
        WS[Web Scrapers\nNews Sources]
        RS[Reddit Scraper\nSocial Media]
        SE[Subscription Events\nWeight Calculation]
    end
    
    %% Event Ingestion
    subgraph "Event Ingestion"
        HQ[High Priority Queue]
        SQ[Standard Priority Queue]
        SR[Sentiment Results Queue]
    end
    
    %% Processing
    subgraph "Sentiment Analysis"
        SA[Sentiment Analysis Service]
        FB[FinBERT Model]
        FG[FinGPT Model]
        LL[Llama4 Scout Model]
    end
    
    %% Storage
    subgraph "Data Storage"
        RD[Redis Cache]
        PG[PostgreSQL DB]
    end
    
    %% API Layer
    subgraph "API Layer"
        API[Backend API]
        AU[Authentication Service]
        WSVC[WebSocket Service]
    end
    
    %% Client Applications
    subgraph "Client Applications"
        %% Old StreamLit (Deprecated)
        ST[Streamlit Dashboard\n(Legacy)]
        
        %% New Flutter Implementation
        subgraph "Flutter Dashboard"
            FU[Flutter UI Layer]
            FSM[State Management\nProviders]
            FM[Model Layer\nJSON Serialization]
            FC[API Client]
        end
    end
    
    %% Monitoring
    subgraph "Monitoring"
        PR[Prometheus]
        GF[Grafana]
        LG[Logging]
    end
    
    %% Connections - Data Flow
    WS & RS & SE --> HQ & SQ
    HQ & SQ --> SA
    SA --> FB & FG & LL
    SA --> SR
    SR --> RD
    RD --> API
    API --> PG
    
    %% Client Connections
    API <--> FC
    WSVC <-.-> FSM
    AU <--> FC
    FC <--> FM
    FSM <--> FU
    FSM <--> FM
    API <--> ST
    
    %% Monitoring Connections
    SA & API --> PR
    PR --> GF
    SA & API --> LG
    
    %% Styling
    classDef acquisition fill:#e1f5fe,stroke:#01579b
    classDef ingestion fill:#e8f5e9,stroke:#2e7d32
    classDef processing fill:#fff3e0,stroke:#e65100
    classDef storage fill:#f3e5f5,stroke:#4a148c
    classDef api fill:#e8eaf6,stroke:#1a237e
    classDef client fill:#dcedc8,stroke:#33691e
    classDef flutter fill:#c8e6c9,stroke:#2e7d32,stroke-width:2
    classDef monitoring fill:#ffebee,stroke:#b71c1c
    
    class WS,RS,SE acquisition
    class HQ,SQ,SR ingestion
    class SA,FB,FG,LL processing
    class RD,PG storage
    class API,AU,WSVC api
    class ST client
    class FU,FSM,FM,FC flutter
    class PR,GF,LG monitoring
```

## Component Details

### Data Acquisition

This layer is responsible for gathering raw data from various sources:
- **Web Scrapers**: Extract data from financial news sites
- **Reddit Scraper**: Collects relevant posts from financial subreddits
- **Subscription Events**: Processes subscription-based data sources with weight calculation

### Event Ingestion

The event ingestion layer manages the flow of events through the system:
- **High Priority Queue**: For time-sensitive and high-value data sources
- **Standard Priority Queue**: For regular data processing
- **Sentiment Results Queue**: For processed sentiment analysis results

### Sentiment Analysis

The core processing layer that performs sentiment analysis:
- **Sentiment Analysis Service**: Coordinates the processing of events
- **FinBERT Model**: Base sentiment analysis model
- **FinGPT Model**: Advanced financial sentiment analysis
- **Llama4 Scout Model**: LLM-based sentiment analysis for complex content

### Data Storage

Persistence layer for storing and retrieving data:
- **Redis Cache**: High-speed cache for recently processed results
- **PostgreSQL DB**: Primary data store for sentiment data and system configuration

### API Layer

Provides access to the system's functionality:
- **Backend API**: RESTful API endpoints for data access
- **Authentication Service**: Manages user authentication and authorization
- **WebSocket Service**: Provides real-time data updates to clients

### Client Applications

User interfaces for interacting with the system:
- **Streamlit Dashboard (Legacy)**: Original data visualization interface
- **Flutter Dashboard**: New cross-platform application with enhanced features:
  - **Flutter UI Layer**: Presentation components and widgets
  - **State Management**: Provider-based state management
  - **Model Layer**: Data models with JSON serialization
  - **API Client**: Communication with backend services

### Monitoring

System observability and metrics:
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization dashboards
- **Logging**: Centralized logging system

## Key Changes in Latest Architecture

1. **Streamlit to Flutter Migration**: Replacing the Streamlit dashboard with a more performant and feature-rich Flutter application
2. **Enhanced API Layer**: Extended API capabilities to support the Flutter client
3. **WebSocket Integration**: Added real-time data streaming capability
4. **Improved Authentication**: More robust authentication flow for client applications
5. **Cross-Platform Support**: The new Flutter dashboard works on web, mobile, and desktop