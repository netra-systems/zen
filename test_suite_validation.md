# Docker Pytest Crashes - Comprehensive Test Suite Validation

## Overview

This document describes a comprehensive, difficult test suite designed to validate all fixes for Docker pytest crashes. The test suite is specifically designed to **actually trigger the bugs if fixes aren't applied** and catch regressions through thorough, edge-case testing.

## Test Suite Structure

The test suite is organized into two main categories:
- **Stress Tests** (`tests/stress/`): Tests that deliberately stress system resources
- **Validation Tests** (`tests/validation/`): Tests that validate proper system behavior

## Critical Design Principles

1. **Regression Detection**: Each test is designed to fail if the underlying fixes are removed or regressed
2. **Edge Case Coverage**: Tests specifically target edge cases and race conditions that caused original crashes  
3. **Resource Exhaustion**: Tests deliberately exhaust system resources to validate limits and recovery
4. **Time-Bounded**: All tests complete within 5 minutes total while being comprehensive
5. **Clear Failure Messages**: Tests provide specific, actionable failure messages when they detect issues

## Test Suite Components

### 1. Docker Memory Limits Tests (`tests/stress/test_docker_memory_limits.py`)

**Purpose**: Validates Docker memory limit enforcement and OOM protection mechanisms.

#### Test Scenarios:

##### `test_gradual_memory_consumption_with_oom_protection()`
- **What it tests**: Gradual memory allocation to trigger OOM protection
- **How it catches regressions**: If OOM protection is broken, test will hang or crash with MemoryError
- **Resources**: Allocates up to 1GB in 10MB chunks with actual data writing
- **Expected behavior**: OOM protection should kick in gracefully, no MemoryError exceptions
- **Failure indicators**:
  - MemoryError raised (protection failed)
  - Memory not recovered after cleanup (leak detection)
  - Allocation stops too early (protection too aggressive)

##### `test_memory_leak_detection_during_pytest_collection()`
- **What it tests**: Memory usage during heavy pytest collection simulation
- **How it catches regressions**: Creates 1000 mock test objects to simulate collection load
- **Resources**: 1000 test objects, each ~100KB with metadata
- **Expected behavior**: Memory growth < 150MB total, sub-linear scaling
- **Failure indicators**:
  - Memory growth exceeds 150MB (leak in collection)
  - Memory retained > 20MB after cleanup (persistent leak)
  - Super-linear memory growth pattern

##### `test_container_restart_under_memory_pressure()`
- **What it tests**: Container behavior during memory pressure
- **How it catches regressions**: Creates memory pressure while monitoring Docker containers
- **Resources**: 50x 20MB allocations while monitoring container health
- **Expected behavior**: Containers remain healthy or restart gracefully
- **Failure indicators**:
  - Container crashes and doesn't restart
  - Container becomes unresponsive
  - Memory pressure causes permanent container failure

##### `test_memory_fragmentation_resistance()`
- **What it tests**: System behavior under memory fragmentation conditions
- **How it catches regressions**: Rapidly allocates/deallocates varying chunk sizes
- **Resources**: Mixed allocation patterns from 1KB to 256KB
- **Expected behavior**: No MemoryError, reasonable memory usage patterns
- **Failure indicators**:
  - MemoryError from fragmentation
  - Excessive memory retention (>50MB)
  - System becomes unresponsive

##### `test_concurrent_memory_pressure_with_workers()`
- **What it tests**: Memory behavior under concurrent worker load (parameterized: 1,2,4,8 workers)
- **How it catches regressions**: Simulates pytest's multiple worker processes
- **Resources**: Multiple threads each allocating 5MB chunks
- **Expected behavior**: At least 50% workers succeed, memory scaling is reasonable
- **Failure indicators**:
  - Too many worker failures (>50%)
  - Memory doesn't scale properly with worker count
  - Excessive memory retention per worker (>10MB)

### 2. Pytest Collection Performance Tests (`tests/stress/test_pytest_collection_performance.py`)

**Purpose**: Validates pytest collection performance and scalability under load.

#### Test Scenarios:

##### `test_collection_performance_with_1000_simple_files()`
- **What it tests**: Collection performance with 1000 simple test files
- **How it catches regressions**: Creates actual test files and runs `pytest --collect-only`
- **Resources**: 1000 test files, 10 tests each, ~10,000 total tests
- **Expected behavior**: Collection < 60s, memory < 500MB, rate > 50 tests/sec
- **Failure indicators**:
  - Collection timeout (>60s indicates performance regression)
  - Excessive memory usage (>500MB indicates leak)
  - Low collection rate (<50/sec indicates inefficiency)

##### `test_collection_performance_with_complex_nested_structure()`
- **What it tests**: Collection with deep directory structure and complex imports
- **How it catches regressions**: 50 directories x 20 files with inheritance and fixtures
- **Resources**: 1000 complex test files with classes, inheritance, fixtures
- **Expected behavior**: Collection < 180s, memory < 800MB, no critical errors
- **Failure indicators**:
  - Collection timeout (>180s for complex structure)
  - Critical import/syntax errors
  - Memory explosion (>800MB)

##### `test_parallel_collection_stress_with_multiple_processes()`
- **What it tests**: Collection under parallel process stress
- **How it catches regressions**: Multiple processes running collection simultaneously
- **Resources**: 4 parallel processes, 200 test files total
- **Expected behavior**: >50% processes succeed, parallel time < 150s
- **Failure indicators**:
  - Most processes fail (indicates concurrency issues)
  - Parallel processing slower than sequential (contention problems)
  - Process crashes or hangs

##### `test_collection_memory_growth_with_large_scale()`
- **What it tests**: Memory growth patterns during incremental collection
- **How it catches regressions**: Tests collection at 100, 200, 500, 1000 file scales
- **Resources**: Incremental batches to track memory scaling
- **Expected behavior**: Sub-linear memory growth, <0.5MB per file
- **Failure indicators**:
  - Linear or super-linear memory growth
  - Excessive memory per file (>0.5MB)
  - Memory not released between batches

##### `test_collection_with_circular_import_simulation()`
- **What it tests**: Collection behavior with circular import scenarios  
- **How it catches regressions**: Creates 20 modules with cross-imports
- **Resources**: 20 modules with 2-3 cross-imports each
- **Expected behavior**: No timeout, collection doesn't hang
- **Failure indicators**:
  - Collection timeout (indicates circular import hanging)
  - Complete collection failure
  - Excessive time for complex imports (>120s)

##### `test_collection_interruption_and_recovery()`
- **What it tests**: Collection interruption and recovery behavior
- **How it catches regressions**: Interrupts collection after 5s, then runs full collection
- **Resources**: 300 test files, controlled interruption
- **Expected behavior**: Interruption works, recovery successful
- **Failure indicators**:
  - Cannot interrupt collection (hangs)
  - Recovery fails after interruption  
  - Inconsistent results between runs

### 3. Circular Import Tests (`tests/stress/test_circular_imports.py`)

**Purpose**: Validates circular import detection and handling mechanisms.

#### Test Scenarios:

##### `test_simple_circular_import_detection()`
- **What it tests**: Basic A->B->C->A circular import detection
- **How it catches regressions**: Creates actual circular import modules
- **Resources**: 3-module circular chain with actual Python imports
- **Expected behavior**: Cycle detection < 1s, correct cycle identification
- **Failure indicators**:
  - Cycle detection fails or takes too long (>1s)
  - Incorrect cycle identification
  - Detection algorithm crashes

##### `test_complex_circular_import_detection()`
- **What it tests**: Complex web of interconnected modules with multiple cycles
- **How it catches regressions**: 15 modules with complex cross-dependencies
- **Resources**: 15 modules with 2-4 imports each, creating multiple overlapping cycles
- **Expected behavior**: Multiple cycles detected, covers 30%+ of modules
- **Failure indicators**:
  - Fails to detect complex cycles
  - Detection takes too long (>5s)
  - Excessive memory usage (>100MB)

##### `test_import_performance_under_circular_dependencies()`
- **What it tests**: Import performance impact of circular dependencies
- **How it catches regressions**: Compares import times: circular vs clean modules
- **Resources**: 4 circular modules vs 4 clean modules
- **Expected behavior**: Circular imports <5x slower than clean imports
- **Failure indicators**:
  - Circular imports dramatically slower (>5x)
  - Memory leaks in circular import handling
  - Import failures due to poor handling

##### `test_threading_deadlock_with_circular_imports()`
- **What it tests**: Threading deadlocks caused by circular imports
- **How it catches regressions**: Creates import scenarios with threading and locks
- **Resources**: 2 modules with locks and cross-imports, 4 concurrent threads
- **Expected behavior**: <10% deadlock failures, completes in <90s
- **Failure indicators**:
  - High deadlock rate (>10%)
  - Test hangs (indicates deadlock)
  - Excessive thread failures

##### `test_memory_leaks_in_circular_import_scenarios()`
- **What it tests**: Memory leaks from repeated circular import loading/unloading
- **How it catches regressions**: 20 cycles of import/unload with circular modules
- **Resources**: 5 circular modules, 20 import/unload cycles
- **Expected behavior**: <5MB growth over cycles, <1MB per cycle average
- **Failure indicators**:
  - Significant memory growth trend (>5MB)
  - High per-cycle retention (>2MB per cycle)
  - Memory not released after cycles

##### `test_all_project_modules_for_circular_imports()`
- **What it tests**: Actual project codebase for circular import issues
- **How it catches regressions**: Scans real project files for circular dependencies
- **Resources**: All Python files in netra_backend, auth_service, etc.
- **Expected behavior**: Analysis <30s, <20 total cycles, no large cycles (>5 modules)
- **Failure indicators**:
  - Too many circular imports found (>20)
  - Large circular import cycles (>5 modules)
  - Analysis takes too long (>30s)

### 4. Docker Health Validation Tests (`tests/validation/test_docker_health.py`)

**Purpose**: Validates Docker container health during pytest operations.

#### Test Scenarios:

##### `test_container_health_during_pytest_collection()`
- **What it tests**: Container health monitoring during collection
- **How it catches regressions**: Monitors containers while running collection on 100 test files
- **Resources**: All running project containers, continuous health monitoring
- **Expected behavior**: No critical health violations, containers remain running
- **Failure indicators**:
  - Containers become unhealthy during collection
  - Container crashes or restarts
  - Excessive memory violations (>2 per container)

##### `test_memory_usage_validation_under_load()`
- **What it tests**: Container memory behavior under system memory pressure
- **How it catches regressions**: Creates memory pressure while monitoring containers
- **Resources**: 500MB memory pressure, container memory monitoring
- **Expected behavior**: Container memory <95%, stability >80%
- **Failure indicators**:
  - Container memory exceeds 95% (limits not enforced)
  - Container crashes during memory pressure
  - Low stability ratio (<80%)

##### `test_cpu_usage_monitoring_during_intensive_operations()`
- **What it tests**: Container CPU usage during intensive operations
- **How it catches regressions**: Creates CPU pressure with mathematical operations
- **Resources**: 4 CPU-intensive threads, container CPU monitoring
- **Expected behavior**: Container CPU reasonable (<200%), no crashes
- **Failure indicators**:
  - Excessive container CPU usage (>200%)
  - Container status issues during CPU pressure
  - Runaway processes indicated by CPU metrics

##### `test_network_isolation_and_connectivity_validation()`
- **What it tests**: Network connectivity and isolation between containers
- **How it catches regressions**: Tests connectivity to expected service endpoints
- **Resources**: All running services (postgres, redis, clickhouse, backend, etc.)
- **Expected behavior**: >60% availability for each service, >1 service with >80% availability
- **Failure indicators**:
  - Low service availability (<60%)
  - Network connectivity issues
  - Container health degradation during network tests

##### `test_container_restart_and_recovery_validation()`
- **What it tests**: Container restart behavior and recovery
- **How it catches regressions**: Deliberately restarts non-critical containers
- **Resources**: Non-database containers (backend/frontend/auth)
- **Expected behavior**: Restart <90s, proper recovery, status becomes "running"
- **Failure indicators**:
  - Container fails to restart (<90s)
  - Container doesn't recover to "running" status
  - Persistent health violations after restart

##### `test_service_dependency_health_validation()`
- **What it tests**: Health validation of service dependencies
- **How it catches regressions**: Monitors categorized services (DB, cache, apps)
- **Resources**: All containers categorized by type (databases, caches, applications)
- **Expected behavior**: >85% stability per category, application health correlates with DB health
- **Failure indicators**:
  - Low dependency stability (<85%)
  - Applications unhealthy when databases are healthy
  - Critical dependency violations (>1)

### 5. Resource Limits Validation Tests (`tests/validation/test_resource_limits.py`)

**Purpose**: Validates resource limit enforcement and recovery mechanisms.

#### Test Scenarios:

##### `test_memory_limit_enforcement_and_recovery()`
- **What it tests**: System memory limit enforcement and recovery
- **How it catches regressions**: Exhausts memory to 60%, 75%, 85% and validates recovery
- **Resources**: Progressive memory exhaustion up to system limits
- **Expected behavior**: Recovery successful, peak <95%, residual increase <20%
- **Failure indicators**:
  - Memory exhaustion takes too long (>30s)
  - Recovery fails (memory not released)
  - System crashes instead of graceful degradation

##### `test_cpu_limit_enforcement_and_throttling()`
- **What it tests**: CPU limit enforcement and throttling
- **How it catches regressions**: Creates 70%, 90%, 100% CPU load with multiple threads
- **Resources**: Multi-threaded CPU-intensive mathematical operations
- **Expected behavior**: Achieves target CPU usage, recovers to <30%
- **Failure indicators**:
  - Cannot achieve target CPU usage (throttling too aggressive)
  - CPU doesn't recover after load (throttling not working)
  - System becomes unresponsive

##### `test_file_descriptor_limit_enforcement()`
- **What it tests**: File descriptor limit enforcement and recovery
- **How it catches regressions**: Opens files until hitting "too many open files" error
- **Resources**: Opens files until FD limit, then tests recovery
- **Expected behavior**: Hits FD limits gracefully, recovery allows new file operations
- **Failure indicators**:
  - Cannot exhaust FDs (limits not enforced)
  - Recovery fails (cannot open files after cleanup)
  - FD leak detected (>20 FDs not cleaned up)

##### `test_disk_space_limit_handling()`
- **What it tests**: Disk space limit handling and recovery
- **How it catches regressions**: Creates temporary files to consume disk space
- **Resources**: Up to 1GB temporary file creation (safety limited)
- **Expected behavior**: Disk space recovered after cleanup, can write files after recovery
- **Failure indicators**:
  - Disk space not recovered (temp files not cleaned)
  - Cannot write files after recovery
  - System instability after disk pressure

##### `test_combined_resource_exhaustion_resilience()`
- **What it tests**: System resilience under combined resource pressure
- **How it catches regressions**: Simultaneous memory, CPU, and FD exhaustion
- **Resources**: 3 concurrent threads exhausting different resources
- **Expected behavior**: >1 successful exhaustion, >67% recovery rate, basic functionality maintained
- **Failure indicators**:
  - System crashes under combined pressure
  - Low recovery rate (<67%)
  - Basic functionality lost after stress

##### `test_resource_limit_configuration_validation()`
- **What it tests**: Resource limit configuration validation
- **How it catches regressions**: Validates Docker and system limits are properly configured
- **Resources**: Inspects Docker container limits and system resource limits
- **Expected behavior**: Reasonable limits configured (256MB-8GB memory, >2GB system, >2 CPUs)
- **Failure indicators**:
  - No resource limits configured
  - Limits outside reasonable ranges
  - System resources insufficient for testing

## Test Execution Strategy

### Running the Full Suite

```bash
# Run all validation tests (recommended sequence)
python -m pytest tests/stress/test_docker_memory_limits.py -v
python -m pytest tests/stress/test_pytest_collection_performance.py -v
python -m pytest tests/stress/test_circular_imports.py -v
python -m pytest tests/validation/test_docker_health.py -v
python -m pytest tests/validation/test_resource_limits.py -v

# Run all tests together (may take up to 5 minutes)
python -m pytest tests/stress/ tests/validation/ -v --tb=short
```

### Individual Test Categories

```bash
# Memory-focused tests
python -m pytest tests/stress/test_docker_memory_limits.py tests/validation/test_resource_limits.py::test_memory_limit_enforcement_and_recovery -v

# Collection performance tests
python -m pytest tests/stress/test_pytest_collection_performance.py -v

# Import-related tests  
python -m pytest tests/stress/test_circular_imports.py -v

# Container health tests
python -m pytest tests/validation/test_docker_health.py -v
```

## Expected Timing

- **Memory Limit Tests**: ~60-90 seconds
- **Collection Performance**: ~120-180 seconds  
- **Circular Import Tests**: ~45-60 seconds
- **Docker Health Tests**: ~90-120 seconds
- **Resource Limits Tests**: ~90-120 seconds
- **Total Suite**: ~5-8 minutes (depending on system resources)

## Regression Detection Guarantees

Each test is specifically designed to catch regressions:

1. **Memory Tests**: Will hang, crash, or leak memory if OOM protection is broken
2. **Collection Tests**: Will timeout or consume excessive memory if collection optimization is broken
3. **Import Tests**: Will hang or deadlock if circular import handling is broken
4. **Health Tests**: Will show container instability if Docker limits aren't enforced
5. **Resource Tests**: Will crash or fail to recover if resource limiting is broken

## Edge Cases Covered

### Memory Edge Cases
- Gradual vs sudden memory exhaustion
- Memory fragmentation scenarios  
- Concurrent worker memory pressure
- Memory leaks in collection phase
- OOM killer simulation

### Collection Edge Cases  
- Large file counts (1000+ files)
- Complex nested directory structures
- Circular import scenarios during collection
- Collection interruption and recovery
- Parallel collection conflicts

### Import Edge Cases
- Simple circular imports (A->B->A)
- Complex multi-module cycles  
- Threading + circular imports (deadlock scenarios)
- Repeated import/unload cycles (leak detection)
- Real codebase circular dependency detection

### Container Edge Cases
- Memory pressure during collection
- CPU intensive operations
- Network connectivity validation
- Container restart scenarios
- Service dependency failures

### Resource Edge Cases
- Combined resource exhaustion
- Resource limit boundary conditions
- Recovery after resource exhaustion
- Resource configuration validation
- Cross-resource interaction effects

## Failure Analysis

When tests fail, they provide specific diagnostic information:

### Memory Failures
- Exact memory usage at failure point
- Time to exhaustion/recovery
- Memory leak detection (MB retained)
- OOM protection behavior analysis

### Collection Failures  
- Collection time breakdown
- Memory usage during collection
- Number of tests collected vs expected
- Error message analysis

### Import Failures
- Cycle detection results
- Import performance comparisons  
- Deadlock detection (timeout-based)
- Memory usage during import operations

### Container Failures
- Container health metrics over time
- Resource usage patterns
- Service availability percentages
- Recovery time measurements  

### Resource Failures
- Peak resource usage achieved
- Recovery success/failure indicators
- System stability assessment
- Resource configuration analysis

## Maintenance and Updates

### Adding New Edge Cases
1. Add new test methods following naming convention `test_<scenario>_<edge_case>()`
2. Include specific regression detection logic
3. Add appropriate timeout and resource limits
4. Update this documentation with new scenarios

### Updating Resource Limits
1. Review system capabilities in CI/test environments  
2. Adjust percentage-based limits in test constants
3. Update expected behavior documentation
4. Test on multiple environments before deployment

### Monitoring Test Effectiveness
1. Periodically remove fixes and verify tests fail
2. Monitor test execution times for performance regressions
3. Review false positive/negative rates
4. Update thresholds based on environment changes

## Integration with CI/CD

### Pre-commit Hooks
- Run memory and import tests (fastest subset)
- Skip container tests in pre-commit (require Docker)

### CI Pipeline Integration
- Run full suite in Docker environment
- Parallel execution where safe (non-interfering tests)
- Failure notification with specific diagnostic info

### Performance Monitoring
- Track test execution times over time  
- Alert on test duration regressions (>20% slower)
- Monitor resource usage patterns in CI

## Conclusion

This test suite provides comprehensive validation of Docker pytest crash fixes through:

1. **Actual Resource Exhaustion**: Tests actually exhaust resources to trigger bugs
2. **Edge Case Coverage**: Covers complex scenarios that caused original crashes  
3. **Regression Detection**: Will fail if fixes are removed or broken
4. **Clear Diagnostics**: Provides actionable failure information
5. **Time-Bounded Execution**: Completes within reasonable time limits
6. **Real-World Scenarios**: Tests real combinations of stress conditions

The suite is designed to be both thorough and maintainable, providing confidence that Docker pytest crash fixes remain effective over time.