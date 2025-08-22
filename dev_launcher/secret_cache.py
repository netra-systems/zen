"""
Encrypted secret cache with 24-hour TTL and fast validation.

Main secret cache orchestrator with encrypted storage and sub-100ms validation.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

try:
    from dev_launcher.cache_entry import CacheEntry, ContentHasher
    from dev_launcher.cache_manager import CacheManager
    from dev_launcher.secret_cache_validation import SecretValidationCache
except ImportError:
    # Support standalone execution
    from cache_entry import CacheEntry, ContentHasher
    from cache_manager import CacheManager
    from secret_cache_validation import SecretValidationCache

logger = logging.getLogger(__name__)


class SecretCache:
    """
    Encrypted secret storage with 24-hour TTL and fast validation.
    
    Provides sub-100ms validation checks for cached secrets with automatic
    invalidation on file changes.
    """
    
    def __init__(self, project_root: Path, cache_manager: Optional[CacheManager] = None):
        """Initialize secret cache."""
        self.project_root = project_root
        self.cache_manager = cache_manager or CacheManager(project_root)
        self.validation_cache = SecretValidationCache(self.cache_manager, project_root)
        self.secret_ttl = 24 * 3600  # 24 hours
    
    def cache_secrets(
        self, 
        secrets: Dict[str, str], 
        validation_result: Dict[str, Any],
        source_metadata: Dict[str, str]
    ) -> bool:
        """Cache secrets with validation result."""
        logger.info("\n[SECRET CACHE] Caching validated secrets...")
        
        # Generate hashes
        secrets_hash = self._generate_secrets_hash(secrets)
        env_files_hash = self._get_env_files_hash()
        
        # Cache individual secrets
        cached_count = self._cache_individual_secrets(secrets, source_metadata)
        
        # Cache validation result
        validation_cached = self.validation_cache.cache_validation_result(
            secrets_hash, env_files_hash, validation_result, source_metadata
        )
        
        if cached_count > 0 and validation_cached:
            logger.info(f"  [OK] Cached {cached_count} secrets with validation")
            return True
        
        return False
    
    def get_cached_secrets(self, required_keys: Set[str]) -> Optional[Dict[str, str]]:
        """Get cached secrets if valid and complete."""
        logger.debug("\n[SECRET CACHE] Checking cached secrets...")
        
        # Check if we have a valid cached validation
        secrets_hash = self._generate_secrets_hash_from_cache(required_keys)
        env_files_hash = self._get_env_files_hash()
        
        cached_validation = self.validation_cache.get_cached_validation(
            secrets_hash, env_files_hash
        )
        
        if not cached_validation:
            logger.debug("  [MISS] No valid cached validation")
            return None
        
        # Get individual cached secrets
        cached_secrets = self._get_cached_individual_secrets(required_keys)
        
        if cached_secrets and len(cached_secrets) == len(required_keys):
            logger.debug(f"  [HIT] All {len(required_keys)} secrets cached and valid")
            return cached_secrets
        
        logger.debug(f"  [PARTIAL] Only {len(cached_secrets or {})} of {len(required_keys)} secrets cached")
        return None
    
    def validate_cached_secrets(self, required_keys: Set[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Fast validation of cached secrets (<100ms)."""
        start_time = datetime.now()
        
        # Get env file hash for comparison
        current_env_hash = self._get_env_files_hash()
        
        # Try to get cached validation
        secrets_hash = self._generate_secrets_hash_from_cache(required_keys)
        cached_validation = self.validation_cache.get_cached_validation(
            secrets_hash, current_env_hash
        )
        
        validation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if cached_validation:
            logger.debug(f"  [FAST] Validation completed in {validation_time:.1f}ms")
            return True, cached_validation['validation_result']
        
        logger.debug(f"  [MISS] Cache validation miss in {validation_time:.1f}ms")
        return False, None
    
    def invalidate_on_changes(self) -> int:
        """Invalidate cache when env files change."""
        logger.debug("\n[SECRET CACHE] Checking for invalidation...")
        
        # Invalidate validation cache
        validation_invalidated = self.validation_cache.invalidate_on_file_changes()
        
        # Individual secret cache doesn't need separate invalidation
        # since they're tied to validation cache results
        
        if validation_invalidated > 0:
            logger.info(f"  [INVALIDATED] {validation_invalidated} cache entries due to changes")
        
        return validation_invalidated
    
    def _cache_individual_secrets(
        self, secrets: Dict[str, str], source_metadata: Dict[str, str]
    ) -> int:
        """Cache individual secrets with metadata."""
        cached_count = 0
        
        for key, value in secrets.items():
            cache_key = f"secret_{key.lower()}"
            
            cache_data = {
                'value': value,
                'source': source_metadata.get(key, 'unknown'),
                'cached_at': datetime.now().isoformat()
            }
            
            entry = CacheEntry(
                key=cache_key,
                content_hash=ContentHasher.hash_content(value),
                value=cache_data,
                created_at=datetime.now(),
                ttl_seconds=self.secret_ttl,
                encrypted=False  # Will be encrypted when stored
            )
            
            if self.cache_manager.set_cache_entry('secrets', entry, encrypt=True):
                cached_count += 1
            else:
                logger.debug(f"  [WARN] Failed to cache {key}")
        
        return cached_count
    
    def _get_cached_individual_secrets(self, required_keys: Set[str]) -> Optional[Dict[str, str]]:
        """Get cached individual secrets."""
        cached_secrets = {}
        
        for key in required_keys:
            cache_key = f"secret_{key.lower()}"
            cached_data = self.cache_manager.get_cached_value(
                'secrets', cache_key, decrypt=True
            )
            
            if cached_data:
                cached_secrets[key] = cached_data['value']
        
        return cached_secrets if cached_secrets else None
    
    def _generate_secrets_hash(self, secrets: Dict[str, str]) -> str:
        """Generate hash of secrets for cache key."""
        # Sort keys for consistent hashing
        sorted_items = sorted(secrets.items())
        content = json.dumps(sorted_items, sort_keys=True)
        return ContentHasher.hash_content(content)
    
    def _generate_secrets_hash_from_cache(self, required_keys: Set[str]) -> str:
        """Generate secrets hash from cached values."""
        cached_secrets = {}
        
        for key in required_keys:
            cache_key = f"secret_{key.lower()}"
            cached_data = self.cache_manager.get_cached_value(
                'secrets', cache_key, decrypt=True
            )
            if cached_data:
                cached_secrets[key] = cached_data['value']
        
        if len(cached_secrets) == len(required_keys):
            return self._generate_secrets_hash(cached_secrets)
        
        return "incomplete_cache"
    
    def _get_env_files_hash(self) -> str:
        """Get hash of environment files."""
        return self.validation_cache._get_current_env_files_hash()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        secrets_cache = self.cache_manager.cache_data.get('secrets', {})
        
        validation_entries = sum(1 for k in secrets_cache.keys() if k.startswith('validation_'))
        secret_entries = sum(1 for k in secrets_cache.keys() if k.startswith('secret_'))
        
        return {
            'validation_entries': validation_entries,
            'secret_entries': secret_entries,
            'total_entries': len(secrets_cache),
            'env_files_hash': self._get_env_files_hash()
        }
    
    def clear_cache(self) -> bool:
        """Clear all secret cache data."""
        return self.cache_manager.clear_cache('secrets')