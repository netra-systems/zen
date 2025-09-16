# Staging Environment Connectivity Report
Generated: 2025-09-15 18:58:34
Environment: https://api.staging.netrasystems.ai

## Executive Summary
- **Total Tests**: 3
- **Successful**: 1
- **Success Rate**: 33.3%

## Test Results
### http_connectivity
- **Status**:  PASS:  PASS
- **Duration**: 13.617s
- **Health Status**: 503

### websocket_connectivity
- **Status**:  FAIL:  FAIL
- **Duration**: 0.408s
- **Error**: server rejected WebSocket connection: HTTP 500

### agent_request_pipeline
- **Status**:  FAIL:  FAIL
- **Duration**: 0.339s
- **Error**: server rejected WebSocket connection: HTTP 500

## Recommendations
 WARNING: [U+FE0F] **Some connectivity issues detected**
- Fix websocket_connectivity: server rejected WebSocket connection: HTTP 500
- Fix agent_request_pipeline: server rejected WebSocket connection: HTTP 500

## Next Steps
1. Run comprehensive agent execution tests with: `test_real_agent_execution_staging.py`
2. Validate WebSocket event delivery for all 5 critical events
3. Test multi-agent coordination and concurrent user isolation
4. Measure performance benchmarks and business value delivery