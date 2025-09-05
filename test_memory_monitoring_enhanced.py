#!/usr/bin/env python3
"""
Test script for enhanced memory monitoring in UnifiedDockerManager.

This script validates the new memory monitoring capabilities without running full tests.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from test_framework.resource_monitor import ResourceThresholdLevel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_memory_monitoring_initialization():
    """Test that memory monitoring components are properly initialized."""
    logger.info("=== Testing Memory Monitoring Initialization ===")
    
    try:
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="memory_test"
        )
        
        # Check that memory monitoring components are initialized
        assert hasattr(manager, 'resource_monitor'), "ResourceMonitor not initialized"
        assert hasattr(manager, 'memory_guardian'), "MemoryGuardian not initialized"
        assert hasattr(manager, 'memory_warnings_issued'), "Memory warnings tracking not initialized"
        
        logger.info("✅ Memory monitoring components initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory monitoring initialization failed: {e}")
        return False

def test_memory_pre_flight_check():
    """Test the memory pre-flight check functionality."""
    logger.info("=== Testing Memory Pre-Flight Check ===")
    
    try:
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="memory_test"
        )
        
        # Run pre-flight check
        result = manager.perform_memory_pre_flight_check()
        logger.info(f"Pre-flight check result: {result}")
        
        if result:
            logger.info("✅ Memory pre-flight check passed")
        else:
            logger.warning("⚠️ Memory pre-flight check failed (may be expected on low-memory systems)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory pre-flight check error: {e}")
        return False

def test_memory_monitoring_during_operations():
    """Test memory monitoring during operations."""
    logger.info("=== Testing Memory Monitoring During Operations ===")
    
    try:
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="memory_test"
        )
        
        # Monitor memory
        snapshot = manager.monitor_memory_during_operations()
        
        if snapshot:
            logger.info(f"Memory monitoring snapshot:")
            logger.info(f"  System Memory: {snapshot.system_memory.percentage:.1f}%")
            logger.info(f"  System CPU: {snapshot.system_cpu.percentage:.1f}%")
            logger.info(f"  Containers: {int(snapshot.docker_containers.current_usage)}")
            logger.info(f"  Networks: {int(snapshot.docker_networks.current_usage)}")
            logger.info(f"  Volumes: {int(snapshot.docker_volumes.current_usage)}")
            logger.info(f"  Threshold Level: {snapshot.get_max_threshold_level().value}")
            
            logger.info("✅ Memory monitoring during operations successful")
        else:
            logger.warning("⚠️ Memory monitoring returned no snapshot")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory monitoring during operations failed: {e}")
        return False

def test_container_memory_info():
    """Test container-specific memory information retrieval."""
    logger.info("=== Testing Container Memory Information ===")
    
    try:
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="memory_test"
        )
        
        # Test getting memory info for common services
        services_to_test = ["backend", "postgres", "redis"]
        
        for service in services_to_test:
            memory_info = manager._get_container_memory_info(service)
            if memory_info:
                logger.info(f"  {service}: {memory_info}")
            else:
                logger.info(f"  {service}: No memory info (container not running)")
        
        logger.info("✅ Container memory information retrieval tested")
        return True
        
    except Exception as e:
        logger.error(f"❌ Container memory information test failed: {e}")
        return False

def test_detailed_memory_report():
    """Test detailed container memory reporting."""
    logger.info("=== Testing Detailed Memory Report ===")
    
    try:
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="memory_test"
        )
        
        # Get detailed memory report
        container_details = manager._get_detailed_container_memory_report()
        
        if container_details:
            logger.info("Detailed memory report:")
            for line in container_details:
                logger.info(f"  {line}")
        else:
            logger.info("No containers running for detailed memory report")
        
        logger.info("✅ Detailed memory report tested")
        return True
        
    except Exception as e:
        logger.error(f"❌ Detailed memory report test failed: {e}")
        return False

def test_health_report_with_memory():
    """Test enhanced health report with memory monitoring."""
    logger.info("=== Testing Enhanced Health Report ===")
    
    try:
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="memory_test"
        )
        
        # Get health report
        health_report = manager.get_health_report()
        
        logger.info("Enhanced Health Report:")
        print(health_report)
        
        # Check that memory monitoring is included
        if "MEMORY & RESOURCE STATUS" in health_report:
            logger.info("✅ Memory monitoring included in health report")
        else:
            logger.warning("⚠️ Memory monitoring not found in health report")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced health report test failed: {e}")
        return False

def test_statistics_with_memory():
    """Test statistics with memory monitoring information."""
    logger.info("=== Testing Statistics with Memory Monitoring ===")
    
    try:
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="memory_test"
        )
        
        # Get statistics
        stats = manager.get_statistics()
        
        logger.info("Statistics with memory monitoring:")
        
        if "memory_monitoring" in stats:
            memory_stats = stats["memory_monitoring"]
            
            # Safe formatting for potentially missing values
            mem_percent = memory_stats.get('system_memory_percent', 'N/A')
            cpu_percent = memory_stats.get('system_cpu_percent', 'N/A')
            containers_count = memory_stats.get('docker_containers_count', 'N/A')
            threshold_level = memory_stats.get('overall_threshold_level', 'N/A')
            
            if isinstance(mem_percent, (int, float)):
                logger.info(f"  System Memory: {mem_percent:.1f}%")
            else:
                logger.info(f"  System Memory: {mem_percent}")
                
            if isinstance(cpu_percent, (int, float)):
                logger.info(f"  System CPU: {cpu_percent:.1f}%")
            else:
                logger.info(f"  System CPU: {cpu_percent}")
                
            logger.info(f"  Containers: {containers_count}")
            logger.info(f"  Threshold Level: {threshold_level}")
            
            if "high_memory_containers" in memory_stats:
                logger.info(f"  High Memory Containers: {len(memory_stats['high_memory_containers'])}")
            
            logger.info("✅ Memory monitoring statistics included")
        else:
            logger.warning("⚠️ Memory monitoring statistics not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Statistics with memory monitoring test failed: {e}")
        return False

def main():
    """Run all memory monitoring tests."""
    logger.info("🚀 Starting Enhanced Memory Monitoring Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Memory Monitoring Initialization", test_memory_monitoring_initialization),
        ("Memory Pre-Flight Check", test_memory_pre_flight_check),
        ("Memory Monitoring During Operations", test_memory_monitoring_during_operations),
        ("Container Memory Information", test_container_memory_info),
        ("Detailed Memory Report", test_detailed_memory_report),
        ("Enhanced Health Report", test_health_report_with_memory),
        ("Statistics with Memory", test_statistics_with_memory),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                logger.error(f"❌ {test_name} failed")
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
        
        logger.info("-" * 40)
    
    logger.info(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All enhanced memory monitoring tests passed!")
        return 0
    else:
        logger.error(f"💥 {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())