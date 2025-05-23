# RT Sentiment Analysis

Real-time sentiment analysis system for monitoring and analyzing text sentiment across multiple data sources.

## Overview

RT Sentiment Analysis is a comprehensive system for gathering, analyzing, and presenting sentiment analysis data in real-time. The system includes data acquisition from various sources, sentiment analysis using NLP models, data storage with Apache Iceberg, and user interfaces for both administrators and mobile clients.

## Features

- Real-time sentiment analysis across multiple data sources
- Custom NLP models for domain-specific sentiment analysis
- Data lake storage using Apache Iceberg
- WebSocket API for real-time updates
- Mobile application for clients
- Web application for administrators
- Scalable containerized architecture
- Comprehensive monitoring and alerting

## System Architecture

The system is organized into the following main components:

- **Data Acquisition Service**: Gathers data from various sources
- **Sentiment Analysis Service**: Processes text to extract sentiment
- **Data Tier Service**: Manages data storage and retrieval
- **API Service**: Provides REST and WebSocket endpoints
- **Auth Service**: Handles authentication and authorization
- **Mobile App**: Client application for mobile devices
- **Admin Web App**: Management interface for administrators

For more details, see the [Architecture Documentation](docs/architecture/architecture_overview.md).

## Getting Started

### Prerequisites

- Docker and Docker Compose
- WSL2 for local development (SIT environment)
- Azure CLI for UAT deployment
- Python 3.9+
- Flutter SDK
- Terraform 1.0+ (for Azure deployment)

### Installation

#### Local Development (SIT Environment)

1. Clone the repository:
```bash
git clone https://github.com/example/rt-sentiment.git
cd rt-sentiment
```

2. Set up the SIT environment:
```bash
cd environments/sit
./setup.sh
```

3. Start the services:
```bash
cd ../../infrastructure
docker compose up -d
```

#### UAT Environment Deployment

For UAT deployment to Azure, follow these steps:

1. **Gather required Azure information**:
   - Follow the detailed instructions in [environments/uat/README.md](environments/uat/README.md#step-1-obtaining-required-azure-information)
   - You'll need subscription ID, tenant ID, and service principal credentials

2. **Configure GitHub Secrets**:
   - Store the Azure credentials in your GitHub repository secrets
   - Required secret: `AZURE_CREDENTIALS` (JSON format with all authentication details)

3. **Trigger the Deployment**:
   - Go to GitHub Actions in your repository
   - Run the "Promote from SIT to UAT" workflow
   - Enter the version to deploy
   - The workflow will:
     - Test in SIT first
     - Build and push Docker images
     - Deploy to Azure in US West region with Proximity Placement Group
     - Run verification tests

4. **Manual Deployment Option**:
   If you prefer to deploy manually:
   ```bash
   # 1. Login to Azure
   az login
   
   # 2. Run the UAT deployment script
   cd environments/uat
   ./setup.sh
   
   # 3. Verify the deployment
   cd tests
   pytest
   ```

For more detailed instructions, see the [Deployment Guide](docs/deployment/deployment_guide.md) and [UAT Environment Guide](environments/uat/README.md).

## Documentation

- [Architecture Documentation](docs/architecture/architecture_overview.md)
- [API Specification](docs/api/api_specification.md)
- [Deployment Guide](docs/deployment/deployment_guide.md)
- [Testing Strategy](docs/testing/testing_strategy.md)
- [Administrator Guide](docs/user-guides/admin_guide.md)
- [Mobile App User Guide](docs/user-guides/mobile_app_guide.md)

## Development

### Project Structure

```
rt-sentiment/
   services/
      data-acquisition/
      sentiment-analysis/
      data-tier/
      api/
      auth/
   ui/
      mobile/
      admin/
   infrastructure/
   environments/
      sit/
      uat/
   docs/
   scripts/
```

### Build and Test

Each service can be built and tested individually:

```bash
cd services/<service-name>
# Build the service
docker build -t <service-name> .
# Run tests
pytest tests/
```

For more information on development workflows, see the [Contributing Guide](CONTRIBUTING.md).

## Contributing

Please read the [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the API framework
- [Apache Iceberg](https://iceberg.apache.org/) for table management
- [Dremio](https://www.dremio.com/) for data virtualization
- [Flutter](https://flutter.dev/) for cross-platform UI development