# Agent Startup E2E Testing Guide

## Overview

This comprehensive guide covers agent startup End-to-End (E2E) testing for Netra Apex. Agent startup tests validate the complete agent initialization flow from cold start to meaningful response, protecting the entire $200K+ MRR by ensuring reliable startup processes.

## Business Value

**Business Value Justification (BVJ):**
- **Segment**: ALL customer segments (Free, Early, Mid, Enterprise)
- **Business Goal**: Ensure 100% reliable agent startup across all scenarios
- **Value Impact**: Prevents agent initialization failures that block user interactions
- **Revenue Impact**: Protects entire revenue stream by ensuring reliable startup process

## Test Categories

### 1. Cold Start Tests
- **Purpose**: Complete system initialization from zero state
- **File**: `tests/unified/test_agent_cold_start.py`
- **Requires Real LLM**: Yes
- **Timeout**: 30 seconds
- **Business Critical**: YES

### 2. Concurrent Startup Tests
- **Purpose**: Concurrent agent startup isolation validation
- **File**: `tests/unified/test_concurrent_agents.py`
- **Requires Real LLM**: Yes
- **Timeout**: 45 seconds
- **Business Critical**: YES

### 3. Tier-Based Startup Tests
- **Purpose**: Startup across different customer tiers (Free, Early, Mid, Enterprise)
- **Requires Real LLM**: Yes
- **Timeout**: 60 seconds
- **Revenue Impact**: Direct tier-based feature validation

### 4. Agent Isolation Tests
- **Purpose**: Agent state isolation validation
- **Requires Real LLM**: No
- **Timeout**: 30 seconds
- **Focus**: Data integrity and security

### 5. Routing Startup Tests
- **Purpose**: Message routing during startup phases
- **Requires Real LLM**: No
- **Timeout**: 25 seconds
- **Focus**: System reliability

### 6. Performance Startup Tests
- **Purpose**: Performance metrics under startup load
- **Requires Real LLM**: Yes
- **Timeout**: 40 seconds
- **SLA**: < 5 seconds for complete cold start

## Quick Start

### Running Tests Locally

#### 1. Basic Test Execution (Recommended for Development)
```bash
# Quick test with mocks - fastest feedback
python run_agent_startup_tests.py

# Using the main test runner
python test_runner.py --level agent-startup
```

#### 2. Full Validation with Real LLM (Recommended for Releases)
```bash
# Real LLM testing - complete validation
python run_agent_startup_tests.py --real-llm

# Using the main test runner with real LLM
python test_runner.py --level agent-startup --real-llm
```

#### 3. Safe Sequential Execution
```bash
# Sequential execution (safer but slower)
python run_agent_startup_tests.py --real-llm --sequential
```

### Test Information and Discovery

```bash
# Show detailed test information
python run_agent_startup_tests.py --info

# List available test categories
python run_agent_startup_tests.py --list-categories

# Show execution time estimates
python run_agent_startup_tests.py --estimate
```

## Environment Setup Requirements

### Prerequisites

1. **Services Running**:
   - Auth Service (port 8001)
   - Backend Service (port 8000)
   - Database services (PostgreSQL, ClickHouse)

2. **Environment Variables**:
   ```bash
   # Required for real LLM testing
   OPENAI_API_KEY=your_openai_key
   ANTHROPIC_API_KEY=your_anthropic_key
   
   # Test configuration
   TEST_DATABASE_URL=your_test_db_url
   TEST_CLICKHOUSE_URL=your_test_clickhouse_url
   
   # Service URLs (if different from defaults)
   AUTH_SERVICE_URL=http://localhost:8001
   BACKEND_SERVICE_URL=http://localhost:8000
   ```

3. **Test Data**:
   - Test users for each tier (Free, Early, Mid, Enterprise)
   - Seed data for agent initialization
   - Performance baseline data

### Starting Services

```bash
# Start development environment
python scripts/dev_launcher.py

# Or start services individually
cd auth_service && python main.py &
cd app && python main.py &
```

## Performance Baselines

### Cold Start Performance Requirements

| Metric | Baseline | Warning | Critical | Business Impact |
|--------|----------|---------|----------|-----------------|
| Complete Cold Start | < 5.0s | 6.0s | 8.0s | User experience, conversion |
| Concurrent Startup (3 users) | < 8.0s | 10.0s | 12.0s | Scalability, enterprise |
| Tier Startup (per tier) | < 6.0s | 8.0s | 10.0s | Tier feature validation |
| Agent Isolation | < 3.0s | 4.0s | 5.0s | Security, data integrity |
| Routing Validation | < 2.5s | 3.5s | 5.0s | System reliability |
| Performance Metrics | < 4.0s | 6.0s | 8.0s | Monitoring effectiveness |

### Performance Baseline Configuration

The system uses `app/tests/performance/performance_baseline_config.py` for:
- Metric definitions and thresholds
- Performance evaluation logic
- Baseline tracking over time
- SLA monitoring and reporting

## Troubleshooting Common Issues

### 1. Service Connection Issues

**Symptom**: Tests fail with "Service not ready" errors

**Solutions**:
```bash
# Check service health
curl http://localhost:8001/health  # Auth service
curl http://localhost:8000/health  # Backend service

# Restart services if needed
python scripts/dev_launcher.py --restart

# Check service logs
python scripts/dev_launcher.py --logs
```

### 2. Authentication Failures

**Symptom**: Auth service returns 401/403 errors

**Solutions**:
```bash
# Verify test users exist
python scripts/seed_test_users.py

# Reset auth database
python scripts/reset_auth_db.py --test-data

# Check JWT token configuration
python scripts/validate_auth_config.py
```

### 3. WebSocket Connection Issues

**Symptom**: WebSocket connections fail or timeout

**Solutions**:
```bash
# Check WebSocket endpoint
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: test" \
  -H "Sec-WebSocket-Version: 13" \
  http://localhost:8000/ws

# Verify backend service WebSocket support
python scripts/test_websocket_health.py
```

### 4. Real LLM API Issues

**Symptom**: Tests fail with LLM API errors

**Solutions**:
```bash
# Check API keys
echo $OPENAI_API_KEY | cut -c1-10  # Should show key prefix
echo $ANTHROPIC_API_KEY | cut -c1-10

# Test API connectivity
python scripts/test_llm_connectivity.py

# Use mock mode for development
python run_agent_startup_tests.py  # Runs with mocks by default
```

### 5. Performance Threshold Failures

**Symptom**: Tests pass functionally but fail on performance

**Solutions**:
1. **Check System Load**:
   ```bash
   top -p $(pgrep -f "python.*main.py")  # Check CPU/memory
   ```

2. **Review Performance Baselines**:
   ```bash
   python scripts/review_performance_baselines.py
   ```

3. **Run Performance Analysis**:
   ```bash
   python test_runner.py --level agent-startup --real-llm --profile
   ```

### 6. Database Connection Issues

**Symptom**: Database-related test failures

**Solutions**:
```bash
# Check database connections
python scripts/test_database_connectivity.py

# Reset test databases
python scripts/reset_test_databases.py

# Verify migrations
python scripts/run_test_migrations.py
```

## Adding New Agent Startup Tests

### 1. Test Structure

Create tests in `tests/unified/` following the pattern:

```python
"""
New Agent Startup Test - Description

Business Value Justification (BVJ):
1. Segment: Target customer segment
2. Business Goal: Specific business objective
3. Value Impact: Expected value impact
4. Revenue Impact: Revenue protection/growth estimate
"""

import asyncio
import pytest
from .harness_complete import TestHarnessContext

class NewStartupTestManager:
    """Manages new startup test execution."""
    
    def __init__(self):
        """Initialize test manager."""
        # Keep under 8 lines (MANDATORY)
        pass

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.real_services  # If requires real services
async def test_new_startup_scenario():
    """Test new startup scenario."""
    manager = NewStartupTestManager()
    # Test implementation under 8 lines per function (MANDATORY)
    await _execute_new_test(manager)

async def _execute_new_test(manager):
    """Execute the new test within harness context."""
    async with TestHarnessContext("new_test") as harness:
        # Test logic here
        pass
```

### 2. Register Test in Runner

Add to `tests/unified/run_agent_startup_tests.py`:

```python
def _initialize_test_configs(self) -> List[StartupTestConfig]:
    """Initialize startup test configurations."""
    return [
        # Existing configs...
        StartupTestConfig(
            AgentStartupCategory.NEW_CATEGORY,  # Add new category to enum
            "test_new_startup",  # Test module name
            "test_new_startup_scenario",  # Test function name
            45,  # Timeout seconds
            True,  # Requires real LLM
            True,  # Parallel safe
            "new_startup_time"  # Performance metric name
        ),
    ]
```

### 3. Add Performance Metrics

Add to `app/tests/performance/performance_baseline_config.py`:

```python
metrics['new_startup_time'] = PerformanceMetric(
    name='New Startup Scenario',
    category=PerformanceCategory.AGENT,
    description='Time for new startup scenario completion',
    unit='seconds',
    baseline_value=5.0,
    warning_threshold=7.0,
    critical_threshold=10.0
)
```

### 4. Update Test Configuration

Add to `test_framework/test_config.py`:

```python
"agent-startup": {
    # Existing configuration...
    "backend_args": [
        "tests/unified/test_agent_cold_start.py",
        "tests/unified/test_concurrent_agents.py",
        "tests/unified/test_new_startup.py",  # Add new test file
        # Other args...
    ],
}
```

## CI/CD Integration

### GitHub Actions Integration

The agent startup tests integrate with the CI/CD pipeline through:

1. **Workflow Configuration** (`.github/workflows/unified-test-runner.yml`):
   ```yaml
   - name: Run Agent Startup Tests
     run: |
       python test_runner.py --level agent-startup --real-llm
     env:
       OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
       ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
   ```

2. **Test Matrix Configuration** (`.github/scripts/test_matrix_config.py`):
   - Parallel execution strategies
   - Service dependency management
   - Failure analysis and reporting

3. **Failure Analysis** (`.github/scripts/failure_analysis.py`):
   - Automatic failure categorization
   - Performance regression detection
   - Business impact assessment

### Pre-deployment Validation

```bash
# Required before any deployment
python test_runner.py --level agent-startup --real-llm --coverage
```

### Staging Environment Testing

```bash
# Test against staging environment
STAGING_MODE=true python run_agent_startup_tests.py --real-llm
```

## Business Value Tracking

### Test Results and Business Impact

Each test category maps to specific business metrics:

| Test Category | Business Metric | Revenue Protection |
|---------------|-----------------|-------------------|
| Cold Start | First-time user conversion | $50K+ MRR |
| Concurrent Startup | Enterprise scalability | $80K+ MRR |
| Tier Startup | Feature differentiation | $60K+ MRR |
| Agent Isolation | Security compliance | $100K+ MRR |
| Routing | System reliability | $40K+ MRR |
| Performance | User satisfaction | $70K+ MRR |

### Performance SLA Monitoring

The tests enforce business-critical SLAs:

1. **Cold Start SLA**: < 5 seconds (99.9% uptime requirement)
2. **Concurrent User SLA**: < 8 seconds for 3+ users
3. **Tier Feature SLA**: < 6 seconds across all tiers
4. **Security SLA**: Zero state leakage between users

### Test Result Reporting

Test results are automatically saved to:
- `test_reports/agent_startup_test_report.json`
- Performance baselines in `test_reports/performance_baselines.json`
- Business impact analysis in CI/CD pipeline

## Integration with Main Test Runner

### Test Level Integration

Agent startup tests are integrated as a distinct test level:

```bash
# Available test levels including agent-startup
python test_runner.py --list-levels

# Run with main test runner
python test_runner.py --level agent-startup [options]
```

### Test Runner Options

| Option | Description | Business Impact |
|--------|-------------|-----------------|
| `--real-llm` | Use real LLM APIs | Complete validation |
| `--coverage` | Generate coverage reports | Quality assurance |
| `--profile` | Performance profiling | Optimization insights |
| `--parallel` | Parallel execution | Development speed |
| `--timeout N` | Custom timeout | Resource management |

### Example Integration Commands

```bash
# Development workflow
python test_runner.py --level agent-startup --fast-fail

# Pre-release validation
python test_runner.py --level agent-startup --real-llm --coverage

# Performance analysis
python test_runner.py --level agent-startup --real-llm --profile --timeout 600
```

## Best Practices

### 1. Test Development Guidelines

- **File Size**: Maximum 300 lines per file (MANDATORY)
- **Function Size**: Maximum 8 lines per function (MANDATORY)
- **Real Services**: Use real services, minimize mocks
- **Performance**: Always include performance validation
- **Business Value**: Include BVJ in every test file

### 2. Test Execution Guidelines

- **Development**: Use mocked tests for fast feedback
- **Feature Testing**: Use `--real-llm` for complete validation
- **Release Testing**: Always run with `--real-llm --coverage`
- **Debugging**: Use sequential mode for isolation

### 3. Performance Guidelines

- **Monitor Trends**: Track performance over time
- **Set Realistic Baselines**: Based on business requirements
- **Alert on Regressions**: Automatic notifications for threshold breaches
- **Regular Reviews**: Monthly performance baseline reviews

### 4. Business Value Guidelines

- **Document Impact**: Every test should have clear business justification
- **Track Revenue Protection**: Quantify revenue at risk
- **Monitor SLAs**: Ensure tests enforce business-critical SLAs
- **Report Results**: Regular business stakeholder reporting

## Support and Troubleshooting

### Getting Help

1. **Documentation**: Check this guide and related docs in `docs/testing/`
2. **Test Information**: Run `python run_agent_startup_tests.py --info`
3. **Health Checks**: Use `python scripts/test_system_health.py`
4. **Performance Analysis**: Use `python scripts/analyze_test_performance.py`

### Common Commands Reference

```bash
# Quick development test
python run_agent_startup_tests.py

# Full validation
python run_agent_startup_tests.py --real-llm

# Test information
python run_agent_startup_tests.py --info

# Main test runner integration
python test_runner.py --level agent-startup --real-llm

# Performance profiling
python test_runner.py --level agent-startup --real-llm --profile

# System health check
python scripts/test_system_health.py --agent-startup
```

---

## Conclusion

Agent startup E2E tests are business-critical components protecting the entire Netra Apex revenue stream. This guide provides comprehensive coverage of test execution, troubleshooting, and integration with the broader testing infrastructure.

For questions or issues, refer to the troubleshooting section or run the built-in help commands. Regular execution of these tests ensures reliable agent startup across all customer segments and scenarios.

**Remember**: These tests protect $200K+ MRR - treat them as mission-critical infrastructure.