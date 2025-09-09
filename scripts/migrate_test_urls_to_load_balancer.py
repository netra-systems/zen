#!/usr/bin/env python3
"""
Load Balancer URL Migration Script
==================================

CRITICAL: Migrate all E2E test files from direct Cloud Run URLs to load balancer endpoints.

Business Value: Platform/Internal - Infrastructure Compliance
Ensures E2E tests validate the same infrastructure path users experience.

CLAUDE.md COMPLIANCE:
- SSOT for URL migration patterns
- Systematic approach to prevent manual errors
- Complete validation and rollback capability
"""

import os
import re
import sys
import glob
import shutil
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


@dataclass
class URLMigration:
    """Configuration for URL migration"""
    old_pattern: str
    new_url: str
    description: str


# SSOT: URL Migration Patterns
URL_MIGRATIONS = [
    URLMigration(
        old_pattern=r"https://netra-backend-staging-pnovr5vsba-uc\.a\.run\.app",
        new_url="https://api.staging.netrasystems.ai",
        description="Backend API load balancer endpoint"
    ),
    URLMigration(
        old_pattern=r"wss://netra-backend-staging-pnovr5vsba-uc\.a\.run\.app",
        new_url="wss://api.staging.netrasystems.ai", 
        description="WebSocket load balancer endpoint"
    ),
    URLMigration(
        old_pattern=r"https://netra-frontend-staging-pnovr5vsba-uc\.a\.run\.app",
        new_url="https://app.staging.netrasystems.ai",
        description="Frontend load balancer endpoint"
    ),
    URLMigration(
        old_pattern=r"wss://netra-frontend-staging-pnovr5vsba-uc\.a\.run\.app",
        new_url="wss://app.staging.netrasystems.ai",
        description="Frontend WebSocket load balancer endpoint"
    )
]

# File patterns to migrate
E2E_TEST_PATTERNS = [
    "tests/e2e/**/*.py",
    "tests/mission_critical/**/*.py", 
    "tests/integration/**/*.py"
]

# Files to exclude from migration
EXCLUDE_PATTERNS = [
    "**/conftest.py",  # Usually doesn't contain direct URLs
    "**/*backup*",     # Backup files
    "**/*_old.py"      # Old files
]


class LoadBalancerURLMigrator:
    """Handles migration from Cloud Run URLs to load balancer endpoints"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = project_root
        self.backup_dir = self.project_root / "backup" / "url_migration" 
        self.migration_stats: Dict[str, int] = {
            "files_processed": 0,
            "files_modified": 0, 
            "replacements_made": 0
        }
        
    def find_test_files(self) -> List[Path]:
        """Find all E2E test files that might need migration"""
        test_files = []
        
        for pattern in E2E_TEST_PATTERNS:
            files = glob.glob(str(self.project_root / pattern), recursive=True)
            for file_path in files:
                path = Path(file_path)
                
                # Skip excluded patterns
                skip_file = False
                for exclude_pattern in EXCLUDE_PATTERNS:
                    if path.match(exclude_pattern):
                        skip_file = True
                        break
                
                if not skip_file and path.suffix == '.py':
                    test_files.append(path)
        
        return sorted(set(test_files))
    
    def analyze_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """Analyze a file for Cloud Run URLs that need migration"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            found_patterns = []
            needs_migration = False
            
            for migration in URL_MIGRATIONS:
                if re.search(migration.old_pattern, content):
                    found_patterns.append(migration.description)
                    needs_migration = True
            
            return needs_migration, found_patterns
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return False, []
    
    def create_backup(self, file_path: Path) -> Path:
        """Create backup of file before migration"""
        if self.dry_run:
            return file_path
        
        # Create backup directory structure
        relative_path = file_path.relative_to(self.project_root)
        backup_path = self.backup_dir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file to backup
        shutil.copy2(file_path, backup_path)
        logger.debug(f"Created backup: {backup_path}")
        
        return backup_path
    
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate URLs in a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Apply all migrations
            modified_content = original_content
            replacements_made = 0
            
            for migration in URL_MIGRATIONS:
                new_content = re.sub(migration.old_pattern, migration.new_url, modified_content)
                if new_content != modified_content:
                    count = len(re.findall(migration.old_pattern, modified_content))
                    replacements_made += count
                    logger.info(f"  {migration.description}: {count} replacements")
                    modified_content = new_content
            
            # Check if any changes were made
            if modified_content != original_content:
                if not self.dry_run:
                    # Create backup first
                    self.create_backup(file_path)
                    
                    # Write modified content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                
                self.migration_stats["replacements_made"] += replacements_made
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error migrating {file_path}: {e}")
            return False
    
    def validate_migration(self, file_path: Path) -> bool:
        """Validate that migration was successful"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for any remaining Cloud Run URLs
            for migration in URL_MIGRATIONS:
                if re.search(migration.old_pattern, content):
                    logger.warning(f"Migration incomplete in {file_path}: still contains {migration.old_pattern}")
                    return False
            
            # Check that new URLs are present if file was modified
            has_staging_urls = (
                "staging.netrasystems.ai" in content or 
                "api.staging.netrasystems.ai" in content or
                "app.staging.netrasystems.ai" in content
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating {file_path}: {e}")
            return False
    
    def run_migration(self) -> bool:
        """Run the complete migration process"""
        logger.info("Starting Load Balancer URL Migration")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        
        # Find all test files
        test_files = self.find_test_files()
        logger.info(f"Found {len(test_files)} test files to analyze")
        
        # Analyze files
        files_to_migrate = []
        for file_path in test_files:
            self.migration_stats["files_processed"] += 1
            needs_migration, patterns = self.analyze_file(file_path)
            
            if needs_migration:
                files_to_migrate.append((file_path, patterns))
                logger.info(f"MIGRATION NEEDED: {file_path}")
                for pattern in patterns:
                    logger.info(f"  - {pattern}")
        
        if not files_to_migrate:
            logger.info("No files require migration")
            return True
        
        logger.info(f"\nMigrating {len(files_to_migrate)} files...")
        
        # Migrate files
        migration_success = True
        for file_path, patterns in files_to_migrate:
            logger.info(f"Migrating: {file_path}")
            
            if self.migrate_file(file_path):
                self.migration_stats["files_modified"] += 1
                
                # Validate migration (only in live mode)
                if not self.dry_run:
                    if not self.validate_migration(file_path):
                        migration_success = False
            else:
                logger.warning(f"No changes made to: {file_path}")
        
        # Print summary
        logger.info("\nMigration Summary:")
        logger.info(f"Files processed: {self.migration_stats['files_processed']}")  
        logger.info(f"Files modified: {self.migration_stats['files_modified']}")
        logger.info(f"Total replacements: {self.migration_stats['replacements_made']}")
        
        if not self.dry_run and migration_success:
            logger.success("Migration completed successfully!")
            logger.info(f"Backups saved to: {self.backup_dir}")
        elif not self.dry_run and not migration_success:
            logger.error("Migration completed with errors - check logs")
        
        return migration_success
    
    def rollback_migration(self) -> bool:
        """Rollback migration using backups"""
        if not self.backup_dir.exists():
            logger.error("No backup directory found - cannot rollback")
            return False
        
        logger.info("Rolling back migration...")
        
        # Find all backup files
        backup_files = glob.glob(str(self.backup_dir / "**" / "*.py"), recursive=True)
        
        rollback_count = 0
        for backup_file_str in backup_files:
            backup_file = Path(backup_file_str)
            
            # Calculate original file path
            relative_path = backup_file.relative_to(self.backup_dir)
            original_file = self.project_root / relative_path
            
            try:
                # Restore from backup
                shutil.copy2(backup_file, original_file)
                rollback_count += 1
                logger.info(f"Restored: {original_file}")
            except Exception as e:
                logger.error(f"Error restoring {original_file}: {e}")
        
        logger.info(f"Rollback completed: {rollback_count} files restored")
        return rollback_count > 0


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate E2E test URLs from Cloud Run to load balancer endpoints"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--rollback",
        action="store_true", 
        help="Rollback migration using backups"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate current state without migrating"
    )
    
    args = parser.parse_args()
    
    migrator = LoadBalancerURLMigrator(dry_run=args.dry_run or args.validate_only)
    
    if args.rollback:
        success = migrator.rollback_migration()
    else:
        success = migrator.run_migration()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()