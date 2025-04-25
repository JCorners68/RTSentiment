#!/bin/bash
# Script to run build_runner for JSON serialization

# Make sure we're in the flutter dashboard directory
cd "$(dirname "$0")"

echo "Running flutter pub get to update dependencies..."
flutter pub get

echo "Running build_runner to generate JSON serialization code..."
flutter pub run build_runner build --delete-conflicting-outputs

echo "Build completed!"