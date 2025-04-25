#!/bin/bash
# Start web server for the minimal app

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting Flutter Web Server${NC}"

# Create a minimal app if it doesn't exist
if [ ! -f "lib/minimal/main.dart" ]; then
  mkdir -p lib/minimal
  cat > lib/minimal/main.dart << 'EOF'
import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RT Sentiment',
      theme: ThemeData(
        primarySwatch: Colors.green,
      ),
      home: const DashboardPage(),
    );
  }
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  int _selectedIndex = 0;
  final List<Map<String, dynamic>> _positiveData = [
    {'ticker': 'AAPL', 'score': 0.85},
    {'ticker': 'MSFT', 'score': 0.78},
    {'ticker': 'GOOGL', 'score': 0.72},
  ];
  
  final List<Map<String, dynamic>> _negativeData = [
    {'ticker': 'META', 'score': -0.45},
    {'ticker': 'TSLA', 'score': -0.65},
    {'ticker': 'GME', 'score': -0.88},
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('RT Sentiment Dashboard'),
      ),
      body: IndexedStack(
        index: _selectedIndex,
        children: [
          // Dashboard
          ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Text('Top Positive Sentiment', 
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              ..._buildSentimentCards(_positiveData, true),
              
              const SizedBox(height: 24),
              
              const Text('Top Negative Sentiment', 
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              ..._buildSentimentCards(_negativeData, false),
            ],
          ),
          
          // Data Flow
          const Center(child: Text('Data Flow Page')),
          
          // Explorer
          const Center(child: Text('Explorer Page')),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: _onItemTapped,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.show_chart),
            label: 'Data Flow',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.explore),
            label: 'Explorer',
          ),
        ],
      ),
    );
  }
  
  List<Widget> _buildSentimentCards(List<Map<String, dynamic>> data, bool isPositive) {
    final color = isPositive ? Colors.green : Colors.red;
    return data.map((item) {
      final score = item['score'].abs();
      return Card(
        margin: const EdgeInsets.only(bottom: 8),
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    item['ticker'],
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                    ),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '${isPositive ? "+" : ""}${item['score'].toStringAsFixed(2)}',
                      style: TextStyle(
                        color: color,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              LinearProgressIndicator(
                value: score,
                backgroundColor: Colors.grey.shade200,
                valueColor: AlwaysStoppedAnimation<Color>(color),
              ),
            ],
          ),
        ),
      );
    }).toList();
  }
}
EOF
  echo -e "${GREEN}Created minimal app at lib/minimal/main.dart${NC}"
else
  echo -e "${BLUE}Using existing minimal app${NC}"
fi

# Copy web wrapper if it exists
if [ -f "web_wrapper.html" ]; then
  cp web_wrapper.html .
  echo -e "${GREEN}Copied web wrapper${NC}"
fi

# Start the web server
echo -e "${GREEN}Starting Flutter web server on port 8090...${NC}"
echo -e "${YELLOW}Please try these access methods:${NC}"
echo -e "1. ${BLUE}http://localhost:8090${NC} - Direct access to the Flutter app"
echo -e "2. Open ${BLUE}web_wrapper.html${NC} in your browser - Wrapper with fallback"
echo -e "3. View the app in Chrome (should open automatically)"
echo -e "\n${RED}Press Ctrl+C to stop the server${NC}\n"

flutter run lib/minimal/main.dart -d web-server --web-port=8090