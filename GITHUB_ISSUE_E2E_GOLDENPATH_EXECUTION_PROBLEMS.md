# GitHub Issue: E2E Golden Path Tests - Execution and Validation Issues

## Issue Creation Summary

**Title:** `[BUG] E2E Golden Path tests fail due to staging infrastructure HTTP 503 errors`

**Labels:** `P0`, `bug`, `infrastructure-dependency`, `claude-code-generated-issue`

**Priority:** P0 (Critical/Blocking) - $500K+ ARR at risk

## Issue Body

```markdown
## Impact
Complete staging infrastructure failure preventing Golden Path validation and enterprise customer acceptance testing. All E2E tests abort with HTTP 503 errors affecting $500K+ ARR.

## Current Behavior
- All staging services (backend, auth, websocket) return HTTP 503 Service Unavailable
- Response times exceed 10+ seconds before timeout
- E2E test runner requires approval for all commands preventing automated validation
- Test execution aborts within 4 minutes due to infrastructure unavailability

## Expected Behavior
- Staging services respond with HTTP 200/201 status codes within <2 seconds
- E2E golden path tests execute without command approval requirements
- Complete user journey (login → AI response) validates successfully
- Test runner executes all 466+ available E2E tests systematically

## Reproduction Steps
1. Run: `python tests/unified_test_runner.py --env staging --category smoke --real-services`
2. Observe: HTTP 503 errors from all staging endpoints
3. Run: `python tests/e2e/staging/test_staging_connectivity_validation.py`
4. Observe: Connection timeouts and 503 responses
5. Attempt: WebSocket connection to `wss://api.staging.netrasystems.ai/ws`
6. Result: Connection rejected with HTTP 503

## Technical Details
- **Environment:** GCP Staging (Cloud Run services)
- **Affected Services:**
  - Backend: `https://api.staging.netrasystems.ai` (HTTP 503, 10.034s response time)
  - Auth: `https://auth.staging.netrasystems.ai` (HTTP 503, 10.412s response time)
  - WebSocket: `wss://api.staging.netrasystems.ai/ws` (Connection rejected)
- **Test Results:** 0-25% success rate across all test suites
- **Business Impact:** Complete Golden Path failure, $500K+ ARR at risk
- **Error Pattern:** All services consistently return 503 Service Unavailable
- **Infrastructure:** VPC connector `staging-connector` may have connectivity issues

## Root Cause Analysis
**Primary Issue:** VPC Connector connectivity failure between Cloud Run and Cloud SQL preventing service initialization

**Supporting Evidence:**
- Services start but fail during database connectivity phase
- Health endpoints return 503 instead of degraded mode responses
- Container logs suggest startup sequence termination during Phase 3 (DATABASE)
- Emergency bypass implementation has termination flaw (lines 486 & 513 in smd.py)

## Immediate Actions Required
1. **🚨 Emergency:** Verify VPC connector `staging-connector` status in us-central1
2. **🚨 Emergency:** Check Cloud SQL connectivity for instances:
   - `netra-staging:us-central1:staging-shared-postgres`
   - `netra-staging:us-central1:netra-postgres`
3. **🚨 Emergency:** Fix emergency bypass termination flaw in `smd.py`
4. **🚨 Emergency:** Implement graceful degradation for health endpoints

## Test Command Approval Issues
E2E test execution requires manual approval for basic commands preventing automated golden path validation:
- `gh issue list` commands fail with "requires approval"
- `gh auth status` blocked by approval requirement
- Unified test runner may need approval for staging connectivity tests

## Related Files
- `/netra_backend/app/core/smd.py` (lines 475-513) - Emergency bypass implementation
- `/tests/e2e/staging/test_staging_connectivity_validation.py` - Infrastructure validation
- `/tests/e2e/staging/test_staging_health_validation.py` - Service health checks
- `/tests/unified_test_runner.py` - Main test execution entry point
- `/terraform-gcp-staging/vpc-connector.tf` - VPC connector configuration

## Success Criteria
- [ ] All staging services respond with HTTP 200 status
- [ ] Response times <2 seconds for all endpoints
- [ ] Complete Golden Path user journey validates successfully
- [ ] E2E test runner executes without command approval requirements
- [ ] VPC connector and database connectivity operational
- [ ] Emergency bypass properly supports graceful degradation
```

## Related Issues to Check/Create

Based on analysis, these are the key issue areas that need GitHub issues:

### 1. **Infrastructure Issues** (Most Critical)
- **Title:** `[CRITICAL] Staging infrastructure HTTP 503 - VPC connector connectivity failure`
- **Priority:** P0
- **Focus:** VPC connector, Cloud SQL connectivity, service availability

### 2. **Test Framework Issues**
- **Title:** `[BUG] E2E test runner requires command approval preventing automated execution`
- **Priority:** P1
- **Focus:** Test runner approval requirements, automation barriers

### 3. **Emergency Bypass Issues**
- **Title:** `[BUG] SMD emergency bypass terminates startup sequence prematurely`
- **Priority:** P1
- **Focus:** Emergency bypass implementation flaw in `smd.py`

### 4. **Test Infrastructure Imports**
- **Title:** `[BUG] E2E test collection failures - missing imports and SSOT violations`
- **Priority:** P2
- **Focus:** Test framework import errors, SSOT compliance

## GitHub Commands to Execute

Since GitHub CLI requires approval, these commands should be run by user:

```bash
# Search for existing related issues
gh issue list --search "goldenpath OR golden path OR e2e test OR staging infrastructure OR HTTP 503"
gh issue list --search "test failure OR test runner OR VPC connector"

# Create the main issue (if not exists)
gh issue create --title "[BUG] E2E Golden Path tests fail due to staging infrastructure HTTP 503 errors" --body-file GITHUB_ISSUE_E2E_GOLDENPATH_EXECUTION_PROBLEMS.md --label "P0,bug,infrastructure-dependency,claude-code-generated-issue"

# Check issue status
gh issue list --state open --label "P0"
gh issue view [ISSUE_NUMBER]
```

## Next Steps

1. **User should run GitHub CLI commands** to search for existing issues
2. **Create missing issues** using the content above
3. **Link related issues** if multiple issues exist
4. **Update existing issues** if similar problems are already tracked
5. **Prioritize infrastructure remediation** (P0) before test framework fixes (P1-P2)

## Business Impact Summary

- **Revenue at Risk:** $500K+ ARR
- **Customer Impact:** Cannot demonstrate Golden Path to enterprise customers
- **Technical Impact:** Complete staging environment unavailable for validation
- **Urgency:** P0 Emergency - Infrastructure team engagement required immediately

---

**Created:** 2025-09-16
**Status:** Ready for GitHub issue creation
**Priority:** P0 Emergency Infrastructure Response Required