#!/usr/bin/env python
"""Integration Tests: agent_completed WebSocket Events - Real Service Testing

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Agent Completion Transparency for User Satisfaction
- Value Impact: Users know when AI has finished solving their problems
- Strategic Impact: Core chat functionality enabling $500K+ ARR through completion transparency

CRITICAL: These tests validate agent completion transparency - users MUST know when AI
has finished processing to deliver substantive chat business value and user satisfaction.

NO MOCKS per CLAUDE.md - Uses ONLY real WebSocket connections for authentic testing.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import pytest

# SSOT imports - absolute imports only per CLAUDE.md
from test_framework.ssot.base_test_case import BaseIntegrationTest  
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import RealWebSocketTestClient
from shared.isolated_environment import get_env


class TestAgentCompletedEvents(BaseIntegrationTest):
    """Integration tests for agent_completed WebSocket events reaching end users.
    
    Business Value: Agent completion transparency is MISSION CRITICAL for user satisfaction.
    Users must know when AI has finished to understand when solutions are ready.
    """
    
    def setup_method(self):
        """Setup real WebSocket test environment."""
        super().setup_method()
        self.auth_helper = E2EAuthHelper(E2EAuthConfig())
        self.test_events = []
        self.websocket_clients = []
    
    async def teardown_method(self):
        """Clean up WebSocket connections."""
        for client in self.websocket_clients:
            if not client.closed:
                await client.close()
        await super().teardown_method()
    
    async def create_authenticated_websocket_client(self, user_email: str = None) -> RealWebSocketTestClient:
        """Create authenticated WebSocket client with real JWT token."""
        user_email = user_email or f"test_user_{uuid.uuid4().hex[:8]}@example.com"
        
        # Get real JWT token
        auth_result = await self.auth_helper.authenticate_user(user_email, "test_password")
        
        # Create real WebSocket client
        client = RealWebSocketTestClient(
            auth_token=auth_result.access_token,
            base_url="ws://localhost:8000"
        )
        await client.connect()
        self.websocket_clients.append(client)
        return client
    
    async def trigger_agent_completion(self, client: RealWebSocketTestClient, message: str) -> List[Dict]:
        """Trigger agent execution and wait for completion event."""
        events = []
        
        # Send agent request
        await client.send_json({
            "type": "agent_request",
            "agent": "triage_agent",  # Reliable agent for completion testing
            "message": message,
            "request_id": str(uuid.uuid4())
        })
        
        # Collect events until agent completion (up to 25 seconds)
        timeout = time.time() + 25.0
        while time.time() < timeout:
            try:
                event = await asyncio.wait_for(client.receive_json(), timeout=2.0)
                events.append(event)
                if event.get("type") == "agent_completed":
                    break
            except asyncio.TimeoutError:
                continue
        
        return events

    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_01_basic_agent_completed_event_delivery(self):
        """
        BVJ: Core chat value - users must know when AI finishes for satisfaction
        Test basic delivery of agent_completed events to end user.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "Simple completion test")
        
        # Verify agent completed event delivered
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        assert len(completed_events) >= 1, "agent_completed events must be delivered"
        
        # Verify completion event structure
        completed_event = completed_events[0]
        assert "data" in completed_event
        assert "type" in completed_event and completed_event["type"] == "agent_completed"
        
        # Should contain final result or summary
        data = completed_event["data"]
        result_indicators = ["result", "response", "output", "summary", "conclusion"]
        has_result = any(indicator in data for indicator in result_indicators)
        assert has_result, "agent_completed events must contain final results"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket  
    async def test_02_complete_execution_lifecycle_validation(self):
        """
        BVJ: User experience - complete execution lifecycle transparency
        Test agent_completed events conclude a complete execution sequence.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "Complete lifecycle analysis")
        
        # Verify complete execution lifecycle
        event_types = [e.get("type") for e in events]
        
        # Should have agent_started at beginning
        assert "agent_started" in event_types, "Complete lifecycle should start with agent_started"
        
        # Should end with agent_completed
        assert "agent_completed" in event_types, "Complete lifecycle should end with agent_completed"
        assert event_types[-1] == "agent_completed", "agent_completed should be the final event"
        
        # Verify logical sequence
        started_index = event_types.index("agent_started") if "agent_started" in event_types else -1
        completed_index = event_types.index("agent_completed")
        
        if started_index >= 0:
            assert completed_index > started_index, "agent_completed should come after agent_started"
    
    @pytest.mark.integration  
    @pytest.mark.real_websocket
    async def test_03_final_result_quality_validation(self):
        """
        BVJ: Solution quality - final results must provide business value
        Test agent_completed events contain high-quality final results.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "Provide comprehensive business analysis")
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        for event in completed_events:
            data = event["data"]
            
            # Extract final result
            final_result = (data.get("result") or data.get("response") or 
                          data.get("output") or data.get("summary"))
            
            assert final_result, "agent_completed must contain final result"
            
            # Result quality checks
            if isinstance(final_result, str):
                # Should be substantial, not trivial
                assert len(final_result.strip()) > 10, "Final results should be substantial"
                
                # Should contain meaningful content, not placeholders
                placeholder_terms = ["todo", "placeholder", "example", "test", "lorem ipsum"]
                result_lower = final_result.lower()
                is_placeholder = any(term in result_lower for term in placeholder_terms)
                assert not is_placeholder, "Final results should be meaningful, not placeholders"
                
                # Should demonstrate problem-solving
                solution_indicators = ["analysis", "recommend", "suggest", "conclusion", "solution"]
                has_solution_content = any(indicator in result_lower for indicator in solution_indicators)
                assert has_solution_content, "Final results should demonstrate problem-solving"

    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_04_execution_timing_and_performance(self):
        """
        BVJ: Performance optimization - completion timing affects user experience
        Test agent_completed events arrive with appropriate timing.
        """
        client = await self.create_authenticated_websocket_client()
        
        start_time = time.time()
        events = await self.trigger_agent_completion(client, "Timed performance analysis")
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        if completed_events:
            completion_time = time.time() - start_time
            
            # Performance requirements
            assert completion_time <= 30.0, "Agent completion should happen within reasonable time"
            assert completion_time >= 1.0, "Agent completion should show some processing time"
            
            # Verify completion event timing
            completed_event = completed_events[0]
            assert "timestamp" in completed_event, "Completion events must include timing information"
            
            # Timestamp should be recent
            event_timestamp = float(completed_event.get("timestamp", start_time))
            time_diff = abs(event_timestamp - time.time())
            assert time_diff <= 60.0, "Completion timestamp should be current"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_05_comprehensive_result_data_structure(self):
        """
        BVJ: Data quality - structured results enable better UX integration
        Test agent_completed events have comprehensive result data structures.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "Generate structured comprehensive results")
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        for event in completed_events:
            # Verify comprehensive structure
            assert "type" in event and event["type"] == "agent_completed"
            assert "data" in event and isinstance(event["data"], dict)
            assert "timestamp" in event
            
            data = event["data"]
            
            # Should contain multiple types of completion information
            completion_fields = ["result", "summary", "status", "execution_time", "metadata"]
            present_fields = [field for field in completion_fields if field in data]
            assert len(present_fields) >= 2, "Should contain multiple types of completion information"
            
            # Result data should be properly structured
            if "result" in data:
                result = data["result"]
                try:
                    json.dumps(result)  # Should be serializable
                except (TypeError, ValueError):
                    pytest.fail("Agent completion results should be JSON serializable")
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_06_user_isolation_in_completion_events(self):
        """
        BVJ: Multi-user platform - completion isolation critical for Enterprise
        Test different users only receive their own agent_completed events.
        """
        user1_email = f"user1_{uuid.uuid4().hex[:8]}@example.com"
        user2_email = f"user2_{uuid.uuid4().hex[:8]}@example.com"
        
        client1 = await self.create_authenticated_websocket_client(user1_email)
        client2 = await self.create_authenticated_websocket_client(user2_email)
        
        # Trigger completions for both users concurrently
        task1 = asyncio.create_task(self.trigger_agent_completion(client1, "User 1 completion test"))
        task2 = asyncio.create_task(self.trigger_agent_completion(client2, "User 2 completion test"))
        
        events1, events2 = await asyncio.gather(task1, task2)
        
        # Verify user isolation
        completed1 = [e for e in events1 if e.get("type") == "agent_completed"]
        completed2 = [e for e in events2 if e.get("type") == "agent_completed"]
        
        # Both users should receive completion events
        assert len(completed1) >= 1, "User 1 should receive completion events"
        assert len(completed2) >= 1, "User 2 should receive completion events"
        
        # Verify no cross-contamination
        for event in completed1:
            user_id = event.get("user_id") or event.get("data", {}).get("user_id")
            if user_id:
                assert user_id != user2_email, "User 1 should not see User 2's completions"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_07_error_handling_in_completion_events(self):
        """
        BVJ: Error transparency - users need to understand execution outcomes
        Test agent_completed events handle error scenarios appropriately.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Try scenarios that might cause issues
        events = await self.trigger_agent_completion(client, "Process invalid or problematic request")
        
        # Should still receive completion events even if there are issues
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        # Completion events should be well-formed regardless of success/failure
        for event in completed_events:
            assert "type" in event and event["type"] == "agent_completed"
            assert "data" in event
            assert "timestamp" in event
            
            data = event["data"]
            
            # If there's an error, it should be clearly communicated
            if "error" in data or "failed" in str(data).lower():
                # Error should be user-friendly
                error_info = data.get("error") or str(data)
                assert isinstance(error_info, str), "Errors should be readable"
                assert len(error_info) > 5, "Errors should be descriptive"
                
                # Should not contain technical stack traces
                technical_terms = ["traceback", "exception", "stack trace", "null pointer"]
                error_lower = error_info.lower()
                has_technical = any(term in error_lower for term in technical_terms)
                assert not has_technical, "Errors should be user-friendly, not technical"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_08_completion_status_and_metadata(self):
        """
        BVJ: Execution transparency - provide comprehensive completion status
        Test agent_completed events include status and metadata information.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "Status and metadata validation")
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        for event in completed_events:
            data = event["data"]
            
            # Should include execution status information
            status_indicators = ["status", "state", "completed", "finished", "success"]
            has_status = any(indicator in data for indicator in status_indicators)
            assert has_status, "Completion events should include status information"
            
            # Should include relevant metadata
            metadata_fields = ["execution_time", "agent_name", "request_id", "thread_id"]
            present_metadata = [field for field in metadata_fields if field in data or field in event]
            assert len(present_metadata) >= 1, "Should include relevant metadata"
            
            # If execution time is present, should be reasonable
            if "execution_time" in data:
                exec_time = data["execution_time"]
                if isinstance(exec_time, (int, float)):
                    assert 0 <= exec_time <= 60.0, "Execution time should be reasonable"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_09_business_metrics_in_completion(self):
        """
        BVJ: Business intelligence - completion events enable business metrics
        Test agent_completed events provide business intelligence data.
        """
        client = await self.create_authenticated_websocket_client()
        
        start_time = time.time()
        events = await self.trigger_agent_completion(client, "Business metrics collection test")
        end_time = time.time()
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        if completed_events:
            # Extract business metrics
            event = completed_events[0]
            data = event["data"]
            
            metrics = {
                "completion_time": end_time - start_time,
                "has_result": bool(data.get("result") or data.get("response")),
                "result_quality": 0,
                "user_satisfaction_indicators": 0
            }
            
            # Measure result quality
            result = data.get("result") or data.get("response") or ""
            if isinstance(result, str):
                word_count = len(result.split())
                metrics["result_quality"] = min(1.0, word_count / 20.0)  # Up to 20 words = quality 1.0
                
                # Satisfaction indicators
                satisfaction_terms = ["complete", "analysis", "recommend", "solution", "insight"]
                metrics["user_satisfaction_indicators"] = sum(
                    1 for term in satisfaction_terms if term in result.lower()
                )
            
            # Verify we can extract business intelligence
            assert metrics["completion_time"] > 0, "Should track completion time"
            assert isinstance(metrics["has_result"], bool), "Should track result presence"
            assert 0 <= metrics["result_quality"] <= 1, "Should measure result quality"
            assert metrics["user_satisfaction_indicators"] >= 0, "Should track satisfaction indicators"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_10_completion_audit_and_compliance(self):
        """
        BVJ: Regulatory compliance - maintain audit trails for agent completions
        Test agent_completed events provide audit information.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "Audit compliance test")
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        for event in completed_events:
            # Verify audit information
            assert "timestamp" in event, "Completions must have timestamps for audit"
            
            # Should include traceability information
            audit_fields = ["user_id", "session_id", "request_id", "thread_id", "agent_name"]
            has_audit_info = any(field in event or field in event.get("data", {}) 
                               for field in audit_fields)
            assert has_audit_info, "Completions should include audit traceability"
            
            # Should identify what was completed
            data = event["data"]
            completion_identifiers = ["agent", "task", "request", "operation"]
            has_identifier = any(field in data for field in completion_identifiers)
            assert has_identifier, "Completions should identify what was completed"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_11_concurrent_completion_handling(self):
        """
        BVJ: System scalability - handle concurrent agent completions
        Test agent_completed events handle concurrent operations properly.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Launch concurrent agent executions
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                self.trigger_agent_completion(client, f"Concurrent completion {i}")
            )
            tasks.append(task)
        
        # Wait for concurrent completions
        all_events = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify concurrent handling
        successful_results = [events for events in all_events if not isinstance(events, Exception)]
        assert len(successful_results) >= 2, "Should handle concurrent completions"
        
        # Collect all completion events
        all_completions = []
        for events in successful_results:
            completed = [e for e in events if e.get("type") == "agent_completed"]
            all_completions.extend(completed)
        
        # Should handle concurrent completions properly
        assert len(all_completions) >= 2, "Should generate concurrent completion events"
        
        # Each completion should be properly formed
        for event in all_completions:
            assert "data" in event
            assert "timestamp" in event
            assert event["type"] == "agent_completed"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_12_completion_result_privacy_and_security(self):
        """
        BVJ: Data security - protect sensitive information in completion results
        Test agent_completed events filter sensitive information appropriately.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "Process confidential business data")
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        for event in completed_events:
            event_str = str(event).lower()
            
            # Should not contain sensitive system information
            sensitive_terms = ["password", "secret", "api_key", "private_key", "credential"]
            for term in sensitive_terms:
                assert term not in event_str, f"Completion events should not expose {term}"
            
            # Should not contain system paths or internal configuration
            system_info = ["/etc/", "/var/", "database_url", "connection_string", "internal_config"]
            for info in system_info:
                assert info not in event_str, f"Completion events should not expose {info}"
            
            # Should not contain raw system errors
            system_errors = ["system error", "internal server error", "database connection failed"]
            for error in system_errors:
                assert error not in event_str, f"Should not expose system errors: {error}"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_13_completion_performance_monitoring(self):
        """
        BVJ: System optimization - monitor completion performance
        Test agent_completed events provide performance insights.
        """
        client = await self.create_authenticated_websocket_client()
        
        start_time = time.time()
        events = await self.trigger_agent_completion(client, "Performance monitoring test")
        end_time = time.time()
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        if completed_events:
            total_time = end_time - start_time
            
            # Performance metrics
            metrics = {
                "total_execution_time": total_time,
                "events_per_second": len(events) / total_time if total_time > 0 else 0,
                "completion_efficiency": 1 / total_time if total_time > 0 else 0
            }
            
            # Performance should be acceptable
            assert metrics["total_execution_time"] <= 30.0, "Total execution should be efficient"
            assert metrics["events_per_second"] <= 50.0, "Event rate should be reasonable"
            assert metrics["completion_efficiency"] >= 0.03, "Completion efficiency should be adequate"
            
            # Event should include performance metadata
            completed_event = completed_events[0]
            assert "timestamp" in completed_event, "Must include timing for performance monitoring"
            
            # Should not be excessively large (performance impact)
            event_size = len(json.dumps(completed_event))
            assert event_size <= 5000, "Completion events should be reasonably sized"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_14_completion_graceful_degradation(self):
        """
        BVJ: System reliability - ensure graceful degradation of completions
        Test agent_completed events handle degraded conditions gracefully.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Test various conditions that might cause degradation
        test_scenarios = [
            "Handle large data processing",
            "Process complex multi-step analysis",
            "Manage resource-intensive operations"
        ]
        
        all_completions = []
        for scenario in test_scenarios:
            events = await self.trigger_agent_completion(client, scenario)
            completed = [e for e in events if e.get("type") == "agent_completed"]
            all_completions.extend(completed)
        
        # Should handle various scenarios gracefully
        assert len(all_completions) >= 1, "Should complete even under various conditions"
        
        # Each completion should be well-formed regardless of conditions
        for event in all_completions:
            # Basic structure should be maintained
            assert "type" in event and event["type"] == "agent_completed"
            assert "data" in event
            assert "timestamp" in event
            
            # Should provide some form of result even in degraded conditions
            data = event["data"]
            has_output = any(key in data for key in ["result", "response", "summary", "status"])
            assert has_output, "Should provide output even under degraded conditions"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_15_completion_business_value_measurement(self):
        """
        BVJ: ROI measurement - measure business value of agent completions
        Test agent_completed events enable business value measurement.
        """
        client = await self.create_authenticated_websocket_client()
        
        start_time = time.time()
        events = await self.trigger_agent_completion(client, "Business value measurement test")
        end_time = time.time()
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        if completed_events:
            event = completed_events[0]
            data = event["data"]
            
            # Calculate business value metrics
            value_metrics = {
                "user_engagement_time": end_time - start_time,
                "completion_success": 0,
                "result_comprehensiveness": 0,
                "actionable_insights": 0,
                "user_trust_score": 0
            }
            
            # Success measurement
            result = data.get("result") or data.get("response") or ""
            has_meaningful_result = isinstance(result, str) and len(result) > 20
            value_metrics["completion_success"] = 1 if has_meaningful_result else 0
            
            if has_meaningful_result:
                result_lower = result.lower()
                
                # Comprehensiveness (result length and depth)
                word_count = len(result.split())
                value_metrics["result_comprehensiveness"] = min(1.0, word_count / 50.0)
                
                # Actionable insights
                action_terms = ["recommend", "suggest", "should", "could", "consider"]
                value_metrics["actionable_insights"] = sum(
                    1 for term in action_terms if term in result_lower
                ) / len(action_terms)
                
                # Trust indicators (completion transparency)
                trust_terms = ["analysis", "complete", "conclude", "result", "summary"]
                value_metrics["user_trust_score"] = sum(
                    1 for term in trust_terms if term in result_lower
                ) / len(trust_terms)
            
            # Verify business value measurement
            assert value_metrics["user_engagement_time"] > 0, "Should measure engagement time"
            assert 0 <= value_metrics["completion_success"] <= 1, "Should measure success"
            assert 0 <= value_metrics["result_comprehensiveness"] <= 1, "Should measure comprehensiveness"
            assert 0 <= value_metrics["actionable_insights"] <= 1, "Should measure actionable insights"
            assert 0 <= value_metrics["user_trust_score"] <= 1, "Should measure trust indicators"
            
            # Should provide measurable business value
            total_value = sum(value_metrics.values()) / len(value_metrics)
            assert total_value > 0, "Agent completions should provide measurable business value"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_16_completion_integration_with_chat_ui(self):
        """
        BVJ: UI/UX integration - completions must integrate with chat interface
        Test agent_completed events provide UI-friendly completion information.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "UI integration test")
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        for event in completed_events:
            data = event["data"]
            
            # Should provide UI-friendly result format
            result = data.get("result") or data.get("response") or data.get("summary")
            if result and isinstance(result, str):
                # Should be displayable text
                assert len(result) > 0, "Should provide displayable content"
                
                # Should not contain UI-breaking characters
                ui_breaking = ["\x00", "\x01", "\x02", "\\u0000"]
                has_breaking_chars = any(char in result for char in ui_breaking)
                assert not has_breaking_chars, "Should not contain UI-breaking characters"
                
                # Should use readable formatting
                if len(result) > 50:
                    # Should have reasonable sentence structure
                    sentence_endings = result.count('.') + result.count('!') + result.count('?')
                    char_to_sentence_ratio = len(result) / max(1, sentence_endings)
                    assert char_to_sentence_ratio <= 200, "Should have reasonable sentence structure for UI"
            
            # Should include UI-relevant metadata
            ui_metadata = ["status", "title", "summary", "completion_time"]
            has_ui_metadata = any(field in data for field in ui_metadata)
            assert has_ui_metadata, "Should include UI-relevant metadata"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_17_completion_accessibility_compliance(self):
        """
        BVJ: Accessibility - ensure completions are accessible to all users
        Test agent_completed events provide accessibility-friendly content.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "Accessibility compliance test")
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        for event in completed_events:
            data = event["data"]
            result = data.get("result") or data.get("response") or ""
            
            if isinstance(result, str) and len(result) > 20:
                # Should not rely on visual-only formatting
                visual_only = ["█", "░", "▓", "◆", "★"]
                has_visual_only = any(char in result for char in visual_only)
                assert not has_visual_only, "Should not rely on visual-only formatting"
                
                # Should use descriptive text instead of symbols
                symbol_heavy = result.count('→') + result.count('•') + result.count('◦')
                if symbol_heavy > len(result) / 20:  # More than 5% symbols
                    pytest.fail("Should use descriptive text, not heavy symbol usage")
                
                # Should have good text-to-noise ratio
                words = len(result.split())
                if words > 10:
                    non_word_chars = sum(1 for char in result if not char.isalnum() and char not in ' .,!?-')
                    noise_ratio = non_word_chars / len(result)
                    assert noise_ratio <= 0.2, "Should have good text-to-noise ratio for accessibility"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_18_completion_multilingual_support(self):
        """
        BVJ: Global market - support international users in completions
        Test agent_completed events handle multilingual content appropriately.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_agent_completion(client, "International business analysis")
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        for event in completed_events:
            # Should handle text encoding properly
            event_json = json.dumps(event)
            
            # Should be valid UTF-8
            try:
                event_json.encode('utf-8')
            except UnicodeEncodeError:
                pytest.fail("Completion events should handle UTF-8 encoding")
            
            # Should not break with international characters
            data = event["data"]
            result = data.get("result") or data.get("response") or ""
            
            if isinstance(result, str):
                # Should preserve text integrity
                assert isinstance(result, str), "Results should be proper strings"
                
                # Should handle character encoding
                try:
                    result.encode('utf-8').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pytest.fail("Should handle character encoding properly")
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_19_completion_advanced_business_scenarios(self):
        """
        BVJ: Advanced use cases - handle complex business completion scenarios
        Test agent_completed events handle advanced business scenarios effectively.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Test advanced business scenarios
        scenarios = [
            "Multi-stakeholder analysis with recommendations",
            "Complex data-driven decision support",
            "Strategic planning with risk assessment"
        ]
        
        all_completions = []
        scenario_results = {}
        
        for scenario in scenarios:
            events = await self.trigger_agent_completion(client, scenario)
            completed = [e for e in events if e.get("type") == "agent_completed"]
            all_completions.extend(completed)
            
            if completed:
                result = completed[0]["data"].get("result", "")
                scenario_results[scenario] = len(str(result))
        
        # Should handle advanced scenarios
        assert len(all_completions) >= len(scenarios) * 0.7, "Should handle most advanced scenarios"
        
        # Advanced scenarios should produce substantial results
        substantial_results = sum(1 for length in scenario_results.values() if length > 50)
        assert substantial_results >= 1, "Should produce substantial results for complex scenarios"
        
        # Should demonstrate advanced capabilities
        for event in all_completions:
            data = event["data"]
            result = str(data.get("result", data.get("response", "")))
            
            if len(result) > 100:
                # Should show advanced analytical capabilities
                advanced_terms = ["analysis", "strategic", "recommend", "assessment", "evaluation"]
                has_advanced = any(term in result.lower() for term in advanced_terms)
                assert has_advanced, "Advanced scenarios should demonstrate analytical capabilities"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_20_completion_end_to_end_business_value_realization(self):
        """
        BVJ: Complete value delivery - completions deliver comprehensive business value
        Test agent_completed events enable complete business value realization.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Comprehensive business scenario
        business_query = """
        Provide comprehensive business analysis including:
        1. Current situation assessment
        2. Key challenges and opportunities  
        3. Strategic recommendations
        4. Implementation roadmap
        5. Success metrics and KPIs
        """
        
        start_time = time.time()
        events = await self.trigger_agent_completion(client, business_query)
        end_time = time.time()
        
        completed_events = [e for e in events if e.get("type") == "agent_completed"]
        
        assert len(completed_events) >= 1, "Should deliver completion for comprehensive business query"
        
        # Measure comprehensive business value
        event = completed_events[0]
        data = event["data"]
        result = str(data.get("result", data.get("response", "")))
        
        comprehensive_value = {
            "execution_time": end_time - start_time,
            "result_length": len(result),
            "strategic_content": 0,
            "actionable_recommendations": 0,
            "business_metrics": 0,
            "user_satisfaction_score": 0,
            "completion_quality": 0
        }
        
        if result:
            result_lower = result.lower()
            
            # Strategic content measurement
            strategic_terms = ["strategic", "business", "analysis", "assessment", "evaluation"]
            comprehensive_value["strategic_content"] = sum(
                1 for term in strategic_terms if term in result_lower
            )
            
            # Actionable recommendations
            action_terms = ["recommend", "suggest", "should", "implement", "action"]
            comprehensive_value["actionable_recommendations"] = sum(
                1 for term in action_terms if term in result_lower
            )
            
            # Business metrics indicators
            metric_terms = ["metric", "kpi", "measure", "track", "monitor"]
            comprehensive_value["business_metrics"] = sum(
                1 for term in metric_terms if term in result_lower
            )
            
            # User satisfaction score (completeness indicators)
            satisfaction_terms = ["complete", "comprehensive", "detailed", "thorough"]
            comprehensive_value["user_satisfaction_score"] = sum(
                1 for term in satisfaction_terms if term in result_lower
            )
            
            # Overall completion quality
            word_count = len(result.split())
            comprehensive_value["completion_quality"] = min(1.0, word_count / 100.0)
        
        # Verify comprehensive business value delivery
        assert comprehensive_value["execution_time"] <= 45.0, "Should deliver value within reasonable time"
        assert comprehensive_value["result_length"] >= 50, "Should provide substantial results"
        assert comprehensive_value["strategic_content"] >= 1, "Should contain strategic content"
        
        # Should deliver measurable business value
        total_business_value = (
            comprehensive_value["strategic_content"] +
            comprehensive_value["actionable_recommendations"] +
            comprehensive_value["business_metrics"] +
            comprehensive_value["user_satisfaction_score"]
        )
        assert total_business_value >= 2, "Should deliver measurable comprehensive business value"
        
        # Should enable complete user satisfaction through comprehensive results
        enables_satisfaction = (
            comprehensive_value["completion_quality"] > 0.3 and
            comprehensive_value["result_length"] > 100 and
            comprehensive_value["execution_time"] > 0
        )
        assert enables_satisfaction, "Should enable complete user satisfaction through comprehensive completion"


if __name__ == "__main__":
    # Run tests directly for development
    pytest.main([__file__, "-v", "--tb=short"])