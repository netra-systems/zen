"""
Cache warming functionality for dev launcher.

Pre-populates caches to improve startup performance.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from dev_launcher.cache_entry import TTL_PRESETS, CacheEntry, ContentHasher
except ImportError:
    from cache_entry import TTL_PRESETS, CacheEntry, ContentHasher

logger = logging.getLogger(__name__)


class CacheWarmer:
    """
    Handles cache warming operations for faster startup.
    """
    
    def __init__(self, project_root: Path, cache_manager: 'CacheManager'):
        """Initialize cache warmer."""
        self.project_root = project_root
        self.cache_manager = cache_manager
        self.max_workers = 4
    
    async def warm_all_caches(self) -> Dict[str, bool]:
        """Warm all caches asynchronously."""
        tasks = {
            'migrations': self._warm_migration_cache(),
            'dependencies': self._warm_dependency_caches(),
            'environment': self._warm_environment_cache(),
            'secrets': self._warm_secrets_cache(),
        }
        
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                logger.warning(f"Cache warming failed for {name}: {e}")
                results[name] = False
        
        return results
    
    async def _warm_migration_cache(self) -> bool:
        """Pre-warm migration cache."""
        try:
            migration_paths = self._get_migration_paths()
            content_hash = await self._async_hash_files(migration_paths)
            
            entry = CacheEntry(
                key='migration_files',
                content_hash=content_hash,
                value={'status': 'checked', 'file_count': len(migration_paths)},
                created_at=datetime.now(),
                ttl_seconds=TTL_PRESETS['permanent']
            )
            
            return self.cache_manager.set_cache_entry('migrations', entry)
            
        except Exception as e:
            logger.error(f"Migration cache warming failed: {e}")
            return False
    
    async def _warm_dependency_caches(self) -> bool:
        """Pre-warm dependency caches for all services."""
        services = ['backend', 'frontend', 'auth']
        success_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._warm_service_dependencies, service): service
                for service in services
            }
            
            for future in as_completed(futures):
                service = futures[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    logger.error(f"Dependency warming failed for {service}: {e}")
        
        return success_count == len(services)
    
    def _warm_service_dependencies(self, service: str) -> bool:
        """Warm dependency cache for specific service."""
        try:
            dep_files = self._get_dependency_files(service)
            existing_files = [f for f in dep_files if Path(f).exists()]
            
            if not existing_files:
                return True
            
            content_hash = ContentHasher.hash_multiple_files(existing_files)
            
            entry = CacheEntry(
                key=f'{service}_dependencies',
                content_hash=content_hash,
                value={
                    'status': 'checked',
                    'files': [str(f) for f in existing_files],
                    'file_count': len(existing_files)
                },
                created_at=datetime.now(),
                ttl_seconds=TTL_PRESETS['weekly']
            )
            
            return self.cache_manager.set_cache_entry(
                f'dependencies_{service}', entry
            )
            
        except Exception as e:
            logger.error(f"Service dependency warming failed for {service}: {e}")
            return False
    
    async def _warm_environment_cache(self) -> bool:
        """Pre-warm environment cache."""
        try:
            env_files = [
                self.project_root / ".env",
                self.project_root / ".env.local", 
                self.project_root / ".env.development"
            ]
            
            existing_files = [str(f) for f in env_files if f.exists()]
            content_hash = ContentHasher.hash_multiple_files(existing_files)
            
            entry = CacheEntry(
                key='environment_files',
                content_hash=content_hash,
                value={
                    'status': 'loaded',
                    'files': existing_files,
                    'file_count': len(existing_files)
                },
                created_at=datetime.now(),
                ttl_seconds=TTL_PRESETS['daily']
            )
            
            return self.cache_manager.set_cache_entry('environment', entry)
            
        except Exception as e:
            logger.error(f"Environment cache warming failed: {e}")
            return False
    
    async def _warm_secrets_cache(self) -> bool:
        """Pre-warm secrets validation cache."""
        try:
            # Only warm if secrets exist locally
            local_secret_files = [
                self.project_root / ".env",
                self.project_root / ".env.local"
            ]
            
            has_secrets = any(f.exists() for f in local_secret_files)
            if not has_secrets:
                return True
            
            content_hash = ContentHasher.hash_multiple_files([
                str(f) for f in local_secret_files if f.exists()
            ])
            
            entry = CacheEntry(
                key='secrets_validation',
                content_hash=content_hash,
                value={'status': 'validated', 'source': 'local'},
                created_at=datetime.now(),
                ttl_seconds=TTL_PRESETS['daily'],
                encrypted=True
            )
            
            return self.cache_manager.set_cache_entry('secrets', entry)
            
        except Exception as e:
            logger.error(f"Secrets cache warming failed: {e}")
            return False
    
    async def _async_hash_files(self, file_paths: List[Path]) -> str:
        """Hash files asynchronously."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            hash_tasks = [
                loop.run_in_executor(
                    executor, ContentHasher.hash_file_content, str(path)
                )
                for path in file_paths if path.exists()
            ]
            
            hashes = await asyncio.gather(*hash_tasks)
            
        combined_data = "|".join([
            f"{path.name}:{hash_val}"
            for path, hash_val in zip(file_paths, hashes)
        ])
        
        return ContentHasher.hash_content(combined_data)
    
    def _get_migration_paths(self) -> List[Path]:
        """Get migration file paths."""
        return [
            self.project_root / "alembic" / "versions",
            self.project_root / "netra_backend" / "app" / "models.py",
            self.project_root / "netra_backend" / "app" / "database.py", 
            self.project_root / "alembic.ini"
        ]
    
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