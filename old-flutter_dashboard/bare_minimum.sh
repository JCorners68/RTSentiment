#!/bin/bash
# Absolute bare minimum Flutter web app

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Creating Absolute Minimal Flutter Web App${NC}"

# Create a directory for the absolute minimal app
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
      title: 'Minimal App',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const MyHomePage(),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key});

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int _counter = 0;

  void _incrementCounter() {
    setState(() {
      _counter++;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Minimal Flutter Web Demo'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            const Text(
              'You have pushed the button this many times:',
            ),
            Text(
              '$_counter',
              style: Theme.of(context).textTheme.headlineMedium,
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

# Clean the project first
echo -e "${BLUE}Cleaning the project...${NC}"
flutter clean

# Get dependencies fresh
echo -e "${BLUE}Getting dependencies...${NC}"
flutter pub get

# Run on all possible modes
echo -e "${GREEN}Trying to run the minimal app in different modes...${NC}"

# Try web-server mode
echo -e "\n${YELLOW}ATTEMPT 1: Web Server Mode${NC}"
echo -e "${BLUE}Press Ctrl+C if this fails after 20 seconds${NC}"
flutter run lib/minimal/main.dart -d web-server --web-port=8090 &
WEB_SERVER_PID=$!

# Wait for user to check
echo -e "${YELLOW}Please check http://localhost:8090${NC}"
sleep 20
kill $WEB_SERVER_PID 2>/dev/null

# Try Chrome directly
echo -e "\n${YELLOW}ATTEMPT 2: Chrome Direct${NC}"
echo -e "${BLUE}Press Ctrl+C if this fails after 20 seconds${NC}"
flutter run lib/minimal/main.dart -d chrome --web-port=9090 &
CHROME_PID=$!

# Wait for user to check
echo -e "${YELLOW}Chrome should open automatically${NC}"
sleep 20
kill $CHROME_PID 2>/dev/null

# Try Flutter directly without specifying device
echo -e "\n${YELLOW}ATTEMPT 3: Default Flutter Run${NC}"
echo -e "${BLUE}Press Ctrl+C if this fails after 20 seconds${NC}"
flutter run lib/minimal/main.dart --web-port=7090 &
DEFAULT_PID=$!

# Wait for user to check
echo -e "${YELLOW}Flutter should select the best available device${NC}"
sleep 20
kill $DEFAULT_PID 2>/dev/null

# Create a direct HTML file as a workaround
echo -e "\n${YELLOW}ATTEMPT 4: Manual HTML File${NC}"
mkdir -p web_minimal
cat > web_minimal/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Minimal HTML Demo</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
    }
    .card {
      background-color: #f0f0f0;
      border-radius: 8px;
      padding: 20px;
      margin: 10px;
      width: 300px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .positive {
      background-color: #d4edda;
      border-left: 5px solid #28a745;
    }
    .negative {
      background-color: #f8d7da;
      border-left: 5px solid #dc3545;
    }
    h1 {
      color: #333;
    }
    button {
      background-color: #007bff;
      color: white;
      border: none;
      padding: 10px 15px;
      border-radius: 4px;
      cursor: pointer;
    }
    button:hover {
      background-color: #0069d9;
    }
  </style>
</head>
<body>
  <h1>RT Sentiment Dashboard</h1>
  <p>HTML Fallback (if Flutter web is not working)</p>
  
  <div class="card positive">
    <h3>AAPL: +0.85</h3>
    <div style="background-color: #ccc; height: 10px; width: 100%;">
      <div style="background-color: #28a745; height: 10px; width: 85%;"></div>
    </div>
  </div>
  
  <div class="card negative">
    <h3>META: -0.45</h3>
    <div style="background-color: #ccc; height: 10px; width: 100%;">
      <div style="background-color: #dc3545; height: 10px; width: 45%;"></div>
    </div>
  </div>
  
  <button onclick="alert('Demo button clicked!')">Demo Button</button>
  
  <script>
    console.log('HTML fallback loaded successfully');
  </script>
</body>
</html>
EOF

echo -e "${BLUE}Created a plain HTML fallback at web_minimal/index.html${NC}"
echo -e "${YELLOW}You can open this file directly in your browser if Flutter web continues to fail${NC}"

echo -e "\n${GREEN}Testing complete.${NC}"
echo -e "${YELLOW}If none of these approaches worked, consider:${NC}"
echo -e "1. Using the plain HTML fallback in web_minimal/index.html"
echo -e "2. Updating Flutter to the latest version"
echo -e "3. Creating a new Flutter project from scratch"
echo -e "4. Using a different framework for WSL development"