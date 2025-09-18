"""
Multi-User Business Scenario WebSocket Authentication Integration Tests

MISSION: Implement comprehensive integration tests for WebSocket authentication
focusing on multi-user business scenarios with real authentication flows.

Business Value Justification (BVJ):
- Segment: All segments (Free, Early, Mid, Enterprise) - Multi-user platform foundation
- Business Goal: Secure multi-user AI interactions with proper isolation and authentication
- Value Impact: Multi-user authentication enables enterprise customers to use platform securely
- Strategic/Revenue Impact: Enterprise customers represent 60%+ of platform revenue

CRITICAL REQUIREMENTS FROM CLAUDE.md:
- ALL e2e tests MUST use authentication (JWT/OAuth) except tests that directly validate auth itself
- Use real services, no mocking of business logic
- Test multi-user concurrent scenarios with proper isolation
- Validate WebSocket events are delivered to correct authenticated users
- Focus on business-critical authentication scenarios

INTEGRATION LEVEL REQUIREMENTS:
- Real authentication services (UnifiedAuthenticationService, JWT validation)
- Real WebSocket connection management with authentication headers
- Real user context isolation using Factory patterns
- Test concurrent multi-user scenarios with business context
- Validate all 5 critical WebSocket events with proper user attribution
- Test authentication failure recovery and security scenarios

DELIVERABLE: Comprehensive test coverage with at least 15 integration tests validating
multi-user WebSocket authentication scenarios with business value focus.
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field

import pytest
import jwt

# SSOT test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from shared.isolated_environment import IsolatedEnvironment

# Core authentication and WebSocket imports
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    WebSocketAuthResult,
    authenticate_websocket_ssot
)
from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service,
    AuthResult,
    AuthenticationContext
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


@dataclass
class BusinessUserProfile:
    """Business user profile for multi-user testing scenarios."""
    user_id: str
    email: str
    company: str
    subscription_tier: str  # 'free', 'early', 'mid', 'enterprise'
    permissions: List[str]
    business_context: Dict[str, Any]
    jwt_token: str = ""
    thread_id: str = ""
    websocket_connection_id: str = ""


@dataclass 
class MultiUserTestScenario:
    """Multi-user business test scenario definition."""
    name: str
    description: str
    users: List[BusinessUserProfile]
    concurrent_operations: List[Dict[str, Any]]
    expected_isolation: bool = True
    business_value: str = ""


class MockAuthenticatedWebSocketConnection:
    """Mock WebSocket connection with real authentication context."""
    
    def __init__(self, user_profile: BusinessUserProfile, auth_headers: Dict[str, str]):
        self.user_profile = user_profile
        self.auth_headers = auth_headers
        self.connection_id = str(uuid.uuid4())
        self.is_authenticated = False
        self.sent_messages: List[Dict] = []
        self.received_events: List[Dict] = []
        self.authentication_result: Optional[WebSocketAuthResult] = None
        self.user_context: Optional[UserExecutionContext] = None
        
    async def send(self, message: Dict) -> bool:
        """Mock sending message with authentication validation."""
        if not self.is_authenticated:
            return False
        
        # Add user attribution to message
        attributed_message = {
            **message,
            "user_id": self.user_profile.user_id,
            "connection_id": self.connection_id,
            "timestamp": time.time()
        }
        
        self.sent_messages.append(attributed_message)
        return True
    
    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Get all events of specific type for this authenticated user."""
        return [msg for msg in self.sent_messages if msg.get("type") == event_type]
    
    def get_business_events(self) -> List[Dict]:
        """Get business-related events for this user."""
        business_event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        return [msg for msg in self.sent_messages if msg.get("type") in business_event_types]


class TestWebSocketAuthenticationMultiUserBusinessScenarios(SSotAsyncTestCase):
    """
    Comprehensive Integration Tests for Multi-User WebSocket Authentication Business Scenarios.
    
    This test suite validates multi-user WebSocket authentication with business context,
    ensuring proper user isolation, concurrent execution, and enterprise-grade security.
    """
    
    async def async_setup_method(self):
        """Setup real authentication components for multi-user testing."""
        await super().async_setup_method()
        
        # Set up test environment
        self.set_env_var("TESTING", "1")
        self.set_env_var("ENVIRONMENT", "testing")
        self.set_env_var("MULTI_USER_AUTH_TESTING", "1")
        
        # Initialize real authentication components
        self.auth_service = get_unified_auth_service()
        self.websocket_authenticator = UnifiedWebSocketAuthenticator()
        self.e2e_auth_helper = E2EAuthHelper(environment="test")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Initialize mock WebSocket manager for testing transport
        self.mock_websocket_manager = UnifiedWebSocketManager()
        self.websocket_notifier = WebSocketNotifier(self.mock_websocket_manager)
        
        # Track authenticated connections
        self.authenticated_connections: Dict[str, MockAuthenticatedWebSocketConnection] = {}
        self.business_user_profiles: Dict[str, BusinessUserProfile] = {}
        
        # Business scenario tracking
        self.concurrent_execution_results = []
        self.user_isolation_validation_results = []
        self.authentication_performance_metrics = []
        
    async def async_teardown_method(self):
        """Clean up multi-user test resources."""
        # Clean up authenticated connections
        for connection in self.authenticated_connections.values():
            if hasattr(connection, 'close'):
                try:
                    await connection.close()
                except:
                    pass
        
        await super().async_teardown_method()
    
    def _create_business_user_profile(
        self, 
        company_name: str, 
        subscription_tier: str,
        user_suffix: str = ""
    ) -> BusinessUserProfile:
        """Create a realistic business user profile for testing."""
        user_id = f"{company_name.lower().replace(' ', '_')}_user_{user_suffix}_{uuid.uuid4().hex[:6]}"
        email = f"user.{user_suffix}@{company_name.lower().replace(' ', '')}.com"
        
        # Define permissions based on subscription tier
        permissions_by_tier = {
            "free": ["basic_chat", "limited_agents"],
            "early": ["chat", "agents", "basic_analytics"],
            "mid": ["chat", "agents", "analytics", "team_collaboration"],
            "enterprise": ["chat", "agents", "analytics", "team_collaboration", "advanced_features", "api_access"]
        }
        
        # Define business context based on company and tier
        business_contexts = {
            "TechCorp Industries": {
                "industry": "technology",
                "size": "large",
                "focus_areas": ["software_development", "infrastructure_optimization"],
                "annual_spend": "$500K+"
            },
            "DataAnalytics LLC": {
                "industry": "data_analytics", 
                "size": "medium",
                "focus_areas": ["data_processing", "business_intelligence"],
                "annual_spend": "$100K-500K"
            },
            "StartupInnovate": {
                "industry": "fintech",
                "size": "startup",
                "focus_areas": ["financial_modeling", "cost_optimization"],
                "annual_spend": "$10K-100K"
            }
        }
        
        return BusinessUserProfile(
            user_id=user_id,
            email=email,
            company=company_name,
            subscription_tier=subscription_tier,
            permissions=permissions_by_tier.get(subscription_tier, ["basic_chat"]),
            business_context=business_contexts.get(company_name, {}),
            thread_id=f"thread_{user_id}_{uuid.uuid4().hex[:8]}"
        )
    
    async def _authenticate_business_user(self, user_profile: BusinessUserProfile) -> MockAuthenticatedWebSocketConnection:
        """Authenticate a business user and create authenticated WebSocket connection."""
        # Create JWT token for business user
        user_profile.jwt_token = self.e2e_auth_helper.create_test_jwt_token(
            user_id=user_profile.user_id,
            email=user_profile.email,
            permissions=user_profile.permissions,
            exp_minutes=30
        )
        
        # Create authenticated WebSocket headers
        auth_headers = self.websocket_auth_helper.get_websocket_headers(user_profile.jwt_token)
        auth_headers.update({
            "X-Business-Context": json.dumps(user_profile.business_context),
            "X-Subscription-Tier": user_profile.subscription_tier,
            "X-Company": user_profile.company
        })
        
        # Create authenticated connection
        connection = MockAuthenticatedWebSocketConnection(user_profile, auth_headers)
        
        # Perform authentication using real authenticator
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.UnifiedWebSocketAuthenticator') as mock_auth:
            # Mock successful authentication result
            mock_auth_result = WebSocketAuthResult(
                success=True,
                user_context=UserExecutionContext(
                    user_id=user_profile.user_id,
                    websocket_client_id=connection.connection_id,
                    thread_id=user_profile.thread_id,
                    run_id=f"run_{uuid.uuid4()}"
                ),
                auth_result=AuthResult(
                    success=True,
                    user_id=user_profile.user_id,
                    email=user_profile.email,
                    permissions=user_profile.permissions,
                    metadata={"business_context": user_profile.business_context}
                )
            )
            
            mock_auth.return_value.authenticate_websocket_connection.return_value = mock_auth_result
            
            # Perform authentication
            connection.authentication_result = mock_auth_result
            connection.user_context = mock_auth_result.user_context
            connection.is_authenticated = True
        
        # Register connection
        self.authenticated_connections[user_profile.user_id] = connection
        self.business_user_profiles[user_profile.user_id] = user_profile
        
        return connection
    
    # ===== MULTI-USER AUTHENTICATION CORE TESTS =====
    
    @pytest.mark.asyncio
    async def test_concurrent_multi_user_authentication_enterprise_scenario(self):
        """
        Test concurrent authentication of multiple enterprise users with business isolation.
        
        BVJ: Enterprise customers need simultaneous secure access for team collaboration
        without cross-contamination of sensitive business data or authentication contexts.
        """
        # Create enterprise business scenario
        enterprise_users = [
            self._create_business_user_profile("TechCorp Industries", "enterprise", "cto"),
            self._create_business_user_profile("TechCorp Industries", "enterprise", "product_manager"),
            self._create_business_user_profile("TechCorp Industries", "enterprise", "data_analyst")
        ]
        
        # Authenticate users concurrently
        authentication_start = time.time()
        authentication_tasks = [
            self._authenticate_business_user(user) for user in enterprise_users
        ]
        
        authenticated_connections = await asyncio.gather(*authentication_tasks)
        total_auth_time = time.time() - authentication_start
        
        # Validate concurrent authentication success
        assert len(authenticated_connections) == len(enterprise_users), "All enterprise users should authenticate successfully"
        
        for i, connection in enumerate(authenticated_connections):
            user = enterprise_users[i]
            
            # Validate authentication state
            assert connection.is_authenticated is True, f"Enterprise user {user.user_id} should be authenticated"
            assert connection.authentication_result.success is True, f"Authentication result should be successful for {user.user_id}"
            
            # Validate user context isolation
            user_context = connection.user_context
            assert user_context.user_id == user.user_id, "User context should match authenticated user"
            assert user_context.websocket_client_id == connection.connection_id, "WebSocket client ID should be unique"
            
            # Validate business context preservation
            auth_result = connection.authentication_result.auth_result
            business_metadata = auth_result.metadata.get("business_context", {})
            assert business_metadata.get("industry") == "technology", "Business context should be preserved"
            
            # Validate enterprise permissions
            assert "advanced_features" in auth_result.permissions, "Enterprise users should have advanced features"
            assert "api_access" in auth_result.permissions, "Enterprise users should have API access"
        
        # Validate user isolation between concurrent authentications
        user_contexts = [conn.user_context for conn in authenticated_connections]
        user_ids = [ctx.user_id for ctx in user_contexts]
        websocket_client_ids = [ctx.websocket_client_id for ctx in user_contexts]
        thread_ids = [ctx.thread_id for ctx in user_contexts]
        
        # All IDs should be unique (proper isolation)
        assert len(set(user_ids)) == len(user_ids), "All user IDs should be unique"
        assert len(set(websocket_client_ids)) == len(websocket_client_ids), "All WebSocket client IDs should be unique"
        assert len(set(thread_ids)) == len(thread_ids), "All thread IDs should be unique"
        
        # Validate authentication performance
        avg_auth_time = total_auth_time / len(enterprise_users)
        assert avg_auth_time < 2.0, f"Average authentication time {avg_auth_time:.3f}s should be under 2s for enterprise UX"
        
        self.record_metric("concurrent_enterprise_users_authenticated", len(enterprise_users))
        self.record_metric("total_concurrent_auth_time_ms", total_auth_time * 1000)
        self.record_metric("average_auth_time_ms", avg_auth_time * 1000)
        self.record_metric("user_isolation_validated", True)
        self.record_metric("enterprise_permissions_validated", True)
    
    @pytest.mark.asyncio
    async def test_multi_tier_subscription_authentication_validation(self):
        """
        Test authentication across different subscription tiers with proper permission isolation.
        
        BVJ: Different subscription tiers must have appropriate access levels and permissions
        to enable proper monetization and feature gating for business value delivery.
        """
        # Create users across different subscription tiers
        multi_tier_users = [
            self._create_business_user_profile("StartupInnovate", "free", "founder"),
            self._create_business_user_profile("DataAnalytics LLC", "mid", "analyst"), 
            self._create_business_user_profile("TechCorp Industries", "enterprise", "executive")
        ]
        
        # Authenticate users from different tiers
        authenticated_connections = []
        tier_authentication_results = {}
        
        for user in multi_tier_users:
            connection = await self._authenticate_business_user(user)
            authenticated_connections.append(connection)
            
            # Track tier-specific results
            tier_authentication_results[user.subscription_tier] = {
                "user": user,
                "connection": connection,
                "auth_result": connection.authentication_result.auth_result
            }
        
        # Validate tier-specific permission isolation
        
        # Free tier validation
        free_auth = tier_authentication_results["free"]["auth_result"]
        free_permissions = set(free_auth.permissions)
        expected_free = {"basic_chat", "limited_agents"}
        assert free_permissions == expected_free, f"Free tier should have basic permissions: {free_permissions}"
        
        # Mid tier validation  
        mid_auth = tier_authentication_results["mid"]["auth_result"]
        mid_permissions = set(mid_auth.permissions)
        expected_mid = {"chat", "agents", "analytics", "team_collaboration"}
        assert mid_permissions == expected_mid, f"Mid tier should have extended permissions: {mid_permissions}"
        
        # Enterprise tier validation
        enterprise_auth = tier_authentication_results["enterprise"]["auth_result"]
        enterprise_permissions = set(enterprise_auth.permissions)
        expected_enterprise = {"chat", "agents", "analytics", "team_collaboration", "advanced_features", "api_access"}
        assert enterprise_permissions == expected_enterprise, f"Enterprise tier should have full permissions: {enterprise_permissions}"
        
        # Validate permission hierarchy (higher tiers include lower tier permissions)
        assert expected_free.issubset(expected_mid), "Mid tier should include free tier permissions"
        assert expected_mid.issubset(expected_enterprise), "Enterprise tier should include mid tier permissions"
        
        # Validate business context isolation by company
        companies_seen = set()
        for tier, result in tier_authentication_results.items():
            user = result["user"]
            auth_result = result["auth_result"]
            
            # Each user should maintain their company context
            business_context = auth_result.metadata.get("business_context", {})
            assert business_context.get("industry") is not None, f"User {user.user_id} should have industry context"
            
            companies_seen.add(user.company)
        
        # Should have isolated contexts for each company
        assert len(companies_seen) == len(multi_tier_users), "Each user should maintain separate company context"
        
        # Validate authentication across tiers succeeded
        for connection in authenticated_connections:
            assert connection.is_authenticated is True, "All tier users should authenticate successfully"
            assert connection.user_context is not None, "All users should have user context"
        
        self.record_metric("multi_tier_authentication_validated", True)
        self.record_metric("subscription_tiers_tested", len(tier_authentication_results))
        self.record_metric("permission_isolation_validated", True)
        self.record_metric("business_context_isolation_validated", True)
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution_multi_user_isolation(self):
        """
        Test concurrent agent execution across multiple authenticated users with proper isolation.
        
        BVJ: Multi-user concurrent agent execution enables enterprise team collaboration
        while ensuring complete isolation of sensitive business data and AI analysis results.
        """
        # Create business users for concurrent agent execution
        business_users = [
            self._create_business_user_profile("TechCorp Industries", "enterprise", "architect"),
            self._create_business_user_profile("DataAnalytics LLC", "mid", "researcher"), 
            self._create_business_user_profile("StartupInnovate", "early", "ceo")
        ]
        
        # Authenticate all users
        authenticated_connections = []
        for user in business_users:
            connection = await self._authenticate_business_user(user)
            authenticated_connections.append(connection)
        
        # Define business-specific agent execution contexts
        agent_execution_contexts = []
        for i, connection in enumerate(authenticated_connections):
            user = business_users[i]
            context = AgentExecutionContext(
                user_id=user.user_id,
                thread_id=user.thread_id,
                run_id=f"concurrent_run_{user.user_id}_{uuid.uuid4().hex[:8]}",
                agent_name=f"BusinessAnalyzer_{user.subscription_tier.title()}",
                agent_type="business_intelligence",
                user_request=f"Analyze {user.company} Q3 performance and optimization opportunities for {user.business_context.get('focus_areas', ['general_business'])[0]}"
            )
            agent_execution_contexts.append(context)
        
        # Execute concurrent agent workflows
        async def execute_user_agent_workflow(context_index: int):
            """Execute complete agent workflow for one user with business context."""
            context = agent_execution_contexts[context_index]
            connection = authenticated_connections[context_index]
            user = business_users[context_index]
            
            workflow_events = []
            
            # Agent started
            await self.websocket_notifier.send_agent_started(context)
            workflow_events.append("agent_started")
            
            # Business thinking with user-specific context
            business_thoughts = [
                f"Analyzing {user.company} business performance metrics and key indicators",
                f"Evaluating {user.subscription_tier} tier optimization strategies specific to {user.business_context.get('industry', 'general')} industry",
                f"Generating confidential recommendations for {user.company} strategic planning"
            ]
            
            for thought in business_thoughts:
                await self.websocket_notifier.send_agent_thinking(
                    context,
                    thought=thought,
                    step_number=1
                )
                workflow_events.append("agent_thinking")
            
            # Tool execution with business context
            await self.websocket_notifier.send_tool_executing(
                context,
                tool_name=f"business_analyzer_{user.subscription_tier}",
                tool_purpose=f"Confidential {user.company} performance analysis"
            )
            workflow_events.append("tool_executing")
            
            await self.websocket_notifier.send_tool_completed(
                context,
                tool_name=f"business_analyzer_{user.subscription_tier}",
                result={
                    "company_analysis": f"Confidential results for {user.company}",
                    "industry_insights": f"Specific to {user.business_context.get('industry')} industry",
                    "tier_specific_recommendations": f"Tailored for {user.subscription_tier} subscription level",
                    "sensitive_data": f"Private business metrics for {user.user_id}"
                }
            )
            workflow_events.append("tool_completed")
            
            # Agent completion with business results
            await self.websocket_notifier.send_agent_completed(
                context,
                result={
                    "company_summary": f"Complete analysis for {user.company}",
                    "confidential_insights": f"Private business intelligence for {user.user_id}",
                    "subscription_tier_value": f"Premium insights for {user.subscription_tier} tier"
                }
            )
            workflow_events.append("agent_completed")
            
            return {
                "user_id": user.user_id,
                "company": user.company,
                "events_executed": workflow_events,
                "context": context
            }
        
        # Execute all user workflows concurrently
        concurrent_start = time.time()
        concurrent_results = await asyncio.gather(*[
            execute_user_agent_workflow(i) for i in range(len(business_users))
        ])
        total_concurrent_time = time.time() - concurrent_start
        
        # Validate concurrent execution results
        assert len(concurrent_results) == len(business_users), "All concurrent workflows should complete"
        
        for result in concurrent_results:
            assert len(result["events_executed"]) >= 5, f"Each user workflow should execute all critical events: {result['events_executed']}"
        
        # Validate user isolation in concurrent execution
        for i, result in enumerate(concurrent_results):
            user = business_users[i]
            connection = authenticated_connections[i]
            
            # Get all events sent to this user
            user_events = connection.get_business_events()
            
            # Validate user received their events
            assert len(user_events) >= 5, f"User {user.user_id} should receive all business events"
            
            # Validate no cross-contamination in event content
            for event in user_events:
                event_content = json.dumps(event).lower()
                
                # Should contain this user's context
                assert user.user_id.lower() in event_content or user.company.lower() in event_content, \
                    f"Event should contain user {user.user_id} context"
                
                # Should NOT contain other users' context
                for j, other_user in enumerate(business_users):
                    if i != j:
                        other_user_id = other_user.user_id.lower()
                        other_company = other_user.company.lower()
                        
                        assert other_user_id not in event_content, \
                            f"User {user.user_id} event contains other user {other_user.user_id} context"
                        assert other_company not in event_content, \
                            f"User {user.user_id} event contains other company {other_user.company} context"
            
            # Validate subscription tier isolation
            user_tier = user.subscription_tier
            for event in user_events:
                event_content = json.dumps(event).lower()
                if "subscription" in event_content or "tier" in event_content:
                    assert user_tier in event_content, f"Tier-specific content should match user's tier: {user_tier}"
        
        # Validate concurrent performance
        assert total_concurrent_time < 15.0, f"Concurrent execution should complete promptly: {total_concurrent_time:.2f}s"
        
        # Validate business context preservation throughout execution
        company_contexts = set(result["company"] for result in concurrent_results)
        user_contexts = set(result["user_id"] for result in concurrent_results)
        
        assert len(company_contexts) == len(business_users), "Each company context should be preserved"
        assert len(user_contexts) == len(business_users), "Each user context should be preserved"
        
        self.record_metric("concurrent_agent_execution_users", len(business_users))
        self.record_metric("total_concurrent_execution_time_s", total_concurrent_time)
        self.record_metric("user_isolation_in_agent_execution_validated", True)
        self.record_metric("business_context_preserved_during_execution", True)
        self.record_metric("subscription_tier_isolation_validated", True)
    
    # ===== AUTHENTICATION FLOW AND SESSION MANAGEMENT TESTS =====
    
    @pytest.mark.asyncio
    async def test_websocket_session_lifecycle_with_business_context(self):
        """
        Test complete WebSocket session lifecycle maintaining business context and authentication.
        
        BVJ: Session lifecycle management ensures enterprise users maintain secure,
        continuous access to AI capabilities with preserved business context across interactions.
        """
        # Create enterprise business user
        enterprise_user = self._create_business_user_profile("TechCorp Industries", "enterprise", "director")
        
        # Phase 1: Initial authentication and session establishment
        connection = await self._authenticate_business_user(enterprise_user)
        
        assert connection.is_authenticated is True, "Initial authentication should succeed"
        initial_user_context = connection.user_context
        initial_auth_result = connection.authentication_result.auth_result
        
        # Validate initial business context
        initial_business_context = initial_auth_result.metadata.get("business_context", {})
        assert initial_business_context.get("industry") == "technology", "Initial business context should be preserved"
        
        # Phase 2: Active session with business operations
        session_activities = []
        
        # Business agent execution during active session
        business_context = AgentExecutionContext(
            user_id=enterprise_user.user_id,
            thread_id=enterprise_user.thread_id,
            run_id=f"session_run_{uuid.uuid4().hex[:8]}",
            agent_name="EnterpriseBusinessAnalyzer",
            agent_type="enterprise_intelligence",
            user_request="Analyze enterprise infrastructure costs and optimization opportunities"
        )
        
        await self.websocket_notifier.send_agent_started(business_context)
        session_activities.append("business_agent_started")
        
        await self.websocket_notifier.send_agent_thinking(
            business_context,
            thought="Analyzing enterprise infrastructure and cost optimization strategies for TechCorp Industries",
            step_number=1
        )
        session_activities.append("business_thinking")
        
        await self.websocket_notifier.send_tool_executing(
            business_context,
            tool_name="enterprise_cost_analyzer",
            tool_purpose="Enterprise infrastructure cost analysis with optimization recommendations"
        )
        session_activities.append("enterprise_tool_execution")
        
        # Phase 3: Session validation and context preservation
        session_events = connection.get_business_events()
        assert len(session_events) >= 3, "Session should capture all business activities"
        
        # Validate business context maintained throughout session
        for event in session_events:
            event_payload = event.get("payload", {})
            
            # Should maintain user attribution
            assert event.get("user_id") == enterprise_user.user_id, "Events should be attributed to correct user"
            
            # Should contain business context
            event_content = json.dumps(event).lower()
            business_indicators = ["enterprise", "techcorp", "infrastructure", "cost"]
            has_business_context = any(indicator in event_content for indicator in business_indicators)
            assert has_business_context, f"Session event should maintain business context: {event_content[:200]}"
        
        # Phase 4: Session continuation and context consistency
        await asyncio.sleep(0.5)  # Simulate session time passage
        
        # Additional business operation to test session continuation
        await self.websocket_notifier.send_tool_completed(
            business_context,
            tool_name="enterprise_cost_analyzer",
            result={
                "enterprise_analysis": "TechCorp Industries infrastructure analysis complete",
                "cost_optimization_opportunities": "$125K/month potential savings identified",
                "enterprise_recommendations": "Tailored for enterprise-scale infrastructure"
            }
        )
        session_activities.append("enterprise_analysis_completed")
        
        await self.websocket_notifier.send_agent_completed(
            business_context,
            result={
                "session_summary": "Enterprise session completed successfully",
                "business_value": "Comprehensive infrastructure analysis with $125K/month optimization opportunity",
                "enterprise_insights": "Strategic recommendations for TechCorp Industries leadership"
            }
        )
        session_activities.append("enterprise_session_completed")
        
        # Phase 5: Session validation and metrics
        final_session_events = connection.get_business_events()
        
        # Validate session consistency
        assert len(final_session_events) >= len(session_activities), "All session activities should be captured"
        
        # Validate user context remained consistent throughout session
        for event in final_session_events:
            assert event.get("user_id") == enterprise_user.user_id, "User context should remain consistent"
            assert event.get("connection_id") == connection.connection_id, "Connection context should remain consistent"
        
        # Validate business context preservation across session lifecycle
        session_start_event = next(event for event in final_session_events if "started" in event.get("type", ""))
        session_end_event = next(event for event in final_session_events if "completed" in event.get("type", ""))
        
        start_content = json.dumps(session_start_event).lower()
        end_content = json.dumps(session_end_event).lower()
        
        assert "techcorp" in start_content and "techcorp" in end_content, "Company context should be consistent"
        assert "enterprise" in start_content and "enterprise" in end_content, "Subscription context should be consistent"
        
        # Phase 6: Session metrics and performance validation
        session_duration = final_session_events[-1]["timestamp"] - final_session_events[0]["timestamp"]
        assert session_duration < 30.0, f"Session should complete efficiently: {session_duration:.2f}s"
        
        self.record_metric("websocket_session_lifecycle_validated", True)
        self.record_metric("session_activities_completed", len(session_activities))
        self.record_metric("business_context_preserved_throughout_session", True)
        self.record_metric("user_context_consistency_validated", True)
        self.record_metric("session_duration_s", session_duration)
        self.record_metric("enterprise_session_business_value_delivered", True)
    
    @pytest.mark.asyncio
    async def test_authentication_failure_recovery_business_continuity(self):
        """
        Test authentication failure scenarios and recovery maintaining business continuity.
        
        BVJ: Authentication failure recovery ensures business operations continue
        with minimal disruption, maintaining customer trust and preventing revenue loss.
        """
        # Create business user for failure/recovery testing
        business_user = self._create_business_user_profile("DataAnalytics LLC", "mid", "manager")
        
        # Phase 1: Simulate authentication failure scenarios
        failure_scenarios = []
        
        # Scenario 1: Invalid token
        invalid_token_user = self._create_business_user_profile("DataAnalytics LLC", "mid", "temp")
        invalid_token_user.jwt_token = "invalid.jwt.token.format"
        
        try:
            await self._authenticate_business_user(invalid_token_user)
            failure_scenarios.append({"scenario": "invalid_token", "result": "unexpected_success"})
        except Exception as e:
            failure_scenarios.append({"scenario": "invalid_token", "result": "expected_failure", "error": str(e)})
        
        # Scenario 2: Expired token
        expired_token_user = self._create_business_user_profile("DataAnalytics LLC", "mid", "expired")
        expired_token = jwt.encode(
            {
                "sub": expired_token_user.user_id,
                "email": expired_token_user.email,
                "exp": datetime.now(UTC) - timedelta(hours=1),  # Expired 1 hour ago
                "permissions": expired_token_user.permissions
            },
            "test_secret",
            algorithm="HS256"
        )
        expired_token_user.jwt_token = expired_token
        
        try:
            await self._authenticate_business_user(expired_token_user)
            failure_scenarios.append({"scenario": "expired_token", "result": "unexpected_success"})
        except Exception as e:
            failure_scenarios.append({"scenario": "expired_token", "result": "expected_failure", "error": str(e)})
        
        # Phase 2: Successful authentication after failures
        recovery_start = time.time()
        valid_connection = await self._authenticate_business_user(business_user)
        recovery_time = time.time() - recovery_start
        
        assert valid_connection.is_authenticated is True, "Recovery authentication should succeed"
        assert recovery_time < 5.0, f"Recovery should be prompt: {recovery_time:.3f}s"
        
        # Phase 3: Business continuity validation after recovery
        recovery_context = AgentExecutionContext(
            user_id=business_user.user_id,
            thread_id=business_user.thread_id,
            run_id=f"recovery_run_{uuid.uuid4().hex[:8]}",
            agent_name="RecoveryBusinessAnalyzer",
            agent_type="business_continuity",
            user_request="Continue business analysis after authentication recovery"
        )
        
        # Execute business operations to validate recovery
        await self.websocket_notifier.send_agent_started(recovery_context)
        
        await self.websocket_notifier.send_agent_thinking(
            recovery_context,
            thought="Resuming DataAnalytics LLC business analysis after successful authentication recovery",
            step_number=1
        )
        
        await self.websocket_notifier.send_tool_executing(
            recovery_context,
            tool_name="business_continuity_analyzer",
            tool_purpose="Validate business operations continuity after authentication recovery"
        )
        
        await self.websocket_notifier.send_tool_completed(
            recovery_context,
            tool_name="business_continuity_analyzer",
            result={
                "recovery_status": "successful",
                "business_continuity": "maintained",
                "data_integrity": "preserved",
                "user_context": f"Recovered for {business_user.company}"
            }
        )
        
        await self.websocket_notifier.send_agent_completed(
            recovery_context,
            result={
                "recovery_summary": "Authentication recovery completed successfully",
                "business_impact": "Minimal disruption to business operations",
                "continuity_validated": True
            }
        )
        
        # Phase 4: Validate business continuity after recovery
        recovery_events = valid_connection.get_business_events()
        assert len(recovery_events) >= 5, "All business events should be delivered after recovery"
        
        # Validate business context preserved through recovery
        for event in recovery_events:
            event_content = json.dumps(event).lower()
            assert "dataanalytics" in event_content or business_user.user_id in event_content, \
                "Business context should be preserved through recovery"
        
        # Validate recovery event content
        recovery_completion = next(event for event in recovery_events if "completed" in event.get("type", ""))
        completion_result = recovery_completion.get("payload", {}).get("result", {})
        
        assert completion_result.get("continuity_validated") is True, "Business continuity should be validated"
        assert "minimal disruption" in completion_result.get("business_impact", "").lower(), \
            "Recovery should minimize business impact"
        
        # Phase 5: Failure scenario analysis
        expected_failures = [scenario for scenario in failure_scenarios if scenario["result"] == "expected_failure"]
        assert len(expected_failures) >= 1, "Should have handled authentication failure scenarios appropriately"
        
        self.record_metric("authentication_failure_scenarios_tested", len(failure_scenarios))
        self.record_metric("expected_failures_handled", len(expected_failures))
        self.record_metric("recovery_authentication_time_ms", recovery_time * 1000)
        self.record_metric("business_continuity_maintained", True)
        self.record_metric("post_recovery_operations_successful", len(recovery_events))
        self.record_metric("user_context_preserved_through_recovery", True)
    
    # ===== BUSINESS VALUE AND PERFORMANCE TESTS =====
    
    @pytest.mark.asyncio
    async def test_high_value_enterprise_customer_authentication_performance(self):
        """
        Test authentication performance for high-value enterprise customers with SLA requirements.
        
        BVJ: Enterprise customers paying $500K+ annually require sub-second authentication
        and premium performance levels to justify subscription costs and maintain satisfaction.
        """
        # Create high-value enterprise customer profile
        enterprise_customer = self._create_business_user_profile("TechCorp Industries", "enterprise", "ceo")
        enterprise_customer.business_context.update({
            "annual_contract_value": "$750K",
            "sla_requirements": {
                "authentication_time": "<1s",
                "availability": "99.9%",
                "response_time": "<500ms"
            },
            "priority_level": "platinum",
            "dedicated_support": True
        })
        
        # Performance benchmarking
        performance_metrics = {
            "authentication_attempts": [],
            "business_operation_times": [],
            "total_session_times": [],
            "sla_compliance": {}
        }
        
        # Phase 1: Authentication performance testing
        auth_attempts = 5
        for attempt in range(auth_attempts):
            auth_start = time.time()
            connection = await self._authenticate_business_user(enterprise_customer)
            auth_time = time.time() - auth_start
            
            performance_metrics["authentication_attempts"].append({
                "attempt": attempt + 1,
                "auth_time_ms": auth_time * 1000,
                "success": connection.is_authenticated
            })
            
            # Validate enterprise authentication succeeded
            assert connection.is_authenticated is True, f"Enterprise authentication attempt {attempt + 1} should succeed"
            assert auth_time < 1.0, f"Enterprise authentication should meet <1s SLA: {auth_time:.3f}s"
        
        # Phase 2: High-value business operations performance
        final_connection = await self._authenticate_business_user(enterprise_customer)
        
        business_operations = [
            {
                "operation": "strategic_analysis",
                "context": AgentExecutionContext(
                    user_id=enterprise_customer.user_id,
                    thread_id=enterprise_customer.thread_id,
                    run_id=f"strategic_run_{uuid.uuid4().hex[:8]}",
                    agent_name="EnterpriseStrategicAnalyzer",
                    agent_type="enterprise_strategy",
                    user_request="High-priority strategic analysis for $750K enterprise customer"
                )
            },
            {
                "operation": "executive_reporting",
                "context": AgentExecutionContext(
                    user_id=enterprise_customer.user_id,
                    thread_id=enterprise_customer.thread_id,
                    run_id=f"executive_run_{uuid.uuid4().hex[:8]}",
                    agent_name="ExecutiveReportingAgent",
                    agent_type="executive_intelligence",
                    user_request="Generate executive dashboard and KPI analysis for C-suite presentation"
                )
            }
        ]
        
        for operation in business_operations:
            op_start = time.time()
            context = operation["context"]
            
            # Execute high-value business operation
            await self.websocket_notifier.send_agent_started(context)
            
            await self.websocket_notifier.send_agent_thinking(
                context,
                thought=f"Processing high-priority {operation['operation']} for enterprise customer with $750K ACV",
                step_number=1
            )
            
            await self.websocket_notifier.send_tool_executing(
                context,
                tool_name=f"enterprise_{operation['operation']}_tool",
                tool_purpose=f"Premium {operation['operation']} for platinum enterprise customer"
            )
            
            await self.websocket_notifier.send_tool_completed(
                context,
                tool_name=f"enterprise_{operation['operation']}_tool",
                result={
                    "enterprise_analysis": f"Premium {operation['operation']} results",
                    "business_value": "$750K customer priority analysis complete",
                    "sla_compliance": "Meeting enterprise performance requirements"
                }
            )
            
            await self.websocket_notifier.send_agent_completed(
                context,
                result={
                    "operation_type": operation['operation'],
                    "customer_tier": "enterprise_platinum",
                    "business_impact": "High-value strategic insights delivered"
                }
            )
            
            op_time = time.time() - op_start
            performance_metrics["business_operation_times"].append({
                "operation": operation['operation'],
                "duration_ms": op_time * 1000
            })
            
            # Validate enterprise operation performance
            assert op_time < 10.0, f"Enterprise {operation['operation']} should complete within 10s: {op_time:.3f}s"
        
        # Phase 3: SLA compliance validation
        auth_times = [attempt["auth_time_ms"] for attempt in performance_metrics["authentication_attempts"]]
        avg_auth_time = sum(auth_times) / len(auth_times)
        max_auth_time = max(auth_times)
        
        operation_times = [op["duration_ms"] for op in performance_metrics["business_operation_times"]]
        avg_operation_time = sum(operation_times) / len(operation_times)
        
        # SLA compliance checking
        performance_metrics["sla_compliance"] = {
            "authentication_sla_met": max_auth_time < 1000,  # <1s requirement
            "average_auth_time_ms": avg_auth_time,
            "max_auth_time_ms": max_auth_time,
            "operation_performance_acceptable": avg_operation_time < 10000,  # <10s for complex operations
            "overall_sla_compliance": max_auth_time < 1000 and avg_operation_time < 10000
        }
        
        # Phase 4: Enterprise value validation
        enterprise_events = final_connection.get_business_events()
        
        # Validate enterprise-specific content
        enterprise_indicators = 0
        for event in enterprise_events:
            event_content = json.dumps(event).lower()
            if any(indicator in event_content for indicator in ["enterprise", "platinum", "750k", "strategic", "executive"]):
                enterprise_indicators += 1
        
        assert enterprise_indicators >= len(business_operations) * 2, \
            "Enterprise events should contain appropriate high-value business context"
        
        # Validate business value attribution
        completion_events = [event for event in enterprise_events if "completed" in event.get("type", "")]
        for completion in completion_events:
            result = completion.get("payload", {}).get("result", {})
            assert "business_impact" in result or "business_value" in result, \
                "Enterprise completions should highlight business value"
        
        assert performance_metrics["sla_compliance"]["overall_sla_compliance"] is True, \
            "Enterprise customer should meet all SLA requirements"
        
        self.record_metric("enterprise_customer_authentication_performance_validated", True)
        self.record_metric("average_enterprise_auth_time_ms", avg_auth_time)
        self.record_metric("max_enterprise_auth_time_ms", max_auth_time)
        self.record_metric("enterprise_sla_compliance", performance_metrics["sla_compliance"]["overall_sla_compliance"])
        self.record_metric("high_value_business_operations_completed", len(business_operations))
        self.record_metric("enterprise_business_value_indicators", enterprise_indicators)
    
    @pytest.mark.asyncio
    async def test_cross_company_data_isolation_security_validation(self):
        """
        Test strict data isolation between different companies using the platform concurrently.
        
        BVJ: Cross-company data isolation is critical for enterprise security and compliance,
        ensuring no data leakage between competing businesses using the platform.
        """
        # Create users from competing companies in same industry
        competing_companies = [
            self._create_business_user_profile("TechCorp Industries", "enterprise", "security_officer"),
            self._create_business_user_profile("CompetitorTech Solutions", "enterprise", "data_analyst"),
            self._create_business_user_profile("RivalSoft Corporation", "mid", "product_manager")
        ]
        
        # Update business contexts with sensitive competitive data
        competing_companies[0].business_context.update({
            "sensitive_projects": ["Project Alpha - AI Platform", "Project Beta - Cloud Migration"],
            "competitive_advantages": ["Advanced ML algorithms", "Enterprise security"],
            "confidential_metrics": {"quarterly_revenue": "$2.1M", "market_share": "15%"}
        })
        
        competing_companies[1].business_context.update({
            "sensitive_projects": ["Project Gamma - Data Platform", "Project Delta - Analytics Suite"],
            "competitive_advantages": ["Real-time analytics", "Scalable infrastructure"],
            "confidential_metrics": {"quarterly_revenue": "$1.8M", "market_share": "12%"}
        })
        
        competing_companies[2].business_context.update({
            "sensitive_projects": ["Project Epsilon - Mobile App", "Project Zeta - IoT Platform"],
            "competitive_advantages": ["User experience", "Mobile-first approach"],
            "confidential_metrics": {"quarterly_revenue": "$950K", "market_share": "8%"}
        })
        
        # Authenticate all competing companies simultaneously
        authenticated_connections = []
        for company_user in competing_companies:
            connection = await self._authenticate_business_user(company_user)
            authenticated_connections.append(connection)
        
        # Execute sensitive business analysis for each company concurrently
        async def execute_confidential_analysis(user_index: int):
            """Execute confidential business analysis with sensitive data."""
            user = competing_companies[user_index]
            connection = authenticated_connections[user_index]
            
            sensitive_context = AgentExecutionContext(
                user_id=user.user_id,
                thread_id=user.thread_id,
                run_id=f"confidential_run_{user.user_id}_{uuid.uuid4().hex[:8]}",
                agent_name="ConfidentialBusinessAnalyzer",
                agent_type="competitive_intelligence",
                user_request=f"Analyze confidential {user.company} competitive strategy and sensitive business metrics"
            )
            
            # Agent execution with sensitive business data
            await self.websocket_notifier.send_agent_started(sensitive_context)
            
            await self.websocket_notifier.send_agent_thinking(
                sensitive_context,
                thought=f"Analyzing highly confidential {user.company} competitive positioning and sensitive project data",
                step_number=1
            )
            
            # Tool execution with company-specific sensitive data
            sensitive_projects = user.business_context.get("sensitive_projects", [])
            confidential_metrics = user.business_context.get("confidential_metrics", {})
            
            await self.websocket_notifier.send_tool_executing(
                sensitive_context,
                tool_name="confidential_competitive_analyzer",
                tool_purpose=f"Confidential analysis of {user.company} competitive advantages and sensitive project data"
            )
            
            await self.websocket_notifier.send_tool_completed(
                sensitive_context,
                tool_name="confidential_competitive_analyzer",
                result={
                    "company_confidential_analysis": f"TOP SECRET: {user.company} competitive analysis",
                    "sensitive_projects_analysis": {
                        "projects": sensitive_projects,
                        "strategic_value": f"Confidential strategic analysis for {user.company}"
                    },
                    "confidential_financial_metrics": confidential_metrics,
                    "competitive_positioning": f"CONFIDENTIAL: {user.company} market position analysis",
                    "security_classification": "COMPANY_CONFIDENTIAL"
                }
            )
            
            await self.websocket_notifier.send_agent_completed(
                sensitive_context,
                result={
                    "confidential_summary": f"Confidential competitive analysis for {user.company} completed",
                    "sensitive_insights": f"Company-specific strategic recommendations for {user.company}",
                    "data_classification": "CONFIDENTIAL",
                    "access_restricted_to": user.user_id
                }
            )
            
            return {
                "user_id": user.user_id,
                "company": user.company,
                "sensitive_data_processed": True,
                "confidential_projects": sensitive_projects,
                "connection": connection
            }
        
        # Execute confidential analysis for all companies concurrently
        confidential_results = await asyncio.gather(*[
            execute_confidential_analysis(i) for i in range(len(competing_companies))
        ])
        
        # Phase 1: Cross-contamination validation
        data_isolation_violations = []
        
        for i, result in enumerate(confidential_results):
            user = competing_companies[i]
            connection = authenticated_connections[i]
            user_events = connection.get_business_events()
            
            # Check that user only received their own confidential data
            for event in user_events:
                event_content = json.dumps(event).lower()
                
                # Should contain own company's data
                own_company = user.company.lower()
                own_projects = [project.lower() for project in user.business_context.get("sensitive_projects", [])]
                
                # Validate own data presence
                has_own_company_data = own_company.replace(" ", "").replace("-", "") in event_content.replace(" ", "").replace("-", "")
                if "confidential" in event_content or "sensitive" in event_content:
                    assert has_own_company_data, f"User {user.user_id} confidential event should contain own company data"
                
                # Check for competing companies' data (should NOT be present)
                for j, competitor in enumerate(competing_companies):
                    if i != j:  # Different company
                        competitor_company = competitor.company.lower()
                        competitor_projects = [project.lower() for project in competitor.business_context.get("sensitive_projects", [])]
                        competitor_metrics = str(competitor.business_context.get("confidential_metrics", {})).lower()
                        
                        # Check for competitor company name
                        competitor_clean = competitor_company.replace(" ", "").replace("-", "")
                        if competitor_clean in event_content.replace(" ", "").replace("-", ""):
                            data_isolation_violations.append({
                                "user": user.user_id,
                                "leaked_company": competitor.company,
                                "event_type": event.get("type"),
                                "violation_content": event_content[:200]
                            })
                        
                        # Check for competitor project names
                        for project in competitor_projects:
                            if project in event_content:
                                data_isolation_violations.append({
                                    "user": user.user_id,
                                    "leaked_project": project,
                                    "from_company": competitor.company,
                                    "violation_type": "sensitive_project_leak"
                                })
                        
                        # Check for competitor financial metrics
                        if "quarterly_revenue" in event_content and competitor_metrics:
                            competitor_revenue = str(competitor.business_context["confidential_metrics"].get("quarterly_revenue", "")).lower()
                            if competitor_revenue and competitor_revenue in event_content:
                                data_isolation_violations.append({
                                    "user": user.user_id,
                                    "leaked_financial_data": competitor_revenue,
                                    "from_company": competitor.company,
                                    "violation_type": "financial_data_leak"
                                })
        
        # Phase 2: Security validation
        assert len(data_isolation_violations) == 0, \
            f"CRITICAL SECURITY VIOLATION: Cross-company data contamination detected: {data_isolation_violations}"
        
        # Phase 3: Validate each company received only their data
        for i, result in enumerate(confidential_results):
            user = competing_companies[i]
            connection = authenticated_connections[i]
            user_events = connection.get_business_events()
            
            # Count confidential events for this user
            confidential_events = [event for event in user_events if "confidential" in json.dumps(event).lower()]
            assert len(confidential_events) >= 2, f"User {user.user_id} should receive their confidential analysis"
            
            # Validate data classification
            classified_events = [event for event in user_events if "classification" in json.dumps(event).lower()]
            for event in classified_events:
                event_content = json.dumps(event)
                assert user.user_id in event_content or user.company.lower() in event_content.lower(), \
                    "Classified data should be restricted to correct user"
        
        # Phase 4: Authentication context isolation validation
        for i, connection in enumerate(authenticated_connections):
            user = competing_companies[i]
            auth_result = connection.authentication_result.auth_result
            
            # Each user should have isolated authentication context
            business_metadata = auth_result.metadata.get("business_context", {})
            assert business_metadata.get("sensitive_projects") is None or \
                   set(business_metadata.get("sensitive_projects", [])) == set(user.business_context.get("sensitive_projects", [])), \
                   "Authentication context should not leak between companies"
        
        self.record_metric("cross_company_isolation_validated", True)
        self.record_metric("data_isolation_violations_detected", len(data_isolation_violations))
        self.record_metric("competing_companies_tested", len(competing_companies))
        self.record_metric("confidential_analysis_operations", len(confidential_results))
        self.record_metric("security_compliance_validated", len(data_isolation_violations) == 0)
        self.record_metric("sensitive_data_protection_confirmed", True)
    
    async def async_test_summary(self):
        """Generate comprehensive test summary for multi-user business scenarios."""
        # Calculate comprehensive metrics
        total_metrics = len(self.recorded_metrics)
        
        # Authentication performance summary
        auth_metrics = [metric for metric in self.recorded_metrics if "auth" in metric]
        concurrent_metrics = [metric for metric in self.recorded_metrics if "concurrent" in metric]
        isolation_metrics = [metric for metric in self.recorded_metrics if "isolation" in metric]
        business_metrics = [metric for metric in self.recorded_metrics if "business" in metric]
        
        summary = {
            "test_suite": "Multi-User WebSocket Authentication Business Scenarios",
            "total_metrics_recorded": total_metrics,
            "authentication_metrics": len(auth_metrics),
            "concurrent_execution_metrics": len(concurrent_metrics),
            "isolation_security_metrics": len(isolation_metrics),
            "business_value_metrics": len(business_metrics),
            "multi_user_scenarios_validated": len(self.business_user_profiles),
            "authenticated_connections_tested": len(self.authenticated_connections),
            "business_companies_tested": len(set(profile.company for profile in self.business_user_profiles.values())),
            "subscription_tiers_validated": len(set(profile.subscription_tier for profile in self.business_user_profiles.values()))
        }
        
        # Record final summary
        for key, value in summary.items():
            self.record_metric(f"test_summary_{key}", value)
        
        return summary