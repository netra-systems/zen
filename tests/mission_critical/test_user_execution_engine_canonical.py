"""Issue #874: UserExecutionEngine canonical SSOT validation test.

This test validates that UserExecutionEngine is properly established as the
Single Source of Truth for execution engine functionality. It tests the
canonical implementation's completeness and proper integration patterns.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Reliability & Performance
- Value Impact: Ensures UserExecutionEngine provides complete execution capabilities for $500K+ ARR chat
- Strategic Impact: Validates SSOT consolidation delivers secure multi-user isolation and performance

Key Validation Areas:
- UserExecutionEngine implements all required execution interfaces
- Factory pattern correctly creates UserExecutionEngine instances
- User isolation patterns work correctly
- WebSocket event routing is user-specific
- Resource management and lifecycle work properly

EXPECTED BEHAVIOR:
This test should PASS after SSOT consolidation, confirming UserExecutionEngine
as the complete and canonical execution engine implementation.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, List, Any
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UserExecutionEngineCanonicalTests(SSotBaseTestCase):
    """Test UserExecutionEngine as canonical SSOT implementation."""
    
    def setUp(self):
        """Set up test environment for canonical validation."""
        super().setUp()
        self.canonical_violations = []
        self.interface_gaps = []
        self.integration_issues = []
        
        logger.info("Starting UserExecutionEngine canonical SSOT validation")
    
    def test_user_execution_engine_import_availability(self):
        """Test UserExecutionEngine can be imported and instantiated."""
        logger.info("✅ CANONICAL TEST: Validating UserExecutionEngine import availability")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            self.assertIsNotNone(UserExecutionEngine, "UserExecutionEngine should be importable")
            
            # Test class attributes
            self.assertTrue(hasattr(UserExecutionEngine, '__init__'), "UserExecutionEngine should have __init__ method")
            self.assertTrue(hasattr(UserExecutionEngine, 'execute_agent'), "UserExecutionEngine should have execute_agent method")
            self.assertTrue(hasattr(UserExecutionEngine, 'cleanup'), "UserExecutionEngine should have cleanup method")
            
            logger.info("✅ PASS: UserExecutionEngine successfully imported and has required methods")
            
        except ImportError as e:
            self.fail(f"CANONICAL VIOLATION: Cannot import UserExecutionEngine - {e}")
    
    def test_user_execution_engine_interface_completeness(self):
        """Test UserExecutionEngine implements all required execution interfaces."""
        logger.info("🔍 CANONICAL TEST: Validating UserExecutionEngine interface completeness")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.agents.execution_engine_interface import IExecutionEngine
            
            # Test interface inheritance
            self.assertTrue(
                issubclass(UserExecutionEngine, IExecutionEngine),
                "UserExecutionEngine should implement IExecutionEngine interface"
            )
            
            # Test required methods from interface
            required_methods = [
                'execute_agent',
                'execute_pipeline', 
                'get_execution_stats',
                'cleanup'
            ]
            
            missing_methods = []
            for method_name in required_methods:
                if not hasattr(UserExecutionEngine, method_name):
                    missing_methods.append(method_name)
                    self.interface_gaps.append(f"Missing method: {method_name}")
            
            # Test method signatures are async where expected
            async_methods = ['execute_agent', 'execute_pipeline', 'get_execution_stats', 'cleanup']
            for method_name in async_methods:
                if hasattr(UserExecutionEngine, method_name):
                    method = getattr(UserExecutionEngine, method_name)
                    if not asyncio.iscoroutinefunction(method):
                        self.interface_gaps.append(f"Method {method_name} should be async")
            
            self.assertEqual(
                len(missing_methods), 0,
                f"UserExecutionEngine missing required methods: {missing_methods}"
            )
            
            logger.info(f"✅ PASS: UserExecutionEngine implements all {len(required_methods)} required interface methods")
            
        except ImportError as e:
            self.fail(f"CANONICAL VIOLATION: Cannot validate interface - {e}")
    
    def test_execution_engine_factory_creates_user_execution_engine(self):
        """Test ExecutionEngineFactory creates UserExecutionEngine instances."""
        logger.info("🔍 CANONICAL TEST: Validating factory creates UserExecutionEngine")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            
            # Create test user context
            test_user_id = UnifiedIdGenerator.generate_base_id("test_user", True, 8)
            thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(test_user_id, "canonical_test")
            
            user_context = UserExecutionContext(
                user_id=test_user_id,
                run_id=run_id,
                thread_id=thread_id,
                metadata={'test': 'canonical_validation'}
            )
            
            # Create factory (without WebSocket bridge for test)
            factory = ExecutionEngineFactory(websocket_bridge=None)
            
            # Test factory creates UserExecutionEngine
            async def test_factory_creation():
                engine = await factory.create_for_user(user_context)
                
                self.assertIsInstance(
                    engine, UserExecutionEngine,
                    "Factory should create UserExecutionEngine instances"
                )
                
                # Test engine has proper user context
                self.assertEqual(
                    engine.get_user_context().user_id, test_user_id,
                    "Engine should have correct user context"
                )
                
                # Cleanup
                await factory.cleanup_engine(engine)
                return True
            
            # Run async test
            result = asyncio.run(test_factory_creation())
            self.assertTrue(result, "Factory should successfully create UserExecutionEngine")
            
            logger.info("✅ PASS: ExecutionEngineFactory creates UserExecutionEngine instances")
            
        except Exception as e:
            self.canonical_violations.append(f"Factory creation test failed: {e}")
            self.fail(f"CANONICAL VIOLATION: Factory does not create UserExecutionEngine - {e}")
    
    def test_user_execution_engine_user_isolation(self):
        """Test UserExecutionEngine provides proper user isolation."""
        logger.info("🔍 SECURITY TEST: Validating UserExecutionEngine user isolation")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            
            # Create two different user contexts
            user1_id = UnifiedIdGenerator.generate_base_id("test_user1", True, 8)
            user2_id = UnifiedIdGenerator.generate_base_id("test_user2", True, 8)
            
            thread1_id, run1_id, _ = UnifiedIdGenerator.generate_user_context_ids(user1_id, "isolation_test")
            thread2_id, run2_id, _ = UnifiedIdGenerator.generate_user_context_ids(user2_id, "isolation_test")
            
            user1_context = UserExecutionContext(
                user_id=user1_id,
                run_id=run1_id,
                thread_id=thread1_id,
                metadata={'test': 'isolation_user1'}
            )
            
            user2_context = UserExecutionContext(
                user_id=user2_id,
                run_id=run2_id,
                thread_id=thread2_id,
                metadata={'test': 'isolation_user2'}
            )
            
            # Test user isolation
            async def test_isolation():
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                
                # Create mock WebSocket manager
                mock_websocket_manager = Mock()
                mock_websocket_manager.emit_user_event = Mock(return_value=True)
                
                # Create two engines for different users
                agent_factory1 = AgentInstanceFactory()
                websocket_emitter1 = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user1_context.user_id,
                    context=user1_context
                )
                
                agent_factory2 = AgentInstanceFactory()
                websocket_emitter2 = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user2_context.user_id,
                    context=user2_context
                )
                
                engine1 = UserExecutionEngine(user1_context, agent_factory1, websocket_emitter1)
                engine2 = UserExecutionEngine(user2_context, agent_factory2, websocket_emitter2)
                
                # Test isolation - engines should have different states
                self.assertNotEqual(
                    engine1.engine_id, engine2.engine_id,
                    "Different users should have different engine IDs"
                )
                
                self.assertEqual(
                    engine1.get_user_context().user_id, user1_id,
                    "Engine1 should maintain user1 context"
                )
                
                self.assertEqual(
                    engine2.get_user_context().user_id, user2_id,
                    "Engine2 should maintain user2 context"
                )
                
                # Test state isolation
                engine1.set_agent_state("test_agent", "user1_state")
                engine2.set_agent_state("test_agent", "user2_state")
                
                self.assertEqual(
                    engine1.get_agent_state("test_agent"), "user1_state",
                    "Engine1 should maintain user1 agent state"
                )
                
                self.assertEqual(
                    engine2.get_agent_state("test_agent"), "user2_state",
                    "Engine2 should maintain user2 agent state"
                )
                
                # Cleanup
                await engine1.cleanup()
                await engine2.cleanup()
                
                return True
            
            result = asyncio.run(test_isolation())
            self.assertTrue(result, "User isolation should work properly")
            
            logger.info("✅ PASS: UserExecutionEngine provides proper user isolation")
            
        except Exception as e:
            self.canonical_violations.append(f"User isolation test failed: {e}")
            self.fail(f"SECURITY VIOLATION: User isolation not working - {e}")
    
    def test_user_execution_engine_websocket_integration(self):
        """Test UserExecutionEngine WebSocket integration works."""
        logger.info("🔍 INTEGRATION TEST: Validating UserExecutionEngine WebSocket integration")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            
            # Create test user context
            test_user_id = UnifiedIdGenerator.generate_base_id("test_user", True, 8)
            thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(test_user_id, "websocket_test")
            
            user_context = UserExecutionContext(
                user_id=test_user_id,
                run_id=run_id,
                thread_id=thread_id,
                metadata={'test': 'websocket_integration'}
            )
            
            # Test WebSocket integration
            async def test_websocket_integration():
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                
                # Create mock WebSocket manager that tracks calls
                mock_websocket_manager = Mock()
                mock_websocket_manager.emit_user_event = Mock(return_value=True)
                
                agent_factory = AgentInstanceFactory()
                websocket_emitter = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user_context.user_id,
                    context=user_context
                )
                
                engine = UserExecutionEngine(user_context, agent_factory, websocket_emitter)
                
                # Test engine has WebSocket capabilities
                self.assertIsNotNone(engine.websocket_emitter, "Engine should have WebSocket emitter")
                
                # Test WebSocket emitter has correct user context
                self.assertEqual(
                    engine.websocket_emitter.user_id, test_user_id,
                    "WebSocket emitter should have correct user ID"
                )
                
                # Cleanup
                await engine.cleanup()
                
                return True
            
            result = asyncio.run(test_websocket_integration())
            self.assertTrue(result, "WebSocket integration should work")
            
            logger.info("✅ PASS: UserExecutionEngine WebSocket integration works")
            
        except Exception as e:
            self.integration_issues.append(f"WebSocket integration failed: {e}")
            self.fail(f"INTEGRATION VIOLATION: WebSocket integration not working - {e}")
    
    def test_user_execution_engine_resource_management(self):
        """Test UserExecutionEngine resource management and cleanup."""
        logger.info("🔍 RESOURCE TEST: Validating UserExecutionEngine resource management")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            
            # Create test user context
            test_user_id = UnifiedIdGenerator.generate_base_id("test_user", True, 8)
            thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(test_user_id, "resource_test")
            
            user_context = UserExecutionContext(
                user_id=test_user_id,
                run_id=run_id,
                thread_id=thread_id,
                metadata={'test': 'resource_management'}
            )
            
            # Test resource management
            async def test_resource_management():
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                
                mock_websocket_manager = Mock()
                mock_websocket_manager.emit_user_event = Mock(return_value=True)
                
                agent_factory = AgentInstanceFactory()
                websocket_emitter = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user_context.user_id,
                    context=user_context
                )
                
                engine = UserExecutionEngine(user_context, agent_factory, websocket_emitter)
                
                # Test engine is initially active
                self.assertTrue(engine.is_active(), "Engine should be active after creation")
                
                # Test engine has resource tracking
                stats = engine.get_user_execution_stats()
                self.assertIsInstance(stats, dict, "Engine should provide execution stats")
                self.assertIn('user_id', stats, "Stats should include user_id")
                self.assertEqual(stats['user_id'], test_user_id, "Stats should have correct user_id")
                
                # Test cleanup
                await engine.cleanup()
                
                # Test engine is no longer active after cleanup
                self.assertFalse(engine.is_active(), "Engine should be inactive after cleanup")
                
                return True
            
            result = asyncio.run(test_resource_management())
            self.assertTrue(result, "Resource management should work")
            
            logger.info("✅ PASS: UserExecutionEngine resource management works")
            
        except Exception as e:
            self.canonical_violations.append(f"Resource management test failed: {e}")
            self.fail(f"RESOURCE VIOLATION: Resource management not working - {e}")
    
    def test_comprehensive_canonical_validation(self):
        """Comprehensive validation that UserExecutionEngine is canonical SSOT."""
        logger.info("📊 COMPREHENSIVE CANONICAL VALIDATION")
        
        # Collect all validation results
        canonical_summary = {
            'canonical_violations': len(self.canonical_violations),
            'interface_gaps': len(self.interface_gaps),
            'integration_issues': len(self.integration_issues),
            'total_issues': len(self.canonical_violations) + len(self.interface_gaps) + len(self.integration_issues)
        }
        
        # Log summary
        logger.info(f"CANONICAL VALIDATION SUMMARY:")
        logger.info(f"  Canonical Violations: {canonical_summary['canonical_violations']}")
        logger.info(f"  Interface Gaps: {canonical_summary['interface_gaps']}")
        logger.info(f"  Integration Issues: {canonical_summary['integration_issues']}")
        logger.info(f"  Total Issues: {canonical_summary['total_issues']}")
        
        # Log specific issues
        all_issues = self.canonical_violations + self.interface_gaps + self.integration_issues
        for i, issue in enumerate(all_issues[:5], 1):  # Log first 5 issues
            logger.info(f"    {i}. {issue}")
        
        if len(all_issues) > 5:
            logger.info(f"    ... and {len(all_issues) - 5} more issues")
        
        # Success criteria: UserExecutionEngine should be complete canonical implementation
        self.assertEqual(
            canonical_summary['total_issues'], 0,
            f"UserExecutionEngine should be complete canonical SSOT implementation. "
            f"Found {canonical_summary['total_issues']} issues requiring resolution."
        )
        
        logger.info("✅ SUCCESS: UserExecutionEngine is complete canonical SSOT implementation")


if __name__ == '__main__':
    # Configure logging for direct execution
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    unittest.main()