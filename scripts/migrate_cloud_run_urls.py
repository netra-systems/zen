#!/usr/bin/env python3
"""
Automated Cloud Run URL Migration Script
=======================================

CRITICAL IMPLEMENTATION: Migrate all staging E2E tests from direct Cloud Run 
endpoints to load balancer endpoints via *.staging.netrasystems.ai

Business Value: Platform/Internal - System Reliability
- Prevents test failures due to direct Cloud Run URL changes
- Ensures consistent staging environment testing
- Improves deployment resilience

CLAUDE.md COMPLIANCE:
- Follows SSOT principles for endpoint configuration
- Uses atomic changes with rollback capability
- Validates changes before applying
"""

import os
import re
import sys
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


@dataclass
class URLMigration:
    """URL migration definition"""
    old_pattern: str
    new_url: str
    description: str


# URL Migration Mappings (SSOT)
URL_MIGRATIONS = [
    URLMigration(
        old_pattern=r'https://netra-backend-staging-[a-zA-Z0-9]+-[a-z]+\.a\.run\.app',
        new_url='https://api.staging.netrasystems.ai',
        description='Backend staging service to load balancer'
    ),
    URLMigration(
        old_pattern=r'https://netra-auth-staging-[a-zA-Z0-9]+-[a-z]+\.a\.run\.app',
        new_url='https://auth.staging.netrasystems.ai',
        description='Auth staging service to load balancer'
    ),
    URLMigration(
        old_pattern=r'https://netra-frontend-staging-[a-zA-Z0-9]+-[a-z]+\.a\.run\.app',
        new_url='https://app.staging.netrasystems.ai',
        description='Frontend staging service to load balancer'
    )
]

# File patterns to exclude from migration
EXCLUDE_PATTERNS = [
    r'backup/',
    r'reports/',
    r'docs/',
    r'logs/',
    r'config/',
    r'SPEC/',
    r'terraform-gcp-staging/',
    r'\.md$',
    r'\.json$',
    r'\.xml$',
    r'\.txt$'
]


class CloudRunURLMigrator:
    """Automated Cloud Run URL migration utility"""
    
    def __init__(self, project_root: Path, dry_run: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.backup_dir = project_root / "backup" / "url_migration" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.changes_log = []
        
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from migration"""
        file_str = str(file_path.relative_to(self.project_root))
        return any(re.search(pattern, file_str) for pattern in EXCLUDE_PATTERNS)
    
    def find_files_with_cloud_run_urls(self) -> List[Path]:
        """Find all files containing Cloud Run URLs"""
        files_with_urls = []
        
        for migration in URL_MIGRATIONS:
            pattern = re.compile(migration.old_pattern)
            
            # Search in Python files
            for py_file in self.project_root.rglob("*.py"):
                if self.should_exclude_file(py_file):
                    continue
                    
                try:
                    content = py_file.read_text(encoding='utf-8')
                    if pattern.search(content):
                        files_with_urls.append(py_file)
                except Exception as e:
                    logger.warning(f"Error reading {py_file}: {e}")
        
        return list(set(files_with_urls))  # Remove duplicates
    
    def analyze_file_changes(self, file_path: Path) -> List[Tuple[str, str, str]]:
        """Analyze what changes would be made to a file"""
        changes = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            for migration in URL_MIGRATIONS:
                pattern = re.compile(migration.old_pattern)
                matches = pattern.finditer(content)
                
                for match in matches:
                    old_url = match.group(0)
                    changes.append((old_url, migration.new_url, migration.description))
                    
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            
        return changes
    
    def create_backup(self, file_path: Path) -> Path:
        """Create backup of file before modification"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
        relative_path = file_path.relative_to(self.project_root)
        backup_path = self.backup_dir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate URLs in a single file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            modified = False
            
            for migration in URL_MIGRATIONS:
                pattern = re.compile(migration.old_pattern)
                if pattern.search(content):
                    content = pattern.sub(migration.new_url, content)
                    modified = True
                    logger.info(f"  {migration.description}")
            
            if modified and not self.dry_run:
                # Create backup before modifying
                backup_path = self.create_backup(file_path)
                logger.info(f"  Created backup: {backup_path}")
                
                # Write modified content
                file_path.write_text(content, encoding='utf-8')
                
                # Log change
                self.changes_log.append({
                    'file': str(file_path),
                    'backup': str(backup_path),
                    'timestamp': datetime.now().isoformat()
                })
            
            return modified
            
        except Exception as e:
            logger.error(f"Error migrating {file_path}: {e}")
            return False
    
    def run_migration(self) -> Dict[str, any]:
        """Run the complete migration process"""
        logger.info("Starting Cloud Run URL migration...")
        
        # Find files to migrate
        files_to_migrate = self.find_files_with_cloud_run_urls()
        logger.info(f"Found {len(files_to_migrate)} files with Cloud Run URLs")
        
        results = {
            'total_files': len(files_to_migrate),
            'migrated_files': [],
            'failed_files': [],
            'dry_run': self.dry_run,
            'backup_dir': str(self.backup_dir) if not self.dry_run else None
        }
        
        for file_path in files_to_migrate:
            logger.info(f"\nProcessing: {file_path.relative_to(self.project_root)}")
            
            # Show what changes would be made
            changes = self.analyze_file_changes(file_path)
            if changes:
                for old_url, new_url, description in changes:
                    logger.info(f"  {old_url} → {new_url}")
                
                if self.dry_run:
                    logger.info(f"  [DRY RUN] Would migrate {len(changes)} URLs")
                    results['migrated_files'].append(str(file_path))
                else:
                    success = self.migrate_file(file_path)
                    if success:
                        results['migrated_files'].append(str(file_path))
                        logger.info(f"  ✅ Successfully migrated")
                    else:
                        results['failed_files'].append(str(file_path))
                        logger.error(f"  ❌ Migration failed")
        
        # Save migration log
        if not self.dry_run and self.changes_log:
            log_file = self.backup_dir / "migration_log.json"
            with open(log_file, 'w') as f:
                json.dump(self.changes_log, f, indent=2)
            logger.info(f"Migration log saved: {log_file}")
        
        return results
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful"""
        logger.info("Validating migration...")
        
        remaining_files = self.find_files_with_cloud_run_urls()
        if remaining_files:
            logger.error(f"❌ {len(remaining_files)} files still contain Cloud Run URLs:")
            for file_path in remaining_files:
                logger.error(f"  - {file_path.relative_to(self.project_root)}")
            return False
        
        logger.info("✅ Validation successful - no Cloud Run URLs found")
        return True
    
    def rollback_migration(self, migration_log_path: Path) -> bool:
        """Rollback migration using backup files"""
        try:
            with open(migration_log_path, 'r') as f:
                changes = json.load(f)
            
            logger.info(f"Rolling back {len(changes)} files...")
            
            for change in changes:
                original_file = Path(change['file'])
                backup_file = Path(change['backup'])
                
                if backup_file.exists():
                    shutil.copy2(backup_file, original_file)
                    logger.info(f"  Restored: {original_file.relative_to(self.project_root)}")
                else:
                    logger.error(f"  Backup not found: {backup_file}")
            
            logger.info("✅ Rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False


def main():
    """Main script entry point"""
    parser = argparse.ArgumentParser(description='Migrate Cloud Run URLs to load balancer endpoints')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be changed without modifying files')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually perform the migration (disables dry-run)')
    parser.add_argument('--validate', action='store_true',
                       help='Only validate that no Cloud Run URLs remain')
    parser.add_argument('--rollback', type=str,
                       help='Rollback migration using specified log file')
    
    args = parser.parse_args()
    
    # Determine if this is a dry run
    dry_run = not args.execute if not args.validate and not args.rollback else False
    
    migrator = CloudRunURLMigrator(project_root, dry_run=dry_run)
    
    if args.rollback:
        success = migrator.rollback_migration(Path(args.rollback))
        sys.exit(0 if success else 1)
    
    if args.validate:
        success = migrator.validate_migration()
        sys.exit(0 if success else 1)
    
    # Run migration
    results = migrator.run_migration()
    
    logger.info("\n" + "="*60)
    logger.info("MIGRATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Mode: {'DRY RUN' if results['dry_run'] else 'EXECUTION'}")
    logger.info(f"Total files: {results['total_files']}")
    logger.info(f"Successfully processed: {len(results['migrated_files'])}")
    logger.info(f"Failed files: {len(results['failed_files'])}")
    
    if results['backup_dir']:
        logger.info(f"Backup directory: {results['backup_dir']}")
    
    if not results['dry_run']:
        # Validate migration
        success = migrator.validate_migration()
        if not success:
            logger.error("❌ Migration validation failed!")
            sys.exit(1)
    
    logger.info("✅ Migration completed successfully!")


if __name__ == "__main__":
    main()