#!/usr/bin/env python3
"""Redis SSOT Migration - Phase 1 Foundation Repair

MISSION: Migrate deprecated Redis patterns to SSOT imports
SCOPE: 102 files using direct Redis imports need migration to SSOT patterns
TARGET: Follow SSOT_IMPORT_REGISTRY.md verified Redis import patterns

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure  
- Business Goal: Eliminate technical debt and improve reliability
- Value Impact: Consistent Redis patterns reduce bugs and improve maintainability
- Strategic Impact: Enables reliable test infrastructure supporting $500K+ ARR

MIGRATION PATTERNS:
OLD: import redis
NEW: from netra_backend.app.services.redis_client import get_redis_client, get_redis_service

OLD: await get_redis_client()
NEW: await get_redis_client()

OLD: redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=..., port=...)
NEW: redis_client = await get_redis_client()
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import subprocess

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import get_env

class RedisMigrationExecutor:
    """Executes systematic Redis SSOT migration."""
    
    def __init__(self):
        self.processed_files: List[str] = []
        self.errors: List[Tuple[str, str]] = []
        self.migration_stats = {
            'files_scanned': 0,
            'files_migrated': 0,
            'imports_replaced': 0,
            'usage_patterns_updated': 0,
            'errors': 0
        }
    
    def scan_redis_violations(self) -> List[str]:
        """Scan for files using deprecated Redis patterns."""
        print("🔍 Scanning for Redis import violations...")
        
        # Use grep to find files with Redis imports
        try:
            result = subprocess.run([
                'grep', '-r', '--include=*.py', 
                '-l', '^import redis\\|^from redis import',
                str(PROJECT_ROOT)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                files = result.stdout.strip().split('\n') if result.stdout.strip() else []
                files = [f for f in files if f]  # Remove empty strings
                print(f"📊 Found {len(files)} files with Redis import violations")
                return files
            else:
                print("📊 No Redis import violations found!")
                return []
                
        except Exception as e:
            print(f"⚠️  Error scanning files: {e}")
            return []
    
    def analyze_file_patterns(self, file_path: str) -> Dict[str, List[str]]:
        """Analyze Redis patterns in a specific file."""
        patterns = {
            'imports': [],
            'instantiations': [],
            'method_calls': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Import patterns
                if re.match(r'^\s*import redis\s*$', line):
                    patterns['imports'].append((i, line.strip()))
                elif re.match(r'^\s*from redis import', line):
                    patterns['imports'].append((i, line.strip()))
                
                # Instantiation patterns
                if 'await get_redis_client()  # MIGRATED: was redis.Redis(' in line:
                    patterns['instantiations'].append((i, line.strip()))
                elif 'Redis(' in line and 'redis' in content.lower():
                    patterns['instantiations'].append((i, line.strip()))
                
                # Method call patterns  
                if re.search(r'redis\.[a-zA-Z_][a-zA-Z0-9_]*\(', line):
                    patterns['method_calls'].append((i, line.strip()))
        
        except Exception as e:
            self.errors.append((file_path, f"Analysis error: {e}"))
        
        return patterns
    
    def migrate_file(self, file_path: str) -> bool:
        """Migrate a single file to SSOT Redis patterns."""
        print(f"🔄 Migrating: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            migration_applied = False
            
            # Pattern 1: Direct import redis
            if re.search(r'^import redis\s*$', content, re.MULTILINE):
                print(f"  ├─ Replacing 'import redis' with SSOT import")
                content = re.sub(
                    r'^import redis\s*$',
                    'from netra_backend.app.services.redis_client import get_redis_client, get_redis_service',
                    content,
                    flags=re.MULTILINE
                )
                migration_applied = True
                self.migration_stats['imports_replaced'] += 1
            
            # Pattern 2: from redis import ...
            if re.search(r'^from redis import', content, re.MULTILINE):
                print(f"  ├─ Replacing 'from redis import' with SSOT import")
                content = re.sub(
                    r'^from redis import.*$',
                    'from netra_backend.app.services.redis_client import get_redis_client, get_redis_service',
                    content,
                    flags=re.MULTILINE
                )
                migration_applied = True
                self.migration_stats['imports_replaced'] += 1
            
            # Pattern 3: await get_redis_client() instantiation
            if 'await get_redis_client()  # MIGRATED: was redis.Redis(' in content:
                print(f"  ├─ Adding async Redis client pattern comment")
                # Add comment for manual review of instantiation patterns
                content = content.replace(
                    'await get_redis_client()  # MIGRATED: was redis.Redis(',
                    '# MIGRATION NEEDED: redis.Redis( -> await get_redis_client() - requires async context\n    await get_redis_client()  # MIGRATED: was redis.Redis('
                )
                migration_applied = True
                self.migration_stats['usage_patterns_updated'] += 1
            
            # Only write if changes were made
            if migration_applied and content != original_content:
                # Backup original file
                backup_path = f"{file_path}.redis_migration_backup"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                # Write migrated content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  ✅ Migrated successfully (backup: {backup_path})")
                self.migration_stats['files_migrated'] += 1
                return True
            else:
                print(f"  ⏭️  No migration needed")
                return False
                
        except Exception as e:
            error_msg = f"Migration error: {e}"
            print(f"  ❌ {error_msg}")
            self.errors.append((file_path, error_msg))
            self.migration_stats['errors'] += 1
            return False
    
    def validate_syntax(self, file_path: str) -> bool:
        """Validate Python syntax after migration."""
        try:
            result = subprocess.run([
                sys.executable, '-m', 'py_compile', file_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return True
            else:
                print(f"  ⚠️  Syntax error: {result.stderr}")
                return False
        except Exception as e:
            print(f"  ⚠️  Syntax validation error: {e}")
            return False
    
    def execute_migration(self):
        """Execute complete Redis migration."""
        print("🚀 Starting Redis SSOT Migration - Phase 1")
        print("=" * 60)
        
        # Step 1: Scan for violations
        files_to_migrate = self.scan_redis_violations()
        
        if not files_to_migrate:
            print("✅ No Redis import violations found!")
            return
        
        self.migration_stats['files_scanned'] = len(files_to_migrate)
        
        # Step 2: Analyze and prioritize files  
        priority_files = []
        test_files = []
        service_files = []
        
        for file_path in files_to_migrate:
            if 'test' in file_path.lower():
                test_files.append(file_path)
            elif '/app/services/' in file_path or '/app/db/' in file_path:
                service_files.append(file_path)
            else:
                priority_files.append(file_path)
        
        # Step 3: Execute migration in priority order
        migration_order = service_files + test_files + priority_files
        
        print(f"📋 Migration Plan:")
        print(f"  ├─ Service files: {len(service_files)}")
        print(f"  ├─ Test files: {len(test_files)}")
        print(f"  └─ Other files: {len(priority_files)}")
        print()
        
        successful_migrations = 0
        
        for file_path in migration_order[:20]:  # Limit to first 20 files for Phase 1
            print(f"Processing {len(self.processed_files) + 1}/{min(20, len(migration_order))}: {file_path}")
            
            # Analyze patterns first
            patterns = self.analyze_file_patterns(file_path)
            if any(patterns.values()):
                if self.migrate_file(file_path):
                    # Validate syntax after migration
                    if self.validate_syntax(file_path):
                        successful_migrations += 1
                    else:
                        print(f"  ⚠️  Syntax validation failed - manual review needed")
            
            self.processed_files.append(file_path)
        
        # Step 4: Report results
        print("\n" + "=" * 60)
        print("📊 Redis Migration Phase 1 Results:")
        print(f"  ✅ Files scanned: {self.migration_stats['files_scanned']}")
        print(f"  ✅ Files migrated: {self.migration_stats['files_migrated']}")
        print(f"  ✅ Import statements replaced: {self.migration_stats['imports_replaced']}")
        print(f"  ✅ Usage patterns commented: {self.migration_stats['usage_patterns_updated']}")
        print(f"  ❌ Errors encountered: {self.migration_stats['errors']}")
        
        if self.errors:
            print("\n⚠️  Errors requiring attention:")
            for file_path, error in self.errors:
                print(f"  - {file_path}: {error}")
        
        # Step 5: Generate follow-up recommendations
        remaining_files = len(files_to_migrate) - len(self.processed_files)
        if remaining_files > 0:
            print(f"\n📋 Phase 2 Scope: {remaining_files} files remaining")
            print("   Next phase should focus on:")
            print("   - Manual async/await pattern updates")
            print("   - Complex Redis usage pattern migration")  
            print("   - Test validation and error resolution")
        
        return successful_migrations > 0

def main():
    """Execute Redis migration."""
    migrator = RedisMigrationExecutor()
    success = migrator.execute_migration()
    
    if success:
        print("\n🎉 Redis Migration Phase 1 completed successfully!")
        print("   Run test suite to validate changes")
        print("   Review backup files before cleanup")
    else:
        print("\n❌ Redis Migration Phase 1 encountered issues")
        print("   Review errors and apply fixes before proceeding")
        sys.exit(1)

if __name__ == "__main__":
    main()