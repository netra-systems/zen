# Docker Resource Limits and Health Checks Configuration

## Overview

This document defines the resource limits and health check configurations for all Docker environments to ensure optimal performance, stability, and fast failure detection.

## Resource Limits Strategy

### Memory Limits by Environment

| Service     | Development | Test    | Alpine Test | CI      | Production |
|-------------|-------------|---------|-------------|---------|------------|
| PostgreSQL  | 512MB       | 256MB   | 1GB         | 512MB   | 2GB        |
| Redis       | 256MB       | 512MB   | 512MB       | 256MB   | 1GB        |
| ClickHouse  | 1GB         | 512MB   | 1GB         | 512MB   | 2GB        |
| Backend     | 2GB         | 2GB     | 2GB         | 2GB     | 4GB        |
| Auth        | 1GB         | 1GB     | 2GB         | 1GB     | 2GB        |
| Frontend    | 1GB         | 1GB     | 512MB       | 1GB     | 1GB        |

### CPU Limits by Environment

| Service     | Development | Test  | Alpine Test | CI    | Production |
|-------------|-------------|-------|-------------|-------|------------|
| PostgreSQL  | 0.25        | 0.3   | 0.5         | 0.5   | 0.5        |
| Redis       | 0.1         | 0.1   | 0.25        | 0.25  | 0.2        |
| ClickHouse  | 0.2         | 0.2   | 0.5         | 0.5   | 0.5        |
| Backend     | 0.4         | 0.4   | 1.0         | 1.0   | 1.0        |
| Auth        | 0.25        | 0.25  | 1.0         | 0.5   | 0.5        |
| Frontend    | 0.3         | 0.3   | 0.3         | 0.5   | 0.5        |

### Resource Reservations

Each service has minimum resource reservations (50% of limits):

```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '0.4'
    reservations:
      memory: 1G  # 50% of limit
```

## Health Check Configuration

### Standard Health Check Parameters

```yaml
healthcheck:
  test: ["CMD", "command"]
  interval: 10s    # How often to check
  timeout: 5s      # Maximum time for check
  retries: 10      # Failures before unhealthy
  start_period: 30s # Grace period on startup
```

### Service-Specific Health Checks

#### PostgreSQL
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
  interval: 10s
  timeout: 5s
  retries: 10
  start_period: 30s
```

#### Redis
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 20s
```

#### ClickHouse
```yaml
healthcheck:
  test: ["CMD", "clickhouse-client", "--query", "SELECT 1"]
  interval: 15s
  timeout: 10s
  retries: 30
  start_period: 60s
```

#### Backend Service
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 5s
  retries: 10
  start_period: 40s
```

#### Auth Service
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
  interval: 10s
  timeout: 5s
  retries: 10
  start_period: 40s
```

#### Frontend Service
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
  interval: 10s
  timeout: 5s
  retries: 10
  start_period: 60s
```

### Environment-Specific Health Check Tuning

#### Development
- Longer intervals (30s) to reduce overhead
- Longer timeouts (10s) for slower systems
- More retries (5-10) for stability

#### Test
- Moderate intervals (10s) for balance
- Standard timeouts (5s)
- Standard retries (10)

#### Alpine Test
- Fast intervals (5s) for quick detection
- Short timeouts (3s) for fast fails
- More retries (15) for stability

#### CI
- Very fast intervals (5s) for speed
- Very short timeouts (3s)
- Many retries (15) for transient issues

#### Production
- Moderate intervals (30s) for efficiency
- Standard timeouts (10s)
- Fewer retries (5) for quick failover

## Performance Optimization Settings

### PostgreSQL Tuning

#### Test Environments
```yaml
command: |
  postgres
    -c fsync=off                        # Disable fsync for speed
    -c synchronous_commit=off           # Async commits
    -c full_page_writes=off             # Disable full page writes
    -c shared_buffers=128MB             # Smaller buffer
    -c checkpoint_completion_target=0.9 # Spread checkpoints
    -c wal_buffers=16MB                 # WAL buffer size
    -c max_connections=100              # Connection limit
```

#### Production
```yaml
command: |
  postgres
    -c fsync=on                         # Enable fsync for safety
    -c synchronous_commit=on            # Sync commits
    -c full_page_writes=on              # Enable full page writes
    -c shared_buffers=512MB             # Larger buffer
    -c effective_cache_size=2GB         # Cache size hint
    -c maintenance_work_mem=256MB       # Maintenance memory
    -c max_connections=200              # Higher connection limit
```

### Redis Tuning

#### Test Environments
```yaml
command: |
  redis-server
    --appendonly no                     # No persistence
    --save ""                           # No snapshots
    --maxmemory 200mb                   # Memory limit
    --maxmemory-policy allkeys-lru      # Eviction policy
    --tcp-keepalive 60                  # Keep connections alive
```

#### Production
```yaml
command: |
  redis-server
    --appendonly yes                    # Enable AOF
    --save "60 1000"                    # Snapshot policy
    --maxmemory 1gb                     # Higher memory
    --maxmemory-policy volatile-lru     # Conservative eviction
    --tcp-keepalive 300                 # Longer keepalive
```

### Application Tuning

#### Backend Workers
```yaml
environment:
  # Test
  WORKERS: 2
  WEB_CONCURRENCY: 2
  
  # Production
  WORKERS: 4
  WEB_CONCURRENCY: 4
  MAX_WORKERS: 8
```

#### Memory Monitoring
```yaml
environment:
  # Test (disabled for speed)
  ENABLE_MEMORY_MONITORING: false
  
  # Production (enabled for safety)
  ENABLE_MEMORY_MONITORING: true
  MEMORY_CHECK_INTERVAL: 30
  MEMORY_WARNING_THRESHOLD: 80
  MEMORY_CRITICAL_THRESHOLD: 90
  MEMORY_CLEANUP_ENABLED: true
```

## Monitoring and Alerting

### Container Stats Monitoring
```bash
# Real-time stats
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# JSON output for automation
docker stats --no-stream --format json
```

### Health Status Checking
```bash
# Check all health statuses
docker ps --format "table {{.Names}}\t{{.Status}}"

# Get specific container health
docker inspect <container> --format '{{.State.Health.Status}}'
```

### Automated Health Monitoring Script
```python
#!/usr/bin/env python3
import subprocess
import json
import time

def check_health():
    result = subprocess.run(
        ['docker', 'ps', '--format', '{{json .}}'],
        capture_output=True,
        text=True
    )
    
    for line in result.stdout.splitlines():
        container = json.loads(line)
        name = container.get('Names', '')
        status = container.get('Status', '')
        
        if 'unhealthy' in status.lower():
            print(f"ALERT: {name} is unhealthy")
        elif 'healthy' not in status.lower():
            print(f"WARNING: {name} health unknown")

while True:
    check_health()
    time.sleep(30)
```

## Best Practices

### Resource Limits
1. Always set both limits and reservations
2. Use 50% reservation for guaranteed resources
3. Monitor actual usage and adjust limits
4. Leave headroom for spikes (20-30%)

### Health Checks
1. Use appropriate check method for each service
2. Balance frequency vs overhead
3. Set start_period for slow-starting services
4. Use retries to handle transient failures

### Performance
1. Disable unnecessary features in test environments
2. Use Alpine images for smaller footprint
3. Implement connection pooling
4. Monitor and tune based on metrics

### Troubleshooting

| Issue | Solution |
|-------|----------|
| OOMKilled | Increase memory limits |
| Slow startup | Increase start_period |
| Flapping health | Increase retries or interval |
| CPU throttling | Increase CPU limits |
| Network timeouts | Increase health check timeout |

## Validation Commands

### Verify Resource Limits
```bash
# Check memory limit
docker inspect <container> --format '{{.HostConfig.Memory}}'

# Check CPU limit
docker inspect <container> --format '{{.HostConfig.CpuQuota}}'
```

### Verify Health Configuration
```bash
# Check health check configuration
docker inspect <container> --format '{{json .Config.Healthcheck}}'

# Watch health status
watch -n 5 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

## Performance Benchmarks

### Expected Startup Times
- PostgreSQL: < 10 seconds
- Redis: < 5 seconds
- ClickHouse: < 30 seconds
- Backend: < 20 seconds
- Auth: < 20 seconds
- Frontend: < 30 seconds

### Expected Memory Usage
- PostgreSQL: 100-400MB
- Redis: 50-200MB
- ClickHouse: 200-800MB
- Backend: 200-1500MB
- Auth: 150-800MB
- Frontend: 100-500MB

### Expected Response Times
- Health endpoint: < 100ms
- Database query: < 10ms
- Redis operation: < 1ms
- API request: < 200ms