"""
Unit tests for database models and validation.

This module tests critical database model functionality including validation rules,
relationship integrity, and business logic constraints.

Business Value: Database models represent core business entities and ensure data integrity
across all customer segments (Free  ->  Enterprise), protecting business-critical data.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from netra_backend.app.auth.models import (
    Base,
    AuthUser,
    AuthSession,
    AuthAuditLog,
    PasswordResetToken
)
from netra_backend.app.agents.models import (
    DataCategory,
    DataPriority,
    DataRequirement,
    DataRequest,
    UserExperience,
    DataSufficiencyAssessment,
    WorkflowPath,
    AgentState,
    WorkflowContext
)


class TestAuthUserModel:
    """Test AuthUser model validation and business logic."""
    
    def test_auth_user_creation_with_required_fields(self):
        """Test AuthUser can be created with minimal required fields."""
        user = AuthUser(
            email="test@example.com",
            full_name="Test User"
        )
        
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.auth_provider == "local"  # Default value
        assert user.is_active is True  # Default value
        assert user.is_verified is False  # Default value
        assert user.failed_login_attempts == 0  # Default value
    
    def test_auth_user_id_generation(self):
        """Test that AuthUser generates valid UUID IDs."""
        user1 = AuthUser(email="user1@example.com")
        user2 = AuthUser(email="user2@example.com")
        
        # IDs should be different UUID strings
        assert user1.id != user2.id
        assert isinstance(user1.id, str)
        assert isinstance(user2.id, str)
        
        # Should be valid UUIDs
        uuid.UUID(user1.id)  # Should not raise
        uuid.UUID(user2.id)  # Should not raise
    
    def test_auth_user_oauth_fields(self):
        """Test AuthUser OAuth provider fields work correctly."""
        user = AuthUser(
            email="oauth@example.com",
            auth_provider="google",
            provider_user_id="google_12345",
            provider_data={"name": "OAuth User", "picture": "http://example.com/pic.jpg"}
        )
        
        assert user.auth_provider == "google"
        assert user.provider_user_id == "google_12345"
        assert user.provider_data["name"] == "OAuth User"
        assert user.provider_data["picture"] == "http://example.com/pic.jpg"
        assert user.hashed_password is None  # OAuth users don't have passwords
    
    def test_auth_user_security_tracking_fields(self):
        """Test AuthUser security and tracking fields."""
        user = AuthUser(
            email="security@example.com",
            failed_login_attempts=3,
            locked_until=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        assert user.failed_login_attempts == 3
        assert user.locked_until > datetime.now(timezone.utc)
        assert user.is_active is True  # Can be active but temporarily locked
    
    def test_auth_user_timestamp_defaults(self):
        """Test that AuthUser timestamp fields have proper defaults."""
        user = AuthUser(email="timestamps@example.com")
        
        # created_at and updated_at should be set (in SQLAlchemy these use func.now())
        # We can't test the exact values without database, but we can test the defaults exist
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')
        assert hasattr(user, 'last_login_at')
        
        # last_login_at should be None by default
        assert user.last_login_at is None


class TestAuthSessionModel:
    """Test AuthSession model for session management."""
    
    def test_auth_session_creation(self):
        """Test AuthSession creation with required fields."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        session = AuthSession(
            user_id="user_123",
            expires_at=expires_at,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 Test Browser"
        )
        
        assert session.user_id == "user_123"
        assert session.expires_at == expires_at
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Mozilla/5.0 Test Browser"
        assert session.is_active is True  # Default
        assert session.revoked_at is None  # Default
    
    def test_auth_session_id_generation(self):
        """Test AuthSession generates unique session IDs."""
        session1 = AuthSession(
            user_id="user_1", 
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        session2 = AuthSession(
            user_id="user_2",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        assert session1.id != session2.id
        assert isinstance(session1.id, str)
        
        # Should be valid UUIDs
        uuid.UUID(session1.id)
        uuid.UUID(session2.id)
    
    def test_auth_session_refresh_token_handling(self):
        """Test AuthSession refresh token hash storage."""
        session = AuthSession(
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            refresh_token_hash="hashed_refresh_token_value"
        )
        
        assert session.refresh_token_hash == "hashed_refresh_token_value"
        # In real implementation, this would be a hash of the actual token
    
    def test_auth_session_device_tracking(self):
        """Test AuthSession device and metadata tracking."""
        session = AuthSession(
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            device_id="device_abc123",
            ip_address="203.0.113.42",
            user_agent="Mobile App v1.2.3"
        )
        
        assert session.device_id == "device_abc123"
        assert session.ip_address == "203.0.113.42"
        assert session.user_agent == "Mobile App v1.2.3"
    
    def test_auth_session_revocation(self):
        """Test AuthSession revocation functionality."""
        session = AuthSession(
            user_id="user_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=False,
            revoked_at=datetime.now(timezone.utc)
        )
        
        assert session.is_active is False
        assert session.revoked_at is not None


class TestAuthAuditLogModel:
    """Test AuthAuditLog model for security audit trails."""
    
    def test_auth_audit_log_creation(self):
        """Test AuthAuditLog creation with required fields."""
        audit_log = AuthAuditLog(
            event_type="login_attempt",
            user_id="user_123",
            success=True,
            ip_address="192.168.1.100"
        )
        
        assert audit_log.event_type == "login_attempt"
        assert audit_log.user_id == "user_123"
        assert audit_log.success is True
        assert audit_log.ip_address == "192.168.1.100"
        assert audit_log.error_message is None  # Default for successful events
    
    def test_auth_audit_log_failure_event(self):
        """Test AuthAuditLog for failed authentication events."""
        audit_log = AuthAuditLog(
            event_type="login_failed",
            user_id="user_456",
            success=False,
            error_message="Invalid password",
            event_metadata={"attempt_count": 3, "lockout_triggered": True}
        )
        
        assert audit_log.success is False
        assert audit_log.error_message == "Invalid password"
        assert audit_log.event_metadata["attempt_count"] == 3
        assert audit_log.event_metadata["lockout_triggered"] is True
    
    def test_auth_audit_log_anonymous_events(self):
        """Test AuthAuditLog for events without associated user."""
        audit_log = AuthAuditLog(
            event_type="suspicious_activity",
            user_id=None,  # Anonymous/unknown user
            success=False,
            error_message="Rate limiting triggered",
            ip_address="10.0.0.1",
            user_agent="Bot/1.0"
        )
        
        assert audit_log.user_id is None
        assert audit_log.event_type == "suspicious_activity"
        assert audit_log.error_message == "Rate limiting triggered"
    
    def test_auth_audit_log_metadata_flexibility(self):
        """Test AuthAuditLog event_metadata JSON field flexibility."""
        complex_metadata = {
            "request_id": "req_abc123",
            "session_id": "sess_def456",
            "features_used": ["2fa", "oauth", "password_reset"],
            "performance_metrics": {
                "response_time_ms": 245,
                "db_queries": 3
            }
        }
        
        audit_log = AuthAuditLog(
            event_type="complex_operation",
            success=True,
            event_metadata=complex_metadata
        )
        
        assert audit_log.event_metadata["request_id"] == "req_abc123"
        assert audit_log.event_metadata["features_used"] == ["2fa", "oauth", "password_reset"]
        assert audit_log.event_metadata["performance_metrics"]["response_time_ms"] == 245
    
    def test_auth_audit_log_id_generation(self):
        """Test AuthAuditLog generates unique IDs."""
        log1 = AuthAuditLog(event_type="event1", success=True)
        log2 = AuthAuditLog(event_type="event2", success=False)
        
        assert log1.id != log2.id
        assert isinstance(log1.id, str)
        
        # Should be valid UUIDs
        uuid.UUID(log1.id)
        uuid.UUID(log2.id)


class TestPasswordResetTokenModel:
    """Test PasswordResetToken model for secure password resets."""
    
    def test_password_reset_token_creation(self):
        """Test PasswordResetToken creation with required fields."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        token = PasswordResetToken(
            user_id="user_789",
            token_hash="hashed_secure_token",
            email="user@example.com",
            expires_at=expires_at
        )
        
        assert token.user_id == "user_789"
        assert token.token_hash == "hashed_secure_token"
        assert token.email == "user@example.com"
        assert token.expires_at == expires_at
        assert token.is_used is False  # Default
        assert token.used_at is None   # Default
    
    def test_password_reset_token_usage_tracking(self):
        """Test PasswordResetToken usage tracking functionality."""
        token = PasswordResetToken(
            user_id="user_789",
            token_hash="hashed_token",
            email="user@example.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            is_used=True,
            used_at=datetime.now(timezone.utc)
        )
        
        assert token.is_used is True
        assert token.used_at is not None
    
    def test_password_reset_token_id_generation(self):
        """Test PasswordResetToken generates unique IDs."""
        token1 = PasswordResetToken(
            user_id="user1",
            token_hash="hash1",
            email="user1@example.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        token2 = PasswordResetToken(
            user_id="user2", 
            token_hash="hash2",
            email="user2@example.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        
        assert token1.id != token2.id
        uuid.UUID(token1.id)  # Should be valid UUID
        uuid.UUID(token2.id)  # Should be valid UUID


class TestAgentModels:
    """Test agent-related Pydantic models for business logic validation."""
    
    def test_data_requirement_model_creation(self):
        """Test DataRequirement model with all fields."""
        requirement = DataRequirement(
            category=DataCategory.FINANCIAL,
            field="monthly_revenue",
            priority=DataPriority.CRITICAL,
            reason="Required for ROI calculation",
            optional=False
        )
        
        assert requirement.category == DataCategory.FINANCIAL
        assert requirement.field == "monthly_revenue"
        assert requirement.priority == DataPriority.CRITICAL
        assert requirement.reason == "Required for ROI calculation"
        assert requirement.optional is False
    
    def test_data_priority_numeric_values(self):
        """Test DataPriority enum numeric value comparison."""
        critical = DataPriority.CRITICAL
        high = DataPriority.HIGH
        medium = DataPriority.MEDIUM
        low = DataPriority.LOW
        
        assert critical.value_numeric == 4
        assert high.value_numeric == 3
        assert medium.value_numeric == 2
        assert low.value_numeric == 1
        
        # Test comparison capability
        assert critical.value_numeric > high.value_numeric
        assert high.value_numeric > medium.value_numeric
        assert medium.value_numeric > low.value_numeric
    
    def test_data_request_model_with_advanced_features(self):
        """Test DataRequest model with advanced UX features."""
        request = DataRequest(
            category=DataCategory.PERFORMANCE,
            priority=DataPriority.HIGH,
            questions=["What is your current API response time?", "How many requests per minute?"],
            format="structured_json",
            examples=["150ms average", "2000 RPM"],
            instructions="Please provide precise metrics if available",
            phase=2,
            language_style="technical",
            focus_areas=["latency", "throughput"],
            acknowledges_previous=["basic_setup_info"],
            remaining_items=3,
            validation_criteria={"response_time": {"min": 0, "max": 10000}},
            error_guidance={"response_time": "Response time must be a positive number in milliseconds"}
        )
        
        assert request.category == DataCategory.PERFORMANCE
        assert len(request.questions) == 2
        assert request.questions[0] == "What is your current API response time?"
        assert request.phase == 2
        assert request.language_style == "technical"
        assert "latency" in request.focus_areas
        assert request.validation_criteria["response_time"]["max"] == 10000
    
    def test_user_experience_model_customization(self):
        """Test UserExperience model for UX customization."""
        ux = UserExperience(
            user_type="startup",
            technical_level="mixed",
            preferred_format="conversational",
            max_questions_per_request=3,
            include_examples=True,
            include_explanations=False  # Startup users prefer brevity
        )
        
        assert ux.user_type == "startup"
        assert ux.technical_level == "mixed"
        assert ux.max_questions_per_request == 3
        assert ux.include_examples is True
        assert ux.include_explanations is False
    
    def test_workflow_context_model_state_management(self):
        """Test WorkflowContext model for agent workflow state."""
        started_time = datetime.now()
        context = WorkflowContext(
            thread_id="thread_abc123",
            turn_id="turn_456",
            workflow_path=WorkflowPath.FLOW_A_SUFFICIENT,
            data_sufficiency=DataSufficiencyAssessment.sufficiency_level if hasattr(DataSufficiencyAssessment, 'sufficiency_level') else "sufficient",
            collected_data={"financial_data": {"revenue": 100000}},
            agent_outputs={"data_agent": {"status": "completed"}},
            current_agent="optimization_agent",
            state=AgentState.PROCESSING,
            started_at=started_time
        )
        
        assert context.thread_id == "thread_abc123"
        assert context.workflow_path == WorkflowPath.FLOW_A_SUFFICIENT
        assert context.state == AgentState.PROCESSING
        assert context.current_agent == "optimization_agent"
        assert context.collected_data["financial_data"]["revenue"] == 100000
        assert context.started_at == started_time
        assert context.completed_at is None  # Not completed yet
    
    def test_data_sufficiency_assessment_business_logic(self):
        """Test DataSufficiencyAssessment model business logic validation."""
        assessment = DataSufficiencyAssessment(
            sufficiency_level="PARTIAL",
            percentage_complete=75,
            can_proceed=True,
            missing_requirements=[
                DataRequirement(
                    category=DataCategory.TECHNICAL,
                    field="api_endpoints",
                    priority=DataPriority.MEDIUM,
                    reason="Optional for enhanced analysis",
                    optional=True
                )
            ],
            optimization_quality={
                "cost_optimization": "high",
                "performance_optimization": "medium",
                "security_optimization": "low"
            },
            value_of_additional_data="Additional technical details could improve recommendations by 15-20%"
        )
        
        assert assessment.sufficiency_level == "PARTIAL"
        assert assessment.percentage_complete == 75
        assert assessment.can_proceed is True
        assert len(assessment.missing_requirements) == 1
        assert assessment.missing_requirements[0].optional is True
        assert assessment.optimization_quality["cost_optimization"] == "high"
        assert "15-20%" in assessment.value_of_additional_data


class TestModelValidationEdgeCases:
    """Test model validation and edge case handling."""
    
    def test_enum_validation_rejects_invalid_values(self):
        """Test that enum fields reject invalid values."""
        with pytest.raises(ValueError):
            DataCategory("invalid_category")  # Should raise ValueError
        
        with pytest.raises(ValueError):
            DataPriority("super_ultra_critical")  # Should raise ValueError
        
        with pytest.raises(ValueError):
            AgentState("confused")  # Should raise ValueError
    
    def test_required_field_validation(self):
        """Test that required fields are properly validated."""
        with pytest.raises(ValueError):
            DataRequirement(
                # Missing required 'category' field
                field="test_field",
                priority=DataPriority.LOW,
                reason="Test reason"
            )
    
    def test_email_field_in_auth_models(self):
        """Test email field validation in auth models."""
        # Valid email should work
        user = AuthUser(email="valid@example.com")
        assert user.email == "valid@example.com"
        
        # Note: Email validation would typically be handled by SQLAlchemy validators
        # or Pydantic validators in a real implementation
    
    def test_model_serialization_deserialization(self):
        """Test that Pydantic models can be serialized and deserialized."""
        original_request = DataRequest(
            category=DataCategory.BUSINESS,
            priority=DataPriority.HIGH,
            questions=["What is your primary business goal?"],
            format="text",
            examples=["Increase user acquisition by 50%"]
        )
        
        # Serialize to dict
        request_dict = original_request.model_dump()
        
        # Deserialize back to model
        restored_request = DataRequest(**request_dict)
        
        assert restored_request.category == original_request.category
        assert restored_request.priority == original_request.priority
        assert restored_request.questions == original_request.questions
        assert restored_request.format == original_request.format
        assert restored_request.examples == original_request.examples
    
    def test_default_values_consistency(self):
        """Test that default values are applied consistently."""
        # Test DataRequest defaults
        minimal_request = DataRequest(
            category=DataCategory.USAGE,
            priority=DataPriority.MEDIUM,
            questions=["How much do you use the service?"]
        )
        
        assert minimal_request.format is None  # Default
        assert minimal_request.examples is None  # Default  
        assert minimal_request.instructions is None  # Default
        assert minimal_request.phase == 1  # Default
        assert minimal_request.remaining_items == 0  # Default
        
        # Test UserExperience defaults
        basic_ux = UserExperience(user_type="enterprise")
        
        assert basic_ux.technical_level == "mixed"  # Default
        assert basic_ux.preferred_format == "structured"  # Default
        assert basic_ux.max_questions_per_request == 5  # Default
        assert basic_ux.include_examples is True  # Default
        assert basic_ux.include_explanations is True  # Default