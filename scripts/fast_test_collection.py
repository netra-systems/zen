#!/usr/bin/env python3
"""
Fast Test Collection Wrapper

Optimized test collection with all performance enhancements enabled.
"""
import os
import sys
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_fast_collection():
    """Run optimized test collection"""
    print("🚀 Running optimized test collection...")
    
    # Set optimization environment
    env = os.environ.copy()
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_COLLECTION_PHASE": "1"
    })
    
    start_time = time.time()
    
    # Run unified test runner with fast collection
    cmd = [
        sys.executable, "tests/unified_test_runner.py",
        "--fast-collection",
        "--quiet",
        "--collection-timeout", "60"
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute max
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ Fast collection completed in {duration:.2f}s")
            print(result.stdout.split('\n')[-2])  # Last meaningful line
            return True
        else:
            print(f"❌ Collection failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏱️  Collection timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error during collection: {e}")
        return False

def run_validation_collection():
    """Run validation collection to measure improvement"""
    print("📊 Running validation collection...")
    
    start_time = time.time()
    
    cmd = [
        sys.executable, "-m", "pytest",
        "--collect-only",
        "--quiet",
        "tests/"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            lines = result.stdout.count('\n')
            print(f"📈 Validation: {lines} tests discovered in {duration:.2f}s")
            return lines, duration
        else:
            print(f"❌ Validation failed: {result.stderr}")
            return 0, duration
            
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return 0, 0

if __name__ == "__main__":
    print("🔧 Test Collection Performance Optimization")
    print("=" * 50)
    
    # Run fast collection
    fast_success = run_fast_collection()
    
    if fast_success:
        # Run validation
        test_count, duration = run_validation_collection()
        
        print("\n📊 Performance Summary:")
        print(f"   Tests discovered: {test_count}")
        print(f"   Collection time: {duration:.2f}s")
        print(f"   Collection rate: {test_count/duration if duration > 0 else 0:.1f} tests/second")
        
        # Compare to baseline
        baseline_count = 4148  # From task description
        if test_count > baseline_count:
            improvement = test_count - baseline_count
            print(f"✅ Improvement: +{improvement} tests discovered ({improvement/baseline_count*100:.1f}% increase)")
        
    sys.exit(0 if fast_success else 1)
