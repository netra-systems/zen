"""
Tests for Dynamic Port Allocator

Comprehensive test suite for the dynamic port allocation system.
Tests port allocation, conflict detection, cleanup, and parallel test scenarios.
"""

import pytest
import asyncio
import socket
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import IsolatedEnvironment

from test_framework.dynamic_port_allocator import (
    DynamicPortAllocator,
    PortRange,
    PortAllocation,
    PortAllocationResult,
    ServicePortConfig,
    allocate_test_ports,
    release_test_ports
)


class TestDynamicPortAllocator:
    """Test suite for DynamicPortAllocator."""
    
    @pytest.fixture
    def allocator(self):
        """Create a test allocator instance."""
        return DynamicPortAllocator(
            port_range=PortRange.SHARED_TEST,
            test_id="test_123"
        )
    
    @pytest.fixture
    def cleanup_allocator(self, allocator):
        """Ensure cleanup after tests."""
        yield allocator
        # Clean up any allocated ports
        allocator.release_ports()
        # Clean up expired allocations
        allocator.cleanup_expired_allocations(max_age_hours=0)
    
    def test_port_allocation_success(self, cleanup_allocator):
        """Test successful port allocation for multiple services."""
        allocator = cleanup_allocator
        services = ["backend", "auth", "postgres", "redis"]
        
        result = allocator.allocate_ports(services)
        
        assert result.success is True
        assert len(result.ports) == len(services)
        assert all(service in result.ports for service in services)
        assert result.environment_id == allocator.environment_id
        assert result.error_message is None
        
        # Verify ports are in the correct range
        start_port, end_port = PortRange.SHARED_TEST.value
        for port in result.ports.values():
            assert start_port <= port <= end_port
    
    def test_port_availability_check(self, allocator):
        """Test OS-level port availability checking."""
        # Test with an available port
        available_port = self._find_free_port()
        assert allocator.is_port_available(available_port) is True
        
        # Test with an occupied port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", available_port))
            sock.listen(1)
            
            # Port should now be unavailable
            assert allocator.is_port_available(available_port) is False
    
    def test_port_reuse_for_same_environment(self, cleanup_allocator):
        """Test that the same environment reuses allocated ports."""
        allocator = cleanup_allocator
        services = ["backend", "auth"]
        
        # First allocation
        result1 = allocator.allocate_ports(services)
        ports1 = result1.ports.copy()
        
        # Second allocation for same environment
        result2 = allocator.allocate_ports(services)
        ports2 = result2.ports
        
        # Should reuse the same ports
        assert ports1 == ports2
        assert result2.success is True
    
    def test_port_conflict_detection(self):
        """Test detection of port conflicts between environments."""
        # Clean up any existing state first
        import shutil
        if DynamicPortAllocator.STATE_DIR.exists():
            shutil.rmtree(DynamicPortAllocator.STATE_DIR)
        
        # Create two allocators with different environment IDs
        allocator1 = DynamicPortAllocator(
            port_range=PortRange.SHARED_TEST,
            environment_id="env1"
        )
        allocator2 = DynamicPortAllocator(
            port_range=PortRange.SHARED_TEST,
            environment_id="env2"
        )
        
        try:
            services = ["backend", "auth"]
            
            # Allocate ports for first environment
            result1 = allocator1.allocate_ports(services)
            assert result1.success is True
            ports1 = result1.ports
            
            # Allocate ports for second environment
            result2 = allocator2.allocate_ports(services)
            assert result2.success is True
            ports2 = result2.ports
            
            # Ports should be different
            assert ports1 != ports2
            
            # No port should be shared between environments
            for service in services:
                assert ports1[service] != ports2[service]
        finally:
            # Cleanup
            allocator1.release_ports()
            allocator2.release_ports()
    
    def test_port_release(self, cleanup_allocator):
        """Test port release functionality."""
        allocator = cleanup_allocator
        services = ["backend", "auth", "postgres"]
        
        # Allocate ports
        result = allocator.allocate_ports(services)
        assert result.success is True
        allocated_ports = set(result.ports.values())
        
        # Release specific services
        allocator.release_ports(["backend", "auth"])
        
        # Check that released ports are available again
        remaining = allocator.get_all_ports()
        assert "postgres" in remaining
        assert "backend" not in remaining
        assert "auth" not in remaining
        
        # Release all remaining
        allocator.release_ports()
        assert len(allocator.get_all_ports()) == 0
    
    def test_expired_allocation_cleanup(self, cleanup_allocator):
        """Test cleanup of expired allocations."""
        allocator = cleanup_allocator
        services = ["backend", "auth"]
        
        # Allocate ports
        result = allocator.allocate_ports(services)
        assert result.success is True
        
        # Manually expire allocations by modifying allocated_at
        for key, allocation in allocator._allocations.items():
            allocation.allocated_at = datetime.now() - timedelta(hours=25)
        
        # Clean up expired allocations
        cleaned = allocator.cleanup_expired_allocations(max_age_hours=24)
        assert cleaned == len(services)
        assert len(allocator.get_all_ports()) == 0
    
    def test_allocation_locking(self, cleanup_allocator):
        """Test allocation locking to prevent cleanup."""
        allocator = cleanup_allocator
        services = ["backend"]
        
        # Allocate and lock
        result = allocator.allocate_ports(services)
        assert result.success is True
        assert allocator.lock_allocation("backend") is True
        
        # Expire the allocation
        for allocation in allocator._allocations.values():
            allocation.allocated_at = datetime.now() - timedelta(hours=25)
        
        # Cleanup should not remove locked allocation
        cleaned = allocator.cleanup_expired_allocations(max_age_hours=24)
        assert cleaned == 0
        assert "backend" in allocator.get_all_ports()
        
        # Unlock and cleanup
        assert allocator.unlock_allocation("backend") is True
        cleaned = allocator.cleanup_expired_allocations(max_age_hours=24)
        assert cleaned == 1
    
    def test_port_range_allocation(self):
        """Test allocation in different port ranges."""
        ranges_to_test = [
            (PortRange.DEVELOPMENT, 8000, 8999),
            (PortRange.SHARED_TEST, 30000, 30999),
            (PortRange.DEDICATED_TEST, 31000, 39999),
            (PortRange.CI_CD, 40000, 49999),
        ]
        
        for port_range, expected_start, expected_end in ranges_to_test:
            allocator = DynamicPortAllocator(port_range=port_range)
            try:
                result = allocator.allocate_ports(["backend"])
                if result.success:
                    port = result.ports["backend"]
                    assert expected_start <= port <= expected_end, \
                        f"Port {port} not in range {expected_start}-{expected_end} for {port_range.name}"
            finally:
                allocator.release_ports()
    
    def test_parallel_allocation_safety(self):
        """Test thread-safe parallel port allocation."""
        results = []
        errors = []
        
        def allocate_ports(env_id: str):
            try:
                allocator = DynamicPortAllocator(
                    port_range=PortRange.SHARED_TEST,
                    environment_id=env_id
                )
                result = allocator.allocate_ports(["backend", "auth"])
                results.append((env_id, result))
            except Exception as e:
                errors.append((env_id, e))
        
        # Create multiple threads for parallel allocation
        threads = []
        for i in range(5):
            thread = threading.Thread(target=allocate_ports, args=(f"env_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors during parallel allocation: {errors}"
        assert len(results) == 5
        
        # Verify all allocations succeeded and ports are unique
        all_ports = set()
        for env_id, result in results:
            assert result.success is True
            for port in result.ports.values():
                assert port not in all_ports, f"Port {port} allocated multiple times"
                all_ports.add(port)
        
        # Cleanup
        for env_id, _ in results:
            allocator = DynamicPortAllocator(environment_id=env_id)
            allocator.release_ports()
    
    def test_allocation_statistics(self, cleanup_allocator):
        """Test allocation statistics tracking."""
        allocator = cleanup_allocator
        
        # Allocate ports
        services = ["backend", "auth", "postgres"]
        result = allocator.allocate_ports(services)
        assert result.success is True
        
        # Get statistics
        stats = allocator.get_allocation_stats()
        
        assert stats["total_allocations"] == len(services)
        assert allocator.environment_id in stats["environments"]
        assert len(stats["environments"][allocator.environment_id]["services"]) == len(services)
        assert len(stats["environments"][allocator.environment_id]["ports"]) == len(services)
        
        # Check port range usage
        assert "SHARED_TEST" in stats["port_ranges"]
        range_stats = stats["port_ranges"]["SHARED_TEST"]
        assert range_stats["used"] == len(services)
        assert range_stats["total"] == 1000  # 30000-30999
        assert 0 < range_stats["percentage"] < 1  # Should be a small percentage
        
        # Check service counts
        for service in services:
            assert service in stats["services"]
            assert stats["services"][service] == 1
    
    def test_service_port_config(self, cleanup_allocator):
        """Test service-specific port configuration."""
        allocator = cleanup_allocator
        
        # Test that services get appropriate offsets
        services = ["backend", "auth", "frontend", "postgres", "redis"]
        result = allocator.allocate_ports(services)
        assert result.success is True
        
        # Verify relative positioning makes sense
        # Frontend should be in a different range than backend/auth
        backend_port = result.ports["backend"]
        frontend_port = result.ports["frontend"]
        postgres_port = result.ports["postgres"]
        
        # These should have reasonable offsets based on config
        assert abs(frontend_port - backend_port) >= 100  # Different ranges
        assert abs(postgres_port - backend_port) >= 100  # Different ranges
    
    def test_convenience_functions(self):
        """Test convenience functions for allocation and release."""
        test_id = "conv_test_123"
        services = ["backend", "auth"]
        
        # Test allocate_test_ports
        result = allocate_test_ports(services, test_id=test_id)
        assert result.success is True
        assert len(result.ports) == len(services)
        env_id = result.environment_id
        
        # Test release_test_ports
        release_test_ports(env_id, services)
        
        # Verify ports were released
        allocator = DynamicPortAllocator(environment_id=env_id)
        assert len(allocator.get_all_ports()) == 0
    
    def test_state_persistence(self, tmp_path):
        """Test that allocation state is persisted and loaded correctly."""
        # Override state directory for testing
        test_state_dir = tmp_path / "port_state"
        test_state_dir.mkdir()
        
        with patch.object(DynamicPortAllocator, 'STATE_DIR', test_state_dir):
            with patch.object(DynamicPortAllocator, 'STATE_FILE', test_state_dir / "test_allocations.json"):
                # Create allocator and allocate ports
                allocator1 = DynamicPortAllocator(
                    port_range=PortRange.SHARED_TEST,
                    environment_id="persist_test"
                )
                services = ["backend", "auth"]
                result = allocator1.allocate_ports(services)
                assert result.success is True
                original_ports = result.ports.copy()
                
                # Create new allocator with same environment ID
                allocator2 = DynamicPortAllocator(
                    port_range=PortRange.SHARED_TEST,
                    environment_id="persist_test"
                )
                
                # Should load existing allocations
                loaded_ports = allocator2.get_all_ports()
                assert loaded_ports == original_ports
                
                # Cleanup
                allocator2.release_ports()
    
    def test_process_id_tracking(self, cleanup_allocator):
        """Test that allocations track process IDs correctly."""
        allocator = cleanup_allocator
        services = ["backend"]
        
        result = allocator.allocate_ports(services)
        assert result.success is True
        
        # Check that process ID is tracked
        for allocation in allocator._allocations.values():
            assert allocation.process_id == allocator.process_id
    
    def test_error_handling(self, cleanup_allocator):
        """Test error handling in various scenarios."""
        allocator = cleanup_allocator
        
        # Test with invalid service (should still work with defaults)
        result = allocator.allocate_ports(["unknown_service"])
        assert result.success is True  # Should allocate with default config
        
        # Test with empty service list
        result = allocator.allocate_ports([])
        assert result.success is True
        assert len(result.ports) == 0
    
    def _find_free_port(self) -> int:
        """Helper to find a free port for testing."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]


class TestIntegrationWithDocker:
    """Integration tests with Docker components."""
    
    @pytest.mark.integration
    def test_docker_manager_integration(self):
        """Test integration with UnifiedDockerManager."""
        from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
        
        manager = UnifiedDockerManager(
            environment_type=EnvironmentType.DEDICATED,
            test_id="integration_test"
        )
        
        # Should have initialized port allocator
        assert hasattr(manager, 'port_allocator')
        assert manager.port_allocator is not None
        
        # Test environment acquisition
        env_name, ports = manager.acquire_environment()
        assert env_name is not None
        assert isinstance(ports, dict)
        
        # Cleanup
        manager.release_environment(env_name)
    
    @pytest.mark.integration
    def test_port_discovery_integration(self):
        """Test integration with DockerPortDiscovery."""
        from test_framework.docker_port_discovery import DockerPortDiscovery
        
        discovery = DockerPortDiscovery(
            use_test_services=True,
            use_dynamic_allocation=True
        )
        
        # Should support dynamic allocation
        assert hasattr(discovery, 'use_dynamic_allocation')
        assert hasattr(discovery, 'allocated_ports')
        
        # Test port discovery with dynamic allocation
        port_mappings = discovery.discover_all_ports()
        assert isinstance(port_mappings, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])