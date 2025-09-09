#!/usr/bin/env python3
"""
Simple WebSocket Events Validation Test

Tests that agents progress beyond "start agent" and deliver complete responses
with all 5 critical WebSocket events.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set
from unittest.mock import AsyncMock, Mock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core components
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from shared.id_generation import UnifiedIdGenerator, generate_uuid_replacement


class WebSocketEventsValidator:
    """Simple validator for WebSocket agent events."""
    
    def __init__(self):
        self.collected_events: List[Dict] = []
        self.required_events: Set[str] = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        self.mock_llm_manager = self._create_mock_llm()
        self.mock_websocket_bridge = self._create_mock_websocket_bridge()
        
    def _create_mock_llm(self) -> Mock:
        """Create mock LLM manager that returns realistic responses."""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.is_available = Mock(return_value=True)
        mock_llm.generate_response = AsyncMock(side_effect=[
            # Triage agent response
            {
                "category": "cost_optimization",
                "priority": "high",
                "next_agents": ["data_helper", "optimization_agent"],
                "reasoning": "User requested cost analysis, will analyze current spending patterns"
            },
            # Data helper response
            {
                "data_analysis": "Current monthly AI spend: $5000",
                "usage_patterns": {"gpt-4": 60, "claude": 40},
                "inefficiencies": ["Over-using premium models for simple tasks"]
            },
            # Optimization agent response
            {
                "recommendations": [
                    "Switch to GPT-3.5 for simple queries",
                    "Implement request batching"
                ],
                "potential_savings": {"monthly": 1500, "percentage": 30},
                "implementation_plan": "Phase 1: Audit usage, Phase 2: Deploy routing"
            }
        ])
        return mock_llm
        
    def _create_mock_websocket_bridge(self) -> Mock:
        """Create mock WebSocket bridge that captures events."""
        mock_bridge = Mock(spec=AgentWebSocketBridge)
        
        # Mock WebSocket manager
        mock_websocket_manager = Mock(spec=WebSocketManager)
        mock_websocket_manager.send_to_user = AsyncMock(side_effect=self._capture_websocket_event)
        mock_websocket_manager.is_connected = Mock(return_value=True)
        
        # Mock bridge methods
        mock_bridge.websocket_manager = mock_websocket_manager
        mock_bridge.emit_agent_event = AsyncMock(side_effect=self._capture_agent_event)
        
        return mock_bridge
        
    async def _capture_websocket_event(self, user_id: str, event_data: Dict):
        """Capture WebSocket events for validation."""
        event_data['captured_at'] = datetime.utcnow().isoformat()
        event_data['user_id'] = user_id
        event_data['source'] = 'websocket_manager'
        self.collected_events.append(event_data)
        logger.info(f"📨 Captured WebSocket event: {event_data.get('type')} for user {user_id}")
        
    async def _capture_agent_event(self, event_type: str, data: Dict, run_id: str = None, agent_name: str = None):
        """Capture agent events for validation."""
        event_data = {
            'type': event_type,
            'data': data,
            'run_id': run_id,
            'agent_name': agent_name,
            'captured_at': datetime.utcnow().isoformat(),
            'source': 'agent_bridge'
        }
        self.collected_events.append(event_data)
        logger.info(f"🤖 Captured agent event: {event_type} from {agent_name}")
        
    def create_test_user_context(self) -> UserExecutionContext:
        """Create test user context for agent execution."""
        user_id = f"test-user-{generate_uuid_replacement()}"
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, "validation")
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=UnifiedIdGenerator.generate_websocket_client_id(user_id),
            db_session=None,  # Mock for this test
            agent_context={
                'user_request': 'Analyze my AI costs and suggest optimizations',
                'request_type': 'cost_optimization',
                'test_mode': True
            },
            audit_metadata={
                'test_source': 'websocket_events_validation',
                'created_at': datetime.utcnow().isoformat()
            }
        )
        
    async def test_complete_agent_execution_with_events(self) -> Dict:
        """Test complete agent execution with WebSocket event validation."""
        logger.info("🚀 Starting WebSocket events validation test...")
        
        # Create supervisor with mocked dependencies
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Create test user context
        user_context = self.create_test_user_context()
        
        # Execute agent with event streaming
        start_time = asyncio.get_event_loop().time()
        try:
            result = await supervisor.execute(user_context, stream_updates=True)
            execution_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"✅ Agent execution completed in {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"❌ Agent execution failed after {execution_time:.2f}s: {e}")
            result = {"error": str(e), "execution_failed": True}
        
        # Analyze collected events
        return self._analyze_collected_events(result, execution_time)
        
    def _analyze_collected_events(self, execution_result: Dict, execution_time: float) -> Dict:
        """Analyze collected WebSocket events for completeness."""
        # Extract event types
        event_types = {event.get('type') for event in self.collected_events}
        missing_events = self.required_events - event_types
        
        # Count events by type
        event_counts = {}
        for event in self.collected_events:
            event_type = event.get('type', 'unknown')
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Analyze event sequence
        event_sequence = [e.get('type') for e in self.collected_events if e.get('type') in self.required_events]
        
        # Determine test result
        test_passed = len(missing_events) == 0 and execution_result.get('execution_failed') != True
        
        analysis = {
            'test_passed': test_passed,
            'execution_time': execution_time,
            'total_events_captured': len(self.collected_events),
            'required_events_received': len(event_types & self.required_events),
            'missing_events': list(missing_events),
            'event_counts': event_counts,
            'event_sequence': event_sequence,
            'all_events': self.collected_events,
            'execution_result': execution_result
        }
        
        # Log results
        if test_passed:
            logger.info("🎉 SUCCESS: All required WebSocket events received!")
            logger.info(f"📊 Events received: {sorted(list(event_types & self.required_events))}")
        else:
            logger.error("❌ FAILURE: Missing WebSocket events!")
            logger.error(f"📊 Missing: {missing_events}")
            logger.error(f"📊 Received: {sorted(list(event_types))}")
            
        logger.info(f"📈 Total events captured: {len(self.collected_events)}")
        logger.info(f"⏱️ Execution time: {execution_time:.2f}s")
        
        return analysis


async def run_websocket_events_validation():
    """Run the WebSocket events validation test."""
    print("=" * 80)
    print("🧪 GOLDEN PATH INTEGRATION TEST: WebSocket Agent Events Validation")
    print("=" * 80)
    
    validator = WebSocketEventsValidator()
    
    try:
        analysis = await validator.test_complete_agent_execution_with_events()
        
        print(f"\n{'=' * 50}")
        print("📋 TEST RESULTS SUMMARY")
        print(f"{'=' * 50}")
        print(f"✅ Test Passed: {analysis['test_passed']}")
        print(f"⏱️ Execution Time: {analysis['execution_time']:.2f}s")
        print(f"📊 Total Events: {analysis['total_events_captured']}")
        print(f"🎯 Required Events Received: {analysis['required_events_received']}/5")
        
        if analysis['missing_events']:
            print(f"❌ Missing Events: {analysis['missing_events']}")
        else:
            print("✅ All 5 critical events received!")
            
        print(f"📈 Event Sequence: {' → '.join(analysis['event_sequence'])}")
        
        # Show event details
        print(f"\n{'=' * 30}")
        print("📋 EVENT DETAILS")
        print(f"{'=' * 30}")
        for event_type, count in analysis['event_counts'].items():
            print(f"  {event_type}: {count} events")
            
        # Success/failure message
        if analysis['test_passed']:
            print(f"\n🚀 SUCCESS: Agent execution progressed beyond 'start agent' to deliver complete user responses!")
            print(f"💰 Business Value: Users will see substantive AI interactions with real-time progress")
            return True
        else:
            print(f"\n💥 FAILURE: Agent execution did not complete properly or missing WebSocket events")
            print(f"🚨 Business Impact: Users won't see agent progress, breaking core chat value")
            return False
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: Test execution failed: {e}")
        print(f"🚨 This indicates fundamental issues with agent execution pipeline")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_websocket_events_validation())
    exit(0 if success else 1)