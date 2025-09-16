#!/usr/bin/env python3
"""
SSOT WebSocket Compliance Validation Tests for Issue #1070

Tests designed to FAIL initially to detect current WebSocket SSOT compliance
violations and PASS after remediation. These tests enforce SSOT compliance by
validating proper factory patterns, canonical imports, and architectural
consistency across the WebSocket subsystem.

Created for GitHub Issue #1070: WebSocket bridge bypass violations - SSOT validation
Part of: SSOT violation detection and prevention system

Business Value: Platform/Internal - System Stability & SSOT Architecture
Ensures WebSocket subsystem follows SSOT principles and proper factory patterns.

DESIGN CRITERIA:
- Tests FAIL initially to prove SSOT violations exist
- Tests PASS after WebSocket subsystem achieves full SSOT compliance
- Provides detailed analysis of factory patterns and architectural consistency
- Uses SSOT test infrastructure patterns
- Validates both static and runtime SSOT compliance

TEST CATEGORIES:
- WebSocket factory pattern SSOT validation
- Canonical import path enforcement
- Architecture consistency verification
- Multi-service SSOT compliance

EXPECTED BEHAVIOR:
- INITIAL STATE: All tests FAIL (detecting SSOT violations)
- POST-REMEDIATION: All tests PASS (full SSOT compliance achieved)
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict
import subprocess

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.unit
class WebSocketSSOTComplianceValidationTests(SSotBaseTestCase):
    """
    SSOT compliance validation tests for WebSocket subsystem.

    These tests are designed to FAIL initially to detect SSOT violations,
    then PASS after remediation. They validate comprehensive SSOT compliance
    across the entire WebSocket subsystem.
    """

    def setup_method(self, method=None):
        """Setup WebSocket SSOT compliance validation test environment."""
        super().setup_method(method)

        # Project paths
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.netra_backend_root = self.project_root / "netra_backend"
        self.websocket_core_path = self.netra_backend_root / "app" / "websocket_core"
        self.agents_path = self.netra_backend_root / "app" / "agents"
        self.auth_service_path = self.project_root / "auth_service"
        self.shared_path = self.project_root / "shared"

        # Canonical SSOT WebSocket patterns (MUST BE USED)
        self.canonical_websocket_imports = [
            "from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
            "from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager",
            "from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry",
        ]

        # SSOT WebSocket factory patterns (CANONICAL)
        self.canonical_factory_patterns = [
            r"create_agent_websocket_bridge\s*\(",
            r"AgentRegistry\s*\(",
            r"get_websocket_manager\s*\(",
        ]

        # Non-SSOT patterns (SHOULD BE ELIMINATED)
        self.non_ssot_patterns = [
            r"WebSocketManagerFactory\s*\(",
            r"get_websocket_manager_factory\s*\(",
            r"websocket_factory\.",
            r"create_websocket_manager\s*\(",
            r"WebSocketFactory\s*\(",
        ]

        # Service-specific SSOT requirements
        self.service_ssot_requirements = {
            "netra_backend": {
                "websocket_manager_path": "netra_backend/app/websocket_core/websocket_manager.py",
                "agent_registry_path": "netra_backend/app/agents/supervisor/agent_registry.py",
                "canonical_imports": [
                    "from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
                    "from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry",
                ],
                "forbidden_imports": [
                    "from netra_backend.app.websocket_core.websocket_manager_factory import",
                ]
            },
            "auth_service": {
                "websocket_dependency": False,  # Auth service should not depend on WebSocket
                "forbidden_imports": [
                    "from netra_backend.app.websocket_core",
                ]
            },
            "shared": {
                "websocket_dependency": False,  # Shared should not depend on WebSocket
                "forbidden_imports": [
                    "from netra_backend.app.websocket_core",
                ]
            }
        }

        # Expected SSOT architecture files
        self.expected_ssot_files = [
            "netra_backend/app/websocket_core/websocket_manager.py",
            "netra_backend/app/agents/supervisor/agent_registry.py",
            "netra_backend/app/services/agent_websocket_bridge.py",
        ]

        # Known SSOT violations to detect
        self.known_ssot_violations = {
            "factory_proliferation": [
                "netra_backend/app/websocket_core/websocket_manager_factory.py",
                "netra_backend/app/websocket_core/factory.py",
            ],
            "direct_imports_in_agents": [
                "netra_backend/app/agents/supervisor/mcp_execution_engine.py",
                "netra_backend/app/agents/supervisor/pipeline_executor.py",
                "netra_backend/app/agents/tool_dispatcher.py",
            ],
            "cross_service_violations": [
                "auth_service/*/websocket*",
                "shared/*/websocket*",
            ]
        }

        # Record test start metrics
        self.record_metric("test_category", "unit")
        self.record_metric("ssot_focus", "websocket_ssot_compliance_validation")
        self.record_metric("services_count", len(self.service_ssot_requirements))
        self.record_metric("expected_ssot_files", len(self.expected_ssot_files))

    def _scan_file_for_patterns(self, file_path: Path, patterns: List[str]) -> List[Tuple[int, str, str]]:
        """
        Scan file for matching patterns and return detailed matches.

        Args:
            file_path: Path to file to scan
            patterns: List of regex patterns to search for

        Returns:
            List of (line_number, match_text, pattern_matched) tuples
        """
        matches = []
        if not file_path.exists() or not file_path.is_file():
            return matches

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        matches.append((line_num, line.strip(), pattern))
        except Exception:
            # Skip files that can't be read
            pass

        return matches

    def _scan_directory_for_patterns(self, directory: Path, patterns: List[str],
                                   file_extensions: Set[str] = {'.py'}) -> Dict[str, List[Tuple[int, str, str]]]:
        """
        Recursively scan directory for pattern matches.

        Args:
            directory: Directory to scan recursively
            patterns: List of regex patterns to search for
            file_extensions: Set of file extensions to include

        Returns:
            Dictionary mapping relative file paths to list of (line_number, match, pattern) tuples
        """
        matches = {}

        if not directory.exists():
            return matches

        for file_path in directory.rglob('*'):
            if file_path.suffix in file_extensions and file_path.is_file():
                # Skip test files and deprecated backups
                relative_path = str(file_path.relative_to(self.project_root))
                if any(skip in relative_path for skip in ['test_', 'tests/', '.deprecated_backup']):
                    continue

                file_matches = self._scan_file_for_patterns(file_path, patterns)
                if file_matches:
                    matches[relative_path] = file_matches

        return matches

    def _analyze_websocket_imports_ast(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze WebSocket-related imports using AST for precise detection.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            Dictionary containing import analysis results
        """
        if not file_path.exists() or not file_path.suffix == '.py':
            return {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
        except:
            return {}

        import_analysis = {
            'websocket_imports': [],
            'factory_imports': [],
            'canonical_imports': [],
            'violation_imports': [],
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module
                    if 'websocket' in module_name.lower():
                        for alias in node.names:
                            import_info = {
                                'module': module_name,
                                'name': alias.name,
                                'line': node.lineno,
                                'import_type': 'from_import'
                            }

                            # Categorize import
                            if 'websocket_manager_factory' in module_name:
                                import_analysis['factory_imports'].append(import_info)
                                import_analysis['violation_imports'].append(import_info)
                            elif 'websocket_manager' in module_name and 'factory' not in module_name:
                                import_analysis['canonical_imports'].append(import_info)
                            elif 'agent_registry' in module_name:
                                import_analysis['canonical_imports'].append(import_info)

                            import_analysis['websocket_imports'].append(import_info)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if 'websocket' in alias.name.lower():
                        import_info = {
                            'name': alias.name,
                            'line': node.lineno,
                            'import_type': 'direct_import'
                        }
                        import_analysis['websocket_imports'].append(import_info)

        return import_analysis

    def _validate_ssot_file_existence(self) -> Dict[str, bool]:
        """
        Validate that expected SSOT files exist.

        Returns:
            Dictionary mapping file paths to existence status
        """
        file_existence = {}

        for ssot_file in self.expected_ssot_files:
            file_path = self.project_root / ssot_file
            file_existence[ssot_file] = file_path.exists()

        return file_existence

    def test_websocket_canonical_import_patterns_enforced(self):
        """
        Test that WebSocket imports use canonical SSOT patterns exclusively.

        **EXPECTED TO FAIL INITIALLY** - Should detect non-canonical import violations
        **EXPECTED TO PASS AFTER REMEDIATION** - All imports use canonical patterns

        This test validates that all WebSocket-related imports follow SSOT
        canonical patterns and eliminate deprecated factory imports.
        """
        self.record_metric("test_method", "websocket_canonical_import_patterns_enforced")
        self.record_metric("expected_initial_result", "FAIL")

        # Scan for canonical import usage
        canonical_import_patterns = [
            r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+WebSocketManager",
            r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+get_websocket_manager",
            r"from\s+netra_backend\.app\.agents\.supervisor\.agent_registry\s+import\s+AgentRegistry",
        ]

        canonical_usage = self._scan_directory_for_patterns(
            self.project_root,
            canonical_import_patterns
        )

        # Scan for non-canonical import violations
        non_canonical_patterns = [
            r"from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import",
            r"from\s+netra_backend\.app\.websocket_core\.factory\s+import",
            r"from\s+.*websocket.*factory.*\s+import",
            r"import.*websocket.*factory",
        ]

        non_canonical_usage = self._scan_directory_for_patterns(
            self.project_root,
            non_canonical_patterns
        )

        # Calculate import compliance metrics
        canonical_files = len(canonical_usage)
        canonical_instances = sum(len(matches) for matches in canonical_usage.values())
        non_canonical_files = len(non_canonical_usage)
        non_canonical_instances = sum(len(matches) for matches in non_canonical_usage.values())

        total_websocket_imports = canonical_instances + non_canonical_instances
        if total_websocket_imports > 0:
            canonical_import_ratio = canonical_instances / total_websocket_imports
        else:
            canonical_import_ratio = 0.0

        self.record_metric("canonical_import_files", canonical_files)
        self.record_metric("canonical_import_instances", canonical_instances)
        self.record_metric("non_canonical_import_files", non_canonical_files)
        self.record_metric("non_canonical_import_instances", non_canonical_instances)
        self.record_metric("canonical_import_ratio", canonical_import_ratio)

        # Analyze import pattern violations by category
        violation_categories = defaultdict(int)
        for file_path, matches in non_canonical_usage.items():
            for line_num, match_text, pattern in matches:
                if "websocket_manager_factory" in match_text:
                    violation_categories["factory_import"] += 1
                elif "websocket.*factory" in pattern:
                    violation_categories["generic_factory"] += 1

        for category, count in violation_categories.items():
            self.record_metric(f"violation_category_{category}", count)

        # Canonical import enforcement requires 100% canonical usage
        if non_canonical_instances > 0 or canonical_import_ratio < 1.0:
            failure_message = [
                f"❌ WEBSOCKET CANONICAL IMPORT PATTERNS NOT ENFORCED ❌",
                f"",
                f"Canonical Import Ratio: {canonical_import_ratio:.1%} (Target: 100%)",
                f"Canonical Imports: {canonical_instances} instances across {canonical_files} files",
                f"Non-Canonical Imports: {non_canonical_instances} instances across {non_canonical_files} files",
                f"",
                f"🚨 SSOT IMPORT VIOLATION: {non_canonical_instances} non-canonical imports detected",
                f"",
                f"VIOLATION CATEGORIES:",
            ]

            for category, count in violation_categories.items():
                failure_message.append(f"• {category.replace('_', ' ').title()}: {count} instances")

            failure_message.append(f"")
            failure_message.append(f"NON-CANONICAL IMPORT VIOLATIONS:")

            for file_path, matches in non_canonical_usage.items():
                failure_message.append(f"")
                failure_message.append(f"📁 File: {file_path}")
                for line_num, match_text, pattern in matches:
                    failure_message.append(f"   Line {line_num}: {match_text}")

            failure_message.append(f"")
            failure_message.append(f"CANONICAL IMPORTS IN USE:")

            for file_path, matches in canonical_usage.items():
                failure_message.append(f"✅ {file_path}: {len(matches)} canonical imports")

            failure_message.extend([
                f"",
                f"🔧 CANONICAL IMPORT REMEDIATION:",
                f"",
                f"❌ ELIMINATE NON-CANONICAL IMPORTS:",
                f"   from netra_backend.app.websocket_core.websocket_manager_factory import *",
                f"   from netra_backend.app.websocket_core.canonical_imports import create_websocket_manager",
                f"   import websocket_factory",
                f"",
                f"✅ USE CANONICAL SSOT IMPORTS:",
                f"   from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
                f"   from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager",
                f"   from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry",
                f"",
                f"📋 IMPORT STANDARDIZATION STEPS:",
                f"1. Replace all factory imports with canonical WebSocketManager imports",
                f"2. Update agent imports to use AgentRegistry for bridge pattern",
                f"3. Remove deprecated factory-based imports",
                f"4. Validate import consistency across all services",
                f"5. Update SSOT_IMPORT_REGISTRY.md with canonical paths",
                f"",
                f"🎯 CANONICAL IMPORT SUCCESS CRITERIA:",
                f"• 100% canonical import ratio",
                f"• Zero non-canonical factory imports",
                f"• Consistent SSOT import patterns across services",
                f"• This test PASSES after remediation",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state
        self.record_metric("canonical_imports_enforced", True)
        print("✅ WEBSOCKET CANONICAL IMPORT PATTERNS ENFORCED")
        print(f"✅ Canonical Import Ratio: {canonical_import_ratio:.1%}")
        print(f"✅ Canonical Imports: {canonical_instances} instances")

    def test_websocket_ssot_factory_pattern_compliance(self):
        """
        Test that WebSocket factory patterns follow SSOT principles.

        **EXPECTED TO FAIL INITIALLY** - Should detect factory proliferation violations
        **EXPECTED TO PASS AFTER REMEDIATION** - Single canonical factory pattern

        This test validates that WebSocket factory patterns are consolidated
        according to SSOT principles with proper user isolation.
        """
        self.record_metric("test_method", "websocket_ssot_factory_pattern_compliance")
        self.record_metric("expected_initial_result", "FAIL")

        # Scan for canonical SSOT factory patterns
        canonical_factory_usage = self._scan_directory_for_patterns(
            self.project_root,
            self.canonical_factory_patterns
        )

        # Scan for non-SSOT factory violations
        non_ssot_factory_usage = self._scan_directory_for_patterns(
            self.project_root,
            self.non_ssot_patterns
        )

        # Validate expected SSOT files exist
        ssot_file_existence = self._validate_ssot_file_existence()

        canonical_factory_files = len(canonical_factory_usage)
        canonical_factory_instances = sum(len(matches) for matches in canonical_factory_usage.values())
        non_ssot_factory_files = len(non_ssot_factory_usage)
        non_ssot_factory_instances = sum(len(matches) for matches in non_ssot_factory_usage.values())

        # Check for factory file proliferation
        factory_files_found = []
        if self.websocket_core_path.exists():
            for file_path in self.websocket_core_path.rglob('*factory*.py'):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(self.project_root))
                    factory_files_found.append(relative_path)

        factory_proliferation_count = len(factory_files_found)

        # Calculate SSOT factory compliance
        total_factory_usage = canonical_factory_instances + non_ssot_factory_instances
        if total_factory_usage > 0:
            ssot_factory_compliance = canonical_factory_instances / total_factory_usage
        else:
            ssot_factory_compliance = 0.0

        # Count missing SSOT files
        missing_ssot_files = [file for file, exists in ssot_file_existence.items() if not exists]

        self.record_metric("canonical_factory_files", canonical_factory_files)
        self.record_metric("canonical_factory_instances", canonical_factory_instances)
        self.record_metric("non_ssot_factory_files", non_ssot_factory_files)
        self.record_metric("non_ssot_factory_instances", non_ssot_factory_instances)
        self.record_metric("factory_proliferation_count", factory_proliferation_count)
        self.record_metric("ssot_factory_compliance", ssot_factory_compliance)
        self.record_metric("missing_ssot_files", len(missing_ssot_files))

        # SSOT factory pattern compliance requirements
        compliance_violations = []

        if non_ssot_factory_instances > 0:
            compliance_violations.append(f"{non_ssot_factory_instances} non-SSOT factory patterns detected")

        if factory_proliferation_count > 1:  # Allow one canonical factory
            compliance_violations.append(f"{factory_proliferation_count} factory files found (should be ≤1)")

        if ssot_factory_compliance < 1.0 and total_factory_usage > 0:
            compliance_violations.append(f"SSOT factory compliance: {ssot_factory_compliance:.1%} (target: 100%)")

        if missing_ssot_files:
            compliance_violations.append(f"{len(missing_ssot_files)} expected SSOT files missing")

        if compliance_violations:
            failure_message = [
                f"❌ WEBSOCKET SSOT FACTORY PATTERN COMPLIANCE FAILED ❌",
                f"",
                f"SSOT Factory Compliance: {ssot_factory_compliance:.1%} (Target: 100%)",
                f"Canonical Factory Usage: {canonical_factory_instances} instances",
                f"Non-SSOT Factory Usage: {non_ssot_factory_instances} instances",
                f"Factory Files Found: {factory_proliferation_count}",
                f"Missing SSOT Files: {len(missing_ssot_files)}",
                f"",
                f"COMPLIANCE VIOLATIONS:",
            ]

            for violation in compliance_violations:
                failure_message.append(f"❌ {violation}")

            if non_ssot_factory_usage:
                failure_message.append(f"")
                failure_message.append(f"NON-SSOT FACTORY VIOLATIONS:")
                for file_path, matches in non_ssot_factory_usage.items():
                    failure_message.append(f"📁 {file_path}")
                    for line_num, match_text, pattern in matches:
                        failure_message.append(f"   Line {line_num}: {match_text}")

            if factory_files_found:
                failure_message.append(f"")
                failure_message.append(f"FACTORY FILE PROLIFERATION:")
                for factory_file in factory_files_found:
                    failure_message.append(f"📁 {factory_file}")

            if missing_ssot_files:
                failure_message.append(f"")
                failure_message.append(f"MISSING SSOT FILES:")
                for missing_file in missing_ssot_files:
                    failure_message.append(f"❌ {missing_file}")

            failure_message.extend([
                f"",
                f"🔧 SSOT FACTORY PATTERN REMEDIATION:",
                f"",
                f"1. Consolidate factory patterns:",
                f"   ❌ Multiple factory files and classes",
                f"   ✅ Single canonical factory: create_agent_websocket_bridge()",
                f"",
                f"2. Eliminate non-SSOT factory usage:",
                f"   ❌ WebSocketManagerFactory(), get_websocket_manager_factory()",
                f"   ✅ AgentRegistry() with bridge pattern",
                f"",
                f"3. Ensure SSOT file structure:",
                f"   ✅ netra_backend/app/websocket_core/websocket_manager.py",
                f"   ✅ netra_backend/app/agents/supervisor/agent_registry.py",
                f"   ✅ netra_backend/app/services/agent_websocket_bridge.py",
                f"",
                f"4. Bridge pattern SSOT compliance:",
                f"   ✅ User isolation through AgentRegistry bridge",
                f"   ✅ No direct WebSocket manager instantiation in agents",
                f"   ✅ Consistent factory usage across all services",
                f"",
                f"🎯 SSOT FACTORY SUCCESS CRITERIA:",
                f"• 100% SSOT factory compliance",
                f"• Single canonical factory pattern",
                f"• All expected SSOT files present",
                f"• Zero factory proliferation violations",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state
        self.record_metric("ssot_factory_compliance_achieved", True)
        print("✅ WEBSOCKET SSOT FACTORY PATTERN COMPLIANCE ACHIEVED")
        print(f"✅ SSOT Factory Compliance: {ssot_factory_compliance:.1%}")
        print(f"✅ Factory Files: {factory_proliferation_count}")

    def test_service_websocket_dependency_isolation(self):
        """
        Test that services maintain proper WebSocket dependency isolation.

        **EXPECTED TO FAIL INITIALLY** - Should detect cross-service dependency violations
        **EXPECTED TO PASS AFTER REMEDIATION** - Proper service isolation maintained

        This test validates that services follow SSOT principles for WebSocket
        dependencies with proper isolation between netra_backend, auth_service, and shared.
        """
        self.record_metric("test_method", "service_websocket_dependency_isolation")
        self.record_metric("expected_initial_result", "FAIL")

        # Analyze each service for WebSocket dependency violations
        service_analysis = {}

        for service_name, requirements in self.service_ssot_requirements.items():
            service_path = getattr(self, f"{service_name}_path", None)
            if not service_path or not service_path.exists():
                continue

            analysis = {
                'websocket_imports': [],
                'forbidden_import_violations': [],
                'dependency_violations': [],
                'compliant': True
            }

            # Scan for WebSocket imports in service
            websocket_import_patterns = [r"from.*websocket.*import", r"import.*websocket"]
            websocket_imports = self._scan_directory_for_patterns(
                service_path,
                websocket_import_patterns
            )

            analysis['websocket_imports'] = websocket_imports

            # Check forbidden imports
            if 'forbidden_imports' in requirements:
                for forbidden_pattern in requirements['forbidden_imports']:
                    forbidden_usage = self._scan_directory_for_patterns(
                        service_path,
                        [forbidden_pattern]
                    )
                    if forbidden_usage:
                        analysis['forbidden_import_violations'].extend(forbidden_usage.items())
                        analysis['compliant'] = False

            # Check WebSocket dependency compliance
            websocket_dependency_allowed = requirements.get('websocket_dependency', True)
            if not websocket_dependency_allowed and websocket_imports:
                analysis['dependency_violations'] = list(websocket_imports.items())
                analysis['compliant'] = False

            service_analysis[service_name] = analysis

        # Calculate service isolation metrics
        compliant_services = sum(1 for analysis in service_analysis.values() if analysis['compliant'])
        total_services = len(service_analysis)
        service_isolation_ratio = compliant_services / total_services if total_services > 0 else 0

        total_violations = sum(
            len(analysis['forbidden_import_violations']) + len(analysis['dependency_violations'])
            for analysis in service_analysis.values()
        )

        self.record_metric("compliant_services", compliant_services)
        self.record_metric("total_services", total_services)
        self.record_metric("service_isolation_ratio", service_isolation_ratio)
        self.record_metric("total_dependency_violations", total_violations)

        # Service isolation compliance requires 100% compliance
        if service_isolation_ratio < 1.0 or total_violations > 0:
            failure_message = [
                f"❌ SERVICE WEBSOCKET DEPENDENCY ISOLATION FAILED ❌",
                f"",
                f"Service Isolation: {service_isolation_ratio:.1%} (Target: 100%)",
                f"Compliant Services: {compliant_services}/{total_services}",
                f"Total Violations: {total_violations}",
                f"",
                f"🚨 SERVICE DEPENDENCY VIOLATION: Cross-service WebSocket dependencies detected",
                f"",
                f"SERVICE ANALYSIS RESULTS:",
            ]

            for service_name, analysis in service_analysis.items():
                status = "✅ COMPLIANT" if analysis['compliant'] else "❌ NON-COMPLIANT"
                failure_message.append(f"")
                failure_message.append(f"📦 Service: {service_name} - {status}")

                if analysis['websocket_imports']:
                    failure_message.append(f"   WebSocket Imports: {len(analysis['websocket_imports'])} files")

                if analysis['forbidden_import_violations']:
                    failure_message.append(f"   Forbidden Import Violations:")
                    for file_path, matches in analysis['forbidden_import_violations'][:3]:  # Show first 3
                        failure_message.append(f"     ❌ {file_path}: {len(matches)} violations")

                if analysis['dependency_violations']:
                    failure_message.append(f"   Dependency Violations:")
                    for file_path, matches in analysis['dependency_violations'][:3]:  # Show first 3
                        failure_message.append(f"     ❌ {file_path}: {len(matches)} violations")

            failure_message.extend([
                f"",
                f"🔧 SERVICE ISOLATION REMEDIATION:",
                f"",
                f"1. netra_backend service (WebSocket allowed):",
                f"   ✅ Can import from netra_backend.app.websocket_core",
                f"   ✅ Can use AgentRegistry bridge pattern",
                f"   ❌ Should not create duplicate WebSocket implementations",
                f"",
                f"2. auth_service (WebSocket forbidden):",
                f"   ❌ Must not import from netra_backend.app.websocket_core",
                f"   ✅ Should use only auth-specific functionality",
                f"   ✅ Communication with netra_backend via API/events only",
                f"",
                f"3. shared service (WebSocket forbidden):",
                f"   ❌ Must not import from netra_backend.app.websocket_core",
                f"   ✅ Should provide only shared utilities",
                f"   ✅ No business logic dependencies",
                f"",
                f"📋 ISOLATION ENFORCEMENT STEPS:",
                f"1. Remove cross-service WebSocket imports",
                f"2. Use proper service communication patterns",
                f"3. Consolidate WebSocket functionality in netra_backend only",
                f"4. Validate service boundary compliance",
                f"",
                f"🎯 SERVICE ISOLATION SUCCESS CRITERIA:",
                f"• 100% service isolation compliance",
                f"• Zero cross-service WebSocket dependencies",
                f"• Proper service boundary enforcement",
                f"• Clean architectural separation",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state
        self.record_metric("service_isolation_achieved", True)
        print("✅ SERVICE WEBSOCKET DEPENDENCY ISOLATION ACHIEVED")
        print(f"✅ Service Isolation: {service_isolation_ratio:.1%}")
        print(f"✅ Compliant Services: {compliant_services}/{total_services}")

    def test_websocket_ssot_architecture_consistency_validation(self):
        """
        Comprehensive validation of WebSocket SSOT architecture consistency.

        **EXPECTED TO PASS AFTER REMEDIATION** - Overall architecture consistency validation

        Validates that the entire WebSocket subsystem achieves consistent SSOT compliance:
        - Canonical import patterns enforced
        - SSOT factory patterns implemented
        - Service dependency isolation maintained
        - Architectural consistency across all components
        """
        self.record_metric("test_method", "websocket_ssot_architecture_consistency_validation")
        self.record_metric("test_type", "comprehensive_validation")

        # Collect comprehensive SSOT architecture metrics
        # Import pattern analysis
        canonical_imports = self._scan_directory_for_patterns(
            self.project_root,
            [r"from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+WebSocketManager"]
        )

        non_canonical_imports = self._scan_directory_for_patterns(
            self.project_root,
            [r"from\s+.*websocket.*factory.*\s+import"]
        )

        # Factory pattern analysis
        canonical_factories = self._scan_directory_for_patterns(
            self.project_root,
            self.canonical_factory_patterns
        )

        non_ssot_factories = self._scan_directory_for_patterns(
            self.project_root,
            self.non_ssot_patterns
        )

        # SSOT file validation
        ssot_file_existence = self._validate_ssot_file_existence()

        # Service isolation analysis
        cross_service_violations = 0
        for service_name, requirements in self.service_ssot_requirements.items():
            if not requirements.get('websocket_dependency', True):
                service_path = getattr(self, f"{service_name}_path", None)
                if service_path and service_path.exists():
                    violations = self._scan_directory_for_patterns(
                        service_path,
                        [r"from.*websocket.*import"]
                    )
                    cross_service_violations += sum(len(matches) for matches in violations.values())

        # Calculate comprehensive metrics
        architecture_metrics = {
            "canonical_imports": sum(len(matches) for matches in canonical_imports.values()),
            "non_canonical_imports": sum(len(matches) for matches in non_canonical_imports.values()),
            "canonical_factories": sum(len(matches) for matches in canonical_factories.values()),
            "non_ssot_factories": sum(len(matches) for matches in non_ssot_factories.values()),
            "ssot_files_present": sum(1 for exists in ssot_file_existence.values() if exists),
            "ssot_files_missing": sum(1 for exists in ssot_file_existence.values() if not exists),
            "cross_service_violations": cross_service_violations,
        }

        # Record comprehensive metrics
        for metric, value in architecture_metrics.items():
            self.record_metric(f"comprehensive_{metric}", value)

        # Calculate overall SSOT architecture consistency score
        total_imports = architecture_metrics["canonical_imports"] + architecture_metrics["non_canonical_imports"]
        if total_imports > 0:
            import_consistency_score = (architecture_metrics["canonical_imports"] / total_imports) * 100
        else:
            import_consistency_score = 0.0

        total_factories = architecture_metrics["canonical_factories"] + architecture_metrics["non_ssot_factories"]
        if total_factories > 0:
            factory_consistency_score = (architecture_metrics["canonical_factories"] / total_factories) * 100
        else:
            factory_consistency_score = 0.0

        total_ssot_files = len(self.expected_ssot_files)
        if total_ssot_files > 0:
            file_consistency_score = (architecture_metrics["ssot_files_present"] / total_ssot_files) * 100
        else:
            file_consistency_score = 0.0

        service_isolation_score = 100 if architecture_metrics["cross_service_violations"] == 0 else 0

        # Overall consistency score (weighted average)
        overall_consistency_score = (
            import_consistency_score * 0.3 +
            factory_consistency_score * 0.3 +
            file_consistency_score * 0.2 +
            service_isolation_score * 0.2
        )

        self.record_metric("import_consistency_score", import_consistency_score)
        self.record_metric("factory_consistency_score", factory_consistency_score)
        self.record_metric("file_consistency_score", file_consistency_score)
        self.record_metric("service_isolation_score", service_isolation_score)
        self.record_metric("overall_consistency_score", overall_consistency_score)

        # SSOT architecture consistency requirements
        consistency_requirements = {
            "100% canonical imports": import_consistency_score == 100.0,
            "100% SSOT factory patterns": factory_consistency_score == 100.0,
            "All SSOT files present": file_consistency_score == 100.0,
            "Complete service isolation": service_isolation_score == 100.0,
            "90%+ overall consistency": overall_consistency_score >= 90.0,
        }

        failed_requirements = [req for req, passed in consistency_requirements.items() if not passed]

        if failed_requirements:
            failure_message = [
                f"❌ WEBSOCKET SSOT ARCHITECTURE CONSISTENCY VALIDATION FAILED ❌",
                f"",
                f"Overall Consistency Score: {overall_consistency_score:.1f}% (Target: ≥90%)",
                f"",
                f"CONSISTENCY SCORE BREAKDOWN:",
                f"• Import Consistency: {import_consistency_score:.1f}% (Weight: 30%)",
                f"• Factory Consistency: {factory_consistency_score:.1f}% (Weight: 30%)",
                f"• File Consistency: {file_consistency_score:.1f}% (Weight: 20%)",
                f"• Service Isolation: {service_isolation_score:.1f}% (Weight: 20%)",
                f"",
                f"ARCHITECTURE METRICS:",
                f"• Canonical Imports: {architecture_metrics['canonical_imports']}",
                f"• Non-Canonical Imports: {architecture_metrics['non_canonical_imports']}",
                f"• Canonical Factories: {architecture_metrics['canonical_factories']}",
                f"• Non-SSOT Factories: {architecture_metrics['non_ssot_factories']}",
                f"• SSOT Files Present: {architecture_metrics['ssot_files_present']}/{total_ssot_files}",
                f"• Cross-Service Violations: {architecture_metrics['cross_service_violations']}",
                f"",
                f"FAILED REQUIREMENTS:",
            ]

            for requirement in failed_requirements:
                failure_message.append(f"❌ {requirement}")

            failure_message.extend([
                f"",
                f"🎯 COMPLETE SSOT ARCHITECTURE CONSISTENCY REMEDIATION:",
                f"• Run all individual WebSocket SSOT compliance tests",
                f"• Fix canonical import pattern violations",
                f"• Consolidate factory patterns according to SSOT principles",
                f"• Ensure all expected SSOT files are present and functional",
                f"• Eliminate cross-service dependency violations",
                f"• Achieve ≥90% overall consistency score",
                f"",
                f"📋 SYSTEMATIC CONSISTENCY REMEDIATION:",
                f"1. Import Pattern Standardization",
                f"   • Replace non-canonical imports with SSOT patterns",
                f"   • Update SSOT_IMPORT_REGISTRY.md with canonical paths",
                f"",
                f"2. Factory Pattern Consolidation",
                f"   • Eliminate factory proliferation",
                f"   • Implement single canonical factory pattern",
                f"",
                f"3. SSOT File Structure Validation",
                f"   • Ensure all expected SSOT files exist",
                f"   • Validate file content follows SSOT principles",
                f"",
                f"4. Service Isolation Enforcement",
                f"   • Remove cross-service WebSocket dependencies",
                f"   • Maintain proper service boundaries",
                f"",
                f"🏆 ARCHITECTURE CONSISTENCY SUCCESS:",
                f"• Achieve comprehensive SSOT compliance",
                f"• Maintain architectural consistency across all components",
                f"• Enable maintainable and scalable WebSocket subsystem",
            ])

            pytest.fail("\n".join(failure_message))

        # Success - Complete SSOT architecture consistency achieved
        self.record_metric("websocket_ssot_architecture_consistent", True)

        print("🏆 WEBSOCKET SSOT ARCHITECTURE CONSISTENCY VALIDATION COMPLETE")
        print(f"✅ Overall Consistency Score: {overall_consistency_score:.1f}%")
        print("✅ All consistency requirements satisfied")
        print("✅ WebSocket SSOT compliance remediation COMPLETE")

    def teardown_method(self, method=None):
        """Clean up after WebSocket SSOT compliance validation tests."""
        # Record final test metrics
        self.record_metric("test_completed", True)

        super().teardown_method(method)