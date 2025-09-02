from shared.isolated_environment import get_env
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

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional


def execute_test_suite(args, config: Dict, runner, real_llm_config: Optional[Dict], speed_opts: Optional[Dict], test_level: str) -> int:
    """Route test execution based on configuration and test level."""
    # Special handling for agent startup E2E tests
    if test_level == "agent-startup":
        from .agent_startup_handler import (
            execute_agent_startup_tests as handler_execute,
        )
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
    """Configure real LLM testing with comprehensive environment validation and setup."""
    if not args.real_llm:
        return None
    if level == "smoke":
        print("[WARNING] Real LLM testing disabled for smoke tests (use unit or higher)")
        return None
    
    print("[INFO] Configuring real LLM testing environment...")
    
    import asyncio
    import os

    from test_framework.archived.executors.real_llm_config import configure_real_llm_testing, get_real_llm_manager
    from test_framework.archived.executors.test_config import configure_real_llm
    from test_framework.archived.executors.test_environment_setup import TestEnvironmentValidator, get_test_orchestrator
    
    # Initialize environment validator
    validator = TestEnvironmentValidator()
    
    # Comprehensive environment validation
    try:
        print("[INFO] Validating test environment...")
        
        # Check database configuration
        database_url = get_env().get('TEST_DATABASE_URL') or get_env().get('DATABASE_URL', '')
        if not database_url:
            print("[ERROR] No database URL configured. Set TEST_DATABASE_URL or DATABASE_URL")
            return None
        
        # Run async validations
        async def validate_environment():
            return await asyncio.gather(
                validator.validate_database_connection(database_url),
                validator.validate_api_keys(True),
                return_exceptions=True
            )
        
        db_validation, api_validation = asyncio.run(validate_environment())
        
        # Handle validation results
        if isinstance(db_validation, Exception):
            print(f"[ERROR] Database validation failed: {db_validation}")
            return None
        if not db_validation:
            print("[ERROR] Database connection validation failed")
            return None
        
        if isinstance(api_validation, Exception):
            print(f"[ERROR] API key validation failed: {api_validation}")
            return None
        if not api_validation:
            print("[ERROR] Real LLM testing requires valid API keys")
            print("  Recommended: Set TEST_ANTHROPIC_API_KEY, TEST_OPENAI_API_KEY, or TEST_GOOGLE_API_KEY")
            print("  Fallback: Production keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY) will be used")
            return None
        
        # Seed data validation for real LLM tests
        required_datasets = get_datasets_for_llm_level(level)
        if required_datasets:
            seed_validation = validator.validate_seed_data_files(required_datasets)
            if not seed_validation:
                print(f"[ERROR] Required seed data validation failed for level '{level}'")
                return None
        
        print("[SUCCESS] Environment validation passed")
        
    except Exception as e:
        print(f"[ERROR] Environment validation failed: {e}")
        return None
    
    # Initialize real LLM configuration
    try:
        llm_config = configure_real_llm_testing()
        if not llm_config.enabled:
            print("[ERROR] Real LLM configuration initialization failed")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to initialize real LLM configuration: {e}")
        return None
    
    # Configure test runner real LLM settings
    real_llm_config = configure_real_llm(
        args.llm_model, 
        args.llm_timeout, 
        args.parallel, 
        test_level=level,
        use_dedicated_env=True
    )
    
    # Enhance configuration with validation results
    real_llm_config.update({
        'validation_passed': True,
        'required_datasets': required_datasets,
        'environment_isolation': True,
        'cost_budget': llm_config.cost_budget_per_run
    })
    
    print_llm_configuration(real_llm_config, config)
    print_dedicated_environment_info()
    
    return real_llm_config

def print_llm_configuration(real_llm_config: Dict, config: Dict):
    """Print comprehensive real LLM configuration details."""
    print(f"[INFO] Real LLM testing configuration:")
    print(f"  - Model: {real_llm_config['model']}")
    print(f"  - Timeout: {real_llm_config['timeout']}s per call")
    print(f"  - Parallelism: {real_llm_config['parallel']}")
    
    if real_llm_config.get('rate_limit_delay'):
        print(f"  - Rate limit delay: {real_llm_config['rate_limit_delay']}s between calls")
    
    if real_llm_config.get('cost_budget'):
        print(f"  - Cost budget: ${real_llm_config['cost_budget']:.2f} per test run")
    
    if real_llm_config.get('required_datasets'):
        datasets = ', '.join(real_llm_config['required_datasets'])
        print(f"  - Seed datasets: {datasets}")
    
    if real_llm_config.get('environment_isolation'):
        print(f"  - Environment isolation: enabled")
    
    # Adjust timeouts for real LLM testing
    timeout_multiplier = 4 if real_llm_config.get('parallel', 'auto') == '1' else 3
    adjusted_timeout = config.get('timeout', 300) * timeout_multiplier
    config['timeout'] = adjusted_timeout
    print(f"  - Test timeout (adjusted): {adjusted_timeout}s")
    
    print(f"[INFO] Ready for real LLM testing")


def print_dedicated_environment_info():
    """Print comprehensive dedicated test environment configuration details."""
    import os
    print(f"[INFO] Test environment configuration:")
    
    # Database configuration with enhanced details
    test_db = get_env().get('TEST_DATABASE_URL')
    prod_db = get_env().get('DATABASE_URL')
    
    if test_db:
        db_name = test_db.split('/')[-1] if '/' in test_db else 'unknown'
        print(f"  - Database: {db_name} (dedicated test DB)")
    elif prod_db:
        db_name = prod_db.split('/')[-1] if '/' in prod_db else 'unknown'
        print(f"  - Database: {db_name} (production DB - CAUTION)")
    else:
        print(f"  - Database: not configured")
    
    # Redis configuration
    test_redis = get_env().get('TEST_REDIS_URL')
    prod_redis = get_env().get('REDIS_URL')
    
    if test_redis:
        redis_db = test_redis.split('/')[-1] if '/' in test_redis else 'default'
        namespace = get_env().get('TEST_REDIS_NAMESPACE', 'test:')
        print(f"  - Redis: DB {redis_db} with namespace '{namespace}' (dedicated)")
    elif prod_redis:
        redis_db = prod_redis.split('/')[-1] if '/' in prod_redis else 'default'
        print(f"  - Redis: DB {redis_db} (production Redis - CAUTION)")
    else:
        print(f"  - Redis: not configured")
    
    # ClickHouse configuration  
    test_clickhouse = get_env().get('TEST_CLICKHOUSE_URL')
    prod_clickhouse = get_env().get('CLICKHOUSE_URL')
    
    if test_clickhouse:
        ch_db = test_clickhouse.split('/')[-1] if '/' in test_clickhouse else 'unknown'
        prefix = get_env().get('TEST_CLICKHOUSE_TABLES_PREFIX', 'test_')
        print(f"  - ClickHouse: {ch_db} with prefix '{prefix}' (dedicated)")
    elif prod_clickhouse:
        ch_db = prod_clickhouse.split('/')[-1] if '/' in prod_clickhouse else 'unknown'
        print(f"  - ClickHouse: {ch_db} (production ClickHouse - CAUTION)")
    else:
        print(f"  - ClickHouse: not configured")
    
    # API key configuration with isolation status
    test_keys = []
    prod_keys = []
    
    for provider in ['ANTHROPIC', 'GOOGLE', 'OPENAI']:
        test_key = get_env().get(f'TEST_{provider}_API_KEY')
        prod_key = get_env().get(f'{provider}_API_KEY')
        
        if test_key:
            test_keys.append(provider.lower())
        elif prod_key:
            prod_keys.append(provider.lower())
    
    if test_keys:
        print(f"  - API keys: {', '.join(test_keys)} (dedicated test keys)")
    if prod_keys:
        status = "(FALLBACK)" if test_keys else "(PRODUCTION KEYS - CAUTION)"
        print(f"  - API keys: {', '.join(prod_keys)} {status}")
    
    if not test_keys and not prod_keys:
        print(f"  - API keys: none configured")
    
    # Environment isolation status
    isolation = get_env().get('USE_TEST_ISOLATION', 'true')
    schema_isolation = get_env().get('TEST_SCHEMA_ISOLATION', 'true')
    
    print(f"  - Transaction isolation: {'enabled' if isolation.lower() == 'true' else 'disabled'}")
    print(f"  - Schema isolation: {'enabled' if schema_isolation.lower() == 'true' else 'disabled'}")
    
    # Environment safety assessment
    safety_score = calculate_environment_safety_score(test_db, test_redis, test_clickhouse, test_keys)
    print(f"  - Environment safety: {safety_score}")

def finalize_test_run(runner, level: str, config: Dict, output: str, exit_code: int) -> int:
    """Finalize test run with reporting and cleanup."""
    runner.results["overall"]["end_time"] = time.time()
    runner.results["overall"]["status"] = "passed" if exit_code == 0 else "failed"
    
    # Special reporting for agent startup tests
    if level == "agent-startup" and hasattr(runner.results, 'agent_performance'):
        from test_framework.archived.executors.agent_startup_handler import print_agent_performance_summary
        print_agent_performance_summary(runner.results['agent_performance'])
    
    generate_test_reports(runner, level, config, output, exit_code)
    runner.print_summary()
    return exit_code

def get_datasets_for_llm_level(test_level: str) -> List[str]:
    """Get required datasets for real LLM testing based on test level."""
    level_datasets = {
        'unit': ['basic_optimization'],
        'integration': ['basic_optimization', 'complex_workflows'],
        'agents': ['basic_optimization', 'complex_workflows'],
        'e2e': ['basic_optimization', 'complex_workflows', 'edge_cases'],
        'comprehensive': ['basic_optimization', 'complex_workflows', 'edge_cases'],
        'critical': ['basic_optimization'],
        'performance': ['basic_optimization']
    }
    return level_datasets.get(test_level, ['basic_optimization'])


def calculate_environment_safety_score(test_db: str, test_redis: str, test_clickhouse: str, test_keys: List[str]) -> str:
    """Calculate environment safety score for real LLM testing."""
    safety_factors = []
    
    # Database isolation
    if test_db:
        safety_factors.append("DB_ISOLATED")
    else:
        safety_factors.append("DB_SHARED")
    
    # Redis isolation
    if test_redis:
        safety_factors.append("REDIS_ISOLATED")
    else:
        safety_factors.append("REDIS_SHARED")
    
    # ClickHouse isolation
    if test_clickhouse:
        safety_factors.append("CH_ISOLATED")
    else:
        safety_factors.append("CH_SHARED")
    
    # API key isolation
    if test_keys:
        safety_factors.append("API_ISOLATED")
    else:
        safety_factors.append("API_SHARED")
    
    # Calculate safety score
    isolated_count = sum(1 for factor in safety_factors if "ISOLATED" in factor)
    total_factors = len(safety_factors)
    
    if isolated_count == total_factors:
        return "EXCELLENT (fully isolated)"
    elif isolated_count >= total_factors * 0.75:
        return "GOOD (mostly isolated)"
    elif isolated_count >= total_factors * 0.5:
        return "FAIR (partially isolated)"
    else:
        return "POOR (limited isolation)"


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
    if not args:
        return
    
    PROJECT_ROOT = Path(__file__).parent.parent
    
    # Generate XML coverage if requested
    if hasattr(args, 'coverage_output') and args.coverage_output:
        try:
            coverage_cmd = [sys.executable, "-m", "coverage", "xml", "-o", args.coverage_output]
            subprocess.run(coverage_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
            if Path(args.coverage_output).exists():
                print(f"[COVERAGE] XML report saved to: {args.coverage_output}")
            else:
                print(f"[WARNING] Coverage XML generation failed")
        except Exception as e:
            print(f"[WARNING] Could not generate XML coverage: {e}")
    
    # Generate HTML coverage if requested
    if hasattr(args, 'coverage_html') and args.coverage_html:
        try:
            html_dir = PROJECT_ROOT / "htmlcov"
            coverage_cmd = [sys.executable, "-m", "coverage", "html", "-d", str(html_dir)]
            subprocess.run(coverage_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
            if html_dir.exists():
                print(f"[COVERAGE] HTML report saved to: {html_dir}")
                print(f"  Open {html_dir / 'index.html'} in a browser to view")
            else:
                print(f"[WARNING] Coverage HTML generation failed")
        except Exception as e:
            print(f"[WARNING] Could not generate HTML coverage: {e}")
