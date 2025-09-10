"""Test Execution Engine Factory SSOT Compliance - P0 Failing Tests.

This test module validates that all execution engine factories ONLY create 
UserExecutionEngine instances and never deprecated execution engines.

EXPECTED BEHAVIOR (BEFORE REMEDIATION):
- These tests should FAIL because factories may create deprecated engines
- After remediation: Tests should PASS when factories enforce SSOT compliance

TEST PURPOSE: Prove factory SSOT violations exist and validate fix effectiveness.

Business Value: Prevents creation of deprecated engines that cause user isolation issues.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from typing import TYPE_CHECKING

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestExecutionEngineFactorySSotCompliance(SSotAsyncTestCase):
    """Test that execution engine factories enforce SSOT UserExecutionEngine compliance.
    
    These tests should FAIL initially, proving the factory SSOT violations exist.
    After remediation, they should PASS to validate the fix.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        
        # Mock WebSocket bridge (required for factory)
        self.mock_websocket_bridge = Mock()
        self.mock_websocket_bridge.create_user_emitter = Mock(return_value=Mock())
        
        # Mock database and Redis managers
        self.mock_db_manager = Mock()
        self.mock_redis_manager = Mock()
        
        # Create valid user context
        self.user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456", 
            run_id="test_run_789"
        )
        
    def test_execution_engine_factory_creates_only_user_execution_engine(self):
        """Test that ExecutionEngineFactory only creates UserExecutionEngine instances.
        
        EXPECTED: This test should FAIL before remediation if factory creates deprecated engines.
        AFTER REMEDIATION: Should PASS when factory enforces SSOT compliance.
        """
        factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=self.mock_db_manager,
            redis_manager=self.mock_redis_manager
        )
        
        # Create engine instance
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_user_engine_class:
            mock_user_engine_class.return_value = Mock(spec=UserExecutionEngine)
            mock_user_engine_class.return_value.__class__.__name__ = "UserExecutionEngine"
            
            engine = asyncio.run(factory.create_engine(self.user_context))
            
            # SSOT Validation: Should ONLY create UserExecutionEngine
            assert engine.__class__.__name__ == "UserExecutionEngine"
            mock_user_engine_class.assert_called_once()
            
    def test_execution_engine_factory_rejects_deprecated_engine_creation_requests(self):
        """Test that factory rejects requests to create deprecated engines.
        
        EXPECTED: This test should FAIL before remediation (no validation exists).
        AFTER REMEDIATION: Should PASS when factory validates engine types.
        """
        factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=self.mock_db_manager,
            redis_manager=self.mock_redis_manager
        )
        
        # Attempt to request deprecated engine type (should be rejected)
        with pytest.raises(ValueError, match="deprecated.*ExecutionEngine.*not supported"):
            asyncio.run(factory.create_engine(
                self.user_context, 
                engine_type="ExecutionEngine"  # Deprecated type
            ))
            
    def test_execution_engine_factory_validates_engine_type_parameter(self):
        """Test that factory validates engine_type parameter for SSOT compliance.
        
        EXPECTED: This test should FAIL before remediation (no parameter validation).
        AFTER REMEDIATION: Should PASS when parameter validation is added.
        """
        factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=self.mock_db_manager,
            redis_manager=self.mock_redis_manager
        )
        
        # Valid engine type should work
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_class:
            mock_class.return_value = Mock(spec=UserExecutionEngine)
            
            engine = asyncio.run(factory.create_engine(
                self.user_context,
                engine_type="UserExecutionEngine"  # Valid SSOT type
            ))
            assert engine is not None
            
        # Invalid engine types should be rejected
        invalid_types = [
            "ExecutionEngine",
            "ExecutionEngineConsolidated", 
            "SomeOtherEngine",
            "RequestScopedExecutionEngine"
        ]
        
        for invalid_type in invalid_types:
            with pytest.raises(ValueError, match=f"Engine type.*{invalid_type}.*not allowed.*SSOT"):
                asyncio.run(factory.create_engine(
                    self.user_context,
                    engine_type=invalid_type
                ))
                
    def test_execution_engine_factory_logs_ssot_compliance_events(self):
        """Test that factory logs SSOT compliance validation events.
        
        EXPECTED: This test should FAIL before remediation (no compliance logging).
        AFTER REMEDIATION: Should PASS when compliance logging is added.
        """
        factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=self.mock_db_manager,
            redis_manager=self.mock_redis_manager
        )
        
        with self.assertLogs("netra_backend.app.agents.supervisor.execution_engine_factory", level="INFO") as log:
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_class:
                mock_class.return_value = Mock(spec=UserExecutionEngine)
                
                asyncio.run(factory.create_engine(self.user_context))
                
        # Should log SSOT compliance validation
        log_messages = " ".join(log.output)
        self.assertIn("SSOT compliance validated", log_messages)
        self.assertIn("UserExecutionEngine", log_messages)
        
    def test_execution_engine_factory_prevents_direct_deprecated_imports(self):
        """Test that factory prevents accidental import of deprecated engines.
        
        EXPECTED: This test should FAIL before remediation (imports not restricted).
        AFTER REMEDIATION: Should PASS when import validation is added.
        """
        # This test validates that factory doesn't accidentally import deprecated modules
        factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=self.mock_db_manager,
            redis_manager=self.mock_redis_manager
        )
        
        # Simulate scenario where someone tries to patch factory to use deprecated engine
        with patch('sys.modules') as mock_modules:
            # Mock deprecated modules being available
            mock_modules['netra_backend.app.agents.supervisor.execution_engine'] = Mock()
            mock_modules['netra_backend.app.agents.execution_engine_consolidated'] = Mock()
            
            # Factory should detect and reject deprecated imports
            with pytest.raises(ValueError, match="Deprecated execution engine.*detected.*SSOT violation"):
                asyncio.run(factory.create_engine(self.user_context))


class TestUnifiedExecutionEngineFactorySSotCompliance(SSotAsyncTestCase):
    """Test UnifiedExecutionEngineFactory SSOT compliance.
    
    This tests the newer unified factory for SSOT violations.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )
        
    def test_unified_factory_only_creates_user_execution_engine(self):
        """Test that UnifiedExecutionEngineFactory only creates UserExecutionEngine.
        
        EXPECTED: This test should FAIL before remediation if unified factory creates deprecated engines.
        AFTER REMEDIATION: Should PASS when unified factory enforces SSOT compliance.
        """
        # Import the unified factory
        try:
            from netra_backend.app.agents.execution_engine_unified_factory import UnifiedExecutionEngineFactory
        except ImportError:
            pytest.skip("UnifiedExecutionEngineFactory not available")
            
        # Mock required dependencies
        mock_websocket_bridge = Mock()
        mock_agent_registry = Mock()
        
        factory = UnifiedExecutionEngineFactory(
            websocket_bridge=mock_websocket_bridge,
            agent_registry=mock_agent_registry
        )
        
        with patch('netra_backend.app.agents.execution_engine_unified_factory.UserExecutionEngine') as mock_class:
            mock_class.return_value = Mock(spec=UserExecutionEngine)
            mock_class.return_value.__class__.__name__ = "UserExecutionEngine"
            
            engine = asyncio.run(factory.create_execution_engine(self.user_context))
            
            # SSOT Validation: Should ONLY create UserExecutionEngine
            assert engine.__class__.__name__ == "UserExecutionEngine"
            mock_class.assert_called_once()
            
    def test_unified_factory_rejects_deprecated_factory_methods(self):
        """Test that unified factory doesn't expose deprecated creation methods.
        
        EXPECTED: This test should FAIL before remediation (deprecated methods exist).
        AFTER REMEDIATION: Should PASS when deprecated methods are removed.
        """
        try:
            from netra_backend.app.agents.execution_engine_unified_factory import UnifiedExecutionEngineFactory
        except ImportError:
            pytest.skip("UnifiedExecutionEngineFactory not available")
            
        factory = UnifiedExecutionEngineFactory(
            websocket_bridge=Mock(),
            agent_registry=Mock()
        )
        
        # These methods should not exist (deprecated)
        deprecated_methods = [
            'create_execution_engine_legacy',
            'create_execution_engine_consolidated',
            'create_request_scoped_engine',
            'get_execution_engine'  # Should be get_user_execution_engine
        ]
        
        for method_name in deprecated_methods:
            assert not hasattr(factory, method_name), f"Deprecated method {method_name} still exists"
            
        # Only SSOT methods should exist
        assert hasattr(factory, 'create_execution_engine'), "SSOT method create_execution_engine missing"
        
    def test_factory_dependency_injection_uses_ssot_patterns(self):
        """Test that factory dependency injection follows SSOT patterns.
        
        EXPECTED: This test should FAIL before remediation (non-SSOT patterns used).
        AFTER REMEDIATION: Should PASS when SSOT dependency injection is enforced.
        """
        # Mock factory dependencies
        mock_websocket_bridge = Mock()
        mock_agent_registry = Mock()
        
        factory = ExecutionEngineFactory(
            websocket_bridge=mock_websocket_bridge,
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        # Test that factory uses SSOT dependency injection patterns
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_class:
            mock_engine = Mock(spec=UserExecutionEngine)
            mock_class.return_value = mock_engine
            
            engine = asyncio.run(factory.create_engine(self.user_context))
            
            # Verify SSOT dependencies were injected
            mock_class.assert_called_once()
            call_args = mock_class.call_args
            
            # Should inject UserExecutionContext (SSOT pattern)
            assert any('user_context' in str(arg) for arg in call_args[0] + tuple(call_args[1].values())), \
                "UserExecutionContext not injected (SSOT violation)"
                
            # Should inject WebSocket bridge for user isolation
            assert mock_websocket_bridge in call_args[0] or mock_websocket_bridge in call_args[1].values(), \
                "WebSocket bridge not injected (user isolation violation)"
                
    def test_factory_prevents_shared_state_creation(self):
        """Test that factory prevents creation of engines with shared state.
        
        EXPECTED: This test should FAIL before remediation (shared state not prevented).
        AFTER REMEDIATION: Should PASS when shared state prevention is added.
        """
        factory = ExecutionEngineFactory(
            websocket_bridge=Mock(),
            database_session_manager=Mock(),
            redis_manager=Mock()
        )
        
        # Create multiple engines for different users
        user1_context = UserExecutionContext(user_id="user1", thread_id="thread1", run_id="run1")
        user2_context = UserExecutionContext(user_id="user2", thread_id="thread2", run_id="run2")
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.UserExecutionEngine') as mock_class:
            mock_class.side_effect = lambda *args, **kwargs: Mock(spec=UserExecutionEngine)
            
            engine1 = asyncio.run(factory.create_engine(user1_context))
            engine2 = asyncio.run(factory.create_engine(user2_context))
            
            # Engines should be different instances (no shared state)
            assert engine1 is not engine2, "Factory created shared engine instance (SSOT violation)"
            
            # Should create separate instances for each user
            assert mock_class.call_count == 2, "Factory did not create separate engines per user"