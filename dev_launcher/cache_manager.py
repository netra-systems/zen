"""
Simplified enhanced cache manager with modular architecture.

Main cache manager that coordinates cache operations, storage, and warming.
"""

import json
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
    from .cache_operations import CacheOperations
except ImportError:
    # Support standalone execution
    from cache_entry import (
        CacheEntry, CacheEncryption, ContentHasher, 
        CacheValidator, TTL_PRESETS
    )
    from cache_warmer import CacheWarmer
    from cache_operations import CacheOperations

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Enhanced cache manager with TTL, encryption, and warming support.
    
    Provides comprehensive caching for startup optimization with content-based
    hashing, time-to-live management, and cache warming capabilities.
    """
    
    def __init__(self, project_root: Path, cache_dir_name: str = ".dev_launcher_cache"):
        """Initialize enhanced cache manager."""
        self.project_root = project_root
        self.cache_dir = project_root / cache_dir_name
        self.cache_dir.mkdir(exist_ok=True)
        self._setup_cache_files()
        self._setup_encryption()
        self.operations = CacheOperations(project_root)
        self.warmer = CacheWarmer(project_root, self)

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

    # Delegate change detection operations
    def has_content_changed(
        self, cache_type: str, key: str, current_content: Any
    ) -> bool:
        """Check if content has changed based on hash."""
        return self.operations.has_content_changed(
            self.cache_data, cache_type, key, current_content
        )

    def has_migration_files_changed(self) -> bool:
        """Check if migration files have changed."""
        return self.operations.has_migration_files_changed(self.cache_data)

    def has_dependencies_changed(self, service_name: str) -> bool:
        """Check if service dependencies have changed."""
        return self.operations.has_dependencies_changed(
            self.cache_data, service_name
        )

    def has_environment_changed(self) -> bool:
        """Check if environment files have changed."""
        return self.operations.has_environment_changed(self.cache_data)

    async def warm_caches(self) -> Dict[str, bool]:
        """Warm all caches for faster startup."""
        return await self.warmer.warm_all_caches()

    def cache_startup_metrics(self, startup_time: float, phase_times: Dict[str, float]):
        """Cache startup performance metrics."""
        entry = self.operations.create_startup_metrics_entry(
            startup_time, phase_times
        )
        self.set_cache_entry('performance', entry)

    def get_startup_metrics(self) -> Optional[Dict[str, Any]]:
        """Get cached startup metrics."""
        return self.get_cached_value('performance', 'startup_metrics')

    def mark_successful_startup(self, startup_time: float):
        """Mark successful startup with metrics."""
        successful_runs = self._get_successful_runs() + 1
        entry = self.operations.create_startup_state_entry(
            startup_time, successful_runs
        )
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
        base_stats = self.operations.get_cache_statistics(
            self.cache_data, self.cache_files, self.cache_dir
        )
        
        # Add cache-specific stats
        base_stats.update({
            'cache_valid': self.is_cache_valid(),
            'last_startup_time': self.get_last_startup_time(),
            'successful_runs': self._get_successful_runs()
        })
        
        return base_stats

    def cleanup_expired_entries(self) -> int:
        """Remove expired cache entries and return count removed."""
        removed_count = self.operations.cleanup_expired_entries(self.cache_data)
        
        # Save updated cache files
        for cache_type, entries in self.cache_data.items():
            if cache_type in self.cache_files:
                self._save_cache_file(self.cache_files[cache_type], entries)
        
        return removed_count