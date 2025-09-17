"""
System Checks

Handles system resource and network connectivity checks.
Maintains 25-line function limit and focused responsibility.
"""

import socket
from pathlib import Path
from typing import List, Tuple

import psutil

from netra_backend.app.config import get_config as get_unified_config
from netra_backend.app.core.network_constants import ServicePorts, HostConstants
from netra_backend.app.startup_checks.models import StartupCheckResult


class SystemChecker:
    """Handles system resource and network checks"""
    
    async def check_file_permissions(self) -> StartupCheckResult:
        """Check file system permissions for required directories"""
        required_dirs = ["logs", "uploads", "temp"]
        issues = self._test_all_directories(required_dirs)
        
        if issues:
            return self._create_permission_failure_result(issues)
        return self._create_permission_success_result()
    
    async def check_memory_and_resources(self) -> StartupCheckResult:
        """Check system resources"""
        try:
            memory, disk, cpu_count = self._collect_system_metrics()
            warnings = self._check_resource_warnings(memory, disk, cpu_count)
            return self._create_resource_result(memory, disk, cpu_count, warnings)
        except Exception as e:
            return self._create_resource_error_result(e)
    
    async def check_network_connectivity(self) -> StartupCheckResult:
        """Check network connectivity to critical services"""
        endpoints = self._get_network_endpoints()
        failed = self._test_all_endpoints(endpoints)
        
        if failed:
            return self._create_network_failure_result(failed)
        return self._create_network_success_result()
    
    def _test_directory_access(self, dir_name: str) -> None:
        """Test directory access permissions"""
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        
        test_file = dir_path / ".write_test"
        test_file.write_text("test")
        test_file.unlink()

    def _test_all_directories(self, required_dirs: List[str]) -> List[str]:
        """Test all required directories for access"""
        issues = []
        for dir_name in required_dirs:
            issue = self._test_single_directory(dir_name)
            if issue:
                issues.append(issue)
        return issues
    
    def _test_single_directory(self, dir_name: str) -> str:
        """Test single directory and return issue if any"""
        try:
            self._test_directory_access(dir_name)
            return ""
        except Exception as e:
            return f"{dir_name}: {e}"

    def _create_permission_failure_result(self, issues: List[str]) -> StartupCheckResult:
        """Create permission failure result"""
        return StartupCheckResult(
            name="file_permissions", success=False, critical=False,
            message=f"Permission issues: {'; '.join(issues)}"
        )

    def _create_permission_success_result(self) -> StartupCheckResult:
        """Create permission success result"""
        return StartupCheckResult(
            name="file_permissions", success=True, critical=False,
            message="All required directories are accessible"
        )

    def _collect_system_metrics(self) -> Tuple:
        """Collect system memory, disk, and CPU metrics"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_count = psutil.cpu_count()
        return memory, disk, cpu_count

    def _create_resource_result(self, memory, disk, cpu_count: int, warnings: List[str]) -> StartupCheckResult:
        """Create resource check result"""
        if warnings:
            return self._create_resource_warning_result(warnings)
        return self._create_resource_ok_result(memory, disk, cpu_count)

    def _create_resource_warning_result(self, warnings: List[str]) -> StartupCheckResult:
        """Create resource warning result"""
        return StartupCheckResult(
            name="system_resources", success=True, critical=False,
            message=f"Resource warnings: {'; '.join(warnings)}"
        )

    def _create_resource_ok_result(self, memory, disk, cpu_count: int) -> StartupCheckResult:
        """Create resource OK result"""
        memory_gb = memory.available / (1024**3)
        disk_gb = disk.free / (1024**3)
        return StartupCheckResult(
            name="system_resources", success=True, critical=False,
            message=f"Resources OK: {memory_gb:.1f}GB RAM, {disk_gb:.1f}GB disk, {cpu_count} CPUs"
        )

    def _create_resource_error_result(self, error: Exception) -> StartupCheckResult:
        """Create resource error result"""
        return StartupCheckResult(
            name="system_resources", success=True, critical=False,
            message=f"Could not check resources: {error}"
        )

    def _test_all_endpoints(self, endpoints: List[Tuple[str, str]]) -> List[str]:
        """Test all network endpoints"""
        failed = []
        for service, endpoint in endpoints:
            failure = self._test_single_endpoint(service, endpoint)
            if failure:
                failed.append(failure)
        return failed
    
    def _test_single_endpoint(self, service: str, endpoint: str) -> str:
        """Test single endpoint and return failure message if any"""
        try:
            self._test_endpoint_connectivity(endpoint)
            return ""
        except Exception as e:
            return f"{service} ({endpoint}): {e}"

    def _create_network_failure_result(self, failed: List[str]) -> StartupCheckResult:
        """Create network failure result"""
        return StartupCheckResult(
            name="network_connectivity", success=False, critical=False,
            message=f"Cannot reach: {', '.join(failed)}"
        )

    def _create_network_success_result(self) -> StartupCheckResult:
        """Create network success result"""
        return StartupCheckResult(
            name="network_connectivity", success=True, critical=False,
            message="All network endpoints reachable"
        )

    def _check_memory_warning(self, warnings: List[str], available_gb: float) -> None:
        """Check for memory warnings"""
        if available_gb < 1:
            warnings.append(f"Low memory: {available_gb:.1f}GB available")

    def _check_disk_warning(self, warnings: List[str], disk_free_gb: float) -> None:
        """Check for disk space warnings"""
        if disk_free_gb < 5:
            warnings.append(f"Low disk space: {disk_free_gb:.1f}GB free")

    def _check_cpu_warning(self, warnings: List[str], cpu_count: int) -> None:
        """Check for CPU warnings"""
        if cpu_count < 2:
            warnings.append(f"Low CPU count: {cpu_count} cores")

    def _get_database_endpoint(self) -> str:
        """Get database endpoint from unified configuration"""
        try:
            config = get_unified_config()
            database_url = getattr(config, 'database_url', '')
            if '@' in database_url:
                return database_url.split('@')[1].split('/')[0]
            # Use configured constants instead of hardcoded values
            return f"{HostConstants.LOCALHOST}:{ServicePorts.POSTGRES_DEFAULT}"
        except Exception:
            # Graceful fallback during early startup if config is not fully loaded
            return f"{HostConstants.LOCALHOST}:{ServicePorts.POSTGRES_DEFAULT}"

    def _get_redis_endpoint(self) -> str:
        """Get Redis endpoint from unified configuration"""
        try:
            config = get_unified_config()
            redis_config = getattr(config, 'redis', None)
            if redis_config:
                host = getattr(redis_config, 'host', HostConstants.LOCALHOST)
                port = getattr(redis_config, 'port', ServicePorts.REDIS_DEFAULT)
                return f"{host}:{port}"
            # Use configured constants instead of hardcoded values
            return f"{HostConstants.LOCALHOST}:{ServicePorts.REDIS_DEFAULT}"
        except Exception:
            # Graceful fallback during early startup if config is not fully loaded
            return f"{HostConstants.LOCALHOST}:{ServicePorts.REDIS_DEFAULT}"

    def _parse_endpoint(self, endpoint: str) -> Tuple[str, int]:
        """Parse endpoint into host and port"""
        if ':' in endpoint:
            host, port = endpoint.split(':')
            return host, int(port)
        return endpoint, 80

    def _create_test_socket(self) -> socket.socket:
        """Create test socket with timeout"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        return sock
    
    def _check_resource_warnings(self, memory, disk, cpu_count: int) -> List[str]:
        """Check for resource warnings"""
        warnings = []
        resource_metrics = self._calculate_resource_metrics(memory, disk)
        self._check_all_resource_warnings(warnings, resource_metrics, cpu_count)
        return warnings
    
    def _calculate_resource_metrics(self, memory, disk) -> dict:
        """Calculate resource metrics in GB"""
        return {
            "available_gb": memory.available / (1024**3),
            "disk_free_gb": disk.free / (1024**3)
        }
    
    def _check_all_resource_warnings(self, warnings: List[str], metrics: dict, cpu_count: int) -> None:
        """Check all resource types for warnings"""
        self._check_memory_warning(warnings, metrics["available_gb"])
        self._check_disk_warning(warnings, metrics["disk_free_gb"])
        self._check_cpu_warning(warnings, cpu_count)
    
    def _get_network_endpoints(self) -> List[Tuple[str, str]]:
        """Get network endpoints to test"""
        db_endpoint = self._get_database_endpoint()
        redis_endpoint = self._get_redis_endpoint()
        return [
            ("postgresql", db_endpoint),
            ("redis", redis_endpoint),
        ]
    
    def _test_endpoint_connectivity(self, endpoint: str) -> None:
        """Test connectivity to network endpoint"""
        host, port = self._parse_endpoint(endpoint)
        sock = self._create_test_socket()
        result = sock.connect_ex((host, port))
        sock.close()
        if result != 0:
            raise ConnectionError(f"Cannot connect to {endpoint}")