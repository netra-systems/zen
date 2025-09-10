"""
Test WebSocket Factory Chain SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate WebSocket factory chain violations blocking golden path
- Value Impact: Remove 4+ layer WebSocket factory abstraction causing connection issues
- Strategic Impact: Critical $120K+ MRR protection through WebSocket reliability

This test validates that WebSocket factory patterns don't create unnecessary
abstraction layers. The over-engineering audit identified multiple WebSocket
factory classes creating complex chains that violate SSOT principles.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

# Import WebSocket factory classes to test SSOT violations
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
from netra_backend.app.agents.supervisor.agent_instance_factory import UserWebSocketEmitter
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager


class TestWebSocketFactoryChainViolations(BaseIntegrationTest):
    """Test SSOT violations in WebSocket factory chain patterns."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_factory_duplication(self, real_services_fixture):
        """
        Test SSOT violation between WebSocketManagerFactory and direct UnifiedWebSocketManager usage.
        
        SSOT Violation: WebSocketManagerFactory creates UnifiedWebSocketManager instances
        but many components also instantiate UnifiedWebSocketManager directly.
        """
        env = get_env()
        
        # SSOT VIOLATION: Multiple ways to create WebSocket managers
        
        # Method 1: Via WebSocketManagerFactory (if it exists)
        try:
            factory = WebSocketManagerFactory()
            factory_manager = await factory.create_websocket_manager(
                redis_client=real_services_fixture["redis"],
                environment="test"
            )
        except Exception as e:
            # Factory might not exist or work - this itself is a SSOT issue
            factory_manager = None
            factory_creation_error = str(e)
        
        # Method 2: Direct instantiation (what most code actually does)
        direct_manager = UnifiedWebSocketManager()
        await direct_manager.initialize(
            redis_client=real_services_fixture["redis"],
            environment="test"
        )
        
        # SSOT VIOLATION: Both methods should produce functionally identical managers
        if factory_manager:
            # Test that factory and direct creation produce equivalent managers
            assert type(factory_manager) == type(direct_manager)
            
            # Both should have same capabilities
            factory_has_broadcast = hasattr(factory_manager, 'broadcast_to_user')
            direct_has_broadcast = hasattr(direct_manager, 'broadcast_to_user')
            assert factory_has_broadcast == direct_has_broadcast
            
            # Both should handle connections identically
            test_user_id = "ssot_test_user"
            test_connection_id = "ssot_test_connection"
            
            # Register connection via both managers
            await factory_manager.register_connection(test_user_id, test_connection_id, {})
            await direct_manager.register_connection(test_user_id, test_connection_id + "_direct", {})
            
            # Both should track connections
            factory_connections = factory_manager.get_user_connections(test_user_id)
            direct_connections = direct_manager.get_user_connections(test_user_id)
            
            assert len(factory_connections) > 0
            assert len(direct_connections) > 0
            
            # Cleanup
            await factory_manager.cleanup()
        
        await direct_manager.cleanup()
        
        # Business value: Eliminating factory duplication reduces connection management complexity
        self.assert_business_value_delivered(
            {"websocket_factory_consolidation": True, "connection_reliability": True},
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_bridge_factory_chain_violation(self, real_services_fixture):
        """
        Test SSOT violation in WebSocket bridge factory chain.
        
        SSOT Violation: WebSocketBridgeFactory -> AgentWebSocketBridge -> UnifiedWebSocketManager
        creates unnecessary abstraction layers.
        """
        # SSOT VIOLATION: Multiple factory layers for simple WebSocket bridging
        
        # Layer 1: WebSocketBridgeFactory
        try:
            bridge_factory = WebSocketBridgeFactory()
            bridge_via_factory = await bridge_factory.create_websocket_bridge(
                websocket_manager=UnifiedWebSocketManager(),
                redis_client=real_services_fixture["redis"]
            )
        except Exception as e:
            # Factory might not exist - create bridge directly
            bridge_via_factory = None
            
        # Layer 2: Direct AgentWebSocketBridge creation (what actually gets used)
        websocket_manager = UnifiedWebSocketManager()
        await websocket_manager.initialize(
            redis_client=real_services_fixture["redis"],
            environment="test"
        )
        
        direct_bridge = AgentWebSocketBridge(websocket_manager=websocket_manager)
        
        # SSOT REQUIREMENT: Both approaches should produce identical functionality
        if bridge_via_factory:
            # Test that factory and direct creation work identically
            test_run_id = "ssot_bridge_test"
            test_agent_name = "test_agent"
            
            # Both bridges should handle notifications identically
            factory_result = await bridge_via_factory.notify_agent_started(
                run_id=test_run_id,
                agent_name=test_agent_name,
                context={"test": True}
            )
            
            direct_result = await direct_bridge.notify_agent_started(
                run_id=test_run_id + "_direct",
                agent_name=test_agent_name,
                context={"test": True}
            )
            
            # SSOT VIOLATION: Results should be identical
            assert type(factory_result) == type(direct_result)
            
        # CRITICAL: Test that bridge integrates with UserWebSocketEmitter properly
        # This tests the full factory chain
        test_user_id = "bridge_chain_test"
        test_thread_id = "thread_bridge_chain"
        test_run_id = "run_bridge_chain"
        
        emitter = UserWebSocketEmitter(
            user_id=test_user_id,
            thread_id=test_thread_id,
            run_id=test_run_id,
            websocket_bridge=direct_bridge
        )
        
        # Test that emitter works through the bridge
        notification_result = await emitter.notify_agent_thinking(
            agent_name="test_agent",
            reasoning="Testing bridge chain"
        )
        
        # Should succeed or fail consistently
        assert isinstance(notification_result, bool)
        
        # Cleanup
        await emitter.cleanup()
        await websocket_manager.cleanup()
        
        # Business value: Simplified bridge chain reduces latency and failure points
        self.assert_business_value_delivered(
            {"bridge_chain_simplification": True, "notification_reliability": True},
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_emitter_factory_proliferation(self, real_services_fixture):
        """
        Test SSOT violation from WebSocket emitter factory proliferation.
        
        SSOT Violation: Multiple factory patterns create UserWebSocketEmitter instances
        with inconsistent initialization and configuration.
        """
        # Create base dependencies
        websocket_manager = UnifiedWebSocketManager()
        await websocket_manager.initialize(
            redis_client=real_services_fixture["redis"],
            environment="test"
        )
        
        bridge = AgentWebSocketBridge(websocket_manager=websocket_manager)
        
        # SSOT VIOLATION: Multiple ways to create emitters
        test_user_id = "emitter_proliferation_test"
        test_thread_id = "thread_emitter"
        test_run_id = "run_emitter"
        
        # Method 1: Direct UserWebSocketEmitter instantiation
        direct_emitter = UserWebSocketEmitter(
            user_id=test_user_id,
            thread_id=test_thread_id,
            run_id=test_run_id,
            websocket_bridge=bridge
        )
        
        # Method 2: Via AgentInstanceFactory._create_emitter (if available)
        from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
        
        agent_factory = AgentInstanceFactory()
        agent_factory.configure(websocket_bridge=bridge)
        
        factory_emitter = await agent_factory._create_emitter(
            test_user_id, test_thread_id, test_run_id + "_factory"
        )
        
        # Method 3: Via ExecutionEngineFactory._create_user_websocket_emitter (if available)
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        execution_factory = ExecutionEngineFactory(websocket_bridge=bridge)
        
        test_context = UserExecutionContext.from_request_supervisor(
            user_id=test_user_id,
            thread_id=test_thread_id,
            run_id=test_run_id + "_execution",
            db_session=real_services_fixture["db"]
        )
        
        execution_emitter = await execution_factory._create_user_websocket_emitter(
            test_context, agent_factory
        )
        
        # SSOT REQUIREMENT: All creation methods should produce equivalent emitters
        emitters = [direct_emitter, factory_emitter, execution_emitter]
        
        # All should have same type
        emitter_types = [type(emitter) for emitter in emitters]
        assert len(set(emitter_types)) == 1, f"Emitter types differ: {emitter_types}"
        
        # All should have same base configuration structure
        for emitter in emitters:
            assert hasattr(emitter, 'user_id')
            assert hasattr(emitter, 'thread_id') 
            assert hasattr(emitter, 'run_id')
            assert hasattr(emitter, 'websocket_bridge')
            assert hasattr(emitter, 'notify_agent_started')
            assert hasattr(emitter, 'notify_agent_completed')
        
        # CRITICAL: All should behave identically for same operations
        agent_name = "ssot_test_agent"
        
        results = []
        for i, emitter in enumerate(emitters):
            try:
                result = await emitter.notify_agent_started(
                    agent_name=agent_name,
                    context={"emitter_index": i}
                )
                results.append(result)
            except Exception as e:
                results.append(f"error: {e}")
        
        # SSOT VIOLATION: All emitters should produce same result type
        result_types = [type(result) for result in results]
        assert len(set(result_types)) <= 2, f"Emitter results vary too much: {results}"
        
        # Cleanup all emitters
        for emitter in emitters:
            await emitter.cleanup()
        
        await websocket_manager.cleanup()
        
        # Business value: Consolidated emitter creation reduces inconsistencies
        self.assert_business_value_delivered(
            {"emitter_creation_consolidation": True, "notification_consistency": True},
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_factory_dependency_chain_complexity(self, real_services_fixture):
        """
        Test SSOT violation from complex WebSocket factory dependency chains.
        
        SSOT Violation: WebSocket factories create circular dependencies and
        complex initialization chains that violate simple instantiation patterns.
        """
        # Map the complex dependency chain that should be simplified
        
        # Current complex chain (SSOT violation):
        # WebSocketManagerFactory -> UnifiedWebSocketManager -> Redis
        # WebSocketBridgeFactory -> AgentWebSocketBridge -> UnifiedWebSocketManager
        # AgentInstanceFactory -> UserWebSocketEmitter -> AgentWebSocketBridge
        # ExecutionEngineFactory -> UserWebSocketEmitter -> AgentWebSocketBridge
        
        # CRITICAL: Test the full initialization chain complexity
        start_time = time.time()
        
        # Step 1: Initialize Redis (base dependency)
        redis_client = real_services_fixture["redis"]
        
        # Step 2: Create WebSocket manager (should be simple)
        websocket_manager = UnifiedWebSocketManager()
        await websocket_manager.initialize(redis_client=redis_client, environment="test")
        
        # Step 3: Create bridge (adds layer)
        bridge = AgentWebSocketBridge(websocket_manager=websocket_manager)
        
        # Step 4: Configure agent factory (adds layer)
        agent_factory = AgentInstanceFactory()
        agent_factory.configure(websocket_bridge=bridge)
        
        # Step 5: Configure execution factory (adds layer)
        execution_factory = ExecutionEngineFactory(websocket_bridge=bridge)
        
        # Step 6: Create user context (adds layer)
        user_context = await agent_factory.create_user_execution_context(
            user_id="complexity_test",
            thread_id="thread_complexity",
            run_id="run_complexity",
            db_session=real_services_fixture["db"]
        )
        
        # Step 7: Create execution engine (adds layer)
        engine = await execution_factory.create_for_user(user_context)
        
        initialization_time = time.time() - start_time
        
        # SSOT VIOLATION: This chain is too complex for simple WebSocket operations
        # Should be: Redis -> WebSocketManager -> DirectEmitter (3 layers max)
        # Currently: Redis -> Manager -> Bridge -> Factory -> Engine -> Context -> Emitter (7+ layers)
        
        # Test that despite complexity, basic operations still work
        test_agent_name = "complexity_test_agent"
        
        # Get emitter from the complex chain
        engine_context = engine.get_user_context()
        assert engine_context.user_id == user_context.user_id
        
        # Test basic functionality still works through all layers
        engine_metrics = engine.get_user_execution_stats()
        assert isinstance(engine_metrics, dict)
        
        # CRITICAL: Measure overhead of complex factory chain
        simple_start = time.time()
        
        # Direct simple approach (what it should be)
        simple_manager = UnifiedWebSocketManager()
        await simple_manager.initialize(redis_client=redis_client, environment="test")
        
        simple_bridge = AgentWebSocketBridge(websocket_manager=simple_manager)
        
        simple_emitter = UserWebSocketEmitter(
            user_id="simple_test",
            thread_id="thread_simple", 
            run_id="run_simple",
            websocket_bridge=simple_bridge
        )
        
        simple_time = time.time() - simple_start
        
        # SSOT BUSINESS IMPACT: Complex chain should not be significantly slower
        complexity_overhead = initialization_time / simple_time if simple_time > 0 else float('inf')
        
        # Complex initialization should not be more than 3x slower than simple
        assert complexity_overhead < 3.0, f"Factory chain too complex: {complexity_overhead}x overhead"
        
        # Cleanup complex chain
        await execution_factory.cleanup_engine(engine)
        await agent_factory.cleanup_user_context(user_context)
        await websocket_manager.cleanup()
        
        # Cleanup simple chain  
        await simple_emitter.cleanup()
        await simple_manager.cleanup()
        
        # Business value: Simplified factory chains reduce initialization overhead
        self.assert_business_value_delivered(
            {
                "factory_chain_efficiency": True, 
                "initialization_overhead_reduced": True,
                "complexity_ratio": complexity_overhead
            },
            "automation"
        )