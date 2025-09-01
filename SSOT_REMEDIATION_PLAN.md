# SSOT Violations Remediation Plan

**Priority:** CRITICAL  
**Timeline:** Immediate action required  
**Business Justification:** Restore test suite functionality and system stability

## Phase 1: Emergency Fixes (Immediate - 2 hours)

### Task 1.1: Fix Test Import Errors
**Files to Fix:**
```python
# netra_backend/tests/integration/critical_paths/test_session_persistence_restart.py
# REPLACE:
from netra_backend.app.auth_integration.auth import create_access_token, validate_token_jwt
# WITH:
from netra_backend.app.clients.auth_client_core import AuthServiceClient
auth_client = AuthServiceClient()
# Use: await auth_client.create_token(user_id, email)

# tests/conftest.py:439
# REPLACE:
from netra_backend.app.auth_integration.auth import create_access_token
# WITH:
from tests.e2e.jwt_token_helpers import JWTTokenHelper
# Use the test helper for test token generation

# tests/e2e/helpers/websocket/websocket_test_helpers.py:299
# Similar fix - use JWTTokenHelper for tests
```

### Task 1.2: Remove Startup Module References
**Files to Clean:**
```bash
# Comment out or remove imports in:
- dev_launcher/launcher.py:41
- All files in dev_launcher/tests/ that import startup_validator
- Update unified_test_runner.py to skip these modules
```

---

## Phase 2: SSOT Consolidation (Day 1 - 4 hours)

### Task 2.1: Consolidate Authentication Functions
**Action:** Remove all duplicate create_access_token implementations

```python
# KEEP ONLY:
auth_service/auth_core/jwt_handler.py - The canonical implementation

# DELETE/REFACTOR these to use auth_client:
- netra_backend/app/core/unified/jwt_validator.py:157
- netra_backend/app/services/token_service.py:78  
- netra_backend/app/services/security_service.py:61

# All should delegate to:
from netra_backend.app.clients.auth_client_core import AuthServiceClient
auth_client = AuthServiceClient()
token = await auth_client.create_token(user_id, email)
```

### Task 2.2: Fix Environment Access Pattern
**Action:** Replace direct os.environ with IsolatedEnvironment

```python
# WRONG:
import os
db_url = os.environ.get("DATABASE_URL")

# CORRECT:
from shared.isolated_environment import IsolatedEnvironment
env = IsolatedEnvironment.get_instance()
db_url = env.get("DATABASE_URL")
```

**Priority Files:**
1. netra_backend/app/core/logging_config.py
2. netra_backend/app/routes/health_check.py
3. All test files using os.environ directly

---

## Phase 3: Test Infrastructure Update (Day 2 - 4 hours)

### Task 3.1: Update Test Helpers
**Create canonical test token generator:**

```python
# tests/helpers/auth_test_utils.py
from tests.e2e.jwt_token_helpers import JWTTokenHelper

class TestAuthHelper:
    """Canonical test authentication helper - SSOT for test tokens"""
    
    def __init__(self):
        self.jwt_helper = JWTTokenHelper()
    
    def create_test_token(self, user_id: str, email: str):
        """Create test token for integration tests"""
        return self.jwt_helper.create_access_token(user_id, email)
```

### Task 3.2: Fix Integration Test Setup
**Update all integration tests to use proper auth patterns:**

```python
# Pattern for integration tests:
async def test_with_auth():
    # For real service tests:
    auth_client = AuthServiceClient()
    token = await auth_client.create_token("test_user", "test@example.com")
    
    # For unit tests:
    from tests.helpers.auth_test_utils import TestAuthHelper
    helper = TestAuthHelper()
    token = helper.create_test_token("test_user", "test@example.com")
```

---

## Phase 4: Automated Compliance (Day 3 - 2 hours)

### Task 4.1: Create SSOT Compliance Checker
```python
# scripts/check_ssot_compliance.py
"""
Check for SSOT violations:
1. No duplicate function implementations
2. No direct os.environ access
3. No cross-service imports
4. All auth through auth_client
"""
```

### Task 4.2: Add Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-ssot
      name: Check SSOT Compliance
      entry: python scripts/check_ssot_compliance.py
      language: python
      files: \.py$
```

---

## Implementation Order

### Day 1 - Morning (2 hours):
1. ✅ Fix critical test imports (Task 1.1)
2. ✅ Remove startup module refs (Task 1.2)
3. ✅ Verify tests can run

### Day 1 - Afternoon (4 hours):
1. ✅ Consolidate auth functions (Task 2.1)
2. ✅ Fix environment access (Task 2.2)
3. ✅ Run integration tests

### Day 2 (4 hours):
1. ✅ Update test helpers (Task 3.1)
2. ✅ Fix integration tests (Task 3.2)
3. ✅ Full test suite validation

### Day 3 (2 hours):
1. ✅ Create compliance checker (Task 4.1)
2. ✅ Add pre-commit hooks (Task 4.2)
3. ✅ Document patterns

---

## Success Criteria

### Immediate Success (End of Day 1):
- [ ] Integration tests run without ImportError
- [ ] No references to removed modules
- [ ] Auth functions consolidated

### Short-term Success (End of Day 2):
- [ ] All tests passing
- [ ] No direct os.environ access in production code
- [ ] Service boundaries enforced

### Long-term Success (End of Week):
- [ ] Automated SSOT compliance checking
- [ ] Zero SSOT violations in codebase
- [ ] Clear documentation of patterns

---

## Risk Mitigation

### Risk 1: Breaking Production
**Mitigation:** Test all changes locally with docker-compose before deploying

### Risk 2: Test Regression
**Mitigation:** Run full test suite after each phase

### Risk 3: Developer Confusion
**Mitigation:** Update documentation immediately with correct patterns

---

## Validation Checklist

After each phase, validate:
- [ ] `python unified_test_runner.py --docker-dedicated` runs
- [ ] No ImportError in test output
- [ ] Service boundaries maintained
- [ ] Auth flows working correctly

---

## Emergency Rollback Plan

If issues arise:
1. Revert commits to last known good state
2. Apply minimal fixes only for test execution
3. Schedule longer refactoring window

**CRITICAL:** Start with Phase 1 immediately to unblock testing!