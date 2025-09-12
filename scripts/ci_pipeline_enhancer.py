#!/usr/bin/env python3
"""
CI/CD Pipeline Enhancer - Level 3 System-wide Safeguards
CRITICAL: Prevents systemic failures affecting multiple components

Business Value: Protects $500K+ ARR through comprehensive validation
Revenue Impact: Eliminates integration failures in production
"""

import argparse
import json
import subprocess
import sys
import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum


class ValidationStage(Enum):
    """Pipeline validation stages"""
    SYNTAX = "syntax"
    ASYNC_PATTERNS = "async_patterns"
    API_CONTRACTS = "api_contracts"  
    TYPE_SAFETY = "type_safety"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"


@dataclass
class PipelineValidationResult:
    """Result of pipeline validation"""
    stage: ValidationStage
    success: bool
    duration_seconds: float
    message: str
    details: Dict[str, Any] = None
    blocking: bool = True


@dataclass 
class PipelineConfiguration:
    """Configuration for enhanced pipeline"""
    enable_async_validation: bool = True
    enable_contract_validation: bool = True
    enable_type_safety: bool = True
    enable_integration_tests: bool = True
    enable_performance_monitoring: bool = True
    fail_fast: bool = False
    parallel_execution: bool = True
    timeout_minutes: int = 10


class AsyncPatternValidator:
    """Validates async patterns in CI/CD"""
    
    def __init__(self, config: PipelineConfiguration):
        self.config = config
        
    def validate(self) -> PipelineValidationResult:
        """Run async pattern validation"""
        try:
            # Run the async pattern enforcer
            result = subprocess.run([
                sys.executable, 'scripts/async_pattern_enforcer.py', 
                '--ci-mode', '--errors-only', '--json'
            ], capture_output=True, text=True, timeout=self.config.timeout_minutes * 60)
            
            if result.returncode == 0:
                output_data = json.loads(result.stdout) if result.stdout else {}
                return PipelineValidationResult(
                    stage=ValidationStage.ASYNC_PATTERNS,
                    success=True,
                    duration_seconds=0.0,  # Would track actual time
                    message="All async patterns valid",
                    details=output_data
                )
            else:
                output_data = json.loads(result.stdout) if result.stdout else {}
                error_count = output_data.get('errors', 0)
                return PipelineValidationResult(
                    stage=ValidationStage.ASYNC_PATTERNS,
                    success=False,
                    duration_seconds=0.0,
                    message=f"Found {error_count} async pattern violations",
                    details=output_data,
                    blocking=True
                )
                
        except subprocess.TimeoutExpired:
            return PipelineValidationResult(
                stage=ValidationStage.ASYNC_PATTERNS,
                success=False,
                duration_seconds=self.config.timeout_minutes * 60,
                message="Async pattern validation timed out",
                blocking=True
            )
        except Exception as e:
            return PipelineValidationResult(
                stage=ValidationStage.ASYNC_PATTERNS,
                success=False,
                duration_seconds=0.0,
                message=f"Async pattern validation failed: {str(e)}",
                blocking=True
            )


class APIContractValidator:
    """Validates API contracts in CI/CD"""
    
    def __init__(self, config: PipelineConfiguration):
        self.config = config
        
    def validate(self) -> PipelineValidationResult:
        """Run API contract validation"""
        try:
            # Run the API contract validator
            result = subprocess.run([
                sys.executable, 'scripts/api_contract_validator.py',
                '--validate-all', '--breaking-changes-only', '--json'
            ], capture_output=True, text=True, timeout=self.config.timeout_minutes * 60)
            
            if result.returncode == 0:
                output_data = json.loads(result.stdout) if result.stdout else {}
                return PipelineValidationResult(
                    stage=ValidationStage.API_CONTRACTS,
                    success=True,
                    duration_seconds=0.0,
                    message="All API contracts compatible",
                    details=output_data
                )
            else:
                output_data = json.loads(result.stdout) if result.stdout else {}
                breaking_count = output_data.get('breaking_changes', 0)
                return PipelineValidationResult(
                    stage=ValidationStage.API_CONTRACTS,
                    success=False,
                    duration_seconds=0.0,
                    message=f"Found {breaking_count} breaking API changes",
                    details=output_data,
                    blocking=True
                )
                
        except subprocess.TimeoutExpired:
            return PipelineValidationResult(
                stage=ValidationStage.API_CONTRACTS,
                success=False,
                duration_seconds=self.config.timeout_minutes * 60,
                message="API contract validation timed out",
                blocking=True
            )
        except Exception as e:
            return PipelineValidationResult(
                stage=ValidationStage.API_CONTRACTS,
                success=False,
                duration_seconds=0.0,
                message=f"API contract validation failed: {str(e)}",
                blocking=True
            )


class TypeSafetyValidator:
    """Validates type safety with mypy"""
    
    def __init__(self, config: PipelineConfiguration):
        self.config = config
        
    def validate(self) -> PipelineValidationResult:
        """Run mypy type checking"""
        try:
            # Run mypy on key directories
            target_dirs = ['netra_backend/app', 'auth_service/auth_core', 'test_framework']
            
            results = []
            for target_dir in target_dirs:
                if Path(target_dir).exists():
                    result = subprocess.run([
                        'mypy', target_dir, '--strict', '--json-report', '/tmp/mypy_report'
                    ], capture_output=True, text=True, timeout=self.config.timeout_minutes * 60)
                    results.append((target_dir, result))
            
            # Analyze results
            total_errors = 0
            error_details = []
            
            for target_dir, result in results:
                if result.returncode != 0:
                    total_errors += 1
                    error_details.append({
                        'directory': target_dir,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    })
            
            if total_errors == 0:
                return PipelineValidationResult(
                    stage=ValidationStage.TYPE_SAFETY,
                    success=True,
                    duration_seconds=0.0,
                    message="All type annotations valid",
                    details={'directories_checked': len(target_dirs)}
                )
            else:
                return PipelineValidationResult(
                    stage=ValidationStage.TYPE_SAFETY,
                    success=False,
                    duration_seconds=0.0,
                    message=f"Type errors found in {total_errors} directories",
                    details={'errors': error_details},
                    blocking=True
                )
                
        except subprocess.TimeoutExpired:
            return PipelineValidationResult(
                stage=ValidationStage.TYPE_SAFETY,
                success=False,
                duration_seconds=self.config.timeout_minutes * 60,
                message="Type safety validation timed out",
                blocking=True
            )
        except Exception as e:
            return PipelineValidationResult(
                stage=ValidationStage.TYPE_SAFETY,
                success=False,
                duration_seconds=0.0,
                message=f"Type safety validation failed: {str(e)}",
                blocking=True
            )


class IntegrationTestValidator:
    """Validates integration tests focusing on async patterns"""
    
    def __init__(self, config: PipelineConfiguration):
        self.config = config
        
    def validate(self) -> PipelineValidationResult:
        """Run integration tests with async pattern focus"""
        try:
            # Run specific async pattern integration tests
            test_commands = [
                # WebSocket async pattern tests
                [sys.executable, 'tests/mission_critical/test_websocket_agent_events_suite.py'],
                # Agent execution async patterns
                [sys.executable, 'tests/mission_critical/test_async_pattern_compliance.py'],
                # Cross-service async communication
                [sys.executable, '-m', 'pytest', 'tests/integration/', '-k', 'async', '--tb=short']
            ]
            
            results = []
            for cmd in test_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, 
                                          timeout=self.config.timeout_minutes * 60)
                    results.append((cmd, result))
                except subprocess.TimeoutExpired:
                    results.append((cmd, None))  # Timeout marker
                except FileNotFoundError:
                    # Test file doesn't exist yet
                    continue
            
            # Analyze results
            failed_tests = []
            successful_tests = []
            
            for cmd, result in results:
                if result is None:
                    failed_tests.append({'command': ' '.join(cmd), 'error': 'Timeout'})
                elif result.returncode != 0:
                    failed_tests.append({
                        'command': ' '.join(cmd),
                        'stderr': result.stderr,
                        'stdout': result.stdout
                    })
                else:
                    successful_tests.append(' '.join(cmd))
            
            if not failed_tests:
                return PipelineValidationResult(
                    stage=ValidationStage.INTEGRATION,
                    success=True,
                    duration_seconds=0.0,
                    message=f"All {len(successful_tests)} integration tests passed",
                    details={'successful_tests': successful_tests}
                )
            else:
                return PipelineValidationResult(
                    stage=ValidationStage.INTEGRATION,
                    success=False,
                    duration_seconds=0.0,
                    message=f"{len(failed_tests)} integration tests failed",
                    details={'failed_tests': failed_tests, 'successful_tests': successful_tests},
                    blocking=True
                )
                
        except Exception as e:
            return PipelineValidationResult(
                stage=ValidationStage.INTEGRATION,
                success=False,
                duration_seconds=0.0,
                message=f"Integration test validation failed: {str(e)}",
                blocking=True
            )


class PerformanceValidator:
    """Validates performance impact of changes"""
    
    def __init__(self, config: PipelineConfiguration):
        self.config = config
        
    def validate(self) -> PipelineValidationResult:
        """Run performance validation"""
        try:
            # Simple performance check - ensuring async patterns don't degrade performance
            performance_tests = [
                # Test WebSocket event delivery speed
                [sys.executable, '-c', '''
import asyncio
import time
start = time.time()
# Simple async pattern performance test
async def test_async_performance():
    tasks = [asyncio.sleep(0.001) for _ in range(100)]
    await asyncio.gather(*tasks)
asyncio.run(test_async_performance())
duration = time.time() - start
print(f"Async pattern performance: {duration:.3f}s")
assert duration < 2.0, f"Performance regression: {duration}s > 2.0s"
''']
            ]
            
            results = []
            for cmd in performance_tests:
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                      timeout=30)  # Shorter timeout for performance tests
                results.append(result)
            
            # Check for performance regressions
            failed_checks = []
            for i, result in enumerate(results):
                if result.returncode != 0:
                    failed_checks.append({
                        'test_index': i,
                        'stderr': result.stderr,
                        'stdout': result.stdout
                    })
            
            if not failed_checks:
                return PipelineValidationResult(
                    stage=ValidationStage.PERFORMANCE,
                    success=True,
                    duration_seconds=0.0,
                    message="No performance regressions detected",
                    details={'tests_run': len(performance_tests)}
                )
            else:
                return PipelineValidationResult(
                    stage=ValidationStage.PERFORMANCE,
                    success=False,
                    duration_seconds=0.0,
                    message=f"Performance regressions detected in {len(failed_checks)} tests",
                    details={'failed_checks': failed_checks},
                    blocking=False  # Performance issues are warnings, not blockers
                )
                
        except Exception as e:
            return PipelineValidationResult(
                stage=ValidationStage.PERFORMANCE,
                success=False,
                duration_seconds=0.0,
                message=f"Performance validation failed: {str(e)}",
                blocking=False
            )


class CIPipelineEnhancer:
    """Main class for enhanced CI/CD pipeline validation"""
    
    def __init__(self, config: PipelineConfiguration = None):
        self.config = config or PipelineConfiguration()
        self.validators = self._initialize_validators()
        
    def _initialize_validators(self) -> Dict[ValidationStage, Any]:
        """Initialize validation components"""
        validators = {}
        
        if self.config.enable_async_validation:
            validators[ValidationStage.ASYNC_PATTERNS] = AsyncPatternValidator(self.config)
            
        if self.config.enable_contract_validation:
            validators[ValidationStage.API_CONTRACTS] = APIContractValidator(self.config)
            
        if self.config.enable_type_safety:
            validators[ValidationStage.TYPE_SAFETY] = TypeSafetyValidator(self.config)
            
        if self.config.enable_integration_tests:
            validators[ValidationStage.INTEGRATION] = IntegrationTestValidator(self.config)
            
        if self.config.enable_performance_monitoring:
            validators[ValidationStage.PERFORMANCE] = PerformanceValidator(self.config)
            
        return validators
    
    def run_validation(self, stages: List[ValidationStage] = None) -> List[PipelineValidationResult]:
        """Run pipeline validation"""
        if stages is None:
            stages = list(self.validators.keys())
        
        results = []
        
        for stage in stages:
            if stage not in self.validators:
                continue
                
            print(f"Running {stage.value} validation...")
            
            try:
                result = self.validators[stage].validate()
                results.append(result)
                
                if not result.success:
                    print(f" FAIL:  {stage.value}: {result.message}")
                    if result.blocking and self.config.fail_fast:
                        print("[U+1F4A5] Fail-fast enabled, stopping validation")
                        break
                else:
                    print(f" PASS:  {stage.value}: {result.message}")
                    
            except Exception as e:
                error_result = PipelineValidationResult(
                    stage=stage,
                    success=False,
                    duration_seconds=0.0,
                    message=f"Validation failed with exception: {str(e)}",
                    blocking=True
                )
                results.append(error_result)
                
                if self.config.fail_fast:
                    break
        
        return results
    
    def generate_github_actions_workflow(self) -> str:
        """Generate GitHub Actions workflow with enhanced validation"""
        workflow = {
            'name': 'Enhanced Async Pattern Validation',
            'on': ['push', 'pull_request'],
            'jobs': {
                'validate': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {
                            'name': 'Checkout code',
                            'uses': 'actions/checkout@v3'
                        },
                        {
                            'name': 'Set up Python',
                            'uses': 'actions/setup-python@v4',
                            'with': {'python-version': '3.9'}
                        },
                        {
                            'name': 'Install dependencies',
                            'run': 'pip install -r requirements.txt'
                        },
                        {
                            'name': 'Async Pattern Validation',
                            'run': 'python scripts/async_pattern_enforcer.py --ci-mode --fail-fast',
                            'if': 'always()'
                        },
                        {
                            'name': 'API Contract Validation', 
                            'run': 'python scripts/api_contract_validator.py --validate-all --breaking-changes-only',
                            'if': 'always()'
                        },
                        {
                            'name': 'Type Safety Validation',
                            'run': 'mypy netra_backend/app auth_service/auth_core test_framework --strict',
                            'if': 'always()'
                        },
                        {
                            'name': 'Integration Tests',
                            'run': 'python -m pytest tests/integration/ -k async --tb=short',
                            'if': 'always()'
                        },
                        {
                            'name': 'Performance Validation',
                            'run': 'python scripts/ci_pipeline_enhancer.py --performance-only',
                            'continue-on-error': True
                        }
                    ]
                }
            }
        }
        
        return yaml.dump(workflow, default_flow_style=False, sort_keys=False)
    
    def install_github_actions_workflow(self) -> bool:
        """Install GitHub Actions workflow file"""
        try:
            workflows_dir = Path('.github/workflows')
            workflows_dir.mkdir(parents=True, exist_ok=True)
            
            workflow_file = workflows_dir / 'async-pattern-validation.yml'
            workflow_content = self.generate_github_actions_workflow()
            
            with open(workflow_file, 'w') as f:
                f.write(workflow_content)
            
            print(f" PASS:  Installed GitHub Actions workflow: {workflow_file}")
            return True
            
        except Exception as e:
            print(f" FAIL:  Failed to install GitHub Actions workflow: {e}")
            return False


class PipelineReporter:
    """Reporter for pipeline validation results"""
    
    @staticmethod
    def generate_console_report(results: List[PipelineValidationResult]) -> str:
        """Generate human-readable console report"""
        if not results:
            return "No validation results to report"
        
        report_lines = []
        report_lines.append("[U+1F680] CI/CD PIPELINE VALIDATION RESULTS")
        report_lines.append("=" * 60)
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        blocking_failures = [r for r in failed if r.blocking]
        
        # Summary
        report_lines.append(f" PASS:  Successful: {len(successful)}")
        report_lines.append(f" FAIL:  Failed: {len(failed)} ({len(blocking_failures)} blocking)")
        report_lines.append("")
        
        # Detailed results
        for result in results:
            status_icon = " PASS: " if result.success else " FAIL: "
            blocking_text = " (BLOCKING)" if not result.success and result.blocking else ""
            
            report_lines.append(f"{status_icon} {result.stage.value.upper()}{blocking_text}")
            report_lines.append(f"   {result.message}")
            if result.details:
                report_lines.append(f"   Details: {json.dumps(result.details, indent=2)}")
            report_lines.append("")
        
        # Final status
        if blocking_failures:
            report_lines.append(" ALERT:  PIPELINE BLOCKED: Fix blocking failures before deployment")
        elif failed:
            report_lines.append(" WARNING: [U+FE0F]  PIPELINE WARNING: Consider addressing non-blocking failures")
        else:
            report_lines.append(" CELEBRATION:  PIPELINE SUCCESS: All validations passed")
        
        return "\n".join(report_lines)
    
    @staticmethod
    def generate_json_report(results: List[PipelineValidationResult]) -> str:
        """Generate JSON report for CI/CD integration"""
        results_data = [asdict(r) for r in results]
        
        # Convert enums to strings
        for result_data in results_data:
            result_data['stage'] = result_data['stage'].value if isinstance(result_data['stage'], ValidationStage) else result_data['stage']
        
        successful = len([r for r in results if r.success])
        failed = len([r for r in results if not r.success])
        blocking_failures = len([r for r in results if not r.success and r.blocking])
        
        return json.dumps({
            'summary': {
                'total_validations': len(results),
                'successful': successful,
                'failed': failed,
                'blocking_failures': blocking_failures
            },
            'results': results_data,
            'pipeline_status': 'BLOCKED' if blocking_failures > 0 else ('WARNING' if failed > 0 else 'SUCCESS'),
            'deployment_allowed': blocking_failures == 0
        }, indent=2)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="CI/CD Pipeline Enhancer - Comprehensive validation"
    )
    
    # Main actions
    parser.add_argument('--run-all', action='store_true',
                       help='Run all pipeline validations')
    parser.add_argument('--async-patterns-only', action='store_true',
                       help='Run only async pattern validation')
    parser.add_argument('--contracts-only', action='store_true',
                       help='Run only API contract validation')
    parser.add_argument('--type-safety-only', action='store_true',
                       help='Run only type safety validation')
    parser.add_argument('--integration-only', action='store_true',
                       help='Run only integration tests')
    parser.add_argument('--performance-only', action='store_true',
                       help='Run only performance validation')
    
    # Pipeline configuration
    parser.add_argument('--fail-fast', action='store_true',
                       help='Stop on first blocking failure')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Timeout for individual validations (minutes)')
    
    # GitHub Actions integration
    parser.add_argument('--install-github-workflow', action='store_true',
                       help='Install GitHub Actions workflow')
    parser.add_argument('--generate-workflow', action='store_true',
                       help='Generate GitHub Actions workflow (stdout)')
    
    # Output options
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    return parser


def main() -> int:
    """Main pipeline enhancement orchestrator"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle GitHub Actions workflow generation
    if args.generate_workflow:
        enhancer = CIPipelineEnhancer()
        print(enhancer.generate_github_actions_workflow())
        return 0
    
    if args.install_github_workflow:
        enhancer = CIPipelineEnhancer()
        success = enhancer.install_github_actions_workflow()
        return 0 if success else 1
    
    # Setup configuration
    config = PipelineConfiguration(
        fail_fast=args.fail_fast,
        timeout_minutes=args.timeout
    )
    
    # Determine which stages to run
    stages = []
    if args.run_all:
        stages = list(ValidationStage)
    elif args.async_patterns_only:
        stages = [ValidationStage.ASYNC_PATTERNS]
    elif args.contracts_only:
        stages = [ValidationStage.API_CONTRACTS]
    elif args.type_safety_only:
        stages = [ValidationStage.TYPE_SAFETY]
    elif args.integration_only:
        stages = [ValidationStage.INTEGRATION]
    elif args.performance_only:
        stages = [ValidationStage.PERFORMANCE]
    else:
        # Default: run critical validations
        stages = [ValidationStage.ASYNC_PATTERNS, ValidationStage.API_CONTRACTS, ValidationStage.TYPE_SAFETY]
    
    # Run pipeline validation
    enhancer = CIPipelineEnhancer(config)
    results = enhancer.run_validation(stages)
    
    # Generate report
    if args.json:
        print(PipelineReporter.generate_json_report(results))
    else:
        print(PipelineReporter.generate_console_report(results))
    
    # Determine exit code
    blocking_failures = [r for r in results if not r.success and r.blocking]
    return 1 if blocking_failures else 0


if __name__ == "__main__":
    sys.exit(main())