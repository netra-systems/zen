"""
Priority 1 SSOT Validation Test: WebSocket Deprecated Pattern Elimination

PURPOSE: Ensure deprecated factory methods are completely removed.
BEHAVIOR:
- PRE-consolidation: SHOULD FAIL (showing deprecated usage exists)
- POST-consolidation: MUST PASS (showing deprecated patterns eliminated)

This test validates the elimination of deprecated WebSocket factory patterns
during SSOT consolidation (GitHub Issue #514).

Business Value: Platform/Internal - System Stability & Development Velocity
Validates that deprecated patterns are eliminated, reducing technical debt
and eliminating confusion in factory pattern usage.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketDeprecatedPatternElimination(SSotBaseTestCase):
    """
    SSOT validation tests for WebSocket deprecated pattern elimination.
    
    These tests verify that deprecated factory methods and patterns are
    completely removed after SSOT consolidation.
    """

    def setup_method(self, method):
        """Set up test environment for deprecated pattern validation."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent
        
        # Define deprecated patterns that MUST be eliminated
        self.deprecated_import_patterns = [
            "from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory",
            "from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory",
            "import websocket_manager_factory",
            "from .websocket_manager_factory import",
        ]
        
        self.deprecated_usage_patterns = [
            r"get_websocket_manager_factory\s*\(\s*\)",
            r"WebSocketManagerFactory\s*\(\s*\)",
            r"websocket_manager_factory\.",
            r"\.get_websocket_manager_factory",
        ]
        
        # Staging deployment warnings that should be eliminated
        self.staging_warning_patterns = [
            "COMPATIBILITY MODULE",
            "DEPRECATED.*websocket_manager_factory", 
            "compatibility.*wrapper",
            "legacy.*factory",
        ]
        
        self.record_metric("deprecated_imports_checked", len(self.deprecated_import_patterns))
        self.record_metric("deprecated_usage_checked", len(self.deprecated_usage_patterns))

    def test_deprecated_factory_imports_eliminated(self):
        """
        CRITICAL TEST: Validate deprecated factory imports are eliminated.
        
        PRE-consolidation: SHOULD FAIL (deprecated imports exist)
        POST-consolidation: MUST PASS (no deprecated imports found)
        """
        print("\n🔍 Scanning for deprecated WebSocket factory imports...")
        
        deprecated_imports = self._scan_for_deprecated_imports()
        
        if deprecated_imports:
            self._report_deprecated_imports(deprecated_imports)
        
        # This assertion SHOULD FAIL before SSOT consolidation
        self.assertEqual(
            len(deprecated_imports), 0,
            f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Found {len(deprecated_imports)} files "
            f"with deprecated factory imports. These must be eliminated during SSOT consolidation. "
            f"This test should PASS after consolidation removes all deprecated imports."
        )
        
        print("✅ Zero deprecated factory imports detected - elimination successful!")
        self.record_metric("deprecated_imports_found", len(deprecated_imports))

    def test_deprecated_factory_usage_eliminated(self):
        """
        CRITICAL TEST: Validate deprecated factory usage is eliminated.
        
        PRE-consolidation: SHOULD FAIL (deprecated usage exists)
        POST-consolidation: MUST PASS (no deprecated usage found)
        """
        print("\n🔍 Scanning for deprecated WebSocket factory usage...")
        
        deprecated_usage = self._scan_for_deprecated_usage()
        
        if deprecated_usage:
            self._report_deprecated_usage(deprecated_usage)
        
        # This assertion SHOULD FAIL before SSOT consolidation
        self.assertEqual(
            len(deprecated_usage), 0,
            f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Found {len(deprecated_usage)} files "
            f"with deprecated factory usage patterns. These must be eliminated during SSOT consolidation. "
            f"This test should PASS after consolidation removes all deprecated usage."
        )
        
        print("✅ Zero deprecated factory usage detected - elimination successful!")
        self.record_metric("deprecated_usage_found", len(deprecated_usage))

    def test_websocket_manager_factory_file_removed(self):
        """
        CRITICAL TEST: Validate websocket_manager_factory.py file is removed.
        
        PRE-consolidation: SHOULD FAIL (file exists)
        POST-consolidation: MUST PASS (file removed or properly consolidated)
        """
        print("\n📁 Checking websocket_manager_factory.py file status...")
        
        factory_file_paths = [
            self.project_root / "netra_backend" / "app" / "websocket_core" / "websocket_manager_factory.py",
            self.project_root / "netra_backend" / "websocket_core" / "websocket_manager_factory.py",
            # Check for any websocket_manager_factory.py files
        ]
        
        existing_factory_files = []
        for factory_path in factory_file_paths:
            if factory_path.exists():
                # Check if it's a legitimate SSOT file or deprecated compatibility file
                if self._is_deprecated_factory_file(factory_path):
                    existing_factory_files.append(str(factory_path))
        
        if existing_factory_files:
            files_list = "\n".join(f"  - {f}" for f in existing_factory_files)
            self.fail(
                f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Found {len(existing_factory_files)} "
                f"deprecated websocket_manager_factory.py files:\n{files_list}\n\n"
                f"These files should be removed or consolidated during SSOT consolidation. "
                f"This test should PASS after consolidation eliminates deprecated factory files."
            )
        
        print("✅ No deprecated websocket_manager_factory.py files found - elimination successful!")
        self.record_metric("deprecated_factory_files", len(existing_factory_files))

    def test_staging_deployment_warnings_eliminated(self):
        """
        CRITICAL TEST: Validate staging deployment warnings are eliminated.
        
        PRE-consolidation: SHOULD FAIL (warnings present in logs/code)
        POST-consolidation: MUST PASS (warnings eliminated)
        """
        print("\n⚠️ Scanning for staging deployment compatibility warnings...")
        
        warning_sources = self._scan_for_staging_warnings()
        
        if warning_sources:
            self._report_staging_warnings(warning_sources)
        
        # This assertion SHOULD FAIL before SSOT consolidation
        self.assertEqual(
            len(warning_sources), 0,
            f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Found {len(warning_sources)} files "
            f"with staging deployment compatibility warnings. These indicate deprecated "
            f"patterns still in use and should be eliminated during SSOT consolidation. "
            f"This test should PASS after consolidation removes all compatibility warnings."
        )
        
        print("✅ Zero staging deployment warnings detected - elimination successful!")
        self.record_metric("staging_warnings_found", len(warning_sources))

    def test_ssot_import_pattern_validation(self):
        """
        CRITICAL TEST: Validate only SSOT import patterns are used.
        
        PRE-consolidation: SHOULD FAIL (mixed import patterns)
        POST-consolidation: MUST PASS (only SSOT imports used)
        """
        print("\n🎯 Validating SSOT import pattern compliance...")
        
        ssot_compliance = self._validate_ssot_import_patterns()
        
        non_compliant_files = []
        for file_path, compliance_data in ssot_compliance.items():
            if not compliance_data['is_compliant']:
                non_compliant_files.append({
                    'file': file_path,
                    'issues': compliance_data['issues']
                })
        
        if non_compliant_files:
            self._report_import_compliance_violations(non_compliant_files)
        
        # This assertion SHOULD FAIL before SSOT consolidation
        self.assertEqual(
            len(non_compliant_files), 0,
            f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Found {len(non_compliant_files)} files "
            f"with non-SSOT import patterns. These should be converted to SSOT patterns "
            f"during consolidation. This test should PASS after consolidation standardizes imports."
        )
        
        print("✅ All files use SSOT import patterns - compliance achieved!")
        self.record_metric("non_compliant_imports", len(non_compliant_files))

    def test_codebase_grep_validation(self):
        """
        CRITICAL TEST: Use grep to validate deprecated pattern elimination.
        
        PRE-consolidation: SHOULD FAIL (grep finds deprecated patterns)
        POST-consolidation: MUST PASS (grep finds no deprecated patterns)
        """
        print("\n🔎 Running codebase grep validation for deprecated patterns...")
        
        grep_results = self._run_grep_validation()
        
        if grep_results['violations']:
            self._report_grep_violations(grep_results)
        
        # This assertion SHOULD FAIL before SSOT consolidation
        self.assertEqual(
            len(grep_results['violations']), 0,
            f"❌ PRE-CONSOLIDATION FAILURE (EXPECTED): Grep found {len(grep_results['violations'])} "
            f"deprecated pattern violations. These must be eliminated during SSOT consolidation. "
            f"This test should PASS after consolidation removes all deprecated patterns."
        )
        
        print("✅ Grep validation passed - no deprecated patterns found!")
        self.record_metric("grep_violations", len(grep_results['violations']))

    def _scan_for_deprecated_imports(self) -> Dict[str, List[str]]:
        """Scan for deprecated import statements."""
        violations = {}
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_violations = []
                for pattern in self.deprecated_import_patterns:
                    if pattern in content:
                        file_violations.append(pattern)
                
                if file_violations:
                    violations[str(py_file)] = file_violations
                    
            except Exception as e:
                print(f"Warning: Could not scan {py_file}: {e}")
        
        return violations

    def _scan_for_deprecated_usage(self) -> Dict[str, List[str]]:
        """Scan for deprecated usage patterns."""
        violations = {}
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_violations = []
                for pattern in self.deprecated_usage_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    if matches:
                        file_violations.append(f"Pattern: {pattern} - Found: {len(matches)} occurrences")
                
                if file_violations:
                    violations[str(py_file)] = file_violations
                    
            except Exception as e:
                print(f"Warning: Could not scan {py_file}: {e}")
        
        return violations

    def _is_deprecated_factory_file(self, file_path: Path) -> bool:
        """Check if a websocket_manager_factory.py file is deprecated."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for deprecated patterns in the factory file
            deprecated_indicators = [
                "get_websocket_manager_factory",
                "WebSocketManagerFactory",
                "COMPATIBILITY MODULE",
                "DEPRECATED",
            ]
            
            for indicator in deprecated_indicators:
                if indicator in content:
                    return True
            
            return False
            
        except Exception:
            return True  # If we can't read it, assume it's deprecated

    def _scan_for_staging_warnings(self) -> Dict[str, List[str]]:
        """Scan for staging deployment compatibility warnings."""
        warnings = {}
        
        for py_file in self._get_python_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_warnings = []
                for pattern in self.staging_warning_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
                    if matches:
                        file_warnings.append(f"Warning pattern: {pattern}")
                
                if file_warnings:
                    warnings[str(py_file)] = file_warnings
                    
            except Exception as e:
                print(f"Warning: Could not scan {py_file}: {e}")
        
        return warnings

    def _validate_ssot_import_patterns(self) -> Dict[str, Dict]:
        """Validate files use only SSOT import patterns."""
        compliance_data = {}
        
        # Define SSOT patterns that SHOULD be used
        ssot_patterns = [
            "from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager",
            "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
        ]
        
        for py_file in self._get_websocket_related_files():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                issues = []
                has_websocket_imports = "websocket" in content.lower() and "import" in content
                
                if has_websocket_imports:
                    # Check for deprecated imports
                    for deprecated_pattern in self.deprecated_import_patterns:
                        if deprecated_pattern in content:
                            issues.append(f"Uses deprecated import: {deprecated_pattern}")
                    
                    # Check if using SSOT patterns
                    uses_ssot = any(pattern in content for pattern in ssot_patterns)
                    if not uses_ssot and "websocket_manager" in content:
                        issues.append("Does not use SSOT import patterns")
                
                compliance_data[str(py_file)] = {
                    'is_compliant': len(issues) == 0,
                    'issues': issues
                }
                
            except Exception as e:
                compliance_data[str(py_file)] = {
                    'is_compliant': False,
                    'issues': [f"Could not analyze file: {e}"]
                }
        
        return compliance_data

    def _run_grep_validation(self) -> Dict:
        """Run grep commands to validate deprecated pattern elimination."""
        grep_patterns = [
            "get_websocket_manager_factory",
            "websocket_manager_factory",
            "WebSocketManagerFactory",
        ]
        
        violations = []
        
        for pattern in grep_patterns:
            try:
                # Use grep to search for deprecated patterns
                cmd = ["grep", "-r", "--include=*.py", pattern, str(self.project_root)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout.strip():
                    # Found occurrences of the deprecated pattern
                    lines = result.stdout.strip().split('\n')
                    for line in lines[:10]:  # Limit output
                        if line.strip():
                            violations.append(f"Pattern '{pattern}': {line}")
                
            except subprocess.TimeoutExpired:
                violations.append(f"Grep timeout for pattern: {pattern}")
            except Exception as e:
                print(f"Warning: Grep failed for pattern {pattern}: {e}")
        
        return {
            'violations': violations,
            'patterns_checked': len(grep_patterns)
        }

    def _get_python_files(self) -> List[Path]:
        """Get relevant Python files for scanning."""
        python_files = []
        
        # Focus on core directories
        core_dirs = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "tests",
        ]
        
        for directory in core_dirs:
            if directory.exists():
                python_files.extend(list(directory.rglob("*.py"))[:100])  # Limit to avoid timeout
        
        return python_files

    def _get_websocket_related_files(self) -> List[Path]:
        """Get WebSocket-related Python files for focused scanning."""
        websocket_files = []
        
        for py_file in self._get_python_files():
            if "websocket" in str(py_file).lower():
                websocket_files.append(py_file)
        
        return websocket_files[:50]  # Limit to most relevant files

    def _report_deprecated_imports(self, violations: Dict[str, List[str]]):
        """Report deprecated import violations."""
        print("\n❌ DEPRECATED IMPORT VIOLATIONS DETECTED:")
        print("=" * 80)
        
        for file_path, imports in violations.items():
            relative_path = str(file_path).replace(str(self.project_root), "")
            print(f"\n📁 {relative_path}")
            for import_stmt in imports:
                print(f"   ❌ {import_stmt}")
        
        print("\n🔧 REMEDIATION REQUIRED:")
        print("   ✅ Replace with: from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager")
        print("   ✅ Replace with: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager")

    def _report_deprecated_usage(self, violations: Dict[str, List[str]]):
        """Report deprecated usage violations."""
        print("\n❌ DEPRECATED USAGE VIOLATIONS DETECTED:")
        print("=" * 80)
        
        for file_path, usage_patterns in violations.items():
            relative_path = str(file_path).replace(str(self.project_root), "")
            print(f"\n📁 {relative_path}")
            for usage in usage_patterns:
                print(f"   ❌ {usage}")

    def _report_staging_warnings(self, warnings: Dict[str, List[str]]):
        """Report staging deployment warnings."""
        print("\n⚠️ STAGING DEPLOYMENT WARNINGS DETECTED:")
        print("=" * 80)
        
        for file_path, file_warnings in warnings.items():
            relative_path = str(file_path).replace(str(self.project_root), "")
            print(f"\n📁 {relative_path}")
            for warning in file_warnings:
                print(f"   ⚠️ {warning}")

    def _report_import_compliance_violations(self, violations: List[Dict]):
        """Report import compliance violations."""
        print("\n❌ SSOT IMPORT COMPLIANCE VIOLATIONS:")
        print("=" * 80)
        
        for violation in violations:
            relative_path = str(violation['file']).replace(str(self.project_root), "")
            print(f"\n📁 {relative_path}")
            for issue in violation['issues']:
                print(f"   ❌ {issue}")

    def _report_grep_violations(self, grep_results: Dict):
        """Report grep validation violations."""
        print("\n❌ GREP VALIDATION VIOLATIONS:")
        print("=" * 80)
        
        print(f"📊 Found {len(grep_results['violations'])} violations across codebase")
        
        for violation in grep_results['violations'][:20]:  # Limit output
            print(f"   ❌ {violation}")
        
        if len(grep_results['violations']) > 20:
            print(f"   ... and {len(grep_results['violations']) - 20} more violations")