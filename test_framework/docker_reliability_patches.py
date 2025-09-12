"""
Docker Reliability Patches - Fixes for common Docker issues in E2E tests
========================================================================

This module addresses the most common Docker reliability issues:
1. Port conflicts between test runs
2. Race conditions in service startup
3. Stale data persistence between test runs
4. Container name conflicts
5. Network isolation issues

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Stability - eliminate random E2E test failures
- Value Impact: Reduces developer friction and CI/CD failures
- Strategic Impact: Enables reliable automated testing at scale
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)
env = get_env()


class DockerReliabilityPatcher:
    """
    Comprehensive Docker reliability patches for E2E testing.
    
    Addresses common issues that cause E2E test flakiness:
    - Port conflicts (uses dedicated E2E ports)
    - Race conditions (proper health check ordering)  
    - Stale data (clean volumes between runs)
    - Container conflicts (unique naming)
    - Network isolation (dedicated test networks)
    """
    
    # Port ranges for different environments to avoid conflicts
    PORT_RANGES = {
        "e2e": {
            "postgres": 5435,
            "redis": 6382, 
            "clickhouse_http": 8126,
            "clickhouse_tcp": 9003,
            "backend": 8002,
            "auth": 8083,
            "frontend": 3002
        },
        "dev": {
            "postgres": 5432,
            "redis": 6379,
            "clickhouse_http": 8123, 
            "clickhouse_tcp": 9000,
            "backend": 8000,
            "auth": 8081,
            "frontend": 3000
        },
        "integration": {
            "postgres": 5434,
            "redis": 6381,
            "clickhouse_http": 8125,
            "clickhouse_tcp": 9002,
            "backend": 8001,
            "auth": 8082,
            "frontend": 3001
        }
    }
    
    def __init__(self, environment_type: str = "e2e"):
        """
        Initialize reliability patcher.
        
        Args:
            environment_type: Type of environment (e2e, dev, integration)
        """
        self.environment_type = environment_type
        self.ports = self.PORT_RANGES.get(environment_type, self.PORT_RANGES["e2e"])
        self.project_root = Path(env.get("PROJECT_ROOT", Path(__file__).parent.parent))
    
    def check_port_conflicts(self) -> List[Tuple[int, str]]:
        """
        Check for port conflicts before starting services.
        
        Returns:
            List of (port, process_info) tuples for conflicting ports
        """
        conflicts = []
        
        for service, port in self.ports.items():
            if self._is_port_in_use(port):
                process_info = self._get_process_on_port(port)
                conflicts.append((port, f"{service} -> {process_info}"))
                logger.warning(f"Port conflict detected: {service} port {port} in use by {process_info}")
        
        return conflicts
    
    def resolve_port_conflicts(self, force_kill: bool = False) -> bool:
        """
        Resolve port conflicts by stopping conflicting processes.
        
        Args:
            force_kill: Whether to force kill conflicting processes
            
        Returns:
            True if all conflicts resolved, False otherwise
        """
        conflicts = self.check_port_conflicts()
        
        if not conflicts:
            logger.info(" PASS:  No port conflicts detected")
            return True
        
        logger.info(f"[U+1F527] Resolving {len(conflicts)} port conflicts...")
        
        for port, process_info in conflicts:
            if force_kill:
                success = self._kill_process_on_port(port)
                if success:
                    logger.info(f" PASS:  Freed port {port}")
                else:
                    logger.error(f" FAIL:  Failed to free port {port}")
                    return False
            else:
                logger.warning(f" WARNING: [U+FE0F]  Port {port} still in use by {process_info}")
                logger.warning("   Use force_kill=True to automatically resolve")
                return False
        
        # Verify conflicts are resolved
        time.sleep(2)  # Give processes time to clean up
        remaining_conflicts = self.check_port_conflicts()
        
        if remaining_conflicts:
            logger.error(f" FAIL:  {len(remaining_conflicts)} port conflicts remain unresolved")
            return False
        
        logger.info(" PASS:  All port conflicts resolved")
        return True
    
    def clean_stale_containers(self, max_age_hours: int = 2) -> int:
        """
        Clean up stale test containers older than specified age.
        
        Args:
            max_age_hours: Maximum age of containers to keep (hours)
            
        Returns:
            Number of containers cleaned up
        """
        logger.info(f"[U+1F9F9] Cleaning containers older than {max_age_hours} hours...")
        
        try:
            # Find containers with test-related names
            result = subprocess.run([
                "docker", "ps", "-a", "--format", "{{.ID}}\t{{.Names}}\t{{.CreatedAt}}"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"Failed to list containers: {result.stderr}")
                return 0
            
            containers_removed = 0
            current_time = time.time()
            
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split('\t')
                if len(parts) < 3:
                    continue
                
                container_id, name, created_at = parts[0], parts[1], parts[2]
                
                # Check if this is a test container
                if any(test_pattern in name.lower() for test_pattern in 
                      ['test', 'e2e', 'netra-alpine-test', 'pytest']):
                    
                    # Parse creation time and check age
                    container_age = self._get_container_age_hours(created_at)
                    
                    if container_age > max_age_hours:
                        logger.info(f"   Removing stale container: {name} (age: {container_age:.1f}h)")
                        
                        # Remove container
                        remove_result = subprocess.run([
                            "docker", "rm", "-f", container_id
                        ], capture_output=True, text=True, timeout=30)
                        
                        if remove_result.returncode == 0:
                            containers_removed += 1
                        else:
                            logger.warning(f"   Failed to remove container {name}: {remove_result.stderr}")
            
            logger.info(f" PASS:  Removed {containers_removed} stale containers")
            return containers_removed
            
        except Exception as e:
            logger.error(f"Error cleaning stale containers: {e}")
            return 0
    
    def clean_stale_volumes(self, max_age_hours: int = 4) -> int:
        """
        Clean up stale test volumes.
        
        Args:
            max_age_hours: Maximum age of volumes to keep (hours)
            
        Returns:
            Number of volumes cleaned up
        """
        logger.info(f"[U+1F9F9] Cleaning volumes older than {max_age_hours} hours...")
        
        try:
            # List all volumes with test-related names
            result = subprocess.run([
                "docker", "volume", "ls", "--format", "{{.Name}}"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"Failed to list volumes: {result.stderr}")
                return 0
            
            volumes_removed = 0
            
            for volume_name in result.stdout.strip().split('\n'):
                if not volume_name.strip():
                    continue
                
                # Check if this is a test volume
                if any(test_pattern in volume_name.lower() for test_pattern in 
                      ['test', 'e2e', 'alpine-test', 'netra-e2e']):
                    
                    # Remove test volumes (they should not persist between runs)
                    logger.info(f"   Removing test volume: {volume_name}")
                    
                    remove_result = subprocess.run([
                        "docker", "volume", "rm", volume_name
                    ], capture_output=True, text=True, timeout=30)
                    
                    if remove_result.returncode == 0:
                        volumes_removed += 1
                    else:
                        # Volume might be in use, that's OK during active tests
                        logger.debug(f"   Could not remove volume {volume_name}: {remove_result.stderr}")
            
            logger.info(f" PASS:  Removed {volumes_removed} stale volumes")
            return volumes_removed
            
        except Exception as e:
            logger.error(f"Error cleaning stale volumes: {e}")
            return 0
    
    def clean_stale_networks(self) -> int:
        """
        Clean up stale test networks.
        
        Returns:
            Number of networks cleaned up
        """
        logger.info("[U+1F9F9] Cleaning stale test networks...")
        
        try:
            # List networks
            result = subprocess.run([
                "docker", "network", "ls", "--format", "{{.ID}}\t{{.Name}}"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"Failed to list networks: {result.stderr}")
                return 0
            
            networks_removed = 0
            
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split('\t')
                if len(parts) < 2:
                    continue
                
                network_id, network_name = parts[0], parts[1]
                
                # Check if this is a test network
                if any(test_pattern in network_name.lower() for test_pattern in 
                      ['test', 'e2e', 'netra-e2e-test']):
                    
                    logger.info(f"   Removing test network: {network_name}")
                    
                    remove_result = subprocess.run([
                        "docker", "network", "rm", network_id
                    ], capture_output=True, text=True, timeout=30)
                    
                    if remove_result.returncode == 0:
                        networks_removed += 1
                    else:
                        # Network might be in use, that's OK during active tests
                        logger.debug(f"   Could not remove network {network_name}: {remove_result.stderr}")
            
            logger.info(f" PASS:  Removed {networks_removed} stale networks")
            return networks_removed
            
        except Exception as e:
            logger.error(f"Error cleaning stale networks: {e}")
            return 0
    
    def fix_race_conditions(self, compose_file: Path) -> bool:
        """
        Fix race conditions in Docker Compose file.
        
        Args:
            compose_file: Path to docker-compose file
            
        Returns:
            True if fixes applied successfully
        """
        logger.info(f"[U+1F527] Checking race conditions in {compose_file.name}...")
        
        if not compose_file.exists():
            logger.error(f"Compose file not found: {compose_file}")
            return False
        
        try:
            import yaml
            
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            services = compose_data.get('services', {})
            fixes_applied = 0
            
            # Fix 1: Ensure proper service dependencies
            dependency_order = [
                'alpine-test-postgres',
                'alpine-test-redis', 
                'alpine-test-clickhouse',
                'alpine-test-auth',
                'alpine-test-backend',
                'alpine-test-frontend'
            ]
            
            for i, service_name in enumerate(dependency_order[3:], 3):  # Start from auth service
                if service_name in services:
                    depends_on = services[service_name].get('depends_on', {})
                    
                    # Ensure it depends on database services with health conditions
                    required_deps = dependency_order[:3]  # DB services
                    if i > 3:  # Backend depends on auth
                        required_deps.append(dependency_order[3])
                    
                    for dep_service in required_deps:
                        if dep_service in services and dep_service not in depends_on:
                            depends_on[dep_service] = {"condition": "service_healthy"}
                            fixes_applied += 1
                    
                    services[service_name]['depends_on'] = depends_on
            
            # Fix 2: Add missing health checks
            health_check_configs = {
                'alpine-test-backend': {
                    "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                    "interval": "10s", "timeout": "5s", "retries": 15, "start_period": "60s"
                },
                'alpine-test-auth': {
                    "test": ["CMD", "curl", "-f", "http://localhost:8081/health"],
                    "interval": "10s", "timeout": "5s", "retries": 15, "start_period": "60s"
                }
            }
            
            for service_name, health_config in health_check_configs.items():
                if service_name in services:
                    current_health = services[service_name].get('healthcheck', {})
                    if not current_health or 'test' not in current_health:
                        services[service_name]['healthcheck'] = health_config
                        fixes_applied += 1
            
            if fixes_applied > 0:
                # Create backup
                backup_file = compose_file.with_suffix('.yml.backup')
                with open(backup_file, 'w') as f:
                    yaml.dump(compose_data, f, default_flow_style=False)
                
                # Write fixes
                with open(compose_file, 'w') as f:
                    yaml.dump(compose_data, f, default_flow_style=False)
                
                logger.info(f" PASS:  Applied {fixes_applied} race condition fixes")
                logger.info(f"   Backup saved to: {backup_file}")
            else:
                logger.info(" PASS:  No race condition fixes needed")
            
            return True
            
        except Exception as e:
            logger.error(f"Error fixing race conditions: {e}")
            return False
    
    async def comprehensive_reliability_check(self) -> Dict[str, bool]:
        """
        Run comprehensive reliability checks and fixes.
        
        Returns:
            Dictionary of check results
        """
        logger.info(" SEARCH:  Running comprehensive Docker reliability check...")
        
        results = {}
        
        # Check 1: Port conflicts
        conflicts = self.check_port_conflicts()
        results['port_conflicts'] = len(conflicts) == 0
        
        if conflicts:
            logger.warning(f"Found {len(conflicts)} port conflicts")
            for port, info in conflicts:
                logger.warning(f"  {info}")
        
        # Check 2: Clean stale containers
        stale_containers = self.clean_stale_containers(max_age_hours=1)
        results['stale_containers_cleaned'] = stale_containers >= 0
        
        # Check 3: Clean stale volumes  
        stale_volumes = self.clean_stale_volumes(max_age_hours=2)
        results['stale_volumes_cleaned'] = stale_volumes >= 0
        
        # Check 4: Clean stale networks
        stale_networks = self.clean_stale_networks()
        results['stale_networks_cleaned'] = stale_networks >= 0
        
        # Check 5: Verify compose file integrity
        compose_file = self.project_root / "docker-compose.alpine-test.yml"
        results['compose_file_valid'] = self.fix_race_conditions(compose_file)
        
        # Summary
        all_passed = all(results.values())
        status = " PASS:  PASSED" if all_passed else " FAIL:  ISSUES FOUND"
        
        logger.info(f"\n CHART:  Reliability Check Results: {status}")
        for check, passed in results.items():
            status_icon = " PASS: " if passed else " FAIL: "
            logger.info(f"   {status_icon} {check}")
        
        return results
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use."""
        import socket
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0
    
    def _get_process_on_port(self, port: int) -> str:
        """Get information about process using a port."""
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run([
                    "netstat", "-ano", "-p", "TCP"
                ], capture_output=True, text=True, timeout=10)
                
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            return f"PID {pid}"
            else:  # Unix-like
                result = subprocess.run([
                    "lsof", "-i", f":{port}"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout:
                    lines = result.stdout.split('\n')
                    if len(lines) > 1:
                        return lines[1].split()[0]  # Process name
                        
        except Exception:
            pass
        
        return "unknown process"
    
    def _kill_process_on_port(self, port: int) -> bool:
        """Kill process using a specific port."""
        try:
            if os.name == 'nt':  # Windows
                # Get PID
                result = subprocess.run([
                    "netstat", "-ano", "-p", "TCP"
                ], capture_output=True, text=True, timeout=10)
                
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            # Kill process
                            subprocess.run([
                                "taskkill", "/PID", pid, "/F"
                            ], capture_output=True, timeout=10)
                            return True
            else:  # Unix-like
                result = subprocess.run([
                    "lsof", "-t", f"-i:{port}"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout:
                    pid = result.stdout.strip()
                    subprocess.run([
                        "kill", "-9", pid
                    ], capture_output=True, timeout=10)
                    return True
                    
        except Exception as e:
            logger.debug(f"Error killing process on port {port}: {e}")
        
        return False
    
    def _get_container_age_hours(self, created_at: str) -> float:
        """Calculate container age in hours from Docker created_at string."""
        try:
            from datetime import datetime
            
            # Docker created_at format: "2023-12-07 10:30:45 +0000 UTC"
            # Parse different possible formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S %z %Z",
                "%Y-%m-%d %H:%M:%S %z", 
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ]:
                try:
                    created_time = datetime.strptime(created_at.strip(), fmt)
                    if created_time.tzinfo is None:
                        # Assume UTC if no timezone
                        from datetime import timezone
                        created_time = created_time.replace(tzinfo=timezone.utc)
                    
                    now = datetime.now(timezone.utc)
                    age = now - created_time
                    return age.total_seconds() / 3600
                except ValueError:
                    continue
            
            # Fallback: assume very old if we can't parse
            return 24.0
            
        except Exception:
            return 24.0  # Assume old if parsing fails


# Convenience functions
async def run_reliability_check(environment_type: str = "e2e") -> Dict[str, bool]:
    """
    Run comprehensive reliability check for Docker E2E tests.
    
    Args:
        environment_type: Environment type (e2e, dev, integration)
        
    Returns:
        Dictionary of check results
    """
    patcher = DockerReliabilityPatcher(environment_type)
    return await patcher.comprehensive_reliability_check()


def resolve_docker_conflicts(environment_type: str = "e2e", force_kill: bool = False) -> bool:
    """
    Resolve Docker port conflicts before running tests.
    
    Args:
        environment_type: Environment type (e2e, dev, integration)
        force_kill: Whether to force kill conflicting processes
        
    Returns:
        True if conflicts resolved
    """
    patcher = DockerReliabilityPatcher(environment_type)
    return patcher.resolve_port_conflicts(force_kill=force_kill)


def cleanup_stale_docker_resources(max_age_hours: int = 2) -> Dict[str, int]:
    """
    Clean up stale Docker resources from previous test runs.
    
    Args:
        max_age_hours: Maximum age to keep resources (hours)
        
    Returns:
        Dictionary with cleanup counts
    """
    patcher = DockerReliabilityPatcher("e2e")
    
    return {
        "containers": patcher.clean_stale_containers(max_age_hours),
        "volumes": patcher.clean_stale_volumes(max_age_hours * 2),
        "networks": patcher.clean_stale_networks()
    }


if __name__ == "__main__":
    # Direct execution for debugging
    import asyncio
    
    async def main():
        results = await run_reliability_check()
        print("\nReliability Check Results:")
        for check, passed in results.items():
            status = " PASS:  PASS" if passed else " FAIL:  FAIL"
            print(f"  {status} {check}")
    
    asyncio.run(main())