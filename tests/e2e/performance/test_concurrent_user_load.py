"""
Concurrent User Load Test Suite

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Platform Stability, Scalability Validation
- Value Impact: Ensures system handles enterprise-level concurrent user loads
- Strategic/Revenue Impact: Critical for enterprise SLA compliance
"""

import asyncio
import time
import uuid
import pytest
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import psutil
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
from test_framework import setup_test_path
setup_test_path()

from tests.e2e.real_services_manager import ServiceManager
from tests.e2e.harness_utils import UnifiedTestHarnessComplete, create_test_harness
from tests.e2e.jwt_token_helpers import JWTTestHelper
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient
from test_framework.http_client import ClientConfig


@dataclass
class TestLoadMetrics:
    """Metrics for concurrent load testing."""
    concurrent_users: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    avg_response_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    test_duration_seconds: float = 0.0
    error_rate: float = 0.0


# Alias for backward compatibility
LoadTestMetrics = TestLoadMetrics


class TestConcurrentUserLoader:
    """Manages concurrent user load testing."""
    
    def __init__(self, harness: UnifiedTestHarnessComplete):
        self.harness = harness
        self.service_manager = ServiceManager(harness)
        self.jwt_helper = JWTTestHelper()
        self.ws_url = "ws://localhost:8000/ws"
        self.config = ClientConfig(timeout=10.0, max_retries=3)
        self.users: List[Dict[str, Any]] = []
        self.connections: List[RealWebSocketClient] = []
        
    async def setup_services(self) -> None:
        """Setup required services."""
        await self.service_manager.start_all_services(skip_frontend=True)
        await asyncio.sleep(2.0)  # Allow services to stabilize
        
    async def teardown_services(self) -> None:
        """Cleanup services."""
        await self._cleanup_all_connections()
        if self.service_manager:
            await self.service_manager.stop_all_services()
    
    def create_test_users(self, count: int) -> List[Dict[str, Any]]:
        """Create test users with unique tokens."""
        users = []
        for i in range(count):
            user_id = f"load-test-user-{i:03d}-{uuid.uuid4().hex[:8]}"
            payload = self.jwt_helper.create_valid_payload()
            payload["sub"] = user_id
            payload["email"] = f"loadtest{i}@netrasystems.ai"
            token = self.jwt_helper.create_token(payload)
            
            users.append({
                "user_id": user_id,
                "token": token,
                "client": None,
                "connected": False
            })
        
        self.users = users
        return users
    
    async def establish_concurrent_connections(self, target_users: int = 100) -> LoadTestMetrics:
        """Establish concurrent connections and measure performance."""
        start_time = time.time()
        initial_memory = self._get_memory_usage()
        
        metrics = LoadTestMetrics(concurrent_users=target_users)
        
        # Create connections concurrently
        connection_tasks = []
        for user in self.users[:target_users]:
            task = self._connect_single_user(user)
            connection_tasks.append(task)
        
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Analyze connection results
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful
        
        metrics.successful_connections = successful
        metrics.failed_connections = failed
        metrics.peak_memory_mb = self._get_memory_usage()
        metrics.test_duration_seconds = time.time() - start_time
        metrics.error_rate = failed / len(results) if results else 0
        
        return metrics
    
    async def _connect_single_user(self, user: Dict[str, Any]) -> bool:
        """Connect a single user to WebSocket."""
        try:
            client = RealWebSocketClient(self.ws_url, self.config)
            headers = {"Authorization": f"Bearer {user['token']}"}
            
            success = await client.connect(headers)
            if success:
                user["client"] = client
                user["connected"] = True
                self.connections.append(client)
                return True
            return False
        except Exception:
            return False
    
    @pytest.mark.performance
    async def test_concurrent_messaging(self, message_count: int = 10) -> LoadTestMetrics:
        """Test concurrent messaging from all connected users."""
        start_time = time.time()
        metrics = LoadTestMetrics()
        
        # Send messages concurrently from all connected users
        messaging_tasks = []
        for user in self.users:
            if user["connected"] and user["client"]:
                task = self._send_user_messages(user, message_count)
                messaging_tasks.append(task)
        
        results = await asyncio.gather(*messaging_tasks, return_exceptions=True)
        
        # Calculate metrics
        total_sent = sum(r["sent"] for r in results if isinstance(r, dict))
        total_received = sum(r["received"] for r in results if isinstance(r, dict))
        response_times = []
        for r in results:
            if isinstance(r, dict) and "response_times" in r:
                response_times.extend(r["response_times"])
        
        metrics.messages_sent = total_sent
        metrics.messages_received = total_received
        metrics.avg_response_time_ms = sum(response_times) / len(response_times) if response_times else 0
        metrics.test_duration_seconds = time.time() - start_time
        
        return metrics
    
    async def _send_user_messages(self, user: Dict[str, Any], count: int) -> Dict[str, Any]:
        """Send messages from a single user."""
        client = user["client"]
        sent = 0
        received = 0
        response_times = []
        
        for i in range(count):
            try:
                message = {
                    "type": "test_message",
                    "content": f"Load test message {i} from {user['user_id']}",
                    "user_id": user["user_id"],
                    "timestamp": time.time()
                }
                
                send_start = time.time()
                success = await client.send(message)
                if success:
                    sent += 1
                    
                    # Try to receive response
                    try:
                        response = await client.receive(timeout=2.0)
                        if response:
                            received += 1
                            response_times.append((time.time() - send_start) * 1000)
                    except Exception:
                        pass  # Timeout or no response
                        
            except Exception:
                pass  # Connection error
        
        return {
            "sent": sent,
            "received": received,
            "response_times": response_times
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    async def _cleanup_all_connections(self) -> None:
        """Cleanup all WebSocket connections."""
        cleanup_tasks = []
        for client in self.connections:
            task = self._cleanup_single_connection(client)
            cleanup_tasks.append(task)
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.connections.clear()
        for user in self.users:
            user["connected"] = False
            user["client"] = None
    
    async def _cleanup_single_connection(self, client: RealWebSocketClient) -> None:
        """Cleanup single connection."""
        try:
            await client.close()
        except Exception:
            pass  # Best effort cleanup


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.timeout(300)  # 5 minutes max
class TestConcurrentUserLoad:
    """Concurrent user load testing."""
    
    @pytest.mark.performance
    async def test_concurrent_user_connections(self, unified_test_harness):
        """Test 100 concurrent user connections."""
        tester = ConcurrentUserLoadTester(unified_test_harness)
        
        try:
            # Setup services
            await tester.setup_services()
            
            # Create test users
            users = tester.create_test_users(100)
            assert len(users) == 100
            
            # Test concurrent connections
            connection_metrics = await tester.establish_concurrent_connections(100)
            
            # Validate connection success rate (should be at least 95%)
            success_rate = connection_metrics.successful_connections / connection_metrics.concurrent_users
            assert success_rate >= 0.95, f"Connection success rate {success_rate:.2%} below 95%"
            
            # Validate performance
            assert connection_metrics.test_duration_seconds < 30.0, "Connection setup took too long"
            assert connection_metrics.error_rate < 0.05, "Too many connection errors"
            
            # Test concurrent messaging
            messaging_metrics = await tester.test_concurrent_messaging(5)
            
            # Validate messaging performance
            assert messaging_metrics.messages_sent > 0, "No messages were sent"
            assert messaging_metrics.avg_response_time_ms < 1000, "Response times too high"
            
        finally:
            await tester.teardown_services()
    
    @pytest.mark.performance
    async def test_resource_usage_under_load(self, unified_test_harness):
        """Test resource usage under concurrent load."""
        tester = ConcurrentUserLoadTester(unified_test_harness)
        
        try:
            await tester.setup_services()
            
            initial_memory = tester._get_memory_usage()
            
            # Create and connect 50 users
            users = tester.create_test_users(50)
            metrics = await tester.establish_concurrent_connections(50)
            
            # Check memory usage increase
            memory_increase = metrics.peak_memory_mb - initial_memory
            assert memory_increase < 500, f"Memory usage increased by {memory_increase:.1f}MB"
            
            # Validate reasonable success rate
            success_rate = metrics.successful_connections / metrics.concurrent_users
            assert success_rate >= 0.90, f"Success rate {success_rate:.2%} too low"
            
        finally:
            await tester.teardown_services()


@pytest.fixture
async def unified_test_harness():
    """Unified test harness fixture for performance tests."""
    harness = await create_test_harness("performance_test")
    yield harness
    await harness.cleanup()


# Backward compatibility aliases
TestConcurrentLoadCore = TestConcurrentUserLoad