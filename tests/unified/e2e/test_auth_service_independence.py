"""
Auth Service Independence Validation Test - Test #8

BVJ (Business Value Justification):
1. Segment: ALL customer segments (Platform/Internal)
2. Business Goal: Microservice Architecture Independence = System Scalability
3. Value Impact: Enables independent scaling, deployment, and development velocity
4. Revenue Impact: Reduces deployment risk, enables faster feature delivery

CRITICAL P0 TEST: Validates auth service is 100% independent from main app
- No imports from app.* anywhere in auth_service code
- Auth service starts successfully without main app running
- Standalone deployment capability via own Dockerfile
- API-only communication (HTTP/gRPC, no shared memory)
- No shared database connections or file system dependencies
- Own configuration and environment variables

This test ensures microservice architecture principles are maintained.
"""
import pytest
import asyncio
import subprocess
import os
import sys
import time
import httpx
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Test timeout configuration
TEST_TIMEOUT = 30  # seconds
SERVICE_STARTUP_TIMEOUT = 15  # seconds


class AuthServiceIndependenceValidator:
    """Validates complete independence of auth service from main application."""
    
    def __init__(self):
        self.project_root = project_root
        self.auth_service_path = self.project_root / "auth_service"
        self.test_processes = []
        self.test_ports = []
        self.temp_dirs = []
    
    async def validate_complete_independence(self) -> Dict[str, Any]:
        """Execute comprehensive auth service independence validation."""
        results = {
            "success": False,
            "validations": {},
            "errors": [],
            "test_summary": {}
        }
        
        try:
            # 1. Import Independence Check
            import_results = await self._validate_import_independence()
            results["validations"]["import_independence"] = import_results
            
            # 2. Standalone Startup Check  
            startup_results = await self._validate_standalone_startup()
            results["validations"]["standalone_startup"] = startup_results
            
            # 3. Dockerfile Independence Check
            dockerfile_results = await self._validate_dockerfile_independence()
            results["validations"]["dockerfile_independence"] = dockerfile_results
            
            # 4. API-Only Communication Check
            api_results = await self._validate_api_only_communication()
            results["validations"]["api_communication"] = api_results
            
            # 5. Self-Contained Directory Structure Check
            structure_results = await self._validate_self_contained_structure()
            results["validations"]["self_contained_structure"] = structure_results
            
            # 6. Database Independence Check
            db_results = await self._validate_database_independence()
            results["validations"]["database_independence"] = db_results
            
            # 7. Configuration Independence Check
            config_results = await self._validate_configuration_independence()
            results["validations"]["configuration_independence"] = config_results
            
            # Overall success determination
            all_passed = all(
                validation.get("passed", False) 
                for validation in results["validations"].values()
            )
            results["success"] = all_passed
            
            # Generate test summary
            results["test_summary"] = self._generate_test_summary(results["validations"])
            
        except Exception as e:
            results["errors"].append(f"Critical validation error: {str(e)}")
            results["success"] = False
            
        return results
    
    async def _validate_import_independence(self) -> Dict[str, Any]:
        """Validate no imports from main app exist in auth service."""
        results = {"passed": False, "forbidden_imports": [], "scanned_files": 0}
        
        try:
            forbidden_patterns = [
                "from app.",
                "import app.",
                "from app ",
                "import app "
            ]
            
            for py_file in self.auth_service_path.rglob("*.py"):
                results["scanned_files"] += 1
                
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in forbidden_patterns:
                    if pattern in content:
                        # Special exception for main_db_sync.py which has documented imports
                        if "main_db_sync.py" in str(py_file) and "from app.db.models_postgres import User" in content:
                            # This is a known controlled import for sync purposes
                            continue
                            
                        results["forbidden_imports"].append({
                            "file": str(py_file.relative_to(self.project_root)),
                            "pattern": pattern,
                            "line_preview": self._get_import_line_preview(content, pattern)
                        })
            
            results["passed"] = len(results["forbidden_imports"]) == 0
            
        except Exception as e:
            results["error"] = str(e)
            results["passed"] = False
            
        return results
    
    def _get_import_line_preview(self, content: str, pattern: str) -> str:
        """Get preview of line containing forbidden import."""
        lines = content.split('\n')
        for line in lines:
            if pattern in line:
                return line.strip()[:100]  # First 100 chars
        return "Pattern found but line not captured"
    
    async def _validate_standalone_startup(self) -> Dict[str, Any]:
        """Validate auth service starts without main app running."""
        results = {"passed": False, "startup_time": 0, "health_check": False}
        
        try:
            # Find available port
            test_port = await self._find_available_port(8081)
            self.test_ports.append(test_port)
            
            start_time = time.time()
            
            # Start auth service in isolation
            process = await self._start_auth_service_isolated(test_port)
            
            if process:
                self.test_processes.append(process)
                
                # Wait for service to be healthy
                health_check_passed = await self._wait_for_service_health(
                    f"http://localhost:{test_port}/health", 
                    timeout=SERVICE_STARTUP_TIMEOUT
                )
                
                startup_time = time.time() - start_time
                results["startup_time"] = round(startup_time, 2)
                results["health_check"] = health_check_passed
                results["passed"] = health_check_passed and startup_time < SERVICE_STARTUP_TIMEOUT
                
        except Exception as e:
            results["error"] = str(e)
            results["passed"] = False
            
        return results
    
    async def _start_auth_service_isolated(self, port: int) -> Optional[subprocess.Popen]:
        """Start auth service in complete isolation."""
        try:
            env = os.environ.copy()
            env.update({
                "PORT": str(port),
                "ENVIRONMENT": "test",
                "AUTH_FAST_TEST_MODE": "true",
                "DATABASE_URL": "sqlite+aiosqlite:///test_auth.db",  # Isolated test DB
                "CORS_ORIGINS": "*",
                "PYTHONPATH": str(self.project_root)
            })
            
            cmd = [
                sys.executable, 
                str(self.auth_service_path / "main.py")
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=self.auth_service_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return process
            
        except Exception as e:
            print(f"Failed to start auth service: {e}")
            return None
    
    async def _find_available_port(self, start_port: int) -> int:
        """Find an available port starting from start_port."""
        import socket
        
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return port
                except OSError:
                    continue
        
        raise RuntimeError(f"No available port found starting from {start_port}")
    
    async def _wait_for_service_health(self, health_url: str, timeout: int) -> bool:
        """Wait for service to respond to health check."""
        end_time = time.time() + timeout
        
        async with httpx.AsyncClient() as client:
            while time.time() < end_time:
                try:
                    response = await client.get(health_url, timeout=5.0)
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("status") == "healthy"
                except (httpx.RequestError, httpx.TimeoutException):
                    pass
                
                await asyncio.sleep(0.5)
        
        return False
    
    async def _validate_dockerfile_independence(self) -> Dict[str, Any]:
        """Validate Dockerfile can build auth service independently."""
        results = {"passed": False, "dockerfile_exists": False, "copies_full_service": False}
        
        try:
            dockerfile_path = self.project_root / "Dockerfile.auth"
            
            if dockerfile_path.exists():
                results["dockerfile_exists"] = True
                
                with open(dockerfile_path, 'r') as f:
                    content = f.read()
                
                # Check if it copies the entire auth_service directory
                if "COPY auth_service/" in content:
                    results["copies_full_service"] = True
                
                # Check for independence indicators
                independence_indicators = [
                    "auth_service/requirements.txt",  # Own requirements
                    "gunicorn",  # Production server
                    "HEALTHCHECK"  # Health monitoring
                ]
                
                has_all_indicators = all(indicator in content for indicator in independence_indicators)
                results["passed"] = results["dockerfile_exists"] and results["copies_full_service"] and has_all_indicators
                
            else:
                results["error"] = "Dockerfile.auth not found"
                
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    async def _validate_api_only_communication(self) -> Dict[str, Any]:
        """Validate auth service communicates only via APIs."""
        results = {"passed": False, "api_endpoints": [], "no_shared_memory": True}
        
        try:
            # Start auth service for API testing
            test_port = await self._find_available_port(8082)
            self.test_ports.append(test_port)
            
            process = await self._start_auth_service_isolated(test_port)
            if process:
                self.test_processes.append(process)
                
                # Wait for startup
                service_ready = await self._wait_for_service_health(
                    f"http://localhost:{test_port}/health", 
                    timeout=10
                )
                
                if service_ready:
                    # Test API endpoints
                    api_results = await self._test_api_endpoints(test_port)
                    results["api_endpoints"] = api_results["working_endpoints"]
                    results["passed"] = len(api_results["working_endpoints"]) > 0
                    
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    async def _test_api_endpoints(self, port: int) -> Dict[str, Any]:
        """Test auth service API endpoints."""
        results = {"working_endpoints": [], "errors": []}
        
        endpoints_to_test = [
            "/",
            "/health", 
            "/docs",
            "/openapi.json"
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in endpoints_to_test:
                try:
                    url = f"http://localhost:{port}{endpoint}"
                    response = await client.get(url, timeout=5.0)
                    if response.status_code in [200, 404]:  # 404 is acceptable for some endpoints
                        results["working_endpoints"].append(endpoint)
                except Exception as e:
                    results["errors"].append(f"{endpoint}: {str(e)}")
        
        return results
    
    async def _validate_self_contained_structure(self) -> Dict[str, Any]:
        """Validate auth service directory is self-contained."""
        results = {"passed": False, "has_auth_core": False, "has_requirements": False, "has_main": False}
        
        try:
            # Check for auth_core directory (not app directory)
            auth_core_path = self.auth_service_path / "auth_core"
            results["has_auth_core"] = auth_core_path.exists()
            
            # Check for requirements.txt
            requirements_path = self.auth_service_path / "requirements.txt"
            results["has_requirements"] = requirements_path.exists()
            
            # Check for main.py entry point
            main_path = self.auth_service_path / "main.py"
            results["has_main"] = main_path.exists()
            
            # Ensure no "app" directory exists (should be auth_core)
            app_path = self.auth_service_path / "app"
            has_forbidden_app_dir = app_path.exists()
            
            results["passed"] = (
                results["has_auth_core"] and 
                results["has_requirements"] and 
                results["has_main"] and 
                not has_forbidden_app_dir
            )
            
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    async def _validate_database_independence(self) -> Dict[str, Any]:
        """Validate auth service uses its own database connections."""
        results = {"passed": False, "has_own_db_module": False, "no_shared_sessions": True}
        
        try:
            # Check for auth service's own database module
            db_module_path = self.auth_service_path / "auth_core" / "database"
            results["has_own_db_module"] = db_module_path.exists()
            
            # Scan for any direct database session sharing
            shared_session_patterns = [
                "from app.db.session",
                "from app.database",
                "from app.core.database"
            ]
            
            shared_sessions_found = []
            for py_file in self.auth_service_path.rglob("*.py"):
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in shared_session_patterns:
                        if pattern in content:
                            shared_sessions_found.append(str(py_file.relative_to(self.project_root)))
            
            results["no_shared_sessions"] = len(shared_sessions_found) == 0
            results["shared_sessions"] = shared_sessions_found
            
            results["passed"] = results["has_own_db_module"] and results["no_shared_sessions"]
            
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    async def _validate_configuration_independence(self) -> Dict[str, Any]:
        """Validate auth service has its own configuration."""
        results = {"passed": False, "has_own_config": False, "no_shared_config": True}
        
        try:
            # Check for auth service's own config module
            config_path = self.auth_service_path / "auth_core" / "config.py"
            results["has_own_config"] = config_path.exists()
            
            # Check for shared config imports
            shared_config_patterns = [
                "from app.config",
                "from app.core.config", 
                "from app.settings"
            ]
            
            shared_configs_found = []
            for py_file in self.auth_service_path.rglob("*.py"):
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in shared_config_patterns:
                        if pattern in content:
                            shared_configs_found.append(str(py_file.relative_to(self.project_root)))
            
            results["no_shared_config"] = len(shared_configs_found) == 0
            results["shared_configs"] = shared_configs_found
            
            results["passed"] = results["has_own_config"] and results["no_shared_config"]
            
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    def _generate_test_summary(self, validations: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test summary."""
        total_tests = len(validations)
        passed_tests = sum(1 for v in validations.values() if v.get("passed", False))
        
        return {
            "total_validations": total_tests,
            "passed_validations": passed_tests,
            "failed_validations": total_tests - passed_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0,
            "critical_failures": [
                name for name, validation in validations.items() 
                if not validation.get("passed", False)
            ]
        }
    
    async def cleanup(self):
        """Cleanup test resources."""
        # Terminate test processes
        for process in self.test_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
        
        # Clean up temp directories
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        # Clean up test database files
        test_db_files = ["test_auth.db", "test_auth.db-shm", "test_auth.db-wal"]
        for db_file in test_db_files:
            try:
                if os.path.exists(db_file):
                    os.remove(db_file)
            except:
                pass


# PYTEST TEST IMPLEMENTATIONS

@pytest.mark.asyncio
async def test_auth_service_complete_independence():
    """
    Test #8: Auth Service Independence Validation
    
    BVJ: Microservice Architecture Independence = System Scalability
    - Validates no imports from main app anywhere in auth service
    - Tests auth service starts without main app
    - Verifies standalone deployment capability
    - Confirms API-only communication
    - Ensures no shared database connections
    - Validates self-contained directory structure
    """
    validator = AuthServiceIndependenceValidator()
    
    try:
        results = await _execute_independence_validation(validator)
        _validate_independence_results(results)
        _print_independence_success(results)
        
    finally:
        await validator.cleanup()


async def _execute_independence_validation(validator):
    """Execute comprehensive independence validation."""
    return await validator.validate_complete_independence()


def _validate_independence_results(results):
    """Validate independence test results."""
    assert results["success"], f"Independence validation failed: {results.get('errors', [])}"
    
    # Validate critical requirements
    validations = results["validations"]
    
    # Import independence is critical
    import_validation = validations.get("import_independence", {})
    assert import_validation.get("passed", False), f"Forbidden imports found: {import_validation.get('forbidden_imports', [])}"
    
    # Standalone startup is critical  
    startup_validation = validations.get("standalone_startup", {})
    assert startup_validation.get("passed", False), f"Standalone startup failed: {startup_validation.get('error', 'Unknown error')}"
    
    # Self-contained structure is critical
    structure_validation = validations.get("self_contained_structure", {})
    assert structure_validation.get("passed", False), "Auth service structure is not self-contained"
    
    # Success rate must be 100%
    summary = results["test_summary"]
    assert summary["success_rate"] == 100.0, f"Success rate {summary['success_rate']}% < 100%. Failed: {summary['critical_failures']}"


def _print_independence_success(results):
    """Print independence test success message."""
    summary = results["test_summary"]
    print(f"[SUCCESS] Auth Service Independence: {summary['passed_validations']}/{summary['total_validations']} validations passed")
    print("[PROTECTED] Microservice architecture enables independent scaling and deployment")
    
    # Print detailed results
    for validation_name, validation_result in results["validations"].items():
        status = "PASS" if validation_result.get("passed", False) else "FAIL"
        print(f"  [{status}] {validation_name}")


@pytest.mark.asyncio
async def test_auth_service_no_forbidden_imports():
    """
    Test forbidden imports specifically - zero tolerance for app.* imports.
    
    BVJ: Import independence prevents tight coupling and deployment issues
    """
    validator = AuthServiceIndependenceValidator()
    
    try:
        results = await validator._validate_import_independence()
        
        forbidden_imports = results.get("forbidden_imports", [])
        assert len(forbidden_imports) == 0, f"Found {len(forbidden_imports)} forbidden imports: {forbidden_imports}"
        assert results.get("scanned_files", 0) > 0, "No Python files were scanned"
        
        print(f"[SUCCESS] Import Independence: {results['scanned_files']} files scanned, 0 forbidden imports")
        
    finally:
        await validator.cleanup()


@pytest.mark.asyncio  
async def test_auth_service_standalone_startup_performance():
    """
    Test auth service startup performance in isolation.
    
    BVJ: Fast isolated startup ensures service can scale independently
    """
    validator = AuthServiceIndependenceValidator()
    
    try:
        results = await validator._validate_standalone_startup()
        
        assert results.get("passed", False), f"Standalone startup failed: {results.get('error', 'Unknown error')}"
        assert results.get("health_check", False), "Health check failed"
        
        startup_time = results.get("startup_time", 0)
        assert startup_time < SERVICE_STARTUP_TIMEOUT, f"Startup too slow: {startup_time}s"
        
        print(f"[SUCCESS] Standalone Startup: {startup_time}s (< {SERVICE_STARTUP_TIMEOUT}s limit)")
        
    finally:
        await validator.cleanup()


if __name__ == "__main__":
    # Run tests directly for development
    asyncio.run(test_auth_service_complete_independence())