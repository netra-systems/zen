# Issue #1182 Test Framework Fixes Required

## Quick Fixes for Integration and E2E Tests

### Integration Test Fixes

#### 1. Fix `test_websocket_factory_consolidation.py`

**Issue**: Missing `self.test_user_contexts` and `self.factory_inconsistencies`

**Fix**: Add to setUp method:
```python
def setUp(self):
    super().setUp()
    self.factory_inconsistencies = []
    self.test_user_contexts = [
        {"user_id": f"test_user_{i}", "session_id": f"session_{i}"} 
        for i in range(3)
    ]
```

#### 2. Fix `test_websocket_multi_user_isolation.py`

**Issue**: Missing `self.user_sessions`

**Fix**: Add to setUp method:
```python
def setUp(self):
    super().setUp()
    self.user_sessions = {
        f"user_{i}": {"session_id": f"session_{i}", "context": {}}
        for i in range(3)
    }
```

### E2E Test Fixes

#### 3. Fix `test_golden_path_websocket_events.py`

**Issue**: WebSocket client `extra_headers` compatibility

**Fix**: Update WebSocket connection call:
```python
# Remove extra_headers parameter or update websockets library
async with websockets.connect(websocket_url) as websocket:
    # ... rest of test
```

## Test Execution Commands (After Fixes)

```bash
# Unit tests (working)
python3 -m pytest tests/unit/websocket_core/test_websocket_manager_ssot_violations.py -v

# Integration tests (after fixes)
python3 -m pytest tests/integration/test_websocket_factory_consolidation.py -v
python3 -m pytest tests/integration/test_websocket_multi_user_isolation.py -v

# E2E tests (after fixes)
python3 -m pytest tests/e2e_staging/test_golden_path_websocket_events.py -v
```

## Validation Strategy

1. **Apply fixes above**
2. **Re-run all test suites**
3. **Confirm consistent FAIL pattern** (proving violations exist)
4. **Ready for Phase 2 SSOT consolidation**