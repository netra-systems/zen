# 🚨 **Issue #416 Comprehensive Test Plan: Deprecation Warning Systematic Remediation**

## **Business Value Justification (BVJ)**
- **Segment:** Platform Infrastructure (All tiers)
- **Business Goal:** Stability & Technical Debt Reduction
- **Value Impact:** Eliminate technical debt that threatens $500K+ ARR Golden Path reliability
- **Strategic Impact:** Ensure smooth future migrations and prevent production warnings

---

## **Executive Summary**

**Current State Analysis:**
- **285 SSOT violations** across 118 files requiring systematic remediation
- **Phase 1 COMPLETE:** 89% reduction achieved (8/9 critical Golden Path deprecation warnings eliminated)
- **Remaining Work:** Systematic testing and remediation of remaining violations across logging, Pydantic, WebSocket, datetime, and environment patterns
- **Business Risk:** Medium-Low (Golden Path protected, but technical debt accumulation threatens future stability)

**Test Strategy:** Create failing tests that reproduce deprecation warnings, then systematically validate fixes following CLAUDE.md best practices with focus on **non-docker tests only** (unit, integration, staging E2E).

---

## **Test Architecture Overview**

### **Test Categories Aligned with CLAUDE.md**
1. **Unit Tests:** Isolated component deprecation detection
2. **Integration Tests:** Cross-service deprecation validation (no docker)
3. **Staging E2E Tests:** Real environment deprecation monitoring
4. **Mission Critical Tests:** Business-critical deprecation prevention

### **Core Test Strategy**
- **Detection First:** Create tests that FAIL when deprecation warnings are present
- **Real Services Only:** No mocks for integration/E2E tests
- **SSOT Compliance:** Use test_framework/ssot/ infrastructure
- **Business Value Focus:** Prioritize tests that protect $500K+ ARR functionality

---

## **Phase 2 Test Plan: Systematic Coverage**

### **Phase 2.1: Detection Test Suite**
**Purpose:** Create comprehensive detection tests that identify and count all deprecation warnings

#### **1. Deprecation Warning Detection Tests**
**Location:** `tests/unit/deprecation_warnings/`

```python
# tests/unit/deprecation_warnings/test_deprecation_warning_detection.py
"""
Deprecation Warning Detection Test Suite

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Technical debt visibility
- Value Impact: Prevent warnings from accumulating and threatening stability
- Strategic Impact: Enable systematic remediation planning
"""

import pytest
import warnings
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.deprecation_scanner import DeprecationScanner

class TestDeprecationWarningDetection(SSotBaseTestCase):
    """Comprehensive deprecation warning detection tests."""
    
    @pytest.mark.unit
    def test_import_pattern_deprecation_warnings(self):
        """Test that detects all import-related deprecation warnings."""
        scanner = DeprecationScanner()
        
        # Scan for deprecated import patterns
        deprecated_imports = scanner.scan_deprecated_imports([
            "netra_backend/app/",
            "auth_service/",
            "shared/"
        ])
        
        # This test should FAIL if deprecation warnings found
        assert len(deprecated_imports) == 0, (
            f"Found {len(deprecated_imports)} deprecated imports: "
            f"{deprecated_imports}"
        )
    
    @pytest.mark.unit
    def test_logging_deprecation_warnings(self):
        """Test that detects logging-related deprecation warnings."""
        scanner = DeprecationScanner()
        
        # Scan for deprecated logging patterns
        deprecated_logging = scanner.scan_deprecated_logging_patterns()
        
        # This test should FAIL if logging deprecations found
        assert len(deprecated_logging) == 0, (
            f"Found {len(deprecated_logging)} deprecated logging patterns"
        )
    
    @pytest.mark.unit
    def test_websocket_deprecation_warnings(self):
        """Test that detects WebSocket-related deprecation warnings."""
        scanner = DeprecationScanner()
        
        # Scan for deprecated WebSocket patterns
        deprecated_websocket = scanner.scan_deprecated_websocket_patterns()
        
        # This test should FAIL if WebSocket deprecations found
        assert len(deprecated_websocket) == 0, (
            f"Found {len(deprecated_websocket)} deprecated WebSocket patterns"
        )
    
    @pytest.mark.unit
    def test_pydantic_deprecation_warnings(self):
        """Test that detects Pydantic configuration deprecation warnings."""
        scanner = DeprecationScanner()
        
        # Scan for deprecated Pydantic patterns
        deprecated_pydantic = scanner.scan_deprecated_pydantic_patterns()
        
        # This test should FAIL if Pydantic deprecations found
        assert len(deprecated_pydantic) == 0, (
            f"Found {len(deprecated_pydantic)} deprecated Pydantic patterns"
        )
    
    @pytest.mark.unit
    def test_datetime_deprecation_warnings(self):
        """Test that detects datetime.utcnow() deprecation warnings."""
        scanner = DeprecationScanner()
        
        # Scan for deprecated datetime patterns
        deprecated_datetime = scanner.scan_deprecated_datetime_patterns()
        
        # This test should FAIL if datetime deprecations found
        assert len(deprecated_datetime) == 0, (
            f"Found {len(deprecated_datetime)} deprecated datetime patterns"
        )
    
    @pytest.mark.unit
    def test_environment_access_deprecation_warnings(self):
        """Test that detects direct os.environ access deprecation warnings."""
        scanner = DeprecationScanner()
        
        # Scan for deprecated environment access patterns
        deprecated_env = scanner.scan_deprecated_environment_patterns()
        
        # This test should FAIL if environment deprecations found
        assert len(deprecated_env) == 0, (
            f"Found {len(deprecated_env)} deprecated environment patterns"
        )
```

#### **2. Runtime Deprecation Warning Monitoring**
**Location:** `tests/integration/deprecation_warnings/`

```python
# tests/integration/deprecation_warnings/test_runtime_deprecation_monitoring.py
"""
Runtime Deprecation Warning Monitoring

Business Value Justification (BVJ):
- Segment: Platform Infrastructure  
- Business Goal: Runtime stability validation
- Value Impact: Ensure production code doesn't generate deprecation warnings
- Strategic Impact: Protect $500K+ ARR from warning-related issues
"""

import pytest
import warnings
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

class TestRuntimeDeprecationMonitoring(BaseIntegrationTest):
    """Monitor deprecation warnings during runtime operations."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_operations_no_warnings(self, real_services_fixture):
        """Test WebSocket operations produce no deprecation warnings."""
        # Capture warnings during WebSocket operations
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always", DeprecationWarning)
            
            # Perform WebSocket operations using real services
            websocket_manager = real_services_fixture["websocket_manager"]
            await websocket_manager.handle_connection()
            
            # Check for deprecation warnings
            deprecation_warnings = [
                w for w in warning_list 
                if issubclass(w.category, DeprecationWarning)
            ]
            
            assert len(deprecation_warnings) == 0, (
                f"WebSocket operations generated {len(deprecation_warnings)} "
                f"deprecation warnings: {[str(w.message) for w in deprecation_warnings]}"
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_no_warnings(self, real_services_fixture):
        """Test agent execution produces no deprecation warnings."""
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always", DeprecationWarning)
            
            # Execute agent using real services
            agent_factory = real_services_fixture["agent_factory"]
            agent = await agent_factory.create_agent("triage_agent")
            result = await agent.execute("Test query")
            
            # Check for deprecation warnings
            deprecation_warnings = [
                w for w in warning_list 
                if issubclass(w.category, DeprecationWarning)
            ]
            
            assert len(deprecation_warnings) == 0, (
                f"Agent execution generated {len(deprecation_warnings)} "
                f"deprecation warnings: {[str(w.message) for w in deprecation_warnings]}"
            )
```

### **Phase 2.2: Migration Validation Tests**
**Purpose:** Verify deprecated patterns are properly replaced with modern equivalents

#### **3. Migration Validation Test Suite**
**Location:** `tests/unit/migration_validation/`

```python
# tests/unit/migration_validation/test_ssot_migration_validation.py
"""
SSOT Migration Validation Tests

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Ensure SSOT compliance
- Value Impact: Validate systematic migration to canonical patterns
- Strategic Impact: Eliminate the 285 SSOT violations across 118 files
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.migration_validator import SSotMigrationValidator

class TestSSotMigrationValidation(SSotBaseTestCase):
    """Validate SSOT migration completeness."""
    
    @pytest.mark.unit
    def test_import_path_consolidation(self):
        """Test that all imports use canonical SSOT paths."""
        validator = SSotMigrationValidator()
        
        # Validate canonical import paths
        non_canonical_imports = validator.find_non_canonical_imports()
        
        # This test should FAIL if non-canonical imports found
        assert len(non_canonical_imports) == 0, (
            f"Found {len(non_canonical_imports)} non-canonical imports that "
            f"should use SSOT patterns: {non_canonical_imports}"
        )
    
    @pytest.mark.unit
    def test_factory_pattern_compliance(self):
        """Test that all factory patterns follow SSOT guidelines."""
        validator = SSotMigrationValidator()
        
        # Validate factory pattern usage
        non_compliant_factories = validator.find_non_compliant_factories()
        
        # This test should FAIL if non-compliant factories found
        assert len(non_compliant_factories) == 0, (
            f"Found {len(non_compliant_factories)} non-compliant factories: "
            f"{non_compliant_factories}"
        )
    
    @pytest.mark.unit
    def test_singleton_pattern_elimination(self):
        """Test that singleton patterns are eliminated per Issue #1116."""
        validator = SSotMigrationValidator()
        
        # Validate singleton elimination
        remaining_singletons = validator.find_singleton_patterns()
        
        # This test should FAIL if singletons found
        assert len(remaining_singletons) == 0, (
            f"Found {len(remaining_singletons)} remaining singleton patterns: "
            f"{remaining_singletons}"
        )
```

### **Phase 2.3: Regression Prevention Tests**
**Purpose:** Prevent new deprecation warnings from being introduced

#### **4. Regression Prevention Test Suite**
**Location:** `tests/mission_critical/deprecation_prevention/`

```python
# tests/mission_critical/deprecation_prevention/test_deprecation_regression_prevention.py
"""
Deprecation Regression Prevention Tests

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Prevent regression of technical debt
- Value Impact: Protect $500K+ ARR from future deprecation-related issues
- Strategic Impact: Ensure deprecation remediation progress is maintained
"""

import pytest
from tests.mission_critical.base import MissionCriticalTest

class TestDeprecationRegressionPrevention(MissionCriticalTest):
    """Prevent regression of deprecation warning fixes."""
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    def test_zero_deprecation_warnings_in_golden_path(self):
        """MISSION CRITICAL: Golden Path must have zero deprecation warnings."""
        # This test MUST pass or deployment is blocked
        
        # Test complete Golden Path user flow
        result = self.execute_complete_golden_path_with_warning_monitoring()
        
        # NON-NEGOTIABLE: Zero deprecation warnings in Golden Path
        assert result.deprecation_warnings == 0, (
            f"Golden Path generated {result.deprecation_warnings} deprecation "
            f"warnings - this breaks business continuity"
        )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip  
    def test_websocket_events_no_deprecation_warnings(self):
        """MISSION CRITICAL: WebSocket events must not generate warnings."""
        # This test MUST pass for chat functionality
        
        result = self.execute_websocket_events_with_warning_monitoring()
        
        # NON-NEGOTIABLE: WebSocket events with zero warnings
        assert result.deprecation_warnings == 0, (
            f"WebSocket events generated {result.deprecation_warnings} "
            f"deprecation warnings - this threatens chat value delivery"
        )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    def test_agent_execution_no_deprecation_warnings(self):
        """MISSION CRITICAL: Agent execution must not generate warnings."""
        # This test MUST pass for AI value delivery
        
        result = self.execute_agent_execution_with_warning_monitoring()
        
        # NON-NEGOTIABLE: Agent execution with zero warnings
        assert result.deprecation_warnings == 0, (
            f"Agent execution generated {result.deprecation_warnings} "
            f"deprecation warnings - this threatens AI value delivery"
        )
```

### **Phase 2.4: Systematic Coverage Tests**
**Purpose:** Comprehensive coverage of all deprecation warning categories

#### **5. Logging System Deprecation Tests**
**Location:** `tests/unit/logging_deprecation/`

```python
# tests/unit/logging_deprecation/test_logging_system_deprecation.py
"""
Logging System Deprecation Tests

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Eliminate logging deprecation warnings
- Value Impact: Ensure logging infrastructure doesn't generate warnings
- Strategic Impact: Support observability without technical debt
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestLoggingSystemDeprecation(SSotBaseTestCase):
    """Test logging system deprecation warning elimination."""
    
    @pytest.mark.unit
    def test_central_logger_import_deprecation(self):
        """Test that central_logger imports use canonical paths."""
        # This test should FAIL if deprecated central_logger imports found
        from test_framework.logging_scanner import LoggingScanner
        
        scanner = LoggingScanner()
        deprecated_imports = scanner.scan_deprecated_central_logger_imports()
        
        assert len(deprecated_imports) == 0, (
            f"Found {len(deprecated_imports)} deprecated central_logger imports"
        )
    
    @pytest.mark.unit
    def test_unified_logger_factory_deprecation(self):
        """Test that unified_logger_factory imports are eliminated."""
        # Based on Phase 1 results - this pattern was eliminated
        from test_framework.logging_scanner import LoggingScanner
        
        scanner = LoggingScanner()
        deprecated_factory_imports = scanner.scan_unified_logger_factory_imports()
        
        assert len(deprecated_factory_imports) == 0, (
            f"Found {len(deprecated_factory_imports)} unified_logger_factory imports"
        )
    
    @pytest.mark.unit
    def test_logging_config_deprecation(self):
        """Test that logging_config imports use canonical paths."""
        from test_framework.logging_scanner import LoggingScanner
        
        scanner = LoggingScanner()
        deprecated_config_imports = scanner.scan_deprecated_logging_config_imports()
        
        assert len(deprecated_config_imports) == 0, (
            f"Found {len(deprecated_config_imports)} deprecated logging_config imports"
        )
```

#### **6. WebSocket System Deprecation Tests**
**Location:** `tests/unit/websocket_deprecation/`

```python
# tests/unit/websocket_deprecation/test_websocket_system_deprecation.py
"""
WebSocket System Deprecation Tests

Business Value Justification (BVJ):
- Segment: Core Business Infrastructure 
- Business Goal: Eliminate WebSocket deprecation warnings
- Value Impact: Protect $500K+ ARR chat functionality from warning-related issues
- Strategic Impact: Ensure WebSocket reliability for real-time features
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestWebSocketSystemDeprecation(SSotBaseTestCase):
    """Test WebSocket system deprecation warning elimination."""
    
    @pytest.mark.unit
    def test_websocket_manager_import_deprecation(self):
        """Test that WebSocketManager imports use canonical paths."""
        from test_framework.websocket_scanner import WebSocketScanner
        
        scanner = WebSocketScanner()
        deprecated_imports = scanner.scan_deprecated_websocket_manager_imports()
        
        assert len(deprecated_imports) == 0, (
            f"Found {len(deprecated_imports)} deprecated WebSocketManager imports"
        )
    
    @pytest.mark.unit
    def test_websocket_factory_deprecation(self):
        """Test that WebSocket factory patterns use SSOT compliance."""
        from test_framework.websocket_scanner import WebSocketScanner
        
        scanner = WebSocketScanner()
        deprecated_factories = scanner.scan_deprecated_websocket_factories()
        
        assert len(deprecated_factories) == 0, (
            f"Found {len(deprecated_factories)} deprecated WebSocket factories"
        )
    
    @pytest.mark.unit
    def test_websocket_event_emitter_deprecation(self):
        """Test that WebSocket event emitters use canonical patterns."""
        from test_framework.websocket_scanner import WebSocketScanner
        
        scanner = WebSocketScanner()
        deprecated_emitters = scanner.scan_deprecated_event_emitters()
        
        assert len(deprecated_emitters) == 0, (
            f"Found {len(deprecated_emitters)} deprecated event emitters"
        )
```

#### **7. Pydantic Configuration Deprecation Tests**
**Location:** `tests/unit/pydantic_deprecation/`

```python
# tests/unit/pydantic_deprecation/test_pydantic_configuration_deprecation.py
"""
Pydantic Configuration Deprecation Tests

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Eliminate Pydantic deprecation warnings  
- Value Impact: Ensure configuration system doesn't generate warnings
- Strategic Impact: Support modern Pydantic patterns without technical debt
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestPydanticConfigurationDeprecation(SSotBaseTestCase):
    """Test Pydantic configuration deprecation warning elimination."""
    
    @pytest.mark.unit
    def test_pydantic_v1_config_deprecation(self):
        """Test that Pydantic v1 Config classes are migrated to v2."""
        from test_framework.pydantic_scanner import PydanticScanner
        
        scanner = PydanticScanner()
        v1_configs = scanner.scan_pydantic_v1_configs()
        
        assert len(v1_configs) == 0, (
            f"Found {len(v1_configs)} Pydantic v1 Config classes that need migration"
        )
    
    @pytest.mark.unit
    def test_pydantic_field_deprecation(self):
        """Test that deprecated Pydantic Field usage is eliminated."""
        from test_framework.pydantic_scanner import PydanticScanner
        
        scanner = PydanticScanner()
        deprecated_fields = scanner.scan_deprecated_field_usage()
        
        assert len(deprecated_fields) == 0, (
            f"Found {len(deprecated_fields)} deprecated Pydantic Field usages"
        )
    
    @pytest.mark.unit
    def test_pydantic_validator_deprecation(self):
        """Test that deprecated Pydantic validator patterns are eliminated."""
        from test_framework.pydantic_scanner import PydanticScanner
        
        scanner = PydanticScanner()
        deprecated_validators = scanner.scan_deprecated_validators()
        
        assert len(deprecated_validators) == 0, (
            f"Found {len(deprecated_validators)} deprecated Pydantic validators"
        )
```

#### **8. Datetime Deprecation Tests**
**Location:** `tests/unit/datetime_deprecation/`

```python
# tests/unit/datetime_deprecation/test_datetime_deprecation.py
"""
Datetime Deprecation Tests

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Eliminate datetime.utcnow() deprecation warnings
- Value Impact: Ensure timestamp generation doesn't generate warnings
- Strategic Impact: Modernize datetime usage for Python 3.12+ compatibility
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestDatetimeDeprecation(SSotBaseTestCase):
    """Test datetime deprecation warning elimination."""
    
    @pytest.mark.unit
    def test_datetime_utcnow_deprecation(self):
        """Test that datetime.utcnow() usage is eliminated."""
        from test_framework.datetime_scanner import DatetimeScanner
        
        scanner = DatetimeScanner()
        utcnow_usages = scanner.scan_datetime_utcnow_usage()
        
        assert len(utcnow_usages) == 0, (
            f"Found {len(utcnow_usages)} datetime.utcnow() usages that should "
            f"be replaced with datetime.now(timezone.utc)"
        )
    
    @pytest.mark.unit  
    def test_timezone_naive_datetime_deprecation(self):
        """Test that timezone-naive datetime usage is eliminated."""
        from test_framework.datetime_scanner import DatetimeScanner
        
        scanner = DatetimeScanner()
        naive_usages = scanner.scan_timezone_naive_datetime()
        
        assert len(naive_usages) == 0, (
            f"Found {len(naive_usages)} timezone-naive datetime usages"
        )
```

#### **9. Environment Access Deprecation Tests**
**Location:** `tests/unit/environment_deprecation/`

```python
# tests/unit/environment_deprecation/test_environment_access_deprecation.py
"""
Environment Access Deprecation Tests

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Eliminate direct os.environ access
- Value Impact: Ensure environment access uses SSOT IsolatedEnvironment
- Strategic Impact: Support proper environment isolation and testing
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestEnvironmentAccessDeprecation(SSotBaseTestCase):
    """Test environment access deprecation warning elimination."""
    
    @pytest.mark.unit
    def test_direct_os_environ_access_deprecation(self):
        """Test that direct os.environ access is eliminated."""
        from test_framework.environment_scanner import EnvironmentScanner
        
        scanner = EnvironmentScanner()
        direct_access = scanner.scan_direct_os_environ_access()
        
        assert len(direct_access) == 0, (
            f"Found {len(direct_access)} direct os.environ accesses that should "
            f"use IsolatedEnvironment"
        )
    
    @pytest.mark.unit
    def test_environment_variable_validation(self):
        """Test that all environment variable access uses proper validation."""
        from test_framework.environment_scanner import EnvironmentScanner
        
        scanner = EnvironmentScanner()
        unvalidated_access = scanner.scan_unvalidated_env_access()
        
        assert len(unvalidated_access) == 0, (
            f"Found {len(unvalidated_access)} unvalidated environment accesses"
        )
```

### **Phase 2.5: Staging E2E Deprecation Tests**
**Purpose:** Real environment validation of deprecation warning elimination

#### **10. Staging Environment Deprecation Monitoring**
**Location:** `tests/e2e/staging/deprecation_monitoring/`

```python
# tests/e2e/staging/deprecation_monitoring/test_staging_deprecation_monitoring.py
"""
Staging Environment Deprecation Monitoring

Business Value Justification (BVJ):
- Segment: Production Infrastructure
- Business Goal: Validate production-ready deprecation elimination  
- Value Impact: Ensure staging environment reflects production quality
- Strategic Impact: Prove system ready for enterprise deployment
"""

import pytest
from test_framework.base_e2e_test import BaseE2ETest

class TestStagingDeprecationMonitoring(BaseE2ETest):
    """Monitor deprecation warnings in staging environment."""
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_websocket_no_warnings(self):
        """Test staging WebSocket operations produce no warnings."""
        # Connect to real staging environment
        async with self.create_staging_websocket_client() as client:
            
            # Monitor for deprecation warnings during operations
            with self.monitor_deprecation_warnings() as monitor:
                
                # Perform complete WebSocket flow
                await client.send_agent_request("Test optimization query")
                events = await client.collect_all_events(timeout=30)
                
                # Verify no deprecation warnings
                warnings = monitor.get_deprecation_warnings()
                assert len(warnings) == 0, (
                    f"Staging WebSocket operations generated "
                    f"{len(warnings)} deprecation warnings"
                )
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_agent_execution_no_warnings(self):
        """Test staging agent execution produces no warnings."""
        # Use real staging environment
        async with self.create_staging_client() as client:
            
            # Monitor for deprecation warnings during agent execution
            with self.monitor_deprecation_warnings() as monitor:
                
                # Execute complete agent workflow
                response = await client.execute_agent_workflow(
                    agent_type="cost_optimizer",
                    query="Analyze infrastructure costs"
                )
                
                # Verify business value delivered AND no warnings
                assert response.has_business_value()
                
                warnings = monitor.get_deprecation_warnings()
                assert len(warnings) == 0, (
                    f"Staging agent execution generated "
                    f"{len(warnings)} deprecation warnings"
                )
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_complete_user_flow_no_warnings(self):
        """Test complete staging user flow produces no warnings."""
        # Test complete Golden Path in staging
        with self.monitor_deprecation_warnings() as monitor:
            
            # Execute complete user flow: login -> chat -> AI response
            result = await self.execute_complete_staging_user_flow()
            
            # Verify business value AND no warnings
            assert result.delivers_business_value()
            
            warnings = monitor.get_deprecation_warnings()
            assert len(warnings) == 0, (
                f"Staging complete user flow generated "
                f"{len(warnings)} deprecation warnings"
            )
```

---

## **Test Execution Strategy**

### **Phase 2 Execution Order**
1. **Week 1:** Detection Test Suite (Phase 2.1)
2. **Week 2:** Migration Validation Tests (Phase 2.2)  
3. **Week 3:** Regression Prevention Tests (Phase 2.3)
4. **Week 4:** Systematic Coverage Tests (Phase 2.4)
5. **Week 5:** Staging E2E Tests (Phase 2.5)

### **Test Commands Following CLAUDE.md**

```bash
# Detection Tests (Unit)
python tests/unified_test_runner.py --category unit --pattern "*deprecation_warnings*"

# Migration Validation Tests (Unit)
python tests/unified_test_runner.py --category unit --pattern "*migration_validation*"

# Regression Prevention Tests (Mission Critical)
python tests/mission_critical/deprecation_prevention/test_deprecation_regression_prevention.py

# Systematic Coverage Tests (Unit)
python tests/unified_test_runner.py --category unit --pattern "*logging_deprecation*"
python tests/unified_test_runner.py --category unit --pattern "*websocket_deprecation*" 
python tests/unified_test_runner.py --category unit --pattern "*pydantic_deprecation*"
python tests/unified_test_runner.py --category unit --pattern "*datetime_deprecation*"
python tests/unified_test_runner.py --category unit --pattern "*environment_deprecation*"

# Staging E2E Tests (No Docker)
python tests/unified_test_runner.py --category e2e --pattern "*staging*deprecation*" --env staging

# Complete Validation Suite
python tests/unified_test_runner.py --category all --pattern "*deprecation*" --real-services
```

### **Success Criteria**
- **Detection Tests:** Must FAIL when deprecation warnings present, then PASS after fixes
- **Migration Tests:** Must validate 285 SSOT violations are addressed
- **Mission Critical Tests:** Must PASS for deployment approval
- **Coverage Tests:** Must cover all deprecation categories systematically
- **Staging Tests:** Must validate production-ready quality

---

## **Supporting Infrastructure**

### **Test Framework Utilities to Create**

#### **1. DeprecationScanner Class**
**Location:** `test_framework/deprecation_scanner.py`

```python
class DeprecationScanner:
    """Comprehensive deprecation warning scanner."""
    
    def scan_deprecated_imports(self, directories: List[str]) -> List[Dict]:
        """Scan for deprecated import patterns."""
        pass
    
    def scan_deprecated_logging_patterns(self) -> List[Dict]:
        """Scan for deprecated logging patterns."""
        pass
    
    def scan_deprecated_websocket_patterns(self) -> List[Dict]:
        """Scan for deprecated WebSocket patterns.""" 
        pass
    
    def scan_deprecated_pydantic_patterns(self) -> List[Dict]:
        """Scan for deprecated Pydantic patterns."""
        pass
    
    def scan_deprecated_datetime_patterns(self) -> List[Dict]:
        """Scan for deprecated datetime patterns."""
        pass
    
    def scan_deprecated_environment_patterns(self) -> List[Dict]:
        """Scan for deprecated environment patterns."""
        pass
```

#### **2. Specialized Scanners**
- `test_framework/logging_scanner.py` - Logging deprecation detection
- `test_framework/websocket_scanner.py` - WebSocket deprecation detection
- `test_framework/pydantic_scanner.py` - Pydantic deprecation detection
- `test_framework/datetime_scanner.py` - Datetime deprecation detection
- `test_framework/environment_scanner.py` - Environment deprecation detection

#### **3. Warning Monitoring Utilities**
**Location:** `test_framework/warning_monitor.py`

```python
class DeprecationWarningMonitor:
    """Monitor and capture deprecation warnings during test execution."""
    
    def __enter__(self):
        """Start monitoring deprecation warnings."""
        pass
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop monitoring and capture results."""
        pass
    
    def get_deprecation_warnings(self) -> List[str]:
        """Get list of deprecation warnings captured."""
        pass
```

---

## **Business Impact & Risk Assessment**

### **Business Value Protection**
- **$500K+ ARR Protected:** Golden Path already validated deprecation-free in Phase 1
- **Technical Debt Reduction:** Systematic elimination of 285 SSOT violations  
- **Production Readiness:** Enterprise-grade warning elimination
- **Future-Proofing:** Prevention of warning accumulation

### **Risk Mitigation**
- **Low Business Risk:** Golden Path protected by Phase 1 completion
- **Testing Risk:** Comprehensive coverage prevents regression
- **Deployment Risk:** Mission critical tests gate deployments
- **Technical Risk:** Systematic approach ensures complete coverage

### **Success Metrics**
- **Zero Deprecation Warnings:** In mission critical tests
- **285 SSOT Violations:** Systematically addressed and validated
- **100% Test Coverage:** All deprecation categories covered
- **Production Ready:** Staging validation confirms enterprise quality

---

## **Conclusion**

This comprehensive test plan provides systematic coverage for eliminating the remaining deprecation warnings while protecting the $500K+ ARR Golden Path functionality. The test-driven approach ensures:

1. **Business Value First:** Mission critical tests protect revenue-generating functionality
2. **Comprehensive Coverage:** All deprecation categories systematically addressed
3. **Real Services Focus:** Integration and E2E tests use real services per CLAUDE.md
4. **Regression Prevention:** Continuous monitoring prevents warning accumulation
5. **Production Readiness:** Staging validation ensures enterprise deployment quality

The plan builds on Phase 1's 89% success rate to achieve complete deprecation warning elimination while maintaining system stability and business value delivery.

---

*Test Plan created following CLAUDE.md best practices with focus on business value protection and systematic technical debt reduction*