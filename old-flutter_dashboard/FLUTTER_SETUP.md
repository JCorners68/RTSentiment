# Flutter Dashboard Setup Guide

This guide will help you install Flutter and set up the Real-Time Sentiment Analysis Dashboard.

## Installing Flutter

### Option 1: Using snap (Ubuntu/Debian)

If you're using a system that supports snap:

```bash
sudo snap install flutter --classic
```

### Option 2: Manual Installation

1. Install required Linux dependencies (especially important for WSL):
   ```bash
   sudo apt update
   sudo apt install -y curl git unzip xz-utils zip libglu1-mesa wget
   
   # For Linux desktop support
   sudo apt install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev
   ```

2. Download the Flutter SDK:
   ```bash
   wget https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.19.3-stable.tar.xz
   ```

3. Extract it to your preferred location (e.g., ~/development):
   ```bash
   mkdir -p ~/development
   tar xf flutter_linux_3.19.3-stable.tar.xz -C ~/development
   ```

4. Add Flutter to your PATH by adding this line to your `~/.bashrc` or `~/.zshrc`:
   ```bash
   export PATH="$PATH:$HOME/development/flutter/bin"
   ```

5. Apply the changes:
   ```bash
   source ~/.bashrc  # or source ~/.zshrc
   ```

6. Enable Linux desktop support:
   ```bash
   flutter config --enable-linux-desktop
   ```

7. Verify the installation:
   ```bash
   flutter doctor
   ```
   
   Fix any issues reported by the doctor command.

### Option 3: Using the Helper Script

Run the provided setup script which will guide you through the process:

```bash
./setup_flutter.sh
```

## Setup Flutter Dashboard

Once Flutter is installed, follow these steps to set up the dashboard:

1. Navigate to the flutter_dashboard directory:
   ```bash
   cd flutter_dashboard
   ```

2. Install dependencies:
   ```bash
   flutter pub get
   ```

3. Generate JSON serialization code:
   ```bash
   flutter pub run build_runner build --delete-conflicting-outputs
   ```

## Running the Flutter Dashboard

### Running on WSL

When running Flutter on WSL, there are some specific considerations:

1. **Linux Desktop App (Recommended for WSL)**:
   ```bash
   cd flutter_dashboard
   flutter run -d linux
   ```
   This will run the app as a native Linux desktop application.

2. **Using Windows Chrome from WSL**:
   
   To run in Chrome from WSL, you need additional setup:
   
   ```bash
   # Install Chrome in WSL if not already installed
   sudo apt update
   sudo apt install -y wget
   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
   sudo apt install -y ./google-chrome-stable_current_amd64.deb
   flutter create .
   
   # Then run with chrome device
   cd flutter_dashboard
   flutter run -d chrome
   ```
   
   Alternatively, you can connect to a Windows Chrome instance by setting up browser discovery.

3. **Using Convenience Scripts (Recommended)**:
   ```bash
   cd flutter_dashboard
   ./fix_code.sh   # Fix code issues and run on Linux
   # OR
   ./run_web.sh    # Run in web mode
   # OR
   ./run_demo.sh   # Run in demo mode with sample data
   ```
   These scripts automatically handle dependency installation, code generation, and running the app.
   
   The demo mode is especially useful when you don't have a backend API running.
   
4. **Default Run (will use available device)**:
   ```bash
   cd flutter_dashboard
   flutter run
   ```
   This will use the first available device (usually Linux desktop in WSL).

### Other Options

#### Web (For non-WSL environments)
```bash
cd flutter_dashboard
flutter run -d chrome
```

#### Desktop (Windows/macOS)
```bash
cd flutter_dashboard
flutter run -d windows  # or macos
```

#### Mobile (Android/iOS)
```bash
cd flutter_dashboard
flutter run -d android  # or ios
```

## Configuring the Backend API URL

By default, the dashboard connects to http://localhost:8001. If your API is running on a different host or port:

1. Open `lib/api/api_client.dart`
2. Modify the `baseUrl` parameter in the `ApiClient` constructor:

```dart
ApiClient({String? baseUrl}) : baseUrl = baseUrl ?? 'http://your-api-host:port';
```

## Building for Production

When you're ready to deploy the application:

### Web
```bash
flutter build web
```
The built files will be in `build/web` directory.

### Android
```bash
flutter build apk --release
```
The APK will be in `build/app/outputs/flutter-apk/app-release.apk`.

### iOS
```bash
flutter build ios --release
```
This will create a release build for iOS devices.

## Troubleshooting

### General Issues

1. **Flutter command not found**: Make sure Flutter is properly installed and added to your PATH.

2. **Dependency issues**: Try cleaning and getting dependencies again:
   ```bash
   flutter clean
   flutter pub get
   ```

3. **Build runner errors**: Check if you have the right dependencies in `pubspec.yaml`:
   ```bash
   flutter pub upgrade
   flutter pub run build_runner build --delete-conflicting-outputs
   ```

4. **API connection issues**: Verify that your backend API is running and accessible.

### WSL-Specific Issues

1. **Linux desktop dependencies**:
   - Install the required packages:
     ```bash
     sudo apt install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev
     ```

2. **X11 display issues**:
   - Make sure you have an X server running on Windows (like VcXsrv)
   - Set the DISPLAY environment variable:
     ```bash
     export DISPLAY=:0
     ```

3. **Segmentation fault when running**:
   - This could be due to missing system libraries. Try:
     ```bash
     sudo apt install -y libglu1-mesa libegl1-mesa libxinerama1 libxinerama-dev
     ```

4. **Linux desktop support not enabled**:
   - Enable it with:
     ```bash
     flutter config --enable-linux-desktop
     ```

5. **Secure storage issues on Linux**:
   - We've replaced flutter_secure_storage with shared_preferences for better compatibility
   - If you still encounter issues, try:
     ```bash
     sudo apt install -y libsecret-1-dev
     ```

6. **Web server mode if Chrome doesn't work**:
   - Run in web-server mode:
     ```bash
     flutter run -d web-server --web-hostname=0.0.0.0 --web-port=8080
     ```
   - Then access from your browser at http://localhost:8080

## Additional Resources

- [Flutter Documentation](https://docs.flutter.dev/)
- [Dart Documentation](https://dart.dev/guides)
- [Flutter GitHub Repository](https://github.com/flutter/flutter)