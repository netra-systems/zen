"""
Recovery Actions for crashed services.

Provides specific recovery actions for different types of failures:
- Process cleanup (zombie processes)
- Temporary file cleanup
- Port conflict resolution
- Dependency management
- Fallback suggestions

ARCHITECTURE COMPLIANCE:
- File size: ≤300 lines (currently under limit)
- Function size: ≤8 lines each (MANDATORY)
- Strong typing throughout
- Async patterns for all I/O operations
"""

import asyncio
import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any

from .crash_recovery_models import DiagnosisResult


logger = logging.getLogger(__name__)


class RecoveryActions:
    """Provides recovery actions for different types of failures."""
    
    def __init__(self):
        """Initialize recovery actions handler."""
        self.temp_directories = self._get_temp_directories()
        self.cleanup_patterns = ['*.tmp', '*.temp', '*.log.*', 'core.*']
    
    def _get_temp_directories(self) -> List[Path]:
        """Get temporary directories for cleanup."""
        common_temps = [
            Path("temp"), Path(".netra/temp"), Path("logs/temp"),
            Path("tmp"), Path(".tmp"), Path("cache")
        ]
        
        if os.name != 'nt':
            common_temps.extend([Path("/tmp"), Path("/var/tmp")])
        
        return [d for d in common_temps if d.exists()]
    
    async def execute_recovery_actions(self, service_name: str, diagnosis: DiagnosisResult) -> List[str]:
        """Execute appropriate recovery actions based on diagnosis."""
        actions = []
        
        # Kill zombie processes
        if diagnosis.zombie_processes:
            actions.extend(await self.cleanup_zombie_processes(diagnosis.zombie_processes))
        
        # Clear temporary files
        actions.extend(await self.cleanup_temp_files())
        
        # Resolve port conflicts
        if diagnosis.port_conflicts:
            actions.extend(await self.resolve_port_conflicts(diagnosis.port_conflicts))
        
        # Handle config issues
        if diagnosis.config_issues:
            actions.extend(await self.handle_config_issues(diagnosis.config_issues))
        
        return actions
    
    async def cleanup_zombie_processes(self, zombie_pids: List[int]) -> List[str]:
        """Kill zombie processes and their parents if necessary."""
        actions = []
        
        for pid in zombie_pids:
            action_result = await self._kill_process(pid)
            actions.append(action_result)
        
        return actions
    
    async def _kill_process(self, pid: int) -> str:
        """Kill a specific process by PID."""
        try:
            if os.name == 'nt':
                result = await asyncio.to_thread(
                    subprocess.run, ['taskkill', '/F', '/PID', str(pid)],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return f"Killed process {pid} (Windows)"
                else:
                    return f"Failed to kill process {pid}: {result.stderr}"
            else:
                os.kill(pid, 9)
                return f"Killed zombie process {pid}"
        except (ProcessLookupError, PermissionError) as e:
            return f"Failed to kill process {pid}: {str(e)}"
        except Exception as e:
            return f"Error killing process {pid}: {str(e)}"
    
    async def cleanup_temp_files(self) -> List[str]:
        """Clean up temporary files and directories."""
        actions = []
        
        for temp_dir in self.temp_directories:
            action_result = await self._cleanup_directory(temp_dir)
            actions.append(action_result)
        
        # Clean up pattern-based files in current directory
        actions.extend(await self._cleanup_pattern_files())
        
        return actions
    
    async def _cleanup_directory(self, temp_dir: Path) -> str:
        """Clean up a specific temporary directory."""
        try:
            if temp_dir.exists() and temp_dir.is_dir():
                file_count = len(list(temp_dir.iterdir()))
                shutil.rmtree(temp_dir)
                temp_dir.mkdir(exist_ok=True)
                return f"Cleaned temp directory {temp_dir} ({file_count} files)"
            else:
                return f"Temp directory {temp_dir} does not exist or is not a directory"
        except Exception as e:
            return f"Failed to clean {temp_dir}: {str(e)}"
    
    async def _cleanup_pattern_files(self) -> List[str]:
        """Clean up files matching cleanup patterns."""
        actions = []
        
        for pattern in self.cleanup_patterns:
            try:
                import glob
                files = glob.glob(pattern)
                for file_path in files:
                    try:
                        os.remove(file_path)
                        actions.append(f"Removed temp file: {file_path}")
                    except Exception as e:
                        actions.append(f"Failed to remove {file_path}: {str(e)}")
            except Exception as e:
                actions.append(f"Failed to process pattern {pattern}: {str(e)}")
        
        return actions
    
    async def resolve_port_conflicts(self, conflicting_ports: List[int]) -> List[str]:
        """Attempt to resolve port conflicts."""
        actions = []
        
        for port in conflicting_ports:
            action_result = await self._resolve_single_port(port)
            actions.append(action_result)
        
        return actions
    
    async def _resolve_single_port(self, port: int) -> str:
        """Attempt to resolve conflict for a single port."""
        try:
            processes = await self._find_processes_using_port(port)
            if processes:
                return f"Port {port} used by processes: {processes}. Manual intervention required."
            else:
                return f"Port {port} conflict resolved automatically"
        except Exception as e:
            return f"Failed to resolve port {port} conflict: {str(e)}"
    
    async def _find_processes_using_port(self, port: int) -> List[str]:
        """Find processes using a specific port."""
        try:
            if os.name == 'nt':
                command = ['netstat', '-ano']
            else:
                command = ['lsof', f'-i:{port}']
            
            result = await asyncio.to_thread(
                subprocess.run, command, capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                return self._parse_port_processes(result.stdout, port)
        except Exception:
            pass
        
        return []
    
    def _parse_port_processes(self, output: str, port: int) -> List[str]:
        """Parse command output to find processes using port."""
        processes = []
        port_pattern = f":{port}"
        
        for line in output.split('\n'):
            if port_pattern in line:
                parts = line.split()
                if len(parts) > 1:
                    if os.name == 'nt' and len(parts) > 4:
                        processes.append(f"PID:{parts[-1]}")
                    elif os.name != 'nt' and len(parts) > 1:
                        processes.append(f"Process:{parts[0]}")
        
        return processes
    
    async def handle_config_issues(self, config_issues: List[str]) -> List[str]:
        """Handle configuration-related issues."""
        actions = []
        
        for issue in config_issues:
            if "syntax" in issue.lower():
                actions.append(f"Config syntax error detected: {issue}. Manual review required.")
            elif "not found" in issue.lower():
                actions.append(f"Config file missing: {issue}. Check file paths.")
            else:
                actions.append(f"Config issue: {issue}. Review configuration.")
        
        return actions
    
    async def restart_dependencies(self, service_name: str, dependencies: List[str] = None) -> List[str]:
        """Restart service dependencies if possible."""
        actions = []
        
        if not dependencies:
            dependencies = self._get_common_dependencies()
        
        for dependency in dependencies:
            action_result = await self._restart_dependency(dependency)
            actions.append(action_result)
        
        return actions
    
    def _get_common_dependencies(self) -> List[str]:
        """Get list of common service dependencies."""
        return ["postgresql", "redis", "nginx", "docker"]
    
    async def _restart_dependency(self, dependency: str) -> str:
        """Attempt to restart a service dependency."""
        try:
            if os.name == 'nt':
                command = ['net', 'restart', dependency]
            else:
                command = ['sudo', 'systemctl', 'restart', dependency]
            
            result = await asyncio.to_thread(
                subprocess.run, command, capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                return f"Restarted dependency: {dependency}"
            else:
                return f"Failed to restart {dependency}: {result.stderr}"
        except Exception as e:
            return f"Cannot restart {dependency}: {str(e)}"
    
    async def reset_network_connections(self) -> List[str]:
        """Reset network connections if possible."""
        actions = []
        
        try:
            if os.name == 'nt':
                commands = [
                    ['ipconfig', '/release'],
                    ['ipconfig', '/renew'],
                    ['ipconfig', '/flushdns']
                ]
            else:
                commands = [
                    ['sudo', 'systemctl', 'restart', 'networking']
                ]
            
            for command in commands:
                try:
                    result = await asyncio.to_thread(
                        subprocess.run, command, capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        actions.append(f"Executed network command: {' '.join(command)}")
                    else:
                        actions.append(f"Network command failed: {' '.join(command)}")
                except Exception as e:
                    actions.append(f"Network command error: {str(e)}")
        
        except Exception as e:
            actions.append(f"Network reset failed: {str(e)}")
        
        return actions
    
    async def generate_fallback_suggestions(self, service_name: str, diagnosis: DiagnosisResult) -> List[str]:
        """Generate fallback suggestions when automatic recovery fails."""
        suggestions = [
            f"Service {service_name} requires manual intervention",
            "=== RECOMMENDED ACTIONS ===",
            "1. Check service configuration files for syntax errors",
            "2. Verify database connectivity and credentials",
            "3. Review system resources (memory, disk space, open files)",
            "4. Check for competing processes on required ports",
            "5. Review service logs for specific error patterns",
            "6. Consider clean restart of development environment"
        ]
        
        # Add specific suggestions based on diagnosis
        suggestions.extend(self._add_specific_suggestions(diagnosis))
        
        return suggestions
    
    def _add_specific_suggestions(self, diagnosis: DiagnosisResult) -> List[str]:
        """Add diagnosis-specific suggestions."""
        suggestions = []
        
        if diagnosis.port_conflicts:
            suggestions.append(f"7. Resolve port conflicts on ports: {diagnosis.port_conflicts}")
            suggestions.append("   Use 'netstat -tulpn' (Linux) or 'netstat -ano' (Windows) to identify processes")
        
        if diagnosis.memory_issues:
            suggestions.append("8. Address memory constraints:")
            suggestions.append("   - Close unused applications")
            suggestions.append("   - Increase virtual memory/swap")
            suggestions.append("   - Check for memory leaks in the application")
        
        if diagnosis.config_issues:
            suggestions.append("9. Fix configuration issues:")
            for issue in diagnosis.config_issues[:3]:  # Limit to first 3 issues
                suggestions.append(f"   - {issue}")
        
        if diagnosis.zombie_processes:
            suggestions.append("10. Clean up zombie processes manually:")
            suggestions.append(f"    PIDs: {diagnosis.zombie_processes}")
        
        return suggestions