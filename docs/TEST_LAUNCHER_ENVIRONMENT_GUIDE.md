# Test Launcher Multi-Environment Assumptions

## Overview

The Test Launcher is designed with specific assumptions about how different environments operate and what resources they require. This guide explains these assumptions to ensure proper usage and configuration.

## Environment Types

### 1. Test Environment (Default)
**Purpose**: Isolated testing with minimal external dependencies

**Assumptions**:
- Docker is available for service containers
- Services run on test-specific ports (5434, 6381, 8124)
- Separate database schemas (netra_test)
- Mock LLM acceptable for unit tests only
- Real LLM required for integration/E2E per CLAUDE.md
- Complete cleanup after test execution

**Configuration**:
```python
# Automatic for test profile
launcher = TestLauncher.for_profile(TestProfile.UNIT)  # Mock services OK
launcher = TestLauncher.for_profile(TestProfile.E2E)   # Real services required
```

### 2. Development Environment
**Purpose**: Local development with real services

**Assumptions**:
- Developer has Docker Desktop running
- Services use development ports (5432, 6379, 8123)
- Persistent data between runs
- Real LLM always enabled (per CLAUDE.md - mocks forbidden)
- Hot-reload disabled for test execution
- Shared resources with dev_launcher

**Note**: Test launcher can coexist with dev_launcher but uses different ports

### 3. CI/CD Environment
**Purpose**: Automated testing in pipelines

**Assumptions**:
- Docker-in-Docker or Kubernetes available
- Ephemeral containers and networks
- Resource limits enforced
- Parallel test execution support
- No interactive features
- Automatic cleanup mandatory
- Service discovery via environment variables

**Configuration**:
```yaml
# In CI pipeline
env:
  TEST_PROFILE: integration
  TEST_ISOLATION: full
  TEST_CLEANUP: always
```

### 4. Staging Environment
**Purpose**: Pre-production validation

**Assumptions**:
- Real cloud services (GCP/AWS)
- Production-like configurations
- Real LLM required (no mocks)
- Persistent test databases
- Network isolation from production
- Performance monitoring enabled

## Port Allocation Strategy

### Default Port Mappings

| Service | Dev Ports | Test Ports | CI/CD Ports | Rationale |
|---------|-----------|------------|-------------|-----------|
| PostgreSQL | 5432 | 5434 | Dynamic | Avoid conflicts with local dev |
| Redis | 6379 | 6381 | Dynamic | Separate cache namespaces |
| ClickHouse | 8123 | 8124 | Dynamic | Analytics isolation |
| Backend | 8000 | 8001 | Dynamic | API separation |
| Auth | 8081 | 8082 | Dynamic | Auth service isolation |
| Frontend | 3000 | 3001 | Dynamic | UI testing isolation |

### Port Discovery

The test launcher includes automatic port discovery:
```python
# Automatic port discovery for Docker containers
port_mappings = test_launcher.discover_ports()
# Updates DATABASE_URL, REDIS_URL automatically
```

## Database Assumptions

### Schema Naming
- **Development**: `netra_dev`
- **Test**: `netra_test` or `netra_test_{test_id}`
- **Staging**: `netra_staging`

### User Credentials
- **Test**: `test:test` (hardcoded for simplicity)
- **Dev**: `netra:netra123` (local development)
- **Staging**: Via secrets manager

### Migration Strategy
- Tests create fresh schemas
- Migrations run automatically for integration/E2E
- Unit tests use in-memory databases

## Service Dependencies

### By Test Profile

**Unit Tests**:
- No external services required
- All dependencies mocked
- SQLite in-memory database

**Integration Tests**:
- PostgreSQL (required)
- Redis (required)
- ClickHouse (optional)
- Real LLM (required per CLAUDE.md)

**E2E Tests**:
- All services required
- Real LLM mandatory
- WebSocket connections
- Frontend build artifacts

**Performance Tests**:
- Dedicated resource pools
- Monitoring enabled
- Isolated networks

## LLM Configuration

### Critical Assumption
Per CLAUDE.md Section 3.4:
> Mocks are forbidden in E2E testing

This means:
- **Unit tests**: Mock LLM only in test environment
- **All other tests**: Real LLM required
- **Dev/Staging**: Always real LLM

### Provider Priority
1. Gemini (default, most cost-effective)
2. OpenAI (fallback)
3. Anthropic (premium features)

Environment variables checked:
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

## Resource Management

### Container Lifecycle

**Test Environment**:
```python
# Containers created per test run
container_name = f"netra-test-{service}-{test_id}"
# Automatic cleanup after tests
cleanup_on_exit = True
```

**CI/CD**:
```yaml
# Ephemeral containers
lifecycle: ephemeral
cleanup: always
timeout: 3600  # 1 hour max
```

### Memory/CPU Limits

**Default Limits**:
- Unit tests: 1 CPU, 2GB RAM
- Integration: 2 CPU, 4GB RAM
- E2E: 4 CPU, 8GB RAM
- Performance: Configurable

## Network Isolation

### Test Networks
Each test profile can create isolated networks:
```python
# Full isolation mode
docker_network = f"test-{profile}-{test_id}"
```

### Service Discovery
Services discover each other via:
1. Docker container names
2. Environment variables
3. Port mapping discovery

## Secret Management

### Test Secrets
Generated per test run:
```python
JWT_SECRET = f"test-jwt-{test_id}-minimum-32-chars"
SERVICE_SECRET = f"test-service-{test_id}-minimum-32"
```

### Never Use Production Secrets
- Test launcher generates safe test secrets
- Production secrets blocked by validation
- Staging uses separate secret namespace

## Cleanup Guarantees

### Automatic Cleanup
The test launcher ensures cleanup of:
- Docker containers (stop and remove)
- Database schemas (drop if created)
- Temporary files
- Network namespaces
- Port allocations

### Cleanup Triggers
- Normal test completion
- Test failure
- Timeout
- Signal interruption (SIGINT, SIGTERM)
- Process termination

## Common Pitfalls and Solutions

### Issue: Port conflicts with dev_launcher
**Solution**: Test launcher uses different ports by design

### Issue: Tests fail with "service not available"
**Solution**: Check Docker is running, use appropriate test profile

### Issue: LLM tests failing
**Solution**: Ensure API keys are set, real LLM enabled for non-unit tests

### Issue: Cleanup not happening
**Solution**: Check cleanup_on_exit flag, ensure proper signal handling

### Issue: Slow test startup
**Solution**: Use container reuse, implement health check caching

## Best Practices

1. **Always use test profiles** instead of manual configuration
2. **Let the launcher manage services** - don't start them manually
3. **Use isolation levels appropriately** - full isolation is slower
4. **Configure CI/CD with dynamic ports** to enable parallelization
5. **Monitor resource usage** in performance tests
6. **Test cleanup locally** before pushing to CI/CD

## Migration from Dev Launcher

When migrating tests from dev_launcher:

1. **Update ports**: Change from dev ports to test ports
2. **Update database names**: Use test schemas
3. **Remove hot-reload flags**: Not needed for tests
4. **Add cleanup configuration**: Ensure resources are freed
5. **Update environment variables**: Use TEST_ prefix

## Debugging

Enable verbose mode for troubleshooting:
```python
config = TestConfig.for_profile(TestProfile.E2E)
config.verbose = True
launcher = TestLauncher(config)
```

Check service logs:
```python
logs = launcher.service_manager.get_service_logs("postgres")
```

View service status:
```python
status = await launcher.get_service_status()
print(status)  # Shows running/ready state for each service
```

## Future Enhancements

Planned improvements:
- Kubernetes pod support for CI/CD
- Service mesh integration for staging
- Distributed tracing for E2E tests
- Smart container reuse strategies
- Test data snapshot/restore