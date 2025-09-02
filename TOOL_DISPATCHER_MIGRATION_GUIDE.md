# ToolDispatcher Security Migration Guide

## 🚨 CRITICAL SECURITY ISSUE: Global ToolDispatcher Patterns

This guide addresses **critical security vulnerabilities** in the current ToolDispatcher implementation that create user isolation issues and potential data leaks.

## 📋 Migration Timeline

- **Current Version**: v2.0.x - Deprecation warnings added
- **Version 2.1.0**: Global state methods will show deprecation warnings  
- **Version 3.0.0**: Global state methods will be **REMOVED** (Q2 2025)

## ⚠️ Security Risks with Global Patterns

### Current Unsafe Patterns

```python
# 🚨 UNSAFE - Global state risks
dispatcher = ToolDispatcher(tools, websocket_bridge)
result = await dispatcher.dispatch("my_tool", param="value")

# 🚨 UNSAFE - Shared between all users  
agent = MyAgent(llm_manager, tool_dispatcher=global_dispatcher)

# 🚨 UNSAFE - No user isolation
def create_global_dispatcher():
    return ToolDispatcher(get_global_tools())
```

### Security Vulnerabilities

1. **User Data Leaks**: Tool results may be delivered to wrong users
2. **WebSocket Event Misrouting**: Real-time events sent to incorrect sessions  
3. **Privilege Escalation**: Tools registered for one user become available to all
4. **Memory Corruption**: Shared state in high-concurrency scenarios
5. **Resource Leaks**: No automatic cleanup of user-specific resources

## ✅ Secure Migration Patterns

### 1. Request-Scoped Dispatcher Factory

```python
# ✅ SECURE - Per-request isolation
async def handle_request(user_context: UserExecutionContext):
    dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
        user_context=user_context,
        tools=get_user_specific_tools(user_context.user_id),
        websocket_manager=websocket_manager
    )
    result = await dispatcher.dispatch("my_tool", param="value")
    return result
```

### 2. Async Context Manager Pattern  

```python
# ✅ SECURE - Automatic cleanup guaranteed
async def handle_request(user_context: UserExecutionContext):
    async with ToolDispatcher.create_scoped_dispatcher_context(
        user_context=user_context,
        tools=user_tools,
        websocket_manager=websocket_manager
    ) as dispatcher:
        # All operations are user-scoped and secure
        result = await dispatcher.dispatch("my_tool", param="value")
        tool_result = await dispatcher.dispatch_tool("other_tool", params, state, run_id)
        # Automatic cleanup happens here - no memory leaks
        return result
```

### 3. Agent Factory Pattern

```python
# ✅ SECURE - Agent with isolated dispatcher
async def create_agent_with_context(
    user_context: UserExecutionContext,
    agent_class: Type[BaseAgent]
) -> BaseAgent:
    """Create agent with request-scoped tool dispatcher."""
    
    # Create isolated dispatcher for this user
    dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
        user_context=user_context,
        tools=get_user_tools(user_context.user_id),
        websocket_manager=get_websocket_manager()
    )
    
    # Create agent with isolated resources
    agent = agent_class(
        llm_manager=get_llm_manager(),
        name=f"{agent_class.__name__}_{user_context.user_id}",
        # No global tool_dispatcher parameter
    )
    
    # Set isolated dispatcher
    agent.tool_dispatcher = dispatcher
    return agent
```

## 📝 Step-by-Step Migration Process

### Step 1: Audit Current Usage

Run the security detection utility:

```python
# Detect unsafe patterns in your code
security_analysis = ToolDispatcher.detect_unsafe_usage_patterns()
if security_analysis['has_unsafe_patterns']:
    print("Found unsafe patterns:", security_analysis['risks'])
    print("Migration steps:", security_analysis['migration_recommendations'])
```

### Step 2: Replace Global Instantiation

```python
# BEFORE (unsafe)
dispatcher = ToolDispatcher(tools, websocket_bridge)

# AFTER (secure)  
async def create_secure_dispatcher(user_context):
    return await ToolDispatcher.create_request_scoped_dispatcher(
        user_context=user_context,
        tools=tools,
        websocket_manager=websocket_manager
    )
```

### Step 3: Update Agent Constructors

```python
# BEFORE (unsafe)
class MyAgent(BaseAgent):
    def __init__(self, llm_manager, tool_dispatcher):
        super().__init__(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher  # Global state risk
        )

# AFTER (secure)
class MyAgent(BaseAgent):  
    def __init__(self, llm_manager):
        super().__init__(
            llm_manager=llm_manager,
            # No tool_dispatcher parameter - will be set later
        )
    
    async def initialize_with_context(self, user_context: UserExecutionContext):
        """Initialize agent with user-scoped dispatcher."""
        self.tool_dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            tools=self.get_required_tools(),
            websocket_manager=get_websocket_manager()
        )
```

### Step 4: Update Request Handlers

```python
# BEFORE (unsafe)
@router.post("/agent/execute")
async def execute_agent(request: RequestModel):
    agent = create_global_agent()  # Uses global dispatcher
    result = await agent.execute(request.message)
    return result

# AFTER (secure)
@router.post("/agent/execute")
async def execute_agent(
    request: RequestModel,
    user_context: UserExecutionContext = Depends(get_request_scoped_user_context)
):
    async with ToolDispatcher.create_scoped_dispatcher_context(
        user_context=user_context
    ) as dispatcher:
        agent = await create_agent_with_context(user_context, MyAgent)
        agent.tool_dispatcher = dispatcher
        result = await agent.execute(user_context)
        return result
```

### Step 5: Remove Global State from Startup

```python
# BEFORE (unsafe startup pattern)
def setup_global_tools(app: FastAPI):
    app.state.tool_dispatcher = ToolDispatcher(get_global_tools())

# AFTER (secure - remove global dispatcher)  
def setup_app_dependencies(app: FastAPI):
    # Remove global tool dispatcher
    # Use request-scoped factory instead
    pass
```

## 🔍 Security Validation

### Runtime Security Checks

```python
# Check dispatcher security status
async def validate_dispatcher_security(dispatcher):
    security_check = await dispatcher.force_secure_migration_check()
    
    if security_check['security_status'] == 'UNSAFE':
        raise SecurityError(f"Unsafe dispatcher detected: {security_check['isolation_status']}")
    
    return security_check
```

### Integration Testing

```python
import pytest

async def test_user_isolation():
    """Test that different users get isolated dispatchers."""
    user1_context = create_user_context("user1")
    user2_context = create_user_context("user2")
    
    async with ToolDispatcher.create_scoped_dispatcher_context(user1_context) as d1:
        async with ToolDispatcher.create_scoped_dispatcher_context(user2_context) as d2:
            # Register user-specific tools
            d1.register_tool("user_tool", lambda: f"user1_data")
            d2.register_tool("user_tool", lambda: f"user2_data")
            
            # Verify isolation
            result1 = await d1.dispatch("user_tool")
            result2 = await d2.dispatch("user_tool")
            
            assert result1.result == "user1_data"
            assert result2.result == "user2_data"
```

## 📊 Migration Checklist

### Code Changes
- [ ] Replace `ToolDispatcher()` with factory methods
- [ ] Update agent constructors to remove `tool_dispatcher` parameter  
- [ ] Use `create_scoped_dispatcher_context()` in request handlers
- [ ] Remove global dispatcher from startup modules
- [ ] Update dependency injection patterns

### Testing
- [ ] Add user isolation tests
- [ ] Test concurrent request handling  
- [ ] Validate WebSocket event routing
- [ ] Test memory cleanup with context managers
- [ ] Performance testing with request-scoped pattern

### Security
- [ ] Run `detect_unsafe_usage_patterns()` utility
- [ ] Audit all `ToolDispatcher` instantiations  
- [ ] Verify no global tool registrations
- [ ] Test user privilege isolation
- [ ] Validate WebSocket bridge isolation

## 🚨 Common Migration Pitfalls

### 1. Forgetting Async Context
```python
# ❌ WRONG - Not using async context  
dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(user_context)
# dispatcher never gets cleaned up

# ✅ CORRECT - Using async context manager
async with ToolDispatcher.create_scoped_dispatcher_context(user_context) as dispatcher:
    # Automatic cleanup guaranteed
```

### 2. Sharing Dispatcher Between Requests
```python
# ❌ WRONG - Reusing dispatcher across requests
cached_dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(user_context)

# ✅ CORRECT - New dispatcher per request  
async def handle_request(user_context):
    async with ToolDispatcher.create_scoped_dispatcher_context(user_context) as dispatcher:
        # Fresh dispatcher per request
```

### 3. Missing User Context
```python
# ❌ WRONG - No user context provided
dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
    user_context=None  # This will fail
)

# ✅ CORRECT - Always provide valid user context
dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
    user_context=get_current_user_context()
)
```

## 📞 Support and Resources

### Documentation
- `netra_backend/app/agents/request_scoped_tool_dispatcher.py` - Reference implementation
- `netra_backend/app/agents/tool_executor_factory.py` - Factory patterns
- This migration guide - Complete migration instructions

### Debugging
- Use `ToolDispatcher.detect_unsafe_usage_patterns()` for pattern detection
- Use `dispatcher.force_secure_migration_check()` for runtime validation  
- Check deprecation warnings in logs for remaining global usage

### Getting Help
- Review existing secure implementations in `agent_route.py`
- Check test files for isolation testing patterns
- Use security validation utilities for verification

---

**Remember**: User data security is critical. Take time to properly test the migration and validate user isolation before deploying to production.