"""Execution Timing Collector for Agent Performance Analysis

Provides comprehensive timing collection with:
- Hierarchical timing trees for nested operations
- Category-based aggregation (LLM, DB, Processing)
- Real-time performance metrics
- Bottleneck identification
- Integration with existing monitoring

Business Value: Enables 20-30% performance optimization through timing visibility.
BVJ: Platform | Development Velocity | Performance insights reduce debugging time
"""

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TimingCategory(Enum):
    """Categories for timing classification."""
    LLM = "llm"                     # LLM API calls
    DATABASE = "database"           # Database queries
    CACHE = "cache"                # Cache operations
    PROCESSING = "processing"       # Data processing/transformation
    NETWORK = "network"            # External API calls
    VALIDATION = "validation"       # Input/output validation
    ORCHESTRATION = "orchestration" # Agent coordination
    UNKNOWN = "unknown"


@dataclass
class TimingEntry:
    """Single timing measurement with metadata."""
    
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: str = ""                     # e.g., "triage_agent.process_query"
    category: TimingCategory = TimingCategory.UNKNOWN
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    error: Optional[str] = None
    
    def complete(self, error: Optional[str] = None) -> None:
        """Mark timing entry as complete."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.error = error
        
    @property
    def is_complete(self) -> bool:
        """Check if timing entry is complete."""
        return self.end_time is not None


@dataclass
class AggregateStats:
    """Aggregated timing statistics."""
    
    total_time_ms: float = 0.0
    count: int = 0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    operations: List[str] = field(default_factory=list)
    
    def add_entry(self, entry: TimingEntry) -> None:
        """Add timing entry to aggregation."""
        if entry.duration_ms is None:
            return
            
        self.total_time_ms += entry.duration_ms
        self.count += 1
        self.min_time_ms = min(self.min_time_ms, entry.duration_ms)
        self.max_time_ms = max(self.max_time_ms, entry.duration_ms)
        self.avg_time_ms = self.total_time_ms / self.count
        if entry.operation not in self.operations:
            self.operations.append(entry.operation)


@dataclass
class ExecutionTimingTree:
    """Hierarchical execution timing structure."""
    
    root_id: str
    correlation_id: str
    agent_name: str
    entries: Dict[str, TimingEntry] = field(default_factory=dict)
    children: Dict[str, List[str]] = field(default_factory=lambda: {})
    start_time: float = field(default_factory=time.perf_counter)
    
    def add_entry(self, entry: TimingEntry) -> None:
        """Add timing entry to tree."""
        self.entries[entry.entry_id] = entry
        
        if entry.parent_id:
            if entry.parent_id not in self.children:
                self.children[entry.parent_id] = []
            self.children[entry.parent_id].append(entry.entry_id)
    
    def get_total_duration_ms(self) -> float:
        """Get total execution duration."""
        root_entry = self.entries.get(self.root_id)
        if root_entry and root_entry.duration_ms:
            return root_entry.duration_ms
        return 0.0
    
    def get_critical_path(self) -> List[TimingEntry]:
        """Identify the critical path (longest execution chain)."""
        def find_longest_path(entry_id: str) -> Tuple[float, List[str]]:
            entry = self.entries.get(entry_id)
            if not entry or entry_id not in self.children:
                duration = entry.duration_ms if entry and entry.duration_ms else 0
                return duration, [entry_id]
            
            max_duration = 0
            max_path = []
            for child_id in self.children[entry_id]:
                child_duration, child_path = find_longest_path(child_id)
                if child_duration > max_duration:
                    max_duration = child_duration
                    max_path = child_path
            
            total_duration = (entry.duration_ms or 0) + max_duration
            return total_duration, [entry_id] + max_path
        
        _, path_ids = find_longest_path(self.root_id)
        return [self.entries[eid] for eid in path_ids if eid in self.entries]


class ExecutionTimingCollector:
    """Collects and manages execution timing data."""
    
    def __init__(self, agent_name: str = "unknown"):
        """Initialize timing collector.
        
        Args:
            agent_name: Name of the agent using this collector
        """
        self.agent_name = agent_name
        self.current_tree: Optional[ExecutionTimingTree] = None
        self.active_entries: Dict[str, TimingEntry] = {}
        self.completed_trees: List[ExecutionTimingTree] = []
        self._entry_stack: List[str] = []  # Stack for nested timings
        
    def start_execution(self, correlation_id: str) -> ExecutionTimingTree:
        """Start a new execution timing tree.
        
        Args:
            correlation_id: Correlation ID for the execution
            
        Returns:
            New execution timing tree
        """
        root_entry = TimingEntry(
            operation=f"{self.agent_name}.execute",
            category=TimingCategory.ORCHESTRATION,
            metadata={"agent_name": self.agent_name}
        )
        
        tree = ExecutionTimingTree(
            root_id=root_entry.entry_id,
            correlation_id=correlation_id,
            agent_name=self.agent_name
        )
        tree.add_entry(root_entry)
        
        self.current_tree = tree
        self.active_entries[root_entry.entry_id] = root_entry
        self._entry_stack = [root_entry.entry_id]
        
        logger.debug(f"Started timing execution for {self.agent_name} (correlation: {correlation_id})")
        return tree
        
    def start_timing(self, operation: str, category: TimingCategory = TimingCategory.UNKNOWN,
                    metadata: Optional[Dict[str, Any]] = None) -> TimingEntry:
        """Start timing an operation.
        
        Args:
            operation: Name of the operation being timed
            category: Category of the operation
            metadata: Additional metadata for the timing
            
        Returns:
            Timing entry for the operation
        """
        parent_id = self._entry_stack[-1] if self._entry_stack else None
        
        entry = TimingEntry(
            operation=operation,
            category=category,
            parent_id=parent_id,
            metadata=metadata or {}
        )
        
        self.active_entries[entry.entry_id] = entry
        self._entry_stack.append(entry.entry_id)
        
        if self.current_tree:
            self.current_tree.add_entry(entry)
            
        logger.debug(f"Started timing: {operation} (category: {category.value})")
        return entry
        
    def end_timing(self, entry: TimingEntry, error: Optional[str] = None) -> None:
        """End timing for an operation.
        
        Args:
            entry: Timing entry to complete
            error: Optional error message if operation failed
        """
        if entry.entry_id not in self.active_entries:
            logger.warning(f"Attempted to end unknown timing entry: {entry.entry_id}")
            return
            
        entry.complete(error)
        del self.active_entries[entry.entry_id]
        
        # Remove from stack
        if entry.entry_id in self._entry_stack:
            idx = self._entry_stack.index(entry.entry_id)
            self._entry_stack = self._entry_stack[:idx]
            
        logger.debug(f"Completed timing: {entry.operation} ({entry.duration_ms:.2f}ms)")
        
    def complete_execution(self) -> Optional[ExecutionTimingTree]:
        """Complete the current execution timing tree.
        
        Returns:
            Completed execution timing tree
        """
        if not self.current_tree:
            return None
            
        # Complete root entry
        root_entry = self.current_tree.entries.get(self.current_tree.root_id)
        if root_entry and not root_entry.is_complete:
            self.end_timing(root_entry)
            
        # Complete any remaining active entries
        for entry_id in list(self.active_entries.keys()):
            entry = self.active_entries[entry_id]
            self.end_timing(entry, error="Execution completed with unclosed timing")
            
        tree = self.current_tree
        self.completed_trees.append(tree)
        self.current_tree = None
        self._entry_stack = []
        
        logger.info(f"Completed execution timing for {self.agent_name} "
                   f"(total: {tree.get_total_duration_ms():.2f}ms)")
        return tree
        
    @contextmanager
    def time_operation(self, operation: str, category: TimingCategory = TimingCategory.UNKNOWN,
                      metadata: Optional[Dict[str, Any]] = None):
        """Context manager for timing an operation.
        
        Args:
            operation: Name of the operation
            category: Category of the operation
            metadata: Additional metadata
            
        Example:
            with collector.time_operation("database_query", TimingCategory.DATABASE):
                result = await db.query()
        """
        entry = self.start_timing(operation, category, metadata)
        error = None
        try:
            yield entry
        except Exception as e:
            error = str(e)
            raise
        finally:
            self.end_timing(entry, error)
            
    def get_aggregated_stats(self) -> Dict[str, AggregateStats]:
        """Get aggregated statistics by category.
        
        Returns:
            Dictionary of category to aggregate stats
        """
        stats_by_category: Dict[str, AggregateStats] = {}
        
        for tree in self.completed_trees:
            for entry in tree.entries.values():
                if not entry.is_complete:
                    continue
                    
                category_name = entry.category.value
                if category_name not in stats_by_category:
                    stats_by_category[category_name] = AggregateStats()
                    
                stats_by_category[category_name].add_entry(entry)
                
        return stats_by_category
        
    def get_slowest_operations(self, limit: int = 10) -> List[TimingEntry]:
        """Get the slowest operations across all executions.
        
        Args:
            limit: Maximum number of operations to return
            
        Returns:
            List of slowest timing entries
        """
        all_entries = []
        for tree in self.completed_trees:
            all_entries.extend([e for e in tree.entries.values() if e.is_complete])
            
        if self.current_tree:
            all_entries.extend([e for e in self.current_tree.entries.values() if e.is_complete])
            
        # Sort by duration descending
        all_entries.sort(key=lambda e: e.duration_ms or 0, reverse=True)
        return all_entries[:limit]
        
    def get_bottlenecks(self, threshold_ms: float = 1000) -> List[TimingEntry]:
        """Identify operations exceeding threshold.
        
        Args:
            threshold_ms: Threshold in milliseconds
            
        Returns:
            List of bottleneck operations
        """
        bottlenecks = []
        
        for tree in self.completed_trees:
            for entry in tree.entries.values():
                if entry.is_complete and entry.duration_ms and entry.duration_ms > threshold_ms:
                    bottlenecks.append(entry)
                    
        return bottlenecks
        
    def clear_history(self) -> None:
        """Clear completed timing trees."""
        self.completed_trees = []
        logger.debug(f"Cleared timing history for {self.agent_name}")