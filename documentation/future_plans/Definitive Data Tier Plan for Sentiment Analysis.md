# **Definitive Data Tier Plan for Sentiment Analysis (v3)**

This document outlines the comprehensive implementation plan for transitioning from the current PostgreSQL/Parquet hybrid storage to an Iceberg lakehouse architecture accessed via Dremio CE, optimized for advanced sentiment analysis. **This version incorporates lessons learned and strategic adjustments following the completion of Phase 1, Phase 2, and Phase 3, with detailed planning for Phase 4 Azure migration.**

## **Table of Contents**

1. [Executive Summary](#executive-summary)  
2. [Current Architecture Overview](#current-architecture-overview)  
3. [Target Architecture](#target-architecture)  
4. [Advanced Schema Design](#advanced-schema-design)  
5. [Implementation Components](#implementation-components)  
6. [Implementation Plan](#implementation-plan)  
7. [Azure Migration Strategy](#azure-migration-strategy)  
8. [Operational Procedures](#operational-procedures)  
9. [Performance Considerations](#performance-considerations)  
10. [Monitoring and Maintenance](#monitoring-and-maintenance)  
11. [General Plan & Documentation Updates](#general-plan--documentation-updates)  
12. [Appendix: Code Samples](#appendix-code-samples)

## **Executive Summary**

The Real-Time Sentiment Analysis system currently uses a hybrid data storage approach combining PostgreSQL, Redis, and Parquet files. While functional, this approach has several limitations in terms of scalability, query performance, and schema evolution. This plan details the migration to an Iceberg lakehouse architecture that will address these limitations while enhancing analytical capabilities.

**Primary Benefits:**

* **Enhanced Analytical Capabilities**: Improved support for advanced sentiment fields and metadata  
* **Simplified Architecture**: Single source of truth with ACID transaction support  
* **Schema Evolution**: Flexible schema updates without data rewriting  
* **Performance Optimization**: Improved query performance through partition pruning and metadata indexing  
* **Operational Efficiency**: Streamlined maintenance procedures and monitoring
* **Cloud-Native Design**: Azure deployment with enterprise-grade reliability and scalability

## **Current Architecture Overview**

The current data tier consists of:

* **Parquet Files**: Primary storage for historical sentiment data, organized by ticker  
* **Redis Cache**: In-memory caching for real-time access to recent data  
* **PostgreSQL**: System state and configuration, with Foreign Data Wrapper (FDW) for querying Parquet

**Limitations include:**

* Complex architecture requiring synchronization across multiple systems  
* Limited schema evolution capabilities in Parquet files  
* Redundant storage and potential for data inconsistency  
* Performance bottlenecks for complex analytical queries  
* Maintenance overhead for multiple systems
* Scaling limitations for on-premise deployments

## **Target Architecture**

The target architecture will consolidate storage into an Iceberg lakehouse with:

```
┌────────────────┐     ┌──────────────┐     ┌─────────────┐  
│                │     │              │     │             │  
│  Data Sources  ├────►│ Iceberg Lake ├────►│ Dremio CE   │  
│  (e.g. Kafka)  │     │  (on Azure)  │     │             │  
└────────────────┘     └──────────────┘     └──────┬──────┘  
                                                  │  
                                                  ▼  
┌────────────────┐     ┌──────────────┐     ┌─────────────┐  
│                │     │              │     │             │  
│ Client Apps    │◄────┤ API Services │◄────┤ Redis Cache │  
│                │     │              │     │             │  
└────────────────┘     └──────────────┘     └─────────────┘
```

**This architecture provides:**

* A single source of truth for all sentiment data  
* ACID transaction support with snapshot isolation  
* Enhanced schema evolution capabilities  
* Optimized query performance through partition pruning  
* Seamless integration with existing Redis caching  
* SQL-based access through Dremio CE
* Cloud-native scalability on Azure

## **Advanced Schema Design**

The Iceberg schema will support enhanced sentiment analysis with these field categories:

### **Core Fields**

```python
# Basic Fields  
NestedField.required(1, "message_id", StringType()),  
NestedField.required(2, "event_timestamp", TimestampType.with_timezone()),  
NestedField.required(3, "ingestion_timestamp", TimestampType.with_timezone()),  
NestedField.required(4, "source_system", StringType()),  
NestedField.required(5, "text_content", StringType()),
```

### **Sentiment Analysis Fields**

```python
# Core Sentiment Fields  
NestedField.required(6, "sentiment_score", FloatType()),  
NestedField.required(7, "sentiment_magnitude", FloatType()),  
NestedField.required(8, "primary_emotion", StringType()),

# Advanced Sentiment Fields  
NestedField.optional(9, "emotion_intensity_vector",  
                     MapType.of(StringType(), FloatType())),  
NestedField.optional(10, "aspect_target_identification",  
                     ListType.of_required(StringType())),  
NestedField.optional(11, "aspect_based_sentiment",  
                     MapType.of(StringType(), FloatType())),  
NestedField.required(12, "sarcasm_detection", BooleanType()),  
NestedField.required(13, "subjectivity_score", FloatType()),  
NestedField.required(14, "toxicity_score", FloatType()),
```

### **Entity and Metadata Fields**

```python
# Entity Recognition  
NestedField.optional(15, "entity_recognition",  
                     ListType.of_required(  
                         StructType.of(  
                             NestedField.required(1, "text", StringType()),  
                             NestedField.required(2, "type", StringType())  
                         )  
                     )),

# Intent and Influence  
NestedField.required(16, "user_intent", StringType()),  
NestedField.optional(17, "influence_score", FloatType()),

# Metadata  
NestedField.required(18, "processing_version", StringType()),

# Financial Context  
NestedField.optional(19, "ticker", StringType()),  
NestedField.optional(20, "article_title", StringType()),  
NestedField.optional(21, "source_url", StringType()),  
NestedField.optional(22, "model_name", StringType()),
```

### **Partition Strategy**

```python
PartitionSpec(  
    PartitionField(source_id=2, field_id=100, transform=YearTransform(), name="year"),  
    PartitionField(source_id=2, field_id=101, transform=MonthTransform(), name="month"),  
    PartitionField(source_id=2, field_id=102, transform=DayTransform(), name="day"),  
    PartitionField(source_id=19, field_id=103, transform=IdentityTransform(), name="ticker"),  
    PartitionField(source_id=4, field_id=104, transform=IdentityTransform(), name="source_system")  
)
```

This partitioning strategy enables efficient data pruning for:

* Time-based queries (daily, monthly, yearly)  
* Ticker-specific queries  
* Source-specific queries

## **Implementation Components**

### **Iceberg Writer**

**(Note: Based on Phase 1 findings, the initial writer will target Dremio via JDBC/ODBC, deferring direct PyIceberg/REST writing.)**

The DremioJdbcWriter (or similar) will handle writing sentiment data to the Iceberg table via Dremio with these key features:

* **JDBC/ODBC Connection Management**  
* **Robust error handling** with automatic retries  
* **Schema validation** (implemented in the application layer before writing) to ensure data consistency  
* **Batch writing** using JDBC batch capabilities for performance optimization  
* **Default values** handled in the application layer  
* **Transaction support** leveraged through Dremio's capabilities

Key methods (Conceptual):

```python
def write_data_via_dremio(self, data: List[Dict[str, Any]]):  
    """Write a batch of sentiment data records to Iceberg via Dremio JDBC/ODBC."""

def write_sentiment_analysis_result_via_dremio(  
    self,  
    message_id: str,  
    text_content: str,  
    source_system: str,  
    analysis_result: Dict[str, Any],  
    ticker: Optional[str] = None,  
    article_title: Optional[str] = None,  
    source_url: Optional[str] = None,  
    model_name: Optional[str] = None  
):  
    """Write a single comprehensive sentiment analysis result via Dremio JDBC/ODBC."""
```

### **Dremio Query Layer**

The DremioSentimentQueryService will provide SQL-based access to sentiment data with these key features:

* **SQL query interface** for flexible data access  
* **Authentication and security** integration  
* **Result pagination** for handling large result sets  
* **Query optimization** through reflections  
* **Custom analytical views** for common sentiment queries  
* **Potential use of Dremio Binder API** for programmatic query generation

Key query methods:

```python
def get_sentiment_with_emotions(self, ticker, days=30):  
    """Get sentiment data including emotion analysis for a specific ticker."""

def get_entity_sentiment_analysis(self, ticker=None, entity_type=None, days=30):  
    """Get sentiment analysis broken down by entity."""

def get_aspect_based_sentiment(self, ticker, days=30):  
    """Get aspect-based sentiment analysis for a specific ticker."""

def get_toxicity_analysis(self, min_toxicity=0.5, days=30):  
    """Get potentially toxic content for moderation."""

def get_intent_distribution(self, ticker=None, days=30):  
    """Get distribution of user intents."""

def get_sentiment_time_series(self, ticker, interval='day', days=30):  
    """Get sentiment time series data with advanced metrics."""
```

### **Data Migration Utilities**

The ParquetToIcebergMigrator will handle data migration from existing Parquet files, writing via the chosen Dremio JDBC/ODBC method:

* **Parallel processing** for efficient migration  
* **Schema transformation** from old to new schema  
* **Data enrichment** for advanced sentiment fields  
* **Validation and verification** of migrated data  
* **Progress tracking** and detailed reporting  
* **Alignment with Dremio JDBC/ODBC writer** and target storage (Azure)

Key methods:

```python
def scan_parquet_files(self):  
    """Scan for Parquet files to migrate."""

def migrate_file(self, file_path):  
    """Migrate a single Parquet file to Iceberg via Dremio with enhanced fields."""

def migrate_all(self):  
    """Migrate all Parquet files to Iceberg via Dremio with parallel processing."""
```

### **Redis Integration**

The existing Redis cache will be integrated with the new Iceberg/Dremio architecture:

* **Cache invalidation** strategies based on Dremio/Iceberg updates (may require polling or event-driven approach)  
* **Parallel query execution** for cache warming via Dremio  
* **Custom serialization** for complex data types retrieved from Dremio  
* **Intelligent caching** based on query patterns  
* **Metrics collection** for cache hit/miss rates

## **Implementation Plan**

The implementation will proceed in five phases, incorporating adjustments based on Phase 1, Phase 2, and Phase 3.

### **Overall Strategic Adjustments (Post Phase 1)**

UPDATE Plan (1-2) Based on Phase 1 learnings:

1. **Prioritize Dremio Integration:** Reinforce the strategic shift suggested in (1.7) to focus development efforts on robust Dremio integration (queries, **ingestion via JDBC/ODBC**) before tackling the complexities of direct PyIceberg-to-REST catalog interactions, especially with S3/MinIO/Azure Blob Storage.  
2. **Phased Rollout of PyIceberg/REST:** Explicitly adopt the phased approach (1.7) for integrating the Iceberg REST catalog, potentially **deferring direct write paths via PyIceberg** until the core Dremio functionality is stable and validated. The REST catalog may still be used by Dremio itself.

### **Phase 1: Infrastructure Setup (1 day) - ✅ COMPLETED**

*(Details omitted for brevity - see original plan section 1.1-1.7)*

#### **1.5 Lessons Learned ✅**

*(Included for context)*

* **S3 Integration Challenges:** Connecting Iceberg REST service to S3-compatible storage (MinIO) requires careful configuration of S3FileIO parameters. Direct PyIceberg client-to-REST catalog integration with S3 was complex due to Hadoop dependencies.  
* **JDBC Configuration:** Iceberg REST catalog requires proper JDBC URI for SQLite backend (undocumented).  
* **Container Networking:** Explicit network configuration needed for service communication.  
* **Dremio Performance:** Resource-intensive; tuning memory is critical.  
* **Schema Compatibility:** PyIceberg 0.9.0 API requirements for complex types differ from docs.

#### **1.6 Installation Notes ✅**

*(Included for context)*

* **Prerequisites:** Docker, Docker Compose, Python 3.8+, ≥8GB RAM.  
* **Virtual Environment:** iceberg_venv with PyIceberg 0.9.0.  
* **Docker Images:** dremio/dremio-oss, minio/minio, tabulario/iceberg-rest.  
* **Ports:** 8181 (REST), 9047 (Dremio), 9000/9001 (MinIO).  
* **Startup Order:** MinIO -> Iceberg REST -> Dremio.  
* **Dremio Access:** dremio/dremio123.  
* **Local Storage:** Used for Phase 1 dev.  
* **Configuration:** Review CATALOG_WAREHOUSE.

#### **1.7 Advice for Next Steps ✅**

*(Included for context)*

* Focus on Dremio integration first.  
* Simplify Writer: Consider JDBC/ODBC to Dremio initially.  
* Use Binder API for programmatic SQL.  
* Prioritize Schema Validation.  
* Phased REST Integration.  
* Early Performance Testing.

### **Phase 2: Writer Implementation (1 week) - ✅ COMPLETED**

We've successfully completed Phase 2 of the data tier plan implementation. The key accomplishments include:

1. Implemented DremioJdbcWriter with robust connection management, error handling, and data validation
2. Resolved JDBC driver symlink handling issues to ensure reliable connections across environments
3. Created Kafka integration for streaming data to Dremio tables
4. Implemented rich schema validation and type conversion for all advanced sentiment fields
5. Developed end-to-end tests to verify the Kafka to Dremio data flow works correctly
6. Added verification with real data (not synthetic) as required by project guidelines

#### **2.1 Implement Writer via Dremio JDBC/ODBC ✅**

* **Decision:** Based on Phase 1 (1.5, 1.7), the initial writer will use JDBC/ODBC directly to Dremio. ✅  
* Develop writer component (DremioJdbcWriter or similar) using appropriate JDBC/ODBC library (e.g., pyodbc, jaydebeapi). ✅  
* Implement connection pooling, batch writing, and robust error handling/retry logic for JDBC/ODBC operations. ✅  
* Handle data type mapping between Python/Application and JDBC types. ✅

#### **2.1.1 Implement Application-Layer Schema Validation ✅**

* **Action:** Implement strong schema validation logic within the application layer *before* data is sent to the writer. ✅  
* Validate against the target Iceberg schema definition (field existence, types, nullability). ✅  
* Implement handling for default values and optional fields. ✅  
* Ensure validation covers all advanced sentiment fields. ✅

#### **2.2 Adapt Kafka Integration ✅**

* **Action:** Update Kafka consumers to prepare data according to the defined schema and pass it to the new DremioJdbcWriter. ✅  
* Ensure serialization/deserialization handles complex types correctly before validation and writing. ✅  
* Modify dual-write capability (if needed during transition) to target Dremio JDBC/ODBC instead of PyIceberg. ✅

#### **2.3 Sentiment Analysis Integration ✅**

* Extend sentiment analysis processors to generate all required fields for the advanced schema. ✅  
* Implement models or logic for advanced sentiment features (emotion vectors, aspect sentiment, etc.). ✅  
* Add validation and metrics collection within the analysis pipeline. ✅

#### **2.4 Automated Verification ✅**

* **Goal:** Implement automated scripts to verify the core infrastructure setup (Phase 1) and the data writing pipeline (Phase 2). ✅  
* **Tooling:** Utilize pytest for Python-based tests, shell scripts for basic infrastructure checks, Kafka client libraries (e.g., kafka-python), and JDBC/ODBC libraries (e.g., pyodbc) for Dremio interaction. ✅  
* **Infrastructure Verification (Phase 1 Checks):** ✅  
  * **Container Health:** Script to check if Dremio, MinIO (or Azure connection point), and Kafka Docker containers (if used) are running and healthy. ✅  
  * **Port Accessibility:** Script to verify required ports (9047 for Dremio, 9000/9001 for MinIO, Kafka ports) are listening. ✅  
  * **Dremio-Storage Connectivity:** Automated test using Dremio's API or JDBC to confirm Dremio can connect to the configured storage source (MinIO/Azure) where the Iceberg warehouse resides. ✅  
  * **Schema Initialization:** Query Dremio (via JDBC/ODBC) to verify the target Iceberg table exists and its schema matches the Advanced Schema Design. ✅  
* **Writer Pipeline Verification (Phase 2 Checks):** ✅  
  * **Unit Tests:** ✅  
    * Test the DremioJdbcWriter component in isolation, mocking the JDBC connection to verify SQL generation, batching logic, and error handling. ✅  
    * Test the application-layer schema validation logic with various valid and invalid inputs. ✅  
  * **Integration Tests:** ✅  
    * Test the Kafka consumer's ability to deserialize messages correctly. ✅  
    * Test the integration between the Kafka consumer and the schema validation logic. ✅  
    * Test the integration between the validated data processor and the DremioJdbcWriter, ensuring data flows correctly. ✅  
    * Test the DremioJdbcWriter's actual connection and writing capability to a test instance of Dremio connected to test storage. Verify successful writes and proper handling of JDBC errors. ✅  
  * **End-to-End Test:** ✅  
    * **Setup:** Ensure Kafka, Dremio, and storage are running. Clear or use a dedicated test Iceberg table. ✅  
    * **Action:** Publish a well-defined test message (including all core and advanced fields, edge cases like nulls, empty strings, complex types) to the relevant Kafka topic. ✅  
    * **Verification:** ✅  
      * Monitor Kafka consumer logs (optional) for successful processing. ✅  
      * Wait an appropriate amount of time for processing. ✅  
      * Query the target Iceberg table directly via Dremio (using a JDBC/ODBC connection in the test script). ✅  
      * Assert that the record exists in the table. ✅  
      * Assert that all fields in the retrieved record match the data sent in the test message, paying close attention to data types (timestamps, floats, maps, lists). ✅  
    * **Negative Test Case:** Send a message that violates the schema validation rules and verify it is *not* written to the Iceberg table (and potentially logged or sent to a dead-letter queue). ✅  

##### **2.4.1 Detailed How-To Guide for Verification**

The verification process involves multiple components working together. Follow these steps to run the end-to-end verification:

1. **JDBC Driver Setup**:
   * Run the improved setup script: `./scripts/setup_dremio_jdbc.sh`
   * The script now resolves symlink issues by using absolute paths with `os.path.abspath()`
   * Verify the driver works by checking the output: look for "✅ JDBC driver test PASSED"
   * Common issue: If the test fails, check that the JAR file exists and is a valid Java archive

2. **Verifying Kafka to Dremio Flow**:
   * Run: `python iceberg_lake/examples/kafka_to_dremio_test.py`
   * This test:
     - Creates a test table in Dremio with a unique name
     - Produces test messages to Kafka
     - Initializes the Kafka consumer that writes to Dremio
     - Verifies records were written correctly
   * Parameters:
     - `--kafka-broker` (default: localhost:9092): Kafka broker address
     - `--kafka-topic` (default: sentiment-data): Topic to use for testing
     - `--test-records` (default: 5): Number of test records to generate

3. **Verifying with Real Data**:
   * Run: `python verify_dremio_writer.py --ticker AAPL --max-records 10`
   * This script:
     - Loads real sentiment data from existing parquet files
     - Writes that data to Dremio via JDBC
     - Verifies the data was written correctly by querying it back
   * Parameters:
     - `--ticker` (default: AAPL): Ticker symbol to load data for
     - `--max-records` (default: 10): Maximum number of records to load
     - `--table-name` (optional): Custom table name (defaults to timestamped name)

4. **Common Issues and Solutions**:
   * **JDBC Driver Not Found**: 
     - Check that `drivers/dremio-jdbc-driver.jar` exists
     - Try running `scripts/setup_dremio_jdbc.sh` again to download it
   * **JVM Not Starting**: 
     - Verify Java is installed: `java -version`
     - Check that jpype1 is installed in your virtual environment
   * **Symlink Problems**: 
     - Always use absolute paths with `os.path.abspath()` when referencing JAR files
     - Avoid using symlinks directly in Java classpath arguments
   * **Connection Issues**: 
     - Verify Dremio is running: `docker ps | grep dremio`
     - Check Dremio credentials (default: dremio/dremio123)
     - Ensure port 31010 is accessible for JDBC connections

* **Execution:** Integrate these tests into a CI/CD pipeline or run them regularly in development/staging environments to ensure regressions are caught early. ✅

#### **2.5 Installation Notes ✅**

*(Added based on Phase 2 experience)*

* **Prerequisites:** Python 3.8+, JDK 8+, Dremio JDBC driver, PyIceberg 0.9.0
* **Virtual Environment:** Extended iceberg_venv to include jaydebeapi and jpype1 for JDBC connectivity
* **JDBC Driver Setup:** Run `scripts/setup_dremio_jdbc.sh` to download and set up the Dremio JDBC driver
* **JDBC Driver Location:** Dremio JDBC driver JAR must be placed in project root, drivers/ directory, or specified via jar_path
* **Packages:** Run `pip install jaydebeapi jpype1` in the virtual environment
* **Configuration:** DremioJdbcWriter requires proper connection details (host, port, credentials)
* **Ports:** JDBC connections use port 31010 (default Dremio JDBC port)
* **Verification:** Use test_dremio_jdbc_writer_test.py to verify driver and connection
* **Troubleshooting:** If JDBC connection fails, verify that the driver is properly installed and JVM is accessible

#### **2.6 Lessons Learned ✅**

*(Added based on Phase 2 experience)*

* **JDBC Driver Requirements:** Explicit inclusion of Dremio JDBC driver is required for JDBC connectivity. The driver must be properly placed in the classpath or specified directly.
* **Schema Complexity:** Complex data types (maps, lists) require special handling during JDBC serialization.
* **Error Handling:** Robust error handling and automatic retries are essential for reliable JDBC operations.
* **Batch Processing:** JDBC batch operations provide optimal performance for multiple records.
* **Integration Testing:** JDBC-specific testing infrastructure is needed for realistic integration tests.
* **Kafka Integration:** Both simulated and real Kafka interaction paths are necessary for testing environments.
* **Symlink Resolution:** JDBC driver validation fails when using symbolic links; absolute paths must be used to resolve symlinks correctly. Using os.path.abspath() solved this issue in the setup script.

#### **2.7 Advice for Next Steps ✅**

*(Added based on Phase 2 experience)*

* **Strengthen Functional Testing (CRITICAL)**: Implement more extensive JDBC-specific functional tests to prevent driver/connectivity issues:
  * Explicitly validate JDBC driver availability at startup and fail fast with clear error messages
  * Add extensive driver discovery logic to find JDBC drivers in various locations
  * Create dedicated verification scripts that test real database connectivity in isolation from business logic
  * Add pre-flight checks in production code that validate all dependencies before starting services
  * Implement automated startup checks that verify all required components (JVM, drivers, connections) are available
  * Add integration tests with real Dremio instance in CI environment using containerized dependencies
  * Create comprehensive test fixtures that simulate failure scenarios (missing driver, connection failures, schema mismatches)
* **Enhance Error Detection**: Improve logging and error detection in Kafka-to-Dremio pipeline:
  * Add robust validation checks at each stage of the pipeline
  * Implement circuit breakers for connectivity issues
  * Create monitoring dashboards for Dremio writes
* **Package JDBC Driver**: Include the JDBC driver with the deployment package:
  * Document steps to acquire the Dremio JDBC driver
  * Create scripts to download driver during setup
  * Consider containerizing the solution with driver included
* **Plan Monitoring**: Design monitoring for the Dremio data pipeline:
  * Record metrics for write latency, error rates, batch sizes
  * Set up alerts for JDBC connection failures
  * Monitor data consistency between source and destination

### **Phase 3: Query Layer Implementation (1 week) - ✅ COMPLETED**

We've successfully completed Phase 3 of the data tier plan implementation. The key accomplishments include:

1. Implemented the DremioSentimentQueryService with comprehensive query methods for all advanced sentiment analysis needs
2. Created a RESTful API service using FastAPI that exposes the query service functionality
3. Implemented extensive error handling and connection management for JDBC interactions
4. Added result caching for frequently executed queries to improve performance
5. Incorporated robust driver discovery and validation to prevent connection issues
6. Verified functionality with comprehensive test scripts against real data

#### **3.1 Dremio Configuration ✅**

* Set up Dremio sources pointing to the Iceberg table(s) in the target storage. ✅
* Created initial Dremio reflections for common query patterns identified. ✅
* Implemented security and access controls within Dremio. ✅

#### **3.2 Query API Development ✅**

* Developed DremioSentimentQueryService that interacts with Dremio via JDBC for SQL-based queries. ✅
* Implemented methods for all defined advanced sentiment queries including emotion analysis, entity sentiment, toxicity analysis, etc. ✅
* Added caching for query results to improve performance. ✅
* Implemented a RESTful API service using FastAPI that exposes the query service functionality. ✅

#### **3.3 Reporting Integration ✅**

* Updated integration points to allow existing dashboards to query the new Dremio-based system. ✅
* Created data access patterns for visualizing the advanced sentiment metrics. ✅
* Implemented structured JSON response formats for easy integration with reporting tools. ✅

#### **3.4 Dremio Tuning ✅**

* Addressed memory allocation and connection pool settings based on initial query patterns. ✅
* Optimized JDBC connection management with appropriate timeouts and retry logic. ✅
* Implemented robust driver discovery and validation to prevent connection issues. ✅

#### **3.5 Installation Notes ✅**

*(Added based on Phase 3 experience)*

* **Prerequisites:** Same as Phase 2 plus FastAPI and uvicorn for API service
* **API Service:** Run `python iceberg_lake/examples/start_sentiment_api.py` to start the API service on port 8000
* **API Documentation:** Auto-generated Swagger documentation at http://localhost:8000/docs when service is running
* **Testing:** Run `python iceberg_lake/examples/query_service_test.py` to verify query service functionality
* **Packages:** Run `pip install fastapi uvicorn pandas tabulate` in the virtual environment
* **Configuration:** Uses the same configuration as the DremioJdbcWriter from Phase 2

#### **3.6 Lessons Learned ✅**

*(Added based on Phase 3 experience)*

* **JDBC Query Performance:** Query response times are affected by Dremio's caching and reflection configuration
* **Complex Data Types:** JSON serialization and deserialization for complex types requires special handling
* **Error Propagation:** JDBC errors must be properly propagated and logged for effective debugging
* **API Design:** RESTful API design patterns with FastAPI provide clean interfaces for client integration
* **Connection Management:** Properly managing JDBC connections is critical for service stability
* **Query Parameterization:** Parameterized queries improve security and performance in JDBC interactions
* **Driver Discovery:** Robust driver discovery logic is essential for reliable JDBC connectivity

#### **3.7 SQL Dialect Compatibility and JDBC/JVM Approach**

*(Added based on UAT experience)*

* **SQL Dialect Considerations**: When working with Dremio's SQL dialect, be aware of these key differences:
  * **Information Schema**: Dremio's implementation of `INFORMATION_SCHEMA.TABLES` differs from standard SQL. Use Dremio's `sys.tables` instead or implement a try-catch approach for table existence checks.
  * **Table Creation**: Always use `CREATE TABLE IF NOT EXISTS` syntax to prevent errors when tables might already exist.
  * **Quoting Identifiers**: Dremio requires proper quoting of catalog, schema, and table names in SQL statements.
  * **Data Type Mappings**: Pay attention to Dremio's specific type mappings, especially for complex types like maps and arrays.

* **JDBC/JVM Configuration Requirements**:
  * **JVM Arguments**: Modern Java (9+) requires specific arguments to allow the Dremio JDBC driver access to internal APIs:
    ```
    --add-opens=java.base/java.lang=ALL-UNNAMED
    --add-opens=java.base/java.nio=ALL-UNNAMED
    --add-opens=java.base/java.util=ALL-UNNAMED
    --add-opens=java.base/java.io=ALL-UNNAMED
    ```
  * **Driver Discovery**: Implement robust JDBC driver discovery logic that checks multiple potential locations.
  * **Connection Management**: Use proper connection pooling and ensure connections are always closed after use.
  * **Error Handling**: Implement comprehensive error handling that gracefully manages JDBC exceptions.

* **Alternative Approaches**:
  * **REST API First**: For many operations, Dremio's REST API is more reliable and has fewer dependencies than JDBC.
  * **Binder API**: Consider using Dremio's Binder API for programmatic query generation if available.
  * **Native Java Service**: For critical production workloads, consider implementing JDBC operations in a separate Java service.

#### **3.8 User Acceptance Testing (UAT) Lessons Learned**

*(Added based on UAT experience)*

* **Documentation Importance**: 
  * **Comprehensive Documentation**: UAT revealed the critical need for thorough documentation covering all aspects of the system:
    * Detailed setup instructions with exact prerequisites and versions
    * Step-by-step troubleshooting guides for common issues
    * SQL compatibility details and differences from standard SQL
    * JDBC driver configuration requirements
    * Environment variable specifications
  * **Configuration Documentation**: Each configuration parameter must be documented with:
    * Purpose and impact
    * Valid values and constraints
    * Default values and when to change them
    * Example configurations for different environments

* **Tester Role Definition**:
  * **Clear Role Boundaries**: The UAT tester's role is to run tests and report results, not to modify code:
    * Tests should be executable without code modifications
    * All necessary scripts should be provided in advance
    * Environment setup should be fully automated or clearly documented
    * Test results should be captured in a standardized format
  * **Result Documentation**: Testers should document:
    * Environment details (OS, versions, etc.)
    * Exact steps executed
    * Expected versus actual results
    * Any error messages or unexpected behavior
    * Timestamps of test execution

* **Test Organization**:
  * **Test Structure**: Tests must be organized in our standard testing folder structure:
    * `/tests/data_tests/` for data tier specific tests
    * Clear naming convention (e.g., `test_dremio_connectivity.py`)
    * Test categories (unit, integration, e2e) in separate directories
    * Consistent argument format across test scripts
  * **Test Documentation**: Each test script should include:
    * Purpose of the test
    * Prerequisites and setup requirements
    * Expected outcomes and success criteria
    * Cleanup procedures
    * Known limitations or edge cases

* **Automated Verification**:
  * **Verification Scripts**: Provide scripts that automatically verify the environment and prerequisites
  * **Status Checks**: Include status check endpoints or commands that report on system health
  * **Self-Diagnosis**: Implement verbose logging and self-diagnostic capabilities
  * **Test Reports**: Generate structured test reports in a standardized format (e.g., JUnit XML)

## **Azure Migration Strategy**

### **Phase 4: Migration to Azure (2 weeks)**

The migration to Azure requires careful planning and execution to ensure data integrity, performance optimization, and minimal disruption to operations. Phase 4 will extend the existing Iceberg/Dremio implementation to leverage Azure's cloud infrastructure.

#### **4.1 Azure Infrastructure Setup**

* **Azure Blob Storage Configuration**:
  * Set up Azure Blob Storage account with ADLS Gen2 capabilities for Iceberg data
  * Configure appropriate storage tiers based on access patterns (hot/cool/archive)
  * Implement Azure-specific security controls including network security groups
  * Set up geo-replication for improved global performance and disaster recovery
  * Configure automated backup policies for critical data

* **Service Principal Authentication**:
  * Create dedicated service principal for non-interactive Dremio access to Azure resources
  * Configure RBAC permissions to ensure principle of least privilege
  * Set up secure credential management using environment variables or Azure Key Vault
  * Document clear rotation procedures for authentication credentials

* **Network Configuration**:
  * Establish secure network connectivity between application services and Azure
  * Configure VNet and subnet design for optimal security and performance
  * Set up private endpoints for Azure Blob Storage to enhance security
  * Implement proper DNS resolution for Azure resources

#### **4.2 Azure Integration with Dremio**

* **Dremio-Azure Connection**:
  * Configure Dremio to connect to Azure Blob Storage using the appropriate connection string
  * Set up authentication using the service principal credentials
  * Optimize connection parameters for performance in cloud environment
  * Implement proper error handling for Azure-specific connectivity issues

* **Performance Tuning for Azure**:
  * Increase JVM memory allocation for optimal query performance in cloud environment
  * Configure reflections specifically optimized for Azure Blob Storage patterns
  * Implement ZSV metadata for improved partitioning in cloud storage
  * Configure connection pooling and timeout settings appropriate for cloud access patterns

* **Monitoring Setup**:
  * Set up Azure Monitor for comprehensive resource monitoring
  * Create Dremio-specific performance dashboards
  * Configure alerting thresholds for critical operations
  * Implement cost monitoring and optimization

#### **4.3 Migration Utility Development**

* **Enhanced ParquetToIcebergMigrator Utility**:
  * Extend the existing utility to support Azure Blob Storage as the target
  * Implement batch processing with comprehensive validation at each step
  * Add detailed logging and progress tracking during migration
  * Implement schema transformation and enrichment for advanced sentiment fields
  * Integrate with monitoring systems for real-time migration status updates

* **Key Methods**:
  ```python
  def setup_azure_target_connection(self, connection_string, container_name):
      """Configure Azure Blob Storage as the target for migration."""
      
  def validate_azure_connectivity(self):
      """Verify connectivity to Azure Blob Storage and appropriate permissions."""
      
  def migrate_file_to_azure(self, file_path, batch_size=1000):
      """Migrate a single Parquet file to Iceberg on Azure with batched processing."""
      
  def verify_migration_integrity(self, source_file, target_table):
      """Validate data integrity between source Parquet and target Iceberg table."""
  ```

* **Validation Framework**:
  * Implement row count comparison between original and migrated data
  * Add statistical validation of numeric fields (min, max, avg, sum)
  * Include hash-based verification of text content
  * Add sample-based manual validation of critical records
  * Create validation reports in standardized format

#### **4.4 Incremental Migration Approach**

* **Batch Processing Strategy**:
  * Implement migration in manageable batches, starting with approximately 10% of data
  * Focus initial migration on non-critical historical data (oldest records first)
  * Schedule migration batches during off-peak hours
  * Establish clear success criteria for each migration batch

* **Dual-Write Implementation**:
  * Set up a dual-write mechanism to maintain continuous data flow during migration
  * Implement reconciliation process to ensure consistency between old and new systems
  * Create monitoring dashboards to track dual-write success rates
  * Document clear endpoint switch procedures for client applications

* **Rollback Planning**:
  * Define clear rollback triggers and procedures for each migration step
  * Create restore points before significant migration actions
  * Implement quick fallback mechanisms in case of migration issues
  * Document step-by-step recovery procedures for various failure scenarios

#### **4.5 Client Application Updates**

* **API Integration**:
  * Update API services to query the Azure-hosted Dremio/Iceberg system
  * Implement proper error handling for cloud-specific connectivity
  * Add connection resilience patterns (circuit breakers, retries)
  * Update documentation for API changes

* **Dashboard and Reporting Tools**:
  * Update integration points for existing dashboards
  * Test all reporting tools with the new Azure backend
  * Optimize query patterns for cloud-based data access
  * Document any performance changes or new features

#### **4.6 Phase 4 UAT Procedure**

* **UAT Testing Framework**:
  * Develop detailed testing scripts that are executable without code modifications
  * Create comprehensive validation procedures with clear pass/fail criteria
  * Document environment setup requirements for UAT testers
  * Provide automated verification tools for easy validation

* **Key UAT Scenarios**:
  * Migration validation tests (data integrity verification)
  * Query performance tests against Azure-hosted data
  * Failover and recovery testing
  * Security and access control verification
  * End-to-end functional validation

* **UAT Results Documentation**:
  * Standardized format for test results reporting
  * Clear tracking of all discovered issues
  * Resolution verification processes
  * Final acceptance criteria validation

### **Phase 5: Cutover (3 days)**

#### **5.1 Final Testing**

* Perform comprehensive end-to-end validation of data consistency between old and new systems (if applicable).  
* Run performance benchmarks against the Dremio/Iceberg system with representative workloads.  
* Verify all dependent applications and reporting tools function correctly against the new system.
* Execute disaster recovery simulations to validate recovery procedures.

#### **5.2 Cutover Execution**

* Schedule maintenance window.  
* Disable writers to the old PostgreSQL/Parquet system.  
* Complete final data synchronization/migration if needed.  
* Switch all read applications, APIs, and reporting tools to query the Dremio/Iceberg data tier.  
* Enable the primary writer targeting Dremio JDBC/ODBC.
* Implement progressive rollout to minimize risk, starting with non-critical components.

#### **5.3 Post-Cutover Optimization**

* Monitor system performance under full production load.  
* Refine Dremio reflections based on actual query patterns.  
* Optimize Iceberg table properties (e.g., compaction settings, file sizes) if needed.  
* Consider implementing Dremio materialized views for highly frequent or complex aggregations.
* Implement continuous performance monitoring and optimization.

#### **5.4 Schedule REST Catalog Integration Testing (Future)**

* **Action:** If the phased approach (1.7) is followed and direct PyIceberg-to-REST writing is pursued later, add specific integration testing tasks for these interactions in a subsequent optimization phase or project.

## **Operational Procedures**

### **Maintenance Tasks**

#### **1. Snapshot Management**  

* **Regular Cleanup**: Implement automated expiration of old snapshots based on retention policy
* **Metadata Compaction**: Schedule regular metadata file compaction to improve query performance
* **History Tracking**: Maintain snapshot history logging for audit and recovery purposes

#### **2. Compaction**  

* **Small Files Compaction**: Schedule regular compaction to merge small files into larger ones
* **Partition Optimization**: Implement partition-aware compaction for balanced file sizes
* **Monitoring**: Track file counts and sizes to trigger compaction when thresholds are reached

#### **3. Statistics Collection**

* **Column Statistics**: Generate and maintain column-level statistics for query optimization
* **Partition Statistics**: Collect partition-level statistics to improve partition pruning
* **Usage Analytics**: Track query patterns to inform optimization decisions

### **Backup and Recovery**

#### **1. Regular Backups**  

* **Azure Snapshots**: Configure regular Azure Blob Storage snapshots for point-in-time recovery
* **Catalog Backups**: Implement automated backups of Iceberg catalog metadata
* **Cross-Region Replication**: Set up geo-redundant storage for disaster recovery

#### **2. Disaster Recovery**

* **Recovery Testing**: Schedule regular recovery testing to validate procedures
* **RTO/RPO Objectives**: Define and monitor recovery time and point objectives
* **Failover Automation**: Implement automated failover procedures where possible

### **Monitoring**

#### **1. System Metrics**  

* **Resource Utilization**: Monitor CPU, memory, and storage utilization
* **Query Performance**: Track query latency, throughput, and error rates
* **Connection Pools**: Monitor JDBC connection pool utilization and health

#### **2. Data Quality**

* **Validation Checks**: Implement automated data quality validation
* **Schema Conformance**: Monitor schema evolution and compatibility
* **Anomaly Detection**: Implement statistical anomaly detection for incoming data

## **Performance Considerations**

### **Query Optimization**

#### **1. Partition Pruning**  

* **Partition Design**: Optimize partition strategy based on actual query patterns
* **Predicate Pushdown**: Ensure queries leverage partition pruning effectively
* **Metadata Caching**: Implement efficient metadata caching for improved partition pruning

#### **2. Metadata Management**  

* **Metadata Compaction**: Schedule regular metadata file compaction
* **Statistics Utilization**: Ensure query planning leverages available statistics
* **Metadata Caching**: Configure appropriate metadata caching policies

#### **3. Caching Strategy**

* **Dremio Reflections**: Configure and fine-tune Dremio reflections for common query patterns
* **Redis Integration**: Optimize Redis caching for frequently accessed data
* **Memory Allocation**: Tune memory allocation for optimal cache performance

### **Storage Optimization**

#### **1. Compression Settings**  

* **Algorithm Selection**: Choose appropriate compression algorithms based on query patterns
* **Compression Level**: Balance compression ratio and CPU overhead
* **Column-specific Settings**: Apply different compression settings based on data characteristics

#### **2. File Layout**

* **File Size Tuning**: Optimize target file sizes for balanced read performance
* **Data Clustering**: Implement data clustering for co-located access patterns
* **Sort Order**: Configure sort orders to improve compression and query efficiency

## **Monitoring and Maintenance**

### **Automated Maintenance**

#### **Script for Regular Maintenance**

```python
#!/usr/bin/env python3
"""
Iceberg Table Maintenance Script for Sentiment Analysis Data.

This script performs regular maintenance tasks on Iceberg tables:
1. Expire old snapshots based on retention policy
2. Remove orphaned files
3. Compact small files
4. Update statistics
"""
import logging
import argparse
import os
from datetime import datetime, timedelta

from iceberg_lake.maintenance import (
    expire_snapshots,
    remove_orphan_files,
    compact_data_files,
    update_statistics
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('iceberg-maintenance')

def main():
    parser = argparse.ArgumentParser(description='Iceberg Table Maintenance')
    parser.add_argument('--catalog-uri', required=True, help='Iceberg catalog URI')
    parser.add_argument('--warehouse', required=True, help='Warehouse location')
    parser.add_argument('--namespace', required=True, help='Table namespace')
    parser.add_argument('--table', required=True, help='Table name')
    parser.add_argument('--retention-days', type=int, default=90, 
                       help='Snapshot retention in days')
    parser.add_argument('--target-file-size-mb', type=int, default=512, 
                       help='Target file size for compaction in MB')
    args = parser.parse_args()
    
    start_time = datetime.now()
    logger.info(f"Starting maintenance for {args.namespace}.{args.table}")
    
    # Connect to the catalog
    catalog = connect_to_catalog(args.catalog_uri, args.warehouse)
    table = catalog.load_table(f"{args.namespace}.{args.table}")
    
    # 1. Expire snapshots older than retention period
    retention_timestamp = datetime.now() - timedelta(days=args.retention_days)
    snapshot_count = expire_snapshots(table, retention_timestamp)
    logger.info(f"Expired {snapshot_count} snapshots older than {retention_timestamp}")
    
    # 2. Remove orphaned files
    orphan_count = remove_orphan_files(table)
    logger.info(f"Removed {orphan_count} orphaned files")
    
    # 3. Compact small files
    compaction_count = compact_data_files(
        table, target_file_size_mb=args.target_file_size_mb
    )
    logger.info(f"Compacted {compaction_count} groups of small files")
    
    # 4. Update statistics
    stats_updated = update_statistics(table)
    logger.info(f"Updated statistics for {stats_updated} partitions")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Maintenance completed in {duration:.2f} seconds")

if __name__ == "__main__":
    main()
```

### **Metrics Collection**

#### **Prometheus Configuration for Dremio/Iceberg Monitoring**

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'dremio'
    static_configs:
      - targets: ['dremio:9090']
    metrics_path: '/metrics'
  
  - job_name: 'sentiment_service'
    static_configs:
      - targets: ['sentiment_service:8000']
    metrics_path: '/metrics'
  
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['node_exporter:9100']

  - job_name: 'iceberg_metrics'
    static_configs:
      - targets: ['iceberg_metrics:8080']
    metrics_path: '/metrics'

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - 'alertmanager:9093'

# Rules for Iceberg and Dremio metrics
rule_files:
  - 'iceberg_rules.yml'
  - 'dremio_rules.yml'
```

## **General Plan & Documentation Updates**

1. **Document Technical Findings:**  
   * **Action:** Add tasks (e.g., in an Appendix or dedicated documentation section) to record:  
     * The required JDBC URI configuration discovered for the Iceberg REST catalog/SQLite backend (1.5).  
     * The specific PyIceberg 0.9.0 API nuances encountered for complex types (Maps, Lists) requiring specific field IDs (1.5).  
     * Configuration details for connecting Dremio/Iceberg to Azure Blob Storage.  
     * Learnings regarding S3FileIO parameters for S3-compatible storage (MinIO/Azure).  
2. **Update Resource Requirements:**  
   * **Action:** Ensure infrastructure planning documents and deployment configurations clearly state the recommended RAM allocation for Dremio (minimum 8GB observed as critical in dev, potentially more needed for production workloads) based on findings (1.5).  
3. **Refine Risk Assessment:**  
   * **Action:** Update the project's risk register to include or update risks related to:  
     * Complexity of direct PyIceberg/REST/S3(Azure) integration, noting the mitigation strategy of prioritizing Dremio JDBC/ODBC writes initially.  
     * Dremio performance tuning requirements.  
     * Potential challenges in configuring Iceberg/Dremio with Azure Blob Storage.  
4. **Track Dependencies:**  
   * **Action:** Maintain a clear record of critical library versions used, particularly PyIceberg 0.9.0 (1.6) where compatibility issues arose. Document any specific workarounds or configurations required for this version. Consider potential compatibility testing if library upgrades are planned in the future.

## **Appendix: Code Samples**

### **Docker Compose Configuration**

*(Include YAML sample - Note: May need updates for Azure integration if run locally)*

### **API Usage Example**

**Query Service Example:**

```python
# Initialize the query service
from iceberg_lake.query.dremio_sentiment_query import DremioSentimentQueryService

query_service = DremioSentimentQueryService(
    dremio_host="localhost",
    dremio_port=31010,
    dremio_username="dremio",
    dremio_password="dremio123",
    catalog="DREMIO",
    namespace="sentiment",
    table_name="sentiment_data"
)

# Get sentiment data for a specific ticker
df = query_service.get_sentiment_with_emotions(ticker="AAPL", days=30)
print(f"Found {len(df)} records")

# Get time series data
ts_df = query_service.get_sentiment_time_series(ticker="AAPL", interval="day", days=30)
print(f"Time series data points: {len(ts_df)}")

# Clean up when done
query_service.close()
```

**API Client Example:**

```python
import requests
import json

# API base URL
base_url = "http://localhost:8000"

# Get top tickers by message volume
response = requests.get(f"{base_url}/sentiment/tickers?days=30&limit=10")
tickers_data = response.json()

print(f"Top {len(tickers_data['data'])} tickers:")
for ticker_data in tickers_data['data']:
    print(f"  {ticker_data['ticker']}: {ticker_data['message_count']} messages, " 
          f"avg sentiment: {ticker_data['avg_sentiment']:.2f}")

# Get sentiment time series for a specific ticker
ticker = tickers_data['data'][0]['ticker']  # Use the top ticker
response = requests.get(f"{base_url}/sentiment/timeseries?ticker={ticker}&interval=day&days=30")
timeseries_data = response.json()

print(f"\nSentiment time series for {ticker}:")
for point in timeseries_data['data'][:5]:  # Show first 5 data points
    print(f"  {point['time_bucket']}: {point['avg_sentiment']:.2f}, "
          f"messages: {point['message_count']}")
```

**Azure Blob Storage Configuration Example:**

```python
# Azure Storage Configuration for Dremio
from azure.storage.blob import BlobServiceClient

def configure_azure_blob_storage(
    connection_string: str,
    container_name: str,
    folder_path: str
) -> str:
    """
    Configure Azure Blob Storage for Iceberg tables.
    
    Args:
        connection_string: Azure Storage connection string
        container_name: Azure Storage container name
        folder_path: Path within the container for Iceberg data
        
    Returns:
        Storage location URI for Dremio configuration
    """
    # Create the BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    # Check if container exists, create if not
    try:
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client = blob_service_client.create_container(container_name)
            print(f"Created container: {container_name}")
        else:
            print(f"Container {container_name} already exists")
    except Exception as e:
        print(f"Error creating/accessing container: {str(e)}")
        raise
    
    # Create the folder path if it doesn't exist (represented as a blob with empty content)
    if folder_path and not folder_path.endswith('/'):
        folder_path += '/'
    
    marker_blob_name = f"{folder_path}.iceberg_ready"
    blob_client = container_client.get_blob_client(marker_blob_name)
    
    if not blob_client.exists():
        blob_client.upload_blob(b"", overwrite=True)
        print(f"Created marker blob: {marker_blob_name}")
    
    # Return the storage location URI for Dremio configuration
    # Format: abfss://<container>@<account>.dfs.core.windows.net/<path>
    account_name = blob_service_client.account_name
    storage_location = f"abfss://{container_name}@{account_name}.dfs.core.windows.net/{folder_path}"
    
    print(f"Configured storage location: {storage_location}")
    return storage_location
```

This updated plan incorporates the key findings from the Comprehensive Phase 4 Implementation Guidelines, with a specific focus on the Azure migration strategy, validation requirements, and enhanced operational procedures.