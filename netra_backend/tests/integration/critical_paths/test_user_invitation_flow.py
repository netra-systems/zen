"""User Invitation and Collaboration Flow Critical Path Tests

Business Value Justification (BVJ):
- Segment: Mid to Enterprise (team collaboration onboarding)
- Business Goal: User onboarding and team adoption
- Value Impact: Smooth team expansion, reduced friction
- Strategic Impact: Team productivity and enterprise conversion

Critical Path: Invitation creation -> Email delivery -> Acceptance -> Role activation
Coverage: Invitation workflow, permission validation, edge cases
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from netra_backend.tests.integration.test_helpers.team_collaboration_base import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    TeamCollaborationManager, TeamRole, PermissionType, validate_audit_trail
)


@pytest.fixture
async def team_with_admin():
    """Create team with owner and admin for invitation testing."""
    manager = TeamCollaborationManager()
    owner_id = f"user_{uuid.uuid4().hex[:8]}"
    team = await manager.create_team(owner_id, "Invitation Test Team", "pro")
    
    # Add admin
    admin_id = f"user_{uuid.uuid4().hex[:8]}"
    admin_invitation = await manager.invite_user(team.team_id, owner_id, "admin@test.com", TeamRole.ADMIN)
    await manager.accept_invitation(admin_invitation["token"], admin_id)
    
    return {
        "manager": manager,
        "team": team,
        "owner_id": owner_id,
        "admin_id": admin_id
    }


class TestUserInvitationFlow:
    """Critical path tests for user invitation and collaboration flows."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_invitation_workflow(self, team_with_admin):
        """Test complete user invitation workflow."""
        team_data = team_with_admin
        manager = team_data["manager"]
        team = team_data["team"]
        admin_id = team_data["admin_id"]
        
        # Test valid invitation by admin
        invitee_email = "newuser@test.com"
        invitation = await manager.invite_user(
            team.team_id, admin_id, invitee_email, TeamRole.MEMBER
        )
        
        # Validate invitation structure
        assert "token" in invitation
        assert invitation["team_id"] == team.team_id
        assert invitation["invitee_email"] == invitee_email
        assert invitation["role"] == TeamRole.MEMBER.value
        assert invitation["status"] == "pending"
        assert "expires_at" in invitation
        
        # Verify invitation stored in team
        assert invitation["token"] in team.invitation_tokens
        
        # Test invitation acceptance
        new_user_id = f"user_{uuid.uuid4().hex[:8]}"
        new_member = await manager.accept_invitation(invitation["token"], new_user_id)
        
        # Validate new member
        assert new_member.user_id == new_user_id
        assert new_member.email == invitee_email
        assert new_member.role == TeamRole.MEMBER
        assert new_member.is_active
        assert new_member.invited_by == admin_id
        
        # Verify new member in team
        assert new_user_id in team.members
        assert team.members[new_user_id] == new_member
        
        # Verify invitation status updated
        assert invitation["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_invitation_permission_validation(self, team_with_admin):
        """Test invitation permission validation for different roles."""
        team_data = team_with_admin
        manager = team_data["manager"]
        team = team_data["team"]
        owner_id = team_data["owner_id"]
        admin_id = team_data["admin_id"]
        
        # Add member and viewer without invitation permissions
        member_id = f"user_{uuid.uuid4().hex[:8]}"
        member_invitation = await manager.invite_user(team.team_id, admin_id, "member@test.com", TeamRole.MEMBER)
        await manager.accept_invitation(member_invitation["token"], member_id)
        
        viewer_id = f"user_{uuid.uuid4().hex[:8]}"
        viewer_invitation = await manager.invite_user(team.team_id, admin_id, "viewer@test.com", TeamRole.VIEWER)
        await manager.accept_invitation(viewer_invitation["token"], viewer_id)
        
        # Test that member cannot invite (no INVITE_USERS permission)
        with pytest.raises(PermissionError, match="Insufficient permissions to invite users"):
            await manager.invite_user(team.team_id, member_id, "unauthorized@test.com", TeamRole.GUEST)
        
        # Test that viewer cannot invite
        with pytest.raises(PermissionError, match="Insufficient permissions to invite users"):
            await manager.invite_user(team.team_id, viewer_id, "unauthorized2@test.com", TeamRole.GUEST)
        
        # Test that owner can invite
        owner_invitation = await manager.invite_user(team.team_id, owner_id, "owner_invite@test.com", TeamRole.GUEST)
        assert owner_invitation["status"] == "pending"
        
        # Test that admin can invite
        admin_invitation = await manager.invite_user(team.team_id, admin_id, "admin_invite@test.com", TeamRole.GUEST)
        assert admin_invitation["status"] == "pending"

    @pytest.mark.asyncio
    async def test_invitation_edge_cases_and_errors(self, team_with_admin):
        """Test invitation edge cases and error handling."""
        team_data = team_with_admin
        manager = team_data["manager"]
        team = team_data["team"]
        admin_id = team_data["admin_id"]
        
        # Test invitation to non-existent team
        with pytest.raises(ValueError, match="Team .+ not found"):
            await manager.invite_user("invalid_team", admin_id, "test@test.com", TeamRole.MEMBER)
        
        # Create valid invitation for expiration test
        invitation = await manager.invite_user(team.team_id, admin_id, "expire@test.com", TeamRole.MEMBER)
        
        # Test invalid token acceptance
        with pytest.raises(ValueError, match="Invalid or expired invitation token"):
            await manager.accept_invitation("invalid_token", "some_user")
        
        # Test expired invitation
        invitation["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with pytest.raises(ValueError, match="Invitation has expired"):
            await manager.accept_invitation(invitation["token"], f"user_{uuid.uuid4().hex[:8]}")
        
        # Reset invitation and accept it
        invitation["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        await manager.accept_invitation(invitation["token"], user_id)
        
        # Test duplicate invitation acceptance
        with pytest.raises(ValueError, match="Invitation already processed"):
            await manager.accept_invitation(invitation["token"], "another_user")

    @pytest.mark.asyncio
    async def test_invitation_audit_trail(self, team_with_admin):
        """Test audit trail for invitation workflow."""
        team_data = team_with_admin
        manager = team_data["manager"]
        team = team_data["team"]
        admin_id = team_data["admin_id"]
        
        # Record initial audit count
        initial_audit_count = len([log for log in manager.audit_log if log["action"] != "permission_check"])
        
        # Perform invitation workflow
        invitation = await manager.invite_user(team.team_id, admin_id, "audit@test.com", TeamRole.GUEST)
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        await manager.accept_invitation(invitation["token"], user_id)
        
        # Validate audit trail
        expected_actions = ["user_invited", "invitation_accepted"]
        validate_audit_trail(manager, expected_actions)
        
        # Verify audit count increased
        final_audit_count = len([log for log in manager.audit_log if log["action"] != "permission_check"])
        assert final_audit_count == initial_audit_count + 2

    @pytest.mark.asyncio
    async def test_multiple_role_invitations(self, team_with_admin):
        """Test invitations for all role types."""
        team_data = team_with_admin
        manager = team_data["manager"]
        team = team_data["team"]
        owner_id = team_data["owner_id"]
        
        # Test inviting users to different roles
        role_test_cases = [
            (TeamRole.ADMIN, "admin2@test.com"),
            (TeamRole.MEMBER, "member@test.com"),
            (TeamRole.GUEST, "guest@test.com"),
            (TeamRole.VIEWER, "viewer@test.com")
        ]
        
        for role, email in role_test_cases:
            # Create invitation
            invitation = await manager.invite_user(team.team_id, owner_id, email, role)
            assert invitation["role"] == role.value
            
            # Accept invitation
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            member = await manager.accept_invitation(invitation["token"], user_id)
            
            # Verify role assignment
            assert member.role == role
            assert team.members[user_id].role == role
            
            # Verify role permissions
            permissions = team.get_member_permissions(user_id)
            expected_permissions = team_data["manager"].teams[team.team_id].get_member_permissions(user_id)
            assert permissions == expected_permissions