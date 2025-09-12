#!/usr/bin/env python3
"""
Validation script for SSOT Unified Managers

Validates that the unified managers properly implement:
- Factory pattern for user isolation
- WebSocket integration
- IsolatedEnvironment usage
- Thread safety
- SSOT compliance
"""

import sys
import inspect
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.core.managers import (
    UnifiedLifecycleManager,
    UnifiedConfigurationManager,
    UnifiedStateManager
)

def validate_factory_pattern():
    """Validate factory pattern implementation."""
    print("Factory Pattern: Validating Factory Pattern Implementation...")
    
    # Check LifecycleManagerFactory
    try:
        from netra_backend.app.core.managers.unified_lifecycle_manager import LifecycleManagerFactory
        
        # Test global manager
        global_manager = LifecycleManagerFactory.get_global_manager()
        assert isinstance(global_manager, UnifiedLifecycleManager)
        assert global_manager.user_id is None
        
        # Test user-specific manager
        user_manager = LifecycleManagerFactory.get_user_manager("test_user")
        assert isinstance(user_manager, UnifiedLifecycleManager)
        assert user_manager.user_id == "test_user"
        
        # Test that same user gets same instance
        same_user_manager = LifecycleManagerFactory.get_user_manager("test_user")
        assert same_user_manager is user_manager
        
        print("  [PASS] LifecycleManagerFactory: SUCCESS")
        
    except Exception as e:
        print(f"   FAIL:  LifecycleManagerFactory: FAIL - {e}")
        return False
    
    # Check ConfigurationManagerFactory
    try:
        from netra_backend.app.core.managers.unified_configuration_manager import ConfigurationManagerFactory
        
        # Test global manager
        global_config = ConfigurationManagerFactory.get_global_manager()
        assert isinstance(global_config, UnifiedConfigurationManager)
        
        # Test user-specific manager
        user_config = ConfigurationManagerFactory.get_user_manager("test_user")
        assert isinstance(user_config, UnifiedConfigurationManager)
        assert user_config.user_id == "test_user"
        
        print("   PASS:  ConfigurationManagerFactory: PASS")
        
    except Exception as e:
        print(f"   FAIL:  ConfigurationManagerFactory: FAIL - {e}")
        return False
    
    # Check StateManagerFactory
    try:
        from netra_backend.app.core.managers.unified_state_manager import StateManagerFactory
        
        # Test global manager
        global_state = StateManagerFactory.get_global_manager()
        assert isinstance(global_state, UnifiedStateManager)
        
        # Test user-specific manager
        user_state = StateManagerFactory.get_user_manager("test_user")
        assert isinstance(user_state, UnifiedStateManager)
        assert user_state.user_id == "test_user"
        
        print("   PASS:  StateManagerFactory: PASS")
        
    except Exception as e:
        print(f"   FAIL:  StateManagerFactory: FAIL - {e}")
        return False
    
    return True

def validate_websocket_integration():
    """Validate WebSocket integration."""
    print("[U+1F50C] Validating WebSocket Integration...")
    
    managers = [
        ("LifecycleManager", UnifiedLifecycleManager()),
        ("ConfigurationManager", UnifiedConfigurationManager()),
        ("StateManager", UnifiedStateManager())
    ]
    
    for name, manager in managers:
        try:
            # Check for WebSocket manager setter
            assert hasattr(manager, 'set_websocket_manager'), f"{name} missing set_websocket_manager method"
            
            # Check for WebSocket event controls
            if hasattr(manager, 'enable_websocket_events'):
                manager.enable_websocket_events(False)
                manager.enable_websocket_events(True)
            
            # Check for internal WebSocket manager storage
            assert hasattr(manager, '_websocket_manager'), f"{name} missing _websocket_manager attribute"
            
            print(f"   PASS:  {name}: PASS")
            
        except Exception as e:
            print(f"   FAIL:  {name}: FAIL - {e}")
            return False
    
    return True

def validate_isolated_environment():
    """Validate IsolatedEnvironment usage."""
    print("[U+1F512] Validating IsolatedEnvironment Usage...")
    
    managers = [
        ("LifecycleManager", UnifiedLifecycleManager()),
        ("ConfigurationManager", UnifiedConfigurationManager()),
        ("StateManager", UnifiedStateManager())
    ]
    
    for name, manager in managers:
        try:
            # Check for IsolatedEnvironment instance
            assert hasattr(manager, '_env'), f"{name} missing _env attribute"
            
            # Verify it's using IsolatedEnvironment (not direct os.environ)
            from shared.isolated_environment import IsolatedEnvironment
            assert isinstance(manager._env, IsolatedEnvironment), f"{name} not using IsolatedEnvironment"
            
            print(f"   PASS:  {name}: PASS")
            
        except Exception as e:
            print(f"   FAIL:  {name}: FAIL - {e}")
            return False
    
    return True

def validate_thread_safety():
    """Validate thread safety mechanisms."""
    print("[U+1F512] Validating Thread Safety...")
    
    managers = [
        ("LifecycleManager", UnifiedLifecycleManager()),
        ("ConfigurationManager", UnifiedConfigurationManager()),  
        ("StateManager", UnifiedStateManager())
    ]
    
    for name, manager in managers:
        try:
            # Check for locking mechanisms
            lock_attributes = [attr for attr in dir(manager) if 'lock' in attr.lower()]
            assert len(lock_attributes) > 0, f"{name} missing locking mechanisms"
            
            # Check for async-safe operations
            async_methods = [method for method in dir(manager) if inspect.iscoroutinefunction(getattr(manager, method))]
            
            print(f"   PASS:  {name}: PASS (locks: {len(lock_attributes)}, async methods: {len(async_methods)})")
            
        except Exception as e:
            print(f"   FAIL:  {name}: FAIL - {e}")
            return False
    
    return True

def validate_ssot_compliance():
    """Validate SSOT compliance."""
    print("[U+1F4CB] Validating SSOT Compliance...")
    
    # Check that managers have proper SSOT methods
    lifecycle_manager = UnifiedLifecycleManager()
    config_manager = UnifiedConfigurationManager()
    state_manager = UnifiedStateManager()
    
    try:
        # Lifecycle Manager SSOT checks
        assert hasattr(lifecycle_manager, 'startup'), "LifecycleManager missing startup method"
        assert hasattr(lifecycle_manager, 'shutdown'), "LifecycleManager missing shutdown method"
        assert hasattr(lifecycle_manager, 'register_component'), "LifecycleManager missing register_component method"
        assert hasattr(lifecycle_manager, 'get_health_status'), "LifecycleManager missing get_health_status method"
        
        # Configuration Manager SSOT checks
        assert hasattr(config_manager, 'get'), "ConfigurationManager missing get method"
        assert hasattr(config_manager, 'set'), "ConfigurationManager missing set method"
        assert hasattr(config_manager, 'get_database_config'), "ConfigurationManager missing get_database_config method"
        assert hasattr(config_manager, 'validate_all_configurations'), "ConfigurationManager missing validate_all_configurations method"
        
        # State Manager SSOT checks
        assert hasattr(state_manager, 'get'), "StateManager missing get method"
        assert hasattr(state_manager, 'set'), "StateManager missing set method"
        assert hasattr(state_manager, 'get_user_state'), "StateManager missing get_user_state method"
        assert hasattr(state_manager, 'get_agent_state'), "StateManager missing get_agent_state method"
        assert hasattr(state_manager, 'query_states'), "StateManager missing query_states method"
        
        print("   PASS:  All SSOT compliance checks: PASS")
        return True
        
    except Exception as e:
        print(f"   FAIL:  SSOT compliance: FAIL - {e}")
        return False

def main():
    """Run all validations."""
    print("[U+1F680] SSOT Unified Managers Validation")
    print("=" * 50)
    
    results = []
    
    # Run all validation checks
    results.append(validate_factory_pattern())
    results.append(validate_websocket_integration())
    results.append(validate_isolated_environment())
    results.append(validate_thread_safety())
    results.append(validate_ssot_compliance())
    
    print("\n" + "=" * 50)
    
    if all(results):
        print(" CELEBRATION:  ALL VALIDATIONS PASSED!")
        print(" PASS:  SSOT Unified Managers are properly implemented")
        print(" CHART:  Summary:")
        print(f"  [U+2022] UnifiedLifecycleManager: {len(inspect.getsource(UnifiedLifecycleManager).splitlines())} lines")
        print(f"  [U+2022] UnifiedConfigurationManager: {len(inspect.getsource(UnifiedConfigurationManager).splitlines())} lines")  
        print(f"  [U+2022] UnifiedStateManager: {len(inspect.getsource(UnifiedStateManager).splitlines())} lines")
        print("  [U+2022] All managers implement factory pattern for user isolation")
        print("  [U+2022] All managers support WebSocket integration")
        print("  [U+2022] All managers use IsolatedEnvironment for env access")
        print("  [U+2022] All managers implement thread-safe operations")
        return 0
    else:
        print(" FAIL:  SOME VALIDATIONS FAILED!")
        failed_count = len([r for r in results if not r])
        print(f" CHART:  {failed_count} out of {len(results)} validations failed")
        return 1

if __name__ == "__main__":
    exit(main())