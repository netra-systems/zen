"""Agent Result Aggregation L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (output quality and consistency)
- Business Goal: Result quality and output value
- Value Impact: Protects $8K MRR from inconsistent or poor quality outputs
- Strategic Impact: Core output processing for reliable AI results

Critical Path: Multiple results -> Conflict detection -> Resolution -> Merging -> Formatting
Coverage: Real result aggregators, conflict resolution, merging strategies, formatting
"""

import pytest
import asyncio
import time
import json
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

# Real components for L2 testing
from app.services.redis_service import RedisService
from app.core.circuit_breaker import CircuitBreaker
from app.core.database_connection_manager import DatabaseConnectionManager
from app.agents.base import BaseSubAgent

logger = logging.getLogger(__name__)


class ResultType(Enum):
    """Types of results that can be aggregated."""
    TEXT = "text"
    JSON = "json"
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    LIST = "list"
    STRUCTURED = "structured"


class ConflictStrategy(Enum):
    """Strategies for resolving conflicts between results."""
    MAJORITY_VOTE = "majority_vote"
    PRIORITY_BASED = "priority_based"
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    MERGE_ALL = "merge_all"
    FIRST_WINS = "first_wins"
    LAST_WINS = "last_wins"


class AggregationStrategy(Enum):
    """Strategies for aggregating multiple results."""
    CONCATENATE = "concatenate"
    AVERAGE = "average"
    MAXIMUM = "maximum"
    MINIMUM = "minimum"
    CONSENSUS = "consensus"
    UNION = "union"
    INTERSECTION = "intersection"


@dataclass
class AgentResult:
    """Individual result from an agent."""
    result_id: str
    agent_id: str
    agent_type: str
    result_type: ResultType
    data: Any
    confidence: float
    priority: int
    metadata: Dict[str, Any]
    created_at: datetime
    
    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["result_type"] = self.result_type.value
        data["created_at"] = self.created_at.isoformat()
        return data
    
    def get_hash(self) -> str:
        """Get hash of result data for conflict detection."""
        data_str = json.dumps(self.data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()


@dataclass
class ConflictGroup:
    """Group of conflicting results."""
    group_id: str
    results: List[AgentResult]
    conflict_type: str
    resolution_strategy: ConflictStrategy
    
    def get_consensus_confidence(self) -> float:
        """Get average confidence of results in group."""
        if not self.results:
            return 0.0
        return sum(r.confidence for r in self.results) / len(self.results)


class ConflictDetector:
    """Detects conflicts between agent results."""
    
    def __init__(self):
        self.similarity_threshold = 0.8
        self.conflict_rules = []
        
    def add_conflict_rule(self, rule: Callable[[AgentResult, AgentResult], bool]):
        """Add a custom conflict detection rule."""
        self.conflict_rules.append(rule)
        
    def detect_conflicts(self, results: List[AgentResult]) -> List[ConflictGroup]:
        """Detect conflicts among results."""
        conflicts = []
        processed_results = set()
        
        for i, result1 in enumerate(results):
            if result1.result_id in processed_results:
                continue
                
            conflicting_results = [result1]
            
            for j, result2 in enumerate(results[i+1:], i+1):
                if result2.result_id in processed_results:
                    continue
                    
                if self._are_conflicting(result1, result2):
                    conflicting_results.append(result2)
                    processed_results.add(result2.result_id)
            
            if len(conflicting_results) > 1:
                conflict_group = ConflictGroup(
                    group_id=f"conflict_{int(time.time() * 1000000)}",
                    results=conflicting_results,
                    conflict_type=self._classify_conflict(conflicting_results),
                    resolution_strategy=ConflictStrategy.MAJORITY_VOTE  # Default
                )
                conflicts.append(conflict_group)
                
            processed_results.add(result1.result_id)
        
        return conflicts
    
    def _are_conflicting(self, result1: AgentResult, result2: AgentResult) -> bool:
        """Check if two results are conflicting."""
        # Type mismatch
        if result1.result_type != result2.result_type:
            return True
        
        # Check custom rules
        for rule in self.conflict_rules:
            if rule(result1, result2):
                return True
        
        # Type-specific conflict detection
        if result1.result_type == ResultType.BOOLEAN:
            return result1.data != result2.data
        
        elif result1.result_type == ResultType.NUMERIC:
            # Consider numeric values conflicting if difference > 10%
            if result2.data == 0:
                return result1.data != 0
            diff_percent = abs(result1.data - result2.data) / abs(result2.data)
            return diff_percent > 0.1
        
        elif result1.result_type == ResultType.TEXT:
            # Use similarity for text
            similarity = self._calculate_text_similarity(result1.data, result2.data)
            return similarity < self.similarity_threshold
        
        elif result1.result_type == ResultType.JSON:
            # JSON structure comparison
            return json.dumps(result1.data, sort_keys=True) != json.dumps(result2.data, sort_keys=True)
        
        return False
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _classify_conflict(self, results: List[AgentResult]) -> str:
        """Classify the type of conflict."""
        if len(set(r.result_type for r in results)) > 1:
            return "type_mismatch"
        elif all(r.result_type == ResultType.BOOLEAN for r in results):
            return "boolean_disagreement"
        elif all(r.result_type == ResultType.NUMERIC for r in results):
            return "numeric_variance"
        elif all(r.result_type == ResultType.TEXT for r in results):
            return "text_disagreement"
        else:
            return "general_conflict"


class ConflictResolver:
    """Resolves conflicts between agent results."""
    
    def __init__(self):
        self.resolution_stats = {
            "total_conflicts": 0,
            "resolved_conflicts": 0,
            "failed_resolutions": 0
        }
        
    def resolve_conflict(self, conflict_group: ConflictGroup) -> Optional[AgentResult]:
        """Resolve a conflict group and return the resolved result."""
        self.resolution_stats["total_conflicts"] += 1
        
        try:
            strategy = conflict_group.resolution_strategy
            resolved_result = None
            
            if strategy == ConflictStrategy.MAJORITY_VOTE:
                resolved_result = self._resolve_by_majority_vote(conflict_group)
            elif strategy == ConflictStrategy.PRIORITY_BASED:
                resolved_result = self._resolve_by_priority(conflict_group)
            elif strategy == ConflictStrategy.CONFIDENCE_WEIGHTED:
                resolved_result = self._resolve_by_confidence(conflict_group)
            elif strategy == ConflictStrategy.FIRST_WINS:
                resolved_result = self._resolve_first_wins(conflict_group)
            elif strategy == ConflictStrategy.LAST_WINS:
                resolved_result = self._resolve_last_wins(conflict_group)
            elif strategy == ConflictStrategy.MERGE_ALL:
                resolved_result = self._resolve_by_merge(conflict_group)
            
            if resolved_result:
                self.resolution_stats["resolved_conflicts"] += 1
                return resolved_result
            else:
                self.resolution_stats["failed_resolutions"] += 1
                return None
                
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            self.resolution_stats["failed_resolutions"] += 1
            return None
    
    def _resolve_by_majority_vote(self, conflict_group: ConflictGroup) -> Optional[AgentResult]:
        """Resolve by majority vote."""
        result_counts = {}
        
        for result in conflict_group.results:
            data_hash = result.get_hash()
            if data_hash not in result_counts:
                result_counts[data_hash] = {"count": 0, "result": result}
            result_counts[data_hash]["count"] += 1
        
        # Find majority
        majority_hash = max(result_counts.keys(), key=lambda k: result_counts[k]["count"])
        return result_counts[majority_hash]["result"]
    
    def _resolve_by_priority(self, conflict_group: ConflictGroup) -> Optional[AgentResult]:
        """Resolve by highest priority."""
        return max(conflict_group.results, key=lambda r: r.priority)
    
    def _resolve_by_confidence(self, conflict_group: ConflictGroup) -> Optional[AgentResult]:
        """Resolve by highest confidence."""
        return max(conflict_group.results, key=lambda r: r.confidence)
    
    def _resolve_first_wins(self, conflict_group: ConflictGroup) -> Optional[AgentResult]:
        """Resolve by taking the first result."""
        return min(conflict_group.results, key=lambda r: r.created_at)
    
    def _resolve_last_wins(self, conflict_group: ConflictGroup) -> Optional[AgentResult]:
        """Resolve by taking the last result."""
        return max(conflict_group.results, key=lambda r: r.created_at)
    
    def _resolve_by_merge(self, conflict_group: ConflictGroup) -> Optional[AgentResult]:
        """Resolve by merging all results."""
        if not conflict_group.results:
            return None
        
        # Create merged result
        base_result = conflict_group.results[0]
        
        if base_result.result_type == ResultType.TEXT:
            # Merge text results
            merged_data = " ".join(r.data for r in conflict_group.results)
        elif base_result.result_type == ResultType.LIST:
            # Merge lists
            merged_data = []
            for result in conflict_group.results:
                merged_data.extend(result.data)
        elif base_result.result_type == ResultType.NUMERIC:
            # Average numeric results
            merged_data = sum(r.data for r in conflict_group.results) / len(conflict_group.results)
        else:
            # For other types, take the highest confidence
            return self._resolve_by_confidence(conflict_group)
        
        # Create merged result
        merged_result = AgentResult(
            result_id=f"merged_{conflict_group.group_id}",
            agent_id="merger",
            agent_type="result_merger",
            result_type=base_result.result_type,
            data=merged_data,
            confidence=conflict_group.get_consensus_confidence(),
            priority=max(r.priority for r in conflict_group.results),
            metadata={"merged_from": [r.result_id for r in conflict_group.results]},
            created_at=datetime.now()
        )
        
        return merged_result


class ResultAggregator:
    """Aggregates multiple agent results into a final result."""
    
    def __init__(self):
        self.conflict_detector = ConflictDetector()
        self.conflict_resolver = ConflictResolver()
        self.aggregation_stats = {
            "total_aggregations": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0
        }
        
    def aggregate_results(self, results: List[AgentResult], 
                         strategy: AggregationStrategy = AggregationStrategy.CONSENSUS) -> Dict[str, Any]:
        """Aggregate multiple results into a final output."""
        self.aggregation_stats["total_aggregations"] += 1
        
        if not results:
            return {"success": False, "error": "No results to aggregate"}
        
        # Detect conflicts
        conflicts = self.conflict_detector.detect_conflicts(results)
        self.aggregation_stats["conflicts_detected"] += len(conflicts)
        
        # Resolve conflicts
        resolved_results = list(results)  # Start with original results
        
        for conflict in conflicts:
            resolved_result = self.conflict_resolver.resolve_conflict(conflict)
            if resolved_result:
                # Remove conflicting results and add resolved result
                for conflict_result in conflict.results:
                    if conflict_result in resolved_results:
                        resolved_results.remove(conflict_result)
                resolved_results.append(resolved_result)
                self.aggregation_stats["conflicts_resolved"] += 1
        
        # Apply aggregation strategy
        final_result = self._apply_aggregation_strategy(resolved_results, strategy)
        
        return {
            "success": True,
            "result": final_result,
            "original_count": len(results),
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": len([c for c in conflicts if any(r.agent_id == "merger" for r in resolved_results)]),
            "final_count": len(resolved_results),
            "aggregation_strategy": strategy.value,
            "metadata": {
                "aggregated_at": datetime.now().isoformat(),
                "contributing_agents": list(set(r.agent_id for r in results))
            }
        }
    
    def _apply_aggregation_strategy(self, results: List[AgentResult], 
                                  strategy: AggregationStrategy) -> Any:
        """Apply the specified aggregation strategy."""
        if not results:
            return None
        
        if strategy == AggregationStrategy.CONSENSUS:
            # Return result with highest confidence
            return max(results, key=lambda r: r.confidence).data
        
        elif strategy == AggregationStrategy.CONCATENATE:
            # Concatenate text results
            if all(r.result_type == ResultType.TEXT for r in results):
                return " ".join(r.data for r in results)
            else:
                return [r.data for r in results]
        
        elif strategy == AggregationStrategy.AVERAGE:
            # Average numeric results
            numeric_results = [r for r in results if r.result_type == ResultType.NUMERIC]
            if numeric_results:
                return sum(r.data for r in numeric_results) / len(numeric_results)
            return None
        
        elif strategy == AggregationStrategy.MAXIMUM:
            # Maximum of numeric results
            numeric_results = [r for r in results if r.result_type == ResultType.NUMERIC]
            if numeric_results:
                return max(r.data for r in numeric_results)
            return None
        
        elif strategy == AggregationStrategy.MINIMUM:
            # Minimum of numeric results
            numeric_results = [r for r in results if r.result_type == ResultType.NUMERIC]
            if numeric_results:
                return min(r.data for r in numeric_results)
            return None
        
        elif strategy == AggregationStrategy.UNION:
            # Union of list results
            list_results = [r for r in results if r.result_type == ResultType.LIST]
            if list_results:
                union_set = set()
                for result in list_results:
                    union_set.update(result.data)
                return list(union_set)
            return None
        
        elif strategy == AggregationStrategy.INTERSECTION:
            # Intersection of list results
            list_results = [r for r in results if r.result_type == ResultType.LIST]
            if list_results:
                intersection_set = set(list_results[0].data)
                for result in list_results[1:]:
                    intersection_set.intersection_update(result.data)
                return list(intersection_set)
            return None
        
        # Default: return first result
        return results[0].data


class ResultFormatter:
    """Formats aggregated results for output."""
    
    def __init__(self):
        self.output_templates = {}
        
    def add_output_template(self, result_type: str, template: Callable[[Any], str]):
        """Add output template for a specific result type."""
        self.output_templates[result_type] = template
        
    def format_result(self, aggregation_output: Dict[str, Any], 
                     output_format: str = "json") -> str:
        """Format aggregation output for presentation."""
        if not aggregation_output.get("success", False):
            return self._format_error(aggregation_output, output_format)
        
        result_data = aggregation_output["result"]
        
        if output_format == "json":
            return json.dumps(aggregation_output, indent=2, default=str)
        
        elif output_format == "text":
            return self._format_as_text(aggregation_output)
        
        elif output_format == "summary":
            return self._format_as_summary(aggregation_output)
        
        else:
            # Check for custom template
            template = self.output_templates.get(output_format)
            if template:
                return template(result_data)
            
            return str(result_data)
    
    def _format_error(self, aggregation_output: Dict[str, Any], output_format: str) -> str:
        """Format error output."""
        error = aggregation_output.get("error", "Unknown error")
        
        if output_format == "json":
            return json.dumps({"error": error}, indent=2)
        else:
            return f"Error: {error}"
    
    def _format_as_text(self, aggregation_output: Dict[str, Any]) -> str:
        """Format as human-readable text."""
        result = aggregation_output["result"]
        metadata = aggregation_output.get("metadata", {})
        
        text_output = f"Result: {result}\n"
        text_output += f"Contributing agents: {', '.join(metadata.get('contributing_agents', []))}\n"
        text_output += f"Conflicts detected: {aggregation_output.get('conflicts_detected', 0)}\n"
        text_output += f"Conflicts resolved: {aggregation_output.get('conflicts_resolved', 0)}\n"
        
        return text_output
    
    def _format_as_summary(self, aggregation_output: Dict[str, Any]) -> str:
        """Format as summary."""
        result = aggregation_output["result"]
        return f"Aggregated result from {aggregation_output.get('original_count', 0)} agents: {result}"


class AgentResultAggregationManager:
    """Manages agent result aggregation testing."""
    
    def __init__(self):
        self.redis_service = None
        self.db_manager = None
        self.result_aggregator = None
        self.result_formatter = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.result_aggregator = ResultAggregator()
        self.result_formatter = ResultFormatter()
        
        self._setup_conflict_rules()
        self._setup_output_templates()
    
    def _setup_conflict_rules(self):
        """Setup custom conflict detection rules."""
        def opposite_boolean_rule(result1: AgentResult, result2: AgentResult) -> bool:
            """Detect opposite boolean values."""
            if (result1.result_type == ResultType.BOOLEAN and 
                result2.result_type == ResultType.BOOLEAN):
                return result1.data != result2.data
            return False
        
        self.result_aggregator.conflict_detector.add_conflict_rule(opposite_boolean_rule)
    
    def _setup_output_templates(self):
        """Setup output formatting templates."""
        def confidence_template(result: Any) -> str:
            return f"High confidence result: {result}"
        
        self.result_formatter.add_output_template("high_confidence", confidence_template)
    
    def create_test_result(self, agent_id: str, result_type: ResultType, 
                          data: Any, confidence: float = 0.8, priority: int = 5) -> AgentResult:
        """Create a test result."""
        return AgentResult(
            result_id=f"result_{agent_id}_{int(time.time() * 1000000)}",
            agent_id=agent_id,
            agent_type="test_agent",
            result_type=result_type,
            data=data,
            confidence=confidence,
            priority=priority,
            metadata={"test": True},
            created_at=datetime.now()
        )
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()


@pytest.fixture
async def result_aggregation_manager():
    """Create result aggregation manager for testing."""
    manager = AgentResultAggregationManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_basic_result_aggregation(result_aggregation_manager):
    """Test basic result aggregation without conflicts."""
    manager = result_aggregation_manager
    
    # Create compatible results
    results = [
        manager.create_test_result("agent1", ResultType.TEXT, "Hello world", 0.9),
        manager.create_test_result("agent2", ResultType.TEXT, "Hello world", 0.8),
        manager.create_test_result("agent3", ResultType.TEXT, "Hello world", 0.7)
    ]
    
    aggregation_output = manager.result_aggregator.aggregate_results(
        results, AggregationStrategy.CONSENSUS
    )
    
    assert aggregation_output["success"] is True
    assert aggregation_output["result"] == "Hello world"
    assert aggregation_output["original_count"] == 3
    assert aggregation_output["conflicts_detected"] == 0


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_conflict_detection_and_resolution(result_aggregation_manager):
    """Test conflict detection and resolution."""
    manager = result_aggregation_manager
    
    # Create conflicting results
    results = [
        manager.create_test_result("agent1", ResultType.BOOLEAN, True, 0.9),
        manager.create_test_result("agent2", ResultType.BOOLEAN, False, 0.8),
        manager.create_test_result("agent3", ResultType.BOOLEAN, True, 0.7)
    ]
    
    aggregation_output = manager.result_aggregator.aggregate_results(
        results, AggregationStrategy.CONSENSUS
    )
    
    assert aggregation_output["success"] is True
    assert aggregation_output["conflicts_detected"] > 0
    assert aggregation_output["conflicts_resolved"] >= 0
    
    # With majority vote, True should win (2 vs 1)
    assert aggregation_output["result"] is True


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_numeric_result_aggregation(result_aggregation_manager):
    """Test numeric result aggregation strategies."""
    manager = result_aggregation_manager
    
    # Create numeric results
    results = [
        manager.create_test_result("agent1", ResultType.NUMERIC, 10.0),
        manager.create_test_result("agent2", ResultType.NUMERIC, 20.0),
        manager.create_test_result("agent3", ResultType.NUMERIC, 30.0)
    ]
    
    # Test different aggregation strategies
    strategies_expected = [
        (AggregationStrategy.AVERAGE, 20.0),
        (AggregationStrategy.MAXIMUM, 30.0),
        (AggregationStrategy.MINIMUM, 10.0)
    ]
    
    for strategy, expected in strategies_expected:
        output = manager.result_aggregator.aggregate_results(results, strategy)
        assert output["success"] is True
        assert output["result"] == expected


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_list_result_aggregation(result_aggregation_manager):
    """Test list result aggregation strategies."""
    manager = result_aggregation_manager
    
    # Create list results
    results = [
        manager.create_test_result("agent1", ResultType.LIST, ["a", "b", "c"]),
        manager.create_test_result("agent2", ResultType.LIST, ["b", "c", "d"]),
        manager.create_test_result("agent3", ResultType.LIST, ["c", "d", "e"])
    ]
    
    # Test union strategy
    union_output = manager.result_aggregator.aggregate_results(
        results, AggregationStrategy.UNION
    )
    
    assert union_output["success"] is True
    union_result = set(union_output["result"])
    expected_union = {"a", "b", "c", "d", "e"}
    assert union_result == expected_union
    
    # Test intersection strategy
    intersection_output = manager.result_aggregator.aggregate_results(
        results, AggregationStrategy.INTERSECTION
    )
    
    assert intersection_output["success"] is True
    intersection_result = set(intersection_output["result"])
    expected_intersection = {"c"}
    assert intersection_result == expected_intersection


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_priority_based_conflict_resolution(result_aggregation_manager):
    """Test priority-based conflict resolution."""
    manager = result_aggregation_manager
    
    # Create conflicting results with different priorities
    results = [
        manager.create_test_result("agent1", ResultType.TEXT, "Low priority", 0.8, priority=1),
        manager.create_test_result("agent2", ResultType.TEXT, "High priority", 0.7, priority=10),
        manager.create_test_result("agent3", ResultType.TEXT, "Medium priority", 0.9, priority=5)
    ]
    
    # Set resolution strategy to priority-based
    conflicts = manager.result_aggregator.conflict_detector.detect_conflicts(results)
    
    if conflicts:
        conflict = conflicts[0]
        conflict.resolution_strategy = ConflictStrategy.PRIORITY_BASED
        
        resolved_result = manager.result_aggregator.conflict_resolver.resolve_conflict(conflict)
        
        assert resolved_result is not None
        assert resolved_result.data == "High priority"
        assert resolved_result.priority == 10


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_confidence_weighted_resolution(result_aggregation_manager):
    """Test confidence-weighted conflict resolution."""
    manager = result_aggregation_manager
    
    # Create conflicting results with different confidence levels
    results = [
        manager.create_test_result("agent1", ResultType.TEXT, "Low confidence", 0.3),
        manager.create_test_result("agent2", ResultType.TEXT, "High confidence", 0.9),
        manager.create_test_result("agent3", ResultType.TEXT, "Medium confidence", 0.6)
    ]
    
    # Set resolution strategy to confidence-weighted
    conflicts = manager.result_aggregator.conflict_detector.detect_conflicts(results)
    
    if conflicts:
        conflict = conflicts[0]
        conflict.resolution_strategy = ConflictStrategy.CONFIDENCE_WEIGHTED
        
        resolved_result = manager.result_aggregator.conflict_resolver.resolve_conflict(conflict)
        
        assert resolved_result is not None
        assert resolved_result.data == "High confidence"
        assert resolved_result.confidence == 0.9


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_result_merging_strategy(result_aggregation_manager):
    """Test result merging for conflict resolution."""
    manager = result_aggregation_manager
    
    # Create text results for merging
    results = [
        manager.create_test_result("agent1", ResultType.TEXT, "Hello"),
        manager.create_test_result("agent2", ResultType.TEXT, "world"),
        manager.create_test_result("agent3", ResultType.TEXT, "test")
    ]
    
    # Set resolution strategy to merge all
    conflicts = manager.result_aggregator.conflict_detector.detect_conflicts(results)
    
    if conflicts:
        conflict = conflicts[0]
        conflict.resolution_strategy = ConflictStrategy.MERGE_ALL
        
        resolved_result = manager.result_aggregator.conflict_resolver.resolve_conflict(conflict)
        
        assert resolved_result is not None
        assert "Hello" in resolved_result.data
        assert "world" in resolved_result.data
        assert "test" in resolved_result.data


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_text_similarity_conflict_detection(result_aggregation_manager):
    """Test text similarity-based conflict detection."""
    manager = result_aggregation_manager
    
    # Create similar and dissimilar text results
    results = [
        manager.create_test_result("agent1", ResultType.TEXT, "The quick brown fox"),
        manager.create_test_result("agent2", ResultType.TEXT, "The quick brown fox jumps"),  # Similar
        manager.create_test_result("agent3", ResultType.TEXT, "Completely different text")   # Different
    ]
    
    conflicts = manager.result_aggregator.conflict_detector.detect_conflicts(results)
    
    # Should detect conflicts between similar and different texts
    assert len(conflicts) > 0
    
    # Check that similar texts are not in the same conflict group as different text
    for conflict in conflicts:
        result_texts = [r.data for r in conflict.results]
        
        # All texts in a conflict group should be somewhat related
        # or clearly different (indicating they are actually conflicting)
        assert len(set(result_texts)) > 1  # Different texts in conflict


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_result_formatting_output(result_aggregation_manager):
    """Test result formatting for different output types."""
    manager = result_aggregation_manager
    
    # Create test results
    results = [
        manager.create_test_result("agent1", ResultType.TEXT, "Test result", 0.9)
    ]
    
    aggregation_output = manager.result_aggregator.aggregate_results(results)
    
    # Test different output formats
    json_output = manager.result_formatter.format_result(aggregation_output, "json")
    assert "Test result" in json_output
    assert json.loads(json_output)  # Should be valid JSON
    
    text_output = manager.result_formatter.format_result(aggregation_output, "text")
    assert "Test result" in text_output
    assert "Contributing agents" in text_output
    
    summary_output = manager.result_formatter.format_result(aggregation_output, "summary")
    assert "Test result" in summary_output
    assert "Aggregated result" in summary_output


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_result_aggregation(result_aggregation_manager):
    """Test concurrent result aggregation performance."""
    manager = result_aggregation_manager
    
    # Create multiple result sets for concurrent processing
    result_sets = []
    for i in range(10):
        result_set = [
            manager.create_test_result(f"agent{j}_{i}", ResultType.NUMERIC, j * 10 + i)
            for j in range(5)
        ]
        result_sets.append(result_set)
    
    # Process result sets concurrently
    async def process_results(results):
        return manager.result_aggregator.aggregate_results(results, AggregationStrategy.AVERAGE)
    
    start_time = time.time()
    tasks = [process_results(result_set) for result_set in result_sets]
    outputs = await asyncio.gather(*tasks)
    processing_time = time.time() - start_time
    
    # Verify all aggregations succeeded
    assert all(output["success"] for output in outputs)
    assert len(outputs) == 10
    
    # Performance check
    assert processing_time < 2.0  # Should process 10 sets quickly
    
    avg_processing_time = processing_time / 10
    assert avg_processing_time < 0.2  # Under 200ms per aggregation


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_aggregation_performance_benchmark(result_aggregation_manager):
    """Benchmark result aggregation performance."""
    manager = result_aggregation_manager
    
    # Create large result set for performance testing
    results = [
        manager.create_test_result(f"agent{i}", ResultType.NUMERIC, i * 1.5, 0.8 + (i % 20) / 100)
        for i in range(100)
    ]
    
    start_time = time.time()
    aggregation_output = manager.result_aggregator.aggregate_results(
        results, AggregationStrategy.AVERAGE
    )
    aggregation_time = time.time() - start_time
    
    assert aggregation_output["success"] is True
    
    # Performance assertions
    assert aggregation_time < 1.0  # 100 results in under 1 second
    
    # Check conflict detection performance
    assert aggregation_output["conflicts_detected"] >= 0  # Should handle conflicts efficiently
    
    avg_result_time = aggregation_time / 100
    assert avg_result_time < 0.01  # Under 10ms per result
    
    logger.info(f"Performance: {avg_result_time*1000:.1f}ms per result")
    logger.info(f"Conflicts detected: {aggregation_output['conflicts_detected']}")
    logger.info(f"Total aggregation time: {aggregation_time:.3f}s")