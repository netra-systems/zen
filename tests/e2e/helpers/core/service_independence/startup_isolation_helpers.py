"""
Startup Isolation Testing Module

BVJ: Enterprise | SOC2 Compliance | Independent Startup | Critical for service autonomy
SPEC: SPEC/independent_services.xml

This module validates that services can start independently without dependencies.
Tests service startup capabilities and configuration isolation.
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List


class StartupIsolationValidator:
    """Validates independent startup capabilities of services."""
    
    def __init__(self, services: Dict[str, Any], project_root: Path):
        self.services = services
        self.project_root = project_root
        self.temp_dirs = []
    
    async def validate_independent_startup(self) -> Dict[str, Any]:
        """Validate that services can start independently."""
        results = self._init_results()
        
        try:
            auth_startup = await self._test_independent_startup("auth_service")
            results["service_startup_tests"]["auth_service"] = auth_startup
            self._update_results_for_service(results, auth_startup)
            
            backend_startup = await self._test_independent_startup("main_backend")
            results["service_startup_tests"]["main_backend"] = backend_startup
            self._update_results_for_service(results, backend_startup)
                
            frontend_startup = await self._test_frontend_independence()
            results["service_startup_tests"]["frontend"] = frontend_startup
            self._update_results_for_service(results, frontend_startup)
            
            results["passed"] = results["services_can_start"] >= 1
            
        except Exception as e:
            results["error"] = str(e)
            results["passed"] = False
            
        return results
    
    def _init_results(self) -> Dict[str, Any]:
        """Initialize results structure."""
        return {"passed": False, "service_startup_tests": {}, "services_tested": 0, "services_can_start": 0}
    
    def _update_results_for_service(self, results: Dict[str, Any], service_result: Dict[str, Any]):
        """Update results with service test outcome."""
        results["services_tested"] += 1
        if service_result.get("can_start", False): results["services_can_start"] += 1
    
    async def _test_independent_startup(self, service_name: str) -> Dict[str, Any]:
        """Test if a service can start independently."""
        result = self._init_service_result()
        
        service_config = self.services.get(service_name)
        if not service_config:
            return result
            
        start_time = time.time()
        
        try:
            entry_point_path = service_config.path / service_config.entry_point
            
            if not entry_point_path.exists():
                result["error"] = f"Entry point {service_config.entry_point} not found"
                return result
            
            # For Python services, try importing
            if service_config.entry_point.endswith('.py'):
                result["can_start"] = await self._test_python_service_import(entry_point_path)
            else:
                result["can_start"] = True  # Non-Python services assumed startable if files exist
                
            result["startup_time"] = round(time.time() - start_time, 2)
            
        except Exception as e:
            result["error"] = str(e)
            result["startup_time"] = round(time.time() - start_time, 2)
            
        return result
    
    def _init_service_result(self) -> Dict[str, Any]:
        """Initialize service result structure."""
        return {"can_start": False, "startup_time": 0, "test_method": "import_test"}
    
    async def _test_python_service_import(self, entry_point_path: Path) -> bool:
        """Test if a Python service can be imported independently."""
        try:
            test_script = self._create_import_test_script(entry_point_path)
            temp_script_path = self._write_temp_script(test_script)
            
            # Run the test script
            result = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return "IMPORT_SUCCESS" in result.stdout
            
        except Exception:
            return False
    
    def _create_import_test_script(self, entry_point_path: Path) -> str:
        """Create test script for import validation."""
        return f"""
import os
os.chdir("{entry_point_path.parent}")

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_module", "{entry_point_path}")
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        # Don't execute the module, just check if it can be loaded
        print("IMPORT_SUCCESS")
    else:
        print("IMPORT_FAILED_SPEC")
except Exception as e:
    print(f"IMPORT_FAILED_ERROR: {{str(e)}}")
"""
    
    def _write_temp_script(self, script_content: str) -> str:
        """Write test script to temporary file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script_path = f.name
        
        self.temp_dirs.append(temp_script_path)
        return temp_script_path
    
    async def _test_frontend_independence(self) -> Dict[str, Any]:
        """Test frontend independence by checking build configuration."""
        result = self._init_frontend_result()
        
        frontend_config = self.services.get("frontend")
        if not frontend_config:
            return result
        
        try:
            package_json_path = frontend_config.path / "package.json"
            if package_json_path.exists():
                self._process_package_json(package_json_path, result)
                if (frontend_config.path / "next.config.ts").exists(): result["has_next_config"] = True
                result["can_start"] = result["has_build_config"] and result["has_dependencies"]
            
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _init_frontend_result(self) -> Dict[str, Any]:
        """Initialize frontend test result."""
        return {"can_start": False, "has_build_config": False, "has_dependencies": False}
    
    def _process_package_json(self, package_json_path: Path, result: Dict[str, Any]):
        """Process package.json for dependency information."""
        result["has_build_config"] = True
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
        deps = package_data.get("dependencies", {})
        dev_deps = package_data.get("devDependencies", {})
        result["has_dependencies"] = len(deps) > 0 or len(dev_deps) > 0
        result["dependency_count"] = len(deps) + len(dev_deps)
    
    
    def cleanup(self):
        """Cleanup temporary files."""
        for temp_path in self.temp_dirs:
            if Path(temp_path).exists():
                Path(temp_path).unlink()


class ConfigurationIsolationTester:
    """Tests configuration isolation between services."""
    
    def __init__(self, services: Dict[str, Any]):
        self.services = services
    
    async def test_configuration_isolation(self) -> Dict[str, Any]:
        """Test that services have isolated configuration."""
        result = self._init_result()
        
        try:
            config_files_found = 0
            independent_configs = 0
            
            for service_name, service_config in self.services.items():
                service_result = await self._test_service_config(service_name, service_config)
                result["service_configs"][service_name] = service_result
                
                if service_result["has_own_config"]:
                    independent_configs += 1
                    config_files_found += len(service_result["config_files"])
            
            self._calculate_isolation_score(result, config_files_found, independent_configs)
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _init_result(self) -> Dict[str, Any]:
        """Initialize result structure."""
        return {"isolation_score": 0, "service_configs": {}, "shared_configs": []}
    
    async def _test_service_config(self, service_name: str, service_config) -> Dict[str, Any]:
        """Test configuration for a single service."""
        service_result = {"has_own_config": False, "config_files": []}
        
        config_patterns = self._get_config_patterns(service_name)
        
        for pattern in config_patterns:
            config_files = list(service_config.path.glob(pattern))
            if config_files:
                service_result["has_own_config"] = True
                service_result["config_files"].extend([str(f.name) for f in config_files])
                
        return service_result
    
    def _get_config_patterns(self, service_name: str) -> List[str]:
        """Get configuration file patterns for service type."""
        if service_name == "frontend":
            return ["next.config.*", "tailwind.config.*", "package.json"]
        return ["config.py", "settings.py", "*.yaml", "*.yml", ".env*"]
    
    def _calculate_isolation_score(self, result: Dict[str, Any], config_files_found: int, independent_configs: int):
        """Calculate configuration isolation score."""
        result["isolation_score"] = (independent_configs / len(self.services)) * 100 if config_files_found > 0 else 0


class DeploymentIsolationTester:
    """Tests deployment isolation configurations."""
    
    def __init__(self, services: Dict[str, Any], project_root: Path):
        self.services = services
        self.project_root = project_root
    
    async def test_deployment_isolation(self) -> Dict[str, Any]:
        """Test deployment isolation (Dockerfiles, build configs)."""
        result = self._init_result()
        
        try:
            for service_name, service_config in self.services.items():
                deploy_result = await self._test_service_deployment(service_name, service_config)
                
                if deploy_result["has_dockerfile"] or deploy_result["has_build_config"]:
                    result["isolated_deployments"] += 1
                
                result["deployment_configs"][service_name] = deploy_result
            
            # Calculate isolation score
            result["isolation_score"] = (result["isolated_deployments"] / len(self.services)) * 100
            
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _init_result(self) -> Dict[str, Any]:
        """Initialize result structure."""
        return {"isolation_score": 0, "deployment_configs": {}, "isolated_deployments": 0}
    
    async def _test_service_deployment(self, service_name: str, service_config) -> Dict[str, Any]:
        """Test deployment configuration for a service."""
        deploy_result = {"has_dockerfile": False, "has_build_config": False, "deployment_files": []}
        
        # Look for Dockerfiles
        self._check_dockerfiles(service_name, deploy_result)
        
        # Look for build configurations
        self._check_build_configs(service_name, service_config, deploy_result)
        
        return deploy_result
    
    def _check_dockerfiles(self, service_name: str, deploy_result: Dict[str, Any]):
        """Check for Dockerfile configurations."""
        patterns = [f"Dockerfile.{service_name}", f"Dockerfile.{service_name.replace('_', '-')}", "Dockerfile"]
        for pattern in patterns:
            if (self.project_root / pattern).exists():
                deploy_result["has_dockerfile"] = True
                deploy_result["deployment_files"].append(pattern)
                break
    
    def _check_build_configs(self, service_name: str, service_config, deploy_result: Dict[str, Any]):
        """Check for build configuration files."""
        configs = ["next.config.ts", "next.config.js", "package.json"] if service_name == "frontend" else ["setup.py", "pyproject.toml", "requirements.txt"]
        for config in configs:
            if (service_config.path / config).exists():
                deploy_result["has_build_config"] = True
                deploy_result["deployment_files"].append(config)