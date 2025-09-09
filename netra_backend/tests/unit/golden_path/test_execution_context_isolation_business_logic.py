"""
Test Execution Context Isolation Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Multi-user system foundation
- Business Goal: Ensure complete user isolation prevents data leakage and cross-contamination
- Value Impact: Context isolation enables concurrent users = scalable $500K+ ARR growth
- Strategic Impact: Data leakage between users = immediate customer trust destruction = platform failure

This test validates core execution context isolation algorithms that power:
1. User execution context factory patterns for complete isolation
2. Session-based data segregation and cleanup
3. Agent execution context inheritance and scoping
4. Memory and state isolation between concurrent users
5. Error boundary isolation preventing cascading failures

CRITICAL BUSINESS RULES:
- Each user execution MUST have completely isolated context
- No shared state between users (memory, cache, database sessions)
- Context cleanup MUST be automatic and complete on session end
- Agent execution contexts inherit user isolation boundaries
- Failed executions MUST NOT contaminate other user contexts
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor

from shared.types.core_types import UserID, SessionID, RunID, AgentID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

# Business Logic Classes (SSOT for execution context isolation)

class IsolationLevel(Enum):
    PROCESS = "process"        # Complete process isolation
    THREAD = "thread"          # Thread-level isolation
    SESSION = "session"        # Session-based isolation
    USER = "user"             # User-level isolation

class ContextState(Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLEANING_UP = "cleaning_up"
    TERMINATED = "terminated"

@dataclass
class IsolatedResource:
    """Individual isolated resource within execution context."""
    resource_id: str
    resource_type: str
    owner_user_id: str
    owner_session_id: str
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    cleanup_registered: bool = False

@dataclass
class ExecutionBoundary:
    """Execution boundary that defines isolation scope."""
    boundary_id: str
    user_id: str
    session_id: str
    isolation_level: IsolationLevel
    resource_limits: Dict[str, int]
    allowed_operations: Set[str]
    created_at: datetime
    expires_at: Optional[datetime] = None

@dataclass
class ContextIsolationMetrics:
    """Metrics for context isolation monitoring."""
    total_contexts: int
    active_contexts: int
    isolated_resources: int
    cross_contamination_incidents: int
    cleanup_failures: int
    average_isolation_overhead_ms: float
    memory_isolation_efficiency: float

class UserExecutionContextFactory:
    """
    SSOT User Execution Context Factory
    
    This class implements the factory pattern for creating completely isolated
    user execution contexts - critical for multi-user platform scalability.
    """
    
    # ISOLATION CONFIGURATION
    ISOLATION_BOUNDARIES = {
        IsolationLevel.PROCESS: {
            'memory_separation': True,
            'database_connection_pool': True,
            'cache_namespace': True,
            'file_system_sandboxing': True,
            'network_isolation': False  # Shared network access
        },
        IsolationLevel.THREAD: {
            'memory_separation': False,  # Shared memory space
            'database_connection_pool': True,
            'cache_namespace': True,
            'file_system_sandboxing': True,
            'network_isolation': False
        },
        IsolationLevel.SESSION: {
            'memory_separation': False,
            'database_connection_pool': False,  # Shared connection pool
            'cache_namespace': True,
            'file_system_sandboxing': False,
            'network_isolation': False
        },
        IsolationLevel.USER: {
            'memory_separation': False,
            'database_connection_pool': False,
            'cache_namespace': True,
            'file_system_sandboxing': False,
            'network_isolation': False
        }
    }
    
    # RESOURCE LIMITS BY CONTEXT
    DEFAULT_RESOURCE_LIMITS = {
        'max_memory_mb': 512,
        'max_execution_time_seconds': 300,
        'max_concurrent_agents': 5,
        'max_database_connections': 10,
        'max_cache_entries': 1000
    }
    
    def __init__(self):
        self._active_contexts: Dict[str, StronglyTypedUserExecutionContext] = {}
        self._resource_registry: Dict[str, IsolatedResource] = {}
        self._cleanup_callbacks: Dict[str, List[callable]] = {}
        self._isolation_lock = threading.Lock()

    def create_isolated_context(self, user_id: str, session_id: str, 
                              isolation_level: IsolationLevel = IsolationLevel.SESSION,
                              resource_limits: Optional[Dict[str, int]] = None) -> StronglyTypedUserExecutionContext:
        """
        Create completely isolated execution context for user.
        
        Critical: Each context MUST be completely isolated from others.
        """
        with self._isolation_lock:
            context_id = str(uuid.uuid4())
            
            # Apply resource limits
            effective_limits = self.DEFAULT_RESOURCE_LIMITS.copy()
            if resource_limits:
                effective_limits.update(resource_limits)
            
            # Create execution boundary
            boundary = ExecutionBoundary(
                boundary_id=context_id,
                user_id=user_id,
                session_id=session_id,
                isolation_level=isolation_level,
                resource_limits=effective_limits,
                allowed_operations=self._determine_allowed_operations(user_id),
                created_at=datetime.now(timezone.utc)
            )
            
            # Initialize isolated resources
            isolated_resources = self._initialize_isolated_resources(boundary)
            
            # Create context
            context = StronglyTypedUserExecutionContext(
                user_id=UserID(user_id),
                session_id=SessionID(session_id),
                run_id=RunID(str(uuid.uuid4())),
                context_metadata={
                    'boundary_id': context_id,
                    'isolation_level': isolation_level.value,
                    'resource_limits': effective_limits,
                    'isolated_resources': {r.resource_id: r.resource_type for r in isolated_resources}
                },
                execution_state=ContextState.INITIALIZING.value
            )
            
            # Register context and resources
            self._active_contexts[context_id] = context
            for resource in isolated_resources:
                self._resource_registry[resource.resource_id] = resource
            
            # Register cleanup callback
            self._register_cleanup_callback(context_id, lambda: self._cleanup_context(context_id))
            
            context.execution_state = ContextState.ACTIVE.value
            
            return context

    def validate_context_isolation(self, context_id: str) -> Dict[str, Any]:
        """
        Validate that context maintains proper isolation.
        
        Critical for preventing cross-user data contamination.
        """
        if context_id not in self._active_contexts:
            return {'valid': False, 'reason': 'context_not_found'}
        
        context = self._active_contexts[context_id]
        boundary_id = context.context_metadata['boundary_id']
        
        validation_results = {
            'valid': True,
            'isolation_violations': [],
            'resource_leaks': [],
            'cross_contamination_risks': [],
            'cleanup_status': 'not_required'
        }
        
        # Check for resource leaks
        user_resources = [r for r in self._resource_registry.values() 
                         if r.owner_user_id == context.user_id.value]
        
        for resource in user_resources:
            # Check if resource is properly scoped
            if not resource.cleanup_registered:
                validation_results['resource_leaks'].append(
                    f"Resource {resource.resource_id} not registered for cleanup"
                )
            
            # Check access patterns
            if resource.access_count == 0:
                validation_results['resource_leaks'].append(
                    f"Unused resource {resource.resource_id} consuming memory"
                )
        
        # Check for cross-contamination risks
        same_session_contexts = [ctx for ctx in self._active_contexts.values()
                               if ctx.session_id == context.session_id and 
                               ctx.context_metadata['boundary_id'] != boundary_id]
        
        if len(same_session_contexts) > 0:
            validation_results['cross_contamination_risks'].append(
                f"Multiple contexts in same session: {len(same_session_contexts) + 1}"
            )
        
        # Update validation status
        has_violations = (len(validation_results['isolation_violations']) > 0 or
                         len(validation_results['resource_leaks']) > 0 or
                         len(validation_results['cross_contamination_risks']) > 0)
        
        validation_results['valid'] = not has_violations
        
        return validation_results

    def cleanup_context(self, context_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Clean up execution context and all associated resources.
        
        Critical: Must be complete and prevent resource leaks.
        """
        cleanup_results = {
            'success': False,
            'resources_cleaned': 0,
            'cleanup_failures': [],
            'cleanup_time_ms': 0
        }
        
        start_time = datetime.now(timezone.utc)
        
        try:
            with self._isolation_lock:
                if context_id not in self._active_contexts:
                    cleanup_results['cleanup_failures'].append('Context not found')
                    return cleanup_results
                
                context = self._active_contexts[context_id]
                context.execution_state = ContextState.CLEANING_UP.value
                
                # Clean up all resources owned by this context
                user_id = context.user_id.value
                session_id = context.session_id.value
                
                resources_to_cleanup = [
                    r for r in self._resource_registry.values()
                    if r.owner_user_id == user_id and r.owner_session_id == session_id
                ]
                
                for resource in resources_to_cleanup:
                    try:
                        self._cleanup_resource(resource)
                        cleanup_results['resources_cleaned'] += 1
                        del self._resource_registry[resource.resource_id]
                    except Exception as e:
                        cleanup_results['cleanup_failures'].append(
                            f"Failed to cleanup resource {resource.resource_id}: {str(e)}"
                        )
                
                # Execute registered cleanup callbacks
                if context_id in self._cleanup_callbacks:
                    for callback in self._cleanup_callbacks[context_id]:
                        try:
                            callback()
                        except Exception as e:
                            cleanup_results['cleanup_failures'].append(
                                f"Cleanup callback failed: {str(e)}"
                            )
                    del self._cleanup_callbacks[context_id]
                
                # Remove context
                context.execution_state = ContextState.TERMINATED.value
                del self._active_contexts[context_id]
                
                cleanup_results['success'] = len(cleanup_results['cleanup_failures']) == 0
                
        except Exception as e:
            cleanup_results['cleanup_failures'].append(f"Critical cleanup error: {str(e)}")
        
        finally:
            end_time = datetime.now(timezone.utc)
            cleanup_results['cleanup_time_ms'] = (end_time - start_time).total_seconds() * 1000
        
        return cleanup_results

    def detect_isolation_violations(self, context_ids: List[str]) -> Dict[str, List[str]]:
        """
        Detect isolation violations between contexts.
        
        Critical for maintaining multi-user data integrity.
        """
        violations = {
            'shared_resources': [],
            'memory_contamination': [],
            'session_bleeding': [],
            'user_boundary_violations': []
        }
        
        contexts = [self._active_contexts.get(cid) for cid in context_ids if cid in self._active_contexts]
        
        # Check for shared resources
        user_resources = {}
        for context in contexts:
            user_id = context.user_id.value
            if user_id not in user_resources:
                user_resources[user_id] = []
            
            context_resources = context.context_metadata.get('isolated_resources', {})
            user_resources[user_id].extend(context_resources.keys())
        
        # Detect resource sharing between users
        all_resource_ids = []
        for resources in user_resources.values():
            all_resource_ids.extend(resources)
        
        resource_counts = {}
        for resource_id in all_resource_ids:
            resource_counts[resource_id] = resource_counts.get(resource_id, 0) + 1
        
        shared_resources = [rid for rid, count in resource_counts.items() if count > 1]
        violations['shared_resources'] = shared_resources
        
        # Check for session bleeding
        session_users = {}
        for context in contexts:
            session_id = context.session_id.value
            user_id = context.user_id.value
            
            if session_id not in session_users:
                session_users[session_id] = set()
            session_users[session_id].add(user_id)
        
        # Sessions should only have one user
        for session_id, users in session_users.items():
            if len(users) > 1:
                violations['session_bleeding'].append(
                    f"Session {session_id} has multiple users: {users}"
                )
        
        return violations

    def calculate_isolation_overhead(self, context_id: str) -> Dict[str, float]:
        """
        Calculate overhead introduced by isolation mechanisms.
        
        Used for performance optimization and resource planning.
        """
        if context_id not in self._active_contexts:
            return {'error': 'context_not_found'}
        
        context = self._active_contexts[context_id]
        isolation_level = IsolationLevel(context.context_metadata['isolation_level'])
        boundary_config = self.ISOLATION_BOUNDARIES[isolation_level]
        
        # Calculate overhead based on isolation mechanisms
        base_overhead_ms = 0.0
        
        if boundary_config['memory_separation']:
            base_overhead_ms += 10.0  # Memory separation overhead
        
        if boundary_config['database_connection_pool']:
            base_overhead_ms += 5.0   # Connection pool overhead
        
        if boundary_config['cache_namespace']:
            base_overhead_ms += 2.0   # Cache namespace overhead
        
        if boundary_config['file_system_sandboxing']:
            base_overhead_ms += 8.0   # File system overhead
        
        # Factor in number of isolated resources
        resource_count = len(context.context_metadata.get('isolated_resources', {}))
        resource_overhead = resource_count * 0.5  # 0.5ms per resource
        
        total_overhead = base_overhead_ms + resource_overhead
        
        return {
            'base_isolation_overhead_ms': base_overhead_ms,
            'resource_overhead_ms': resource_overhead,
            'total_overhead_ms': total_overhead,
            'isolation_level': isolation_level.value,
            'resource_count': resource_count
        }

    def generate_isolation_metrics(self) -> ContextIsolationMetrics:
        """
        Generate comprehensive isolation metrics for monitoring.
        
        Critical for operational visibility and optimization.
        """
        with self._isolation_lock:
            total_contexts = len(self._active_contexts)
            active_contexts = len([ctx for ctx in self._active_contexts.values() 
                                 if ctx.execution_state == ContextState.ACTIVE.value])
            
            total_resources = len(self._resource_registry)
            
            # Calculate average overhead
            overhead_measurements = []
            for context_id in self._active_contexts.keys():
                overhead = self.calculate_isolation_overhead(context_id)
                if 'total_overhead_ms' in overhead:
                    overhead_measurements.append(overhead['total_overhead_ms'])
            
            avg_overhead = sum(overhead_measurements) / len(overhead_measurements) if overhead_measurements else 0.0
            
            # Detect contamination incidents (simplified)
            violations = self.detect_isolation_violations(list(self._active_contexts.keys()))
            contamination_incidents = sum(len(v) for v in violations.values())
            
            return ContextIsolationMetrics(
                total_contexts=total_contexts,
                active_contexts=active_contexts,
                isolated_resources=total_resources,
                cross_contamination_incidents=contamination_incidents,
                cleanup_failures=0,  # Would be tracked in real implementation
                average_isolation_overhead_ms=avg_overhead,
                memory_isolation_efficiency=0.95  # Placeholder - would measure actual efficiency
            )

    # PRIVATE HELPER METHODS

    def _determine_allowed_operations(self, user_id: str) -> Set[str]:
        """Determine allowed operations for user based on permissions."""
        # In real implementation, this would check user permissions/tier
        return {
            'agent_execution', 'data_access', 'cache_read', 'cache_write',
            'database_read', 'database_write', 'file_read', 'file_write'
        }

    def _initialize_isolated_resources(self, boundary: ExecutionBoundary) -> List[IsolatedResource]:
        """Initialize isolated resources for execution boundary."""
        resources = []
        
        # Create database connection resource
        db_resource = IsolatedResource(
            resource_id=f"db_conn_{boundary.boundary_id}",
            resource_type="database_connection",
            owner_user_id=boundary.user_id,
            owner_session_id=boundary.session_id,
            created_at=datetime.now(timezone.utc),
            last_accessed=datetime.now(timezone.utc),
            cleanup_registered=True
        )
        resources.append(db_resource)
        
        # Create cache namespace resource
        cache_resource = IsolatedResource(
            resource_id=f"cache_ns_{boundary.boundary_id}",
            resource_type="cache_namespace",
            owner_user_id=boundary.user_id,
            owner_session_id=boundary.session_id,
            created_at=datetime.now(timezone.utc),
            last_accessed=datetime.now(timezone.utc),
            cleanup_registered=True
        )
        resources.append(cache_resource)
        
        # Create memory allocation resource
        memory_resource = IsolatedResource(
            resource_id=f"memory_alloc_{boundary.boundary_id}",
            resource_type="memory_allocation",
            owner_user_id=boundary.user_id,
            owner_session_id=boundary.session_id,
            created_at=datetime.now(timezone.utc),
            last_accessed=datetime.now(timezone.utc),
            cleanup_registered=True
        )
        resources.append(memory_resource)
        
        return resources

    def _cleanup_resource(self, resource: IsolatedResource):
        """Clean up individual isolated resource."""
        # Simulate cleanup based on resource type
        if resource.resource_type == "database_connection":
            # Close database connection
            pass
        elif resource.resource_type == "cache_namespace":
            # Clear cache namespace
            pass
        elif resource.resource_type == "memory_allocation":
            # Free memory allocation
            pass
        
        # Update resource status
        resource.last_accessed = datetime.now(timezone.utc)

    def _register_cleanup_callback(self, context_id: str, callback: callable):
        """Register cleanup callback for context."""
        if context_id not in self._cleanup_callbacks:
            self._cleanup_callbacks[context_id] = []
        self._cleanup_callbacks[context_id].append(callback)

    def _cleanup_context(self, context_id: str):
        """Internal cleanup method."""
        # This would be called automatically on context termination
        pass


class TestExecutionContextIsolationBusinessLogic:
    """Test execution context isolation business logic for multi-user platform."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.factory = UserExecutionContextFactory()
        self.test_user_1 = str(uuid.uuid4())
        self.test_user_2 = str(uuid.uuid4())
        self.test_session_1 = str(uuid.uuid4())
        self.test_session_2 = str(uuid.uuid4())

    # CONTEXT CREATION TESTS

    def test_create_isolated_context_successful(self):
        """Test successful creation of isolated execution context."""
        context = self.factory.create_isolated_context(
            user_id=self.test_user_1,
            session_id=self.test_session_1,
            isolation_level=IsolationLevel.SESSION
        )
        
        assert context.user_id.value == self.test_user_1
        assert context.session_id.value == self.test_session_1
        assert context.execution_state == ContextState.ACTIVE.value
        assert 'boundary_id' in context.context_metadata
        assert 'isolated_resources' in context.context_metadata

    def test_create_multiple_contexts_different_users(self):
        """Test creating multiple contexts for different users."""
        context1 = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        context2 = self.factory.create_isolated_context(self.test_user_2, self.test_session_2)
        
        # Contexts should be completely separate
        assert context1.user_id != context2.user_id
        assert context1.session_id != context2.session_id
        assert context1.context_metadata['boundary_id'] != context2.context_metadata['boundary_id']
        
        # Each should have their own resources
        resources1 = context1.context_metadata['isolated_resources']
        resources2 = context2.context_metadata['isolated_resources']
        
        # No shared resource IDs
        shared_resources = set(resources1.keys()) & set(resources2.keys())
        assert len(shared_resources) == 0

    def test_create_context_with_custom_resource_limits(self):
        """Test context creation with custom resource limits."""
        custom_limits = {
            'max_memory_mb': 256,
            'max_execution_time_seconds': 120,
            'max_concurrent_agents': 3
        }
        
        context = self.factory.create_isolated_context(
            user_id=self.test_user_1,
            session_id=self.test_session_1,
            resource_limits=custom_limits
        )
        
        context_limits = context.context_metadata['resource_limits']
        
        assert context_limits['max_memory_mb'] == 256
        assert context_limits['max_execution_time_seconds'] == 120
        assert context_limits['max_concurrent_agents'] == 3

    def test_isolation_level_configuration(self):
        """Test different isolation levels create appropriate configurations."""
        session_context = self.factory.create_isolated_context(
            self.test_user_1, self.test_session_1, IsolationLevel.SESSION
        )
        
        thread_context = self.factory.create_isolated_context(
            self.test_user_2, self.test_session_2, IsolationLevel.THREAD
        )
        
        assert session_context.context_metadata['isolation_level'] == 'session'
        assert thread_context.context_metadata['isolation_level'] == 'thread'

    # CONTEXT VALIDATION TESTS

    def test_validate_healthy_context_isolation(self):
        """Test validation of healthy context with proper isolation."""
        context = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        context_id = context.context_metadata['boundary_id']
        
        validation = self.factory.validate_context_isolation(context_id)
        
        assert validation['valid'] is True
        assert len(validation['isolation_violations']) == 0
        assert len(validation['resource_leaks']) == 0

    def test_validate_nonexistent_context(self):
        """Test validation of nonexistent context."""
        fake_context_id = str(uuid.uuid4())
        
        validation = self.factory.validate_context_isolation(fake_context_id)
        
        assert validation['valid'] is False
        assert validation['reason'] == 'context_not_found'

    def test_detect_resource_leaks(self):
        """Test detection of resource leaks in context validation."""
        context = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        context_id = context.context_metadata['boundary_id']
        
        # Manually create an unregistered resource to simulate leak
        leaked_resource = IsolatedResource(
            resource_id="leaked_resource",
            resource_type="database_connection",
            owner_user_id=self.test_user_1,
            owner_session_id=self.test_session_1,
            created_at=datetime.now(timezone.utc),
            last_accessed=datetime.now(timezone.utc),
            cleanup_registered=False  # Not registered for cleanup
        )
        self.factory._resource_registry["leaked_resource"] = leaked_resource
        
        validation = self.factory.validate_context_isolation(context_id)
        
        # Should detect the resource leak
        assert len(validation['resource_leaks']) > 0
        assert any("not registered for cleanup" in leak for leak in validation['resource_leaks'])

    # CONTEXT CLEANUP TESTS

    def test_successful_context_cleanup(self):
        """Test successful cleanup of execution context."""
        context = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        context_id = context.context_metadata['boundary_id']
        
        cleanup_result = self.factory.cleanup_context(context_id)
        
        assert cleanup_result['success'] is True
        assert cleanup_result['resources_cleaned'] > 0
        assert len(cleanup_result['cleanup_failures']) == 0
        
        # Context should be removed
        assert context_id not in self.factory._active_contexts

    def test_cleanup_nonexistent_context(self):
        """Test cleanup of nonexistent context."""
        fake_context_id = str(uuid.uuid4())
        
        cleanup_result = self.factory.cleanup_context(fake_context_id)
        
        assert cleanup_result['success'] is False
        assert 'Context not found' in cleanup_result['cleanup_failures']

    def test_context_cleanup_timing(self):
        """Test that context cleanup completes within reasonable time."""
        context = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        context_id = context.context_metadata['boundary_id']
        
        cleanup_result = self.factory.cleanup_context(context_id)
        
        # Should complete cleanup quickly (under 100ms for test scenario)
        assert cleanup_result['cleanup_time_ms'] < 100

    def test_cleanup_removes_all_user_resources(self):
        """Test that cleanup removes all resources owned by user."""
        context = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        context_id = context.context_metadata['boundary_id']
        
        # Count resources before cleanup
        user_resources_before = [
            r for r in self.factory._resource_registry.values()
            if r.owner_user_id == self.test_user_1
        ]
        
        cleanup_result = self.factory.cleanup_context(context_id)
        
        # Count resources after cleanup
        user_resources_after = [
            r for r in self.factory._resource_registry.values()
            if r.owner_user_id == self.test_user_1
        ]
        
        assert len(user_resources_before) > 0  # Had resources
        assert len(user_resources_after) == 0  # All cleaned up
        assert cleanup_result['resources_cleaned'] == len(user_resources_before)

    # ISOLATION VIOLATION DETECTION TESTS

    def test_detect_no_violations_separate_users(self):
        """Test that separate user contexts show no isolation violations."""
        context1 = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        context2 = self.factory.create_isolated_context(self.test_user_2, self.test_session_2)
        
        context_ids = [
            context1.context_metadata['boundary_id'],
            context2.context_metadata['boundary_id']
        ]
        
        violations = self.factory.detect_isolation_violations(context_ids)
        
        assert len(violations['shared_resources']) == 0
        assert len(violations['memory_contamination']) == 0
        assert len(violations['session_bleeding']) == 0
        assert len(violations['user_boundary_violations']) == 0

    def test_detect_session_bleeding(self):
        """Test detection of session bleeding between users."""
        # Create contexts with same session but different users (violation)
        shared_session = str(uuid.uuid4())
        
        context1 = self.factory.create_isolated_context(self.test_user_1, shared_session)
        context2 = self.factory.create_isolated_context(self.test_user_2, shared_session)
        
        context_ids = [
            context1.context_metadata['boundary_id'],
            context2.context_metadata['boundary_id']
        ]
        
        violations = self.factory.detect_isolation_violations(context_ids)
        
        # Should detect session bleeding
        assert len(violations['session_bleeding']) > 0
        assert shared_session in violations['session_bleeding'][0]

    def test_detect_shared_resources_violation(self):
        """Test detection of shared resources between contexts."""
        context1 = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        context2 = self.factory.create_isolated_context(self.test_user_2, self.test_session_2)
        
        # Manually create a shared resource violation
        shared_resource_id = "shared_violation"
        context1.context_metadata['isolated_resources'][shared_resource_id] = "database_connection"
        context2.context_metadata['isolated_resources'][shared_resource_id] = "database_connection"
        
        context_ids = [
            context1.context_metadata['boundary_id'],
            context2.context_metadata['boundary_id']
        ]
        
        violations = self.factory.detect_isolation_violations(context_ids)
        
        assert shared_resource_id in violations['shared_resources']

    # ISOLATION OVERHEAD CALCULATION TESTS

    def test_calculate_isolation_overhead_session_level(self):
        """Test isolation overhead calculation for session-level isolation."""
        context = self.factory.create_isolated_context(
            self.test_user_1, self.test_session_1, IsolationLevel.SESSION
        )
        context_id = context.context_metadata['boundary_id']
        
        overhead = self.factory.calculate_isolation_overhead(context_id)
        
        assert 'total_overhead_ms' in overhead
        assert overhead['isolation_level'] == 'session'
        assert overhead['total_overhead_ms'] > 0
        assert overhead['resource_count'] > 0

    def test_calculate_isolation_overhead_thread_level(self):
        """Test that thread-level isolation has higher overhead than session-level."""
        session_context = self.factory.create_isolated_context(
            self.test_user_1, self.test_session_1, IsolationLevel.SESSION
        )
        
        thread_context = self.factory.create_isolated_context(
            self.test_user_2, self.test_session_2, IsolationLevel.THREAD
        )
        
        session_overhead = self.factory.calculate_isolation_overhead(
            session_context.context_metadata['boundary_id']
        )
        
        thread_overhead = self.factory.calculate_isolation_overhead(
            thread_context.context_metadata['boundary_id']
        )
        
        # Thread isolation should have higher base overhead
        assert thread_overhead['base_isolation_overhead_ms'] > session_overhead['base_isolation_overhead_ms']

    def test_isolation_overhead_scales_with_resources(self):
        """Test that isolation overhead scales with number of resources."""
        # Create context with more resources by using higher isolation level
        process_context = self.factory.create_isolated_context(
            self.test_user_1, self.test_session_1, IsolationLevel.PROCESS
        )
        
        session_context = self.factory.create_isolated_context(
            self.test_user_2, self.test_session_2, IsolationLevel.SESSION
        )
        
        process_overhead = self.factory.calculate_isolation_overhead(
            process_context.context_metadata['boundary_id']
        )
        
        session_overhead = self.factory.calculate_isolation_overhead(
            session_context.context_metadata['boundary_id']
        )
        
        # Process isolation should have higher total overhead
        assert process_overhead['total_overhead_ms'] > session_overhead['total_overhead_ms']

    # ISOLATION METRICS TESTS

    def test_generate_isolation_metrics_empty_state(self):
        """Test isolation metrics generation with no active contexts."""
        metrics = self.factory.generate_isolation_metrics()
        
        assert metrics.total_contexts == 0
        assert metrics.active_contexts == 0
        assert metrics.isolated_resources == 0
        assert metrics.cross_contamination_incidents == 0

    def test_generate_isolation_metrics_with_contexts(self):
        """Test isolation metrics generation with active contexts."""
        context1 = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        context2 = self.factory.create_isolated_context(self.test_user_2, self.test_session_2)
        
        metrics = self.factory.generate_isolation_metrics()
        
        assert metrics.total_contexts == 2
        assert metrics.active_contexts == 2
        assert metrics.isolated_resources > 0
        assert metrics.average_isolation_overhead_ms > 0

    def test_metrics_track_contamination_incidents(self):
        """Test that metrics properly track contamination incidents."""
        # Create contexts with violation
        shared_session = str(uuid.uuid4())
        context1 = self.factory.create_isolated_context(self.test_user_1, shared_session)
        context2 = self.factory.create_isolated_context(self.test_user_2, shared_session)
        
        metrics = self.factory.generate_isolation_metrics()
        
        # Should detect the contamination incident
        assert metrics.cross_contamination_incidents > 0

    # CONCURRENT ACCESS TESTS

    def test_concurrent_context_creation_thread_safety(self):
        """Test thread safety of concurrent context creation."""
        results = []
        
        def create_context(user_index):
            user_id = f"user_{user_index}"
            session_id = f"session_{user_index}"
            context = self.factory.create_isolated_context(user_id, session_id)
            results.append(context)
        
        # Create contexts concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_context, i) for i in range(10)]
            for future in futures:
                future.result()  # Wait for completion
        
        assert len(results) == 10
        
        # All contexts should be unique
        context_ids = [ctx.context_metadata['boundary_id'] for ctx in results]
        assert len(set(context_ids)) == 10  # All unique

    def test_concurrent_context_cleanup_thread_safety(self):
        """Test thread safety of concurrent context cleanup."""
        # Create multiple contexts
        contexts = []
        for i in range(5):
            context = self.factory.create_isolated_context(f"user_{i}", f"session_{i}")
            contexts.append(context)
        
        cleanup_results = []
        
        def cleanup_context(context):
            context_id = context.context_metadata['boundary_id']
            result = self.factory.cleanup_context(context_id)
            cleanup_results.append(result)
        
        # Cleanup concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(cleanup_context, ctx) for ctx in contexts]
            for future in futures:
                future.result()  # Wait for completion
        
        assert len(cleanup_results) == 5
        
        # All cleanups should be successful
        successful_cleanups = sum(1 for result in cleanup_results if result['success'])
        assert successful_cleanups == 5

    # BUSINESS RULE VALIDATION TESTS

    def test_isolation_boundaries_configuration(self):
        """Test that isolation boundaries are properly configured."""
        boundaries = self.factory.ISOLATION_BOUNDARIES
        
        # All isolation levels should be configured
        for level in IsolationLevel:
            assert level in boundaries
            
            config = boundaries[level]
            assert 'memory_separation' in config
            assert 'database_connection_pool' in config
            assert 'cache_namespace' in config

    def test_default_resource_limits_are_reasonable(self):
        """Test that default resource limits are set to reasonable values."""
        limits = self.factory.DEFAULT_RESOURCE_LIMITS
        
        assert limits['max_memory_mb'] > 0
        assert limits['max_execution_time_seconds'] > 0
        assert limits['max_concurrent_agents'] > 0
        assert limits['max_database_connections'] > 0
        assert limits['max_cache_entries'] > 0

    def test_context_state_transitions(self):
        """Test that context states transition properly."""
        context = self.factory.create_isolated_context(self.test_user_1, self.test_session_1)
        
        # Should start as ACTIVE
        assert context.execution_state == ContextState.ACTIVE.value
        
        # Cleanup should transition through CLEANING_UP to TERMINATED
        context_id = context.context_metadata['boundary_id']
        self.factory.cleanup_context(context_id)
        
        # Context should be terminated and removed
        assert context_id not in self.factory._active_contexts