# Real Services Integration Testing

This directory contains comprehensive integration tests that use **actual service connections** instead of mocks to validate real-world multi-agent orchestration scenarios.

## 🎯 Purpose

These tests are designed to catch integration issues that only appear in production environments and cannot be detected by mocked tests. They validate:

- Real LLM API integrations with OpenAI and Anthropic
- Actual PostgreSQL database transactions and consistency
- Real Redis state management and caching
- Cross-service data synchronization
- Network failure and timeout handling
- Concurrent agent execution patterns
- Service health monitoring and recovery

## 🛠️ Requirements

### Environment Variables

The following environment variables must be set to run these tests:

```bash
# LLM Providers (at least one required)
export OPENAI_API_KEY="sk-..."              # OpenAI API key
export ANTHROPIC_API_KEY="sk-ant-..."       # Anthropic Claude API key

# Database (required)
export DATABASE_URL="postgresql://user:pass@host:port/dbname"

# Redis (required)  
export REDIS_URL="redis://localhost:6379"   # Redis connection string

# Auth Service (optional)
export AUTH_SERVICE_URL="http://localhost:8001"  # Auth service endpoint
```

### Service Dependencies

Ensure the following services are running and accessible:

1. **PostgreSQL Database**
   - Version 12+ recommended
   - Database must allow table creation for test isolation
   - Connection pool should support concurrent connections

2. **Redis Server**
   - Version 6+ recommended
   - Should support streams, lists, and hash operations
   - Memory should allow for test data storage

3. **LLM Provider APIs**
   - OpenAI: Valid API key with sufficient quota
   - Anthropic: Valid API key with sufficient quota
   - Network access to API endpoints required

4. **Auth Service** (optional)
   - Local auth service instance
   - Health check endpoint available

## 🚀 Running Tests

### Basic Execution

```bash
# Run all real service tests
pytest netra_backend/tests/integration/real_services/ -m real_services -v

# Run with detailed output
pytest netra_backend/tests/integration/real_services/ -m real_services -v --tb=long

# Run specific test
pytest netra_backend/tests/integration/real_services/test_multi_agent_real_services.py::TestMultiAgentRealServices::test_real_database_agent_state_persistence -v
```

### Test Categories

```bash
# Database-only tests
pytest -k "database" -m real_services

# LLM-only tests  
pytest -k "llm" -m real_services

# Redis-only tests
pytest -k "redis" -m real_services

# Cross-service tests
pytest -k "cross_service or consistency" -m real_services

# Concurrent execution tests
pytest -k "concurrent" -m real_services
```

### Selective Execution

Tests automatically skip if required services are not available:

```bash
# Skip tests requiring specific services
pytest -m "real_services and not (openai or anthropic)" # Skip LLM tests
pytest -m "real_services and not database"              # Skip DB tests
pytest -m "real_services and not redis"                 # Skip Redis tests
```

## 📋 Test Coverage

### Multi-Agent Orchestration Tests

| Test | Services | Description |
|------|----------|-------------|
| `test_real_database_agent_state_persistence` | PostgreSQL | Agent state CRUD operations with real transactions |
| `test_real_redis_state_management` | Redis | Session and state management with TTL and data structures |
| `test_real_openai_llm_integration` | OpenAI | Actual GPT model calls with response validation |
| `test_real_anthropic_llm_integration` | Anthropic | Actual Claude model calls with response validation |
| `test_real_cross_service_data_consistency` | PostgreSQL + Redis | Data synchronization across services |
| `test_real_database_connection_retry_logic` | PostgreSQL | Connection failure recovery and retry mechanisms |
| `test_real_redis_connection_failure_handling` | Redis | Redis connection resilience and pipeline operations |
| `test_real_message_queue_integration` | Redis | Message queue functionality using Redis streams/lists |
| `test_real_network_timeout_handling` | LLM APIs | Network timeout scenarios and error handling |
| `test_real_multi_agent_coordination_with_llm` | All | End-to-end multi-agent workflow with real LLM calls |
| `test_real_database_transaction_rollback` | PostgreSQL | Transaction rollback scenarios and consistency |
| `test_real_concurrent_agent_execution` | PostgreSQL + Redis | Concurrent agent execution patterns |
| `test_real_service_health_monitoring` | All | Health check implementation across services |

### Production Scenarios Validated

1. **Database Consistency**
   - ACID transaction compliance
   - Connection pool management
   - Deadlock detection and resolution
   - Rollback scenarios

2. **Redis Operations**
   - Key expiration and TTL management
   - Pipeline operation atomicity
   - Memory usage optimization
   - Connection pooling

3. **LLM Integration**
   - API rate limiting compliance
   - Response parsing and validation
   - Error handling for API failures
   - Token usage tracking

4. **Cross-Service Scenarios**
   - Data consistency during failures
   - Service discovery and failover
   - Message routing and delivery
   - State synchronization

5. **Failure Scenarios**
   - Network partitions
   - Service unavailability
   - Timeout handling
   - Graceful degradation

## 🔧 Configuration

### Test Database Setup

The tests automatically create required tables but you may want to pre-configure:

```sql
-- Optional: Create dedicated test database
CREATE DATABASE netra_test;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE netra_test TO test_user;
```

### Redis Configuration

Recommended Redis configuration for testing:

```conf
# redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
timeout 300
tcp-keepalive 60
```

### Environment File

Create a `.env.test` file for consistent configuration:

```bash
# .env.test
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
DATABASE_URL=postgresql://testuser:testpass@localhost:5432/netra_test
REDIS_URL=redis://localhost:6379/1
AUTH_SERVICE_URL=http://localhost:8001
```

## 🚨 Important Notes

### Cost Considerations

- **LLM API Calls**: These tests make actual API calls which incur costs
- **Rate Limits**: Respect provider rate limits to avoid test failures
- **Token Usage**: Tests use minimal tokens but costs can accumulate

### Test Isolation

- Each test creates unique identifiers to avoid conflicts
- Tests clean up their own data automatically
- Use separate Redis DB numbers for isolation (e.g., `/1`, `/2`)

### Production Safety

- **Never run against production services**
- Use dedicated test databases and Redis instances
- Ensure test API keys have appropriate usage limits
- Monitor service resource usage during test execution

### Performance Expectations

- **Database tests**: < 1 second per operation
- **Redis tests**: < 100ms per operation  
- **LLM tests**: 2-30 seconds depending on model and complexity
- **Concurrent tests**: Faster than sequential execution due to parallelism

## 🐛 Troubleshooting

### Common Issues

1. **Service Connection Failures**
   ```bash
   # Check service availability
   pg_isready -h localhost -p 5432
   redis-cli ping
   curl -s https://api.openai.com/v1/models | jq '.data[0].id'
   ```

2. **Permission Errors**
   ```bash
   # Verify database permissions
   psql $#removed-legacy-c "\l"
   
   # Verify Redis access
   redis-cli -u $REDIS_URL info replication
   ```

3. **API Key Issues**
   ```bash
   # Test OpenAI key
   curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
   
   # Test Anthropic key  
   curl -H "x-api-key: $ANTHROPIC_API_KEY" https://api.anthropic.com/v1/messages
   ```

4. **Network/Timeout Issues**
   - Increase timeout values in test configuration
   - Check firewall rules for API access
   - Verify DNS resolution for API endpoints

### Debug Mode

Run tests with debug logging:

```bash
pytest netra_backend/tests/integration/real_services/ -m real_services -v -s --log-cli-level=DEBUG
```

## 📊 Integration with CI/CD

### GitHub Actions Integration

```yaml
# .github/workflows/real-services-tests.yml
name: Real Services Integration Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:     # Manual trigger

jobs:
  real-services-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: netra_test
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
        
      redis:
        image: redis:7
        options: --health-cmd "redis-cli ping" --health-interval 10s --health-timeout 5s --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
          
      - name: Run real services tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/netra_test
          REDIS_URL: redis://localhost:6379
        run: |
          pytest netra_backend/tests/integration/real_services/ -m real_services -v --junitxml=real-services-results.xml
          
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: real-services-test-results
          path: real-services-results.xml
```

## 🎯 Business Value

These tests provide critical business value by:

- **Preventing Production Incidents**: Catch real integration issues before deployment
- **Reducing MTTR**: Faster diagnosis of production issues through realistic test scenarios  
- **Improving Reliability**: Validate actual service behavior under various conditions
- **Cost Savings**: Prevent expensive production failures and customer impact
- **Compliance**: Ensure data consistency and transaction integrity requirements

The investment in real service testing typically pays for itself by preventing a single production incident.

## 📈 Metrics and Monitoring

Key metrics tracked by these tests:

- **Response Times**: Database, Redis, and LLM API response times
- **Error Rates**: Service failure and recovery rates
- **Concurrency**: Multi-agent coordination efficiency
- **Resource Usage**: Memory and connection utilization
- **Data Consistency**: Cross-service synchronization accuracy

Monitor these metrics over time to identify performance trends and potential issues before they impact production systems.