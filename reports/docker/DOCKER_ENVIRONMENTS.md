# Docker Dual-Environment Setup

## Quick Start

We now have **TWO separate Docker environments** that can run simultaneously:

### 1. TEST Environment (Port 8001)
**Purpose**: Automated testing with real services (no mocks)

```bash
# Start TEST environment
python scripts/launch_test_env.py

# Run tests
python unified_test_runner.py --category integration --no-coverage --fast-fail

# Stop TEST environment
python scripts/launch_test_env.py --stop
```

### 2. DEV Environment (Port 8000)
**Purpose**: Local development with hot reload for manual testing

```bash
# Start DEV environment (with hot reload)
python scripts/launch_dev_env.py -d

# Open browser automatically when ready
python scripts/launch_dev_env.py -d --open

# View logs
python scripts/launch_dev_env.py --logs backend

# Stop DEV environment
python scripts/launch_dev_env.py --stop
```

## Master Environment Manager

Use the unified manager to control both environments:

```bash
# Check status of both environments
python scripts/docker_env_manager.py status

# Start both environments simultaneously
python scripts/docker_env_manager.py start both

# Stop all environments
python scripts/docker_env_manager.py stop all

# Clean everything (including volumes)
python scripts/docker_env_manager.py clean
```

## Port Mapping

| Service | DEV Port | TEST Port |
|---------|----------|-----------|
| PostgreSQL | 5432 | 5433 |
| Redis | 6379 | 6380 |
| ClickHouse | 8123 | 8124 |
| Backend API | 8000 | 8001 |
| Auth Service | 8081 | 8082 |
| Frontend | 3000 | 3001 |

## Key Benefits

1. **Run tests while developing**: TEST environment on port 8001, DEV on port 8000
2. **No conflicts**: Separate networks, volumes, and ports
3. **Hot reload in DEV**: Code changes reflect immediately
4. **Fast test execution**: TEST environment optimized for speed
5. **Real services**: Both environments use real databases, no mocks

## Environment Files

- `.env.dev`: Development environment configuration
- `.env.test`: Test environment configuration
- `docker-compose.dev.yml`: DEV environment services
- `docker-compose.test.yml`: TEST environment services
- `docker-compose.override.yml`: Hot reload configuration for DEV

## Common Workflows

### Test-Driven Development
```bash
# 1. Start TEST environment
python scripts/launch_test_env.py

# 2. Write failing test
# ... edit test files ...

# 3. Run test to see failure
python unified_test_runner.py --category unit --fast-fail

# 4. Start DEV environment for implementation
python scripts/launch_dev_env.py -d --open

# 5. Implement feature (hot reload shows changes)
# ... edit code ...

# 6. Run test again to verify
python unified_test_runner.py --category unit --fast-fail
```

### Parallel Development
```bash
# Terminal 1: Run tests continuously
python scripts/launch_test_env.py
watch python unified_test_runner.py --category integration

# Terminal 2: Develop with hot reload
python scripts/launch_dev_env.py
# Make changes, see immediate updates
```

## Troubleshooting

### Port conflicts?
```bash
# Check what's using ports
python scripts/docker_env_manager.py status

# Stop specific environment
python scripts/docker_env_manager.py stop test
python scripts/docker_env_manager.py stop dev
```

### Need fresh start?
```bash
# Clean everything and start fresh
python scripts/docker_env_manager.py clean
python scripts/docker_env_manager.py start both
```

### View logs?
```bash
# DEV environment logs
docker-compose -f docker-compose.dev.yml logs -f backend

# TEST environment logs
docker-compose -f docker-compose.test.yml logs -f backend-test
```

## Documentation

For detailed documentation, see:
- [`docs/docker-dual-environment-setup.md`](docs/docker-dual-environment-setup.md) - Complete guide
- [`docs/docker-hot-reload-guide.md`](docs/docker-hot-reload-guide.md) - Hot reload setup

## Quick Reference

```bash
# Status check
python scripts/docker_env_manager.py status

# Start both
python scripts/docker_env_manager.py start both

# Start DEV only
python scripts/launch_dev_env.py -d

# Start TEST only
python scripts/launch_test_env.py

# Run tests
python unified_test_runner.py

# Stop all
python scripts/docker_env_manager.py stop all
```