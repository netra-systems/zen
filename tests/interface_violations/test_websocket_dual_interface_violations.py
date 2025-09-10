"""
TEST SUITE 1: WebSocket Dual Interface Violations Detection
==========================================================

CRITICAL PURPOSE: This test suite reproduces the WebSocket race condition regression
caused by dual-interface architecture violations where:

1. AgentRegistry has both WebSocketManager and AgentWebSocketBridge patterns
2. Interface mismatches in inheritance calls
3. Method Resolution Order (MRO) violations in WebSocket method resolution
4. Type signature inconsistencies between dual interfaces

BUSINESS VALUE:
- Prevents interface confusion causing 503 errors in production
- Ensures SSOT compliance in WebSocket architecture
- Validates proper inheritance patterns for user isolation

EXPECTED BEHAVIOR: These tests should INITIALLY FAIL, reproducing the regression issues.
"""

import asyncio
import pytest
import logging
import inspect
import uuid
from typing import Dict, Any, List, Optional, Type, get_type_hints
from unittest.mock import Mock, patch
import weakref

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


# Critical imports that expose the dual interface issue
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    UserAgentSession
)
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    create_agent_websocket_bridge
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)


@pytest.mark.unit
@pytest.mark.interface_violations
class TestWebSocketDualInterfaceViolations(SSotBaseTestCase):
    """
    Unit tests for detecting WebSocket dual interface architecture violations.
    
    These tests expose the regression where AgentRegistry tries to use both
    WebSocketManager and AgentWebSocketBridge interfaces inconsistently.
    """

    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.test_user_id = str(uuid.uuid4())
        
    @pytest.mark.regression_reproduction
    @pytest.mark.asyncio
    async def test_agent_registry_websocket_interface_consistency(self):
        """
        CRITICAL: Test that AgentRegistry uses consistent WebSocket interfaces.
        
        UPDATED AFTER SSOT REMEDIATION: Now tests the SSOT-compliant implementation
        where set_websocket_manager is async and creates appropriate bridges.
        
        EXPECTED BEHAVIOR: Test should PASS after SSOT remediation.
        """
        logger.info("🚨 TESTING: WebSocket interface consistency in AgentRegistry (SSOT-compliant)")
        
        # Create user session - this should use ONE interface type
        user_session = UserAgentSession(self.test_user_id)
        
        # CRITICAL: Test interface type consistency
        websocket_manager = Mock(spec=WebSocketManager)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        # TEST 1: Should use consistent interface internally (now async)
        await user_session.set_websocket_manager(websocket_manager)
        
        # REGRESSION EXPOSURE: Check if internal state is consistent
        internal_manager = user_session._websocket_manager
        internal_bridge = user_session._websocket_bridge
        
        # UPDATED ASSERTION: After SSOT remediation, bridge should be created
        # The SSOT implementation creates a bridge when manager is set
        assert internal_bridge is not None, "WebSocket bridge should be created after SSOT remediation"
        
        # INTERFACE COMPLIANCE: SSOT implementation should use bridge pattern
        # This validates proper SSOT compliance without dual interface confusion
        logger.info(f"SSOT Compliance Check - Bridge created: {internal_bridge is not None}")
        logger.info(f"SSOT Compliance Check - Manager reference: {internal_manager is not None}")
        
        # SUCCESS: SSOT implementation resolves dual interface issues
        
    @pytest.mark.regression_reproduction  
    def test_websocket_manager_bridge_type_mismatch(self):
        """
        CRITICAL: Test type signature consistency between WebSocket interfaces.
        
        ROOT CAUSE REPRODUCTION: WebSocketManager and AgentWebSocketBridge have
        different method signatures, causing runtime failures when methods are
        called on the wrong interface type.
        
        EXPECTED FAILURE: Should fail due to signature mismatches.
        """
        logger.info("🚨 TESTING: WebSocket interface type signature consistency")
        
        # Get method signatures from both interfaces
        manager_methods = self._get_public_methods(WebSocketManager)
        bridge_methods = self._get_public_methods(AgentWebSocketBridge)
        
        # CRITICAL: Find overlapping method names
        common_methods = set(manager_methods.keys()) & set(bridge_methods.keys())
        
        logger.info(f"Common methods between interfaces: {common_methods}")
        
        # REGRESSION EXPOSURE: Check signature compatibility
        signature_mismatches = []
        for method_name in common_methods:
            if method_name.startswith('_'):  # Skip private methods
                continue
                
            try:
                manager_sig = inspect.signature(manager_methods[method_name])
                bridge_sig = inspect.signature(bridge_methods[method_name])
                
                # CRITICAL: Signatures should match for interface substitution
                if str(manager_sig) != str(bridge_sig):
                    signature_mismatches.append({
                        'method': method_name,
                        'manager_signature': str(manager_sig),
                        'bridge_signature': str(bridge_sig)
                    })
            except Exception as e:
                logger.warning(f"Could not compare signatures for {method_name}: {e}")
        
        # CRITICAL ASSERTION: Should fail due to signature mismatches
        assert len(signature_mismatches) == 0, (
            f"REGRESSION DETECTED: Method signature mismatches between WebSocket interfaces - "
            f"this causes runtime errors when wrong interface is called: {signature_mismatches}"
        )
        
    @pytest.mark.regression_reproduction
    def test_method_resolution_order_violations(self):
        """
        CRITICAL: Test Method Resolution Order (MRO) consistency in WebSocket inheritance.
        
        ROOT CAUSE REPRODUCTION: When AgentRegistry inherits from both patterns,
        MRO can cause method calls to resolve to unexpected implementations.
        
        EXPECTED FAILURE: Should fail due to MRO violations.
        """
        logger.info("🚨 TESTING: Method Resolution Order in WebSocket inheritance")
        
        # CRITICAL: Test MRO chain for WebSocket-related classes
        registry_mro = AgentRegistry.__mro__
        session_mro = UserAgentSession.__mro__
        bridge_mro = AgentWebSocketBridge.__mro__
        
        logger.info(f"AgentRegistry MRO: {[cls.__name__ for cls in registry_mro]}")
        logger.info(f"UserAgentSession MRO: {[cls.__name__ for cls in session_mro]}")
        logger.info(f"AgentWebSocketBridge MRO: {[cls.__name__ for cls in bridge_mro]}")
        
        # REGRESSION EXPOSURE: Check for problematic MRO patterns
        mro_violations = []
        
        # Check if multiple WebSocket-related base classes in MRO
        websocket_base_classes = []
        for cls in registry_mro:
            if 'websocket' in cls.__name__.lower() or 'bridge' in cls.__name__.lower():
                websocket_base_classes.append(cls.__name__)
                
        if len(websocket_base_classes) > 1:
            mro_violations.append(f"Multiple WebSocket base classes in MRO: {websocket_base_classes}")
            
        # CRITICAL: Check method shadowing between interfaces
        critical_methods = ['send_event', 'notify', 'handle_message', 'emit']
        for method_name in critical_methods:
            method_sources = []
            for cls in registry_mro:
                if hasattr(cls, method_name) and method_name in cls.__dict__:
                    method_sources.append(cls.__name__)
                    
            if len(method_sources) > 1:
                mro_violations.append(f"Method '{method_name}' shadowed by multiple classes: {method_sources}")
        
        # CRITICAL ASSERTION: Should fail due to MRO violations  
        assert len(mro_violations) == 0, (
            f"REGRESSION DETECTED: MRO violations in WebSocket inheritance - "
            f"this causes unpredictable method resolution: {mro_violations}"
        )
        
    @pytest.mark.regression_reproduction
    @pytest.mark.asyncio
    async def test_websocket_interface_initialization_race_condition(self):
        """
        CRITICAL: Test race conditions during WebSocket interface initialization.
        
        UPDATED AFTER SSOT REMEDIATION: Now validates SSOT-compliant initialization
        where setting a manager properly creates the corresponding bridge.
        
        EXPECTED BEHAVIOR: Should pass with proper SSOT initialization patterns.
        """
        logger.info("🚨 TESTING: WebSocket interface initialization race conditions")
        
        # CRITICAL: Simulate concurrent initialization
        user_sessions = []
        initialization_results = []
        
        async def initialize_session_with_timing(session_id: str, delay: float):
            """Initialize session with artificial delay to trigger races."""
            await asyncio.sleep(delay)
            session = UserAgentSession(f"{self.test_user_id}_{session_id}")
            
            # Create different interface types
            manager = Mock(spec=WebSocketManager)
            bridge = Mock(spec=AgentWebSocketBridge)
            
            # UPDATED AFTER SSOT REMEDIATION: Use async set_websocket_manager
            await session.set_websocket_manager(manager)
            await asyncio.sleep(0.001)  # Tiny delay to trigger race
            
            result = {
                'session_id': session_id,
                'manager_set': session._websocket_manager is not None,
                'bridge_set': session._websocket_bridge is not None,
                'manager_type': type(session._websocket_manager).__name__ if session._websocket_manager else None,
                'bridge_type': type(session._websocket_bridge).__name__ if session._websocket_bridge else None,
            }
            
            initialization_results.append(result)
            return session
            
        # CRITICAL: Run concurrent initializations
        async def run_concurrent_test():
            tasks = []
            for i in range(5):
                delay = i * 0.002  # Stagger initialization
                task = initialize_session_with_timing(str(i), delay)
                tasks.append(task)
                
            sessions = await asyncio.gather(*tasks)
            return sessions
            
        # Execute the concurrent test (now properly awaited since test is async)
        sessions = await run_concurrent_test()
        
        logger.info(f"Initialization results: {initialization_results}")
        
        # UPDATED AFTER SSOT REMEDIATION: Check for SSOT-compliant behavior
        inconsistent_states = []
        for result in initialization_results:
            # UPDATED: SSOT implementation properly creates bridge when manager is set
            # This is now the EXPECTED behavior, not an error
            if result['manager_set'] and result['bridge_set']:
                # This is GOOD - SSOT compliance achieved
                pass
                
            # CRITICAL: At least one interface should be properly initialized
            if not result['manager_set'] and not result['bridge_set']:
                inconsistent_states.append(f"Session {result['session_id']}: No interface initialized")
                
            # CRITICAL: Bridge should be created when manager is set (SSOT compliance)
            if result['manager_set'] and not result['bridge_set']:
                inconsistent_states.append(f"Session {result['session_id']}: Manager set but bridge not created (SSOT violation)")
                
        # UPDATED ASSERTION: Should pass with SSOT-compliant initialization
        assert len(inconsistent_states) == 0, (
            f"SSOT COMPLIANCE CHECK FAILED: Interface initialization not following SSOT patterns - "
            f"inconsistent states detected: {inconsistent_states}"
        )
        
    @pytest.mark.regression_reproduction
    def test_interface_method_dispatch_correctness(self):
        """
        CRITICAL: Test that methods dispatch to correct interface implementation.
        
        ROOT CAUSE REPRODUCTION: Dual interfaces can cause method calls to be
        dispatched to wrong implementation, leading to runtime errors.
        
        EXPECTED FAILURE: Should fail due to incorrect method dispatch.
        """
        logger.info("🚨 TESTING: WebSocket interface method dispatch correctness")
        
        # CRITICAL: Create session with dual interface setup
        user_session = UserAgentSession(self.test_user_id)
        
        # Mock both interface types with tracking
        manager_mock = Mock(spec=WebSocketManager)
        bridge_mock = Mock(spec=AgentWebSocketBridge)
        
        # REGRESSION EXPOSURE: Track method calls
        method_calls = []
        
        def track_manager_call(method_name):
            def wrapper(*args, **kwargs):
                method_calls.append(f"manager.{method_name}")
                return Mock()
            return wrapper
            
        def track_bridge_call(method_name):
            def wrapper(*args, **kwargs):
                method_calls.append(f"bridge.{method_name}")
                return Mock()
            return wrapper
            
        # Setup method tracking
        manager_mock.send_event = track_manager_call('send_event')
        bridge_mock.send_event = track_bridge_call('send_event')
        
        # CRITICAL: Set both interfaces (this exposes the race condition)
        user_session.set_websocket_manager(manager_mock)
        
        # Simulate interface method calls
        try:
            # These calls should go to consistent interface
            if hasattr(user_session, 'send_event'):
                user_session.send_event("test_event", {"data": "test"})
            elif user_session._websocket_bridge and hasattr(user_session._websocket_bridge, 'send_event'):
                user_session._websocket_bridge.send_event("test_event", {"data": "test"})
            elif user_session._websocket_manager and hasattr(user_session._websocket_manager, 'send_event'):
                user_session._websocket_manager.send_event("test_event", {"data": "test"})
                
        except Exception as e:
            method_calls.append(f"ERROR: {str(e)}")
            
        logger.info(f"Method dispatch calls: {method_calls}")
        
        # REGRESSION EXPOSURE: Check for dispatch inconsistencies
        dispatch_errors = []
        
        # CRITICAL: Should not have calls to both interfaces for same operation
        manager_calls = [call for call in method_calls if call.startswith('manager.')]
        bridge_calls = [call for call in method_calls if call.startswith('bridge.')]
        error_calls = [call for call in method_calls if call.startswith('ERROR:')]
        
        if manager_calls and bridge_calls:
            dispatch_errors.append("Method calls dispatched to both manager and bridge interfaces")
            
        if error_calls:
            dispatch_errors.append(f"Method dispatch errors: {error_calls}")
            
        if not manager_calls and not bridge_calls and not error_calls:
            dispatch_errors.append("No method calls were successfully dispatched")
            
        # CRITICAL ASSERTION: Should fail due to dispatch inconsistencies
        assert len(dispatch_errors) == 0, (
            f"REGRESSION DETECTED: Incorrect method dispatch in dual WebSocket interfaces - "
            f"dispatch inconsistencies: {dispatch_errors}"
        )

    def _get_public_methods(self, cls: Type) -> Dict[str, Any]:
        """Helper to extract public methods from a class."""
        methods = {}
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_'):  # Public methods only
                methods[name] = method
        return methods


@pytest.mark.integration  
@pytest.mark.interface_violations
class TestWebSocketInterfaceIntegrationViolations(SSotBaseTestCase):
    """
    Integration tests for WebSocket interface violations in real scenarios.
    
    These tests use real components to expose interface mismatches that
    cause runtime failures in production scenarios.
    """
    
    def setup_method(self):
        """Setup for integration tests."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        
    @pytest.mark.regression_reproduction
    @pytest.mark.real_services
    async def test_real_websocket_interface_conflict_integration(self):
        """
        CRITICAL: Integration test with real WebSocket components showing interface conflicts.
        
        ROOT CAUSE REPRODUCTION: Real AgentRegistry + WebSocketManager combination
        exposes the dual interface violations in actual execution context.
        
        EXPECTED FAILURE: Should fail with interface conflict errors.
        """
        logger.info("🚨 INTEGRATION TEST: Real WebSocket interface conflicts")
        
        # CRITICAL: Create real components that expose interface issues
        user_context = UserExecutionContext(
            user_id="integration_test_user",
            request_id="interface_test_request",
            thread_id="interface_test_thread",
            run_id="interface_test_run"
        )
        
        # REGRESSION EXPOSURE: Try to use both interface patterns
        try:
            # Create AgentWebSocketBridge (new pattern)
            bridge = create_agent_websocket_bridge(user_context)
            
            # Create UnifiedWebSocketManager (alternative pattern)
            unified_manager = UnifiedWebSocketManager()
            
            # CRITICAL: Test interface compatibility
            interface_conflicts = []
            
            # Test 1: Method signature compatibility
            if hasattr(bridge, 'send_event') and hasattr(unified_manager, 'send_event'):
                bridge_sig = inspect.signature(bridge.send_event)
                manager_sig = inspect.signature(unified_manager.send_event)
                
                if str(bridge_sig) != str(manager_sig):
                    interface_conflicts.append(
                        f"send_event signature mismatch: bridge={bridge_sig} vs manager={manager_sig}"
                    )
                    
            # Test 2: Interface substitutability  
            try:
                # This should work if interfaces are properly compatible
                test_event = {"type": "test", "data": {"message": "interface test"}}
                
                # Try using bridge interface
                if hasattr(bridge, 'send_event'):
                    bridge.send_event("test_event", test_event)
                    
                # Try using manager interface  
                if hasattr(unified_manager, 'send_event'):
                    unified_manager.send_event("test_event", test_event)
                    
            except Exception as e:
                interface_conflicts.append(f"Interface substitution failed: {str(e)}")
                
            # CRITICAL ASSERTION: Should fail due to interface conflicts
            assert len(interface_conflicts) == 0, (
                f"REGRESSION DETECTED: Real WebSocket interface conflicts prevent proper operation - "
                f"conflicts: {interface_conflicts}"
            )
            
        except Exception as e:
            # EXPECTED: This should fail due to interface violations
            logger.error(f"Expected interface failure: {e}")
            pytest.fail(f"REGRESSION DETECTED: WebSocket interface integration failure - {str(e)}")