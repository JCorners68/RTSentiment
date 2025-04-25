#!/bin/bash
# Script to run a very minimal Flutter web app

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

WSL_IP=$(hostname -I | awk '{print $1}')
PORT=7070

echo -e "${YELLOW}Starting Minimal Flutter Web App${NC}"

# Create a very minimal Flutter app
mkdir -p lib/minimal
cat > lib/minimal/app.dart << 'EOF'
import 'package:flutter/material.dart';

void main() {
  runApp(const MinimalApp());
}

class MinimalApp extends StatelessWidget {
  const MinimalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Minimal Flutter App',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: const MinimalPage(),
    );
  }
}

class MinimalPage extends StatelessWidget {
  const MinimalPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Minimal Flutter App'),
        backgroundColor: Colors.blue,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            const Text(
              'This is a minimal Flutter web app',
              style: TextStyle(fontSize: 20),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Button pressed!'),
                    duration: Duration(seconds: 1),
                  ),
                );
              },
              child: const Text('Press Me'),
            ),
          ],
        ),
      ),
    );
  }
}
EOF

# Copy web files
mkdir -p web_simple
cat > web_simple/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta content="IE=Edge" http-equiv="X-UA-Compatible">
  <meta name="description" content="A minimal Flutter application">
  <title>Minimal Flutter App</title>
  <style>
    body {
      margin: 0;
      padding: 0;
      background-color: #f5f5f5;
      overflow: hidden;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
    }
    .center {
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      height: 100%;
    }
    .loading {
      width: 50px;
      height: 50px;
      border: 5px solid #e0e0e0;
      border-radius: 50%;
      border-top: 5px solid #2196f3;
      animation: spin 1s linear infinite;
      margin-bottom: 20px;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  </style>
  <script src="flutter.js" defer></script>
</head>
<body>
  <div id="loading" class="center">
    <div class="loading"></div>
    <p>Loading Flutter app...</p>
  </div>
  <div id="flutter_target" style="width: 100%; height: 100%;"></div>

  <script>
    window.addEventListener('load', function() {
      // Dynamic service worker version
      const serviceWorkerVersion = Date.now().toString();
      
      console.log('Loading Flutter app');
      
      // Initialize Flutter app with explicit HTML renderer
      _flutter.loader.loadEntrypoint({
        serviceWorker: {
          serviceWorkerVersion: serviceWorkerVersion,
        },
        onEntrypointLoaded: async function(engineInitializer) {
          try {
            console.log('Flutter entrypoint loaded');
            
            // Initialize engine with HTML renderer
            const appRunner = await engineInitializer.initializeEngine({
              hostElement: document.getElementById('flutter_target'),
              renderer: 'html'
            });
            
            console.log('Flutter engine initialized');
            await appRunner.runApp();
            console.log('Flutter app started');
            
            // Hide loading indicator
            document.getElementById('loading').style.display = 'none';
          } catch (e) {
            console.error('Error initializing Flutter app:', e);
            document.getElementById('loading').innerHTML = 
              '<p style="color: red;">Error loading Flutter app: ' + e + '</p>';
          }
        }
      });
    });
  </script>
</body>
</html>
EOF

# Check Flutter version for proper web-renderer syntax
FLUTTER_VERSION=$(flutter --version | head -n 1 | sed 's/Flutter //' | awk '{print $1}')
MAJOR_VERSION=$(echo $FLUTTER_VERSION | cut -d. -f1)
MINOR_VERSION=$(echo $FLUTTER_VERSION | cut -d. -f2)

# Choose the correct syntax based on Flutter version
if [ $MAJOR_VERSION -gt 3 ] || ([ $MAJOR_VERSION -eq 3 ] && [ $MINOR_VERSION -ge 3 ]); then
  WEB_RENDERER_FLAG="--web-renderer=html"
else
  WEB_RENDERER_FLAG="--web-renderer html"
fi

echo -e "${YELLOW}Building minimal Flutter web app...${NC}"
flutter build web -t lib/minimal/app.dart

echo -e "${YELLOW}Copying custom HTML...${NC}"
cp web_simple/index.html build/web/

echo -e "${GREEN}Starting minimal web server on port ${PORT}${NC}"
echo -e "${BLUE}Access from Windows at: http://${WSL_IP}:${PORT}${NC}"

cd build/web && python3 -m http.server ${PORT} --bind 0.0.0.0