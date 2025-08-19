"""
Test Execution Engine - Core test execution logic for different test types

Business Value Justification (BVJ):
1. Segment: ALL customer segments - core testing infrastructure  
2. Business Goal: Ensure reliable test execution across all test types
3. Value Impact: Prevents test infrastructure failures that block development
4. Revenue Impact: Protects development velocity and release confidence

Architectural Compliance:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Single responsibility: Test execution coordination
- Modular design for different test types
"""

import time
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


def execute_test_suite(args, config: Dict, runner, real_llm_config: Optional[Dict], speed_opts: Optional[Dict], test_level: str) -> int:
    """Route test execution based on configuration and test level."""
    # Special handling for agent startup E2E tests
    if test_level == "agent-startup":
        from .agent_startup_handler import execute_agent_startup_tests as handler_execute
        return handler_execute(args, config, runner, real_llm_config, speed_opts)
    elif args.backend_only:
        return execute_backend_only_tests(config, runner, real_llm_config, speed_opts)
    elif args.frontend_only:
        return execute_frontend_only_tests(config, runner, speed_opts, test_level)
    else:
        return execute_full_test_suite(config, runner, real_llm_config, speed_opts, test_level)

def execute_backend_only_tests(config: Dict, runner, real_llm_config: Optional[Dict], speed_opts: Optional[Dict]) -> int:
    """Execute backend-only tests."""
    backend_exit, _ = runner.run_backend_tests(
        config['backend_args'], 
        config.get('timeout', 300),
        real_llm_config,
        speed_opts
    )
    runner.results["frontend"]["status"] = "skipped"
    return backend_exit

def execute_frontend_only_tests(config: Dict, runner, speed_opts: Optional[Dict], test_level: str) -> int:
    """Execute frontend-only tests."""
    frontend_exit, _ = runner.run_frontend_tests(
        config['frontend_args'],
        config.get('timeout', 300),
        speed_opts,
        test_level
    )
    runner.results["backend"]["status"] = "skipped"
    return frontend_exit

def execute_full_test_suite(config: Dict, runner, real_llm_config: Optional[Dict], speed_opts: Optional[Dict], test_level: str) -> int:
    """Execute full test suite (backend + frontend + E2E)."""
    if config.get('run_both', True):
        backend_exit, _ = runner.run_backend_tests(
            config['backend_args'],
            config.get('timeout', 300),
            real_llm_config,
            speed_opts
        )
        frontend_exit, _ = runner.run_frontend_tests(
            config['frontend_args'], 
            config.get('timeout', 300),
            speed_opts,
            test_level
        )
        exit_code = max(backend_exit, frontend_exit)
        if config.get('run_e2e', False):
            e2e_exit, _ = runner.run_e2e_tests([], config.get('timeout', 600))
            exit_code = max(exit_code, e2e_exit)
        return exit_code
    else:
        return execute_backend_only_tests(config, runner, real_llm_config, speed_opts)

def configure_real_llm_if_requested(args, level: str, config: Dict):
    """Configure real LLM testing if requested."""
    if not args.real_llm:
        return None
    if level == "smoke":
        print("[WARNING] Real LLM testing disabled for smoke tests (use unit or higher)")
        return None
    
    from .test_config import configure_real_llm
    real_llm_config = configure_real_llm(args.llm_model, args.llm_timeout, args.parallel)
    print_llm_configuration(args, config)
    return real_llm_config

def print_llm_configuration(args, config: Dict):
    """Print real LLM configuration details."""
    print(f"[INFO] Real LLM testing enabled")
    print(f"  - Model: {args.llm_model}")
    print(f"  - Timeout: {args.llm_timeout}s per call")
    print(f"  - Parallelism: {args.parallel}")
    adjusted_timeout = config.get('timeout', 300) * 3
    config['timeout'] = adjusted_timeout
    print(f"  - Adjusted test timeout: {adjusted_timeout}s")

def finalize_test_run(runner, level: str, config: Dict, output: str, exit_code: int) -> int:
    """Finalize test run with reporting and cleanup."""
    runner.results["overall"]["end_time"] = time.time()
    runner.results["overall"]["status"] = "passed" if exit_code == 0 else "failed"
    
    # Special reporting for agent startup tests
    if level == "agent-startup" and hasattr(runner.results, 'agent_performance'):
        from .agent_startup_handler import print_agent_performance_summary
        print_agent_performance_summary(runner.results['agent_performance'])
    
    generate_test_reports(runner, level, config, output, exit_code)
    runner.print_summary()
    return exit_code

def generate_test_reports(runner, level: str, config: Dict, output: str, exit_code: int):
    """Generate test reports in requested formats."""
    module = sys.modules.get('test_framework.test_runner')
    if not hasattr(module, '_no_report') or not module._no_report:
        runner.save_test_report(level, config, output, exit_code)
        save_additional_reports(runner, level, config, exit_code)
        generate_coverage_report()

def save_additional_reports(runner, level: str, config: Dict, exit_code: int):
    """Save additional report formats if requested."""
    args = sys.modules.get('test_framework.test_runner').__dict__.get('_current_args')
    if not args or not args.output:
        return
    
    if args.report_format == "json":
        save_json_report(runner, level, config, exit_code, args.output)
    elif args.report_format == "text":
        save_text_report(runner, level, config, exit_code, args.output)

def save_json_report(runner, level: str, config: Dict, exit_code: int, output_file: str):
    """Save JSON report to file."""
    json_report = runner.generate_json_report(level, config, exit_code)
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(json_report, f, indent=2)
    print(f"[REPORT] JSON report saved to: {output_file}")

def save_text_report(runner, level: str, config: Dict, exit_code: int, output_file: str):
    """Save text report to file."""
    text_report = runner.generate_text_report(level, config, exit_code)
    with open(output_file, "w", encoding='utf-8') as f:
        f.write(text_report)
    print(f"[REPORT] Text report saved to: {output_file}")

def generate_coverage_report():
    """Generate coverage report if requested."""
    args = sys.modules.get('test_framework.test_runner').__dict__.get('_current_args')
    if not args or not args.coverage_output:
        return
    
    try:
        PROJECT_ROOT = Path(__file__).parent.parent
        coverage_cmd = [sys.executable, "-m", "coverage", "xml", "-o", args.coverage_output]
        subprocess.run(coverage_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if Path(args.coverage_output).exists():
            print(f"[COVERAGE] Coverage report saved to: {args.coverage_output}")
        else:
            print(f"[WARNING] Coverage report generation failed - file not created")
    except Exception as e:
        print(f"[WARNING] Could not generate coverage report: {e}")
