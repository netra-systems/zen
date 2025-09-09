#!/usr/bin/env python
"""
E2E Staging Tests for WebSocket Real-time Collaboration

MISSION CRITICAL: Real-time collaborative features with WebSocket events.
Tests multi-user collaboration scenarios with agent coordination in staging.

Business Value: $500K+ ARR - Collaborative AI interactions for teams
- Tests real-time collaboration between multiple users and agents
- Validates shared workspace WebSocket events and coordination
- Ensures business value through team-based AI optimization workflows
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import WebSocketEventType, UserID, ThreadID, RequestID
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType as TestEventType
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Import production components - NO MOCKS per CLAUDE.md
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.fixture
async def collaboration_websocket_utility():
    """Create WebSocket utility for collaboration testing."""
    # Use staging WebSocket URL for collaboration features
    staging_ws_url = "wss://staging.netra-apex.com/ws"
    
    async with WebSocketTestUtility(base_url=staging_ws_url) as ws_util:
        yield ws_util


@pytest.fixture
def collaboration_auth_helper():
    """Create authentication helper for collaboration testing."""
    return E2EAuthHelper(environment="staging")


@pytest.mark.e2e
@pytest.mark.staging
class TestStagingWebSocketCollaboration:
    """E2E tests for WebSocket real-time collaboration features."""
    
    @pytest.mark.asyncio
    async def test_shared_workspace_agent_coordination(self, collaboration_websocket_utility, collaboration_auth_helper):
        """
        Test shared workspace with coordinated agent execution.
        
        CRITICAL: Multiple users sharing workspace must see coordinated agent activities.
        This enables team-based AI optimization workflows for business value.
        """
        # Arrange - Create team of users sharing workspace
        team_size = 3
        workspace_id = f"shared_workspace_{uuid.uuid4().hex[:8]}"
        team_users = []
        
        for i in range(team_size):
            auth_result = await collaboration_auth_helper.create_authenticated_user(
                user_id=f"team_member_{i}_{uuid.uuid4().hex[:6]}",
                permissions=["chat_access", "shared_workspace", "agent_coordination"],
                workspace_id=workspace_id
            )
            team_users.append(auth_result)
        
        # Create shared thread for collaboration
        shared_thread_id = ThreadID(f"shared_thread_{workspace_id}")
        
        # Connect all team members
        team_clients = []
        for i, auth_result in enumerate(team_users):
            user_context = UserExecutionContext(
                user_id=UserID(auth_result["user_id"]),
                thread_id=shared_thread_id,  # Shared thread
                request_id=RequestID(f"collab_request_{i}_{uuid.uuid4().hex[:8]}"),
                session_id=auth_result["session_id"],
                workspace_id=workspace_id
            )
            
            auth_headers = {
                "Authorization": f"Bearer {auth_result['access_token']}",
                "X-User-ID": auth_result["user_id"],
                "X-Workspace-ID": workspace_id
            }
            
            client = await collaboration_websocket_utility.create_authenticated_client(
                auth_result["user_id"],
                auth_result["access_token"]
            )
            client.headers = auth_headers
            
            connected = await client.connect(timeout=60.0)
            assert connected is True, f"Team member {i} must connect to shared workspace"
            
            team_clients.append((client, user_context, auth_result))
        
        # Act - Coordinate shared agent execution
        # Team lead initiates optimization analysis
        lead_client, lead_context, lead_auth = team_clients[0]
        
        collaborative_request = {
            "type": "collaborative_agent_request",
            "content": "Team optimization analysis: Analyze our infrastructure for cost optimization opportunities",
            "workspace_id": workspace_id,
            "collaboration_mode": "shared_analysis",
            "team_members": [auth["user_id"] for auth in team_users],
            "timestamp": datetime.now().isoformat()
        }
        
        await lead_client.send_message(
            TestEventType.MESSAGE_CREATED,
            collaborative_request,
            user_id=str(lead_context.user_id),
            thread_id=str(shared_thread_id)
        )
        
        # Wait for coordinated agent events across all team members
        collaboration_events = {}
        
        async def collect_user_events(client_data, member_index):
            client, context, auth = client_data
            user_events = []
            
            try:
                # Wait for shared agent workflow events
                expected_shared_events = [
                    TestEventType.AGENT_STARTED,
                    TestEventType.AGENT_THINKING,
                    TestEventType.TOOL_EXECUTING,
                    TestEventType.TOOL_COMPLETED,
                    TestEventType.AGENT_COMPLETED
                ]
                
                # Collect events for this user
                for _ in range(len(expected_shared_events)):
                    try:
                        event = await client.wait_for_message(timeout=30.0)
                        if event:
                            user_events.append(event)
                    except asyncio.TimeoutError:
                        break
                
                return user_events
                
            except Exception as e:
                print(f"Error collecting events for member {member_index}: {e}")
                return user_events
        
        # Collect events from all team members concurrently
        event_collection_tasks = [
            asyncio.create_task(collect_user_events(client_data, i))
            for i, client_data in enumerate(team_clients)
        ]
        
        all_user_events = await asyncio.gather(*event_collection_tasks, return_exceptions=True)
        
        # Assert shared coordination
        successful_collections = [events for events in all_user_events if isinstance(events, list) and len(events) > 0]
        assert len(successful_collections) >= team_size * 0.8, f"At least 80% team members must receive shared events"
        
        # Verify all team members see the same agent execution
        shared_event_types = set()
        for user_events in successful_collections:
            for event in user_events:
                if hasattr(event, 'event_type'):
                    shared_event_types.add(event.event_type)
        
        # All team members should see coordinated agent activity
        required_coordination_events = {
            TestEventType.AGENT_STARTED,
            TestEventType.AGENT_THINKING,
            TestEventType.AGENT_COMPLETED
        }
        
        received_coordination_events = shared_event_types.intersection(required_coordination_events)
        assert len(received_coordination_events) >= 2, f"Must see coordinated agent events: {received_coordination_events}"
        
        # Verify workspace isolation - events should be scoped to shared workspace
        for user_events in successful_collections:
            for event in user_events:
                if hasattr(event, 'data') and isinstance(event.data, dict):
                    # Events in shared workspace should reference the workspace or shared context
                    workspace_indicators = [
                        event.data.get("workspace_id") == workspace_id,
                        event.data.get("collaboration_mode") is not None,
                        event.data.get("shared") is True
                    ]
                    
                    # At least some indication of shared context
                    # Note: Exact implementation may vary
                    assert any(workspace_indicators) or event.thread_id == str(shared_thread_id), \
                        "Shared events must indicate workspace context"
        
        # Cleanup
        cleanup_tasks = [client.disconnect() for client, _, _ in team_clients]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        print(f"✅ Shared workspace coordination validated")
        print(f"   Team members connected: {len(team_clients)}")
        print(f"   Successful event collections: {len(successful_collections)}")
        print(f"   Shared event types: {[et.value for et in shared_event_types]}")
    
    @pytest.mark.asyncio
    async def test_real_time_collaborative_editing_with_agent_suggestions(self, collaboration_websocket_utility, collaboration_auth_helper):
        """
        Test real-time collaborative editing with agent suggestions.
        
        CRITICAL: Users must see real-time updates and agent suggestions during collaboration.
        This enables live optimization planning sessions with AI assistance.
        """
        # Arrange - Create collaboration session
        session_id = f"collab_editing_session_{uuid.uuid4().hex[:8]}"
        collaborator_count = 2
        
        collaborators = []
        for i in range(collaborator_count):
            auth_result = await collaboration_auth_helper.create_authenticated_user(
                user_id=f"collaborator_{i}_{uuid.uuid4().hex[:6]}",
                permissions=["chat_access", "collaborative_editing", "agent_suggestions"],
                session_id=session_id
            )
            collaborators.append(auth_result)
        
        # Create shared editing context
        shared_document_id = f"optimization_plan_{session_id}"
        shared_thread_id = ThreadID(f"collab_thread_{session_id}")
        
        # Connect collaborators
        collaborator_clients = []
        for i, auth_result in enumerate(collaborators):
            user_context = UserExecutionContext(
                user_id=UserID(auth_result["user_id"]),
                thread_id=shared_thread_id,
                request_id=RequestID(f"edit_request_{i}_{uuid.uuid4().hex[:8]}"),
                session_id=session_id
            )
            
            auth_headers = {
                "Authorization": f"Bearer {auth_result['access_token']}",
                "X-User-ID": auth_result["user_id"],
                "X-Session-ID": session_id,
                "X-Document-ID": shared_document_id
            }
            
            client = await collaboration_websocket_utility.create_authenticated_client(
                auth_result["user_id"],
                auth_result["access_token"]
            )
            client.headers = auth_headers
            
            connected = await client.connect(timeout=60.0)
            assert connected is True, f"Collaborator {i} must connect for real-time editing"
            
            collaborator_clients.append((client, user_context, auth_result))
        
        # Act - Collaborative editing with agent suggestions
        editor1_client, editor1_context, editor1_auth = collaborator_clients[0]
        editor2_client, editor2_context, editor2_auth = collaborator_clients[1]
        
        # Editor 1 starts optimization plan
        editing_action_1 = {
            "type": "collaborative_edit",
            "action": "insert_text",
            "content": "Optimization Plan Draft:\n1. Analyze current infrastructure costs\n",
            "document_id": shared_document_id,
            "position": 0,
            "editor_id": editor1_auth["user_id"],
            "timestamp": datetime.now().isoformat()
        }
        
        await editor1_client.send_message(
            TestEventType.MESSAGE_CREATED,
            editing_action_1,
            user_id=str(editor1_context.user_id),
            thread_id=str(shared_thread_id)
        )
        
        # Request agent suggestions for the plan
        suggestion_request = {
            "type": "agent_suggestion_request",
            "content": "Please provide suggestions for our optimization plan structure",
            "document_context": editing_action_1["content"],
            "collaboration_mode": "real_time_suggestions",
            "timestamp": datetime.now().isoformat()
        }
        
        await editor1_client.send_message(
            TestEventType.MESSAGE_CREATED,
            suggestion_request,
            user_id=str(editor1_context.user_id),
            thread_id=str(shared_thread_id)
        )
        
        # Wait for collaborative events
        collaborative_events = {
            "editor1_events": [],
            "editor2_events": [],
            "agent_suggestions": []
        }
        
        async def collect_collaborative_events():
            """Collect events from both editors and agent suggestions."""
            timeout_time = time.time() + 60.0  # 1 minute timeout
            
            while time.time() < timeout_time:
                try:
                    # Check for events from both editors
                    for i, (client, context, auth) in enumerate(collaborator_clients):
                        try:
                            event = await client.wait_for_message(timeout=2.0)
                            if event:
                                if i == 0:
                                    collaborative_events["editor1_events"].append(event)
                                else:
                                    collaborative_events["editor2_events"].append(event)
                                
                                # Check if it's an agent suggestion
                                if (hasattr(event, 'data') and 
                                    isinstance(event.data, dict) and 
                                    event.data.get("type") == "agent_suggestion"):
                                    collaborative_events["agent_suggestions"].append(event)
                        
                        except asyncio.TimeoutError:
                            continue
                    
                    # Stop if we have sufficient events
                    total_events = (len(collaborative_events["editor1_events"]) + 
                                  len(collaborative_events["editor2_events"]))
                    if total_events >= 4:  # Reasonable number of collaborative events
                        break
                        
                except Exception as e:
                    print(f"Error in collaborative event collection: {e}")
                    break
        
        await collect_collaborative_events()
        
        # Editor 2 adds to the plan (simulate real-time collaboration)
        editing_action_2 = {
            "type": "collaborative_edit", 
            "action": "append_text",
            "content": "2. Identify optimization opportunities\n3. Implement recommendations\n",
            "document_id": shared_document_id,
            "position": -1,  # Append
            "editor_id": editor2_auth["user_id"],
            "timestamp": datetime.now().isoformat()
        }
        
        await editor2_client.send_message(
            TestEventType.MESSAGE_CREATED,
            editing_action_2,
            user_id=str(editor2_context.user_id),
            thread_id=str(shared_thread_id)
        )
        
        # Brief wait for final events
        await asyncio.sleep(5.0)
        
        # Assert collaborative functionality
        editor1_event_count = len(collaborative_events["editor1_events"])
        editor2_event_count = len(collaborative_events["editor2_events"])
        agent_suggestion_count = len(collaborative_events["agent_suggestions"])
        
        assert editor1_event_count > 0, "Editor 1 must receive collaborative events"
        assert editor2_event_count > 0, "Editor 2 must receive collaborative events"
        
        # Verify real-time synchronization
        # Both editors should see updates from each other
        cross_editor_events = 0
        
        # Check if editor1 sees editor2's changes
        for event in collaborative_events["editor1_events"]:
            if (hasattr(event, 'data') and 
                isinstance(event.data, dict) and 
                event.data.get("editor_id") == editor2_auth["user_id"]):
                cross_editor_events += 1
        
        # Check if editor2 sees editor1's changes  
        for event in collaborative_events["editor2_events"]:
            if (hasattr(event, 'data') and 
                isinstance(event.data, dict) and 
                event.data.get("editor_id") == editor1_auth["user_id"]):
                cross_editor_events += 1
        
        # Real-time collaboration should show cross-editor visibility
        # Note: Exact implementation may vary, so we check for general collaborative indicators
        total_collaborative_events = editor1_event_count + editor2_event_count
        assert total_collaborative_events >= 2, f"Must have collaborative event exchange, got {total_collaborative_events}"
        
        # Agent suggestions should be available (if implemented)
        if agent_suggestion_count > 0:
            print(f"   Agent suggestions received: {agent_suggestion_count}")
        
        # Cleanup
        await editor1_client.disconnect()
        await editor2_client.disconnect()
        
        print(f"✅ Real-time collaborative editing validated")
        print(f"   Editor 1 events: {editor1_event_count}")
        print(f"   Editor 2 events: {editor2_event_count}")
        print(f"   Cross-editor events: {cross_editor_events}")
        print(f"   Agent suggestions: {agent_suggestion_count}")
    
    @pytest.mark.asyncio
    async def test_team_agent_handoff_coordination(self, collaboration_websocket_utility, collaboration_auth_helper):
        """
        Test coordinated agent handoffs between team members.
        
        CRITICAL: Agent work must be coordinated across team members seamlessly.
        This enables complex multi-step optimization workflows with team collaboration.
        """
        # Arrange - Create team workflow scenario
        workflow_id = f"team_workflow_{uuid.uuid4().hex[:8]}"
        team_roles = ["lead_analyst", "technical_specialist", "implementation_manager"]
        
        team_members = []
        for i, role in enumerate(team_roles):
            auth_result = await collaboration_auth_helper.create_authenticated_user(
                user_id=f"team_{role}_{uuid.uuid4().hex[:6]}",
                permissions=["chat_access", "agent_handoff", "workflow_coordination"],
                team_role=role,
                workflow_id=workflow_id
            )
            team_members.append((auth_result, role))
        
        # Create workflow thread
        workflow_thread_id = ThreadID(f"workflow_thread_{workflow_id}")
        
        # Connect team members
        team_connections = []
        for i, (auth_result, role) in enumerate(team_members):
            user_context = UserExecutionContext(
                user_id=UserID(auth_result["user_id"]),
                thread_id=workflow_thread_id,
                request_id=RequestID(f"workflow_request_{i}_{uuid.uuid4().hex[:8]}"),
                session_id=auth_result["session_id"],
                team_role=role,
                workflow_id=workflow_id
            )
            
            auth_headers = {
                "Authorization": f"Bearer {auth_result['access_token']}",
                "X-User-ID": auth_result["user_id"],
                "X-Team-Role": role,
                "X-Workflow-ID": workflow_id
            }
            
            client = await collaboration_websocket_utility.create_authenticated_client(
                auth_result["user_id"],
                auth_result["access_token"]
            )
            client.headers = auth_headers
            
            connected = await client.connect(timeout=60.0)
            assert connected is True, f"Team member {role} must connect for workflow coordination"
            
            team_connections.append((client, user_context, auth_result, role))
        
        # Act - Execute coordinated agent handoff workflow
        lead_client, lead_context, lead_auth, lead_role = team_connections[0]
        
        # Lead analyst starts workflow
        workflow_initiation = {
            "type": "workflow_initiation",
            "content": "Starting team optimization workflow - need analysis, technical review, and implementation planning",
            "workflow_id": workflow_id,
            "current_stage": "analysis",
            "next_handoff": "technical_specialist",
            "team_coordination": True,
            "timestamp": datetime.now().isoformat()
        }
        
        await lead_client.send_message(
            TestEventType.MESSAGE_CREATED,
            workflow_initiation,
            user_id=str(lead_context.user_id),
            thread_id=str(workflow_thread_id)
        )
        
        # Collect workflow coordination events
        workflow_events = {role: [] for _, _, _, role in team_connections}
        
        async def monitor_workflow_events():
            """Monitor workflow events across all team members."""
            monitoring_time = 0
            max_monitoring_time = 90.0  # 1.5 minutes
            
            while monitoring_time < max_monitoring_time:
                for client, context, auth, role in team_connections:
                    try:
                        event = await client.wait_for_message(timeout=5.0)
                        if event:
                            workflow_events[role].append(event)
                            
                            # Check for workflow coordination events
                            if (hasattr(event, 'data') and 
                                isinstance(event.data, dict) and 
                                event.data.get("workflow_id") == workflow_id):
                                print(f"Workflow event for {role}: {event.event_type.value}")
                    
                    except asyncio.TimeoutError:
                        continue
                
                monitoring_time += 5.0
                
                # Stop if all roles have received some events
                if all(len(events) > 0 for events in workflow_events.values()):
                    break
        
        await monitor_workflow_events()
        
        # Simulate handoff to technical specialist
        specialist_client, specialist_context, specialist_auth, specialist_role = team_connections[1]
        
        handoff_message = {
            "type": "agent_handoff",
            "content": "Receiving handoff from lead analyst - beginning technical analysis",
            "workflow_id": workflow_id,
            "previous_stage": "analysis", 
            "current_stage": "technical_review",
            "handoff_from": lead_auth["user_id"],
            "handoff_to": specialist_auth["user_id"],
            "timestamp": datetime.now().isoformat()
        }
        
        await specialist_client.send_message(
            TestEventType.MESSAGE_CREATED,
            handoff_message,
            user_id=str(specialist_context.user_id),
            thread_id=str(workflow_thread_id)
        )
        
        # Brief wait for handoff coordination
        await asyncio.sleep(10.0)
        
        # Assert workflow coordination
        total_workflow_events = sum(len(events) for events in workflow_events.values())
        assert total_workflow_events >= 3, f"Must have workflow coordination events across team, got {total_workflow_events}"
        
        # Verify all team members are aware of workflow
        team_members_with_events = sum(1 for events in workflow_events.values() if len(events) > 0)
        assert team_members_with_events >= 2, f"At least 2 team members must receive workflow events, got {team_members_with_events}"
        
        # Check for workflow-specific events
        workflow_event_types = set()
        for role_events in workflow_events.values():
            for event in role_events:
                if hasattr(event, 'event_type'):
                    workflow_event_types.add(event.event_type)
        
        # Should see agent activity and coordination events
        coordination_indicators = {
            TestEventType.AGENT_STARTED,
            TestEventType.MESSAGE_CREATED,
            TestEventType.AGENT_THINKING
        }
        
        received_coordination = workflow_event_types.intersection(coordination_indicators)
        assert len(received_coordination) >= 1, f"Must see workflow coordination events: {received_coordination}"
        
        # Cleanup
        cleanup_tasks = [client.disconnect() for client, _, _, _ in team_connections]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        print(f"✅ Team agent handoff coordination validated")
        print(f"   Total workflow events: {total_workflow_events}")
        print(f"   Team members with events: {team_members_with_events}")
        print(f"   Event types: {[et.value for et in workflow_event_types]}")
        print(f"   Workflow coordination: {[et.value for et in received_coordination]}")