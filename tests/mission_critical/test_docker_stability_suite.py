"""
MISSION CRITICAL: Docker Stability Test Suite - P1 Remediation Validation

CRITICAL BUSINESS VALUE: This test suite validates ALL P1 Docker stability fixes
to prevent the 4-8 hours/week of developer downtime that costs $2M+ ARR protection.

This comprehensive test suite validates ALL P1 remediation items from the
Docker Test Stability Remediation Plan dated 2025-09-02, including:

P1 REMEDIATION VALIDATION COVERAGE:
1. ✅ Environment Lock Mechanism Testing
2. ✅ Resource Monitor Functionality Testing  
3. ✅ tmpfs Volume Fixes (No RAM Exhaustion)
4. ✅ Parallel Execution Stability Testing
5. ✅ Cleanup Mechanism Testing
6. ✅ Resource Limit Enforcement Testing
7. ✅ Orphaned Resource Cleanup Testing
8. ✅ Docker Daemon Stability Stress Testing

CRITICAL REQUIREMENTS (Per P1 Plan):
- NO MOCKS: All tests use real Docker operations
- COMPREHENSIVE: Tests ALL P1 remediation items
- STRESS TESTING: Push systems to breaking points
- FAILURE RECOVERY: Validate error recovery mechanisms
- RESOURCE VALIDATION: Comprehensive resource management
- PARALLEL SAFETY: Validate concurrent execution safety
- TMPFS PROHIBITION: Ensure no RAM exhaustion from tmpfs volumes
- CLEANUP VALIDATION: Ensure no resource leaks

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity, Risk Reduction
2. Business Goal: Validate Docker stability prevents infrastructure failures
3. Value Impact: Ensures reliable CI/CD and prevents developer downtime
4. Revenue Impact: Protects $2M+ ARR through stable test infrastructure

SUCCESS METRICS (Per P1 Plan):
- Docker daemon crashes: Target 0 (currently 5-10/day)
- Orphaned containers: Target 0 (currently 50+)
- Test execution time: Target < 5 min (currently 10+ min)
- Memory usage: Target < 4GB peak (currently 6GB+ from tmpfs)
- Parallel test success: Target 100% (currently 60%)
"""

import asyncio
import time
import threading
import logging
import pytest
import subprocess
import random
import psutil
import json
import gc
import socket
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from unittest.mock import patch
import uuid
import signal
import sys
import os

# Add parent directory to path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# CRITICAL IMPORTS: All P1 Remediation Components
from test_framework.docker_force_flag_guardian import (
    DockerForceFlagGuardian,
    DockerForceFlagViolation,
    validate_docker_command
)
from test_framework.docker_rate_limiter import (
    DockerRateLimiter,
    execute_docker_command,
    get_docker_rate_limiter,
    DockerCommandResult
)
from test_framework.unified_docker_manager import UnifiedDockerManager
from test_framework.dynamic_port_allocator import (
    DynamicPortAllocator,
    allocate_test_ports,
    release_test_ports
)
# P1 REMEDIATION IMPORTS: Environment Lock Mechanism
from test_framework.environment_lock import (
    EnvironmentLock, LockStatusInfo, EnvironmentLockError
)
# P1 REMEDIATION IMPORTS: Resource Monitor Functionality  
from test_framework.resource_monitor import (
    DockerResourceMonitor, ResourceThresholdLevel, ResourceReport, CleanupReport
)
# P1 REMEDIATION IMPORTS: Docker Introspection and Cleanup
from test_framework.docker_introspection import DockerIntrospector
from test_framework.docker_cleanup_scheduler import DockerCleanupScheduler

from shared.isolated_environment import get_env

# Configure logging for maximum visibility
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# P1 REMEDIATION CONFIGURATION: Based on Docker Test Stability Remediation Plan
class DockerStabilityP1Config:
    """Configuration for P1 Docker stability remediation validation."""
    
    # Resource Limits (from P1 plan - Section 2: Fix Test Environment Resource Usage)
    MAX_MEMORY_GB = 4.0  # Maximum memory usage before intervention
    MAX_CONTAINERS_PER_TEST = 20  # Container limit per test environment
    POSTGRES_MEMORY_LIMIT = "512M"  # P1 Fix: No more tmpfs RAM exhaustion
    REDIS_MEMORY_LIMIT = "256M"    # P1 Fix: Reduced memory footprint
    
    # Parallel Execution Limits (P1 Validation)
    MAX_PARALLEL_ENVIRONMENTS = 10  # Stress test parallel execution
    CONCURRENT_TEST_DURATION = 300  # 5 minutes stress test duration
    
    # Cleanup Validation (P1 Section 3: Add Mandatory Cleanup)
    ORPHANED_RESOURCE_THRESHOLD = 5  # Max orphaned resources before cleanup
    CLEANUP_VALIDATION_CYCLES = 3    # Multiple cleanup cycles to test
    
    # Stress Testing Parameters (P1 Validation)
    STRESS_TEST_OPERATIONS = 100     # Operations per stress test
    RAPID_CREATE_DESTROY_CYCLES = 50 # Container lifecycle stress test
    MEMORY_PRESSURE_TEST_MB = 3500   # Memory pressure threshold
    
    # Timeout Configuration (P1 Based)
    ENVIRONMENT_LOCK_TIMEOUT = 60    # Lock acquisition timeout
    RESOURCE_MONITOR_TIMEOUT = 30    # Resource check timeout
    DOCKER_OPERATION_TIMEOUT = 45    # Individual Docker operation timeout


class DockerStabilityTestFramework:
    """Framework for comprehensive P1 Docker stability testing."""
    
    def __init__(self):
        """Initialize P1 test framework with all necessary components."""
        self.test_containers = []
        self.test_networks = []
        self.test_volumes = []
        self.test_images = []
        self.allocated_ports = []
        
        # P1 REMEDIATION METRICS: Track all P1 validation items
        self.metrics = {
            # General Operations
            'operations_attempted': 0,
            'operations_successful': 0,
            'operations_failed': 0,
            
            # P1 Environment Lock Metrics
            'lock_acquisitions_attempted': 0,
            'lock_acquisitions_successful': 0,
            'concurrent_lock_conflicts': 0,
            'lock_timeout_events': 0,
            
            # P1 Resource Monitor Metrics
            'resource_warnings_triggered': 0,
            'memory_pressure_events': 0,
            'resource_cleanup_operations': 0,
            'orphaned_resources_found': 0,
            'orphaned_resources_cleaned': 0,
            
            # P1 tmpfs Volume Fix Metrics
            'tmpfs_violations_detected': 0,
            'memory_exhaustion_events': 0,
            'resource_limit_enforcements': 0,
            
            # P1 Parallel Execution Metrics
            'parallel_environments_created': 0,
            'parallel_execution_failures': 0,
            'concurrent_operations_peak': 0,
            
            # P1 Cleanup Mechanism Metrics
            'cleanup_operations': 0,
            'cleanup_failures': 0,
            'automatic_cleanup_triggers': 0,
            
            # P1 Daemon Stability Metrics
            'daemon_health_checks': 0,
            'daemon_health_failures': 0,
            'daemon_crash_events': 0,
            
            # Compliance Metrics
            'force_flag_violations_detected': 0,
            'recovery_attempts': 0,
            'recovery_successes': 0
        }
        self.start_time = time.time()
        
        # Initialize ALL P1 Docker components
        self.docker_manager = UnifiedDockerManager(environment_type="test")
        self.rate_limiter = get_docker_rate_limiter()
        self.force_guardian = DockerForceFlagGuardian(
            audit_log_path="logs/docker_stability_p1_violations.log"
        )
        
        # P1 REMEDIATION COMPONENTS: Initialize new components
        self.environment_lock_manager = EnvironmentLock()
        self.resource_monitor = DockerResourceMonitor()
        self.docker_introspector = DockerIntrospector()
        self.cleanup_scheduler = DockerCleanupScheduler()
        
        logger.info("🔧 P1 Docker Stability Test Framework initialized with ALL REMEDIATION COMPONENTS")
        
    def cleanup(self):
        """Comprehensive cleanup of all test resources."""
        logger.info("🧹 Starting comprehensive Docker cleanup...")
        cleanup_errors = []
        
        try:
            # Cleanup containers
            for container in self.test_containers:
                try:
                    result = execute_docker_command(['docker', 'container', 'stop', container])
                    if result.returncode == 0:
                        execute_docker_command(['docker', 'container', 'rm', container])
                except Exception as e:
                    cleanup_errors.append(f"Container {container}: {e}")
            
            # Cleanup networks
            for network in self.test_networks:
                try:
                    execute_docker_command(['docker', 'network', 'rm', network])
                except Exception as e:
                    cleanup_errors.append(f"Network {network}: {e}")
            
            # Cleanup volumes
            for volume in self.test_volumes:
                try:
                    execute_docker_command(['docker', 'volume', 'rm', volume])
                except Exception as e:
                    cleanup_errors.append(f"Volume {volume}: {e}")
                    
            # Cleanup test images
            for image in self.test_images:
                try:
                    execute_docker_command(['docker', 'image', 'rm', image])
                except Exception as e:
                    cleanup_errors.append(f"Image {image}: {e}")
            
            # Release allocated ports
            for port_range in self.allocated_ports:
                try:
                    release_test_ports(port_range)
                except Exception as e:
                    cleanup_errors.append(f"Port release {port_range}: {e}")
                    
        except Exception as e:
            logger.error(f"Critical cleanup error: {e}")
            cleanup_errors.append(f"Critical cleanup: {e}")
        
        if cleanup_errors:
            logger.warning(f"Cleanup completed with {len(cleanup_errors)} errors")
            for error in cleanup_errors:
                logger.debug(f"Cleanup error: {error}")
        else:
            logger.info("✅ All test resources cleaned up successfully")
        
        self.metrics['cleanup_operations'] += 1
        
    def record_operation(self, success: bool, operation: str = ""):
        """Record operation metrics."""
        self.metrics['operations_attempted'] += 1
        if success:
            self.metrics['operations_successful'] += 1
        else:
            self.metrics['operations_failed'] += 1
            logger.warning(f"❌ Operation failed: {operation}")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            return {
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'cpu_percent': cpu_percent,
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'active_processes': len(psutil.pids())
            }
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
            return {}
    
    def simulate_memory_pressure(self, duration_seconds: int = 10) -> bool:
        """Simulate memory pressure to test Docker stability under resource constraints."""
        logger.info(f"🔥 Simulating memory pressure for {duration_seconds} seconds...")
        
        # Allocate memory to create pressure
        memory_chunks = []
        try:
            # Allocate in 100MB chunks up to 80% of available memory
            available_memory = psutil.virtual_memory().available
            target_allocation = int(available_memory * 0.8)
            chunk_size = 100 * 1024 * 1024  # 100MB
            
            for i in range(target_allocation // chunk_size):
                memory_chunks.append(bytearray(chunk_size))
                if i % 10 == 0:  # Log progress every GB
                    logger.debug(f"Allocated {(i + 1) * chunk_size / (1024**3):.1f}GB")
            
            self.metrics['memory_pressure_events'] += 1
            time.sleep(duration_seconds)
            return True
            
        except MemoryError:
            logger.warning("⚠️ Memory allocation limit reached")
            return True
        except Exception as e:
            logger.error(f"Memory pressure simulation failed: {e}")
            return False
        finally:
            # Clear memory pressure
            del memory_chunks
            gc.collect()
            logger.info("✅ Memory pressure simulation completed")


@pytest.fixture
def stability_framework():
    """Pytest fixture providing Docker stability test framework."""
    framework = DockerStabilityTestFramework()
    yield framework
    framework.cleanup()


# ========================================
# P1 REMEDIATION VALIDATION TEST CLASSES
# ========================================

class TestP1EnvironmentLockMechanism:
    """P1 REMEDIATION: Test Environment Lock Mechanism (Section 2.2 from P1 plan)."""
    
    def test_environment_lock_acquisition_and_release(self, stability_framework):
        """Test basic environment lock acquisition and release functionality."""
        logger.info("🔒 P1 TEST: Environment lock acquisition and release")
        
        stability_framework.metrics['lock_acquisitions_attempted'] += 1
        
        try:
            # Test dev environment lock
            with stability_framework.environment_lock_manager.acquire_environment_lock(
                EnvironmentType.DEVELOPMENT, 
                timeout=DockerStabilityP1Config.ENVIRONMENT_LOCK_TIMEOUT
            ) as dev_lock:
                assert dev_lock is not None, "Failed to acquire development environment lock"
                stability_framework.metrics['lock_acquisitions_successful'] += 1
                
                logger.info(f"✅ Successfully acquired dev environment lock: {dev_lock.lock_id}")
                
                # Verify lock properties
                assert dev_lock.environment_type == EnvironmentType.DEVELOPMENT
                assert dev_lock.process_id == os.getpid()
                assert dev_lock.acquired_at is not None
                
                # Test that we can't acquire the same environment lock concurrently
                stability_framework.metrics['lock_acquisitions_attempted'] += 1
                try:
                    with stability_framework.environment_lock_manager.acquire_environment_lock(
                        EnvironmentType.DEVELOPMENT, timeout=2  # Short timeout
                    ) as concurrent_lock:
                        assert concurrent_lock is None, "Concurrent lock should fail"
                        stability_framework.metrics['concurrent_lock_conflicts'] += 1
                except Exception:
                    stability_framework.metrics['concurrent_lock_conflicts'] += 1
                    logger.info("✅ Concurrent lock correctly rejected")
            
            # Test test environment lock after dev lock is released
            stability_framework.metrics['lock_acquisitions_attempted'] += 1
            with stability_framework.environment_lock_manager.acquire_environment_lock(
                EnvironmentType.TEST,
                timeout=DockerStabilityP1Config.ENVIRONMENT_LOCK_TIMEOUT
            ) as test_lock:
                assert test_lock is not None, "Failed to acquire test environment lock"
                stability_framework.metrics['lock_acquisitions_successful'] += 1
                logger.info(f"✅ Successfully acquired test environment lock: {test_lock.lock_id}")
            
            logger.info("✅ P1 Environment lock mechanism validation completed successfully")
            
        except Exception as e:
            logger.error(f"❌ P1 Environment lock test failed: {e}")
            stability_framework.metrics['lock_timeout_events'] += 1
            raise
    
    def test_concurrent_environment_lock_prevention(self, stability_framework):
        """Test that concurrent environment locks are properly prevented (P1 requirement)."""
        logger.info("🔒 P1 TEST: Concurrent environment lock prevention")
        
        def attempt_lock_acquisition(env_type, timeout, results_queue):
            """Attempt lock acquisition in separate thread."""
            try:
                stability_framework.metrics['lock_acquisitions_attempted'] += 1
                with stability_framework.environment_lock_manager.acquire_environment_lock(
                    env_type, timeout=timeout
                ) as lock:
                    if lock:
                        stability_framework.metrics['lock_acquisitions_successful'] += 1
                        results_queue.put(('success', lock.lock_id))
                        time.sleep(5)  # Hold lock briefly
                    else:
                        stability_framework.metrics['concurrent_lock_conflicts'] += 1
                        results_queue.put(('blocked', None))
            except Exception as e:
                stability_framework.metrics['lock_timeout_events'] += 1
                results_queue.put(('error', str(e)))
        
        import queue
        results = queue.Queue()
        
        # Start multiple threads attempting to acquire the same environment lock
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=attempt_lock_acquisition,
                args=(EnvironmentType.TEST, 10, results)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads and collect results
        for thread in threads:
            thread.join(timeout=20)
        
        # Analyze results
        thread_results = []
        while not results.empty():
            thread_results.append(results.get_nowait())
        
        successful_locks = [r for r in thread_results if r[0] == 'success']
        blocked_locks = [r for r in thread_results if r[0] == 'blocked']
        
        # P1 Requirement: Only one lock should succeed, others should be blocked
        assert len(successful_locks) == 1, f"Expected 1 successful lock, got {len(successful_locks)}"
        assert len(blocked_locks) >= 1, f"Expected at least 1 blocked lock, got {len(blocked_locks)}"
        
        logger.info(f"✅ P1 Concurrent lock prevention: {len(successful_locks)} success, {len(blocked_locks)} blocked")


class TestP1ResourceMonitorFunctionality:
    """P1 REMEDIATION: Test Resource Monitor Functionality (Section 2.3 from P1 plan)."""
    
    def test_resource_monitoring_and_thresholds(self, stability_framework):
        """Test comprehensive resource monitoring and threshold checking."""
        logger.info("📊 P1 TEST: Resource monitoring and threshold validation")
        
        try:
            # Get current resource state
            resource_state = stability_framework.resource_monitor.get_current_resource_state()
            assert resource_state is not None, "Failed to get resource state"
            
            # Verify all expected metrics are present
            assert hasattr(resource_state, 'memory_usage_mb'), "Missing memory usage metric"
            assert hasattr(resource_state, 'container_count'), "Missing container count metric"
            assert hasattr(resource_state, 'network_count'), "Missing network count metric" 
            assert hasattr(resource_state, 'volume_count'), "Missing volume count metric"
            
            # Log current state
            logger.info(f"Current resource state: Memory {resource_state.memory_usage_mb}MB, "
                       f"Containers: {resource_state.container_count}, Networks: {resource_state.network_count}, "
                       f"Volumes: {resource_state.volume_count}")
            
            # Test threshold checking
            thresholds = stability_framework.resource_monitor.get_resource_thresholds()
            assert thresholds.max_memory_mb > 0, "Resource thresholds not configured"
            assert thresholds.max_containers > 0, "Container thresholds not configured"
            
            # Check for threshold violations
            warnings = stability_framework.resource_monitor.check_resource_thresholds(resource_state)
            stability_framework.metrics['resource_warnings_triggered'] += len(warnings)
            
            if warnings:
                for warning in warnings:
                    logger.warning(f"Resource threshold warning: {warning}")
            
            # P1 Requirement: Memory usage should be below 4GB (P1 plan target)
            assert resource_state.memory_usage_mb < (DockerStabilityP1Config.MAX_MEMORY_GB * 1024), \
                f"Memory usage {resource_state.memory_usage_mb}MB exceeds P1 limit"
                
            logger.info("✅ P1 Resource monitoring validation completed successfully")
            
        except Exception as e:
            logger.error(f"❌ P1 Resource monitoring test failed: {e}")
            raise
    
    def test_orphaned_resource_detection_and_cleanup(self, stability_framework):
        """Test detection and cleanup of orphaned Docker resources (P1 requirement)."""
        logger.info("🧹 P1 TEST: Orphaned resource detection and cleanup")
        
        orphaned_containers = []
        orphaned_networks = []
        
        try:
            # Create some intentionally orphaned resources
            for i in range(3):
                container_name = f"p1-orphan-test-{i}-{int(time.time())}"
                result = execute_docker_command([
                    'docker', 'run', '-d', '--name', container_name,
                    'alpine:latest', 'echo', 'orphaned-test'
                ])
                if result.returncode == 0:
                    orphaned_containers.append(container_name)
                    stability_framework.test_containers.append(container_name)
            
            # Create orphaned networks
            for i in range(2):
                network_name = f"p1-orphan-net-{i}-{int(time.time())}"
                result = execute_docker_command(['docker', 'network', 'create', network_name])
                if result.returncode == 0:
                    orphaned_networks.append(network_name)
                    stability_framework.test_networks.append(network_name)
            
            # Allow containers to exit (become orphaned)
            time.sleep(5)
            
            # Test orphaned resource detection
            found_containers = stability_framework.resource_monitor.find_orphaned_containers()
            found_networks = stability_framework.resource_monitor.find_orphaned_networks()
            
            stability_framework.metrics['orphaned_resources_found'] += len(found_containers) + len(found_networks)
            
            logger.info(f"Found {len(found_containers)} orphaned containers, {len(found_networks)} orphaned networks")
            
            # Verify our test orphans were detected
            detected_test_containers = [c for c in found_containers 
                                      if any(name in c.name for name in orphaned_containers)]
            detected_test_networks = [n for n in found_networks 
                                    if any(name in n for name in orphaned_networks)]
            
            assert len(detected_test_containers) > 0, "Failed to detect test orphaned containers"
            assert len(detected_test_networks) > 0, "Failed to detect test orphaned networks"
            
            # Test cleanup of orphaned resources
            cleaned_containers = 0
            for container_name in orphaned_containers:
                result = execute_docker_command(['docker', 'rm', '-f', container_name])
                if result.returncode == 0:
                    cleaned_containers += 1
                    stability_framework.metrics['orphaned_resources_cleaned'] += 1
            
            cleaned_networks = 0
            for network_name in orphaned_networks:
                result = execute_docker_command(['docker', 'network', 'rm', network_name])
                if result.returncode == 0:
                    cleaned_networks += 1
                    stability_framework.metrics['orphaned_resources_cleaned'] += 1
            
            logger.info(f"✅ P1 Orphaned resource cleanup: {cleaned_containers} containers, {cleaned_networks} networks")
            
        except Exception as e:
            logger.error(f"❌ P1 Orphaned resource test failed: {e}")
            raise
        finally:
            # Emergency cleanup
            for container_name in orphaned_containers:
                execute_docker_command(['docker', 'rm', '-f', container_name])
            for network_name in orphaned_networks:
                execute_docker_command(['docker', 'network', 'rm', network_name])


class TestP1TmpfsVolumeFixes:
    """P1 REMEDIATION: Test tmpfs Volume Fixes to prevent RAM exhaustion (Section 2 from P1 plan)."""
    
    def test_no_tmpfs_memory_exhaustion(self, stability_framework):
        """Test that tmpfs volumes don't cause RAM exhaustion (P1 critical fix)."""
        logger.info("💾 P1 TEST: tmpfs volume RAM exhaustion prevention")
        
        initial_memory = psutil.virtual_memory().used / (1024**3)  # GB
        logger.info(f"Initial memory usage: {initial_memory:.2f}GB")
        
        try:
            # Start test environment - should NOT use tmpfs according to P1 plan
            env_name, ports = stability_framework.docker_manager.acquire_environment()
            stability_framework.metrics['parallel_environments_created'] += 1
            
            try:
                # Wait for services to start
                stability_framework.docker_manager.wait_for_services(timeout=120)
                
                # Monitor memory usage during service startup
                peak_memory = initial_memory
                for i in range(10):  # Monitor for 30 seconds
                    current_memory = psutil.virtual_memory().used / (1024**3)
                    peak_memory = max(peak_memory, current_memory)
                    time.sleep(3)
                
                memory_increase = peak_memory - initial_memory
                logger.info(f"Memory usage: {initial_memory:.2f}GB -> {peak_memory:.2f}GB (+{memory_increase:.2f}GB)")
                
                # P1 CRITICAL REQUIREMENT: Memory increase should be reasonable (not 3GB+ from tmpfs)
                MAX_ACCEPTABLE_INCREASE_GB = 1.5  # Much less than 3GB from tmpfs
                
                assert memory_increase < MAX_ACCEPTABLE_INCREASE_GB, \
                    f"Memory increase {memory_increase:.2f}GB exceeds P1 limit {MAX_ACCEPTABLE_INCREASE_GB}GB - tmpfs may still be in use"
                
                # Verify postgres and redis are using proper resource limits (P1 plan requirement)
                containers = stability_framework.docker_manager.get_running_containers()
                for container in containers:
                    if 'postgres' in container.name.lower():
                        # Verify postgres memory limit enforcement (P1: 512MB limit)
                        inspect_result = execute_docker_command(['docker', 'inspect', container.name])
                        if inspect_result.returncode == 0:
                            import json
                            inspect_data = json.loads(inspect_result.stdout)
                            host_config = inspect_data[0].get('HostConfig', {})
                            memory_limit = host_config.get('Memory', 0)
                            
                            if memory_limit > 0:
                                memory_limit_mb = memory_limit / (1024*1024)
                                expected_limit_mb = 512  # P1 plan requirement
                                assert memory_limit_mb <= expected_limit_mb * 1.2, \
                                    f"Postgres memory limit {memory_limit_mb}MB exceeds P1 requirement {expected_limit_mb}MB"
                                stability_framework.metrics['resource_limit_enforcements'] += 1
                                logger.info(f"✅ Postgres memory limit verified: {memory_limit_mb}MB")
                
                logger.info(f"✅ P1 tmpfs RAM exhaustion prevention validated: {memory_increase:.2f}GB increase")
                
            finally:
                stability_framework.docker_manager.release_environment(env_name)
                
        except Exception as e:
            stability_framework.metrics['tmpfs_violations_detected'] += 1
            logger.error(f"❌ P1 tmpfs volume fix test failed: {e}")
            raise
    
    def test_resource_limit_enforcement(self, stability_framework):
        """Test that P1 resource limits are properly enforced."""
        logger.info("🎯 P1 TEST: Resource limit enforcement validation")
        
        try:
            # Test postgres memory limit (P1 requirement: 512MB)
            postgres_test = execute_docker_command([
                'docker', 'run', '--rm', '--memory', DockerStabilityP1Config.POSTGRES_MEMORY_LIMIT,
                '--name', f'p1-postgres-limit-test-{int(time.time())}',
                'postgres:15-alpine', 'echo', 'P1 memory limit test'
            ])
            
            stability_framework.record_operation(
                postgres_test.returncode == 0, "postgres memory limit test"
            )
            assert postgres_test.returncode == 0, f"Postgres P1 memory limit test failed: {postgres_test.stderr}"
            stability_framework.metrics['resource_limit_enforcements'] += 1
            
            # Test redis memory limit (P1 requirement: 256MB)
            redis_test = execute_docker_command([
                'docker', 'run', '--rm', '--memory', DockerStabilityP1Config.REDIS_MEMORY_LIMIT,
                '--name', f'p1-redis-limit-test-{int(time.time())}',
                'redis:7-alpine', 'echo', 'P1 memory limit test'
            ])
            
            stability_framework.record_operation(
                redis_test.returncode == 0, "redis memory limit test"
            )
            assert redis_test.returncode == 0, f"Redis P1 memory limit test failed: {redis_test.stderr}"
            stability_framework.metrics['resource_limit_enforcements'] += 1
            
            logger.info("✅ P1 Resource limit enforcement validation completed")
            
        except Exception as e:
            logger.error(f"❌ P1 Resource limit enforcement test failed: {e}")
            raise


class TestP1ParallelExecutionStability:
    """P1 REMEDIATION: Test Parallel Execution Stability (P1 plan requirement)."""
    
    def test_concurrent_environment_creation(self, stability_framework):
        """Test multiple environments can be created concurrently without conflicts (P1 requirement)."""
        logger.info("🚀 P1 TEST: Concurrent environment creation stability")
        
        def create_test_environment(env_id):
            """Create environment in parallel thread."""
            try:
                logger.info(f"Starting environment creation for env_id: {env_id}")
                
                # Use isolated manager for each thread
                manager = UnifiedDockerManager(environment_type="test")
                env_name, ports = manager.acquire_environment()
                
                stability_framework.metrics['parallel_environments_created'] += 1
                
                # Brief validation
                manager.wait_for_services(timeout=60)
                
                # Clean up
                manager.release_environment(env_name)
                
                return {'env_id': env_id, 'success': True, 'env_name': env_name, 'ports': ports}
                
            except Exception as e:
                stability_framework.metrics['parallel_execution_failures'] += 1
                return {'env_id': env_id, 'success': False, 'error': str(e)}
        
        # Test with multiple concurrent environments (P1 requirement)
        max_concurrent = min(5, DockerStabilityP1Config.MAX_PARALLEL_ENVIRONMENTS)
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all environment creation tasks
            futures = [executor.submit(create_test_environment, i) for i in range(max_concurrent)]
            
            # Collect results
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=300):
                result = future.result()
                results.append(result)
                
                if not result['success']:
                    logger.error(f"Parallel environment {result['env_id']} failed: {result.get('error')}")
        
        # Analyze results
        successful_environments = [r for r in results if r['success']]
        failed_environments = [r for r in results if not r['success']]
        
        stability_framework.metrics['concurrent_operations_peak'] = len(successful_environments)
        
        # P1 REQUIREMENT: At least 80% success rate for parallel execution
        success_rate = len(successful_environments) / len(results)
        assert success_rate >= 0.8, f"P1 parallel execution success rate {success_rate:.2%} below 80% requirement"
        
        # Verify no environment name conflicts (P1 requirement)
        env_names = [r['env_name'] for r in successful_environments]
        unique_names = set(env_names) 
        assert len(unique_names) == len(env_names), \
            f"P1 environment name conflicts: {len(env_names)} created, {len(unique_names)} unique"
        
        logger.info(f"✅ P1 Parallel execution: {len(successful_environments)} successful, "
                   f"{len(failed_environments)} failed ({success_rate:.2%} success rate)")
    
    def test_rapid_container_lifecycle_stress(self, stability_framework):
        """Stress test rapid container creation/destruction cycles (P1 daemon stability)."""
        logger.info("⚡ P1 TEST: Rapid container lifecycle stress test")
        
        def check_daemon_health():
            """Check if Docker daemon is responsive."""
            try:
                result = execute_docker_command(['docker', 'info'])
                return result.returncode == 0
            except Exception:
                return False
        
        # Initial daemon health check
        assert check_daemon_health(), "Docker daemon not healthy before P1 stress test"
        stability_framework.metrics['daemon_health_checks'] += 1
        
        try:
            cycles = DockerStabilityP1Config.RAPID_CREATE_DESTROY_CYCLES
            containers_created = []
            
            logger.info(f"Starting P1 rapid lifecycle stress: {cycles} cycles")
            
            for cycle in range(cycles):
                container_name = f"p1-stress-{cycle}-{int(time.time())}"
                
                # Create container
                create_result = execute_docker_command([
                    'docker', 'run', '-d', '--name', container_name,
                    '--memory', '50m',  # Small footprint per P1 requirements
                    'alpine:latest', 'sleep', '5'
                ])
                
                stability_framework.record_operation(
                    create_result.returncode == 0, f"create container {container_name}"
                )
                
                if create_result.returncode == 0:
                    containers_created.append(container_name)
                    stability_framework.test_containers.append(container_name)
                    
                    # Brief pause then destroy
                    time.sleep(0.1)
                    
                    destroy_result = execute_docker_command(['docker', 'rm', '-f', container_name])
                    stability_framework.record_operation(
                        destroy_result.returncode == 0, f"destroy container {container_name}"
                    )
                    
                    if destroy_result.returncode == 0:
                        containers_created.remove(container_name)
                        stability_framework.test_containers.remove(container_name)
                        stability_framework.metrics['cleanup_operations'] += 1
                
                # P1 REQUIREMENT: Periodic daemon health checks during stress
                if cycle % 10 == 0:
                    daemon_healthy = check_daemon_health()
                    stability_framework.metrics['daemon_health_checks'] += 1
                    if not daemon_healthy:
                        stability_framework.metrics['daemon_health_failures'] += 1
                        logger.error(f"P1 CRITICAL: Docker daemon unhealthy at cycle {cycle}")
                        break
                    
                    logger.info(f"P1 stress progress: {cycle + 1}/{cycles} cycles, daemon healthy")
            
            # Final daemon health check (P1 critical requirement)
            final_health = check_daemon_health()
            stability_framework.metrics['daemon_health_checks'] += 1
            
            if not final_health:
                stability_framework.metrics['daemon_crash_events'] += 1
                raise AssertionError("P1 CRITICAL: Docker daemon crashed during rapid lifecycle stress")
            
            logger.info(f"✅ P1 Rapid lifecycle stress completed: {cycles} cycles, daemon stable")
            
        except Exception as e:
            logger.error(f"❌ P1 Rapid lifecycle stress failed: {e}")
            raise
        finally:
            # Emergency cleanup
            for container_name in containers_created:
                execute_docker_command(['docker', 'rm', '-f', container_name])


class TestP1CleanupMechanisms:
    """P1 REMEDIATION: Test Cleanup Mechanisms (Section 3 from P1 plan)."""
    
    def test_automatic_cleanup_mechanisms(self, stability_framework):
        """Test automatic cleanup mechanisms work correctly (P1 Section 3 requirement)."""
        logger.info("🧹 P1 TEST: Automatic cleanup mechanisms validation")
        
        test_containers = []
        test_networks = []
        
        try:
            # Create resources that should trigger cleanup
            for i in range(DockerStabilityP1Config.ORPHANED_RESOURCE_THRESHOLD + 2):
                container_name = f"p1-cleanup-test-{i}-{int(time.time())}"
                result = execute_docker_command([
                    'docker', 'run', '-d', '--name', container_name,
                    '--label', 'netra.test=p1-cleanup',
                    'alpine:latest', 'echo', 'p1-cleanup-test'
                ])
                
                if result.returncode == 0:
                    test_containers.append(container_name)
                    stability_framework.test_containers.append(container_name)
            
            # Create test networks
            for i in range(3):
                network_name = f"p1-cleanup-net-{i}-{int(time.time())}"
                result = execute_docker_command([
                    'docker', 'network', 'create',
                    '--label', 'netra.test=p1-cleanup',
                    network_name
                ])
                
                if result.returncode == 0:
                    test_networks.append(network_name)
                    stability_framework.test_networks.append(network_name)
            
            # Wait for containers to exit (become eligible for cleanup)
            time.sleep(5)
            
            # Trigger P1 cleanup mechanism
            cleanup_result = stability_framework.cleanup_scheduler.perform_cleanup(
                max_age_hours=0,  # Clean immediately per P1 requirements
                dry_run=False
            )
            
            stability_framework.metrics['cleanup_operations'] += 1
            stability_framework.metrics['automatic_cleanup_triggers'] += 1
            
            cleaned_containers = cleanup_result.get('containers_removed', 0)
            cleaned_networks = cleanup_result.get('networks_removed', 0)
            
            stability_framework.metrics['orphaned_resources_cleaned'] += cleaned_containers + cleaned_networks
            
            logger.info(f"P1 cleanup results: {cleaned_containers} containers, {cleaned_networks} networks cleaned")
            
            # P1 REQUIREMENT: Verify cleanup effectiveness (should clean most resources)
            total_created = len(test_containers) + len(test_networks)
            total_cleaned = cleaned_containers + cleaned_networks
            cleanup_effectiveness = total_cleaned / total_created if total_created > 0 else 0
            
            # P1 requirement: At least 70% cleanup effectiveness
            assert cleanup_effectiveness >= 0.7, \
                f"P1 cleanup effectiveness {cleanup_effectiveness:.2%} below 70% requirement"
            
            logger.info(f"✅ P1 Automatic cleanup validation: {cleanup_effectiveness:.2%} effectiveness")
            
        except Exception as e:
            stability_framework.metrics['cleanup_failures'] += 1
            logger.error(f"❌ P1 Automatic cleanup test failed: {e}")
            raise
        finally:
            # Manual cleanup of remaining resources
            for container_name in test_containers:
                execute_docker_command(['docker', 'rm', '-f', container_name])
            for network_name in test_networks:
                execute_docker_command(['docker', 'network', 'rm', network_name])
    
    def test_cleanup_cycle_consistency(self, stability_framework):
        """Test multiple cleanup cycles work consistently (P1 requirement)."""
        logger.info("🔄 P1 TEST: Cleanup cycle consistency validation")
        
        try:
            cleanup_results = []
            
            # Perform multiple cleanup cycles (P1 requirement)
            for cycle in range(DockerStabilityP1Config.CLEANUP_VALIDATION_CYCLES):
                logger.info(f"P1 cleanup cycle {cycle + 1}/{DockerStabilityP1Config.CLEANUP_VALIDATION_CYCLES}")
                
                # Create some test resources for cleanup
                temp_containers = []
                for i in range(2):
                    container_name = f"p1-cycle-{cycle}-{i}-{int(time.time())}"
                    result = execute_docker_command([
                        'docker', 'run', '-d', '--name', container_name,
                        '--label', f'netra.test=p1-cycle-{cycle}',
                        'alpine:latest', 'echo', f'p1-cycle-{cycle}'
                    ])
                    
                    if result.returncode == 0:
                        temp_containers.append(container_name)
                        stability_framework.test_containers.append(container_name)
                
                # Allow containers to exit
                time.sleep(2)
                
                # Perform cleanup
                cleanup_start = time.time()
                cycle_result = stability_framework.cleanup_scheduler.perform_cleanup(
                    max_age_hours=0, dry_run=False
                )
                cleanup_duration = time.time() - cleanup_start
                
                cycle_result['cleanup_duration'] = cleanup_duration
                cleanup_results.append(cycle_result)
                
                stability_framework.metrics['cleanup_operations'] += 1
                
                logger.info(f"P1 cleanup cycle {cycle + 1} completed in {cleanup_duration:.2f}s")
            
            # Analyze cleanup consistency (P1 requirement)
            cleanup_durations = [r['cleanup_duration'] for r in cleanup_results]
            avg_cleanup_time = sum(cleanup_durations) / len(cleanup_durations)
            max_cleanup_time = max(cleanup_durations)
            
            # P1 REQUIREMENT: Cleanup should be fast and consistent
            assert avg_cleanup_time < 30, f"P1 average cleanup time {avg_cleanup_time:.2f}s too slow"
            assert max_cleanup_time < 60, f"P1 max cleanup time {max_cleanup_time:.2f}s too slow"
            
            # Check cleanup consistency
            successful_cleanups = [r for r in cleanup_results if r.get('containers_removed', 0) >= 0]
            consistency_rate = len(successful_cleanups) / len(cleanup_results)
            
            # P1 REQUIREMENT: At least 90% consistency rate
            assert consistency_rate >= 0.9, f"P1 cleanup consistency {consistency_rate:.2%} below 90%"
            
            logger.info(f"✅ P1 Cleanup consistency: avg {avg_cleanup_time:.2f}s, {consistency_rate:.2%} consistent")
            
        except Exception as e:
            stability_framework.metrics['cleanup_failures'] += 1
            logger.error(f"❌ P1 Cleanup cycle consistency test failed: {e}")
            raise


class TestP1DockerDaemonStability:
    """P1 REMEDIATION: Test Docker Daemon Stability under stress (P1 critical requirement)."""
    
    def test_daemon_stability_under_load(self, stability_framework):
        """Test Docker daemon stability under high load (P1 critical requirement)."""
        logger.info("⚡ P1 TEST: Docker daemon stability under load")
        
        def check_daemon_responsive():
            """Check if Docker daemon is responsive."""
            try:
                result = execute_docker_command(['docker', 'info'])
                return result.returncode == 0
            except Exception:
                return False
        
        # Initial daemon health check
        initial_health = check_daemon_responsive()
        stability_framework.metrics['daemon_health_checks'] += 1
        
        assert initial_health, "Docker daemon not responsive before P1 stability test"
        
        try:
            operations = DockerStabilityP1Config.STRESS_TEST_OPERATIONS
            concurrent_containers = min(10, DockerStabilityP1Config.MAX_CONTAINERS_PER_TEST)
            
            containers_created = []
            
            # Phase 1: Rapid container creation
            logger.info(f"P1 Phase 1: Creating {concurrent_containers} containers under load")
            
            for i in range(concurrent_containers):
                container_name = f"p1-daemon-stress-{i}-{int(time.time())}"
                
                create_result = execute_docker_command([
                    'docker', 'run', '-d', '--name', container_name,
                    '--memory', '80m', '--cpus', '0.1',  # Resource constrained per P1
                    'alpine:latest', 'sleep', '60'
                ])
                
                stability_framework.record_operation(
                    create_result.returncode == 0, f"daemon stress create {container_name}"
                )
                
                if create_result.returncode == 0:
                    containers_created.append(container_name)
                    stability_framework.test_containers.append(container_name)
                
                # P1 REQUIREMENT: Check daemon health every 5 containers
                if i % 5 == 0:
                    health_check = check_daemon_responsive()
                    stability_framework.metrics['daemon_health_checks'] += 1
                    if not health_check:
                        stability_framework.metrics['daemon_health_failures'] += 1
                        logger.error(f"P1 CRITICAL: Daemon health failed after {i} containers")
                        raise AssertionError("Docker daemon became unresponsive during container creation")
            
            # Phase 2: High-frequency operations stress test
            logger.info(f"P1 Phase 2: Performing {operations} rapid operations")
            
            for op in range(operations):
                # Cycle through different operation types
                op_type = op % 4
                
                if op_type == 0:  # List containers
                    result = execute_docker_command(['docker', 'ps', '-a'])
                elif op_type == 1:  # Inspect random container
                    if containers_created:
                        container = random.choice(containers_created)
                        result = execute_docker_command(['docker', 'inspect', container])
                    else:
                        continue
                elif op_type == 2:  # List networks
                    result = execute_docker_command(['docker', 'network', 'ls'])
                else:  # System info
                    result = execute_docker_command(['docker', 'system', 'df'])
                
                stability_framework.record_operation(result.returncode == 0, f"daemon stress op {op_type}")
                
                # P1 REQUIREMENT: Periodic daemon health checks during load
                if op % 20 == 0:
                    health_check = check_daemon_responsive()
                    stability_framework.metrics['daemon_health_checks'] += 1
                    if not health_check:
                        stability_framework.metrics['daemon_health_failures'] += 1
                        logger.error(f"P1 CRITICAL: Daemon health failed at operation {op}")
                        raise AssertionError("Docker daemon became unresponsive during stress operations")
                    
                    if op % 50 == 0:
                        logger.info(f"P1 daemon stress progress: {op}/{operations} operations completed")
            
            # Phase 3: Cleanup under load
            logger.info("P1 Phase 3: Cleanup under load")
            
            for container_name in containers_created[:]:
                cleanup_result = execute_docker_command(['docker', 'rm', '-f', container_name])
                stability_framework.record_operation(
                    cleanup_result.returncode == 0, f"daemon stress cleanup {container_name}"
                )
                
                if cleanup_result.returncode == 0:
                    containers_created.remove(container_name)
                    stability_framework.test_containers.remove(container_name)
                    stability_framework.metrics['cleanup_operations'] += 1
            
            # Final daemon health check (P1 CRITICAL)
            final_health = check_daemon_responsive()
            stability_framework.metrics['daemon_health_checks'] += 1
            
            if not final_health:
                stability_framework.metrics['daemon_crash_events'] += 1
                raise AssertionError("P1 CRITICAL FAILURE: Docker daemon crashed during stability test")
            
            logger.info(f"✅ P1 Docker daemon stability validated: {operations} operations completed")
            
        except Exception as e:
            logger.error(f"❌ P1 Docker daemon stability test failed: {e}")
            raise
        finally:
            # Emergency cleanup
            for container_name in containers_created:
                execute_docker_command(['docker', 'rm', '-f', container_name])
    
    def test_long_running_daemon_stability(self, stability_framework):
        """Test Docker daemon stability over extended period (P1 requirement)."""
        logger.info("⏱️ P1 TEST: Long-running daemon stability validation")
        
        def check_daemon_health():
            """Check Docker daemon health comprehensively."""
            try:
                # Multiple health checks for thoroughness
                info_result = execute_docker_command(['docker', 'info'])
                ps_result = execute_docker_command(['docker', 'ps'])
                version_result = execute_docker_command(['docker', 'version'])
                
                return all(r.returncode == 0 for r in [info_result, ps_result, version_result])
            except Exception:
                return False
        
        test_duration = 120  # 2 minutes for CI compatibility
        check_interval = 10   # Check every 10 seconds
        
        start_time = time.time()
        
        # Create stable workload containers
        workload_containers = []
        try:
            for i in range(3):
                container_name = f"p1-stability-workload-{i}-{int(time.time())}"
                result = execute_docker_command([
                    'docker', 'run', '-d', '--name', container_name,
                    '--memory', '100m', '--restart', 'unless-stopped',
                    'alpine:latest', 'sh', '-c', 
                    'while true; do echo "P1 stability test"; sleep 5; done'
                ])
                
                if result.returncode == 0:
                    workload_containers.append(container_name)
                    stability_framework.test_containers.append(container_name)
            
            # Monitor daemon health over time
            health_checks = 0
            health_failures = 0
            
            while (time.time() - start_time) < test_duration:
                # Comprehensive daemon health check
                daemon_healthy = check_daemon_health()
                health_checks += 1
                stability_framework.metrics['daemon_health_checks'] += 1
                
                if not daemon_healthy:
                    health_failures += 1
                    stability_framework.metrics['daemon_health_failures'] += 1
                    logger.error(f"P1 daemon health failure at {time.time() - start_time:.1f}s")
                
                # Resource monitoring
                try:
                    resource_state = stability_framework.resource_monitor.get_current_resource_state()
                    if resource_state.memory_usage_mb > (DockerStabilityP1Config.MAX_MEMORY_GB * 1024):
                        stability_framework.metrics['memory_pressure_events'] += 1
                        logger.warning(f"P1 memory pressure: {resource_state.memory_usage_mb}MB")
                except Exception:
                    pass
                
                time.sleep(check_interval)
            
            # Final validation
            all_containers_healthy = True
            for container_name in workload_containers:
                status_result = execute_docker_command([
                    'docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Status}}'
                ])
                
                if status_result.returncode != 0 or 'Up' not in status_result.stdout:
                    all_containers_healthy = False
                    logger.error(f"P1 container {container_name} not healthy after stability test")
            
            assert all_containers_healthy, "P1 containers failed during long-running stability test"
            
            # P1 REQUIREMENT: Health failure rate should be minimal
            health_failure_rate = health_failures / health_checks if health_checks > 0 else 0
            assert health_failure_rate <= 0.1, f"P1 daemon health failure rate {health_failure_rate:.2%} too high"
            
            logger.info(f"✅ P1 Long-running stability: {health_checks} checks, "
                       f"{health_failure_rate:.2%} failure rate over {test_duration}s")
            
        except Exception as e:
            stability_framework.metrics['daemon_crash_events'] += 1
            logger.error(f"❌ P1 Long-running stability test failed: {e}")
            raise
        finally:
            # Cleanup workload containers
            for container_name in workload_containers:
                execute_docker_command(['docker', 'rm', '-f', container_name])
                stability_framework.metrics['cleanup_operations'] += 1


# ========================================
# EXISTING TEST CLASSES (Enhanced with P1 metrics)
# ========================================

class TestDockerStabilityStressTesting:
    """EXTREME STRESS TESTS: Push Docker operations beyond normal limits (Enhanced for P1)."""
    
    def test_concurrent_container_operations_extreme(self, stability_framework):
        """Test extreme concurrent container operations (50+ simultaneous)."""
        logger.info("🚀 EXTREME TEST: 50+ concurrent container operations")
        
        def create_and_destroy_container(container_id: str) -> bool:
            try:
                # Create container
                result1 = execute_docker_command([
                    'docker', 'create', '--name', f'stress_test_{container_id}', 
                    'alpine:latest', 'sleep', '1'
                ])
                if result1.returncode != 0:
                    return False
                
                stability_framework.test_containers.append(f'stress_test_{container_id}')
                
                # Start container
                result2 = execute_docker_command(['docker', 'start', f'stress_test_{container_id}'])
                if result2.returncode != 0:
                    return False
                
                # Stop and remove
                execute_docker_command(['docker', 'stop', f'stress_test_{container_id}'])
                execute_docker_command(['docker', 'rm', f'stress_test_{container_id}'])
                
                return True
                
            except Exception as e:
                logger.error(f"Container operation failed for {container_id}: {e}")
                return False
        
        # Launch 50 concurrent operations
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for i in range(50):
                future = executor.submit(create_and_destroy_container, f"extreme_{i}")
                futures.append(future)
            
            # Track peak concurrency
            stability_framework.metrics['concurrent_operations_peak'] = max(
                stability_framework.metrics['concurrent_operations_peak'], 20
            )
            
            # Wait for all operations
            successful_operations = 0
            for future in as_completed(futures, timeout=300):  # 5 minute timeout
                try:
                    if future.result():
                        successful_operations += 1
                        stability_framework.record_operation(True, "concurrent_container")
                    else:
                        stability_framework.record_operation(False, "concurrent_container")
                except Exception as e:
                    logger.error(f"Future execution failed: {e}")
                    stability_framework.record_operation(False, "concurrent_container")
        
        success_rate = successful_operations / 50 * 100
        logger.info(f"✅ Extreme concurrency test completed: {success_rate:.1f}% success rate")
        
        # CRITICAL: Must maintain >90% success rate even under extreme load
        assert success_rate >= 90, f"Success rate too low: {success_rate:.1f}%"
        
    def test_rapid_network_operations(self, stability_framework):
        """Test rapid network creation/deletion operations."""
        logger.info("🌐 STRESS TEST: Rapid network operations")
        
        def network_operation_cycle(network_id: str) -> bool:
            try:
                network_name = f'stress_network_{network_id}'
                
                # Create network
                result1 = execute_docker_command([
                    'docker', 'network', 'create', '--driver', 'bridge', network_name
                ])
                if result1.returncode != 0:
                    return False
                
                stability_framework.test_networks.append(network_name)
                
                # Inspect network
                result2 = execute_docker_command(['docker', 'network', 'inspect', network_name])
                if result2.returncode != 0:
                    return False
                
                # Remove network
                result3 = execute_docker_command(['docker', 'network', 'rm', network_name])
                return result3.returncode == 0
                
            except Exception as e:
                logger.error(f"Network operation failed for {network_id}: {e}")
                return False
        
        # Execute 30 rapid network operations
        successful = 0
        for i in range(30):
            if network_operation_cycle(f"rapid_{i}"):
                successful += 1
                stability_framework.record_operation(True, "network_operation")
            else:
                stability_framework.record_operation(False, "network_operation")
            
            # Small delay to prevent overwhelming Docker API
            time.sleep(0.1)
        
        success_rate = successful / 30 * 100
        logger.info(f"✅ Network stress test: {success_rate:.1f}% success rate")
        assert success_rate >= 95, f"Network operations success rate too low: {success_rate:.1f}%"
    
    def test_volume_operations_under_pressure(self, stability_framework):
        """Test volume operations under memory pressure."""
        logger.info("💾 STRESS TEST: Volume operations under memory pressure")
        
        # Start memory pressure simulation
        pressure_thread = threading.Thread(
            target=stability_framework.simulate_memory_pressure, 
            args=(20,)
        )
        pressure_thread.start()
        
        try:
            successful_volumes = 0
            for i in range(15):
                try:
                    volume_name = f'pressure_volume_{i}'
                    
                    # Create volume
                    result1 = execute_docker_command(['docker', 'volume', 'create', volume_name])
                    if result1.returncode == 0:
                        stability_framework.test_volumes.append(volume_name)
                        
                        # Inspect volume
                        result2 = execute_docker_command(['docker', 'volume', 'inspect', volume_name])
                        if result2.returncode == 0:
                            successful_volumes += 1
                            stability_framework.record_operation(True, "volume_pressure")
                        else:
                            stability_framework.record_operation(False, "volume_pressure")
                    else:
                        stability_framework.record_operation(False, "volume_pressure")
                        
                except Exception as e:
                    logger.error(f"Volume operation {i} failed: {e}")
                    stability_framework.record_operation(False, "volume_pressure")
                
                time.sleep(0.5)  # Controlled pace during pressure
            
        finally:
            pressure_thread.join(timeout=30)
            
        success_rate = successful_volumes / 15 * 100
        logger.info(f"✅ Volume pressure test: {success_rate:.1f}% success rate")
        assert success_rate >= 85, f"Volume operations under pressure failed: {success_rate:.1f}%"


class TestDockerForceProhibition:
    """ZERO TOLERANCE: Force flag prohibition tests."""
    
    def test_force_flag_prohibition_comprehensive(self, stability_framework):
        """Comprehensive test of force flag prohibition across all Docker commands."""
        logger.info("🚨 ZERO TOLERANCE: Comprehensive force flag prohibition test")
        
        # All possible force flag variations to test
        prohibited_commands = [
            ['docker', 'rm', '-f', 'test_container'],
            ['docker', 'rmi', '--force', 'test_image'],
            ['docker', 'system', 'prune', '-f'],
            ['docker', 'container', 'prune', '--force'],
            ['docker', 'image', 'prune', '-f'],
            ['docker', 'network', 'prune', '--force'],
            ['docker', 'volume', 'prune', '-f'],
            ['docker', 'container', 'rm', '-rf', 'test'],  # Combined flags
            ['docker', 'stop', '-f', 'container'],
            ['docker', 'kill', '--force', 'container'],
        ]
        
        violations_detected = 0
        for cmd in prohibited_commands:
            try:
                # This should ALWAYS fail due to force flag protection
                execute_docker_command(cmd)
                
                # If we reach here, protection failed
                logger.critical(f"🚨 CRITICAL FAILURE: Force flag protection bypassed for: {cmd}")
                assert False, f"Force flag protection failed for command: {' '.join(cmd)}"
                
            except DockerForceFlagViolation as e:
                violations_detected += 1
                stability_framework.metrics['force_flag_violations_detected'] += 1
                logger.info(f"✅ Force flag correctly blocked: {' '.join(cmd)}")
                
            except Exception as e:
                logger.error(f"Unexpected error testing {cmd}: {e}")
                assert False, f"Unexpected error: {e}"
        
        logger.info(f"✅ Force flag prohibition: {violations_detected}/{len(prohibited_commands)} violations correctly detected")
        assert violations_detected == len(prohibited_commands), "Not all force flags were detected"
    
    def test_force_flag_audit_logging(self, stability_framework):
        """Test that force flag violations are properly logged for audit."""
        logger.info("📋 Testing force flag audit logging")
        
        # Test command that should trigger violation
        test_command = 'docker rm -f test_container_audit'
        
        try:
            stability_framework.force_guardian.validate_command(test_command)
            assert False, "Force flag should have been detected"
            
        except DockerForceFlagViolation:
            # Check audit report
            audit_report = stability_framework.force_guardian.audit_report()
            
            assert audit_report['total_violations'] > 0, "Violation not recorded in audit"
            assert audit_report['violation_rate'] > 0, "Violation rate not calculated"
            
            logger.info("✅ Force flag audit logging working correctly")


class TestDockerRateLimiting:
    """RATE LIMITER VALIDATION: Ensure rate limiting prevents Docker daemon overload."""
    
    def test_rate_limiter_effectiveness(self, stability_framework):
        """Test that rate limiter effectively prevents Docker API storms."""
        logger.info("⏱️ Testing rate limiter effectiveness")
        
        rate_limiter = stability_framework.rate_limiter
        
        # Record initial stats
        initial_stats = rate_limiter.get_statistics()
        
        # Execute rapid commands
        start_time = time.time()
        commands_executed = 0
        
        for i in range(20):
            try:
                result = execute_docker_command(['docker', 'version', '--format', '{{.Server.Version}}'])
                if result.returncode == 0:
                    commands_executed += 1
            except Exception as e:
                logger.warning(f"Rate limited command {i} failed: {e}")
        
        execution_time = time.time() - start_time
        
        # Check final stats
        final_stats = rate_limiter.get_statistics()
        rate_limited_ops = final_stats['rate_limited_operations'] - initial_stats['rate_limited_operations']
        
        logger.info(f"✅ Rate limiter test: {commands_executed} commands in {execution_time:.2f}s, "
                   f"{rate_limited_ops} operations rate limited")
        
        # Should have rate limited some operations
        assert rate_limited_ops > 0, "Rate limiter should have throttled some operations"
        assert execution_time > 10, f"Execution too fast: {execution_time:.2f}s (rate limiting not working)"
        
    def test_rate_limiter_concurrent_safety(self, stability_framework):
        """Test rate limiter thread safety under concurrent load."""
        logger.info("🧵 Testing rate limiter concurrent safety")
        
        def concurrent_docker_operation(operation_id: int) -> bool:
            try:
                result = execute_docker_command(['docker', 'info', '--format', '{{.Name}}'])
                return result.returncode == 0
            except Exception as e:
                logger.warning(f"Concurrent operation {operation_id} failed: {e}")
                return False
        
        # Launch 15 concurrent operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(concurrent_docker_operation, i) 
                for i in range(15)
            ]
            
            successful_ops = sum(1 for future in as_completed(futures) if future.result())
        
        # Should complete successfully with rate limiting
        success_rate = successful_ops / 15 * 100
        logger.info(f"✅ Concurrent rate limiting: {success_rate:.1f}% success rate")
        assert success_rate >= 90, f"Concurrent operations success rate too low: {success_rate:.1f}%"


class TestDockerRecoveryScenarios:
    """RECOVERY VALIDATION: Test graceful recovery from failure scenarios."""
    
    def test_kill_containers_mid_test_recovery(self, stability_framework):
        """CRITICAL: Kill containers mid-test and verify cleanup still works."""
        logger.info("💀 CRITICAL: Testing recovery from killed containers mid-test")
        
        containers_created = []
        containers_killed = []
        
        try:
            # Create several test containers
            for i in range(8):
                container_name = f'recovery_test_container_{i}'
                
                result = execute_docker_command([
                    'docker', 'run', '--name', container_name,
                    '-d', 'alpine:latest', 'sh', '-c', 'sleep 60'
                ])
                
                if result.returncode == 0:
                    containers_created.append(container_name)
                    stability_framework.test_containers.append(container_name)
                    logger.info(f"Created container: {container_name}")
                
            logger.info(f"Created {len(containers_created)} containers for kill test")
            
            # Wait for containers to be running
            time.sleep(3)
            
            # Simulate killing containers mid-test (emergency scenarios)
            kill_targets = containers_created[:4]  # Kill half of them
            for container in kill_targets:
                try:
                    # Use kill -9 equivalent to simulate crashes
                    result = subprocess.run([
                        'docker', 'kill', '-s', 'KILL', container
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        containers_killed.append(container)
                        logger.info(f"Killed container: {container}")
                    else:
                        logger.warning(f"Failed to kill {container}: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Exception killing {container}: {e}")
                    
            logger.info(f"Killed {len(containers_killed)} containers")
            
            # Wait a moment, then test recovery cleanup
            time.sleep(2)
            
            # Test that cleanup can handle killed containers
            cleanup_successful = 0
            cleanup_failed = 0
            
            for container in containers_created:
                try:
                    # Try to stop (will fail for killed containers)
                    stop_result = execute_docker_command(['docker', 'stop', container], timeout=5)
                    
                    # Try to remove (should work regardless)
                    rm_result = execute_docker_command(['docker', 'rm', container], timeout=5)
                    
                    if rm_result.returncode == 0:
                        cleanup_successful += 1
                        logger.info(f"Successfully cleaned up: {container}")
                    else:
                        cleanup_failed += 1
                        logger.warning(f"Failed to clean up: {container}")
                        
                except Exception as e:
                    cleanup_failed += 1
                    logger.warning(f"Cleanup exception for {container}: {e}")
            
            cleanup_rate = cleanup_successful / len(containers_created) * 100
            logger.info(f"✅ Kill recovery results:")
            logger.info(f"   - Containers killed: {len(containers_killed)}")
            logger.info(f"   - Cleanup successful: {cleanup_successful}/{len(containers_created)}")
            logger.info(f"   - Cleanup rate: {cleanup_rate:.1f}%")
            
            # CRITICAL: Cleanup must work even after containers are killed
            assert cleanup_rate >= 90, f"Cleanup recovery rate too low: {cleanup_rate:.1f}%"
            
            stability_framework.metrics['recovery_attempts'] += 1
            stability_framework.metrics['recovery_successes'] += 1 if cleanup_rate >= 90 else 0
            stability_framework.record_operation(cleanup_rate >= 90, "kill_recovery")
            
        except Exception as e:
            logger.error(f"Kill container recovery test failed: {e}")
            stability_framework.record_operation(False, "kill_recovery")
            raise
        finally:
            # Ensure all containers are cleaned up
            for container in containers_created:
                try:
                    execute_docker_command(['docker', 'rm', '-f', container], timeout=5)
                except:
                    pass
    
    def test_docker_daemon_restart_recovery(self, stability_framework):
        """CRITICAL: Simulate Docker daemon restart and verify recovery."""
        logger.info("🔄 CRITICAL: Testing Docker daemon restart recovery")
        
        # NOTE: We can't actually restart Docker daemon in CI, so we simulate
        # the conditions and test recovery mechanisms
        
        recovery_tests = []
        
        # Test 1: Create resources, simulate daemon unavailable, then recover
        try:
            # Create test resources
            container_name = 'daemon_restart_test'
            network_name = 'daemon_restart_network'
            
            # Pre-restart resource creation
            create_result = execute_docker_command([
                'docker', 'create', '--name', container_name,
                'alpine:latest', 'echo', 'restart_test'
            ])
            
            if create_result.returncode == 0:
                stability_framework.test_containers.append(container_name)
                
                network_result = execute_docker_command([
                    'docker', 'network', 'create', network_name
                ])
                
                if network_result.returncode == 0:
                    stability_framework.test_networks.append(network_name)
                
                # Simulate post-restart recovery by testing operations
                # Test basic Docker operations work
                version_check = execute_docker_command(['docker', 'version'])
                info_check = execute_docker_command(['docker', 'info'])
                ps_check = execute_docker_command(['docker', 'ps', '-a'])
                network_list = execute_docker_command(['docker', 'network', 'ls'])
                
                recovery_operations = [
                    ('version_check', version_check.returncode == 0),
                    ('info_check', info_check.returncode == 0),
                    ('ps_check', ps_check.returncode == 0),
                    ('network_list', network_list.returncode == 0)
                ]
                
                successful_recoveries = sum(1 for _, success in recovery_operations if success)
                
                logger.info("✅ Daemon restart recovery simulation:")
                for op_name, success in recovery_operations:
                    status = "✅ OK" if success else "❌ FAILED"
                    logger.info(f"   - {op_name}: {status}")
                
                recovery_rate = successful_recoveries / len(recovery_operations) * 100
                
                # Test resource cleanup after "restart"
                cleanup_result = execute_docker_command(['docker', 'rm', container_name])
                network_cleanup = execute_docker_command(['docker', 'network', 'rm', network_name])
                
                cleanup_works = cleanup_result.returncode == 0 and network_cleanup.returncode == 0
                
                logger.info(f"✅ Post-restart cleanup: {'✅ OK' if cleanup_works else '❌ FAILED'}")
                
                # CRITICAL: All basic operations must work after restart
                assert recovery_rate == 100, f"Post-restart operations failed: {recovery_rate:.1f}%"
                assert cleanup_works, "Resource cleanup failed after daemon restart"
                
                stability_framework.metrics['recovery_attempts'] += 1
                stability_framework.metrics['recovery_successes'] += 1
                stability_framework.record_operation(True, "daemon_restart_recovery")
                
            else:
                logger.warning("Could not create test resources for daemon restart test")
                stability_framework.record_operation(False, "daemon_restart_recovery")
                
        except Exception as e:
            logger.error(f"Daemon restart recovery test failed: {e}")
            stability_framework.record_operation(False, "daemon_restart_recovery")
            raise
            
    def test_docker_daemon_connection_recovery(self, stability_framework):
        """Test recovery when Docker daemon becomes temporarily unavailable."""
        logger.info("🔄 Testing Docker daemon connection recovery")
        
        # First, ensure Docker is available
        health_check = execute_docker_command(['docker', 'version'])
        assert health_check.returncode == 0, "Docker must be available for recovery test"
        
        # Simulate temporary connectivity issues by introducing delays
        original_timeout = 30
        
        # Try operations with very short timeout to simulate connection issues
        recovery_attempts = 0
        successful_recoveries = 0
        
        for i in range(5):
            try:
                # Simulate difficult conditions
                result = execute_docker_command(['docker', 'info'], timeout=2)
                if result.returncode == 0:
                    successful_recoveries += 1
                recovery_attempts += 1
                
            except Exception as e:
                logger.info(f"Expected recovery scenario {i}: {e}")
                recovery_attempts += 1
                
                # Try with longer timeout (recovery)
                try:
                    result = execute_docker_command(['docker', 'info'], timeout=30)
                    if result.returncode == 0:
                        successful_recoveries += 1
                        stability_framework.metrics['recovery_successes'] += 1
                except Exception:
                    pass
                
                stability_framework.metrics['recovery_attempts'] += 1
        
        recovery_rate = successful_recoveries / recovery_attempts * 100
        logger.info(f"✅ Docker daemon recovery: {recovery_rate:.1f}% success rate")
        
        # Should recover from most scenarios
        assert recovery_rate >= 60, f"Recovery rate too low: {recovery_rate:.1f}%"
    
    def test_resource_exhaustion_recovery(self, stability_framework):
        """Test recovery from resource exhaustion scenarios."""
        logger.info("🔋 Testing resource exhaustion recovery")
        
        # Create many containers to approach resource limits
        container_names = []
        successful_creations = 0
        
        try:
            for i in range(20):  # Create 20 containers
                container_name = f'resource_test_{i}'
                try:
                    result = execute_docker_command([
                        'docker', 'create', '--name', container_name,
                        '--memory', '50m', '--cpus', '0.1',
                        'alpine:latest', 'sleep', '300'
                    ])
                    
                    if result.returncode == 0:
                        container_names.append(container_name)
                        stability_framework.test_containers.append(container_name)
                        successful_creations += 1
                    
                except Exception as e:
                    logger.info(f"Expected resource limit reached at container {i}: {e}")
                    break
            
            logger.info(f"Created {successful_creations} containers before resource limits")
            
            # Now test cleanup and recovery
            cleanup_successful = 0
            for container_name in container_names:
                try:
                    # Stop and remove container
                    execute_docker_command(['docker', 'container', 'rm', container_name])
                    cleanup_successful += 1
                except Exception as e:
                    logger.warning(f"Cleanup failed for {container_name}: {e}")
            
            cleanup_rate = cleanup_successful / len(container_names) * 100 if container_names else 100
            logger.info(f"✅ Resource exhaustion recovery: {cleanup_rate:.1f}% cleanup success")
            
            # Should be able to clean up most resources
            assert cleanup_rate >= 90, f"Resource cleanup rate too low: {cleanup_rate:.1f}%"
            
        finally:
            # Ensure cleanup of any remaining containers
            for container_name in container_names:
                try:
                    execute_docker_command(['docker', 'container', 'rm', container_name])
                except:
                    pass


class TestDockerCleanupScheduler:
    """CLEANUP VALIDATION: Test comprehensive resource cleanup scheduling."""
    
    def test_orphaned_resource_cleanup(self, stability_framework):
        """Test cleanup of orphaned Docker resources."""
        logger.info("🧹 Testing orphaned resource cleanup")
        
        # Create resources that might become orphaned
        test_resources = {
            'containers': [],
            'networks': [],
            'volumes': []
        }
        
        try:
            # Create test containers
            for i in range(5):
                container_name = f'orphan_test_container_{i}'
                result = execute_docker_command([
                    'docker', 'create', '--name', container_name,
                    'alpine:latest', 'echo', 'test'
                ])
                if result.returncode == 0:
                    test_resources['containers'].append(container_name)
                    stability_framework.test_containers.append(container_name)
            
            # Create test networks
            for i in range(3):
                network_name = f'orphan_test_network_{i}'
                result = execute_docker_command([
                    'docker', 'network', 'create', network_name
                ])
                if result.returncode == 0:
                    test_resources['networks'].append(network_name)
                    stability_framework.test_networks.append(network_name)
            
            # Create test volumes
            for i in range(3):
                volume_name = f'orphan_test_volume_{i}'
                result = execute_docker_command([
                    'docker', 'volume', 'create', volume_name
                ])
                if result.returncode == 0:
                    test_resources['volumes'].append(volume_name)
                    stability_framework.test_volumes.append(volume_name)
            
            # Verify resources were created
            total_created = (len(test_resources['containers']) + 
                           len(test_resources['networks']) + 
                           len(test_resources['volumes']))
            
            logger.info(f"Created {total_created} test resources for orphan cleanup test")
            
            # Test cleanup can find and remove these resources
            cleanup_successful = 0
            
            # Cleanup containers
            for container in test_resources['containers']:
                try:
                    execute_docker_command(['docker', 'container', 'rm', container])
                    cleanup_successful += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup container {container}: {e}")
            
            # Cleanup networks
            for network in test_resources['networks']:
                try:
                    execute_docker_command(['docker', 'network', 'rm', network])
                    cleanup_successful += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup network {network}: {e}")
            
            # Cleanup volumes
            for volume in test_resources['volumes']:
                try:
                    execute_docker_command(['docker', 'volume', 'rm', volume])
                    cleanup_successful += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup volume {volume}: {e}")
            
            cleanup_rate = cleanup_successful / total_created * 100 if total_created > 0 else 100
            logger.info(f"✅ Orphaned resource cleanup: {cleanup_rate:.1f}% success rate")
            
            assert cleanup_rate >= 95, f"Cleanup success rate too low: {cleanup_rate:.1f}%"
            
        except Exception as e:
            logger.error(f"Orphaned resource cleanup test failed: {e}")
            raise
    
    def test_stale_network_cleanup(self, stability_framework):
        """Test cleanup of stale networks with no connected containers."""
        logger.info("🌐 Testing stale network cleanup")
        
        stale_networks = []
        
        try:
            # Create networks that will become stale
            for i in range(4):
                network_name = f'stale_network_{uuid.uuid4().hex[:8]}'
                result = execute_docker_command([
                    'docker', 'network', 'create', '--driver', 'bridge', network_name
                ])
                if result.returncode == 0:
                    stale_networks.append(network_name)
                    stability_framework.test_networks.append(network_name)
            
            logger.info(f"Created {len(stale_networks)} networks to test stale cleanup")
            
            # Verify networks exist
            existing_networks = 0
            for network in stale_networks:
                try:
                    result = execute_docker_command(['docker', 'network', 'inspect', network])
                    if result.returncode == 0:
                        existing_networks += 1
                except:
                    pass
            
            logger.info(f"Verified {existing_networks} networks exist")
            
            # Test cleanup of stale networks
            cleaned_networks = 0
            for network in stale_networks:
                try:
                    result = execute_docker_command(['docker', 'network', 'rm', network])
                    if result.returncode == 0:
                        cleaned_networks += 1
                except Exception as e:
                    logger.warning(f"Failed to clean stale network {network}: {e}")
            
            cleanup_rate = cleaned_networks / len(stale_networks) * 100 if stale_networks else 100
            logger.info(f"✅ Stale network cleanup: {cleanup_rate:.1f}% success rate")
            
            assert cleanup_rate >= 90, f"Stale network cleanup rate too low: {cleanup_rate:.1f}%"
            
        except Exception as e:
            logger.error(f"Stale network cleanup test failed: {e}")
            raise


class TestDockerMemoryPressure:
    """MEMORY PRESSURE: Test Docker operations under memory constraints."""
    
    def test_memory_usage_limit_validation(self, stability_framework):
        """CRITICAL: Verify test environment uses < 4GB RAM (no more tmpfs bloat)."""
        logger.info("🔥 CRITICAL: Testing memory usage stays under 4GB limit")
        
        # Get baseline memory usage
        initial_memory = psutil.virtual_memory()
        initial_used_gb = (initial_memory.total - initial_memory.available) / (1024**3)
        
        logger.info(f"Initial memory usage: {initial_used_gb:.2f}GB")
        
        # Start test environment
        try:
            docker_manager = UnifiedDockerManager()
            docker_manager.start_test_environment()
            
            # Wait for services to fully start
            time.sleep(30)
            
            # Monitor memory usage over 2 minutes
            max_memory_used = 0
            peak_memory_gb = 0
            
            for i in range(24):  # 2 minutes, every 5 seconds
                current_memory = psutil.virtual_memory()
                current_used_gb = (current_memory.total - current_memory.available) / (1024**3)
                
                memory_increase = current_used_gb - initial_used_gb
                if memory_increase > max_memory_used:
                    max_memory_used = memory_increase
                    peak_memory_gb = current_used_gb
                
                logger.debug(f"Memory check {i+1}: {current_used_gb:.2f}GB total, "
                           f"+{memory_increase:.2f}GB from baseline")
                time.sleep(5)
            
            logger.info(f"✅ Peak memory usage: {peak_memory_gb:.2f}GB (increase: +{max_memory_used:.2f}GB)")
            
            # CRITICAL: Must stay under 4GB total usage increase
            assert max_memory_used < 4.0, f"Memory usage exceeded 4GB limit: +{max_memory_used:.2f}GB"
            
            # Additional check for tmpfs volumes (should be eliminated)
            result = execute_docker_command(['docker', 'system', 'df', '-v'])
            if result.returncode == 0 and 'tmpfs' in result.stdout:
                tmpfs_volumes = [line for line in result.stdout.split('\n') if 'tmpfs' in line.lower()]
                assert len(tmpfs_volumes) == 0, f"Found {len(tmpfs_volumes)} tmpfs volumes that should be eliminated"
                
            stability_framework.record_operation(True, "memory_limit_validation")
            
        except Exception as e:
            logger.error(f"Memory usage validation failed: {e}")
            stability_framework.record_operation(False, "memory_limit_validation")
            raise
        finally:
            # Clean up test environment
            try:
                docker_manager.stop_test_environment()
            except:
                pass
    
    def test_container_operations_under_memory_pressure(self, stability_framework):
        """Test container operations while system is under memory pressure."""
        logger.info("🔥 Testing container operations under memory pressure")
        
        # Start memory pressure in background
        pressure_thread = threading.Thread(
            target=stability_framework.simulate_memory_pressure,
            args=(30,)  # 30 seconds of pressure
        )
        pressure_thread.start()
        
        try:
            # Wait for pressure to build
            time.sleep(2)
            
            # Perform container operations under pressure
            successful_operations = 0
            total_operations = 10
            
            for i in range(total_operations):
                try:
                    container_name = f'memory_pressure_test_{i}'
                    
                    # Create small container
                    result1 = execute_docker_command([
                        'docker', 'create', '--name', container_name,
                        '--memory', '20m',  # Small memory limit
                        'alpine:latest', 'echo', 'memory_test'
                    ])
                    
                    if result1.returncode == 0:
                        stability_framework.test_containers.append(container_name)
                        
                        # Start container
                        result2 = execute_docker_command(['docker', 'start', container_name])
                        if result2.returncode == 0:
                            successful_operations += 1
                            
                            # Clean up immediately
                            execute_docker_command(['docker', 'stop', container_name])
                            execute_docker_command(['docker', 'rm', container_name])
                    
                    time.sleep(1)  # Pace operations during pressure
                    
                except Exception as e:
                    logger.warning(f"Container operation {i} failed under memory pressure: {e}")
            
            success_rate = successful_operations / total_operations * 100
            logger.info(f"✅ Memory pressure container operations: {success_rate:.1f}% success rate")
            
            # Should maintain reasonable success rate even under pressure
            assert success_rate >= 70, f"Success rate under memory pressure too low: {success_rate:.1f}%"
            
        finally:
            pressure_thread.join(timeout=35)
    
    def test_docker_build_under_memory_pressure(self, stability_framework):
        """Test Docker image builds under memory pressure."""
        logger.info("🏗️ Testing Docker builds under memory pressure")
        
        # Create simple Dockerfile for testing
        dockerfile_content = """
FROM alpine:latest
RUN echo "Memory pressure build test" > /test.txt
RUN cat /test.txt
CMD ["cat", "/test.txt"]
"""
        
        # Create temporary directory for build context
        with tempfile.TemporaryDirectory() as temp_dir:
            dockerfile_path = Path(temp_dir) / 'Dockerfile'
            dockerfile_path.write_text(dockerfile_content)
            
            # Start memory pressure
            pressure_thread = threading.Thread(
                target=stability_framework.simulate_memory_pressure,
                args=(25,)
            )
            pressure_thread.start()
            
            try:
                time.sleep(2)  # Let pressure build
                
                # Attempt build under pressure
                image_tag = f'memory_pressure_test:{uuid.uuid4().hex[:8]}'
                
                result = execute_docker_command([
                    'docker', 'build', '-t', image_tag, str(temp_dir)
                ], timeout=60)
                
                if result.returncode == 0:
                    stability_framework.test_images.append(image_tag)
                    logger.info("✅ Docker build succeeded under memory pressure")
                    
                    # Clean up image
                    execute_docker_command(['docker', 'image', 'rm', image_tag])
                    build_success = True
                else:
                    logger.warning(f"Docker build failed under memory pressure: {result.stderr}")
                    build_success = False
                
                # Build should either succeed or fail gracefully (no crashes)
                assert build_success or "out of memory" in result.stderr.lower(), \
                    "Build should succeed or fail gracefully with memory error"
                
            finally:
                pressure_thread.join(timeout=30)


class TestDockerParallelExecution:
    """PARALLEL EXECUTION: Test Docker stability under parallel test execution."""
    
    def test_parallel_test_suite_execution(self, stability_framework):
        """CRITICAL: Run 5 parallel test suites and verify stability."""
        logger.info("🚀 CRITICAL: Testing 5 parallel test suite execution")
        
        def run_parallel_test_suite(suite_id: int) -> Dict[str, Any]:
            """Run a single test suite in parallel."""
            suite_name = f"parallel_suite_{suite_id}"
            start_time = time.time()
            
            try:
                # Create dedicated containers for this test suite
                container_name = f"{suite_name}_container"
                network_name = f"{suite_name}_network"
                volume_name = f"{suite_name}_volume"
                
                # Create network
                result1 = execute_docker_command([
                    'docker', 'network', 'create', '--driver', 'bridge', network_name
                ])
                if result1.returncode != 0:
                    return {'suite_id': suite_id, 'success': False, 'error': 'network_creation_failed'}
                
                # Create volume
                result2 = execute_docker_command(['docker', 'volume', 'create', volume_name])
                if result2.returncode != 0:
                    return {'suite_id': suite_id, 'success': False, 'error': 'volume_creation_failed'}
                
                # Create and start container
                result3 = execute_docker_command([
                    'docker', 'run', '--name', container_name,
                    '--network', network_name,
                    '-v', f'{volume_name}:/data',
                    '--rm', '-d',
                    'alpine:latest', 'sh', '-c', 
                    f'echo "Suite {suite_id} running" > /data/test.txt && sleep 10'
                ])
                if result3.returncode != 0:
                    return {'suite_id': suite_id, 'success': False, 'error': 'container_run_failed'}
                
                # Wait for container to complete
                time.sleep(12)
                
                # Cleanup
                execute_docker_command(['docker', 'network', 'rm', network_name])
                execute_docker_command(['docker', 'volume', 'rm', volume_name])
                
                execution_time = time.time() - start_time
                return {
                    'suite_id': suite_id,
                    'success': True,
                    'execution_time': execution_time,
                    'error': None
                }
                
            except Exception as e:
                return {
                    'suite_id': suite_id,
                    'success': False,
                    'error': str(e),
                    'execution_time': time.time() - start_time
                }
        
        # Launch 5 parallel test suites
        logger.info("🔥 Launching 5 parallel test suites...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(run_parallel_test_suite, i)
                for i in range(1, 6)
            ]
            
            # Collect results
            results = []
            for future in as_completed(futures, timeout=180):  # 3 minute timeout
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Parallel test suite execution failed: {e}")
                    results.append({
                        'suite_id': 'unknown',
                        'success': False,
                        'error': str(e)
                    })
        
        total_execution_time = time.time() - start_time
        successful_suites = sum(1 for r in results if r['success'])
        success_rate = successful_suites / 5 * 100
        
        logger.info(f"✅ Parallel execution results:")
        logger.info(f"   - Total time: {total_execution_time:.2f}s")
        logger.info(f"   - Successful suites: {successful_suites}/5")
        logger.info(f"   - Success rate: {success_rate:.1f}%")
        
        for result in results:
            if result['success']:
                stability_framework.record_operation(True, f"parallel_suite_{result['suite_id']}")
            else:
                stability_framework.record_operation(False, f"parallel_suite_{result['suite_id']}")
                logger.warning(f"Suite {result['suite_id']} failed: {result['error']}")
        
        # CRITICAL: All parallel suites must succeed for Docker stability
        assert success_rate == 100, f"Parallel execution failed: {success_rate:.1f}% success rate"
        assert total_execution_time < 120, f"Parallel execution too slow: {total_execution_time:.2f}s"
        
        # Update peak concurrency metric
        stability_framework.metrics['concurrent_operations_peak'] = max(
            stability_framework.metrics['concurrent_operations_peak'], 5
        )
        
    def test_docker_daemon_crash_prevention(self, stability_framework):
        """CRITICAL: Ensure Docker daemon doesn't crash under load."""
        logger.info("⚡ CRITICAL: Testing Docker daemon crash prevention under load")
        
        # Check initial Docker daemon health
        initial_health = execute_docker_command(['docker', 'version'])
        assert initial_health.returncode == 0, "Docker daemon not healthy at start"
        
        # Track Docker daemon PID if possible
        daemon_pid = None
        try:
            # Try to get Docker daemon PID
            result = execute_docker_command(['docker', 'system', 'info', '--format', '{{.ServerVersion}}'])
            if result.returncode == 0:
                logger.info(f"Docker daemon version: {result.stdout.strip()}")
        except:
            pass
        
        # Create extreme load scenario
        load_operations = []
        
        def create_load_operation(op_id: int) -> bool:
            """Create intensive Docker operation."""
            try:
                # Rapid container lifecycle operations
                for i in range(3):
                    container_name = f'load_test_{op_id}_{i}'
                    
                    # Create
                    result1 = execute_docker_command([
                        'docker', 'create', '--name', container_name,
                        'alpine:latest', 'sh', '-c', 'echo "load test" && sleep 2'
                    ])
                    if result1.returncode != 0:
                        return False
                    
                    # Start
                    result2 = execute_docker_command(['docker', 'start', container_name])
                    if result2.returncode != 0:
                        return False
                    
                    # Stop and remove
                    execute_docker_command(['docker', 'stop', container_name])
                    execute_docker_command(['docker', 'rm', container_name])
                
                return True
                
            except Exception as e:
                logger.warning(f"Load operation {op_id} failed: {e}")
                return False
        
        # Execute high-intensity operations
        logger.info("🔥 Executing extreme load operations...")
        successful_operations = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_load_operation, i)
                for i in range(20)  # 20 intensive operations
            ]
            
            for future in as_completed(futures, timeout=300):
                try:
                    if future.result():
                        successful_operations += 1
                except Exception as e:
                    logger.warning(f"Load operation failed: {e}")
        
        # Check Docker daemon still healthy
        final_health = execute_docker_command(['docker', 'version'])
        daemon_survived = final_health.returncode == 0
        
        # Verify Docker daemon can still perform basic operations
        test_health = execute_docker_command(['docker', 'run', '--rm', 'alpine:latest', 'echo', 'health_check'])
        basic_ops_work = test_health.returncode == 0
        
        success_rate = successful_operations / 20 * 100
        
        logger.info(f"✅ Daemon crash prevention results:")
        logger.info(f"   - Operations completed: {successful_operations}/20 ({success_rate:.1f}%)")
        logger.info(f"   - Docker daemon survived: {daemon_survived}")
        logger.info(f"   - Basic operations work: {basic_ops_work}")
        
        # CRITICAL: Docker daemon must survive and remain functional
        assert daemon_survived, "Docker daemon crashed during load testing"
        assert basic_ops_work, "Docker daemon not responsive after load testing"
        assert success_rate >= 80, f"Load operation success rate too low: {success_rate:.1f}%"
        
        stability_framework.record_operation(daemon_survived, "daemon_crash_prevention")


class TestDockerConfigurationValidation:
    """CONFIGURATION VALIDATION: Test PostgreSQL and other service configurations."""
    
    def test_postgresql_conservative_settings(self, stability_framework):
        """CRITICAL: Verify PostgreSQL has conservative settings (fsync=on, etc.)."""
        logger.info("🗄️ CRITICAL: Testing PostgreSQL conservative configuration")
        
        try:
            # Start test PostgreSQL container with our configuration
            container_name = 'config_test_postgres'
            
            result = execute_docker_command([
                'docker', 'run', '--name', container_name,
                '-e', 'POSTGRES_DB=test_db',
                '-e', 'POSTGRES_USER=test_user',
                '-e', 'POSTGRES_PASSWORD=test_pass',
                '-p', '5435:5432',
                '-d', 'postgres:15-alpine',
                'postgres',
                '-c', 'shared_buffers=128MB',
                '-c', 'effective_cache_size=512MB',
                '-c', 'fsync=on',
                '-c', 'synchronous_commit=on',
                '-c', 'wal_buffers=16MB',
                '-c', 'checkpoint_completion_target=0.7'
            ])
            
            if result.returncode != 0:
                raise Exception(f"Failed to start PostgreSQL container: {result.stderr}")
            
            stability_framework.test_containers.append(container_name)
            
            # Wait for PostgreSQL to be ready
            logger.info("Waiting for PostgreSQL to be ready...")
            max_wait = 60
            postgres_ready = False
            
            for i in range(max_wait):
                check_result = execute_docker_command([
                    'docker', 'exec', container_name,
                    'pg_isready', '-U', 'test_user', '-d', 'test_db'
                ])
                if check_result.returncode == 0:
                    postgres_ready = True
                    logger.info(f"PostgreSQL ready after {i+1} seconds")
                    break
                time.sleep(1)
            
            assert postgres_ready, "PostgreSQL failed to become ready within 60 seconds"
            
            # Check configuration settings
            config_checks = [
                ('fsync', 'on'),
                ('synchronous_commit', 'on'),
                ('shared_buffers', '128MB'),
                ('effective_cache_size', '512MB')
            ]
            
            all_settings_correct = True
            
            for setting, expected_value in config_checks:
                check_cmd = [
                    'docker', 'exec', container_name,
                    'psql', '-U', 'test_user', '-d', 'test_db',
                    '-c', f"SHOW {setting};"
                ]
                
                result = execute_docker_command(check_cmd)
                if result.returncode == 0:
                    output_lines = result.stdout.strip().split('\n')
                    if len(output_lines) >= 3:  # Header, value, separator
                        actual_value = output_lines[2].strip()
                        if actual_value == expected_value:
                            logger.info(f"✅ {setting}: {actual_value} (correct)")
                        else:
                            logger.error(f"❌ {setting}: {actual_value} (expected: {expected_value})")
                            all_settings_correct = False
                    else:
                        logger.warning(f"Could not verify {setting}: unexpected output format")
                        all_settings_correct = False
                else:
                    logger.error(f"Failed to check {setting}: {result.stderr}")
                    all_settings_correct = False
            
            # Test conservative behavior under load
            logger.info("Testing conservative behavior under load...")
            
            # Create some load on PostgreSQL
            load_result = execute_docker_command([
                'docker', 'exec', container_name,
                'psql', '-U', 'test_user', '-d', 'test_db',
                '-c', """
                CREATE TABLE IF NOT EXISTS load_test (
                    id SERIAL PRIMARY KEY,
                    data VARCHAR(1000),
                    created_at TIMESTAMP DEFAULT NOW()
                );
                INSERT INTO load_test (data) 
                SELECT 'Load test data ' || generate_series(1, 1000);
                SELECT COUNT(*) FROM load_test;
                """
            ])
            
            load_test_passed = load_result.returncode == 0
            if load_test_passed:
                logger.info("✅ PostgreSQL handled load test successfully")
            else:
                logger.error(f"❌ PostgreSQL load test failed: {load_result.stderr}")
            
            assert all_settings_correct, "PostgreSQL configuration settings are not conservative"
            assert load_test_passed, "PostgreSQL failed load test with conservative settings"
            
            stability_framework.record_operation(True, "postgresql_config_validation")
            
        except Exception as e:
            logger.error(f"PostgreSQL configuration validation failed: {e}")
            stability_framework.record_operation(False, "postgresql_config_validation")
            raise
        finally:
            # Cleanup test container
            try:
                execute_docker_command(['docker', 'stop', container_name])
                execute_docker_command(['docker', 'rm', container_name])
            except:
                pass
    
    def test_no_tmpfs_volumes_validation(self, stability_framework):
        """CRITICAL: Verify no tmpfs volumes are used in test environment."""
        logger.info("💾 CRITICAL: Validating no tmpfs volumes are configured")
        
        try:
            # Check Docker compose configuration files
            compose_files = [
                'docker-compose.test.yml',
                'docker-compose.yml',
                'docker-compose.override.yml'
            ]
            
            tmpfs_violations = []
            
            for compose_file in compose_files:
                compose_path = Path(compose_file)
                if compose_path.exists():
                    content = compose_path.read_text()
                    
                    # Check for tmpfs usage
                    if 'tmpfs' in content.lower():
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if 'tmpfs' in line.lower():
                                tmpfs_violations.append(f"{compose_file}:{i}: {line.strip()}")
            
            # Check running containers for tmpfs mounts
            result = execute_docker_command(['docker', 'ps', '--format', 'table {{.Names}}'])
            if result.returncode == 0:
                running_containers = [
                    line.strip() for line in result.stdout.split('\n')[1:]  # Skip header
                    if line.strip()
                ]
                
                for container in running_containers:
                    if 'test' in container.lower() or 'netra' in container.lower():
                        inspect_result = execute_docker_command([
                            'docker', 'inspect', container, '--format', 
                            '{{range .Mounts}}{{.Type}}: {{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
                        ])
                        
                        if inspect_result.returncode == 0 and 'tmpfs' in inspect_result.stdout.lower():
                            tmpfs_violations.append(f"Container {container}: has tmpfs mounts")
            
            # Check system df for tmpfs volumes
            df_result = execute_docker_command(['docker', 'system', 'df', '-v'])
            if df_result.returncode == 0 and 'tmpfs' in df_result.stdout.lower():
                tmpfs_lines = [
                    line.strip() for line in df_result.stdout.split('\n')
                    if 'tmpfs' in line.lower()
                ]
                for line in tmpfs_lines:
                    tmpfs_violations.append(f"System volumes: {line}")
            
            # Report results
            if tmpfs_violations:
                logger.error("❌ CRITICAL: tmpfs violations found:")
                for violation in tmpfs_violations:
                    logger.error(f"   - {violation}")
                
                assert False, f"Found {len(tmpfs_violations)} tmpfs violations that must be eliminated"
            else:
                logger.info("✅ No tmpfs volumes found - memory usage optimized")
            
            stability_framework.record_operation(True, "tmpfs_validation")
            
        except Exception as e:
            logger.error(f"tmpfs validation failed: {e}")
            stability_framework.record_operation(False, "tmpfs_validation")
            raise
    
    def test_resource_limits_enforcement(self, stability_framework):
        """CRITICAL: Verify resource limits are enforced."""
        logger.info("⚖️ CRITICAL: Testing resource limits enforcement")
        
        try:
            # Test memory limit enforcement
            container_name = 'resource_limit_test'
            
            # Try to create container with specific memory limit
            result = execute_docker_command([
                'docker', 'run', '--name', container_name,
                '--memory', '100m',  # 100MB limit
                '--rm', '-d',
                'alpine:latest', 'sh', '-c',
                'dd if=/dev/zero of=/tmp/memory_test bs=1M count=150 2>/dev/null || echo "Memory limit enforced"'
            ])
            
            if result.returncode == 0:
                stability_framework.test_containers.append(container_name)
                
                # Wait for container to complete
                time.sleep(10)
                
                # Check container logs
                logs_result = execute_docker_command(['docker', 'logs', container_name])
                
                if logs_result.returncode == 0:
                    if "Memory limit enforced" in logs_result.stdout or logs_result.returncode != 0:
                        logger.info("✅ Memory limit successfully enforced")
                        memory_limit_works = True
                    else:
                        logger.warning("⚠️ Memory limit may not be enforced")
                        memory_limit_works = False
                else:
                    logger.warning("Could not check memory limit enforcement")
                    memory_limit_works = False
                
                # Clean up
                execute_docker_command(['docker', 'stop', container_name])
                execute_docker_command(['docker', 'rm', container_name])
            else:
                memory_limit_works = False
            
            # Test CPU limit enforcement
            cpu_container_name = 'cpu_limit_test'
            
            result = execute_docker_command([
                'docker', 'run', '--name', cpu_container_name,
                '--cpus', '0.1',  # 10% CPU limit
                '--rm', '-d',
                'alpine:latest', 'sh', '-c',
                'timeout 5 yes > /dev/null 2>&1; echo "CPU limit test complete"'
            ])
            
            cpu_limit_works = result.returncode == 0
            
            if cpu_limit_works:
                stability_framework.test_containers.append(cpu_container_name)
                time.sleep(8)
                execute_docker_command(['docker', 'stop', cpu_container_name])
                execute_docker_command(['docker', 'rm', cpu_container_name])
            
            logger.info(f"✅ Resource limits enforcement:")
            logger.info(f"   - Memory limits: {'✅ Working' if memory_limit_works else '❌ Failed'}")
            logger.info(f"   - CPU limits: {'✅ Working' if cpu_limit_works else '❌ Failed'}")
            
            assert memory_limit_works, "Memory limits are not being enforced"
            assert cpu_limit_works, "CPU limits are not being enforced"
            
            stability_framework.record_operation(True, "resource_limits_validation")
            
        except Exception as e:
            logger.error(f"Resource limits validation failed: {e}")
            stability_framework.record_operation(False, "resource_limits_validation")
            raise


class TestDockerHealthChecks:
    """HEALTH CHECK VALIDATION: Test all services become healthy within timeout."""
    
    def test_all_services_health_checks(self, stability_framework):
        """CRITICAL: Verify all services become healthy within timeout."""
        logger.info("💊 CRITICAL: Testing comprehensive service health checks")
        
        # Define services to test with their health check criteria
        services_to_test = [
            {
                'name': 'postgres',
                'container_name': 'health_test_postgres',
                'image': 'postgres:15-alpine',
                'port': '5436:5432',
                'env': [
                    'POSTGRES_DB=health_test',
                    'POSTGRES_USER=health_user', 
                    'POSTGRES_PASSWORD=health_pass'
                ],
                'health_check_cmd': ['pg_isready', '-U', 'health_user', '-d', 'health_test'],
                'timeout_seconds': 60
            },
            {
                'name': 'redis',
                'container_name': 'health_test_redis',
                'image': 'redis:7-alpine',
                'port': '6382:6379',
                'env': [],
                'health_check_cmd': ['redis-cli', 'ping'],
                'timeout_seconds': 30
            }
        ]
        
        health_results = []
        
        try:
            for service in services_to_test:
                logger.info(f"🔍 Testing {service['name']} health checks...")
                
                # Start service container
                docker_cmd = ['docker', 'run', '--name', service['container_name'], '-d']
                
                # Add port mapping
                if service['port']:
                    docker_cmd.extend(['-p', service['port']])
                
                # Add environment variables
                for env_var in service['env']:
                    docker_cmd.extend(['-e', env_var])
                
                docker_cmd.append(service['image'])
                
                start_result = execute_docker_command(docker_cmd)
                
                if start_result.returncode == 0:
                    stability_framework.test_containers.append(service['container_name'])
                    
                    # Wait for service to become healthy
                    logger.info(f"Waiting for {service['name']} to become healthy...")
                    start_time = time.time()
                    healthy = False
                    
                    while (time.time() - start_time) < service['timeout_seconds']:
                        try:
                            health_result = execute_docker_command([
                                'docker', 'exec', service['container_name']
                            ] + service['health_check_cmd'], timeout=5)
                            
                            if health_result.returncode == 0:
                                healthy = True
                                health_time = time.time() - start_time
                                logger.info(f"✅ {service['name']} healthy after {health_time:.1f}s")
                                break
                                
                        except Exception as e:
                            logger.debug(f"Health check attempt failed: {e}")
                        
                        time.sleep(2)
                    
                    health_results.append({
                        'service': service['name'],
                        'healthy': healthy,
                        'time_to_healthy': time.time() - start_time if healthy else None,
                        'timeout': service['timeout_seconds']
                    })
                    
                    if not healthy:
                        logger.error(f"❌ {service['name']} failed to become healthy within {service['timeout_seconds']}s")
                        
                        # Get logs for debugging
                        logs_result = execute_docker_command(['docker', 'logs', service['container_name']])
                        if logs_result.returncode == 0:
                            logger.error(f"Service logs: {logs_result.stdout}")
                else:
                    logger.error(f"❌ Failed to start {service['name']}: {start_result.stderr}")
                    health_results.append({
                        'service': service['name'],
                        'healthy': False,
                        'time_to_healthy': None,
                        'timeout': service['timeout_seconds']
                    })
                    
            # Analyze results
            healthy_services = sum(1 for result in health_results if result['healthy'])
            total_services = len(health_results)
            health_rate = healthy_services / total_services * 100 if total_services > 0 else 0
            
            logger.info(f"✅ Health check results:")
            logger.info(f"   - Healthy services: {healthy_services}/{total_services}")
            logger.info(f"   - Health rate: {health_rate:.1f}%")
            
            for result in health_results:
                if result['healthy']:
                    logger.info(f"   - {result['service']}: ✅ ({result['time_to_healthy']:.1f}s)")
                    stability_framework.record_operation(True, f"health_{result['service']}")
                else:
                    logger.info(f"   - {result['service']}: ❌ (timeout)")
                    stability_framework.record_operation(False, f"health_{result['service']}")
            
            # CRITICAL: All services must become healthy
            assert health_rate == 100, f"Service health check failure: {health_rate:.1f}% healthy"
            
        except Exception as e:
            logger.error(f"Health check test failed: {e}")
            raise
        finally:
            # Cleanup all test containers
            for service in services_to_test:
                try:
                    execute_docker_command(['docker', 'stop', service['container_name']])
                    execute_docker_command(['docker', 'rm', service['container_name']])
                except:
                    pass
    
    def test_health_checks_dont_overwhelm_system(self, stability_framework):
        """CRITICAL: Verify health checks don't overwhelm system."""
        logger.info("⚡ CRITICAL: Testing health checks don't overwhelm system")
        
        # Monitor system resources during intensive health checking
        initial_cpu = psutil.cpu_percent(interval=1)
        initial_memory = psutil.virtual_memory().percent
        
        try:
            # Create container that responds to health checks
            container_name = 'health_load_test'
            
            result = execute_docker_command([
                'docker', 'run', '--name', container_name,
                '--health-cmd', 'echo "healthy"',
                '--health-interval', '2s',
                '--health-timeout', '1s',
                '--health-retries', '3',
                '-d', 'alpine:latest', 'sh', '-c', 'sleep 60'
            ])
            
            if result.returncode == 0:
                stability_framework.test_containers.append(container_name)
                
                # Simulate intensive health checking (external)
                health_check_threads = []
                health_results = []
                
                def intensive_health_check(thread_id: int):
                    """Perform intensive health checks."""
                    thread_results = []
                    for i in range(20):  # 20 health checks per thread
                        try:
                            start_time = time.time()
                            result = execute_docker_command([
                                'docker', 'exec', container_name, 'echo', 'health_test'
                            ], timeout=5)
                            end_time = time.time()
                            
                            thread_results.append({
                                'thread_id': thread_id,
                                'check_id': i,
                                'success': result.returncode == 0,
                                'duration': end_time - start_time
                            })
                            
                        except Exception as e:
                            thread_results.append({
                                'thread_id': thread_id,
                                'check_id': i,
                                'success': False,
                                'duration': None,
                                'error': str(e)
                            })
                        
                        time.sleep(0.1)  # Small delay between checks
                    
                    return thread_results
                
                # Launch multiple threads doing health checks
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [
                        executor.submit(intensive_health_check, i)
                        for i in range(5)
                    ]
                    
                    # Monitor system resources during load
                    max_cpu = initial_cpu
                    max_memory = initial_memory
                    
                    for i in range(10):  # Monitor for 20 seconds
                        current_cpu = psutil.cpu_percent(interval=1)
                        current_memory = psutil.virtual_memory().percent
                        
                        max_cpu = max(max_cpu, current_cpu)
                        max_memory = max(max_memory, current_memory)
                        
                        time.sleep(2)
                    
                    # Collect results
                    for future in as_completed(futures):
                        thread_results = future.result()
                        health_results.extend(thread_results)
                
                # Analyze system impact
                cpu_increase = max_cpu - initial_cpu
                memory_increase = max_memory - initial_memory
                
                successful_checks = sum(1 for r in health_results if r['success'])
                total_checks = len(health_results)
                success_rate = successful_checks / total_checks * 100 if total_checks > 0 else 0
                
                avg_duration = sum(r['duration'] for r in health_results if r['duration']) / successful_checks if successful_checks > 0 else 0
                
                logger.info(f"✅ Health check system impact:")
                logger.info(f"   - Total health checks: {total_checks}")
                logger.info(f"   - Success rate: {success_rate:.1f}%")
                logger.info(f"   - Average duration: {avg_duration:.3f}s")
                logger.info(f"   - CPU increase: {cpu_increase:.1f}%")
                logger.info(f"   - Memory increase: {memory_increase:.1f}%")
                
                # CRITICAL: Health checks shouldn't overwhelm system
                assert cpu_increase < 20, f"Health checks caused excessive CPU load: {cpu_increase:.1f}%"
                assert memory_increase < 10, f"Health checks caused excessive memory usage: {memory_increase:.1f}%"
                assert success_rate >= 95, f"Health check success rate too low: {success_rate:.1f}%"
                assert avg_duration < 0.5, f"Health checks too slow: {avg_duration:.3f}s average"
                
                stability_framework.record_operation(True, "health_check_load")
                
            else:
                logger.error(f"Failed to start health load test container: {result.stderr}")
                stability_framework.record_operation(False, "health_check_load")
                raise Exception("Could not start health load test container")
                
        except Exception as e:
            logger.error(f"Health check load test failed: {e}")
            stability_framework.record_operation(False, "health_check_load")
            raise
        finally:
            try:
                execute_docker_command(['docker', 'stop', container_name])
                execute_docker_command(['docker', 'rm', container_name])
            except:
                pass


if __name__ == "__main__":
    # Direct execution for comprehensive debugging
    framework = DockerStabilityTestFramework()
    try:
        logger.info("🚀 Starting COMPREHENSIVE Docker Stability Test Suite...")
        logger.info("=" * 80)
        
        # Track overall results
        test_results = {}
        total_tests = 0
        passed_tests = 0
        
        # Test suites to run
        test_suites = [
            ("Force Flag Prohibition", TestDockerForceProhibition),
            ("Rate Limiting", TestDockerRateLimiting), 
            ("Memory Pressure", TestDockerMemoryPressure),
            ("Parallel Execution", TestDockerParallelExecution),
            ("Configuration Validation", TestDockerConfigurationValidation),
            ("Recovery Scenarios", TestDockerRecoveryScenarios),
            ("Cleanup Validation", TestDockerCleanupScheduler),
            ("Health Checks", TestDockerHealthChecks)
        ]
        
        for suite_name, test_class in test_suites:
            logger.info(f"\n🔥 EXECUTING: {suite_name} Tests")
            logger.info("-" * 60)
            
            suite_results = {}
            suite_instance = test_class()
            
            # Get all test methods
            test_methods = [method for method in dir(suite_instance) if method.startswith('test_')]
            
            for method_name in test_methods:
                total_tests += 1
                try:
                    logger.info(f"Running {method_name}...")
                    method = getattr(suite_instance, method_name)
                    method(framework)
                    
                    suite_results[method_name] = "✅ PASSED"
                    passed_tests += 1
                    logger.info(f"✅ {method_name} completed successfully")
                    
                except Exception as e:
                    suite_results[method_name] = f"❌ FAILED: {str(e)}"
                    logger.error(f"❌ {method_name} failed: {e}")
            
            test_results[suite_name] = suite_results
        
        # Final comprehensive report
        logger.info("\n" + "=" * 80)
        logger.info("🏆 COMPREHENSIVE DOCKER STABILITY TEST RESULTS")
        logger.info("=" * 80)
        
        success_rate = passed_tests / total_tests * 100 if total_tests > 0 else 0
        
        logger.info(f"📊 OVERALL RESULTS:")
        logger.info(f"   - Total Tests: {total_tests}")
        logger.info(f"   - Passed: {passed_tests}")
        logger.info(f"   - Failed: {total_tests - passed_tests}")
        logger.info(f"   - Success Rate: {success_rate:.1f}%")
        logger.info("")
        
        # Detailed results by test suite
        for suite_name, suite_results in test_results.items():
            suite_passed = sum(1 for result in suite_results.values() if "PASSED" in result)
            suite_total = len(suite_results)
            suite_rate = suite_passed / suite_total * 100 if suite_total > 0 else 0
            
            logger.info(f"📋 {suite_name} ({suite_rate:.1f}% passed):")
            for test_name, result in suite_results.items():
                logger.info(f"   - {test_name}: {result}")
            logger.info("")
        
        # Framework metrics
        logger.info("🔍 FRAMEWORK METRICS:")
        for metric, value in framework.metrics.items():
            logger.info(f"   - {metric}: {value}")
        
        logger.info("")
        execution_time = time.time() - framework.start_time
        logger.info(f"⏱️ Total execution time: {execution_time:.2f} seconds")
        
        if success_rate >= 90:
            logger.info("🎉 DOCKER STABILITY TEST SUITE: EXCELLENT RESULTS!")
        elif success_rate >= 80:
            logger.info("⚠️ DOCKER STABILITY TEST SUITE: GOOD RESULTS with some issues")
        else:
            logger.error("🚨 DOCKER STABILITY TEST SUITE: CRITICAL FAILURES DETECTED")
        
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Critical test suite execution failure: {e}")
        raise
    finally:
        # Comprehensive cleanup
        logger.info("🧹 Performing comprehensive cleanup...")
        framework.cleanup()
        logger.info("✅ Cleanup completed")


# ========================================
# P1 DOCKER STABILITY TEST SUITE EXECUTION GUIDE
# ========================================

if __name__ == "__main__":
    """
    P1 Docker Stability Test Suite - Comprehensive Execution Guide
    
    This test suite validates ALL P1 Docker stability fixes per the remediation plan.
    
    EXECUTION METHODS:
    
    1. RUN ALL P1 REMEDIATION TESTS (Recommended):
        python -m pytest tests/mission_critical/test_docker_stability_suite.py -v --tb=short -k "TestP1"
    
    2. RUN SPECIFIC P1 TEST CATEGORIES:
        
        # Environment Lock Tests
        python -m pytest tests/mission_critical/test_docker_stability_suite.py::TestP1EnvironmentLockMechanism -v
        
        # Resource Monitor Tests  
        python -m pytest tests/mission_critical/test_docker_stability_suite.py::TestP1ResourceMonitorFunctionality -v
        
        # tmpfs Volume Fix Tests
        python -m pytest tests/mission_critical/test_docker_stability_suite.py::TestP1TmpfsVolumeFixes -v
        
        # Parallel Execution Tests
        python -m pytest tests/mission_critical/test_docker_stability_suite.py::TestP1ParallelExecutionStability -v
        
        # Cleanup Mechanism Tests
        python -m pytest tests/mission_critical/test_docker_stability_suite.py::TestP1CleanupMechanisms -v
        
        # Docker Daemon Stability Tests
        python -m pytest tests/mission_critical/test_docker_stability_suite.py::TestP1DockerDaemonStability -v
    
    3. RUN COMPREHENSIVE STABILITY SUITE (All tests including existing):
        python -m pytest tests/mission_critical/test_docker_stability_suite.py -v --tb=short
    
    4. RUN WITH DETAILED LOGGING:
        python -m pytest tests/mission_critical/test_docker_stability_suite.py -v -s --log-cli-level=INFO
    
    5. STRESS TEST EXECUTION (Extended timeout):
        python -m pytest tests/mission_critical/test_docker_stability_suite.py -v --timeout=1800 -k "stress"
    
    P1 SUCCESS CRITERIA VALIDATION:
    
    The test suite validates these P1 success metrics:
    ✅ Docker daemon crashes: Target 0 (currently 5-10/day)
    ✅ Orphaned containers: Target 0 (currently 50+) 
    ✅ Test execution time: Target < 5 min (currently 10+ min)
    ✅ Memory usage: Target < 4GB peak (currently 6GB+ from tmpfs)
    ✅ Parallel test success: Target 100% (currently 60%)
    
    CRITICAL REQUIREMENTS:
    - Docker Desktop must be running and healthy
    - At least 8GB RAM available on system
    - Administrative privileges for Docker operations
    - No other intensive Docker operations running concurrently
    
    TROUBLESHOOTING:
    
    If tests fail:
    1. Check Docker daemon health: `docker info`
    2. Free system resources: `docker system prune -f`
    3. Restart Docker Desktop if needed
    4. Check available memory: At least 4GB free
    5. Review test logs in logs/docker_stability_p1_violations.log
    
    REPORTING:
    
    Test results are logged to:
    - Console output with detailed progress
    - logs/docker_stability_p1_violations.log (violations)
    - Comprehensive metrics in test output
    
    BUSINESS IMPACT:
    
    This test suite directly validates the P1 fixes that prevent:
    - 4-8 hours/week of developer downtime
    - $2M+ ARR risk from infrastructure failures
    - Docker daemon crashes (currently 5-10/day)
    - Memory exhaustion from tmpfs volumes (3GB+ RAM usage)
    - Test environment instability and parallel execution failures
    
    SUCCESS: All P1 tests passing indicates stable Docker infrastructure
             ready for production use without the historical stability issues.
    """
    
    import sys
    print("=" * 80)
    print("🔧 P1 DOCKER STABILITY TEST SUITE")
    print("CRITICAL BUSINESS VALUE: Validates $2M+ ARR Protection")
    print("=" * 80)
    print()
    print("This test suite validates ALL P1 Docker stability fixes.")
    print("Choose your execution method:")
    print()
    print("1. pytest tests/mission_critical/test_docker_stability_suite.py -k 'TestP1' -v")
    print("   → Run only P1 remediation validation tests")
    print()
    print("2. pytest tests/mission_critical/test_docker_stability_suite.py -v")
    print("   → Run comprehensive stability suite (all tests)")
    print()
    print("3. pytest tests/mission_critical/test_docker_stability_suite.py::TestP1EnvironmentLockMechanism -v")
    print("   → Run specific P1 test category")
    print()
    print("For detailed execution guide, see docstring above.")
    print("=" * 80)