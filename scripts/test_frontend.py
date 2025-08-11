#!/usr/bin/env python
"""
Comprehensive frontend test runner for Netra AI Platform
Designed for easy use by Claude Code and CI/CD pipelines
Now with test isolation support for concurrent execution
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional, Dict

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
sys.path.insert(0, str(PROJECT_ROOT))

# Import test isolation utilities
try:
    from scripts.test_isolation import TestIsolationManager
except ImportError:
    TestIsolationManager = None

# Test categories for organized testing
TEST_CATEGORIES = {
    "unit": ["__tests__/unit", "components/**/*.test.tsx", "hooks/**/*.test.ts"],
    "integration": ["__tests__/integration", "__tests__/api"],
    "components": ["components/**/*.test.tsx", "__tests__/components"],
    "hooks": ["hooks/**/*.test.ts", "__tests__/hooks"],
    "store": ["store/**/*.test.ts", "__tests__/store"],
    "websocket": ["__tests__/websocket", "providers/**/*WebSocket*.test.tsx"],
    "auth": ["__tests__/auth", "auth/**/*.test.ts"],
    "e2e": ["cypress/e2e"],
    "smoke": ["__tests__/smoke", "__tests__/critical"],
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
            text=True
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
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            status["node"] = True
    except:
        pass
    
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
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
    jest_args = ["npm", "run", "test"]
    
    # Add Jest-specific arguments
    if args.coverage:
        jest_args.extend(["--", "--coverage"])
        if isolation_manager and isolation_manager.directories:
            coverage_dir = isolation_manager.directories.get('frontend_coverage')
            jest_args.extend([f"--coverageDirectory={coverage_dir}"])
        else:
            jest_args.extend(["--coverageDirectory=../reports/frontend-coverage"])
    
    if args.watch:
        jest_args.extend(["--", "--watch"])
    
    if args.update_snapshots:
        jest_args.extend(["--", "--updateSnapshot"])
    
    if args.verbose:
        jest_args.extend(["--", "--verbose"])
    
    if args.keyword:
        jest_args.extend(["--", f"--testNamePattern={args.keyword}"])
    
    # Add isolation-specific Jest arguments
    if isolation_manager:
        isolation_args = isolation_manager.get_jest_args()
        # Only add cache directory arg as other args are already handled
        for arg in isolation_args:
            if "--cacheDirectory" in arg:
                jest_args.extend([arg])
    
    if args.tests:
        jest_args.extend(["--"] + args.tests)
    elif args.category and args.category != "e2e":
        patterns = TEST_CATEGORIES.get(args.category, [])
        jest_args.extend(["--"] + patterns)
    
    # Run Jest
    print(f"Running: {' '.join(jest_args)}")
    print("-" * 80)
    
    result = subprocess.run(
        jest_args,
        cwd=FRONTEND_DIR,
        capture_output=False,
        text=True
    )
    
    return result.returncode


def run_cypress_tests(args, isolation_manager=None) -> int:
    """Run Cypress E2E tests"""
    # Check if backend is running
    backend_running = check_backend_running(isolation_manager)
    frontend_running = check_frontend_running(isolation_manager)
    
    if not backend_running:
        print("⚠️  Backend server is not running. Starting it...")
        start_backend()
        # Removed unnecessary sleep  # Give backend time to start
    
    if not frontend_running:
        print("⚠️  Frontend dev server is not running. Starting it...")
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
        text=True
    )
    
    return result.returncode


def check_backend_running(isolation_manager=None) -> bool:
    """Check if backend server is running"""
    try:
        import requests
        if isolation_manager and isolation_manager.ports:
            port = isolation_manager.ports.get('backend', 8000)
        else:
            port = int(os.environ.get('BACKEND_PORT', 8000))
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
            port = int(os.environ.get('FRONTEND_PORT', 3000))
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
        text=True
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
        text=True
    )
    return result.returncode


def run_type_check(args) -> int:
    """Run TypeScript type checking"""
    print("Running TypeScript type check...")
    result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd=FRONTEND_DIR,
        capture_output=False,
        text=True
    )
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive frontend test runner for Netra AI Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all Jest tests
  python scripts/test_frontend.py
  
  # Run specific category
  python scripts/test_frontend.py --category components
  python scripts/test_frontend.py --category hooks
  
  # Run with coverage
  python scripts/test_frontend.py --coverage
  
  # Run E2E tests with Cypress
  python scripts/test_frontend.py --e2e
  python scripts/test_frontend.py --cypress-open
  
  # Run specific test file
  python scripts/test_frontend.py components/Button.test.tsx
  
  # Watch mode for development
  python scripts/test_frontend.py --watch
  
  # Full CI/CD run
  python scripts/test_frontend.py --lint --type-check --coverage --build
        """
    )
    
    # Test selection
    parser.add_argument(
        "tests",
        nargs="*",
        help="Specific test files or patterns to run"
    )
    parser.add_argument(
        "--category", "-c",
        choices=list(TEST_CATEGORIES.keys()),
        help="Run tests from a specific category"
    )
    parser.add_argument(
        "--keyword", "-k",
        help="Only run tests matching the given pattern"
    )
    
    # Test types
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Run E2E tests with Cypress"
    )
    parser.add_argument(
        "--cypress-open",
        action="store_true",
        help="Open Cypress interactive runner"
    )
    
    # Jest options
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Run Jest in watch mode"
    )
    parser.add_argument(
        "--coverage", "--cov",
        action="store_true",
        help="Enable coverage reporting"
    )
    parser.add_argument(
        "--update-snapshots", "-u",
        action="store_true",
        help="Update Jest snapshots"
    )
    
    # Additional checks
    parser.add_argument(
        "--lint", "-l",
        action="store_true",
        help="Run ESLint"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix linting issues"
    )
    parser.add_argument(
        "--type-check", "-t",
        action="store_true",
        help="Run TypeScript type checking"
    )
    parser.add_argument(
        "--build", "-b",
        action="store_true",
        help="Build frontend for production"
    )
    
    # Environment options
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check test dependencies before running"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies if missing"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    # Isolation options
    parser.add_argument(
        "--isolation",
        action="store_true",
        help="Use test isolation for concurrent execution"
    )
    
    args = parser.parse_args()
    
    # Setup test isolation if requested
    isolation_manager = None
    if args.isolation and TestIsolationManager:
        isolation_manager = TestIsolationManager()
        isolation_manager.setup_environment()
        isolation_manager.apply_environment()
        isolation_manager.register_cleanup()
    
    print("=" * 80)
    print("NETRA AI PLATFORM - FRONTEND TEST RUNNER")
    print("=" * 80)
    
    # Check dependencies
    if args.check_deps:
        print("\nChecking dependencies...")
        deps = check_dependencies()
        for dep, available in deps.items():
            status = "✅" if available else "❌"
            print(f"  {status} {dep}")
        print()
    
    # Install dependencies if needed
    if args.install_deps or not check_node_modules():
        if not install_dependencies(args.install_deps):
            sys.exit(1)
    
    # Track overall exit code
    exit_code = 0
    
    # Run linting if requested
    if args.lint:
        print("\n" + "=" * 80)
        lint_result = run_lint(args)
        if lint_result != 0:
            exit_code = lint_result
            if not args.fix:
                print("❌ Linting failed. Use --fix to auto-fix issues.")
    
    # Run type checking if requested
    if args.type_check:
        print("\n" + "=" * 80)
        type_result = run_type_check(args)
        if type_result != 0:
            exit_code = type_result
            print("❌ Type checking failed.")
    
    # Run tests
    if args.e2e or args.cypress_open:
        print("\n" + "=" * 80)
        print("Running Cypress E2E Tests")
        print("-" * 80)
        test_result = run_cypress_tests(args, isolation_manager)
    else:
        print("\n" + "=" * 80)
        print("Running Jest Tests")
        print("-" * 80)
        test_result = run_jest_tests(args, isolation_manager)
    
    if test_result != 0:
        exit_code = test_result
    
    # Build if requested
    if args.build:
        print("\n" + "=" * 80)
        build_result = build_frontend(args)
        if build_result != 0:
            exit_code = build_result
            print("❌ Build failed.")
    
    # Final results
    print("\n" + "=" * 80)
    if exit_code == 0:
        print("✅ ALL CHECKS PASSED")
    else:
        print(f"❌ CHECKS FAILED with exit code {exit_code}")
    print("=" * 80)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()