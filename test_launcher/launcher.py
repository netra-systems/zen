"""
Core TestLauncher class - optimized for testing scenarios.

Key differences from DevLauncher:
- No browser auto-open
- No hot-reload by default
- Test-specific service profiles
- Enhanced isolation capabilities
- Optimized for CI/CD environments
"""

import asyncio
import logging
import os
import sys
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from test_launcher.config import TestConfig, TestProfile
from test_launcher.isolation.environment import TestEnvironmentManager
from test_launcher.test_services import TestServiceManager


logger = logging.getLogger(__name__)


class TestLauncher:
    """Test-focused launcher for Netra platform services."""
    
    def __init__(self, config: TestConfig):
        """Initialize test launcher with configuration."""
        self.config = config
        self.project_root = Path.cwd()
        self.services: Dict[str, subprocess.Popen] = {}
        self.service_manager = TestServiceManager(config)
        self.env_manager = TestEnvironmentManager(config)
        self.shutdown_event = asyncio.Event()
        self.startup_complete = False
        self.cleanup_handlers = []
        
        # Setup logging
        self._setup_logging()
        
        # Register signal handlers
        self._setup_signal_handlers()
    
    def _setup_logging(self):
        """Configure logging for test execution."""
        log_level = logging.DEBUG if self.config.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='[%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(
                    self.project_root / 'logs' / f'test_launcher_{int(time.time())}.log',
                    mode='w'
                )
            ]
        )
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.cleanup())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if sys.platform == "win32":
            # Windows-specific signal handling
            signal.signal(signal.SIGBREAK, signal_handler)
    
    async def run(self) -> int:
        """
        Main entry point for test launcher.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            logger.info(f"Starting TestLauncher with profile: {self.config.profile.value}")
            
            # Phase 1: Environment setup
            logger.info("Phase 1: Setting up test environment...")
            await self._setup_environment()
            
            # Phase 2: Start required services
            logger.info("Phase 2: Starting required services...")
            services_started = await self._start_services()
            if not services_started:
                logger.error("Failed to start required services")
                return 1
            
            # Phase 3: Wait for services to be ready
            logger.info("Phase 3: Waiting for services to be ready...")
            services_ready = await self._wait_for_services()
            if not services_ready:
                logger.error("Services failed to become ready")
                return 1
            
            # Phase 4: Run any pre-test setup
            logger.info("Phase 4: Running pre-test setup...")
            await self._run_pre_test_setup()
            
            self.startup_complete = True
            logger.info("Test environment ready!")
            
            # For test launcher, we don't keep services running indefinitely
            # Instead, return success and let the test runner take over
            return 0
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 0
        except Exception as e:
            logger.error(f"Test launcher failed: {e}", exc_info=True)
            return 1
        finally:
            if self.config.cleanup_on_exit:
                await self.cleanup()
    
    async def _setup_environment(self):
        """Setup test environment variables and configuration."""
        logger.debug("Setting up test environment variables...")
        
        # Apply test-specific environment configuration
        self.env_manager.setup()
        
        # Create necessary directories
        log_dir = self.project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        test_data_dir = self.project_root / 'test_data'
        test_data_dir.mkdir(exist_ok=True)
    
    async def _start_services(self) -> bool:
        """
        Start required services based on test profile.
        
        Returns:
            True if all services started successfully
        """
        required_services = self.config.get_required_services()
        
        if not required_services:
            logger.info("No services required for this test profile")
            return True
        
        logger.info(f"Starting services: {', '.join(required_services)}")
        
        # Start services in parallel where possible
        if self.config.parallel_execution and len(required_services) > 1:
            tasks = [
                self.service_manager.start_service(service)
                for service in required_services
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            for service, result in zip(required_services, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to start {service}: {result}")
                    return False
                elif not result:
                    logger.error(f"Failed to start {service}")
                    return False
        else:
            # Start services sequentially
            for service in required_services:
                try:
                    success = await self.service_manager.start_service(service)
                    if not success:
                        logger.error(f"Failed to start {service}")
                        return False
                except Exception as e:
                    logger.error(f"Exception starting {service}: {e}")
                    return False
        
        return True
    
    async def _wait_for_services(self) -> bool:
        """
        Wait for all services to be ready.
        
        Returns:
            True if all services are ready
        """
        required_services = self.config.get_required_services()
        
        if not required_services:
            return True
        
        logger.info("Waiting for services to be ready...")
        
        # Check service readiness with timeout
        max_wait = max(
            self.config.services[service].startup_timeout
            for service in required_services
        )
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            all_ready = True
            
            for service in required_services:
                if not await self.service_manager.is_service_ready(service):
                    all_ready = False
                    break
            
            if all_ready:
                logger.info("All services are ready!")
                return True
            
            await asyncio.sleep(2)
        
        # Log which services are not ready
        for service in required_services:
            if not await self.service_manager.is_service_ready(service):
                logger.error(f"Service {service} is not ready after {max_wait}s")
        
        return False
    
    async def _run_pre_test_setup(self):
        """Run any pre-test setup required for the profile."""
        if self.config.profile == TestProfile.E2E:
            # For E2E tests, might need to seed database or setup test data
            logger.info("Running E2E pre-test setup...")
            # TODO: Add database seeding logic here
        elif self.config.profile == TestProfile.INTEGRATION:
            # For integration tests, might need to run migrations
            logger.info("Running integration test setup...")
            # TODO: Add migration logic here
    
    async def cleanup(self):
        """Clean up all resources and stop services."""
        logger.info("Starting cleanup...")
        
        try:
            # Stop all services
            await self.service_manager.stop_all_services()
            
            # Clean up environment
            self.env_manager.cleanup()
            
            # Run any registered cleanup handlers
            for handler in self.cleanup_handlers:
                try:
                    await handler()
                except Exception as e:
                    logger.error(f"Cleanup handler failed: {e}")
            
            logger.info("Cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def register_cleanup_handler(self, handler):
        """Register a cleanup handler to be called on shutdown."""
        self.cleanup_handlers.append(handler)
    
    async def get_service_status(self) -> Dict[str, Dict]:
        """
        Get status of all services.
        
        Returns:
            Dictionary mapping service names to their status
        """
        status = {}
        
        for service in self.config.get_required_services():
            is_ready = await self.service_manager.is_service_ready(service)
            status[service] = {
                "enabled": True,
                "running": service in self.service_manager.running_services,
                "ready": is_ready,
                "port": self.config.services[service].port,
            }
        
        return status
    
    @classmethod
    def for_profile(cls, profile: TestProfile, **kwargs) -> "TestLauncher":
        """
        Create a TestLauncher for a specific profile.
        
        Args:
            profile: Test profile to use
            **kwargs: Additional configuration overrides
            
        Returns:
            Configured TestLauncher instance
        """
        config = TestConfig.for_profile(profile)
        
        # Apply any overrides
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return cls(config)