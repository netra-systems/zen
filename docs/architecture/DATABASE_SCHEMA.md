# Database Schema Documentation

Comprehensive database schema documentation for the Netra AI Optimization Platform apex-v1.

## Overview

Netra uses a dual-database architecture:
- **PostgreSQL**: Primary transactional database for user data, configurations, and persistent state
- **ClickHouse**: Time-series database for analytics and event logging

## PostgreSQL Schema

### Database Configuration

```sql
-- Database: netra_db
-- Encoding: UTF8
-- Collation: en_US.UTF-8
```

### Tables

#### users
Stores user account information.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(255),
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255),
    picture TEXT,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);
CREATE INDEX idx_users_created_at ON users(created_at);
```

**Columns:**
- `id`: Unique user identifier
- `email`: User's email address (unique)
- `name`: User's display name
- `password_hash`: Bcrypt hashed password (null for OAuth users)
- `oauth_provider`: OAuth provider name (google, github, etc.)
- `oauth_id`: OAuth provider user ID
- `picture`: Profile picture URL
- `is_active`: Account active status
- `is_superuser`: Admin privileges flag
- `created_at`: Account creation timestamp
- `updated_at`: Last modification timestamp
- `last_login_at`: Last successful login
- `metadata`: Additional user data in JSON format

---

#### threads
Stores conversation threads for each user.

```sql
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT check_status CHECK (status IN ('active', 'archived', 'deleted'))
);

CREATE INDEX idx_threads_user_id ON threads(user_id);
CREATE INDEX idx_threads_created_at ON threads(created_at);
CREATE INDEX idx_threads_status ON threads(status);
```

**Columns:**
- `id`: UUID thread identifier
- `user_id`: Foreign key to users table
- `title`: Thread title/summary
- `status`: Thread status (active, archived, deleted)
- `created_at`: Thread creation timestamp
- `updated_at`: Last activity timestamp
- `metadata`: Additional thread data

---

#### messages
Stores individual messages within threads.

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    tokens_used INTEGER,
    model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT check_role CHECK (role IN ('user', 'assistant', 'system', 'tool'))
);

CREATE INDEX idx_messages_thread_id ON messages(thread_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_role ON messages(role);
```

**Columns:**
- `id`: UUID message identifier
- `thread_id`: Foreign key to threads table
- `role`: Message sender role
- `content`: Message content
- `tokens_used`: LLM tokens consumed
- `model`: AI model used (for assistant messages)
- `created_at`: Message timestamp
- `metadata`: Additional message data (attachments, etc.)

---

#### runs
Tracks agent execution runs.

```sql
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE SET NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    agent_type VARCHAR(100),
    input_data JSONB NOT NULL,
    output_data JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT check_status CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_runs_user_id ON runs(user_id);
CREATE INDEX idx_runs_thread_id ON runs(thread_id);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_created_at ON runs(created_at);
CREATE INDEX idx_runs_agent_type ON runs(agent_type);
```

**Columns:**
- `id`: UUID run identifier
- `thread_id`: Associated thread (optional)
- `user_id`: User who initiated the run
- `status`: Execution status
- `agent_type`: Type of agent executed
- `input_data`: Input parameters (JSON)
- `output_data`: Execution results (JSON)
- `error_message`: Error details if failed
- `started_at`: Execution start time
- `completed_at`: Execution end time
- `created_at`: Run creation timestamp
- `metadata`: Additional run data

---

#### references
Stores user-uploaded references and data.

```sql
CREATE TABLE references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    content TEXT,
    file_path TEXT,
    file_size BIGINT,
    mime_type VARCHAR(255),
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT check_type CHECK (type IN ('document', 'dataset', 'configuration', 'model', 'other'))
);

CREATE INDEX idx_references_user_id ON references(user_id);
CREATE INDEX idx_references_type ON references(type);
CREATE INDEX idx_references_created_at ON references(created_at);
CREATE INDEX idx_references_embedding ON references USING ivfflat (embedding vector_cosine_ops);
```

**Columns:**
- `id`: UUID reference identifier
- `user_id`: Owner of the reference
- `name`: Reference name/title
- `type`: Reference type category
- `content`: Text content (for documents)
- `file_path`: Storage path for files
- `file_size`: File size in bytes
- `mime_type`: MIME type for files
- `embedding`: Vector embedding for similarity search
- `created_at`: Upload timestamp
- `updated_at`: Last modification timestamp
- `metadata`: Additional reference data

---

#### supply_catalog
Stores optimization supply configurations.

```sql
CREATE TABLE supply_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    provider VARCHAR(100),
    specifications JSONB NOT NULL,
    pricing JSONB,
    availability JSONB,
    performance_metrics JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_supply_catalog_category ON supply_catalog(category);
CREATE INDEX idx_supply_catalog_provider ON supply_catalog(provider);
CREATE INDEX idx_supply_catalog_is_active ON supply_catalog(is_active);
CREATE INDEX idx_supply_catalog_user_id ON supply_catalog(user_id);
```

**Columns:**
- `id`: UUID supply item identifier
- `user_id`: Owner (null for system items)
- `name`: Supply item name
- `category`: Category (compute, storage, network, etc.)
- `provider`: Cloud/service provider
- `specifications`: Technical specifications (JSON)
- `pricing`: Pricing information (JSON)
- `availability`: Availability data (JSON)
- `performance_metrics`: Performance benchmarks (JSON)
- `is_active`: Item active status
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `metadata`: Additional supply data

---

#### api_keys
Stores API keys for programmatic access.

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
```

---

#### audit_logs
Tracks important system events for audit purposes.

```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(255),
    response_status INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
```

---

### Database Functions

#### update_updated_at_column()
Automatically updates the updated_at timestamp.

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';
```

Apply to tables:
```sql
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_threads_updated_at BEFORE UPDATE ON threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_references_updated_at BEFORE UPDATE ON references
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_supply_catalog_updated_at BEFORE UPDATE ON supply_catalog
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## ClickHouse Schema

### Database Configuration

```sql
CREATE DATABASE IF NOT EXISTS netra_analytics
ENGINE = Atomic;

USE netra_analytics;
```

### Tables

#### workload_events
Stores time-series event data for workload analysis.

```sql
CREATE TABLE workload_events (
    event_id UUID DEFAULT generateUUIDv4(),
    timestamp DateTime64(3) DEFAULT now(),
    user_id UInt32,
    workload_id String,
    event_type String,
    event_category String,
    metrics Nested(
        name String,
        value Float64,
        unit String
    ),
    dimensions Map(String, String),
    metadata String,
    INDEX idx_user_id user_id TYPE minmax GRANULARITY 8192,
    INDEX idx_workload_id workload_id TYPE bloom_filter GRANULARITY 1,
    INDEX idx_event_type event_type TYPE set(100) GRANULARITY 1
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, timestamp, event_id)
TTL timestamp + INTERVAL 90 DAY;
```

**Columns:**
- `event_id`: Unique event identifier
- `timestamp`: Event timestamp with millisecond precision
- `user_id`: User identifier
- `workload_id`: Workload identifier
- `event_type`: Type of event (start, stop, metric, error, etc.)
- `event_category`: Event category (compute, storage, network, etc.)
- `metrics`: Nested structure for metric data
- `dimensions`: Key-value pairs for dimensional data
- `metadata`: Additional event data (JSON string)

---

#### aggregated_metrics
Pre-aggregated metrics for fast querying.

```sql
CREATE MATERIALIZED VIEW aggregated_metrics
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (user_id, workload_id, hour, metric_name)
AS SELECT
    toStartOfHour(timestamp) as hour,
    user_id,
    workload_id,
    metrics.name[1] as metric_name,
    sum(metrics.value[1]) as total_value,
    count() as event_count,
    min(metrics.value[1]) as min_value,
    max(metrics.value[1]) as max_value,
    avg(metrics.value[1]) as avg_value
FROM workload_events
WHERE event_type = 'metric'
GROUP BY hour, user_id, workload_id, metric_name;
```

---

#### user_activity
Tracks user activity patterns.

```sql
CREATE TABLE user_activity (
    date Date DEFAULT today(),
    user_id UInt32,
    action String,
    count UInt64,
    total_duration_ms UInt64,
    metadata String
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (date, user_id, action);
```

---

### ClickHouse Views

#### recent_workloads
View for recently active workloads.

```sql
CREATE VIEW recent_workloads AS
SELECT
    workload_id,
    user_id,
    max(timestamp) as last_seen,
    count() as event_count,
    uniqExact(event_type) as unique_event_types
FROM workload_events
WHERE timestamp > now() - INTERVAL 7 DAY
GROUP BY workload_id, user_id;
```

---

## Migration Management

### Alembic Configuration

The system uses Alembic for PostgreSQL schema migrations.

```python
# alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://user:pass@localhost/netra_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic
```

### Creating Migrations

```bash
# Create a new migration
alembic revision -m "Add new feature table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Example Migration

```python
"""Add performance_metrics to supply_catalog

Revision ID: abc123
Revises: def456
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('supply_catalog', 
        sa.Column('performance_metrics', postgresql.JSONB(), nullable=True)
    )
    op.create_index('idx_supply_catalog_performance', 
        'supply_catalog', 
        ['performance_metrics'],
        postgresql_using='gin'
    )

def downgrade():
    op.drop_index('idx_supply_catalog_performance', 'supply_catalog')
    op.drop_column('supply_catalog', 'performance_metrics')
```

---

## Database Best Practices

### Indexing Strategy

1. **Primary Keys**: All tables have UUID or serial primary keys
2. **Foreign Keys**: Indexed for join performance
3. **Timestamp Columns**: Indexed for time-based queries
4. **JSON Columns**: GIN indexes for JSONB search
5. **Vector Columns**: IVFFlat indexes for similarity search

### Performance Optimization

1. **Connection Pooling**: 
   ```python
   # SQLAlchemy configuration
   pool_size=20
   max_overflow=40
   pool_pre_ping=True
   ```

2. **Query Optimization**:
   - Use EXPLAIN ANALYZE for query planning
   - Batch inserts for bulk data
   - Prepared statements for repeated queries

3. **Partitioning**:
   - ClickHouse: Monthly partitions for time-series data
   - PostgreSQL: Consider partitioning for large tables

### Data Retention

1. **PostgreSQL**:
   - User data: Retained indefinitely
   - Audit logs: 2 years retention
   - Threads/Messages: User-controlled deletion

2. **ClickHouse**:
   - Workload events: 90-day TTL
   - Aggregated metrics: 1-year retention
   - User activity: 6-month retention

### Backup Strategy

1. **PostgreSQL**:
   ```bash
   # Daily backups
   pg_dump netra_db > backup_$(date +%Y%m%d).sql
   
   # Point-in-time recovery with WAL archiving
   archive_mode = on
   archive_command = 'cp %p /backup/wal/%f'
   ```

2. **ClickHouse**:
   ```bash
   # Table backups
   clickhouse-client --query="BACKUP TABLE workload_events TO '/backup/'"
   ```

### Security Considerations

1. **Encryption**:
   - Passwords: Bcrypt hashing
   - API keys: SHA-256 hashing
   - Sensitive data: AES-256 encryption

2. **Access Control**:
   - Row-level security for multi-tenant data
   - Column-level encryption for PII
   - Audit logging for compliance

3. **SQL Injection Prevention**:
   - Parameterized queries only
   - Input validation
   - Stored procedures for complex operations

---

## Monitoring

### Key Metrics to Monitor

1. **PostgreSQL**:
   - Connection pool usage
   - Query execution time
   - Table bloat
   - Index usage
   - Replication lag

2. **ClickHouse**:
   - Query performance
   - Disk usage
   - Memory consumption
   - Merge operations
   - Replication status

### Health Checks

```sql
-- PostgreSQL health check
SELECT 
    current_database() as database,
    pg_database_size(current_database()) as size_bytes,
    (SELECT count(*) FROM pg_stat_activity) as active_connections,
    (SELECT count(*) FROM pg_stat_activity WHERE state = 'idle') as idle_connections;

-- ClickHouse health check
SELECT 
    name,
    engine,
    total_rows,
    total_bytes,
    formatReadableSize(total_bytes) as size
FROM system.tables
WHERE database = 'netra_analytics';
```

---

## Troubleshooting

### Common Issues

1. **Connection Pool Exhaustion**:
   - Increase pool_size and max_overflow
   - Check for connection leaks
   - Implement connection timeout

2. **Slow Queries**:
   - Add appropriate indexes
   - Optimize query structure
   - Consider materialized views

3. **Storage Issues**:
   - Implement data archival
   - Configure TTL policies
   - Monitor disk usage

### Useful Queries

```sql
-- Find slow queries (PostgreSQL)
SELECT 
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check table sizes (PostgreSQL)
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Monitor ClickHouse merges
SELECT 
    table,
    partition,
    elapsed,
    progress,
    formatReadableSize(total_size_bytes_compressed) as compressed_size
FROM system.merges;
```