"""
Phase 3.4 Supervisor Factory Dependency Injection Validation Tests

GOLDEN PATH PHASE 3.4: Issue #1188 - SupervisorAgent Integration Validation
Test Plan: Validate supervisor factory dependency injection patterns and user isolation.

Business Value:
- Segment: Platform/Internal - 500K+ ARR Protection
- Goal: Validate SSOT supervisor factory patterns prevent user context leakage
- Impact: Ensures enterprise-grade multi-user isolation for production deployment
- Revenue Impact: Prevents security vulnerabilities that could block enterprise adoption

Test Strategy:
- FAILING FIRST: Tests designed to fail initially to validate they work
- Real Services: Use actual dependency injection patterns, no mocks for core logic
- User Isolation: Validate factory creates unique instances per user
- SSOT Compliance: Verify factory patterns follow SSOT architecture

Key Test Areas:
1. Factory creation with proper dependency injection
2. User context isolation between concurrent requests
3. WebSocket bridge integration through factory
4. LLM manager dependency binding
5. Database session factory lifecycle management
"""

import pytest
import asyncio
from typing import Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following test framework patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Core supervisor imports for testing
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.core.supervisor_factory import create_supervisor_core
from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor

# SSOT service imports
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# Test utilities
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SupervisorFactoryDependencyInjectionTests(SSotAsyncTestCase):
    """
    Phase 3.4 Supervisor Factory Dependency Injection Tests
    
    CRITICAL: These tests are designed to FAIL initially to validate proper test behavior.
    Once implementation is complete, they should pass.
    """
    
    def setUp(self):
        """Set up test fixtures for supervisor factory validation."""
        super().setUp()
        
        # Create mock factory for consistent test patterns
        self.mock_factory = SSotMockFactory()
        
        # Mock user contexts for testing isolation
        self.user_context_1 = UserExecutionContext.from_request(
            user_id="test_user_1",
            thread_id="test_thread_1", 
            run_id="test_run_1",
            websocket_client_id="test_client_1"
        )
        
        self.user_context_2 = UserExecutionContext.from_request(
            user_id="test_user_2",
            thread_id="test_thread_2",
            run_id="test_run_2", 
            websocket_client_id="test_client_2"
        )
        
        # Mock dependencies
        self.mock_llm_manager = self.mock_factory.create_mock(LLMManager)
        self.mock_websocket_bridge = self.mock_factory.create_mock(AgentWebSocketBridge)
        
    async def test_supervisor_requires_user_context_for_security(self):
        """
        CRITICAL SECURITY TEST: Supervisor must require user_context to prevent data leakage.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if supervisor allows creation
        without user_context (security vulnerability).
        """
        logger.info("🔒 Testing supervisor security requirement for user_context")
        
        # CRITICAL: Supervisor creation without user_context should raise ValueError
        # This prevents the singleton pattern security vulnerability from Issue #1116
        with self.assertRaises(ValueError) as context:
            supervisor = SupervisorAgent(
                llm_manager=self.mock_llm_manager,
                websocket_bridge=self.mock_websocket_bridge,
                # MISSING: user_context parameter - should cause security error
            )
        
        # Validate security error message mentions user isolation
        error_message = str(context.exception)
        self.assertIn("user_context", error_message.lower())
        self.assertIn("security", error_message.lower() or "isolation" in error_message.lower())
        
        logger.info(f"CHECK Security validation passed: {error_message}")
        
    async def test_supervisor_factory_creates_unique_instances_per_user(self):
        """
        CRITICAL USER ISOLATION TEST: Factory must create separate instances per user.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if factory shares state
        between users (data contamination vulnerability).
        """
        logger.info("👥 Testing supervisor factory user isolation")
        
        # Create supervisors for different users
        supervisor_1 = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.user_context_1
        )
        
        supervisor_2 = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.user_context_2
        )
        
        # CRITICAL: Each supervisor must have separate agent_factory instances
        # Shared instances would cause user data contamination
        self.assertIsNotNone(supervisor_1.agent_factory)
        self.assertIsNotNone(supervisor_2.agent_factory)
        self.assertNotEqual(
            id(supervisor_1.agent_factory), 
            id(supervisor_2.agent_factory),
            "SECURITY VIOLATION: Supervisors sharing agent_factory instances can leak user data"
        )
        
        # Validate user context isolation
        self.assertEqual(supervisor_1._initialization_user_context.user_id, "test_user_1")
        self.assertEqual(supervisor_2._initialization_user_context.user_id, "test_user_2")
        
        logger.info("CHECK User isolation validation passed")
        
    async def test_supervisor_factory_dependency_injection_patterns(self):
        """
        DEPENDENCY INJECTION TEST: Validate factory properly injects dependencies.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if dependency injection
        is not properly implemented according to SSOT patterns.
        """
        logger.info("🔧 Testing supervisor factory dependency injection")
        
        # Create supervisor with all dependencies
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.user_context_1
        )
        
        # Validate core dependencies are properly injected
        self.assertIsNotNone(supervisor._llm_manager)
        self.assertEqual(supervisor._llm_manager, self.mock_llm_manager)
        
        self.assertIsNotNone(supervisor.websocket_bridge)
        self.assertEqual(supervisor.websocket_bridge, self.mock_websocket_bridge)
        
        # Validate factory is created with user context
        self.assertIsNotNone(supervisor.agent_factory)
        self.assertIsNotNone(supervisor._initialization_user_context)
        
        # Validate BaseAgent initialization patterns
        self.assertEqual(supervisor.name, "Supervisor")
        self.assertIn("Orchestrates sub-agents", supervisor.description)
        
        logger.info("CHECK Dependency injection validation passed")
        
    async def test_core_supervisor_factory_protocol_agnostic(self):
        """
        CORE FACTORY TEST: Validate core supervisor factory works across protocols.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if core factory
        doesn't properly handle protocol-agnostic creation.
        """
        logger.info("🌐 Testing core supervisor factory protocol independence")
        
        # Mock required dependencies for core factory
        mock_db_session = AsyncMock()
        mock_llm_client = AsyncMock()
        
        # Test core factory creation
        with patch('netra_backend.app.core.supervisor_factory.get_user_execution_context') as mock_get_context:
            mock_get_context.return_value = self.user_context_1
            
            # This should work for both HTTP and WebSocket protocols
            supervisor = await create_supervisor_core(
                user_id="test_user_1",
                thread_id="test_thread_1",
                run_id="test_run_1",
                db_session=mock_db_session,
                websocket_client_id="test_client_1",
                llm_client=mock_llm_client,
                websocket_bridge=self.mock_websocket_bridge
            )
            
            # Validate supervisor creation
            self.assertIsInstance(supervisor, SupervisorAgent)
            self.assertIsNotNone(supervisor._llm_manager)
            self.assertIsNotNone(supervisor.websocket_bridge)
            
        logger.info("CHECK Core factory protocol independence validated")
        
    async def test_websocket_supervisor_factory_context_handling(self):
        """
        WEBSOCKET FACTORY TEST: Validate WebSocket-specific factory patterns.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if WebSocket factory
        doesn't properly handle WebSocket context and cleanup.
        """
        logger.info("🔌 Testing WebSocket supervisor factory context handling")
        
        # Mock WebSocket context
        from netra_backend.app.websocket_core.context import WebSocketContext
        mock_ws_context = MagicMock(spec=WebSocketContext)
        mock_ws_context.user_id = "test_user_1" 
        mock_ws_context.thread_id = "test_thread_1"
        mock_ws_context.run_id = "test_run_1"
        mock_ws_context.client_id = "test_client_1"
        
        mock_db_session = AsyncMock()
        
        # Test WebSocket factory creation
        with patch('netra_backend.app.websocket_core.supervisor_factory.create_supervisor_core') as mock_core:
            mock_supervisor = MagicMock(spec=SupervisorAgent)
            mock_core.return_value = mock_supervisor
            
            supervisor = await get_websocket_scoped_supervisor(
                context=mock_ws_context,
                db_session=mock_db_session
            )
            
            # Validate WebSocket factory delegates to core factory
            mock_core.assert_called_once()
            call_args = mock_core.call_args
            
            # Verify proper parameter passing
            self.assertEqual(call_args[1]['user_id'], "test_user_1")
            self.assertEqual(call_args[1]['thread_id'], "test_thread_1") 
            self.assertEqual(call_args[1]['run_id'], "test_run_1")
            self.assertEqual(call_args[1]['websocket_client_id'], "test_client_1")
            
        logger.info("CHECK WebSocket factory context handling validated")
        
    async def test_supervisor_legacy_parameter_compatibility(self):
        """
        COMPATIBILITY TEST: Validate supervisor handles legacy parameters gracefully.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if supervisor doesn't
        properly handle legacy parameters during migration.
        """
        logger.info("🔄 Testing supervisor legacy parameter compatibility")
        
        # Test with legacy parameters (should be ignored)
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.user_context_1,
            db_session_factory="legacy_parameter",  # Should be ignored
            tool_dispatcher="legacy_parameter"       # Should be ignored  
        )
        
        # Validate supervisor creation succeeded despite legacy parameters
        self.assertIsInstance(supervisor, SupervisorAgent)
        self.assertIsNotNone(supervisor._llm_manager)
        self.assertIsNotNone(supervisor.agent_factory)
        
        # Validate legacy parameters were properly ignored (no errors)
        logger.info("CHECK Legacy parameter compatibility validated")
        
    def test_supervisor_factory_imports_and_dependencies(self):
        """
        IMPORT TEST: Validate all required imports are available and correct.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if imports are broken
        or dependencies are missing.
        """
        logger.info("📦 Testing supervisor factory imports and dependencies")
        
        # Validate core supervisor classes can be imported
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.core.supervisor_factory import create_supervisor_core
        from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
        
        # Validate supervisor class has required attributes
        self.assertTrue(hasattr(SupervisorAgent, '__init__'))
        self.assertTrue(hasattr(SupervisorAgent, 'agent_factory'))
        
        # Validate factory functions exist
        self.assertTrue(callable(create_supervisor_core))
        self.assertTrue(callable(get_websocket_scoped_supervisor))
        
        logger.info("CHECK Import and dependency validation passed")


# Execute tests if run directly
if __name__ == "__main__":
    logger.info("🚀 Starting Phase 3.4 Supervisor Factory Dependency Injection Tests")
    logger.info("WARNING️  EXPECTED: Tests may FAIL initially - this validates proper test behavior")
    
    # Run with asyncio
    import unittest
    unittest.main()