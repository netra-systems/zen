"""
Priority 1 SSOT Validation Test: WebSocket Factory Pattern Consolidation

PURPOSE: Validate single factory pattern enforcement after SSOT consolidation.
BEHAVIOR: 
- PRE-consolidation: SHOULD FAIL (showing multiple competing patterns)
- POST-consolidation: MUST PASS (showing unified SSOT pattern only)

This test is critical for validating the success of WebSocket factory pattern 
SSOT consolidation (GitHub Issue #514).

Business Value: Platform/Internal - System Stability & Development Velocity
Validates that factory pattern consolidation eliminates competing patterns
while maintaining SSOT compliance across the WebSocket system.
"""

import os
import re
import ast
import importlib.util
from pathlib import Path
from typing import List, Dict, Set, Tuple
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketFactoryPatternEnforcement(SSotBaseTestCase):
    """
    SSOT validation tests for WebSocket factory pattern consolidation.
    
    These tests verify that only the unified SSOT factory pattern exists
    after consolidation, eliminating competing factory implementations.
    """

    def setup_method(self, method):
        """Set up test environment for factory pattern validation."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent
        self.netra_backend_root = self.project_root / "netra_backend"
        
        # Define deprecated patterns to detect
        self.deprecated_factory_patterns = [
            # Deprecated factory function calls
            r"get_websocket_manager_factory\s*\(\s*\)",
            r"WebSocketManagerFactory\s*\(\s*\)",
            
            # Deprecated import patterns
            r"from\s+.*websocket_manager_factory\s+import\s+get_websocket_manager_factory",
            r"from\s+.*websocket_manager_factory\s+import\s+WebSocketManagerFactory",
            
            # Direct instantiation patterns that bypass SSOT
            r"UnifiedWebSocketManager\s*\(\s*\)",
            r"new\s+WebSocketManager\s*\(\s*\)",
            
            # Legacy factory method calls
            r"create_websocket_manager_factory\s*\(\s*\)",
            r"get_manager_factory\s*\(\s*\)",
        ]
        
        # Define SSOT patterns that SHOULD exist
        self.ssot_factory_patterns = [
            r"get_websocket_manager\s*\(",
            r"create_websocket_manager\s*\(",
            r"from\s+.*websocket_manager\s+import\s+get_websocket_manager",
            r"from\s+.*websocket_manager\s+import\s+WebSocketManager",
        ]
        
        self.record_metric("factory_patterns_checked", len(self.deprecated_factory_patterns))
        self.record_metric("ssot_patterns_expected", len(self.ssot_factory_patterns))

    def test_no_deprecated_factory_patterns_exist(self):
        """
        CRITICAL TEST: Validate that NO deprecated factory patterns exist.
        
        PRE-consolidation: SHOULD FAIL (deprecated patterns detected)
        POST-consolidation: MUST PASS (no deprecated patterns found)
        """
        print("\n🔍 Scanning for deprecated WebSocket factory patterns...")
        
        deprecated_violations = self._scan_for_deprecated_patterns()
        
        if deprecated_violations:
            self._report_deprecated_violations(deprecated_violations)
            
        # This assertion SHOULD FAIL before SSOT consolidation
        self.assertEqual(
            len(deprecated_violations), 0,
            f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Found {len(deprecated_violations)} "
            f"deprecated factory patterns that must be eliminated during SSOT consolidation. "
            f"This test should PASS after consolidation is complete."
        )
        
        print("✅ Zero deprecated factory patterns detected - SSOT consolidation successful!")
        self.record_metric("deprecated_violations", len(deprecated_violations))

    def test_unified_factory_pattern_enforcement(self):
        """
        CRITICAL TEST: Validate only unified SSOT factory patterns are used.
        
        PRE-consolidation: SHOULD FAIL (missing unified patterns)
        POST-consolidation: MUST PASS (unified patterns properly implemented)
        """
        print("\n🏗️ Validating unified SSOT factory pattern implementation...")
        
        ssot_pattern_coverage = self._validate_ssot_factory_patterns()
        
        # Check that essential SSOT patterns are implemented
        required_patterns = {
            "get_websocket_manager": False,
            "WebSocketManager_import": False,
            "ssot_factory_usage": False
        }
        
        for file_path, patterns in ssot_pattern_coverage.items():
            for pattern_name in patterns:
                if "get_websocket_manager" in pattern_name:
                    required_patterns["get_websocket_manager"] = True
                elif "WebSocketManager" in pattern_name and "import" in pattern_name:
                    required_patterns["WebSocketManager_import"] = True
                elif "create_websocket_manager" in pattern_name:
                    required_patterns["ssot_factory_usage"] = True
        
        missing_patterns = [name for name, found in required_patterns.items() if not found]
        
        if missing_patterns:
            self.fail(
                f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Missing unified SSOT patterns: "
                f"{missing_patterns}. This test should PASS after consolidation implements "
                f"the unified factory pattern."
            )
        
        print("✅ Unified SSOT factory patterns properly implemented!")
        self.record_metric("ssot_patterns_found", len(ssot_pattern_coverage))
        self.record_metric("required_patterns_complete", len(required_patterns))

    def test_factory_method_consolidation(self):
        """
        CRITICAL TEST: Validate factory methods are consolidated into single source.
        
        PRE-consolidation: SHOULD FAIL (multiple factory method implementations)
        POST-consolidation: MUST PASS (single consolidated factory implementation)
        """
        print("\n🔧 Validating factory method consolidation...")
        
        factory_method_sources = self._identify_factory_method_sources()
        
        # After consolidation, there should be exactly ONE factory method source
        expected_factory_sources = 1
        
        if len(factory_method_sources) > expected_factory_sources:
            violations = []
            for source_path, methods in factory_method_sources.items():
                if len(methods) > 0:
                    violations.append(f"{source_path}: {methods}")
            
            self.fail(
                f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Found {len(factory_method_sources)} "
                f"factory method sources, expected {expected_factory_sources} after consolidation.\n"
                f"Multiple factory sources detected:\n" + "\n".join(f"  - {v}" for v in violations) +
                f"\n\nThis test should PASS after SSOT consolidation eliminates duplicate factory methods."
            )
        
        print(f"✅ Factory methods consolidated into {len(factory_method_sources)} source(s)!")
        self.record_metric("factory_sources", len(factory_method_sources))

    def test_compatibility_layer_elimination(self):
        """
        CRITICAL TEST: Validate compatibility layers are eliminated post-consolidation.
        
        PRE-consolidation: SHOULD FAIL (compatibility layers present)
        POST-consolidation: MUST PASS (compatibility layers removed)
        """
        print("\n🧹 Validating compatibility layer elimination...")
        
        compatibility_violations = self._scan_for_compatibility_layers()
        
        if compatibility_violations:
            violation_summary = []
            for file_path, layers in compatibility_violations.items():
                violation_summary.append(f"{file_path}: {layers}")
            
            self.fail(
                f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Found {len(compatibility_violations)} "
                f"files with compatibility layers that should be eliminated after consolidation.\n"
                f"Compatibility layers detected:\n" + "\n".join(f"  - {v}" for v in violation_summary) +
                f"\n\nThis test should PASS after SSOT consolidation removes compatibility layers."
            )
        
        print("✅ Compatibility layers successfully eliminated!")
        self.record_metric("compatibility_violations", len(compatibility_violations))

    def _scan_for_deprecated_patterns(self) -> Dict[str, List[str]]:
        """Scan codebase for deprecated factory patterns."""
        violations = {}
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_violations = []
                for pattern in self.deprecated_factory_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                    if matches:
                        file_violations.extend([f"Pattern: {pattern} - Matches: {matches}"])
                
                if file_violations:
                    violations[str(py_file)] = file_violations
                    
            except Exception as e:
                print(f"Warning: Could not scan {py_file}: {e}")
        
        return violations

    def _validate_ssot_factory_patterns(self) -> Dict[str, List[str]]:
        """Validate SSOT factory patterns are properly implemented."""
        ssot_coverage = {}
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_patterns = []
                for pattern in self.ssot_factory_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                    if matches:
                        file_patterns.append(f"{pattern}")
                
                if file_patterns:
                    ssot_coverage[str(py_file)] = file_patterns
                    
            except Exception as e:
                print(f"Warning: Could not scan {py_file}: {e}")
        
        return ssot_coverage

    def _identify_factory_method_sources(self) -> Dict[str, List[str]]:
        """Identify all sources that define factory methods."""
        factory_sources = {}
        
        factory_method_names = [
            "create_websocket_manager",
            "get_websocket_manager",
            "get_websocket_manager_factory",
            "WebSocketManagerFactory",
            "create_websocket_manager_sync"
        ]
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST to find function/class definitions
                try:
                    tree = ast.parse(content)
                    file_factories = []
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name in factory_method_names:
                                file_factories.append(f"function:{node.name}")
                        elif isinstance(node, ast.ClassDef):
                            if node.name in factory_method_names:
                                file_factories.append(f"class:{node.name}")
                    
                    if file_factories:
                        factory_sources[str(py_file)] = file_factories
                        
                except SyntaxError:
                    # Fallback to regex for files with syntax issues
                    pass
                    
            except Exception as e:
                print(f"Warning: Could not analyze {py_file}: {e}")
        
        return factory_sources

    def _scan_for_compatibility_layers(self) -> Dict[str, List[str]]:
        """Scan for compatibility layers that should be eliminated."""
        compatibility_patterns = [
            r"# COMPATIBILITY",
            r"# Legacy compatibility",
            r"DEPRECATED.*compatibility",
            r"@deprecated",
            r"compatibility_wrapper",
            r"legacy_factory",
            r"backward_compatible",
        ]
        
        violations = {}
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_violations = []
                for pattern in compatibility_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                    if matches:
                        file_violations.append(f"Compatibility layer: {pattern}")
                
                if file_violations:
                    violations[str(py_file)] = file_violations
                    
            except Exception as e:
                print(f"Warning: Could not scan {py_file}: {e}")
        
        return violations

    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the netra_backend directory."""
        python_files = []
        
        # Focus on WebSocket-related files for factory pattern validation
        websocket_dirs = [
            self.netra_backend_root / "app" / "websocket_core",
            self.netra_backend_root / "app" / "services",
            self.netra_backend_root / "app" / "agents",
        ]
        
        for directory in websocket_dirs:
            if directory.exists():
                python_files.extend(directory.rglob("*.py"))
        
        # Also check test files for factory usage
        test_dirs = [
            self.project_root / "tests",
            self.netra_backend_root / "tests",
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                # Only check websocket-related test files to avoid false positives
                websocket_test_files = []
                for test_file in test_dir.rglob("*.py"):
                    if "websocket" in str(test_file).lower():
                        websocket_test_files.append(test_file)
                
                python_files.extend(websocket_test_files[:50])  # Limit to avoid timeout
        
        return python_files

    def _report_deprecated_violations(self, violations: Dict[str, List[str]]):
        """Report deprecated pattern violations with detailed information."""
        print("\n❌ DEPRECATED FACTORY PATTERN VIOLATIONS DETECTED:")
        print("=" * 80)
        
        total_files = len(violations)
        total_violations = sum(len(v) for v in violations.values())
        
        print(f"📊 SUMMARY: {total_violations} violations across {total_files} files")
        print("\n🔍 VIOLATIONS BY FILE:")
        
        for file_path, file_violations in violations.items():
            relative_path = str(file_path).replace(str(self.project_root), "")
            print(f"\n📁 {relative_path}")
            for i, violation in enumerate(file_violations[:5], 1):  # Limit output
                print(f"   {i}. {violation}")
            if len(file_violations) > 5:
                print(f"   ... and {len(file_violations) - 5} more violations")
        
        print("\n" + "=" * 80)
        print("🎯 SSOT CONSOLIDATION REQUIRED:")
        print("   ✅ Replace get_websocket_manager_factory() with get_websocket_manager()")
        print("   ✅ Replace WebSocketManagerFactory with direct WebSocketManager usage")
        print("   ✅ Eliminate compatibility wrapper functions")
        print("   ✅ Consolidate all factory methods into single SSOT implementation")
        print("=" * 80)