#!/usr/bin/env python3
"""
Fix syntax errors in updated test files.
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class SyntaxFixer:
    """Fix common syntax errors in Python test files."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.files_fixed = 0
        self.total_errors = 0
        self.error_report = []
        
    def find_test_files(self) -> List[Path]:
        """Find all Python test files."""
        test_files = []
        for root, dirs, files in os.walk(self.root_dir):
            # Skip virtual environments
            if '.venv' in root or '__pycache__' in root:
                continue
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(Path(root) / file)
        return test_files
    
    def check_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Check if a file has syntax errors."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                compile(content, str(file_path), 'exec')
            return True, ""
        except SyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def fix_common_syntax_errors(self, content: str) -> str:
        """Fix common syntax errors."""
        
        # Fix escaped characters
        content = re.sub(r'\\n', '\n', content)
        content = re.sub(r'\\"', '"', content)
        
        # Fix empty fixture bodies
        content = re.sub(
            r'(@pytest\.fixture.*?\n\s*def\s+\w+\([^)]*\):\s*\n)(\s*"""[^"]*"""\s*\n)?(\s*# TODO:.*?\n)?$',
            r'\1\2\3    return None\n',
            content,
            flags=re.MULTILINE
        )
        
        # Fix functions with only TODO comments (no body)
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if this is a function definition
            if re.match(r'^(async\s+)?def\s+\w+\([^)]*\):\s*$', line.strip()):
                new_lines.append(line)
                i += 1
                # Check if next line is docstring
                if i < len(lines) and '"""' in lines[i]:
                    new_lines.append(lines[i])
                    i += 1
                    # Find end of docstring
                    while i < len(lines) and not lines[i].strip().endswith('"""'):
                        new_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        new_lines.append(lines[i])
                        i += 1
                
                # Check if next line is a TODO comment
                if i < len(lines) and '# TODO' in lines[i]:
                    new_lines.append(lines[i])
                    i += 1
                
                # Check if we need to add a body
                if i >= len(lines) or (i < len(lines) and not lines[i].strip().startswith(' ') and lines[i].strip() != ''):
                    # No body found, add pass statement
                    new_lines.append('    pass')
            else:
                new_lines.append(line)
                i += 1
        
        content = '\n'.join(new_lines)
        
        # Fix duplicate websocket assignments
        lines = content.split('\n')
        fixed_lines = []
        prev_line = ''
        
        for line in lines:
            # Skip duplicate websocket assignments
            if 'websocket = TestWebSocketConnection()' in line and 'websocket = TestWebSocketConnection()' in prev_line:
                continue
            # Fix websocket.websocket patterns
            line = re.sub(r'websocket\.websocket = TestWebSocketConnection\(\)', '# websocket setup complete', line)
            fixed_lines.append(line)
            prev_line = line
        
        content = '\n'.join(fixed_lines)
        
        # Fix variable naming issues
        content = re.sub(r'user1_websocket\.websocket', 'user1_websocket', content)
        content = re.sub(r'user2_websocket\.websocket', 'user2_websocket', content)
        content = re.sub(r'legitimate_websocket\.websocket', 'legitimate_websocket', content)
        content = re.sub(r'malicious_websocket\.websocket', 'malicious_websocket', content)
        
        # Fix async functions without await
        content = re.sub(
            r'(async\s+def\s+\w+\([^)]*\):.*?)(return\s+)',
            r'\1await asyncio.sleep(0)\n    \2',
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        
        # Ensure asyncio is imported if async functions exist
        if 'async def' in content and 'import asyncio' not in content:
            lines = content.split('\n')
            import_index = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_index = i + 1
            lines.insert(import_index, 'import asyncio')
            content = '\n'.join(lines)
        
        # Fix incomplete class definitions
        content = re.sub(
            r'(class\s+\w+.*?:\s*\n)(\s*"""[^"]*"""\s*\n)?$',
            r'\1\2    pass\n',
            content,
            flags=re.MULTILINE
        )
        
        # Fix invalid indentation (tabs to spaces)
        content = content.replace('\t', '    ')
        
        # Fix trailing commas in function definitions
        content = re.sub(r',\s*\)', ')', content)
        
        # Fix missing colons after function definitions
        content = re.sub(r'(def\s+\w+\([^)]*\))(\s*\n)', r'\1:\2', content)
        
        # Fix incorrect websocket parameter syntax
        content = re.sub(r'websocket = TestWebSocketConnection\(\),', 'websocket=TestWebSocketConnection(),', content)
        
        return content
    
    def fix_file(self, file_path: Path) -> bool:
        """Fix syntax errors in a single file."""
        try:
            # First check if file has syntax errors
            valid, error = self.check_syntax(file_path)
            if valid:
                return False
            
            logger.info(f"Fixing syntax in {file_path.relative_to(self.root_dir)}")
            self.total_errors += 1
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply fixes
            fixed_content = self.fix_common_syntax_errors(content)
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            # Check if fixed
            valid, error = self.check_syntax(file_path)
            if valid:
                self.files_fixed += 1
                logger.info(f"  ✓ Fixed successfully")
                return True
            else:
                logger.warning(f"  ✗ Still has errors: {error}")
                self.error_report.append((str(file_path.relative_to(self.root_dir)), error))
                return False
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.error_report.append((str(file_path.relative_to(self.root_dir)), str(e)))
            return False
    
    def run(self):
        """Run the syntax fixing process."""
        logger.info("Starting syntax error fixing...")
        
        test_files = self.find_test_files()
        logger.info(f"Checking {len(test_files)} test files for syntax errors...")
        
        for file_path in test_files:
            self.fix_file(file_path)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info(f"Syntax Fix Complete")
        logger.info(f"Total files with errors: {self.total_errors}")
        logger.info(f"Files fixed: {self.files_fixed}")
        logger.info(f"Files still with errors: {len(self.error_report)}")
        
        if self.error_report:
            logger.error("\nFiles still needing manual fixes:")
            for file, error in self.error_report[:10]:
                logger.error(f"  - {file}: {error.split(':', 1)[0] if ':' in error else error}")
            if len(self.error_report) > 10:
                logger.error(f"  ... and {len(self.error_report) - 10} more files")
        
        self.create_report()
    
    def create_report(self):
        """Create a detailed report."""
        report_path = self.root_dir / "SYNTAX_FIX_REPORT.md"
        
        report = f"""# Syntax Fix Report

## Summary
- **Files with errors**: {self.total_errors}
- **Files fixed**: {self.files_fixed}
- **Files still with errors**: {len(self.error_report)}
- **Success rate**: {(self.files_fixed / self.total_errors * 100 if self.total_errors > 0 else 0):.1f}%

## Fixes Applied
1. Fixed escaped characters (\\n, \\")
2. Added missing function bodies (pass statements)
3. Fixed empty fixtures
4. Fixed duplicate websocket assignments
5. Fixed websocket.websocket patterns
6. Added missing colons after function definitions
7. Fixed indentation issues (tabs to spaces)
8. Added asyncio imports for async functions
9. Fixed trailing commas in function signatures

## Files Still Needing Manual Fixes
"""
        
        if self.error_report:
            for file, error in self.error_report:
                report += f"- `{file}`: {error}\n"
        else:
            report += "None - all syntax errors were fixed automatically!\n"
        
        report += """
## Next Steps
1. Review files that still have errors
2. Run tests: `python tests/unified_test_runner.py --real-services`
3. Fix any runtime errors
"""
        
        report_path.write_text(report)
        logger.info(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    fixer = SyntaxFixer()
    fixer.run()