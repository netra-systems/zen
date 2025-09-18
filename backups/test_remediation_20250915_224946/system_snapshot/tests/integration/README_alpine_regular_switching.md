# Alpine vs Regular Container Switching Integration Tests

## Overview

The `test_alpine_regular_switching.py` file contains comprehensive integration tests for Alpine vs regular container switching functionality in the Netra Apex platform.

## Business Value

- **Segment**: Platform/Internal - Development Velocity, Risk Reduction, CI/CD Optimization
- **Business Goal**: Enable memory-optimized test execution with seamless switching capabilities
- **Value Impact**: Reduces CI costs by 40-60%, faster test execution, robust container orchestration
- **Strategic Impact**: Enables production-ready container switching for different deployment scenarios

## Test Coverage

### 1. Sequential Switching Tests (`TestSequentialSwitching`)
- **Regular → Alpine → Regular switching cycle**
- **Data persistence across container type switches**
- Validates that switching between container types works seamlessly
- Ensures data survives container type transitions

### 2. Parallel Execution Tests (`TestParallelExecution`)
- **Simultaneous Alpine and regular container execution**
- **Port isolation and conflict prevention**
- **Resource contention handling**
- **Independent operations verification**

### 3. Performance Comparison Tests (`TestPerformanceComparison`)
- **Startup time comparison** between Alpine and regular containers
- **Memory usage comparison** with detailed metrics
- **CPU usage comparison** under load
- Multiple iterations for reliable benchmarking

### 4. Error Recovery Tests (`TestErrorRecovery`)
- **Fallback from Alpine to regular** when Alpine fails
- **Cleanup after failed deployments**
- **Partial deployment recovery**
- Graceful degradation scenarios

### 5. Migration Path Tests (`TestMigrationPaths`)
- **Gradual migration** (some services Alpine, some regular)
- **Rollback scenarios** from Alpine to regular
- **Data integrity during migrations**

### 6. CI/CD Integration Tests (`TestCICDIntegration`)
- **Environment variable configuration**
- **CI-specific optimizations**
- **Different test runner configurations**
- Integration with unified test runner

## Usage

### Running All Tests
```bash
python tests/unified_test_runner.py --category integration --pattern "*alpine_regular_switching*"
```

### Running Specific Test Classes
```bash
# Sequential switching tests
python -m pytest tests/integration/test_alpine_regular_switching.py::TestSequentialSwitching -v

# Performance comparison tests  
python -m pytest tests/integration/test_alpine_regular_switching.py::TestPerformanceComparison -v

# Error recovery tests
python -m pytest tests/integration/test_alpine_regular_switching.py::TestErrorRecovery -v
```

### Running with Real Docker Services
```bash
python tests/unified_test_runner.py --category integration --pattern "*alpine_regular_switching*" --real-services
```

## Test Markers

- `@pytest.mark.integration` - All tests are integration tests
- `@pytest.mark.performance` - Performance benchmark tests
- `@pytest.mark.slow` - Tests that take longer to execute

## Prerequisites

1. **Docker Desktop** must be running
2. **Docker Compose** must be available
3. **Alpine compose files** must exist:
   - `docker-compose.alpine.yml`
   - `docker-compose.alpine-test.yml`

## Key Features

### Real Services Only
- Uses **real Docker containers** (no mocks)
- Tests actual container switching scenarios
- Validates production-ready functionality

### Comprehensive Metrics Collection
- Container startup times
- Memory usage measurements
- CPU utilization tracking
- Image size comparisons

### Robust Error Handling
- Graceful fallback mechanisms
- Comprehensive cleanup procedures
- Resource contention management

### CI/CD Ready
- Environment variable configuration
- Multiple test runner integration modes
- Performance benchmarking for CI optimization

## Expected Results

### Performance Expectations
- **Alpine containers**: 20-60% memory savings over regular containers
- **Startup times**: Alpine should not be >50% slower than regular
- **CPU usage**: Should be comparable within 2x ratio

### Functionality Expectations
- **100% data persistence** across container type switches
- **Zero port conflicts** in parallel execution
- **Graceful fallback** when Alpine containers fail
- **Successful cleanup** after all test scenarios

## Troubleshooting

### Docker Not Available
Tests will be skipped automatically with appropriate messages.

### Port Conflicts
Each test uses isolated test IDs to prevent conflicts.

### Memory Issues
Tests use minimal service sets to reduce resource usage.

### Cleanup Issues
Comprehensive cleanup procedures handle orphaned containers and volumes.

## Integration with Existing System

This test suite integrates with:
- **UnifiedDockerManager** for container orchestration
- **Unified Test Runner** for execution
- **Docker Port Discovery** for conflict resolution
- **Isolated Environment** for configuration management

The tests validate the complete container switching pipeline used by the development and CI/CD systems.