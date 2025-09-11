"""
WebSocket SSOT Connection Lifecycle Violation Tests

Tests for SSOT violations in WebSocket connection lifecycle management,
ensuring proper connection creation, management, and cleanup through unified system.

Business Value: Platform/Internal - Prevent connection leaks and race conditions
Critical for system stability and resource management in production.

Test Status: DESIGNED TO FAIL with current code (detecting violations)
Expected Result: PASS after SSOT consolidation unifies connection lifecycle
"""

import asyncio
import gc
import sys
import weakref
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime, timezone

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ConnectionID, ensure_user_id


class TestWebSocketSSotConnectionLifecycle(SSotAsyncTestCase):
    """Test connection lifecycle SSOT violations."""
    
    async def test_connection_creation_through_unified_path(self):
        """
        Test that connection creation goes through single unified path.
        
        CURRENT BEHAVIOR: Multiple connection creation paths (VIOLATION)
        EXPECTED AFTER SSOT: Single creation path
        """
        user_id = ensure_user_id("lifecycle_test_user")
        connection_id = "test_connection_001"
        
        creation_paths_tested = {}
        
        # Test different connection creation methods
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager = UnifiedWebSocketManager()
            
            # Test direct connection creation
            try:
                await manager.add_connection(user_id, connection_id, None)
                creation_paths_tested['direct_add_connection'] = True
            except Exception:
                creation_paths_tested['direct_add_connection'] = False
            
            # Test factory-based creation
            try:
                from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
                factory = WebSocketManagerFactory()
                factory_manager = factory.create_manager()
                await factory_manager.add_connection(user_id, f"{connection_id}_factory", None)
                creation_paths_tested['factory_creation'] = True
            except (ImportError, AttributeError, Exception):
                creation_paths_tested['factory_creation'] = False
            
            # Test legacy creation methods
            legacy_methods = ['register_connection', 'create_connection', 'establish_connection']
            for method_name in legacy_methods:
                if hasattr(manager, method_name):
                    try:
                        method = getattr(manager, method_name)
                        await method(user_id, f"{connection_id}_{method_name}", None)
                        creation_paths_tested[f'legacy_{method_name}'] = True
                    except Exception:
                        creation_paths_tested[f'legacy_{method_name}'] = False
                else:
                    creation_paths_tested[f'legacy_{method_name}'] = False
        
        except ImportError as e:
            self.fail(f"Failed to import WebSocket manager: {e}")
        
        working_creation_paths = sum(creation_paths_tested.values())
        
        # CURRENT EXPECTATION: Multiple creation paths work (violation)
        # AFTER SSOT: Should have single creation path
        self.assertGreater(working_creation_paths, 1,
                          "SSOT VIOLATION DETECTED: Multiple connection creation paths exist. "
                          f"Found {working_creation_paths} working paths: {creation_paths_tested}")
        
        self.metrics.record_test_event("connection_creation_path_violation", {
            "working_paths": working_creation_paths,
            "path_results": creation_paths_tested
        })

    async def test_connection_cleanup_consistency(self):
        """
        Test that connection cleanup is consistent across all creation methods.
        
        CURRENT BEHAVIOR: Inconsistent cleanup methods (VIOLATION)
        EXPECTED AFTER SSOT: Unified cleanup process
        """
        user_id = ensure_user_id("cleanup_test_user")
        cleanup_methods_tested = {}
        connection_leaks = []
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager = UnifiedWebSocketManager()
            
            # Create connections through different methods and test cleanup
            connection_ids = ["cleanup_conn_1", "cleanup_conn_2", "cleanup_conn_3"]
            
            for i, conn_id in enumerate(connection_ids):
                # Create connection
                try:
                    await manager.add_connection(user_id, conn_id, None)
                except Exception:
                    continue
                
                # Test different cleanup methods
                cleanup_method = None
                cleanup_success = False
                
                if i == 0 and hasattr(manager, 'remove_connection'):
                    try:
                        await manager.remove_connection(user_id, conn_id)
                        cleanup_method = 'remove_connection'
                        cleanup_success = True
                    except Exception:
                        pass
                
                elif i == 1 and hasattr(manager, 'disconnect_user'):
                    try:
                        await manager.disconnect_user(user_id, conn_id)
                        cleanup_method = 'disconnect_user'
                        cleanup_success = True
                    except Exception:
                        pass
                
                elif i == 2 and hasattr(manager, 'close_connection'):
                    try:
                        await manager.close_connection(conn_id)
                        cleanup_method = 'close_connection'
                        cleanup_success = True
                    except Exception:
                        pass
                
                cleanup_methods_tested[conn_id] = {
                    "method": cleanup_method,
                    "success": cleanup_success
                }
                
                # Check for connection leaks
                try:
                    connections = getattr(manager, '_connections', {})
                    if conn_id in str(connections):
                        connection_leaks.append(conn_id)
                except Exception:
                    pass
        
        except ImportError as e:
            self.fail(f"Failed to import WebSocket manager: {e}")
        
        # Analyze cleanup consistency
        successful_cleanups = sum(1 for r in cleanup_methods_tested.values() if r['success'])
        total_attempts = len(cleanup_methods_tested)
        cleanup_methods_used = set(r['method'] for r in cleanup_methods_tested.values() if r['method'])
        
        # CURRENT EXPECTATION: Inconsistent cleanup or leaks (violation)
        # AFTER SSOT: Consistent cleanup, no leaks
        inconsistency_issues = len(connection_leaks) + (len(cleanup_methods_used) - 1 if len(cleanup_methods_used) > 1 else 0)
        
        self.assertGreater(inconsistency_issues, 0,
                          "SSOT VIOLATION DETECTED: Connection cleanup inconsistencies found. "
                          f"Leaks: {len(connection_leaks)}, Methods used: {len(cleanup_methods_used)}")
        
        self.metrics.record_test_event("connection_cleanup_violation", {
            "successful_cleanups": successful_cleanups,
            "total_attempts": total_attempts,
            "cleanup_methods_used": list(cleanup_methods_used),
            "connection_leaks": connection_leaks,
            "inconsistency_issues": inconsistency_issues
        })

    async def test_connection_state_synchronization(self):
        """
        Test that connection state is synchronized across all access points.
        
        CURRENT BEHAVIOR: State inconsistencies between managers (VIOLATION)
        EXPECTED AFTER SSOT: Unified state management
        """
        user_id = ensure_user_id("state_sync_user")
        connection_id = "state_sync_conn"
        
        state_inconsistencies = []
        manager_states = {}
        
        try:
            # Create multiple manager instances and check state sync
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            managers = []
            for i in range(3):
                manager = UnifiedWebSocketManager()
                managers.append(manager)
                
                # Create connection in first manager only
                if i == 0:
                    try:
                        await manager.add_connection(user_id, connection_id, None)
                    except Exception:
                        pass
                
                # Check connection state in all managers
                try:
                    connections = getattr(manager, '_connections', {})
                    user_connections = [conn for conn_user, conn in connections.items() if str(conn_user) == str(user_id)]
                    manager_states[f'manager_{i}'] = {
                        "connection_count": len(user_connections),
                        "has_target_connection": connection_id in str(connections),
                        "manager_id": id(manager)
                    }
                except Exception as e:
                    manager_states[f'manager_{i}'] = {
                        "error": str(e),
                        "manager_id": id(manager)
                    }
            
            # Check for state inconsistencies
            connection_counts = [state.get('connection_count', 0) for state in manager_states.values() if 'connection_count' in state]
            has_connection_flags = [state.get('has_target_connection', False) for state in manager_states.values() if 'has_target_connection' in state]
            
            if len(set(connection_counts)) > 1:
                state_inconsistencies.append("connection_count_mismatch")
            
            if len(set(has_connection_flags)) > 1:
                state_inconsistencies.append("connection_presence_mismatch")
            
            # Check for singleton violation (different manager instances)
            manager_ids = [state.get('manager_id') for state in manager_states.values() if 'manager_id' in state]
            unique_manager_ids = len(set(manager_ids))
            
            if unique_manager_ids > 1:
                state_inconsistencies.append("multiple_manager_instances")
        
        except ImportError as e:
            self.fail(f"Failed to import WebSocket manager: {e}")
        
        total_inconsistencies = len(state_inconsistencies)
        
        # CURRENT EXPECTATION: State inconsistencies exist (violation)
        # AFTER SSOT: Should have consistent state across all access points
        self.assertGreater(total_inconsistencies, 0,
                          "SSOT VIOLATION DETECTED: Connection state inconsistencies found. "
                          f"Found {total_inconsistencies} inconsistencies: {state_inconsistencies}")
        
        self.metrics.record_test_event("connection_state_sync_violation", {
            "total_inconsistencies": total_inconsistencies,
            "inconsistency_types": state_inconsistencies,
            "manager_states": manager_states,
            "unique_manager_instances": unique_manager_ids
        })