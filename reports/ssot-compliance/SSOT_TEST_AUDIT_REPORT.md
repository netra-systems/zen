# SSOT Test Audit Report - Critical Test Failures Analysis

## Executive Summary
Recent SSOT refactoring has introduced breaking changes that have not been propagated to test files. The tests are attempting to use deprecated patterns that have been replaced with factory-based isolation patterns.

## Git History Analysis

### Key SSOT Refactoring Commits:
1. **1dc3fed36** - Removed `agent_execution_registry.py` entirely
2. **dfa10aea3** - Removed legacy tool dispatcher and registry modules  
3. **5ef8561b0** - Consolidated core agent modules and interfaces
4. **efc26fa5b** - Added UnifiedIdManager for centralized ID generation
5. **5943e2b14** - Consolidated to single AgentInstanceFactory per SSOT

## Critical Test Failures Root Cause Analysis

### 1. Tool Dispatcher Factory Pattern ❌
**Issue:** Direct instantiation forbidden - must use factory methods
**Root Cause:** SSOT refactoring enforces factory pattern to prevent shared state

**Old Pattern (tests using):**
```python
dispatcher = ToolDispatcher()  # FORBIDDEN
```

**New SSOT Pattern (required):**
```python
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
dispatcher = UnifiedToolDispatcherFactory.create_for_request(context)
```

**Files Requiring Update:**
- `tests/smoke/test_startup_wiring_smoke.py:39`

### 2. Agent Execution Registry Module Not Found ❌
**Issue:** ModuleNotFoundError: 'netra_backend.app.orchestration.agent_execution_registry'
**Root Cause:** Module completely removed in commit 1dc3fed36

**Migration Path:**
- Old: `netra_backend.app.orchestration.agent_execution_registry.AgentExecutionRegistry`
- New: `netra_backend.app.agents.supervisor.agent_registry.AgentRegistry`

**Files Requiring Update:**
- `tests/smoke/test_startup_wiring_smoke.py:55`

### 3. LLM Manager Missing Methods ❌
**Issue:** LLMManager missing `get_llm` method
**Root Cause:** Method never existed in current implementation

**Available Methods:**
- `ask_llm(prompt, llm_config_name, use_cache)`
- `ask_llm_structured(prompt, response_model, ...)`
- `health_check()`

**Test Expectation Mismatch:**
- Test expects: `get_llm` method
- Reality: No such method exists

**Files Requiring Update:**
- `tests/smoke/test_startup_wiring_smoke.py:304-307`

### 4. KeyManager Method Signature Change ❌
**Issue:** `generate_key()` requires positional arguments
**Root Cause:** Method signature changed to require context

**Old Pattern (tests using):**
```python
KeyManager.generate_key()  # Missing required args
```

**New SSOT Pattern:**
```python
manager = KeyManager()
manager.generate_key(
    key_id="test_key",
    key_type=KeyType.ENCRYPTION_KEY,
    length=32
)
```

**Files Requiring Update:**
- `tests/smoke/test_startup_wiring_smoke.py:321`

### 5. Database Connection Issues 🔴
**Issue:** PostgreSQL not available on port 5433
**Root Cause:** Docker/Podman services not running

## Test File Update Requirements

### Priority 1 - Smoke Tests (5 failures)
```python
# test_startup_wiring_smoke.py updates needed:

# 1. Tool Dispatcher - Use factory pattern
from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory

context = UserExecutionContext(user_id="test", run_id="test_run")
dispatcher = UnifiedToolDispatcherFactory.create_for_request(context)

# 2. Agent Registry - Update import
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry

# 3. LLM Manager - Remove get_llm check
# Remove line checking for 'get_llm' method

# 4. KeyManager - Fix method call
from netra_backend.app.services.key_manager import KeyManager, KeyType
manager = KeyManager()
key = manager.generate_key("test_key", KeyType.ENCRYPTION_KEY)
```

## Architecture Compliance Issues

### Duplicate Types (103 instances)
- Frontend has 103 duplicate type definitions
- Violates SSOT principle
- Requires consolidation into shared type modules

### Unjustified Mocks (2,043 instances)
- Tests contain massive mock usage without justification
- Violates "MOCKS = ABOMINATION" principle from CLAUDE.md
- Should use real services with Docker

## Recommendations

### Immediate Actions Required:
1. **Update Smoke Tests** - Apply factory pattern fixes
2. **Fix Import Paths** - Update to new SSOT module locations
3. **Start Docker Services** - Required for integration tests
4. **Remove Method Expectations** - Align tests with actual implementations

### Medium-Term Actions:
1. **Consolidate Frontend Types** - Create shared type definitions
2. **Replace Mocks with Real Services** - Use Docker-based testing
3. **Update Test Architecture** - Align with factory-based isolation

### Testing Strategy Alignment:
Per CLAUDE.md: **Real Everything (LLM, Services) E2E > E2E > Integration > Unit**
- Current tests violate this with excessive mocking
- Should prioritize real service testing with Docker

## Affected Test Categories:
- **Smoke Tests**: 5 failures (Critical)
- **Integration Tests**: Cannot run without Docker
- **WebSocket Tests**: Timeout due to missing services
- **Architecture Compliance**: 18,657 violations

## Next Steps:
1. Apply the test fixes outlined above
2. Start Docker/Podman services for integration testing
3. Create migration script for remaining test files
4. Document new testing patterns in test architecture guide