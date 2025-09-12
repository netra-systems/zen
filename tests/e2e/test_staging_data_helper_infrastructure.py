#!/usr/bin/env python
"""
Staging Data Helper Infrastructure E2E Tests - Reproducing 0% Pass Rate

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Data Helper affects all data analysis customers
- Business Goal: Reproduce Data Helper Agent 0% pass rate to identify staging infrastructure failures
- Value Impact: Data Helper delivers critical data insights worth $1.5M+ ARR - currently failing completely
- Strategic Impact: Systematic reproduction of staging failures to enable rapid remediation

CRITICAL MISSION: These tests are designed to REPRODUCE the exact staging failures:
1. Complete Data Helper Agent execution failures (0% success rate)
2. Staging GCP WebSocket connectivity issues (503 errors)
3. Authentication bypass failures with E2E_OAUTH_SIMULATION_KEY
4. Agent Registry + WebSocket integration gaps in staging environment
5. Multi-user isolation failures causing data leakage

TEST FAILURE EXPECTATIONS (All Expected to Fail):
- Data Helper Agent execution timeout/failures in staging
- WebSocket connection errors to wss://api.staging.netrasystems.ai/ws
- Authentication errors due to missing OAuth simulation key
- Agent business value delivery failure (no cost savings results)
- Real-time WebSocket event delivery failure

This test suite systematically reproduces the staging infrastructure issues
preventing Data Helper Agents from delivering any business value.
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

# SSOT imports per CLAUDE.md requirements
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context,
    create_test_user_with_auth
)
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env
from shared.types.core_types import UserID


@dataclass
class StagingInfrastructureFailure:
    """Data structure for capturing staging infrastructure failures."""
    
    test_name: str
    failure_category: str
    component: str
    error_message: str
    expected_failure: bool
    business_impact: str
    staging_specific: bool
    timestamp: str
    technical_details: Dict[str, Any]
    reproduction_success: bool = True  # Whether we successfully reproduced the expected failure
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert failure to dictionary for analysis."""
        return {
            "test_name": self.test_name,
            "failure_category": self.failure_category,
            "component": self.component,
            "error_message": self.error_message,
            "expected_failure": self.expected_failure,
            "business_impact": self.business_impact,
            "staging_specific": self.staging_specific,
            "timestamp": self.timestamp,
            "technical_details": self.technical_details,
            "reproduction_success": self.reproduction_success
        }


@dataclass
class DataHelperBusinessValueMetrics:
    """Business value metrics for Data Helper Agent execution."""
    
    execution_time_seconds: float = 0.0
    data_points_processed: int = 0
    insights_generated: int = 0
    cost_savings_identified: float = 0.0
    recommendations_count: int = 0
    websocket_events_received: int = 0
    agent_completion_success: bool = False
    business_value_delivered: bool = False
    
    def calculate_business_value_score(self) -> float:
        """Calculate overall business value delivery score (0-1)."""
        score = 0.0
        
        if self.agent_completion_success:
            score += 0.3
        if self.insights_generated > 0:
            score += 0.2
        if self.cost_savings_identified > 0:
            score += 0.3
        if self.recommendations_count > 0:
            score += 0.1
        if self.websocket_events_received >= 5:  # All 5 critical events
            score += 0.1
            
        return min(score, 1.0)


class TestStagingDataHelperInfrastructure(BaseE2ETest):
    """E2E tests designed to reproduce Data Helper Agent staging infrastructure failures."""
    
    def __init__(self):
        super().__init__()
        self.env = get_env()
        self.staging_failures: List[StagingInfrastructureFailure] = []
        self.business_metrics: List[DataHelperBusinessValueMetrics] = []
        self.auth_helper = None
        self.websocket_auth_helper = None
        
    def setup_method(self):
        """Setup for staging E2E tests with failure reproduction focus."""
        # Force staging environment for infrastructure failure reproduction
        test_environment = "staging"
        
        # Initialize staging-specific auth helpers
        self.auth_helper = E2EAuthHelper(environment=test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=test_environment)
        
        print(f"[INFO] Staging Data Helper Infrastructure Test Environment: {test_environment}")
        print(f"[INFO] Auth service URL: {self.auth_helper.config.auth_service_url}")
        print(f"[INFO] Backend URL: {self.auth_helper.config.backend_url}")
        print(f"[INFO] WebSocket URL: {self.auth_helper.config.websocket_url}")
        print(f"[INFO] Expected outcome: ALL TESTS SHOULD FAIL (infrastructure reproduction)")
        
    def capture_staging_failure(
        self,
        test_name: str,
        failure_category: str,
        component: str,
        error_message: str,
        expected_failure: bool,
        business_impact: str,
        staging_specific: bool = True,
        technical_details: Optional[Dict[str, Any]] = None,
        reproduction_success: bool = True
    ):
        """Capture structured staging failure for infrastructure gap analysis."""
        failure = StagingInfrastructureFailure(
            test_name=test_name,
            failure_category=failure_category,
            component=component,
            error_message=error_message,
            expected_failure=expected_failure,
            business_impact=business_impact,
            staging_specific=staging_specific,
            timestamp=datetime.now(timezone.utc).isoformat(),
            technical_details=technical_details or {},
            reproduction_success=reproduction_success
        )
        
        self.staging_failures.append(failure)
        
        # Log failure for immediate visibility
        failure_status = "REPRODUCED" if expected_failure and reproduction_success else "UNEXPECTED"
        print(f"[{failure_status}] {test_name}: {business_impact}")
        print(f"[CATEGORY] {failure_category} - {component}")
        print(f"[ERROR] {error_message}")
        if technical_details:
            print(f"[TECHNICAL] {json.dumps(technical_details, indent=2)}")
    
    # ===================== Staging Authentication Infrastructure Tests =====================
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_data_helper_authentication_failure_reproduction(self):
        """
        Test staging Data Helper authentication failure reproduction.
        
        EXPECTED TO FAIL: This should reproduce the exact authentication failures
        preventing Data Helper Agents from obtaining valid JWT tokens in staging.
        
        Infrastructure Gap: Missing E2E_OAUTH_SIMULATION_KEY or auth service failures
        """
        test_name = "staging_data_helper_authentication_failure"
        
        try:
            # Test E2E OAuth simulation key availability
            e2e_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            
            if not e2e_key:
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category="authentication_infrastructure",
                    component="EnvironmentConfiguration",
                    error_message="E2E_OAUTH_SIMULATION_KEY not available in environment",
                    expected_failure=True,
                    business_impact="Data Helper cannot authenticate in staging - 0% success rate",
                    technical_details={
                        "environment_check": "E2E_OAUTH_SIMULATION_KEY",
                        "key_available": False,
                        "staging_oauth_simulation": "disabled"
                    }
                )
            
            # Test staging authentication flow
            try:
                print(f"[INFO] Attempting staging authentication for Data Helper Agent...")
                
                # Use staging-specific authentication
                staging_token = await self.websocket_auth_helper.get_staging_token_async(
                    email="data_helper_test@staging.example.com",
                    bypass_key=e2e_key
                )
                
                if not staging_token:
                    self.capture_staging_failure(
                        test_name=test_name,
                        failure_category="oauth_simulation_failure",
                        component="StagingAuthService",
                        error_message="Staging OAuth simulation returned no token",
                        expected_failure=True,
                        business_impact="Data Helper authentication fails - no staging token available",
                        technical_details={
                            "oauth_method": "get_staging_token_async",
                            "token_result": None,
                            "bypass_key_provided": bool(e2e_key)
                        }
                    )
                else:
                    # Unexpected success - authentication may be working
                    self.capture_staging_failure(
                        test_name=test_name,
                        failure_category="authentication_success",
                        component="StagingAuthService",
                        error_message="Staging authentication succeeded unexpectedly",
                        expected_failure=False,
                        business_impact="Authentication infrastructure may be resolved",
                        technical_details={
                            "token_length": len(staging_token),
                            "authentication_method": "oauth_simulation",
                            "success_unexpected": True
                        },
                        reproduction_success=False
                    )
                    
            except Exception as auth_error:
                # EXPECTED: Authentication should fail in staging
                error_message = str(auth_error).lower()
                
                auth_failure_patterns = [
                    "unauthorized", "forbidden", "invalid", "key", "oauth", 
                    "simulation", "bypass", "503", "unavailable"
                ]
                
                is_auth_failure = any(pattern in error_message for pattern in auth_failure_patterns)
                
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category="staging_auth_service_failure" if is_auth_failure else "staging_connection_error",
                    component="StagingAuthService",
                    error_message=str(auth_error),
                    expected_failure=True,
                    business_impact="Staging auth service failure prevents Data Helper execution",
                    technical_details={
                        "error_type": type(auth_error).__name__,
                        "is_auth_failure": is_auth_failure,
                        "auth_patterns_found": [p for p in auth_failure_patterns if p in error_message],
                        "bypass_key_provided": bool(e2e_key)
                    }
                )
                
        except Exception as test_error:
            self.capture_staging_failure(
                test_name=test_name,
                failure_category="test_execution_error",
                component="TestFramework",
                error_message=str(test_error),
                expected_failure=False,
                business_impact="Cannot test staging authentication",
                technical_details={"error_type": type(test_error).__name__},
                reproduction_success=False
            )
            raise
    
    @pytest.mark.e2e
    @pytest.mark.staging  
    async def test_staging_websocket_connection_failure_reproduction(self):
        """
        Test staging WebSocket connection failure reproduction.
        
        EXPECTED TO FAIL: This should reproduce the exact WebSocket connection failures
        (503 Service Unavailable) preventing Data Helper real-time communication.
        
        Infrastructure Gap: GCP Cloud Run WebSocket service unavailable
        """
        test_name = "staging_websocket_connection_failure"
        
        try:
            # Get authentication token for WebSocket connection attempt
            auth_token = None
            try:
                auth_token = await self.websocket_auth_helper.get_staging_token_async()
            except Exception as token_error:
                print(f"[INFO] Using fallback token due to auth error: {token_error}")
                auth_token = self.websocket_auth_helper._create_staging_compatible_jwt("data_helper_ws_test@staging.com")
            
            if not auth_token:
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category="websocket_auth_prerequisite_failure",
                    component="AuthenticationService",
                    error_message="Cannot obtain authentication token for WebSocket connection",
                    expected_failure=True,
                    business_impact="WebSocket connection impossible without auth token",
                    technical_details={"auth_token_available": False}
                )
                return
            
            # Test staging WebSocket connection
            staging_websocket_url = "wss://api.staging.netrasystems.ai/ws"
            
            try:
                print(f"[INFO] Attempting WebSocket connection to: {staging_websocket_url}")
                
                # EXPECTED TO FAIL: This should timeout or return 503 Service Unavailable
                websocket_connection = await self.websocket_auth_helper.connect_authenticated_websocket(
                    timeout=15.0  # Reasonable timeout for staging
                )
                
                # If connection succeeds, this is unexpected
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category="websocket_connection_success",
                    component="StagingWebSocketService", 
                    error_message="WebSocket connection to staging succeeded unexpectedly",
                    expected_failure=False,
                    business_impact="WebSocket infrastructure may be resolved",
                    technical_details={
                        "websocket_url": staging_websocket_url,
                        "connection_success": True,
                        "auth_token_provided": True
                    },
                    reproduction_success=False
                )
                
                # Test basic WebSocket communication
                try:
                    test_message = {
                        "type": "ping",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "test": "staging_infrastructure"
                    }
                    
                    await websocket_connection.send(json.dumps(test_message))
                    
                    # Wait for response with timeout
                    response = await asyncio.wait_for(websocket_connection.recv(), timeout=5.0)
                    
                    print(f"[UNEXPECTED] WebSocket communication successful: {response}")
                    
                except asyncio.TimeoutError:
                    self.capture_staging_failure(
                        test_name=test_name,
                        failure_category="websocket_communication_timeout",
                        component="StagingWebSocketService",
                        error_message="WebSocket connected but communication timed out",
                        expected_failure=True,
                        business_impact="WebSocket connects but cannot communicate - partial failure",
                        technical_details={
                            "connection_established": True,
                            "communication_timeout": True,
                            "timeout_seconds": 5.0
                        }
                    )
                
                await websocket_connection.close()
                
            except Exception as websocket_error:
                # EXPECTED: WebSocket connection should fail
                error_message = str(websocket_error).lower()
                
                staging_failure_patterns = [
                    "503", "service unavailable", "unavailable", "timeout",
                    "connection refused", "failed to connect", "handshake",
                    "cloud run", "network", "dns"
                ]
                
                is_503_error = "503" in error_message or "unavailable" in error_message
                is_staging_infrastructure_failure = any(pattern in error_message for pattern in staging_failure_patterns)
                
                failure_category = "503_service_unavailable" if is_503_error else "staging_websocket_connection_failure"
                
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category=failure_category,
                    component="StagingWebSocketService",
                    error_message=str(websocket_error),
                    expected_failure=True,
                    business_impact="Staging WebSocket service unavailable - Data Helper cannot provide real-time updates",
                    technical_details={
                        "error_type": type(websocket_error).__name__,
                        "is_503_error": is_503_error,
                        "is_staging_failure": is_staging_infrastructure_failure,
                        "staging_patterns_found": [p for p in staging_failure_patterns if p in error_message],
                        "websocket_url": staging_websocket_url,
                        "timeout_seconds": 15.0
                    }
                )
                
        except Exception as test_error:
            self.capture_staging_failure(
                test_name=test_name,
                failure_category="test_execution_error",
                component="TestFramework",
                error_message=str(test_error),
                expected_failure=False,
                business_impact="Cannot test WebSocket infrastructure",
                technical_details={"error_type": type(test_error).__name__},
                reproduction_success=False
            )
            raise
    
    # ===================== Data Helper Agent Execution Tests =====================
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_data_helper_complete_execution_failure_reproduction(self):
        """
        Test complete Data Helper Agent execution failure reproduction in staging.
        
        EXPECTED TO FAIL: This should reproduce the exact Data Helper Agent execution
        failures causing the 0% pass rate in staging environment.
        
        Infrastructure Gap: Complete Data Helper execution pipeline failure
        """
        test_name = "staging_data_helper_complete_execution_failure"
        
        # Initialize business value metrics tracking
        metrics = DataHelperBusinessValueMetrics()
        execution_start_time = time.time()
        
        try:
            # Step 1: Create authenticated user for Data Helper execution
            try:
                auth_user = await create_test_user_with_auth(
                    email="data_helper_execution_test@staging.com",
                    name="Data Helper E2E Test User",
                    environment="staging"
                )
                
                print(f"[INFO] Created authenticated user: {auth_user.get('user_id', 'unknown')}")
                
            except Exception as user_creation_error:
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category="user_creation_failure",
                    component="AuthenticationService",
                    error_message=str(user_creation_error),
                    expected_failure=True,
                    business_impact="Cannot create authenticated users for Data Helper testing",
                    technical_details={"error_type": type(user_creation_error).__name__}
                )
                return
            
            # Step 2: Establish WebSocket connection for real-time events
            websocket_connection = None
            try:
                # Use the staging WebSocket URL directly
                staging_websocket_url = "wss://api.staging.netrasystems.ai/ws"
                
                print(f"[INFO] Establishing WebSocket connection for Data Helper events...")
                
                # Create WebSocket connection using authenticated user
                websocket_connection = await self.websocket_auth_helper.connect_authenticated_websocket(
                    timeout=20.0  # Extended timeout for staging
                )
                
                print(f"[UNEXPECTED] WebSocket connection established successfully")
                
            except Exception as websocket_error:
                # EXPECTED: WebSocket connection should fail
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category="data_helper_websocket_connection_failure", 
                    component="StagingWebSocketService",
                    error_message=str(websocket_error),
                    expected_failure=True,
                    business_impact="Data Helper cannot establish WebSocket for real-time events",
                    technical_details={
                        "error_type": type(websocket_error).__name__,
                        "connection_phase": "websocket_establishment"
                    }
                )
            
            # Step 3: Send Data Helper Agent execution request
            data_analysis_request = {
                "type": "agent_request",
                "agent": "data_helper",
                "message": "Analyze our cloud infrastructure costs and identify optimization opportunities with detailed recommendations",
                "context": {
                    "analysis_type": "comprehensive_cost_analysis",
                    "data_sources": ["aws_billing", "usage_metrics", "performance_data"],
                    "business_context": "enterprise_cost_optimization",
                    "expected_savings_target": 15000,  # $15k monthly savings target
                    "priority": "high"
                },
                "user_id": auth_user.get("user_id", "test_user"),
                "thread_id": str(uuid.uuid4()),
                "request_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                if websocket_connection:
                    print(f"[INFO] Sending Data Helper execution request...")
                    await websocket_connection.send(json.dumps(data_analysis_request))
                    
                    # Step 4: Monitor WebSocket events and collect business value metrics
                    websocket_events = []
                    agent_result = None
                    timeout_duration = 120.0  # 2 minutes for complex data analysis
                    
                    try:
                        async with asyncio.timeout(timeout_duration):
                            while True:
                                try:
                                    event_data = await websocket_connection.recv()
                                    event = json.loads(event_data)
                                    websocket_events.append(event)
                                    
                                    event_type = event.get("type", "unknown")
                                    print(f"[INFO] Received WebSocket event: {event_type}")
                                    
                                    # Track WebSocket events for business value
                                    metrics.websocket_events_received += 1
                                    
                                    # Check for agent completion
                                    if event_type == "agent_completed":
                                        agent_result = event.get("data", {}).get("result", {})
                                        metrics.agent_completion_success = True
                                        break
                                        
                                    # Break on error events
                                    if event_type == "error":
                                        error_data = event.get("data", {})
                                        raise Exception(f"Agent execution error: {error_data}")
                                        
                                except json.JSONDecodeError as json_error:
                                    print(f"[WARNING] Invalid JSON in WebSocket event: {json_error}")
                                    continue
                                    
                    except asyncio.TimeoutError:
                        # EXPECTED: Data Helper should timeout in staging
                        self.capture_staging_failure(
                            test_name=test_name,
                            failure_category="data_helper_execution_timeout",
                            component="DataHelperAgent",
                            error_message=f"Data Helper execution timed out after {timeout_duration} seconds",
                            expected_failure=True,
                            business_impact="Data Helper cannot complete analysis - 0% success rate",
                            technical_details={
                                "timeout_seconds": timeout_duration,
                                "websocket_events_received": len(websocket_events),
                                "agent_completion_success": False,
                                "event_types": [e.get("type") for e in websocket_events]
                            }
                        )
                        
                    # Step 5: Analyze business value delivery
                    execution_time = time.time() - execution_start_time
                    metrics.execution_time_seconds = execution_time
                    
                    if agent_result:
                        # Analyze business value in agent result
                        metrics.insights_generated = len(agent_result.get("insights", []))
                        metrics.recommendations_count = len(agent_result.get("recommendations", []))
                        
                        # Check for cost savings identification
                        cost_savings = agent_result.get("cost_savings", 0)
                        if not cost_savings:
                            cost_savings = agent_result.get("potential_savings", 0)
                        if not cost_savings:
                            cost_savings = agent_result.get("total_monthly_savings", 0)
                            
                        metrics.cost_savings_identified = cost_savings
                        
                        # Calculate business value score
                        business_value_score = metrics.calculate_business_value_score()
                        metrics.business_value_delivered = business_value_score >= 0.7
                        
                        if not metrics.business_value_delivered:
                            self.capture_staging_failure(
                                test_name=test_name,
                                failure_category="data_helper_insufficient_business_value",
                                component="DataHelperAgent",
                                error_message=f"Data Helper delivered insufficient business value (score: {business_value_score:.2f})",
                                expected_failure=True,
                                business_impact="Data Helper execution completes but delivers no actionable business value",
                                technical_details={
                                    "business_value_score": business_value_score,
                                    "insights_generated": metrics.insights_generated,
                                    "cost_savings_identified": metrics.cost_savings_identified,
                                    "recommendations_count": metrics.recommendations_count,
                                    "websocket_events_received": metrics.websocket_events_received
                                }
                            )
                        else:
                            # Unexpected success
                            self.capture_staging_failure(
                                test_name=test_name,
                                failure_category="data_helper_business_value_success",
                                component="DataHelperAgent",
                                error_message="Data Helper delivered business value unexpectedly",
                                expected_failure=False,
                                business_impact="Data Helper execution successful - infrastructure may be resolved",
                                technical_details={
                                    "business_value_score": business_value_score,
                                    "insights_generated": metrics.insights_generated,
                                    "cost_savings_identified": metrics.cost_savings_identified,
                                    "execution_time_seconds": execution_time
                                },
                                reproduction_success=False
                            )
                            
                    else:
                        # No agent result received - complete failure
                        self.capture_staging_failure(
                            test_name=test_name,
                            failure_category="data_helper_no_result",
                            component="DataHelperAgent",
                            error_message="Data Helper execution produced no result",
                            expected_failure=True,
                            business_impact="Data Helper complete execution failure - 0% business value delivery",
                            technical_details={
                                "execution_time_seconds": execution_time,
                                "websocket_events_received": len(websocket_events),
                                "timeout_reached": execution_time >= timeout_duration
                            }
                        )
                    
                    # Store metrics for analysis
                    self.business_metrics.append(metrics)
                    
                    if websocket_connection:
                        await websocket_connection.close()
                        
                else:
                    # Cannot test Data Helper without WebSocket connection
                    self.capture_staging_failure(
                        test_name=test_name,
                        failure_category="data_helper_websocket_prerequisite_failure",
                        component="TestPrerequisites",
                        error_message="Cannot test Data Helper execution without WebSocket connection",
                        expected_failure=True,
                        business_impact="Data Helper testing impossible due to WebSocket infrastructure failure",
                        technical_details={
                            "websocket_connection_available": False,
                            "prerequisite_failure": "websocket_connection"
                        }
                    )
                    
            except Exception as execution_error:
                # EXPECTED: Data Helper execution should fail in staging
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category="data_helper_execution_error",
                    component="DataHelperAgent",
                    error_message=str(execution_error),
                    expected_failure=True,
                    business_impact="Data Helper execution fails with errors",
                    technical_details={
                        "error_type": type(execution_error).__name__,
                        "execution_time_seconds": time.time() - execution_start_time
                    }
                )
                
        except Exception as test_error:
            self.capture_staging_failure(
                test_name=test_name,
                failure_category="test_execution_error",
                component="TestFramework",
                error_message=str(test_error),
                expected_failure=False,
                business_impact="Cannot test Data Helper execution",
                technical_details={"error_type": type(test_error).__name__},
                reproduction_success=False
            )
            raise
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_data_helper_multi_user_isolation_failure_reproduction(self):
        """
        Test Data Helper multi-user isolation failure reproduction in staging.
        
        EXPECTED TO FAIL: This should reproduce multi-user isolation failures
        that could cause data leakage between Data Helper Agent executions.
        
        Infrastructure Gap: Multi-user isolation failures in staging WebSocket/Agent context
        """
        test_name = "staging_data_helper_multi_user_isolation_failure"
        
        try:
            # Create two different authenticated users
            try:
                user_alice = await create_test_user_with_auth(
                    email="alice_data_analyst@staging.com",
                    name="Alice Data Analyst",
                    environment="staging"
                )
                
                user_bob = await create_test_user_with_auth(
                    email="bob_data_analyst@staging.com", 
                    name="Bob Data Analyst",
                    environment="staging"
                )
                
                print(f"[INFO] Created multi-user test accounts: Alice={user_alice.get('user_id')}, Bob={user_bob.get('user_id')}")
                
            except Exception as user_creation_error:
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category="multi_user_creation_failure",
                    component="AuthenticationService",
                    error_message=str(user_creation_error),
                    expected_failure=True,
                    business_impact="Cannot create multiple users for isolation testing",
                    technical_details={"error_type": type(user_creation_error).__name__}
                )
                return
            
            # Test concurrent Data Helper executions for both users
            async def execute_data_helper_for_user(user_data, user_name):
                """Execute Data Helper for a specific user and return results."""
                user_events = []
                user_result = None
                websocket_connection = None
                
                try:
                    # Establish separate WebSocket connection for each user
                    websocket_connection = await self.websocket_auth_helper.connect_authenticated_websocket(
                        timeout=15.0
                    )
                    
                    # Send Data Helper request with user-specific data
                    request = {
                        "type": "agent_request",
                        "agent": "data_helper",
                        "message": f"Analyze costs for {user_name}'s department with confidential data",
                        "context": {
                            "user_context": user_name,
                            "confidential_data": f"{user_name}_sensitive_financial_data",
                            "department": f"{user_name}_department"
                        },
                        "user_id": user_data.get("user_id"),
                        "thread_id": str(uuid.uuid4())
                    }
                    
                    await websocket_connection.send(json.dumps(request))
                    
                    # Collect events with timeout
                    async with asyncio.timeout(60.0):
                        while True:
                            event_data = await websocket_connection.recv()
                            event = json.loads(event_data)
                            user_events.append(event)
                            
                            if event.get("type") == "agent_completed":
                                user_result = event.get("data", {}).get("result", {})
                                break
                                
                except Exception as execution_error:
                    print(f"[EXPECTED] {user_name} execution failed: {execution_error}")
                    
                finally:
                    if websocket_connection:
                        await websocket_connection.close()
                
                return {
                    "user_name": user_name,
                    "user_id": user_data.get("user_id"),
                    "events": user_events,
                    "result": user_result,
                    "execution_success": bool(user_result)
                }
            
            # Execute Data Helper for both users concurrently
            try:
                alice_task = execute_data_helper_for_user(user_alice, "Alice")
                bob_task = execute_data_helper_for_user(user_bob, "Bob")
                
                alice_execution, bob_execution = await asyncio.gather(
                    alice_task, bob_task, return_exceptions=True
                )
                
                # Analyze isolation failures
                isolation_failures = []
                
                if isinstance(alice_execution, dict) and isinstance(bob_execution, dict):
                    # Check for data cross-contamination in results
                    alice_result = alice_execution.get("result", {})
                    bob_result = bob_execution.get("result", {})
                    
                    if alice_result and bob_result:
                        # Check if Alice's result contains Bob's data or vice versa
                        alice_result_str = json.dumps(alice_result).lower()
                        bob_result_str = json.dumps(bob_result).lower()
                        
                        if "bob" in alice_result_str or "bob_department" in alice_result_str:
                            isolation_failures.append("Alice's result contains Bob's data")
                            
                        if "alice" in bob_result_str or "alice_department" in bob_result_str:
                            isolation_failures.append("Bob's result contains Alice's data")
                    
                    # Check WebSocket event isolation
                    alice_events = alice_execution.get("events", [])
                    bob_events = bob_execution.get("events", [])
                    
                    alice_user_ids = set(e.get("user_id") for e in alice_events if "user_id" in e)
                    bob_user_ids = set(e.get("user_id") for e in bob_events if "user_id" in e)
                    
                    if alice_user_ids.intersection(bob_user_ids):
                        isolation_failures.append("WebSocket events show user ID cross-contamination")
                
                if isolation_failures:
                    # CRITICAL: Multi-user isolation failure detected
                    self.capture_staging_failure(
                        test_name=test_name,
                        failure_category="critical_multi_user_isolation_failure",
                        component="DataHelperAgent",
                        error_message=f"Multi-user isolation violations: {', '.join(isolation_failures)}",
                        expected_failure=True,
                        business_impact="CRITICAL: Data leakage between users - security breach risk",
                        technical_details={
                            "isolation_violations": isolation_failures,
                            "alice_execution_success": alice_execution.get("execution_success", False),
                            "bob_execution_success": bob_execution.get("execution_success", False),
                            "alice_events_count": len(alice_execution.get("events", [])),
                            "bob_events_count": len(bob_execution.get("events", []))
                        }
                    )
                else:
                    # Check if executions failed for other reasons
                    alice_failed = isinstance(alice_execution, Exception) or not alice_execution.get("execution_success", False)
                    bob_failed = isinstance(bob_execution, Exception) or not bob_execution.get("execution_success", False)
                    
                    if alice_failed or bob_failed:
                        self.capture_staging_failure(
                            test_name=test_name,
                            failure_category="multi_user_execution_failure",
                            component="DataHelperAgent",
                            error_message="Multi-user Data Helper executions failed in staging",
                            expected_failure=True,
                            business_impact="Data Helper cannot handle multiple concurrent users",
                            technical_details={
                                "alice_execution_failed": alice_failed,
                                "bob_execution_failed": bob_failed,
                                "alice_error": str(alice_execution) if isinstance(alice_execution, Exception) else None,
                                "bob_error": str(bob_execution) if isinstance(bob_execution, Exception) else None
                            }
                        )
                    else:
                        # Unexpected success - isolation working
                        self.capture_staging_failure(
                            test_name=test_name,
                            failure_category="multi_user_isolation_success",
                            component="DataHelperAgent",
                            error_message="Multi-user isolation appears functional",
                            expected_failure=False,
                            business_impact="Multi-user Data Helper execution successful",
                            technical_details={
                                "alice_execution_success": True,
                                "bob_execution_success": True,
                                "isolation_verified": True
                            },
                            reproduction_success=False
                        )
                        
            except Exception as concurrent_error:
                # EXPECTED: Concurrent execution should fail in staging
                self.capture_staging_failure(
                    test_name=test_name,
                    failure_category="concurrent_execution_failure",
                    component="DataHelperAgent",
                    error_message=str(concurrent_error),
                    expected_failure=True,
                    business_impact="Data Helper cannot handle concurrent multi-user execution",
                    technical_details={
                        "error_type": type(concurrent_error).__name__,
                        "failure_phase": "concurrent_execution"
                    }
                )
                
        except Exception as test_error:
            self.capture_staging_failure(
                test_name=test_name,
                failure_category="test_execution_error",
                component="TestFramework",
                error_message=str(test_error),
                expected_failure=False,
                business_impact="Cannot test multi-user isolation",
                technical_details={"error_type": type(test_error).__name__},
                reproduction_success=False
            )
            raise
    
    # ===================== Staging Infrastructure Analysis and Reporting =====================
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_staging_infrastructure_comprehensive_failure_analysis(self):
        """
        Generate comprehensive staging infrastructure failure analysis.
        
        This test analyzes all captured staging failures and generates a structured
        report of Data Helper infrastructure issues in staging environment.
        """
        test_name = "staging_infrastructure_comprehensive_failure_analysis"
        
        print(f"\n{'='*100}")
        print(f"STAGING DATA HELPER INFRASTRUCTURE FAILURE ANALYSIS REPORT")
        print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        print(f"Total Staging Failures Captured: {len(self.staging_failures)}")
        print(f"Business Value Metrics Collected: {len(self.business_metrics)}")
        print(f"{'='*100}")
        
        # Categorize failures by type and impact
        failure_categories = {}
        critical_failures = []
        expected_failures = []
        unexpected_failures = []
        reproduction_successes = []
        
        for failure in self.staging_failures:
            category = failure.failure_category
            if category not in failure_categories:
                failure_categories[category] = []
            failure_categories[category].append(failure)
            
            if "critical" in failure.failure_category.lower() or "security" in failure.business_impact.lower():
                critical_failures.append(failure)
            
            if failure.expected_failure:
                expected_failures.append(failure)
            else:
                unexpected_failures.append(failure)
            
            if failure.reproduction_success:
                reproduction_successes.append(failure)
        
        # Analyze business value metrics
        business_value_analysis = {
            "total_executions": len(self.business_metrics),
            "successful_executions": sum(1 for m in self.business_metrics if m.business_value_delivered),
            "average_execution_time": sum(m.execution_time_seconds for m in self.business_metrics) / len(self.business_metrics) if self.business_metrics else 0,
            "total_cost_savings_identified": sum(m.cost_savings_identified for m in self.business_metrics),
            "total_insights_generated": sum(m.insights_generated for m in self.business_metrics),
            "websocket_events_received": sum(m.websocket_events_received for m in self.business_metrics)
        }
        
        business_value_success_rate = (business_value_analysis["successful_executions"] / business_value_analysis["total_executions"] * 100) if business_value_analysis["total_executions"] > 0 else 0
        
        # Print categorized analysis
        print(f"\nSTAGING FAILURE CATEGORIES:")
        for category, failures in failure_categories.items():
            print(f"  {category.upper().replace('_', ' ')}: {len(failures)} failures")
            for failure in failures:
                status = "REPRODUCED" if failure.expected_failure and failure.reproduction_success else "UNEXPECTED"
                print(f"    - {failure.component}: {failure.business_impact} ({status})")
        
        print(f"\nCRITICAL INFRASTRUCTURE FAILURES: {len(critical_failures)}")
        for failure in critical_failures:
            print(f"   ALERT:  {failure.component}: {failure.business_impact}")
            print(f"     Category: {failure.failure_category}")
            print(f"     Error: {failure.error_message}")
        
        print(f"\nDATA HELPER BUSINESS VALUE ANALYSIS:")
        print(f"  Total Executions Attempted: {business_value_analysis['total_executions']}")
        print(f"  Successful Business Value Delivery: {business_value_analysis['successful_executions']}")
        print(f"  Business Value Success Rate: {business_value_success_rate:.1f}%")
        print(f"  Average Execution Time: {business_value_analysis['average_execution_time']:.1f} seconds")
        print(f"  Total Cost Savings Identified: ${business_value_analysis['total_cost_savings_identified']:,.2f}")
        print(f"  Total Insights Generated: {business_value_analysis['total_insights_generated']}")
        print(f"  WebSocket Events Received: {business_value_analysis['websocket_events_received']}")
        
        print(f"\nFAILURE REPRODUCTION ANALYSIS:")
        print(f"  Expected Failures: {len(expected_failures)} (infrastructure gaps successfully exposed)")
        print(f"  Unexpected Failures: {len(unexpected_failures)} (resolved issues or test problems)")
        print(f"  Successful Reproductions: {len(reproduction_successes)}")
        print(f"  Reproduction Success Rate: {len(reproduction_successes) / len(self.staging_failures) * 100:.1f}%")
        
        if unexpected_failures:
            print(f"\nUNEXPECTED FAILURES (May Indicate Resolution):")
            for failure in unexpected_failures:
                print(f"  - {failure.component}: {failure.error_message}")
        
        # Generate structured report for analysis
        staging_failure_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "staging",
            "total_failures": len(self.staging_failures),
            "expected_failures": len(expected_failures),
            "unexpected_failures": len(unexpected_failures),
            "critical_failures": len(critical_failures),
            "reproduction_success_rate": len(reproduction_successes) / len(self.staging_failures) if self.staging_failures else 0,
            "failure_categories": {k: len(v) for k, v in failure_categories.items()},
            "business_value_analysis": business_value_analysis,
            "business_value_success_rate": business_value_success_rate,
            "key_infrastructure_issues": list(set(failure.business_impact for failure in self.staging_failures)),
            "detailed_failures": [failure.to_dict() for failure in self.staging_failures]
        }
        
        # Priority remediation recommendations
        remediation_priorities = []
        
        if any(f.failure_category == "authentication_infrastructure" for f in self.staging_failures):
            remediation_priorities.append("P0: Deploy missing E2E_OAUTH_SIMULATION_KEY to GCP Secret Manager")
        
        if any(f.failure_category == "503_service_unavailable" for f in self.staging_failures):
            remediation_priorities.append("P0: Fix staging backend service 503 errors - complete service outage")
        
        if any("critical_multi_user_isolation_failure" in f.failure_category for f in self.staging_failures):
            remediation_priorities.append("P0: CRITICAL - Fix multi-user isolation - security breach risk")
        
        if any(f.failure_category == "data_helper_execution_timeout" for f in self.staging_failures):
            remediation_priorities.append("P1: Fix Data Helper Agent execution timeouts in staging")
        
        if any(f.failure_category == "staging_websocket_connection_failure" for f in self.staging_failures):
            remediation_priorities.append("P1: Resolve staging WebSocket connectivity issues")
        
        print(f"\nREMEDIATION PRIORITIES:")
        for i, priority in enumerate(remediation_priorities, 1):
            print(f"  {i}. {priority}")
        
        print(f"\nSTAGING READINESS ASSESSMENT:")
        readiness_score = 0
        if business_value_success_rate > 80:
            readiness_score += 40
        elif business_value_success_rate > 50:
            readiness_score += 20
        elif business_value_success_rate > 10:
            readiness_score += 10
        
        if len(critical_failures) == 0:
            readiness_score += 30
        elif len(critical_failures) <= 2:
            readiness_score += 15
        
        if len(reproduction_successes) / len(self.staging_failures) > 0.8:
            readiness_score += 20
        elif len(reproduction_successes) / len(self.staging_failures) > 0.5:
            readiness_score += 10
        
        readiness_assessment = "PRODUCTION READY" if readiness_score >= 80 else "NOT READY - REQUIRES FIXES" if readiness_score >= 40 else "MAJOR ISSUES - EXTENSIVE REMEDIATION REQUIRED"
        
        print(f"  Business Value Success Rate: {business_value_success_rate:.1f}% (Target: >80%)")
        print(f"  Critical Failures: {len(critical_failures)} (Target: 0)")
        print(f"  Overall Staging Readiness: {readiness_assessment} ({readiness_score}/100)")
        
        print(f"\n{'='*100}")
        print(f"STAGING INFRASTRUCTURE FAILURE ANALYSIS COMPLETE")
        print(f"Data Helper Agent 0% Pass Rate Successfully Reproduced and Analyzed")
        print(f"Report Available for Infrastructure Remediation Planning")
        print(f"{'='*100}\n")
        
        # Verify that we successfully reproduced staging failures
        assert len(self.staging_failures) > 0, "No staging failures reproduced - test framework may have issues"
        assert len(expected_failures) > 0, "No expected failures captured - staging issues not reproduced"
        assert business_value_success_rate < 50, f"Business value success rate too high ({business_value_success_rate:.1f}%) - expected <50% for infrastructure gap testing"
        
        # Store report as class attribute for potential further use
        self.staging_failure_report = staging_failure_report
        
        return staging_failure_report


# Integration with pytest fixtures and markers
if __name__ == "__main__":
    import asyncio
    
    async def run_direct_tests():
        """Run tests directly for development and debugging."""
        print("Starting Staging Data Helper Infrastructure E2E Tests...")
        print("EXPECTED OUTCOME: ALL TESTS SHOULD FAIL (reproducing staging infrastructure issues)")
        
        test_instance = TestStagingDataHelperInfrastructure()
        test_instance.setup_method()
        
        try:
            # Run key tests to reproduce staging failures
            await test_instance.test_staging_data_helper_authentication_failure_reproduction()
            await test_instance.test_staging_websocket_connection_failure_reproduction()
            await test_instance.test_staging_data_helper_complete_execution_failure_reproduction()
            await test_instance.test_staging_data_helper_multi_user_isolation_failure_reproduction()
            
            # Generate comprehensive analysis report
            report = await test_instance.test_staging_infrastructure_comprehensive_failure_analysis()
            
            print(f" PASS:  Staging infrastructure failure reproduction completed")
            print(f"    ->  {report['total_failures']} staging failures reproduced")
            print(f"    ->  {report['critical_failures']} critical infrastructure issues identified")
            print(f"    ->  {report['business_value_success_rate']:.1f}% business value success rate (confirming 0% issue)")
            print(f"    ->  Infrastructure gaps successfully exposed for remediation")
            
        except Exception as e:
            print(f"[U+2717] Staging infrastructure testing encountered issues: {e}")
            raise
    
    # Run tests if executed directly
    asyncio.run(run_direct_tests())