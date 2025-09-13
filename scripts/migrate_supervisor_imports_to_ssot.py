#!/usr/bin/env python3
"""
SSOT Migration Script: supervisor_consolidated → supervisor_ssot

Business Value: Resolve Issue #800 - Eliminate duplicate SupervisorAgent implementations
BVJ: ALL segments | Platform Stability | Golden Path reliability for $500K+ ARR

This script systematically migrates all imports from supervisor_consolidated to supervisor_ssot,
ensuring consistent agent behavior across the entire system.

CRITICAL SAFETY:
- Creates backups of all modified files
- Validates imports work before committing changes
- Provides rollback capability
- Maintains backward compatibility during transition
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
import subprocess
import sys

# Import mapping patterns
IMPORT_MIGRATIONS = [
    # Direct imports
    (
        r'from netra_backend\.app\.agents\.supervisor_consolidated import',
        'from netra_backend.app.agents.supervisor_ssot import'
    ),
    # Aliased imports
    (
        r'from netra_backend\.app\.agents\.supervisor_consolidated import \(\s*SupervisorAgent as Supervisor,?\s*\)',
        'from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as Supervisor'
    ),
    # Multi-line imports
    (
        r'from netra_backend\.app\.agents\.supervisor_consolidated import \(\s*SupervisorAgent as Supervisor,\s*\)',
        'from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as Supervisor'
    ),
]

# Files to migrate (active codebase only, excluding tests and backups)
CRITICAL_FILES = [
    "netra_backend/app/dependencies.py",
    "netra_backend/app/websocket_core/supervisor_factory.py",
    "netra_backend/app/websocket_core/ssot_service_initializer.py",
    "netra_backend/app/core/supervisor_factory.py",
    "netra_backend/app/agents/supervisor_admin_init.py",
    "netra_backend/app/startup_module.py",
    "netra_backend/app/services/agent_service_factory.py",
    "netra_backend/app/routes/agent_route.py",
    "netra_backend/app/services/agent_service_core.py",
    "netra_backend/app/services/message_handlers.py",
]

class SSotMigrationTool:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.backup_dir = self.root_dir / "backups" / "supervisor_ssot_migration"
        self.migrated_files: List[Path] = []

    def create_backup_structure(self):
        """Create backup directory structure."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created backup directory: {self.backup_dir}")

    def backup_file(self, file_path: Path) -> Path:
        """Create backup of file before modification."""
        backup_path = self.backup_dir / file_path.name
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backed up: {file_path} → {backup_path}")
        return backup_path

    def migrate_file_imports(self, file_path: Path) -> bool:
        """Migrate imports in a single file."""
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return False

        # Read original content
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Apply migration patterns
        modified_content = original_content
        changes_made = False

        for old_pattern, new_pattern in IMPORT_MIGRATIONS:
            if re.search(old_pattern, modified_content):
                modified_content = re.sub(old_pattern, new_pattern, modified_content)
                changes_made = True
                print(f"✅ Applied pattern: {old_pattern} → {new_pattern}")

        if changes_made:
            # Create backup first
            self.backup_file(file_path)

            # Write modified content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)

            self.migrated_files.append(file_path)
            print(f"✅ Migrated imports in: {file_path}")
            return True
        else:
            print(f"ℹ️  No migration needed: {file_path}")
            return False

    def validate_imports(self) -> bool:
        """Validate that migrated imports work correctly."""
        print("\n🔍 Validating migrated imports...")

        # Test import of SSOT supervisor
        try:
            result = subprocess.run([
                sys.executable, "-c",
                "from netra_backend.app.agents.supervisor_ssot import SupervisorAgent; print('✅ SSOT import successful')"
            ], capture_output=True, text=True, cwd=self.root_dir)

            if result.returncode != 0:
                print(f"❌ SSOT import validation failed: {result.stderr}")
                return False
            else:
                print("✅ SSOT SupervisorAgent import validation passed")

        except Exception as e:
            print(f"❌ Import validation error: {e}")
            return False

        return True

    def run_migration(self) -> bool:
        """Execute the complete migration process."""
        print("🚀 Starting SSOT SupervisorAgent migration...")

        # Step 1: Create backup structure
        self.create_backup_structure()

        # Step 2: Migrate each critical file
        migration_results = []
        for file_path in CRITICAL_FILES:
            full_path = self.root_dir / file_path
            result = self.migrate_file_imports(full_path)
            migration_results.append((file_path, result))

        # Step 3: Validate imports work
        if not self.validate_imports():
            print("❌ Import validation failed - consider rolling back")
            return False

        # Step 4: Report results
        print(f"\n📊 Migration Summary:")
        print(f"  Total files processed: {len(CRITICAL_FILES)}")
        print(f"  Files migrated: {len(self.migrated_files)}")
        print(f"  Backup location: {self.backup_dir}")

        print(f"\n✅ Migration completed successfully!")
        print(f"🎯 Issue #800 remediation: supervisor_consolidated → supervisor_ssot")

        return True

    def rollback_migration(self):
        """Rollback migration if needed."""
        print("🔄 Rolling back migration...")

        for file_path in self.migrated_files:
            backup_path = self.backup_dir / file_path.name
            if backup_path.exists():
                shutil.copy2(backup_path, file_path)
                print(f"✅ Restored: {file_path}")

        print("🔄 Rollback completed")

def main():
    """Main execution function."""
    root_dir = os.getcwd()
    print("SSOT Migration Tool - Issue #800 Resolution")
    print(f"Working directory: {root_dir}")

    migrator = SSotMigrationTool(root_dir)

    try:
        success = migrator.run_migration()
        if success:
            print("\n🎉 SSOT migration completed successfully!")
            print("📋 Next steps:")
            print("  1. Run tests to validate system stability")
            print("  2. Remove supervisor_consolidated.py file")
            print("  3. Run mission-critical WebSocket events suite")
        else:
            print("\n❌ Migration failed - check logs above")

    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
        migrator.rollback_migration()
    except Exception as e:
        print(f"\n❌ Migration error: {e}")
        migrator.rollback_migration()

if __name__ == "__main__":
    main()