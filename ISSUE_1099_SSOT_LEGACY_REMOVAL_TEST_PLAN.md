# Issue #1099 SSOT Legacy Removal Test Plan

## Status Assessment

❌ **Issue #1099 is NOT resolved** - Legacy SSOT violation needs remediation

### Current State Analysis
- **Legacy file exists**: `services/websocket/message_handler.py` (710 lines)
- **SSOT file exists**: `websocket_core/handlers.py` (2,088 lines)
- **Files importing legacy patterns**: 27 files identified
- **Critical infrastructure dependency**: Golden Path user flow (login → AI responses)

## Critical Interface Differences Discovered

### Legacy Pattern (`services/websocket/message_handler.py`)
```python
async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
    """Handle the message"""
    # Returns None, takes payload dict
```

### SSOT Pattern (`websocket_core/handlers.py`)
```python
async def handle_message(self, user_id: str, websocket: WebSocket, message: WebSocketMessage) -> bool:
    """Handle a WebSocket message."""
    # Returns bool (success/failure), takes WebSocket + WebSocketMessage object
```

### Key Breaking Changes
1. **Method name**: `handle()` → `handle_message()`
2. **Return type**: `None` → `bool` (success/failure indication)
3. **Parameters**: `payload: Dict` → `websocket: WebSocket, message: WebSocketMessage`
4. **Message format**: Raw dict → Structured WebSocketMessage object
5. **Error handling**: Exception-based → Return code based

## Business Impact Assessment

### Golden Path Protection ($500K+ ARR)
- **Critical dependency**: WebSocket message handling enables chat functionality
- **User flow**: Login → Agent messages → AI responses → Chat completion
- **Handler types requiring migration**:
  - `StartAgentHandler` - Agent execution requests
  - `UserMessageHandler` - User chat messages
  - `ThreadHistoryHandler` - Conversation context
  - `StopAgentHandler` - Agent termination
  - `MessageHandlerService` - Handler orchestration

### Migration Risk Analysis
- **HIGH RISK**: Interface breaking changes affect 27 files
- **CRITICAL**: Golden Path functionality must be preserved
- **COMPLEX**: Two different handler architectures need bridging

## Test Strategy

### Phase 1: Legacy Functionality Validation (FAILING Tests)

#### Test Suite 1: Legacy Handler Core Functionality
```bash
# Create tests that FAIL initially to prove legacy system works
tests/unit/ssot_legacy_removal/test_legacy_message_handlers_baseline.py
```
**Test Coverage:**
- ✅ StartAgentHandler processes start_agent messages correctly
- ✅ UserMessageHandler processes user_message correctly
- ✅ ThreadHistoryHandler retrieves conversation history
- ✅ StopAgentHandler terminates agents properly
- ✅ MessageHandlerService orchestrates handlers correctly
- ✅ BaseMessageHandler interface contract validation

#### Test Suite 2: Legacy Message Processing Pipeline
```bash
tests/integration/ssot_legacy_removal/test_legacy_message_pipeline_integration.py
```
**Test Coverage:**
- ✅ End-to-end message routing from WebSocket to handler
- ✅ Handler registration and discovery
- ✅ Message validation and sanitization
- ✅ Error handling and recovery
- ✅ Queue management and priorities

#### Test Suite 3: Golden Path Legacy Validation
```bash
tests/e2e/ssot_legacy_removal/test_golden_path_legacy_preservation_e2e.py
```
**Test Coverage:**
- ✅ User login → Agent start → AI response flow
- ✅ WebSocket event sequence validation
- ✅ Thread history continuity
- ✅ Multi-user isolation
- ✅ Error recovery scenarios

### Phase 2: SSOT Equivalence Validation

#### Test Suite 4: SSOT Handler Equivalence
```bash
tests/unit/ssot_legacy_removal/test_ssot_handler_equivalence_unit.py
```
**Test Coverage:**
- ✅ SSOT handlers provide equivalent functionality to legacy
- ✅ Interface adapter validation for breaking changes
- ✅ Message format conversion accuracy
- ✅ WebSocket integration correctness
- ✅ Return code mapping (None → bool)

#### Test Suite 5: SSOT Integration Validation
```bash
tests/integration/ssot_legacy_removal/test_ssot_integration_validation.py
```
**Test Coverage:**
- ✅ SSOT message routing equivalence
- ✅ WebSocket manager integration
- ✅ Error handling consistency
- ✅ Performance parity validation

### Phase 3: Migration Validation

#### Test Suite 6: Import Migration Validation
```bash
tests/unit/ssot_legacy_removal/test_import_migration_validation.py
```
**Test Coverage:**
- ✅ All 27 files successfully migrate imports
- ✅ No circular import dependencies introduced
- ✅ Import path consistency validation
- ✅ Backwards compatibility shims if needed

#### Test Suite 7: Post-Migration Integration
```bash
tests/integration/ssot_legacy_removal/test_post_migration_integration.py
```
**Test Coverage:**
- ✅ All handlers work with SSOT patterns
- ✅ No functionality regression
- ✅ Golden Path preservation confirmed
- ✅ Performance maintained or improved

### Phase 4: Legacy Removal Validation

#### Test Suite 8: Legacy Cleanup Validation
```bash
tests/unit/ssot_legacy_removal/test_legacy_cleanup_validation.py
```
**Test Coverage:**
- ✅ Legacy file completely removed
- ✅ All imports updated to SSOT patterns
- ✅ No orphaned references remain
- ✅ Documentation updated correctly

## Migration Strategy

### Step 1: Create Interface Adapter
```python
# Create adapter to bridge interface differences
class LegacyToSSOTAdapter:
    """Adapter to bridge legacy handle() to SSOT handle_message()"""

    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        """Legacy interface that delegates to SSOT handle_message"""
        # Convert payload to WebSocketMessage
        # Call SSOT handle_message
        # Convert bool return to None/Exception
```

### Step 2: Gradual Migration with Backwards Compatibility
1. Create adapter classes for interface bridging
2. Update imports file-by-file with validation
3. Provide temporary shims during transition
4. Remove legacy file only after all migrations complete

### Step 3: Validation at Each Step
- Run full test suite after each file migration
- Validate Golden Path functionality preserved
- Check for performance regressions
- Verify WebSocket event delivery

## Test Execution Requirements

### Non-Docker Test Focus
- **Unit tests**: Pure Python logic, no Docker required
- **Integration tests**: Use staging environment for real service testing
- **E2E tests**: Execute against staging GCP remote environment
- **Mock strategy**: Minimal mocking, prefer real services where possible

### Test Success Criteria
1. **Phase 1**: All legacy tests PASS (proving baseline functionality)
2. **Phase 2**: All SSOT equivalence tests PASS
3. **Phase 3**: All migration tests PASS with zero Golden Path regression
4. **Phase 4**: All cleanup tests PASS with complete legacy removal

### Golden Path Success Metrics
- ✅ User login flow: <2s response time
- ✅ Agent message processing: All 5 WebSocket events delivered
- ✅ Chat completion: End-to-end <10s for simple queries
- ✅ Thread history: Complete conversation context preserved
- ✅ Multi-user isolation: No data leakage between concurrent users

## Implementation Timeline

### Phase 1: Test Creation (Est: 2-3 hours)
- Create 8 test suites with comprehensive coverage
- Establish baseline functionality validation
- Verify tests FAIL appropriately before migration

### Phase 2: Interface Analysis (Est: 1 hour)
- Deep dive into interface differences
- Design adapter architecture
- Plan backwards compatibility approach

### Phase 3: Gradual Migration (Est: 4-5 hours)
- Implement interface adapters
- Migrate imports file-by-file
- Validate each step with test suite

### Phase 4: Legacy Cleanup (Est: 1 hour)
- Remove legacy file
- Clean up temporary shims
- Final validation and documentation

**Total Estimated Time: 8-10 hours**

## Risk Mitigation

### High Risk Areas
1. **WebSocket event delivery**: Critical for Golden Path
2. **Thread history continuity**: Required for chat context
3. **Multi-user isolation**: Security and data integrity
4. **Agent execution pipeline**: Core business functionality

### Mitigation Strategies
1. **Comprehensive test coverage**: 8 test suites covering all scenarios
2. **Gradual migration**: File-by-file with validation at each step
3. **Interface adapters**: Bridge breaking changes temporarily
4. **Rollback plan**: Ability to revert any migration step
5. **Staging validation**: Real environment testing before production

## Success Definition

✅ **Complete Success Criteria:**
1. Legacy file `services/websocket/message_handler.py` completely removed
2. All 27 files successfully migrated to SSOT imports
3. Golden Path functionality fully preserved and validated
4. All test suites passing (8 test suites, ~50+ individual tests)
5. No performance regression measured
6. Zero customer impact or functionality loss

This comprehensive test plan ensures safe, validated SSOT legacy removal while protecting the critical Golden Path user flow that generates $500K+ ARR.