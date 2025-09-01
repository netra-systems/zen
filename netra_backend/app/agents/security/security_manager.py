"""SecurityManager - Central security orchestration for agent execution.

This module integrates all security components (ResourceGuard, CircuitBreaker, TimeoutManager)
into a unified security management system that provides comprehensive protection
against resource exhaustion, cascading failures, and DoS attacks.

Business Value: Single point of control for all security policies and enforcement,
ensuring consistent protection across all agent execution paths.
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import IsolatedEnvironment

from .resource_guard import ResourceGuard, ResourceLimits
from .circuit_breaker import SystemCircuitBreaker, CircuitBreakerConfig, FailureType
from ..execution_tracking.timeout import TimeoutManager

logger = central_logger.get_logger(__name__)


@dataclass
class SecurityConfig:
    """Comprehensive security configuration."""
    # Resource limits
    max_memory_mb: int = 512
    max_cpu_percent: float = 80.0
    max_concurrent_per_user: int = 10
    max_concurrent_global: int = 100
    rate_limit_per_minute: int = 100
    
    # Timeout settings
    default_timeout_seconds: float = 30.0
    max_timeout_seconds: float = 120.0
    timeout_check_interval: float = 5.0
    
    # Circuit breaker settings
    failure_threshold: int = 3
    recovery_timeout: int = 60
    success_threshold: int = 2
    failure_window_seconds: int = 300
    
    # Security policies
    enable_resource_protection: bool = True
    enable_circuit_breaker: bool = True
    enable_timeout_protection: bool = True
    emergency_shutdown_threshold: int = 10  # Violations before emergency shutdown


@dataclass
class ExecutionRequest:
    """Request for agent execution with security context."""
    agent_name: str
    user_id: str
    estimated_memory_mb: float = 0
    timeout_seconds: Optional[float] = None
    context: Optional[Dict[str, Any]] = None
    bypass_security: bool = False  # Only for emergency/admin operations


@dataclass
class ExecutionPermission:
    """Result of security validation."""
    allowed: bool
    reason: Optional[str] = None
    recommended_agent: Optional[str] = None
    timeout_seconds: float = 30.0
    execution_id: Optional[str] = None


class SecurityManager:
    """Central security orchestration system.
    
    This class coordinates all security components to provide comprehensive
    protection for agent execution, including:
    - Resource management and limits
    - Circuit breaker failure detection
    - Timeout enforcement
    - Rate limiting and abuse prevention
    - Emergency recovery procedures
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize SecurityManager with configuration."""
        self.env = IsolatedEnvironment()
        
        # Load configuration
        self.config = config or SecurityConfig(
            max_memory_mb=int(self.env.get('SECURITY_MAX_MEMORY_MB', '512')),
            max_cpu_percent=float(self.env.get('SECURITY_MAX_CPU_PERCENT', '80.0')),
            max_concurrent_per_user=int(self.env.get('SECURITY_MAX_CONCURRENT_PER_USER', '10')),
            rate_limit_per_minute=int(self.env.get('SECURITY_RATE_LIMIT_PER_MINUTE', '100')),
            default_timeout_seconds=float(self.env.get('SECURITY_DEFAULT_TIMEOUT', '30.0')),
            enable_resource_protection=self.env.get('SECURITY_ENABLE_RESOURCE_PROTECTION', 'true').lower() == 'true',
            enable_circuit_breaker=self.env.get('SECURITY_ENABLE_CIRCUIT_BREAKER', 'true').lower() == 'true',
            enable_timeout_protection=self.env.get('SECURITY_ENABLE_TIMEOUT_PROTECTION', 'true').lower() == 'true'
        )
        
        # Initialize security components
        self.resource_guard: Optional[ResourceGuard] = None
        self.circuit_breaker: Optional[SystemCircuitBreaker] = None  
        self.timeout_manager: Optional[TimeoutManager] = None
        
        if self.config.enable_resource_protection:
            resource_limits = ResourceLimits(
                max_memory_mb=self.config.max_memory_mb,
                max_cpu_percent=self.config.max_cpu_percent,
                max_concurrent_per_user=self.config.max_concurrent_per_user,
                max_concurrent_global=self.config.max_concurrent_global,
                rate_limit_per_minute=self.config.rate_limit_per_minute
            )
            self.resource_guard = ResourceGuard(resource_limits)
        
        if self.config.enable_circuit_breaker:
            breaker_config = CircuitBreakerConfig(
                failure_threshold=self.config.failure_threshold,
                recovery_timeout=self.config.recovery_timeout,
                success_threshold=self.config.success_threshold,
                failure_window_seconds=self.config.failure_window_seconds
            )
            self.circuit_breaker = SystemCircuitBreaker(breaker_config)
        
        if self.config.enable_timeout_protection:
            self.timeout_manager = TimeoutManager(self.config.timeout_check_interval)
        
        # Security metrics
        self.total_requests = 0
        self.blocked_requests = 0
        self.security_violations = 0
        self.emergency_shutdowns = 0
        self.started_at = datetime.now(UTC)
        
        logger.info(f"🛡️ SecurityManager initialized with config: {self.config}")
    
    async def validate_execution_request(self, request: ExecutionRequest) -> ExecutionPermission:
        """Validate if an execution request should be allowed.
        
        This is the main entry point for all security validation.
        
        Args:
            request: The execution request to validate
            
        Returns:
            ExecutionPermission with allow/deny decision and context
        """
        self.total_requests += 1
        
        # Allow bypass for emergency operations
        if request.bypass_security:
            logger.warning(f"⚠️ Security bypass requested for {request.agent_name} by {request.user_id}")
            return ExecutionPermission(
                allowed=True,
                timeout_seconds=request.timeout_seconds or self.config.max_timeout_seconds,
                execution_id=f"{request.agent_name}_{int(time.time() * 1000)}"
            )
        
        # 1. Resource validation
        if self.resource_guard:
            resource_error = await self.resource_guard.validate_resource_request(
                request.user_id, 
                request.estimated_memory_mb
            )
            if resource_error:
                self.blocked_requests += 1
                self.security_violations += 1
                logger.warning(f"🚫 Resource constraint violation: {resource_error}")
                return ExecutionPermission(allowed=False, reason=resource_error)
        
        # 2. Circuit breaker validation
        if self.circuit_breaker:
            can_execute, fallback_agent = await self.circuit_breaker.can_execute_agent(request.agent_name)
            if not can_execute:
                self.blocked_requests += 1
                self.security_violations += 1
                reason = f"Agent {request.agent_name} is currently unavailable due to repeated failures"
                return ExecutionPermission(allowed=False, reason=reason)
            
            # If fallback is recommended, note it
            if fallback_agent:
                logger.info(f"🔄 Recommending fallback agent {fallback_agent} for {request.agent_name}")
        
        # 3. Determine timeout
        timeout = request.timeout_seconds or self.config.default_timeout_seconds
        timeout = min(timeout, self.config.max_timeout_seconds)  # Cap at maximum
        
        # 4. Generate execution ID
        execution_id = f"{request.agent_name}_{request.user_id}_{int(time.time() * 1000)}"
        
        # Request is approved
        return ExecutionPermission(
            allowed=True,
            recommended_agent=fallback_agent,
            timeout_seconds=timeout,
            execution_id=execution_id
        )
    
    async def acquire_execution_resources(self, request: ExecutionRequest, permission: ExecutionPermission) -> bool:
        """Acquire resources for execution after validation.
        
        Args:
            request: The execution request
            permission: The previously granted permission
            
        Returns:
            True if resources acquired successfully
        """
        try:
            # Acquire resource protection
            if self.resource_guard and not await self.resource_guard.acquire_resources(
                request.user_id, 
                request.estimated_memory_mb
            ):
                logger.error(f"🚫 Failed to acquire resources for {request.user_id}")
                return False
            
            # Set timeout if enabled
            if self.timeout_manager and permission.execution_id:
                await self.timeout_manager.set_timeout(
                    permission.execution_id,
                    permission.timeout_seconds,
                    request.agent_name
                )
            
            return True
            
        except Exception as e:
            logger.error(f"🚨 Error acquiring execution resources: {e}")
            return False
    
    async def record_execution_result(
        self,
        request: ExecutionRequest,
        permission: ExecutionPermission,
        success: bool,
        error_message: str = "",
        execution_duration: float = 0,
        memory_used: float = 0
    ) -> None:
        """Record the result of an execution for security analysis.
        
        Args:
            request: The original request
            permission: The granted permission
            success: Whether execution succeeded
            error_message: Error message if failed
            execution_duration: How long execution took
            memory_used: Peak memory usage during execution
        """
        try:
            # Release resources
            if self.resource_guard:
                await self.resource_guard.release_resources(request.user_id)
            
            # Clear timeout
            if self.timeout_manager and permission.execution_id:
                await self.timeout_manager.clear_timeout(permission.execution_id)
            
            # Record circuit breaker result
            if self.circuit_breaker:
                failure_type = None
                if not success:
                    # Determine failure type from error message
                    if "timeout" in error_message.lower():
                        failure_type = FailureType.TIMEOUT
                    elif "memory" in error_message.lower():
                        failure_type = FailureType.MEMORY_ERROR
                    elif "rate limit" in error_message.lower():
                        failure_type = FailureType.RATE_LIMIT
                    elif error_message.strip() in ['...', '', 'None']:
                        failure_type = FailureType.SILENT_FAILURE
                    else:
                        failure_type = FailureType.EXCEPTION
                
                agent_name = permission.recommended_agent or request.agent_name
                await self.circuit_breaker.record_execution_result(
                    agent_name,
                    success,
                    failure_type,
                    error_message,
                    request.user_id,
                    request.context
                )