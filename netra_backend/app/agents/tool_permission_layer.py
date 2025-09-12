"""Unified Tool Permission Layer - Centralized security and access control for tools.

This module provides a comprehensive permission and security layer for tool execution,
separating security concerns from dispatch and execution logic.

Key Features:
- Role-based access control (RBAC) for tools
- User plan and feature flag based permissions
- Rate limiting and quota enforcement
- Security policy validation
- Audit logging and compliance tracking
- Dynamic permission evaluation
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PermissionResult(Enum):
    """Permission check results."""
    ALLOWED = "allowed"
    DENIED = "denied" 
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    INSUFFICIENT_PLAN = "insufficient_plan"
    MISSING_FEATURE = "missing_feature"
    POLICY_VIOLATION = "policy_violation"


class SecurityLevel(Enum):
    """Tool security levels."""
    PUBLIC = 0      # No restrictions
    BASIC = 1       # Basic authentication required
    STANDARD = 2    # Standard plan required
    PREMIUM = 3     # Premium plan required
    ADMIN = 4       # Admin privileges required
    SYSTEM = 5      # System-level access only


@dataclass
class ToolPermissionPolicy:
    """Tool permission policy definition."""
    tool_name: str
    security_level: SecurityLevel = SecurityLevel.BASIC
    required_roles: Set[str] = field(default_factory=set)
    required_features: Set[str] = field(default_factory=set)
    allowed_plans: Set[str] = field(default_factory=lambda: {"free", "basic", "premium", "enterprise"})
    
    # Rate limiting
    max_calls_per_minute: Optional[int] = None
    max_calls_per_hour: Optional[int] = None
    max_calls_per_day: Optional[int] = None
    
    # Resource limits
    max_concurrent_executions: Optional[int] = None
    max_execution_time_seconds: Optional[int] = None
    max_memory_mb: Optional[int] = None
    
    # Validation rules
    validation_rules: List[Callable[[Dict[str, Any]], bool]] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    created_by: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            'tool_name': self.tool_name,
            'security_level': self.security_level.name,
            'required_roles': list(self.required_roles),
            'required_features': list(self.required_features),
            'allowed_plans': list(self.allowed_plans),
            'max_calls_per_minute': self.max_calls_per_minute,
            'max_calls_per_hour': self.max_calls_per_hour,
            'max_calls_per_day': self.max_calls_per_day,
            'max_concurrent_executions': self.max_concurrent_executions,
            'max_execution_time_seconds': self.max_execution_time_seconds,
            'max_memory_mb': self.max_memory_mb,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }


@dataclass 
class UserContext:
    """User context for permission evaluation."""
    user_id: str
    plan_tier: str = "free"
    roles: Set[str] = field(default_factory=set)
    feature_flags: Dict[str, bool] = field(default_factory=dict)
    is_developer: bool = False
    is_admin: bool = False
    
    # Computed properties
    @property
    def security_clearance(self) -> SecurityLevel:
        """Get user's security clearance level."""
        if self.is_admin:
            return SecurityLevel.ADMIN
        elif "premium" in self.plan_tier.lower():
            return SecurityLevel.PREMIUM
        elif "basic" in self.plan_tier.lower():
            return SecurityLevel.STANDARD
        else:
            return SecurityLevel.BASIC


@dataclass
class PermissionCheckResult:
    """Result of permission check."""
    allowed: bool
    result: PermissionResult
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Rate limiting info
    calls_remaining: Optional[int] = None
    reset_time: Optional[datetime] = None
    
    # Policy info
    policy_applied: Optional[str] = None
    security_level_required: Optional[SecurityLevel] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'allowed': self.allowed,
            'result': self.result.value,
            'reason': self.reason,
            'metadata': self.metadata,
            'calls_remaining': self.calls_remaining,
            'reset_time': self.reset_time.isoformat() if self.reset_time else None,
            'policy_applied': self.policy_applied,
            'security_level_required': self.security_level_required.name if self.security_level_required else None
        }


class RateLimitTracker:
    """Rate limiting tracker for users and tools."""
    
    def __init__(self):
        self.call_history: Dict[str, deque] = defaultdict(deque)
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
    
    def _cleanup_old_entries(self) -> None:
        """Clean up old rate limit entries."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = current_time - 86400  # 24 hours ago
        
        for key in list(self.call_history.keys()):
            history = self.call_history[key]
            
            # Remove old entries
            while history and history[0] < cutoff_time:
                history.popleft()
            
            # Remove empty histories
            if not history:
                del self.call_history[key]
        
        self.last_cleanup = current_time
    
    def check_rate_limit(
        self,
        user_id: str,
        tool_name: str,
        max_per_minute: Optional[int] = None,
        max_per_hour: Optional[int] = None,
        max_per_day: Optional[int] = None
    ) -> tuple[bool, int, Optional[datetime]]:
        """Check if user is within rate limits for tool.
        
        Returns:
            (is_allowed, calls_remaining, reset_time)
        """
        self._cleanup_old_entries()
        
        key = f"{user_id}:{tool_name}"
        current_time = time.time()
        
        history = self.call_history[key]
        
        # Check limits in order of severity
        if max_per_minute:
            minute_ago = current_time - 60
            recent_calls = sum(1 for call_time in history if call_time > minute_ago)
            
            if recent_calls >= max_per_minute:
                reset_time = datetime.fromtimestamp(
                    min(call_time for call_time in history if call_time > minute_ago) + 60,
                    tz=timezone.utc
                )
                return False, 0, reset_time
        
        if max_per_hour:
            hour_ago = current_time - 3600
            recent_calls = sum(1 for call_time in history if call_time > hour_ago)
            
            if recent_calls >= max_per_hour:
                reset_time = datetime.fromtimestamp(
                    min(call_time for call_time in history if call_time > hour_ago) + 3600,
                    tz=timezone.utc
                )
                return False, max_per_hour - recent_calls, reset_time
        
        if max_per_day:
            day_ago = current_time - 86400
            recent_calls = sum(1 for call_time in history if call_time > day_ago)
            
            if recent_calls >= max_per_day:
                reset_time = datetime.fromtimestamp(
                    min(call_time for call_time in history if call_time > day_ago) + 86400,
                    tz=timezone.utc
                )
                return False, max_per_day - recent_calls, reset_time
        
        # Calculate remaining calls (using most restrictive limit)
        remaining = float('inf')
        reset_time = None
        
        if max_per_minute:
            minute_calls = sum(1 for call_time in history if call_time > current_time - 60)
            remaining = min(remaining, max_per_minute - minute_calls)
        
        if max_per_hour:
            hour_calls = sum(1 for call_time in history if call_time > current_time - 3600)
            remaining = min(remaining, max_per_hour - hour_calls)
        
        if max_per_day:
            day_calls = sum(1 for call_time in history if call_time > current_time - 86400)
            remaining = min(remaining, max_per_day - day_calls)
        
        return True, int(remaining) if remaining != float('inf') else None, reset_time
    
    def record_call(self, user_id: str, tool_name: str) -> None:
        """Record a tool call for rate limiting."""
        key = f"{user_id}:{tool_name}"
        self.call_history[key].append(time.time())


class ConcurrencyTracker:
    """Track concurrent tool executions for users."""
    
    def __init__(self):
        self.active_executions: Dict[str, Set[str]] = defaultdict(set)
    
    def start_execution(self, user_id: str, execution_id: str) -> None:
        """Start tracking execution."""
        self.active_executions[user_id].add(execution_id)
    
    def end_execution(self, user_id: str, execution_id: str) -> None:
        """End tracking execution."""
        self.active_executions[user_id].discard(execution_id)
        if not self.active_executions[user_id]:
            del self.active_executions[user_id]
    
    def get_concurrent_count(self, user_id: str) -> int:
        """Get current concurrent execution count for user."""
        return len(self.active_executions.get(user_id, set()))
    
    def check_concurrency_limit(self, user_id: str, max_concurrent: int) -> bool:
        """Check if user is within concurrency limits."""
        return self.get_concurrent_count(user_id) < max_concurrent


class UnifiedToolPermissionLayer:
    """Unified permission layer for tool access control and security.
    
    This layer provides comprehensive permission management including:
    - Role-based access control (RBAC)
    - Plan-based feature access
    - Rate limiting and quota enforcement
    - Concurrency control
    - Security policy validation
    - Audit logging
    """
    
    def __init__(self, layer_id: Optional[str] = None):
        """Initialize the permission layer.
        
        Args:
            layer_id: Optional identifier for this layer instance
        """
        self.layer_id = layer_id or f"permlayer_{int(time.time() * 1000)}"
        self.created_at = datetime.now(timezone.utc)
        
        # Policy storage
        self.policies: Dict[str, ToolPermissionPolicy] = {}
        self.default_policy = ToolPermissionPolicy(
            tool_name="default",
            security_level=SecurityLevel.BASIC,
            max_calls_per_minute=60,
            max_calls_per_hour=1000,
            max_calls_per_day=10000
        )
        
        # Tracking components
        self.rate_limiter = RateLimitTracker()
        self.concurrency_tracker = ConcurrencyTracker()
        
        # Audit logging
        self.audit_log: List[Dict[str, Any]] = []
        self.max_audit_entries = 10000
        
        # Metrics
        self._metrics = {
            'permissions_checked': 0,
            'permissions_granted': 0,
            'permissions_denied': 0,
            'rate_limit_violations': 0,
            'quota_violations': 0,
            'policy_violations': 0,
            'last_check_time': None
        }
        
        # Initialize default policies
        self._initialize_default_policies()
        
        logger.info(f" PASS:  Created UnifiedToolPermissionLayer {self.layer_id}")
    
    def _initialize_default_policies(self) -> None:
        """Initialize default tool policies."""
        # Public tools - no restrictions
        public_tools = [
            "health_check", "system_status", "version_info"
        ]
        for tool_name in public_tools:
            self.add_policy(ToolPermissionPolicy(
                tool_name=tool_name,
                security_level=SecurityLevel.PUBLIC,
                allowed_plans={"free", "basic", "premium", "enterprise"},
                max_calls_per_minute=100
            ))
        
        # Basic tools - require authentication
        basic_tools = [
            "search_corpus", "validate_synthetic_data", "analyze_corpus"
        ]
        for tool_name in basic_tools:
            self.add_policy(ToolPermissionPolicy(
                tool_name=tool_name,
                security_level=SecurityLevel.BASIC,
                allowed_plans={"free", "basic", "premium", "enterprise"},
                max_calls_per_minute=30,
                max_calls_per_hour=500
            ))
        
        # Premium tools - require premium plan
        premium_tools = [
            "generate_synthetic_data_batch", "create_corpus", "export_corpus"
        ]
        for tool_name in premium_tools:
            self.add_policy(ToolPermissionPolicy(
                tool_name=tool_name,
                security_level=SecurityLevel.PREMIUM,
                allowed_plans={"premium", "enterprise"},
                max_calls_per_minute=10,
                max_calls_per_hour=100,
                max_concurrent_executions=3
            ))
        
        # Admin tools - require admin role
        admin_tools = [
            "delete_corpus", "system_maintenance", "user_management"
        ]
        for tool_name in admin_tools:
            self.add_policy(ToolPermissionPolicy(
                tool_name=tool_name,
                security_level=SecurityLevel.ADMIN,
                required_roles={"admin"},
                allowed_plans={"enterprise"},
                max_calls_per_minute=5,
                max_concurrent_executions=1
            ))
    
    # ===================== POLICY MANAGEMENT =====================
    
    def add_policy(self, policy: ToolPermissionPolicy) -> bool:
        """Add or update tool permission policy."""
        try:
            policy.updated_at = datetime.now(timezone.utc)
            self.policies[policy.tool_name] = policy
            
            logger.info(f" PASS:  Added/updated policy for tool {policy.tool_name} "
                       f"(security_level: {policy.security_level.name})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add policy for {policy.tool_name}: {e}")
            return False
    
    def get_policy(self, tool_name: str) -> ToolPermissionPolicy:
        """Get policy for tool (returns default if not found)."""
        return self.policies.get(tool_name, self.default_policy)
    
    def remove_policy(self, tool_name: str) -> bool:
        """Remove tool policy."""
        if tool_name in self.policies:
            del self.policies[tool_name]
            logger.info(f"[U+1F5D1][U+FE0F] Removed policy for tool {tool_name}")
            return True
        return False
    
    def list_policies(self) -> List[str]:
        """List all tool names with policies."""
        return list(self.policies.keys())
    
    def get_all_policies(self) -> Dict[str, Dict[str, Any]]:
        """Get all policies as dictionaries."""
        return {
            name: policy.to_dict()
            for name, policy in self.policies.items()
        }
    
    # ===================== PERMISSION CHECKING =====================
    
    async def check_permission(
        self,
        user_context: UserContext,
        tool_name: str,
        execution_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> PermissionCheckResult:
        """Check if user has permission to execute tool.
        
        Args:
            user_context: User context with roles, plan, etc.
            tool_name: Name of tool to check
            execution_id: Optional execution ID for concurrency tracking
            parameters: Optional tool parameters for validation
            
        Returns:
            PermissionCheckResult: Detailed permission check result
        """
        self._metrics['permissions_checked'] += 1
        self._metrics['last_check_time'] = datetime.now(timezone.utc)
        
        policy = self.get_policy(tool_name)
        
        try:
            # 1. Security level check
            if user_context.security_clearance.value < policy.security_level.value:
                result = PermissionCheckResult(
                    allowed=False,
                    result=PermissionResult.INSUFFICIENT_PLAN,
                    reason=f"Security level {policy.security_level.name} required, "
                           f"user has {user_context.security_clearance.name}",
                    policy_applied=tool_name,
                    security_level_required=policy.security_level
                )
                self._record_audit("permission_denied", user_context.user_id, tool_name, result.reason)
                self._metrics['permissions_denied'] += 1
                return result
            
            # 2. Plan check
            if user_context.plan_tier not in policy.allowed_plans:
                result = PermissionCheckResult(
                    allowed=False,
                    result=PermissionResult.INSUFFICIENT_PLAN,
                    reason=f"Plan {user_context.plan_tier} not allowed for {tool_name}. "
                           f"Required: {list(policy.allowed_plans)}",
                    policy_applied=tool_name
                )
                self._record_audit("plan_denied", user_context.user_id, tool_name, result.reason)
                self._metrics['permissions_denied'] += 1
                return result
            
            # 3. Role check
            if policy.required_roles and not policy.required_roles.intersection(user_context.roles):
                result = PermissionCheckResult(
                    allowed=False,
                    result=PermissionResult.POLICY_VIOLATION,
                    reason=f"Required roles {list(policy.required_roles)} not satisfied. "
                           f"User roles: {list(user_context.roles)}",
                    policy_applied=tool_name
                )
                self._record_audit("role_denied", user_context.user_id, tool_name, result.reason)
                self._metrics['policy_violations'] += 1
                return result
            
            # 4. Feature flag check
            for required_feature in policy.required_features:
                if not user_context.feature_flags.get(required_feature, False):
                    result = PermissionCheckResult(
                        allowed=False,
                        result=PermissionResult.MISSING_FEATURE,
                        reason=f"Required feature '{required_feature}' not enabled for user",
                        policy_applied=tool_name
                    )
                    self._record_audit("feature_denied", user_context.user_id, tool_name, result.reason)
                    self._metrics['permissions_denied'] += 1
                    return result
            
            # 5. Rate limit check
            is_allowed, calls_remaining, reset_time = self.rate_limiter.check_rate_limit(
                user_context.user_id,
                tool_name,
                policy.max_calls_per_minute,
                policy.max_calls_per_hour,
                policy.max_calls_per_day
            )
            
            if not is_allowed:
                result = PermissionCheckResult(
                    allowed=False,
                    result=PermissionResult.RATE_LIMITED,
                    reason="Rate limit exceeded for tool",
                    calls_remaining=0,
                    reset_time=reset_time,
                    policy_applied=tool_name
                )
                self._record_audit("rate_limited", user_context.user_id, tool_name, result.reason)
                self._metrics['rate_limit_violations'] += 1
                return result
            
            # 6. Concurrency check
            if policy.max_concurrent_executions:
                if not self.concurrency_tracker.check_concurrency_limit(
                    user_context.user_id, policy.max_concurrent_executions
                ):
                    result = PermissionCheckResult(
                        allowed=False,
                        result=PermissionResult.QUOTA_EXCEEDED,
                        reason=f"Concurrent execution limit exceeded "
                               f"({policy.max_concurrent_executions})",
                        policy_applied=tool_name
                    )
                    self._record_audit("concurrency_limited", user_context.user_id, tool_name, result.reason)
                    self._metrics['quota_violations'] += 1
                    return result
            
            # 7. Parameter validation
            if parameters and policy.validation_rules:
                for rule in policy.validation_rules:
                    try:
                        if not rule(parameters):
                            result = PermissionCheckResult(
                                allowed=False,
                                result=PermissionResult.POLICY_VIOLATION,
                                reason="Parameters failed validation rule",
                                policy_applied=tool_name
                            )
                            self._record_audit("validation_failed", user_context.user_id, tool_name, result.reason)
                            self._metrics['policy_violations'] += 1
                            return result
                    except Exception as e:
                        logger.error(f"Validation rule error for {tool_name}: {e}")
                        result = PermissionCheckResult(
                            allowed=False,
                            result=PermissionResult.POLICY_VIOLATION,
                            reason=f"Parameter validation error: {e}",
                            policy_applied=tool_name
                        )
                        self._record_audit("validation_error", user_context.user_id, tool_name, result.reason)
                        return result
            
            # All checks passed - grant permission
            result = PermissionCheckResult(
                allowed=True,
                result=PermissionResult.ALLOWED,
                reason="All permission checks passed",
                calls_remaining=calls_remaining,
                reset_time=reset_time,
                policy_applied=tool_name
            )
            
            # Record successful permission and track usage
            self.rate_limiter.record_call(user_context.user_id, tool_name)
            if execution_id and policy.max_concurrent_executions:
                self.concurrency_tracker.start_execution(user_context.user_id, execution_id)
            
            self._record_audit("permission_granted", user_context.user_id, tool_name, result.reason)
            self._metrics['permissions_granted'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Permission check error for {tool_name}: {e}")
            result = PermissionCheckResult(
                allowed=False,
                result=PermissionResult.POLICY_VIOLATION,
                reason=f"Permission check failed: {e}",
                policy_applied=tool_name
            )
            self._record_audit("check_error", user_context.user_id, tool_name, str(e))
            return result
    
    def end_execution(self, user_id: str, execution_id: str) -> None:
        """End execution tracking for concurrency limits."""
        self.concurrency_tracker.end_execution(user_id, execution_id)
    
    # ===================== AUDIT LOGGING =====================
    
    def _record_audit(
        self,
        action: str,
        user_id: str,
        tool_name: str,
        details: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record audit log entry."""
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': action,
            'user_id': user_id,
            'tool_name': tool_name,
            'details': details,
            'metadata': metadata or {},
            'layer_id': self.layer_id
        }
        
        self.audit_log.append(entry)
        
        # Trim audit log if too large
        if len(self.audit_log) > self.max_audit_entries:
            self.audit_log = self.audit_log[-self.max_audit_entries//2:]
        
        logger.debug(f"[U+1F4DD] Audit: {action} - {user_id} - {tool_name} - {details}")
    
    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        action: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get filtered audit log entries."""
        entries = self.audit_log
        
        # Apply filters
        if user_id:
            entries = [e for e in entries if e['user_id'] == user_id]
        if tool_name:
            entries = [e for e in entries if e['tool_name'] == tool_name]
        if action:
            entries = [e for e in entries if e['action'] == action]
        
        # Apply limit
        if limit:
            entries = entries[-limit:]
        
        return entries
    
    def clear_audit_log(self) -> None:
        """Clear audit log."""
        self.audit_log.clear()
        logger.info(f"Cleared audit log for permission layer {self.layer_id}")
    
    # ===================== METRICS AND MONITORING =====================
    
    def get_permission_metrics(self) -> Dict[str, Any]:
        """Get comprehensive permission layer metrics."""
        uptime_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        
        # Calculate success rate
        total_checks = self._metrics['permissions_checked']
        success_rate = (
            self._metrics['permissions_granted'] / max(1, total_checks)
        )
        
        # Get top denied tools
        tool_denials = defaultdict(int)
        for entry in self.audit_log:
            if entry['action'].endswith('_denied'):
                tool_denials[entry['tool_name']] += 1
        
        top_denied_tools = sorted(
            tool_denials.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            **self._metrics,
            'layer_id': self.layer_id,
            'uptime_seconds': uptime_seconds,
            'policies_count': len(self.policies),
            'audit_entries': len(self.audit_log),
            'success_rate': success_rate,
            'top_denied_tools': [
                {'tool_name': tool, 'denials': count}
                for tool, count in top_denied_tools
            ],
            'active_users_rate_limited': len(self.rate_limiter.call_history),
            'users_with_active_executions': len(self.concurrency_tracker.active_executions),
            'created_at': self.created_at.isoformat()
        }
    
    def get_user_usage_summary(self, user_id: str) -> Dict[str, Any]:
        """Get usage summary for specific user."""
        user_entries = [e for e in self.audit_log if e['user_id'] == user_id]
        
        tool_usage = defaultdict(int)
        actions = defaultdict(int)
        
        for entry in user_entries:
            tool_usage[entry['tool_name']] += 1
            actions[entry['action']] += 1
        
        # Get current rate limit status
        current_limits = {}
        for tool_name in self.policies.keys():
            policy = self.policies[tool_name]
            is_allowed, remaining, reset_time = self.rate_limiter.check_rate_limit(
                user_id, tool_name,
                policy.max_calls_per_minute,
                policy.max_calls_per_hour,
                policy.max_calls_per_day
            )
            current_limits[tool_name] = {
                'is_allowed': is_allowed,
                'calls_remaining': remaining,
                'reset_time': reset_time.isoformat() if reset_time else None
            }
        
        return {
            'user_id': user_id,
            'total_actions': len(user_entries),
            'tool_usage': dict(tool_usage),
            'action_breakdown': dict(actions),
            'current_concurrent_executions': self.concurrency_tracker.get_concurrent_count(user_id),
            'current_rate_limits': current_limits,
            'last_activity': user_entries[-1]['timestamp'] if user_entries else None
        }
    
    def validate_layer_health(self) -> Dict[str, Any]:
        """Validate permission layer health."""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'issues': [],
            'metrics': self.get_permission_metrics()
        }
        
        # Check for high denial rate
        if self._metrics['permissions_checked'] > 100:
            denial_rate = (
                (self._metrics['permissions_denied'] + self._metrics['rate_limit_violations'] +
                 self._metrics['quota_violations'] + self._metrics['policy_violations']) /
                self._metrics['permissions_checked']
            )
            
            if denial_rate > 0.5:  # More than 50% denials
                health_status['status'] = 'degraded'
                health_status['issues'].append(f"High denial rate: {denial_rate:.1%}")
        
        # Check for missing policies
        if len(self.policies) < 5:  # Very few policies
            health_status['status'] = 'warning'
            health_status['issues'].append(f"Low policy count: {len(self.policies)}")
        
        # Check audit log size
        if len(self.audit_log) > self.max_audit_entries * 0.9:
            health_status['status'] = 'warning'
            health_status['issues'].append("Audit log near capacity")
        
        return health_status


# ===================== GLOBAL PERMISSION LAYER INSTANCE =====================

_global_permission_layer: Optional[UnifiedToolPermissionLayer] = None


def get_global_permission_layer() -> UnifiedToolPermissionLayer:
    """Get global permission layer instance."""
    global _global_permission_layer
    
    if _global_permission_layer is None:
        _global_permission_layer = UnifiedToolPermissionLayer("global")
        logger.info("Created global UnifiedToolPermissionLayer")
    
    return _global_permission_layer


def create_request_scoped_permission_layer(layer_id: Optional[str] = None) -> UnifiedToolPermissionLayer:
    """Create request-scoped permission layer."""
    return UnifiedToolPermissionLayer(layer_id)


# Export all public interfaces
__all__ = [
    'UnifiedToolPermissionLayer',
    'ToolPermissionPolicy',
    'UserContext',
    'PermissionCheckResult',
    'PermissionResult',
    'SecurityLevel',
    'get_global_permission_layer',
    'create_request_scoped_permission_layer'
]