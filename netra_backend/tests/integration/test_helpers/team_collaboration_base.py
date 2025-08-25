"""Team Collaboration Test Base Classes and Utilities

Shared utilities for team collaboration integration tests.
Provides common fixtures, validation helpers, and test patterns.
"""

import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# Essential test environment setup
os.environ.update({
    "TESTING": "1", "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "GEMINI_API_KEY": "test-key", "GOOGLE_CLIENT_ID": "test-id", 
    "GOOGLE_CLIENT_SECRET": "test-secret", "CLICKHOUSE_PASSWORD": "test-pass"
})

class TeamRole(Enum):
    """Team role definitions for permissions testing."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"
    VIEWER = "viewer"

class PermissionType(Enum):
    """Permission types for resource access."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_TEAM = "manage_team"
    INVITE_USERS = "invite_users"
    MANAGE_PERMISSIONS = "manage_permissions"
    ACCESS_BILLING = "access_billing"

@dataclass
class TeamPermissionMatrix:
    """Permission matrix for different team roles."""
    owner: Set[PermissionType] = field(default_factory=lambda: {
        PermissionType.READ, PermissionType.WRITE, PermissionType.DELETE,
        PermissionType.MANAGE_TEAM, PermissionType.INVITE_USERS,
        PermissionType.MANAGE_PERMISSIONS, PermissionType.ACCESS_BILLING
    })
    admin: Set[PermissionType] = field(default_factory=lambda: {
        PermissionType.READ, PermissionType.WRITE, PermissionType.DELETE,
        PermissionType.MANAGE_TEAM, PermissionType.INVITE_USERS,
        PermissionType.MANAGE_PERMISSIONS
    })
    member: Set[PermissionType] = field(default_factory=lambda: {
        PermissionType.READ, PermissionType.WRITE, PermissionType.DELETE
    })
    guest: Set[PermissionType] = field(default_factory=lambda: {
        PermissionType.READ, PermissionType.WRITE
    })
    viewer: Set[PermissionType] = field(default_factory=lambda: {
        PermissionType.READ
    })
    
    def get_permissions(self, role: TeamRole) -> Set[PermissionType]:
        """Get permissions for a specific role."""
        return getattr(self, role.value)

@dataclass
class TeamMember:
    """Team member representation with permissions."""
    user_id: str
    email: str
    role: TeamRole
    invited_at: datetime
    joined_at: Optional[datetime] = None
    invited_by: Optional[str] = None
    is_active: bool = True
    workspace_access: Set[str] = field(default_factory=set)
    custom_permissions: Set[PermissionType] = field(default_factory=set)

@dataclass
class TeamWorkspace:
    """Team workspace with resources and permissions."""
    workspace_id: str
    name: str
    team_id: str
    created_by: str
    created_at: datetime
    resources: Set[str] = field(default_factory=set)
    access_members: Set[str] = field(default_factory=set)
    is_shared: bool = False
    sharing_permissions: Dict[str, Set[PermissionType]] = field(default_factory=dict)

@dataclass
class CollaborationTeam:
    """Team model for collaboration testing."""
    team_id: str
    name: str
    owner_id: str
    created_at: datetime
    plan_tier: str
    members: Dict[str, TeamMember] = field(default_factory=dict)
    workspaces: Dict[str, TeamWorkspace] = field(default_factory=dict)
    invitation_tokens: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    is_active: bool = True
    billing_contact: Optional[str] = None
    
    def add_member(self, member: TeamMember):
        """Add member to team with role validation."""
        self.members[member.user_id] = member
        
    def get_member_permissions(self, user_id: str) -> Set[PermissionType]:
        """Get effective permissions for a team member."""
        if user_id not in self.members:
            return set()
        
        member = self.members[user_id]
        matrix = TeamPermissionMatrix()
        base_permissions = matrix.get_permissions(member.role)
        
        # Combine with custom permissions
        return base_permissions.union(member.custom_permissions)

class TeamCollaborationManager:
    """Manages team collaboration features and permissions."""
    
    def __init__(self):
        self.teams: Dict[str, CollaborationTeam] = {}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, str] = {}  # user_id -> team_id
        self.concurrent_locks: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        
    async def create_team(self, owner_id: str, team_name: str, plan_tier: str = "pro") -> CollaborationTeam:
        """Create a new team with owner permissions."""
        team_id = f"team_{uuid.uuid4().hex[:12]}"
        
        owner_member = TeamMember(
            user_id=owner_id,
            email=f"owner_{owner_id}@test.com",
            role=TeamRole.OWNER,
            invited_at=datetime.now(timezone.utc),
            joined_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        team = CollaborationTeam(
            team_id=team_id,
            name=team_name,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
            plan_tier=plan_tier,
            billing_contact=owner_id
        )
        
        team.add_member(owner_member)
        self.teams[team_id] = team
        
        self._audit_log("team_created", {"team_id": team_id, "owner_id": owner_id})
        return team
        
    async def invite_user(self, team_id: str, inviter_id: str, invitee_email: str, 
                         role: TeamRole) -> Dict[str, Any]:
        """Invite user to team with role-based validation."""
        if team_id not in self.teams:
            raise ValueError(f"Team {team_id} not found")
            
        team = self.teams[team_id]
        
        # Check if inviter has permission to invite
        inviter_permissions = team.get_member_permissions(inviter_id)
        if PermissionType.INVITE_USERS not in inviter_permissions:
            raise PermissionError("Insufficient permissions to invite users")
            
        # Generate invitation token
        invitation_token = str(uuid.uuid4())
        invitation_data = {
            "token": invitation_token,
            "team_id": team_id,
            "invitee_email": invitee_email,
            "role": role.value,
            "inviter_id": inviter_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "status": "pending"
        }
        
        team.invitation_tokens[invitation_token] = invitation_data
        
        self._audit_log("user_invited", {
            "team_id": team_id, "inviter_id": inviter_id, 
            "invitee_email": invitee_email, "role": role.value
        })
        
        return invitation_data
        
    async def accept_invitation(self, invitation_token: str, user_id: str) -> TeamMember:
        """Accept team invitation and join team."""
        # Find invitation across all teams
        invitation_data = None
        team = None
        
        for team_obj in self.teams.values():
            if invitation_token in team_obj.invitation_tokens:
                invitation_data = team_obj.invitation_tokens[invitation_token]
                team = team_obj
                break
                
        if not invitation_data or not team:
            raise ValueError("Invalid or expired invitation token")
            
        if invitation_data["status"] != "pending":
            raise ValueError("Invitation already processed")
            
        # Check expiration
        expires_at = datetime.fromisoformat(invitation_data["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            raise ValueError("Invitation has expired")
            
        # Create team member
        member = TeamMember(
            user_id=user_id,
            email=invitation_data["invitee_email"],
            role=TeamRole(invitation_data["role"]),
            invited_at=datetime.fromisoformat(invitation_data["created_at"]),
            joined_at=datetime.now(timezone.utc),
            invited_by=invitation_data["inviter_id"],
            is_active=True
        )
        
        team.add_member(member)
        invitation_data["status"] = "accepted"
        
        self._audit_log("invitation_accepted", {
            "team_id": team.team_id, "user_id": user_id, 
            "role": member.role.value
        })
        
        return member

    async def check_permission(self, team_id: str, user_id: str, 
                             permission: PermissionType, resource_id: Optional[str] = None) -> bool:
        """Check if user has specific permission in team context."""
        start_time = time.time()
        
        if team_id not in self.teams:
            return False
            
        team = self.teams[team_id]
        permissions = team.get_member_permissions(user_id)
        
        # Check base permission
        has_permission = permission in permissions
        
        # Check resource-specific permissions if needed
        if resource_id and resource_id in team.workspaces:
            workspace = team.workspaces[resource_id]
            if workspace.is_shared:
                # Check sharing permissions
                if user_id in workspace.sharing_permissions:
                    shared_perms = workspace.sharing_permissions[user_id]
                    has_permission = has_permission and permission in shared_perms
                else:
                    has_permission = has_permission and user_id in workspace.access_members
            else:
                # Not shared workspace - only creator has access
                has_permission = has_permission and user_id == workspace.created_by
                    
        # Performance validation - should be <100ms
        duration_ms = (time.time() - start_time) * 1000
        assert duration_ms < 100, f"Permission check took {duration_ms}ms (exceeds 100ms limit)"
        
        self._audit_log("permission_check", {
            "team_id": team_id, "user_id": user_id, "permission": permission.value,
            "resource_id": resource_id, "granted": has_permission, "duration_ms": duration_ms
        })
        
        return has_permission

    def _audit_log(self, action: str, details: Dict[str, Any]):
        """Log team collaboration actions for audit trail."""
        self.audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details
        })

# Test validation helpers
def assert_permission_matrix(manager: TeamCollaborationManager, team_id: str, 
                           user_id: str, role: str, expected_permissions: Dict[PermissionType, bool]):
    """Assert user has expected permissions for their role."""
    for permission, should_have in expected_permissions.items():
        import asyncio
        has_permission = asyncio.run(manager.check_permission(team_id, user_id, permission))
        assert has_permission == should_have, \
            f"{role} should {'have' if should_have else 'not have'} {permission.value} permission"

def assert_performance_benchmark(manager: TeamCollaborationManager, team_id: str, 
                               user_id: str, iterations: int = 100, max_avg_ms: float = 50):
    """Assert permission check performance meets benchmarks."""
    import asyncio
    
    async def run_benchmark():
        start_time = time.time()
        for _ in range(iterations):
            await manager.check_permission(team_id, user_id, PermissionType.READ)
        total_time = (time.time() - start_time) * 1000
        avg_time = total_time / iterations
        assert avg_time < max_avg_ms, f"Average time {avg_time}ms exceeds {max_avg_ms}ms"
        return avg_time
    
    return asyncio.run(run_benchmark())

def validate_audit_trail(manager: TeamCollaborationManager, expected_actions: List[str]):
    """Validate audit trail contains expected actions."""
    recent_logs = [log for log in manager.audit_log if log["action"] != "permission_check"][-len(expected_actions):]
    for i, log_entry in enumerate(recent_logs):
        assert "timestamp" in log_entry
        assert "action" in log_entry
        assert "details" in log_entry
        if i < len(expected_actions):
            assert log_entry["action"] == expected_actions[i]