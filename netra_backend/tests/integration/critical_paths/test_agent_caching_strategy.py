"""Agent Caching Strategy L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise (cost optimization and performance)
- Business Goal: Reduce API costs and improve response times through intelligent caching
- Value Impact: Protects $7K MRR from redundant API calls and latency issues
- Strategic Impact: Enables cost-effective scaling of AI operations

Critical Path: Cache key generation -> Hit/miss detection -> Storage -> Retrieval -> Invalidation
Coverage: Real caching strategies, TTL management, cache warming, intelligent invalidation
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

# Add project root to path


# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Different caching strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out
    ADAPTIVE = "adaptive"  # Adaptive based on usage patterns


class CacheType(Enum):
    """Types of caches."""
    RESPONSE_CACHE = "response_cache"
    EMBEDDING_CACHE = "embedding_cache"
    MODEL_CACHE = "model_cache"
    SESSION_CACHE = "session_cache"
    COMPUTATION_CACHE = "computation_cache"


class CacheInvalidationType(Enum):
    """Cache invalidation triggers."""
    MANUAL = "manual"
    TTL_EXPIRED = "ttl_expired"
    CAPACITY_LIMIT = "capacity_limit"
    DEPENDENCY_CHANGE = "dependency_change"
    PATTERN_MATCH = "pattern_match"


@dataclass
class CacheKey:
    """Represents a cache key with metadata."""
    key: str
    hash_key: str
    namespace: str
    cache_type: CacheType
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, namespace: str, cache_type: CacheType, **components) -> "CacheKey":
        """Create a cache key from components."""
        # Sort components for consistent key generation
        sorted_components = sorted(components.items())
        key_string = f"{namespace}:{cache_type.value}:" + ":".join(f"{k}={v}" for k, v in sorted_components)
        
        # Generate hash for efficient storage
        hash_key = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return cls(
            key=key_string,
            hash_key=hash_key,
            namespace=namespace,
            cache_type=cache_type
        )


@dataclass
class CacheEntry:
    """Represents a cached entry."""
    key: CacheKey
    value: Any
    size_bytes: int
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def access(self):
        """Record access to this cache entry."""
        self.access_count += 1
        self.last_accessed = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key.key,
            "hash_key": self.key.hash_key,
            "value": self.value,
            "size_bytes": self.size_bytes,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat(),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "tags": self.tags,
            "metadata": self.metadata
        }


class CacheMetrics:
    """Tracks cache performance metrics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.invalidations = 0
        self.total_size = 0
        self.entry_count = 0
        self.start_time = datetime.now()
        
    def record_hit(self, size_bytes: int = 0):
        """Record a cache hit."""
        self.hits += 1
        
    def record_miss(self):
        """Record a cache miss."""
        self.misses += 1
        
    def record_eviction(self, size_bytes: int):
        """Record a cache eviction."""
        self.evictions += 1
        self.total_size -= size_bytes
        self.entry_count -= 1
        
    def record_store(self, size_bytes: int):
        """Record storing an entry."""
        self.total_size += size_bytes
        self.entry_count += 1
        
    def record_invalidation(self, size_bytes: int):
        """Record a cache invalidation."""
        self.invalidations += 1
        self.total_size -= size_bytes
        self.entry_count -= 1
    
    def get_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total_requests = self.hits + self.misses
        return self.hits / total_requests if total_requests > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self.hits + self.misses
        runtime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_ratio": self.get_hit_ratio(),
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "entry_count": self.entry_count,
            "total_size_mb": self.total_size / (1024 * 1024),
            "avg_entry_size_kb": (self.total_size / self.entry_count / 1024) if self.entry_count > 0 else 0,
            "requests_per_hour": total_requests / runtime_hours if runtime_hours > 0 else 0,
            "runtime_hours": runtime_hours
        }


class CacheEvictionPolicy:
    """Base class for cache eviction policies."""
    
    def __init__(self, max_size_bytes: int):
        self.max_size_bytes = max_size_bytes
    
    def should_evict(self, current_size: int, new_entry_size: int) -> bool:
        """Check if eviction is needed."""
        return current_size + new_entry_size > self.max_size_bytes
    
    def select_eviction_candidates(self, entries: List[CacheEntry], required_space: int) -> List[CacheEntry]:
        """Select entries for eviction."""
        raise NotImplementedError


class LRUEvictionPolicy(CacheEvictionPolicy):
    """Least Recently Used eviction policy."""
    
    def select_eviction_candidates(self, entries: List[CacheEntry], required_space: int) -> List[CacheEntry]:
        """Select LRU entries for eviction."""
        # Sort by last accessed time (oldest first)
        sorted_entries = sorted(entries, key=lambda e: e.last_accessed)
        
        candidates = []
        freed_space = 0
        
        for entry in sorted_entries:
            if not entry.is_expired():  # Don't count expired entries
                candidates.append(entry)
                freed_space += entry.size_bytes
                
                if freed_space >= required_space:
                    break
        
        return candidates


class LFUEvictionPolicy(CacheEvictionPolicy):
    """Least Frequently Used eviction policy."""
    
    def select_eviction_candidates(self, entries: List[CacheEntry], required_space: int) -> List[CacheEntry]:
        """Select LFU entries for eviction."""
        # Sort by access count (least accessed first)
        sorted_entries = sorted(entries, key=lambda e: e.access_count)
        
        candidates = []
        freed_space = 0
        
        for entry in sorted_entries:
            if not entry.is_expired():
                candidates.append(entry)
                freed_space += entry.size_bytes
                
                if freed_space >= required_space:
                    break
        
        return candidates


class AdaptiveEvictionPolicy(CacheEvictionPolicy):
    """Adaptive eviction policy that considers multiple factors."""
    
    def select_eviction_candidates(self, entries: List[CacheEntry], required_space: int) -> List[CacheEntry]:
        """Select entries using adaptive scoring."""
        # Calculate adaptive score for each entry
        now = datetime.now()
        scored_entries = []
        
        for entry in entries:
            if entry.is_expired():
                continue
                
            # Factors: recency, frequency, size, age
            time_since_access = (now - entry.last_accessed).total_seconds()
            age = (now - entry.created_at).total_seconds()
            
            # Lower score = higher priority for eviction
            score = (
                time_since_access / 3600 +  # Hours since last access
                1 / (entry.access_count + 1) +  # Inverse frequency
                entry.size_bytes / (1024 * 1024) +  # Size in MB
                age / (24 * 3600)  # Age in days
            )
            
            scored_entries.append((score, entry))
        
        # Sort by score (highest score = first to evict)
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        
        candidates = []
        freed_space = 0
        
        for score, entry in scored_entries:
            candidates.append(entry)
            freed_space += entry.size_bytes
            
            if freed_space >= required_space:
                break
        
        return candidates


class CacheStorage:
    """Handles cache storage operations."""
    
    def __init__(self, redis_service: RedisService, namespace: str = "agent_cache"):
        self.redis_service = redis_service
        self.namespace = namespace
        self.local_entries: Dict[str, CacheEntry] = {}
        self.metrics = CacheMetrics()
        
    async def get(self, cache_key: CacheKey) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        # Try local cache first
        if cache_key.hash_key in self.local_entries:
            entry = self.local_entries[cache_key.hash_key]
            if not entry.is_expired():
                entry.access()
                self.metrics.record_hit(entry.size_bytes)
                return entry
            else:
                # Remove expired entry
                del self.local_entries[cache_key.hash_key]
                self.metrics.record_invalidation(entry.size_bytes)
        
        # Try Redis cache
        redis_key = f"{self.namespace}:{cache_key.hash_key}"
        cached_data = await self.redis_service.client.get(redis_key)
        
        if cached_data:
            try:
                entry_data = json.loads(cached_data)
                
                # Reconstruct cache entry
                entry = CacheEntry(
                    key=cache_key,
                    value=entry_data["value"],
                    size_bytes=entry_data["size_bytes"],
                    access_count=entry_data["access_count"],
                    last_accessed=datetime.fromisoformat(entry_data["last_accessed"]),
                    created_at=datetime.fromisoformat(entry_data["created_at"]),
                    expires_at=datetime.fromisoformat(entry_data["expires_at"]) if entry_data["expires_at"] else None,
                    tags=entry_data.get("tags", []),
                    metadata=entry_data.get("metadata", {})
                )
                
                if not entry.is_expired():
                    entry.access()
                    self.local_entries[cache_key.hash_key] = entry
                    self.metrics.record_hit(entry.size_bytes)
                    return entry
                else:
                    # Remove expired entry from Redis
                    await self.redis_service.client.delete(redis_key)
                    
            except Exception as e:
                logger.warning(f"Failed to deserialize cache entry: {e}")
        
        self.metrics.record_miss()
        return None
    
    async def set(self, cache_key: CacheKey, value: Any, ttl_seconds: Optional[int] = None, tags: List[str] = None) -> bool:
        """Set cache entry."""
        try:
            # Calculate size (rough estimation)
            size_bytes = len(json.dumps(value).encode('utf-8'))
            
            # Create cache entry
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            
            entry = CacheEntry(
                key=cache_key,
                value=value,
                size_bytes=size_bytes,
                expires_at=expires_at,
                tags=tags or []
            )
            
            # Store in local cache
            self.local_entries[cache_key.hash_key] = entry
            self.metrics.record_store(size_bytes)
            
            # Store in Redis
            redis_key = f"{self.namespace}:{cache_key.hash_key}"
            entry_data = json.dumps(entry.to_dict())
            
            if ttl_seconds:
                await self.redis_service.client.setex(redis_key, ttl_seconds, entry_data)
            else:
                await self.redis_service.client.set(redis_key, entry_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache entry: {e}")
            return False
    
    async def delete(self, cache_key: CacheKey) -> bool:
        """Delete cache entry."""
        try:
            # Remove from local cache
            if cache_key.hash_key in self.local_entries:
                entry = self.local_entries[cache_key.hash_key]
                del self.local_entries[cache_key.hash_key]
                self.metrics.record_invalidation(entry.size_bytes)
            
            # Remove from Redis
            redis_key = f"{self.namespace}:{cache_key.hash_key}"
            result = await self.redis_service.client.delete(redis_key)
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete cache entry: {e}")
            return False
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate cache entries by tags."""
        invalidated = 0
        entries_to_remove = []
        
        for hash_key, entry in self.local_entries.items():
            if any(tag in entry.tags for tag in tags):
                entries_to_remove.append(hash_key)
        
        for hash_key in entries_to_remove:
            entry = self.local_entries[hash_key]
            del self.local_entries[hash_key]
            self.metrics.record_invalidation(entry.size_bytes)
            
            # Also remove from Redis
            redis_key = f"{self.namespace}:{hash_key}"
            await self.redis_service.client.delete(redis_key)
            invalidated += 1
        
        return invalidated
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries."""
        expired_keys = []
        
        for hash_key, entry in self.local_entries.items():
            if entry.is_expired():
                expired_keys.append(hash_key)
        
        for hash_key in expired_keys:
            entry = self.local_entries[hash_key]
            del self.local_entries[hash_key]
            self.metrics.record_invalidation(entry.size_bytes)
        
        return len(expired_keys)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        return self.metrics.get_stats()


class AgentCacheManager:
    """Manages caching for AI agent operations."""
    
    def __init__(self, storage: CacheStorage, eviction_policy: CacheEvictionPolicy):
        self.storage = storage
        self.eviction_policy = eviction_policy
        self.cache_warming_enabled = True
        self.auto_cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
        
    async def get_cached_response(self, 
                                agent_id: str, 
                                input_text: str, 
                                model: str,
                                temperature: float = 0.7,
                                max_tokens: int = 2000) -> Optional[str]:
        """Get cached response for agent input."""
        
        # Create cache key
        cache_key = CacheKey.create(
            namespace=f"agent:{agent_id}",
            cache_type=CacheType.RESPONSE_CACHE,
            input_hash=hashlib.md5(input_text.encode()).hexdigest(),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Try to get from cache
        entry = await self.storage.get(cache_key)
        
        if entry:
            logger.info(f"Cache hit for agent {agent_id}")
            return entry.value
        
        logger.info(f"Cache miss for agent {agent_id}")
        return None
    
    async def cache_response(self, 
                           agent_id: str, 
                           input_text: str, 
                           response: str,
                           model: str,
                           temperature: float = 0.7,
                           max_tokens: int = 2000,
                           ttl_seconds: int = 3600) -> bool:
        """Cache agent response."""
        
        # Create cache key
        cache_key = CacheKey.create(
            namespace=f"agent:{agent_id}",
            cache_type=CacheType.RESPONSE_CACHE,
            input_hash=hashlib.md5(input_text.encode()).hexdigest(),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Cache with tags for easy invalidation
        tags = [f"agent:{agent_id}", f"model:{model}", "response_cache"]
        
        return await self.storage.set(cache_key, response, ttl_seconds, tags)
    
    async def get_cached_embedding(self, text: str, model: str) -> Optional[List[float]]:
        """Get cached text embedding."""
        
        cache_key = CacheKey.create(
            namespace="embeddings",
            cache_type=CacheType.EMBEDDING_CACHE,
            text_hash=hashlib.sha256(text.encode()).hexdigest(),
            model=model
        )
        
        entry = await self.storage.get(cache_key)
        return entry.value if entry else None
    
    async def cache_embedding(self, text: str, model: str, embedding: List[float], ttl_seconds: int = 86400) -> bool:
        """Cache text embedding."""
        
        cache_key = CacheKey.create(
            namespace="embeddings",
            cache_type=CacheType.EMBEDDING_CACHE,
            text_hash=hashlib.sha256(text.encode()).hexdigest(),
            model=model
        )
        
        tags = [f"model:{model}", "embedding_cache"]
        return await self.storage.set(cache_key, embedding, ttl_seconds, tags)
    
    async def get_cached_computation(self, computation_id: str, parameters: Dict[str, Any]) -> Optional[Any]:
        """Get cached computation result."""
        
        param_hash = hashlib.md5(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        
        cache_key = CacheKey.create(
            namespace="computations",
            cache_type=CacheType.COMPUTATION_CACHE,
            computation_id=computation_id,
            param_hash=param_hash
        )
        
        entry = await self.storage.get(cache_key)
        return entry.value if entry else None
    
    async def cache_computation(self, 
                              computation_id: str, 
                              parameters: Dict[str, Any], 
                              result: Any,
                              ttl_seconds: int = 1800) -> bool:
        """Cache computation result."""
        
        param_hash = hashlib.md5(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        
        cache_key = CacheKey.create(
            namespace="computations",
            cache_type=CacheType.COMPUTATION_CACHE,
            computation_id=computation_id,
            param_hash=param_hash
        )
        
        tags = [f"computation:{computation_id}", "computation_cache"]
        return await self.storage.set(cache_key, result, ttl_seconds, tags)
    
    async def warm_cache(self, agent_id: str, common_inputs: List[str], model: str) -> int:
        """Warm cache with common inputs."""
        if not self.cache_warming_enabled:
            return 0
        
        warmed = 0
        
        for input_text in common_inputs:
            # Check if already cached
            cached = await self.get_cached_response(agent_id, input_text, model)
            
            if not cached:
                # Generate and cache response (mock)
                mock_response = f"Pre-warmed response for: {input_text[:50]}..."
                success = await self.cache_response(agent_id, input_text, mock_response, model)
                if success:
                    warmed += 1
        
        return warmed
    
    async def invalidate_agent_cache(self, agent_id: str) -> int:
        """Invalidate all cache entries for an agent."""
        return await self.storage.invalidate_by_tags([f"agent:{agent_id}"])
    
    async def invalidate_model_cache(self, model: str) -> int:
        """Invalidate all cache entries for a model."""
        return await self.storage.invalidate_by_tags([f"model:{model}"])
    
    async def periodic_cleanup(self) -> Dict[str, int]:
        """Perform periodic cache cleanup."""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self.auto_cleanup_interval:
            return {"expired_removed": 0, "evicted": 0}
        
        self._last_cleanup = current_time
        
        # Clean up expired entries
        expired_removed = self.storage.cleanup_expired()
        
        # Check if eviction is needed
        evicted = 0
        current_size = self.storage.metrics.total_size
        
        if current_size > self.eviction_policy.max_size_bytes:
            required_space = current_size - self.eviction_policy.max_size_bytes
            candidates = self.eviction_policy.select_eviction_candidates(
                list(self.storage.local_entries.values()),
                required_space
            )
            
            for entry in candidates:
                await self.storage.delete(entry.key)
                evicted += 1
        
        return {"expired_removed": expired_removed, "evicted": evicted}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return self.storage.get_metrics()


class CacheTestManager:
    """Manages cache testing."""
    
    def __init__(self):
        self.redis_service = None
        self.storage = None
        self.cache_manager = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        # Initialize with LRU eviction policy (10MB limit)
        eviction_policy = LRUEvictionPolicy(max_size_bytes=10 * 1024 * 1024)
        
        self.storage = CacheStorage(self.redis_service, namespace="test_cache")
        self.cache_manager = AgentCacheManager(self.storage, eviction_policy)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()


@pytest.fixture
async def cache_manager():
    """Create cache test manager."""
    manager = CacheTestManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_basic_cache_operations(cache_manager):
    """Test basic cache set and get operations."""
    manager = cache_manager
    
    # Test caching a response
    cache_success = await manager.cache_manager.cache_response(
        agent_id="test_agent_001",
        input_text="What is machine learning?",
        response="Machine learning is a subset of AI that enables systems to learn from data.",
        model="gpt-4",
        temperature=0.7,
        ttl_seconds=3600
    )
    
    assert cache_success is True
    
    # Test retrieving cached response
    cached_response = await manager.cache_manager.get_cached_response(
        agent_id="test_agent_001",
        input_text="What is machine learning?",
        model="gpt-4",
        temperature=0.7
    )
    
    assert cached_response is not None
    assert "Machine learning" in cached_response


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cache_key_generation(cache_manager):
    """Test cache key generation and uniqueness."""
    manager = cache_manager
    
    # Test that same inputs generate same cache key
    key1 = CacheKey.create(
        namespace="test",
        cache_type=CacheType.RESPONSE_CACHE,
        input="hello",
        model="gpt-4"
    )
    
    key2 = CacheKey.create(
        namespace="test",
        cache_type=CacheType.RESPONSE_CACHE,
        input="hello",
        model="gpt-4"
    )
    
    assert key1.hash_key == key2.hash_key
    
    # Test that different inputs generate different cache keys
    key3 = CacheKey.create(
        namespace="test",
        cache_type=CacheType.RESPONSE_CACHE,
        input="hello",
        model="gpt-3.5"  # Different model
    )
    
    assert key1.hash_key != key3.hash_key


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cache_hit_miss_ratio(cache_manager):
    """Test cache hit/miss ratio tracking."""
    manager = cache_manager
    
    # Prime cache with some responses
    responses = [
        ("What is AI?", "AI is artificial intelligence."),
        ("What is ML?", "ML is machine learning."),
        ("What is DL?", "DL is deep learning.")
    ]
    
    for input_text, response in responses:
        await manager.cache_manager.cache_response(
            agent_id="hit_test_agent",
            input_text=input_text,
            response=response,
            model="gpt-4"
        )
    
    # Test cache hits
    for input_text, expected_response in responses:
        cached = await manager.cache_manager.get_cached_response(
            agent_id="hit_test_agent",
            input_text=input_text,
            model="gpt-4"
        )
        assert cached == expected_response
    
    # Test cache misses
    miss1 = await manager.cache_manager.get_cached_response(
        agent_id="hit_test_agent",
        input_text="What is NLP?",  # Not cached
        model="gpt-4"
    )
    assert miss1 is None
    
    # Check metrics
    stats = manager.cache_manager.get_cache_stats()
    assert stats["hits"] >= 3
    assert stats["misses"] >= 1
    assert stats["hit_ratio"] > 0.0


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_embedding_caching(cache_manager):
    """Test embedding caching functionality."""
    manager = cache_manager
    
    # Cache an embedding
    text = "This is a test sentence for embedding"
    model = "text-embedding-ada-002"
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 200  # Mock 1000-dimensional embedding
    
    cache_success = await manager.cache_manager.cache_embedding(text, model, embedding)
    assert cache_success is True
    
    # Retrieve cached embedding
    cached_embedding = await manager.cache_manager.get_cached_embedding(text, model)
    assert cached_embedding is not None
    assert len(cached_embedding) == 1000
    assert cached_embedding == embedding
    
    # Test cache miss for different text
    miss_embedding = await manager.cache_manager.get_cached_embedding("Different text", model)
    assert miss_embedding is None


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_computation_caching(cache_manager):
    """Test computation result caching."""
    manager = cache_manager
    
    # Cache a computation result
    computation_id = "similarity_calculation"
    parameters = {"text1": "hello", "text2": "hi", "method": "cosine"}
    result = {"similarity": 0.85, "confidence": 0.92}
    
    cache_success = await manager.cache_manager.cache_computation(
        computation_id, parameters, result
    )
    assert cache_success is True
    
    # Retrieve cached computation
    cached_result = await manager.cache_manager.get_cached_computation(
        computation_id, parameters
    )
    assert cached_result is not None
    assert cached_result["similarity"] == 0.85
    
    # Test cache miss for different parameters
    different_params = {"text1": "hello", "text2": "goodbye", "method": "cosine"}
    miss_result = await manager.cache_manager.get_cached_computation(
        computation_id, different_params
    )
    assert miss_result is None


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cache_ttl_expiration(cache_manager):
    """Test cache TTL and expiration."""
    manager = cache_manager
    
    # Cache with short TTL
    await manager.cache_manager.cache_response(
        agent_id="ttl_test_agent",
        input_text="TTL test question",
        response="TTL test response",
        model="gpt-4",
        ttl_seconds=1  # 1 second TTL
    )
    
    # Should be available immediately
    cached = await manager.cache_manager.get_cached_response(
        agent_id="ttl_test_agent",
        input_text="TTL test question",
        model="gpt-4"
    )
    assert cached is not None
    
    # Wait for TTL to expire
    await asyncio.sleep(2)
    
    # Should be expired and not available
    expired = await manager.cache_manager.get_cached_response(
        agent_id="ttl_test_agent",
        input_text="TTL test question",
        model="gpt-4"
    )
    assert expired is None


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cache_invalidation_by_tags(cache_manager):
    """Test cache invalidation by tags."""
    manager = cache_manager
    
    # Cache multiple responses for the same agent
    agent_id = "invalidation_test_agent"
    
    for i in range(3):
        await manager.cache_manager.cache_response(
            agent_id=agent_id,
            input_text=f"Question {i}",
            response=f"Response {i}",
            model="gpt-4"
        )
    
    # Verify all are cached
    for i in range(3):
        cached = await manager.cache_manager.get_cached_response(
            agent_id=agent_id,
            input_text=f"Question {i}",
            model="gpt-4"
        )
        assert cached is not None
    
    # Invalidate all cache entries for this agent
    invalidated_count = await manager.cache_manager.invalidate_agent_cache(agent_id)
    assert invalidated_count >= 3
    
    # Verify all are invalidated
    for i in range(3):
        cached = await manager.cache_manager.get_cached_response(
            agent_id=agent_id,
            input_text=f"Question {i}",
            model="gpt-4"
        )
        assert cached is None


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cache_warming(cache_manager):
    """Test cache warming functionality."""
    manager = cache_manager
    
    # Define common inputs for warming
    common_inputs = [
        "What is the weather today?",
        "How do I reset my password?",
        "What are your business hours?",
        "How can I contact support?"
    ]
    
    # Warm cache
    warmed_count = await manager.cache_manager.warm_cache(
        agent_id="warming_test_agent",
        common_inputs=common_inputs,
        model="gpt-4"
    )
    
    assert warmed_count == len(common_inputs)
    
    # Verify warmed entries are cached
    for input_text in common_inputs:
        cached = await manager.cache_manager.get_cached_response(
            agent_id="warming_test_agent",
            input_text=input_text,
            model="gpt-4"
        )
        assert cached is not None
        assert "Pre-warmed response" in cached


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_lru_eviction_policy(cache_manager):
    """Test LRU eviction policy."""
    manager = cache_manager
    
    # Set a small cache size for testing
    manager.cache_manager.eviction_policy.max_size_bytes = 1024  # 1KB
    
    # Cache entries that will exceed the limit
    large_responses = []
    for i in range(10):
        large_response = "X" * 200  # ~200 bytes each
        large_responses.append(large_response)
        
        await manager.cache_manager.cache_response(
            agent_id="eviction_test_agent",
            input_text=f"Large question {i}",
            response=large_response,
            model="gpt-4"
        )
    
    # Trigger cleanup/eviction
    cleanup_stats = await manager.cache_manager.periodic_cleanup()
    
    # Should have evicted some entries
    assert cleanup_stats["evicted"] > 0
    
    # Check that cache size is within limits
    stats = manager.cache_manager.get_cache_stats()
    assert stats["total_size_mb"] * 1024 * 1024 <= manager.cache_manager.eviction_policy.max_size_bytes


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cache_access_tracking(cache_manager):
    """Test cache access count tracking."""
    manager = cache_manager
    
    # Cache a response
    await manager.cache_manager.cache_response(
        agent_id="access_test_agent",
        input_text="Access tracking test",
        response="This response will be accessed multiple times",
        model="gpt-4"
    )
    
    # Access the cached response multiple times
    for i in range(5):
        cached = await manager.cache_manager.get_cached_response(
            agent_id="access_test_agent",
            input_text="Access tracking test",
            model="gpt-4"
        )
        assert cached is not None
    
    # Verify access count is tracked (check internal storage)
    cache_key = CacheKey.create(
        namespace="agent:access_test_agent",
        cache_type=CacheType.RESPONSE_CACHE,
        input_hash=hashlib.md5("Access tracking test".encode()).hexdigest(),
        model="gpt-4",
        temperature=0.7,
        max_tokens=2000
    )
    
    entry = manager.storage.local_entries.get(cache_key.hash_key)
    if entry:
        assert entry.access_count >= 5


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_cache_operations(cache_manager):
    """Test concurrent cache operations."""
    manager = cache_manager
    
    # Concurrent cache writes
    write_tasks = []
    for i in range(20):
        task = manager.cache_manager.cache_response(
            agent_id=f"concurrent_agent_{i % 3}",
            input_text=f"Concurrent question {i}",
            response=f"Concurrent response {i}",
            model="gpt-4"
        )
        write_tasks.append(task)
    
    write_results = await asyncio.gather(*write_tasks)
    assert all(write_results)
    
    # Concurrent cache reads
    read_tasks = []
    for i in range(20):
        task = manager.cache_manager.get_cached_response(
            agent_id=f"concurrent_agent_{i % 3}",
            input_text=f"Concurrent question {i}",
            model="gpt-4"
        )
        read_tasks.append(task)
    
    read_results = await asyncio.gather(*read_tasks)
    successful_reads = [r for r in read_results if r is not None]
    assert len(successful_reads) == 20


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cache_performance_benchmarks(cache_manager):
    """Benchmark cache performance."""
    manager = cache_manager
    
    # Benchmark cache writes
    start_time = time.time()
    
    write_tasks = []
    for i in range(100):
        task = manager.cache_manager.cache_response(
            agent_id=f"perf_agent_{i % 5}",
            input_text=f"Performance test question {i}",
            response=f"Performance test response {i} with some content",
            model="gpt-4"
        )
        write_tasks.append(task)
    
    write_results = await asyncio.gather(*write_tasks)
    write_time = time.time() - start_time
    
    assert all(write_results)
    
    # Benchmark cache reads
    start_time = time.time()
    
    read_tasks = []
    for i in range(100):
        task = manager.cache_manager.get_cached_response(
            agent_id=f"perf_agent_{i % 5}",
            input_text=f"Performance test question {i}",
            model="gpt-4"
        )
        read_tasks.append(task)
    
    read_results = await asyncio.gather(*read_tasks)
    read_time = time.time() - start_time
    
    assert len([r for r in read_results if r is not None]) == 100
    
    # Performance assertions
    assert write_time < 3.0  # 100 writes in under 3 seconds
    assert read_time < 1.0   # 100 reads in under 1 second
    
    avg_write_time = write_time / 100
    avg_read_time = read_time / 100
    
    assert avg_write_time < 0.03  # Average write under 30ms
    assert avg_read_time < 0.01   # Average read under 10ms
    
    # Check final cache statistics
    stats = manager.cache_manager.get_cache_stats()
    assert stats["hit_ratio"] > 0.9  # Should have high hit ratio
    
    logger.info(f"Cache Performance: {avg_write_time*1000:.1f}ms write, {avg_read_time*1000:.1f}ms read")
    logger.info(f"Cache Stats: {stats['hit_ratio']:.2%} hit ratio, {stats['entry_count']} entries")