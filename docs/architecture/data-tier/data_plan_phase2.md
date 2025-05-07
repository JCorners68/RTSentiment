# Data Tier Implementation Plan - Phase 2

## Interface Abstraction Implementation

This second phase builds upon the foundation established in Phase 1, focusing on creating a robust abstraction layer with consistent error handling, transaction management, and performance monitoring. Phase 2 enhances the flexibility and reliability of the data tier, preparing it for the eventual Iceberg implementation in Phase 3.

## Key Objectives for Phase 2

### 1. Enhance Repository Pattern

The basic repository pattern implemented in Phase 1 will be enhanced with:

- **Unit of Work Pattern**: Implement a Unit of Work to coordinate operations across multiple repositories
- **Specification Pattern**: Add support for complex query specifications
- **Specialized Repository Operations**: Create specialized repository operations for common complex queries
- **Command Query Responsibility Segregation (CQRS)**: Separate read and write operations where appropriate

#### Implementation Steps:

1. **Unit of Work Implementation**:
   
   ```java
   public interface UnitOfWork {
       void begin();
       void commit();
       void rollback();
       <T> Repository<T, ?> getRepository(Class<T> entityClass);
   }
   
   @Component
   public class PostgresUnitOfWork implements UnitOfWork {
       private final Connection connection;
       private final Map<Class<?>, Repository<?, ?>> repositories;
       private final RepositoryFactory repositoryFactory;
       
       @Autowired
       public PostgresUnitOfWork(DataSource dataSource, RepositoryFactory repositoryFactory) {
           this.repositoryFactory = repositoryFactory;
           this.repositories = new HashMap<>();
           try {
               this.connection = dataSource.getConnection();
               this.connection.setAutoCommit(false);
           } catch (SQLException e) {
               throw new DatabaseException("Failed to create unit of work", e);
           }
       }
       
       @Override
       public void begin() {
           try {
               connection.setAutoCommit(false);
           } catch (SQLException e) {
               throw new DatabaseException("Failed to begin transaction", e);
           }
       }
       
       @Override
       public void commit() {
           try {
               connection.commit();
           } catch (SQLException e) {
               throw new DatabaseException("Failed to commit transaction", e);
           }
       }
       
       @Override
       public void rollback() {
           try {
               connection.rollback();
           } catch (SQLException e) {
               throw new DatabaseException("Failed to rollback transaction", e);
           }
       }
       
       @SuppressWarnings("unchecked")
       @Override
       public <T> Repository<T, ?> getRepository(Class<T> entityClass) {
           if (!repositories.containsKey(entityClass)) {
               Repository<T, ?> repository = repositoryFactory.getRepository(entityClass);
               if (repository instanceof TransactionAwareRepository) {
                   ((TransactionAwareRepository) repository).setConnection(connection);
               }
               repositories.put(entityClass, repository);
           }
           return (Repository<T, ?>) repositories.get(entityClass);
       }
       
       @PreDestroy
       public void close() {
           try {
               connection.close();
           } catch (SQLException e) {
               // Log error but don't throw
               log.error("Error closing connection", e);
           }
       }
   }
   ```

2. **Specification Pattern**:
   
   ```java
   public interface Specification<T> {
       boolean isSatisfiedBy(T entity);
       String toSqlClause();
       Map<String, Object> getParameters();
   }
   
   public class SentimentScoreRangeSpecification implements Specification<SentimentRecord> {
       private final double minScore;
       private final double maxScore;
       
       public SentimentScoreRangeSpecification(double minScore, double maxScore) {
           this.minScore = minScore;
           this.maxScore = maxScore;
       }
       
       @Override
       public boolean isSatisfiedBy(SentimentRecord entity) {
           return entity.getSentimentScore() >= minScore && 
                  entity.getSentimentScore() <= maxScore;
       }
       
       @Override
       public String toSqlClause() {
           return "sentiment_score BETWEEN :minScore AND :maxScore";
       }
       
       @Override
       public Map<String, Object> getParameters() {
           Map<String, Object> params = new HashMap<>();
           params.put("minScore", minScore);
           params.put("maxScore", maxScore);
           return params;
       }
   }
   ```

3. **Enhanced Repository Interface**:

   ```java
   public interface EnhancedRepository<T, ID> extends Repository<T, ID> {
       List<T> findAll(Specification<T> spec);
       List<T> findAll(Specification<T> spec, OrderBy orderBy, int limit, int offset);
       long count(Specification<T> spec);
   }
   ```

4. **CQRS Implementation**:

   ```java
   public interface QueryRepository<T, ID> {
       Optional<T> findById(ID id);
       List<T> findAll();
       List<T> findAll(Specification<T> spec);
       long count(Specification<T> spec);
   }
   
   public interface CommandRepository<T, ID> {
       T save(T entity);
       T update(T entity);
       void delete(ID id);
       void deleteAll(Specification<T> spec);
   }
   
   public interface SentimentRecordRepository extends 
       QueryRepository<SentimentRecord, UUID>,
       CommandRepository<SentimentRecord, UUID> {
       // Additional query methods
       List<SentimentRecord> findByTicker(String ticker);
   }
   ```

### 2. Implement Transaction Management

Implement a robust transaction management system that supports:

- **Declarative Transactions**: Use annotations to define transaction boundaries
- **Cross-Repository Transactions**: Coordinate operations across multiple repositories
- **Nested Transactions**: Support for transaction nesting with proper isolation
- **Transaction Templates**: Provide templates for common transaction patterns

#### Implementation Steps:

1. **Transaction Manager Interface**:

   ```java
   public interface TransactionManager {
       <T> T executeInTransaction(TransactionCallback<T> callback);
       void begin();
       void commit();
       void rollback();
       boolean isTransactionActive();
   }
   
   @FunctionalInterface
   public interface TransactionCallback<T> {
       T doInTransaction();
   }
   ```

2. **PostgreSQL Transaction Manager Implementation**:

   ```java
   @Component
   public class PostgresTransactionManager implements TransactionManager {
       private final DataSource dataSource;
       private final ThreadLocal<Connection> connectionHolder = new ThreadLocal<>();
       private final ThreadLocal<Integer> transactionDepth = ThreadLocal.withInitial(() -> 0);
       
       @Autowired
       public PostgresTransactionManager(DataSource dataSource) {
           this.dataSource = dataSource;
       }
       
       @Override
       public <T> T executeInTransaction(TransactionCallback<T> callback) {
           boolean isNewTransaction = !isTransactionActive();
           
           if (isNewTransaction) {
               begin();
           } else {
               incrementTransactionDepth();
           }
           
           try {
               T result = callback.doInTransaction();
               
               if (isNewTransaction) {
                   commit();
               } else {
                   decrementTransactionDepth();
               }
               
               return result;
           } catch (Exception e) {
               if (isNewTransaction) {
                   rollback();
               } else {
                   decrementTransactionDepth();
               }
               
               throw e instanceof RuntimeException ? 
                   (RuntimeException) e : new RuntimeException(e);
           }
       }
       
       @Override
       public void begin() {
           try {
               if (isTransactionActive()) {
                   incrementTransactionDepth();
                   return;
               }
               
               Connection connection = dataSource.getConnection();
               connection.setAutoCommit(false);
               connectionHolder.set(connection);
               transactionDepth.set(1);
           } catch (SQLException e) {
               throw new DatabaseException("Failed to begin transaction", e);
           }
       }
       
       @Override
       public void commit() {
           if (!isTransactionActive()) {
               throw new IllegalStateException("No active transaction to commit");
           }
           
           try {
               if (getTransactionDepth() > 1) {
                   decrementTransactionDepth();
                   return;
               }
               
               Connection connection = connectionHolder.get();
               connection.commit();
               connection.close();
               connectionHolder.remove();
               transactionDepth.remove();
           } catch (SQLException e) {
               throw new DatabaseException("Failed to commit transaction", e);
           }
       }
       
       @Override
       public void rollback() {
           if (!isTransactionActive()) {
               throw new IllegalStateException("No active transaction to rollback");
           }
           
           try {
               if (getTransactionDepth() > 1) {
                   decrementTransactionDepth();
                   return;
               }
               
               Connection connection = connectionHolder.get();
               connection.rollback();
               connection.close();
               connectionHolder.remove();
               transactionDepth.remove();
           } catch (SQLException e) {
               throw new DatabaseException("Failed to rollback transaction", e);
           }
       }
       
       @Override
       public boolean isTransactionActive() {
           return connectionHolder.get() != null;
       }
       
       public Connection getCurrentConnection() {
           if (!isTransactionActive()) {
               throw new IllegalStateException("No active transaction");
           }
           
           return connectionHolder.get();
       }
       
       private int getTransactionDepth() {
           return transactionDepth.get();
       }
       
       private void incrementTransactionDepth() {
           transactionDepth.set(getTransactionDepth() + 1);
       }
       
       private void decrementTransactionDepth() {
           transactionDepth.set(getTransactionDepth() - 1);
       }
   }
   ```

3. **Transaction-Aware Repository**:

   ```java
   public interface TransactionAwareRepository {
       void setConnection(Connection connection);
   }
   
   @Repository("postgresSentimentRecordRepository")
   public class PostgresSentimentRecordRepository implements 
       SentimentRecordRepository, TransactionAwareRepository {
       
       private final DataSource dataSource;
       private final TransactionManager transactionManager;
       private final ThreadLocal<Connection> connectionHolder = new ThreadLocal<>();
       
       @Autowired
       public PostgresSentimentRecordRepository(
               DataSource dataSource, 
               TransactionManager transactionManager) {
           this.dataSource = dataSource;
           this.transactionManager = transactionManager;
       }
       
       @Override
       public void setConnection(Connection connection) {
           connectionHolder.set(connection);
       }
       
       protected Connection getConnection() throws SQLException {
           Connection connection = connectionHolder.get();
           if (connection != null) {
               return connection; // Use transaction-bound connection
           }
           
           // Otherwise get a new connection
           connection = dataSource.getConnection();
           try {
               // Auto-commit for non-transactional operations
               connection.setAutoCommit(true);
               return connection;
           } catch (SQLException e) {
               connection.close();
               throw e;
           }
       }
       
       protected void closeConnection(Connection connection) throws SQLException {
           if (connectionHolder.get() == null) {
               // Only close connections we created (not transaction-bound ones)
               connection.close();
           }
       }
       
       // Repository method implementations using getConnection() and closeConnection()
   }
   ```

4. **Declarative Transaction Support**:

   ```java
   @Component
   @Aspect
   public class TransactionAspect {
       private final TransactionManager transactionManager;
       
       @Autowired
       public TransactionAspect(TransactionManager transactionManager) {
           this.transactionManager = transactionManager;
       }
       
       @Around("@annotation(Transactional)")
       public Object aroundTransactionalMethod(ProceedingJoinPoint joinPoint) throws Throwable {
           return transactionManager.executeInTransaction(() -> {
               try {
                   return joinPoint.proceed();
               } catch (Throwable e) {
                   throw new RuntimeException(e);
               }
           });
       }
   }
   
   @Target(ElementType.METHOD)
   @Retention(RetentionPolicy.RUNTIME)
   public @interface Transactional {
   }
   ```

### 3. Standardize Error Handling

Create a consistent error handling approach that:

- **Translates Database-Specific Errors**: Convert database-specific errors to application-specific exceptions
- **Provides Detailed Context**: Include operation context in error messages
- **Categorizes Errors**: Distinguish between different types of errors (connection, constraint violation, etc.)
- **Supports Recovery**: Provide mechanisms for graceful error recovery

#### Implementation Steps:

1. **Exception Hierarchy**:

   ```java
   public class DatabaseException extends RuntimeException {
       public DatabaseException(String message) {
           super(message);
       }
       
       public DatabaseException(String message, Throwable cause) {
           super(message, cause);
       }
   }
   
   public class ConnectionException extends DatabaseException {
       public ConnectionException(String message, Throwable cause) {
           super(message, cause);
       }
   }
   
   public class QueryException extends DatabaseException {
       public QueryException(String message, Throwable cause) {
           super(message, cause);
       }
   }
   
   public class EntityNotFoundException extends DatabaseException {
       public EntityNotFoundException(String message) {
           super(message);
       }
   }
   
   public class ConstraintViolationException extends DatabaseException {
       private final String constraintName;
       
       public ConstraintViolationException(String message, String constraintName, Throwable cause) {
           super(message, cause);
           this.constraintName = constraintName;
       }
       
       public String getConstraintName() {
           return constraintName;
       }
   }
   ```

2. **Exception Translator**:

   ```java
   public interface ExceptionTranslator {
       RuntimeException translate(Exception e);
       RuntimeException translate(Exception e, String contextMessage);
   }
   
   @Component
   public class PostgresExceptionTranslator implements ExceptionTranslator {
       private static final Logger logger = LoggerFactory.getLogger(PostgresExceptionTranslator.class);
       
       @Override
       public RuntimeException translate(Exception e) {
           return translate(e, null);
       }
       
       @Override
       public RuntimeException translate(Exception e, String contextMessage) {
           String baseMessage = contextMessage != null ? contextMessage : "Database operation failed";
           
           if (e instanceof SQLException) {
               SQLException sqlException = (SQLException) e;
               String sqlState = sqlException.getSQLState();
               
               // Log the exception with SQL state and error code
               logger.error("SQL Exception: {} - State: {}, Code: {}", 
                           baseMessage, sqlState, sqlException.getErrorCode(), e);
               
               // Connection-related errors
               if (sqlState != null) {
                   // Connection errors (08xxx)
                   if (sqlState.startsWith("08")) {
                       return new ConnectionException(baseMessage + ": Connection failed", e);
                   }
                   
                   // Constraint violations (23xxx)
                   if (sqlState.startsWith("23")) {
                       String constraintName = extractConstraintName(sqlException.getMessage());
                       return new ConstraintViolationException(
                           baseMessage + ": Constraint violation", constraintName, e);
                   }
                   
                   // Data exceptions (22xxx)
                   if (sqlState.startsWith("22")) {
                       return new QueryException(baseMessage + ": Data error", e);
                   }
                   
                   // Syntax or access rule violations (42xxx)
                   if (sqlState.startsWith("42")) {
                       return new QueryException(baseMessage + ": Query syntax or access rule violation", e);
                   }
               }
               
               // Default SQL exception handling
               return new DatabaseException(baseMessage, e);
           }
           
           // Non-SQL exceptions
           return new DatabaseException(baseMessage, e);
       }
       
       private String extractConstraintName(String message) {
           // Extract constraint name from PostgreSQL error message
           // Example message: "ERROR: duplicate key value violates unique constraint "users_pkey""
           if (message == null) {
               return "unknown";
           }
           
           // This is a simplified example; actual implementation would be more robust
           int constraintIndex = message.indexOf("constraint");
           if (constraintIndex != -1 && message.length() > constraintIndex + 12) {
               int startQuote = message.indexOf("\"", constraintIndex);
               int endQuote = message.indexOf("\"", startQuote + 1);
               if (startQuote != -1 && endQuote != -1) {
                   return message.substring(startQuote + 1, endQuote);
               }
           }
           
           return "unknown";
       }
   }
   ```

3. **Error Recovery Strategies**:

   ```java
   public interface ErrorRecoveryStrategy<T> {
       boolean canRecover(Exception e);
       T recover(Exception e, Supplier<T> retryOperation);
   }
   
   public class RetryRecoveryStrategy<T> implements ErrorRecoveryStrategy<T> {
       private final int maxRetries;
       private final long delayMs;
       private final Class<? extends Exception>[] recoverableExceptions;
       
       public RetryRecoveryStrategy(int maxRetries, long delayMs, 
                                    Class<? extends Exception>... recoverableExceptions) {
           this.maxRetries = maxRetries;
           this.delayMs = delayMs;
           this.recoverableExceptions = recoverableExceptions;
       }
       
       @Override
       public boolean canRecover(Exception e) {
           for (Class<? extends Exception> exceptionClass : recoverableExceptions) {
               if (exceptionClass.isInstance(e)) {
                   return true;
               }
           }
           return false;
       }
       
       @Override
       public T recover(Exception e, Supplier<T> retryOperation) {
           int attempts = 0;
           Exception lastException = e;
           
           while (attempts < maxRetries) {
               attempts++;
               
               try {
                   // Exponential backoff
                   Thread.sleep(delayMs * (long) Math.pow(2, attempts - 1));
                   return retryOperation.get();
               } catch (Exception retryException) {
                   lastException = retryException;
                   if (!canRecover(retryException)) {
                       break;
                   }
               } catch (InterruptedException ie) {
                   Thread.currentThread().interrupt();
                   break;
               }
           }
           
           throw new DatabaseException("Recovery failed after " + attempts + " attempts", lastException);
       }
   }
   
   public class RecoverableRepository<T, ID> implements Repository<T, ID> {
       private final Repository<T, ID> delegate;
       private final List<ErrorRecoveryStrategy<T>> recoveryStrategies;
       
       public RecoverableRepository(Repository<T, ID> delegate,
                                    List<ErrorRecoveryStrategy<T>> recoveryStrategies) {
           this.delegate = delegate;
           this.recoveryStrategies = recoveryStrategies;
       }
       
       @Override
       public Optional<T> findById(ID id) {
           try {
               return delegate.findById(id);
           } catch (Exception e) {
               return recoverIfPossible(e, () -> delegate.findById(id));
           }
       }
       
       // Implement other Repository methods with similar recovery pattern
       
       private <R> R recoverIfPossible(Exception e, Supplier<R> operation) {
           for (ErrorRecoveryStrategy strategy : recoveryStrategies) {
               if (strategy.canRecover(e)) {
                   return (R) strategy.recover(e, operation);
               }
           }
           
           if (e instanceof RuntimeException) {
               throw (RuntimeException) e;
           } else {
               throw new DatabaseException("Unrecoverable error", e);
           }
       }
   }
   ```

### 4. Improve Testability

Enhance test infrastructure to support thorough testing of the data tier:

- **Repository Test Base Class**: Create a base class for repository tests
- **In-Memory Repository Implementation**: Implement in-memory versions for testing
- **Test Fixtures**: Create fixtures and generators for test data
- **Assertions**: Create specialized assertions for repository operations

#### Implementation Steps:

1. **Repository Test Base Class**:

   ```java
   @TestInstance(TestInstance.Lifecycle.PER_CLASS)
   public abstract class RepositoryTestBase<T, ID, R extends Repository<T, ID>> {
       
       protected abstract R createRepository();
       protected abstract T createEntity();
       protected abstract ID getEntityId(T entity);
       protected abstract T updateEntity(T entity);
       protected abstract void assertEntitiesEqual(T expected, T actual);
       
       private R repository;
       
       @BeforeEach
       public void setUp() {
           repository = createRepository();
       }
       
       @Test
       public void testSaveAndFindById() {
           // Given
           T entity = createEntity();
           
           // When
           T savedEntity = repository.save(entity);
           Optional<T> foundEntity = repository.findById(getEntityId(savedEntity));
           
           // Then
           assertTrue(foundEntity.isPresent());
           assertEntitiesEqual(savedEntity, foundEntity.get());
       }
       
       @Test
       public void testUpdate() {
           // Given
           T entity = createEntity();
           T savedEntity = repository.save(entity);
           
           // When
           T updatedEntity = updateEntity(savedEntity);
           repository.update(updatedEntity);
           Optional<T> foundEntity = repository.findById(getEntityId(updatedEntity));
           
           // Then
           assertTrue(foundEntity.isPresent());
           assertEntitiesEqual(updatedEntity, foundEntity.get());
       }
       
       @Test
       public void testDelete() {
           // Given
           T entity = createEntity();
           T savedEntity = repository.save(entity);
           
           // When
           repository.delete(getEntityId(savedEntity));
           Optional<T> foundEntity = repository.findById(getEntityId(savedEntity));
           
           // Then
           assertTrue(foundEntity.isEmpty());
       }
       
       // Additional test methods for specific repository behavior
   }
   ```

2. **In-Memory Repository Implementation**:

   ```java
   public class InMemorySentimentRecordRepository implements SentimentRecordRepository {
       private final Map<UUID, SentimentRecord> records = new ConcurrentHashMap<>();
       
       @Override
       public Optional<SentimentRecord> findById(UUID id) {
           return Optional.ofNullable(records.get(id));
       }
       
       @Override
       public List<SentimentRecord> findAll() {
           return new ArrayList<>(records.values());
       }
       
       @Override
       public SentimentRecord save(SentimentRecord entity) {
           if (entity.getId() == null) {
               entity.setId(UUID.randomUUID());
           }
           records.put(entity.getId(), entity);
           return entity;
       }
       
       @Override
       public SentimentRecord update(SentimentRecord entity) {
           if (!records.containsKey(entity.getId())) {
               throw new EntityNotFoundException("Entity not found: " + entity.getId());
           }
           records.put(entity.getId(), entity);
           return entity;
       }
       
       @Override
       public void delete(UUID id) {
           records.remove(id);
       }
       
       @Override
       public List<SentimentRecord> findByTicker(String ticker) {
           return records.values().stream()
               .filter(record -> record.getTicker().equals(ticker))
               .collect(Collectors.toList());
       }
       
       @Override
       public List<SentimentRecord> findByTickerAndTimeRange(String ticker, Instant start, Instant end) {
           return records.values().stream()
               .filter(record -> record.getTicker().equals(ticker))
               .filter(record -> !record.getTimestamp().isBefore(start) && !record.getTimestamp().isAfter(end))
               .collect(Collectors.toList());
       }
       
       @Override
       public double getAverageSentimentForTicker(String ticker, Instant since) {
           List<SentimentRecord> matchingRecords = records.values().stream()
               .filter(record -> record.getTicker().equals(ticker))
               .filter(record -> !record.getTimestamp().isBefore(since))
               .collect(Collectors.toList());
           
           if (matchingRecords.isEmpty()) {
               return 0.0;
           }
           
           return matchingRecords.stream()
               .mapToDouble(SentimentRecord::getSentimentScore)
               .average()
               .orElse(0.0);
       }
   }
   ```

3. **Test Data Generators**:

   ```java
   public class SentimentRecordGenerator {
       private static final String[] TICKERS = {"AAPL", "MSFT", "GOOGL", "AMZN", "FB"};
       private static final String[] SOURCES = {"twitter", "news", "financial-report", "analyst-review"};
       private static final Random random = new Random();
       
       public static SentimentRecord generate() {
           SentimentRecord record = new SentimentRecord();
           record.setTicker(randomTicker());
           record.setSentimentScore(randomSentimentScore());
           record.setTimestamp(randomTimestamp());
           record.setSource(randomSource());
           record.setAttributes(randomAttributes());
           return record;
       }
       
       public static List<SentimentRecord> generateList(int count) {
           return IntStream.range(0, count)
               .mapToObj(i -> generate())
               .collect(Collectors.toList());
       }
       
       public static String randomTicker() {
           return TICKERS[random.nextInt(TICKERS.length)];
       }
       
       public static double randomSentimentScore() {
           return -1.0 + (2.0 * random.nextDouble());
       }
       
       public static Instant randomTimestamp() {
           return Instant.now().minus(random.nextInt(30), ChronoUnit.DAYS);
       }
       
       public static String randomSource() {
           return SOURCES[random.nextInt(SOURCES.length)];
       }
       
       public static Map<String, Double> randomAttributes() {
           Map<String, Double> attributes = new HashMap<>();
           attributes.put("confidence", 0.5 + (0.5 * random.nextDouble()));
           attributes.put("volume", 100.0 + (900.0 * random.nextDouble()));
           return attributes;
       }
   }
   ```

4. **Repository Assertions**:

   ```java
   public class RepositoryAssertions {
       public static <T, ID> void assertEntityExists(Repository<T, ID> repository, ID id) {
           assertTrue(repository.findById(id).isPresent(), 
                    "Entity with ID " + id + " should exist");
       }
       
       public static <T, ID> void assertEntityDoesNotExist(Repository<T, ID> repository, ID id) {
           assertTrue(repository.findById(id).isEmpty(), 
                    "Entity with ID " + id + " should not exist");
       }
       
       public static void assertSentimentRecordsEqual(SentimentRecord expected, SentimentRecord actual) {
           assertEquals(expected.getId(), actual.getId());
           assertEquals(expected.getTicker(), actual.getTicker());
           assertEquals(expected.getSentimentScore(), actual.getSentimentScore(), 0.001);
           assertEquals(expected.getTimestamp(), actual.getTimestamp());
           assertEquals(expected.getSource(), actual.getSource());
           assertEquals(expected.getAttributes().size(), actual.getAttributes().size());
           
           for (Map.Entry<String, Double> entry : expected.getAttributes().entrySet()) {
               assertTrue(actual.getAttributes().containsKey(entry.getKey()));
               assertEquals(entry.getValue(), actual.getAttributes().get(entry.getKey()), 0.001);
           }
       }
   }
   ```

### 5. Add Performance Monitoring

Implement a performance monitoring system for tracking database operations:

- **Query Performance Metrics**: Track timing and resource usage for queries
- **Performance Logging**: Log slow queries and performance bottlenecks
- **Monitoring Hooks**: Add hooks for external monitoring tools
- **Performance Dashboard**: Create a simple performance dashboard

#### Implementation Steps:

1. **Performance Metrics Collection**:

   ```java
   public class QueryMetrics {
       private final String queryType;
       private final String queryDetails;
       private final long startTimeNanos;
       private long endTimeNanos;
       private final Map<String, Object> queryParameters;
       private Exception exception;
       
       public QueryMetrics(String queryType, String queryDetails, Map<String, Object> queryParameters) {
           this.queryType = queryType;
           this.queryDetails = queryDetails;
           this.startTimeNanos = System.nanoTime();
           this.queryParameters = queryParameters != null ? queryParameters : Collections.emptyMap();
       }
       
       public void markComplete() {
           this.endTimeNanos = System.nanoTime();
       }
       
       public void markError(Exception e) {
           this.endTimeNanos = System.nanoTime();
           this.exception = e;
       }
       
       public long getDurationNanos() {
           return endTimeNanos - startTimeNanos;
       }
       
       public long getDurationMillis() {
           return getDurationNanos() / 1_000_000;
       }
       
       public boolean isSuccess() {
           return exception == null;
       }
       
       public String getQueryType() {
           return queryType;
       }
       
       public String getQueryDetails() {
           return queryDetails;
       }
       
       public Map<String, Object> getQueryParameters() {
           return queryParameters;
       }
       
       public Exception getException() {
           return exception;
       }
   }
   ```

2. **Performance Monitoring Service**:

   ```java
   public interface PerformanceMonitoringService {
       QueryMetrics startQueryMetrics(String queryType, String queryDetails);
       QueryMetrics startQueryMetrics(String queryType, String queryDetails, Map<String, Object> queryParameters);
       void recordMetrics(QueryMetrics metrics);
       List<QueryMetrics> getSlowQueries(int maxResults);
       Map<String, Double> getAverageQueryTimes();
   }
   
   @Component
   public class DefaultPerformanceMonitoringService implements PerformanceMonitoringService {
       private static final Logger logger = LoggerFactory.getLogger(DefaultPerformanceMonitoringService.class);
       
       private final Queue<QueryMetrics> recentQueries = new ConcurrentLinkedQueue<>();
       private final int maxQueriesStored = 1000;
       private final long slowQueryThresholdMillis = 100;
       
       @Override
       public QueryMetrics startQueryMetrics(String queryType, String queryDetails) {
           return startQueryMetrics(queryType, queryDetails, null);
       }
       
       @Override
       public QueryMetrics startQueryMetrics(String queryType, String queryDetails, 
                                           Map<String, Object> queryParameters) {
           return new QueryMetrics(queryType, queryDetails, queryParameters);
       }
       
       @Override
       public void recordMetrics(QueryMetrics metrics) {
           // Store metrics for analysis
           addToRecentQueries(metrics);
           
           // Log slow queries
           if (metrics.getDurationMillis() > slowQueryThresholdMillis) {
               logger.warn("Slow query detected: {} - {} took {}ms", 
                          metrics.getQueryType(), 
                          metrics.getQueryDetails(), 
                          metrics.getDurationMillis());
               
               if (!metrics.getQueryParameters().isEmpty()) {
                   logger.debug("Query parameters: {}", metrics.getQueryParameters());
               }
           }
           
           // Log errors
           if (!metrics.isSuccess()) {
               logger.error("Query error: {} - {} failed after {}ms", 
                           metrics.getQueryType(), 
                           metrics.getQueryDetails(), 
                           metrics.getDurationMillis(), 
                           metrics.getException());
           }
       }
       
       @Override
       public List<QueryMetrics> getSlowQueries(int maxResults) {
           return recentQueries.stream()
               .filter(metrics -> metrics.getDurationMillis() > slowQueryThresholdMillis)
               .sorted(Comparator.comparingLong(QueryMetrics::getDurationMillis).reversed())
               .limit(maxResults)
               .collect(Collectors.toList());
       }
       
       @Override
       public Map<String, Double> getAverageQueryTimes() {
           return recentQueries.stream()
               .filter(QueryMetrics::isSuccess)
               .collect(Collectors.groupingBy(
                   QueryMetrics::getQueryType,
                   Collectors.averagingLong(QueryMetrics::getDurationMillis)
               ));
       }
       
       private void addToRecentQueries(QueryMetrics metrics) {
           recentQueries.add(metrics);
           
           // Trim if needed
           while (recentQueries.size() > maxQueriesStored) {
               recentQueries.poll();
           }
       }
   }
   ```

3. **Monitoring Aspect**:

   ```java
   @Aspect
   @Component
   public class RepositoryMonitoringAspect {
       private final PerformanceMonitoringService monitoringService;
       
       @Autowired
       public RepositoryMonitoringAspect(PerformanceMonitoringService monitoringService) {
           this.monitoringService = monitoringService;
       }
       
       @Around("execution(* com.sentimark.data.repository.*Repository.*(..))")
       public Object monitorRepositoryMethod(ProceedingJoinPoint joinPoint) throws Throwable {
           String methodName = joinPoint.getSignature().getName();
           String className = joinPoint.getTarget().getClass().getSimpleName();
           String queryType = className + "." + methodName;
           
           Map<String, Object> parameters = new HashMap<>();
           Object[] args = joinPoint.getArgs();
           String[] paramNames = ((MethodSignature) joinPoint.getSignature()).getParameterNames();
           
           for (int i = 0; i < args.length; i++) {
               parameters.put(paramNames[i], args[i]);
           }
           
           QueryMetrics metrics = monitoringService.startQueryMetrics(queryType, queryType, parameters);
           
           try {
               Object result = joinPoint.proceed();
               metrics.markComplete();
               return result;
           } catch (Exception e) {
               metrics.markError(e);
               throw e;
           } finally {
               monitoringService.recordMetrics(metrics);
           }
       }
   }
   ```

4. **Performance Dashboard Controller**:

   ```java
   @RestController
   @RequestMapping("/api/monitoring")
   public class PerformanceMonitoringController {
       private final PerformanceMonitoringService monitoringService;
       
       @Autowired
       public PerformanceMonitoringController(PerformanceMonitoringService monitoringService) {
           this.monitoringService = monitoringService;
       }
       
       @GetMapping("/slow-queries")
       public List<Map<String, Object>> getSlowQueries(@RequestParam(defaultValue = "10") int limit) {
           return monitoringService.getSlowQueries(limit).stream()
               .map(this::convertToResponseMap)
               .collect(Collectors.toList());
       }
       
       @GetMapping("/average-times")
       public Map<String, Double> getAverageQueryTimes() {
           return monitoringService.getAverageQueryTimes();
       }
       
       private Map<String, Object> convertToResponseMap(QueryMetrics metrics) {
           Map<String, Object> result = new HashMap<>();
           result.put("queryType", metrics.getQueryType());
           result.put("queryDetails", metrics.getQueryDetails());
           result.put("durationMillis", metrics.getDurationMillis());
           result.put("success", metrics.isSuccess());
           result.put("parameters", metrics.getQueryParameters());
           
           if (!metrics.isSuccess() && metrics.getException() != null) {
               result.put("error", metrics.getException().getMessage());
           }
           
           return result;
       }
   }
   ```

## Verification and Testing

### Database Operations Tests:

1. **Unit of Work Tests**:
   - Test transaction boundaries
   - Test commit and rollback operations
   - Test nested transactions

2. **Specification Pattern Tests**:
   - Test SQL clause generation
   - Test parameter binding
   - Test entity filtering

3. **Error Handling Tests**:
   - Test exception translation
   - Test error recovery strategies
   - Test resilience against database failures

4. **Performance Tests**:
   - Test query performance
   - Test monitoring accuracy
   - Test slow query detection

## Expected Outcomes

By the end of Phase 2, you will have:

1. Enhanced repository abstraction with support for complex operations
2. Robust transaction management across repositories
3. Consistent error handling with appropriate exception hierarchies
4. Improved testability with comprehensive test infrastructure
5. Performance monitoring for database operations

These enhancements will make the database abstraction layer more resilient, maintainable, and ready for the Iceberg implementation in Phase 3.

## Timeline: 2-3 weeks