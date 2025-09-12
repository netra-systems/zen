#!/usr/bin/env python3
"""
Dynamic Port Allocation Script for Parallel Test Execution

This script allocates unique ports for Docker services to enable parallel test runs
without port conflicts. It implements the port allocation strategy defined in
docs/port_allocation_strategy.md

Usage:
    python scripts/allocate_test_ports.py [options]
    
Options:
    --parallel-id ID    Unique identifier for this test run (default: process ID)
    --env ENV           Environment name (default: dynamic-test)
    --base-port PORT    Starting port for allocation (default: 9500)
    --output FILE       Output env file (default: .env.dynamic)
    --check-only        Only check port availability, don't allocate
    --release           Release previously allocated ports
"""

import argparse
import os
import socket
import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import platform

# Port allocation configuration
DEFAULT_BASE_PORT = 9500
MAX_PORT = 9999
PORT_RETRY_COUNT = 10
PORT_GROUP_SIZE = 10  # Ports per service group

# Service port offsets within a group
SERVICE_OFFSETS = {
    'postgres': 0,
    'redis': 1,
    'clickhouse_http': 2,
    'clickhouse_tcp': 3,
    'backend': 4,
    'auth': 5,
    'frontend': 6,
}

# Allocation state file
ALLOCATION_STATE_FILE = '.port_allocations.json'


class PortAllocator:
    """Manages dynamic port allocation for Docker services"""
    
    def __init__(self, base_port: int = DEFAULT_BASE_PORT, parallel_id: Optional[str] = None):
        self.base_port = base_port
        self.parallel_id = parallel_id or str(os.getpid())
        self.allocations = {}
        self.state_file = Path(ALLOCATION_STATE_FILE)
        self.load_state()
    
    def load_state(self) -> None:
        """Load existing port allocations from state file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.allocations = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.allocations = {}
    
    def save_state(self) -> None:
        """Save port allocations to state file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.allocations, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save allocation state: {e}")
    
    def is_port_available(self, port: int, host: str = '127.0.0.1') -> bool:
        """Check if a port is available for binding"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.bind((host, port))
                return True
        except (socket.error, OSError):
            return False
    
    def check_docker_port(self, port: int) -> bool:
        """Check if port is used by any Docker container"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Ports}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if str(port) in line:
                        return False
            return True
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            # If Docker check fails, rely on socket check
            return True
    
    def find_available_port(self, start_port: int, service_name: str) -> Optional[int]:
        """Find an available port starting from the given port"""
        for attempt in range(PORT_RETRY_COUNT):
            port = start_port + attempt
            
            if port > MAX_PORT:
                return None
            
            if self.is_port_available(port) and self.check_docker_port(port):
                return port
            
            print(f"  Port {port} is occupied, trying next...")
        
        return None
    
    def calculate_port_group(self, parallel_id: str) -> int:
        """Calculate base port for a parallel test run"""
        # Use hash of parallel_id to get consistent port assignment
        id_hash = abs(hash(parallel_id))
        offset = (id_hash % 50) * PORT_GROUP_SIZE
        return self.base_port + offset
    
    def allocate_ports(self) -> Dict[str, int]:
        """Allocate ports for all services"""
        print(f"Allocating ports for parallel ID: {self.parallel_id}")
        
        # Calculate starting port based on parallel ID
        group_base = self.calculate_port_group(self.parallel_id)
        
        allocated_ports = {}
        failed_services = []
        
        for service, offset in SERVICE_OFFSETS.items():
            target_port = group_base + offset
            print(f"Checking {service}...")
            
            available_port = self.find_available_port(target_port, service)
            
            if available_port:
                allocated_ports[service] = available_port
                print(f"  [U+2713] Allocated port {available_port} for {service}")
            else:
                failed_services.append(service)
                print(f"  [U+2717] Failed to allocate port for {service}")
        
        if failed_services:
            print(f"\nError: Could not allocate ports for: {', '.join(failed_services)}")
            return {}
        
        # Save allocation with metadata
        self.allocations[self.parallel_id] = {
            'ports': allocated_ports,
            'timestamp': datetime.now().isoformat(),
            'pid': os.getpid()
        }
        self.save_state()
        
        return allocated_ports
    
    def release_ports(self, parallel_id: Optional[str] = None) -> bool:
        """Release previously allocated ports"""
        id_to_release = parallel_id or self.parallel_id
        
        if id_to_release in self.allocations:
            released = self.allocations[id_to_release]
            del self.allocations[id_to_release]
            self.save_state()
            
            print(f"Released ports for parallel ID: {id_to_release}")
            for service, port in released['ports'].items():
                print(f"  - {service}: {port}")
            return True
        else:
            print(f"No ports allocated for parallel ID: {id_to_release}")
            return False
    
    def check_ports(self, ports: Dict[str, int]) -> Dict[str, bool]:
        """Check availability of specific ports"""
        status = {}
        for service, port in ports.items():
            available = self.is_port_available(port) and self.check_docker_port(port)
            status[service] = available
            symbol = "[U+2713]" if available else "[U+2717]"
            print(f"  {symbol} {service}: {port} - {'available' if available else 'occupied'}")
        return status
    
    def generate_env_file(self, ports: Dict[str, int], env_name: str, output_file: str) -> None:
        """Generate environment file with allocated ports"""
        env_content = f"""# Dynamically Allocated Ports
# Generated: {datetime.now().isoformat()}
# Parallel ID: {self.parallel_id}
# Environment: {env_name}

# Port Allocations
DYNAMIC_POSTGRES_PORT={ports['postgres']}
DYNAMIC_REDIS_PORT={ports['redis']}
DYNAMIC_CLICKHOUSE_HTTP_PORT={ports['clickhouse_http']}
DYNAMIC_CLICKHOUSE_TCP_PORT={ports['clickhouse_tcp']}
DYNAMIC_BACKEND_PORT={ports['backend']}
DYNAMIC_AUTH_PORT={ports['auth']}
DYNAMIC_FRONTEND_PORT={ports['frontend']}

# Service Configuration
POSTGRES_PORT={ports['postgres']}
REDIS_PORT={ports['redis']}
CLICKHOUSE_HTTP_PORT={ports['clickhouse_http']}
CLICKHOUSE_TCP_PORT={ports['clickhouse_tcp']}
BACKEND_PORT={ports['backend']}
AUTH_PORT={ports['auth']}
FRONTEND_PORT={ports['frontend']}

# Environment Settings
ENVIRONMENT={env_name}
PARALLEL_ID={self.parallel_id}
COMPOSE_PROJECT_NAME=netra-{env_name}-{self.parallel_id}

# Test Mode
TEST_MODE=true
TESTING=1
"""
        
        try:
            with open(output_file, 'w') as f:
                f.write(env_content)
            print(f"\nGenerated environment file: {output_file}")
        except IOError as e:
            print(f"Error writing environment file: {e}")
            sys.exit(1)
    
    def cleanup_stale_allocations(self, max_age_hours: int = 24) -> int:
        """Clean up allocations older than max_age_hours"""
        now = datetime.now()
        stale_ids = []
        
        for parallel_id, allocation in self.allocations.items():
            if 'timestamp' in allocation:
                alloc_time = datetime.fromisoformat(allocation['timestamp'])
                age = (now - alloc_time).total_seconds() / 3600
                
                if age > max_age_hours:
                    stale_ids.append(parallel_id)
        
        for parallel_id in stale_ids:
            print(f"Cleaning up stale allocation: {parallel_id}")
            del self.allocations[parallel_id]
        
        if stale_ids:
            self.save_state()
        
        return len(stale_ids)


def check_system_ports() -> None:
    """Check commonly used ports on the system"""
    common_ports = {
        'PostgreSQL (default)': 5432,
        'PostgreSQL (dev)': 5433,
        'PostgreSQL (test)': 5434,
        'Redis (default)': 6379,
        'Redis (dev)': 6380,
        'Redis (test)': 6381,
        'Backend (default)': 8000,
        'Frontend (default)': 3000,
    }
    
    print("\nSystem Port Check:")
    print("-" * 40)
    
    allocator = PortAllocator()
    for name, port in common_ports.items():
        available = allocator.is_port_available(port)
        symbol = "[U+2713]" if available else "[U+2717]"
        status = "available" if available else "occupied"
        print(f"{symbol} {name:25} {port:5} - {status}")


def main():
    parser = argparse.ArgumentParser(
        description='Dynamic port allocation for parallel Docker test execution'
    )
    parser.add_argument(
        '--parallel-id',
        help='Unique identifier for this test run',
        default=None
    )
    parser.add_argument(
        '--env',
        help='Environment name',
        default='dynamic-test'
    )
    parser.add_argument(
        '--base-port',
        type=int,
        help='Starting port for allocation',
        default=DEFAULT_BASE_PORT
    )
    parser.add_argument(
        '--output',
        help='Output environment file',
        default='.env.dynamic'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check port availability'
    )
    parser.add_argument(
        '--release',
        action='store_true',
        help='Release previously allocated ports'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Clean up stale allocations'
    )
    parser.add_argument(
        '--system-check',
        action='store_true',
        help='Check common system ports'
    )
    
    args = parser.parse_args()
    
    # Initialize allocator
    allocator = PortAllocator(
        base_port=args.base_port,
        parallel_id=args.parallel_id
    )
    
    # Handle different operations
    if args.system_check:
        check_system_ports()
        return 0
    
    if args.cleanup:
        cleaned = allocator.cleanup_stale_allocations()
        print(f"Cleaned up {cleaned} stale allocations")
        return 0
    
    if args.release:
        success = allocator.release_ports()
        return 0 if success else 1
    
    # Allocate ports
    ports = allocator.allocate_ports()
    
    if not ports:
        print("\nFailed to allocate ports. Suggestions:")
        print("  1. Check for running Docker containers: docker ps")
        print("  2. Clean up old allocations: python scripts/allocate_test_ports.py --cleanup")
        print("  3. Use a different parallel ID: --parallel-id <unique-id>")
        return 1
    
    if args.check_only:
        print("\nPort availability check:")
        allocator.check_ports(ports)
    else:
        # Generate environment file
        allocator.generate_env_file(ports, args.env, args.output)
        
        print("\nDocker usage:")
        print(f"  docker-compose -f docker-compose.unified.yml --env-file {args.output} up")
        print("\nCleanup:")
        print(f"  python scripts/allocate_test_ports.py --release --parallel-id {allocator.parallel_id}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())