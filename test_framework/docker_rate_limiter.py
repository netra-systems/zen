"""
Docker Rate Limiter - Prevents API storms and daemon overload

This module provides rate limiting for Docker operations to prevent Docker Desktop crashes
due to concurrent operation storms. All Docker commands should go through this rate limiter.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Prevent Docker daemon crashes, enable reliable CI/CD
3. Value Impact: Prevents 2-4 hours/week of developer downtime from Docker crashes
4. Revenue Impact: Protects development velocity for $2M+ ARR platform
"""

import threading
import time
import subprocess
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from contextlib import contextmanager

# CRITICAL SECURITY IMPORT: Force flag guardian
from test_framework.docker_force_flag_guardian import (
    DockerForceFlagGuardian, 
    DockerForceFlagViolation,
    validate_docker_command
)

logger = logging.getLogger(__name__)


@dataclass
class DockerCommandResult:
    """Result of a Docker command execution."""
    returncode: int
    stdout: str
    stderr: str
    duration: float
    retry_count: int


class DockerRateLimiter:
    """Rate limiter for Docker operations to prevent API storms."""
    
    def __init__(self, 
                 min_interval: float = 0.5, 
                 max_concurrent: int = 3,
                 max_retries: int = 3,
                 base_backoff: float = 1.0):
        """
        Initialize Docker rate limiter with CRITICAL security enforcement.
        
        Args:
            min_interval: Minimum seconds between operations
            max_concurrent: Maximum concurrent Docker operations
            max_retries: Maximum retry attempts for failed operations
            base_backoff: Base seconds for exponential backoff
        """
        self.min_interval = min_interval
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        
        # CRITICAL SECURITY: Initialize force flag guardian
        self.force_flag_guardian = DockerForceFlagGuardian(
            audit_log_path="logs/docker_force_violations_rate_limiter.log"
        )
        
        # Thread synchronization
        self._lock = threading.RLock()
        self._last_operation_time = 0
        self._concurrent_operations = 0
        self._operation_semaphore = threading.Semaphore(max_concurrent)
        
        # Statistics
        self._total_operations = 0
        self._failed_operations = 0
        self._rate_limited_operations = 0
        self._force_flag_violations = 0
        
        logger.info(f"Docker rate limiter initialized with FORCE FLAG PROTECTION: "
                   f"min_interval={min_interval}s, max_concurrent={max_concurrent}, "
                   f"max_retries={max_retries}")
        logger.critical("[U+1F6E1][U+FE0F]  FORCE FLAG GUARDIAN ACTIVE - Zero tolerance for -f/--force flags")
    
    def execute_docker_command(self, 
                             cmd: List[str], 
                             timeout: Optional[float] = 30,
                             **kwargs) -> DockerCommandResult:
        """
        Execute Docker command with CRITICAL force flag validation, rate limiting and exponential backoff.
        
        Args:
            cmd: Docker command as list of strings
            timeout: Command timeout in seconds
            **kwargs: Additional arguments for subprocess.run
            
        Returns:
            DockerCommandResult with execution details
            
        Raises:
            DockerForceFlagViolation: If force flags are detected (CRITICAL SECURITY)
            subprocess.TimeoutExpired: If command times out
            RuntimeError: If all retries fail
        """
        #  ALERT:  CRITICAL SECURITY CHECK FIRST - NO EXCEPTIONS
        try:
            command_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
            self.force_flag_guardian.validate_command(command_str)
        except DockerForceFlagViolation as e:
            self._force_flag_violations += 1
            logger.critical(f" ALERT:  FORCE FLAG VIOLATION BLOCKED: {command_str}")
            # Re-raise with no possibility of bypass
            raise e
        
        start_time = time.time()
        last_exception = None
        
        for retry in range(self.max_retries + 1):
            try:
                with self._operation_semaphore:
                    with self._lock:
                        # Track operation start
                        self._total_operations += 1
                        
                        # Enforce minimum interval between operations
                        elapsed = time.time() - self._last_operation_time
                        if elapsed < self.min_interval:
                            sleep_time = self.min_interval - elapsed
                            self._rate_limited_operations += 1
                            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                            time.sleep(sleep_time)
                        
                        self._concurrent_operations += 1
                        operation_start = time.time()
                    
                    try:
                        # Set default values for subprocess.run
                        run_kwargs = {
                            'capture_output': True,
                            'text': True,
                            'timeout': timeout,
                            **kwargs
                        }
                        
                        logger.debug(f"Executing Docker command: {' '.join(cmd)} "
                                   f"(attempt {retry + 1}/{self.max_retries + 1})")
                        
                        result = subprocess.run(cmd, **run_kwargs)
                        
                        duration = time.time() - operation_start
                        
                        # Log command execution
                        if result.returncode != 0:
                            logger.warning(f"Docker command failed (rc={result.returncode}): {' '.join(cmd)}")
                            if result.stderr:
                                logger.debug(f"Docker stderr: {result.stderr[:500]}")
                        else:
                            logger.debug(f"Docker command succeeded in {duration:.2f}s: {' '.join(cmd)}")
                        
                        return DockerCommandResult(
                            returncode=result.returncode,
                            stdout=result.stdout,
                            stderr=result.stderr,
                            duration=duration,
                            retry_count=retry
                        )
                        
                    finally:
                        with self._lock:
                            self._last_operation_time = time.time()
                            self._concurrent_operations -= 1
                            
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as e:
                last_exception = e
                
                # Don't retry timeout errors immediately
                if isinstance(e, subprocess.TimeoutExpired):
                    logger.warning(f"Docker command timed out after {timeout}s: {' '.join(cmd)}")
                    if retry < self.max_retries:
                        backoff_time = self.base_backoff * (2 ** retry)
                        logger.info(f"Retrying after {backoff_time:.1f}s backoff (attempt {retry + 2})")
                        time.sleep(backoff_time)
                        continue
                    else:
                        raise
                
                # Handle other errors with exponential backoff
                if retry < self.max_retries:
                    backoff_time = self.base_backoff * (2 ** retry)
                    logger.warning(f"Docker command failed, retrying in {backoff_time:.1f}s: {e}")
                    time.sleep(backoff_time)
                    continue
                else:
                    self._failed_operations += 1
                    logger.error(f"Docker command failed after {self.max_retries + 1} attempts: {' '.join(cmd)}")
                    raise RuntimeError(f"Docker command failed after {self.max_retries + 1} attempts: {e}")
            
            except Exception as e:
                # Unexpected errors
                last_exception = e
                logger.error(f"Unexpected error executing Docker command: {e}")
                if retry < self.max_retries:
                    backoff_time = self.base_backoff * (2 ** retry)
                    logger.info(f"Retrying after {backoff_time:.1f}s backoff")
                    time.sleep(backoff_time)
                    continue
                else:
                    self._failed_operations += 1
                    raise
        
        # Should never reach here, but just in case
        raise RuntimeError(f"Max retries exceeded: {last_exception}")
    
    @contextmanager
    def batch_operation(self):
        """
        Context manager for batch operations with reduced rate limiting.
        
        Use this when performing multiple related Docker operations that should
        be treated as a single logical unit.
        """
        original_interval = self.min_interval
        self.min_interval = self.min_interval / 2  # Reduce interval for batch ops
        
        try:
            yield self
        finally:
            self.min_interval = original_interval
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiter statistics including CRITICAL force flag violations."""
        with self._lock:
            return {
                "total_operations": self._total_operations,
                "failed_operations": self._failed_operations,
                "rate_limited_operations": self._rate_limited_operations,
                "force_flag_violations": self._force_flag_violations,
                "success_rate": (
                    (self._total_operations - self._failed_operations) / self._total_operations * 100
                    if self._total_operations > 0 else 0
                ),
                "current_concurrent": self._concurrent_operations,
                "max_concurrent": self.max_concurrent,
                "rate_limit_percentage": (
                    self._rate_limited_operations / self._total_operations * 100
                    if self._total_operations > 0 else 0
                ),
                "force_flag_guardian_status": "ACTIVE - ZERO TOLERANCE ENFORCED",
                "guardian_audit_report": self.force_flag_guardian.audit_report()
            }
    
    def reset_statistics(self):
        """Reset all statistics counters."""
        with self._lock:
            self._total_operations = 0
            self._failed_operations = 0
            self._rate_limited_operations = 0
            self._force_flag_violations = 0
    
    def health_check(self) -> bool:
        """
        Perform a health check on Docker availability.
        
        Returns:
            True if Docker is available and responsive
        """
        try:
            result = self.execute_docker_command(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Docker health check failed: {e}")
            return False


# Global rate limiter instance
_global_rate_limiter = None
_rate_limiter_lock = threading.Lock()


def get_docker_rate_limiter() -> DockerRateLimiter:
    """
    Get the global Docker rate limiter instance.
    
    Returns:
        Singleton DockerRateLimiter instance
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        with _rate_limiter_lock:
            if _global_rate_limiter is None:
                _global_rate_limiter = DockerRateLimiter()
    
    return _global_rate_limiter


def execute_docker_command(cmd: List[str], **kwargs) -> DockerCommandResult:
    """
    Convenience function to execute Docker command with CRITICAL force flag validation and rate limiting.
    
    Args:
        cmd: Docker command as list of strings
        **kwargs: Additional arguments for subprocess.run
        
    Returns:
        DockerCommandResult with execution details
        
    Raises:
        DockerForceFlagViolation: If force flags detected (CRITICAL SECURITY)
    """
    rate_limiter = get_docker_rate_limiter()
    return rate_limiter.execute_docker_command(cmd, **kwargs)


def docker_health_check() -> bool:
    """
    Convenience function to check Docker health.
    
    Returns:
        True if Docker is available and responsive
    """
    rate_limiter = get_docker_rate_limiter()
    return rate_limiter.health_check()


# Legacy compatibility for direct subprocess usage
def safe_subprocess_run(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """
    Legacy compatibility wrapper for subprocess.run with CRITICAL Docker force flag validation.
    
    This function maintains backward compatibility while adding CRITICAL security enforcement.
    
    Args:
        cmd: Command as list of strings
        **kwargs: Arguments for subprocess.run
        
    Returns:
        subprocess.CompletedProcess result
        
    Raises:
        DockerForceFlagViolation: If Docker command contains force flags (CRITICAL SECURITY)
    """
    if len(cmd) > 0 and cmd[0] in ['docker', 'docker-compose']:
        #  ALERT:  CRITICAL: Use rate limiter with force flag protection for Docker commands
        result = execute_docker_command(cmd, **kwargs)
        
        # Convert to subprocess.CompletedProcess for compatibility
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr
        )
    else:
        # Non-Docker commands go through normal subprocess
        return subprocess.run(cmd, **kwargs)