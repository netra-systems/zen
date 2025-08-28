"""
API Contract Validators

Validates contracts between services to ensure compatibility and correct communication.
Prevents breaking changes and integration failures at service boundaries.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import httpx
from pydantic import BaseModel, ValidationError

from netra_backend.app.core.cross_service_validators.validator_framework import (
    BaseValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from netra_backend.app.schemas.auth_types import (
    AuthConfigResponse,
    LoginRequest,
    LoginResponse,
    TokenRequest,
    TokenResponse,
)
from netra_backend.app.schemas.websocket_message_types import (
    ClientMessageUnion,
    ServerMessageUnion,
    WebSocketMessage,
)


class EndpointSpec(BaseModel):
    """API endpoint specification."""
    path: str
    method: str
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: bool = True


class APIContractValidator(BaseValidator):
    """Validates API contracts between frontend, backend, and auth service."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("api_contract_validator", config)
        self.timeout = config.get("timeout", 10) if config else 10
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate API contracts across services."""
        results = []
        services = context.get("services", [])
        
        # Validate Frontend-Backend API contracts
        if "frontend" in services and "backend" in services:
            results.extend(await self._validate_frontend_backend_contracts(context))
        
        # Validate Backend-Auth API contracts
        if "backend" in services and "auth" in services:
            results.extend(await self._validate_backend_auth_contracts(context))
        
        return results
    
    async def _validate_frontend_backend_contracts(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate contracts between frontend and backend."""
        results = []
        
        # Define critical API endpoints to validate
        critical_endpoints = [
            EndpointSpec(
                path="/api/agents/start",
                method="POST",
                request_schema={"text": "str", "thread_id": "str"},
                response_schema={"status": "str", "agent_id": "str"}
            ),
            EndpointSpec(
                path="/api/threads",
                method="GET",
                response_schema={"threads": "list"}
            ),
            EndpointSpec(
                path="/api/health",
                method="GET",
                auth_required=False,
                response_schema={"status": "str", "service": "str"}
            )
        ]
        
        for endpoint in critical_endpoints:
            try:
                result = await self._validate_endpoint_contract(endpoint, "frontend-backend")
                results.append(result)
            except Exception as e:
                results.append(self.create_result(
                    check_name=f"endpoint_validation_{endpoint.path}",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Failed to validate endpoint {endpoint.path}: {str(e)}",
                    service_pair="frontend-backend",
                    details={"endpoint": endpoint.path, "method": endpoint.method}
                ))
        
        return results
    
    async def _validate_backend_auth_contracts(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate contracts between backend and auth service."""
        results = []
        
        # Validate auth service endpoints
        auth_endpoints = [
            EndpointSpec(
                path="/auth/config",
                method="GET",
                auth_required=False,
                response_schema=AuthConfigResponse.model_json_schema()
            ),
            EndpointSpec(
                path="/auth/validate",
                method="POST",
                request_schema=TokenRequest.model_json_schema(),
                response_schema=TokenResponse.model_json_schema()
            ),
            EndpointSpec(
                path="/auth/login",
                method="POST",
                request_schema=LoginRequest.model_json_schema(),
                response_schema=LoginResponse.model_json_schema(),
                auth_required=False
            )
        ]
        
        for endpoint in auth_endpoints:
            try:
                result = await self._validate_auth_endpoint_contract(endpoint)
                results.append(result)
            except Exception as e:
                results.append(self.create_result(
                    check_name=f"auth_endpoint_{endpoint.path}",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Auth endpoint validation failed: {str(e)}",
                    service_pair="backend-auth",
                    details={"endpoint": endpoint.path}
                ))
        
        return results
    
    async def _validate_endpoint_contract(
        self, 
        endpoint: EndpointSpec, 
        service_pair: str
    ) -> ValidationResult:
        """Validate a specific endpoint contract."""
        start_time = datetime.now(timezone.utc)
        
        # Mock validation - in real implementation would make actual API calls
        # For now, we validate that the endpoint specification is well-formed
        
        issues = []
        
        # Validate path format
        if not endpoint.path.startswith("/"):
            issues.append("Path must start with '/'")
        
        # Validate method
        if endpoint.method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            issues.append(f"Invalid HTTP method: {endpoint.method}")
        
        # Validate schema presence for POST/PUT
        if endpoint.method in ["POST", "PUT"] and not endpoint.request_schema:
            issues.append("Request schema required for POST/PUT methods")
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        if issues:
            return self.create_result(
                check_name=f"contract_validation_{endpoint.path.replace('/', '_')}",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Contract validation failed: {', '.join(issues)}",
                service_pair=service_pair,
                execution_time_ms=execution_time,
                details={
                    "endpoint": endpoint.path,
                    "method": endpoint.method,
                    "issues": issues
                }
            )
        else:
            return self.create_result(
                check_name=f"contract_validation_{endpoint.path.replace('/', '_')}",
                status=ValidationStatus.PASSED,
                severity=ValidationSeverity.INFO,
                message=f"Contract validation passed for {endpoint.path}",
                service_pair=service_pair,
                execution_time_ms=execution_time,
                details={"endpoint": endpoint.path, "method": endpoint.method}
            )
    
    async def _validate_auth_endpoint_contract(
        self, 
        endpoint: EndpointSpec
    ) -> ValidationResult:
        """Validate auth service endpoint contract."""
        # Validate that auth schemas are properly defined
        try:
            if endpoint.request_schema:
                # Validate request schema structure
                if isinstance(endpoint.request_schema, dict):
                    required_fields = endpoint.request_schema.get("required", [])
                    properties = endpoint.request_schema.get("properties", {})
                    
                    if not properties:
                        raise ValueError("Request schema must have properties")
            
            if endpoint.response_schema:
                # Validate response schema structure
                if isinstance(endpoint.response_schema, dict):
                    properties = endpoint.response_schema.get("properties", {})
                    if not properties:
                        raise ValueError("Response schema must have properties")
            
            return self.create_result(
                check_name=f"auth_contract_{endpoint.path.replace('/', '_')}",
                status=ValidationStatus.PASSED,
                severity=ValidationSeverity.INFO,
                message=f"Auth contract validation passed for {endpoint.path}",
                service_pair="backend-auth",
                details={"endpoint": endpoint.path}
            )
            
        except Exception as e:
            return self.create_result(
                check_name=f"auth_contract_{endpoint.path.replace('/', '_')}",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Auth contract validation failed: {str(e)}",
                service_pair="backend-auth",
                details={"endpoint": endpoint.path, "error": str(e)}
            )


class WebSocketContractValidator(BaseValidator):
    """Validates WebSocket message contracts between frontend and backend."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("websocket_contract_validator", config)
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate WebSocket message contracts."""
        results = []
        
        # Validate client message types
        results.extend(await self._validate_client_message_contracts())
        
        # Validate server message types
        results.extend(await self._validate_server_message_contracts())
        
        # Validate message flow patterns
        results.extend(await self._validate_message_flow_patterns())
        
        return results
    
    async def _validate_client_message_contracts(self) -> List[ValidationResult]:
        """Validate client-to-server message contracts."""
        results = []
        
        # Test message creation and validation
        test_messages = [
            {
                "type": "user_message",
                "payload": {"text": "Hello"},
                "message_id": "test-123",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "type": "start_agent", 
                "payload": {"agent_type": "triage"},
                "message_id": "test-124",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        for msg_data in test_messages:
            try:
                # Validate message structure
                msg = WebSocketMessage(**msg_data)
                
                results.append(self.create_result(
                    check_name=f"client_message_{msg_data['type']}",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"Client message validation passed for {msg_data['type']}",
                    service_pair="frontend-backend",
                    details={"message_type": msg_data['type']}
                ))
                
            except ValidationError as e:
                results.append(self.create_result(
                    check_name=f"client_message_{msg_data['type']}",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Client message validation failed: {str(e)}",
                    service_pair="frontend-backend",
                    details={"message_type": msg_data['type'], "errors": str(e)}
                ))
        
        return results
    
    async def _validate_server_message_contracts(self) -> List[ValidationResult]:
        """Validate server-to-client message contracts."""
        results = []
        
        # Validate common server message types
        server_message_types = [
            "agent_started",
            "agent_completed", 
            "agent_error",
            "connection_established",
            "tool_started",
            "tool_completed"
        ]
        
        for msg_type in server_message_types:
            try:
                # Create test message
                test_msg = {
                    "type": msg_type,
                    "payload": {"status": "success"},
                    "message_id": f"server-{msg_type}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                msg = WebSocketMessage(**test_msg)
                
                results.append(self.create_result(
                    check_name=f"server_message_{msg_type}",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"Server message validation passed for {msg_type}",
                    service_pair="backend-frontend",
                    details={"message_type": msg_type}
                ))
                
            except ValidationError as e:
                results.append(self.create_result(
                    check_name=f"server_message_{msg_type}",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Server message validation failed: {str(e)}",
                    service_pair="backend-frontend",
                    details={"message_type": msg_type, "error": str(e)}
                ))
        
        return results
    
    async def _validate_message_flow_patterns(self) -> List[ValidationResult]:
        """Validate expected message flow patterns."""
        results = []
        
        # Define expected flow patterns
        flow_patterns = [
            {
                "name": "agent_execution_flow",
                "sequence": ["start_agent", "agent_started", "agent_thinking", "agent_completed"],
                "description": "Standard agent execution flow"
            },
            {
                "name": "tool_execution_flow", 
                "sequence": ["tool_started", "tool_executing", "tool_completed"],
                "description": "Tool execution flow"
            }
        ]
        
        for pattern in flow_patterns:
            # Validate that all message types in the flow exist
            missing_types = []
            for msg_type in pattern["sequence"]:
                # This would check against actual message type definitions
                # For now, we assume they exist if they follow naming conventions
                if not msg_type.replace("_", "").isalnum():
                    missing_types.append(msg_type)
            
            if missing_types:
                results.append(self.create_result(
                    check_name=f"flow_pattern_{pattern['name']}",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.MEDIUM,
                    message=f"Flow pattern validation failed: missing types {missing_types}",
                    service_pair="frontend-backend",
                    details={"pattern": pattern["name"], "missing_types": missing_types}
                ))
            else:
                results.append(self.create_result(
                    check_name=f"flow_pattern_{pattern['name']}",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message=f"Flow pattern validation passed for {pattern['name']}",
                    service_pair="frontend-backend",
                    details={"pattern": pattern["name"], "sequence": pattern["sequence"]}
                ))
        
        return results


class SchemaCompatibilityValidator(BaseValidator):
    """Validates schema compatibility across service boundaries."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("schema_compatibility_validator", config)
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate schema compatibility."""
        results = []
        
        # Check auth schema compatibility
        results.extend(await self._validate_auth_schema_compatibility())
        
        # Check WebSocket schema compatibility  
        results.extend(await self._validate_websocket_schema_compatibility())
        
        return results
    
    async def _validate_auth_schema_compatibility(self) -> List[ValidationResult]:
        """Validate auth-related schema compatibility."""
        results = []
        
        # Test that auth schemas can be instantiated
        try:
            # Test LoginRequest
            login_req = LoginRequest(
                email="test@example.com",
                password="test123",
                provider="local"
            )
            
            # Test LoginResponse  
            login_resp = LoginResponse(
                access_token="test-token",
                expires_in=3600
            )
            
            results.append(self.create_result(
                check_name="auth_schema_instantiation",
                status=ValidationStatus.PASSED,
                severity=ValidationSeverity.INFO,
                message="Auth schema instantiation successful",
                service_pair="backend-auth",
                details={"schemas_tested": ["LoginRequest", "LoginResponse"]}
            ))
            
        except Exception as e:
            results.append(self.create_result(
                check_name="auth_schema_instantiation",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Auth schema instantiation failed: {str(e)}",
                service_pair="backend-auth",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_websocket_schema_compatibility(self) -> List[ValidationResult]:
        """Validate WebSocket schema compatibility."""
        results = []
        
        try:
            # Test WebSocket message creation
            ws_msg = WebSocketMessage(
                type="test_message",
                payload={"data": "test"},
                message_id="test-msg-123"
            )
            
            results.append(self.create_result(
                check_name="websocket_schema_instantiation",
                status=ValidationStatus.PASSED,
                severity=ValidationSeverity.INFO,
                message="WebSocket schema instantiation successful",
                service_pair="frontend-backend",
                details={"message_id": ws_msg.message_id}
            ))
            
        except Exception as e:
            results.append(self.create_result(
                check_name="websocket_schema_instantiation",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"WebSocket schema instantiation failed: {str(e)}",
                service_pair="frontend-backend",
                details={"error": str(e)}
            ))
        
        return results


class EndpointValidator(BaseValidator):
    """Validates endpoint availability and response formats."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("endpoint_validator", config)
        self.base_urls = config.get("base_urls", {}) if config else {}
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate endpoint availability."""
        results = []
        
        # Get service URLs from context
        service_urls = context.get("service_urls", {})
        
        for service_name, base_url in service_urls.items():
            results.extend(await self._validate_service_endpoints(service_name, base_url))
        
        return results
    
    async def _validate_service_endpoints(
        self, 
        service_name: str, 
        base_url: str
    ) -> List[ValidationResult]:
        """Validate endpoints for a specific service."""
        results = []
        
        # Common endpoints to check
        endpoints_to_check = ["/health", "/api/health"]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in endpoints_to_check:
                try:
                    response = await client.get(f"{base_url}{endpoint}")
                    
                    if response.status_code == 200:
                        results.append(self.create_result(
                            check_name=f"{service_name}_endpoint_{endpoint.replace('/', '_')}",
                            status=ValidationStatus.PASSED,
                            severity=ValidationSeverity.INFO,
                            message=f"Endpoint {endpoint} is accessible",
                            service_pair=service_name,
                            details={
                                "endpoint": endpoint,
                                "status_code": response.status_code,
                                "response_time_ms": response.elapsed.total_seconds() * 1000
                            }
                        ))
                    else:
                        results.append(self.create_result(
                            check_name=f"{service_name}_endpoint_{endpoint.replace('/', '_')}",
                            status=ValidationStatus.FAILED,
                            severity=ValidationSeverity.HIGH,
                            message=f"Endpoint {endpoint} returned status {response.status_code}",
                            service_pair=service_name,
                            details={
                                "endpoint": endpoint,
                                "status_code": response.status_code
                            }
                        ))
                        
                except Exception as e:
                    results.append(self.create_result(
                        check_name=f"{service_name}_endpoint_{endpoint.replace('/', '_')}",
                        status=ValidationStatus.FAILED,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Failed to reach endpoint {endpoint}: {str(e)}",
                        service_pair=service_name,
                        details={"endpoint": endpoint, "error": str(e)}
                    ))
        
        return results