# Agent Startup E2E Test Runner

Comprehensive test runner for agent initialization and startup validation across all customer segments.

## Business Value Justification (BVJ)
- **Segment**: ALL customer segments (Free, Early, Mid, Enterprise)
- **Business Goal**: Ensure 100% reliable agent startup across all scenarios  
- **Value Impact**: Prevents agent initialization failures blocking user interactions
- **Revenue Impact**: Protects entire $200K+ MRR by ensuring reliable startup process

## Quick Start

### Simple Commands (Recommended)

```bash
# Quick validation with mocks (development)
python run_agent_startup_tests.py

# Full validation with real LLM (releases)
python run_agent_startup_tests.py --real-llm

# Safe sequential execution
python run_agent_startup_tests.py --real-llm --sequential

# Show test information
python run_agent_startup_tests.py --info
```

### Integration with Main Test Runner

```bash
# Use the main test framework for full integration
python test_runner.py --level agent-startup --real-llm

# Integration with other test levels
python test_runner.py --level integration --real-llm  # Includes agent startup
```

## Test Categories

| Category | Description | Real LLM | Timeout |
|----------|-------------|----------|---------|
| cold_start | Agent cold start from zero state | Required | 30s |
| concurrent_startup | Concurrent agent startup isolation | Required | 45s |
| tier_startup | Startup across different user tiers | Required | 60s |
| agent_isolation | Agent state isolation validation | Optional | 30s |
| routing_startup | Message routing during startup | Optional | 25s |
| performance_startup | Performance metrics under startup load | Required | 40s |

## Features

### Performance Baseline Tracking
- Tracks startup times against established baselines
- Generates performance reports with SLA compliance
- Identifies performance regressions automatically

### Real LLM Testing Support
- `--real-llm` flag enables actual LLM API calls
- Configurable LLM model and timeout settings
- Cost-aware testing with gemini-2.5-flash default

### Parallel Execution
- Safe parallel execution where appropriate
- Automatic detection of parallel-safe vs sequential tests
- `--sequential` flag for conservative execution

### Comprehensive Reporting
- JSON reports with detailed metrics
- Performance baseline comparisons
- Business impact analysis
- Actionable recommendations

## Test Scenarios

### Complete Cold Start Test
Tests complete system initialization from zero state through first meaningful agent interaction.

**Validates:**
- Auth service initialization
- WebSocket connection establishment
- Agent system startup
- First message routing and response
- Performance requirements (< 5 seconds)

### Concurrent User Isolation
Tests multiple concurrent users with complete session isolation.

**Validates:**
- No state cross-contamination
- Correct message routing under load
- Isolation of sensitive data
- Performance under concurrent load

### User Tier Validation
Tests startup behavior across all customer tiers (Free, Early, Mid, Enterprise).

**Validates:**
- Tier-specific configurations
- Permission-based routing
- Performance consistency across tiers

## Performance Baselines

| Metric | Baseline | Warning | Critical |
|--------|----------|---------|----------|
| Cold Start Time | < 5s | 8s | 12s |
| Concurrent Startup | < 8s | 12s | 20s |
| Memory Usage | < 512MB | 1GB | 2GB |
| Success Rate | > 99% | 95% | 90% |

## Integration Points

### With test_runner.py
The agent startup tests integrate seamlessly with the main test runner:

```bash
# Available test levels that include agent startup
python test_runner.py --level agent-startup    # Agent startup only
python test_runner.py --level integration      # Includes agent startup
python test_runner.py --level comprehensive    # Full suite
```

### With CI/CD Pipeline
The tests support CI/CD integration through:

- Exit codes (0 = pass, 1 = fail, 130 = interrupted)
- JSON report output for parsing
- Timeout controls for build time limits
- Parallel execution for faster CI runs

### With Performance Monitoring
Integrates with performance baseline tracking:

```python
from app.tests.performance.performance_baseline_config import get_benchmark_runner

runner = get_benchmark_runner()
# Performance metrics are automatically recorded
```

## File Structure

```
tests/unified/
├── run_agent_startup_tests.py          # Main test runner
├── agent_startup_integration.py        # Integration layer
├── test_agent_cold_start.py           # Cold start tests
└── test_concurrent_agents.py          # Concurrent agent tests

run_agent_startup_tests.py              # Simple CLI wrapper
```

## Troubleshooting

### Common Issues

**Tests timing out:**
```bash
python run_agent_startup_tests.py --timeout 600  # Increase timeout
```

**LLM API errors:**
```bash
# Check environment variables
echo $GOOGLE_API_KEY
echo $ENABLE_REAL_LLM_TESTING
```

**Parallel execution issues:**
```bash
python run_agent_startup_tests.py --sequential  # Force sequential
```

### Debug Mode

```bash
# Run individual test categories
python -m pytest tests/unified/test_agent_cold_start.py::test_complete_agent_cold_start -v

# Run with detailed output  
python run_agent_startup_tests.py --real-llm --sequential
```

## Development

### Adding New Test Categories

1. Add test config to `StartupTestConfig` in `run_agent_startup_tests.py`
2. Implement test in appropriate test module
3. Update performance baselines if needed
4. Add documentation to this file

### Performance Baselines

Update baselines in `app/tests/performance/performance_baseline_config.py`:

```python
metrics['agent_startup_time'] = PerformanceMetric(
    name='Agent Startup Time',
    baseline_value=5.0,  # 5 seconds
    warning_threshold=8.0,
    critical_threshold=12.0
)
```

## Business Impact

These tests directly protect revenue by ensuring:

1. **Zero Downtime Startups**: Prevents initialization failures that block customer interactions
2. **Performance SLA Compliance**: Maintains < 5 second startup times per enterprise contracts  
3. **Multi-Tenant Security**: Validates isolation between customer sessions
4. **Scalability Validation**: Ensures system handles concurrent user growth

**Revenue Protection**: $200K+ MRR protected by preventing startup failures that would block all customer usage.