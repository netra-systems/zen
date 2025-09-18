"""
Test API validation patterns and error boundaries
Focus on request validation, response serialization, and error handling patterns
"""

import pytest
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, ValidationError, Field
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.core.exceptions_config import ValidationError as ValidationServiceError


class MockAPIRequest(BaseModel):
    """Mock API request model for testing"""
    user_id: str = Field(..., min_length=1, max_length=100)
    data: Dict[str, Any] = Field(default_factory=dict)
    options: Optional[List[str]] = None
    priority: int = Field(default=1, ge=1, le=10)


class MockAPIResponse(BaseModel):
    """Mock API response model for testing"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class APIValidationPatternsTests:
    """Test API validation patterns and error handling"""

    def test_request_validation_success(self):
        """Test successful request validation"""
        valid_data = {
            "user_id": "test_user_123",
            "data": {"key": "value"},
            "options": ["option1", "option2"],
            "priority": 5
        }
        
        request = MockAPIRequest(**valid_data)
        assert request.user_id == "test_user_123"
        assert request.data == {"key": "value"}
        assert request.options == ["option1", "option2"]
        assert request.priority == 5

    def test_request_validation_missing_required_field(self):
        """Test validation error for missing required fields"""
        invalid_data = {
            "data": {"key": "value"},
            "priority": 3
            # Missing user_id
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MockAPIRequest(**invalid_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("user_id",)
        assert "required" in errors[0]["msg"].lower()

    def test_request_validation_field_constraints(self):
        """Test validation of field constraints"""
        # Test empty user_id
        with pytest.raises(ValidationError):
            MockAPIRequest(user_id="", data={})
        
        # Test user_id too long
        with pytest.raises(ValidationError):
            MockAPIRequest(user_id="x" * 101, data={})
        
        # Test priority out of range
        with pytest.raises(ValidationError):
            MockAPIRequest(user_id="valid_user", data={}, priority=15)

    def test_request_validation_with_defaults(self):
        """Test that default values are properly applied"""
        minimal_data = {
            "user_id": "test_user"
        }
        
        request = MockAPIRequest(**minimal_data)
        assert request.user_id == "test_user"
        assert request.data == {}  # Default empty dict
        assert request.options is None  # Optional field
        assert request.priority == 1  # Default value

    def test_response_validation_and_serialization(self):
        """Test response validation and serialization patterns"""
        # Test successful response
        success_response = MockAPIResponse(
            success=True,
            result={"processed": True, "count": 42},
            metadata={"timestamp": "2024-01-01T00:00:00Z"}
        )
        
        response_dict = success_response.model_dump()
        assert response_dict["success"] is True
        assert response_dict["result"]["count"] == 42
        assert response_dict["error"] is None
        
        # Test error response
        error_response = MockAPIResponse(
            success=False,
            error="Validation failed",
            metadata={"error_code": "VALIDATION_ERROR"}
        )
        
        error_dict = error_response.model_dump()
        assert error_dict["success"] is False
        assert error_dict["error"] == "Validation failed"
        assert error_dict["result"] is None

    def test_validation_error_transformation(self):
        """Test transformation of Pydantic validation errors to service errors"""
        def transform_validation_error(data: Dict[str, Any]) -> MockAPIRequest:
            """Transform validation errors to service errors"""
            try:
                return MockAPIRequest(**data)
            except ValidationError as e:
                error_details = []
                for error in e.errors():
                    field = ".".join(str(loc) for loc in error["loc"])
                    message = error["msg"]
                    error_details.append(f"{field}: {message}")
                
                raise ValidationServiceError(
                    f"Request validation failed: {'; '.join(error_details)}"
                )

        # Test successful transformation
        valid_data = {"user_id": "valid_user"}
        result = transform_validation_error(valid_data)
        assert isinstance(result, MockAPIRequest)
        
        # Test validation error transformation
        invalid_data = {"user_id": "", "priority": 15}
        with pytest.raises(ValidationServiceError) as exc_info:
            transform_validation_error(invalid_data)
        
        error_message = str(exc_info.value)
        assert "validation failed" in error_message.lower()
        assert "user_id" in error_message
        assert "priority" in error_message


class APIErrorBoundariesTests:
    """Test API error boundary patterns"""

    @pytest.mark.asyncio
    async def test_service_error_handling_pattern(self):
        """Test service error handling patterns"""
        async def api_endpoint_with_error_boundary(request_data: Dict[str, Any]):
            """Mock API endpoint with error boundary"""
            try:
                # Validate request
                request = MockAPIRequest(**request_data)
                
                # Simulate business logic that might fail
                if request.user_id == "error_user":
                    raise ServiceError("Business logic error")
                
                # Success response
                return MockAPIResponse(
                    success=True,
                    result={"processed": True, "user_id": request.user_id}
                )
            
            except ValidationError as e:
                return MockAPIResponse(
                    success=False,
                    error="Invalid request data",
                    metadata={"validation_errors": [err["msg"] for err in e.errors()]}
                )
            
            except ServiceError as e:
                return MockAPIResponse(
                    success=False,
                    error=str(e),
                    metadata={"error_type": "service_error"}
                )
            
            except Exception as e:
                # Catch-all for unexpected errors
                return MockAPIResponse(
                    success=False,
                    error="Internal server error",
                    metadata={"error_type": "unexpected", "debug_info": str(e)}
                )

        # Test successful request
        result = await api_endpoint_with_error_boundary({"user_id": "valid_user"})
        assert result.success is True
        assert result.result["user_id"] == "valid_user"
        
        # Test validation error
        result = await api_endpoint_with_error_boundary({"user_id": ""})
        assert result.success is False
        assert result.error == "Invalid request data"
        assert "validation_errors" in result.metadata
        
        # Test service error
        result = await api_endpoint_with_error_boundary({"user_id": "error_user"})
        assert result.success is False
        assert "Business logic error" in result.error
        assert result.metadata["error_type"] == "service_error"

    def test_nested_validation_patterns(self):
        """Test validation patterns for nested data structures"""
        class NestedRequest(BaseModel):
            user_id: str
            config: Dict[str, Any]
            
            def validate_config(self):
                """Custom validation for config field"""
                required_keys = ["api_key", "timeout"]
                for key in required_keys:
                    if key not in self.config:
                        raise ValueError(f"Missing required config key: {key}")
                
                if not isinstance(self.config.get("timeout"), (int, float)):
                    raise ValueError("Config timeout must be a number")
                
                if self.config["timeout"] <= 0:
                    raise ValueError("Config timeout must be positive")

        def validate_nested_request(data: Dict[str, Any]) -> NestedRequest:
            """Validate nested request with custom validation"""
            try:
                request = NestedRequest(**data)
                request.validate_config()  # Additional custom validation
                return request
            except (ValidationError, ValueError) as e:
                raise ValidationServiceError(f"Nested validation failed: {str(e)}")

        # Test successful nested validation
        valid_data = {
            "user_id": "test_user",
            "config": {
                "api_key": "secret_key",
                "timeout": 30,
                "optional_param": "value"
            }
        }
        
        result = validate_nested_request(valid_data)
        assert result.user_id == "test_user"
        assert result.config["api_key"] == "secret_key"
        
        # Test missing config key
        invalid_data = {
            "user_id": "test_user",
            "config": {"timeout": 30}  # Missing api_key
        }
        
        with pytest.raises(ValidationServiceError) as exc_info:
            validate_nested_request(invalid_data)
        
        assert "api_key" in str(exc_info.value)

    def test_conditional_validation_patterns(self):
        """Test conditional validation based on request context"""
        class ConditionalRequest(BaseModel):
            user_id: str
            action: str
            target: Optional[str] = None
            admin_key: Optional[str] = None
            
            def validate_conditional_fields(self):
                """Validate fields based on action type"""
                if self.action == "admin_action":
                    if not self.admin_key:
                        raise ValueError("admin_key required for admin actions")
                    if self.admin_key != "secret_admin_key":
                        raise ValueError("Invalid admin key")
                
                if self.action in ["update", "delete"]:
                    if not self.target:
                        raise ValueError(f"target required for {self.action} action")

        def validate_conditional_request(data: Dict[str, Any]) -> ConditionalRequest:
            """Validate request with conditional logic"""
            request = ConditionalRequest(**data)
            request.validate_conditional_fields()
            return request

        # Test normal action (no extra validation)
        normal_request = validate_conditional_request({
            "user_id": "user123",
            "action": "read"
        })
        assert normal_request.action == "read"
        
        # Test admin action with valid key
        admin_request = validate_conditional_request({
            "user_id": "admin_user",
            "action": "admin_action",
            "admin_key": "secret_admin_key"
        })
        assert admin_request.action == "admin_action"
        
        # Test admin action with invalid key
        with pytest.raises(ValueError):
            validate_conditional_request({
                "user_id": "admin_user",
                "action": "admin_action",
                "admin_key": "wrong_key"
            })
        
        # Test update action without target
        with pytest.raises(ValueError):
            validate_conditional_request({
                "user_id": "user123",
                "action": "update"
                # Missing target
            })


class APIResponsePatternsTests:
    """Test API response patterns and serialization"""

    def test_standardized_response_format(self):
        """Test standardized response format patterns"""
        class StandardResponse(BaseModel):
            success: bool
            data: Optional[Any] = None
            error: Optional[str] = None
            pagination: Optional[Dict[str, int]] = None
            metadata: Dict[str, Any] = Field(default_factory=dict)
            
            @classmethod
            def success_response(cls, data: Any = None, pagination: Dict[str, int] = None, **metadata):
                """Create success response"""
                return cls(
                    success=True,
                    data=data,
                    pagination=pagination,
                    metadata=metadata
                )
            
            @classmethod
            def error_response(cls, error: str, **metadata):
                """Create error response"""
                return cls(
                    success=False,
                    error=error,
                    metadata=metadata
                )

        # Test success response creation
        success_resp = StandardResponse.success_response(
            data={"items": [1, 2, 3]},
            pagination={"page": 1, "total": 3},
            request_id="req_123"
        )
        
        assert success_resp.success is True
        assert success_resp.data["items"] == [1, 2, 3]
        assert success_resp.pagination["total"] == 3
        assert success_resp.metadata["request_id"] == "req_123"
        assert success_resp.error is None
        
        # Test error response creation
        error_resp = StandardResponse.error_response(
            error="Resource not found",
            error_code="NOT_FOUND",
            request_id="req_456"
        )
        
        assert error_resp.success is False
        assert error_resp.error == "Resource not found"
        assert error_resp.metadata["error_code"] == "NOT_FOUND"
        assert error_resp.data is None

    def test_response_serialization_edge_cases(self):
        """Test response serialization with edge cases"""
        # Test with None values
        response = MockAPIResponse(
            success=True,
            result=None,
            error=None
        )
        
        serialized = response.model_dump()
        assert "result" in serialized
        assert serialized["result"] is None
        
        # Test with empty collections (fix the dict type constraint)
        response = MockAPIResponse(
            success=True,
            result={},  # Use empty dict instead of empty list
            metadata={}
        )
        
        serialized = response.model_dump()
        assert serialized["result"] == {}
        assert serialized["metadata"] == {}
        
        # Test excluding None values
        response = MockAPIResponse(success=True, result={"key": "value"})
        serialized = response.model_dump(exclude_none=True)
        assert "error" not in serialized
        assert serialized["result"]["key"] == "value"