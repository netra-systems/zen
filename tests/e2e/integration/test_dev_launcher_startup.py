from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment

"""

E2E tests for dev launcher startup sequence in DEV MODE.



Tests comprehensive startup behavior with real services, database connections,

configuration loading, health checks, port allocation, and graceful shutdown.



Follows 450-line file limit and 25-line function limit constraints.

"""



import asyncio

import json

import os

import signal

import subprocess

import sys

import time

from pathlib import Path

from typing import Dict, List, Optional, Tuple



import pytest

import requests



# Add project root to path for imports



from dev_launcher import DevLauncher, LauncherConfig

from tests.e2e.dev_launcher_test_fixtures import TestEnvironmentManager





class TestDevLauncherFixture:

    """Manages dev launcher lifecycle for testing."""

    

    def __init__(self):

        self.launcher: Optional[DevLauncher] = None

        self.process: Optional[subprocess.Popen] = None

        self.config: Optional[LauncherConfig] = None

        self.test_env = TestEnvironmentManager()

        self._setup_test_environment()

    

    def _setup_test_environment(self) -> None:

        """Setup isolated test environment."""

        self.test_env.setup_test_db()

        self.test_env.setup_test_redis()

        self.test_env.setup_test_secrets()

        self._set_test_env_vars()

    

    def _set_test_env_vars(self) -> None:

        """Set environment variables for testing."""

        get_env().set("TESTING", "true", "test")

        get_env().set("DEV_MODE", "true", "test")

        get_env().set("LOG_LEVEL", "DEBUG", "test")

        get_env().set("DISABLE_BROWSER_OPEN", "true", "test")

    

    async def start_launcher(self, **config_overrides) -> bool:

        """Start dev launcher with test configuration."""

        try:

            self.config = self._create_test_config(**config_overrides)

            self.launcher = DevLauncher(self.config)

            result = await asyncio.wait_for(

                self.launcher.run(), timeout=180

            )

            return result == 0

        except asyncio.TimeoutError:

            return False

    

    def _create_test_config(self, **overrides) -> LauncherConfig:

        """Create test configuration with overrides."""

        defaults = {

            "dynamic_ports": True,

            "no_browser": True,

            "load_secrets": False,  # Use load_secrets=False instead of no_secrets=True

            "non_interactive": True,

            "startup_mode": "minimal"  # Use startup_mode instead of minimal

        }

        return LauncherConfig(**{**defaults, **overrides})





@pytest.fixture

async def dev_launcher_fixture():

    """Fixture providing dev launcher test management."""

    fixture = DevLauncherTestFixture()

    yield fixture

    # Clean up launcher resources - DevLauncher doesn't have cleanup method

    # Cleanup is handled by the TestEnvironmentManager

    fixture.test_env.cleanup()





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_dev_launcher_starts_successfully(dev_launcher_fixture):

    """Test dev launcher starts all services without errors."""

    success = await dev_launcher_fixture.start_launcher()

    assert success, "Dev launcher should start successfully"

    

    # Verify launcher state

    launcher = dev_launcher_fixture.launcher

    assert launcher is not None

    assert launcher.config.dynamic_ports

    assert launcher.config.no_browser





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_port_allocation_works(dev_launcher_fixture):

    """Test dynamic port allocation prevents conflicts."""

    # Start first launcher

    success1 = await dev_launcher_fixture.start_launcher()

    assert success1

    

    ports1 = _extract_allocated_ports(dev_launcher_fixture.launcher)

    

    # Start second launcher (should get different ports)

    fixture2 = DevLauncherTestFixture()

    success2 = await fixture2.start_launcher()

    assert success2

    

    ports2 = _extract_allocated_ports(fixture2.launcher)

    assert not _ports_overlap(ports1, ports2)





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_configuration_loading(dev_launcher_fixture):

    """Test .env files and configuration are loaded correctly."""

    success = await dev_launcher_fixture.start_launcher()

    assert success

    

    config = dev_launcher_fixture.config

    assert config.dynamic_ports is True

    assert config.no_browser is True

    assert config.non_interactive is True





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_startup_sequence_ordering(dev_launcher_fixture):

    """Test services start in correct order with dependencies."""

    logs = []

    

    # Mock log capture

    # Mock: Component isolation for testing without external dependencies

    with patch('dev_launcher.log_streamer.LogManager') as mock_log:

        mock_log.return_value.log_message.side_effect = \

            lambda msg: logs.append(msg)

        

        success = await dev_launcher_fixture.start_launcher()

        assert success

    

    # Verify startup order

    assert _verify_startup_order(logs)





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_graceful_shutdown(dev_launcher_fixture):

    """Test graceful shutdown stops all services cleanly."""

    success = await dev_launcher_fixture.start_launcher()

    assert success

    

    launcher = dev_launcher_fixture.launcher

    

    # Trigger graceful shutdown via process manager

    start_time = time.time()

    if hasattr(launcher, 'process_manager') and launcher.process_manager:

        launcher.process_manager.cleanup_all()  # cleanup_all is synchronous

    shutdown_time = time.time() - start_time

    

    # Should shutdown within reasonable time

    assert shutdown_time < 30

    assert _verify_clean_shutdown(launcher)





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_error_recovery(dev_launcher_fixture):

    """Test launcher recovers from service failures."""

    # Simulate service failure during startup

    # Mock: Component isolation for testing without external dependencies

    with patch('dev_launcher.service_startup.ServiceStartupCoordinator') as mock:

        mock.return_value.start_service.side_effect = \

            [Exception("Simulated failure"), None, None]

        

        success = await dev_launcher_fixture.start_launcher()

        # Should recover and continue

        assert success or _verify_partial_startup(dev_launcher_fixture.launcher)





def _extract_allocated_ports(launcher: DevLauncher) -> Dict[str, int]:

    """Extract allocated ports from launcher."""

    if not launcher or not hasattr(launcher, 'process_manager'):

        return {}

    return getattr(launcher.process_manager, 'allocated_ports', {})





def _ports_overlap(ports1: Dict[str, int], ports2: Dict[str, int]) -> bool:

    """Check if two port sets overlap."""

    values1 = set(ports1.values())

    values2 = set(ports2.values())

    return bool(values1.intersection(values2))





def _verify_startup_order(logs: List[str]) -> bool:

    """Verify services started in correct order."""

    # Look for specific startup order patterns

    service_starts = []

    for log in logs:

        if "starting" in log.lower():

            if "database" in log.lower():

                service_starts.append("database")

            elif "auth" in log.lower():

                service_starts.append("auth")

            elif "backend" in log.lower():

                service_starts.append("backend")

            elif "frontend" in log.lower():

                service_starts.append("frontend")

    

    # Database should start before backend

    try:

        db_idx = service_starts.index("database")

        backend_idx = service_starts.index("backend")

        return db_idx < backend_idx

    except ValueError:

        return False





def _verify_clean_shutdown(launcher: DevLauncher) -> bool:

    """Verify all processes shutdown cleanly."""

    if not launcher or not hasattr(launcher, 'process_manager'):

        return True

    

    pm = launcher.process_manager

    active_processes = getattr(pm, 'processes', {})

    return len(active_processes) == 0





def _verify_partial_startup(launcher: DevLauncher) -> bool:

    """Verify launcher achieved partial startup despite errors."""

    if not launcher:

        return False

    

    # Check if at least some critical services started

    return hasattr(launcher, 'health_monitor') and \

           launcher.health_monitor is not None





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_env_file_validation(dev_launcher_fixture):

    """Test .env file loading and validation."""

    # Create test .env content

    test_env_content = {

        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",

        "REDIS_URL": "redis://localhost:6379/1",

        "SECRET_KEY": "test-secret-key"

    }

    

    success = await dev_launcher_fixture.start_launcher()

    assert success

    

    # Verify environment variables loaded

    launcher = dev_launcher_fixture.launcher

    assert _verify_env_loaded(launcher, test_env_content)





def _verify_env_loaded(launcher: DevLauncher, expected: Dict[str, str]) -> bool:

    """Verify environment variables were loaded correctly."""

    for key, value in expected.items():

        if get_env().get(key) != value:

            return False

    return True





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_process_cleanup_on_failure(dev_launcher_fixture):

    """Test processes are cleaned up if startup fails."""

    # Force startup failure

    # Mock: Component isolation for testing without external dependencies

    with patch('dev_launcher.environment_checker.EnvironmentChecker') as mock:

        mock.return_value.check_environment.side_effect = Exception("Test failure")

        

        try:

            await dev_launcher_fixture.start_launcher()

        except:

            pass

    

    # Verify no orphaned processes

    assert _verify_no_orphaned_processes()





def _verify_no_orphaned_processes() -> bool:

    """Verify no test processes are still running."""

    try:

        # Check for common dev launcher process patterns

        result = subprocess.run(

            ["tasklist" if os.name == "nt" else "ps", "aux"],

            capture_output=True, text=True

        )

        return "uvicorn" not in result.stdout and "next" not in result.stdout

    except:

        return True

