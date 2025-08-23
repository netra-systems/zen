import ast
import re
from pathlib import Path

def fix_common_syntax_errors():
    """Fix common syntax errors systematically"""
    base_dir = Path('tests/e2e')
    fixed_count = 0
    
    for py_file in base_dir.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip if already valid
            try:
                ast.parse(content)
                continue
            except SyntaxError as original_error:
                pass
            
            print(f'Fixing: {py_file.name}')
            lines = content.split('\n')
            fixed_lines = []
            changes_made = []
            
            i = 0
            while i < len(lines):
                line = lines[i]
                original_line = line
                
                # Fix 1: Remove orphaned import lines
                stripped = line.strip()
                if (stripped and 
                    not stripped.startswith('from ') and 
                    not stripped.startswith('import ') and
                    not stripped.startswith('#') and
                    stripped.replace(',', '').strip() in [
                        'SECURE_WEBSOCKET_CONFIG', 'SecureWebSocketManager', 
                        'ConnectionManager', 'SupervisorAgent', 'AgentService'
                    ]):
                    changes_made.append(f'Removed orphaned import: {stripped}')
                    i += 1
                    continue
                
                # Fix 2: Close unclosed import parentheses
                if line.strip().endswith('import (') and i + 1 < len(lines):
                    # Look for the import items
                    j = i + 1
                    import_items = []
                    while j < len(lines) and not lines[j].strip().startswith(')'):
                        item_line = lines[j].strip()
                        if item_line and not item_line.startswith('#'):
                            if item_line.endswith(','):
                                import_items.append(item_line[:-1])  # Remove trailing comma
                            else:
                                import_items.append(item_line)
                        j += 1
                    
                    if import_items:
                        # Reconstruct the import with closing paren
                        fixed_lines.append(line)
                        for item in import_items:
                            fixed_lines.append(f'    {item}')
                        fixed_lines.append(')')
                        changes_made.append('Fixed unclosed import parentheses')
                        i = j + 1
                        continue
                
                # Fix 3: Add pass statements to empty classes/functions
                if (line.strip().startswith('class ') and line.strip().endswith(':')) or \
                   (line.strip().startswith('def ') and line.strip().endswith(':')) or \
                   (line.strip() in ['if ', 'else:', 'try:', 'except:', 'finally:']):
                    fixed_lines.append(line)
                    # Check if next line is properly indented
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if not next_line.startswith('    ') or next_line.strip().startswith('#'):
                            fixed_lines.append('    pass')
                            changes_made.append(f'Added pass statement after {line.strip()}')
                    else:
                        fixed_lines.append('    pass')
                        changes_made.append(f'Added pass statement after {line.strip()}')
                    i += 1
                    continue
                
                # Fix 4: Remove unexpected indentation
                if line.startswith('    ') and i > 0:
                    prev_line = lines[i-1].strip()
                    if (prev_line and 
                        not prev_line.endswith("\\") and 
                        not any(kw in prev_line for kw in ['def ', 'class ', 'if ', 'else', 'elif', 'for ', 'while ', 'try:', 'except', 'with '])):
                        fixed_lines.append(line.lstrip())
                        changes_made.append(f'Fixed unexpected indent: {line.strip()}')
                        i += 1
                        continue
                
                fixed_lines.append(line)
                i += 1
            
            # Try to parse the fixed content
            fixed_content = '\n'.join(fixed_lines)
            try:
                ast.parse(fixed_content)
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f'  ✓ Fixed successfully: {", ".join(changes_made)}')
                fixed_count += 1
            except SyntaxError as e:
                print(f'  ✗ Still has errors: {str(e)[:60]}...')
                
        except Exception as e:
            print(f'Error processing {py_file}: {e}')
    
    print(f'\nFixed {fixed_count} files successfully')
    return fixed_count

if __name__ == '__main__':
    fix_common_syntax_errors()
