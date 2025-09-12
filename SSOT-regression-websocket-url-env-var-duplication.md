# SSOT-regression-websocket-url-env-var-duplication

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/507
**Priority:** P0 (Critical/Blocking - Golden Path Broken)
**Created:** 2025-09-11

## Problem Statement
Duplicate and conflicting WebSocket URL environment variables create configuration confusion that directly blocks the Golden Path user flow (users login → get AI responses):

- `NEXT_PUBLIC_WS_URL` (canonical)
- `NEXT_PUBLIC_WEBSOCKET_URL` (competing/duplicate)

## Business Impact
- **Golden Path Blocking:** WebSocket connection failures prevent AI responses
- **Revenue Risk:** Core chat functionality (90% of platform value) affected  
- **Configuration Chaos:** Developers unsure which variable to use
- **Environment Inconsistency:** Different vars used across dev/staging/prod

## Work Progress Tracker

### ✅ Step 0: SSOT Audit Complete
- [x] Identified critical WebSocket URL environment variable duplication
- [x] Created GitHub issue #507
- [x] Created local tracking file

### ⏳ Step 1: Discover and Plan Tests (IN PROGRESS)
- [ ] 1.1 Discover existing WebSocket configuration tests
- [ ] 1.2 Plan new SSOT validation tests

### ⏳ Step 2: Execute Test Plan (PENDING)
- [ ] Create new SSOT tests for WebSocket configuration
- [ ] Validate test execution (non-docker)

### ⏳ Step 3: Plan SSOT Remediation (PENDING) 
- [ ] Plan consolidation to single canonical variable
- [ ] Plan elimination of duplicate references

### ⏳ Step 4: Execute SSOT Remediation (PENDING)
- [ ] Implement WebSocket URL SSOT consolidation
- [ ] Update all references to use canonical variable

### ⏳ Step 5: Test Fix Loop (PENDING)
- [ ] Run all tests and fix any failures
- [ ] Validate Golden Path WebSocket connectivity

### ⏳ Step 6: PR and Closure (PENDING)
- [ ] Create PR linking to issue #507
- [ ] Ensure all acceptance criteria met

## Files Identified for Remediation
- Frontend WebSocket connection logic
- Environment configuration files (.env, .env.example, etc.)
- Docker compose configurations
- Deployment scripts
- Any hardcoded WebSocket URL references

## Test Strategy
- Focus on unit, integration (non-docker), and e2e staging GCP tests
- ~20% new SSOT validation tests, ~60% updating existing tests, ~20% validating fixes
- Ensure Golden Path WebSocket connectivity tests pass

## Acceptance Criteria
- [ ] Single WebSocket URL environment variable across codebase
- [ ] All WebSocket connections use canonical configuration (`NEXT_PUBLIC_WS_URL`)
- [ ] Golden Path WebSocket connectivity restored
- [ ] Tests validate WebSocket connection stability
- [ ] No configuration conflicts between environments

## Notes
- This is a P0 critical issue that directly impacts $500K+ ARR
- Golden Path must remain functional throughout remediation
- All changes must be atomic and not introduce breaking changes