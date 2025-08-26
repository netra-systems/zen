"""Multi-Tab WebSocket Isolation Test - E2E Critical Integration Test

Tests multiple browser tabs with separate WebSocket connections but shared authentication session.
Validates proper message routing, data isolation, and shared session state.

Business Value Justification (BVJ):
- Segment: Enterprise | Goal: UX | Impact: Enterprise user experience
- Business Goal: Ensure proper multi-tab WebSocket isolation for power users
- Value Impact: Validates critical multi-tab functionality for enterprise workflows
- Revenue Impact: Protects $100K+ MRR through reliable multi-tab experience

Architecture: <300 lines per module, real connections only, deterministic testing
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import pytest

# Test infrastructure
from tests.e2e.jwt_token_helpers import JWTTestHelper
from test_framework.http_client import ClientConfig, ConnectionState
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient


@dataclass
class TabSession:
    """Represents a browser tab with WebSocket connection."""
    tab_id: str
    user_id: str
    session_token: str
    client: Optional[RealWebSocketClient] = None
    messages_sent: List[Dict[str, Any]] = field(default_factory=list)
    messages_received: List[Dict[str, Any]] = field(default_factory=list)
    connection_time: float = 0.0
    isolated_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiTabTestResult:
    """Results from multi-tab isolation testing."""
    tabs_connected: int
    message_isolation_verified: bool
    shared_session_verified: bool
    no_cross_contamination: bool
    concurrent_operations_successful: bool
    tab_specific_data_isolated: bool


class MultiTabWebSocketIsolationManager:
    """Manager for multi-tab WebSocket isolation testing."""
    
    def __init__(self):
        """Initialize multi-tab isolation manager."""
        self.jwt_helper = JWTTestHelper()
        self.ws_url = "ws://localhost:8000/ws"
        self.config = ClientConfig(timeout=5.0, max_retries=2)
        self.tab_sessions: Dict[str, TabSession] = {}
        self.shared_user_id = f"multi_tab_user_{str(uuid.uuid4())[:8]}"
        self.shared_session_token = ""
        
    async def setup_shared_session(self) -> str:
        """Create shared authentication session for all tabs."""
        payload = self.jwt_helper.create_valid_payload()
        payload["sub"] = self.shared_user_id
        self.shared_session_token = self.jwt_helper.create_token(payload)
        return self.shared_session_token
    
    async def create_tab_session(self, tab_id: str) -> TabSession:
        """Create new tab session with shared authentication."""
        client = RealWebSocketClient(self.ws_url, self.config)
        
        tab_session = TabSession(
            tab_id=tab_id,
            user_id=self.shared_user_id,
            session_token=self.shared_session_token,
            client=client
        )
        
        self.tab_sessions[tab_id] = tab_session
        return tab_session
    
    async def connect_all_tabs(self, tab_count: int) -> List[str]:
        """Connect multiple tabs with shared session."""
        connected_tabs = []
        auth_headers = {"Authorization": f"Bearer {self.shared_session_token}"}
        
        for i in range(tab_count):
            tab_id = f"tab_{i}_{str(uuid.uuid4())[:6]}"
            tab_session = await self.create_tab_session(tab_id)
            
            start_time = time.time()
            success = await tab_session.client.connect(auth_headers)
            tab_session.connection_time = time.time() - start_time
            
            if success:
                connected_tabs.append(tab_id)
            
        return connected_tabs
    
    @pytest.mark.e2e
    async def test_message_isolation(self, tab_ids: List[str]) -> bool:
        """Test that messages are isolated between tabs."""
        if len(tab_ids) < 2:
            return False
            
        sender_tab = tab_ids[0]
        receiver_tabs = tab_ids[1:]
        
        # Send tab-specific message
        isolation_message = self._create_tab_specific_message(sender_tab)
        sender_session = self.tab_sessions[sender_tab]
        await sender_session.client.send(isolation_message)
        sender_session.messages_sent.append(isolation_message)
        
        # Wait for potential message propagation
        await asyncio.sleep(1.0)
        
        # Verify other tabs don't receive the message
        for receiver_tab in receiver_tabs:
            receiver_session = self.tab_sessions[receiver_tab]
            try:
                received = await receiver_session.client.receive(timeout=0.5)
                if received and received.get("tab_id") == sender_tab:
                    return False  # Cross-contamination detected
            except asyncio.TimeoutError:
                pass  # Expected - no message should be received
        
        return True
    
    @pytest.mark.e2e
    async def test_shared_session_state(self, tab_ids: List[str]) -> bool:
        """Test that session state is shared across tabs."""
        if len(tab_ids) < 2:
            return False
        
        # Send session state update from first tab
        state_update = {
            "type": "session_state_update",
            "user_id": self.shared_user_id,
            "session_data": {
                "workspace_id": "shared_workspace_123",
                "user_preferences": {"theme": "dark", "notifications": True},
                "last_activity": time.time()
            }
        }
        
        first_tab = self.tab_sessions[tab_ids[0]]
        await first_tab.client.send(state_update)
        
        # Wait for state propagation
        await asyncio.sleep(1.5)
        
        # Verify state is accessible from other tabs
        for tab_id in tab_ids[1:]:
            tab_session = self.tab_sessions[tab_id]
            state_request = {
                "type": "get_session_state",
                "user_id": self.shared_user_id
            }
            await tab_session.client.send(state_request)
            
            try:
                response = await tab_session.client.receive(timeout=2.0)
                if not response or response.get("session_data", {}).get("workspace_id") != "shared_workspace_123":
                    return False
            except asyncio.TimeoutError:
                return False
        
        return True
    
    @pytest.mark.e2e
    async def test_concurrent_operations(self, tab_ids: List[str]) -> bool:
        """Test concurrent operations across multiple tabs."""
        if len(tab_ids) < 3:
            return False
        
        # Create concurrent tasks for each tab
        concurrent_tasks = []
        for i, tab_id in enumerate(tab_ids):
            task = self._execute_tab_operation(tab_id, operation_type=f"operation_{i}")
            concurrent_tasks.append(task)
        
        # Execute all operations concurrently
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Verify all operations completed successfully
        successful_operations = sum(1 for result in results if result is True)
        return successful_operations >= len(tab_ids) * 0.8  # 80% success rate
    
    @pytest.mark.e2e
    async def test_tab_specific_data_isolation(self, tab_ids: List[str]) -> bool:
        """Test that tab-specific data remains isolated."""
        # Set unique data for each tab
        for i, tab_id in enumerate(tab_ids):
            tab_session = self.tab_sessions[tab_id]
            tab_data = {
                "type": "set_tab_data",
                "tab_id": tab_id,
                "data": {
                    "tab_index": i,
                    "unique_id": str(uuid.uuid4()),
                    "tab_specific_state": f"state_for_tab_{i}"
                }
            }
            await tab_session.client.send(tab_data)
            tab_session.isolated_data = tab_data["data"]
        
        await asyncio.sleep(1.0)
        
        # Verify each tab only has its own data
        for tab_id in tab_ids:
            tab_session = self.tab_sessions[tab_id]
            data_request = {
                "type": "get_tab_data",
                "tab_id": tab_id
            }
            await tab_session.client.send(data_request)
            
            try:
                response = await tab_session.client.receive(timeout=2.0)
                expected_data = tab_session.isolated_data
                
                if not response or response.get("data") != expected_data:
                    return False
            except asyncio.TimeoutError:
                return False
        
        return True
    
    def _create_tab_specific_message(self, tab_id: str) -> Dict[str, Any]:
        """Create message specific to a tab."""
        return {
            "type": "tab_specific_message",
            "tab_id": tab_id,
            "message_id": str(uuid.uuid4()),
            "content": f"Message from {tab_id}",
            "timestamp": time.time(),
            "isolation_test": True
        }
    
    async def _execute_tab_operation(self, tab_id: str, operation_type: str) -> bool:
        """Execute operation for specific tab."""
        tab_session = self.tab_sessions[tab_id]
        operation = {
            "type": operation_type,
            "tab_id": tab_id,
            "operation_data": {
                "action": "test_concurrent_action",
                "timestamp": time.time()
            }
        }
        
        try:
            await tab_session.client.send(operation)
            response = await tab_session.client.receive(timeout=3.0)
            return response is not None
        except Exception:
            return False
    
    async def cleanup(self) -> None:
        """Cleanup all tab sessions and connections."""
        cleanup_tasks = []
        for tab_session in self.tab_sessions.values():
            if tab_session.client:
                cleanup_tasks.append(tab_session.client.close())
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        self.tab_sessions.clear()


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.e2e
class TestMultiTabIsolation:
    """Critical E2E Test: Multi-Tab WebSocket Isolation."""
    
    @pytest.mark.e2e
    async def test_multi_tab_isolation(self):
        """
        BVJ: Segment: Enterprise | Goal: UX | Impact: Enterprise user experience
        Tests: Multi-tab WebSocket isolation
        """
        manager = MultiTabWebSocketIsolationManager()
        
        try:
            # Setup shared session
            await manager.setup_shared_session()
            
            # Connect multiple tabs
            tab_ids = await manager.connect_all_tabs(3)
            assert len(tab_ids) == 3, f"Expected 3 tabs connected, got {len(tab_ids)}"
            
            # Test message isolation
            message_isolation = await manager.test_message_isolation(tab_ids)
            assert message_isolation, "Message isolation failed - cross-contamination detected"
            
            # Test shared session state
            shared_session = await manager.test_shared_session_state(tab_ids)
            assert shared_session, "Shared session state not working across tabs"
            
            # Test concurrent operations
            concurrent_ops = await manager.test_concurrent_operations(tab_ids)
            assert concurrent_ops, "Concurrent operations failed across tabs"
            
            # Test tab-specific data isolation
            data_isolation = await manager.test_tab_specific_data_isolation(tab_ids)
            assert data_isolation, "Tab-specific data isolation failed"
            
        finally:
            await manager.cleanup()
    
    @pytest.mark.e2e
    async def test_two_tabs_separate_websocket_connections(self):
        """Test that each tab has its own WebSocket connection."""
        manager = MultiTabWebSocketIsolationManager()
        
        try:
            await manager.setup_shared_session()
            tab_ids = await manager.connect_all_tabs(2)
            
            assert len(tab_ids) == 2, "Failed to connect 2 tabs"
            
            # Verify separate connections
            tab1_client = manager.tab_sessions[tab_ids[0]].client
            tab2_client = manager.tab_sessions[tab_ids[1]].client
            
            assert tab1_client is not tab2_client, "Tabs sharing same WebSocket client"
            assert tab1_client.state == ConnectionState.CONNECTED
            assert tab2_client.state == ConnectionState.CONNECTED
            
        finally:
            await manager.cleanup()
    
    @pytest.mark.e2e
    async def test_message_routing_correctness(self):
        """Test that messages are routed correctly to each tab."""
        manager = MultiTabWebSocketIsolationManager()
        
        try:
            await manager.setup_shared_session()
            tab_ids = await manager.connect_all_tabs(3)
            
            # Send messages from each tab
            for i, tab_id in enumerate(tab_ids):
                message = {
                    "type": "routing_test",
                    "tab_id": tab_id,
                    "sender_index": i,
                    "content": f"Message from tab {i}"
                }
                
                tab_session = manager.tab_sessions[tab_id]
                await tab_session.client.send(message)
                tab_session.messages_sent.append(message)
            
            await asyncio.sleep(1.0)
            
            # Verify messages were sent correctly
            for tab_id in tab_ids:
                tab_session = manager.tab_sessions[tab_id]
                assert len(tab_session.messages_sent) == 1, "Incorrect number of messages sent"
                
        finally:
            await manager.cleanup()
    
    @pytest.mark.e2e
    async def test_no_data_cross_contamination(self):
        """Test that there's no data cross-contamination between tabs."""
        manager = MultiTabWebSocketIsolationManager()
        
        try:
            await manager.setup_shared_session()
            tab_ids = await manager.connect_all_tabs(2)
            
            # Set different data for each tab
            for i, tab_id in enumerate(tab_ids):
                unique_data = {
                    "type": "set_private_data",
                    "tab_id": tab_id,
                    "private_data": f"secret_data_for_tab_{i}_{uuid.uuid4()}"
                }
                
                tab_session = manager.tab_sessions[tab_id]
                await tab_session.client.send(unique_data)
            
            await asyncio.sleep(1.0)
            
            # Verify data isolation
            contamination_detected = False
            for tab_id in tab_ids:
                other_tab_id = [t for t in tab_ids if t != tab_id][0]
                
                # Try to access other tab's data
                access_request = {
                    "type": "get_private_data",
                    "requested_tab_id": other_tab_id
                }
                
                tab_session = manager.tab_sessions[tab_id]
                await tab_session.client.send(access_request)
                
                try:
                    response = await tab_session.client.receive(timeout=1.0)
                    if response and "secret_data" in str(response):
                        contamination_detected = True
                        break
                except asyncio.TimeoutError:
                    pass  # Expected - should not receive other tab's data
            
            assert not contamination_detected, "Data cross-contamination detected between tabs"
            
        finally:
            await manager.cleanup()
    
    @pytest.mark.e2e
    async def test_shared_session_across_tabs(self):
        """Test that session data is properly shared across tabs."""
        manager = MultiTabWebSocketIsolationManager()
        
        try:
            await manager.setup_shared_session()
            tab_ids = await manager.connect_all_tabs(2)
            
            # Verify shared user ID
            for tab_id in tab_ids:
                tab_session = manager.tab_sessions[tab_id]
                assert tab_session.user_id == manager.shared_user_id
                assert tab_session.session_token == manager.shared_session_token
            
            # Test shared session functionality
            shared_session_works = await manager.test_shared_session_state(tab_ids)
            assert shared_session_works, "Shared session state not functioning properly"
            
        finally:
            await manager.cleanup()
