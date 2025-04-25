# Senti Hub - Architecture & Implementation Guide

**Document Version:** 2.0  
**Date:** April 22, 2025  
**Status:** Active Development  

This document outlines the architecture, implementation details, and connection specifications for the **Senti Hub** Flutter application (formerly Real-Time Sentiment Backend Visualizer).

## 1. Architecture Overview

The application follows a layered architecture separating presentation, state management, and data concerns.

```mermaid
graph TD
    subgraph "Flutter Application (Senti Hub)"
        %% Presentation Layer
        subgraph "Presentation Layer"
            direction LR
            SC[Screens]
            WD[Widgets]
            T[Theming]
        end

        %% State Management
        subgraph "State Management Layer"
            direction LR
            DP[Dashboard Provider]
            AP[Auth Provider]
            SP[Settings Provider]
        end

        %% Data Layer
        subgraph "Data Layer"
            direction LR
            AC[API Client]
            MOD[Models]
            SR[Services/Repository]
            WSVC[WebSocket Service]
        end

        %% External Services
        subgraph "Backend Services"
            direction LR
            API[REST API]
            WS[WebSocket]
            AUTH[Authentication]
        end

        %% Connections
        SC <--> WD
        SC -- Uses --> DP
        SC -- Uses --> AP
        WD -- Uses --> DP
        WD -- Uses --> SP
        WD <--> T

        DP -- Uses --> AC
        DP -- Uses --> WSVC
        AP -- Uses --> AC
        SP --> T

        AC <--> MOD
        AC <--> SR
        WSVC <--> MOD

        AC --> API
        AC --> AUTH
        WSVC --> WS

        SR -- Uses --> AC
        SR -- Uses --> WSVC
    end

    %% Styling
    classDef presentation fill:#e1f5fe,stroke:#01579b
    classDef state fill:#e8f5e9,stroke:#2e7d32
    classDef data fill:#fff3e0,stroke:#e65100
    classDef backend fill:#e1bee7,stroke:#6a1b9a

    class SC,WD,T presentation
    class DP,AP,SP state
    class AC,MOD,SR,WSVC data
    class API,WS,AUTH backend
```

## 2. Backend Integration Architecture

The Senti Hub connects to a comprehensive backend ecosystem that provides data acquisition, processing, and storage capabilities:

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
    subgraph "Senti Hub Flutter App"
        FU[Flutter UI Layer]
        FSM[State Management\nProviders]
        FM[Model Layer\nJSON Serialization]
        FC[API Client]
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
    class FU,FSM,FM,FC flutter
    class PR,GF,LG monitoring
```

## 3. Component Details

### 3.1 Presentation Layer

The presentation layer handles UI rendering and user interaction:

#### Screens
- **HomeScreen**: Main dashboard with visualization widgets and data display
- **LoginScreen**: Authentication screen for user credentials
- **SettingsScreen**: User preferences and application configuration
- **SplashScreen**: Loading screen for app initialization (Planned)

#### Widgets
- **TopSentimentsChart**: Bar chart for top positive/negative sentiments (Implemented)
- **RecentEventsList**: List of recent sentiment events (Implemented)
- **SystemOverviewCard**: System metrics visualization (Planned)
- **DataFlowChart**: Line chart showing real-time data flow (Planned)

#### Theming
- Light/dark mode support (Implemented)
- Consistent styling across the application
- Responsive design for multiple screen sizes (In Progress)

### 3.2 State Management Layer

State management uses the Provider pattern for reactive state handling:

#### Providers
- **DashboardProvider**: Manages dashboard data and UI state
- **AuthProvider**: Handles authentication state and token management
- **SettingsProvider**: Manages user preferences and theme settings

### 3.3 Data Layer

The data layer handles API communication and data models:

#### API Client
- RESTful API client with HTTP package
- Error handling and retry logic
- Authentication token management

#### Models
- **TickerSentiment**: Sentiment data for financial tickers
- **SentimentEvent**: Individual sentiment analysis events
- **EventSource**: Data sources configuration
- **MessageStats**: System statistics and metrics
- **QueryParams**: Parameters for data filtering

#### Services
- **WebSocketService**: Manages real-time data connections

### 3.4 Backend Services

External services that the Flutter app communicates with:

- **REST API**: HTTP endpoints for data access
- **WebSocket**: Real-time data updates
- **Authentication**: JWT-based authentication service

## 4. Backend Connection Details

### 4.1 PostgreSQL Database Connection

The application connects to PostgreSQL through the API service, which handles the database operations.

**Connection Parameters:**
```
POSTGRES_USER=pgadmin
POSTGRES_PASSWORD=localdev
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=sentimentdb
```

**Connection String:**
```
postgresql://pgadmin:localdev@postgres:5432/sentimentdb
```

**Key Tables:**
- `sentiment_events`: Stores processed sentiment events
  - Columns: id, source, priority, text, timestamp, model, sentiment_score, sentiment_label, processing_time, event_id
- `ticker_sentiments`: Stores ticker-specific sentiment scores
  - Columns: id, event_id, ticker, sentiment_score, sentiment_label

**SQLAlchemy Models:**
```python
class SentimentEvent(Base):
    __tablename__ = "sentiment_events"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    model = Column(String(100), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(50), nullable=True)
    processing_time = Column(Float, nullable=True)
    event_id = Column(String(100), unique=True, index=True)
    ticker_sentiments = relationship("TickerSentiment", back_populates="event")

class TickerSentiment(Base):
    __tablename__ = "ticker_sentiments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("sentiment_events.id"), nullable=False)
    ticker = Column(String(20), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    sentiment_label = Column(String(50), nullable=False)
    event = relationship("SentimentEvent", back_populates="ticker_sentiments")
```

### 4.2 Redis Cache Connection

Redis provides high-speed caching for recently processed sentiment results.

**Connection Parameters:**
```
REDIS_HOST=redis
REDIS_PORT=6379
```

**Redis Usage:**
1. **Caching Sentiment Results**: Recent sentiment analysis results are cached for quick retrieval
2. **Configuration Storage**: System configuration parameters stored in Redis
3. **WebSocket Notification**: Used as a pubsub mechanism for real-time updates

**Redis Data Structure:**
- Hash: `sentiment:{event_id}` - Stores sentiment event details
- Set: `tickers` - Stores unique ticker symbols
- Sorted Set: `ticker_scores` - Ranked list of ticker sentiment scores

**Cache Implementation in Sentiment Service:**
```python
class RedisClient:
    def __init__(self, host='redis', port=6379):
        self.host = host
        self.port = port
        self.redis = None
        self.is_connected = False
        
    async def connect(self):
        try:
            self.redis = aioredis.from_url(f"redis://{self.host}:{self.port}")
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.is_connected = False
            return False
            
    async def set_sentiment(self, event_id, sentiment_data, ttl=3600):
        if not self.is_connected:
            return False
        
        try:
            # Store sentiment as hash
            await self.redis.hset(f"sentiment:{event_id}", mapping=sentiment_data)
            
            # Set expiration
            if ttl:
                await self.redis.expire(f"sentiment:{event_id}", ttl)
                
            return True
        except Exception as e:
            logger.error(f"Redis error: {e}")
            return False
```

### 4.3 API Endpoints

The Flutter app communicates with these RESTful API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sentiment/ticker/{ticker}` | GET | Get sentiment for a specific ticker |
| `/sentiment/tickers` | GET | Get list of available tickers |
| `/sentiment/top` | GET | Get top tickers by sentiment score |
| `/sentiment/analyze` | POST | Analyze sentiment of custom text |
| `/sentiment/query` | POST | Query sentiment events with filters |
| `/sentiment/event` | POST | Store a new sentiment event |
| `/sentiment/metadata` | GET | Get metadata for UI filtering |
| `/auth/login` | POST | User authentication |
| `/auth/register` | POST | User registration |

### 4.4 WebSocket Integration

The Flutter app connects to the WebSocket server for real-time updates:

**Connection URL:**
```
ws://api-host:8001/ws?token={auth_token}
```

**WebSocket Message Types:**
1. **new_event**: New sentiment event has been processed
2. **sentiment_update**: Existing sentiment score has been updated
3. **stats_update**: System statistics have been updated

**WebSocket Message Format:**
```json
{
  "type": "new_event",
  "data": {
    "event_id": "abc123",
    "timestamp": "2025-04-22T14:30:00Z",
    "source": "news",
    "sentiment_score": 0.75,
    "sentiment_label": "positive",
    "ticker": "AAPL"
  }
}
```

**Flutter WebSocket Service Implementation:**
```dart
class WebSocketService {
  WebSocketChannel? _channel;
  StreamController<Map<String, dynamic>> _controller = StreamController.broadcast();
  Stream<Map<String, dynamic>> get sentimentStream => _controller.stream;
  String baseUrl;
  String? authToken;
  bool isConnected = false;
  
  WebSocketService({
    this.baseUrl = 'ws://localhost:8001/ws',
    this.authToken,
  });
  
  void connect() {
    final wsUrl = authToken != null ? '$baseUrl?token=$authToken' : baseUrl;
    _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
    _channel!.stream.listen(
      (dynamic message) {
        try {
          isConnected = true;
          final data = jsonDecode(message);
          _controller.add(data);
        } catch (e) {
          print('Error processing WebSocket message: $e');
        }
      },
      onError: (error) {
        isConnected = false;
        print('WebSocket error: $error');
        reconnect();
      },
      onDone: () {
        isConnected = false;
        reconnect();
      },
    );
  }
  
  void reconnect() {
    if (_channel != null) {
      Future.delayed(Duration(seconds: 5), connect);
    }
  }
  
  void close() {
    _channel?.sink.close();
    _channel = null;
    isConnected = false;
  }
}
```

## 5. Class Diagram

```mermaid
classDiagram
    class ApiClient {
        -String baseUrl
        -String? authToken
        -http.Client client
        +setAuthToken(String token)
        +clearAuthToken()
        +getSystemStats() MessageStats
        +getTickerSentiment(String ticker) TickerSentiment
        +getTopPositiveSentiment(int limit) List~TickerSentiment~
        +getTopNegativeSentiment(int limit) List~TickerSentiment~
        +getRecentEvents(int limit) List~SentimentEvent~
        +querySentimentEvents(QueryParams) List~SentimentEvent~
        +getEventSources() List~EventSource~
        +login(String username, String password) String
    }
    
    class WebSocketService {
        -String serverUrl
        -WebSocketChannel? channel
        -StreamSubscription? streamSubscription
        -bool isConnected
        +connect(Function onMessage)
        +disconnect()
        +sendMessage(String message)
        +dispose()
    }
    
    class DashboardProvider {
        -ApiClient apiClient
        -WebSocketService webSocketService
        -List~TickerSentiment~ topPositive
        -List~TickerSentiment~ topNegative
        -List~SentimentEvent~ recentEvents
        -bool isLoadingEvents
        -bool isLoadingTopSentiments
        +loadAllDashboardData() void
        +loadRecentEvents(int limit) void
        +loadTopSentiments(int limit) void
        #_handleWebSocketMessage(dynamic message) void
    }
    
    class AuthProvider {
        -ApiClient apiClient
        -String? _token
        -bool _isAuthenticated
        -bool _isAuthenticating
        +login(String u, String p) Future~bool~
        +logout() Future~void~
    }
    
    class SettingsProvider {
        -ThemeMode _themeMode
        +ThemeMode themeMode
        +setThemeMode(ThemeMode mode) Future~void~
        #_loadPreferences() Future~void~
    }
    
    class TickerSentiment {
        +String ticker
        +String sentiment
        +double score
        +double weight
        +int count
        +String model
        +Color sentimentColor
    }
    
    class SentimentEvent {
        +int id
        +String eventId
        +DateTime timestamp
        +String source
        +String priority
        +String model
        +double sentimentScore
        +String sentimentLabel
    }
    
    class EventSource {
        +String name
        +bool isActive
    }
    
    class MessageStats {
       +MessageCategoryStats highPriority
       +MessageCategoryStats standardPriority
       +MessageCategoryStats sentimentResults
    }
    
    ApiClient <-- DashboardProvider : uses
    WebSocketService <-- DashboardProvider : uses
    ApiClient <-- AuthProvider : uses
    
    TickerSentiment <-- ApiClient : returns
    SentimentEvent <-- ApiClient : returns
    EventSource <-- ApiClient : returns
    MessageStats <-- ApiClient : returns
    
    SentimentEvent <-- WebSocketService : receives/parses
```

## 6. Data Flow Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Flutter UI
    participant P as Provider (Dashboard)
    participant A as API Client
    participant B as Backend API
    participant WS as WebSocket Service
    participant WSS as WebSocket Server
    participant R as Redis Cache
    participant DB as PostgreSQL
    
    U->>UI: Open App / Login
    UI-->>P: Provider Initialized
    P->>A: Request Initial Data
    P->>WS: Connect WebSocket
    
    A->>B: HTTP Request (Events)
    B->>R: Check Cache
    
    alt Cache Hit
        R-->>B: Return Cached Data
    else Cache Miss
        B->>DB: Query Database
        DB-->>B: Return Results
        B->>R: Update Cache
    end
    
    A->>B: HTTP Request (Sentiments)
    B->>DB: Query Database
    DB-->>B: Return Results
    
    WS->>WSS: Establish Connection
    WSS-->>WS: Connection Ack
    
    B-->>A: JSON Response (Events)
    B-->>A: JSON Response (Sentiments)
    
    A-->>P: Parsed Models (Events)
    A-->>P: Parsed Models (Sentiments)
    P-->>UI: Update State (Loading false)
    UI-->>U: Display Initial Data
    
    %% Real-time Update
    WSS-->>WS: Send Message (new_event)
    WS-->>P: Invoke onMessage callback
    P-->>P: Process Message, Update State
    P-->>UI: Update State (notifyListeners)
    UI-->>U: Display Updated Data
```

## 7. Directory Structure

```
senti/
├── lib/
│   ├── api/
│   │   └── api_client.dart         # API communication
│   ├── constants/
│   │   └── app_theme.dart          # Theming constants
│   ├── models/
│   │   ├── ticker_sentiment.dart   # Sentiment data model
│   │   ├── sentiment_event.dart    # Event data model
│   │   ├── event_source.dart       # Source configuration
│   │   ├── message_stats.dart      # System metrics
│   │   └── query_params.dart       # Query parameters
│   ├── providers/
│   │   ├── dashboard_provider.dart # Dashboard state
│   │   ├── auth_provider.dart      # Authentication state
│   │   └── settings_provider.dart  # User preferences
│   ├── screens/
│   │   ├── home/
│   │   │   └── home_screen.dart    # Main dashboard
│   │   ├── login/
│   │   │   └── login_screen.dart   # Login screen
│   │   └── settings/
│   │       └── settings_screen.dart # Settings screen
│   ├── services/
│   │   └── websocket_service.dart  # Real-time updates
│   ├── widgets/
│   │   ├── common/                 # Shared widgets
│   │   └── dashboard/
│   │       ├── top_sentiments_chart.dart
│   │       └── recent_events_list.dart
│   └── main.dart                   # App entry point
```

## 8. Database Schema

```mermaid
erDiagram
    SENTIMENT_EVENTS ||--o{ TICKER_SENTIMENTS : has
    USERS ||--o{ USER_PREFERENCES : has
    
    SENTIMENT_EVENTS {
        int id PK
        string event_id UK
        string source
        string priority
        text text
        datetime timestamp
        string model
        float sentiment_score
        string sentiment_label
        float processing_time
    }
    
    TICKER_SENTIMENTS {
        int id PK
        int event_id FK
        string ticker
        float sentiment_score
        string sentiment_label
    }
    
    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        datetime created_at
        datetime last_login
        boolean is_active
    }
    
    USER_PREFERENCES {
        int id PK
        int user_id FK
        string theme
        json favorite_tickers
        json notification_settings
    }
```

## 9. Environment Configuration

### 9.1 API Service
```
POSTGRES_USER=pgadmin
POSTGRES_PASSWORD=localdev
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=sentimentdb
REDIS_HOST=redis
REDIS_PORT=6379
LOG_LEVEL=INFO
JWT_SECRET=your_jwt_secret
```

### 9.2 Sentiment Service
```
REDIS_HOST=redis
REDIS_PORT=6379
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
HIPRI_TOPIC=high-priority-events
STDPRI_TOPIC=standard-priority-events
SENTIMENT_RESULTS_TOPIC=sentiment-results
CONSUMER_GROUP_ID=sentiment-service-group
AUTOSTART_LISTENERS=true
LOG_LEVEL=INFO
MODEL_PATH=/app/models/weights/finbert
```

### 9.3 Flutter App Configuration (environment.dart)
```dart
class Environment {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://localhost:8001',
  );
  
  static const String wsBaseUrl = String.fromEnvironment(
    'WS_URL',
    defaultValue: 'ws://localhost:8001/ws',
  );
  
  static const bool useMockData = bool.fromEnvironment(
    'USE_MOCK_DATA',
    defaultValue: false,
  );
}
```

## 10. Development & Testing

### 10.1 Starting the Backend Services

Using Docker Compose:
```bash
docker compose up -d
```

Starting individual services:
```bash
# API Service
uvicorn api.main:app --reload --port 8001

# Sentiment Service
uvicorn sentiment_service.main:app --reload --port 8000
```

### 10.2 Running the Flutter App

```bash
# For web
cd senti
flutter run -d chrome --web-port=8080

# For desktop
flutter run -d linux  # or windows/macos

# For mobile
flutter run -d <device-id>
```

### 10.3 Testing the System

```bash
# Run mock tests
./run_tests.sh --mock

# Run integration tests
./run_tests.sh --integration

# Run all tests
./run_tests.sh --all

# Run specific tests
pytest tests/test_sentiment_api.py
```

## 11. Build Status & Roadmap

### 11.1 Completed
- Core application structure and state management
- Basic UI components and visualization widgets
- Authentication flow and token management
- Offline preference storage
- Light/dark theme support
- Mock data integration

### 11.2 In Progress
- WebSocket real-time updates integration
- API client implementation for backend communication
- Error handling and retry logic
- Responsive design improvements

### 11.3 Future Enhancements
- Advanced visualizations and charts
- Filtering and search functionality
- Notification system
- Offline data caching
- Customizable dashboard layout
- Integration testing
- Performance optimizations

## 5. Middle Tier API Design

The middle tier acts as an interface between the Flutter client application and the backend services. It provides consistent API endpoints, handles data transformation, validation, authentication, and request routing.

```mermaid
graph TD
    %% Client
    Client[Senti Flutter App]

    %% Middle Tier
    subgraph "Middle Tier API Layer"
        REST[REST API Gateway]
        WS[WebSocket Gateway]
        Auth[Authentication Service]
        Facade[API Facade Layer]
        Validate[Validation Layer]
        Cache[Cache Manager]
    end

    %% Backend Services
    subgraph "Backend Services"
        SentimentSVC[Sentiment Analysis Service]
        DataAcquSVC[Data Acquisition Service]
        DB[(PostgreSQL)]
        Redis[(Redis Cache)]
        MessageQ[Message Queue\nKafka]
    end

    %% Connections
    Client --> REST
    Client --> WS
    Client --> Auth
    
    REST --> Facade
    WS --> Facade
    Auth --> Facade
    
    Facade --> Validate
    Validate --> Cache
    
    Cache --> SentimentSVC
    Cache --> DataAcquSVC
    Cache --> Redis
    
    SentimentSVC --> DB
    SentimentSVC --> MessageQ
    DataAcquSVC --> MessageQ
    DataAcquSVC --> DB
    
    %% Styling
    classDef client fill:#dcedc8,stroke:#33691e
    classDef middletier fill:#e8eaf6,stroke:#1a237e
    classDef backend fill:#fff3e0,stroke:#e65100
    classDef database fill:#f3e5f5,stroke:#4a148c
    
    class Client client
    class REST,WS,Auth,Facade,Validate,Cache middletier
    class SentimentSVC,DataAcquSVC,MessageQ backend
    class DB,Redis database
```

### 5.1 API Facade Layer

The API Facade provides a unified interface for all backend services, simplifying the client application's interaction with the system.

#### Core Interfaces

```typescript
// Service interfaces that define the contract between the client and backend

export interface IAuthService {
  login(credentials: LoginRequest): Promise<AuthResponse>;
  register(userData: RegisterRequest): Promise<AuthResponse>;
  refreshToken(token: string): Promise<AuthResponse>;
  validateToken(token: string): Promise<boolean>;
  logout(token: string): Promise<void>;
}

export interface ISentimentService {
  // REST endpoints (batch operations)
  getTickerSentiment(ticker: string): Promise<TickerSentiment>;
  getTopSentiments(params: TopSentimentParams): Promise<TickerSentiment[]>;
  getRecentEvents(limit: number): Promise<SentimentEvent[]>;
  querySentimentEvents(params: QueryParams): Promise<SentimentEvent[]>;
  analyzeText(text: string, options?: AnalysisOptions): Promise<SentimentResponse>;
  getEventSources(): Promise<EventSource[]>;
  getSystemStats(): Promise<MessageStats>;
  
  // WebSocket connections
  subscribeToTickerUpdates(tickers: string[]): void;
  subscribeToEvents(filters?: EventFilter): void;
  subscribeToSystemStats(interval?: number): void;
  unsubscribeFromTicker(ticker: string): void;
  unsubscribeFromEvents(): void;
  unsubscribeFromSystemStats(): void;
}

export interface IDataService {
  getHistoricalSentiment(ticker: string, timeRange: TimeRange): Promise<HistoricalSentiment[]>;
  getCorrelatedTickers(ticker: string, limit?: number): Promise<CorrelatedTicker[]>;
  exportData(params: ExportParams): Promise<string>; // URL to download file
}
```

### 5.2 API Request/Response Definitions

#### Authentication Endpoints

```typescript
// POST /auth/login
interface LoginRequest {
  username: string;
  password: string;
  deviceInfo?: string;
}

interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  user: {
    id: number;
    username: string;
    email: string;
    roles: string[];
  };
}

// POST /auth/register
interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
}

// POST /auth/refresh
interface RefreshRequest {
  refreshToken: string;
}

// POST /auth/logout
interface LogoutRequest {
  refreshToken: string;
}
```

#### Sentiment Analysis Endpoints

```typescript
// GET /sentiment/ticker/{ticker}
interface TickerSentiment {
  ticker: string;
  sentiment: "positive" | "negative" | "neutral";
  score: number;
  weight: number;
  count: number;
  model: string;
}

// GET /sentiment/top
interface TopSentimentParams {
  limit?: number; // default: 10
  minScore?: number; // optional, e.g. 0 for positive only
  maxScore?: number; // optional, e.g. 0 for negative only
  sortBy?: "score" | "count"; // default: "score"
  order?: "asc" | "desc"; // default: "desc"
}

// GET /sentiment/events
interface SentimentEvent {
  id: number;
  eventId: string;
  timestamp: string; // ISO format
  source: string;
  priority: "high" | "standard";
  model: string;
  sentimentScore: number;
  sentimentLabel: "positive" | "negative" | "neutral";
  tickers?: string[];
  text?: string; // may be omitted for privacy/storage reasons
}

// POST /sentiment/query
interface QueryParams {
  startDate?: string; // ISO format
  endDate?: string; // ISO format
  sources?: string[];
  priority?: string[];
  models?: string[];
  minScore?: number;
  maxScore?: number;
  tickers?: string[];
  limit?: number; // default: 100
  offset?: number; // default: 0
}

// POST /sentiment/analyze
interface AnalysisOptions {
  model?: string; // default model if not specified
  tickers?: string[]; // optional list of tickers to associate
}

interface SentimentResponse {
  sentiment: "positive" | "negative" | "neutral";
  score: number;
  tickers: string[];
  model: string;
}

// GET /sentiment/sources
interface EventSource {
  name: string;
  isActive: boolean;
  targets?: string[]; // e.g. tickers or topics
  outputTopic?: string;
  frequency?: string;
}

// GET /sentiment/stats
interface MessageStats {
  highPriority: MessageCategoryStats;
  standardPriority: MessageCategoryStats;
  sentimentResults: MessageCategoryStats;
}

interface MessageCategoryStats {
  count: number;
  averageProcessingTime: number;
  messagesPerMinute: number;
  errorRate: number;
}
```

#### Historical Data Endpoints

```typescript
// GET /data/historical/{ticker}
interface TimeRange {
  start: string; // ISO format
  end: string; // ISO format
  interval?: "hour" | "day" | "week" | "month"; // default: "day"
}

interface HistoricalSentiment {
  timestamp: string; // ISO format
  score: number;
  volume: number; // number of events
}

// GET /data/correlated/{ticker}
interface CorrelatedTicker {
  ticker: string;
  correlationScore: number; // -1 to 1
  sentimentSimilarity: number; // 0 to 1
}

// POST /data/export
interface ExportParams {
  format: "csv" | "json" | "parquet";
  tickers?: string[];
  timeRange?: TimeRange;
  includeText?: boolean;
}
```

### 5.3 WebSocket Message Definitions

```typescript
// WebSocket message type definitions
type WebSocketMessageType = 
  | "new_event" 
  | "sentiment_update" 
  | "stats_update" 
  | "ticker_alert"
  | "connection_status"
  | "error";

interface WebSocketMessage {
  type: WebSocketMessageType;
  data: any; // Type depends on message type
}

interface EventMessage {
  type: "new_event";
  data: SentimentEvent;
}

interface SentimentUpdateMessage {
  type: "sentiment_update";
  data: {
    ticker: string;
    previousScore: number;
    newScore: number;
    sentimentLabel: string;
    timestamp: string;
  };
}

interface StatsUpdateMessage {
  type: "stats_update";
  data: MessageStats;
}

interface TickerAlertMessage {
  type: "ticker_alert";
  data: {
    ticker: string;
    sentimentShift: number; // The change in sentiment
    threshold: number; // The threshold that was crossed
    timestamp: string;
  };
}

interface ConnectionStatusMessage {
  type: "connection_status";
  data: {
    connected: boolean;
    timestamp: string;
    reconnectAttempt?: number;
  };
}

interface ErrorMessage {
  type: "error";
  data: {
    code: string;
    message: string;
    context?: any;
  };
}

// Subscription message from client to server
interface SubscriptionRequest {
  action: "subscribe" | "unsubscribe";
  channel: "tickers" | "events" | "stats";
  filters?: {
    tickers?: string[];
    sources?: string[];
    threshold?: number;
  };
}
```

### 5.4 Unit Test Specifications

The following test specifications define how to verify the API endpoints and WebSocket connections:

#### Authentication Service Tests

```typescript
describe('AuthService', () => {
  it('should successfully login with valid credentials', async () => {
    // Test logic
  });

  it('should reject login with invalid credentials', async () => {
    // Test logic
  });

  it('should register a new user with valid data', async () => {
    // Test logic
  });

  it('should reject registration with existing username', async () => {
    // Test logic
  });

  it('should refresh access token with valid refresh token', async () => {
    // Test logic
  });

  it('should validate a valid token', async () => {
    // Test logic
  });

  it('should invalidate an expired token', async () => {
    // Test logic
  });

  it('should successfully logout and invalidate tokens', async () => {
    // Test logic
  });
});
```

#### REST API Endpoint Tests

```typescript
describe('SentimentAPI', () => {
  describe('GET /sentiment/ticker/{ticker}', () => {
    it('should return sentiment data for a valid ticker', async () => {
      const response = await request(app)
        .get('/sentiment/ticker/AAPL')
        .set('Authorization', `Bearer ${validToken}`);
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('ticker', 'AAPL');
      expect(response.body).toHaveProperty('score');
      expect(response.body).toHaveProperty('sentiment');
    });

    it('should return 404 for non-existent ticker', async () => {
      // Test logic
    });

    it('should return 401 without valid authentication', async () => {
      // Test logic
    });
  });

  describe('GET /sentiment/top', () => {
    it('should return top positive sentiments with default parameters', async () => {
      // Test logic
    });

    it('should respect the limit parameter', async () => {
      // Test logic
    });

    it('should filter by minimum score', async () => {
      // Test logic
    });

    it('should sort results as specified', async () => {
      // Test logic
    });
  });

  describe('POST /sentiment/analyze', () => {
    it('should analyze provided text and return sentiment', async () => {
      const response = await request(app)
        .post('/sentiment/analyze')
        .set('Authorization', `Bearer ${validToken}`)
        .send({
          text: 'Company XYZ announced positive earnings, exceeding expectations.',
        });
      
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('sentiment');
      expect(response.body).toHaveProperty('score');
      expect(response.body).toHaveProperty('model');
    });

    it('should identify tickers in text when not specified', async () => {
      // Test logic
    });

    it('should use specified model when provided', async () => {
      // Test logic
    });
  });

  // Add tests for other endpoints
});
```

#### WebSocket Connection Tests

```typescript
describe('WebSocket Service', () => {
  let wsClient;
  let receivedMessages = [];

  beforeEach(async () => {
    wsClient = new WebSocket('ws://localhost:8001/ws?token=' + validToken);
    
    await new Promise(resolve => {
      wsClient.onopen = () => resolve();
    });
    
    receivedMessages = [];
    wsClient.onmessage = (message) => {
      receivedMessages.push(JSON.parse(message.data));
    };
  });

  afterEach(() => {
    wsClient.close();
  });

  it('should establish connection with valid token', async () => {
    expect(wsClient.readyState).toBe(WebSocket.OPEN);
  });

  it('should reject connection with invalid token', async () => {
    // Test logic
  });

  it('should receive ticker updates after subscription', async () => {
    // Subscribe to a ticker
    wsClient.send(JSON.stringify({
      action: 'subscribe',
      channel: 'tickers',
      filters: {
        tickers: ['AAPL', 'MSFT']
      }
    }));
    
    // Trigger an update (may need to be done externally)
    
    // Wait for the response
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Check received messages
    const tickerUpdates = receivedMessages.filter(msg => 
      msg.type === 'sentiment_update' && 
      ['AAPL', 'MSFT'].includes(msg.data.ticker)
    );
    
    expect(tickerUpdates.length).toBeGreaterThan(0);
  });

  it('should stop receiving updates after unsubscribe', async () => {
    // Test logic
  });

  it('should maintain connection and reconnect after service restart', async () => {
    // This would be more of an integration test
    // Test logic
  });
});
```

#### API Health Check Tests

```typescript
describe('Health Checks', () => {
  it('API service should respond to health endpoint', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('status', 'healthy');
  });

  it('Sentiment service should be operational', async () => {
    const response = await request(app).get('/health/services');
    expect(response.status).toBe(200);
    expect(response.body.services).toHaveProperty('sentiment');
    expect(response.body.services.sentiment).toBe('operational');
  });

  it('Database should be connected', async () => {
    const response = await request(app).get('/health/database');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('database', 'connected');
  });

  it('Redis cache should be available', async () => {
    const response = await request(app).get('/health/cache');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('cache', 'connected');
  });

  it('WebSocket service should be running', async () => {
    const response = await request(app).get('/health/websocket');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('websocket', 'running');
  });
});
```

### 5.5 API Implementation Guidelines

#### REST Endpoints

- All endpoints should return consistent error formats
- Use appropriate HTTP status codes (200, 201, 400, 401, 403, 404, 500)
- Apply rate limiting to prevent abuse
- Include pagination for list endpoints
- Support CORS for browser clients
- Implement request validation using a schema validator
- Log all requests and responses for debugging
- Add appropriate caching headers

#### WebSocket Best Practices

- Implement heartbeat mechanism to detect disconnections
- Support automatic reconnection with exponential backoff
- Use subscription-based model for specific updates
- Implement message acknowledgement for critical notifications
- Provide connection status updates to clients
- Handle graceful service degradation when backend services are unavailable

#### Authentication Requirements

- Use JWT for authentication with short-lived access tokens
- Support refresh tokens for maintaining session
- Implement token revocation
- Store token status in Redis for quick validation
- Apply RBAC (Role-Based Access Control) for authorization
- Log authentication events for security auditing

## 12. Common Issues & Troubleshooting

### WebSocket Connection
- Ensure the WebSocket server is running and accessible
- Check authentication token validity if connection is rejected
- Verify network connectivity and firewall settings
- Look for CORS issues if connecting from web application
- Check for proper WebSocket handshake in network logs

### API Data Retrieval
- Verify API service is running using health check endpoint
- Check authentication headers are correctly set
- Inspect PostgreSQL connection if data is missing
- Verify payload format matches API expectations
- Look for validation errors in API logs

### Redis Cache
- Use `redis-cli` to manually verify cached data: `redis-cli hgetall sentiment:123`
- Check TTL settings if data expires too quickly: `redis-cli ttl sentiment:123`
- Monitor memory usage with `redis-cli info memory`
- Verify Redis connection string in service configuration

### PostgreSQL Database
- Connect using `psql`: `psql -h postgres -U pgadmin -d sentimentdb`
- Verify tables exist: `\dt`
- Check sentiment data: `SELECT * FROM sentiment_events LIMIT 10;`
- Monitor query performance: `EXPLAIN ANALYZE SELECT * FROM sentiment_events WHERE ticker = 'AAPL';`
- Check connection pool usage and configure appropriately

### Summary for Context
- Project: Senti Hub (Flutter Dashboard)
- Directory: ~/WSL_RT_Sentiment/senti
- Target: Linux Desktop (flutter run -d linux) and Web (flutter build web --wasm --base-href /senti/)
- State Management: Provider
- Status: Phase 5 started. Core structure, auth flow, basic dashboard UI with mock data (events list, sentiment chart), and theme settings persistence are implemented. Basic WebSocket connection setup is done but message handling is placeholder.
- Known Issues: Initial rendering problems resolved by starting a new project. WebSocket connection uses a placeholder URL and will fail until updated.
- Next Step: Implement WebSocket message parsing