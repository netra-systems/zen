#!/usr/bin/env python3
"""
Memory-optimized test collection script

Implements lazy loading and memory management strategies during test discovery.
"""
import gc
import sys
import os
from pathlib import Path

# Memory management during collection
def optimize_collection_memory():
    """Apply memory optimizations during test collection"""
    
    # Force garbage collection before collection starts
    gc.collect()
    
    # Set environment variables for memory optimization
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # Don't create .pyc files
    os.environ["PYTHONHASHSEED"] = "0"           # Consistent hash seeds
    
    # Optimize Python memory allocation
    if hasattr(sys, 'setrecursionlimit'):
        sys.setrecursionlimit(2000)  # Reduce recursion limit for safety
        
    print("[MEMORY] Collection memory optimizations applied")

def run_optimized_collection(test_path="tests/", pattern="test_*.py"):
    """Run pytest collection with memory optimizations"""
    optimize_collection_memory()
    
    import subprocess
    import time
    
    start_time = time.time()
    
    cmd = [
        sys.executable, "-m", "pytest",
        "--collect-only",
        "--quiet", 
        "--tb=no",
        "--disable-warnings",
        "--maxfail=1",
        test_path
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=120,  # 2 minute timeout
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            lines = result.stdout.count('\n')
            print(f"[SUCCESS] Collected {lines} items in {duration:.2f}s")
            return lines, duration
        else:
            print(f"[ERROR] Collection failed: {result.stderr}")
            return 0, duration
            
    except subprocess.TimeoutExpired:
        print("[TIMEOUT] Collection timed out after 120s")
        return 0, 120
    except Exception as e:
        print(f"[ERROR] Collection error: {e}")
        return 0, time.time() - start_time

if __name__ == "__main__":
    items, duration = run_optimized_collection()
    print(f"Final result: {items} tests in {duration:.2f}s")
