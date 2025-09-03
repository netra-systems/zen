# Port Allocation Strategy

## Overview

This document defines the port allocation strategy for the Netra Docker infrastructure to ensure no conflicts between different environments when running in parallel.

## Port Allocation Matrix

### Base Port Ranges

Each environment uses a specific port range to avoid conflicts:

| Environment     | Port Range  | Purpose                    |
|-----------------|-------------|----------------------------|
| Development     | 5433-9000   | Default local development  |
| Test            | 5434-9002   | Standard testing           |
| Alpine Test     | 5435-9003   | Alpine-optimized testing   |
| CI              | 5436-9004   | CI/CD pipelines            |
| Dynamic         | 9500-9999   | Dynamic allocation pool    |

### Service Port Assignments

#### Development Environment (Default)
```yaml
PostgreSQL:       5433
Redis:            6380
ClickHouse HTTP:  8124
ClickHouse TCP:   9001
Backend:          8000
Auth:             8081
Frontend:         3000
```

#### Test Environment
```yaml
PostgreSQL:       5434
Redis:            6381
ClickHouse HTTP:  8125
ClickHouse TCP:   9002
Backend:          8001
Auth:             8082
Frontend:         3001
```

#### Alpine Test Environment
```yaml
PostgreSQL:       5435
Redis:            6382
ClickHouse HTTP:  8126
ClickHouse TCP:   9003
Backend:          8002
Auth:             8083
Frontend:         3002
```

#### CI Environment
```yaml
PostgreSQL:       5436
Redis:            6383
ClickHouse HTTP:  8127
ClickHouse TCP:   9004
Backend:          8003
Auth:             8084
Frontend:         3003
```

## Dynamic Port Allocation

### Algorithm

The dynamic port allocation system follows these rules:

1. **Check for Available Ports**: Scan the dynamic range (9500-9999) for available ports
2. **Service Groups**: Allocate ports in groups to maintain service relationships
3. **Persistence**: Save allocated ports to `.env.dynamic` for consistency
4. **Collision Detection**: Verify no other process is using the port before allocation

### Port Group Structure

Each environment requires a group of 7 ports:
- 1 for PostgreSQL
- 1 for Redis
- 2 for ClickHouse (HTTP + TCP)
- 1 for Backend
- 1 for Auth
- 1 for Frontend

### Allocation Strategy

```python
def allocate_port_group(base_port: int) -> dict:
    return {
        "postgres": base_port,
        "redis": base_port + 100,
        "clickhouse_http": base_port + 200,
        "clickhouse_tcp": base_port + 300,
        "backend": base_port + 400,
        "auth": base_port + 401,
        "frontend": base_port + 500
    }
```

## Parallel Execution Support

### Test Parallelization

For parallel test execution, the system:

1. Uses process ID or timestamp as a seed
2. Calculates unique port offset: `offset = (pid % 20) * 10`
3. Applies offset to base ports for the environment
4. Validates availability before use

### CI/CD Parallelization

CI systems can use build ID for port calculation:
```bash
PORT_OFFSET=$((CI_BUILD_NUMBER % 50))
BASE_PORT=$((9500 + PORT_OFFSET * 10))
```

## Conflict Resolution

### Detection Methods

1. **Socket Binding Test**: Try to bind to the port
2. **Process Scanning**: Check if any process is listening
3. **Docker Network Inspection**: Verify no containers are using the port

### Resolution Strategy

1. If a port is occupied, increment by 1 and retry
2. Maximum 10 retry attempts per port
3. If all retries fail, move to next port group
4. Log all conflicts for debugging

## Best Practices

### Development
- Always use `.env.local` for consistent development ports
- Run `docker-compose down` before switching environments
- Use `--remove-orphans` flag to clean up unused containers

### Testing
- Use dynamic allocation for parallel test runs
- Clean up containers after test completion
- Monitor port usage with `scripts/check_ports.py`

### CI/CD
- Use CI-specific ports from `.env.ci`
- Implement cleanup jobs to release ports
- Use ephemeral storage (tmpfs) where appropriate

### Production
- Never use dynamic allocation in production
- Define static ports in secure configuration
- Implement firewall rules for port access

## Monitoring and Debugging

### Port Usage Commands

Check port availability:
```bash
# Windows
netstat -an | findstr :PORT

# Linux/Mac
lsof -i :PORT
```

List Docker port mappings:
```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

### Troubleshooting

Common issues and solutions:

| Issue | Solution |
|-------|----------|
| Port already in use | Run cleanup script: `python scripts/docker_cleanup.py` |
| Container name conflict | Use unique project names: `docker-compose -p unique_name up` |
| Orphaned containers | Clean with: `docker-compose down --remove-orphans` |
| Network conflicts | Reset networks: `docker network prune` |

## Configuration Files

### Environment Files
- `.env.local` - Development environment
- `.env.test` - Test environment  
- `.env.ci` - CI environment
- `.env.dynamic` - Dynamic allocation (generated)

### Docker Compose
- `docker-compose.unified.yml` - Single source of truth
- Uses environment variables for all port assignments
- Profile-based environment selection

## Script Usage

### Manual Port Check
```bash
python scripts/check_ports.py --env test
```

### Dynamic Allocation
```bash
python scripts/allocate_test_ports.py --parallel-id 1
```

### Port Cleanup
```bash
python scripts/release_ports.py --env test
```

## Security Considerations

1. **Internal Networks**: Use Docker internal networks when possible
2. **Localhost Binding**: Bind to 127.0.0.1 in development
3. **Firewall Rules**: Implement strict rules in production
4. **Port Scanning**: Regularly audit exposed ports
5. **Access Control**: Use authentication for all services

## Future Improvements

1. **Service Discovery**: Implement Consul or similar for dynamic service discovery
2. **Port Registry**: Central registry for port allocations
3. **Automatic Cleanup**: Scheduled cleanup of unused allocations
4. **Health Monitoring**: Real-time port health dashboard
5. **Zero-Port Mode**: Support for Unix socket connections where applicable