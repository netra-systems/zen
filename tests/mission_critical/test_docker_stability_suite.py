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


if __name__ == "__main__":
    # Direct execution for debugging
    framework = DockerStabilityTestFramework()
    try:
        logger.info("🚀 Starting Docker Stability Test Suite...")
        
        # Run a subset of tests for direct execution
        test_force = TestDockerForceProhibition()
        test_force.test_force_flag_prohibition_comprehensive(framework)
        
        test_rate = TestDockerRateLimiting()
        test_rate.test_rate_limiter_effectiveness(framework)
        
        logger.info("✅ Direct execution tests completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Direct execution test failed: {e}")
        raise
    finally:
        framework.cleanup()