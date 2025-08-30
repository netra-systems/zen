# E2E Test Execution Strategy: Fast-Fail with Comprehensive Failure Recording

## Executive Summary

This document outlines the strategy for running E2E tests with effective fast-fail mechanisms while ensuring comprehensive failure recording and preventing infinite loops or perpetual stuck states.

## Current State Analysis

### Existing Infrastructure

1. **Unified Test Runner** (`scripts/unified_test_runner.py`)
   - Supports multiple fail-fast modes via `FailFastStrategy`
   - Category-based execution with priority levels
   - Progress tracking and execution history
   - Test execution timeout configuration

2. **Fail-Fast Strategies** (`test_framework/fail_fast_strategies.py`)
   - Multiple modes: DISABLED, FIRST_FAILURE, CATEGORY_FAILURE, CRITICAL_FAILURE, THRESHOLD_BASED, SMART_ADAPTIVE, DEPENDENCY_AWARE
   - Failure event tracking with impact assessment
   - Skip decision logic based on failure patterns
   - Configurable thresholds and time windows

3. **Cypress Integration** (`test_framework/cypress_runner.py`)
   - Service dependency management
   - Dynamic configuration generation
   - Results aggregation
   - Timeout configuration (default 30 minutes)

4. **Test Execution Tracking** (`scripts/test_execution_tracker.py`)
   - SQLite-based execution history
   - Failure pattern analysis
   - Priority scoring for test selection
   - Flaky test detection

### Identified Gaps

1. **Timeout Management**
   - No cascading timeout mechanism (test → category → suite)
   - Missing adaptive timeout based on historical data
   - No circuit breaker for perpetually failing tests

2. **Failure Recording**
   - Incomplete capture of timeout scenarios
   - Missing structured failure categorization
   - No automatic failure report generation for E2E tests

3. **Recovery Mechanisms**
   - No automatic retry with backoff for transient failures
   - Missing service health pre-checks before E2E execution
   - No graceful degradation when services are partially available

4. **Loop Prevention**
   - No detection of cyclic test dependencies
   - Missing maximum retry limits at suite level
   - No prevention of infinite wait states in async operations

## Remediation Plan

### 1. Enhanced Timeout Architecture

```python
class TimeoutStrategy:
    """Multi-level timeout management"""
    
    TIMEOUTS = {
        'test': 60,        # Individual test timeout (seconds)
        'category': 600,   # Category timeout (10 minutes)
        'suite': 1800,     # Full suite timeout (30 minutes)
        'service': 30,     # Service availability check
        'websocket': 5,    # WebSocket connection timeout
    }
    
    ADAPTIVE_MULTIPLIERS = {
        'first_run': 2.0,      # Extra time for first runs
        'flaky_test': 1.5,     # Extra time for known flaky tests
        'peak_hours': 1.3,     # Extra time during peak usage
    }
```

### 2. Comprehensive Failure Recording

```python
class FailureRecorder:
    """Enhanced failure recording with categorization"""
    
    FAILURE_CATEGORIES = {
        'TIMEOUT': ['test_timeout', 'service_timeout', 'network_timeout'],
        'ASSERTION': ['value_mismatch', 'missing_element', 'unexpected_state'],
        'INFRASTRUCTURE': ['service_down', 'database_error', 'auth_failure'],
        'ENVIRONMENT': ['config_missing', 'dependency_not_found', 'permission_denied'],
        'FLAKY': ['intermittent_failure', 'timing_issue', 'race_condition'],
    }
    
    def record_failure(self, test, error, context):
        """Record failure with full context preservation"""
        return {
            'test_id': test.id,
            'category': self.categorize_error(error),
            'timestamp': datetime.now(),
            'error_details': {
                'message': str(error),
                'stack_trace': traceback.format_exc(),
                'type': type(error).__name__,
            },
            'context': {
                'environment': context.env,
                'services_status': context.services,
                'test_duration': context.duration,
                'retry_count': context.retries,
            },
            'recovery_attempted': context.recovery_actions,
        }
```

### 3. Smart Retry with Circuit Breaker

```python
class SmartRetryStrategy:
    """Intelligent retry with circuit breaker pattern"""
    
    def __init__(self):
        self.circuit_breakers = {}  # Per-test circuit breakers
        self.retry_config = {
            'max_retries': 3,
            'backoff_base': 2,
            'max_backoff': 30,
            'jitter': True,
        }
    
    def should_retry(self, test_id, failure_type):
        """Determine if test should be retried"""
        
        # Check circuit breaker state
        if self.circuit_breakers.get(test_id, {}).get('open', False):
            return False
            
        # Don't retry certain failure types
        non_retriable = ['assertion_failure', 'compilation_error', 'import_error']
        if failure_type in non_retriable:
            return False
            
        # Check retry budget
        if self.get_retry_count(test_id) >= self.retry_config['max_retries']:
            self.open_circuit_breaker(test_id)
            return False
            
        return True
```

### 4. Loop Prevention Mechanisms

```python
class LoopPrevention:
    """Prevent infinite loops and stuck states"""
    
    def __init__(self):
        self.execution_stack = []
        self.wait_states = {}
        self.max_stack_depth = 100
        self.max_wait_time = 300  # 5 minutes max wait
    
    def check_cyclic_dependency(self, test_id):
        """Detect cyclic test dependencies"""
        if test_id in self.execution_stack:
            cycle = self.execution_stack[self.execution_stack.index(test_id):]
            raise CyclicDependencyError(f"Cycle detected: {' -> '.join(cycle)}")
        
        if len(self.execution_stack) > self.max_stack_depth:
            raise StackOverflowError("Maximum test dependency depth exceeded")
    
    async def monitored_wait(self, coroutine, test_id, timeout=None):
        """Monitor async operations to prevent infinite waits"""
        timeout = timeout or self.max_wait_time
        
        try:
            self.wait_states[test_id] = {
                'start_time': time.time(),
                'timeout': timeout,
            }
            
            result = await asyncio.wait_for(coroutine, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            self.record_timeout(test_id)
            raise TestTimeoutError(f"Test {test_id} exceeded timeout of {timeout}s")
            
        finally:
            self.wait_states.pop(test_id, None)
```

## Implementation Commands

### Running E2E Tests with Fast-Fail

```bash
# Basic E2E run with category-level fast-fail
python unified_test_runner.py --category e2e --fail-fast-mode category_failure

# Smart adaptive mode with failure recording
python unified_test_runner.py --category e2e --fail-fast-mode smart_adaptive --verbose

# Threshold-based with custom limits
python unified_test_runner.py --category e2e \
    --fail-fast-mode threshold_based \
    --failure-threshold 0.3 \
    --consecutive-failures 3

# With retry and circuit breaker
python unified_test_runner.py --category e2e \
    --fail-fast-mode smart_adaptive \
    --enable-retry \
    --max-retries 2 \
    --circuit-breaker-threshold 5
```

### Cypress-Specific E2E Commands

```bash
# Run Cypress with built-in fail-fast
npm run cy:run -- --bail

# Run specific spec with retries
npm run cy:run -- --spec "cypress/e2e/critical-*.cy.ts" --retries 2

# Headless with failure screenshots
npm run cy:run -- --headed false --screenshot on-failure --video false
```

### Monitoring and Recovery

```bash
# Check test execution status
python scripts/test_execution_tracker.py status --category e2e

# Generate failure report
python scripts/test_execution_tracker.py report --failures-only --last-24h

# Reset circuit breakers
python scripts/test_execution_tracker.py reset-circuits --category e2e

# Analyze flaky tests
python scripts/test_execution_tracker.py analyze-flaky --threshold 0.2
```

## Best Practices

### 1. Pre-Execution Checks

Always verify service availability before running E2E tests:

```python
def pre_e2e_checks():
    """Run before E2E test suite"""
    checks = [
        verify_database_connection(),
        verify_auth_service(),
        verify_backend_api(),
        verify_websocket_server(),
        check_test_data_exists(),
    ]
    
    if not all(checks):
        raise EnvironmentError("Pre-execution checks failed")
```

### 2. Failure Categorization

Properly categorize failures for better analysis:

```python
FAILURE_PATTERNS = {
    r'.*timeout.*': 'TIMEOUT',
    r'.*connection refused.*': 'INFRASTRUCTURE',
    r'.*assertion.*': 'ASSERTION',
    r'.*not found.*': 'MISSING_ELEMENT',
    r'.*unauthorized.*': 'AUTH_FAILURE',
}
```

### 3. Progressive Test Execution

Run tests in order of criticality:

```python
TEST_PRIORITY = {
    'smoke': 100,      # Run first
    'auth': 90,        # Critical path
    'core_features': 80,
    'integrations': 70,
    'edge_cases': 60,
    'performance': 50,  # Run last
}
```

### 4. Graceful Degradation

Handle partial service availability:

```python
def run_with_degradation(test_suite):
    """Run tests that can work with available services"""
    available_services = check_service_availability()
    
    if not available_services['database']:
        skip_tests_requiring('database')
    
    if not available_services['websocket']:
        mark_tests_as_xfail('real_time_features')
    
    return run_applicable_tests(test_suite, available_services)
```

## Monitoring Dashboard

Key metrics to track:

1. **Execution Metrics**
   - Total tests run
   - Pass/fail ratio
   - Average duration
   - Timeout occurrences

2. **Failure Analysis**
   - Failure categories distribution
   - Top failing tests
   - Flakiness score
   - Recovery success rate

3. **Performance Indicators**
   - Time saved by fast-fail
   - Circuit breaker activations
   - Retry effectiveness
   - Service availability correlation

## Recovery Procedures

### When Tests Get Stuck

1. **Immediate Actions**
   ```bash
   # Kill stuck processes
   pkill -f "cypress|pytest|node"
   
   # Clear test locks
   rm -f test_data/.locks/*
   
   # Reset test database
   python scripts/reset_test_db.py
   ```

2. **Investigation**
   ```bash
   # Check running processes
   ps aux | grep -E "cypress|pytest"
   
   # Review recent logs
   tail -f logs/test_execution.log
   
   # Analyze timeout patterns
   python scripts/analyze_timeouts.py --last-hour
   ```

3. **Prevention**
   - Implement hard timeout at OS level
   - Use process monitors with auto-kill
   - Add deadlock detection in async code
   - Regular health checks during execution

## Summary

This comprehensive strategy ensures:

1. **Fast Failure Detection**: Multiple fail-fast modes prevent wasting time on doomed test runs
2. **Complete Failure Recording**: All failures are captured with full context for analysis
3. **Loop Prevention**: Multiple mechanisms prevent infinite loops and stuck states
4. **Smart Recovery**: Intelligent retry logic with circuit breakers prevents perpetual failure
5. **Operational Visibility**: Comprehensive monitoring and reporting for continuous improvement

The implementation balances speed (fast-fail) with completeness (failure recording) while maintaining system stability through timeout management and loop prevention.