"""Example Usage of Analytics Event Processor

This script demonstrates how to use the analytics event processor
with batch processing, error handling, and report generation.
"""

import asyncio
import logging
from datetime import datetime, date
from uuid import uuid4

from analytics_service.analytics_core import (
    create_event_processor,
    FrontendEvent,
    EventType,
    EventCategory,
    get_analytics_config
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_event_processing():
    """Example of event processing with the analytics service"""
    logger.info("Starting analytics event processor example")
    
    # Get configuration
    config = get_analytics_config()
    logger.info(f"Using configuration: {config.to_dict()}")
    
    # Create event processor
    processor = create_event_processor(config)
    
    # Use processor context manager for proper lifecycle management
    async with processor.processor_context():
        logger.info("Event processor started successfully")
        
        # Example 1: Process individual events
        await process_sample_events(processor)
        
        # Example 2: Generate reports
        await generate_sample_reports(processor)
        
        # Example 3: Get real-time metrics
        await show_realtime_metrics(processor)
        
        # Example 4: Health check
        await show_health_status(processor)
    
    logger.info("Event processor stopped successfully")


async def process_sample_events(processor):
    """Process some sample events"""
    logger.info("Processing sample events...")
    
    # Create sample chat interaction event
    chat_event = FrontendEvent(
        event_id=uuid4(),
        timestamp=datetime.utcnow(),
        user_id="user_123",
        session_id="session_456",
        event_type=EventType.CHAT_INTERACTION,
        event_category=EventCategory.USER_INTERACTION,
        event_action="message_sent",
        event_label="user_prompt",
        event_value=50.0,  # tokens consumed
        properties={
            "thread_id": "thread_789",
            "message_id": "msg_001",
            "message_type": "user_prompt",
            "prompt_text": "How do I optimize my AI costs?",
            "prompt_length": 30,
            "response_time_ms": 1250,
            "model_used": "claude-sonnet-4",
            "tokens_consumed": 50,
            "is_follow_up": False
        },
        user_agent="Mozilla/5.0 (Chrome/120.0)",
        page_path="/chat",
        page_title="AI Chat Interface",
        environment="development"
    )
    
    # Create sample feature usage event
    feature_event = FrontendEvent(
        event_id=uuid4(),
        timestamp=datetime.utcnow(),
        user_id="user_123",
        session_id="session_456",
        event_type=EventType.FEATURE_USAGE,
        event_category=EventCategory.USER_INTERACTION,
        event_action="feature_accessed",
        event_label="cost_optimizer",
        properties={
            "feature_name": "cost_optimizer",
            "action": "analysis_run",
            "success": True,
            "duration_ms": 2500
        },
        user_agent="Mozilla/5.0 (Chrome/120.0)",
        page_path="/optimizer",
        page_title="Cost Optimizer",
        environment="development"
    )
    
    # Create sample performance metric event
    performance_event = FrontendEvent(
        event_id=uuid4(),
        timestamp=datetime.utcnow(),
        user_id="user_123",
        session_id="session_456",
        event_type=EventType.PERFORMANCE_METRIC,
        event_category=EventCategory.TECHNICAL,
        event_action="api_response",
        event_label="chat_api",
        event_value=1250.0,  # response time ms
        properties={
            "metric_type": "api_call",
            "duration_ms": 1250,
            "success": True,
            "endpoint": "/api/chat/message"
        },
        user_agent="Mozilla/5.0 (Chrome/120.0)",
        page_path="/chat",
        environment="development"
    )
    
    # Process events
    events = [chat_event, feature_event, performance_event]
    
    for i, event in enumerate(events, 1):
        success = await processor.process_event(event)
        logger.info(f"Event {i}/3 processed: {'[U+2713]' if success else '[U+2717]'}")
    
    # Wait for batch processing
    await asyncio.sleep(2)
    
    logger.info(f"Processed events. Stats: {processor.get_stats()}")


async def generate_sample_reports(processor):
    """Generate sample analytics reports"""
    logger.info("Generating sample reports...")
    
    # User activity report
    user_activity = await processor.generate_user_activity_report(
        user_id="user_123",
        start_date=date.today(),
        granularity="hour"
    )
    logger.info(f"User activity report: {len(user_activity)} records")
    
    if user_activity:
        logger.info(f"Sample activity record: {user_activity[0]}")
    
    # Prompt analytics report
    prompt_analytics = await processor.generate_prompt_analytics(
        time_range="1h",
        min_frequency=1
    )
    logger.info(f"Prompt analytics report: {len(prompt_analytics)} records")
    
    if prompt_analytics:
        logger.info(f"Sample prompt record: {prompt_analytics[0]}")


async def show_realtime_metrics(processor):
    """Show real-time metrics"""
    logger.info("Getting real-time metrics...")
    
    metrics = await processor.get_realtime_metrics()
    logger.info(f"Real-time metrics: {metrics}")


async def show_health_status(processor):
    """Show health status"""
    logger.info("Checking health status...")
    
    health = await processor.health_check()
    logger.info(f"Health status: {health}")


async def example_privacy_compliance():
    """Example of privacy compliance features"""
    logger.info("Testing privacy compliance features...")
    
    from analytics_service.analytics_core.utils.privacy import PrivacyFilter
    
    # Create privacy filter
    privacy_filter = PrivacyFilter(
        enable_pii_detection=True,
        enable_keyword_filtering=True,
        max_text_length=500
    )
    
    # Test text with PII
    test_text = """
    Hi, my email is john.doe@example.com and my phone is 555-123-4567.
    My credit card number is 4532 1234 5678 9012.
    I need help with my password reset.
    """
    
    # Sanitize text
    result = privacy_filter.sanitize_text(test_text)
    
    logger.info(f"Original text length: {result['original_length']}")
    logger.info(f"Sanitized text: {result['sanitized_text']}")
    logger.info(f"PII detected: {result['pii_detected']}")
    logger.info(f"Was truncated: {result['was_truncated']}")
    
    # Validate compliance
    compliance = privacy_filter.validate_compliance(test_text)
    logger.info(f"Compliance validation: {compliance}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_event_processing())
    asyncio.run(example_privacy_compliance())