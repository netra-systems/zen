# Staging Environment Connectivity Report
Generated: 2025-09-14 23:45:01
Environment: https://api.staging.netrasystems.ai

## Executive Summary
- **Total Tests**: 3
- **Successful**: 2
- **Success Rate**: 66.7%

## Test Results
### http_connectivity
- **Status**:  PASS:  PASS
- **Duration**: 0.539s
- **Health Status**: 200
- **Service Status**: healthy
- **Version**: 1.0.0

### websocket_connectivity
- **Status**:  FAIL:  FAIL
- **Duration**: 1.141s
- **Error**: received 1011 (internal error) main mode error; then sent 1011 (internal error) main mode error

### agent_request_pipeline
- **Status**:  PASS:  PASS
- **Duration**: 1.141s
- **Pipeline Working**: True
- **Response Type**: error_message

## Recommendations
 WARNING: [U+FE0F] **Some connectivity issues detected**
- Fix websocket_connectivity: received 1011 (internal error) main mode error; then sent 1011 (internal error) main mode error

## Next Steps
1. Run comprehensive agent execution tests with: `test_real_agent_execution_staging.py`
2. Validate WebSocket event delivery for all 5 critical events
3. Test multi-agent coordination and concurrent user isolation
4. Measure performance benchmarks and business value delivery