# SSOT-incomplete-migration-websocket-message-router-duplication

## Critical SSOT Violation: Multiple WebSocket Message Router Implementations

### Status
- **Priority:** P0 CRITICAL
- **Impact:** Blocks golden path - users cannot reliably get AI responses
- **Business Impact:** $500K+ ARR at risk - affects 90% of platform value (chat)

### Violation Details
Multiple competing WebSocket message router implementations exist:

1. **Duplicate CanonicalMessageRouter Classes:**
   - `/netra_backend/app/websocket_core/canonical_message_router.py` (Line 94)
   - `/netra_backend/app/websocket_core/handlers.py` (Line 1351)

2. **Circular/Duplicate Router Inheritance:**
   - `MessageRouter(ExternalCanonicalMessageRouter)` in handlers.py creates circular dependencies

3. **Inconsistent WebSocket Manager Import Patterns:**
   - Two different import paths for `get_websocket_manager` in example_message_processor.py

### Why This Blocks Golden Path
- Messages may be processed by wrong router
- WebSocket events (agent_started, etc.) delivered inconsistently
- Agent responses may not reach correct users
- Factory pattern user isolation can break

### Test Plan

#### Existing Tests (Found)
**Mission Critical Tests:**
- ✅ `/tests/mission_critical/test_websocket_agent_events_suite.py` - Protects $500K ARR golden path
- ✅ `/tests/unit/message_routing/test_ssot_message_router_consolidation.py` - SSOT validation (expected to fail)
- ✅ `/tests/integration/websocket/test_user_isolation_message_routing.py` - Enterprise compliance

**Integration Tests:**
- ✅ `/netra_backend/tests/integration/test_message_routing_integration.py` - Pipeline validation
- ✅ `/tests/validation/test_canonical_message_router_non_docker.py` - Import validation
- ✅ `/tests/unit/websocket_core/test_issue_1099_ssot_handler_validation.py` - Handler validation

#### New Tests Needed (PLANNED)
- ✅ `/tests/unit/ssot/test_canonical_message_router_single_implementation_validation.py` (CREATED & TESTED)
  - Validates only ONE CanonicalMessageRouter class exists
  - Currently FAILS: Found 2 CanonicalMessageRouter implementations, 104 total router classes
  - Will PASS after consolidation
- [ ] `/tests/unit/ssot/test_message_router_inheritance_validation.py`
  - Prevents circular inheritance patterns
  - Validates clean MRO and base class structure
- [ ] `/tests/unit/ssot/test_websocket_manager_import_consistency.py`
  - Ensures consistent import path for get_websocket_manager
  - Prevents fallback/backup import anti-patterns
- [ ] `/tests/unit/ssot/test_message_router_backwards_compatibility.py`
  - Validates legacy imports continue working via aliases
  - Ensures method signatures preserved for smooth transition

### Remediation Plan
- [ ] Consolidate to single CanonicalMessageRouter in canonical_message_router.py
- [ ] Remove duplicate in handlers.py
- [ ] Update all imports to use SSOT WebSocket manager factory
- [ ] Ensure all 5 critical WebSocket events flow correctly

### Progress Log
- 2025-09-17: Issue discovered and documented
- 2025-09-17: GitHub issue to be created manually (gh command restricted)
- 2025-09-17: Starting test discovery phase
- 2025-09-17: Found 6 critical existing test suites to protect
- 2025-09-17: Created SSOT validation test - confirmed 2 CanonicalMessageRouter, 104 total router classes