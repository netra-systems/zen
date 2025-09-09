"""
Integration Test: Frontend-Backend Contract Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure frontend and backend API contracts are synchronized
- Value Impact: Prevents user-facing errors and broken chat functionality
- Strategic Impact: Critical for reliable user experience and business value delivery

CRITICAL: This test is DESIGNED TO FAIL initially to demonstrate API contract mismatches.
These failures provide concrete evidence of schema/endpoint issues before implementing fixes.

This integration test validates that the backend API matches the contracts expected by the frontend.
It tests with real backend services but controlled data to identify mismatches.
"""

import asyncio
import json
import pytest
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from test_framework.base_integration_test import BaseIntegrationTest  
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, get_test_jwt_token
from shared.isolated_environment import get_env

import httpx
import aiohttp


class TestFrontendBackendContractValidation(BaseIntegrationTest):
    """
    Integration test for frontend-backend API contract validation.
    
    CRITICAL: This test uses real backend services to validate actual API responses
    against expected frontend contracts. Tests are designed to fail initially.
    """
    
    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        self.env = get_env()
        self.base_url = "http://localhost:8000"  # Real backend service
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Expected API contracts that frontend expects
        self.frontend_api_contracts = {
            "agent_execution": {
                "endpoint": "/api/agent/v2/execute",
                "method": "POST", 
                "expected_request_schema": {
                    "type": "object",
                    "required": ["type", "message"],
                    "properties": {
                        "type": {"type": "string"},
                        "message": {"type": "string"},
                        "context": {"type": "object"},
                        "thread_id": {"type": "string"}
                    }
                },
                "expected_response_schema": {
                    "type": "object",
                    "required": ["id", "status", "result"],
                    "properties": {
                        "id": {"type": "string"},
                        "status": {"type": "string"},
                        "result": {"type": "object"},
                        "thread_id": {"type": "string"}
                    }
                }
            },
            "thread_messages": {
                "endpoint": "/api/threads/{thread_id}/messages",
                "method": "GET",
                "expected_response_schema": {
                    "type": "object", 
                    "required": ["messages", "total"],
                    "properties": {
                        "messages": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "content", "timestamp", "role"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "content": {"type": "string"},
                                    "timestamp": {"type": "string"},
                                    "role": {"type": "string"}
                                }
                            }
                        },
                        "total": {"type": "integer"}
                    }
                }
            },
            "agent_status": {
                "endpoint": "/api/agents/status",
                "method": "GET",
                "expected_response_schema": {
                    "type": "object",
                    "required": ["agents", "system_status"],
                    "properties": {
                        "agents": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "required": ["available", "status"],
                                "properties": {
                                    "available": {"type": "boolean"},
                                    "status": {"type": "string"},
                                    "last_update": {"type": "string"}
                                }
                            }
                        },
                        "system_status": {"type": "string"}
                    }
                }
            }
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_v2_execute_contract_validation(self, real_services_fixture):
        """
        Test that /api/agent/v2/execute exists and matches frontend contract.
        
        EXPECTED RESULT: This test should FAIL, demonstrating:
        1. Endpoint doesn't exist (404)
        2. Request/response schema mismatch
        3. Missing required fields
        """
        # Get authentication headers
        token = get_test_jwt_token(environment="test")
        headers = self.auth_helper.get_auth_headers(token)
        
        contract = self.frontend_api_contracts["agent_execution"]
        endpoint_url = f"{self.base_url}{contract['endpoint']}"
        
        # Prepare test request matching frontend expectations
        test_request = {
            "type": "triage", 
            "message": "Test message for contract validation",
            "context": {"test": True},
            "thread_id": "test-thread-contract-123"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    endpoint_url, 
                    json=test_request,
                    headers=headers,
                    timeout=10
                ) as response:
                    
                    # CRITICAL: This should FAIL with 404 initially
                    self.assertNotEqual(
                        response.status,
                        404,
                        "EXPECTED FAILURE: /api/agent/v2/execute endpoint missing (404). "
                        "Frontend cannot execute agents without this v2 endpoint."
                    )
                    
                    # If endpoint exists, validate response contract
                    if response.status in [200, 201]:
                        response_data = await response.json()
                        
                        # Validate required response fields
                        required_fields = contract["expected_response_schema"]["required"]
                        missing_fields = [
                            field for field in required_fields 
                            if field not in response_data
                        ]
                        
                        if missing_fields:
                            self.fail(
                                f"RESPONSE CONTRACT MISMATCH: Missing required fields {missing_fields}. "
                                f"Frontend expects: {required_fields}. "
                                f"Backend returned: {list(response_data.keys())}"
                            )
                    
                    else:
                        self.fail(
                            f"ENDPOINT CONTRACT FAILURE: {endpoint_url} returned {response.status}. "
                            f"Frontend expects successful execution (200/201). "
                            f"Response: {await response.text()}"
                        )
                        
            except aiohttp.ClientError as e:
                self.fail(
                    f"CONNECTION FAILURE to {endpoint_url}: {e}. "
                    "Frontend cannot connect to backend agent execution endpoint."
                )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_messages_contract_validation(self, real_services_fixture):
        """
        Test that /api/threads/{thread_id}/messages matches frontend contract.
        
        EXPECTED RESULT: This test should FAIL, demonstrating:
        1. Endpoint doesn't exist (404)
        2. Response schema mismatch
        3. Missing pagination or message format
        """
        token = get_test_jwt_token(environment="test")
        headers = self.auth_helper.get_auth_headers(token)
        
        contract = self.frontend_api_contracts["thread_messages"]
        test_thread_id = "test-thread-messages-123"
        endpoint_url = f"{self.base_url}/api/threads/{test_thread_id}/messages"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    endpoint_url,
                    headers=headers,
                    timeout=10
                ) as response:
                    
                    # CRITICAL: This should FAIL with 404 initially
                    self.assertNotEqual(
                        response.status,
                        404,
                        "EXPECTED FAILURE: /api/threads/{thread_id}/messages endpoint missing (404). "
                        "Frontend cannot retrieve thread messages without this endpoint."
                    )
                    
                    # If endpoint exists, validate response contract
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Validate required response structure
                        required_fields = contract["expected_response_schema"]["required"]
                        missing_fields = [
                            field for field in required_fields
                            if field not in response_data
                        ]
                        
                        if missing_fields:
                            self.fail(
                                f"THREAD MESSAGES CONTRACT MISMATCH: Missing required fields {missing_fields}. "
                                f"Frontend expects: {required_fields}. "
                                f"Backend returned: {list(response_data.keys())}"
                            )
                        
                        # Validate message structure if messages exist
                        if "messages" in response_data and response_data["messages"]:
                            message = response_data["messages"][0]
                            message_required = ["id", "content", "timestamp", "role"]
                            missing_message_fields = [
                                field for field in message_required
                                if field not in message
                            ]
                            
                            if missing_message_fields:
                                self.fail(
                                    f"MESSAGE FORMAT CONTRACT MISMATCH: Missing fields {missing_message_fields}. "
                                    f"Frontend expects message format: {message_required}. "
                                    f"Backend message format: {list(message.keys())}"
                                )
                    
                    else:
                        self.fail(
                            f"THREAD MESSAGES ENDPOINT FAILURE: {endpoint_url} returned {response.status}. "
                            f"Frontend expects successful retrieval (200). "
                            f"Response: {await response.text()}"
                        )
                        
            except aiohttp.ClientError as e:
                self.fail(
                    f"CONNECTION FAILURE to {endpoint_url}: {e}. "
                    "Frontend cannot connect to backend thread messages endpoint."
                )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_status_contract_validation(self, real_services_fixture):
        """
        Test that /api/agents/status matches frontend contract.
        
        EXPECTED RESULT: This test may FAIL, demonstrating:
        1. Missing agent status endpoint
        2. Incorrect status response format
        3. Missing agent availability information
        """
        token = get_test_jwt_token(environment="test")
        headers = self.auth_helper.get_auth_headers(token)
        
        contract = self.frontend_api_contracts["agent_status"]
        endpoint_url = f"{self.base_url}{contract['endpoint']}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    endpoint_url,
                    headers=headers,
                    timeout=10
                ) as response:
                    
                    if response.status == 404:
                        self.fail(
                            "EXPECTED POTENTIAL FAILURE: /api/agents/status endpoint missing (404). "
                            "Frontend cannot check agent availability without this endpoint."
                        )
                    
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Validate agent status contract
                        required_fields = contract["expected_response_schema"]["required"]
                        missing_fields = [
                            field for field in required_fields
                            if field not in response_data
                        ]
                        
                        if missing_fields:
                            self.fail(
                                f"AGENT STATUS CONTRACT MISMATCH: Missing required fields {missing_fields}. "
                                f"Frontend expects: {required_fields}. "
                                f"Backend returned: {list(response_data.keys())}"
                            )
                    
                    else:
                        self.fail(
                            f"AGENT STATUS ENDPOINT FAILURE: {endpoint_url} returned {response.status}. "
                            f"Frontend expects agent status (200). "
                            f"Response: {await response.text()}"
                        )
                        
            except aiohttp.ClientError as e:
                # This may be expected if endpoint is missing
                self.fail(
                    f"CONNECTION FAILURE to {endpoint_url}: {e}. "
                    "Frontend cannot connect to backend agent status endpoint."
                )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_comprehensive_api_contract_validation(self, real_services_fixture):
        """
        Comprehensive validation of all frontend-backend API contracts.
        
        EXPECTED RESULT: This test should FAIL with multiple contract violations,
        providing a complete picture of API mismatches between frontend and backend.
        """
        token = get_test_jwt_token(environment="test")
        headers = self.auth_helper.get_auth_headers(token)
        
        contract_violations = []
        successful_contracts = []
        
        async with aiohttp.ClientSession() as session:
            for contract_name, contract in self.frontend_api_contracts.items():
                endpoint = contract["endpoint"]
                method = contract["method"]
                
                # Replace placeholders for testing
                test_endpoint = endpoint.replace("{thread_id}", "test-thread-123")
                endpoint_url = f"{self.base_url}{test_endpoint}"
                
                try:
                    if method == "GET":
                        async with session.get(endpoint_url, headers=headers, timeout=10) as response:
                            result = await self._validate_contract_response(contract_name, contract, response)
                    elif method == "POST":
                        test_data = self._generate_test_request_data(contract_name)
                        async with session.post(endpoint_url, json=test_data, headers=headers, timeout=10) as response:
                            result = await self._validate_contract_response(contract_name, contract, response)
                    
                    if result["success"]:
                        successful_contracts.append(contract_name)
                    else:
                        contract_violations.append(f"{contract_name}: {result['error']}")
                        
                except Exception as e:
                    contract_violations.append(f"{contract_name}: Connection error - {e}")
        
        # CRITICAL: This should FAIL initially, showing all contract violations
        if contract_violations:
            failure_message = (
                "COMPREHENSIVE API CONTRACT VALIDATION FAILURE:\n"
                f"Contract violations ({len(contract_violations)}):\n"
                + "\n".join(f"  ❌ {violation}" for violation in contract_violations)
            )
            
            if successful_contracts:
                failure_message += (
                    f"\n\nWorking contracts ({len(successful_contracts)}):\n"
                    + "\n".join(f"  ✅ {contract}" for contract in successful_contracts)
                )
            
            failure_message += (
                "\n\nThis demonstrates critical frontend-backend API contract mismatches. "
                "The frontend expects these API contracts but the backend doesn't provide them correctly."
            )
            
            self.fail(failure_message)
    
    async def _validate_contract_response(self, contract_name: str, contract: Dict[str, Any], response) -> Dict[str, Any]:
        """Validate response against expected contract."""
        if response.status == 404:
            return {
                "success": False,
                "error": f"Endpoint {contract['endpoint']} missing (404)"
            }
        
        if response.status not in [200, 201]:
            return {
                "success": False,
                "error": f"Unexpected status {response.status}"
            }
        
        try:
            response_data = await response.json()
            expected_schema = contract.get("expected_response_schema", {})
            required_fields = expected_schema.get("required", [])
            
            missing_fields = [
                field for field in required_fields
                if field not in response_data
            ]
            
            if missing_fields:
                return {
                    "success": False,
                    "error": f"Missing required fields: {missing_fields}"
                }
            
            return {"success": True, "error": None}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Response parsing error: {e}"
            }
    
    def _generate_test_request_data(self, contract_name: str) -> Dict[str, Any]:
        """Generate test request data for contract validation."""
        if contract_name == "agent_execution":
            return {
                "type": "triage",
                "message": "Contract validation test message",
                "context": {"test": True, "contract_validation": True},
                "thread_id": "test-thread-contract-validation"
            }
        
        return {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])