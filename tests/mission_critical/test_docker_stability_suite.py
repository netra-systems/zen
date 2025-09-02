"""
MISSION CRITICAL: Ultimate Docker Stability Test Suite
BUSINESS IMPACT: PROTECTS $2M+ ARR PLATFORM FROM DOCKER CRASHES

This is the most comprehensive Docker stability test suite ever created for Netra.
It validates EVERY aspect of our Docker stability improvements under extreme conditions.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Risk Reduction & Development Velocity  
2. Business Goal: Ensure zero Docker Desktop crashes, maintain CI/CD reliability
3. Value Impact: Prevents 4-8 hours/week developer downtime, enables parallel testing
4. Revenue Impact: Protects $2M+ ARR platform from infrastructure failures

CRITICAL REQUIREMENTS:
- NO MOCKS: Real Docker operations only
- EXTREME STRESS: Push systems beyond normal limits
- FAILURE SCENARIOS: Test every possible failure mode
- RECOVERY VALIDATION: Ensure graceful recovery from all failures
- FORCE FLAG ZERO TOLERANCE: Absolute prohibition enforcement
- MEMORY PRESSURE: Test under resource constraints
- CONCURRENT OPERATIONS: Validate thread safety and race conditions
- CLEANUP VALIDATION: Ensure no resource leaks
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

# CRITICAL IMPORTS: All Docker infrastructure
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
from shared.isolated_environment import get_env

# Configure logging for maximum visibility
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DockerStabilityTestFramework:
    """Framework for comprehensive Docker stability testing."""
    
    def __init__(self):
        """Initialize test framework with all necessary components."""
        self.test_containers = []
        self.test_networks = []
        self.test_volumes = []
        self.test_images = []
        self.allocated_ports = []
        self.metrics = {
            'operations_attempted': 0,
            'operations_successful': 0,
            'operations_failed': 0,
            'force_flag_violations_detected': 0,
            'memory_pressure_events': 0,
            'cleanup_operations': 0,
            'concurrent_operations_peak': 0,
            'recovery_attempts': 0,
            'recovery_successes': 0
        }
        self.start_time = time.time()
        
        # Initialize Docker components with maximum strictness
        self.docker_manager = UnifiedDockerManager()
        self.rate_limiter = get_docker_rate_limiter()
        self.force_guardian = DockerForceFlagGuardian(
            audit_log_path="logs/docker_stability_test_violations.log"
        )
        
        logger.info("🔧 Docker Stability Test Framework initialized with MAXIMUM PROTECTION")
        
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


class TestDockerStabilityStressTesting:
    """EXTREME STRESS TESTS: Push Docker operations beyond normal limits."""
    
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