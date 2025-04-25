# Flutter Dashboard Architecture

This document outlines the architecture of the Flutter dashboard for the Real-Time Sentiment Analysis system.

## Architecture Overview

```mermaid
graph TD
    subgraph "Flutter Application"
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
        SC <--> DP
        WD <--> DP
        WD <--> T
        
        DP <--> AC
        AP <--> AC
        SP --> T
        
        AC <--> MOD
        AC <--> SR
        
        AC <--> API
        AC <--> AUTH
        WS <--> SR
    end
    
    %% Styling
    classDef presentation fill:#e1f5fe,stroke:#01579b
    classDef state fill:#e8f5e9,stroke:#2e7d32
    classDef data fill:#fff3e0,stroke:#e65100
    classDef backend fill:#e1bee7,stroke:#6a1b9a
    
    class SC,WD,T presentation
    class DP,AP,SP state
    class AC,MOD,SR data
    class API,WS,AUTH backend
```

## Component Details

### Presentation Layer

The presentation layer is responsible for the UI and user interactions:

#### Screens
- `HomeScreen`: Main dashboard with tabs for different views
- `LoginScreen`: Authentication screen
- `SplashScreen`: Loading screen for app initialization

#### Widgets
- `TopSentimentsChart`: Bar chart for top positive/negative sentiments
- `DataFlowChart`: Line chart showing real-time data flow
- `SystemOverviewCard`: System metrics visualization
- `RecentEventsList`: List of recent sentiment events

#### Theming
- Light/dark mode support
- Consistent styling across the application
- Responsive design for multiple screen sizes

### State Management Layer

State management uses the Provider pattern for reactive state handling:

#### Providers
- `DashboardProvider`: Manages dashboard data and UI state
- `AuthProvider`: Handles authentication state and token management
- `SettingsProvider`: Manages user preferences

### Data Layer

The data layer handles API communication and data models:

#### API Client
- RESTful API client with HTTP package
- Error handling and retry logic
- Authentication token management

#### Models
- `TickerSentiment`: Sentiment data for financial tickers
- `SentimentEvent`: Individual sentiment analysis events
- `EventSource`: Data sources configuration
- `MessageStats`: System statistics and metrics
- `QueryParams`: Parameters for data filtering

#### Services/Repository
- Data caching and persistence
- Business logic implementation
- WebSocket connection management (planned)

### Backend Services

External services that the Flutter app communicates with:

- REST API: HTTP endpoints for data access
- WebSocket: Real-time data updates (planned)
- Authentication: JWT-based authentication service

## Class Diagram

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
    
    class DashboardProvider {
        -ApiClient apiClient
        -List~TickerSentiment~ topPositive
        -List~TickerSentiment~ topNegative
        -List~SentimentEvent~ recentEvents
        -List~String~ availableTickers
        -List~EventSource~ eventSources
        -bool isLoading
        +loadData() void
        +loadTopSentiment() void
        +loadRecentEvents(int limit) void
        +loadEventSources() void
        +loadSystemStats() void
        +loadDataFlow() void
    }
    
    class TickerSentiment {
        +String ticker
        +String sentiment
        +double score
        +double weight
        +int count
        +String model
        +String get sentimentColor
        +TickerSentiment.fromJson(Map json)
        +Map toJson()
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
        +String get sentimentColor
        +SentimentEvent.fromJson(Map json)
        +Map toJson()
    }
    
    class EventSource {
        +String name
        +bool isActive
        +List~String~ targets
        +String outputTopic
        +String frequency
        +EventSource.fromJson(Map json)
        +Map toJson()
    }
    
    class MessageStats {
        +MessageCategoryStats highPriority
        +MessageCategoryStats standardPriority
        +MessageCategoryStats sentimentResults
        +MessageStats.fromJson(Map json)
        +Map toJson()
    }
    
    ApiClient <-- DashboardProvider : uses
    TickerSentiment <-- ApiClient : returns
    SentimentEvent <-- ApiClient : returns
    EventSource <-- ApiClient : returns
    MessageStats <-- ApiClient : returns
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Flutter UI
    participant P as Provider
    participant A as API Client
    participant B as Backend API
    
    U->>UI: Open Dashboard
    UI->>P: Request Dashboard Data
    P->>A: API Request
    A->>B: HTTP Request
    B-->>A: JSON Response
    A-->>P: Parsed Models
    P-->>UI: Update State
    UI-->>U: Display Data
    
    U->>UI: Filter Data
    UI->>P: Update Filter Parameters
    P->>A: API Request with Filters
    A->>B: HTTP Request
    B-->>A: Filtered JSON Data
    A-->>P: Parsed Models
    P-->>UI: Update State
    UI-->>U: Display Filtered Data
```

## Directory Structure

```
flutter_dashboard/
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
│   │   ├── home_screen.dart        # Main dashboard
│   │   ├── login_screen.dart       # Login screen
│   │   └── splash_screen.dart      # Loading screen
│   ├── widgets/
│   │   ├── top_sentiments_chart.dart    # Sentiment visualization
│   │   ├── system_overview_card.dart    # System metrics cards
│   │   ├── data_flow_chart.dart         # Data flow graph
│   │   └── recent_events_list.dart      # Recent events list
│   └── main.dart                   # App entry point
├── assets/
│   └── images/                     # Image assets
└── pubspec.yaml                    # Dependencies
```

## Future Enhancements

1. **WebSocket Integration**: Real-time updates using WebSocket connection
2. **Offline Mode**: Local caching for offline operation
3. **Advanced Visualizations**: More interactive and detailed charts
4. **Push Notifications**: Alerts for significant sentiment changes
5. **Customizable Dashboard**: User-configurable dashboard layout
6. **Deep Linking**: Direct navigation to specific views
7. **Widget Testing**: Comprehensive test coverage