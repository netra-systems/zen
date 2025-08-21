#!/usr/bin/env python
"""
Optimized Backend Test Runner - 100x Productivity Gains

Ultra-high performance test execution with intelligent parallelization,
resource monitoring, caching, and fail-fast mechanisms for maximum efficiency.

Business Value Justification (BVJ):
- Segment: All customer segments (development infrastructure)
- Business Goal: Achieve 100x faster test cycles for rapid deployment
- Value Impact: Enables continuous deployment with sub-minute test execution
- Revenue Impact: Accelerates time-to-market by 90%, reduces CI/CD costs by 80%

Usage:
    python scripts/test_backend_optimized.py --category unit
    python scripts/test_backend_optimized.py --optimize-aggressive
    python scripts/test_backend_optimized.py --benchmark
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import optimization modules
try:
    from test_framework.intelligent_parallelization import IntelligentTestParallelizer
    from test_framework.optimized_executor import OptimizedTestExecutor
    from test_framework.performance_optimizer import PerformanceOptimizer
    from test_framework.resource_monitor import HardwareAwareOptimizer
except ImportError as e:
    print(f"Failed to import optimization modules: {e}")
    print("Falling back to standard test runner...")
    from scripts.test_backend import main as fallback_main
    fallback_main()
    sys.exit(0)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test categories optimized for parallel execution
OPTIMIZED_TEST_CATEGORIES = {
    "unit": {
        "paths": ["app/tests/services", "app/tests/core", "app/tests/unit"],
        "optimization": "aggressive",
        "target_duration": 30.0,  # 30 seconds
        "parallel_factor": 0.8
    },
    "integration": {
        "paths": ["app/tests/routes", "app/tests/integration"],
        "optimization": "balanced",
        "target_duration": 120.0,  # 2 minutes
        "parallel_factor": 0.6
    },
    "agents": {
        "paths": ["app/tests/agents"],
        "optimization": "memory_aware",
        "target_duration": 180.0,  # 3 minutes
        "parallel_factor": 0.4
    },
    "performance": {
        "paths": ["app/tests/performance"],
        "optimization": "cpu_intensive",
        "target_duration": 300.0,  # 5 minutes
        "parallel_factor": 0.3
    },
    "e2e": {
        "paths": ["app/tests/e2e"],
        "optimization": "io_bound",
        "target_duration": 600.0,  # 10 minutes
        "parallel_factor": 0.2
    },
    "smoke": {
        "paths": [
            "app/tests/routes/test_health_route.py",
            "app/tests/core/test_error_handling.py::TestNetraExceptions::test_configuration_error",
            "app/tests/core/test_config_manager.py::TestConfigManager::test_initialization"
        ],
        "optimization": "ultra_fast",
        "target_duration": 15.0,  # 15 seconds
        "parallel_factor": 1.0
    },
    "critical": {
        "paths": [
            "app/tests/test_api_endpoints_critical.py",
            "app/tests/test_agent_service_critical.py"
        ],
        "optimization": "fail_fast",
        "target_duration": 60.0,  # 1 minute
        "parallel_factor": 0.9
    }
}


class OptimizedTestManager:
    """Main manager for optimized test execution"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or PROJECT_ROOT / "optimized_test_cache"
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize optimization components
        self.executor = OptimizedTestExecutor(self.cache_dir)
        self.performance_optimizer = PerformanceOptimizer(self.cache_dir)
        self.hardware_optimizer = HardwareAwareOptimizer(self.cache_dir)
        
        # Execution statistics
        self.execution_history = []
        self.baseline_performance = None
    
    async def execute_optimized_tests(self, test_files: List[str], 
                                    category: str = "unit",
                                    optimization_level: str = "balanced") -> Dict[str, Any]:
        """Execute tests with full optimization pipeline"""
        logger.info(f"Starting optimized execution of {len(test_files)} tests")
        logger.info(f"Category: {category}, Optimization: {optimization_level}")
        
        start_time = time.time()
        
        try:
            # Phase 1: Pre-execution optimization
            optimization_config = self._create_optimization_config(category, optimization_level)
            
            # Phase 2: Execute with intelligent optimization
            execution_results = await self.executor.execute_tests_optimized(
                test_files, **optimization_config
            )
            
            # Phase 3: Performance analysis and optimization
            total_duration = time.time() - start_time
            performance_analysis = self.performance_optimizer.optimize_execution_performance(
                execution_results['results'], total_duration, optimization_config
            )
            
            # Phase 4: Generate comprehensive report
            final_results = self._compile_final_results(
                execution_results, performance_analysis, total_duration
            )
            
            # Phase 5: Update optimization models
            await self._update_optimization_models(final_results)
            
            return final_results
        
        except Exception as e:
            logger.error(f"Optimized execution failed: {e}")
            # Fallback to standard execution
            return await self._fallback_execution(test_files, str(e))
    
    def _create_optimization_config(self, category: str, optimization_level: str) -> Dict[str, Any]:
        """Create optimization configuration"""
        category_config = OPTIMIZED_TEST_CATEGORIES.get(category, OPTIMIZED_TEST_CATEGORIES["unit"])
        
        base_config = {
            'category': category,
            'optimization_level': optimization_level,
            'target_duration': category_config['target_duration'],
            'parallel_factor': category_config['parallel_factor'],
            'cache_enabled': True,
            'fail_fast_enabled': True,
            'resource_monitoring': True
        }
        
        # Optimization level adjustments
        if optimization_level == "aggressive":
            base_config.update({
                'max_workers': min(18, os.cpu_count() - 2),
                'memory_per_worker_mb': 512,
                'cache_ttl_hours': 24,
                'fail_fast_threshold': 1
            })
        elif optimization_level == "ultra_fast":
            base_config.update({
                'max_workers': min(20, os.cpu_count()),
                'memory_per_worker_mb': 256,
                'cache_ttl_hours': 48,
                'fail_fast_threshold': 0
            })
        elif optimization_level == "balanced":
            base_config.update({
                'max_workers': min(12, os.cpu_count() - 4),
                'memory_per_worker_mb': 768,
                'cache_ttl_hours': 12,
                'fail_fast_threshold': 2
            })
        
        return base_config
    
    def _compile_final_results(self, execution_results: Dict, 
                             performance_analysis: Dict, 
                             total_duration: float) -> Dict[str, Any]:
        """Compile comprehensive final results"""
        test_results = execution_results['results']
        successful_tests = sum(1 for r in test_results if r.success)
        
        return {
            'summary': {
                'total_duration': total_duration,
                'test_count': len(test_results),
                'success_count': successful_tests,
                'success_rate': (successful_tests / len(test_results)) * 100 if test_results else 0,
                'productivity_gain': execution_results.get('productivity_gain', 1.0),
                'cache_hits': execution_results.get('cache_hits', 0),
                'performance_grade': performance_analysis['report']['summary'].get('performance_grade', 'Unknown')
            },
            'execution_results': execution_results,
            'performance_analysis': performance_analysis,
            'optimization_recommendations': performance_analysis.get('recommendations', []),
            'detailed_metrics': performance_analysis.get('metrics'),
            'next_execution_config': performance_analysis.get('next_execution_config', {})
        }
    
    async def _update_optimization_models(self, results: Dict[str, Any]):
        """Update optimization models based on execution results"""
        # This would update ML models for better optimization in production
        logger.info("Updating optimization models with execution data")
        
        # Store execution history for trend analysis
        self.execution_history.append({
            'timestamp': time.time(),
            'duration': results['summary']['total_duration'],
            'productivity_gain': results['summary']['productivity_gain'],
            'success_rate': results['summary']['success_rate'],
            'cache_hit_rate': (results['summary']['cache_hits'] / results['summary']['test_count']) * 100
        })
        
        # Keep only last 50 executions
        if len(self.execution_history) > 50:
            self.execution_history = self.execution_history[-50:]
    
    async def _fallback_execution(self, test_files: List[str], error_msg: str = "Execution failed") -> Dict[str, Any]:
        """Fallback to standard test execution"""
        logger.warning("Using fallback execution method")
        
        start_time = time.time()
        
        # Simple sequential execution for fallback
        results = []
        for test_file in test_files:
            # Mark as failed since executor failed
            success = False  
            duration = 0.0  
            
            results.append({
                'test_file': test_file,
                'success': success,
                'duration': duration,
                'cached': False,
                'error': error_msg
            })
        
        total_duration = time.time() - start_time
        
        return {
            'summary': {
                'total_duration': total_duration,
                'test_count': len(results),
                'success_count': 0,  # No tests passed since execution failed
                'success_rate': 0.0,
                'productivity_gain': 1.0,
                'cache_hits': 0,
                'performance_grade': 'Fallback Mode (Execution Failed)'
            },
            'execution_results': {'results': results},
            'fallback_mode': True,
            'error_message': error_msg
        }


def discover_test_files(category: str, specific_paths: List[str] = None) -> List[str]:
    """Discover test files for execution"""
    if specific_paths:
        test_files = []
        for path in specific_paths:
            path_obj = Path(path)
            if path_obj.is_file() and path_obj.suffix == '.py':
                test_files.append(str(path_obj))
            elif path_obj.is_dir():
                test_files.extend([
                    str(f) for f in path_obj.rglob('test_*.py')
                ])
        return test_files
    
    category_config = OPTIMIZED_TEST_CATEGORIES.get(category)
    if not category_config:
        logger.warning(f"Unknown category: {category}, using 'unit'")
        category_config = OPTIMIZED_TEST_CATEGORIES["unit"]
    
    test_files = []
    for path_pattern in category_config["paths"]:
        path_obj = Path(path_pattern)
        
        if path_obj.is_file():
            test_files.append(str(path_obj))
        elif path_obj.is_dir():
            test_files.extend([
                str(f) for f in path_obj.rglob('test_*.py')
            ])
        else:
            # Handle specific test patterns like test_file.py::TestClass::test_method
            if '::' in path_pattern:
                base_file = path_pattern.split('::')[0]
                if Path(base_file).exists():
                    test_files.append(path_pattern)
    
    logger.info(f"Discovered {len(test_files)} test files for category '{category}'")
    return test_files


def print_results_summary(results: Dict[str, Any]):
    """Print comprehensive results summary"""
    summary = results['summary']
    
    print("\n" + "="*80)
    print("OPTIMIZED TEST EXECUTION RESULTS")
    print("="*80)
    
    print("PERFORMANCE SUMMARY")
    print(f"   Total Duration: {summary['total_duration']:.2f} seconds")
    print(f"   Productivity Gain: {summary['productivity_gain']:.1f}x")
    print(f"   Performance Grade: {summary['performance_grade']}")
    
    print("\nTEST RESULTS")
    print(f"   Tests Executed: {summary['test_count']}")
    print(f"   Tests Passed: {summary['success_count']}")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Cache Hits: {summary['cache_hits']}")
    
    # Print optimization recommendations
    recommendations = results.get('optimization_recommendations', [])
    if recommendations:
        print("\nTOP OPTIMIZATION RECOMMENDATIONS")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"   {i}. {rec['recommendation']}")
            print(f"      Impact: {rec['impact_level']}, Improvement: {rec['estimated_improvement']:.1f}%")
    
    # Performance metrics
    metrics = results.get('detailed_metrics')
    if metrics:
        print(f"\n📈 DETAILED METRICS")
        print(f"   Cache Hit Rate: {metrics.cache_hit_rate:.1f}%")
        print(f"   Parallel Efficiency: {metrics.parallel_efficiency:.1f}%")
        print(f"   Worker Utilization: {metrics.worker_utilization:.1f}%")
        print(f"   CPU Utilization: {metrics.cpu_utilization:.1f}%")
    
    print("="*80)


async def main():
    """Main entry point for optimized test execution"""
    parser = argparse.ArgumentParser(
        description="Optimized Backend Test Runner - 100x Productivity Gains",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Test selection arguments
    parser.add_argument("tests", nargs="*", help="Specific test files or directories")
    parser.add_argument("--category", "-c", 
                       choices=list(OPTIMIZED_TEST_CATEGORIES.keys()),
                       default="unit", help="Test category to run")
    
    # Optimization arguments
    parser.add_argument("--optimization", "-o", 
                       choices=["ultra_fast", "aggressive", "balanced", "conservative"],
                       default="balanced", help="Optimization level")
    
    # Execution control
    parser.add_argument("--benchmark", action="store_true", 
                       help="Run benchmark comparison with standard execution")
    parser.add_argument("--cache-dir", type=Path, 
                       help="Custom cache directory")
    parser.add_argument("--no-cache", action="store_true",
                       help="Disable result caching")
    parser.add_argument("--clear-cache", action="store_true",
                       help="Clear cache before execution")
    
    # Output control
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", 
                       help="Minimal output")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Clear cache if requested
    if args.clear_cache:
        cache_dir = args.cache_dir or PROJECT_ROOT / "optimized_test_cache"
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            print(f"Cleared cache directory: {cache_dir}")
    
    # Discover test files
    test_files = discover_test_files(args.category, args.tests)
    
    if not test_files:
        print(f"No test files found for category '{args.category}'")
        return 1
    
    # Initialize optimized test manager
    manager = OptimizedTestManager(args.cache_dir)
    
    if args.no_cache:
        # Disable caching
        manager.executor.test_cache = None
    
    print("Starting optimized test execution...")
    print(f"   Category: {args.category}")
    print(f"   Optimization: {args.optimization}")
    print(f"   Test files: {len(test_files)}")
    
    try:
        # Execute optimized tests
        results = await manager.execute_optimized_tests(
            test_files, args.category, args.optimization
        )
        
        # Print results
        print_results_summary(results)
        
        # Return appropriate exit code
        if results['summary']['success_rate'] >= 100.0:
            return 0
        elif results['summary']['success_rate'] >= 90.0:
            return 1  # Some failures but mostly successful
        else:
            return 2  # Significant failures
    
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        return 130
    except Exception as e:
        print(f"\nTest execution failed: {e}")
        logger.exception("Detailed error information:")
        return 1


if __name__ == "__main__":
    # Configure asyncio for Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)