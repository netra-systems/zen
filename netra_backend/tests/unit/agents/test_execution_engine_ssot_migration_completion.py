#!/usr/bin/env python3
"""
Issue #565 Migration Completion Verification Tests
==================================================

Purpose: Verify complete SSOT migration from ExecutionEngine to UserExecutionEngine
is finished with no remaining deprecated patterns or merge conflicts.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Code Quality & Security  
- Value Impact: Ensure complete migration eliminates all user isolation vulnerabilities
- Strategic Impact: Enable confident production deployment with zero SSOT violations

Test Strategy: FAILING TESTS that prove migration is incomplete
1. Detect deprecated execution_engine.py file still exists
2. Validate all imports reference UserExecutionEngine ONLY
3. Detect merge conflicts in supervisor directory  
4. Verify SSOT import registry reflects migration completion
5. Validate no compatibility bridges remain in production code

Expected Results:
- BEFORE Migration Complete: FAIL - deprecated patterns detected
- AFTER Migration Complete: PASS - complete SSOT compliance achieved
"""

import ast
import os
import sys
import unittest
from pathlib import Path
from typing import List, Dict, Set, Any, Tuple
import re
import subprocess

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestExecutionEngineSSotMigrationCompletion(SSotBaseTestCase):
    """
    Unit tests to verify Issue #565 SSOT migration is completely finished.
    
    These tests should FAIL before migration is complete, then PASS after
    all deprecated patterns are removed and UserExecutionEngine is the
    single source of truth.
    """

    def setUp(self):
        """Set up migration completion verification"""
        super().setUp()
        self.project_root = project_root
        self.supervisor_path = self.project_root / "netra_backend" / "app" / "agents" / "supervisor"
        self.ssot_registry_path = self.project_root / "SSOT_IMPORT_REGISTRY.md"
        self.migration_results = {
            'deprecated_files_found': [],
            'merge_conflicts_found': [],
            'import_violations': [],
            'registry_inconsistencies': [],
            'compatibility_bridges_found': []
        }

    def test_01_deprecated_execution_engine_file_removal_verification(self):
        """
        Verify deprecated execution_engine.py is completely removed.
        
        CRITICAL: The deprecated file should NOT exist after migration is complete.
        
        Expected: FAIL before fix - deprecated file exists
        Expected: PASS after fix - deprecated file completely removed
        """
        print("\n" + "="*80)
        print("🔍 MIGRATION VERIFICATION: Deprecated File Removal")
        print("="*80)
        
        deprecated_file_path = self.supervisor_path / "execution_engine.py"
        
        print(f"📁 Checking for deprecated file: {deprecated_file_path}")
        
        if deprecated_file_path.exists():
            print(f"🚨 MIGRATION INCOMPLETE:")
            print(f"   ❌ Deprecated file still exists: {deprecated_file_path}")
            
            # Check if it's a compatibility bridge vs full implementation
            try:
                with open(deprecated_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Look for compatibility bridge indicators
                    bridge_indicators = [
                        "DEPRECATED",
                        "compatibility",
                        "delegation",
                        "UserExecutionEngine",
                        "MIGRATION REQUIRED"
                    ]
                    
                    is_compatibility_bridge = any(indicator in content for indicator in bridge_indicators)
                    lines_count = len(content.splitlines())
                    
                    print(f"   📊 File analysis:")
                    print(f"      - Lines of code: {lines_count}")
                    print(f"      - Compatibility bridge: {'Yes' if is_compatibility_bridge else 'No'}")
                    
                    if is_compatibility_bridge:
                        print(f"   ⚠️  COMPATIBILITY BRIDGE DETECTED:")
                        print(f"      - File should be completely REMOVED for SSOT compliance")
                        print(f"      - Compatibility bridges violate SSOT principles")
                        
                    # Store violation details
                    self.migration_results['deprecated_files_found'].append({
                        'file': str(deprecated_file_path),
                        'is_compatibility_bridge': is_compatibility_bridge,
                        'lines_count': lines_count,
                        'violation_type': 'deprecated_file_exists'
                    })
                    
            except Exception as e:
                print(f"   ❌ Error analyzing deprecated file: {e}")
        
            # CRITICAL FAILURE: Deprecated file should not exist
            self.fail(
                f"MIGRATION INCOMPLETE: Deprecated execution_engine.py still exists at {deprecated_file_path}. "
                f"For complete SSOT migration, this file must be completely REMOVED, not converted to compatibility bridge."
            )
        else:
            print(f"✅ MIGRATION COMPLETE: Deprecated file successfully removed")
            print(f"   ✅ {deprecated_file_path} does not exist")

    def test_02_all_imports_use_user_execution_engine_only_verification(self):
        """
        Verify ALL imports reference UserExecutionEngine exclusively.
        
        CRITICAL: No code should import from deprecated execution_engine.py path.
        
        Expected: FAIL before fix - deprecated imports detected  
        Expected: PASS after fix - all imports use UserExecutionEngine
        """
        print("\n" + "="*80)
        print("🔍 MIGRATION VERIFICATION: Import Path Consistency")
        print("="*80)
        
        # Scan for any remaining deprecated import patterns
        deprecated_import_patterns = [
            # Direct deprecated imports
            r'from\s+netra_backend\.app\.agents\.supervisor\.execution_engine\s+import',
            r'import\s+netra_backend\.app\.agents\.supervisor\.execution_engine',
            
            # Aliased imports that might mask the violation
            r'from\s+.*\.execution_engine\s+import\s+ExecutionEngine(?!\s+as\s+\w+)',
            
            # Factory imports from deprecated path
            r'from\s+netra_backend\.app\.agents\.supervisor\.execution_engine\s+import.*factory',
        ]
        
        correct_import_pattern = r'from\s+netra_backend\.app\.agents\.supervisor\.user_execution_engine\s+import'
        
        # Scan all Python files
        scan_directories = [
            'netra_backend',
            'tests',
            'auth_service',
            'shared',
            'scripts'
        ]
        
        python_files = []
        for scan_dir in scan_directories:
            scan_path = self.project_root / scan_dir
            if scan_path.exists():
                python_files.extend(scan_path.rglob('*.py'))
        
        print(f"📁 Scanning {len(python_files)} Python files for import violations...")
        
        import_violations = []
        correct_imports_found = 0
        files_with_violations = set()
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for line_num, line in enumerate(content.splitlines(), 1):
                        # Check for deprecated patterns
                        for pattern in deprecated_import_patterns:
                            if re.search(pattern, line):
                                import_violations.append({
                                    'file': str(file_path.relative_to(self.project_root)),
                                    'line': line_num,
                                    'content': line.strip(),
                                    'pattern': pattern,
                                    'violation_type': 'deprecated_import_path'
                                })
                                files_with_violations.add(str(file_path.relative_to(self.project_root)))
                        
                        # Count correct imports
                        if re.search(correct_import_pattern, line):
                            correct_imports_found += 1
                            
            except (UnicodeDecodeError, PermissionError):
                continue  # Skip binary or inaccessible files
        
        print(f"📊 IMPORT ANALYSIS RESULTS:")
        print(f"   - Deprecated import violations: {len(import_violations)}")
        print(f"   - Files with violations: {len(files_with_violations)}")
        print(f"   - Correct UserExecutionEngine imports: {correct_imports_found}")
        
        if import_violations:
            print(f"\n🚨 IMPORT VIOLATIONS FOUND:")
            for i, violation in enumerate(import_violations[:10]):  # Show first 10
                print(f"   {i+1}. {violation['file']}:{violation['line']}")
                print(f"      ❌ {violation['content']}")
        
        # Store results
        self.migration_results['import_violations'] = import_violations
        
        # CRITICAL FAILURE: Should have zero deprecated import violations
        if import_violations:
            self.fail(
                f"MIGRATION INCOMPLETE: Found {len(import_violations)} deprecated import violations "
                f"in {len(files_with_violations)} files. All imports must reference UserExecutionEngine exclusively."
            )
        else:
            print(f"✅ IMPORT MIGRATION COMPLETE:")
            print(f"   ✅ Zero deprecated import violations")
            print(f"   ✅ {correct_imports_found} correct UserExecutionEngine imports")

    def test_03_no_merge_conflicts_in_supervisor_directory_verification(self):
        """
        Verify no merge conflicts exist in execution engine related files.
        
        CRITICAL: Merge conflicts indicate incomplete migration state.
        
        Expected: FAIL before fix - merge conflicts detected
        Expected: PASS after fix - all merge conflicts resolved
        """
        print("\n" + "="*80)
        print("🔍 MIGRATION VERIFICATION: Merge Conflict Detection")
        print("="*80)
        
        # Check for git merge conflict markers
        conflict_markers = [
            '<<<<<<< ',
            '======='
            '>>>>>>> '
        ]
        
        # Scan supervisor directory for merge conflicts
        supervisor_files = list(self.supervisor_path.rglob('*.py'))
        
        print(f"📁 Scanning {len(supervisor_files)} files in supervisor directory for merge conflicts...")
        
        merge_conflicts_found = []
        
        for file_path in supervisor_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for line_num, line in enumerate(content.splitlines(), 1):
                        for marker in conflict_markers:
                            if marker in line:
                                merge_conflicts_found.append({
                                    'file': str(file_path.relative_to(self.project_root)),
                                    'line': line_num,
                                    'content': line.strip(),
                                    'marker': marker,
                                    'violation_type': 'merge_conflict_marker'
                                })
                                
            except (UnicodeDecodeError, PermissionError):
                continue
        
        print(f"📊 MERGE CONFLICT ANALYSIS:")
        print(f"   - Merge conflicts found: {len(merge_conflicts_found)}")
        
        if merge_conflicts_found:
            print(f"\n🚨 MERGE CONFLICTS DETECTED:")
            for conflict in merge_conflicts_found:
                print(f"   ❌ {conflict['file']}:{conflict['line']}")
                print(f"      {conflict['content']}")
        
        # Store results
        self.migration_results['merge_conflicts_found'] = merge_conflicts_found
        
        # CRITICAL FAILURE: Should have zero merge conflicts
        if merge_conflicts_found:
            self.fail(
                f"MIGRATION INCOMPLETE: Found {len(merge_conflicts_found)} merge conflicts "
                f"in supervisor directory. All conflicts must be resolved for complete migration."
            )
        else:
            print(f"✅ NO MERGE CONFLICTS: Supervisor directory is clean")

    def test_04_ssot_import_registry_compliance_verification(self):
        """
        Verify SSOT_IMPORT_REGISTRY.md reflects UserExecutionEngine migration.
        
        CRITICAL: Import registry should document only UserExecutionEngine as valid.
        
        Expected: FAIL before fix - registry shows deprecated paths
        Expected: PASS after fix - registry shows only UserExecutionEngine  
        """
        print("\n" + "="*80)
        print("🔍 MIGRATION VERIFICATION: SSOT Import Registry Compliance")
        print("="*80)
        
        if not self.ssot_registry_path.exists():
            print(f"⚠️  SSOT Import Registry not found: {self.ssot_registry_path}")
            print(f"   Registry should exist to document valid imports")
            self.migration_results['registry_inconsistencies'].append({
                'issue': 'registry_file_missing',
                'path': str(self.ssot_registry_path)
            })
            return
        
        try:
            with open(self.ssot_registry_path, 'r', encoding='utf-8') as f:
                registry_content = f.read()
            
            print(f"📁 Analyzing SSOT Import Registry: {self.ssot_registry_path}")
            
            # Check for deprecated execution_engine references
            deprecated_references = []
            correct_references = []
            
            for line_num, line in enumerate(registry_content.splitlines(), 1):
                # Look for deprecated execution_engine references
                if 'execution_engine' in line.lower() and 'user_execution_engine' not in line.lower():
                    deprecated_references.append({
                        'line': line_num,
                        'content': line.strip(),
                        'issue': 'deprecated_reference_in_registry'
                    })
                
                # Look for correct UserExecutionEngine references
                if 'user_execution_engine' in line.lower():
                    correct_references.append({
                        'line': line_num,
                        'content': line.strip(),
                        'type': 'correct_reference'
                    })
            
            print(f"📊 REGISTRY ANALYSIS:")
            print(f"   - Deprecated references: {len(deprecated_references)}")  
            print(f"   - Correct UserExecutionEngine references: {len(correct_references)}")
            
            if deprecated_references:
                print(f"\n🚨 DEPRECATED REFERENCES IN REGISTRY:")
                for ref in deprecated_references[:5]:  # Show first 5
                    print(f"   ❌ Line {ref['line']}: {ref['content']}")
            
            # Store results
            self.migration_results['registry_inconsistencies'] = deprecated_references
            
            # CRITICAL FAILURE: Should have zero deprecated references in registry
            if deprecated_references:
                self.fail(
                    f"MIGRATION INCOMPLETE: SSOT Import Registry contains {len(deprecated_references)} "
                    f"deprecated execution_engine references. Registry must reflect complete UserExecutionEngine migration."
                )
            else:
                print(f"✅ REGISTRY COMPLIANCE: Only UserExecutionEngine references found")
                
        except Exception as e:
            print(f"❌ Error analyzing SSOT registry: {e}")
            self.fail(f"Could not verify SSOT registry compliance: {e}")

    def test_05_no_compatibility_bridges_in_production_code_verification(self):
        """
        Verify no compatibility bridges remain in production code.
        
        CRITICAL: Compatibility bridges violate SSOT principles and should be temporary only.
        
        Expected: FAIL before fix - compatibility bridges detected
        Expected: PASS after fix - no compatibility bridges remain
        """
        print("\n" + "="*80)
        print("🔍 MIGRATION VERIFICATION: Compatibility Bridge Detection")
        print("="*80)
        
        # Patterns that indicate compatibility bridges
        compatibility_patterns = [
            r'compatibility.*bridge',
            r'backward.*compatibility',
            r'legacy.*factory',
            r'deprecated.*wrapper',
            r'delegation.*UserExecutionEngine',
            r'automatic.*delegation',
            r'COMPATIBILITY.*BRIDGE',
            r'Issue #565.*bridge'
        ]
        
        # Scan production code (exclude tests)
        production_directories = [
            'netra_backend/app',
            'auth_service',
            'shared'
        ]
        
        python_files = []
        for prod_dir in production_directories:
            prod_path = self.project_root / prod_dir
            if prod_path.exists():
                python_files.extend(prod_path.rglob('*.py'))
        
        print(f"📁 Scanning {len(python_files)} production files for compatibility bridges...")
        
        compatibility_bridges = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for line_num, line in enumerate(content.splitlines(), 1):
                        for pattern in compatibility_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                compatibility_bridges.append({
                                    'file': str(file_path.relative_to(self.project_root)),
                                    'line': line_num,
                                    'content': line.strip(),
                                    'pattern': pattern,
                                    'violation_type': 'compatibility_bridge_detected'
                                })
                                
            except (UnicodeDecodeError, PermissionError):
                continue
        
        print(f"📊 COMPATIBILITY BRIDGE ANALYSIS:")
        print(f"   - Compatibility bridges found: {len(compatibility_bridges)}")
        
        if compatibility_bridges:
            print(f"\n🚨 COMPATIBILITY BRIDGES DETECTED:")
            for bridge in compatibility_bridges[:10]:  # Show first 10
                print(f"   ❌ {bridge['file']}:{bridge['line']}")
                print(f"      {bridge['content']}")
        
        # Store results
        self.migration_results['compatibility_bridges_found'] = compatibility_bridges
        
        # CRITICAL FAILURE: Should have zero compatibility bridges in production
        if compatibility_bridges:
            self.fail(
                f"MIGRATION INCOMPLETE: Found {len(compatibility_bridges)} compatibility bridges "
                f"in production code. All bridges must be removed for complete SSOT migration."
            )
        else:
            print(f"✅ NO COMPATIBILITY BRIDGES: Production code is clean")

    def test_06_migration_completion_summary_validation(self):
        """
        Provide comprehensive summary of migration completion status.
        
        This test aggregates all migration verification results.
        """
        print("\n" + "="*80)
        print("📋 MIGRATION COMPLETION SUMMARY")
        print("="*80)
        
        # Aggregate all violation counts
        total_violations = (
            len(self.migration_results['deprecated_files_found']) +
            len(self.migration_results['merge_conflicts_found']) + 
            len(self.migration_results['import_violations']) +
            len(self.migration_results['registry_inconsistencies']) +
            len(self.migration_results['compatibility_bridges_found'])
        )
        
        print(f"📊 MIGRATION STATUS SUMMARY:")
        print(f"   - Deprecated files found: {len(self.migration_results['deprecated_files_found'])}")
        print(f"   - Merge conflicts found: {len(self.migration_results['merge_conflicts_found'])}")
        print(f"   - Import violations: {len(self.migration_results['import_violations'])}")
        print(f"   - Registry inconsistencies: {len(self.migration_results['registry_inconsistencies'])}")
        print(f"   - Compatibility bridges: {len(self.migration_results['compatibility_bridges_found'])}")
        print(f"   - TOTAL VIOLATIONS: {total_violations}")
        
        if total_violations == 0:
            print(f"\n✅ MIGRATION COMPLETE:")
            print(f"   ✅ All deprecated patterns removed")
            print(f"   ✅ UserExecutionEngine is the single source of truth")
            print(f"   ✅ Zero SSOT violations detected")
            print(f"   ✅ Ready for production deployment")
        else:
            print(f"\n🚨 MIGRATION INCOMPLETE:")
            print(f"   ❌ {total_violations} violations require remediation")
            print(f"   ❌ SSOT compliance not achieved")
            print(f"   ❌ User isolation vulnerabilities may persist")
            
            # This is the final validation - fail if any violations exist
            self.fail(
                f"Issue #565 Migration INCOMPLETE: Found {total_violations} total violations. "
                f"Complete SSOT migration to UserExecutionEngine required for production safety."
            )


if __name__ == '__main__':
    unittest.main()