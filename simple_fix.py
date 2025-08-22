import os
import ast
from pathlib import Path

def simple_syntax_fix():
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
            except SyntaxError:
                pass
            
            lines = content.split('\n')
            fixed_lines = []
            
            for line in lines:
                # Remove orphaned import lines
                stripped = line.strip()
                if (stripped and 
                    not stripped.startswith('from ') and 
                    not stripped.startswith('import ') and
                    stripped.replace(',', '').strip() in [
                        'SECURE_WEBSOCKET_CONFIG', 'SecureWebSocketManager', 'ConnectionManager'
                    ]):
                    continue
                
                fixed_lines.append(line)
            
            fixed_content = '\n'.join(fixed_lines)
            
            # Test and save if valid
            try:
                ast.parse(fixed_content)
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f'Fixed: {py_file.name}')
                fixed_count += 1
            except SyntaxError as e:
                print(f'Still broken {py_file.name}: {str(e)[:50]}')
                
        except Exception as e:
            print(f'Error with {py_file}: {e}')
    
    print(f'Fixed {fixed_count} files')

if __name__ == '__main__':
    simple_syntax_fix()
