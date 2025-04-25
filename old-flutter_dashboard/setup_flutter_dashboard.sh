#!/bin/bash
# Setup script for Flutter dashboard

echo "Setting up Flutter dashboard..."

# Create necessary directories
mkdir -p flutter_dashboard/assets/images
mkdir -p flutter_dashboard/lib/utils

# Install Flutter dependencies
cd flutter_dashboard
echo "Installing Flutter dependencies..."
flutter pub get

# Generate JSON serialization code
echo "Generating JSON serialization code..."
flutter pub run build_runner build --delete-conflicting-outputs

echo "Setup complete! You can now run the Flutter dashboard with:"
echo "  cd flutter_dashboard && flutter run -d chrome"