"""Test execution utilities."""

import sys
import os
import subprocess
import time
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any
from dotenv import load_dotenv

from .test_config import RUNNERS
from .test_parser import parse_test_counts, parse_coverage, extract_failing_tests, parse_cypress_counts

# Load environment variables
load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

def run_backend_tests(args: List[str], timeout: int = 300, real_llm_config: Optional[Dict[str, Any]] = None, results: Dict[str, Any] = None) -> Tuple[int, str]:
    """Run backend tests with specified arguments."""
    print(f"\n{'='*60}")
    print("RUNNING BACKEND TESTS")
    print(f"{'='*60}")
    
    start_time = time.time()
    if results:
        results["backend"]["status"] = "running"
    
    # Use backend test runner
    backend_script = PROJECT_ROOT / RUNNERS["backend"]
    if not backend_script.exists():
        print(f"[ERROR] Backend test runner not found: {backend_script}")
        return 1, "Backend test runner not found"
    
    cmd = [sys.executable, str(backend_script)] + args
    
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
            
            # Parse coverage
            coverage = parse_coverage(result.stdout + result.stderr)
            if coverage is not None:
                results["backend"]["coverage"] = coverage
        
        # Print output with proper encoding handling
        print_output(result.stdout, result.stderr)
        
        print(f"[{'PASS' if result.returncode == 0 else 'FAIL'}] Backend tests completed in {duration:.2f}s")
        
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

def run_frontend_tests(args: List[str], timeout: int = 300, results: Dict[str, Any] = None) -> Tuple[int, str]:
    """Run frontend tests with specified arguments."""
    print(f"\n{'='*60}")
    print("RUNNING FRONTEND TESTS")
    print(f"{'='*60}")
    
    start_time = time.time()
    if results:
        results["frontend"]["status"] = "running"
    
    # Adjust timeout for smoke tests - they should be fast
    if len(args) == 0 or ("--category" in args and "smoke" in str(args)):
        timeout = min(timeout, 60)  # Cap smoke tests at 60 seconds
        frontend_script = PROJECT_ROOT / "scripts" / "test_frontend_simple.py"
    else:
        frontend_script = PROJECT_ROOT / RUNNERS["frontend"]
        
    if not frontend_script.exists():
        print(f"[ERROR] Frontend test runner not found: {frontend_script}")
        return 1, "Frontend test runner not found"
        
    cmd = [sys.executable, str(frontend_script)] + args
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=PROJECT_ROOT, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if results:
            results["frontend"]["duration"] = duration
            results["frontend"]["exit_code"] = result.returncode
            results["frontend"]["output"] = result.stdout + "\n" + result.stderr
            results["frontend"]["status"] = "passed" if result.returncode == 0 else "failed"
            
            # Parse test counts from output
            counts = parse_test_counts(result.stdout + result.stderr, "frontend")
            results["frontend"]["test_counts"] = counts
            
            # Parse coverage
            coverage = parse_coverage(result.stdout + result.stderr)
            if coverage is not None:
                results["frontend"]["coverage"] = coverage
        
        # Print output with proper encoding handling
        print_output(result.stdout, result.stderr)
        
        print(f"[{'PASS' if result.returncode == 0 else 'FAIL'}] Frontend tests completed in {duration:.2f}s")
        
        return result.returncode, result.stdout + result.stderr
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        if results:
            results["frontend"]["duration"] = duration
            results["frontend"]["exit_code"] = -1
            results["frontend"]["status"] = "timeout"
            results["frontend"]["output"] = f"Tests timed out after {timeout}s"
        
        print(f"[TIMEOUT] Frontend tests timed out after {timeout}s")
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

def run_failing_tests(failing_tests: Dict, max_fixes: int = None, backend_only: bool = False, frontend_only: bool = False) -> int:
    """Run only the currently failing tests."""
    total_failures = 0
    fixed_count = 0
    
    # Run backend failing tests
    if not frontend_only and failing_tests["backend"]["count"] > 0:
        print(f"\n[FAILING TESTS] Running {failing_tests['backend']['count']} failing backend tests...")
        
        for failure in failing_tests["backend"]["failures"][:max_fixes]:
            test_spec = f"{failure['test_path']}::{failure['test_name']}"
            print(f"  Testing: {test_spec}")
            
            cmd = [sys.executable, "-m", "pytest", test_spec, "-xvs"]
            result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"    ✓ FIXED: {failure['test_name']}")
                fixed_count += 1
            else:
                print(f"    ✗ Still failing: {failure['test_name']}")
                total_failures += 1
    
    # Run frontend failing tests  
    if not backend_only and failing_tests["frontend"]["count"] > 0:
        print(f"\n[FAILING TESTS] Running {failing_tests['frontend']['count']} failing frontend tests...")
        
        for failure in failing_tests["frontend"]["failures"][:max_fixes]:
            print(f"  Testing: {failure['test_path']} - {failure['test_name']}")
            
            # Run specific Jest test
            cmd = ["npm", "test", "--", failure["test_path"], "--testNamePattern", failure["test_name"]]
            result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"    ✓ FIXED: {failure['test_name']}")
                fixed_count += 1
            else:
                print(f"    ✗ Still failing: {failure['test_name']}")
                total_failures += 1
    
    print(f"\n[SUMMARY] Fixed {fixed_count} tests, {total_failures} still failing")
    return total_failures

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
            cleaned_error = stderr.encode('ascii', errors='replace').decode('ascii')
            print(cleaned_error, file=sys.stderr)