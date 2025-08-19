"""
Cache operations and utilities for enhanced cache manager.

Provides core cache operations separated from the main manager for modularity.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from .cache_entry import CacheEntry, ContentHasher, CacheValidator, TTL_PRESETS
except ImportError:
    from cache_entry import CacheEntry, ContentHasher, CacheValidator, TTL_PRESETS

logger = logging.getLogger(__name__)


class CacheOperations:
    """
    Core cache operations for the enhanced cache manager.
    """
    
    def __init__(self, project_root: Path):
        """Initialize cache operations."""
        self.project_root = project_root
    
    def has_content_changed(
        self, cache_data: Dict[str, Dict[str, CacheEntry]], 
        cache_type: str, 
        key: str, 
        current_content: Any
    ) -> bool:
        """Check if content has changed based on hash."""
        current_hash = ContentHasher.hash_content(current_content)
        
        if cache_type not in cache_data:
            return True
            
        entry = cache_data[cache_type].get(key)
        if not entry or not CacheValidator.validate_ttl(entry):
            return True
        
        return entry.content_hash != current_hash
    
    def has_migration_files_changed(
        self, cache_data: Dict[str, Dict[str, CacheEntry]]
    ) -> bool:
        """Check if migration files have changed."""
        migration_paths = [
            self.project_root / "alembic" / "versions",
            self.project_root / "app" / "models.py", 
            self.project_root / "app" / "database.py",
            self.project_root / "alembic.ini"
        ]
        
        existing_paths = [str(p) for p in migration_paths if p.exists()]
        current_hash = ContentHasher.hash_multiple_files(existing_paths)
        
        return self.has_content_changed(
            cache_data, 'hashes', 'migrations', current_hash
        )

    def has_dependencies_changed(
        self, cache_data: Dict[str, Dict[str, CacheEntry]], service_name: str
    ) -> bool:
        """Check if service dependencies have changed."""
        dependency_files = self._get_dependency_files(service_name)
        existing_files = [str(f) for f in dependency_files if f.exists()]
        
        if not existing_files:
            return False
        
        current_hash = ContentHasher.hash_multiple_files(existing_files)
        cache_key = f"{service_name}_dependencies"
        
        return self.has_content_changed(
            cache_data, 'hashes', cache_key, current_hash
        )

    def has_environment_changed(
        self, cache_data: Dict[str, Dict[str, CacheEntry]]
    ) -> bool:
        """Check if environment files have changed."""
        env_files = [
            self.project_root / ".env",
            self.project_root / ".env.local",
            self.project_root / ".env.development"
        ]
        
        existing_files = [str(f) for f in env_files if f.exists()]
        if not existing_files:
            return False
        
        current_hash = ContentHasher.hash_multiple_files(existing_files)
        return self.has_content_changed(
            cache_data, 'hashes', 'environment', current_hash
        )
    
    def _get_dependency_files(self, service_name: str) -> List[Path]:
        """Get dependency files for service."""
        if service_name == "backend":
            return [
                self.project_root / "requirements.txt",
                self.project_root / "pyproject.toml"
            ]
        elif service_name == "frontend":
            return [
                self.project_root / "frontend" / "package.json",
                self.project_root / "frontend" / "package-lock.json"
            ]
        elif service_name == "auth":
            return [
                self.project_root / "auth_service" / "requirements.txt"
            ]
        return []

    def create_startup_metrics_entry(
        self, startup_time: float, phase_times: Dict[str, float]
    ) -> CacheEntry:
        """Create cache entry for startup metrics."""
        return CacheEntry(
            key='startup_metrics',
            content_hash=ContentHasher.hash_content(str(datetime.now())),
            value={
                'startup_time': startup_time,
                'phase_times': phase_times,
                'timestamp': datetime.now().isoformat()
            },
            created_at=datetime.now(),
            ttl_seconds=TTL_PRESETS['daily']
        )

    def create_startup_state_entry(
        self, startup_time: float, successful_runs: int
    ) -> CacheEntry:
        """Create cache entry for startup state."""
        return CacheEntry(
            key='last_startup',
            content_hash=ContentHasher.hash_content(str(datetime.now())),
            value={
                'startup_time': startup_time,
                'timestamp': datetime.now().isoformat(),
                'successful_runs': successful_runs
            },
            created_at=datetime.now(),
            ttl_seconds=TTL_PRESETS['session']
        )

    def cleanup_expired_entries(
        self, cache_data: Dict[str, Dict[str, CacheEntry]]
    ) -> int:
        """Remove expired cache entries and return count removed."""
        removed_count = 0
        
        for cache_type, entries in cache_data.items():
            expired_keys = [
                key for key, entry in entries.items() if entry.is_expired()
            ]
            
            for key in expired_keys:
                del entries[key]
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired cache entries")
        
        return removed_count

    def get_cache_statistics(
        self, 
        cache_data: Dict[str, Dict[str, CacheEntry]], 
        cache_files: Dict[str, Path],
        cache_dir: Path
    ) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            'cache_dir': str(cache_dir),
            'cache_files_exist': {
                name: file_path.exists() 
                for name, file_path in cache_files.items()
            },
            'cache_entry_counts': {
                cache_type: len(entries)
                for cache_type, entries in cache_data.items()
            }
        }
        
        # Add TTL info for cache entries
        expired_counts = {}
        for cache_type, entries in cache_data.items():
            expired_counts[cache_type] = sum(
                1 for entry in entries.values() if entry.is_expired()
            )
        stats['expired_entry_counts'] = expired_counts
        
        return stats