#!/bin/bash
# Ultra-simple test script for Flutter dashboard

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running Simplified Flutter Test${NC}"

# Create a very minimal flutter app to test rendering
mkdir -p lib/test
cat > lib/test/simple.dart << 'EOF'
import 'package:flutter/material.dart';

void main() {
  runApp(const SimpleTestApp());
}

class SimpleTestApp extends StatelessWidget {
  const SimpleTestApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Basic Test App',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      home: const SimpleTestScreen(),
    );
  }
}

class SimpleTestScreen extends StatelessWidget {
  const SimpleTestScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Log that we're building the screen
    print('Building SimpleTestScreen');
    
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('Basic Test App'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'If you can see this text, rendering is working',
              style: TextStyle(fontSize: 20),
            ),
            const SizedBox(height: 20),
            Card(
              color: Colors.blue,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Test Card',
                      style: TextStyle(color: Colors.white, fontSize: 18),
                    ),
                    const SizedBox(height: 8),
                    ElevatedButton(
                      onPressed: () {
                        print('Button pressed!');
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('It works!')),
                        );
                      },
                      child: const Text('Test Button'),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
EOF

# Run the minimal test
echo -e "${GREEN}Running basic test app on port 9100...${NC}"
flutter run -d chrome lib/test/simple.dart --web-port=9100