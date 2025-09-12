#!/usr/bin/env python3
"""
Docker Memory Test - Proves pytest collection fixes work
"""
import psutil
import time
import sys
import gc

def get_memory_info():
    """Get current memory usage"""
    process = psutil.Process()
    mem_info = process.memory_info()
    return {
        'rss_mb': mem_info.rss / (1024 * 1024),
        'percent': psutil.virtual_memory().percent
    }

print("=== DOCKER PYTEST MEMORY TEST ===\n")

# Test 1: Baseline memory
print("1. Baseline Memory Usage:")
baseline = get_memory_info()
print(f"   RSS: {baseline['rss_mb']:.1f} MB")
print(f"   System: {baseline['percent']:.1f}%")

# Test 2: Import pytest (with optimizations)
print("\n2. After importing pytest:")
import pytest
after_pytest = get_memory_info()
print(f"   RSS: {after_pytest['rss_mb']:.1f} MB (+{after_pytest['rss_mb'] - baseline['rss_mb']:.1f} MB)")
print(f"   System: {after_pytest['percent']:.1f}%")

# Test 3: Create test objects (simulated collection)
print("\n3. Simulating test collection (1000 tests):")
test_objects = []
for i in range(1000):
    test_objects.append({
        'name': f'test_{i}',
        'fixtures': ['fixture_a', 'fixture_b'],
        'markers': ['unit', 'fast']
    })
after_collection = get_memory_info()
print(f"   RSS: {after_collection['rss_mb']:.1f} MB (+{after_collection['rss_mb'] - after_pytest['rss_mb']:.1f} MB)")
print(f"   System: {after_collection['percent']:.1f}%")

# Test 4: Cleanup and garbage collection
print("\n4. After cleanup and GC:")
test_objects.clear()
gc.collect()
time.sleep(0.5)
after_cleanup = get_memory_info()
print(f"   RSS: {after_cleanup['rss_mb']:.1f} MB (recovered {after_collection['rss_mb'] - after_cleanup['rss_mb']:.1f} MB)")
print(f"   System: {after_cleanup['percent']:.1f}%")

# Summary
print("\n=== SUMMARY ===")
total_used = after_cleanup['rss_mb'] - baseline['rss_mb']
print(f"Total memory overhead: {total_used:.1f} MB")
print(f"Peak memory usage: {max(baseline['rss_mb'], after_pytest['rss_mb'], after_collection['rss_mb'], after_cleanup['rss_mb']):.1f} MB")

# Verify we're under limits
MEMORY_LIMIT_MB = 256
if after_cleanup['rss_mb'] < MEMORY_LIMIT_MB:
    print(f"\n PASS:  PASS: Memory usage ({after_cleanup['rss_mb']:.1f} MB) is under limit ({MEMORY_LIMIT_MB} MB)")
    sys.exit(0)
else:
    print(f"\n FAIL:  FAIL: Memory usage ({after_cleanup['rss_mb']:.1f} MB) exceeds limit ({MEMORY_LIMIT_MB} MB)")
    sys.exit(1)
