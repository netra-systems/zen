# SSOT Gardener Progress: WebSocket Authentication Path Fragmentation

**Issue Name:** SSOT-regression-WebSocket Authentication path fragmentation blocking Golden Path
**GitHub Issue:** [To be created]
**Status:** In Progress
**Created:** 2025-09-14

## SSOT Violation Summary

**Critical Issue:** Multiple JWT validation implementations across services creating authentication failures at WebSocket handshake, blocking Golden Path (users login → AI responses).

### Evidence Found
1. **4+ JWT validation paths identified:**
   - `/auth_service/auth_core/core/token_validator.py` - Auth service JWT validation
   - `/netra_backend/app/auth_integration/auth.py` - Backend auth integration bypass
   - `/netra_backend/app/websocket_core/unified_jwt_protocol_handler.py` - WebSocket-specific JWT
   - Frontend JWT decoding in `/frontend/auth/context.tsx`

2. **Multiple WebSocket managers violating SSOT:**
   - `/netra_backend/app/websocket_core/websocket_manager.py` - Main manager
   - `/netra_backend/app/websocket_core/unified_manager.py` - Duplicate manager
   - `/netra_backend/app/services/websocket_bridge_factory.py` - Factory wrapper

### Business Impact
- **Golden Path Blocked:** Users cannot complete login → AI responses flow
- **WebSocket Events Fail:** agent_started, agent_thinking, tool_executing, tool_completed, agent_completed delivery inconsistent
- **Authentication Inconsistencies:** Different validation logic between HTTP and WebSocket requests

## Work Progress

### Phase 0: SSOT Audit ✅ COMPLETED
- [x] Identified 4+ JWT validation paths
- [x] Found multiple WebSocket manager implementations
- [x] Documented business impact on Golden Path
- [x] Prioritized most critical violations

### Phase 1: Test Discovery & Planning
- [ ] Discover existing auth/websocket tests
- [ ] Plan SSOT validation test suite
- [ ] Plan regression tests for Golden Path flow

### Phase 2: Test Creation
- [ ] Create failing SSOT violation tests
- [ ] Create Golden Path integration tests
- [ ] Validate test infrastructure

### Phase 3: SSOT Remediation Planning
- [ ] Plan JWT validation consolidation
- [ ] Plan WebSocket manager consolidation
- [ ] Design SSOT architecture

### Phase 4: SSOT Implementation
- [ ] Implement JWT SSOT consolidation
- [ ] Consolidate WebSocket managers
- [ ] Update all consumers

### Phase 5: Validation & Testing
- [ ] Run all existing tests
- [ ] Fix any breaking changes
- [ ] Validate Golden Path works

### Phase 6: PR Creation
- [ ] Create pull request
- [ ] Link to issue for auto-closure
- [ ] Document changes

## Files Requiring Changes (Top Priority)
1. `/netra_backend/app/auth_integration/auth.py` - Remove JWT bypass logic
2. `/auth_service/auth_core/core/token_validator.py` - Strengthen as single authority
3. `/netra_backend/app/websocket_core/unified_manager.py` - Consolidate or remove
4. `/netra_backend/app/websocket_core/unified_jwt_protocol_handler.py` - Remove duplicate JWT logic
5. `/frontend/auth/context.tsx` - Use consistent JWT validation

## Test Coverage Requirements
- JWT validation SSOT compliance tests
- WebSocket manager SSOT tests
- Golden Path end-to-end authentication flow
- Regression tests for existing functionality

## Risk Assessment
- **Risk Level:** HIGH - Authentication affects all user flows
- **Complexity:** HIGH - Cross-service coordination required
- **Impact:** CRITICAL - Blocks core business objective

## Notes
- Stay on develop-long-lived branch
- Ensure all changes are atomic and safe
- Focus on existing SSOT classes where possible
- Update tests to match SSOT patterns, don't bypass them