#!/usr/bin/env python3
"""
Script to migrate all IsolatedEnvironment imports to the unified shared implementation.

This script systematically updates all import statements across the codebase to use
shared.isolated_environment instead of service-specific implementations.

CRITICAL: This migration enforces SSOT compliance per SPEC/unified_environment_management.xml
"""
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImportMigrator:
    """Handles systematic migration of IsolatedEnvironment imports."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.migration_stats = {
            "files_processed": 0,
            "imports_updated": 0,
            "errors": []
        }
        
        # Define import replacement patterns
        self.import_patterns = [
            # dev_launcher imports
            (r'from dev_launcher\.isolated_environment import (.+)', r'from shared.isolated_environment import \1'),
            
            # netra_backend imports
            (r'from netra_backend\.app\.core\.isolated_environment import (.+)', r'from shared.isolated_environment import \1'),
            
            # auth_service imports
            (r'from auth_service\.auth_core\.isolated_environment import (.+)', r'from shared.isolated_environment import \1'),
            
            # analytics_service imports
            (r'from analytics_service\.analytics_core\.isolated_environment import (.+)', r'from shared.isolated_environment import \1'),
            
            # Handle class imports specifically
            (r'from shared.isolated_environment import IsolatedEnvironment'),
        ]
    
    def find_python_files_with_imports(self) -> List[Path]:
        """Find all Python files that import from isolated_environment modules."""
        files_with_imports = []
        
        for root, dirs, files in os.walk(self.repo_root):
            # Skip certain directories
            skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        if 'isolated_environment import' in content:
                            files_with_imports.append(file_path)
                    except Exception as e:
                        logger.warning(f"Could not read {file_path}: {e}")
        
        return files_with_imports
    
    def update_imports_in_file(self, file_path: Path) -> bool:
        """Update imports in a single file."""
        try:
            original_content = file_path.read_text(encoding='utf-8')
            content = original_content
            file_updated = False
            
            for pattern, replacement in self.import_patterns:
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
                    file_updated = True
                    logger.info(f"Updated import pattern in {file_path.relative_to(self.repo_root)}")
            
            if file_updated:
                file_path.write_text(content, encoding='utf-8')
                self.migration_stats["imports_updated"] += 1
                return True
            
            return False
            
        except Exception as e:
            error_msg = f"Failed to update {file_path}: {e}"
            logger.error(error_msg)
            self.migration_stats["errors"].append(error_msg)
            return False
    
    def migrate_all_imports(self) -> Dict[str, any]:
        """Migrate all isolated_environment imports to shared version."""
        logger.info("Starting IsolatedEnvironment import migration...")
        
        # Find all files with imports
        files_with_imports = self.find_python_files_with_imports()
        logger.info(f"Found {len(files_with_imports)} files with isolated_environment imports")
        
        # Update each file
        updated_files = []
        for file_path in files_with_imports:
            if self.update_imports_in_file(file_path):
                updated_files.append(file_path)
            self.migration_stats["files_processed"] += 1
        
        logger.info(f"Migration complete: {len(updated_files)} files updated")
        
        return {
            "updated_files": [str(f.relative_to(self.repo_root)) for f in updated_files],
            "stats": self.migration_stats
        }


def main():
    """Main migration function."""
    repo_root = Path(__file__).parent.parent
    migrator = ImportMigrator(repo_root)
    
    result = migrator.migrate_all_imports()
    
    print(f"\nMIGRATION SUMMARY:")
    print(f"Files processed: {result['stats']['files_processed']}")
    print(f"Files updated: {len(result['updated_files'])}")
    print(f"Import statements updated: {result['stats']['imports_updated']}")
    
    if result['stats']['errors']:
        print(f"\nERRORS ({len(result['stats']['errors'])}):")
        for error in result['stats']['errors']:
            print(f"  - {error}")
    
    if result['updated_files']:
        print(f"\nUPDATED FILES:")
        for file in result['updated_files']:
            print(f"  - {file}")
    
    return len(result['stats']['errors']) == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)