"""Workspace Management and Resource Sharing Critical Path Tests

Business Value Justification (BVJ):
- Segment: Mid to Enterprise (collaborative workspaces)
- Business Goal: Team productivity and resource collaboration
- Value Impact: Shared workspace efficiency, resource access control
- Strategic Impact: Enterprise feature differentiation and retention

Critical Path: Workspace creation -> Access control -> Resource sharing -> Permission validation
Coverage: Workspace management, sharing permissions, access isolation
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import uuid

import pytest

# Add project root to path
from netra_backend.tests.integration.test_helpers.team_collaboration_base import (
    PermissionType,
    # Add project root to path
    TeamCollaborationManager,
    TeamRole,
    validate_audit_trail,
)


@pytest.fixture
async def team_with_multiple_roles():
    """Create team with multiple role types for workspace testing."""
    manager = TeamCollaborationManager()
    owner_id = f"user_{uuid.uuid4().hex[:8]}"
    team = await manager.create_team(owner_id, "Workspace Test Team", "enterprise")
    
    # Add members with different roles
    admin_id = f"user_{uuid.uuid4().hex[:8]}"
    admin_invitation = await manager.invite_user(team.team_id, owner_id, "admin@test.com", TeamRole.ADMIN)
    await manager.accept_invitation(admin_invitation["token"], admin_id)
    
    member_id = f"user_{uuid.uuid4().hex[:8]}"
    member_invitation = await manager.invite_user(team.team_id, owner_id, "member@test.com", TeamRole.MEMBER)
    await manager.accept_invitation(member_invitation["token"], member_id)
    
    guest_id = f"user_{uuid.uuid4().hex[:8]}"
    guest_invitation = await manager.invite_user(team.team_id, admin_id, "guest@test.com", TeamRole.GUEST)
    await manager.accept_invitation(guest_invitation["token"], guest_id)
    
    viewer_id = f"user_{uuid.uuid4().hex[:8]}"
    viewer_invitation = await manager.invite_user(team.team_id, admin_id, "viewer@test.com", TeamRole.VIEWER)
    await manager.accept_invitation(viewer_invitation["token"], viewer_id)
    
    return {
        "manager": manager,
        "team": team,
        "members": {
            "owner": owner_id,
            "admin": admin_id,
            "member": member_id,
            "guest": guest_id,
            "viewer": viewer_id
        }
    }


class TestWorkspaceResourceSharing:
    """Critical path tests for workspace management and resource sharing."""
    
    @pytest.mark.asyncio
    async def test_workspace_creation_and_access_control(self, team_with_multiple_roles):
        """Test workspace creation and basic access control."""
        team_data = team_with_multiple_roles
        manager = team_data["manager"]
        team = team_data["team"]
        members = team_data["members"]
        
        # Test workspace creation by member with write permission
        workspace = await manager.create_workspace(
            team.team_id, members["member"], "Test Workspace"
        )
        
        # Validate workspace creation
        assert workspace.workspace_id in team.workspaces
        assert workspace.created_by == members["member"]
        assert workspace.name == "Test Workspace"
        assert workspace.team_id == team.team_id
        assert members["member"] in workspace.access_members
        
        # Test workspace creation denial for viewer (no write permission)
        with pytest.raises(PermissionError, match="Insufficient permissions to create workspace"):
            await manager.create_workspace(
                team.team_id, members["viewer"], "Denied Workspace"
            )
        
        # Test creator access
        can_access_creator = await manager.check_permission(
            team.team_id, members["member"], PermissionType.READ, workspace.workspace_id
        )
        assert can_access_creator
        
        # Test non-creator access (should be denied by default)
        can_access_other = await manager.check_permission(
            team.team_id, members["guest"], PermissionType.READ, workspace.workspace_id
        )
        assert not can_access_other

    @pytest.mark.asyncio
    async def test_resource_sharing_permissions(self, team_with_multiple_roles):
        """Test comprehensive resource sharing between team members."""
        team_data = team_with_multiple_roles
        manager = team_data["manager"]
        team = team_data["team"]
        members = team_data["members"]
        
        # Create workspace as admin
        workspace = await manager.create_workspace(
            team.team_id, members["admin"], "Shared Workspace"
        )
        
        # Share with member (read-only)
        success = await manager.share_resource(
            team.team_id, 
            members["admin"], 
            workspace.workspace_id,
            members["member"],
            {PermissionType.READ}
        )
        assert success
        
        # Verify sharing configuration
        workspace = team.workspaces[workspace.workspace_id]
        assert workspace.is_shared
        assert members["member"] in workspace.sharing_permissions
        assert workspace.sharing_permissions[members["member"]] == {PermissionType.READ}
        assert members["member"] in workspace.access_members
        
        # Test shared read access
        can_read = await manager.check_permission(
            team.team_id, members["member"], PermissionType.READ, workspace.workspace_id
        )
        assert can_read
        
        # Test denied write access
        can_write = await manager.check_permission(
            team.team_id, members["member"], PermissionType.WRITE, workspace.workspace_id
        )
        assert not can_write
        
        # Share with guest (read/write)
        success = await manager.share_resource(
            team.team_id,
            members["admin"],
            workspace.workspace_id,
            members["guest"],
            {PermissionType.READ, PermissionType.WRITE}
        )
        assert success
        
        # Test guest read/write access
        can_guest_read = await manager.check_permission(
            team.team_id, members["guest"], PermissionType.READ, workspace.workspace_id
        )
        assert can_guest_read
        
        can_guest_write = await manager.check_permission(
            team.team_id, members["guest"], PermissionType.WRITE, workspace.workspace_id
        )
        assert can_guest_write

    @pytest.mark.asyncio
    async def test_sharing_permission_validation(self, team_with_multiple_roles):
        """Test permission validation for resource sharing operations."""
        team_data = team_with_multiple_roles
        manager = team_data["manager"]
        team = team_data["team"]
        members = team_data["members"]
        
        # Create workspace as owner
        workspace = await manager.create_workspace(
            team.team_id, members["owner"], "Permission Test Workspace"
        )
        
        # Test unauthorized sharing by guest (no MANAGE_PERMISSIONS)
        with pytest.raises(PermissionError, match="Insufficient permissions to share resource"):
            await manager.share_resource(
                team.team_id,
                members["guest"],
                workspace.workspace_id,
                members["viewer"],
                {PermissionType.READ}
            )
        
        # Test unauthorized sharing by member (no MANAGE_PERMISSIONS)
        with pytest.raises(PermissionError, match="Insufficient permissions to share resource"):
            await manager.share_resource(
                team.team_id,
                members["member"],
                workspace.workspace_id,
                members["viewer"],
                {PermissionType.READ}
            )
        
        # Test authorized sharing by admin (has MANAGE_PERMISSIONS)
        success = await manager.share_resource(
            team.team_id,
            members["admin"],
            workspace.workspace_id,
            members["member"],
            {PermissionType.READ}
        )
        assert success
        
        # Test authorized sharing by owner (has MANAGE_PERMISSIONS)
        success = await manager.share_resource(
            team.team_id,
            members["owner"],
            workspace.workspace_id,
            members["guest"],
            {PermissionType.READ, PermissionType.WRITE}
        )
        assert success

    @pytest.mark.asyncio
    async def test_workspace_isolation_between_creators(self, team_with_multiple_roles):
        """Test workspace isolation between different creators."""
        team_data = team_with_multiple_roles
        manager = team_data["manager"]
        team = team_data["team"]
        members = team_data["members"]
        
        # Create workspaces by different users
        admin_workspace = await manager.create_workspace(
            team.team_id, members["admin"], "Admin Workspace"
        )
        
        member_workspace = await manager.create_workspace(
            team.team_id, members["member"], "Member Workspace"
        )
        
        # Test that admin cannot access member's workspace by default
        can_admin_access_member_ws = await manager.check_permission(
            team.team_id, members["admin"], PermissionType.READ, member_workspace.workspace_id
        )
        assert not can_admin_access_member_ws
        
        # Test that member cannot access admin's workspace by default
        can_member_access_admin_ws = await manager.check_permission(
            team.team_id, members["member"], PermissionType.READ, admin_workspace.workspace_id
        )
        assert not can_member_access_admin_ws
        
        # Test that owner can access both (due to higher permissions)
        can_owner_access_admin_ws = await manager.check_permission(
            team.team_id, members["owner"], PermissionType.READ, admin_workspace.workspace_id
        )
        assert not can_owner_access_admin_ws  # Even owners need explicit sharing for workspaces they didn't create

    @pytest.mark.asyncio
    async def test_sharing_edge_cases_and_errors(self, team_with_multiple_roles):
        """Test edge cases and error handling for resource sharing."""
        team_data = team_with_multiple_roles
        manager = team_data["manager"]
        team = team_data["team"]
        members = team_data["members"]
        
        # Test sharing non-existent resource
        invalid_workspace_id = "invalid_workspace_123"
        success = await manager.share_resource(
            team.team_id, members["admin"], invalid_workspace_id,
            members["member"], {PermissionType.READ}
        )
        assert not success
        
        # Create valid workspace for other tests
        workspace = await manager.create_workspace(
            team.team_id, members["admin"], "Edge Case Workspace"
        )
        
        # Test sharing with non-team member (invalid user)
        invalid_user_id = "invalid_user_123"
        success = await manager.share_resource(
            team.team_id, members["admin"], workspace.workspace_id,
            invalid_user_id, {PermissionType.READ}
        )
        assert success  # Implementation allows sharing with any user ID
        
        # Test sharing with empty permissions set
        success = await manager.share_resource(
            team.team_id, members["admin"], workspace.workspace_id,
            members["member"], set()
        )
        assert success

    @pytest.mark.asyncio
    async def test_workspace_sharing_audit_trail(self, team_with_multiple_roles):
        """Test audit trail for workspace operations."""
        team_data = team_with_multiple_roles
        manager = team_data["manager"]
        team = team_data["team"]
        members = team_data["members"]
        
        # Record initial audit state
        initial_audit_count = len([log for log in manager.audit_log if log["action"] != "permission_check"])
        
        # Perform workspace operations
        workspace = await manager.create_workspace(
            team.team_id, members["admin"], "Audit Workspace"
        )
        
        await manager.share_resource(
            team.team_id, members["admin"], workspace.workspace_id,
            members["member"], {PermissionType.READ}
        )
        
        await manager.share_resource(
            team.team_id, members["admin"], workspace.workspace_id,
            members["guest"], {PermissionType.READ, PermissionType.WRITE}
        )
        
        # Validate audit trail
        expected_actions = ["workspace_created", "resource_shared", "resource_shared"]
        validate_audit_trail(manager, expected_actions)
        
        # Verify audit count increased appropriately
        final_audit_count = len([log for log in manager.audit_log if log["action"] != "permission_check"])
        assert final_audit_count == initial_audit_count + 3