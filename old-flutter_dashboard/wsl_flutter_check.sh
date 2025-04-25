#!/bin/bash
# WLS Flutter Environment Diagnostic Tool

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

OUTPUT_FILE="flutter_wsl_diagnosis.log"

# Helper to log messages
log_section() {
  echo -e "\n${YELLOW}======== $1 ========${NC}" | tee -a "$OUTPUT_FILE"
}

log_info() {
  echo -e "${BLUE}$1${NC}" | tee -a "$OUTPUT_FILE"
}

log_pass() {
  echo -e "${GREEN}✓ $1${NC}" | tee -a "$OUTPUT_FILE"
}

log_fail() {
  echo -e "${RED}✗ $1${NC}" | tee -a "$OUTPUT_FILE"
}

log_cmd() {
  echo -e "\n${BLUE}Running: $1${NC}" | tee -a "$OUTPUT_FILE"
  eval "$1" | tee -a "$OUTPUT_FILE"
}

# Start fresh log
echo "WSL Flutter Environment Check - $(date)" > "$OUTPUT_FILE"
echo -e "${YELLOW}Running WSL Flutter Environment Check${NC}" | tee -a "$OUTPUT_FILE"
echo -e "${YELLOW}Detailed logs will be saved to ${OUTPUT_FILE}${NC}"

# System information
log_section "SYSTEM INFORMATION"
log_cmd "uname -a"
log_cmd "cat /etc/os-release"
log_cmd "lsb_release -a 2>/dev/null || echo 'lsb_release not available'"
log_cmd "env | grep -E 'WSL|DISPLAY|WAYLAND'"

# WSL version
log_section "WSL VERSION"
if grep -q Microsoft /proc/version; then
  log_info "Running in WSL"
  if grep -q microsoft-standard-WSL2 /proc/version; then
    log_pass "WSL2 detected"
  else
    log_info "WSL1 detected"
  fi
else
  log_info "Not running in WSL"
fi

# Display settings
log_section "DISPLAY SETTINGS"
if [ -n "$DISPLAY" ]; then
  log_pass "DISPLAY variable is set to: $DISPLAY"
else
  log_fail "DISPLAY variable is not set"
  echo -e "  ${YELLOW}This may prevent GUI applications from opening${NC}" | tee -a "$OUTPUT_FILE"
fi

# X server check
log_section "X SERVER CHECK"
if command -v xdpyinfo >/dev/null 2>&1; then
  log_info "xdpyinfo is installed. Checking X server connection..."
  if xdpyinfo >/dev/null 2>&1; then
    log_pass "X server connection successful"
  else
    log_fail "X server connection failed"
    echo -e "  ${YELLOW}Make sure an X server (like VcXsrv or Xming) is running on Windows${NC}" | tee -a "$OUTPUT_FILE"
  fi
else
  log_info "xdpyinfo not installed. Installing x11-utils for testing..."
  sudo apt-get install -y x11-utils >/dev/null 2>&1
  if xdpyinfo >/dev/null 2>&1; then
    log_pass "X server connection successful after installing x11-utils"
  else
    log_fail "X server connection failed after installing x11-utils"
  fi
fi

# OpenGL check
log_section "OPENGL CHECK"
if command -v glxinfo >/dev/null 2>&1; then
  log_info "glxinfo is installed. Checking OpenGL rendering..."
  if glxinfo | grep "OpenGL renderer" | grep -v "llvmpipe"; then
    log_pass "Hardware OpenGL rendering available"
  else
    log_info "Software OpenGL rendering detected"
  fi
else
  log_info "glxinfo not installed. Installing mesa-utils for testing..."
  sudo apt-get install -y mesa-utils >/dev/null 2>&1
  if glxinfo | grep "OpenGL renderer" | grep -v "llvmpipe"; then
    log_pass "Hardware OpenGL rendering available"
  else
    log_info "Software OpenGL rendering detected"
  fi
fi

# Flutter information
log_section "FLUTTER INFORMATION"
log_cmd "flutter --version"
log_cmd "flutter doctor -v"

# Flutter web support
log_section "FLUTTER WEB SUPPORT"
log_cmd "flutter devices"
if flutter devices | grep -q "Chrome"; then
  log_pass "Chrome is available for Flutter web development"
else
  log_fail "Chrome not detected. Web development may be limited"
fi

if flutter devices | grep -q "Linux"; then
  log_pass "Linux desktop target is available"
else
  log_info "Linux desktop target not detected"
fi

if flutter devices | grep -q "Web Server"; then
  log_pass "Web Server target is available"
else
  log_info "Web Server target not detected"
fi

# Project configuration
log_section "PROJECT CONFIGURATION"
log_cmd "ls -la"
log_cmd "cat pubspec.yaml"

# Generate minimal test app
log_section "GENERATING TEST APP"
mkdir -p lib/wsl_test
cat > lib/wsl_test/minimal.dart << 'EOF'
import 'package:flutter/material.dart';

void main() {
  print("Starting minimal test app");
  runApp(const MinimalApp());
}

class MinimalApp extends StatelessWidget {
  const MinimalApp({super.key});

  @override
  Widget build(BuildContext context) {
    print("Building MinimalApp");
    return MaterialApp(
      title: 'WSL Test',
      home: Scaffold(
        appBar: AppBar(title: const Text('WSL Flutter Test')),
        body: const Center(child: Text('Test App')),
      ),
    );
  }
}
EOF
log_pass "Test app created at lib/wsl_test/minimal.dart"

# Create test script
cat > run_wsl_test.sh << 'EOF'
#!/bin/bash
if [ "$1" = "chrome" ]; then
  flutter run -d chrome lib/wsl_test/minimal.dart
elif [ "$1" = "linux" ]; then
  flutter run -d linux lib/wsl_test/minimal.dart
else
  flutter run -d web-server lib/wsl_test/minimal.dart
fi
EOF
chmod +x run_wsl_test.sh
log_pass "Test script created: run_wsl_test.sh"

# Summary
log_section "RECOMMENDATION"
echo -e "Based on the checks performed, here are recommendations:" | tee -a "$OUTPUT_FILE"

if grep -q "DISPLAY variable is not set" "$OUTPUT_FILE"; then
  echo -e "1. ${YELLOW}Set your DISPLAY variable:${NC}" | tee -a "$OUTPUT_FILE"
  echo -e "   export DISPLAY=:0" | tee -a "$OUTPUT_FILE"
fi

if grep -q "X server connection failed" "$OUTPUT_FILE"; then
  echo -e "2. ${YELLOW}Make sure an X server is running on Windows:${NC}" | tee -a "$OUTPUT_FILE"
  echo -e "   - Install VcXsrv, Xming, or another X server" | tee -a "$OUTPUT_FILE"
  echo -e "   - Ensure it's configured to allow connections from WSL" | tee -a "$OUTPUT_FILE"
fi

echo -e "\n${YELLOW}Try running the app with:${NC}" | tee -a "$OUTPUT_FILE"
echo -e "   ./run_wsl_test.sh chrome  # For Chrome" | tee -a "$OUTPUT_FILE"
echo -e "   ./run_wsl_test.sh linux   # For Linux desktop" | tee -a "$OUTPUT_FILE"
echo -e "   ./run_wsl_test.sh         # For web-server mode" | tee -a "$OUTPUT_FILE"

echo -e "\n${BLUE}Complete log saved to: ${OUTPUT_FILE}${NC}"
echo -e "${GREEN}Diagnostic complete. Use the above recommendations to troubleshoot WSL Flutter rendering.${NC}"