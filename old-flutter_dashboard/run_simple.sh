#!/bin/bash
# Improved diagnostic script with logging for Flutter dashboard

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

LOG_FILE="flutter_dashboard.log"

# Function to log messages with timestamp
log_message() {
  local message="$1"
  local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
  echo -e "${timestamp} - $message" | tee -a "$LOG_FILE"
}

# Cleanup previous log file
rm -f "$LOG_FILE"
log_message "${YELLOW}Starting Flutter Dashboard Diagnostic Mode${NC}"

# Check Flutter version and environment
log_message "${BLUE}Checking Flutter environment...${NC}"
flutter --version | tee -a "$LOG_FILE"
log_message "${BLUE}Checking connected devices...${NC}"
flutter devices | tee -a "$LOG_FILE"

# Force demo mode to ensure data appears
log_message "${BLUE}Setting up config files...${NC}"
mkdir -p lib/utils
cat > lib/utils/app_config.dart << 'EOF'
// lib/utils/app_config.dart

const bool isDemoMode = true; // Force demo mode for testing

// Enable diagnostic logging
const bool enableDiagnosticLogging = true;
// You might later configure this using build flavors or environment variables
EOF

# Set up a test wrapper
log_message "${BLUE}Creating test launcher that logs UI creation...${NC}"
mkdir -p lib/logging
cat > lib/logging/app_logger.dart << 'EOF'
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../utils/app_config.dart';

class AppLogger {
  static void log(String message) {
    if (enableDiagnosticLogging) {
      debugPrint('🔍 APP-LOG: $message');
    }
  }

  static void logWidget(String widgetName) {
    log('Widget built: $widgetName');
  }

  static void logError(String message, [dynamic error]) {
    debugPrint('❌ APP-ERROR: $message ${error != null ? '- $error' : ''}');
  }

  static void logNavigation(String route) {
    log('Navigation to: $route');
  }
  
  static void logProvider(String providerName, String action) {
    log('Provider $providerName: $action');
  }
}
EOF

# Create a diagnostic main app
cat > lib/main.dart << 'EOF'
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'providers/dashboard_provider.dart';
import 'providers/settings_provider.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/splash_screen.dart';
import 'constants/app_theme.dart';
import 'logging/app_logger.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Add error handling
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    AppLogger.logError('Flutter Error: ${details.exception}', details.stack);
  };
  
  // Log app startup
  AppLogger.log('Application starting...');
  
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) {
          AppLogger.log('Creating AuthProvider');
          return AuthProvider();
        }),
        ChangeNotifierProvider(create: (_) {
          AppLogger.log('Creating DashboardProvider');
          return DashboardProvider();
        }),
        ChangeNotifierProvider(create: (_) {
          AppLogger.log('Creating SettingsProvider');
          return SettingsProvider();
        }),
      ],
      child: const RTSentimentApp(),
    ),
  );
}

class RTSentimentApp extends StatelessWidget {
  const RTSentimentApp({super.key});

  @override
  Widget build(BuildContext context) {
    AppLogger.logWidget('RTSentimentApp');
    
    return MaterialApp(
      title: 'RT Sentiment Dashboard',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: Provider.of<SettingsProvider>(context).themeMode,
      debugShowCheckedModeBanner: true, // Show debug banner for diagnostics
      home: Builder(
        builder: (context) {
          AppLogger.log('Building Home Screen directly');
          return const HomeScreen();
        }
      ),
      builder: (context, child) {
        // Add global error handling and logging wrapper
        AppLogger.log('Application UI tree building');
        return Column(
          children: [
            Expanded(
              child: child ?? const SizedBox.shrink(),
            ),
            // Debug banner for diagnostic mode (visible only in diagnostics mode)
            Container(
              color: Colors.red,
              width: double.infinity,
              padding: const EdgeInsets.all(8),
              child: const Text(
                'DIAGNOSTIC MODE',
                style: TextStyle(color: Colors.white),
                textAlign: TextAlign.center,
              ),
            ),
          ],
        );
      },
    );
  }
}
EOF

# Update HomeScreen to have additional logging
log_message "${BLUE}Creating basic test widget to verify rendering...${NC}"
mkdir -p lib/test_widgets
cat > lib/test_widgets/test_card.dart << 'EOF'
import 'package:flutter/material.dart';
import '../logging/app_logger.dart';

class TestCard extends StatelessWidget {
  final String title;
  final Color color;

  const TestCard({
    Key? key, 
    required this.title,
    this.color = Colors.blue,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    AppLogger.logWidget('TestCard: $title');
    
    return Card(
      elevation: 4,
      color: color,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'This is a test card to verify UI rendering is working.',
              style: TextStyle(color: Colors.white),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                AppLogger.log('Button pressed in TestCard: $title');
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Button pressed in $title')),
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: color,
              ),
              child: const Text('Test Button'),
            ),
          ],
        ),
      ),
    );
  }
}
EOF

# Create an alternate simple home screen for testing
cat > lib/screens/home_screen.dart << 'EOF'
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/dashboard_provider.dart';
import '../providers/auth_provider.dart';
import '../providers/settings_provider.dart';
import '../logging/app_logger.dart';
import '../test_widgets/test_card.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  String _diagnosticMessage = 'Initializing...';

  @override
  void initState() {
    super.initState();
    AppLogger.log('HomeScreen - initState called');
    
    // Use post-frame callback to avoid setState during build
    WidgetsBinding.instance.addPostFrameCallback((_) {
      AppLogger.log('HomeScreen - post-frame callback running');
      _loadDashboardData();
    });
  }

  Future<void> _loadDashboardData() async {
    AppLogger.log('HomeScreen - loadDashboardData called');
    try {
      setState(() {
        _diagnosticMessage = 'Loading data...';
      });
      
      final dashboardProvider = Provider.of<DashboardProvider>(context, listen: false);
      await dashboardProvider.loadData();
      
      if (mounted) {
        setState(() {
          _diagnosticMessage = 'Data loaded successfully';
        });
      }
    } catch (e) {
      AppLogger.logError('Error loading dashboard data', e);
      if (mounted) {
        setState(() {
          _diagnosticMessage = 'Error loading data: $e';
        });
      }
    }
  }

  void _switchTab(int index) {
    AppLogger.log('HomeScreen - switching to tab $index');
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    AppLogger.logWidget('HomeScreen - build method');
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('RT Sentiment Dashboard (Test Mode)'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDashboardData,
            tooltip: 'Refresh Data',
          ),
          IconButton(
            icon: Icon(
              Provider.of<SettingsProvider>(context).themeMode == ThemeMode.dark
                  ? Icons.light_mode
                  : Icons.dark_mode,
            ),
            onPressed: () {
              AppLogger.log('Toggling theme');
              final settings = Provider.of<SettingsProvider>(context, listen: false);
              settings.toggleTheme();
            },
            tooltip: 'Toggle Theme',
          ),
        ],
      ),
      body: Column(
        children: [
          // Diagnostic banner
          Container(
            color: Colors.amber.shade200,
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'DIAGNOSTIC INFORMATION',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text('Status: $_diagnosticMessage'),
                Text('Selected Tab: $_selectedIndex'),
                Consumer<DashboardProvider>(
                  builder: (context, dashboardProvider, _) {
                    return Text(
                      'Provider loaded: ${!dashboardProvider.isLoading ? "Yes" : "No"}',
                    );
                  },
                ),
              ],
            ),
          ),
          
          // Simple test content
          Expanded(
            child: IndexedStack(
              index: _selectedIndex,
              children: [
                // Tab 1: Test cards
                SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      const TestCard(
                        title: 'Main Dashboard Card',
                        color: Colors.blue,
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Expanded(
                            child: TestCard(
                              title: 'Positive Sentiment',
                              color: Colors.green.shade700,
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: TestCard(
                              title: 'Negative Sentiment',
                              color: Colors.red.shade700,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      TestCard(
                        title: 'Recent Activity',
                        color: Colors.purple.shade700,
                      ),
                    ],
                  ),
                ),
                
                // Tab 2: Provider Data
                Consumer<DashboardProvider>(
                  builder: (context, provider, _) {
                    return SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Provider Data',
                            style: TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 16),
                          Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Loading state: ${provider.isLoading}'),
                                  Text('Top positive: ${provider.topPositive.length} items'),
                                  Text('Top negative: ${provider.topNegative.length} items'),
                                  Text('Recent events: ${provider.recentEvents.length} items'),
                                  Text('Data flow points: ${provider.dataFlowPoints.length} items'),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
                
                // Tab 3: System Information
                SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'System Information',
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Platform: ${Theme.of(context).platform}'),
                              const Text('App Version: 1.0.0'),
                              Text('Theme Mode: ${Theme.of(context).brightness}'),
                              Consumer<SettingsProvider>(
                                builder: (context, settings, _) {
                                  return Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('Auto Refresh: ${settings.autoRefresh}'),
                                      Text('Refresh Interval: ${settings.refreshInterval} seconds'),
                                      Text('API URL: ${settings.apiUrl}'),
                                    ],
                                  );
                                },
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _switchTab,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Test Cards',
          ),
          NavigationDestination(
            icon: Icon(Icons.data_usage_outlined),
            selectedIcon: Icon(Icons.data_usage),
            label: 'Provider Data',
          ),
          NavigationDestination(
            icon: Icon(Icons.info_outline),
            selectedIcon: Icon(Icons.info),
            label: 'System Info',
          ),
        ],
      ),
    );
  }
}
EOF

# Update dashboard provider to include more logging
log_message "${BLUE}Updating dashboard provider with logging...${NC}"
cat > lib/providers/dashboard_provider.dart << 'EOF'
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:math';
import '../api/api_client.dart';
import '../models/ticker_sentiment.dart';
import '../models/sentiment_event.dart';
import '../models/query_params.dart';
import '../models/event_source.dart';
import '../utils/app_config.dart';
import '../logging/app_logger.dart';

class DashboardProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  
  // Dashboard data
  List<TickerSentiment> _topPositive = [];
  List<TickerSentiment> _topNegative = [];
  List<SentimentEvent> _recentEvents = [];
  List<String> _availableTickers = [];
  List<EventSource> _eventSources = [];
  List<Map<String, dynamic>> _dataFlowPoints = [];
  
  // System stats
  int _sourceCount = 0;
  String _sourceNames = '';
  int _eventsProcessed = 0;
  int _modelCount = 1;
  String _primaryModel = 'FinBERT';
  String _systemStatus = 'Healthy';
  String _uptime = '3h 24m';
  
  // Loading states
  bool _isLoading = false;
  bool _isLoadingEvents = false;
  bool _isLoadingDataFlow = false;
  
  // Getters
  List<TickerSentiment> get topPositive => _topPositive;
  List<TickerSentiment> get topNegative => _topNegative;
  List<SentimentEvent> get recentEvents => _recentEvents;
  List<String> get availableTickers => _availableTickers;
  List<EventSource> get eventSources => _eventSources;
  List<Map<String, dynamic>> get dataFlowPoints => _dataFlowPoints;
  
  int get sourceCount => _sourceCount;
  String get sourceNames => _sourceNames;
  int get eventsProcessed => _eventsProcessed;
  int get modelCount => _modelCount;
  String get primaryModel => _primaryModel;
  String get systemStatus => _systemStatus;
  String get uptime => _uptime;
  
  bool get isLoading => _isLoading;
  bool get isLoadingEvents => _isLoadingEvents;
  bool get isLoadingDataFlow => _isLoadingDataFlow;
  
  // Constructor with logging
  DashboardProvider() {
    AppLogger.logProvider('DashboardProvider', 'initialized');
  }
  
  // Load all dashboard data
  Future<void> loadData() async {
    AppLogger.logProvider('DashboardProvider', 'loadData() called');
    _isLoading = true;
    notifyListeners();
    
    try {
      AppLogger.log('DashboardProvider.loadData: isDemoMode=$isDemoMode, kIsWeb=$kIsWeb');
      
      // Always use sample data for now to ensure content appears
      AppLogger.log('DashboardProvider.loadData: Loading sample data');
      _loadSampleSentimentData();
      _loadSampleEventsData();
      _availableTickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA'];
      _loadSampleEventSources();
      _loadSampleSystemStats();
      _loadSampleDataFlow();
      
      AppLogger.log('DashboardProvider.loadData: Sample data loaded successfully');
    } catch (e) {
      AppLogger.logError('Error loading dashboard data', e);
    } finally {
      _isLoading = false;
      notifyListeners();
      AppLogger.log('DashboardProvider.loadData: Completed, notified listeners');
    }
  }
  
  // Load sample event sources
  void _loadSampleEventSources() {
    AppLogger.log('DashboardProvider: Loading sample event sources');
    _eventSources = [
      EventSource(
        name: 'news_scrapers',
        isActive: true,
        targets: ['financial_news', 'market_updates', 'earnings_reports'],
        outputTopic: 'news-events-high',
        frequency: '5min',
      ),
      EventSource(
        name: 'reddit_scrapers',
        isActive: true,
        targets: ['wallstreetbets', 'investing', 'stocks'],
        outputTopic: 'news-events-standard',
        frequency: '10min',
      ),
      EventSource(
        name: 'twitter_scrapers',
        isActive: false,
        targets: ['\$TICKER', 'investing', 'markets'],
        outputTopic: 'news-events-standard',
        frequency: '2min',
      ),
      EventSource(
        name: 'sec_filings',
        isActive: true,
        targets: ['8-K', '10-Q', '10-K'],
        outputTopic: 'news-events-high',
        frequency: '15min',
      ),
    ];
    
    _sourceCount = _eventSources.where((s) => s.isActive).length;
    _sourceNames = _eventSources
        .where((s) => s.isActive)
        .map((s) => s.name.replaceAll('_scrapers', '').replaceAll('_', ' '))
        .join(', ');
  }
  
  // Load sample system stats
  void _loadSampleSystemStats() {
    AppLogger.log('DashboardProvider: Loading sample system stats');
    _eventsProcessed = 128;
    _modelCount = 1;
    _primaryModel = 'FinBERT';
    _systemStatus = 'Healthy';
    _uptime = '3h 24m';
  }
  
  // Create sample data when API is not available
  void _loadSampleSentimentData() {
    AppLogger.log('DashboardProvider: Loading sample sentiment data');
    _topPositive = [
      TickerSentiment(
        ticker: 'AAPL',
        sentiment: 'positive',
        score: 0.85,
        weight: 1.5,
        count: 25,
        model: 'finbert',
      ),
      TickerSentiment(
        ticker: 'MSFT',
        sentiment: 'positive',
        score: 0.78,
        weight: 1.2,
        count: 18,
        model: 'finbert',
      ),
      TickerSentiment(
        ticker: 'GOOGL',
        sentiment: 'positive',
        score: 0.72,
        weight: 1.0,
        count: 15,
        model: 'finbert',
      ),
      TickerSentiment(
        ticker: 'AMZN',
        sentiment: 'positive',
        score: 0.65,
        weight: 1.1,
        count: 20,
        model: 'finbert',
      ),
      TickerSentiment(
        ticker: 'NVDA',
        sentiment: 'positive',
        score: 0.58,
        weight: 1.3,
        count: 22,
        model: 'finbert',
      ),
    ];
    
    _topNegative = [
      TickerSentiment(
        ticker: 'META',
        sentiment: 'negative',
        score: -0.45,
        weight: 0.9,
        count: 12,
        model: 'finbert',
      ),
      TickerSentiment(
        ticker: 'NFLX',
        sentiment: 'negative',
        score: -0.52,
        weight: 1.0,
        count: 8,
        model: 'finbert',
      ),
      TickerSentiment(
        ticker: 'TSLA',
        sentiment: 'negative',
        score: -0.65,
        weight: 1.4,
        count: 30,
        model: 'finbert',
      ),
      TickerSentiment(
        ticker: 'BABA',
        sentiment: 'negative',
        score: -0.72,
        weight: 0.8,
        count: 10,
        model: 'finbert',
      ),
      TickerSentiment(
        ticker: 'GME',
        sentiment: 'negative',
        score: -0.88,
        weight: 1.1,
        count: 15,
        model: 'finbert',
      ),
    ];
    
    AppLogger.log('DashboardProvider: Loaded ${_topPositive.length} positive and ${_topNegative.length} negative sentiments');
  }
  
  void _loadSampleEventsData() {
    AppLogger.log('DashboardProvider: Loading sample events data');
    final now = DateTime.now();
    
    _recentEvents = [
      SentimentEvent(
        id: 1001,
        eventId: 'evt_001',
        timestamp: now.subtract(const Duration(minutes: 5)),
        source: 'news',
        priority: 'high',
        model: 'finbert',
        sentimentScore: 0.85,
        sentimentLabel: 'positive',
      ),
      SentimentEvent(
        id: 1002,
        eventId: 'evt_002',
        timestamp: now.subtract(const Duration(minutes: 12)),
        source: 'reddit',
        priority: 'standard',
        model: 'finbert',
        sentimentScore: -0.45,
        sentimentLabel: 'negative',
      ),
      SentimentEvent(
        id: 1003,
        eventId: 'evt_003',
        timestamp: now.subtract(const Duration(minutes: 18)),
        source: 'twitter',
        priority: 'standard',
        model: 'finbert',
        sentimentScore: 0.12,
        sentimentLabel: 'neutral',
      ),
      SentimentEvent(
        id: 1004,
        eventId: 'evt_004',
        timestamp: now.subtract(const Duration(minutes: 25)),
        source: 'sec',
        priority: 'high',
        model: 'finbert',
        sentimentScore: -0.78,
        sentimentLabel: 'negative',
      ),
      SentimentEvent(
        id: 1005,
        eventId: 'evt_005',
        timestamp: now.subtract(const Duration(minutes: 35)),
        source: 'news',
        priority: 'high',
        model: 'finbert',
        sentimentScore: 0.91,
        sentimentLabel: 'positive',
      ),
    ];
    
    AppLogger.log('DashboardProvider: Loaded ${_recentEvents.length} sample events');
  }
  
  // Load data flow visualization data
  void _loadSampleDataFlow() {
    AppLogger.log('DashboardProvider: Loading sample data flow');
    // Generate sample data points for the last 30 minutes
    final now = DateTime.now();
    _dataFlowPoints = List.generate(30, (index) {
      final timestamp = now.subtract(Duration(minutes: 30 - index));
      return {
        'timestamp': timestamp,
        'high_priority': _generateRandomValue(index, 0, 3),
        'standard_priority': _generateRandomValue(index, 2, 5),
        'results': _generateRandomValue(index - 1, 1, 7),
      };
    });
    
    AppLogger.log('DashboardProvider: Loaded ${_dataFlowPoints.length} data flow points');
  }
  
  // Helper for data flow visualization
  double _generateRandomValue(int index, int min, int max) {
    if (index < 0) return 0;
    
    // Create a pattern that looks somewhat realistic
    final base = min + (index % (max - min));
    return base + (index % 3) * 0.5;
  }
}
EOF

# Create a minimal application to test the basics
log_message "${BLUE}Creating ultra minimal test harness...${NC}"
cat > lib/minimal_app.dart << 'EOF'
import 'package:flutter/material.dart';

// This is an extremely minimal Flutter app used only for testing rendering
class MinimalApp extends StatelessWidget {
  const MinimalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Minimal Test App',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: const MinimalTestScreen(),
    );
  }
}

class MinimalTestScreen extends StatelessWidget {
  const MinimalTestScreen({super.key});

  @override
  Widget build(BuildContext context) {
    print('Building MinimalTestScreen');
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Minimal UI Test'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'This is a minimal test application',
              style: TextStyle(fontSize: 18),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () {
                print('Button pressed!');
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Button pressed!')),
                );
              },
              child: const Text('Test Button'),
            ),
          ],
        ),
      ),
    );
  }
}
EOF

# Create a test main.dart that allows switching between implementations
cat > lib/test_harness.dart << 'EOF'
import 'package:flutter/material.dart';
import 'main.dart' as main_app;
import 'minimal_app.dart';

void main() {
  runApp(const TestHarnessApp());
}

class TestHarnessApp extends StatefulWidget {
  const TestHarnessApp({super.key});

  @override
  State<TestHarnessApp> createState() => _TestHarnessAppState();
}

class _TestHarnessAppState extends State<TestHarnessApp> {
  bool _useMinimalApp = true;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'UI Test Harness',
      home: Scaffold(
        body: Column(
          children: [
            // Header with test controls
            Container(
              color: Colors.black,
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Text(
                    'TEST HARNESS',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Switch(
                    value: _useMinimalApp,
                    onChanged: (value) {
                      setState(() {
                        _useMinimalApp = value;
                      });
                    },
                  ),
                  Text(
                    _useMinimalApp ? 'Minimal App' : 'Full App',
                    style: const TextStyle(color: Colors.white),
                  ),
                ],
              ),
            ),
            
            // App container
            Expanded(
              child: _useMinimalApp
                  ? const MinimalApp()
                  : Builder(
                      builder: (context) {
                        try {
                          main_app.main();
                          // This won't be reached due to runApp, but prevents compile errors
                          return const SizedBox.shrink();
                        } catch (e) {
                          return Center(
                            child: Text('Error: $e'),
                          );
                        }
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
EOF

# Run a simple series of diagnostic tests
log_message "${BLUE}Running pre-flight diagnostic checks...${NC}"

# Check Flutter doctor
flutter doctor -v | tee -a "$LOG_FILE"

# Check key dependencies
log_message "${BLUE}Checking key packages...${NC}"
flutter pub get | tee -a "$LOG_FILE"

# Try to run the minimal test app
log_message "${GREEN}Running minimal Flutter test app...${NC}"
export FLUTTER_WEB_PORT=9333
flutter run -d chrome lib/minimal_app.dart &

# Store the PID
FLUTTER_PID=$!

# Give it some time to start
sleep 10

# Let user know about the diagnostic app
log_message "${YELLOW}Minimal app is running on port 9333. Please check http://localhost:9333 to verify basic Flutter rendering works.${NC}"
log_message "${YELLOW}You can stop this app by pressing Ctrl+C and then run the full diagnostic app.${NC}"

# Wait for user input
read -p "Press Enter to continue to main diagnostic app or Ctrl+C to exit..."

# Kill minimal app if it's still running
kill $FLUTTER_PID 2>/dev/null

# Run the main diagnostic app
log_message "${GREEN}Running full diagnostic app on port 9100...${NC}"
flutter run -d chrome lib/main.dart --web-port=9100

# Final notes
log_message "${YELLOW}Diagnostic run completed. Check logs in $LOG_FILE${NC}"