#!/bin/bash
# Script to run the Flutter app in live mode (with real API data)

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running Flutter Dashboard in Live Data Mode${NC}"

# Create app_config.dart with live mode settings
echo -e "${YELLOW}Configuring live mode...${NC}"
mkdir -p lib/utils
cat > lib/utils/app_config.dart << 'EOF'
// lib/utils/app_config.dart

const bool isDemoMode = false; // Set to true for demo, false for live
// You might later configure this using build flavors or environment variables
EOF

# Get dependencies
echo -e "${YELLOW}Getting dependencies...${NC}"
flutter pub get

# Run build runner to generate JSON serialization code
echo -e "${YELLOW}Running build_runner...${NC}"
dart run build_runner build --delete-conflicting-outputs

# Create a smaller sized window for Chrome
echo -e "${YELLOW}Creating window configuration...${NC}"
mkdir -p web
cat > web/window_config.js << 'EOF'
// Set the initial window size
window.addEventListener('load', function() {
  // Set window size to 1200x800 (smaller than default)
  if (window.chrome) {
    const width = 1200;
    const height = 800;
    window.resizeTo(width, height);
  }
});
EOF

# Update index.html if it exists to include the window config
if [ -f web/index.html ]; then
  # Check if the script is already included
  if ! grep -q "window_config.js" web/index.html; then
    echo -e "${YELLOW}Updating index.html...${NC}"
    sed -i '/<\/head>/i \  <script src="window_config.js"></script>' web/index.html
  fi
else
  # Create a basic index.html
  cat > web/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta content="IE=Edge" http-equiv="X-UA-Compatible">
  <meta name="description" content="Real-Time Sentiment Analysis Dashboard.">

  <!-- iOS meta tags & icons -->
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <meta name="apple-mobile-web-app-title" content="RT Sentiment">
  <link rel="apple-touch-icon" href="icons/Icon-192.png">

  <!-- Favicon -->
  <link rel="icon" type="image/png" href="favicon.png"/>

  <!-- Window size configuration -->
  <script src="window_config.js"></script>

  <title>RT Sentiment Dashboard</title>
  <link rel="manifest" href="manifest.json">
</head>
<body>
  <script src="flutter.js" defer></script>
  <script>
    window.addEventListener('load', function(ev) {
      _flutter.loader.loadEntrypoint({
        serviceWorker: {
          serviceWorkerVersion: serviceWorkerVersion,
        },
        onEntrypointLoaded: function(engineInitializer) {
          engineInitializer.initializeEngine().then(function(appRunner) {
            appRunner.runApp();
          });
        }
      });
    });
  </script>
</body>
</html>
EOF
fi

# Try to run with Chrome
if flutter devices | grep -q chrome; then
  echo -e "${GREEN}Running in Chrome with live data...${NC}"
  flutter run -d chrome --web-port=9100
# Otherwise try with web-server
else
  echo -e "${YELLOW}Chrome not found, running in web-server mode...${NC}"
  flutter run -d web-server --web-hostname=0.0.0.0 --web-port=8080
  echo -e "${GREEN}Web server running at http://localhost:8080${NC}"
fi