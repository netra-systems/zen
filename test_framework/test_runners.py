#!/usr/bin/env python
"""
Test Runners - Core test execution functions for different test types
Handles backend, frontend, E2E, and simple test runners
"""

import atexit
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from .bad_test_detector import BadTestDetector
from .test_config import RUNNERS
from .test_parser import (
    extract_test_details,
    parse_coverage,
    parse_cypress_counts,
    parse_test_counts,
)

# Load environment variables
load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

# Track subprocesses for cleanup
_active_processes = []

def cleanup_processes():
    """Clean up any active subprocesses on exit."""
    global _active_processes
    for proc in _active_processes:
        try:
            if proc.poll() is None:  # Process is still running
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except:
            pass
    _active_processes = []

# Register cleanup on exit
atexit.register(cleanup_processes)

def handle_signal(signum, frame):
    """Handle interrupt signals."""
    cleanup_processes()
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def print_output(stdout: str, stderr: str):
    """Print output with proper encoding handling."""
    try:
        print(stdout)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Force ASCII output for Windows terminals with encoding issues
        cleaned_output = stdout.encode('ascii', errors='replace').decode('ascii')
        print(cleaned_output)
    
    if stderr:
        try:
            print(stderr, file=sys.stderr)
        except (UnicodeEncodeError, UnicodeDecodeError):
            # Force ASCII output for Windows terminals with encoding issues
            cleaned_stderr = stderr.encode('ascii', errors='replace').decode('ascii')
            print(cleaned_stderr, file=sys.stderr)


def run_backend_tests(args: List[str], timeout: int = 300, real_llm_config: Optional[Dict[str, Any]] = None, results: Dict[str, Any] = None, speed_opts: Optional[Dict[str, bool]] = None) -> Tuple[int, str]:
    """Run backend tests with specified arguments."""
    print(f"\n{'='*60}")
    print("RUNNING BACKEND TESTS")
    if speed_opts and speed_opts.get('enabled'):
        print("[SPEED] Speed optimizations active")
    print(f"{'='*60}")
    
    start_time = time.time()
    if results:
        results["backend"]["status"] = "running"
    
    # Initialize bad test detector
    bad_test_detector = BadTestDetector()
    
    # Use backend test runner
    backend_script = PROJECT_ROOT / RUNNERS["backend"]
    if not backend_script.exists():
        print(f"[ERROR] Backend test runner not found: {backend_script}")
        return 1, "Backend test runner not found"
    
    cmd = [sys.executable, str(backend_script)] + args
    
    # Apply speed optimizations if requested
    if speed_opts:
        cmd = _apply_speed_optimizations(cmd, speed_opts)
    
    # Prepare environment with real LLM configuration if provided
    env = os.environ.copy()
    if real_llm_config:
        env["TEST_USE_REAL_LLM"] = "true"
        env["ENABLE_REAL_LLM_TESTING"] = "true"
        env["TEST_LLM_TIMEOUT"] = str(real_llm_config.get("timeout", 45))
        if real_llm_config.get("parallel"):
            env["TEST_PARALLEL"] = str(real_llm_config["parallel"])
        
        # Load .env file to get API keys
        load_dotenv()
        
        # Pass through API keys from environment - Use GEMINI_API_KEY for Google services
        api_keys = ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
        for key in api_keys:
            value = os.environ.get(key)
            if value:
                env[key] = value
                # Also set GOOGLE_API_KEY to GEMINI_API_KEY value for compatibility
                if key == "GEMINI_API_KEY":
                    env["GOOGLE_API_KEY"] = value
                print(f"[INFO] Found {key} in environment")
        
        model_name = real_llm_config.get("model", "gemini-2.5-flash")
        print(f"[INFO] Real LLM testing enabled with {model_name} (timeout: {env['TEST_LLM_TIMEOUT']}s)")
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if results:
            results["backend"]["duration"] = duration
            results["backend"]["exit_code"] = result.returncode
            results["backend"]["output"] = result.stdout + "\n" + result.stderr
            results["backend"]["status"] = "passed" if result.returncode == 0 else "failed"
            
            # Parse test counts from output
            counts = parse_test_counts(result.stdout + result.stderr, "backend")
            results["backend"]["test_counts"] = counts
            
            # Extract test details for unified reporter
            test_details = extract_test_details(result.stdout + result.stderr, "backend")
            results["backend"]["test_details"] = test_details
            
            # Track bad tests
            for test in test_details:
                bad_test_detector.record_test_result(
                    test_name=test["name"],
                    component="backend",
                    status=test["status"],
                    error_type=test.get("error", "").split(":")[0] if test.get("error") else None,
                    error_message=test.get("error")
                )
            
            # Parse coverage
            coverage = parse_coverage(result.stdout + result.stderr)
            if coverage is not None:
                results["backend"]["coverage"] = coverage
        
        # Print output with proper encoding handling
        print_output(result.stdout, result.stderr)
        
        print(f"[{'PASS' if result.returncode == 0 else 'FAIL'}] Backend tests completed in {duration:.2f}s")
        
        # Finalize bad test detection and show report if needed
        if results and "test_counts" in results["backend"]:
            bad_tests = bad_test_detector.finalize_run(
                total_tests=results["backend"]["test_counts"]["total"],
                passed=results["backend"]["test_counts"]["passed"],
                failed=results["backend"]["test_counts"]["failed"]
            )
            
            # Show warning if bad tests detected
            if bad_tests["consistently_failing"]:
                print(f"\n⚠️  WARNING: {len(bad_tests['consistently_failing'])} tests are consistently failing!")
                print("Run 'python -m test_framework.bad_test_reporter' for detailed report")
        
        return result.returncode, result.stdout + result.stderr
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        if results:
            results["backend"]["duration"] = duration
            results["backend"]["exit_code"] = -1
            results["backend"]["status"] = "timeout"
            results["backend"]["output"] = f"Tests timed out after {timeout}s"
        
        print(f"[TIMEOUT] Backend tests timed out after {timeout}s")
        return -1, f"Tests timed out after {timeout}s"


def run_frontend_tests(args: List[str], timeout: int = 300, results: Dict[str, Any] = None, speed_opts: Optional[Dict[str, bool]] = None, test_level: str = None) -> Tuple[int, str]:
    """Run frontend tests with specified arguments."""
    global _active_processes
    
    print(f"\n{'='*60}")
    print("RUNNING FRONTEND TESTS")
    if speed_opts and speed_opts.get('enabled'):
        print("[SPEED] Speed optimizations active")
    print(f"{'='*60}")
    
    start_time = time.time()
    if results:
        results["frontend"]["status"] = "running"
    
    # Determine if we should use simple frontend runner (for smoke tests or when no args)
    use_simple_runner = (len(args) == 0 or ("--category" in args and "smoke" in str(args)))
    
    if use_simple_runner:
        timeout = min(timeout, 60)  # Cap smoke tests at 60 seconds
        frontend_script = PROJECT_ROOT / "scripts" / "test_frontend_simple.py"
        # For simple runner, we need to pass the test level
        if test_level and len(args) == 0:
            args = ["--level", test_level]
    else:
        frontend_script = PROJECT_ROOT / RUNNERS["frontend"]
        
    if not frontend_script.exists():
        print(f"[ERROR] Frontend test runner not found: {frontend_script}")
        return 1, "Frontend test runner not found"
        
    cmd = [sys.executable, str(frontend_script)] + args
    
    # Apply speed optimizations if requested
    if speed_opts:
        cmd = _apply_speed_optimizations(cmd, speed_opts)
    
    # Add cleanup flag for frontend tests only if script supports it
    if "test_frontend.py" in str(frontend_script):
        cmd.append("--cleanup-on-exit")
    
    try:
        # Use Popen for better process control
        process = subprocess.Popen(
            cmd, 
            cwd=PROJECT_ROOT, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Track the process for cleanup
        _active_processes.append(process)
        
        # Wait for completion with timeout
        stdout, stderr = process.communicate(timeout=timeout)
        result_code = process.returncode
        
        # Remove from active processes
        if process in _active_processes:
            _active_processes.remove(process)
        
        duration = time.time() - start_time
        output = stdout + "\n" + stderr
        
        if results:
            results["frontend"]["duration"] = duration
            results["frontend"]["exit_code"] = result_code
            results["frontend"]["output"] = output
            results["frontend"]["status"] = "passed" if result_code == 0 else "failed"
            
            # Parse test counts from output
            counts = parse_test_counts(output, "frontend")
            results["frontend"]["test_counts"] = counts
            
            # Extract test details for unified reporter
            test_details = extract_test_details(output, "frontend")
            results["frontend"]["test_details"] = test_details
            
            # Parse coverage
            coverage = parse_coverage(output)
            if coverage is not None:
                results["frontend"]["coverage"] = coverage
        
        # Print output with proper encoding handling
        print_output(stdout, stderr)
        
        print(f"[{'PASS' if result_code == 0 else 'FAIL'}] Frontend tests completed in {duration:.2f}s")
        
        return result_code, output
        
    except subprocess.TimeoutExpired:
        # Kill the process and its children
        try:
            process.kill()
            process.wait(timeout=5)
        except:
            pass
        
        # Remove from active processes
        if process in _active_processes:
            _active_processes.remove(process)
        
        duration = time.time() - start_time
        if results:
            results["frontend"]["duration"] = duration
            results["frontend"]["exit_code"] = -1
            results["frontend"]["status"] = "timeout"
            results["frontend"]["output"] = f"Tests timed out after {timeout}s"
        
        print(f"[TIMEOUT] Frontend tests timed out after {timeout}s")
        
        # Run cleanup script to kill any hanging Node processes
        cleanup_script = PROJECT_ROOT / "scripts" / "cleanup_test_processes.py"
        if cleanup_script.exists():
            try:
                subprocess.run([sys.executable, str(cleanup_script), "--force"], 
                             timeout=10, capture_output=True)
            except:
                pass
        
        return -1, f"Tests timed out after {timeout}s"


def run_e2e_tests(args: List[str], timeout: int = 600, results: Dict[str, Any] = None) -> Tuple[int, str]:
    """Run end-to-end Cypress tests."""
    print(f"\n{'='*60}")
    print("RUNNING E2E TESTS")
    print(f"{'='*60}")
    
    start_time = time.time()
    if results:
        results["e2e"]["status"] = "running"
    
    # Change to frontend directory for Cypress
    frontend_dir = PROJECT_ROOT / "frontend"
    
    # Check if npm and cypress are available
    check_cmd = ["npm", "list", "cypress", "--depth=0"]
    try:
        subprocess.run(check_cmd, cwd=frontend_dir, capture_output=True, timeout=10)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("[ERROR] Cypress not found. Please run 'npm install' in frontend directory")
        if results:
            results["e2e"]["status"] = "failed"
            results["e2e"]["exit_code"] = 1
        return 1, "Cypress not installed"
    
    # Run Cypress tests
    cmd = ["npm", "run", "cy:run", "--", "--reporter", "json"]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if results:
            results["e2e"]["duration"] = duration
            results["e2e"]["exit_code"] = result.returncode
            results["e2e"]["output"] = result.stdout + "\n" + result.stderr
            results["e2e"]["status"] = "passed" if result.returncode == 0 else "failed"
            
            # Parse test counts from Cypress output
            counts = parse_cypress_counts(result.stdout + result.stderr)
            results["e2e"]["test_counts"] = counts
            
            # Extract test details for unified reporter
            test_details = extract_test_details(result.stdout + result.stderr, "e2e")
            results["e2e"]["test_details"] = test_details
        
        # Print output with proper encoding handling
        print_output(result.stdout, result.stderr)
        
        print(f"[{'PASS' if result.returncode == 0 else 'FAIL'}] E2E tests completed in {duration:.2f}s")
        
        return result.returncode, result.stdout + result.stderr
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        if results:
            results["e2e"]["duration"] = duration
            results["e2e"]["exit_code"] = -1
            results["e2e"]["status"] = "timeout"
            results["e2e"]["output"] = f"Tests timed out after {timeout}s"
        
        print(f"[TIMEOUT] E2E tests timed out after {timeout}s")
        return -1, f"Tests timed out after {timeout}s"


def run_simple_tests(results: Dict[str, Any] = None) -> Tuple[int, str]:
    """Run simple test runner for basic validation."""
    print(f"\n{'='*60}")
    print("RUNNING SIMPLE TESTS")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Use simple test runner
    simple_script = PROJECT_ROOT / RUNNERS["simple"]
    if not simple_script.exists():
        print(f"[ERROR] Simple test runner not found: {simple_script}")
        return 1, "Simple test runner not found"
        
    cmd = [sys.executable, str(simple_script)]
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=PROJECT_ROOT, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60
        )
        
        duration = time.time() - start_time
        
        if results:
            # Update results for both backend and frontend
            results["backend"]["duration"] = duration / 2
            results["backend"]["exit_code"] = result.returncode
            results["backend"]["status"] = "passed" if result.returncode == 0 else "failed"
            results["backend"]["output"] = result.stdout + "\n" + result.stderr
            results["frontend"]["duration"] = duration / 2  
            results["frontend"]["exit_code"] = result.returncode
            results["frontend"]["status"] = "passed" if result.returncode == 0 else "failed"
            results["frontend"]["output"] = ""
            
            # Parse test counts from output
            counts = parse_test_counts(result.stdout + result.stderr, "backend")
            results["backend"]["test_counts"] = counts
        
        # Print output with proper encoding handling
        print_output(result.stdout, result.stderr)
        
        print(f"[{'PASS' if result.returncode == 0 else 'FAIL'}] Simple tests completed in {duration:.2f}s")
        
        return result.returncode, result.stdout + result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Simple tests timed out after 60s")
        return -1, "Tests timed out after 60s"


def _apply_speed_optimizations(cmd: List[str], speed_opts: Dict[str, bool]) -> List[str]:
    """Apply speed optimizations to test command.
    
    SAFETY ANALYSIS:
    - no_warnings: Safe - only suppresses deprecation warnings
    - no_coverage: Safe - skips coverage but doesn't affect test results
    - fast_fail: Safe - stops on first failure, useful for quick feedback
    - parallel: Safe with caveats - may hide race conditions
    - skip_slow: RISKY - may skip important tests, requires explicit flag
    """
    optimized_cmd = cmd.copy()
    
    # Check what type of test runner we're using
    is_backend_runner = any('test_backend.py' in str(c) for c in cmd)
    is_frontend_simple_runner = any('test_frontend_simple.py' in str(c) for c in cmd)
    is_frontend_runner = any('test_frontend.py' in str(c) for c in cmd)
    
    if is_backend_runner:
        # Backend runner has specific flags
        if speed_opts.get('fast_fail', False):
            optimized_cmd.append('--fail-fast')
        
        if speed_opts.get('parallel', False):
            # Backend runner uses --parallel flag with number
            optimized_cmd.extend(['--parallel', 'auto'])
        
        if speed_opts.get('no_warnings', False):
            # Backend runner doesn't show warnings by default
            pass  # No specific flag needed
        
        if speed_opts.get('no_coverage', False):
            # Remove any existing --coverage flags and add --no-coverage
            optimized_cmd = [arg for arg in optimized_cmd if arg != '--coverage' and arg != '--cov']
            # Backend runner doesn't have --no-coverage flag, so we remove --coverage instead
            # This effectively disables coverage collection
        
        # Backend runner doesn't have direct skip slow support
        # Would need to use --markers flag
    elif is_frontend_simple_runner:
        # Simple frontend runner only accepts --level and additional args
        # Don't add any speed optimization flags as they're not supported
        pass
    elif is_frontend_runner:
        # Full frontend runner supports more options
        if speed_opts.get('fast_fail', False):
            # Frontend runner might support some Jest options
            pass  # Would need to check what's supported
    else:
        # Standard pytest flags for other runners
        if speed_opts.get('no_warnings', False):
            optimized_cmd.extend(['-W', 'ignore::DeprecationWarning'])
            optimized_cmd.extend(['-W', 'ignore::PendingDeprecationWarning'])
        
        if speed_opts.get('no_coverage', False):
            # Skip coverage collection
            optimized_cmd.extend(['--no-cov'])
        
        if speed_opts.get('fast_fail', False):
            # Stop on first failure
            optimized_cmd.extend(['-x', '--maxfail=1'])
        
        # Potentially risky optimizations (require explicit flag)
        if speed_opts.get('skip_slow', False):
            # Skip tests marked as slow - REQUIRES WARNING
            print("[WARNING] Skipping slow tests - may miss important edge cases!")
            optimized_cmd.extend(['-m', 'not slow'])
        
        if speed_opts.get('parallel', False) and '-n' not in ' '.join(optimized_cmd):
            # Auto-detect CPU count for parallel execution
            optimized_cmd.extend(['-n', 'auto'])
    
    return optimized_cmd