"""Team Creation and Permission Management Critical Path Tests

Business Value Justification (BVJ):
- Segment: Mid to Enterprise (team collaboration features)
- Business Goal: Multi-user workflows protecting $100K-$200K MRR
- Value Impact: Team productivity, enterprise sales, user retention
- Strategic Impact: Revenue pipeline tier differentiation

Critical Path: Team creation -> Role assignment -> Permission validation
Coverage: Team ownership, role-based permissions, permission inheritance
"""

import pytest
import uuid
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.integration.test_helpers.team_collaboration_base import (

# Add project root to path
    TeamCollaborationManager, TeamRole, PermissionType, TeamPermissionMatrix,
    assert_permission_matrix
)


@pytest.fixture
async def team_manager():
    """Create team collaboration manager for testing."""
    return TeamCollaborationManager()


class TestTeamCreationPermissions:
    """Critical path tests for team creation and permission management."""
    
    @pytest.mark.asyncio
    async def test_team_creation_and_ownership(self, team_manager: TeamCollaborationManager):
        """Test team creation and owner permission assignment."""
        owner_id = f"user_{uuid.uuid4().hex[:8]}"
        team = await team_manager.create_team(owner_id, "New Team", "pro")
        
        # Verify team creation
        assert team.team_id in team_manager.teams
        assert team.owner_id == owner_id
        assert team.plan_tier == "pro"
        assert len(team.members) == 1
        
        # Verify owner permissions
        owner_permissions = team.get_member_permissions(owner_id)
        expected_permissions = TeamPermissionMatrix().owner
        assert owner_permissions == expected_permissions
        
        # Verify owner can access all permission types
        for permission in PermissionType:
            has_permission = await team_manager.check_permission(team.team_id, owner_id, permission)
            assert has_permission, f"Owner should have {permission.value} permission"

    @pytest.mark.asyncio
    async def test_role_based_permission_matrix(self, team_manager: TeamCollaborationManager):
        """Test comprehensive role-based permission matrix validation."""
        # Create team with owner
        owner_id = f"user_{uuid.uuid4().hex[:8]}"
        team = await team_manager.create_team(owner_id, "Test Team", "enterprise")
        
        # Add members with different roles
        admin_id = f"user_{uuid.uuid4().hex[:8]}"
        member_id = f"user_{uuid.uuid4().hex[:8]}"
        guest_id = f"user_{uuid.uuid4().hex[:8]}"
        viewer_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Create and accept invitations
        admin_invitation = await team_manager.invite_user(team.team_id, owner_id, "admin@test.com", TeamRole.ADMIN)
        await team_manager.accept_invitation(admin_invitation["token"], admin_id)
        
        member_invitation = await team_manager.invite_user(team.team_id, owner_id, "member@test.com", TeamRole.MEMBER)
        await team_manager.accept_invitation(member_invitation["token"], member_id)
        
        guest_invitation = await team_manager.invite_user(team.team_id, admin_id, "guest@test.com", TeamRole.GUEST)
        await team_manager.accept_invitation(guest_invitation["token"], guest_id)
        
        viewer_invitation = await team_manager.invite_user(team.team_id, admin_id, "viewer@test.com", TeamRole.VIEWER)
        await team_manager.accept_invitation(viewer_invitation["token"], viewer_id)
        
        # Define expected permissions for each role
        permission_expectations = {
            "owner": {perm: True for perm in PermissionType},
            "admin": {
                PermissionType.READ: True,
                PermissionType.WRITE: True,
                PermissionType.DELETE: True,
                PermissionType.MANAGE_TEAM: True,
                PermissionType.INVITE_USERS: True,
                PermissionType.MANAGE_PERMISSIONS: True,
                PermissionType.ACCESS_BILLING: False
            },
            "member": {
                PermissionType.READ: True,
                PermissionType.WRITE: True,
                PermissionType.DELETE: True,
                PermissionType.MANAGE_TEAM: False,
                PermissionType.INVITE_USERS: False,
                PermissionType.MANAGE_PERMISSIONS: False,
                PermissionType.ACCESS_BILLING: False
            },
            "guest": {
                PermissionType.READ: True,
                PermissionType.WRITE: True,
                PermissionType.DELETE: False,
                PermissionType.MANAGE_TEAM: False,
                PermissionType.INVITE_USERS: False,
                PermissionType.MANAGE_PERMISSIONS: False,
                PermissionType.ACCESS_BILLING: False
            },
            "viewer": {
                PermissionType.READ: True,
                PermissionType.WRITE: False,
                PermissionType.DELETE: False,
                PermissionType.MANAGE_TEAM: False,
                PermissionType.INVITE_USERS: False,
                PermissionType.MANAGE_PERMISSIONS: False,
                PermissionType.ACCESS_BILLING: False
            }
        }
        
        # Test each role's permissions
        members = {"owner": owner_id, "admin": admin_id, "member": member_id, "guest": guest_id, "viewer": viewer_id}
        for role_name, user_id in members.items():
            assert_permission_matrix(team_manager, team.team_id, user_id, role_name, permission_expectations[role_name])

    @pytest.mark.asyncio
    async def test_permission_inheritance_and_override(self, team_manager: TeamCollaborationManager):
        """Test permission inheritance and custom permission overrides."""
        owner_id = f"user_{uuid.uuid4().hex[:8]}"
        team = await team_manager.create_team(owner_id, "Inheritance Team", "enterprise")
        
        # Add member
        member_id = f"user_{uuid.uuid4().hex[:8]}"
        member_invitation = await team_manager.invite_user(team.team_id, owner_id, "member@test.com", TeamRole.MEMBER)
        await team_manager.accept_invitation(member_invitation["token"], member_id)
        
        # Get current member permissions
        original_permissions = team.get_member_permissions(member_id)
        
        # Verify base permissions
        assert PermissionType.WRITE in original_permissions
        assert PermissionType.MANAGE_TEAM not in original_permissions
        
        # Add custom permission to member
        team.members[member_id].custom_permissions.add(PermissionType.MANAGE_TEAM)
        
        # Verify permission inheritance
        updated_permissions = team.get_member_permissions(member_id)
        assert PermissionType.WRITE in updated_permissions  # Base permission
        assert PermissionType.MANAGE_TEAM in updated_permissions  # Custom permission
        
        # Test effective permission checking
        can_manage_team = await team_manager.check_permission(
            team.team_id, member_id, PermissionType.MANAGE_TEAM
        )
        assert can_manage_team

    @pytest.mark.asyncio
    async def test_plan_tier_restrictions(self, team_manager: TeamCollaborationManager):
        """Test plan tier-based restrictions for team features."""
        # Create teams with different plan tiers
        free_owner_id = f"user_{uuid.uuid4().hex[:8]}"
        pro_owner_id = f"user_{uuid.uuid4().hex[:8]}"
        enterprise_owner_id = f"user_{uuid.uuid4().hex[:8]}"
        
        free_team = await team_manager.create_team(free_owner_id, "Free Team", "free")
        pro_team = await team_manager.create_team(pro_owner_id, "Pro Team", "pro")
        enterprise_team = await team_manager.create_team(enterprise_owner_id, "Enterprise Team", "enterprise")
        
        # Test that plan tiers are properly set
        assert free_team.plan_tier == "free"
        assert pro_team.plan_tier == "pro" 
        assert enterprise_team.plan_tier == "enterprise"
        
        # Verify all owners have full permissions regardless of tier
        for team in [free_team, pro_team, enterprise_team]:
            owner_permissions = team.get_member_permissions(team.owner_id)
            expected_permissions = TeamPermissionMatrix().owner
            assert owner_permissions == expected_permissions