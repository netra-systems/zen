# SSOT Violation Remediation - Test Execution Guide

**Issue #1076 Companion Guide**
**Date:** 2025-09-16
**Purpose:** Practical execution instructions for SSOT violation test strategy
**Prerequisites:** Read `SSOT_VIOLATION_REMEDIATION_TEST_STRATEGY.md` first

## Quick Start - Immediate Actions

### Current State Validation
```bash
# 1. Verify existing tests are working and detecting violations
cd C:\netra-apex

# Run existing Issue #1076 tests (should FAIL initially)
python tests/mission_critical/test_ssot_wrapper_function_detection_1076_simple.py -v
python tests/mission_critical/test_ssot_behavioral_consistency_1076.py -v
python tests/mission_critical/test_ssot_websocket_integration_1076.py -v
python tests/mission_critical/test_ssot_file_reference_migration_1076.py -v

# Expected Result: Tests FAIL with specific violation counts and details
```

### Test Infrastructure Validation
```bash
# 2. Verify SSOT test framework is operational
python -c "from test_framework.ssot.base_test_case import SSotBaseTestCase; print('SSOT framework ready')"

# 3. Verify unified test runner supports SSOT patterns
python tests/unified_test_runner.py --help | grep -i ssot

# 4. Check test framework utilities
ls test_framework/ssot/ | wc -l  # Should show 60+ utility modules
```

## Phase 1: Enhanced Unit Test Implementation (Immediate Priority)

### Test Creation Priority Order

#### 1. Critical Logging SSOT Tests (P0 - Highest Impact)
**Target:** 2,202 deprecated logging references

```bash
# Create test directory structure
mkdir -p tests/unit/ssot_compliance
mkdir -p tests/integration/ssot_compliance
mkdir -p tests/e2e/ssot_compliance
```

**Create:** `tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py`

```python
"""
SSOT Logging Migration Tests for Issue #1076
Target: 2,202 deprecated logging_config references

EXPECTED: Tests FAIL initially detecting violations
REMEDIATION: All logging migrated to unified_logging_ssot
"""

import pytest
from pathlib import Path
import ast
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestLoggingSSOTMigration(SSotBaseTestCase):
    """Tests for logging SSOT compliance - highest impact violations"""

    @property
    def project_root(self):
        return Path(__file__).parent.parent.parent.parent

    def test_no_deprecated_logging_config_imports(self):
        """
        CRITICAL: Detect deprecated logging_config imports
        EXPECTED: FAIL initially - 2,202+ violations detected
        """
        violations = []
        deprecated_patterns = [
            "from netra_backend.app.logging_config import",
            "import netra_backend.app.logging_config"
        ]

        search_paths = [
            self.project_root / "netra_backend",
            self.project_root / "auth_service",
            self.project_root / "shared"
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob("*.py"):
                if py_file.name.startswith("__") or "test" in py_file.name.lower():
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for pattern in deprecated_patterns:
                        if pattern in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if pattern in line:
                                    violations.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'line': i,
                                        'content': line.strip(),
                                        'pattern': pattern
                                    })
                except Exception:
                    continue

        # Test FAILS initially if violations exist
        if violations:
            sample_violations = violations[:10]
            violation_summary = "\n".join([
                f"  - {v['file']}:{v['line']} - {v['content']}"
                for v in sample_violations
            ])

            self.fail(
                f"SSOT VIOLATION: Found {len(violations)} deprecated logging imports:\n"
                f"{violation_summary}\n"
                f"{'... and ' + str(len(violations) - 10) + ' more' if len(violations) > 10 else ''}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"1. Replace with: from shared.logging.unified_logging_ssot import get_logger\n"
                f"2. Update logger usage: logger = get_logger(__name__)\n"
                f"3. Remove all logging_config references"
            )

    def test_consistent_logger_instantiation_patterns(self):
        """
        CRITICAL: Detect inconsistent logger instantiation
        EXPECTED: FAIL initially - mixed logger patterns detected
        """
        inconsistent_patterns = []

        # Expected SSOT pattern
        ssot_pattern = "get_logger(__name__)"

        # Deprecated patterns to detect
        deprecated_logger_patterns = [
            "logging.getLogger(",
            "central_logger.get_logger(",
            "Logger(",
            "logger = logging"
        ]

        search_paths = [self.project_root / "netra_backend", self.project_root / "auth_service"]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob("*.py"):
                if py_file.name.startswith("__") or "test" in py_file.name.lower():
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for pattern in deprecated_logger_patterns:
                        if pattern in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if pattern in line:
                                    inconsistent_patterns.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'line': i,
                                        'content': line.strip(),
                                        'pattern': pattern
                                    })
                except Exception:
                    continue

        if inconsistent_patterns:
            sample_patterns = inconsistent_patterns[:8]
            pattern_summary = "\n".join([
                f"  - {p['file']}:{p['line']} - {p['content']}"
                for p in sample_patterns
            ])

            self.fail(
                f"SSOT VIOLATION: Found {len(inconsistent_patterns)} inconsistent logger patterns:\n"
                f"{pattern_summary}\n"
                f"{'... and ' + str(len(inconsistent_patterns) - 8) + ' more' if len(inconsistent_patterns) > 8 else ''}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"1. Use SSOT pattern: {ssot_pattern}\n"
                f"2. Import from: from shared.logging.unified_logging_ssot import get_logger\n"
                f"3. Ensure consistent logger instantiation across all files"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

#### 2. Import Pattern SSOT Tests (P0 - High Volume)
**Target:** 718 function delegation + 727 deprecated imports

**Create:** `tests/unit/ssot_compliance/test_import_pattern_ssot_1076.py`

#### 3. Auth Integration SSOT Tests (P0 - Security Critical)
**Target:** 45 wrapper functions + 27 auth imports

**Create:** `tests/unit/ssot_compliance/test_auth_integration_ssot_1076.py`

### Test Execution Commands

```bash
# Execute Phase 1 tests individually
cd C:\netra-apex

# 1. Logging SSOT tests (highest impact)
python tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py -v

# 2. Import pattern tests
python tests/unit/ssot_compliance/test_import_pattern_ssot_1076.py -v

# 3. Auth integration tests
python tests/unit/ssot_compliance/test_auth_integration_ssot_1076.py -v

# Execute all Phase 1 tests together
python tests/unified_test_runner.py --category unit --path "tests/unit/ssot_compliance" --pattern "*1076*"

# Expected Result: All tests FAIL with specific violation details
```

## Phase 2: Integration Tests (Real Services, Non-Docker)

### Integration Test Focus Areas

#### WebSocket SSOT Behavioral Tests
**Target:** WebSocket auth violations + consistency

```bash
# Create integration test
mkdir -p tests/integration/ssot_compliance
```

**Create:** `tests/integration/ssot_compliance/test_websocket_ssot_integration_1076.py`

```python
"""
WebSocket SSOT Integration Tests for Issue #1076
Target: 5 WebSocket auth violations + behavioral consistency

EXPECTED: Tests FAIL initially detecting violations
EXECUTION: Real services via test fixtures (no Docker required)
"""

import pytest
from test_framework.ssot.base_integration_test import BaseIntegrationTest
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket_test_client import WebSocketTestClient


class TestWebSocketSSOTIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket SSOT compliance"""

    @pytest.mark.integration
    async def test_websocket_auth_ssot_compliance(self, real_services_fixture):
        """
        CRITICAL: Verify WebSocket uses SSOT auth patterns
        EXPECTED: FAIL initially - detects deprecated auth usage
        """
        # Test implementation validates WebSocket auth integration
        pass

    @pytest.mark.integration
    async def test_websocket_event_emission_consistency(self, real_services_fixture):
        """
        CRITICAL: Verify consistent event emission patterns
        EXPECTED: FAIL initially - detects inconsistent patterns
        """
        # Test implementation validates event consistency
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### Integration Test Execution

```bash
# Run WebSocket integration tests
python tests/integration/ssot_compliance/test_websocket_ssot_integration_1076.py -v

# Run with real services (non-Docker)
python tests/unified_test_runner.py --category integration --path "tests/integration/ssot_compliance" --real-services --no-docker

# Expected: Tests FAIL initially, detecting behavioral violations
```

## Phase 3: E2E GCP Staging Tests (Golden Path Critical)

### Golden Path SSOT Validation
**Target:** 6 golden path violations (business critical)

```bash
# Create E2E test directory
mkdir -p tests/e2e/ssot_compliance
```

**Create:** `tests/e2e/ssot_compliance/test_golden_path_ssot_staging_1076.py`

```python
"""
Golden Path SSOT E2E Tests for Issue #1076
Target: 6 golden path violations - BUSINESS CRITICAL

EXPECTED: Tests FAIL initially detecting violations
EXECUTION: GCP staging environment
BUSINESS IMPACT: $500K+ ARR chat functionality
"""

import pytest
from test_framework.base_e2e_test import BaseE2ETest


class TestGoldenPathSSOTStaging(BaseE2ETest):
    """E2E tests for golden path SSOT compliance"""

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    @pytest.mark.mission_critical
    async def test_complete_golden_path_ssot_compliance(self, staging_env):
        """
        MISSION CRITICAL: Validate golden path uses SSOT patterns
        Business Impact: Complete user journey functionality
        """
        # Implementation validates end-to-end SSOT compliance
        pass

    @pytest.mark.e2e
    @pytest.mark.staging_gcp
    async def test_websocket_events_ssot_staging(self, staging_env):
        """
        CRITICAL: Validate WebSocket events use SSOT in staging
        """
        # Implementation validates staging WebSocket compliance
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### E2E Test Execution

```bash
# Execute E2E staging tests
python tests/e2e/ssot_compliance/test_golden_path_ssot_staging_1076.py -v

# Execute with staging environment
python tests/unified_test_runner.py --category e2e --env staging --path "tests/e2e/ssot_compliance" --pattern "*1076*"

# Expected: Tests FAIL initially, detecting golden path violations
```

## Continuous Monitoring and Validation

### Progressive Test Execution During Remediation

```bash
# 1. Run specific test category during focused remediation
python tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py -v

# 2. Monitor violation count reduction
pytest tests/unit/ssot_compliance/test_*_1076.py -v --tb=no | grep "VIOLATION:"

# 3. Validate remediation success (tests start passing)
python tests/unified_test_runner.py --category unit --path "tests/unit/ssot_compliance"

# 4. Full SSOT compliance validation
pytest tests/**/ssot_compliance/test_*1076*.py -v
```

### Test Success Progression Tracking

```bash
# Track test progression from FAIL → PASS
echo "REMEDIATION PROGRESS TRACKING" > ssot_progress.log

# Before remediation (expect failures)
pytest tests/unit/ssot_compliance/ -v >> ssot_progress.log 2>&1

# After each remediation batch
pytest tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py -v >> ssot_progress.log 2>&1

# Final validation (expect all passing)
pytest tests/**/ssot_compliance/ -v >> ssot_progress.log 2>&1
```

### Violation Count Monitoring

```bash
# Extract violation counts from test output
python -c "
import re
import subprocess

result = subprocess.run(['pytest', 'tests/unit/ssot_compliance/', '-v'],
                       capture_output=True, text=True)

violations = re.findall(r'Found (\d+) .*violations', result.stdout)
total_violations = sum(int(v) for v in violations)
print(f'Total SSOT violations detected: {total_violations}')
"
```

## Test Infrastructure Integration

### Using Existing SSOT Framework
```bash
# Verify SSOT test utilities are available
python -c "
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from test_framework.ssot.orchestration import OrchestrationConfig
print('All SSOT test utilities available')
"

# Test unified runner integration
python tests/unified_test_runner.py --execution-mode fast_feedback --path "tests/unit/ssot_compliance"
```

### Mission Critical Integration
```bash
# Run SSOT tests alongside existing mission critical tests
python tests/mission_critical/test_websocket_agent_events_suite.py -v
python tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py -v

# Validate no regression in golden path while fixing SSOT violations
python tests/mission_critical/test_websocket_agent_events_suite.py -v && \
python tests/unit/ssot_compliance/test_*_1076.py -v
```

## Troubleshooting and Common Issues

### Test Environment Issues
```bash
# 1. SSOT framework import errors
export PYTHONPATH="/c/netra-apex:$PYTHONPATH"
python -c "from test_framework.ssot.base_test_case import SSotBaseTestCase; print('OK')"

# 2. Test discovery issues
pytest --collect-only tests/unit/ssot_compliance/

# 3. Path resolution issues (Windows)
python tests/unified_test_runner.py --category unit --path "tests\\unit\\ssot_compliance"
```

### Expected Test Behavior
```bash
# BEFORE remediation - tests should FAIL
pytest tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py -v
# Expected: FAILED - "SSOT VIOLATION: Found 2202+ deprecated logging imports"

# DURING remediation - violation counts decrease
pytest tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py -v
# Expected: FAILED - "SSOT VIOLATION: Found 1500 deprecated logging imports"

# AFTER remediation - tests should PASS
pytest tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py -v
# Expected: PASSED - No violations detected
```

## Success Criteria Validation

### Quantitative Success Metrics
```bash
# 1. Violation count progression: 3,845 → 0
grep -r "Found .* violations" tests/unit/ssot_compliance/ | wc -l

# 2. Test success rate: 0% → 100%
pytest tests/**/ssot_compliance/ --tb=no | grep -E "(PASSED|FAILED)"

# 3. Execution time validation
time pytest tests/unit/ssot_compliance/ -v  # Should complete in <5 minutes
```

### Qualitative Success Indicators
- **Developer Experience:** Clear test failure messages with specific remediation steps
- **Golden Path Protection:** Mission critical tests continue passing throughout remediation
- **System Stability:** No performance regression during SSOT migration
- **Architectural Clarity:** Single source of truth clearly enforced

## Next Steps and Action Items

### Immediate Actions (Today)
1. Create `tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py`
2. Execute initial test run to establish baseline: `python tests/unit/ssot_compliance/test_logging_ssot_migration_1076.py -v`
3. Verify test FAILS with 2,202+ violation detection
4. Begin logging SSOT remediation guided by test feedback

### Week 1: Complete Unit Test Suite
1. Create remaining 4 unit test files (import patterns, auth integration, configuration, architectural)
2. Execute full Phase 1 test suite
3. Establish violation baseline across all categories
4. Begin systematic remediation of P0 violations

### Week 2: Integration Test Expansion
1. Create integration test files for behavioral consistency
2. Execute integration tests with real services
3. Validate cross-service SSOT compliance
4. Remediate integration-level violations

### Week 3: E2E Staging Validation
1. Create E2E staging test files for golden path
2. Execute tests in GCP staging environment
3. Validate production-ready SSOT compliance
4. Final remediation of remaining violations

### Ongoing: Continuous Monitoring
1. Integrate SSOT tests into CI/CD pipeline
2. Monitor violation count trends
3. Prevent regression through automated testing
4. Maintain 100% SSOT compliance

---

**This execution guide provides the practical steps to implement and run the comprehensive SSOT violation remediation test strategy. Follow the progressive approach to ensure systematic violation detection, remediation, and validation.**