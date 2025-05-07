# RT Sentiment Analysis - Architecture Overview

## System Architecture

This document provides an overview of the RT Sentiment Analysis system architecture, describing the main components, their interactions, and the overall system design.

## System Components

The RT Sentiment Analysis system consists of the following main components:

### Data Acquisition Service
- Responsible for gathering data from various sources
- Processes and normalizes incoming data
- Forwards data to the sentiment analysis pipeline

### Sentiment Analysis Service
- Analyzes text to determine sentiment
- Uses NLP models to extract sentiment scores
- Processes data in real-time

### Data Tier Service
- Manages data storage and retrieval
- Implements Iceberg for table management
- Uses Dremio for query execution

### API Service
- Provides REST and WebSocket endpoints
- Manages client connections
- Delivers real-time updates

### Auth Service
- Handles authentication and authorization
- Manages user sessions
- Controls access to protected resources

## Component Interactions

[Diagram to be added]

## Data Flow

1. Data is acquired from external sources via the Data Acquisition Service
2. Raw data is processed and sent to the Sentiment Analysis Service
3. Sentiment results are stored in the Data Tier Service
4. Results are made available through the API Service
5. Client applications consume the data via REST or WebSocket connections

## Deployment Architecture

The system is deployed in the following environments:

### SIT Environment (WSL)
- Local development and testing
- Docker Compose for service orchestration
- Local data storage

### UAT Environment (Azure)
- Cloud-based testing environment
- Azure managed services
- Terraform-based deployment

## Technology Stack

- Python FastAPI for backend services
- Flutter for client applications
- PostgreSQL for relational data
- Apache Iceberg for data lake management
- Dremio for data virtualization
- Docker for containerization
- Azure for cloud infrastructure

## Security Architecture

[To be completed]

## Performance Considerations

[To be completed]