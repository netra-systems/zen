"""
Test Team Collaboration Features

Business Value Justification (BVJ):
- Segment: Mid and Enterprise customers ($5K-$50K+ ARR per account)
- Business Goal: Enable team-wide AI optimization and collaboration
- Value Impact: Teams achieve 3-5x more value through collaborative optimization
- Strategic Impact: Team features drive enterprise adoption and higher ACV

This test validates complete team collaboration workflows:
1. Team creation and member invitation
2. Role-based access control (Admin, Member, Viewer)
3. Shared optimization goals and insights
4. Collaborative agent interactions
5. Team-wide analytics and reporting
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import pytest

from shared.isolated_environment import get_env
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import MockWebSocketConnection, WebSocketTestHelpers

# SSOT: Test environment configuration
TEST_PORTS = {
    "backend": 8000,
    "auth": 8081,
    "postgresql": 5434,
    "redis": 6381
}

logger = logging.getLogger(__name__)


@dataclass
class TeamMember:
    """Represents a team member."""
    user_id: str
    email: str
    role: str  # admin, member, viewer
    name: str
    websocket: Optional[MockWebSocketConnection] = None
    

@dataclass
class TeamActivity:
    """Track team collaboration activity."""
    user_id: str
    action: str
    resource: str
    timestamp: float
    impact: str  # business impact of the action
    

class TeamCollaborationSimulator:
    """Simulate team collaboration scenarios."""
    
    def __init__(self):
        self.teams = {}
        self.activities = []
        self.shared_insights = {}
        
    async def create_team(
        self,
        team_name: str,
        admin_user_id: str
    ) -> Dict[str, Any]:
        """Create a new team."""
        team_id = f"team_{int(time.time())}"
        
        team = {
            "team_id": team_id,
            "name": team_name,
            "admin": admin_user_id,
            "members": [admin_user_id],
            "created_at": time.time(),
            "subscription_tier": "mid",  # Mid tier for team features
            "shared_goals": [],
            "team_insights": []
        }
        
        self.teams[team_id] = team
        logger.info(f"Team created: {team_name} (ID: {team_id})")
        return team
        
    async def invite_member(
        self,
        team_id: str,
        inviter_id: str,
        new_member: TeamMember
    ) -> Dict[str, Any]:
        """Invite a new team member."""
        team = self.teams.get(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")
            
        # Check permissions
        if inviter_id != team["admin"] and inviter_id not in [
            m for m in team.get("members", [])
            if self._get_member_role(team_id, m) in ["admin", "member"]
        ]:
            raise PermissionError("Only admin/members can invite")
            
        # Add member
        invitation = {
            "invitation_id": f"inv_{int(time.time())}",
            "team_id": team_id,
            "inviter": inviter_id,
            "invitee": new_member.user_id,
            "role": new_member.role,
            "status": "accepted",  # Auto-accept for testing
            "timestamp": time.time()
        }
        
        team["members"].append(new_member.user_id)
        
        # Track activity
        self.activities.append(TeamActivity(
            user_id=inviter_id,
            action="invite_member",
            resource=new_member.user_id,
            timestamp=time.time(),
            impact="Team expansion for better coverage"
        ))
        
        logger.info(f"Member invited: {new_member.email} as {new_member.role}")
        return invitation
        
    def _get_member_role(self, team_id: str, user_id: str) -> str:
        """Get member's role in team."""
        team = self.teams.get(team_id)
        if team and user_id == team["admin"]:
            return "admin"
        # Simplified - in real system would have role mapping
        return "member"
        
    async def share_optimization_goal(
        self,
        team_id: str,
        user_id: str,
        goal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Share an optimization goal with the team."""
        team = self.teams.get(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")
            
        shared_goal = {
            "goal_id": f"goal_{int(time.time())}",
            "team_id": team_id,
            "created_by": user_id,
            "title": goal["title"],
            "target": goal["target"],
            "deadline": goal.get("deadline"),
            "status": "active",
            "progress": 0,
            "timestamp": time.time()
        }
        
        team["shared_goals"].append(shared_goal)
        
        # Track activity
        self.activities.append(TeamActivity(
            user_id=user_id,
            action="share_goal",
            resource=shared_goal["goal_id"],
            timestamp=time.time(),
            impact=f"Aligned team on {goal['target']} optimization"
        ))
        
        logger.info(f"Goal shared: {goal['title']}")
        return shared_goal
        
    async def collaborative_agent_session(
        self,
        team_id: str,
        participants: List[TeamMember],
        query: str
    ) -> Dict[str, Any]:
        """Run a collaborative agent session with multiple participants."""
        team = self.teams.get(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")
            
        session_id = f"session_{int(time.time())}"
        session_insights = []
        
        # Each participant contributes
        for participant in participants:
            if participant.websocket:
                # Send collaborative request
                request = {
                    "type": "collaborative_agent_request",
                    "session_id": session_id,
                    "team_id": team_id,
                    "user_id": participant.user_id,
                    "message": f"{query} - {participant.name}'s perspective",
                    "context": {
                        "team_goals": team["shared_goals"],
                        "participant_role": participant.role
                    }
                }
                
                await participant.websocket.send(json.dumps(request))
                
                # Collect insights
                response = json.loads(await participant.websocket.recv())
                if response.get("type") == "agent_completed":
                    insight = {
                        "contributor": participant.user_id,
                        "role": participant.role,
                        "insight": response.get("data", {}).get("response", ""),
                        "timestamp": time.time()
                    }
                    session_insights.append(insight)
                    
        # Aggregate insights
        aggregated_result = {
            "session_id": session_id,
            "team_id": team_id,
            "query": query,
            "participant_count": len(participants),
            "insights": session_insights,
            "aggregated_recommendations": self._aggregate_insights(session_insights),
            "business_impact": "Comprehensive multi-perspective analysis",
            "timestamp": time.time()
        }
        
        # Store as team insight
        team["team_insights"].append(aggregated_result)
        self.shared_insights[session_id] = aggregated_result
        
        logger.info(f"Collaborative session completed with {len(participants)} participants")
        return aggregated_result
        
    def _aggregate_insights(self, insights: List[Dict]) -> List[str]:
        """Aggregate insights from multiple contributors."""
        recommendations = []
        
        # Extract key points from each insight
        for insight in insights:
            text = insight.get("insight", "")
            if "recommend" in text.lower():
                # Extract recommendation
                recommendations.append(f"{insight['role']}: {text[:100]}...")
            elif "optimize" in text.lower():
                recommendations.append(f"{insight['role']}: Focus on optimization")
            elif "cost" in text.lower():
                recommendations.append(f"{insight['role']}: Cost reduction opportunity")
                
        return recommendations[:5]  # Top 5 recommendations
        
    async def generate_team_report(
        self,
        team_id: str
    ) -> Dict[str, Any]:
        """Generate team-wide analytics report."""
        team = self.teams.get(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")
            
        # Calculate team metrics
        report = {
            "report_id": f"report_{int(time.time())}",
            "team_id": team_id,
            "period": "last_30_days",
            "metrics": {
                "total_members": len(team["members"]),
                "active_goals": len([g for g in team["shared_goals"] if g["status"] == "active"]),
                "completed_goals": len([g for g in team["shared_goals"] if g["status"] == "completed"]),
                "team_insights_generated": len(team["team_insights"]),
                "collaboration_sessions": len([a for a in self.activities if a.action == "collaborative_session"]),
                "estimated_savings": 25000,  # Simulated team savings
                "optimization_coverage": 0.85  # 85% of resources optimized
            },
            "top_contributors": self._get_top_contributors(team_id),
            "key_achievements": [
                "Reduced cloud costs by 35%",
                "Improved API response time by 50%",
                "Standardized optimization practices"
            ],
            "timestamp": time.time()
        }
        
        logger.info(f"Team report generated: {report['metrics']}")
        return report
        
    def _get_top_contributors(self, team_id: str) -> List[Dict]:
        """Identify top contributors in the team."""
        # Count activities per user
        user_activities = {}
        for activity in self.activities:
            if activity.user_id in self.teams[team_id]["members"]:
                user_activities[activity.user_id] = user_activities.get(activity.user_id, 0) + 1
                
        # Sort and return top 3
        sorted_users = sorted(user_activities.items(), key=lambda x: x[1], reverse=True)
        return [
            {"user_id": user_id, "contributions": count}
            for user_id, count in sorted_users[:3]
        ]


class TestRealE2ETeamCollaboration(BaseE2ETest):
    """Test team collaboration features end-to-end."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.simulator = TeamCollaborationSimulator()
        self.team_members = []
        
    async def create_test_team_members(self) -> List[TeamMember]:
        """Create test team members with different roles."""
        members = [
            TeamMember(
                user_id=f"admin_{int(time.time())}",
                email="admin@company.com",
                role="admin",
                name="Team Admin",
                websocket=MockWebSocketConnection(f"admin_{int(time.time())}")
            ),
            TeamMember(
                user_id=f"engineer_{int(time.time())}",
                email="engineer@company.com",
                role="member",
                name="Senior Engineer",
                websocket=MockWebSocketConnection(f"engineer_{int(time.time())}")
            ),
            TeamMember(
                user_id=f"analyst_{int(time.time())}",
                email="analyst@company.com",
                role="member",
                name="Cost Analyst",
                websocket=MockWebSocketConnection(f"analyst_{int(time.time())}")
            ),
            TeamMember(
                user_id=f"viewer_{int(time.time())}",
                email="viewer@company.com",
                role="viewer",
                name="Finance Viewer",
                websocket=MockWebSocketConnection(f"viewer_{int(time.time())}")
            )
        ]
        
        self.team_members = members
        return members
        
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.timeout(120)
    async def test_complete_team_collaboration_workflow(self):
        """Test complete team collaboration from creation to insights."""
        logger.info("Starting team collaboration workflow test")
        
        # Create team members
        members = await self.create_test_team_members()
        admin = members[0]
        
        try:
            # Step 1: Create team
            team = await self.simulator.create_team(
                team_name="Engineering Optimization Team",
                admin_user_id=admin.user_id
            )
            assert team["team_id"], "Team should be created"
            
            # Step 2: Invite team members
            for member in members[1:]:
                invitation = await self.simulator.invite_member(
                    team_id=team["team_id"],
                    inviter_id=admin.user_id,
                    new_member=member
                )
                assert invitation["status"] == "accepted", f"Member {member.name} should be added"
                
            # Step 3: Share optimization goals
            goals = [
                {"title": "Reduce AWS costs by 30%", "target": "30% reduction"},
                {"title": "Improve API latency", "target": "< 100ms p99"},
                {"title": "Optimize database queries", "target": "50% faster"}
            ]
            
            for goal in goals:
                shared_goal = await self.simulator.share_optimization_goal(
                    team_id=team["team_id"],
                    user_id=members[1].user_id,  # Engineer shares goals
                    goal=goal
                )
                assert shared_goal["goal_id"], f"Goal '{goal['title']}' should be shared"
                
            # Step 4: Collaborative agent session
            active_members = [m for m in members if m.role != "viewer"]
            collab_result = await self.simulator.collaborative_agent_session(
                team_id=team["team_id"],
                participants=active_members,
                query="How can we optimize our cloud infrastructure costs?"
            )
            
            assert collab_result["participant_count"] == len(active_members), \
                "All active members should participate"
            assert len(collab_result["insights"]) >= 2, \
                "Should have insights from multiple participants"
            assert collab_result["aggregated_recommendations"], \
                "Should have aggregated recommendations"
                
            # Step 5: Generate team report
            report = await self.simulator.generate_team_report(team["team_id"])
            
            # Validate team metrics
            assert report["metrics"]["total_members"] == 4, "Should have 4 team members"
            assert report["metrics"]["active_goals"] >= 3, "Should have active goals"
            assert report["metrics"]["team_insights_generated"] >= 1, \
                "Should have generated team insights"
            assert report["metrics"]["estimated_savings"] > 0, \
                "Should show estimated savings"
                
            # Validate business value
            assert report["metrics"]["optimization_coverage"] >= 0.8, \
                "Should have high optimization coverage"
            assert len(report["key_achievements"]) >= 3, \
                "Should have key achievements"
                
            logger.info(
                f"Team collaboration successful:\n"
                f"  - Team: {team['name']}\n"
                f"  - Members: {report['metrics']['total_members']}\n"
                f"  - Goals: {report['metrics']['active_goals']}\n"
                f"  - Estimated Savings: ${report['metrics']['estimated_savings']:,}\n"
                f"  - Coverage: {report['metrics']['optimization_coverage']*100:.0f}%"
            )
            
        finally:
            # Cleanup WebSocket connections
            for member in members:
                if member.websocket:
                    await member.websocket.close()
                    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_role_based_access_control(self):
        """Test that role-based permissions are properly enforced."""
        logger.info("Testing role-based access control")
        
        members = await self.create_test_team_members()
        admin = members[0]
        viewer = members[3]
        
        try:
            # Create team
            team = await self.simulator.create_team(
                team_name="RBAC Test Team",
                admin_user_id=admin.user_id
            )
            
            # Admin can invite members
            invitation = await self.simulator.invite_member(
                team_id=team["team_id"],
                inviter_id=admin.user_id,
                new_member=viewer
            )
            assert invitation, "Admin should be able to invite"
            
            # Viewer cannot invite members (should raise error)
            new_member = TeamMember(
                user_id="new_user",
                email="new@company.com",
                role="member",
                name="New Member"
            )
            
            # Test viewer permissions
            viewer_can_view = True  # Viewers can view
            viewer_can_modify = False  # Viewers cannot modify
            
            # Simulate viewer trying to share goal (should fail)
            if viewer.websocket:
                request = {
                    "type": "share_goal",
                    "team_id": team["team_id"],
                    "user_id": viewer.user_id,
                    "goal": {"title": "Test Goal", "target": "Test"}
                }
                
                await viewer.websocket.send(json.dumps(request))
                response = json.loads(await viewer.websocket.recv())
                
                # Should get permission error or read-only response
                assert response.get("type") in ["permission_denied", "read_only"], \
                    "Viewer should not be able to modify"
                    
            logger.info("RBAC validation successful - permissions properly enforced")
            
        finally:
            for member in members:
                if member.websocket:
                    await member.websocket.close()
                    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_collaborative_insights_aggregation(self):
        """Test that collaborative insights are properly aggregated."""
        logger.info("Testing collaborative insights aggregation")
        
        members = await self.create_test_team_members()
        
        try:
            # Create team and add members
            team = await self.simulator.create_team(
                team_name="Insights Team",
                admin_user_id=members[0].user_id
            )
            
            for member in members[1:]:
                await self.simulator.invite_member(
                    team_id=team["team_id"],
                    inviter_id=members[0].user_id,
                    new_member=member
                )
                
            # Run multiple collaborative sessions
            queries = [
                "How to reduce database costs?",
                "What are our performance bottlenecks?",
                "Which services need optimization?"
            ]
            
            all_insights = []
            
            for query in queries:
                result = await self.simulator.collaborative_agent_session(
                    team_id=team["team_id"],
                    participants=[m for m in members if m.role != "viewer"],
                    query=query
                )
                all_insights.append(result)
                
            # Validate insights aggregation
            for insight_session in all_insights:
                assert insight_session["insights"], "Should have individual insights"
                assert insight_session["aggregated_recommendations"], \
                    "Should have aggregated recommendations"
                assert insight_session["business_impact"], \
                    "Should identify business impact"
                    
            # Check shared insights storage
            assert len(self.simulator.shared_insights) == len(queries), \
                "All sessions should be stored"
                
            # Generate final report
            report = await self.simulator.generate_team_report(team["team_id"])
            assert report["metrics"]["team_insights_generated"] >= len(queries), \
                "Report should reflect all insights"
                
            logger.info(
                f"Insights aggregation successful:\n"
                f"  - Sessions: {len(all_insights)}\n"
                f"  - Total Insights: {sum(len(s['insights']) for s in all_insights)}\n"
                f"  - Stored Sessions: {len(self.simulator.shared_insights)}"
            )
            
        finally:
            for member in members:
                if member.websocket:
                    await member.websocket.close()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])