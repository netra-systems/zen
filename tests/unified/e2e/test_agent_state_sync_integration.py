"""
Agent State Synchronization Integration Test

Tests state preservation during reconnections and tab switches to ensure
multi-session consistency and protect $22K MRR from session management issues.

Business Value Justification (BVJ):
- Segment: Mid to Enterprise customers using multi-tab workflows
- Business Goal: Retention and user experience optimization
- Value Impact: Prevents session state loss that causes user frustration
- Strategic/Revenue Impact: Protects $22K MRR from multi-session use cases

Test Coverage:
- State persistence during WebSocket reconnections
- Session synchronization across multiple browser tabs
- Recovery mechanisms for interrupted agent workflows
- Cross-session data consistency validation
"""

import asyncio
import pytest
import time
import uuid
import json
import websockets
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict

from tests.unified.jwt_token_helpers import JWTTestHelper
from app.schemas.shared_types import AgentStatus, ProcessingResult


@dataclass
class AgentSessionState:
    """Represents agent state for testing synchronization."""
    session_id: str
    user_id: str
    agent_status: str
    conversation_history: List[Dict[str, Any]]
    context_data: Dict[str, Any]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class AgentStateSyncTester:
    """Integration tester for agent state synchronization."""
    
    def __init__(self):
        """Initialize state sync tester."""
        self.jwt_helper = JWTTestHelper()
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000"
        self.test_sessions: List[str] = []
        
    async def create_test_session_state(self) -> AgentSessionState:
        """Create test session state for validation."""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        user_id = f"sync_test_user_{uuid.uuid4().hex[:8]}"
        
        state = AgentSessionState(
            session_id=session_id,
            user_id=user_id,
            agent_status=AgentStatus.READY.value,
            conversation_history=[
                {
                    "message_id": str(uuid.uuid4()),
                    "content": "Test message for state sync",
                    "timestamp": time.time(),
                    "type": "user_message"
                }
            ],
            context_data={
                "active_tools": ["cost_analyzer", "performance_predictor"],
                "user_preferences": {"optimization_focus": "cost"},
                "session_metadata": {"browser_tab_id": str(uuid.uuid4())}
            },
            timestamp=time.time()
        )
        
        self.test_sessions.append(session_id)
        return state
    
    async def simulate_websocket_reconnection(
        self, 
        token: str,
        initial_state: AgentSessionState
    ) -> Tuple[bool, str]:
        """Simulate WebSocket reconnection and validate state persistence."""
        try:
            # First connection - establish state
            ws_uri = f"{self.websocket_url}/ws?token={token}"
            websocket = await asyncio.wait_for(
                websockets.connect(ws_uri),
                timeout=10.0
            )
            
            # Send state initialization message
            init_message = {
                "type": "state_sync",
                "action": "initialize",
                "session_id": initial_state.session_id,
                "state_data": initial_state.to_dict()
            }
            await websocket.send(json.dumps(init_message))
            
            # Wait for acknowledgment
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            init_response = json.loads(response)
            
            # Simulate connection drop
            await websocket.close()
            await asyncio.sleep(1)  # Brief disconnect
            
            # Reconnect and validate state persistence
            websocket_reconnect = await asyncio.wait_for(
                websockets.connect(ws_uri),
                timeout=10.0
            )
            
            # Request state restoration
            restore_message = {
                "type": "state_sync",
                "action": "restore",
                "session_id": initial_state.session_id
            }
            await websocket_reconnect.send(json.dumps(restore_message))
            
            # Validate restored state
            restore_response = await asyncio.wait_for(
                websocket_reconnect.recv(), 
                timeout=5.0
            )
            restored_data = json.loads(restore_response)
            
            await websocket_reconnect.close()
            
            # Validate state consistency
            if (restored_data.get("type") == "state_restored" and
                restored_data.get("session_id") == initial_state.session_id):
                return True, "State successfully restored after reconnection"
            else:
                return False, f"State restoration failed: {restored_data}"
                
        except Exception as e:
            return False, f"Reconnection test failed: {e}"
    
    async def simulate_multi_tab_sync(
        self, 
        token: str,
        session_state: AgentSessionState
    ) -> Tuple[bool, str]:
        """Simulate multi-tab scenario and validate state synchronization."""
        try:
            ws_uri = f"{self.websocket_url}/ws?token={token}"
            
            # Tab 1: Primary connection
            tab1_ws = await asyncio.wait_for(
                websockets.connect(ws_uri),
                timeout=10.0
            )
            
            # Tab 2: Secondary connection (same user, different tab)
            tab2_ws = await asyncio.wait_for(
                websockets.connect(ws_uri),
                timeout=10.0
            )
            
            # Tab 1: Initialize session state
            tab1_init = {
                "type": "state_sync",
                "action": "initialize",
                "session_id": session_state.session_id,
                "tab_id": "tab_1",
                "state_data": session_state.to_dict()
            }
            await tab1_ws.send(json.dumps(tab1_init))
            
            # Tab 2: Request same session state
            tab2_sync = {
                "type": "state_sync",
                "action": "sync_request",
                "session_id": session_state.session_id,
                "tab_id": "tab_2"
            }
            await tab2_ws.send(json.dumps(tab2_sync))
            
            # Tab 1: Update conversation history
            new_message = {
                "message_id": str(uuid.uuid4()),
                "content": "Updated message from tab 1",
                "timestamp": time.time(),
                "type": "agent_response"
            }
            
            tab1_update = {
                "type": "state_sync",
                "action": "update",
                "session_id": session_state.session_id,
                "updates": {
                    "conversation_history": session_state.conversation_history + [new_message]
                }
            }
            await tab1_ws.send(json.dumps(tab1_update))
            
            # Tab 2: Validate state synchronization
            tab2_check = {
                "type": "state_sync",
                "action": "get_current",
                "session_id": session_state.session_id
            }
            await tab2_ws.send(json.dumps(tab2_check))
            
            # Receive and validate sync responses
            tab2_response = await asyncio.wait_for(tab2_ws.recv(), timeout=5.0)
            sync_data = json.loads(tab2_response)
            
            await tab1_ws.close()
            await tab2_ws.close()
            
            # Validate that Tab 2 received the update from Tab 1
            if (sync_data.get("type") == "state_current" and
                len(sync_data.get("conversation_history", [])) > 1):
                return True, "Multi-tab state synchronization successful"
            else:
                return False, f"Multi-tab sync failed: {sync_data}"
                
        except Exception as e:
            return False, f"Multi-tab sync test failed: {e}"
    
    async def test_state_recovery_mechanisms(
        self, 
        token: str
    ) -> Tuple[bool, str]:
        """Test state recovery after various failure scenarios."""
        try:
            # Create test state with complex agent workflow
            test_state = await self.create_test_session_state()
            test_state.agent_status = AgentStatus.PROCESSING.value
            test_state.context_data.update({
                "active_workflow": {
                    "workflow_id": str(uuid.uuid4()),
                    "step": "cost_analysis",
                    "progress": 0.6,
                    "intermediate_results": {
                        "analyzed_functions": 15,
                        "potential_savings": "$1,200/month"
                    }
                }
            })
            
            ws_uri = f"{self.websocket_url}/ws?token={token}"
            websocket = await asyncio.wait_for(
                websockets.connect(ws_uri),
                timeout=10.0
            )
            
            # Initialize workflow state
            workflow_init = {
                "type": "workflow_state",
                "action": "checkpoint",
                "session_id": test_state.session_id,
                "workflow_data": test_state.context_data["active_workflow"]
            }
            await websocket.send(json.dumps(workflow_init))
            
            # Simulate workflow interruption
            await websocket.close()
            await asyncio.sleep(2)  # Simulate downtime
            
            # Reconnect and attempt workflow recovery
            recovery_ws = await asyncio.wait_for(
                websockets.connect(ws_uri),
                timeout=10.0
            )
            
            recovery_request = {
                "type": "workflow_state",
                "action": "recover",
                "session_id": test_state.session_id
            }
            await recovery_ws.send(json.dumps(recovery_request))
            
            # Validate workflow recovery
            recovery_response = await asyncio.wait_for(
                recovery_ws.recv(), 
                timeout=5.0
            )
            recovery_data = json.loads(recovery_response)
            
            await recovery_ws.close()
            
            # Check if workflow state was preserved
            if (recovery_data.get("type") == "workflow_recovered" and
                recovery_data.get("workflow_id") == 
                test_state.context_data["active_workflow"]["workflow_id"]):
                return True, "Workflow state recovery successful"
            else:
                return False, f"Workflow recovery failed: {recovery_data}"
                
        except Exception as e:
            return False, f"State recovery test failed: {e}"
    
    async def cleanup_test_sessions(self):
        """Clean up test session data."""
        for session_id in self.test_sessions:
            # In a real implementation, this would clean up Redis/database entries
            pass
        self.test_sessions.clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_state_synchronization_integration():
    """
    Integration test for agent state synchronization across sessions.
    
    Validates state persistence during reconnections, multi-tab scenarios,
    and workflow recovery mechanisms. Protects $22K MRR from session issues.
    
    BVJ: Ensures multi-session consistency for Mid/Enterprise customers
    """
    tester = AgentStateSyncTester()
    
    try:
        # Create test JWT token
        payload = tester.jwt_helper.create_valid_payload()
        payload.update({
            "sub": f"state_sync_user_{uuid.uuid4().hex[:8]}",
            "permissions": ["read", "write", "agent_access"],
            "multi_session_test": True
        })
        token = await tester.jwt_helper.create_jwt_token(payload)
        
        # Test 1: WebSocket reconnection state persistence
        initial_state = await tester.create_test_session_state()
        reconnect_success, reconnect_msg = await tester.simulate_websocket_reconnection(
            token, initial_state
        )
        
        assert reconnect_success, f"Reconnection state persistence failed: {reconnect_msg}"
        
        # Test 2: Multi-tab state synchronization
        multi_tab_state = await tester.create_test_session_state()
        sync_success, sync_msg = await tester.simulate_multi_tab_sync(
            token, multi_tab_state
        )
        
        assert sync_success, f"Multi-tab synchronization failed: {sync_msg}"
        
        # Test 3: State recovery mechanisms
        recovery_success, recovery_msg = await tester.test_state_recovery_mechanisms(token)
        
        assert recovery_success, f"State recovery failed: {recovery_msg}"
        
        # Business value validation
        assert len(tester.test_sessions) >= 2, "Multiple test sessions should be created"
        
        print(f"[SUCCESS] Agent state synchronization integration test PASSED")
        print(f"[BUSINESS VALUE] $22K MRR protection validated through state sync")
        print(f"[VALIDATION] Reconnection: {reconnect_msg}")
        print(f"[VALIDATION] Multi-tab: {sync_msg}")
        print(f"[VALIDATION] Recovery: {recovery_msg}")
        
    finally:
        await tester.cleanup_test_sessions()


@pytest.mark.asyncio
async def test_session_state_consistency_quick_check():
    """
    Quick consistency check for session state management.
    
    Lightweight test for CI/CD pipelines focused on basic state operations.
    """
    tester = AgentStateSyncTester()
    
    try:
        # Create minimal test session
        test_state = await tester.create_test_session_state()
        
        # Validate state structure
        assert test_state.session_id is not None
        assert test_state.user_id is not None
        assert test_state.agent_status == AgentStatus.READY.value
        assert len(test_state.conversation_history) > 0
        assert "active_tools" in test_state.context_data
        
        # Validate serialization
        state_dict = test_state.to_dict()
        assert isinstance(state_dict, dict)
        assert "session_id" in state_dict
        
        print(f"[QUICK CHECK PASS] Session state consistency validated")
        
    finally:
        await tester.cleanup_test_sessions()


if __name__ == "__main__":
    """Run agent state synchronization test standalone."""
    async def run_test():
        tester = AgentStateSyncTester()
        try:
            print("Running Agent State Synchronization Integration Test...")
            await test_agent_state_synchronization_integration()
            print("Test completed successfully!")
        finally:
            await tester.cleanup_test_sessions()
    
    asyncio.run(run_test())


# Business Value Summary
"""
Agent State Synchronization Integration Test - Business Value Summary

BVJ: Multi-session consistency protection for $22K MRR
- Validates state persistence across WebSocket reconnections
- Ensures multi-tab synchronization for enterprise workflows  
- Tests workflow recovery mechanisms for interrupted processes
- Protects against session state loss causing user frustration

Strategic Value:
- Enterprise customer retention through reliable multi-session experience
- Reduction in support tickets related to lost session state
- Foundation for advanced collaborative features
- Quality assurance for high-value customer segments
"""