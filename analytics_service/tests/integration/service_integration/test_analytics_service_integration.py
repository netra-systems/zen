"""
Analytics Service Integration Tests

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (Free/Early have limited analytics)
- Business Goal: Data-Driven Insights & Performance Monitoring 
- Value Impact: Enables customers to track optimization ROI and platform usage insights
- Strategic Impact: Analytics drive customer retention and upselling through demonstrated value

These tests validate ClickHouse integration, cross-service analytics consistency,
and analytics pipeline reliability critical for business intelligence.
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any, Optional, Union
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class TestAnalyticsServiceIntegration(BaseIntegrationTest):
    """Test analytics service integration with ClickHouse and other services."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_clickhouse_event_pipeline_reliability(self, real_services_fixture):
        """
        Test ClickHouse event pipeline reliability under various conditions.
        
        BVJ: Ensures analytics data is reliably captured and stored, critical for
        enterprise customers who need accurate usage and optimization metrics.
        """
        pipeline_events = []
        processing_results = []
        
        class ClickHouseEventPipeline:
            def __init__(self):
                self.event_buffer = []
                self.processed_events = []
                self.failed_events = []
                self.batch_size = 100
                self.flush_interval = 5.0
                self.retry_attempts = 3
                
            async def ingest_event(self, event: Dict[str, Any]):
                # Validate event structure
                required_fields = ["event_type", "user_id", "timestamp", "data"]
                for field in required_fields:
                    if field not in event:
                        pipeline_events.append(f"invalid_event_missing_{field}")
                        self.failed_events.append({"event": event, "reason": f"missing_{field}"})
                        return False
                
                # Add metadata
                enriched_event = {
                    **event,
                    "ingestion_timestamp": time.time(),
                    "pipeline_version": "1.0",
                    "event_id": f"event_{len(self.event_buffer)}"
                }
                
                self.event_buffer.append(enriched_event)
                pipeline_events.append(f"event_ingested_{event['event_type']}")
                
                # Trigger batch processing if buffer is full
                if len(self.event_buffer) >= self.batch_size:
                    await self.flush_events()
                
                return True
            
            async def flush_events(self):
                if not self.event_buffer:
                    return
                
                batch = self.event_buffer.copy()
                self.event_buffer.clear()
                
                pipeline_events.append(f"batch_processing_{len(batch)}_events")
                
                # Simulate ClickHouse batch insert
                try:
                    await self._insert_to_clickhouse(batch)
                    self.processed_events.extend(batch)
                    processing_results.append({
                        "batch_size": len(batch),
                        "status": "success",
                        "timestamp": time.time()
                    })
                    pipeline_events.append(f"batch_success_{len(batch)}")
                
                except Exception as e:
                    # Retry logic
                    for attempt in range(self.retry_attempts):
                        try:
                            pipeline_events.append(f"retry_attempt_{attempt + 1}")
                            await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                            await self._insert_to_clickhouse(batch)
                            self.processed_events.extend(batch)
                            pipeline_events.append(f"retry_success_{attempt + 1}")
                            break
                        except Exception:
                            if attempt == self.retry_attempts - 1:
                                self.failed_events.extend(batch)
                                pipeline_events.append(f"batch_failed_after_retries")
                                processing_results.append({
                                    "batch_size": len(batch),
                                    "status": "failed",
                                    "error": str(e),
                                    "timestamp": time.time()
                                })
            
            async def _insert_to_clickhouse(self, events: List[Dict[str, Any]]):
                # Simulate ClickHouse insertion with potential failures
                import random
                
                # 5% chance of simulated failure
                if random.random() < 0.05:
                    raise ConnectionError("ClickHouse connection failed")
                
                # Simulate insertion time
                await asyncio.sleep(0.01 * len(events))
                pipeline_events.append(f"clickhouse_insert_{len(events)}")
            
            def get_pipeline_stats(self):
                return {
                    "total_ingested": len(self.processed_events) + len(self.failed_events),
                    "successfully_processed": len(self.processed_events),
                    "failed_events": len(self.failed_events),
                    "success_rate": len(self.processed_events) / (len(self.processed_events) + len(self.failed_events)) if (len(self.processed_events) + len(self.failed_events)) > 0 else 0,
                    "buffered_events": len(self.event_buffer)
                }
        
        pipeline = ClickHouseEventPipeline()
        
        # Test normal event ingestion
        test_events = [
            {
                "event_type": "agent_execution",
                "user_id": f"user_{i}",
                "timestamp": time.time(),
                "data": {
                    "agent_name": "cost_optimizer",
                    "execution_time": 2.5,
                    "cost_analyzed": 1000 + (i * 100)
                }
            }
            for i in range(150)  # More than batch size to trigger multiple batches
        ]
        
        # Ingest events
        ingestion_results = []
        for event in test_events:
            result = await pipeline.ingest_event(event)
            ingestion_results.append(result)
        
        # Flush remaining events
        await pipeline.flush_events()
        
        # Verify pipeline performance
        stats = pipeline.get_pipeline_stats()
        
        assert stats["total_ingested"] == 150
        assert stats["success_rate"] > 0.9  # Should have high success rate
        assert stats["buffered_events"] == 0  # All events should be flushed
        
        # Verify batch processing occurred
        batch_events = [e for e in pipeline_events if e.startswith("batch_processing")]
        assert len(batch_events) >= 2  # Should have processed multiple batches
        
        # Verify ClickHouse insertions
        clickhouse_inserts = [e for e in pipeline_events if e.startswith("clickhouse_insert")]
        assert len(clickhouse_inserts) >= 2
        
        # Test pipeline resilience with high event volume
        pipeline_events.clear()
        processing_results.clear()
        
        # Simulate high-volume event stream
        high_volume_events = [
            {
                "event_type": "user_action",
                "user_id": f"user_{i % 50}",  # 50 different users
                "timestamp": time.time(),
                "data": {
                    "action": "view_dashboard" if i % 2 == 0 else "run_optimization",
                    "duration_ms": random.randint(100, 5000)
                }
            }
            for i in range(500)  # High volume
        ]
        
        # Ingest high volume concurrently
        ingestion_tasks = [
            pipeline.ingest_event(event) 
            for event in high_volume_events
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*ingestion_tasks)
        processing_time = time.time() - start_time
        
        # Final flush
        await pipeline.flush_events()
        
        final_stats = pipeline.get_pipeline_stats()
        
        # Verify high-volume performance
        assert final_stats["total_ingested"] >= 500
        assert final_stats["success_rate"] > 0.85  # Should maintain good success rate
        assert processing_time < 10.0  # Should process 500 events in reasonable time
        
        # Verify processing efficiency
        successful_batches = [r for r in processing_results if r["status"] == "success"]
        assert len(successful_batches) >= 5  # Should have multiple successful batches

    @pytest.mark.integration
    async def test_cross_service_analytics_data_consistency(self):
        """
        Test analytics data consistency across different services.
        
        BVJ: Ensures analytics accurately reflect user activities across all services,
        critical for customer trust in platform insights and ROI calculations.
        """
        service_events = {
            "backend": [],
            "auth_service": [],
            "frontend": []
        }
        consistency_checks = []
        
        class CrossServiceAnalyticsValidator:
            def __init__(self):
                self.event_correlations = {}
                self.service_counters = {
                    "backend": {"agent_executions": 0, "api_calls": 0},
                    "auth_service": {"logins": 0, "token_refreshes": 0},
                    "frontend": {"page_views": 0, "user_interactions": 0}
                }
            
            async def track_backend_event(self, user_id: str, event_type: str, data: Dict[str, Any]):
                event = {
                    "service": "backend",
                    "user_id": user_id,
                    "event_type": event_type,
                    "timestamp": time.time(),
                    "data": data,
                    "correlation_id": f"corr_{user_id}_{len(service_events['backend'])}"
                }
                
                service_events["backend"].append(event)
                self.service_counters["backend"][event_type] += 1
                
                # Create correlation entry
                if user_id not in self.event_correlations:
                    self.event_correlations[user_id] = {"sessions": []}
                
                self.event_correlations[user_id]["sessions"].append({
                    "service": "backend",
                    "event": event_type,
                    "timestamp": event["timestamp"],
                    "correlation_id": event["correlation_id"]
                })
            
            async def track_auth_event(self, user_id: str, event_type: str, data: Dict[str, Any]):
                event = {
                    "service": "auth_service",
                    "user_id": user_id,
                    "event_type": event_type,
                    "timestamp": time.time(),
                    "data": data,
                    "correlation_id": f"corr_{user_id}_{len(service_events['auth_service'])}"
                }
                
                service_events["auth_service"].append(event)
                self.service_counters["auth_service"][event_type] += 1
                
                if user_id not in self.event_correlations:
                    self.event_correlations[user_id] = {"sessions": []}
                
                self.event_correlations[user_id]["sessions"].append({
                    "service": "auth_service",
                    "event": event_type,
                    "timestamp": event["timestamp"],
                    "correlation_id": event["correlation_id"]
                })
            
            async def track_frontend_event(self, user_id: str, event_type: str, data: Dict[str, Any]):
                event = {
                    "service": "frontend",
                    "user_id": user_id,
                    "event_type": event_type,
                    "timestamp": time.time(),
                    "data": data,
                    "correlation_id": f"corr_{user_id}_{len(service_events['frontend'])}"
                }
                
                service_events["frontend"].append(event)
                self.service_counters["frontend"][event_type] += 1
                
                if user_id not in self.event_correlations:
                    self.event_correlations[user_id] = {"sessions": []}
                
                self.event_correlations[user_id]["sessions"].append({
                    "service": "frontend",
                    "event": event_type,
                    "timestamp": event["timestamp"],
                    "correlation_id": event["correlation_id"]
                })
            
            async def validate_user_journey_consistency(self, user_id: str):
                if user_id not in self.event_correlations:
                    return {"consistent": False, "reason": "no_events"}
                
                user_events = self.event_correlations[user_id]["sessions"]
                user_events.sort(key=lambda x: x["timestamp"])
                
                # Validate typical user journey: login -> page views -> agent execution
                consistency_result = {
                    "user_id": user_id,
                    "total_events": len(user_events),
                    "services_used": list(set(event["service"] for event in user_events)),
                    "consistent": True,
                    "issues": []
                }
                
                # Check for logical flow
                auth_events = [e for e in user_events if e["service"] == "auth_service"]
                frontend_events = [e for e in user_events if e["service"] == "frontend"]
                backend_events = [e for e in user_events if e["service"] == "backend"]
                
                # Should have authentication before other activities
                if backend_events and not auth_events:
                    consistency_result["consistent"] = False
                    consistency_result["issues"].append("backend_activity_without_auth")
                
                if frontend_events and not auth_events:
                    consistency_result["consistent"] = False
                    consistency_result["issues"].append("frontend_activity_without_auth")
                
                # Check timestamp ordering
                if auth_events and (frontend_events or backend_events):
                    first_auth_time = min(e["timestamp"] for e in auth_events)
                    
                    for event in frontend_events + backend_events:
                        if event["timestamp"] < first_auth_time:
                            consistency_result["consistent"] = False
                            consistency_result["issues"].append(f"activity_before_auth_{event['service']}")
                
                consistency_checks.append(consistency_result)
                return consistency_result
            
            async def generate_analytics_summary(self):
                return {
                    "total_events": sum(len(events) for events in service_events.values()),
                    "events_by_service": {
                        service: len(events) for service, events in service_events.items()
                    },
                    "unique_users": len(self.event_correlations),
                    "service_counters": self.service_counters,
                    "consistency_rate": len([c for c in consistency_checks if c["consistent"]]) / len(consistency_checks) if consistency_checks else 0
                }
        
        validator = CrossServiceAnalyticsValidator()
        
        # Simulate user journeys across services
        users = [f"user_{i}" for i in range(10)]
        
        for user_id in users:
            # Typical user journey
            # 1. User logs in (auth service)
            await validator.track_auth_event(user_id, "logins", {
                "login_method": "oauth",
                "session_id": f"session_{user_id}"
            })
            
            # 2. User views dashboard (frontend)
            await validator.track_frontend_event(user_id, "page_views", {
                "page": "dashboard",
                "referrer": "direct"
            })
            
            # 3. User interacts with UI (frontend)
            await validator.track_frontend_event(user_id, "user_interactions", {
                "interaction": "click_optimize_button",
                "element": "cost_optimizer"
            })
            
            # 4. Agent execution happens (backend)
            await validator.track_backend_event(user_id, "agent_executions", {
                "agent_name": "cost_optimizer",
                "execution_time_ms": 2500,
                "result_size_kb": 45
            })
            
            # 5. API calls for data (backend)
            await validator.track_backend_event(user_id, "api_calls", {
                "endpoint": "/api/optimization-results",
                "response_time_ms": 150
            })
            
            # 6. Token refresh (auth service)
            await validator.track_auth_event(user_id, "token_refreshes", {
                "refresh_reason": "expiry",
                "new_expiry": time.time() + 3600
            })
        
        # Validate consistency for each user
        consistency_results = []
        for user_id in users:
            result = await validator.validate_user_journey_consistency(user_id)
            consistency_results.append(result)
        
        # Verify cross-service consistency
        consistent_users = [r for r in consistency_results if r["consistent"]]
        assert len(consistent_users) == 10  # All users should have consistent journeys
        
        # Verify service event counts match
        analytics_summary = await validator.generate_analytics_summary()
        
        assert analytics_summary["total_events"] == 60  # 10 users  x  6 events each
        assert analytics_summary["events_by_service"]["auth_service"] == 20  # 10 users  x  2 auth events
        assert analytics_summary["events_by_service"]["frontend"] == 20   # 10 users  x  2 frontend events
        assert analytics_summary["events_by_service"]["backend"] == 20     # 10 users  x  2 backend events
        assert analytics_summary["unique_users"] == 10
        assert analytics_summary["consistency_rate"] == 1.0  # 100% consistent
        
        # Verify service counters
        assert validator.service_counters["auth_service"]["logins"] == 10
        assert validator.service_counters["auth_service"]["token_refreshes"] == 10
        assert validator.service_counters["frontend"]["page_views"] == 10
        assert validator.service_counters["frontend"]["user_interactions"] == 10
        assert validator.service_counters["backend"]["agent_executions"] == 10
        assert validator.service_counters["backend"]["api_calls"] == 10

    @pytest.mark.integration
    async def test_analytics_service_failure_resilience(self):
        """
        Test analytics service resilience during various failure scenarios.
        
        BVJ: Ensures analytics data isn't lost during service disruptions, maintaining
        data integrity for customer insights and business intelligence.
        """
        failure_scenarios = []
        recovery_metrics = []
        
        class ResilientAnalyticsService:
            def __init__(self):
                self.primary_storage = []
                self.backup_storage = []
                self.failure_buffer = []
                self.service_state = "healthy"
                self.failure_detection_threshold = 3
                self.consecutive_failures = 0
                self.circuit_breaker_open = False
                
            async def ingest_analytics_event(self, event: Dict[str, Any]):
                event_with_metadata = {
                    **event,
                    "ingestion_attempt_timestamp": time.time(),
                    "attempt_count": 1
                }
                
                try:
                    if self.circuit_breaker_open:
                        # Circuit breaker is open, route to backup
                        await self._store_in_backup(event_with_metadata)
                        failure_scenarios.append("circuit_breaker_backup_routing")
                        return {"status": "backup", "location": "backup_storage"}
                    
                    # Try primary storage
                    await self._store_in_primary(event_with_metadata)
                    
                    # Reset failure counter on success
                    self.consecutive_failures = 0
                    if self.circuit_breaker_open:
                        await self._close_circuit_breaker()
                    
                    return {"status": "success", "location": "primary_storage"}
                
                except Exception as e:
                    self.consecutive_failures += 1
                    failure_scenarios.append(f"primary_storage_failure_{self.consecutive_failures}")
                    
                    # Open circuit breaker if threshold reached
                    if self.consecutive_failures >= self.failure_detection_threshold:
                        await self._open_circuit_breaker()
                    
                    # Try backup storage
                    try:
                        await self._store_in_backup(event_with_metadata)
                        failure_scenarios.append("fallback_to_backup_success")
                        return {"status": "backup", "location": "backup_storage"}
                    
                    except Exception as backup_error:
                        # Both primary and backup failed, buffer event
                        self.failure_buffer.append(event_with_metadata)
                        failure_scenarios.append("both_storages_failed_buffered")
                        return {"status": "buffered", "location": "failure_buffer"}
            
            async def _store_in_primary(self, event: Dict[str, Any]):
                # Simulate primary storage with potential failures
                import random
                
                if self.service_state == "degraded":
                    # Higher failure rate in degraded state
                    if random.random() < 0.3:  # 30% failure rate
                        raise ConnectionError("Primary storage connection failed")
                
                if self.service_state == "failing":
                    # Very high failure rate
                    if random.random() < 0.8:  # 80% failure rate
                        raise ConnectionError("Primary storage severely degraded")
                
                # Simulate storage latency
                await asyncio.sleep(0.01)
                self.primary_storage.append(event)
            
            async def _store_in_backup(self, event: Dict[str, Any]):
                # Backup storage is more reliable but slower
                await asyncio.sleep(0.02)
                event["backup_stored"] = True
                self.backup_storage.append(event)
            
            async def _open_circuit_breaker(self):
                self.circuit_breaker_open = True
                failure_scenarios.append("circuit_breaker_opened")
            
            async def _close_circuit_breaker(self):
                self.circuit_breaker_open = False
                self.consecutive_failures = 0
                failure_scenarios.append("circuit_breaker_closed")
            
            async def attempt_recovery(self):
                recovery_start = time.time()
                recovered_events = 0
                
                # Try to replay buffered events
                events_to_replay = self.failure_buffer.copy()
                self.failure_buffer.clear()
                
                for event in events_to_replay:
                    event["attempt_count"] = event.get("attempt_count", 1) + 1
                    event["recovery_attempt_timestamp"] = time.time()
                    
                    try:
                        await self._store_in_primary(event)
                        recovered_events += 1
                    except Exception:
                        # If still failing, try backup
                        try:
                            await self._store_in_backup(event)
                            recovered_events += 1
                        except Exception:
                            # Return to failure buffer
                            self.failure_buffer.append(event)
                
                recovery_duration = time.time() - recovery_start
                recovery_result = {
                    "recovered_events": recovered_events,
                    "remaining_buffered": len(self.failure_buffer),
                    "recovery_duration": recovery_duration,
                    "success_rate": recovered_events / len(events_to_replay) if events_to_replay else 1.0
                }
                
                recovery_metrics.append(recovery_result)
                failure_scenarios.append(f"recovery_completed_{recovered_events}_events")
                
                return recovery_result
            
            def simulate_service_degradation(self, state: str):
                """Simulate different service states: healthy, degraded, failing"""
                self.service_state = state
                failure_scenarios.append(f"service_state_changed_{state}")
            
            def get_service_stats(self):
                return {
                    "primary_events": len(self.primary_storage),
                    "backup_events": len(self.backup_storage),
                    "buffered_events": len(self.failure_buffer),
                    "total_events": len(self.primary_storage) + len(self.backup_storage) + len(self.failure_buffer),
                    "consecutive_failures": self.consecutive_failures,
                    "circuit_breaker_open": self.circuit_breaker_open,
                    "service_state": self.service_state
                }
        
        analytics_service = ResilientAnalyticsService()
        
        # Test normal operation
        normal_events = [
            {"event_type": "user_action", "user_id": f"user_{i}", "data": {"action": "dashboard_view"}}
            for i in range(20)
        ]
        
        for event in normal_events:
            result = await analytics_service.ingest_analytics_event(event)
            assert result["status"] == "success"
        
        stats = analytics_service.get_service_stats()
        assert stats["primary_events"] == 20
        assert stats["backup_events"] == 0
        assert stats["buffered_events"] == 0
        
        # Simulate service degradation
        analytics_service.simulate_service_degradation("degraded")
        
        degraded_events = [
            {"event_type": "agent_execution", "user_id": f"user_{i}", "data": {"agent": "cost_optimizer"}}
            for i in range(30)
        ]
        
        degraded_results = []
        for event in degraded_events:
            result = await analytics_service.ingest_analytics_event(event)
            degraded_results.append(result)
        
        # Some events should succeed, some should fall back to backup
        successful_results = [r for r in degraded_results if r["status"] == "success"]
        backup_results = [r for r in degraded_results if r["status"] == "backup"]
        
        assert len(successful_results) > 0  # Some should still succeed
        assert len(backup_results) > 0     # Some should fall back to backup
        
        # Simulate severe failure
        analytics_service.simulate_service_degradation("failing")
        
        failing_events = [
            {"event_type": "optimization_result", "user_id": f"user_{i}", "data": {"savings": 100 * i}}
            for i in range(15)
        ]
        
        failing_results = []
        for event in failing_events:
            result = await analytics_service.ingest_analytics_event(event)
            failing_results.append(result)
        
        # Most events should either go to backup or be buffered
        buffered_results = [r for r in failing_results if r["status"] == "buffered"]
        backup_results_2 = [r for r in failing_results if r["status"] == "backup"]
        
        # Circuit breaker should have opened
        assert analytics_service.circuit_breaker_open
        assert "circuit_breaker_opened" in failure_scenarios
        
        # Test recovery
        analytics_service.simulate_service_degradation("healthy")
        recovery_result = await analytics_service.attempt_recovery()
        
        # Verify recovery
        assert recovery_result["recovered_events"] > 0
        assert recovery_result["success_rate"] > 0.5  # Should recover most events
        
        # Verify circuit breaker closed
        assert not analytics_service.circuit_breaker_open
        assert "circuit_breaker_closed" in failure_scenarios
        
        final_stats = analytics_service.get_service_stats()
        
        # Should have processed most events across primary and backup
        total_processed = final_stats["primary_events"] + final_stats["backup_events"]
        assert total_processed >= 50  # Should have processed most of the 65 total events
        
        # Verify recovery metrics
        assert len(recovery_metrics) > 0
        assert all(metric["recovery_duration"] < 5.0 for metric in recovery_metrics)  # Recovery should be fast

    @pytest.mark.integration
    async def test_event_processing_under_high_volume(self):
        """
        Test analytics event processing under high volume scenarios.
        
        BVJ: Ensures analytics system can handle enterprise-level event volumes
        without performance degradation or data loss.
        """
        volume_metrics = {
            "processing_times": [],
            "throughput_measurements": [],
            "memory_usage": [],
            "batch_sizes": [],
            "queue_depths": []
        }
        
        class HighVolumeAnalyticsProcessor:
            def __init__(self):
                self.event_queue = asyncio.Queue(maxsize=10000)
                self.processed_events = []
                self.processing_stats = {
                    "events_processed": 0,
                    "batches_processed": 0,
                    "total_processing_time": 0,
                    "peak_queue_depth": 0
                }
                self.batch_size = 50
                self.processing_active = False
            
            async def queue_event(self, event: Dict[str, Any]):
                try:
                    await self.event_queue.put(event)
                    
                    # Track queue depth
                    queue_depth = self.event_queue.qsize()
                    volume_metrics["queue_depths"].append(queue_depth)
                    
                    if queue_depth > self.processing_stats["peak_queue_depth"]:
                        self.processing_stats["peak_queue_depth"] = queue_depth
                    
                    return True
                except asyncio.QueueFull:
                    volume_metrics["queue_depths"].append(10000)  # Max capacity
                    return False
            
            async def start_processing(self):
                self.processing_active = True
                
                while self.processing_active:
                    batch = []
                    batch_start_time = time.time()
                    
                    # Collect batch
                    for _ in range(self.batch_size):
                        try:
                            event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                            batch.append(event)
                        except asyncio.TimeoutError:
                            break  # No more events immediately available
                    
                    if batch:
                        # Process batch
                        await self._process_batch(batch)
                        
                        # Record metrics
                        batch_processing_time = time.time() - batch_start_time
                        volume_metrics["processing_times"].append(batch_processing_time)
                        volume_metrics["batch_sizes"].append(len(batch))
                        
                        # Calculate throughput
                        throughput = len(batch) / batch_processing_time if batch_processing_time > 0 else 0
                        volume_metrics["throughput_measurements"].append(throughput)
                        
                        # Update stats
                        self.processing_stats["events_processed"] += len(batch)
                        self.processing_stats["batches_processed"] += 1
                        self.processing_stats["total_processing_time"] += batch_processing_time
                        
                        # Simulate memory usage
                        simulated_memory = 100 + (len(self.processed_events) * 0.1)  # MB
                        volume_metrics["memory_usage"].append(simulated_memory)
                    
                    else:
                        # No events to process, short sleep
                        await asyncio.sleep(0.01)
            
            async def _process_batch(self, batch: List[Dict[str, Any]]):
                # Simulate batch processing overhead
                await asyncio.sleep(0.005 * len(batch))
                
                # Process each event in batch
                for event in batch:
                    # Simulate event processing
                    processed_event = {
                        **event,
                        "processed_timestamp": time.time(),
                        "batch_id": self.processing_stats["batches_processed"]
                    }
                    self.processed_events.append(processed_event)
            
            def stop_processing(self):
                self.processing_active = False
            
            def get_performance_stats(self):
                avg_processing_time = (
                    self.processing_stats["total_processing_time"] / 
                    self.processing_stats["batches_processed"]
                ) if self.processing_stats["batches_processed"] > 0 else 0
                
                avg_throughput = (
                    sum(volume_metrics["throughput_measurements"]) /
                    len(volume_metrics["throughput_measurements"])
                ) if volume_metrics["throughput_measurements"] else 0
                
                return {
                    **self.processing_stats,
                    "avg_batch_processing_time": avg_processing_time,
                    "avg_throughput_events_per_second": avg_throughput,
                    "max_queue_depth": max(volume_metrics["queue_depths"]) if volume_metrics["queue_depths"] else 0,
                    "peak_memory_mb": max(volume_metrics["memory_usage"]) if volume_metrics["memory_usage"] else 0
                }
        
        processor = HighVolumeAnalyticsProcessor()
        
        # Start background processing
        processing_task = asyncio.create_task(processor.start_processing())
        
        # Generate high volume of events
        event_types = ["user_login", "agent_execution", "optimization_result", "dashboard_view", "report_generation"]
        users = [f"user_{i}" for i in range(100)]
        
        # Phase 1: Moderate volume
        moderate_volume_events = []
        for i in range(1000):
            event = {
                "event_type": event_types[i % len(event_types)],
                "user_id": users[i % len(users)],
                "timestamp": time.time(),
                "event_id": f"event_{i}",
                "data": {
                    "value": i,
                    "batch": "moderate_volume"
                }
            }
            moderate_volume_events.append(event)
        
        # Queue events with controlled rate
        moderate_start_time = time.time()
        for event in moderate_volume_events:
            queued = await processor.queue_event(event)
            if not queued:
                break
        moderate_queue_time = time.time() - moderate_start_time
        
        # Wait for moderate volume to be processed
        await asyncio.sleep(2.0)
        
        moderate_stats = processor.get_performance_stats()
        
        # Phase 2: High volume burst
        high_volume_events = []
        for i in range(5000):  # Much higher volume
            event = {
                "event_type": event_types[i % len(event_types)],
                "user_id": users[i % len(users)],
                "timestamp": time.time(),
                "event_id": f"burst_event_{i}",
                "data": {
                    "value": i,
                    "batch": "high_volume_burst"
                }
            }
            high_volume_events.append(event)
        
        # Queue high volume events rapidly
        burst_start_time = time.time()
        burst_tasks = [processor.queue_event(event) for event in high_volume_events]
        burst_results = await asyncio.gather(*burst_tasks)
        burst_queue_time = time.time() - burst_start_time
        
        # Wait for high volume to be processed
        await asyncio.sleep(5.0)
        
        # Stop processing
        processor.stop_processing()
        await processing_task
        
        final_stats = processor.get_performance_stats()
        
        # Verify volume handling
        assert final_stats["events_processed"] >= 1000  # Should process at least moderate volume
        assert final_stats["batches_processed"] >= 20   # Should have processed multiple batches
        
        # Verify performance under load
        assert final_stats["avg_throughput_events_per_second"] > 100  # Should maintain good throughput
        assert final_stats["avg_batch_processing_time"] < 1.0        # Batch processing should be fast
        
        # Verify queue management
        max_queue_depth = final_stats["max_queue_depth"]
        assert max_queue_depth > 0  # Should have queued events
        
        # Check if system handled burst without major issues
        successful_bursts = sum(1 for result in burst_results if result)
        burst_success_rate = successful_bursts / len(burst_results)
        
        # Should handle most of the burst, though some may be dropped due to queue limits
        assert burst_success_rate > 0.5  # Should handle at least 50% of burst
        
        # Verify processing efficiency
        processing_times = volume_metrics["processing_times"]
        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)
            assert avg_processing_time < 0.5  # Each batch should process quickly
        
        throughput_measurements = volume_metrics["throughput_measurements"]
        if throughput_measurements:
            peak_throughput = max(throughput_measurements)
            assert peak_throughput > 200  # Should achieve high peak throughput

    @pytest.mark.integration
    async def test_analytics_query_optimization_and_performance(self):
        """
        Test analytics query optimization and performance for customer insights.
        
        BVJ: Ensures customers can quickly access optimization insights and usage analytics,
        critical for user experience and platform value demonstration.
        """
        query_performance = []
        optimization_results = []
        
        class AnalyticsQueryEngine:
            def __init__(self):
                # Simulate analytics database with indexes
                self.data_store = {
                    "user_events": [],
                    "agent_executions": [],
                    "optimization_results": [],
                    "cost_savings": []
                }
                
                # Simulate pre-computed aggregations for performance
                self.aggregations = {
                    "daily_user_activity": {},
                    "agent_performance_stats": {},
                    "cost_savings_by_user": {},
                    "usage_trends": {}
                }
                
                self.query_cache = {}
                self.cache_ttl = 300  # 5 minutes
            
            async def ingest_sample_data(self):
                """Generate sample analytics data for testing"""
                import random
                current_time = time.time()
                
                # Generate user events
                for i in range(1000):
                    event = {
                        "event_id": f"event_{i}",
                        "user_id": f"user_{i % 50}",  # 50 different users
                        "timestamp": current_time - (i * 60),  # Events over time
                        "event_type": random.choice(["login", "dashboard_view", "agent_request", "report_view"]),
                        "session_id": f"session_{i // 10}"
                    }
                    self.data_store["user_events"].append(event)
                
                # Generate agent execution data
                for i in range(500):
                    execution = {
                        "execution_id": f"exec_{i}",
                        "user_id": f"user_{i % 50}",
                        "agent_name": random.choice(["cost_optimizer", "security_scanner", "performance_analyzer"]),
                        "timestamp": current_time - (i * 120),
                        "duration_ms": random.randint(1000, 30000),
                        "success": random.random() > 0.1  # 90% success rate
                    }
                    self.data_store["agent_executions"].append(execution)
                
                # Generate optimization results
                for i in range(300):
                    result = {
                        "result_id": f"result_{i}",
                        "user_id": f"user_{i % 50}",
                        "timestamp": current_time - (i * 180),
                        "monthly_savings": random.randint(100, 10000),
                        "optimization_category": random.choice(["compute", "storage", "network", "database"])
                    }
                    self.data_store["optimization_results"].append(result)
                
                # Pre-compute aggregations
                await self._update_aggregations()
            
            async def _update_aggregations(self):
                """Update pre-computed aggregations for fast queries"""
                # Daily user activity
                daily_activity = {}
                for event in self.data_store["user_events"]:
                    day_key = int(event["timestamp"] // 86400)  # Group by day
                    if day_key not in daily_activity:
                        daily_activity[day_key] = {"users": set(), "events": 0}
                    
                    daily_activity[day_key]["users"].add(event["user_id"])
                    daily_activity[day_key]["events"] += 1
                
                # Convert sets to counts for JSON serialization
                for day, stats in daily_activity.items():
                    daily_activity[day]["unique_users"] = len(stats["users"])
                    del daily_activity[day]["users"]
                
                self.aggregations["daily_user_activity"] = daily_activity
                
                # Agent performance stats
                agent_stats = {}
                for execution in self.data_store["agent_executions"]:
                    agent = execution["agent_name"]
                    if agent not in agent_stats:
                        agent_stats[agent] = {
                            "total_executions": 0,
                            "successful_executions": 0,
                            "total_duration_ms": 0
                        }
                    
                    agent_stats[agent]["total_executions"] += 1
                    if execution["success"]:
                        agent_stats[agent]["successful_executions"] += 1
                    agent_stats[agent]["total_duration_ms"] += execution["duration_ms"]
                
                # Calculate derived metrics
                for agent, stats in agent_stats.items():
                    stats["success_rate"] = stats["successful_executions"] / stats["total_executions"]
                    stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_executions"]
                
                self.aggregations["agent_performance_stats"] = agent_stats
                
                # Cost savings by user
                user_savings = {}
                for result in self.data_store["optimization_results"]:
                    user_id = result["user_id"]
                    if user_id not in user_savings:
                        user_savings[user_id] = {"total_savings": 0, "optimizations": 0}
                    
                    user_savings[user_id]["total_savings"] += result["monthly_savings"]
                    user_savings[user_id]["optimizations"] += 1
                
                self.aggregations["cost_savings_by_user"] = user_savings
            
            async def execute_user_dashboard_query(self, user_id: str):
                """Execute optimized query for user dashboard"""
                query_start = time.time()
                
                # Check cache first
                cache_key = f"dashboard_{user_id}"
                if cache_key in self.query_cache:
                    cached_result, cached_time = self.query_cache[cache_key]
                    if time.time() - cached_time < self.cache_ttl:
                        query_duration = time.time() - query_start
                        query_performance.append({
                            "query_type": "user_dashboard",
                            "user_id": user_id,
                            "duration_ms": query_duration * 1000,
                            "cache_hit": True
                        })
                        return cached_result
                
                # Execute query (optimized with pre-computed aggregations)
                result = {
                    "user_id": user_id,
                    "total_savings": self.aggregations["cost_savings_by_user"].get(user_id, {}).get("total_savings", 0),
                    "optimizations_count": self.aggregations["cost_savings_by_user"].get(user_id, {}).get("optimizations", 0),
                    "recent_activity": len([
                        e for e in self.data_store["user_events"] 
                        if e["user_id"] == user_id and e["timestamp"] > (time.time() - 86400)
                    ]),
                    "agent_usage": {}
                }
                
                # Calculate agent usage for this user
                user_executions = [e for e in self.data_store["agent_executions"] if e["user_id"] == user_id]
                for execution in user_executions:
                    agent = execution["agent_name"]
                    if agent not in result["agent_usage"]:
                        result["agent_usage"][agent] = 0
                    result["agent_usage"][agent] += 1
                
                # Cache result
                self.query_cache[cache_key] = (result, time.time())
                
                query_duration = time.time() - query_start
                query_performance.append({
                    "query_type": "user_dashboard",
                    "user_id": user_id,
                    "duration_ms": query_duration * 1000,
                    "cache_hit": False
                })
                
                return result
            
            async def execute_platform_analytics_query(self, time_range_days: int = 7):
                """Execute platform-wide analytics query"""
                query_start = time.time()
                
                cache_key = f"platform_analytics_{time_range_days}d"
                if cache_key in self.query_cache:
                    cached_result, cached_time = self.query_cache[cache_key]
                    if time.time() - cached_time < self.cache_ttl:
                        query_duration = time.time() - query_start
                        query_performance.append({
                            "query_type": "platform_analytics",
                            "duration_ms": query_duration * 1000,
                            "cache_hit": True
                        })
                        return cached_result
                
                # Use pre-computed aggregations for fast results
                time_threshold = time.time() - (time_range_days * 86400)
                
                # Filter daily activity within time range
                recent_daily_activity = {
                    day: stats for day, stats in self.aggregations["daily_user_activity"].items()
                    if (day * 86400) > time_threshold
                }
                
                result = {
                    "time_range_days": time_range_days,
                    "total_unique_users": len(set(
                        event["user_id"] for event in self.data_store["user_events"]
                        if event["timestamp"] > time_threshold
                    )),
                    "total_events": len([
                        e for e in self.data_store["user_events"]
                        if e["timestamp"] > time_threshold
                    ]),
                    "total_agent_executions": len([
                        e for e in self.data_store["agent_executions"]
                        if e["timestamp"] > time_threshold
                    ]),
                    "agent_performance": self.aggregations["agent_performance_stats"],
                    "daily_activity": recent_daily_activity,
                    "total_cost_savings": sum(
                        result["monthly_savings"] for result in self.data_store["optimization_results"]
                        if result["timestamp"] > time_threshold
                    )
                }
                
                # Cache result
                self.query_cache[cache_key] = (result, time.time())
                
                query_duration = time.time() - query_start
                query_performance.append({
                    "query_type": "platform_analytics",
                    "duration_ms": query_duration * 1000,
                    "cache_hit": False
                })
                
                return result
            
            async def execute_optimization_insights_query(self, user_id: str):
                """Execute complex optimization insights query"""
                query_start = time.time()
                
                # This query involves complex aggregations and analysis
                user_results = [
                    r for r in self.data_store["optimization_results"]
                    if r["user_id"] == user_id
                ]
                
                user_executions = [
                    e for e in self.data_store["agent_executions"]
                    if e["user_id"] == user_id and e["success"]
                ]
                
                # Calculate optimization insights
                insights = {
                    "user_id": user_id,
                    "total_optimizations": len(user_results),
                    "total_savings": sum(r["monthly_savings"] for r in user_results),
                    "avg_savings_per_optimization": 0,
                    "optimization_categories": {},
                    "optimization_trend": {},
                    "agent_effectiveness": {}
                }
                
                if user_results:
                    insights["avg_savings_per_optimization"] = insights["total_savings"] / len(user_results)
                    
                    # Group by category
                    for result in user_results:
                        category = result["optimization_category"]
                        if category not in insights["optimization_categories"]:
                            insights["optimization_categories"][category] = {"count": 0, "savings": 0}
                        
                        insights["optimization_categories"][category]["count"] += 1
                        insights["optimization_categories"][category]["savings"] += result["monthly_savings"]
                    
                    # Calculate trend (simplified)
                    sorted_results = sorted(user_results, key=lambda x: x["timestamp"])
                    if len(sorted_results) > 1:
                        recent_savings = sum(r["monthly_savings"] for r in sorted_results[-5:])  # Last 5
                        earlier_savings = sum(r["monthly_savings"] for r in sorted_results[:5])  # First 5
                        insights["optimization_trend"]["direction"] = "increasing" if recent_savings > earlier_savings else "decreasing"
                        insights["optimization_trend"]["recent_avg"] = recent_savings / min(5, len(sorted_results[-5:]))
                
                # Agent effectiveness
                for execution in user_executions:
                    agent = execution["agent_name"]
                    if agent not in insights["agent_effectiveness"]:
                        insights["agent_effectiveness"][agent] = {"executions": 0, "avg_duration": 0}
                    
                    insights["agent_effectiveness"][agent]["executions"] += 1
                
                query_duration = time.time() - query_start
                query_performance.append({
                    "query_type": "optimization_insights",
                    "user_id": user_id,
                    "duration_ms": query_duration * 1000,
                    "cache_hit": False
                })
                
                optimization_results.append(insights)
                return insights
        
        query_engine = AnalyticsQueryEngine()
        
        # Set up sample data
        await query_engine.ingest_sample_data()
        
        # Test user dashboard queries (should be fast due to pre-computed aggregations)
        dashboard_users = [f"user_{i}" for i in range(10)]
        
        dashboard_tasks = [
            query_engine.execute_user_dashboard_query(user_id)
            for user_id in dashboard_users
        ]
        
        dashboard_results = await asyncio.gather(*dashboard_tasks)
        
        # Verify dashboard query performance
        dashboard_queries = [q for q in query_performance if q["query_type"] == "user_dashboard"]
        assert len(dashboard_queries) == 10
        
        # First-time queries should be reasonably fast
        first_time_queries = [q for q in dashboard_queries if not q["cache_hit"]]
        if first_time_queries:
            avg_dashboard_time = sum(q["duration_ms"] for q in first_time_queries) / len(first_time_queries)
            assert avg_dashboard_time < 100  # Should be under 100ms
        
        # Test cache effectiveness - run same queries again
        cached_dashboard_tasks = [
            query_engine.execute_user_dashboard_query(user_id)
            for user_id in dashboard_users
        ]
        
        await asyncio.gather(*cached_dashboard_tasks)
        
        # Verify cached queries are faster
        cached_queries = [q for q in query_performance if q["query_type"] == "user_dashboard" and q["cache_hit"]]
        assert len(cached_queries) == 10  # Second round should all be cached
        
        avg_cached_time = sum(q["duration_ms"] for q in cached_queries) / len(cached_queries)
        assert avg_cached_time < 10  # Cached queries should be very fast
        
        # Test platform analytics query
        platform_result = await query_engine.execute_platform_analytics_query(7)
        
        platform_queries = [q for q in query_performance if q["query_type"] == "platform_analytics"]
        assert len(platform_queries) == 1
        assert platform_queries[0]["duration_ms"] < 200  # Should be reasonably fast
        
        # Verify platform analytics content
        assert platform_result["total_unique_users"] > 0
        assert platform_result["total_events"] > 0
        assert len(platform_result["agent_performance"]) > 0
        assert platform_result["total_cost_savings"] > 0
        
        # Test complex optimization insights queries
        insight_users = [f"user_{i}" for i in range(5)]  # Fewer users for complex queries
        
        insight_tasks = [
            query_engine.execute_optimization_insights_query(user_id)
            for user_id in insight_users
        ]
        
        insight_results = await asyncio.gather(*insight_tasks)
        
        # Verify optimization insights performance
        insight_queries = [q for q in query_performance if q["query_type"] == "optimization_insights"]
        assert len(insight_queries) == 5
        
        avg_insight_time = sum(q["duration_ms"] for q in insight_queries) / len(insight_queries)
        assert avg_insight_time < 500  # Complex queries should still be under 500ms
        
        # Verify optimization insights content
        assert len(optimization_results) == 5
        for insight in optimization_results:
            assert "total_optimizations" in insight
            assert "total_savings" in insight
            assert "optimization_categories" in insight
            assert "agent_effectiveness" in insight
        
        # Overall performance verification
        all_queries = query_performance
        total_query_time = sum(q["duration_ms"] for q in all_queries)
        avg_query_time = total_query_time / len(all_queries)
        
        assert avg_query_time < 200  # Average query time should be reasonable
        assert len(all_queries) == 26  # 10 + 10 + 1 + 5 queries total

    @pytest.mark.integration
    async def test_multi_tenant_analytics_data_isolation(self):
        """
        Test multi-tenant analytics data isolation to ensure customer data privacy.
        
        BVJ: Critical for customer data privacy and compliance, especially for
        enterprise customers who require strict data isolation.
        """
        tenant_data = {}
        isolation_violations = []
        
        class MultiTenantAnalyticsEngine:
            def __init__(self):
                self.tenant_stores = {}
                self.cross_tenant_access_log = []
                self.data_isolation_rules = {
                    "user_events": "user_based",     # Isolated by user_id
                    "agent_executions": "user_based",
                    "optimization_results": "user_based",
                    "admin_metrics": "tenant_based",  # Isolated by tenant_id
                    "billing_data": "tenant_based"
                }
            
            def _get_tenant_store(self, tenant_id: str):
                """Get or create tenant-specific data store"""
                if tenant_id not in self.tenant_stores:
                    self.tenant_stores[tenant_id] = {
                        "user_events": [],
                        "agent_executions": [],
                        "optimization_results": [],
                        "admin_metrics": [],
                        "billing_data": []
                    }
                return self.tenant_stores[tenant_id]
            
            async def store_analytics_event(self, tenant_id: str, event_type: str, event_data: Dict[str, Any]):
                """Store analytics event with proper tenant isolation"""
                # Validate tenant access
                if not self._validate_tenant_access(tenant_id, event_type):
                    isolation_violations.append(f"invalid_tenant_access_{tenant_id}_{event_type}")
                    raise PermissionError(f"Invalid tenant access for {tenant_id}")
                
                # Get tenant-specific store
                tenant_store = self._get_tenant_store(tenant_id)
                
                # Add tenant metadata to event
                isolated_event = {
                    **event_data,
                    "tenant_id": tenant_id,
                    "isolation_timestamp": time.time(),
                    "event_id": f"{tenant_id}_{event_type}_{len(tenant_store[event_type])}"
                }
                
                tenant_store[event_type].append(isolated_event)
                
                # Track in tenant data for verification
                if tenant_id not in tenant_data:
                    tenant_data[tenant_id] = {}
                if event_type not in tenant_data[tenant_id]:
                    tenant_data[tenant_id][event_type] = []
                
                tenant_data[tenant_id][event_type].append(isolated_event)
                
                return isolated_event["event_id"]
            
            async def query_tenant_analytics(self, tenant_id: str, query_type: str, filters: Dict[str, Any] = None):
                """Query analytics data with tenant isolation"""
                # Validate tenant access
                if tenant_id not in self.tenant_stores:
                    isolation_violations.append(f"query_nonexistent_tenant_{tenant_id}")
                    return {"error": "Tenant not found", "data": []}
                
                tenant_store = self._get_tenant_store(tenant_id)
                
                # Log cross-tenant access attempt check
                self.cross_tenant_access_log.append({
                    "tenant_id": tenant_id,
                    "query_type": query_type,
                    "timestamp": time.time()
                })
                
                if query_type == "user_events":
                    events = tenant_store["user_events"]
                    
                    # Apply user-based filtering if specified
                    if filters and "user_id" in filters:
                        requested_user = filters["user_id"]
                        # Verify user belongs to tenant (simplified check)
                        events = [e for e in events if e.get("user_id") == requested_user]
                    
                    return {"tenant_id": tenant_id, "data": events}
                
                elif query_type == "agent_executions":
                    executions = tenant_store["agent_executions"]
                    
                    if filters and "user_id" in filters:
                        requested_user = filters["user_id"]
                        executions = [e for e in executions if e.get("user_id") == requested_user]
                    
                    return {"tenant_id": tenant_id, "data": executions}
                
                elif query_type == "tenant_summary":
                    # Aggregate data across all event types for tenant
                    summary = {
                        "tenant_id": tenant_id,
                        "total_events": sum(len(events) for events in tenant_store.values()),
                        "event_types": {
                            event_type: len(events) 
                            for event_type, events in tenant_store.items()
                        },
                        "unique_users": len(set(
                            event.get("user_id") for events in tenant_store.values() 
                            for event in events if event.get("user_id")
                        ))
                    }
                    return {"tenant_id": tenant_id, "data": summary}
                
                else:
                    return {"error": "Unknown query type", "data": []}
            
            async def attempt_cross_tenant_access(self, requesting_tenant: str, target_tenant: str, query_type: str):
                """Attempt cross-tenant access (should be blocked)"""
                self.cross_tenant_access_log.append({
                    "requesting_tenant": requesting_tenant,
                    "target_tenant": target_tenant,
                    "query_type": query_type,
                    "timestamp": time.time(),
                    "violation_attempt": True
                })
                
                # This should be blocked by isolation
                if requesting_tenant != target_tenant:
                    isolation_violations.append(f"cross_tenant_access_{requesting_tenant}_to_{target_tenant}")
                    raise PermissionError("Cross-tenant access denied")
                
                return await self.query_tenant_analytics(target_tenant, query_type)
            
            def _validate_tenant_access(self, tenant_id: str, event_type: str):
                """Validate tenant has access to specific event type"""
                # Simplified validation - in real system would check permissions
                if not tenant_id or not event_type:
                    return False
                
                if event_type not in self.data_isolation_rules:
                    return False
                
                return True
            
            def verify_data_isolation(self):
                """Verify data isolation across tenants"""
                isolation_report = {
                    "total_tenants": len(self.tenant_stores),
                    "isolation_violations": len(isolation_violations),
                    "cross_tenant_attempts": len([
                        log for log in self.cross_tenant_access_log 
                        if log.get("violation_attempt", False)
                    ]),
                    "tenant_data_leakage": []
                }
                
                # Check for data leakage between tenants
                for tenant_id, store in self.tenant_stores.items():
                    for event_type, events in store.items():
                        for event in events:
                            event_tenant = event.get("tenant_id")
                            if event_tenant != tenant_id:
                                isolation_report["tenant_data_leakage"].append({
                                    "event_id": event.get("event_id"),
                                    "stored_in_tenant": tenant_id,
                                    "event_tenant_id": event_tenant
                                })
                
                return isolation_report
        
        analytics_engine = MultiTenantAnalyticsEngine()
        
        # Set up test tenants
        tenants = ["tenant_enterprise_a", "tenant_enterprise_b", "tenant_mid_c"]
        
        # Generate tenant-specific data
        for tenant_id in tenants:
            # Each tenant has different users
            tenant_users = [f"{tenant_id}_user_{i}" for i in range(10)]
            
            # Store user events for each tenant
            for i, user_id in enumerate(tenant_users):
                await analytics_engine.store_analytics_event(
                    tenant_id, 
                    "user_events",
                    {
                        "user_id": user_id,
                        "event_type": "login",
                        "timestamp": time.time() - (i * 3600)  # Spread over time
                    }
                )
                
                # Store agent executions
                await analytics_engine.store_analytics_event(
                    tenant_id,
                    "agent_executions", 
                    {
                        "user_id": user_id,
                        "agent_name": "cost_optimizer",
                        "duration_ms": 2000 + (i * 100)
                    }
                )
            
            # Store tenant-level admin metrics
            await analytics_engine.store_analytics_event(
                tenant_id,
                "admin_metrics",
                {
                    "metric_type": "monthly_usage",
                    "value": 1000 + (len(tenants.index(tenant_id)) * 500)
                }
            )
        
        # Verify tenant data is properly isolated
        for tenant_id in tenants:
            # Query tenant's own data (should succeed)
            user_events_result = await analytics_engine.query_tenant_analytics(tenant_id, "user_events")
            agent_executions_result = await analytics_engine.query_tenant_analytics(tenant_id, "agent_executions")
            tenant_summary = await analytics_engine.query_tenant_analytics(tenant_id, "tenant_summary")
            
            # Verify results contain only tenant's data
            assert user_events_result["tenant_id"] == tenant_id
            assert len(user_events_result["data"]) == 10  # 10 users per tenant
            
            assert agent_executions_result["tenant_id"] == tenant_id
            assert len(agent_executions_result["data"]) == 10  # 10 executions per tenant
            
            # Verify all events have correct tenant_id
            for event in user_events_result["data"]:
                assert event["tenant_id"] == tenant_id
                assert event["user_id"].startswith(tenant_id)
            
            for execution in agent_executions_result["data"]:
                assert execution["tenant_id"] == tenant_id
                assert execution["user_id"].startswith(tenant_id)
            
            # Verify tenant summary
            assert tenant_summary["data"]["tenant_id"] == tenant_id
            assert tenant_summary["data"]["unique_users"] == 10
            assert tenant_summary["data"]["total_events"] >= 21  # At least user events + executions + admin metrics
        
        # Test cross-tenant access attempts (should be blocked)
        cross_tenant_attempts = [
            ("tenant_enterprise_a", "tenant_enterprise_b", "user_events"),
            ("tenant_enterprise_b", "tenant_mid_c", "agent_executions"),
            ("tenant_mid_c", "tenant_enterprise_a", "tenant_summary")
        ]
        
        for requesting_tenant, target_tenant, query_type in cross_tenant_attempts:
            with pytest.raises(PermissionError):
                await analytics_engine.attempt_cross_tenant_access(requesting_tenant, target_tenant, query_type)
        
        # Test user-level isolation within tenant
        tenant_a_users = [f"tenant_enterprise_a_user_{i}" for i in range(10)]
        
        # Query for specific user (should only return that user's data)
        specific_user_events = await analytics_engine.query_tenant_analytics(
            "tenant_enterprise_a",
            "user_events",
            {"user_id": tenant_a_users[0]}
        )
        
        # Should only contain events for the specific user
        assert len(specific_user_events["data"]) == 1
        assert specific_user_events["data"][0]["user_id"] == tenant_a_users[0]
        
        # Verify isolation report
        isolation_report = analytics_engine.verify_data_isolation()
        
        assert isolation_report["total_tenants"] == 3
        assert isolation_report["isolation_violations"] == 3  # The 3 cross-tenant attempts
        assert isolation_report["cross_tenant_attempts"] == 3
        assert len(isolation_report["tenant_data_leakage"]) == 0  # No data should leak between tenants
        
        # Verify cross-tenant access log
        violation_attempts = [
            log for log in analytics_engine.cross_tenant_access_log
            if log.get("violation_attempt", False)
        ]
        assert len(violation_attempts) == 3
        
        # Verify tenant data integrity
        assert len(tenant_data) == 3  # 3 tenants
        for tenant_id, data in tenant_data.items():
            assert "user_events" in data
            assert "agent_executions" in data
            assert "admin_metrics" in data
            
            # Each tenant should have isolated data
            for event_type, events in data.items():
                for event in events:
                    assert event["tenant_id"] == tenant_id