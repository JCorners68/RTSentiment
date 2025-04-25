#!/bin/bash
# Script to fix Grafana issues

# Stop any running metrics_updater
if [ -f /tmp/metrics_updater_pid.txt ]; then
    echo "Stopping existing metrics updater..."
    kill $(cat /tmp/metrics_updater_pid.txt) 2>/dev/null || true
    rm /tmp/metrics_updater_pid.txt
fi

# Restart the continuous metrics updater
echo "Starting continuous metrics updater..."
source metrics_venv/bin/activate && python tests/update_metrics.py > /tmp/update_metrics.log 2>&1 &
echo $! > /tmp/metrics_updater_pid.txt
sleep 2

# Restart Grafana and Prometheus
echo "Restarting Grafana and Prometheus..."
docker-compose restart prometheus grafana
sleep 5

# Create a fresh provisioning file
echo "Creating fresh provisioning files..."
cat > monitoring/grafana/provisioning/datasources/prometheus.yaml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

cat > monitoring/grafana/provisioning/dashboards/default.yaml << EOF
apiVersion: 1

providers:
  - name: 'Default'
    orgId: 1
    folder: 'Scraper Metrics'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
EOF

# Print instructions
echo ""
echo "=========================="
echo "Fix applied! Please:"
echo "1. Go to http://localhost:3000/ (admin/admin)"
echo "2. Add a Prometheus data source manually:"
echo "   a. Go to Connections -> Data sources"
echo "   b. Add new data source"
echo "   c. Select Prometheus"
echo "   d. URL: http://prometheus:9090"
echo "   e. Save & Test"
echo "3. Import dashboards at:"
echo "   a. http://localhost:3000/dashboard/import"
echo "   b. Upload JSON files from: monitoring/grafana/dashboards/scraper/"
echo "=========================="
echo ""
echo "Metrics are continuously updating, check Prometheus at:"
echo "http://localhost:9090/graph?g0.expr=scraper_unique_items_total&g0.tab=0&g0.stacked=0&g0.show_exemplars=0&g0.range_input=1h"