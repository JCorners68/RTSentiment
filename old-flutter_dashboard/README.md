# RT Sentiment Dashboard - Flutter Application

A Flutter-based dashboard application for the Real-Time Sentiment Analysis system.

## Quick Start

Use one of the following scripts to run the dashboard:

```bash
# Run with real API data (Live Mode)
./run_live.sh

# Run in demo mode (sample data only)
./run_demo.sh

# Fix code issues and run on Linux desktop
./fix_code.sh

# Quick run with existing configuration (fastest)
./run_quick.sh
```

## Features

1. **Dashboard Overview**: System metrics and performance indicators
2. **Data Flow Visualization**: Real-time event processing visualization
3. **Sentiment Analysis Charts**: Visualizations of ticker sentiment
4. **Event Explorer**: Detailed event information
5. **Advanced Query Builder**: Custom data filtering options

## Mode Selection

The dashboard can run in two modes:

### Live Mode
Connects to the backend API to fetch real data, with fallback to sample data if API calls fail.

```bash
./run_live.sh
```

### Demo Mode
Uses sample data only, no API connections required. Great for showcasing the UI without a backend.

```bash
./run_demo.sh
```

## App Configuration

The dashboard behavior is controlled by the app configuration in `lib/utils/app_config.dart`:

```dart
const bool isDemoMode = false; // Set to true for demo, false for live
```

This allows switching between demo and live mode without script changes.

## For Developers

See [Documentation/FLUTTER_SETUP.md](../Documentation/FLUTTER_SETUP.md) for detailed setup instructions and advanced configuration options.

## Login Credentials (Demo Mode)

- Username: `demo`
- Password: `password`