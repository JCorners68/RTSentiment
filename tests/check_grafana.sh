#!/bin/bash
# Check if Grafana is properly displaying metrics

echo "Checking Grafana health..."
HEALTH=$(curl -s http://localhost:3000/api/health)
echo $HEALTH | grep -q "ok" && echo "✅ Grafana is healthy" || echo "❌ Grafana is not healthy"

echo ""
echo "Checking Prometheus data source in Grafana..."
docker-compose exec -T grafana curl -s http://admin:admin@localhost:3000/api/datasources | grep -q "Prometheus" && echo "✅ Prometheus data source found" || echo "❌ Prometheus data source not found"

echo ""
echo "Checking if scraper dashboard is available..."
DASHBOARD_UID=$(docker-compose exec -T grafana curl -s http://admin:admin@localhost:3000/api/search?query=scraper | grep -o '"uid":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$DASHBOARD_UID" ]; then
    echo "✅ Found dashboard with UID: $DASHBOARD_UID"
    
    echo ""
    echo "Checking metrics data in dashboard..."
    METRICS_DATA=$(docker-compose exec -T grafana curl -s "http://admin:admin@localhost:3000/api/datasources/proxy/1/api/v1/query?query=scraper_unique_items_total")
    echo $METRICS_DATA | grep -q "scraper_unique_items_total" && echo "✅ Metrics data is available" || echo "❌ Metrics data not available"
    
    echo ""
    echo "Grafana is accessible at: http://localhost:3000"
    echo "Default credentials: admin/admin"
    echo "Scraper dashboard should be available at: http://localhost:3000/d/$DASHBOARD_UID"
else
    echo "❌ Scraper dashboard not found"
fi