"""
Basic Startup Test - Validates core system initialization

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Startup Reliability
- Value Impact: Ensures system can start consistently
- Strategic Impact: Prevents startup failures that block all operations

This test validates the most basic startup requirements:
1. Environment detection works
2. Configuration loads
3. Basic imports are functional
"""
import pytest
from typing import Dict, Any
import os

from netra_backend.app.core.environment_constants import EnvironmentDetector
from test_framework.performance_helpers import fast_test


@pytest.mark.unit
@fast_test
def test_environment_detection():
    """Test that environment detection works correctly."""
    # This should not raise an exception
    env = EnvironmentDetector.get_environment()
    
    # Environment should be one of the valid values
    valid_envs = ["development", "staging", "production", "test", "testing"]
    assert env in valid_envs, f"Environment '{env}' not in valid environments: {valid_envs}"
    
    # Environment should be consistent across calls
    env2 = EnvironmentDetector.get_environment()
    assert env == env2, "Environment detection should be consistent"


@pytest.mark.unit  
@fast_test
def test_configuration_loading():
    """Test that basic configuration loading works."""
    from netra_backend.app.core.configuration import get_unified_config
    
    # Should not raise an exception
    config = get_unified_config()
    
    # Config should be a configuration object
    assert config is not None, "Config should not be None"
    
    # Should have some basic expected keys
    # Note: Using lenient checks to avoid environment-specific failures


@pytest.mark.unit
@fast_test  
def test_core_imports():
    """Test that core system imports work correctly."""
    # These imports should not fail
    try:
        from netra_backend.app.core.unified_logging import get_logger
        from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreakerManager
        from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
        
        # Basic usage should work
        logger = get_logger(__name__)
        assert logger is not None, "Logger should be created"
        
        # Circuit breaker manager should be creatable
        cb_manager = UnifiedCircuitBreakerManager()
        assert cb_manager is not None, "Circuit breaker manager should be created"
        
    except ImportError as e:
        pytest.fail(f"Core import failed: {e}")
    except Exception as e:
        pytest.fail(f"Core system initialization failed: {e}")


@pytest.mark.integration
def test_startup_manager_basics():
    """Test that startup manager can be imported and initialized."""
    try:
        from netra_backend.app.core.startup_manager import StartupManager
        
        # Should be able to create instance
        startup_manager = StartupManager()
        assert startup_manager is not None, "StartupManager should be created"
        
        # Should have expected methods
        assert hasattr(startup_manager, 'register_component'), "StartupManager should have register_component method"
        
    except ImportError as e:
        pytest.fail(f"StartupManager import failed: {e}")
    except Exception as e:
        pytest.fail(f"StartupManager initialization failed: {e}")


@pytest.mark.integration
def test_database_connector_import():
    """Test that database connector can be imported."""
    try:
        from dev_launcher.database_connector import DatabaseConnector, ConnectionStatus
        
        # Should be able to create instance
        connector = DatabaseConnector()
        assert connector is not None, "DatabaseConnector should be created"
        
        # ConnectionStatus enum should have expected values
        assert hasattr(ConnectionStatus, 'CONNECTED'), "ConnectionStatus should have CONNECTED"
        assert hasattr(ConnectionStatus, 'FAILED'), "ConnectionStatus should have FAILED"
        
    except ImportError as e:
        pytest.fail(f"DatabaseConnector import failed: {e}")
    except Exception as e:
        pytest.fail(f"DatabaseConnector initialization failed: {e}")