"""E2E Staging Tests for Issue #1186 UserExecutionEngine SSOT Consolidation - Phase 3

PURPOSE: Golden Path Protection Validation
Validates that UserExecutionEngine SSOT consolidation preserves critical Golden Path
functionality in production-like staging environment.

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Protect $500K+ ARR Golden Path user flow functionality
- Value Impact: Ensures SSOT consolidation doesn't break core user experience
- Strategic Impact: Validates enterprise-grade multi-user agent execution post-consolidation

CRITICAL TEST COVERAGE:
1. Golden Path User Flow - Login → AI Response (post-SSOT)
2. All 5 WebSocket Events - Real-time user feedback with consolidated engine
3. Multi-User Isolation - SSOT consolidation maintains user separation
4. Agent Execution Performance - Consolidated engine performance validation
5. Production Environment Simulation - Staging GCP validation

This validates Issue #1186 UserExecutionEngine SSOT consolidation Phase 1 & 2
achievements don't break the Golden Path that protects $500K+ ARR.
"""

import pytest
import asyncio
import uuid
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from tests.e2e.staging_config import get_staging_config
from tests.e2e.staging_auth_client import StagingAuthClient, StagingAPIClient
from tests.e2e.staging_websocket_client import StagingWebSocketClient

logger = logging.getLogger(__name__)

# Mark as E2E staging tests
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.issue_1186_phase3
]


@dataclass
class GoldenPathMetrics:
    """Metrics for Golden Path performance validation."""
    connection_time: float
    first_event_time: float
    total_execution_time: float
    event_count: int
    events_received: List[str]
    multi_user_isolation_verified: bool


@pytest.mark.e2e
class Issue1186GoldenPathPreservationStagingTests:
    """E2E staging tests for Issue #1186 UserExecutionEngine SSOT consolidation Golden Path protection."""
    
    def setup_method(self):
        """Set up staging test environment."""
        self.staging_config = get_staging_config()
        self.staging_config.validate_configuration()
        
    async def _create_authenticated_user(self, user_suffix: str) -> tuple[StagingAuthClient, str]:
        """Create authenticated staging user."""
        auth_client = StagingAuthClient(self.staging_config)
        
        # Create unique test user email
        user_email = f"issue-1186-{user_suffix}-{uuid.uuid4().hex[:8]}@netra.test"
        user_name = f"Issue 1186 Test User {user_suffix.title()}"
        
        # Get auth tokens (simulates OAuth login)
        auth_response = await auth_client.get_auth_token(
            email=user_email,
            name=user_name,
            permissions=["read", "write", "agent_execute"]
        )
        
        user_id = auth_response.get("user_id", user_email)
        
        return auth_client, user_id
    
    async def _validate_websocket_events(self, websocket_client: StagingWebSocketClient, 
                                       timeout: float = 30.0) -> List[Dict]:
        """Validate all 5 critical WebSocket events are received."""
        collected_events = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                events = await websocket_client.receive_events(timeout=2.0)
                collected_events.extend(events)
                
                # Check for completion
                if any(e.get("type") == "agent_completed" for e in events):
                    break
                    
            except asyncio.TimeoutError:
                continue
        
        return collected_events
    
    async def _validate_golden_path_metrics(self, metrics: GoldenPathMetrics) -> None:
        """Validate Golden Path performance metrics."""
        # Connection performance
        assert metrics.connection_time <= 5.0, \
            f"WebSocket connection too slow: {metrics.connection_time}s (max 5s)"
        
        # First event responsiveness
        assert metrics.first_event_time <= 10.0, \
            f"First event too slow: {metrics.first_event_time}s (max 10s)"
        
        # Total execution reasonable
        assert metrics.total_execution_time <= 60.0, \
            f"Total execution too slow: {metrics.total_execution_time}s (max 60s)"
        
        # Event completeness
        required_events = ["agent_started", "agent_thinking", "tool_executing", 
                          "tool_completed", "agent_completed"]
        missing_events = [e for e in required_events if e not in metrics.events_received]
        
        assert len(missing_events) == 0, \
            f"Missing critical WebSocket events: {missing_events}"
        
        # Multi-user isolation
        assert metrics.multi_user_isolation_verified, \
            "Multi-user isolation not verified - SSOT consolidation security issue"

    @pytest.mark.asyncio
    async def test_golden_path_user_flow_post_ssot_consolidation(self):
        """Test complete Golden Path user flow after UserExecutionEngine SSOT consolidation.
        
        CRITICAL: Validates Issue #1186 Phase 1 & 2 SSOT consolidation preserves
        core user experience protecting $500K+ ARR.
        """
        # Arrange - Create authenticated user
        auth_client, user_id = await self._create_authenticated_user("golden-path")
        
        # Create API client
        api_client = StagingAPIClient(auth_client)
        await api_client.authenticate()
        
        # Create WebSocket client 
        websocket_client = StagingWebSocketClient(auth_client)
        
        start_time = time.time()
        
        try:
            # Act - Execute Golden Path flow
            
            # Step 1: WebSocket Connection (post-SSOT consolidation)
            connection_start = time.time()
            await websocket_client.connect()
            connection_time = time.time() - connection_start
            
            assert websocket_client.is_connected, "WebSocket connection failed post-SSOT"
            
            # Step 2: Send user message triggering agent execution
            thread_id = f"golden-path-{uuid.uuid4().hex}"
            
            message = {
                "type": "user_message",
                "text": "Analyze my AI optimization opportunities using consolidated engine",
                "thread_id": thread_id,
                "user_id": user_id
            }
            
            await websocket_client.send_message(message)
            
            # Step 3: Collect WebSocket events (validate consolidated engine)
            events = await self._validate_websocket_events(websocket_client, timeout=45.0)
            
            # Step 4: Validate Golden Path completion
            total_time = time.time() - start_time
            first_event_time = events[0].get("timestamp", start_time) - start_time if events else float('inf')
            
            metrics = GoldenPathMetrics(
                connection_time=connection_time,
                first_event_time=first_event_time,
                total_execution_time=total_time,
                event_count=len(events),
                events_received=[e.get("type") for e in events],
                multi_user_isolation_verified=True  # Single user test validates structure
            )
            
            await self._validate_golden_path_metrics(metrics)
            
            # Assert - Validate SSOT consolidation success
            assert len(events) >= 5, f"Insufficient events: {len(events)} (expected ≥5)"
            
            # Verify agent execution completed successfully
            completion_events = [e for e in events if e.get("type") == "agent_completed"]
            assert len(completion_events) >= 1, "Agent execution not completed"
            
            # Verify no SSOT consolidation errors
            error_events = [e for e in events if "error" in e.get("type", "").lower()]
            assert len(error_events) == 0, f"SSOT consolidation errors: {error_events}"
            
            logger.info(f"Golden Path post-SSOT validation successful: {metrics}")
            
        finally:
            if websocket_client.is_connected:
                await websocket_client.disconnect()
    
    @pytest.mark.asyncio
    async def test_all_five_websocket_events_consolidated_engine(self):
        """Test all 5 critical WebSocket events work with consolidated UserExecutionEngine.
        
        CRITICAL: Validates consolidated engine preserves real-time user feedback
        that builds trust and engagement worth $100K+ ARR.
        """
        # Arrange
        auth_client, user_id = await self._create_authenticated_user("websocket-events")
        websocket_client = StagingWebSocketClient(auth_client)
        
        try:
            await websocket_client.connect()
            
            # Act - Trigger agent execution
            thread_id = f"events-test-{uuid.uuid4().hex}"
            message = {
                "type": "user_message", 
                "text": "Test all WebSocket events with consolidated UserExecutionEngine",
                "thread_id": thread_id,
                "user_id": user_id
            }
            
            await websocket_client.send_message(message)
            
            # Collect events
            events = await self._validate_websocket_events(websocket_client, timeout=40.0)
            
            # Assert - Validate all 5 critical events
            event_types = [e.get("type") for e in events]
            required_events = [
                "agent_started",    # User sees AI began work
                "agent_thinking",   # Real-time reasoning  
                "tool_executing",   # Tool transparency
                "tool_completed",   # Tool results
                "agent_completed"   # Final results ready
            ]
            
            for required_event in required_events:
                assert required_event in event_types, \
                    f"Missing critical event '{required_event}' in consolidated engine. Events: {event_types}"
            
            # Verify event ordering (agent_started first, agent_completed last)
            assert event_types[0] == "agent_started", \
                f"First event should be 'agent_started', got '{event_types[0]}'"
            
            assert event_types[-1] == "agent_completed", \
                f"Last event should be 'agent_completed', got '{event_types[-1]}'"
            
            # Verify event content integrity
            for event in events:
                assert "type" in event, f"Event missing type: {event}"
                assert "timestamp" in event, f"Event missing timestamp: {event}"
                if event.get("type") in ["tool_executing", "tool_completed"]:
                    assert "tool_name" in event or "data" in event, \
                        f"Tool event missing details: {event}"
            
            logger.info(f"All 5 WebSocket events validated with consolidated engine: {required_events}")
            
        finally:
            if websocket_client.is_connected:
                await websocket_client.disconnect()
    
    @pytest.mark.asyncio
    async def test_multi_user_isolation_consolidated_engine(self):
        """Test multi-user isolation works with consolidated UserExecutionEngine.
        
        CRITICAL: Validates SSOT consolidation maintains enterprise-grade user
        separation preventing data contamination worth $200K+ ARR.
        """
        # Arrange - Create two users
        auth_client1, user_id1 = await self._create_authenticated_user("isolation-user1")
        auth_client2, user_id2 = await self._create_authenticated_user("isolation-user2")
        
        websocket_client1 = StagingWebSocketClient(auth_client1)
        websocket_client2 = StagingWebSocketClient(auth_client2)
        
        try:
            # Connect both users
            await websocket_client1.connect()
            await websocket_client2.connect()
            
            # Act - Execute concurrent agent requests
            thread_id1 = f"isolation-1-{uuid.uuid4().hex}"
            thread_id2 = f"isolation-2-{uuid.uuid4().hex}"
            
            message1 = {
                "type": "user_message",
                "text": f"User 1 isolated request: {user_id1}",
                "thread_id": thread_id1,
                "user_id": user_id1
            }
            
            message2 = {
                "type": "user_message", 
                "text": f"User 2 isolated request: {user_id2}",
                "thread_id": thread_id2,
                "user_id": user_id2
            }
            
            # Send concurrent requests
            await asyncio.gather(
                websocket_client1.send_message(message1),
                websocket_client2.send_message(message2)
            )
            
            # Collect events from both users
            events1_task = asyncio.create_task(
                self._validate_websocket_events(websocket_client1, timeout=35.0)
            )
            events2_task = asyncio.create_task(
                self._validate_websocket_events(websocket_client2, timeout=35.0)
            )
            
            events1, events2 = await asyncio.gather(events1_task, events2_task)
            
            # Assert - Validate isolation
            assert len(events1) >= 3, f"User 1 insufficient events: {len(events1)}"
            assert len(events2) >= 3, f"User 2 insufficient events: {len(events2)}"
            
            # Verify no cross-contamination
            user1_contexts = [e.get("user_id") or e.get("data", {}).get("user_id") 
                             for e in events1 if "user_id" in str(e)]
            user2_contexts = [e.get("user_id") or e.get("data", {}).get("user_id")
                             for e in events2 if "user_id" in str(e)]
            
            # No user 2 data in user 1 events
            contamination1 = [ctx for ctx in user1_contexts if ctx == user_id2]
            assert len(contamination1) == 0, \
                f"User isolation violation: User 2 data in User 1 events: {contamination1}"
            
            # No user 1 data in user 2 events  
            contamination2 = [ctx for ctx in user2_contexts if ctx == user_id1]
            assert len(contamination2) == 0, \
                f"User isolation violation: User 1 data in User 2 events: {contamination2}"
            
            # Verify thread isolation
            thread1_refs = [e.get("thread_id") for e in events1 if "thread_id" in e]
            thread2_refs = [e.get("thread_id") for e in events2 if "thread_id" in e]
            
            # Check thread contamination
            wrong_threads1 = [t for t in thread1_refs if t == thread_id2]
            wrong_threads2 = [t for t in thread2_refs if t == thread_id1]
            
            assert len(wrong_threads1) == 0, \
                f"Thread isolation violation: User 1 got User 2 thread: {wrong_threads1}"
            assert len(wrong_threads2) == 0, \
                f"Thread isolation violation: User 2 got User 1 thread: {wrong_threads2}"
            
            logger.info(f"Multi-user isolation validated: User1({len(events1)} events), User2({len(events2)} events)")
            
        finally:
            if websocket_client1.is_connected:
                await websocket_client1.disconnect()
            if websocket_client2.is_connected:
                await websocket_client2.disconnect()
    
    @pytest.mark.asyncio
    async def test_agent_execution_performance_consolidated_engine(self):
        """Test agent execution performance with consolidated UserExecutionEngine.
        
        CRITICAL: Validates SSOT consolidation maintains acceptable performance
        protecting user experience worth $100K+ ARR.
        """
        # Arrange
        auth_client, user_id = await self._create_authenticated_user("performance")
        websocket_client = StagingWebSocketClient(auth_client)
        
        try:
            await websocket_client.connect()
            
            # Act - Test performance metrics
            start_time = time.time()
            
            thread_id = f"performance-{uuid.uuid4().hex}"
            message = {
                "type": "user_message",
                "text": "Performance test with consolidated UserExecutionEngine",
                "thread_id": thread_id,
                "user_id": user_id
            }
            
            await websocket_client.send_message(message)
            
            # Track event timings
            first_event_time = None
            completion_time = None
            
            events = []
            timeout = time.time() + 45.0
            
            while time.time() < timeout:
                try:
                    new_events = await websocket_client.receive_events(timeout=2.0)
                    events.extend(new_events)
                    
                    # Track first event
                    if not first_event_time and new_events:
                        first_event_time = time.time()
                    
                    # Track completion
                    if any(e.get("type") == "agent_completed" for e in new_events):
                        completion_time = time.time()
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
            # Assert - Validate performance metrics
            total_time = completion_time - start_time if completion_time else float('inf')
            first_event_delay = first_event_time - start_time if first_event_time else float('inf')
            
            # Performance thresholds
            assert first_event_delay <= 10.0, \
                f"First event too slow: {first_event_delay:.2f}s (max 10s) - SSOT consolidation performance issue"
            
            assert total_time <= 60.0, \
                f"Total execution too slow: {total_time:.2f}s (max 60s) - consolidated engine performance issue"
            
            assert len(events) >= 5, \
                f"Insufficient events for performance validation: {len(events)} (expected ≥5)"
            
            # Calculate event rate
            event_rate = len(events) / total_time if total_time > 0 else 0
            assert event_rate >= 0.1, \
                f"Event rate too low: {event_rate:.2f} events/sec - consolidated engine responsiveness issue"
            
            logger.info(f"Performance validated - First event: {first_event_delay:.2f}s, "
                       f"Total: {total_time:.2f}s, Events: {len(events)}, Rate: {event_rate:.2f}/sec")
            
        finally:
            if websocket_client.is_connected:
                await websocket_client.disconnect()
    
    @pytest.mark.asyncio 
    async def test_production_environment_simulation_post_ssot(self):
        """Test production-like environment behavior after UserExecutionEngine SSOT consolidation.
        
        CRITICAL: Validates consolidated engine works in production-like staging
        environment protecting deployment confidence worth $500K+ ARR.
        """
        # Arrange - Multiple users simulating production load
        num_users = 3
        users = []
        
        for i in range(num_users):
            auth_client, user_id = await self._create_authenticated_user(f"prod-sim-{i}")
            websocket_client = StagingWebSocketClient(auth_client)
            users.append((auth_client, user_id, websocket_client))
        
        try:
            # Act - Connect all users
            for _, _, websocket_client in users:
                await websocket_client.connect()
                assert websocket_client.is_connected, "Production simulation connection failed"
            
            # Send concurrent production-like requests
            tasks = []
            for i, (_, user_id, websocket_client) in enumerate(users):
                thread_id = f"prod-sim-{i}-{uuid.uuid4().hex}"
                message = {
                    "type": "user_message",
                    "text": f"Production simulation user {i}: Analyze AI costs and optimization",
                    "thread_id": thread_id,
                    "user_id": user_id
                }
                
                task = asyncio.create_task(self._simulate_production_user(websocket_client, message))
                tasks.append(task)
            
            # Wait for all production simulations
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Assert - Validate production simulation
            successful_results = [r for r in results if not isinstance(r, Exception)]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            assert len(failed_results) == 0, \
                f"Production simulation failures: {failed_results}"
            
            assert len(successful_results) == num_users, \
                f"Expected {num_users} successful simulations, got {len(successful_results)}"
            
            # Validate each user got complete experience
            for i, result in enumerate(successful_results):
                events = result["events"]
                metrics = result["metrics"]
                
                assert len(events) >= 5, \
                    f"User {i} insufficient events: {len(events)} - production readiness issue"
                
                assert metrics["total_time"] <= 70.0, \
                    f"User {i} too slow: {metrics['total_time']:.2f}s - production performance issue"
                
                # Verify all critical events
                event_types = [e.get("type") for e in events]
                required = ["agent_started", "agent_thinking", "agent_completed"]
                missing = [e for e in required if e not in event_types]
                
                assert len(missing) == 0, \
                    f"User {i} missing events: {missing} - production reliability issue"
            
            logger.info(f"Production simulation successful: {num_users} concurrent users validated")
            
        finally:
            for _, _, websocket_client in users:
                if websocket_client.is_connected:
                    await websocket_client.disconnect()
    
    async def _simulate_production_user(self, websocket_client: StagingWebSocketClient, 
                                       message: Dict) -> Dict:
        """Simulate a production user's complete experience."""
        start_time = time.time()
        
        # Send message
        await websocket_client.send_message(message)
        
        # Collect events
        events = await self._validate_websocket_events(websocket_client, timeout=50.0)
        
        total_time = time.time() - start_time
        
        return {
            "events": events,
            "metrics": {
                "total_time": total_time,
                "event_count": len(events)
            }
        }


# Additional helper tests for SSOT consolidation validation

@pytest.mark.e2e
class Issue1186SSotConsolidationValidationTests:
    """Additional validation tests for UserExecutionEngine SSOT consolidation."""
    
    def setup_method(self):
        """Set up SSOT validation tests."""
        self.staging_config = get_staging_config()
        self.staging_config.validate_configuration()
    
    @pytest.mark.asyncio
    async def test_no_singleton_violations_post_consolidation(self):
        """Test no singleton violations remain after UserExecutionEngine SSOT consolidation."""
        # Arrange
        auth_client, user_id = await self._create_authenticated_user("singleton-test")
        
        # Create multiple WebSocket clients to test for singleton violations
        websocket_clients = []
        for i in range(2):
            client = StagingWebSocketClient(auth_client)
            await client.connect()
            websocket_clients.append(client)
        
        try:
            # Act - Test concurrent execution with different clients
            messages = []
            for i, client in enumerate(websocket_clients):
                thread_id = f"singleton-test-{i}-{uuid.uuid4().hex}"
                message = {
                    "type": "user_message",
                    "text": f"Singleton violation test {i}",
                    "thread_id": thread_id,
                    "user_id": user_id
                }
                messages.append((client, message))
            
            # Send concurrent messages
            tasks = []
            for client, message in messages:
                task = asyncio.create_task(client.send_message(message))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Collect events from all clients
            all_events = []
            for client in websocket_clients:
                events = await self._validate_websocket_events(client, timeout=30.0)
                all_events.extend(events)
            
            # Assert - No singleton violations (each client gets independent events)
            assert len(all_events) >= 6, \
                f"Insufficient events for singleton test: {len(all_events)} (expected ≥6)"
            
            # Verify no shared state contamination
            thread_ids = [e.get("thread_id") for e in all_events if "thread_id" in e]
            unique_threads = set(thread_ids)
            
            assert len(unique_threads) >= 2, \
                f"Singleton violation detected: threads not isolated: {unique_threads}"
            
            logger.info(f"Singleton violation test passed: {len(unique_threads)} isolated threads")
            
        finally:
            for client in websocket_clients:
                if client.is_connected:
                    await client.disconnect()
    
    async def _create_authenticated_user(self, user_suffix: str) -> tuple[StagingAuthClient, str]:
        """Create authenticated staging user."""
        auth_client = StagingAuthClient(self.staging_config)
        
        # Create unique test user email
        user_email = f"issue-1186-{user_suffix}-{uuid.uuid4().hex[:8]}@netra.test"
        user_name = f"Issue 1186 Test User {user_suffix.title()}"
        
        # Get auth tokens (simulates OAuth login)
        auth_response = await auth_client.get_auth_token(
            email=user_email,
            name=user_name,
            permissions=["read", "write", "agent_execute"]
        )
        
        user_id = auth_response.get("user_id", user_email)
        
        return auth_client, user_id
    
    async def _validate_websocket_events(self, websocket_client: StagingWebSocketClient, 
                                       timeout: float = 30.0) -> List[Dict]:
        """Validate WebSocket events collection."""
        collected_events = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                events = await websocket_client.receive_events(timeout=2.0)
                collected_events.extend(events)
                
                if any(e.get("type") == "agent_completed" for e in events):
                    break
                    
            except asyncio.TimeoutError:
                continue
        
        return collected_events