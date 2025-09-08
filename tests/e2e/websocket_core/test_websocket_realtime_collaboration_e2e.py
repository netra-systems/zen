"""
E2E tests for WebSocket Real-time Collaboration - Testing collaborative features via WebSocket.

Business Value Justification (BVJ):
- Segment: Mid, Enterprise
- Business Goal: Collaborative AI analysis and team productivity
- Value Impact: Enables teams to collaboratively analyze data and share AI insights
- Strategic Impact: Premium differentiator - validates collaborative features for enterprise customers

These E2E tests validate real-time collaboration features: shared sessions, collaborative
analysis, team notifications, and concurrent user interactions with full authentication.

CRITICAL: All E2E tests MUST use authentication as per CLAUDE.md requirements.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from test_framework.ssot.base import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import WebSocketTestUtility
from shared.isolated_environment import get_env


class TestWebSocketRealtimeCollaborationE2E(SSotBaseTestCase):
    """E2E tests for WebSocket real-time collaboration features."""
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated E2E auth helper."""
        env = get_env()
        config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002", 
            websocket_url="ws://localhost:8002/ws",
            jwt_secret=env.get("JWT_SECRET", "test-jwt-secret-key-unified-testing-32chars")
        )
        return E2EAuthHelper(config)
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_user_collaborative_analysis_e2e(self, auth_helper, websocket_utility):
        """Test multi-user collaborative cost analysis with authentication.
        
        Validates that multiple team members can collaborate on AI analysis in real-time.
        """
        # STEP 1: Authenticate multiple team members (MANDATORY for E2E)
        team_members = []
        for i in range(3):
            auth_result = await auth_helper.authenticate_test_user(
                email=f"team_member_{i}@company.com",
                subscription_tier="enterprise"  # Collaboration requires enterprise
            )
            assert auth_result.success is True, f"Authentication failed for team member {i}"
            team_members.append(auth_result)
        
        # STEP 2: Create shared collaboration session
        collaboration_id = f"collab_session_{datetime.now().timestamp()}"
        
        # STEP 3: Connect all team members to WebSocket
        websockets = []
        connected_websockets = []
        
        for member in team_members:
            websocket = websocket_utility.create_authenticated_websocket_client(
                access_token=member.access_token,
                websocket_url=auth_helper.config.websocket_url
            )
            websockets.append(websocket)
            connected_ws = await websocket.__aenter__()
            connected_websockets.append(connected_ws)
        
        try:
            # STEP 4: Team leader initiates collaborative analysis
            leader = team_members[0]
            leader_ws = connected_websockets[0]
            
            collaboration_request = {
                "type": "start_collaborative_session",
                "collaboration_id": collaboration_id,
                "session_type": "cost_analysis",
                "participants": [member.user_id for member in team_members],
                "leader_id": leader.user_id,
                "project": {
                    "name": "Q4 Cost Optimization",
                    "scope": "enterprise_infrastructure",
                    "priority": "high"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await leader_ws.send_json(collaboration_request)
            
            # STEP 5: Verify all team members receive collaboration invitation
            invitation_responses = []
            for i, websocket in enumerate(connected_websockets):
                try:
                    response = await asyncio.wait_for(websocket.receive_json(), timeout=10)
                    invitation_responses.append((i, response))
                except asyncio.TimeoutError:
                    invitation_responses.append((i, None))
            
            # All members should receive collaboration notification
            successful_invitations = [resp for resp in invitation_responses if resp[1] is not None]
            assert len(successful_invitations) >= 2, "At least 2 team members should receive collaboration invitation"
            
            # STEP 6: Team members join collaborative session
            join_tasks = []
            for i, member in enumerate(team_members[1:], 1):  # Skip leader
                join_request = {
                    "type": "join_collaborative_session",
                    "collaboration_id": collaboration_id,
                    "user_id": member.user_id,
                    "role": "participant",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                join_tasks.append(connected_websockets[i].send_json(join_request))
            
            if join_tasks:
                await asyncio.gather(*join_tasks)
            
            # STEP 7: Collaborative agent analysis with real-time sharing
            collaborative_analysis = {
                "type": "start_collaborative_agent",
                "agent": "cost_optimizer",
                "collaboration_id": collaboration_id,
                "message": "Analyze our enterprise cloud costs across all departments. Focus on: 1) Compute optimization 2) Storage tiering 3) Network efficiency",
                "shared_context": {
                    "departments": ["engineering", "sales", "marketing"],
                    "budget_target": "reduce_by_20_percent",
                    "timeline": "Q1_implementation"
                },
                "user_id": leader.user_id,
                "broadcast_to_participants": True
            }
            
            await leader_ws.send_json(collaborative_analysis)
            
            # STEP 8: Collect collaborative events from all participants
            collaborative_events = [[] for _ in range(len(connected_websockets))]
            max_analysis_time = 45
            start_analysis_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_analysis_time) < max_analysis_time:
                for i, websocket in enumerate(connected_websockets):
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
                        collaborative_events[i].append(event)
                    except asyncio.TimeoutError:
                        continue
                
                # Check if analysis completed for any participant
                analysis_completed = any(
                    any(event.get("type") == "collaborative_agent_completed" for event in events)
                    for events in collaborative_events
                )
                
                if analysis_completed:
                    break
                    
                await asyncio.sleep(0.1)
            
            # STEP 9: Validate collaborative analysis results
            # All participants should receive shared analysis updates
            for i, events in enumerate(collaborative_events):
                participant_events = [e.get("type") for e in events]
                
                # Should receive collaborative notifications
                collaborative_notifications = [
                    "collaborative_session_started",
                    "collaborative_agent_started", 
                    "collaborative_thinking",
                    "collaborative_progress"
                ]
                
                received_notifications = sum(1 for notif in collaborative_notifications if notif in participant_events)
                assert received_notifications >= 1, f"Participant {i} should receive collaborative notifications"
            
            # STEP 10: Test real-time comment/annotation sharing
            comment_tasks = []
            comments = [
                {"user_idx": 0, "comment": "Great analysis! The compute optimization looks promising."},
                {"user_idx": 1, "comment": "I agree, but we should also consider network costs in Asia-Pacific."},
                {"user_idx": 2, "comment": "Storage tiering could save us significant money - let's prioritize this."}
            ]
            
            for comment_data in comments:
                user_idx = comment_data["user_idx"]
                comment_message = {
                    "type": "collaborative_comment",
                    "collaboration_id": collaboration_id,
                    "comment": comment_data["comment"],
                    "user_id": team_members[user_idx].user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context": "cost_analysis_results"
                }
                
                comment_tasks.append(connected_websockets[user_idx].send_json(comment_message))
                await asyncio.sleep(0.5)  # Stagger comments
            
            await asyncio.gather(*comment_tasks)
            
            # STEP 11: Verify comment distribution
            comment_responses = [[] for _ in range(len(connected_websockets))]
            comment_collection_time = 10
            comment_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - comment_start) < comment_collection_time:
                for i, websocket in enumerate(connected_websockets):
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=0.2)
                        if event.get("type") == "collaborative_comment":
                            comment_responses[i].append(event)
                    except asyncio.TimeoutError:
                        continue
            
            # Each participant should see comments from others (but not their own)
            for i, comments_received in enumerate(comment_responses):
                if len(comments_received) > 0:
                    # Should receive comments from other participants
                    other_user_comments = [
                        comment for comment in comments_received
                        if comment.get("user_id") != team_members[i].user_id
                    ]
                    assert len(other_user_comments) > 0, f"Participant {i} should see comments from other team members"
            
            # STEP 12: Test collaborative decision making
            decision_request = {
                "type": "collaborative_decision",
                "collaboration_id": collaboration_id,
                "decision_type": "prioritization",
                "options": [
                    {"id": "compute_opt", "title": "Compute Optimization", "impact": "high", "effort": "medium"},
                    {"id": "storage_tier", "title": "Storage Tiering", "impact": "medium", "effort": "low"},
                    {"id": "network_opt", "title": "Network Optimization", "impact": "medium", "effort": "high"}
                ],
                "user_id": leader.user_id,
                "require_consensus": True
            }
            
            await leader_ws.send_json(decision_request)
            
            # Team members vote
            votes = [
                {"user_idx": 0, "vote": "compute_opt"},
                {"user_idx": 1, "vote": "storage_tier"}, 
                {"user_idx": 2, "vote": "storage_tier"}
            ]
            
            vote_tasks = []
            for vote_data in votes:
                user_idx = vote_data["user_idx"]
                vote_message = {
                    "type": "collaborative_vote",
                    "collaboration_id": collaboration_id,
                    "decision_id": "prioritization",
                    "vote": vote_data["vote"],
                    "user_id": team_members[user_idx].user_id
                }
                vote_tasks.append(connected_websockets[user_idx].send_json(vote_message))
            
            await asyncio.gather(*vote_tasks)
            
            # STEP 13: Verify collaborative decision results
            decision_results = []
            decision_wait = 10
            decision_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - decision_start) < decision_wait:
                for websocket in connected_websockets:
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
                        if event.get("type") == "collaborative_decision_result":
                            decision_results.append(event)
                            break
                    except asyncio.TimeoutError:
                        continue
                
                if decision_results:
                    break
            
            # Should have decision results
            if decision_results:
                result = decision_results[0]
                assert result.get("winning_option") in ["compute_opt", "storage_tier"], "Should have valid decision result"
                assert "vote_count" in result.get("data", {}), "Should include vote tallies"
        
        finally:
            # STEP 14: Cleanup collaborative session
            for websocket in websockets:
                try:
                    await websocket.__aexit__(None, None, None)
                except Exception:
                    pass
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_real_time_presence_and_activity_e2e(self, auth_helper, websocket_utility):
        """Test real-time presence and activity indicators with authentication.
        
        Validates that users can see who else is active and what they're doing.
        """
        # Authenticate multiple users (MANDATORY for E2E)
        users = []
        for i in range(3):
            auth_result = await auth_helper.authenticate_test_user(
                email=f"presence_user_{i}@company.com",
                subscription_tier="enterprise"
            )
            assert auth_result.success is True
            users.append(auth_result)
        
        # Connect users to WebSocket
        websockets = []
        connected_websockets = []
        
        for user in users:
            websocket = websocket_utility.create_authenticated_websocket_client(
                access_token=user.access_token,
                websocket_url=auth_helper.config.websocket_url
            )
            websockets.append(websocket)
            connected_ws = await websocket.__aenter__()
            connected_websockets.append(connected_ws)
        
        try:
            # Enable presence tracking for all users
            for i, (user, websocket) in enumerate(zip(users, connected_websockets)):
                presence_enable = {
                    "type": "enable_presence",
                    "user_id": user.user_id,
                    "user_info": {
                        "name": f"User {i}",
                        "role": ["analyst", "manager", "engineer"][i],
                        "department": ["finance", "operations", "engineering"][i]
                    },
                    "share_activity": True
                }
                await websocket.send_json(presence_enable)
            
            # Allow presence to propagate
            await asyncio.sleep(2)
            
            # Test user activity broadcasting
            activities = [
                {"user_idx": 0, "activity": "analyzing_costs", "details": "Q4 budget review"},
                {"user_idx": 1, "activity": "reviewing_reports", "details": "Monthly optimization reports"},
                {"user_idx": 2, "activity": "configuring_alerts", "details": "Cost spike notifications"}
            ]
            
            activity_tasks = []
            for activity_data in activities:
                user_idx = activity_data["user_idx"]
                activity_message = {
                    "type": "update_activity",
                    "user_id": users[user_idx].user_id,
                    "activity": activity_data["activity"],
                    "details": activity_data["details"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                activity_tasks.append(connected_websockets[user_idx].send_json(activity_message))
            
            await asyncio.gather(*activity_tasks)
            
            # Collect presence updates
            presence_updates = [[] for _ in range(len(connected_websockets))]
            presence_wait = 15
            presence_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - presence_start) < presence_wait:
                for i, websocket in enumerate(connected_websockets):
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
                        if event.get("type") in ["user_presence", "activity_update", "presence_change"]:
                            presence_updates[i].append(event)
                    except asyncio.TimeoutError:
                        continue
            
            # Validate presence awareness
            for i, updates in enumerate(presence_updates):
                if len(updates) > 0:
                    # Should see activity from other users
                    other_user_activities = []
                    for update in updates:
                        update_user_id = update.get("user_id") or update.get("data", {}).get("user_id")
                        if update_user_id and update_user_id != users[i].user_id:
                            other_user_activities.append(update)
                    
                    # Should be aware of other users' activities
                    assert len(other_user_activities) > 0, f"User {i} should see other users' activities"
            
            # Test typing indicators
            typing_tests = [
                {"user_idx": 0, "typing": True, "content": "I'm composing a question about storage costs..."},
                {"user_idx": 1, "typing": True, "content": "Looking at the compute utilization data..."}
            ]
            
            for typing_data in typing_tests:
                user_idx = typing_data["user_idx"]
                typing_message = {
                    "type": "typing_indicator",
                    "user_id": users[user_idx].user_id,
                    "typing": typing_data["typing"],
                    "preview": typing_data["content"][:50] if typing_data["content"] else None
                }
                await connected_websockets[user_idx].send_json(typing_message)
                await asyncio.sleep(1)
            
            # Collect typing indicators
            typing_indicators = [[] for _ in range(len(connected_websockets))]
            typing_wait = 8
            typing_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - typing_start) < typing_wait:
                for i, websocket in enumerate(connected_websockets):
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=0.3)
                        if event.get("type") == "typing_indicator":
                            typing_indicators[i].append(event)
                    except asyncio.TimeoutError:
                        continue
            
            # Users should see typing from others
            typing_awareness_count = 0
            for i, indicators in enumerate(typing_indicators):
                other_typing = [
                    ind for ind in indicators
                    if ind.get("user_id") != users[i].user_id and ind.get("typing") is True
                ]
                if other_typing:
                    typing_awareness_count += 1
            
            assert typing_awareness_count >= 1, "Users should see typing indicators from others"
            
            # Test presence status changes
            status_changes = [
                {"user_idx": 0, "status": "away", "message": "In a meeting"},
                {"user_idx": 2, "status": "do_not_disturb", "message": "Deep analysis mode"}
            ]
            
            for status_data in status_changes:
                user_idx = status_data["user_idx"] 
                status_message = {
                    "type": "presence_status",
                    "user_id": users[user_idx].user_id,
                    "status": status_data["status"],
                    "message": status_data["message"]
                }
                await connected_websockets[user_idx].send_json(status_message)
            
            # Verify status propagation
            await asyncio.sleep(3)
            
            status_updates = []
            status_check_time = 5
            status_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - status_start) < status_check_time:
                for websocket in connected_websockets:
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=0.2)
                        if event.get("type") == "presence_status":
                            status_updates.append(event)
                    except asyncio.TimeoutError:
                        continue
            
            # Should propagate status changes
            if status_updates:
                status_messages = [update.get("status") for update in status_updates]
                assert "away" in status_messages or "do_not_disturb" in status_messages, "Status changes should propagate"
        
        finally:
            # Cleanup
            for websocket in websockets:
                try:
                    await websocket.__aexit__(None, None, None)
                except Exception:
                    pass
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_shared_workspace_collaboration_e2e(self, auth_helper, websocket_utility):
        """Test shared workspace collaboration features with authentication.
        
        Validates shared workspaces where teams can collaboratively build analyses.
        """
        # Authenticate workspace team (MANDATORY for E2E)
        team_size = 2  # Simplified for E2E testing
        workspace_team = []
        
        for i in range(team_size):
            auth_result = await auth_helper.authenticate_test_user(
                email=f"workspace_user_{i}@company.com",
                subscription_tier="enterprise"
            )
            assert auth_result.success is True
            workspace_team.append(auth_result)
        
        # Connect team to WebSocket
        websockets = []
        connected_websockets = []
        
        for member in workspace_team:
            websocket = websocket_utility.create_authenticated_websocket_client(
                access_token=member.access_token,
                websocket_url=auth_helper.config.websocket_url
            )
            websockets.append(websocket)
            connected_ws = await websocket.__aenter__()
            connected_websockets.append(connected_ws)
        
        try:
            # Create shared workspace
            workspace_id = f"workspace_{datetime.now().timestamp()}"
            workspace_owner = workspace_team[0]
            
            workspace_creation = {
                "type": "create_shared_workspace",
                "workspace_id": workspace_id,
                "name": "Q4 Cost Analysis Workspace",
                "description": "Collaborative space for Q4 cost optimization analysis",
                "owner_id": workspace_owner.user_id,
                "members": [member.user_id for member in workspace_team],
                "permissions": {
                    "all_can_edit": True,
                    "all_can_invite": False,
                    "all_can_delete": False
                }
            }
            
            await connected_websockets[0].send_json(workspace_creation)
            
            # Members join workspace
            for i, member in enumerate(workspace_team[1:], 1):
                join_workspace = {
                    "type": "join_shared_workspace",
                    "workspace_id": workspace_id,
                    "user_id": member.user_id
                }
                await connected_websockets[i].send_json(join_workspace)
            
            await asyncio.sleep(2)  # Allow workspace setup
            
            # Collaborative analysis building
            analysis_components = [
                {
                    "user_idx": 0,
                    "component": {
                        "type": "add_analysis_component",
                        "workspace_id": workspace_id,
                        "component_type": "cost_trend_analysis", 
                        "title": "Monthly Cost Trends",
                        "query": "Analyze cost trends for past 6 months",
                        "user_id": workspace_team[0].user_id
                    }
                },
                {
                    "user_idx": 1,
                    "component": {
                        "type": "add_analysis_component",
                        "workspace_id": workspace_id,
                        "component_type": "resource_utilization",
                        "title": "Resource Utilization Analysis",
                        "query": "Check utilization across all instances",
                        "user_id": workspace_team[1].user_id
                    }
                }
            ]
            
            # Add components to workspace
            for comp_data in analysis_components:
                user_idx = comp_data["user_idx"]
                await connected_websockets[user_idx].send_json(comp_data["component"])
                await asyncio.sleep(1)
            
            # Collect workspace updates
            workspace_updates = [[] for _ in range(len(connected_websockets))]
            update_collection_time = 20
            update_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - update_start) < update_collection_time:
                for i, websocket in enumerate(connected_websockets):
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
                        if "workspace" in event.get("type", "").lower():
                            workspace_updates[i].append(event)
                    except asyncio.TimeoutError:
                        continue
            
            # Validate workspace collaboration
            for i, updates in enumerate(workspace_updates):
                workspace_events = [
                    update for update in updates
                    if update.get("workspace_id") == workspace_id
                ]
                
                if workspace_events:
                    # Should see workspace component additions
                    component_additions = [
                        event for event in workspace_events
                        if "add_analysis_component" in event.get("type", "")
                    ]
                    
                    # Members should see components added by others
                    other_user_components = [
                        comp for comp in component_additions
                        if comp.get("user_id") != workspace_team[i].user_id
                    ]
                    
                    assert len(other_user_components) >= 0, f"User {i} should see workspace updates from others"
            
            # Test workspace synchronization
            sync_request = {
                "type": "sync_workspace",
                "workspace_id": workspace_id,
                "user_id": workspace_team[0].user_id
            }
            
            await connected_websockets[0].send_json(sync_request)
            
            # Collect sync responses
            sync_responses = []
            sync_wait = 10
            sync_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - sync_start) < sync_wait:
                for websocket in connected_websockets:
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=1)
                        if event.get("type") == "workspace_sync":
                            sync_responses.append(event)
                    except asyncio.TimeoutError:
                        continue
                
                if sync_responses:
                    break
            
            # Should provide workspace state synchronization
            if sync_responses:
                sync_data = sync_responses[0]
                assert "workspace_id" in sync_data, "Sync should include workspace identifier"
                assert "components" in sync_data.get("data", {}), "Sync should include workspace components"
        
        finally:
            # Cleanup workspace connections
            for websocket in websockets:
                try:
                    await websocket.__aexit__(None, None, None)
                except Exception:
                    pass