"""
Business Cache Strategies - Business Logic Caching Module

This module provides business-focused caching strategies for different types
of business data with appropriate TTL and invalidation policies.

Business Value Justification (BVJ):
- Segment: All customer segments - Platform optimization benefits all users
- Business Goal: Improve application performance and reduce infrastructure costs
- Value Impact: Faster response times and reduced database load improve user experience
- Strategic Impact: Enables platform scalability and cost optimization
"""

import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """Business cache strategy types."""
    SHORT_LIVED = "short_lived"
    MEDIUM_LIVED = "medium_lived"
    LONG_LIVED = "long_lived"
    LONG_LIVED_WITH_VERSIONING = "long_lived_with_versioning"
    USER_SESSION_SCOPED = "user_session_scoped"
    ANALYSIS_SCOPED = "analysis_scoped"


@dataclass
class CachePolicy:
    """Cache policy configuration."""
    strategy: CacheStrategy
    ttl_seconds: int
    max_size_mb: Optional[float] = None
    invalidation_triggers: List[str] = None
    compression_enabled: bool = False
    
    def __post_init__(self):
        if self.invalidation_triggers is None:
            self.invalidation_triggers = []


class BusinessCacheStrategies:
    """
    Business Cache Strategies for optimizing application performance.
    
    Provides intelligent caching strategies for different types of business data
    based on data characteristics, usage patterns, and business requirements.
    """
    
    def __init__(self):
        """Initialize business cache strategies."""
        self._strategy_policies = self._initialize_strategy_policies()
        logger.info("Business Cache Strategies initialized")
    
    def _initialize_strategy_policies(self) -> Dict[str, CachePolicy]:
        """Initialize predefined cache policies for different data types."""
        return {
            # User data caching
            "user_profile": CachePolicy(
                strategy=CacheStrategy.USER_SESSION_SCOPED,
                ttl_seconds=1800,  # 30 minutes
                invalidation_triggers=["user_update", "profile_change"]
            ),
            
            # Cost analysis results (expensive to generate)
            "cost_analysis_results": CachePolicy(
                strategy=CacheStrategy.LONG_LIVED_WITH_VERSIONING,
                ttl_seconds=7200,  # 2 hours
                compression_enabled=True,
                invalidation_triggers=["data_refresh", "analysis_rerun"]
            ),
            
            # Optimization recommendations
            "optimization_recommendations": CachePolicy(
                strategy=CacheStrategy.ANALYSIS_SCOPED,
                ttl_seconds=3600,  # 1 hour
                invalidation_triggers=["recommendations_update", "analysis_change"]
            ),
            
            # Performance metrics (frequent access)
            "performance_metrics": CachePolicy(
                strategy=CacheStrategy.SHORT_LIVED,
                ttl_seconds=300,  # 5 minutes
                max_size_mb=10.0
            ),
            
            # Business insights (moderate frequency)
            "business_insights": CachePolicy(
                strategy=CacheStrategy.MEDIUM_LIVED,
                ttl_seconds=1800,  # 30 minutes
                compression_enabled=True
            ),
            
            # Configuration data (infrequent changes)
            "configuration_data": CachePolicy(
                strategy=CacheStrategy.LONG_LIVED,
                ttl_seconds=14400,  # 4 hours
                invalidation_triggers=["config_update"]
            )
        }
    
    def generate_business_cache_key(self, data_type: str, data: Dict[str, Any], 
                                  user_id: Optional[str] = None,
                                  organization_id: Optional[str] = None) -> str:
        """
        Generate business-aware cache key for data.
        
        Args:
            data_type: Type of business data being cached
            data: The data being cached (used for key generation)
            user_id: Optional user ID for user-scoped caching
            organization_id: Optional organization ID for org-scoped caching
            
        Returns:
            Generated cache key string
        """
        # Start with data type prefix
        key_parts = [f"business:{data_type}"]
        
        # Add scope identifiers
        if organization_id:
            key_parts.append(f"org:{organization_id}")
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        # Generate content hash for data uniqueness
        if data:
            # Extract key fields for hash generation
            hash_data = self._extract_hash_fields(data_type, data)
            content_hash = self._generate_content_hash(hash_data)
            key_parts.append(f"hash:{content_hash}")
        
        cache_key = ":".join(key_parts)
        logger.debug(f"Generated cache key for {data_type}: {cache_key}")
        
        return cache_key
    
    def _extract_hash_fields(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields relevant for cache key generation based on data type."""
        if data_type == "cost_analysis_results":
            return {
                "aws_account_id": data.get("aws_account_id"),
                "analysis_id": data.get("analysis_id"),
                "month": data.get("month", datetime.now(timezone.utc).strftime("%Y-%m"))
            }
        elif data_type == "user_profile":
            return {
                "user_id": data.get("user_id"),
                "profile_version": data.get("profile_version", "latest")
            }
        elif data_type == "optimization_recommendations":
            return {
                "service_type": data.get("service_type"),
                "account_id": data.get("account_id"),
                "recommendation_type": data.get("recommendation_type")
            }
        else:
            # Default: use all data for hash (less efficient but safe)
            return data
    
    def _generate_content_hash(self, data: Dict[str, Any]) -> str:
        """Generate SHA-256 hash of data for cache key uniqueness."""
        # Sort keys for consistent hash generation
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(sorted_data.encode()).hexdigest()[:16]
    
    async def apply_caching_strategy(self, cache_manager, cache_key: str, 
                                   data: Dict[str, Any], data_type: str,
                                   strategy_override: Optional[str] = None) -> bool:
        """
        Apply appropriate caching strategy for business data.
        
        Args:
            cache_manager: Cache manager instance to use
            cache_key: Cache key for the data
            data: Data to cache
            data_type: Type of business data
            strategy_override: Optional strategy override
            
        Returns:
            True if data was successfully cached, False otherwise
        """
        try:
            # Get cache policy for data type
            cache_policy = self._get_cache_policy(data_type, strategy_override)
            
            # Apply caching with policy
            success = await cache_manager.set_cache(
                key=cache_key,
                data=data,
                ttl=cache_policy.ttl_seconds
            )
            
            if success:
                logger.info(f"Applied {cache_policy.strategy} strategy for {data_type}")
            else:
                logger.warning(f"Failed to apply caching strategy for {data_type}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error applying cache strategy for {data_type}: {e}")
            return False
    
    def _get_cache_policy(self, data_type: str, strategy_override: Optional[str] = None) -> CachePolicy:
        """Get cache policy for data type with optional strategy override."""
        if strategy_override and strategy_override in CacheStrategy.__members__.values():
            # Create policy with overridden strategy
            base_policy = self._strategy_policies.get(data_type, self._get_default_policy())
            return CachePolicy(
                strategy=CacheStrategy(strategy_override),
                ttl_seconds=base_policy.ttl_seconds,
                max_size_mb=base_policy.max_size_mb,
                invalidation_triggers=base_policy.invalidation_triggers,
                compression_enabled=base_policy.compression_enabled
            )
        
        return self._strategy_policies.get(data_type, self._get_default_policy())
    
    def _get_default_policy(self) -> CachePolicy:
        """Get default cache policy for unknown data types."""
        return CachePolicy(
            strategy=CacheStrategy.MEDIUM_LIVED,
            ttl_seconds=1800,  # 30 minutes default
            compression_enabled=False
        )
    
    async def invalidate_by_trigger(self, cache_manager, trigger: str, 
                                  user_id: Optional[str] = None,
                                  organization_id: Optional[str] = None) -> int:
        """
        Invalidate cached data based on business triggers.
        
        Args:
            cache_manager: Cache manager instance
            trigger: Invalidation trigger name
            user_id: Optional user ID for scoped invalidation
            organization_id: Optional organization ID for scoped invalidation
            
        Returns:
            Number of cache entries invalidated
        """
        try:
            # Build invalidation pattern based on trigger and scope
            invalidation_patterns = self._build_invalidation_patterns(
                trigger, user_id, organization_id
            )
            
            total_invalidated = 0
            for pattern in invalidation_patterns:
                count = await cache_manager.delete_pattern(pattern)
                total_invalidated += count
                logger.info(f"Invalidated {count} entries for pattern: {pattern}")
            
            logger.info(f"Total cache entries invalidated by trigger '{trigger}': {total_invalidated}")
            return total_invalidated
            
        except Exception as e:
            logger.error(f"Error invalidating cache by trigger '{trigger}': {e}")
            return 0
    
    def _build_invalidation_patterns(self, trigger: str, user_id: Optional[str] = None,
                                   organization_id: Optional[str] = None) -> List[str]:
        """Build cache key patterns for invalidation based on trigger."""
        patterns = []
        
        # Find data types that use this trigger
        affected_data_types = [
            data_type for data_type, policy in self._strategy_policies.items()
            if trigger in policy.invalidation_triggers
        ]
        
        for data_type in affected_data_types:
            if organization_id and user_id:
                patterns.append(f"business:{data_type}:org:{organization_id}:user:{user_id}:*")
            elif organization_id:
                patterns.append(f"business:{data_type}:org:{organization_id}:*")
            elif user_id:
                patterns.append(f"business:{data_type}:user:{user_id}:*")
            else:
                patterns.append(f"business:{data_type}:*")
        
        return patterns
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache strategy statistics and configuration."""
        return {
            "configured_strategies": len(self._strategy_policies),
            "data_types": list(self._strategy_policies.keys()),
            "strategy_distribution": {
                strategy.value: sum(1 for p in self._strategy_policies.values() 
                                  if p.strategy == strategy)
                for strategy in CacheStrategy
            },
            "avg_ttl_seconds": sum(p.ttl_seconds for p in self._strategy_policies.values()) / 
                             len(self._strategy_policies) if self._strategy_policies else 0
        }


# Export for import compatibility
__all__ = [
    'BusinessCacheStrategies',
    'CacheStrategy',
    'CachePolicy'
]