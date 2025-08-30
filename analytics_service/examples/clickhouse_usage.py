#!/usr/bin/env python3
"""
Example usage of ClickHouse Analytics Integration

This example demonstrates how to use the ClickHouse manager and service
for analytics operations in the Netra Analytics Service.
"""
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Import from analytics_core
from analytics_core import ClickHouseManager, ClickHouseService


async def example_usage():
    """
    Example of using ClickHouse integration for analytics.
    """
    # Initialize ClickHouse manager with configuration
    ch_manager = ClickHouseManager(
        host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
        port=int(os.getenv('CLICKHOUSE_PORT', '9000')),
        database=os.getenv('CLICKHOUSE_DATABASE', 'analytics'),
        user=os.getenv('CLICKHOUSE_USER', 'default'),
        password=os.getenv('CLICKHOUSE_PASSWORD', ''),
        max_connections=10,
        connection_timeout=10,
        query_timeout=30,
        max_retries=3
    )
    
    # Initialize ClickHouse service
    ch_service = ClickHouseService(ch_manager)
    
    try:
        # Initialize the connection manager
        await ch_manager.initialize()
        print("✅ ClickHouse connection manager initialized")
        
        # Initialize tables and materialized views
        await ch_service.initialize_tables()
        print("✅ ClickHouse tables and views created")
        
        # Example 1: Insert a chat interaction event
        event_id = await ch_service.insert_chat_interaction(
            user_id="user_123",
            session_id="session_456",
            thread_id="thread_789",
            message_id="msg_001",
            message_type="user_prompt",
            prompt_text="How can I optimize my AI costs?",
            prompt_length=35,
            response_time_ms=1250.0,
            model_used="claude-3-sonnet",
            tokens_consumed=85,
            is_follow_up=False,
            page_path="/chat",
            environment="production"
        )
        print(f"✅ Inserted chat interaction event: {event_id}")
        
        # Example 2: Insert prompt analytics
        prompt_id = await ch_service.insert_prompt_analytics(
            user_id="user_123",
            thread_id="thread_789",
            prompt_hash="abc123hash",
            prompt_category="cost_optimization",
            prompt_intent="seek_advice",
            prompt_complexity_score=0.7,
            response_quality_score=0.9,
            response_relevance_score=0.85,
            follow_up_generated=True,
            is_repeat_question=False,
            estimated_cost_cents=2.5,
            actual_cost_cents=2.3
        )
        print(f"✅ Inserted prompt analytics: {prompt_id}")
        
        # Example 3: Batch insert multiple events
        batch_events = [
            {
                'user_id': 'user_124',
                'session_id': 'session_457',
                'event_type': 'feature_usage',
                'event_category': 'User Interaction Events',
                'event_action': 'button_click',
                'event_label': 'export_data',
                'event_value': 1.0,
                'properties': {'feature': 'data_export', 'success': True},
                'page_path': '/dashboard',
                'environment': 'production'
            },
            {
                'user_id': 'user_125',
                'session_id': 'session_458',
                'event_type': 'performance_metric',
                'event_category': 'Technical Events',
                'event_action': 'page_load',
                'event_label': '/dashboard',
                'event_value': 1850.0,  # Load time in ms
                'properties': {'metric_type': 'page_load', 'success': True},
                'page_path': '/dashboard',
                'environment': 'production'
            }
        ]
        
        count = await ch_service.batch_insert_events(batch_events)
        print(f"✅ Batch inserted {count} events")
        
        # Example 4: Get user activity summary
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        activity_summary = await ch_service.get_user_activity_summary(
            start_date=start_date,
            end_date=end_date,
            granularity='day'
        )
        print(f"✅ Retrieved activity summary for {len(activity_summary)} user-day records")
        
        # Example 5: Get real-time metrics
        real_time_metrics = await ch_service.get_real_time_metrics()
        print("✅ Real-time metrics:")
        for metric, value in real_time_metrics.items():
            print(f"   {metric}: {value}")
        
        # Example 6: Get prompt analytics report
        prompt_report = await ch_service.get_prompt_analytics_report(
            time_range='24h',
            min_frequency=1
        )
        print(f"✅ Prompt analytics report generated with {len(prompt_report['top_prompts'])} prompts")
        
        # Example 7: Get storage usage
        storage_usage = await ch_service.get_storage_usage()
        print(f"✅ Storage usage: {storage_usage['total_size_bytes']} bytes across {len(storage_usage['tables'])} tables")
        
        # Example 8: Get materialized view status
        view_status = await ch_service.get_materialized_view_status()
        print("✅ Materialized view status:")
        for view_name, status in view_status.items():
            print(f"   {view_name}: {status.get('status', 'unknown')}")
        
        # Example 9: Health check
        health_status = await ch_manager.get_health_status()
        print("✅ ClickHouse health status:")
        for key, value in health_status.items():
            print(f"   {key}: {value}")
        
        print("\n🎉 All examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during example execution: {e}")
        raise
    
    finally:
        # Always close the connection manager
        await ch_manager.close()
        print("✅ ClickHouse connection manager closed")


async def performance_example():
    """
    Example demonstrating high-performance batch operations.
    """
    print("\n📊 Performance Example: Batch Operations")
    
    ch_manager = ClickHouseManager()
    ch_service = ClickHouseService(ch_manager)
    
    try:
        await ch_manager.initialize()
        await ch_service.initialize_tables()
        
        # Generate a large batch of events
        import random
        from uuid import uuid4
        
        batch_size = 1000
        events = []
        
        event_types = ['chat_interaction', 'feature_usage', 'performance_metric']
        users = [f"user_{i}" for i in range(100)]
        
        for i in range(batch_size):
            event = {
                'user_id': random.choice(users),
                'session_id': f"session_{random.randint(1000, 9999)}",
                'event_type': random.choice(event_types),
                'event_category': 'User Interaction Events',
                'event_action': f"action_{i}",
                'event_label': f"label_{i}",
                'event_value': random.uniform(0, 100),
                'properties': {'batch_id': 'performance_test', 'index': i},
                'environment': 'test'
            }
            events.append(event)
        
        # Time the batch insertion
        import time
        start_time = time.time()
        
        count = await ch_service.batch_insert_events(events)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Inserted {count} events in {duration:.2f} seconds")
        print(f"✅ Rate: {count/duration:.0f} events/second")
        
        # Clean up test data
        await ch_manager.execute_command(
            "DELETE FROM frontend_events WHERE JSONExtractString(properties, 'batch_id') = 'performance_test'"
        )
        print("✅ Cleaned up test data")
        
    finally:
        await ch_manager.close()


if __name__ == "__main__":
    """
    Run the examples.
    """
    print("🚀 Starting ClickHouse Analytics Integration Examples")
    
    # Run basic usage example
    asyncio.run(example_usage())
    
    # Run performance example
    asyncio.run(performance_example())
    
    print("\n✨ All examples completed!")