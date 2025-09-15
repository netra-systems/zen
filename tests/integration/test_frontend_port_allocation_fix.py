"""
Integration test for frontend port allocation fix.

Validates that the enhanced port allocation system properly handles
the common case where port 3000 is already occupied.

Business Value: Platform/Internal - Development Velocity - Ensures reliable
frontend startup when default port is occupied.
"""
import pytest
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Optional
from shared.isolated_environment import IsolatedEnvironment
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from dev_launcher.utils import find_available_port, is_port_available
from dev_launcher.port_manager import PortManager

class PortServer:
    """Simple test server that occupies a port for testing."""

    def __init__(self, port: int):
        self.port = port
        self.socket = None
        self.running = False
        self.thread = None

    def start(self) -> bool:
        """Start the test server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.listen(1)
            self.running = True
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()
            time.sleep(0.1)
            return True
        except OSError as e:
            print(f'Failed to start test server on port {self.port}: {e}')
            return False

    def _run_server(self):
        """Run the server loop."""
        while self.running:
            try:
                self.socket.settimeout(0.5)
                conn, addr = self.socket.accept()
                conn.close()
            except socket.timeout:
                continue
            except OSError:
                break

    def stop(self):
        """Stop the test server."""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join(timeout=1)

@pytest.mark.integration
class TestFrontendPortAllocationFix:
    """Test the enhanced frontend port allocation system."""

    def test_basic_port_conflict_detection(self):
        """Test that port conflicts are properly detected."""
        test_port = 3005
        assert is_port_available(test_port, '0.0.0.0'), f'Port {test_port} should be available initially'
        server = TestPortServer(test_port)
        assert server.start(), f'Should be able to start server on port {test_port}'
        try:
            assert not is_port_available(test_port, '0.0.0.0'), f'Port {test_port} should be occupied by test server'
        finally:
            server.stop()
        print(f'SUCCESS: Port conflict detection working for port {test_port}')

    def test_find_available_port_fallback(self):
        """Test that find_available_port properly falls back when preferred port is occupied."""
        preferred_port = 3006
        test_range = (3006, 3010)
        server = TestPortServer(preferred_port)
        assert server.start(), f'Should be able to start server on preferred port {preferred_port}'
        try:
            available_port = find_available_port(preferred_port=preferred_port, port_range=test_range, host='0.0.0.0')
            assert available_port != preferred_port, f'Should get different port than occupied {preferred_port}'
            assert test_range[0] <= available_port <= test_range[1], f'Port {available_port} should be in range {test_range}'
            assert is_port_available(available_port, '0.0.0.0'), f'Allocated port {available_port} should be available'
            print(f'SUCCESS: find_available_port fallback working - {preferred_port} -> {available_port}')
        finally:
            server.stop()

    def test_port_manager_allocation_with_conflict(self):
        """Test PortManager handles conflicts and provides detailed information."""
        port_manager = PortManager()
        test_port = 3011
        server = TestPortServer(test_port)
        assert server.start(), f'Should be able to start server on port {test_port}'
        try:
            allocated_port = port_manager.allocate_port(service_name='test_frontend', preferred_port=test_port, port_range=(3011, 3015), max_retries=2)
            assert allocated_port is not None, 'Should successfully allocate alternative port'
            assert allocated_port != test_port, f'Should allocate different port than occupied {test_port}'
            process_info = port_manager.find_process_using_port(test_port)
            print(f'Process using port {test_port}: {process_info}')
            tracked_port = port_manager.get_allocated_port('test_frontend')
            assert tracked_port == allocated_port, f'Manager should track allocated port {allocated_port}'
            print(f'SUCCESS: PortManager allocation with conflict - {test_port} -> {allocated_port}')
        finally:
            port_manager.release_port('test_frontend')
            server.stop()

    def test_multiple_port_conflicts(self):
        """Test handling multiple occupied ports in sequence."""
        occupied_ports = [3021, 3022, 3023]
        servers = []
        for port in occupied_ports:
            server = TestPortServer(port)
            if server.start():
                servers.append(server)
        try:
            available_port = find_available_port(preferred_port=3021, port_range=(3021, 3025), host='0.0.0.0')
            assert available_port not in occupied_ports, f'Should avoid occupied ports {occupied_ports}'
            assert available_port >= 3024, f'Should get port 3024 or higher, got {available_port}'
            print(f'SUCCESS: Multiple port conflicts handled - found port {available_port}')
        finally:
            for server in servers:
                server.stop()

    def test_extended_range_fallback(self):
        """Test extended range fallback for frontend ports."""
        preferred_port = 3030
        original_range = (3030, 3032)
        servers = []
        for port in range(3030, 3033):
            server = TestPortServer(port)
            if server.start():
                servers.append(server)
        try:
            available_port = find_available_port(preferred_port=preferred_port, port_range=original_range, host='0.0.0.0')
            assert available_port not in range(3030, 3033), f'Should avoid occupied range'
            assert available_port > 1024, f'Should get valid port number: {available_port}'
            print(f'SUCCESS: Extended range fallback working - got port {available_port}')
        finally:
            for server in servers:
                server.stop()

    def test_cross_platform_consistency(self):
        """Test that port allocation works consistently across platforms."""
        test_port = 3040
        localhost_available = is_port_available(test_port, 'localhost')
        all_interfaces_available = is_port_available(test_port, '0.0.0.0')
        assert localhost_available == all_interfaces_available, 'Port availability should be consistent across interfaces'
        server = TestPortServer(test_port)
        if server.start():
            try:
                localhost_occupied = is_port_available(test_port, 'localhost')
                all_interfaces_occupied = is_port_available(test_port, '0.0.0.0')
                assert not localhost_occupied, 'Port should be unavailable on localhost'
                assert not all_interfaces_occupied, 'Port should be unavailable on 0.0.0.0'
                print(f'SUCCESS: Cross-platform consistency verified for port {test_port}')
            finally:
                server.stop()
        else:
            print(f'SKIP: Could not occupy port {test_port} for cross-platform test')

    def test_windows_specific_race_condition_prevention(self):
        """Test Windows-specific race condition prevention measures."""
        if sys.platform != 'win32':
            pytest.skip('Windows-specific test')
        port_manager = PortManager()
        test_port = 3050
        for i in range(5):
            allocated_port = port_manager.allocate_port(service_name=f'rapid_test_{i}', preferred_port=test_port + i, port_range=(3050, 3060))
            assert allocated_port is not None, f'Should allocate port in iteration {i}'
            tracked_port = port_manager.get_allocated_port(f'rapid_test_{i}')
            assert tracked_port == allocated_port, f'Should track port correctly in iteration {i}'
            released = port_manager.release_port(f'rapid_test_{i}')
            assert released, f'Should release port in iteration {i}'
            time.sleep(0.05)
        print('SUCCESS: Windows race condition prevention verified')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')