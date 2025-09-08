"""
API Contract Validation Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Reliability & Development Velocity
- Business Goal: Ensure API compatibility and prevent breaking changes
- Value Impact: Reduces integration failures and deployment rollbacks
- Strategic Impact: Enables confident deployments and faster feature delivery

These tests validate API contracts between services to ensure backward compatibility
and proper error handling across service boundaries.
"""

import pytest
import httpx
from typing import Dict, Any, List
from unittest.mock import Mock, patch
from datetime import datetime

from test_framework.ssot.base_test_case import BaseTestCase
from shared.isolated_environment import get_env


class TestAPIContractValidation(BaseTestCase):
    """Integration tests for API contract validation between services."""
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.api_contract
    async def test_auth_service_token_validation_contract(self):
        """
        Test auth service token validation API contract compliance.
        
        BVJ: Security critical - ensures token validation API maintains expected
        interface, preventing authentication bypasses due to contract changes.
        """
        env = get_env()
        env.enable_isolation()
        env.set("AUTH_SERVICE_URL", "http://localhost:8081", "test")
        
        # Define expected API contract for token validation
        expected_request_schema = {
            "url": "/api/auth/validate",
            "method": "POST",
            "required_headers": ["Authorization", "Content-Type"],
            "required_fields": ["token"],
            "optional_fields": ["include_permissions", "validate_scopes"]
        }
        
        expected_response_schema = {
            "success_response": {
                "required_fields": ["valid", "user_id", "email"],
                "optional_fields": ["scopes", "permissions", "expires_at"],
                "status_codes": [200]
            },
            "error_response": {
                "required_fields": ["valid", "error", "message"],
                "optional_fields": ["error_code", "details"],
                "status_codes": [401, 400, 500]
            }
        }
        
        # Mock successful validation response
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "valid": True,
            "user_id": "test-user-123",
            "email": "test@example.com",
            "scopes": ["read", "write"],
            "permissions": ["agent_access"],
            "expires_at": "2024-09-07T16:30:00Z"
        }
        
        with patch('httpx.AsyncClient.post', return_value=mock_success_response) as mock_post:
            # Test successful token validation contract
            request_data = {
                "token": "test-jwt-token",
                "include_permissions": True
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{env.get('AUTH_SERVICE_URL')}/api/auth/validate",
                    json=request_data,
                    headers={
                        "Authorization": "Bearer service-secret",
                        "Content-Type": "application/json"
                    }
                )
            
            # Verify API call structure
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # Verify URL contract
            called_url = str(call_args[1]["url"])
            assert "/api/auth/validate" in called_url, "Must use correct API endpoint"
            
            # Verify request headers contract
            headers = call_args[1]["headers"]
            for required_header in expected_request_schema["required_headers"]:
                assert required_header in headers, f"Missing required header: {required_header}"
            
            # Verify request body contract
            request_json = call_args[1]["json"]
            for required_field in expected_request_schema["required_fields"]:
                assert required_field in request_json, f"Missing required field: {required_field}"
            
            # Verify response contract
            response_data = mock_success_response.json()
            success_schema = expected_response_schema["success_response"]
            
            for required_field in success_schema["required_fields"]:
                assert required_field in response_data, f"Response missing required field: {required_field}"
            
            # Verify response data types
            assert isinstance(response_data["valid"], bool), "valid field must be boolean"
            assert isinstance(response_data["user_id"], str), "user_id must be string"
            assert isinstance(response_data["email"], str), "email must be string"
            
            # Verify status code contract
            assert mock_success_response.status_code in success_schema["status_codes"]
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.api_contract
    async def test_analytics_event_ingestion_contract(self):
        """
        Test analytics service event ingestion API contract compliance.
        
        BVJ: Data pipeline reliability - ensures event data is properly structured
        and processed, maintaining data quality for business intelligence.
        """
        env = get_env()
        env.enable_isolation()
        env.set("ANALYTICS_SERVICE_URL", "http://localhost:8002", "test")
        
        # Define expected API contract for event ingestion
        expected_contract = {
            "url": "/api/events/ingest",
            "method": "POST",
            "required_headers": ["Authorization", "Content-Type"],
            "required_fields": ["user_id", "event_type", "timestamp"],
            "optional_fields": ["event_data", "session_id", "metadata"],
            "event_types": ["agent_execution", "user_action", "system_event"],
            "response_fields": ["event_id", "status", "processed_at"]
        }
        
        # Mock successful ingestion response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "event_id": "evt_789456123",
            "status": "accepted",
            "processed_at": "2024-09-07T15:45:00Z",
            "validation_warnings": []
        }
        
        # Test event data structure
        test_event = {
            "user_id": "user-contract-test",
            "event_type": "agent_execution",
            "timestamp": "2024-09-07T15:44:30Z",
            "event_data": {
                "agent_type": "cost_optimizer",
                "execution_time_ms": 1500,
                "tokens_used": 420,
                "success": True
            },
            "session_id": "session-contract-123",
            "metadata": {
                "source": "backend_service",
                "version": "1.0.0"
            }
        }
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Test event ingestion contract
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{env.get('ANALYTICS_SERVICE_URL')}/api/events/ingest",
                    json=test_event,
                    headers={
                        "Authorization": "Bearer service-secret",
                        "Content-Type": "application/json"
                    }
                )
            
            # Verify API contract compliance
            call_args = mock_post.call_args
            
            # Verify URL contract
            called_url = str(call_args[1]["url"])
            assert "/api/events/ingest" in called_url, "Must use correct ingestion endpoint"
            
            # Verify request structure
            sent_event = call_args[1]["json"]
            
            # Check required fields
            for field in expected_contract["required_fields"]:
                assert field in sent_event, f"Event missing required field: {field}"
            
            # Verify event type is valid
            assert sent_event["event_type"] in expected_contract["event_types"], \
                f"Invalid event type: {sent_event['event_type']}"
            
            # Verify timestamp format (ISO 8601)
            timestamp = sent_event["timestamp"]
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                assert False, f"Invalid timestamp format: {timestamp}"
            
            # Verify response contract
            response_data = mock_response.json()
            for field in expected_contract["response_fields"]:
                assert field in response_data, f"Response missing required field: {field}"
            
            # Verify response data types
            assert isinstance(response_data["event_id"], str), "event_id must be string"
            assert isinstance(response_data["status"], str), "status must be string"
            assert response_data["status"] in ["accepted", "rejected", "queued"], \
                f"Invalid status: {response_data['status']}"
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.api_contract
    async def test_backend_agent_execution_api_contract(self):
        """
        Test backend agent execution API contract for frontend integration.
        
        BVJ: User experience critical - ensures frontend can reliably trigger
        agent executions and receive proper responses, maintaining core platform value.
        """
        env = get_env()
        env.enable_isolation()
        env.set("BACKEND_SERVICE_URL", "http://localhost:8000", "test")
        
        # Define expected API contract for agent execution
        expected_contract = {
            "url": "/api/agents/execute",
            "method": "POST",
            "required_headers": ["Authorization", "Content-Type"],
            "required_fields": ["agent_type", "user_message"],
            "optional_fields": ["context", "settings", "thread_id"],
            "agent_types": ["cost_optimizer", "security_advisor", "triage_agent"],
            "response_fields": ["execution_id", "status", "result"]
        }
        
        # Mock agent execution response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "execution_id": "exec_456789012",
            "status": "completed",
            "result": {
                "summary": "Cost optimization analysis complete",
                "recommendations": [
                    {
                        "category": "infrastructure",
                        "description": "Resize underutilized instances",
                        "potential_savings": 1250.00
                    }
                ],
                "total_potential_savings": 1250.00
            },
            "execution_time_ms": 3500,
            "tokens_used": 890,
            "created_at": "2024-09-07T15:40:00Z",
            "completed_at": "2024-09-07T15:40:03Z"
        }
        
        # Test execution request
        execution_request = {
            "agent_type": "cost_optimizer",
            "user_message": "Analyze my AWS costs for optimization opportunities",
            "context": {
                "user_id": "user-contract-test",
                "subscription_tier": "enterprise"
            },
            "settings": {
                "include_recommendations": True,
                "max_execution_time": 30
            },
            "thread_id": "thread_contract_123"
        }
        
        with patch('httpx.AsyncClient.post', return_value=mock_response) as mock_post:
            # Test agent execution contract
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{env.get('BACKEND_SERVICE_URL')}/api/agents/execute",
                    json=execution_request,
                    headers={
                        "Authorization": "Bearer user-jwt-token",
                        "Content-Type": "application/json"
                    }
                )
            
            # Verify API contract compliance
            call_args = mock_post.call_args
            
            # Verify URL contract
            called_url = str(call_args[1]["url"])
            assert "/api/agents/execute" in called_url, "Must use correct execution endpoint"
            
            # Verify request structure
            sent_request = call_args[1]["json"]
            
            # Check required fields
            for field in expected_contract["required_fields"]:
                assert field in sent_request, f"Request missing required field: {field}"
            
            # Verify agent type is supported
            assert sent_request["agent_type"] in expected_contract["agent_types"], \
                f"Unsupported agent type: {sent_request['agent_type']}"
            
            # Verify user message is substantial
            assert len(sent_request["user_message"]) >= 10, "User message must be substantial"
            
            # Verify response contract
            response_data = mock_response.json()
            for field in expected_contract["response_fields"]:
                assert field in response_data, f"Response missing required field: {field}"
            
            # Verify response data structure
            assert isinstance(response_data["execution_id"], str), "execution_id must be string"
            assert response_data["status"] in ["queued", "running", "completed", "failed"], \
                f"Invalid status: {response_data['status']}"
            assert isinstance(response_data["result"], dict), "result must be object"
            
            # Verify result structure for completed execution
            if response_data["status"] == "completed":
                result = response_data["result"]
                assert "summary" in result, "Completed result must have summary"
                assert isinstance(result["summary"], str), "Summary must be string"
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.api_contract
    async def test_error_response_contract_consistency(self):
        """
        Test error response contract consistency across all services.
        
        BVJ: Developer experience - ensures consistent error handling across
        services, reducing integration complexity and debugging time.
        """
        env = get_env()
        env.enable_isolation()
        
        # Define standard error response contract
        standard_error_contract = {
            "required_fields": ["error", "message", "timestamp"],
            "optional_fields": ["error_code", "details", "request_id"],
            "error_types": ["validation_error", "authentication_error", "authorization_error", 
                           "not_found", "internal_error", "service_unavailable"],
            "status_codes": [400, 401, 403, 404, 422, 500, 503]
        }
        
        # Mock error responses for different services
        services_and_errors = [
            ("backend", "http://localhost:8000", 400, {
                "error": "validation_error",
                "message": "Invalid agent type specified",
                "error_code": "INVALID_AGENT_TYPE",
                "details": {"field": "agent_type", "value": "invalid_agent"},
                "timestamp": "2024-09-07T15:50:00Z",
                "request_id": "req_123456"
            }),
            ("auth", "http://localhost:8081", 401, {
                "error": "authentication_error", 
                "message": "Invalid or expired token",
                "error_code": "TOKEN_EXPIRED",
                "timestamp": "2024-09-07T15:50:01Z"
            }),
            ("analytics", "http://localhost:8002", 422, {
                "error": "validation_error",
                "message": "Event data validation failed",
                "details": {"missing_fields": ["user_id", "timestamp"]},
                "timestamp": "2024-09-07T15:50:02Z"
            })
        ]
        
        for service_name, service_url, status_code, error_response in services_and_errors:
            # Mock error response
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.json.return_value = error_response
            
            with patch('httpx.AsyncClient.post', return_value=mock_response):
                # Verify error response contract
                
                # Check required fields
                for field in standard_error_contract["required_fields"]:
                    assert field in error_response, \
                        f"{service_name} error response missing required field: {field}"
                
                # Verify error type is standard
                assert error_response["error"] in standard_error_contract["error_types"], \
                    f"{service_name} uses non-standard error type: {error_response['error']}"
                
                # Verify status code is appropriate
                assert status_code in standard_error_contract["status_codes"], \
                    f"{service_name} uses non-standard status code: {status_code}"
                
                # Verify message is descriptive
                assert len(error_response["message"]) >= 10, \
                    f"{service_name} error message too brief: {error_response['message']}"
                
                # Verify timestamp format
                timestamp = error_response["timestamp"]
                try:
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    assert False, f"{service_name} invalid timestamp format: {timestamp}"
                
                # Verify optional fields are properly typed
                if "details" in error_response:
                    assert isinstance(error_response["details"], (dict, list)), \
                        f"{service_name} details must be object or array"
                
                if "error_code" in error_response:
                    assert isinstance(error_response["error_code"], str), \
                        f"{service_name} error_code must be string"
                    assert len(error_response["error_code"]) >= 3, \
                        f"{service_name} error_code too brief"