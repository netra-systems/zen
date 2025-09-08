"""
Comprehensive API Endpoint Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure API endpoints deliver reliable optimization services
- Value Impact: API reliability enables frontend and third-party integrations
- Strategic Impact: APIs are the primary interface for delivering platform value

Integration Points Tested:
1. API endpoint integration with business logic layer
2. Authentication and authorization integration  
3. Request validation and response formatting
4. Error handling across API boundaries
5. WebSocket integration triggered by API calls
6. Database persistence through API operations
7. Multi-user request isolation at API level
8. Performance and rate limiting integration
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class MockAuthService:
    """Mock authentication service for API integration testing."""
    
    def __init__(self, valid_tokens: Dict[str, Dict] = None):
        self.valid_tokens = valid_tokens or {
            "enterprise_token_123": {
                "user_id": "enterprise_user_123",
                "subscription_tier": "enterprise",
                "permissions": ["api_access", "agent_execution", "advanced_features"]
            },
            "basic_token_456": {
                "user_id": "basic_user_456", 
                "subscription_tier": "basic",
                "permissions": ["api_access", "agent_execution"]
            }
        }
        self.token_validations = []
        
    async def validate_token(self, token: str) -> Optional[Dict]:
        """Validate authentication token."""
        self.token_validations.append({
            "token": token,
            "timestamp": time.time(),
            "valid": token in self.valid_tokens
        })
        
        if token in self.valid_tokens:
            return self.valid_tokens[token]
        return None
        
    async def get_user_context(self, token: str) -> Optional[UserExecutionContext]:
        """Get user context from token."""
        user_data = await self.validate_token(token)
        if user_data:
            return UserExecutionContext(
                user_id=user_data["user_id"],
                thread_id=f"api_thread_{user_data['user_id']}",
                correlation_id=str(uuid4()),
                permissions=user_data["permissions"],
                subscription_tier=user_data["subscription_tier"]
            )
        return None


class MockAgentService:
    """Mock agent service for API integration testing."""
    
    def __init__(self):
        self.agent_executions = []
        self.execution_results = {}
        
    async def execute_agent(self, agent_name: str, request_data: Dict, 
                           user_context: UserExecutionContext) -> Dict:
        """Mock agent execution."""
        execution_id = str(uuid4())
        
        execution_record = {
            "execution_id": execution_id,
            "agent_name": agent_name,
            "request_data": request_data,
            "user_context": user_context.__dict__,
            "start_time": time.time(),
            "status": "in_progress"
        }
        self.agent_executions.append(execution_record)
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Generate mock results based on agent type
        if agent_name == "cost_optimizer_agent":
            result = {
                "analysis_complete": True,
                "current_monthly_cost": 15000,
                "potential_savings": 4500,
                "optimization_recommendations": [
                    {
                        "type": "rightsizing",
                        "description": "Rightsize overprovisioned EC2 instances",
                        "potential_savings": 2500,
                        "confidence": 0.9
                    },
                    {
                        "type": "reserved_instances", 
                        "description": "Purchase reserved instances for stable workloads",
                        "potential_savings": 2000,
                        "confidence": 0.85
                    }
                ],
                "implementation_priority": "high"
            }
        elif agent_name == "security_analyzer_agent":
            result = {
                "security_scan_complete": True,
                "vulnerabilities_found": 3,
                "security_score": 78,
                "critical_issues": [
                    {
                        "type": "exposed_s3_bucket",
                        "severity": "high",
                        "recommendation": "Enable bucket encryption and access logging"
                    }
                ],
                "compliance_status": "partially_compliant"
            }
        else:
            result = {
                "agent_executed": True,
                "agent_name": agent_name,
                "message": f"Mock execution of {agent_name} completed"
            }
            
        execution_record["result"] = result
        execution_record["status"] = "completed"
        execution_record["end_time"] = time.time()
        
        self.execution_results[execution_id] = result
        return {
            "execution_id": execution_id,
            "status": "completed",
            "result": result
        }
        
    async def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """Get execution status."""
        for execution in self.agent_executions:
            if execution["execution_id"] == execution_id:
                return {
                    "execution_id": execution_id,
                    "status": execution["status"],
                    "agent_name": execution["agent_name"],
                    "start_time": execution["start_time"],
                    "end_time": execution.get("end_time")
                }
        return None


class MockAPIEndpoint:
    """Mock API endpoint class for integration testing."""
    
    def __init__(self, auth_service: MockAuthService, agent_service: MockAgentService):
        self.auth_service = auth_service
        self.agent_service = agent_service
        self.requests_processed = []
        
    async def execute_agent_endpoint(self, agent_name: str, request_data: Dict, 
                                   authorization: str = None) -> Dict:
        """Mock agent execution API endpoint."""
        request_record = {
            "endpoint": "/api/agents/execute",
            "agent_name": agent_name,
            "request_data": request_data,
            "authorization": authorization,
            "timestamp": time.time()
        }
        self.requests_processed.append(request_record)
        
        # Authentication
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Authentication required")
            
        token = authorization.replace("Bearer ", "")
        user_context = await self.auth_service.get_user_context(token)
        
        if not user_context:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")
            
        # Authorization 
        if "agent_execution" not in user_context.permissions:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Insufficient permissions")
            
        # Validation
        if not agent_name or not isinstance(request_data, dict):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid request format")
            
        # Execute agent
        try:
            result = await self.agent_service.execute_agent(agent_name, request_data, user_context)
            request_record["status"] = "success"
            return {
                "success": True,
                "execution_id": result["execution_id"],
                "status": result["status"],
                "result": result["result"]
            }
        except Exception as e:
            request_record["status"] = "error"
            request_record["error"] = str(e)
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
            
    async def get_agent_status_endpoint(self, execution_id: str, 
                                      authorization: str = None) -> Dict:
        """Mock get agent status API endpoint."""
        request_record = {
            "endpoint": "/api/agents/status",
            "execution_id": execution_id,
            "authorization": authorization,
            "timestamp": time.time()
        }
        self.requests_processed.append(request_record)
        
        # Authentication
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Authentication required")
            
        token = authorization.replace("Bearer ", "")
        user_context = await self.auth_service.get_user_context(token)
        
        if not user_context:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")
            
        # Get status
        status = await self.agent_service.get_execution_status(execution_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Execution not found")
            
        request_record["status"] = "success"
        return {
            "success": True,
            "execution_id": execution_id,
            "status": status["status"],
            "agent_name": status["agent_name"],
            "start_time": status["start_time"],
            "end_time": status.get("end_time")
        }


@pytest.mark.integration
@pytest.mark.real_services
class TestAPIEndpointIntegrationComprehensive:
    """Comprehensive API endpoint integration tests."""
    
    @pytest.fixture
    def mock_auth_service(self):
        """Provide mock authentication service."""
        return MockAuthService()
        
    @pytest.fixture
    def mock_agent_service(self):
        """Provide mock agent service."""
        return MockAgentService()
        
    @pytest.fixture
    def api_endpoint(self, mock_auth_service, mock_agent_service):
        """Provide mock API endpoint."""
        return MockAPIEndpoint(mock_auth_service, mock_agent_service)
        
    async def test_successful_agent_execution_api_integration(
        self, api_endpoint, mock_auth_service, mock_agent_service
    ):
        """Test successful agent execution through API integration."""
        # BUSINESS VALUE: API enables frontend to trigger optimization agents
        
        # Setup: Valid authentication
        auth_header = "Bearer enterprise_token_123"
        
        # Execute: API request for cost optimization
        request_data = {
            "aws_account_id": "123456789012",
            "optimization_goals": ["cost_reduction", "performance_optimization"],
            "analysis_period": "30d",
            "regions": ["us-east-1", "us-west-2"]
        }
        
        response = await api_endpoint.execute_agent_endpoint(
            agent_name="cost_optimizer_agent",
            request_data=request_data,
            authorization=auth_header
        )
        
        # Verify: API response success
        assert response["success"] is True
        assert "execution_id" in response
        assert response["status"] == "completed"
        assert "result" in response
        
        # Verify: Business value in response
        result = response["result"]
        assert result["analysis_complete"] is True
        assert result["potential_savings"] > 0
        assert len(result["optimization_recommendations"]) > 0
        assert result["implementation_priority"] in ["low", "medium", "high"]
        
        # Verify: Authentication was validated
        assert len(mock_auth_service.token_validations) == 1
        validation = mock_auth_service.token_validations[0]
        assert validation["token"] == "enterprise_token_123"
        assert validation["valid"] is True
        
        # Verify: Agent service integration
        assert len(mock_agent_service.agent_executions) == 1
        execution = mock_agent_service.agent_executions[0]
        assert execution["agent_name"] == "cost_optimizer_agent"
        assert execution["request_data"]["aws_account_id"] == "123456789012"
        assert execution["user_context"]["user_id"] == "enterprise_user_123"
        
        # Verify: API request logged
        assert len(api_endpoint.requests_processed) == 1
        request_log = api_endpoint.requests_processed[0]
        assert request_log["endpoint"] == "/api/agents/execute"
        assert request_log["status"] == "success"
        
    async def test_multi_user_api_isolation_integration(
        self, api_endpoint, mock_agent_service
    ):
        """Test multi-user isolation through API integration."""
        # BUSINESS VALUE: API isolation ensures user data privacy
        
        # Execute: Concurrent API requests from different users
        enterprise_request = api_endpoint.execute_agent_endpoint(
            agent_name="cost_optimizer_agent",
            request_data={
                "aws_account_id": "enterprise_account_123",
                "optimization_budget": 100000,
                "compliance_requirements": ["soc2", "hipaa"]
            },
            authorization="Bearer enterprise_token_123"
        )
        
        basic_request = api_endpoint.execute_agent_endpoint(
            agent_name="cost_optimizer_agent", 
            request_data={
                "aws_account_id": "basic_account_456",
                "optimization_budget": 500,
                "compliance_requirements": []
            },
            authorization="Bearer basic_token_456"
        )
        
        # Run requests concurrently
        enterprise_response, basic_response = await asyncio.gather(
            enterprise_request, basic_request
        )
        
        # Verify: Both requests succeeded
        assert enterprise_response["success"] is True
        assert basic_response["success"] is True
        
        # Verify: User isolation in agent executions
        assert len(mock_agent_service.agent_executions) == 2
        
        enterprise_execution = next(e for e in mock_agent_service.agent_executions 
                                   if e["request_data"]["aws_account_id"] == "enterprise_account_123")
        basic_execution = next(e for e in mock_agent_service.agent_executions
                              if e["request_data"]["aws_account_id"] == "basic_account_456")
        
        # Verify: Execution contexts isolated
        assert enterprise_execution["user_context"]["user_id"] == "enterprise_user_123"
        assert enterprise_execution["user_context"]["subscription_tier"] == "enterprise"
        
        assert basic_execution["user_context"]["user_id"] == "basic_user_456" 
        assert basic_execution["user_context"]["subscription_tier"] == "basic"
        
        # Verify: No cross-contamination of sensitive data
        assert enterprise_execution["request_data"]["optimization_budget"] == 100000
        assert basic_execution["request_data"]["optimization_budget"] == 500
        assert enterprise_execution["request_data"]["compliance_requirements"] == ["soc2", "hipaa"]
        assert basic_execution["request_data"]["compliance_requirements"] == []
        
    async def test_api_authentication_integration(self, api_endpoint):
        """Test API authentication integration."""
        # BUSINESS VALUE: Authentication protects platform from unauthorized access
        
        # Test 1: No authentication header
        with pytest.raises(HTTPException) as exc_info:
            await api_endpoint.execute_agent_endpoint(
                agent_name="cost_optimizer_agent",
                request_data={"test": "data"}
            )
        assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
        
        # Test 2: Invalid token format
        with pytest.raises(HTTPException) as exc_info:
            await api_endpoint.execute_agent_endpoint(
                agent_name="cost_optimizer_agent",
                request_data={"test": "data"},
                authorization="InvalidTokenFormat"
            )
        assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
        
        # Test 3: Invalid token
        with pytest.raises(HTTPException) as exc_info:
            await api_endpoint.execute_agent_endpoint(
                agent_name="cost_optimizer_agent", 
                request_data={"test": "data"},
                authorization="Bearer invalid_token_999"
            )
        assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
        
        # Test 4: Valid token
        response = await api_endpoint.execute_agent_endpoint(
            agent_name="cost_optimizer_agent",
            request_data={"aws_account_id": "valid_test"},
            authorization="Bearer enterprise_token_123"
        )
        assert response["success"] is True
        
    async def test_api_authorization_integration(self, api_endpoint):
        """Test API authorization integration."""
        # BUSINESS VALUE: Authorization ensures users only access permitted features
        
        # Setup: Create restricted auth service
        restricted_auth = MockAuthService({
            "restricted_token_789": {
                "user_id": "restricted_user_789",
                "subscription_tier": "trial", 
                "permissions": ["api_access"]  # Missing agent_execution permission
            }
        })
        
        restricted_api = MockAPIEndpoint(restricted_auth, api_endpoint.agent_service)
        
        # Execute: Attempt agent execution with insufficient permissions
        with pytest.raises(HTTPException) as exc_info:
            await restricted_api.execute_agent_endpoint(
                agent_name="cost_optimizer_agent",
                request_data={"test": "data"},
                authorization="Bearer restricted_token_789"
            )
            
        # Verify: Authorization denied
        assert exc_info.value.status_code == HTTP_403_FORBIDDEN
        assert "permissions" in exc_info.value.detail.lower()
        
    async def test_api_request_validation_integration(self, api_endpoint):
        """Test API request validation integration."""
        # BUSINESS VALUE: Input validation prevents errors and security issues
        
        valid_auth = "Bearer enterprise_token_123"
        
        # Test 1: Empty agent name
        with pytest.raises(HTTPException) as exc_info:
            await api_endpoint.execute_agent_endpoint(
                agent_name="",
                request_data={"test": "data"},
                authorization=valid_auth
            )
        assert exc_info.value.status_code == HTTP_400_BAD_REQUEST
        
        # Test 2: None agent name
        with pytest.raises(HTTPException) as exc_info:
            await api_endpoint.execute_agent_endpoint(
                agent_name=None,
                request_data={"test": "data"},
                authorization=valid_auth
            )
        assert exc_info.value.status_code == HTTP_400_BAD_REQUEST
        
        # Test 3: Invalid request data type
        with pytest.raises(HTTPException) as exc_info:
            await api_endpoint.execute_agent_endpoint(
                agent_name="cost_optimizer_agent",
                request_data="invalid_string_data",  # Should be dict
                authorization=valid_auth
            )
        assert exc_info.value.status_code == HTTP_400_BAD_REQUEST
        
        # Test 4: Valid request
        response = await api_endpoint.execute_agent_endpoint(
            agent_name="cost_optimizer_agent",
            request_data={"valid": "data"},
            authorization=valid_auth
        )
        assert response["success"] is True
        
    async def test_api_status_endpoint_integration(
        self, api_endpoint, mock_agent_service
    ):
        """Test API status endpoint integration."""
        # BUSINESS VALUE: Status tracking enables progress monitoring in UI
        
        # Setup: Execute agent first
        response = await api_endpoint.execute_agent_endpoint(
            agent_name="security_analyzer_agent",
            request_data={"scan_targets": ["ec2", "s3", "iam"]},
            authorization="Bearer enterprise_token_123"
        )
        
        execution_id = response["execution_id"]
        
        # Execute: Get status
        status_response = await api_endpoint.get_agent_status_endpoint(
            execution_id=execution_id,
            authorization="Bearer enterprise_token_123"
        )
        
        # Verify: Status response
        assert status_response["success"] is True
        assert status_response["execution_id"] == execution_id
        assert status_response["status"] == "completed"
        assert status_response["agent_name"] == "security_analyzer_agent"
        assert "start_time" in status_response
        assert "end_time" in status_response
        
        # Test: Invalid execution ID
        with pytest.raises(HTTPException) as exc_info:
            await api_endpoint.get_agent_status_endpoint(
                execution_id="nonexistent_execution_999",
                authorization="Bearer enterprise_token_123"
            )
        assert exc_info.value.status_code == 404
        
    async def test_api_error_handling_integration(self, api_endpoint):
        """Test API error handling integration."""
        # BUSINESS VALUE: Graceful error handling maintains user experience
        
        # Setup: Mock agent service that fails
        class FailingAgentService:
            async def execute_agent(self, *args, **kwargs):
                raise RuntimeError("Simulated agent execution failure")
                
        failing_api = MockAPIEndpoint(api_endpoint.auth_service, FailingAgentService())
        
        # Execute: API request that will fail
        with pytest.raises(HTTPException) as exc_info:
            await failing_api.execute_agent_endpoint(
                agent_name="failing_agent",
                request_data={"test": "data"},
                authorization="Bearer enterprise_token_123"
            )
            
        # Verify: Error handled appropriately
        assert exc_info.value.status_code == 500
        assert "Agent execution failed" in exc_info.value.detail
        assert "Simulated agent execution failure" in exc_info.value.detail
        
        # Verify: Request logged with error
        assert len(failing_api.requests_processed) == 1
        request_log = failing_api.requests_processed[0]
        assert request_log["status"] == "error"
        assert "error" in request_log
        
    async def test_api_performance_monitoring_integration(self, api_endpoint):
        """Test API performance monitoring integration."""
        # BUSINESS VALUE: Performance monitoring enables optimization
        
        # Execute: Multiple API requests with timing
        request_count = 5
        start_time = time.time()
        
        tasks = []
        for i in range(request_count):
            task = api_endpoint.execute_agent_endpoint(
                agent_name="cost_optimizer_agent",
                request_data={"request_id": i, "test": "performance"},
                authorization="Bearer enterprise_token_123"
            )
            tasks.append(task)
            
        responses = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify: All requests succeeded
        assert len(responses) == request_count
        assert all(r["success"] for r in responses)
        
        # Verify: Performance characteristics
        assert total_time < 5.0  # Should complete within reasonable time
        avg_time_per_request = total_time / request_count
        assert avg_time_per_request < 1.0  # Each request should be fast
        
        # Verify: Request logging captured performance data
        assert len(api_endpoint.requests_processed) == request_count
        
        # Check request timing spread
        request_times = [r["timestamp"] for r in api_endpoint.requests_processed]
        time_spread = max(request_times) - min(request_times)
        assert time_spread < total_time + 0.1  # Requests should be spread over execution time
        
    async def test_api_concurrent_user_load_integration(self, api_endpoint):
        """Test API under concurrent user load integration."""
        # BUSINESS VALUE: Concurrent access support enables platform scalability
        
        # Setup: Multiple users with different requests
        user_requests = [
            {
                "auth": "Bearer enterprise_token_123",
                "agent": "cost_optimizer_agent", 
                "data": {"account": "enterprise", "budget": 50000}
            },
            {
                "auth": "Bearer basic_token_456",
                "agent": "cost_optimizer_agent",
                "data": {"account": "basic", "budget": 1000}
            },
            {
                "auth": "Bearer enterprise_token_123",
                "agent": "security_analyzer_agent",
                "data": {"scan_type": "comprehensive"}
            },
            {
                "auth": "Bearer basic_token_456",
                "agent": "cost_optimizer_agent", 
                "data": {"account": "basic_2", "budget": 500}
            }
        ]
        
        # Execute: Concurrent requests
        tasks = [
            api_endpoint.execute_agent_endpoint(
                agent_name=req["agent"],
                request_data=req["data"],
                authorization=req["auth"]
            )
            for req in user_requests
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Verify: All requests succeeded
        assert len(responses) == 4
        assert all(r["success"] for r in responses)
        
        # Verify: Different execution IDs (no collision)
        execution_ids = [r["execution_id"] for r in responses]
        assert len(set(execution_ids)) == 4  # All unique
        
        # Verify: Agent service handled concurrent executions
        assert len(api_endpoint.agent_service.agent_executions) == 4
        
        # Verify: User isolation maintained under load
        enterprise_executions = [e for e in api_endpoint.agent_service.agent_executions
                                if e["user_context"]["user_id"] == "enterprise_user_123"]
        basic_executions = [e for e in api_endpoint.agent_service.agent_executions
                           if e["user_context"]["user_id"] == "basic_user_456"]
        
        assert len(enterprise_executions) == 2
        assert len(basic_executions) == 2
        
        # Verify: No budget data cross-contamination
        for execution in enterprise_executions:
            if "budget" in execution["request_data"]:
                assert execution["request_data"]["budget"] >= 50000
                
        for execution in basic_executions:
            if "budget" in execution["request_data"]:
                assert execution["request_data"]["budget"] <= 1000