"""
Startup state and file hash caching component.

Provides intelligent caching to skip unnecessary steps during development
launcher startup when files haven't changed.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages startup state and file hash caching for development environment.
    
    Tracks file changes, dependency states, and startup status to optimize
    subsequent launcher runs by skipping unchanged components.
    """
    
    def __init__(self, project_root: Path, cache_dir_name: str = ".dev_launcher_cache"):
        """Initialize cache manager."""
        self.project_root = project_root
        self.cache_dir = project_root / cache_dir_name
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "startup_cache.json"
        self.migration_cache_file = self.cache_dir / "migration_cache.json"
        self.dependency_cache_file = self.cache_dir / "dependency_cache.json"
        self.cache_data = self._load_cache_file(self.cache_file)
        self.migration_cache = self._load_cache_file(self.migration_cache_file)
        self.dependency_cache = self._load_cache_file(self.dependency_cache_file)
    
    def _load_cache_file(self, cache_file: Path) -> Dict[str, Any]:
        """Load cache data from specific file."""
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning(f"Invalid cache file {cache_file}, resetting")
        return {}
    
    def _save_cache_file(self, cache_file: Path, data: Dict[str, Any]):
        """Save cache data to specific file."""
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save cache {cache_file}: {e}")
    
    def get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file contents."""
        if not file_path.exists():
            return ""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except IOError:
            return ""
    
    def get_directory_hash(self, directory: Path, patterns: List[str]) -> str:
        """Calculate combined hash of files in directory matching patterns."""
        if not directory.exists():
            return ""
        
        file_hashes = []
        for pattern in patterns:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    file_hashes.append(f"{file_path.name}:{self.get_file_hash(file_path)}")
        
        # Sort for consistent ordering
        file_hashes.sort()
        combined = "\n".join(file_hashes)
        return hashlib.md5(combined.encode()).hexdigest()
    
    def has_migration_files_changed(self) -> bool:
        """Check if database migration files have changed."""
        migration_paths = [
            self.project_root / "alembic" / "versions",
            self.project_root / "app" / "models.py",
            self.project_root / "app" / "database.py",
            self.project_root / "alembic.ini"
        ]
        
        current_hash = self._calculate_migration_hash(migration_paths)
        cached_hash = self.migration_cache.get("migration_files_hash", "")
        
        if current_hash != cached_hash:
            self.migration_cache["migration_files_hash"] = current_hash
            self.migration_cache["last_checked"] = datetime.now().isoformat()
            self._save_cache_file(self.migration_cache_file, self.migration_cache)
            return True
        
        return False
    
    def _calculate_migration_hash(self, paths: List[Path]) -> str:
        """Calculate combined hash of migration-related files."""
        hashes = []
        for path in paths:
            if path.is_file():
                hashes.append(self.get_file_hash(path))
            elif path.is_dir():
                hashes.append(self.get_directory_hash(path, ["*.py", "*.ini"]))
        
        combined = "|".join(hashes)
        return hashlib.md5(combined.encode()).hexdigest()
    
    def has_dependencies_changed(self, service_name: str) -> bool:
        """Check if dependencies have changed for a service."""
        dependency_files = self._get_dependency_files(service_name)
        current_hash = self._calculate_dependency_hash(dependency_files)
        cache_key = f"{service_name}_dependencies_hash"
        cached_hash = self.dependency_cache.get(cache_key, "")
        
        if current_hash != cached_hash:
            self.dependency_cache[cache_key] = current_hash
            self.dependency_cache[f"{service_name}_last_checked"] = datetime.now().isoformat()
            self._save_cache_file(self.dependency_cache_file, self.dependency_cache)
            return True
        
        return False
    
    def _get_dependency_files(self, service_name: str) -> List[Path]:
        """Get dependency files for a service."""
        if service_name == "backend":
            return [
                self.project_root / "requirements.txt",
                self.project_root / "pyproject.toml",
                self.project_root / "Pipfile"
            ]
        elif service_name == "frontend":
            return [
                self.project_root / "frontend" / "package.json",
                self.project_root / "frontend" / "package-lock.json",
                self.project_root / "frontend" / "yarn.lock"
            ]
        elif service_name == "auth":
            return [
                self.project_root / "auth_service" / "requirements.txt",
                self.project_root / "auth_service" / "pyproject.toml"
            ]
        return []
    
    def _calculate_dependency_hash(self, files: List[Path]) -> str:
        """Calculate combined hash of dependency files."""
        hashes = []
        for file_path in files:
            if file_path.exists():
                hashes.append(self.get_file_hash(file_path))
        
        combined = "|".join(hashes)
        return hashlib.md5(combined.encode()).hexdigest()
    
    def has_environment_changed(self) -> bool:
        """Check if environment configuration has changed."""
        env_files = [
            self.project_root / ".env",
            self.project_root / ".env.local",
            self.project_root / ".env.development"
        ]
        
        current_hash = self._calculate_dependency_hash(env_files)
        cached_hash = self.cache_data.get("environment_hash", "")
        
        if current_hash != cached_hash:
            self.cache_data["environment_hash"] = current_hash
            self.cache_data["env_last_checked"] = datetime.now().isoformat()
            self._save_cache_file(self.cache_file, self.cache_data)
            return True
        
        return False
    
    def mark_successful_startup(self, startup_time: float):
        """Mark a successful startup with timing information."""
        self.cache_data.update({
            "last_successful_startup": datetime.now().isoformat(),
            "last_startup_time": startup_time,
            "successful_runs": self.cache_data.get("successful_runs", 0) + 1
        })
        self._save_cache_file(self.cache_file, self.cache_data)
    
    def get_last_startup_time(self) -> Optional[float]:
        """Get the last recorded startup time."""
        return self.cache_data.get("last_startup_time")
    
    def is_cache_valid(self, max_age_hours: int = 24) -> bool:
        """Check if the cache is still valid based on age."""
        last_startup = self.cache_data.get("last_successful_startup")
        if not last_startup:
            return False
        
        try:
            last_time = datetime.fromisoformat(last_startup)
            age = datetime.now() - last_time
            return age < timedelta(hours=max_age_hours)
        except (ValueError, TypeError):
            return False
    
    def clear_cache(self):
        """Clear all cache data."""
        self.cache_data.clear()
        self.migration_cache.clear()
        self.dependency_cache.clear()
        self._save_cache_file(self.cache_file, self.cache_data)
        self._save_cache_file(self.migration_cache_file, self.migration_cache)
        self._save_cache_file(self.dependency_cache_file, self.dependency_cache)
        logger.info("Cache cleared successfully")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for debugging."""
        return {
            "cache_dir": str(self.cache_dir),
            "cache_files_exist": {
                "startup": self.cache_file.exists(),
                "migration": self.migration_cache_file.exists(),
                "dependency": self.dependency_cache_file.exists()
            },
            "last_successful_startup": self.cache_data.get("last_successful_startup"),
            "successful_runs": self.cache_data.get("successful_runs", 0),
            "cache_valid": self.is_cache_valid()
        }