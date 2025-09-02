"""
Docker Resource Monitor Integration Examples

This file demonstrates how to integrate the DockerResourceMonitor
into existing test frameworks and workflows.

Usage patterns for test_framework/resource_monitor.py
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Import the resource monitor
from resource_monitor import (
    DockerResourceMonitor,
    ResourceThresholdLevel,
    TestFrameworkIntegration,
    monitor_test_execution,
    check_docker_resources,
    cleanup_docker_resources
)

logger = logging.getLogger(__name__)


class TestRunnerWithResourceMonitoring:
    """
    Example integration with a test runner that uses resource monitoring.
    
    This shows how to integrate the resource monitor into existing test infrastructure
    following the patterns from the remediation plan.
    """
    
    def __init__(self, test_category: str = "integration"):
        """Initialize with resource monitoring."""
        self.test_category = test_category
        self.integration = TestFrameworkIntegration()
        self.monitor = DockerResourceMonitor(
            enable_auto_cleanup=True,
            cleanup_aggressive=False  # Be conservative in test environments
        )
        
    def run_tests_with_monitoring(self, test_commands: list) -> Dict[str, Any]:
        """
        Run tests with comprehensive resource monitoring.
        
        This follows the pattern from DOCKER_TEST_STABILITY_REMEDIATION_PLAN.md
        """
        results = {
            'success': False,
            'tests_run': 0,
            'cleanup_performed': False,
            'resource_stats': {},
            'errors': []
        }
        
        try:
            # 1. PRE-TEST RESOURCE VALIDATION
            logger.info(f"Starting {self.test_category} tests with resource monitoring")
            
            if not self.integration.pre_test_setup(self.test_category):
                results['errors'].append("Pre-test resource validation failed")
                return results
            
            # 2. CAPTURE INITIAL STATE
            initial_snapshot = self.monitor.check_system_resources()
            logger.info(f"Initial resource state - Memory: {initial_snapshot.system_memory.percentage:.1f}%, "
                       f"Containers: {int(initial_snapshot.docker_containers.current_usage)}")
            
            # 3. RUN TESTS WITH MONITORING CONTEXT
            with self.monitor.monitoring_context(f"{self.test_category}_test_suite"):
                for i, test_cmd in enumerate(test_commands):
                    logger.info(f"Running test {i+1}/{len(test_commands)}: {test_cmd}")
                    
                    # Simulate test execution (replace with actual test runner)
                    success = self._execute_test_command(test_cmd)
                    
                    if success:
                        results['tests_run'] += 1
                    else:
                        results['errors'].append(f"Test failed: {test_cmd}")
                        # Check if resource exhaustion caused the failure
                        current_snapshot = self.monitor.check_system_resources()
                        if current_snapshot.get_max_threshold_level() == ResourceThresholdLevel.EMERGENCY:
                            results['errors'].append("Resource exhaustion detected during test execution")
                            break
            
            # 4. POST-TEST CLEANUP
            cleanup_report = self.integration.post_test_cleanup()
            results['cleanup_performed'] = True
            
            if cleanup_report.containers_removed > 0:
                logger.info(f"Post-test cleanup: removed {cleanup_report.containers_removed} containers, "
                          f"{cleanup_report.networks_removed} networks, {cleanup_report.volumes_removed} volumes")
            
            # 5. FINAL RESOURCE STATE
            final_snapshot = self.monitor.check_system_resources()
            results['resource_stats'] = {
                'initial_memory_percent': initial_snapshot.system_memory.percentage,
                'final_memory_percent': final_snapshot.system_memory.percentage,
                'initial_containers': int(initial_snapshot.docker_containers.current_usage),
                'final_containers': int(final_snapshot.docker_containers.current_usage),
                'cleanup_duration': cleanup_report.cleanup_duration_seconds,
                'resources_cleaned': cleanup_report.containers_removed + cleanup_report.networks_removed + cleanup_report.volumes_removed
            }
            
            results['success'] = len(results['errors']) == 0
            
        except Exception as e:
            logger.error(f"Error during test execution with monitoring: {e}")
            results['errors'].append(f"Monitoring error: {str(e)}")
        
        return results
    
    def _execute_test_command(self, test_cmd: str) -> bool:
        """
        Simulate test execution.
        Replace this with actual test runner integration.
        """
        # This is a placeholder - integrate with your actual test runner
        # Example integrations:
        #   - pytest subprocess execution
        #   - unittest runner
        #   - custom test framework calls
        
        time.sleep(0.1)  # Simulate test execution time
        return True  # Simulate success (replace with actual logic)


class UnifiedTestRunnerIntegration:
    """
    Integration example for the unified test runner.
    
    This shows how to modify the existing unified_test_runner.py
    to use the resource monitor.
    """
    
    @staticmethod
    def add_resource_monitoring_to_test_runner():
        """
        Example of how to integrate resource monitoring into unified_test_runner.py
        
        Add these modifications to the existing test runner:
        """
        
        code_example = '''
        # At the top of unified_test_runner.py, add:
        from test_framework.resource_monitor import TestFrameworkIntegration, DockerResourceMonitor
        
        # In the main test execution function, add:
        def run_tests_with_resource_monitoring(categories, real_services=False):
            """Enhanced test runner with resource monitoring."""
            
            # Initialize resource monitoring
            integration = TestFrameworkIntegration()
            
            try:
                # Pre-test resource validation
                test_category = "integration" if "integration" in categories else "unit"
                if not integration.pre_test_setup(test_category):
                    logger.error("Insufficient resources for test execution")
                    return False
                
                # Run existing test logic with monitoring context
                monitor = DockerResourceMonitor(enable_auto_cleanup=True)
                with monitor.monitoring_context(f"{test_category}_tests"):
                    # Your existing test execution code here
                    success = run_original_test_logic(categories, real_services)
                
                # Post-test cleanup
                cleanup_report = integration.post_test_cleanup()
                if cleanup_report.containers_removed > 0:
                    logger.info(f"Cleaned up {cleanup_report.containers_removed} containers after tests")
                
                return success
                
            except ResourceExhaustionError as e:
                logger.critical(f"Resource exhaustion during tests: {e}")
                # Force cleanup on resource exhaustion
                cleanup_docker_resources()
                return False
        '''
        
        print("Integration code example:")
        print(code_example)


# Decorator-based integration examples
@monitor_test_execution("integration_api_test")
def example_api_test():
    """Example of using the monitoring decorator."""
    # Your test logic here
    time.sleep(1)  # Simulate test work
    return True


def example_manual_monitoring():
    """Example of manual resource monitoring during specific operations."""
    monitor = DockerResourceMonitor()
    
    # Check resources before heavy operation
    snapshot = monitor.check_system_resources()
    logger.info(f"Pre-operation resources: Memory {snapshot.system_memory.percentage:.1f}%, "
               f"Containers {int(snapshot.docker_containers.current_usage)}")
    
    if snapshot.get_max_threshold_level() in [ResourceThresholdLevel.CRITICAL, ResourceThresholdLevel.EMERGENCY]:
        logger.warning("Resource usage critical - performing cleanup before operation")
        cleanup_report = monitor.cleanup_if_needed(force_cleanup=True)
        logger.info(f"Cleanup removed {cleanup_report.containers_removed} containers")
    
    # Perform heavy operation
    try:
        # Your heavy operation here (e.g., start multiple Docker containers)
        pass
    finally:
        # Always cleanup after heavy operations
        monitor.cleanup_if_needed()


def example_periodic_monitoring():
    """Example of periodic monitoring in long-running processes."""
    monitor = DockerResourceMonitor(enable_auto_cleanup=True)
    
    # Monitor every 30 seconds for 5 minutes
    end_time = time.time() + 300  # 5 minutes
    
    while time.time() < end_time:
        try:
            snapshot = monitor.check_system_resources()
            status = snapshot.get_max_threshold_level()
            
            logger.info(f"Resource status: {status.value} - "
                       f"Memory: {snapshot.system_memory.percentage:.1f}% - "
                       f"Containers: {int(snapshot.docker_containers.current_usage)}")
            
            # Auto-cleanup if approaching limits
            if status in [ResourceThresholdLevel.WARNING, ResourceThresholdLevel.CRITICAL]:
                logger.info("Performing preventive cleanup")
                cleanup_report = monitor.cleanup_if_needed()
                if cleanup_report.containers_removed > 0:
                    logger.info(f"Preventive cleanup: removed {cleanup_report.containers_removed} containers")
            
        except Exception as e:
            logger.error(f"Error during periodic monitoring: {e}")
        
        time.sleep(30)  # Check every 30 seconds


def example_test_environment_health_check():
    """Example health check for test environment."""
    integration = TestFrameworkIntegration()
    
    # Get comprehensive environment status
    status = integration.get_test_environment_status()
    
    print(f"=== Test Environment Health Check ===")
    print(f"Overall Status: {status['overall_status'].upper()}")
    print(f"Timestamp: {status['timestamp']}")
    
    # Resource usage
    usage = status['resource_usage']
    print(f"\nResource Usage:")
    print(f"  Memory: {usage['memory_percent']:.1f}%")
    print(f"  CPU: {usage.get('cpu_percent', 'N/A')}%")
    print(f"  Containers: {usage['containers_count']}")
    print(f"  Networks: {usage['networks_count']}")
    print(f"  Volumes: {usage['volumes_count']}")
    
    # Monitoring stats
    stats = status['monitoring_stats']
    print(f"\nMonitoring Statistics:")
    print(f"  Uptime: {stats['monitor_uptime_seconds']:.1f}s")
    print(f"  Total Checks: {stats['total_resource_checks']}")
    print(f"  Cleanups: {stats['total_cleanups_performed']}")
    print(f"  Docker Available: {stats['docker_available']}")
    
    # Recommendations
    if status.get('recommendations'):
        print(f"\nRecommendations:")
        for rec in status['recommendations']:
            print(f"  - {rec}")
    
    # Orphaned resources
    if status['orphaned_resources_count'] > 0:
        print(f"\nWarning: {status['orphaned_resources_count']} orphaned resources found")
    
    return status


def cli_integration_examples():
    """CLI examples showing how to use the resource monitor from command line."""
    cli_examples = '''
    # Basic resource monitoring commands:
    
    # Check current resource usage
    python -m test_framework.resource_monitor --check
    
    # Perform cleanup
    python -m test_framework.resource_monitor --cleanup
    
    # Force cleanup regardless of thresholds
    python -m test_framework.resource_monitor --cleanup --force
    
    # Find orphaned resources
    python -m test_framework.resource_monitor --orphaned
    
    # Start continuous monitoring
    python -m test_framework.resource_monitor --monitor
    
    # Export resource snapshot to JSON
    python -m test_framework.resource_monitor --check --export resource_snapshot.json
    
    # Integration with existing test scripts:
    
    # Before running tests
    python -m test_framework.resource_monitor --check || exit 1
    
    # Run tests
    python tests/unified_test_runner.py --real-services
    
    # Clean up after tests  
    python -m test_framework.resource_monitor --cleanup
    
    '''
    
    print("CLI Integration Examples:")
    print(cli_examples)


if __name__ == "__main__":
    # Configure logging for examples
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Docker Resource Monitor Integration Examples")
    print("=" * 50)
    
    # Example 1: Test runner integration
    print("\n1. Test Runner Integration Example:")
    runner = TestRunnerWithResourceMonitoring("integration")
    results = runner.run_tests_with_monitoring([
        "pytest tests/test_basic.py",
        "pytest tests/test_integration.py"
    ])
    print(f"Test Results: {results}")
    
    # Example 2: Manual monitoring
    print("\n2. Manual Monitoring Example:")
    example_manual_monitoring()
    
    # Example 3: Health check
    print("\n3. Environment Health Check Example:")
    health_status = example_test_environment_health_check()
    
    # Example 4: Show integration patterns
    print("\n4. Test Runner Integration Pattern:")
    UnifiedTestRunnerIntegration.add_resource_monitoring_to_test_runner()
    
    # Example 5: CLI examples
    print("\n5. CLI Usage Examples:")
    cli_integration_examples()
    
    print("\n" + "=" * 50)
    print("Integration examples completed!")
    print("See the functions above for detailed implementation patterns.")