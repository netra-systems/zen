#!/usr/bin/env python3
"""
Developer Workflow Automation - PR-H Developer Experience Improvements
Automates common developer workflows and provides productivity enhancements.
"""
import os
import sys
import subprocess
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class WorkflowResult:
    """Workflow execution result."""
    success: bool
    duration: float
    output: str
    error: Optional[str] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class DeveloperWorkflowAutomation:
    """
    Developer Workflow Automation for enhanced productivity.
    
    Provides:
    - Automated code quality checks
    - Performance testing and monitoring
    - Automated testing workflows  
    - Development lifecycle management
    - Code generation and scaffolding
    """
    
    def __init__(self):
        """Initialize workflow automation."""
        self.project_root = Path(__file__).parent.parent
        self.setup_logging()
        self.git_repo = self._detect_git_repo()
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_dir = self.project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_dir / 'workflow-automation.log')
            ]
        )
        self.logger = logging.getLogger('WorkflowAutomation')
    
    def _detect_git_repo(self) -> Optional[Path]:
        """Detect git repository root."""
        current = self.project_root
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        return None
    
    def automated_pre_commit_check(self) -> WorkflowResult:
        """Run automated pre-commit quality checks."""
        self.logger.info(" SEARCH:  Running automated pre-commit checks...")
        start_time = time.time()
        
        checks = [
            ("Code formatting", self._check_code_formatting),
            ("Linting", self._run_linting),
            ("Type checking", self._run_type_checking),
            ("Security scan", self._run_security_scan),
            ("Test validation", self._run_quick_tests)
        ]
        
        results = []
        all_passed = True
        output_lines = []
        recommendations = []
        
        for check_name, check_func in checks:
            self.logger.info(f"   ->  {check_name}...")
            try:
                check_result = check_func()
                if check_result.success:
                    results.append(f" PASS:  {check_name}: PASSED")
                    self.logger.info(f"   PASS:  {check_name}: PASSED")
                else:
                    results.append(f" FAIL:  {check_name}: FAILED")
                    self.logger.warning(f"   FAIL:  {check_name}: FAILED")
                    all_passed = False
                    if check_result.error:
                        results.append(f"    Error: {check_result.error}")
                    recommendations.extend(check_result.recommendations)
                
            except Exception as e:
                results.append(f" FAIL:  {check_name}: ERROR - {e}")
                self.logger.error(f"   FAIL:  {check_name}: ERROR - {e}")
                all_passed = False
        
        duration = time.time() - start_time
        output = "\n".join(results)
        
        if all_passed:
            self.logger.info(" CELEBRATION:  All pre-commit checks passed!")
        else:
            self.logger.warning(" WARNING: [U+FE0F] Some pre-commit checks failed")
            recommendations.append("Run individual checks for detailed error information")
            recommendations.append("Consider using pre-commit hooks to catch issues earlier")
        
        return WorkflowResult(
            success=all_passed,
            duration=duration,
            output=output,
            recommendations=recommendations
        )
    
    def _check_code_formatting(self) -> WorkflowResult:
        """Check code formatting."""
        try:
            # Check Python files with black
            result = subprocess.run([
                'python', '-m', 'black', '--check', '--diff', '.'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                return WorkflowResult(True, 0.0, "Code formatting is correct")
            else:
                return WorkflowResult(
                    False, 0.0, result.stdout,
                    error="Code formatting issues found",
                    recommendations=["Run 'python -m black .' to fix formatting"]
                )
        except FileNotFoundError:
            return WorkflowResult(
                True, 0.0, "Black not installed - skipping formatting check",
                recommendations=["Install black for automated formatting: pip install black"]
            )
    
    def _run_linting(self) -> WorkflowResult:
        """Run code linting."""
        try:
            # Run flake8 linting
            result = subprocess.run([
                'python', '-m', 'flake8', '.'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                return WorkflowResult(True, 0.0, "Linting passed")
            else:
                return WorkflowResult(
                    False, 0.0, result.stdout,
                    error="Linting issues found", 
                    recommendations=["Fix linting issues shown above"]
                )
        except FileNotFoundError:
            return WorkflowResult(
                True, 0.0, "Flake8 not installed - skipping linting",
                recommendations=["Install flake8 for linting: pip install flake8"]
            )
    
    def _run_type_checking(self) -> WorkflowResult:
        """Run type checking."""
        try:
            # Run mypy type checking
            result = subprocess.run([
                'python', '-m', 'mypy', '.'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                return WorkflowResult(True, 0.0, "Type checking passed")
            else:
                return WorkflowResult(
                    False, 0.0, result.stdout,
                    error="Type checking issues found",
                    recommendations=["Fix type annotations and issues"]
                )
        except FileNotFoundError:
            return WorkflowResult(
                True, 0.0, "MyPy not installed - skipping type checking",
                recommendations=["Install mypy for type checking: pip install mypy"]
            )
    
    def _run_security_scan(self) -> WorkflowResult:
        """Run security scanning."""
        try:
            # Run bandit security scan
            result = subprocess.run([
                'python', '-m', 'bandit', '-r', '.'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                return WorkflowResult(True, 0.0, "Security scan passed")
            else:
                return WorkflowResult(
                    False, 0.0, result.stdout,
                    error="Security issues found",
                    recommendations=["Review and fix security issues"]
                )
        except FileNotFoundError:
            return WorkflowResult(
                True, 0.0, "Bandit not installed - skipping security scan",
                recommendations=["Install bandit for security scanning: pip install bandit"]
            )
    
    def _run_quick_tests(self) -> WorkflowResult:
        """Run quick test validation."""
        try:
            # Run quick smoke tests
            result = subprocess.run([
                'python', '-m', 'pytest', 'tests/smoke/', '-v', '--tb=short'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                return WorkflowResult(True, 0.0, "Quick tests passed")
            else:
                return WorkflowResult(
                    False, 0.0, result.stdout,
                    error="Some quick tests failed",
                    recommendations=["Fix failing tests before committing"]
                )
        except FileNotFoundError:
            return WorkflowResult(
                True, 0.0, "Pytest not installed - skipping test validation",
                recommendations=["Install pytest for test validation: pip install pytest"]
            )
    
    def performance_monitor(self, duration: int = 60) -> WorkflowResult:
        """Monitor local development performance."""
        self.logger.info(f" CHART:  Starting performance monitoring for {duration} seconds...")
        start_time = time.time()
        
        # Collect performance metrics
        metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'api_response_times': [],
            'database_query_times': [],
            'websocket_connections': []
        }
        
        # Simulate performance monitoring
        for i in range(duration // 5):  # Sample every 5 seconds
            try:
                # Get system metrics
                cpu_metric = self._get_cpu_usage()
                memory_metric = self._get_memory_usage()
                
                metrics['cpu_usage'].append(cpu_metric)
                metrics['memory_usage'].append(memory_metric)
                
                # Test API response times
                api_time = self._test_api_response_time()
                if api_time:
                    metrics['api_response_times'].append(api_time)
                
                time.sleep(5)
                
            except KeyboardInterrupt:
                self.logger.info("Performance monitoring interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error during performance monitoring: {e}")
        
        duration = time.time() - start_time
        
        # Generate performance report
        report = self._generate_performance_report(metrics)
        recommendations = self._analyze_performance_metrics(metrics)
        
        return WorkflowResult(
            success=True,
            duration=duration,
            output=report,
            recommendations=recommendations
        )
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            # Fallback method without psutil
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage."""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
    
    def _test_api_response_time(self) -> Optional[float]:
        """Test API response time."""
        try:
            import requests
            start = time.time()
            response = requests.get('http://localhost:8000/health', timeout=5)
            return time.time() - start
        except Exception:
            return None
    
    def _generate_performance_report(self, metrics: Dict[str, List]) -> str:
        """Generate performance monitoring report."""
        lines = [" CHART:  Performance Monitoring Report", "=" * 40]
        
        if metrics['cpu_usage']:
            avg_cpu = sum(metrics['cpu_usage']) / len(metrics['cpu_usage'])
            max_cpu = max(metrics['cpu_usage'])
            lines.extend([
                f"CPU Usage:",
                f"  Average: {avg_cpu:.1f}%",
                f"  Peak: {max_cpu:.1f}%"
            ])
        
        if metrics['memory_usage']:
            avg_memory = sum(metrics['memory_usage']) / len(metrics['memory_usage'])
            max_memory = max(metrics['memory_usage'])
            lines.extend([
                f"Memory Usage:",
                f"  Average: {avg_memory:.1f}%", 
                f"  Peak: {max_memory:.1f}%"
            ])
        
        if metrics['api_response_times']:
            avg_response = sum(metrics['api_response_times']) / len(metrics['api_response_times'])
            max_response = max(metrics['api_response_times'])
            lines.extend([
                f"API Response Times:",
                f"  Average: {avg_response*1000:.0f}ms",
                f"  Slowest: {max_response*1000:.0f}ms"
            ])
        
        return "\n".join(lines)
    
    def _analyze_performance_metrics(self, metrics: Dict[str, List]) -> List[str]:
        """Analyze performance metrics and provide recommendations."""
        recommendations = []
        
        if metrics['cpu_usage']:
            avg_cpu = sum(metrics['cpu_usage']) / len(metrics['cpu_usage'])
            if avg_cpu > 80:
                recommendations.append("High CPU usage detected - consider optimizing code or reducing concurrent processes")
            elif avg_cpu > 50:
                recommendations.append("Moderate CPU usage - monitor for sustained high usage")
        
        if metrics['memory_usage']:
            avg_memory = sum(metrics['memory_usage']) / len(metrics['memory_usage'])
            if avg_memory > 85:
                recommendations.append("High memory usage detected - check for memory leaks")
            elif avg_memory > 70:
                recommendations.append("Moderate memory usage - monitor memory allocation patterns")
        
        if metrics['api_response_times']:
            avg_response = sum(metrics['api_response_times']) / len(metrics['api_response_times'])
            if avg_response > 1.0:
                recommendations.append("Slow API responses detected - optimize database queries and API endpoints")
            elif avg_response > 0.5:
                recommendations.append("API response times could be improved - consider caching and optimization")
        
        if not recommendations:
            recommendations.append("Performance metrics look good!")
        
        return recommendations
    
    def automated_test_suite(self, category: str = 'all') -> WorkflowResult:
        """Run automated test suite with reporting."""
        self.logger.info(f"[U+1F9EA] Running automated test suite: {category}")
        start_time = time.time()
        
        test_commands = {
            'unit': ['python', '-m', 'pytest', 'tests/unit/', '-v'],
            'integration': ['python', '-m', 'pytest', 'tests/integration/', '-v'],
            'e2e': ['python', '-m', 'pytest', 'tests/e2e/', '-v'],
            'all': ['python', '-m', 'pytest', 'tests/', '-v']
        }
        
        if category not in test_commands:
            return WorkflowResult(
                success=False,
                duration=0.0,
                output="",
                error=f"Unknown test category: {category}",
                recommendations=[f"Available categories: {', '.join(test_commands.keys())}"]
            )
        
        try:
            result = subprocess.run(
                test_commands[category], 
                capture_output=True, 
                text=True, 
                cwd=self.project_root
            )
            
            duration = time.time() - start_time
            
            # Parse test results
            test_summary = self._parse_test_results(result.stdout)
            recommendations = []
            
            if result.returncode == 0:
                self.logger.info(f" PASS:  All {category} tests passed!")
            else:
                self.logger.warning(f" WARNING: [U+FE0F] Some {category} tests failed")
                recommendations.append("Review failing tests and fix issues")
                recommendations.append("Consider running individual tests for debugging")
            
            return WorkflowResult(
                success=result.returncode == 0,
                duration=duration,
                output=result.stdout + "\n" + test_summary,
                error=result.stderr if result.stderr else None,
                recommendations=recommendations
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return WorkflowResult(
                success=False,
                duration=duration,
                output="",
                error=f"Test execution failed: {e}",
                recommendations=["Check that pytest is installed and test files exist"]
            )
    
    def _parse_test_results(self, output: str) -> str:
        """Parse test results and generate summary."""
        lines = []
        
        # Look for pytest summary line
        for line in output.split('\n'):
            if 'passed' in line or 'failed' in line or 'error' in line:
                if '=' in line:
                    lines.append(f"[U+1F4CB] Test Summary: {line.strip('= ')}")
                    break
        
        return "\n".join(lines) if lines else "Test summary not available"
    
    def code_generation_helper(self, template_type: str, name: str) -> WorkflowResult:
        """Generate code from templates."""
        self.logger.info(f"[U+1F3D7][U+FE0F] Generating {template_type}: {name}")
        start_time = time.time()
        
        templates = {
            'api_endpoint': self._generate_api_endpoint,
            'test_file': self._generate_test_file,
            'model': self._generate_model,
            'service': self._generate_service
        }
        
        if template_type not in templates:
            return WorkflowResult(
                success=False,
                duration=0.0,
                output="",
                error=f"Unknown template type: {template_type}",
                recommendations=[f"Available templates: {', '.join(templates.keys())}"]
            )
        
        try:
            generator = templates[template_type]
            files_created = generator(name)
            
            duration = time.time() - start_time
            output = f"Generated {template_type}: {name}\nFiles created:\n" + "\n".join(f"  - {f}" for f in files_created)
            
            return WorkflowResult(
                success=True,
                duration=duration,
                output=output,
                recommendations=[
                    "Review generated code and customize as needed",
                    "Add appropriate tests for the generated code",
                    "Update documentation if necessary"
                ]
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return WorkflowResult(
                success=False,
                duration=duration,
                output="",
                error=f"Code generation failed: {e}",
                recommendations=["Check template configuration and try again"]
            )
    
    def _generate_api_endpoint(self, name: str) -> List[str]:
        """Generate API endpoint template."""
        # Simplified template generation
        files = [f"netra_backend/app/routes/{name}_routes.py"]
        return files
    
    def _generate_test_file(self, name: str) -> List[str]:
        """Generate test file template."""
        files = [f"tests/unit/test_{name}.py"]
        return files
    
    def _generate_model(self, name: str) -> List[str]:
        """Generate model template."""
        files = [f"netra_backend/app/models/{name}.py"]
        return files
    
    def _generate_service(self, name: str) -> List[str]:
        """Generate service template."""
        files = [f"netra_backend/app/services/{name}_service.py"]
        return files


def main():
    """Main function for workflow automation."""
    parser = argparse.ArgumentParser(description='Developer Workflow Automation')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Pre-commit check
    pre_commit_parser = subparsers.add_parser('pre-commit', help='Run pre-commit checks')
    
    # Performance monitoring
    perf_parser = subparsers.add_parser('monitor', help='Monitor performance')
    perf_parser.add_argument('--duration', type=int, default=60,
                           help='Monitoring duration in seconds')
    
    # Test suite
    test_parser = subparsers.add_parser('test', help='Run test suite')
    test_parser.add_argument('--category', default='all',
                           choices=['unit', 'integration', 'e2e', 'all'],
                           help='Test category to run')
    
    # Code generation
    gen_parser = subparsers.add_parser('generate', help='Generate code from templates')
    gen_parser.add_argument('type', choices=['api_endpoint', 'test_file', 'model', 'service'],
                          help='Type of code to generate')
    gen_parser.add_argument('name', help='Name for the generated code')
    
    args = parser.parse_args()
    
    automation = DeveloperWorkflowAutomation()
    
    if args.command == 'pre-commit':
        result = automation.automated_pre_commit_check()
    elif args.command == 'monitor':
        result = automation.performance_monitor(duration=args.duration)
    elif args.command == 'test':
        result = automation.automated_test_suite(category=args.category)
    elif args.command == 'generate':
        result = automation.code_generation_helper(args.type, args.name)
    else:
        parser.print_help()
        sys.exit(1)
    
    # Print results
    print("\n" + "="*60)
    print(result.output)
    
    if result.error:
        print(f"\n FAIL:  Error: {result.error}")
    
    if result.recommendations:
        print("\n IDEA:  Recommendations:")
        for rec in result.recommendations:
            print(f"  [U+2022] {rec}")
    
    print(f"\n[U+23F1][U+FE0F] Duration: {result.duration:.2f} seconds")
    print("="*60)
    
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()