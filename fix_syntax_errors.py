#!/usr/bin/env python3
"""
Fix common syntax errors in test files:
1. Double 'await' statements: await await -> await
2. Incorrect 'self.await' usage: self.await -> await
3. Invalid class definition syntax
4. Indentation errors
"""

import os
import re
import glob

def fix_file(filepath):
    """Fix syntax errors in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix 1: Double await statements
        content = re.sub(r'await\s+await\s+', 'await ', content)
        
        # Fix 2: self.await usage
        content = re.sub(r'self\.await\s+', 'await ', content)
        
        # Fix 3: Common pattern where awaitable is being used incorrectly
        # Look for patterns like: self.await redis_client.ping() -> await redis_client.ping()
        content = re.sub(r'(\s+)self\.await(\s+[a-zA-Z_][a-zA-Z0-9_]*\.)', r'\1await\2', content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed syntax errors in: {filepath}")
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Fix syntax errors in all Python test files"""
    
    # Get all Python files in test directories
    test_patterns = [
        "**/test_*.py",
        "**/tests/**/*.py",
        "**/test/**/*.py"
    ]
    
    fixed_files = []
    
    for pattern in test_patterns:
        files = glob.glob(pattern, recursive=True)
        for filepath in files:
            if fix_file(filepath):
                fixed_files.append(filepath)
    
    print(f"\nFixed {len(fixed_files)} files:")
    for filepath in fixed_files:
        print(f"  - {filepath}")
    
    # Test a few files to make sure they compile
    critical_files = [
        "./netra_backend/tests/integration/golden_path/test_golden_path_service_boundaries.py",
        "./tests/integration/golden_path/test_user_sessions_golden_path_validation.py", 
        "./tests/e2e/golden_path/test_complete_golden_path_business_value.py"
    ]
    
    print("\nTesting compilation of critical files...")
    for filepath in critical_files:
        if os.path.exists(filepath):
            os.system(f"python -m py_compile \"{filepath}\"")
            print(f"Tested: {filepath}")

if __name__ == "__main__":
    main()