#!/usr/bin/env python3
"""
Fix remaining syntax errors in specific e2e test files.
"""

import ast
import os
import sys

def fix_specific_files():
    """Fix the remaining syntax errors."""
    files_to_fix = [
        'tests/e2e/test_cors_dynamic_ports.py',
        'tests/e2e/test_performance_targets.py', 
        'tests/e2e/test_rapid_message_succession_agent.py',
        'tests/e2e/test_rapid_message_succession_api.py',
        'tests/e2e/test_rapid_message_succession_core.py',
        'tests/e2e/test_resource_limits.py',
        'tests/e2e/test_response_quality.py',
        'tests/e2e/test_spike_recovery_core.py',
        'tests/e2e/test_spike_recovery_performance.py'
    ]
    
    fixed_count = 0
    
    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
            
        print(f"\nProcessing {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check current syntax
            try:
                ast.parse(content)
                print(f"  Already valid: {file_path}")
                fixed_count += 1
                continue
            except SyntaxError as e:
                print(f"  Syntax error on line {e.lineno}: {e.msg}")
                
            # Apply manual fixes based on error patterns
            original_content = content
            
            # Fix missing closing parentheses/braces
            lines = content.split('\n')
            
            # Common patterns to fix
            for i, line in enumerate(lines):
                line_num = i + 1
                
                # Fix dictionary entries missing closing braces
                if ('benchmark_results[' in line or 'validation_result[' in line) and line.strip().endswith(','):
                    # Look ahead for closing brace
                    j = i + 1
                    while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith('}'):
                        j += 1
                    if j < len(lines) and not lines[j].strip().startswith('}'):
                        lines[i] = line.rstrip(',') + '}'
                
                # Fix function calls missing closing parentheses
                if 'await client.get(' in line and ')' not in line:
                    if i + 1 < len(lines) and ')' not in lines[i + 1]:
                        lines[i] = line + ')'
                        
                # Fix f-string issues and missing commas
                if line.strip().endswith('"') and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith(('}', ')', ']', ',', '#')):
                        lines[i] = line + ','
            
            content = '\n'.join(lines)
            
            # Check if fixes worked
            try:
                ast.parse(content)
                # Save the fixed file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  Fixed: {file_path}")
                fixed_count += 1
            except SyntaxError as e:
                print(f"  Still has errors after attempted fix: line {e.lineno}: {e.msg}")
                # Restore original
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
    
    print(f"\nSummary: Fixed {fixed_count}/{len(files_to_fix)} files")
    return fixed_count == len(files_to_fix)

if __name__ == "__main__":
    success = fix_specific_files()
    
    # Final validation
    print("\nFinal validation...")
    error_count = 0
    for root, dirs, files in os.walk('tests/e2e'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError:
                    error_count += 1
    
    print(f"Remaining files with syntax errors: {error_count}")
    sys.exit(0 if error_count == 0 else 1)