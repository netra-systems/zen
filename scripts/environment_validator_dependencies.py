"""
Dependency Validation Module
Validates Python/Node.js versions and required dependencies.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv


class DependencyValidator:
    """Dependency validation logic."""
    
    def __init__(self):
        """Initialize dependency validator."""
        # Load environment variables
        load_dotenv()
        
        self.project_root = Path(__file__).parent.parent
        self.python_requirements = self._load_python_requirements()
        self.node_requirements = self._load_node_requirements()
        
    async def validate_all_dependencies(self) -> Dict[str, Any]:
        """Validate all system dependencies."""
        results = {
            "status": "success",
            "python": {},
            "nodejs": {},
            "packages": {},
            "recommendations": []
        }
        
        await self._validate_python_environment(results)
        await self._validate_nodejs_environment(results)
        await self._validate_package_dependencies(results)
        self._update_dependency_status(results)
        
        return results
    
    def _load_python_requirements(self) -> List[str]:
        """Load Python requirements from requirements.txt."""
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            return []
        
        try:
            with open(requirements_file) as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except Exception:
            return []
    
    def _load_node_requirements(self) -> Dict[str, Any]:
        """Load Node.js requirements from package.json."""
        package_file = self.project_root / "frontend" / "package.json"
        
        if not package_file.exists():
            return {}
        
        try:
            with open(package_file) as f:
                return json.load(f)
        except Exception:
            return {}
    
    async def _validate_python_environment(self, results: Dict[str, Any]) -> None:
        """Validate Python version and environment."""
        python_result = {
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "executable": sys.executable,
            "virtual_env": sys.prefix != sys.base_prefix,
            "compatible": True,
            "installed_packages": 0
        }
        
        await self._check_python_compatibility(python_result)
        await self._count_installed_python_packages(python_result)
        
        results["python"] = python_result
    
    async def _check_python_compatibility(self, python_result: Dict[str, Any]) -> None:
        """Check Python version compatibility."""
        major, minor = sys.version_info.major, sys.version_info.minor
        
        # Netra requires Python 3.8+
        if major < 3 or (major == 3 and minor < 8):
            python_result["compatible"] = False
            python_result["error"] = f"Python {major}.{minor} not supported, requires 3.8+"
    
    async def _count_installed_python_packages(self, python_result: Dict[str, Any]) -> None:
        """Count installed Python packages."""
        try:
            result = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "list", "--format=json",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                packages = json.loads(stdout.decode())
                python_result["installed_packages"] = len(packages)
                
        except Exception:
            python_result["installed_packages"] = 0
    
    async def _validate_nodejs_environment(self, results: Dict[str, Any]) -> None:
        """Validate Node.js version and environment."""
        nodejs_result = {
            "version": None,
            "npm_version": None,
            "compatible": False,
            "frontend_deps_installed": False
        }
        
        await self._check_nodejs_version(nodejs_result)
        await self._check_npm_version(nodejs_result)
        await self._check_frontend_dependencies(nodejs_result)
        
        results["nodejs"] = nodejs_result
    
    async def _check_nodejs_version(self, nodejs_result: Dict[str, Any]) -> None:
        """Check Node.js version."""
        try:
            result = await asyncio.create_subprocess_exec(
                "node", "--version",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                version = stdout.decode().strip().lstrip('v')
                nodejs_result["version"] = version
                
                # Check compatibility (Node 18+)
                major_version = int(version.split('.')[0])
                nodejs_result["compatible"] = major_version >= 18
                
        except Exception:
            nodejs_result["version"] = None
            nodejs_result["compatible"] = False
    
    async def _check_npm_version(self, nodejs_result: Dict[str, Any]) -> None:
        """Check npm version."""
        try:
            result = await asyncio.create_subprocess_exec(
                "npm", "--version",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                nodejs_result["npm_version"] = stdout.decode().strip()
                
        except Exception:
            nodejs_result["npm_version"] = None
    
    async def _check_frontend_dependencies(self, nodejs_result: Dict[str, Any]) -> None:
        """Check if frontend dependencies are installed."""
        node_modules = self.project_root / "frontend" / "node_modules"
        package_lock = self.project_root / "frontend" / "package-lock.json"
        
        nodejs_result["frontend_deps_installed"] = (
            node_modules.exists() and 
            package_lock.exists() and
            len(list(node_modules.iterdir())) > 10  # Some packages installed
        )
    
    async def _validate_package_dependencies(self, results: Dict[str, Any]) -> None:
        """Validate package dependencies."""
        packages_result = {
            "python_requirements": len(self.python_requirements),
            "missing_python": [],
            "nodejs_dependencies": 0,
            "missing_nodejs": []
        }
        
        await self._check_critical_python_packages(packages_result)
        self._check_critical_nodejs_packages(packages_result)
        
        results["packages"] = packages_result
    
    async def _check_critical_python_packages(self, packages_result: Dict[str, Any]) -> None:
        """Check critical Python packages."""
        # Map package names to their import names
        critical_packages = {
            "fastapi": "fastapi",
            "uvicorn": "uvicorn", 
            "pydantic": "pydantic",
            "sqlalchemy": "sqlalchemy",
            "asyncpg": "asyncpg",
            "clickhouse-connect": "clickhouse_connect",
            "python-dotenv": "dotenv"
        }
        
        for package_name, import_name in critical_packages.items():
            if not await self._is_python_package_installed(import_name):
                packages_result["missing_python"].append(package_name)
    
    async def _is_python_package_installed(self, package_name: str) -> bool:
        """Check if Python package is installed."""
        try:
            result = await asyncio.create_subprocess_exec(
                sys.executable, "-c", f"import {package_name.replace('-', '_')}",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            await result.communicate()
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _check_critical_nodejs_packages(self, packages_result: Dict[str, Any]) -> None:
        """Check critical Node.js packages."""
        if not self.node_requirements:
            return
        
        dependencies = self.node_requirements.get("dependencies", {})
        dev_dependencies = self.node_requirements.get("devDependencies", {})
        
        packages_result["nodejs_dependencies"] = len(dependencies) + len(dev_dependencies)
        
        critical_packages = ["next", "react", "react-dom", "typescript"]
        
        for package in critical_packages:
            if package not in dependencies and package not in dev_dependencies:
                packages_result["missing_nodejs"].append(package)
    
    def _update_dependency_status(self, results: Dict[str, Any]) -> None:
        """Update overall dependency validation status."""
        python_ok = results["python"].get("compatible", False)
        nodejs_ok = results["nodejs"].get("compatible", False)
        missing_python = len(results["packages"].get("missing_python", []))
        missing_nodejs = len(results["packages"].get("missing_nodejs", []))
        
        if not python_ok or not nodejs_ok or missing_python > 0 or missing_nodejs > 0:
            results["status"] = "error"
            self._add_dependency_recommendations(results)
        else:
            results["status"] = "success"
            results["summary"] = "All dependencies validated"
    
    def _add_dependency_recommendations(self, results: Dict[str, Any]) -> None:
        """Add recommendations for dependency issues."""
        if not results["python"]["compatible"]:
            results["recommendations"].append("Upgrade Python to version 3.8 or higher")
        
        if not results["nodejs"]["compatible"]:
            results["recommendations"].append("Upgrade Node.js to version 18 or higher")
        
        if results["packages"]["missing_python"]:
            results["recommendations"].append("Run: pip install -r requirements.txt")
        
        if not results["nodejs"]["frontend_deps_installed"]:
            results["recommendations"].append("Run: cd frontend && npm install")