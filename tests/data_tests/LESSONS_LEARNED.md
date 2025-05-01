# Lessons Learned: Sentiment Analysis Data Tier Setup

## Overview

This document captures the key insights and lessons learned during the implementation and setup of the sentiment analysis data tier using Dremio, JDBC, and Iceberg. These observations can help future implementations avoid common pitfalls and improve the setup process.

## Technical Challenges and Solutions

### 1. JDBC Connectivity from Python

**Challenge**: Establishing JDBC connections from Python to Dremio proved problematic due to issues with the Java bridge libraries.

**Observations**:
- JPype library consistently produced errors like "Can't find org.jpype.jar support library"
- Multiple JPype versions (1.4.1, 1.5.2) were attempted without success
- The error persisted despite correct CLASSPATH and JAVA_HOME configuration

**Solutions**:
- Use the REST API approach for testing connectivity and operations
- For production systems, consider:
  - Using PySpark with the Dremio connector instead of direct JDBC
  - Implementing a small Java service that handles JDBC operations
  - Using the Dremio Python client library if available
- Alternative Java/Python integration methods like py4j might work better than JPype

### 2. Docker Integration with WSL

**Challenge**: Running Docker containers in WSL requires specific configuration.

**Observations**:
- Docker commands failed with "command not found" errors initially
- Volume mounts have path translation issues between WSL and Windows

**Solutions**:
- Enable WSL integration in Docker Desktop settings
- Use absolute paths in volume mounts with the correct WSL format
- Restart Docker Desktop after changing integration settings
- Ensure Docker daemon is running before attempting any container operations

### 3. Environment Configuration Management

**Challenge**: Managing environment variables and dependencies across multiple components.

**Observations**:
- Different components require different environment variables
- Manual environment setup is error-prone and difficult to reproduce

**Solutions**:
- Created unified environment setup script (`setup_dremio_env.sh`)
- Used .env files for configuration that can be source controlled
- Documented all environment variables and their purposes
- Implemented automatic activation of virtual environments in scripts

## Best Practices Identified

### 1. Isolated Testing Environments

Creating isolated testing environments for each component helped identify integration issues:

- Separate test scripts for Dremio REST API connections
- Standalone JDBC driver tests 
- Individual environment setup scripts

### 2. Structured Setup Process

Breaking down the setup into distinct phases improved troubleshooting:

1. Infrastructure setup (Docker, network)
2. Python environment configuration
3. Java/JVM setup
4. Dremio configuration
5. Connection testing
6. Data validation

This structure made it easier to identify the source of problems when they occurred.

### 3. Layered Testing Approach

Testing connectivity at multiple layers proved invaluable:

- **Layer 1**: Basic infrastructure (Is Dremio running?)
- **Layer 2**: Authentication (Can we log in?)
- **Layer 3**: API access (Can we retrieve catalog data?)
- **Layer 4**: Data operations (Can we write/read data?)

When an issue occurred at one layer, we could focus troubleshooting efforts without being distracted by higher-level concerns.

## Architectural Insights

### 1. REST API vs. JDBC

The Dremio REST API proved more reliable for Python integration than JDBC:

- More consistent across environments
- Fewer dependencies (no JVM required)
- Simpler error handling
- Better documentation

For Python-based applications, the REST API should be considered the primary integration method, with JDBC as a fallback for specific use cases.

### 2. Container-Based Development

Using containerized Dremio for development offered several advantages:

- Consistent environment across team members
- Simple restart/reset capability
- Isolation from system-level changes
- Easy version control of configurations

## Future Improvements

### 1. Automated Environment Setup

A complete automation script that:
- Checks prerequisites
- Sets up all required components
- Configures environment variables
- Verifies connectivity
- Generates sample data

### 2. Connection Pooling

Implement proper connection pooling for production environments:
- Reduced connection overhead
- Better resource management
- Improved fault tolerance

### 3. CI/CD Pipeline Integration

Integrate Dremio testing into CI/CD pipelines:
- Automated testing of data tier functionality
- Validation of schema changes
- Performance testing of queries

## Common Pitfalls to Avoid

1. **Assuming JDBC Connectivity**: Don't assume JDBC will work seamlessly with Python - test early and have alternatives ready.

2. **Java Version Mismatch**: Ensure the Java version is compatible with both Dremio and the JDBC drivers.

3. **Ignoring Permissions**: Dremio container needs appropriate permissions to access mounted volumes.

4. **Complex Queries in Testing**: Start with simple queries during testing before moving to complex ones.

5. **Hard-Coded Credentials**: Avoid hard-coding credentials in scripts or code - use environment variables or secure stores.

## Learning Resources

These resources were particularly helpful during this implementation:

1. **Dremio Documentation**: Comprehensive guide to Dremio features and configuration
   - https://docs.dremio.com/

2. **Iceberg Project**: Apache Iceberg table format documentation
   - https://iceberg.apache.org/docs/latest/

3. **PyIceberg Documentation**: Python library for Apache Iceberg
   - https://py.iceberg.apache.org/

4. **Docker-WSL Integration Guide**: Helpful for resolving Docker-WSL issues
   - https://docs.docker.com/desktop/wsl/

5. **JPype Troubleshooting Guide**: Useful for Java-Python integration issues
   - https://jpype.readthedocs.io/en/latest/install.html#troubleshooting