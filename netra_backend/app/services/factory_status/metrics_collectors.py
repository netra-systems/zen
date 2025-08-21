"""Factory Status Metrics Collectors.

Specialized collectors for different types of factory metrics.
Each collector handles a specific domain of metrics collection.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import psutil
import os

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SystemMetricsCollector:
    """Collects system performance metrics."""
    
    async def collect(self) -> Dict[str, float]:
        """Get system performance metrics."""
        try:
            return await self._collect_system_data()
        except Exception as e:
            logger.warning(f"System metrics collection failed: {e}")
            return await self._get_default_system_metrics()
    
    async def _collect_system_data(self) -> Dict[str, float]:
        """Collect actual system performance data."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load_avg = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0.0
        return self._format_system_metrics(cpu_percent, memory.percent, disk.percent, load_avg)
    
    def _format_system_metrics(self, cpu: float, memory: float, disk: float, load: float) -> Dict[str, float]:
        """Format system metrics into standard dictionary."""
        return {
            "cpu_usage": cpu,
            "memory_usage": memory,
            "disk_usage": disk,
            "load_average": load
        }
    
    async def _get_default_system_metrics(self) -> Dict[str, float]:
        """Get default system metrics when collection fails."""
        return {"cpu_usage": 0.0, "memory_usage": 0.0, "disk_usage": 0.0, "load_average": 0.0}


class GitMetricsCollector:
    """Collects git repository metrics."""
    
    async def collect(self) -> Dict[str, Any]:
        """Get git repository metrics."""
        try:
            result = await self._execute_git_log_command()
            return await self._parse_git_result(result)
        except Exception as e:
            logger.warning(f"Git metrics collection failed: {e}")
            return await self._get_default_git_metrics()
    
    async def _execute_git_log_command(self) -> tuple:
        """Execute git log command and return process result."""
        result = await self._create_git_process()
        stdout, stderr = await result.communicate()
        return result.returncode, stdout, stderr
    
    async def _create_git_process(self):
        """Create git log subprocess."""
        return await asyncio.create_subprocess_exec(
            'git', 'log', '--oneline', '-10',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
    async def _parse_git_result(self, result: tuple) -> Dict[str, Any]:
        """Parse git command result into metrics dictionary."""
        returncode, stdout, stderr = result
        if returncode == 0:
            return self._format_successful_git_metrics(stdout)
        return await self._get_unknown_git_metrics()
    
    def _format_successful_git_metrics(self, stdout: bytes) -> Dict[str, Any]:
        """Format successful git metrics from stdout."""
        commits = stdout.decode().strip().split('\n')
        return {
            "recent_commits": len(commits),
            "latest_commit": commits[0] if commits else "No commits",
            "repository_health": "healthy"
        }
    
    async def _get_unknown_git_metrics(self) -> Dict[str, Any]:
        """Get git metrics when command fails."""
        return {"recent_commits": 0, "latest_commit": "Unknown", "repository_health": "unknown"}
    
    async def _get_default_git_metrics(self) -> Dict[str, Any]:
        """Get default git metrics when collection fails."""
        return {"recent_commits": 0, "latest_commit": "Error", "repository_health": "error"}


class CodeQualityMetricsCollector:
    """Collects code quality metrics."""
    
    async def collect(self) -> Dict[str, float]:
        """Get code quality metrics."""
        try:
            syntax_score = await self._check_syntax_quality()
            return await self._build_quality_metrics(syntax_score)
        except Exception as e:
            logger.warning(f"Code quality metrics collection failed: {e}")
            return await self._get_default_quality_metrics()
    
    async def _check_syntax_quality(self) -> float:
        """Check syntax quality by compiling main module."""
        result = await self._create_compile_process()
        stdout, stderr = await result.communicate()
        return 1.0 if result.returncode == 0 else 0.0
    
    async def _create_compile_process(self):
        """Create Python compile subprocess."""
        return await asyncio.create_subprocess_exec(
            'python', '-m', 'py_compile', 'app/main.py',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
    async def _build_quality_metrics(self, syntax_score: float) -> Dict[str, float]:
        """Build complete code quality metrics dictionary."""
        return {
            "syntax_score": syntax_score,
            "module_count": await self._count_python_modules(),
            "test_coverage": await self._estimate_test_coverage(),
            "complexity_score": 0.85  # Placeholder - would integrate with real tools
        }
    
    async def _get_default_quality_metrics(self) -> Dict[str, float]:
        """Get default code quality metrics when collection fails."""
        return {"syntax_score": 0.0, "module_count": 0, "test_coverage": 0.0, "complexity_score": 0.0}
    
    async def _count_python_modules(self) -> int:
        """Count Python modules in the project."""
        try:
            result = await self._execute_find_command('*.py')
            return self._parse_find_result(result)
        except Exception:
            return 0
    
    async def _estimate_test_coverage(self) -> float:
        """Estimate test coverage percentage."""
        try:
            test_count = await self._count_files_pattern('**/test_*.py')
            source_count = await self._count_files_pattern('**/*.py')
            return self._calculate_coverage_ratio(test_count, source_count)
        except Exception:
            return 0.0
    
    def _calculate_coverage_ratio(self, test_count: int, source_count: int) -> float:
        """Calculate test coverage ratio from counts."""
        if source_count > 0:
            return min((test_count / source_count) * 100, 100.0)
        return 0.0
    
    async def _count_files_pattern(self, pattern: str) -> int:
        """Count files matching a pattern."""
        try:
            clean_pattern = pattern.replace('**/', '')
            result = await self._execute_find_command(clean_pattern)
            return self._count_non_empty_lines(result)
        except Exception:
            return 0
    
    def _count_non_empty_lines(self, result: tuple) -> int:
        """Count non-empty lines from find command result."""
        returncode, stdout, stderr = result
        if returncode == 0:
            lines = stdout.decode().strip().split('\n')
            return len([line for line in lines if line.strip()])
        return 0
    
    async def _execute_find_command(self, pattern: str) -> tuple:
        """Execute find command for given pattern."""
        result = await self._create_find_process(pattern)
        stdout, stderr = await result.communicate()
        return result.returncode, stdout, stderr
    
    async def _create_find_process(self, pattern: str):
        """Create find command subprocess."""
        return await asyncio.create_subprocess_exec(
            'find', '.', '-name', pattern, '-type', 'f',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
    def _parse_find_result(self, result: tuple) -> int:
        """Parse find command result to count files."""
        returncode, stdout, stderr = result
        if returncode == 0:
            return len(stdout.decode().strip().split('\n'))
        return 0


class PerformanceMetricsCollector:
    """Collects application performance metrics."""
    
    async def collect(self) -> Dict[str, float]:
        """Get application performance metrics."""
        try:
            response_time = await self._measure_response_time()
            return self._calculate_performance_scores(response_time)
        except Exception as e:
            logger.warning(f"Performance metrics collection failed: {e}")
            return await self._get_default_performance_metrics()
    
    async def _measure_response_time(self) -> float:
        """Measure basic response time with simulated work."""
        start_time = datetime.now()
        await asyncio.sleep(0.01)  # Simulate work
        end_time = datetime.now()
        return (end_time - start_time).total_seconds() * 1000
    
    def _calculate_performance_scores(self, response_time: float) -> Dict[str, float]:
        """Calculate performance scores from response time."""
        return {
            "response_time_ms": response_time,
            "throughput_score": min(100.0 / response_time, 100.0),
            "availability": 1.0,
            "error_rate": 0.0
        }
    
    async def _get_default_performance_metrics(self) -> Dict[str, float]:
        """Get default performance metrics when measurement fails."""
        return {"response_time_ms": 1000.0, "throughput_score": 0.0, "availability": 0.0, "error_rate": 1.0}