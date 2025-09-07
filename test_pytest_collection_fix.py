"""
Test script to verify pytest collection doesn't crash Docker after fix.
Run this to confirm the fix is working.
"""
import subprocess
import sys
import os

def test_pytest_collection():
    """Test that pytest collection works without crashing Docker."""
    print("Testing pytest collection phase...")
    
    # Set environment to avoid Docker startup
    env = os.environ.copy()
    env['SKIP_DOCKER_TESTS'] = 'true'
    env['USE_REAL_SERVICES'] = 'false'
    
    # Try collecting tests without running them
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/e2e/test_real_chat_output_validation.py',
        '--collect-only',
        '-q'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        print("\n=== STDOUT ===")
        print(result.stdout)
        
        if result.stderr:
            print("\n=== STDERR ===")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n[SUCCESS] Pytest collection completed without crashing!")
            return True
        else:
            print(f"\n[FAILED] Pytest collection failed with exit code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n[FAILED] Pytest collection timed out (likely frozen)")
        return False
    except Exception as e:
        print(f"\n[FAILED] Error during pytest collection: {e}")
        return False

if __name__ == "__main__":
    success = test_pytest_collection()
    sys.exit(0 if success else 1)