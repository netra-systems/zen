# GitHub Issue: P0 Critical Auth Service Import Architecture Violation

## Issue Content

**Title:** [BUG] GCP production failures - Backend imports auth_service module instead of using HTTP API

## Impact
**CRITICAL P0:** 84 ERROR logs (8.4% of all logs) causing continuous service restart loops on netra-backend-staging. $500K+ ARR at risk due to WebSocket functionality completely broken.

## Current Behavior
- netra-backend service fails to start with `ModuleNotFoundError: No module named 'auth_service'`
- Service enters restart loop: Container exits with code 3, Master shuts down, restarts
- WebSocket core, authentication integration, and middleware completely non-functional
- Affects complete user chat experience - primary business value delivery blocked

## Expected Behavior
- Services should communicate via HTTP API calls, not direct module imports
- netra-backend should start successfully without requiring auth_service module presence
- WebSocket and authentication should function through service-to-service API communication

## Technical Details

### Root Cause Analysis (Five Whys)
1. **Why:** Service failing to start → Import error: "No module named 'auth_service'"
2. **Why:** auth_service module missing → Separate microservice not available in netra-backend container
3. **Why:** Backend importing directly → Architecture violation - using direct imports instead of API calls
4. **Why:** Direct imports exist → Services should communicate via HTTP/REST, not imports
5. **Why:** Not caught pre-deployment → Deployment process lacks service isolation testing

### Affected Files (Import Violations)
- `/app/netra_backend/app/auth/models.py:22` - `from auth_service.auth_core.database.models import`
- `/app/netra_backend/app/websocket_core/websocket_manager.py:53` - `from auth_service.auth_core.core.token_validator import TokenValidator`
- `/app/netra_backend/app/auth_integration/auth.py:45` (implied by log patterns)
- `/app/netra_backend/app/middleware/gcp_auth_context_middleware.py` (affected in import chain)

### Error Evidence (GCP Logs 2025-09-15T21:38:00Z to 2025-09-15T22:38:00Z)
```
File "/app/netra_backend/app/websocket_core/websocket_manager.py", line 53
from auth_service.auth_core.core.token_validator import TokenValidator
→ ModuleNotFoundError: No module named 'auth_service'
```

### Service Impact
- **Service:** netra-backend-staging (netra-staging project)
- **Revision:** netra-backend-staging-00764-9ct
- **Error Count:** 84 of 1,000 logs (8.4%)
- **Pattern:** Import chain failures across WebSocket, auth, middleware components

## Reproduction Steps
1. Deploy netra-backend service to GCP staging environment
2. Observe service startup logs
3. Service fails with auth_service import errors
4. Container exits with code 3 and restarts

## Required Fix
Replace all direct `auth_service` imports with HTTP client calls to auth service API endpoints:

1. **Update Models:** Replace auth_service model imports with local auth integration models
2. **Update WebSocket Manager:** Replace TokenValidator import with HTTP token validation calls
3. **Update Auth Integration:** Use HTTP API for all auth service communication
4. **Update Middleware:** Remove direct auth_service dependencies

## Business Priority Justification
- **Segment:** Enterprise/Platform
- **Goal:** Stability - Golden Path working (users login → get AI responses)
- **Value Impact:** Complete chat functionality (90% of platform value) currently broken
- **Revenue Impact:** $500K+ ARR dependent on working WebSocket/auth infrastructure

## Related Issues
- Links to similar auth service, architecture, or import violation issues (to be added)

---

## GitHub CLI Commands

### Search for Similar Issues
```bash
# Search for existing auth_service issues
gh issue list --repo netra-systems/netra-apex --state open --search "auth_service" --limit 10

# Search for import architecture issues  
gh issue list --repo netra-systems/netra-apex --state open --search "import OR architecture" --limit 10

# Search for WebSocket issues
gh issue list --repo netra-systems/netra-apex --state open --search "websocket" --limit 10
```

### Create New Issue (if no duplicates found)
```bash
gh issue create --repo netra-systems/netra-apex \
  --title "[BUG] GCP production failures - Backend imports auth_service module instead of using HTTP API" \
  --body "$(cat <<'EOF'
## Impact
**CRITICAL P0:** 84 ERROR logs (8.4% of all logs) causing continuous service restart loops on netra-backend-staging. $500K+ ARR at risk due to WebSocket functionality completely broken.

## Current Behavior
- netra-backend service fails to start with `ModuleNotFoundError: No module named 'auth_service'`
- Service enters restart loop: Container exits with code 3, Master shuts down, restarts
- WebSocket core, authentication integration, and middleware completely non-functional
- Affects complete user chat experience - primary business value delivery blocked

## Expected Behavior
- Services should communicate via HTTP API calls, not direct module imports
- netra-backend should start successfully without requiring auth_service module presence
- WebSocket and authentication should function through service-to-service API communication

## Technical Details

### Root Cause Analysis (Five Whys)
1. **Why:** Service failing to start → Import error: "No module named 'auth_service'"
2. **Why:** auth_service module missing → Separate microservice not available in netra-backend container
3. **Why:** Backend importing directly → Architecture violation - using direct imports instead of API calls
4. **Why:** Direct imports exist → Services should communicate via HTTP/REST, not imports
5. **Why:** Not caught pre-deployment → Deployment process lacks service isolation testing

### Affected Files (Import Violations)
- `/app/netra_backend/app/auth/models.py:22` - `from auth_service.auth_core.database.models import`
- `/app/netra_backend/app/websocket_core/websocket_manager.py:53` - `from auth_service.auth_core.core.token_validator import TokenValidator`
- `/app/netra_backend/app/auth_integration/auth.py:45` (implied by log patterns)
- `/app/netra_backend/app/middleware/gcp_auth_context_middleware.py` (affected in import chain)

### Error Evidence (GCP Logs 2025-09-15T21:38:00Z to 2025-09-15T22:38:00Z)
```
File "/app/netra_backend/app/websocket_core/websocket_manager.py", line 53
from auth_service.auth_core.core.token_validator import TokenValidator
→ ModuleNotFoundError: No module named 'auth_service'
```

### Service Impact
- **Service:** netra-backend-staging (netra-staging project)
- **Revision:** netra-backend-staging-00764-9ct
- **Error Count:** 84 of 1,000 logs (8.4%)
- **Pattern:** Import chain failures across WebSocket, auth, middleware components

## Reproduction Steps
1. Deploy netra-backend service to GCP staging environment
2. Observe service startup logs
3. Service fails with auth_service import errors
4. Container exits with code 3 and restarts

## Required Fix
Replace all direct `auth_service` imports with HTTP client calls to auth service API endpoints:

1. **Update Models:** Replace auth_service model imports with local auth integration models
2. **Update WebSocket Manager:** Replace TokenValidator import with HTTP token validation calls
3. **Update Auth Integration:** Use HTTP API for all auth service communication
4. **Update Middleware:** Remove direct auth_service dependencies

## Business Priority Justification
- **Segment:** Enterprise/Platform
- **Goal:** Stability - Golden Path working (users login → get AI responses)
- **Value Impact:** Complete chat functionality (90% of platform value) currently broken
- **Revenue Impact:** $500K+ ARR dependent on working WebSocket/auth infrastructure
EOF
)" \
  --label "P0,bug,auth,claude-code-generated-issue"
```

### Update Existing Issue (if duplicate found)
```bash
# Replace ISSUE_NUMBER with actual issue number if duplicate exists
gh issue comment ISSUE_NUMBER --repo netra-systems/netra-apex --body "$(cat <<'EOF'
**Status Update:** CRITICAL P0 escalation - 84 ERROR logs confirmed in GCP staging

**Latest Evidence:** Service restart loops caused by auth_service import violations
- Error count: 84 of 1,000 logs (8.4%) 
- Timeline: 2025-09-15T21:38:00Z to 2025-09-15T22:38:00Z
- Impact: Complete WebSocket/auth functionality broken

**Root Cause Confirmed:** Architecture violation - direct module imports instead of HTTP API calls
- File: `/app/netra_backend/app/auth/models.py:22`
- File: `/app/netra_backend/app/websocket_core/websocket_manager.py:53`

**Next Action:** Replace all auth_service imports with HTTP client calls to restore service functionality
EOF
)"
```

---

## Safety Considerations Met
- ✅ READ-ONLY operations only (no code changes, infrastructure modifications, or deployments)
- ✅ GitHub issue operations only (create, update, link)
- ✅ No direct auth_service or backend service modifications
- ✅ Complete documentation of findings for safe handoff

## Expected Deliverables
1. **New GitHub Issue Created:** Following GITHUB_STYLE_GUIDE.md format with P0/bug/auth/claude-code-generated-issue labels
2. **OR Existing Issue Updated:** If duplicate found, updated with latest log evidence and escalation
3. **Related Issues Linked:** Any similar auth, import, or architecture issues cross-referenced
4. **Action Summary:** Documentation of GitHub operations performed and issue URL(s)