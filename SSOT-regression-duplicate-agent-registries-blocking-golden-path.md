# SSOT-regression-duplicate-agent-registries-blocking-golden-path

## 🚨 CRITICAL SSOT VIOLATION: Duplicate Agent Registries Blocking Golden Path

**STATUS:** In Progress - SSOT Gardener Session  
**Impact:** BLOCKING GOLDEN PATH - User login → AI responses broken  
**Revenue at Risk:** $500K+ ARR from chat functionality  
**Priority:** P0 - Immediate action required  
**Issue Created:** 2025-09-14  

### Root Cause: Competing Agent Registry Implementations

#### Violation Details:
- **Two competing agent registries** with overlapping functionality
- `/netra_backend/app/agents/registry.py` (DEPRECATED) - compatibility wrapper
- `/netra_backend/app/agents/supervisor/agent_registry.py` (ENHANCED) - proper isolation
- **Both registries create different agent instances, causing context confusion**

#### Golden Path Impact:
- Users can't get reliable AI responses due to inconsistent agent creation
- WebSocket events sent to wrong user sessions  
- Memory leaks in multi-user scenarios
- User context isolation completely broken

#### Evidence:
```python
# Legacy registry (agents/registry.py:405)
agent_registry = AgentRegistry()  # Global instance

# Enhanced registry (agents/supervisor/agent_registry.py:286)  
class AgentRegistry(BaseAgentRegistry):  # Different inheritance chain
```

### Related SSOT Violations Discovered:
1. **Duplicate Message Handlers** - `websocket/message_handler.py` vs `message_handlers.py`
2. **Factory Pattern Bypass** - Direct agent instantiation without proper isolation

### Remediation Plan:
1. Consolidate to single SSOT agent registry
2. Remove deprecated registry implementation  
3. Update all imports to use enhanced registry
4. Validate user isolation patterns
5. Run comprehensive test suite

## WORK LOG:

### Step 0: SSOT Audit Complete ✅
- Discovered 3 critical SSOT violations in agent/goldenpath/messages domain
- Prioritized agent registry consolidation as highest impact
- Created issue tracking and local progress file

### Next Steps:
1. Discover and plan tests for SSOT violations
2. Execute test plan for validation
3. Plan and execute remediation
4. Test fix loop until system stable
5. Create PR and close issue

**Documentation References:** 
- @SSOT_IMPORT_REGISTRY.md 
- @USER_CONTEXT_ARCHITECTURE.md
- @GOLDEN_PATH_USER_FLOW_COMPLETE.md

**Related Issues:** This blocks Issue #420 Docker infrastructure and golden path validation.