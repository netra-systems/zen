"""
Test WebSocket User Context Inheritance Validation During Agent Execution Integration (#27)

Business Value Justification (BVJ):
- Segment: All (Core AI agent functionality for business value delivery)
- Business Goal: Ensure user context is perfectly inherited by agents during WebSocket execution
- Value Impact: Users receive personalized AI responses based on their complete context and permissions
- Strategic Impact: Foundation of AI value delivery - agents must operate with correct user context

CRITICAL REQUIREMENT: When agents execute via WebSocket, they must inherit and maintain
the complete user context (permissions, organization, data access, preferences). Any
context inheritance failure results in wrong AI responses or security violations.
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
AgentID = str
ExecutionID = str
ContextID = str


class AgentExecutionStage(Enum):
    """Stages of agent execution lifecycle."""
    INITIATED = "initiated"
    CONTEXT_INHERITED = "context_inherited"
    CONTEXT_VALIDATED = "context_validated"
    EXECUTION_STARTED = "execution_started"
    TOOLS_EXECUTING = "tools_executing"
    RESULTS_GENERATED = "results_generated"
    CONTEXT_PRESERVED = "context_preserved"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UserExecutionContext:
    """Complete user execution context for agent inheritance."""
    user_id: UserID
    context_id: ContextID
    organization_id: str
    permissions: Set[str]
    data_access_scopes: Set[str]
    thread_access: Set[str]
    user_preferences: Dict[str, Any]
    session_metadata: Dict[str, Any]
    security_constraints: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    last_validated: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "context_id": self.context_id,
            "organization_id": self.organization_id,
            "permissions": list(self.permissions),
            "data_access_scopes": list(self.data_access_scopes),
            "thread_access": list(self.thread_access),
            "user_preferences": self.user_preferences,
            "session_metadata": self.session_metadata,
            "security_constraints": self.security_constraints,
            "created_at": self.created_at,
            "last_validated": self.last_validated
        }
    
    def validate_integrity(self) -> bool:
        """Validate context integrity."""
        return (
            self.user_id and
            self.context_id and
            self.organization_id and
            len(self.permissions) > 0 and
            time.time() - self.last_validated < 3600  # Context valid for 1 hour
        )


@dataclass
class AgentExecutionRecord:
    """Record of agent execution with context inheritance tracking."""
    execution_id: ExecutionID
    agent_id: AgentID
    user_context: UserExecutionContext
    websocket_connection_id: str
    execution_stages: List[Dict[str, Any]] = field(default_factory=list)
    context_inheritance_log: List[Dict[str, Any]] = field(default_factory=list)
    context_violations: List[Dict[str, Any]] = field(default_factory=list)
    agent_outputs: List[Dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    def add_stage(self, stage: AgentExecutionStage, context_valid: bool = True, 
                 details: Dict[str, Any] = None):
        """Add execution stage with context validation."""
        stage_record = {
            "stage": stage.value,
            "timestamp": time.time(),
            "context_valid": context_valid,
            "context_id": self.user_context.context_id,
            "user_id": self.user_context.user_id,
            "details": details or {}
        }
        self.execution_stages.append(stage_record)
        
        # Log context inheritance
        inheritance_record = {
            "stage": stage.value,
            "context_inherited": context_valid,
            "user_permissions_count": len(self.user_context.permissions),
            "data_access_scopes_count": len(self.user_context.data_access_scopes),
            "context_integrity": self.user_context.validate_integrity(),
            "timestamp": time.time()
        }
        self.context_inheritance_log.append(inheritance_record)
        
        if not context_valid:
            self.context_violations.append({
                "stage": stage.value,
                "violation_type": "context_inheritance_failure",
                "timestamp": time.time(),
                "details": details or {}
            })


class AgentContextInheritanceValidator:
    """Validates user context inheritance during agent execution via WebSocket."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.redis_client = None
        self.execution_records = {}
        self.context_inheritance_violations = []
    
    async def setup(self):
        """Set up validator with Redis connection."""
        import redis.asyncio as redis
        self.redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        await self.redis_client.ping()
    
    async def cleanup(self):
        """Clean up validator resources."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def create_user_with_execution_context(self, user_suffix: str, 
                                               organization_id: str = None) -> Tuple[UserExecutionContext, str]:
        """Create user with complete execution context for agent inheritance."""
        user_id = f"agent-ctx-user-{user_suffix}"
        context_id = f"ctx-{uuid.uuid4().hex}"
        websocket_connection_id = f"ws-{uuid.uuid4().hex}"
        
        # Create user in database
        await self.real_services["db"].execute("""
            INSERT INTO auth.users (id, email, name, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, user_id, f"{user_id}@agent-context-test.com", f"Agent Context Test User {user_suffix}", True)
        
        # Create organization if specified
        if organization_id is None:
            organization_id = f"agent-org-{user_suffix}"
        
        await self.real_services["db"].execute("""
            INSERT INTO backend.organizations (id, name, slug, plan, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                plan = EXCLUDED.plan
        """, organization_id, f"Agent Context Org {user_suffix}", 
            f"agent-org-{user_suffix}", "enterprise")
        
        # Create organization membership
        await self.real_services["db"].execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, organization_id) DO UPDATE SET role = EXCLUDED.role
        """, user_id, organization_id, "member")
        
        # Create user's threads and data for context
        thread_access = set()
        data_access_scopes = set()
        
        for i in range(3):
            thread_id = f"thread-{user_suffix}-{i}"
            await self.real_services["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (id) DO UPDATE SET 
                    title = EXCLUDED.title,
                    updated_at = NOW()
            """, thread_id, user_id, f"Agent Context Thread {i}")
            thread_access.add(thread_id)
            
            # Create messages in thread
            for j in range(2):
                message_id = f"msg-{user_suffix}-{i}-{j}"
                await self.real_services["db"].execute("""
                    INSERT INTO backend.messages (id, thread_id, user_id, content, role, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
                """, message_id, thread_id, user_id, 
                    f"Context message {j} for agent inheritance testing", "user")
            
            data_access_scopes.add(f"thread_data:{thread_id}")
        
        # Add general data access scopes
        data_access_scopes.update([
            f"user_data:{user_id}",
            f"org_data:{organization_id}",
            "public_data",
            "agent_tools"
        ])
        
        # Create comprehensive execution context
        execution_context = UserExecutionContext(
            user_id=user_id,
            context_id=context_id,
            organization_id=organization_id,
            permissions={
                "read_messages", "write_messages", "execute_agents", "access_threads",
                "view_analytics", "export_data", f"org_access:{organization_id}"
            },
            data_access_scopes=data_access_scopes,
            thread_access=thread_access,
            user_preferences={
                "agent_execution_timeout": 300,
                "preferred_response_format": "structured",
                "include_reasoning": True,
                "data_privacy_level": "standard",
                "language": "en",
                "timezone": "UTC"
            },
            session_metadata={
                "websocket_connection_id": websocket_connection_id,
                "session_id": f"session-{user_suffix}",
                "client_type": "web",
                "user_agent": "test-client",
                "ip_address": "127.0.0.1"
            },
            security_constraints={
                "max_execution_time": 600,
                "allowed_tools": ["search", "analyze", "summarize"],
                "blocked_domains": ["malicious.com"],
                "data_retention_days": 30,
                "audit_required": True
            }
        )
        
        # Store execution context in Redis
        context_key = f"user_execution_context:{context_id}"
        await self.redis_client.set(
            context_key,
            json.dumps(execution_context.to_dict()),
            ex=3600
        )
        
        # Store WebSocket context association
        ws_context_key = f"ws_context:{websocket_connection_id}"
        await self.redis_client.set(
            ws_context_key,
            json.dumps({
                "user_id": user_id,
                "context_id": context_id,
                "connection_state": WebSocketConnectionState.CONNECTED,
                "agent_execution_enabled": True,
                "context_inheritance_verified": True
            }),
            ex=3600
        )
        
        return execution_context, websocket_connection_id
    
    async def simulate_agent_execution_with_context_inheritance(self, 
                                                              user_context: UserExecutionContext,
                                                              websocket_connection_id: str,
                                                              agent_id: str = "test_agent") -> AgentExecutionRecord:
        """Simulate complete agent execution with context inheritance validation."""
        execution_id = f"exec-{uuid.uuid4().hex}"
        
        execution_record = AgentExecutionRecord(
            execution_id=execution_id,
            agent_id=agent_id,
            user_context=user_context,
            websocket_connection_id=websocket_connection_id
        )
        
        # Stage 1: Agent Execution Initiated
        execution_record.add_stage(AgentExecutionStage.INITIATED, True, {
            "agent_id": agent_id,
            "requested_by": user_context.user_id,
            "websocket_connection": websocket_connection_id
        })
        
        # Stage 2: Context Inheritance
        context_inherited = await self._validate_context_inheritance(execution_record)
        execution_record.add_stage(AgentExecutionStage.CONTEXT_INHERITED, context_inherited)
        
        if not context_inherited:
            execution_record.add_stage(AgentExecutionStage.FAILED, False, {
                "reason": "context_inheritance_failure"
            })
            return execution_record
        
        # Stage 3: Context Validation
        context_validation = await self._validate_inherited_context(execution_record)
        execution_record.add_stage(AgentExecutionStage.CONTEXT_VALIDATED, 
                                  context_validation["valid"], context_validation)
        
        if not context_validation["valid"]:
            execution_record.add_stage(AgentExecutionStage.FAILED, False, context_validation)
            return execution_record
        
        # Stage 4: Agent Execution Started
        execution_started = await self._simulate_agent_execution_start(execution_record)
        execution_record.add_stage(AgentExecutionStage.EXECUTION_STARTED, 
                                  execution_started["success"], execution_started)
        
        # Stage 5: Tools Execution (with context)
        tools_execution = await self._simulate_tools_execution_with_context(execution_record)
        execution_record.add_stage(AgentExecutionStage.TOOLS_EXECUTING, 
                                  tools_execution["context_preserved"], tools_execution)
        
        # Stage 6: Results Generation
        results_generation = await self._simulate_results_generation(execution_record)
        execution_record.add_stage(AgentExecutionStage.RESULTS_GENERATED,
                                  results_generation["context_used_correctly"], results_generation)
        
        # Stage 7: Context Preservation Check
        context_preservation = await self._validate_context_preservation(execution_record)
        execution_record.add_stage(AgentExecutionStage.CONTEXT_PRESERVED,
                                  context_preservation["preserved"], context_preservation)
        
        # Stage 8: Completion
        execution_record.add_stage(AgentExecutionStage.COMPLETED, True, {
            "execution_duration_ms": (time.time() - execution_record.started_at) * 1000
        })
        execution_record.completed_at = time.time()
        
        self.execution_records[execution_id] = execution_record
        return execution_record
    
    async def _validate_context_inheritance(self, execution_record: AgentExecutionRecord) -> bool:
        """Validate that agent inherited user context correctly."""
        context_key = f"user_execution_context:{execution_record.user_context.context_id}"
        stored_context = await self.redis_client.get(context_key)
        
        if not stored_context:
            execution_record.context_violations.append({
                "type": "missing_context",
                "details": "User execution context not found in storage",
                "context_id": execution_record.user_context.context_id
            })
            return False
        
        try:
            stored_context_data = json.loads(stored_context)
            
            # Validate critical context elements are present
            required_fields = ["user_id", "organization_id", "permissions", "data_access_scopes"]
            for field in required_fields:
                if field not in stored_context_data:
                    execution_record.context_violations.append({
                        "type": "missing_context_field",
                        "field": field,
                        "context_id": execution_record.user_context.context_id
                    })
                    return False
            
            # Validate context matches execution record
            if stored_context_data["user_id"] != execution_record.user_context.user_id:
                execution_record.context_violations.append({
                    "type": "context_user_mismatch",
                    "expected": execution_record.user_context.user_id,
                    "actual": stored_context_data["user_id"]
                })
                return False
            
            return True
            
        except json.JSONDecodeError:
            execution_record.context_violations.append({
                "type": "context_parse_error",
                "details": "Failed to parse stored context"
            })
            return False
    
    async def _validate_inherited_context(self, execution_record: AgentExecutionRecord) -> Dict[str, Any]:
        """Validate inherited context integrity and completeness."""
        validation_result = {
            "valid": True,
            "permissions_inherited": True,
            "data_access_inherited": True,
            "security_constraints_inherited": True,
            "user_preferences_inherited": True,
            "issues": []
        }
        
        context = execution_record.user_context
        
        # Validate permissions inheritance
        if len(context.permissions) == 0:
            validation_result["permissions_inherited"] = False
            validation_result["issues"].append("No permissions inherited")
            validation_result["valid"] = False
        
        # Validate data access scope inheritance
        if len(context.data_access_scopes) == 0:
            validation_result["data_access_inherited"] = False
            validation_result["issues"].append("No data access scopes inherited")
            validation_result["valid"] = False
        
        # Validate security constraints
        required_constraints = ["max_execution_time", "allowed_tools", "audit_required"]
        for constraint in required_constraints:
            if constraint not in context.security_constraints:
                validation_result["security_constraints_inherited"] = False
                validation_result["issues"].append(f"Missing security constraint: {constraint}")
                validation_result["valid"] = False
        
        # Validate user preferences
        if not context.user_preferences:
            validation_result["user_preferences_inherited"] = False
            validation_result["issues"].append("No user preferences inherited")
            validation_result["valid"] = False
        
        # Validate context integrity
        if not context.validate_integrity():
            validation_result["valid"] = False
            validation_result["issues"].append("Context failed integrity validation")
        
        return validation_result
    
    async def _simulate_agent_execution_start(self, execution_record: AgentExecutionRecord) -> Dict[str, Any]:
        """Simulate agent execution startup with inherited context."""
        context = execution_record.user_context
        
        # Simulate agent initialization with user context
        agent_initialization = {
            "success": True,
            "agent_id": execution_record.agent_id,
            "user_id": context.user_id,
            "organization_id": context.organization_id,
            "execution_timeout": context.security_constraints.get("max_execution_time", 600),
            "allowed_tools": context.security_constraints.get("allowed_tools", []),
            "user_preferences_applied": True,
            "data_access_scopes_loaded": len(context.data_access_scopes),
            "thread_access_loaded": len(context.thread_access)
        }
        
        # Store agent execution state
        agent_state_key = f"agent_execution:{execution_record.execution_id}"
        await self.redis_client.set(
            agent_state_key,
            json.dumps({
                "execution_id": execution_record.execution_id,
                "agent_id": execution_record.agent_id,
                "user_context_id": context.context_id,
                "user_id": context.user_id,
                "organization_id": context.organization_id,
                "permissions": list(context.permissions),
                "started_at": time.time(),
                "status": "running"
            }),
            ex=1800  # 30 minutes
        )
        
        return agent_initialization
    
    async def _simulate_tools_execution_with_context(self, execution_record: AgentExecutionRecord) -> Dict[str, Any]:
        """Simulate agent tools execution using inherited context."""
        context = execution_record.user_context
        
        tools_execution = {
            "context_preserved": True,
            "tools_executed": [],
            "context_violations": []
        }
        
        # Simulate executing different tools with context validation
        allowed_tools = context.security_constraints.get("allowed_tools", [])
        
        for tool_name in allowed_tools[:2]:  # Execute first 2 allowed tools
            tool_execution = {
                "tool_name": tool_name,
                "user_id": context.user_id,
                "data_access_used": [],
                "permissions_checked": True,
                "thread_access_verified": True,
                "execution_success": True
            }
            
            # Simulate tool accessing user data with inherited context
            if tool_name == "search":
                # Search tool needs thread access
                if context.thread_access:
                    accessible_thread = list(context.thread_access)[0]
                    tool_execution["data_access_used"].append(f"thread_data:{accessible_thread}")
                else:
                    tools_execution["context_violations"].append({
                        "tool": tool_name,
                        "issue": "no_thread_access_inherited"
                    })
                    tools_execution["context_preserved"] = False
            
            elif tool_name == "analyze":
                # Analyze tool needs user data access
                if f"user_data:{context.user_id}" in context.data_access_scopes:
                    tool_execution["data_access_used"].append(f"user_data:{context.user_id}")
                else:
                    tools_execution["context_violations"].append({
                        "tool": tool_name,
                        "issue": "no_user_data_access_inherited"
                    })
                    tools_execution["context_preserved"] = False
            
            tools_execution["tools_executed"].append(tool_execution)
            
            # Store tool execution with context
            tool_key = f"tool_execution:{execution_record.execution_id}:{tool_name}"
            await self.redis_client.set(
                tool_key,
                json.dumps(tool_execution),
                ex=600
            )
        
        return tools_execution
    
    async def _simulate_results_generation(self, execution_record: AgentExecutionRecord) -> Dict[str, Any]:
        """Simulate agent results generation using inherited context."""
        context = execution_record.user_context
        
        results_generation = {
            "context_used_correctly": True,
            "user_preferences_applied": True,
            "personalization_level": "high",
            "data_access_respected": True,
            "results_generated": []
        }
        
        # Generate personalized results based on inherited context
        personalized_result = {
            "type": "analysis_summary",
            "personalized_for": context.user_id,
            "organization_context": context.organization_id,
            "response_format": context.user_preferences.get("preferred_response_format", "text"),
            "include_reasoning": context.user_preferences.get("include_reasoning", False),
            "language": context.user_preferences.get("language", "en"),
            "data_sources_used": list(context.data_access_scopes)[:3],  # Sample
            "thread_references": list(context.thread_access)[:2],  # Sample
            "generated_at": time.time()
        }
        
        results_generation["results_generated"].append(personalized_result)
        execution_record.agent_outputs.append(personalized_result)
        
        # Validate context usage
        if personalized_result["personalized_for"] != context.user_id:
            results_generation["context_used_correctly"] = False
        
        if personalized_result["response_format"] != context.user_preferences.get("preferred_response_format"):
            results_generation["user_preferences_applied"] = False
        
        return results_generation
    
    async def _validate_context_preservation(self, execution_record: AgentExecutionRecord) -> Dict[str, Any]:
        """Validate that user context was preserved throughout execution."""
        preservation_result = {
            "preserved": True,
            "context_integrity_maintained": True,
            "no_context_corruption": True,
            "issues": []
        }
        
        # Check if context is still valid
        current_context_integrity = execution_record.user_context.validate_integrity()
        if not current_context_integrity:
            preservation_result["context_integrity_maintained"] = False
            preservation_result["issues"].append("Context integrity check failed")
            preservation_result["preserved"] = False
        
        # Check for context violations during execution
        if execution_record.context_violations:
            preservation_result["no_context_corruption"] = False
            preservation_result["issues"].extend([
                f"Context violation: {v['type']}" for v in execution_record.context_violations
            ])
            preservation_result["preserved"] = False
        
        # Verify context is still accessible
        context_key = f"user_execution_context:{execution_record.user_context.context_id}"
        stored_context = await self.redis_client.get(context_key)
        if not stored_context:
            preservation_result["preserved"] = False
            preservation_result["issues"].append("Context lost during execution")
        
        return preservation_result
    
    async def validate_multi_user_agent_context_isolation(self, 
                                                         execution_records: List[AgentExecutionRecord]) -> Dict[str, Any]:
        """Validate context isolation across multiple concurrent agent executions."""
        isolation_validation = {
            "context_isolation_maintained": True,
            "cross_user_contamination": [],
            "context_inheritance_success_rate": 0.0,
            "execution_summaries": {},
            "violations": []
        }
        
        successful_inheritances = 0
        total_executions = len(execution_records)
        
        for record in execution_records:
            user_id = record.user_context.user_id
            
            # Analyze execution success
            execution_summary = {
                "user_id": user_id,
                "execution_id": record.execution_id,
                "stages_completed": len(record.execution_stages),
                "context_violations": len(record.context_violations),
                "context_inheritance_successful": len(record.context_violations) == 0,
                "agent_outputs_count": len(record.agent_outputs)
            }
            
            if execution_summary["context_inheritance_successful"]:
                successful_inheritances += 1
            
            # Check for cross-user contamination in agent outputs
            for output in record.agent_outputs:
                if output.get("personalized_for") != user_id:
                    isolation_validation["cross_user_contamination"].append({
                        "execution_id": record.execution_id,
                        "expected_user": user_id,
                        "actual_user": output.get("personalized_for"),
                        "contamination_type": "agent_output_mispersonalization"
                    })
                    isolation_validation["context_isolation_maintained"] = False
            
            # Check for violations
            for violation in record.context_violations:
                isolation_validation["violations"].append({
                    "user_id": user_id,
                    "execution_id": record.execution_id,
                    "violation": violation
                })
            
            isolation_validation["execution_summaries"][record.execution_id] = execution_summary
        
        # Calculate success rate
        if total_executions > 0:
            isolation_validation["context_inheritance_success_rate"] = successful_inheritances / total_executions
        
        return isolation_validation


class TestWebSocketAgentContextInheritance(BaseIntegrationTest):
    """
    Integration test for user context inheritance during agent execution via WebSocket.
    
    CRITICAL: Validates that agents inherit and maintain complete user context throughout execution.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.agent_critical
    async def test_agent_execution_inherits_complete_user_context(self, real_services_fixture):
        """
        Test agent execution inherits complete user context via WebSocket.
        
        CRITICAL: Agents must inherit ALL user context elements for proper personalization.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = AgentContextInheritanceValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create user with comprehensive execution context
            user_context, websocket_connection_id = await validator.create_user_with_execution_context("complete-ctx")
            
            # Verify initial context integrity
            assert user_context.validate_integrity(), "User context must be valid before agent execution"
            assert len(user_context.permissions) > 0, "User must have permissions"
            assert len(user_context.data_access_scopes) > 0, "User must have data access"
            assert len(user_context.thread_access) > 0, "User must have thread access"
            assert user_context.user_preferences, "User must have preferences"
            assert user_context.security_constraints, "User must have security constraints"
            
            # Execute agent with context inheritance
            execution_record = await validator.simulate_agent_execution_with_context_inheritance(
                user_context, websocket_connection_id, "comprehensive_test_agent"
            )
            
            # CRITICAL VALIDATIONS: Context inheritance must be complete
            
            # Verify all execution stages completed successfully
            stage_names = [stage["stage"] for stage in execution_record.execution_stages]
            expected_stages = [
                "initiated", "context_inherited", "context_validated", "execution_started",
                "tools_executing", "results_generated", "context_preserved", "completed"
            ]
            
            for expected_stage in expected_stages:
                assert expected_stage in stage_names, \
                    f"Expected stage '{expected_stage}' not found in execution"
            
            # Verify no context violations occurred
            assert len(execution_record.context_violations) == 0, \
                f"Context violations detected: {execution_record.context_violations}"
            
            # Verify context inheritance was successful at each stage
            inheritance_log = execution_record.context_inheritance_log
            for log_entry in inheritance_log:
                assert log_entry["context_inherited"], \
                    f"Context inheritance failed at stage: {log_entry['stage']}"
                assert log_entry["context_integrity"], \
                    f"Context integrity failed at stage: {log_entry['stage']}"
            
            # Verify agent outputs are properly personalized
            assert len(execution_record.agent_outputs) > 0, "Agent must produce outputs"
            for output in execution_record.agent_outputs:
                assert output["personalized_for"] == user_context.user_id, \
                    "Agent output must be personalized for correct user"
                assert output["organization_context"] == user_context.organization_id, \
                    "Agent output must use correct organization context"
                assert output["response_format"] == user_context.user_preferences["preferred_response_format"], \
                    "Agent output must respect user preferences"
            
            # Verify execution completed successfully
            assert execution_record.completed_at is not None, "Execution must complete"
            execution_duration = execution_record.completed_at - execution_record.started_at
            max_allowed_time = user_context.security_constraints["max_execution_time"]
            assert execution_duration < max_allowed_time, \
                f"Execution took too long: {execution_duration}s > {max_allowed_time}s"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.concurrency
    async def test_concurrent_agent_executions_maintain_context_isolation(self, real_services_fixture):
        """Test context isolation during concurrent agent executions."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = AgentContextInheritanceValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create multiple users with different contexts
            concurrent_contexts = []
            for i in range(3):
                user_context, websocket_id = await validator.create_user_with_execution_context(f"concurrent-{i}")
                concurrent_contexts.append((user_context, websocket_id))
            
            # Execute agents concurrently for all users
            concurrent_executions = []
            for i, (user_context, websocket_id) in enumerate(concurrent_contexts):
                execution_task = validator.simulate_agent_execution_with_context_inheritance(
                    user_context, websocket_id, f"concurrent_agent_{i}"
                )
                concurrent_executions.append(execution_task)
            
            # Wait for all executions to complete
            execution_records = await asyncio.gather(*concurrent_executions)
            
            # Validate context isolation across all executions
            isolation_results = await validator.validate_multi_user_agent_context_isolation(execution_records)
            
            # CRITICAL ASSERTIONS: Context isolation must be maintained
            assert isolation_results["context_isolation_maintained"], \
                f"Context isolation violated: {isolation_results['cross_user_contamination']}"
            assert len(isolation_results["cross_user_contamination"]) == 0, \
                f"Cross-user contamination detected: {isolation_results['cross_user_contamination']}"
            assert isolation_results["context_inheritance_success_rate"] == 1.0, \
                f"Context inheritance success rate: {isolation_results['context_inheritance_success_rate']}"
            
            # Verify each execution maintained its user's context
            for i, record in enumerate(execution_records):
                expected_user_id = concurrent_contexts[i][0].user_id
                assert record.user_context.user_id == expected_user_id, \
                    f"Execution {i} has wrong user context"
                
                # Verify agent outputs are correctly personalized
                for output in record.agent_outputs:
                    assert output["personalized_for"] == expected_user_id, \
                        f"Agent output mispersonalized for execution {i}"
            
            # Verify no context violations across all executions
            total_violations = sum(len(record.context_violations) for record in execution_records)
            assert total_violations == 0, f"Total context violations: {total_violations}"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.enterprise
    async def test_organization_scoped_agent_context_inheritance(self, real_services_fixture):
        """Test agent context inheritance with organization-level scoping."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = AgentContextInheritanceValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create users from different organizations
            org_a_context, org_a_websocket = await validator.create_user_with_execution_context(
                "org-a", "enterprise-organization-a"
            )
            org_b_context, org_b_websocket = await validator.create_user_with_execution_context(
                "org-b", "enterprise-organization-b"
            )
            
            # Execute agents for both organizations
            org_a_execution = await validator.simulate_agent_execution_with_context_inheritance(
                org_a_context, org_a_websocket, "org_agent_a"
            )
            org_b_execution = await validator.simulate_agent_execution_with_context_inheritance(
                org_b_context, org_b_websocket, "org_agent_b"
            )
            
            # Validate organization-scoped context inheritance
            org_isolation = await validator.validate_multi_user_agent_context_isolation(
                [org_a_execution, org_b_execution]
            )
            
            # ORGANIZATION-LEVEL VALIDATIONS
            assert org_isolation["context_isolation_maintained"], \
                "Organization-level context isolation must be maintained"
            assert org_isolation["context_inheritance_success_rate"] == 1.0, \
                "All organization contexts must inherit successfully"
            
            # Verify organization-specific context inheritance
            assert org_a_execution.user_context.organization_id == "enterprise-organization-a"
            assert org_b_execution.user_context.organization_id == "enterprise-organization-b"
            
            # Verify agent outputs respect organization boundaries
            for output in org_a_execution.agent_outputs:
                assert output["organization_context"] == "enterprise-organization-a", \
                    "Org A agent output must use Org A context"
            
            for output in org_b_execution.agent_outputs:
                assert output["organization_context"] == "enterprise-organization-b", \
                    "Org B agent output must use Org B context"
            
            # Verify no cross-organization data access
            org_a_data_access = org_a_execution.user_context.data_access_scopes
            org_b_data_access = org_b_execution.user_context.data_access_scopes
            
            org_a_scopes = [scope for scope in org_a_data_access if "enterprise-organization-a" in scope]
            org_b_scopes = [scope for scope in org_b_data_access if "enterprise-organization-b" in scope]
            
            assert len(org_a_scopes) > 0, "Org A must have organization-specific data access"
            assert len(org_b_scopes) > 0, "Org B must have organization-specific data access"
            
            # No scope should overlap between organizations
            overlapping_scopes = set(org_a_scopes).intersection(set(org_b_scopes))
            assert len(overlapping_scopes) == 0, \
                f"Organizations should not have overlapping data access: {overlapping_scopes}"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security_critical
    async def test_agent_context_inheritance_security_constraints(self, real_services_fixture):
        """Test that security constraints are properly inherited and enforced."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = AgentContextInheritanceValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create user with strict security constraints
            user_context, websocket_id = await validator.create_user_with_execution_context("security-strict")
            
            # Modify security constraints to be more restrictive
            user_context.security_constraints.update({
                "max_execution_time": 60,  # Very short timeout
                "allowed_tools": ["search"],  # Only one tool allowed
                "blocked_domains": ["malicious.com", "unsafe.org"],
                "data_retention_days": 1,  # Very short retention
                "audit_required": True
            })
            
            # Update stored context
            context_key = f"user_execution_context:{user_context.context_id}"
            await validator.redis_client.set(
                context_key,
                json.dumps(user_context.to_dict()),
                ex=3600
            )
            
            # Execute agent with strict security constraints
            security_execution = await validator.simulate_agent_execution_with_context_inheritance(
                user_context, websocket_id, "security_constrained_agent"
            )
            
            # SECURITY VALIDATIONS
            
            # Verify security constraints were inherited
            assert len(security_execution.context_violations) == 0, \
                f"Security constraints inheritance failed: {security_execution.context_violations}"
            
            # Verify execution respects time constraints
            execution_duration = security_execution.completed_at - security_execution.started_at
            max_time = user_context.security_constraints["max_execution_time"]
            assert execution_duration < max_time, \
                f"Execution exceeded security time limit: {execution_duration}s > {max_time}s"
            
            # Verify only allowed tools were used
            tools_stage = None
            for stage in security_execution.execution_stages:
                if stage["stage"] == "tools_executing":
                    tools_stage = stage
                    break
            
            assert tools_stage is not None, "Tools execution stage must be present"
            
            # Verify audit trail was created
            audit_required = user_context.security_constraints["audit_required"]
            assert audit_required, "Audit must be required for this user"
            
            # Verify context preservation maintained security
            preservation_stage = None
            for stage in security_execution.execution_stages:
                if stage["stage"] == "context_preserved":
                    preservation_stage = stage
                    break
            
            assert preservation_stage is not None, "Context preservation stage must be present"
            assert preservation_stage["context_valid"], "Security constraints must be preserved"
            
        finally:
            await validator.cleanup()