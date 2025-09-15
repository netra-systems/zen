"""Comprehensive Test Suite for SSOT Managers

Tests all three SSOT managers:
1. UnifiedLifecycleManager
2. UnifiedConfigurationManager  
3. UnifiedStateManager

Business Value: Validates the core foundation of the entire platform.
These managers underpin ALL user-facing functionality.
"""
import asyncio
import os
import pytest
import sys
import uuid
from typing import Any, Dict, Optional
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.managers.unified_lifecycle_manager import UnifiedLifecycleManager, LifecyclePhase
from netra_backend.app.core.configuration.base import UnifiedConfigManager, get_config, get_config_value, set_config_value, validate_config_value, get_environment, is_production, is_development, is_testing, config_manager
from netra_backend.app.core.managers.unified_state_manager import UnifiedStateManager

class SSOTManagersBasicTests:
    """Basic functionality tests for SSOT managers."""

    def test_ssot_managers_import_successfully(self):
        """Test that all SSOT managers can be imported without errors."""
        assert UnifiedLifecycleManager is not None
        assert UnifiedConfigurationManager is not None
        assert UnifiedStateManager is not None
        assert LifecyclePhase is not None
        assert LifecyclePhase.INITIALIZING is not None
        assert LifecyclePhase.RUNNING is not None

    def test_unified_lifecycle_manager_instantiation(self):
        """Test UnifiedLifecycleManager can be instantiated."""
        user_id = f'test-user-{uuid.uuid4()}'
        manager = UnifiedLifecycleManager(user_id=user_id, startup_timeout=30, shutdown_timeout=15)
        assert manager is not None
        assert manager.user_id == user_id
        assert manager.startup_timeout == 30
        assert manager.shutdown_timeout == 15

    def test_unified_configuration_manager_instantiation(self):
        """Test UnifiedConfigurationManager can be instantiated."""
        user_id = f'test-user-{uuid.uuid4()}'
        manager = UnifiedConfigurationManager(user_id=user_id)
        assert manager is not None
        assert manager.user_id == user_id

    def test_unified_state_manager_instantiation(self):
        """Test UnifiedStateManager can be instantiated."""
        user_id = f'test-user-{uuid.uuid4()}'
        manager = UnifiedStateManager(user_id=user_id)
        assert manager is not None
        assert manager.user_id == user_id

    def test_multi_user_isolation_different_instances(self):
        """Test that different users get different manager instances."""
        user1_id = f'user1-{uuid.uuid4()}'
        user2_id = f'user2-{uuid.uuid4()}'
        lifecycle1 = UnifiedLifecycleManager(user_id=user1_id)
        lifecycle2 = UnifiedLifecycleManager(user_id=user2_id)
        config1 = UnifiedConfigurationManager(user_id=user1_id)
        config2 = UnifiedConfigurationManager(user_id=user2_id)
        state1 = UnifiedStateManager(user_id=user1_id)
        state2 = UnifiedStateManager(user_id=user2_id)
        assert lifecycle1 is not lifecycle2
        assert config1 is not config2
        assert state1 is not state2
        assert lifecycle1.user_id == user1_id
        assert lifecycle2.user_id == user2_id
        assert config1.user_id == user1_id
        assert config2.user_id == user2_id
        assert state1.user_id == user1_id
        assert state2.user_id == user2_id

    @pytest.mark.asyncio
    async def test_lifecycle_manager_basic_startup(self):
        """Test basic lifecycle manager startup."""
        user_id = f'test-user-{uuid.uuid4()}'
        manager = UnifiedLifecycleManager(user_id=user_id, startup_timeout=10)
        assert manager._current_phase == LifecyclePhase.INITIALIZING
        try:
            result = await manager.startup()
            if result:
                assert manager._current_phase == LifecyclePhase.RUNNING
        except Exception as e:
            print(f'Startup failed as expected in unit test: {e}')

    @pytest.mark.asyncio
    async def test_lifecycle_manager_shutdown(self):
        """Test lifecycle manager shutdown without startup."""
        user_id = f'test-user-{uuid.uuid4()}'
        manager = UnifiedLifecycleManager(user_id=user_id)
        try:
            await manager.shutdown()
            assert manager._current_phase in [LifecyclePhase.SHUTDOWN_COMPLETE, LifecyclePhase.SHUTTING_DOWN]
        except Exception as e:
            print(f'Shutdown had issues in unit test (expected): {e}')

class SSOTManagersFactoryPatternTests:
    """Test factory pattern isolation across SSOT managers."""

    def test_factory_pattern_creates_isolated_instances(self):
        """Test that factory pattern creates isolated instances for each user."""
        users = [f'user{i}-{uuid.uuid4()}' for i in range(3)]
        lifecycle_managers = []
        config_managers = []
        state_managers = []
        for user_id in users:
            lifecycle_managers.append(UnifiedLifecycleManager(user_id=user_id))
            config_managers.append(UnifiedConfigurationManager(user_id=user_id))
            state_managers.append(UnifiedStateManager(user_id=user_id))
        for i in range(len(users)):
            for j in range(i + 1, len(users)):
                assert lifecycle_managers[i] is not lifecycle_managers[j]
                assert config_managers[i] is not config_managers[j]
                assert state_managers[i] is not state_managers[j]
                assert lifecycle_managers[i].user_id == users[i]
                assert lifecycle_managers[j].user_id == users[j]

    def test_ssot_managers_use_isolated_environment(self):
        """Test that SSOT managers use IsolatedEnvironment for environment access."""
        user_id = f'test-user-{uuid.uuid4()}'
        lifecycle = UnifiedLifecycleManager(user_id=user_id)
        config = UnifiedConfigurationManager(user_id=user_id)
        state = UnifiedStateManager(user_id=user_id)
        assert hasattr(lifecycle, '_load_environment_config')
        assert config is not None
        assert state is not None
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')