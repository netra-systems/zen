# Test Suite 8: Token Expiry Unified - Implementation Plan

## Test Overview
**File**: `tests/unified/test_token_expiry_unified.py`
**Priority**: MEDIUM
**Business Impact**: $35K+ MRR
**Performance Target**: < 100ms rejection time

## Core Functionality to Test
1. Generate token with short expiry
2. Use token successfully before expiry
3. Wait for token expiry
4. Verify rejection by Auth service
5. Verify rejection by Backend service
6. Verify WebSocket disconnection
7. Test refresh token flow

## Test Cases (minimum 5 required)

1. **Token Expiry Basic Flow** - Token works before expiry, fails after
2. **Unified Service Rejection** - All services reject expired tokens
3. **WebSocket Auto-Disconnect** - WebSocket disconnects on token expiry
4. **Refresh Token Flow** - Refresh token renews access properly
5. **Grace Period Handling** - Test expiry grace period if exists
6. **Clock Skew Tolerance** - Handle minor time differences
7. **Expiry Performance** - Rejection < 100ms for expired tokens

## Success Criteria
- Consistent expiry handling
- < 100ms rejection time
- WebSocket auto-disconnect
- Refresh flow works
- No expired token access