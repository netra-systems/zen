# Test Framework - Unified Test Infrastructure

## ⚠️ IMPORTANT: Primary Test Runners

**`tests/unified_test_runner.py`** is the PRIMARY test runner for the Netra AI Platform.

**Alternative runners for specific use cases:**
- `test_framework/integrated_test_runner.py` - Alpine-based isolated testing
- `scripts/docker_manual.py test` - Docker-integrated testing

## Overview

The Netra Test Framework provides a unified, modular testing infrastructure with intelligent test organization, execution efficiency, and comprehensive failure analysis.

## Key Features

### 🎯 Intelligent Test Organization
- **Automatic categorization** of tests based on path and naming patterns
- **Priority-based execution** to run critical tests first
- **Dependency management** to handle test interdependencies
- **Smart test selection** based on recent code changes

### 🚀 Advanced Execution
- **Parallel execution** with configurable worker pools
- **Automatic retry** for flaky tests with confidence scoring
- **Fail-fast mode** for rapid feedback
- **Progressive timeout** based on historical test duration

### 🔍 Failure Pattern Analysis
- **Pattern recognition** to identify common failure causes
- **Root cause analysis** with actionable recommendations
- **Flaky test detection** using statistical analysis
- **Regression detection** to catch newly introduced failures

### 📊 Comprehensive Reporting
- **Multi-format reports** (JSON, Markdown, HTML)
- **Historical trend analysis** to track test health over time
- **Performance metrics** to identify slow tests
- **Coverage integration** with target tracking

## Architecture

```
tests/
└── unified_test_runner.py       # ⭐ PRIMARY TEST RUNNER

test_framework/
├── __init__.py                  # Module exports
├── unified_docker_manager.py    # ⭐ SSOT for Docker operations
├── resource_monitor.py          # Resource usage monitoring
├── environment_lock.py          # Thread-safe environment management
├── docker_rate_limiter.py       # Docker API rate limiting
├── docker_force_flag_guardian.py # Force flag prohibition
├── integrated_test_runner.py    # Alpine-based isolated runner
├── unified_orchestrator.py      # Service orchestration
├── ssot/                        # SSOT test infrastructure
│   ├── base_test_case.py        # Canonical base test class
│   ├── mock_factory.py          # Single mock generator
│   ├── database_test_utility.py # Unified database testing
│   ├── websocket_test_utility.py # Unified WebSocket testing
│   └── docker_test_utility.py   # Unified Docker testing
├── test_discovery.py            # Test discovery engine
├── failure_pattern_analyzer.py  # Pattern recognition & analysis
├── report_generators.py         # Multi-format report generation
└── comprehensive_reporter.py    # Comprehensive reporting
```

## Quick Start

### Basic Usage

```bash
# Primary test runner (recommended)
python tests/unified_test_runner.py --category unit --no-coverage --fast-fail

# Run mission critical tests
python tests/unified_test_runner.py --category mission_critical --real-services

# Run with Docker services
python tests/unified_test_runner.py --real-services  # Docker starts automatically

# Run specific test categories
python tests/unified_test_runner.py --categories smoke unit integration api

# Alpine-based isolated testing
python test_framework/integrated_test_runner.py --mode isolated --suites unit integration

# Docker manual operations
python scripts/docker_manual.py start     # Start test environment
python scripts/docker_manual.py test      # Run tests with Docker
python scripts/docker_manual.py status    # Check status
```

### Test Categories

| Category | Description | Duration | Use Case |
|----------|------------|----------|----------|
| `smoke` | Quick validation tests | < 30s | Pre-commit hooks |
| `unit` | Isolated component tests | 1-2 min | Development |
| `integration` | Component interaction tests | 3-5 min | Feature validation |
| `mission_critical` | Business-critical tests | 5-10 min | Pre-deployment |
| `e2e` | End-to-end flows | 10-15 min | Pre-release |
| `api` | API endpoint tests | 2-3 min | API validation |

## 🚀 New Infrastructure Features (2025-09-02)

### Resource Monitoring
The framework now includes comprehensive resource monitoring to prevent system overload:

```python
from test_framework.resource_monitor import DockerResourceMonitor

monitor = DockerResourceMonitor()
# Check system resources
snapshot = monitor.check_system_resources()
# Run tests with resource monitoring...
resource_usage = monitor.get_resource_usage()
```

**Features:**
- Memory usage tracking and limits
- CPU utilization monitoring  
- Docker container resource tracking
- Automatic test throttling when resources exceed thresholds

### Environment Locking
Thread-safe environment management prevents test conflicts:

```python
from test_framework.environment_lock import EnvironmentLock

with EnvironmentLock("test_env"):
    # Exclusive access to environment variables
    os.environ["TEST_VAR"] = "value"
```

### Docker Rate Limiting
Prevents Docker daemon crashes from excessive API calls:

```python
from test_framework.docker_rate_limiter import DockerRateLimiter

limiter = DockerRateLimiter(max_calls_per_second=10)
async with limiter:
    # Docker operations are automatically rate-limited
    pass
```

### Force Flag Guardian
Enforces prohibition of dangerous Docker force operations:

```python
from test_framework.docker_force_flag_guardian import DockerForceGuardian

guardian = DockerForceGuardian()
guardian.validate_command(docker_cmd)  # Raises error if force flag detected
```

## Components

### 1. Test Suite Orchestrator

The orchestrator manages test execution with intelligent scheduling:

```python
from test_framework.test_suite_orchestrator import TestSuiteOrchestrator

orchestrator = TestSuiteOrchestrator()

# Discover tests
discovered = orchestrator.discover_tests()

# Execute suite with options
results = await orchestrator.execute_suite(
    "unit",
    parallel=True,
    fail_fast=False,
    retry_failed=True
)

# Get insights
insights = orchestrator.get_test_insights()
```

**Key Features:**
- Test discovery with automatic categorization
- Priority-based execution ordering
- Parallel execution with semaphore control
- Automatic retry with exponential backoff
- Test profile tracking for historical analysis

### 2. Failure Pattern Analyzer

Analyzes test failures to identify patterns and root causes:

```python
from test_framework.failure_pattern_analyzer import FailurePatternAnalyzer

analyzer = FailurePatternAnalyzer()

# Analyze failures
analysis = analyzer.analyze_batch(failures)

# Get recommendations
for rec in analysis["recommendations"]:
    print(f"[{rec['priority']}] {rec['action']}")

# Generate report
report = analyzer.get_pattern_report()
```

**Pattern Categories:**
- Import errors (missing dependencies)
- Database connection issues
- Timeout errors
- Mock assertion failures
- Type mismatches
- Permission errors
- Flaky test patterns

### 3. Unified Test Runner

The ONLY entry point for all testing (use test_runner.py in project root):

```python
# DO NOT import or use test framework modules directly
# Always use the test_runner.py CLI:

# From command line:
# python test_runner.py --level unit --parallel auto

# The test_runner.py handles all configuration and execution
```

## Test Categories

Tests are automatically categorized based on their location and naming:

| Category | Pattern | Priority | Description |
|----------|---------|----------|-------------|
| `smoke` | */smoke/* | Critical | Quick validation tests |
| `unit` | */unit/*, */core/* | Medium | Isolated component tests |
| `integration` | */integration/* | Medium | Component interaction tests |
| `api` | */routes/*, */api/* | High | API endpoint tests |
| `database` | */db/*, */database/* | High | Database layer tests |
| `auth` | */auth/*, */security/* | Critical | Authentication tests |
| `websocket` | */websocket/*, */ws_* | Medium | WebSocket tests |
| `agent` | */agents/* | Medium | AI agent tests |
| `llm` | */llm/* | Low | LLM integration tests |
| `e2e` | */e2e/*, */cypress/* | Low | End-to-end tests |
| `performance` | */perf/*, */performance/* | Low | Performance tests |

## Failure Pattern Recognition

The framework identifies common failure patterns:

### Known Patterns

1. **Import Errors**
   - Missing modules
   - Circular imports
   - Version conflicts

2. **Connection Errors**
   - Database unavailable
   - Redis connection refused
   - WebSocket disconnected

3. **Test Issues**
   - Flaky tests (intermittent failures)
   - Timeout errors
   - Mock configuration problems

4. **Regressions**
   - Recently introduced failures
   - Breaking changes in dependencies

### Pattern Analysis Output

```json
{
  "pattern_id": "database_connection",
  "category": "database_error",
  "occurrences": 15,
  "affected_tests": ["test_db_connection", "test_repository"],
  "confidence": 0.95,
  "suggested_fix": "Ensure database is running and migrations are up to date"
}
```

## Configuration

### test_config.json

```json
{
  "max_parallel": 8,
  "timeout_multiplier": 1.5,
  "retry_flaky": true,
  "fail_fast": false,
  "coverage_threshold": 80,
  "test_categories": {
    "unit": {
      "priority": 2,
      "parallel": true,
      "timeout": 60
    },
    "integration": {
      "priority": 3,
      "parallel": true,
      "timeout": 120
    }
  }
}
```

### Environment Variables

```bash
# Control test execution
TEST_PARALLEL_WORKERS=4
TEST_TIMEOUT_MULTIPLIER=2
TEST_RETRY_COUNT=2

# Enable features
TEST_COVERAGE=true
TEST_FAIL_FAST=false
TEST_VERBOSE=true
```

## Reports

### Report Formats

1. **JSON Report** - Machine-readable format for CI/CD
2. **Markdown Report** - Human-readable documentation
3. **HTML Report** - Interactive dashboard (coming soon)

### Report Structure

```
tests/test_reports/modular/
├── test_report_unit_20250813_120000.json
├── test_report_unit_20250813_120000.md
├── analysis/
│   ├── failure_patterns.json
│   └── test_insights.json
└── metrics/
    ├── performance_metrics.json
    └── coverage_trends.json
```

## Best Practices

### 1. Test Organization

- **Group related tests** in the same directory
- **Use descriptive names** that indicate test purpose
- **Follow naming conventions** for automatic categorization
- **Add test markers** for fine-grained control

### 2. Failure Management

- **Review failure patterns** regularly
- **Fix consistent failures** before flaky ones
- **Update known patterns** when new issues arise
- **Document workarounds** in test comments

### 3. Performance Optimization

- **Run tests in parallel** when possible
- **Use fail-fast** for rapid feedback
- **Skip expensive tests** during development
- **Cache test fixtures** to reduce setup time

### 4. Continuous Improvement

- **Monitor test health metrics**
- **Track coverage trends**
- **Identify and fix slow tests**
- **Refactor flaky tests**

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run Tests
  run: |
    python test_runner.py \
      --level ${{ matrix.level }} \
      --parallel auto \
      --fail-fast
  
- name: Analyze Failures
  if: failure()
  run: |
    python test_runner.py --show-failing
```

### Jenkins Pipeline

```groovy
stage('Test') {
    parallel {
        stage('Unit Tests') {
            steps {
                sh 'python test_runner.py --level unit'
            }
        }
        stage('Integration Tests') {
            steps {
                sh 'python test_runner.py --level integration'
            }
        }
    }
}
```

## Troubleshooting

### Common Issues

1. **Tests not discovered**
   - Check test naming conventions
   - Verify test directory structure
   - Review categorization patterns

2. **Parallel execution issues**
   - Reduce worker count
   - Check for test interdependencies
   - Review resource constraints

3. **Pattern not recognized**
   - Update error signatures
   - Add new pattern definition
   - Review pattern confidence threshold

4. **Flaky test detection**
   - Increase test history threshold
   - Review flaky score calculation
   - Check for environmental factors

## Future Enhancements

- [ ] HTML dashboard with interactive charts
- [ ] Machine learning for pattern prediction
- [ ] Automatic test generation
- [ ] Integration with code coverage tools
- [ ] Test impact analysis based on code changes
- [ ] Distributed test execution
- [ ] Real-time test monitoring
- [ ] Automatic flaky test quarantine

## Contributing

To add new patterns or improve the framework:

1. Add pattern definitions to `failure_pattern_analyzer.py`
2. Update categorization logic in `test_suite_orchestrator.py`
3. Add new test levels in `test_config.py`
4. Integrate changes through `test_runner.py` (DO NOT create new runners)
5. Update documentation with new features

## License

Part of the Netra AI Optimization Platform - Enterprise License