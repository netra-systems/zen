#!/usr/bin/env python3
"""
Enhanced Mission Critical Base Class Migration Script
Converts various test base classes to SSOT base class pattern
"""
import os
import re
from pathlib import Path

def convert_file_to_ssot(file_path):
    """Convert a single test file to SSOT base class pattern."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Skip files that already have SSOT imports and classes
        if 'SSotBaseTestCase' in content or 'SSotAsyncTestCase' in content:
            return False
        
        # 1. Add SSOT imports if not present
        if 'from test_framework.ssot.base_test_case import' not in content:
            # Find the import section and add SSOT import
            import_match = re.search(r'^(import .*\n|from .*\n)+', content, re.MULTILINE)
            if import_match:
                import_end = import_match.end()
                ssot_import = "from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase\n"
                content = content[:import_end] + ssot_import + content[import_end:]
                changes_made.append("Added SSOT imports")
        
        # 2. Convert different base class types to SSOT
        base_class_mappings = {
            r'\(BaseTestCase\)': '(SSotBaseTestCase)',
            r'\(BaseIntegrationTest\)': '(SSotBaseTestCase)', 
            r'\(BaseE2ETest\)': '(SSotBaseTestCase)',
            r'\(IsolatedTestCase\)': '(SSotBaseTestCase)',
            r'\(IntegrationTestCase\)': '(SSotBaseTestCase)',
            r'\(TestCase\)': '(SSotBaseTestCase)',
            r'\(BaseMissionCriticalTest\)': '(SSotBaseTestCase)',
            r'\(AsyncBaseTestCase\)': '(SSotAsyncTestCase)',
        }
        
        for old_pattern, new_class in base_class_mappings.items():
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_class, content)
                changes_made.append(f"Changed {old_pattern[2:-2]} to {new_class[1:-1]}")
        
        # 3. Update method names for SSOT compatibility
        method_mappings = {
            r'def setUpClass\(': 'def setup_class(',
            r'def tearDownClass\(': 'def teardown_class(',
            r'def setUp\(self\):': 'def setup_method(self, method):',
            r'def tearDown\(self\):': 'def teardown_method(self, method):',
        }
        
        for old_method, new_method in method_mappings.items():
            if re.search(old_method, content):
                content = re.sub(old_method, new_method, content)
                changes_made.append(f"Updated method: {old_method} -> {new_method}")
        
        # Write the updated content if changes were made
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Converted {file_path}")
            for change in changes_made:
                print(f"   - {change}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main migration execution."""
    mission_critical_dir = Path("/Users/anthony/Desktop/netra-apex/tests/mission_critical")
    
    # Get all Python test files that need conversion
    test_files = []
    
    # Find files with non-SSOT base classes
    for test_file in mission_critical_dir.glob("test_*.py"):
        try:
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Skip if already has SSOT base classes
            if 'SSotBaseTestCase' in content or 'SSotAsyncTestCase' in content:
                continue
                
            # Check if has base classes that need conversion
            base_class_patterns = [
                r'BaseTestCase', r'BaseIntegrationTest', r'BaseE2ETest',
                r'IsolatedTestCase', r'IntegrationTestCase', r'TestCase\)',
                r'BaseMissionCriticalTest', r'AsyncBaseTestCase'
            ]
            
            if any(re.search(pattern, content) for pattern in base_class_patterns):
                test_files.append(test_file)
                
        except Exception as e:
            print(f"Warning: Could not read {test_file}: {e}")
    
    print(f"Found {len(test_files)} files needing base class conversion")
    
    converted_count = 0
    
    for test_file in test_files:
        if convert_file_to_ssot(test_file):
            converted_count += 1
    
    print(f"\n📊 Enhanced Migration Summary:")
    print(f"   - Files needing conversion: {len(test_files)}")
    print(f"   - Files converted: {converted_count}")
    print(f"   - Files unchanged: {len(test_files) - converted_count}")

if __name__ == "__main__":
    main()