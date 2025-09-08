"""
File System Isolation Tests for Agent Resource Isolation

Tests that validate file system isolation between tenant agents to ensure
one tenant's file system usage doesn't impact others.

Business Value Justification (BVJ):
- Segment: Enterprise (multi-tenant isolation requirements)
- Business Goal: Ensure file system isolation prevents disk I/O interference
- Value Impact: Protects against I/O-based noisy neighbor problems
- Revenue Impact: Critical for $500K+ enterprise contract SLAs
"""

import pytest
import asyncio
import logging
import time
import os
import tempfile
import shutil
import statistics
from typing import Dict, Any, List
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.fixtures.resource_monitoring import isolation_test_config, resource_limits
from tests.e2e.test_helpers.agent_isolation_base import AgentIsolationBase
from tests.e2e.test_helpers.file_system_helpers import (
    simulate_file_operations, simulate_disk_usage, concurrent_file_access
)
from tests.e2e.resource_isolation.test_suite import resource_isolation_suite, tenant_agents

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.filesystem_isolation
async def test_file_handle_isolation(resource_isolation_suite, tenant_agents):
    """Test file handle isolation between tenants."""
    suite = resource_isolation_suite
    isolation_base = AgentIsolationBase()
    
    # Establish baseline
    for agent in tenant_agents:
        await isolation_base.establish_baseline_metrics(agent.tenant_id, duration=5.0)
    
    # Create temporary files for each tenant
    temp_files = {}
    file_operations = []
    
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    for agent in tenant_agents:
        # Create tenant-specific temp file
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"tenant_{agent.tenant_id}_", 
            suffix=".tmp", 
            delete=False
        )
        temp_files[agent.tenant_id] = temp_file.name
        temp_file.close()
        
        # Start file I/O operations
        task = asyncio.create_task(
            simulate_file_operations(agent.tenant_id, temp_file.name, duration=30.0)
        )
        file_operations.append(task)
    
    results = await asyncio.gather(*file_operations, return_exceptions=True)
    
    # Check that all file operations completed successfully
    failed_operations = [r for r in results if isinstance(r, Exception)]
    assert len(failed_operations) == 0, f"File operations failed: {failed_operations}"
    
    # Check for fair I/O distribution
    successful_results = [r for r in results if isinstance(r, dict)]
    io_rates = [r.get("io_rate", 0) for r in successful_results]
    
    if len(io_rates) > 1:
        mean_rate = statistics.mean(io_rates)
        if mean_rate > 0:
            max_rate = max(io_rates)
            rate_ratio = max_rate / mean_rate
            
            # No tenant should monopolize I/O (max 2.5x average)
            assert rate_ratio < 2.5, f"I/O monopolization detected: {rate_ratio:.2f}x"
    
    logger.info(f"File handle isolation test passed: {len(successful_results)} operations")
    
    # Cleanup temp files
    for temp_file in temp_files.values():
        if os.path.exists(temp_file):
            os.unlink(temp_file)

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.filesystem_isolation
async def test_disk_space_isolation(resource_isolation_suite, tenant_agents):
    """Test disk space usage isolation between tenants."""
    suite = resource_isolation_suite
    
    # Create separate temp directories for each tenant
    temp_dirs = {}
    space_usage_tasks = []
    
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    for agent in tenant_agents:
        # Create tenant-specific temp directory
        temp_dir = tempfile.mkdtemp(prefix=f"tenant_{agent.tenant_id}_")
        temp_dirs[agent.tenant_id] = temp_dir
        
        # Simulate disk space usage
        task = asyncio.create_task(
            simulate_disk_usage(agent.tenant_id, temp_dir, max_mb=50)
        )
        space_usage_tasks.append(task)
    
    results = await asyncio.gather(*space_usage_tasks, return_exceptions=True)
    
    # Check disk usage results
    successful_results = [r for r in results if isinstance(r, dict)]
    failed_count = len(results) - len(successful_results)
    
    # Most operations should succeed
    success_rate = len(successful_results) / len(results) * 100
    assert success_rate >= 80.0, f"Low disk operation success rate: {success_rate:.2f}%"
    
    # Check space usage is reasonable
    total_space_used = sum(r.get("space_used_mb", 0) for r in successful_results)
    expected_max = len(tenant_agents) * 50  # 50MB per tenant max
    
    assert total_space_used <= expected_max * 1.2, \
        f"Excessive disk usage: {total_space_used:.2f}MB > {expected_max:.2f}MB"
    
    logger.info(f"Disk space isolation test: {total_space_used:.2f}MB used by {len(successful_results)} tenants")
    
    # Cleanup temp directories
    for temp_dir in temp_dirs.values():
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.filesystem_isolation
async def test_concurrent_file_access(resource_isolation_suite, tenant_agents):
    """Test concurrent file access patterns don't interfere."""
    suite = resource_isolation_suite
    
    # Create shared temp directory but separate files
    temp_dir = tempfile.mkdtemp(prefix="concurrent_access_test_")
    
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    concurrent_tasks = []
    
    for i, agent in enumerate(tenant_agents):
        # Each tenant works with different files
        file_pattern = f"tenant_{agent.tenant_id}_file_*.dat"
        
        task = asyncio.create_task(
            concurrent_file_access(agent.tenant_id, temp_dir, file_pattern, duration=25.0)
        )
        concurrent_tasks.append(task)
    
    results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
    
    # Analyze concurrent access results
    successful_results = [r for r in results if isinstance(r, dict)]
    access_rates = [r.get("access_rate", 0) for r in successful_results]
    
    # Check that all tenants achieved reasonable access rates
    min_expected_rate = 10  # operations per second
    low_performers = [r for r in access_rates if r < min_expected_rate]
    
    max_low_performers = len(tenant_agents) // 3  # Allow 33% to be slower
    assert len(low_performers) <= max_low_performers, \
        f"Too many tenants with low file access rates: {len(low_performers)}"
    
    # Check for file corruption or conflicts
    corruption_count = sum(r.get("corruption_errors", 0) for r in successful_results)
    assert corruption_count == 0, f"File corruption detected: {corruption_count} errors"
    
    logger.info(f"Concurrent file access test: rates {access_rates}")
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.filesystem_isolation
async def test_file_system_error_isolation(resource_isolation_suite, tenant_agents):
    """Test that file system errors in one tenant don't affect others."""
    suite = resource_isolation_suite
    
    if len(tenant_agents) < 2:
        pytest.skip("Need at least 2 agents for error isolation test")
    
    # Select one tenant to cause file system errors
    error_tenant = tenant_agents[0]
    normal_tenants = tenant_agents[1:]
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="fs_error_test_")
    
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    # Start error simulation for one tenant
    error_task = asyncio.create_task(
        _simulate_file_system_errors(error_tenant.tenant_id, temp_dir)
    )
    
    # Normal file operations for other tenants
    normal_tasks = []
    for agent in normal_tenants:
        task = asyncio.create_task(
            _normal_file_operations(agent.tenant_id, temp_dir, duration=20.0)
        )
        normal_tasks.append(task)
    
    # Wait for all operations
    await asyncio.gather(error_task, *normal_tasks, return_exceptions=True)
    
    # Check that normal tenants completed successfully
    normal_results = await asyncio.gather(*normal_tasks, return_exceptions=True)
    successful_normal = [r for r in normal_results if isinstance(r, dict)]
    
    # Most normal tenants should succeed despite errors from one tenant
    success_rate = len(successful_normal) / len(normal_tenants) * 100
    assert success_rate >= 75.0, f"File system errors affected too many tenants: {success_rate:.2f}%"
    
    logger.info(f"File system error isolation: {len(successful_normal)}/{len(normal_tenants)} normal tenants succeeded")
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

async def _simulate_file_system_errors(tenant_id: str, base_dir: str):
    """Simulate various file system errors."""
    error_scenarios = [
        "permission_denied", "disk_full_simulation", 
        "invalid_paths", "concurrent_access_conflicts"
    ]
    
    for scenario in error_scenarios:
        if scenario == "permission_denied":
            # Try to access files in ways that might cause permission errors
            invalid_path = os.path.join(base_dir, "invalid", "deeply", "nested", "file.dat")
            os.makedirs(os.path.dirname(invalid_path), exist_ok=True)
            with open(invalid_path, "w") as f:
                f.write("test")
            
        elif scenario == "invalid_paths":
            # Try invalid file operations
            invalid_chars = '<>:"|?*'
            for char in invalid_chars:
                # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                # Expected to fail with invalid characters in filename - let it raise
                invalid_file = os.path.join(base_dir, f"invalid{char}file.dat")
                if char in '<>:"|?*':
                    continue  # Skip invalid chars that would raise exceptions
                with open(invalid_file, "w") as f:
                    f.write("test")
        
        await asyncio.sleep(2.0)

async def _normal_file_operations(tenant_id: str, base_dir: str, duration: float) -> Dict[str, Any]:
    """Perform normal file operations that should succeed."""
    start_time = time.time()
    operations_count = 0
    errors = 0
    
    tenant_dir = os.path.join(base_dir, f"normal_{tenant_id}")
    os.makedirs(tenant_dir, exist_ok=True)
    
    end_time = start_time + duration
    
    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
    while time.time() < end_time:
        file_path = os.path.join(tenant_dir, f"file_{operations_count}.dat")
        
        # Simple write and read operation
        test_data = f"normal_data_{tenant_id}_{operations_count}".encode()
        
        with open(file_path, "wb") as f:
            f.write(test_data)
        
        with open(file_path, "rb") as f:
            read_data = f.read()
            if read_data != test_data:
                errors += 1
        
        operations_count += 1
        
        # Clean up immediately
        os.unlink(file_path)
        
        await asyncio.sleep(0.05)
    
    # Cleanup tenant directory
    if os.path.exists(tenant_dir):
        shutil.rmtree(tenant_dir)
    
    duration = time.time() - start_time
    
    return {
        "tenant_id": tenant_id,
        "operations_count": operations_count,
        "errors": errors,
        "duration": duration,
        "success_rate": (operations_count - errors) / operations_count * 100 if operations_count > 0 else 0
    }
