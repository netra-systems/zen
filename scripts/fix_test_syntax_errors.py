#!/usr/bin/env python
"""
PHASE 4: Fix remaining critical test syntax errors blocking Golden Path execution

This script fixes common syntax error patterns in test files:
1. Dollar signs in ARR mentions
2. Unterminated strings
3. Mismatched parentheses in imports
4. Invalid decimal literals
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

class TestSyntaxFixer:
    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        self.error_patterns = [
            # Pattern 1: Fix mismatched parentheses in imports
            {
                'pattern': r'__import__\(([^,]+),\s*fromlist=\[([^]]*)\)\s*if\s+([^)]+)\s+else\s+\[\)',
                'replacement': r'__import__(\1, fromlist=[\2] if \3 else [])',
                'description': 'Fix mismatched parentheses in conditional fromlist imports'
            },
            {
                'pattern': r'fromlist=\[([^]]*)\)\s*if\s+([^)]+)\s+else\s+\[\)',
                'replacement': r'fromlist=[\1] if \2 else [])',
                'description': 'Fix mismatched parentheses in fromlist conditions'
            },
            # Pattern 2: Fix dollar signs in ARR mentions
            {
                'pattern': r'\$(\d+K\+\s+(?:plus\s+)?ARR)',
                'replacement': r'\1',
                'description': 'Remove dollar signs from ARR business value mentions'
            },
            # Pattern 3: Fix unterminated strings
            {
                'pattern': r'"([^"]*WebSocket[^"]*)\)"([^"]*)',
                'replacement': r'"\1)"',
                'description': 'Fix unterminated strings with WebSocket mentions'
            },
            {
                'pattern': r'f"([^"]*Warning:[^"]*{[^}]*}[^"]*)"([^"]*)',
                'replacement': r'f"\1"',
                'description': 'Fix unterminated f-strings with warnings'
            },
            # Pattern 4: Fix invalid decimal literals with ARR
            {
                'pattern': r'(\d+K\+\s+)plus(\s+ARR)',
                'replacement': r'\1\2',
                'description': 'Fix invalid decimal literal patterns with "plus" in ARR mentions'
            },
            # Pattern 5: Fix multiline string terminators
            {
                'pattern': r"'''([^']*Business Value:[^']*ARR[^']*)",
                'replacement': r'"""\1"""',
                'description': 'Fix multiline string terminators for business value descriptions'
            },
            # Pattern 6: Fix print statements with missing quotes
            {
                'pattern': r'print\(f"([^"]*Warning:[^"]*{[^}]*}:[^"]*)"([^"]*)\)',
                'replacement': r'print(f"\1")',
                'description': 'Fix print statements with missing quote terminators'
            }
        ]

    def fix_file_content(self, content: str, file_path: str) -> Tuple[str, int]:
        """Fix syntax errors in file content and return fixed content with count of fixes"""
        fixed_content = content
        local_fixes = 0

        for pattern_info in self.error_patterns:
            pattern = pattern_info['pattern']
            replacement = pattern_info['replacement']
            description = pattern_info['description']

            matches = re.findall(pattern, fixed_content)
            if matches:
                print(f"  Applying fix: {description}")
                print(f"    Found {len(matches)} matches")
                fixed_content = re.sub(pattern, replacement, fixed_content)
                local_fixes += len(matches)

        return fixed_content, local_fixes

    def process_file(self, file_path: Path) -> bool:
        """Process a single file and fix syntax errors"""
        try:
            print(f"\nProcessing: {file_path}")

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Apply fixes
            fixed_content, local_fixes = self.fix_file_content(original_content, str(file_path))

            # Write back if changes were made
            if local_fixes > 0:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                print(f"  Applied {local_fixes} fixes to {file_path.name}")
                self.fixes_applied += local_fixes
                return True
            else:
                print(f"  No fixes needed for {file_path.name}")
                return False

        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
            return False

    def find_files_to_fix(self) -> List[Path]:
        """Find test files that likely need syntax fixes"""
        base_path = Path("C:\\netra-apex")

        # Priority patterns for files to check
        patterns = [
            "**/test_*golden*.py",
            "**/test_websocket_*.py",
            "**/test_*factory*.py",
            "tests/e2e/**/*.py",
            "tests/mission_critical/**/*.py"
        ]

        files_to_check = set()

        for pattern in patterns:
            for file_path in base_path.glob(pattern):
                # Skip backup directories
                if "backups" not in str(file_path):
                    files_to_check.add(file_path)

        return sorted(list(files_to_check))

    def run_syntax_fixes(self) -> Dict[str, int]:
        """Run syntax fixes on all relevant test files"""
        print("PHASE 4: Fixing critical test syntax errors...")
        print("=" * 60)

        files_to_fix = self.find_files_to_fix()
        print(f"Found {len(files_to_fix)} files to check for syntax errors")

        fixed_files = []

        for file_path in files_to_fix:
            self.files_processed += 1
            if self.process_file(file_path):
                fixed_files.append(file_path)

        print("\n" + "=" * 60)
        print(f"PHASE 4 COMPLETE:")
        print(f"   Files processed: {self.files_processed}")
        print(f"   Files fixed: {len(fixed_files)}")
        print(f"   Total fixes applied: {self.fixes_applied}")

        if fixed_files:
            print(f"\nFiles that were fixed:")
            for file_path in fixed_files[:10]:  # Show first 10
                print(f"   - {file_path.name}")
            if len(fixed_files) > 10:
                print(f"   ... and {len(fixed_files) - 10} more files")

        return {
            'files_processed': self.files_processed,
            'files_fixed': len(fixed_files),
            'fixes_applied': self.fixes_applied,
            'fixed_files': [str(f) for f in fixed_files]
        }

def main():
    """Main execution function"""
    fixer = TestSyntaxFixer()
    results = fixer.run_syntax_fixes()

    # Return results for validation
    return results

if __name__ == "__main__":
    results = main()
    print(f"\nReady for validation - {results['fixes_applied']} syntax errors fixed")