"""
Stub implementation for CacheManager to fix broken imports.
Functionality moved to cache_entry.py and cache_warmer.py.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, Union, List
from dev_launcher.cache_entry import CacheEntry, ContentHasher
from dev_launcher.cache_warmer import CacheWarmer


class CacheManager:
    """Stub for backward compatibility - use CacheEntry and CacheWarmer directly."""
    
    def __init__(self, project_root: Optional[Union[str, Path, Dict[str, Any]]] = None):
        # Handle both old-style config dict and new project_root argument
        if isinstance(project_root, dict):
            # Old-style config dict
            self.config = project_root
            self.project_root = Path(project_root.get('project_root', '.'))
        elif isinstance(project_root, (str, Path)):
            # New-style project_root argument
            self.project_root = Path(project_root)
            self.config = {}
        else:
            # Default fallback
            self.project_root = Path('.')
            self.config = {}
        
        # Initialize CacheWarmer with required arguments
        self.cache_warmer = CacheWarmer(self.project_root, self)
        self.entries = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache entry."""
        entry = self.entries.get(key)
        return entry.value if entry else None
    
    def set(self, key: str, value: Any) -> None:
        """Set cache entry."""
        # Create a simple content hash for the value
        content_hash = str(hash(str(value)))
        self.entries[key] = CacheEntry(
            key=key,
            content_hash=content_hash, 
            value=value,
            created_at=datetime.now()
        )
    
    def set_cache_entry(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry with CacheEntry object."""
        try:
            self.entries[key] = entry
            return True
        except Exception:
            return False
    
    def clear(self) -> None:
        """Clear cache."""
        self.entries.clear()
    
    async def warm_cache(self) -> None:
        """Warm cache - delegates to CacheWarmer."""
        await self.cache_warmer.warm_all_caches()
    
    def has_dependencies_changed(self, service: str) -> bool:
        """Check if dependencies have changed for a service."""
        cache_key = f"dependencies_{service}"
        cached_entry = self.entries.get(cache_key)
        
        if cached_entry is None:
            # No cache entry, assume changed
            return True
        
        if cached_entry.is_expired():
            # Cache expired, assume changed
            return True
        
        # Get current dependency files for the service
        dependency_files = self._get_dependency_files(service)
        existing_files = [str(f) for f in dependency_files if f.exists()]
        
        if not existing_files:
            # No dependency files found, not changed
            return False
        
        # Calculate current content hash
        current_hash = ContentHasher.hash_multiple_files(existing_files)
        
        # Compare with cached hash
        return current_hash != cached_entry.content_hash
    
    def has_environment_changed(self) -> bool:
        """Check if environment files have changed."""
        cache_key = "environment"
        cached_entry = self.entries.get(cache_key)
        
        if cached_entry is None:
            # No cache entry, assume changed
            return True
        
        if cached_entry.is_expired():
            # Cache expired, assume changed
            return True
        
        # Get current environment files
        env_files = [
            self.project_root / ".env",
            self.project_root / ".env.local",
            self.project_root / ".env.development"
        ]
        
        existing_files = [str(f) for f in env_files if f.exists()]
        
        if not existing_files:
            # No env files found, check if we had any cached
            cached_files = cached_entry.value.get('files', []) if isinstance(cached_entry.value, dict) else []
            return len(cached_files) > 0  # Changed if we used to have files but don't now
        
        # Calculate current content hash
        current_hash = ContentHasher.hash_multiple_files(existing_files)
        
        # Compare with cached hash
        return current_hash != cached_entry.content_hash
    
    def _get_dependency_files(self, service: str) -> List[Path]:
        """Get dependency files for service."""
        if service == "backend":
            return [
                self.project_root / "requirements.txt",
                self.project_root / "pyproject.toml"
            ]
        elif service == "frontend":
            return [
                self.project_root / "frontend" / "package.json",
                self.project_root / "frontend" / "package-lock.json"
            ]
        elif service == "auth":
            return [
                self.project_root / "auth_service" / "requirements.txt"
            ]
        return []