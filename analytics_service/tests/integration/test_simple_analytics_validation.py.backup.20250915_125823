"""
Simple Analytics Validation Test - SSOT Compliance Check
=========================================================

This test validates that the analytics integration components work correctly
with the SSOT patterns and event models.

Business Value: Platform/Internal - Ensures analytics integration functions correctly
"""

import pytest
import time
from datetime import datetime, timezone
from uuid import uuid4

# SSOT imports
from test_framework.ssot.base_test_case import SSotBaseTestCase
from analytics_service.analytics_core.models.events import (
    AnalyticsEvent, EventType, EventCategory, EventContext
)
from analytics_service.analytics_core.services.event_processor import (
    EventProcessor, ProcessorConfig
)
from analytics_service.analytics_core import create_event_processor, FrontendEvent


class TestSimpleAnalyticsValidation(SSotBaseTestCase):
    """Simple validation tests for analytics integration"""
    
    def setup_method(self, method=None):
        """Setup for analytics validation tests"""
        super().setup_method(method)
        
        # Analytics test environment
        self.set_env_var("ANALYTICS_SERVICE_ENABLED", "true")
        self.set_env_var("REQUIRE_USER_CONTEXT", "false")  # Disable for basic validation
        
    def test_event_model_creation(self):
        """Test that AnalyticsEvent models can be created with correct structure"""
        user_id = f"test_user_{int(time.time())}"
        
        # Create event context
        context = EventContext(
            user_id=user_id,
            session_id=f"session_{int(time.time())}",
            page_path="/test",
            environment="test"
        )
        
        # Create analytics event
        event = AnalyticsEvent(
            event_type=EventType.CHAT_INTERACTION,
            event_category="user_interaction", 
            event_action="test_action",
            event_label="test_label",
            properties={
                "thread_id": f"thread_{uuid4()}",
                "message_id": f"msg_test",
                "message_type": "user_prompt",
                "prompt_length": 25,
                "is_follow_up": False
            },
            context=context
        )
        
        # Validate event structure
        assert event.event_type == EventType.CHAT_INTERACTION
        assert event.context.user_id == user_id
        assert event.properties["thread_id"] is not None
        
        # Record success
        self.record_metric("event_model_creation", "PASS")
        
    def test_frontend_event_helper(self):
        """Test FrontendEvent helper function works correctly"""
        user_id = f"frontend_test_user_{int(time.time())}"
        
        # Create event using helper
        event = FrontendEvent(
            user_id=user_id,
            session_id=f"session_{int(time.time())}",
            event_type=EventType.FEATURE_USAGE,
            event_category=EventCategory.BUSINESS,
            event_action="test_feature",
            properties={
                "feature_name": "test_dashboard",
                "action": "view",
                "success": True
            }
        )
        
        # Validate helper creates correct structure
        assert isinstance(event, AnalyticsEvent)
        assert event.context.user_id == user_id
        assert event.event_type == EventType.FEATURE_USAGE
        assert event.properties["feature_name"] == "test_dashboard"
        
        # Record success
        self.record_metric("frontend_event_helper", "PASS")
        
    async def test_event_processor_creation(self):
        """Test that EventProcessor can be created and initialized"""
        config = ProcessorConfig(
            batch_size=1,
            require_user_context=False,  # Disable for validation
            enable_analytics=True
        )
        
        processor = create_event_processor(config)
        assert processor is not None
        
        # Test initialization
        init_result = await processor.initialize()
        assert init_result is True or init_result is None  # Some managers return None on success
        
        # Record success 
        self.record_metric("event_processor_creation", "PASS")
        
    async def test_basic_event_validation(self):
        """Test basic event validation logic"""
        user_id = f"validation_user_{int(time.time())}"
        
        # Create valid event
        valid_event = FrontendEvent(
            user_id=user_id,
            session_id=f"session_{int(time.time())}",
            event_type=EventType.CHAT_INTERACTION,
            event_category=EventCategory.USER_INTERACTION,
            event_action="chat_message",
            properties={
                "thread_id": f"thread_{uuid4()}",
                "message_id": f"msg_{uuid4()}",
                "message_type": "user_prompt",
                "prompt_text": "Test message",
                "prompt_length": 12,
                "is_follow_up": False
            }
        )
        
        # Create processor for validation testing
        config = ProcessorConfig(require_user_context=False)
        processor = create_event_processor(config)
        
        # Test internal validation (access private method for testing)
        is_valid = processor._validate_event(valid_event)
        assert is_valid is True, "Valid event should pass validation"
        
        # Record metrics
        self.record_metric("event_validation_works", True)
        self.record_metric("validation_result", "PASS")