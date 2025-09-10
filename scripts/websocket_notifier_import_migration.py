#!/usr/bin/env python3
"""
Automated WebSocketNotifier import path migration.
Converts all non-canonical imports to SSOT canonical path.

Usage:
    python scripts/websocket_notifier_import_migration.py

Part of GitHub Issue #216 SSOT Remediation Plan - Phase 1.1
"""

import os
import re
import subprocess
import sys
from typing import List, Set

# SSOT Configuration
CANONICAL_IMPORT = "from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier"

DEPRECATED_PATTERNS = [
    r'from netra_backend\.app\.agents\.supervisor\.websocket_notifier import WebSocketNotifier',
    r'from netra_backend\.app\.websocket_core\.websocket_notifier import WebSocketNotifier',
    r'from netra_backend\.app\.services\.websocket_notifier import WebSocketNotifier'
]

# Files to exclude from migration (already updated or special cases)
EXCLUDED_FILES = {
    'tests/unit/ssot_validation/test_websocket_notifier_ssot_violations.py',  # Test violations intentionally
    'tests/unit/ssot_validation/test_websocket_notifier_ssot_compliance.py',  # Test compliance
    'scripts/websocket_notifier_import_migration.py',  # This script
    'WEBSOCKET_NOTIFIER_SSOT_REMEDIATION_PLAN_COMPREHENSIVE.md'  # Documentation
}

class ImportMigrator:
    """Handles WebSocketNotifier import migration."""
    
    def __init__(self):
        self.migrated_files = []
        self.failed_files = []
        self.skipped_files = []
        
    def migrate_imports_in_file(self, file_path: str) -> bool:
        """Migrate deprecated imports in a single file."""
        try:
            # Skip excluded files
            if any(file_path.endswith(excluded) for excluded in EXCLUDED_FILES):
                self.skipped_files.append(file_path)
                return False
                
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Replace each deprecated pattern with canonical import
            for pattern in DEPRECATED_PATTERNS:
                content = re.sub(pattern, CANONICAL_IMPORT, content)
            
            if content != original_content:
                # Create backup before modifying
                backup_path = f"{file_path}.backup_pre_ssot_migration"
                with open(backup_path, 'w') as f:
                    f.write(original_content)
                
                # Write migrated content
                with open(file_path, 'w') as f:
                    f.write(content)
                
                self.migrated_files.append(file_path)
                return True
            
            return False
        
        except Exception as e:
            print(f"❌ Error migrating {file_path}: {e}")
            self.failed_files.append(file_path)
            return False

    def find_files_needing_migration(self) -> List[str]:
        """Find all Python files with deprecated imports."""
        files = set()
        
        # Search for each deprecated pattern
        for pattern in DEPRECATED_PATTERNS:
            # Use ripgrep if available, otherwise grep
            try:
                cmd = ['rg', '-l', pattern, '--type', 'py', '.']
                result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/anthony/Desktop/netra-apex')
                if result.returncode == 0 and result.stdout.strip():
                    files.update(result.stdout.strip().split('\n'))
            except FileNotFoundError:
                # Fallback to grep
                cmd = ['grep', '-r', '-l', pattern, '.', '--include=*.py']
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/anthony/Desktop/netra-apex')
                    if result.returncode == 0 and result.stdout.strip():
                        files.update(result.stdout.strip().split('\n'))
                except subprocess.CalledProcessError:
                    continue
        
        # Filter out empty strings and invalid paths
        return [f for f in files if f.strip() and os.path.exists(f)]
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful."""
        print("\n🔍 Validating migration...")
        
        # Check for remaining deprecated imports
        remaining_violations = self.find_files_needing_migration()
        
        if remaining_violations:
            print(f"⚠️  WARNING: {len(remaining_violations)} files still have deprecated imports:")
            for violation in remaining_violations[:10]:  # Show first 10
                print(f"   - {violation}")
            if len(remaining_violations) > 10:
                print(f"   ... and {len(remaining_violations) - 10} more")
            return False
        else:
            print("✅ All deprecated imports successfully migrated!")
            return True
    
    def generate_migration_report(self) -> str:
        """Generate detailed migration report."""
        report = []
        report.append("=" * 60)
        report.append("WebSocketNotifier Import Migration Report")
        report.append("=" * 60)
        
        report.append(f"✅ Successfully migrated: {len(self.migrated_files)} files")
        report.append(f"⏭️  Skipped (excluded): {len(self.skipped_files)} files")
        report.append(f"❌ Failed: {len(self.failed_files)} files")
        
        if self.migrated_files:
            report.append("\nMigrated Files:")
            for file in self.migrated_files:
                report.append(f"  ✅ {file}")
        
        if self.failed_files:
            report.append("\nFailed Files:")
            for file in self.failed_files:
                report.append(f"  ❌ {file}")
        
        if self.skipped_files:
            report.append("\nSkipped Files:")
            for file in self.skipped_files:
                report.append(f"  ⏭️  {file}")
        
        report.append(f"\nCanonical Import Used:")
        report.append(f"  {CANONICAL_IMPORT}")
        
        return "\n".join(report)

def main():
    """Execute import migration process."""
    print("🚀 Starting WebSocketNotifier SSOT Import Migration")
    print("📋 GitHub Issue #216 - Phase 1.1: Import Path Consolidation")
    print("=" * 60)
    
    migrator = ImportMigrator()
    
    # Find files needing migration
    print("🔍 Scanning for files with deprecated imports...")
    files = migrator.find_files_needing_migration()
    print(f"📁 Found {len(files)} files with deprecated imports")
    
    if not files:
        print("✅ No files found with deprecated imports - migration complete!")
        return 0
    
    # Show files to be migrated
    print("\n📝 Files to be migrated:")
    for file in files[:10]:  # Show first 10
        print(f"  - {file}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")
    
    # Confirm migration
    try:
        response = input("\n❓ Proceed with migration? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Migration cancelled by user")
            return 1
    except KeyboardInterrupt:
        print("\n❌ Migration cancelled by user")
        return 1
    
    # Execute migration
    print("\n🔄 Executing migration...")
    for i, file_path in enumerate(files, 1):
        print(f"  📄 [{i}/{len(files)}] Migrating {file_path}...")
        success = migrator.migrate_imports_in_file(file_path)
        if success:
            print(f"    ✅ Migrated successfully")
        else:
            print(f"    ⏭️  Skipped or failed")
    
    # Validate migration
    migration_success = migrator.validate_migration()
    
    # Generate and display report
    print("\n" + migrator.generate_migration_report())
    
    # Save report to file
    report_file = "websocket_notifier_import_migration_report.txt"
    with open(report_file, 'w') as f:
        f.write(migrator.generate_migration_report())
    print(f"\n📄 Migration report saved to: {report_file}")
    
    # Next steps
    if migration_success:
        print("\n🎉 Migration completed successfully!")
        print("\n📋 Next Steps:")
        print("  1. Run mission critical tests: python tests/mission_critical/test_websocket_agent_events_suite.py")
        print("  2. Execute Phase 1.2: Legacy Implementation Deprecation")
        print("  3. Validate development environment for import errors")
        return 0
    else:
        print("\n⚠️  Migration completed with warnings - manual review required")
        return 2

if __name__ == "__main__":
    sys.exit(main())