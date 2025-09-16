"""Unit Tests: WebSocket Class Fragmentation Monitoring - Issue #965

PURPOSE: Monitor and detect WebSocket class fragmentation patterns across the system

BUSINESS IMPACT:
- Priority: P2 (Monitoring/Infrastructure)
- Impact: $500K+ ARR system maintenance and stability
- Root Cause: Multiple WebSocket class implementations need continuous monitoring
- Technical Debt: Fragmentation detection and remediation tracking

TEST OBJECTIVES:
1. Monitor import path fragmentation across WebSocket-related modules
2. Detect new WebSocket class implementations being created
3. Validate SSOT compliance through automated monitoring
4. Track fragmentation remediation progress over time
5. Prevent regression to fragmented patterns

EXPECTED BEHAVIOR:
- Tests should FAIL when new fragmentation is introduced
- Tests should PASS when fragmentation is eliminated through SSOT
- Provides monitoring dashboard for fragmentation status

This test suite runs as unit tests and provides continuous monitoring.
"""

import sys
import os
import importlib
import inspect
import ast
import json
import time
from typing import Set, Dict, List, Any, Optional, Tuple
from pathlib import Path
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class WebSocketClassFragmentationMonitoringTests(SSotBaseTestCase, unittest.TestCase):
    """Monitor WebSocket class fragmentation across the system."""

    def setUp(self):
        """Set up fragmentation monitoring environment."""
        super().setUp()
        self.websocket_base_paths = [
            'netra_backend/app/websocket_core',
            'netra_backend/app/core',
            'netra_backend/app/services',
            'netra_backend/app/agents',
            'shared'
        ]
        self.fragmentation_report = {
            'timestamp': time.time(),
            'scan_results': {},
            'violations': [],
            'recommendations': []
        }

    def scan_websocket_classes(self) -> Dict[str, List[Dict[str, Any]]]:
        """Scan the codebase for WebSocket-related classes."""
        websocket_classes = {}

        for base_path in self.websocket_base_paths:
            full_path = os.path.join(project_root, base_path)
            if not os.path.exists(full_path):
                continue

            for root, dirs, files in os.walk(full_path):
                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        file_path = os.path.join(root, file)
                        try:
                            classes = self._extract_websocket_classes_from_file(file_path)
                            if classes:
                                relative_path = os.path.relpath(file_path, project_root)
                                websocket_classes[relative_path] = classes
                        except Exception as e:
                            self.logger.warning(f"Could not analyze {file_path}: {e}")

        return websocket_classes

    def _extract_websocket_classes_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract WebSocket-related classes from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)
            websocket_classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name

                    # Check if this is a WebSocket-related class
                    if self._is_websocket_related_class(class_name, node):
                        class_info = {
                            'name': class_name,
                            'line_number': node.lineno,
                            'bases': [self._get_base_name(base) for base in node.bases],
                            'methods': [method.name for method in node.body if isinstance(method, ast.FunctionDef)],
                            'is_websocket_manager': 'websocketmanager' in class_name.lower(),
                            'is_factory': 'factory' in class_name.lower(),
                            'is_protocol': 'protocol' in class_name.lower(),
                            'docstring': ast.get_docstring(node)
                        }
                        websocket_classes.append(class_info)

            return websocket_classes

        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _is_websocket_related_class(self, class_name: str, node: ast.ClassDef) -> bool:
        """Determine if a class is WebSocket-related."""
        websocket_indicators = [
            'websocket', 'webSocket', 'WebSocket',
            'ws_', 'WS_', 'socket',
            'connection', 'Connection',
            'bridge', 'Bridge',
            'notifier', 'Notifier',
            'event', 'Event'
        ]

        # Check class name
        class_name_lower = class_name.lower()
        if any(indicator.lower() in class_name_lower for indicator in websocket_indicators):
            return True

        # Check base classes
        for base in node.bases:
            base_name = self._get_base_name(base)
            if any(indicator.lower() in base_name.lower() for indicator in websocket_indicators):
                return True

        # Check docstring
        docstring = ast.get_docstring(node)
        if docstring and any(indicator.lower() in docstring.lower() for indicator in websocket_indicators):
            return True

        return False

    def _get_base_name(self, base_node: ast.expr) -> str:
        """Extract base class name from AST node."""
        if isinstance(base_node, ast.Name):
            return base_node.id
        elif isinstance(base_node, ast.Attribute):
            return f"{self._get_base_name(base_node.value)}.{base_node.attr}"
        else:
            return str(base_node)

    def test_websocket_class_count_monitoring(self):
        """
        CLASS COUNT MONITORING: Track the number of WebSocket-related classes.

        EXPECTED BEHAVIOR: Count should decrease as fragmentation is resolved
        """
        websocket_classes = self.scan_websocket_classes()

        total_classes = sum(len(classes) for classes in websocket_classes.values())
        manager_classes = 0
        factory_classes = 0
        protocol_classes = 0

        for file_path, classes in websocket_classes.items():
            for class_info in classes:
                if class_info['is_websocket_manager']:
                    manager_classes += 1
                if class_info['is_factory']:
                    factory_classes += 1
                if class_info['is_protocol']:
                    protocol_classes += 1

        # Log current state
        self.logger.info(f"WebSocket Class Monitoring Results:")
        self.logger.info(f"  Total WebSocket-related classes: {total_classes}")
        self.logger.info(f"  WebSocket Manager classes: {manager_classes}")
        self.logger.info(f"  Factory classes: {factory_classes}")
        self.logger.info(f"  Protocol classes: {protocol_classes}")

        # Update fragmentation report
        self.fragmentation_report['scan_results'] = {
            'total_classes': total_classes,
            'manager_classes': manager_classes,
            'factory_classes': factory_classes,
            'protocol_classes': protocol_classes,
            'files_with_websocket_classes': len(websocket_classes)
        }

        # Define acceptable thresholds for SSOT compliance
        max_acceptable_managers = 2  # Unified manager + legacy compatibility
        max_acceptable_factories = 1  # Single factory pattern
        max_acceptable_total = 15     # Total WebSocket classes

        violations = []

        if manager_classes > max_acceptable_managers:
            violations.append(f"Too many WebSocket Manager classes: {manager_classes} (max: {max_acceptable_managers})")

        if factory_classes > max_acceptable_factories:
            violations.append(f"Too many Factory classes: {factory_classes} (max: {max_acceptable_factories})")

        if total_classes > max_acceptable_total:
            violations.append(f"Too many total WebSocket classes: {total_classes} (max: {max_acceptable_total})")

        self.fragmentation_report['violations'] = violations

        if violations:
            for violation in violations:
                self.logger.error(f"FRAGMENTATION VIOLATION: {violation}")

        # Assert compliance
        self.assertLessEqual(
            manager_classes, max_acceptable_managers,
            f"WEBSOCKET MANAGER FRAGMENTATION: Found {manager_classes} WebSocket Manager classes, "
            f"maximum acceptable is {max_acceptable_managers}. "
            f"Multiple managers indicate SSOT violations requiring consolidation."
        )

    def test_import_path_diversity_monitoring(self):
        """
        IMPORT PATH MONITORING: Track diversity of WebSocket import paths.

        EXPECTED BEHAVIOR: Import path diversity should decrease with SSOT consolidation
        """
        import_paths = set()
        files_analyzed = 0

        # Scan Python files for WebSocket imports
        for base_path in self.websocket_base_paths:
            full_path = os.path.join(project_root, base_path)
            if not os.path.exists(full_path):
                continue

            for root, dirs, files in os.walk(full_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            file_imports = self._extract_websocket_imports(file_path)
                            import_paths.update(file_imports)
                            files_analyzed += 1
                        except Exception as e:
                            self.logger.warning(f"Could not analyze imports in {file_path}: {e}")

        # Analyze import diversity
        total_import_paths = len(import_paths)
        websocket_manager_imports = [imp for imp in import_paths if 'websocket' in imp.lower() and 'manager' in imp.lower()]
        factory_imports = [imp for imp in import_paths if 'factory' in imp.lower() and 'websocket' in imp.lower()]

        self.logger.info(f"Import Path Diversity Analysis:")
        self.logger.info(f"  Files analyzed: {files_analyzed}")
        self.logger.info(f"  Total unique WebSocket import paths: {total_import_paths}")
        self.logger.info(f"  WebSocket Manager import variations: {len(websocket_manager_imports)}")
        self.logger.info(f"  Factory import variations: {len(factory_imports)}")

        # Log specific problematic imports
        if websocket_manager_imports:
            self.logger.info("  WebSocket Manager import paths:")
            for imp in sorted(websocket_manager_imports)[:10]:  # Show first 10
                self.logger.info(f"    {imp}")

        # Update fragmentation report
        self.fragmentation_report['scan_results'].update({
            'total_import_paths': total_import_paths,
            'manager_import_variations': len(websocket_manager_imports),
            'factory_import_variations': len(factory_imports),
            'files_analyzed': files_analyzed
        })

        # Define acceptable thresholds
        max_manager_import_variations = 3  # Canonical + 2 legacy paths
        max_total_import_paths = 25        # Total WebSocket imports

        violations = []

        if len(websocket_manager_imports) > max_manager_import_variations:
            violations.append(f"Too many WebSocket Manager import variations: {len(websocket_manager_imports)} (max: {max_manager_import_variations})")

        if total_import_paths > max_total_import_paths:
            violations.append(f"Too many total WebSocket import paths: {total_import_paths} (max: {max_total_import_paths})")

        self.fragmentation_report['violations'].extend(violations)

        # Assert compliance
        self.assertLessEqual(
            len(websocket_manager_imports), max_manager_import_variations,
            f"IMPORT PATH FRAGMENTATION: Found {len(websocket_manager_imports)} different WebSocket Manager import paths, "
            f"maximum acceptable is {max_manager_import_variations}. "
            f"Import variations: {websocket_manager_imports[:5]}... "
            f"Multiple import paths indicate fragmentation requiring SSOT consolidation."
        )

    def _extract_websocket_imports(self, file_path: str) -> Set[str]:
        """Extract WebSocket-related import statements from a file."""
        websocket_imports = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if self._is_websocket_import(alias.name):
                            websocket_imports.add(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module and self._is_websocket_import(node.module):
                        for alias in node.names:
                            full_import = f"{node.module}.{alias.name}"
                            websocket_imports.add(full_import)

        except Exception as e:
            self.logger.warning(f"Error parsing imports from {file_path}: {e}")

        return websocket_imports

    def _is_websocket_import(self, import_name: str) -> bool:
        """Check if an import is WebSocket-related."""
        websocket_indicators = [
            'websocket', 'webSocket', 'WebSocket',
            'socket', 'connection',
            'bridge', 'notifier', 'event'
        ]

        if not import_name:
            return False

        import_lower = import_name.lower()
        return any(indicator.lower() in import_lower for indicator in websocket_indicators)

    def test_websocket_method_signature_consistency(self):
        """
        METHOD SIGNATURE MONITORING: Check consistency of WebSocket method signatures.

        EXPECTED BEHAVIOR: Method signatures should be consistent across implementations
        """
        websocket_classes = self.scan_websocket_classes()
        method_signatures = {}

        # Common WebSocket methods to monitor
        critical_methods = [
            'send_agent_event',
            'get_websocket_manager',
            'connect',
            'disconnect',
            'send_message',
            'handle_connection'
        ]

        for file_path, classes in websocket_classes.items():
            for class_info in classes:
                if class_info['is_websocket_manager']:
                    for method in class_info['methods']:
                        if method in critical_methods:
                            signature_key = f"{class_info['name']}.{method}"
                            if signature_key not in method_signatures:
                                method_signatures[signature_key] = []
                            method_signatures[signature_key].append(file_path)

        # Analyze method consistency
        inconsistent_methods = []
        for method_name in critical_methods:
            implementations = [sig for sig in method_signatures.keys() if sig.endswith(f".{method_name}")]
            if len(implementations) > 1:
                inconsistent_methods.append({
                    'method': method_name,
                    'implementations': implementations
                })

        if inconsistent_methods:
            self.logger.warning(f"Method signature inconsistencies detected:")
            for inconsistency in inconsistent_methods:
                self.logger.warning(f"  {inconsistency['method']}: {len(inconsistency['implementations'])} implementations")

        # Update fragmentation report
        self.fragmentation_report['scan_results'].update({
            'method_inconsistencies': len(inconsistent_methods),
            'critical_methods_found': len(method_signatures)
        })

        # Generate recommendations
        recommendations = []
        if inconsistent_methods:
            recommendations.append("Standardize method signatures across WebSocket Manager implementations")

        if self.fragmentation_report['scan_results'].get('manager_classes', 0) > 2:
            recommendations.append("Consolidate multiple WebSocket Manager classes into single SSOT implementation")

        if self.fragmentation_report['scan_results'].get('manager_import_variations', 0) > 3:
            recommendations.append("Consolidate WebSocket Manager import paths to single canonical path")

        self.fragmentation_report['recommendations'] = recommendations

        # Method consistency assertion
        max_acceptable_method_inconsistencies = 2

        self.assertLessEqual(
            len(inconsistent_methods), max_acceptable_method_inconsistencies,
            f"METHOD SIGNATURE FRAGMENTATION: Found {len(inconsistent_methods)} inconsistent method signatures, "
            f"maximum acceptable is {max_acceptable_method_inconsistencies}. "
            f"Inconsistent methods: {[inc['method'] for inc in inconsistent_methods]}. "
            f"Method signature variations indicate implementation fragmentation requiring standardization."
        )

    def test_generate_fragmentation_monitoring_report(self):
        """
        MONITORING REPORT: Generate comprehensive fragmentation monitoring report.

        This test always passes but generates monitoring data for tracking progress.
        """
        # Finalize fragmentation report
        self.fragmentation_report['summary'] = {
            'total_violations': len(self.fragmentation_report['violations']),
            'total_recommendations': len(self.fragmentation_report['recommendations']),
            'monitoring_timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.fragmentation_report['timestamp']))
        }

        # Save report to file for tracking
        report_file = os.path.join(project_root, 'tests', 'reports', 'websocket_fragmentation_monitoring.json')
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        try:
            with open(report_file, 'w') as f:
                json.dump(self.fragmentation_report, f, indent=2)
            self.logger.info(f"Fragmentation monitoring report saved to: {report_file}")
        except Exception as e:
            self.logger.warning(f"Could not save monitoring report: {e}")

        # Log summary
        self.logger.info("=== WEBSOCKET FRAGMENTATION MONITORING SUMMARY ===")
        self.logger.info(f"Violations: {self.fragmentation_report['summary']['total_violations']}")
        self.logger.info(f"Recommendations: {self.fragmentation_report['summary']['total_recommendations']}")

        if self.fragmentation_report['violations']:
            self.logger.info("Active Violations:")
            for violation in self.fragmentation_report['violations']:
                self.logger.info(f"  - {violation}")

        if self.fragmentation_report['recommendations']:
            self.logger.info("Recommendations:")
            for recommendation in self.fragmentation_report['recommendations']:
                self.logger.info(f"  - {recommendation}")

        # This test always passes - it's for monitoring only
        self.assertTrue(True, "Fragmentation monitoring report generated successfully")

@pytest.mark.unit
class WebSocketFragmentationRegressionTests(SSotBaseTestCase, unittest.TestCase):
    """Prevent regression to fragmented WebSocket patterns."""

    def test_prevent_new_websocket_manager_classes(self):
        """
        REGRESSION PREVENTION: Prevent creation of new WebSocket Manager classes.

        EXPECTED TO FAIL: If new WebSocket Manager classes are added
        EXPECTED TO PASS: When SSOT is maintained
        """
        # Known acceptable WebSocket Manager classes (baseline)
        acceptable_manager_classes = {
            'UnifiedWebSocketManager',
            'WebSocketManager',
            'WebSocketManagerMode',      # Enum/configuration class
            'WebSocketManagerProtocol'   # Protocol/interface
        }

        websocket_classes = {}
        for base_path in ['netra_backend/app/websocket_core']:
            full_path = os.path.join(project_root, base_path)
            if os.path.exists(full_path):
                for root, dirs, files in os.walk(full_path):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            try:
                                classes = self._find_manager_classes(file_path)
                                if classes:
                                    relative_path = os.path.relpath(file_path, project_root)
                                    websocket_classes[relative_path] = classes
                            except Exception as e:
                                self.logger.warning(f"Could not analyze {file_path}: {e}")

        # Collect all manager classes found
        all_manager_classes = set()
        for file_path, classes in websocket_classes.items():
            for class_name in classes:
                all_manager_classes.add(class_name)

        # Check for unauthorized new classes
        unauthorized_classes = all_manager_classes - acceptable_manager_classes

        if unauthorized_classes:
            self.logger.error(f"REGRESSION DETECTED: New WebSocket Manager classes found: {unauthorized_classes}")

        self.assertEqual(
            len(unauthorized_classes), 0,
            f"REGRESSION VIOLATION: {len(unauthorized_classes)} unauthorized WebSocket Manager classes detected: {unauthorized_classes}. "
            f"All new WebSocket functionality must use existing SSOT classes: {acceptable_manager_classes}. "
            f"Adding new manager classes violates SSOT principles and reintroduces fragmentation."
        )

    def _find_manager_classes(self, file_path: str) -> List[str]:
        """Find WebSocket Manager classes in a file."""
        manager_classes = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    if 'websocketmanager' in class_name.lower() or class_name.endswith('Manager'):
                        # Additional check to ensure it's WebSocket-related
                        if any(indicator in class_name.lower() for indicator in ['websocket', 'ws', 'socket']):
                            manager_classes.append(class_name)

        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {e}")

        return manager_classes

if __name__ == '__main__':
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category unit')