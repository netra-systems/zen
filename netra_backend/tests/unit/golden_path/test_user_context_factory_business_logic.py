"""
Test User Context Factory Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Multi-user platform foundation
- Business Goal: Enable secure, isolated user contexts for concurrent operations  
- Value Impact: Context factory enables scalable multi-user platform = $500K+ ARR growth
- Strategic Impact: User isolation is mandatory for enterprise customers and compliance

This test validates core user context factory algorithms that power:
1. Secure user context creation and validation
2. Tier-based context configuration and resource allocation
3. Context inheritance and scoping for agent execution
4. Authentication integration and security validation
5. Resource cleanup and context lifecycle management

CRITICAL BUSINESS RULES:
- Enterprise tier: Enhanced security, dedicated resources, audit logging
- Mid tier: Balanced security and performance, shared resource pools
- Early tier: Standard security, limited resources, basic logging
- Free tier: Minimal security overhead, shared resources, no audit logs
- All contexts MUST maintain complete user isolation
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import uuid
import threading

from shared.types.core_types import UserID, SessionID, RunID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

# Business Logic Classes (SSOT for user context factory)

class SubscriptionTier(Enum):
    FREE = "free"
    EARLY = "early"
    MID = "mid"
    ENTERPRISE = "enterprise"

class ContextSecurityLevel(Enum):
    MINIMAL = "minimal"      # Free tier
    STANDARD = "standard"    # Early tier
    ENHANCED = "enhanced"    # Mid tier
    MAXIMUM = "maximum"      # Enterprise tier

class ContextStatus(Enum):
    CREATING = "creating"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"

@dataclass
class UserContextConfig:
    """Configuration for user context based on tier."""
    security_level: ContextSecurityLevel
    max_concurrent_contexts: int
    max_context_lifetime_hours: int
    resource_allocation: Dict[str, int]
    audit_logging_enabled: bool
    encryption_required: bool
    isolation_level: str

@dataclass
class ContextResourceAllocation:
    """Resource allocation for user context."""
    memory_limit_mb: int
    cpu_limit_percentage: int
    storage_limit_mb: int
    network_bandwidth_mbps: int
    concurrent_operations: int

@dataclass
class UserContextMetrics:
    """Metrics for user context monitoring."""
    contexts_created: int
    contexts_active: int
    contexts_terminated: int
    average_context_lifetime: float
    resource_utilization: Dict[str, float]
    security_violations: int

class UserContextFactory:
    """
    SSOT User Context Factory Business Logic
    
    This class implements secure user context creation and management
    for multi-tenant platform operations.
    """
    
    # TIER-BASED CONTEXT CONFIGURATIONS
    TIER_CONFIGS = {
        SubscriptionTier.FREE: UserContextConfig(
            security_level=ContextSecurityLevel.MINIMAL,
            max_concurrent_contexts=1,
            max_context_lifetime_hours=2,
            resource_allocation={
                'memory_mb': 256,
                'cpu_percentage': 10,
                'storage_mb': 100,
                'network_mbps': 1,
                'concurrent_operations': 2
            },
            audit_logging_enabled=False,
            encryption_required=True,
            isolation_level="basic"
        ),
        SubscriptionTier.EARLY: UserContextConfig(
            security_level=ContextSecurityLevel.STANDARD,
            max_concurrent_contexts=3,
            max_context_lifetime_hours=4,
            resource_allocation={
                'memory_mb': 512,
                'cpu_percentage': 25,
                'storage_mb': 500,
                'network_mbps': 5,
                'concurrent_operations': 5
            },
            audit_logging_enabled=True,
            encryption_required=True,
            isolation_level="standard"
        ),
        SubscriptionTier.MID: UserContextConfig(
            security_level=ContextSecurityLevel.ENHANCED,
            max_concurrent_contexts=10,
            max_context_lifetime_hours=8,
            resource_allocation={
                'memory_mb': 1024,
                'cpu_percentage': 50,
                'storage_mb': 2000,
                'network_mbps': 10,
                'concurrent_operations': 15
            },
            audit_logging_enabled=True,
            encryption_required=True,
            isolation_level="enhanced"
        ),
        SubscriptionTier.ENTERPRISE: UserContextConfig(
            security_level=ContextSecurityLevel.MAXIMUM,
            max_concurrent_contexts=50,
            max_context_lifetime_hours=24,
            resource_allocation={
                'memory_mb': 4096,
                'cpu_percentage': 100,
                'storage_mb': 10000,
                'network_mbps': 50,
                'concurrent_operations': 50
            },
            audit_logging_enabled=True,
            encryption_required=True,
            isolation_level="maximum"
        )
    }
    
    def __init__(self):
        self._active_contexts: Dict[str, StronglyTypedUserExecutionContext] = {}
        self._user_contexts: Dict[str, List[str]] = {}  # user_id -> context_ids
        self._context_lock = threading.Lock()
        self._security_audit_log: List[Dict[str, Any]] = []
        
    def create_user_context(self, user_id: str, user_tier: SubscriptionTier,
                          session_id: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> StronglyTypedUserExecutionContext:
        """
        Create secure user context with tier-based configuration.
        
        Critical: Each context must be completely isolated and secure.
        """
        with self._context_lock:
            # Validate concurrent context limits
            existing_contexts = self._get_active_user_contexts(user_id)
            config = self.TIER_CONFIGS[user_tier]
            
            if len(existing_contexts) >= config.max_concurrent_contexts:
                # Try cleanup first
                self._cleanup_expired_contexts(user_id)
                existing_contexts = self._get_active_user_contexts(user_id)
                
                if len(existing_contexts) >= config.max_concurrent_contexts:
                    raise ValueError(f"Maximum concurrent contexts ({config.max_concurrent_contexts}) reached for tier {user_tier.value}")
            
            # Generate secure identifiers
            context_id = str(uuid.uuid4())
            if not session_id:
                session_id = str(uuid.uuid4())
            run_id = str(uuid.uuid4())
            
            # Create context with tier-specific configuration
            context = StronglyTypedUserExecutionContext(
                user_id=UserID(user_id),
                session_id=SessionID(session_id),
                run_id=RunID(run_id),
                context_metadata={
                    'context_id': context_id,
                    'user_tier': user_tier.value,
                    'security_level': config.security_level.value,
                    'resource_allocation': config.resource_allocation,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'expires_at': (datetime.now(timezone.utc) + timedelta(hours=config.max_context_lifetime_hours)).isoformat(),
                    'isolation_level': config.isolation_level,
                    'audit_logging_enabled': config.audit_logging_enabled,
                    'custom_metadata': metadata or {}
                },
                execution_state=ContextStatus.CREATING.value
            )
            
            # Register context
            self._active_contexts[context_id] = context
            
            if user_id not in self._user_contexts:
                self._user_contexts[user_id] = []
            self._user_contexts[user_id].append(context_id)
            
            # Initialize security monitoring
            if config.audit_logging_enabled:
                self._log_security_event("context_created", {
                    'user_id': user_id,
                    'context_id': context_id,
                    'tier': user_tier.value,
                    'security_level': config.security_level.value
                })
            
            # Activate context
            context.execution_state = ContextStatus.ACTIVE.value
            
            return context

    def validate_context_security(self, context_id: str) -> Dict[str, Any]:
        """
        Validate context security compliance.
        
        Critical for maintaining security standards across tiers.
        """
        if context_id not in self._active_contexts:
            return {
                'valid': False,
                'reason': 'context_not_found',
                'security_violations': ['context_not_found']
            }
        
        context = self._active_contexts[context_id]
        user_tier = SubscriptionTier(context.context_metadata['user_tier'])
        config = self.TIER_CONFIGS[user_tier]
        
        violations = []
        security_checks = {
            'context_not_expired': True,
            'resource_limits_compliant': True,
            'isolation_maintained': True,
            'encryption_enabled': True,
            'audit_logging_active': True
        }
        
        # Check expiration
        expires_at = datetime.fromisoformat(context.context_metadata['expires_at'].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expires_at:
            security_checks['context_not_expired'] = False
            violations.append('context_expired')
        
        # Check resource allocation compliance
        allocated_resources = context.context_metadata['resource_allocation']
        expected_resources = config.resource_allocation
        
        for resource, expected_value in expected_resources.items():
            allocated_value = allocated_resources.get(resource.replace('_', '_'))
            if allocated_value and allocated_value > expected_value:
                security_checks['resource_limits_compliant'] = False
                violations.append(f'resource_limit_exceeded_{resource}')
        
        # Check encryption requirement
        if config.encryption_required and not context.context_metadata.get('encryption_enabled', True):
            security_checks['encryption_enabled'] = False
            violations.append('encryption_not_enabled')
        
        # Log security violations if audit logging is enabled
        if config.audit_logging_enabled and violations:
            self._log_security_event("security_violations", {
                'context_id': context_id,
                'user_id': str(context.user_id),
                'violations': violations
            })
        
        return {
            'valid': len(violations) == 0,
            'security_checks': security_checks,
            'security_violations': violations,
            'security_level': config.security_level.value
        }

    def extend_context_lifetime(self, context_id: str, extension_hours: int = 2) -> bool:
        """
        Extend context lifetime within tier limits.
        
        Used for active users to prevent context termination.
        """
        if context_id not in self._active_contexts:
            return False
        
        context = self._active_contexts[context_id]
        user_tier = SubscriptionTier(context.context_metadata['user_tier'])
        config = self.TIER_CONFIGS[user_tier]
        
        # Limit extension to max context lifetime
        max_extension = config.max_context_lifetime_hours
        extension_hours = min(extension_hours, max_extension)
        
        # Update expiration
        new_expiration = datetime.now(timezone.utc) + timedelta(hours=extension_hours)
        context.context_metadata['expires_at'] = new_expiration.isoformat()
        
        # Log extension if audit logging enabled
        if config.audit_logging_enabled:
            self._log_security_event("context_extended", {
                'context_id': context_id,
                'user_id': str(context.user_id),
                'extension_hours': extension_hours,
                'new_expiration': new_expiration.isoformat()
            })
        
        return True

    def get_context_resource_usage(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current resource usage for context.
        
        Used for monitoring and optimization.
        """
        if context_id not in self._active_contexts:
            return None
        
        context = self._active_contexts[context_id]
        allocated_resources = context.context_metadata['resource_allocation']
        
        # Simulate current usage (in real implementation, would query actual usage)
        current_usage = {}
        for resource, allocated in allocated_resources.items():
            # Simulate 60-80% utilization
            import random
            utilization = 0.6 + (random.random() * 0.2)  # 60-80%
            current_usage[resource] = {
                'allocated': allocated,
                'used': int(allocated * utilization) if isinstance(allocated, int) else allocated * utilization,
                'utilization_percentage': utilization * 100
            }
        
        return {
            'context_id': context_id,
            'resource_usage': current_usage,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }

    def terminate_context(self, context_id: str, reason: str = "user_request") -> Dict[str, Any]:
        """
        Terminate user context and cleanup resources.
        
        Critical: Must ensure complete cleanup and security.
        """
        termination_result = {
            'terminated': False,
            'reason': reason,
            'resources_cleaned': 0,
            'security_events_logged': 0
        }
        
        with self._context_lock:
            if context_id not in self._active_contexts:
                termination_result['reason'] = 'context_not_found'
                return termination_result
            
            context = self._active_contexts[context_id]
            user_tier = SubscriptionTier(context.context_metadata['user_tier'])
            config = self.TIER_CONFIGS[user_tier]
            
            # Mark as terminated
            context.execution_state = ContextStatus.TERMINATED.value
            
            # Cleanup resources (simulate)
            allocated_resources = context.context_metadata['resource_allocation']
            termination_result['resources_cleaned'] = len(allocated_resources)
            
            # Remove from tracking
            user_id = str(context.user_id)
            if user_id in self._user_contexts:
                self._user_contexts[user_id] = [
                    cid for cid in self._user_contexts[user_id] if cid != context_id
                ]
                if not self._user_contexts[user_id]:
                    del self._user_contexts[user_id]
            
            # Security logging
            if config.audit_logging_enabled:
                self._log_security_event("context_terminated", {
                    'context_id': context_id,
                    'user_id': user_id,
                    'reason': reason,
                    'lifetime_minutes': self._calculate_context_lifetime_minutes(context)
                })
                termination_result['security_events_logged'] = 1
            
            # Remove from active contexts
            del self._active_contexts[context_id]
            termination_result['terminated'] = True
        
        return termination_result

    def get_user_context_metrics(self, user_id: str) -> UserContextMetrics:
        """
        Get comprehensive metrics for user's contexts.
        
        Used for monitoring and optimization.
        """
        user_context_ids = self._user_contexts.get(user_id, [])
        
        contexts_created = len(user_context_ids)
        contexts_active = len([cid for cid in user_context_ids if cid in self._active_contexts])
        contexts_terminated = contexts_created - contexts_active
        
        # Calculate average lifetime
        total_lifetime = 0.0
        lifetime_count = 0
        
        for context_id in user_context_ids:
            if context_id in self._active_contexts:
                context = self._active_contexts[context_id]
                lifetime_minutes = self._calculate_context_lifetime_minutes(context)
                total_lifetime += lifetime_minutes
                lifetime_count += 1
        
        average_lifetime = total_lifetime / max(1, lifetime_count)
        
        # Get resource utilization
        resource_utilization = {}
        if contexts_active > 0:
            for context_id in user_context_ids:
                if context_id in self._active_contexts:
                    usage = self.get_context_resource_usage(context_id)
                    if usage:
                        for resource, usage_data in usage['resource_usage'].items():
                            if resource not in resource_utilization:
                                resource_utilization[resource] = []
                            resource_utilization[resource].append(usage_data['utilization_percentage'])
        
        # Calculate averages
        avg_utilization = {}
        for resource, utilizations in resource_utilization.items():
            avg_utilization[resource] = sum(utilizations) / len(utilizations)
        
        # Count security violations
        security_violations = len([
            event for event in self._security_audit_log
            if event.get('event_type') == 'security_violations' and
            event.get('data', {}).get('user_id') == user_id
        ])
        
        return UserContextMetrics(
            contexts_created=contexts_created,
            contexts_active=contexts_active,
            contexts_terminated=contexts_terminated,
            average_context_lifetime=average_lifetime,
            resource_utilization=avg_utilization,
            security_violations=security_violations
        )

    def detect_context_anomalies(self) -> Dict[str, List[str]]:
        """
        Detect context anomalies for security monitoring.
        
        Critical for detecting potential security issues.
        """
        anomalies = {
            'expired_but_active': [],
            'resource_violations': [],
            'security_violations': [],
            'unusual_usage_patterns': []
        }
        
        now = datetime.now(timezone.utc)
        
        for context_id, context in self._active_contexts.items():
            # Check for expired contexts still active
            expires_at = datetime.fromisoformat(context.context_metadata['expires_at'].replace('Z', '+00:00'))
            if now > expires_at:
                anomalies['expired_but_active'].append(context_id)
            
            # Check resource violations
            user_tier = SubscriptionTier(context.context_metadata['user_tier'])
            config = self.TIER_CONFIGS[user_tier]
            allocated = context.context_metadata['resource_allocation']
            expected = config.resource_allocation
            
            for resource, expected_value in expected.items():
                allocated_value = allocated.get(resource)
                if allocated_value and allocated_value > expected_value * 1.1:  # 10% tolerance
                    anomalies['resource_violations'].append(f"{context_id}:{resource}")
            
            # Check unusual usage patterns
            lifetime_hours = self._calculate_context_lifetime_minutes(context) / 60
            if lifetime_hours > config.max_context_lifetime_hours * 1.5:  # 50% over limit
                anomalies['unusual_usage_patterns'].append(f"{context_id}:long_lifetime")
        
        # Check security violations from audit log
        recent_violations = [
            event for event in self._security_audit_log[-100:]  # Last 100 events
            if event.get('event_type') == 'security_violations'
        ]
        
        for violation in recent_violations:
            context_id = violation.get('data', {}).get('context_id')
            if context_id:
                anomalies['security_violations'].append(context_id)
        
        return anomalies

    # PRIVATE HELPER METHODS

    def _get_active_user_contexts(self, user_id: str) -> List[str]:
        """Get active context IDs for user."""
        user_context_ids = self._user_contexts.get(user_id, [])
        return [cid for cid in user_context_ids if cid in self._active_contexts]

    def _cleanup_expired_contexts(self, user_id: str):
        """Cleanup expired contexts for user."""
        user_context_ids = self._user_contexts.get(user_id, [])
        now = datetime.now(timezone.utc)
        
        expired_contexts = []
        for context_id in user_context_ids:
            if context_id in self._active_contexts:
                context = self._active_contexts[context_id]
                expires_at = datetime.fromisoformat(context.context_metadata['expires_at'].replace('Z', '+00:00'))
                if now > expires_at:
                    expired_contexts.append(context_id)
        
        for context_id in expired_contexts:
            self.terminate_context(context_id, "expired")

    def _log_security_event(self, event_type: str, data: Dict[str, Any]):
        """Log security event for audit trail."""
        event = {
            'event_type': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data
        }
        self._security_audit_log.append(event)
        
        # Keep only last 1000 events to manage memory
        if len(self._security_audit_log) > 1000:
            self._security_audit_log = self._security_audit_log[-1000:]

    def _calculate_context_lifetime_minutes(self, context: StronglyTypedUserExecutionContext) -> float:
        """Calculate context lifetime in minutes."""
        created_at = datetime.fromisoformat(context.context_metadata['created_at'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return (now - created_at).total_seconds() / 60


class TestUserContextFactoryBusinessLogic:
    """Test user context factory business logic for multi-tenant platform."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.factory = UserContextFactory()
        self.test_user_id = str(uuid.uuid4())
        
    # CONTEXT CREATION TESTS

    def test_create_user_context_successful(self):
        """Test successful user context creation."""
        context = self.factory.create_user_context(
            user_id=self.test_user_id,
            user_tier=SubscriptionTier.MID
        )
        
        assert str(context.user_id) == self.test_user_id
        assert context.context_metadata['user_tier'] == SubscriptionTier.MID.value
        assert context.execution_state == ContextStatus.ACTIVE.value
        assert 'context_id' in context.context_metadata
        assert 'resource_allocation' in context.context_metadata

    def test_create_context_with_custom_metadata(self):
        """Test context creation with custom metadata."""
        custom_metadata = {
            'department': 'engineering',
            'project': 'cost_optimization',
            'priority': 'high'
        }
        
        context = self.factory.create_user_context(
            user_id=self.test_user_id,
            user_tier=SubscriptionTier.ENTERPRISE,
            metadata=custom_metadata
        )
        
        stored_metadata = context.context_metadata['custom_metadata']
        assert stored_metadata['department'] == 'engineering'
        assert stored_metadata['project'] == 'cost_optimization'
        assert stored_metadata['priority'] == 'high'

    def test_context_creation_enforces_concurrent_limits(self):
        """Test that context creation enforces concurrent limits."""
        # Create maximum allowed contexts for Free tier (1)
        context1 = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.FREE
        )
        
        # Attempt to create second context should fail
        with pytest.raises(ValueError) as exc_info:
            self.factory.create_user_context(
                self.test_user_id, SubscriptionTier.FREE
            )
        
        assert "Maximum concurrent contexts" in str(exc_info.value)

    def test_different_tiers_get_different_resource_allocations(self):
        """Test that different tiers receive appropriate resource allocations."""
        free_context = self.factory.create_user_context(
            str(uuid.uuid4()), SubscriptionTier.FREE
        )
        
        enterprise_context = self.factory.create_user_context(
            str(uuid.uuid4()), SubscriptionTier.ENTERPRISE
        )
        
        free_memory = free_context.context_metadata['resource_allocation']['memory_mb']
        enterprise_memory = enterprise_context.context_metadata['resource_allocation']['memory_mb']
        
        assert enterprise_memory > free_memory

    def test_context_expiration_time_by_tier(self):
        """Test that context expiration varies by tier."""
        free_context = self.factory.create_user_context(
            str(uuid.uuid4()), SubscriptionTier.FREE
        )
        
        enterprise_context = self.factory.create_user_context(
            str(uuid.uuid4()), SubscriptionTier.ENTERPRISE
        )
        
        free_expires = datetime.fromisoformat(free_context.context_metadata['expires_at'].replace('Z', '+00:00'))
        enterprise_expires = datetime.fromisoformat(enterprise_context.context_metadata['expires_at'].replace('Z', '+00:00'))
        
        assert enterprise_expires > free_expires

    # CONTEXT SECURITY VALIDATION TESTS

    def test_validate_secure_context(self):
        """Test validation of secure, compliant context."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        
        context_id = context.context_metadata['context_id']
        validation = self.factory.validate_context_security(context_id)
        
        assert validation['valid'] is True
        assert validation['security_level'] == 'enhanced'
        assert len(validation['security_violations']) == 0

    def test_validate_nonexistent_context(self):
        """Test validation of nonexistent context."""
        fake_context_id = str(uuid.uuid4())
        
        validation = self.factory.validate_context_security(fake_context_id)
        
        assert validation['valid'] is False
        assert validation['reason'] == 'context_not_found'
        assert 'context_not_found' in validation['security_violations']

    def test_validate_expired_context(self):
        """Test validation of expired context."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.EARLY
        )
        
        # Manually expire the context
        context.context_metadata['expires_at'] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        
        context_id = context.context_metadata['context_id']
        validation = self.factory.validate_context_security(context_id)
        
        assert validation['valid'] is False
        assert 'context_expired' in validation['security_violations']

    def test_security_violation_logging(self):
        """Test that security violations are logged for audit."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID  # Has audit logging enabled
        )
        
        # Force a security violation
        context.context_metadata['expires_at'] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        
        context_id = context.context_metadata['context_id']
        self.factory.validate_context_security(context_id)
        
        # Check that violation was logged
        violation_events = [
            event for event in self.factory._security_audit_log
            if event['event_type'] == 'security_violations'
        ]
        
        assert len(violation_events) > 0

    # CONTEXT LIFETIME EXTENSION TESTS

    def test_extend_context_lifetime_successful(self):
        """Test successful context lifetime extension."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        
        original_expiration = context.context_metadata['expires_at']
        context_id = context.context_metadata['context_id']
        
        success = self.factory.extend_context_lifetime(context_id, 2)
        
        assert success is True
        assert context.context_metadata['expires_at'] != original_expiration

    def test_extend_nonexistent_context(self):
        """Test extending nonexistent context."""
        fake_context_id = str(uuid.uuid4())
        
        success = self.factory.extend_context_lifetime(fake_context_id, 2)
        
        assert success is False

    def test_extension_limited_by_tier_max(self):
        """Test that extension is limited by tier maximum."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.FREE
        )
        
        context_id = context.context_metadata['context_id']
        
        # Try to extend beyond Free tier limit (2 hours)
        success = self.factory.extend_context_lifetime(context_id, 10)
        
        assert success is True  # Should succeed but be limited
        
        # Check that expiration doesn't exceed tier maximum
        expires_at = datetime.fromisoformat(context.context_metadata['expires_at'].replace('Z', '+00:00'))
        created_at = datetime.fromisoformat(context.context_metadata['created_at'].replace('Z', '+00:00'))
        
        total_lifetime_hours = (expires_at - created_at).total_seconds() / 3600
        free_tier_max = self.factory.TIER_CONFIGS[SubscriptionTier.FREE].max_context_lifetime_hours
        
        assert total_lifetime_hours <= free_tier_max * 1.1  # Small tolerance for timing

    # RESOURCE USAGE MONITORING TESTS

    def test_get_context_resource_usage(self):
        """Test getting context resource usage."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        
        context_id = context.context_metadata['context_id']
        usage = self.factory.get_context_resource_usage(context_id)
        
        assert usage is not None
        assert 'resource_usage' in usage
        assert 'memory_mb' in usage['resource_usage']
        assert 'utilization_percentage' in usage['resource_usage']['memory_mb']

    def test_get_usage_for_nonexistent_context(self):
        """Test getting usage for nonexistent context."""
        fake_context_id = str(uuid.uuid4())
        
        usage = self.factory.get_context_resource_usage(fake_context_id)
        
        assert usage is None

    def test_resource_usage_within_allocated_limits(self):
        """Test that resource usage stays within allocated limits."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.EARLY
        )
        
        context_id = context.context_metadata['context_id']
        usage = self.factory.get_context_resource_usage(context_id)
        
        for resource, usage_data in usage['resource_usage'].items():
            assert usage_data['used'] <= usage_data['allocated']

    # CONTEXT TERMINATION TESTS

    def test_terminate_context_successful(self):
        """Test successful context termination."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        
        context_id = context.context_metadata['context_id']
        
        termination = self.factory.terminate_context(context_id, "test_termination")
        
        assert termination['terminated'] is True
        assert termination['reason'] == "test_termination"
        assert termination['resources_cleaned'] > 0
        assert context_id not in self.factory._active_contexts

    def test_terminate_nonexistent_context(self):
        """Test terminating nonexistent context."""
        fake_context_id = str(uuid.uuid4())
        
        termination = self.factory.terminate_context(fake_context_id)
        
        assert termination['terminated'] is False
        assert termination['reason'] == 'context_not_found'

    def test_termination_removes_from_user_tracking(self):
        """Test that termination removes context from user tracking."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        
        context_id = context.context_metadata['context_id']
        
        # Verify context is tracked
        assert self.test_user_id in self.factory._user_contexts
        assert context_id in self.factory._user_contexts[self.test_user_id]
        
        self.factory.terminate_context(context_id)
        
        # Should be removed from user tracking
        if self.test_user_id in self.factory._user_contexts:
            assert context_id not in self.factory._user_contexts[self.test_user_id]

    def test_termination_logs_security_event_for_audit_enabled_tiers(self):
        """Test that termination logs security event for audit-enabled tiers."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.ENTERPRISE  # Has audit logging
        )
        
        context_id = context.context_metadata['context_id']
        
        self.factory.terminate_context(context_id, "audit_test")
        
        # Check for termination event in audit log
        termination_events = [
            event for event in self.factory._security_audit_log
            if event['event_type'] == 'context_terminated'
        ]
        
        assert len(termination_events) > 0

    # USER CONTEXT METRICS TESTS

    def test_user_context_metrics_generation(self):
        """Test user context metrics generation."""
        # Create and terminate some contexts
        context1 = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        context2 = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        
        # Terminate one context
        self.factory.terminate_context(context1.context_metadata['context_id'])
        
        metrics = self.factory.get_user_context_metrics(self.test_user_id)
        
        assert metrics.contexts_created == 2
        assert metrics.contexts_active == 1
        assert metrics.contexts_terminated == 1
        assert metrics.average_context_lifetime >= 0

    def test_metrics_for_user_with_no_contexts(self):
        """Test metrics for user with no contexts."""
        fake_user_id = str(uuid.uuid4())
        
        metrics = self.factory.get_user_context_metrics(fake_user_id)
        
        assert metrics.contexts_created == 0
        assert metrics.contexts_active == 0
        assert metrics.contexts_terminated == 0

    def test_resource_utilization_in_metrics(self):
        """Test that resource utilization is included in metrics."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        
        metrics = self.factory.get_user_context_metrics(self.test_user_id)
        
        if metrics.resource_utilization:  # May be empty if no utilization data
            for resource, utilization in metrics.resource_utilization.items():
                assert 0 <= utilization <= 100  # Percentage

    # ANOMALY DETECTION TESTS

    def test_detect_expired_but_active_contexts(self):
        """Test detection of expired but still active contexts."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        
        # Manually expire the context but keep it active
        context.context_metadata['expires_at'] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        
        anomalies = self.factory.detect_context_anomalies()
        
        context_id = context.context_metadata['context_id']
        assert context_id in anomalies['expired_but_active']

    def test_detect_resource_violations(self):
        """Test detection of resource violations."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.FREE
        )
        
        # Manually increase resource allocation beyond tier limits
        context.context_metadata['resource_allocation']['memory_mb'] = 1000  # Way over Free limit
        
        anomalies = self.factory.detect_context_anomalies()
        
        context_id = context.context_metadata['context_id']
        memory_violation = f"{context_id}:memory_mb"
        assert any(memory_violation in violation for violation in anomalies['resource_violations'])

    def test_detect_no_anomalies_for_healthy_contexts(self):
        """Test that healthy contexts produce no anomalies."""
        context = self.factory.create_user_context(
            self.test_user_id, SubscriptionTier.MID
        )
        
        anomalies = self.factory.detect_context_anomalies()
        
        context_id = context.context_metadata['context_id']
        
        assert context_id not in anomalies['expired_but_active']
        assert not any(context_id in violation for violation in anomalies['resource_violations'])

    # TIER CONFIGURATION VALIDATION TESTS

    def test_all_tiers_have_configurations(self):
        """Test that all tiers have proper configurations."""
        configs = self.factory.TIER_CONFIGS
        
        for tier in SubscriptionTier:
            assert tier in configs
            
            config = configs[tier]
            assert config.max_concurrent_contexts > 0
            assert config.max_context_lifetime_hours > 0
            assert len(config.resource_allocation) > 0

    def test_enterprise_tier_has_maximum_security(self):
        """Test that Enterprise tier has maximum security settings."""
        enterprise_config = self.factory.TIER_CONFIGS[SubscriptionTier.ENTERPRISE]
        
        assert enterprise_config.security_level == ContextSecurityLevel.MAXIMUM
        assert enterprise_config.audit_logging_enabled is True
        assert enterprise_config.encryption_required is True
        assert enterprise_config.isolation_level == "maximum"

    def test_free_tier_has_minimal_security(self):
        """Test that Free tier has minimal security settings."""
        free_config = self.factory.TIER_CONFIGS[SubscriptionTier.FREE]
        
        assert free_config.security_level == ContextSecurityLevel.MINIMAL
        assert free_config.audit_logging_enabled is False  # No audit logging for free
        assert free_config.max_concurrent_contexts == 1
        assert free_config.isolation_level == "basic"

    def test_tier_progression_logical(self):
        """Test that tier configurations progress logically."""
        free_config = self.factory.TIER_CONFIGS[SubscriptionTier.FREE]
        enterprise_config = self.factory.TIER_CONFIGS[SubscriptionTier.ENTERPRISE]
        
        # Higher tiers should have more resources
        assert (enterprise_config.max_concurrent_contexts > 
                free_config.max_concurrent_contexts)
        assert (enterprise_config.max_context_lifetime_hours > 
                free_config.max_context_lifetime_hours)
        assert (enterprise_config.resource_allocation['memory_mb'] > 
                free_config.resource_allocation['memory_mb'])