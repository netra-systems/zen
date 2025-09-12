#!/usr/bin/env python3
"""
Migration script to update hardcoded test IDs to SSOT-compliant format.

This script scans the codebase for hardcoded test IDs and provides
automated migration to valid ID formats using the IDManager.
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Set

# Add parent directory to path to import UnifiedIDManager
sys.path.insert(0, str(Path(__file__).parent.parent))

from netra_backend.app.core.unified_id_manager import UnifiedIDManager


class TestIDMigrator:
    """Migrate hardcoded test IDs to SSOT-compliant format."""
    
    # Common invalid ID patterns found in tests
    INVALID_PATTERNS = [
        (re.compile(r'run_id\s*=\s*["\']test-run["\']'), 'test-run'),
        (re.compile(r'run_id\s*=\s*["\']test_run["\']'), 'test_run'),
        (re.compile(r'run_id\s*=\s*["\']test_run_\d+["\']'), 'test_run_NUM'),
        (re.compile(r'run_id\s*=\s*["\']run-[\w-]+["\']'), 'run-HYPHENATED'),
        (re.compile(r'["\']run_id["\']\s*:\s*["\']test-run["\']'), 'test-run (dict)'),
        (re.compile(r'thread_id\s*=\s*["\']thread_\d+["\']'), 'thread_NUM'),
    ]
    
    def __init__(self, dry_run: bool = True):
        """
        Initialize the migrator.
        
        Args:
            dry_run: If True, only report changes without modifying files
        """
        self.dry_run = dry_run
        self.violations_found: List[Tuple[str, int, str, str]] = []
        self.files_scanned = 0
        self.files_with_violations = 0
        
    def scan_file(self, filepath: Path) -> List[Tuple[int, str, str]]:
        """
        Scan a file for invalid ID patterns.
        
        Args:
            filepath: Path to the file to scan
            
        Returns:
            List of (line_number, original_text, violation_type)
        """
        violations = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                for pattern, violation_type in self.INVALID_PATTERNS:
                    if pattern.search(line):
                        violations.append((line_num, line.strip(), violation_type))
                        
        except Exception as e:
            print(f"Error scanning {filepath}: {e}")
            
        return violations
    
    def generate_replacement(self, original: str) -> str:
        """
        Generate a valid replacement for an invalid ID.
        
        Args:
            original: The original invalid ID string
            
        Returns:
            Valid replacement string
        """
        # Extract the context to determine appropriate thread_id
        if 'test-run' in original or 'test_run' in original:
            thread_id = "test_thread"
        elif 'integration' in original.lower():
            thread_id = "integration_test"
        elif 'e2e' in original.lower():
            thread_id = "e2e_test"
        elif 'websocket' in original.lower():
            thread_id = "websocket_test"
        elif 'agent' in original.lower():
            thread_id = "agent_test"
        else:
            # Try to extract a meaningful thread_id from the original
            match = re.search(r'["\']([^"\']+)["\']', original)
            if match:
                old_id = match.group(1)
                # Clean up the old ID to make a valid thread_id
                thread_id = old_id.replace('-', '_').replace('run_', '')
                if not thread_id or not UnifiedIDManager.validate_thread_id(thread_id):
                    thread_id = "migrated_test"
            else:
                thread_id = "migrated_test"
        
        # Generate valid run_id
        valid_run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Replace in the original string
        if 'run_id' in original:
            # Find the quoted value and replace it
            return re.sub(r'(["\'])[^"\']+(["\'])', f'\\1{valid_run_id}\\2', original)
        else:
            return original
    
    def migrate_file(self, filepath: Path) -> bool:
        """
        Migrate invalid IDs in a file.
        
        Args:
            filepath: Path to the file to migrate
            
        Returns:
            True if file was modified, False otherwise
        """
        violations = self.scan_file(filepath)
        
        if not violations:
            return False
        
        print(f"\n{'[DRY RUN] ' if self.dry_run else ''}Processing: {filepath}")
        print(f"  Found {len(violations)} violations")
        
        if not self.dry_run:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            modified = False
            for line_num, original, violation_type in violations:
                idx = line_num - 1
                old_line = lines[idx]
                new_line = self.generate_replacement(old_line)
                
                if old_line != new_line:
                    lines[idx] = new_line
                    modified = True
                    print(f"  Line {line_num}: Fixed {violation_type}")
            
            if modified:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"  [U+2713] File updated")
        else:
            for line_num, original, violation_type in violations:
                print(f"  Line {line_num}: {violation_type}")
                print(f"    Current: {original[:80]}...")
                replacement = self.generate_replacement(original)
                print(f"    Suggested: {replacement[:80]}...")
        
        return True
    
    def scan_directory(self, directory: Path, extensions: Set[str] = {'.py'}) -> None:
        """
        Scan a directory recursively for files with invalid IDs.
        
        Args:
            directory: Directory to scan
            extensions: File extensions to check
        """
        for root, dirs, files in os.walk(directory):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'node_modules', '.pytest_cache',
                'venv', '.venv', 'env', '.env'
            }]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    filepath = Path(root) / file
                    self.files_scanned += 1
                    
                    if self.migrate_file(filepath):
                        self.files_with_violations += 1
    
    def generate_report(self) -> str:
        """
        Generate a summary report.
        
        Returns:
            Report string
        """
        report = []
        report.append("\n" + "="*60)
        report.append("ID Migration Report")
        report.append("="*60)
        report.append(f"Mode: {'DRY RUN' if self.dry_run else 'MIGRATION'}")
        report.append(f"Files scanned: {self.files_scanned}")
        report.append(f"Files with violations: {self.files_with_violations}")
        
        if self.dry_run and self.files_with_violations > 0:
            report.append("\nTo apply these changes, run:")
            report.append("  python scripts/migrate_test_ids.py --apply")
        
        return "\n".join(report)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate hardcoded test IDs to SSOT-compliant format"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry run)"
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to scan (default: current directory)"
    )
    parser.add_argument(
        "--extensions",
        type=str,
        default=".py",
        help="Comma-separated file extensions to scan (default: .py)"
    )
    
    args = parser.parse_args()
    
    # Parse extensions
    extensions = set(ext.strip() for ext in args.extensions.split(','))
    
    # Create migrator
    migrator = TestIDMigrator(dry_run=not args.apply)
    
    # Scan directory
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path '{path}' does not exist")
        sys.exit(1)
    
    print(f"Scanning {path} for invalid test IDs...")
    print(f"Extensions: {', '.join(extensions)}")
    
    if path.is_file():
        migrator.files_scanned = 1
        if migrator.migrate_file(path):
            migrator.files_with_violations = 1
    else:
        migrator.scan_directory(path, extensions)
    
    # Print report
    print(migrator.generate_report())


if __name__ == "__main__":
    main()