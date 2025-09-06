#!/usr/bin/env python3
"""
Final Syntax Repair Script - Handles the most stubborn patterns
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict

class FinalSyntaxRepair:
    def __init__(self):
        self.repaired_files = 0
        self.skipped_files = 0
        self.error_files = 0
        
    def repair_file(self, file_path: str) -> bool:
        """Repair syntax errors in a single file."""
        try:
            # Read with error handling for problematic encodings
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                except:
                    print(f"ENCODING_ERROR: Could not read {file_path}")
                    self.error_files += 1
                    return False
            
            original_content = content
            
            # Remove or replace problematic Unicode characters
            content = self.fix_unicode_issues(content)
            
            # Fix the most common patterns we observed
            content = self.fix_common_patterns(content)
            
            # Validate and write if changed
            if content != original_content:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"REPAIRED: {os.path.relpath(file_path)}")
                    self.repaired_files += 1
                    return True
                except Exception as e:
                    print(f"WRITE_ERROR: {file_path} - {e}")
                    self.error_files += 1
                    return False
            else:
                self.skipped_files += 1
                return True
                
        except Exception as e:
            print(f"PROCESS_ERROR: {file_path} - {e}")
            self.error_files += 1
            return False
    
    def fix_unicode_issues(self, content: str) -> str:
        """Fix Unicode character issues."""
        # Replace problematic Unicode characters with safe equivalents
        replacements = {
            '\u2192': '->',  # Right arrow
            '\u2264': '<=',  # Less than or equal
            '\u2265': '>=',  # Greater than or equal  
            '\U0001f534': '',  # Red circle emoji
            '\u2705': '',  # Check mark emoji
        }
        
        for unicode_char, replacement in replacements.items():
            content = content.replace(unicode_char, replacement)
            
        return content
    
    def fix_common_patterns(self, content: str) -> str:
        """Fix the most common syntax error patterns."""
        
        # 1. Fix leading zeros in decimal literals (invalid decimal literal)
        content = re.sub(r'\b0+(\d+)', r'\1', content)
        
        # 2. Fix unterminated string literals - simple case
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Simple unterminated string fix - if line ends with odd number of quotes
            if line.count('"') % 2 != 0 and not line.strip().startswith('#'):
                # Check if it's not already a complete string
                if line.strip() and not line.strip().endswith('"""') and '"""' not in line:
                    line = line + '"'
            
            # Fix triple quotes
            if '"""' in line and line.count('"""') % 2 != 0:
                if not line.strip().endswith('"""'):
                    line = line + '"""'
            
            fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        # 3. Fix f-string bracket mismatches - simple pattern
        content = re.sub(r'f"([^"]*?)\{([^}]*?)\]([^"]*?)"', r'f"\1{\2}\3"', content)
        content = re.sub(r"f'([^']*?)\{([^}]*?)\]([^']*?)'", r"f'\1{\2}\3'", content)
        
        # 4. Fix dictionary bracket mismatches
        content = re.sub(r'\{([^}]*?)\]', r'{\1}', content)
        
        # 5. Fix simple indentation issues
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # If line ends with colon and next line is not indented properly
            if (line.strip().endswith(':') and 
                i + 1 < len(lines) and 
                lines[i + 1].strip() and
                not lines[i + 1].startswith('    ')):
                
                fixed_lines.append(line)
                # Add proper indentation to next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip():
                        lines[i + 1] = '    ' + next_line.lstrip()
            else:
                fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        # 6. Fix basic import issues
        if 'from unittest.mock import' not in content and ('Mock(' in content or 'AsyncMock(' in content):
            # Add missing import at the top
            lines = content.split('\n')
            import_line = 'from unittest.mock import Mock, patch, MagicMock, AsyncMock'
            
            # Find where to insert the import
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#') and not line.startswith('"""'):
                    insert_pos = i
                    break
            
            lines.insert(insert_pos, import_line)
            content = '\n'.join(lines)
        
        return content
    
    def process_directories(self, directories: List[str]):
        """Process all test files in the specified directories."""
        print("Final Syntax Repair Script")
        print("=" * 40)
        print("Targeting:")
        print("- Unicode character issues")
        print("- Leading zeros in decimals")
        print("- Unterminated strings")
        print("- F-string bracket mismatches")
        print("- Dictionary bracket issues")
        print("- Basic indentation problems")
        print("- Missing imports")
        print()
        
        for directory in directories:
            if not os.path.exists(directory):
                print(f"Directory not found: {directory}")
                continue
                
            print(f"Processing: {directory}")
            
            # Find all test files
            test_files = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.py') and file.startswith('test_'):
                        test_files.append(os.path.join(root, file))
            
            print(f"Found {len(test_files)} test files")
            
            for file_path in test_files[:20]:  # Process first 20 files to test
                self.repair_file(file_path)
    
    def print_summary(self):
        """Print repair summary."""
        print("\n" + "=" * 40)
        print("REPAIR SUMMARY")
        print("=" * 40)
        print(f"Repaired files: {self.repaired_files}")
        print(f"Skipped files: {self.skipped_files}")
        print(f"Error files: {self.error_files}")
        print(f"Total processed: {self.repaired_files + self.skipped_files + self.error_files}")

def main():
    """Main execution function."""
    repair = FinalSyntaxRepair()
    
    # Focus on the most critical directories
    directories = [
        "netra_backend/tests/critical",
        "netra_backend/tests/agents",
        "netra_backend/tests/e2e",
        "netra_backend/tests/integration"
    ]
    
    repair.process_directories(directories)
    repair.print_summary()

if __name__ == "__main__":
    main()