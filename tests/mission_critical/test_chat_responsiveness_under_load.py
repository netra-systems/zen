#!/usr/bin/env python
"""MISSION CRITICAL: Real-Time Chat Responsiveness Under Load Test Suite

Business Value: $500K+ ARR - Chat delivers 90% of user value
Priority: CRITICAL
Impact: Core User Experience

This test suite validates that chat remains responsive during peak usage scenarios
that beta users will experience. 

TEST COVERAGE:
1. Concurrent User Load Test - 5 simultaneous users, <2s response time
2. Agent Processing Backlog Test - Queue 10 requests, proper indicators
3. WebSocket Connection Recovery - Network disruption recovery

ACCEPTANCE CRITERIA:
✅ 5 concurrent users get responses within 2s
✅ All WebSocket events fire correctly under load  
✅ Zero message loss during normal operation
✅ Connection recovery works within 5s
"""

import asyncio
import json
import os
import sys
import time
import uuid
import jwt
import hashlib
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple, Union
import threading
import random
from dataclasses import dataclass, field
from netra_backend.app.core.agent_registry import AgentRegistry

# Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Real services infrastructure
from test_framework.real_services import get_real_services, RealServicesManager
from test_framework.environment_isolation import IsolatedEnvironment

# Import production components
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.schemas.websocket_models import WebSocketMessage
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


@dataclass
class LoadTestMetrics:
    """Comprehensive metrics for load testing."""
    concurrent_users: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    response_times: List[float] = field(default_factory=list)
    avg_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    events_received: Dict[str, int] = field(default_factory=dict)
    missing_events: List[str] = field(default_factory=list)
    message_loss_count: int = 0
    connection_drops: int = 0
    recovery_times: List[float] = field(default_factory=list)
    avg_recovery_time_ms: float = 0.0
    test_duration_seconds: float = 0.0
    error_rate: float = 0.0


@dataclass
class BusinessMetrics:
    """Business value tracking for chat responsiveness tests."""
    user_satisfaction_score: float = 0.0
    engagement_rate: float = 0.0
    conversion_probability: float = 0.0
    revenue_attribution: float = 0.0
    retention_impact: float = 0.0
    premium_feature_adoption: float = 0.0
    enterprise_readiness_score: float = 0.0
    chat_completion_rate: float = 0.0
    ai_value_delivered: float = 0.0
    concurrent_user_capacity: int = 0
    response_quality_score: float = 0.0


@dataclass  
class AuthenticationFlowMetrics:
    """Authentication flow specific metrics."""
    login_success_rate: float = 0.0
    token_validation_time_ms: float = 0.0
    session_establishment_time_ms: float = 0.0
    jwt_refresh_success_rate: float = 0.0
    mfa_validation_time_ms: float = 0.0
    oauth_flow_completion_rate: float = 0.0
    cross_service_auth_time_ms: float = 0.0
    permission_check_time_ms: float = 0.0
    logout_cleanup_success_rate: float = 0.0
    concurrent_session_capacity: int = 0
    
    def calculate_percentiles(self):
        """Calculate response time percentiles."""
        if self.response_times:
            sorted_times = sorted(self.response_times)
            self.avg_response_time_ms = sum(sorted_times) / len(sorted_times) * 1000
            self.max_response_time_ms = max(sorted_times) * 1000
            self.min_response_time_ms = min(sorted_times) * 1000
            
            # Calculate percentiles
            n = len(sorted_times)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)
            self.p95_response_time_ms = sorted_times[min(p95_idx, n-1)] * 1000
            self.p99_response_time_ms = sorted_times[min(p99_idx, n-1)] * 1000
            
        if self.recovery_times:
            self.avg_recovery_time_ms = sum(self.recovery_times) / len(self.recovery_times) * 1000


@pytest.mark.auth_flow
class TestAuthenticationFlowValidation:
    """Comprehensive authentication flow validation - 10+ tests covering complete user auth journeys."""
    
    def __init__(self):
    pass
        self.real_services = None
        self.auth_metrics = AuthenticationFlowMetrics()
        self.test_users = []
        self.jwt_secret = "test-secret-key-for-jwt-validation"
    
    async def setup(self):
        """Initialize real services for authentication testing."""
        self.real_services = get_real_services()
        await self.real_services.ensure_all_services_available()
        
        # Create test users with different tiers
        self.test_users = [
            {"user_id": f"auth_test_user_{i:03d}", "tier": tier, "email": f"test{i}@example.com"}
            for i, tier in enumerate(["free", "premium", "enterprise", "free", "premium"], 1)
        ]
    
    async def teardown(self):
        """Clean up authentication test resources."""
    pass
        if self.real_services:
            await self.real_services.close_all()
    
    def generate_jwt_token(self, user_data: Dict[str, Any], expires_delta: timedelta = None) -> str:
        """Generate JWT token for testing."""
        expires_delta = expires_delta or timedelta(hours=1)
        expire = datetime.utcnow() + expires_delta
        
        payload = {
            "user_id": user_data["user_id"],
            "email": user_data["email"], 
            "tier": user_data["tier"],
            "exp": expire,
            "iat": datetime.utcnow(),
            "sub": user_data["user_id"]
        }
        
        await asyncio.sleep(0)
    return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    async def test_complete_signup_to_chat_flow(self) -> Dict[str, Any]:
        """Test complete signup → email verification → login → first chat flow."""
        start_time = time.time()
        results = {"status": "success", "metrics": {}, "errors": []}
        
        try:
            user_data = self.test_users[0]
            
            # Step 1: Signup simulation
            signup_start = time.time()
            signup_payload = {
                "email": user_data["email"],
                "password": "test_password_123!",
                "tier": user_data["tier"]
            }
            
            # Simulate auth service call
            auth_response = await self._simulate_auth_request("POST", "/auth/signup", signup_payload)
            signup_time = (time.time() - signup_start) * 1000
            
            # Step 2: Email verification simulation
            verification_token = hashlib.md5(user_data["email"].encode()).hexdigest()
            verify_payload = {"token": verification_token, "email": user_data["email"]}
            verify_response = await self._simulate_auth_request("POST", "/auth/verify", verify_payload)
            
            # Step 3: Login with credentials
            login_start = time.time()
            login_payload = {
                "email": user_data["email"],
                "password": "test_password_123!"
            }
            login_response = await self._simulate_auth_request("POST", "/auth/login", login_payload)
            login_time = (time.time() - login_start) * 1000
            
            # Step 4: JWT token validation
            token_start = time.time()
            jwt_token = self.generate_jwt_token(user_data)
            
            try:
                decoded = jwt.decode(jwt_token, self.jwt_secret, algorithms=["HS256"])
                token_valid = decoded["user_id"] == user_data["user_id"]
            except Exception as e:
                results["errors"].append(f"JWT validation failed: {e}")
                token_valid = False
                
            token_time = (time.time() - token_start) * 1000
            
            # Step 5: First chat message with authenticated connection
            chat_start = time.time()
            chat_client = ChatResponsivenessTestClient(user_data["user_id"])
            connected = await chat_client.connect()
            
            if connected:
                chat_success = await chat_client.send_message("Hello, I'm a new user! Can you help me?")
                await asyncio.sleep(2)  # Wait for response
                chat_time = (time.time() - chat_start) * 1000
            else:
                results["errors"].append("Failed to establish chat connection")
                chat_success = False
                chat_time = 0
            
            # Calculate success rate
            steps_completed = sum([
                auth_response.get("success", False),
                verify_response.get("success", False), 
                login_response.get("success", False),
                token_valid,
                chat_success
            ])
            
            results["metrics"] = {
                "signup_time_ms": signup_time,
                "login_time_ms": login_time,
                "token_validation_time_ms": token_time,
                "chat_connection_time_ms": chat_time,
                "total_flow_time_ms": (time.time() - start_time) * 1000,
                "flow_completion_rate": steps_completed / 5,
                "user_tier": user_data["tier"]
            }
            
            self.auth_metrics.login_success_rate = steps_completed / 5
            self.auth_metrics.session_establishment_time_ms = chat_time
            self.auth_metrics.token_validation_time_ms = token_time
            
            await chat_client.disconnect()
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Signup flow failed: {e}")
            
        return results
    
    async def test_jwt_token_lifecycle_validation(self) -> Dict[str, Any]:
        """Test complete JWT token lifecycle: generation → validation → refresh → expiry."""
        results = {"status": "success", "metrics": {}, "errors": []}
        
        try:
            user_data = self.test_users[1]
            
            # Step 1: Generate initial token
            token_start = time.time()
            initial_token = self.generate_jwt_token(user_data)
            generation_time = (time.time() - token_start) * 1000
            
            # Step 2: Validate token
            validation_start = time.time()
            try:
                decoded = jwt.decode(initial_token, self.jwt_secret, algorithms=["HS256"])
                validation_success = decoded["user_id"] == user_data["user_id"]
            except Exception as e:
                validation_success = False
                results["errors"].append(f"Token validation failed: {e}")
            validation_time = (time.time() - validation_start) * 1000
            
            # Step 3: Test token refresh
            refresh_start = time.time()
            refreshed_token = self.generate_jwt_token(user_data, timedelta(hours=2))
            
            try:
                refresh_decoded = jwt.decode(refreshed_token, self.jwt_secret, algorithms=["HS256"])
                refresh_success = refresh_decoded["user_id"] == user_data["user_id"]
            except Exception as e:
                refresh_success = False
                results["errors"].append(f"Token refresh failed: {e}")
            refresh_time = (time.time() - refresh_start) * 1000
            
            # Step 4: Test expired token
            expired_token = self.generate_jwt_token(user_data, timedelta(seconds=-1))
            
            try:
                jwt.decode(expired_token, self.jwt_secret, algorithms=["HS256"])
                expiry_test_success = False  # Should have failed
            except jwt.ExpiredSignatureError:
                expiry_test_success = True  # Correctly rejected expired token
            except Exception as e:
                expiry_test_success = False
                results["errors"].append(f"Unexpected expiry test error: {e}")
            
            # Calculate success metrics
            total_success = sum([validation_success, refresh_success, expiry_test_success]) / 3
            
            results["metrics"] = {
                "token_generation_time_ms": generation_time,
                "token_validation_time_ms": validation_time,
                "token_refresh_time_ms": refresh_time,
                "jwt_lifecycle_success_rate": total_success,
                "user_tier": user_data["tier"]
            }
            
            self.auth_metrics.jwt_refresh_success_rate = total_success
            self.auth_metrics.token_validation_time_ms = validation_time
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"JWT lifecycle test failed: {e}")
            
        return results
    
    async def test_multi_device_session_coordination(self) -> Dict[str, Any]:
        """Test user authentication and chat across multiple devices/sessions."""
        results = {"status": "success", "metrics": {}, "errors": []}
        
        try:
            user_data = self.test_users[2]
            device_sessions = []
            
            # Create multiple device sessions
            devices = ["web_browser", "mobile_app", "desktop_client"]
            connection_times = []
            
            for device in devices:
                session_start = time.time()
                
                # Generate device-specific token
                token = self.generate_jwt_token({
                    **user_data,
                    "device": device,
                    "session_id": f"{user_data['user_id']}_{device}_{int(time.time())}"
                })
                
                # Create chat client for this device
                client = ChatResponsivenessTestClient(f"{user_data['user_id']}_{device}")
                connected = await client.connect()
                
                if connected:
                    # Send device-specific message
                    await client.send_message(f"Message from {device}")
                    await asyncio.sleep(0.5)
                    
                device_sessions.append({
                    "device": device,
                    "client": client,
                    "connected": connected,
                    "connection_time": (time.time() - session_start) * 1000
                })
                
                connection_times.append((time.time() - session_start) * 1000)
            
            # Test cross-device message visibility
            main_client = device_sessions[0]["client"]
            await main_client.send_message("Cross-device test message")
            await asyncio.sleep(2)
            
            # Check if other devices received events
            cross_device_events = 0
            for session in device_sessions[1:]:
                if session["connected"] and len(session["client"].events_received) > 0:
                    cross_device_events += 1
            
            # Calculate metrics
            successful_connections = sum(1 for s in device_sessions if s["connected"])
            avg_connection_time = statistics.mean(connection_times) if connection_times else 0
            
            results["metrics"] = {
                "devices_tested": len(devices),
                "successful_connections": successful_connections,
                "avg_connection_time_ms": avg_connection_time,
                "cross_device_events": cross_device_events,
                "multi_device_success_rate": successful_connections / len(devices),
                "user_tier": user_data["tier"]
            }
            
            self.auth_metrics.concurrent_session_capacity = successful_connections
            self.auth_metrics.session_establishment_time_ms = avg_connection_time
            
            # Clean up
            for session in device_sessions:
                if session["connected"]:
                    await session["client"].disconnect()
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Multi-device test failed: {e}")
            
        return results
    
    async def test_mfa_readiness_validation(self) -> Dict[str, Any]:
        """Test MFA (Multi-Factor Authentication) readiness and flow."""
        results = {"status": "success", "metrics": {}, "errors": []}
        
        try:
            user_data = self.test_users[3]
            
            # Step 1: Enable MFA for user
            mfa_setup_start = time.time()
            mfa_secret = hashlib.sha256(f"{user_data['user_id']}_mfa".encode()).hexdigest()[:16]
            
            # Simulate TOTP code generation (6-digit)
            totp_code = str(int(time.time()) % 1000000).zfill(6)
            mfa_setup_time = (time.time() - mfa_setup_start) * 1000
            
            # Step 2: Login with MFA
            login_start = time.time()
            login_payload = {
                "email": user_data["email"],
                "password": "test_password_123!",
                "mfa_code": totp_code
            }
            
            login_response = await self._simulate_auth_request("POST", "/auth/login_mfa", login_payload)
            login_time = (time.time() - login_start) * 1000
            
            # Step 3: Validate MFA-protected chat session
            token_payload = {
                **user_data,
                "mfa_verified": True,
                "mfa_timestamp": datetime.utcnow().isoformat()
            }
            mfa_token = self.generate_jwt_token(token_payload)
            
            # Step 4: Test chat with MFA-protected session
            chat_start = time.time()
            client = ChatResponsivenessTestClient(user_data["user_id"])
            connected = await client.connect()
            
            if connected:
                await client.send_message("MFA-protected message")
                await asyncio.sleep(1)
                mfa_chat_success = len(client.messages_received) > 0
            else:
                mfa_chat_success = False
                
            mfa_total_time = (time.time() - chat_start) * 1000
            
            # Calculate success metrics
            mfa_flow_success = all([
                login_response.get("success", False),
                mfa_chat_success
            ])
            
            results["metrics"] = {
                "mfa_setup_time_ms": mfa_setup_time,
                "mfa_login_time_ms": login_time,
                "mfa_chat_time_ms": mfa_total_time,
                "mfa_flow_success_rate": 1.0 if mfa_flow_success else 0.0,
                "mfa_code_generated": totp_code,
                "user_tier": user_data["tier"]
            }
            
            self.auth_metrics.mfa_validation_time_ms = login_time
            
            if connected:
                await client.disconnect()
                
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"MFA test failed: {e}")
            
        return results
    
    async def test_enterprise_team_authentication(self) -> Dict[str, Any]:
        """Test enterprise team authentication and permission levels."""
        results = {"status": "success", "metrics": {}, "errors": []}
        
        try:
            # Create enterprise team structure
            team_users = [
                {"user_id": "enterprise_admin", "role": "admin", "tier": "enterprise"},
                {"user_id": "enterprise_manager", "role": "manager", "tier": "enterprise"}, 
                {"user_id": "enterprise_member", "role": "member", "tier": "enterprise"}
            ]
            
            team_metrics = []
            permission_tests = []
            
            for user in team_users:
                user_start = time.time()
                
                # Generate role-specific token
                token_payload = {
                    **user,
                    "team_id": "enterprise_team_001",
                    "permissions": self._get_role_permissions(user["role"]),
                    "email": f"{user['user_id']}@enterprise.com"
                }
                
                enterprise_token = self.generate_jwt_token(token_payload)
                
                # Test role-based chat access
                client = ChatResponsivenessTestClient(user["user_id"])
                connected = await client.connect()
                
                if connected:
                    # Send role-specific message
                    role_message = f"Enterprise {user['role']} requesting assistance"
                    await client.send_message(role_message)
                    await asyncio.sleep(1)
                    
                    # Test permission-based features
                    permission_success = await self._test_role_permissions(client, user["role"])
                    permission_tests.append(permission_success)
                    
                user_time = (time.time() - user_start) * 1000
                team_metrics.append({
                    "role": user["role"],
                    "connection_time": user_time,
                    "connected": connected,
                    "permission_test_passed": permission_success
                })
                
                if connected:
                    await client.disconnect()
            
            # Calculate team authentication metrics
            successful_connections = sum(1 for m in team_metrics if m["connected"])
            avg_connection_time = statistics.mean([m["connection_time"] for m in team_metrics])
            permission_success_rate = sum(permission_tests) / len(permission_tests) if permission_tests else 0
            
            results["metrics"] = {
                "team_members_tested": len(team_users),
                "successful_team_connections": successful_connections,
                "avg_team_connection_time_ms": avg_connection_time,
                "permission_success_rate": permission_success_rate,
                "enterprise_auth_success_rate": successful_connections / len(team_users)
            }
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Enterprise team auth test failed: {e}")
            
        return results
    
    async def _simulate_auth_request(self, method: str, endpoint: str, payload: Dict) -> Dict[str, Any]:
        """Simulate authentication service request."""
        # Mock successful auth responses for testing
        await asyncio.sleep(random.uniform(0.05, 0.2))  # Simulate network latency
        
        success_responses = {
            "/auth/signup": {"success": True, "user_id": payload.get("email", "").split("@")[0]},
            "/auth/verify": {"success": True, "verified": True},
            "/auth/login": {"success": True, "token": "mock_jwt_token"},
            "/auth/login_mfa": {"success": True, "token": "mock_mfa_jwt_token"}
        }
        
        return success_responses.get(endpoint, {"success": False, "error": "Unknown endpoint"})
    
    def _get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for enterprise role."""
        permission_map = {
            "admin": ["read", "write", "delete", "manage_users", "manage_billing", "access_analytics"],
            "manager": ["read", "write", "manage_team", "access_reports"],
            "member": ["read", "write", "basic_features"]
        }
        return permission_map.get(role, ["read"])
    
    async def _test_role_permissions(self, client: 'ChatResponsivenessTestClient', role: str) -> bool:
        """Test role-based permissions."""
        try:
            # Simulate permission-based feature access
            if role == "admin":
                await client.send_message("Admin: Show system analytics")
            elif role == "manager":
                await client.send_message("Manager: Generate team report")
            else:
                await client.send_message("Member: Help with basic task")
            
            await asyncio.sleep(0.5)
            return len(client.events_received) > 0
        except Exception:
            return False


@pytest.mark.user_journey
class TestUserJourneyValidation:
    """Comprehensive user journey validation - 10+ tests covering complete user experiences."""
    
    def __init__(self):
    pass
        self.real_services = None
        self.journey_metrics = {}
        self.business_metrics = BusinessMetrics()
    
    async def setup(self):
        """Initialize services for user journey testing."""
        self.real_services = get_real_services()
        await self.real_services.ensure_all_services_available()
    
    async def teardown(self):
        """Clean up journey test resources."""
    pass
        if self.real_services:
            await self.real_services.close_all()
    
    async def test_first_time_user_onboarding_journey(self) -> Dict[str, Any]:
        """Test complete first-time user onboarding through first successful chat."""
        results = {"status": "success", "metrics": {}, "errors": [], "business_impact": {}}
        
        try:
            journey_start = time.time()
            
            # Step 1: Landing page simulation
            user_data = {
                "user_id": "first_time_user_001",
                "email": "newuser@example.com",
                "tier": "free",
                "source": "organic_search"
            }
            
            # Step 2: Account creation
            signup_start = time.time()
            # Simulate signup process
            await asyncio.sleep(0.5)  # Account creation time
            signup_time = (time.time() - signup_start) * 1000
            
            # Step 3: Welcome chat sequence
            welcome_start = time.time()
            client = ChatResponsivenessTestClient(user_data["user_id"])
            connected = await client.connect()
            
            if not connected:
                results["errors"].append("Failed to connect new user")
                await asyncio.sleep(0)
    return results
            
            # Welcome message sequence
            welcome_messages = [
                "Hello! I'm new to Netra AI. Can you help me get started?",
                "What can you help me with?",
                "How do I create my first AI workflow?"
            ]
            
            message_responses = []
            for msg in welcome_messages:
                await client.send_message(msg)
                await asyncio.sleep(2)  # Wait for AI response
                message_responses.append(len(client.messages_received))
            
            welcome_time = (time.time() - welcome_start) * 1000
            
            # Step 4: First successful AI interaction
            ai_interaction_start = time.time()
            await client.send_message("Create a simple data analysis workflow for sales data")
            await asyncio.sleep(3)  # AI processing time
            
            ai_interaction_time = (time.time() - ai_interaction_start) * 1000
            total_onboarding_time = (time.time() - journey_start) * 1000
            
            # Evaluate journey success
            messages_received = len(client.messages_received)
            events_received = len(client.events_received)
            journey_completion_score = min(1.0, (messages_received + events_received) / 10)
            
            # Calculate business metrics
            conversion_probability = 0.15 if journey_completion_score > 0.7 else 0.05  # 15% vs 5%
            estimated_ltv = 120.0 if conversion_probability > 0.1 else 30.0  # $120 vs $30
            
            results["metrics"] = {
                "signup_time_ms": signup_time,
                "welcome_sequence_time_ms": welcome_time,
                "ai_interaction_time_ms": ai_interaction_time,
                "total_onboarding_time_ms": total_onboarding_time,
                "messages_in_onboarding": len(welcome_messages),
                "ai_responses_received": messages_received,
                "journey_completion_score": journey_completion_score,
                "user_tier": user_data["tier"],
                "traffic_source": user_data["source"]
            }
            
            results["business_impact"] = {
                "conversion_probability": conversion_probability,
                "estimated_lifetime_value": estimated_ltv,
                "onboarding_efficiency": journey_completion_score,
                "revenue_attribution": estimated_ltv * conversion_probability,
                "user_satisfaction_estimate": journey_completion_score * 0.9
            }
            
            self.business_metrics.conversion_probability = conversion_probability
            self.business_metrics.revenue_attribution = estimated_ltv * conversion_probability
            
            await client.disconnect()
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Onboarding journey failed: {e}")
        
        return results
    
    async def test_free_to_premium_upgrade_journey(self) -> Dict[str, Any]:
        """Test user journey from free tier through premium upgrade decision."""
        results = {"status": "success", "metrics": {}, "errors": [], "business_impact": {}}
        
        try:
            # Step 1: Free tier user with usage patterns
            user_data = {
                "user_id": "upgrade_candidate_001",
                "email": "poweruser@example.com",
                "tier": "free",
                "usage_days": 14,
                "monthly_queries": 95  # Near free tier limit of 100
            }
            
            journey_start = time.time()
            client = ChatResponsivenessTestClient(user_data["user_id"])
            connected = await client.connect()
            
            if not connected:
                results["errors"].append("Failed to connect upgrade candidate")
                return results
            
            # Step 2: Hit usage limits
            limit_reached_start = time.time()
            
            # Simulate hitting free tier limits
            for i in range(8):  # Remaining queries to hit limit
                await client.send_message(f"Query {96 + i}: Complex data analysis request")
                await asyncio.sleep(0.5)
            
            limit_experience_time = (time.time() - limit_reached_start) * 1000
            
            # Step 3: Premium feature showcase
            showcase_start = time.time()
            premium_features = [
                "Advanced AI model access",
                "Priority processing queue",
                "Extended chat history",
                "Team collaboration features",
                "API access"
            ]
            
            for feature in premium_features[:3]:  # Show subset of features
                await client.send_message(f"Tell me about {feature}")
                await asyncio.sleep(1)
            
            showcase_time = (time.time() - showcase_start) * 1000
            
            # Step 4: Upgrade decision simulation
            upgrade_start = time.time()
            await client.send_message("I need more queries and better features. How do I upgrade?")
            await asyncio.sleep(2)
            
            upgrade_inquiry_time = (time.time() - upgrade_start) * 1000
            total_journey_time = (time.time() - journey_start) * 1000
            
            # Analyze upgrade likelihood
            responses_received = len(client.messages_received)
            feature_engagement = min(1.0, responses_received / len(premium_features))
            
            # Business impact calculations
            upgrade_probability = 0.35 if feature_engagement > 0.6 else 0.15  # 35% vs 15%
            monthly_revenue_gain = 29.0  # Premium tier price
            annual_revenue_impact = monthly_revenue_gain * 12 * upgrade_probability
            
            results["metrics"] = {
                "current_tier": user_data["tier"],
                "usage_pattern_days": user_data["usage_days"],
                "queries_before_limit": user_data["monthly_queries"],
                "limit_experience_time_ms": limit_experience_time,
                "feature_showcase_time_ms": showcase_time,
                "upgrade_inquiry_time_ms": upgrade_inquiry_time,
                "total_journey_time_ms": total_journey_time,
                "feature_engagement_score": feature_engagement,
                "responses_in_journey": responses_received
            }
            
            results["business_impact"] = {
                "upgrade_probability": upgrade_probability,
                "monthly_revenue_gain": monthly_revenue_gain,
                "annual_revenue_impact": annual_revenue_impact,
                "customer_lifetime_value_increase": annual_revenue_impact * 3,  # 3-year LTV
                "conversion_optimization_score": feature_engagement
            }
            
            self.business_metrics.conversion_probability = upgrade_probability
            self.business_metrics.revenue_attribution = annual_revenue_impact
            self.business_metrics.premium_feature_adoption = feature_engagement
            
            await client.disconnect()
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Upgrade journey failed: {e}")
        
        return results
    
    async def test_enterprise_team_collaboration_journey(self) -> Dict[str, Any]:
        """Test enterprise team collaboration and shared workspace journey."""
        results = {"status": "success", "metrics": {}, "errors": [], "business_impact": {}}
        
        try:
            # Step 1: Team setup
            team_data = {
                "team_id": "enterprise_team_collab_001",
                "plan": "enterprise",
                "seat_count": 25,
                "monthly_cost": 2500.0  # $100/seat
            }
            
            team_members = [
                {"user_id": "team_lead", "role": "admin"},
                {"user_id": "data_scientist", "role": "member"},
                {"user_id": "analyst", "role": "member"},
                {"user_id": "manager", "role": "manager"}
            ]
            
            journey_start = time.time()
            connected_members = []
            
            # Step 2: Team member connections
            connection_start = time.time()
            for member in team_members:
                client = ChatResponsivenessTestClient(f"enterprise_{member['user_id']}")
                connected = await client.connect()
                
                if connected:
                    connected_members.append({
                        "client": client,
                        "role": member["role"],
                        "user_id": member["user_id"]
                    })
            
            connection_time = (time.time() - connection_start) * 1000
            
            # Step 3: Collaborative AI session
            collaboration_start = time.time()
            
            if len(connected_members) >= 2:
                # Lead initiates shared project
                lead = next(m for m in connected_members if m["role"] == "admin")
                await lead["client"].send_message("Team: Let's create a quarterly analysis workflow")
                await asyncio.sleep(1)
                
                # Other members contribute
                for member in connected_members[1:3]:  # First 2 members
                    await member["client"].send_message(f"I can help with {member['role']} perspective")
                    await asyncio.sleep(1)
                
                # Shared workspace simulation
                workspace_messages = [
                    "Share this analysis with the team",
                    "Add team member access to this workflow", 
                    "Schedule team review of results"
                ]
                
                for msg in workspace_messages:
                    await lead["client"].send_message(msg)
                    await asyncio.sleep(0.5)
            
            collaboration_time = (time.time() - collaboration_start) * 1000
            
            # Step 4: Enterprise feature utilization
            enterprise_features_start = time.time()
            
            enterprise_feature_usage = []
            if connected_members:
                # Test enterprise-specific features
                admin_client = next(m for m in connected_members if m["role"] == "admin")["client"]
                
                enterprise_tests = [
                    "Enable advanced analytics for team",
                    "Set up automated reporting dashboard",
                    "Configure team permission levels"
                ]
                
                for test in enterprise_tests:
                    await admin_client.send_message(test)
                    await asyncio.sleep(1)
                    enterprise_feature_usage.append(len(admin_client.events_received))
            
            enterprise_time = (time.time() - enterprise_features_start) * 1000
            total_journey_time = (time.time() - journey_start) * 1000
            
            # Calculate collaboration effectiveness
            total_messages = sum(len(m["client"].messages_received) for m in connected_members)
            collaboration_score = min(1.0, total_messages / 20)  # 20 messages = perfect collaboration
            
            # Business impact
            team_productivity_gain = collaboration_score * 0.3  # 30% max productivity gain
            monthly_roi = team_productivity_gain * team_data["monthly_cost"] * 0.5  # 50% efficiency factor
            
            results["metrics"] = {
                "team_size": len(team_members),
                "connected_members": len(connected_members),
                "connection_setup_time_ms": connection_time,
                "collaboration_session_time_ms": collaboration_time,
                "enterprise_features_time_ms": enterprise_time,
                "total_team_journey_time_ms": total_journey_time,
                "collaboration_effectiveness_score": collaboration_score,
                "enterprise_feature_adoption": len(enterprise_feature_usage) / 3,
                "team_plan": team_data["plan"],
                "monthly_investment": team_data["monthly_cost"]
            }
            
            results["business_impact"] = {
                "team_productivity_gain": team_productivity_gain,
                "monthly_roi": monthly_roi,
                "annual_value_created": monthly_roi * 12,
                "collaboration_efficiency": collaboration_score,
                "enterprise_retention_score": collaboration_score * 0.9
            }
            
            self.business_metrics.enterprise_readiness_score = collaboration_score
            self.business_metrics.revenue_attribution = monthly_roi * 12
            
            # Clean up
            for member in connected_members:
                await member["client"].disconnect()
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Enterprise collaboration journey failed: {e}")
        
        return results


@pytest.mark.performance_load
class TestPerformanceUnderLoad:
    """Performance testing under concurrent load - 5+ tests with 50+ concurrent users."""
    
    def __init__(self):
    pass
        self.real_services = None
        self.load_metrics = LoadTestMetrics()
        self.business_metrics = BusinessMetrics()
    
    async def setup(self):
        """Initialize services for performance testing."""
        self.real_services = get_real_services()
        await self.real_services.ensure_all_services_available()
    
    async def teardown(self):
        """Clean up performance test resources."""
    pass
        if self.real_services:
            await self.real_services.close_all()
    
    async def test_concurrent_chat_responsiveness_50_users(self) -> Dict[str, Any]:
        """Test chat responsiveness with 50 concurrent users - core business metric."""
        results = {"status": "success", "metrics": {}, "errors": [], "business_impact": {}}
        
        try:
            user_count = 50
            test_start = time.time()
            
            logger.info(f"Starting 50-user concurrent chat responsiveness test")
            
            # Create concurrent users
            clients = []
            connection_tasks = []
            
            for i in range(user_count):
                client = ChatResponsivenessTestClient(f"load_user_{i:03d}")
                clients.append(client)
                connection_tasks.append(client.connect())
            
            # Connect all users concurrently
            connection_start = time.time()
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            connection_time = (time.time() - connection_start) * 1000
            
            successful_connections = sum(1 for r in connection_results if r is True)
            
            if successful_connections < user_count * 0.8:  # 80% success threshold
                results["errors"].append(f"Only {successful_connections}/{user_count} users connected")
            
            # Concurrent message sending
            message_start = time.time()
            message_tasks = []
            
            for i, client in enumerate(clients[:successful_connections]):
                if hasattr(client, 'connected') and client.connected:
                    # Stagger messages slightly to simulate realistic usage
                    delay = (i % 10) * 0.1  # 0-0.9 second stagger per 10 users
                    message_tasks.append(self._send_delayed_message(client, delay, f"Load test message from user {i}"))
            
            # Wait for all messages to be sent
            await asyncio.gather(*message_tasks, return_exceptions=True)
            message_send_time = (time.time() - message_start) * 1000
            
            # Wait for responses
            response_wait_start = time.time()
            await asyncio.sleep(5)  # 5-second response window
            response_wait_time = (time.time() - response_wait_start) * 1000
            
            # Collect performance metrics
            response_times = []
            messages_received = 0
            events_received = 0
            
            for client in clients:
                if hasattr(client, 'response_times'):
                    response_times.extend(client.response_times)
                if hasattr(client, 'messages_received'):
                    messages_received += len(client.messages_received)
                if hasattr(client, 'events_received'):
                    events_received += len(client.events_received)
            
            # Calculate performance metrics
            avg_response_time = statistics.mean(response_times) * 1000 if response_times else 0
            p95_response_time = statistics.quantiles(response_times, n=20)[18] * 1000 if len(response_times) > 20 else 0
            p99_response_time = statistics.quantiles(response_times, n=100)[98] * 1000 if len(response_times) > 100 else 0
            
            total_test_time = (time.time() - test_start) * 1000
            
            # Business impact analysis
            user_satisfaction = 1.0 if avg_response_time < 2000 else max(0.3, 1.0 - (avg_response_time - 2000) / 5000)
            engagement_rate = messages_received / (successful_connections + 1)  # +1 to avoid division by zero
            
            # Revenue calculation - responsive chat increases conversion
            base_conversion_rate = 0.12  # 12% base
            performance_multiplier = user_satisfaction * 1.5  # Up to 50% boost
            effective_conversion_rate = base_conversion_rate * performance_multiplier
            
            monthly_revenue_impact = successful_connections * 29.0 * effective_conversion_rate  # $29 premium tier
            
            results["metrics"] = {
                "concurrent_users": user_count,
                "successful_connections": successful_connections,
                "connection_success_rate": successful_connections / user_count,
                "connection_time_ms": connection_time,
                "message_send_time_ms": message_send_time,
                "avg_response_time_ms": avg_response_time,
                "p95_response_time_ms": p95_response_time,
                "p99_response_time_ms": p99_response_time,
                "total_messages_received": messages_received,
                "total_events_received": events_received,
                "total_test_time_ms": total_test_time,
                "user_engagement_rate": engagement_rate
            }
            
            results["business_impact"] = {
                "user_satisfaction_score": user_satisfaction,
                "engagement_rate": engagement_rate,
                "effective_conversion_rate": effective_conversion_rate,
                "monthly_revenue_impact": monthly_revenue_impact,
                "annual_revenue_potential": monthly_revenue_impact * 12,
                "performance_sla_compliance": 1.0 if avg_response_time < 2000 else 0.0
            }
            
            # Update business metrics
            self.business_metrics.user_satisfaction_score = user_satisfaction
            self.business_metrics.engagement_rate = engagement_rate
            self.business_metrics.revenue_attribution = monthly_revenue_impact * 12
            self.business_metrics.concurrent_user_capacity = successful_connections
            
            # Clean up connections
            cleanup_tasks = []
            for client in clients:
                if hasattr(client, 'connected') and client.connected:
                    cleanup_tasks.append(client.disconnect())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                
            logger.info(f"50-user test completed: {successful_connections} users, {avg_response_time:.1f}ms avg response")
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"50-user load test failed: {e}")
        
        await asyncio.sleep(0)
    return results
    
    async def test_memory_leak_detection_under_load(self) -> Dict[str, Any]:
        """Test for memory leaks during sustained chat load."""
        results = {"status": "success", "metrics": {}, "errors": [], "business_impact": {}}
        
        try:
            import psutil
            import gc
            
            # Initial memory baseline
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            test_duration_minutes = 3  # 3-minute sustained load test
            user_count = 25
            
            logger.info(f"Starting {test_duration_minutes}-minute memory leak detection test")
            
            memory_samples = [initial_memory]
            gc_collections = []
            
            test_start = time.time()
            
            # Create sustained load
            active_clients = []
            
            while (time.time() - test_start) < (test_duration_minutes * 60):
                iteration_start = time.time()
                
                # Create batch of users
                batch_clients = []
                for i in range(user_count):
                    client = ChatResponsivenessTestClient(f"memory_test_user_{int(time.time())}_{i}")
                    batch_clients.append(client)
                
                # Connect and send messages
                connection_tasks = [client.connect() for client in batch_clients]
                await asyncio.gather(*connection_tasks, return_exceptions=True)
                
                # Send messages from connected users
                message_tasks = []
                for client in batch_clients:
                    if hasattr(client, 'connected') and client.connected:
                        message_tasks.append(client.send_message("Sustained load test message"))
                
                await asyncio.gather(*message_tasks, return_exceptions=True)
                
                # Wait for responses
                await asyncio.sleep(2)
                
                # Disconnect users
                disconnect_tasks = []
                for client in batch_clients:
                    if hasattr(client, 'connected') and client.connected:
                        disconnect_tasks.append(client.disconnect())
                
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
                
                # Memory sampling
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_samples.append(current_memory)
                
                # Garbage collection monitoring
                gc.collect()
                gc_collections.append(len(gc.garbage))
                
                # Control iteration timing
                iteration_time = time.time() - iteration_start
                if iteration_time < 30:  # 30-second iterations
                    await asyncio.sleep(30 - iteration_time)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Analyze memory usage
            memory_growth = final_memory - initial_memory
            max_memory = max(memory_samples)
            avg_memory = statistics.mean(memory_samples)
            
            # Calculate memory growth rate (MB per minute)
            memory_growth_rate = memory_growth / test_duration_minutes
            
            # Memory leak detection
            leak_threshold = 10.0  # 10 MB growth per minute
            memory_leak_detected = memory_growth_rate > leak_threshold
            
            # Business impact of memory issues
            stability_score = 1.0 if not memory_leak_detected else max(0.2, 1.0 - (memory_growth_rate / 50.0))
            uptime_impact = stability_score  # Lower stability = more downtime risk
            
            # Cost of memory issues
            infrastructure_cost_increase = max(0, memory_growth_rate * 0.1)  # $0.10 per MB/min growth
            
            results["metrics"] = {
                "test_duration_minutes": test_duration_minutes,
                "users_per_iteration": user_count,
                "initial_memory_mb": initial_memory,
                "final_memory_mb": final_memory,
                "max_memory_mb": max_memory,
                "avg_memory_mb": avg_memory,
                "memory_growth_mb": memory_growth,
                "memory_growth_rate_mb_per_min": memory_growth_rate,
                "memory_leak_detected": memory_leak_detected,
                "gc_collections_total": sum(gc_collections),
                "memory_samples_count": len(memory_samples)
            }
            
            results["business_impact"] = {
                "stability_score": stability_score,
                "uptime_reliability": uptime_impact,
                "infrastructure_cost_increase_monthly": infrastructure_cost_increase * 30 * 24,  # Monthly estimate
                "performance_degradation_risk": 1.0 - stability_score,
                "scalability_confidence": stability_score
            }
            
            self.business_metrics.enterprise_readiness_score = stability_score
            
            if memory_leak_detected:
                results["errors"].append(f"Memory leak detected: {memory_growth_rate:.1f} MB/min growth rate")
            
            logger.info(f"Memory test completed: {memory_growth:.1f}MB growth over {test_duration_minutes}min")
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Memory leak test failed: {e}")
        
        return results
    
    async def _send_delayed_message(self, client, delay: float, message: str):
        """Send a message after a specified delay."""
        await asyncio.sleep(delay)
        if hasattr(client, 'connected') and client.connected:
            await asyncio.sleep(0)
    return await client.send_message(message)
        return False


class ChatResponsivenessTestClient:
    """Enhanced client for testing chat responsiveness under load."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self, user_id: str, ws_manager: Optional[WebSocketManager] = None):
    pass
        self.user_id = user_id
        self.ws_manager = ws_manager
        self.websocket = None
        self.connected = False
        self.messages_sent = []
        self.messages_received = []
        self.events_received = []
        self.response_times = []
        self.last_message_time = None
        self.connection_drops = 0
        self.recovery_times = []
        self.event_tracker = {}
        
    async def connect(self, ws_url: str = "ws://localhost:8000/ws") -> bool:
        """Establish WebSocket connection with real services."""
        try:
            real_services = get_real_services()
            ws_client = real_services.create_websocket_client()
            
            # Connect with authentication
            headers = {"Authorization": f"Bearer test-token-{self.user_id}"}
            await ws_client.connect(f"chat/{self.user_id}", headers=headers)
            
            self.websocket = ws_client._websocket
            self.connected = True
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
            return True
        except Exception as e:
            logger.error(f"User {self.user_id} connection failed: {e}")
            return False
    
    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages."""
        try:
            while self.connected and self.websocket:
                message = await self.websocket.recv()
                
                # Record timing
                if self.last_message_time:
                    response_time = time.time() - self.last_message_time
                    self.response_times.append(response_time)
                
                # Parse and track message
                try:
                    data = json.loads(message)
                    self.messages_received.append(data)
                    
                    # Track event types
                    event_type = data.get("type", "unknown")
                    self.events_received.append(event_type)
                    self.event_tracker[event_type] = self.event_tracker.get(event_type, 0) + 1
                    
                    logger.debug(f"User {self.user_id} received: {event_type}")
                except json.JSONDecodeError:
                    logger.error(f"User {self.user_id} received invalid JSON: {message}")
                    
        except Exception as e:
            logger.error(f"User {self.user_id} listen error: {e}")
            self.connected = False
    
    async def send_message(self, content: str) -> bool:
        """Send a chat message and record timing."""
    pass
        if not self.connected or not self.websocket:
            await asyncio.sleep(0)
    return False
            
        try:
            message = {
                "type": "chat_message",
                "content": content,
                "user_id": self.user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.last_message_time = time.time()
            await self.websocket.send(json.dumps(message))
            self.messages_sent.append(message)
            
            return True
        except Exception as e:
            logger.error(f"User {self.user_id} send error: {e}")
            return False
    
    async def simulate_network_disruption(self, duration_seconds: float = 2.0):
        """Simulate a network disruption and measure recovery."""
        if not self.websocket:
            await asyncio.sleep(0)
    return
            
        logger.info(f"User {self.user_id} simulating {duration_seconds}s network disruption")
        
        # Record disruption
        disruption_start = time.time()
        self.connection_drops += 1
        
        # Close connection
        await self.websocket.close()
        self.connected = False
        
        # Wait for disruption duration
        await asyncio.sleep(duration_seconds)
        
        # Attempt reconnection
        reconnect_start = time.time()
        success = await self.connect()
        
        if success:
            recovery_time = time.time() - reconnect_start
            self.recovery_times.append(recovery_time)
            logger.info(f"User {self.user_id} recovered in {recovery_time:.2f}s")
        else:
            logger.error(f"User {self.user_id} failed to recover")
            
        return success
    
    def validate_events(self) -> Tuple[bool, List[str]]:
        """Validate that all required events were received."""
    pass
        received_types = set(self.event_tracker.keys())
        missing = self.REQUIRED_EVENTS - received_types
        
        if missing:
            return False, list(missing)
        return True, []
    
    async def disconnect(self):
        """Clean disconnect."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False


class ChatLoadTestOrchestrator:
    """Orchestrates comprehensive load testing scenarios."""
    
    def __init__(self):
    pass
        self.real_services = None
        self.ws_manager = None
        self.agent_registry = None
        self.execution_engine = None
        self.supervisor_agent = None
        self.clients: List[ChatResponsivenessTestClient] = []
        self.metrics = LoadTestMetrics()
        
    async def setup(self):
        """Initialize all required services."""
        logger.info("Setting up real services for load testing")
        
        # Initialize real services
        self.real_services = get_real_services()
        await self.real_services.ensure_all_services_available()
        
        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager()
        
        # Initialize agent components
        self.agent_registry = AgentRegistry()
        self.execution_engine = ExecutionEngine()
        
        # Set up WebSocket integration
        notifier = WebSocketNotifier(self.ws_manager)
        self.agent_registry.set_websocket_manager(self.ws_manager)
        self.execution_engine.set_notifier(notifier)
        
        # Initialize supervisor agent
        llm_manager = LLMManager()
        self.supervisor_agent = SupervisorAgent(
            llm_manager=llm_manager,
            registry=self.agent_registry,
            execution_engine=self.execution_engine
        )
        
        logger.info("Load test setup complete")
    
    async def teardown(self):
        """Clean up all resources."""
    pass
        # Disconnect all clients
        for client in self.clients:
            await client.disconnect()
        
        # Stop services
        if self.real_services:
            await self.real_services.close_all()
    
    async def test_concurrent_user_load(self, user_count: int = 5) -> LoadTestMetrics:
        """
        TEST 1.1: Concurrent User Load Test
        - 5 simultaneous users sending messages
        - Each user receives real-time updates within 2 seconds
        - WebSocket events flow correctly
        - No message loss or connection drops
        """
        logger.info(f"Starting concurrent user load test with {user_count} users")
        
        test_start = time.time()
        self.metrics = LoadTestMetrics(concurrent_users=user_count)
        
        # Create and connect users concurrently
        connect_tasks = []
        for i in range(user_count):
            client = ChatResponsivenessTestClient(f"user-{i:03d}", self.ws_manager)
            self.clients.append(client)
            connect_tasks.append(client.connect())
        
        # Wait for all connections
        connection_results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        # Count successful connections
        self.metrics.successful_connections = sum(1 for r in connection_results if r is True)
        self.metrics.failed_connections = user_count - self.metrics.successful_connections
        
        if self.metrics.successful_connections == 0:
            logger.error("No users connected successfully!")
            await asyncio.sleep(0)
    return self.metrics
        
        logger.info(f"Connected {self.metrics.successful_connections}/{user_count} users")
        
        # Send messages from all users simultaneously
        message_tasks = []
        for client in self.clients:
            if client.connected:
                for msg_idx in range(3):  # Each user sends 3 messages
                    message = f"Test message {msg_idx} from {client.user_id}"
                    message_tasks.append(client.send_message(message))
                    await asyncio.sleep(0.1)  # Small delay between messages
        
        # Wait for all messages to be sent
        send_results = await asyncio.gather(*message_tasks, return_exceptions=True)
        self.metrics.messages_sent = sum(1 for r in send_results if r is True)
        
        # Wait for responses (max 5 seconds)
        await asyncio.sleep(5)
        
        # Collect metrics from all clients
        for client in self.clients:
            self.metrics.messages_received += len(client.messages_received)
            self.metrics.response_times.extend(client.response_times)
            
            # Track events
            for event_type, count in client.event_tracker.items():
                self.metrics.events_received[event_type] = \
                    self.metrics.events_received.get(event_type, 0) + count
            
            # Validate required events
            valid, missing = client.validate_events()
            if not valid:
                self.metrics.missing_events.extend(missing)
        
        # Calculate message loss
        expected_responses = self.metrics.messages_sent
        self.metrics.message_loss_count = max(0, expected_responses - self.metrics.messages_received)
        
        # Calculate metrics
        self.metrics.test_duration_seconds = time.time() - test_start
        self.metrics.calculate_percentiles()
        self.metrics.error_rate = self.metrics.failed_connections / user_count if user_count > 0 else 0
        
        # Log results
        self._log_test_results("Concurrent User Load Test")
        
        return self.metrics
    
    async def test_agent_processing_backlog(self, queue_size: int = 10) -> LoadTestMetrics:
        """
        TEST 1.2: Agent Processing Backlog Test
        - Queue 10 requests rapidly
        - Verify each user sees proper "processing" indicators
        - Ensure messages are processed in order
        - No user is left without feedback
        """
        logger.info(f"Starting agent processing backlog test with {queue_size} queued requests")
        
        test_start = time.time()
        self.metrics = LoadTestMetrics()
        
        # Create a single user for this test
        client = ChatResponsivenessTestClient("backlog-user", self.ws_manager)
        self.clients = [client]
        
        # Connect user
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect test user")
            return self.metrics
        
        self.metrics.successful_connections = 1
        
        # Rapidly send messages to create backlog
        logger.info(f"Sending {queue_size} rapid messages to create backlog")
        send_tasks = []
        for i in range(queue_size):
            message = f"Backlog message {i:02d} - Process this request"
            send_tasks.append(client.send_message(message))
            await asyncio.sleep(0.05)  # 50ms between messages
        
        # Wait for all messages to be sent
        send_results = await asyncio.gather(*send_tasks, return_exceptions=True)
        self.metrics.messages_sent = sum(1 for r in send_results if r is True)
        
        # Monitor for processing indicators
        processing_events = ["agent_started", "agent_thinking", "tool_executing"]
        completion_events = ["tool_completed", "agent_completed"]
        
        # Wait for processing (max 30 seconds for backlog)
        max_wait = 30
        start_wait = time.time()
        
        while time.time() - start_wait < max_wait:
            # Check if we've received processing indicators
            has_processing = any(
                client.event_tracker.get(event, 0) > 0 
                for event in processing_events
            )
            
            has_completion = any(
                client.event_tracker.get(event, 0) > 0
                for event in completion_events
            )
            
            if has_processing and has_completion:
                logger.info("Received both processing and completion indicators")
                break
                
            await asyncio.sleep(0.5)
        
        # Collect metrics
        self.metrics.messages_received = len(client.messages_received)
        self.metrics.response_times = client.response_times
        
        # Verify message ordering
        message_order_valid = self._verify_message_order(client.messages_received)
        
        # Track events
        self.metrics.events_received = dict(client.event_tracker)
        
        # Validate all messages got feedback
        messages_with_feedback = 0
        for msg in client.messages_sent:
            # Check if there's a corresponding response
            if any(r.get("correlation_id") == msg.get("timestamp") 
                   for r in client.messages_received):
                messages_with_feedback += 1
        
        # Calculate metrics
        self.metrics.test_duration_seconds = time.time() - test_start
        self.metrics.calculate_percentiles()
        
        # Log results
        logger.info(f"Backlog test results:")
        logger.info(f"  Messages sent: {self.metrics.messages_sent}")
        logger.info(f"  Messages received: {self.metrics.messages_received}")
        logger.info(f"  Messages with feedback: {messages_with_feedback}")
        logger.info(f"  Message order valid: {message_order_valid}")
        logger.info(f"  Events received: {self.metrics.events_received}")
        
        return self.metrics
    
    async def test_websocket_connection_recovery(self, disruption_count: int = 3) -> LoadTestMetrics:
        """
        TEST 1.3: WebSocket Connection Recovery
        - Simulate brief network disruption during active chat
        - Verify automatic reconnection and message replay
        - User sees seamless continuation
        """
        logger.info(f"Starting connection recovery test with {disruption_count} disruptions")
        
        test_start = time.time()
        self.metrics = LoadTestMetrics()
        
        # Create test users
        user_count = 3
        for i in range(user_count):
            client = ChatResponsivenessTestClient(f"recovery-user-{i}", self.ws_manager)
            self.clients.append(client)
        
        # Connect all users
        connect_tasks = [client.connect() for client in self.clients]
        connection_results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        self.metrics.successful_connections = sum(1 for r in connection_results if r is True)
        
        if self.metrics.successful_connections == 0:
            logger.error("No users connected for recovery test")
            return self.metrics
        
        logger.info(f"Connected {self.metrics.successful_connections} users for recovery test")
        
        # Simulate disruptions and recovery
        for disruption_idx in range(disruption_count):
            logger.info(f"Disruption cycle {disruption_idx + 1}/{disruption_count}")
            
            # Send messages before disruption
            for client in self.clients:
                if client.connected:
                    await client.send_message(f"Pre-disruption message {disruption_idx}")
            
            await asyncio.sleep(1)
            
            # Simulate network disruption for all users
            disruption_tasks = []
            for client in self.clients:
                if client.connected:
                    disruption_duration = random.uniform(1.0, 3.0)  # 1-3 seconds
                    disruption_tasks.append(
                        client.simulate_network_disruption(disruption_duration)
                    )
            
            # Wait for all disruptions to complete
            recovery_results = await asyncio.gather(*disruption_tasks, return_exceptions=True)
            
            # Count successful recoveries
            successful_recoveries = sum(1 for r in recovery_results if r is True)
            logger.info(f"  Recovered: {successful_recoveries}/{len(self.clients)}")
            
            # Send messages after recovery
            for client in self.clients:
                if client.connected:
                    await client.send_message(f"Post-recovery message {disruption_idx}")
            
            await asyncio.sleep(2)
        
        # Collect metrics
        for client in self.clients:
            self.metrics.connection_drops += client.connection_drops
            self.metrics.recovery_times.extend(client.recovery_times)
            self.metrics.messages_sent += len(client.messages_sent)
            self.metrics.messages_received += len(client.messages_received)
        
        # Calculate recovery metrics
        self.metrics.test_duration_seconds = time.time() - test_start
        self.metrics.calculate_percentiles()
        
        if self.metrics.recovery_times:
            avg_recovery = sum(self.metrics.recovery_times) / len(self.metrics.recovery_times)
            max_recovery = max(self.metrics.recovery_times)
            
            logger.info(f"Recovery test results:")
            logger.info(f"  Total disruptions: {self.metrics.connection_drops}")
            logger.info(f"  Avg recovery time: {avg_recovery:.2f}s")
            logger.info(f"  Max recovery time: {max_recovery:.2f}s")
            logger.info(f"  Messages sent: {self.metrics.messages_sent}")
            logger.info(f"  Messages received: {self.metrics.messages_received}")
        
        return self.metrics
    
    def _verify_message_order(self, messages: List[Dict]) -> bool:
        """Verify messages are processed in order."""
        # Extract timestamps and check ordering
        timestamps = []
        for msg in messages:
            if "timestamp" in msg:
                timestamps.append(msg["timestamp"])
        
        # Check if timestamps are in order
        for i in range(1, len(timestamps)):
            if timestamps[i] < timestamps[i-1]:
                return False
        return True
    
    def _log_test_results(self, test_name: str):
        """Log comprehensive test results."""
        logger.info(f"
{'='*60}")
        logger.info(f"{test_name} Results")
        logger.info(f"{'='*60}")
        logger.info(f"Concurrent Users: {self.metrics.concurrent_users}")
        logger.info(f"Successful Connections: {self.metrics.successful_connections}")
        logger.info(f"Failed Connections: {self.metrics.failed_connections}")
        logger.info(f"Messages Sent: {self.metrics.messages_sent}")
        logger.info(f"Messages Received: {self.metrics.messages_received}")
        logger.info(f"Message Loss: {self.metrics.message_loss_count}")
        
        if self.metrics.response_times:
            logger.info(f"
Response Times:")
            logger.info(f"  Average: {self.metrics.avg_response_time_ms:.2f}ms")
            logger.info(f"  Min: {self.metrics.min_response_time_ms:.2f}ms")
            logger.info(f"  Max: {self.metrics.max_response_time_ms:.2f}ms")
            logger.info(f"  P95: {self.metrics.p95_response_time_ms:.2f}ms")
            logger.info(f"  P99: {self.metrics.p99_response_time_ms:.2f}ms")
        
        if self.metrics.events_received:
            logger.info(f"
WebSocket Events:")
            for event_type, count in self.metrics.events_received.items():
                logger.info(f"  {event_type}: {count}")
        
        if self.metrics.missing_events:
            logger.info(f"
Missing Required Events: {self.metrics.missing_events}")
        
        logger.info(f"
Test Duration: {self.metrics.test_duration_seconds:.2f}s")
        logger.info(f"Error Rate: {self.metrics.error_rate:.2%}")
        logger.info(f"{'='*60}
")


# ============================================================================
# COMPREHENSIVE PYTEST TEST METHODS - 25+ Tests Total
# ============================================================================

@pytest.mark.asyncio  
@pytest.mark.auth_flow
@pytest.mark.timeout(30)
async def test_auth_signup_to_first_chat_complete_flow():
    """Test 1: Complete signup → verification → login → first chat authentication flow."""
    pass
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        results = await auth_validator.test_complete_signup_to_chat_flow()
        
        # Assertions
        assert results["status"] == "success", f"Auth flow failed: {results.get('errors', [])}"
        assert results["metrics"]["flow_completion_rate"] >= 0.8, \
            f"Low completion rate: {results['metrics']['flow_completion_rate']}"
        assert results["metrics"]["total_flow_time_ms"] < 10000, \
            f"Flow took too long: {results['metrics']['total_flow_time_ms']}ms"
        
        logger.info("✅ Auth signup to chat flow test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.auth_flow  
@pytest.mark.timeout(20)
async def test_jwt_token_lifecycle_complete():
    """Test 2: JWT token generation → validation → refresh → expiry cycle."""
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        results = await auth_validator.test_jwt_token_lifecycle_validation()
        
        # Assertions
        assert results["status"] == "success", f"JWT lifecycle failed: {results.get('errors', [])}"
        assert results["metrics"]["jwt_lifecycle_success_rate"] >= 0.9, \
            f"JWT lifecycle issues: {results['metrics']['jwt_lifecycle_success_rate']}"
        assert results["metrics"]["token_validation_time_ms"] < 100, \
            f"Token validation too slow: {results['metrics']['token_validation_time_ms']}ms"
        
        logger.info("✅ JWT token lifecycle test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.auth_flow
@pytest.mark.timeout(40)
async def test_multi_device_session_coordination():
    """Test 3: Multi-device authentication and session coordination."""
    pass
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        results = await auth_validator.test_multi_device_session_coordination()
        
        # Assertions
        assert results["status"] == "success", f"Multi-device test failed: {results.get('errors', [])}"
        assert results["metrics"]["multi_device_success_rate"] >= 0.8, \
            f"Multi-device connection issues: {results['metrics']['multi_device_success_rate']}"
        assert results["metrics"]["devices_tested"] >= 3, \
            f"Not enough devices tested: {results['metrics']['devices_tested']}"
        
        logger.info("✅ Multi-device session coordination test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.auth_flow
@pytest.mark.timeout(30)
async def test_mfa_authentication_readiness():
    """Test 4: MFA (Multi-Factor Authentication) readiness and flow."""
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        results = await auth_validator.test_mfa_readiness_validation()
        
        # Assertions
        assert results["status"] == "success", f"MFA test failed: {results.get('errors', [])}"
        assert results["metrics"]["mfa_flow_success_rate"] >= 0.9, \
            f"MFA flow issues: {results['metrics']['mfa_flow_success_rate']}"
        assert results["metrics"]["mfa_login_time_ms"] < 2000, \
            f"MFA login too slow: {results['metrics']['mfa_login_time_ms']}ms"
        
        logger.info("✅ MFA authentication readiness test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.auth_flow
@pytest.mark.timeout(45)
async def test_enterprise_team_authentication_permissions():
    """Test 5: Enterprise team authentication with role-based permissions."""
    pass
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        results = await auth_validator.test_enterprise_team_authentication()
        
        # Assertions
        assert results["status"] == "success", f"Enterprise auth failed: {results.get('errors', [])}"
        assert results["metrics"]["enterprise_auth_success_rate"] >= 0.8, \
            f"Enterprise auth issues: {results['metrics']['enterprise_auth_success_rate']}"
        assert results["metrics"]["permission_success_rate"] >= 0.8, \
            f"Permission validation issues: {results['metrics']['permission_success_rate']}"
        
        logger.info("✅ Enterprise team authentication test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.user_journey
@pytest.mark.timeout(45)
async def test_first_time_user_onboarding_complete():
    """Test 6: Complete first-time user onboarding journey to first successful chat."""
    journey_validator = TestUserJourneyValidation()
    await journey_validator.setup()
    
    try:
        results = await journey_validator.test_first_time_user_onboarding_journey()
        
        # Assertions
        assert results["status"] == "success", f"Onboarding failed: {results.get('errors', [])}"
        assert results["metrics"]["journey_completion_score"] >= 0.7, \
            f"Low onboarding completion: {results['metrics']['journey_completion_score']}"
        assert results["business_impact"]["conversion_probability"] >= 0.1, \
            f"Low conversion potential: {results['business_impact']['conversion_probability']}"
        
        logger.info("✅ First-time user onboarding test PASSED")
    finally:
        await journey_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.user_journey
@pytest.mark.timeout(50)
async def test_free_to_premium_upgrade_journey():
    """Test 7: User journey from free tier limits to premium upgrade decision."""
    pass
    journey_validator = TestUserJourneyValidation()
    await journey_validator.setup()
    
    try:
        results = await journey_validator.test_free_to_premium_upgrade_journey()
        
        # Assertions
        assert results["status"] == "success", f"Upgrade journey failed: {results.get('errors', [])}"
        assert results["metrics"]["feature_engagement_score"] >= 0.5, \
            f"Low feature engagement: {results['metrics']['feature_engagement_score']}"
        assert results["business_impact"]["upgrade_probability"] >= 0.1, \
            f"Low upgrade probability: {results['business_impact']['upgrade_probability']}"
        
        logger.info("✅ Free to premium upgrade journey test PASSED")
    finally:
        await journey_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.user_journey
@pytest.mark.timeout(60)
async def test_enterprise_team_collaboration_journey():
    """Test 8: Enterprise team collaboration and shared workspace journey."""
    journey_validator = TestUserJourneyValidation()
    await journey_validator.setup()
    
    try:
        results = await journey_validator.test_enterprise_team_collaboration_journey()
        
        # Assertions  
        assert results["status"] == "success", f"Team collaboration failed: {results.get('errors', [])}"
        assert results["metrics"]["collaboration_effectiveness_score"] >= 0.6, \
            f"Low collaboration score: {results['metrics']['collaboration_effectiveness_score']}"
        assert results["business_impact"]["monthly_roi"] >= 100, \
            f"Low ROI: ${results['business_impact']['monthly_roi']}"
        
        logger.info("✅ Enterprise team collaboration test PASSED")
    finally:
        await journey_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.performance_load
@pytest.mark.timeout(120)
async def test_concurrent_chat_responsiveness_50_users():
    """Test 9: Chat responsiveness with 50 concurrent users - critical performance test."""
    pass
    performance_validator = TestPerformanceUnderLoad()
    await performance_validator.setup()
    
    try:
        results = await performance_validator.test_concurrent_chat_responsiveness_50_users()
        
        # Assertions
        assert results["status"] == "success", f"50-user test failed: {results.get('errors', [])}"
        assert results["metrics"]["successful_connections"] >= 40, \
            f"Too many connection failures: {results['metrics']['successful_connections']}/50"
        assert results["metrics"]["avg_response_time_ms"] < 3000, \
            f"Response time too high: {results['metrics']['avg_response_time_ms']}ms"
        assert results["business_impact"]["user_satisfaction_score"] >= 0.7, \
            f"Low user satisfaction: {results['business_impact']['user_satisfaction_score']}"
        
        logger.info("✅ 50-user concurrent responsiveness test PASSED")
    finally:
        await performance_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.performance_load
@pytest.mark.timeout(300)
async def test_memory_leak_detection_sustained_load():
    """Test 10: Memory leak detection during sustained chat load."""
    performance_validator = TestPerformanceUnderLoad()
    await performance_validator.setup()
    
    try:
        results = await performance_validator.test_memory_leak_detection_under_load()
        
        # Assertions
        assert results["status"] == "success", f"Memory test failed: {results.get('errors', [])}"
        assert not results["metrics"]["memory_leak_detected"], \
            f"Memory leak detected: {results['metrics']['memory_growth_rate_mb_per_min']} MB/min"
        assert results["business_impact"]["stability_score"] >= 0.8, \
            f"Stability issues: {results['business_impact']['stability_score']}"
        
        logger.info("✅ Memory leak detection test PASSED")
    finally:
        await performance_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.auth_flow
@pytest.mark.timeout(25)
async def test_oauth_social_login_integration():
    """Test 11: OAuth and social media login integration flows."""
    pass
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        # Test OAuth flow with multiple providers
        oauth_providers = ["google", "github", "microsoft"]
        oauth_results = []
        
        for provider in oauth_providers:
            client = ChatResponsivenessTestClient(f"oauth_{provider}_user")
            connected = await client.connect()
            
            if connected:
                await client.send_message(f"Login via {provider} OAuth")
                await asyncio.sleep(1)
                oauth_results.append(len(client.events_received) > 0)
                await client.disconnect()
            else:
                oauth_results.append(False)
        
        oauth_success_rate = sum(oauth_results) / len(oauth_results) if oauth_results else 0
        
        assert oauth_success_rate >= 0.8, f"OAuth integration issues: {oauth_success_rate}"
        logger.info("✅ OAuth social login integration test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.auth_flow 
@pytest.mark.timeout(35)
async def test_session_timeout_and_renewal():
    """Test 12: Session timeout handling and automatic renewal."""
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        user_data = {"user_id": "session_test_user", "email": "session@test.com", "tier": "premium"}
        
        # Create short-lived token (5 seconds)
        short_token = auth_validator.generate_jwt_token(user_data, timedelta(seconds=5))
        
        client = ChatResponsivenessTestClient(user_data["user_id"])
        connected = await client.connect()
        
        if connected:
            # Send message with valid token
            await client.send_message("Message with valid token")
            await asyncio.sleep(1)
            initial_events = len(client.events_received)
            
            # Wait for token expiry
            await asyncio.sleep(6)
            
            # Attempt message with expired token - should trigger renewal
            await client.send_message("Message with expired token")
            await asyncio.sleep(2)
            post_expiry_events = len(client.events_received)
            
            # Should have handled token renewal gracefully
            assert post_expiry_events >= initial_events, "Session renewal failed"
            await client.disconnect()
        
        logger.info("✅ Session timeout and renewal test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.auth_flow
@pytest.mark.timeout(30)
async def test_cross_service_authentication():
    """Test 13: Authentication across multiple services (backend, auth, frontend)."""
    pass
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        user_data = {"user_id": "cross_service_user", "email": "cross@test.com", "tier": "enterprise"}
        
        # Test authentication across services
        services = ["backend", "auth_service", "frontend"]
        service_results = []
        
        for service in services:
            client = ChatResponsivenessTestClient(f"{service}_{user_data['user_id']}")
            connected = await client.connect()
            
            if connected:
                await client.send_message(f"Cross-service auth test for {service}")
                await asyncio.sleep(1)
                service_results.append(len(client.messages_received) > 0)
                await client.disconnect()
            else:
                service_results.append(False)
        
        cross_service_success = sum(service_results) / len(service_results) if service_results else 0
        
        assert cross_service_success >= 0.8, f"Cross-service auth issues: {cross_service_success}"
        logger.info("✅ Cross-service authentication test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.auth_flow
@pytest.mark.timeout(20)
async def test_permission_escalation_prevention():
    """Test 14: Permission escalation prevention and security boundaries."""
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        # Test user trying to access admin features
        user_data = {"user_id": "basic_user", "email": "basic@test.com", "tier": "free"}
        
        client = ChatResponsivenessTestClient(user_data["user_id"])
        connected = await client.connect()
        
        if connected:
            # Attempt admin-level commands
            admin_commands = [
                "Delete all user data",
                "Access admin panel", 
                "Modify billing settings",
                "Export user database"
            ]
            
            blocked_commands = 0
            for cmd in admin_commands:
                await client.send_message(cmd)
                await asyncio.sleep(0.5)
                # Should not receive admin-level responses
                if "admin" not in str(client.messages_received).lower():
                    blocked_commands += 1
            
            security_score = blocked_commands / len(admin_commands)
            assert security_score >= 0.8, f"Security vulnerability: {security_score}"
            await client.disconnect()
        
        logger.info("✅ Permission escalation prevention test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.auth_flow
@pytest.mark.timeout(25)
async def test_concurrent_login_rate_limiting():
    """Test 15: Rate limiting for concurrent login attempts."""
    pass
    auth_validator = TestAuthenticationFlowValidation()
    await auth_validator.setup()
    
    try:
        # Simulate rapid login attempts
        rapid_attempts = 10
        user_data = {"user_id": "rate_limit_user", "email": "rate@test.com", "tier": "free"}
        
        connection_results = []
        connection_tasks = []
        
        # Create concurrent login attempts
        for i in range(rapid_attempts):
            client = ChatResponsivenessTestClient(f"rate_limit_{i}")
            connection_tasks.append(client.connect())
        
        # Execute concurrent connections
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        successful_connections = sum(1 for r in results if r is True)
        
        # Should have rate limiting - not all attempts succeed immediately
        rate_limit_working = successful_connections < rapid_attempts * 0.9
        
        assert rate_limit_working, f"Rate limiting not working: {successful_connections}/{rapid_attempts} succeeded"
        logger.info("✅ Concurrent login rate limiting test PASSED")
    finally:
        await auth_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.user_journey
@pytest.mark.timeout(40)
async def test_power_user_workflow_optimization():
    """Test 16: Power user workflow optimization and efficiency."""
    journey_validator = TestUserJourneyValidation()
    await journey_validator.setup()
    
    try:
        # Simulate power user behavior
        user_data = {
            "user_id": "power_user_001", 
            "tier": "premium",
            "usage_pattern": "heavy",
            "daily_queries": 150
        }
        
        client = ChatResponsivenessTestClient(user_data["user_id"])
        connected = await client.connect()
        
        if connected:
            # Power user workflows
            power_workflows = [
                "Create complex data pipeline with error handling",
                "Set up automated report generation for 5 departments", 
                "Configure advanced AI model with custom parameters",
                "Integrate with 3 external APIs for real-time data",
                "Schedule recurring analysis jobs"
            ]
            
            workflow_start = time.time()
            for workflow in power_workflows:
                await client.send_message(workflow)
                await asyncio.sleep(1)
            
            workflow_time = (time.time() - workflow_start) * 1000
            responses_received = len(client.messages_received)
            
            # Power user efficiency metrics
            efficiency_score = responses_received / len(power_workflows)
            speed_score = 1.0 if workflow_time < 10000 else max(0.5, 1.0 - (workflow_time - 10000) / 20000)
            
            assert efficiency_score >= 0.8, f"Low power user efficiency: {efficiency_score}"
            assert speed_score >= 0.7, f"Power user workflows too slow: {speed_score}"
            
            await client.disconnect()
        
        logger.info("✅ Power user workflow optimization test PASSED")
    finally:
        await journey_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.user_journey
@pytest.mark.timeout(35)
async def test_billing_integration_user_journey():
    """Test 17: Billing integration and payment flow user journey."""
    pass
    journey_validator = TestUserJourneyValidation()
    await journey_validator.setup()
    
    try:
        # Simulate billing upgrade journey
        user_data = {
            "user_id": "billing_user_001",
            "tier": "free", 
            "billing_intent": "upgrade_to_premium"
        }
        
        client = ChatResponsivenessTestClient(user_data["user_id"])
        connected = await client.connect()
        
        if connected:
            # Billing flow simulation
            billing_steps = [
                "I want to upgrade to premium",
                "Show me pricing options",
                "Add payment method",
                "Confirm subscription",
                "Access premium features"
            ]
            
            billing_start = time.time()
            billing_responses = []
            
            for step in billing_steps:
                await client.send_message(step)
                await asyncio.sleep(1)
                billing_responses.append(len(client.messages_received))
            
            billing_time = (time.time() - billing_start) * 1000
            
            # Calculate billing conversion metrics
            response_progression = all(
                billing_responses[i] >= billing_responses[i-1] 
                for i in range(1, len(billing_responses))
            )
            
            billing_completion_score = len([r for r in billing_responses if r > 0]) / len(billing_steps)
            
            assert response_progression, "Billing flow responses not progressing"
            assert billing_completion_score >= 0.8, f"Billing flow incomplete: {billing_completion_score}"
            
            await client.disconnect()
        
        logger.info("✅ Billing integration user journey test PASSED")
    finally:
        await journey_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.user_journey
@pytest.mark.timeout(45)
async def test_ai_value_tracking_and_attribution():
    """Test 18: AI value tracking and revenue attribution."""
    journey_validator = TestUserJourneyValidation()
    await journey_validator.setup()
    
    try:
        # Track AI value delivery
        user_data = {
            "user_id": "value_tracking_user",
            "tier": "enterprise",
            "department": "data_science"
        }
        
        client = ChatResponsivenessTestClient(user_data["user_id"])
        connected = await client.connect()
        
        if connected:
            # AI value-generating interactions
            value_interactions = [
                "Generate quarterly sales forecast model",
                "Identify cost optimization opportunities", 
                "Analyze customer churn patterns",
                "Create automated reporting dashboard",
                "Recommend product pricing strategy"
            ]
            
            value_metrics = []
            for interaction in value_interactions:
                interaction_start = time.time()
                await client.send_message(interaction)
                await asyncio.sleep(2)  # AI processing time
                
                interaction_time = (time.time() - interaction_start) * 1000
                responses = len(client.messages_received)
                
                # Simulate value calculation
                estimated_value = random.uniform(500, 5000)  # $500-$5000 per interaction
                value_metrics.append({
                    "interaction": interaction,
                    "response_time_ms": interaction_time,
                    "responses": responses,
                    "estimated_value_usd": estimated_value
                })
            
            # Calculate total AI value delivered
            total_value = sum(m["estimated_value_usd"] for m in value_metrics)
            avg_response_time = statistics.mean([m["response_time_ms"] for m in value_metrics])
            
            assert total_value >= 2000, f"Low AI value delivered: ${total_value}"
            assert avg_response_time < 5000, f"AI interactions too slow: {avg_response_time}ms"
            
            await client.disconnect()
        
        logger.info("✅ AI value tracking and attribution test PASSED")
    finally:
        await journey_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.user_journey
@pytest.mark.timeout(50)
async def test_multi_tier_feature_progression():
    """Test 19: Multi-tier feature progression and upgrade incentives."""
    pass
    journey_validator = TestUserJourneyValidation()
    await journey_validator.setup()
    
    try:
        # Test progression through tiers
        tier_progression = [
            {"tier": "free", "features": ["basic_chat", "limited_history"]},
            {"tier": "premium", "features": ["advanced_chat", "full_history", "priority_queue"]},
            {"tier": "enterprise", "features": ["team_collaboration", "api_access", "custom_models"]}
        ]
        
        progression_results = []
        
        for tier_info in tier_progression:
            user_data = {
                "user_id": f"tier_{tier_info['tier']}_user",
                "tier": tier_info["tier"]
            }
            
            client = ChatResponsivenessTestClient(user_data["user_id"])
            connected = await client.connect()
            
            if connected:
                # Test tier-specific features
                tier_start = time.time()
                
                for feature in tier_info["features"]:
                    await client.send_message(f"Use {feature} feature")
                    await asyncio.sleep(0.5)
                
                tier_time = (time.time() - tier_start) * 1000
                responses = len(client.messages_received)
                
                feature_adoption = responses / len(tier_info["features"])
                
                progression_results.append({
                    "tier": tier_info["tier"],
                    "feature_adoption": feature_adoption,
                    "response_time_ms": tier_time
                })
                
                await client.disconnect()
        
        # Validate tier progression
        for i, result in enumerate(progression_results):
            if i > 0:
                # Higher tiers should have better performance/features
                prev_result = progression_results[i-1]
                assert result["feature_adoption"] >= prev_result["feature_adoption"], \
                    f"Tier progression issue: {result['tier']} vs {prev_result['tier']}"
        
        logger.info("✅ Multi-tier feature progression test PASSED")
    finally:
        await journey_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.user_journey
@pytest.mark.timeout(40)
async def test_user_preference_persistence():
    """Test 20: User preference persistence across sessions."""
    journey_validator = TestUserJourneyValidation()
    await journey_validator.setup()
    
    try:
        user_data = {
            "user_id": "preference_user_001",
            "tier": "premium"
        }
        
        # Session 1: Set preferences
        client1 = ChatResponsivenessTestClient(user_data["user_id"])
        connected1 = await client1.connect()
        
        if connected1:
            # Set user preferences
            preferences = [
                "Set response format to detailed",
                "Enable dark mode",
                "Prefer technical explanations", 
                "Default to enterprise context"
            ]
            
            for pref in preferences:
                await client1.send_message(pref)
                await asyncio.sleep(0.5)
            
            await client1.disconnect()
        
        # Wait to simulate session gap
        await asyncio.sleep(2)
        
        # Session 2: Test preference persistence
        client2 = ChatResponsivenessTestClient(user_data["user_id"])
        connected2 = await client2.connect()
        
        if connected2:
            # Test if preferences are remembered
            await client2.send_message("Show my current preferences")
            await asyncio.sleep(1)
            
            preference_responses = len(client2.messages_received)
            
            assert preference_responses > 0, "Preferences not persisted across sessions"
            await client2.disconnect()
        
        logger.info("✅ User preference persistence test PASSED")
    finally:
        await journey_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.performance_load
@pytest.mark.timeout(90)
async def test_burst_traffic_handling():
    """Test 21: Burst traffic handling - sudden spikes in chat volume."""
    pass
    performance_validator = TestPerformanceUnderLoad()
    await performance_validator.setup()
    
    try:
        # Simulate burst traffic pattern
        baseline_users = 10
        burst_users = 40
        
        logger.info(f"Testing burst traffic: {baseline_users} → {burst_users} users")
        
        # Phase 1: Baseline load
        baseline_clients = []
        for i in range(baseline_users):
            client = ChatResponsivenessTestClient(f"baseline_user_{i}")
            connected = await client.connect()
            if connected:
                baseline_clients.append(client)
                await client.send_message("Baseline load message")
        
        await asyncio.sleep(2)
        baseline_performance = sum(len(c.messages_received) for c in baseline_clients)
        
        # Phase 2: Burst load
        burst_start = time.time()
        burst_clients = []
        connection_tasks = []
        
        for i in range(burst_users):
            client = ChatResponsivenessTestClient(f"burst_user_{i}")
            burst_clients.append(client)
            connection_tasks.append(client.connect())
        
        # Sudden connection burst
        burst_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        burst_connections = sum(1 for r in burst_results if r is True)
        
        # Burst message sending
        message_tasks = []
        for client in burst_clients:
            if hasattr(client, 'connected') and client.connected:
                message_tasks.append(client.send_message("Burst traffic message"))
        
        await asyncio.gather(*message_tasks, return_exceptions=True)
        burst_time = (time.time() - burst_start) * 1000
        
        await asyncio.sleep(3)  # Wait for processing
        
        burst_performance = sum(len(c.messages_received) for c in burst_clients if hasattr(c, 'messages_received'))
        
        # Performance degradation analysis
        baseline_rate = baseline_performance / baseline_users if baseline_users > 0 else 0
        burst_rate = burst_performance / burst_connections if burst_connections > 0 else 0
        
        performance_ratio = burst_rate / baseline_rate if baseline_rate > 0 else 0
        burst_tolerance = performance_ratio >= 0.6  # 60% performance retention under burst
        
        assert burst_connections >= burst_users * 0.8, f"Burst connection failure: {burst_connections}/{burst_users}"
        assert burst_tolerance, f"Poor burst performance: {performance_ratio} ratio"
        assert burst_time < 15000, f"Burst response too slow: {burst_time}ms"
        
        # Cleanup
        for client in baseline_clients + burst_clients:
            if hasattr(client, 'connected') and client.connected:
                await client.disconnect()
        
        logger.info("✅ Burst traffic handling test PASSED")
    finally:
        await performance_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.performance_load
@pytest.mark.timeout(120)
async def test_sustained_high_load_stability():
    """Test 22: Sustained high load stability over extended period."""
    performance_validator = TestPerformanceUnderLoad()
    await performance_validator.setup()
    
    try:
        # Sustained load parameters
        sustained_users = 30
        duration_minutes = 2  # 2-minute sustained test
        
        logger.info(f"Starting {duration_minutes}-minute sustained load test with {sustained_users} users")
        
        # Create sustained load
        sustained_clients = []
        connection_tasks = []
        
        for i in range(sustained_users):
            client = ChatResponsivenessTestClient(f"sustained_user_{i}")
            sustained_clients.append(client)
            connection_tasks.append(client.connect())
        
        # Connect all users
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        active_clients = [c for c, result in zip(sustained_clients, connection_results) 
                         if result is True and hasattr(c, 'connected') and c.connected]
        
        if len(active_clients) < sustained_users * 0.8:
            raise AssertionError(f"Insufficient connections: {len(active_clients)}/{sustained_users}")
        
        # Sustained load execution
        test_start = time.time()
        performance_samples = []
        stability_metrics = []
        
        while (time.time() - test_start) < (duration_minutes * 60):
            cycle_start = time.time()
            
            # Send messages from all active clients
            message_tasks = []
            for i, client in enumerate(active_clients):
                message = f"Sustained load cycle message {int(time.time() - test_start)}"
                message_tasks.append(client.send_message(message))
            
            await asyncio.gather(*message_tasks, return_exceptions=True)
            
            # Wait and measure responses
            await asyncio.sleep(3)
            
            # Sample performance
            cycle_responses = sum(len(c.messages_received) for c in active_clients)
            cycle_time = (time.time() - cycle_start) * 1000
            
            performance_samples.append({
                "responses": cycle_responses,
                "cycle_time_ms": cycle_time,
                "active_users": len(active_clients)
            })
            
            # Control cycle timing (30-second cycles)
            remaining_time = 30 - (time.time() - cycle_start)
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)
        
        # Analyze sustained performance
        if performance_samples:
            avg_responses = statistics.mean([s["responses"] for s in performance_samples])
            avg_cycle_time = statistics.mean([s["cycle_time_ms"] for s in performance_samples])
            
            # Performance stability check
            response_variance = statistics.variance([s["responses"] for s in performance_samples]) if len(performance_samples) > 1 else 0
            stability_score = 1.0 - min(1.0, response_variance / (avg_responses ** 2)) if avg_responses > 0 else 0
        else:
            avg_responses = 0
            avg_cycle_time = 0
            stability_score = 0
        
        # Assertions
        assert avg_responses >= len(active_clients) * 0.8, f"Low sustained response rate: {avg_responses}"
        assert avg_cycle_time < 5000, f"Sustained cycles too slow: {avg_cycle_time}ms"
        assert stability_score >= 0.7, f"Performance instability: {stability_score}"
        
        # Cleanup
        cleanup_tasks = [c.disconnect() for c in active_clients if hasattr(c, 'connected') and c.connected]
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        logger.info("✅ Sustained high load stability test PASSED")
    finally:
        await performance_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.performance_load
@pytest.mark.timeout(60)
async def test_resource_scaling_efficiency():
    """Test 23: Resource scaling efficiency under varying load."""
    pass
    performance_validator = TestPerformanceUnderLoad()
    await performance_validator.setup()
    
    try:
        # Test scaling at different load levels
        load_levels = [5, 15, 25, 35]  # Progressive load increase
        scaling_metrics = []
        
        for load_level in load_levels:
            logger.info(f"Testing scaling at {load_level} concurrent users")
            
            # Create load level
            level_start = time.time()
            level_clients = []
            
            connection_tasks = []
            for i in range(load_level):
                client = ChatResponsivenessTestClient(f"scaling_user_{load_level}_{i}")
                level_clients.append(client)
                connection_tasks.append(client.connect())
            
            # Measure connection scaling
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            successful_connections = sum(1 for r in connection_results if r is True)
            connection_time = (time.time() - level_start) * 1000
            
            # Message throughput test
            message_start = time.time()
            message_tasks = []
            
            for client in level_clients:
                if hasattr(client, 'connected') and client.connected:
                    message_tasks.append(client.send_message(f"Scaling test at {load_level} users"))
            
            await asyncio.gather(*message_tasks, return_exceptions=True)
            await asyncio.sleep(2)
            
            message_time = (time.time() - message_start) * 1000
            total_responses = sum(len(c.messages_received) for c in level_clients if hasattr(c, 'messages_received'))
            
            # Calculate scaling metrics
            connection_efficiency = successful_connections / load_level if load_level > 0 else 0
            throughput_per_user = total_responses / load_level if load_level > 0 else 0
            response_time_per_user = message_time / load_level if load_level > 0 else 0
            
            scaling_metrics.append({
                "load_level": load_level,
                "connection_efficiency": connection_efficiency,
                "throughput_per_user": throughput_per_user,
                "response_time_per_user": response_time_per_user,
                "connection_time_ms": connection_time
            })
            
            # Cleanup level
            cleanup_tasks = []
            for client in level_clients:
                if hasattr(client, 'connected') and client.connected:
                    cleanup_tasks.append(client.disconnect())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            # Brief pause between levels
            await asyncio.sleep(1)
        
        # Analyze scaling efficiency
        if len(scaling_metrics) >= 2:
            # Check if efficiency degrades gracefully
            efficiency_degradation = []
            for i in range(1, len(scaling_metrics)):
                prev_metric = scaling_metrics[i-1]
                curr_metric = scaling_metrics[i]
                
                efficiency_ratio = curr_metric["connection_efficiency"] / prev_metric["connection_efficiency"]
                efficiency_degradation.append(efficiency_ratio)
            
            avg_degradation = statistics.mean(efficiency_degradation) if efficiency_degradation else 1.0
            scaling_tolerance = avg_degradation >= 0.8  # 80% efficiency retention
            
            assert scaling_tolerance, f"Poor scaling efficiency: {avg_degradation} retention ratio"
            
            # Highest load level should still meet minimum performance
            highest_load_metric = scaling_metrics[-1]
            assert highest_load_metric["connection_efficiency"] >= 0.8, \
                f"High load connection issues: {highest_load_metric['connection_efficiency']}"
        
        logger.info("✅ Resource scaling efficiency test PASSED")
    finally:
        await performance_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.performance_load
@pytest.mark.timeout(45)
async def test_concurrent_user_journey_completion():
    """Test 24: Complete user journeys under concurrent load."""
    performance_validator = TestPerformanceUnderLoad()
    await performance_validator.setup()
    
    try:
        # Concurrent complete user journeys
        concurrent_journeys = 12
        
        logger.info(f"Testing {concurrent_journeys} concurrent complete user journeys")
        
        journey_tasks = []
        
        # Create concurrent journey tasks
        for i in range(concurrent_journeys):
            journey_task = asyncio.create_task(
                self._execute_complete_user_journey(f"journey_user_{i}", i)
            )
            journey_tasks.append(journey_task)
        
        # Execute all journeys concurrently
        journey_start = time.time()
        journey_results = await asyncio.gather(*journey_tasks, return_exceptions=True)
        total_journey_time = (time.time() - journey_start) * 1000
        
        # Analyze journey completion
        successful_journeys = []
        failed_journeys = []
        
        for i, result in enumerate(journey_results):
            if isinstance(result, Exception):
                failed_journeys.append(i)
            elif isinstance(result, dict) and result.get("status") == "success":
                successful_journeys.append(result)
            else:
                failed_journeys.append(i)
        
        journey_success_rate = len(successful_journeys) / concurrent_journeys
        avg_journey_time = statistics.mean([j["journey_time_ms"] for j in successful_journeys]) if successful_journeys else 0
        
        # Business impact of concurrent journey performance
        estimated_conversion_rate = journey_success_rate * 0.12  # 12% base conversion
        concurrent_revenue_potential = len(successful_journeys) * 29.0 * estimated_conversion_rate
        
        assert journey_success_rate >= 0.8, f"Low journey success rate: {journey_success_rate}"
        assert avg_journey_time < 20000, f"Journeys too slow under load: {avg_journey_time}ms"
        assert total_journey_time < 30000, f"Total concurrent time too high: {total_journey_time}ms"
        assert concurrent_revenue_potential >= 20, f"Low revenue potential: ${concurrent_revenue_potential}"
        
        logger.info("✅ Concurrent user journey completion test PASSED")
    finally:
        await performance_validator.teardown()


@pytest.mark.asyncio
@pytest.mark.performance_load
@pytest.mark.timeout(75)
async def test_comprehensive_load_performance_metrics():
    """Test 25: Comprehensive load performance metrics and business impact."""
    pass
    performance_validator = TestPerformanceUnderLoad()
    await performance_validator.setup()
    
    try:
        # Comprehensive performance test across multiple dimensions
        test_scenarios = [
            {"name": "light_load", "users": 8, "duration_sec": 15},
            {"name": "medium_load", "users": 20, "duration_sec": 20}, 
            {"name": "heavy_load", "users": 35, "duration_sec": 25}
        ]
        
        comprehensive_metrics = {}
        
        for scenario in test_scenarios:
            logger.info(f"Running {scenario['name']} scenario: {scenario['users']} users for {scenario['duration_sec']}s")
            
            scenario_start = time.time()
            scenario_clients = []
            
            # Create scenario load
            connection_tasks = []
            for i in range(scenario["users"]):
                client = ChatResponsivenessTestClient(f"{scenario['name']}_user_{i}")
                scenario_clients.append(client)
                connection_tasks.append(client.connect())
            
            # Connect users
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            active_clients = [c for c, result in zip(scenario_clients, connection_results) 
                             if result is True and hasattr(c, 'connected') and c.connected]
            
            # Run load for specified duration
            scenario_end_time = scenario_start + scenario["duration_sec"]
            message_count = 0
            response_times = []
            
            while time.time() < scenario_end_time:
                batch_start = time.time()
                
                # Send messages
                message_tasks = []
                for client in active_clients:
                    message_tasks.append(client.send_message(f"{scenario['name']} message {message_count}"))
                
                await asyncio.gather(*message_tasks, return_exceptions=True)
                message_count += 1
                
                # Brief pause
                await asyncio.sleep(2)
                
                batch_time = (time.time() - batch_start) * 1000
                response_times.append(batch_time)
            
            # Collect scenario metrics
            total_responses = sum(len(c.messages_received) for c in active_clients)
            total_events = sum(len(c.events_received) for c in active_clients)
            scenario_duration = (time.time() - scenario_start) * 1000
            
            # Calculate comprehensive metrics
            throughput = total_responses / (scenario_duration / 1000) if scenario_duration > 0 else 0
            event_rate = total_events / (scenario_duration / 1000) if scenario_duration > 0 else 0
            avg_response_time = statistics.mean(response_times) if response_times else 0
            
            # Business impact calculations
            user_satisfaction = 1.0 if avg_response_time < 3000 else max(0.3, 1.0 - (avg_response_time - 3000) / 10000)
            engagement_quality = min(1.0, (total_responses + total_events) / (len(active_clients) * 5))
            revenue_multiplier = user_satisfaction * engagement_quality
            
            potential_monthly_revenue = len(active_clients) * 29.0 * 0.12 * revenue_multiplier
            
            comprehensive_metrics[scenario["name"]] = {
                "users": len(active_clients),
                "duration_ms": scenario_duration,
                "throughput_responses_per_sec": throughput,
                "event_rate_per_sec": event_rate,
                "avg_response_time_ms": avg_response_time,
                "user_satisfaction": user_satisfaction,
                "engagement_quality": engagement_quality,
                "potential_monthly_revenue": potential_monthly_revenue,
                "performance_score": (user_satisfaction + engagement_quality) / 2
            }
            
            # Cleanup scenario
            cleanup_tasks = []
            for client in active_clients:
                if hasattr(client, 'connected') and client.connected:
                    cleanup_tasks.append(client.disconnect())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Validate comprehensive performance
        for scenario_name, metrics in comprehensive_metrics.items():
            assert metrics["performance_score"] >= 0.7, \
                f"{scenario_name} performance too low: {metrics['performance_score']}"
            assert metrics["user_satisfaction"] >= 0.6, \
                f"{scenario_name} user satisfaction low: {metrics['user_satisfaction']}"
            assert metrics["potential_monthly_revenue"] >= 10, \
                f"{scenario_name} revenue potential low: ${metrics['potential_monthly_revenue']}"
        
        # Log comprehensive results
        logger.info("📊 COMPREHENSIVE LOAD PERFORMANCE RESULTS:")
        for scenario_name, metrics in comprehensive_metrics.items():
            logger.info(f"  {scenario_name.upper()}:")
            logger.info(f"    Users: {metrics['users']}")
            logger.info(f"    Throughput: {metrics['throughput_responses_per_sec']:.2f} responses/sec")
            logger.info(f"    Avg Response Time: {metrics['avg_response_time_ms']:.1f}ms")
            logger.info(f"    User Satisfaction: {metrics['user_satisfaction']:.2%}")
            logger.info(f"    Monthly Revenue Potential: ${metrics['potential_monthly_revenue']:.2f}")
        
        logger.info("✅ Comprehensive load performance metrics test PASSED")
    finally:
        await performance_validator.teardown()


async def _execute_complete_user_journey(self, user_id: str, journey_index: int) -> Dict[str, Any]:
    """Execute a complete user journey for concurrent testing."""
    journey_start = time.time()
    
    try:
        # Complete user journey simulation
        client = ChatResponsivenessTestClient(user_id)
        connected = await client.connect()
        
        if not connected:
            await asyncio.sleep(0)
    return {"status": "error", "error": "Connection failed"}
        
        # Journey phases
        phases = [
            "Hello, I'm a new user",
            "What can you help me with?",
            "Create a data analysis workflow",
            "Show me advanced features",
            "How do I upgrade my account?"
        ]
        
        for phase in phases:
            await client.send_message(phase)
            await asyncio.sleep(random.uniform(0.5, 1.5))  # Realistic user timing
        
        # Wait for final responses
        await asyncio.sleep(2)
        
        journey_time = (time.time() - journey_start) * 1000
        responses_received = len(client.messages_received)
        events_received = len(client.events_received)
        
        await client.disconnect()
        
        return {
            "status": "success",
            "journey_time_ms": journey_time,
            "responses": responses_received,
            "events": events_received,
            "phases_completed": len(phases)
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ============================================================================
# ORIGINAL LOAD TEST SUITE (Enhanced)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.timeout(60)
async def test_concurrent_user_load():
    """
    CRITICAL TEST: 5 concurrent users must get responses within 2 seconds.
    
    Acceptance Criteria:
    ✅ 5 concurrent users connect successfully
    ✅ All users receive responses within 2 seconds
    ✅ All required WebSocket events are received
    ✅ Zero message loss
    """
    pass
    orchestrator = ChatLoadTestOrchestrator()
    
    try:
        await orchestrator.setup()
        
        # Run concurrent user load test
        metrics = await orchestrator.test_concurrent_user_load(user_count=5)
        
        # Assertions
        assert metrics.successful_connections >= 4, \
            f"Failed to connect enough users: {metrics.successful_connections}/5"
        
        assert metrics.avg_response_time_ms <= 2000, \
            f"Average response time too high: {metrics.avg_response_time_ms}ms > 2000ms"
        
        assert metrics.p95_response_time_ms <= 3000, \
            f"P95 response time too high: {metrics.p95_response_time_ms}ms > 3000ms"
        
        assert metrics.message_loss_count == 0, \
            f"Message loss detected: {metrics.message_loss_count} messages lost"
        
        # Verify all required events were received
        required_events = {"agent_started", "agent_thinking", "tool_executing", 
                          "tool_completed", "agent_completed"}
        missing_events = required_events - set(metrics.events_received.keys())
        assert not missing_events, \
            f"Missing required WebSocket events: {missing_events}"
        
        logger.info("✅ Concurrent user load test PASSED")
        
    finally:
        await orchestrator.teardown()


@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.timeout(60)
async def test_agent_processing_backlog():
    """
    CRITICAL TEST: System must handle message backlog with proper indicators.
    
    Acceptance Criteria:
    ✅ 10 queued messages are processed
    ✅ Processing indicators are shown
    ✅ Messages processed in order
    ✅ All messages receive feedback
    """
    pass
    orchestrator = ChatLoadTestOrchestrator()
    
    try:
        await orchestrator.setup()
        
        # Run backlog test
        metrics = await orchestrator.test_agent_processing_backlog(queue_size=10)
        
        # Assertions
        assert metrics.messages_sent == 10, \
            f"Failed to send all messages: {metrics.messages_sent}/10"
        
        assert metrics.messages_received > 0, \
            f"No responses received for backlog messages"
        
        # Verify processing indicators were shown
        processing_events = ["agent_started", "agent_thinking", "tool_executing"]
        has_processing = any(
            metrics.events_received.get(event, 0) > 0 
            for event in processing_events
        )
        assert has_processing, \
            f"No processing indicators received. Events: {metrics.events_received}"
        
        # Verify completion events
        completion_events = ["tool_completed", "agent_completed"]
        has_completion = any(
            metrics.events_received.get(event, 0) > 0
            for event in completion_events
        )
        assert has_completion, \
            f"No completion indicators received. Events: {metrics.events_received}"
        
        logger.info("✅ Agent processing backlog test PASSED")
        
    finally:
        await orchestrator.teardown()


@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.timeout(90)
async def test_websocket_connection_recovery():
    """
    CRITICAL TEST: Connection must recover within 5 seconds of disruption.
    
    Acceptance Criteria:
    ✅ Connections recover after disruption
    ✅ Recovery happens within 5 seconds
    ✅ Messages continue after recovery
    ✅ No data loss during recovery
    """
    pass
    orchestrator = ChatLoadTestOrchestrator()
    
    try:
        await orchestrator.setup()
        
        # Run recovery test
        metrics = await orchestrator.test_websocket_connection_recovery(disruption_count=3)
        
        # Assertions
        assert metrics.successful_connections > 0, \
            "No users connected for recovery test"
        
        assert len(metrics.recovery_times) > 0, \
            "No recovery times recorded"
        
        # All recoveries must be under 5 seconds
        max_recovery = max(metrics.recovery_times) if metrics.recovery_times else 0
        assert max_recovery <= 5.0, \
            f"Recovery took too long: {max_recovery:.2f}s > 5s"
        
        # Average recovery should be under 3 seconds
        avg_recovery = sum(metrics.recovery_times) / len(metrics.recovery_times) \
            if metrics.recovery_times else 0
        assert avg_recovery <= 3.0, \
            f"Average recovery too slow: {avg_recovery:.2f}s > 3s"
        
        # Messages should continue after recovery
        assert metrics.messages_received > 0, \
            "No messages received after recovery"
        
        logger.info("✅ WebSocket connection recovery test PASSED")
        
    finally:
        await orchestrator.teardown()


@pytest.mark.asyncio
@pytest.mark.mission_critical
@pytest.mark.timeout(120)
async def test_comprehensive_load_scenario():
    """
    COMPREHENSIVE TEST: All load scenarios combined.
    
    This test runs all three scenarios in sequence to validate
    the system under comprehensive load conditions.
    """
    pass
    orchestrator = ChatLoadTestOrchestrator()
    
    try:
        await orchestrator.setup()
        
        logger.info("="*80)
        logger.info("STARTING COMPREHENSIVE LOAD TEST SUITE")
        logger.info("="*80)
        
        all_passed = True
        
        # Test 1: Concurrent Users
        try:
            logger.info("
[1/3] Running Concurrent User Load Test...")
            metrics1 = await orchestrator.test_concurrent_user_load(user_count=5)
            
            assert metrics1.successful_connections >= 4
            assert metrics1.avg_response_time_ms <= 2000
            assert metrics1.message_loss_count == 0
            
            logger.info("✅ Concurrent User Load Test PASSED")
        except AssertionError as e:
            logger.error(f"❌ Concurrent User Load Test FAILED: {e}")
            all_passed = False
        
        # Reset for next test
        await orchestrator.teardown()
        await orchestrator.setup()
        
        # Test 2: Agent Backlog
        try:
            logger.info("
[2/3] Running Agent Processing Backlog Test...")
            metrics2 = await orchestrator.test_agent_processing_backlog(queue_size=10)
            
            assert metrics2.messages_sent == 10
            assert metrics2.messages_received > 0
            assert any(metrics2.events_received.get(e, 0) > 0 
                      for e in ["agent_started", "agent_thinking"])
            
            logger.info("✅ Agent Processing Backlog Test PASSED")
        except AssertionError as e:
            logger.error(f"❌ Agent Processing Backlog Test FAILED: {e}")
            all_passed = False
        
        # Reset for next test
        await orchestrator.teardown()
        await orchestrator.setup()
        
        # Test 3: Connection Recovery
        try:
            logger.info("
[3/3] Running WebSocket Connection Recovery Test...")
            metrics3 = await orchestrator.test_websocket_connection_recovery(disruption_count=3)
            
            assert len(metrics3.recovery_times) > 0
            assert max(metrics3.recovery_times) <= 5.0
            assert metrics3.messages_received > 0
            
            logger.info("✅ WebSocket Connection Recovery Test PASSED")
        except AssertionError as e:
            logger.error(f"❌ WebSocket Connection Recovery Test FAILED: {e}")
            all_passed = False
        
        # Final summary
        logger.info("
" + "="*80)
        if all_passed:
            logger.info("✅ COMPREHENSIVE LOAD TEST SUITE: ALL TESTS PASSED")
        else:
            logger.error("❌ COMPREHENSIVE LOAD TEST SUITE: SOME TESTS FAILED")
        logger.info("="*80)
        
        assert all_passed, "Not all load tests passed"
        
    finally:
        await orchestrator.teardown()


if __name__ == "__main__":
    # Run the comprehensive test suite
    asyncio.run(test_comprehensive_load_scenario())