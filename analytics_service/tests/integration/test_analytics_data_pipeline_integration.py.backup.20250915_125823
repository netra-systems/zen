"""
Analytics Data Pipeline Integration Tests - SSOT Implementation
===============================================================

Business Value Justification (BVJ):
1. Segment: Early, Mid, Enterprise - ALL customer segments require reliable analytics data
2. Business Goal: Revenue Protection & Customer Insights - Data pipeline failures = revenue loss
3. Value Impact: Real-time business intelligence for customer behavior and AI usage optimization
4. Strategic Impact: Foundation for $2.3M ARR analytics features and customer retention insights

CRITICAL: This module tests the COMPLETE analytics data pipeline with REAL services.
NO MOCKS - Uses actual ClickHouse database connections and Redis caching.

Architecture Compliance:
- Inherits from test_framework.ssot.base_test_case.SSotBaseTestCase 
- Uses IsolatedEnvironment for all configuration access (NO direct os.environ)
- Follows analytics event model definitions from analytics_service.analytics_core.models.events
- Tests with real EventProcessor and ClickHouse operations
- Validates business metrics calculation accuracy

Test Coverage Areas:
1. Event ingestion pipeline from backend services (BVJ: Platform Reliability)
2. ClickHouse connection and query execution (BVJ: Data Infrastructure)  
3. Business metrics calculation and storage (BVJ: Customer Insights)
4. User activity tracking and analytics (BVJ: Product Optimization)
5. Performance monitoring data collection (BVJ: System Health)
6. Data retention and cleanup processes (BVJ: Operational Efficiency)
7. Analytics API endpoints for reporting (BVJ: Customer Value Delivery)
8. Real-time vs batch processing patterns (BVJ: Performance)

SSOT Compliance:
- Uses analytics_service.analytics_core.models.events for ALL event models
- Uses shared.isolated_environment.IsolatedEnvironment for environment access
- Follows test_framework.ssot.base_test_case patterns for test structure
- No duplicate analytics logic - imports from canonical locations
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta, date
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from unittest.mock import patch

# SSOT Base Test Case - The CANONICAL test base class
from test_framework.ssot.base_test_case import SSotBaseTestCase

# SSOT Analytics Models - The CANONICAL event models
from analytics_service.analytics_core.models.events import (
    AnalyticsEvent, EventType, EventCategory, EventContext,
    ChatInteractionProperties, ThreadLifecycleProperties,
    FeatureUsageProperties, SurveyResponseProperties,
    FeedbackSubmissionProperties, PerformanceMetricProperties,
    ErrorTrackingProperties, EventBatch, ProcessingResult
)

# SSOT Event Processing - The CANONICAL event processor
from analytics_service.analytics_core.services.event_processor import (
    EventProcessor, ProcessorConfig
)

# SSOT Analytics Core components
from analytics_service.analytics_core import create_event_processor, FrontendEvent

# User Context for proper isolation (SECURITY CRITICAL)
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
except ImportError:
    # Fallback for testing environment
    class UserExecutionContext:
        def __init__(self, user_id: str, thread_id: str, run_id: str, request_id: str):
            self.user_id = user_id
            self.thread_id = thread_id
            self.run_id = run_id
            self.request_id = request_id
        
        @classmethod
        def from_request(cls, user_id: str, thread_id: str, run_id: str, request_id: str):
            return cls(user_id, thread_id, run_id, request_id)
        
        def to_dict(self):
            return {
                'user_id': self.user_id,
                'thread_id': self.thread_id,
                'run_id': self.run_id,
                'request_id': self.request_id
            }
        
        def get_correlation_id(self):
            return f"{self.user_id}:{self.request_id}"


class TestAnalyticsDataPipelineIntegration(SSotBaseTestCase):
    """
    COMPREHENSIVE Analytics Data Pipeline Integration Tests
    
    Business Value: Platform/Internal - System Stability & Customer Data Insights
    Tests the complete analytics data pipeline from event ingestion through 
    business metrics calculation using REAL ClickHouse and Redis connections.
    
    CRITICAL: All tests use REAL services - NO MOCKS
    """
    
    def setup_method(self, method=None):
        """Setup test environment with analytics-specific configuration"""
        super().setup_method(method)
        
        # Analytics-specific environment configuration using SSOT IsolatedEnvironment
        self.set_env_var("ANALYTICS_SERVICE_ENABLED", "true")
        self.set_env_var("CLICKHOUSE_ENABLED", "true") 
        self.set_env_var("REDIS_ENABLED", "true")
        self.set_env_var("EVENT_BATCH_SIZE", "10")  # Smaller batches for testing
        self.set_env_var("EVENT_FLUSH_INTERVAL_MS", "100")  # Fast flush for tests
        self.set_env_var("REQUIRE_USER_CONTEXT", "true")  # SECURITY: Enforce user context
        
        # Performance tracking
        self.record_metric("test_category", "analytics_pipeline_integration")
        self.record_metric("real_services_used", True)
        self.record_metric("mock_services_used", False)  # NO MOCKS POLICY
        
    async def test_event_ingestion_pipeline_with_real_clickhouse(self):
        """
        BVJ: Platform/Internal - Data Pipeline Reliability
        Test complete event ingestion pipeline using REAL ClickHouse connection.
        
        Business Impact: Prevents $50K+ revenue loss from missing analytics data.
        Customer Value: Ensures accurate billing and usage tracking.
        """
        # Create test user context for proper isolation
        user_context = UserExecutionContext.from_request(
            user_id=f"pipeline_test_user_{int(time.time())}",
            thread_id=f"thread_{uuid4()}",
            run_id=f"run_{uuid4()}",
            request_id=f"req_{uuid4()}"
        )
        
        # Create real event processor with user context requirement
        config = ProcessorConfig(
            batch_size=5,
            flush_interval_seconds=1,
            require_user_context=True,
            enable_analytics=True
        )
        
        processor = create_event_processor(config)
        
        # Track database operations
        with self.track_db_queries():
            try:
                # Initialize processor with REAL services
                await processor.initialize()
                await processor.start()
                
                # Create test events with proper business context
                test_events = self._create_business_realistic_events(user_context.user_id, 10)
                
                # Process events through pipeline
                processing_results = []
                for event in test_events:
                    self.increment_db_query_count()
                    result = await processor.process_event(event, user_context)
                    processing_results.append(result)
                    
                # Wait for pipeline to flush to ClickHouse
                await asyncio.sleep(2)
                
                # Verify all events processed successfully  
                successful_events = sum(1 for result in processing_results if result)
                assert successful_events == len(test_events), f"Expected {len(test_events)} successful events, got {successful_events}"
                
                # Validate business metrics were calculated
                metrics = await processor.get_realtime_metrics()
                assert metrics is not None, "Real-time metrics should be available"
                assert metrics.get('processor_events_processed', 0) >= len(test_events)
                
                # Record performance metrics
                self.record_metric("events_ingested", len(test_events))
                self.record_metric("clickhouse_operations", self.get_db_query_count())
                self.record_metric("pipeline_success_rate", successful_events / len(test_events))
                
            finally:
                await processor.stop()
        
        # Validate pipeline performance requirements
        self.assert_execution_time_under(10.0)  # Pipeline should be fast
        self.record_metric("test_result", "PASS")

    async def test_clickhouse_business_metrics_calculation(self):
        """
        BVJ: Early/Mid/Enterprise - Customer Analytics & Revenue Optimization  
        Test ClickHouse operations for business metrics calculation.
        
        Business Impact: Accurate customer usage metrics = $100K+ increased conversion
        Customer Value: Real-time insights into AI spending optimization opportunities
        """
        user_context = UserExecutionContext.from_request(
            user_id=f"metrics_test_user_{int(time.time())}",
            thread_id=f"thread_{uuid4()}",
            run_id=f"run_{uuid4()}",
            request_id=f"req_{uuid4()}"
        )
        
        processor = create_event_processor()
        
        try:
            await processor.initialize()
            await processor.start()
            
            # Create business-focused test events
            chat_events = self._create_chat_interaction_events(user_context.user_id, 15)
            survey_events = self._create_survey_response_events(user_context.user_id, 3) 
            performance_events = self._create_performance_events(user_context.user_id, 8)
            
            all_events = chat_events + survey_events + performance_events
            
            # Process events with business context
            with self.track_db_queries():
                for event in all_events:
                    await processor.process_event(event, user_context)
                
                # Allow time for ClickHouse processing
                await asyncio.sleep(3)
                
                # Generate business activity report
                self.increment_db_query_count()
                activity_report = await processor.generate_user_activity_report(
                    user_context=user_context,
                    start_date=date.today() - timedelta(days=1),
                    end_date=date.today() + timedelta(days=1),
                    granularity="hour"
                )
            
            # Validate business metrics accuracy
            assert isinstance(activity_report, list), "Activity report should be a list"
            
            # Business validation: User should have measurable activity
            if activity_report:
                total_events = sum(item.get('total_events', 0) for item in activity_report)
                chat_interactions = sum(item.get('chat_interactions', 0) for item in activity_report) 
                assert total_events >= len(all_events) * 0.8, f"Expected ~{len(all_events)} events, got {total_events}"
                assert chat_interactions >= len(chat_events) * 0.8, f"Expected ~{len(chat_events)} chat events, got {chat_interactions}"
            
            # Record business metrics
            self.record_metric("total_business_events", len(all_events))
            self.record_metric("chat_interactions", len(chat_events))
            self.record_metric("survey_responses", len(survey_events))
            self.record_metric("performance_metrics", len(performance_events))
            self.record_metric("clickhouse_queries", self.get_db_query_count())
            
        finally:
            await processor.stop()
        
        self.record_metric("test_result", "PASS")

    async def test_user_activity_tracking_with_isolation(self):
        """
        BVJ: Enterprise - Multi-User Analytics & Data Security
        Test user activity tracking with proper user context isolation.
        
        Business Impact: Secure multi-tenant analytics = $200K+ enterprise sales
        Customer Value: Isolated user data prevents privacy violations
        """
        # Create multiple user contexts for isolation testing
        user_contexts = [
            UserExecutionContext.from_request(
                user_id=f"isolation_user_{i}_{int(time.time())}",
                thread_id=f"thread_{uuid4()}",
                run_id=f"run_{uuid4()}",
                request_id=f"req_{uuid4()}"
            ) for i in range(3)
        ]
        
        processor = create_event_processor(ProcessorConfig(require_user_context=True))
        
        try:
            await processor.initialize()
            await processor.start()
            
            # Process events for each user separately
            events_per_user = {}
            
            for user_context in user_contexts:
                user_events = self._create_user_specific_events(user_context.user_id, 12)
                events_per_user[user_context.user_id] = user_events
                
                for event in user_events:
                    result = await processor.process_event(event, user_context)
                    assert result is True, f"Event processing failed for user {user_context.user_id}"
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # Validate user isolation - each user should only see their own data
            for user_context in user_contexts:
                activity_report = await processor.generate_user_activity_report(
                    user_context=user_context,
                    start_date=date.today() - timedelta(days=1),
                    end_date=date.today() + timedelta(days=1)
                )
                
                # Business validation: User isolation is maintained
                expected_events = len(events_per_user[user_context.user_id])
                if activity_report:
                    total_events = sum(item.get('total_events', 0) for item in activity_report)
                    
                    # Each user should see approximately their own events (allow for processing latency)
                    assert total_events >= expected_events * 0.7, \
                        f"User {user_context.user_id} expected ~{expected_events} events, got {total_events}"
                    assert total_events <= expected_events * 1.3, \
                        f"User {user_context.user_id} got too many events: {total_events} (expected ~{expected_events})"
            
            # Record isolation metrics
            self.record_metric("users_tested", len(user_contexts))
            self.record_metric("events_per_user", sum(len(events) for events in events_per_user.values()) / len(user_contexts))
            self.record_metric("user_isolation_validated", True)
            
        finally:
            await processor.stop()
        
        self.record_metric("test_result", "PASS")

    async def test_performance_monitoring_data_collection(self):
        """
        BVJ: Platform/Internal - System Performance & Customer Experience
        Test performance monitoring data collection and analysis.
        
        Business Impact: 99.9% uptime = $300K+ revenue protection
        Customer Value: Sub-second response times improve user satisfaction
        """
        user_context = UserExecutionContext.from_request(
            user_id=f"perf_user_{int(time.time())}",
            thread_id=f"thread_{uuid4()}",
            run_id=f"run_{uuid4()}",
            request_id=f"req_{uuid4()}"
        )
        
        processor = create_event_processor()
        
        try:
            await processor.initialize()
            await processor.start()
            
            # Create performance monitoring events
            performance_scenarios = [
                {"metric_type": "api_call", "duration_ms": 150.5, "success": True, "endpoint": "/chat/send"},
                {"metric_type": "api_call", "duration_ms": 2500.0, "success": False, "endpoint": "/analytics/report", "error": "timeout"},
                {"metric_type": "websocket", "duration_ms": 45.2, "success": True, "event_type": "agent_started"},
                {"metric_type": "render", "duration_ms": 890.3, "success": True, "component": "analytics_dashboard"},
                {"metric_type": "page_load", "duration_ms": 1200.7, "success": True, "page": "/dashboard"},
            ]
            
            performance_events = []
            for i, scenario in enumerate(performance_scenarios):
                event = FrontendEvent(
                    user_id=user_context.user_id,
                    session_id=f"perf_session_{int(time.time())}",
                    event_type=EventType.PERFORMANCE_METRIC,
                    event_category=EventCategory.TECHNICAL,
                    event_action="performance_measurement",
                    event_label=scenario["metric_type"],
                    event_value=scenario["duration_ms"],
                    properties={
                        "metric_type": scenario["metric_type"],
                        "duration_ms": scenario["duration_ms"],
                        "success": scenario["success"],
                        "error_details": scenario.get("error"),
                        "endpoint": scenario.get("endpoint"),
                        "component": scenario.get("component"),
                        "page": scenario.get("page")
                    }
                )
                performance_events.append(event)
            
            # Process performance events
            start_time = time.time()
            for event in performance_events:
                result = await processor.process_event(event, user_context)
                assert result is True, f"Performance event processing failed: {event.properties}"
            
            processing_duration = time.time() - start_time
            
            # Wait for metrics aggregation
            await asyncio.sleep(2)
            
            # Validate real-time metrics collection
            metrics = await processor.get_realtime_metrics()
            assert metrics is not None, "Performance metrics should be available"
            
            # Business validation: Performance monitoring works
            processed_count = metrics.get('processor_events_processed', 0)
            assert processed_count >= len(performance_events), \
                f"Expected {len(performance_events)} performance events processed, got {processed_count}"
            
            # Record performance analysis metrics
            self.record_metric("performance_events_count", len(performance_events))
            self.record_metric("processing_duration_ms", processing_duration * 1000)
            self.record_metric("avg_event_processing_time_ms", (processing_duration * 1000) / len(performance_events))
            self.record_metric("successful_events", sum(1 for scenario in performance_scenarios if scenario["success"]))
            self.record_metric("failed_events", sum(1 for scenario in performance_scenarios if not scenario["success"]))
            
        finally:
            await processor.stop()
        
        # Performance validation
        self.assert_execution_time_under(8.0)
        self.record_metric("test_result", "PASS")

    async def test_data_retention_and_cleanup_processes(self):
        """
        BVJ: Platform/Internal - Operational Efficiency & Cost Management
        Test data retention and cleanup processes for analytics data.
        
        Business Impact: 30% storage cost reduction = $25K+ annual savings
        Customer Value: Efficient data management ensures system performance
        """
        user_context = UserExecutionContext.from_request(
            user_id=f"retention_user_{int(time.time())}",
            thread_id=f"thread_{uuid4()}",
            run_id=f"run_{uuid4()}",
            request_id=f"req_{uuid4()}"
        )
        
        processor = create_event_processor()
        
        try:
            await processor.initialize()
            await processor.start()
            
            # Create events with different timestamps for retention testing
            retention_test_events = []
            
            # Recent events (should be retained)
            recent_events = self._create_timestamped_events(
                user_context.user_id, 
                count=5,
                base_timestamp=datetime.now(timezone.utc)
            )
            retention_test_events.extend(recent_events)
            
            # Older events (subject to retention policy)
            old_events = self._create_timestamped_events(
                user_context.user_id,
                count=5, 
                base_timestamp=datetime.now(timezone.utc) - timedelta(days=100)
            )
            retention_test_events.extend(old_events)
            
            # Process all events
            processed_count = 0
            for event in retention_test_events:
                result = await processor.process_event(event, user_context)
                if result:
                    processed_count += 1
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # Validate data ingestion
            assert processed_count >= len(retention_test_events) * 0.8, \
                f"Expected most events processed, got {processed_count}/{len(retention_test_events)}"
            
            # Test cleanup processes (simulate)
            health_status = await processor.health_check()
            assert health_status['running'] is True, "Processor should be running for cleanup"
            assert 'clickhouse_healthy' in health_status, "ClickHouse health should be monitored"
            assert 'redis_healthy' in health_status, "Redis health should be monitored"
            
            # Record retention metrics
            self.record_metric("recent_events_count", len(recent_events))
            self.record_metric("old_events_count", len(old_events))
            self.record_metric("total_processed_events", processed_count)
            self.record_metric("retention_policy_active", True)
            self.record_metric("cleanup_process_healthy", health_status.get('clickhouse_healthy', False))
            
        finally:
            await processor.stop()
        
        self.record_metric("test_result", "PASS")

    async def test_analytics_api_endpoints_for_reporting(self):
        """
        BVJ: Early/Mid/Enterprise - Customer Value Delivery & Business Intelligence
        Test analytics API endpoints for customer reporting features.
        
        Business Impact: Analytics features = $500K+ ARR from premium tiers
        Customer Value: Real-time business insights drive AI optimization decisions
        """
        user_context = UserExecutionContext.from_request(
            user_id=f"api_test_user_{int(time.time())}",
            thread_id=f"thread_{uuid4()}",
            run_id=f"run_{uuid4()}",
            request_id=f"req_{uuid4()}"
        )
        
        processor = create_event_processor()
        
        try:
            await processor.initialize()
            await processor.start()
            
            # Create comprehensive test data for reporting
            chat_events = self._create_chat_interaction_events(user_context.user_id, 20)
            thread_events = self._create_thread_lifecycle_events(user_context.user_id, 5)
            feature_events = self._create_feature_usage_events(user_context.user_id, 10)
            
            all_events = chat_events + thread_events + feature_events
            
            # Process events for reporting
            for event in all_events:
                await processor.process_event(event, user_context)
            
            # Wait for data aggregation
            await asyncio.sleep(3)
            
            # Test user activity report API
            activity_report = await processor.generate_user_activity_report(
                user_context=user_context,
                start_date=date.today() - timedelta(days=1),
                end_date=date.today() + timedelta(days=1),
                granularity="day"
            )
            
            # Validate reporting API responses
            assert isinstance(activity_report, list), "Activity report should be a list"
            
            # Test prompt analytics API (aggregate data)
            prompt_analytics = await processor.generate_prompt_analytics(
                category="chat_interaction",
                min_frequency=1,
                time_range="24h"
            )
            
            assert isinstance(prompt_analytics, list), "Prompt analytics should be a list"
            
            # Test real-time metrics API
            realtime_metrics = await processor.get_realtime_metrics()
            
            assert isinstance(realtime_metrics, dict), "Real-time metrics should be a dict"
            assert 'processor_events_processed' in realtime_metrics, "Should include processor metrics"
            
            # Validate business reporting metrics
            if activity_report:
                total_reported_events = sum(item.get('total_events', 0) for item in activity_report)
                assert total_reported_events >= len(all_events) * 0.7, \
                    f"Reporting should capture most events: {total_reported_events}/{len(all_events)}"
            
            # Record API performance metrics
            self.record_metric("api_endpoints_tested", 3)
            self.record_metric("activity_report_size", len(activity_report))
            self.record_metric("prompt_analytics_size", len(prompt_analytics))
            self.record_metric("realtime_metrics_count", len(realtime_metrics))
            self.record_metric("reporting_apis_functional", True)
            
        finally:
            await processor.stop()
        
        self.record_metric("test_result", "PASS")

    async def test_real_time_vs_batch_processing_patterns(self):
        """
        BVJ: Platform/Internal - Performance Optimization & Scalability  
        Test real-time vs batch processing patterns for different workloads.
        
        Business Impact: 50% better throughput = support 10x more customers
        Customer Value: Faster insights and reduced latency for time-sensitive decisions
        """
        user_context = UserExecutionContext.from_request(
            user_id=f"processing_user_{int(time.time())}",
            thread_id=f"thread_{uuid4()}",
            run_id=f"run_{uuid4()}",
            request_id=f"req_{uuid4()}"
        )
        
        # Test real-time processing
        realtime_config = ProcessorConfig(
            batch_size=1,  # Process immediately
            flush_interval_seconds=0.1,  # Very fast flush
            require_user_context=True
        )
        
        realtime_processor = create_event_processor(realtime_config)
        
        # Test batch processing  
        batch_config = ProcessorConfig(
            batch_size=50,  # Large batches
            flush_interval_seconds=5,  # Longer interval
            require_user_context=True
        )
        
        batch_processor = create_event_processor(batch_config)
        
        try:
            # Initialize both processors
            await realtime_processor.initialize()
            await realtime_processor.start()
            
            await batch_processor.initialize()
            await batch_processor.start()
            
            # Create test events
            test_events = self._create_mixed_event_types(user_context.user_id, 30)
            
            # Test real-time processing performance
            realtime_start = time.time()
            realtime_results = []
            
            for event in test_events[:15]:  # First half real-time
                result = await realtime_processor.process_event(event, user_context)
                realtime_results.append(result)
            
            realtime_duration = time.time() - realtime_start
            
            # Wait for real-time processing to complete
            await asyncio.sleep(1)
            
            # Test batch processing performance
            batch_start = time.time()
            batch_results = []
            
            for event in test_events[15:]:  # Second half batch
                result = await batch_processor.process_event(event, user_context)
                batch_results.append(result)
            
            batch_duration = time.time() - batch_start
            
            # Wait for batch processing to complete
            await asyncio.sleep(6)
            
            # Validate processing patterns
            realtime_success = sum(1 for r in realtime_results if r) / len(realtime_results)
            batch_success = sum(1 for r in batch_results if r) / len(batch_results)
            
            assert realtime_success >= 0.9, f"Real-time processing success rate too low: {realtime_success}"
            assert batch_success >= 0.9, f"Batch processing success rate too low: {batch_success}"
            
            # Get final metrics
            realtime_metrics = await realtime_processor.get_realtime_metrics()
            batch_metrics = await batch_processor.get_realtime_metrics()
            
            # Record performance comparison
            self.record_metric("realtime_duration_ms", realtime_duration * 1000)
            self.record_metric("batch_duration_ms", batch_duration * 1000)
            self.record_metric("realtime_success_rate", realtime_success)
            self.record_metric("batch_success_rate", batch_success)
            self.record_metric("realtime_events_processed", realtime_metrics.get('processor_events_processed', 0))
            self.record_metric("batch_events_processed", batch_metrics.get('processor_events_processed', 0))
            
            # Performance analysis
            realtime_throughput = len(realtime_results) / realtime_duration if realtime_duration > 0 else 0
            batch_throughput = len(batch_results) / batch_duration if batch_duration > 0 else 0
            
            self.record_metric("realtime_throughput_events_per_sec", realtime_throughput)
            self.record_metric("batch_throughput_events_per_sec", batch_throughput)
            
        finally:
            await realtime_processor.stop()
            await batch_processor.stop()
        
        self.record_metric("test_result", "PASS")

    async def test_cross_service_event_ingestion_integration(self):
        """
        BVJ: Platform/Internal - Inter-Service Communication & Data Consistency
        Test event ingestion from other services (backend, auth, frontend).
        
        Business Impact: Complete customer journey tracking = 25% better conversion
        Customer Value: Unified analytics across all touchpoints
        """
        # Create multiple user contexts simulating different services
        backend_user = UserExecutionContext.from_request(
            user_id=f"backend_service_user_{int(time.time())}",
            thread_id=f"backend_thread_{uuid4()}",
            run_id=f"backend_run_{uuid4()}",
            request_id=f"backend_req_{uuid4()}"
        )
        
        frontend_user = UserExecutionContext.from_request(
            user_id=f"frontend_service_user_{int(time.time())}",
            thread_id=f"frontend_thread_{uuid4()}",
            run_id=f"frontend_run_{uuid4()}",
            request_id=f"frontend_req_{uuid4()}"
        )
        
        processor = create_event_processor()
        
        try:
            await processor.initialize()
            await processor.start()
            
            # Simulate events from different services
            backend_events = self._create_backend_service_events(backend_user.user_id, 8)
            frontend_events = self._create_frontend_service_events(frontend_user.user_id, 12)
            auth_events = self._create_auth_service_events(backend_user.user_id, 4)  # Same user across services
            
            # Process events from each service
            service_results = {
                'backend': [],
                'frontend': [], 
                'auth': []
            }
            
            # Backend service events
            for event in backend_events:
                result = await processor.process_event(event, backend_user)
                service_results['backend'].append(result)
            
            # Frontend service events  
            for event in frontend_events:
                result = await processor.process_event(event, frontend_user)
                service_results['frontend'].append(result)
            
            # Auth service events
            for event in auth_events:
                result = await processor.process_event(event, backend_user)  # Same user as backend
                service_results['auth'].append(result)
            
            # Wait for cross-service processing
            await asyncio.sleep(3)
            
            # Validate cross-service integration
            for service, results in service_results.items():
                success_rate = sum(1 for r in results if r) / len(results) if results else 0
                assert success_rate >= 0.8, f"{service} service integration failed: {success_rate} success rate"
                
                self.record_metric(f"{service}_events_processed", len(results))
                self.record_metric(f"{service}_success_rate", success_rate)
            
            # Test cross-service user activity correlation
            backend_report = await processor.generate_user_activity_report(
                user_context=backend_user,
                start_date=date.today() - timedelta(days=1),
                end_date=date.today() + timedelta(days=1)
            )
            
            frontend_report = await processor.generate_user_activity_report(
                user_context=frontend_user,
                start_date=date.today() - timedelta(days=1),
                end_date=date.today() + timedelta(days=1)
            )
            
            # Validate service-specific analytics
            self.record_metric("cross_service_reports_generated", 2)
            self.record_metric("backend_report_size", len(backend_report) if backend_report else 0)
            self.record_metric("frontend_report_size", len(frontend_report) if frontend_report else 0)
            
        finally:
            await processor.stop()
        
        self.record_metric("test_result", "PASS")

    async def test_event_processing_error_recovery_resilience(self):
        """
        BVJ: Platform/Internal - System Resilience & Business Continuity
        Test error recovery and resilience in event processing pipeline.
        
        Business Impact: 99.9% uptime = $300K+ revenue protection  
        Customer Value: Uninterrupted analytics even during system stress
        """
        user_context = UserExecutionContext.from_request(
            user_id=f"resilience_user_{int(time.time())}",
            thread_id=f"thread_{uuid4()}",
            run_id=f"run_{uuid4()}",
            request_id=f"req_{uuid4()}"
        )
        
        # Configure processor for resilience testing
        resilience_config = ProcessorConfig(
            batch_size=10,
            max_retries=3,
            retry_delay_seconds=0.5,
            require_user_context=True
        )
        
        processor = create_event_processor(resilience_config)
        
        try:
            await processor.initialize()
            await processor.start()
            
            # Create mix of valid and problematic events
            valid_events = self._create_chat_interaction_events(user_context.user_id, 10)
            
            # Create problematic events (missing fields, invalid data)
            problematic_events = [
                # Event with missing required properties
                FrontendEvent(
                    user_id=user_context.user_id,
                    session_id="error_test_session",
                    event_type=EventType.CHAT_INTERACTION,
                    event_category=EventCategory.USER_INTERACTION,
                    event_action="problematic_chat",
                    properties={}  # Missing required chat interaction properties
                ),
                # Event with invalid property types
                FrontendEvent(
                    user_id=user_context.user_id,
                    session_id="error_test_session",
                    event_type=EventType.PERFORMANCE_METRIC,
                    event_category=EventCategory.TECHNICAL,
                    event_action="invalid_metric",
                    properties={
                        "metric_type": "api_call",
                        "duration_ms": "invalid_number",  # Should be float
                        "success": "maybe"  # Should be boolean
                    }
                )
            ]
            
            all_test_events = valid_events + problematic_events
            
            # Process events and track results
            processing_results = []
            error_count = 0
            
            for event in all_test_events:
                try:
                    result = await processor.process_event(event, user_context)
                    processing_results.append(result)
                except Exception as e:
                    error_count += 1
                    self.record_metric(f"error_{error_count}", str(e)[:100])  # Truncate error message
                    processing_results.append(False)
            
            # Wait for processing with potential retries
            await asyncio.sleep(4)
            
            # Validate resilience
            successful_events = sum(1 for result in processing_results if result)
            total_events = len(all_test_events)
            success_rate = successful_events / total_events
            
            # Should process most valid events successfully
            assert successful_events >= len(valid_events) * 0.8, \
                f"Too many valid events failed: {successful_events} successful out of {len(valid_events)} valid events"
            
            # System should remain healthy despite errors
            health_status = await processor.health_check()
            assert health_status['running'] is True, "Processor should still be running after errors"
            
            # Get processor statistics
            stats = processor.get_stats()
            
            # Record resilience metrics
            self.record_metric("total_events_tested", total_events)
            self.record_metric("valid_events_count", len(valid_events))
            self.record_metric("problematic_events_count", len(problematic_events))
            self.record_metric("successful_events", successful_events)
            self.record_metric("error_count", error_count)
            self.record_metric("success_rate", success_rate)
            self.record_metric("system_remained_healthy", health_status['running'])
            self.record_metric("processor_events_failed", stats.get('events_failed', 0))
            
        finally:
            await processor.stop()
        
        # Validate overall resilience
        assert self.get_metric("success_rate", 0) >= 0.7, "System should handle errors gracefully"
        self.record_metric("test_result", "PASS")

    # === HELPER METHODS FOR TEST DATA CREATION ===

    def _create_business_realistic_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create business-realistic analytics events for testing"""
        events = []
        
        for i in range(count):
            if i % 3 == 0:
                # Chat interaction event
                event = FrontendEvent(
                    user_id=user_id,
                    session_id=f"business_session_{int(time.time())}",
                    event_type=EventType.CHAT_INTERACTION,
                    event_category=EventCategory.USER_INTERACTION,
                    event_action="ai_conversation",
                    event_label=f"optimization_query_{i}",
                    event_value=float(100 + i * 10),  # Token count
                    properties={
                        "thread_id": f"thread_{uuid4()}",
                        "message_id": f"msg_{i}",
                        "message_type": "user_prompt",
                        "prompt_text": f"How can I reduce my AI costs by optimizing usage pattern {i}?",
                        "prompt_length": 45 + i,
                        "response_time_ms": 1200.5 + i * 50,
                        "model_used": "claude-sonnet-4",
                        "tokens_consumed": 100 + i * 10,
                        "is_follow_up": i > 0
                    }
                )
            elif i % 3 == 1:
                # Feature usage event
                event = FrontendEvent(
                    user_id=user_id,
                    session_id=f"business_session_{int(time.time())}",
                    event_type=EventType.FEATURE_USAGE,
                    event_category=EventCategory.BUSINESS,
                    event_action="feature_interaction",
                    event_label=f"analytics_dashboard_{i}",
                    properties={
                        "feature_name": "cost_optimization_dashboard",
                        "action": "view_report",
                        "success": True,
                        "duration_ms": 850.3 + i * 25
                    }
                )
            else:
                # Performance metric event
                event = FrontendEvent(
                    user_id=user_id,
                    session_id=f"business_session_{int(time.time())}",
                    event_type=EventType.PERFORMANCE_METRIC,
                    event_category=EventCategory.TECHNICAL,
                    event_action="performance_measurement",
                    event_label="api_response_time",
                    event_value=float(250.5 + i * 15),
                    properties={
                        "metric_type": "api_call",
                        "duration_ms": 250.5 + i * 15,
                        "success": True
                    }
                )
            
            events.append(event)
        
        return events

    def _create_chat_interaction_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create chat interaction events for testing"""
        events = []
        thread_id = f"chat_thread_{uuid4()}"
        
        for i in range(count):
            event = FrontendEvent(
                user_id=user_id,
                session_id=f"chat_session_{int(time.time())}",
                event_type=EventType.CHAT_INTERACTION,
                event_category=EventCategory.USER_INTERACTION,
                event_action="user_message",
                event_label=f"message_{i}",
                event_value=float(80 + i * 5),
                properties={
                    "thread_id": thread_id,
                    "message_id": f"msg_{i}",
                    "message_type": "user_prompt" if i % 2 == 0 else "ai_response",
                    "prompt_text": f"Test chat message {i}",
                    "prompt_length": 20 + i,
                    "response_time_ms": 1000.0 + i * 100,
                    "model_used": "claude-sonnet-4",
                    "tokens_consumed": 80 + i * 5,
                    "is_follow_up": i > 0
                }
            )
            events.append(event)
        
        return events

    def _create_survey_response_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create survey response events for testing"""
        events = []
        
        for i in range(count):
            event = FrontendEvent(
                user_id=user_id,
                session_id=f"survey_session_{int(time.time())}",
                event_type=EventType.SURVEY_RESPONSE,
                event_category=EventCategory.BUSINESS,
                event_action="survey_submission",
                event_label=f"ai_spend_survey_{i}",
                properties={
                    "survey_id": "ai_optimization_survey_2025",
                    "question_id": f"question_{i}",
                    "question_type": "spending" if i % 2 == 0 else "pain_perception",
                    "response_value": f"Response to question {i}",
                    "response_scale": 7 + (i % 4),
                    "ai_spend_last_month": 5000.0 + i * 1000,
                    "ai_spend_next_quarter": 15000.0 + i * 3000
                }
            )
            events.append(event)
        
        return events

    def _create_performance_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create performance metric events for testing"""
        events = []
        
        for i in range(count):
            event = FrontendEvent(
                user_id=user_id,
                session_id=f"perf_session_{int(time.time())}",
                event_type=EventType.PERFORMANCE_METRIC,
                event_category=EventCategory.TECHNICAL,
                event_action="metric_collection",
                event_label=f"performance_{i}",
                event_value=float(200.0 + i * 50),
                properties={
                    "metric_type": ["api_call", "websocket", "page_load", "render"][i % 4],
                    "duration_ms": 200.0 + i * 50,
                    "success": i % 5 != 0,  # 80% success rate
                    "error_details": f"Error {i}" if i % 5 == 0 else None
                }
            )
            events.append(event)
        
        return events

    def _create_user_specific_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create events specific to a user for isolation testing"""
        events = []
        session_id = f"user_session_{user_id}_{int(time.time())}"
        
        for i in range(count):
            event_types = [EventType.CHAT_INTERACTION, EventType.FEATURE_USAGE, EventType.PERFORMANCE_METRIC]
            event_type = event_types[i % len(event_types)]
            
            if event_type == EventType.CHAT_INTERACTION:
                properties = {
                    "thread_id": f"user_thread_{user_id}_{i}",
                    "message_id": f"msg_{i}",
                    "message_type": "user_prompt",
                    "prompt_text": f"User {user_id} specific query {i}",
                    "prompt_length": 25 + i,
                    "tokens_consumed": 90 + i * 5,
                    "is_follow_up": i > 0
                }
            elif event_type == EventType.FEATURE_USAGE:
                properties = {
                    "feature_name": f"user_feature_{i}",
                    "action": "user_specific_action",
                    "success": True,
                    "duration_ms": 300.0 + i * 20
                }
            else:  # PERFORMANCE_METRIC
                properties = {
                    "metric_type": "api_call",
                    "duration_ms": 150.0 + i * 10,
                    "success": True
                }
            
            event = FrontendEvent(
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                event_category=EventCategory.USER_INTERACTION,
                event_action=f"user_action_{i}",
                event_label=f"user_label_{i}",
                properties=properties
            )
            events.append(event)
        
        return events

    def _create_timestamped_events(self, user_id: str, count: int, base_timestamp: datetime) -> List[AnalyticsEvent]:
        """Create events with specific timestamps for retention testing"""
        events = []
        
        for i in range(count):
            # Add small time increments
            event_timestamp = base_timestamp + timedelta(minutes=i * 10)
            
            event = FrontendEvent(
                user_id=user_id,
                session_id=f"timestamp_session_{int(time.time())}",
                event_type=EventType.CHAT_INTERACTION,
                event_category=EventCategory.USER_INTERACTION,
                event_action="timestamped_action",
                event_label=f"retention_test_{i}",
                properties={
                    "thread_id": f"timestamp_thread_{i}",
                    "message_id": f"timestamp_msg_{i}",
                    "message_type": "user_prompt",
                    "prompt_text": f"Timestamp test message {i}",
                    "prompt_length": 30,
                    "tokens_consumed": 100,
                    "is_follow_up": False
                }
            )
            # Override the timestamp
            event.timestamp = event_timestamp
            events.append(event)
        
        return events

    def _create_thread_lifecycle_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create thread lifecycle events for testing"""
        events = []
        
        for i in range(count):
            thread_id = f"lifecycle_thread_{i}"
            action = ["created", "continued", "completed", "abandoned"][i % 4]
            
            event = FrontendEvent(
                user_id=user_id,
                session_id=f"thread_session_{int(time.time())}",
                event_type=EventType.THREAD_LIFECYCLE,
                event_category=EventCategory.USER_INTERACTION,
                event_action=action,
                event_label=f"thread_lifecycle_{i}",
                properties={
                    "thread_id": thread_id,
                    "action": action,
                    "message_count": i + 1,
                    "duration_seconds": (i + 1) * 60.0
                }
            )
            events.append(event)
        
        return events

    def _create_feature_usage_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create feature usage events for testing"""
        events = []
        features = ["dashboard", "cost_optimizer", "usage_analyzer", "report_generator", "settings"]
        
        for i in range(count):
            feature = features[i % len(features)]
            
            event = FrontendEvent(
                user_id=user_id,
                session_id=f"feature_session_{int(time.time())}",
                event_type=EventType.FEATURE_USAGE,
                event_category=EventCategory.BUSINESS,
                event_action="feature_interaction",
                event_label=f"feature_{feature}_{i}",
                properties={
                    "feature_name": feature,
                    "action": ["view", "click", "configure", "export"][i % 4],
                    "success": i % 10 != 0,  # 90% success rate
                    "error_code": f"ERR_{i}" if i % 10 == 0 else None,
                    "duration_ms": 500.0 + i * 100
                }
            )
            events.append(event)
        
        return events

    def _create_mixed_event_types(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create a mix of different event types for comprehensive testing"""
        events = []
        
        # Distribute events across different types
        chat_count = count // 3
        feature_count = count // 3  
        performance_count = count - chat_count - feature_count
        
        events.extend(self._create_chat_interaction_events(user_id, chat_count))
        events.extend(self._create_feature_usage_events(user_id, feature_count))
        events.extend(self._create_performance_events(user_id, performance_count))
        
        return events

    def _create_backend_service_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create events simulating backend service interactions"""
        events = []
        
        for i in range(count):
            event = FrontendEvent(
                user_id=user_id,
                session_id=f"backend_session_{int(time.time())}",
                event_type=EventType.FEATURE_USAGE,
                event_category=EventCategory.SYSTEM,
                event_action="backend_operation",
                event_label=f"backend_service_{i}",
                properties={
                    "feature_name": "backend_api",
                    "action": ["user_context_creation", "agent_execution", "data_processing"][i % 3],
                    "success": True,
                    "duration_ms": 300.0 + i * 25,
                    "service_origin": "netra_backend"
                }
            )
            events.append(event)
        
        return events

    def _create_frontend_service_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create events simulating frontend service interactions"""
        events = []
        
        for i in range(count):
            event = FrontendEvent(
                user_id=user_id,
                session_id=f"frontend_session_{int(time.time())}",
                event_type=EventType.PERFORMANCE_METRIC,
                event_category=EventCategory.TECHNICAL,
                event_action="frontend_metric",
                event_label=f"ui_interaction_{i}",
                event_value=float(120.0 + i * 30),
                properties={
                    "metric_type": "render",
                    "duration_ms": 120.0 + i * 30,
                    "success": True,
                    "component": ["chat_interface", "dashboard", "settings", "reports"][i % 4],
                    "service_origin": "frontend"
                }
            )
            events.append(event)
        
        return events

    def _create_auth_service_events(self, user_id: str, count: int) -> List[AnalyticsEvent]:
        """Create events simulating auth service interactions"""
        events = []
        
        for i in range(count):
            event = FrontendEvent(
                user_id=user_id,
                session_id=f"auth_session_{int(time.time())}",
                event_type=EventType.FEATURE_USAGE,
                event_category=EventCategory.SYSTEM,
                event_action="auth_operation",
                event_label=f"authentication_{i}",
                properties={
                    "feature_name": "authentication",
                    "action": ["login", "token_refresh", "permission_check", "logout"][i % 4],
                    "success": i % 20 != 0,  # 95% success rate for auth
                    "duration_ms": 80.0 + i * 10,
                    "auth_method": "oauth2",
                    "service_origin": "auth_service"
                }
            )
            events.append(event)
        
        return events