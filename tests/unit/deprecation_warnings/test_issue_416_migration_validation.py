"""
Issue #416 Migration Validation Tests
=====================================

Business Value: Ensures safe migration paths exist for all deprecated imports,
protecting $500K+ ARR by validating that fixes don't break functionality.

Test Strategy:
1. Validate canonical import paths work correctly
2. Test backward compatibility during migration
3. Ensure no functional regression during migration
4. Validate SSOT consolidation effectiveness

These tests validate the migration strategy is sound before applying fixes.
"""

import unittest
import importlib
import sys
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Optional
import warnings

from test_framework.ssot.base_test_case import SSotBaseTestCase


class DeprecationMigrationValidationTests(SSotBaseTestCase):
    """Validate migration paths for deprecated imports"""
    
    def setUp(self):
        super().setUp()
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        
        # Define migration mappings based on ISSUE #1144
        self.migration_mappings = {
            # WebSocket Core migrations
            'from netra_backend.app.websocket_core import WebSocketManager': [
                'from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager',
                'from netra_backend.app.websocket_core.manager import WebSocketManager'
            ],
            'from netra_backend.app.websocket_core.event_validator import get_websocket_validator': [
                'from netra_backend.app.websocket_core.event_validation_framework import get_websocket_validator'
            ],
            'from netra_backend.app.websocket_core import create_websocket_manager': [
                'from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager'
            ],
            'from netra_backend.app.websocket_core import get_websocket_manager': [
                'from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager'
            ]
        }
        
        self.test_results = {
            'working_migrations': 0,
            'failing_migrations': 0,
            'migration_details': []
        }
    
    def test_canonical_import_paths_functional(self):
        """
        Validate that all canonical import paths actually work
        
        This ensures the migration guidance is accurate and functional.
        """
        print("\n=== Testing Canonical Import Path Functionality ===")
        
        working_imports = 0
        total_imports = 0
        
        for deprecated_import, canonical_options in self.migration_mappings.items():
            print(f"\n🔄 Testing migrations for: {deprecated_import}")
            
            for canonical_import in canonical_options:
                total_imports += 1
                print(f"  🧪 Testing: {canonical_import}")
                
                # Test canonical import in isolated environment
                test_success = self._test_import_in_isolation(canonical_import)
                
                if test_success:
                    print(f"    ✓ Import successful")
                    working_imports += 1
                    self.test_results['working_migrations'] += 1
                else:
                    print(f"    ✗ Import failed")
                    self.test_results['failing_migrations'] += 1
                
                self.test_results['migration_details'].append({
                    'deprecated': deprecated_import,
                    'canonical': canonical_import,
                    'working': test_success
                })
        
        success_rate = working_imports / total_imports if total_imports > 0 else 0
        print(f"\n📊 Canonical Import Success Rate: {success_rate:.1%} ({working_imports}/{total_imports})")
        
        # At least 80% of canonical imports should work
        self.assertGreaterEqual(
            success_rate, 0.8,
            f"Canonical import success rate too low: {success_rate:.1%}. "
            f"This indicates migration paths need fixing before deprecation removal."
        )
    
    def test_functional_equivalence_validation(self):
        """
        Validate that canonical imports provide equivalent functionality
        
        Ensures migrated code maintains the same behavior.
        """
        print("\n=== Testing Functional Equivalence ===")
        
        equivalence_tests = [
            {
                'name': 'WebSocketManager functionality',
                'deprecated_code': '''
try:
    from netra_backend.app.websocket_core import WebSocketManager
    manager = WebSocketManager
    result = "WebSocketManager imported successfully"
except Exception as e:
    result = f"Failed: {e}"
print(result)
''',
                'canonical_code': '''
try:
    from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
    manager = WebSocketManager
    result = "WebSocketManager imported successfully"
except Exception as e:
    result = f"Failed: {e}"
print(result)
'''
            },
            {
                'name': 'Event validator functionality',
                'deprecated_code': '''
try:
    from netra_backend.app.websocket_core.event_validator import get_websocket_validator
    validator = get_websocket_validator
    result = f"get_websocket_validator: {validator is not None}"
except Exception as e:
    result = f"Failed: {e}"
print(result)
''',
                'canonical_code': '''
try:
    from netra_backend.app.websocket_core.event_validation_framework import get_websocket_validator
    validator = get_websocket_validator
    result = f"get_websocket_validator: {validator is not None}"
except Exception as e:
    result = f"Failed: {e}"
print(result)
'''
            }
        ]
        
        equivalence_results = []
        
        for test_case in equivalence_tests:
            print(f"\n🧪 Testing {test_case['name']}")
            
            # Run deprecated version (may generate warnings)
            deprecated_result = self._run_code_in_isolation(
                test_case['deprecated_code'], 
                capture_warnings=True
            )
            
            # Run canonical version
            canonical_result = self._run_code_in_isolation(
                test_case['canonical_code'], 
                capture_warnings=False
            )
            
            print(f"  📊 Deprecated result: {deprecated_result['output']}")
            print(f"  📊 Canonical result: {canonical_result['output']}")
            print(f"  📊 Warnings in deprecated: {len(deprecated_result.get('warnings', []))}")
            
            # Check for functional equivalence
            functional_equivalent = (
                deprecated_result['success'] == canonical_result['success'] and
                "imported successfully" in deprecated_result['output'] and
                "imported successfully" in canonical_result['output']
            )
            
            equivalence_results.append({
                'test': test_case['name'],
                'equivalent': functional_equivalent,
                'deprecated_success': deprecated_result['success'],
                'canonical_success': canonical_result['success']
            })
            
            print(f"  🔍 Functionally equivalent: {functional_equivalent}")
        
        # All tests should show functional equivalence
        failed_equivalence = [r for r in equivalence_results if not r['equivalent']]
        
        self.assertEqual(
            len(failed_equivalence), 0,
            f"Functional equivalence failed for: {[r['test'] for r in failed_equivalence]}"
        )
    
    def test_migration_impact_analysis(self):
        """
        Analyze the scope and impact of required migrations
        
        Provides data for planning the migration effort.
        """
        print("\n=== Testing Migration Impact Analysis ===")
        
        # Find all files that need migration
        files_needing_migration = []
        total_deprecated_imports = 0
        
        for deprecated_pattern in self.migration_mappings.keys():
            # Extract the import pattern for searching
            import_module = deprecated_pattern.split(' import ')[0].replace('from ', '')
            
            print(f"🔍 Searching for imports from: {import_module}")
            
            # Search for files using this deprecated import
            result = subprocess.run([
                "grep", "-r", "-l", f"from {import_module}", 
                str(self.project_root / "netra_backend"),
                str(self.project_root / "tests")
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                files_needing_migration.extend(files)
                total_deprecated_imports += len(files)
                
                print(f"  📁 Found {len(files)} files using deprecated import")
                for file_path in files[:5]:  # Show first 5 files
                    print(f"    - {file_path}")
                if len(files) > 5:
                    print(f"    ... and {len(files) - 5} more")
        
        # Remove duplicates
        unique_files = list(set(files_needing_migration))
        
        print(f"\n📊 Migration Impact Summary:")
        print(f"  Total files needing migration: {len(unique_files)}")
        print(f"  Total deprecated import instances: {total_deprecated_imports}")
        print(f"  Average imports per file: {total_deprecated_imports / len(unique_files) if unique_files else 0:.1f}")
        
        # Categorize files by type
        file_categories = {
            'test_files': [f for f in unique_files if '/test' in f],
            'source_files': [f for f in unique_files if '/test' not in f],
            'agent_files': [f for f in unique_files if '/agent' in f],
            'websocket_files': [f for f in unique_files if '/websocket' in f]
        }
        
        for category, files in file_categories.items():
            print(f"  {category}: {len(files)} files")
        
        # Store results for test validation
        self.migration_impact = {
            'total_files': len(unique_files),
            'total_imports': total_deprecated_imports,
            'categories': file_categories
        }
        
        # Validate migration scope is reasonable
        self.assertLess(
            len(unique_files), 1000,
            f"Migration scope too large: {len(unique_files)} files. "
            "Consider phased migration approach."
        )
        
        # Should find some files to migrate (otherwise deprecation is unnecessary)
        self.assertGreater(
            len(unique_files), 0,
            "No files found using deprecated imports. "
            "Either search is incorrect or deprecation is already complete."
        )
    
    def test_ssot_consolidation_readiness(self):
        """
        Validate system readiness for SSOT Phase 2 consolidation
        
        Ensures the system can handle the removal of deprecated imports.
        """
        print("\n=== Testing SSOT Consolidation Readiness ===")
        
        readiness_checks = {
            'canonical_imports_functional': False,
            'migration_paths_documented': False,
            'no_circular_dependencies': False,
            'test_coverage_adequate': False
        }
        
        # Check 1: Canonical imports functional
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            from netra_backend.app.websocket_core.event_validation_framework import get_websocket_validator
            readiness_checks['canonical_imports_functional'] = True
            print("  ✓ Canonical imports functional")
        except Exception as e:
            print(f"  ✗ Canonical imports failed: {e}")
        
        # Check 2: Migration paths documented
        migration_doc_exists = (self.project_root / "docs" / "SSOT_IMPORT_REGISTRY.md").exists()
        readiness_checks['migration_paths_documented'] = migration_doc_exists
        print(f"  {'✓' if migration_doc_exists else '✗'} Migration paths documented")
        
        # Check 3: No circular dependencies (basic check)
        try:
            # Test import chain doesn't create circles
            import netra_backend.app.websocket_core.websocket_manager
            import netra_backend.app.websocket_core.event_validation_framework
            readiness_checks['no_circular_dependencies'] = True
            print("  ✓ No obvious circular dependencies")
        except Exception as e:
            print(f"  ✗ Potential circular dependency: {e}")
        
        # Check 4: Test coverage for migration
        test_files = list(self.project_root.glob("tests/**/test_*deprecation*.py"))
        readiness_checks['test_coverage_adequate'] = len(test_files) > 0
        print(f"  {'✓' if len(test_files) > 0 else '✗'} Test coverage for deprecation migration")
        
        readiness_score = sum(readiness_checks.values()) / len(readiness_checks)
        print(f"\n📊 SSOT Consolidation Readiness: {readiness_score:.1%}")
        
        for check, status in readiness_checks.items():
            print(f"  {check}: {'✓' if status else '✗'}")
        
        # Should be at least 75% ready for Phase 2
        self.assertGreaterEqual(
            readiness_score, 0.75,
            f"System not ready for SSOT Phase 2. Readiness: {readiness_score:.1%}"
        )
    
    def _test_import_in_isolation(self, import_statement: str) -> bool:
        """Test an import statement in an isolated Python process"""
        test_code = f"""
import sys
sys.path.insert(0, '/Users/anthony/Desktop/netra-apex')

try:
    {import_statement}
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {{e}}")
"""
        
        result = self._run_code_in_isolation(test_code)
        return result['success'] and "SUCCESS" in result['output']
    
    def _run_code_in_isolation(self, code: str, capture_warnings: bool = False) -> Dict:
        """Run Python code in an isolated process and return results"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            if capture_warnings:
                f.write("import warnings\nwarnings.simplefilter('always')\n")
            f.write(code)
            temp_file = f.name
        
        try:
            args = [sys.executable, temp_file]
            if capture_warnings:
                args.insert(-1, "-W")
                args.insert(-1, "always")
                
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            warnings_captured = []
            if capture_warnings and result.stderr:
                warnings_captured = [
                    line for line in result.stderr.split('\n') 
                    if 'DeprecationWarning' in line
                ]
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout.strip(),
                'error': result.stderr.strip(),
                'warnings': warnings_captured
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': 'Timeout',
                'warnings': []
            }
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass


if __name__ == '__main__':
    print("🔄 Issue #416 Migration Validation Test Suite")
    print("=" * 60)
    print("Purpose: Validate migration paths for deprecated imports")
    print("Expected: All canonical imports should work correctly")
    print("=" * 60)
    
    unittest.main(verbosity=2)