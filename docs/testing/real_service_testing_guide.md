# Real Service Testing Guide

## Overview

This guide provides comprehensive documentation for running and managing real service tests in the Netra AI Platform. Real service tests validate the platform's functionality with actual external services including LLM providers, databases, and caching systems.

## Table of Contents

1. [Test Categories](#test-categories)
2. [Environment Setup](#environment-setup)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [Metrics and Reporting](#metrics-and-reporting)
6. [Cost Management](#cost-management)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Test Categories

### Real Service Test Types

| Category | Description | Required Services | Test Count |
|----------|-------------|-------------------|------------|
| **real_llm** | Tests with actual LLM API calls | OpenAI, Anthropic, Google APIs | 90+ tests |
| **real_database** | PostgreSQL operations | PostgreSQL instance | 20+ tests |
| **real_redis** | Redis cache and pub/sub | Redis server | 15+ tests |
| **real_clickhouse** | Analytics and metrics | ClickHouse database | 25+ tests |
| **e2e** | End-to-end workflows | All services | 50+ tests |

### Test Files

#### Core Real Service Tests
- `test_real_services_comprehensive.py` - Main comprehensive test suite
- `test_example_prompts_e2e_real.py` - 90 variations of example prompts
- `test_realistic_data_integration.py` - Real data integration scenarios
- `test_categories.py` - Test categorization validation

#### Service-Specific Tests
- `services/test_agent_service_orchestration.py` - Agent orchestration with real LLMs
- `clickhouse/test_realistic_clickhouse_operations.py` - ClickHouse with real data
- `services/test_synthetic_data_service_v3.py` - Synthetic data generation
- `llm/test_structured_generation.py` - Structured output from LLMs

## Environment Setup

### Required Environment Variables

```bash
# LLM Provider API Keys
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-gemini-key"

# Database Connections
export DATABASE_URL="postgresql://user:pass@localhost/netra"
export CLICKHOUSE_URL="clickhouse://localhost:9000/default"
export REDIS_URL="redis://localhost:6379"

# Test Flags
export ENABLE_REAL_LLM_TESTING="true"
export ENABLE_REAL_DB_TESTING="true"
export ENABLE_REAL_REDIS_TESTING="true"
export ENABLE_REAL_CLICKHOUSE_TESTING="true"
```

### Test Database Setup

```sql
-- PostgreSQL test database
CREATE DATABASE netra_test;
GRANT ALL PRIVILEGES ON DATABASE netra_test TO test_user;

-- ClickHouse test database
CREATE DATABASE IF NOT EXISTS netra_test;
```

### Redis Test Configuration

```bash
# Use separate Redis database for tests
redis-cli SELECT 1  # Use DB 1 for tests
```

## Running Tests

### Quick Start

```bash
# Run all real service tests (Alpine containers automatically used)
python tests/unified_test_runner.py --real-services

# Run with specific LLM model using Alpine containers
python tests/unified_test_runner.py --real-services --real-llm --llm-model gemini-1.5-flash

# Run specific category with Alpine containers
python tests/unified_test_runner.py --category real_llm --real-services

# Force regular containers (if needed for debugging)
python tests/unified_test_runner.py --real-services --no-alpine

# Enhanced runner with detailed reporting
python scripts/run_real_service_tests_enhanced.py --model gemini-1.5-flash --parallel 2
```

### Alpine Container Performance Benefits

**CRITICAL: Alpine containers are now the DEFAULT for all test environments, providing:**

- **3x faster startup times** (5-8s vs 15-20s regular containers)
- **50% memory reduction** (768MB vs 1536MB total environment)
- **78% smaller image sizes** (186MB vs 847MB backend image)
- **2x more parallel test capacity** due to reduced resource usage

**Alpine vs Regular Container Comparison:**

| Test Scenario | Regular Containers | Alpine Containers | Improvement |
|---------------|-------------------|-------------------|-------------|
| **Cold Start** | 15-20 seconds | 5-8 seconds | **3x faster** |
| **Memory Usage** | 1536MB total | 768MB total | **50% less** |
| **Parallel Capacity** | 4 test runners | 8 test runners | **2x more** |
| **Build Time** | 180-240s | 60-90s | **67% faster** |

### Test Levels

**With Alpine Containers (Default):**

| Level | Command | Duration | Cost | Use Case |
|-------|---------|----------|------|----------|
| **Quick** | `--category real_llm --parallel 8` | 3-5 min | ~$0.50 | Development |
| **Standard** | `--real-services` | 8-15 min | ~$2.00 | Pre-commit |
| **Comprehensive** | `--categories unit integration api --real-llm` | 15-25 min | ~$5.00 | Pre-release |
| **Full E2E** | All categories with retries | 30-45 min | ~$10.00 | Production |

**Note:** Alpine containers enable 2x higher parallelism and 50% faster execution compared to regular containers.

### Parallel Execution

```bash
# Sequential (avoid rate limits with production keys)
python test_runner.py --real-llm --parallel 1

# Parallel with test keys
python test_runner.py --real-llm --parallel 4

# Auto-detect optimal parallelism
python test_runner.py --real-llm --parallel auto
```

## Test Coverage

### Current Coverage Statistics

| Component | Mock Tests | Real Tests | Coverage |
|-----------|------------|------------|----------|
| Agent Service | 45 tests | 15 tests | 92% |
| LLM Manager | 30 tests | 10 tests | 88% |
| Database Repos | 60 tests | 20 tests | 95% |
| Quality Gates | 25 tests | 8 tests | 90% |
| Cache Service | 20 tests | 5 tests | 85% |
| **Total** | **2574 tests** | **114 tests** | **97%** |

### Coverage Gaps

Areas needing additional real service tests:
- WebSocket real-time communication with actual clients
- Long-running agent tasks (>5 minutes)
- High-concurrency scenarios (100+ simultaneous requests)
- Cross-service transaction rollbacks
- Rate limit handling and retry logic

## Metrics and Reporting

### Test Metrics Collected

```json
{
  "llm_calls": {
    "gemini-1.5-flash": 45,
    "gpt-3.5-turbo": 12,
    "claude-3-sonnet": 8
  },
  "llm_costs": {
    "total": 2.35,
    "by_model": {
      "gemini-1.5-flash": 0.45,
      "gpt-3.5-turbo": 0.90,
      "claude-3-sonnet": 1.00
    }
  },
  "db_queries": {
    "postgresql": 234,
    "clickhouse": 89,
    "redis": 156
  },
  "cache_stats": {
    "hits": 78,
    "misses": 22,
    "hit_rate": 0.78
  },
  "quality_scores": {
    "average": 0.82,
    "min": 0.65,
    "max": 0.95
  },
  "test_duration": 1823.5
}
```

### Report Generation

```bash
# Generate comprehensive report
python scripts/run_real_service_tests_enhanced.py --model gemini-1.5-flash

# Reports generated in:
# - test_reports/real_services/latest_real_service_report.json
# - test_reports/real_services/latest_real_service_report.md
# - test_reports/real_services/latest_real_service_report.html
```

### Report Sections

1. **Executive Summary** - Pass/fail rates, total duration, cost
2. **LLM Usage** - Calls per model, token usage, costs
3. **Database Performance** - Query counts, latencies, connection pools
4. **Cache Effectiveness** - Hit rates, memory usage
5. **Quality Metrics** - Score distributions, validation results
6. **Error Analysis** - Failures, timeouts, rate limits

## Cost Management

### LLM API Costs (per 1000 tokens)

| Model | Input Cost | Output Cost | Avg Test Cost |
|-------|------------|-------------|---------------|
| gemini-1.5-flash | $0.00035 | $0.0007 | $0.01/test |
| gemini-2.5-pro | $0.0035 | $0.007 | $0.05/test |
| gpt-3.5-turbo | $0.0005 | $0.0015 | $0.02/test |
| gpt-4 | $0.03 | $0.06 | $0.10/test |
| claude-3-sonnet | $0.003 | $0.015 | $0.04/test |

### Cost Optimization Strategies

```bash
# Use cheaper models for most tests
export DEFAULT_TEST_MODEL="gemini-1.5-flash"

# Run expensive tests selectively
pytest -m "real_llm and not expensive" 

# Cache LLM responses
export ENABLE_LLM_CACHE="true"
export LLM_CACHE_TTL="3600"

# Limit test scope
python test_runner.py --real-llm -k "critical"
```

### Monthly Budget Example

```yaml
development:
  daily_runs: 10
  model: gemini-1.5-flash
  tests_per_run: 50
  monthly_cost: $15

staging:
  daily_runs: 5
  model: mix (flash + pro)
  tests_per_run: 100
  monthly_cost: $75

production:
  weekly_runs: 2
  model: comprehensive
  tests_per_run: 500
  monthly_cost: $200
```

## Best Practices

### 1. Test Data Management

```python
# Use consistent seed data
@pytest.fixture
async def seed_data():
    """Load consistent test data for reproducibility"""
    data = load_json("test_data/seed/optimization.json")
    await db.insert_batch(data)
    yield data
    await db.cleanup()

# Generate synthetic data on-demand
context = await synthetic_service.generate_context(
    scenario="cost_optimization",
    complexity="medium"
)
```

### 2. API Key Management

```bash
# Use separate keys for testing
export TEST_ANTHROPIC_API_KEY="test-key-with-lower-limits"
export TEST_OPENAI_API_KEY="test-key-with-lower-limits"

# Rotate keys to avoid rate limits
export API_KEY_POOL="key1,key2,key3"
```

### 3. Error Handling

```python
@pytest.mark.real_llm
@pytest.mark.retry(3)  # Retry flaky tests
async def test_with_retry():
    """Test with automatic retry on failure"""
    try:
        response = await llm.generate(prompt)
    except RateLimitError:
        await asyncio.sleep(60)  # Wait and retry
        response = await llm.generate(prompt)
```

### 4. Performance Monitoring

```python
# Track test performance
@measure_performance
async def test_latency_critical():
    """Test with performance measurement"""
    start = time.time()
    result = await service.process()
    latency = time.time() - start
    
    assert latency < 5.0  # Max 5 seconds
    metrics.track_latency(latency)
```

### 5. Parallel Execution

```yaml
# config/pytest.ini configuration
[tool:pytest]
markers =
    real_services: All real service tests
    real_llm: LLM API tests
    expensive: High-cost tests
    
# Parallel execution groups
testpaths = 
    app/tests/real_llm::2  # 2 workers
    app/tests/real_db::4   # 4 workers
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Rate Limit Errors

**Problem:** `RateLimitError: Too many requests`

**Solution:**
```bash
# Reduce parallelism
python test_runner.py --real-llm --parallel 1

# Add delays between tests
export TEST_DELAY_SECONDS=2

# Use different API keys
export API_KEY_ROTATION=true
```

#### 2. Database Connection Issues

**Problem:** `psycopg2.OperationalError: connection refused`

**Solution:**
```bash
# Check database is running
pg_isready -h localhost -p 5432

# Verify connection string
psql $#removed-legacy-c "SELECT 1"

# Use connection pooling
export DB_POOL_SIZE=5
export DB_MAX_OVERFLOW=10
```

#### 3. Timeout Errors

**Problem:** `TimeoutError: Test exceeded 300s`

**Solution:**
```bash
# Increase timeout
python test_runner.py --real-llm --llm-timeout 120

# Run long tests separately
pytest -m "real_llm and long_running" --timeout=600
```

#### 4. Cache Inconsistencies

**Problem:** Stale cache affecting test results

**Solution:**
```bash
# Clear cache before tests
redis-cli FLUSHDB

# Disable cache for debugging
export DISABLE_LLM_CACHE=true

# Use unique cache keys
export CACHE_KEY_PREFIX="test_$(date +%s)_"
```

#### 5. Quality Gate Failures

**Problem:** `AssertionError: Quality score 0.45 < 0.6`

**Solution:**
```python
# Adjust thresholds for tests
quality_result = await quality_gate.validate(
    response,
    min_score=0.5,  # Lower threshold for tests
    content_type="OPTIMIZATION"
)

# Skip quality checks for specific tests
@pytest.mark.skip_quality_gate
async def test_experimental_feature():
    pass
```

#### 6. Alpine Container Issues

**Problem:** `Error: No such image: netra-alpine-test-backend:latest`

**Solution:**
```bash
# Force rebuild Alpine images
python scripts/docker_manual.py clean
python scripts/docker_manual.py start --alpine

# Verify Alpine containers are running
docker ps --format "table {{.Image}}\t{{.Names}}" | grep alpine
```

**Problem:** `Package not found in Alpine container`

**Solution:**
```bash
# Check Alpine package availability
docker exec container-name apk search package-name

# Install missing packages in Alpine Dockerfile
# Add to docker/backend.alpine.Dockerfile:
RUN apk add --no-cache package-name
```

**Problem:** `glibc compatibility issues`

**Solution:**
```bash
# Add compatibility layer to Alpine Dockerfile if needed
RUN apk add --no-cache libc6-compat

# Or use musl-compatible alternatives
RUN apk add --no-cache musl-dev
```

### Debugging Commands

**General Test Debugging:**
```bash
# Verbose test output
python tests/unified_test_runner.py --real-services -v

# Run single test with real services
python tests/unified_test_runner.py --real-services -k "test_specific_function"

# Generate detailed logs
export LOG_LEVEL=DEBUG
export LOG_FILE=test_debug.log

# Profile test performance
pytest --profile --profile-svg
```

**Alpine Container Debugging:**
```bash
# Verify Alpine containers are being used
docker ps --format "table {{.Image}}\t{{.Names}}\t{{.Status}}" | grep alpine

# Check Alpine container resource usage
docker stats --no-stream | grep alpine

# Monitor Alpine container startup time
time python tests/unified_test_runner.py --category smoke --real-services

# Compare Alpine vs Regular performance
time python tests/unified_test_runner.py --category smoke --real-services --alpine
time python tests/unified_test_runner.py --category smoke --real-services --no-alpine

# Shell into Alpine container for debugging (use sh, not bash)
docker exec -it netra_alpine-test-backend_1 sh

# Check Alpine package versions
docker exec container-name apk info -v

# View Alpine container logs
docker logs netra_alpine-test-backend_1 -f
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Real Service Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  real-service-tests:
    runs-on: warp-custom-default
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run Real Service Tests
      env:
        ANTHROPIC_API_KEY: ${{ secrets.TEST_ANTHROPIC_API_KEY }}
        OPENAI_API_KEY: ${{ secrets.TEST_OPENAI_API_KEY }}
        GEMINI_API_KEY: ${{ secrets.TEST_GEMINI_API_KEY }}
        DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
        REDIS_URL: ${{ secrets.TEST_REDIS_URL }}
        CLICKHOUSE_URL: ${{ secrets.TEST_CLICKHOUSE_URL }}
      run: |
        python scripts/run_real_service_tests_enhanced.py \
          --model gemini-1.5-flash \
          --parallel 2 \
          --timeout 300
    
    - name: Upload Test Reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: real-service-test-reports
        path: test_reports/real_services/
```

## Monitoring and Alerting

### Metrics to Track

```python
# Key metrics for monitoring
METRICS = {
    "test_pass_rate": 0.95,  # Alert if < 95%
    "avg_llm_latency": 3.0,  # Alert if > 3s
    "cache_hit_rate": 0.70,  # Alert if < 70%
    "quality_score": 0.60,   # Alert if < 0.6
    "api_cost_daily": 10.00, # Alert if > $10/day
}
```

### Alerting Rules

```yaml
alerts:
  - name: RealServiceTestFailureRate
    expr: test_pass_rate < 0.9
    for: 5m
    annotations:
      summary: "High failure rate in real service tests"
      
  - name: LLMCostSpike
    expr: daily_llm_cost > 20
    for: 1h
    annotations:
      summary: "LLM API costs exceeding budget"
```

## Conclusion

Real service testing is critical for validating the Netra AI Platform's functionality in production-like conditions. By following this guide, you can:

1. **Run comprehensive tests** with actual external services
2. **Monitor costs** and optimize API usage
3. **Generate detailed reports** for analysis
4. **Troubleshoot issues** effectively
5. **Maintain high quality** standards

Remember to:
- Use test API keys with appropriate rate limits
- Run real service tests selectively to control costs
- Monitor metrics and set up alerts
- Keep test data consistent and reproducible
- Document any new patterns or issues discovered

For additional support, refer to the [Testing Specification](../SPEC/testing.xml) and [Real LLM Testing](../SPEC/testing.xml#real_llm_testing) documentation.