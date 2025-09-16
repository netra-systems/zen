#!/usr/bin/env python
"""
ISSUE #1176 - SSOT INFRASTRUCTURE INCONSISTENCY VALIDATION
=========================================================

This test suite validates SSOT (Single Source of Truth) infrastructure and exposes:
1. SSOT compliance claims vs reality gaps
2. Duplicate implementations violating SSOT principles
3. Inconsistent test framework usage patterns
4. Documentation vs implementation discrepancies

BUSINESS IMPACT: SSOT violations create maintenance burden and hidden bugs
"""

import pytest
import subprocess
import sys
import os
import json
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


class TestSSOTInfrastructureInconsistency:
    """Validate SSOT infrastructure consistency claims vs reality."""

    def test_ssot_compliance_claims_vs_reality(self):
        """
        Compare SSOT compliance claims in documentation against actual implementation.

        This exposes the gap between claimed 98.7% SSOT compliance and reality.
        """
        # Check for SSOT compliance documentation claims
        compliance_claims = {}

        # Look for compliance reports and claims
        report_files = [
            PROJECT_ROOT / "reports" / "MASTER_WIP_STATUS.md",
            PROJECT_ROOT / "CLAUDE.md",
            PROJECT_ROOT / "reports" / "DEFINITION_OF_DONE_CHECKLIST.md"
        ]

        for report_file in report_files:
            if report_file.exists():
                with open(report_file, 'r') as f:
                    content = f.read()

                # Look for compliance percentage claims
                import re
                compliance_matches = re.findall(r'(\d+\.?\d*)%.*(?:compliance|SSOT)', content, re.IGNORECASE)
                if compliance_matches:
                    compliance_claims[str(report_file)] = compliance_matches

        print(f"Found SSOT compliance claims: {json.dumps(compliance_claims, indent=2)}")

        # Now validate actual SSOT compliance by checking for violations
        ssot_violations = self._detect_ssot_violations()

        # If high compliance is claimed but violations exist, that's a discrepancy
        has_high_compliance_claims = any(
            float(claim.replace('%', '')) > 90
            for claims in compliance_claims.values()
            for claim in claims
        )

        if has_high_compliance_claims and ssot_violations:
            violation_details = json.dumps(ssot_violations[:10], indent=2)  # First 10 violations
            pytest.fail(f"SSOT COMPLIANCE REALITY GAP: High compliance claimed but {len(ssot_violations)} violations found:\n{violation_details}")

    def _detect_ssot_violations(self) -> List[Dict[str, Any]]:
        """
        Detect actual SSOT violations in the codebase.
        """
        violations = []

        # Look for duplicate test base classes (should use SSOT BaseTestCase)
        test_files = list(PROJECT_ROOT.glob("**/test_*.py"))

        base_class_patterns = {}

        for test_file in test_files:
            try:
                with open(test_file, 'r') as f:
                    content = f.read()

                # Look for base class inheritance patterns
                import re
                class_matches = re.findall(r'class.*\((.*TestCase[^)]*)\):', content)

                for match in class_matches:
                    base_class = match.strip()
                    if base_class not in base_class_patterns:
                        base_class_patterns[base_class] = []
                    base_class_patterns[base_class].append(str(test_file))

            except Exception as e:
                violations.append({
                    "type": "file_read_error",
                    "file": str(test_file),
                    "error": str(e)
                })

        # Detect non-SSOT base class usage
        for base_class, files in base_class_patterns.items():
            if ("SSot" not in base_class and
                base_class != "unittest.TestCase" and
                base_class != "pytest.TestCase" and
                len(files) > 1):
                violations.append({
                    "type": "non_ssot_base_class",
                    "base_class": base_class,
                    "files": files,
                    "violation_count": len(files)
                })

        return violations

    def test_duplicate_mock_implementations(self):
        """
        Detect duplicate mock implementations that violate SSOT mock factory principle.
        """
        mock_violations = []

        # Search for mock implementations across test files
        test_files = list(PROJECT_ROOT.glob("**/test_*.py"))

        mock_patterns = {}

        for test_file in test_files:
            try:
                with open(test_file, 'r') as f:
                    content = f.read()

                # Look for mock creation patterns
                import re
                mock_matches = re.findall(r'(Mock\w+|@patch|mock\.)', content)

                if mock_matches:
                    for mock_pattern in set(mock_matches):  # Unique patterns
                        if mock_pattern not in mock_patterns:
                            mock_patterns[mock_pattern] = []
                        mock_patterns[mock_pattern].append(str(test_file))

            except Exception as e:
                mock_violations.append({
                    "type": "file_read_error",
                    "file": str(test_file),
                    "error": str(e)
                })

        # Detect potential SSOT violations in mock usage
        for pattern, files in mock_patterns.items():
            if len(files) > 5:  # Pattern used in many files - potential SSOT violation
                mock_violations.append({
                    "type": "duplicate_mock_pattern",
                    "pattern": pattern,
                    "files": files[:10],  # First 10 files
                    "total_files": len(files)
                })

        if mock_violations:
            violation_details = json.dumps(mock_violations, indent=2)
            pytest.fail(f"DUPLICATE MOCK IMPLEMENTATIONS: {len(mock_violations)} SSOT violations found:\n{violation_details}")

    def test_test_framework_consistency(self):
        """
        Validate consistent usage of test framework patterns.
        """
        framework_inconsistencies = []

        # Check for inconsistent test runner usage
        test_runner_patterns = {
            "unified_test_runner.py": 0,
            "pytest.main": 0,
            "subprocess.run.*pytest": 0,
            "python.*-m.*pytest": 0
        }

        test_files = list(PROJECT_ROOT.glob("**/test_*.py"))

        for test_file in test_files:
            try:
                with open(test_file, 'r') as f:
                    content = f.read()

                # Count different test runner patterns
                if "unified_test_runner" in content:
                    test_runner_patterns["unified_test_runner.py"] += 1
                if "pytest.main" in content:
                    test_runner_patterns["pytest.main"] += 1
                if "subprocess.run" in content and "pytest" in content:
                    test_runner_patterns["subprocess.run.*pytest"] += 1
                if "python" in content and "-m" in content and "pytest" in content:
                    test_runner_patterns["python.*-m.*pytest"] += 1

            except Exception as e:
                framework_inconsistencies.append({
                    "type": "file_read_error",
                    "file": str(test_file),
                    "error": str(e)
                })

        # Analyze patterns for inconsistency
        total_patterns = sum(test_runner_patterns.values())
        if total_patterns > 0:
            pattern_percentages = {
                pattern: (count / total_patterns) * 100
                for pattern, count in test_runner_patterns.items()
            }

            # If no single pattern dominates (> 70%), it indicates inconsistency
            max_percentage = max(pattern_percentages.values())
            if max_percentage < 70:
                framework_inconsistencies.append({
                    "type": "test_runner_inconsistency",
                    "patterns": test_runner_patterns,
                    "percentages": pattern_percentages,
                    "dominant_pattern_percentage": max_percentage
                })

        if framework_inconsistencies:
            inconsistency_details = json.dumps(framework_inconsistencies, indent=2)
            pytest.fail(f"TEST FRAMEWORK INCONSISTENCIES: {len(framework_inconsistencies)} inconsistencies found:\n{inconsistency_details}")

    def test_configuration_ssot_compliance(self):
        """
        Validate SSOT compliance in configuration management.
        """
        config_violations = []

        # Look for direct os.environ usage (violates SSOT IsolatedEnvironment pattern)
        python_files = list(PROJECT_ROOT.glob("**/*.py"))

        direct_environ_usage = []

        for py_file in python_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()

                # Look for direct os.environ usage
                import re
                environ_matches = re.findall(r'os\.environ', content)

                if environ_matches and "isolated_environment" not in content.lower():
                    direct_environ_usage.append({
                        "file": str(py_file),
                        "environ_usages": len(environ_matches)
                    })

            except Exception as e:
                config_violations.append({
                    "type": "file_read_error",
                    "file": str(py_file),
                    "error": str(e)
                })

        if direct_environ_usage:
            config_violations.append({
                "type": "direct_environ_usage_violation",
                "files": direct_environ_usage,
                "total_violations": len(direct_environ_usage)
            })

        # Look for multiple configuration patterns
        config_patterns = {
            "get_config()": 0,
            "IsolatedEnvironment": 0,
            "os.environ": 0,
            "config.py": 0
        }

        for py_file in python_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()

                if "get_config()" in content:
                    config_patterns["get_config()"] += 1
                if "IsolatedEnvironment" in content:
                    config_patterns["IsolatedEnvironment"] += 1
                if "os.environ" in content:
                    config_patterns["os.environ"] += 1
                if "config.py" in str(py_file):
                    config_patterns["config.py"] += 1

            except Exception:
                pass

        # Check for configuration pattern inconsistency
        total_config_usage = sum(config_patterns.values())
        if total_config_usage > 0:
            if config_patterns["os.environ"] > config_patterns["IsolatedEnvironment"]:
                config_violations.append({
                    "type": "config_pattern_inconsistency",
                    "issue": "More direct os.environ usage than IsolatedEnvironment",
                    "patterns": config_patterns
                })

        if config_violations:
            violation_details = json.dumps(config_violations, indent=2)
            pytest.fail(f"CONFIGURATION SSOT VIOLATIONS: {len(config_violations)} violations found:\n{violation_details}")

    def test_documentation_vs_implementation_gaps(self):
        """
        Detect gaps between documented SSOT patterns and actual implementation.
        """
        documentation_gaps = []

        # Check if documented SSOT classes actually exist and are used
        ssot_documentation_claims = [
            ("test_framework.ssot.base_test_case.SSotBaseTestCase", "SSOT Base Test Case"),
            ("test_framework.ssot.mock_factory.SSotMockFactory", "SSOT Mock Factory"),
            ("test_framework.unified_docker_manager.UnifiedDockerManager", "SSOT Docker Manager"),
            ("tests.unified_test_runner.py", "SSOT Test Runner"),
        ]

        for import_path, description in ssot_documentation_claims:
            try:
                if import_path.endswith('.py'):
                    # Check file existence
                    file_path = PROJECT_ROOT / import_path
                    if not file_path.exists():
                        documentation_gaps.append({
                            "type": "missing_documented_file",
                            "path": import_path,
                            "description": description
                        })
                else:
                    # Try importing the module
                    result = subprocess.run([
                        sys.executable, '-c',
                        f'import {import_path}; print("EXISTS: {import_path}")'
                    ], capture_output=True, text=True, cwd=PROJECT_ROOT)

                    if result.returncode != 0:
                        documentation_gaps.append({
                            "type": "missing_documented_import",
                            "import": import_path,
                            "description": description,
                            "error": result.stderr.strip()
                        })

            except Exception as e:
                documentation_gaps.append({
                    "type": "documentation_verification_error",
                    "import": import_path,
                    "description": description,
                    "error": str(e)
                })

        if documentation_gaps:
            gap_details = json.dumps(documentation_gaps, indent=2)
            pytest.fail(f"DOCUMENTATION VS IMPLEMENTATION GAPS: {len(documentation_gaps)} gaps found:\n{gap_details}")

    def test_test_infrastructure_health_claims_validation(self):
        """
        Validate health claims made in MASTER_WIP_STATUS.md against actual infrastructure state.
        """
        health_claim_violations = []

        # Read the master status file
        status_file = PROJECT_ROOT / "reports" / "MASTER_WIP_STATUS.md"

        if not status_file.exists():
            pytest.fail("MASTER_WIP_STATUS.md not found - cannot validate health claims")

        with open(status_file, 'r') as f:
            status_content = f.read()

        # Extract health claims
        import re
        health_claims = {
            "system_health": re.search(r'System Health:\s*(\d+)%', status_content),
            "ssot_compliance": re.search(r'SSOT.*?(\d+\.?\d*)%', status_content),
            "test_coverage": re.search(r'Coverage.*?(\d+)%', status_content)
        }

        print(f"Found health claims: {health_claims}")

        # Now validate these claims against reality
        # 1. Check if system is actually healthy by running basic tests
        basic_health_check = subprocess.run([
            sys.executable, '-c',
            'import netra_backend.app.config; print("Basic import works")'
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)

        if basic_health_check.returncode != 0 and health_claims["system_health"]:
            claimed_health = health_claims["system_health"].group(1)
            if int(claimed_health) > 80:
                health_claim_violations.append({
                    "type": "system_health_claim_violation",
                    "claimed_health": f"{claimed_health}%",
                    "reality": "Basic imports failing",
                    "evidence": basic_health_check.stderr.strip()
                })

        # 2. Spot check SSOT compliance
        ssot_violations = self._detect_ssot_violations()
        if len(ssot_violations) > 10 and health_claims["ssot_compliance"]:
            claimed_compliance = health_claims["ssot_compliance"].group(1)
            if float(claimed_compliance) > 90:
                health_claim_violations.append({
                    "type": "ssot_compliance_claim_violation",
                    "claimed_compliance": f"{claimed_compliance}%",
                    "reality": f"{len(ssot_violations)} SSOT violations detected",
                    "sample_violations": ssot_violations[:3]
                })

        if health_claim_violations:
            violation_details = json.dumps(health_claim_violations, indent=2)
            pytest.fail(f"HEALTH CLAIMS VALIDATION FAILURES: {len(health_claim_violations)} claim violations:\n{violation_details}")


if __name__ == "__main__":
    # Run this test suite directly
    pytest.main([__file__, "-v", "--tb=short"])