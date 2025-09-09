# Staging Environment Connectivity Report
Generated: 2025-09-09 16:09:13
Environment: https://api.staging.netrasystems.ai

## Executive Summary
- **Total Tests**: 3
- **Successful**: 2
- **Success Rate**: 66.7%

## Test Results
### http_connectivity
- **Status**: ✅ PASS
- **Duration**: 0.511s
- **Health Status**: 200
- **Service Status**: healthy
- **Version**: 1.0.0

### websocket_connectivity
- **Status**: ✅ PASS
- **Duration**: 0.000s
- **Connection Time**: 0.787s
- **Ping Time**: 0.000s

### agent_request_pipeline
- **Status**: ❌ FAIL
- **Duration**: 0.582s
- **Error**: received 1011 (internal error) Internal error; then sent 1011 (internal error) Internal error

## Recommendations
⚠️ **Some connectivity issues detected**
- Fix agent_request_pipeline: received 1011 (internal error) Internal error; then sent 1011 (internal error) Internal error

## Next Steps
1. Run comprehensive agent execution tests with: `test_real_agent_execution_staging.py`
2. Validate WebSocket event delivery for all 5 critical events
3. Test multi-agent coordination and concurrent user isolation
4. Measure performance benchmarks and business value delivery