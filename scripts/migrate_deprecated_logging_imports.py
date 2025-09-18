#!/usr/bin/env python3
"""
Test Warning Remediation: Logging SSOT Migration Script

Business Value Justification (BVJ):
- Segment: Platform/All Services  
- Business Goal: Golden Path stability and operational excellence
- Value Impact: Eliminates logging fragmentation that causes $500K+ ARR debugging failures
- Strategic Impact: SSOT compliance prevents cascade failures during infrastructure incidents

This script migrates deprecated logging imports to the unified SSOT logging system.
CRITICAL: This supports Issue #1278 infrastructure remediation by ensuring 
consistent logging during recovery operations.
"""

import os
import re
import shutil
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
from datetime import datetime

class LoggingSSOTMigrator:
    """Migrates deprecated logging imports to SSOT patterns"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.changes_made = []
        self.backup_dir = Path("backups/logging_migration_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        # SSOT import patterns to use
        self.ssot_imports = {
            'basic_logger': 'from shared.logging.unified_logging_ssot import get_ssot_logger',
            'legacy_logger': 'from shared.logging.unified_logging_ssot import get_logger',
            'reset_logging': 'from shared.logging.unified_logging_ssot import reset_logging'
        }
        
        # Patterns to replace
        self.deprecated_patterns = [
            (r'^import logging$', 'from shared.logging.unified_logging_ssot import get_ssot_logger'),
            (r'^from logging import.*$', 'from shared.logging.unified_logging_ssot import get_ssot_logger'),
            (r'logging\.getLogger\((.*?)\)', r'get_ssot_logger(\1)'),
            (r'logging\.info\((.*?)\)', r'get_ssot_logger().info(\1)'),
            (r'logging\.error\((.*?)\)', r'get_ssot_logger().error(\1)'),
            (r'logging\.warning\((.*?)\)', r'get_ssot_logger().warning(\1)'),
            (r'logging\.debug\((.*?)\)', r'get_ssot_logger().debug(\1)'),
        ]
    
    def create_backup(self, file_path: Path) -> None:
        """Create backup of file before modification"""
        if not self.dry_run:
            backup_path = self.backup_dir / file_path.relative_to(Path.cwd())
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
    
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate a single file to SSOT logging patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            changes_in_file = []
            
            # Apply each replacement pattern
            for pattern, replacement in self.deprecated_patterns:
                new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
                if count > 0:
                    changes_in_file.append(f"Applied {pattern} -> {replacement} ({count} times)")
                    content = new_content
            
            # If changes were made
            if changes_in_file:
                # Ensure SSOT import is present
                if 'get_ssot_logger' in content and 'from shared.logging.unified_logging_ssot import get_ssot_logger' not in content:
                    import_line = 'from shared.logging.unified_logging_ssot import get_ssot_logger\n'
                    
                    # Find good insertion point (after other imports)
                    lines = content.split('\n')
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            insert_idx = i + 1
                        elif line.strip() == '' or line.startswith('#'):
                            continue
                        else:
                            break
                    
                    lines.insert(insert_idx, import_line.rstrip())
                    content = '\n'.join(lines)
                
                if not self.dry_run:
                    self.create_backup(file_path)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                self.changes_made.append({
                    'file': str(file_path),
                    'changes': changes_in_file
                })
                return True
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False
        
        return False
    
    def scan_and_migrate(self, target_dirs: List[str]) -> Dict:
        """Scan target directories and migrate deprecated logging imports"""
        results = {
            'files_processed': 0,
            'files_changed': 0,
            'total_changes': 0,
            'errors': []
        }
        
        for target_dir in target_dirs:
            if not os.path.exists(target_dir):
                print(f"Warning: Directory {target_dir} does not exist")
                continue
                
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = Path(root) / file
                        results['files_processed'] += 1
                        
                        if self.migrate_file(file_path):
                            results['files_changed'] += 1
                            results['total_changes'] += len(self.changes_made[-1]['changes'])
        
        return results
    
    def generate_report(self) -> str:
        """Generate migration report"""
        report = f"""
Logging SSOT Migration Report
Generated: {datetime.now().isoformat()}
Mode: {'DRY RUN' if self.dry_run else 'EXECUTION'}

Changes Made: {len(self.changes_made)} files

"""
        for change in self.changes_made:
            report += f"\nFile: {change['file']}\n"
            for change_detail in change['changes']:
                report += f"  - {change_detail}\n"
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Migrate deprecated logging imports to SSOT')
    parser.add_argument('--execute', action='store_true', help='Execute changes (default is dry run)')
    parser.add_argument('--target-dirs', nargs='+', default=['tests', 'netra_backend/tests'], 
                       help='Directories to scan')
    parser.add_argument('--report-file', default='logging_migration_report.txt',
                       help='Output file for migration report')
    
    args = parser.parse_args()
    
    migrator = LoggingSSOTMigrator(dry_run=not args.execute)
    
    print(f"Starting logging SSOT migration ({'EXECUTION' if args.execute else 'DRY RUN'})...")
    print(f"Target directories: {args.target_dirs}")
    
    results = migrator.scan_and_migrate(args.target_dirs)
    
    print(f"\nMigration Results:")
    print(f"Files processed: {results['files_processed']}")
    print(f"Files changed: {results['files_changed']}")
    print(f"Total changes: {results['total_changes']}")
    
    # Generate and save report
    report = migrator.generate_report()
    with open(args.report_file, 'w') as f:
        f.write(report)
    
    print(f"\nDetailed report saved to: {args.report_file}")
    
    if not args.execute:
        print("\nThis was a DRY RUN. Use --execute to apply changes.")
        print("Recommended: Review the report and test critical files before full execution.")

if __name__ == "__main__":
    main()