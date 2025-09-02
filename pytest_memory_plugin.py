"""
Pytest memory monitoring plugin to prevent Docker container crashes.
This plugin monitors memory usage during test collection and execution.
"""
import gc
import os
import psutil
import pytest
import sys
import tracemalloc
from typing import Optional


class MemoryMonitorPlugin:
    """Plugin to monitor and limit memory usage during pytest execution."""
    
    def __init__(self):
        self.memory_limit_mb = int(os.environ.get('PYTEST_MEMORY_LIMIT_MB', '512'))
        self.collection_limit_mb = int(os.environ.get('PYTEST_COLLECTION_LIMIT_MB', '256'))
        self.process = psutil.Process(os.getpid())
        self.start_memory = None
        self.tracemalloc_enabled = False
        
    def pytest_configure(self, config):
        """Configure the memory monitor at pytest startup."""
        # Enable tracemalloc for detailed memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self.tracemalloc_enabled = True
            
        self.start_memory = self.get_memory_usage()
        print(f"[MEMORY] Starting pytest with {self.start_memory:.1f}MB memory")
        print(f"[MEMORY] Memory limits - Collection: {self.collection_limit_mb}MB, Execution: {self.memory_limit_mb}MB")
        
    def pytest_collection_modifyitems(self, config, items):
        """Monitor memory after test collection."""
        current_memory = self.get_memory_usage()
        print(f"[MEMORY] After collection: {current_memory:.1f}MB ({len(items)} tests)")
        
        if current_memory > self.collection_limit_mb:
            self.force_garbage_collection()
            gc_memory = self.get_memory_usage()
            print(f"[MEMORY] After GC: {gc_memory:.1f}MB")
            
            if gc_memory > self.collection_limit_mb:
                pytest.exit(f"Memory limit exceeded after collection: {gc_memory:.1f}MB > {self.collection_limit_mb}MB")
                
    def pytest_runtest_setup(self, item):
        """Monitor memory before each test."""
        current_memory = self.get_memory_usage()
        
        if current_memory > self.memory_limit_mb:
            self.force_garbage_collection()
            gc_memory = self.get_memory_usage()
            
            if gc_memory > self.memory_limit_mb:
                pytest.skip(f"Skipping test due to memory limit: {gc_memory:.1f}MB > {self.memory_limit_mb}MB")
                
    def pytest_runtest_teardown(self, item, nextitem):
        """Clean up memory after each test."""
        if nextitem is None or self.get_memory_usage() > (self.memory_limit_mb * 0.8):
            self.force_garbage_collection()
            
    def pytest_unconfigure(self, config):
        """Clean up at the end of pytest execution."""
        if self.tracemalloc_enabled:
            # Get memory statistics
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            print(f"[MEMORY] Final memory usage: {self.get_memory_usage():.1f}MB")
            print(f"[MEMORY] Peak traced memory: {peak / 1024 / 1024:.1f}MB")
            
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
            
    def force_garbage_collection(self):
        """Force garbage collection to free memory."""
        for _ in range(3):
            gc.collect()


def pytest_configure(config):
    """Register the memory monitor plugin."""
    if not hasattr(config, '_memory_plugin'):
        config._memory_plugin = MemoryMonitorPlugin()
        config.pluginmanager.register(config._memory_plugin, 'memory_monitor')


def pytest_collection_modifyitems(config, items):
    """Delegate to the memory monitor plugin."""
    if hasattr(config, '_memory_plugin'):
        config._memory_plugin.pytest_collection_modifyitems(config, items)


def pytest_runtest_setup(item):
    """Delegate to the memory monitor plugin."""
    if hasattr(item.config, '_memory_plugin'):
        item.config._memory_plugin.pytest_runtest_setup(item)


def pytest_runtest_teardown(item, nextitem):
    """Delegate to the memory monitor plugin."""
    if hasattr(item.config, '_memory_plugin'):
        item.config._memory_plugin.pytest_runtest_teardown(item, nextitem)


def pytest_unconfigure(config):
    """Delegate to the memory monitor plugin."""
    if hasattr(config, '_memory_plugin'):
        config._memory_plugin.pytest_unconfigure(config)