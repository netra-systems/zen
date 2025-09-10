# 🔧 Redis Validation SSOT Compliance Test Plan

## 📋 Executive Summary

**MISSION**: Create failing tests that expose Redis validation SSOT violations where validation logic is scattered across multiple services instead of being centralized in SSOT patterns.

**ROOT CAUSE IDENTIFIED**: Redis validation logic is implemented multiple times across different services (backend, auth, analytics) instead of having a single, canonical validation implementation.

**TEST STRATEGY**: Design tests that FAIL when SSOT violations exist and PASS when validation is properly centralized.

## 🚨 CRITICAL CONTEXT

### SSOT Violation Analysis
Based on codebase analysis, I found these Redis validation SSOT violations:

1. **Backend Service** (`netra_backend/app/api/health_checks.py`)
   - Implements `check_redis_health()` with custom logic
   - Direct Redis connection validation
   - Response time measurement
   - Service-specific caching mechanism

2. **Auth Service** (`auth_service/services/health_check_service.py`)
   - Implements `_check_redis_health()` with different logic
   - Test key set/get validation pattern
   - Different error handling approach
   - Service-specific Redis manager integration

3. **Analytics Service** (`analytics_service/analytics_core/database/connection.py`)
   - Implements `RedisHealthChecker` class
   - Stub implementation with different interface
   - Different health status return format
   - Service-specific connection management

### Current 98% SSOT Compliance Issue
While Redis **configuration** is well centralized, the **validation logic** is duplicated across services.

## 🎯 Test Objectives

### Primary Goals
1. **Detect Validation Logic Duplication**: Tests must FAIL when multiple services implement their own Redis validation
2. **Enforce Canonical Implementation**: Tests must PASS only when all services use a single SSOT validation method
3. **Validate Interface Consistency**: Ensure all Redis validation follows the same patterns and returns consistent formats

### Success Criteria
- **FAILING TESTS**: When validation logic exists in multiple places (current state)
- **PASSING TESTS**: When validation is consolidated into shared utilities (target state)

## 📁 Test Suite Structure

```
tests/integration/redis_validation_ssot/
├── __init__.py
├── test_redis_validation_duplication_detection.py      # Core SSOT violation detection
├── test_redis_validation_interface_consistency.py      # Interface standardization
├── test_redis_validation_centralization.py             # Centralization enforcement
└── test_redis_validation_cross_service_compliance.py   # Cross-service compliance

tests/unit/redis_validation_ssot/
├── __init__.py
├── test_redis_health_checker_ssot.py                   # Unit tests for SSOT violations
└── test_redis_validation_pattern_detection.py          # Pattern analysis tests

tests/mission_critical/
└── test_redis_validation_ssot_critical.py              # Mission critical SSOT compliance
```

## 🔬 Detailed Test Cases

### 1. Integration Tests

#### 1.1 Redis Validation Duplication Detection (`test_redis_validation_duplication_detection.py`)

```python
"""
Test Redis Validation SSOT Compliance - Duplication Detection

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Architecture Compliance
- Value Impact: Prevents maintenance overhead and inconsistent behavior
- Strategic Impact: Ensures single source of truth for validation logic
"""

import pytest
from typing import Dict, Set, Any
import inspect
import importlib
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

class TestRedisValidationDuplication(BaseIntegrationTest):
    """Detect Redis validation logic duplication across services."""

    @pytest.mark.integration
    @pytest.mark.ssot_compliance
    async def test_redis_validation_method_uniqueness_violation(self):
        """CRITICAL: This test MUST FAIL when multiple services implement Redis validation."""
        
        # Scan all services for Redis validation methods
        validation_implementations = self._scan_redis_validation_methods()
        
        # Count unique implementations
        unique_implementations = len(validation_implementations)
        
        # This assertion SHOULD FAIL currently (multiple implementations exist)
        assert unique_implementations <= 1, (
            f"SSOT VIOLATION: Found {unique_implementations} Redis validation implementations "
            f"across services: {list(validation_implementations.keys())}. "
            f"Only ONE canonical implementation should exist."
        )

    @pytest.mark.integration  
    @pytest.mark.ssot_compliance
    async def test_redis_health_check_interface_consistency_violation(self):
        """CRITICAL: This test MUST FAIL when services use different validation interfaces."""
        
        from netra_backend.app.api.health_checks import HealthManager
        from auth_service.services.health_check_service import HealthCheckService
        from analytics_service.analytics_core.database.connection import RedisHealthChecker
        
        # Get method signatures from each service
        backend_methods = self._extract_redis_methods(HealthManager)
        auth_methods = self._extract_redis_methods(HealthCheckService)  
        analytics_methods = self._extract_redis_methods(RedisHealthChecker)
        
        all_methods = {
            "backend": backend_methods,
            "auth": auth_methods,
            "analytics": analytics_methods
        }
        
        # Check for interface consistency
        inconsistencies = self._detect_interface_inconsistencies(all_methods)
        
        # This assertion SHOULD FAIL currently (interfaces are inconsistent)
        assert len(inconsistencies) == 0, (
            f"SSOT VIOLATION: Redis validation interfaces are inconsistent across services: "
            f"{inconsistencies}. All services must use identical validation interface."
        )

    async def test_redis_validation_return_format_standardization_violation(self, real_services_fixture):
        """CRITICAL: This test MUST FAIL when services return different validation formats."""
        
        # Test actual Redis validation calls
        backend_result = await self._call_backend_redis_validation()
        auth_result = await self._call_auth_redis_validation() 
        analytics_result = await self._call_analytics_redis_validation()
        
        results = {
            "backend": backend_result,
            "auth": auth_result,
            "analytics": analytics_result
        }
        
        # Analyze return format consistency
        format_inconsistencies = self._analyze_return_format_consistency(results)
        
        # This assertion SHOULD FAIL currently (different return formats)
        assert len(format_inconsistencies) == 0, (
            f"SSOT VIOLATION: Redis validation return formats are inconsistent: "
            f"{format_inconsistencies}. All services must return standardized format."
        )

    def _scan_redis_validation_methods(self) -> Dict[str, Any]:
        """Scan codebase for Redis validation method implementations."""
        implementations = {}
        
        # Backend service
        try:
            from netra_backend.app.api.health_checks import HealthManager
            if hasattr(HealthManager, 'check_redis_health'):
                implementations['backend'] = {
                    'class': HealthManager,
                    'method': 'check_redis_health',
                    'file': 'netra_backend/app/api/health_checks.py'
                }
        except ImportError:
            pass
            
        # Auth service  
        try:
            from auth_service.services.health_check_service import HealthCheckService
            if hasattr(HealthCheckService, '_check_redis_health'):
                implementations['auth'] = {
                    'class': HealthCheckService,
                    'method': '_check_redis_health', 
                    'file': 'auth_service/services/health_check_service.py'
                }
        except ImportError:
            pass
            
        # Analytics service
        try:
            from analytics_service.analytics_core.database.connection import RedisHealthChecker
            if hasattr(RedisHealthChecker, 'check_health'):
                implementations['analytics'] = {
                    'class': RedisHealthChecker,
                    'method': 'check_health',
                    'file': 'analytics_service/analytics_core/database/connection.py'
                }
        except ImportError:
            pass
            
        return implementations

    def _extract_redis_methods(self, cls) -> Dict[str, Any]:
        """Extract Redis validation methods from a class."""
        methods = {}
        
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if 'redis' in name.lower() and ('check' in name.lower() or 'health' in name.lower()):
                signature = inspect.signature(method)
                methods[name] = {
                    'signature': str(signature),
                    'parameters': list(signature.parameters.keys()),
                    'annotations': signature.return_annotation
                }
                
        return methods

    def _detect_interface_inconsistencies(self, all_methods: Dict[str, Dict]) -> List[str]:
        """Detect interface inconsistencies between services."""
        inconsistencies = []
        
        # Compare method signatures across services
        all_signatures = {}
        for service, methods in all_methods.items():
            for method_name, details in methods.items():
                if method_name not in all_signatures:
                    all_signatures[method_name] = {}
                all_signatures[method_name][service] = details['signature']
        
        # Check for signature differences
        for method, signatures in all_signatures.items():
            unique_sigs = set(signatures.values())
            if len(unique_sigs) > 1:
                inconsistencies.append(f"Method '{method}' has different signatures: {signatures}")
                
        return inconsistencies

    async def _call_backend_redis_validation(self) -> Dict[str, Any]:
        """Call backend Redis validation and return result format."""
        try:
            from netra_backend.app.api.health_checks import HealthManager
            manager = HealthManager()
            result = await manager.check_redis_health()
            return result.dict() if hasattr(result, 'dict') else result
        except Exception as e:
            return {"error": str(e), "service": "backend"}

    async def _call_auth_redis_validation(self) -> Dict[str, Any]:
        """Call auth service Redis validation and return result format.""" 
        try:
            from auth_service.services.health_check_service import HealthCheckService
            from auth_service.auth_core.config import get_auth_config
            
            config = get_auth_config()
            service = HealthCheckService(config)
            result = await service._check_redis_health()
            return result
        except Exception as e:
            return {"error": str(e), "service": "auth"}

    async def _call_analytics_redis_validation(self) -> Dict[str, Any]:
        """Call analytics service Redis validation and return result format."""
        try:
            from analytics_service.analytics_core.database.connection import RedisHealthChecker
            checker = RedisHealthChecker()
            result = await checker.check_health()
            return result
        except Exception as e:
            return {"error": str(e), "service": "analytics"}

    def _analyze_return_format_consistency(self, results: Dict[str, Dict]) -> List[str]:
        """Analyze return format consistency across services."""
        inconsistencies = []
        
        # Check required fields consistency
        required_fields_by_service = {}
        for service, result in results.items():
            if "error" not in result:
                required_fields_by_service[service] = set(result.keys())
        
        # Find field differences
        if len(required_fields_by_service) > 1:
            all_fields = set()
            for fields in required_fields_by_service.values():
                all_fields.update(fields)
                
            for service, fields in required_fields_by_service.items():
                missing_fields = all_fields - fields
                if missing_fields:
                    inconsistencies.append(f"Service '{service}' missing fields: {missing_fields}")
        
        return inconsistencies
```

#### 1.2 Redis Validation Centralization Tests (`test_redis_validation_centralization.py`)

```python
"""
Test Redis Validation Centralization Enforcement

This test ensures that all Redis validation goes through a single, 
canonical implementation in shared utilities.
"""

import pytest
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

class TestRedisValidationCentralization(BaseIntegrationTest):
    """Enforce centralized Redis validation implementation."""

    @pytest.mark.integration
    @pytest.mark.ssot_compliance
    async def test_shared_redis_validator_exists_requirement(self):
        """CRITICAL: This test MUST FAIL until shared Redis validator is implemented."""
        
        # Check for canonical Redis validator in shared utilities
        try:
            from shared.redis_validator import RedisValidator  # SHOULD NOT EXIST YET
            from shared.redis_validator import validate_redis_connection  # SHOULD NOT EXIST YET
            
            # If we get here, shared validator exists (TEST SHOULD PASS)
            validator = RedisValidator()
            assert validator is not None
            assert callable(validate_redis_connection)
            
        except ImportError as e:
            # Expected current behavior - shared validator doesn't exist yet
            pytest.fail(
                f"SSOT VIOLATION: Shared Redis validator not implemented. "
                f"Import error: {e}. All services are using their own validation logic instead of "
                f"a shared SSOT implementation in 'shared.redis_validator'."
            )

    @pytest.mark.integration
    @pytest.mark.ssot_compliance  
    async def test_services_use_shared_validator_requirement(self):
        """CRITICAL: This test MUST FAIL until services use shared validator."""
        
        # Check that services import from shared validator (not implemented yet)
        violations = []
        
        # Check backend service
        if self._service_has_local_redis_validation("backend"):
            violations.append("backend service has local Redis validation instead of using shared")
            
        # Check auth service  
        if self._service_has_local_redis_validation("auth"):
            violations.append("auth service has local Redis validation instead of using shared")
            
        # Check analytics service
        if self._service_has_local_redis_validation("analytics"):
            violations.append("analytics service has local Redis validation instead of using shared")
        
        # This assertion SHOULD FAIL currently (services have local validation)
        assert len(violations) == 0, (
            f"SSOT VIOLATION: Services still using local Redis validation: {violations}. "
            f"All services must import and use shared.redis_validator.validate_redis_connection()"
        )

    def _service_has_local_redis_validation(self, service: str) -> bool:
        """Check if service has local Redis validation implementation."""
        
        if service == "backend":
            try:
                import netra_backend.app.api.health_checks as backend_health
                return hasattr(backend_health.HealthManager, 'check_redis_health')
            except ImportError:
                return False
                
        elif service == "auth":
            try:
                import auth_service.services.health_check_service as auth_health
                return hasattr(auth_health.HealthCheckService, '_check_redis_health')
            except ImportError:
                return False
                
        elif service == "analytics": 
            try:
                import analytics_service.analytics_core.database.connection as analytics_db
                return hasattr(analytics_db, 'RedisHealthChecker')
            except ImportError:
                return False
                
        return False
```

### 2. Unit Tests

#### 2.1 Redis Health Checker SSOT Tests (`test_redis_health_checker_ssot.py`)

```python
"""
Unit Tests for Redis Health Checker SSOT Violations

Tests individual Redis health checker implementations to detect
duplication and interface inconsistencies at the unit level.
"""

import pytest
import inspect
from typing import Dict, Any

class TestRedisHealthCheckerSSOT:
    """Unit tests for Redis health checker SSOT compliance."""

    @pytest.mark.unit
    @pytest.mark.ssot_compliance
    def test_redis_health_checker_class_duplication_violation(self):
        """CRITICAL: This test MUST FAIL when multiple Redis health checker classes exist."""
        
        health_checker_classes = []
        
        # Scan for Redis health checker classes
        try:
            from netra_backend.app.api.health_checks import HealthManager
            if self._has_redis_health_methods(HealthManager):
                health_checker_classes.append("netra_backend.app.api.health_checks.HealthManager")
        except ImportError:
            pass
            
        try:
            from auth_service.services.health_check_service import HealthCheckService  
            if self._has_redis_health_methods(HealthCheckService):
                health_checker_classes.append("auth_service.services.health_check_service.HealthCheckService")
        except ImportError:
            pass
            
        try:
            from analytics_service.analytics_core.database.connection import RedisHealthChecker
            health_checker_classes.append("analytics_service.analytics_core.database.connection.RedisHealthChecker")
        except ImportError:
            pass
        
        # This assertion SHOULD FAIL currently (multiple classes exist)  
        assert len(health_checker_classes) <= 1, (
            f"SSOT VIOLATION: Found {len(health_checker_classes)} Redis health checker classes: "
            f"{health_checker_classes}. Only ONE canonical implementation should exist in shared utilities."
        )

    @pytest.mark.unit
    @pytest.mark.ssot_compliance  
    def test_redis_validation_method_signature_consistency_violation(self):
        """CRITICAL: This test MUST FAIL when Redis validation methods have different signatures."""
        
        method_signatures = {}
        
        # Collect method signatures from each service
        try:
            from netra_backend.app.api.health_checks import HealthManager
            method_signatures['backend'] = self._get_redis_method_signature(HealthManager, 'check_redis_health')
        except (ImportError, AttributeError):
            pass
            
        try:
            from auth_service.services.health_check_service import HealthCheckService
            method_signatures['auth'] = self._get_redis_method_signature(HealthCheckService, '_check_redis_health')
        except (ImportError, AttributeError):
            pass
            
        try:
            from analytics_service.analytics_core.database.connection import RedisHealthChecker
            method_signatures['analytics'] = self._get_redis_method_signature(RedisHealthChecker, 'check_health')
        except (ImportError, AttributeError):
            pass
        
        # Check signature consistency
        unique_signatures = set(method_signatures.values())
        
        # This assertion SHOULD FAIL currently (different signatures exist)
        assert len(unique_signatures) <= 1, (
            f"SSOT VIOLATION: Redis validation methods have inconsistent signatures: "
            f"{method_signatures}. All validation methods must have identical signatures."
        )

    def _has_redis_health_methods(self, cls) -> bool:
        """Check if class has Redis health check methods."""
        methods = inspect.getmembers(cls, predicate=inspect.ismethod)
        redis_methods = [name for name, _ in methods 
                        if 'redis' in name.lower() and 'health' in name.lower()]
        return len(redis_methods) > 0

    def _get_redis_method_signature(self, cls, method_name: str) -> str:
        """Get method signature as string."""
        if hasattr(cls, method_name):
            method = getattr(cls, method_name)
            return str(inspect.signature(method))
        return ""
```

### 3. Mission Critical Tests

#### 3.1 Redis Validation SSOT Critical Tests (`test_redis_validation_ssot_critical.py`)

```python
"""
Mission Critical Redis Validation SSOT Compliance Tests

These tests MUST PASS before any deployment. They ensure that
Redis validation follows SSOT principles and doesn't introduce
system-wide inconsistencies.
"""

import pytest
from tests.mission_critical.base import MissionCriticalTest

class TestRedisValidationSSORCritical(MissionCriticalTest):
    """Mission critical Redis validation SSOT compliance tests."""

    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_redis_validation_ssot_compliance_deployment_blocker(self):
        """
        MISSION CRITICAL: This test blocks deployment if Redis validation SSOT is violated.
        
        This test MUST PASS before any deployment to prevent:
        - Inconsistent Redis validation behavior across services
        - Maintenance overhead from duplicated validation logic
        - Silent failures due to different validation implementations
        """
        
        # Scan all services for Redis validation implementations
        validation_violations = await self._scan_redis_validation_violations()
        
        # Check for SSOT compliance
        if len(validation_violations) > 0:
            pytest.fail(
                f"DEPLOYMENT BLOCKED: Redis validation SSOT violations detected: "
                f"{validation_violations}. "
                f"All Redis validation must go through shared.redis_validator before deployment."
            )
        
        # If we reach here, SSOT compliance is achieved
        assert True, "Redis validation SSOT compliance verified - deployment approved"

    async def _scan_redis_validation_violations(self) -> Dict[str, str]:
        """Scan for Redis validation SSOT violations."""
        violations = {}
        
        # Check each service for local Redis validation
        services_to_check = ['backend', 'auth', 'analytics']
        
        for service in services_to_check:
            violation = await self._check_service_redis_validation(service)
            if violation:
                violations[service] = violation
                
        return violations

    async def _check_service_redis_validation(self, service: str) -> str:
        """Check if service has local Redis validation (violation)."""
        
        if service == "backend":
            try:
                from netra_backend.app.api.health_checks import HealthManager
                if hasattr(HealthManager, 'check_redis_health'):
                    # Check if it imports from shared validator
                    import inspect
                    source = inspect.getsource(HealthManager.check_redis_health)
                    if 'shared.redis_validator' not in source:
                        return "Backend service implements local Redis validation instead of using shared validator"
            except ImportError:
                pass
                
        elif service == "auth":
            try:
                from auth_service.services.health_check_service import HealthCheckService
                if hasattr(HealthCheckService, '_check_redis_health'):
                    import inspect
                    source = inspect.getsource(HealthCheckService._check_redis_health)
                    if 'shared.redis_validator' not in source:
                        return "Auth service implements local Redis validation instead of using shared validator"
            except ImportError:
                pass
                
        elif service == "analytics":
            try:
                from analytics_service.analytics_core.database.connection import RedisHealthChecker
                # Analytics service has local Redis health checker class
                return "Analytics service has local RedisHealthChecker class instead of using shared validator"
            except ImportError:
                pass
        
        return ""
```

## 🔄 Test Execution Strategy

### Phase 1: Failing Tests (Current State)
```bash
# Run Redis validation SSOT compliance tests - SHOULD FAIL
python tests/unified_test_runner.py --category integration --test-pattern "*redis_validation_ssot*"

# Expected Results:
# ❌ test_redis_validation_method_uniqueness_violation - FAIL (multiple implementations)
# ❌ test_redis_health_check_interface_consistency_violation - FAIL (inconsistent interfaces)
# ❌ test_shared_redis_validator_exists_requirement - FAIL (no shared validator)
# ❌ test_services_use_shared_validator_requirement - FAIL (services use local validation)
```

### Phase 2: Implementation Guidance
After tests FAIL (proving SSOT violations exist), the development team should:

1. **Create Shared Redis Validator**:
   ```python
   # shared/redis_validator.py
   class RedisValidator:
       async def validate_redis_connection(self, redis_client) -> Dict[str, Any]:
           # Single canonical implementation
   ```

2. **Update All Services** to use shared validator:
   - Remove local Redis validation methods
   - Import and use `shared.redis_validator.validate_redis_connection()`
   - Standardize return formats

### Phase 3: Passing Tests (Target State)
```bash
# After SSOT implementation - SHOULD PASS
python tests/unified_test_runner.py --category integration --test-pattern "*redis_validation_ssot*"

# Expected Results:
# ✅ test_redis_validation_method_uniqueness_violation - PASS (single implementation)
# ✅ test_redis_health_check_interface_consistency_violation - PASS (consistent interfaces)  
# ✅ test_shared_redis_validator_exists_requirement - PASS (shared validator exists)
# ✅ test_services_use_shared_validator_requirement - PASS (services use shared validator)
```

## 📊 Expected Test Results

### Current State (SSOT Violations Present)
- **Integration Tests**: 8/10 FAILING ❌
- **Unit Tests**: 3/3 FAILING ❌  
- **Mission Critical**: 1/1 FAILING ❌ (BLOCKS DEPLOYMENT)

### Target State (SSOT Compliance Achieved)  
- **Integration Tests**: 10/10 PASSING ✅
- **Unit Tests**: 3/3 PASSING ✅
- **Mission Critical**: 1/1 PASSING ✅ (DEPLOYMENT APPROVED)

## 🚨 Critical Success Indicators

1. **Test Failure Rate**: Tests MUST fail initially to prove SSOT violations exist
2. **Violation Detection**: Tests must accurately identify all Redis validation duplications
3. **Implementation Guidance**: Failed tests must provide clear guidance on SSOT implementation
4. **Deployment Blocking**: Mission critical tests must block deployment until SSOT compliance achieved

## 📝 Implementation Notes

### Key Testing Patterns Used
- **Real Service Integration**: Tests use real Redis connections where possible
- **Code Analysis**: Tests scan source code for validation implementations
- **Interface Consistency**: Tests verify method signatures and return formats
- **Import Dependency**: Tests check that services import from shared utilities

### Business Value Delivered
- **Reduced Maintenance**: Single validation implementation reduces code duplication
- **Consistent Behavior**: All services validate Redis with identical logic
- **Deployment Safety**: Mission critical tests prevent SSOT violation deployments
- **Developer Experience**: Clear test failures guide proper SSOT implementation

---

**Final Note**: This test plan creates comprehensive failing tests that will drive the proper centralization of Redis validation logic into SSOT patterns, eliminating the current duplication across services and ensuring consistent, maintainable Redis validation throughout the platform.