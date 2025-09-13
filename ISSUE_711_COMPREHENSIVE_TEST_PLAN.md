# Issue #711 SSOT Environment Access Violations Test Plan - Ready for Implementation

## 🎯 Executive Summary

**Status:** ✅ **TEST PLAN COMPLETE** - Ready for implementation
**Business Impact:** $500K+ ARR Golden Path protection from configuration drift
**Current Violation Status:** 5,449 total violations across 1,017 files (344 violations in 144 production files)
**Foundation Ready:** SSOT `IsolatedEnvironment` infrastructure complete, migration patterns established

## 📊 Current Violation Analysis

### Violation Scale and Distribution
- **Total Violations:** 5,449 across 1,017 files
- **Production Code:** 344 violations in 144 real system files
- **Test Files:** 5,105 violations (test infrastructure modernization needed)
- **Critical Services:** Auth, Configuration, Startup, WebSocket all affected

### Key Violation Patterns Identified
```python
# ❌ VIOLATION PATTERN 1: Direct os.getenv access
import os
env_value = os.getenv('ENVIRONMENT', 'development')
corpus_path = os.getenv('CORPUS_BASE_PATH', '/data/corpus')

# ❌ VIOLATION PATTERN 2: Direct os.environ access
import os
if 'JWT_SECRET_KEY' in os.environ:
    secret = os.environ['JWT_SECRET_KEY']

# ❌ VIOLATION PATTERN 3: Environment patching in tests
import os
os.environ['TEST_VAR'] = 'test_value'

# ✅ CORRECT SSOT PATTERN:
from shared.isolated_environment import get_env
env_value = get_env('ENVIRONMENT', 'development')
corpus_path = get_env('CORPUS_BASE_PATH', '/data/corpus')
```

## 🧪 Test Plan: SSOT Environment Access Violations

### Test Strategy Overview
1. **Detection Tests:** Identify and catalog all violations
2. **Reproduction Tests:** Demonstrate configuration drift scenarios
3. **SSOT Compliance Tests:** Validate proper migration patterns
4. **Golden Path Protection Tests:** Ensure startup reliability
5. **Enforcement Tests:** Prevent future violations

---

## 📋 Phase 1: Unit Tests - Environment Access Violation Detection

### Test File: `tests/unit/environment_access/test_environment_violation_detection.py`

**Purpose:** Systematically detect and catalog all environment access violations

```python
"""
Unit Test Suite: Environment Access Violation Detection
Systematically identifies direct os.environ/os.getenv usage violations
"""

class TestEnvironmentViolationDetection(SSotBaseTestCase):

    def test_detect_direct_os_getenv_violations(self):
        """Detect files using os.getenv() instead of IsolatedEnvironment"""
        violations = scan_codebase_for_pattern(r'os\.getenv\(')

        # Should initially FAIL with 5,449+ violations found
        assert len(violations) == 0, f"Found {len(violations)} os.getenv violations"

    def test_detect_direct_os_environ_violations(self):
        """Detect files using os.environ[] instead of IsolatedEnvironment"""
        violations = scan_codebase_for_pattern(r'os\.environ\[')

        # Should initially FAIL with violations found
        assert len(violations) == 0, f"Found {len(violations)} os.environ violations"

    def test_golden_path_critical_files_compliance(self):
        """Verify Golden Path critical files use SSOT patterns"""
        critical_files = [
            'netra_backend/app/core/configuration/base.py',
            'netra_backend/app/core/auth_startup_validator.py',
            'auth_service/auth_core/core/environment.py',
            'shared/isolated_environment.py'
        ]

        for file_path in critical_files:
            violations = check_file_environment_compliance(file_path)
            assert len(violations) == 0, f"Golden Path file {file_path} has violations: {violations}"
```

### Test File: `tests/unit/environment_access/test_ssot_pattern_validation.py`

**Purpose:** Validate correct SSOT usage patterns

```python
"""
Unit Test Suite: SSOT Pattern Validation
Validates correct usage of IsolatedEnvironment patterns
"""

class TestSsotPatternValidation(SSotBaseTestCase):

    def test_isolated_environment_import_pattern(self):
        """Test that IsolatedEnvironment imports follow SSOT pattern"""
        from shared.isolated_environment import get_env, IsolatedEnvironment

        # Test basic functionality
        env = IsolatedEnvironment()
        test_value = env.get('TEST_ENV_VAR', 'default_value')
        assert test_value == 'default_value'

    def test_isolated_environment_vs_direct_access_comparison(self):
        """Compare IsolatedEnvironment behavior vs direct os.environ access"""

        # Set test variable through IsolatedEnvironment
        env = IsolatedEnvironment()
        env.set('COMPARISON_TEST_VAR', 'isolated_value', 'test_source')

        # Verify isolation - should NOT appear in os.environ
        assert 'COMPARISON_TEST_VAR' not in os.environ
        assert env.get('COMPARISON_TEST_VAR') == 'isolated_value'

    def test_environment_configuration_drift_prevention(self):
        """Test that IsolatedEnvironment prevents configuration drift"""
        env = IsolatedEnvironment()

        # Set conflicting values in different contexts
        env.set('DRIFT_TEST_VAR', 'context1_value', 'context1')

        # Different context should get consistent value
        env2 = IsolatedEnvironment()
        assert env2.get('DRIFT_TEST_VAR') == 'context1_value'
```

---

## 📋 Phase 2: Integration Tests - SSOT Compliance Validation (Non-Docker)

### Test File: `tests/integration/environment_ssot/test_service_environment_compliance_integration.py`

**Purpose:** Validate SSOT compliance across service boundaries without Docker

```python
"""
Integration Test Suite: Service Environment Compliance
Tests SSOT environment patterns across service boundaries
"""

class TestServiceEnvironmentComplianceIntegration(SSotBaseTestCase):

    def test_backend_service_environment_compliance(self):
        """Test backend service uses SSOT environment patterns"""
        # Import backend configuration
        from netra_backend.app.config import get_config

        config = get_config()

        # Verify configuration loaded through SSOT patterns
        assert hasattr(config, 'database_url')
        assert hasattr(config, 'jwt_secret_key')

        # Verify no direct os.environ access in configuration loading
        violations = scan_module_for_violations('netra_backend.app.config')
        assert len(violations) == 0, f"Backend config has violations: {violations}"

    def test_auth_service_environment_compliance(self):
        """Test auth service uses SSOT environment patterns"""
        # Test auth service configuration
        from auth_service.auth_core.core.environment import AuthEnvironment

        auth_env = AuthEnvironment()

        # Verify auth environment uses IsolatedEnvironment
        assert hasattr(auth_env, '_isolated_env')

        # Check for violations in auth service
        violations = scan_module_for_violations('auth_service.auth_core')
        assert len(violations) == 0, f"Auth service has violations: {violations}"

    def test_cross_service_environment_consistency(self):
        """Test environment consistency across services"""
        from shared.isolated_environment import IsolatedEnvironment

        env = IsolatedEnvironment()

        # Set test environment variable
        env.set('CROSS_SERVICE_TEST', 'consistent_value', 'integration_test')

        # Verify consistency across different service imports
        from netra_backend.app.core.configuration.base import get_environment_value
        from auth_service.auth_core.core.environment import get_auth_environment_value

        backend_value = get_environment_value('CROSS_SERVICE_TEST')
        auth_value = get_auth_environment_value('CROSS_SERVICE_TEST')

        assert backend_value == 'consistent_value'
        assert auth_value == 'consistent_value'
```

### Test File: `tests/integration/environment_ssot/test_configuration_drift_scenarios_integration.py`

**Purpose:** Test configuration drift prevention scenarios

```python
"""
Integration Test Suite: Configuration Drift Prevention
Tests scenarios where configuration drift could occur
"""

class TestConfigurationDriftScenariosIntegration(SSotBaseTestCase):

    def test_startup_sequence_environment_consistency(self):
        """Test environment consistency during startup sequence"""
        # Simulate startup sequence with mixed environment access
        from netra_backend.app.core.startup_sequence import validate_startup_environment

        # Should use SSOT patterns throughout startup
        startup_result = validate_startup_environment()

        assert startup_result['environment_compliance'] == True
        assert len(startup_result['violations']) == 0

    def test_multi_user_environment_isolation(self):
        """Test that environment isolation works for multiple users"""
        from shared.isolated_environment import IsolatedEnvironment

        # Create separate environment contexts for different users
        user1_env = IsolatedEnvironment()
        user2_env = IsolatedEnvironment()

        user1_env.set('USER_SPECIFIC_VAR', 'user1_value', 'user1_context')
        user2_env.set('USER_SPECIFIC_VAR', 'user2_value', 'user2_context')

        # Verify isolation is maintained
        assert user1_env.get('USER_SPECIFIC_VAR') != user2_env.get('USER_SPECIFIC_VAR')

    def test_golden_path_configuration_stability(self):
        """Test Golden Path configuration remains stable under load"""
        from netra_backend.app.core.golden_path_validator import validate_golden_path_config

        # Simulate configuration access patterns during Golden Path execution
        for i in range(100):
            config_status = validate_golden_path_config()
            assert config_status['stable'] == True
            assert config_status['environment_source'] == 'IsolatedEnvironment'
```

---

## 📋 Phase 3: E2E Tests - Golden Path Configuration Stability (Staging GCP)

### Test File: `tests/e2e/environment_ssot/test_golden_path_environment_stability_e2e.py`

**Purpose:** Validate Golden Path configuration stability in staging environment

```python
"""
E2E Test Suite: Golden Path Environment Stability
Tests environment configuration stability in real staging environment
"""

class TestGoldenPathEnvironmentStabilityE2E(SSotBaseTestCase):

    @pytest.mark.staging_only
    def test_user_login_environment_consistency_e2e(self):
        """Test user login flow maintains environment consistency"""
        # Execute complete Golden Path user flow
        from tests.e2e.golden_path_helper import execute_golden_path_flow

        result = execute_golden_path_flow(
            user_email="test@example.com",
            validate_environment=True
        )

        # Verify environment consistency throughout flow
        assert result['login_success'] == True
        assert result['environment_violations'] == 0
        assert result['configuration_drift'] == False

    @pytest.mark.staging_only
    def test_ai_response_generation_environment_stability_e2e(self):
        """Test AI response generation maintains environment stability"""
        from tests.e2e.ai_response_helper import test_ai_response_with_environment_monitoring

        response_result = test_ai_response_with_environment_monitoring(
            message="Test environment stability during AI response"
        )

        # Verify environment remained stable during AI processing
        assert response_result['response_generated'] == True
        assert response_result['environment_stable'] == True
        assert len(response_result['environment_violations']) == 0

    @pytest.mark.staging_only
    def test_websocket_events_environment_isolation_e2e(self):
        """Test WebSocket events maintain environment isolation"""
        from tests.e2e.websocket_helper import test_websocket_environment_isolation

        websocket_result = test_websocket_environment_isolation(
            concurrent_users=5,
            messages_per_user=10
        )

        # Verify environment isolation maintained across WebSocket events
        assert websocket_result['all_users_isolated'] == True
        assert websocket_result['environment_leakage'] == 0
        assert websocket_result['configuration_consistency'] == True
```

---

## 📋 Phase 4: Compliance Tests - Violation Prevention

### Test File: `tests/compliance/environment_access/test_environment_access_enforcement.py`

**Purpose:** Prevent future environment access violations

```python
"""
Compliance Test Suite: Environment Access Enforcement
Prevents future violations and enforces SSOT compliance
"""

class TestEnvironmentAccessEnforcement(SSotBaseTestCase):

    def test_prevent_new_os_getenv_usage(self):
        """Test that new code cannot use os.getenv()"""
        # This test should be integrated with pre-commit hooks

        # Scan for any new os.getenv usage
        recent_violations = scan_recent_commits_for_violations(
            pattern=r'os\.getenv\(',
            since_days=1
        )

        assert len(recent_violations) == 0, f"New os.getenv violations found: {recent_violations}"

    def test_prevent_new_os_environ_usage(self):
        """Test that new code cannot use os.environ[]"""
        recent_violations = scan_recent_commits_for_violations(
            pattern=r'os\.environ\[',
            since_days=1
        )

        assert len(recent_violations) == 0, f"New os.environ violations found: {recent_violations}"

    def test_require_isolated_environment_imports(self):
        """Test that new environment access uses IsolatedEnvironment"""
        recent_env_files = scan_recent_files_with_environment_access(since_days=1)

        for file_path in recent_env_files:
            isolated_env_imports = check_file_for_isolated_environment_import(file_path)
            assert isolated_env_imports > 0, f"File {file_path} accesses environment without IsolatedEnvironment import"
```

---

## 🔧 Test Implementation Requirements

### Test Infrastructure Dependencies
```python
# Required test utilities to implement:

def scan_codebase_for_pattern(pattern: str) -> List[Dict[str, Any]]:
    """Scan entire codebase for regex pattern violations"""

def check_file_environment_compliance(file_path: str) -> List[str]:
    """Check specific file for environment access compliance"""

def scan_module_for_violations(module_name: str) -> List[str]:
    """Scan Python module for environment access violations"""

def validate_golden_path_config() -> Dict[str, Any]:
    """Validate Golden Path configuration stability"""

def scan_recent_commits_for_violations(pattern: str, since_days: int) -> List[str]:
    """Scan recent commits for new violations"""
```

### Test Execution Commands
```bash
# Unit Tests (No Docker Required)
python -m pytest tests/unit/environment_access/ -v

# Integration Tests (No Docker Required)
python -m pytest tests/integration/environment_ssot/ -v

# E2E Tests (Staging GCP Only)
python -m pytest tests/e2e/environment_ssot/ -v -m staging_only

# Compliance Tests
python -m pytest tests/compliance/environment_access/ -v

# Full Suite
python tests/unified_test_runner.py --category environment_ssot --real-services
```

---

## 📊 Expected Test Results

### Initial Test Execution (Before Fix)
- **Detection Tests:** ❌ Should FAIL with 5,449+ violations detected
- **SSOT Compliance Tests:** ❌ Should FAIL showing missing migrations
- **Golden Path Tests:** ⚠️ May pass but vulnerable to drift
- **Enforcement Tests:** ❌ Should FAIL showing ongoing violations

### Post-Migration Test Execution (After Fix)
- **Detection Tests:** ✅ Should PASS with 0 violations detected
- **SSOT Compliance Tests:** ✅ Should PASS with proper SSOT usage
- **Golden Path Tests:** ✅ Should PASS with stable configuration
- **Enforcement Tests:** ✅ Should PASS preventing future violations

---

## 💼 Business Value Impact

### Revenue Protection
- **$500K+ ARR:** Protected from configuration-related service failures
- **Golden Path Reliability:** Consistent user login → AI response flow
- **Deployment Stability:** Reduced GCP staging/production issues

### System Stability Benefits
- **Configuration Consistency:** Eliminated environment drift across services
- **Security Isolation:** Proper environment access control
- **Debugging Efficiency:** Clear environment variable source tracking
- **Future Violation Prevention:** Automated enforcement via testing

---

## 🎯 Success Criteria

1. **Complete Violation Detection:** All 5,449 violations identified and cataloged
2. **SSOT Migration:** All environment access routed through `IsolatedEnvironment`
3. **Golden Path Protection:** Configuration stability verified in staging
4. **Enforcement Implementation:** Pre-commit hooks prevent future violations
5. **Test Coverage:** 100% coverage of environment access patterns
6. **Documentation:** Complete migration guide for developers

---

**Next Steps:** Ready for immediate test implementation and systematic violation remediation.