#!/usr/bin/env python3
"""
Critical E2E Test Runner
Run the critical authentication and service health tests to capture errors
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"Running critical E2E tests...")
print("=" * 60)

# Test commands to try
test_commands = [
    # Try unified test runner with e2e_critical category
    ["python", "tests/unified_test_runner.py", "--category", "e2e_critical", "-v"],
    
    # Try pytest directly on the critical test files
    ["python", "-m", "pytest", "tests/e2e/critical/test_auth_jwt_critical.py", "-v", "--tb=short", "-x"],
    ["python", "-m", "pytest", "tests/e2e/critical/test_service_health_critical.py", "-v", "--tb=short", "-x"],
    
    # Try running individual test classes
    ["python", "-m", "pytest", "tests/e2e/critical/test_auth_jwt_critical.py::CriticalJWTAuthenticationTests::test_jwt_token_generation_works", "-v", "--tb=short"],
]

def run_command(cmd):
    """Run a command and capture output"""
    print(f"\n🔧 Running command: {' '.join(cmd)}")
    print("-" * 40)
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=PROJECT_ROOT,
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minute timeout
        )
        
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
            
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        return result.returncode, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print("❌ Command timed out after 5 minutes")
        return -1, "", "Command timed out"
        
    except Exception as e:
        print(f"❌ Command execution failed: {e}")
        return -1, "", str(e)

# Execute all test commands and collect results
results = []
for i, cmd in enumerate(test_commands):
    print(f"\n{'='*60}")
    print(f"TEST ATTEMPT {i+1}/{len(test_commands)}")
    print(f"{'='*60}")
    
    return_code, stdout, stderr = run_command(cmd)
    
    results.append({
        'command': ' '.join(cmd),
        'return_code': return_code,
        'stdout': stdout,
        'stderr': stderr
    })
    
    # If command succeeds, we can break early
    if return_code == 0:
        print("✅ Command succeeded!")
        break
    else:
        print(f"❌ Command failed with return code: {return_code}")

# Summary report
print(f"\n{'='*60}")
print("SUMMARY REPORT")
print(f"{'='*60}")

for i, result in enumerate(results):
    print(f"\nCommand {i+1}: {result['command']}")
    print(f"Return code: {result['return_code']}")
    
    if result['return_code'] == 0:
        print("✅ SUCCESS")
    else:
        print("❌ FAILED")
        if result['stderr']:
            print("Key errors:")
            # Extract key error lines
            error_lines = result['stderr'].split('\n')
            for line in error_lines:
                if any(keyword in line.lower() for keyword in ['error', 'import', 'module', 'exception', 'traceback']):
                    print(f"  - {line.strip()}")

print(f"\n{'='*60}")
print("DETAILED ERROR ANALYSIS")
print(f"{'='*60}")

for i, result in enumerate(results):
    if result['return_code'] != 0:
        print(f"\nFAILED COMMAND {i+1}: {result['command']}")
        print(f"Full stderr:")
        print(result['stderr'])
        print(f"Full stdout:")
        print(result['stdout'])
        print("-" * 40)