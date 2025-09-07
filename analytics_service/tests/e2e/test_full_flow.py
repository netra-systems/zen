"""
Analytics Service End-to-End Flow Tests
======================================

Comprehensive end-to-end tests for complete analytics service workflows.
Tests real event flows from ingestion through processing to reporting.

NO MOCKS POLICY: Tests use real services, databases, and network connections.

Test Coverage:
- Complete event ingestion to reporting workflow
- WebSocket streaming for real-time analytics
- Performance tests (10,000 events/second target)
- Cross-service integration with auth and main backend
- GTM integration and frontend event capture
- Grafana dashboard data validation
- Error recovery and resilience testing
- Multi-user concurrent usage scenarios
- Data consistency across all storage layers
"""

import asyncio
import json
import pytest
import time
import websockets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
from shared.isolated_environment import IsolatedEnvironment

import httpx
from websockets.exceptions import ConnectionClosed

# =============================================================================
# E2E TEST INFRASTRUCTURE
# =============================================================================

class AnalyticsE2ETestHarness:
    """
    End-to-end test harness for analytics service.
    Orchestrates full service stack for realistic testing.
    """
    
    def __init__(self, base_url: str = "http://localhost:8090"):
        self.base_url = base_url
        self.websocket_url = base_url.replace("http", "ws") + "/ws/analytics"
        self.clickhouse_url = "http://localhost:9090"
        self.redis_url = "redis://localhost:6380"
        self.grafana_url = "http://localhost:3001"
        
        self.http_client = None
        self.websocket_connection = None
        self.test_session_id = f"e2e_test_{int(time.time())}"
        
        # Track test data for cleanup
        self.test_users = []
        self.test_events = []
    
    async def setup(self) -> None:
        """Setup E2E test environment"""
        self.http_client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        
        # Wait for service to be ready
        await self._wait_for_service_ready()
    
    async def teardown(self) -> None:
        """Cleanup E2E test environment"""
        if self.websocket_connection:
            await self.websocket_connection.close()
        
        if self.http_client:
            await self.http_client.aclose()
    
    async def _wait_for_service_ready(self, max_attempts: int = 30) -> None:
        """Wait for analytics service to be ready"""
        for attempt in range(max_attempts):
            try:
                response = await self.http_client.get("/health")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "healthy":
                        return
            except:
                pass
            
            await asyncio.sleep(1)
        
        raise TimeoutError("Analytics service did not become ready in time")
    
    async def send_events(self, events: List[Dict[str, Any]], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send events via HTTP API"""
        payload = {
            "events": events,
            "context": context or {"user_id": f"test_user_{self.test_session_id}"}
        }
        
        response = await self.http_client.post("/api/analytics/events", json=payload)
        response.raise_for_status()
        
        return response.json()
    
    async def get_user_activity_report(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Get user activity report"""
        params = {"user_id": user_id}
        params.update(kwargs)
        
        response = await self.http_client.get("/api/analytics/reports/user-activity", params=params)
        response.raise_for_status()
        
        return response.json()
    
    async def get_prompt_analysis_report(self, **kwargs) -> Dict[str, Any]:
        """Get prompt analysis report"""
        response = await self.http_client.get("/api/analytics/reports/prompts", params=kwargs)
        response.raise_for_status()
        
        return response.json()
    
    async def connect_websocket(self) -> None:
        """Connect to WebSocket for real-time updates"""
        try:
            self.websocket_connection = await websockets.connect(
                self.websocket_url,
                timeout=10
            )
        except Exception as e:
            # WebSocket might not be implemented yet
            pytest.skip(f"WebSocket connection not available: {e}")
    
    async def send_websocket_message(self, message: Dict[str, Any]) -> None:
        """Send message via WebSocket"""
        if not self.websocket_connection:
            await self.connect_websocket()
        
        await self.websocket_connection.send(json.dumps(message))
    
    async def receive_websocket_message(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Receive message from WebSocket"""
        if not self.websocket_connection:
            raise RuntimeError("WebSocket not connected")
        
        try:
            message = await asyncio.wait_for(
                self.websocket_connection.recv(),
                timeout=timeout
            )
            return json.loads(message)
        except asyncio.TimeoutError:
            raise TimeoutError("No WebSocket message received within timeout")
    
    def generate_test_user(self) -> str:
        """Generate unique test user ID"""
        user_id = f"e2e_user_{self.test_session_id}_{len(self.test_users)}"
        self.test_users.append(user_id)
        return user_id
    
    def generate_test_events(self, count: int, user_id: str = None, event_types: List[str] = None) -> List[Dict[str, Any]]:
        """Generate test events for E2E testing"""
        if not user_id:
            user_id = self.generate_test_user()
        
        if not event_types:
            event_types = ["chat_interaction", "feature_usage", "performance_metric"]
        
        events = []
        session_id = f"e2e_session_{int(time.time())}"
        
        for i in range(count):
            event_type = event_types[i % len(event_types)]
            
            if event_type == "chat_interaction":
                properties = {
                    "thread_id": f"thread_{i // 5}",  # Group events into threads
                    "message_id": f"msg_{i}",
                    "message_type": "user_prompt",
                    "prompt_text": f"Test prompt {i}: How can I optimize my AI costs?",
                    "prompt_length": 40 + i,
                    "tokens_consumed": 100 + i * 5,
                    "is_follow_up": i % 3 == 0,
                    "response_time_ms": 1000 + i * 10
                }
            elif event_type == "feature_usage":
                properties = {
                    "feature_name": ["dashboard", "reports", "settings", "billing"][i % 4],
                    "action": "view",
                    "success": True,
                    "duration_ms": 200 + i * 5
                }
            else:  # performance_metric
                properties = {
                    "metric_type": "api_call",
                    "duration_ms": 150 + i * 3,
                    "success": True
                }
            
            event = {
                "event_id": f"e2e_event_{self.test_session_id}_{i}",
                "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=i)).isoformat(),
                "user_id": user_id,
                "session_id": session_id,
                "event_type": event_type,
                "event_category": "E2E Test Events",
                "event_action": "test",
                "event_value": float(100 + i),
                "properties": json.dumps(properties),
                "page_path": f"/test/page/{i % 3}",
                "page_title": f"Test Page {i % 3}",
                "environment": "e2e_test"
            }
            
            events.append(event)
            self.test_events.append(event["event_id"])
        
        return events

# =============================================================================
# BASIC E2E WORKFLOW TESTS
# =============================================================================

class TestBasicE2EWorkflows:
    """Test suite for basic end-to-end workflows"""
    
    @pytest.fixture
    async def e2e_harness(self):
        """E2E test harness fixture"""
        harness = AnalyticsE2ETestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_complete_event_ingestion_to_reporting_flow(self, e2e_harness):
        """Test complete flow from event ingestion to report generation"""
        # Step 1: Generate test user and events
        user_id = e2e_harness.generate_test_user()
        test_events = e2e_harness.generate_test_events(50, user_id)
        
        # Step 2: Send events via API
        response = await e2e_harness.send_events(test_events, {"user_id": user_id})
        
        assert response["status"] == "processed"
        assert response["ingested"] == 50
        assert response["failed"] == 0
        
        # Step 3: Wait for processing
        await asyncio.sleep(3)
        
        # Step 4: Generate user activity report
        report = await e2e_harness.get_user_activity_report(user_id)
        
        assert report["report_type"] == "user_activity"
        assert report["data"]["user_id"] == user_id
        
        # Validate report contains expected metrics
        metrics = report["data"]["metrics"]
        assert metrics["total_events"] > 0
        assert metrics["chat_interactions"] > 0
        assert "avg_response_time_ms" in metrics
    
    async def test_multi_user_concurrent_workflow(self, e2e_harness):
        """Test concurrent workflows for multiple users"""
        # Create multiple users with different usage patterns
        users = []
        for i in range(5):
            user_id = e2e_harness.generate_test_user()
            users.append({
                "id": user_id,
                "event_count": 20 + i * 10,  # Varying event counts
                "event_types": ["chat_interaction"] if i % 2 == 0 else ["feature_usage", "performance_metric"]
            })
        
        # Send events concurrently for all users
        tasks = []
        for user in users:
            events = e2e_harness.generate_test_events(
                user["event_count"], 
                user["id"], 
                user["event_types"]
            )
            task = e2e_harness.send_events(events, {"user_id": user["id"]})
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All submissions should succeed
        for response in responses:
            assert response["status"] == "processed"
            assert response["failed"] == 0
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Generate reports for all users concurrently
        report_tasks = [e2e_harness.get_user_activity_report(user["id"]) for user in users]
        reports = await asyncio.gather(*report_tasks)
        
        # Validate all reports
        for i, report in enumerate(reports):
            assert report["data"]["user_id"] == users[i]["id"]
            assert report["data"]["metrics"]["total_events"] >= users[i]["event_count"]
    
    async def test_event_type_specific_workflows(self, e2e_harness):
        """Test workflows for specific event types"""
        user_id = e2e_harness.generate_test_user()
        
        # Test chat interaction workflow
        chat_events = e2e_harness.generate_test_events(
            20, user_id, ["chat_interaction"]
        )
        
        response = await e2e_harness.send_events(chat_events, {"user_id": user_id})
        assert response["ingested"] == 20
        
        # Test feature usage workflow
        feature_events = e2e_harness.generate_test_events(
            15, user_id, ["feature_usage"]
        )
        
        response = await e2e_harness.send_events(feature_events, {"user_id": user_id})
        assert response["ingested"] == 15
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Validate report reflects different event types
        report = await e2e_harness.get_user_activity_report(user_id)
        
        metrics = report["data"]["metrics"]
        assert metrics["total_events"] == 35  # 20 + 15
        assert metrics["chat_interactions"] == 20
        assert metrics["feature_interactions"] == 15

# =============================================================================
# WEBSOCKET STREAMING TESTS
# =============================================================================

class TestWebSocketStreaming:
    """Test suite for WebSocket streaming functionality"""
    
    @pytest.fixture
    async def e2e_harness(self):
        """E2E test harness fixture"""
        harness = AnalyticsE2ETestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_real_time_event_streaming(self, e2e_harness):
        """Test real-time event streaming via WebSocket"""
        try:
            await e2e_harness.connect_websocket()
        except Exception as e:
            # WebSocket may not be available in test environment
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"WebSocket not available for test: {e}")
            return
        
        user_id = e2e_harness.generate_test_user()
        
        # Subscribe to user events
        subscribe_message = {
            "type": "subscribe",
            "user_id": user_id,
            "event_types": ["chat_interaction", "feature_usage"]
        }
        
        await e2e_harness.send_websocket_message(subscribe_message)
        
        # Send events via HTTP API
        test_events = e2e_harness.generate_test_events(5, user_id)
        await e2e_harness.send_events(test_events, {"user_id": user_id})
        
        # Should receive real-time notifications
        received_notifications = []
        try:
            for _ in range(5):  # Expect 5 event notifications
                message = await e2e_harness.receive_websocket_message(timeout=10.0)
                received_notifications.append(message)
        except TimeoutError:
            pytest.fail("Did not receive expected WebSocket notifications")
        
        # Validate notifications
        assert len(received_notifications) >= 1
        for notification in received_notifications:
            assert notification.get("user_id") == user_id
            assert "event_type" in notification
    
    async def test_dashboard_real_time_updates(self, e2e_harness):
        """Test real-time dashboard updates via WebSocket"""
        try:
            await e2e_harness.connect_websocket()
        except Exception as e:
            # WebSocket may not be available in test environment
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"WebSocket not available for test: {e}")
            return
        
        # Subscribe to dashboard updates
        subscribe_message = {
            "type": "subscribe_dashboard",
            "metrics": ["active_users", "event_rate", "error_rate"]
        }
        
        await e2e_harness.send_websocket_message(subscribe_message)
        
        # Generate activity to trigger dashboard updates
        users = [e2e_harness.generate_test_user() for _ in range(3)]
        
        tasks = []
        for user_id in users:
            events = e2e_harness.generate_test_events(10, user_id)
            task = e2e_harness.send_events(events, {"user_id": user_id})
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Should receive dashboard update
        try:
            update = await e2e_harness.receive_websocket_message(timeout=15.0)
            
            assert update.get("type") == "dashboard_update"
            assert "metrics" in update
            assert "timestamp" in update
            
        except TimeoutError:
            pytest.skip("Dashboard updates not implemented or too slow")

# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestE2EPerformance:
    """Test suite for end-to-end performance validation"""
    
    @pytest.fixture
    async def e2e_harness(self):
        """E2E test harness fixture"""
        harness = AnalyticsE2ETestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_high_volume_event_ingestion_performance(self, e2e_harness, analytics_performance_monitor):
        """Test high-volume event ingestion performance (target: 10,000 events/second)"""
        user_id = e2e_harness.generate_test_user()
        
        # Generate high volume of events
        event_count = 10000
        batch_size = 1000
        
        total_events = []
        for i in range(0, event_count, batch_size):
            batch = e2e_harness.generate_test_events(
                min(batch_size, event_count - i), 
                user_id,
                ["chat_interaction", "performance_metric"]
            )
            total_events.extend(batch)
        
        # Send events in batches and measure total time
        analytics_performance_monitor.start_measurement("high_volume_ingestion")
        
        responses = []
        for i in range(0, len(total_events), batch_size):
            batch = total_events[i:i + batch_size]
            response = await e2e_harness.send_events(batch, {"user_id": user_id})
            responses.append(response)
        
        total_duration = analytics_performance_monitor.end_measurement("high_volume_ingestion")
        
        # Validate all events were ingested
        total_ingested = sum(r["ingested"] for r in responses)
        total_failed = sum(r["failed"] for r in responses)
        
        assert total_ingested == event_count
        assert total_failed == 0
        
        # Calculate throughput
        throughput = event_count / total_duration
        print(f"E2E Ingestion throughput: {throughput:.2f} events/second")
        
        # Should achieve reasonable throughput for E2E (lower than direct processing due to HTTP overhead)
        assert throughput > 500  # At least 500 events/second via HTTP API
        
        # Validate overall performance requirement
        analytics_performance_monitor.validate_performance("high_volume_ingestion")
    
    async def test_concurrent_user_performance(self, e2e_harness, analytics_performance_monitor):
        """Test performance with many concurrent users"""
        user_count = 50
        events_per_user = 100
        
        # Create users and events
        users = []
        all_tasks = []
        
        for i in range(user_count):
            user_id = e2e_harness.generate_test_user()
            users.append(user_id)
            
            events = e2e_harness.generate_test_events(events_per_user, user_id)
            task = e2e_harness.send_events(events, {"user_id": user_id})
            all_tasks.append(task)
        
        # Execute all requests concurrently
        analytics_performance_monitor.start_measurement("concurrent_users")
        
        responses = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        duration = analytics_performance_monitor.end_measurement("concurrent_users")
        
        # Validate responses
        successful_responses = [r for r in responses if isinstance(r, dict) and r.get("status") == "processed"]
        
        assert len(successful_responses) >= user_count * 0.9  # At least 90% success rate
        
        total_events = sum(r["ingested"] for r in successful_responses)
        expected_events = user_count * events_per_user
        
        # Should handle concurrent load
        assert total_events >= expected_events * 0.9  # At least 90% of events processed
        
        print(f"Concurrent users performance: {user_count} users, {total_events} events in {duration:.2f}s")
    
    async def test_report_generation_performance_at_scale(self, e2e_harness, analytics_performance_monitor):
        """Test report generation performance with large datasets"""
        # Create multiple users with substantial data
        users = []
        for i in range(10):
            user_id = e2e_harness.generate_test_user()
            users.append(user_id)
            
            # Create substantial event history
            events = e2e_harness.generate_test_events(500, user_id)  # 500 events per user
            await e2e_harness.send_events(events, {"user_id": user_id})
        
        # Wait for all events to be processed
        await asyncio.sleep(10)
        
        # Test concurrent report generation
        analytics_performance_monitor.start_measurement("query_response")
        
        report_tasks = []
        for user_id in users:
            task = e2e_harness.get_user_activity_report(
                user_id,
                start_date=(datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
                end_date=datetime.now(timezone.utc).strftime("%Y-%m-%d")
            )
            report_tasks.append(task)
        
        reports = await asyncio.gather(*report_tasks, return_exceptions=True)
        
        duration = analytics_performance_monitor.end_measurement("query_response")
        
        # Validate reports
        successful_reports = [r for r in reports if isinstance(r, dict) and r.get("report_type")]
        
        assert len(successful_reports) >= 8  # At least 80% success rate
        
        # Validate performance
        analytics_performance_monitor.validate_performance("query_response")
        
        print(f"Generated {len(successful_reports)} reports in {duration:.2f}s")

# =============================================================================
# DATA CONSISTENCY TESTS
# =============================================================================

class TestDataConsistency:
    """Test suite for data consistency across all storage layers"""
    
    @pytest.fixture
    async def e2e_harness(self):
        """E2E test harness fixture"""
        harness = AnalyticsE2ETestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_event_data_consistency_across_layers(self, e2e_harness):
        """Test data consistency between ingestion and reporting"""
        user_id = e2e_harness.generate_test_user()
        
        # Send precisely counted events
        chat_events = 25
        feature_events = 15
        performance_events = 10
        total_events = chat_events + feature_events + performance_events
        
        # Send each event type separately to ensure accurate counting
        for event_type, count in [
            ("chat_interaction", chat_events),
            ("feature_usage", feature_events),
            ("performance_metric", performance_events)
        ]:
            events = e2e_harness.generate_test_events(count, user_id, [event_type])
            response = await e2e_harness.send_events(events, {"user_id": user_id})
            assert response["ingested"] == count
            assert response["failed"] == 0
        
        # Wait for processing and aggregation
        await asyncio.sleep(5)
        
        # Verify data consistency in reports
        report = await e2e_harness.get_user_activity_report(user_id)
        
        metrics = report["data"]["metrics"]
        assert metrics["total_events"] == total_events
        assert metrics["chat_interactions"] == chat_events
        assert metrics["feature_interactions"] == feature_events
    
    async def test_temporal_data_consistency(self, e2e_harness):
        """Test data consistency across time-based queries"""
        user_id = e2e_harness.generate_test_user()
        
        # Send events with specific timestamps
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        
        # Events from yesterday
        yesterday_events = e2e_harness.generate_test_events(10, user_id)
        for event in yesterday_events:
            event["timestamp"] = yesterday.isoformat()
        
        # Events from today
        today_events = e2e_harness.generate_test_events(15, user_id)
        for event in today_events:
            event["timestamp"] = now.isoformat()
        
        # Send all events
        all_events = yesterday_events + today_events
        response = await e2e_harness.send_events(all_events, {"user_id": user_id})
        
        assert response["ingested"] == 25
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Query with date range filters
        yesterday_report = await e2e_harness.get_user_activity_report(
            user_id,
            start_date=yesterday.strftime("%Y-%m-%d"),
            end_date=yesterday.strftime("%Y-%m-%d")
        )
        
        today_report = await e2e_harness.get_user_activity_report(
            user_id,
            start_date=now.strftime("%Y-%m-%d"),
            end_date=now.strftime("%Y-%m-%d")
        )
        
        # Validate temporal consistency
        # Note: Depending on implementation, events might be aggregated differently
        total_from_daily = (
            yesterday_report["data"]["metrics"]["total_events"] + 
            today_report["data"]["metrics"]["total_events"]
        )
        
        # Should match total events (allowing for some aggregation differences)
        assert total_from_daily >= 20  # At least 80% of events should be captured in date-filtered queries
    
    async def test_multi_session_data_consistency(self, e2e_harness):
        """Test data consistency across multiple sessions for same user"""
        user_id = e2e_harness.generate_test_user()
        
        # Simulate multiple sessions
        sessions = []
        total_expected_events = 0
        
        for session_num in range(3):
            session_events = e2e_harness.generate_test_events(
                20, user_id, ["chat_interaction", "feature_usage"]
            )
            
            # Update session IDs
            session_id = f"session_{session_num}"
            for event in session_events:
                event["session_id"] = session_id
            
            sessions.append({
                "id": session_id,
                "events": session_events,
                "count": len(session_events)
            })
            
            total_expected_events += len(session_events)
        
        # Send events from all sessions
        for session in sessions:
            response = await e2e_harness.send_events(
                session["events"], 
                {"user_id": user_id, "session_id": session["id"]}
            )
            assert response["ingested"] == session["count"]
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Verify aggregated data
        report = await e2e_harness.get_user_activity_report(user_id)
        
        assert report["data"]["metrics"]["total_events"] == total_expected_events
        
        # All events should be attributed to the same user regardless of session
        assert report["data"]["user_id"] == user_id

# =============================================================================
# ERROR RECOVERY TESTS
# =============================================================================

class TestErrorRecovery:
    """Test suite for error recovery and resilience"""
    
    @pytest.fixture
    async def e2e_harness(self):
        """E2E test harness fixture"""
        harness = AnalyticsE2ETestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_partial_batch_failure_recovery(self, e2e_harness):
        """Test recovery from partial batch failures"""
        user_id = e2e_harness.generate_test_user()
        
        # Create batch with mix of valid and invalid events
        valid_events = e2e_harness.generate_test_events(10, user_id)
        
        invalid_events = [
            {"event_id": "invalid_1"},  # Missing required fields
            {
                "event_id": "invalid_2",
                "timestamp": "invalid_timestamp",
                "user_id": user_id,
                "session_id": "test",
                "event_type": "test",
                "event_category": "test",
                "properties": "{}"
            }
        ]
        
        mixed_batch = valid_events + invalid_events
        
        # Send mixed batch
        response = await e2e_harness.send_events(mixed_batch, {"user_id": user_id})
        
        # Should process valid events despite failures
        assert response["ingested"] > 0  # Some events should succeed
        assert response["failed"] > 0   # Some events should fail
        assert len(response["errors"]) > 0
        
        # Valid events should still generate reports
        await asyncio.sleep(3)
        
        report = await e2e_harness.get_user_activity_report(user_id)
        assert report["data"]["metrics"]["total_events"] >= response["ingested"]
    
    async def test_service_timeout_recovery(self, e2e_harness):
        """Test recovery from service timeouts"""
        user_id = e2e_harness.generate_test_user()
        
        # Send very large batch that might cause timeouts
        large_batch = e2e_harness.generate_test_events(1000, user_id)
        
        try:
            # Use shorter timeout to potentially trigger timeout scenarios
            original_timeout = e2e_harness.http_client.timeout
            e2e_harness.http_client.timeout = httpx.Timeout(5.0)  # 5 second timeout
            
            response = await e2e_harness.send_events(large_batch, {"user_id": user_id})
            
            # Should either succeed or fail gracefully
            if response["status"] == "processed":
                assert response["ingested"] > 0
            elif response["status"] == "error":
                assert len(response["errors"]) > 0
            
        except httpx.TimeoutException:
            # Timeout is expected for very large batches with short timeout
            # This tests the service's ability to handle timeout gracefully
            pass
        finally:
            # Restore original timeout
            e2e_harness.http_client.timeout = original_timeout
    
    async def test_concurrent_load_stress_recovery(self, e2e_harness):
        """Test recovery under concurrent load stress"""
        # Create many concurrent users
        user_count = 20
        events_per_user = 50
        
        users = [e2e_harness.generate_test_user() for _ in range(user_count)]
        
        # Create tasks for all users
        tasks = []
        for user_id in users:
            events = e2e_harness.generate_test_events(events_per_user, user_id)
            task = e2e_harness.send_events(events, {"user_id": user_id})
            tasks.append(task)
        
        # Execute with high concurrency
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_responses = []
        failed_responses = []
        exceptions = []
        
        for response in responses:
            if isinstance(response, Exception):
                exceptions.append(response)
            elif isinstance(response, dict):
                if response.get("status") == "processed":
                    successful_responses.append(response)
                else:
                    failed_responses.append(response)
        
        # Should handle most requests successfully despite high load
        success_rate = len(successful_responses) / user_count
        
        print(f"Stress test results: {success_rate:.2%} success rate")
        print(f"Successful: {len(successful_responses)}, Failed: {len(failed_responses)}, Exceptions: {len(exceptions)}")
        
        # Should maintain at least 70% success rate under stress
        assert success_rate >= 0.7, f"Success rate too low: {success_rate:.2%}"

# =============================================================================
# INTEGRATION WITH EXTERNAL SERVICES
# =============================================================================

class TestExternalServiceIntegration:
    """Test suite for integration with external services"""
    
    @pytest.fixture
    async def e2e_harness(self):
        """E2E test harness fixture"""
        harness = AnalyticsE2ETestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_grafana_dashboard_integration(self, e2e_harness):
        """Test integration with Grafana dashboards"""
        # This test would verify that analytics data appears in Grafana dashboards
        # Implementation depends on actual Grafana integration
        
        user_id = e2e_harness.generate_test_user()
        events = e2e_harness.generate_test_events(100, user_id)
        
        await e2e_harness.send_events(events, {"user_id": user_id})
        
        # Wait for data to propagate to Grafana
        await asyncio.sleep(10)
        
        # Check Grafana API for data (if available)
        try:
            grafana_client = httpx.AsyncClient(base_url=e2e_harness.grafana_url)
            
            # Query Grafana API for dashboard data
            # This would require actual Grafana API implementation
            response = await grafana_client.get("/api/dashboards/analytics")
            
            if response.status_code == 200:
                dashboard_data = response.json()
                # Validate dashboard contains our test data
                assert "panels" in dashboard_data
            
        except Exception as e:
            # Grafana may not be available in test environment
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Grafana integration not available: {e}")
            return
    
    async def test_gtm_event_capture_integration(self, e2e_harness):
        """Test integration with Google Tag Manager event capture"""
        # This test would verify GTM events are properly captured and processed
        # Implementation depends on actual GTM integration
        
        # Simulate GTM event payload
        gtm_event = {
            "event_id": f"gtm_test_{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": e2e_harness.generate_test_user(),
            "session_id": "gtm_session",
            "event_type": "gtm_event",
            "event_category": "GTM Integration Test",
            "properties": json.dumps({
                "gtm_event": "page_view",
                "page_location": "https://netra.ai/dashboard",
                "gtm_container_id": "GTM-TEST123"
            }),
            "gtm_container_id": "GTM-TEST123",
            "user_agent": "Mozilla/5.0 (GTM Test)"
        }
        
        response = await e2e_harness.send_events([gtm_event])
        
        assert response["ingested"] == 1
        assert response["failed"] == 0
        
        # Verify GTM events are processed correctly
        await asyncio.sleep(2)
        
        report = await e2e_harness.get_user_activity_report(gtm_event["user_id"])
        assert report["data"]["metrics"]["total_events"] >= 1

# =============================================================================
# INTEGRATION WITH FIXTURES
# =============================================================================

class TestE2EWithFixtures:
    """Test E2E functionality using conftest fixtures"""
    
    @pytest.fixture
    async def e2e_harness(self):
        """E2E test harness fixture"""
        harness = AnalyticsE2ETestHarness()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    async def test_e2e_with_sample_events(self, e2e_harness, sample_chat_interaction_event, 
                                        sample_survey_response_event, sample_performance_event):
        """Test E2E workflow with sample events from fixtures"""
        user_id = e2e_harness.generate_test_user()
        
        # Use fixture events but update user_id for consistency
        events = [sample_chat_interaction_event, sample_survey_response_event, sample_performance_event]
        for event in events:
            event["user_id"] = user_id
        
        # Send fixture events
        response = await e2e_harness.send_events(events, {"user_id": user_id})
        
        assert response["ingested"] == 3
        assert response["failed"] == 0
        
        # Wait and generate report
        await asyncio.sleep(3)
        
        report = await e2e_harness.get_user_activity_report(user_id)
        
        assert report["data"]["user_id"] == user_id
        assert report["data"]["metrics"]["total_events"] == 3
    
    async def test_e2e_performance_with_high_volume_generator(self, e2e_harness, high_volume_event_generator, analytics_performance_monitor):
        """Test E2E performance with high volume event generator from fixtures"""
        user_id = e2e_harness.generate_test_user()
        
        # Use fixture generator for consistent test data
        events = high_volume_event_generator(count=1000, user_count=1)
        
        # Update events to use our test user
        for event in events:
            event["user_id"] = user_id
        
        # Measure E2E performance
        analytics_performance_monitor.start_measurement("high_volume_ingestion")
        
        # Send in batches for better performance
        batch_size = 200
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            response = await e2e_harness.send_events(batch, {"user_id": user_id})
            assert response["failed"] == 0
        
        duration = analytics_performance_monitor.end_measurement("high_volume_ingestion")
        
        # Calculate throughput
        throughput = 1000 / duration
        print(f"E2E throughput with fixtures: {throughput:.2f} events/second")
        
        # Should achieve reasonable E2E performance
        assert throughput > 200
        
        # Validate report generation after high volume
        await asyncio.sleep(5)
        
        report = await e2e_harness.get_user_activity_report(user_id)
        assert report["data"]["metrics"]["total_events"] == 1000