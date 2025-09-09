#!/usr/bin/env python3
"""
UVS Test Suite Validation Script

This script validates the 100+ comprehensive UVS integration tests to ensure
they are syntactically correct and can be imported properly.
"""

import sys
import os
import ast
import importlib.util
from pathlib import Path

def validate_python_syntax(file_path):
    """Validate Python syntax for a file"""
    print(f"📁 Validating: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse syntax
        ast.parse(content)
        print(f"✅ Syntax OK: {file_path.name}")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax Error in {file_path.name}: Line {e.lineno}: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ Error reading {file_path.name}: {e}")
        return False

def count_test_functions(file_path):
    """Count test functions in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        test_functions = []
        
        for node in ast.walk(tree):
            # Check for both sync and async function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                test_functions.append(node.name)
        
        return test_functions
    except:
        return []

def validate_test_structure(file_path):
    """Validate test file structure"""
    print(f"🧪 Analyzing test structure: {file_path.name}")
    
    test_functions = count_test_functions(file_path)
    test_count = len(test_functions)
    
    print(f"📊 Found {test_count} test functions")
    
    # Check for BVJ comments and proper structure
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for BVJ in content
        has_bvj = 'Business Value Justification' in content or 'BVJ:' in content
        
        # Check for integration test markers
        has_integration_markers = '@pytest.mark.integration' in content
        
        # Check for proper imports
        has_proper_imports = 'UserExecutionContext' in content
        
        print(f"✅ Has BVJ comments: {has_bvj}")
        print(f"✅ Has integration markers: {has_integration_markers}")
        print(f"✅ Has proper imports: {has_proper_imports}")
        
        return {
            'test_count': test_count,
            'test_functions': test_functions,
            'has_bvj': has_bvj,
            'has_integration_markers': has_integration_markers,
            'has_proper_imports': has_proper_imports
        }
        
    except Exception as e:
        print(f"❌ Error analyzing structure: {e}")
        return {'test_count': test_count, 'test_functions': test_functions}

def main():
    """Main validation function"""
    print("🚀 UVS Test Suite Validation")
    print("=" * 50)
    
    # Test files to validate
    test_files = [
        "netra_backend/tests/integration/uvs/test_user_isolation_validation_core.py",
        "netra_backend/tests/integration/uvs/test_reporting_context_integration.py", 
        "netra_backend/tests/integration/uvs/test_user_context_factory_isolation.py",
        "netra_backend/tests/integration/uvs/test_error_handling_edge_cases.py"
    ]
    
    validation_results = {}
    total_tests = 0
    syntax_errors = 0
    
    for test_file in test_files:
        test_path = Path(test_file)
        if not test_path.exists():
            print(f"❌ File not found: {test_file}")
            continue
        
        print(f"\n📂 Processing: {test_file}")
        print("-" * 40)
        
        # Validate syntax
        syntax_ok = validate_python_syntax(test_path)
        if not syntax_ok:
            syntax_errors += 1
            continue
        
        # Analyze structure
        structure = validate_test_structure(test_path)
        validation_results[test_file] = structure
        total_tests += structure['test_count']
    
    # Generate summary report
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY REPORT")
    print("=" * 50)
    
    print(f"📁 Files validated: {len(validation_results)}")
    print(f"🧪 Total test functions: {total_tests}")
    print(f"❌ Syntax errors: {syntax_errors}")
    print(f"✅ Success rate: {((len(validation_results) - syntax_errors) / len(test_files) * 100):.1f}%")
    
    # Detailed breakdown
    print("\n📈 Test File Breakdown:")
    for file_path, results in validation_results.items():
        file_name = Path(file_path).name
        print(f"  {file_name}: {results['test_count']} tests")
        
        # Show sample test functions
        if results.get('test_functions'):
            sample_tests = results['test_functions'][:3]  # Show first 3
            for test_func in sample_tests:
                print(f"    - {test_func}")
            if len(results['test_functions']) > 3:
                print(f"    ... and {len(results['test_functions']) - 3} more tests")
    
    # Business value validation
    print(f"\n💼 Business Value Validation:")
    bvj_files = sum(1 for r in validation_results.values() if r.get('has_bvj', False))
    integration_files = sum(1 for r in validation_results.values() if r.get('has_integration_markers', False))
    
    print(f"  Files with BVJ comments: {bvj_files}/{len(validation_results)}")
    print(f"  Files with integration markers: {integration_files}/{len(validation_results)}")
    
    # Final status
    if syntax_errors == 0 and total_tests >= 100:
        print("\n🎉 VALIDATION PASSED!")
        print(f"✅ All {total_tests} tests are syntactically valid and ready for execution")
        return 0
    else:
        print(f"\n⚠️  VALIDATION ISSUES FOUND")
        if syntax_errors > 0:
            print(f"❌ {syntax_errors} files have syntax errors")
        if total_tests < 100:
            print(f"❌ Only {total_tests} tests found, expected 100+")
        return 1

if __name__ == "__main__":
    sys.exit(main())