# **Definitive Data Tier Plan for Sentiment Analysis (v2 \- Updated Post Phase 1\)**

This document outlines the comprehensive implementation plan for transitioning from the current PostgreSQL/Parquet hybrid storage to an Iceberg lakehouse architecture accessed via Dremio CE, optimized for advanced sentiment analysis. **This version incorporates lessons learned and strategic adjustments following the completion of Phase 1\.**

## **Table of Contents**

1. [Executive Summary](#bookmark=id.59o3tyr4me12)  
2. [Current Architecture Overview](#bookmark=id.5rio621m7t0s)  
3. [Target Architecture](#bookmark=id.79svokqsyo84)  
4. [Advanced Schema Design](#bookmark=id.v7i1wyg5vnbx)  
5. [Implementation Components](#bookmark=id.yvo3u6cf15zs)  
   * [Iceberg Writer](#bookmark=id.tylei76dosbg)  
   * [Dremio Query Layer](#bookmark=id.7z7zsovqxmbb)  
   * [Data Migration Utilities](#bookmark=id.nj8e4y104v3e)  
   * [Redis Integration](#bookmark=id.63fqgbntje0o)  
6. [Implementation Plan](#bookmark=id.o6o52dn8v5h6)  
   * [Overall Strategic Adjustments (Post Phase 1\)](#bookmark=id.jztwgk2gxto)  
   * [Phase 1: Infrastructure Setup (Completed)](#bookmark=id.e4wviffekq5l)  
   * [Phase 2: Writer Implementation (Updated)](#bookmark=id.os6jyz5f7g5l)  
   * [Phase 3: Query Layer Implementation (Updated)](#bookmark=id.1pu1ki2cy7nf)  
   * [Phase 4: Migration (Updated)](#bookmark=id.30k92kbr1drg)  
   * [Phase 5: Cutover (Updated)](#bookmark=id.aismaq63s0h3)  
7. [Operational Procedures](#bookmark=id.ouiumhtdoazy)  
8. [Performance Considerations](#bookmark=id.vea4dl8zminm)  
9. [Monitoring and Maintenance](#bookmark=id.2x8bxhgs8bbw)  
10. [General Plan & Documentation Updates (Post Phase 1\)](#bookmark=id.8qmwrn2w6y8u)  
11. [Appendix: Code Samples](#bookmark=id.jkiy2sebtthh)

## **Executive Summary**

The Real-Time Sentiment Analysis system currently uses a hybrid data storage approach combining PostgreSQL, Redis, and Parquet files. While functional, this approach has several limitations in terms of scalability, query performance, and schema evolution. This plan details the migration to an Iceberg lakehouse architecture that will address these limitations while enhancing analytical capabilities.

**Primary Benefits:**

* **Enhanced Analytical Capabilities**: Improved support for advanced sentiment fields and metadata  
* **Simplified Architecture**: Single source of truth with ACID transaction support  
* **Schema Evolution**: Flexible schema updates without data rewriting  
* **Performance Optimization**: Improved query performance through partition pruning and metadata indexing  
* **Operational Efficiency**: Streamlined maintenance procedures and monitoring

## **Current Architecture Overview**

The current data tier consists of:

* **Parquet Files**: Primary storage for historical sentiment data, organized by ticker  
* **Redis Cache**: In-memory caching for real-time access to recent data  
* **PostgreSQL**: System state and configuration, with Foreign Data Wrapper (FDW) for querying Parquet

Limitations include:

* Complex architecture requiring synchronization across multiple systems  
* Limited schema evolution capabilities in Parquet files  
* Redundant storage and potential for data inconsistency  
* Performance bottlenecks for complex analytical queries  
* Maintenance overhead for multiple systems

## **Target Architecture**

The target architecture will consolidate storage into an Iceberg lakehouse with:

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

This architecture provides:

* A single source of truth for all sentiment data  
* ACID transaction support with snapshot isolation  
* Enhanced schema evolution capabilities  
* Optimized query performance through partition pruning  
* Seamless integration with existing Redis caching  
* SQL-based access through Dremio CE

## **Advanced Schema Design**

The Iceberg schema will support enhanced sentiment analysis with these field categories:

### **Core Fields**

\# Basic Fields  
NestedField.required(1, "message\_id", StringType()),  
NestedField.required(2, "event\_timestamp", TimestampType.with\_timezone()),  
NestedField.required(3, "ingestion\_timestamp", TimestampType.with\_timezone()),  
NestedField.required(4, "source\_system", StringType()),  
NestedField.required(5, "text\_content", StringType()),

### **Sentiment Analysis Fields**

\# Core Sentiment Fields  
NestedField.required(6, "sentiment\_score", FloatType()),  
NestedField.required(7, "sentiment\_magnitude", FloatType()),  
NestedField.required(8, "primary\_emotion", StringType()),

\# Advanced Sentiment Fields  
NestedField.optional(9, "emotion\_intensity\_vector",  
                     MapType.of(StringType(), FloatType())),  
NestedField.optional(10, "aspect\_target\_identification",  
                     ListType.of\_required(StringType())),  
NestedField.optional(11, "aspect\_based\_sentiment",  
                     MapType.of(StringType(), FloatType())),  
NestedField.required(12, "sarcasm\_detection", BooleanType()),  
NestedField.required(13, "subjectivity\_score", FloatType()),  
NestedField.required(14, "toxicity\_score", FloatType()),

### **Entity and Metadata Fields**

\# Entity Recognition  
NestedField.optional(15, "entity\_recognition",  
                     ListType.of\_required(  
                         StructType.of(  
                             NestedField.required(1, "text", StringType()),  
                             NestedField.required(2, "type", StringType())  
                         )  
                     )),

\# Intent and Influence  
NestedField.required(16, "user\_intent", StringType()),  
NestedField.optional(17, "influence\_score", FloatType()),

\# Metadata  
NestedField.required(18, "processing\_version", StringType()),

\# Financial Context  
NestedField.optional(19, "ticker", StringType()),  
NestedField.optional(20, "article\_title", StringType()),  
NestedField.optional(21, "source\_url", StringType()),  
NestedField.optional(22, "model\_name", StringType()),

### **Partition Strategy**

To optimize query performance, particularly for ticker and time-based queries, we'll implement this partition specification:

PartitionSpec(  
    PartitionField(source\_id=2, field\_id=100, transform=YearTransform(), name="year"),  
    PartitionField(source\_id=2, field\_id=101, transform=MonthTransform(), name="month"),  
    PartitionField(source\_id=2, field\_id=102, transform=DayTransform(), name="day"),  
    PartitionField(source\_id=19, field\_id=103, transform=IdentityTransform(), name="ticker"),  
    PartitionField(source\_id=4, field\_id=104, transform=IdentityTransform(), name="source\_system")  
)

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

def write\_data\_via\_dremio(self, data: List\[Dict\[str, Any\]\]):  
    """Write a batch of sentiment data records to Iceberg via Dremio JDBC/ODBC."""

def write\_sentiment\_analysis\_result\_via\_dremio(  
    self,  
    message\_id: str,  
    text\_content: str,  
    source\_system: str,  
    analysis\_result: Dict\[str, Any\],  
    ticker: Optional\[str\] \= None,  
    article\_title: Optional\[str\] \= None,  
    source\_url: Optional\[str\] \= None,  
    model\_name: Optional\[str\] \= None  
):  
    """Write a single comprehensive sentiment analysis result via Dremio JDBC/ODBC."""

### **Dremio Query Layer**

The DremioSentimentQueryService will provide SQL-based access to sentiment data with these key features:

* **SQL query interface** for flexible data access  
* **Authentication and security** integration  
* **Result pagination** for handling large result sets  
* **Query optimization** through reflections  
* **Custom analytical views** for common sentiment queries  
* **Potential use of Dremio Binder API** for programmatic query generation

Key query methods:

def get\_sentiment\_with\_emotions(self, ticker, days=30):  
    """Get sentiment data including emotion analysis for a specific ticker."""

def get\_entity\_sentiment\_analysis(self, ticker=None, entity\_type=None, days=30):  
    """Get sentiment analysis broken down by entity."""

def get\_aspect\_based\_sentiment(self, ticker, days=30):  
    """Get aspect-based sentiment analysis for a specific ticker."""

def get\_toxicity\_analysis(self, min\_toxicity=0.5, days=30):  
    """Get potentially toxic content for moderation."""

def get\_intent\_distribution(self, ticker=None, days=30):  
    """Get distribution of user intents."""

def get\_sentiment\_time\_series(self, ticker, interval='day', days=30):  
    """Get sentiment time series data with advanced metrics."""

### **Data Migration Utilities**

The ParquetToIcebergMigrator will handle data migration from existing Parquet files, writing via the chosen Dremio JDBC/ODBC method:

* **Parallel processing** for efficient migration  
* **Schema transformation** from old to new schema  
* **Data enrichment** for advanced sentiment fields  
* **Validation and verification** of migrated data  
* **Progress tracking** and detailed reporting  
* **Alignment with Dremio JDBC/ODBC writer** and target storage (Azure)

Key methods:

def scan\_parquet\_files(self):  
    """Scan for Parquet files to migrate."""

def migrate\_file(self, file\_path):  
    """Migrate a single Parquet file to Iceberg via Dremio with enhanced fields."""

def migrate\_all(self):  
    """Migrate all Parquet files to Iceberg via Dremio with parallel processing."""

### **Redis Integration**

The existing Redis cache will be integrated with the new Iceberg/Dremio architecture:

* **Cache invalidation** strategies based on Dremio/Iceberg updates (may require polling or event-driven approach)  
* **Parallel query execution** for cache warming via Dremio  
* **Custom serialization** for complex data types retrieved from Dremio  
* **Intelligent caching** based on query patterns  
* **Metrics collection** for cache hit/miss rates

## **Implementation Plan**

The implementation will proceed in five phases, incorporating adjustments based on Phase 1\.

### **Overall Strategic Adjustments (Post Phase 1\)**

UPDATE Plan (1-2) Based on Phase 1 learnings:

1. **Prioritize Dremio Integration:** Reinforce the strategic shift suggested in (1.7) to focus development efforts on robust Dremio integration (queries, **ingestion via JDBC/ODBC**) before tackling the complexities of direct PyIceberg-to-REST catalog interactions, especially with S3/MinIO/Azure Blob Storage.  
2. **Phased Rollout of PyIceberg/REST:** Explicitly adopt the phased approach (1.7) for integrating the Iceberg REST catalog, potentially **deferring direct write paths via PyIceberg** until the core Dremio functionality is stable and validated. The REST catalog may still be used by Dremio itself.

### **Phase 1: Infrastructure Setup (1 day) \- ✅ COMPLETED**

*(Details omitted for brevity \- see original plan section 1.1-1.7)*

#### **1.5 Lessons Learned ✅**

*(Included for context)*

* S3 Integration Challenges: Connecting Iceberg REST service to S3-compatible storage (MinIO) requires careful configuration of S3FileIO parameters. Direct PyIceberg client-to-REST catalog integration with S3 was complex due to Hadoop dependencies.  
* JDBC Configuration: Iceberg REST catalog requires proper JDBC URI for SQLite backend (undocumented).  
* Container Networking: Explicit network configuration needed for service communication.  
* Dremio Performance: Resource-intensive; tuning memory is critical.  
* Schema Compatibility: PyIceberg 0.9.0 API requirements for complex types differ from docs.

#### **1.6 Installation Notes ✅**

*(Included for context)*

* Prerequisites: Docker, Docker Compose, Python 3.8+, \>=8GB RAM.  
* Virtual Environment: iceberg\_venv with PyIceberg 0.9.0.  
* Docker Images: dremio/dremio-oss, minio/minio, tabulario/iceberg-rest.  
* Ports: 8181 (REST), 9047 (Dremio), 9000/9001 (MinIO).  
* Startup Order: MinIO \-\> Iceberg REST \-\> Dremio.  
* Dremio Access: dremio/dremio123.  
* Local Storage: Used for Phase 1 dev.  
* Configuration: Review CATALOG\_WAREHOUSE.

#### **1.7 Advice for Next Steps ✅**

*(Included for context)*

* Focus on Dremio integration first.  
* Simplify Writer: Consider JDBC/ODBC to Dremio initially.  
* Use Binder API for programmatic SQL.  
* Prioritize Schema Validation.  
* Phased REST Integration.  
* Early Performance Testing.

### **Phase 2: Writer Implementation (1 week \- Updated)**

#### **2.1 Implement Writer via Dremio JDBC/ODBC (UPDATE Plan)**

* **Decision:** Based on Phase 1 (1.5, 1.7), the initial writer will use JDBC/ODBC directly to Dremio.  
* Develop writer component (DremioJdbcWriter or similar) using appropriate JDBC/ODBC library (e.g., pyodbc, jaydebeapi).  
* Implement connection pooling, batch writing, and robust error handling/retry logic for JDBC/ODBC operations.  
* Handle data type mapping between Python/Application and JDBC types.

#### **2.1.1 Implement Application-Layer Schema Validation (UPDATE Plan \- New Task)**

* **Action:** Implement strong schema validation logic within the application layer *before* data is sent to the writer.  
* Validate against the target Iceberg schema definition (field existence, types, nullability).  
* Implement handling for default values and optional fields.  
* Ensure validation covers all advanced sentiment fields.

#### **2.2 Adapt Kafka Integration (UPDATE Plan)**

* **Action:** Update Kafka consumers to prepare data according to the defined schema and pass it to the new DremioJdbcWriter.  
* Ensure serialization/deserialization handles complex types correctly before validation and writing.  
* Modify dual-write capability (if needed during transition) to target Dremio JDBC/ODBC instead of PyIceberg.

#### **2.3 Sentiment Analysis Integration**

* Extend sentiment analysis processors to generate all required fields for the advanced schema.  
* Implement models or logic for advanced sentiment features (emotion vectors, aspect sentiment, etc.).  
* Add validation and metrics collection within the analysis pipeline.

#### **2.4 Automated Verification (Phase 1 & 2\) (NEW SECTION)**

* **Goal:** Implement automated scripts to verify the core infrastructure setup (Phase 1\) and the data writing pipeline (Phase 2).  
* **Tooling:** Utilize pytest for Python-based tests, shell scripts for basic infrastructure checks, Kafka client libraries (e.g., kafka-python), and JDBC/ODBC libraries (e.g., pyodbc) for Dremio interaction.  
* **Infrastructure Verification (Phase 1 Checks):**  
  * **Container Health:** Script to check if Dremio, MinIO (or Azure connection point), and Kafka Docker containers (if used) are running and healthy.  
  * **Port Accessibility:** Script to verify required ports (9047 for Dremio, 9000/9001 for MinIO, Kafka ports) are listening.  
  * **Dremio-Storage Connectivity:** Automated test using Dremio's API or JDBC to confirm Dremio can connect to the configured storage source (MinIO/Azure) where the Iceberg warehouse resides.  
  * **Schema Initialization:** Query Dremio (via JDBC/ODBC) to verify the target Iceberg table exists and its schema matches the Advanced Schema Design.  
* **Writer Pipeline Verification (Phase 2 Checks):**  
  * **Unit Tests:**  
    * Test the DremioJdbcWriter component in isolation, mocking the JDBC connection to verify SQL generation, batching logic, and error handling.  
    * Test the application-layer schema validation logic with various valid and invalid inputs.  
  * **Integration Tests:**  
    * Test the Kafka consumer's ability to deserialize messages correctly.  
    * Test the integration between the Kafka consumer and the schema validation logic.  
    * Test the integration between the validated data processor and the DremioJdbcWriter, ensuring data flows correctly.  
    * Test the DremioJdbcWriter's actual connection and writing capability to a test instance of Dremio connected to test storage. Verify successful writes and proper handling of JDBC errors.  
  * **End-to-End Test:**  
    * **Setup:** Ensure Kafka, Dremio, and storage are running. Clear or use a dedicated test Iceberg table.  
    * **Action:** Publish a well-defined test message (including all core and advanced fields, edge cases like nulls, empty strings, complex types) to the relevant Kafka topic.  
    * **Verification:**  
      * Monitor Kafka consumer logs (optional) for successful processing.  
      * Wait an appropriate amount of time for processing.  
      * Query the target Iceberg table directly via Dremio (using a JDBC/ODBC connection in the test script).  
      * Assert that the record exists in the table.  
      * Assert that all fields in the retrieved record match the data sent in the test message, paying close attention to data types (timestamps, floats, maps, lists).  
    * **Negative Test Case:** Send a message that violates the schema validation rules and verify it is *not* written to the Iceberg table (and potentially logged or sent to a dead-letter queue).  
* **Execution:** Integrate these tests into a CI/CD pipeline or run them regularly in development/staging environments to ensure regressions are caught early.

### **Phase 3: Query Layer Implementation (1 week \- Updated)**

#### **3.1 Dremio Configuration**

* Set up Dremio sources pointing to the Iceberg table(s) in the target storage (initially MinIO, later Azure).  
* Create initial Dremio reflections for common query patterns identified.  
* Implement security and access controls within Dremio.

#### **3.2 Query API Development (UPDATE Plan)**

* Develop REST API (DremioSentimentQueryService) for the query service, interacting with Dremio via JDBC/ODBC or potentially Dremio's REST API.  
* Implement methods for all defined advanced sentiment queries.  
* Add caching (e.g., Redis integration) and performance optimization measures.  
* **Action:** Add an investigation task to evaluate the suitability of Dremio's Binder API (1.7) for programmatic SQL generation, especially for complex/dynamic queries, and potentially incorporate it.

#### **3.3 Reporting Integration**

* Update existing dashboards (e.g., Grafana, Tableau) to query Dremio instead of the old system.  
* Create new visualizations for the advanced sentiment metrics.  
* Implement alerting based on insights derived from Dremio queries.

#### **3.4 Allocate Dremio Tuning Time (UPDATE Plan \- New Task)**

* **Action:** Schedule dedicated time within this phase or Phase 5 for Dremio performance tuning based on initial load and query patterns.  
* Address memory allocation (based on 1.5), reflection optimization, and other performance parameters.

### **Phase 4: Migration (1 week \- Updated)**

#### **4.1 Migration Utility Development (UPDATE Plan)**

* Develop the ParquetToIcebergMigrator utility.  
* Implement logic to read Parquet files, transform data to the new advanced schema, and enrich missing fields.  
* Ensure the utility writes data using the chosen DremioJdbcWriter.  
* Add robust validation, error handling, and progress reporting.  
* **Action:** Add a validation step to confirm the migration utility correctly interacts with the Dremio JDBC/ODBC writer and the target storage backend (Azure).

#### **4.2 Address Target Storage Configuration & Incremental Migration (UPDATE Plan)**

* **UPDATE Plan production target is Azure:** **Recommendation:** Explicitly plan for the transition from the local file system (Phase 1 dev) to the production target storage on **Azure** (e.g., Azure Blob Storage with ADLS Gen2 capabilities).  
* **Action:** Add specific sub-tasks for configuring, testing, and validating necessary connection parameters (e.g., S3FileIO parameters if using S3 compatibility layer, or Azure-specific connectors/credentials recognized by Dremio/Iceberg) for Azure Blob Storage within the migration process and potentially the writer configuration.  
* Migrate historical data from Parquet to Iceberg (via Dremio) in manageable batches.  
* Validate data integrity and consistency after each batch migration.  
* Monitor system performance (Dremio, Azure storage, network) during migration.

#### **4.3 Dual-Write Period**

* If necessary, implement a dual-writing period where new data goes to both the old system and the new Iceberg table via Dremio.  
* Create and run reconciliation processes to identify and resolve any discrepancies.  
* Monitor for divergence and ensure stability.

### **Phase 5: Cutover (3 days \- Updated)**

#### **5.1 Final Testing**

* Perform comprehensive end-to-end validation of data consistency between old and new systems (if applicable).  
* Run performance benchmarks against the Dremio/Iceberg system with representative workloads.  
* Verify all dependent applications and reporting tools function correctly against the new system.

#### **5.2 Cutover Execution**

* Schedule maintenance window.  
* Disable writers to the old PostgreSQL/Parquet system.  
* Complete final data synchronization/migration if needed.  
* Switch all read applications, APIs, and reporting tools to query the Dremio/Iceberg data tier.  
* Enable the primary writer targeting Dremio JDBC/ODBC.

#### **5.3 Post-Cutover Optimization**

* Monitor system performance under full production load.  
* Refine Dremio reflections based on actual query patterns.  
* Optimize Iceberg table properties (e.g., compaction settings, file sizes) if needed.  
* Consider implementing Dremio materialized views for highly frequent or complex aggregations.

#### **5.4 Schedule REST Catalog Integration Testing (Future) (UPDATE Plan \- New Task)**

* **Action:** If the phased approach (1.7) is followed and direct PyIceberg-to-REST writing is pursued later, add specific integration testing tasks for these interactions in a subsequent optimization phase or project.

## **Operational Procedures**

*(Content remains largely the same as original plan \- sections 7.1, 7.2, 7.3)*

### **Maintenance Tasks**

1. **Snapshot Management**  
2. **Compaction**  
3. **Statistics Collection**

### **Backup and Recovery**

1. **Regular Backups**  
2. **Disaster Recovery**

### **Monitoring**

1. **System Metrics**  
2. **Data Quality**

## **Performance Considerations**

*(Content remains largely the same as original plan \- sections 8.1, 8.2)*

### **Query Optimization**

1. **Partition Pruning**  
2. **Metadata Management**  
3. **Caching Strategy**

### **Storage Optimization**

1. **Compression Settings**  
2. **File Layout**

## **Monitoring and Maintenance**

*(Content remains largely the same as original plan \- sections 9.1, 9.2, including code samples)*

### **Automated Maintenance**

*(Include Python script sample)*

### **Metrics Collection**

*(Include Prometheus config sample)*

## **General Plan & Documentation Updates (Post Phase 1\)**

(UPDATE Plan all 1 \- 4 : New Section based on Phase 1 Findings)

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

*(Content remains the same as original plan \- sections 10.1, 10.2)*

### **Docker Compose Configuration**

*(Include YAML sample \- Note: May need updates for Azure integration if run locally)*

### **API Usage Example**

*(Include Python sample for Dremio query service)*

This updated plan incorporates the strategic decisions and technical learnings from Phase 1, providing a revised roadmap focused on leveraging Dremio's capabilities for both writing and querying in the initial phases, while preparing for migration to Azure and acknowledging the complexities deferred for later consideration.