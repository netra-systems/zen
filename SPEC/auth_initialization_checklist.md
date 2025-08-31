# Auth Initialization Checklist

## 🔴 CRITICAL: This checklist MUST be reviewed before ANY auth-related changes

### Pre-Development Checklist
- [ ] Review [`SPEC/learnings/auth_race_conditions_critical.xml`](learnings/auth_race_conditions_critical.xml)
- [ ] Review [`SPEC/learnings/auth_initialization_complete_learnings.md`](learnings/auth_initialization_complete_learnings.md)
- [ ] Understand that **CHAT IS KING** - 90% of value delivery
- [ ] Confirm changes won't affect token decode logic in `frontend/auth/context.tsx`

### Development Checklist

#### Code Requirements
- [ ] Token decode MUST be unconditional when token exists
- [ ] User state MUST be set whenever a valid token is present
- [ ] Auth state changes MUST be atomic (token + user together)
- [ ] Storage events MUST be handled for multi-tab sync
- [ ] Add `[AUTH INIT]` prefix to all auth initialization logs

#### Error Handling
- [ ] Handle malformed tokens gracefully
- [ ] Handle localStorage disabled/blocked
- [ ] Handle network timeouts during auth config fetch
- [ ] Handle expired tokens with proper refresh logic
- [ ] Implement recovery mechanisms for invalid states

#### State Validation
- [ ] Import and use `auth-validation.ts` helpers
- [ ] Add `monitorAuthState()` calls at critical points
- [ ] Validate token/user consistency before rendering protected routes
- [ ] Check for the critical bug: token exists but user is null

### Testing Checklist

#### Required Test Scenarios
- [ ] **Fresh page load with token in localStorage** (CRITICAL)
- [ ] **Page refresh with active session** (CRITICAL)
- [ ] **OAuth callback with existing token**
- [ ] **Multiple rapid token updates**
- [ ] **Component unmount during auth processing**
- [ ] **Expired token handling**
- [ ] **Malformed token in storage**
- [ ] **localStorage disabled or quota exceeded**
- [ ] **Multi-tab synchronization**
- [ ] **Network timeout during auth**

#### Test Files to Run
- [ ] `frontend/tests/auth-initialization.test.tsx`
- [ ] `frontend/tests/auth-initialization-edge-cases.test.tsx`
- [ ] `tests/mission_critical/test_chat_initialization.py`
- [ ] `tests/mission_critical/test_websocket_agent_events_suite.py`

#### Manual Testing
- [ ] Login → Refresh → Chat should remain accessible
- [ ] Close browser → Reopen → Navigate to /chat → Should load
- [ ] Open multiple tabs → Login in one → All tabs authenticated
- [ ] Clear cookies (not localStorage) → Chat should still work
- [ ] Test in Safari private browsing mode
- [ ] Test in Firefox with strict tracking protection

### Code Review Checklist

#### Review Points
- [ ] Token decode is unconditional
- [ ] No assumptions about state correlation
- [ ] Comprehensive error handling
- [ ] Enhanced logging with clear prefixes
- [ ] Auth state validation implemented
- [ ] Test coverage for page refresh scenarios

#### Questions to Ask
- [ ] What happens if the token exists but user is null?
- [ ] How does this handle page refresh?
- [ ] What if localStorage is blocked?
- [ ] How are race conditions prevented?
- [ ] Is the chat interface guaranteed to load?

### Pre-Deployment Checklist

#### Staging Validation
- [ ] Run full auth test suite in staging
- [ ] Test with real OAuth flow
- [ ] Verify WebSocket connects with auth
- [ ] Test page refresh 10 times consecutively
- [ ] Monitor auth state consistency metrics

#### Production Readiness
- [ ] Auth initialization success rate baseline recorded
- [ ] Monitoring alerts configured for token/user mismatches
- [ ] Rollback plan documented
- [ ] Support team briefed on potential issues
- [ ] First 100 sessions will be monitored

### Post-Deployment Checklist

#### Immediate Monitoring (First Hour)
- [ ] Auth init success rate >95%
- [ ] No token/user state mismatches
- [ ] Chat render time <3 seconds
- [ ] No increase in "can't access chat" support tickets
- [ ] WebSocket connection success rate stable

#### 24-Hour Review
- [ ] Review auth error logs
- [ ] Check for any auth recovery attempts
- [ ] Validate no regression in user retention
- [ ] Confirm no infinite refresh loops
- [ ] Document any edge cases discovered

## Red Flags 🚩

**STOP and escalate if you see:**
- Conditional token processing based on state
- Assumptions that token presence means user exists
- Missing page refresh test coverage
- No auth state validation
- Removal of auth logging
- Changes to AuthGuard without comprehensive testing

## Remember

1. **The chat interface is our primary value delivery channel**
2. **Page refresh is a different flow than fresh login**
3. **Never assume state correlation**
4. **Test with existing tokens, not just new auth flows**
5. **When in doubt, add more logging**

## References

- Root Cause Analysis: [`AUTH_INITIALIZATION_FIX_DOCUMENTATION.md`](../AUTH_INITIALIZATION_FIX_DOCUMENTATION.md)
- Complete Learnings: [`SPEC/learnings/auth_initialization_complete_learnings.md`](learnings/auth_initialization_complete_learnings.md)
- Auth Validation Library: [`frontend/lib/auth-validation.ts`](../frontend/lib/auth-validation.ts)
- Test Suites: [`frontend/tests/auth-initialization*.test.tsx`](../frontend/tests/)

---

**This checklist is MANDATORY for all auth-related changes. Skipping items requires explicit justification and approval.**