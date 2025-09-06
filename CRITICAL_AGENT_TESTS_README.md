# 🚨 Critical Agent Tests - Enhanced Memory Management

**BUSINESS CRITICAL**: This test suite protects **$500K+ ARR** by validating the top 5 critical agent tests that are essential for core product functionality.

## Overview

The critical agent tests must run sequentially with fresh Docker containers to prevent memory exhaustion failures. Each test requires ~850MB memory during agent operations.

## Quick Start

```bash
# Run all critical tests (dry-run mode first recommended)
python scripts/run_critical_agent_tests.py --dry-run

# Run with verbose logging
python scripts/run_critical_agent_tests.py --dry-run --verbose

# Run actual tests (PRODUCTION READY)
python scripts/run_critical_agent_tests.py --verbose

# Run with custom memory limit
python scripts/run_critical_agent_tests.py --memory-limit 6 --verbose
```

## Features

✅ **Sequential Test Execution** - Prevents memory exhaustion by running tests one at a time  
✅ **Docker Isolation** - Fresh containers for each test prevent resource conflicts  
✅ **Memory Monitoring** - Pre-flight checks and continuous memory tracking  
✅ **Failure Recovery** - Automatic retry logic with detailed error reporting  
✅ **Comprehensive Reporting** - JSON reports with memory statistics and business impact analysis  
✅ **UnifiedDockerManager Integration** - Uses enhanced Docker management with Alpine optimization  

## The 5 Critical Tests

### 1. WebSocket Agent Events Suite (HIGHEST PRIORITY)
- **File**: `tests/mission_critical/test_websocket_agent_events_suite.py`
- **Business Value**: $500K+ ARR - Core Chat Functionality
- **Description**: Validates all 5 WebSocket events during agent execution
- **Memory**: ~850MB
- **Timeout**: 300s
- **Retries**: 2 (most critical)

### 2. Agent Orchestration Real LLM
- **File**: `tests/e2e/test_agent_orchestration_real_llm.py`
- **Business Value**: Core Agent Execution Engine
- **Description**: ExecutionEngine with real LLM integration and tool dispatch
- **Memory**: ~900MB
- **Timeout**: 600s
- **Retries**: 1

### 3. Agent WebSocket Events Comprehensive
- **File**: `tests/e2e/test_agent_websocket_events_comprehensive.py`
- **Business Value**: Complete Event Flow Coverage
- **Description**: Full agent lifecycle and complex event sequences
- **Memory**: ~850MB
- **Timeout**: 400s
- **Retries**: 1

### 4. Agent Message Flow Implementation
- **File**: `tests/e2e/test_agent_message_flow_implementation.py`
- **Business Value**: End-to-End User Chat Flow
- **Description**: Complete message processing and streaming pipeline
- **Memory**: ~800MB
- **Timeout**: 400s
- **Retries**: 1

### 5. Agent Write-Review-Refine Integration
- **File**: `tests/e2e/test_agent_write_review_refine_integration_core.py`
- **Business Value**: Multi-Agent Collaboration
- **Description**: Complex agent workflow and state management
- **Memory**: ~950MB
- **Timeout**: 500s
- **Retries**: 1

## Memory Requirements

- **Minimum System Memory**: 8GB available
- **Recommended**: 12GB+ available
- **Peak Usage per Test**: ~850-950MB
- **Docker Overhead**: ~2GB for all services
- **Safety Buffer**: 1GB additional

## Command Line Options

```bash
--dry-run           # Show what would run without executing (RECOMMENDED FIRST)
--skip-cleanup      # Skip Docker cleanup (for debugging)
--memory-limit N    # Set memory threshold in GB (default: 8.0)
--verbose, -v       # Enable detailed logging
```

## Memory Pre-flight Checks

The system performs comprehensive memory validation:

1. **Available Memory Check**: Ensures minimum memory threshold is met
2. **MemoryGuardian Integration**: Advanced memory analysis for Docker workloads
3. **Per-Test Memory Verification**: Checks memory before each individual test
4. **High Memory Detection**: Automatic cleanup when memory usage exceeds 90%

## Execution Flow

1. **Pre-flight Check**: Validates system has sufficient memory
2. **Initial Cleanup**: Removes any existing Docker resources
3. **Sequential Test Execution**:
   - Start fresh Docker environment with Alpine containers
   - Run single test with monitoring
   - Capture detailed results and memory usage
   - Stop and cleanup Docker environment
   - Pause between tests to allow system recovery
4. **Retry Logic**: Failed tests are retried with extended cleanup
5. **Final Reporting**: Comprehensive JSON report with business impact analysis

## Output Reports

Reports are automatically saved to `/reports/` directory:

```json
{
  "execution_summary": {
    "timestamp": "2025-09-05T15:29:42",
    "total_tests": 5,
    "passed": 5,
    "failed": 0,
    "success_rate": 100.0,
    "total_execution_time_seconds": 1847.3
  },
  "memory_analysis": {
    "peak_usage_mb": 18500,
    "total_memory_delta_mb": 234,
    "average_test_memory_mb": 867
  },
  "business_impact": {
    "critical_failures": [],
    "arr_at_risk": "$0 ARR"
  }
}
```

## Troubleshooting

### Memory Issues
```bash
# Check current memory usage
free -h

# Run with lower threshold
python scripts/run_critical_agent_tests.py --memory-limit 6

# Skip cleanup for debugging
python scripts/run_critical_agent_tests.py --skip-cleanup
```

### Docker Issues
```bash
# Manual cleanup before running
docker system prune -f
docker volume prune -f

# Check Docker resource usage
docker system df
```

### Test Failures
```bash
# Run with maximum verbosity
python scripts/run_critical_agent_tests.py --verbose

# Check individual test files exist
ls -la tests/mission_critical/test_websocket_agent_events_suite.py
ls -la tests/e2e/test_agent_orchestration_real_llm.py
```

## Integration with CI/CD

This test suite is designed for:

1. **Local Development**: Validate critical functionality before commits
2. **Pre-deployment**: Ensure core agent tests pass before releases
3. **Staging Validation**: Verify agent functionality in staging environment
4. **Production Readiness**: Final validation before production deployment

## Business Impact

When all 5 tests pass:
✅ **$500K+ ARR Protected** - Core functionality validated  
✅ **User Chat Works** - WebSocket events and message flow confirmed  
✅ **Agent Execution Reliable** - LLM integration and orchestration verified  
✅ **Multi-Agent Workflows** - Complex agent collaboration functional  

When tests fail:
❌ **$500K+ ARR at Risk** - Core functionality compromised  
❌ **User Experience Degraded** - Chat or agent execution issues  
❌ **Revenue Impact** - Potential customer churn or subscription cancellations  

## Support

For issues or questions:
1. Check verbose logs with `--verbose` flag
2. Review JSON reports in `/reports/` directory
3. Verify memory and Docker resources
4. Run dry-run mode first to validate setup