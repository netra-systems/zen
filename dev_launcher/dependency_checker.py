"""
Asynchronous dependency checker for development launcher optimization.
"""

import os
import sys
import time
import hashlib
import asyncio
import logging
import subprocess
from typing import Dict, List, Optional, Tuple, Set, Any
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from dev_launcher.parallel_executor import ParallelExecutor, ParallelTask, TaskType

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Dependency management system type."""
    PYTHON_PIP = "pip"
    NODE_NPM = "npm" 
    NODE_YARN = "yarn"
    PYTHON_CONDA = "conda"


@dataclass
class DependencyCheckResult:
    """Result of dependency check operation."""
    dep_type: DependencyType
    service: str
    up_to_date: bool
    cached: bool
    hash_changed: bool
    install_required: bool
    duration: float = 0.0
    error: Optional[str] = None


class AsyncDependencyChecker:
    """
    Asynchronous dependency checker with smart caching.
    
    Performs parallel pip/npm dependency checks with
    file hash-based smart skip logic and background installation.
    """
    
    def __init__(self, project_root: Path, cache_dir: Optional[Path] = None):
        """Initialize async dependency checker."""
        self.project_root = Path(project_root)
        self.cache_dir = cache_dir or (self.project_root / ".dev_launcher_cache")
        self._setup_cache_dir()
        self._setup_executors()
        self._load_dependency_cache()
    
    def _setup_cache_dir(self):
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hash_file = self.cache_dir / "dependency_hashes.json"
    
    def _setup_executors(self):
        """Setup parallel executor for dependency operations."""
        self.executor = ParallelExecutor(max_cpu_workers=2, max_io_workers=6)
    
    def _load_dependency_cache(self):
        """Load cached dependency hashes."""
        import json
        self.dependency_hashes: Dict[str, str] = {}
        
        if self.hash_file.exists():
            try:
                with open(self.hash_file, 'r') as f:
                    self.dependency_hashes = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load dependency cache: {e}")
    
    def _save_dependency_cache(self):
        """Save dependency hashes to cache."""
        import json
        try:
            with open(self.hash_file, 'w') as f:
                json.dump(self.dependency_hashes, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save dependency cache: {e}")
    
    async def check_all_dependencies(self, services: List[str] = None) -> Dict[str, DependencyCheckResult]:
        """Check dependencies for all services concurrently."""
        services = services or ["auth", "backend", "frontend"]
        tasks = []
        
        # Create dependency check tasks
        for service in services:
            service_tasks = self._create_service_tasks(service)
            tasks.extend(service_tasks)
        
        # Execute all tasks in parallel
        results = self.executor.execute_all(timeout=60)
        
        # Process results into dependency check format
        return self._process_dependency_results(results)
    
    def _create_service_tasks(self, service: str) -> List[ParallelTask]:
        """Create dependency check tasks for service."""
        tasks = []
        service_path = self.project_root / service
        
        if not service_path.exists():
            return tasks
        
        # Python dependencies
        requirements_file = service_path / "requirements.txt"
        if requirements_file.exists():
            task = ParallelTask(
                task_id=f"{service}_pip_check",
                func=self._check_python_dependencies,
                args=(service, requirements_file),
                task_type=TaskType.IO_BOUND,
                timeout=30
            )
            tasks.append(task)
        
        # Node dependencies  
        package_json = service_path / "package.json"
        if package_json.exists():
            task = ParallelTask(
                task_id=f"{service}_npm_check", 
                func=self._check_node_dependencies,
                args=(service, package_json),
                task_type=TaskType.IO_BOUND,
                timeout=45
            )
            tasks.append(task)
        
        return tasks
    
    def _check_python_dependencies(self, service: str, requirements_file: Path) -> DependencyCheckResult:
        """Check Python pip dependencies."""
        start_time = time.time()
        
        # Calculate file hash
        current_hash = self._calculate_file_hash(requirements_file)
        cache_key = f"{service}_pip"
        cached_hash = self.dependency_hashes.get(cache_key)
        
        result = DependencyCheckResult(
            dep_type=DependencyType.PYTHON_PIP,
            service=service,
            up_to_date=False,
            cached=cached_hash is not None,
            hash_changed=current_hash != cached_hash,
            install_required=False
        )
        
        try:
            # Check if hash changed
            if current_hash == cached_hash:
                result.up_to_date = True
                result.duration = time.time() - start_time
                return result
            
            # Check if packages are installed
            install_required = self._pip_install_required(service, requirements_file)
            result.install_required = install_required
            result.up_to_date = not install_required
            
            # Update hash cache
            if not install_required:
                self.dependency_hashes[cache_key] = current_hash
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Python dependency check failed for {service}: {e}")
        
        result.duration = time.time() - start_time
        return result
    
    def _check_node_dependencies(self, service: str, package_json: Path) -> DependencyCheckResult:
        """Check Node npm dependencies.""" 
        start_time = time.time()
        
        # Use package-lock.json for more accurate caching
        lock_file = package_json.parent / "package-lock.json"
        target_file = lock_file if lock_file.exists() else package_json
        
        current_hash = self._calculate_file_hash(target_file)
        cache_key = f"{service}_npm"
        cached_hash = self.dependency_hashes.get(cache_key)
        
        result = DependencyCheckResult(
            dep_type=DependencyType.NODE_NPM,
            service=service,
            up_to_date=False,
            cached=cached_hash is not None,
            hash_changed=current_hash != cached_hash,
            install_required=False
        )
        
        try:
            if current_hash == cached_hash:
                result.up_to_date = True
                result.duration = time.time() - start_time
                return result
            
            # Check node_modules directory
            node_modules = package_json.parent / "node_modules"
            install_required = not node_modules.exists() or self._npm_install_required(package_json)
            
            result.install_required = install_required
            result.up_to_date = not install_required
            
            if not install_required:
                self.dependency_hashes[cache_key] = current_hash
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Node dependency check failed for {service}: {e}")
        
        result.duration = time.time() - start_time
        return result
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file contents."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash {file_path}: {e}")
            return ""
    
    def _pip_install_required(self, service: str, requirements_file: Path) -> bool:
        """Check if pip install is required."""
        try:
            # Try pip check command for fast validation
            cmd = [sys.executable, "-m", "pip", "check"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, 
                timeout=10, cwd=requirements_file.parent
            )
            
            # If pip check passes, dependencies are satisfied
            if result.returncode == 0:
                return False
            
            # Fallback: check if requirements can be imported
            return self._test_import_requirements(requirements_file)
            
        except Exception as e:
            logger.warning(f"Pip check failed for {service}: {e}")
            return True
    
    def _test_import_requirements(self, requirements_file: Path) -> bool:
        """Test if requirements can be imported."""
        try:
            with open(requirements_file, 'r') as f:
                lines = f.readlines()
            
            # Extract package names (simple parsing)
            packages = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    pkg = line.split('==')[0].split('>=')[0].split('<=')[0]
                    packages.append(pkg.strip())
            
            # Test a few key packages
            test_packages = packages[:5]  # Only test first 5 to be fast
            for pkg in test_packages:
                try:
                    __import__(pkg.replace('-', '_'))
                except ImportError:
                    return True  # Install required
            
            return False  # All tested packages available
            
        except Exception:
            return True  # Install required on error
    
    def _npm_install_required(self, package_json: Path) -> bool:
        """Check if npm install is required."""
        try:
            # Quick check: verify package-lock.json exists
            lock_file = package_json.parent / "package-lock.json"
            if not lock_file.exists():
                return True
            
            # Check if node_modules matches package-lock.json timestamp
            node_modules = package_json.parent / "node_modules"
            if not node_modules.exists():
                return True
            
            # Compare modification times
            lock_mtime = lock_file.stat().st_mtime
            modules_mtime = node_modules.stat().st_mtime
            
            return lock_mtime > modules_mtime
            
        except Exception:
            return True  # Install required on error
    
    def _process_dependency_results(self, results: Dict[str, Any]) -> Dict[str, DependencyCheckResult]:
        """Process parallel execution results into dependency results."""
        dependency_results = {}
        
        for task_id, result in results.items():
            if result.success and isinstance(result.result, DependencyCheckResult):
                dependency_results[task_id] = result.result
            else:
                # Create error result
                service = task_id.split('_')[0]
                dep_type = DependencyType.PYTHON_PIP if 'pip' in task_id else DependencyType.NODE_NPM
                
                dependency_results[task_id] = DependencyCheckResult(
                    dep_type=dep_type,
                    service=service,
                    up_to_date=False,
                    cached=False,
                    hash_changed=True,
                    install_required=True,
                    error=str(result.error) if result.error else "Unknown error"
                )
        
        return dependency_results
    
    async def install_dependencies_background(self, check_results: Dict[str, DependencyCheckResult]) -> Dict[str, bool]:
        """Install required dependencies in background."""
        install_tasks = []
        
        for task_id, result in check_results.items():
            if result.install_required:
                task = ParallelTask(
                    task_id=f"{task_id}_install",
                    func=self._install_dependency,
                    args=(result,),
                    task_type=TaskType.IO_BOUND,
                    timeout=120
                )
                install_tasks.append(task)
        
        # Execute installation tasks
        install_executor = ParallelExecutor(max_cpu_workers=1, max_io_workers=3)
        for task in install_tasks:
            install_executor.add_task(task)
        
        install_results = install_executor.execute_all(timeout=180)
        
        # Process install results
        success_map = {}
        for task_id, result in install_results.items():
            original_task = task_id.replace('_install', '')
            success_map[original_task] = result.success
        
        return success_map
    
    def _install_dependency(self, check_result: DependencyCheckResult) -> bool:
        """Install single dependency."""
        try:
            service_path = self.project_root / check_result.service
            
            if check_result.dep_type == DependencyType.PYTHON_PIP:
                return self._install_pip_dependencies(service_path)
            elif check_result.dep_type == DependencyType.NODE_NPM:
                return self._install_npm_dependencies(service_path)
            
            return False
            
        except Exception as e:
            logger.error(f"Dependency install failed for {check_result.service}: {e}")
            return False
    
    def _install_pip_dependencies(self, service_path: Path) -> bool:
        """Install pip dependencies."""
        requirements_file = service_path / "requirements.txt"
        
        cmd = [
            sys.executable, "-m", "pip", "install", 
            "-r", str(requirements_file),
            "--quiet", "--disable-pip-version-check"
        ]
        
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=120, cwd=service_path
        )
        
        return result.returncode == 0
    
    def _install_npm_dependencies(self, service_path: Path) -> bool:
        """Install npm dependencies."""
        # Use npm ci for faster, more reliable installs
        cmd = ["npm", "ci", "--silent", "--no-progress"]
        
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=180, cwd=service_path
        )
        
        return result.returncode == 0
    
    def cleanup(self):
        """Cleanup resources and save cache."""
        self._save_dependency_cache()
        if hasattr(self, 'executor'):
            self.executor.cleanup()
    
    def check_and_install_all_parallel(self, services: List[str] = None) -> bool:
        """Check and install dependencies for all services in parallel."""
        import asyncio
        return asyncio.run(self._async_check_and_install_all(services))
    
    async def _async_check_and_install_all(self, services: List[str] = None) -> bool:
        """Async implementation of check and install all."""
        check_results = await self.check_all_dependencies(services)
        install_results = await self.install_dependencies_background(check_results)
        return all(install_results.values())
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get dependency cache statistics."""
        return {
            "cached_dependencies": len(self.dependency_hashes),
            "cache_file": str(self.hash_file),
            "cache_size": self.hash_file.stat().st_size if self.hash_file.exists() else 0
        }


def create_dependency_checker(project_root: Path) -> AsyncDependencyChecker:
    """Factory function to create dependency checker."""
    return AsyncDependencyChecker(project_root)