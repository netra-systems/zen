#!/usr/bin/env python3
"""
Simple validation script for SSOT Unified Managers
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Run basic validation."""
    print("SSOT Unified Managers Validation")
    print("=" * 50)
    
    try:
        # Test imports
        print("Testing imports...")
        from netra_backend.app.core.managers import (
            UnifiedLifecycleManager,
            UnifiedConfigurationManager,
            UnifiedStateManager
        )
        print("[PASS] All managers imported successfully")
        
        # Test factory patterns
        print("Testing factory patterns...")
        from netra_backend.app.core.managers.unified_lifecycle_manager import LifecycleManagerFactory
        from netra_backend.app.core.configuration.base import config_manager
        from netra_backend.app.core.managers.unified_state_manager import StateManagerFactory
        
        # Test lifecycle factory
        lifecycle_manager = LifecycleManagerFactory.get_global_manager()
        assert isinstance(lifecycle_manager, UnifiedLifecycleManager)
        
        user_lifecycle = LifecycleManagerFactory.get_user_manager("test_user")
        assert isinstance(user_lifecycle, UnifiedLifecycleManager)
        assert user_lifecycle.user_id == "test_user"
        print("[PASS] LifecycleManagerFactory working")
        
        # Test config factory
        config_manager = ConfigurationManagerFactory.get_global_manager()
        assert isinstance(config_manager, UnifiedConfigurationManager)
        
        user_config = ConfigurationManagerFactory.get_user_manager("test_user")
        assert isinstance(user_config, UnifiedConfigurationManager)
        assert user_config.user_id == "test_user"
        print("[PASS] ConfigurationManagerFactory working")
        
        # Test state factory
        state_manager = StateManagerFactory.get_global_manager()
        assert isinstance(state_manager, UnifiedStateManager)
        
        user_state = StateManagerFactory.get_user_manager("test_user")
        assert isinstance(user_state, UnifiedStateManager)  
        assert user_state.user_id == "test_user"
        print("[PASS] StateManagerFactory working")
        
        # Test WebSocket integration
        print("Testing WebSocket integration...")
        assert hasattr(lifecycle_manager, 'set_websocket_manager')
        assert hasattr(config_manager, 'set_websocket_manager')
        assert hasattr(state_manager, 'set_websocket_manager')
        print("[PASS] WebSocket integration methods present")
        
        # Test IsolatedEnvironment usage
        print("Testing IsolatedEnvironment usage...")
        assert hasattr(lifecycle_manager, '_env')
        assert hasattr(config_manager, '_env')
        assert hasattr(state_manager, '_env')
        print("[PASS] IsolatedEnvironment integration present")
        
        # Test SSOT methods
        print("Testing SSOT methods...")
        
        # Lifecycle methods
        assert hasattr(lifecycle_manager, 'startup')
        assert hasattr(lifecycle_manager, 'shutdown')
        assert hasattr(lifecycle_manager, 'register_component')
        
        # Config methods
        assert hasattr(config_manager, 'get')
        assert hasattr(config_manager, 'set')
        assert hasattr(config_manager, 'get_database_config')
        
        # State methods
        assert hasattr(state_manager, 'get')
        assert hasattr(state_manager, 'set')
        assert hasattr(state_manager, 'get_user_state')
        assert hasattr(state_manager, 'get_agent_state')
        
        print("[PASS] All SSOT methods present")
        
        # Test basic operations
        print("Testing basic operations...")
        
        # Test config operations
        config_manager.set("test_key", "test_value")
        assert config_manager.get("test_key") == "test_value"
        
        # Test state operations  
        state_manager.set("test_state", {"key": "value"})
        assert state_manager.get("test_state")["key"] == "value"
        
        print("[PASS] Basic operations working")
        
        print("\n" + "=" * 50)
        print("ALL VALIDATIONS PASSED!")
        print("\nSummary:")
        print("  - UnifiedLifecycleManager: Implemented")
        print("  - UnifiedConfigurationManager: Implemented") 
        print("  - UnifiedStateManager: Implemented")
        print("  - Factory patterns: Working")
        print("  - WebSocket integration: Ready")
        print("  - IsolatedEnvironment: Integrated")
        print("  - SSOT methods: Complete")
        print("  - Basic operations: Functional")
        
        return 0
        
    except Exception as e:
        print(f"[FAIL] Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())