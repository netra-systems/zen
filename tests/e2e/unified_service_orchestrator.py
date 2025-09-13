"""

Unified Service Orchestrator - E2E Service Management (SSOT Compliant)



This is the Single Source of Truth (SSOT) wrapper for E2E service orchestration.

Uses UnifiedDockerManager as the core engine for all Docker operations.



Business Value Justification (BVJ):

1. Segment: Platform/Internal - Development Velocity, Risk Reduction

2. Business Goal: Eliminate E2E test infrastructure fragmentation

3. Value Impact: Reduces Docker-related test failures, improves reliability

4. Revenue Impact: Protects development velocity and CI/CD pipeline stability

"""

import asyncio

import logging

from pathlib import Path

from typing import Any, Dict, List, Optional



# SSOT import - all Docker operations go through UnifiedDockerManager

from test_framework.unified_docker_manager import UnifiedDockerManager, ServiceMode, EnvironmentType



# E2E testing specific imports

from tests.e2e.database_test_connections import DatabaseConnectionManager

from tests.e2e.real_services_manager import RealServicesManager

from tests.e2e.test_environment_config import TestEnvironmentConfig



logger = logging.getLogger(__name__)





class UnifiedServiceOrchestrator:

    """

    SSOT Service Orchestrator for E2E testing using UnifiedDockerManager.

    

    This replaces all duplicate ServiceOrchestrator implementations

    with a single, consistent interface backed by UnifiedDockerManager.

    """

    

    def __init__(self, 

                 project_root: Optional[Path] = None, 

                 env_config: Optional[TestEnvironmentConfig] = None,

                 service_mode: ServiceMode = ServiceMode.DOCKER,

                 environment_type: EnvironmentType = EnvironmentType.DEDICATED):

        """

        Initialize unified service orchestrator.

        

        Args:

            project_root: Optional project root path

            env_config: Environment configuration for environment-aware service management

            service_mode: Service execution mode (DOCKER/LOCAL/MOCK)

            environment_type: Environment isolation type

        """

        self.project_root = project_root or self._detect_project_root()

        self.env_config = env_config

        self.service_mode = service_mode

        self.environment_type = environment_type

        self.ready = False

        

        # Core SSOT Docker manager

        self.docker_manager = UnifiedDockerManager(

            environment="e2e-test",

            environment_type=environment_type

        )

        

        # Legacy compatibility managers (will be phased out)

        self.services_manager = RealServicesManager(self.project_root, env_config)

        self.db_manager = DatabaseConnectionManager(env_config)

        

    def _detect_project_root(self) -> Path:

        """Detect project root directory."""

        current = Path(__file__).parent

        while current.parent != current:

            if (current / "app").exists() or (current / "netra_backend").exists():

                return current

            current = current.parent

        raise RuntimeError("Cannot detect project root")

    

    async def start_test_environment(self, 

                                   db_name: Optional[str] = None, 

                                   services: Optional[List[str]] = None) -> None:

        """

        Start complete test environment using UnifiedDockerManager.

        

        Args:

            db_name: Database name for testing

            services: Specific services to start, None for all

        """

        logger.info("Starting E2E test environment with UnifiedDockerManager")

        

        try:

            # Get effective service mode based on Docker availability

            effective_mode = self.docker_manager.get_effective_mode(self.service_mode)

            

            if effective_mode == ServiceMode.MOCK:

                logger.info("Using mock mode for E2E tests")

                self.ready = True

                return

                

            elif effective_mode == ServiceMode.LOCAL:

                logger.info("Using local services for E2E tests")

                # Fallback to legacy services manager for local mode

                await self.services_manager.test_start_test_environment()

                self.ready = True

                return

                

            # Use Docker mode with UnifiedDockerManager

            logger.info("Using Docker services via UnifiedDockerManager")

            

            # Acquire dedicated test environment

            env_name, port_mappings = self.docker_manager.acquire_environment()

            logger.info(f"Acquired test environment: {env_name} with ports: {port_mappings}")

            

            # Start services using smart container reuse

            default_services = services or ["postgres", "redis", "backend", "auth"]

            success = await self.docker_manager.start_services_smart(

                services=default_services,

                wait_healthy=True

            )

            

            if not success:

                raise RuntimeError("Failed to start Docker services")

            

            # Initialize database if specified

            if db_name and self.db_manager:

                await self.db_manager.initialize_test_database(db_name)

            

            self.ready = True

            logger.info("E2E test environment started successfully")

            

        except Exception as e:

            logger.error(f"Failed to start E2E test environment: {e}")

            await self.cleanup()

            raise

    

    async def cleanup(self) -> None:

        """Clean up test environment and release resources."""

        logger.info("Cleaning up E2E test environment")

        

        try:

            if hasattr(self, 'docker_manager'):

                # Graceful shutdown of services

                await self.docker_manager.graceful_shutdown(timeout=30)

                

                # Release environment resources

                if hasattr(self.docker_manager, '_current_env'):

                    self.docker_manager.release_environment(self.docker_manager._current_env)

                

                # Clean up orphaned containers

                self.docker_manager.cleanup_orphaned_containers()

            

            # Legacy cleanup

            if hasattr(self, 'services_manager'):

                if hasattr(self.services_manager, 'cleanup'):

                    await self.services_manager.cleanup()

                    

            if hasattr(self, 'db_manager'):

                if hasattr(self.db_manager, 'cleanup'):

                    await self.db_manager.cleanup()

            

            self.ready = False

            logger.info("E2E test environment cleaned up")

            

        except Exception as e:

            logger.error(f"Error during E2E test cleanup: {e}")

    

    async def reset_test_data(self, services: Optional[List[str]] = None) -> bool:

        """

        Reset test data without restarting containers (performance optimization).

        

        Args:

            services: Services to reset data for

            

        Returns:

            True if data reset was successful

        """

        if not self.ready:

            logger.warning("Cannot reset test data - environment not ready")

            return False

            

        logger.info("Resetting test data using UnifiedDockerManager")

        

        try:

            # Use UnifiedDockerManager's test data reset capability

            success = await self.docker_manager.reset_test_data(services)

            

            if success:

                logger.info("Test data reset completed successfully")

            else:

                logger.warning("Test data reset had issues")

                

            return success

            

        except Exception as e:

            logger.error(f"Error resetting test data: {e}")

            return False

    

    def get_service_urls(self) -> Dict[str, str]:

        """Get service URLs for the current environment."""

        if not self.ready:

            return {}

            

        try:

            # Get port mappings from UnifiedDockerManager

            state = self.docker_manager._load_state()

            current_env = getattr(self.docker_manager, '_current_env', 'default')

            

            if current_env in state.get('environments', {}):

                ports = state['environments'][current_env].get('ports', {})

                

                base_url = "http://localhost"

                return {

                    f"{service}": f"{base_url}:{port}"

                    for service, port in ports.items()

                }

            

            return {}

            

        except Exception as e:

            logger.error(f"Error getting service URLs: {e}")

            return {}

    

    async def wait_for_services(self, 

                               services: Optional[List[str]] = None, 

                               timeout: int = 60) -> bool:

        """

        Wait for services to become healthy.

        

        Args:

            services: Services to wait for, None for all

            timeout: Timeout in seconds

            

        Returns:

            True if all services became healthy

        """

        if not self.ready:

            logger.warning("Cannot wait for services - environment not ready")

            return False

            

        logger.info(f"Waiting for services to become healthy: {services or 'all'}")

        

        try:

            return self.docker_manager.wait_for_services(services, timeout)

            

        except Exception as e:

            logger.error(f"Error waiting for services: {e}")

            return False

    

    def get_container_status(self) -> Dict[str, Any]:

        """Get current container status information."""

        if not self.ready:

            return {}

            

        try:

            return self.docker_manager.get_enhanced_container_status()

            

        except Exception as e:

            logger.error(f"Error getting container status: {e}")

            return {}

    

    async def restart_service(self, service: str, force: bool = False) -> bool:

        """

        Restart a specific service.

        

        Args:

            service: Service name to restart

            force: Force restart even if service is healthy

            

        Returns:

            True if restart was successful

        """

        if not self.ready:

            logger.warning("Cannot restart service - environment not ready")

            return False

            

        logger.info(f"Restarting service: {service} (force={force})")

        

        try:

            return self.docker_manager.restart_service(service, force)

            

        except Exception as e:

            logger.error(f"Error restarting service {service}: {e}")

            return False





# Backward compatibility aliases for legacy code

E2EServiceOrchestrator = UnifiedServiceOrchestrator

ServiceOrchestrator = UnifiedServiceOrchestrator





# Convenience functions

async def create_test_orchestrator(**kwargs) -> UnifiedServiceOrchestrator:

    """Create and initialize a test orchestrator."""

    orchestrator = UnifiedServiceOrchestrator(**kwargs)

    await orchestrator.start_test_environment()

    return orchestrator





async def cleanup_test_orchestrator(orchestrator: UnifiedServiceOrchestrator):

    """Clean up a test orchestrator."""

    if orchestrator:

        await orchestrator.cleanup()

