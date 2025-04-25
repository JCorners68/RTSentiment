# Streamlit to Flutter Migration Guide

**Migration Status**: Complete  
**Date**: April 23, 2025  
**Author**: Development Team

## Overview

The Senti platform has migrated from the original Streamlit-based dashboard to a Flutter/Dart application for the Real-Time Sentiment Analysis project. This document outlines the migration process, reasons for the change, and provides guidance for developers working on the project.

The migration improves performance, enhances UI/UX, and provides a more maintainable and scalable architecture.

## Migration Benefits

1. **Performance**: Flutter offers superior performance compared to Streamlit for complex dashboards
2. **Cross-platform**: The Flutter app can be deployed on web, mobile, and desktop platforms
3. **Enhanced UI/UX**: Material Design components and custom widgets provide a richer user experience
4. **State Management**: Provider pattern ensures clean and maintainable state management
5. **Offline Support**: Potential for offline caching and operation
6. **Code Organization**: Better separation of concerns with clear architecture

## Architecture

The Flutter dashboard follows a layered architecture:

1. **Presentation Layer**: 
   - Screens: High-level UI components representing whole screens
   - Widgets: Reusable UI components
   - Theme: Consistent styling across the application

2. **State Management Layer**: 
   - Provider pattern for reactive state management
   - Separation of business logic from UI

3. **Data Layer**:
   - API Client: Communication with backend services
   - Models: Strongly typed data structures with JSON serialization
   - Repository Pattern: Abstract data access

4. **Services Layer**:
   - Authentication
   - Local storage/caching
   - Logging

## Key Components

### Models

The core data models represent the domain objects:
- `TickerSentiment`: Sentiment data for financial tickers
- `SentimentEvent`: Individual sentiment analysis events
- `EventSource`: Data sources configuration
- `MessageStats`: System statistics and performance metrics
- `QueryParams`: Parameters for data filtering

### State Management

State management uses the Provider pattern:
- `DashboardProvider`: Main dashboard state and data management
- `AuthProvider`: Authentication state
- `SettingsProvider`: User preferences and settings

### UI Components

Custom Flutter widgets provide the UI foundation:
- `TopSentimentsChart`: Bar charts for positive/negative sentiment
- `DataFlowChart`: Line chart showing real-time data flow
- `SystemOverviewCard`: System metrics cards
- `RecentEventsList`: List view for sentiment events

## API Integration

The application communicates with the existing backend API:
- RESTful API client using HTTP package
- JSON serialization/deserialization
- Error handling with graceful fallbacks
- Authentication token management

## Testing Strategy

The Flutter app includes three types of tests:
- Unit tests for business logic and providers
- Widget tests for UI components
- Integration tests for end-to-end workflows

## Deployment

The Flutter application can be deployed to multiple platforms:
- Web: Compiled to JavaScript for web deployment
- Android/iOS: Native app deployment
- Desktop: Windows, macOS, Linux installation options

## Migration Steps

1. **Project Structure Setup**
   - Created Flutter project structure
   - Configured build system and dependencies

2. **Data Models**
   - Implemented data models with JSON serialization
   - Mapped backend API response structures

3. **API Client**
   - Developed HTTP client for backend communication
   - Implemented error handling and authentication

4. **State Management**
   - Set up Provider pattern for state management
   - Created providers for dashboard, auth, and settings

5. **UI Components**
   - Developed reusable widgets for common UI elements
   - Implemented charts, cards, and list components

6. **Screens**
   - Created main application screens
   - Implemented navigation and routing

7. **Testing**
   - Set up testing framework
   - Implemented test cases

## Future Enhancements

1. WebSocket integration for real-time updates
2. Advanced data visualization options
3. Offline data caching
4. Push notifications for important events
5. User customization options
6. Mobile-specific optimizations

## Development Workflow

### Local Development with Flutter

1. Set up Flutter development environment:
   ```bash
   # Check Flutter installation
   flutter --version
   
   # Navigate to Flutter project
   cd senti
   
   # Get dependencies
   flutter pub get
   ```

2. Run the Flutter app:
   ```bash
   # For web
   flutter run -d chrome
   
   # For desktop (Linux)
   flutter run -d linux
   
   # For Android
   flutter run -d <android-device-id>
   ```

### Testing with Backend Services

To test the Flutter UI with the backend services:

1. Build the Flutter web app:
   ```bash
   cd senti
   flutter build web
   ```

2. Start the backend services with Docker:
   ```bash
   cd ..  # Back to project root
   docker-compose up -d api sentiment-analysis redis postgres kafka
   ```

3. Start the Flutter web server container:
   ```bash
   docker-compose up -d flutter-web
   ```

4. Access the application at http://localhost:8888

## Legacy Streamlit Dashboard

The Streamlit dashboard has been deprecated but is retained for reference in the `/old_streamlit_dashboard` directory. A `DEPRECATED.md` file has been added to document its status.

**Note**: The Streamlit dashboard is scheduled for removal in October 2025.