"""
Performance Metrics Collector and Optimizer for Test Execution

Advanced performance analysis and optimization recommendations for achieving
100x productivity gains through intelligent test execution strategies.

Business Value Justification (BVJ):
- Segment: All customer segments (development efficiency)
- Business Goal: Continuous optimization of development velocity
- Value Impact: Enables data-driven test optimization for sustained high performance
- Revenue Impact: Maintains competitive advantage through fastest deployment cycles
"""

import os
import sys
import time
import json
import psutil
import statistics
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
import threading
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for test execution"""
    timestamp: float
    total_duration: float
    test_count: int
    success_rate: float
    cache_hit_rate: float
    avg_test_duration: float
    max_test_duration: float
    min_test_duration: float
    cpu_utilization: float
    memory_utilization: float
    disk_io_rate: float
    network_io_rate: float
    parallel_efficiency: float
    worker_utilization: float
    productivity_gain: float
    
    # Resource allocation metrics
    optimal_workers: int = 0
    memory_per_worker: int = 0
    shard_distribution_score: float = 0.0
    
    # Quality metrics
    failure_cascade_prevented: int = 0
    tests_skipped_by_cache: int = 0
    tests_skipped_by_failfast: int = 0


@dataclass
class TestTypeMetrics:
    """Metrics specific to test types"""
    test_type: str
    execution_count: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    success_rate: float = 100.0
    resource_efficiency: float = 0.0
    optimal_parallelization: int = 1
    cache_effectiveness: float = 0.0


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation with impact assessment"""
    category: str
    recommendation: str
    impact_level: str  # 'low', 'medium', 'high', 'critical'
    estimated_improvement: float
    implementation_effort: str  # 'trivial', 'easy', 'moderate', 'complex'
    business_value: str


class PerformanceAnalyzer:
    """Analyzes test execution performance and identifies bottlenecks"""
    
    def __init__(self):
        self.baseline_metrics = {}
        self.trend_analysis = defaultdict(deque)
        self.bottleneck_patterns = {}
        self.optimization_history = []
    
    def analyze_execution_performance(self, results: List[Any], total_duration: float) -> PerformanceMetrics:
        """Analyze performance of test execution"""
        if not results:
            return self._create_empty_metrics()
        
        # Basic metrics
        test_count = len(results)
        successful_tests = sum(1 for r in results if r.success)
        cached_tests = sum(1 for r in results if r.cached)
        
        durations = [r.duration for r in results if hasattr(r, 'duration')]
        
        # Calculate performance metrics
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            total_duration=total_duration,
            test_count=test_count,
            success_rate=(successful_tests / test_count) * 100 if test_count > 0 else 0,
            cache_hit_rate=(cached_tests / test_count) * 100 if test_count > 0 else 0,
            avg_test_duration=statistics.mean(durations) if durations else 0,
            max_test_duration=max(durations) if durations else 0,
            min_test_duration=min(durations) if durations else 0,
            cpu_utilization=self._calculate_cpu_utilization(),
            memory_utilization=self._calculate_memory_utilization(),
            disk_io_rate=self._calculate_disk_io_rate(),
            network_io_rate=0.0,  # Not applicable for local tests
            parallel_efficiency=self._calculate_parallel_efficiency(results, total_duration),
            worker_utilization=self._calculate_worker_utilization(results),
            productivity_gain=self._calculate_productivity_gain(total_duration, test_count)
        )
        
        # Store for trend analysis
        self._update_trend_analysis(metrics)
        
        return metrics
    
    def _calculate_cpu_utilization(self) -> float:
        """Calculate average CPU utilization during execution"""
        try:
            return psutil.cpu_percent(interval=1)
        except:
            return 0.0
    
    def _calculate_memory_utilization(self) -> float:
        """Calculate memory utilization percentage"""
        try:
            return psutil.virtual_memory().percent
        except:
            return 0.0
    
    def _calculate_disk_io_rate(self) -> float:
        """Calculate disk IO rate in MB/s"""
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                # This is a simplified calculation
                return (disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024)
            return 0.0
        except:
            return 0.0
    
    def _calculate_parallel_efficiency(self, results: List[Any], total_duration: float) -> float:
        """Calculate how efficiently parallel execution was utilized"""
        if not results or total_duration <= 0:
            return 0.0
        
        # Calculate theoretical sequential time
        sequential_time = sum(r.duration for r in results if hasattr(r, 'duration'))
        
        if sequential_time <= 0:
            return 0.0
        
        # Efficiency = Sequential Time / (Parallel Time * Workers Used)
        workers_used = len(set(getattr(r, 'worker_id', 0) for r in results))
        workers_used = max(workers_used, 1)
        
        efficiency = sequential_time / (total_duration * workers_used)
        return min(efficiency * 100, 100.0)  # Cap at 100%
    
    def _calculate_worker_utilization(self, results: List[Any]) -> float:
        """Calculate worker utilization efficiency"""
        if not results:
            return 0.0
        
        worker_loads = defaultdict(float)
        for result in results:
            worker_id = getattr(result, 'worker_id', 0)
            duration = getattr(result, 'duration', 0)
            worker_loads[worker_id] += duration
        
        if not worker_loads:
            return 0.0
        
        # Calculate load balance (lower variance = better utilization)
        load_values = list(worker_loads.values())
        avg_load = statistics.mean(load_values)
        
        if avg_load == 0:
            return 0.0
        
        # Calculate coefficient of variation (std dev / mean)
        if len(load_values) > 1:
            load_variance = statistics.stdev(load_values) / avg_load
            utilization = max(0, 100 - (load_variance * 100))
        else:
            utilization = 100.0
        
        return min(utilization, 100.0)
    
    def _calculate_productivity_gain(self, actual_duration: float, test_count: int) -> float:
        """Calculate productivity gain vs baseline"""
        # Estimate baseline: average 2 seconds per test sequentially
        estimated_baseline = test_count * 2.0
        
        if actual_duration <= 0:
            return 1.0
        
        gain = estimated_baseline / actual_duration
        return min(gain, 100.0)  # Cap at 100x
    
    def identify_bottlenecks(self, metrics: PerformanceMetrics, results: List[Any]) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # CPU bottleneck
        if metrics.cpu_utilization > 95:
            bottlenecks.append("CPU overutilization - consider reducing parallel workers")
        elif metrics.cpu_utilization < 50:
            bottlenecks.append("CPU underutilization - consider increasing parallel workers")
        
        # Memory bottleneck
        if metrics.memory_utilization > 90:
            bottlenecks.append("Memory pressure - reduce memory per worker or test batch size")
        
        # Parallel efficiency bottleneck
        if metrics.parallel_efficiency < 60:
            bottlenecks.append("Poor parallel efficiency - check test dependencies and sharding")
        
        # Worker utilization bottleneck
        if metrics.worker_utilization < 70:
            bottlenecks.append("Uneven worker load distribution - optimize test sharding")
        
        # Cache effectiveness
        if metrics.cache_hit_rate < 20 and len(results) > 10:
            bottlenecks.append("Low cache hit rate - improve test stability and caching strategy")
        
        return bottlenecks


class OptimizationEngine:
    """Generates optimization recommendations based on performance analysis"""
    
    def __init__(self):
        self.recommendation_rules = self._initialize_recommendation_rules()
        self.historical_effectiveness = defaultdict(list)
    
    def _initialize_recommendation_rules(self) -> Dict[str, Any]:
        """Initialize optimization recommendation rules"""
        return {
            'cpu_optimization': {
                'high_cpu_low_efficiency': {
                    'condition': lambda m: m.cpu_utilization > 90 and m.parallel_efficiency < 60,
                    'recommendation': 'Reduce parallel workers and optimize test sharding for CPU-bound tests',
                    'impact': 'high',
                    'effort': 'easy'
                },
                'low_cpu_high_capacity': {
                    'condition': lambda m: m.cpu_utilization < 50 and m.worker_utilization > 80,
                    'recommendation': 'Increase parallel workers to utilize available CPU capacity',
                    'impact': 'medium',
                    'effort': 'trivial'
                }
            },
            'memory_optimization': {
                'memory_pressure': {
                    'condition': lambda m: m.memory_utilization > 85,
                    'recommendation': 'Implement memory pooling and reduce test isolation overhead',
                    'impact': 'high',
                    'effort': 'moderate'
                }
            },
            'caching_optimization': {
                'low_cache_hit': {
                    'condition': lambda m: m.cache_hit_rate < 30 and m.test_count > 20,
                    'recommendation': 'Improve test determinism and dependency tracking for better caching',
                    'impact': 'high',
                    'effort': 'moderate'
                }
            },
            'sharding_optimization': {
                'poor_load_balance': {
                    'condition': lambda m: m.worker_utilization < 70,
                    'recommendation': 'Implement intelligent test sharding based on execution time history',
                    'impact': 'medium',
                    'effort': 'moderate'
                }
            }
        }
    
    def generate_recommendations(self, metrics: PerformanceMetrics, 
                               bottlenecks: List[str]) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Apply recommendation rules
        for category, rules in self.recommendation_rules.items():
            for rule_name, rule in rules.items():
                if rule['condition'](metrics):
                    recommendation = OptimizationRecommendation(
                        category=category,
                        recommendation=rule['recommendation'],
                        impact_level=rule['impact'],
                        estimated_improvement=self._estimate_improvement(rule, metrics),
                        implementation_effort=rule['effort'],
                        business_value=self._calculate_business_value(rule, metrics)
                    )
                    recommendations.append(recommendation)
        
        # Sort by impact and business value
        recommendations.sort(key=lambda r: (
            {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[r.impact_level],
            r.estimated_improvement
        ), reverse=True)
        
        return recommendations
    
    def _estimate_improvement(self, rule: Dict, metrics: PerformanceMetrics) -> float:
        """Estimate performance improvement percentage"""
        # Base improvement estimates based on rule type and current metrics
        base_improvements = {
            'cpu_optimization': min(50.0, (100 - metrics.parallel_efficiency) * 0.8),
            'memory_optimization': min(30.0, (metrics.memory_utilization - 50) * 0.5),
            'caching_optimization': min(60.0, (100 - metrics.cache_hit_rate) * 0.6),
            'sharding_optimization': min(40.0, (100 - metrics.worker_utilization) * 0.4)
        }
        
        # Get category from rule context (simplified)
        for category in base_improvements:
            if category in rule['recommendation'].lower():
                return base_improvements[category]
        
        return 10.0  # Default improvement estimate
    
    def _calculate_business_value(self, rule: Dict, metrics: PerformanceMetrics) -> str:
        """Calculate business value description"""
        improvement = self._estimate_improvement(rule, metrics)
        
        if improvement > 40:
            return "High business value: Significant reduction in CI/CD time and developer wait time"
        elif improvement > 20:
            return "Medium business value: Notable improvement in development velocity"
        else:
            return "Low business value: Incremental efficiency gains"


class PerformanceReporter:
    """Generates performance reports and visualizations"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def generate_performance_report(self, metrics: PerformanceMetrics, 
                                  recommendations: List[OptimizationRecommendation],
                                  historical_data: List[PerformanceMetrics] = None) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'summary': self._generate_summary(metrics),
            'detailed_metrics': asdict(metrics),
            'recommendations': [asdict(rec) for rec in recommendations],
            'trends': self._analyze_trends(historical_data) if historical_data else {},
            'generated_at': datetime.now().isoformat(),
            'productivity_assessment': self._assess_productivity(metrics)
        }
        
        # Save report to file
        report_file = self.output_dir / f"performance_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate human-readable summary
        self._generate_text_summary(report, metrics, recommendations)
        
        return report
    
    def _generate_summary(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Generate executive summary"""
        return {
            'execution_time': f"{metrics.total_duration:.2f} seconds",
            'productivity_gain': f"{metrics.productivity_gain:.1f}x",
            'success_rate': f"{metrics.success_rate:.1f}%",
            'cache_effectiveness': f"{metrics.cache_hit_rate:.1f}%",
            'resource_efficiency': f"{metrics.parallel_efficiency:.1f}%",
            'tests_executed': metrics.test_count,
            'performance_grade': self._calculate_performance_grade(metrics)
        }
    
    def _calculate_performance_grade(self, metrics: PerformanceMetrics) -> str:
        """Calculate overall performance grade"""
        score = (
            metrics.success_rate * 0.3 +
            metrics.cache_hit_rate * 0.2 +
            metrics.parallel_efficiency * 0.3 +
            min(metrics.productivity_gain * 10, 100) * 0.2
        )
        
        if score >= 90:
            return "A+ (Excellent)"
        elif score >= 80:
            return "A (Very Good)"
        elif score >= 70:
            return "B (Good)"
        elif score >= 60:
            return "C (Fair)"
        else:
            return "D (Needs Improvement)"
    
    def _generate_text_summary(self, report: Dict, metrics: PerformanceMetrics, 
                              recommendations: List[OptimizationRecommendation]):
        """Generate human-readable text summary"""
        summary_file = self.output_dir / "latest_performance_summary.md"
        
        with open(summary_file, 'w') as f:
            f.write("# Test Execution Performance Report\n\n")
            f.write(f"**Generated:** {report['generated_at']}\n\n")
            
            f.write("## Executive Summary\n\n")
            for key, value in report['summary'].items():
                f.write(f"- **{key.replace('_', ' ').title()}:** {value}\n")
            
            f.write(f"\n## Key Metrics\n\n")
            f.write(f"- **Total Duration:** {metrics.total_duration:.2f} seconds\n")
            f.write(f"- **Tests Executed:** {metrics.test_count}\n")
            f.write(f"- **Success Rate:** {metrics.success_rate:.1f}%\n")
            f.write(f"- **Productivity Gain:** {metrics.productivity_gain:.1f}x\n")
            f.write(f"- **Cache Hit Rate:** {metrics.cache_hit_rate:.1f}%\n")
            f.write(f"- **Parallel Efficiency:** {metrics.parallel_efficiency:.1f}%\n")
            
            if recommendations:
                f.write(f"\n## Top Optimization Recommendations\n\n")
                for i, rec in enumerate(recommendations[:3], 1):
                    f.write(f"{i}. **{rec.category.replace('_', ' ').title()}** ({rec.impact_level} impact)\n")
                    f.write(f"   - {rec.recommendation}\n")
                    f.write(f"   - Estimated improvement: {rec.estimated_improvement:.1f}%\n")
                    f.write(f"   - Implementation effort: {rec.implementation_effort}\n\n")


class PerformanceOptimizer:
    """Main performance optimization coordinator"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path("performance_optimization")
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        self.analyzer = PerformanceAnalyzer()
        self.optimizer = OptimizationEngine()
        self.reporter = PerformanceReporter(self.cache_dir / "reports")
        
        # Historical data
        self.metrics_history = deque(maxlen=100)
        self.optimization_effectiveness = defaultdict(list)
    
    def optimize_execution_performance(self, results: List[Any], 
                                     total_duration: float,
                                     execution_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Complete performance optimization pipeline"""
        
        # Analyze performance
        metrics = self.analyzer.analyze_execution_performance(results, total_duration)
        self.metrics_history.append(metrics)
        
        # Identify bottlenecks
        bottlenecks = self.analyzer.identify_bottlenecks(metrics, results)
        
        # Generate recommendations
        recommendations = self.optimizer.generate_recommendations(metrics, bottlenecks)
        
        # Generate report
        report = self.reporter.generate_performance_report(
            metrics, recommendations, list(self.metrics_history)
        )
        
        # Log key insights
        self._log_performance_insights(metrics, recommendations)
        
        return {
            'metrics': metrics,
            'bottlenecks': bottlenecks,
            'recommendations': recommendations,
            'report': report,
            'next_execution_config': self._suggest_next_config(metrics, recommendations)
        }
    
    def _suggest_next_config(self, metrics: PerformanceMetrics, 
                           recommendations: List[OptimizationRecommendation]) -> Dict[str, Any]:
        """Suggest configuration for next execution"""
        config = {
            'max_workers': max(1, psutil.cpu_count() - 1),
            'cache_enabled': True,
            'fail_fast_enabled': True,
            'memory_per_worker_mb': 512
        }
        
        # Apply recommendations to config
        for rec in recommendations:
            if 'increase parallel workers' in rec.recommendation.lower():
                config['max_workers'] = min(config['max_workers'] + 2, psutil.cpu_count())
            elif 'reduce parallel workers' in rec.recommendation.lower():
                config['max_workers'] = max(1, config['max_workers'] - 2)
            elif 'memory' in rec.recommendation.lower():
                config['memory_per_worker_mb'] = max(256, config['memory_per_worker_mb'] - 128)
        
        return config
    
    def _log_performance_insights(self, metrics: PerformanceMetrics, 
                                recommendations: List[OptimizationRecommendation]):
        """Log key performance insights"""
        logger.info(f"Performance Analysis Complete:")
        logger.info(f"  - Productivity Gain: {metrics.productivity_gain:.1f}x")
        logger.info(f"  - Success Rate: {metrics.success_rate:.1f}%")
        logger.info(f"  - Cache Hit Rate: {metrics.cache_hit_rate:.1f}%")
        logger.info(f"  - Parallel Efficiency: {metrics.parallel_efficiency:.1f}%")
        
        if recommendations:
            logger.info(f"  - Top Recommendation: {recommendations[0].recommendation}")
            logger.info(f"  - Estimated Improvement: {recommendations[0].estimated_improvement:.1f}%")