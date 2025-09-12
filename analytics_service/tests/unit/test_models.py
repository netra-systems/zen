"""
Analytics Service Models Unit Tests
=================================

Comprehensive unit tests for analytics service data models.
Tests all event type validations, report model serialization, and edge cases.

NO MOCKS POLICY: Tests use real data validation and serialization.

Test Coverage:
- Event model validation for all event types
- Property validation and type checking
- JSON serialization/deserialization
- Edge cases and error conditions
- Required field validation
- Enum value validation
- Data type conversions
"""

import json
import pytest
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID
from shared.isolated_environment import IsolatedEnvironment

# Pydantic imports for model validation
from pydantic import ValidationError, BaseModel
from pydantic.fields import Field
from enum import Enum

# =============================================================================
# MODEL DEFINITIONS (To be moved to actual models module)
# =============================================================================

class MessageType(str, Enum):
    USER_PROMPT = "user_prompt"
    AI_RESPONSE = "ai_response"
    SYSTEM_MESSAGE = "system_message"

class ThreadAction(str, Enum):
    CREATED = "created"
    CONTINUED = "continued"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class FeedbackType(str, Enum):
    NPS = "nps"
    CSAT = "csat"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"

class QuestionType(str, Enum):
    PAIN_PERCEPTION = "pain_perception"
    MAGIC_WAND = "magic_wand"
    SPENDING = "spending"
    PLANNING = "planning"

class MetricType(str, Enum):
    PAGE_LOAD = "page_load"
    API_CALL = "api_call"
    WEBSOCKET = "websocket"
    RENDER = "render"

class UserImpact(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ChatInteractionProperties(BaseModel):
    """Chat interaction event properties"""
    thread_id: str
    message_id: str
    message_type: MessageType
    prompt_text: str = None
    prompt_length: int
    response_length: int = None
    response_time_ms: float = None
    model_used: str = None
    tokens_consumed: int = None
    is_follow_up: bool

class ThreadLifecycleProperties(BaseModel):
    """Thread lifecycle event properties"""
    thread_id: str
    action: ThreadAction
    message_count: int = None
    duration_seconds: float = None

class FeatureUsageProperties(BaseModel):
    """Feature usage event properties"""
    feature_name: str
    action: str
    success: bool
    error_code: str = None
    duration_ms: float = None

class SurveyResponseProperties(BaseModel):
    """Survey response event properties"""
    survey_id: str
    question_id: str
    question_type: QuestionType
    response_value: str = None
    response_scale: int = None
    ai_spend_last_month: float = None
    ai_spend_next_quarter: float = None

class FeedbackSubmissionProperties(BaseModel):
    """Feedback submission event properties"""
    feedback_type: FeedbackType
    score: int = None
    comment: str = None
    context_thread_id: str = None

class PerformanceMetricProperties(BaseModel):
    """Performance metric event properties"""
    metric_type: MetricType
    duration_ms: float
    success: bool
    error_details: str = None

class ErrorTrackingProperties(BaseModel):
    """Error tracking event properties"""
    error_type: str
    error_message: str
    stack_trace: str = None
    user_impact: UserImpact

class EventModel(BaseModel):
    """Base event model for all analytics events"""
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime
    user_id: str
    session_id: str
    event_type: str
    event_category: str
    event_action: str = None
    event_label: str = None
    event_value: float = None
    
    # Event-specific properties as JSON
    properties: str = Field(..., description="JSON string with event-specific data")
    
    # User context
    user_agent: str = None
    ip_address: str = None
    country_code: str = None
    
    # Page context
    page_path: str = None
    page_title: str = None
    referrer: str = None
    
    # Technical metadata
    gtm_container_id: str = None
    environment: str = "production"
    app_version: str = None

class ReportModel(BaseModel):
    """Base report model for analytics reports"""
    report_id: str
    report_type: str
    generated_at: datetime
    user_id: str = None
    parameters: Dict[str, Any]
    data: Dict[str, Any]
    metadata: Dict[str, Any] = {}

class UserActivitySummary(BaseModel):
    """User activity summary report model"""
    user_id: str
    date: datetime
    total_events: int
    chat_interactions: int
    threads_created: int
    feature_interactions: int
    total_tokens_consumed: float
    avg_response_time: float

# =============================================================================
# EVENT MODEL VALIDATION TESTS
# =============================================================================

class TestEventModel:
    """Test suite for EventModel validation"""
    
    def test_valid_chat_interaction_event(self, sample_chat_interaction_event):
        """Test valid chat interaction event validation"""
        event = EventModel(**sample_chat_interaction_event)
        
        assert event.event_type == "chat_interaction"
        assert event.event_category == "User Interaction Events"
        assert event.user_id is not None
        assert event.session_id is not None
        
        # Validate properties can be parsed
        properties = json.loads(event.properties)
        chat_props = ChatInteractionProperties(**properties)
        assert chat_props.message_type in MessageType
        assert chat_props.is_follow_up is not None
    
    def test_valid_survey_response_event(self, sample_survey_response_event):
        """Test valid survey response event validation"""
        event = EventModel(**sample_survey_response_event)
        
        assert event.event_type == "survey_response"
        assert event.event_category == "Survey and Feedback Events"
        
        # Validate properties
        properties = json.loads(event.properties)
        survey_props = SurveyResponseProperties(**properties)
        assert survey_props.question_type in QuestionType
        assert survey_props.response_scale is None or 1 <= survey_props.response_scale <= 10
    
    def test_valid_performance_event(self, sample_performance_event):
        """Test valid performance metric event validation"""
        event = EventModel(**sample_performance_event)
        
        assert event.event_type == "performance_metric"
        assert event.event_category == "Technical Events"
        
        # Validate properties
        properties = json.loads(event.properties)
        perf_props = PerformanceMetricProperties(**properties)
        assert perf_props.metric_type in MetricType
        assert perf_props.duration_ms > 0
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields"""
        with pytest.raises(ValidationError) as exc_info:
            EventModel()
        
        errors = exc_info.value.errors()
        required_fields = ["event_id", "timestamp", "user_id", "session_id", "event_type", "event_category", "properties"]
        
        error_fields = {error["loc"][0] for error in errors}
        for field in required_fields:
            assert field in error_fields, f"Missing required field validation: {field}"
    
    def test_invalid_timestamp_format(self):
        """Test invalid timestamp format validation"""
        invalid_data = {
            "event_id": "test-id",
            "timestamp": "invalid-timestamp",
            "user_id": "test-user",
            "session_id": "test-session",
            "event_type": "test",
            "event_category": "test",
            "properties": "{}"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            EventModel(**invalid_data)
        
        errors = exc_info.value.errors()
        timestamp_errors = [e for e in errors if "timestamp" in str(e["loc"])]
        assert len(timestamp_errors) > 0, "Should validate timestamp format"
    
    def test_invalid_json_properties(self):
        """Test invalid JSON in properties field"""
        invalid_data = {
            "event_id": "test-id",
            "timestamp": datetime.now(timezone.utc),
            "user_id": "test-user",
            "session_id": "test-session",
            "event_type": "test",
            "event_category": "test",
            "properties": "invalid-json-{"
        }
        
        # Model should accept the string but JSON parsing should fail separately
        event = EventModel(**invalid_data)
        with pytest.raises(json.JSONDecodeError):
            json.loads(event.properties)
    
    def test_event_serialization(self, sample_chat_interaction_event):
        """Test event model serialization to JSON"""
        event = EventModel(**sample_chat_interaction_event)
        
        # Test dict serialization
        event_dict = event.model_dump()
        assert isinstance(event_dict, dict)
        assert "event_id" in event_dict
        assert "timestamp" in event_dict
        
        # Test JSON serialization
        json_str = event.model_dump_json()
        assert isinstance(json_str, str)
        
        # Test deserialization
        reconstructed = EventModel.model_validate_json(json_str)
        assert reconstructed.event_id == event.event_id
        assert reconstructed.event_type == event.event_type
    
    def test_event_with_all_optional_fields(self):
        """Test event with all optional fields populated"""
        full_event_data = {
            "event_id": "test-event-full",
            "timestamp": datetime.now(timezone.utc),
            "user_id": "test-user-123",
            "session_id": "test-session-456",
            "event_type": "chat_interaction",
            "event_category": "User Interaction Events",
            "event_action": "message_sent",
            "event_label": "user_prompt",
            "event_value": 150.0,
            "properties": json.dumps({"test": "data"}),
            "user_agent": "Mozilla/5.0 Test",
            "ip_address": "hashed_ip_address",
            "country_code": "US",
            "page_path": "/chat",
            "page_title": "Chat Interface",
            "referrer": "https://netra.ai/dashboard",
            "gtm_container_id": "GTM-TEST123",
            "environment": "test",
            "app_version": "1.0.0-test"
        }
        
        event = EventModel(**full_event_data)
        assert event.event_action == "message_sent"
        assert event.event_value == 150.0
        assert event.country_code == "US"
        assert event.gtm_container_id == "GTM-TEST123"

# =============================================================================
# PROPERTY MODEL VALIDATION TESTS
# =============================================================================

class TestPropertyModels:
    """Test suite for event property models"""
    
    def test_chat_interaction_properties_validation(self):
        """Test chat interaction properties validation"""
        valid_props = {
            "thread_id": "thread-123",
            "message_id": "msg-456",
            "message_type": "user_prompt",
            "prompt_text": "Test prompt",
            "prompt_length": 11,
            "response_time_ms": 1500.5,
            "tokens_consumed": 100,
            "is_follow_up": True
        }
        
        props = ChatInteractionProperties(**valid_props)
        assert props.message_type == MessageType.USER_PROMPT
        assert props.is_follow_up is True
        assert props.tokens_consumed == 100
    
    def test_chat_interaction_invalid_message_type(self):
        """Test invalid message type in chat interaction properties"""
        invalid_props = {
            "thread_id": "thread-123",
            "message_id": "msg-456",
            "message_type": "invalid_type",
            "prompt_length": 11,
            "is_follow_up": True
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ChatInteractionProperties(**invalid_props)
        
        errors = exc_info.value.errors()
        message_type_errors = [e for e in errors if "message_type" in str(e["loc"])]
        assert len(message_type_errors) > 0
    
    def test_survey_response_properties_validation(self):
        """Test survey response properties validation"""
        valid_props = {
            "survey_id": "ai_spend_2025",
            "question_id": "q1",
            "question_type": "pain_perception",
            "response_value": "High costs",
            "response_scale": 8,
            "ai_spend_last_month": 15000.50
        }
        
        props = SurveyResponseProperties(**valid_props)
        assert props.question_type == QuestionType.PAIN_PERCEPTION
        assert props.response_scale == 8
        assert props.ai_spend_last_month == 15000.50
    
    def test_performance_metric_properties_validation(self):
        """Test performance metric properties validation"""
        valid_props = {
            "metric_type": "api_call",
            "duration_ms": 245.7,
            "success": True,
            "error_details": None
        }
        
        props = PerformanceMetricProperties(**valid_props)
        assert props.metric_type == MetricType.API_CALL
        assert props.success is True
        assert props.duration_ms == 245.7
    
    def test_error_tracking_properties_validation(self):
        """Test error tracking properties validation"""
        valid_props = {
            "error_type": "ValidationError",
            "error_message": "Invalid input data",
            "stack_trace": "Traceback...",
            "user_impact": "high"
        }
        
        props = ErrorTrackingProperties(**valid_props)
        assert props.user_impact == UserImpact.HIGH
        assert props.error_type == "ValidationError"

# =============================================================================
# REPORT MODEL TESTS
# =============================================================================

class TestReportModel:
    """Test suite for report models"""
    
    def test_valid_report_model(self):
        """Test valid report model creation"""
        report_data = {
            "report_id": "report-123",
            "report_type": "user_activity",
            "generated_at": datetime.now(timezone.utc),
            "user_id": "user-456",
            "parameters": {"date_range": "last_7_days"},
            "data": {"total_events": 150, "chat_sessions": 25},
            "metadata": {"version": "1.0", "source": "analytics_service"}
        }
        
        report = ReportModel(**report_data)
        assert report.report_type == "user_activity"
        assert report.parameters["date_range"] == "last_7_days"
        assert report.data["total_events"] == 150
        assert report.metadata["version"] == "1.0"
    
    def test_report_serialization(self):
        """Test report model serialization"""
        report_data = {
            "report_id": "report-serialize-test",
            "report_type": "performance_summary",
            "generated_at": datetime.now(timezone.utc),
            "parameters": {"metric_type": "api_response_time"},
            "data": {"avg_response_time": 245.5, "p95_response_time": 500.0}
        }
        
        report = ReportModel(**report_data)
        
        # Test JSON serialization
        json_str = report.model_dump_json()
        assert isinstance(json_str, str)
        
        # Test deserialization
        reconstructed = ReportModel.model_validate_json(json_str)
        assert reconstructed.report_id == report.report_id
        assert reconstructed.data["avg_response_time"] == 245.5
    
    def test_user_activity_summary_model(self):
        """Test user activity summary model"""
        summary_data = {
            "user_id": "user-123",
            "date": datetime.now(timezone.utc),
            "total_events": 50,
            "chat_interactions": 25,
            "threads_created": 5,
            "feature_interactions": 10,
            "total_tokens_consumed": 2500.0,
            "avg_response_time": 1250.5
        }
        
        summary = UserActivitySummary(**summary_data)
        assert summary.user_id == "user-123"
        assert summary.total_events == 50
        assert summary.chat_interactions == 25
        assert summary.avg_response_time == 1250.5

# =============================================================================
# EDGE CASES AND ERROR CONDITIONS
# =============================================================================

class TestEdgeCases:
    """Test suite for edge cases and error conditions"""
    
    def test_empty_properties_json(self):
        """Test event with empty properties JSON"""
        event_data = {
            "event_id": "empty-props-test",
            "timestamp": datetime.now(timezone.utc),
            "user_id": "test-user",
            "session_id": "test-session",
            "event_type": "feature_usage",
            "event_category": "User Interaction Events",
            "properties": "{}"
        }
        
        event = EventModel(**event_data)
        properties = json.loads(event.properties)
        assert properties == {}
    
    def test_unicode_text_handling(self):
        """Test handling of unicode text in event properties"""
        unicode_props = {
            "thread_id": "thread-unicode",
            "message_id": "msg-unicode",
            "message_type": "user_prompt",
            "prompt_text": "[U+00BF]C[U+00F3]mo puedo optimizar los costos de IA? [U+1F916][U+1F4B0]",
            "prompt_length": 42,
            "is_follow_up": False
        }
        
        event_data = {
            "event_id": "unicode-test",
            "timestamp": datetime.now(timezone.utc),
            "user_id": "test-user",
            "session_id": "test-session",
            "event_type": "chat_interaction",
            "event_category": "User Interaction Events",
            "properties": json.dumps(unicode_props, ensure_ascii=False)
        }
        
        event = EventModel(**event_data)
        parsed_props = json.loads(event.properties)
        assert "[U+1F916][U+1F4B0]" in parsed_props["prompt_text"]
    
    def test_large_property_values(self):
        """Test handling of large property values"""
        large_props = {
            "thread_id": "thread-large",
            "message_id": "msg-large",
            "message_type": "user_prompt",
            "prompt_text": "A" * 10000,  # Large prompt text
            "prompt_length": 10000,
            "is_follow_up": False
        }
        
        event_data = {
            "event_id": "large-props-test",
            "timestamp": datetime.now(timezone.utc),
            "user_id": "test-user",
            "session_id": "test-session",
            "event_type": "chat_interaction",
            "event_category": "User Interaction Events",
            "properties": json.dumps(large_props)
        }
        
        event = EventModel(**event_data)
        parsed_props = json.loads(event.properties)
        assert len(parsed_props["prompt_text"]) == 10000
    
    def test_negative_numeric_values(self):
        """Test handling of negative numeric values"""
        event_data = {
            "event_id": "negative-values-test",
            "timestamp": datetime.now(timezone.utc),
            "user_id": "test-user",
            "session_id": "test-session",
            "event_type": "performance_metric",
            "event_category": "Technical Events",
            "event_value": -100.0,  # Negative event value
            "properties": json.dumps({
                "metric_type": "api_call",
                "duration_ms": -50.0,  # This should probably be validated as positive
                "success": False
            })
        }
        
        event = EventModel(**event_data)
        assert event.event_value == -100.0
        
        # The properties validation should catch negative duration
        # but the event model itself doesn't enforce this
        properties = json.loads(event.properties)
        assert properties["duration_ms"] == -50.0
    
    def test_null_optional_fields(self):
        """Test event with explicit null values for optional fields"""
        event_data = {
            "event_id": "null-fields-test",
            "timestamp": datetime.now(timezone.utc),
            "user_id": "test-user",
            "session_id": "test-session",
            "event_type": "chat_interaction",
            "event_category": "User Interaction Events",
            "properties": json.dumps({"test": "data"}),
            "event_action": None,
            "event_label": None,
            "event_value": None,
            "user_agent": None,
            "page_path": None
        }
        
        event = EventModel(**event_data)
        assert event.event_action is None
        assert event.event_label is None
        assert event.event_value is None
    
    def test_boundary_timestamp_values(self):
        """Test boundary timestamp values"""
        # Very old timestamp
        old_event = EventModel(
            event_id="old-timestamp",
            timestamp=datetime(1970, 1, 1, tzinfo=timezone.utc),
            user_id="test-user",
            session_id="test-session",
            event_type="test",
            event_category="test",
            properties="{}"
        )
        assert old_event.timestamp.year == 1970
        
        # Future timestamp
        future_event = EventModel(
            event_id="future-timestamp",
            timestamp=datetime(2050, 12, 31, tzinfo=timezone.utc),
            user_id="test-user",
            session_id="test-session",
            event_type="test",
            event_category="test",
            properties="{}"
        )
        assert future_event.timestamp.year == 2050

# =============================================================================
# INTEGRATION WITH EXISTING FIXTURES
# =============================================================================

class TestWithFixtures:
    """Test models using conftest fixtures"""
    
    def test_sample_events_validation(self, sample_chat_interaction_event, 
                                     sample_survey_response_event, 
                                     sample_performance_event):
        """Test all sample events from fixtures validate correctly"""
        # Chat interaction event
        chat_event = EventModel(**sample_chat_interaction_event)
        assert chat_event.event_type == "chat_interaction"
        
        # Survey response event
        survey_event = EventModel(**sample_survey_response_event)
        assert survey_event.event_type == "survey_response"
        
        # Performance event
        perf_event = EventModel(**sample_performance_event)
        assert perf_event.event_type == "performance_metric"
    
    def test_batch_events_validation(self, sample_event_batch):
        """Test batch events validation"""
        validated_events = []
        
        for event_data in sample_event_batch:
            event = EventModel(**event_data)
            validated_events.append(event)
        
        assert len(validated_events) == len(sample_event_batch)
        
        # Check mix of event types
        event_types = {event.event_type for event in validated_events}
        assert "chat_interaction" in event_types
        assert "performance_metric" in event_types