#!/usr/bin/env python
"""Integration Tests: tool_completed WebSocket Events - Real Service Testing

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Tool Result Transparency for User Satisfaction
- Value Impact: Users see AI tool results, building confidence in solutions
- Strategic Impact: Core chat functionality enabling $500K+ ARR through result transparency

CRITICAL: These tests validate tool completion transparency - users MUST see AI tool
results to understand how problems were solved and deliver substantive chat business value.

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


class TestToolCompletedEvents(BaseIntegrationTest):
    """Integration tests for tool_completed WebSocket events reaching end users.
    
    Business Value: Tool completion transparency is MISSION CRITICAL for user satisfaction.
    Users must see AI tool results to understand solutions and deliver chat value.
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
    
    async def trigger_tool_completion(self, client: RealWebSocketTestClient, message: str) -> List[Dict]:
        """Trigger agent execution and collect tool completion events."""
        events = []
        
        # Send agent request that requires tool usage
        await client.send_json({
            "type": "agent_request",
            "agent": "data_analyst_agent",  # Agent likely to use and complete tools
            "message": message,
            "request_id": str(uuid.uuid4())
        })
        
        # Collect events for up to 20 seconds (tools need time to complete)
        timeout = time.time() + 20.0
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
    async def test_01_basic_tool_completed_event_delivery(self):
        """
        BVJ: Core chat value - users must see tool results for satisfaction
        Test basic delivery of tool_completed events to end user.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Analyze data and provide results")
        
        # Verify tool completed events delivered
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        assert len(tool_events) >= 1, "tool_completed events must be delivered"
        
        # Verify tool completion event structure
        tool_event = tool_events[0]
        assert "data" in tool_event
        assert "result" in tool_event["data"] or "output" in tool_event["data"] or "response" in tool_event["data"]
        
        # Should identify which tool completed
        tool_identifier = tool_event["data"].get("tool_name") or tool_event["data"].get("tool")
        assert tool_identifier, "tool_completed events must identify completed tool"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket  
    async def test_02_successful_tool_completion_results(self):
        """
        BVJ: Result quality - users need meaningful tool results
        Test tool_completed events contain meaningful results for successful executions.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Calculate basic statistics")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            data = event["data"]
            
            # Should contain actual results
            result_fields = ["result", "output", "response", "data", "value"]
            has_results = any(field in data for field in result_fields)
            assert has_results, "tool_completed events must contain results"
            
            # Results should be meaningful (not empty/null)
            for field in result_fields:
                if field in data and data[field] is not None:
                    result_value = data[field]
                    if isinstance(result_value, str):
                        assert len(result_value.strip()) > 0, "String results should not be empty"
                    elif isinstance(result_value, (list, dict)):
                        assert len(result_value) > 0, "Collection results should not be empty"
    
    @pytest.mark.integration  
    @pytest.mark.real_websocket
    async def test_03_tool_result_data_structure_validation(self):
        """
        BVJ: Data quality - structured results enable better UX
        Test tool_completed events have proper result data structures.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Process structured data")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            # Verify required structure
            assert "type" in event and event["type"] == "tool_completed"
            assert "data" in event and isinstance(event["data"], dict)
            assert "timestamp" in event
            
            # Verify result structure is accessible
            data = event["data"]
            if "result" in data:
                result = data["result"]
                # Result should be serializable (basic validation)
                try:
                    json.dumps(result)
                except (TypeError, ValueError):
                    pytest.fail("Tool results should be JSON serializable")

    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_04_tool_completion_timing_validation(self):
        """
        BVJ: Performance optimization - completion timing affects user experience
        Test tool_completed events arrive with appropriate timing.
        """
        client = await self.create_authenticated_websocket_client()
        
        start_time = time.time()
        events = await self.trigger_tool_completion(client, "Timed analysis task")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        if tool_events:
            for event in tool_events:
                event_time = float(event.get("timestamp", start_time))
                completion_delay = event_time - start_time
                
                # Tool completion should happen within reasonable time
                assert completion_delay <= 30.0, "Tool completion should not take excessively long"
                assert completion_delay >= 0.1, "Tool completion timing should be realistic"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_05_tool_result_formatting_and_presentation(self):
        """
        BVJ: User experience - well-formatted results improve satisfaction
        Test tool_completed events format results appropriately for users.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Generate formatted report")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            data = event["data"]
            
            # Check for user-friendly formatting
            result = data.get("result") or data.get("output") or data.get("response")
            if result and isinstance(result, str):
                # Should not contain raw technical output
                technical_artifacts = ["</", "<?", "{\"", "null,", "undefined"]
                clean_result = not any(artifact in result for artifact in technical_artifacts)
                assert clean_result, "Tool results should be user-friendly, not raw technical output"
                
                # Should be readable length (not too long or too short for a result)
                if len(result) > 5:  # Meaningful results
                    assert len(result) <= 2000, "Tool results should be reasonably sized for display"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_06_tool_error_completion_handling(self):
        """
        BVJ: Error transparency - users need to understand tool failures
        Test tool_completed events handle and communicate tool errors properly.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Try to trigger potential tool error scenarios
        events = await self.trigger_tool_completion(client, "Access invalid data source")
        
        # Should get some events even if tools fail
        all_events = [e for e in events]
        assert len(all_events) >= 1, "Should receive events even with potential tool issues"
        
        # Look for tool completed events
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            data = event["data"]
            
            # If there's an error, it should be clearly communicated
            if "error" in data or "failed" in str(data).lower():
                # Error should be user-friendly, not technical
                error_info = data.get("error") or str(data)
                assert not any(tech_term in error_info.lower() 
                             for tech_term in ["traceback", "stack", "exception", "null pointer"]), \
                    "Errors should be user-friendly, not technical"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_07_multiple_tool_completion_sequence(self):
        """
        BVJ: Complex workflow transparency - show multi-step completion
        Test tool_completed events for tasks involving multiple tools.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Multi-step analysis: research, calculate, summarize")
        
        tool_completed_events = [e for e in events if e.get("type") == "tool_completed"]
        
        if len(tool_completed_events) >= 2:
            # Verify completion sequence
            timestamps = []
            for event in tool_completed_events:
                timestamp = float(event.get("timestamp", 0))
                timestamps.append(timestamp)
            
            # Should complete in logical order
            for i in range(1, len(timestamps)):
                assert timestamps[i] >= timestamps[i-1], "Tool completions should be in sequence"
            
            # Each completion should have distinct results
            results = []
            for event in tool_completed_events:
                result = event["data"].get("result") or event["data"].get("output")
                if result:
                    results.append(str(result))
            
            # Results should generally be distinct (not identical)
            if len(results) >= 2:
                unique_results = set(results)
                assert len(unique_results) >= len(results) * 0.5, "Tool results should generally be distinct"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_08_tool_result_privacy_filtering(self):
        """
        BVJ: Data security - protect sensitive information in tool results
        Test tool_completed events filter sensitive information from results.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Analyze business confidential data")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            event_str = str(event).lower()
            
            # Should not contain sensitive system information
            sensitive_terms = ["password", "secret", "api_key", "private_key", "token"]
            for term in sensitive_terms:
                assert term not in event_str, f"Tool results should not expose {term}"
            
            # Should not contain system configuration details
            system_info = ["/etc/", "/var/", "c:\\windows", "database_url", "connection_string"]
            for info in system_info:
                assert info not in event_str, f"Tool results should not expose {info}"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_09_tool_completion_user_isolation(self):
        """
        BVJ: Multi-user platform - ensure user-specific tool results
        Test different users only receive their own tool_completed events.
        """
        user1_email = f"user1_{uuid.uuid4().hex[:8]}@example.com"
        user2_email = f"user2_{uuid.uuid4().hex[:8]}@example.com"
        
        client1 = await self.create_authenticated_websocket_client(user1_email)
        client2 = await self.create_authenticated_websocket_client(user2_email)
        
        # Trigger tool completion for both users
        task1 = asyncio.create_task(self.trigger_tool_completion(client1, "User 1 specific analysis"))
        task2 = asyncio.create_task(self.trigger_tool_completion(client2, "User 2 specific calculation"))
        
        events1, events2 = await asyncio.gather(task1, task2)
        
        # Verify user isolation in tool results
        tools1 = [e for e in events1 if e.get("type") == "tool_completed"]
        tools2 = [e for e in events2 if e.get("type") == "tool_completed"]
        
        # Verify no cross-contamination of results
        for event in tools1:
            user_id = event.get("user_id") or event.get("data", {}).get("user_id")
            if user_id:
                assert user_id != user2_email, "User 1 should not receive User 2's tool results"
        
        for event in tools2:
            user_id = event.get("user_id") or event.get("data", {}).get("user_id")  
            if user_id:
                assert user_id != user1_email, "User 2 should not receive User 1's tool results"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_10_tool_result_quality_assurance(self):
        """
        BVJ: Output quality - ensure tool results meet quality standards
        Test tool_completed events deliver high-quality results.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Quality analysis with detailed results")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            data = event["data"]
            
            # Quality checks for results
            result = data.get("result") or data.get("output") or data.get("response")
            if result:
                # Result should be meaningful (not placeholder text)
                placeholder_indicators = ["todo", "placeholder", "example", "sample", "test data"]
                result_str = str(result).lower()
                is_placeholder = any(indicator in result_str for indicator in placeholder_indicators)
                assert not is_placeholder, "Tool results should be meaningful, not placeholders"
                
                # Result should have substance (not trivial)
                if isinstance(result, str) and len(result) > 10:
                    word_count = len(result.split())
                    assert word_count >= 3, "Substantial tool results should have multiple words"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_11_tool_completion_performance_metrics(self):
        """
        BVJ: Performance monitoring - track tool completion performance
        Test tool_completed events provide performance insights.
        """
        client = await self.create_authenticated_websocket_client()
        
        start_time = time.time()
        events = await self.trigger_tool_completion(client, "Performance measurement test")
        end_time = time.time()
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        if tool_events:
            total_duration = end_time - start_time
            
            # Performance metrics
            metrics = {
                "total_completions": len(tool_events),
                "avg_completion_time": total_duration / len(tool_events),
                "completion_rate": len(tool_events) / total_duration
            }
            
            # Performance should be reasonable
            assert metrics["avg_completion_time"] <= 15.0, "Average tool completion time should be reasonable"
            assert metrics["completion_rate"] >= 0.05, "Tool completion rate should be adequate"
            
            # Each completion event should be properly timed
            for event in tool_events:
                assert "timestamp" in event, "Tool completions must include timing for performance tracking"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_12_tool_result_business_value_content(self):
        """
        BVJ: Business outcomes - tool results should provide business value
        Test tool_completed events contain business-relevant information.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Business analysis for decision making")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            data = event["data"]
            result = data.get("result") or data.get("output") or data.get("response")
            
            if result and isinstance(result, str) and len(result) > 20:
                # Should contain business-relevant content
                business_indicators = [
                    "analysis", "result", "data", "information", "finding",
                    "recommendation", "insight", "conclusion", "summary"
                ]
                
                result_lower = result.lower()
                has_business_content = any(indicator in result_lower for indicator in business_indicators)
                assert has_business_content, "Tool results should contain business-relevant content"
                
                # Should not be purely technical/system output
                technical_only = ["debug", "log", "trace", "system", "internal", "config"]
                is_technical_only = any(tech in result_lower for tech in technical_only) and \
                                   not any(biz in result_lower for biz in business_indicators)
                assert not is_technical_only, "Tool results should be business-focused, not purely technical"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_13_tool_completion_audit_trail(self):
        """
        BVJ: Compliance tracking - maintain audit trails for tool completions
        Test tool_completed events provide audit information.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Auditable business process")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            # Verify audit trail information
            assert "timestamp" in event, "Tool completions must have timestamps for audit"
            
            # Should include traceability
            audit_fields = ["user_id", "session_id", "request_id", "thread_id", "tool_name", "tool"]
            has_audit_info = any(field in event or field in event.get("data", {}) 
                               for field in audit_fields)
            assert has_audit_info, "Tool completions should include audit traceability"
            
            # Should identify what was completed
            data = event["data"]
            completion_id = (data.get("tool_name") or data.get("tool") or 
                           data.get("operation") or data.get("task"))
            assert completion_id, "Tool completions must identify what was completed"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_14_tool_result_data_integrity(self):
        """
        BVJ: Data quality assurance - ensure result data integrity
        Test tool_completed events maintain data integrity in results.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Data integrity validation test")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            # Verify event structure integrity
            assert isinstance(event, dict), "Tool completion events must be valid dictionaries"
            assert "type" in event and event["type"] == "tool_completed"
            assert "data" in event and isinstance(event["data"], dict)
            
            # Verify result data integrity
            data = event["data"]
            if "result" in data:
                result = data["result"]
                # Result should be consistently typed
                assert result is not None or "error" in data, "Results should not be null unless there's an error"
                
                # If result is structured, verify integrity
                if isinstance(result, dict):
                    # Dictionary should be properly formed
                    try:
                        json.dumps(result)
                    except (TypeError, ValueError):
                        pytest.fail("Structured results should be JSON serializable")
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_15_concurrent_tool_completion_handling(self):
        """
        BVJ: System scalability - handle concurrent tool completions
        Test tool_completed events handle concurrent operations properly.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Launch concurrent tasks
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                self.trigger_tool_completion(client, f"Concurrent completion task {i}")
            )
            tasks.append(task)
        
        # Wait for concurrent completions
        all_events = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify concurrent handling
        successful_results = [events for events in all_events if not isinstance(events, Exception)]
        assert len(successful_results) >= 2, "Should handle concurrent tool completions"
        
        # Collect all tool completion events
        all_tool_events = []
        for events in successful_results:
            tool_events = [e for e in events if e.get("type") == "tool_completed"]
            all_tool_events.extend(tool_events)
        
        # Should properly handle concurrent completions
        if all_tool_events:
            # Each completion should be properly formed
            for event in all_tool_events:
                assert "data" in event
                assert "timestamp" in event
                assert event["type"] == "tool_completed"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_16_tool_completion_resource_cleanup(self):
        """
        BVJ: Resource efficiency - ensure proper cleanup after tool completion
        Test tool_completed events indicate proper resource management.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Resource cleanup validation")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        # Check for resource efficiency indicators
        for event in tool_events:
            event_size = len(json.dumps(event))
            assert event_size <= 3000, "Tool completion events should be reasonably sized"
            
            # Should not contain excessive debug information
            data = event["data"]
            debug_indicators = ["debug", "verbose", "trace", "internal_state"]
            data_str = str(data).lower()
            has_excessive_debug = any(indicator in data_str for indicator in debug_indicators)
            assert not has_excessive_debug, "Tool completions should not contain excessive debug info"
            
            # Should contain essential completion information
            essential_fields = ["result", "output", "response", "status", "completed"]
            has_essential = any(field in data for field in essential_fields)
            assert has_essential, "Tool completions should contain essential information"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_17_tool_result_accessibility_formatting(self):
        """
        BVJ: User accessibility - ensure results are accessible to all users
        Test tool_completed events format results for accessibility.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Accessible result formatting test")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        for event in tool_events:
            data = event["data"]
            result = data.get("result") or data.get("output") or data.get("response")
            
            if result and isinstance(result, str):
                # Check for accessibility-friendly formatting
                # Should not rely solely on visual formatting
                visual_only_formatting = ["&nbsp;", "<i>", "<b>", "░", "▓"]
                has_visual_only = any(formatting in result for formatting in visual_only_formatting)
                assert not has_visual_only, "Results should not rely on visual-only formatting"
                
                # Should use clear, descriptive text
                if len(result) > 30:
                    # Should have reasonable word-to-character ratio (readable text)
                    words = len(result.split())
                    chars = len(result)
                    word_ratio = words / chars if chars > 0 else 0
                    assert word_ratio >= 0.1, "Results should be readable text, not encoded data"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_18_tool_completion_business_intelligence(self):
        """
        BVJ: Business optimization - extract intelligence from tool completions
        Test tool_completed events enable business intelligence collection.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_completion(client, "Business intelligence data collection")
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        # Collect business intelligence metrics
        bi_metrics = {
            "completion_count": len(tool_events),
            "success_rate": 0,
            "avg_result_quality": 0,
            "tool_usage_patterns": {}
        }
        
        if tool_events:
            # Calculate success rate
            successful_completions = 0
            quality_scores = []
            
            for event in tool_events:
                data = event["data"]
                
                # Success indicators
                has_result = bool(data.get("result") or data.get("output") or data.get("response"))
                has_error = "error" in data or "failed" in str(data).lower()
                
                if has_result and not has_error:
                    successful_completions += 1
                
                # Quality score (0-1 based on result substance)
                result = data.get("result") or data.get("output") or data.get("response") or ""
                if isinstance(result, str):
                    quality = min(1.0, len(result.split()) / 10.0)  # Up to 10 words = quality 1.0
                    quality_scores.append(quality)
                
                # Track tool usage
                tool_name = data.get("tool_name") or data.get("tool") or "unknown"
                bi_metrics["tool_usage_patterns"][tool_name] = \
                    bi_metrics["tool_usage_patterns"].get(tool_name, 0) + 1
            
            bi_metrics["success_rate"] = successful_completions / len(tool_events)
            bi_metrics["avg_result_quality"] = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Verify actionable business intelligence
        assert bi_metrics["completion_count"] >= 0, "Should track completion count"
        assert 0 <= bi_metrics["success_rate"] <= 1, "Should track success rate"
        assert 0 <= bi_metrics["avg_result_quality"] <= 1, "Should measure result quality"
        
        # Should provide actionable insights
        has_actionable_data = (
            bi_metrics["completion_count"] > 0 or
            bi_metrics["success_rate"] > 0 or
            len(bi_metrics["tool_usage_patterns"]) > 0
        )
        assert has_actionable_data, "Should provide actionable business intelligence"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_19_tool_completion_error_recovery(self):
        """
        BVJ: System reliability - ensure graceful handling of tool failures
        Test tool_completed events handle error scenarios gracefully.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Try scenarios that might cause tool issues
        test_scenarios = [
            "Process invalid data format",
            "Access restricted resource", 
            "Perform complex calculation with edge cases"
        ]
        
        all_events = []
        for scenario in test_scenarios:
            events = await self.trigger_tool_completion(client, scenario)
            all_events.extend(events)
        
        # Should handle various scenarios gracefully
        tool_events = [e for e in all_events if e.get("type") == "tool_completed"]
        
        # Even with potential errors, should get some tool events
        # Error handling should be graceful, not silent failures
        for event in tool_events:
            # Event should be well-formed regardless of success/failure
            assert "type" in event and event["type"] == "tool_completed"
            assert "data" in event
            assert "timestamp" in event
            
            # If there's an error, it should be communicated clearly
            data = event["data"]
            if "error" in data:
                error = data["error"]
                assert isinstance(error, str), "Errors should be readable strings"
                assert len(error) > 5, "Errors should be descriptive"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_20_tool_completion_end_to_end_value_delivery(self):
        """
        BVJ: Complete value delivery - tool completions deliver end-to-end business value
        Test tool_completed events enable complete business value realization.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Test comprehensive business scenario
        business_query = "Analyze current performance, identify improvements, and provide actionable recommendations"
        
        start_time = time.time()
        events = await self.trigger_tool_completion(client, business_query)
        end_time = time.time()
        
        tool_events = [e for e in events if e.get("type") == "tool_completed"]
        
        # Measure end-to-end value delivery
        value_metrics = {
            "completion_time": end_time - start_time,
            "tools_completed": len(tool_events),
            "value_delivered": 0,
            "user_satisfaction_indicators": 0,
            "actionable_results": 0
        }
        
        # Analyze value delivered
        total_result_content = ""
        actionable_indicators = ["recommend", "suggest", "should", "could", "improve", "optimize"]
        satisfaction_indicators = ["complete", "success", "result", "analysis", "insight"]
        
        for event in tool_events:
            data = event["data"]
            result = str(data.get("result", data.get("output", data.get("response", ""))))
            total_result_content += result.lower()
        
        # Calculate value metrics
        if total_result_content:
            value_metrics["actionable_results"] = sum(
                1 for indicator in actionable_indicators 
                if indicator in total_result_content
            )
            value_metrics["user_satisfaction_indicators"] = sum(
                1 for indicator in satisfaction_indicators 
                if indicator in total_result_content
            )
            value_metrics["value_delivered"] = len(total_result_content) / 100.0  # Content richness
        
        # Verify end-to-end value delivery
        assert value_metrics["completion_time"] <= 30.0, "Should deliver value within reasonable time"
        assert value_metrics["tools_completed"] >= 0, "Should track tool completion progress"
        
        # Should deliver actual business value
        delivers_value = (
            value_metrics["actionable_results"] > 0 or
            value_metrics["user_satisfaction_indicators"] > 0 or
            value_metrics["value_delivered"] > 0.5
        )
        assert delivers_value, "Tool completions should deliver measurable business value"
        
        # Should enable user satisfaction
        enables_satisfaction = (
            value_metrics["tools_completed"] > 0 and
            value_metrics["completion_time"] > 0 and
            len(total_result_content) > 10
        )
        assert enables_satisfaction, "Tool completions should enable user satisfaction through meaningful results"


if __name__ == "__main__":
    # Run tests directly for development
    pytest.main([__file__, "-v", "--tb=short"])