# Master Plan: Remove Legacy WebSocket Authentication Pathways (Issue #1296)

**Step 2 Planning Complete - Ready for Implementation**

## Executive Summary

This master plan addresses the removal of legacy WebSocket authentication pathways (Issue #1296) and its blocking dependencies. The plan provides a holistic resolution approach that prioritizes Golden Path functionality while ensuring system stability.

## Current Status Analysis

### ✅ Issue #1294 - RESOLVED
- Secret loading infrastructure fixed
- Service account permissions corrected
- Configuration validation made graceful
- **Status:** Complete and operational in staging

### ⚠️ Issues #1293, #1295, #1296 - NOT IMPLEMENTED
Based on codebase analysis, **NO ticket-based authentication infrastructure exists yet**:
- No `POST /websocket/ticket` endpoint found
- No ticket validation logic in WebSocket routes
- No frontend ticket integration
- Legacy pathways still fully operational

## Scope and Definition of Done

### Primary Goal
Replace the current multi-pathway authentication system with a single, ticket-based authentication flow that:
1. Eliminates browser WebSocket Authorization header limitations
2. Provides cryptographically secure, short-lived tickets
3. Maintains all 5 critical WebSocket events for Golden Path
4. Ensures complete user isolation and security

### Legacy Pathways to Remove (Post-Ticket Implementation)
Current analysis identifies these legacy authentication methods in `unified_auth_ssot.py`:

1. **JWT Authorization Header** - May be stripped by GCP load balancer
2. **JWT Query Parameter Fallback** - Infrastructure workaround, insecure
3. **Multiple JWT Validation Paths** - `_validate_jwt_via_legacy_service()`, `_fallback_via_legacy_jwt_decoding()`
4. **E2E Bypass Authentication** - Testing-only pathway
5. **Multiple Subprotocol Formats** - `jwt-auth.`, `jwt.`, `bearer.` variations
6. **Auth Service API Fallbacks** - Multiple fallback chains creating complexity

## Holistic Resolution Approach

### 1. Infrastructure/Config Changes Required

**Redis Configuration:**
- Ensure Redis available in all environments (dev, staging, prod)
- Configure ticket storage with TTL support
- Set appropriate connection timeouts and pooling

**GCP Cloud Run Updates:**
- Verify load balancer preserves query parameters
- Test WebSocket upgrade with ticket parameters
- Validate SSL certificate coverage for ticket endpoints

**Environment Variables:**
```bash
# New variables needed
TICKET_TTL_SECONDS=30  # Production: 30s, Dev: 60s
TICKET_LENGTH=32       # Cryptographic strength
ENABLE_TICKET_AUTH=true
DISABLE_LEGACY_AUTH=false  # Feature flag for gradual migration

# Existing variables to audit
WEBSOCKET_AUTH_TIMEOUT=15.0
WEBSOCKET_AUTH_RETRIES=3
```

### 2. Code Implementation Approach

**Phase 1: Ticket Infrastructure (#1293)**
```python
# New endpoint: POST /websocket/ticket
# Files to create/modify:
- netra_backend/app/routes/websocket_ticket.py  # New endpoint
- netra_backend/app/services/ticket_service.py  # Ticket generation logic
- netra_backend/app/core/redis_ticket_store.py  # Redis integration
```

**Phase 2: WebSocket Ticket Validation (#1294)**
```python
# Modify existing WebSocket route:
- netra_backend/app/routes/websocket_ssot.py     # Add ticket validation
- netra_backend/app/websocket_core/ticket_auth.py  # New auth module
```

**Phase 3: Frontend Integration (#1295)**
```typescript
// Frontend changes:
- frontend/lib/websocket-auth.ts         # Ticket-based connection
- frontend/contexts/websocket-context.tsx # Update connection logic
```

**Phase 4: Legacy Removal (#1296)**
```python
# Remove from unified_auth_ssot.py:
- _extract_jwt_from_auth_header()
- _extract_jwt_from_query_params()
- _validate_jwt_via_legacy_service()
- _fallback_via_legacy_jwt_decoding()
- All fallback chains and multiple auth methods
```

### 3. Implementation Order

**Week 1: Backend Infrastructure (Issues #1293 → #1294)**
1. Implement ticket generation endpoint with Redis
2. Add ticket validation to WebSocket route
3. Create comprehensive error handling and logging
4. Add feature flags for gradual rollout

**Week 2: Frontend Integration (Issue #1295)**
1. Update frontend WebSocket connection logic
2. Implement ticket acquisition flow
3. Add error handling for ticket failures
4. Test complete authentication flow

**Week 3: Legacy Removal (Issue #1296)**
1. Remove legacy authentication pathways
2. Clean up unused imports and dependencies
3. Update configuration to disable legacy features
4. Remove fallback chains and outdated logic

### 4. Test Requirements

**Unit Tests:**
- Ticket generation with various TTL values
- Ticket validation and consumption logic
- Error handling for all failure modes
- WebSocket connection with ticket authentication

**Integration Tests (Non-Docker):**
- Redis ticket storage and retrieval
- Full authentication flow from ticket generation to WebSocket connection
- Error scenarios: expired tickets, invalid tickets, Redis unavailable
- Auth service integration for user context establishment

**E2E Staging Tests:**
- Complete user journey: login → ticket → WebSocket → agent response
- Cross-browser compatibility for WebSocket ticket authentication
- Load testing with concurrent ticket generation and consumption
- Security testing: replay attacks, ticket reuse prevention

**Performance Tests:**
- Ticket generation rate: >1000 tickets/minute
- WebSocket connection latency with ticket auth: <50ms p99
- Memory usage under load (no ticket accumulation)

### 5. Risk Mitigation Strategy

**Gradual Migration Approach:**
1. **Feature Flags:** `ENABLE_TICKET_AUTH` and `DISABLE_LEGACY_AUTH` for controlled rollout
2. **Parallel Systems:** Run both ticket and legacy auth initially with monitoring
3. **Circuit Breaker:** Automatic fallback if ticket system fails
4. **Monitoring:** Comprehensive metrics for authentication success rates

**Rollback Plan:**
- Immediate: Set `ENABLE_TICKET_AUTH=false` to revert to legacy
- Database: No schema changes, Redis-only storage for tickets
- Code: Legacy pathways remain until final removal phase

## Critical Success Metrics

1. **Golden Path Preservation:** All 5 WebSocket events functional
2. **Authentication Success Rate:** >99.5% for ticket-based auth
3. **Performance:** Ticket auth faster than legacy (baseline: <50ms)
4. **Security:** Zero successful replay attacks in testing
5. **User Experience:** No degradation in chat functionality

## Prerequisites Before Starting

1. ✅ **Issue #1294 Complete:** Secret access confirmed working
2. ⚠️ **Redis Connectivity:** Verify Redis available in all environments
3. ⚠️ **GCP Testing:** Validate WebSocket query parameter preservation
4. ⚠️ **Auth Service:** Confirm auth service APIs for user context retrieval

## Next Actions

1. **Technical Review:** Validate Redis configuration across environments
2. **Architecture Approval:** Confirm ticket-based approach with stakeholders
3. **Resource Allocation:** Assign developers for 3-week implementation timeline
4. **Environment Preparation:** Ensure staging environment ready for testing

## Success Definition

Issue #1296 is complete when:
- ✅ Only ticket-based WebSocket authentication remains
- ✅ All legacy authentication pathways removed from codebase
- ✅ Golden Path (login → AI responses) fully functional
- ✅ All tests passing with ticket authentication only
- ✅ Production deployment successful with new authentication flow

---

**Ready to begin implementation with Issues #1293 → #1294 → #1295 → #1296**