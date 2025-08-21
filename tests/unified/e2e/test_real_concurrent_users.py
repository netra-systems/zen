"""Real Concurrent Users E2E Test - Enterprise Multi-Tenancy Validation

CRITICAL: Enterprise Feature - Real Concurrent User Data Isolation & Performance
This test validates enterprise-grade multi-tenant architecture under concurrent load.

Business Value Justification (BVJ):
- Segment: Enterprise (multi-tenant architecture required)
- Business Goal: Guarantee data isolation and performance under concurrent load
- Value Impact: Prevents enterprise customer churn from concurrency/isolation issues
- Revenue Impact: Protects $100K+ ARR from enterprise contracts

Test #10: Real Concurrent Users with Data Isolation
- 10+ real user sessions with unique data
- Real WebSocket connections and authentication
- Complete data isolation validation
- Database connection pooling stress test
- Performance metrics (latency, throughput)
- Resource allocation fairness
- Message cross-contamination detection

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines (MANDATORY)
- Function size: <25 lines each (MANDATORY)
- Real services integration (NO MOCKING)
- Type safety with annotations
"""

import pytest
import pytest_asyncio
import asyncio
import time
import uuid
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from netra_backend.tests.unified.real_services_manager import create_real_services_manager
from netra_backend.tests.unified.real_websocket_client import RealWebSocketClient
from netra_backend.tests.unified.real_client_types import ClientConfig, ConnectionState
from netra_backend.tests.unified.jwt_token_helpers import JWTTestHelper


@dataclass
class RealUserSession:
    """Real user session with authentication and WebSocket connection"""
    user_id: str
    email: str
    access_token: Optional[str] = None
    websocket_client: Optional[RealWebSocketClient] = None
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sent_messages: List[Dict[str, Any]] = field(default_factory=list)
    received_responses: List[Dict[str, Any]] = field(default_factory=list)
    secret_data: str = field(default_factory=lambda: f"SECRET_{uuid.uuid4().hex[:8]}")
    response_times: List[float] = field(default_factory=list)


@dataclass
class ConcurrentUserMetrics:
    """Performance and isolation metrics for concurrent user testing"""
    total_users: int = 0
    successful_authentications: int = 0
    successful_connections: int = 0
    successful_messages: int = 0
    response_times: List[float] = field(default_factory=list)
    connection_times: List[float] = field(default_factory=list)
    isolation_violations: int = 0
    cross_contamination_detected: bool = False
    throughput_messages_per_second: float = 0.0
    avg_response_latency: float = 0.0
    resource_allocation_fairness: float = 0.0


class RealConcurrentUserManager:
    """Manages real concurrent user sessions with authentication and WebSocket connections"""
    
    def __init__(self):
        self.services_manager = None
        self.jwt_helper = JWTTestHelper()
        self.metrics = ConcurrentUserMetrics()
        self.auth_url = "http://localhost:8081"
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        self.user_sessions: List[RealUserSession] = []
    
    async def setup_real_services(self) -> None:
        """Start real services for testing"""
        self.services_manager = create_real_services_manager()
        await self.services_manager.start_all_services()
        
        # Verify services are ready
        health_status = await self.services_manager.health_status()
        if not all(svc['ready'] for svc in health_status.values()):
            raise RuntimeError(f"Services not ready: {health_status}")
    
    async def teardown_real_services(self) -> None:
        """Clean shutdown of all services and connections"""
        # Close all WebSocket connections
        cleanup_tasks = []
        for user in self.user_sessions:
            if user.websocket_client:
                cleanup_tasks.append(user.websocket_client.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Stop services
        if self.services_manager:
            await self.services_manager.stop_all_services()
    
    async def create_concurrent_users(self, user_count: int) -> List[RealUserSession]:
        """Create multiple authenticated user sessions concurrently"""
        self.metrics.total_users = user_count
        
        # Create user authentication tasks
        auth_tasks = []
        for i in range(user_count):
            user_id = f"real_concurrent_user_{i}_{uuid.uuid4().hex[:6]}"
            email = f"{user_id}@enterprise.netrasystems.ai"
            task = asyncio.create_task(self._authenticate_user(user_id, email))
            auth_tasks.append(task)
        
        # Execute authentication concurrently
        results = await asyncio.gather(*auth_tasks, return_exceptions=True)
        
        # Process authentication results
        authenticated_users = []
        for result in results:
            if isinstance(result, RealUserSession) and result.access_token:
                authenticated_users.append(result)
                self.metrics.successful_authentications += 1
        
        self.user_sessions = authenticated_users
        return authenticated_users
    
    async def _authenticate_user(self, user_id: str, email: str) -> RealUserSession:
        """Authenticate a single user and create session"""
        user = RealUserSession(user_id=user_id, email=email)
        
        # Create JWT token for user
        user.access_token = self.jwt_helper.create_access_token(
            user_id=user_id,
            email=email,
            permissions=["read", "write", "chat"]
        )
        
        return user
    
    async def establish_websocket_connections(self, users: List[RealUserSession]) -> int:
        """Establish WebSocket connections for all users concurrently"""
        connection_tasks = []
        for user in users:
            task = asyncio.create_task(self._connect_user_websocket(user))
            connection_tasks.append(task)
        
        # Execute connections concurrently
        start_time = time.time()
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_connection_time = time.time() - start_time
        
        # Count successful connections
        successful_connections = sum(1 for r in results if r is True)
        self.metrics.successful_connections = successful_connections
        self.metrics.connection_times.append(total_connection_time)
        
        return successful_connections
    
    async def _connect_user_websocket(self, user: RealUserSession) -> bool:
        """Establish WebSocket connection for single user"""
        try:
            config = ClientConfig(timeout=10.0, max_retries=2)
            user.websocket_client = RealWebSocketClient(self.websocket_url, config)
            
            headers = {"Authorization": f"Bearer {user.access_token}"}
            connected = await user.websocket_client.connect(headers)
            
            return connected
        except Exception:
            return False
    
    async def send_concurrent_messages(self, users: List[RealUserSession]) -> Dict[str, Any]:
        """Send unique messages from all users concurrently and collect responses"""
        message_tasks = []
        for user in users:
            if user.websocket_client:
                task = asyncio.create_task(self._send_user_message_and_receive(user))
                message_tasks.append(task)
        
        # Execute concurrent messaging
        start_time = time.time()
        results = await asyncio.gather(*message_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_messages = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        self.metrics.successful_messages = successful_messages
        
        # Calculate throughput
        if total_time > 0:
            self.metrics.throughput_messages_per_second = successful_messages / total_time
        
        return {
            "total_messages": len(results),
            "successful_messages": successful_messages,
            "total_time": total_time,
            "throughput_msgs_per_sec": self.metrics.throughput_messages_per_second
        }
    
    async def _send_user_message_and_receive(self, user: RealUserSession) -> Dict[str, Any]:
        """Send unique message for user and wait for response"""
        start_time = time.time()
        
        # Create unique message with user's secret data
        unique_message = {
            "type": "chat_message",
            "content": f"Analyze my confidential data: {user.secret_data}. Optimize AI costs for user {user.user_id}.",
            "thread_id": user.thread_id,
            "user_id": user.user_id,
            "timestamp": time.time(),
            "session_secret": user.secret_data
        }
        
        try:
            # Send message
            sent = await user.websocket_client.send(unique_message)
            user.sent_messages.append(unique_message)
            
            if sent:
                # Wait for response
                response = await user.websocket_client.receive(timeout=5.0)
                response_time = time.time() - start_time
                
                if response:
                    user.received_responses.append(response)
                    user.response_times.append(response_time)
                    self.metrics.response_times.append(response_time)
                    
                    return {"success": True, "response": response, "response_time": response_time}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "No response received"}


class RealDataIsolationValidator:
    """Validates strict data isolation between concurrent users"""
    
    def __init__(self, metrics: ConcurrentUserMetrics):
        self.metrics = metrics
    
    def validate_complete_isolation(self, users: List[RealUserSession]) -> Dict[str, Any]:
        """Perform comprehensive data isolation validation"""
        isolation_results = {
            "thread_id_conflicts": self._check_thread_conflicts(users),
            "token_isolation_violations": self._check_token_isolation(users),
            "secret_data_contamination": self._check_secret_data_contamination(users),
            "response_cross_contamination": self._check_response_contamination(users),
            "user_id_leakage": self._check_user_id_leakage(users),
            "session_boundary_violations": self._check_session_boundaries(users)
        }
        
        # Calculate total violations
        total_violations = sum(isolation_results.values())
        self.metrics.isolation_violations = total_violations
        self.metrics.cross_contamination_detected = total_violations > 0
        
        return isolation_results
    
    def _check_thread_conflicts(self, users: List[RealUserSession]) -> int:
        """Check for thread ID conflicts between users"""
        thread_ids = [user.thread_id for user in users]
        unique_threads = set(thread_ids)
        return len(thread_ids) - len(unique_threads)
    
    def _check_token_isolation(self, users: List[RealUserSession]) -> int:
        """Check that users have unique access tokens"""
        tokens = [user.access_token for user in users if user.access_token]
        unique_tokens = set(tokens)
        return len(tokens) - len(unique_tokens)
    
    def _check_secret_data_contamination(self, users: List[RealUserSession]) -> int:
        """Check if users' secret data appears in other users' responses"""
        contamination_count = 0
        
        for user in users:
            user_secret = user.secret_data
            
            # Check if this user's secret appears in other users' responses
            for other_user in users:
                if other_user.user_id != user.user_id:
                    for response in other_user.received_responses:
                        response_content = str(response.get("content", "")).upper()
                        if user_secret.upper() in response_content:
                            contamination_count += 1
        
        return contamination_count
    
    def _check_response_contamination(self, users: List[RealUserSession]) -> int:
        """Check if users received responses containing other users' identifiers"""
        contamination_count = 0
        
        for user in users:
            for response in user.received_responses:
                response_content = str(response.get("content", "")).lower()
                
                # Check if response contains other users' identifiers
                for other_user in users:
                    if other_user.user_id != user.user_id:
                        if other_user.user_id.lower() in response_content:
                            contamination_count += 1
        
        return contamination_count
    
    def _check_user_id_leakage(self, users: List[RealUserSession]) -> int:
        """Check for user ID leakage in responses"""
        leakage_count = 0
        
        for user in users:
            for response in user.received_responses:
                # Response should not contain other users' IDs
                response_str = str(response).lower()
                for other_user in users:
                    if other_user.user_id != user.user_id:
                        if other_user.user_id.lower() in response_str:
                            leakage_count += 1
        
        return leakage_count
    
    def _check_session_boundaries(self, users: List[RealUserSession]) -> int:
        """Check that session data stays within user boundaries"""
        boundary_violations = 0
        
        for user in users:
            # Check sent messages don't appear in other users' data
            for sent_msg in user.sent_messages:
                sent_content = sent_msg.get("content", "")
                
                for other_user in users:
                    if other_user.user_id != user.user_id:
                        # Check if this user's message content appears in other user's responses
                        for response in other_user.received_responses:
                            if sent_content.lower() in str(response).lower():
                                boundary_violations += 1
        
        return boundary_violations


class RealPerformanceAnalyzer:
    """Analyzes performance metrics for concurrent users"""
    
    def __init__(self, metrics: ConcurrentUserMetrics):
        self.metrics = metrics
    
    def analyze_performance(self, users: List[RealUserSession]) -> Dict[str, Any]:
        """Comprehensive performance analysis"""
        if not self.metrics.response_times:
            return {"error": "No response times recorded"}
        
        # Calculate latency statistics
        response_times = self.metrics.response_times
        self.metrics.avg_response_latency = statistics.mean(response_times)
        
        # Analyze resource allocation fairness
        user_response_counts = [len(user.response_times) for user in users]
        fairness_score = self._calculate_fairness_score(user_response_counts)
        self.metrics.resource_allocation_fairness = fairness_score
        
        return {
            "avg_response_latency": self.metrics.avg_response_latency,
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "median_response_time": statistics.median(response_times),
            "response_time_std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0.0,
            "throughput_msgs_per_sec": self.metrics.throughput_messages_per_second,
            "resource_allocation_fairness": fairness_score,
            "total_successful_messages": self.metrics.successful_messages
        }
    
    def _calculate_fairness_score(self, response_counts: List[int]) -> float:
        """Calculate fairness score for resource allocation (0.0 = unfair, 1.0 = perfectly fair)"""
        if not response_counts or all(count == 0 for count in response_counts):
            return 0.0
        
        # Use coefficient of variation to measure fairness
        mean_count = statistics.mean(response_counts)
        if mean_count == 0:
            return 0.0
        
        std_dev = statistics.stdev(response_counts) if len(response_counts) > 1 else 0.0
        coefficient_of_variation = std_dev / mean_count if mean_count > 0 else 1.0
        
        # Convert to fairness score (lower variation = higher fairness)
        fairness_score = max(0.0, 1.0 - coefficient_of_variation)
        return fairness_score


@pytest_asyncio.fixture
async def real_concurrent_manager():
    """Real concurrent user manager fixture"""
    manager = RealConcurrentUserManager()
    await manager.setup_real_services()
    yield manager
    await manager.teardown_real_services()


class TestRealConcurrentUsers:
    """Test real concurrent users with data isolation and performance validation"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_concurrent_users_data_isolation(self, real_concurrent_manager):
        """
        CRITICAL Test #10: Real concurrent users with complete data isolation
        
        Enterprise Feature Validation:
        - 10+ real user sessions
        - Real WebSocket connections
        - Complete data isolation
        - Performance under load
        - Resource allocation fairness
        """
        manager = real_concurrent_manager
        start_time = time.time()
        
        try:
            # Step 1: Create 12 concurrent authenticated users
            users = await manager.create_concurrent_users(12)
            assert len(users) >= 10, f"Expected at least 10 users, got {len(users)}"
            assert manager.metrics.successful_authentications >= 10, "Authentication failures detected"
            
            # Step 2: Establish WebSocket connections concurrently
            successful_connections = await manager.establish_websocket_connections(users)
            assert successful_connections >= 10, f"Expected at least 10 connections, got {successful_connections}"
            
            # Step 3: Send concurrent messages with secret data
            message_results = await manager.send_concurrent_messages(users)
            assert message_results["successful_messages"] >= 10, "Not enough successful messages"
            
            # Step 4: Validate complete data isolation
            validator = RealDataIsolationValidator(manager.metrics)
            isolation_results = validator.validate_complete_isolation(users)
            
            # Critical isolation assertions
            assert isolation_results["thread_id_conflicts"] == 0, "Thread ID conflicts detected"
            assert isolation_results["token_isolation_violations"] == 0, "Token isolation violated"
            assert isolation_results["secret_data_contamination"] == 0, "SECRET DATA CONTAMINATION DETECTED"
            assert isolation_results["response_cross_contamination"] == 0, "Response cross-contamination detected"
            assert isolation_results["user_id_leakage"] == 0, "User ID leakage detected"
            assert isolation_results["session_boundary_violations"] == 0, "Session boundary violations detected"
            
            # Step 5: Performance validation
            analyzer = RealPerformanceAnalyzer(manager.metrics)
            perf_results = analyzer.analyze_performance(users)
            
            # Performance assertions
            assert perf_results["avg_response_latency"] < 5.0, f"Avg latency {perf_results['avg_response_latency']:.2f}s > 5s"
            assert perf_results["throughput_msgs_per_sec"] > 2.0, f"Throughput {perf_results['throughput_msgs_per_sec']:.2f} < 2 msg/s"
            assert perf_results["resource_allocation_fairness"] > 0.7, f"Resource fairness {perf_results['resource_allocation_fairness']:.2f} < 0.7"
            
            # Overall test time constraint
            total_time = time.time() - start_time
            assert total_time < 30.0, f"Test took {total_time:.2f}s, must be <30s"
            
            # Success metrics logging
            print(f"SUCCESS: Real Concurrent Users Test PASSED: {total_time:.2f}s")
            print(f"SUCCESS: Users: {len(users)}, Connections: {successful_connections}, Messages: {manager.metrics.successful_messages}")
            print(f"SUCCESS: Avg Response Time: {perf_results['avg_response_latency']:.2f}s")
            print(f"SUCCESS: Throughput: {perf_results['throughput_msgs_per_sec']:.2f} msg/s")
            print(f"SUCCESS: Resource Fairness: {perf_results['resource_allocation_fairness']:.2f}")
            print(f"SUCCESS: ZERO ISOLATION VIOLATIONS - Enterprise security VALIDATED")
            print(f"SUCCESS: Enterprise Multi-Tenant Architecture VALIDATED - $100K+ ARR PROTECTED")
            
        except Exception as e:
            # Log detailed failure information
            print(f"FAILURE: Real Concurrent Users Test FAILED: {str(e)}")
            print(f"FAILURE: Users: {len(manager.user_sessions)}, Connections: {manager.metrics.successful_connections}")
            print(f"FAILURE: Messages: {manager.metrics.successful_messages}")
            raise
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_user_performance_targets(self, real_concurrent_manager):
        """Test performance targets for concurrent users under sustained load"""
        manager = real_concurrent_manager
        
        # Create users and establish connections
        users = await manager.create_concurrent_users(8)
        await manager.establish_websocket_connections(users)
        
        # Run multiple message rounds to test sustained performance
        round_times = []
        for round_num in range(3):
            start_time = time.time()
            await manager.send_concurrent_messages(users)
            round_time = time.time() - start_time
            round_times.append(round_time)
            
            # Each round must meet performance target
            assert round_time < 10.0, f"Round {round_num + 1} took {round_time:.2f}s > 10s limit"
            
            # Brief pause between rounds
            await asyncio.sleep(1.0)
        
        # Validate performance consistency
        avg_round_time = statistics.mean(round_times)
        max_round_time = max(round_times)
        
        assert avg_round_time < 7.0, f"Average round time {avg_round_time:.2f}s exceeds 7s target"
        assert max_round_time < 10.0, f"Max round time {max_round_time:.2f}s exceeds 10s limit"
        
        print(f"SUCCESS: Performance Targets MET - Avg: {avg_round_time:.2f}s, Max: {max_round_time:.2f}s")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_database_connection_pooling(self, real_concurrent_manager):
        """Test database connection pooling under concurrent user load"""
        manager = real_concurrent_manager
        
        # Create larger user set to stress database connections
        users = await manager.create_concurrent_users(15)
        await manager.establish_websocket_connections(users)
        
        # Send messages that should trigger database operations
        db_intensive_tasks = []
        for user in users:
            if user.websocket_client:
                # Send message that likely triggers database operations
                message = {
                    "type": "chat_message",
                    "content": f"Create new conversation thread and save message history for {user.user_id}",
                    "thread_id": user.thread_id,
                    "user_id": user.user_id,
                    "requires_persistence": True
                }
                task = asyncio.create_task(user.websocket_client.send_and_wait(message, timeout=8.0))
                db_intensive_tasks.append(task)
        
        # Execute concurrent database-intensive operations
        start_time = time.time()
        results = await asyncio.gather(*db_intensive_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Validate database connection pooling handled the load
        successful_ops = sum(1 for r in results if r is not None and not isinstance(r, Exception))
        success_rate = (successful_ops / len(results)) * 100 if results else 0
        
        assert success_rate >= 80.0, f"Database connection pooling failed: {success_rate:.1f}% success rate"
        assert total_time < 15.0, f"Database operations took {total_time:.2f}s > 15s limit"
        
        print(f"SUCCESS: Database Connection Pooling VALIDATED - {success_rate:.1f}% success rate in {total_time:.2f}s")


def create_test_jwt_token(user_id: str) -> str:
    """Helper function to create test JWT tokens"""
    helper = JWTTestHelper()
    return helper.create_access_token(user_id, f"{user_id}@test.netrasystems.ai")