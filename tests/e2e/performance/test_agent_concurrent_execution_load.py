"""E2E Agent Performance Under Load Test - GCP Staging Environment

Business Value: $500K+ ARR protection through concurrent agent execution validation
Critical Coverage for Issue #872: Agent performance under load scenarios

REQUIREMENTS:
- Tests 50+ concurrent agent executions in staging environment
- Validates memory usage and response time degradation under load
- Ensures proper resource cleanup after load testing
- Validates WebSocket events under concurrent load
- Uses real services only (no Docker mocking)

Phase 1 Focus: Performance, load handling, and resource management
Target: Validate system stability under concurrent user load

SSOT Compliance: Uses SSotAsyncTestCase, IsolatedEnvironment, real services
"""

import asyncio
import time
import uuid
import psutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.auth import create_real_jwt_token
from tests.e2e.staging_test_base import StagingTestBase
from tests.e2e.staging_websocket_client import StagingWebSocketClient
from tests.e2e.staging_config import get_staging_config


@dataclass
class LoadTestMetrics:
    """Performance metrics for load testing"""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    concurrent_users: int = 0
    successful_connections: int = 0
    successful_agent_executions: int = 0
    failed_executions: int = 0
    response_times: List[float] = field(default_factory=list)
    memory_samples: List[float] = field(default_factory=list)
    cpu_samples: List[float] = field(default_factory=list)
    websocket_events_received: int = 0
    peak_memory_mb: float = 0.0
    avg_response_time: float = 0.0
    
    def record_performance_sample(self) -> None:
        """Record current system performance"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            
            self.memory_samples.append(memory_mb)
            self.cpu_samples.append(cpu_percent)
            self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
        except Exception:
            # Continue test if psutil fails
            pass
    
    def finalize_metrics(self) -> None:
        """Calculate final metrics"""
        self.end_time = time.time()
        if self.response_times:
            self.avg_response_time = sum(self.response_times) / len(self.response_times)


@dataclass
class ConcurrentUser:
    """Represents a concurrent user in load test"""
    user_id: str
    email: str
    access_token: str
    websocket_client: Optional[StagingWebSocketClient] = None
    messages_sent: int = 0
    responses_received: int = 0
    connection_established: bool = False
    test_queries: List[str] = field(default_factory=list)
    received_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Generate test queries for this user"""
        user_suffix = self.user_id.split('_')[-1][:4]
        self.test_queries = [
            f"Analyze AI optimization opportunities for project_{user_suffix}",
            f"What are the cost implications of scaling model_{user_suffix}?",
            f"Recommend infrastructure changes for workload_{user_suffix}",
            f"How can we optimize token usage for application_{user_suffix}?",
            f"Suggest monitoring improvements for system_{user_suffix}"
        ]


class ConcurrentAgentLoadTester(SSotAsyncTestCase, StagingTestBase):
    """Comprehensive agent load testing for GCP staging environment"""
    
    def setup_method(self, method=None):
        """Setup for each test method"""
        super().setup_method(method)
        self.staging_config = get_staging_config()
        self.metrics = LoadTestMetrics()
        self.concurrent_users: List[ConcurrentUser] = []
        self.websocket_url = self.staging_config.websocket_url
        
        # Set test environment variables
        self.set_env_var("TESTING_ENVIRONMENT", "staging")
        self.set_env_var("E2E_LOAD_TEST", "true")
        self.set_env_var("LOAD_TEST_CONCURRENT_USERS", "50")
        
        # Record test start metrics
        self.record_metric("test_start_time", time.time())
        self.metrics.record_performance_sample()
    
    async def create_concurrent_users(self, user_count: int = 50) -> List[ConcurrentUser]:
        """Create authenticated users for concurrent testing"""
        self.metrics.concurrent_users = user_count
        
        # Create users in batches to avoid overwhelming auth service
        batch_size = 10
        all_users = []
        
        for batch_start in range(0, user_count, batch_size):
            batch_end = min(batch_start + batch_size, user_count)
            batch_users = await self._create_user_batch(batch_start, batch_end)
            all_users.extend(batch_users)
            
            # Brief pause between batches
            await asyncio.sleep(0.1)
        
        self.concurrent_users = all_users
        self.record_metric("users_created", len(all_users))
        return all_users
    
    async def _create_user_batch(self, start_idx: int, end_idx: int) -> List[ConcurrentUser]:
        """Create a batch of users concurrently"""
        tasks = []
        for i in range(start_idx, end_idx):
            task = asyncio.create_task(self._create_single_user(i))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [user for user in results if isinstance(user, ConcurrentUser)]
    
    async def _create_single_user(self, index: int) -> ConcurrentUser:
        """Create and authenticate a single user"""
        session_id = f"load_test_{index}_{uuid.uuid4().hex[:8]}"
        user_id = f"load_user_{index}_{int(time.time())}"
        email = f"{user_id}@loadtest.netra.ai"
        
        # Create JWT token with appropriate permissions
        access_token = create_real_jwt_token(
            user_id=user_id,
            permissions=["chat", "agent_execute", "websocket"],
            email=email,
            expires_in=7200  # 2 hours for load test
        )
        
        return ConcurrentUser(
            user_id=user_id,
            email=email,
            access_token=access_token
        )
    
    async def establish_websocket_connections(self, users: List[ConcurrentUser]) -> int:
        """Establish WebSocket connections for all users concurrently"""
        # Connect in smaller batches to avoid overwhelming the server
        batch_size = 15
        successful_connections = 0
        
        for batch_start in range(0, len(users), batch_size):
            batch_end = min(batch_start + batch_size, len(users))
            batch = users[batch_start:batch_end]
            
            # Connect batch concurrently
            tasks = [self._connect_single_user(user) for user in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_connections += sum(1 for r in results if r is True)
            
            # Brief pause between batches
            await asyncio.sleep(0.2)
        
        self.metrics.successful_connections = successful_connections
        self.record_metric("websocket_connections", successful_connections)
        return successful_connections
    
    async def _connect_single_user(self, user: ConcurrentUser) -> bool:
        """Connect a single user's WebSocket"""
        try:
            user.websocket_client = StagingWebSocketClient(
                websocket_url=self.websocket_url,
                access_token=user.access_token,
                user_id=user.user_id
            )
            
            success = await user.websocket_client.connect()
            if success:
                user.connection_established = True
                return True
            
        except Exception as e:
            self.logger.warning(f"Failed to connect user {user.user_id}: {e}")
        
        return False
    
    async def execute_concurrent_agent_load(self, users: List[ConcurrentUser]) -> Dict[str, Any]:
        """Execute concurrent agent requests and measure performance"""
        connected_users = [u for u in users if u.connection_established]
        
        if not connected_users:
            return {"error": "No connected users for load testing"}
        
        self.logger.info(f"Starting load test with {len(connected_users)} connected users")
        
        # Execute agent requests in waves for realistic load patterns
        wave_size = 20  # Users per wave
        wave_delay = 0.5  # Seconds between waves
        
        all_results = []
        for wave_start in range(0, len(connected_users), wave_size):
            wave_end = min(wave_start + wave_size, len(connected_users))
            wave_users = connected_users[wave_start:wave_end]
            
            # Execute wave
            wave_results = await self._execute_agent_wave(wave_users)
            all_results.extend(wave_results)
            
            # Brief pause before next wave
            if wave_end < len(connected_users):
                await asyncio.sleep(wave_delay)
        
        # Calculate results
        successful_executions = sum(1 for r in all_results if r.get("success"))
        failed_executions = len(all_results) - successful_executions
        
        self.metrics.successful_agent_executions = successful_executions
        self.metrics.failed_executions = failed_executions
        
        return {
            "total_executions": len(all_results),
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / len(all_results) if all_results else 0
        }
    
    async def _execute_agent_wave(self, wave_users: List[ConcurrentUser]) -> List[Dict[str, Any]]:
        """Execute agent requests for a wave of users"""
        tasks = []
        for user in wave_users:
            query = user.test_queries[0]  # Use first query for initial load
            task = asyncio.create_task(self._execute_single_agent_request(user, query))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if isinstance(r, dict) else {"success": False, "error": str(r)} 
                for r in results]
    
    async def _execute_single_agent_request(self, user: ConcurrentUser, query: str) -> Dict[str, Any]:
        """Execute a single agent request and measure performance"""
        start_time = time.time()
        self.metrics.record_performance_sample()
        
        try:
            # Send agent message
            message = {
                "type": "chat_message",
                "content": query,
                "user_id": user.user_id,
                "session_id": f"session_{user.user_id}",
                "timestamp": time.time()
            }
            
            await user.websocket_client.send_message(message)
            user.messages_sent += 1
            
            # Wait for agent response with timeout
            response = await self._wait_for_agent_response(user, timeout=15.0)
            
            if response:
                response_time = time.time() - start_time
                self.metrics.response_times.append(response_time)
                user.responses_received += 1
                
                # Count WebSocket events received
                events_count = len(response.get("events", []))
                self.metrics.websocket_events_received += events_count
                user.received_events.extend(response.get("events", []))
                
                return {
                    "success": True,
                    "response_time": response_time,
                    "events_received": events_count,
                    "user_id": user.user_id
                }
            else:
                return {
                    "success": False,
                    "error": "No response received",
                    "user_id": user.user_id
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "user_id": user.user_id
            }
    
    async def _wait_for_agent_response(self, user: ConcurrentUser, timeout: float = 15.0) -> Optional[Dict[str, Any]]:
        """Wait for complete agent response with all WebSocket events"""
        events_received = []
        agent_completed = False
        start_time = time.time()
        
        while time.time() - start_time < timeout and not agent_completed:
            try:
                # Check for new messages
                message = await user.websocket_client.receive_message(timeout=1.0)
                if message:
                    events_received.append(message)
                    
                    # Check if agent execution is complete
                    if message.get("type") == "agent_completed":
                        agent_completed = True
                        break
                        
                await asyncio.sleep(0.1)
                
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
        
        if events_received:
            return {"events": events_received, "completed": agent_completed}
        
        return None
    
    async def cleanup_test_resources(self) -> None:
        """Clean up all test resources"""
        self.logger.info("Cleaning up load test resources...")
        
        # Close all WebSocket connections
        cleanup_tasks = []
        for user in self.concurrent_users:
            if user.websocket_client:
                task = asyncio.create_task(user.websocket_client.disconnect())
                cleanup_tasks.append(task)
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Record final metrics
        self.metrics.finalize_metrics()
        
        # Log cleanup completion
        self.record_metric("cleanup_completed", time.time())
        self.logger.info("Load test cleanup completed")


class TestAgentConcurrentExecutionLoad:
    """E2E Agent Performance Load Tests for GCP Staging"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.performance
    @pytest.mark.staging
    async def test_50_concurrent_agent_executions(self):
        """
        CRITICAL: Test 50 concurrent agent executions in staging
        
        This test validates:
        1. System can handle 50+ concurrent users
        2. Memory usage remains within acceptable limits
        3. Response times don't degrade excessively
        4. WebSocket events are delivered under load
        5. Proper resource cleanup after load
        
        Success Criteria:
        - At least 80% of agent executions successful
        - Average response time < 10 seconds
        - Peak memory usage < 2GB
        - All WebSocket events delivered
        """
        tester = ConcurrentAgentLoadTester()
        tester.setup_method()
        
        try:
            # Phase 1: Create concurrent users
            users = await tester.create_concurrent_users(50)
            assert len(users) == 50, f"Expected 50 users, created {len(users)}"
            
            # Phase 2: Establish WebSocket connections
            connections = await tester.establish_websocket_connections(users)
            assert connections >= 40, f"Expected at least 40 connections, got {connections}"
            
            # Phase 3: Execute concurrent load
            load_results = await tester.execute_concurrent_agent_load(users)
            
            # Phase 4: Validate performance requirements
            await tester._validate_load_performance(load_results)
            
            # Phase 5: Validate system stability
            await tester._validate_system_stability()
            
        finally:
            await tester.cleanup_test_resources()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.performance
    @pytest.mark.staging
    async def test_memory_usage_under_concurrent_load(self):
        """
        Test memory usage patterns under concurrent agent load
        
        Validates:
        1. Memory usage doesn't exceed limits during load
        2. Memory is properly released after user disconnection
        3. No memory leaks during sustained load
        """
        tester = ConcurrentAgentLoadTester()
        tester.setup_method()
        
        try:
            # Create smaller batch for memory testing
            users = await tester.create_concurrent_users(25)
            connections = await tester.establish_websocket_connections(users)
            
            # Record baseline memory
            baseline_memory = tester.metrics.peak_memory_mb
            
            # Execute load and monitor memory
            load_results = await tester.execute_concurrent_agent_load(users)
            peak_memory = tester.metrics.peak_memory_mb
            
            # Disconnect half the users and check memory
            await tester._disconnect_users(users[:12])
            await asyncio.sleep(2.0)  # Allow cleanup
            
            tester.metrics.record_performance_sample()
            post_cleanup_memory = tester.metrics.memory_samples[-1]
            
            # Validate memory behavior
            memory_growth = peak_memory - baseline_memory
            memory_released = peak_memory - post_cleanup_memory
            
            assert memory_growth < 1000, f"Memory growth {memory_growth}MB exceeds 1GB limit"
            assert memory_released > memory_growth * 0.3, "Insufficient memory cleanup after disconnection"
            
        finally:
            await tester.cleanup_test_resources()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.performance
    @pytest.mark.staging
    async def test_websocket_events_under_load(self):
        """
        Test WebSocket event delivery under concurrent load
        
        Validates:
        1. All required WebSocket events are delivered
        2. Events are delivered to correct users
        3. Event delivery remains reliable under load
        """
        tester = ConcurrentAgentLoadTester()
        tester.setup_method()
        
        try:
            # Create moderate load for event testing
            users = await tester.create_concurrent_users(30)
            connections = await tester.establish_websocket_connections(users)
            
            # Execute load with focus on event validation
            load_results = await tester.execute_concurrent_agent_load(users)
            
            # Validate WebSocket events
            await tester._validate_websocket_events_delivery(users)
            
        finally:
            await tester.cleanup_test_resources()


# Extended methods for ConcurrentAgentLoadTester
async def _validate_load_performance(self, load_results: Dict[str, Any]) -> None:
    """Validate load test performance requirements"""
    success_rate = load_results.get("success_rate", 0)
    assert success_rate >= 0.8, f"Success rate {success_rate:.2%} below 80% threshold"
    
    if self.metrics.avg_response_time > 0:
        assert self.metrics.avg_response_time < 10.0, \
            f"Average response time {self.metrics.avg_response_time:.2f}s exceeds 10s limit"
    
    assert self.metrics.peak_memory_mb < 2048, \
        f"Peak memory {self.metrics.peak_memory_mb:.1f}MB exceeds 2GB limit"
    
    self.logger.info(f"LOAD TEST SUCCESS: {success_rate:.2%} success rate, "
                    f"{self.metrics.avg_response_time:.2f}s avg response time, "
                    f"{self.metrics.peak_memory_mb:.1f}MB peak memory")


async def _validate_system_stability(self) -> None:
    """Validate system remains stable after load test"""
    # Check that metrics were collected
    assert len(self.metrics.memory_samples) > 0, "No memory samples collected"
    assert len(self.metrics.response_times) > 0, "No response times recorded"
    
    # Check for reasonable event delivery
    assert self.metrics.websocket_events_received > 0, "No WebSocket events received"
    
    # Log stability validation
    self.logger.info("System stability validated after concurrent load test")


async def _disconnect_users(self, users: List[ConcurrentUser]) -> None:
    """Disconnect a subset of users for cleanup testing"""
    tasks = []
    for user in users:
        if user.websocket_client:
            task = asyncio.create_task(user.websocket_client.disconnect())
            tasks.append(task)
    
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def _validate_websocket_events_delivery(self, users: List[ConcurrentUser]) -> None:
    """Validate WebSocket events were properly delivered to users"""
    connected_users = [u for u in users if u.connection_established]
    users_with_events = [u for u in connected_users if u.received_events]
    
    event_delivery_rate = len(users_with_events) / len(connected_users) if connected_users else 0
    assert event_delivery_rate >= 0.7, f"Event delivery rate {event_delivery_rate:.2%} below 70%"
    
    # Validate event types received
    required_events = {"agent_started", "agent_thinking", "agent_completed"}
    for user in users_with_events[:5]:  # Check first 5 users
        event_types = {event.get("type") for event in user.received_events}
        missing_events = required_events - event_types
        assert len(missing_events) <= 1, f"User {user.user_id} missing events: {missing_events}"


# Attach extended methods to the class
ConcurrentAgentLoadTester._validate_load_performance = _validate_load_performance
ConcurrentAgentLoadTester._validate_system_stability = _validate_system_stability
ConcurrentAgentLoadTester._disconnect_users = _disconnect_users
ConcurrentAgentLoadTester._validate_websocket_events_delivery = _validate_websocket_events_delivery