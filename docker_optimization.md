# Docker Resource Optimization for PyTest

## Overview
This document outlines critical fixes applied to resolve Docker resource limits causing container crashes during pytest execution. The primary issue was containers restarting 3-5 times per test run due to insufficient memory allocation during test collection and execution phases.

## Problem Analysis
- **Root Cause**: Insufficient memory allocation for pytest collection phase
- **Symptoms**: Container restarts, OOM kills, failed test runs
- **Impact**: 3-5 container restarts per test run, unreliable CI/CD
- **Critical Services**: backend, auth, postgres, redis, clickhouse

## Applied Fixes

### 1. Enhanced docker-compose.alpine-test.yml

#### Resource Limit Increases
| Service | Memory (Before) | Memory (After) | CPU (Before) | CPU (After) |
|---------|-----------------|----------------|--------------|-------------|
| alpine-test-backend | 2G | **4G** | 0.5 | **1.0** |
| alpine-test-auth | 1G | **2G** | 0.25 | **1.0** |
| alpine-test-postgres | 512M | **1G** | 0.25 | **0.5** |
| alpine-test-redis | 256M | **512M** | 0.1 | **0.25** |
| alpine-test-clickhouse | 512M | **1G** | 0.2 | **0.5** |

#### tmpfs Volume Increases
All tmpfs volumes increased from **512M to 1G** for:
- PostgreSQL data directory
- Redis data directory  
- ClickHouse data directory

#### Enhanced Health Checks
- **Start Period**: Extended from 5-15s to 30-60s for pytest collection time
- **Intervals**: Increased from 2-3s to 5-15s to reduce overhead
- **Retries**: Increased from 5-10 to 15-20 for better reliability
- **Timeouts**: Increased from 1-2s to 3-10s for loaded containers

### 2. New docker-compose.pytest.yml

Created specialized compose file for pytest with:

#### Pytest-Optimized Resources
| Service | Memory Limit | CPU Cores | tmpfs Size |
|---------|-------------|-----------|------------|
| pytest-backend | **6G** | **2.0** | - |
| pytest-auth | **3G** | **1.5** | - |
| pytest-postgres | **2G** | **1.0** | **2G** |
| pytest-redis | **1G** | **0.5** | **1G** |
| pytest-clickhouse | **2G** | **1.0** | **2G** |

#### Pytest-Specific Features
- **Extended Health Checks**: 120s start period for collection time
- **Memory Monitoring Labels**: Automated resource tracking
- **Environment Variables**: 
  - `PYTEST_MODE=true`
  - `PYTEST_COLLECTION_TIMEOUT=300`
  - `PYTEST_EXECUTION_TIMEOUT=1800`
  - `MALLOC_ARENA_MAX=4` (memory optimization)
- **Network Isolation**: Dedicated pytest-network bridge

### 3. Advanced Resource Monitor

#### Script: `scripts/pytest_resource_monitor.py`

**Key Features:**
- **Real-time Monitoring**: 15-second intervals during test runs
- **Memory Alerts**: Warning at 80%, Critical at 90%
- **Auto-adjustment**: Automatic memory limit increases up to 20%
- **Historical Tracking**: Maintains last 100 measurements per container
- **Report Generation**: JSON reports with detailed metrics

**Alert System:**
```python
ResourceThresholds:
  memory_warning: 80.0%   # First alert level
  memory_critical: 90.0%  # Emergency level
  cpu_warning: 80.0%      # CPU performance alert
  cpu_critical: 90.0%     # CPU emergency level
```

**Auto-adjustment Logic:**
- Monitors critical services (backend, auth)
- Increases memory by 20% when usage > 85%
- Respects maximum limits defined in container config
- Logs all adjustments for tracking

#### Monitored Containers
| Container | Auto-Adjust | Base Memory | Max Memory |
|-----------|-------------|-------------|------------|
| pytest-backend | ✅ | 6G | 8G |
| pytest-auth | ✅ | 3G | 4G |
| pytest-postgres | ❌ | 2G | 3G |
| pytest-redis | ✅ | 1G | 1.5G |
| pytest-clickhouse | ✅ | 2G | 3G |

### 4. Health Check Optimizations

#### Collection Phase Adaptations
- **Backend/Auth**: 120s start period for pytest collection
- **Databases**: 30-60s start period for initialization  
- **Check Intervals**: Reduced frequency to minimize load
- **Failure Tolerance**: Increased retries for loaded systems

#### Memory-Aware Health Checks
- Health check commands include memory status
- Graceful degradation on memory pressure
- Timeout adjustments based on container load

### 5. Network and Storage Optimizations

#### Network Configuration
- **MTU**: Set to 1500 for optimal packet size
- **Bridge Name**: pytest-br0 for isolation
- **Driver Options**: Optimized for container communication

#### tmpfs Configuration
- **Size Increases**: All critical services 2x-4x larger tmpfs
- **Performance**: Ultra-fast ephemeral storage for tests
- **Memory Impact**: Balanced against container memory limits

## Usage Instructions

### Using Enhanced Alpine Test Environment
```bash
# Standard alpine test with optimized resources
docker-compose -f docker-compose.alpine-test.yml up

# With resource monitoring
python scripts/pytest_resource_monitor.py --compose-file docker-compose.alpine-test.yml &
docker-compose -f docker-compose.alpine-test.yml up
```

### Using Dedicated PyTest Environment  
```bash
# PyTest-optimized environment
docker-compose -f docker-compose.pytest.yml up

# With monitoring and custom thresholds
python scripts/pytest_resource_monitor.py \
  --compose-file docker-compose.pytest.yml \
  --memory-warning 75 \
  --memory-critical 85 \
  --interval 10 &

docker-compose -f docker-compose.pytest.yml up
```

### Running Resource Monitor Standalone
```bash
# Basic monitoring
python scripts/pytest_resource_monitor.py

# Advanced monitoring with custom settings
python scripts/pytest_resource_monitor.py \
  --compose-file docker-compose.pytest.yml \
  --interval 15 \
  --memory-warning 80 \
  --memory-critical 90
```

## Expected Results

### Performance Improvements
- **Container Restarts**: Reduced from 3-5 to 0-1 per test run
- **Collection Time**: Stable memory usage during pytest collection
- **Test Execution**: No OOM kills during test execution
- **CI/CD Reliability**: Consistent test environment startup

### Resource Usage
- **Memory Utilization**: Better managed with auto-scaling
- **CPU Load**: Distributed across more cores
- **Storage I/O**: Faster with larger tmpfs volumes
- **Network**: Isolated pytest network reduces interference

### Monitoring Benefits
- **Proactive Alerts**: Early warning before OOM conditions
- **Auto-recovery**: Automatic resource adjustment prevents crashes
- **Historical Data**: Performance trends for optimization
- **Detailed Reports**: JSON logs for troubleshooting

## Troubleshooting

### High Memory Usage
```bash
# Check current usage
docker stats

# Review monitor logs
tail -f pytest_resource_monitor.log

# Generate immediate report
python scripts/pytest_resource_monitor.py --interval 1 --compose-file docker-compose.pytest.yml
```

### Container Startup Issues
```bash
# Check enhanced health checks
docker-compose -f docker-compose.pytest.yml ps

# Review service logs
docker-compose -f docker-compose.pytest.yml logs pytest-backend

# Monitor startup sequence
docker-compose -f docker-compose.pytest.yml up --no-deps pytest-postgres
```

### Resource Monitoring Problems
```bash
# Verify Docker stats access
docker stats --no-stream

# Check monitor script permissions
ls -la scripts/pytest_resource_monitor.py

# Test monitoring manually
python scripts/pytest_resource_monitor.py --interval 5 --compose-file docker-compose.pytest.yml
```

## Migration Notes

### From Original Alpine Test
1. **Immediate**: Use updated `docker-compose.alpine-test.yml`
2. **Gradual**: Migrate to `docker-compose.pytest.yml` for better isolation
3. **Monitoring**: Deploy resource monitor in CI/CD environments

### Resource Scaling
- **Development**: Use alpine-test.yml with monitoring
- **CI/CD**: Use pytest.yml for reliable automated testing  
- **Load Testing**: Monitor and adjust limits based on actual usage

### Rollback Plan
- Original configurations preserved in git history
- Monitor script can be disabled without affecting core functionality
- Resource limits can be reduced if over-provisioned

## Configuration Files Modified

### Primary Changes
- `C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\docker-compose.alpine-test.yml` - Enhanced resource limits
- `C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\docker-compose.pytest.yml` - New pytest-optimized environment  
- `C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\scripts\pytest_resource_monitor.py` - Resource monitoring and auto-adjustment

### Environment Variables
New environment variables added:
- `PYTEST_MODE=true` - Enables pytest-specific optimizations
- `PYTEST_COLLECTION_TIMEOUT=300` - Collection phase timeout
- `PYTEST_EXECUTION_TIMEOUT=1800` - Test execution timeout
- `MALLOC_ARENA_MAX=4` - Memory allocation optimization
- `PYTHONHASHSEED=0` - Deterministic hash seeding

## Success Metrics

### Target Improvements
- **Container Restarts**: < 1 per test run (from 3-5)
- **Memory Usage**: < 85% sustained during pytest collection
- **Startup Time**: < 120s for full environment (previously timed out)
- **Test Reliability**: > 95% successful test runs (from ~60%)

### Monitoring Metrics
- **Response Time**: Health checks < 10s response time
- **Resource Efficiency**: Memory utilization 60-80% range
- **Alert Frequency**: < 2 warnings per test run
- **Auto-adjustment**: < 1 memory increase per test run

This optimization ensures reliable pytest execution in Docker environments with automatic resource management and comprehensive monitoring.