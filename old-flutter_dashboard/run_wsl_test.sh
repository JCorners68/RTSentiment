#!/bin/bash
if [ "$1" = "chrome" ]; then
  flutter run -d chrome lib/wsl_test/minimal.dart
elif [ "$1" = "linux" ]; then
  flutter run -d linux lib/wsl_test/minimal.dart
else
  flutter run -d web-server lib/wsl_test/minimal.dart
fi
