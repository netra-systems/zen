"""Integration Tests: Real Agent WebSocket Event Structure Validation - Issue #1021

Tests real agent execution against staging GCP services to validate WebSocket event structures
without Docker dependencies. Uses HTTPS/WSS endpoints for complete integration testing.

CRITICAL: These tests MUST FAIL initially to prove Issue #1021 exists in real environment,
then pass after unified_manager.py remediation.

Purpose: Validate WebSocket events from real agent workflows contain business fields
at the correct structural level for frontend consumption.

Business Value: $500K+ ARR - Ensures real-time chat functionality works with proper
event structure for 90% of platform value delivery.
"""

import asyncio
import json
import time
import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
import aiohttp
import websockets

from shared.isolated_environment import get_env
from tests.clients.factory import TestClientFactory
from test_framework.staging_config import StagingConfig


class RealAgentEventStructuresTests:
    """Integration test suite for real agent WebSocket event structures."""

    @pytest.fixture
    async def staging_config(self):
        """Get staging environment configuration."""
        config = StagingConfig()
        await config.initialize()
        return config

    @pytest.fixture
    async def authenticated_client(self, staging_config):
        """Get authenticated HTTP client for staging."""
        client = await staging_config.create_authenticated_client()
        yield client
        await client.close()

    @pytest.fixture
    async def websocket_client(self, staging_config):
        """Get authenticated WebSocket client for staging."""
        client = await staging_config.create_websocket_client()
        try:
            yield client
        finally:
            await client.close()

    @pytest.mark.integration
    @pytest.mark.staging
    async def test_real_agent_websocket_event_structures_comprehensive(self, authenticated_client, websocket_client):
        """Test real agent execution generates proper WebSocket event structures.

        COMPREHENSIVE INTEGRATION: Runs against staging GCP services - NO Docker required
        Tests complete agent workflow: agent_started -> tool_executing -> tool_completed -> agent_completed

        CRITICAL: This test FAILS initially due to Issue #1021 business data wrapping problems.
        """
        # Trigger real agent execution via staging API
        agent_request = {
            "message": "Please analyze system performance and search for optimization opportunities",
            "agent_type": "data_helper",
            "include_tools": True
        }

        # Send HTTP request to trigger agent execution with WebSocket events
        try:
            response = await authenticated_client.post(
                "/api/v1/chat/agents/execute",
                json=agent_request,
                headers={"Content-Type": "application/json"}
            )
            assert response.status == 200 or response.status == 202, f"Agent execution failed: {response.status}"
        except Exception as e:
            pytest.skip(f"Staging API not available: {e}")

        # Collect WebSocket events from real agent execution
        collected_events = []
        expected_event_types = {
            "agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"
        }
        found_event_types = set()

        timeout = 45.0  # Generous timeout for real agent execution
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # Receive WebSocket message with timeout
                message = await asyncio.wait_for(websocket_client.recv(), timeout=2.0)

                if isinstance(message, str):
                    try:
                        event = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                else:
                    event = message

                collected_events.append(event)
                event_type = event.get("type")
                if event_type in expected_event_types:
                    found_event_types.add(event_type)

                # Stop when we have all expected events or timeout
                if len(found_event_types) >= 3:  # At minimum agent_started, tool_executing, agent_completed
                    break

            except asyncio.TimeoutError:
                break
            except Exception as e:
                print(f"WebSocket receive error: {e}")
                break

        # Must receive some events from real agent
        assert len(collected_events) > 0, f"No WebSocket events received from real agent execution"
        assert len(found_event_types) > 0, f"No recognized event types found in {len(collected_events)} events"

        # Validate each event structure based on type
        structure_failures = []

        for event in collected_events:
            event_type = event.get("type")

            if event_type == "tool_executing":
                # CRITICAL VALIDATION: tool_executing MUST have top-level tool_name
                # Issue #1021: This fails because tool_name is wrapped in 'payload' or 'data'
                if "tool_name" not in event:
                    structure_failures.append(f"tool_executing missing top-level tool_name: {event}")
                if "tool_args" not in event and "parameters" not in event:
                    structure_failures.append(f"tool_executing missing top-level tool_args/parameters: {event}")

            elif event_type == "tool_completed":
                # CRITICAL VALIDATION: tool_completed MUST have top-level results and tool_name
                if "tool_name" not in event:
                    structure_failures.append(f"tool_completed missing top-level tool_name: {event}")
                if "results" not in event and "result" not in event:
                    structure_failures.append(f"tool_completed missing top-level results/result: {event}")
                if "execution_time" not in event and "duration" not in event and "duration_ms" not in event:
                    structure_failures.append(f"tool_completed missing top-level execution_time/duration: {event}")

            elif event_type == "agent_started":
                # CRITICAL VALIDATION: agent_started MUST have top-level user_id and agent_name
                if "user_id" not in event:
                    structure_failures.append(f"agent_started missing top-level user_id: {event}")
                if "agent_name" not in event and "agent_id" not in event:
                    structure_failures.append(f"agent_started missing top-level agent_name/agent_id: {event}")

            elif event_type == "agent_completed":
                # CRITICAL VALIDATION: agent_completed MUST have top-level final_response or result
                if "final_response" not in event and "result" not in event and "response" not in event:
                    structure_failures.append(f"agent_completed missing top-level final_response/result/response: {event}")

        # Report all structure failures - these prove Issue #1021 exists
        if structure_failures:
            failure_summary = "\n".join(structure_failures)
            pytest.fail(f"WebSocket event structure validation failures (Issue #1021):\n{failure_summary}")

    @pytest.mark.integration
    @pytest.mark.staging
    async def test_specific_tool_event_business_fields(self, authenticated_client, websocket_client):
        """Test specific tool execution events have required business fields at top level.

        FOCUSED TEST: Specifically validates tool_executing and tool_completed events
        have the exact business fields needed for frontend tool transparency.
        """
        # Request that will definitely trigger tool usage
        tool_request = {
            "message": "Search for recent data about system performance metrics",
            "agent_type": "data_helper",
            "force_tool_usage": True
        }

        try:
            response = await authenticated_client.post(
                "/api/v1/chat/agents/execute",
                json=tool_request
            )
            assert response.status in [200, 202], f"Tool execution request failed: {response.status}"
        except Exception as e:
            pytest.skip(f"Staging API unavailable: {e}")

        # Focus specifically on tool events
        tool_events = []
        timeout = 30.0
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(websocket_client.recv(), timeout=1.5)

                if isinstance(message, str):
                    event = json.loads(message)
                else:
                    event = message

                event_type = event.get("type")
                if event_type in ["tool_executing", "tool_completed"]:
                    tool_events.append(event)

                # Stop after finding both types or timeout
                types_found = {e.get("type") for e in tool_events}
                if "tool_executing" in types_found and "tool_completed" in types_found:
                    break

            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue

        # Validate we got tool events
        assert len(tool_events) > 0, "No tool events received from real agent execution"

        # Validate each tool event structure
        for event in tool_events:
            event_type = event.get("type")

            if event_type == "tool_executing":
                # These fields MUST be at top level for transparency
                assert "tool_name" in event, f"tool_executing event missing tool_name at top level: {event}"
                assert isinstance(event["tool_name"], str), f"tool_name must be string: {event}"
                assert event["tool_name"].strip(), f"tool_name cannot be empty: {event}"

                # Should have parameters or args
                has_params = "tool_args" in event or "parameters" in event or "args" in event
                assert has_params, f"tool_executing missing parameters at top level: {event}"

            elif event_type == "tool_completed":
                # Critical business fields for tool completion transparency
                assert "tool_name" in event, f"tool_completed event missing tool_name at top level: {event}"
                assert isinstance(event["tool_name"], str), f"tool_name must be string: {event}"

                # Must have results at top level
                has_results = "results" in event or "result" in event
                assert has_results, f"tool_completed missing results at top level: {event}"

                # Should have execution timing
                has_timing = any(field in event for field in ["execution_time", "duration", "duration_ms"])
                assert has_timing, f"tool_completed missing timing info at top level: {event}"

    @pytest.mark.integration
    @pytest.mark.staging
    async def test_event_structure_consistency_across_execution(self, authenticated_client, websocket_client):
        """Test that event structure is consistent throughout agent execution lifecycle.

        CONSISTENCY TEST: All events in a single agent execution should follow the same
        structural pattern - either all top-level business fields OR all wrapped fields,
        but not mixed patterns that confuse frontend consumers.
        """
        execution_request = {
            "message": "Run comprehensive analysis with multiple tools",
            "agent_type": "data_helper",
            "comprehensive": True
        }

        try:
            response = await authenticated_client.post("/api/v1/chat/agents/execute", json=execution_request)
            assert response.status in [200, 202]
        except Exception as e:
            pytest.skip(f"Staging API unavailable: {e}")

        # Collect complete execution event sequence
        all_events = []
        timeout = 40.0
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(websocket_client.recv(), timeout=2.0)

                if isinstance(message, str):
                    event = json.loads(message)
                else:
                    event = message

                all_events.append(event)

                # Stop on agent_completed
                if event.get("type") == "agent_completed":
                    break

            except asyncio.TimeoutError:
                continue

        assert len(all_events) > 0, "No events received from agent execution"

        # Analyze structural consistency
        events_with_top_level_business = 0
        events_with_wrapped_business = 0
        business_field_locations = []

        for event in all_events:
            event_type = event.get("type")

            # Check where business fields are located
            if event_type in ["tool_executing", "tool_completed", "agent_started", "agent_completed"]:

                # Look for business fields at top level
                top_level_business = any(field in event for field in [
                    "tool_name", "results", "execution_time", "agent_name", "final_response"
                ])

                # Look for business fields in nested structures
                wrapped_business = any(
                    isinstance(event.get(wrapper), dict) and
                    any(field in event[wrapper] for field in ["tool_name", "results", "execution_time", "agent_name", "final_response"])
                    for wrapper in ["payload", "data", "content"]
                    if wrapper in event
                )

                if top_level_business:
                    events_with_top_level_business += 1
                    business_field_locations.append(f"{event_type}: TOP_LEVEL")

                if wrapped_business:
                    events_with_wrapped_business += 1
                    business_field_locations.append(f"{event_type}: WRAPPED")

        # CONSISTENCY REQUIREMENT: All business events should follow the same pattern
        # Mixed patterns indicate Issue #1021 - inconsistent wrapping logic
        if events_with_top_level_business > 0 and events_with_wrapped_business > 0:
            pattern_analysis = "\n".join(business_field_locations)
            pytest.fail(f"INCONSISTENT event structure patterns detected (Issue #1021):\n{pattern_analysis}")

        # Should have found business fields somewhere
        total_business_events = events_with_top_level_business + events_with_wrapped_business
        assert total_business_events > 0, "No business fields found in any events - possible transmission failure"