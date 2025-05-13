# RT Sentiment Analysis - Project Restructuring Plan

This document outlines a comprehensive restructuring plan for the RT Sentiment Analysis system, focusing on clearer organization, environment separation, and improved infrastructure management.

## Goals of Restructuring

1. **Clear Service Separation** - Organize the codebase into distinct service boundaries
2. **Consistent Environment Strategy** - Separate SIT (System Integration Testing) in WSL and UAT (User Acceptance Testing) in Azure
3. **Improved Infrastructure Management** - Better organization of containerized components
4. **Enhanced UI Architecture** - Clearly separate mobile app client and admin web application
5. **Standardized Testing Approach** - Consistent test structure across all environments
6. **Better Documentation** - Clear documentation for each component and environment
7. **Simplified Deployment** - Streamlined deployment process for all environments

## New Directory Structure

```
rt-sentiment/
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── deployment/
│   ├── testing/
│   └── user-guides/
│
├── services/
│   ├── data-acquisition/           # Data acquisition service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── scrapers/
│   │   │   ├── subscription/
│   │   │   └── utils/
│   │   └── tests/
│   │
│   ├── sentiment-analysis/        # Sentiment analysis service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── models/
│   │   │   ├── event_consumers/
│   │   │   └── utils/
│   │   └── tests/
│   │
│   ├── data-tier/                 # Data storage and query service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── iceberg/
│   │   │   ├── writer/
│   │   │   ├── query/
│   │   │   ├── schema/
│   │   │   └── utils/
│   │   └── tests/
│   │
│   ├── api/                       # API service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   ├── models/
│   │   │   └── utils/
│   │   └── tests/
│   │
│   └── auth/                      # Authentication service
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── README.md
│       ├── src/
│       └── tests/
│
├── ui/
│   ├── mobile/                    # Flutter mobile app for clients
│   │   ├── README.md
│   │   ├── lib/
│   │   ├── test/
│   │   └── pubspec.yaml
│   │
│   └── admin/                     # Web app for admin dashboard
│       ├── README.md
│       ├── lib/
│       ├── test/
│       └── pubspec.yaml
│
├── infrastructure/
│   ├── docker-compose.yml         # Base composition for all services
│   ├── docker-compose.monitoring.yml  # Monitoring stack configuration
│   ├── docker-compose.dev.yml     # Local development overrides
│   ├── kubernetes/                # K8s manifests for production
│   │   ├── base/
│   │   └── overlays/
│   └── terraform/                 # Infrastructure as code
│       ├── azure/                 # Azure-specific configuration
│       └── local/                 # Local infrastructure setup
│
├── environments/
│   ├── sit/                       # System Integration Testing environment (WSL)
│   │   ├── README.md
│   │   ├── setup.sh
│   │   ├── config/
│   │   └── tests/
│   │
│   └── uat/                       # User Acceptance Testing environment (Azure)
│       ├── README.md
│       ├── setup.sh
│       ├── config/
│       └── tests/
│
├── scripts/
│   ├── setup/                     # Environment setup scripts
│   ├── migration/                 # Data migration utilities
│   ├── maintenance/               # System maintenance scripts
│   └── ci/                        # CI/CD pipeline scripts
│
└── tools/
    ├── data-tools/                # Data management utilities
    │   ├── deduplication/
    │   └── cleaning/
    │
    └── monitoring/                # Monitoring tools
        ├── grafana-dashboards/
        └── prometheus-config/
```

## Key Improvements

### 1. Service Isolation

Each service is isolated with its own directory, including:
- Source code in `/src`
- Service-specific tests
- Individual README with service documentation
- Dedicated Dockerfile and requirements.txt

### 2. Environment Separation

Clear separation between environments:
- `sit/` - System Integration Testing in WSL
- `uat/` - User Acceptance Testing in Azure
- Each environment has its own configuration and test scripts

### 3. UI Architecture

Distinct separation between:
- Client mobile application (Flutter)
- Admin web application (Flutter Web)
- Shared components where appropriate

### 4. Infrastructure Management

Improved organization of infrastructure:
- Base docker-compose for all services
- Environment-specific overrides
- Kubernetes manifests for production
- Terraform for infrastructure as code

### 5. Documentation Strategy

Comprehensive documentation approach:
- Architecture documentation
- API specifications
- Deployment guides
- Testing procedures
- User guides

## Migration Plan

### Phase 1: Initial Restructuring (2 weeks)

1. Create the new directory structure
2. Set up documentation framework
3. Move core services with minimal changes
4. Update docker-compose files

### Phase 2: Service Refactoring (3 weeks)

1. Refactor data acquisition service
2. Refactor sentiment analysis service
3. Refactor data tier service
4. Refactor API service
5. Refactor authentication service

### Phase 3: Environment Setup (2 weeks)

1. Set up SIT environment in WSL
2. Set up UAT environment in Azure
3. Create environment-specific tests
4. Test environment switching

### Phase 4: UI Separation (2 weeks)

1. Separate mobile app for clients
2. Develop admin web application
3. Set up shared components
4. Test UI in different environments

### Phase 5: Infrastructure Improvements (2 weeks)

1. Set up Kubernetes manifests
2. Implement Terraform configurations
3. Create CI/CD pipelines
4. Test deployment to all environments

## Testing Strategy

### Test Organization

Tests will be organized in a consistent structure across all services:

```
tests/
├── unit/               # Unit tests for individual components
├── integration/        # Integration tests between components
├── e2e/                # End-to-end tests
└── performance/        # Performance and load tests
```

### Environment-Specific Testing

Each environment (SIT, UAT) will have:
- Environment setup verification tests
- Service connectivity tests
- Data flow validation tests
- UI interaction tests

## Migration Verification

For each phase:
1. Run comprehensive test suite
2. Verify service functionality
3. Validate data consistency
4. Check performance metrics
5. Document any issues and resolutions

## Post-Migration Tasks

1. **Documentation Update**: Ensure all documentation reflects the new structure
2. **Training**: Provide team training on the new organization
3. **Cleanup**: Remove deprecated code and files
4. **Performance Verification**: Compare performance before and after restructuring

## Initial Implementation Steps

### 1. Create New Project Structure

```bash
# Create base directories
mkdir -p rt-sentiment/docs/{architecture,api,deployment,testing,user-guides}
mkdir -p rt-sentiment/services/{data-acquisition,sentiment-analysis,data-tier,api,auth}/{src,tests}
mkdir -p rt-sentiment/ui/{mobile,admin}
mkdir -p rt-sentiment/infrastructure/{kubernetes/{base,overlays},terraform/{azure,local}}
mkdir -p rt-sentiment/environments/{sit,uat}/{config,tests}
mkdir -p rt-sentiment/scripts/{setup,migration,maintenance,ci}
mkdir -p rt-sentiment/tools/{data-tools/{deduplication,cleaning},monitoring/{grafana-dashboards,prometheus-config}}

# Create base README files
touch rt-sentiment/README.md
touch rt-sentiment/CONTRIBUTING.md
touch rt-sentiment/LICENSE

# Create service-specific README files
for service in data-acquisition sentiment-analysis data-tier api auth; do
  touch rt-sentiment/services/$service/README.md
  touch rt-sentiment/services/$service/Dockerfile
  touch rt-sentiment/services/$service/requirements.txt
done

# Create environment setup scripts
touch rt-sentiment/environments/sit/setup.sh
touch rt-sentiment/environments/uat/setup.sh
touch rt-sentiment/environments/sit/README.md
touch rt-sentiment/environments/uat/README.md

# Create infrastructure files
touch rt-sentiment/infrastructure/docker-compose.yml
touch rt-sentiment/infrastructure/docker-compose.monitoring.yml
touch rt-sentiment/infrastructure/docker-compose.dev.yml
```

### 2. Begin Service Migration

Start with the most independent services first, then move to services with dependencies.

### 3. Configure Docker Compose

Update docker-compose.yml to reference the new directory structure, maintaining the same service connections.

### 4. Update Documentation

Begin updating the documentation to reflect the new structure and organization.

## Conclusion

This restructuring plan provides a clear path forward for organizing the RT Sentiment Analysis system into a more maintainable, scalable, and understandable architecture. The separation of concerns, clear environment boundaries, and improved documentation will make the system easier to work with for all stakeholders.

The modular approach allows for incremental migration, minimizing the risk of disruption while providing immediate benefits as each component is restructured.