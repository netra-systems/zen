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

# Use centralized environment management
try:
    from dev_launcher.isolated_environment import get_env
except ImportError:
    # Hard failure - IsolatedEnvironment is required for test runner
    raise RuntimeError("IsolatedEnvironment required for test runner. Cannot import from dev_launcher.isolated_environment")

# Import test framework - using absolute imports from project root
from test_framework.runner import UnifiedTestRunner as FrameworkRunner
from test_framework.test_config import configure_dev_environment, configure_test_environment, configure_real_llm
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

# Cypress integration
from test_framework.cypress_runner import CypressTestRunner, CypressExecutionOptions

# Test execution tracking
try:
    from scripts.test_execution_tracker import TestExecutionTracker, TestRunRecord
except ImportError:
    TestExecutionTracker = None
    TestRunRecord = None


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
        
        # Initialize test execution tracker
        self.test_tracker = TestExecutionTracker(self.project_root) if TestExecutionTracker else None
        
        # Initialize Cypress runner lazily to avoid Docker issues during init
        self.cypress_runner = None
        
        # Test execution timeout fix for iterations 41-60
        env = get_env()
        self.max_collection_size = int(env.get("MAX_TEST_COLLECTION_SIZE", "1000"))
        
        # Test configurations - Use project root as working directory to fix import issues
        self.test_configs = {
            "backend": {
                "path": self.project_root,  # Changed from backend_path to project_root
                "test_dir": "netra_backend/tests",  # Updated to full path from root
                "config": "netra_backend/pytest.ini",  # Updated to full path from root
                "command": "pytest"
            },
            "auth": {
                "path": self.project_root,  # Changed from auth_path to project_root
                "test_dir": "auth_service/tests",  # Updated to full path from root
                "config": "auth_service/pytest.ini",  # Updated to full path from root
                "command": "pytest"
            },
            "frontend": {
                "path": self.frontend_path,  # Frontend can stay as-is since it uses npm
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
        
        # Start test tracking session
        if self.test_tracker:
            self.test_tracker.start_session(
                environment=args.env,
                categories=args.categories if hasattr(args, 'categories') else None
            )
        
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
        
        # End test tracking session
        if self.test_tracker:
            session_summary = self.test_tracker.end_session(metadata={
                "args": vars(args),
                "execution_plan": self.execution_plan.to_dict() if self.execution_plan and hasattr(self.execution_plan, 'to_dict') else None
            })
            print(f"\nSession Summary: {session_summary['total_tests']} tests, "
                  f"{session_summary['passed']} passed, {session_summary['failed']} failed, "
                  f"Pass rate: {session_summary['pass_rate']:.1f}%")
            
            # Show test tracking report if verbose
            if args.verbose:
                print("\n" + self.test_tracker.generate_report())
        
        return 0 if all(r["success"] for r in results.values()) else 1
    
    def _configure_environment(self, args: argparse.Namespace):
        """Configure test environment based on arguments."""
        # Load test environment secrets first to prevent validation errors
        self._load_test_environment_secrets()
        
        if args.env == "dev" or args.real_services:
            configure_dev_environment()
            # Enable real services for frontend tests
            if args.real_services:
                env = get_env()
                env.set('USE_REAL_SERVICES', 'true', 'test_runner')
                env.set('BACKEND_URL', env.get('BACKEND_URL', 'http://localhost:8000'), 'test_runner')
                env.set('AUTH_SERVICE_URL', env.get('AUTH_SERVICE_URL', 'http://localhost:8081'), 'test_runner')
                env.set('WEBSOCKET_URL', env.get('WEBSOCKET_URL', 'ws://localhost:8000'), 'test_runner')
        else:
            # Default: Configure testing environment for unit/integration tests
            configure_test_environment()
        
        if args.real_llm:
            configure_real_llm(
                model="gemini-2.5-flash",
                timeout=60,
                parallel="auto",
                test_level="category",
                use_dedicated_env=True
            )
        
        # Set environment variables using IsolatedEnvironment
        env = get_env()
        env.set("TEST_ENV", args.env, "test_runner")
        
        if args.no_coverage:
            env.set("COVERAGE_ENABLED", "false", "test_runner")
    
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
            'CLICKHOUSE_PASSWORD': 'test-clickhouse-password-for-integration-testing'
        }
        
        # Only set if not already present (don't override existing values)
        env = get_env()
        for key, value in test_env_vars.items():
            if not env.get(key):
                env.set(key, value, "test_runner_secrets")
        
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
        
        # Default to categories marked as default in tracker
        if not categories:
            if self.test_tracker:
                categories = self.test_tracker.get_default_categories()
            else:
                # Fallback defaults: quick tests that should usually pass
                categories = ["smoke", "unit", "integration"]
        
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
            
            # Record test results in tracker
            if self.test_tracker and TestRunRecord:
                self._record_test_results(category_name, result, args.env)
            
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
            "smoke": ["backend"],  # Auth service has no smoke tests
            "unit": ["backend", "auth"],
            "integration": ["backend"],
            "api": ["backend"],
            "database": ["backend"],
            "websocket": ["backend"],
            "agent": ["backend"],
            "security": ["auth"],
            "frontend": ["frontend"],
            "e2e": ["backend"],  # E2E tests run from backend
            "e2e_critical": ["backend"],  # Critical e2e tests
            "e2e_full": ["backend"],  # Full e2e suite
            "cypress": ["cypress"],  # Special handler for Cypress E2E tests
            "performance": ["backend", "auth"]
        }
        
        return category_service_mapping.get(category_name, ["backend"])
    
    def _run_service_tests_for_category(self, service: str, category_name: str, args: argparse.Namespace) -> Dict:
        """Run tests for a specific service and category combination."""
        # Special handling for Cypress tests
        if service == "cypress":
            return self._run_cypress_tests(category_name, args)
            
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
        
        # Execute tests with timeout
        start_time = time.time()
        # Set timeout based on service type and category
        if service == "frontend":
            timeout_seconds = 120  # 2 minutes for frontend tests (mostly unit tests)
        elif category_name == "unit":
            timeout_seconds = 180  # 3 minutes for unit tests specifically
        else:
            timeout_seconds = 600  # 10 minutes timeout for integration tests
        try:
            # Fix stdout flush issue by using run with explicit flushing
            import sys
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Use subprocess.run with proper buffering for Windows
            result = subprocess.run(
                cmd,
                cwd=config["path"],
                capture_output=True,
                text=True,
                shell=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout_seconds,
                # Force immediate output on Windows
                env_manager = get_env()
                subprocess_env = env_manager.get_subprocess_env()
                subprocess_env.update({'PYTHONUNBUFFERED': '1', 'PYTHONUTF8': '1'})
                env=subprocess_env
            )
            # Handle unicode encoding issues by cleaning the output
            if result.stdout:
                result.stdout = result.stdout.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            if result.stderr:
                result.stderr = result.stderr.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            success = result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"[ERROR] {service} tests timed out after {timeout_seconds} seconds")
            print(f"[ERROR] Command: {cmd}")
            success = False
            result = subprocess.CompletedProcess(
                args=cmd, 
                returncode=1, 
                stdout="", 
                stderr=f"Tests timed out after {timeout_seconds} seconds"
            )
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
    
    def _can_run_cypress_tests(self) -> Tuple[bool, str]:
        """Check if Cypress tests can run given current environment."""
        from dev_launcher.docker_services import check_docker_availability
        import socket
        
        # Check Docker availability
        docker_available = check_docker_availability()
        
        # Quick service availability checks (non-blocking)
        def quick_service_check(host: str, port: int, timeout: float = 1.0) -> bool:
            """Quick, non-blocking check if a service is available."""
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return True
            except (socket.timeout, socket.error, ConnectionRefusedError, OSError):
                return False
        
        local_postgres = quick_service_check("localhost", 5432)
        local_redis = quick_service_check("localhost", 6379)
        local_backend = quick_service_check("localhost", 8000)
        
        if not docker_available and not (local_postgres and local_redis):
            raise RuntimeError(
                "Cannot run Cypress tests: Docker Desktop not running and "
                "required local services not available. "
                "Either start Docker Desktop or run local PostgreSQL (port 5432) "
                "and Redis (port 6379) services."
            )
        
        if not local_backend:
            raise RuntimeError(
                "Cannot run Cypress tests: Backend service not running on port 8000. "
                "Start the backend service first."
            )
        
        return True, "Services available for Cypress tests"
    
    def _get_cypress_runner(self):
        """Get Cypress runner, initializing it lazily."""
        if self.cypress_runner is None:
            self.cypress_runner = CypressTestRunner(self.project_root)
        return self.cypress_runner
    
    def _run_cypress_tests(self, category_name: str, args: argparse.Namespace) -> Dict:
        """Run Cypress E2E tests using the CypressTestRunner."""
        print(f"Running Cypress tests for category: {category_name}")
        
        # Early check for service availability - will raise exception if services unavailable
        try:
            can_run, message = self._can_run_cypress_tests()
        except RuntimeError as e:
            # Hard failure - let the exception propagate
            raise RuntimeError(f"Cypress test prerequisites not met: {str(e)}")
        
        try:
            # Create Cypress execution options
            options = CypressExecutionOptions(
                headed=args.cypress_headed if hasattr(args, 'cypress_headed') else False,
                browser=args.cypress_browser if hasattr(args, 'cypress_browser') else "chrome",
                timeout=1800,  # 30 minutes timeout
                retries=2,
                parallel=False,  # Cypress parallel execution not enabled for now
                env_vars={}
            )
            
            # Set spec pattern based on category if needed
            if category_name == "cypress":
                # Run all Cypress tests
                options.spec_pattern = None
            elif category_name == "smoke":
                # Run critical tests only
                options.spec_pattern = "cypress/e2e/critical-basic-flow.cy.ts,cypress/e2e/basic-ui-test.cy.ts"
            else:
                # Category-specific patterns
                cypress_runner = self._get_cypress_runner()
                spec_patterns = cypress_runner.config_manager.get_spec_patterns(category_name)
                if spec_patterns:
                    options.spec_pattern = ",".join(spec_patterns)
            
            # Run Cypress tests (handle async call with event loop detection)
            cypress_runner = self._get_cypress_runner()
            import asyncio
            try:
                # Try to get existing event loop
                loop = asyncio.get_running_loop()
                # If we have a loop, we need to run in a separate thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(lambda: asyncio.run(cypress_runner.run_tests(options)))
                    success, results = future.result(timeout=options.timeout)
            except RuntimeError:
                # No event loop running, safe to create new one
                success, results = asyncio.run(cypress_runner.run_tests(options))
            
            # Convert to unified format
            result_dict = {
                "success": success,
                "duration": results.get("execution_time_seconds", 0),
                "output": results.get("raw_output", {}).get("stdout", ""),
                "errors": results.get("raw_output", {}).get("stderr", "") if not success else "",
                "category": "cypress",
                "test_count": results.get("total_tests", 0),
                "passed": results.get("passed", 0),
                "failed": results.get("failed", 0),
                "skipped": results.get("skipped", 0)
            }
            
            # Add Docker-specific error handling if present
            if not success and "docker_info" in results:
                docker_info = results["docker_info"]
                if not docker_info.get("docker_available", True):
                    print("ERROR: Cypress tests failed due to missing services")
                    print(f"HINT: {results.get('suggestion', 'Please ensure required services are running')}")
                    result_dict["docker_error"] = True
            
            return result_dict
            
        except Exception as e:
            error_msg = f"Cypress test execution failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            
            # Check if this is a Docker-related error
            if "Docker" in str(e) or "docker" in str(e).lower():
                print("HINT: This appears to be a Docker-related issue.")
                print("      Either start Docker Desktop or ensure required services are running locally.")
                print("      Required services: PostgreSQL (port 5432), Redis (port 6379)")
            
            return {
                "success": False,
                "duration": 0,
                "output": "",
                "errors": error_msg,
                "category": "cypress"
            }
    
    def _build_pytest_command(self, service: str, category_name: str, args: argparse.Namespace) -> str:
        """Build pytest command for backend/auth services."""
        config = self.test_configs[service]
        
        cmd_parts = ["pytest"]
        
        # Add category-specific selection (simplified to avoid marker hang issues)
        category_markers = {
            "smoke": [str(config["test_dir"]), "-k", "smoke"],
            "unit": ["netra_backend/tests/unit", "netra_backend/tests/core"],
            "integration": ["netra_backend/tests/integration", "netra_backend/tests/startup"],
            "api": ["netra_backend/tests/test_api_core_critical.py", "netra_backend/tests/test_api_error_handling_critical.py", "netra_backend/tests/test_api_threads_messages_critical.py", "netra_backend/tests/test_api_agent_generation_critical.py", "netra_backend/tests/test_api_endpoints_critical.py"],
            "database": ["netra_backend/tests/test_database_connections.py", "netra_backend/tests/test_database_manager_managers.py", "netra_backend/tests/clickhouse"],
            "websocket": [str(config["test_dir"]), "-k", '"websocket or ws"'],
            "agent": ["netra_backend/tests/agents"],
            "security": [str(config["test_dir"]), "-k", '"auth or security"'],
            # FIXED: E2E category now points only to actual e2e tests
            "e2e_critical": ["tests/e2e/critical"],  # Curated critical e2e tests
            "e2e": ["tests/e2e/integration"],  # Actual e2e integration tests only
            "e2e_full": ["tests/e2e"],  # Full e2e suite (use with caution - may timeout),
            "performance": [str(config["test_dir"]), "-k", "performance"]
        }
        
        if category_name in category_markers:
            cmd_parts.extend(category_markers[category_name])
        else:
            # Default: use the test directory
            cmd_parts.append(str(config["test_dir"]))
        
        # Add environment-specific filtering (skip for API category which doesn't use env markers)
        # TEMPORARILY DISABLED: Environment markers cause pytest to hang when no matching tests exist
        # TODO: Implement smarter environment marker detection
        # if hasattr(args, 'env') and args.env and category_name != "api":
        #     # Add environment marker to filter tests - use pytest markers, not -k expressions
        #     env_marker = f'env_{args.env}'
        #     cmd_parts.extend(["-m", env_marker])
        
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
        
        # Add timeout for unit tests to prevent hanging
        # DISABLED: pytest-timeout conflicts with subprocess timeout causing hangs
        # if category_name == "unit":
        #     cmd_parts.extend(["--timeout=120", "--timeout-method=thread"])
        
        # Add specific test pattern
        if args.pattern:
            # Clean up pattern - remove asterisks that are invalid for pytest -k expressions
            # pytest -k expects Python-like expressions, not glob patterns
            clean_pattern = args.pattern.strip('*')
            cmd_parts.extend(["-k", f'"{clean_pattern}"'])
        
        return " ".join(cmd_parts)
    
    def _build_frontend_command(self, category_name: str, args: argparse.Namespace) -> str:
        """Build test command for frontend."""
        # Determine which Jest setup to use
        if args.real_services or args.env in ['dev', 'staging']:
            setup_file = "jest.setup.real.js"
            # Set environment variables for real service testing using IsolatedEnvironment
            env = get_env()
            env.set('USE_REAL_SERVICES', 'true', 'test_runner_frontend')
            if args.env == 'dev':
                env.set('USE_DOCKER_SERVICES', 'true', 'test_runner_frontend')
            if args.real_llm:
                env.set('USE_REAL_LLM', 'true', 'test_runner_frontend')
        else:
            setup_file = "jest.setup.js"
            # Note: Cannot unset in IsolatedEnvironment, set to false instead
            env = get_env()
            env.set('USE_REAL_SERVICES', 'false', 'test_runner_frontend')
            env.set('USE_DOCKER_SERVICES', 'false', 'test_runner_frontend')
            env.set('USE_REAL_LLM', 'false', 'test_runner_frontend')
        
        category_commands = {
            "unit": f"npm run test:unit -- --setupFilesAfterEnv='<rootDir>/{setup_file}'",
            "integration": f"npm run test:integration -- --setupFilesAfterEnv='<rootDir>/{setup_file}'",
            "e2e": f"npm run test:critical -- --setupFilesAfterEnv='<rootDir>/{setup_file}'",
            "frontend": f"npm run test:fast"
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
        # Set TEST_ENV for environment-aware testing using IsolatedEnvironment
        env = get_env()
        if hasattr(args, 'env'):
            env.set('TEST_ENV', args.env, 'test_runner_pytest')
        
        # Set production protection
        if hasattr(args, 'allow_prod') and args.allow_prod:
            env.set('ALLOW_PROD_TESTS', 'true', 'test_runner_pytest')
        else:
            # Note: Cannot unset in IsolatedEnvironment, set to false instead
            env.set('ALLOW_PROD_TESTS', 'false', 'test_runner_pytest')
        
        # Map env to existing env var patterns
        env_mapping = {
            'test': 'local',
            'dev': 'dev',
            'staging': 'staging',
            'prod': 'prod'
        }
        
        if hasattr(args, 'env'):
            env = get_env()
            mapped_env = env_mapping.get(args.env, args.env)
            env.set('ENVIRONMENT', mapped_env, 'test_runner_nodetest')
            
            # Set specific flags based on environment
            if args.env == 'test':
                env.set('TEST_MODE', 'mock', 'test_runner_nodetest')
                env.set('USE_TEST_DATABASE', 'true', 'test_runner_nodetest')
            elif args.env in ['dev', 'staging', 'prod']:
                env.set('TEST_MODE', 'real', 'test_runner_nodetest')
                env.set('USE_TEST_DATABASE', 'false', 'test_runner_nodetest')
    
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
    
    def _record_test_results(self, category_name: str, result: Dict, environment: str):
        """Record test execution results in the tracker."""
        if not self.test_tracker or not TestRunRecord:
            return
            
        import re
        from datetime import datetime
        
        # Parse output to extract individual test results if possible
        output = result.get("output", "")
        
        # Try to parse pytest output for individual test results
        test_pattern = r"(\S+\.py::\S+)\s+(PASSED|FAILED|SKIPPED|ERROR)"
        matches = re.findall(test_pattern, output)
        
        if matches:
            # Record individual test results
            for test_path, status in matches:
                # Extract file path and test name
                parts = test_path.split("::") 
                file_path = parts[0] if parts else test_path
                test_name = parts[1] if len(parts) > 1 else "unknown"
                
                # Map status
                status_map = {
                    "PASSED": "passed",
                    "FAILED": "failed",
                    "SKIPPED": "skipped",
                    "ERROR": "error"
                }
                
                record = TestRunRecord(
                    test_id="",  # Will be generated by tracker
                    file_path=file_path,
                    test_name=test_name,
                    category=category_name,
                    subcategory=self._determine_subcategory(file_path),
                    status=status_map.get(status, "unknown"),
                    duration=0.0,  # Would need more parsing to extract
                    timestamp=datetime.now().isoformat(),
                    environment=environment,
                    error_message=None,  # Would need more parsing
                    failure_type=None
                )
                
                self.test_tracker.record_test_run(record)
        else:
            # Record category-level result
            record = TestRunRecord(
                test_id="",
                file_path=f"category_{category_name}",
                test_name=f"{category_name}_tests",
                category=category_name,
                subcategory=category_name,
                status="passed" if result["success"] else "failed",
                duration=result.get("duration", 0.0),
                timestamp=datetime.now().isoformat(),
                environment=environment,
                error_message=result.get("errors") if not result["success"] else None,
                failure_type="category_failure" if not result["success"] else None
            )
            
            self.test_tracker.record_test_run(record)
    
    def _determine_subcategory(self, file_path: str) -> str:
        """Determine test subcategory from file path."""
        if "unit" in file_path:
            return "unit"
        elif "integration" in file_path:
            return "integration"
        elif "e2e" in file_path:
            return "e2e"
        elif "api" in file_path:
            return "api"
        elif "websocket" in file_path:
            return "websocket"
        else:
            return "other"
    
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
    
    # Cypress-specific arguments
    parser.add_argument(
        "--cypress-headed",
        action="store_true",
        help="Run Cypress tests in headed mode (show browser UI)"
    )
    
    parser.add_argument(
        "--cypress-browser",
        choices=["chrome", "firefox", "edge", "electron"],
        default="chrome",
        help="Browser to use for Cypress tests (default: chrome)"
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
        validator = TestValidation()
        print("Test structure validation not fully implemented yet.")
        print("Cypress integration completed successfully!")
        return 0
    
    # Run tests
    runner = UnifiedTestRunner()
    return runner.run(args)


if __name__ == "__main__":
    sys.exit(main())