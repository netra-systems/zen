"""Retry Policy Service for service mesh"""

from typing import Dict, Any, Optional, Callable, List
import asyncio
import random
from datetime import datetime, UTC
from enum import Enum


class RetryStrategy(Enum):
    """Retry strategies"""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    RANDOM_JITTER = "random_jitter"


class RetryPolicyService:
    """Retry policy management for service calls"""
    
    def __init__(self):
        self.policies: Dict[str, Dict[str, Any]] = {}
        self.retry_stats: Dict[str, Dict[str, int]] = {}
        self.default_policy = {
            "max_retries": 3,
            "base_delay": 1.0,  # seconds
            "max_delay": 30.0,  # seconds
            "strategy": RetryStrategy.EXPONENTIAL_BACKOFF,
            "backoff_multiplier": 2.0,
            "jitter": True
        }
    
    async def register_policy(self, service_name: str, policy: Dict[str, Any]) -> bool:
        """Register retry policy for a service"""
        validated_policy = self._validate_policy(policy)
        
        self.policies[service_name] = {
            **self.default_policy,
            **validated_policy,
            "created_at": datetime.now(UTC).isoformat()
        }
        
        self.retry_stats[service_name] = {
            "total_attempts": 0,
            "successful_retries": 0,
            "failed_after_retries": 0,
            "total_retry_attempts": 0
        }
        
        return True
    
    def _validate_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize retry policy"""
        validated = {}
        
        if "max_retries" in policy:
            validated["max_retries"] = max(0, min(10, policy["max_retries"]))
        
        if "base_delay" in policy:
            validated["base_delay"] = max(0.1, min(60.0, policy["base_delay"]))
        
        if "max_delay" in policy:
            validated["max_delay"] = max(1.0, min(300.0, policy["max_delay"]))
        
        if "strategy" in policy:
            if isinstance(policy["strategy"], str):
                try:
                    validated["strategy"] = RetryStrategy(policy["strategy"])
                except ValueError:
                    pass  # Use default
            elif isinstance(policy["strategy"], RetryStrategy):
                validated["strategy"] = policy["strategy"]
        
        if "backoff_multiplier" in policy:
            validated["backoff_multiplier"] = max(1.0, min(10.0, policy["backoff_multiplier"]))
        
        if "jitter" in policy:
            validated["jitter"] = bool(policy["jitter"])
        
        return validated
    
    async def execute_with_retry(self, service_name: str, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with retry policy"""
        policy = self.policies.get(service_name, self.default_policy)
        stats = self.retry_stats.get(service_name, {})
        
        max_retries = policy["max_retries"]
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if stats:
                    stats["total_attempts"] += 1
                
                result = await operation(*args, **kwargs)
                
                # Success - record stats if this was a retry
                if attempt > 0 and stats:
                    stats["successful_retries"] += 1
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # If this was the last attempt, don't retry
                if attempt >= max_retries:
                    if stats:
                        stats["failed_after_retries"] += 1
                    break
                
                # Calculate delay and wait
                delay = self._calculate_delay(policy, attempt)
                if stats:
                    stats["total_retry_attempts"] += 1
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        raise last_exception
    
    def _calculate_delay(self, policy: Dict[str, Any], attempt: int) -> float:
        """Calculate delay for retry attempt"""
        base_delay = policy["base_delay"]
        max_delay = policy["max_delay"]
        strategy = policy["strategy"]
        multiplier = policy["backoff_multiplier"]
        jitter = policy["jitter"]
        
        if strategy == RetryStrategy.FIXED_DELAY:
            delay = base_delay
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = base_delay * (multiplier ** attempt)
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = base_delay * (1 + attempt)
        elif strategy == RetryStrategy.RANDOM_JITTER:
            delay = base_delay + random.uniform(0, base_delay)
        else:
            delay = base_delay
        
        # Apply jitter if enabled
        if jitter and strategy != RetryStrategy.RANDOM_JITTER:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        # Ensure delay is within bounds
        return max(0.1, min(max_delay, delay))
    
    async def get_policy(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get retry policy for a service"""
        policy = self.policies.get(service_name)
        if policy:
            # Convert enum to string for serialization
            policy_copy = policy.copy()
            if isinstance(policy_copy.get("strategy"), RetryStrategy):
                policy_copy["strategy"] = policy_copy["strategy"].value
            return policy_copy
        return None
    
    async def update_policy(self, service_name: str, updates: Dict[str, Any]) -> bool:
        """Update retry policy for a service"""
        if service_name not in self.policies:
            return False
        
        validated_updates = self._validate_policy(updates)
        self.policies[service_name].update(validated_updates)
        return True
    
    async def remove_policy(self, service_name: str) -> bool:
        """Remove retry policy for a service"""
        if service_name in self.policies:
            del self.policies[service_name]
            if service_name in self.retry_stats:
                del self.retry_stats[service_name]
            return True
        return False
    
    async def get_retry_stats(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get retry statistics for a service"""
        if service_name not in self.retry_stats:
            return None
        
        stats = self.retry_stats[service_name]
        total_attempts = stats["total_attempts"]
        
        return {
            "service_name": service_name,
            "total_attempts": total_attempts,
            "successful_retries": stats["successful_retries"],
            "failed_after_retries": stats["failed_after_retries"],
            "total_retry_attempts": stats["total_retry_attempts"],
            "success_rate": (total_attempts - stats["failed_after_retries"]) / total_attempts if total_attempts > 0 else 0,
            "average_retries_per_call": stats["total_retry_attempts"] / total_attempts if total_attempts > 0 else 0
        }
    
    async def list_policies(self) -> Dict[str, Dict[str, Any]]:
        """List all retry policies"""
        policies = {}
        for service_name, policy in self.policies.items():
            policy_copy = policy.copy()
            if isinstance(policy_copy.get("strategy"), RetryStrategy):
                policy_copy["strategy"] = policy_copy["strategy"].value
            policies[service_name] = policy_copy
        return policies
    
    async def test_policy(self, service_name: str, failure_rate: float = 0.5) -> Dict[str, Any]:
        """Test retry policy with simulated failures"""
        async def test_operation():
            if random.random() < failure_rate:
                raise Exception("Simulated failure")
            return "success"
        
        start_time = datetime.now(UTC)
        attempts = 0
        
        try:
            result = await self.execute_with_retry(service_name, test_operation)
            success = True
        except Exception:
            result = None
            success = False
        
        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()
        
        return {
            "service_name": service_name,
            "success": success,
            "result": result,
            "duration_seconds": duration,
            "policy": await self.get_policy(service_name)
        }
    
    def get_retry_service_stats(self) -> Dict[str, Any]:
        """Get overall retry service statistics"""
        total_policies = len(self.policies)
        total_attempts = sum(stats["total_attempts"] for stats in self.retry_stats.values())
        total_successful_retries = sum(stats["successful_retries"] for stats in self.retry_stats.values())
        total_failed = sum(stats["failed_after_retries"] for stats in self.retry_stats.values())
        
        return {
            "total_policies": total_policies,
            "total_attempts": total_attempts,
            "total_successful_retries": total_successful_retries,
            "total_failed_after_retries": total_failed,
            "overall_success_rate": (total_attempts - total_failed) / total_attempts if total_attempts > 0 else 0,
            "services": list(self.policies.keys())
        }