"""
Unit tests for Docker resource state validation - NO DOCKER BUILDS REQUIRED

Purpose: Validate Docker resource accumulation issues that cause build failures
Issue: #1082 - Docker Alpine build infrastructure failure
Approach: System resource and file system validation only, no container operations

MISSION CRITICAL: These tests must detect Docker resource issues causing:
"failed to solve: failed to compute cache key" errors

Business Impact: $500K+ ARR Golden Path depends on working Docker infrastructure
Critical Context: Issue escalated from P2 to P1 due to mission-critical test blocking

Test Strategy: These tests are designed to FAIL initially to prove they detect real issues
"""
import pytest
import os
import json
import shutil
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestDockerResourceStateValidation(SSotBaseTestCase):
    """Unit tests for Docker resource state validation - FILE SYSTEM ONLY

    These tests validate system resources and Docker-related file accumulation
    that can cause cache key computation failures.
    """

    def setup_method(self, method):
        """Setup test environment - locate Docker-related directories"""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.docker_dir = self.project_root / 'docker'
        self.dockerfiles_dir = self.project_root / 'dockerfiles'

        # Common Docker data locations
        self.docker_data_locations = [
            Path.home() / '.docker',
            Path('/var/lib/docker'),
            Path('/Users') / os.environ.get('USER', 'user') / 'Library/Containers/com.docker.docker',
            Path('/tmp/docker-buildx'),
            self.project_root / '.docker-cache'
        ]

        self.logger.info(f'Testing Docker resource state across system locations')

    def test_available_disk_space_sufficient_for_builds(self):
        """
        Test that available disk space is sufficient for Docker Alpine builds

        Issue: #1082 - Build failures suggest "docker system prune -a" needed
        Difficulty: Low (5 minutes)
        Expected: FAIL initially - Insufficient disk space causing cache key failures
        """
        disk_space_issues = []

        try:
            # Check disk space on project root drive
            project_disk_usage = shutil.disk_usage(self.project_root)
            available_gb = project_disk_usage.free / (1024**3)
            total_gb = project_disk_usage.total / (1024**3)
            used_gb = project_disk_usage.used / (1024**3)

            # Docker builds typically need 5-10GB free space
            min_required_gb = 5.0

            if available_gb < min_required_gb:
                disk_space_issues.append(
                    f"Insufficient disk space on {self.project_root.anchor}: "
                    f"{available_gb:.2f}GB available, {min_required_gb}GB required. "
                    f"Total: {total_gb:.2f}GB, Used: {used_gb:.2f}GB"
                )

            # Check if we're approaching capacity (>90% full)
            usage_percent = (used_gb / total_gb) * 100
            if usage_percent > 90:
                disk_space_issues.append(
                    f"Disk usage critically high: {usage_percent:.1f}% full on {self.project_root.anchor}. "
                    f"Docker builds may fail due to insufficient space for cache operations."
                )

        except Exception as e:
            disk_space_issues.append(f"Failed to check disk space: {str(e)}")

        assert not disk_space_issues, \
            f"Disk space validation failures: {json.dumps(disk_space_issues, indent=2)}. " \
            f"Insufficient disk space causes Docker cache key computation failures. " \
            f"Recommended: Run 'docker system prune -a' to free space."

    def test_docker_cache_directories_not_corrupted(self):
        """
        Test that Docker cache directories are not corrupted or excessively large

        Issue: #1082 - Cache key computation failures may indicate corrupted cache
        Difficulty: Medium (10 minutes)
        Expected: FAIL initially - Corrupted or oversized Docker cache directories
        """
        cache_issues = []

        for cache_location in self.docker_data_locations:
            if not cache_location.exists():
                continue

            try:
                # Check if directory is accessible
                if not os.access(cache_location, os.R_OK):
                    cache_issues.append(f"Docker cache directory not readable: {cache_location}")
                    continue

                # Calculate cache directory size
                total_size = 0
                file_count = 0
                error_files = []

                for file_path in cache_location.rglob('*'):
                    if file_path.is_file():
                        try:
                            file_size = file_path.stat().st_size
                            total_size += file_size
                            file_count += 1

                            # Check for corrupted files (0 bytes when they should have content)
                            if file_path.suffix in ['.json', '.tar', '.gz'] and file_size == 0:
                                error_files.append(str(file_path))

                        except (OSError, PermissionError):
                            error_files.append(f"{file_path} (access denied)")

                        # Limit iteration to prevent test timeouts
                        if file_count > 50000:
                            break

                cache_size_gb = total_size / (1024**3)

                # Docker cache shouldn't exceed 20GB typically
                if cache_size_gb > 20:
                    cache_issues.append(
                        f"Docker cache oversized: {cache_location} = {cache_size_gb:.2f}GB "
                        f"({file_count:,} files). May cause cache key computation failures."
                    )

                if error_files:
                    cache_issues.append(
                        f"Corrupted cache files in {cache_location}: "
                        f"{error_files[:5]} (showing first 5 of {len(error_files)})"
                    )

            except Exception as e:
                cache_issues.append(f"Failed to analyze cache directory {cache_location}: {str(e)}")

        assert not cache_issues, \
            f"Docker cache validation failures: {json.dumps(cache_issues, indent=2)}. " \
            f"Corrupted or oversized cache directories cause Alpine build cache key failures. " \
            f"Recommended: Run 'docker system prune -a' and 'docker builder prune -a'."

    def test_system_memory_sufficient_for_docker_builds(self):
        """
        Test that system memory is sufficient for Docker Alpine builds

        Issue: #1082 - Memory pressure can cause cache key computation failures
        Difficulty: Low (5 minutes)
        Expected: FAIL initially - Insufficient memory causing Docker build issues
        """
        memory_issues = []

        try:
            # Get system memory information
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            total_gb = memory.total / (1024**3)
            used_gb = memory.used / (1024**3)

            # Docker Alpine builds typically need 2GB+ available memory
            min_required_gb = 2.0

            if available_gb < min_required_gb:
                memory_issues.append(
                    f"Insufficient memory: {available_gb:.2f}GB available, "
                    f"{min_required_gb}GB required for Docker builds. "
                    f"Total: {total_gb:.2f}GB, Used: {used_gb:.2f}GB"
                )

            # Check memory usage percentage
            usage_percent = memory.percent
            if usage_percent > 90:
                memory_issues.append(
                    f"Memory usage critically high: {usage_percent:.1f}% used. "
                    f"Docker cache key computation may fail under memory pressure."
                )

            # Check swap usage if available
            try:
                swap = psutil.swap_memory()
                if swap.total > 0:
                    swap_percent = swap.percent
                    if swap_percent > 80:
                        memory_issues.append(
                            f"Swap usage high: {swap_percent:.1f}% used. "
                            f"Indicates memory pressure affecting Docker operations."
                        )
            except Exception:
                pass  # Swap info may not be available on all systems

        except Exception as e:
            memory_issues.append(f"Failed to check system memory: {str(e)}")

        assert not memory_issues, \
            f"System memory validation failures: {json.dumps(memory_issues, indent=2)}. " \
            f"Insufficient memory causes Docker Alpine build cache key computation failures."

    def test_docker_build_temporary_files_accumulation(self):
        """
        Test for excessive Docker temporary file accumulation

        Issue: #1082 - Temporary file buildup can cause cache key computation failures
        Difficulty: Medium (15 minutes)
        Expected: FAIL initially - Excessive temp files causing build issues
        """
        temp_file_issues = []

        # Common temporary file locations used by Docker
        temp_locations = [
            Path('/tmp'),
            Path('/var/tmp'),
            Path.home() / 'Library/Caches/com.docker.docker',  # macOS
            self.project_root / 'tmp'
        ]

        docker_temp_patterns = [
            'docker-build*',
            'buildx-*',
            'docker-*',
            '*.dockerignore.*',
            'buildkit-*'
        ]

        for temp_location in temp_locations:
            if not temp_location.exists():
                continue

            try:
                docker_temp_files = []
                docker_temp_size = 0

                for pattern in docker_temp_patterns:
                    matching_files = list(temp_location.glob(pattern))
                    for temp_file in matching_files:
                        try:
                            if temp_file.is_file():
                                file_size = temp_file.stat().st_size
                                docker_temp_size += file_size
                                docker_temp_files.append((str(temp_file), file_size))
                            elif temp_file.is_dir():
                                # Calculate directory size
                                dir_size = sum(f.stat().st_size for f in temp_file.rglob('*')
                                             if f.is_file())
                                docker_temp_size += dir_size
                                docker_temp_files.append((str(temp_file), dir_size))

                        except (OSError, PermissionError):
                            docker_temp_files.append((str(temp_file), -1))

                        # Limit to prevent test timeouts
                        if len(docker_temp_files) > 1000:
                            break

                temp_size_mb = docker_temp_size / (1024**2)

                # Check for excessive temporary file accumulation
                if temp_size_mb > 1000:  # 1GB
                    temp_file_issues.append(
                        f"Excessive Docker temp files in {temp_location}: "
                        f"{temp_size_mb:.2f}MB across {len(docker_temp_files)} files/dirs"
                    )

                # Check for old temporary files (older than 7 days)
                old_temp_files = []
                import time
                current_time = time.time()
                seven_days_ago = current_time - (7 * 24 * 60 * 60)

                for temp_file_path, size in docker_temp_files:
                    try:
                        temp_path = Path(temp_file_path)
                        if temp_path.exists():
                            mtime = temp_path.stat().st_mtime
                            if mtime < seven_days_ago:
                                old_temp_files.append(temp_file_path)
                    except (OSError, PermissionError):
                        pass

                    if len(old_temp_files) >= 10:
                        break

                if old_temp_files:
                    temp_file_issues.append(
                        f"Old Docker temp files in {temp_location}: "
                        f"{len(old_temp_files)} files older than 7 days (showing first 10): {old_temp_files[:10]}"
                    )

            except Exception as e:
                temp_file_issues.append(f"Failed to analyze temp files in {temp_location}: {str(e)}")

        assert not temp_file_issues, \
            f"Docker temporary file validation failures: {json.dumps(temp_file_issues, indent=2)}. " \
            f"Excessive temporary file accumulation causes Alpine build cache key computation failures. " \
            f"Recommended: Clean temporary files and run 'docker system prune -a'."

    def test_file_descriptor_limits_sufficient(self):
        """
        Test that system file descriptor limits are sufficient for Docker builds

        Issue: #1082 - File descriptor exhaustion can cause cache key computation failures
        Difficulty: Medium (10 minutes)
        Expected: FAIL initially - File descriptor limits too low for complex builds
        """
        fd_issues = []

        try:
            import resource

            # Get current file descriptor limits
            soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

            # Get current number of open file descriptors for this process
            current_process = psutil.Process()
            current_fds = len(current_process.open_files()) + len(current_process.connections())

            # Docker builds typically need 1000+ file descriptors available
            min_required_fds = 1000
            available_fds = soft_limit - current_fds

            if available_fds < min_required_fds:
                fd_issues.append(
                    f"Insufficient file descriptors: {available_fds} available, "
                    f"{min_required_fds} required for Docker builds. "
                    f"Soft limit: {soft_limit}, Hard limit: {hard_limit}, Currently open: {current_fds}"
                )

            # Check if soft limit is reasonable for Docker operations
            if soft_limit < 4096:
                fd_issues.append(
                    f"File descriptor soft limit too low: {soft_limit}. "
                    f"Docker Alpine builds may fail cache key computation with limits below 4096."
                )

            # Check system-wide file descriptor usage if possible
            try:
                with open('/proc/sys/fs/file-nr', 'r') as f:
                    allocated, unused, max_fds = map(int, f.read().strip().split())
                    system_usage_percent = (allocated / max_fds) * 100

                    if system_usage_percent > 80:
                        fd_issues.append(
                            f"System-wide file descriptor usage high: {system_usage_percent:.1f}% "
                            f"({allocated:,}/{max_fds:,}). May affect Docker build performance."
                        )
            except (FileNotFoundError, PermissionError, ValueError):
                pass  # /proc/sys/fs/file-nr not available on all systems

        except Exception as e:
            fd_issues.append(f"Failed to check file descriptor limits: {str(e)}")

        assert not fd_issues, \
            f"File descriptor limit validation failures: {json.dumps(fd_issues, indent=2)}. " \
            f"Insufficient file descriptor limits cause Docker cache key computation failures. " \
            f"Recommended: Increase ulimit -n or system file descriptor limits."

    def test_docker_daemon_resource_conflicts(self):
        """
        Test for resource conflicts that prevent Docker daemon operations

        Issue: #1082 - Resource conflicts can cause cache key computation failures
        Difficulty: High (20 minutes)
        Expected: FAIL initially - Port conflicts or resource locks affecting Docker
        """
        resource_conflict_issues = []

        # Check for port conflicts that affect Docker operations
        docker_ports = [2375, 2376, 2377]  # Docker daemon ports
        project_ports = [5432, 6379, 8000, 8001, 3000]  # Ports used by our services

        try:
            # Check if any processes are using Docker ports
            for port in docker_ports:
                connections = psutil.net_connections()
                port_users = [conn for conn in connections if conn.laddr.port == port]

                if port_users:
                    resource_conflict_issues.append(
                        f"Docker port {port} in use by {len(port_users)} connections. "
                        f"May prevent Docker daemon operations."
                    )

            # Check for excessive processes that might compete for resources
            process_count = len(psutil.pids())
            if process_count > 500:
                resource_conflict_issues.append(
                    f"High process count: {process_count} processes running. "
                    f"May cause resource contention affecting Docker builds."
                )

            # Check for Docker-related processes that might be stuck
            docker_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    if proc_info['name'] and any(docker_term in proc_info['name'].lower()
                                                for docker_term in ['docker', 'containerd', 'buildx']):
                        docker_processes.append({
                            'pid': proc_info['pid'],
                            'name': proc_info['name'],
                            'cmdline': ' '.join(proc_info['cmdline'] or [])[:100]
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

                if len(docker_processes) >= 20:
                    break

            if len(docker_processes) > 10:
                resource_conflict_issues.append(
                    f"Many Docker-related processes running: {len(docker_processes)} processes. "
                    f"Sample: {docker_processes[:3]}. May indicate stuck builds."
                )

        except Exception as e:
            resource_conflict_issues.append(f"Failed to check resource conflicts: {str(e)}")

        assert not resource_conflict_issues, \
            f"Docker daemon resource conflict validation failures: {json.dumps(resource_conflict_issues, indent=2)}. " \
            f"Resource conflicts cause Docker Alpine build cache key computation failures. " \
            f"Recommended: Kill stuck Docker processes and restart Docker daemon."