# Staging Environment Connectivity Report
Generated: 2025-09-08 12:02:57
Environment: https://api.staging.netrasystems.ai

## Executive Summary
- **Total Tests**: 3
- **Successful**: 1
- **Success Rate**: 33.3%

## Test Results
### http_connectivity
- **Status**: ✅ PASS
- **Duration**: 0.612s
- **Health Status**: 200
- **Service Status**: healthy
- **Version**: 1.0.0

### websocket_connectivity
- **Status**: ❌ FAIL
- **Duration**: 1.125s
- **Error**: received 1011 (internal error) Internal error; then sent 1011 (internal error) Internal error

### agent_request_pipeline
- **Status**: ❌ FAIL
- **Duration**: 0.810s
- **Error**: received 1011 (internal error) Internal error; then sent 1011 (internal error) Internal error

## Recommendations
⚠️ **Some connectivity issues detected**
- Fix websocket_connectivity: received 1011 (internal error) Internal error; then sent 1011 (internal error) Internal error
- Fix agent_request_pipeline: received 1011 (internal error) Internal error; then sent 1011 (internal error) Internal error

## Next Steps
1. Run comprehensive agent execution tests with: `test_real_agent_execution_staging.py`
2. Validate WebSocket event delivery for all 5 critical events
3. Test multi-agent coordination and concurrent user isolation
4. Measure performance benchmarks and business value delivery