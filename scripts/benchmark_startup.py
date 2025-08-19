#!/usr/bin/env python3
"""
Benchmark startup performance improvements.

Business Value: Validates productivity improvements to justify
development time investment.
"""

import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def measure_startup(command: List[str], name: str, 
                   timeout: int = 60) -> float:
    """Measure startup time for a command."""
    print(f"Measuring {name}...")
    start = time.time()
    
    try:
        # Start process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for "READY" or similar indicator
        ready_indicators = [
            "All services started",
            "Development environment ready",
            "READY",
            "Frontend ready at"
        ]
        
        while time.time() - start < timeout:
            line = process.stdout.readline()
            if any(indicator in line for indicator in ready_indicators):
                elapsed = time.time() - start
                process.terminate()
                return elapsed
        
        # Timeout
        process.terminate()
        return timeout
        
    except Exception as e:
        print(f"Error: {e}")
        return -1


def run_benchmark() -> Dict[str, float]:
    """Run startup benchmarks."""
    results = {}
    project_root = Path(__file__).parent.parent
    
    # Test configurations
    tests = [
        {
            "name": "Traditional Launcher",
            "command": [sys.executable, "scripts/dev_launcher.py", 
                       "--no-browser", "--non-interactive"]
        },
        {
            "name": "Fast Dev (Cold)",
            "command": [sys.executable, "scripts/fast_dev.py", 
                       "--fresh", "--skip-checks"]
        },
        {
            "name": "Fast Dev (Warm)",
            "command": [sys.executable, "scripts/fast_dev.py", 
                       "--skip-checks"]
        },
        {
            "name": "Fast Dev (Minimal)",
            "command": [sys.executable, "scripts/fast_dev.py", 
                       "--minimal", "--skip-checks"]
        }
    ]
    
    # Run benchmarks
    for test in tests:
        time_taken = measure_startup(test["command"], test["name"])
        if time_taken > 0:
            results[test["name"]] = time_taken
    
    return results


def show_results(results: Dict[str, float]):
    """Display benchmark results."""
    print("\n" + "=" * 60)
    print("STARTUP BENCHMARK RESULTS")
    print("=" * 60)
    
    if not results:
        print("No results collected")
        return
    
    # Find baseline
    baseline = results.get("Traditional Launcher", 0)
    
    # Show results
    for name, time_taken in sorted(results.items(), 
                                  key=lambda x: x[1]):
        if baseline and time_taken != baseline:
            improvement = ((baseline - time_taken) / baseline) * 100
            print(f"{name:25} : {time_taken:6.1f}s "
                  f"({improvement:+.0f}% vs baseline)")
        else:
            print(f"{name:25} : {time_taken:6.1f}s (baseline)")
    
    print("=" * 60)
    
    # Show summary
    if len(results) > 1:
        avg_improvement = sum(
            ((baseline - t) / baseline * 100) 
            for n, t in results.items() 
            if n != "Traditional Launcher" and baseline > 0
        ) / (len(results) - 1)
        
        print(f"\nAverage Improvement: {avg_improvement:.0f}%")
        
        fastest = min(results.items(), key=lambda x: x[1])
        print(f"Fastest: {fastest[0]} ({fastest[1]:.1f}s)")


def main():
    """Run benchmarks."""
    print("=" * 60)
    print("DEV STARTUP PERFORMANCE BENCHMARK")
    print("=" * 60)
    print("\nThis will start and stop services multiple times.")
    print("Please ensure no dev services are currently running.\n")
    
    try:
        results = run_benchmark()
        show_results(results)
    except KeyboardInterrupt:
        print("\nBenchmark cancelled")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())