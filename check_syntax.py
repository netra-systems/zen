import os
import ast
import sys
from pathlib import Path

def check_syntax(filepath):
    """Check if a Python file has syntax errors."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        return None
    except SyntaxError as e:
        return f"{filepath}:{e.lineno}: {e.msg}"
    except Exception as e:
        return f"{filepath}: {str(e)}"

def main():
    test_dirs = [
        'netra_backend/tests',
        'auth_service/tests',
        'frontend/__tests__',
        'tests'
    ]
    
    errors = []
    total_files = 0
    
    for test_dir in test_dirs:
        if not os.path.exists(test_dir):
            continue
            
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    total_files += 1
                    error = check_syntax(filepath)
                    if error:
                        errors.append(error)
    
    print(f"Checked {total_files} Python test files")
    print(f"Found {len(errors)} files with syntax errors\n")
    
    if errors:
        print("Syntax errors found:")
        for error in errors[:50]:  # Show first 50 errors
            print(error)
        
        if len(errors) > 50:
            print(f"\n... and {len(errors) - 50} more errors")
    
    return len(errors)

if __name__ == "__main__":
    sys.exit(main())
