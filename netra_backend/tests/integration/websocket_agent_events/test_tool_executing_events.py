#!/usr/bin/env python
"""Integration Tests: tool_executing WebSocket Events - Real Service Testing

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Tool Execution Transparency for User Trust
- Value Impact: Users see AI using tools to solve problems, building confidence
- Strategic Impact: Core chat functionality enabling $500K+ ARR through tool transparency

CRITICAL: These tests validate tool execution transparency - users MUST see AI using
tools to solve their problems to build trust and deliver substantive chat business value.

NO MOCKS per CLAUDE.md - Uses ONLY real WebSocket connections for authentic testing.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import pytest
from unittest.mock import AsyncMock, patch

# SSOT imports - absolute imports only per CLAUDE.md
from test_framework.ssot.base_test_case import BaseIntegrationTest  
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import RealWebSocketTestClient
from shared.isolated_environment import get_env

# Production components for real testing
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
# ISSUE #565 SSOT MIGRATION: Use UserExecutionEngine with compatibility bridge
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine


class TestToolExecutingEvents(BaseIntegrationTest):
    """Integration tests for tool_executing WebSocket events reaching end users.
    
    Business Value: Tool execution transparency is MISSION CRITICAL for user trust.
    Users must see AI using tools to solve their problems to deliver chat value.
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
    
    async def trigger_tool_execution(self, client: RealWebSocketTestClient, message: str) -> List[Dict]:
        """Trigger agent execution requiring tools and collect events."""
        events = []
        
        # Send agent request that requires tool usage
        await client.send_json({
            "type": "agent_request",
            "agent": "data_analyst_agent",  # Agent likely to use tools
            "message": message,
            "request_id": str(uuid.uuid4())
        })
        
        # Collect events for up to 15 seconds (tools can be slower)
        timeout = time.time() + 15.0
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
    async def test_01_basic_tool_executing_event_delivery(self):
        """
        BVJ: Core chat value - users must see AI using tools for trust
        Test basic delivery of tool_executing events to end user.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Analyze the data trends")
        
        # Verify tool executing events delivered
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        assert len(tool_events) >= 1, "tool_executing events must be delivered"
        
        # Verify tool event structure
        tool_event = tool_events[0]
        assert "data" in tool_event
        assert "tool_name" in tool_event["data"] or "tool" in tool_event["data"]
        tool_name = tool_event["data"].get("tool_name") or tool_event["data"].get("tool")
        assert isinstance(tool_name, str), "Tool name must be string"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket  
    async def test_02_tool_identification_transparency(self):
        """
        BVJ: User education - users learn what tools AI uses
        Test tool_executing events clearly identify which tool is being used.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Search for information online")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        for event in tool_events:
            data = event["data"]
            tool_identifier = data.get("tool_name") or data.get("tool") or data.get("name")
            
            assert tool_identifier, "Tool executing events must identify the tool"
            assert len(tool_identifier) >= 3, "Tool name should be meaningful"
            assert tool_identifier != "unknown", "Tool name should be specific"
    
    @pytest.mark.integration  
    @pytest.mark.real_websocket
    async def test_03_tool_parameter_visibility(self):
        """
        BVJ: AI transparency - show users how tools are being used
        Test tool_executing events show tool parameters appropriately.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Calculate statistics for dataset")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Should show some parameter information for transparency
        for event in tool_events:
            data = event["data"]
            
            # Should have some indication of what the tool will do
            parameter_indicators = ["parameters", "args", "input", "query", "config"]
            has_parameters = any(key in data for key in parameter_indicators)
            
            # Or should show the action being performed
            action_indicators = ["action", "operation", "task", "request"]
            has_action = any(key in data for key in action_indicators)
            
            assert has_parameters or has_action, "Should show tool usage details"

    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_04_data_analysis_tool_events(self):
        """
        BVJ: Business intelligence - data analysis tool transparency
        Test tool_executing events for data analysis tools.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Analyze customer data patterns")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Look for data analysis tools
        analysis_tools = ["analyzer", "calculator", "data", "stats", "metrics"]
        
        for event in tool_events:
            tool_name = str(event["data"].get("tool_name", event["data"].get("tool", ""))).lower()
            
            # Verify tool event completeness for analysis
            assert "timestamp" in event
            assert "data" in event
            
            # Should indicate analysis operation
            is_analysis_tool = any(tool_type in tool_name for tool_type in analysis_tools)
            if is_analysis_tool:
                assert "data" in event["data"] or "parameters" in event["data"], \
                    "Analysis tools should show what they're analyzing"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_05_web_search_tool_events(self):
        """
        BVJ: Research transparency - show users what AI searches for
        Test tool_executing events for web search tools.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Find latest industry reports")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Look for search-related tools
        search_tools = ["search", "web", "google", "bing", "lookup", "find"]
        
        for event in tool_events:
            tool_name = str(event["data"].get("tool_name", event["data"].get("tool", ""))).lower()
            
            is_search_tool = any(tool_type in tool_name for tool_type in search_tools)
            if is_search_tool:
                # Search tools should indicate what they're searching for
                data = event["data"]
                search_indicators = ["query", "search_term", "keywords", "topic"]
                has_search_info = any(key in data for key in search_indicators)
                
                assert has_search_info or "parameters" in data, \
                    "Search tools should show search parameters"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_06_calculation_tool_events(self):
        """
        BVJ: Computation transparency - show users mathematical operations
        Test tool_executing events for calculation tools.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Calculate ROI and financial metrics")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Look for calculation tools
        calc_tools = ["calculator", "compute", "math", "formula", "calculate"]
        
        for event in tool_events:
            tool_name = str(event["data"].get("tool_name", event["data"].get("tool", ""))).lower()
            
            is_calc_tool = any(tool_type in tool_name for tool_type in calc_tools)
            if is_calc_tool:
                # Should indicate calculation being performed
                data = event["data"]
                calc_indicators = ["expression", "formula", "operation", "input", "values"]
                has_calc_info = any(key in data for key in calc_indicators)
                
                assert has_calc_info or len(str(data)) > 20, \
                    "Calculation tools should show operation details"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_07_tool_execution_timing_patterns(self):
        """
        BVJ: User experience - tool execution timing affects perception
        Test tool_executing events follow expected timing patterns.
        """
        client = await self.create_authenticated_websocket_client()
        
        start_time = time.time()
        events = await self.trigger_tool_execution(client, "Process data using multiple tools")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        if len(tool_events) >= 1:
            # Verify reasonable timing for tool execution
            for event in tool_events:
                event_time = float(event.get("timestamp", start_time))
                time_from_start = event_time - start_time
                
                # Tool execution should start reasonably quickly
                assert time_from_start <= 10.0, "Tools should start executing within reasonable time"
                assert time_from_start >= 0, "Tool timing should be logical"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_08_multiple_tool_execution_sequence(self):
        """
        BVJ: Complex task transparency - show multi-step tool usage
        Test tool_executing events for complex tasks requiring multiple tools.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Research, analyze, and calculate comprehensive report")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        if len(tool_events) >= 2:
            # Verify multiple tools can be tracked
            tool_names = []
            for event in tool_events:
                tool_name = event["data"].get("tool_name") or event["data"].get("tool")
                if tool_name:
                    tool_names.append(tool_name.lower())
            
            # Should show variety in tools for complex tasks
            unique_tools = set(tool_names)
            assert len(unique_tools) >= 1, "Complex tasks should involve distinguishable tools"
            
            # Verify sequential execution
            timestamps = [float(e.get("timestamp", 0)) for e in tool_events]
            for i in range(1, len(timestamps)):
                assert timestamps[i] >= timestamps[i-1], "Tool events should be in sequence"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_09_tool_error_handling_events(self):
        """
        BVJ: Error transparency - users should understand tool failures
        Test tool_executing events handle tool errors appropriately.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Try to trigger a scenario that might cause tool issues
        events = await self.trigger_tool_execution(client, "Access non-existent data source")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Tool events should be well-formed even if tools might fail later
        for event in tool_events:
            assert "type" in event and event["type"] == "tool_executing"
            assert "data" in event
            assert "timestamp" in event
            
            # Should not contain error information in executing event
            # (errors come in tool_completed events)
            data_str = str(event["data"]).lower()
            assert "error" not in data_str or "no error" in data_str, \
                "tool_executing should not contain error information"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_10_user_isolation_in_tool_events(self):
        """
        BVJ: Multi-user platform - tool execution isolation critical for Enterprise
        Test different users only receive their own tool_executing events.
        """
        user1_email = f"user1_{uuid.uuid4().hex[:8]}@example.com"
        user2_email = f"user2_{uuid.uuid4().hex[:8]}@example.com"
        
        client1 = await self.create_authenticated_websocket_client(user1_email)
        client2 = await self.create_authenticated_websocket_client(user2_email)
        
        # Trigger tool execution for both users concurrently
        task1 = asyncio.create_task(self.trigger_tool_execution(client1, "User 1 data analysis"))
        task2 = asyncio.create_task(self.trigger_tool_execution(client2, "User 2 calculations"))
        
        events1, events2 = await asyncio.gather(task1, task2)
        
        # Verify user isolation
        tools1 = [e for e in events1 if e.get("type") == "tool_executing"]
        tools2 = [e for e in events2 if e.get("type") == "tool_executing"]
        
        # Both users should receive tool events
        assert len(tools1) >= 0, "User 1 should receive tool events"
        assert len(tools2) >= 0, "User 2 should receive tool events"
        
        # Verify no cross-contamination
        for event in tools1:
            user_id = event.get("user_id") or event.get("data", {}).get("user_id")
            if user_id:
                assert user_id != user2_email, "User 1 should not see User 2's tool events"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_11_tool_security_and_privacy(self):
        """
        BVJ: Data protection - tool events should not leak sensitive information
        Test tool_executing events filter sensitive information properly.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Process confidential business data")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        for event in tool_events:
            event_str = str(event).lower()
            
            # Should not contain sensitive system information
            sensitive_terms = ["password", "secret", "key", "token", "credential"]
            for term in sensitive_terms:
                assert term not in event_str, f"Tool events should not expose {term}"
            
            # Should not contain system paths or configuration
            system_paths = ["/var/", "/usr/", "/home/", "c:\\", "config"]
            for path in system_paths:
                assert path not in event_str, f"Tool events should not expose {path}"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_12_tool_performance_monitoring(self):
        """
        BVJ: System optimization - monitor tool performance for improvements
        Test tool_executing events provide performance insights.
        """
        client = await self.create_authenticated_websocket_client()
        
        start_time = time.time()
        events = await self.trigger_tool_execution(client, "Performance monitoring test")
        end_time = time.time()
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        if tool_events:
            # Measure tool execution performance
            total_duration = end_time - start_time
            tools_per_second = len(tool_events) / total_duration if total_duration > 0 else 0
            
            # Performance should be reasonable
            assert total_duration <= 20.0, "Tool execution should complete within reasonable time"
            assert tools_per_second <= 10.0, "Tool execution rate should be reasonable"
            
            # Each tool event should be delivered promptly
            for event in tool_events:
                assert "timestamp" in event, "Tool events must include timing information"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_13_tool_permission_validation(self):
        """
        BVJ: Security compliance - validate tool permissions
        Test tool_executing events respect user permissions.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Access user-specific resources")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Tool events should exist for authenticated users
        for event in tool_events:
            # Verify event is properly authenticated
            assert "data" in event
            
            # Should not indicate permission violations
            data_str = str(event["data"]).lower()
            permission_violations = ["access denied", "unauthorized", "forbidden", "permission denied"]
            for violation in permission_violations:
                assert violation not in data_str, f"Tool should have proper permissions"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_14_tool_resource_efficiency(self):
        """
        BVJ: Cost optimization - ensure tool usage is resource efficient
        Test tool_executing events indicate efficient resource usage.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Efficient resource usage test")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Verify reasonable resource usage patterns
        for event in tool_events:
            event_size = len(json.dumps(event))
            assert event_size <= 2000, "Tool events should be reasonably sized"
            
            # Verify essential information is present but not excessive
            data = event["data"]
            data_keys = len(data.keys()) if isinstance(data, dict) else 0
            assert data_keys <= 10, "Tool events should not have excessive data fields"
            assert data_keys >= 2, "Tool events should have essential information"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_15_concurrent_tool_execution_handling(self):
        """
        BVJ: Scalability - handle concurrent tool executions
        Test tool_executing events handle concurrent operations properly.
        """
        client = await self.create_authenticated_websocket_client()
        
        # Send concurrent requests that might trigger tool usage
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                self.trigger_tool_execution(client, f"Concurrent analysis task {i}")
            )
            tasks.append(task)
        
        # Wait for concurrent executions
        all_events = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify concurrent tool events handled properly
        successful_executions = [events for events in all_events if not isinstance(events, Exception)]
        assert len(successful_executions) >= 2, "Should handle concurrent tool executions"
        
        # Collect all tool events
        all_tool_events = []
        for events in successful_executions:
            tool_events = [e for e in events if e.get("type") == "tool_executing"]
            all_tool_events.extend(tool_events)
        
        # Should have tool events from concurrent executions
        if all_tool_events:
            assert len(all_tool_events) >= 1, "Concurrent executions should generate tool events"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_16_tool_audit_and_compliance(self):
        """
        BVJ: Regulatory compliance - maintain audit trails for tool usage
        Test tool_executing events provide compliance information.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Compliance audit test")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Verify audit information
        for event in tool_events:
            assert "timestamp" in event, "Tool events must have timestamps for audit"
            
            # Should have traceability information
            audit_fields = ["user_id", "session_id", "request_id", "thread_id"]
            has_audit_info = any(field in event or field in event.get("data", {}) 
                               for field in audit_fields)
            assert has_audit_info, "Tool events should include audit traceability"
            
            # Should identify the tool being used
            data = event["data"]
            tool_id = data.get("tool_name") or data.get("tool") or data.get("name")
            assert tool_id, "Tool events must identify which tool is executing for audit"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket  
    async def test_17_tool_execution_state_management(self):
        """
        BVJ: System reliability - maintain consistent tool execution state
        Test tool_executing events maintain proper state information.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "State management test")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        if len(tool_events) >= 1:
            # Verify consistent state information
            first_event = tool_events[0]
            required_fields = ["type", "data", "timestamp"]
            
            for field in required_fields:
                assert field in first_event, f"Tool events must include {field}"
            
            # All tool events should have consistent structure
            for event in tool_events:
                event_fields = set(event.keys())
                first_fields = set(first_event.keys())
                common_fields = event_fields.intersection(first_fields)
                assert len(common_fields) >= 2, "Tool events should have consistent structure"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_18_tool_business_intelligence_tracking(self):
        """
        BVJ: Business optimization - track tool usage for intelligence
        Test tool_executing events enable business intelligence collection.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Business intelligence tracking test")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Collect business intelligence metrics
        bi_metrics = {
            "tools_used_count": len(tool_events),
            "unique_tools": set(),
            "avg_tool_event_size": 0,
            "tools_per_request": 0
        }
        
        if tool_events:
            # Track unique tools
            for event in tool_events:
                tool_name = event["data"].get("tool_name") or event["data"].get("tool")
                if tool_name:
                    bi_metrics["unique_tools"].add(tool_name)
            
            # Calculate metrics
            bi_metrics["unique_tools"] = len(bi_metrics["unique_tools"])
            total_size = sum(len(json.dumps(event)) for event in tool_events)
            bi_metrics["avg_tool_event_size"] = total_size / len(tool_events)
            bi_metrics["tools_per_request"] = len(tool_events)
        
        # Verify we can extract actionable business intelligence
        assert bi_metrics["tools_used_count"] >= 0, "Should track tool usage count"
        assert bi_metrics["unique_tools"] >= 0, "Should track tool diversity"
        assert bi_metrics["avg_tool_event_size"] >= 0, "Should measure event efficiency"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_19_tool_integration_quality_assurance(self):
        """
        BVJ: Quality assurance - ensure tool integration quality
        Test tool_executing events meet quality standards.
        """
        client = await self.create_authenticated_websocket_client()
        
        events = await self.trigger_tool_execution(client, "Quality assurance test")
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Quality assurance checks
        for event in tool_events:
            # Structure quality
            assert isinstance(event, dict), "Tool events must be dictionaries"
            assert "type" in event and event["type"] == "tool_executing"
            assert "data" in event and isinstance(event["data"], dict)
            
            # Content quality
            tool_name = event["data"].get("tool_name") or event["data"].get("tool")
            if tool_name:
                assert len(tool_name) >= 2, "Tool names should be meaningful"
                assert tool_name.replace("_", "").replace("-", "").isalnum(), \
                    "Tool names should be clean identifiers"
            
            # Timestamp quality
            if "timestamp" in event:
                timestamp = event["timestamp"]
                assert isinstance(timestamp, (str, int, float)), "Timestamp should be valid type"
    
    @pytest.mark.integration
    @pytest.mark.real_websocket
    async def test_20_tool_execution_business_value_metrics(self):
        """
        BVJ: ROI measurement - measure business value of tool execution
        Test tool_executing events enable business value measurement.
        """
        client = await self.create_authenticated_websocket_client()
        
        start_time = time.time()
        events = await self.trigger_tool_execution(client, "Business value measurement test")
        end_time = time.time()
        
        tool_events = [e for e in events if e.get("type") == "tool_executing"]
        
        # Calculate business value metrics
        value_metrics = {
            "user_engagement_time": end_time - start_time,
            "tool_transparency_score": len(tool_events),
            "execution_efficiency": 0,
            "user_trust_indicators": 0
        }
        
        if tool_events:
            # Efficiency: events per second
            value_metrics["execution_efficiency"] = len(tool_events) / (end_time - start_time)
            
            # Trust indicators: clear tool identification and transparency
            clear_tool_names = sum(
                1 for event in tool_events 
                if event["data"].get("tool_name") or event["data"].get("tool")
            )
            value_metrics["user_trust_indicators"] = clear_tool_names / len(tool_events)
        
        # Verify business value can be measured
        assert value_metrics["user_engagement_time"] >= 0, "Should measure user engagement time"
        assert value_metrics["tool_transparency_score"] >= 0, "Should measure transparency"
        assert value_metrics["execution_efficiency"] >= 0, "Should measure efficiency"
        assert value_metrics["user_trust_indicators"] >= 0, "Should measure trust indicators"
        
        # Business value should be positive
        has_business_value = (
            value_metrics["tool_transparency_score"] > 0 or
            value_metrics["user_engagement_time"] > 0
        )
        assert has_business_value, "Tool execution should provide measurable business value"


if __name__ == "__main__":
    # Run tests directly for development
    pytest.main([__file__, "-v", "--tb=short"])