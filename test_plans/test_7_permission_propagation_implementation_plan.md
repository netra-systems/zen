# Test Suite 7: Permission Propagation - Implementation Plan

## Test Overview
**File**: `tests/unified/test_permission_propagation_basic.py`
**Priority**: MEDIUM
**Business Impact**: $40K+ MRR
**Performance Target**: < 500ms propagation

## Core Functionality to Test
1. Create user with basic permissions
2. Elevate to admin in Auth service
3. Verify admin access in Backend
4. Verify admin commands in WebSocket
5. Revoke permissions
6. Verify revocation across all services

## Test Cases (minimum 5 required)

1. **Basic Permission Grant** - Grant permissions and verify across services
2. **Admin Elevation** - Elevate user to admin and verify elevated access
3. **Permission Revocation** - Revoke permissions and verify loss of access
4. **WebSocket Command Access** - Verify permission-based command filtering
5. **Permission Propagation Speed** - Changes propagate < 500ms
6. **Concurrent Permission Changes** - Multiple permission changes don't conflict
7. **Permission Rollback** - Failed permission changes rollback properly

## Success Criteria
- Permissions propagate correctly
- < 500ms propagation time
- WebSocket commands filtered
- Revocation works properly
- No permission leaks