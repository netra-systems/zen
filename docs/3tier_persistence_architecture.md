# 3-Tier Agent Persistence Architecture

## Overview

The 3-Tier Agent Persistence Architecture provides enterprise-grade reliability and data integrity for AI agent state management. This architecture implements a sophisticated failover chain with three distinct storage tiers, each optimized for specific performance and reliability requirements.

## Architecture Components

### Storage Tiers

#### 1. Redis (PRIMARY) - Active State Storage
- **Purpose**: High-performance storage for active agent states
- **Performance**: Sub-100ms read/write operations
- **Use Cases**: Real-time agent execution, active workflows
- **TTL Management**: Automatic expiration for memory optimization
- **Related Files**:
  - [`netra_backend/app/redis_manager.py`](../netra_backend/app/redis_manager.py) - Redis connection management
  - [`netra_backend/app/services/state_cache_manager.py`](../netra_backend/app/services/state_cache_manager.py) - Primary state operations

#### 2. PostgreSQL - Critical Recovery Checkpoints
- **Purpose**: Durable storage for disaster recovery
- **Performance**: Sub-second writes with ACID guarantees
- **Use Cases**: Critical checkpoints, recovery points, compliance
- **Retention**: Long-term storage for audit trails
- **Related Files**:
  - [`netra_backend/app/db/database_manager.py`](../netra_backend/app/db/database_manager.py) - Database connection pooling
  - [`netra_backend/app/schemas/agent_state.py`](../netra_backend/app/schemas/agent_state.py) - State persistence schemas

#### 3. ClickHouse - Analytics and Archive
- **Purpose**: Cost-effective storage for completed runs
- **Performance**: Optimized for batch writes and analytics queries
- **Use Cases**: Historical analysis, cost optimization insights
- **Migration**: Automatic migration of completed states
- **Related Files**:
  - [`netra_backend/app/db/clickhouse.py`](../netra_backend/app/db/clickhouse.py) - ClickHouse client
  - [`tests/fixtures/golden_datasets.py`](../tests/fixtures/golden_datasets.py) - Test datasets for validation

### Failover Chain

```
Redis (PRIMARY) 
    ↓ (failure)
PostgreSQL (SECONDARY)
    ↓ (failure)
ClickHouse (TERTIARY)
    ↓ (failure)  
Legacy Storage (FALLBACK)
```

## Core Modules

### State Management

#### DeepAgentState
- **Location**: [`netra_backend/app/agents/state.py`](../netra_backend/app/agents/state.py)
- **Purpose**: Core state model for agent execution
- **Features**:
  - Hierarchical state tracking
  - Metadata management
  - Version control support

#### StatePersistenceRequest
- **Location**: [`netra_backend/app/schemas/agent_state.py`](../netra_backend/app/schemas/agent_state.py)
- **Purpose**: Request model for persistence operations
- **Checkpoint Types**:
  - `AUTO`: Automatic checkpoints during execution
  - `CRITICAL`: Forced checkpoints at critical points
  - `FULL`: Complete state snapshots

### Service Layer

#### StateCacheManager
- **Location**: [`netra_backend/app/services/state_cache_manager.py`](../netra_backend/app/services/state_cache_manager.py)
- **Key Methods**:
  - `save_primary_state()`: Save to Redis with versioning
  - `load_primary_state()`: Load from Redis with failover
  - `mark_state_completed()`: Trigger migration to analytics tier

#### Optimized Persistence Service
- **Documentation**: [`docs/optimized_state_persistence.md`](optimized_state_persistence.md)
- **Features**:
  - Smart state diffing
  - Selective persistence
  - Async monitoring
  - Connection pool optimization

## Testing Infrastructure

### Integration Tests
- **Main Test File**: [`tests/integration/test_3tier_persistence_integration.py`](../tests/integration/test_3tier_persistence_integration.py)
- **Test Coverage**:
  - Primary Redis operations
  - PostgreSQL checkpoint creation
  - ClickHouse migration scheduling
  - Failover chain validation
  - Cross-database consistency
  - Atomic transaction guarantees
  - Concurrent agent persistence
  - 24-hour lifecycle validation
  - Enterprise workload scenarios

### Golden Datasets
- **Location**: [`tests/fixtures/golden_datasets.py`](../tests/fixtures/golden_datasets.py)
- **Datasets**:
  - `GOLDEN_SIMPLE_FLOW`: Basic free tier workflow
  - `GOLDEN_MULTI_AGENT_FLOW`: Complex multi-agent collaboration
  - `GOLDEN_LONG_RUNNING_FLOW`: 24-hour monitoring scenarios
  - `GOLDEN_HIGH_CONCURRENCY_FLOW`: 100+ concurrent agents
  - `GOLDEN_RECOVERY_FLOW`: Failure and recovery scenarios

### Related Test Files
- [`netra_backend/tests/services/test_state_persistence_integration_critical.py`](../netra_backend/tests/services/test_state_persistence_integration_critical.py) - Critical path testing
- [`netra_backend/tests/services/test_optimized_persistence_integration.py`](../netra_backend/tests/services/test_optimized_persistence_integration.py) - Optimization validation

## Configuration

### Environment Variables

#### Redis Configuration
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password
REDIS_SSL=false
```

#### PostgreSQL Configuration
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/netra
DB_POOL_SIZE=15        # Optimized for persistence workload
DB_MAX_OVERFLOW=25     # Higher burst capacity
DB_POOL_TIMEOUT=3.0    # Faster failure detection
```

#### ClickHouse Configuration
```bash
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=netra_analytics
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
```

#### Persistence Optimization
```bash
ENABLE_OPTIMIZED_PERSISTENCE=true      # Enable optimizations
OPTIMIZED_PERSISTENCE_MONITORING=true  # Async metrics collection
```

### Connection Pool Settings

| Environment | Redis Pool | PostgreSQL Pool | ClickHouse Pool |
|-------------|------------|-----------------|-----------------|
| Development | 5 connections | 10 connections | 5 connections |
| Staging | 10 connections | 15 connections | 10 connections |
| Production | 20 connections | 25 connections | 15 connections |

## Business Value Justification

### Customer Segments
- **Enterprise** ($25K+ MRR): Mission-critical workloads requiring zero data loss
- **Mid-Market** ($5K-25K MRR): High-value workflows needing reliability
- **Early** ($500-5K MRR): Growing workloads with increasing persistence needs
- **Free Tier**: Basic persistence with Redis-only storage

### Value Propositions

#### 1. Zero Data Loss Guarantee
- **Implementation**: Multi-tier persistence with atomic transactions
- **Customer Impact**: Trust in platform for critical operations
- **Revenue Impact**: Enables enterprise contracts with SLA guarantees

#### 2. Sub-100ms State Access
- **Implementation**: Redis primary storage with optimized serialization
- **Customer Impact**: Real-time agent responsiveness
- **Revenue Impact**: Supports high-frequency trading and monitoring use cases

#### 3. Disaster Recovery
- **Implementation**: PostgreSQL checkpoints with point-in-time recovery
- **Customer Impact**: Business continuity during failures
- **Revenue Impact**: Reduces churn from data loss incidents

#### 4. Cost Optimization Analytics
- **Implementation**: ClickHouse analytics on completed runs
- **Customer Impact**: Insights into AI spend optimization
- **Revenue Impact**: Increases platform stickiness and expansion

## Performance Metrics

### Target SLAs

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Redis Write Latency | < 50ms | < 100ms |
| Redis Read Latency | < 20ms | < 50ms |
| PostgreSQL Checkpoint | < 500ms | < 1000ms |
| ClickHouse Migration | < 2s batch | < 5s batch |
| Failover Recovery Time | < 5s | < 30s |
| Data Integrity Score | 100% | >= 99.9% |

### Monitoring

#### Key Performance Indicators
1. **Persistence Success Rate**: > 99.9%
2. **Average Latency**: < 100ms for 95th percentile
3. **Failover Frequency**: < 0.1% of operations
4. **Data Consistency Score**: 100%

#### Metrics Collection
- **Prometheus Metrics**: Real-time performance monitoring
- **Grafana Dashboards**: Visual performance tracking
- **Alert Thresholds**: Automatic alerting on SLA breaches

## Operational Procedures

### Deployment

#### Local Development
```bash
# Start all required services
docker-compose -f docker-compose.dev.yml up -d redis postgres clickhouse

# Run integration tests
python -m pytest tests/integration/test_3tier_persistence_integration.py -v
```

#### Staging Validation
```bash
# Deploy to staging
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Run persistence validation
ENABLE_OPTIMIZED_PERSISTENCE=true python unified_test_runner.py --category integration --env staging
```

#### Production Rollout
1. Enable optimized persistence in canary (10% traffic)
2. Monitor metrics for 24 hours
3. Gradual rollout to 100% if metrics are favorable
4. Full rollback capability via environment variables

### Maintenance

#### Redis Maintenance
- **Memory Monitoring**: Alert when usage > 80%
- **TTL Verification**: Ensure expired keys are cleaned
- **Connection Pool Health**: Monitor pool utilization

#### PostgreSQL Maintenance
- **Checkpoint Cleanup**: Archive old checkpoints > 30 days
- **Index Optimization**: Regular VACUUM and ANALYZE
- **Connection Monitoring**: Track slow queries

#### ClickHouse Maintenance
- **Partition Management**: Monthly partitions for efficient queries
- **Compression**: Automatic compression for older data
- **Query Optimization**: Materialized views for common queries

### Troubleshooting

#### Common Issues

1. **Redis Connection Timeouts**
   - **Symptom**: `RedisConnectionError` in logs
   - **Solution**: Check Redis server health and network connectivity
   - **Verification**: `redis-cli ping` should return PONG

2. **PostgreSQL Checkpoint Failures**
   - **Symptom**: `checkpoint creation failed` in logs
   - **Solution**: Check disk space and database permissions
   - **Verification**: Manual checkpoint creation test

3. **ClickHouse Migration Delays**
   - **Symptom**: Completed states not appearing in analytics
   - **Solution**: Check migration queue and ClickHouse availability
   - **Verification**: Query migration status table

4. **Cross-Database Inconsistency**
   - **Symptom**: Data mismatch between tiers
   - **Solution**: Run consistency validation and repair script
   - **Verification**: Cross-tier hash comparison

## Security Considerations

### Data Protection
- **Encryption at Rest**: All tiers support encryption
- **Encryption in Transit**: TLS/SSL for all connections
- **Access Control**: Role-based access per tier
- **Audit Logging**: Complete audit trail of all operations

### Compliance
- **GDPR**: Data retention and deletion policies
- **SOC2**: Access controls and audit trails
- **HIPAA**: Encryption and access logging (if required)

## Future Enhancements

### Planned Features
1. **Global Distribution**: Multi-region replication for Redis
2. **Intelligent Caching**: ML-based cache warming
3. **Compression**: State compression for large payloads
4. **Streaming Analytics**: Real-time analytics on state changes

### Performance Optimizations
1. **Batch Persistence**: Group multiple updates
2. **Write-Behind Caching**: Asynchronous persistence
3. **Connection Multiplexing**: Reduced connection overhead
4. **Query Optimization**: Prepared statements and caching

## Related Documentation

- [`SPEC/database_connectivity_architecture.xml`](../SPEC/database_connectivity_architecture.xml) - Database connection architecture
- [`SPEC/unified_environment_management.xml`](../SPEC/unified_environment_management.xml) - Environment configuration
- [`SPEC/learnings/state_persistence_optimization.xml`](../SPEC/learnings/state_persistence_optimization.xml) - Optimization learnings
- [`SPEC/learnings/state_persistence_foreign_key.xml`](../SPEC/learnings/state_persistence_foreign_key.xml) - Foreign key considerations
- [`docs/optimized_state_persistence.md`](optimized_state_persistence.md) - Optimization features
- [`LLM_MASTER_INDEX.md`](../LLM_MASTER_INDEX.md) - Master navigation index

## Support and Monitoring

### Health Checks
- **Endpoint**: `/health/persistence`
- **Checks**: All three tiers connectivity and performance
- **Frequency**: Every 30 seconds

### Dashboards
- **Grafana**: `https://monitoring.netrasystems.ai/dashboard/persistence`
- **Metrics**: Latency, throughput, error rates, failover events

### Alerts
- **PagerDuty**: Critical persistence failures
- **Slack**: Performance degradation warnings
- **Email**: Daily persistence report

## Contributing

When modifying the persistence architecture:

1. Update this documentation
2. Add/update integration tests
3. Update golden datasets if needed
4. Run full test suite
5. Update monitoring dashboards
6. Document in SPEC files