# OpenTelemetry Automatic Instrumentation Test Suite

**FOCUS:** Automatic instrumentation only - comprehensive testing for OpenTelemetry auto-instrumentation libraries without manual span creation or custom instrumentation.

This test suite validates OpenTelemetry automatic instrumentation across the Netra Apex AI Optimization Platform, ensuring reliable observability for our $500K+ ARR chat functionality.

## 🎯 Business Value

- **Enterprise/Platform Segment**: Observability foundation for AI operations
- **Business Goal**: Zero observability gaps in production systems
- **Value Impact**: Enables proactive monitoring and troubleshooting of chat functionality
- **Revenue Impact**: Prevents performance issues that could impact customer retention

## 📋 Test Categories

### Unit Tests (`tests/telemetry/unit/`)
- **File**: `test_opentelemetry_auto_instrumentation_config.py`
- **Focus**: Configuration and initialization validation
- **Duration**: ~5 minutes
- **Dependencies**: None
- **Critical**: ✅ Yes

**Tests Include:**
- Auto-instrumentation environment variable configuration
- Instrumentor library availability validation
- Framework detection (FastAPI, SQLAlchemy, Redis, requests)
- Resource attributes and sampling configuration
- Export configuration validation

### Integration Tests (`tests/telemetry/integration/`)
- **Files**: 
  - `test_opentelemetry_auto_framework_discovery.py`
  - `test_opentelemetry_trace_export_validation.py`
- **Focus**: Real framework integration and trace export
- **Duration**: ~15 minutes
- **Dependencies**: PostgreSQL, Redis
- **Critical**: ✅ Yes

**Tests Include:**
- FastAPI automatic instrumentation with real app
- SQLAlchemy instrumentation with real database queries
- Redis instrumentation with real cache operations
- HTTP requests instrumentation validation
- Multi-framework instrumentation coordination
- Trace export format and connectivity validation
- Cloud Trace and OTLP endpoint testing

### E2E Tests (`tests/telemetry/e2e/`)
- **File**: `test_opentelemetry_golden_path_auto_tracing.py`
- **Focus**: Complete user flow with automatic tracing
- **Duration**: ~20 minutes
- **Dependencies**: Backend, Auth Service, PostgreSQL, Redis
- **Critical**: ✅ Yes

**Tests Include:**
- Golden Path user flow automatic tracing
- WebSocket connection tracing
- Agent execution pipeline tracing
- End-to-end trace correlation
- Performance impact measurement

### Performance Tests (`tests/telemetry/performance/`)
- **File**: `test_opentelemetry_auto_instrumentation_overhead.py`
- **Focus**: Performance overhead measurement
- **Duration**: ~30 minutes
- **Dependencies**: PostgreSQL, Redis
- **Critical**: ❌ No (monitoring only)

**Tests Include:**
- Database operation overhead measurement
- Redis operation overhead measurement
- HTTP request overhead measurement
- System-wide overhead with multiple instrumentors
- Performance target validation (<5% critical path, <15% overall)

## 🚀 Quick Start

### Prerequisites

1. **OpenTelemetry Dependencies**:
   ```bash
   pip install opentelemetry-api==1.24.0
   pip install opentelemetry-sdk==1.24.0
   pip install opentelemetry-instrumentation-fastapi==0.45b0
   pip install opentelemetry-instrumentation-requests==0.45b0
   pip install opentelemetry-instrumentation-sqlalchemy==0.45b0
   pip install opentelemetry-instrumentation-redis==0.45b0
   pip install opentelemetry-exporter-otlp==1.24.0
   ```

2. **Required Services** (for integration/E2E tests):
   - PostgreSQL (port 5432)
   - Redis (port 6379)
   - Backend service (port 8000) - for E2E tests
   - Auth service (port 8001) - for E2E tests

### Running Tests

#### All Tests
```bash
python tests/telemetry/test_telemetry_suite_runner.py --all
```

#### By Category
```bash
# Unit tests only (no service dependencies)
python tests/telemetry/test_telemetry_suite_runner.py --unit

# Integration tests (requires PostgreSQL, Redis)
python tests/telemetry/test_telemetry_suite_runner.py --integration

# E2E tests (requires all services)
python tests/telemetry/test_telemetry_suite_runner.py --e2e

# Performance tests (requires PostgreSQL, Redis)
python tests/telemetry/test_telemetry_suite_runner.py --performance
```

#### Using Unified Test Runner
```bash
# Run through main test infrastructure
python tests/unified_test_runner.py --category telemetry

# Run specific telemetry test files
python tests/unified_test_runner.py tests/telemetry/unit/test_opentelemetry_auto_instrumentation_config.py
```

#### Direct pytest execution
```bash
# Run individual test files
pytest tests/telemetry/unit/test_opentelemetry_auto_instrumentation_config.py -v
pytest tests/telemetry/integration/test_opentelemetry_auto_framework_discovery.py -v --real-services
pytest tests/telemetry/e2e/test_opentelemetry_golden_path_auto_tracing.py -v --real-services
pytest tests/telemetry/performance/test_opentelemetry_auto_instrumentation_overhead.py -v --real-services
```

## 🔧 Configuration

### Environment Variables

**Basic Configuration:**
```bash
# Enable tracing
export ENABLE_TRACING=true
export OTEL_SERVICE_NAME=netra-apex-backend
export OTEL_RESOURCE_ATTRIBUTES="service.name=netra-apex-backend,service.version=1.0.0"

# Development (console export)
export OTEL_TRACES_EXPORTER=console
export OTEL_TRACES_SAMPLER=always_on

# Production (Cloud Trace)
export OTEL_TRACES_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT="https://cloudtrace.googleapis.com/v2/projects/YOUR_PROJECT/traces"
export OTEL_EXPORTER_OTLP_HEADERS="x-goog-user-project=YOUR_PROJECT"
export OTEL_TRACES_SAMPLER=traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling
```

**Performance Optimization:**
```bash
# Batch processing settings
export OTEL_BSP_SCHEDULE_DELAY=5000  # 5 second batch delay
export OTEL_BSP_MAX_EXPORT_BATCH_SIZE=512
export OTEL_BSP_MAX_QUEUE_SIZE=2048

# Exclude health check endpoints
export OTEL_PYTHON_EXCLUDED_URLS="/health,/metrics,/ready"

# Disable expensive features in production
export OTEL_PYTHON_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST=""
export OTEL_PYTHON_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_CLIENT_REQUEST=""
```

### Test Environment Setup

**Docker Services:**
```bash
# Start required services for integration/E2E tests
docker-compose up postgres redis

# For E2E tests, also start:
docker-compose up backend auth-service
```

**Environment Variables for Testing:**
```bash
# Test configuration
export ENVIRONMENT=test
export DEMO_MODE=1  # For E2E tests without OAuth complexity

# Database connection
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=netra
export POSTGRES_PASSWORD=netra_secure_2024
export POSTGRES_DB=netra_test

# Redis connection
export REDIS_HOST=localhost
export REDIS_PORT=6379

# WebSocket for E2E tests
export WEBSOCKET_URL=ws://localhost:8000/ws
```

## 📊 Test Results and Metrics

### Success Criteria

**Unit Tests:**
- All configuration validation tests pass
- All instrumentor availability tests pass
- All framework detection tests pass

**Integration Tests:**
- Real framework instrumentation succeeds
- Real service integration works
- Trace export configuration validates
- Multi-framework coordination succeeds

**E2E Tests:**
- Complete Golden Path flow traces automatically
- WebSocket events are captured
- Agent execution is traced end-to-end
- Performance impact < 15%

**Performance Tests:**
- Database overhead < 20%
- Redis overhead < 25%
- HTTP overhead < 30%
- System-wide overhead < 25%

### Metrics Collected

Each test collects detailed metrics:
- Execution times
- Instrumentation success rates
- Framework detection results
- Export configuration validation
- Performance overhead measurements
- Error counts and types

## 🛠️ Test Architecture

### SSOT Compliance

All tests inherit from `SSotBaseTestCase` ensuring:
- Consistent environment variable handling
- Unified metrics collection
- Proper cleanup and resource management
- Integration with existing test infrastructure

### Real Services Preference

Following Netra Apex testing principles:
- **Integration/E2E tests use REAL SERVICES**
- No mocks for database, Redis, or HTTP connections
- Docker services managed through `UnifiedDockerManager`
- Actual instrumentor libraries, not test doubles

### Test Isolation

Each test ensures:
- Independent execution (no shared state)
- Proper instrumentation cleanup
- Environment variable isolation
- Resource cleanup

## 🔍 Troubleshooting

### Common Issues

**1. Missing OpenTelemetry Dependencies**
```bash
# Install all required packages
pip install -r requirements.txt
```

**2. Service Dependencies Not Available**
```bash
# Check service health
docker ps
python -c "from test_framework.unified_docker_manager import UnifiedDockerManager; print(UnifiedDockerManager().is_service_healthy('postgres'))"
```

**3. Tests Failing Due to Network/Connectivity**
```bash
# Run unit tests only (no external dependencies)
python tests/telemetry/test_telemetry_suite_runner.py --unit
```

**4. Performance Tests Taking Too Long**
```bash
# Reduce iterations for faster testing
export PERFORMANCE_TEST_ITERATIONS=10  # Default is 50
```

### Debug Mode

Enable verbose logging:
```bash
python tests/telemetry/test_telemetry_suite_runner.py --all --verbose
```

View detailed test output:
```bash
pytest tests/telemetry/unit/test_opentelemetry_auto_instrumentation_config.py -v -s
```

## 📚 Related Documentation

- [Golden Path User Flow](../../docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md) - End-to-end user journey
- [Test Infrastructure SSOT](../../test_framework/ssot/README.md) - Base test framework
- [Unified Test Runner](../unified_test_runner.py) - Main test orchestration
- [Docker Test Infrastructure](../../test_framework/unified_docker_manager.py) - Service management

## 🤝 Contributing

When adding new telemetry tests:

1. **Follow automatic instrumentation focus** - no manual spans
2. **Inherit from SSotBaseTestCase** - consistent patterns
3. **Use real services** for integration/E2E tests
4. **Include performance validation** - measure overhead
5. **Add to appropriate category** - unit/integration/e2e/performance
6. **Update test suite runner** - register new test files
7. **Document business value** - explain why the test matters

### Test Naming Convention

```python
def test_[component]_auto_instrumentation_[specific_aspect](self):
    """
    Test [specific aspect] of [component] automatic instrumentation.
    
    This test MUST FAIL before auto-instrumentation is configured.
    """
```

### Required Test Structure

1. **Setup** - Configure test environment
2. **Before State** - Validate not instrumented initially
3. **Apply Instrumentation** - Configure automatic instrumentation
4. **Validate** - Confirm instrumentation works
5. **Performance Check** - Measure overhead if applicable
6. **Cleanup** - Uninstrument to avoid affecting other tests

---

**Last Updated**: 2025-09-10  
**Contact**: Development Team  
**Business Impact**: Critical for $500K+ ARR chat functionality observability