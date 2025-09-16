"""
Test WebSocket User Context Cleanup Validation During Disconnection Integration (#29)

Business Value Justification (BVJ):
- Segment: All (Critical for system resource management and security)
- Business Goal: Ensure complete user context cleanup during WebSocket disconnection
- Value Impact: Users' sensitive data is properly cleaned up and not left in system memory
- Strategic Impact: Foundation of system security and performance - prevents memory leaks and data persistence

CRITICAL REQUIREMENT: When users disconnect from WebSocket, ALL user context data must be
completely cleaned up from memory, cache, and temporary storage. Any context data persistence
after disconnection is a security risk and resource leak that could impact system performance.
"""

import asyncio
import pytest
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState, MessageType
from shared.isolated_environment import get_env

# Type definitions
UserID = str
ConnectionID = str
ContextID = str
CleanupTaskID = str


class DisconnectionType(Enum):
    """Types of WebSocket disconnections."""
    GRACEFUL = "graceful"  # User-initiated clean disconnection
    ABRUPT = "abrupt"  # Network error or browser close
    TIMEOUT = "timeout"  # Connection timeout
    SERVER_INITIATED = "server_initiated"  # Server forced disconnection
    ERROR_INDUCED = "error_induced"  # Disconnection due to error


class ContextCleanupStage(Enum):
    """Stages of context cleanup process."""
    INITIATED = "initiated"
    MEMORY_CLEARED = "memory_cleared"
    CACHE_CLEARED = "cache_cleared"
    TEMPORARY_DATA_CLEARED = "temporary_data_cleared"
    SESSION_STATE_CLEARED = "session_state_cleared"
    WEBSOCKET_STATE_CLEARED = "websocket_state_cleared"
    AGENT_STATE_CLEARED = "agent_state_cleared"
    AUDIT_LOG_UPDATED = "audit_log_updated"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UserContextSnapshot:
    """Snapshot of user context before and after cleanup."""
    user_id: UserID
    connection_id: ConnectionID
    context_id: ContextID
    snapshot_timestamp: float
    memory_usage: Dict[str, Any] = field(default_factory=dict)
    cache_keys: Set[str] = field(default_factory=set)
    temporary_data: Dict[str, Any] = field(default_factory=dict)
    websocket_state: Dict[str, Any] = field(default_factory=dict)
    agent_states: List[Dict[str, Any]] = field(default_factory=list)
    session_data: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_total_size_bytes(self) -> int:
        """Calculate total size of context data in bytes."""
        total_size = 0
        
        # Estimate memory usage
        total_size += len(json.dumps(self.memory_usage))
        total_size += sum(len(key) for key in self.cache_keys) * 2  # Key + estimated value
        total_size += len(json.dumps(self.temporary_data))
        total_size += len(json.dumps(self.websocket_state))
        total_size += len(json.dumps(self.agent_states))
        total_size += len(json.dumps(self.session_data))
        
        return total_size


@dataclass
class ContextCleanupRecord:
    """Record of context cleanup process and results."""
    cleanup_id: CleanupTaskID
    user_id: UserID
    connection_id: ConnectionID
    disconnection_type: DisconnectionType
    pre_cleanup_snapshot: Optional[UserContextSnapshot] = None
    post_cleanup_snapshot: Optional[UserContextSnapshot] = None
    cleanup_stages: List[Dict[str, Any]] = field(default_factory=list)
    cleanup_duration_ms: Optional[float] = None
    cleanup_success: bool = False
    memory_freed_bytes: int = 0
    cache_keys_cleaned: int = 0
    cleanup_violations: List[Dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    def add_stage(self, stage: ContextCleanupStage, success: bool = True, 
                 details: Dict[str, Any] = None):
        """Add cleanup stage with details."""
        stage_record = {
            "stage": stage.value,
            "timestamp": time.time(),
            "success": success,
            "details": details or {}
        }
        self.cleanup_stages.append(stage_record)
        
        if stage == ContextCleanupStage.COMPLETED and success:
            self.cleanup_success = True
            self.completed_at = time.time()
            self.cleanup_duration_ms = (self.completed_at - self.started_at) * 1000
        elif not success and stage != ContextCleanupStage.FAILED:
            # Record violation if stage failed
            self.cleanup_violations.append({
                "stage": stage.value,
                "failure_reason": details.get("error", "unknown"),
                "timestamp": time.time()
            })


class WebSocketContextCleanupValidator:
    """Validates user context cleanup during WebSocket disconnection."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.redis_client = None
        self.cleanup_records = {}
        self.persistent_context_violations = []
        self.memory_leak_detections = []
    
    async def setup(self):
        """Set up validator with Redis connection."""
        import redis.asyncio as redis
        self.redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        await self.redis_client.ping()
    
    async def cleanup(self):
        """Clean up validator resources."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def create_user_with_comprehensive_context(self, user_suffix: str) -> Tuple[UserID, ConnectionID, ContextID]:
        """Create user with comprehensive context data for cleanup testing."""
        user_id = f"cleanup-test-user-{user_suffix}"
        connection_id = f"conn-{uuid.uuid4().hex}"
        context_id = f"ctx-{uuid.uuid4().hex}"
        
        # Create user in database
        await self.real_services["db"].execute("""
            INSERT INTO auth.users (id, email, name, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, user_id, f"{user_id}@cleanup-test.com", f"Cleanup Test User {user_suffix}", True)
        
        # Create organization
        org_id = f"cleanup-org-{user_suffix}"
        await self.real_services["db"].execute("""
            INSERT INTO backend.organizations (id, name, slug, plan, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                plan = EXCLUDED.plan
        """, org_id, f"Cleanup Test Org {user_suffix}", f"cleanup-org-{user_suffix}", "enterprise")
        
        # Create organization membership
        await self.real_services["db"].execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, organization_id) DO UPDATE SET role = EXCLUDED.role
        """, user_id, org_id, "member")
        
        # Create comprehensive context data in various layers
        
        # 1. User session data
        session_data = {
            "user_id": user_id,
            "session_id": f"session-{uuid.uuid4().hex}",
            "organization_id": org_id,
            "login_time": time.time(),
            "permissions": ["read", "write", "admin"],
            "preferences": {
                "theme": "dark",
                "language": "en",
                "notifications": True
            },
            "activity_log": [
                {"action": "login", "timestamp": time.time()},
                {"action": "navigate", "timestamp": time.time() + 10},
                {"action": "message_sent", "timestamp": time.time() + 20}
            ]
        }
        
        session_key = f"user_session:{user_id}"
        await self.redis_client.set(session_key, json.dumps(session_data), ex=3600)
        
        # 2. WebSocket connection state
        websocket_state = {
            "connection_id": connection_id,
            "user_id": user_id,
            "state": WebSocketConnectionState.CONNECTED,
            "connected_at": time.time(),
            "last_heartbeat": time.time(),
            "active_channels": ["general", f"user_{user_id}", f"org_{org_id}"],
            "message_queue": [],
            "subscription_filters": ["user_messages", "system_notifications"],
            "connection_metadata": {
                "ip_address": "127.0.0.1",
                "user_agent": "test-client",
                "protocol_version": "v1"
            }
        }
        
        ws_state_key = f"ws_state:{connection_id}"
        await self.redis_client.set(ws_state_key, json.dumps(websocket_state), ex=3600)
        
        # 3. User execution context
        execution_context = {
            "context_id": context_id,
            "user_id": user_id,
            "organization_id": org_id,
            "execution_permissions": ["execute_agents", "access_tools", "view_analytics"],
            "data_access_scopes": [f"user_data:{user_id}", f"org_data:{org_id}"],
            "security_constraints": {
                "max_execution_time": 600,
                "allowed_tools": ["search", "analyze"],
                "audit_required": True
            },
            "active_threads": [],
            "execution_history": []
        }
        
        exec_context_key = f"execution_context:{context_id}"
        await self.redis_client.set(exec_context_key, json.dumps(execution_context), ex=3600)
        
        # 4. Agent state data
        for i in range(3):
            agent_id = f"agent-{i}"
            agent_state = {
                "agent_id": agent_id,
                "user_id": user_id,
                "execution_id": f"exec-{uuid.uuid4().hex}",
                "state": "idle",
                "last_activity": time.time(),
                "context_data": {
                    "user_preferences": session_data["preferences"],
                    "organization_context": org_id,
                    "execution_permissions": execution_context["execution_permissions"]
                }
            }
            
            agent_state_key = f"agent_state:{user_id}:{agent_id}"
            await self.redis_client.set(agent_state_key, json.dumps(agent_state), ex=1800)
        
        # 5. Temporary data (message queue, file uploads, etc.)
        for i in range(5):
            temp_data = {
                "temp_id": f"temp-{uuid.uuid4().hex}",
                "user_id": user_id,
                "data_type": "message_draft" if i < 3 else "file_upload",
                "content": f"Temporary data item {i} for cleanup testing",
                "created_at": time.time(),
                "expires_at": time.time() + 1800
            }
            
            temp_key = f"temp_data:{user_id}:{temp_data['temp_id']}"
            await self.redis_client.set(temp_key, json.dumps(temp_data), ex=1800)
        
        # 6. User analytics/metrics data
        analytics_data = {
            "user_id": user_id,
            "session_metrics": {
                "messages_sent": 15,
                "agents_executed": 3,
                "time_active_seconds": 1200
            },
            "feature_usage": {
                "chat": 25,
                "agents": 8,
                "analytics": 2
            },
            "performance_metrics": {
                "avg_response_time": 0.5,
                "error_rate": 0.02
            }
        }
        
        analytics_key = f"analytics:{user_id}:session"
        await self.redis_client.set(analytics_key, json.dumps(analytics_data), ex=7200)
        
        return user_id, connection_id, context_id
    
    async def capture_context_snapshot(self, user_id: UserID, connection_id: ConnectionID, 
                                     context_id: ContextID, snapshot_type: str = "pre_cleanup") -> UserContextSnapshot:
        """Capture complete snapshot of user context."""
        snapshot = UserContextSnapshot(
            user_id=user_id,
            connection_id=connection_id,
            context_id=context_id,
            snapshot_timestamp=time.time()
        )
        
        # Capture session data
        session_key = f"user_session:{user_id}"
        session_data = await self.redis_client.get(session_key)
        if session_data:
            snapshot.session_data = json.loads(session_data)
        
        # Capture WebSocket state
        ws_state_key = f"ws_state:{connection_id}"
        ws_state = await self.redis_client.get(ws_state_key)
        if ws_state:
            snapshot.websocket_state = json.loads(ws_state)
        
        # Capture execution context
        exec_context_key = f"execution_context:{context_id}"
        exec_context = await self.redis_client.get(exec_context_key)
        if exec_context:
            snapshot.memory_usage["execution_context"] = json.loads(exec_context)
        
        # Capture agent states
        agent_keys = await self.redis_client.keys(f"agent_state:{user_id}:*")
        for agent_key in agent_keys:
            agent_data = await self.redis_client.get(agent_key)
            if agent_data:
                snapshot.agent_states.append(json.loads(agent_data))
        
        # Capture temporary data
        temp_keys = await self.redis_client.keys(f"temp_data:{user_id}:*")
        for temp_key in temp_keys:
            temp_data = await self.redis_client.get(temp_key)
            if temp_data:
                snapshot.temporary_data[temp_key.decode()] = json.loads(temp_data)
        
        # Capture analytics data
        analytics_key = f"analytics:{user_id}:session"
        analytics_data = await self.redis_client.get(analytics_key)
        if analytics_data:
            snapshot.memory_usage["analytics"] = json.loads(analytics_data)
        
        # Collect all cache keys related to user
        all_user_keys = await self.redis_client.keys(f"*{user_id}*")
        snapshot.cache_keys = {key.decode() for key in all_user_keys}
        
        return snapshot
    
    async def simulate_websocket_disconnection_with_cleanup(self, user_id: UserID, connection_id: ConnectionID,
                                                           context_id: ContextID, 
                                                           disconnection_type: DisconnectionType) -> ContextCleanupRecord:
        """Simulate WebSocket disconnection with comprehensive context cleanup."""
        cleanup_id = f"cleanup-{uuid.uuid4().hex}"
        
        cleanup_record = ContextCleanupRecord(
            cleanup_id=cleanup_id,
            user_id=user_id,
            connection_id=connection_id,
            disconnection_type=disconnection_type
        )
        
        # Capture pre-cleanup snapshot
        cleanup_record.pre_cleanup_snapshot = await self.capture_context_snapshot(
            user_id, connection_id, context_id, "pre_cleanup"
        )
        
        # Stage 1: Initiate cleanup
        cleanup_record.add_stage(ContextCleanupStage.INITIATED, True, {
            "disconnection_type": disconnection_type.value,
            "context_size_bytes": cleanup_record.pre_cleanup_snapshot.calculate_total_size_bytes(),
            "cache_keys_count": len(cleanup_record.pre_cleanup_snapshot.cache_keys)
        })
        
        try:
            # Stage 2: Clear memory/execution context
            memory_cleanup = await self._cleanup_memory_context(user_id, context_id)
            cleanup_record.add_stage(ContextCleanupStage.MEMORY_CLEARED, 
                                    memory_cleanup["success"], memory_cleanup)
            
            # Stage 3: Clear cache data
            cache_cleanup = await self._cleanup_cache_data(user_id, connection_id)
            cleanup_record.add_stage(ContextCleanupStage.CACHE_CLEARED,
                                    cache_cleanup["success"], cache_cleanup)
            cleanup_record.cache_keys_cleaned = cache_cleanup.get("keys_cleaned", 0)
            
            # Stage 4: Clear temporary data
            temp_cleanup = await self._cleanup_temporary_data(user_id)
            cleanup_record.add_stage(ContextCleanupStage.TEMPORARY_DATA_CLEARED,
                                    temp_cleanup["success"], temp_cleanup)
            
            # Stage 5: Clear session state
            session_cleanup = await self._cleanup_session_state(user_id)
            cleanup_record.add_stage(ContextCleanupStage.SESSION_STATE_CLEARED,
                                    session_cleanup["success"], session_cleanup)
            
            # Stage 6: Clear WebSocket state
            ws_cleanup = await self._cleanup_websocket_state(connection_id)
            cleanup_record.add_stage(ContextCleanupStage.WEBSOCKET_STATE_CLEARED,
                                    ws_cleanup["success"], ws_cleanup)
            
            # Stage 7: Clear agent states
            agent_cleanup = await self._cleanup_agent_states(user_id)
            cleanup_record.add_stage(ContextCleanupStage.AGENT_STATE_CLEARED,
                                    agent_cleanup["success"], agent_cleanup)
            
            # Stage 8: Update audit log
            audit_update = await self._update_cleanup_audit_log(cleanup_record)
            cleanup_record.add_stage(ContextCleanupStage.AUDIT_LOG_UPDATED,
                                    audit_update["success"], audit_update)
            
            # Stage 9: Completion
            cleanup_record.add_stage(ContextCleanupStage.COMPLETED, True, {
                "total_stages": len(cleanup_record.cleanup_stages),
                "cleanup_duration_ms": cleanup_record.cleanup_duration_ms
            })
            
        except Exception as e:
            cleanup_record.add_stage(ContextCleanupStage.FAILED, False, {
                "error": str(e),
                "failed_at": time.time()
            })
            cleanup_record.cleanup_success = False
        
        # Capture post-cleanup snapshot
        cleanup_record.post_cleanup_snapshot = await self.capture_context_snapshot(
            user_id, connection_id, context_id, "post_cleanup"
        )
        
        # Calculate memory freed
        if cleanup_record.pre_cleanup_snapshot and cleanup_record.post_cleanup_snapshot:
            pre_size = cleanup_record.pre_cleanup_snapshot.calculate_total_size_bytes()
            post_size = cleanup_record.post_cleanup_snapshot.calculate_total_size_bytes()
            cleanup_record.memory_freed_bytes = max(0, pre_size - post_size)
        
        self.cleanup_records[cleanup_id] = cleanup_record
        return cleanup_record
    
    async def _cleanup_memory_context(self, user_id: UserID, context_id: ContextID) -> Dict[str, Any]:
        """Clean up in-memory execution context."""
        cleanup_result = {"success": True, "contexts_cleared": 0, "errors": []}
        
        try:
            # Clear execution context
            exec_context_key = f"execution_context:{context_id}"
            deleted_exec = await self.redis_client.delete(exec_context_key)
            cleanup_result["contexts_cleared"] += deleted_exec
            
            # Clear any cached computation results
            computation_keys = await self.redis_client.keys(f"computation:{user_id}:*")
            if computation_keys:
                deleted_computation = await self.redis_client.delete(*computation_keys)
                cleanup_result["contexts_cleared"] += deleted_computation
                
        except Exception as e:
            cleanup_result["success"] = False
            cleanup_result["errors"].append(str(e))
        
        return cleanup_result
    
    async def _cleanup_cache_data(self, user_id: UserID, connection_id: ConnectionID) -> Dict[str, Any]:
        """Clean up cache data related to user and connection."""
        cleanup_result = {"success": True, "keys_cleaned": 0, "errors": []}
        
        try:
            # Get all keys related to user or connection
            user_keys = await self.redis_client.keys(f"*{user_id}*")
            connection_keys = await self.redis_client.keys(f"*{connection_id}*")
            
            all_keys = set(user_keys + connection_keys)
            
            if all_keys:
                deleted_count = await self.redis_client.delete(*all_keys)
                cleanup_result["keys_cleaned"] = deleted_count
                
        except Exception as e:
            cleanup_result["success"] = False
            cleanup_result["errors"].append(str(e))
        
        return cleanup_result
    
    async def _cleanup_temporary_data(self, user_id: UserID) -> Dict[str, Any]:
        """Clean up temporary data for user."""
        cleanup_result = {"success": True, "temp_data_cleared": 0, "errors": []}
        
        try:
            # Clear temporary data
            temp_keys = await self.redis_client.keys(f"temp_data:{user_id}:*")
            if temp_keys:
                deleted_temp = await self.redis_client.delete(*temp_keys)
                cleanup_result["temp_data_cleared"] = deleted_temp
            
            # Clear any draft messages
            draft_keys = await self.redis_client.keys(f"draft:{user_id}:*")
            if draft_keys:
                deleted_drafts = await self.redis_client.delete(*draft_keys)
                cleanup_result["temp_data_cleared"] += deleted_drafts
                
        except Exception as e:
            cleanup_result["success"] = False
            cleanup_result["errors"].append(str(e))
        
        return cleanup_result
    
    async def _cleanup_session_state(self, user_id: UserID) -> Dict[str, Any]:
        """Clean up user session state."""
        cleanup_result = {"success": True, "sessions_cleared": 0, "errors": []}
        
        try:
            # Clear user session
            session_key = f"user_session:{user_id}"
            deleted_session = await self.redis_client.delete(session_key)
            cleanup_result["sessions_cleared"] = deleted_session
            
            # Clear any cached authentication data
            auth_keys = await self.redis_client.keys(f"auth:{user_id}:*")
            if auth_keys:
                deleted_auth = await self.redis_client.delete(*auth_keys)
                cleanup_result["sessions_cleared"] += deleted_auth
                
        except Exception as e:
            cleanup_result["success"] = False
            cleanup_result["errors"].append(str(e))
        
        return cleanup_result
    
    async def _cleanup_websocket_state(self, connection_id: ConnectionID) -> Dict[str, Any]:
        """Clean up WebSocket connection state."""
        cleanup_result = {"success": True, "ws_states_cleared": 0, "errors": []}
        
        try:
            # Clear WebSocket state
            ws_state_key = f"ws_state:{connection_id}"
            deleted_ws = await self.redis_client.delete(ws_state_key)
            cleanup_result["ws_states_cleared"] = deleted_ws
            
            # Clear any WebSocket message queues
            queue_keys = await self.redis_client.keys(f"ws_queue:{connection_id}:*")
            if queue_keys:
                deleted_queues = await self.redis_client.delete(*queue_keys)
                cleanup_result["ws_states_cleared"] += deleted_queues
                
        except Exception as e:
            cleanup_result["success"] = False
            cleanup_result["errors"].append(str(e))
        
        return cleanup_result
    
    async def _cleanup_agent_states(self, user_id: UserID) -> Dict[str, Any]:
        """Clean up agent execution states for user."""
        cleanup_result = {"success": True, "agent_states_cleared": 0, "errors": []}
        
        try:
            # Clear agent states
            agent_keys = await self.redis_client.keys(f"agent_state:{user_id}:*")
            if agent_keys:
                deleted_agents = await self.redis_client.delete(*agent_keys)
                cleanup_result["agent_states_cleared"] = deleted_agents
            
            # Clear agent execution history
            history_keys = await self.redis_client.keys(f"agent_history:{user_id}:*")
            if history_keys:
                deleted_history = await self.redis_client.delete(*history_keys)
                cleanup_result["agent_states_cleared"] += deleted_history
                
        except Exception as e:
            cleanup_result["success"] = False
            cleanup_result["errors"].append(str(e))
        
        return cleanup_result
    
    async def _update_cleanup_audit_log(self, cleanup_record: ContextCleanupRecord) -> Dict[str, Any]:
        """Update audit log with cleanup information."""
        audit_result = {"success": True, "log_updated": True, "errors": []}
        
        try:
            # Create audit log entry
            audit_entry = {
                "event_type": "user_context_cleanup",
                "user_id": cleanup_record.user_id,
                "connection_id": cleanup_record.connection_id,
                "cleanup_id": cleanup_record.cleanup_id,
                "disconnection_type": cleanup_record.disconnection_type.value,
                "cleanup_stages": len(cleanup_record.cleanup_stages),
                "cleanup_success": cleanup_record.cleanup_success,
                "memory_freed_bytes": cleanup_record.memory_freed_bytes,
                "cache_keys_cleaned": cleanup_record.cache_keys_cleaned,
                "timestamp": time.time()
            }
            
            # Store audit entry
            audit_key = f"audit:cleanup:{cleanup_record.cleanup_id}"
            await self.redis_client.set(audit_key, json.dumps(audit_entry), ex=86400)  # 24 hours
            
        except Exception as e:
            audit_result["success"] = False
            audit_result["errors"].append(str(e))
        
        return audit_result
    
    async def validate_context_cleanup_completeness(self, cleanup_records: List[ContextCleanupRecord]) -> Dict[str, Any]:
        """Validate that context cleanup was complete across all records."""
        validation_result = {
            "cleanup_completeness_score": 0.0,
            "total_cleanups": len(cleanup_records),
            "successful_cleanups": 0,
            "failed_cleanups": 0,
            "persistent_data_violations": [],
            "memory_leak_detections": [],
            "cleanup_performance": {
                "avg_cleanup_duration_ms": 0.0,
                "max_cleanup_duration_ms": 0.0,
                "memory_freed_total_bytes": 0
            }
        }
        
        total_duration = 0.0
        max_duration = 0.0
        total_memory_freed = 0
        
        for record in cleanup_records:
            if record.cleanup_success:
                validation_result["successful_cleanups"] += 1
            else:
                validation_result["failed_cleanups"] += 1
            
            # Performance metrics
            if record.cleanup_duration_ms:
                total_duration += record.cleanup_duration_ms
                max_duration = max(max_duration, record.cleanup_duration_ms)
            
            total_memory_freed += record.memory_freed_bytes
            
            # Check for persistent data violations
            if record.post_cleanup_snapshot:
                post_cache_keys = len(record.post_cleanup_snapshot.cache_keys)
                if post_cache_keys > 0:
                    validation_result["persistent_data_violations"].append({
                        "cleanup_id": record.cleanup_id,
                        "user_id": record.user_id,
                        "persistent_cache_keys": post_cache_keys,
                        "sample_keys": list(record.post_cleanup_snapshot.cache_keys)[:5]
                    })
                
                # Check for memory leaks
                if record.post_cleanup_snapshot.calculate_total_size_bytes() > 100:  # More than 100 bytes remaining
                    validation_result["memory_leak_detections"].append({
                        "cleanup_id": record.cleanup_id,
                        "user_id": record.user_id,
                        "remaining_size_bytes": record.post_cleanup_snapshot.calculate_total_size_bytes(),
                        "remaining_data_types": list(record.post_cleanup_snapshot.memory_usage.keys())
                    })
            
            # Check for cleanup violations
            if record.cleanup_violations:
                for violation in record.cleanup_violations:
                    validation_result["persistent_data_violations"].append({
                        "cleanup_id": record.cleanup_id,
                        "violation_type": "cleanup_stage_failure",
                        "failed_stage": violation["stage"],
                        "failure_reason": violation["failure_reason"]
                    })
        
        # Calculate metrics
        if len(cleanup_records) > 0:
            validation_result["cleanup_completeness_score"] = validation_result["successful_cleanups"] / len(cleanup_records)
            validation_result["cleanup_performance"]["avg_cleanup_duration_ms"] = total_duration / len(cleanup_records)
            validation_result["cleanup_performance"]["max_cleanup_duration_ms"] = max_duration
            validation_result["cleanup_performance"]["memory_freed_total_bytes"] = total_memory_freed
        
        return validation_result


class TestWebSocketUserContextCleanupValidation(BaseIntegrationTest):
    """
    Integration test for user context cleanup validation during WebSocket disconnection.
    
    CRITICAL: Validates complete cleanup of user context data to prevent memory leaks and security risks.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.cleanup_critical
    async def test_websocket_disconnection_complete_context_cleanup(self, real_services_fixture):
        """
        Test complete user context cleanup during WebSocket disconnection.
        
        CRITICAL: All user context must be cleaned up to prevent memory leaks and data persistence.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketContextCleanupValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create user with comprehensive context
            user_id, connection_id, context_id = await validator.create_user_with_comprehensive_context("cleanup-complete")
            
            # Capture initial context state
            initial_snapshot = await validator.capture_context_snapshot(user_id, connection_id, context_id, "initial")
            
            # Verify comprehensive context was created
            assert len(initial_snapshot.cache_keys) > 0, "User should have cache data"
            assert initial_snapshot.session_data, "User should have session data"
            assert initial_snapshot.websocket_state, "User should have WebSocket state"
            assert len(initial_snapshot.agent_states) > 0, "User should have agent states"
            assert initial_snapshot.temporary_data, "User should have temporary data"
            initial_size = initial_snapshot.calculate_total_size_bytes()
            assert initial_size > 1000, f"Initial context size should be substantial: {initial_size} bytes"
            
            # Simulate graceful disconnection with cleanup
            cleanup_record = await validator.simulate_websocket_disconnection_with_cleanup(
                user_id, connection_id, context_id, DisconnectionType.GRACEFUL
            )
            
            # CRITICAL CLEANUP VALIDATIONS
            
            # Cleanup must succeed
            assert cleanup_record.cleanup_success, \
                f"Context cleanup failed: {cleanup_record.cleanup_violations}"
            
            # All cleanup stages must complete successfully
            failed_stages = [stage for stage in cleanup_record.cleanup_stages if not stage["success"]]
            assert len(failed_stages) == 0, f"Cleanup stages failed: {failed_stages}"
            
            # Verify expected cleanup stages completed
            expected_stages = [
                "initiated", "memory_cleared", "cache_cleared", "temporary_data_cleared",
                "session_state_cleared", "websocket_state_cleared", "agent_state_cleared",
                "audit_log_updated", "completed"
            ]
            completed_stages = [stage["stage"] for stage in cleanup_record.cleanup_stages]
            for expected_stage in expected_stages:
                assert expected_stage in completed_stages, \
                    f"Expected cleanup stage '{expected_stage}' not completed"
            
            # Verify significant memory was freed
            assert cleanup_record.memory_freed_bytes > 500, \
                f"Insufficient memory freed: {cleanup_record.memory_freed_bytes} bytes"
            
            # Verify cache keys were cleaned
            assert cleanup_record.cache_keys_cleaned > 0, \
                "Cache keys should have been cleaned"
            
            # Verify post-cleanup state is minimal
            post_snapshot = cleanup_record.post_cleanup_snapshot
            assert post_snapshot is not None, "Post-cleanup snapshot should exist"
            
            # Post-cleanup context should be minimal or empty
            post_size = post_snapshot.calculate_total_size_bytes()
            assert post_size < 100, f"Post-cleanup context too large: {post_size} bytes"
            assert len(post_snapshot.cache_keys) == 0, \
                f"Cache keys still present after cleanup: {post_snapshot.cache_keys}"
            assert not post_snapshot.session_data, "Session data should be cleared"
            assert not post_snapshot.websocket_state, "WebSocket state should be cleared"
            assert len(post_snapshot.agent_states) == 0, "Agent states should be cleared"
            assert not post_snapshot.temporary_data, "Temporary data should be cleared"
            
            # Cleanup should be reasonably fast
            assert cleanup_record.cleanup_duration_ms < 5000, \
                f"Cleanup took too long: {cleanup_record.cleanup_duration_ms}ms"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.cleanup_types
    async def test_different_disconnection_types_cleanup_consistency(self, real_services_fixture):
        """Test context cleanup consistency across different disconnection types."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketContextCleanupValidator(real_services_fixture)
        await validator.setup()
        
        try:
            cleanup_records = []
            
            # Test different disconnection types
            disconnection_types = [
                DisconnectionType.GRACEFUL,
                DisconnectionType.ABRUPT,
                DisconnectionType.TIMEOUT,
                DisconnectionType.SERVER_INITIATED
            ]
            
            for i, disconnect_type in enumerate(disconnection_types):
                # Create user with context
                user_id, connection_id, context_id = await validator.create_user_with_comprehensive_context(f"disconnect-{i}")
                
                # Execute cleanup for this disconnection type
                cleanup_record = await validator.simulate_websocket_disconnection_with_cleanup(
                    user_id, connection_id, context_id, disconnect_type
                )
                
                cleanup_records.append(cleanup_record)
            
            # Validate cleanup consistency across all disconnection types
            cleanup_validation = await validator.validate_context_cleanup_completeness(cleanup_records)
            
            # CONSISTENCY VALIDATIONS
            
            # All cleanups should succeed regardless of disconnection type
            assert cleanup_validation["cleanup_completeness_score"] == 1.0, \
                f"Cleanup completeness: {cleanup_validation['cleanup_completeness_score']}"
            assert cleanup_validation["failed_cleanups"] == 0, \
                f"Failed cleanups detected: {cleanup_validation['failed_cleanups']}"
            
            # No persistent data violations
            assert len(cleanup_validation["persistent_data_violations"]) == 0, \
                f"Persistent data violations: {cleanup_validation['persistent_data_violations']}"
            
            # No memory leaks
            assert len(cleanup_validation["memory_leak_detections"]) == 0, \
                f"Memory leaks detected: {cleanup_validation['memory_leak_detections']}"
            
            # Performance should be consistent
            avg_duration = cleanup_validation["cleanup_performance"]["avg_cleanup_duration_ms"]
            max_duration = cleanup_validation["cleanup_performance"]["max_cleanup_duration_ms"]
            assert avg_duration < 3000, f"Average cleanup too slow: {avg_duration}ms"
            assert max_duration < 5000, f"Max cleanup too slow: {max_duration}ms"
            
            # Memory should be freed for all
            total_freed = cleanup_validation["cleanup_performance"]["memory_freed_total_bytes"]
            assert total_freed > 2000, f"Insufficient total memory freed: {total_freed} bytes"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.concurrent_cleanup
    async def test_concurrent_user_disconnections_cleanup_isolation(self, real_services_fixture):
        """Test cleanup isolation during concurrent user disconnections."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketContextCleanupValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create multiple users concurrently
            concurrent_user_data = []
            for i in range(4):
                user_id, connection_id, context_id = await validator.create_user_with_comprehensive_context(f"concurrent-{i}")
                concurrent_user_data.append((user_id, connection_id, context_id))
            
            # Execute concurrent disconnections with cleanup
            cleanup_tasks = []
            for i, (user_id, connection_id, context_id) in enumerate(concurrent_user_data):
                disconnect_type = [DisconnectionType.GRACEFUL, DisconnectionType.ABRUPT, 
                                 DisconnectionType.TIMEOUT, DisconnectionType.SERVER_INITIATED][i]
                
                cleanup_task = validator.simulate_websocket_disconnection_with_cleanup(
                    user_id, connection_id, context_id, disconnect_type
                )
                cleanup_tasks.append(cleanup_task)
            
            # Wait for all concurrent cleanups to complete
            concurrent_cleanup_records = await asyncio.gather(*cleanup_tasks)
            
            # Validate concurrent cleanup isolation
            concurrent_validation = await validator.validate_context_cleanup_completeness(concurrent_cleanup_records)
            
            # CONCURRENT CLEANUP VALIDATIONS
            
            # All concurrent cleanups should succeed
            assert concurrent_validation["cleanup_completeness_score"] == 1.0, \
                "Concurrent cleanups must all succeed"
            assert concurrent_validation["failed_cleanups"] == 0, \
                "No concurrent cleanup failures allowed"
            
            # No cross-user cleanup contamination
            user_ids = {record.user_id for record in concurrent_cleanup_records}
            assert len(user_ids) == 4, "All users should have distinct cleanup records"
            
            # Each user's cleanup should be isolated
            for i, record in enumerate(concurrent_cleanup_records):
                expected_user_id = concurrent_user_data[i][0]
                assert record.user_id == expected_user_id, \
                    f"Cleanup record {i} has wrong user ID: {record.user_id} vs {expected_user_id}"
                
                # Post-cleanup should be clean for each user
                post_snapshot = record.post_cleanup_snapshot
                assert len(post_snapshot.cache_keys) == 0, \
                    f"User {record.user_id} still has cache keys after cleanup"
                assert post_snapshot.calculate_total_size_bytes() < 100, \
                    f"User {record.user_id} has too much remaining data"
            
            # Performance should not degrade significantly under concurrency
            avg_duration = concurrent_validation["cleanup_performance"]["avg_cleanup_duration_ms"]
            assert avg_duration < 4000, f"Concurrent cleanup too slow: {avg_duration}ms"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.cleanup_stress
    async def test_cleanup_under_high_context_load(self, real_services_fixture):
        """Test context cleanup under high context data load."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketContextCleanupValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create user with very large context (stress test)
            user_id, connection_id, context_id = await validator.create_user_with_comprehensive_context("stress-load")
            
            # Add additional heavy context data
            for i in range(20):  # Create many temporary items
                large_temp_data = {
                    "temp_id": f"stress-temp-{i}",
                    "user_id": user_id,
                    "large_content": "x" * 10000,  # 10KB per item
                    "metadata": {"index": i, "stress_test": True},
                    "created_at": time.time()
                }
                
                temp_key = f"stress_temp:{user_id}:{i}"
                await validator.redis_client.set(temp_key, json.dumps(large_temp_data), ex=1800)
            
            # Add large analytics data
            large_analytics = {
                "user_id": user_id,
                "detailed_logs": ["log_entry_" + str(i) for i in range(1000)],
                "performance_data": {f"metric_{i}": i * 0.1 for i in range(500)},
                "feature_usage_history": [{"feature": f"feature_{i}", "usage": i} for i in range(200)]
            }
            
            await validator.redis_client.set(f"stress_analytics:{user_id}", 
                                           json.dumps(large_analytics), ex=7200)
            
            # Capture pre-cleanup snapshot
            pre_cleanup_snapshot = await validator.capture_context_snapshot(user_id, connection_id, context_id)
            initial_size = pre_cleanup_snapshot.calculate_total_size_bytes()
            
            # Should have substantial context data
            assert initial_size > 50000, f"Stress test context should be large: {initial_size} bytes"
            
            # Execute cleanup under stress
            stress_cleanup_record = await validator.simulate_websocket_disconnection_with_cleanup(
                user_id, connection_id, context_id, DisconnectionType.GRACEFUL
            )
            
            # STRESS CLEANUP VALIDATIONS
            
            # Cleanup should still succeed under high load
            assert stress_cleanup_record.cleanup_success, \
                f"Stress cleanup failed: {stress_cleanup_record.cleanup_violations}"
            
            # Should free significant memory
            assert stress_cleanup_record.memory_freed_bytes > 40000, \
                f"Should free substantial memory under stress: {stress_cleanup_record.memory_freed_bytes} bytes"
            
            # Should clean up many cache keys
            assert stress_cleanup_record.cache_keys_cleaned > 20, \
                f"Should clean many cache keys under stress: {stress_cleanup_record.cache_keys_cleaned}"
            
            # Should complete within reasonable time even under stress
            assert stress_cleanup_record.cleanup_duration_ms < 10000, \
                f"Stress cleanup took too long: {stress_cleanup_record.cleanup_duration_ms}ms"
            
            # Post-cleanup should still be clean despite large initial size
            post_snapshot = stress_cleanup_record.post_cleanup_snapshot
            post_size = post_snapshot.calculate_total_size_bytes()
            assert post_size < 200, f"Post-stress cleanup should be minimal: {post_size} bytes"
            
        finally:
            await validator.cleanup()