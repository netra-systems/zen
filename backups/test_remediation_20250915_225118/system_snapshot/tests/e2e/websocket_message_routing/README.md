# WebSocket Message Routing E2E Tests

## Overview

This directory contains comprehensive E2E tests for the WebSocket message routing system, specifically testing the complete golden path from user message to agent execution with all required WebSocket events.

## Business Value

- **Revenue Protection**: $500K+ ARR protection by validating core chat functionality
- **User Experience**: Ensures real-time WebSocket events provide transparency during AI processing  
- **System Reliability**: Proves end-to-end message routing and agent execution works correctly

## Test Files

### `test_websocket_message_to_agent_golden_path.py`
**Main test file containing:**
- `test_websocket_message_to_agent_complete_golden_path()` - Primary golden path validation
- `test_websocket_message_routing_failure_modes()` - Error handling scenarios
- `test_websocket_concurrent_message_handling()` - Concurrent message processing

**Key Validations:**
1. ✅ WebSocket connection with JWT authentication
2. ✅ User message routing to AgentHandler
3. ✅ Agent execution pipeline with SupervisorAgent  
4. ✅ All 5 critical WebSocket events validation:
   - `agent_started` - Agent begins processing
   - `agent_thinking` - Real-time reasoning updates
   - `tool_executing` - Tool usage transparency
   - `tool_completed` - Tool results display
   - `agent_completed` - Final response ready
5. ✅ Complete flow from GOLDEN_PATH_USER_FLOW_COMPLETE.md

### `run_golden_path_test.py` 
**Standalone test runner with:**
- Simple command-line execution
- Detailed failure analysis  
- Expected failure detection (proves system issues exist)

### `__init__.py`
**Package initialization** with documentation and usage examples.

## Expected Results

⚠️ **CRITICAL**: These tests are **EXPECTED TO FAIL INITIALLY** to prove current system issues exist.

**Initial Failure Indicators:**
- Missing WebSocket events during agent execution
- Incomplete message routing to agent pipeline
- Problems with agent execution or event notification

**After Fixes (Expected Success):**
- All 5 critical WebSocket events received in correct order
- Agent execution completes successfully
- Message routing works end-to-end
- Proper resource cleanup

## Usage

### Run with pytest (recommended)
```bash
# Run all WebSocket message routing tests
pytest tests/e2e/websocket_message_routing/ -v

# Run specific golden path test
pytest tests/e2e/websocket_message_routing/test_websocket_message_to_agent_golden_path.py::TestWebSocketMessageToAgentGoldenPath::test_websocket_message_to_agent_complete_golden_path -v

# Run with coverage  
pytest tests/e2e/websocket_message_routing/ -v --cov=netra_backend
```

### Run with standalone runner
```bash
# Run golden path test only
python tests/e2e/websocket_message_routing/run_golden_path_test.py golden

# Run failure modes test
python tests/e2e/websocket_message_routing/run_golden_path_test.py failure

# Run concurrent handling test
python tests/e2e/websocket_message_routing/run_golden_path_test.py concurrent

# Run all tests
python tests/e2e/websocket_message_routing/run_golden_path_test.py all
```

### Run with unified test runner
```bash
# Use the unified test runner for real services
python tests/unified_test_runner.py --real-services --category e2e --filter websocket_message_routing
```

## Architecture Compliance

✅ **Follows CLAUDE.md requirements:**
- Uses real services, no inappropriate mocks
- SSOT authentication via E2EWebSocketAuthHelper  
- Absolute imports only
- IsolatedEnvironment for configuration
- Proper resource cleanup
- Comprehensive error handling

✅ **Test quality standards:**
- Deterministic and reliable
- Comprehensive event validation
- Proper timing and order checks
- Edge case and failure mode testing
- Clear business value justification

## Integration Points

**Dependencies:**
- `test_framework/ssot/e2e_auth_helper.py` - SSOT authentication
- `shared/isolated_environment.py` - Configuration management
- `tests/e2e/staging_config.py` - Environment-specific settings
- WebSocket infrastructure in `/netra_backend/app/routes/websocket.py`

**Related Documentation:**
- `docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md` - Complete user flow specification
- `SPEC/learnings/websocket_agent_integration_critical.xml` - WebSocket integration patterns
- `docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md` - Agent architecture clarification

## Troubleshooting

**Common Issues:**
1. **Connection Timeout**: Check if services are running with `docker-compose up`
2. **Auth Failures**: Verify JWT_SECRET_KEY is consistent across services  
3. **Missing Events**: Check AgentRegistry.set_websocket_manager() integration
4. **Import Errors**: Ensure absolute imports and proper PYTHONPATH

**Debug Commands:**
```bash
# Check service health
curl http://localhost:8002/health
curl http://localhost:8083/health

# Validate JWT configuration
python -c "from shared.jwt_secret_manager import get_unified_jwt_secret; print('JWT OK:', bool(get_unified_jwt_secret()))"

# Check Docker services
docker-compose ps
```

## Next Steps After Initial Failure

1. **Analyze Missing Events**: Review which of the 5 critical events are missing
2. **Check Integration**: Validate AgentRegistry WebSocket manager setup  
3. **Verify Event Flow**: Ensure EnhancedToolExecutionEngine wraps tool execution
4. **Fix Root Causes**: Address WebSocket event integration issues
5. **Re-run Tests**: Validate fixes restored golden path functionality

This test suite provides comprehensive validation of the WebSocket message routing system and serves as both a diagnostic tool and a regression test for the core chat functionality.