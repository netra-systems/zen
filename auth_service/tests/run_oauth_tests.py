"""
OAuth Tests Runner
Runs comprehensive OAuth flow tests for auth service
"""
import os
import sys
import subprocess
import asyncio
from pathlib import Path

# Add auth service to Python path
auth_service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(auth_service_dir))

def run_tests():
    """Run OAuth tests with proper configuration"""
    # Set test environment
    os.environ["ENVIRONMENT"] = "test"
    os.environ["PYTHONPATH"] = str(auth_service_dir)
    
    # Test commands
    commands = [
        # Run unit tests
        [
            "python", "-m", "pytest",
            "tests/unit/test_oauth_models.py",
            "-v", "--tb=short"
        ],
        # Run integration tests
        [
            "python", "-m", "pytest", 
            "tests/integration/test_oauth_flows.py",
            "-v", "--tb=short", "-x"
        ],
        # Run with coverage
        [
            "python", "-m", "pytest",
            "tests/",
            "--cov=auth_core",
            "--cov-report=html",
            "--cov-report=term-missing"
        ]
    ]
    
    results = []
    for i, cmd in enumerate(commands, 1):
        print(f"\n{'='*60}")
        print(f"Running test suite {i}/{len(commands)}: {' '.join(cmd[3:])}")
        print('='*60)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=auth_service_dir,
                capture_output=False,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            results.append((cmd, result.returncode))
            
            if result.returncode != 0:
                print(f"[FAIL] Test suite {i} failed with exit code {result.returncode}")
            else:
                print(f"✅ Test suite {i} passed")
                
        except subprocess.TimeoutExpired:
            print(f"[FAIL] Test suite {i} timed out after 5 minutes")
            results.append((cmd, -1))
        except Exception as e:
            print(f"[FAIL] Test suite {i} failed with error: {e}")
            results.append((cmd, -1))
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    all_passed = True
    for i, (cmd, returncode) in enumerate(results, 1):
        status = "✅ PASSED" if returncode == 0 else "[FAIL] FAILED"
        print(f"Suite {i}: {status} - {' '.join(cmd[3:])}")
        if returncode != 0:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All OAuth tests passed!")
        return 0
    else:
        print("\n💥 Some OAuth tests failed!")
        return 1

def check_dependencies():
    """Check if test dependencies are installed"""
    try:
        import pytest
        import httpx
        import fastapi
        print("✅ Test dependencies available")
        return True
    except ImportError as e:
        print(f"[FAIL] Missing test dependency: {e}")
        print("Install with: pip install -r tests/requirements-test.txt")
        return False

def main():
    """Main test runner"""
    print("Auth Service OAuth Tests Runner")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Change to auth service directory
    os.chdir(auth_service_dir)
    
    # Run tests
    return run_tests()

if __name__ == "__main__":
    sys.exit(main())