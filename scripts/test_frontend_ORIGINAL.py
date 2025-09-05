from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python
"""
env = get_env()
Comprehensive frontend test runner for Netra AI Platform
Designed for easy use by Claude Code and CI/CD pipelines
Now with test isolation support for concurrent execution
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Import test isolation utilities
try:
    from test_framework.test_isolation import TestIsolationManager
except ImportError:
    TestIsolationManager = None

# Test categories for organized testing
TEST_CATEGORIES = {
    "unit": ["__tests__/components", "__tests__/hooks", "__tests__/store", "__tests__/services", "__tests__/lib", "__tests__/utils"],
    "integration": ["__tests__/integration"],
    "components": ["__tests__/components"],
    "hooks": ["__tests__/hooks"],
    "store": ["__tests__/store"],
    "websocket": ["__tests__/services/webSocketService.test.ts"],
    "auth": ["__tests__/auth"],
    "e2e": ["cypress/e2e"],
    "smoke": ["__tests__/system/startup.test.tsx", "__tests__/integration/critical-integration.test.tsx"],
}


def check_node_modules() -> bool:
    """Check if node_modules exists"""
    node_modules = FRONTEND_DIR / "node_modules"
    return node_modules.exists()


def install_dependencies(force: bool = False) -> bool:
    """Install frontend dependencies if needed"""
    if not check_node_modules() or force:
        print("Installing frontend dependencies...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            shell=True  # Need shell=True on Windows for npm commands
        )
        if result.returncode != 0:
            print(f"Failed to install dependencies: {result.stderr}")
            return False
        print("Dependencies installed successfully")
    return True


def check_dependencies() -> Dict[str, bool]:
    """Check if required test dependencies are available"""
    status = {
        "node": False,
        "npm": False,
        "jest": False,
        "cypress": False,
        "next": False,
        "typescript": False,
    }
    
    # Check Node.js and npm
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, encoding='utf-8', errors='replace', shell=True)
        if result.returncode == 0:
            status["node"] = True
    except:
        pass
    
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True, encoding='utf-8', errors='replace', shell=True)
        if result.returncode == 0:
            status["npm"] = True
    except:
        pass
    
    # Check frontend packages if node_modules exists
    if check_node_modules():
        package_json_path = FRONTEND_DIR / "package.json"
        if package_json_path.exists():
            with open(package_json_path) as f:
                package_data = json.load(f)
                deps = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                status["jest"] = "jest" in deps
                status["cypress"] = "cypress" in deps
                status["next"] = "next" in deps
                status["typescript"] = "typescript" in deps
    
    return status


def run_jest_tests(args, isolation_manager=None) -> int:
    """Run Jest tests"""
    jest_args = _build_base_jest_args()
    _add_jest_coverage_args(args, jest_args, isolation_manager)
    _add_jest_option_args(args, jest_args)
    _add_isolation_args(isolation_manager, jest_args)
    _add_test_selection_args(args, jest_args)
    return _execute_jest_command(jest_args)

def _build_base_jest_args():
    """Build base Jest command arguments"""
    jest_args = ["npm", "run", "test"]
    if "--" not in jest_args:
        jest_args.append("--")
    jest_args.extend(["--forceExit", "--detectOpenHandles"])
    return jest_args

def _add_jest_coverage_args(args, jest_args, isolation_manager):
    """Add Jest coverage arguments"""
    if args.coverage:
        jest_args.extend(["--coverage"])
        coverage_dir = _get_coverage_directory(isolation_manager)
        jest_args.extend([f"--coverageDirectory={coverage_dir}"])

def _get_coverage_directory(isolation_manager):
    """Get coverage directory path"""
    if isolation_manager and isolation_manager.directories:
        return isolation_manager.directories.get('frontend_coverage')
    return "../reports/frontend-coverage"

def _add_jest_option_args(args, jest_args):
    """Add Jest option arguments"""
    if args.watch:
        jest_args.extend(["--watch"])
    if args.update_snapshots:
        jest_args.extend(["--updateSnapshot"])
    if args.verbose:
        jest_args.extend(["--verbose"])
    if args.keyword:
        jest_args.extend([f"--testNamePattern={args.keyword}"])

def _add_isolation_args(isolation_manager, jest_args):
    """Add isolation-specific Jest arguments"""
    if isolation_manager:
        isolation_args = isolation_manager.get_jest_args()
        for arg in isolation_args:
            if "--cacheDirectory" in arg:
                jest_args.extend([arg])

def _add_test_selection_args(args, jest_args):
    """Add test selection arguments"""
    if args.tests:
        jest_args.extend(args.tests)
    elif args.category and args.category != "e2e":
        _add_category_patterns(args, jest_args)

def _add_category_patterns(args, jest_args):
    """Add test patterns for selected category"""
    patterns = TEST_CATEGORIES.get(args.category, [])
    if patterns:
        test_patterns = _build_test_patterns(patterns)
        _apply_test_patterns(args, jest_args, test_patterns)

def _build_test_patterns(patterns):
    """Build test patterns from category patterns"""
    test_patterns = []
    for pattern in patterns:
        if pattern.endswith(".test.ts") or pattern.endswith(".test.tsx"):
            test_patterns.append(f"**/{pattern}")
        elif "/" in pattern:
            test_patterns.append(f"**/{pattern}/**/*.test.[jt]s?(x)")
        else:
            test_patterns.append(f"**/{pattern}/**/*.test.[jt]s?(x)")
    return test_patterns

def _apply_test_patterns(args, jest_args, test_patterns):
    """Apply test patterns to Jest arguments"""
    if len(test_patterns) == 1:
        jest_args.extend(["--testMatch", test_patterns[0]])
    elif args.category == "unit":
        jest_args.extend(["--testMatch", "**/__tests__/@(components|hooks|store|services|lib|utils)/**/*.test.[jt]s?(x)"])
    else:
        jest_args.extend(["--testMatch", test_patterns[0]])

def _execute_jest_command(jest_args):
    """Execute Jest command and return exit code"""
    print(f"Running: {' '.join(jest_args)}")
    print("-" * 80)
    result = subprocess.run(
        jest_args, cwd=FRONTEND_DIR, capture_output=False,
        text=True, encoding='utf-8', errors='replace', shell=True
    )
    return result.returncode


def run_cypress_tests(args, isolation_manager=None) -> int:
    """Run Cypress E2E tests"""
    # Check if backend is running
    backend_running = check_backend_running(isolation_manager)
    frontend_running = check_frontend_running(isolation_manager)
    
    if not backend_running:
        print("[WARNING] Backend server is not running. Starting it...")
        start_backend()
        # Removed unnecessary sleep  # Give backend time to start
    
    if not frontend_running:
        print("[WARNING] Frontend dev server is not running. Starting it...")
        start_frontend()
        # Removed unnecessary sleep  # Give frontend time to start
    
    # Determine Cypress command
    if args.cypress_open:
        cypress_cmd = ["npm", "run", "cypress:open"]
    else:
        cypress_cmd = ["npm", "run", "cy:run"]
    
    # Add spec pattern if provided
    if args.tests:
        cypress_cmd.extend(["--", "--spec"] + args.tests)
    elif args.category == "e2e":
        cypress_cmd.extend(["--", "--spec", "cypress/e2e/**/*.cy.ts"])
    
    # Run Cypress
    print(f"Running: {' '.join(cypress_cmd)}")
    print("-" * 80)
    
    result = subprocess.run(
        cypress_cmd,
        cwd=FRONTEND_DIR,
        capture_output=False,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=True  # Need shell=True on Windows for npm commands
    )
    
    return result.returncode


def check_backend_running(isolation_manager=None) -> bool:
    """Check if backend server is running"""
    try:
        import requests
        if isolation_manager and isolation_manager.ports:
            port = isolation_manager.ports.get('backend', 8000)
        else:
            port = int(env.get('BACKEND_PORT', 8000))
        response = requests.get(f"http://localhost:{port}/health", timeout=1)
        return response.status_code == 200
    except:
        return False


def check_frontend_running(isolation_manager=None) -> bool:
    """Check if frontend dev server is running"""
    try:
        import requests
        if isolation_manager and isolation_manager.ports:
            port = isolation_manager.ports.get('frontend', 3000)
        else:
            port = int(env.get('FRONTEND_PORT', 3000))
        response = requests.get(f"http://localhost:{port}", timeout=1)
        return response.status_code == 200
    except:
        return False


def start_backend():
    """Start backend server in background"""
    subprocess.Popen(
        ["python", "run_server.py"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def start_frontend():
    """Start frontend dev server in background"""
    subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def build_frontend(args) -> int:
    """Build frontend for production"""
    print("Building frontend...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=False,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=True  # Need shell=True on Windows for npm commands
    )
    return result.returncode


def run_lint(args) -> int:
    """Run ESLint"""
    print("Running ESLint...")
    lint_cmd = ["npm", "run", "lint"]
    
    if args.fix:
        lint_cmd.extend(["--", "--fix"])
    
    result = subprocess.run(
        lint_cmd,
        cwd=FRONTEND_DIR,
        capture_output=False,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=True  # Need shell=True on Windows for npm commands
    )
    return result.returncode


def run_type_check(args) -> int:
    """Run TypeScript type checking"""
    print("Running TypeScript type check...")
    result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd=FRONTEND_DIR,
        capture_output=False,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=True  # Need shell=True on Windows for npm commands
    )
    return result.returncode


def create_argument_parser():
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description="Comprehensive frontend test runner for Netra AI Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=get_usage_examples()
    )
    return parser


def get_usage_examples():
    """Get usage examples string"""
    return """
Examples:
  # Run all Jest tests
  python unified_test_runner.py --service frontend
  
  # Run specific category
  python unified_test_runner.py --service frontend --category components
  python unified_test_runner.py --service frontend --category hooks
  
  # Run with coverage
  python unified_test_runner.py --service frontend --coverage
  
  # Run E2E tests with Cypress
  python unified_test_runner.py --service frontend --e2e
  python unified_test_runner.py --service frontend --cypress-open
  
  # Run specific test file
  python unified_test_runner.py --service frontend components/Button.test.tsx
  
  # Watch mode for development
  python unified_test_runner.py --service frontend --watch
  
  # Full CI/CD run
  python unified_test_runner.py --service frontend --lint --type-check --coverage --build
        """


def add_test_selection_args(parser):
    """Add test selection arguments to parser"""
    parser.add_argument("tests", nargs="*", help="Specific test files or patterns to run")
    parser.add_argument("--category", "-c", choices=list(TEST_CATEGORIES.keys()), help="Run tests from a specific category")
    parser.add_argument("--keyword", "-k", help="Only run tests matching the given pattern")


def add_test_type_args(parser):
    """Add test type arguments to parser"""
    parser.add_argument("--e2e", action="store_true", help="Run E2E tests with Cypress")
    parser.add_argument("--cypress-open", action="store_true", help="Open Cypress interactive runner")


def add_jest_option_args(parser):
    """Add Jest option arguments to parser"""
    parser.add_argument("--watch", "-w", action="store_true", help="Run Jest in watch mode")
    parser.add_argument("--coverage", "--cov", action="store_true", help="Enable coverage reporting")
    parser.add_argument("--update-snapshots", "-u", action="store_true", help="Update Jest snapshots")


def add_additional_check_args(parser):
    """Add additional check arguments to parser"""
    parser.add_argument("--lint", "-l", action="store_true", help="Run ESLint")
    parser.add_argument("--fix", action="store_true", help="Auto-fix linting issues")
    parser.add_argument("--type-check", "-t", action="store_true", help="Run TypeScript type checking")
    parser.add_argument("--build", "-b", action="store_true", help="Build frontend for production")


def add_environment_args(parser):
    """Add environment arguments to parser"""
    parser.add_argument("--check-deps", action="store_true", help="Check test dependencies before running")
    parser.add_argument("--install-deps", action="store_true", help="Install dependencies if missing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")


def add_isolation_args(parser):
    """Add isolation arguments to parser"""
    parser.add_argument("--isolation", action="store_true", help="Use test isolation for concurrent execution")
    parser.add_argument("--cleanup-on-exit", action="store_true", help="Clean up Node processes on exit (automatic on Windows)")


def setup_isolation_manager(args):
    """Setup test isolation manager if requested"""
    if not (args.isolation and TestIsolationManager):
        return None
    manager = TestIsolationManager()
    manager.setup_environment()
    manager.apply_environment()
    manager.register_cleanup()
    return manager


def print_header():
    """Print test runner header"""
    print("=" * 80)
    print("NETRA AI PLATFORM - FRONTEND TEST RUNNER")
    print("=" * 80)


def handle_dependency_check(args):
    """Handle dependency checking if requested"""
    if not args.check_deps:
        return
    print("\nChecking dependencies...")
    deps = check_dependencies()
    for dep, available in deps.items():
        status = "[OK]" if available else "[MISSING]"
        print(f"  {status} {dep}")
    print()


def handle_dependency_install(args):
    """Handle dependency installation if needed"""
    if args.install_deps or not check_node_modules():
        if not install_dependencies(args.install_deps):
            sys.exit(1)


def execute_lint_check(args):
    """Execute linting check if requested"""
    if not args.lint:
        return 0
    print("\n" + "=" * 80)
    lint_result = run_lint(args)
    if lint_result != 0 and not args.fix:
        print("[FAIL] Linting failed. Use --fix to auto-fix issues.")
    return lint_result


def execute_type_check(args):
    """Execute type checking if requested"""
    if not args.type_check:
        return 0
    print("\n" + "=" * 80)
    type_result = run_type_check(args)
    if type_result != 0:
        print("[FAIL] Type checking failed.")
    return type_result


def execute_tests(args, isolation_manager):
    """Execute tests based on arguments"""
    if args.e2e or args.cypress_open:
        print("\n" + "=" * 80)
        print("Running Cypress E2E Tests")
        print("-" * 80)
        return run_cypress_tests(args, isolation_manager)
    else:
        print("\n" + "=" * 80)
        print("Running Jest Tests")
        print("-" * 80)
        return run_jest_tests(args, isolation_manager)


def execute_build(args):
    """Execute build if requested"""
    if not args.build:
        return 0
    print("\n" + "=" * 80)
    build_result = build_frontend(args)
    if build_result != 0:
        print("[FAIL] Build failed.")
    return build_result


def print_final_results(exit_code):
    """Print final test results"""
    print("\n" + "=" * 80)
    if exit_code == 0:
        print("[SUCCESS] ALL CHECKS PASSED")
    else:
        print(f"[FAIL] CHECKS FAILED with exit code {exit_code}")
    print("=" * 80)


def handle_cleanup(args, exit_code):
    """Handle cleanup processes if needed"""
    if not (args.cleanup_on_exit or (exit_code != 0 and sys.platform == "win32")):
        return
    cleanup_script = PROJECT_ROOT / "scripts" / "cleanup_test_processes.py"
    if cleanup_script.exists():
        try:
            print("\nCleaning up test processes...")
            subprocess.run([sys.executable, str(cleanup_script), "--force"], timeout=10, capture_output=True)
        except:
            pass


def main():
    """Main entry point for frontend test runner"""
    parser = create_argument_parser()
    add_test_selection_args(parser)
    add_test_type_args(parser)
    add_jest_option_args(parser)
    add_additional_check_args(parser)
    add_environment_args(parser)
    add_isolation_args(parser)
    args = parser.parse_args()
    
    isolation_manager = setup_isolation_manager(args)
    print_header()
    
    handle_dependency_check(args)
    handle_dependency_install(args)
    
    exit_code = 0
    exit_code = max(exit_code, execute_lint_check(args))
    exit_code = max(exit_code, execute_type_check(args))
    exit_code = max(exit_code, execute_tests(args, isolation_manager))
    exit_code = max(exit_code, execute_build(args))
    
    print_final_results(exit_code)
    handle_cleanup(args, exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()