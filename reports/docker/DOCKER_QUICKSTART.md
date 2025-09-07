# Docker Quick Start Guide for Netra

## TL;DR - Just Make It Work

```bash
# Start Docker services (automatic for most commands)
python scripts/docker.py start

# Run tests (Docker starts automatically if needed)
python tests/unified_test_runner.py

# Check if everything is working
python scripts/docker.py health
```

## Common Docker Commands

### Basic Operations
```bash
# Start services
python scripts/docker.py start        # Test environment (default)
python scripts/docker.py start dev    # Development environment
python scripts/docker.py start prod   # Production environment

# Stop services
python scripts/docker.py stop

# Restart services
python scripts/docker.py restart

# Check status
python scripts/docker.py status

# Health check
python scripts/docker.py health

# View logs
python scripts/docker.py logs backend
python scripts/docker.py logs auth -f  # Follow logs in real-time

# Clean up everything
python scripts/docker.py cleanup
```

## Automatic Docker Startup

The test runner now **automatically starts Docker** when needed:

```bash
# Just run tests - Docker starts automatically
python tests/unified_test_runner.py --category unit

# Run with real services - Docker starts automatically
python tests/unified_test_runner.py --real-services

# Run E2E tests - Docker starts automatically
python tests/unified_test_runner.py --category e2e
```

## Troubleshooting

### Docker Not Starting?

1. **Check Docker Desktop is installed and running**
   ```bash
   docker --version
   docker ps
   ```

2. **Manually start services**
   ```bash
   python scripts/docker.py start
   ```

3. **Check service health**
   ```bash
   python scripts/docker.py health
   ```

4. **View logs for errors**
   ```bash
   python scripts/docker.py logs backend
   python scripts/docker.py logs postgres
   ```

### Port Conflicts?

If you see port conflict errors:

1. **Check what's using the ports**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   netstat -ano | findstr :5432
   
   # Mac/Linux
   lsof -i :8000
   lsof -i :5432
   ```

2. **Stop conflicting services or use different environment**
   ```bash
   python scripts/docker.py stop
   python scripts/docker.py start test  # Uses different ports
   ```

### Services Unhealthy?

1. **Restart unhealthy services**
   ```bash
   python scripts/docker.py restart
   ```

2. **Check logs for specific service**
   ```bash
   python scripts/docker.py logs backend
   python scripts/docker.py logs auth
   ```

3. **Clean up and start fresh**
   ```bash
   python scripts/docker.py cleanup
   python scripts/docker.py start
   ```

## Environment-Specific Configurations

### Test Environment (Default)
- **Ports**: PostgreSQL (5434), Redis (6381), Backend (8000), Auth (8081)
- **Use Case**: Running tests, isolated from development
- **Start**: `python scripts/docker.py start` or `python scripts/docker.py start test`

### Development Environment
- **Ports**: PostgreSQL (5432), Redis (6379), Backend (8000), Auth (8081)
- **Use Case**: Local development, debugging
- **Start**: `python scripts/docker.py start dev`

### Production Environment
- **Ports**: Standard production ports
- **Use Case**: Testing production configurations
- **Start**: `python scripts/docker.py start prod`

## Advanced Options

### Disable Automatic Docker Startup

If you want to manage Docker manually:

```bash
# Disable automatic Docker startup for tests
export TEST_NO_DOCKER=true
python tests/unified_test_runner.py
```

### Use Dedicated Docker Environment

For parallel test execution without conflicts:

```bash
python tests/unified_test_runner.py --docker-dedicated
```

### Manual Docker Compose

If you prefer using docker-compose directly:

```bash
# Test environment
docker-compose -f docker-compose.test.yml up -d

# Development environment
docker-compose up -d

# Production environment
docker-compose -f docker-compose.prod.yml up -d
```

## Getting Help

```bash
# Show help for Docker manager
python scripts/docker.py help

# Show help for test runner
python tests/unified_test_runner.py --help
```

## Key Benefits of the New System

1. **Automatic Startup**: Tests automatically start Docker when needed
2. **Clear Error Messages**: Helpful guidance when something goes wrong
3. **Simple Commands**: Easy-to-remember `python scripts/docker.py` commands
4. **Health Monitoring**: Built-in health checks for all services
5. **Environment Isolation**: Separate test/dev/prod environments

## Migration from Old Commands

| Old Command | New Command |
|------------|-------------|
| `docker-compose up -d` | `python scripts/docker.py start` |
| `docker-compose down` | `python scripts/docker.py stop` |
| `docker-compose ps` | `python scripts/docker.py status` |
| `docker-compose logs backend` | `python scripts/docker.py logs backend` |
| `python tests/unified_test_runner.py --real-services --env dev` | Just `python tests/unified_test_runner.py` (auto-starts) |

## Summary

The new Docker management system makes it simple:

1. **For testing**: Just run tests - Docker starts automatically
2. **For manual control**: Use `python scripts/docker.py [command]`
3. **For debugging**: Check health, view logs, restart services

No more remembering complex docker-compose commands or wondering why tests fail!