# Docker Dual-Environment Setup

## Overview

This system provides two distinct Docker Compose environments that can run simultaneously:

1. **TEST Environment**: For automated testing with real services
2. **DEV Environment**: For local development with hot reload

## Architecture

### Environment Separation

Each environment operates in complete isolation:
- Separate Docker networks (prevents cross-environment communication)
- Separate volumes (no data sharing between environments)  
- Different port mappings (allows simultaneous operation)
- Environment-specific configuration files

### Port Allocation

| Service | DEV Port | TEST Port | Description |
|---------|----------|-----------|-------------|
| PostgreSQL | 5432 | 5433 | Database |
| Redis | 6379 | 6380 | Cache & Message Queue |
| ClickHouse HTTP | 8123 | 8124 | Analytics Database |
| ClickHouse TCP | 9000 | 9001 | Analytics Native Protocol |
| Backend API | 8000 | 8001 | Main Application |
| Auth Service | 8081 | 8082 | Authentication |
| Frontend | 3000 | 3001 | Web UI |

## Quick Start

### Running the TEST Environment

```bash
# Run tests with real services
docker-compose -f docker-compose.test.yml --env-file .env.test up -d

# Run the test suite
python unified_test_runner.py --category integration --no-coverage --fast-fail

# Stop the TEST environment
docker-compose -f docker-compose.test.yml --env-file .env.test down
```

### Running the DEV Environment

```bash
# Start development environment with hot reload
docker-compose -f docker-compose.dev.yml --env-file .env.dev up

# Or run specific services
docker-compose -f docker-compose.dev.yml --env-file .env.dev up backend auth

# Stop the DEV environment
docker-compose -f docker-compose.dev.yml --env-file .env.dev down
```

### Running Both Environments Simultaneously

```bash
# Terminal 1: Start TEST environment for automated testing
docker-compose -f docker-compose.test.yml --env-file .env.test up -d

# Terminal 2: Start DEV environment for manual testing
docker-compose -f docker-compose.dev.yml --env-file .env.dev up

# Now you can:
# - Run automated tests against TEST environment (port 8001)
# - Manually test features in DEV environment (port 8000)
# - Make code changes and see hot reload in DEV
# - Run tests without affecting your development work
```

## Environment Configuration

### TEST Environment (.env.test)

- **Purpose**: Automated testing with real services
- **Characteristics**:
  - Minimal logging (ERROR level)
  - Fast startup and teardown
  - Mock API keys by default
  - Isolated test database
  - No hot reload (not needed for tests)

### DEV Environment (.env.dev)

- **Purpose**: Local development and manual testing
- **Characteristics**:
  - Verbose logging (DEBUG level)
  - Hot reload enabled for all services
  - Development OAUTH SIMULATION
  - Real API keys from .env.development
  - Browser-accessible frontend

## Service Details

### PostgreSQL
- **DEV**: `postgresql://netra:netra123@localhost:5432/netra_dev`
- **TEST**: `postgresql://test:test@localhost:5433/netra_test`

### Redis
- **DEV**: `redis://localhost:6379`
- **TEST**: `redis://localhost:6380`

### ClickHouse
- **DEV**: `http://localhost:8123` (user: netra, password: netra123)
- **TEST**: `http://localhost:8124` (user: test, password: test)

### Backend API
- **DEV**: `http://localhost:8000`
  - Hot reload enabled
  - Development OAUTH SIMULATION
  - Debug logging
- **TEST**: `http://localhost:8001`
  - Minimal logging
  - Strict auth validation
  - Test fixtures enabled

### Auth Service
- **DEV**: `http://localhost:8081`
  - OAuth development credentials
  - Session debugging enabled
- **TEST**: `http://localhost:8082`
  - Mock OAuth providers
  - Fast token validation

### Frontend
- **DEV**: `http://localhost:3000`
  - Next.js hot reload
  - Development error pages
  - Source maps enabled
- **TEST**: `http://localhost:3001`
  - E2E test mode
  - Minimal bundle
  - Test selectors enabled

## Common Use Cases

### 1. Test-Driven Development (TDD)

```bash
# Start TEST environment
docker-compose -f docker-compose.test.yml --env-file .env.test up -d

# Write a failing test
# ... edit test files ...

# Run tests to see failure
python unified_test_runner.py --category unit --fast-fail

# Implement the feature in DEV environment
docker-compose -f docker-compose.dev.yml --env-file .env.dev up

# Test manually at http://localhost:8000
# Hot reload shows changes immediately

# Run tests again to verify
python unified_test_runner.py --category unit --fast-fail
```

### 2. Debugging Production Issues

```bash
# Reproduce issue in TEST environment with production-like settings
docker-compose -f docker-compose.test.yml --env-file .env.test up

# Debug in DEV environment with verbose logging
docker-compose -f docker-compose.dev.yml --env-file .env.dev up

# Compare behavior between environments
```

### 3. Running Integration Tests

```bash
# Ensure TEST environment is running
docker-compose -f docker-compose.test.yml --env-file .env.test up -d

# Run integration tests
python unified_test_runner.py --category integration --real-llm

# Tests use TEST environment ports automatically
```

### 4. Parallel Development and Testing

```bash
# Developer 1: Working on frontend
docker-compose -f docker-compose.dev.yml --env-file .env.dev up frontend

# Developer 2: Running backend tests
docker-compose -f docker-compose.test.yml --env-file .env.test up -d
python unified_test_runner.py --category backend

# No conflicts - different ports and networks
```

## Troubleshooting

### Port Conflicts

If you get "port already in use" errors:

```bash
# Check what's using the port
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Stop conflicting containers
docker ps  # List running containers
docker stop <container_id>

# Or use different ports in .env files
```

### Network Issues

If services can't communicate:

```bash
# Verify networks exist
docker network ls

# Ensure services are on correct network
docker inspect <container_name> | grep NetworkMode

# Recreate networks if needed
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up
```

### Volume Conflicts

If data persists unexpectedly:

```bash
# List volumes
docker volume ls

# Remove specific volume
docker volume rm netra-dev-postgres-data  # DEV database
docker volume rm netra-postgres-test-data  # TEST database

# Clean all unused volumes
docker volume prune
```

### Hot Reload Not Working

For DEV environment:

```bash
# Check docker-compose.override.yml is being loaded
docker-compose -f docker-compose.dev.yml config | grep reload

# Verify watchdog settings
docker logs netra-backend | grep reload

# On Mac/Windows, ensure polling is enabled
# Check WATCHDOG_USE_POLLING=true in docker-compose.override.yml
```

## Best Practices

1. **Always specify environment files explicitly**
   ```bash
   docker-compose -f docker-compose.test.yml --env-file .env.test up
   ```

2. **Clean up after testing**
   ```bash
   docker-compose -f docker-compose.test.yml down -v  # -v removes volumes
   ```

3. **Use profiles for partial environments**
   ```bash
   # Just databases for testing
   docker-compose -f docker-compose.dev.yml --profile db up
   ```

4. **Monitor resource usage**
   ```bash
   docker stats  # Real-time resource usage
   ```

5. **Keep environments in sync**
   - Update both .env.test and .env.dev when adding new variables
   - Test in both environments before committing

## Environment Variables Reference

### Required in Both Environments

- Database credentials
- Redis configuration
- Service ports
- API endpoints

### TEST-Specific

- `TESTING=1` - Enables test mode
- `LOG_LEVEL=ERROR` - Minimal logging
- `TEST_*` prefixed ports

### DEV-Specific

- `ALLOW_DEV_OAUTH_SIMULATION=true` - Skip auth for development
- `WATCHDOG_*` - Hot reload configuration
- Debug and monitoring settings

## Migration Guide

### From Single Environment to Dual Environment

1. Stop existing containers:
   ```bash
   docker-compose down
   ```

2. Copy your existing .env to .env.dev:
   ```bash
   cp .env .env.dev
   ```

3. Update ports if needed in .env.dev

4. Start using environment-specific commands:
   ```bash
   docker-compose -f docker-compose.dev.yml --env-file .env.dev up
   ```

### Switching Between Environments

```bash
# Stop DEV, start TEST
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.test.yml --env-file .env.test up

# Stop TEST, start DEV
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.dev.yml --env-file .env.dev up
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Start TEST environment
  run: docker-compose -f docker-compose.test.yml --env-file .env.test up -d

- name: Run tests
  run: python unified_test_runner.py --category all --no-coverage

- name: Stop TEST environment
  if: always()
  run: docker-compose -f docker-compose.test.yml down -v
```

## Performance Optimization

### TEST Environment
- Use `--no-cache` for faster builds
- Minimize volume mounts
- Disable unnecessary services with profiles

### DEV Environment
- Use docker-compose.override.yml for platform-specific optimizations
- Enable BuildKit: `DOCKER_BUILDKIT=1`
- Use `.dockerignore` to exclude unnecessary files

## Security Considerations

1. **Never commit real API keys to .env.test**
2. **Use different secrets between environments**
3. **Restrict TEST environment to localhost only**
4. **Regularly rotate development credentials**

## Appendix

### Complete Environment Comparison

| Aspect | TEST | DEV |
|--------|------|-----|
| Purpose | Automated Testing | Development |
| Network | netra-test-network | netra-network |
| Database | netra_test | netra_dev |
| Hot Reload | No | Yes |
| Logging | ERROR | DEBUG |
| OAUTH SIMULATION | No | Yes |
| API Keys | Mock | Real |
| Startup Time | Fast | Normal |
| Resource Usage | Minimal | Normal |

### Docker Commands Reference

```bash
# View logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Execute commands in container
docker-compose -f docker-compose.dev.yml exec backend bash

# Rebuild specific service
docker-compose -f docker-compose.dev.yml build backend

# Scale services
docker-compose -f docker-compose.dev.yml up --scale backend=2

# View configuration
docker-compose -f docker-compose.dev.yml config
```