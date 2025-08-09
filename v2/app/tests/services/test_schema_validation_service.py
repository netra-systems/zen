import pytest
from pydantic import BaseModel, ValidationError
from typing import Optional, List
from app.services.schema_validation_service import SchemaValidationService
from app.schemas.Agent import AgentRequest, AgentResponse
from app.schemas.WebSocket import MessageRequest

class TestUserData(BaseModel):
    id: str
    email: str
    age: Optional[int] = None
    tags: List[str] = []

@pytest.mark.asyncio
class TestSchemaValidationService:
    
    def test_validate_valid_schema(self):
        validator = SchemaValidationService()
        
        valid_data = {
            "id": "user-123",
            "email": "test@example.com",
            "age": 25,
            "tags": ["active", "premium"]
        }
        
        result = validator.validate_data(valid_data, TestUserData)
        assert result.is_valid is True
        assert result.errors == []
        assert result.validated_data.id == "user-123"
    
    def test_validate_invalid_schema(self):
        validator = SchemaValidationService()
        
        invalid_data = {
            "id": "user-123",
            "email": "invalid-email",
            "age": "not-a-number",
            "tags": "not-a-list"
        }
        
        result = validator.validate_data(invalid_data, TestUserData)
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("email" in error for error in result.errors)
    
    def test_validate_partial_data(self):
        validator = SchemaValidationService()
        
        partial_data = {
            "id": "user-123",
            "email": "test@example.com"
        }
        
        result = validator.validate_data(partial_data, TestUserData)
        assert result.is_valid is True
        assert result.validated_data.age is None
        assert result.validated_data.tags == []
    
    def test_validate_agent_request_schema(self):
        validator = SchemaValidationService()
        
        agent_request_data = {
            "message": "Analyze performance metrics",
            "thread_id": "thread-456",
            "user_id": "user-123",
            "metadata": {"priority": "high"}
        }
        
        result = validator.validate_data(agent_request_data, AgentRequest)
        assert result.is_valid is True
        assert result.validated_data.message == "Analyze performance metrics"
    
    def test_validate_websocket_message_schema(self):
        validator = SchemaValidationService()
        
        message_data = {
            "type": "message",
            "content": "Hello AI",
            "thread_id": "thread-789"
        }
        
        result = validator.validate_data(message_data, MessageRequest)
        assert result.is_valid is True
        assert result.validated_data.type == "message"
    
    def test_batch_validation(self):
        validator = SchemaValidationService()
        
        batch_data = [
            {"id": "user-1", "email": "user1@example.com"},
            {"id": "user-2", "email": "user2@example.com"},
            {"id": "user-3", "email": "invalid-email"}
        ]
        
        results = validator.validate_batch(batch_data, TestUserData)
        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is True
        assert results[2].is_valid is False
    
    def test_custom_validation_rules(self):
        validator = SchemaValidationService()
        
        def custom_rule(data):
            if data.get("age") and data["age"] < 18:
                return ["Age must be 18 or older"]
            return []
        
        validator.add_custom_rule("age_check", custom_rule)
        
        young_user_data = {
            "id": "user-123",
            "email": "test@example.com",
            "age": 16
        }
        
        result = validator.validate_with_custom_rules(young_user_data, TestUserData)
        assert result.is_valid is False
        assert any("18 or older" in error for error in result.errors)
    
    def test_schema_transformation(self):
        validator = SchemaValidationService()
        
        raw_data = {
            "user_id": "123",
            "user_email": "test@example.com",
            "user_age": "25"
        }
        
        transformation_map = {
            "user_id": "id",
            "user_email": "email",
            "user_age": "age"
        }
        
        transformed_data = validator.transform_data(raw_data, transformation_map)
        result = validator.validate_data(transformed_data, TestUserData)
        
        assert result.is_valid is True
        assert result.validated_data.id == "123"
        assert result.validated_data.age == 25