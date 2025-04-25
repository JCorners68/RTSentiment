# Local Development Setup

This document provides guidance for running the Flutter dashboard locally, especially in a WSL environment.

## Running the Dashboard

You have several options for running the Flutter dashboard:

### Run on Windows Chrome (Recommended for Windows Users)
```bash
./run_windows_chrome.sh
```
This will start the app in web server mode. Access the application using your WSL IP address (shown in the script output), typically at http://172.xx.xx.xx:8080.

### Debug Mode for Troubleshooting
```bash
./run_debug_windows.sh
```
Provides enhanced logging and debugging for when you encounter issues.

### Minimal Debug Version
```bash
./run_minimal_debug.sh
```
Runs a simplified version that helps isolate issues with the Flutter web framework.

### Run on Linux/WSL
```bash
./run_flutter_wsl.sh
```
This attempts to run the app in Linux desktop mode, which requires proper X11 setup in WSL.

## Connection Troubleshooting

If you're having trouble connecting from Windows to the WSL app:

1. **Use the WSL IP address** - Instead of using "localhost", access using the WSL IP address shown in the script output (e.g., http://172.25.21.114:8080)

2. **Check WSL connectivity from Windows:**
   ```
   ping <your-wsl-ip>
   ```

3. **Check Windows Firewall:**
   - Make sure Windows Firewall allows connections to WSL
   - You may need to add a rule for incoming connections on the port (8080, 9090, etc.)

4. **Port conflicts:**
   - Check if something else is using the port on your Windows system
   - Try the debug version with a different port: `./run_debug_windows.sh`
   - Check running services: `netstat -ano | findstr :8080` (in Windows CMD)

5. **Try a different browser** if Chrome is having issues

## Logs and Debugging

- Regular logs: `flutter_web_debug.log`
- Debug mode logs: `flutter_debug.log`
- Minimal version logs: `flutter_minimal_debug.log`

If none of the scripts work, you can try a direct Flutter web launch:
```bash
flutter run -d web-server --web-hostname=0.0.0.0 --web-port=8080 --verbose
```