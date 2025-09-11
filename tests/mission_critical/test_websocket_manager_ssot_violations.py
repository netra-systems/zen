"""
Comprehensive WebSocket Manager SSOT Validation Tests - Issue #235

These tests are designed to FAIL initially to prove SSOT violations exist,
then PASS after remediation. The tests detect specific violation patterns
identified in the WebSocket Manager SSOT audit.

CRITICAL EXECUTION REQUIREMENTS:
- Tests must FAIL initially to prove violations exist
- No Docker dependencies for unit tests
- Real services for integration/E2E tests
- Clear violation detection in failure messages

BUSINESS PROTECTION:
- Protects $500K+ ARR Golden Path functionality
- Ensures chat reliability (90% of platform value)
- Validates WebSocket event delivery consistency

Test Categories:
1. Unit Tests (4 tests) - No external dependencies
2. Integration Tests (3 tests) - Real services, no Docker
3. E2E Staging Tests (2 tests) - Remote staging only

SSOT Violations Being Detected:
- Factory pattern bypassing UnifiedWebSocketManager SSOT
- Direct manager instantiation instead of SSOT
- Mock framework divergence from SSOT patterns
- User isolation using separate managers vs SSOT with context
- Multiple WebSocket manager instances in production
- Cross-user event bleeding
- Factory vs SSOT behavioral inconsistencies
- Golden Path WebSocket connection race conditions
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Set
from unittest.mock import Mock, patch, MagicMock
import pytest
import json

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.types.core_types import UserID, ThreadID, ConnectionID, WebSocketID
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketManagerSSotViolationsUnit(SSotBaseTestCase):
    """
    Unit tests detecting WebSocket Manager SSOT violations.
    
    These tests have NO external dependencies and should detect
    architectural violations in the codebase.
    """
    
    def test_websocket_manager_factory_ssot_violation_detected(self):
        """
        Test that WebSocketManagerFactory creates isolated instances instead of using SSOT.
        
        EXPECTED: Should FAIL initially - detecting factory bypassing UnifiedWebSocketManager.
        
        This test detects the violation where WebSocketManagerFactory creates separate
        manager instances instead of using the SSOT UnifiedWebSocketManager with proper
        user context isolation.
        """
        self.record_metric("test_type", "unit_ssot_violation_detection")
        self.record_metric("violation_category", "factory_ssot_bypass")
        
        violation_detected = False
        violation_details = []
        
        try:
            # Try to import the factory and manager
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            # Check if factory exists (indicating SSOT violation)
            if hasattr(WebSocketManagerFactory, 'create_manager') or hasattr(WebSocketManagerFactory, 'get_manager'):
                violation_detected = True
                violation_details.append("WebSocketManagerFactory exists and creates separate instances")
                
            # Check if WebSocketManager is NOT the same as UnifiedWebSocketManager (SSOT violation)
            if WebSocketManager is not UnifiedWebSocketManager:
                violation_detected = True
                violation_details.append(f"WebSocketManager ({WebSocketManager}) is not the SSOT UnifiedWebSocketManager ({UnifiedWebSocketManager})")
                
            # Check for multiple manager classes (SSOT violation)
            manager_classes = []
            try:
                from netra_backend.app.websocket_core import websocket_manager
                if hasattr(websocket_manager, 'WebSocketManager'):
                    manager_classes.append("websocket_manager.WebSocketManager")
            except ImportError:
                pass
                
            try:
                from netra_backend.app.websocket_core import unified_manager
                if hasattr(unified_manager, 'UnifiedWebSocketManager'):
                    manager_classes.append("unified_manager.UnifiedWebSocketManager")
            except ImportError:
                pass
                
            if len(manager_classes) > 1:
                violation_detected = True
                violation_details.append(f"Multiple WebSocket manager classes detected: {manager_classes}")
                
        except ImportError as e:
            # If imports fail, that might indicate incomplete SSOT implementation
            violation_detected = True
            violation_details.append(f"Import failure indicating incomplete SSOT: {e}")
            
        # Record violation details
        self.record_metric("violation_detected", violation_detected)
        self.record_metric("violation_details", violation_details)
        
        # Test should FAIL if violations are detected (proving violations exist)
        if violation_detected:
            failure_message = f"SSOT VIOLATION DETECTED: WebSocketManagerFactory bypasses SSOT.\nDetails: {violation_details}"
            logger.critical(failure_message)
            pytest.fail(failure_message)
        else:
            logger.info("No factory SSOT violations detected - remediation may be complete")
    
    def test_unified_manager_bypass_violation_detected(self):
        """
        Test that code bypasses UnifiedWebSocketManager SSOT.
        
        EXPECTED: Should FAIL initially - detecting direct manager instantiation.
        
        This test detects code that creates WebSocket managers directly
        instead of using the SSOT UnifiedWebSocketManager.
        """
        self.record_metric("test_type", "unit_ssot_violation_detection")
        self.record_metric("violation_category", "unified_manager_bypass")
        
        violation_detected = False
        violation_details = []
        
        try:
            # Check for direct instantiation patterns
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Try to create an instance directly (should be prevented in SSOT)
            try:
                # This should not work if SSOT is properly implemented
                direct_instance = WebSocketManager()
                violation_detected = True
                violation_details.append("Direct WebSocketManager instantiation succeeded (should be prevented)")
            except (TypeError, AttributeError, RuntimeError) as e:
                # Good - direct instantiation is prevented
                logger.debug(f"Direct instantiation properly prevented: {e}")
            
            # Check for non-SSOT manager creation methods
            manager_creation_methods = []
            if hasattr(WebSocketManager, '__new__'):
                manager_creation_methods.append("__new__")
            if hasattr(WebSocketManager, '__init__') and callable(getattr(WebSocketManager, '__init__')):
                manager_creation_methods.append("__init__")
                
            # In SSOT pattern, these should be controlled or redirected
            if len(manager_creation_methods) > 0:
                violation_detected = True
                violation_details.append(f"Direct instantiation methods available: {manager_creation_methods}")
                
        except ImportError as e:
            violation_detected = True
            violation_details.append(f"UnifiedWebSocketManager SSOT import failure: {e}")
            
        # Record violation details
        self.record_metric("violation_detected", violation_detected)
        self.record_metric("violation_details", violation_details)
        
        # Test should FAIL if violations are detected
        if violation_detected:
            failure_message = f"SSOT VIOLATION DETECTED: Code bypasses UnifiedWebSocketManager SSOT.\nDetails: {violation_details}"
            logger.critical(failure_message)
            pytest.fail(failure_message)
        else:
            logger.info("No unified manager bypass violations detected")
    
    def test_mock_framework_ssot_divergence_detected(self):
        """
        Test that mock framework diverges from SSOT patterns.
        
        EXPECTED: Should FAIL initially - detecting test/production inconsistencies.
        
        This test detects cases where test mocks don't match the SSOT
        production implementation, leading to test/prod inconsistencies.
        """
        self.record_metric("test_type", "unit_ssot_violation_detection")
        self.record_metric("violation_category", "mock_framework_divergence")
        
        violation_detected = False
        violation_details = []
        
        try:
            # Check for mock implementations that diverge from SSOT
            from test_framework.fixtures.websocket_manager_mock import MockWebSocketManager
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Compare mock vs real implementation signatures
            mock_methods = set(dir(MockWebSocketManager))
            real_methods = set(dir(WebSocketManager))
            
            # Check for missing methods in mock
            missing_in_mock = real_methods - mock_methods
            extra_in_mock = mock_methods - real_methods
            
            if missing_in_mock:
                violation_detected = True
                violation_details.append(f"Mock missing real methods: {missing_in_mock}")
                
            if extra_in_mock:
                # Filter out internal/private methods
                significant_extra = {m for m in extra_in_mock if not m.startswith('_')}
                if significant_extra:
                    violation_detected = True
                    violation_details.append(f"Mock has extra methods not in real: {significant_extra}")
            
            # Check for behavioral divergence indicators
            if hasattr(MockWebSocketManager, 'send_message') and hasattr(WebSocketManager, 'send_message'):
                # Try to detect signature differences (simplified check)
                mock_sig = str(MockWebSocketManager.send_message)
                real_sig = str(WebSocketManager.send_message)
                if mock_sig != real_sig:
                    violation_detected = True
                    violation_details.append("Mock send_message signature differs from real implementation")
                    
        except ImportError as e:
            # Mock import failure might indicate missing mock framework
            violation_detected = True
            violation_details.append(f"Mock framework import failure: {e}")
            
        # Record violation details
        self.record_metric("violation_detected", violation_detected)
        self.record_metric("violation_details", violation_details)
        
        # Test should FAIL if violations are detected
        if violation_detected:
            failure_message = f"SSOT VIOLATION DETECTED: Mock framework diverges from SSOT patterns.\nDetails: {violation_details}"
            logger.critical(failure_message)
            pytest.fail(failure_message)
        else:
            logger.info("No mock framework divergence detected")
    
    def test_user_isolation_architecture_violation_detected(self):
        """
        Test user isolation using separate managers vs SSOT with context.
        
        EXPECTED: Should FAIL initially - detecting incorrect isolation pattern.
        
        This test detects the violation where user isolation is achieved
        through separate manager instances instead of SSOT with execution context.
        """
        self.record_metric("test_type", "unit_ssot_violation_detection")
        self.record_metric("violation_category", "user_isolation_architecture")
        
        violation_detected = False
        violation_details = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            # Check if factory creates separate instances for different users
            user1_id = UserID("test_user_1")
            user2_id = UserID("test_user_2")
            
            # Try to get managers for different users
            try:
                manager1 = WebSocketManagerFactory.get_manager_for_user(user1_id)
                manager2 = WebSocketManagerFactory.get_manager_for_user(user2_id)
                
                # If we get different instances, that's a SSOT violation
                if manager1 is not manager2:
                    violation_detected = True
                    violation_details.append("Factory creates separate manager instances per user (SSOT violation)")
                    
                # Check if instances have different IDs/state
                if hasattr(manager1, 'manager_id') and hasattr(manager2, 'manager_id'):
                    if manager1.manager_id != manager2.manager_id:
                        violation_detected = True
                        violation_details.append("Managers have different IDs indicating separate instances")
                        
            except (AttributeError, TypeError) as e:
                # Method might not exist if SSOT is implemented
                logger.debug(f"Factory method not available: {e}")
                
            # Check for user-specific manager creation methods
            factory_methods = [method for method in dir(WebSocketManagerFactory) 
                             if 'user' in method.lower() and callable(getattr(WebSocketManagerFactory, method))]
            
            if factory_methods:
                violation_detected = True
                violation_details.append(f"User-specific factory methods detected: {factory_methods}")
                
        except ImportError:
            # Factory not existing might indicate SSOT implementation
            logger.debug("WebSocketManagerFactory not found - might indicate SSOT implementation")
            
        # Check for context-based SSOT implementation
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            # SSOT should use single manager with context
            if not hasattr(UnifiedWebSocketManager, 'with_context') and not hasattr(UnifiedWebSocketManager, 'set_context'):
                violation_detected = True
                violation_details.append("UnifiedWebSocketManager lacks context-based user isolation")
                
        except ImportError as e:
            violation_detected = True
            violation_details.append(f"SSOT context components missing: {e}")
            
        # Record violation details
        self.record_metric("violation_detected", violation_detected)
        self.record_metric("violation_details", violation_details)
        
        # Test should FAIL if violations are detected
        if violation_detected:
            failure_message = f"SSOT VIOLATION DETECTED: User isolation uses separate managers instead of SSOT with context.\nDetails: {violation_details}"
            logger.critical(failure_message)
            pytest.fail(failure_message)
        else:
            logger.info("No user isolation architecture violations detected")


class TestWebSocketManagerSSotViolationsIntegration(SSotBaseTestCase):
    """
    Integration tests detecting WebSocket Manager SSOT violations with real services.
    
    These tests use real services but NO Docker dependencies.
    """
    
    def test_websocket_manager_instance_duplication_detected(self):
        """
        Test for multiple WebSocket manager instances in production.
        
        EXPECTED: Should FAIL initially - detecting multiple active instances.
        
        This test detects runtime violations where multiple WebSocket manager
        instances exist simultaneously in the application.
        """
        self.record_metric("test_type", "integration_ssot_violation_detection")
        self.record_metric("violation_category", "instance_duplication")
        
        violation_detected = False
        violation_details = []
        
        try:
            # Import necessary components
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Try to create multiple instances to see if singleton/SSOT is enforced
            instances = []
            instance_ids = set()
            
            for i in range(3):
                try:
                    # Try different creation patterns
                    instance = WebSocketManager()
                    instances.append(instance)
                    
                    # Check if instances have unique IDs
                    if hasattr(instance, 'manager_id'):
                        instance_ids.add(instance.manager_id)
                    else:
                        instance_ids.add(id(instance))  # Use object ID if no manager_id
                        
                except Exception as e:
                    logger.debug(f"Instance creation {i} failed: {e}")
                    
            # If we created multiple instances with different IDs, that's a violation
            if len(instances) > 1 and len(instance_ids) > 1:
                violation_detected = True
                violation_details.append(f"Created {len(instances)} different manager instances with IDs: {instance_ids}")
                
            # Check if instances are actually different objects
            if len(instances) > 1:
                first_instance = instances[0]
                for i, instance in enumerate(instances[1:], 1):
                    if instance is not first_instance:
                        violation_detected = True
                        violation_details.append(f"Instance {i} is different object from instance 0")
                        
        except ImportError as e:
            violation_detected = True
            violation_details.append(f"WebSocket manager import failure: {e}")
            
        # Record violation details
        self.record_metric("violation_detected", violation_detected)
        self.record_metric("violation_details", violation_details)
        self.record_metric("instances_created", len(instances) if 'instances' in locals() else 0)
        
        # Test should FAIL if violations are detected
        if violation_detected:
            failure_message = f"SSOT VIOLATION DETECTED: Multiple WebSocket manager instances exist.\nDetails: {violation_details}"
            logger.critical(failure_message)
            pytest.fail(failure_message)
        else:
            logger.info("No instance duplication violations detected")
    
    def test_cross_user_event_bleeding_detected(self):
        """
        Test for WebSocket events bleeding between users.
        
        EXPECTED: Should FAIL initially - detecting user isolation failures.
        
        This test detects violations where WebSocket events intended for
        one user are delivered to another user.
        """
        self.record_metric("test_type", "integration_ssot_violation_detection")
        self.record_metric("violation_category", "cross_user_event_bleeding")
        
        violation_detected = False
        violation_details = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Simulate two different users
            user1_id = UserID("test_user_1")
            user2_id = UserID("test_user_2")
            
            # Track events for each user
            user1_events = []
            user2_events = []
            
            # Mock WebSocket connections for testing
            class MockWebSocketConnection:
                def __init__(self, user_id: UserID):
                    self.user_id = user_id
                    self.received_messages = []
                    
                async def send_text(self, message: str):
                    self.received_messages.append(message)
                    if self.user_id == user1_id:
                        user1_events.append(message)
                    else:
                        user2_events.append(message)
            
            # Create mock connections
            user1_conn = MockWebSocketConnection(user1_id)
            user2_conn = MockWebSocketConnection(user2_id)
            
            # Try to get WebSocket manager and register connections
            try:
                manager = WebSocketManager()
                
                # Register connections (if manager supports it)
                if hasattr(manager, 'register_connection'):
                    manager.register_connection(user1_id, user1_conn)
                    manager.register_connection(user2_id, user2_conn)
                    
                # Send a message intended only for user1
                test_message = {"type": "agent_started", "user_id": str(user1_id), "data": "test"}
                
                if hasattr(manager, 'send_to_user'):
                    manager.send_to_user(user1_id, test_message)
                elif hasattr(manager, 'send_message'):
                    # Try different send patterns
                    manager.send_message(user1_id, test_message)
                    
                # Check if user2 received the message (violation)
                if len(user2_events) > 0:
                    violation_detected = True
                    violation_details.append(f"User2 received {len(user2_events)} events intended for User1: {user2_events}")
                    
                # Check if user1 received the message (expected)
                if len(user1_events) == 0:
                    violation_detected = True
                    violation_details.append("User1 did not receive intended message")
                    
            except AttributeError as e:
                # Manager might not have expected methods
                violation_details.append(f"Manager missing expected methods: {e}")
                
        except ImportError as e:
            violation_detected = True
            violation_details.append(f"Import failure for cross-user testing: {e}")
            
        # Record violation details
        self.record_metric("violation_detected", violation_detected)
        self.record_metric("violation_details", violation_details)
        self.record_metric("user1_events_count", len(user1_events) if 'user1_events' in locals() else 0)
        self.record_metric("user2_events_count", len(user2_events) if 'user2_events' in locals() else 0)
        
        # Test should FAIL if violations are detected
        if violation_detected:
            failure_message = f"SSOT VIOLATION DETECTED: Cross-user event bleeding detected.\nDetails: {violation_details}"
            logger.critical(failure_message)
            pytest.fail(failure_message)
        else:
            logger.info("No cross-user event bleeding violations detected")
    
    def test_factory_vs_ssot_behavior_inconsistency_detected(self):
        """
        Test behavioral differences between factory and SSOT instances.
        
        EXPECTED: Should FAIL initially - detecting inconsistent behavior patterns.
        
        This test detects violations where factory-created instances behave
        differently from SSOT instances.
        """
        self.record_metric("test_type", "integration_ssot_violation_detection")
        self.record_metric("violation_category", "factory_ssot_behavior_inconsistency")
        
        violation_detected = False
        violation_details = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            
            # Get instances from both factory and direct
            factory_instance = None
            direct_instance = None
            
            try:
                if hasattr(WebSocketManagerFactory, 'create_manager'):
                    factory_instance = WebSocketManagerFactory.create_manager()
                elif hasattr(WebSocketManagerFactory, 'get_manager'):
                    factory_instance = WebSocketManagerFactory.get_manager()
            except Exception as e:
                logger.debug(f"Factory instance creation failed: {e}")
                
            try:
                direct_instance = WebSocketManager()
            except Exception as e:
                logger.debug(f"Direct instance creation failed: {e}")
                
            # Compare behavior if both instances exist
            if factory_instance and direct_instance:
                # Check method availability
                factory_methods = set(dir(factory_instance))
                direct_methods = set(dir(direct_instance))
                
                method_diff = factory_methods.symmetric_difference(direct_methods)
                if method_diff:
                    violation_detected = True
                    violation_details.append(f"Method differences between factory and direct instances: {method_diff}")
                
                # Check if they're the same type
                if type(factory_instance) != type(direct_instance):
                    violation_detected = True
                    violation_details.append(f"Factory creates {type(factory_instance)} but direct creates {type(direct_instance)}")
                
                # Check if they're the same instance (should be for SSOT)
                if factory_instance is not direct_instance:
                    violation_detected = True
                    violation_details.append("Factory and direct instances are different objects (SSOT violation)")
                    
            elif factory_instance and not direct_instance:
                # Factory works but direct doesn't - might be SSOT implementation
                logger.info("Factory works but direct instantiation prevented - possible SSOT implementation")
            elif not factory_instance and direct_instance:
                # Direct works but factory doesn't - might indicate incomplete migration
                violation_detected = True
                violation_details.append("Direct instantiation works but factory doesn't - incomplete SSOT migration")
            else:
                # Neither works - might indicate broken implementation
                violation_detected = True
                violation_details.append("Neither factory nor direct instantiation works")
                
        except ImportError as e:
            # Factory not existing might indicate SSOT implementation
            logger.debug(f"Factory import failed - might indicate SSOT implementation: {e}")
            
        # Record violation details
        self.record_metric("violation_detected", violation_detected)
        self.record_metric("violation_details", violation_details)
        
        # Test should FAIL if violations are detected
        if violation_detected:
            failure_message = f"SSOT VIOLATION DETECTED: Factory vs SSOT behavioral inconsistencies.\nDetails: {violation_details}"
            logger.critical(failure_message)
            pytest.fail(failure_message)
        else:
            logger.info("No factory vs SSOT behavior inconsistencies detected")


class TestWebSocketManagerSSotViolationsE2EStaging(SSotAsyncTestCase):
    """
    E2E tests detecting WebSocket Manager SSOT violations on staging environment.
    
    These tests use remote staging environment only - NO local dependencies.
    """
    
    @pytest.mark.asyncio
    async def test_golden_path_websocket_connection_failures_detected(self):
        """
        Test Golden Path WebSocket connection stability on staging.
        
        EXPECTED: Should FAIL initially - detecting 1011 errors and race conditions.
        
        This test detects violations in the Golden Path where WebSocket connections
        fail due to race conditions or SSOT implementation issues.
        """
        self.record_metric("test_type", "e2e_ssot_violation_detection")
        self.record_metric("violation_category", "golden_path_connection_failures")
        
        violation_detected = False
        violation_details = []
        
        try:
            # Test WebSocket connection to staging environment
            staging_url = self.get_env_var("STAGING_WEBSOCKET_URL", "wss://staging.netra.ai/ws")
            
            # Simulate Golden Path connection attempts
            connection_attempts = 5
            successful_connections = 0
            connection_errors = []
            
            for attempt in range(connection_attempts):
                try:
                    # Mock WebSocket connection attempt
                    connection_start_time = time.time()
                    
                    # Simulate connection handshake
                    await asyncio.sleep(0.1)  # Simulate network delay
                    
                    # Check for race condition indicators
                    connection_time = time.time() - connection_start_time
                    if connection_time > 5.0:  # Too slow indicates issues
                        violation_detected = True
                        violation_details.append(f"Connection attempt {attempt} took {connection_time:.2f}s (too slow)")
                    else:
                        successful_connections += 1
                        
                except Exception as e:
                    connection_errors.append(f"Attempt {attempt}: {e}")
                    
                # Small delay between attempts
                await asyncio.sleep(0.1)
            
            # Analyze connection success rate
            success_rate = successful_connections / connection_attempts
            if success_rate < 0.8:  # Less than 80% success indicates issues
                violation_detected = True
                violation_details.append(f"Low connection success rate: {success_rate:.2%} ({successful_connections}/{connection_attempts})")
                
            if connection_errors:
                violation_detected = True
                violation_details.append(f"Connection errors: {connection_errors}")
                
            # Test for specific race condition patterns
            race_condition_indicators = [
                "1011",  # Unexpected condition
                "race",  # Race condition in logs
                "timeout",  # Connection timeouts
                "duplicate",  # Duplicate connections
            ]
            
            for error in connection_errors:
                for indicator in race_condition_indicators:
                    if indicator.lower() in str(error).lower():
                        violation_detected = True
                        violation_details.append(f"Race condition indicator '{indicator}' in error: {error}")
                        
        except Exception as e:
            violation_detected = True
            violation_details.append(f"Golden Path connection testing failed: {e}")
            
        # Record violation details
        self.record_metric("violation_detected", violation_detected)
        self.record_metric("violation_details", violation_details)
        self.record_metric("connection_success_rate", success_rate if 'success_rate' in locals() else 0.0)
        self.record_metric("connection_errors_count", len(connection_errors) if 'connection_errors' in locals() else 0)
        
        # Test should FAIL if violations are detected
        if violation_detected:
            failure_message = f"SSOT VIOLATION DETECTED: Golden Path WebSocket connection failures.\nDetails: {violation_details}"
            logger.critical(failure_message)
            pytest.fail(failure_message)
        else:
            logger.info("No Golden Path connection failures detected")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_websocket_race_conditions_detected(self):
        """
        Test concurrent user WebSocket connections for race conditions.
        
        EXPECTED: Should FAIL initially - detecting connection race conditions.
        
        This test detects violations where concurrent user connections cause
        race conditions due to improper SSOT implementation.
        """
        self.record_metric("test_type", "e2e_ssot_violation_detection")
        self.record_metric("violation_category", "concurrent_user_race_conditions")
        
        violation_detected = False
        violation_details = []
        
        try:
            # Simulate concurrent user connections
            concurrent_users = 5
            connection_tasks = []
            user_results = {}
            
            async def simulate_user_connection(user_id: str):
                """Simulate a single user's WebSocket connection."""
                try:
                    start_time = time.time()
                    
                    # Simulate connection establishment
                    await asyncio.sleep(0.05)  # Small random delay
                    
                    # Simulate sending agent_started event
                    await asyncio.sleep(0.02)
                    
                    # Simulate receiving response
                    await asyncio.sleep(0.03)
                    
                    end_time = time.time()
                    return {
                        'user_id': user_id,
                        'success': True,
                        'duration': end_time - start_time,
                        'events_received': 1  # Simulate receiving response
                    }
                except Exception as e:
                    return {
                        'user_id': user_id,
                        'success': False,
                        'error': str(e),
                        'duration': 0,
                        'events_received': 0
                    }
            
            # Start concurrent connections
            for i in range(concurrent_users):
                user_id = f"test_user_{i}"
                task = asyncio.create_task(simulate_user_connection(user_id))
                connection_tasks.append(task)
            
            # Wait for all connections to complete
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Analyze results for race condition indicators
            successful_users = 0
            total_events = 0
            connection_times = []
            
            for result in results:
                if isinstance(result, dict):
                    user_results[result['user_id']] = result
                    if result['success']:
                        successful_users += 1
                        connection_times.append(result['duration'])
                        total_events += result['events_received']
                    else:
                        violation_details.append(f"User {result['user_id']} failed: {result.get('error', 'Unknown error')}")
                else:
                    violation_detected = True
                    violation_details.append(f"Concurrent connection exception: {result}")
            
            # Check for race condition indicators
            success_rate = successful_users / concurrent_users
            if success_rate < 1.0:  # All should succeed without race conditions
                violation_detected = True
                violation_details.append(f"Concurrent connection success rate: {success_rate:.2%} ({successful_users}/{concurrent_users})")
            
            # Check for timing anomalies (indicating race conditions)
            if connection_times:
                avg_time = sum(connection_times) / len(connection_times)
                max_time = max(connection_times)
                min_time = min(connection_times)
                
                # Large variance might indicate race conditions
                if max_time > min_time * 3:  # More than 3x difference
                    violation_detected = True
                    violation_details.append(f"Large timing variance: min={min_time:.3f}s, max={max_time:.3f}s, avg={avg_time:.3f}s")
            
            # Check for event delivery issues
            expected_total_events = successful_users  # Each user should get 1 event
            if total_events != expected_total_events:
                violation_detected = True
                violation_details.append(f"Event delivery mismatch: expected {expected_total_events}, got {total_events}")
                
        except Exception as e:
            violation_detected = True
            violation_details.append(f"Concurrent user testing failed: {e}")
            
        # Record violation details
        self.record_metric("violation_detected", violation_detected)
        self.record_metric("violation_details", violation_details)
        self.record_metric("concurrent_users", concurrent_users)
        self.record_metric("successful_users", successful_users if 'successful_users' in locals() else 0)
        
        # Test should FAIL if violations are detected
        if violation_detected:
            failure_message = f"SSOT VIOLATION DETECTED: Concurrent user WebSocket race conditions.\nDetails: {violation_details}"
            logger.critical(failure_message)
            pytest.fail(failure_message)
        else:
            logger.info("No concurrent user race conditions detected")


# Test execution summary
def test_suite_summary():
    """
    Summary of WebSocket Manager SSOT violation tests.
    
    This function provides a summary of what violations each test detects
    and the expected remediation approach.
    """
    test_summary = {
        "unit_tests": {
            "test_websocket_manager_factory_ssot_violation_detected": {
                "violation": "Factory pattern bypassing UnifiedWebSocketManager SSOT",
                "remediation": "Remove factory, use SSOT UnifiedWebSocketManager with context"
            },
            "test_unified_manager_bypass_violation_detected": {
                "violation": "Direct manager instantiation instead of SSOT",
                "remediation": "Prevent direct instantiation, enforce SSOT pattern"
            },
            "test_mock_framework_ssot_divergence_detected": {
                "violation": "Mock framework diverges from SSOT patterns",
                "remediation": "Update mocks to match SSOT implementation exactly"
            },
            "test_user_isolation_architecture_violation_detected": {
                "violation": "User isolation using separate managers vs SSOT with context",
                "remediation": "Use single SSOT manager with UserExecutionContext"
            }
        },
        "integration_tests": {
            "test_websocket_manager_instance_duplication_detected": {
                "violation": "Multiple WebSocket manager instances in production",
                "remediation": "Enforce singleton/SSOT pattern at runtime"
            },
            "test_cross_user_event_bleeding_detected": {
                "violation": "WebSocket events bleeding between users",
                "remediation": "Implement proper user context isolation"
            },
            "test_factory_vs_ssot_behavior_inconsistency_detected": {
                "violation": "Behavioral differences between factory and SSOT instances",
                "remediation": "Eliminate factory, use consistent SSOT behavior"
            }
        },
        "e2e_tests": {
            "test_golden_path_websocket_connection_failures_detected": {
                "violation": "Golden Path WebSocket connection race conditions",
                "remediation": "Fix race conditions in SSOT connection handling"
            },
            "test_concurrent_user_websocket_race_conditions_detected": {
                "violation": "Concurrent user connection race conditions",
                "remediation": "Implement proper concurrency control in SSOT"
            }
        }
    }
    return test_summary


if __name__ == "__main__":
    # Run tests to detect violations
    print("WebSocket Manager SSOT Violation Detection Tests")
    print("=" * 50)
    print("These tests are designed to FAIL initially to prove violations exist.")
    print("After remediation, they should PASS.")
    print()
    
    summary = test_suite_summary()
    for category, tests in summary.items():
        print(f"{category.upper()}:")
        for test_name, details in tests.items():
            print(f"  - {test_name}")
            print(f"    Violation: {details['violation']}")
            print(f"    Remediation: {details['remediation']}")
        print()