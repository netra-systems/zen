"""Agent Context Window Management L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise (long-running conversations)
- Business Goal: Efficient context management for complex AI workflows
- Value Impact: Protects $8K MRR from context overflow and memory issues
- Strategic Impact: Enables sophisticated multi-turn conversations

Critical Path: Context tracking -> Window management -> Compression -> Retrieval -> Optimization
Coverage: Real context handling, memory optimization, conversation continuity
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.config import get_settings
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class ContextPriority(Enum):
    """Priority levels for context segments."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVE = "archive"

class CompressionStrategy(Enum):
    """Strategies for context compression."""
    SUMMARIZATION = "summarization"
    KEYWORD_EXTRACTION = "keyword_extraction"
    SEMANTIC_CLUSTERING = "semantic_clustering"
    SLIDING_WINDOW = "sliding_window"
    HIERARCHICAL = "hierarchical"

@dataclass
class ContextSegment:
    """Represents a segment of conversation context."""
    segment_id: str
    agent_id: str
    session_id: str
    content: str
    role: str  # user, assistant, system
    token_count: int
    priority: ContextPriority
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_segment_id: Optional[str] = None
    compressed: bool = False
    embedding_vector: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            "segment_id": self.segment_id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "content": self.content,
            "role": self.role,
            "token_count": self.token_count,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "parent_segment_id": self.parent_segment_id,
            "compressed": self.compressed,
            "embedding_vector": self.embedding_vector
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextSegment":
        """Create from dictionary."""
        data["priority"] = ContextPriority(data["priority"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

@dataclass
class ContextWindow:
    """Represents the current context window for an agent."""
    agent_id: str
    session_id: str
    max_tokens: int
    current_tokens: int
    segments: List[ContextSegment]
    compression_threshold: float = 0.8  # Compress when 80% full
    last_compressed: Optional[datetime] = None
    
    def is_near_limit(self) -> bool:
        """Check if context window is near token limit."""
        return self.current_tokens / self.max_tokens >= self.compression_threshold
    
    def get_utilization(self) -> float:
        """Get current token utilization percentage."""
        return self.current_tokens / self.max_tokens if self.max_tokens > 0 else 0.0
    
    def add_segment(self, segment: ContextSegment) -> bool:
        """Add a segment to the context window."""
        if self.current_tokens + segment.token_count > self.max_tokens:
            return False
        
        self.segments.append(segment)
        self.current_tokens += segment.token_count
        return True
    
    def remove_segment(self, segment_id: str) -> bool:
        """Remove a segment from the context window."""
        for i, segment in enumerate(self.segments):
            if segment.segment_id == segment_id:
                self.current_tokens -= segment.token_count
                self.segments.pop(i)
                return True
        return False

class ContextCompressor:
    """Handles compression of context segments."""
    
    def __init__(self):
        self.compression_strategies = {
            CompressionStrategy.SUMMARIZATION: self._summarize_content,
            CompressionStrategy.KEYWORD_EXTRACTION: self._extract_keywords,
            CompressionStrategy.SEMANTIC_CLUSTERING: self._cluster_semantically,
            CompressionStrategy.SLIDING_WINDOW: self._sliding_window,
            CompressionStrategy.HIERARCHICAL: self._hierarchical_compression
        }
    
    async def compress_segments(self, 
                              segments: List[ContextSegment], 
                              strategy: CompressionStrategy,
                              target_reduction: float = 0.5) -> List[ContextSegment]:
        """Compress a list of context segments."""
        if strategy not in self.compression_strategies:
            raise ValueError(f"Unknown compression strategy: {strategy}")
        
        compression_func = self.compression_strategies[strategy]
        return await compression_func(segments, target_reduction)
    
    async def _summarize_content(self, segments: List[ContextSegment], target_reduction: float) -> List[ContextSegment]:
        """Compress by summarizing content."""
        if not segments:
            return segments
        
        # Group consecutive segments by role
        groups = []
        current_group = [segments[0]]
        
        for segment in segments[1:]:
            if segment.role == current_group[-1].role:
                current_group.append(segment)
            else:
                groups.append(current_group)
                current_group = [segment]
        
        if current_group:
            groups.append(current_group)
        
        compressed_segments = []
        
        for group in groups:
            if len(group) == 1:
                compressed_segments.append(group[0])
            else:
                # Combine multiple segments of same role
                combined_content = " ".join(seg.content for seg in group)
                
                # Mock summarization (in practice, use actual LLM)
                summary = await self._mock_summarize(combined_content, target_reduction)
                
                compressed_segment = ContextSegment(
                    segment_id=f"compressed_{group[0].segment_id}",
                    agent_id=group[0].agent_id,
                    session_id=group[0].session_id,
                    content=summary,
                    role=group[0].role,
                    token_count=int(sum(seg.token_count for seg in group) * target_reduction),
                    priority=max((seg.priority for seg in group), key=lambda p: p.value if hasattr(p, 'value') else p),
                    timestamp=group[-1].timestamp,
                    metadata={"original_segments": len(group), "compression_ratio": target_reduction},
                    compressed=True
                )
                compressed_segments.append(compressed_segment)
        
        return compressed_segments
    
    async def _extract_keywords(self, segments: List[ContextSegment], target_reduction: float) -> List[ContextSegment]:
        """Compress by extracting keywords."""
        compressed = []
        
        for segment in segments:
            if segment.priority in [ContextPriority.CRITICAL, ContextPriority.HIGH]:
                # Keep important segments as-is
                compressed.append(segment)
            else:
                # Extract keywords for less important segments
                keywords = await self._mock_extract_keywords(segment.content)
                
                compressed_segment = ContextSegment(
                    segment_id=f"keywords_{segment.segment_id}",
                    agent_id=segment.agent_id,
                    session_id=segment.session_id,
                    content=f"Keywords: {', '.join(keywords)}",
                    role=segment.role,
                    token_count=max(1, int(segment.token_count * 0.2)),  # 80% reduction
                    priority=ContextPriority.LOW,
                    timestamp=segment.timestamp,
                    metadata={"original_content_length": len(segment.content)},
                    compressed=True
                )
                compressed.append(compressed_segment)
        
        return compressed
    
    async def _cluster_semantically(self, segments: List[ContextSegment], target_reduction: float) -> List[ContextSegment]:
        """Compress by clustering semantically similar segments."""
        # Mock semantic clustering
        clusters = self._mock_semantic_clustering(segments)
        compressed = []
        
        for cluster in clusters:
            if len(cluster) == 1:
                compressed.append(cluster[0])
            else:
                # Merge semantically similar segments
                merged_content = "\n".join(seg.content for seg in cluster)
                summary = await self._mock_summarize(merged_content, target_reduction)
                
                merged_segment = ContextSegment(
                    segment_id=f"cluster_{cluster[0].segment_id}",
                    agent_id=cluster[0].agent_id,
                    session_id=cluster[0].session_id,
                    content=summary,
                    role=cluster[0].role,
                    token_count=int(sum(seg.token_count for seg in cluster) * target_reduction),
                    priority=max((seg.priority for seg in cluster), key=lambda p: p.value if hasattr(p, 'value') else p),
                    timestamp=cluster[-1].timestamp,
                    metadata={"cluster_size": len(cluster)},
                    compressed=True
                )
                compressed.append(merged_segment)
        
        return compressed
    
    async def _sliding_window(self, segments: List[ContextSegment], target_reduction: float) -> List[ContextSegment]:
        """Compress using sliding window approach."""
        if not segments:
            return segments
        
        # Keep recent segments, compress older ones
        keep_count = max(1, int(len(segments) * target_reduction))
        recent_segments = segments[-keep_count:]
        old_segments = segments[:-keep_count]
        
        if old_segments:
            # Create summary of old segments
            old_content = "\n".join(seg.content for seg in old_segments)
            summary = await self._mock_summarize(old_content, 0.3)  # Heavy compression for old content
            
            summary_segment = ContextSegment(
                segment_id=f"historical_{old_segments[0].segment_id}",
                agent_id=old_segments[0].agent_id,
                session_id=old_segments[0].session_id,
                content=f"Previous conversation summary: {summary}",
                role="system",
                token_count=int(sum(seg.token_count for seg in old_segments) * 0.1),
                priority=ContextPriority.MEDIUM,
                timestamp=old_segments[-1].timestamp,
                metadata={"summarized_segments": len(old_segments)},
                compressed=True
            )
            
            return [summary_segment] + recent_segments
        
        return recent_segments
    
    async def _hierarchical_compression(self, segments: List[ContextSegment], target_reduction: float) -> List[ContextSegment]:
        """Compress using hierarchical strategy based on priority."""
        # Sort by priority and timestamp
        priority_order = {
            ContextPriority.CRITICAL: 0,
            ContextPriority.HIGH: 1,
            ContextPriority.MEDIUM: 2,
            ContextPriority.LOW: 3,
            ContextPriority.ARCHIVE: 4
        }
        
        sorted_segments = sorted(segments, key=lambda s: (priority_order[s.priority], s.timestamp))
        
        compressed = []
        current_tokens = 0
        target_tokens = int(sum(seg.token_count for seg in segments) * target_reduction)
        
        # Always keep critical segments
        critical_segments = [s for s in sorted_segments if s.priority == ContextPriority.CRITICAL]
        for segment in critical_segments:
            compressed.append(segment)
            current_tokens += segment.token_count
        
        # Add other segments until target is reached
        remaining_segments = [s for s in sorted_segments if s.priority != ContextPriority.CRITICAL]
        
        for segment in remaining_segments:
            if current_tokens + segment.token_count <= target_tokens:
                compressed.append(segment)
                current_tokens += segment.token_count
            else:
                # Compress this segment if it doesn't fit
                compressed_content = await self._mock_summarize(segment.content, 0.5)
                compressed_segment = ContextSegment(
                    segment_id=f"compressed_{segment.segment_id}",
                    agent_id=segment.agent_id,
                    session_id=segment.session_id,
                    content=compressed_content,
                    role=segment.role,
                    token_count=int(segment.token_count * 0.5),
                    priority=segment.priority,
                    timestamp=segment.timestamp,
                    compressed=True
                )
                
                if current_tokens + compressed_segment.token_count <= target_tokens:
                    compressed.append(compressed_segment)
                    current_tokens += compressed_segment.token_count
        
        return compressed
    
    async def _mock_summarize(self, content: str, reduction_factor: float) -> str:
        """Mock summarization function."""
        await asyncio.sleep(0.01)  # Simulate processing time
        
        # Simple mock summarization
        words = content.split()
        keep_words = max(1, int(len(words) * reduction_factor))
        
        if keep_words >= len(words):
            return content
        
        return " ".join(words[:keep_words]) + "..."
    
    async def _mock_extract_keywords(self, content: str) -> List[str]:
        """Mock keyword extraction."""
        await asyncio.sleep(0.005)  # Simulate processing time
        
        # Simple mock keyword extraction
        words = content.lower().split()
        # Filter common words and take unique words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were"}
        keywords = [word for word in words if word not in common_words and len(word) > 3]
        return list(set(keywords))[:10]  # Return up to 10 unique keywords
    
    def _mock_semantic_clustering(self, segments: List[ContextSegment]) -> List[List[ContextSegment]]:
        """Mock semantic clustering."""
        # Simple clustering based on content similarity (mock)
        clusters = []
        used_segments = set()
        
        for i, segment in enumerate(segments):
            if segment.segment_id in used_segments:
                continue
            
            cluster = [segment]
            used_segments.add(segment.segment_id)
            
            # Find similar segments (mock similarity check)
            for j, other_segment in enumerate(segments[i+1:], i+1):
                if other_segment.segment_id in used_segments:
                    continue
                
                # Mock similarity based on common words
                words1 = set(segment.content.lower().split())
                words2 = set(other_segment.content.lower().split())
                similarity = len(words1 & words2) / len(words1 | words2) if words1 | words2 else 0
                
                if similarity > 0.3:  # Threshold for clustering
                    cluster.append(other_segment)
                    used_segments.add(other_segment.segment_id)
            
            clusters.append(cluster)
        
        return clusters

class ContextWindowManager:
    """Manages context windows for agents."""
    
    def __init__(self, redis_service: RedisService, db_manager: DatabaseConnectionManager):
        self.redis_service = redis_service
        self.db_manager = db_manager
        self.compressor = ContextCompressor()
        self.active_windows: Dict[str, ContextWindow] = {}
        self.default_max_tokens = 8000
        
    async def get_or_create_window(self, agent_id: str, session_id: str, max_tokens: int = None) -> ContextWindow:
        """Get or create a context window for an agent session."""
        window_key = f"{agent_id}:{session_id}"
        
        if window_key in self.active_windows:
            return self.active_windows[window_key]
        
        # Try to load from cache/database
        window = await self._load_window(agent_id, session_id)
        
        if not window:
            # Create new window
            window = ContextWindow(
                agent_id=agent_id,
                session_id=session_id,
                max_tokens=max_tokens or self.default_max_tokens,
                current_tokens=0,
                segments=[]
            )
        
        self.active_windows[window_key] = window
        return window
    
    async def add_message(self, 
                         agent_id: str, 
                         session_id: str, 
                         content: str, 
                         role: str,
                         priority: ContextPriority = ContextPriority.MEDIUM) -> str:
        """Add a message to the context window."""
        window = await self.get_or_create_window(agent_id, session_id)
        
        # Estimate token count (rough approximation)
        token_count = self._estimate_tokens(content)
        
        segment = ContextSegment(
            segment_id=f"{agent_id}_{session_id}_{int(time.time() * 1000)}",
            agent_id=agent_id,
            session_id=session_id,
            content=content,
            role=role,
            token_count=token_count,
            priority=priority,
            timestamp=datetime.now()
        )
        
        # Check if we need to compress before adding
        if window.current_tokens + token_count > window.max_tokens:
            await self._manage_window_capacity(window, token_count)
        
        # Add the segment
        success = window.add_segment(segment)
        
        if success:
            # Cache and persist
            await self._save_window(window)
            return segment.segment_id
        else:
            raise Exception("Failed to add segment to context window")
    
    async def _manage_window_capacity(self, window: ContextWindow, required_tokens: int):
        """Manage context window capacity through compression."""
        if not window.segments:
            return
        
        # Calculate how much space we need
        available_space = window.max_tokens - window.current_tokens
        space_needed = required_tokens - available_space
        
        if space_needed <= 0:
            return
        
        # Determine compression strategy based on window state
        if window.last_compressed and datetime.now() - window.last_compressed < timedelta(minutes=5):
            # Recent compression, use aggressive sliding window
            strategy = CompressionStrategy.SLIDING_WINDOW
            target_reduction = 0.3
        elif len(window.segments) > 50:
            # Many segments, use semantic clustering
            strategy = CompressionStrategy.SEMANTIC_CLUSTERING
            target_reduction = 0.5
        else:
            # Default to hierarchical compression
            strategy = CompressionStrategy.HIERARCHICAL
            target_reduction = 0.6
        
        # Compress segments
        compressed_segments = await self.compressor.compress_segments(
            window.segments.copy(),
            strategy,
            target_reduction
        )
        
        # Update window
        window.segments = compressed_segments
        window.current_tokens = sum(seg.token_count for seg in compressed_segments)
        window.last_compressed = datetime.now()
        
        logger.info(f"Compressed context window for {window.agent_id}:{window.session_id}. "
                   f"Tokens: {window.current_tokens}/{window.max_tokens}")
    
    async def get_context_for_prompt(self, agent_id: str, session_id: str, max_context_tokens: int = None) -> str:
        """Get formatted context for LLM prompt."""
        window = await self.get_or_create_window(agent_id, session_id)
        
        if not window.segments:
            return ""
        
        # Sort segments by timestamp
        sorted_segments = sorted(window.segments, key=lambda s: s.timestamp)
        
        context_parts = []
        token_count = 0
        max_tokens = max_context_tokens or (window.max_tokens // 2)  # Use half of window for prompt context
        
        # Add segments until we hit token limit
        for segment in reversed(sorted_segments):  # Most recent first
            if token_count + segment.token_count > max_tokens:
                break
            
            context_parts.insert(0, f"{segment.role}: {segment.content}")
            token_count += segment.token_count
        
        return "\n".join(context_parts)
    
    async def get_window_stats(self, agent_id: str, session_id: str) -> Dict[str, Any]:
        """Get statistics about a context window."""
        window = await self.get_or_create_window(agent_id, session_id)
        
        priority_counts = {}
        role_counts = {}
        compressed_count = 0
        
        for segment in window.segments:
            priority_counts[segment.priority.value] = priority_counts.get(segment.priority.value, 0) + 1
            role_counts[segment.role] = role_counts.get(segment.role, 0) + 1
            if segment.compressed:
                compressed_count += 1
        
        return {
            "total_segments": len(window.segments),
            "current_tokens": window.current_tokens,
            "max_tokens": window.max_tokens,
            "utilization": window.get_utilization(),
            "compressed_segments": compressed_count,
            "priority_distribution": priority_counts,
            "role_distribution": role_counts,
            "last_compressed": window.last_compressed.isoformat() if window.last_compressed else None
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough approximation: 1 token ≈ 4 characters
        return max(1, len(text) // 4)
    
    async def _load_window(self, agent_id: str, session_id: str) -> Optional[ContextWindow]:
        """Load context window from storage."""
        # Try Redis cache first
        cache_key = f"context_window:{agent_id}:{session_id}"
        cached_data = await self.redis_service.client.get(cache_key)
        
        if cached_data:
            try:
                window_data = json.loads(cached_data)
                segments = [ContextSegment.from_dict(seg_data) for seg_data in window_data["segments"]]
                
                window = ContextWindow(
                    agent_id=window_data["agent_id"],
                    session_id=window_data["session_id"],
                    max_tokens=window_data["max_tokens"],
                    current_tokens=window_data["current_tokens"],
                    segments=segments,
                    compression_threshold=window_data.get("compression_threshold", 0.8)
                )
                
                if window_data.get("last_compressed"):
                    window.last_compressed = datetime.fromisoformat(window_data["last_compressed"])
                
                return window
            except Exception as e:
                logger.error(f"Failed to load cached window: {e}")
        
        return None
    
    async def _save_window(self, window: ContextWindow):
        """Save context window to storage."""
        window_data = {
            "agent_id": window.agent_id,
            "session_id": window.session_id,
            "max_tokens": window.max_tokens,
            "current_tokens": window.current_tokens,
            "compression_threshold": window.compression_threshold,
            "segments": [seg.to_dict() for seg in window.segments],
            "last_compressed": window.last_compressed.isoformat() if window.last_compressed else None
        }
        
        # Cache in Redis
        cache_key = f"context_window:{window.agent_id}:{window.session_id}"
        await self.redis_service.client.setex(
            cache_key,
            3600,  # 1 hour TTL
            json.dumps(window_data)
        )
    
    async def cleanup_window(self, agent_id: str, session_id: str):
        """Clean up a context window."""
        window_key = f"{agent_id}:{session_id}"
        if window_key in self.active_windows:
            del self.active_windows[window_key]
        
        # Remove from cache
        cache_key = f"context_window:{agent_id}:{session_id}"
        await self.redis_service.client.delete(cache_key)

class ContextWindowTestManager:
    """Manages context window testing."""
    
    def __init__(self):
        self.redis_service = None
        self.db_manager = None
        self.context_manager = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.context_manager = ContextWindowManager(self.redis_service, self.db_manager)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()

@pytest.fixture
async def context_manager():
    """Create context window test manager."""
    manager = ContextWindowTestManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_context_window_creation(context_manager):
    """Test context window creation and basic operations."""
    manager = context_manager
    
    # Create a new context window
    window = await manager.context_manager.get_or_create_window("test_agent", "session_001")
    
    assert window.agent_id == "test_agent"
    assert window.session_id == "session_001"
    assert window.current_tokens == 0
    assert len(window.segments) == 0
    assert window.max_tokens > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_message_addition(context_manager):
    """Test adding messages to context window."""
    manager = context_manager
    
    # Add messages to context window
    segment_id1 = await manager.context_manager.add_message(
        "test_agent", "session_002", 
        "Hello, I need help with something", "user",
        ContextPriority.HIGH
    )
    
    segment_id2 = await manager.context_manager.add_message(
        "test_agent", "session_002",
        "I'd be happy to help! What do you need assistance with?", "assistant",
        ContextPriority.MEDIUM
    )
    
    assert segment_id1 is not None
    assert segment_id2 is not None
    
    # Verify window state
    window = await manager.context_manager.get_or_create_window("test_agent", "session_002")
    assert len(window.segments) == 2
    assert window.current_tokens > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_context_compression_summarization(context_manager):
    """Test context compression using summarization strategy."""
    manager = context_manager
    compressor = manager.context_manager.compressor
    
    # Create test segments
    segments = []
    for i in range(5):
        segment = ContextSegment(
            segment_id=f"test_seg_{i}",
            agent_id="test_agent",
            session_id="test_session",
            content=f"This is test message number {i} with some additional content to make it longer",
            role="user" if i % 2 == 0 else "assistant",
            token_count=20,
            priority=ContextPriority.MEDIUM,
            timestamp=datetime.now() + timedelta(seconds=i)
        )
        segments.append(segment)
    
    # Compress using summarization
    compressed = await compressor.compress_segments(
        segments, CompressionStrategy.SUMMARIZATION, 0.5
    )
    
    assert len(compressed) <= len(segments)
    
    # Verify token reduction
    original_tokens = sum(seg.token_count for seg in segments)
    compressed_tokens = sum(seg.token_count for seg in compressed)
    assert compressed_tokens < original_tokens

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_context_compression_keywords(context_manager):
    """Test context compression using keyword extraction."""
    manager = context_manager
    compressor = manager.context_manager.compressor
    
    # Create segments with different priorities
    segments = [
        ContextSegment(
            segment_id="critical_seg",
            agent_id="test_agent",
            session_id="test_session",
            content="This is critical information that must be preserved completely",
            role="system",
            token_count=15,
            priority=ContextPriority.CRITICAL,
            timestamp=datetime.now()
        ),
        ContextSegment(
            segment_id="low_seg",
            agent_id="test_agent",
            session_id="test_session",
            content="This is less important information that can be compressed to keywords",
            role="user",
            token_count=15,
            priority=ContextPriority.LOW,
            timestamp=datetime.now()
        )
    ]
    
    # Compress using keyword extraction
    compressed = await compressor.compress_segments(
        segments, CompressionStrategy.KEYWORD_EXTRACTION, 0.6
    )
    
    # Critical segment should be preserved
    critical_preserved = any(seg.segment_id == "critical_seg" for seg in compressed)
    assert critical_preserved
    
    # Low priority segment should be compressed to keywords
    keyword_segment = next(seg for seg in compressed if seg.segment_id.startswith("keywords_"))
    assert "Keywords:" in keyword_segment.content

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_sliding_window_compression(context_manager):
    """Test sliding window compression strategy."""
    manager = context_manager
    compressor = manager.context_manager.compressor
    
    # Create many segments to simulate long conversation
    segments = []
    for i in range(10):
        segment = ContextSegment(
            segment_id=f"slide_seg_{i}",
            agent_id="test_agent",
            session_id="test_session",
            content=f"Message {i}: This is content for message number {i}",
            role="user" if i % 2 == 0 else "assistant",
            token_count=10,
            priority=ContextPriority.MEDIUM,
            timestamp=datetime.now() + timedelta(seconds=i)
        )
        segments.append(segment)
    
    # Apply sliding window compression
    compressed = await compressor.compress_segments(
        segments, CompressionStrategy.SLIDING_WINDOW, 0.5
    )
    
    # Should have fewer segments
    assert len(compressed) < len(segments)
    
    # Should contain recent segments and a summary of old ones
    has_summary = any("summary" in seg.content.lower() for seg in compressed)
    assert has_summary

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_automatic_compression_on_capacity(context_manager):
    """Test automatic compression when context window reaches capacity."""
    manager = context_manager
    
    # Create a small context window
    window = await manager.context_manager.get_or_create_window("capacity_test", "session_001", max_tokens=200)
    
    # Add messages until capacity is reached
    message_count = 0
    while window.current_tokens < window.max_tokens * 0.7:  # Fill to 70%
        await manager.context_manager.add_message(
            "capacity_test", "session_001",
            f"This is message {message_count} with enough content to consume tokens in the context window",
            "user" if message_count % 2 == 0 else "assistant",
            ContextPriority.MEDIUM
        )
        message_count += 1
        window = await manager.context_manager.get_or_create_window("capacity_test", "session_001")
    
    initial_token_count = window.current_tokens
    initial_segment_count = len(window.segments)
    
    # Add one more large message to trigger compression
    await manager.context_manager.add_message(
        "capacity_test", "session_001",
        "This is a very long message that should trigger compression because it will exceed the context window capacity limit",
        "user",
        ContextPriority.HIGH
    )
    
    # Verify compression occurred
    window = await manager.context_manager.get_or_create_window("capacity_test", "session_001")
    assert window.last_compressed is not None
    
    # Should have compressed content
    compressed_segments = [seg for seg in window.segments if seg.compressed]
    assert len(compressed_segments) > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_context_prompt_generation(context_manager):
    """Test generating context for LLM prompts."""
    manager = context_manager
    
    # Add several messages
    messages = [
        ("user", "What is machine learning?"),
        ("assistant", "Machine learning is a subset of AI that enables systems to learn from data."),
        ("user", "Can you give me an example?"),
        ("assistant", "Sure! Email spam detection is a common example of machine learning."),
        ("user", "How does it work?")
    ]
    
    for role, content in messages:
        await manager.context_manager.add_message(
            "prompt_test", "session_001", content, role, ContextPriority.HIGH
        )
    
    # Generate context for prompt
    context = await manager.context_manager.get_context_for_prompt("prompt_test", "session_001", max_context_tokens=100)
    
    assert len(context) > 0
    assert "machine learning" in context.lower()
    assert "user:" in context
    assert "assistant:" in context

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_window_statistics(context_manager):
    """Test context window statistics generation."""
    manager = context_manager
    
    # Add messages with different priorities and roles
    await manager.context_manager.add_message("stats_test", "session_001", "Critical message", "system", ContextPriority.CRITICAL)
    await manager.context_manager.add_message("stats_test", "session_001", "User question", "user", ContextPriority.HIGH)
    await manager.context_manager.add_message("stats_test", "session_001", "Assistant response", "assistant", ContextPriority.MEDIUM)
    await manager.context_manager.add_message("stats_test", "session_001", "Follow-up", "user", ContextPriority.LOW)
    
    # Get statistics
    stats = await manager.context_manager.get_window_stats("stats_test", "session_001")
    
    assert stats["total_segments"] == 4
    assert stats["current_tokens"] > 0
    assert stats["utilization"] > 0
    assert "priority_distribution" in stats
    assert "role_distribution" in stats
    
    # Verify priority distribution
    assert stats["priority_distribution"]["critical"] == 1
    assert stats["priority_distribution"]["high"] == 1
    assert stats["priority_distribution"]["medium"] == 1
    assert stats["priority_distribution"]["low"] == 1
    
    # Verify role distribution
    assert stats["role_distribution"]["system"] == 1
    assert stats["role_distribution"]["user"] == 2
    assert stats["role_distribution"]["assistant"] == 1

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_window_persistence_and_recovery(context_manager):
    """Test context window persistence and recovery from cache."""
    manager = context_manager
    
    # Add messages to a window
    await manager.context_manager.add_message("persist_test", "session_001", "First message", "user")
    await manager.context_manager.add_message("persist_test", "session_001", "Second message", "assistant")
    
    # Get initial window state
    original_window = await manager.context_manager.get_or_create_window("persist_test", "session_001")
    original_token_count = original_window.current_tokens
    original_segment_count = len(original_window.segments)
    
    # Clear active windows to simulate restart
    manager.context_manager.active_windows.clear()
    
    # Retrieve window again (should load from cache)
    recovered_window = await manager.context_manager.get_or_create_window("persist_test", "session_001")
    
    assert recovered_window.current_tokens == original_token_count
    assert len(recovered_window.segments) == original_segment_count
    assert recovered_window.agent_id == "persist_test"
    assert recovered_window.session_id == "session_001"

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_context_operations(context_manager):
    """Test concurrent context window operations."""
    manager = context_manager
    
    # Create multiple concurrent operations
    tasks = []
    for i in range(20):
        task = manager.context_manager.add_message(
            f"concurrent_agent_{i % 3}",  # 3 different agents
            f"session_{i % 2}",          # 2 sessions each
            f"Concurrent message {i}",
            "user" if i % 2 == 0 else "assistant",
            ContextPriority.MEDIUM
        )
        tasks.append(task)
    
    # Execute concurrently
    segment_ids = await asyncio.gather(*tasks)
    
    assert len(segment_ids) == 20
    assert all(segment_id is not None for segment_id in segment_ids)
    
    # Verify final state
    for agent_idx in range(3):
        for session_idx in range(2):
            window = await manager.context_manager.get_or_create_window(
                f"concurrent_agent_{agent_idx}",
                f"session_{session_idx}"
            )
            # Each window should have some messages
            assert len(window.segments) > 0

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_context_window_performance(context_manager):
    """Benchmark context window performance."""
    manager = context_manager
    
    # Benchmark message addition
    start_time = time.time()
    
    tasks = []
    for i in range(100):
        task = manager.context_manager.add_message(
            "perf_agent",
            "perf_session",
            f"Performance test message {i} with some content to simulate real usage",
            "user" if i % 2 == 0 else "assistant",
            ContextPriority.MEDIUM
        )
        tasks.append(task)
    
    segment_ids = await asyncio.gather(*tasks)
    add_time = time.time() - start_time
    
    assert len(segment_ids) == 100
    
    # Benchmark context retrieval
    start_time = time.time()
    
    retrieval_tasks = []
    for i in range(50):
        task = manager.context_manager.get_context_for_prompt("perf_agent", "perf_session", max_context_tokens=1000)
        retrieval_tasks.append(task)
    
    contexts = await asyncio.gather(*retrieval_tasks)
    retrieval_time = time.time() - start_time
    
    assert len(contexts) == 50
    assert all(len(context) > 0 for context in contexts)
    
    # Performance assertions
    assert add_time < 5.0  # 100 additions in under 5 seconds
    assert retrieval_time < 2.0  # 50 retrievals in under 2 seconds
    
    avg_add_time = add_time / 100
    avg_retrieval_time = retrieval_time / 50
    
    assert avg_add_time < 0.05  # Average addition under 50ms
    assert avg_retrieval_time < 0.04  # Average retrieval under 40ms
    
    logger.info(f"Context Performance: {avg_add_time*1000:.1f}ms add, {avg_retrieval_time*1000:.1f}ms retrieval")