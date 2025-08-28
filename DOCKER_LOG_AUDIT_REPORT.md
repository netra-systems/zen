# Docker E2E Test Audit Report
## Generated: 2025-08-28

## Executive Summary
The netra-assistant is experiencing significant performance issues with processing times exceeding 27.5 seconds, causing WebSocket timeouts and test failures. The primary bottleneck appears to be in the ReportingSubAgent and ActionsToMeetGoalsSubAgent processing.

## Key Issues Identified

### 1. Critical Performance Issue: ReportingSubAgent Timeout
- **Status**: CRITICAL ⚠️
- **Issue**: ReportingSubAgent taking 27.5+ seconds for processing
- **Impact**: 
  - WebSocket heartbeat timeouts
  - Connection drops after ~30 seconds
  - E2E test failures due to timeout
- **Evidence**: 
  ```
  elapsed_time_seconds: 27.5, status: "processing"
  WebSocket heartbeat timeout warnings
  WebSocket disconnect with code 1011
  ```

### 2. Circuit Breaker Tripping
- **Status**: ERROR
- **Issue**: Circuit breaker 'llm_fallback_triage' transitioning to OPEN state
- **Impact**: LLM fallback mechanism activated due to repeated failures
- **Threshold**: 3 failures trigger circuit breaker

### 3. Agent Registration Loops
- **Status**: WARNING
- **Issue**: Agents being re-registered repeatedly every ~30 seconds
- **Pattern**: triage, data, optimization, actions, reporting, synthetic_data, corpus_admin
- **Possible Cause**: Connection resets triggering re-initialization

### 4. Test Execution Status
- **Total Categories Attempted**: 6
- **Failed**: database, unit, frontend (all failed in Phase 1)
- **Skipped**: api, integration, e2e (due to fast-fail mode)
- **Duration**: 50.69 seconds before failure

## Service Health Status
| Service | Status | Issue |
|---------|--------|-------|
| netra-backend | ✅ Healthy | Performance issues |
| netra-clickhouse | ✅ Healthy | - |
| netra-auth | ✅ Healthy | - |
| netra-postgres | ✅ Healthy | - |
| netra-frontend | ✅ Healthy | - |
| netra-redis | ✅ Healthy | - |

## Root Cause Analysis

### Primary Bottleneck: LLM Processing Time
The ReportingSubAgent and ActionsToMeetGoalsSubAgent are taking excessive time (25-30 seconds) to complete their LLM calls. This exceeds:
- WebSocket heartbeat timeout (appears to be ~30 seconds)
- Circuit breaker timeout threshold (10 seconds based on config)
- Expected response time for user interactions

### Contributing Factors:
1. **No response streaming**: Agents appear to wait for complete LLM responses
2. **Sequential processing**: Multiple agents running in sequence compound delays
3. **No timeout controls**: Missing timeout limits on LLM calls
4. **Heartbeat interval mismatch**: WebSocket heartbeat interval may be too short for LLM operations

## Recommendations

### Immediate Actions (P0)
1. **Implement LLM timeout controls**
   - Add 15-second timeout for individual LLM calls
   - Implement graceful degradation for timeout scenarios
   
2. **Enable response streaming**
   - Stream partial responses to maintain connection
   - Send heartbeat signals during long operations

3. **Adjust WebSocket heartbeat**
   - Increase heartbeat timeout to 60 seconds
   - Send keepalive messages during LLM processing

### Short-term Fixes (P1)
1. **Optimize Agent Processing**
   - Parallelize independent agent operations
   - Cache frequently used LLM responses
   - Implement request batching where possible

2. **Circuit Breaker Tuning**
   - Increase timeout threshold to 20 seconds for LLM operations
   - Implement graduated timeouts based on operation type

3. **Add Monitoring**
   - Track P95 response times per agent
   - Alert on operations exceeding 10 seconds
   - Log detailed timing breakdowns

### Long-term Improvements (P2)
1. **Architecture Review**
   - Consider async job queue for long-running operations
   - Implement WebSocket reconnection logic
   - Add progress indicators for multi-step operations

2. **LLM Optimization**
   - Use smaller/faster models for simple operations
   - Implement prompt optimization to reduce token count
   - Add result caching layer

## Test Environment Recommendations
For running E2E tests with Docker:
1. Increase test timeouts to 60 seconds
2. Add retry logic for WebSocket connections
3. Implement health checks before test execution
4. Use mock LLM responses for deterministic testing

## Monitoring Metrics to Track
- Agent processing time (P50, P95, P99)
- WebSocket connection duration
- Circuit breaker state transitions
- LLM API response times
- Memory usage during agent operations

## Next Steps
1. Implement timeout controls in LLM client
2. Add WebSocket keepalive during long operations  
3. Create performance test suite for agent operations
4. Set up monitoring dashboard for agent metrics
5. Document expected response times per agent type