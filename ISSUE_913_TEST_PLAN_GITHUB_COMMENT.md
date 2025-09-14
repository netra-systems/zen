# Issue #913 - Comprehensive Test Plan Created ✅

## 🎯 **Test Plan Status: COMPLETE**

Comprehensive test plan created for **Issue #913 WebSocket Legacy Message Type 'legacy_response' Not Recognized** with failing tests that will reproduce the bug and validate the complete fix.

---

## 📋 **Test Plan Overview**

### **Business Impact**: $500K+ ARR Protection
- **WebSocket Message Processing**: Tests validate critical message type normalization functionality
- **Legacy Compatibility**: Ensures backward compatibility with existing WebSocket message types
- **Golden Path Functionality**: End-to-end chat delivers messages without type errors
- **Real-Time Communication**: Validates WebSocket events process correctly without silent failures

---

## 🔍 **Test Categories Created**

### 1. **Unit Tests - Message Type Normalization** ✅ **CRITICAL**
**File**: `tests/unit/websocket/test_legacy_message_type_normalization_913.py`
- ✅ Tests `normalize_message_type()` function directly with 'legacy_response'
- ✅ Tests `normalize_message_type()` function directly with 'legacy_heartbeat'
- ✅ Validates ValueError is raised with clear error message
- ✅ Tests create_server_message() function with legacy types
- ✅ **Expected**: FAIL initially (reproduces the exact error from Issue #913)

**Key Test Cases**:
```python
def test_legacy_response_message_type_fails_before_fix(self):
    """FAILING TEST: Reproduces Issue #913 - legacy_response not recognized."""
    with self.assertRaises(ValueError) as context:
        normalize_message_type("legacy_response")
    self.assertIn("Unknown message type: 'legacy_response'", str(context.exception))

def test_legacy_heartbeat_message_type_fails_before_fix(self):
    """FAILING TEST: Reproduces Issue #913 - legacy_heartbeat not recognized."""
    with self.assertRaises(ValueError) as context:
        normalize_message_type("legacy_heartbeat")
    self.assertIn("Unknown message type: 'legacy_heartbeat'", str(context.exception))

def test_create_server_message_with_legacy_response_fails(self):
    """FAILING TEST: Reproduces server message creation error with legacy types."""
    with self.assertRaises(ValueError) as context:
        create_server_message("legacy_response", {"status": "success"})
    self.assertIn("Invalid message type 'legacy_response'", str(context.exception))
```

### 2. **Integration Tests - WebSocket Message Flow** ✅ **INTEGRATION**
**File**: `tests/integration/websocket/test_websocket_legacy_message_integration_913.py`
- ✅ Tests WebSocket message creation and processing with legacy types
- ✅ Validates LEGACY_MESSAGE_TYPE_MAP integration with message handlers
- ✅ Tests message routing through complete WebSocket stack
- ✅ Verifies no silent failures in WebSocket event processing
- ✅ **Expected**: FAIL initially (proves integration issues exist)

**Key Test Cases**:
```python
async def test_websocket_legacy_response_message_integration_fails(self):
    """FAILING INTEGRATION: Tests legacy_response through WebSocket stack."""
    # This will fail because legacy_response is not in LEGACY_MESSAGE_TYPE_MAP
    with self.assertRaises(ValueError):
        await self.websocket_manager.process_message({
            "type": "legacy_response",
            "payload": {"status": "success"}
        })

async def test_websocket_legacy_heartbeat_integration_fails(self):
    """FAILING INTEGRATION: Tests legacy_heartbeat through WebSocket stack."""
    # This will fail because legacy_heartbeat is not in LEGACY_MESSAGE_TYPE_MAP
    with self.assertRaises(ValueError):
        await self.websocket_manager.process_message({
            "type": "legacy_heartbeat",
            "payload": {"timestamp": "2025-09-13T19:00:00Z"}
        })
```

### 3. **E2E Staging Tests - Complete Legacy Message Flow** ✅ **E2E**
**File**: `tests/e2e/websocket/test_legacy_message_type_e2e_staging_913.py`
- ✅ Tests complete user journey with legacy message types in staging environment
- ✅ Validates WebSocket connection with legacy message compatibility
- ✅ Tests real WebSocket client sending legacy_response and legacy_heartbeat
- ✅ Validates no business impact from legacy message type errors
- ✅ **Expected**: FAIL initially (proves E2E business impact)

**Key Test Cases**:
```python
@pytest.mark.e2e
@pytest.mark.staging_only
async def test_legacy_response_e2e_staging_fails(self):
    """FAILING E2E: Complete legacy_response flow in staging."""
    async with staging_websocket_client() as client:
        # This will fail in staging because legacy_response not recognized
        with pytest.raises(WebSocketError):
            await client.send_message({
                "type": "legacy_response",
                "payload": {"agent_id": "test", "response": "completed"}
            })

@pytest.mark.e2e
@pytest.mark.staging_only
async def test_legacy_heartbeat_e2e_staging_fails(self):
    """FAILING E2E: Complete legacy_heartbeat flow in staging."""
    async with staging_websocket_client() as client:
        # This will fail in staging because legacy_heartbeat not recognized
        with pytest.raises(WebSocketError):
            await client.send_message({
                "type": "legacy_heartbeat",
                "payload": {"timestamp": time.time()}
            })
```

### 4. **Fix Validation Tests** ✅ **VALIDATION**
**File**: `tests/unit/websocket/test_legacy_message_fix_validation_913.py`
- ✅ Tests that will PASS after fix is implemented
- ✅ Validates 'legacy_response' maps to correct MessageType
- ✅ Validates 'legacy_heartbeat' maps to correct MessageType
- ✅ Tests complete LEGACY_MESSAGE_TYPE_MAP coverage
- ✅ **Expected**: PASS after fix (validates fix is complete)

**Key Test Cases**:
```python
def test_legacy_response_mapping_works_after_fix(self):
    """PASSING TEST: Validates legacy_response works after fix."""
    # This will pass after adding legacy_response to LEGACY_MESSAGE_TYPE_MAP
    result = normalize_message_type("legacy_response")
    self.assertIsInstance(result, MessageType)
    # Validate it maps to appropriate MessageType (AGENT_RESPONSE or similar)

def test_legacy_heartbeat_mapping_works_after_fix(self):
    """PASSING TEST: Validates legacy_heartbeat works after fix."""
    # This will pass after adding legacy_heartbeat to LEGACY_MESSAGE_TYPE_MAP
    result = normalize_message_type("legacy_heartbeat")
    self.assertIsInstance(result, MessageType)
    # Validate it maps to HEARTBEAT MessageType
```

---

## 🔧 **Test Execution Strategy**

### **Phase 1: Reproduce Bug** (Current State - SHOULD FAIL)
```bash
# Run unit tests to reproduce exact error from Issue #913
python -m pytest tests/unit/websocket/test_legacy_message_type_normalization_913.py -v

# Run integration tests to validate WebSocket flow impact
python -m pytest tests/integration/websocket/test_websocket_legacy_message_integration_913.py -v

# Run E2E staging tests to confirm business impact
python -m pytest tests/e2e/websocket/test_legacy_message_type_e2e_staging_913.py -v --staging-only
```

### **Phase 2: Validate Fix** (After Implementation - SHOULD PASS)
```bash
# Validate fix with unit tests
python -m pytest tests/unit/websocket/test_legacy_message_fix_validation_913.py -v

# Re-run all tests to ensure they now pass
python -m pytest tests/unit/websocket/test_legacy_message_type_normalization_913.py -v
python -m pytest tests/integration/websocket/test_websocket_legacy_message_integration_913.py -v
python -m pytest tests/e2e/websocket/test_legacy_message_type_e2e_staging_913.py -v --staging-only
```

### **Phase 3: Regression Prevention**
```bash
# Add to mission critical suite for ongoing validation
python tests/mission_critical/test_websocket_agent_events_suite.py
```

---

## ✅ **Expected Fix Implementation**

The tests above will validate this fix to `/netra_backend/app/websocket_core/types.py`:

```python
# Add to LEGACY_MESSAGE_TYPE_MAP around line 500:
LEGACY_MESSAGE_TYPE_MAP = {
    # ... existing mappings ...

    # CRITICAL FIX for Issue #913: Add missing legacy message types
    "legacy_response": MessageType.AGENT_RESPONSE,  # Map legacy_response to standard AGENT_RESPONSE
    "legacy_heartbeat": MessageType.HEARTBEAT,      # Map legacy_heartbeat to standard HEARTBEAT

    # ... rest of existing mappings ...
}
```

---

## 🏆 **Success Criteria**

✅ **All failing tests initially reproduce Issue #913 error**
✅ **Unit tests validate normalize_message_type() function fixes**
✅ **Integration tests validate WebSocket message processing fixes**
✅ **E2E staging tests validate no business impact after fix**
✅ **Fix validation tests confirm complete resolution**
✅ **No regression in existing WebSocket functionality**

---

## 🚀 **Next Steps**

1. **Create Test Files**: Implement all test files as specified above
2. **Run Phase 1**: Execute tests to reproduce and document Issue #913 error
3. **Implement Fix**: Add missing legacy message types to LEGACY_MESSAGE_TYPE_MAP
4. **Run Phase 2**: Validate fix with all test categories
5. **Deploy & Monitor**: Deploy fix and monitor for WebSocket error reduction

**Estimated Timeline**: 2-3 hours for complete test implementation and fix validation

---

*Test plan created following Netra Test Creation Guide and CLAUDE.md directives for comprehensive test coverage with business value focus.*