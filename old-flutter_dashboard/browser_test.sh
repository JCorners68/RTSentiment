#!/bin/bash
# Cross-browser test script for Flutter dashboard

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running Cross-Browser Flutter Test${NC}"

# Create a very minimal flutter app to test rendering
mkdir -p lib/test
cat > lib/test/cross_browser.dart << 'EOF'
import 'package:flutter/material.dart';

void main() {
  // Print startup message
  print('\n\n==== FLUTTER APP STARTING ====\n');
  runApp(const CrossBrowserTestApp());
}

class CrossBrowserTestApp extends StatelessWidget {
  const CrossBrowserTestApp({super.key});

  @override
  Widget build(BuildContext context) {
    print('Building CrossBrowserTestApp');
    return MaterialApp(
      title: 'Cross-Browser Test',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      home: const TestScreen(),
      debugShowCheckedModeBanner: true,
    );
  }
}

class TestScreen extends StatefulWidget {
  const TestScreen({super.key});

  @override
  State<TestScreen> createState() => _TestScreenState();
}

class _TestScreenState extends State<TestScreen> {
  bool _showBanner = true;
  
  @override
  void initState() {
    super.initState();
    print('TestScreen initState called');
  }
  
  @override
  Widget build(BuildContext context) {
    print('Building TestScreen');
    
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.green,
        title: const Text('Cross-Browser Test', style: TextStyle(color: Colors.white)),
      ),
      body: Column(
        children: [
          // Debug Banner
          if (_showBanner)
            Container(
              color: Colors.red,
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      'If you can see this text, rendering is working correctly!',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white),
                    onPressed: () {
                      setState(() {
                        _showBanner = false;
                      });
                    },
                  ),
                ],
              ),
            ),
          
          // Main Content
          Expanded(
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    'Cross-Browser Test',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 20),
                  Container(
                    width: 400,
                    padding: const EdgeInsets.all(16),
                    color: Colors.blue.shade100,
                    child: Column(
                      children: [
                        Text(
                          'Platform: ${Theme.of(context).platform}',
                          style: const TextStyle(fontSize: 16),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Window Size: ${MediaQuery.of(context).size.width.toInt()}x${MediaQuery.of(context).size.height.toInt()}',
                          style: const TextStyle(fontSize: 16),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: () {
                      print('Button clicked!');
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Button clicked!'),
                          duration: Duration(seconds: 1),
                        ),
                      );
                    },
                    child: const Text('Click Me'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
EOF

echo -e "${BLUE}Check available devices...${NC}"
flutter devices

# Function to test the app on a specific platform
test_on_platform() {
  local platform=$1
  local port=$2
  
  echo -e "\n${YELLOW}=====================================${NC}"
  echo -e "${GREEN}Testing on $platform (port $port)...${NC}"
  echo -e "${YELLOW}=====================================${NC}\n"
  
  # Try to launch the app
  flutter run -d $platform lib/test/cross_browser.dart --web-port=$port
  
  # Ask for feedback
  echo -e "\n${YELLOW}Did the app render correctly on $platform? (y/n)${NC}"
  read -n 1 -r
  echo ""
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}$platform test PASSED!${NC}"
    return 0
  else
    echo -e "${RED}$platform test FAILED!${NC}"
    return 1
  fi
}

# Try Linux first if available
if flutter devices | grep -q linux; then
  echo -e "${BLUE}Linux platform found. Testing on Linux...${NC}"
  test_on_platform "linux" "9100"
  linux_result=$?
else
  echo -e "${RED}Linux platform not available.${NC}"
  linux_result=1
fi

# Try Chrome next if available
if flutter devices | grep -q chrome; then
  echo -e "${BLUE}Chrome platform found. Testing on Chrome...${NC}"
  test_on_platform "chrome" "9200"
  chrome_result=$?
else
  echo -e "${RED}Chrome platform not available.${NC}"
  chrome_result=1
fi

# Print summary
echo -e "\n${YELLOW}===== TEST SUMMARY =====${NC}"
if [ $linux_result -eq 0 ]; then
  echo -e "${GREEN}Linux: PASSED${NC}"
else
  echo -e "${RED}Linux: FAILED${NC}"
fi

if [ $chrome_result -eq 0 ]; then
  echo -e "${GREEN}Chrome: PASSED${NC}"
else
  echo -e "${RED}Chrome: FAILED${NC}"
fi

# Provide next steps
echo -e "\n${BLUE}Next steps:${NC}"
if [ $linux_result -eq 0 ] || [ $chrome_result -eq 0 ]; then
  echo -e "- At least one platform worked! You should be able to use that platform for development."
  if [ $linux_result -eq 0 ] && [ $chrome_result -ne 0 ]; then
    echo -e "- Update your run scripts to use Linux instead of Chrome."
  elif [ $chrome_result -eq 0 ] && [ $linux_result -ne 0 ]; then
    echo -e "- Continue using Chrome for development."
  fi
else
  echo -e "${RED}Both platforms failed. This suggests a deeper Flutter configuration issue.${NC}"
  echo -e "- Check Flutter installation with 'flutter doctor'"
  echo -e "- Consider upgrading Flutter with 'flutter upgrade'"
  echo -e "- Verify WSL graphics configuration for Linux/GUI support"
fi