#!/usr/bin/env python3
"""
Minimal soak test monitoring validation
Tests the monitoring framework without long-duration execution
"""

import asyncio
import time
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the monitoring components from the soak test
from tests.e2e.test_soak_testing import ResourceMonitor, SOAK_CONFIG

async def test_monitoring_framework():
    """Test the resource monitoring framework with short duration."""
    print("Testing resource monitoring framework...")
    
    monitor = ResourceMonitor(monitoring_interval=2)  # Monitor every 2 seconds
    
    try:
        print("Starting monitoring...")
        monitor.start_monitoring()
        
        # Let it monitor for 10 seconds
        await asyncio.sleep(10)
        
        print("Stopping monitoring...")
        monitor.stop_monitoring()
        
        # Analyze collected data
        snapshots = monitor.snapshots
        print(f"Collected {len(snapshots)} snapshots")
        
        if snapshots:
            first_snapshot = snapshots[0]
            last_snapshot = snapshots[-1]
            
            print(f"First snapshot: {first_snapshot.memory_usage_mb:.1f} MB")
            print(f"Last snapshot: {last_snapshot.memory_usage_mb:.1f} MB")
            print(f"Memory difference: {last_snapshot.memory_usage_mb - first_snapshot.memory_usage_mb:.1f} MB")
            
            # Test memory leak analysis
            leak_detected, analysis = monitor.analyze_memory_leaks()
            print(f"Memory leak detected: {leak_detected}")
            print(f"Analysis: {analysis}")
            
        print("PASSED: Monitoring framework test")
        return True
        
    except Exception as e:
        print(f"FAILED: Monitoring framework test: {e}")
        return False

async def test_configuration():
    """Test soak test configuration."""
    print("Testing soak test configuration...")
    
    try:
        print("Configuration values:")
        for key, value in SOAK_CONFIG.items():
            print(f"  {key}: {value}")
            
        # Test that URLs are reachable (basic format validation)
        urls = [
            SOAK_CONFIG["auth_service_url"],
            SOAK_CONFIG["backend_url"],
            SOAK_CONFIG["redis_url"],
            SOAK_CONFIG["postgres_url"],
            SOAK_CONFIG["clickhouse_url"]
        ]
        
        for url in urls:
            if not url or not isinstance(url, str):
                raise ValueError(f"Invalid URL configuration: {url}")
                
        print("PASSED: Configuration test")
        return True
        
    except Exception as e:
        print(f"FAILED: Configuration test: {e}")
        return False

async def main():
    """Run all validation tests."""
    print("Soak Testing Framework Validation")
    print("=" * 50)
    
    tests = [
        test_configuration,
        test_monitoring_framework
    ]
    
    results = []
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        result = await test()
        results.append(result)
        
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("All validation tests PASSED!")
        print("Soak testing framework is ready for execution")
        return 0
    else:
        print("Some validation tests FAILED!")
        print("Please fix issues before running soak tests")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)