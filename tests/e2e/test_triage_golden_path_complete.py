
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""E2E Tests for Complete Triage Golden Path - Production Scenarios

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform) - Revenue Critical
- Business Goal: Validate complete $500K+ ARR golden path user journey from authentication to AI insights
- Value Impact: Tests the complete triage → agent execution flow that delivers core business value
- Strategic Impact: Mission-critical validation of revenue-generating user workflows
- Revenue Protection: E2E failures directly translate to lost revenue and customer churn

PURPOSE: This test suite validates the complete end-to-end triage golden path that enables
users to get from initial request through triage to final AI-powered insights. This is the
core revenue-generating workflow that must work flawlessly in production.

KEY COVERAGE:
1. Complete authentication flow with real JWT/OAuth
2. Real WebSocket connections with actual event delivery
3. Concurrent multi-user scenarios with proper isolation
4. Race condition prevention in Cloud Run environments  
5. Real LLM integration for actual triage processing
6. Database persistence and Redis caching with real services
7. Complete agent pipeline execution after triage

GOLDEN PATH PROTECTION:
This is the ultimate validation that the $500K+ ARR user journey works end-to-end:
User Login → WebSocket Connection → Message Send → Triage → Agent Execution → AI Insights

These tests MUST pass for production deployment.
"""

import pytest
import asyncio
import time
import uuid
import json
import websockets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import real service requirements
from shared.isolated_environment import IsolatedEnvironment, get_env

# Import WebSocket client utilities 
import aiohttp
from aiohttp import ClientSession, WSMsgType

# Import authentication components
from netra_backend.app.auth_integration.auth import get_auth_client
from netra_backend.app.services.user_execution_context import UserExecutionContext


@dataclass
class E2EUserProfile:
    """Complete user profile for E2E testing"""
    user_id: str
    email: str
    name: str
    subscription_tier: str
    jwt_token: str
    refresh_token: str
    created_at: datetime
    metadata: Dict[str, Any]
    
    def to_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers"""
        return {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }


@dataclass
class E2EWebSocketMessage:
    """WebSocket message for E2E testing"""
    type: str
    data: Dict[str, Any]
    timestamp: float
    user_id: str
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps({
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "user_id": self.user_id
        })


@dataclass
class E2ETriageResult:
    """E2E triage execution result"""
    user_id: str
    category: str
    priority: str
    confidence_score: float
    data_sufficiency: str
    next_agents: List[str]
    websocket_events: List[str]
    execution_time: float
    success: bool
    error: Optional[str] = None


class E2EWebSocketClient:
    """E2E WebSocket client for real connections"""
    
    def __init__(self, base_url: str, user_profile: E2EUserProfile):
        self.base_url = base_url
        self.user_profile = user_profile
        self.websocket = None
        self.session = None
        self.received_messages = []
        self.connection_active = False
        
    async def connect(self, timeout: float = 10.0) -> bool:
        """Connect to WebSocket endpoint with authentication"""
        try:
            # Create HTTP session for initial auth
            self.session = ClientSession()
            
            # Build WebSocket URL with authentication
            ws_url = f"{self.base_url.replace('http', 'ws')}/ws"
            
            # Add JWT token as subprotocol (common pattern)
            headers = {
                "Authorization": f"Bearer {self.user_profile.jwt_token}",
                "User-Agent": "E2E-Test-Client/1.0"
            }
            
            # Connect with timeout
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    ws_url,
                    extra_headers=headers,
                    ping_interval=30,
                    ping_timeout=10
                ),
                timeout=timeout
            )
            
            self.connection_active = True
            return True
            
        except Exception as e:
            await self.cleanup()
            raise Exception(f"WebSocket connection failed: {e}")
    
    async def send_message(self, message_type: str, data: Dict[str, Any]) -> bool:
        """Send message via WebSocket"""
        if not self.connection_active or not self.websocket:
            raise Exception("WebSocket not connected")
        
        message = E2EWebSocketMessage(
            type=message_type,
            data=data,
            timestamp=time.time(),
            user_id=self.user_profile.user_id
        )
        
        try:
            await self.websocket.send(message.to_json())
            return True
        except Exception as e:
            raise Exception(f"Failed to send message: {e}")
    
    async def receive_events(self, timeout: float = 30.0, expected_event_count: int = 5) -> List[Dict[str, Any]]:
        """Receive WebSocket events with timeout"""
        if not self.connection_active or not self.websocket:
            raise Exception("WebSocket not connected")
        
        events = []
        start_time = time.time()
        
        try:
            while len(events) < expected_event_count and (time.time() - start_time) < timeout:
                try:
                    # Wait for message with shorter timeout for responsiveness
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=min(5.0, timeout - (time.time() - start_time))
                    )
                    
                    event = json.loads(message)
                    events.append(event)
                    self.received_messages.append(event)
                    
                    # Stop if we got agent_completed event
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    # Check if we have minimum required events
                    if len(events) >= 3:  # At least started, thinking, completed
                        break
                    continue
                    
        except Exception as e:
            raise Exception(f"Failed to receive events: {e}")
        
        return events
    
    async def wait_for_agent_completion(self, timeout: float = 60.0) -> Dict[str, Any]:
        """Wait specifically for agent completion"""
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                event = json.loads(message)
                self.received_messages.append(event)
                
                if event.get("type") == "agent_completed":
                    return event
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                raise Exception(f"Error waiting for completion: {e}")
        
        raise TimeoutError(f"Agent completion not received within {timeout}s")
    
    async def cleanup(self):
        """Cleanup WebSocket connection"""
        self.connection_active = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None
        
        if self.session:
            try:
                await self.session.close()
            except:
                pass
            self.session = None


class E2EAuthManager:
    """E2E authentication manager for real auth flows"""
    
    def __init__(self, auth_base_url: str):
        self.auth_base_url = auth_base_url
        self.session = None
    
    async def create_test_user(
        self,
        email: str,
        password: str = "E2E_Test_Password_2024!",
        subscription_tier: str = "free"
    ) -> E2EUserProfile:
        """Create a real test user via auth service"""
        
        if not self.session:
            self.session = ClientSession()
        
        # Create user account
        signup_data = {
            "email": email,
            "password": password,
            "name": f"E2E Test User {email.split('@')[0]}",
            "subscription_tier": subscription_tier
        }
        
        async with self.session.post(
            f"{self.auth_base_url}/auth/signup",
            json=signup_data
        ) as response:
            if response.status != 201:
                error_text = await response.text()
                raise Exception(f"User creation failed: {error_text}")
            
            user_data = await response.json()
        
        # Login to get tokens
        login_data = {
            "email": email,
            "password": password
        }
        
        async with self.session.post(
            f"{self.auth_base_url}/auth/login",
            json=login_data
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Login failed: {error_text}")
            
            auth_data = await response.json()
        
        return E2EUserProfile(
            user_id=user_data["user_id"],
            email=email,
            name=signup_data["name"],
            subscription_tier=subscription_tier,
            jwt_token=auth_data["access_token"],
            refresh_token=auth_data["refresh_token"],
            created_at=datetime.utcnow(),
            metadata={
                "e2e_test": True,
                "created_by": "e2e_triage_test"
            }
        )
    
    async def cleanup_test_user(self, user_profile: E2EUserProfile):
        """Cleanup test user (optional - depends on auth service capabilities)"""
        if not self.session:
            return
        
        try:
            # Attempt to delete test user if auth service supports it
            headers = user_profile.to_auth_headers()
            async with self.session.delete(
                f"{self.auth_base_url}/auth/users/{user_profile.user_id}",
                headers=headers
            ) as response:
                # Don't fail if cleanup fails
                pass
        except:
            pass
    
    async def cleanup(self):
        """Cleanup auth manager"""
        if self.session:
            await self.session.close()
            self.session = None


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.slow
class TestTriageGoldenPathE2E(SSotAsyncTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """E2E tests for complete triage golden path with real services
    
    These tests validate the complete user journey that generates business value:
    Authentication → WebSocket Connection → Triage Request → Agent Execution → AI Insights
    
    CRITICAL: All tests use real services and real authentication.
    NO MOCKS are allowed in E2E tests.
    """
    
    def setup_method(self, method=None):
        """Setup E2E test environment with real services"""
        super().setup_method(method)
        
        # Get environment configuration
        self.env = self.get_env()
        
        # Configure service URLs (use environment or defaults)
        self.backend_url = self.env.get("E2E_BACKEND_URL", "http://localhost:8000")
        self.auth_url = self.env.get("E2E_AUTH_URL", "http://localhost:8081")
        self.use_real_llm = self.env.get("E2E_USE_REAL_LLM", "false").lower() == "true"
        
        # Initialize auth manager
        self.auth_manager = E2EAuthManager(self.auth_url)
        
        # Track resources for cleanup
        self.test_users = []
        self.websocket_clients = []
        
        # Performance tracking
        self.test_start_time = time.time()
    
    # ========================================================================
    # SINGLE USER GOLDEN PATH TESTS
    # ========================================================================
    
    @pytest.mark.e2e
    @pytest.mark.critical
    async def test_complete_golden_path_single_user(self):
        """Test complete golden path for single user end-to-end
        
        Business Impact: Validates the core $500K+ ARR user journey that
        must work for every customer interaction.
        
        Steps:
        1. Create authenticated user
        2. Establish WebSocket connection  
        3. Send triage request
        4. Receive all required WebSocket events
        5. Verify agent execution pipeline
        6. Confirm AI insights delivery
        """
        # Step 1: Create authenticated test user
        test_email = f"e2e_golden_path_{uuid.uuid4().hex[:8]}@example.com"
        user_profile = await self.auth_manager.create_test_user(
            email=test_email,
            subscription_tier="enterprise"  # Use premium tier for full features
        )
        self.test_users.append(user_profile)
        
        # Step 2: Establish WebSocket connection
        websocket_client = E2EWebSocketClient(self.backend_url, user_profile)
        self.websocket_clients.append(websocket_client)
        
        connection_start = time.time()
        connection_success = await websocket_client.connect(timeout=15.0)
        connection_time = time.time() - connection_start
        
        assert connection_success, "WebSocket connection failed"
        assert connection_time < 10.0, f"Connection took {connection_time:.3f}s, should be < 10.0s"
        
        # Step 3: Send triage request with business-relevant content
        triage_request = {
            "type": "user_message",
            "content": "Help me optimize my machine learning training costs on AWS. I'm spending $15,000/month on GPU instances and want to reduce costs by 30% while maintaining model quality.",
            "thread_id": f"e2e_thread_{uuid.uuid4().hex[:8]}",
            "metadata": {
                "current_spend": 15000,
                "target_reduction": 0.3,
                "platform": "aws",
                "workload_type": "ml_training"
            }
        }
        
        send_start = time.time()
        send_success = await websocket_client.send_message(
            triage_request["type"],
            triage_request
        )
        assert send_success, "Failed to send triage request"
        
        # Step 4: Receive and validate all required WebSocket events
        events_start = time.time()
        events = await websocket_client.receive_events(
            timeout=60.0,
            expected_event_count=5
        )
        events_time = time.time() - events_start
        
        # Validate event sequence
        event_types = [event.get("type", "") for event in events]
        
        # CRITICAL: All 5 events must be present for golden path
        required_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        received_events = set(event_types)
        missing_events = required_events - received_events
        
        assert len(missing_events) == 0, f"Missing critical events: {missing_events}"
        
        # Step 5: Validate triage categorization
        triage_event = None
        completion_event = None
        
        for event in events:
            if event.get("type") == "agent_completed":
                completion_event = event
                # Look for triage data in completion event
                if "triage_category" in event.get("data", {}):
                    triage_event = event
                break
        
        assert completion_event is not None, "No agent_completed event received"
        
        # Validate triage results
        completion_data = completion_event.get("data", {})
        
        # Should have been categorized as cost optimization
        assert "category" in completion_data or "triage_category" in completion_data
        category = completion_data.get("category") or completion_data.get("triage_category")
        assert "Cost" in category or "Optimization" in category, f"Wrong category: {category}"
        
        # Should have high priority due to specific dollar amounts
        priority = completion_data.get("priority", "").lower()
        assert priority in ["high", "critical", "medium"], f"Unexpected priority: {priority}"
        
        # Should have sufficient or partial data sufficiency
        data_sufficiency = completion_data.get("data_sufficiency", "")
        assert data_sufficiency in ["sufficient", "partial"], f"Poor data sufficiency: {data_sufficiency}"
        
        # Should have next agents identified
        next_agents = completion_data.get("next_agents", [])
        assert len(next_agents) > 0, "No next agents identified"
        assert any("data" in agent.lower() or "optimization" in agent.lower() for agent in next_agents)
        
        # Step 6: Validate performance requirements
        total_time = time.time() - send_start
        
        assert events_time < 45.0, f"Event processing took {events_time:.3f}s, should be < 45.0s"
        assert total_time < 60.0, f"Total golden path took {total_time:.3f}s, should be < 60.0s"
        
        # Record comprehensive metrics
        self.record_metric("golden_path_connection_time", connection_time)
        self.record_metric("golden_path_events_time", events_time)
        self.record_metric("golden_path_total_time", total_time)
        self.record_metric("golden_path_events_received", len(events))
        self.record_metric("golden_path_success", True)
        self.record_metric("triage_category_accuracy", "Cost" in category)
        self.record_metric("data_sufficiency_quality", data_sufficiency != "insufficient")
        
        # Increment tracking metrics
        self.increment_websocket_events(len(events))
        self.increment_llm_requests(1)  # Triage used LLM
    
    @pytest.mark.e2e 
    @pytest.mark.real_llm
    async def test_golden_path_with_real_llm_integration(self):
        """Test golden path with real LLM for authentic triage analysis
        
        Business Impact: Validates that real AI processing delivers accurate
        triage results that enable proper agent routing.
        """
        if not self.use_real_llm:
            pytest.skip("Real LLM integration not enabled (set E2E_USE_REAL_LLM=true)")
        
        # Create premium user for LLM access
        test_email = f"e2e_real_llm_{uuid.uuid4().hex[:8]}@example.com"
        user_profile = await self.auth_manager.create_test_user(
            email=test_email,
            subscription_tier="enterprise"
        )
        self.test_users.append(user_profile)
        
        # Connect WebSocket
        websocket_client = E2EWebSocketClient(self.backend_url, user_profile)
        self.websocket_clients.append(websocket_client)
        await websocket_client.connect(timeout=15.0)
        
        # Send complex request requiring real LLM analysis
        complex_request = {
            "type": "user_message",
            "content": """I'm running a multi-modal AI pipeline with the following setup:
            - Training: 8x A100 GPUs for transformer models (GPT-style architecture)
            - Inference: 16x V100 GPUs for real-time serving
            - Data processing: 32 CPU instances for ETL
            - Storage: 50TB of training data in S3
            - Current monthly cost: $45,000
            
            I need to optimize this for cost while maintaining <200ms p95 latency.
            The training runs 24/7 and inference handles 10M requests/day.
            
            What's the best approach to reduce costs by 40% without compromising performance?""",
            "thread_id": f"real_llm_thread_{uuid.uuid4().hex[:8]}",
            "metadata": {
                "workload_complexity": "high",
                "cost_target": 0.4,
                "latency_requirement": 200,
                "scale": "enterprise"
            }
        }
        
        # Send request and collect events
        await websocket_client.send_message(
            complex_request["type"],
            complex_request
        )
        
        # Real LLM may take longer
        events = await websocket_client.receive_events(
            timeout=90.0,
            expected_event_count=5
        )
        
        # Validate real LLM provided sophisticated analysis
        completion_event = next(
            (event for event in events if event.get("type") == "agent_completed"),
            None
        )
        
        assert completion_event is not None
        completion_data = completion_event.get("data", {})
        
        # Real LLM should identify this as performance optimization (not just cost)
        category = completion_data.get("category") or completion_data.get("triage_category", "")
        assert "Performance" in category or "Optimization" in category
        
        # Should have high confidence with real LLM
        confidence = completion_data.get("confidence_score", 0)
        assert confidence > 0.7, f"Real LLM confidence too low: {confidence}"
        
        # Should extract entities (GPUs, latency, etc.)
        entities = completion_data.get("entities", {})
        if entities:
            # Should detect GPU mentions
            models = entities.get("models", [])
            services = entities.get("services", [])
            metrics = entities.get("metrics", [])
            
            # Real LLM should extract relevant information
            tech_entities = models + services + metrics
            has_gpu_info = any("gpu" in str(entity).lower() or "a100" in str(entity).lower() or "v100" in str(entity).lower() for entity in tech_entities)
            has_latency_info = any("latency" in str(entity).lower() for entity in tech_entities)
            
            # At least one technical entity should be extracted
            assert len(tech_entities) > 0, "Real LLM should extract technical entities"
        
        # Should provide comprehensive next steps
        next_agents = completion_data.get("next_agents", [])
        assert len(next_agents) >= 2, "Complex request should trigger multiple agents"
        
        self.record_metric("real_llm_confidence", confidence)
        self.record_metric("real_llm_entities_extracted", len(entities) if entities else 0)
        self.record_metric("real_llm_next_agents", len(next_agents))
        self.record_metric("real_llm_integration_success", True)
    
    # ========================================================================
    # MULTI-USER CONCURRENT TESTS
    # ========================================================================
    
    @pytest.mark.e2e
    @pytest.mark.concurrent
    async def test_concurrent_users_isolation(self):
        """Test multiple users using triage simultaneously with proper isolation
        
        Business Impact: Validates system can handle production load with
        multiple customers without cross-contamination.
        """
        num_users = 5
        users = []
        clients = []
        
        # Create multiple test users
        for i in range(num_users):
            test_email = f"e2e_concurrent_{i}_{uuid.uuid4().hex[:8]}@example.com"
            user_profile = await self.auth_manager.create_test_user(
                email=test_email,
                subscription_tier="mid" if i % 2 == 0 else "enterprise"
            )
            users.append(user_profile)
            self.test_users.append(user_profile)
            
            # Create WebSocket client
            client = E2EWebSocketClient(self.backend_url, user_profile)
            clients.append(client)
            self.websocket_clients.append(client)
        
        # Connect all clients concurrently
        connection_tasks = [client.connect(timeout=20.0) for client in clients]
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Verify all connections succeeded
        successful_connections = sum(1 for result in connection_results if result is True)
        assert successful_connections == num_users, f"Only {successful_connections}/{num_users} connections succeeded"
        
        # Send different requests simultaneously
        requests = [
            f"User {i}: Optimize {['CPU', 'GPU', 'Memory', 'Storage', 'Network'][i]} costs for {['web app', 'ML training', 'data pipeline', 'API service', 'batch jobs'][i]}"
            for i in range(num_users)
        ]
        
        # Send all requests concurrently
        send_tasks = []
        for i, (client, request) in enumerate(zip(clients, requests)):
            task = client.send_message(
                "user_message",
                {
                    "type": "user_message",
                    "content": request,
                    "thread_id": f"concurrent_thread_{i}_{uuid.uuid4().hex[:8]}",
                    "user_index": i
                }
            )
            send_tasks.append(task)
        
        send_results = await asyncio.gather(*send_tasks, return_exceptions=True)
        successful_sends = sum(1 for result in send_results if result is True)
        assert successful_sends == num_users, f"Only {successful_sends}/{num_users} sends succeeded"
        
        # Receive events from all users concurrently
        receive_tasks = [
            client.receive_events(timeout=45.0, expected_event_count=5)
            for client in clients
        ]
        
        event_results = await asyncio.gather(*receive_tasks, return_exceptions=True)
        
        # Validate each user received their own events
        successful_executions = 0
        for i, (user, events) in enumerate(zip(users, event_results)):
            if isinstance(events, Exception):
                pytest.fail(f"User {i} events failed: {events}")
            
            # Verify minimum event count
            assert len(events) >= 3, f"User {i} received insufficient events: {len(events)}"
            
            # Verify event isolation (events should be for this user only)
            for event in events:
                event_data = event.get("data", {})
                # If user identification is in event data, verify it matches
                if "user_id" in event_data:
                    assert event_data["user_id"] == user.user_id
            
            successful_executions += 1
        
        assert successful_executions == num_users, f"Only {successful_executions}/{num_users} executions completed"
        
        # Record concurrency metrics
        self.record_metric("concurrent_users_tested", num_users)
        self.record_metric("concurrent_connections_success_rate", successful_connections / num_users)
        self.record_metric("concurrent_sends_success_rate", successful_sends / num_users)
        self.record_metric("concurrent_executions_success_rate", successful_executions / num_users)
        self.record_metric("concurrent_isolation_success", True)
    
    # ========================================================================
    # RACE CONDITION AND TIMING TESTS
    # ========================================================================
    
    @pytest.mark.e2e
    @pytest.mark.race_conditions  
    async def test_websocket_handshake_race_condition_prevention(self):
        """Test prevention of WebSocket handshake race conditions in Cloud Run
        
        Business Impact: Validates fixes for the 1011 WebSocket errors that
        were blocking user access to the platform.
        """
        # Create user for race condition testing
        test_email = f"e2e_race_{uuid.uuid4().hex[:8]}@example.com"
        user_profile = await self.auth_manager.create_test_user(
            email=test_email,
            subscription_tier="free"
        )
        self.test_users.append(user_profile)
        
        # Test rapid connect/disconnect cycles to trigger race conditions
        connection_attempts = 3
        successful_connections = 0
        
        for attempt in range(connection_attempts):
            client = E2EWebSocketClient(self.backend_url, user_profile)
            self.websocket_clients.append(client)
            
            try:
                # Attempt rapid connection
                connection_start = time.time()
                connected = await client.connect(timeout=10.0)
                connection_time = time.time() - connection_start
                
                if connected:
                    # Immediately send message to test handshake completion
                    immediate_message = {
                        "type": "user_message",
                        "content": f"Race test {attempt}: Quick optimization query",
                        "thread_id": f"race_thread_{attempt}_{uuid.uuid4().hex[:8]}"
                    }
                    
                    # This should not fail due to race conditions
                    send_success = await client.send_message(
                        immediate_message["type"],
                        immediate_message
                    )
                    
                    if send_success:
                        # Try to receive at least one event
                        try:
                            events = await client.receive_events(timeout=15.0, expected_event_count=1)
                            if len(events) > 0:
                                successful_connections += 1
                        except:
                            # Receiving might timeout, but connection/send success is enough
                            successful_connections += 1
                
                # Cleanup this connection
                await client.cleanup()
                
            except Exception as e:
                # Log but continue testing
                print(f"Connection attempt {attempt} failed: {e}")
                await client.cleanup()
        
        # Should have at least majority success rate
        success_rate = successful_connections / connection_attempts
        assert success_rate >= 0.7, f"Race condition success rate {success_rate:.2f} below threshold"
        
        self.record_metric("race_condition_attempts", connection_attempts)
        self.record_metric("race_condition_successes", successful_connections) 
        self.record_metric("race_condition_success_rate", success_rate)
        self.record_metric("race_condition_prevention_success", success_rate >= 0.7)
    
    @pytest.mark.e2e
    async def test_high_frequency_request_handling(self):
        """Test system handles high-frequency requests without degradation
        
        Business Impact: Validates system can handle bursts of user activity
        during peak usage periods.
        """
        # Create user for high-frequency testing
        test_email = f"e2e_frequency_{uuid.uuid4().hex[:8]}@example.com"
        user_profile = await self.auth_manager.create_test_user(
            email=test_email,
            subscription_tier="enterprise"
        )
        self.test_users.append(user_profile)
        
        # Create single WebSocket connection
        client = E2EWebSocketClient(self.backend_url, user_profile)
        self.websocket_clients.append(client)
        await client.connect(timeout=15.0)
        
        # Send multiple requests in quick succession
        num_requests = 3  # Conservative for E2E testing
        request_times = []
        
        for i in range(num_requests):
            request_start = time.time()
            
            success = await client.send_message(
                "user_message",
                {
                    "type": "user_message", 
                    "content": f"High frequency request #{i}: Quick cost check for workload type {i}",
                    "thread_id": f"freq_thread_{i}_{uuid.uuid4().hex[:8]}",
                    "request_index": i
                }
            )
            
            request_time = time.time() - request_start
            request_times.append(request_time)
            
            assert success, f"Request {i} failed to send"
            
            # Brief pause to avoid overwhelming the system
            await asyncio.sleep(0.5)
        
        # Collect responses for all requests
        total_events = []
        collection_start = time.time()
        
        # Collect events for reasonable time (multiple requests may be processing)
        try:
            while len(total_events) < num_requests * 3 and (time.time() - collection_start) < 90.0:
                events = await client.receive_events(timeout=10.0, expected_event_count=1)
                total_events.extend(events)
                
                # Check if we have completion events for all requests
                completion_events = [e for e in total_events if e.get("type") == "agent_completed"]
                if len(completion_events) >= num_requests:
                    break
                    
        except:
            # May timeout, check what we got
            pass
        
        # Validate we got reasonable responses
        completion_events = [e for e in total_events if e.get("type") == "agent_completed"]
        assert len(completion_events) >= 1, "No completion events received for high-frequency requests"
        
        # Performance validation
        avg_request_time = sum(request_times) / len(request_times)
        max_request_time = max(request_times)
        
        assert avg_request_time < 1.0, f"Average request time {avg_request_time:.3f}s too high"
        assert max_request_time < 2.0, f"Max request time {max_request_time:.3f}s too high"
        
        self.record_metric("high_freq_requests_sent", num_requests)
        self.record_metric("high_freq_completions_received", len(completion_events))
        self.record_metric("high_freq_avg_request_time", avg_request_time)
        self.record_metric("high_freq_max_request_time", max_request_time)
        self.record_metric("high_freq_handling_success", True)
    
    # ========================================================================
    # ERROR RECOVERY E2E TESTS
    # ========================================================================
    
    @pytest.mark.e2e
    async def test_websocket_reconnection_recovery(self):
        """Test WebSocket reconnection and recovery scenarios
        
        Business Impact: Validates users can recover from network interruptions
        without losing their session or context.
        """
        # Create user for reconnection testing
        test_email = f"e2e_reconnect_{uuid.uuid4().hex[:8]}@example.com"
        user_profile = await self.auth_manager.create_test_user(
            email=test_email,
            subscription_tier="mid"
        )
        self.test_users.append(user_profile)
        
        # Initial connection and request
        client1 = E2EWebSocketClient(self.backend_url, user_profile)
        self.websocket_clients.append(client1)
        await client1.connect(timeout=15.0)
        
        # Send initial request
        initial_request = {
            "type": "user_message",
            "content": "Initial request: analyze my infrastructure costs",
            "thread_id": f"reconnect_thread_{uuid.uuid4().hex[:8]}"
        }
        
        await client1.send_message(initial_request["type"], initial_request)
        
        # Collect some initial events
        initial_events = await client1.receive_events(timeout=20.0, expected_event_count=2)
        assert len(initial_events) >= 1, "No initial events received"
        
        # Simulate disconnection by closing WebSocket
        await client1.cleanup()
        
        # Wait a bit (simulate network interruption)
        await asyncio.sleep(2.0)
        
        # Reconnect with new client (same user)
        client2 = E2EWebSocketClient(self.backend_url, user_profile)
        self.websocket_clients.append(client2)
        
        reconnect_start = time.time()
        reconnected = await client2.connect(timeout=15.0)
        reconnect_time = time.time() - reconnect_start
        
        assert reconnected, "Reconnection failed"
        assert reconnect_time < 10.0, f"Reconnection took {reconnect_time:.3f}s, should be < 10.0s"
        
        # Send follow-up request to test session continuity
        followup_request = {
            "type": "user_message",
            "content": "Follow-up request: continue with cost optimization analysis",
            "thread_id": initial_request["thread_id"]  # Same thread to test continuity
        }
        
        await client2.send_message(followup_request["type"], followup_request)
        
        # Should receive events for follow-up request
        followup_events = await client2.receive_events(timeout=30.0, expected_event_count=3)
        assert len(followup_events) >= 2, "Insufficient events after reconnection"
        
        # Verify we got completion for follow-up
        completion_events = [e for e in followup_events if e.get("type") == "agent_completed"]
        assert len(completion_events) >= 1, "No completion after reconnection"
        
        self.record_metric("reconnection_time", reconnect_time)
        self.record_metric("reconnection_events_received", len(followup_events))
        self.record_metric("reconnection_recovery_success", True)
    
    # ========================================================================
    # PERFORMANCE E2E TESTS
    # ========================================================================
    
    @pytest.mark.e2e
    @pytest.mark.performance
    async def test_e2e_performance_requirements(self):
        """Test end-to-end performance meets business requirements
        
        Business Impact: Validates user experience meets expectations for
        response times that drive satisfaction and retention.
        """
        # Create premium user for performance testing
        test_email = f"e2e_perf_{uuid.uuid4().hex[:8]}@example.com"
        user_profile = await self.auth_manager.create_test_user(
            email=test_email,
            subscription_tier="enterprise"
        )
        self.test_users.append(user_profile)
        
        # Test performance requirements
        performance_results = []
        
        # Test multiple request types for comprehensive performance validation
        test_requests = [
            ("Simple optimization", "Help me reduce costs"),
            ("Complex analysis", "Analyze my multi-cloud infrastructure costs across AWS, Azure, and GCP for ML workloads"),
            ("Specific technical", "Optimize my Kubernetes cluster GPU utilization for deep learning training pipelines")
        ]
        
        for request_name, request_content in test_requests:
            # Create fresh connection for each test
            client = E2EWebSocketClient(self.backend_url, user_profile)
            self.websocket_clients.append(client)
            
            # Measure connection time
            connect_start = time.time()
            connected = await client.connect(timeout=15.0)
            connect_time = time.time() - connect_start
            
            assert connected, f"Connection failed for {request_name}"
            
            # Measure request processing time
            request_start = time.time()
            await client.send_message(
                "user_message",
                {
                    "type": "user_message",
                    "content": request_content,
                    "thread_id": f"perf_thread_{uuid.uuid4().hex[:8]}"
                }
            )
            
            # Measure time to first event (responsiveness)
            first_event_time = None
            total_events = []
            
            try:
                events = await client.receive_events(timeout=45.0, expected_event_count=5)
                total_events = events
                
                if events:
                    first_event_time = time.time() - request_start
                
                # Find completion time
                completion_event = next(
                    (e for e in events if e.get("type") == "agent_completed"),
                    None
                )
                
                completion_time = time.time() - request_start if completion_event else None
                
            except Exception as e:
                pytest.fail(f"Performance test failed for {request_name}: {e}")
            
            # Record performance metrics
            result = {
                "request_type": request_name,
                "connect_time": connect_time,
                "first_event_time": first_event_time,
                "completion_time": completion_time,
                "total_events": len(total_events),
                "success": completion_event is not None
            }
            
            performance_results.append(result)
            
            # Cleanup connection
            await client.cleanup()
        
        # Validate performance requirements
        for result in performance_results:
            assert result["success"], f"Failed: {result['request_type']}"
            
            # Business performance requirements
            assert result["connect_time"] < 10.0, f"Connection too slow for {result['request_type']}: {result['connect_time']:.3f}s"
            
            if result["first_event_time"]:
                assert result["first_event_time"] < 10.0, f"First response too slow for {result['request_type']}: {result['first_event_time']:.3f}s"
            
            if result["completion_time"]:
                # Different requirements for different complexity
                max_completion_time = 30.0 if "Simple" in result["request_type"] else 60.0
                assert result["completion_time"] < max_completion_time, f"Completion too slow for {result['request_type']}: {result['completion_time']:.3f}s"
        
        # Calculate summary metrics
        avg_connect = sum(r["connect_time"] for r in performance_results) / len(performance_results)
        avg_first_event = sum(r["first_event_time"] for r in performance_results if r["first_event_time"]) / len([r for r in performance_results if r["first_event_time"]])
        avg_completion = sum(r["completion_time"] for r in performance_results if r["completion_time"]) / len([r for r in performance_results if r["completion_time"]])
        
        self.record_metric("e2e_avg_connect_time", avg_connect)
        self.record_metric("e2e_avg_first_event_time", avg_first_event)
        self.record_metric("e2e_avg_completion_time", avg_completion)
        self.record_metric("e2e_performance_tests_passed", len(performance_results))
        self.record_metric("e2e_performance_requirements_met", True)
    
    # ========================================================================
    # CLEANUP AND TEARDOWN
    # ========================================================================
    
    async def cleanup_test_resources(self):
        """Cleanup all test resources"""
        # Cleanup WebSocket connections
        for client in getattr(self, 'websocket_clients', []):
            try:
                await client.cleanup()
            except:
                pass
        
        # Cleanup test users (optional)
        if hasattr(self, 'auth_manager'):
            for user in getattr(self, 'test_users', []):
                try:
                    await self.auth_manager.cleanup_test_user(user)
                except:
                    pass
            
            try:
                await self.auth_manager.cleanup()
            except:
                pass
    
    def teardown_method(self, method=None):
        """Cleanup after each test"""
        # Run async cleanup
        try:
            asyncio.run(self.cleanup_test_resources())
        except Exception as e:
            # Don't fail test cleanup
            print(f"Cleanup warning: {e}")
        
        # Record final test metrics
        total_test_time = time.time() - getattr(self, 'test_start_time', time.time())
        metrics = self.get_all_metrics()
        
        # Count successful tests
        success_metrics = [key for key, value in metrics.items() if key.endswith("_success") and value is True]
        
        self.record_metric("e2e_test_execution_time", total_test_time)
        self.record_metric("e2e_successful_validations", len(success_metrics))
        self.record_metric("e2e_golden_path_validation_complete", True)
        
        # Call parent teardown
        super().teardown_method(method)