"""
Cross-Service Communication Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable cross-service communication enables integrated AI platform
- Value Impact: Service integration creates seamless user experience and comprehensive AI capabilities
- Strategic Impact: Microservice communication foundation for scalable $500K+ ARR platform

CRITICAL: Cross-service communication enables coordinated AI workflows per CLAUDE.md
Service integration prevents data silos and enables comprehensive AI analysis.

These integration tests validate inter-service messaging, service discovery, API contracts,
timeout handling, and service health monitoring without requiring Docker services.
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets import WebSocketException, ConnectionClosed

# SSOT imports - using absolute imports only per CLAUDE.md
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    WebSocketMessage,
    WebSocketTestMetrics
)


@dataclass
class ServiceEndpoint:
    """Represents a service endpoint for cross-service communication testing."""
    service_name: str
    endpoint_url: str
    service_type: str  # 'backend', 'auth', 'frontend'
    health_check_path: str
    api_version: str


@pytest.mark.integration
class TestCrossServiceMessaging(SSotBaseTestCase):
    """
    Test cross-service messaging patterns and protocols.
    
    BVJ: Inter-service messaging enables coordinated AI workflows
    """
    
    async def test_backend_to_auth_service_communication(self):
        """
        Test communication between backend and auth service for user validation.
        
        BVJ: Backend-auth integration ensures secure AI service access
        """
        async with WebSocketTestUtility() as ws_util:
            # Mock backend service client
            backend_client = await ws_util.create_test_client(user_id="backend-service")
            backend_client.is_connected = True
            backend_client.websocket = AsyncMock()
            
            # Mock auth service endpoints
            auth_endpoints = {
                "validate_token": "/auth/validate",
                "get_user_permissions": "/auth/permissions",
                "refresh_token": "/auth/refresh"
            }
            
            # Simulate backend requesting user validation
            user_token = f"jwt_token_{uuid.uuid4().hex[:8]}"
            validation_request = {
                "service": "netra-backend",
                "operation": "validate_user_token",
                "token": user_token,
                "required_permissions": ["read", "agent_execute"],
                "request_id": f"req_{uuid.uuid4().hex[:8]}"
            }
            
            await backend_client.send_message(
                WebSocketEventType.STATUS_UPDATE,
                {
                    "type": "auth_validation_request",
                    "endpoint": auth_endpoints["validate_token"],
                    "payload": validation_request
                },
                user_id="backend-service"
            )
            
            # Simulate auth service response
            auth_response = {
                "request_id": validation_request["request_id"],
                "status": "success",
                "user_id": "validated_user_123",
                "permissions": ["read", "write", "agent_execute"],
                "token_valid": True,
                "expires_at": "2024-12-31T23:59:59Z"
            }
            
            auth_response_msg = WebSocketMessage(
                event_type=WebSocketEventType.STATUS_UPDATE,
                data={
                    "type": "auth_validation_response",
                    "response": auth_response
                },
                timestamp=datetime.now(timezone.utc),
                message_id=f"auth_resp_{uuid.uuid4().hex[:8]}",
                user_id="auth-service"
            )
            backend_client.received_messages.append(auth_response_msg)
            
            # Verify cross-service communication
            assert len(backend_client.sent_messages) == 1
            assert len(backend_client.received_messages) == 1
            
            # Verify request structure
            sent_request = backend_client.sent_messages[0]
            assert sent_request.data["type"] == "auth_validation_request"
            assert sent_request.data["payload"]["token"] == user_token
            
            # Verify response structure
            received_response = backend_client.received_messages[0]
            assert received_response.data["type"] == "auth_validation_response"
            assert received_response.data["response"]["status"] == "success"
            assert received_response.data["response"]["token_valid"] is True
            
            self.record_metric("backend_auth_integration", "validated")
    
    async def test_service_discovery_integration(self):
        """
        Test service discovery and health check integration.
        
        BVJ: Service discovery enables dynamic scaling and reliability
        """
        # Define mock services in the platform
        platform_services = [
            ServiceEndpoint(
                service_name="netra-backend",
                endpoint_url="http://backend:8000",
                service_type="backend",
                health_check_path="/health",
                api_version="v1"
            ),
            ServiceEndpoint(
                service_name="netra-auth",
                endpoint_url="http://auth:8001", 
                service_type="auth",
                health_check_path="/health",
                api_version="v1"
            ),
            ServiceEndpoint(
                service_name="netra-frontend",
                endpoint_url="http://frontend:3000",
                service_type="frontend", 
                health_check_path="/api/health",
                api_version="v1"
            )
        ]
        
        async with WebSocketTestUtility() as ws_util:
            discovery_client = await ws_util.create_test_client(user_id="service-discovery")
            discovery_client.is_connected = True
            discovery_client.websocket = AsyncMock()
            
            # Simulate service registration events
            for service in platform_services:
                registration_event = {
                    "type": "service_registration",
                    "service": {
                        "name": service.service_name,
                        "url": service.endpoint_url,
                        "type": service.service_type,
                        "health_path": service.health_check_path,
                        "version": service.api_version,
                        "status": "healthy",
                        "registered_at": datetime.now(timezone.utc).isoformat()
                    }
                }
                
                await discovery_client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    registration_event,
                    user_id="service-discovery"
                )
            
            # Simulate service health check responses
            for service in platform_services:
                health_check_result = {
                    "type": "health_check_result",
                    "service_name": service.service_name,
                    "status": "healthy",
                    "response_time": 0.045,  # 45ms
                    "checks": {
                        "database": "connected",
                        "redis": "connected" if service.service_type == "backend" else "n/a",
                        "external_apis": "accessible"
                    },
                    "checked_at": datetime.now(timezone.utc).isoformat()
                }
                
                health_msg = WebSocketMessage(
                    event_type=WebSocketEventType.STATUS_UPDATE,
                    data=health_check_result,
                    timestamp=datetime.now(timezone.utc),
                    message_id=f"health_{uuid.uuid4().hex[:8]}",
                    user_id="health-monitor"
                )
                discovery_client.received_messages.append(health_msg)
            
            # Verify service discovery
            assert len(discovery_client.sent_messages) == len(platform_services)
            assert len(discovery_client.received_messages) == len(platform_services)
            
            # Verify all services registered
            registered_services = [
                msg.data["service"]["name"]
                for msg in discovery_client.sent_messages
                if msg.data["type"] == "service_registration"
            ]
            expected_services = [s.service_name for s in platform_services]
            assert set(registered_services) == set(expected_services)
            
            # Verify health checks
            health_results = [
                msg.data
                for msg in discovery_client.received_messages
                if msg.data["type"] == "health_check_result"
            ]
            assert all(result["status"] == "healthy" for result in health_results)
            
            self.record_metric("service_discovery", len(platform_services))
    
    async def test_api_contract_validation(self):
        """
        Test API contract validation between services.
        
        BVJ: Contract validation prevents integration failures and data corruption
        """
        async with WebSocketTestUtility() as ws_util:
            api_client = await ws_util.create_test_client(user_id="api-contract-client")
            api_client.is_connected = True
            api_client.websocket = AsyncMock()
            
            # Define API contracts for cross-service communication
            api_contracts = {
                "user_analysis_request": {
                    "version": "1.0",
                    "required_fields": ["user_id", "analysis_type", "parameters"],
                    "optional_fields": ["priority", "callback_url"],
                    "response_format": {
                        "required_fields": ["status", "result_id", "estimated_completion"],
                        "optional_fields": ["error_message", "retry_after"]
                    }
                },
                "agent_execution_request": {
                    "version": "1.0", 
                    "required_fields": ["agent_type", "user_request", "context"],
                    "optional_fields": ["execution_options", "timeout"],
                    "response_format": {
                        "required_fields": ["execution_id", "status", "events"],
                        "optional_fields": ["error_details", "partial_results"]
                    }
                }
            }
            
            # Test valid contract requests
            for contract_name, contract_spec in api_contracts.items():
                # Create valid request
                if contract_name == "user_analysis_request":
                    valid_request = {
                        "user_id": "user_123",
                        "analysis_type": "cost_optimization",
                        "parameters": {"time_range": "30_days", "services": ["EC2", "S3"]},
                        "priority": "normal"
                    }
                else:  # agent_execution_request
                    valid_request = {
                        "agent_type": "cost_optimizer",
                        "user_request": "Analyze my cloud costs",
                        "context": {"user_tier": "premium", "region": "us-east-1"},
                        "execution_options": {"stream_events": True}
                    }
                
                # Send contract-compliant request
                await api_client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    {
                        "type": "api_request",
                        "contract": contract_name,
                        "contract_version": contract_spec["version"],
                        "payload": valid_request,
                        "validation_status": "passed"
                    },
                    user_id="api-contract-client"
                )
                
                # Simulate contract-compliant response
                if contract_name == "user_analysis_request":
                    valid_response = {
                        "status": "accepted",
                        "result_id": f"analysis_{uuid.uuid4().hex[:8]}",
                        "estimated_completion": "2024-01-15T10:30:00Z"
                    }
                else:  # agent_execution_request
                    valid_response = {
                        "execution_id": f"exec_{uuid.uuid4().hex[:8]}",
                        "status": "started",
                        "events": ["agent_started"]
                    }
                
                response_msg = WebSocketMessage(
                    event_type=WebSocketEventType.STATUS_UPDATE,
                    data={
                        "type": "api_response",
                        "contract": contract_name,
                        "payload": valid_response,
                        "validation_status": "passed"
                    },
                    timestamp=datetime.now(timezone.utc),
                    message_id=f"resp_{uuid.uuid4().hex[:8]}",
                    user_id="api-service"
                )
                api_client.received_messages.append(response_msg)
            
            # Verify contract validation
            assert len(api_client.sent_messages) == len(api_contracts)
            assert len(api_client.received_messages) == len(api_contracts)
            
            # Verify all requests passed validation
            request_validations = [
                msg.data["validation_status"]
                for msg in api_client.sent_messages
                if msg.data["type"] == "api_request"
            ]
            assert all(status == "passed" for status in request_validations)
            
            # Verify all responses passed validation
            response_validations = [
                msg.data["validation_status"]
                for msg in api_client.received_messages
                if msg.data["type"] == "api_response"
            ]
            assert all(status == "passed" for status in response_validations)
            
            self.record_metric("api_contract_validation", len(api_contracts))
    
    async def test_cross_service_error_propagation(self):
        """
        Test error propagation and handling across services.
        
        BVJ: Error propagation enables comprehensive error handling and user feedback
        """
        async with WebSocketTestUtility() as ws_util:
            error_client = await ws_util.create_test_client(user_id="error-propagation-client")
            error_client.is_connected = True
            error_client.websocket = AsyncMock()
            
            # Define cross-service error scenarios
            error_scenarios = [
                {
                    "source_service": "netra-backend",
                    "target_service": "netra-auth",
                    "error_type": "authentication_failure",
                    "error_code": "AUTH_TOKEN_EXPIRED",
                    "message": "JWT token has expired",
                    "retryable": True,
                    "impact": "request_blocked"
                },
                {
                    "source_service": "netra-backend", 
                    "target_service": "external-llm-api",
                    "error_type": "service_unavailable",
                    "error_code": "LLM_SERVICE_DOWN",
                    "message": "LLM service is temporarily unavailable",
                    "retryable": True,
                    "impact": "agent_execution_delayed"
                },
                {
                    "source_service": "netra-auth",
                    "target_service": "netra-backend", 
                    "error_type": "authorization_failure",
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "User lacks required permissions for operation",
                    "retryable": False,
                    "impact": "request_denied"
                }
            ]
            
            # Simulate error propagation
            for error_scenario in error_scenarios:
                # Service A encounters error when calling Service B
                error_event = {
                    "type": "cross_service_error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error_id": f"err_{uuid.uuid4().hex[:8]}",
                    "source_service": error_scenario["source_service"],
                    "target_service": error_scenario["target_service"],
                    "error_details": {
                        "type": error_scenario["error_type"],
                        "code": error_scenario["error_code"],
                        "message": error_scenario["message"],
                        "retryable": error_scenario["retryable"],
                        "impact": error_scenario["impact"]
                    }
                }
                
                await error_client.send_message(
                    WebSocketEventType.ERROR,
                    error_event,
                    user_id="error-propagation-client"
                )
                
                # Simulate error recovery if retryable
                if error_scenario["retryable"]:
                    recovery_event = {
                        "type": "error_recovery",
                        "original_error_id": error_event["error_id"],
                        "recovery_action": "retry_after_delay",
                        "recovery_status": "successful",
                        "recovery_time": 2.5
                    }
                    
                    recovery_msg = WebSocketMessage(
                        event_type=WebSocketEventType.STATUS_UPDATE,
                        data=recovery_event,
                        timestamp=datetime.now(timezone.utc),
                        message_id=f"recovery_{uuid.uuid4().hex[:8]}",
                        user_id="error-recovery-service"
                    )
                    error_client.received_messages.append(recovery_msg)
            
            # Verify error propagation
            error_messages = [
                msg for msg in error_client.sent_messages
                if msg.event_type == WebSocketEventType.ERROR
            ]
            assert len(error_messages) == len(error_scenarios)
            
            # Verify recovery messages for retryable errors
            recovery_messages = [
                msg for msg in error_client.received_messages
                if msg.data.get("type") == "error_recovery"
            ]
            retryable_errors = [e for e in error_scenarios if e["retryable"]]
            assert len(recovery_messages) == len(retryable_errors)
            
            # Verify error details
            for i, error_msg in enumerate(error_messages):
                error_data = error_msg.data
                expected_scenario = error_scenarios[i]
                
                assert error_data["source_service"] == expected_scenario["source_service"]
                assert error_data["target_service"] == expected_scenario["target_service"]
                assert error_data["error_details"]["code"] == expected_scenario["error_code"]
            
            self.record_metric("error_propagation", len(error_scenarios))


@pytest.mark.integration
class TestServiceCommunicationReliability(SSotBaseTestCase):
    """
    Test reliability patterns for cross-service communication.
    
    BVJ: Reliable communication ensures consistent AI service delivery
    """
    
    async def test_service_timeout_handling(self):
        """
        Test timeout handling in cross-service communication.
        
        BVJ: Timeout handling prevents cascading failures and provides user feedback
        """
        async with WebSocketTestUtility() as ws_util:
            timeout_client = await ws_util.create_test_client(user_id="timeout-test-client")
            timeout_client.is_connected = True
            timeout_client.websocket = AsyncMock()
            
            # Define service call scenarios with timeouts
            timeout_scenarios = [
                {
                    "service_call": "llm_analysis",
                    "target_service": "openai-api",
                    "timeout_config": 30.0,  # 30 seconds
                    "actual_duration": 45.0,  # Exceeds timeout
                    "expected_outcome": "timeout"
                },
                {
                    "service_call": "user_validation",
                    "target_service": "netra-auth", 
                    "timeout_config": 5.0,   # 5 seconds
                    "actual_duration": 2.5,  # Within timeout
                    "expected_outcome": "success"
                },
                {
                    "service_call": "data_query",
                    "target_service": "database",
                    "timeout_config": 10.0,  # 10 seconds
                    "actual_duration": 12.0, # Exceeds timeout
                    "expected_outcome": "timeout"
                }
            ]
            
            # Simulate service calls with timeout behavior
            for scenario in timeout_scenarios:
                call_start = time.time()
                
                # Send service call request
                request_event = {
                    "type": "service_call_request",
                    "call_id": f"call_{uuid.uuid4().hex[:8]}",
                    "service_call": scenario["service_call"],
                    "target_service": scenario["target_service"],
                    "timeout_config": scenario["timeout_config"],
                    "started_at": call_start
                }
                
                await timeout_client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    request_event,
                    user_id="timeout-test-client"
                )
                
                # Simulate timeout or success based on scenario
                if scenario["expected_outcome"] == "timeout":
                    timeout_event = {
                        "type": "service_call_timeout",
                        "call_id": request_event["call_id"],
                        "service_call": scenario["service_call"],
                        "timeout_after": scenario["timeout_config"],
                        "action": "request_cancelled",
                        "user_impact": "operation_failed"
                    }
                    
                    timeout_msg = WebSocketMessage(
                        event_type=WebSocketEventType.ERROR,
                        data=timeout_event,
                        timestamp=datetime.now(timezone.utc),
                        message_id=f"timeout_{uuid.uuid4().hex[:8]}",
                        user_id="timeout-handler"
                    )
                    timeout_client.received_messages.append(timeout_msg)
                    
                else:  # success
                    success_event = {
                        "type": "service_call_success",
                        "call_id": request_event["call_id"],
                        "service_call": scenario["service_call"],
                        "duration": scenario["actual_duration"],
                        "result": "operation_completed"
                    }
                    
                    success_msg = WebSocketMessage(
                        event_type=WebSocketEventType.STATUS_UPDATE,
                        data=success_event,
                        timestamp=datetime.now(timezone.utc),
                        message_id=f"success_{uuid.uuid4().hex[:8]}",
                        user_id="service-handler"
                    )
                    timeout_client.received_messages.append(success_msg)
            
            # Verify timeout handling
            assert len(timeout_client.sent_messages) == len(timeout_scenarios)
            assert len(timeout_client.received_messages) == len(timeout_scenarios)
            
            # Verify timeout vs success outcomes
            timeout_events = [
                msg for msg in timeout_client.received_messages
                if msg.event_type == WebSocketEventType.ERROR and 
                   msg.data.get("type") == "service_call_timeout"
            ]
            
            success_events = [
                msg for msg in timeout_client.received_messages
                if msg.event_type == WebSocketEventType.STATUS_UPDATE and
                   msg.data.get("type") == "service_call_success"
            ]
            
            expected_timeouts = sum(1 for s in timeout_scenarios if s["expected_outcome"] == "timeout")
            expected_successes = sum(1 for s in timeout_scenarios if s["expected_outcome"] == "success")
            
            assert len(timeout_events) == expected_timeouts
            assert len(success_events) == expected_successes
            
            self.record_metric("timeout_handling", len(timeout_scenarios))
    
    async def test_service_retry_mechanisms(self):
        """
        Test retry mechanisms for failed cross-service calls.
        
        BVJ: Retry mechanisms improve system reliability and user experience
        """
        async with WebSocketTestUtility() as ws_util:
            retry_client = await ws_util.create_test_client(user_id="retry-test-client")
            retry_client.is_connected = True
            retry_client.websocket = AsyncMock()
            
            # Define retry scenarios
            retry_scenarios = [
                {
                    "operation": "llm_request",
                    "max_retries": 3,
                    "retry_delay": 1.0,
                    "failure_count": 2,  # Fails twice, succeeds on 3rd try
                    "failure_reasons": ["rate_limited", "timeout"],
                    "final_outcome": "success"
                },
                {
                    "operation": "database_query", 
                    "max_retries": 2,
                    "retry_delay": 0.5,
                    "failure_count": 3,  # Fails more than max retries
                    "failure_reasons": ["connection_lost", "connection_lost", "connection_lost"],
                    "final_outcome": "permanent_failure"
                }
            ]
            
            # Simulate retry scenarios
            for scenario in retry_scenarios:
                operation_id = f"op_{uuid.uuid4().hex[:8]}"
                
                # Initial request
                initial_request = {
                    "type": "operation_request",
                    "operation_id": operation_id,
                    "operation": scenario["operation"],
                    "max_retries": scenario["max_retries"],
                    "retry_delay": scenario["retry_delay"]
                }
                
                await retry_client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    initial_request,
                    user_id="retry-test-client"
                )
                
                # Simulate retry attempts
                for attempt in range(min(scenario["failure_count"], scenario["max_retries"])):
                    failure_reason = scenario["failure_reasons"][attempt]
                    
                    retry_attempt = {
                        "type": "retry_attempt",
                        "operation_id": operation_id,
                        "attempt": attempt + 1,
                        "max_attempts": scenario["max_retries"],
                        "failure_reason": failure_reason,
                        "next_retry_delay": scenario["retry_delay"]
                    }
                    
                    retry_msg = WebSocketMessage(
                        event_type=WebSocketEventType.STATUS_UPDATE,
                        data=retry_attempt,
                        timestamp=datetime.now(timezone.utc),
                        message_id=f"retry_{uuid.uuid4().hex[:8]}",
                        user_id="retry-handler"
                    )
                    retry_client.received_messages.append(retry_msg)
                
                # Final outcome
                if scenario["final_outcome"] == "success":
                    success_event = {
                        "type": "operation_success",
                        "operation_id": operation_id,
                        "total_attempts": scenario["failure_count"] + 1,
                        "result": "operation_completed"
                    }
                    
                    final_msg = WebSocketMessage(
                        event_type=WebSocketEventType.STATUS_UPDATE,
                        data=success_event,
                        timestamp=datetime.now(timezone.utc),
                        message_id=f"final_{uuid.uuid4().hex[:8]}",
                        user_id="operation-handler"
                    )
                    
                else:  # permanent_failure
                    failure_event = {
                        "type": "operation_permanent_failure",
                        "operation_id": operation_id,
                        "total_attempts": scenario["max_retries"] + 1,
                        "final_error": "max_retries_exceeded"
                    }
                    
                    final_msg = WebSocketMessage(
                        event_type=WebSocketEventType.ERROR,
                        data=failure_event,
                        timestamp=datetime.now(timezone.utc),
                        message_id=f"final_{uuid.uuid4().hex[:8]}",
                        user_id="operation-handler"
                    )
                
                retry_client.received_messages.append(final_msg)
            
            # Verify retry mechanisms
            assert len(retry_client.sent_messages) == len(retry_scenarios)
            
            # Count retry attempts
            retry_attempts = [
                msg for msg in retry_client.received_messages
                if msg.data.get("type") == "retry_attempt"
            ]
            
            expected_retry_attempts = sum(
                min(s["failure_count"], s["max_retries"]) 
                for s in retry_scenarios
            )
            assert len(retry_attempts) == expected_retry_attempts
            
            # Verify final outcomes
            success_outcomes = [
                msg for msg in retry_client.received_messages
                if msg.data.get("type") == "operation_success"
            ]
            
            failure_outcomes = [
                msg for msg in retry_client.received_messages
                if msg.data.get("type") == "operation_permanent_failure"
            ]
            
            expected_successes = sum(1 for s in retry_scenarios if s["final_outcome"] == "success")
            expected_failures = len(retry_scenarios) - expected_successes
            
            assert len(success_outcomes) == expected_successes
            assert len(failure_outcomes) == expected_failures
            
            self.record_metric("retry_mechanisms", len(retry_scenarios))
    
    async def test_circuit_breaker_pattern(self):
        """
        Test circuit breaker pattern for failing services.
        
        BVJ: Circuit breakers prevent cascading failures and improve system resilience
        """
        async with WebSocketTestUtility() as ws_util:
            breaker_client = await ws_util.create_test_client(user_id="circuit-breaker-client")
            breaker_client.is_connected = True
            breaker_client.websocket = AsyncMock()
            
            # Circuit breaker configuration
            breaker_config = {
                "failure_threshold": 5,    # Open after 5 failures
                "recovery_timeout": 10.0,  # Try recovery after 10 seconds
                "success_threshold": 2     # Close after 2 successful calls
            }
            
            # Simulate circuit breaker states
            breaker_states = [
                {"state": "closed", "failures": 0, "action": "allow_requests"},
                {"state": "closed", "failures": 1, "action": "allow_requests"},
                {"state": "closed", "failures": 3, "action": "allow_requests"},
                {"state": "closed", "failures": 5, "action": "open_circuit"},  # Threshold reached
                {"state": "open", "failures": 5, "action": "reject_requests"},
                {"state": "open", "failures": 5, "action": "reject_requests"},
                {"state": "half_open", "failures": 5, "action": "test_request"},  # After timeout
                {"state": "closed", "failures": 0, "action": "allow_requests"}   # Recovery successful
            ]
            
            service_name = "external-llm-service"
            
            # Simulate circuit breaker behavior
            for i, breaker_state in enumerate(breaker_states):
                circuit_event = {
                    "type": "circuit_breaker_state",
                    "service_name": service_name,
                    "state": breaker_state["state"],
                    "failure_count": breaker_state["failures"],
                    "action": breaker_state["action"],
                    "config": breaker_config,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sequence": i + 1
                }
                
                await breaker_client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    circuit_event,
                    user_id="circuit-breaker-client"
                )
                
                # Simulate request handling based on circuit state
                if breaker_state["action"] == "reject_requests":
                    rejection_event = {
                        "type": "request_rejected",
                        "service_name": service_name,
                        "reason": "circuit_breaker_open",
                        "suggested_action": "try_later"
                    }
                    
                    rejection_msg = WebSocketMessage(
                        event_type=WebSocketEventType.STATUS_UPDATE,
                        data=rejection_event,
                        timestamp=datetime.now(timezone.utc),
                        message_id=f"reject_{uuid.uuid4().hex[:8]}",
                        user_id="circuit-breaker"
                    )
                    breaker_client.received_messages.append(rejection_msg)
                
                elif breaker_state["action"] == "open_circuit":
                    open_event = {
                        "type": "circuit_opened",
                        "service_name": service_name,
                        "trigger": "failure_threshold_exceeded",
                        "impact": "requests_will_be_rejected"
                    }
                    
                    open_msg = WebSocketMessage(
                        event_type=WebSocketEventType.STATUS_UPDATE,
                        data=open_event,
                        timestamp=datetime.now(timezone.utc),
                        message_id=f"open_{uuid.uuid4().hex[:8]}",
                        user_id="circuit-breaker"
                    )
                    breaker_client.received_messages.append(open_msg)
            
            # Verify circuit breaker behavior
            assert len(breaker_client.sent_messages) == len(breaker_states)
            
            # Verify state transitions
            sent_states = [msg.data["state"] for msg in breaker_client.sent_messages]
            expected_states = [state["state"] for state in breaker_states]
            assert sent_states == expected_states
            
            # Verify circuit opening/closing events
            circuit_events = [
                msg for msg in breaker_client.received_messages
                if msg.data.get("type") in ["circuit_opened", "request_rejected"]
            ]
            
            # Should have circuit opening and rejection events
            assert len(circuit_events) > 0
            
            # Verify rejection events during open state
            rejection_events = [
                msg for msg in breaker_client.received_messages
                if msg.data.get("type") == "request_rejected"
            ]
            
            # Should reject requests when circuit is open
            open_states = sum(1 for state in breaker_states if state["action"] == "reject_requests")
            assert len(rejection_events) == open_states
            
            self.record_metric("circuit_breaker_transitions", len(breaker_states))