"""
Migration Compliance Tests - Issue #89

This test suite validates UnifiedIDManager migration compliance across services
as specified in the comprehensive test plan. These tests are designed to FAIL
until complete migration from uuid.uuid4() to UnifiedIDManager patterns.

Business Value Justification:
- Segment: Platform/All Tiers (Migration affects system reliability for all users)
- Business Goal: System Stability & Development Velocity
- Value Impact: Ensures systematic migration prevents regression and system failures
- Strategic Impact: Provides migration validation framework for enterprise deployment

Test Strategy: Create FAILING tests that validate complete migration compliance
"""

import os
import re
import ast
import time
from typing import Dict, List, Set, Any, Optional
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestMigrationCompliance(SSotBaseTestCase):
    """
    Test suite to validate migration compliance across all services.

    These tests are designed to FAIL until migration is complete,
    providing clear metrics on migration progress and remaining work.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.unified_id_manager = UnifiedIDManager()
        self.project_root = Path(__file__).parent.parent.parent.parent

        # Define service boundaries for migration validation
        self.service_boundaries = {
            "backend_core": self.project_root / "netra_backend" / "app",
            "auth_service": self.project_root / "auth_service",
            "shared_libraries": self.project_root / "shared",
            "frontend_lib": self.project_root / "frontend" / "lib",
            "scripts": self.project_root / "scripts"
        }

        # Define critical modules that must be 100% compliant
        self.critical_modules = [
            "unified_id_manager",
            "user_execution_context",
            "websocket_manager",
            "agent_execution_tracker",
            "auth_integration"
        ]

    def test_backend_service_migration_compliance(self):
        """
        FAILING TEST: Backend service migration must be 100% complete.

        This test scans all backend production modules and validates
        complete migration to UnifiedIDManager patterns.
        """
        backend_path = self.service_boundaries["backend_core"]
        if not backend_path.exists():
            self.skip("Backend path not found")

        # Scan all backend modules for migration compliance
        violations = self._scan_service_migration_compliance(backend_path, "backend")
        compliance_report = self._generate_compliance_report(violations, "backend")

        # Record comprehensive metrics
        self.record_metric("backend_violation_count", compliance_report["violation_count"])
        self.record_metric("backend_coverage_percentage", compliance_report["coverage_percentage"])
        self.record_metric("backend_compliant_modules", compliance_report["compliant_modules"])
        self.record_metric("backend_non_compliant_modules", compliance_report["non_compliant_modules"])
        self.record_metric("backend_critical_violations", compliance_report["critical_violations"])

        # Backend must be 100% compliant for production readiness
        assert compliance_report["violation_count"] == 0, (
            f"Backend service has {compliance_report['violation_count']} migration violations. "
            f"Coverage: {compliance_report['coverage_percentage']:.2f}%. "
            f"Non-compliant modules: {len(compliance_report['non_compliant_modules'])}. "
            f"Critical violations: {compliance_report['critical_violations']}. "
            f"Backend must be 100% migrated to UnifiedIDManager for production deployment."
        )

    def test_auth_service_migration_compliance(self):
        """
        FAILING TEST: Auth service must not contain uuid.uuid4() calls.

        Auth service is critical for security and must use UnifiedIDManager
        for all ID generation to ensure consistent security patterns.
        """
        auth_path = self.service_boundaries["auth_service"]
        if not auth_path.exists():
            self.skip("Auth service path not found")

        # Auth service gets special scrutiny due to security requirements
        auth_violations = self._scan_auth_service_for_uuid4()
        security_compliance = self._validate_auth_security_compliance(auth_path)

        # Record auth-specific metrics
        self.record_metric("auth_uuid4_violations", len(auth_violations))
        self.record_metric("auth_security_compliance", security_compliance)
        self.record_metric("auth_violation_details", auth_violations)

        # Critical modules in auth service must be violation-free
        critical_auth_violations = []
        for violation in auth_violations:
            if any(critical_module in violation["file_path"] for critical_module in self.critical_modules):
                critical_auth_violations.append(violation)

        self.record_metric("auth_critical_violations", len(critical_auth_violations))

        # Auth service must be completely migrated due to security requirements
        assert len(auth_violations) == 0, (
            f"Auth service contains {len(auth_violations)} uuid.uuid4() violations. "
            f"Critical violations: {len(critical_auth_violations)}. "
            f"Security compliance: {security_compliance}. "
            f"Auth service must use UnifiedIDManager exclusively for security consistency."
        )

    def test_shared_library_migration_compliance(self):
        """
        FAILING TEST: Shared libraries must not contain uuid.uuid4() calls.

        Shared libraries are used across all services and must be
        completely migrated to prevent violation propagation.
        """
        shared_path = self.service_boundaries["shared_libraries"]
        if not shared_path.exists():
            self.skip("Shared libraries path not found")

        shared_violations = self._scan_shared_libraries_for_uuid4()

        # Categorize violations by library module
        library_violations = {}
        for violation in shared_violations:
            library_name = self._extract_library_name(violation["file_path"])
            if library_name not in library_violations:
                library_violations[library_name] = []
            library_violations[library_name].append(violation)

        # Check critical shared modules separately
        critical_shared_violations = []
        for critical_module in self.critical_modules:
            module_violations = [v for v in shared_violations
                               if critical_module in v["file_path"]]
            critical_shared_violations.extend(module_violations)

        # Record shared library metrics
        self.record_metric("shared_total_violations", len(shared_violations))
        self.record_metric("shared_library_violations", library_violations)
        self.record_metric("shared_critical_violations", len(critical_shared_violations))
        self.record_metric("shared_affected_libraries", len(library_violations))

        # Critical shared modules must be 100% compliant
        assert len(critical_shared_violations) == 0, (
            f"Critical shared modules have {len(critical_shared_violations)} violations. "
            f"Affected libraries: {list(library_violations.keys())}. "
            f"Total violations: {len(shared_violations)}. "
            f"Critical shared modules must be completely migrated to UnifiedIDManager."
        )

    def test_websocket_id_migration_compliance(self):
        """
        FAILING TEST: WebSocket IDs should use UnifiedIDManager patterns.

        WebSocket ID generation is critical for chat functionality
        and must use consistent UnifiedIDManager patterns.
        """
        websocket_violations = self._scan_websocket_code_for_uuid4()
        websocket_patterns = self._analyze_websocket_id_patterns()

        # Validate WebSocket-specific compliance
        websocket_compliance = {
            "connection_id_compliance": 0,
            "event_id_compliance": 0,
            "session_id_compliance": 0,
            "total_compliance": 0
        }

        # Analyze each type of WebSocket ID usage
        for violation in websocket_violations:
            violation_type = self._classify_websocket_violation(violation)
            if violation_type in websocket_compliance:
                websocket_compliance[violation_type] += 1

        total_websocket_violations = len(websocket_violations)
        websocket_compliance["total_compliance"] = total_websocket_violations

        # Record WebSocket-specific metrics
        self.record_metric("websocket_violations", total_websocket_violations)
        self.record_metric("websocket_compliance_breakdown", websocket_compliance)
        self.record_metric("websocket_pattern_analysis", websocket_patterns)

        # WebSocket must be fully migrated for chat functionality reliability
        assert total_websocket_violations == 0, (
            f"WebSocket code has {total_websocket_violations} uuid.uuid4() violations. "
            f"Connection ID violations: {websocket_compliance['connection_id_compliance']}, "
            f"Event ID violations: {websocket_compliance['event_id_compliance']}, "
            f"Session ID violations: {websocket_compliance['session_id_compliance']}. "
            f"WebSocket must use UnifiedIDManager for all ID generation to ensure chat reliability."
        )

    def test_service_by_service_migration_status(self):
        """
        FAILING TEST: Comprehensive migration status across all services.

        This test provides a complete migration dashboard showing
        progress and remaining work for each service.
        """
        migration_dashboard = {}

        for service_name, service_path in self.service_boundaries.items():
            if not service_path.exists():
                migration_dashboard[service_name] = {"status": "path_not_found"}
                continue

            # Comprehensive service analysis
            service_analysis = self._comprehensive_service_analysis(service_path, service_name)
            migration_dashboard[service_name] = service_analysis

        # Calculate overall migration metrics
        overall_metrics = self._calculate_overall_migration_metrics(migration_dashboard)

        # Record comprehensive dashboard
        self.record_metric("migration_dashboard", migration_dashboard)
        self.record_metric("overall_migration_metrics", overall_metrics)

        # Set migration completion thresholds
        required_compliance = {
            "backend_core": 100.0,  # Must be 100% for production
            "auth_service": 100.0,  # Security-critical
            "shared_libraries": 90.0,  # High priority
            "frontend_lib": 70.0,   # Lower priority
            "scripts": 50.0         # Lowest priority
        }

        compliance_failures = []
        for service_name, required_percentage in required_compliance.items():
            if service_name in migration_dashboard:
                actual_compliance = migration_dashboard[service_name].get("compliance_percentage", 0)
                if actual_compliance < required_percentage:
                    compliance_failures.append({
                        "service": service_name,
                        "required": required_percentage,
                        "actual": actual_compliance,
                        "gap": required_percentage - actual_compliance
                    })

        # The test should FAIL if compliance requirements are not met
        assert len(compliance_failures) == 0, (
            f"Migration compliance requirements not met for {len(compliance_failures)} services. "
            f"Overall compliance: {overall_metrics['overall_compliance_percentage']:.2f}%. "
            f"Compliance failures: {compliance_failures}. "
            f"Services must meet minimum compliance thresholds for deployment."
        )

    def test_performance_impact_validation(self):
        """
        FAILING TEST: UnifiedIDManager should not degrade system performance.

        This test benchmarks ID generation performance to ensure
        migration doesn't introduce unacceptable performance overhead.
        """
        # Benchmark different ID generation methods
        performance_benchmarks = {}

        # Benchmark UnifiedIDManager vs uuid.uuid4()
        unified_time = self._benchmark_unified_id_generation(iterations=10000)
        uuid4_time = self._benchmark_uuid4_generation(iterations=10000)

        performance_ratio = unified_time / uuid4_time if uuid4_time > 0 else float('inf')

        performance_benchmarks = {
            "unified_id_time_seconds": unified_time,
            "uuid4_time_seconds": uuid4_time,
            "performance_ratio": performance_ratio,
            "acceptable_threshold": 2.0  # UnifiedIDManager should be at most 2x slower
        }

        # Test concurrent performance
        concurrent_unified_time = self._benchmark_concurrent_unified_generation(
            iterations=5000, threads=10
        )
        concurrent_uuid4_time = self._benchmark_concurrent_uuid4_generation(
            iterations=5000, threads=10
        )

        concurrent_ratio = (concurrent_unified_time / concurrent_uuid4_time
                          if concurrent_uuid4_time > 0 else float('inf'))

        performance_benchmarks.update({
            "concurrent_unified_time": concurrent_unified_time,
            "concurrent_uuid4_time": concurrent_uuid4_time,
            "concurrent_performance_ratio": concurrent_ratio
        })

        # Record performance metrics
        self.record_metric("performance_benchmarks", performance_benchmarks)

        # Performance should be acceptable for production use
        assert performance_ratio < 2.0, (
            f"UnifiedIDManager performance degradation too high: {performance_ratio:.2f}x slower than uuid4. "
            f"Single-threaded: {unified_time:.4f}s vs {uuid4_time:.4f}s. "
            f"Concurrent: {concurrent_unified_time:.4f}s vs {concurrent_uuid4_time:.4f}s. "
            f"Performance ratio must be <2.0x for acceptable production performance."
        )

    def test_backward_compatibility_validation(self):
        """
        FAILING TEST: Migration should not break existing ID validation.

        This test ensures that existing systems can still work with
        both old and new ID formats during the migration period.
        """
        compatibility_issues = []

        # Test legacy UUID format acceptance
        legacy_uuids = self._generate_legacy_uuid4_ids(50)
        new_structured_ids = self._generate_unified_manager_ids(50)

        # Validate legacy ID acceptance
        for uuid_id in legacy_uuids:
            if not self._is_valid_id_format_compatible(uuid_id):
                compatibility_issues.append({
                    "type": "legacy_uuid_rejected",
                    "id": uuid_id,
                    "issue": "Legacy UUID format should be accepted during migration"
                })

        # Validate new ID format acceptance
        for structured_id in new_structured_ids:
            if not self._is_valid_id_format_compatible(structured_id):
                compatibility_issues.append({
                    "type": "new_format_rejected",
                    "id": structured_id,
                    "issue": "New structured format should be accepted"
                })

        # Test cross-format operations
        cross_format_issues = self._test_cross_format_operations(legacy_uuids, new_structured_ids)
        compatibility_issues.extend(cross_format_issues)

        # Record compatibility metrics
        self.record_metric("compatibility_issues", len(compatibility_issues))
        self.record_metric("legacy_uuid_tested", len(legacy_uuids))
        self.record_metric("new_format_tested", len(new_structured_ids))
        self.record_metric("compatibility_issue_details", compatibility_issues)

        # Backward compatibility must be maintained
        assert len(compatibility_issues) == 0, (
            f"Found {len(compatibility_issues)} backward compatibility issues. "
            f"Legacy UUIDs tested: {len(legacy_uuids)}, "
            f"New formats tested: {len(new_structured_ids)}. "
            f"Migration must maintain backward compatibility with existing systems."
        )

    # Helper methods for migration compliance validation

    def _scan_service_migration_compliance(self, service_path: Path, service_name: str) -> List[Dict[str, Any]]:
        """Scan a service for migration compliance violations."""
        violations = []

        for py_file in service_path.rglob("*.py"):
            if self._should_exclude_file(py_file):
                continue

            file_violations = self._scan_file_for_migration_violations(py_file)
            violations.extend(file_violations)

        return violations

    def _scan_file_for_migration_violations(self, file_path: Path) -> List[Dict[str, Any]]:
        """Scan a single file for migration violations."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            # Look for uuid.uuid4() usage
            for line_num, line in enumerate(lines, 1):
                if re.search(r'uuid\.uuid4\(', line, re.IGNORECASE):
                    violations.append({
                        "type": "uuid4_usage",
                        "file_path": str(file_path),
                        "line_number": line_num,
                        "line_content": line.strip(),
                        "severity": "high"
                    })

                # Look for direct UUID imports
                if re.search(r'from uuid import uuid4|import uuid', line, re.IGNORECASE):
                    violations.append({
                        "type": "uuid_import",
                        "file_path": str(file_path),
                        "line_number": line_num,
                        "line_content": line.strip(),
                        "severity": "medium"
                    })

        except Exception as e:
            violations.append({
                "type": "scan_error",
                "file_path": str(file_path),
                "error": str(e),
                "severity": "low"
            })

        return violations

    def _generate_compliance_report(self, violations: List[Dict[str, Any]], service_name: str) -> Dict[str, Any]:
        """Generate a comprehensive compliance report for a service."""
        total_violations = len(violations)
        high_severity = len([v for v in violations if v.get("severity") == "high"])
        medium_severity = len([v for v in violations if v.get("severity") == "medium"])

        # Calculate compliance percentage
        affected_files = set(v["file_path"] for v in violations if "file_path" in v)
        total_files = self._count_service_files(service_name)
        compliant_files = total_files - len(affected_files)
        coverage_percentage = (compliant_files / max(1, total_files)) * 100

        # Identify critical violations
        critical_violations = len([v for v in violations
                                 if any(critical_module in v.get("file_path", "")
                                       for critical_module in self.critical_modules)])

        return {
            "violation_count": total_violations,
            "high_severity_violations": high_severity,
            "medium_severity_violations": medium_severity,
            "critical_violations": critical_violations,
            "affected_files": len(affected_files),
            "total_files": total_files,
            "compliant_files": compliant_files,
            "coverage_percentage": coverage_percentage,
            "compliant_modules": compliant_files,
            "non_compliant_modules": list(affected_files)
        }

    def _scan_auth_service_for_uuid4(self) -> List[Dict[str, Any]]:
        """Specialized scan for auth service UUID violations."""
        auth_path = self.service_boundaries["auth_service"]
        return self._scan_service_migration_compliance(auth_path, "auth_service")

    def _validate_auth_security_compliance(self, auth_path: Path) -> Dict[str, Any]:
        """Validate auth service security compliance."""
        # Check for proper UnifiedIDManager usage in auth
        security_patterns = {
            "unified_id_manager_imports": 0,
            "proper_id_type_usage": 0,
            "security_context_usage": 0
        }

        for py_file in auth_path.rglob("*.py"):
            if self._should_exclude_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if re.search(r'from.*unified_id_manager.*import|UnifiedIDManager', content, re.IGNORECASE):
                    security_patterns["unified_id_manager_imports"] += 1

                if re.search(r'IDType\.', content):
                    security_patterns["proper_id_type_usage"] += 1

                if re.search(r'context.*security|security.*context', content, re.IGNORECASE):
                    security_patterns["security_context_usage"] += 1

            except Exception:
                pass

        return security_patterns

    def _scan_shared_libraries_for_uuid4(self) -> List[Dict[str, Any]]:
        """Scan shared libraries for UUID violations."""
        shared_path = self.service_boundaries["shared_libraries"]
        return self._scan_service_migration_compliance(shared_path, "shared_libraries")

    def _extract_library_name(self, file_path: str) -> str:
        """Extract library name from file path."""
        path_parts = Path(file_path).parts
        if "shared" in path_parts:
            shared_index = path_parts.index("shared")
            if shared_index + 1 < len(path_parts):
                return path_parts[shared_index + 1]
        return "unknown"

    def _scan_websocket_code_for_uuid4(self) -> List[Dict[str, Any]]:
        """Scan WebSocket-related code for UUID violations."""
        websocket_violations = []

        # Scan backend WebSocket modules
        backend_path = self.service_boundaries["backend_core"]
        if backend_path.exists():
            websocket_paths = [
                backend_path / "websocket_core",
                backend_path / "websocket",
                backend_path / "routes" / "websocket.py"
            ]

            for ws_path in websocket_paths:
                if ws_path.exists():
                    if ws_path.is_file():
                        violations = self._scan_file_for_migration_violations(ws_path)
                        websocket_violations.extend(violations)
                    else:
                        for py_file in ws_path.rglob("*.py"):
                            violations = self._scan_file_for_migration_violations(py_file)
                            websocket_violations.extend(violations)

        return websocket_violations

    def _analyze_websocket_id_patterns(self) -> Dict[str, Any]:
        """Analyze WebSocket ID generation patterns."""
        # This would analyze actual WebSocket ID usage patterns
        # For now, return placeholder structure
        return {
            "connection_id_patterns": [],
            "event_id_patterns": [],
            "session_id_patterns": [],
            "pattern_consistency": 0.0
        }

    def _classify_websocket_violation(self, violation: Dict[str, Any]) -> str:
        """Classify the type of WebSocket violation."""
        line_content = violation.get("line_content", "").lower()

        if "connection" in line_content:
            return "connection_id_compliance"
        elif "event" in line_content:
            return "event_id_compliance"
        elif "session" in line_content:
            return "session_id_compliance"
        else:
            return "other_compliance"

    def _comprehensive_service_analysis(self, service_path: Path, service_name: str) -> Dict[str, Any]:
        """Perform comprehensive migration analysis for a service."""
        violations = self._scan_service_migration_compliance(service_path, service_name)
        compliance_report = self._generate_compliance_report(violations, service_name)

        return {
            "status": "analyzed",
            "total_violations": len(violations),
            "compliance_percentage": compliance_report["coverage_percentage"],
            "critical_violations": compliance_report["critical_violations"],
            "migration_priority": self._calculate_migration_priority(service_name, violations),
            "estimated_migration_effort": self._estimate_migration_effort(violations)
        }

    def _calculate_overall_migration_metrics(self, migration_dashboard: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall migration metrics across all services."""
        total_violations = 0
        total_files = 0
        total_compliant_files = 0

        for service_name, service_data in migration_dashboard.items():
            if service_data.get("status") == "analyzed":
                total_violations += service_data.get("total_violations", 0)

        # Calculate weighted compliance based on service importance
        service_weights = {
            "backend_core": 0.4,
            "auth_service": 0.3,
            "shared_libraries": 0.2,
            "frontend_lib": 0.05,
            "scripts": 0.05
        }

        weighted_compliance = 0.0
        for service_name, weight in service_weights.items():
            if service_name in migration_dashboard:
                service_compliance = migration_dashboard[service_name].get("compliance_percentage", 0)
                weighted_compliance += service_compliance * weight

        return {
            "total_violations": total_violations,
            "overall_compliance_percentage": weighted_compliance,
            "services_analyzed": len([s for s in migration_dashboard.values()
                                    if s.get("status") == "analyzed"]),
            "migration_readiness": "ready" if weighted_compliance >= 90 else "not_ready"
        }

    def _calculate_migration_priority(self, service_name: str, violations: List[Dict[str, Any]]) -> str:
        """Calculate migration priority for a service."""
        critical_services = ["backend_core", "auth_service"]
        high_violation_threshold = 10

        if service_name in critical_services:
            return "critical"
        elif len(violations) > high_violation_threshold:
            return "high"
        elif len(violations) > 0:
            return "medium"
        else:
            return "low"

    def _estimate_migration_effort(self, violations: List[Dict[str, Any]]) -> str:
        """Estimate migration effort based on violations."""
        total_violations = len(violations)

        if total_violations == 0:
            return "complete"
        elif total_violations < 5:
            return "low"
        elif total_violations < 20:
            return "medium"
        else:
            return "high"

    def _benchmark_unified_id_generation(self, iterations: int) -> float:
        """Benchmark UnifiedIDManager ID generation performance."""
        start_time = time.time()

        for _ in range(iterations):
            self.unified_id_manager.generate_id(IDType.USER)

        return time.time() - start_time

    def _benchmark_uuid4_generation(self, iterations: int) -> float:
        """Benchmark uuid.uuid4() generation performance."""
        import uuid

        start_time = time.time()

        for _ in range(iterations):
            str(uuid.uuid4())

        return time.time() - start_time

    def _benchmark_concurrent_unified_generation(self, iterations: int, threads: int) -> float:
        """Benchmark concurrent UnifiedIDManager performance."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        def generate_batch(batch_size):
            for _ in range(batch_size):
                self.unified_id_manager.generate_id(IDType.USER)

        start_time = time.time()
        batch_size = iterations // threads

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(generate_batch, batch_size) for _ in range(threads)]
            for future in futures:
                future.result()

        return time.time() - start_time

    def _benchmark_concurrent_uuid4_generation(self, iterations: int, threads: int) -> float:
        """Benchmark concurrent uuid.uuid4() performance."""
        import uuid
        from concurrent.futures import ThreadPoolExecutor

        def generate_batch(batch_size):
            for _ in range(batch_size):
                str(uuid.uuid4())

        start_time = time.time()
        batch_size = iterations // threads

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(generate_batch, batch_size) for _ in range(threads)]
            for future in futures:
                future.result()

        return time.time() - start_time

    def _generate_legacy_uuid4_ids(self, count: int) -> List[str]:
        """Generate legacy UUID4 format IDs for testing."""
        import uuid
        return [str(uuid.uuid4()) for _ in range(count)]

    def _generate_unified_manager_ids(self, count: int) -> List[str]:
        """Generate UnifiedIDManager format IDs for testing."""
        ids = []
        id_types = [IDType.USER, IDType.SESSION, IDType.REQUEST, IDType.EXECUTION]

        for i in range(count):
            id_type = id_types[i % len(id_types)]
            ids.append(self.unified_id_manager.generate_id(id_type))

        return ids

    def _is_valid_id_format_compatible(self, id_value: str) -> bool:
        """Test ID format compatibility."""
        return self.unified_id_manager.is_valid_id_format_compatible(id_value)

    def _test_cross_format_operations(self, legacy_ids: List[str], new_ids: List[str]) -> List[Dict[str, Any]]:
        """Test operations across different ID formats."""
        issues = []

        # Test validation consistency
        for legacy_id in legacy_ids[:5]:  # Test subset
            if not self._is_valid_id_format_compatible(legacy_id):
                issues.append({
                    "type": "legacy_validation_failed",
                    "id": legacy_id,
                    "issue": "Legacy ID should validate during migration period"
                })

        for new_id in new_ids[:5]:  # Test subset
            if not self._is_valid_id_format_compatible(new_id):
                issues.append({
                    "type": "new_validation_failed",
                    "id": new_id,
                    "issue": "New ID format should validate"
                })

        return issues

    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from migration scanning."""
        exclude_patterns = [
            r".*test.*\.py$",
            r".*tests.*\.py$",
            r".*__pycache__.*",
            r".*\.pyc$",
            r".*migration.*\.py$"
        ]

        file_str = str(file_path)
        return any(re.search(pattern, file_str, re.IGNORECASE) for pattern in exclude_patterns)

    def _count_service_files(self, service_name: str) -> int:
        """Count total Python files in a service."""
        service_path = self.service_boundaries.get(service_name)
        if not service_path or not service_path.exists():
            return 0

        count = 0
        for py_file in service_path.rglob("*.py"):
            if not self._should_exclude_file(py_file):
                count += 1

        return count


if __name__ == "__main__":
    # Run migration compliance tests
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])