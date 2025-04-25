# Flutter Dashboard Project Structure

This document provides an overview of the Flutter project structure created to replace the Streamlit dashboard for the Real-Time Sentiment Analysis system.

## Project Structure Overview

```
flutter_dashboard/
├── assets/
│   ├── config/    # Configuration files including .env
│   ├── icons/     # App icons
│   └── images/    # Images and graphics
├── lib/
│   ├── api/       # API clients
│   ├── constants/ # App constants and themes
│   ├── models/    # Data models
│   ├── providers/ # State management
│   ├── screens/   # Full screen UIs
│   ├── services/  # Business logic services
│   ├── utils/     # Utility functions
│   ├── widgets/   # Reusable UI components
│   └── main.dart  # App entry point
├── test/
│   ├── unit/      # Unit tests
│   └── widget/    # Widget tests
└── pubspec.yaml   # Dependencies
```

## Key Components

### 1. API Client

The `ApiClient` class in `lib/api/api_client.dart` handles all API communication with the backend sentiment analysis services. It includes methods for:

- Fetching ticker sentiment data
- Querying sentiment events with filters
- Getting metadata for UI filtering
- Submitting sentiment analysis requests

### 2. Data Models

The application includes several data models to represent the sentiment data:

- `TickerSentiment`: Represents sentiment data for a specific ticker
- `SentimentEvent`: Represents a sentiment analysis event
- `QueryParams`: Parameters for filtering sentiment queries
- `EventSource`: Configuration for data sources
- `MessageStats`: Statistics about message processing

### 3. State Management

The app uses the Provider pattern for state management:

- `DashboardProvider`: Manages dashboard data and refresh logic
- `AuthProvider`: Handles authentication state
- `SettingsProvider`: Manages app settings and preferences

### 4. Screens

The app includes several main screens:

- `SplashScreen`: Initial loading screen
- `LoginScreen`: Authentication screen
- `HomeScreen`: Main dashboard with tabs for different functionality

### 5. Widgets

Custom widgets for visualizing sentiment data:

- `SystemOverviewCards`: System status overview
- `DataFlowChart`: Real-time data flow visualization 
- `RecentEventsList`: List of recent sentiment events
- `TopSentimentsChart`: Chart showing top sentiment data

## Features Implemented

1. **Dashboard Overview**: System metrics and container status
2. **Data Flow Visualization**: Real-time event processing visualization
3. **Sentiment Analysis**: Top ticker sentiment charts
4. **Event Explorer**: List and details of sentiment events
5. **Authentication**: Basic login/logout functionality
6. **Theme Support**: Light and dark theme support
7. **Settings Management**: User preferences for refresh interval and notifications

## API Endpoints Used

The app communicates with these backend API endpoints:

- `GET /sentiment/ticker/{ticker}`: Get sentiment for a specific ticker
- `GET /sentiment/tickers`: Get list of available tickers
- `GET /sentiment/top`: Get top tickers by sentiment score
- `POST /sentiment/query`: Query sentiment events with filters
- `GET /sentiment/metadata`: Get metadata for UI filtering
- `POST /sentiment/analyze`: Analyze sentiment of custom text

## Dependencies

Key dependencies include:

- **State Management**: provider
- **HTTP Client**: dio, http
- **Charting**: fl_chart
- **Storage**: shared_preferences, flutter_secure_storage
- **Utilities**: intl, json_annotation, path_provider
- **Serialization**: json_serializable, build_runner

## Getting Started

1. Ensure Flutter SDK is installed (v3.3.0+)
2. Clone the repository
3. Run `flutter pub get` to install dependencies
4. Run `flutter pub run build_runner build` to generate model classes
5. Create `.env` in assets/config with API configuration
6. Run `flutter run` to start the application

## Comparison with Streamlit Dashboard

The Flutter dashboard improves upon the Streamlit version in several ways:

1. **Performance**: Native app performance vs. web-based Streamlit
2. **Offline Support**: Ability to cache data for offline viewing
3. **Authentication**: Built-in secure authentication
4. **Customization**: More flexible UI customization
5. **Mobile Support**: Responsive design for mobile and desktop
6. **Push Notifications**: Support for system notifications (future enhancement)
7. **Advanced Filtering**: More powerful data filtering capabilities