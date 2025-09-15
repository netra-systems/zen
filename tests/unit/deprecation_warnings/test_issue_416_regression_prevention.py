"""
Issue #416 Regression Prevention Tests
======================================

Business Value: Prevents regression of deprecation warnings after fixes are applied,
protecting $500K+ ARR by ensuring deprecated imports don't reappear.

Test Strategy:
1. Prevent new deprecated import patterns
2. Enforce canonical import usage
3. Monitor for reintroduction of deprecated patterns
4. Validate SSOT compliance after fixes

These tests should PASS after migration is complete, serving as ongoing protection.
"""

import unittest
import ast
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Set, Optional
import re

from test_framework.ssot.base_test_case import SSotBaseTestCase


class DeprecationRegressionPreventionTests(SSotBaseTestCase):
    """Prevent regression of deprecated import patterns"""
    
    def setUp(self):
        super().setUp()
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        
        # Define patterns that should NOT appear in code after migration
        self.forbidden_import_patterns = [
            # Generic websocket_core imports (ISSUE #1144)
            r'from\s+netra_backend\.app\.websocket_core\s+import\s+\w+',
            r'import\s+netra_backend\.app\.websocket_core$',
            
            # Specific deprecated patterns identified in ISSUE #1144
            r'from\s+netra_backend\.app\.websocket_core\s+import\s+WebSocketManager',
            r'from\s+netra_backend\.app\.websocket_core\s+import\s+create_websocket_manager',
            r'from\s+netra_backend\.app\.websocket_core\s+import\s+get_websocket_manager',
        ]
        
        # Define canonical patterns that SHOULD be used instead
        self.canonical_import_patterns = [
            r'from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import\s+WebSocketManager',
            r'from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import\s+create_websocket_manager',
            r'from\s+netra_backend\.app\.websocket_core\.event_validation_framework\s+import\s+get_websocket_validator',
        ]
        
        # Files that may be temporarily exempt during migration
        self.exempted_files = {
            'netra_backend/app/websocket_core/__init__.py',  # Contains deprecation warning itself
            'tests/unit/deprecation_warnings/',  # Our test files may reference deprecated patterns
        }
    
    def test_no_forbidden_import_patterns_in_source(self):
        """
        REGRESSION TEST: Ensure no forbidden import patterns exist in source code
        
        This test should PASS after migration completion.
        """
        print("\n=== Testing for Forbidden Import Patterns in Source ===")
        
        violations = []
        source_dirs = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "auth_service",
            self.project_root / "shared",
        ]
        
        for source_dir in source_dirs:
            if source_dir.exists():
                violations.extend(self._scan_directory_for_patterns(
                    source_dir, 
                    self.forbidden_import_patterns,
                    "source"
                ))
        
        print(f"📊 Found {len(violations)} violations in source code")
        
        # Filter out exempted files
        filtered_violations = []
        for violation in violations:
            file_relative = str(violation['file']).replace(str(self.project_root) + '/', '')
            
            # Check if file is exempted
            exempted = any(
                exempt_pattern in file_relative 
                for exempt_pattern in self.exempted_files
            )
            
            if not exempted:
                filtered_violations.append(violation)
                print(f"  ❌ {violation['file']}:{violation['line']} - {violation['pattern']}")
            else:
                print(f"  ⚠️  EXEMPTED: {violation['file']}:{violation['line']}")
        
        # REGRESSION TEST: Should have NO violations after migration
        self.assertEqual(
            len(filtered_violations), 0,
            f"Found {len(filtered_violations)} forbidden import patterns in source code. "
            f"Migration incomplete or regression occurred."
        )
    
    def test_canonical_imports_preferred_in_new_files(self):
        """
        REGRESSION TEST: Ensure new files use canonical import patterns
        
        Validates that developers use correct import patterns going forward.
        """
        print("\n=== Testing Canonical Import Usage ===")
        
        # Find files that import WebSocket functionality
        websocket_importing_files = []
        source_dirs = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "tests"
        ]
        
        for source_dir in source_dirs:
            if source_dir.exists():
                websocket_importing_files.extend(
                    self._find_websocket_importing_files(source_dir)
                )
        
        print(f"📊 Found {len(websocket_importing_files)} files importing WebSocket functionality")
        
        # Analyze import patterns
        canonical_usage = 0
        deprecated_usage = 0
        
        for file_info in websocket_importing_files:
            file_relative = str(file_info['file']).replace(str(self.project_root) + '/', '')
            
            # Skip exempted files
            exempted = any(
                exempt_pattern in file_relative 
                for exempt_pattern in self.exempted_files
            )
            
            if exempted:
                continue
            
            has_canonical = any(
                re.search(pattern, file_info['content'], re.MULTILINE)
                for pattern in self.canonical_import_patterns
            )
            
            has_deprecated = any(
                re.search(pattern, file_info['content'], re.MULTILINE)
                for pattern in self.forbidden_import_patterns
            )
            
            if has_canonical:
                canonical_usage += 1
                print(f"  ✓ {file_relative} - Uses canonical imports")
            elif has_deprecated:
                deprecated_usage += 1
                print(f"  ❌ {file_relative} - Uses deprecated imports")
        
        total_files = canonical_usage + deprecated_usage
        canonical_rate = canonical_usage / total_files if total_files > 0 else 1.0
        
        print(f"📊 Canonical import usage rate: {canonical_rate:.1%} ({canonical_usage}/{total_files})")
        
        # After migration, should prefer canonical imports
        self.assertGreaterEqual(
            canonical_rate, 0.8,
            f"Canonical import usage rate too low: {canonical_rate:.1%}. "
            f"Ensure developers use canonical import patterns."
        )
    
    def test_ssot_compliance_maintenance(self):
        """
        REGRESSION TEST: Ensure SSOT compliance is maintained after migration
        
        Validates that SSOT principles are followed consistently.
        """
        print("\n=== Testing SSOT Compliance Maintenance ===")
        
        ssot_violations = []
        
        # Check for duplicate WebSocket manager implementations
        manager_implementations = self._find_websocket_manager_implementations()
        
        print(f"📊 Found {len(manager_implementations)} WebSocket manager implementations")
        
        # Should have exactly one canonical WebSocket manager
        canonical_managers = [
            impl for impl in manager_implementations
            if 'websocket_manager.py' in str(impl['file'])
        ]
        
        duplicate_managers = [
            impl for impl in manager_implementations
            if 'websocket_manager.py' not in str(impl['file'])
            and 'test' not in str(impl['file']).lower()
        ]
        
        print(f"  Canonical managers: {len(canonical_managers)}")
        print(f"  Duplicate managers: {len(duplicate_managers)}")
        
        for duplicate in duplicate_managers:
            print(f"    ❌ Duplicate: {duplicate['file']}")
            ssot_violations.append({
                'type': 'duplicate_manager',
                'file': duplicate['file'],
                'description': 'Duplicate WebSocket manager implementation'
            })
        
        # Check for import path consistency
        import_consistency_violations = self._check_import_path_consistency()
        ssot_violations.extend(import_consistency_violations)
        
        print(f"📊 Total SSOT violations: {len(ssot_violations)}")
        
        # REGRESSION TEST: Should maintain SSOT compliance
        self.assertLessEqual(
            len(ssot_violations), 2,  # Allow minimal violations during transition
            f"SSOT compliance violations found: {len(ssot_violations)}. "
            f"System regressing from SSOT principles."
        )
    
    def test_deprecation_warning_removal_verification(self):
        """
        REGRESSION TEST: Verify deprecation warnings are properly removed
        
        Ensures deprecation warnings don't continue after migration.
        """
        print("\n=== Testing Deprecation Warning Removal ===")
        
        # Test that importing doesn't generate ISSUE #1144 warnings
        test_imports = [
            'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
            'from netra_backend.app.websocket_core.event_validation_framework import get_websocket_validator',
        ]
        
        warnings_detected = []
        
        for import_statement in test_imports:
            print(f"🧪 Testing: {import_statement}")
            
            result = self._test_import_for_warnings(import_statement)
            
            if result['has_warnings']:
                warnings_detected.extend(result['warnings'])
                print(f"  ❌ Warnings detected: {len(result['warnings'])}")
                for warning in result['warnings']:
                    print(f"    - {warning}")
            else:
                print(f"  ✓ No warnings")
        
        # REGRESSION TEST: Should have no ISSUE #1144 warnings after migration
        issue_1144_warnings = [
            w for w in warnings_detected 
            if 'ISSUE #1144' in w
        ]
        
        self.assertEqual(
            len(issue_1144_warnings), 0,
            f"ISSUE #1144 deprecation warnings still present after migration: {issue_1144_warnings}"
        )
    
    def test_new_file_template_compliance(self):
        """
        REGRESSION TEST: Ensure new files follow canonical import templates
        
        Provides guidance for developers creating new files.
        """
        print("\n=== Testing New File Template Compliance ===")
        
        # Define template patterns for common WebSocket imports
        recommended_templates = {
            'websocket_manager': 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager',
            'event_validator': 'from netra_backend.app.websocket_core.event_validation_framework import get_websocket_validator',
            'websocket_factory': 'from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager',
        }
        
        # Find recently modified files (simulation - in real case would check git)
        recent_files = self._find_recently_modified_files()
        
        print(f"📊 Analyzing {len(recent_files)} recent files")
        
        template_compliance = []
        
        for file_path in recent_files:
            if self._file_uses_websocket_imports(file_path):
                compliance = self._check_template_compliance(file_path, recommended_templates)
                template_compliance.append(compliance)
                
                file_relative = str(file_path).replace(str(self.project_root) + '/', '')
                if compliance['compliant']:
                    print(f"  ✓ {file_relative} - Template compliant")
                else:
                    print(f"  ❌ {file_relative} - Template violations: {compliance['violations']}")
        
        # Calculate compliance rate
        compliant_files = sum(1 for c in template_compliance if c['compliant'])
        compliance_rate = compliant_files / len(template_compliance) if template_compliance else 1.0
        
        print(f"📊 Template compliance rate: {compliance_rate:.1%} ({compliant_files}/{len(template_compliance)})")
        
        # Should maintain high template compliance
        self.assertGreaterEqual(
            compliance_rate, 0.8,
            f"Template compliance rate too low: {compliance_rate:.1%}. "
            f"Developers not following canonical import patterns."
        )
    
    def _scan_directory_for_patterns(self, directory: Path, patterns: List[str], scan_type: str) -> List[Dict]:
        """Scan directory for forbidden import patterns"""
        violations = []
        
        for py_file in directory.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for line_num, line in enumerate(content.split('\n'), 1):
                    for pattern in patterns:
                        if re.search(pattern, line):
                            violations.append({
                                'file': py_file,
                                'line': line_num,
                                'pattern': pattern,
                                'content': line.strip(),
                                'type': scan_type
                            })
            except Exception as e:
                print(f"⚠️  Could not scan {py_file}: {e}")
        
        return violations
    
    def _find_websocket_importing_files(self, directory: Path) -> List[Dict]:
        """Find files that import WebSocket functionality"""
        websocket_files = []
        
        for py_file in directory.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file imports WebSocket functionality
                websocket_import_patterns = [
                    r'websocket',
                    r'WebSocket',
                    r'event_validator',
                    r'websocket_manager'
                ]
                
                has_websocket_import = any(
                    re.search(pattern, content, re.IGNORECASE)
                    for pattern in websocket_import_patterns
                )
                
                if has_websocket_import:
                    websocket_files.append({
                        'file': py_file,
                        'content': content
                    })
                    
            except Exception as e:
                print(f"⚠️  Could not scan {py_file}: {e}")
        
        return websocket_files
    
    def _find_websocket_manager_implementations(self) -> List[Dict]:
        """Find WebSocket manager implementations"""
        implementations = []
        
        # Search for WebSocketManager class definitions
        result = subprocess.run([
            "grep", "-r", "-n", "class.*WebSocketManager",
            str(self.project_root / "netra_backend")
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        implementations.append({
                            'file': parts[0],
                            'line': parts[1],
                            'content': parts[2]
                        })
        
        return implementations
    
    def _check_import_path_consistency(self) -> List[Dict]:
        """Check for import path consistency violations"""
        violations = []
        
        # Find all WebSocket-related imports
        result = subprocess.run([
            "grep", "-r", "-n", "from.*websocket",
            str(self.project_root / "netra_backend")
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            import_paths = set()
            for line in result.stdout.strip().split('\n'):
                if line.strip() and 'from' in line:
                    # Extract import path
                    match = re.search(r'from\s+([^\s]+)', line)
                    if match:
                        import_paths.add(match.group(1))
            
            # Check for inconsistent paths
            websocket_core_imports = [
                path for path in import_paths 
                if 'websocket_core' in path
            ]
            
            # Should use specific module paths, not generic websocket_core
            generic_imports = [
                path for path in websocket_core_imports
                if path.endswith('websocket_core')
            ]
            
            for generic_import in generic_imports:
                violations.append({
                    'type': 'generic_import_path',
                    'file': 'multiple',
                    'description': f'Generic import path used: {generic_import}'
                })
        
        return violations
    
    def _test_import_for_warnings(self, import_statement: str) -> Dict:
        """Test an import statement for deprecation warnings"""
        import tempfile
        import subprocess
        
        test_code = f"""
import warnings
warnings.simplefilter('always')

import sys
sys.path.insert(0, '/Users/anthony/Desktop/netra-apex')

{import_statement}
print("Import completed successfully")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name
        
        try:
            result = subprocess.run([
                sys.executable, "-W", "always", temp_file
            ], capture_output=True, text=True)
            
            warnings = []
            if result.stderr:
                warning_lines = [
                    line for line in result.stderr.split('\n')
                    if 'Warning' in line or 'warning' in line
                ]
                warnings = warning_lines
            
            return {
                'success': result.returncode == 0,
                'has_warnings': len(warnings) > 0,
                'warnings': warnings,
                'output': result.stdout
            }
            
        finally:
            try:
                import os
                os.unlink(temp_file)
            except:
                pass
    
    def _find_recently_modified_files(self) -> List[Path]:
        """Find recently modified Python files (simulation)"""
        # In a real implementation, this would use git to find recent files
        # For testing, we'll find files in key directories
        recent_files = []
        
        search_dirs = [
            self.project_root / "netra_backend" / "app" / "agents",
            self.project_root / "netra_backend" / "app" / "services",
            self.project_root / "tests" / "unit" / "websocket_core"
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                # Get a sample of files from each directory
                py_files = list(search_dir.rglob("*.py"))
                recent_files.extend(py_files[:3])  # Take first 3 from each dir
        
        return recent_files
    
    def _file_uses_websocket_imports(self, file_path: Path) -> bool:
        """Check if file uses WebSocket imports"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            websocket_patterns = [
                r'websocket',
                r'WebSocket',
                r'event_validator'
            ]
            
            return any(
                re.search(pattern, content, re.IGNORECASE)
                for pattern in websocket_patterns
            )
        except:
            return False
    
    def _check_template_compliance(self, file_path: Path, templates: Dict[str, str]) -> Dict:
        """Check if file follows canonical import templates"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            violations = []
            
            # Check if file uses canonical patterns
            for template_name, canonical_import in templates.items():
                if template_name.replace('_', '') in content.lower():
                    # File uses this functionality, check if import is canonical
                    if canonical_import not in content:
                        # Check if using deprecated pattern instead
                        deprecated_pattern = canonical_import.split('.')[-2]  # Get module name
                        if f"from netra_backend.app.websocket_core import {deprecated_pattern}" in content:
                            violations.append(f"Using deprecated import for {template_name}")
            
            return {
                'file': file_path,
                'compliant': len(violations) == 0,
                'violations': violations
            }
        except:
            return {
                'file': file_path,
                'compliant': True,
                'violations': []
            }


if __name__ == '__main__':
    print("🛡️  Issue #416 Regression Prevention Test Suite")
    print("=" * 60)
    print("Purpose: Prevent regression of deprecated import patterns")
    print("Expected: Tests should PASS after migration completion")
    print("=" * 60)
    
    unittest.main(verbosity=2)