"""
System Checks

Handles system resource and network connectivity checks.
Maintains 8-line function limit and focused responsibility.
"""

import socket
from typing import List, Tuple
from pathlib import Path
import psutil
from app.config import settings
from .models import StartupCheckResult


class SystemChecker:
    """Handles system resource and network checks"""
    
    async def check_file_permissions(self) -> StartupCheckResult:
        """Check file system permissions for required directories"""
        required_dirs = ["logs", "uploads", "temp"]
        issues = []
        
        for dir_name in required_dirs:
            try:
                self._test_directory_access(dir_name)
            except Exception as e:
                issues.append(f"{dir_name}: {e}")
        
        if issues:
            return StartupCheckResult(
                name="file_permissions",
                success=False,
                message=f"Permission issues: {'; '.join(issues)}",
                critical=False
            )
        else:
            return StartupCheckResult(
                name="file_permissions",
                success=True,
                message="All required directories are accessible",
                critical=False
            )
    
    async def check_memory_and_resources(self) -> StartupCheckResult:
        """Check system resources"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_count = psutil.cpu_count()
            
            warnings = self._check_resource_warnings(memory, disk, cpu_count)
            
            if warnings:
                return StartupCheckResult(
                    name="system_resources",
                    success=True,
                    message=f"Resource warnings: {'; '.join(warnings)}",
                    critical=False
                )
            else:
                memory_gb = memory.available / (1024**3)
                disk_gb = disk.free / (1024**3)
                return StartupCheckResult(
                    name="system_resources",
                    success=True,
                    message=f"Resources OK: {memory_gb:.1f}GB RAM, {disk_gb:.1f}GB disk, {cpu_count} CPUs",
                    critical=False
                )
        except Exception as e:
            return StartupCheckResult(
                name="system_resources",
                success=True,
                message=f"Could not check resources: {e}",
                critical=False
            )
    
    async def check_network_connectivity(self) -> StartupCheckResult:
        """Check network connectivity to critical services"""
        endpoints = self._get_network_endpoints()
        failed = []
        
        for service, endpoint in endpoints:
            try:
                self._test_endpoint_connectivity(endpoint)
            except Exception as e:
                failed.append(f"{service} ({endpoint}): {e}")
        
        if failed:
            return StartupCheckResult(
                name="network_connectivity",
                success=False,
                message=f"Cannot reach: {', '.join(failed)}",
                critical=False
            )
        else:
            return StartupCheckResult(
                name="network_connectivity",
                success=True,
                message="All network endpoints reachable",
                critical=False
            )
    
    def _test_directory_access(self, dir_name: str) -> None:
        """Test directory access permissions"""
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        
        test_file = dir_path / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    
    def _check_resource_warnings(self, memory, disk, cpu_count: int) -> List[str]:
        """Check for resource warnings"""
        warnings = []
        
        available_gb = memory.available / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        
        if available_gb < 1:
            warnings.append(f"Low memory: {available_gb:.1f}GB available")
        if disk_free_gb < 5:
            warnings.append(f"Low disk space: {disk_free_gb:.1f}GB free")
        if cpu_count < 2:
            warnings.append(f"Low CPU count: {cpu_count} cores")
        
        return warnings
    
    def _get_network_endpoints(self) -> List[Tuple[str, str]]:
        """Get network endpoints to test"""
        db_endpoint = "localhost:5432"
        if '@' in settings.database_url:
            db_endpoint = settings.database_url.split('@')[1].split('/')[0]
        
        redis_endpoint = "localhost:6379"
        if settings.redis:
            redis_endpoint = f"{settings.redis.host}:{settings.redis.port}"
        
        return [
            ("postgresql", db_endpoint),
            ("redis", redis_endpoint),
        ]
    
    def _test_endpoint_connectivity(self, endpoint: str) -> None:
        """Test connectivity to network endpoint"""
        if ':' in endpoint:
            host, port = endpoint.split(':')
            port = int(port)
        else:
            host = endpoint
            port = 80
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result != 0:
            raise ConnectionError(f"Cannot connect to {endpoint}")