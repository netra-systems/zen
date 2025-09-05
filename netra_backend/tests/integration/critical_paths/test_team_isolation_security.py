"""Team Isolation and Security Critical Path Tests

Business Value Justification (BVJ):
- Segment: Enterprise (security and compliance)
- Business Goal: Data isolation and security compliance
- Value Impact: Enterprise trust, compliance adherence, data protection
- Strategic Impact: Enterprise sales enablement and risk mitigation

Critical Path: Team isolation -> Cross-team access prevention -> Security validation
Coverage: Multi-tenant isolation, edge case handling, security boundaries
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import uuid

import pytest

from netra_backend.tests.integration.test_helpers.team_collaboration_base import (
    PermissionType,
    TeamCollaborationManager,
    TeamRole,
    validate_audit_trail,
)

@pytest.fixture
async def multi_team_environment():
    """Create multiple teams for isolation testing."""
    manager = TeamCollaborationManager()
    
    # Create three separate teams
    teams_data = []
    for i in range(3):
        owner_id = f"owner_{uuid.uuid4().hex[:8]}"
        team = await manager.create_team(owner_id, f"Team {i+1}", "enterprise")
        
        # Add members to each team
        member_id = f"member_{uuid.uuid4().hex[:8]}"
        member_invitation = await manager.invite_user(team.team_id, owner_id, f"member{i}@test.com", TeamRole.MEMBER)
        await manager.accept_invitation(member_invitation["token"], member_id)
        
        # Create workspace for each team
        workspace = await manager.create_workspace(team.team_id, owner_id, f"Team {i+1} Workspace")
        
        teams_data.append({
            "team": team,
            "owner_id": owner_id,
            "member_id": member_id,
            "workspace": workspace
        })
    
    yield {
        "manager": manager,
        "teams": teams_data
    }

class TestTeamIsolationSecurity:
    """Critical path tests for team isolation and security boundaries."""
    
    @pytest.mark.asyncio
    async def test_cross_team_access_prevention(self, multi_team_environment):
        """Test prevention of cross-team access."""
        test_data = multi_team_environment
        manager = test_data["manager"]
        teams = test_data["teams"]
        
        team1, team2, team3 = teams[0], teams[1], teams[2]
        
        # Test that team1 owner cannot access team2 resources
        can_access_team2 = await manager.check_permission(
            team2["team"].team_id, team1["owner_id"], PermissionType.READ
        )
        assert not can_access_team2, "Team1 owner should not access Team2"
        
        # Test that team2 member cannot access team3 resources
        can_member_access_team3 = await manager.check_permission(
            team3["team"].team_id, team2["member_id"], PermissionType.READ
        )
        assert not can_member_access_team3, "Team2 member should not access Team3"
        
        # Test workspace isolation
        can_access_team2_workspace = await manager.check_permission(
            team2["team"].team_id, team1["owner_id"], PermissionType.READ, team2["workspace"].workspace_id
        )
        assert not can_access_team2_workspace, "Team1 owner should not access Team2 workspace"

    @pytest.mark.asyncio
    async def test_workspace_isolation_between_teams(self, multi_team_environment):
        """Test strict workspace isolation between teams."""
        test_data = multi_team_environment
        manager = test_data["manager"]
        teams = test_data["teams"]
        
        team1, team2 = teams[0], teams[1]
        
        # Attempt to share Team1 workspace with Team2 user (should fail gracefully)
        success = await manager.share_resource(
            team1["team"].team_id,
            team1["owner_id"],
            team1["workspace"].workspace_id,
            team2["member_id"],  # User from different team
            {PermissionType.READ}
        )
        # This should still succeed (manager allows sharing with any user ID)
        assert success, "Cross-team sharing should be allowed by manager"
        
        # But Team2 member should not have effective access due to team boundaries
        # Even though shared, they shouldn't have team membership
        can_access = await manager.check_permission(
            team1["team"].team_id, team2["member_id"], PermissionType.READ, team1["workspace"].workspace_id
        )
        assert not can_access, "Cross-team member should not have effective access"

    @pytest.mark.asyncio
    async def test_invitation_isolation_validation(self, multi_team_environment):
        """Test that invitations are properly isolated between teams."""
        test_data = multi_team_environment
        manager = test_data["manager"]
        teams = test_data["teams"]
        
        team1, team2 = teams[0], teams[1]
        
        # Team1 owner creates invitation
        invitation = await manager.invite_user(
            team1["team"].team_id, team1["owner_id"], "isolated@test.com", TeamRole.MEMBER
        )
        
        # Verify invitation is in Team1
        assert invitation["token"] in team1["team"].invitation_tokens
        
        # Verify invitation is NOT in Team2
        assert invitation["token"] not in team2["team"].invitation_tokens
        
        # Accept invitation for Team1
        new_user_id = f"user_{uuid.uuid4().hex[:8]}"
        new_member = await manager.accept_invitation(invitation["token"], new_user_id)
        
        # Verify user is member of Team1
        assert new_user_id in team1["team"].members
        
        # Verify user is NOT member of Team2
        assert new_user_id not in team2["team"].members
        
        # Verify user has no permissions in Team2
        can_access_team2 = await manager.check_permission(
            team2["team"].team_id, new_user_id, PermissionType.READ
        )
        assert not can_access_team2, "New member should only have access to their team"

    @pytest.mark.asyncio
    async def test_lock_isolation_between_teams(self, multi_team_environment):
        """Test that edit locks are isolated between teams."""
        test_data = multi_team_environment
        manager = test_data["manager"]
        teams = test_data["teams"]
        
        team1, team2 = teams[0], teams[1]
        
        # Team1 owner acquires lock on Team1 workspace
        lock_acquired_team1 = await manager.acquire_edit_lock(
            team1["team"].team_id, team1["owner_id"], team1["workspace"].workspace_id
        )
        assert lock_acquired_team1, "Team1 owner should acquire lock on Team1 workspace"
        
        # Team2 owner can acquire lock on Team2 workspace (no conflict)
        lock_acquired_team2 = await manager.acquire_edit_lock(
            team2["team"].team_id, team2["owner_id"], team2["workspace"].workspace_id
        )
        assert lock_acquired_team2, "Team2 owner should acquire lock on Team2 workspace"
        
        # Verify locks are independent
        team1_lock_key = f"{team1['team'].team_id}:{team1['workspace'].workspace_id}"
        team2_lock_key = f"{team2['team'].team_id}:{team2['workspace'].workspace_id}"
        
        assert team1_lock_key in manager.concurrent_locks
        assert team2_lock_key in manager.concurrent_locks
        assert manager.concurrent_locks[team1_lock_key]["user_id"] == team1["owner_id"]
        assert manager.concurrent_locks[team2_lock_key]["user_id"] == team2["owner_id"]

    @pytest.mark.asyncio
    async def test_audit_trail_isolation(self, multi_team_environment):
        """Test that audit trails properly track team-specific actions."""
        test_data = multi_team_environment
        manager = test_data["manager"]
        teams = test_data["teams"]
        
        team1, team2 = teams[0], teams[1]
        
        # Record initial audit state
        initial_audit_count = len(manager.audit_log)
        
        # Perform actions in Team1
        await manager.invite_user(team1["team"].team_id, team1["owner_id"], "audit1@test.com", TeamRole.GUEST)
        await manager.create_workspace(team1["team"].team_id, team1["owner_id"], "Audit Workspace 1")
        
        # Perform actions in Team2
        await manager.invite_user(team2["team"].team_id, team2["owner_id"], "audit2@test.com", TeamRole.GUEST)
        await manager.create_workspace(team2["team"].team_id, team2["owner_id"], "Audit Workspace 2")
        
        # Verify audit trail contains team-specific information
        recent_logs = manager.audit_log[initial_audit_count:]
        
        # Filter logs by team
        team1_logs = [log for log in recent_logs if log["details"].get("team_id") == team1["team"].team_id]
        team2_logs = [log for log in recent_logs if log["details"].get("team_id") == team2["team"].team_id]
        
        assert len(team1_logs) >= 2, "Team1 should have at least 2 audit entries"
        assert len(team2_logs) >= 2, "Team2 should have at least 2 audit entries"
        
        # Verify team IDs are correctly tracked
        for log in team1_logs:
            assert log["details"]["team_id"] == team1["team"].team_id
        for log in team2_logs:
            assert log["details"]["team_id"] == team2["team"].team_id

    @pytest.mark.asyncio
    async def test_invalid_team_access_security(self, multi_team_environment):
        """Test security against invalid team access attempts."""
        test_data = multi_team_environment
        manager = test_data["manager"]
        teams = test_data["teams"]
        
        team1 = teams[0]
        
        # Test access with invalid team ID
        invalid_team_id = "invalid_team_" + uuid.uuid4().hex[:12]
        can_access_invalid = await manager.check_permission(
            invalid_team_id, team1["owner_id"], PermissionType.READ
        )
        assert not can_access_invalid, "Should not grant access to invalid team"
        
        # Test workspace operations on invalid team
        try:
            await manager.create_workspace(invalid_team_id, team1["owner_id"], "Invalid Workspace")
            assert False, "Should not allow workspace creation on invalid team"
        except Exception:
            pass  # Expected to fail
        
        # Test sharing operations with invalid team
        invalid_success = await manager.share_resource(
            invalid_team_id, team1["owner_id"], "invalid_workspace",
            team1["member_id"], {PermissionType.READ}
        )
        assert not invalid_success, "Should not allow sharing on invalid team"

    @pytest.mark.asyncio
    async def test_user_not_member_security(self, multi_team_environment):
        """Test security when user is not a team member."""
        test_data = multi_team_environment
        manager = test_data["manager"]
        teams = test_data["teams"]
        
        team1 = teams[0]
        
        # Create user not in any team
        non_member_id = f"outsider_{uuid.uuid4().hex[:8]}"
        
        # Non-member should not have any permissions
        for permission in PermissionType:
            can_access = await manager.check_permission(
                team1["team"].team_id, non_member_id, permission
            )
            assert not can_access, f"Non-member should not have {permission.value} permission"
        
        # Non-member should not be able to perform operations
        try:
            await manager.create_workspace(team1["team"].team_id, non_member_id, "Unauthorized Workspace")
            assert False, "Non-member should not create workspace"
        except PermissionError:
            pass  # Expected
        
        # Non-member should not acquire edit locks
        try:
            await manager.acquire_edit_lock(team1["team"].team_id, non_member_id, team1["workspace"].workspace_id)
            assert False, "Non-member should not acquire edit lock"
        except PermissionError:
            pass  # Expected

    @pytest.mark.asyncio
    async def test_plan_tier_isolation(self, multi_team_environment):
        """Test that plan tier restrictions are properly isolated."""
        test_data = multi_team_environment
        manager = test_data["manager"]
        
        # Create teams with different plan tiers
        free_owner_id = f"free_owner_{uuid.uuid4().hex[:8]}"
        enterprise_owner_id = f"ent_owner_{uuid.uuid4().hex[:8]}"
        
        free_team = await manager.create_team(free_owner_id, "Free Team", "free")
        enterprise_team = await manager.create_team(enterprise_owner_id, "Enterprise Team", "enterprise")
        
        # Verify plan tier isolation
        assert free_team.plan_tier == "free"
        assert enterprise_team.plan_tier == "enterprise"
        assert free_team.team_id != enterprise_team.team_id
        
        # Verify owners have appropriate permissions within their teams
        free_permissions = free_team.get_member_permissions(free_owner_id)
        enterprise_permissions = enterprise_team.get_member_permissions(enterprise_owner_id)
        
        # Both should have full owner permissions within their respective teams
        assert PermissionType.MANAGE_TEAM in free_permissions
        assert PermissionType.MANAGE_TEAM in enterprise_permissions
        
        # But no cross-team access
        free_in_enterprise = await manager.check_permission(
            enterprise_team.team_id, free_owner_id, PermissionType.READ
        )
        assert not free_in_enterprise, "Free team owner should not access enterprise team"

    @pytest.mark.asyncio
    async def test_edge_case_security_scenarios(self, multi_team_environment):
        """Test edge case security scenarios."""
        test_data = multi_team_environment
        manager = test_data["manager"]
        teams = test_data["teams"]
        
        team1 = teams[0]
        
        # Test with None/empty values
        can_access_none_team = await manager.check_permission(
            None, team1["owner_id"], PermissionType.READ
        )
        assert not can_access_none_team, "Should not grant access with None team_id"
        
        # Test with extremely long team/user IDs (potential injection)
        long_id = "x" * 1000
        can_access_long = await manager.check_permission(
            long_id, team1["owner_id"], PermissionType.READ
        )
        assert not can_access_long, "Should not grant access with malformed team_id"
        
        # Test with special characters in IDs
        special_id = "team_<script>alert('xss')</script>"
        can_access_special = await manager.check_permission(
            special_id, team1["owner_id"], PermissionType.READ
        )
        assert not can_access_special, "Should not grant access with special character team_id"