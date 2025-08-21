"""
Simplified enhanced cache manager with modular architecture.

Main cache manager that coordinates cache operations, storage, and warming.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

try:
    from .cache_entry import (
        CacheEntry, CacheEncryption, ContentHasher, 
        CacheValidator, TTL_PRESETS
    )
    from .cache_warmer import CacheWarmer
except ImportError:
    # Support standalone execution
    from cache_entry import (
        CacheEntry, CacheEncryption, ContentHasher, 
        CacheValidator, TTL_PRESETS
    )
    from cache_warmer import CacheWarmer

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Enhanced cache manager with TTL, encryption, and warming support.
    
    Provides comprehensive caching for startup optimization with content-based
    hashing, time-to-live management, and cache warming capabilities.
    """
    
    def __init__(self, project_root: Path, cache_dir_name: str = ".dev_launcher_cache", aggressive_mode: bool = False):
        """Initialize enhanced cache manager."""
        self.project_root = project_root
        self.cache_dir = project_root / cache_dir_name
        self.cache_dir.mkdir(exist_ok=True)
        self.aggressive_mode = aggressive_mode
        self._setup_cache_files()
        self._setup_encryption()
        self.warmer = CacheWarmer(project_root, self)
        if aggressive_mode:
            self._extend_cache_ttl()

    def _setup_cache_files(self) -> None:
        """Setup cache file structure."""
        self.cache_files = {
            'state': self.cache_dir / 'state.json',
            'hashes': self.cache_dir / 'hashes.json', 
            'services': self.cache_dir / 'services.json',
            'secrets': self.cache_dir / 'secrets.json',
            'performance': self.cache_dir / 'performance.json'
        }
        self.cache_data = {}
        for name, file_path in self.cache_files.items():
            self.cache_data[name] = self._load_cache_file(file_path)
    
    def _setup_encryption(self) -> None:
        """Setup encryption for sensitive data."""
        key_file = self.cache_dir / 'encryption.key'
        if key_file.exists():
            with open(key_file, 'r') as f:
                key_string = f.read().strip()
            self.encryption = CacheEncryption.from_key_string(key_string)
        else:
            self.encryption = CacheEncryption()
            with open(key_file, 'w') as f:
                f.write(self.encryption.get_key_string())
    
    def _load_cache_file(self, cache_file: Path) -> Dict[str, CacheEntry]:
        """Load cache entries from file."""
        if not cache_file.exists():
            return {}
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return {k: CacheEntry.from_dict(v) for k, v in data.items()}
        except (json.JSONDecodeError, IOError, TypeError, ValueError):
            logger.warning(f"Invalid cache file {cache_file}, resetting")
            return {}
    
    def _save_cache_file(self, cache_file: Path, entries: Dict[str, CacheEntry]):
        """Save cache entries to file."""
        try:
            data = {k: v.to_dict() for k, v in entries.items()}
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save cache {cache_file}: {e}")

    def get_cache_entry(self, cache_type: str, key: str) -> Optional[CacheEntry]:
        """Get cache entry by type and key."""
        if cache_type not in self.cache_data:
            return None
        entry = self.cache_data[cache_type].get(key)
        if entry and CacheValidator.validate_ttl(entry):
            return entry
        return None
    
    def set_cache_entry(
        self, cache_type: str, entry: CacheEntry, encrypt: bool = False
    ) -> bool:
        """Set cache entry with optional encryption."""
        try:
            if encrypt and not entry.encrypted:
                entry.value = self.encryption.encrypt_value(entry.value)
                entry.encrypted = True
            
            if cache_type not in self.cache_data:
                self.cache_data[cache_type] = {}
            
            self.cache_data[cache_type][entry.key] = entry
            
            if cache_type in self.cache_files:
                self._save_cache_file(
                    self.cache_files[cache_type], 
                    self.cache_data[cache_type]
                )
            return True
        except Exception as e:
            logger.error(f"Failed to set cache entry: {e}")
            return False

    def get_cached_value(
        self, cache_type: str, key: str, decrypt: bool = False
    ) -> Optional[Any]:
        """Get cached value with optional decryption."""
        entry = self.get_cache_entry(cache_type, key)
        if not entry:
            return None
        
        value = entry.value
        if decrypt and entry.encrypted:
            try:
                value = self.encryption.decrypt_value(value)
            except Exception as e:
                logger.error(f"Decryption failed for {key}: {e}")
                return None
        
        return value
    
    def invalidate_cache_entry(self, cache_type: str, key: str) -> bool:
        """Invalidate specific cache entry."""
        if cache_type not in self.cache_data:
            return False
        
        if key in self.cache_data[cache_type]:
            del self.cache_data[cache_type][key]
            if cache_type in self.cache_files:
                self._save_cache_file(
                    self.cache_files[cache_type],
                    self.cache_data[cache_type]
                )
            return True
        return False

    # Core cache operations (consolidated from cache_operations.py)
    def has_content_changed(
        self, cache_type: str, key: str, current_content: Any
    ) -> bool:
        """Check if content has changed based on hash."""
        current_hash = ContentHasher.hash_content(current_content)
        
        if cache_type not in self.cache_data:
            return True
            
        entry = self.cache_data[cache_type].get(key)
        if not entry or not CacheValidator.validate_ttl(entry):
            return True
        
        return entry.content_hash != current_hash

    def has_migration_files_changed(self) -> bool:
        """Check if migration files have changed."""
        migration_paths = [
            self.project_root / "alembic" / "versions",
            self.project_root / "netra_backend" / "app" / "models.py", 
            self.project_root / "netra_backend" / "app" / "database.py",
            self.project_root / "alembic.ini"
        ]
        
        existing_paths = [str(p) for p in migration_paths if p.exists()]
        current_hash = ContentHasher.hash_multiple_files(existing_paths)
        
        return self.has_content_changed(
            'hashes', 'migrations', current_hash
        )

    def has_dependencies_changed(self, service_name: str) -> bool:
        """Check if service dependencies have changed."""
        dependency_files = self._get_dependency_files(service_name)
        existing_files = [str(f) for f in dependency_files if f.exists()]
        
        if not existing_files:
            return False
        
        current_hash = ContentHasher.hash_multiple_files(existing_files)
        cache_key = f"{service_name}_dependencies"
        
        return self.has_content_changed(
            'hashes', cache_key, current_hash
        )

    def has_environment_changed(self) -> bool:
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
            'hashes', 'environment', current_hash
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

    async def warm_caches(self) -> Dict[str, bool]:
        """Warm all caches for faster startup."""
        return await self.warmer.warm_all_caches()

    def cache_startup_metrics(self, startup_time: float, phase_times: Dict[str, float]):
        """Cache startup performance metrics."""
        entry = self._create_startup_metrics_entry(startup_time, phase_times)
        self.set_cache_entry('performance', entry)

    def get_startup_metrics(self) -> Optional[Dict[str, Any]]:
        """Get cached startup metrics."""
        return self.get_cached_value('performance', 'startup_metrics')

    def mark_successful_startup(self, startup_time: float):
        """Mark successful startup with metrics."""
        successful_runs = self._get_successful_runs() + 1
        entry = self._create_startup_state_entry(startup_time, successful_runs)
        self.set_cache_entry('state', entry)
    
    def _get_successful_runs(self) -> int:
        """Get number of successful runs."""
        last_startup = self.get_cached_value('state', 'last_startup')
        return last_startup.get('successful_runs', 0) if last_startup else 0

    def get_last_startup_time(self) -> Optional[float]:
        """Get last startup time from cache."""
        last_startup = self.get_cached_value('state', 'last_startup')
        return last_startup.get('startup_time') if last_startup else None

    def is_cache_valid(self, max_age_hours: int = 24) -> bool:
        """Check cache validity based on age."""
        last_startup = self.get_cached_value('state', 'last_startup')
        if not last_startup:
            return False
        
        try:
            timestamp = last_startup.get('timestamp')
            last_time = datetime.fromisoformat(timestamp)
            age = datetime.now() - last_time
            return age < timedelta(hours=max_age_hours)
        except (ValueError, TypeError, AttributeError):
            return False

    def is_cached_and_valid(self, key: str, max_age_hours: int = 24) -> bool:
        """Check if a specific cache key exists and is valid."""
        # Try to find the key in different cache types
        for cache_type in ['state', 'hashes', 'services', 'secrets']:
            entry = self.get_cache_entry(cache_type, key)
            if entry:
                # Check if entry is recent enough
                if hasattr(entry, 'timestamp'):
                    try:
                        entry_time = datetime.fromisoformat(entry.timestamp)
                        age = datetime.now() - entry_time
                        return age < timedelta(hours=max_age_hours)
                    except (ValueError, TypeError, AttributeError):
                        pass
                # If no timestamp, consider valid if it exists
                return True
        return False

    def cache_result(self, key: str, value: Any) -> None:
        """Cache a result with automatic timestamp."""
        # Determine the appropriate cache type based on key
        cache_type = 'state'  # Default to state
        if 'hash' in key.lower():
            cache_type = 'hashes'
        elif 'service' in key.lower():
            cache_type = 'services'
        elif 'secret' in key.lower():
            cache_type = 'secrets'
        
        # Create content hash for the value
        value_str = json.dumps(value) if not isinstance(value, str) else value
        content_hash = hashlib.md5(value_str.encode()).hexdigest()
        
        # Create a CacheEntry with proper fields
        entry = CacheEntry(
            key=key,
            content_hash=content_hash,
            value=value,
            created_at=datetime.now(),
            ttl_seconds=24 * 3600,  # 24 hours in seconds
            encrypted=False
        )
        # Set the cache entry
        self.set_cache_entry(cache_type, entry)

    def clear_cache(self, cache_type: Optional[str] = None) -> bool:
        """Clear cache data with optional type filter."""
        try:
            if cache_type:
                if cache_type in self.cache_data:
                    self.cache_data[cache_type].clear()
                    if cache_type in self.cache_files:
                        self._save_cache_file(
                            self.cache_files[cache_type],
                            self.cache_data[cache_type]
                        )
                    logger.info(f"Cache cleared for {cache_type}")
            else:
                for cache_name, entries in self.cache_data.items():
                    entries.clear()
                    if cache_name in self.cache_files:
                        self._save_cache_file(
                            self.cache_files[cache_name], entries
                        )
                logger.info("All caches cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        base_stats = self._get_cache_statistics()
        
        # Add cache-specific stats
        base_stats.update({
            'cache_valid': self.is_cache_valid(),
            'last_startup_time': self.get_last_startup_time(),
            'successful_runs': self._get_successful_runs()
        })
        
        return base_stats

    def cleanup_expired_entries(self) -> int:
        """Remove expired cache entries and return count removed."""
        removed_count = 0
        
        for cache_type, entries in self.cache_data.items():
            expired_keys = [
                key for key, entry in entries.items() if entry.is_expired()
            ]
            
            for key in expired_keys:
                del entries[key]
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired cache entries")
        
        # Save updated cache files
        for cache_type, entries in self.cache_data.items():
            if cache_type in self.cache_files:
                self._save_cache_file(self.cache_files[cache_type], entries)
        
        return removed_count
    
    def _extend_cache_ttl(self) -> None:
        """Extend TTL for aggressive caching mode."""
        for cache_type, entries in self.cache_data.items():
            for entry in entries.values():
                # Extend TTL to 7 days for aggressive mode
                entry.ttl_seconds = 7 * 24 * 3600
    
    def enable_aggressive_caching(self) -> None:
        """Enable aggressive caching mode for faster startup."""
        self.aggressive_mode = True
        self._extend_cache_ttl()
        logger.info("Aggressive caching mode enabled")
    
    def is_cache_hot(self) -> bool:
        """Check if cache is 'hot' (recently used and valid)."""
        if not self.aggressive_mode:
            return False
        return self.is_cache_valid(max_age_hours=1)  # Hot if used within 1 hour
    
    def preload_cache_keys(self, keys: List[str]) -> Dict[str, bool]:
        """Preload specific cache keys for aggressive mode."""
        results = {}
        for key in keys:
            try:
                # Check if key exists in any cache type
                found = False
                for cache_type in self.cache_data:
                    if self.get_cache_entry(cache_type, key):
                        results[key] = True
                        found = True
                        break
                if not found:
                    results[key] = False
            except Exception as e:
                logger.error(f"Failed to preload cache key {key}: {e}")
                results[key] = False
        return results
    
    def _create_startup_metrics_entry(
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

    def _create_startup_state_entry(
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

    def _get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            'cache_dir': str(self.cache_dir),
            'cache_files_exist': {
                name: file_path.exists() 
                for name, file_path in self.cache_files.items()
            },
            'cache_entry_counts': {
                cache_type: len(entries)
                for cache_type, entries in self.cache_data.items()
            }
        }
        
        # Add TTL info for cache entries
        expired_counts = {}
        for cache_type, entries in self.cache_data.items():
            expired_counts[cache_type] = sum(
                1 for entry in entries.values() if entry.is_expired()
            )
        stats['expired_entry_counts'] = expired_counts
        
        return stats