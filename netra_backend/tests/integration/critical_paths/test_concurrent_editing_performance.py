"""Concurrent Editing and Performance Critical Path Tests

Business Value Justification (BVJ):
- Segment: Mid to Enterprise (collaborative editing)
- Business Goal: Prevent data conflicts and ensure responsiveness
- Value Impact: Real-time collaboration efficiency, user experience
- Strategic Impact: Platform reliability and enterprise feature stability

Critical Path: Lock acquisition -> Conflict prevention -> Performance validation
Coverage: Concurrent editing protection, performance benchmarks, audit trails
"""

import pytest
import asyncio
import time
import uuid
from netra_backend.tests.integration.test_helpers.team_collaboration_base import (
    TeamCollaborationManager, TeamRole, PermissionType, 
    assert_performance_benchmark, validate_audit_trail
)


@pytest.fixture
async def collaboration_workspace():
    """Create team with shared workspace for concurrent editing tests."""
    manager = TeamCollaborationManager()
    owner_id = f"user_{uuid.uuid4().hex[:8]}"
    team = await manager.create_team(owner_id, "Concurrent Test Team", "enterprise")
    
    # Add multiple members
    user_ids = []
    for i in range(4):
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        invitation = await manager.invite_user(team.team_id, owner_id, f"user{i}@test.com", TeamRole.MEMBER)
        await manager.accept_invitation(invitation["token"], user_id)
        user_ids.append(user_id)
    
    # Create shared workspace
    workspace = await manager.create_workspace(team.team_id, owner_id, "Collaboration Workspace")
    
    # Share with all members
    for user_id in user_ids:
        await manager.share_resource(
            team.team_id, owner_id, workspace.workspace_id,
            user_id, {PermissionType.READ, PermissionType.WRITE}
        )
    
    return {
        "manager": manager,
        "team": team,
        "workspace": workspace,
        "owner_id": owner_id,
        "user_ids": user_ids
    }


class TestConcurrentEditingPerformance:
    """Critical path tests for concurrent editing and performance validation."""
    
    @pytest.mark.asyncio
    async def test_exclusive_edit_lock_acquisition(self, collaboration_workspace):
        """Test exclusive edit lock acquisition and release."""
        test_data = collaboration_workspace
        manager = test_data["manager"]
        team = test_data["team"]
        workspace = test_data["workspace"]
        user_ids = test_data["user_ids"]
        
        # First user acquires edit lock
        lock_acquired = await manager.acquire_edit_lock(
            team.team_id, user_ids[0], workspace.workspace_id
        )
        assert lock_acquired, "First user should acquire lock successfully"
        
        # Second user attempts to acquire lock (should fail)
        lock_blocked = await manager.acquire_edit_lock(
            team.team_id, user_ids[1], workspace.workspace_id
        )
        assert not lock_blocked, "Second user should be blocked from acquiring lock"
        
        # First user can extend their lock
        lock_extended = await manager.acquire_edit_lock(
            team.team_id, user_ids[0], workspace.workspace_id
        )
        assert lock_extended, "Original user should be able to extend lock"
        
        # First user releases lock
        lock_released = await manager.release_edit_lock(
            team.team_id, user_ids[0], workspace.workspace_id
        )
        assert lock_released, "Lock should be released successfully"
        
        # Second user can now acquire lock
        lock_acquired_after = await manager.acquire_edit_lock(
            team.team_id, user_ids[1], workspace.workspace_id
        )
        assert lock_acquired_after, "Second user should acquire lock after release"

    @pytest.mark.asyncio
    async def test_concurrent_lock_contention(self, collaboration_workspace):
        """Test lock contention with multiple concurrent users."""
        test_data = collaboration_workspace
        manager = test_data["manager"]
        team = test_data["team"]
        workspace = test_data["workspace"]
        user_ids = test_data["user_ids"]
        
        # Track lock acquisition results
        lock_results = {}
        
        async def attempt_lock(user_id: str, delay: float = 0):
            """Attempt to acquire lock with optional delay."""
            if delay > 0:
                await asyncio.sleep(delay)
            
            try:
                result = await manager.acquire_edit_lock(
                    team.team_id, user_id, workspace.workspace_id
                )
                lock_results[user_id] = result
            except Exception as e:
                lock_results[user_id] = f"error: {e}"
        
        # Launch concurrent lock attempts
        tasks = [
            attempt_lock(user_ids[0]),  # Immediate
            attempt_lock(user_ids[1], 0.1),  # Small delay
            attempt_lock(user_ids[2], 0.2),  # Larger delay
            attempt_lock(user_ids[3], 0.3),  # Largest delay
        ]
        
        await asyncio.gather(*tasks)
        
        # Validate only one lock succeeded
        successful_locks = [user_id for user_id, result in lock_results.items() if result is True]
        assert len(successful_locks) == 1, f"Expected exactly 1 successful lock, got {len(successful_locks)}"
        
        # Validate others were properly blocked
        blocked_locks = [user_id for user_id, result in lock_results.items() if result is False]
        assert len(blocked_locks) == 3, f"Expected 3 blocked locks, got {len(blocked_locks)}"

    @pytest.mark.asyncio
    async def test_lock_expiration_and_takeover(self, collaboration_workspace):
        """Test lock expiration and automatic takeover."""
        test_data = collaboration_workspace
        manager = test_data["manager"]
        team = test_data["team"]
        workspace = test_data["workspace"]
        user_ids = test_data["user_ids"]
        
        # First user acquires lock
        await manager.acquire_edit_lock(team.team_id, user_ids[0], workspace.workspace_id)
        
        # Manually expire the lock for testing
        lock_key = f"{team.team_id}:{workspace.workspace_id}"
        if lock_key in manager.concurrent_locks:
            lock_info = manager.concurrent_locks[lock_key]
            # Set expiration to past
            from datetime import datetime, timezone, timedelta
            lock_info["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)
        
        # Second user should be able to take over expired lock
        lock_takeover = await manager.acquire_edit_lock(
            team.team_id, user_ids[1], workspace.workspace_id
        )
        assert lock_takeover, "Second user should take over expired lock"
        
        # Verify lock is now held by second user
        assert manager.concurrent_locks[lock_key]["user_id"] == user_ids[1]

    @pytest.mark.asyncio
    async def test_permission_validation_for_locks(self, collaboration_workspace):
        """Test permission validation during lock operations."""
        test_data = collaboration_workspace
        manager = test_data["manager"]
        team = test_data["team"]
        workspace = test_data["workspace"]
        owner_id = test_data["owner_id"]
        
        # Add viewer without write permission
        viewer_id = f"user_{uuid.uuid4().hex[:8]}"
        viewer_invitation = await manager.invite_user(team.team_id, owner_id, "viewer@test.com", TeamRole.VIEWER)
        await manager.accept_invitation(viewer_invitation["token"], viewer_id)
        
        # Viewer cannot acquire edit lock (no write permission)
        with pytest.raises(PermissionError, match="Insufficient permissions to edit resource"):
            await manager.acquire_edit_lock(team.team_id, viewer_id, workspace.workspace_id)
        
        # Member with write permission can acquire lock
        member_id = test_data["user_ids"][0]
        lock_acquired = await manager.acquire_edit_lock(team.team_id, member_id, workspace.workspace_id)
        assert lock_acquired, "Member with write permission should acquire lock"

    @pytest.mark.asyncio
    async def test_permission_check_performance_benchmarks(self, collaboration_workspace):
        """Test permission check performance meets requirements."""
        test_data = collaboration_workspace
        manager = test_data["manager"]
        team = test_data["team"]
        workspace = test_data["workspace"]
        user_id = test_data["user_ids"][0]
        
        # Benchmark basic permission checks
        avg_time = assert_performance_benchmark(
            manager, team.team_id, user_id, iterations=100, max_avg_ms=50
        )
        
        # Benchmark resource-specific permission checks
        start_time = time.time()
        for _ in range(50):
            await manager.check_permission(
                team.team_id, user_id, PermissionType.WRITE, workspace.workspace_id
            )
        total_time = (time.time() - start_time) * 1000
        avg_resource_time = total_time / 50
        
        assert avg_resource_time < 75, f"Resource permission check avg {avg_resource_time}ms exceeds 75ms"

    @pytest.mark.asyncio
    async def test_high_volume_permission_validation(self, collaboration_workspace):
        """Test permission system under high volume load."""
        test_data = collaboration_workspace
        manager = test_data["manager"]
        team = test_data["team"]
        user_ids = test_data["user_ids"]
        
        # Simulate high volume of permission checks
        permission_types = list(PermissionType)
        
        async def permission_check_batch(user_id: str, batch_size: int = 25):
            """Perform batch of permission checks."""
            for i in range(batch_size):
                permission = permission_types[i % len(permission_types)]
                await manager.check_permission(team.team_id, user_id, permission)
        
        # Run concurrent permission check batches
        start_time = time.time()
        tasks = [permission_check_batch(user_id) for user_id in user_ids]
        await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000
        
        # Validate high volume performance
        total_checks = len(user_ids) * 25
        avg_time_per_check = total_time / total_checks
        assert avg_time_per_check < 10, f"High volume avg {avg_time_per_check}ms exceeds 10ms per check"

    @pytest.mark.asyncio
    async def test_concurrent_workspace_operations(self, collaboration_workspace):
        """Test concurrent workspace operations without conflicts."""
        test_data = collaboration_workspace
        manager = test_data["manager"]
        team = test_data["team"]
        owner_id = test_data["owner_id"]
        user_ids = test_data["user_ids"]
        
        # Track operation results
        operation_results = {}
        
        async def create_workspace_concurrent(user_id: str, name: str):
            """Create workspace concurrently."""
            try:
                workspace = await manager.create_workspace(team.team_id, user_id, name)
                operation_results[f"create_{user_id}"] = workspace.workspace_id
            except Exception as e:
                operation_results[f"create_{user_id}"] = f"error: {e}"
        
        async def share_resource_concurrent(user_id: str, target_user: str):
            """Share existing resource concurrently."""
            try:
                workspace_id = test_data["workspace"].workspace_id
                result = await manager.share_resource(
                    team.team_id, owner_id, workspace_id,
                    target_user, {PermissionType.READ}
                )
                operation_results[f"share_{user_id}"] = result
            except Exception as e:
                operation_results[f"share_{user_id}"] = f"error: {e}"
        
        # Run concurrent operations
        tasks = []
        
        # Concurrent workspace creation
        for i, user_id in enumerate(user_ids[:2]):
            tasks.append(create_workspace_concurrent(user_id, f"Concurrent Workspace {i}"))
        
        # Concurrent sharing operations
        for i, user_id in enumerate(user_ids[2:]):
            tasks.append(share_resource_concurrent(user_id, f"share_target_{i}"))
        
        await asyncio.gather(*tasks)
        
        # Validate all operations completed
        assert len(operation_results) == 4, f"Expected 4 operations, got {len(operation_results)}"
        
        # Validate workspace creations succeeded
        created_workspaces = [result for key, result in operation_results.items() 
                            if key.startswith("create_") and not str(result).startswith("error")]
        assert len(created_workspaces) == 2, f"Expected 2 workspace creations, got {len(created_workspaces)}"

    @pytest.mark.asyncio
    async def test_audit_trail_for_concurrent_operations(self, collaboration_workspace):
        """Test audit trail captures concurrent operations correctly."""
        test_data = collaboration_workspace
        manager = test_data["manager"]
        team = test_data["team"]
        workspace = test_data["workspace"]
        user_ids = test_data["user_ids"]
        
        # Record initial audit state
        initial_audit_count = len([log for log in manager.audit_log if log["action"] != "permission_check"])
        
        # Perform concurrent lock operations
        tasks = []
        
        # User 1 acquires lock
        tasks.append(manager.acquire_edit_lock(team.team_id, user_ids[0], workspace.workspace_id))
        
        # User 2 attempts lock (will fail)
        tasks.append(manager.acquire_edit_lock(team.team_id, user_ids[1], workspace.workspace_id))
        
        # Wait a bit, then user 1 releases
        async def delayed_release():
            await asyncio.sleep(0.1)
            return await manager.release_edit_lock(team.team_id, user_ids[0], workspace.workspace_id)
        
        tasks.append(delayed_release())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # User 2 now acquires lock
        await manager.acquire_edit_lock(team.team_id, user_ids[1], workspace.workspace_id)
        
        # Validate audit trail captured operations
        expected_actions = ["edit_lock_acquired", "edit_lock_released", "edit_lock_acquired"]
        validate_audit_trail(manager, expected_actions)
        
        # Verify audit count increased appropriately
        final_audit_count = len([log for log in manager.audit_log if log["action"] != "permission_check"])
        assert final_audit_count >= initial_audit_count + 3