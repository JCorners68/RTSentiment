#!/bin/bash
# Super simple demo app with guaranteed demo mode

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Creating Flutter Dashboard Demo App${NC}"

# Create the demo app
mkdir -p lib/basic_demo/models
mkdir -p lib/basic_demo/widgets

# Create model class
cat > lib/basic_demo/models/sentiment.dart << 'EOF'
class Sentiment {
  final String ticker;
  final double score;
  final String label;
  
  Sentiment({
    required this.ticker,
    required this.score,
    required this.label,
  });
}
EOF

# Create a simple dashboard
cat > lib/basic_demo/dashboard.dart << 'EOF'
import 'package:flutter/material.dart';
import 'models/sentiment.dart';
import 'widgets/sentiment_card.dart';

void main() {
  print("Starting Dashboard Demo");
  runApp(const DashboardDemo());
}

class DashboardDemo extends StatelessWidget {
  const DashboardDemo({super.key});

  @override
  Widget build(BuildContext context) {
    print("Building DashboardDemo");
    return MaterialApp(
      title: 'RT Sentiment Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      home: const DemoScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class DemoScreen extends StatefulWidget {
  const DemoScreen({super.key});

  @override
  State<DemoScreen> createState() => _DemoScreenState();
}

class _DemoScreenState extends State<DemoScreen> {
  final List<Sentiment> _positiveData = [
    Sentiment(ticker: "AAPL", score: 0.85, label: "positive"),
    Sentiment(ticker: "MSFT", score: 0.78, label: "positive"),
    Sentiment(ticker: "GOOGL", score: 0.72, label: "positive"),
    Sentiment(ticker: "AMZN", score: 0.65, label: "positive"),
  ];
  
  final List<Sentiment> _negativeData = [
    Sentiment(ticker: "META", score: -0.45, label: "negative"),
    Sentiment(ticker: "NFLX", score: -0.52, label: "negative"),
    Sentiment(ticker: "TSLA", score: -0.65, label: "negative"),
    Sentiment(ticker: "GME", score: -0.88, label: "negative"),
  ];
  
  bool _loading = false;
  
  @override
  Widget build(BuildContext context) {
    print("Building DemoScreen");
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.green,
        title: const Text('RT Sentiment Demo', style: TextStyle(color: Colors.white)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            onPressed: () {
              setState(() {
                _loading = true;
              });
              
              // Simulate loading
              Future.delayed(const Duration(seconds: 1), () {
                if (mounted) {
                  setState(() {
                    _loading = false;
                  });
                  
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Data refreshed')),
                  );
                }
              });
            },
          ),
        ],
      ),
      body: _loading 
        ? const Center(child: CircularProgressIndicator())
        : SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Welcome to RT Sentiment Dashboard',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                const Text(
                  'DEMO MODE',
                  style: TextStyle(
                    fontSize: 16, 
                    color: Colors.green,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                
                const SizedBox(height: 24),
                
                const Text(
                  'Top Positive Sentiment',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                
                ...List.generate(_positiveData.length, (index) {
                  return SentimentCard(
                    sentiment: _positiveData[index],
                    isPositive: true,
                  );
                }),
                
                const SizedBox(height: 24),
                
                const Text(
                  'Top Negative Sentiment',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                
                ...List.generate(_negativeData.length, (index) {
                  return SentimentCard(
                    sentiment: _negativeData[index],
                    isPositive: false,
                  );
                }),
              ],
            ),
          ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: 0,
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
}

// Don't use a custom class to avoid const issues
// Just create the items directly in the BottomNavigationBar
EOF

# Create simple widget
cat > lib/basic_demo/widgets/sentiment_card.dart << 'EOF'
import 'package:flutter/material.dart';
import '../models/sentiment.dart';

class SentimentCard extends StatelessWidget {
  final Sentiment sentiment;
  final bool isPositive;
  
  const SentimentCard({
    Key? key,
    required this.sentiment,
    required this.isPositive,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    final color = isPositive ? Colors.green : Colors.red;
    final scoreAbs = sentiment.score.abs();
    
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
                  sentiment.ticker,
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
                    '${isPositive ? "+" : ""}${sentiment.score.toStringAsFixed(2)}',
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
              value: scoreAbs,
              backgroundColor: Colors.grey.shade200,
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ],
        ),
      ),
    );
  }
}
EOF

# Make it runnable
chmod +x basic_demo.sh

# Launch the app
echo -e "${GREEN}Launching Basic Demo on Chrome...${NC}"
echo -e "${BLUE}This is a minimal implementation with guaranteed demo mode${NC}"
flutter run -d chrome --web-port=9100 lib/basic_demo/dashboard.dart