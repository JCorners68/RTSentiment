#!/bin/bash
# Web server mode test script for Flutter dashboard

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running Web Server Flutter Test${NC}"

# Create a very minimal flutter app to test rendering
mkdir -p lib/test
cat > lib/test/server_test.dart << 'EOF'
import 'package:flutter/material.dart';

void main() {
  // Print startup message
  print('\n\n==== WEB SERVER TEST APP STARTING ====\n');
  runApp(const WebServerTestApp());
}

class WebServerTestApp extends StatelessWidget {
  const WebServerTestApp({super.key});

  @override
  Widget build(BuildContext context) {
    print('Building WebServerTestApp');
    return MaterialApp(
      title: 'Web Server Test',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.purple),
        useMaterial3: true,
      ),
      home: const ServerTestScreen(),
      debugShowCheckedModeBanner: true,
    );
  }
}

class ServerTestScreen extends StatefulWidget {
  const ServerTestScreen({super.key});

  @override
  State<ServerTestScreen> createState() => _ServerTestScreenState();
}

class _ServerTestScreenState extends State<ServerTestScreen> {
  int _counter = 0;
  
  @override
  void initState() {
    super.initState();
    print('ServerTestScreen initState called');
  }
  
  void _incrementCounter() {
    setState(() {
      _counter++;
    });
    print('Counter incremented: $_counter');
  }
  
  @override
  Widget build(BuildContext context) {
    print('Building ServerTestScreen');
    
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.purple,
        title: const Text('Web Server Test', style: TextStyle(color: Colors.white)),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'WEB SERVER MODE',
              style: TextStyle(
                fontSize: 24, 
                fontWeight: FontWeight.bold,
                color: Colors.purple,
              ),
            ),
            const SizedBox(height: 30),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.purple.shade100,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Text(
                'If you can see this text, web server mode is working!',
                style: TextStyle(fontSize: 18),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 30),
            const Text(
              'You have pushed the button this many times:',
            ),
            Text(
              '$_counter',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.purple,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              ),
              onPressed: _incrementCounter,
              child: const Text('Increment Counter'),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _incrementCounter,
        tooltip: 'Increment',
        child: const Icon(Icons.add),
      ),
    );
  }
}
EOF

echo -e "${BLUE}Starting Flutter app in web-server mode...${NC}"
echo -e "${YELLOW}This will make the app available on http://localhost:8080${NC}"
echo -e "${YELLOW}Make sure to open that URL in your browser!${NC}"

# Run in web-server mode
flutter run -d web-server --web-hostname=0.0.0.0 --web-port=8080 lib/test/server_test.dart