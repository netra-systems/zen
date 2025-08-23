#!/usr/bin/env python
"""
NETRA APEX UNIFIED TEST RUNNER
==============================
Enhanced single entry point for ALL testing operations across the entire Netra platform.
This runner coordinates testing for backend, frontend, auth service, and integration tests
with advanced categorization, progress tracking, and intelligent execution planning.

USAGE:
    python unified_test_runner.py              # Run default test suite
    python unified_test_runner.py --help       # Show all options
    
TEST LEVELS (Legacy Support):
    unit            Fast isolated component tests (1-3min)
    integration     Service interaction tests (3-8min) [DEFAULT]
    e2e             End-to-end real service tests (10-30min)
    performance     Performance and load testing (3-10min)
    comprehensive   Complete system validation (30-60min)
    
    Legacy levels (deprecated, will redirect):
    smoke, critical, agents -> unit
    real_e2e, real_services, staging* -> e2e

ENHANCED CATEGORY SYSTEM:
    --category <name>           Run specific category (unit, integration, api, etc.)
    --categories <name1> <name2> Run multiple categories
    --list-categories           List all available categories
    --show-category-stats       Show historical category performance

CATEGORIES:
    CRITICAL: smoke, startup
    HIGH:     unit, security, database
    MEDIUM:   integration, api, websocket, agent
    LOW:      frontend, performance, e2e, real_e2e, real_services
    
    ROLLUP:   critical_path, core_functionality, communication, 
              full_stack, performance_suite, external_dependencies

ENHANCED FEATURES:
    --window-size <minutes>     Auto-split window size (default: 15)
    --fail-fast-mode <mode>     Fail-fast strategy (smart_adaptive, threshold_based, etc.)
    --progress-mode <mode>      Progress display (simple, rich, json)
    --disable-auto-split        Disable automatic test splitting
    --resume-from <category>    Resume execution from specific category

SERVICES:
    backend         Main backend application
    auth            Auth service
    frontend        Frontend application
    dev_launcher    Development launcher and system startup tests
    all             Run tests for all services

EXAMPLES:
    # Legacy usage (still supported)
    python unified_test_runner.py                           # Run integration tests (default)
    python unified_test_runner.py --level unit              # Quick development tests
    python unified_test_runner.py --level e2e --real-llm    # Real service E2E tests
    
    # Enhanced category usage
    python unified_test_runner.py --category unit           # Run unit tests category
    python unified_test_runner.py --categories unit api     # Run unit and API tests
    python unified_test_runner.py --category critical_path  # Run critical path rollup
    python unified_test_runner.py --category performance --window-size 30  # Performance with 30min windows
    
    # Enhanced features
    python unified_test_runner.py --categories unit integration --fail-fast-mode smart_adaptive
    python unified_test_runner.py --category e2e --progress-mode rich --window-size 20
    python unified_test_runner.py --list-categories         # Show available categories
    python unified_test_runner.py --show-category-stats     # Show performance statistics
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()

def _check_pytest_timeout_installed() -> bool:
    """Check if pytest-timeout plugin is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "pytest-timeout"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

# Import test framework
from test_framework.runner import UnifiedTestRunner as FrameworkRunner
from test_framework.test_config import TEST_LEVELS, configure_dev_environment, configure_real_llm, resolve_test_level
from test_framework.test_discovery import TestDiscovery
from test_framework.test_validation import TestValidation

# Enhanced category system imports - handle graceful fallback
try:
    from test_framework.category_system import CategorySystem, ExecutionPlan, CategoryPriority
    from test_framework.progress_tracker import ProgressTracker, ProgressEvent
    from test_framework.auto_splitter import TestSplitter, SplittingStrategy
    from test_framework.fail_fast_strategies import FailFastStrategy, FailFastMode
    from test_framework.config.category_config import CategoryConfigLoader
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Enhanced features not available: {e}")
    # Create stub classes for graceful fallback
    CategorySystem = ExecutionPlan = CategoryPriority = None
    ProgressTracker = ProgressEvent = None
    TestSplitter = SplittingStrategy = None
    FailFastStrategy = FailFastMode = None
    CategoryConfigLoader = None
    ENHANCED_FEATURES_AVAILABLE = False


class UnifiedTestRunner:
    """Main test runner orchestrating all test operations with enhanced category system."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.test_framework_path = self.project_root / "test_framework"
        self.backend_path = self.project_root / "netra_backend"
        self.auth_path = self.project_root / "auth_service"
        self.frontend_path = self.project_root / "frontend"
        
        # Enhanced category system components
        self.config_loader = None
        self.category_system = None
        self.progress_tracker = None
        self.test_splitter = None
        self.fail_fast_strategy = None
        self.execution_plan = None
        self.use_enhanced_features = False
        
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
            },
            "dev_launcher": {
                "path": self.project_root,
                "test_dir": "tests",
                "config": "pytest.ini",
                "command": "pytest"
            }
        }
        
    def _initialize_enhanced_features(self, args: argparse.Namespace) -> bool:
        """Initialize enhanced category system features if requested."""
        # Check if enhanced features are available
        if not ENHANCED_FEATURES_AVAILABLE:
            return False
            
        # Check if enhanced features are requested
        enhanced_args = ['category', 'categories', 'window_size', 'fail_fast_mode', 
                        'progress_mode', 'resume_from', 'show_category_stats', 'disable_auto_split']
        
        self.use_enhanced_features = any(hasattr(args, arg) and getattr(args, arg) is not None 
                                       for arg in enhanced_args)
        
        if not self.use_enhanced_features:
            return False
            
        try:
            # Initialize configuration loader
            self.config_loader = CategoryConfigLoader(self.project_root)
            config = self.config_loader.load_config()
            
            # Initialize category system
            self.category_system = self.config_loader.create_category_system(config)
            
            # Initialize progress tracker
            if getattr(args, 'progress_mode', None):
                self.progress_tracker = self.config_loader.create_progress_tracker(config)
            
            # Initialize test splitter for auto-splitting
            if not getattr(args, 'disable_auto_split', False) and TestSplitter:
                self.test_splitter = TestSplitter(project_root=self.project_root)
                # Store the strategy and window size for later use
                self.splitting_strategy = SplittingStrategy(getattr(args, 'splitting_strategy', 'hybrid'))
                self.target_window_duration = getattr(args, 'window_size', 15)
            
            # Initialize fail-fast strategy
            if hasattr(args, 'fail_fast_mode') and args.fail_fast_mode and FailFastStrategy and FailFastMode:
                threshold_config = self.config_loader.create_threshold_config(config)
                self.fail_fast_strategy = FailFastStrategy(
                    mode=FailFastMode(args.fail_fast_mode),
                    threshold_config=threshold_config
                )
            
            print(f"Enhanced category system initialized with {len(self.category_system.categories)} categories")
            return True
            
        except Exception as e:
            print(f"Warning: Could not initialize enhanced features: {e}")
            print("Falling back to legacy test runner")
            self.use_enhanced_features = False
            return False
    
    def run(self, args: argparse.Namespace) -> int:
        """Main entry point for test execution."""
        
        # Try to initialize enhanced features
        enhanced_initialized = self._initialize_enhanced_features(args)
        
        if enhanced_initialized and self.use_enhanced_features:
            return self._run_enhanced_execution(args)
        else:
            return self._run_legacy_execution(args)
    
    def _run_enhanced_execution(self, args: argparse.Namespace) -> int:
        """Run tests using the enhanced category system."""
        try:
            # Configure environment
            self._configure_environment(args)
            
            # Determine categories to run
            categories_to_run = self._determine_categories_to_run(args)
            if not categories_to_run:
                print("No categories to run based on selection criteria")
                return 1
            
            # Create execution plan
            self.execution_plan = self.category_system.create_execution_plan(
                categories_to_run,
                max_parallel=getattr(args, 'workers', 8)
            )
            
            # Start progress tracking
            if self.progress_tracker:
                run_id = f"run_{int(time.time())}"
                self.progress_tracker.start_run(
                    run_id=run_id,
                    categories=categories_to_run,
                    test_level=args.level,
                    parallel_workers=getattr(args, 'workers', 8),
                    fail_fast=getattr(args, 'fast_fail', False),
                    real_llm=getattr(args, 'real_llm', False),
                    environment=getattr(args, 'env', 'local')
                )
            
            # Show execution plan
            self._show_execution_plan(self.execution_plan, args)
            
            # Execute categories by phase
            results = self._execute_categories_by_phases(self.execution_plan, args)
            
            # Complete progress tracking
            if self.progress_tracker:
                success = all(r["success"] for r in results.values())
                self.progress_tracker.complete_run(success)
            
            # Generate enhanced report
            self._generate_enhanced_report(results, args)
            
            return 0 if all(r["success"] for r in results.values()) else 1
            
        except Exception as e:
            print(f"Error in enhanced execution: {e}")
            print("Falling back to legacy execution")
            return self._run_legacy_execution(args)
    
    def _run_legacy_execution(self, args: argparse.Namespace) -> int:
        """Run tests using the legacy system (backward compatibility)."""
        # Configure environment
        self._configure_environment(args)
        
        # Determine which services to test
        services = self._get_services_to_test(args)
        
        # Run tests for each service
        results = {}
        for service in services:
            print(f"\n{'='*60}")
            print(f"Running {service.upper()} tests - Level: {args.level}")
            print(f"{'='*60}\n")
            
            result = self._run_service_tests(service, args)
            results[service] = result
            
        # Generate consolidated report
        self._generate_report(results, args)
        
        # Return overall status
        return 0 if all(r["success"] for r in results.values()) else 1
    
    def _configure_environment(self, args: argparse.Namespace):
        """Configure test environment based on arguments."""
        if args.env == "dev":
            configure_dev_environment()
        elif args.real_llm:
            # Use default values for real LLM configuration
            configure_real_llm(
                model="gemini-2.5-flash",  # Default model
                timeout=60,  # Default timeout
                parallel="auto",  # Auto-detect parallelism
                test_level=args.level,  # Pass the test level
                use_dedicated_env=True  # Use dedicated test environment
            )
            
        # Set environment variables
        os.environ["TEST_LEVEL"] = args.level
        os.environ["TEST_ENV"] = args.env
        
        if args.no_coverage:
            os.environ["COVERAGE_ENABLED"] = "false"
        
    def _get_services_to_test(self, args: argparse.Namespace) -> List[str]:
        """Determine which services to test based on arguments."""
        if args.service == "all":
            return ["backend", "auth", "frontend", "dev_launcher"]
        return [args.service]
    
    def _run_service_tests(self, service: str, args: argparse.Namespace) -> Dict:
        """Run tests for a specific service."""
        config = self.test_configs[service]
        
        # Build test command
        if service == "frontend":
            cmd = self._build_frontend_command(args)
        elif service == "dev_launcher":
            cmd = self._build_dev_launcher_command(args)
        else:
            cmd = self._build_pytest_command(service, args)
        
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
    
    def _build_pytest_command(self, service: str, args: argparse.Namespace) -> str:
        """Build pytest command for backend/auth services."""
        config = self.test_configs[service]
        
        cmd_parts = ["pytest"]
        
        # Add test directory
        cmd_parts.append(str(config["test_dir"]))
        
        # Add level-specific markers
        if args.level in TEST_LEVELS:
            level_config = TEST_LEVELS[args.level]
            if "markers" in level_config:
                for marker in level_config["markers"]:
                    cmd_parts.append(f"-m {marker}")
        
        # Add coverage options
        if not args.no_coverage:
            cmd_parts.extend([
                "--cov=.",
                "--cov-report=html",
                "--cov-report=term-missing"
            ])
        
        # Add parallelization
        if args.parallel:
            cmd_parts.append(f"-n {args.workers}")
        
        # Add verbosity
        if args.verbose:
            cmd_parts.append("-vv")
        
        # Add fast fail
        if args.fast_fail:
            cmd_parts.append("-x")
        
        # Add specific test pattern
        if args.pattern:
            cmd_parts.append(f"-k {args.pattern}")
        
        return " ".join(cmd_parts)
    
    def _build_dev_launcher_command(self, args: argparse.Namespace) -> str:
        """Build pytest command for dev_launcher tests."""
        cmd_parts = ["pytest"]
        
        # Dev launcher test patterns - tests that validate dev_launcher functionality
        dev_launcher_patterns = [
            "tests/test_system_startup.py",
            "tests/e2e/test_dev_launcher_real_startup.py", 
            "tests/e2e/integration/test_dev_launcher_startup_complete.py",
            "tests/integration/test_dev_launcher_utilities_validation.py",
            "-k", "dev_launcher"
        ]
        
        # Add test level specific filtering
        if args.level == "unit":
            # For unit tests, focus on basic dev_launcher functionality
            cmd_parts.extend([
                "tests/test_system_startup.py::TestSystemStartup::test_dev_launcher_help",
                "tests/test_system_startup.py::TestSystemStartup::test_dev_launcher_list_services",
                "tests/test_system_startup.py::TestSystemStartup::test_dev_launcher_minimal_mode"
            ])
        elif args.level == "integration":
            # For integration tests, include service interaction tests
            cmd_parts.extend([
                "tests/e2e/test_dev_launcher_real_startup.py",
                "tests/integration/test_dev_launcher_utilities_validation.py",
                "tests/test_system_startup.py"
            ])
            # Only add timeout if pytest-timeout is installed
            if _check_pytest_timeout_installed():
                cmd_parts.append("--timeout=300")  # 5 minute timeout for integration tests
        elif args.level == "e2e":
            # For e2e tests, include comprehensive startup tests
            cmd_parts.extend(dev_launcher_patterns)
            # Only add timeout if pytest-timeout is installed
            if _check_pytest_timeout_installed():
                cmd_parts.extend(["--timeout=600"])  # 10 minute timeout for e2e tests
        elif args.level == "performance":
            # For performance tests, focus on startup performance
            cmd_parts.extend([
                "tests/e2e/test_dev_launcher_real_startup.py::TestDevLauncherRealStartup::test_service_startup_order_validation"
            ])
            # Only add timeout if pytest-timeout is installed  
            if _check_pytest_timeout_installed():
                cmd_parts.append("--timeout=300")
        elif args.level == "comprehensive":
            # For comprehensive tests, run all dev_launcher tests
            cmd_parts.extend(dev_launcher_patterns)
            # Only add timeout if pytest-timeout is installed
            if _check_pytest_timeout_installed():
                cmd_parts.extend(["--timeout=900"])  # 15 minute timeout for comprehensive tests
        else:
            # Default pattern
            cmd_parts.extend(dev_launcher_patterns)
        
        # Add coverage options (skip for performance tests)
        if not args.no_coverage and args.level not in ["performance", "e2e"]:
            cmd_parts.extend([
                "--cov=scripts.dev_launcher",
                "--cov=scripts.dev_launcher_core", 
                "--cov=scripts.dev_launcher_config",
                "--cov-report=html:htmlcov/dev_launcher",
                "--cov-report=term-missing"
            ])
        
        # Add parallelization (limited for dev_launcher tests due to port conflicts)
        if args.parallel and args.level not in ["e2e", "performance"]:
            # Limited parallelization to avoid port conflicts
            cmd_parts.append("-n 2")
        
        # Add verbosity
        if args.verbose:
            cmd_parts.append("-vv")
        
        # Add fast fail
        if args.fast_fail:
            cmd_parts.append("-x")
        
        # Add specific test pattern
        if args.pattern:
            cmd_parts.append(f"-k {args.pattern}")
        
        # Windows compatibility - ensure proper test isolation
        cmd_parts.extend([
            "--tb=short",  # Shorter tracebacks for cleaner output
            "--strict-markers",  # Ensure test markers are defined
            "--disable-warnings"  # Reduce noise in dev_launcher tests
        ])
        
        return " ".join(cmd_parts)
    
    def _build_frontend_command(self, args: argparse.Namespace) -> str:
        """Build test command for frontend using level mapping."""
        from test_framework.frontend_test_mapping import get_jest_command_for_level
        
        # Use the mapping to get appropriate Jest command
        base_command = get_jest_command_for_level(args.level)
        
        # Add additional flags based on args
        if args.no_coverage and "--coverage" not in base_command:
            base_command += " --coverage=false"
        if args.fast_fail and "--bail" not in base_command:
            base_command += " --bail"
        if args.verbose:
            base_command += " --verbose"
            
        return base_command
    
    def _generate_report(self, results: Dict, args: argparse.Namespace):
        """Generate consolidated test report."""
        report_dir = self.project_root / "test_reports"
        report_dir.mkdir(exist_ok=True)
        
        # Create timestamp for report
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Build report data
        report_data = {
            "timestamp": timestamp,
            "level": args.level,
            "environment": args.env,
            "services": results,
            "overall_success": all(r["success"] for r in results.values()),
            "total_duration": sum(r["duration"] for r in results.values())
        }
        
        # Save JSON report
        json_report = report_dir / f"unified_test_report_{timestamp}.json"
        with open(json_report, "w") as f:
            json.dump(report_data, f, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*60}")
        print(f"Level: {args.level}")
        print(f"Environment: {args.env}")
        print(f"Total Duration: {report_data['total_duration']:.2f}s")
        print(f"\nService Results:")
        
        for service, result in results.items():
            status = "PASSED" if result["success"] else "FAILED"
            print(f"  {service:10} {status:10} ({result['duration']:.2f}s)")
        
        print(f"\nOverall: {'PASSED' if report_data['overall_success'] else 'FAILED'}")
        print(f"Report saved: {json_report}")
    
    def _determine_categories_to_run(self, args: argparse.Namespace) -> List[str]:
        """Determine which categories to run based on arguments."""
        categories = []
        
        # Handle specific category selection
        if hasattr(args, 'category') and args.category:
            categories.append(args.category)
        
        if hasattr(args, 'categories') and args.categories:
            categories.extend(args.categories)
        
        # Handle legacy level mapping if no specific categories selected
        if not categories and self.config_loader:
            # Try to load legacy mapping from config
            config_file = self.config_loader.config_dir / "test_categories.yml"
            if config_file.exists():
                import yaml
                with open(config_file) as f:
                    config_data = yaml.safe_load(f)
                legacy_mapping = config_data.get("legacy_mapping", {})
                if args.level in legacy_mapping:
                    categories = legacy_mapping[args.level]
        
        # Fallback to standard categories based on level
        if not categories:
            level_to_categories = {
                "smoke": ["smoke"],
                "unit": ["unit"],
                "integration": ["smoke", "unit", "integration", "api", "database"],
                "e2e": ["smoke", "unit", "integration", "api", "database", "e2e"],
                "performance": ["performance"],
                "comprehensive": ["smoke", "unit", "integration", "api", "database", "websocket", "agent", "frontend", "e2e"]
            }
            categories = level_to_categories.get(args.level, ["integration"])
        
        # Filter categories that exist in the system
        if self.category_system:
            valid_categories = [cat for cat in categories if cat in self.category_system.categories]
            if valid_categories != categories:
                missing = set(categories) - set(valid_categories)
                print(f"Warning: Categories not found in system: {missing}")
            return valid_categories
        
        return categories
    
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
                else:
                    print(f"  - {category_name} (unknown)")
        
        print(f"\n{'='*60}")
    
    def _execute_categories_by_phases(self, execution_plan: ExecutionPlan, args: argparse.Namespace) -> Dict:
        """Execute categories according to the execution plan."""
        results = {}
        
        for phase_num, phase_categories in enumerate(execution_plan.phases):
            print(f"\n{'='*40}")
            print(f"PHASE {phase_num + 1}: {len(phase_categories)} categories")
            print(f"{'='*40}")
            
            # Execute categories in this phase (potentially in parallel)
            phase_results = self._execute_phase_categories(phase_categories, phase_num, args)
            results.update(phase_results)
            
            # Check if we should stop due to fail-fast
            if self.fail_fast_strategy and self.fail_fast_strategy.should_stop_execution(phase_results):
                print("\nStopping execution due to fail-fast strategy")
                # Mark remaining categories as skipped
                remaining_categories = []
                for remaining_phase in execution_plan.phases[phase_num + 1:]:
                    remaining_categories.extend(remaining_phase)
                
                for category_name in remaining_categories:
                    results[category_name] = {
                        "success": False,
                        "duration": 0,
                        "output": "",
                        "errors": "Skipped due to fail-fast strategy",
                        "skipped": True
                    }
                break
        
        return results
    
    def _execute_phase_categories(self, category_names: List[str], phase_num: int, args: argparse.Namespace) -> Dict:
        """Execute categories in a single phase."""
        results = {}
        
        # For now, execute sequentially - parallel execution would require more complex orchestration
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
        # Map category to appropriate service execution
        # This is a simplified implementation - in practice, you'd want more sophisticated mapping
        
        category_to_service_mapping = {
            "smoke": "all",
            "unit": "all", 
            "integration": "backend",
            "api": "backend",
            "database": "backend",
            "websocket": "backend",
            "agent": "backend",
            "security": "auth",
            "frontend": "frontend",
            "e2e": "all",
            "performance": "all",
            "real_e2e": "all",
            "real_services": "all"
        }
        
        # Determine which service(s) to run for this category
        service_mapping = category_to_service_mapping.get(category_name, "backend")
        
        if service_mapping == "all":
            # Run all services with category-specific configuration
            all_results = {}
            services = ["backend", "auth", "frontend"]
            
            for service in services:
                service_result = self._run_service_tests_for_category(service, category_name, args)
                all_results[service] = service_result
            
            # Combine results
            overall_success = all(r["success"] for r in all_results.values())
            combined_output = "\n".join(r["output"] for r in all_results.values())
            combined_errors = "\n".join(r["errors"] for r in all_results.values())
            total_duration = sum(r["duration"] for r in all_results.values())
            
            return {
                "success": overall_success,
                "duration": total_duration,
                "output": combined_output,
                "errors": combined_errors,
                "service_results": all_results
            }
        else:
            # Run specific service
            return self._run_service_tests_for_category(service_mapping, category_name, args)
    
    def _run_service_tests_for_category(self, service: str, category_name: str, args: argparse.Namespace) -> Dict:
        """Run tests for a specific service and category combination."""
        # This method adapts the existing service test execution to be category-aware
        # For now, we'll use the existing service test execution with modified markers/patterns
        
        # Create a modified args for this category
        category_args = argparse.Namespace(**vars(args))
        
        # Override level with category-specific settings if available
        if self.category_system:
            category = self.category_system.get_category(category_name)
            if category:
                # Apply category-specific test patterns or markers
                if hasattr(category_args, 'pattern'):
                    if category_args.pattern:
                        category_args.pattern = f"({category_args.pattern}) and {category_name}"
                    else:
                        category_args.pattern = category_name
        
        # Execute using existing service test method
        return self._run_service_tests(service, category_args)
    
    def _extract_test_counts_from_result(self, result: Dict) -> Dict[str, int]:
        """Extract test counts from execution result."""
        # This is a simplified extraction - in practice, you'd parse the actual test output
        # to get accurate counts
        test_counts = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0
        }
        
        if result.get("success", False):
            test_counts["total"] = 1
            test_counts["passed"] = 1
        else:
            test_counts["total"] = 1
            test_counts["failed"] = 1
        
        return test_counts
    
    def _generate_enhanced_report(self, results: Dict, args: argparse.Namespace):
        """Generate enhanced report with category system features."""
        report_dir = self.project_root / "test_reports"
        report_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Build enhanced report data
        report_data = {
            "timestamp": timestamp,
            "test_level": args.level,
            "environment": getattr(args, 'env', 'local'),
            "enhanced_execution": True,
            "categories": results,
            "overall_success": all(r["success"] for r in results.values()),
            "total_duration": sum(r["duration"] for r in results.values()),
            "execution_plan": self.execution_plan.to_dict() if hasattr(self.execution_plan, 'to_dict') else None,
            "category_statistics": self.category_system.get_category_statistics() if self.category_system else None
        }
        
        # Add progress tracking data if available
        if self.progress_tracker:
            progress_data = self.progress_tracker.get_current_progress()
            if progress_data:
                report_data["progress_tracking"] = progress_data
        
        # Save enhanced JSON report
        json_report = report_dir / f"enhanced_test_report_{timestamp}.json"
        with open(json_report, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Print enhanced summary
        print(f"\n{'='*60}")
        print("ENHANCED TEST EXECUTION SUMMARY")
        print(f"{'='*60}")
        print(f"Test Level: {args.level}")
        print(f"Environment: {getattr(args, 'env', 'local')}")
        print(f"Total Duration: {report_data['total_duration']:.2f}s")
        print(f"Categories Executed: {len(results)}")
        
        # Category results
        print(f"\nCategory Results:")
        for category_name, result in results.items():
            status = "PASSED" if result["success"] else "FAILED"
            print(f"  {category_name:15} {status:10} ({result['duration']:.2f}s)")
        
        # Overall result
        print(f"\nOverall: {'PASSED' if report_data['overall_success'] else 'FAILED'}")
        print(f"Enhanced Report: {json_report}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for Netra Apex Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test level selection - new 5-level system with backward compatibility
    parser.add_argument(
        "--level",
        choices=["unit", "integration", "e2e", "performance", "comprehensive", 
                # Legacy levels for backward compatibility
                "smoke", "critical", "agents", "real_e2e", "real_services", 
                "staging", "staging-real", "staging-quick"],
        default="integration",
        help="Test level to run (default: integration). See docs for 5-level system."
    )
    
    # Service selection
    parser.add_argument(
        "--service",
        choices=["backend", "auth", "frontend", "dev_launcher", "all"],
        default="all",
        help="Service to test (default: all)"
    )
    
    # Environment configuration
    parser.add_argument(
        "--env",
        choices=["local", "dev", "staging", "prod"],
        default="local",
        help="Environment to test against (default: local)"
    )
    
    # LLM configuration
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Use real LLM instead of mocks"
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
    
    # Enhanced category system arguments
    parser.add_argument(
        "--category",
        help="Run specific category (e.g., 'unit', 'integration', 'api')"
    )
    
    parser.add_argument(
        "--categories", 
        nargs='+',
        help="Run multiple categories (e.g., '--categories unit integration api')"
    )
    
    parser.add_argument(
        "--window-size",
        type=int,
        default=15,
        help="Auto-split window size in minutes (default: 15)"
    )
    
    parser.add_argument(
        "--fail-fast-mode",
        choices=["disabled", "first_failure", "category_failure", "critical_failure", "threshold_based", "smart_adaptive", "dependency_aware"],
        help="Fail-fast strategy mode"
    )
    
    parser.add_argument(
        "--progress-mode",
        choices=["simple", "rich", "json"],
        help="Progress display mode"
    )
    
    parser.add_argument(
        "--resume-from",
        help="Resume execution from specific category"
    )
    
    parser.add_argument(
        "--show-category-stats",
        action="store_true",
        help="Show historical category statistics"
    )
    
    parser.add_argument(
        "--disable-auto-split",
        action="store_true", 
        help="Disable automatic test splitting"
    )
    
    parser.add_argument(
        "--splitting-strategy",
        choices=["time_based", "count_based", "category_based", "complexity_based", "dependency_aware", "hybrid"],
        default="hybrid",
        help="Test splitting strategy (default: hybrid)"
    )
    
    # Discovery options
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available tests without running"
    )
    
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available categories and their configuration"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate test structure and configuration"
    )
    
    args = parser.parse_args()
    
    # Handle special operations
    if args.list:
        # Simple pytest-based test listing for now
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q", "tests/integration/"], 
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        if result.returncode == 0:
            print("Integration Tests Found:")
            for line in result.stdout.strip().split('\n')[:20]:  # Show first 20
                if "::" in line:
                    print(f"  - {line}")
        else:
            print("Error collecting tests:")
            print(result.stderr)
        return 0
    
    if args.list_categories:
        # List available categories
        if not ENHANCED_FEATURES_AVAILABLE:
            print("Enhanced category system not available. Using legacy levels:")
            print("  unit, integration, e2e, performance, comprehensive")
            return 0
        
        try:
            config_loader = CategoryConfigLoader(PROJECT_ROOT)
            category_system = config_loader.create_category_system()
            
            print(f"\n{'='*60}")
            print("AVAILABLE TEST CATEGORIES")
            print(f"{'='*60}")
            
            # Group by priority
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
            
            # Show rollup categories
            rollup_categories = [cat for cat in category_system.categories.values() 
                               if hasattr(cat, 'rollup_categories') and getattr(cat, 'rollup_categories', None)]
            if rollup_categories:
                print(f"\nRollup Categories:")
                for category in rollup_categories:
                    print(f"  {category.name:15} - {category.description}")
                    print(f"                    Includes: {', '.join(getattr(category, 'rollup_categories', []))}")
            
        except Exception as e:
            print(f"Error listing categories: {e}")
            return 1
        return 0
    
    if args.show_category_stats:
        # Show historical category statistics
        if not ENHANCED_FEATURES_AVAILABLE:
            print("Enhanced category system not available. No statistics to show.")
            return 0
        
        try:
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
            
        except Exception as e:
            print(f"Error showing category stats: {e}")
            return 1
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