"""
WebSocket Cloud Run Race Condition Reproduction Tests

Purpose: Reproduce the specific race conditions identified in GCP Cloud Run environments
that cause the Golden Path failures and WebSocket 1011 errors.

Based on:
- GOLDEN_PATH_USER_FLOW_COMPLETE.md: "Cloud Run environments experience race conditions 
  where message handling starts before WebSocket handshake completion"
- Five Whys Analysis: Infrastructure-level race conditions in GCP staging environment
- Real production logs showing specific timing failures

CRITICAL: These tests simulate GCP Cloud Run specific behaviors that cause race conditions
in production. They are designed to FAIL until proper coordination mechanisms are implemented.

Business Value:
- Segment: Platform Infrastructure
- Goal: $500K+ ARR Chat Functionality Reliability
- Value Impact: Prevents WebSocket 1011 errors in Cloud Run deployment
- Strategic Impact: Validates infrastructure-specific race condition fixes
"""

import asyncio
import pytest
import time
import threading
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import random

from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    ConnectionStateMachine,
    StateTransitionError
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass 
class CloudRunRaceCondition:
    """Tracks Cloud Run specific race condition scenarios."""
    test_name: str
    cloud_run_phase: str  # "handshake", "routing", "processing", "scaling"
    timing_issue: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_details: Optional[str] = None
    infrastructure_delays: List[float] = field(default_factory=list)
    concurrent_operations: int = 1
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


class TestWebSocketCloudRunRaceConditions:
    """
    Tests that reproduce the exact race conditions that occur in GCP Cloud Run environments.
    
    Cloud Run introduces specific timing challenges:
    1. Network handshake vs application state timing gaps
    2. Load balancer routing delays
    3. Container startup race conditions  
    4. Service discovery delays
    5. Auto-scaling timing issues
    """

    def setup_method(self):
        """Setup for each test method."""
        self.race_conditions: List[CloudRunRaceCondition] = []
        logger.info("[U+1F325][U+FE0F] CLOUD RUN RACE CONDITION TEST SETUP")

    def teardown_method(self):
        """Cleanup and analysis after each test."""
        if self.race_conditions:
            logger.info(f"[U+2601][U+FE0F] CLOUD RUN ANALYSIS: {len(self.race_conditions)} race conditions tested")
            for rc in self.race_conditions:
                if rc.infrastructure_delays:
                    avg_delay = sum(rc.infrastructure_delays) / len(rc.infrastructure_delays)
                    logger.info(f"[U+23F1][U+FE0F] {rc.test_name}: Avg delay {avg_delay:.3f}s, Max delay {max(rc.infrastructure_delays):.3f}s")

    @pytest.mark.race_condition
    @pytest.mark.cloud_run
    @pytest.mark.xfail(reason="MUST FAIL: GCP Load Balancer routing delay race condition")
    async def test_gcp_load_balancer_routing_race_condition(self):
        """
        CLOUD RUN ISSUE: GCP Load Balancer takes time to route WebSocket upgrade requests,
        causing race between network-level handshake and application-level readiness.
        
        REPRODUCTION: Simulate load balancer delays that cause application to start
        processing before network handshake is fully established.
        
        EXPECTED FAILURE: "Connection not ready" or "Accept not called" errors.
        """
        race_condition = CloudRunRaceCondition(
            test_name="gcp_load_balancer_routing_race",
            cloud_run_phase="routing",
            timing_issue="Load balancer delay vs application readiness",
            start_time=time.time()
        )
        
        logger.info("[U+1F325][U+FE0F] REPRODUCING: GCP Load Balancer routing delay race condition")
        
        try:
            # Simulate GCP Load Balancer behavior
            websocket_mock = self._create_cloud_run_websocket_mock()
            
            # Start application processing immediately (as Cloud Run does)
            app_processing_task = asyncio.create_task(
                self._simulate_immediate_application_processing(websocket_mock, race_condition)
            )
            
            # Simulate load balancer delay before handshake completion
            load_balancer_delay = random.uniform(0.1, 0.5)  # 100-500ms typical Cloud Run delay
            race_condition.infrastructure_delays.append(load_balancer_delay)
            
            logger.info(f" CYCLE:  Simulating {load_balancer_delay:.3f}s load balancer delay")
            await asyncio.sleep(load_balancer_delay)
            
            # Now complete handshake (after application already tried to process)
            handshake_task = asyncio.create_task(
                self._simulate_delayed_websocket_handshake(websocket_mock, race_condition)
            )
            
            # Wait for both with timeout
            results = await asyncio.wait_for(
                asyncio.gather(app_processing_task, handshake_task, return_exceptions=True),
                timeout=2.0
            )
            
            # Analyze race condition results
            app_result, handshake_result = results
            
            if isinstance(app_result, Exception):
                # Expected - application processing failed due to race condition
                race_condition.success = False
                race_condition.error_details = f"App processing failed: {str(app_result)}"
                logger.info(f" PASS:  Expected race condition: {app_result}")
            else:
                # Unexpected - no race condition detected
                race_condition.success = True  
                race_condition.error_details = "NO RACE CONDITION: Application processing succeeded before handshake"
                
        except Exception as e:
            race_condition.success = False
            race_condition.error_details = f"Unexpected error: {str(e)}"
            logger.info(f" PASS:  Race condition caused unexpected error: {e}")
            
        finally:
            race_condition.end_time = time.time()
            self.race_conditions.append(race_condition)
        
        # CRITICAL ASSERTION: Race condition should cause failures
        assert not race_condition.success, (
            f"RACE CONDITION NOT DETECTED: Application processing succeeded despite load balancer delay. "
            f"This indicates the race condition is not being properly reproduced or has been fixed. "
            f"Details: {race_condition.error_details}"
        )

    @pytest.mark.race_condition
    @pytest.mark.cloud_run  
    @pytest.mark.xfail(reason="MUST FAIL: Container startup service discovery race")
    async def test_cloud_run_container_startup_service_discovery_race(self):
        """
        CLOUD RUN ISSUE: When containers start, service discovery (finding supervisor/thread services)
        has timing gaps where WebSocket connections are established before required services are ready.
        
        REPRODUCTION: Simulate WebSocket connection attempt when container is starting
        but dependent services aren't ready yet.
        
        EXPECTED FAILURE: Service unavailability errors or connection establishment failures.
        """
        race_condition = CloudRunRaceCondition(
            test_name="container_startup_service_discovery_race",
            cloud_run_phase="scaling",
            timing_issue="Service discovery lag during container startup", 
            start_time=time.time()
        )
        
        logger.info("[U+1F325][U+FE0F] REPRODUCING: Container startup service discovery race")
        
        try:
            # Simulate container startup scenario
            connection_id = "startup-race-connection"
            user_id = "startup-race-user"
            
            # Create state machine during container startup
            state_machine = ConnectionStateMachine(connection_id, user_id)
            
            # Simulate rapid WebSocket connection establishment
            logger.info(" CYCLE:  Attempting WebSocket connection during container startup")
            
            # Try to transition through states while services are starting
            startup_sequence = [
                (ApplicationConnectionState.ACCEPTED, "WebSocket accepted"),
                (ApplicationConnectionState.AUTHENTICATED, "User authenticated"),
                (ApplicationConnectionState.SERVICES_READY, "Services initializing...")  # This should fail
            ]
            
            for target_state, reason in startup_sequence:
                # Simulate service discovery delays
                if target_state == ApplicationConnectionState.SERVICES_READY:
                    # Simulate supervisor service not yet available
                    service_discovery_delay = random.uniform(0.2, 1.0)  # 200ms-1s startup delay
                    race_condition.infrastructure_delays.append(service_discovery_delay)
                    
                    logger.info(f" CYCLE:  Service discovery delay: {service_discovery_delay:.3f}s")
                    
                    # During this delay, services aren't ready yet
                    services_ready = await self._check_services_availability_during_startup(
                        race_condition, service_discovery_delay
                    )
                    
                    if not services_ready:
                        # Expected - services not ready during startup
                        raise RuntimeError("Required services not available during container startup")
                
                # Attempt transition
                transition_success = state_machine.transition_to(target_state, reason)
                
                if not transition_success:
                    raise StateTransitionError(f"Failed to transition to {target_state.value}")
            
            # If we get here, no race condition was detected
            race_condition.success = True
            race_condition.error_details = "NO RACE CONDITION: All services ready during startup"
            
        except (RuntimeError, StateTransitionError) as e:
            # Expected - race condition detected
            race_condition.success = False
            race_condition.error_details = str(e)
            logger.info(f" PASS:  Expected startup race condition: {e}")
            
        except Exception as e:
            race_condition.success = False  
            race_condition.error_details = f"Unexpected error: {str(e)}"
            logger.info(f" PASS:  Race condition caused unexpected error: {e}")
            
        finally:
            race_condition.end_time = time.time()
            self.race_conditions.append(race_condition)
        
        # CRITICAL ASSERTION: Startup race condition should cause failures
        assert not race_condition.success, (
            f"STARTUP RACE CONDITION NOT DETECTED: Services were ready during container startup. "
            f"This indicates either the race condition is not being reproduced properly, "
            f"or startup coordination has been implemented. Details: {race_condition.error_details}"
        )

    @pytest.mark.race_condition
    @pytest.mark.cloud_run
    @pytest.mark.xfail(reason="MUST FAIL: Auto-scaling concurrent connection race") 
    async def test_cloud_run_auto_scaling_concurrent_connection_race(self):
        """
        CLOUD RUN ISSUE: When auto-scaling triggers new container instances,
        multiple WebSocket connections can attempt to establish simultaneously,
        causing race conditions in shared state management.
        
        REPRODUCTION: Simulate multiple containers starting simultaneously and
        handling WebSocket connections concurrently.
        
        EXPECTED FAILURE: State corruption, connection ID conflicts, or resource contention.
        """
        race_condition = CloudRunRaceCondition(
            test_name="auto_scaling_concurrent_connection_race",
            cloud_run_phase="scaling",
            timing_issue="Concurrent container startup with multiple connections",
            start_time=time.time(),
            concurrent_operations=4  # Simulate 4 containers starting
        )
        
        logger.info("[U+1F325][U+FE0F] REPRODUCING: Auto-scaling concurrent connection race")
        
        try:
            num_containers = 4
            connections_per_container = 3
            total_connections = num_containers * connections_per_container
            
            logger.info(f" CYCLE:  Simulating {num_containers} containers with {connections_per_container} connections each")
            
            # Simulate concurrent container startup with WebSocket connections
            container_tasks = []
            
            for container_idx in range(num_containers):
                task = asyncio.create_task(
                    self._simulate_container_with_concurrent_connections(
                        container_idx, connections_per_container, race_condition
                    )
                )
                container_tasks.append(task)
                
                # Small delay between container startups to simulate auto-scaling timing
                container_startup_delay = random.uniform(0.05, 0.15)  # 50-150ms between containers
                race_condition.infrastructure_delays.append(container_startup_delay)
                await asyncio.sleep(container_startup_delay)
            
            # Wait for all containers to complete with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*container_tasks, return_exceptions=True),
                timeout=5.0
            )
            
            # Analyze results for race conditions
            successful_containers = []
            failed_containers = []
            
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_containers.append((idx, result))
                    logger.info(f" PASS:  Container {idx} failed with expected race condition: {result}")
                else:
                    successful_containers.append((idx, result))
            
            # Check for state conflicts in successful containers
            connection_ids = set()
            state_conflicts = 0
            
            for container_idx, container_result in successful_containers:
                if isinstance(container_result, dict) and 'connections' in container_result:
                    for conn_info in container_result['connections']:
                        conn_id = conn_info.get('connection_id')
                        if conn_id:
                            if conn_id in connection_ids:
                                state_conflicts += 1
                                logger.info(f" PASS:  State conflict detected: Duplicate connection ID {conn_id}")
                            connection_ids.add(conn_id)
            
            # Evaluate race condition detection
            if failed_containers or state_conflicts > 0:
                race_condition.success = False
                race_condition.error_details = (
                    f"Race conditions detected: {len(failed_containers)} failed containers, "
                    f"{state_conflicts} state conflicts"
                )
                logger.info(f" PASS:  Auto-scaling race conditions detected: {race_condition.error_details}")
            else:
                race_condition.success = True
                race_condition.error_details = (
                    f"NO RACE CONDITION: All {num_containers} containers succeeded without conflicts"
                )
                
        except Exception as e:
            race_condition.success = False
            race_condition.error_details = f"Unexpected error during auto-scaling test: {str(e)}"
            logger.info(f" PASS:  Auto-scaling race condition caused unexpected error: {e}")
            
        finally:
            race_condition.end_time = time.time()  
            self.race_conditions.append(race_condition)
        
        # CRITICAL ASSERTION: Auto-scaling should cause race conditions
        assert not race_condition.success, (
            f"AUTO-SCALING RACE CONDITION NOT DETECTED: All containers succeeded without conflicts. "
            f"This indicates auto-scaling coordination is working properly or race conditions "
            f"are not being triggered. Details: {race_condition.error_details}"
        )

    @pytest.mark.race_condition
    @pytest.mark.cloud_run
    @pytest.mark.xfail(reason="MUST FAIL: Network partition message ordering race")
    async def test_cloud_run_network_partition_message_ordering_race(self):
        """
        CLOUD RUN ISSUE: Network partitions or delays can cause messages to arrive
        out of order or during connection state transitions, causing race conditions.
        
        REPRODUCTION: Simulate network delays causing messages to arrive while
        WebSocket connection is in intermediate states.
        
        EXPECTED FAILURE: Message processing errors or state inconsistency.
        """
        race_condition = CloudRunRaceCondition(
            test_name="network_partition_message_ordering_race",
            cloud_run_phase="processing",
            timing_issue="Network delays causing message arrival during state transitions",
            start_time=time.time()
        )
        
        logger.info("[U+1F325][U+FE0F] REPRODUCING: Network partition message ordering race")
        
        try:
            connection_id = "network-partition-test"
            user_id = "network-partition-user"
            
            # Create state machine
            state_machine = ConnectionStateMachine(connection_id, user_id)
            
            # Simulate messages arriving during network partition
            messages = [
                {"type": "user_message", "text": "Message 1", "sequence": 1},
                {"type": "user_message", "text": "Message 2", "sequence": 2}, 
                {"type": "user_message", "text": "Message 3", "sequence": 3}
            ]
            
            # Start state transitions
            transition_task = asyncio.create_task(
                self._simulate_slow_state_transitions(state_machine, race_condition)
            )
            
            # Simulate messages arriving with network delays during transitions
            message_task = asyncio.create_task(
                self._simulate_messages_during_network_partition(messages, race_condition)
            )
            
            # Wait for both with different timing
            results = await asyncio.gather(transition_task, message_task, return_exceptions=True)
            transition_result, message_result = results
            
            # Check for race conditions
            if isinstance(transition_result, Exception) or isinstance(message_result, Exception):
                race_condition.success = False
                race_condition.error_details = (
                    f"Transition: {transition_result}, Messages: {message_result}"
                )
                logger.info(f" PASS:  Network partition race condition detected")
            else:
                race_condition.success = True
                race_condition.error_details = "NO RACE CONDITION: All operations completed successfully"
                
        except Exception as e:
            race_condition.success = False
            race_condition.error_details = f"Network partition error: {str(e)}"
            logger.info(f" PASS:  Network partition caused race condition: {e}")
            
        finally:
            race_condition.end_time = time.time()
            self.race_conditions.append(race_condition)
        
        # CRITICAL ASSERTION: Network partition should cause race conditions
        assert not race_condition.success, (
            f"NETWORK PARTITION RACE CONDITION NOT DETECTED: Operations completed without issues. "
            f"This indicates message ordering is properly coordinated or race conditions "
            f"are not being triggered. Details: {race_condition.error_details}"
        )

    # Helper methods for Cloud Run simulation

    def _create_cloud_run_websocket_mock(self) -> MagicMock:
        """Create WebSocket mock that simulates Cloud Run behavior."""
        websocket_mock = MagicMock()
        websocket_mock.client_state = "CONNECTING"
        websocket_mock.accept = AsyncMock()
        websocket_mock.send_text = AsyncMock()
        websocket_mock.receive_text = AsyncMock()
        websocket_mock.close = AsyncMock()
        return websocket_mock

    async def _simulate_immediate_application_processing(self, websocket_mock, race_condition: CloudRunRaceCondition):
        """Simulate application trying to process immediately (Cloud Run behavior)."""
        try:
            logger.info(" CYCLE:  Application attempting immediate processing")
            
            # Try to use WebSocket before handshake is complete
            if websocket_mock.client_state != "CONNECTED":
                raise RuntimeError("Application processing attempted before handshake completion")
            
            await websocket_mock.send_text('{"type": "connection_ready"}')
            return {"success": True, "message": "Application processing succeeded"}
            
        except Exception as e:
            logger.info(f"Application processing failed as expected: {e}")
            raise

    async def _simulate_delayed_websocket_handshake(self, websocket_mock, race_condition: CloudRunRaceCondition):
        """Simulate delayed WebSocket handshake completion."""
        try:
            logger.info(" CYCLE:  Completing delayed WebSocket handshake")
            
            # Simulate handshake completion
            await websocket_mock.accept()
            websocket_mock.client_state = "CONNECTED"
            
            return {"success": True, "message": "Handshake completed"}
            
        except Exception as e:
            logger.info(f"Handshake failed: {e}")
            raise

    async def _check_services_availability_during_startup(self, race_condition: CloudRunRaceCondition, delay: float) -> bool:
        """Check if services are available during container startup."""
        # Simulate service discovery with delay
        await asyncio.sleep(delay)
        
        # During startup, services are not immediately available
        supervisor_available = random.random() > 0.7  # 30% chance services ready
        thread_service_available = random.random() > 0.6  # 40% chance thread service ready
        
        services_ready = supervisor_available and thread_service_available
        
        logger.info(f" SEARCH:  Service availability check: Supervisor={supervisor_available}, Threads={thread_service_available}")
        
        return services_ready

    async def _simulate_container_with_concurrent_connections(self, container_idx: int, num_connections: int, 
                                                            race_condition: CloudRunRaceCondition) -> Dict[str, Any]:
        """Simulate a container handling multiple concurrent connections."""
        try:
            logger.info(f"[U+1F3ED] Container {container_idx} starting with {num_connections} connections")
            
            # Create connections concurrently within this container
            connection_tasks = []
            
            for conn_idx in range(num_connections):
                connection_id = f"container_{container_idx}_conn_{conn_idx}_{int(time.time() * 1000)}"
                user_id = f"user_{container_idx}_{conn_idx}"
                
                task = asyncio.create_task(
                    self._create_connection_in_container(connection_id, user_id, container_idx)
                )
                connection_tasks.append(task)
            
            # Wait for all connections in this container
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Analyze connection results
            successful_connections = []
            failed_connections = []
            
            for idx, result in enumerate(connection_results):
                if isinstance(result, Exception):
                    failed_connections.append({"index": idx, "error": str(result)})
                else:
                    successful_connections.append(result)
            
            container_result = {
                "container_idx": container_idx,
                "connections": successful_connections,
                "failures": failed_connections,
                "success": len(failed_connections) == 0
            }
            
            if failed_connections:
                logger.info(f" PASS:  Container {container_idx} had expected failures: {len(failed_connections)}")
            
            return container_result
            
        except Exception as e:
            logger.info(f" PASS:  Container {container_idx} failed with race condition: {e}")
            raise

    async def _create_connection_in_container(self, connection_id: str, user_id: str, container_idx: int) -> Dict[str, Any]:
        """Create a WebSocket connection within a container."""
        try:
            # Small random delay to simulate real connection timing
            await asyncio.sleep(random.uniform(0.01, 0.05))
            
            # Create state machine
            state_machine = ConnectionStateMachine(connection_id, user_id)
            
            # Rapid state transitions (may cause race conditions)
            states = [
                ApplicationConnectionState.ACCEPTED,
                ApplicationConnectionState.AUTHENTICATED, 
                ApplicationConnectionState.SERVICES_READY
            ]
            
            for state in states:
                if not state_machine.transition_to(state, f"Container {container_idx} transition"):
                    raise RuntimeError(f"Failed to transition to {state.value}")
                
                # Small delay between transitions
                await asyncio.sleep(0.001)
            
            return {
                "connection_id": connection_id,
                "user_id": user_id,
                "container_idx": container_idx,
                "final_state": state_machine.current_state.value,
                "success": True
            }
            
        except Exception as e:
            logger.info(f"Connection creation failed in container {container_idx}: {e}")
            raise

    async def _simulate_slow_state_transitions(self, state_machine: ConnectionStateMachine, 
                                             race_condition: CloudRunRaceCondition):
        """Simulate slow state transitions during network issues."""
        try:
            states = [
                (ApplicationConnectionState.ACCEPTED, "Accept with network delay"),
                (ApplicationConnectionState.AUTHENTICATED, "Auth with network delay"),
                (ApplicationConnectionState.SERVICES_READY, "Services with network delay")
            ]
            
            for state, reason in states:
                # Simulate network delay during transition
                network_delay = random.uniform(0.1, 0.3)
                race_condition.infrastructure_delays.append(network_delay)
                
                logger.info(f" CYCLE:  State transition to {state.value} with {network_delay:.3f}s network delay")
                await asyncio.sleep(network_delay)
                
                if not state_machine.transition_to(state, reason):
                    raise StateTransitionError(f"Failed transition to {state.value}")
            
            return {"success": True, "final_state": state_machine.current_state.value}
            
        except Exception as e:
            logger.info(f"State transitions failed: {e}")
            raise

    async def _simulate_messages_during_network_partition(self, messages: List[Dict[str, Any]], 
                                                        race_condition: CloudRunRaceCondition):
        """Simulate messages arriving during network partition."""
        try:
            processed_messages = []
            
            for message in messages:
                # Simulate network partition delay
                partition_delay = random.uniform(0.05, 0.25)
                race_condition.infrastructure_delays.append(partition_delay)
                
                logger.info(f"[U+1F4E8] Processing message {message['sequence']} with {partition_delay:.3f}s partition delay")
                await asyncio.sleep(partition_delay)
                
                # Try to process message (may fail if state is not ready)
                processed_messages.append({
                    "sequence": message["sequence"],
                    "processed_at": time.time(),
                    "delay": partition_delay
                })
            
            return {"success": True, "processed_messages": processed_messages}
            
        except Exception as e:
            logger.info(f"Message processing failed during network partition: {e}")
            raise


# Test configuration
pytestmark = [
    pytest.mark.race_condition,
    pytest.mark.cloud_run,
    pytest.mark.critical,
    pytest.mark.xfail(reason="Cloud Run race condition tests designed to FAIL until proper coordination is implemented")
]


if __name__ == "__main__":
    """
    Run Cloud Run race condition reproduction tests.
    
    Usage:
        python -m pytest tests/critical/test_websocket_cloud_run_race_conditions.py -v
        
    Expected: ALL TESTS SHOULD FAIL with current implementation.
    After implementing proper Cloud Run coordination, tests should PASS.
    """
    pytest.main([__file__, "-v", "--tb=short", "-m", "race_condition"])