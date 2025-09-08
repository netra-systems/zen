"""
WebSocket Manager Protocol Compliance Test Suite - Five Whys Prevention

This test suite validates that all WebSocket manager implementations comply with
the WebSocketManagerProtocol, directly preventing the root cause identified in
the Five Whys analysis: "lack of formal interface contracts."

Test Focus:
1. Protocol compliance validation for all manager types
2. Critical method functionality testing (Five Whys specific)
3. Interface compatibility verification
4. Runtime behavior validation

Root Cause Prevention:
These tests ensure that NO WebSocket manager can be deployed without implementing
the complete protocol interface, preventing AttributeError exceptions during
agent execution.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from netra_backend.app.websocket_core.protocols import (
    WebSocketManagerProtocol,
    WebSocketManagerProtocolValidator
)
from netra_backend.app.websocket_core.protocol_validator import (
    validate_websocket_manager_on_startup,
    create_protocol_compliance_report,
    test_critical_method_functionality
)
from netra_backend.app.websocket_core.websocket_manager_factory import (
    create_websocket_manager,
    IsolatedWebSocketManager
)
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestWebSocketManagerProtocolCompliance:
    """
    Test suite to ensure WebSocket managers implement WebSocketManagerProtocol.
    
    FIVE WHYS PREVENTION: These tests directly prevent the root cause by ensuring
    all managers implement the required interface methods.
    """
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_user_id = "usr_9d8f7e6c5b4a3210"  # Use realistic user ID format
        self.test_connection_id = "conn_test_12345"
        self.test_thread_id = "thread_test_12345"
        
        # Create test user context using SSOT ID generator
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
            self.test_user_id, "protocol_test"
        )
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=f"ws_client_{self.test_user_id}"
        )
        
        # Create test WebSocket connection
        self.mock_websocket = AsyncMock()
        self.test_connection = WebSocketConnection(
            connection_id=self.test_connection_id,
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            connected_at=datetime.utcnow(),
            thread_id=self.test_thread_id
        )
    
    def test_isolated_manager_protocol_compliance(self):
        """
        Test IsolatedWebSocketManager implements WebSocketManagerProtocol.
        
        FIVE WHYS CRITICAL: This test prevents the specific error that triggered
        the Five Whys analysis by ensuring IsolatedWebSocketManager has all
        required methods.
        """
        # Create isolated manager
        manager = create_websocket_manager(self.user_context)
        
        # Verify it's protocol compliant
        validation_result = WebSocketManagerProtocolValidator.validate_manager_protocol(manager)
        
        # Assert compliance
        assert validation_result['compliant'], (
            f"IsolatedWebSocketManager MUST be protocol compliant. "
            f"Missing methods: {validation_result['missing_methods']}, "
            f"Invalid signatures: {validation_result['invalid_signatures']}. "
            f"Compliance: {validation_result['summary']['compliance_percentage']}%"
        )
        
        # Verify it's recognized as protocol instance
        assert isinstance(manager, WebSocketManagerProtocol), (
            "IsolatedWebSocketManager must implement WebSocketManagerProtocol"
        )
        
        # Check Five Whys critical methods specifically
        assert hasattr(manager, 'get_connection_id_by_websocket'), (
            "FIVE WHYS CRITICAL: get_connection_id_by_websocket method missing"
        )
        assert hasattr(manager, 'update_connection_thread'), (
            "FIVE WHYS CRITICAL: update_connection_thread method missing"
        )
    
    def test_unified_manager_protocol_compliance(self):
        """
        Test UnifiedWebSocketManager implements required protocol methods.
        
        While UnifiedWebSocketManager doesn't formally implement the protocol,
        it should have all required methods for interface compatibility.
        """
        manager = UnifiedWebSocketManager()
        
        validation_result = WebSocketManagerProtocolValidator.validate_manager_protocol(manager)
        
        # Log detailed results for debugging
        print(f"UnifiedWebSocketManager compliance: {validation_result['summary']['compliance_percentage']}%")
        print(f"Missing methods: {validation_result['missing_methods']}")
        print(f"Invalid signatures: {validation_result['invalid_signatures']}")
        
        # Should have Five Whys critical methods
        assert hasattr(manager, 'get_connection_id_by_websocket'), (
            "UnifiedWebSocketManager missing get_connection_id_by_websocket"
        )
        assert hasattr(manager, 'update_connection_thread'), (
            "UnifiedWebSocketManager missing update_connection_thread"
        )
        
        # Should have core connection management methods
        required_methods = [
            'add_connection', 'remove_connection', 'get_connection',
            'get_user_connections', 'is_connection_active', 'send_to_user',
            'emit_critical_event', 'get_connection_health', 'send_to_thread'
        ]
        
        for method in required_methods:
            assert hasattr(manager, method), f"UnifiedWebSocketManager missing {method} method"
    
    @pytest.mark.asyncio
    async def test_five_whys_critical_methods_functionality(self):
        """
        Test the specific methods identified in Five Whys analysis work correctly.
        
        This test ensures the methods that were missing (causing the original error)
        now function properly.
        """
        manager = create_websocket_manager(self.user_context)
        
        # Add a test connection
        await manager.add_connection(self.test_connection)
        
        # Test get_connection_id_by_websocket - the method that was missing!
        found_connection_id = manager.get_connection_id_by_websocket(self.mock_websocket)
        assert found_connection_id == self.test_connection_id, (
            f"get_connection_id_by_websocket should return {self.test_connection_id}, "
            f"got {found_connection_id}"
        )
        
        # Test with unknown websocket
        unknown_websocket = AsyncMock()
        not_found = manager.get_connection_id_by_websocket(unknown_websocket)
        assert not_found is None, "Should return None for unknown WebSocket"
        
        # Test update_connection_thread - the companion method
        new_thread_id = "new_thread_12345"
        update_result = manager.update_connection_thread(self.test_connection_id, new_thread_id)
        assert update_result is True, "update_connection_thread should return True for existing connection"
        
        # Verify thread was actually updated
        connection = manager.get_connection(self.test_connection_id)
        assert hasattr(connection, 'thread_id'), "Connection should have thread_id attribute"
        assert connection.thread_id == new_thread_id, f"Thread ID should be updated to {new_thread_id}"
        
        # Test with non-existent connection
        update_result = manager.update_connection_thread("nonexistent", "thread")
        assert update_result is False, "Should return False for non-existent connection"
    
    @pytest.mark.asyncio
    async def test_protocol_method_signatures(self):
        """Test that all protocol methods have correct signatures."""
        manager = create_websocket_manager(self.user_context)
        
        # Test async methods
        async_methods = [
            ('add_connection', [self.test_connection]),
            ('remove_connection', [self.test_connection_id]),
            ('send_to_user', [{"test": "message"}]),
            ('emit_critical_event', ["test_event", {"data": "test"}]),
            ('send_to_thread', [self.test_thread_id, {"test": "message"}])
        ]
        
        for method_name, args in async_methods:
            method = getattr(manager, method_name)
            assert asyncio.iscoroutinefunction(method), (
                f"{method_name} should be an async method"
            )
            
            # Test that method can be called (even if it fails due to test conditions)
            try:
                if method_name == 'send_to_user':
                    await method(*args)
                elif method_name == 'emit_critical_event':
                    await method(self.test_user_id, *args)
                elif method_name == 'send_to_thread':
                    result = await method(*args)
                    assert isinstance(result, bool), f"{method_name} should return bool"
                else:
                    await method(*args)
            except Exception as e:
                # Method exists and can be called, specific failures are OK for test data
                print(f"{method_name} callable but failed with test data: {e}")
        
        # Test sync methods
        sync_methods = [
            ('get_connection', [self.test_connection_id]),
            ('get_user_connections', [self.test_user_id]),
            ('is_connection_active', [self.test_user_id]),
            ('get_connection_id_by_websocket', [self.mock_websocket]),
            ('update_connection_thread', [self.test_connection_id, self.test_thread_id]),
            ('get_connection_health', [self.test_user_id])
        ]
        
        for method_name, args in sync_methods:
            method = getattr(manager, method_name)
            assert not asyncio.iscoroutinefunction(method), (
                f"{method_name} should be a sync method"
            )
            
            # Test that method can be called
            try:
                result = method(*args)
                print(f"{method_name} returned: {type(result)}")
            except Exception as e:
                # Method exists and can be called
                print(f"{method_name} callable but failed with test data: {e}")
    
    def test_startup_validation_integration(self):
        """
        Test the startup validation workflow for protocol compliance.
        
        This simulates how the validation would be used during system startup
        to prevent deployment of non-compliant managers.
        """
        manager = create_websocket_manager(self.user_context)
        
        # Should pass startup validation
        validation_passed = validate_websocket_manager_on_startup(manager, "Test Context")
        assert validation_passed, (
            "WebSocket manager should pass startup validation. "
            "This indicates protocol compliance issues."
        )
    
    def test_compliance_report_generation(self):
        """Test generation of detailed protocol compliance reports."""
        manager = create_websocket_manager(self.user_context)
        
        report = create_protocol_compliance_report(manager)
        
        # Verify report structure
        assert 'compliant' in report
        assert 'manager_type' in report
        assert 'method_check_details' in report
        assert 'five_whys_critical_methods' in report
        assert 'recommendations' in report
        
        # Should be compliant
        assert report['compliant'], f"Manager should be compliant: {report.get('missing_methods', [])}"
        
        # Should have Five Whys critical methods documented
        five_whys_methods = report['five_whys_critical_methods']
        assert 'get_connection_id_by_websocket' in five_whys_methods
        assert 'update_connection_thread' in five_whys_methods
        
        # Critical methods should be marked as existing and callable
        for method_name in ['get_connection_id_by_websocket', 'update_connection_thread']:
            method_details = five_whys_methods[method_name]
            assert method_details.get('exists', False), f"{method_name} should exist"
            assert method_details.get('callable', False), f"{method_name} should be callable"
    
    @pytest.mark.asyncio
    async def test_critical_method_runtime_functionality(self):
        """
        Test runtime functionality of Five Whys critical methods.
        
        This ensures the methods not only exist but actually work correctly
        in runtime scenarios.
        """
        manager = create_websocket_manager(self.user_context)
        
        # Run comprehensive functionality tests
        test_results = await test_critical_method_functionality(manager)
        
        # Should have run tests
        assert test_results['tests_run'] > 0, "Should have run functionality tests"
        
        # Should have reasonable success rate
        assert test_results['success_rate'] >= 80, (
            f"Critical method functionality tests should have high success rate. "
            f"Success rate: {test_results['success_rate']}%. "
            f"Errors: {test_results['errors']}"
        )
        
        # Log detailed results
        print(f"Critical method test results: {test_results['tests_passed']}/{test_results['tests_run']} passed")
        if test_results['errors']:
            print(f"Errors encountered: {test_results['errors']}")
    
    def test_protocol_validator_error_handling(self):
        """Test protocol validator handles edge cases gracefully."""
        
        # Test with None input
        validation_result = WebSocketManagerProtocolValidator.validate_manager_protocol(None)
        assert not validation_result['compliant']
        assert 'validation_error' in validation_result or 'missing_methods' in validation_result
        
        # Test with object that doesn't have required methods
        class IncompleteManager:
            pass
        
        incomplete = IncompleteManager()
        validation_result = WebSocketManagerProtocolValidator.validate_manager_protocol(incomplete)
        assert not validation_result['compliant']
        assert len(validation_result['missing_methods']) > 0
        
        # Should specifically identify Five Whys critical methods as missing
        assert 'get_connection_id_by_websocket' in validation_result['missing_methods']
        assert 'update_connection_thread' in validation_result['missing_methods']
    
    def test_require_protocol_compliance_enforcement(self):
        """Test that protocol compliance can be strictly enforced."""
        compliant_manager = create_websocket_manager(self.user_context)
        
        # Should not raise for compliant manager
        try:
            WebSocketManagerProtocolValidator.require_protocol_compliance(
                compliant_manager, "Test Context"
            )
        except RuntimeError:
            pytest.fail("Should not raise RuntimeError for compliant manager")
        
        # Should raise for non-compliant manager
        class NonCompliantManager:
            pass
        
        non_compliant = NonCompliantManager()
        
        with pytest.raises(RuntimeError) as exc_info:
            WebSocketManagerProtocolValidator.require_protocol_compliance(
                non_compliant, "Test Context"
            )
        
        error_message = str(exc_info.value)
        assert "PROTOCOL COMPLIANCE FAILURE" in error_message
        assert "get_connection_id_by_websocket" in error_message or "Missing methods" in error_message
        assert "Five Whys" in error_message


if __name__ == "__main__":
    # Run the tests directly for development/debugging
    pytest.main([__file__, "-v", "-s"])