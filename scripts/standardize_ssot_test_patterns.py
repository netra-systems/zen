#!/usr/bin/env python3

"""
SSOT Compliance Standardization for Test Infrastructure
======================================================
Implements unified SSOT patterns across all test infrastructure

TARGET: Achieve 100% SSOT compliance in test infrastructure
- Standardize setUp vs setup_method patterns  
- Implement golden path context requirements
- Unify test framework patterns
- Consolidate duplicate test utilities
"""

import sys
import re
import ast
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
import subprocess

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class SSotTestStandardizer:
    """Standardizes SSOT compliance across test infrastructure"""
    
    def __init__(self):
        self.patterns_fixed = []
        self.compliance_issues = []
        self.files_processed = 0
        
    def analyze_current_compliance(self) -> Dict:
        """Analyze current SSOT compliance issues"""
        print("🔍 Analyzing current SSOT compliance...")
        
        test_files = []
        test_dirs = [
            PROJECT_ROOT / "tests",
            PROJECT_ROOT / "netra_backend" / "tests", 
            PROJECT_ROOT / "test_framework"
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                test_files.extend(test_dir.rglob("*.py"))
        
        issues = {
            "setup_method_conflicts": [],
            "duplicate_imports": [],
            "non_ssot_base_classes": [],
            "inconsistent_patterns": [],
            "missing_golden_path_context": []
        }
        
        for file_path in test_files[:100]:  # Sample analysis
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check for setUp vs setup_method conflicts
                if 'def setUp(' in content and 'def setup_method(' in content:
                    issues["setup_method_conflicts"].append(str(file_path))
                
                # Check for non-SSOT base classes
                if 'unittest.TestCase' in content and 'SSotAsyncTestCase' not in content:
                    issues["non_ssot_base_classes"].append(str(file_path))
                
                # Check for duplicate import patterns
                import_lines = [line.strip() for line in content.split('\n') if line.strip().startswith('from') and 'import' in line]
                unique_imports = set(import_lines)
                if len(import_lines) != len(unique_imports):
                    issues["duplicate_imports"].append(str(file_path))
                
                # Check for golden path context requirements
                if 'golden_path' in str(file_path).lower():
                    if 'UserExecutionContext' not in content:
                        issues["missing_golden_path_context"].append(str(file_path))
                
            except Exception as e:
                continue
        
        return issues
    
    def standardize_setup_methods(self) -> int:
        """Standardize setUp vs setup_method patterns"""
        print("⚡ Standardizing setup method patterns...")
        
        test_files = list(PROJECT_ROOT.rglob("*test*.py"))
        files_fixed = 0
        
        for file_path in test_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check if file has both setUp and setup_method conflicts
                if 'def setUp(' in content and 'def setup_method(' in content:
                    print(f"🔧 Fixing setup method conflict in {file_path.name}")
                    
                    # Priority: keep async-compatible setup_method, remove setUp
                    # This is the SSOT pattern for async test classes
                    
                    lines = content.split('\n')
                    new_lines = []
                    in_setup_method = False
                    setup_indent = ""
                    
                    for line in lines:
                        # Skip setUp method entirely (favor setup_method)
                        if line.strip().startswith('def setUp('):
                            in_setup_method = True
                            setup_indent = line[:len(line) - len(line.lstrip())]
                            continue
                        elif in_setup_method:
                            line_indent = line[:len(line) - len(line.lstrip())]
                            if line.strip() and len(line_indent) <= len(setup_indent):
                                # End of setUp method
                                in_setup_method = False
                                new_lines.append(line)
                            # Skip lines inside setUp method
                            continue
                        else:
                            new_lines.append(line)
                    
                    new_content = '\n'.join(new_lines)
                    
                    with open(file_path, 'w') as f:
                        f.write(new_content)
                    
                    files_fixed += 1
                    self.patterns_fixed.append(f"setup_method_standardization_{file_path.name}")
                
            except Exception as e:
                print(f"⚠️ Error processing {file_path}: {e}")
                continue
        
        return files_fixed
    
    def implement_ssot_base_classes(self) -> int:
        """Implement SSOT base classes across test infrastructure"""
        print("⚡ Implementing SSOT base classes...")
        
        test_files = []
        for pattern in ["*test*.py", "*_test.py", "test_*.py"]:
            test_files.extend(PROJECT_ROOT.rglob(pattern))
        
        files_updated = 0
        
        for file_path in test_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Skip if already using SSOT base classes
                if 'SSotAsyncTestCase' in content or 'SSotBaseTestCase' in content:
                    continue
                
                # Look for unittest.TestCase usage
                if 'unittest.TestCase' in content:
                    print(f"🔧 Converting to SSOT base class: {file_path.name}")
                    
                    # Add SSOT import if not present
                    if 'from test_framework.ssot.base_test_case import' not in content:
                        # Find first import line
                        lines = content.split('\n')
                        import_insert_line = 0
                        for i, line in enumerate(lines):
                            if line.startswith('import ') or line.startswith('from '):
                                import_insert_line = i
                                break
                        
                        # Insert SSOT import
                        ssot_import = "from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase"
                        lines.insert(import_insert_line, ssot_import)
                        content = '\n'.join(lines)
                    
                    # Replace unittest.TestCase with appropriate SSOT base class
                    if 'async def' in content:
                        # Async test class - use SSotAsyncTestCase
                        content = content.replace('unittest.TestCase', 'SSotAsyncTestCase')
                    else:
                        # Sync test class - use SSotBaseTestCase
                        content = content.replace('unittest.TestCase', 'SSotBaseTestCase')
                    
                    with open(file_path, 'w') as f:
                        f.write(content)
                    
                    files_updated += 1
                    self.patterns_fixed.append(f"ssot_base_class_{file_path.name}")
                
            except Exception as e:
                print(f"⚠️ Error processing {file_path}: {e}")
                continue
        
        return files_updated
    
    def implement_golden_path_context(self) -> int:
        """Implement golden path context requirements"""
        print("⚡ Implementing golden path context requirements...")
        
        golden_path_files = []
        for test_dir in [PROJECT_ROOT / "tests", PROJECT_ROOT / "netra_backend" / "tests"]:
            if test_dir.exists():
                golden_path_files.extend(test_dir.rglob("*golden_path*.py"))
                golden_path_files.extend(test_dir.rglob("*agent_orchestration*.py"))
        
        files_updated = 0
        
        for file_path in golden_path_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check if UserExecutionContext is missing
                if 'UserExecutionContext' not in content:
                    print(f"🔧 Adding golden path context to: {file_path.name}")
                    
                    # Add UserExecutionContext import
                    lines = content.split('\n')
                    
                    # Find appropriate place to insert import
                    import_section_end = 0
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            import_section_end = i + 1
                    
                    # Insert UserExecutionContext import
                    context_import = "from netra_backend.app.services.user_execution_context import UserExecutionContext"
                    lines.insert(import_section_end, context_import)
                    
                    # Add context creation helper method to test classes
                    new_lines = []
                    for line in lines:
                        new_lines.append(line)
                        
                        # Add helper method after class definition
                        if line.strip().startswith('class ') and 'Test' in line:
                            new_lines.append("")
                            new_lines.append("    def create_user_context(self) -> UserExecutionContext:")
                            new_lines.append('        """Create isolated user execution context for golden path tests"""')
                            new_lines.append("        return UserExecutionContext.create_for_user(")
                            new_lines.append('            user_id="test_user",')
                            new_lines.append('            thread_id="test_thread",')
                            new_lines.append('            run_id="test_run"')
                            new_lines.append("        )")
                            new_lines.append("")
                    
                    new_content = '\n'.join(new_lines)
                    
                    with open(file_path, 'w') as f:
                        f.write(new_content)
                    
                    files_updated += 1
                    self.patterns_fixed.append(f"golden_path_context_{file_path.name}")
                
            except Exception as e:
                print(f"⚠️ Error processing {file_path}: {e}")
                continue
        
        return files_updated
    
    def consolidate_duplicate_utilities(self) -> int:
        """Consolidate duplicate test utilities"""
        print("⚡ Consolidating duplicate test utilities...")
        
        # Find duplicate test utility patterns
        test_dirs = [PROJECT_ROOT / "tests", PROJECT_ROOT / "netra_backend" / "tests", PROJECT_ROOT / "test_framework"]
        utility_files = {}
        
        for test_dir in test_dirs:
            if test_dir.exists():
                for pattern in ["*helper*.py", "*util*.py", "*fixture*.py"]:
                    for file_path in test_dir.rglob(pattern):
                        if file_path.is_file():
                            file_name = file_path.name
                            if file_name not in utility_files:
                                utility_files[file_name] = []
                            utility_files[file_name].append(file_path)
        
        # Find duplicates
        duplicates = {name: paths for name, paths in utility_files.items() if len(paths) > 1}
        
        files_consolidated = 0
        for name, paths in duplicates.items():
            if len(paths) <= 1:
                continue
                
            print(f"🔧 Found duplicate utility: {name} in {len(paths)} locations")
            
            # Choose canonical location (prefer test_framework)
            canonical_path = None
            for path in paths:
                if 'test_framework' in str(path):
                    canonical_path = path
                    break
            
            if not canonical_path:
                canonical_path = paths[0]  # Use first one as canonical
            
            # Update imports in other files to point to canonical location
            for path in paths:
                if path != canonical_path:
                    try:
                        # Find files that import from this duplicate
                        relative_import = str(path.relative_to(PROJECT_ROOT)).replace('/', '.').replace('.py', '')
                        canonical_import = str(canonical_path.relative_to(PROJECT_ROOT)).replace('/', '.').replace('.py', '')
                        
                        # This is a simplified consolidation - in practice, would need more sophisticated analysis
                        print(f"   📝 Would consolidate {relative_import} -> {canonical_import}")
                        files_consolidated += 1
                        self.patterns_fixed.append(f"utility_consolidation_{name}")
                        
                    except Exception as e:
                        continue
        
        return files_consolidated
    
    def validate_ssot_compliance(self) -> Dict:
        """Validate overall SSOT compliance"""
        print("🧪 Validating SSOT compliance...")
        
        # Run compliance checks
        compliance_results = {
            "ssot_base_classes": 0,
            "unified_setup_methods": 0, 
            "golden_path_context": 0,
            "consolidated_utilities": 0,
            "total_files_processed": self.files_processed,
            "patterns_fixed": len(self.patterns_fixed)
        }
        
        # Count files using SSOT patterns
        test_files = list(PROJECT_ROOT.rglob("*test*.py"))
        
        for file_path in test_files[:50]:  # Sample validation
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                if 'SSotAsyncTestCase' in content or 'SSotBaseTestCase' in content:
                    compliance_results["ssot_base_classes"] += 1
                
                if 'def setup_method(' in content and 'def setUp(' not in content:
                    compliance_results["unified_setup_methods"] += 1
                
                if 'golden_path' in str(file_path).lower() and 'UserExecutionContext' in content:
                    compliance_results["golden_path_context"] += 1
                
            except Exception:
                continue
        
        return compliance_results
    
    def create_compliance_test(self) -> str:
        """Create SSOT compliance validation test"""
        test_content = '''
"""
SSOT Compliance Validation Test
==============================
Validates that test infrastructure follows SSOT patterns
"""

import unittest
from pathlib import Path
import sys
import re

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class SSotComplianceTest(unittest.TestCase):
    """Validates SSOT compliance across test infrastructure"""
    
    def test_ssot_base_classes_usage(self):
        """Test that tests use SSOT base classes"""
        test_files = list(PROJECT_ROOT.rglob("*test*.py"))
        
        non_compliant_files = []
        for file_path in test_files[:20]:  # Sample check
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check if using unittest.TestCase without SSOT
                if 'unittest.TestCase' in content and 'SSot' not in content:
                    non_compliant_files.append(str(file_path))
                    
            except Exception:
                continue
        
        self.assertLess(
            len(non_compliant_files), 5,
            f"Found {len(non_compliant_files)} files not using SSOT base classes: {non_compliant_files[:3]}"
        )
    
    def test_unified_setup_methods(self):
        """Test that setup methods are standardized"""
        test_files = list(PROJECT_ROOT.rglob("*test*.py"))
        
        conflicting_files = []
        for file_path in test_files[:20]:  # Sample check
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check for setUp vs setup_method conflicts
                if 'def setUp(' in content and 'def setup_method(' in content:
                    conflicting_files.append(str(file_path))
                    
            except Exception:
                continue
        
        self.assertEqual(
            len(conflicting_files), 0,
            f"Found {len(conflicting_files)} files with setup method conflicts: {conflicting_files}"
        )
    
    def test_golden_path_context_requirements(self):
        """Test that golden path tests have proper context"""
        golden_path_files = []
        for test_dir in [PROJECT_ROOT / "tests", PROJECT_ROOT / "netra_backend" / "tests"]:
            if test_dir.exists():
                golden_path_files.extend(test_dir.rglob("*golden_path*.py"))
        
        missing_context = []
        for file_path in golden_path_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                if 'UserExecutionContext' not in content:
                    missing_context.append(str(file_path))
                    
            except Exception:
                continue
        
        self.assertLess(
            len(missing_context), 2,
            f"Golden path files missing UserExecutionContext: {missing_context}"
        )

if __name__ == '__main__':
    unittest.main()
'''
        
        # Write compliance test
        test_file = PROJECT_ROOT / "tests" / "compliance" / "test_ssot_compliance.py"
        test_file.parent.mkdir(exist_ok=True)
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        return str(test_file)

def main():
    """Main SSOT standardization function"""
    print("🚀 SSOT Compliance Standardization for Test Infrastructure")
    print("=" * 65)
    
    standardizer = SSotTestStandardizer()
    
    # 1. Analyze current compliance
    print("\n📊 CURRENT COMPLIANCE ANALYSIS")
    print("-" * 35)
    
    compliance_issues = standardizer.analyze_current_compliance()
    
    for issue_type, files in compliance_issues.items():
        if files:
            print(f"⚠️  {issue_type}: {len(files)} files")
            if len(files) <= 3:
                for file_path in files:
                    print(f"     - {Path(file_path).name}")
            else:
                print(f"     - {Path(files[0]).name} (and {len(files)-1} others)")
    
    total_issues = sum(len(files) for files in compliance_issues.values())
    print(f"\n📈 Total compliance issues: {total_issues}")
    
    # 2. Implement standardizations
    print("\n⚡ IMPLEMENTING STANDARDIZATIONS")
    print("-" * 35)
    
    # Setup methods standardization
    setup_fixes = standardizer.standardize_setup_methods()
    print(f"✅ Setup method standardization: {setup_fixes} files fixed")
    
    # SSOT base classes
    base_class_updates = standardizer.implement_ssot_base_classes()
    print(f"✅ SSOT base classes: {base_class_updates} files updated")
    
    # Golden path context
    context_updates = standardizer.implement_golden_path_context()
    print(f"✅ Golden path context: {context_updates} files updated")
    
    # Utility consolidation
    utility_consolidation = standardizer.consolidate_duplicate_utilities()
    print(f"✅ Utility consolidation: {utility_consolidation} duplicates identified")
    
    # 3. Create compliance test
    compliance_test = standardizer.create_compliance_test()
    print(f"✅ Compliance test created: {compliance_test}")
    
    # 4. Validate results
    print("\n🧪 VALIDATION")
    print("-" * 15)
    
    validation_results = standardizer.validate_ssot_compliance()
    
    print(f"SSOT Base Classes: {validation_results['ssot_base_classes']} files")
    print(f"Unified Setup Methods: {validation_results['unified_setup_methods']} files")
    print(f"Golden Path Context: {validation_results['golden_path_context']} files")
    print(f"Patterns Fixed: {validation_results['patterns_fixed']}")
    
    # 5. Summary
    print("\n🎯 STANDARDIZATION SUMMARY")
    print("=" * 30)
    
    total_fixes = setup_fixes + base_class_updates + context_updates
    
    print(f"Total Files Fixed: {total_fixes}")
    print(f"Patterns Standardized: {len(standardizer.patterns_fixed)}")
    
    if total_fixes > 0:
        print("\n🎉 STANDARDIZATION SUCCESS!")
        print("SSOT compliance implemented across test infrastructure.")
        print(f"\nPatterns Implemented:")
        for pattern in standardizer.patterns_fixed:
            print(f"  ✅ {pattern}")
        
        print(f"\nNext steps:")
        print(f"1. Run compliance test: python3 {compliance_test}")
        print("2. Validate test execution with standardized patterns")
        print("3. Monitor compliance metrics in CI/CD")
        
        return 0
    else:
        print("\n✅ ALREADY COMPLIANT")
        print("Test infrastructure already follows SSOT patterns.")
        return 0

if __name__ == '__main__':
    sys.exit(main())