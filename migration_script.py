#!/usr/bin/env python3
"""
Mission Critical Base Class Migration Script
Converts unittest.TestCase to SSotBaseTestCase systematically
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
        
        # 1. Replace unittest import with SSOT import
        if 'import unittest' in content and 'from test_framework.ssot.base_test_case import' not in content:
            content = re.sub(
                r'^import unittest$',
                '# SSOT Base Test Case Import\nfrom test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase',
                content,
                flags=re.MULTILINE
            )
            changes_made.append("Added SSOT imports")
        
        # 2. Replace unittest.TestCase with SSotBaseTestCase
        if 'unittest.TestCase' in content:
            content = re.sub(r'\(unittest\.TestCase\)', '(SSotBaseTestCase)', content)
            changes_made.append("Changed unittest.TestCase to SSotBaseTestCase")
        
        # 3. Replace unittest.IsolatedAsyncioTestCase with SSotAsyncTestCase
        if 'unittest.IsolatedAsyncioTestCase' in content:
            content = re.sub(r'\(unittest\.IsolatedAsyncioTestCase\)', '(SSotAsyncTestCase)', content)
            changes_made.append("Changed unittest.IsolatedAsyncioTestCase to SSotAsyncTestCase")
        
        # 4. Replace setUpClass with setup_class
        content = re.sub(r'def setUpClass\(', 'def setup_class(', content)
        if 'setup_class' in content and 'setUpClass' not in original_content:
            changes_made.append("Changed setUpClass to setup_class")
        
        # 5. Replace tearDownClass with teardown_class  
        content = re.sub(r'def tearDownClass\(', 'def teardown_class(', content)
        if 'teardown_class' in content and 'tearDownClass' not in original_content:
            changes_made.append("Changed tearDownClass to teardown_class")
        
        # 6. Replace setUp with setup_method
        content = re.sub(r'def setUp\(self\):', 'def setup_method(self, method):', content)
        if 'setup_method' in content and 'setUp' not in original_content:
            changes_made.append("Changed setUp to setup_method")
        
        # 7. Replace tearDown with teardown_method
        content = re.sub(r'def tearDown\(self\):', 'def teardown_method(self, method):', content)
        if 'teardown_method' in content and 'tearDown' not in original_content:
            changes_made.append("Changed tearDown to teardown_method")
        
        # Write the updated content if changes were made
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Converted {file_path}")
            for change in changes_made:
                print(f"   - {change}")
            return True
        else:
            print(f"⏸️  No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main migration execution."""
    mission_critical_dir = Path("/Users/anthony/Desktop/netra-apex/tests/mission_critical")
    
    # Get all Python test files
    test_files = list(mission_critical_dir.glob("test_*.py"))
    print(f"Found {len(test_files)} test files")
    
    converted_count = 0
    
    for test_file in test_files:
        if convert_file_to_ssot(test_file):
            converted_count += 1
    
    print(f"\n📊 Migration Summary:")
    print(f"   - Total files processed: {len(test_files)}")
    print(f"   - Files converted: {converted_count}")
    print(f"   - Files unchanged: {len(test_files) - converted_count}")

if __name__ == "__main__":
    main()