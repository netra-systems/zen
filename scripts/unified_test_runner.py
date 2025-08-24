#!/usr/bin/env python
"""
NETRA APEX UNIFIED TEST RUNNER
==============================
Modern test runner with advanced categorization, progress tracking, and intelligent execution planning.

USAGE:
    python unified_test_runner.py                       # Run default categories
    python unified_test_runner.py --category unit       # Run specific category
    python unified_test_runner.py --help                # Show all options

CATEGORIES:
    CRITICAL: smoke, startup
    HIGH:     unit, security, database
    MEDIUM:   integration, api, websocket, agent
    LOW:      frontend, performance, e2e

EXAMPLES:
    python unified_test_runner.py --category unit
    python unified_test_runner.py --categories unit api
    python unified_test_runner.py --category performance --window-size 30
    python unified_test_runner.py --list-categories
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import timedelta

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Add parent directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test framework - using absolute imports from project root
from test_framework.runner import UnifiedTestRunner as FrameworkRunner
from test_framework.test_config import configure_dev_environment, configure_real_llm
from test_framework.test_discovery import TestDiscovery
from test_framework.test_validation import TestValidation

# Enhanced category system imports
from test_framework.category_system import CategorySystem, ExecutionPlan, CategoryPriority
from test_framework.progress_tracker import ProgressTracker, ProgressEvent
from test_framework.auto_splitter import TestSplitter, SplittingStrategy
from test_framework.fail_fast_strategies import FailFastStrategy, FailFastMode
from test_framework.config.category_config import CategoryConfigLoader

# Environment-aware testing imports
from test_framework.environment_markers import TestEnvironment, filter_tests_by_environment


class UnifiedTestRunner:
    """Modern test runner with category-based execution and progress tracking."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.test_framework_path = self.project_root / "test_framework"
        self.backend_path = self.project_root / "netra_backend"
        self.auth_path = self.project_root / "auth_service"
        self.frontend_path = self.project_root / "frontend"
        
        # Initialize category system components
        self.config_loader = CategoryConfigLoader(self.project_root)
        config = self.config_loader.load_config()
        
        self.category_system = self.config_loader.create_category_system(config)
        self.progress_tracker = None
        self.test_splitter = None
        self.fail_fast_strategy = None
        self.execution_plan = None
        
        # Test configurations
        self.test_configs = {
            "backend": {
                "path": self.backend_path,
                "test_dir": "tests",
                "config": "pytest.ini",
                "command": "pytest"
            },
            "auth": {
                "path": self.auth_path,
                "test_dir": "tests",
                "config": "pytest.ini",
                "command": "pytest"
            },
            "frontend": {
                "path": self.frontend_path,
                "test_dir": "__tests__",
                "config": "jest.config.cjs",
                "command": "npm test"
            }
        }
    
    def initialize_components(self, args: argparse.Namespace):
        """Initialize test execution components based on arguments."""
        # Initialize progress tracker
        if args.progress_mode:
            config = self.config_loader.load_config()
            self.progress_tracker = self.config_loader.create_progress_tracker(config)
        
        # Initialize test splitter
        if not args.disable_auto_split:
            self.test_splitter = TestSplitter(project_root=self.project_root)
            self.test_splitter.strategy = SplittingStrategy(args.splitting_strategy)
            self.target_window_duration = timedelta(minutes=args.window_size)
        
        # Initialize fail-fast strategy
        if args.fail_fast_mode:
            self.fail_fast_strategy = FailFastStrategy(
                project_root=self.project_root,
                mode=FailFastMode(args.fail_fast_mode)
            )
    
    def run(self, args: argparse.Namespace) -> int:
        """Main entry point for test execution."""
        # Initialize components
        self.initialize_components(args)
        
        # Configure environment
        self._configure_environment(args)
        
        # Determine categories to run
        categories_to_run = self._determine_categories_to_run(args)
        if not categories_to_run:
            print("No categories to run based on selection criteria")
            return 1
        
        # Handle resume functionality
        if args.resume_from:
            categories_to_run = self._handle_resume(categories_to_run, args.resume_from)
        
        # Create execution plan
        self.execution_plan = self.category_system.create_execution_plan(
            categories_to_run,
            max_parallel=args.workers
        )
        
        # Start progress tracking
        if self.progress_tracker:
            run_id = f"run_{int(time.time())}"
            self.progress_tracker.start_run(
                run_id=run_id,
                categories=categories_to_run,
                test_level="category",
                parallel_workers=args.workers,
                fail_fast=args.fast_fail,
                real_llm=args.real_llm,
                environment=args.env
            )
        
        # Show execution plan
        self._show_execution_plan(self.execution_plan, args)
        
        # Execute categories by phase
        results = self._execute_categories_by_phases(self.execution_plan, args)
        
        # Complete progress tracking
        if self.progress_tracker:
            success = all(r["success"] for r in results.values())
            self.progress_tracker.complete_run(success)
        
        # Generate report
        self._generate_report(results, args)
        
        return 0 if all(r["success"] for r in results.values()) else 1
    
    def _configure_environment(self, args: argparse.Namespace):
        """Configure test environment based on arguments."""
        # Load test environment secrets first to prevent validation errors
        self._load_test_environment_secrets()
        
        if args.env == "dev" or args.real_services:
            configure_dev_environment()
            # Enable real services for frontend tests
            if args.real_services:
                os.environ['USE_REAL_SERVICES'] = 'true'
                os.environ['BACKEND_URL'] = os.getenv('BACKEND_URL', 'http://localhost:8000')
                os.environ['AUTH_SERVICE_URL'] = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8081')
                os.environ['WEBSOCKET_URL'] = os.getenv('WEBSOCKET_URL', 'ws://localhost:8000')
        
        if args.real_llm:
            configure_real_llm(
                model="gemini-2.5-flash",
                timeout=60,
                parallel="auto",
                test_level="category",
                use_dedicated_env=True
            )
        
        # Set environment variables
        os.environ["TEST_ENV"] = args.env
        
        if args.no_coverage:
            os.environ["COVERAGE_ENABLED"] = "false"
    
    def _load_test_environment_secrets(self):
        """Load test environment secrets to prevent validation errors during testing."""
        # Set essential test environment variables
        test_env_vars = {
            'ENVIRONMENT': 'testing',
            'TESTING': '1',
            'GOOGLE_CLIENT_ID': 'test-google-client-id-for-integration-testing',
            'GOOGLE_CLIENT_SECRET': 'test-google-client-secret-for-integration-testing',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-for-integration-testing-must-be-32-chars-minimum',
            'SERVICE_SECRET': 'test-service-secret-for-cross-service-auth-32-chars-minimum-length',
            'FERNET_KEY': 'iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=',
            'CLICKHOUSE_DEFAULT_PASSWORD': 'test-clickhouse-password-for-integration-testing'
        }
        
        # Only set if not already present (don't override existing values)
        for key, value in test_env_vars.items():
            if key not in os.environ:
                os.environ[key] = value
        
        # Try to load .env.test file if it exists
        test_env_file = self.project_root / ".env.test"
        if test_env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(test_env_file, override=False)
            except ImportError:
                # dotenv not available, use manual loading
                pass
            except Exception as e:
                print(f"Warning: Could not load .env.test file: {e}")
    
    def _determine_categories_to_run(self, args: argparse.Namespace) -> List[str]:
        """Determine which categories to run based on arguments."""
        categories = []
        
        # Handle specific category selection
        if args.category:
            categories.append(args.category)
        
        if args.categories:
            categories.extend(args.categories)
        
        # Default to common categories if none specified
        if not categories:
            categories = ["unit", "integration", "api"]
        
        # Filter categories that exist in the system
        valid_categories = [cat for cat in categories if cat in self.category_system.categories]
        if valid_categories != categories:
            missing = set(categories) - set(valid_categories)
            if missing:
                print(f"Warning: Categories not found: {missing}")
        
        return valid_categories
    
    def _handle_resume(self, categories: List[str], resume_from: str) -> List[str]:
        """Handle resume functionality by skipping already completed categories."""
        if resume_from not in categories:
            print(f"Warning: Resume category '{resume_from}' not in execution list")
            return categories
        
        resume_index = categories.index(resume_from)
        return categories[resume_index:]
    
    def _show_execution_plan(self, execution_plan: ExecutionPlan, args: argparse.Namespace):
        """Display the execution plan to the user."""
        if not execution_plan or not execution_plan.phases:
            return
        
        print(f"\n{'='*60}")
        print("EXECUTION PLAN")
        print(f"{'='*60}")
        print(f"Total Categories: {len(execution_plan.execution_order)}")
        print(f"Execution Phases: {len(execution_plan.phases)}")
        print(f"Estimated Duration: {execution_plan.total_estimated_duration}")
        
        for phase_num, phase_categories in enumerate(execution_plan.phases):
            print(f"\nPhase {phase_num + 1}: {len(phase_categories)} categories")
            for category_name in phase_categories:
                category = self.category_system.get_category(category_name)
                if category:
                    duration = category.estimated_duration
                    priority = category.priority.name
                    print(f"  - {category_name} ({priority}, ~{duration})")
        
        print(f"\n{'='*60}\n")
    
    def _execute_categories_by_phases(self, execution_plan: ExecutionPlan, args: argparse.Namespace) -> Dict:
        """Execute categories according to the execution plan."""
        results = {}
        
        for phase_num, phase_categories in enumerate(execution_plan.phases):
            print(f"\n{'='*40}")
            print(f"PHASE {phase_num + 1}: {len(phase_categories)} categories")
            print(f"{'='*40}")
            
            # Execute categories in this phase
            phase_results = self._execute_phase_categories(phase_categories, phase_num, args)
            results.update(phase_results)
            
            # Check if we should stop due to fail-fast
            if self.fail_fast_strategy:
                failed_categories = [cat for cat, result in phase_results.items() if not result["success"]]
                if failed_categories:
                    for failed_cat in failed_categories:
                        # Record the failure
                        self.fail_fast_strategy.record_failure(
                            test_name=f"{failed_cat}_tests",
                            category=failed_cat,
                            error_message="Category failed",
                            error_type="CategoryFailure"
                        )
                    
                    should_stop, decision = self.fail_fast_strategy.should_fail_fast(
                        current_stats=self.progress_tracker.get_current_progress() if self.progress_tracker else None
                    )
                    if should_stop and decision:
                        print(f"\nStopping execution: {decision.reason}")
                        # Mark remaining categories as skipped
                        for remaining_phase in execution_plan.phases[phase_num + 1:]:
                            for category_name in remaining_phase:
                                results[category_name] = {
                                    "success": False,
                                    "duration": 0,
                                    "output": "",
                                    "errors": f"Skipped: {decision.reason}",
                                    "skipped": True
                                }
                        break
        
        return results
    
    def _execute_phase_categories(self, category_names: List[str], phase_num: int, args: argparse.Namespace) -> Dict:
        """Execute categories in a single phase."""
        results = {}
        
        for category_name in category_names:
            print(f"\nExecuting category: {category_name}")
            
            # Start category tracking
            if self.progress_tracker:
                self.progress_tracker.start_category(category_name, phase=phase_num)
            
            # Execute the category
            result = self._execute_single_category(category_name, args)
            results[category_name] = result
            
            # Update progress tracking
            if self.progress_tracker:
                test_counts = self._extract_test_counts_from_result(result)
                self.progress_tracker.complete_category(
                    category_name,
                    success=result["success"],
                    test_counts=test_counts
                )
            
            # Check for early termination
            if args.fast_fail and not result["success"]:
                print(f"Fast-fail triggered by category: {category_name}")
                break
        
        return results
    
    def _execute_single_category(self, category_name: str, args: argparse.Namespace) -> Dict:
        """Execute a single category."""
        category = self.category_system.get_category(category_name)
        if not category:
            return {
                "success": False,
                "duration": 0,
                "output": "",
                "errors": f"Category '{category_name}' not found"
            }
        
        # Map category to services
        category_services = self._get_services_for_category(category_name)
        
        if len(category_services) > 1:
            # Run multiple services
            all_results = {}
            for service in category_services:
                service_result = self._run_service_tests_for_category(service, category_name, args)
                all_results[service] = service_result
            
            # Combine results
            overall_success = all(r["success"] for r in all_results.values())
            combined_output = "\n".join(r.get("output", "") for r in all_results.values())
            combined_errors = "\n".join(r.get("errors", "") for r in all_results.values())
            total_duration = sum(r.get("duration", 0) for r in all_results.values())
            
            return {
                "success": overall_success,
                "duration": total_duration,
                "output": combined_output,
                "errors": combined_errors,
                "service_results": all_results
            }
        else:
            # Run single service
            return self._run_service_tests_for_category(category_services[0], category_name, args)
    
    def _get_services_for_category(self, category_name: str) -> List[str]:
        """Determine which services to run for a category."""
        category_service_mapping = {
            "smoke": ["backend", "auth"],
            "unit": ["backend", "auth"],
            "integration": ["backend"],
            "api": ["backend"],
            "database": ["backend"],
            "websocket": ["backend"],
            "agent": ["backend"],
            "security": ["auth"],
            "frontend": ["frontend"],
            "e2e": ["backend", "auth", "frontend"],
            "performance": ["backend", "auth"]
        }
        
        return category_service_mapping.get(category_name, ["backend"])
    
    def _run_service_tests_for_category(self, service: str, category_name: str, args: argparse.Namespace) -> Dict:
        """Run tests for a specific service and category combination."""
        config = self.test_configs.get(service)
        if not config:
            return {
                "success": False,
                "duration": 0,
                "output": "",
                "errors": f"Service '{service}' not configured"
            }
        
        # Set environment for test execution
        self._set_test_environment(args)
        
        # Build test command
        if service == "frontend":
            cmd = self._build_frontend_command(category_name, args)
        else:
            cmd = self._build_pytest_command(service, category_name, args)
        
        # Debug output
        if args.verbose:
            print(f"[DEBUG] Running command for {service}: {cmd}")
        
        # Execute tests
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=config["path"],
                capture_output=True,
                text=True,
                shell=True,
                encoding='utf-8',
                errors='replace'
            )
            success = result.returncode == 0
        except Exception as e:
            print(f"[ERROR] Failed to run {service} tests: {e}")
            success = False
            result = None
        
        duration = time.time() - start_time
        
        return {
            "success": success,
            "duration": duration,
            "output": result.stdout if result else "",
            "errors": result.stderr if result else ""
        }
    
    def _build_pytest_command(self, service: str, category_name: str, args: argparse.Namespace) -> str:
        """Build pytest command for backend/auth services."""
        config = self.test_configs[service]
        
        cmd_parts = ["pytest"]
        
        # Add test directory
        cmd_parts.append(str(config["test_dir"]))
        
        # Add category-specific markers
        category_markers = {
            "smoke": ["-m", '"smoke"'],
            "unit": ["-m", '"not integration and not e2e"'],
            "integration": ["-m", '"integration"'],
            "api": ["-k", '"api"'],
            "database": ["-k", '"database or db"'],
            "websocket": ["-k", '"websocket or ws"'],
            "agent": ["-k", '"agent"'],
            "security": ["-k", '"auth or security"'],
            "e2e": ["-m", '"e2e"'],
            "performance": ["-m", '"performance"']
        }
        
        if category_name in category_markers:
            cmd_parts.extend(category_markers[category_name])
        
        # Add environment-specific filtering
        if hasattr(args, 'env') and args.env:
            # Add environment marker to filter tests - use pytest markers, not -k expressions
            env_marker = f'env_{args.env}'
            cmd_parts.extend(["-m", env_marker])
        
        # Add coverage options
        if not args.no_coverage:
            cmd_parts.extend([
                "--cov=.",
                "--cov-report=html",
                "--cov-report=term-missing"
            ])
        
        # Add parallelization
        if args.parallel:
            cmd_parts.extend(["-n", str(args.workers)])
        
        # Add verbosity
        if args.verbose:
            cmd_parts.append("-vv")
        
        # Add fast fail
        if args.fast_fail:
            cmd_parts.append("-x")
        
        # Add specific test pattern
        if args.pattern:
            cmd_parts.extend(["-k", f'"{args.pattern}"'])
        
        return " ".join(cmd_parts)
    
    def _build_frontend_command(self, category_name: str, args: argparse.Namespace) -> str:
        """Build test command for frontend."""
        # Determine which Jest setup to use
        if args.real_services or args.env in ['dev', 'staging']:
            setup_file = "jest.setup.real.js"
            # Set environment variables for real service testing
            os.environ['USE_REAL_SERVICES'] = 'true'
            if args.env == 'dev':
                os.environ['USE_DOCKER_SERVICES'] = 'true'
            if args.real_llm:
                os.environ['USE_REAL_LLM'] = 'true'
        else:
            setup_file = "jest.setup.js"
            os.environ.pop('USE_REAL_SERVICES', None)
            os.environ.pop('USE_DOCKER_SERVICES', None)
            os.environ.pop('USE_REAL_LLM', None)
        
        category_commands = {
            "unit": f"npm test -- --setupFilesAfterEnv='<rootDir>/{setup_file}' --testPathPattern=unit",
            "integration": f"npm test -- --setupFilesAfterEnv='<rootDir>/{setup_file}' --testPathPattern=integration",
            "e2e": f"npm test -- --setupFilesAfterEnv='<rootDir>/{setup_file}' --testPathPattern=e2e",
            "frontend": f"npm test -- --setupFilesAfterEnv='<rootDir>/{setup_file}'"
        }
        
        base_command = category_commands.get(category_name, f"npm test -- --setupFilesAfterEnv='<rootDir>/{setup_file}'")
        
        # Add additional flags
        if args.no_coverage:
            base_command += " --coverage=false"
        if args.fast_fail:
            base_command += " --bail"
        if args.verbose:
            base_command += " --verbose"
        if hasattr(args, 'max_workers') and args.max_workers:
            base_command += f" --maxWorkers={args.max_workers}"
        
        return base_command
    
    def _set_test_environment(self, args: argparse.Namespace):
        """Set environment variables for test execution."""
        # Set TEST_ENV for environment-aware testing
        if hasattr(args, 'env'):
            os.environ['TEST_ENV'] = args.env
        
        # Set production protection
        if hasattr(args, 'allow_prod') and args.allow_prod:
            os.environ['ALLOW_PROD_TESTS'] = 'true'
        else:
            os.environ.pop('ALLOW_PROD_TESTS', None)
        
        # Map env to existing env var patterns
        env_mapping = {
            'test': 'local',
            'dev': 'dev',
            'staging': 'staging',
            'prod': 'prod'
        }
        
        if hasattr(args, 'env'):
            mapped_env = env_mapping.get(args.env, args.env)
            os.environ['ENVIRONMENT'] = mapped_env
            
            # Set specific flags based on environment
            if args.env == 'test':
                os.environ['TEST_MODE'] = 'mock'
                os.environ['USE_TEST_DATABASE'] = 'true'
            elif args.env in ['dev', 'staging', 'prod']:
                os.environ['TEST_MODE'] = 'real'
                os.environ.pop('USE_TEST_DATABASE', None)
    
    def _extract_test_counts_from_result(self, result: Dict) -> Dict[str, int]:
        """Extract test counts from execution result."""
        # Parse pytest output for actual counts
        output = result.get("output", "")
        test_counts = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0
        }
        
        # Simple parsing - could be enhanced
        if "passed" in output:
            import re
            passed_match = re.search(r'(\d+) passed', output)
            if passed_match:
                test_counts["passed"] = int(passed_match.group(1))
        
        if "failed" in output:
            import re
            failed_match = re.search(r'(\d+) failed', output)
            if failed_match:
                test_counts["failed"] = int(failed_match.group(1))
        
        test_counts["total"] = test_counts["passed"] + test_counts["failed"]
        
        return test_counts
    
    def _safe_print_unicode(self, text):
        """Safely print text with Unicode characters, falling back to ASCII on encoding errors."""
        try:
            print(text)
        except UnicodeEncodeError:
            # Replace Unicode symbols with ASCII equivalents for Windows console compatibility
            ascii_text = text.replace("✅", "[PASS]").replace("❌", "[FAIL]").replace("⏭️", "[SKIP]")
            print(ascii_text)

    def _generate_report(self, results: Dict, args: argparse.Namespace):
        """Generate test execution report."""
        report_dir = self.project_root / "test_reports"
        report_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Build report data
        report_data = {
            "timestamp": timestamp,
            "environment": args.env,
            "categories": results,
            "overall_success": all(r["success"] for r in results.values()),
            "total_duration": sum(r["duration"] for r in results.values()),
            "execution_plan": self.execution_plan.to_dict() if hasattr(self.execution_plan, 'to_dict') else None,
            "category_statistics": self.category_system.get_category_statistics()
        }
        
        # Add progress tracking data
        if self.progress_tracker:
            progress_data = self.progress_tracker.get_current_progress()
            if progress_data:
                report_data["progress_tracking"] = progress_data
        
        # Save JSON report
        json_report = report_dir / f"test_report_{timestamp}.json"
        with open(json_report, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Print summary
        print(f"\n{'='*60}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*60}")
        print(f"Environment: {args.env}")
        print(f"Total Duration: {report_data['total_duration']:.2f}s")
        print(f"Categories Executed: {len(results)}")
        
        print(f"\nCategory Results:")
        for category_name, result in results.items():
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            if result.get("skipped"):
                status = "⏭️ SKIPPED"
            self._safe_print_unicode(f"  {category_name:15} {status:15} ({result['duration']:.2f}s)")
        
        overall_status = "✅ PASSED" if report_data['overall_success'] else "❌ FAILED"
        self._safe_print_unicode(f"\nOverall: {overall_status}")
        print(f"Report: {json_report}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for Netra Apex Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Category selection
    parser.add_argument(
        "--category",
        help="Run specific category (e.g., 'unit', 'integration', 'api')"
    )
    
    parser.add_argument(
        "--categories",
        nargs='+',
        help="Run multiple categories (e.g., '--categories unit integration api')"
    )
    
    # Environment configuration
    parser.add_argument(
        "--env",
        choices=["test", "dev", "staging", "prod"],
        default="test",
        help="Environment to test against (default: test)"
    )
    
    parser.add_argument(
        "--exclude-env",
        choices=["test", "dev", "staging", "prod"],
        help="Exclude tests for specific environment"
    )
    
    parser.add_argument(
        "--allow-prod",
        action="store_true",
        help="Allow production tests to run (requires explicit flag)"
    )
    
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Use real LLM instead of mocks"
    )
    
    parser.add_argument(
        "--real-services",
        action="store_true",
        help="Use real backend services (Docker or local) for frontend tests"
    )
    
    parser.add_argument(
        "--max-workers",
        type=int,
        help="Maximum number of worker processes for Jest (frontend tests)"
    )
    
    # Coverage options
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    # Execution options
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    
    parser.add_argument(
        "--fast-fail",
        action="store_true",
        help="Stop on first test failure"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--pattern",
        help="Run tests matching pattern"
    )
    
    # Enhanced features
    parser.add_argument(
        "--window-size",
        type=int,
        default=15,
        help="Auto-split window size in minutes (default: 15)"
    )
    
    parser.add_argument(
        "--fail-fast-mode",
        choices=["disabled", "first_failure", "category_failure", "critical_failure", 
                "threshold_based", "smart_adaptive", "dependency_aware"],
        default="category_failure",
        help="Fail-fast strategy mode (default: category_failure)"
    )
    
    parser.add_argument(
        "--progress-mode",
        choices=["simple", "rich", "json"],
        default="simple",
        help="Progress display mode (default: simple)"
    )
    
    parser.add_argument(
        "--resume-from",
        help="Resume execution from specific category"
    )
    
    parser.add_argument(
        "--disable-auto-split",
        action="store_true",
        help="Disable automatic test splitting"
    )
    
    parser.add_argument(
        "--splitting-strategy",
        choices=["time_based", "count_based", "category_based", 
                "complexity_based", "dependency_aware", "hybrid"],
        default="hybrid",
        help="Test splitting strategy (default: hybrid)"
    )
    
    # Discovery options
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available categories and their configuration"
    )
    
    parser.add_argument(
        "--show-category-stats",
        action="store_true",
        help="Show historical category statistics"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate test structure and configuration"
    )
    
    args = parser.parse_args()
    
    # Handle special operations
    if args.list_categories:
        config_loader = CategoryConfigLoader(PROJECT_ROOT)
        category_system = config_loader.create_category_system()
        
        print(f"\n{'='*60}")
        print("AVAILABLE TEST CATEGORIES")
        print(f"{'='*60}")
        
        for priority in CategoryPriority:
            categories = category_system.get_categories_by_priority(priority)
            if categories:
                print(f"\n{priority.name} Priority:")
                for category in sorted(categories, key=lambda x: x.name):
                    print(f"  {category.name:15} - {category.description}")
                    if category.dependencies:
                        print(f"                    Dependencies: {', '.join(category.dependencies)}")
                    if category.conflicts:
                        print(f"                    Conflicts: {', '.join(category.conflicts)}")
                    print(f"                    Est. Duration: {category.estimated_duration}")
        
        print(f"\nTotal Categories: {len(category_system.categories)}")
        return 0
    
    if args.show_category_stats:
        config_loader = CategoryConfigLoader(PROJECT_ROOT)
        category_system = config_loader.create_category_system()
        stats = category_system.get_category_statistics()
        
        print(f"\n{'='*60}")
        print("CATEGORY STATISTICS")
        print(f"{'='*60}")
        print(f"Total Categories: {stats['total_categories']}")
        print(f"Parallel Safe: {stats['parallel_safe']}")
        print(f"Require Real Services: {stats['requires_real_services']}")
        print(f"Require Real LLM: {stats['requires_real_llm']}")
        print(f"Memory Intensive: {stats['memory_intensive']}")
        print(f"CPU Intensive: {stats['cpu_intensive']}")
        print(f"Database Dependent: {stats['database_dependent']}")
        print(f"Average Duration: {stats['average_estimated_duration']}")
        print(f"Categories with History: {stats['categories_with_history']}")
        print(f"Average Success Rate: {stats['average_success_rate']:.2%}")
        
        print(f"\nBy Priority:")
        for priority, count in stats['by_priority'].items():
            print(f"  {priority:10}: {count}")
        
        print(f"\nBy Type:")
        for cat_type, count in stats['by_type'].items():
            print(f"  {cat_type:12}: {count}")
        
        return 0
    
    if args.validate:
        validator = TestValidation(PROJECT_ROOT)
        issues = validator.validate_all()
        if issues:
            print("Validation Issues Found:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        print("All tests validated successfully")
        return 0
    
    # Run tests
    runner = UnifiedTestRunner()
    return runner.run(args)


if __name__ == "__main__":
    sys.exit(main())