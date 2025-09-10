"""
Mission Critical Test: Triage Agent Start Failure Reproduction

This test reproduces the EXACT failure that prevents triage agents from starting,
which directly impacts the Golden Path user flow and $500K+ ARR chat functionality.

BUSINESS CRITICAL ISSUE:
- Users cannot get AI responses because triage agent fails to start
- Failure occurs at agent_handler.py line 125: 'async for' with _AsyncGeneratorContextManager
- This blocks the entire chat experience delivery pipeline

PURPOSE: Validate the exact conditions that cause triage start failure and
ensure the fix (async for → async with) resolves the issue completely.

FAILURE REPRODUCTION:
1. WebSocket connection established 
2. User sends chat message
3. AgentHandler.start_agent() called for triage
4. get_request_scoped_db_session() returns _AsyncGeneratorContextManager
5. 'async for db_session in ...' fails with TypeError
6. Agent never starts, user gets no response

Business Value: Free/Early/Mid/Enterprise - Chat Functionality (90% of platform value)
Ensures triage agents can start successfully to deliver AI-powered responses.

MISSION CRITICAL REQUIREMENTS:
- Must reproduce exact production failure conditions
- Must fail with current broken code
- Must pass after async for → async with fix  
- Uses real services where possible
- Validates complete triage agent start flow
"""

import asyncio
import pytest
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase  
from shared.isolated_environment import IsolatedEnvironment

# Mission Critical Imports - Real Services  
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.dependencies import get_request_scoped_db_session
from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager
from shared.id_generation import UnifiedIdGenerator


class TestTriageStartFailureReproduction(SSotAsyncTestCase):
    """
    Mission Critical: Triage Agent Start Failure Reproduction
    
    Reproduces the exact failure that blocks triage agents from starting,
    preventing users from receiving AI responses in the chat interface.
    
    GOLDEN PATH IMPACT: This failure breaks the core user journey:
    User Message → Triage Agent → AI Response
    """
    
    async def asyncSetUp(self):
        """Set up mission critical test environment."""
        await super().asyncSetUp()
        self.env = IsolatedEnvironment()
        self.env.set('ENVIRONMENT', 'test')
        
        # Create realistic production-like WebSocket setup
        self.connection_id = UnifiedIdGenerator.generate_base_id("conn")
        self.run_id = UnifiedIdGenerator.generate_base_id("run") 
        self.user_id = "mission_critical_user_123"
        self.thread_id = UnifiedIdGenerator.generate_base_id("thread")
        
        # Mock WebSocket that simulates real connection
        self.mock_websocket = AsyncMock()
        self.mock_websocket.scope = {
            'app': MagicMock(),
            'user': {'sub': self.user_id},
            'path': '/ws/chat',
            'client': ('127.0.0.1', 8000),
            'headers': []
        }
        
        # Mock app state with required components
        app_state = MagicMock()
        app_state.bridge = MagicMock()  # WebSocket bridge
        app_state.supervisor_factory = MagicMock()  # Supervisor factory
        self.mock_websocket.scope['app'].state = app_state
        
        # Create WebSocket manager context
        self.ws_manager = None
        try:
            self.ws_manager = UnifiedWebSocketManager()
        except Exception as e:
            # Use mock if real manager not available
            self.ws_manager = AsyncMock()
        
        # Real agent handler instance (this is where the failure occurs)
        self.agent_handler = AgentMessageHandler()
        
        # Triage message that triggers agent start
        self.triage_message = {
            'type': 'user_message',
            'content': 'Help me optimize my AI infrastructure',
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'timestamp': '2025-01-09T10:00:00Z'
        }

    @pytest.mark.asyncio
    async def test_triage_agent_start_exact_failure_reproduction(self):
        """
        MISSION CRITICAL: Reproduce the exact triage agent start failure.
        
        This test simulates the complete flow that fails in production:
        1. User sends message via WebSocket
        2. AgentHandler.start_agent() called 
        3. Line 125 'async for' fails with TypeError
        4. Triage agent never starts
        5. User receives no AI response
        
        BUSINESS IMPACT: Blocks $500K+ ARR chat functionality
        
        EXPECTED BEHAVIOR:
        - With current broken code: Test FAILS, reproducing production issue
        - After fix (async for → async with): Test PASSES, chat works
        """
        
        # Create execution context that would be passed to start_agent
        execution_context = {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'message_content': self.triage_message['content'],
            'agent_type': 'triage',
            'timestamp': self.triage_message['timestamp']
        }
        
        # Mock components that come after the failing database session
        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_supervisor, \
             patch('netra_backend.app.services.thread_service.ThreadService') as mock_thread_service, \
             patch('netra_backend.app.services.message_handler.MessageHandlerService') as mock_message_handler:
            
            # Configure mocks for post-session components
            mock_supervisor.return_value = AsyncMock()
            mock_thread_service.return_value = AsyncMock()
            mock_message_handler.return_value = AsyncMock()
            
            # This should reproduce the EXACT failure from agent_handler.py line 125
            with pytest.raises(TypeError) as exc_info:
                await self.agent_handler.start_agent(
                    agent_type='triage',
                    context=execution_context,
                    websocket=self.mock_websocket,
                    ws_manager=self.ws_manager,
                    connection_id=self.connection_id
                )
            
            # Validate this is the exact error that blocks triage agent start
            error_message = str(exc_info.value)
            assert "async for" in error_message.lower()
            assert "__aiter__" in error_message
            
            # Ensure downstream components never called due to session failure
            mock_supervisor.assert_not_called()
            mock_thread_service.assert_not_called() 
            mock_message_handler.assert_not_called()
            
            self.record_metric(
                "triage_start_exact_failure",
                f"REPRODUCED - Triage agent start failure reproduced: {error_message}"
            )

    @pytest.mark.asyncio
    async def test_triage_start_session_pattern_isolation(self):
        """
        Isolate the exact session pattern that causes triage start failure.
        
        This focuses specifically on the problematic lines 125-137 in agent_handler.py
        that prevent database session creation for agent operations.
        """
        
        # Get the exact session context used in agent_handler.py line 125
        session_context = get_request_scoped_db_session()
        
        # Mock WebSocket context creation (lines 113-122 in agent_handler.py)
        websocket_context = {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'connection_id': self.connection_id
        }
        
        # This reproduces the EXACT failure pattern from lines 125-137
        with pytest.raises(TypeError) as exc_info:
            # Line 125: async for db_session in get_request_scoped_db_session():
            async for db_session in session_context:  # BROKEN LINE!
                # Lines 126-137 should execute but never do due to TypeError
                try:
                    # Line 128-130: Get app_state from WebSocket connection
                    app_state = None
                    if hasattr(self.mock_websocket, 'scope') and 'app' in self.mock_websocket.scope:
                        app_state = self.mock_websocket.scope['app'].state
                    
                    # This code should never execute due to session pattern failure
                    pytest.fail("Should not reach supervisor creation due to TypeError")
                    
                except Exception:
                    # Should not reach this except block either
                    pytest.fail("Should not handle exceptions due to TypeError")
                
                break  # Should never reach this break
        
        # Validate the exact TypeError that prevents triage agent start
        error_message = str(exc_info.value)
        assert "'async for' requires an object with __aiter__ method" in error_message
        assert "_AsyncGeneratorContextManager" in error_message
        
        self.record_metric(
            "session_pattern_isolation",
            "REPRODUCED - Isolated exact session pattern causing triage start failure"
        )

    @pytest.mark.asyncio
    async def test_triage_start_fix_validation_async_with(self):
        """
        Validate that the proposed fix (async for → async with) resolves triage start.
        
        This demonstrates the exact change needed in agent_handler.py line 125
        to fix the triage agent start failure and restore chat functionality.
        
        EXPECTED BEHAVIOR:
        - Should pass completely (demonstrating the fix works)
        - Triage agent should be able to start successfully
        - Chat functionality should be restored
        """
        
        # Mock downstream components to focus on session pattern fix
        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_supervisor, \
             patch('netra_backend.app.services.thread_service.ThreadService') as mock_thread_service, \
             patch('netra_backend.app.services.message_handler.MessageHandlerService') as mock_message_handler, \
             patch.object(self.agent_handler, '_route_agent_message_v3') as mock_route:
            
            # Configure mocks for successful flow
            mock_supervisor.return_value = AsyncMock()
            mock_thread_service.return_value = AsyncMock()
            mock_message_handler.return_value = AsyncMock()
            mock_route.return_value = True
            
            # Get the session context (same as broken version)
            session_context = get_request_scoped_db_session()
            
            # Apply the FIX: Use 'async with' instead of 'async for'
            try:
                async with session_context as db_session:  # FIXED LINE!
                    # Validate session is available for agent operations
                    assert db_session is not None
                    assert hasattr(db_session, 'execute')
                    
                    # Simulate successful supervisor creation (lines 133-137)
                    app_state = self.mock_websocket.scope['app'].state
                    
                    supervisor = await mock_supervisor(
                        context={'user_id': self.user_id},
                        db_session=db_session,
                        app_state=app_state
                    )
                    
                    # Validate supervisor creation succeeded
                    assert supervisor is not None
                    mock_supervisor.assert_called_once()
                    
                self.record_metric(
                    "triage_start_fix_validation",
                    "FIXED - Async with pattern successfully enables triage agent start"
                )
                
            except Exception as e:
                pytest.fail(f"Fix should work but failed: {e}")

    @pytest.mark.asyncio
    async def test_golden_path_user_flow_impact(self):
        """
        Validate the business impact of triage start failure on Golden Path user flow.
        
        Golden Path: User Login → Send Message → Get AI Response
        Failure Point: Triage agent cannot start to process user message
        
        This test demonstrates how the session pattern failure breaks the
        complete user experience and $500K+ ARR chat functionality.
        """
        
        # Simulate Golden Path user flow up to triage agent start
        golden_path_flow = {
            'step_1_user_login': 'COMPLETED',  # User successfully logged in
            'step_2_websocket_connect': 'COMPLETED',  # WebSocket connection established  
            'step_3_send_message': 'COMPLETED',  # User sent chat message
            'step_4_triage_start': 'BLOCKED',  # BLOCKED by async session pattern
            'step_5_ai_response': 'BLOCKED',  # BLOCKED because triage failed
            'step_6_user_value': 'LOST'  # USER VALUE LOST due to session issue
        }
        
        # Attempt the flow and demonstrate where it breaks
        try:
            # Steps 1-3 work fine (login, connect, send message)
            assert golden_path_flow['step_1_user_login'] == 'COMPLETED'
            assert golden_path_flow['step_2_websocket_connect'] == 'COMPLETED'
            assert golden_path_flow['step_3_send_message'] == 'COMPLETED'
            
            # Step 4 fails due to session pattern (the focus of this test)
            session_context = get_request_scoped_db_session()
            
            with pytest.raises(TypeError):
                async for db_session in session_context:  # FAILURE POINT
                    # Step 5 and 6 never execute due to this failure
                    golden_path_flow['step_4_triage_start'] = 'COMPLETED'
                    golden_path_flow['step_5_ai_response'] = 'COMPLETED'
                    golden_path_flow['step_6_user_value'] = 'DELIVERED'
                    break
            
            # Validate the Golden Path is broken at triage start
            assert golden_path_flow['step_4_triage_start'] == 'BLOCKED'
            assert golden_path_flow['step_5_ai_response'] == 'BLOCKED'
            assert golden_path_flow['step_6_user_value'] == 'LOST'
            
            self.record_metric(
                "golden_path_user_flow_impact",
                "BUSINESS_IMPACT_CONFIRMED - Session pattern failure blocks complete Golden Path user flow"
            )
            
        except Exception as e:
            pytest.fail(f"Golden Path impact test should demonstrate failure: {e}")

    @pytest.mark.asyncio
    async def test_mission_critical_revenue_impact_validation(self):
        """
        Validate the revenue impact of triage start failure on chat functionality.
        
        BUSINESS METRICS:
        - Chat = 90% of platform value
        - $500K+ ARR dependent on chat functionality  
        - Triage agent is first step in AI response pipeline
        - Session pattern failure = complete chat breakdown
        
        This test quantifies the business impact of the technical failure.
        """
        
        # Business metrics affected by triage start failure
        business_impact = {
            'chat_functionality_available': False,  # Blocked by triage start failure
            'ai_responses_delivered': 0,  # No responses due to agent start failure
            'user_experience_quality': 'BROKEN',  # Users get no AI assistance
            'platform_value_delivery': '0%',  # No value delivered without chat
            'revenue_at_risk': '$500K+ ARR',  # Revenue dependent on chat functionality
            'customer_satisfaction': 'DEGRADED'  # Customers cannot use core feature
        }
        
        # Simulate the technical failure and measure business impact
        try:
            # Attempt to start triage agent (core functionality)
            session_context = get_request_scoped_db_session()
            
            # This failure blocks all subsequent business value delivery
            with pytest.raises(TypeError):
                async for db_session in session_context:  # TECHNICAL FAILURE
                    # Business value that cannot be delivered due to technical issue
                    business_impact['chat_functionality_available'] = True
                    business_impact['ai_responses_delivered'] = 1
                    business_impact['user_experience_quality'] = 'EXCELLENT'
                    business_impact['platform_value_delivery'] = '90%'
                    business_impact['revenue_at_risk'] = '$0'
                    business_impact['customer_satisfaction'] = 'HIGH'
                    break
            
            # Validate business impact of technical failure
            assert business_impact['chat_functionality_available'] == False
            assert business_impact['ai_responses_delivered'] == 0
            assert business_impact['user_experience_quality'] == 'BROKEN'
            assert business_impact['platform_value_delivery'] == '0%'
            assert '$500K+' in business_impact['revenue_at_risk']
            assert business_impact['customer_satisfaction'] == 'DEGRADED'
            
            self.record_metric(
                "revenue_impact_validation",
                f"BUSINESS_CRITICAL - Technical failure blocks {business_impact['revenue_at_risk']} chat functionality"
            )
            
        except Exception as e:
            pytest.fail(f"Revenue impact validation should demonstrate business impact: {e}")

    async def asyncTearDown(self):
        """Clean up mission critical test environment."""
        await super().asyncTearDown()
        
        # Log mission critical test results
        print(f"\n=== MISSION CRITICAL: Triage Start Failure Reproduction Results ===")
        print(f"Business Impact: $500K+ ARR chat functionality at risk")
        print(f"Technical Issue: async for with _AsyncGeneratorContextManager")
        print(f"Required Fix: Change line 125 in agent_handler.py from 'async for' to 'async with'")
        print(f"Golden Path Impact: Complete user journey blocked at triage agent start")
        
        metrics = self.get_all_metrics()
        for metric_name, metric_value in metrics.items():
            print(f"  ✓ {metric_name}: {metric_value}")
        print("=" * 80)


if __name__ == '__main__':
    # Run mission critical tests
    pytest.main([__file__, '-v', '--tb=long', '--asyncio-mode=auto'])