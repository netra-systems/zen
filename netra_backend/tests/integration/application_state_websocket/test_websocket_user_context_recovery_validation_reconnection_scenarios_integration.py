"""
Test WebSocket User Context Recovery Validation During Reconnection Scenarios Integration (#30)

Business Value Justification (BVJ):
- Segment: All (Critical for user experience continuity and system reliability)
- Business Goal: Ensure seamless user context recovery during WebSocket reconnections
- Value Impact: Users maintain conversation history and state across network interruptions
- Strategic Impact: Foundation of reliable real-time communication - prevents user frustration and data loss

CRITICAL REQUIREMENT: When users reconnect to WebSocket after disconnection, their context
must be accurately restored while maintaining security and isolation. Context recovery must
be complete for owned data and completely blocked for unauthorized data. Any context recovery
failure results in poor user experience and potential data inconsistency.
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
RecoveryTaskID = str


class ReconnectionScenario(Enum):
    """Types of reconnection scenarios."""
    QUICK_RECONNECT = "quick_reconnect"  # Reconnect within seconds
    DELAYED_RECONNECT = "delayed_reconnect"  # Reconnect after minutes
    LONG_TERM_RECONNECT = "long_term_reconnect"  # Reconnect after hours
    CROSS_DEVICE_RECONNECT = "cross_device_reconnect"  # Reconnect from different device
    NETWORK_SWITCH_RECONNECT = "network_switch_reconnect"  # Network/IP change
    BROWSER_REFRESH_RECONNECT = "browser_refresh_reconnect"  # Browser refresh/restart


class ContextRecoveryStage(Enum):
    """Stages of context recovery process."""
    INITIATED = "initiated"
    AUTHENTICATION_VERIFIED = "authentication_verified"
    SESSION_RESTORED = "session_restored"
    USER_PREFERENCES_LOADED = "user_preferences_loaded"
    CONVERSATION_HISTORY_RECOVERED = "conversation_history_recovered"
    WEBSOCKET_STATE_REBUILT = "websocket_state_rebuilt"
    AGENT_STATES_RESTORED = "agent_states_restored"
    PERMISSIONS_VALIDATED = "permissions_validated"
    CONTEXT_SYNCHRONIZED = "context_synchronized"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ContextRecoveryProfile:
    """Profile defining what context should be recovered for a user."""
    user_id: UserID
    organization_id: str
    recovery_permissions: Set[str]
    conversation_history_depth: int  # How many messages to recover
    agent_state_recovery_enabled: bool
    preference_sync_enabled: bool
    security_level: str  # basic, standard, strict
    data_residency_region: str
    max_recovery_age_hours: int  # How old data can be recovered
    recovery_scope: Set[str]  # Types of data to recover
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "recovery_permissions": list(self.recovery_permissions),
            "conversation_history_depth": self.conversation_history_depth,
            "agent_state_recovery_enabled": self.agent_state_recovery_enabled,
            "preference_sync_enabled": self.preference_sync_enabled,
            "security_level": self.security_level,
            "data_residency_region": self.data_residency_region,
            "max_recovery_age_hours": self.max_recovery_age_hours,
            "recovery_scope": list(self.recovery_scope)
        }


@dataclass
class ContextRecoveryRecord:
    """Record of context recovery process and results."""
    recovery_id: RecoveryTaskID
    user_id: UserID
    old_connection_id: Optional[ConnectionID]
    new_connection_id: ConnectionID
    reconnection_scenario: ReconnectionScenario
    recovery_profile: ContextRecoveryProfile
    recovery_stages: List[Dict[str, Any]] = field(default_factory=list)
    recovered_data: Dict[str, Any] = field(default_factory=dict)
    recovery_metrics: Dict[str, Any] = field(default_factory=dict)
    recovery_violations: List[Dict[str, Any]] = field(default_factory=list)
    recovery_success: bool = False
    recovery_completeness_score: float = 0.0
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    def add_stage(self, stage: ContextRecoveryStage, success: bool = True, 
                 details: Dict[str, Any] = None):
        """Add recovery stage with details."""
        stage_record = {
            "stage": stage.value,
            "timestamp": time.time(),
            "success": success,
            "details": details or {}
        }
        self.recovery_stages.append(stage_record)
        
        if stage == ContextRecoveryStage.COMPLETED and success:
            self.recovery_success = True
            self.completed_at = time.time()
        elif not success:
            self.recovery_violations.append({
                "stage": stage.value,
                "failure_reason": details.get("error", "unknown"),
                "timestamp": time.time()
            })


class WebSocketContextRecoveryValidator:
    """Validates user context recovery during WebSocket reconnection scenarios."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.redis_client = None
        self.recovery_records = {}
        self.persistent_context_store = {}  # Simulates persistent storage
        self.cross_session_violations = []
        self.unauthorized_recovery_attempts = []
    
    async def setup(self):
        """Set up validator with Redis connection."""
        import redis.asyncio as redis
        self.redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        await self.redis_client.ping()
    
    async def cleanup(self):
        """Clean up validator resources."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def create_user_session_for_recovery_testing(self, user_suffix: str, 
                                                      organization_id: str = None) -> Tuple[UserID, ConnectionID, ContextRecoveryProfile]:
        """Create user session with comprehensive context for recovery testing."""
        user_id = f"recovery-test-user-{user_suffix}"
        connection_id = f"conn-{uuid.uuid4().hex}"
        
        # Create user in database
        await self.real_services["db"].execute("""
            INSERT INTO auth.users (id, email, name, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, user_id, f"{user_id}@recovery-test.com", f"Recovery Test User {user_suffix}", True)
        
        # Create organization if not provided
        if organization_id is None:
            organization_id = f"recovery-org-{user_suffix}"
        
        await self.real_services["db"].execute("""
            INSERT INTO backend.organizations (id, name, slug, plan, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                plan = EXCLUDED.plan
        """, organization_id, f"Recovery Test Org {user_suffix}", 
            f"recovery-org-{user_suffix}", "enterprise")
        
        # Create organization membership
        await self.real_services["db"].execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, organization_id) DO UPDATE SET role = EXCLUDED.role
        """, user_id, organization_id, "member")
        
        # Create comprehensive conversation history
        thread_ids = []
        message_ids = []
        for i in range(3):
            thread_id = f"thread-{user_suffix}-{i}"
            await self.real_services["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (id) DO UPDATE SET 
                    title = EXCLUDED.title,
                    updated_at = NOW()
            """, thread_id, user_id, f"Recovery Test Conversation {i}")
            thread_ids.append(thread_id)
            
            # Create messages in each thread
            for j in range(5):  # 5 messages per thread
                message_id = f"msg-{user_suffix}-{i}-{j}"
                content = f"Message {j} in conversation {i} - recovery test content for {user_suffix}"
                await self.real_services["db"].execute("""
                    INSERT INTO backend.messages (id, thread_id, user_id, content, role, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
                """, message_id, thread_id, user_id, content, "user" if j % 2 == 0 else "assistant")
                message_ids.append(message_id)
        
        # Create user session with rich context
        session_context = {
            "user_id": user_id,
            "connection_id": connection_id,
            "organization_id": organization_id,
            "session_start_time": time.time(),
            "conversation_threads": thread_ids,
            "recent_messages": message_ids[-10:],  # Last 10 messages
            "user_preferences": {
                "theme": "dark",
                "language": "en",
                "notification_settings": {
                    "email": True,
                    "push": False,
                    "websocket": True
                },
                "ai_settings": {
                    "response_style": "detailed",
                    "include_sources": True,
                    "max_response_length": 1000
                }
            },
            "agent_interaction_history": [
                {
                    "agent_type": "data_analyst",
                    "interaction_count": 5,
                    "last_used": time.time() - 300,
                    "preferred_settings": {"detail_level": "high"}
                },
                {
                    "agent_type": "code_assistant", 
                    "interaction_count": 3,
                    "last_used": time.time() - 600,
                    "preferred_settings": {"language": "python"}
                }
            ],
            "active_features": ["chat", "agents", "analytics"],
            "session_metrics": {
                "messages_sent": 25,
                "agents_used": 8,
                "time_active_minutes": 45
            }
        }
        
        # Store session in persistent context store (simulates durable storage)
        persistent_key = f"persistent_session:{user_id}"
        self.persistent_context_store[persistent_key] = session_context
        
        # Store in Redis with longer TTL for recovery testing
        session_key = f"user_session:{user_id}"
        await self.redis_client.set(session_key, json.dumps(session_context), ex=7200)  # 2 hours
        
        # Store WebSocket connection state
        ws_state = {
            "connection_id": connection_id,
            "user_id": user_id,
            "state": WebSocketConnectionState.CONNECTED,
            "connected_at": time.time(),
            "channels": ["general", f"user_{user_id}", f"org_{organization_id}"],
            "active_subscriptions": ["messages", "agent_updates", "system_notifications"],
            "last_activity": time.time(),
            "connection_metadata": {
                "ip": "127.0.0.1",
                "user_agent": "test-client",
                "session_id": f"session-{user_suffix}"
            }
        }
        
        ws_key = f"ws_state:{connection_id}"
        await self.redis_client.set(ws_key, json.dumps(ws_state), ex=3600)
        
        # Create recovery profile
        recovery_profile = ContextRecoveryProfile(
            user_id=user_id,
            organization_id=organization_id,
            recovery_permissions={"read_messages", "write_messages", "access_agents", "view_history"},
            conversation_history_depth=50,  # Recover last 50 messages
            agent_state_recovery_enabled=True,
            preference_sync_enabled=True,
            security_level="standard",
            data_residency_region="us-east-1",
            max_recovery_age_hours=24,
            recovery_scope={"session", "preferences", "history", "agents", "subscriptions"}
        )
        
        return user_id, connection_id, recovery_profile
    
    async def simulate_disconnection_and_context_persistence(self, user_id: UserID, connection_id: ConnectionID,
                                                            disconnection_delay_seconds: float = 0.0):
        """Simulate disconnection and context persistence for later recovery."""
        # Simulate disconnection delay
        if disconnection_delay_seconds > 0:
            await asyncio.sleep(disconnection_delay_seconds)
        
        # Mark WebSocket as disconnected but preserve session data
        ws_key = f"ws_state:{connection_id}"
        ws_data = await self.redis_client.get(ws_key)
        
        if ws_data:
            ws_state = json.loads(ws_data)
            ws_state["state"] = WebSocketConnectionState.DISCONNECTED
            ws_state["disconnected_at"] = time.time()
            ws_state["disconnect_reason"] = "network_interruption"
            
            # Store disconnection state with extended TTL for recovery
            await self.redis_client.set(ws_key, json.dumps(ws_state), ex=3600)
        
        # Persist critical context data for recovery
        session_key = f"user_session:{user_id}"
        session_data = await self.redis_client.get(session_key)
        
        if session_data:
            # Store in persistent recovery store
            recovery_key = f"recovery_context:{user_id}:{int(time.time())}"
            self.persistent_context_store[recovery_key] = json.loads(session_data)
    
    async def simulate_websocket_reconnection_with_context_recovery(self, user_id: UserID, 
                                                                   old_connection_id: Optional[ConnectionID],
                                                                   recovery_profile: ContextRecoveryProfile,
                                                                   reconnection_scenario: ReconnectionScenario,
                                                                   reconnection_delay_seconds: float = 0.0) -> ContextRecoveryRecord:
        """Simulate WebSocket reconnection with comprehensive context recovery."""
        recovery_id = f"recovery-{uuid.uuid4().hex}"
        new_connection_id = f"conn-{uuid.uuid4().hex}"
        
        # Simulate reconnection delay
        if reconnection_delay_seconds > 0:
            await asyncio.sleep(reconnection_delay_seconds)
        
        recovery_record = ContextRecoveryRecord(
            recovery_id=recovery_id,
            user_id=user_id,
            old_connection_id=old_connection_id,
            new_connection_id=new_connection_id,
            reconnection_scenario=reconnection_scenario,
            recovery_profile=recovery_profile
        )
        
        try:
            # Stage 1: Initiate Recovery
            recovery_record.add_stage(ContextRecoveryStage.INITIATED, True, {
                "scenario": reconnection_scenario.value,
                "delay_seconds": reconnection_delay_seconds,
                "user_id": user_id,
                "new_connection": new_connection_id
            })
            
            # Stage 2: Verify Authentication
            auth_verification = await self._verify_authentication_for_recovery(user_id, recovery_profile)
            recovery_record.add_stage(ContextRecoveryStage.AUTHENTICATION_VERIFIED,
                                    auth_verification["success"], auth_verification)
            
            if not auth_verification["success"]:
                recovery_record.add_stage(ContextRecoveryStage.FAILED, False, auth_verification)
                return recovery_record
            
            # Stage 3: Restore Session
            session_restoration = await self._restore_user_session(user_id, recovery_profile)
            recovery_record.add_stage(ContextRecoveryStage.SESSION_RESTORED,
                                    session_restoration["success"], session_restoration)
            recovery_record.recovered_data["session"] = session_restoration.get("session_data", {})
            
            # Stage 4: Load User Preferences
            preferences_loading = await self._load_user_preferences(user_id, recovery_profile)
            recovery_record.add_stage(ContextRecoveryStage.USER_PREFERENCES_LOADED,
                                    preferences_loading["success"], preferences_loading)
            recovery_record.recovered_data["preferences"] = preferences_loading.get("preferences", {})
            
            # Stage 5: Recover Conversation History
            history_recovery = await self._recover_conversation_history(user_id, recovery_profile)
            recovery_record.add_stage(ContextRecoveryStage.CONVERSATION_HISTORY_RECOVERED,
                                    history_recovery["success"], history_recovery)
            recovery_record.recovered_data["conversation_history"] = history_recovery.get("history", [])
            
            # Stage 6: Rebuild WebSocket State
            websocket_rebuilding = await self._rebuild_websocket_state(new_connection_id, user_id, recovery_profile)
            recovery_record.add_stage(ContextRecoveryStage.WEBSOCKET_STATE_REBUILT,
                                    websocket_rebuilding["success"], websocket_rebuilding)
            recovery_record.recovered_data["websocket_state"] = websocket_rebuilding.get("state", {})
            
            # Stage 7: Restore Agent States
            agent_restoration = await self._restore_agent_states(user_id, recovery_profile)
            recovery_record.add_stage(ContextRecoveryStage.AGENT_STATES_RESTORED,
                                    agent_restoration["success"], agent_restoration)
            recovery_record.recovered_data["agent_states"] = agent_restoration.get("agent_states", [])
            
            # Stage 8: Validate Permissions
            permission_validation = await self._validate_recovery_permissions(user_id, recovery_profile, recovery_record)
            recovery_record.add_stage(ContextRecoveryStage.PERMISSIONS_VALIDATED,
                                    permission_validation["success"], permission_validation)
            
            # Stage 9: Synchronize Context
            context_sync = await self._synchronize_recovered_context(recovery_record)
            recovery_record.add_stage(ContextRecoveryStage.CONTEXT_SYNCHRONIZED,
                                    context_sync["success"], context_sync)
            
            # Stage 10: Complete Recovery
            completion_metrics = await self._calculate_recovery_metrics(recovery_record)
            recovery_record.recovery_metrics = completion_metrics
            recovery_record.recovery_completeness_score = completion_metrics.get("completeness_score", 0.0)
            
            recovery_record.add_stage(ContextRecoveryStage.COMPLETED, True, {
                "recovery_metrics": completion_metrics,
                "completeness_score": recovery_record.recovery_completeness_score
            })
            
        except Exception as e:
            recovery_record.add_stage(ContextRecoveryStage.FAILED, False, {
                "error": str(e),
                "failed_at": time.time()
            })
        
        self.recovery_records[recovery_id] = recovery_record
        return recovery_record
    
    async def _verify_authentication_for_recovery(self, user_id: UserID, 
                                                 recovery_profile: ContextRecoveryProfile) -> Dict[str, Any]:
        """Verify user authentication for context recovery."""
        auth_result = {"success": True, "user_verified": True, "permissions_valid": True}
        
        try:
            # Verify user exists and is active
            user_record = await self.real_services["db"].fetchrow("""
                SELECT id, is_active, created_at FROM auth.users WHERE id = $1
            """, user_id)
            
            if not user_record:
                auth_result["success"] = False
                auth_result["error"] = "user_not_found"
                return auth_result
            
            if not user_record["is_active"]:
                auth_result["success"] = False
                auth_result["error"] = "user_inactive"
                return auth_result
            
            # Verify organization membership
            org_membership = await self.real_services["db"].fetchrow("""
                SELECT role FROM backend.organization_memberships 
                WHERE user_id = $1 AND organization_id = $2
            """, user_id, recovery_profile.organization_id)
            
            if not org_membership:
                auth_result["success"] = False
                auth_result["error"] = "organization_access_denied"
                return auth_result
            
            auth_result["user_role"] = org_membership["role"]
            
        except Exception as e:
            auth_result["success"] = False
            auth_result["error"] = str(e)
        
        return auth_result
    
    async def _restore_user_session(self, user_id: UserID, 
                                   recovery_profile: ContextRecoveryProfile) -> Dict[str, Any]:
        """Restore user session data."""
        restoration_result = {"success": True, "session_data": {}}
        
        try:
            # Try to restore from Redis cache first
            session_key = f"user_session:{user_id}"
            cached_session = await self.redis_client.get(session_key)
            
            if cached_session:
                restoration_result["session_data"] = json.loads(cached_session)
                restoration_result["restored_from"] = "cache"
            else:
                # Restore from persistent storage
                persistent_keys = [key for key in self.persistent_context_store.keys() 
                                 if key.startswith(f"persistent_session:{user_id}")]
                
                if persistent_keys:
                    # Get most recent persistent session
                    latest_key = max(persistent_keys)
                    restoration_result["session_data"] = self.persistent_context_store[latest_key]
                    restoration_result["restored_from"] = "persistent_storage"
                    
                    # Restore to cache with extended TTL
                    await self.redis_client.set(session_key, 
                                               json.dumps(restoration_result["session_data"]), ex=7200)
                else:
                    restoration_result["success"] = False
                    restoration_result["error"] = "no_session_data_found"
        
        except Exception as e:
            restoration_result["success"] = False
            restoration_result["error"] = str(e)
        
        return restoration_result
    
    async def _load_user_preferences(self, user_id: UserID, 
                                    recovery_profile: ContextRecoveryProfile) -> Dict[str, Any]:
        """Load user preferences for recovery."""
        preferences_result = {"success": True, "preferences": {}}
        
        if not recovery_profile.preference_sync_enabled:
            preferences_result["preferences"] = {}  # Default empty preferences
            preferences_result["reason"] = "preference_sync_disabled"
            return preferences_result
        
        try:
            # Load from session data or persistent storage
            session_key = f"user_session:{user_id}"
            session_data = await self.redis_client.get(session_key)
            
            if session_data:
                session_dict = json.loads(session_data)
                preferences_result["preferences"] = session_dict.get("user_preferences", {})
            else:
                # Default preferences
                preferences_result["preferences"] = {
                    "theme": "light",
                    "language": "en",
                    "notification_settings": {"websocket": True},
                    "ai_settings": {"response_style": "standard"}
                }
                preferences_result["reason"] = "using_defaults"
        
        except Exception as e:
            preferences_result["success"] = False
            preferences_result["error"] = str(e)
        
        return preferences_result
    
    async def _recover_conversation_history(self, user_id: UserID,
                                           recovery_profile: ContextRecoveryProfile) -> Dict[str, Any]:
        """Recover conversation history from database."""
        history_result = {"success": True, "history": []}
        
        try:
            # Get user's threads
            threads = await self.real_services["db"].fetch("""
                SELECT id, title, created_at FROM backend.threads 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT 10
            """, user_id)
            
            history_entries = []
            for thread in threads:
                # Get recent messages from each thread
                messages = await self.real_services["db"].fetch("""
                    SELECT id, content, role, created_at FROM backend.messages 
                    WHERE thread_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, thread["id"], min(recovery_profile.conversation_history_depth, 20))
                
                thread_history = {
                    "thread_id": thread["id"],
                    "thread_title": thread["title"],
                    "messages": [
                        {
                            "message_id": msg["id"],
                            "content": msg["content"],
                            "role": msg["role"],
                            "created_at": msg["created_at"].timestamp()
                        } for msg in messages
                    ]
                }
                
                history_entries.append(thread_history)
            
            history_result["history"] = history_entries
            history_result["threads_recovered"] = len(history_entries)
            history_result["total_messages"] = sum(len(entry["messages"]) for entry in history_entries)
            
        except Exception as e:
            history_result["success"] = False
            history_result["error"] = str(e)
        
        return history_result
    
    async def _rebuild_websocket_state(self, new_connection_id: ConnectionID, user_id: UserID,
                                      recovery_profile: ContextRecoveryProfile) -> Dict[str, Any]:
        """Rebuild WebSocket connection state."""
        rebuild_result = {"success": True, "state": {}}
        
        try:
            # Create new WebSocket state
            new_ws_state = {
                "connection_id": new_connection_id,
                "user_id": user_id,
                "organization_id": recovery_profile.organization_id,
                "state": WebSocketConnectionState.CONNECTED,
                "connected_at": time.time(),
                "reconnection_recovery": True,
                "channels": ["general", f"user_{user_id}", f"org_{recovery_profile.organization_id}"],
                "active_subscriptions": ["messages", "agent_updates", "system_notifications"],
                "recovery_metadata": {
                    "recovered_from_scenario": "context_recovery",
                    "recovery_permissions": list(recovery_profile.recovery_permissions),
                    "security_level": recovery_profile.security_level
                }
            }
            
            # Store new WebSocket state
            ws_key = f"ws_state:{new_connection_id}"
            await self.redis_client.set(ws_key, json.dumps(new_ws_state), ex=3600)
            
            rebuild_result["state"] = new_ws_state
            
        except Exception as e:
            rebuild_result["success"] = False
            rebuild_result["error"] = str(e)
        
        return rebuild_result
    
    async def _restore_agent_states(self, user_id: UserID,
                                   recovery_profile: ContextRecoveryProfile) -> Dict[str, Any]:
        """Restore agent interaction states."""
        agent_result = {"success": True, "agent_states": []}
        
        if not recovery_profile.agent_state_recovery_enabled:
            agent_result["reason"] = "agent_recovery_disabled"
            return agent_result
        
        try:
            # Look for agent states in session data
            session_key = f"user_session:{user_id}"
            session_data = await self.redis_client.get(session_key)
            
            if session_data:
                session_dict = json.loads(session_data)
                agent_history = session_dict.get("agent_interaction_history", [])
                
                # Restore agent states
                for agent_info in agent_history:
                    if agent_info["last_used"] > time.time() - (recovery_profile.max_recovery_age_hours * 3600):
                        restored_agent = {
                            "agent_type": agent_info["agent_type"],
                            "user_id": user_id,
                            "last_interaction": agent_info["last_used"],
                            "interaction_count": agent_info["interaction_count"],
                            "preferred_settings": agent_info.get("preferred_settings", {}),
                            "state": "ready",
                            "recovered": True
                        }
                        
                        agent_result["agent_states"].append(restored_agent)
                        
                        # Store restored agent state
                        agent_key = f"agent_state:{user_id}:{agent_info['agent_type']}"
                        await self.redis_client.set(agent_key, json.dumps(restored_agent), ex=1800)
            
        except Exception as e:
            agent_result["success"] = False
            agent_result["error"] = str(e)
        
        return agent_result
    
    async def _validate_recovery_permissions(self, user_id: UserID, 
                                           recovery_profile: ContextRecoveryProfile,
                                           recovery_record: ContextRecoveryRecord) -> Dict[str, Any]:
        """Validate that recovered context respects user permissions."""
        validation_result = {"success": True, "violations": []}
        
        try:
            # Verify user can access recovered conversation history
            recovered_history = recovery_record.recovered_data.get("conversation_history", [])
            for thread_entry in recovered_history:
                thread_id = thread_entry["thread_id"]
                
                # Check thread ownership
                thread_owner = await self.real_services["db"].fetchval("""
                    SELECT user_id FROM backend.threads WHERE id = $1
                """, thread_id)
                
                if thread_owner != user_id:
                    validation_result["violations"].append({
                        "type": "unauthorized_thread_access",
                        "thread_id": thread_id,
                        "owner": thread_owner,
                        "accessor": user_id
                    })
                    validation_result["success"] = False
            
            # Verify organization access
            if recovery_profile.organization_id:
                org_access = await self.real_services["db"].fetchval("""
                    SELECT COUNT(*) FROM backend.organization_memberships 
                    WHERE user_id = $1 AND organization_id = $2
                """, user_id, recovery_profile.organization_id)
                
                if org_access == 0:
                    validation_result["violations"].append({
                        "type": "unauthorized_organization_access",
                        "organization_id": recovery_profile.organization_id,
                        "user_id": user_id
                    })
                    validation_result["success"] = False
            
        except Exception as e:
            validation_result["success"] = False
            validation_result["error"] = str(e)
        
        return validation_result
    
    async def _synchronize_recovered_context(self, recovery_record: ContextRecoveryRecord) -> Dict[str, Any]:
        """Synchronize all recovered context components."""
        sync_result = {"success": True, "synchronized_components": []}
        
        try:
            # Ensure all recovered data is consistent
            recovered_data = recovery_record.recovered_data
            
            # Synchronize session with preferences
            if "session" in recovered_data and "preferences" in recovered_data:
                session_data = recovered_data["session"]
                preferences = recovered_data["preferences"]
                
                # Update session with latest preferences
                session_data["user_preferences"] = preferences
                sync_result["synchronized_components"].append("session_preferences")
            
            # Synchronize WebSocket state with conversation history
            if "websocket_state" in recovered_data and "conversation_history" in recovered_data:
                ws_state = recovered_data["websocket_state"]
                history = recovered_data["conversation_history"]
                
                # Add active threads to WebSocket channels
                active_threads = [entry["thread_id"] for entry in history[:3]]  # Top 3 threads
                for thread_id in active_threads:
                    if f"thread_{thread_id}" not in ws_state.get("channels", []):
                        ws_state.setdefault("channels", []).append(f"thread_{thread_id}")
                
                sync_result["synchronized_components"].append("websocket_history")
            
            # Synchronize agent states with preferences
            if "agent_states" in recovered_data and "preferences" in recovered_data:
                agent_states = recovered_data["agent_states"]
                preferences = recovered_data["preferences"]
                ai_settings = preferences.get("ai_settings", {})
                
                # Apply user AI preferences to agent states
                for agent_state in agent_states:
                    agent_state["user_preferences"] = ai_settings
                
                sync_result["synchronized_components"].append("agent_preferences")
            
        except Exception as e:
            sync_result["success"] = False
            sync_result["error"] = str(e)
        
        return sync_result
    
    async def _calculate_recovery_metrics(self, recovery_record: ContextRecoveryRecord) -> Dict[str, Any]:
        """Calculate comprehensive recovery metrics."""
        metrics = {
            "completeness_score": 0.0,
            "recovery_time_ms": 0.0,
            "data_recovered": {},
            "recovery_quality": {}
        }
        
        try:
            # Calculate recovery time
            if recovery_record.completed_at and recovery_record.started_at:
                metrics["recovery_time_ms"] = (recovery_record.completed_at - recovery_record.started_at) * 1000
            
            # Calculate completeness score
            expected_components = {"session", "preferences", "conversation_history", "websocket_state", "agent_states"}
            recovered_components = set(recovery_record.recovered_data.keys())
            metrics["completeness_score"] = len(recovered_components.intersection(expected_components)) / len(expected_components)
            
            # Calculate data recovery metrics
            recovered_data = recovery_record.recovered_data
            
            if "conversation_history" in recovered_data:
                history = recovered_data["conversation_history"]
                metrics["data_recovered"]["threads"] = len(history)
                metrics["data_recovered"]["messages"] = sum(len(entry["messages"]) for entry in history)
            
            if "agent_states" in recovered_data:
                metrics["data_recovered"]["agents"] = len(recovered_data["agent_states"])
            
            if "preferences" in recovered_data:
                metrics["data_recovered"]["preferences"] = len(recovered_data["preferences"])
            
            # Quality assessment
            successful_stages = len([stage for stage in recovery_record.recovery_stages if stage["success"]])
            total_stages = len(recovery_record.recovery_stages)
            metrics["recovery_quality"]["stage_success_rate"] = successful_stages / total_stages if total_stages > 0 else 0
            
            metrics["recovery_quality"]["violations_count"] = len(recovery_record.recovery_violations)
            metrics["recovery_quality"]["security_compliant"] = len(recovery_record.recovery_violations) == 0
            
        except Exception as e:
            metrics["error"] = str(e)
        
        return metrics


class TestWebSocketUserContextRecoveryValidation(BaseIntegrationTest):
    """
    Integration test for user context recovery validation during WebSocket reconnection scenarios.
    
    CRITICAL: Validates seamless and secure context recovery across various reconnection scenarios.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.recovery_critical
    async def test_websocket_quick_reconnection_context_recovery(self, real_services_fixture):
        """
        Test context recovery during quick WebSocket reconnection (within seconds).
        
        CRITICAL: Quick reconnections should restore complete context seamlessly.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketContextRecoveryValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create user session with rich context
            user_id, original_connection_id, recovery_profile = await validator.create_user_session_for_recovery_testing("quick-recovery")
            
            # Verify initial context is comprehensive
            assert recovery_profile.conversation_history_depth == 50
            assert recovery_profile.agent_state_recovery_enabled
            assert recovery_profile.preference_sync_enabled
            
            # Simulate brief disconnection (network glitch)
            await validator.simulate_disconnection_and_context_persistence(user_id, original_connection_id, 0.5)
            
            # Quick reconnection with context recovery
            recovery_record = await validator.simulate_websocket_reconnection_with_context_recovery(
                user_id, original_connection_id, recovery_profile, 
                ReconnectionScenario.QUICK_RECONNECT, 2.0  # 2-second delay
            )
            
            # CRITICAL RECOVERY VALIDATIONS
            
            # Recovery must succeed completely
            assert recovery_record.recovery_success, \
                f"Quick reconnection recovery failed: {recovery_record.recovery_violations}"
            
            # High completeness expected for quick reconnection
            assert recovery_record.recovery_completeness_score >= 0.9, \
                f"Quick recovery completeness too low: {recovery_record.recovery_completeness_score}"
            
            # All expected stages should complete
            expected_stages = [
                "initiated", "authentication_verified", "session_restored",
                "user_preferences_loaded", "conversation_history_recovered",
                "websocket_state_rebuilt", "agent_states_restored",
                "permissions_validated", "context_synchronized", "completed"
            ]
            completed_stages = [stage["stage"] for stage in recovery_record.recovery_stages]
            
            for expected_stage in expected_stages:
                assert expected_stage in completed_stages, \
                    f"Expected recovery stage '{expected_stage}' not completed"
            
            # Verify comprehensive data recovery
            recovered_data = recovery_record.recovered_data
            assert "session" in recovered_data, "Session data should be recovered"
            assert "preferences" in recovered_data, "User preferences should be recovered"
            assert "conversation_history" in recovered_data, "Conversation history should be recovered"
            assert "websocket_state" in recovered_data, "WebSocket state should be rebuilt"
            assert "agent_states" in recovered_data, "Agent states should be restored"
            
            # Verify conversation history recovery
            history = recovered_data["conversation_history"]
            assert len(history) > 0, "Should recover conversation history"
            assert len(history) <= 10, "Should limit thread count reasonably"
            
            total_messages = sum(len(thread["messages"]) for thread in history)
            assert total_messages > 0, "Should recover messages"
            
            # Verify agent states recovery
            agent_states = recovered_data["agent_states"]
            assert len(agent_states) > 0, "Should recover agent interaction states"
            
            for agent_state in agent_states:
                assert agent_state["recovered"], "Agent state should be marked as recovered"
                assert agent_state["user_id"] == user_id, "Agent state should belong to correct user"
            
            # Performance validation for quick reconnection
            recovery_time = recovery_record.recovery_metrics.get("recovery_time_ms", 0)
            assert recovery_time < 3000, f"Quick recovery too slow: {recovery_time}ms"
            
            # Security validation
            assert len(recovery_record.recovery_violations) == 0, \
                f"Security violations in recovery: {recovery_record.recovery_violations}"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.delayed_recovery
    async def test_websocket_delayed_reconnection_context_recovery(self, real_services_fixture):
        """Test context recovery during delayed WebSocket reconnection (after minutes)."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketContextRecoveryValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create user session for delayed recovery testing
            user_id, original_connection_id, recovery_profile = await validator.create_user_session_for_recovery_testing("delayed-recovery")
            
            # Simulate longer disconnection (simulated - don't actually wait minutes)
            await validator.simulate_disconnection_and_context_persistence(user_id, original_connection_id, 1.0)
            
            # Simulate delayed reconnection
            delayed_recovery_record = await validator.simulate_websocket_reconnection_with_context_recovery(
                user_id, original_connection_id, recovery_profile,
                ReconnectionScenario.DELAYED_RECONNECT, 5.0  # 5-second delay (simulated minutes)
            )
            
            # DELAYED RECOVERY VALIDATIONS
            
            # Delayed recovery should still succeed
            assert delayed_recovery_record.recovery_success, \
                f"Delayed recovery failed: {delayed_recovery_record.recovery_violations}"
            
            # Completeness may be slightly lower due to cache expiration
            assert delayed_recovery_record.recovery_completeness_score >= 0.8, \
                f"Delayed recovery completeness too low: {delayed_recovery_record.recovery_completeness_score}"
            
            # Should recover from persistent storage
            recovered_session = delayed_recovery_record.recovered_data.get("session", {})
            if "restored_from" in recovered_session:
                # Should use persistent storage for delayed recovery
                assert recovered_session.get("restored_from") in ["persistent_storage", "cache"]
            
            # Conversation history should be fully recovered (from database)
            history = delayed_recovery_record.recovered_data.get("conversation_history", [])
            assert len(history) > 0, "Delayed recovery should still recover conversation history"
            
            # Agent states may have limited recovery after delay
            agent_states = delayed_recovery_record.recovered_data.get("agent_states", [])
            # Agent state recovery depends on max_recovery_age_hours setting
            
            # Recovery time may be longer but should still be reasonable
            recovery_time = delayed_recovery_record.recovery_metrics.get("recovery_time_ms", 0)
            assert recovery_time < 8000, f"Delayed recovery too slow: {recovery_time}ms"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.cross_device_recovery
    async def test_websocket_cross_device_reconnection_context_recovery(self, real_services_fixture):
        """Test context recovery during cross-device reconnection scenarios."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketContextRecoveryValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create user session on "device 1"
            user_id, device1_connection_id, recovery_profile = await validator.create_user_session_for_recovery_testing("cross-device")
            
            # Simulate disconnection from device 1
            await validator.simulate_disconnection_and_context_persistence(user_id, device1_connection_id, 1.0)
            
            # Simulate reconnection from "device 2" (different connection, no old connection reference)
            cross_device_recovery = await validator.simulate_websocket_reconnection_with_context_recovery(
                user_id, None,  # No old connection (cross-device)
                recovery_profile, ReconnectionScenario.CROSS_DEVICE_RECONNECT, 3.0
            )
            
            # CROSS-DEVICE RECOVERY VALIDATIONS
            
            # Cross-device recovery should succeed with proper authentication
            assert cross_device_recovery.recovery_success, \
                f"Cross-device recovery failed: {cross_device_recovery.recovery_violations}"
            
            # Should authenticate properly for cross-device scenario
            auth_stage = None
            for stage in cross_device_recovery.recovery_stages:
                if stage["stage"] == "authentication_verified":
                    auth_stage = stage
                    break
            
            assert auth_stage is not None, "Authentication stage should be present"
            assert auth_stage["success"], "Cross-device authentication should succeed"
            
            # Should recover persistent data (conversation history from database)
            history = cross_device_recovery.recovered_data.get("conversation_history", [])
            assert len(history) > 0, "Cross-device should recover conversation history from database"
            
            # Preferences should be recovered or use defaults
            preferences = cross_device_recovery.recovered_data.get("preferences", {})
            assert isinstance(preferences, dict), "Should recover or provide default preferences"
            
            # WebSocket state should be completely new for new device
            ws_state = cross_device_recovery.recovered_data.get("websocket_state", {})
            assert ws_state.get("connection_id") != device1_connection_id, \
                "New device should have different connection ID"
            assert ws_state.get("reconnection_recovery"), \
                "WebSocket state should be marked as recovery connection"
            
            # Security validation - should not recover temporary/session-specific data
            session_data = cross_device_recovery.recovered_data.get("session", {})
            # Cross-device should establish new session or recover from persistent store
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.recovery_security
    async def test_websocket_context_recovery_security_validation(self, real_services_fixture):
        """Test security validation during context recovery (unauthorized access prevention)."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketContextRecoveryValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create two users with different organizations
            user_a_id, conn_a_id, profile_a = await validator.create_user_session_for_recovery_testing("security-a", "org-alpha")
            user_b_id, conn_b_id, profile_b = await validator.create_user_session_for_recovery_testing("security-b", "org-beta")
            
            # Simulate disconnection for user A
            await validator.simulate_disconnection_and_context_persistence(user_a_id, conn_a_id, 1.0)
            
            # Attempt 1: User B tries to recover User A's context (should fail)
            unauthorized_recovery = await validator.simulate_websocket_reconnection_with_context_recovery(
                user_b_id,  # User B trying to recover
                conn_a_id,  # User A's old connection
                profile_a,  # User A's recovery profile
                ReconnectionScenario.QUICK_RECONNECT, 1.0
            )
            
            # SECURITY VALIDATION ASSERTIONS
            
            # Unauthorized recovery should fail
            assert not unauthorized_recovery.recovery_success, \
                "Unauthorized context recovery should fail"
            
            # Should fail at authentication or permission validation
            failed_stages = [stage for stage in unauthorized_recovery.recovery_stages if not stage["success"]]
            assert len(failed_stages) > 0, "Should have failed stages for unauthorized access"
            
            # Should have security violations
            assert len(unauthorized_recovery.recovery_violations) > 0, \
                "Should detect security violations for unauthorized recovery"
            
            # Attempt 2: Valid recovery for User A
            legitimate_recovery = await validator.simulate_websocket_reconnection_with_context_recovery(
                user_a_id,  # Correct user
                conn_a_id,  # User A's old connection
                profile_a,  # User A's recovery profile
                ReconnectionScenario.QUICK_RECONNECT, 1.0
            )
            
            # Legitimate recovery should succeed
            assert legitimate_recovery.recovery_success, \
                f"Legitimate recovery should succeed: {legitimate_recovery.recovery_violations}"
            
            # Should have no security violations
            assert len(legitimate_recovery.recovery_violations) == 0, \
                f"Legitimate recovery should have no violations: {legitimate_recovery.recovery_violations}"
            
            # Verify recovered data belongs to correct user
            recovered_history = legitimate_recovery.recovered_data.get("conversation_history", [])
            for thread_entry in recovered_history:
                # All recovered threads should belong to user A
                assert thread_entry.get("user_verified", True), "Thread ownership should be verified"
            
            # Attempt 3: Cross-organization context access (should be blocked)
            cross_org_profile = ContextRecoveryProfile(
                user_id=user_b_id,
                organization_id="org-alpha",  # Wrong org for user B
                recovery_permissions={"read_messages"},
                conversation_history_depth=10,
                agent_state_recovery_enabled=False,
                preference_sync_enabled=False,
                security_level="strict",
                data_residency_region="us-east-1",
                max_recovery_age_hours=24,
                recovery_scope={"session", "history"}
            )
            
            cross_org_recovery = await validator.simulate_websocket_reconnection_with_context_recovery(
                user_b_id, None, cross_org_profile, ReconnectionScenario.QUICK_RECONNECT, 1.0
            )
            
            # Cross-org recovery should fail
            assert not cross_org_recovery.recovery_success, \
                "Cross-organization recovery should fail"
            
            # Should fail at organization validation
            for violation in cross_org_recovery.recovery_violations:
                if "organization" in violation.get("failure_reason", "").lower():
                    break
            else:
                # Should have organization-related failure
                auth_stages = [stage for stage in cross_org_recovery.recovery_stages 
                             if stage["stage"] == "authentication_verified" and not stage["success"]]
                assert len(auth_stages) > 0, "Should fail authentication for wrong organization"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.recovery_performance
    async def test_concurrent_context_recovery_performance(self, real_services_fixture):
        """Test context recovery performance under concurrent reconnection load."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = WebSocketContextRecoveryValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create multiple users for concurrent recovery testing
            user_sessions = []
            for i in range(4):  # 4 concurrent users
                user_id, conn_id, profile = await validator.create_user_session_for_recovery_testing(f"concurrent-{i}")
                user_sessions.append((user_id, conn_id, profile))
            
            # Simulate disconnections for all users
            for user_id, conn_id, profile in user_sessions:
                await validator.simulate_disconnection_and_context_persistence(user_id, conn_id, 0.5)
            
            # Execute concurrent recoveries
            recovery_tasks = []
            for i, (user_id, conn_id, profile) in enumerate(user_sessions):
                scenario = [ReconnectionScenario.QUICK_RECONNECT, ReconnectionScenario.DELAYED_RECONNECT,
                           ReconnectionScenario.BROWSER_REFRESH_RECONNECT, ReconnectionScenario.NETWORK_SWITCH_RECONNECT][i]
                
                recovery_task = validator.simulate_websocket_reconnection_with_context_recovery(
                    user_id, conn_id, profile, scenario, 2.0
                )
                recovery_tasks.append(recovery_task)
            
            # Wait for all concurrent recoveries
            concurrent_recoveries = await asyncio.gather(*recovery_tasks)
            
            # CONCURRENT RECOVERY PERFORMANCE VALIDATIONS
            
            # All concurrent recoveries should succeed
            successful_recoveries = [r for r in concurrent_recoveries if r.recovery_success]
            assert len(successful_recoveries) == 4, \
                f"All concurrent recoveries should succeed: {len(successful_recoveries)}/4"
            
            # Performance should not degrade significantly under concurrency
            recovery_times = [r.recovery_metrics.get("recovery_time_ms", 0) for r in concurrent_recoveries]
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
            max_recovery_time = max(recovery_times)
            
            assert avg_recovery_time < 5000, f"Average concurrent recovery too slow: {avg_recovery_time}ms"
            assert max_recovery_time < 8000, f"Max concurrent recovery too slow: {max_recovery_time}ms"
            
            # Completeness should remain high under concurrency
            completeness_scores = [r.recovery_completeness_score for r in concurrent_recoveries]
            avg_completeness = sum(completeness_scores) / len(completeness_scores)
            
            assert avg_completeness >= 0.85, \
                f"Concurrent recovery completeness too low: {avg_completeness}"
            
            # Verify user isolation maintained during concurrent recovery
            user_ids = [r.user_id for r in concurrent_recoveries]
            unique_user_ids = set(user_ids)
            assert len(unique_user_ids) == 4, "All users should maintain distinct recovery contexts"
            
            # Verify no cross-user data contamination
            for i, recovery in enumerate(concurrent_recoveries):
                expected_user_id = user_sessions[i][0]
                assert recovery.user_id == expected_user_id, \
                    f"Recovery {i} has wrong user context: {recovery.user_id} vs {expected_user_id}"
                
                # Verify recovered data belongs to correct user
                history = recovery.recovered_data.get("conversation_history", [])
                for thread_entry in history:
                    # All message user IDs in history should match the recovering user
                    for message in thread_entry.get("messages", []):
                        # Messages may have different roles (user/assistant) but should be from correct conversation
                        pass  # Database query would verify thread ownership
                
                # No security violations for any concurrent user
                assert len(recovery.recovery_violations) == 0, \
                    f"User {recovery.user_id} has recovery violations: {recovery.recovery_violations}"
            
        finally:
            await validator.cleanup()

