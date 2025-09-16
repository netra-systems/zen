"""
Performance Baseline Configuration and Documentation

Defines performance benchmarks, baselines, and SLA requirements.
Provides configuration for performance test execution and reporting.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Establish performance SLAs and monitoring
- Value Impact: Prevents performance regressions and ensures scalability
- Revenue Impact: Maintains customer satisfaction and prevents churn (+$30K MRR)
"""

from dataclasses import asdict, dataclass
from enum import Enum
from netra_backend.app.monitoring.metrics_collector import PerformanceMetric
from typing import Any, Dict, List, Optional
import json
import os
import time

class PerformanceCategory(Enum):

    """Categories of performance metrics."""

    DATABASE = "database"

    WEBSOCKET = "websocket"

    AGENT = "agent"

    API = "api"

    MEMORY = "memory"

    CACHE = "cache"

    CONCURRENT = "concurrent"

    NETWORK = "network"

class SeverityLevel(Enum):

    """Severity levels for performance issues."""

    CRITICAL = "critical"

    HIGH = "high"

    MEDIUM = "medium"

    LOW = "low"

    INFO = "info"

@dataclass

class PerformanceMetric:

    """Definition of a performance metric."""

    name: str

    category: PerformanceCategory

    description: str

    unit: str

    baseline_value: float

    warning_threshold: float

    critical_threshold: float

    higher_is_better: bool = False  # True for metrics like throughput
    
    def evaluate_performance(self, actual_value: float) -> SeverityLevel:

        """Evaluate performance level based on actual value."""

        if self.higher_is_better:

            if actual_value >= self.baseline_value:

                return SeverityLevel.INFO

            elif actual_value >= self.warning_threshold:

                return SeverityLevel.LOW

            elif actual_value >= self.critical_threshold:

                return SeverityLevel.MEDIUM

            else:

                return SeverityLevel.CRITICAL

        else:

            if actual_value <= self.baseline_value:

                return SeverityLevel.INFO

            elif actual_value <= self.warning_threshold:

                return SeverityLevel.LOW

            elif actual_value <= self.critical_threshold:

                return SeverityLevel.MEDIUM

            else:

                return SeverityLevel.CRITICAL

class PerformanceBaselines:

    """Centralized performance baseline configuration."""
    
    def __init__(self):

        self.metrics = self._initialize_metrics()
    
    def _initialize_metrics(self) -> Dict[str, PerformanceMetric]:

        """Initialize all performance metrics and their baselines."""

        metrics = {}
        
        # Database Performance Metrics

        metrics['db_bulk_insert_50k'] = PerformanceMetric(

            name='Database Bulk Insert (50K records)',

            category=PerformanceCategory.DATABASE,

            description='Time to insert 50,000 records in bulk operation',

            unit='seconds',

            baseline_value=30.0,

            warning_threshold=45.0,

            critical_threshold=60.0

        )
        
        metrics['db_concurrent_reads'] = PerformanceMetric(

            name='Concurrent Database Reads',

            category=PerformanceCategory.DATABASE,

            description='Time for 10 concurrent database read operations',

            unit='seconds',

            baseline_value=5.0,

            warning_threshold=8.0,

            critical_threshold=12.0

        )
        
        metrics['db_query_response_time'] = PerformanceMetric(

            name='Database Query Response Time',

            category=PerformanceCategory.DATABASE,

            description='Average response time for database queries',

            unit='seconds',

            baseline_value=0.1,

            warning_threshold=0.5,

            critical_threshold=1.0

        )
        
        # WebSocket Performance Metrics

        metrics['websocket_throughput'] = PerformanceMetric(

            name='WebSocket Message Throughput',

            category=PerformanceCategory.WEBSOCKET,

            description='Messages processed per second through WebSocket',

            unit='messages/second',

            baseline_value=1000.0,

            warning_threshold=500.0,

            critical_threshold=250.0,

            higher_is_better=True

        )
        
        metrics['websocket_broadcast_throughput'] = PerformanceMetric(

            name='WebSocket Broadcast Throughput',

            category=PerformanceCategory.WEBSOCKET,

            description='Broadcast messages per second to multiple connections',

            unit='messages/second',

            baseline_value=5000.0,

            warning_threshold=2500.0,

            critical_threshold=1000.0,

            higher_is_better=True

        )
        
        metrics['websocket_connection_time'] = PerformanceMetric(

            name='WebSocket Connection Time',

            category=PerformanceCategory.WEBSOCKET,

            description='Time to establish WebSocket connection',

            unit='seconds',

            baseline_value=0.1,

            warning_threshold=0.3,

            critical_threshold=0.5

        )
        
        # Agent Performance Metrics

        metrics['agent_processing_time'] = PerformanceMetric(

            name='Agent Processing Time',

            category=PerformanceCategory.AGENT,

            description='Time for agent to process 100 requests',

            unit='seconds',

            baseline_value=10.0,

            warning_threshold=20.0,

            critical_threshold=30.0

        )
        
        metrics['concurrent_agent_throughput'] = PerformanceMetric(

            name='Concurrent Agent Throughput',

            category=PerformanceCategory.AGENT,

            description='Requests processed per second by concurrent agents',

            unit='requests/second',

            baseline_value=20.0,

            warning_threshold=10.0,

            critical_threshold=5.0,

            higher_is_better=True

        )
        
        metrics['llm_response_time'] = PerformanceMetric(

            name='LLM Response Time',

            category=PerformanceCategory.AGENT,

            description='Average LLM API response time',

            unit='seconds',

            baseline_value=2.0,

            warning_threshold=5.0,

            critical_threshold=10.0

        )
        
        # API Performance Metrics

        metrics['api_response_time'] = PerformanceMetric(

            name='API Response Time',

            category=PerformanceCategory.API,

            description='Average API endpoint response time',

            unit='seconds',

            baseline_value=0.2,

            warning_threshold=1.0,

            critical_threshold=2.0

        )
        
        metrics['concurrent_api_load'] = PerformanceMetric(

            name='Concurrent API Load',

            category=PerformanceCategory.API,

            description='Time to handle 1000 requests with 50 concurrent clients',

            unit='seconds',

            baseline_value=20.0,

            warning_threshold=40.0,

            critical_threshold=60.0

        )
        
        metrics['api_throughput'] = PerformanceMetric(

            name='API Throughput',

            category=PerformanceCategory.API,

            description='Requests processed per second',

            unit='requests/second',

            baseline_value=100.0,

            warning_threshold=50.0,

            critical_threshold=25.0,

            higher_is_better=True

        )
        
        # Memory Performance Metrics

        metrics['memory_allocation_time'] = PerformanceMetric(

            name='Memory Allocation Time',

            category=PerformanceCategory.MEMORY,

            description='Time to allocate 100MB of memory',

            unit='seconds',

            baseline_value=1.0,

            warning_threshold=3.0,

            critical_threshold=5.0

        )
        
        metrics['memory_cleanup_time'] = PerformanceMetric(

            name='Memory Cleanup Time',

            category=PerformanceCategory.MEMORY,

            description='Time for garbage collection and cleanup',

            unit='seconds',

            baseline_value=0.1,

            warning_threshold=0.5,

            critical_threshold=1.0

        )
        
        metrics['memory_peak_usage'] = PerformanceMetric(

            name='Peak Memory Usage',

            category=PerformanceCategory.MEMORY,

            description='Peak memory usage during operations',

            unit='MB',

            baseline_value=512.0,

            warning_threshold=1024.0,

            critical_threshold=2048.0

        )
        
        # Cache Performance Metrics

        metrics['cache_hit_rate'] = PerformanceMetric(

            name='Cache Hit Rate',

            category=PerformanceCategory.CACHE,

            description='Percentage of cache hits',

            unit='percentage',

            baseline_value=80.0,

            warning_threshold=60.0,

            critical_threshold=40.0,

            higher_is_better=True

        )
        
        metrics['cache_response_time'] = PerformanceMetric(

            name='Cache Response Time',

            category=PerformanceCategory.CACHE,

            description='Average cache lookup response time',

            unit='seconds',

            baseline_value=0.001,

            warning_threshold=0.01,

            critical_threshold=0.1

        )
        
        # Concurrent User Metrics

        metrics['concurrent_user_response_time'] = PerformanceMetric(

            name='Concurrent User Response Time',

            category=PerformanceCategory.CONCURRENT,

            description='Average response time with concurrent users',

            unit='seconds',

            baseline_value=2.0,

            warning_threshold=5.0,

            critical_threshold=10.0

        )
        
        metrics['concurrent_user_success_rate'] = PerformanceMetric(

            name='Concurrent User Success Rate',

            category=PerformanceCategory.CONCURRENT,

            description='Success rate under concurrent load',

            unit='percentage',

            baseline_value=99.0,

            warning_threshold=95.0,

            critical_threshold=90.0,

            higher_is_better=True

        )
        
        metrics['max_concurrent_users'] = PerformanceMetric(

            name='Maximum Concurrent Users',

            category=PerformanceCategory.CONCURRENT,

            description='Maximum number of concurrent users supported',

            unit='users',

            baseline_value=100.0,

            warning_threshold=75.0,

            critical_threshold=50.0,

            higher_is_better=True

        )
        
        return metrics
    
    def get_metric(self, name: str) -> Optional[PerformanceMetric]:

        """Get metric configuration by name."""

        return self.metrics.get(name)
    
    def get_metrics_by_category(self, category: PerformanceCategory) -> Dict[str, PerformanceMetric]:

        """Get all metrics for a specific category."""

        return {

            name: metric for name, metric in self.metrics.items() 

            if metric.category == category

        }
    
    def get_all_categories(self) -> List[PerformanceCategory]:

        """Get all performance categories."""

        return list(set(metric.category for metric in self.metrics.values()))

@dataclass

class PerformanceTestResult:

    """Result of a performance test execution."""

    metric_name: str

    actual_value: float

    baseline_value: float

    severity: SeverityLevel

    passed: bool

    timestamp: float

    test_duration: float

    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):

        if self.additional_data is None:

            self.additional_data = {}

class PerformanceReporter:

    """Generates performance test reports and documentation."""
    
    def __init__(self, baselines: PerformanceBaselines):

        self.baselines = baselines
    
    def generate_baseline_report(self) -> Dict[str, Any]:

        """Generate comprehensive baseline configuration report."""

        report = {

            'generated_at': time.time(),

            'total_metrics': len(self.baselines.metrics),

            'categories': {},

            'metrics': {}

        }
        
        # Group by category

        for category in self.baselines.get_all_categories():

            category_metrics = self.baselines.get_metrics_by_category(category)

            report['categories'][category.value] = {

                'count': len(category_metrics),

                'metrics': list(category_metrics.keys())

            }
        
        # Add detailed metric information

        for name, metric in self.baselines.metrics.items():

            report['metrics'][name] = {

                'category': metric.category.value,

                'description': metric.description,

                'unit': metric.unit,

                'baseline_value': metric.baseline_value,

                'warning_threshold': metric.warning_threshold,

                'critical_threshold': metric.critical_threshold,

                'higher_is_better': metric.higher_is_better

            }
        
        return report
    
    def generate_test_results_report(self, results: List[PerformanceTestResult]) -> Dict[str, Any]:

        """Generate test results report."""

        if not results:

            return {'error': 'No test results provided'}
        
        # Categorize results

        passed = [r for r in results if r.passed]

        failed = [r for r in results if not r.passed]
        
        # Group by severity

        by_severity = {}

        for severity in SeverityLevel:

            by_severity[severity.value] = [r for r in results if r.severity == severity]
        
        # Group by category

        by_category = {}

        for result in results:

            metric = self.baselines.get_metric(result.metric_name)

            if metric:

                category = metric.category.value

                if category not in by_category:

                    by_category[category] = []

                by_category[category].append(result)
        
        report = {

            'generated_at': time.time(),

            'summary': {

                'total_tests': len(results),

                'passed': len(passed),

                'failed': len(failed),

                'pass_rate': (len(passed) / len(results)) * 100 if results else 0,

                'avg_duration': sum(r.test_duration for r in results) / len(results) if results else 0

            },

            'severity_breakdown': {

                severity: len(results_list) 

                for severity, results_list in by_severity.items()

            },

            'category_breakdown': {

                category: {

                    'total': len(results_list),

                    'passed': len([r for r in results_list if r.passed]),

                    'failed': len([r for r in results_list if not r.passed])

                }

                for category, results_list in by_category.items()

            },

            'detailed_results': [

                {

                    'metric_name': r.metric_name,

                    'actual_value': r.actual_value,

                    'baseline_value': r.baseline_value,

                    'severity': r.severity.value,

                    'passed': r.passed,

                    'timestamp': r.timestamp,

                    'duration': r.test_duration,

                    'additional_data': r.additional_data

                }

                for r in results

            ]

        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str, directory: str = "test_reports"):

        """Save report to file."""

        os.makedirs(directory, exist_ok=True)

        filepath = os.path.join(directory, filename)
        
        with open(filepath, 'w') as f:

            json.dump(report, f, indent=2, default=str)
        
        print(f"Report saved to: {filepath}")
    
    def print_summary(self, report: Dict[str, Any]):

        """Print performance summary to console."""

        if 'summary' in report:

            summary = report['summary']

            print("\n" + "=" * 60)

            print("PERFORMANCE TEST SUMMARY")

            print("=" * 60)

            print(f"Total Tests: {summary['total_tests']}")

            print(f"Passed: {summary['passed']}")

            print(f"Failed: {summary['failed']}")

            print(f"Pass Rate: {summary['pass_rate']:.1f}%")

            print(f"Average Duration: {summary['avg_duration']:.3f}s")
            
            if 'severity_breakdown' in report:

                print("\nSeverity Breakdown:")

                for severity, count in report['severity_breakdown'].items():

                    if count > 0:

                        print(f"  {severity.upper()}: {count}")
            
            if 'category_breakdown' in report:

                print("\nCategory Breakdown:")

                for category, stats in report['category_breakdown'].items():

                    pass_rate = (stats['passed'] / stats['total']) * 100 if stats['total'] > 0 else 0

                    print(f"  {category.upper()}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)")
            
            print("=" * 60)
        
        elif 'total_metrics' in report:

            print("\n" + "=" * 60)

            print("PERFORMANCE BASELINE CONFIGURATION")

            print("=" * 60)

            print(f"Total Metrics Defined: {report['total_metrics']}")
            
            print("\nMetrics by Category:")

            for category, info in report['categories'].items():

                print(f"  {category.upper()}: {info['count']} metrics")
            
            print("=" * 60)

class PerformanceBenchmarkRunner:

    """Orchestrates performance benchmark execution."""
    
    def __init__(self):

        self.baselines = PerformanceBaselines()

        self.reporter = PerformanceReporter(self.baselines)

        self.results: List[PerformanceTestResult] = []
    
    def record_result(self, metric_name: str, actual_value: float, 

                     test_duration: float, additional_data: Dict[str, Any] = None):

        """Record a performance test result."""

        metric = self.baselines.get_metric(metric_name)

        if not metric:

            print(f"Warning: Unknown metric '{metric_name}'")

            return
        
        severity = metric.evaluate_performance(actual_value)

        passed = severity in [SeverityLevel.INFO, SeverityLevel.LOW]
        
        result = PerformanceTestResult(

            metric_name=metric_name,

            actual_value=actual_value,

            baseline_value=metric.baseline_value,

            severity=severity,

            passed=passed,

            timestamp=time.time(),

            test_duration=test_duration,

            additional_data=additional_data or {}

        )
        
        self.results.append(result)
    
    def generate_final_report(self, save_to_file: bool = True) -> Dict[str, Any]:

        """Generate final benchmark report."""

        report = self.reporter.generate_test_results_report(self.results)
        
        if save_to_file:

            timestamp = int(time.time())

            filename = f"performance_benchmark_report_{timestamp}.json"

            self.reporter.save_report(report, filename)
        
        return report
    
    def print_results_summary(self):

        """Print results summary to console."""

        report = self.reporter.generate_test_results_report(self.results)

        self.reporter.print_summary(report)
    
    def clear_results(self):

        """Clear accumulated results."""

        self.results = []

def get_performance_baselines() -> PerformanceBaselines:

    """Get the global performance baselines instance."""

    return PerformanceBaselines()

def get_benchmark_runner() -> PerformanceBenchmarkRunner:

    """Get a new benchmark runner instance."""

    return PerformanceBenchmarkRunner()

if __name__ == "__main__":
    # Generate baseline configuration documentation

    baselines = get_performance_baselines()

    reporter = PerformanceReporter(baselines)
    
    baseline_report = reporter.generate_baseline_report()

    reporter.save_report(baseline_report, "performance_baselines.json")

    reporter.print_summary(baseline_report)
    
    print("\nPerformance baseline configuration generated.")

    print("Run performance tests to generate benchmark reports.")
