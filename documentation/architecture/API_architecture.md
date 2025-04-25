# Sentiment API Architecture Diagram

Below is a mermaid diagram representing the architecture of the Real-Time Sentiment Analysis API. This diagram shows the flow of data between components, the API endpoints, and the relationships between different services.

## API Component Diagram

```mermaid
graph TD
    Client([Client Application]) -->|HTTP/WS Requests| LB[Load Balancer]
    LB --> API[API Service]
    
    subgraph "API Layer"
        API --> AuthRouter[Auth Router]
        API --> SentimentRouter[Sentiment Router]
        API --> StatsRouter[Stats Router]
        API --> SubscriptionRouter[Subscription Router]
        API --> WSHandler[WebSocket Handler]
    end
    
    subgraph "Service Layer"
        AuthRouter --> AuthService[Authentication Service]
        SentimentRouter --> SentimentService[Sentiment Service]
        StatsRouter --> StatsService[Statistics Service]
        SubscriptionRouter --> SubscriptionService[Subscription Service]
        WSHandler --> NotificationService[Notification Service]
    end
    
    subgraph "Data Layer"
        SentimentService --> DB[(PostgreSQL)]
        SentimentService --> Redis[(Redis Cache)]
        StatsService --> DB
        SubscriptionService --> DB
        AuthService --> DB
        NotificationService --> Redis
    end
    
    subgraph "External Services"
        SentimentService --> KafkaBroker[Kafka Message Broker]
        KafkaBroker --> SentimentProcessor[Sentiment Processing Service]
        SentimentProcessor --> FinBERT[FinBERT Model]
        SentimentProcessor --> FinGPT[FinGPT Model]
        SentimentProcessor --> Llama[Llama4 Scout Model]
        SentimentProcessor --> KafkaBroker
    end
    
    classDef apiComponents fill:#f9f,stroke:#333,stroke-width:2px;
    classDef serviceComponents fill:#bbf,stroke:#333,stroke-width:2px;
    classDef dataComponents fill:#bfb,stroke:#333,stroke-width:2px;
    classDef externalComponents fill:#fbb,stroke:#333,stroke-width:2px;
    
    class AuthRouter,SentimentRouter,StatsRouter,SubscriptionRouter,WSHandler apiComponents;
    class AuthService,SentimentService,StatsService,SubscriptionService,NotificationService serviceComponents;
    class DB,Redis dataComponents;
    class KafkaBroker,SentimentProcessor,FinBERT,FinGPT,Llama externalComponents;
```

## API Endpoint Diagram

```mermaid
classDiagram
    class AuthAPI {
        +login(username, password): TokenResponse
        +refresh(token): TokenResponse
        +validate(token): UserResponse
    }
    
    class SentimentAPI {
        +getTickerSentiment(ticker): TickerSentiment
        +getAvailableTickers(): Ticker[]
        +getTopSentiments(limit, minScore, maxScore, sortBy, order): TickerSentiment[]
        +querySentimentEvents(filters): SentimentEvent[]
        +createSentimentEvent(event): SentimentEvent
        +analyzeTextSentiment(text): SentimentAnalysis
    }
    
    class StatsAPI {
        +getSystemStats(): SystemStats
        +getMetadata(): Metadata
    }
    
    class SubscriptionAPI {
        +getSubscriptions(): Subscription[]
        +createSubscription(subscription): Subscription
        +updateSubscription(id, subscription): Subscription
        +deleteSubscription(id): void
    }
    
    class WebSocketAPI {
        +connect(token): WebSocketConnection
        +subscribe(channel, filters): SubscriptionStatus
        +unsubscribe(channel): SubscriptionStatus
    }
    
    class DataModels {
        TickerSentiment
        SentimentEvent
        SentimentAnalysis
        SystemStats
        Metadata
        Subscription
        TokenResponse
        UserResponse
    }
    
    AuthAPI -- DataModels
    SentimentAPI -- DataModels
    StatsAPI -- DataModels
    SubscriptionAPI -- DataModels
    WebSocketAPI -- DataModels
```

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB
    participant Cache
    participant Kafka
    participant Model
    
    Client->>API: POST /sentiment/event
    Note over API: Validate request
    API->>DB: Store event
    API->>Kafka: Produce message
    API->>Client: Return event response
    
    Kafka->>Model: Consume message
    Model->>Model: Analyze sentiment
    Model->>Kafka: Produce results
    
    Kafka->>API: Consume results
    API->>DB: Update event with results
    API->>Cache: Update ticker sentiment
    
    Client->>API: GET /sentiment/ticker/AAPL
    API->>Cache: Check cache
    Cache->>API: Return cached data
    API->>Client: Return ticker sentiment
    
    Client->>API: WS Connect
    API->>Client: Accept connection
    Client->>API: Subscribe to ticker updates
    Note over API: Register subscription
    
    API->>Client: Send ticker updates in real-time
```

## Entity Relationship Diagram

```mermaid
erDiagram
    USER {
        int id PK
        string username
        string email
        string password_hash
        string subscription_tier
        datetime created_at
    }
    
    SENTIMENT_EVENT {
        int id PK
        string event_id UK
        datetime timestamp
        string source
        string priority
        text text
        string model
        float sentiment_score
        string sentiment_label
        float processing_time
    }
    
    TICKER_SENTIMENT {
        int id PK
        int event_id FK
        string ticker
        float sentiment_score
        string sentiment_label
    }
    
    SUBSCRIPTION {
        int id PK
        int user_id FK
        string name
        datetime created_at
    }
    
    SUBSCRIPTION_FILTER {
        int id PK
        int subscription_id FK
        string filter_type
        string filter_value
    }
    
    USER ||--o{ SUBSCRIPTION : "has"
    SENTIMENT_EVENT ||--o{ TICKER_SENTIMENT : "contains"
    SUBSCRIPTION ||--o{ SUBSCRIPTION_FILTER : "has"
```