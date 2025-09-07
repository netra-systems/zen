from shared.isolated_environment import get_env
"""
Cypress E2E Test Runner Integration.

Provides integration of Cypress E2E tests into the unified test runner,
including service dependency management, health checks, and results aggregation.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from test_framework.cypress.service_manager import ServiceDependencyManager
from test_framework.cypress.config_manager import CypressConfigManager
from test_framework.cypress.results_processor import CypressResults
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType, ServiceStatus

logger = logging.getLogger(__name__)


@dataclass
class CypressExecutionOptions:
    """Options for Cypress test execution."""
    
    headed: bool = False
    browser: str = "chrome"
    spec_pattern: Optional[str] = None
    timeout: int = 1800  # 30 minutes default
    retries: int = 2
    parallel: bool = False
    record: bool = False
    env_vars: Dict[str, str] = None
    
    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}


class CypressTestRunner:
    """
    Cypress E2E Test Runner with service dependency management.
    
    Integrates Cypress tests into the unified test runner system with:
    - Service availability checking
    - Dynamic configuration generation  
    - Health monitoring
    - Results aggregation
    """
    
    def __init__(self, project_root: Optional[Path] = None, use_centralized_docker: bool = True):
        """
        Initialize Cypress test runner.
        
        Args:
            project_root: Root directory of the project
            use_centralized_docker: Use centralized Docker manager (default: True)
        """
        self.project_root = project_root or Path.cwd()
        self.frontend_path = self.project_root / "frontend"
        self.cypress_config_path = self.frontend_path / "cypress.config.ts"
        
        # Initialize managers
        self.use_centralized_docker = use_centralized_docker
        if use_centralized_docker:
            # Use centralized Docker manager for unified test runner integration
            self.docker_manager = UnifiedDockerManager(
                environment_type=EnvironmentType.DEDICATED,
                use_production_images=False  # Use test images for Cypress
            )
        else:
            self.docker_manager = None
            
        self.service_manager = ServiceDependencyManager(self.project_root)
        self.config_manager = CypressConfigManager(self.project_root)
        self.results_processor = CypressResults()
        
        # Execution state
        self.is_running = False
        self.current_process: Optional[subprocess.Popen] = None
        
    def validate_setup(self) -> Tuple[bool, List[str]]:
        """
        Validate Cypress test setup.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check if frontend directory exists
        if not self.frontend_path.exists():
            errors.append(f"Frontend directory not found: {self.frontend_path}")
            
        # Check if Cypress config exists
        if not self.cypress_config_path.exists():
            errors.append(f"Cypress config not found: {self.cypress_config_path}")
            
        # Check if node_modules exists (Cypress should be installed)
        node_modules_path = self.frontend_path / "node_modules"
        if not node_modules_path.exists():
            errors.append(f"Node modules not found: {node_modules_path}. Run 'npm install' in frontend directory.")
            
        # Check if Cypress is installed
        cypress_bin = node_modules_path / ".bin" / "cypress"
        cypress_exe = node_modules_path / ".bin" / "cypress.cmd"  # Windows
        if not cypress_bin.exists() and not cypress_exe.exists():
            errors.append("Cypress not installed. Run 'npm install cypress' in frontend directory.")
            
        return len(errors) == 0, errors
        
    async def ensure_services_ready(self, timeout: int = 300) -> Tuple[bool, Dict[str, Any]]:
        """
        Ensure all required services are ready for Cypress tests.
        
        Args:
            timeout: Maximum time to wait for services (seconds)
            
        Returns:
            Tuple of (all_ready, service_status)
        """
        logger.info("Checking service dependencies for Cypress tests...")
        
        # Use centralized Docker manager if available
        if self.use_centralized_docker and self.docker_manager:
            logger.info("Using centralized Docker manager for service orchestration")
            
            # Ensure Docker environment is ready
            compose_file = "docker-compose.test.yml"
            if (self.project_root / compose_file).exists():
                success = self.docker_manager.ensure_docker_compose_up(compose_file)
                if not success:
                    logger.warning("Failed to start Docker Compose services")
                    # Fall back to service manager
                else:
                    # Wait for services to be healthy
                    service_health = self.docker_manager.wait_for_services_healthy(
                        services=["backend", "frontend", "postgres", "redis"],
                        timeout=timeout
                    )
                    
                    # Convert to expected format
                    service_status = {}
                    for service, healthy in service_health.items():
                        service_status[service] = {
                            "healthy": healthy,
                            "name": service,
                            "status": "healthy" if healthy else "unhealthy"
                        }
                    
                    all_ready = all(status["healthy"] for status in service_status.values())
                    
                    if all_ready:
                        logger.info("All services ready via centralized Docker manager")
                    else:
                        logger.warning("Some services not ready via centralized Docker manager")
                        
                    return all_ready, service_status
        
        # Fall back to original service manager
        service_status = await self.service_manager.ensure_all_services_ready(timeout)
        
        all_ready = all(status.get("healthy", False) for status in service_status.values())
        
        if all_ready:
            logger.info("All services ready for Cypress tests")
        else:
            logger.warning("Some services not ready for Cypress tests")
            for service, status in service_status.items():
                if not status.get("healthy", False):
                    logger.warning(f"Service {service} not ready: {status}")
                    
        return all_ready, service_status
        
    def generate_dynamic_config(self, service_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate dynamic Cypress configuration based on service status.
        
        Args:
            service_status: Current status of all services
            
        Returns:
            Dynamic configuration for Cypress
        """
        return self.config_manager.generate_config(service_status)
        
    async def run_tests(self, options: CypressExecutionOptions) -> Tuple[bool, Dict[str, Any]]:
        """
        Run Cypress tests with the given options.
        
        Args:
            options: Cypress execution options
            
        Returns:
            Tuple of (success, results)
        """
        logger.info("Starting Cypress test execution...")
        
        # Validate setup first
        is_valid, errors = self.validate_setup()
        if not is_valid:
            return False, {
                "success": False,
                "errors": errors,
                "timestamp": datetime.now().isoformat()
            }
            
        # Ensure services are ready
        services_ready, service_status = await self.ensure_services_ready(options.timeout // 3)
        if not services_ready:
            # Get Docker status information for better error reporting
            docker_info = self.service_manager.get_docker_status_info()
            
            error_details = {
                "success": False,
                "error": "Required services not available",
                "service_status": service_status,
                "docker_info": docker_info,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add helpful message for Docker unavailability
            if not docker_info["docker_available"]:
                error_details["suggestion"] = (
                    "Docker Desktop is not running. Either start Docker Desktop to enable "
                    "automatic service containers, or ensure the following services are "
                    f"running locally: {', '.join(docker_info['docker_dependent_services'])}"
                )
            
            return False, error_details
            
        # Generate dynamic configuration
        dynamic_config = self.generate_dynamic_config(service_status)
        
        # Build Cypress command
        cmd = self._build_cypress_command(options, dynamic_config)
        
        # Execute Cypress tests
        try:
            self.is_running = True
            start_time = time.time()
            
            logger.info(f"Executing Cypress command: {' '.join(cmd)}")
            
            # Set up environment
            env = os.environ.copy()
            env.update(options.env_vars)
            env.update(dynamic_config.get("env", {}))
            
            # Run Cypress
            self.current_process = subprocess.Popen(
                cmd,
                cwd=self.frontend_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            stdout, stderr = self.current_process.communicate(timeout=options.timeout)
            return_code = self.current_process.returncode
            execution_time = time.time() - start_time
            
            # Process results
            success = return_code == 0
            results = self.results_processor.process_results(
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                options=options
            )
            
            logger.info(f"Cypress tests completed in {execution_time:.2f}s with return code {return_code}")
            
            return success, results
            
        except subprocess.TimeoutExpired:
            logger.error(f"Cypress tests timed out after {options.timeout}s")
            if self.current_process:
                self.current_process.kill()
            return False, {
                "success": False,
                "error": f"Tests timed out after {options.timeout}s",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error running Cypress tests: {e}")
            return False, {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            self.is_running = False
            self.current_process = None
            
    def _build_cypress_command(self, options: CypressExecutionOptions, config: Dict[str, Any]) -> List[str]:
        """
        Build Cypress command line arguments.
        
        Args:
            options: Cypress execution options
            config: Dynamic configuration
            
        Returns:
            Command line arguments list
        """
        cmd = ["npx", "cypress", "run"]
        
        # Browser selection
        cmd.extend(["--browser", options.browser])
        
        # Headed/headless mode
        if options.headed:
            cmd.append("--headed")
            
        # Spec pattern
        if options.spec_pattern:
            cmd.extend(["--spec", options.spec_pattern])
            
        # Parallel execution
        if options.parallel:
            cmd.append("--parallel")
            
        # Recording
        if options.record:
            cmd.append("--record")
            
        # Reporter for JSON output
        cmd.extend(["--reporter", "json"])
        
        # Config overrides from dynamic config
        config_overrides = config.get("config", {})
        for key, value in config_overrides.items():
            cmd.extend(["--config", f"{key}={value}"])
            
        return cmd
        
    def stop(self):
        """Stop currently running Cypress tests."""
        if self.is_running and self.current_process:
            logger.info("Stopping Cypress tests...")
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.current_process.kill()
            self.is_running = False
            self.current_process = None
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of Cypress test runner.
        
        Returns:
            Status information
        """
        return {
            "is_running": self.is_running,
            "has_process": self.current_process is not None,
            "frontend_path": str(self.frontend_path),
            "config_exists": self.cypress_config_path.exists()
        }
