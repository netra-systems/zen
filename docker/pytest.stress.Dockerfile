# Pytest Stress Testing Dockerfile
# Includes memory profiling and resource monitoring tools
# For load testing and performance analysis

FROM python:3.11-slim as base

# Performance monitoring environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Memory profiling settings
ENV PYTHONTRACEMALLOC=1
ENV PYTHONMALLOC=debug
ENV MALLOC_CHECK_=2

WORKDIR /app

# --- System Dependencies for Monitoring ---
FROM base as system

# Install monitoring and profiling tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libffi-dev \
    htop \
    iotop \
    sysstat \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# --- Dependencies Stage ---
FROM system as deps

COPY requirements.txt /app/
COPY test_framework/requirements.txt /app/test_framework/

# Create comprehensive stress testing requirements
RUN cat > /app/stress_requirements.txt << 'EOF'
# Core testing framework with stress testing plugins
pytest>=8.4.1
pytest-asyncio>=1.1.0
pytest-cov>=6.0.0
pytest-xdist>=3.6.0
pytest-benchmark>=4.0.0
pytest-timeout>=2.3.1
pytest-html>=4.1.1

# Application dependencies (full set for stress testing)
fastapi>=0.116.1
starlette>=0.47.3
uvicorn[standard]>=0.35.0
pydantic>=2.11.7
sqlalchemy>=2.0.43
sqlmodel>=0.0.24
asyncpg>=0.30.0
redis>=6.4.0
clickhouse-connect>=0.8.18

# Authentication & Security
PyJWT[cryptography]>=2.10.1
bcrypt>=4.3.0
cryptography>=45.0.6

# HTTP & WebSocket clients
httpx>=0.28.1
aiohttp>=3.12.15
websockets>=15.0.1

# Configuration
python-dotenv>=1.1.1

# Performance monitoring and profiling
memory-profiler>=0.61.0
py-spy>=0.3.14
pympler>=0.9
objgraph>=3.6.1
tracemalloc>=0.0.3

# System monitoring
psutil>=7.0.0
prometheus-client>=0.22.1

# Load testing
locust>=2.31.8
asyncio-throttle>=1.0.2

# Utilities
tenacity>=9.1.2
beartype>=0.21.0
python-dateutil>=2.9.0.post0
rich>=14.1.0
EOF

# Install with monitoring tools
RUN pip install --no-cache-dir -r /app/stress_requirements.txt

# --- Final Stage ---
FROM system as final

# Copy dependencies
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY netra_backend/ /app/netra_backend/
COPY shared/ /app/shared/
COPY test_framework/ /app/test_framework/
COPY tests/ /app/tests/
COPY scripts/ /app/scripts/

# Create stress testing configuration
RUN cat > /app/pytest-stress.ini << 'EOF'
[tool:pytest]
minversion = 8.0
testpaths = tests
python_files = test_*.py stress_test_*.py
python_classes = Test* Stress*
python_functions = test_* stress_test_*
addopts = 
    --tb=long
    --strict-markers
    --benchmark-only
    --benchmark-sort=mean
    --benchmark-columns=min,max,mean,stddev,median,iqr,outliers,ops,rounds
    --html=test-results/stress-report.html
    --self-contained-html
    --maxfail=10
    --timeout=300
markers =
    stress: marks tests as stress tests
    load: marks tests as load tests
    memory: marks tests as memory tests
    performance: marks tests as performance tests
asyncio_mode = auto
timeout = 300
EOF

# Create monitoring scripts
RUN cat > /app/monitor.sh << 'EOF'
#!/bin/bash
# System monitoring during stress tests

echo "Starting system monitoring..."
mkdir -p /app/monitoring

# Start background monitoring
(
    while true; do
        date=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$date] $(free -m | grep '^Mem:' | awk '{print "Memory: "$3"MB used / "$2"MB total"}')" >> /app/monitoring/memory.log
        echo "[$date] $(ps aux --sort=-%cpu | head -5)" >> /app/monitoring/cpu.log
        sleep 5
    done
) &

# Run tests with memory profiling
mprof run pytest -c pytest-stress.ini "$@"
mprof plot --output /app/monitoring/memory-profile.png

echo "Monitoring complete. Results in /app/monitoring/"
EOF

RUN chmod +x /app/monitor.sh

# Create memory profile runner
RUN cat > /app/profile_memory.py << 'EOF'
#!/usr/bin/env python3
"""
Memory profiling utility for stress tests
"""
import psutil
import time
import json
import tracemalloc
from datetime import datetime

def monitor_memory(duration=300, interval=5):
    """Monitor memory usage during test execution"""
    
    tracemalloc.start()
    process = psutil.Process()
    
    stats = []
    start_time = time.time()
    
    print(f"Starting memory monitoring for {duration}s...")
    
    while time.time() - start_time < duration:
        # Get memory info
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        # Get tracemalloc stats
        current, peak = tracemalloc.get_traced_memory()
        
        # System memory
        system_memory = psutil.virtual_memory()
        
        stat = {
            'timestamp': datetime.now().isoformat(),
            'rss': memory_info.rss,
            'vms': memory_info.vms,
            'percent': memory_percent,
            'tracemalloc_current': current,
            'tracemalloc_peak': peak,
            'system_available': system_memory.available,
            'system_percent': system_memory.percent
        }
        
        stats.append(stat)
        print(f"Memory: {memory_percent:.1f}% | RSS: {memory_info.rss/1024/1024:.1f}MB")
        
        time.sleep(interval)
    
    # Save results
    with open('/app/monitoring/memory_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    tracemalloc.stop()
    print("Memory monitoring complete")

if __name__ == "__main__":
    monitor_memory()
EOF

RUN chmod +x /app/profile_memory.py

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Create monitoring and results directories
RUN mkdir -p /app/monitoring /app/test-results \
    && chmod 755 /app/monitoring /app/test-results

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash testuser \
    && chown -R testuser:testuser /app
USER testuser

# Health check with stress test readiness
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=2 \
    CMD python -c "import pytest, memory_profiler, psutil; print('Stress test environment ready')" || exit 1

# Default command for stress testing
CMD ["bash", "/app/monitor.sh", "-v", "--tb=long"]