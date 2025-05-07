# Sentimark Architecture Documentation

This directory contains comprehensive architecture documentation for the Sentimark project, organized into logical categories for easy navigation and reference.

## Directory Structure

- **overview/** - High-level architecture documents providing a comprehensive system view
- **data-tier/** - Database architecture, migration plans, and implementation details
- **ml-models/** - Machine learning models, data sources, and sentiment analysis implementation
- **deployment/** - Environment-specific deployment guides and procedures
- **infrastructure/** - Cloud infrastructure, resource provisioning, and configuration
- **cost-management/** - Cost analysis, optimization strategies, and budget controls
- **api/** - API design, specifications, and implementation details
- **project-planning/** - Strategic direction, roadmaps, and planning materials
- **phase-results/** - Implementation results from each project phase
- **notes/** - Miscellaneous notes and reference materials

## Getting Started

For newcomers to the project, we recommend starting with these key documents:

1. [Architecture Overview](overview/architecture_overview.md) - Core architecture document
2. [Market Analysis Project Overview](overview/market_analysis_project_overview.md) - Detailed trading sentiment analysis architecture
3. [Database Migration Plan](data-tier/database_migration_plan.md) - Dual-database architecture approach
4. [Phase Results](phase-results/) - Implementation results by project phase

## Documentation Standards

All architecture documentation should follow these standards:

1. **Clarity** - Documents should be clear, concise, and accessible to technical team members
2. **Completeness** - Include all relevant details while avoiding unnecessary verbosity
3. **Currency** - Documentation should be kept up-to-date with the actual implementation
4. **Cross-referencing** - Reference related documents to provide a complete picture
5. **Diagrams** - Use visual representations where appropriate to clarify complex concepts

## Architecture Principles

The Sentimark architecture is guided by these core principles:

1. **Performance** - Optimize for low latency in sentiment analysis operations
2. **Scalability** - Design for horizontal scaling to handle increased load
3. **Reliability** - Ensure high availability and fault tolerance
4. **Flexibility** - Support multiple database backends via abstraction layers
5. **Security** - Implement security by design at all architectural layers
6. **Cost-effectiveness** - Balance performance requirements with fiscal responsibility

## Contributing

When adding new architecture documentation:

1. Place files in the appropriate category directory
2. Follow the established naming conventions
3. Update relevant README.md files
4. Cross-reference related documents
5. Include diagrams for complex concepts

## Tools and Technologies

The Sentimark architecture leverages these core technologies:

- **Database**: PostgreSQL (development), Apache Iceberg (production)
- **Cloud**: Azure (AKS, Container Apps, Data Lake Storage)
- **ML**: FinBERT model for financial sentiment analysis
- **API**: FastAPI with async processing
- **Infrastructure**: Terraform for infrastructure as code
- **Containers**: Docker and Kubernetes for orchestration