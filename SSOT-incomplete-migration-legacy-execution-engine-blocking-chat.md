# SSOT Chat Migration Issue - Issue #802

**GitHub Issue**: https://github.com/netra-systems/netra-apex/issues/802
**Priority**: P1 - High Impact Chat SSOT Violation
**Status**: In Progress

## Problem Summary
Issue #565 Legacy ExecutionEngine migration is incomplete, maintaining compatibility bridges that block optimal chat functionality and Golden Path reliability.

## Golden Path Impact
This directly affects the core Golden Path (users login → get AI responses) by causing:
- **Chat Response Delays**: Legacy execution engine patterns cause slower agent initialization
- **WebSocket Event Inconsistencies**: Mixed execution patterns cause incomplete event emission (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- **User Isolation Risks**: Legacy signature bypasses modern user context isolation patterns
- **Real-Time Chat Degradation**: Compatibility bridges introduce latency in AI response generation

## Files Affected
- `netra_backend/app/agents/supervisor/user_execution_engine.py:345-376` (compatibility bridge)
- `netra_backend/app/agents/supervisor/user_execution_engine.py:495-540` (legacy detection)
- `netra_backend/app/agents/execution_engine_consolidated.py:55-64` (consolidated engine)
- Multiple test files using deprecated patterns

## Evidence
```python
# ⚠️  ISSUE #565 API COMPATIBILITY BRIDGE ⚠️
# This method provides backward compatibility for the 128 deprecated imports
warnings.warn(
    "UserExecutionEngine(registry, websocket_bridge, user_context) pattern is DEPRECATED."
)
```

## Business Impact
- **$500K+ ARR Risk**: Chat functionality degradation affects core product value
- **User Experience**: Slower AI responses and inconsistent real-time updates
- **Technical Debt**: 128 deprecated imports require migration to modern patterns

## Solution Plan
Complete Issue #565 migration by:
1. Migrating remaining legacy ExecutionEngine usage to modern UserExecutionEngine patterns
2. Removing compatibility bridges after migration verification
3. Updating test infrastructure to use modern patterns
4. Ensuring consistent WebSocket event emission

## Progress Log

### Step 0: SSOT Audit - COMPLETED
- ✅ Discovered critical chat SSOT violation (Issue #565 incomplete migration)
- ✅ Created GitHub Issue #802
- ✅ Created progress tracker file
- ✅ Identified P1 priority impact on Golden Path

### Step 1: Discover and Plan Tests - IN PROGRESS
- [ ] Discover existing tests protecting against breaking changes
- [ ] Plan new SSOT tests for execution engine migration
- [ ] Follow TEST_CREATION_GUIDE.md best practices

### Next Steps
1. Discover existing tests for affected execution engine files
2. Plan SSOT-compliant test suite for migration verification
3. Execute remediation plan
4. Validate all tests pass
5. Create PR and close issue