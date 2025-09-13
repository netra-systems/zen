"""

Platform-Specific Port Allocation Tests

Business Value: Ensures cross-platform compatibility for port management

"""



import asyncio

import platform

import pytest

import socket

import sys

from typing import List, Set

from shared.isolated_environment import IsolatedEnvironment



from dev_launcher.service_coordination import (

    PlatformAwarePortAllocator,

    PortAllocationStrategy

)





@pytest.mark.e2e

class TestWindowsPlatformPortAllocation:

    """Test Windows-specific port allocation behavior."""

    

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_windows_dynamic_port_range(self):

        """Test Windows uses correct dynamic port range."""

        allocator = PlatformAwarePortAllocator()

        assert allocator.platform_name == "Windows"

        assert allocator.PLATFORM_PORT_RANGES["Windows"] == (49152, 65535)

        

        # Allocate a dynamic port

        port = await allocator.allocate_port(

            "windows_service",

            strategy=PortAllocationStrategy.DYNAMIC

        )

        

        # Should be in Windows dynamic range

        assert 49152 <= port <= 65535

    

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")

    @pytest.mark.e2e

    def test_windows_socket_options(self):

        """Test Windows-specific socket options."""

        allocator = PlatformAwarePortAllocator()

        

        # Test that SO_EXCLUSIVEADDRUSE is used on Windows

        # Mock: Component isolation for testing without external dependencies

        with patch('socket.socket') as mock_socket:

            # Mock: Generic component isolation for controlled unit testing

            mock_sock = MagicNone  # TODO: Use real service instead of Mock

            mock_socket.return_value = mock_sock

            mock_sock.bind.return_value = None

            

            allocator._is_port_available(12345)

            

            # Check Windows-specific socket option was set

            mock_sock.setsockopt.assert_called_with(

                socket.SOL_SOCKET,

                socket.SO_EXCLUSIVEADDRUSE,

                1

            )





@pytest.mark.e2e

class TestLinuxPlatformPortAllocation:

    """Test Linux-specific port allocation behavior."""

    

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux-specific test")

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_linux_ephemeral_port_range(self):

        """Test Linux uses correct ephemeral port range."""

        allocator = PlatformAwarePortAllocator()

        assert allocator.platform_name == "Linux"

        assert allocator.PLATFORM_PORT_RANGES["Linux"] == (32768, 60999)

        

        # Allocate a dynamic port

        port = await allocator.allocate_port(

            "linux_service",

            strategy=PortAllocationStrategy.DYNAMIC

        )

        

        # Should be in Linux ephemeral range or fallback

        assert port > 1024  # At minimum, above privileged ports

    

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux-specific test")

    @pytest.mark.e2e

    def test_linux_socket_options(self):

        """Test Linux-specific socket options."""

        allocator = PlatformAwarePortAllocator()

        

        # Test that SO_REUSEADDR is used on Linux

        # Mock: Component isolation for testing without external dependencies

        with patch('socket.socket') as mock_socket:

            # Mock: Generic component isolation for controlled unit testing

            mock_sock = MagicNone  # TODO: Use real service instead of Mock

            mock_socket.return_value = mock_sock

            mock_sock.bind.return_value = None

            

            allocator._is_port_available(12345)

            

            # Check Linux-specific socket option was set

            mock_sock.setsockopt.assert_called_with(

                socket.SOL_SOCKET,

                socket.SO_REUSEADDR,

                1

            )





@pytest.mark.e2e

class TestMacOSPlatformPortAllocation:

    """Test macOS-specific port allocation behavior."""

    

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS-specific test")

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_macos_dynamic_port_range(self):

        """Test macOS uses correct dynamic port range."""

        allocator = PlatformAwarePortAllocator()

        assert allocator.platform_name == "Darwin"

        assert allocator.PLATFORM_PORT_RANGES["Darwin"] == (49152, 65535)

        

        # Allocate a dynamic port

        port = await allocator.allocate_port(

            "macos_service",

            strategy=PortAllocationStrategy.DYNAMIC

        )

        

        # Should be in macOS dynamic range

        assert 49152 <= port <= 65535

    

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS-specific test")

    @pytest.mark.e2e

    def test_macos_socket_options(self):

        """Test macOS-specific socket options."""

        allocator = PlatformAwarePortAllocator()

        

        # Test that SO_REUSEADDR is used on macOS (Unix-like)

        # Mock: Component isolation for testing without external dependencies

        with patch('socket.socket') as mock_socket:

            # Mock: Generic component isolation for controlled unit testing

            mock_sock = MagicNone  # TODO: Use real service instead of Mock

            mock_socket.return_value = mock_sock

            mock_sock.bind.return_value = None

            

            allocator._is_port_available(12345)

            

            # Check Unix-like socket option was set

            mock_sock.setsockopt.assert_called_with(

                socket.SOL_SOCKET,

                socket.SO_REUSEADDR,

                1

            )





@pytest.mark.e2e

class TestCrossPlatformPortAllocation:

    """Test cross-platform port allocation compatibility."""

    

    @pytest.fixture

    def allocator(self):

        """Create a port allocator instance."""

        return PlatformAwarePortAllocator()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_service_specific_ports_cross_platform(self, allocator):

        """Test service-specific ports work across platforms."""

        # These should work on any platform

        services_to_test = ["backend", "auth", "frontend", "redis", "postgres"]

        

        allocated_ports: Set[int] = set()

        for service in services_to_test:

            port = await allocator.allocate_port(service)

            assert port > 1024  # Above privileged range

            assert port not in allocated_ports  # Unique port

            allocated_ports.add(port)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_fallback_to_ephemeral(self, allocator):

        """Test fallback to ephemeral ports when dynamic allocation fails."""

        # Mock to always fail dynamic allocation

        async def mock_find_dynamic_port():

            # Simulate failure by returning ephemeral

            return allocator._get_ephemeral_port()

        

        allocator._find_dynamic_port = mock_find_dynamic_port

        

        port = await allocator.allocate_port(

            "fallback_service",

            strategy=PortAllocationStrategy.DYNAMIC

        )

        

        assert port > 1024

        assert "fallback_service" in allocator.service_port_map

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_concurrent_allocation_cross_platform(self, allocator):

        """Test concurrent allocation works on all platforms."""

        num_services = 20

        tasks = []

        

        for i in range(num_services):

            tasks.append(

                allocator.allocate_port(

                    f"concurrent_{i}",

                    strategy=PortAllocationStrategy.DYNAMIC

                )

            )

        

        ports = await asyncio.gather(*tasks)

        

        # All ports should be unique

        assert len(set(ports)) == num_services

        

        # All should be valid ports

        for port in ports:

            assert 1024 < port <= 65535

    

    @pytest.mark.e2e

    def test_platform_detection(self, allocator):

        """Test correct platform detection."""

        current_platform = platform.system()

        assert allocator.platform_name == current_platform

        assert current_platform in ["Windows", "Darwin", "Linux"] or \

               allocator.platform_name is not None

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_port_exhaustion_handling(self, allocator):

        """Test handling when no ports are available."""

        # Mock to simulate all ports being unavailable

        original_is_available = allocator._is_port_available

        attempt_count = 0

        

        def mock_is_available(port):

            nonlocal attempt_count

            attempt_count += 1

            # Always return False to simulate exhaustion

            if attempt_count > 200:  # Prevent infinite loop

                return original_is_available(port)

            return False

        

        allocator._is_port_available = mock_is_available

        

        # Should eventually fall back to ephemeral

        port = await allocator.allocate_port(

            "exhausted_service",

            strategy=PortAllocationStrategy.DYNAMIC

        )

        

        assert port > 1024  # Should still get a valid port

    

    @pytest.mark.asyncio 

    @pytest.mark.e2e

    async def test_static_strategy_failure(self, allocator):

        """Test static strategy fails when port unavailable."""

        # Allocate a port

        port1 = await allocator.allocate_port("service1", preferred_port=9876)

        assert port1 == 9876

        

        # Try static allocation of same port - should fail

        with pytest.raises(ValueError, match="No available port"):

            await allocator.allocate_port(

                "service2",

                preferred_port=9876,

                strategy=PortAllocationStrategy.STATIC

            )





@pytest.mark.e2e

class TestPortAllocationEdgeCases:

    """Test edge cases in port allocation."""

    

    @pytest.fixture

    def allocator(self):

        """Create a port allocator instance."""

        return PlatformAwarePortAllocator()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_allocate_same_service_twice(self, allocator):

        """Test allocating port for same service returns same port."""

        port1 = await allocator.allocate_port("duplicate_service", preferred_port=7654)

        port2 = await allocator.allocate_port("duplicate_service", preferred_port=8765)

        

        assert port1 == port2  # Should return already allocated port

        assert port1 == 7654  # Should be the first allocated port

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_release_nonexistent_service(self, allocator):

        """Test releasing port for non-existent service."""

        # Should not raise error

        await allocator.release_port("nonexistent_service")

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_allocate_privileged_port(self, allocator):

        """Test allocation of privileged ports (< 1024)."""

        # Should not be able to bind to privileged ports without root

        # But allocation should still track it

        port = await allocator.allocate_port("privileged_service", preferred_port=80)

        

        # Port may or may not be 80 depending on permissions

        # But service should be in map

        assert "privileged_service" in allocator.service_port_map

    

    @pytest.mark.e2e

    def test_allocation_summary_empty(self, allocator):

        """Test allocation summary when no ports allocated."""

        summary = allocator.get_allocation_summary()

        

        assert summary["allocated_ports"] == 0

        assert summary["service_ports"] == {}

        assert summary["platform"] == platform.system()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_allocation_summary_with_ports(self, allocator):

        """Test allocation summary with allocated ports."""

        await allocator.allocate_port("service1", preferred_port=5000)

        await allocator.allocate_port("service2", preferred_port=5001)

        await allocator.allocate_port("service3")

        

        summary = allocator.get_allocation_summary()

        

        assert summary["allocated_ports"] == 3

        assert len(summary["service_ports"]) == 3

        assert summary["service_ports"]["service1"] == 5000

        assert summary["service_ports"]["service2"] == 5001

        assert "service3" in summary["service_ports"]





@pytest.mark.e2e

class TestPortAllocationIntegration:

    """Integration tests for port allocation with real sockets."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_real_port_binding(self):

        """Test actual port binding and release."""

        allocator = PlatformAwarePortAllocator()

        

        # Allocate a port

        port = await allocator.allocate_port("real_service")

        

        # Try to bind to the allocated port - should work

        try:

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if platform.system() == "Windows":

                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)

            else:

                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            

            sock.bind(('127.0.0.1', port))

            sock.listen(1)

            

            # Port is bound, now release it in allocator

            await allocator.release_port("real_service")

            

            # Close socket

            sock.close()

            

        except OSError as e:

            pytest.fail(f"Could not bind to allocated port {port}: {e}")

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_detect_occupied_port(self):

        """Test detection of occupied ports."""

        allocator = PlatformAwarePortAllocator()

        

        # Bind to a specific port

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.bind(('127.0.0.1', 0))  # Get any available port

        occupied_port = sock.getsockname()[1]

        sock.listen(1)

        

        try:

            # Try to allocate the occupied port

            port = await allocator.allocate_port(

                "blocked_service",

                preferred_port=occupied_port

            )

            

            # Should get a different port

            assert port != occupied_port

            assert port > 1024

            

        finally:

            sock.close()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_rapid_allocation_deallocation(self):

        """Test rapid allocation and deallocation cycles."""

        allocator = PlatformAwarePortAllocator()

        

        for i in range(10):

            # Allocate

            port = await allocator.allocate_port(f"cycle_service_{i}")

            assert port > 1024

            

            # Immediately deallocate

            await allocator.release_port(f"cycle_service_{i}")

            

            # Should be able to reallocate same port

            port2 = await allocator.allocate_port(

                f"cycle_service_{i}_new",

                preferred_port=port

            )

            assert port2 == port

            

            # Clean up

            await allocator.release_port(f"cycle_service_{i}_new")

