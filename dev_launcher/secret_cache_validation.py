"""
Secret cache validation with fast sub-100ms checks.

Provides validation caching and invalidation logic for secret cache.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

try:
    from dev_launcher.cache_entry import CacheEntry, ContentHasher
    from dev_launcher.cache_manager import CacheManager
except ImportError:
    # Support standalone execution
    from cache_entry import CacheEntry, ContentHasher
    from cache_manager import CacheManager

logger = logging.getLogger(__name__)


class SecretValidationCache:
    """Fast secret validation with encrypted caching."""
    
    def __init__(self, cache_manager: CacheManager, project_root: Path):
        """Initialize secret validation cache."""
        self.cache_manager = cache_manager
        self.project_root = project_root
        self.validation_ttl = 24 * 3600  # 24 hours
    
    def get_cached_validation(
        self, secrets_hash: str, env_files_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached validation result if still valid (<100ms)."""
        start_time = datetime.now()
        
        cache_key = self._generate_validation_key(secrets_hash, env_files_hash)
        cached_result = self.cache_manager.get_cached_value(
            'secrets', cache_key, decrypt=True
        )
        
        validation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if cached_result and validation_time < 100:  # Sub-100ms requirement
            logger.debug(f"  [CACHE] Validation hit in {validation_time:.1f}ms")
            return cached_result
        
        if validation_time >= 100:
            logger.debug(f"  [SLOW] Cache validation took {validation_time:.1f}ms")
        
        return None
    
    def cache_validation_result(
        self,
        secrets_hash: str,
        env_files_hash: str,
        validation_result: Dict[str, Any],
        secrets_metadata: Dict[str, str]
    ) -> bool:
        """Cache validation result with encryption."""
        cache_key = self._generate_validation_key(secrets_hash, env_files_hash)
        
        cache_data = {
            'validation_result': validation_result,
            'secrets_metadata': secrets_metadata,
            'cached_at': datetime.now().isoformat(),
            'env_files_hash': env_files_hash,
            'secrets_hash': secrets_hash
        }
        
        # Create cache entry with 24-hour TTL
        entry = CacheEntry(
            key=cache_key,
            content_hash=secrets_hash,
            value=cache_data,
            created_at=datetime.now(),
            ttl_seconds=self.validation_ttl,
            encrypted=False  # Will be encrypted when stored
        )
        
        success = self.cache_manager.set_cache_entry('secrets', entry, encrypt=True)
        
        if success:
            logger.debug(f"  [CACHED] Validation result for 24h")
        
        return success
    
    def _generate_validation_key(self, secrets_hash: str, env_files_hash: str) -> str:
        """Generate cache key for validation result."""
        combined = f"{secrets_hash}:{env_files_hash}"
        return f"validation_{ContentHasher.hash_content(combined)[:16]}"
    
    def invalidate_on_file_changes(self) -> int:
        """Invalidate cache entries when env files change."""
        current_env_hash = self._get_current_env_files_hash()
        
        # Get all cached validations
        secrets_cache = self.cache_manager.cache_data.get('secrets', {})
        invalidated_count = 0
        
        keys_to_remove = []
        for key, entry in secrets_cache.items():
            if key.startswith('validation_'):
                try:
                    cached_data = self.cache_manager.get_cached_value(
                        'secrets', key, decrypt=True
                    )
                    if cached_data:
                        cached_env_hash = cached_data.get('env_files_hash', '')
                        if cached_env_hash != current_env_hash:
                            keys_to_remove.append(key)
                            invalidated_count += 1
                except Exception as e:
                    logger.debug(f"Error checking cache entry {key}: {e}")
                    keys_to_remove.append(key)
        
        # Remove invalidated entries
        for key in keys_to_remove:
            self.cache_manager.invalidate_cache_entry('secrets', key)
        
        if invalidated_count > 0:
            logger.info(f"  [INVALIDATED] {invalidated_count} cached validations due to file changes")
        
        return invalidated_count
    
    def _get_current_env_files_hash(self) -> str:
        """Get hash of current env files."""
        env_files = [
            self.project_root / '.env',
            self.project_root / '.env.local'
        ]
        
        existing_files = [str(f) for f in env_files if f.exists()]
        
        if not existing_files:
            return "no_env_files"
        
        return ContentHasher.hash_multiple_files(existing_files)