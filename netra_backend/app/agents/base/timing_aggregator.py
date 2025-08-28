"""Timing Aggregator for Performance Analysis and Reporting

Provides rollup reporting and analysis of execution timing data:
- Category-based aggregation
- Agent performance comparison
- Bottleneck identification
- Optimization recommendations
- Historical trend analysis

Business Value: Identifies optimization opportunities for 20-30% performance gain.
BVJ: Platform | Operational Excellence | Data-driven performance optimization
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from netra_backend.app.agents.base.timing_collector import (
    ExecutionTimingTree,
    TimingEntry,
    TimingCategory,
    AggregateStats
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class OptimizationPriority(Enum):
    """Priority levels for optimization recommendations."""
    CRITICAL = "critical"   # >5s operations
    HIGH = "high"          # 2-5s operations  
    MEDIUM = "medium"      # 1-2s operations
    LOW = "low"           # 0.5-1s operations


@dataclass
class Bottleneck:
    """Identified performance bottleneck."""
    
    operation: str
    category: TimingCategory
    avg_duration_ms: float
    occurrence_count: int
    total_impact_ms: float  # Total time spent across all occurrences
    priority: OptimizationPriority
    recommendation: str
    affected_agents: List[str]
    
    @property
    def impact_percentage(self) -> float:
        """Calculate impact as percentage of total execution time."""
        # Will be set by aggregator based on total context
        return getattr(self, '_impact_percentage', 0.0)


@dataclass
class OptimizationReport:
    """Comprehensive optimization analysis report."""
    
    total_executions: int
    total_duration_ms: float
    avg_duration_ms: float
    bottlenecks: List[Bottleneck]
    category_breakdown: Dict[str, AggregateStats]
    agent_breakdown: Dict[str, AggregateStats]
    optimization_potential_ms: float  # Estimated time savings
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TrendData:
    """Historical trend information for an operation."""
    
    operation: str
    period_days: int
    data_points: List[Dict[str, Any]]  # timestamp, duration_ms, count
    avg_duration_trend: float  # Positive = getting slower
    volume_trend: float  # Positive = more frequent
    performance_status: str  # "improving", "degrading", "stable"


class TimingAggregator:
    """Aggregates and analyzes execution timing data."""
    
    # Thresholds for bottleneck identification (in ms)
    BOTTLENECK_THRESHOLDS = {
        OptimizationPriority.CRITICAL: 5000,
        OptimizationPriority.HIGH: 2000,
        OptimizationPriority.MEDIUM: 1000,
        OptimizationPriority.LOW: 500
    }
    
    # Optimization recommendations by category
    OPTIMIZATION_RECOMMENDATIONS = {
        TimingCategory.LLM: {
            "cache": "Implement LLM response caching for repeated queries",
            "batch": "Batch multiple LLM calls when possible",
            "model": "Consider using a faster model for non-critical operations",
            "prompt": "Optimize prompt length and complexity"
        },
        TimingCategory.DATABASE: {
            "index": "Add database indexes for frequently queried fields",
            "cache": "Implement query result caching",
            "batch": "Batch database operations",
            "optimize": "Optimize query structure and joins"
        },
        TimingCategory.PROCESSING: {
            "parallel": "Parallelize independent processing steps",
            "algorithm": "Optimize algorithm complexity",
            "batch": "Process data in larger batches",
            "cache": "Cache intermediate processing results"
        },
        TimingCategory.NETWORK: {
            "cache": "Cache external API responses",
            "batch": "Batch API calls when possible",
            "retry": "Implement exponential backoff for retries",
            "timeout": "Optimize timeout settings"
        }
    }
    
    def __init__(self):
        """Initialize timing aggregator."""
        self.timing_trees: List[ExecutionTimingTree] = []
        
    def add_timing_tree(self, tree: ExecutionTimingTree) -> None:
        """Add execution timing tree for analysis.
        
        Args:
            tree: Execution timing tree to analyze
        """
        self.timing_trees.append(tree)
        logger.debug(f"Added timing tree for {tree.agent_name} to aggregator")
        
    def aggregate_by_category(self) -> Dict[str, AggregateStats]:
        """Aggregate timing data by category.
        
        Returns:
            Dictionary of category name to aggregate statistics
        """
        category_stats: Dict[str, AggregateStats] = {}
        
        for tree in self.timing_trees:
            for entry in tree.entries.values():
                if not entry.is_complete:
                    continue
                    
                category_name = entry.category.value
                if category_name not in category_stats:
                    category_stats[category_name] = AggregateStats()
                    
                category_stats[category_name].add_entry(entry)
                
        logger.info(f"Aggregated timing data for {len(category_stats)} categories")
        return category_stats
        
    def aggregate_by_agent(self) -> Dict[str, AggregateStats]:
        """Aggregate timing data by agent.
        
        Returns:
            Dictionary of agent name to aggregate statistics
        """
        agent_stats: Dict[str, AggregateStats] = {}
        
        for tree in self.timing_trees:
            agent_name = tree.agent_name
            if agent_name not in agent_stats:
                agent_stats[agent_name] = AggregateStats()
                
            # Add root entry (total agent execution)
            root_entry = tree.entries.get(tree.root_id)
            if root_entry and root_entry.is_complete:
                agent_stats[agent_name].add_entry(root_entry)
                
        logger.info(f"Aggregated timing data for {len(agent_stats)} agents")
        return agent_stats
        
    def identify_bottlenecks(self, threshold_ms: float = 500) -> List[Bottleneck]:
        """Identify performance bottlenecks.
        
        Args:
            threshold_ms: Minimum duration to consider as bottleneck
            
        Returns:
            List of identified bottlenecks sorted by impact
        """
        operation_stats: Dict[str, Dict[str, Any]] = {}
        total_duration_ms = 0
        
        # Collect statistics for each operation
        for tree in self.timing_trees:
            for entry in tree.entries.values():
                if not entry.is_complete or not entry.duration_ms:
                    continue
                    
                total_duration_ms += entry.duration_ms
                
                if entry.duration_ms < threshold_ms:
                    continue
                    
                op_key = f"{entry.category.value}:{entry.operation}"
                if op_key not in operation_stats:
                    operation_stats[op_key] = {
                        "operation": entry.operation,
                        "category": entry.category,
                        "durations": [],
                        "agents": set()
                    }
                    
                operation_stats[op_key]["durations"].append(entry.duration_ms)
                operation_stats[op_key]["agents"].add(tree.agent_name)
                
        # Create bottleneck objects
        bottlenecks = []
        for op_key, stats in operation_stats.items():
            durations = stats["durations"]
            avg_duration = sum(durations) / len(durations)
            total_impact = sum(durations)
            
            priority = self._determine_priority(avg_duration)
            recommendation = self._get_recommendation(stats["category"], avg_duration)
            
            bottleneck = Bottleneck(
                operation=stats["operation"],
                category=stats["category"],
                avg_duration_ms=avg_duration,
                occurrence_count=len(durations),
                total_impact_ms=total_impact,
                priority=priority,
                recommendation=recommendation,
                affected_agents=list(stats["agents"])
            )
            
            # Set impact percentage
            if total_duration_ms > 0:
                bottleneck._impact_percentage = (total_impact / total_duration_ms) * 100
                
            bottlenecks.append(bottleneck)
            
        # Sort by total impact
        bottlenecks.sort(key=lambda b: b.total_impact_ms, reverse=True)
        
        logger.info(f"Identified {len(bottlenecks)} performance bottlenecks")
        return bottlenecks
        
    def generate_optimization_report(self) -> OptimizationReport:
        """Generate comprehensive optimization report.
        
        Returns:
            Optimization report with recommendations
        """
        # Calculate totals
        total_executions = len(self.timing_trees)
        total_duration_ms = sum(
            tree.get_total_duration_ms() for tree in self.timing_trees
        )
        avg_duration_ms = total_duration_ms / total_executions if total_executions > 0 else 0
        
        # Get breakdowns
        category_breakdown = self.aggregate_by_category()
        agent_breakdown = self.aggregate_by_agent()
        
        # Identify bottlenecks
        bottlenecks = self.identify_bottlenecks()
        
        # Calculate optimization potential
        optimization_potential_ms = self._calculate_optimization_potential(bottlenecks)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(bottlenecks, category_breakdown)
        
        report = OptimizationReport(
            total_executions=total_executions,
            total_duration_ms=total_duration_ms,
            avg_duration_ms=avg_duration_ms,
            bottlenecks=bottlenecks[:10],  # Top 10 bottlenecks
            category_breakdown=category_breakdown,
            agent_breakdown=agent_breakdown,
            optimization_potential_ms=optimization_potential_ms,
            recommendations=recommendations
        )
        
        logger.info(f"Generated optimization report: {total_executions} executions, "
                   f"{len(bottlenecks)} bottlenecks, {optimization_potential_ms:.0f}ms potential savings")
        
        return report
        
    def get_critical_paths(self) -> List[List[TimingEntry]]:
        """Get critical paths from all timing trees.
        
        Returns:
            List of critical paths (longest execution chains)
        """
        critical_paths = []
        
        for tree in self.timing_trees:
            path = tree.get_critical_path()
            if path:
                critical_paths.append(path)
                
        # Sort by total duration
        critical_paths.sort(
            key=lambda p: sum(e.duration_ms or 0 for e in p),
            reverse=True
        )
        
        return critical_paths
        
    def export_report_json(self, report: OptimizationReport) -> str:
        """Export optimization report as JSON.
        
        Args:
            report: Optimization report to export
            
        Returns:
            JSON string representation of the report
        """
        report_dict = {
            "generated_at": report.generated_at.isoformat(),
            "summary": {
                "total_executions": report.total_executions,
                "total_duration_ms": report.total_duration_ms,
                "avg_duration_ms": report.avg_duration_ms,
                "optimization_potential_ms": report.optimization_potential_ms
            },
            "bottlenecks": [
                {
                    "operation": b.operation,
                    "category": b.category.value,
                    "avg_duration_ms": b.avg_duration_ms,
                    "occurrence_count": b.occurrence_count,
                    "total_impact_ms": b.total_impact_ms,
                    "impact_percentage": b.impact_percentage,
                    "priority": b.priority.value,
                    "recommendation": b.recommendation,
                    "affected_agents": b.affected_agents
                }
                for b in report.bottlenecks
            ],
            "category_breakdown": {
                cat: {
                    "total_time_ms": stats.total_time_ms,
                    "count": stats.count,
                    "avg_time_ms": stats.avg_time_ms,
                    "min_time_ms": stats.min_time_ms,
                    "max_time_ms": stats.max_time_ms
                }
                for cat, stats in report.category_breakdown.items()
            },
            "agent_breakdown": {
                agent: {
                    "total_time_ms": stats.total_time_ms,
                    "count": stats.count,
                    "avg_time_ms": stats.avg_time_ms
                }
                for agent, stats in report.agent_breakdown.items()
            },
            "recommendations": report.recommendations
        }
        
        return json.dumps(report_dict, indent=2)
        
    def _determine_priority(self, duration_ms: float) -> OptimizationPriority:
        """Determine optimization priority based on duration.
        
        Args:
            duration_ms: Operation duration in milliseconds
            
        Returns:
            Optimization priority level
        """
        for priority, threshold in self.BOTTLENECK_THRESHOLDS.items():
            if duration_ms >= threshold:
                return priority
        return OptimizationPriority.LOW
        
    def _get_recommendation(self, category: TimingCategory, 
                           duration_ms: float) -> str:
        """Get optimization recommendation for category.
        
        Args:
            category: Timing category
            duration_ms: Operation duration
            
        Returns:
            Optimization recommendation string
        """
        recommendations = self.OPTIMIZATION_RECOMMENDATIONS.get(category, {})
        
        # Select recommendation based on duration
        if duration_ms > 5000 and "cache" in recommendations:
            return recommendations["cache"]
        elif duration_ms > 2000 and "batch" in recommendations:
            return recommendations["batch"]
        elif "optimize" in recommendations:
            return recommendations["optimize"]
        else:
            return next(iter(recommendations.values()), "Analyze operation for optimization opportunities")
            
    def _calculate_optimization_potential(self, bottlenecks: List[Bottleneck]) -> float:
        """Calculate potential time savings from optimizations.
        
        Args:
            bottlenecks: List of identified bottlenecks
            
        Returns:
            Estimated time savings in milliseconds
        """
        potential_ms = 0.0
        
        for bottleneck in bottlenecks:
            # Estimate 30-50% improvement for critical bottlenecks
            if bottleneck.priority == OptimizationPriority.CRITICAL:
                potential_ms += bottleneck.total_impact_ms * 0.5
            elif bottleneck.priority == OptimizationPriority.HIGH:
                potential_ms += bottleneck.total_impact_ms * 0.4
            elif bottleneck.priority == OptimizationPriority.MEDIUM:
                potential_ms += bottleneck.total_impact_ms * 0.3
            else:
                potential_ms += bottleneck.total_impact_ms * 0.2
                
        return potential_ms
        
    def _generate_recommendations(self, bottlenecks: List[Bottleneck],
                                 category_breakdown: Dict[str, AggregateStats]) -> List[str]:
        """Generate prioritized optimization recommendations.
        
        Args:
            bottlenecks: List of identified bottlenecks
            category_breakdown: Category statistics
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Top bottleneck recommendations
        for bottleneck in bottlenecks[:3]:
            recommendations.append(
                f"Optimize {bottleneck.operation}: {bottleneck.recommendation} "
                f"(potential savings: {bottleneck.total_impact_ms * 0.3:.0f}ms)"
            )
            
        # Category-based recommendations
        for category, stats in category_breakdown.items():
            if stats.total_time_ms > 10000:  # More than 10 seconds total
                cat_enum = TimingCategory(category)
                if cat_enum in self.OPTIMIZATION_RECOMMENDATIONS:
                    rec = self.OPTIMIZATION_RECOMMENDATIONS[cat_enum].get("cache", "")
                    if rec:
                        recommendations.append(f"For {category} operations: {rec}")
                        
        # General recommendations
        if len(self.timing_trees) > 100:
            recommendations.append("Consider implementing request batching to reduce overhead")
            
        return recommendations[:10]  # Top 10 recommendations