# Staging Environment Connectivity Report
<<<<<<< HEAD
Generated: 2025-09-15 22:49:21
=======
<<<<<<< HEAD
Generated: 2025-09-15 22:48:26
=======
Generated: 2025-09-15 23:17:02
>>>>>>> 676d97d9a0cae0ef51f70704c13a477b77a305a7
>>>>>>> 05c6be3dfb1dc6976637367390a12e4d2c3f76d2
Environment: https://api.staging.netrasystems.ai

## Executive Summary
- **Total Tests**: 3
- **Successful**: 1
- **Success Rate**: 33.3%

## Test Results
### http_connectivity
- **Status**:  PASS:  PASS
<<<<<<< HEAD
- **Duration**: 12.562s
=======
<<<<<<< HEAD
- **Duration**: 12.859s
=======
- **Duration**: 8.813s
>>>>>>> 676d97d9a0cae0ef51f70704c13a477b77a305a7
>>>>>>> 05c6be3dfb1dc6976637367390a12e4d2c3f76d2
- **Health Status**: 503

### websocket_connectivity
- **Status**:  FAIL:  FAIL
<<<<<<< HEAD
- **Duration**: 6.076s
=======
<<<<<<< HEAD
- **Duration**: 6.464s
=======
- **Duration**: 1.686s
>>>>>>> 676d97d9a0cae0ef51f70704c13a477b77a305a7
>>>>>>> 05c6be3dfb1dc6976637367390a12e4d2c3f76d2
- **Error**: server rejected WebSocket connection: HTTP 503

### agent_request_pipeline
- **Status**:  FAIL:  FAIL
<<<<<<< HEAD
- **Duration**: 7.370s
=======
<<<<<<< HEAD
- **Duration**: 6.312s
=======
- **Duration**: 5.875s
>>>>>>> 676d97d9a0cae0ef51f70704c13a477b77a305a7
>>>>>>> 05c6be3dfb1dc6976637367390a12e4d2c3f76d2
- **Error**: server rejected WebSocket connection: HTTP 503

## Recommendations
 WARNING: [U+FE0F] **Some connectivity issues detected**
- Fix websocket_connectivity: server rejected WebSocket connection: HTTP 503
- Fix agent_request_pipeline: server rejected WebSocket connection: HTTP 503

## Next Steps
1. Run comprehensive agent execution tests with: `test_real_agent_execution_staging.py`
2. Validate WebSocket event delivery for all 5 critical events
3. Test multi-agent coordination and concurrent user isolation
4. Measure performance benchmarks and business value delivery