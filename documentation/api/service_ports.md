# Service Ports Reference

This document lists all the ports used by services in the Senti platform, helping developers avoid port conflicts and understand the system architecture.

## Service Port Assignments

| Service | Host Port | Container Port | Description |
|---------|-----------|---------------|-------------|
| flutter-web | 8888 | 80 | Flutter Web UI (Nginx) |
| api | 8001 | 8001 | Backend API Service |
| sentiment-analysis | 8000 | 8000 | Sentiment Analysis Service |
| auth-service | 8002 | 8002 | Authentication Service |
| postgres | 5432 | 5432 | PostgreSQL Database |
| redis | 6379 | 6379 | Redis Cache Server |
| zookeeper | 2181 | 2181 | ZooKeeper (for Kafka) |
| kafka | 9092, 29092 | 9092 | Kafka Message Broker |
| kafka-ui | 8080 | 8080 | Kafka UI Dashboard |
| prometheus | 9090 | 9090 | Prometheus Metrics |
| grafana | 3000 | 3000 | Grafana Dashboards |
| kafka-exporter | 9308 | 9308 | Kafka Metrics Exporter |
| node-exporter | 9100 | 9100 | System Metrics Exporter |

## Accessing Services

### Development Environment

When running services in development, you can access them at:

- Flutter Web UI: http://localhost:8888
- API Swagger Documentation: http://localhost:8001/docs
- Sentiment Analysis Service: http://localhost:8000
- Grafana Dashboards: http://localhost:3000
- Prometheus: http://localhost:9090
- Kafka UI: http://localhost:8080

### Production Environment

In production, all services except the Flutter UI are typically behind an API Gateway with proper authentication and are not directly accessible.

## Avoiding Port Conflicts

If you encounter port conflicts when starting services, you can:

1. Identify which local service is using the conflicting port:
   ```bash
   sudo lsof -i :<port_number>
   # or
   netstat -tuln | grep <port_number>
   ```

2. Either stop the conflicting service or modify the port mapping in docker-compose.yml:
   ```yaml
   service_name:
     ports:
       - "new_port:container_port"  # Change new_port to an available port
   ```

3. Update any references to the changed port in documentation and configuration files

## Notes for Windows/WSL Users

When using WSL, be aware that ports are shared with the Windows host system. If a port is in use by a Windows application, it will cause conflicts with services running in WSL. Use `netstat -ano | findstr <port_number>` in a Windows Command Prompt to identify Windows processes using specific ports.

## Port Reservation Strategy

To avoid future conflicts, the project follows these port allocation guidelines:

- 8000-8099: Reserved for API and core services
- 5000-5099: Reserved for databases and caches
- 9000-9099: Reserved for monitoring services
- 3000-3099: Reserved for dashboards and UIs