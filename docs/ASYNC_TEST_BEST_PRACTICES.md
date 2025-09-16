# Async Test Best Practices for Netra Apex

**Created:** 2025-09-15
**Purpose:** Prevent async test decorator gaps and ensure reliable test execution
**Business Impact:** Maintains 100% unit test success rate, preventing CI/CD blockages

## Business Value Justification (BVJ)

- **Segment:** Platform Development & CI/CD Infrastructure
- **Business Goal:** Development Velocity - Prevent test failures that block deployments
- **Value Impact:** Reliable tests enable rapid feature delivery and maintain system quality
- **Strategic Impact:** Developer productivity directly impacts time-to-market for customer features

## Root Cause Analysis: The 94.7% → 100% Issue

### What Happened
- 11 async test methods in `test_agent_execution_core_business_logic_comprehensive.py` were missing `@pytest.mark.asyncio` decorators
- This caused "RuntimeWarning: coroutine was never awaited" failures
- Unit test success rate dropped from expected 100% to 94.7%
- Broader scan revealed 458 similar violations across supervisor tests

### Why It Matters
- **CI/CD Impact:** Failed tests block deployments and feature releases
- **Developer Experience:** Confusing errors slow down development velocity
- **System Reliability:** Improperly tested async code can cause race conditions in production

## Async Test Pattern Requirements

### 1. Required Decorator Pattern

**ALWAYS use `@pytest.mark.asyncio` for async test methods:**

```python
@pytest.mark.asyncio
async def test_some_async_functionality(self):
    """Test async functionality with proper decorator."""
    result = await some_async_function()
    assert result is not None
```

### 2. Import Requirements

**Ensure pytest is imported in all test files with async methods:**

```python
import pytest
import asyncio
from unittest.mock import AsyncMock
```

### 3. Fixture Patterns

**Use AsyncMock for async fixtures and methods:**

```python
@pytest.fixture
def mock_async_service(self):
    """Create AsyncMock for async service methods."""
    service = AsyncMock()
    service.execute = AsyncMock(return_value={"success": True})
    return service
```

### 4. Common Anti-Patterns to Avoid

❌ **Missing Decorator:**
```python
# WRONG - Missing @pytest.mark.asyncio
async def test_async_function(self):
    result = await some_async_call()
    assert result
```

✅ **Correct Pattern:**
```python
# CORRECT - Has @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_function(self):
    result = await some_async_call()
    assert result
```

❌ **Using Mock instead of AsyncMock:**
```python
# WRONG - Mock for async method
mock_service.execute = Mock(return_value={"success": True})
```

✅ **Correct Pattern:**
```python
# CORRECT - AsyncMock for async method
mock_service.execute = AsyncMock(return_value={"success": True})
```

## Validation and Prevention

### 1. Automated Validation Script

Use the validation script before committing:

```bash
# Check specific file
python scripts/validate_async_test_patterns.py --file "path/to/test_file.py"

# Check entire directory
python scripts/validate_async_test_patterns.py --dir "netra_backend/tests/unit"

# Auto-fix violations
python scripts/validate_async_test_patterns.py --dir "netra_backend/tests/unit" --fix
```

### 2. Pre-Commit Hook Integration

Add to `.pre-commit-config.yaml`:

```yaml
  - repo: local
    hooks:
      - id: async-test-validation
        name: Validate async test patterns
        entry: python scripts/validate_async_test_patterns.py --dir netra_backend/tests
        language: system
        pass_filenames: false
        always_run: true
```

### 3. CI/CD Integration

Add to GitHub Actions workflow:

```yaml
- name: Validate Async Test Patterns
  run: python scripts/validate_async_test_patterns.py --dir netra_backend/tests
```

## Development Workflow Integration

### 1. Before Writing Tests

1. **Plan Async Methods:** Identify which test methods will be async
2. **Import Dependencies:** Ensure `pytest` and `AsyncMock` are imported
3. **Use Templates:** Start with proven async test templates

### 2. During Test Development

1. **Decorator First:** Add `@pytest.mark.asyncio` before writing async test body
2. **Mock Properly:** Use `AsyncMock` for all async method mocks
3. **Test Locally:** Run individual test files to verify async execution

### 3. Before Committing

1. **Run Validation:** `python scripts/validate_async_test_patterns.py --dir netra_backend/tests`
2. **Fix Violations:** Use `--fix` flag if violations found
3. **Verify Tests:** Run affected test files to ensure they pass

## Test Execution Verification

### 1. Local Testing Commands

```bash
# Test specific async file
python -m pytest path/to/async_test_file.py -v

# Test with async warnings
python -m pytest path/to/async_test_file.py -v --tb=short

# Run through unified test runner
python tests/unified_test_runner.py --category unit --fast-fail
```

### 2. Success Indicators

✅ **Tests Pass:** No "RuntimeWarning: coroutine was never awaited"
✅ **Proper Execution:** Tests show proper async execution times
✅ **Clean Output:** No async-related warnings in test output

### 3. Failure Indicators

❌ **Runtime Warnings:** "coroutine was never awaited" messages
❌ **Fast Execution:** Async tests completing in 0.00s (not actually awaiting)
❌ **Mock Errors:** "Mock object used where AsyncMock expected"

## Architecture Integration

### 1. SSOT Compliance

- **BaseTestCase:** All async tests inherit from `SSotBaseTestCase`
- **Mock Factory:** Use `SSotMockFactory` for consistent async mocks
- **Test Runner:** Execute through `tests/unified_test_runner.py`

### 2. Business Logic Testing

- **Real Services:** Prefer real services over mocks in integration tests
- **User Context:** Use `UserExecutionContext` for user isolation
- **WebSocket Events:** Test actual WebSocket event delivery

### 3. Error Boundaries

- **Graceful Failures:** Test async error handling and recovery
- **Timeout Testing:** Validate timeout behavior with proper async patterns
- **Concurrency:** Test multi-user async execution isolation

## Monitoring and Metrics

### 1. Test Success Metrics

- **Unit Test Pass Rate:** Should maintain 100%
- **Async Test Coverage:** Track percentage of async methods tested
- **Violation Count:** Monitor async pattern violations over time

### 2. Development Velocity Metrics

- **CI/CD Pipeline Success:** Async test failures should not block deployments
- **Developer Productivity:** Time spent debugging async test issues
- **Code Review Efficiency:** Catch async patterns during review

## Rollback and Recovery

### 1. Emergency Procedures

If async test failures block critical deployments:

1. **Immediate Fix:** Use validation script with `--fix` flag
2. **Verify Quickly:** Run affected tests to confirm fix
3. **Deploy Safely:** Proceed with deployment after verification

### 2. Long-term Resolution

1. **Root Cause Analysis:** Document why violations occurred
2. **Process Improvement:** Strengthen validation in development workflow
3. **Team Training:** Share learnings with development team

## Examples and Templates

### 1. Basic Async Test Template

```python
import pytest
from unittest.mock import AsyncMock

class TestAsyncFunctionality(SSotBaseTestCase):
    """Test async business functionality."""

    @pytest.mark.asyncio
    async def test_async_business_operation(self):
        """Test core async business logic."""
        # Setup
        mock_service = AsyncMock()
        mock_service.execute = AsyncMock(return_value={"success": True})

        # Execute
        result = await async_business_function(mock_service)

        # Verify
        assert result["success"] is True
        mock_service.execute.assert_called_once()
```

### 2. WebSocket Integration Test Template

```python
@pytest.mark.asyncio
async def test_websocket_async_events(self):
    """Test WebSocket event delivery in async context."""
    # Setup WebSocket bridge
    bridge = AsyncMock()
    bridge.notify_agent_started = AsyncMock(return_value=True)

    # Execute async operation with WebSocket notifications
    result = await agent_execution_with_websocket_events(bridge)

    # Verify WebSocket events were sent
    bridge.notify_agent_started.assert_called_once()
    assert result.success is True
```

## Conclusion

Proper async test patterns are critical for:
- **System Reliability:** Ensure async code works correctly in production
- **Development Velocity:** Prevent test failures that block deployments
- **Business Value:** Enable rapid feature delivery with confidence

**Remember:** Every async test method MUST have `@pytest.mark.asyncio` decorator.

---

**Next Review:** After any major async codebase changes or test framework updates
**Ownership:** Platform Development Team
**Escalation:** For violations blocking deployment, contact DevOps immediately