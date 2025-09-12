#!/usr/bin/env python3
"""Find ALL import errors in the test suite systematically."""

import subprocess
import sys
from pathlib import Path
import json

def run_pytest_collect(test_dir: Path) -> list:
    """Run pytest --collect-only to find import errors."""
    cmd = [
        sys.executable, '-m', 'pytest',
        str(test_dir),
        '--collect-only',
        '--tb=short',
        '-q'
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(test_dir.parent) if test_dir.name == 'tests' else str(test_dir.parent.parent)
    )
    
    errors = []
    lines = result.stdout.split('\n') + result.stderr.split('\n')
    
    for i, line in enumerate(lines):
        if 'ModuleNotFoundError' in line or 'ImportError' in line:
            # Get context around the error
            error_context = {
                'error': line,
                'file': '',
                'module': ''
            }
            
            # Look for the file path
            for j in range(max(0, i-5), min(len(lines), i+5)):
                if 'importing test module' in lines[j]:
                    error_context['file'] = lines[j].split("'")[1] if "'" in lines[j] else lines[j]
                if 'No module named' in lines[j]:
                    error_context['module'] = lines[j].split("'")[1] if "'" in lines[j] else lines[j]
            
            if error_context['module']:
                errors.append(error_context)
    
    return errors

def main():
    """Main execution."""
    root_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1')
    
    test_dirs = [
        root_dir / 'netra_backend' / 'tests',
        root_dir / 'tests',
        root_dir / 'auth_service' / 'tests',
    ]
    
    all_errors = []
    
    print("Scanning for import errors...")
    print("=" * 60)
    
    for test_dir in test_dirs:
        if test_dir.exists():
            print(f"\nChecking: {test_dir}")
            errors = run_pytest_collect(test_dir)
            if errors:
                print(f"  Found {len(errors)} import errors")
                all_errors.extend(errors)
            else:
                print(f"  No import errors found")
    
    if all_errors:
        print("\n" + "=" * 60)
        print("SUMMARY OF ALL IMPORT ERRORS:")
        print("=" * 60)
        
        # Group by module
        module_errors = {}
        for error in all_errors:
            module = error['module']
            if module:
                if module not in module_errors:
                    module_errors[module] = []
                module_errors[module].append(error['file'])
        
        for module, files in module_errors.items():
            print(f"\nMissing module: {module}")
            print(f"  Required by {len(files)} file(s):")
            for file in files[:3]:  # Show first 3 files
                if file:
                    file_path = Path(file)
                    print(f"    - {file_path.name if file_path.exists() else file}")
            if len(files) > 3:
                print(f"    ... and {len(files) - 3} more")
        
        # Save to file for further processing
        output_file = root_dir / 'import_errors.json'
        with open(output_file, 'w') as f:
            json.dump(module_errors, f, indent=2)
        print(f"\nDetailed report saved to: {output_file}")
    else:
        print("\n[U+2713] No import errors found!")
    
    return 0

if __name__ == "__main__":
    exit(main())