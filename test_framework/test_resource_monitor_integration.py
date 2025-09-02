#!/usr/bin/env python3
"""
Integration Test for Docker Resource Monitor

Tests the resource monitor functionality with real Docker resources.
This test validates the core functionality before integrating into the main test framework.
"""

import logging
import sys
import time
from pathlib import Path

# Add the test_framework to the path
sys.path.insert(0, str(Path(__file__).parent))

from resource_monitor import (
    DockerResourceMonitor,
    ResourceThresholdLevel,
    ResourceType,
    TestFrameworkIntegration,
    check_docker_resources,
    cleanup_docker_resources
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_resource_monitoring():
    """Test basic resource monitoring functionality."""
    print("\n=== Testing Basic Resource Monitoring ===")
    
    try:
        monitor = DockerResourceMonitor()
        
        # Test resource snapshot
        snapshot = monitor.check_system_resources()
        
        print(f"Resource Check Results:")
        print(f"  Overall Status: {snapshot.get_max_threshold_level().value}")
        print(f"  Memory: {snapshot.system_memory.percentage:.1f}% "
              f"({snapshot.system_memory.current_usage / 1024**3:.1f}GB / "
              f"{snapshot.system_memory.max_limit / 1024**3:.1f}GB)")
        print(f"  CPU: {snapshot.system_cpu.percentage:.1f}%")
        print(f"  Containers: {int(snapshot.docker_containers.current_usage)} / "
              f"{int(snapshot.docker_containers.max_limit)}")
        print(f"  Networks: {int(snapshot.docker_networks.current_usage)} / "
              f"{int(snapshot.docker_networks.max_limit)}")
        print(f"  Volumes: {int(snapshot.docker_volumes.current_usage)} / "
              f"{int(snapshot.docker_volumes.max_limit)}")
        print(f"  Disk: {snapshot.docker_disk.current_usage / 1024**3:.1f}GB / "
              f"{snapshot.docker_disk.max_limit / 1024**3:.1f}GB")
        
        # Test container details
        if snapshot.container_details:
            print(f"  Container Details: {len(snapshot.container_details)} containers found")
            for container in snapshot.container_details[:3]:  # Show first 3
                print(f"    - {container['name']} ({container['status']})")
        
        return True
        
    except Exception as e:
        print(f"Error in basic monitoring test: {e}")
        logger.error(f"Basic monitoring test failed: {e}", exc_info=True)
        return False


def test_orphaned_resource_detection():
    """Test orphaned resource detection."""
    print("\n=== Testing Orphaned Resource Detection ===")
    
    try:
        monitor = DockerResourceMonitor()
        
        orphaned = monitor.detect_orphaned_resources()
        
        print(f"Orphaned Resources Found: {len(orphaned)}")
        for resource in orphaned[:5]:  # Show first 5
            print(f"  {resource.resource_type}: {resource.resource_name} "
                  f"(created: {resource.created.strftime('%Y-%m-%d %H:%M:%S')})")
        
        if len(orphaned) > 5:
            print(f"  ... and {len(orphaned) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"Error in orphaned resource detection test: {e}")
        logger.error(f"Orphaned resource detection test failed: {e}", exc_info=True)
        return False


def test_cleanup_functionality():
    """Test cleanup functionality (non-destructive)."""
    print("\n=== Testing Cleanup Functionality ===")
    
    try:
        # Use non-aggressive cleanup to avoid disrupting system
        monitor = DockerResourceMonitor(
            enable_auto_cleanup=True,
            cleanup_aggressive=False
        )
        
        # Get current state
        pre_snapshot = monitor.check_system_resources()
        print(f"Pre-cleanup containers: {int(pre_snapshot.docker_containers.current_usage)}")
        
        # Test cleanup assessment (won't cleanup unless needed)
        cleanup_report = monitor.cleanup_if_needed(force_cleanup=False)
        
        print(f"Cleanup Assessment:")
        print(f"  Containers removed: {cleanup_report.containers_removed}")
        print(f"  Networks removed: {cleanup_report.networks_removed}")
        print(f"  Volumes removed: {cleanup_report.volumes_removed}")
        print(f"  Duration: {cleanup_report.cleanup_duration_seconds:.2f}s")
        
        if cleanup_report.errors:
            print(f"  Cleanup errors: {len(cleanup_report.errors)}")
            for error in cleanup_report.errors[:2]:  # Show first 2 errors
                print(f"    - {error}")
        
        # Get post state
        post_snapshot = monitor.check_system_resources()
        print(f"Post-cleanup containers: {int(post_snapshot.docker_containers.current_usage)}")
        
        return True
        
    except Exception as e:
        print(f"Error in cleanup functionality test: {e}")
        logger.error(f"Cleanup functionality test failed: {e}", exc_info=True)
        return False


def test_resource_prediction():
    """Test resource prediction for different test categories."""
    print("\n=== Testing Resource Prediction ===")
    
    try:
        monitor = DockerResourceMonitor()
        
        test_categories = ["unit", "integration", "e2e", "performance"]
        
        for category in test_categories:
            predicted = monitor.predict_resource_needs(category)
            print(f"Predicted needs for {category} tests:")
            print(f"  Memory: {predicted['memory_gb']:.1f}GB")
            print(f"  Containers: {predicted['containers']}")
            print(f"  Networks: {predicted['networks']}")
            print(f"  Volumes: {predicted['volumes']}")
            print(f"  Disk: {predicted['disk_gb']:.1f}GB")
        
        return True
        
    except Exception as e:
        print(f"Error in resource prediction test: {e}")
        logger.error(f"Resource prediction test failed: {e}", exc_info=True)
        return False


def test_monitoring_context():
    """Test the monitoring context manager."""
    print("\n=== Testing Monitoring Context ===")
    
    try:
        monitor = DockerResourceMonitor()
        
        with monitor.monitoring_context("test_integration_test") as pre_snapshot:
            print(f"Context started - Memory: {pre_snapshot.system_memory.percentage:.1f}%")
            
            # Simulate some work
            time.sleep(1)
            
            print("Context work completed")
        
        print("Context exited successfully")
        return True
        
    except Exception as e:
        print(f"Error in monitoring context test: {e}")
        logger.error(f"Monitoring context test failed: {e}", exc_info=True)
        return False


def test_test_framework_integration():
    """Test the TestFrameworkIntegration class."""
    print("\n=== Testing Test Framework Integration ===")
    
    try:
        integration = TestFrameworkIntegration()
        
        # Test pre-test setup
        print("Testing pre-test setup...")
        setup_success = integration.pre_test_setup("integration")
        print(f"Pre-test setup successful: {setup_success}")
        
        # Test status reporting
        print("Getting test environment status...")
        status = integration.get_test_environment_status()
        
        print(f"Test Environment Status:")
        print(f"  Overall Status: {status['overall_status']}")
        print(f"  Memory: {status['resource_usage']['memory_percent']:.1f}%")
        print(f"  Containers: {status['resource_usage']['containers_count']}")
        print(f"  Networks: {status['resource_usage']['networks_count']}")
        print(f"  Volumes: {status['resource_usage']['volumes_count']}")
        print(f"  Orphaned Resources: {status['orphaned_resources_count']}")
        
        if status.get('recommendations'):
            print(f"  Recommendations: {len(status['recommendations'])}")
            for rec in status['recommendations'][:3]:  # Show first 3
                print(f"    - {rec}")
        
        # Test post-test cleanup
        print("Testing post-test cleanup...")
        post_cleanup = integration.post_test_cleanup()
        print(f"Post-test cleanup completed in {post_cleanup.cleanup_duration_seconds:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"Error in test framework integration test: {e}")
        logger.error(f"Test framework integration test failed: {e}", exc_info=True)
        return False


def test_convenience_functions():
    """Test the convenience functions."""
    print("\n=== Testing Convenience Functions ===")
    
    try:
        # Test check_docker_resources
        print("Testing check_docker_resources()...")
        snapshot = check_docker_resources()
        print(f"Quick check - Status: {snapshot.get_max_threshold_level().value}")
        
        # Test cleanup_docker_resources (non-destructive)
        print("Testing cleanup_docker_resources()...")
        cleanup_report = cleanup_docker_resources()
        print(f"Quick cleanup completed - Duration: {cleanup_report.cleanup_duration_seconds:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"Error in convenience functions test: {e}")
        logger.error(f"Convenience functions test failed: {e}", exc_info=True)
        return False


def test_monitoring_stats():
    """Test monitoring statistics and performance tracking."""
    print("\n=== Testing Monitoring Statistics ===")
    
    try:
        monitor = DockerResourceMonitor()
        
        # Perform some operations to generate stats
        monitor.check_system_resources()
        monitor.detect_orphaned_resources()
        
        # Get stats
        stats = monitor.get_monitoring_stats()
        
        print(f"Monitoring Statistics:")
        print(f"  Uptime: {stats['monitor_uptime_seconds']:.2f}s")
        print(f"  Resource checks: {stats['total_resource_checks']}")
        print(f"  Cleanups performed: {stats['total_cleanups_performed']}")
        print(f"  Resources cleaned: {stats['total_resources_cleaned']}")
        print(f"  Docker available: {stats['docker_available']}")
        print(f"  psutil available: {stats['psutil_available']}")
        print(f"  Auto cleanup enabled: {stats['auto_cleanup_enabled']}")
        print(f"  History entries: {stats['history_entries']}")
        
        print(f"Configured Limits:")
        limits = stats['configured_limits']
        print(f"  Max memory: {limits['max_memory_gb']}GB")
        print(f"  Max containers: {limits['max_containers']}")
        print(f"  Max networks: {limits['max_networks']}")
        print(f"  Max volumes: {limits['max_volumes']}")
        print(f"  Max disk: {limits['max_disk_gb']}GB")
        
        return True
        
    except Exception as e:
        print(f"Error in monitoring stats test: {e}")
        logger.error(f"Monitoring stats test failed: {e}", exc_info=True)
        return False


def run_all_tests():
    """Run all integration tests."""
    print("Docker Resource Monitor Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Basic Resource Monitoring", test_basic_resource_monitoring),
        ("Orphaned Resource Detection", test_orphaned_resource_detection),
        ("Cleanup Functionality", test_cleanup_functionality),
        ("Resource Prediction", test_resource_prediction),
        ("Monitoring Context", test_monitoring_context),
        ("Test Framework Integration", test_test_framework_integration),
        ("Convenience Functions", test_convenience_functions),
        ("Monitoring Statistics", test_monitoring_stats)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            start_time = time.time()
            success = test_func()
            duration = time.time() - start_time
            results[test_name] = {
                'success': success,
                'duration': duration
            }
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"Result: {status} ({duration:.2f}s)")
        except Exception as e:
            results[test_name] = {
                'success': False,
                'duration': 0,
                'error': str(e)
            }
            print(f"Result: ✗ FAIL (Exception: {e})")
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r['success'])
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print(f"\nFailed Tests:")
        for test_name, result in results.items():
            if not result['success']:
                error = result.get('error', 'Unknown error')
                print(f"  - {test_name}: {error}")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)