# Staging Environment Connectivity Report
Generated: 2025-09-07 00:30:58
Environment: https://api.staging.netrasystems.ai

## Executive Summary
- **Total Tests**: 3
- **Successful**: 1
- **Success Rate**: 33.3%

## Test Results
### http_connectivity
- **Status**: ✅ PASS
- **Duration**: 0.763s
- **Health Status**: 200
- **Service Status**: healthy
- **Version**: 1.0.0

### websocket_connectivity
- **Status**: ❌ FAIL
- **Duration**: 0.747s
- **Error**: server rejected WebSocket connection: HTTP 403

### agent_request_pipeline
- **Status**: ❌ FAIL
- **Duration**: 0.717s
- **Error**: server rejected WebSocket connection: HTTP 403

## Recommendations
⚠️ **Some connectivity issues detected**
- Fix websocket_connectivity: server rejected WebSocket connection: HTTP 403
- Fix agent_request_pipeline: server rejected WebSocket connection: HTTP 403

## Next Steps
1. Run comprehensive agent execution tests with: `test_real_agent_execution_staging.py`
2. Validate WebSocket event delivery for all 5 critical events
3. Test multi-agent coordination and concurrent user isolation
4. Measure performance benchmarks and business value delivery