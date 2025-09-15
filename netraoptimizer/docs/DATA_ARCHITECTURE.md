# Data Architecture Documentation - NetraOptimizer

## 🏗️ System Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                         Application Layer                        │
│                    (Scripts, Services, APIs)                     │
├────────────────────────────────────────────────────────────────┤
│                      NetraOptimizerClient                        │
│                    (Centralized Entry Point)                     │
├────────────────────────────────────────────────────────────────┤
│   ┌────────────┐  ┌────────────┐  ┌─────────────┐             │
│   │  Execution │  │   Parser   │  │  Analytics  │             │
│   │   Engine   │  │  & Feature │  │  & Predict  │             │
│   │            │  │ Extraction │  │   Engine    │             │
│   └────────────┘  └────────────┘  └─────────────┘             │
├────────────────────────────────────────────────────────────────┤
│                    CloudSQL Configuration                        │
│              (cloud_config.py + Secret Manager)                  │
├────────────────────────────────────────────────────────────────┤
│                       Database Client                            │
│                    (Connection Pool Manager)                     │
├────────────────────────────────────────────────────────────────┤
│                    Google CloudSQL (PostgreSQL)                  │
│   ┌──────────────────────────┐  ┌─────────────────────────┐   │
│   │   command_executions     │  │   command_patterns      │   │
│   │   (Fact Table)           │  │   (Dimension Table)     │   │
│   └──────────────────────────┘  └─────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

## 📊 Database Schema Design

### Primary Tables

#### 1. `command_executions` (Fact Table)

**Purpose**: Store every single Claude Code execution with comprehensive metrics.

**Design Philosophy**: Wide table with JSONB columns for flexibility and performance.

```sql
CREATE TABLE command_executions (
    -- Identity (Primary Key & Relationships)
    id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    batch_id UUID,                    -- Groups related executions
    execution_sequence INTEGER,       -- Order within batch

    -- Command Data
    command_raw TEXT NOT NULL,        -- Original command string
    command_base VARCHAR(100),        -- Extracted base command
    command_args JSONB,              -- Parsed arguments
    command_features JSONB,          -- Semantic features

    -- Context
    workspace_context JSONB,         -- Workspace state
    session_context JSONB,           -- Session information

    -- Token Metrics
    total_tokens INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cached_tokens INTEGER,
    fresh_tokens INTEGER,
    cache_hit_rate FLOAT,

    -- Performance
    execution_time_ms INTEGER,
    tool_calls INTEGER,
    status VARCHAR(20),
    error_message TEXT,

    -- Financial
    cost_usd DECIMAL(10,6),
    fresh_cost_usd DECIMAL(10,6),
    cache_savings_usd DECIMAL(10,6),

    -- Output Analysis
    output_characteristics JSONB,
    model_version VARCHAR(50)
);
```

**Key Design Decisions**:
- **UUID Primary Key**: Distributed system friendly, no central sequence
- **JSONB Columns**: Flexible schema evolution without migrations
- **Denormalized Metrics**: Fast queries without joins
- **Wide Table**: Optimized for analytics (OLAP pattern)

#### 2. `command_patterns` (Dimension Table)

**Purpose**: Store learned patterns and aggregated statistics.

```sql
CREATE TABLE command_patterns (
    id SERIAL PRIMARY KEY,
    pattern_signature VARCHAR(500) UNIQUE,
    command_base VARCHAR(100),

    -- Aggregated Statistics
    statistics_30d JSONB,
    token_drivers JSONB,
    cache_patterns JSONB,

    -- Optimization Intelligence
    optimization_insights JSONB,
    failure_patterns JSONB,

    -- Metadata
    last_updated TIMESTAMPTZ,
    sample_size INTEGER
);
```

### Index Strategy

```sql
-- Time-series queries
CREATE INDEX idx_timestamp ON command_executions(timestamp DESC);

-- Command analysis
CREATE INDEX idx_command_base ON command_executions(command_base);

-- Batch processing
CREATE INDEX idx_batch_id ON command_executions(batch_id);

-- Status filtering
CREATE INDEX idx_status ON command_executions(status);

-- JSONB searches (GIN indexes)
CREATE INDEX idx_command_args_gin ON command_executions USING GIN(command_args);
CREATE INDEX idx_command_features_gin ON command_executions USING GIN(command_features);
```

**Index Design Rationale**:
- **B-tree indexes**: For exact matches and range queries
- **GIN indexes**: For JSONB containment queries
- **Partial indexes**: Could be added for frequently filtered subsets

## 🔄 Data Flow Architecture

### 1. Ingestion Flow

```
User Command
    ↓
NetraOptimizerClient.run()
    ↓
[Execute Subprocess] → [Parse Output] → [Extract Features]
    ↓
ExecutionRecord (Pydantic Model)
    ↓
DatabaseClient.insert_execution()
    ↓
PostgreSQL (command_executions)
```

### 2. Analytics Flow

```
PostgreSQL (command_executions)
    ↓
Analytics Engine Query
    ↓
[Aggregate] → [Calculate] → [Pattern Match]
    ↓
command_patterns (Updated)
    ↓
Insights & Recommendations
```

### 3. Prediction Flow

```
New Command
    ↓
Parser.parse_command()
    ↓
Feature Extraction
    ↓
Query command_patterns
    ↓
Statistical Model
    ↓
Prediction Result
```

## 📐 Data Model Design Patterns

### 1. Star Schema Pattern

```
         command_executions (Fact)
                    ↓
    ┌──────────────┼──────────────┐
    ↓              ↓              ↓
command_patterns  workspace_dim  time_dim
(Dimension)      (Future)       (Future)
```

### 2. JSONB for Flexibility

**Why JSONB?**
- Schema evolution without migrations
- Rich querying with GIN indexes
- Stores complex nested structures
- Maintains query performance

**Example Query**:
```sql
-- Find all commands affecting 'agents' component
SELECT * FROM command_executions
WHERE command_features @> '{"affects_components": ["agents"]}';
```

### 3. Wide Table Optimization

Instead of normalized tables with joins:
```sql
-- Avoided: Multiple tables requiring joins
SELECT e.*, t.*, c.*
FROM executions e
JOIN tokens t ON e.id = t.execution_id
JOIN costs c ON e.id = c.execution_id;
```

We use a single wide table:
```sql
-- Optimized: Single table scan
SELECT * FROM command_executions
WHERE timestamp > NOW() - INTERVAL '7 days';
```

## 🎯 Data Quality & Integrity

### Constraints

```sql
-- Enforce data quality
ALTER TABLE command_executions
ADD CONSTRAINT status_check
CHECK (status IN ('pending', 'completed', 'failed', 'timeout'));

ALTER TABLE command_executions
ADD CONSTRAINT positive_tokens
CHECK (total_tokens >= 0);

ALTER TABLE command_executions
ADD CONSTRAINT cache_rate_range
CHECK (cache_hit_rate >= 0 AND cache_hit_rate <= 100);
```

### Data Validation Pipeline

```python
class ExecutionRecord(BaseModel):
    # Pydantic validation
    @field_validator('cache_hit_rate')
    def validate_cache_hit_rate(cls, v):
        return max(0.0, min(100.0, v))

    @field_validator('status')
    def validate_status(cls, v):
        if v not in {'pending', 'completed', 'failed', 'timeout'}:
            raise ValueError(f"Invalid status: {v}")
        return v

    def calculate_derived_metrics(self):
        # Ensure consistency
        self.fresh_tokens = self.total_tokens - self.cached_tokens
        self.cache_hit_rate = (self.cached_tokens / self.total_tokens) * 100
```

## 📈 Performance Optimization

### Query Optimization Strategies

#### 1. Partitioning (Future)
```sql
-- Partition by month for better performance
CREATE TABLE command_executions_2024_01
PARTITION OF command_executions
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

#### 2. Materialized Views
```sql
-- Pre-compute expensive aggregations
CREATE MATERIALIZED VIEW daily_command_stats AS
SELECT
    DATE(timestamp) as day,
    command_base,
    COUNT(*) as execution_count,
    AVG(total_tokens) as avg_tokens,
    SUM(cost_usd) as total_cost
FROM command_executions
GROUP BY DATE(timestamp), command_base;

-- Refresh periodically
REFRESH MATERIALIZED VIEW daily_command_stats;
```

#### 3. Connection Pooling
```python
# Implemented in DatabaseClient
self._pool = await asyncpg.create_pool(
    self.database_url,
    min_size=2,      # Minimum connections
    max_size=10,     # Maximum connections
    command_timeout=60,
    max_queries=50000
)
```

## 🔐 Security Considerations

### 1. SQL Injection Prevention
```python
# Always use parameterized queries
await conn.execute("""
    INSERT INTO command_executions (id, command_raw)
    VALUES ($1, $2)
""", record.id, record.command_raw)

# Never use string formatting
# BAD: f"INSERT INTO table VALUES ('{value}')"
```

### 2. Connection Security
```python
# CloudSQL connections are automatically secured
# Via Cloud SQL Proxy (local development)
database_url = "postgresql://user:pass@localhost:5434/netra_optimizer"

# Via Unix socket (Cloud Run deployment)
database_url = "postgresql://user:pass@/netra_optimizer?host=/cloudsql/PROJECT:REGION:INSTANCE"

# Credentials from Google Secret Manager (staging/production)
# Automatically loaded by cloud_config.py
```

### 3. Data Privacy
```python
# Sanitize sensitive data before storage
def sanitize_command(command: str) -> str:
    # Remove API keys, tokens, passwords
    return re.sub(r'(api_key|token|password)=\S+', r'\1=***', command)
```

## 📊 Analytics Queries

### High-Value Queries

#### 1. Token Usage Trends
```sql
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    SUM(total_tokens) as tokens,
    AVG(cache_hit_rate) as cache_rate
FROM command_executions
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;
```

#### 2. Cost Analysis by Command
```sql
SELECT
    command_base,
    COUNT(*) as executions,
    SUM(cost_usd) as total_cost,
    AVG(cost_usd) as avg_cost,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY cost_usd) as p95_cost
FROM command_executions
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY command_base
ORDER BY total_cost DESC;
```

#### 3. Cache Effectiveness
```sql
WITH cache_stats AS (
    SELECT
        command_base,
        AVG(cache_hit_rate) as avg_cache_rate,
        SUM(cache_savings_usd) as total_savings
    FROM command_executions
    WHERE timestamp > NOW() - INTERVAL '7 days'
    GROUP BY command_base
)
SELECT
    command_base,
    avg_cache_rate,
    total_savings,
    RANK() OVER (ORDER BY avg_cache_rate DESC) as cache_rank
FROM cache_stats;
```

## 🔄 Data Lifecycle Management

### Retention Policy

```sql
-- Archive old data
CREATE TABLE command_executions_archive AS
SELECT * FROM command_executions
WHERE timestamp < NOW() - INTERVAL '90 days';

-- Delete from main table
DELETE FROM command_executions
WHERE timestamp < NOW() - INTERVAL '90 days';
```

### Aggregation Pipeline

```python
async def aggregate_daily_patterns():
    """Run nightly to update pattern statistics."""
    # 1. Query recent executions
    # 2. Calculate statistics
    # 3. Update command_patterns
    # 4. Generate recommendations
```

## 🚀 Scaling Considerations

### Horizontal Scaling Options

1. **Read Replicas**: For analytics queries
2. **Sharding**: By command_base or timestamp
3. **Time-Series Database**: Migration path to TimescaleDB
4. **Data Lake**: Export to S3/Parquet for big data analytics

### Vertical Scaling Optimizations

1. **Index Tuning**: Regular EXPLAIN ANALYZE
2. **Query Optimization**: Prepared statements
3. **Connection Management**: Proper pooling
4. **Resource Allocation**: Tune PostgreSQL settings

## 📉 Monitoring & Alerting

### Key Metrics to Monitor

```sql
-- Database health check
SELECT
    pg_database_size('netra_optimizer') as db_size,
    (SELECT count(*) FROM command_executions) as total_records,
    (SELECT count(*) FROM pg_stat_activity) as active_connections,
    (SELECT max(timestamp) FROM command_executions) as last_execution;
```

### Alert Conditions

- Database size > 100GB
- Query time > 5 seconds
- Connection pool exhaustion
- No new records for > 1 hour

## 🎓 Best Practices

1. **Always use ExecutionRecord model** for data consistency
2. **Batch inserts** when possible for performance
3. **Use JSONB queries** sparingly (they're slower)
4. **Regular VACUUM** for PostgreSQL health
5. **Monitor slow queries** with pg_stat_statements
6. **Backup regularly** with point-in-time recovery
7. **Test migrations** in staging first

---

**Data Architecture Principle**: Every byte stored should enable a decision or optimization.