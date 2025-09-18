# Staging Environment Connectivity Report
Generated: 2025-09-17 23:17:10
Environment: https://staging.netrasystems.ai

## Executive Summary
- **Total Tests**: 3
- **Successful**: 1
- **Success Rate**: 33.3%

## Test Results
### http_connectivity
- **Status**:  PASS:  PASS
- **Duration**: 2.381s
- **Health Status**: 200
- **Service Status**: degraded
- **Version**: 1.0.0

### websocket_connectivity
- **Status**:  FAIL:  FAIL
- **Duration**: 10.010s
- **Error**: 

### agent_request_pipeline
- **Status**:  FAIL:  FAIL
- **Duration**: 10.009s
- **Error**: 

## Recommendations
 WARNING: [U+FE0F] **Some connectivity issues detected**
- Fix websocket_connectivity: 
- Fix agent_request_pipeline: 

## Next Steps
1. Run comprehensive agent execution tests with: `test_real_agent_execution_staging.py`
2. Validate WebSocket event delivery for all 5 critical events
3. Test multi-agent coordination and concurrent user isolation
4. Measure performance benchmarks and business value delivery