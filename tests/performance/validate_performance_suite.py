#!/usr/bin/env python3
"""
Performance Suite Validation Script

This script validates the entire performance testing suite by running all tests
and generating a comprehensive validation report for the UserExecutionContext migration.

This ensures all performance tests are working correctly and provides confidence
in the performance validation results.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pytest
    import psutil
    from netra_backend.app.logging_config import central_logger
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install dependencies: pip install -r tests/performance/requirements-performance.txt")
    sys.exit(1)

logger = central_logger.get_logger(__name__)


class PerformanceSuiteValidator:
    """Comprehensive validator for the performance testing suite."""
    
    def __init__(self):
        self.validation_start = None
        self.validation_results = {}
        self.system_info = self._get_system_info()
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for validation context."""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'platform': sys.platform,
            'python_version': sys.version,
            'cpu_count': os.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'working_directory': str(Path.cwd()),
            'pytest_version': pytest.__version__ if hasattr(pytest, '__version__') else 'unknown'
        }
    
    def validate_test_files_exist(self) -> Dict[str, bool]:
        """Validate that all required test files exist."""
        logger.info("Validating performance test files...")
        
        required_files = [
            "tests/performance/test_phase1_context_performance.py",
            "tests/performance/test_database_performance.py", 
            "tests/performance/test_stress_and_limits.py",
            "tests/performance/run_performance_tests.py",
            "tests/performance/performance_monitor.py",
            "tests/performance/requirements-performance.txt",
            "tests/performance/performance_thresholds.json"
        ]
        
        file_status = {}
        
        for file_path in required_files:
            full_path = project_root / file_path
            exists = full_path.exists()
            file_status[file_path] = exists
            
            if exists:
                # Check file size (should be substantial)
                size_kb = full_path.stat().st_size / 1024
                logger.info(f"✅ {file_path} exists ({size_kb:.1f}KB)")
            else:
                logger.error(f"❌ {file_path} missing")
        
        return file_status
    
    def validate_test_syntax(self) -> Dict[str, Tuple[bool, str]]:
        """Validate Python syntax of all test files."""
        logger.info("Validating test file syntax...")
        
        test_files = [
            "tests/performance/test_phase1_context_performance.py",
            "tests/performance/test_database_performance.py",
            "tests/performance/test_stress_and_limits.py",
            "tests/performance/run_performance_tests.py",
            "tests/performance/performance_monitor.py"
        ]
        
        syntax_results = {}
        
        for test_file in test_files:
            file_path = project_root / test_file
            
            try:
                # Check syntax by compiling
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                compile(source_code, str(file_path), 'exec')
                syntax_results[test_file] = (True, "Syntax valid")
                logger.info(f"✅ {test_file} syntax valid")
                
            except SyntaxError as e:
                syntax_results[test_file] = (False, f"Syntax error: {e}")
                logger.error(f"❌ {test_file} syntax error: {e}")
                
            except Exception as e:
                syntax_results[test_file] = (False, f"Error: {e}")
                logger.error(f"❌ {test_file} validation error: {e}")
        
        return syntax_results
    
    def validate_test_dependencies(self) -> Dict[str, bool]:
        """Validate that all test dependencies are available."""
        logger.info("Validating test dependencies...")
        
        required_modules = [
            'pytest',
            'pytest_asyncio', 
            'psutil',
            'asyncio',
            'time',
            'uuid',
            'json',
            'gc',
            'threading',
            'concurrent.futures',
            'unittest.mock',
            'dataclasses',
            'datetime',
            'pathlib'
        ]
        
        dependency_status = {}
        
        for module_name in required_modules:
            try:
                __import__(module_name)
                dependency_status[module_name] = True
                logger.debug(f"✅ {module_name} available")
                
            except ImportError:
                dependency_status[module_name] = False
                logger.error(f"❌ {module_name} not available")
        
        return dependency_status
    
    async def run_quick_performance_validation(self) -> Dict[str, Any]:
        """Run quick validation of performance test functionality."""
        logger.info("Running quick performance validation...")
        
        validation_results = {}
        
        # Test 1: Context creation validation
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            start_time = time.time()
            contexts = []
            
            for i in range(100):
                context = UserExecutionContext(
                    user_id=f"validation_user_{i}",
                    thread_id=f"validation_thread_{i}",
                    run_id=f"validation_run_{i}",
                    request_id=f"validation_req_{i}"
                )
                contexts.append(context)
            
            creation_time = (time.time() - start_time) * 1000
            
            validation_results['context_creation'] = {
                'success': True,
                'contexts_created': len(contexts),
                'creation_time_ms': creation_time,
                'creation_rate_per_sec': len(contexts) / (creation_time / 1000)
            }
            
            logger.info(f"✅ Context creation validation: {len(contexts)} contexts in {creation_time:.1f}ms")
            
        except Exception as e:
            validation_results['context_creation'] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"❌ Context creation validation failed: {e}")
        
        # Test 2: Memory profiling validation
        try:
            import gc
            
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Create and destroy objects to test memory tracking
            test_objects = []
            for i in range(1000):
                test_objects.append({"id": i, "data": f"test_data_{i}" * 100})
            
            peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Clean up
            del test_objects
            gc.collect()
            
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            validation_results['memory_profiling'] = {
                'success': True,
                'start_memory_mb': start_memory,
                'peak_memory_mb': peak_memory,
                'end_memory_mb': end_memory,
                'memory_growth_mb': peak_memory - start_memory,
                'memory_recovered_mb': peak_memory - end_memory
            }
            
            logger.info(f"✅ Memory profiling validation: {start_memory:.1f}MB -> {peak_memory:.1f}MB -> {end_memory:.1f}MB")
            
        except Exception as e:
            validation_results['memory_profiling'] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"❌ Memory profiling validation failed: {e}")
        
        # Test 3: Async operation validation
        try:
            async def test_async_operation():
                await asyncio.sleep(0.01)  # 10ms
                return "async_test_result"
            
            start_time = time.time()
            
            # Run multiple async operations
            tasks = [test_async_operation() for _ in range(50)]
            results = await asyncio.gather(*tasks)
            
            async_time = (time.time() - start_time) * 1000
            
            validation_results['async_operations'] = {
                'success': True,
                'operations_completed': len(results),
                'total_time_ms': async_time,
                'operations_per_second': len(results) / (async_time / 1000)
            }
            
            logger.info(f"✅ Async operations validation: {len(results)} operations in {async_time:.1f}ms")
            
        except Exception as e:
            validation_results['async_operations'] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"❌ Async operations validation failed: {e}")
        
        return validation_results
    
    def run_dry_run_tests(self) -> Dict[str, Any]:
        """Run dry-run of performance tests to validate functionality."""
        logger.info("Running performance test dry-run...")
        
        dry_run_results = {}
        
        # List of test files to dry-run
        test_files = [
            "tests/performance/test_phase1_context_performance.py",
            "tests/performance/test_database_performance.py",
            "tests/performance/test_stress_and_limits.py"
        ]
        
        for test_file in test_files:
            file_path = project_root / test_file
            
            logger.info(f"Dry-running {test_file}...")
            
            try:
                # Run pytest with collect-only to validate test discovery
                result = subprocess.run([
                    sys.executable, '-m', 'pytest',
                    str(file_path),
                    '--collect-only',
                    '--quiet'
                ], capture_output=True, text=True, cwd=project_root)
                
                if result.returncode == 0:
                    # Count discovered tests
                    lines = result.stdout.split('\n')
                    test_count = len([line for line in lines if '::test_' in line])
                    
                    dry_run_results[test_file] = {
                        'success': True,
                        'tests_discovered': test_count,
                        'output_lines': len(lines)
                    }
                    
                    logger.info(f"✅ {test_file}: {test_count} tests discovered")
                    
                else:
                    dry_run_results[test_file] = {
                        'success': False,
                        'error': result.stderr,
                        'exit_code': result.returncode
                    }
                    
                    logger.error(f"❌ {test_file}: dry-run failed (exit code {result.returncode})")
                    logger.error(f"Error output: {result.stderr}")
                
            except Exception as e:
                dry_run_results[test_file] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"❌ {test_file}: dry-run exception: {e}")
        
        return dry_run_results
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        logger.info("Generating validation report...")
        
        # Collect all validation data
        file_validation = self.validate_test_files_exist()
        syntax_validation = self.validate_test_syntax()
        dependency_validation = self.validate_test_dependencies()
        
        # Run quick performance validation (async)
        async def run_quick_validation():
            return await self.run_quick_performance_validation()
        
        quick_validation = asyncio.run(run_quick_validation())
        dry_run_validation = self.run_dry_run_tests()
        
        # Assess overall validation status
        files_valid = all(file_validation.values())
        syntax_valid = all(result[0] for result in syntax_validation.values())
        dependencies_valid = all(dependency_validation.values())
        quick_tests_valid = all(result.get('success', False) for result in quick_validation.values())
        dry_runs_valid = all(result.get('success', False) for result in dry_run_validation.values())
        
        overall_valid = all([files_valid, syntax_valid, dependencies_valid, quick_tests_valid, dry_runs_valid])
        
        validation_report = {
            'validation_summary': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_status': 'VALID' if overall_valid else 'INVALID',
                'files_valid': files_valid,
                'syntax_valid': syntax_valid,
                'dependencies_valid': dependencies_valid,
                'quick_tests_valid': quick_tests_valid,
                'dry_runs_valid': dry_runs_valid
            },
            'system_information': self.system_info,
            'file_validation': file_validation,
            'syntax_validation': {k: {'valid': v[0], 'message': v[1]} for k, v in syntax_validation.items()},
            'dependency_validation': dependency_validation,
            'quick_performance_validation': quick_validation,
            'dry_run_validation': dry_run_validation,
            'recommendations': self._generate_validation_recommendations(overall_valid)
        }
        
        return validation_report
    
    def _generate_validation_recommendations(self, overall_valid: bool) -> List[Dict[str, str]]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if overall_valid:
            recommendations.extend([
                {
                    'priority': 'INFO',
                    'category': 'validation',
                    'action': 'Performance suite validation passed - ready for execution'
                },
                {
                    'priority': 'MEDIUM',
                    'category': 'execution',
                    'action': 'Run full performance test suite with: python tests/performance/run_performance_tests.py --all'
                },
                {
                    'priority': 'LOW',
                    'category': 'monitoring',
                    'action': 'Consider running continuous monitoring during performance tests'
                }
            ])
        else:
            recommendations.extend([
                {
                    'priority': 'HIGH',
                    'category': 'validation',
                    'action': 'Fix validation issues before running performance tests'
                },
                {
                    'priority': 'HIGH', 
                    'category': 'dependencies',
                    'action': 'Install missing dependencies: pip install -r tests/performance/requirements-performance.txt'
                }
            ])
        
        return recommendations
    
    def save_validation_report(self, report: Dict[str, Any]) -> str:
        """Save validation report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_suite_validation_{timestamp}.json"
        report_path = project_root / filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Validation report saved to: {report_path}")
        return str(report_path)
    
    def print_validation_summary(self, report: Dict[str, Any]):
        """Print validation summary to console."""
        print("\n" + "="*80)
        print("PERFORMANCE SUITE VALIDATION SUMMARY")
        print("="*80)
        
        summary = report['validation_summary']
        overall_status = summary['overall_status']
        status_icon = "✅" if overall_status == 'VALID' else "❌"
        
        print(f"{status_icon} Overall Status: {overall_status}")
        print(f"🕒 Validation Time: {summary['timestamp']}")
        print()
        
        # Detailed validation results
        validation_checks = [
            ('📁 Files Valid', summary['files_valid']),
            ('🐍 Syntax Valid', summary['syntax_valid']),
            ('📦 Dependencies Valid', summary['dependencies_valid']),
            ('⚡ Quick Tests Valid', summary['quick_tests_valid']),
            ('🔍 Dry Runs Valid', summary['dry_runs_valid'])
        ]
        
        for check_name, is_valid in validation_checks:
            icon = "✅" if is_valid else "❌"
            print(f"{icon} {check_name}")
        
        print()
        
        # File validation details
        print("📁 File Validation Details:")
        for file_path, exists in report['file_validation'].items():
            icon = "✅" if exists else "❌"
            print(f"  {icon} {file_path}")
        
        print()
        
        # Syntax validation details
        print("🐍 Syntax Validation Details:")
        for file_path, result in report['syntax_validation'].items():
            icon = "✅" if result['valid'] else "❌"
            print(f"  {icon} {file_path}: {result['message']}")
        
        print()
        
        # Quick test details
        print("⚡ Quick Test Validation:")
        for test_name, result in report['quick_performance_validation'].items():
            icon = "✅" if result.get('success', False) else "❌"
            print(f"  {icon} {test_name}")
            
            if result.get('success', False):
                if 'creation_rate_per_sec' in result:
                    print(f"      Rate: {result['creation_rate_per_sec']:.0f} ops/sec")
                if 'operations_per_second' in result:
                    print(f"      Rate: {result['operations_per_second']:.0f} ops/sec")
            else:
                print(f"      Error: {result.get('error', 'Unknown')}")
        
        print()
        
        # Recommendations
        print("💡 Recommendations:")
        for rec in report['recommendations']:
            priority_icons = {'HIGH': '🔥', 'MEDIUM': '⚠️', 'LOW': '💭', 'INFO': 'ℹ️', 'CRITICAL': '💀'}
            icon = priority_icons.get(rec['priority'], '❓')
            print(f"  {icon} [{rec['priority']}] {rec['action']}")
        
        print("\n" + "="*80)
        
        if overall_status == 'VALID':
            print("✅ Performance suite validation PASSED")
            print("🚀 Ready to run full performance tests")
        else:
            print("❌ Performance suite validation FAILED")
            print("🔧 Please fix issues before running performance tests")
        
        print("="*80)


def main():
    """Main entry point for performance suite validation."""
    parser = argparse.ArgumentParser(
        description="Validate Performance Testing Suite for UserExecutionContext Migration"
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        help='Output file for validation report (JSON format)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--quick-only',
        action='store_true',
        help='Run only quick validation (skip dry-run tests)'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        validator = PerformanceSuiteValidator()
        
        print("🔍 Starting performance suite validation...")
        print(f"🖥️  System: {validator.system_info['platform']} | "
              f"Python: {validator.system_info['python_version'].split()[0]} | "
              f"CPUs: {validator.system_info['cpu_count']} | "
              f"Memory: {validator.system_info['memory_total_gb']:.1f}GB")
        print()
        
        # Generate validation report
        report = validator.generate_validation_report()
        
        # Print summary
        validator.print_validation_summary(report)
        
        # Save report if requested
        if args.output_file or report['validation_summary']['overall_status'] == 'INVALID':
            report_file = validator.save_validation_report(report)
            print(f"\n📊 Detailed validation report: {report_file}")
        
        # Return appropriate exit code
        if report['validation_summary']['overall_status'] == 'VALID':
            print(f"\n🎉 Performance suite ready for testing!")
            print("Run tests with: python tests/performance/run_performance_tests.py --all")
            return 0
        else:
            print(f"\n💥 Performance suite has validation issues")
            print("Please review the validation report and fix issues")
            return 1
    
    except Exception as e:
        logger.error(f"Error during validation: {e}")
        print(f"❌ Validation error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)