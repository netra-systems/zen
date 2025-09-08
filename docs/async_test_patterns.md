# Async Test Patterns and Best Practices

**Business Value**: Platform/Internal - Test Reliability & Development Velocity  
**Status**: COMPLETE - Remediated RuntimeWarning async issues  
**Date**: September 8, 2025

## Overview

This document provides comprehensive guidance for writing async tests that properly manage coroutine lifecycles and eliminate RuntimeWarnings about unawaited coroutines.

## Problem Statement

Integration tests with async components were generating RuntimeWarnings:
```
RuntimeWarning: coroutine 'MockAgentRegistry.unregister_agent' was never awaited
```

This occurred when:
- Async methods called in sync teardown contexts
- `asyncio.create_task()` used without proper awaiting
- Mock objects with async methods not properly cleaned up

## SSOT Solution: Async Test Helpers

### 1. Import SSOT Async Helpers

```python
from test_framework.ssot.async_test_helpers import (
    async_cleanup_registry, 
    AsyncTestFixtureMixin,
    AsyncMockManager
)
```

### 2. Use AsyncTestFixtureMixin

```python
class TestMyAsyncFeature(SSotBaseTestCase, AsyncTestFixtureMixin):
    """Example async test class."""
    
    def setup_method(self, method=None):
        super().setup_method(method)
        self.setup_async_resources()
        
        # Create and track mock registry
        self.mock_registry = MockAgentRegistry()
        self.track_mock_registry(self.mock_registry)
    
    @pytest.fixture(autouse=True)
    async def auto_cleanup_agents(self):
        """Auto cleanup fixture."""
        yield
        await self.cleanup_all_async_resources()
```

### 3. Proper Async Mock Creation

```python
# Use AsyncMockManager for properly configured mocks
agent_mock = AsyncMockManager.create_agent_mock(
    agent_id="test_001",
    agent_type="analysis",
    state="ready"
)

registry_mock = AsyncMockManager.create_registry_mock()
```

## Anti-Patterns to Avoid

### ❌ Wrong: Unawaited asyncio.create_task

```python
def teardown_method(self):
    # This creates RuntimeWarning
    for agent_id in self.registry.agents:
        asyncio.create_task(self.registry.unregister_agent(agent_id))
```

### ✅ Correct: Proper Async Cleanup

```python
@pytest.fixture(autouse=True)
async def auto_cleanup(self):
    yield
    await async_cleanup_registry(self.mock_registry)
```

### ❌ Wrong: Sync teardown with async calls

```python
def teardown_method(self):
    # This doesn't work - mixing sync/async
    asyncio.run(self.cleanup_async_stuff())
```

### ✅ Correct: Async fixture for cleanup

```python
@pytest.fixture(autouse=True)
async def auto_cleanup(self):
    yield
    await self.cleanup_all_async_resources()
```

## Available SSOT Helpers

### async_cleanup_registry(registry)
Safely cleanup all agents in a mock registry without RuntimeWarnings.

### AsyncTestFixtureMixin
Provides standardized async resource tracking and cleanup methods.

### AsyncMockManager
Factory for creating properly configured async mocks.

### async_resource_context(*resources)
Context manager for automatic async resource cleanup.

## Test Patterns

### Pattern 1: Simple Async Resource Cleanup

```python
class TestAsyncFeature(SSotBaseTestCase):
    @pytest.fixture(autouse=True)
    async def auto_cleanup(self):
        yield
        if hasattr(self, 'mock_registry'):
            await async_cleanup_registry(self.mock_registry)
```

### Pattern 2: Multiple Async Resources

```python
class TestComplexAsyncFeature(SSotBaseTestCase, AsyncTestFixtureMixin):
    def setup_method(self, method=None):
        super().setup_method(method)
        self.setup_async_resources()
        
        # Track multiple resources
        self.track_mock_registry(self.registry1)
        self.track_mock_registry(self.registry2)
        self.track_async_resource(self.async_manager)
    
    @pytest.fixture(autouse=True)
    async def auto_cleanup(self):
        yield
        await self.cleanup_all_async_resources()
```

### Pattern 3: Context Manager Pattern

```python
async def test_with_context_manager(self):
    async with async_resource_context(
        self.mock_registry, 
        self.async_service
    ) as resources:
        # Test with resources
        registry, service = resources
        # ... test logic
    # Resources automatically cleaned up
```

## Validation

Use the validation script to verify async patterns:
```bash
python test_async_cleanup_validation.py
```

Expected output:
```
[CHECK] ASYNC CLEANUP VALIDATION SUMMARY
============================================================
Basic async cleanup:       [PASS]
SSOT helpers import:       [PASS]  
Cleanup helper function:   [PASS]
No RuntimeWarnings:        [PASS]

[RESULT] OVERALL: SUCCESS
```

## Migration Checklist

When updating existing async tests:

- [ ] Import SSOT async helpers
- [ ] Replace sync teardown with async fixture
- [ ] Use AsyncTestFixtureMixin for complex tests
- [ ] Track async resources with `track_mock_registry()` 
- [ ] Replace manual cleanup with `cleanup_all_async_resources()`
- [ ] Use AsyncMockManager for mock creation
- [ ] Run validation script to verify no RuntimeWarnings
- [ ] Test all async test methods pass

## Business Impact

**Before**: RuntimeWarnings masked real issues, flaky test execution  
**After**: Clean async execution, reliable test outcomes, improved debugging

**Benefits**:
- ✅ Eliminated RuntimeWarnings about unawaited coroutines
- ✅ Standardized async test patterns across codebase
- ✅ Improved test reliability and debugging clarity
- ✅ Faster development velocity with consistent patterns

## Related Files

- `test_framework/ssot/async_test_helpers.py` - SSOT async helpers
- `tests/integration/offline/test_agent_factory_integration_offline.py` - Example implementation
- `test_async_cleanup_validation.py` - Validation script

## Compliance with CLAUDE.md

✅ **SSOT Compliance**: Single source of truth for async test patterns  
✅ **Business Value Focus**: Improves test reliability and development velocity  
✅ **Error Visibility**: Eliminates warnings that mask real issues  
✅ **Async Hygiene**: Proper coroutine lifecycle management  
✅ **Integration**: Works with existing SSotBaseTestCase patterns