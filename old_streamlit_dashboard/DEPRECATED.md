# DEPRECATED: Streamlit Dashboard

## Status: Deprecated

This Streamlit dashboard has been deprecated in favor of the new Flutter UI located in the `/senti` directory.

## Reasons for Deprecation

1. The Flutter UI provides better performance and a more responsive user experience
2. Flutter enables cross-platform support (web, mobile, desktop)
3. The new UI offers enhanced visualizations and interactive features
4. Improved integration with WebSocket for real-time updates

## Migration Path

If you need dashboard functionality, please use the new Flutter UI:

```bash
# Navigate to the Flutter project directory
cd /home/jonat/WSL_RT_Sentiment/senti

# Run the Flutter app (web version)
flutter run -d chrome
```

## Historical Reference

This directory is retained for historical reference and as a backup. The code is no longer actively maintained or deployed as part of the standard system.

If you need to temporarily run the old Streamlit dashboard for comparison or testing:

1. Uncomment the dashboard service in `docker-compose.yml`
2. Run `docker-compose up -d dashboard`
3. Access the dashboard at http://localhost:8501

## Timeline

- **Created**: [Original creation date]
- **Deprecated**: April 23, 2025
- **Scheduled for removal**: October 2025 (6 months after deprecation)