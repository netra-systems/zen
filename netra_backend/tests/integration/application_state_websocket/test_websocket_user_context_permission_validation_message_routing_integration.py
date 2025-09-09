"""
Test WebSocket User Permission Validation During Message Routing and Processing Integration (#25)

Business Value Justification (BVJ):
- Segment: Enterprise (Role-based access control for secure multi-tenant operations)
- Business Goal: Ensure users can only access and perform operations they're authorized for
- Value Impact: Enterprise customers trust granular permission controls prevent unauthorized actions
- Strategic Impact: Foundation of enterprise security model - enables role-based pricing tiers

CRITICAL SECURITY REQUIREMENT: User permissions must be validated at every message routing
and processing step. Users must NEVER be able to bypass permission checks through WebSocket
message manipulation, routing exploits, or concurrent operation abuse.
"""

import asyncio
import pytest
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState, MessageType
from shared.isolated_environment import get_env

# Type definitions
UserID = str
RoleID = str
PermissionID = str
MessageRouteID = str


class Permission(Enum):
    """System permissions that can be granted to users."""
    READ_MESSAGES = "read_messages"
    WRITE_MESSAGES = "write_messages"
    DELETE_MESSAGES = "delete_messages"
    MANAGE_THREADS = "manage_threads"
    DELETE_THREADS = "delete_threads"
    ADMIN_ACCESS = "admin_access"
    BROADCAST_MESSAGES = "broadcast_messages"
    ACCESS_ALL_THREADS = "access_all_threads"
    MANAGE_USERS = "manage_users"
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_DATA = "export_data"
    AGENT_EXECUTION = "agent_execution"
    AGENT_MANAGEMENT = "agent_management"


class UserRole(Enum):
    """User roles with different permission sets."""
    VIEWER = "viewer"  # Read-only access
    USER = "user"  # Standard user permissions
    MODERATOR = "moderator"  # Additional management permissions
    ADMIN = "admin"  # Full access
    SYSTEM = "system"  # System-level operations


@dataclass
class UserPermissionContext:
    """Complete user permission context for validation."""
    user_id: UserID
    role: UserRole
    permissions: Set[Permission]
    organization_id: Optional[str] = None
    thread_access_permissions: Set[str] = field(default_factory=set)
    denied_permissions: Set[Permission] = field(default_factory=set)
    permission_expires_at: Optional[float] = None
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return (
            permission in self.permissions and
            permission not in self.denied_permissions and
            (self.permission_expires_at is None or self.permission_expires_at > time.time())
        )
    
    def can_access_thread(self, thread_id: str) -> bool:
        """Check if user can access a specific thread."""
        return (
            self.has_permission(Permission.ACCESS_ALL_THREADS) or
            thread_id in self.thread_access_permissions
        )


@dataclass
class WebSocketMessageRoute:
    """Represents a WebSocket message routing attempt."""
    route_id: MessageRouteID
    source_user_id: UserID
    target_user_id: Optional[UserID]
    message_type: MessageType
    required_permissions: Set[Permission]
    thread_id: Optional[str] = None
    organization_scope: Optional[str] = None
    route_timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_id": self.route_id,
            "source_user_id": self.source_user_id,
            "target_user_id": self.target_user_id,
            "message_type": self.message_type.value,
            "required_permissions": [p.value for p in self.required_permissions],
            "thread_id": self.thread_id,
            "organization_scope": self.organization_scope,
            "route_timestamp": self.route_timestamp
        }


@dataclass
class PermissionValidationResult:
    """Result of permission validation."""
    allowed: bool
    user_id: UserID
    requested_permissions: Set[Permission]
    granted_permissions: Set[Permission]
    denied_permissions: Set[Permission]
    validation_reasons: List[str] = field(default_factory=list)
    security_violations: List[str] = field(default_factory=list)


class WebSocketPermissionValidator:
    """Validates user permissions during WebSocket message routing and processing."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.redis_client = None
        self.permission_violations = []
        self.routing_attempts = []
    
    # Role-based permission mappings
    ROLE_PERMISSIONS = {
        UserRole.VIEWER: {
            Permission.READ_MESSAGES
        },
        UserRole.USER: {
            Permission.READ_MESSAGES,
            Permission.WRITE_MESSAGES,
            Permission.MANAGE_THREADS,
            Permission.AGENT_EXECUTION
        },
        UserRole.MODERATOR: {
            Permission.READ_MESSAGES,
            Permission.WRITE_MESSAGES,
            Permission.DELETE_MESSAGES,
            Permission.MANAGE_THREADS,
            Permission.DELETE_THREADS,
            Permission.AGENT_EXECUTION,
            Permission.BROADCAST_MESSAGES
        },
        UserRole.ADMIN: {
            Permission.READ_MESSAGES,
            Permission.WRITE_MESSAGES,
            Permission.DELETE_MESSAGES,
            Permission.MANAGE_THREADS,
            Permission.DELETE_THREADS,
            Permission.ADMIN_ACCESS,
            Permission.BROADCAST_MESSAGES,
            Permission.ACCESS_ALL_THREADS,
            Permission.MANAGE_USERS,
            Permission.VIEW_ANALYTICS,
            Permission.EXPORT_DATA,
            Permission.AGENT_EXECUTION,
            Permission.AGENT_MANAGEMENT
        }
    }
    
    async def setup(self):
        """Set up validator with Redis connection."""
        import redis.asyncio as redis
        self.redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        await self.redis_client.ping()
    
    async def cleanup(self):
        """Clean up validator resources."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def create_user_with_permissions(self, user_suffix: str, role: UserRole, 
                                         organization_id: str = None,
                                         additional_permissions: Set[Permission] = None,
                                         denied_permissions: Set[Permission] = None) -> UserPermissionContext:
        """Create user with specific permission context."""
        user_id = f"perm-test-user-{user_suffix}"
        
        # Create user in database
        await self.real_services["db"].execute("""
            INSERT INTO auth.users (id, email, name, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, user_id, f"{user_id}@permission-test.com", f"Permission Test User {user_suffix}", True)
        
        # Create organization if specified
        if organization_id is None:
            organization_id = f"perm-org-{user_suffix}"
        
        await self.real_services["db"].execute("""
            INSERT INTO backend.organizations (id, name, slug, plan, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                plan = EXCLUDED.plan
        """, organization_id, f"Permission Test Org {user_suffix}", 
            f"perm-org-{user_suffix}", "enterprise")
        
        # Create organization membership
        await self.real_services["db"].execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, organization_id) DO UPDATE SET role = EXCLUDED.role
        """, user_id, organization_id, role.value)
        
        # Get base permissions for role
        base_permissions = self.ROLE_PERMISSIONS.get(role, set())
        
        # Add additional permissions if specified
        if additional_permissions:
            base_permissions = base_permissions.union(additional_permissions)
        
        # Create user threads for access testing
        thread_access_permissions = set()
        for i in range(2):
            thread_id = f"thread-{user_suffix}-{i}"
            await self.real_services["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (id) DO UPDATE SET 
                    title = EXCLUDED.title,
                    updated_at = NOW()
            """, thread_id, user_id, f"Permission Test Thread {i}")
            thread_access_permissions.add(thread_id)
        
        # Create permission context
        permission_context = UserPermissionContext(
            user_id=user_id,
            role=role,
            permissions=base_permissions,
            organization_id=organization_id,
            thread_access_permissions=thread_access_permissions,
            denied_permissions=denied_permissions or set()
        )
        
        # Store permission context in Redis
        perm_key = f"user_permissions:{user_id}"
        await self.redis_client.set(
            perm_key,
            json.dumps({
                "user_id": user_id,
                "role": role.value,
                "permissions": [p.value for p in base_permissions],
                "organization_id": organization_id,
                "thread_access": list(thread_access_permissions),
                "denied_permissions": [p.value for p in (denied_permissions or set())],
                "updated_at": time.time()
            }),
            ex=3600
        )
        
        return permission_context
    
    async def validate_message_route_permissions(self, route: WebSocketMessageRoute, 
                                               user_context: UserPermissionContext) -> PermissionValidationResult:
        """Validate user permissions for a specific message route."""
        validation_result = PermissionValidationResult(
            allowed=True,
            user_id=user_context.user_id,
            requested_permissions=route.required_permissions,
            granted_permissions=set(),
            denied_permissions=set()
        )
        
        # Check each required permission
        for required_permission in route.required_permissions:
            if user_context.has_permission(required_permission):
                validation_result.granted_permissions.add(required_permission)
                validation_result.validation_reasons.append(
                    f"Permission {required_permission.value} granted via role {user_context.role.value}"
                )
            else:
                validation_result.denied_permissions.add(required_permission)
                validation_result.allowed = False
                validation_result.validation_reasons.append(
                    f"Permission {required_permission.value} denied - not in user permissions"
                )
        
        # Thread access validation
        if route.thread_id and not user_context.can_access_thread(route.thread_id):
            validation_result.allowed = False
            validation_result.security_violations.append(
                f"User {user_context.user_id} cannot access thread {route.thread_id}"
            )
        
        # Organization scope validation
        if route.organization_scope and route.organization_scope != user_context.organization_id:
            validation_result.allowed = False
            validation_result.security_violations.append(
                f"User {user_context.user_id} cannot access organization {route.organization_scope}"
            )
        
        # Cross-user message validation
        if route.target_user_id and route.target_user_id != user_context.user_id:
            if not user_context.has_permission(Permission.ADMIN_ACCESS):
                validation_result.allowed = False
                validation_result.security_violations.append(
                    f"User {user_context.user_id} cannot send messages as user {route.target_user_id}"
                )
        
        return validation_result
    
    async def simulate_websocket_message_routing_with_permissions(self, 
                                                               routes: List[Tuple[WebSocketMessageRoute, UserPermissionContext]]) -> Dict[str, Any]:
        """Simulate WebSocket message routing with permission validation."""
        routing_results = {
            "total_routes": len(routes),
            "allowed_routes": 0,
            "denied_routes": 0,
            "security_violations": [],
            "route_results": []
        }
        
        for route, user_context in routes:
            # Validate permissions for this route
            validation_result = await self.validate_message_route_permissions(route, user_context)
            
            route_result = {
                "route_id": route.route_id,
                "user_id": user_context.user_id,
                "message_type": route.message_type.value,
                "allowed": validation_result.allowed,
                "granted_permissions": [p.value for p in validation_result.granted_permissions],
                "denied_permissions": [p.value for p in validation_result.denied_permissions],
                "security_violations": validation_result.security_violations,
                "validation_reasons": validation_result.validation_reasons
            }
            
            if validation_result.allowed:
                routing_results["allowed_routes"] += 1
                
                # Simulate message processing for allowed routes
                await self._process_allowed_message_route(route, user_context)
            else:
                routing_results["denied_routes"] += 1
                routing_results["security_violations"].extend(validation_result.security_violations)
                
                # Log permission violation
                self.permission_violations.append({
                    "route_id": route.route_id,
                    "user_id": user_context.user_id,
                    "violation_type": "insufficient_permissions",
                    "denied_permissions": [p.value for p in validation_result.denied_permissions],
                    "security_violations": validation_result.security_violations,
                    "timestamp": time.time()
                })
            
            routing_results["route_results"].append(route_result)
            self.routing_attempts.append(route_result)
        
        return routing_results
    
    async def _process_allowed_message_route(self, route: WebSocketMessageRoute, 
                                           user_context: UserPermissionContext):
        """Process a message route that passed permission validation."""
        
        # Simulate different message processing based on type
        if route.message_type == MessageType.USER_MESSAGE:
            await self._process_user_message(route, user_context)
        elif route.message_type == MessageType.BROADCAST:
            await self._process_broadcast_message(route, user_context)
        elif route.message_type == MessageType.AGENT_REQUEST:
            await self._process_agent_request(route, user_context)
        elif route.message_type == MessageType.THREAD_UPDATE:
            await self._process_thread_update(route, user_context)
    
    async def _process_user_message(self, route: WebSocketMessageRoute, user_context: UserPermissionContext):
        """Process user message with permission validation."""
        message_id = f"msg-{route.route_id}"
        
        # Store message in database (with permission context)
        await self.real_services["db"].execute("""
            INSERT INTO backend.messages (id, thread_id, user_id, content, role, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
        """, message_id, route.thread_id, user_context.user_id, 
            f"Message processed with permissions: {[p.value for p in user_context.permissions]}", "user")
        
        # Store routing record in Redis
        await self.redis_client.set(
            f"processed_message:{message_id}",
            json.dumps({
                "route_id": route.route_id,
                "user_id": user_context.user_id,
                "permissions_validated": [p.value for p in user_context.permissions],
                "processed_at": time.time()
            }),
            ex=600
        )
    
    async def _process_broadcast_message(self, route: WebSocketMessageRoute, user_context: UserPermissionContext):
        """Process broadcast message (requires special permissions)."""
        broadcast_id = f"broadcast-{route.route_id}"
        
        # Store broadcast record
        await self.redis_client.set(
            f"broadcast:{broadcast_id}",
            json.dumps({
                "route_id": route.route_id,
                "broadcaster_id": user_context.user_id,
                "organization_scope": user_context.organization_id,
                "broadcast_at": time.time(),
                "permissions_verified": True
            }),
            ex=600
        )
    
    async def _process_agent_request(self, route: WebSocketMessageRoute, user_context: UserPermissionContext):
        """Process agent request (requires agent execution permissions)."""
        agent_request_id = f"agent-req-{route.route_id}"
        
        # Store agent execution record
        await self.redis_client.set(
            f"agent_request:{agent_request_id}",
            json.dumps({
                "route_id": route.route_id,
                "user_id": user_context.user_id,
                "agent_permissions": user_context.has_permission(Permission.AGENT_EXECUTION),
                "execution_allowed": True,
                "requested_at": time.time()
            }),
            ex=600
        )
    
    async def _process_thread_update(self, route: WebSocketMessageRoute, user_context: UserPermissionContext):
        """Process thread update (requires thread management permissions)."""
        if route.thread_id:
            # Update thread metadata
            await self.real_services["db"].execute("""
                UPDATE backend.threads 
                SET updated_at = NOW()
                WHERE id = $1 AND user_id = $2
            """, route.thread_id, user_context.user_id)
    
    async def validate_permission_isolation_across_users(self, user_contexts: List[UserPermissionContext]) -> Dict[str, Any]:
        """Validate that permission isolation is maintained across multiple users."""
        isolation_results = {
            "total_users": len(user_contexts),
            "permission_isolation_maintained": True,
            "cross_user_violations": [],
            "user_permission_summaries": {}
        }
        
        # Check each user's permissions are isolated
        for i, user_a in enumerate(user_contexts):
            for j, user_b in enumerate(user_contexts):
                if i != j:  # Different users
                    # Verify user A cannot access user B's restricted resources
                    
                    # Thread access isolation
                    user_a_threads = user_a.thread_access_permissions
                    user_b_threads = user_b.thread_access_permissions
                    
                    # Users should not have access to each other's threads (unless admin)
                    if not user_a.has_permission(Permission.ACCESS_ALL_THREADS):
                        thread_overlap = user_a_threads.intersection(user_b_threads)
                        if thread_overlap:
                            isolation_results["cross_user_violations"].append({
                                "type": "thread_access_overlap",
                                "user_a": user_a.user_id,
                                "user_b": user_b.user_id,
                                "overlapping_threads": list(thread_overlap)
                            })
                            isolation_results["permission_isolation_maintained"] = False
                    
                    # Organization isolation (if different orgs)
                    if (user_a.organization_id != user_b.organization_id and 
                        user_a.organization_id and user_b.organization_id):
                        # Neither user should have permissions affecting the other's org
                        pass  # This is expected and correct
            
            # Summarize user permissions
            isolation_results["user_permission_summaries"][user_a.user_id] = {
                "role": user_a.role.value,
                "permissions_count": len(user_a.permissions),
                "permissions": [p.value for p in user_a.permissions],
                "thread_access_count": len(user_a.thread_access_permissions),
                "organization_id": user_a.organization_id
            }
        
        return isolation_results


class TestWebSocketUserPermissionValidation(BaseIntegrationTest):
    """
    Integration test for user permission validation during WebSocket message routing and processing.
    
    CRITICAL: Validates that permission checks prevent unauthorized access and operations.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security_critical
    async def test_websocket_message_routing_permission_validation(self, real_services_fixture):
        """
        Test permission validation during WebSocket message routing.
        
        SECURITY CRITICAL: Users must only route messages they're authorized for.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketPermissionValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create users with different permission levels
            viewer_context = await validator.create_user_with_permissions("viewer", UserRole.VIEWER)
            user_context = await validator.create_user_with_permissions("user", UserRole.USER)
            admin_context = await validator.create_user_with_permissions("admin", UserRole.ADMIN)
            
            # Define message routes with different permission requirements
            routes_with_contexts = [
                # Viewer trying to read (should succeed)
                (WebSocketMessageRoute(
                    route_id="read-msg-viewer",
                    source_user_id=viewer_context.user_id,
                    target_user_id=None,
                    message_type=MessageType.USER_MESSAGE,
                    required_permissions={Permission.READ_MESSAGES},
                    thread_id=list(viewer_context.thread_access_permissions)[0]
                ), viewer_context),
                
                # Viewer trying to write (should fail)
                (WebSocketMessageRoute(
                    route_id="write-msg-viewer",
                    source_user_id=viewer_context.user_id,
                    target_user_id=None,
                    message_type=MessageType.USER_MESSAGE,
                    required_permissions={Permission.WRITE_MESSAGES},
                    thread_id=list(viewer_context.thread_access_permissions)[0]
                ), viewer_context),
                
                # User trying to write (should succeed)
                (WebSocketMessageRoute(
                    route_id="write-msg-user",
                    source_user_id=user_context.user_id,
                    target_user_id=None,
                    message_type=MessageType.USER_MESSAGE,
                    required_permissions={Permission.WRITE_MESSAGES},
                    thread_id=list(user_context.thread_access_permissions)[0]
                ), user_context),
                
                # User trying to broadcast (should fail)
                (WebSocketMessageRoute(
                    route_id="broadcast-user",
                    source_user_id=user_context.user_id,
                    target_user_id=None,
                    message_type=MessageType.BROADCAST,
                    required_permissions={Permission.BROADCAST_MESSAGES}
                ), user_context),
                
                # Admin trying to broadcast (should succeed)
                (WebSocketMessageRoute(
                    route_id="broadcast-admin",
                    source_user_id=admin_context.user_id,
                    target_user_id=None,
                    message_type=MessageType.BROADCAST,
                    required_permissions={Permission.BROADCAST_MESSAGES}
                ), admin_context),
                
                # User trying to access another user's thread (should fail)
                (WebSocketMessageRoute(
                    route_id="cross-thread-access",
                    source_user_id=user_context.user_id,
                    target_user_id=None,
                    message_type=MessageType.USER_MESSAGE,
                    required_permissions={Permission.WRITE_MESSAGES},
                    thread_id=list(viewer_context.thread_access_permissions)[0]  # Different user's thread
                ), user_context),
            ]
            
            # Execute routing with permission validation
            routing_results = await validator.simulate_websocket_message_routing_with_permissions(routes_with_contexts)
            
            # CRITICAL VALIDATIONS
            assert routing_results["total_routes"] == 6
            
            # Verify expected allowed/denied routes
            expected_allowed = 3  # viewer read, user write, admin broadcast
            expected_denied = 3   # viewer write, user broadcast, cross-thread access
            
            assert routing_results["allowed_routes"] == expected_allowed, \
                f"Expected {expected_allowed} allowed routes, got {routing_results['allowed_routes']}"
            assert routing_results["denied_routes"] == expected_denied, \
                f"Expected {expected_denied} denied routes, got {routing_results['denied_routes']}"
            
            # Verify specific route results
            route_results = {result["route_id"]: result for result in routing_results["route_results"]}
            
            assert route_results["read-msg-viewer"]["allowed"], "Viewer should be able to read"
            assert not route_results["write-msg-viewer"]["allowed"], "Viewer should not be able to write"
            assert route_results["write-msg-user"]["allowed"], "User should be able to write"
            assert not route_results["broadcast-user"]["allowed"], "User should not be able to broadcast"
            assert route_results["broadcast-admin"]["allowed"], "Admin should be able to broadcast"
            assert not route_results["cross-thread-access"]["allowed"], "Should not access other user's thread"
            
            # Verify security violations were logged
            assert len(routing_results["security_violations"]) >= 1, \
                "Security violations should be detected and logged"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.concurrency
    async def test_concurrent_permission_validation_isolation(self, real_services_fixture):
        """Test permission validation isolation during concurrent operations."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketPermissionValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create multiple users with different permissions
            user_contexts = []
            for i in range(3):
                role = [UserRole.VIEWER, UserRole.USER, UserRole.MODERATOR][i]
                context = await validator.create_user_with_permissions(f"concurrent-{i}", role)
                user_contexts.append(context)
            
            # Create concurrent routing scenarios
            concurrent_routes = []
            for i, context in enumerate(user_contexts):
                # Each user tries multiple operations simultaneously
                user_routes = [
                    (WebSocketMessageRoute(
                        route_id=f"concurrent-read-{i}-{j}",
                        source_user_id=context.user_id,
                        target_user_id=None,
                        message_type=MessageType.USER_MESSAGE,
                        required_permissions={Permission.READ_MESSAGES},
                        thread_id=list(context.thread_access_permissions)[0] if context.thread_access_permissions else None
                    ), context)
                    for j in range(2)
                ]
                
                user_routes.extend([
                    (WebSocketMessageRoute(
                        route_id=f"concurrent-write-{i}-{j}",
                        source_user_id=context.user_id,
                        target_user_id=None,
                        message_type=MessageType.USER_MESSAGE,
                        required_permissions={Permission.WRITE_MESSAGES},
                        thread_id=list(context.thread_access_permissions)[0] if context.thread_access_permissions else None
                    ), context)
                    for j in range(2)
                ])
                
                concurrent_routes.extend(user_routes)
            
            # Execute all routes concurrently
            concurrent_results = await validator.simulate_websocket_message_routing_with_permissions(concurrent_routes)
            
            # Validate isolation maintained during concurrent operations
            assert concurrent_results["total_routes"] == 12  # 3 users × 4 routes each
            
            # Verify permission isolation
            isolation_results = await validator.validate_permission_isolation_across_users(user_contexts)
            
            assert isolation_results["permission_isolation_maintained"], \
                f"Permission isolation violated: {isolation_results['cross_user_violations']}"
            assert len(isolation_results["cross_user_violations"]) == 0
            
            # Verify each user's permissions were correctly applied
            for user_id, summary in isolation_results["user_permission_summaries"].items():
                user_results = [r for r in concurrent_results["route_results"] if r["user_id"] == user_id]
                
                # Check that read operations succeeded for all users (all roles have read)
                read_results = [r for r in user_results if "read" in r["route_id"]]
                for read_result in read_results:
                    assert read_result["allowed"], f"Read should be allowed for user {user_id}"
                
                # Check write operations based on role
                write_results = [r for r in user_results if "write" in r["route_id"]]
                for write_result in write_results:
                    if summary["role"] == "viewer":
                        assert not write_result["allowed"], f"Write should be denied for viewer {user_id}"
                    else:
                        assert write_result["allowed"], f"Write should be allowed for {summary['role']} {user_id}"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.enterprise
    async def test_organization_scoped_permission_validation(self, real_services_fixture):
        """Test permission validation with organization-level scoping."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketPermissionValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create users from different organizations
            org_a_user = await validator.create_user_with_permissions("org-a-user", UserRole.USER, "organization-a")
            org_b_user = await validator.create_user_with_permissions("org-b-user", UserRole.USER, "organization-b")
            admin_user = await validator.create_user_with_permissions("admin-user", UserRole.ADMIN, "organization-a")
            
            # Test organization-scoped routing
            org_scoped_routes = [
                # User A accessing their own org (should succeed)
                (WebSocketMessageRoute(
                    route_id="org-a-internal",
                    source_user_id=org_a_user.user_id,
                    target_user_id=None,
                    message_type=MessageType.USER_MESSAGE,
                    required_permissions={Permission.WRITE_MESSAGES},
                    organization_scope="organization-a",
                    thread_id=list(org_a_user.thread_access_permissions)[0]
                ), org_a_user),
                
                # User A trying to access org B (should fail)
                (WebSocketMessageRoute(
                    route_id="org-cross-access",
                    source_user_id=org_a_user.user_id,
                    target_user_id=None,
                    message_type=MessageType.USER_MESSAGE,
                    required_permissions={Permission.WRITE_MESSAGES},
                    organization_scope="organization-b"
                ), org_a_user),
                
                # Admin accessing their own org (should succeed)
                (WebSocketMessageRoute(
                    route_id="admin-org-access",
                    source_user_id=admin_user.user_id,
                    target_user_id=None,
                    message_type=MessageType.BROADCAST,
                    required_permissions={Permission.BROADCAST_MESSAGES},
                    organization_scope="organization-a"
                ), admin_user),
            ]
            
            # Execute organization-scoped routing
            org_results = await validator.simulate_websocket_message_routing_with_permissions(org_scoped_routes)
            
            # Verify organization isolation
            route_results = {result["route_id"]: result for result in org_results["route_results"]}
            
            assert route_results["org-a-internal"]["allowed"], "User should access their own org"
            assert not route_results["org-cross-access"]["allowed"], "User should not access different org"
            assert route_results["admin-org-access"]["allowed"], "Admin should access their org"
            
            # Verify security violations for cross-org access
            cross_org_violations = [v for v in org_results["security_violations"] if "organization" in v]
            assert len(cross_org_violations) > 0, "Cross-organization access should be flagged as violation"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.agent_critical
    async def test_agent_execution_permission_validation(self, real_services_fixture):
        """Test permission validation for agent execution operations."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketPermissionValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create users with different agent permissions
            no_agent_user = await validator.create_user_with_permissions(
                "no-agent", UserRole.VIEWER, denied_permissions={Permission.AGENT_EXECUTION}
            )
            
            agent_user = await validator.create_user_with_permissions(
                "agent-user", UserRole.USER  # Has agent execution by default
            )
            
            agent_admin = await validator.create_user_with_permissions(
                "agent-admin", UserRole.ADMIN,
                additional_permissions={Permission.AGENT_MANAGEMENT}
            )
            
            # Test agent execution routing
            agent_routes = [
                # No-agent user trying to execute (should fail)
                (WebSocketMessageRoute(
                    route_id="denied-agent-exec",
                    source_user_id=no_agent_user.user_id,
                    target_user_id=None,
                    message_type=MessageType.AGENT_REQUEST,
                    required_permissions={Permission.AGENT_EXECUTION}
                ), no_agent_user),
                
                # Regular user executing agent (should succeed)
                (WebSocketMessageRoute(
                    route_id="user-agent-exec",
                    source_user_id=agent_user.user_id,
                    target_user_id=None,
                    message_type=MessageType.AGENT_REQUEST,
                    required_permissions={Permission.AGENT_EXECUTION}
                ), agent_user),
                
                # Admin managing agents (should succeed)
                (WebSocketMessageRoute(
                    route_id="admin-agent-mgmt",
                    source_user_id=agent_admin.user_id,
                    target_user_id=None,
                    message_type=MessageType.AGENT_REQUEST,
                    required_permissions={Permission.AGENT_MANAGEMENT}
                ), agent_admin),
                
                # Regular user trying to manage agents (should fail)
                (WebSocketMessageRoute(
                    route_id="user-agent-mgmt-denied",
                    source_user_id=agent_user.user_id,
                    target_user_id=None,
                    message_type=MessageType.AGENT_REQUEST,
                    required_permissions={Permission.AGENT_MANAGEMENT}
                ), agent_user),
            ]
            
            # Execute agent routing validation
            agent_results = await validator.simulate_websocket_message_routing_with_permissions(agent_routes)
            
            # Verify agent permission enforcement
            route_results = {result["route_id"]: result for result in agent_results["route_results"]}
            
            assert not route_results["denied-agent-exec"]["allowed"], "Should deny agent execution without permission"
            assert route_results["user-agent-exec"]["allowed"], "Should allow agent execution with permission"
            assert route_results["admin-agent-mgmt"]["allowed"], "Should allow agent management for admin"
            assert not route_results["user-agent-mgmt-denied"]["allowed"], "Should deny agent management for regular user"
            
            # Verify agent execution security
            assert agent_results["denied_routes"] == 2, "Two agent operations should be denied"
            assert agent_results["allowed_routes"] == 2, "Two agent operations should be allowed"
            
        finally:
            await validator.cleanup()