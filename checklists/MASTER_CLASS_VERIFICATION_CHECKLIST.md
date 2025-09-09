# Master Class Verification Checklist

## Ultra-Critical Classes - Must Check ALWAYS

### 1. WebSocket Core Classes
- [ ] **AgentWebSocketBridge** (`netra_backend/app/services/agent_websocket_bridge.py`)
  - [ ] ensure_integration() is idempotent
  - [ ] Health monitoring active
  - [ ] Fallback paths exist
  - [ ] All 5 critical events sent: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
  
- [ ] **WebSocketManager** (`netra_backend/app/websocket/connection_manager.py`)
  - [ ] Connection tracking correct
  - [ ] User isolation maintained
  - [ ] Broadcast scoped to user_id
  - [ ] No shared state between users
  
- [ ] **UnifiedManager** (`netra_backend/app/websocket_core/unified_manager.py`)
  - [ ] Singleton pattern correct
  - [ ] Thread-safe initialization
  - [ ] Graceful shutdown implemented

### 2. Agent Execution Classes
- [ ] **AgentRegistry** (`netra_backend/app/agents/supervisor/agent_registry.py`)
  - [ ] set_websocket_manager() enhances dispatcher
  - [ ] All agents registered correctly
  - [ ] Factory pattern used for instances
  
- [ ] **ExecutionEngine** (`netra_backend/app/agents/supervisor/execution_engine_factory.py`)
  - [ ] AgentWebSocketBridge initialized
  - [ ] User context properly isolated
  - [ ] No cross-user contamination
  
- [ ] **EnhancedToolExecutionEngine** 
  - [ ] Wraps tool execution with notifications
  - [ ] Sends tool_executing before execution
  - [ ] Sends tool_completed after execution

### 3. Configuration Classes
- [ ] **UnifiedConfigurationManager** (`netra_backend/app/core/managers/unified_configuration_manager.py`)
  - [ ] Environment-specific configs separated
  - [ ] No config leakage between environments
  - [ ] SERVICE_ID = "netra-backend" (stable, no timestamps)
  
- [ ] **IsolatedEnvironment** (`shared/isolated_environment.py`)
  - [ ] All env access goes through this
  - [ ] No direct os.environ access
  - [ ] Service-specific isolation maintained

### 4. Authentication Classes
- [ ] **OAuthManager** (`auth_service/auth_core/oauth_manager.py`)
  - [ ] Environment-specific credentials
  - [ ] No credential sharing between environments
  - [ ] Silent failures prevented
  
- [ ] **JWTSecretManager** (`shared/jwt_secret_manager.py`)
  - [ ] Shared secret handling
  - [ ] Cross-service authentication works
  - [ ] Token validation consistent

### 5. Database/Redis Classes
- [ ] **DatabaseManager** (`netra_backend/app/db/database_manager.py`)
  - [ ] Connection pooling correct
  - [ ] Transaction boundaries clear
  - [ ] Session scoping per request
  
- [ ] **RedisManager** (`netra_backend/app/db/redis_manager.py`)
  - [ ] Connection pooling
  - [ ] Key namespacing correct
  - [ ] TTL management consistent

### 6. Factory Classes
- [ ] **AgentInstanceFactory** (`netra_backend/app/agents/supervisor/agent_instance_factory.py`)
  - [ ] Creates isolated instances per request
  - [ ] No shared state between instances
  - [ ] User context properly injected
  
- [ ] **ExecutionFactory** (`netra_backend/app/agents/supervisor/execution_factory.py`)
  - [ ] Request-scoped executors
  - [ ] WebSocket integration automatic
  - [ ] Proper cleanup on completion

### 7. Manager Classes
- [ ] **UnifiedLifecycleManager** (`netra_backend/app/core/managers/unified_lifecycle_manager.py`)
  - [ ] Startup sequence correct
  - [ ] Shutdown graceful
  - [ ] Resource cleanup complete
  
- [ ] **UnifiedStateManager** (`netra_backend/app/core/managers/unified_state_manager.py`)
  - [ ] State transitions atomic
  - [ ] No race conditions
  - [ ] Recovery mechanisms in place

## Per-Module Verification

### When Modifying WebSocket Module
1. Check WebSocket event flow
2. Verify user isolation
3. Test with multiple concurrent users
4. Run `python tests/mission_critical/test_websocket_agent_events_suite.py`

### When Modifying Agent Module
1. Check AgentRegistry registration
2. Verify WebSocket integration
3. Test agent_started and agent_completed events
4. Check execution order (Data → Optimization → etc.)

### When Modifying Configuration
1. Check MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
2. Verify environment separation
3. Test with each environment (dev/staging/prod)
4. Check for hardcoded values

### When Modifying Authentication
1. Check OAuth credentials per environment
2. Verify JWT secret consistency
3. Test multi-user scenarios
4. Check for credential leakage

## Critical Invariants to Maintain

1. **User Isolation**: No shared state between users
2. **Environment Separation**: Configs never leak between environments
3. **WebSocket Events**: All 5 critical events must be sent
4. **Service Independence**: Services communicate only through defined interfaces
5. **Factory Pattern**: All user-specific instances created through factories
6. **SSOT Compliance**: One canonical implementation per concept per service
7. **Error Visibility**: All errors must be loud and visible
8. **Test Reality**: E2E tests use real services, real auth, real LLMs

## Red Flags - Stop and Investigate

- [ ] Direct os.environ access outside configuration classes
- [ ] Shared state in singleton classes
- [ ] Missing WebSocket events in agent execution
- [ ] Cross-service imports (except from /shared)
- [ ] Mocked services in E2E tests
- [ ] Hardcoded URLs or credentials
- [ ] Non-idempotent initialization
- [ ] Silent error suppression
- [ ] Test execution time = 0.00s
- [ ] SERVICE_ID with timestamps