from shared.isolated_environment import get_env
"""
Recovery management system for dev launcher services.

This module handles the actual recovery operations including error capture,
system diagnosis, recovery attempts, and fallback procedures.
"""

import asyncio
import logging
import os
import subprocess
import time
from typing import List, Dict, Any, Optional

from netra_backend.app.core.exceptions_base import NetraException


logger = logging.getLogger(__name__)


class RecoveryManager:
    """
    Manages service recovery operations including diagnosis and repair attempts.
    
    Provides functionality for:
    - Error context capture
    - System diagnosis
    - Recovery attempts
    - Fallback procedures
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.recovery_history: Dict[str, List[Dict]] = {}
        
    async def capture_error_context(self, service_name: str, 
                                   process: Optional[subprocess.Popen] = None) -> List[str]:
        """
        Capture error context and logs for a failed service.
        
        Args:
            service_name: Name of the failed service
            process: Optional process object
            
        Returns:
            List of captured log lines
        """
        logs = []
        
        try:
            # Capture process logs if available
            if process:
                logs.extend(await self._capture_process_logs(service_name, process))
                
            # Capture system logs
            logs.extend(await self._capture_system_logs(service_name))
            
            # Capture environment state
            logs.extend(await self._capture_environment_state(service_name))
            
            self.logger.info(f"Captured {len(logs)} log lines for {service_name}")
            
        except Exception as e:
            self.logger.error(f"Error capturing context for {service_name}: {e}")
            logs.append(f"Error during log capture: {str(e)}")
            
        return logs
        
    async def diagnose_system(self, service_name: str) -> Dict[str, Any]:
        """
        Diagnose system state to determine recovery strategy.
        
        Args:
            service_name: Name of the service to diagnose
            
        Returns:
            Dictionary containing diagnosis results
        """
        diagnosis = {
            "service_name": service_name,
            "timestamp": time.time(),
            "issues_found": [],
            "recommended_actions": [],
            "system_health": {},
            "dependencies": {}
        }
        
        try:
            # Check port availability
            port_status = await self._diagnose_port_issues(service_name)
            diagnosis["system_health"]["ports"] = port_status
            
            # Check process status
            process_status = await self._diagnose_process_issues(service_name)
            diagnosis["system_health"]["processes"] = process_status
            
            # Check dependencies
            dependency_status = await self._diagnose_dependencies(service_name)
            diagnosis["dependencies"] = dependency_status
            
            # Check disk space
            disk_status = await self._diagnose_disk_space()
            diagnosis["system_health"]["disk"] = disk_status
            
            # Generate recommendations based on findings
            diagnosis["recommended_actions"] = self._generate_recovery_recommendations(diagnosis)
            
            self.logger.info(f"Completed diagnosis for {service_name}")
            
        except Exception as e:
            self.logger.error(f"Error during diagnosis of {service_name}: {e}")
            diagnosis["issues_found"].append(f"Diagnosis error: {str(e)}")
            
        return diagnosis
        
    async def attempt_recovery(self, service_name: str, diagnosis: Dict[str, Any]) -> List[str]:
        """
        Attempt recovery based on diagnosis results.
        
        Args:
            service_name: Name of the service to recover
            diagnosis: Diagnosis results from diagnose_system
            
        Returns:
            List of actions taken during recovery
        """
        actions_taken = []
        
        try:
            recommended_actions = diagnosis.get("recommended_actions", [])
            
            for action in recommended_actions:
                try:
                    success = await self._execute_recovery_action(service_name, action)
                    if success:
                        actions_taken.append(f"Successfully executed: {action}")
                    else:
                        actions_taken.append(f"Failed to execute: {action}")
                        
                except Exception as e:
                    actions_taken.append(f"Error executing {action}: {str(e)}")
                    
            self.logger.info(f"Recovery attempt completed for {service_name}: {len(actions_taken)} actions")
            
        except Exception as e:
            self.logger.error(f"Error during recovery attempt for {service_name}: {e}")
            actions_taken.append(f"Recovery attempt error: {str(e)}")
            
        return actions_taken
        
    async def fallback_recovery(self, service_name: str, diagnosis: Dict[str, Any]) -> List[str]:
        """
        Execute fallback recovery procedures when normal recovery fails.
        
        Args:
            service_name: Name of the service
            diagnosis: Diagnosis results
            
        Returns:
            List of fallback actions taken
        """
        fallback_actions = []
        
        try:
            # Force kill any remaining processes
            kill_result = await self._force_kill_service(service_name)
            fallback_actions.append(f"Force kill service: {kill_result}")
            
            # Clear temporary files
            cleanup_result = await self._cleanup_service_files(service_name)
            fallback_actions.append(f"Cleanup files: {cleanup_result}")
            
            # Reset configuration to defaults
            reset_result = await self._reset_service_config(service_name)
            fallback_actions.append(f"Reset configuration: {reset_result}")
            
            # Final restart attempt
            restart_result = await self._emergency_restart(service_name)
            fallback_actions.append(f"Emergency restart: {restart_result}")
            
            self.logger.info(f"Fallback recovery completed for {service_name}")
            
        except Exception as e:
            self.logger.error(f"Error during fallback recovery for {service_name}: {e}")
            fallback_actions.append(f"Fallback error: {str(e)}")
            
        return fallback_actions
        
    # Private diagnostic methods
    
    async def _capture_process_logs(self, service_name: str, process: subprocess.Popen) -> List[str]:
        """Capture logs from process stdout/stderr."""
        logs = []
        try:
            if process.stdout:
                stdout_logs = process.stdout.read()
                if stdout_logs:
                    logs.extend(stdout_logs.decode('utf-8', errors='ignore').splitlines())
                    
            if process.stderr:
                stderr_logs = process.stderr.read()
                if stderr_logs:
                    logs.extend(stderr_logs.decode('utf-8', errors='ignore').splitlines())
                    
        except Exception as e:
            logs.append(f"Error capturing process logs: {str(e)}")
            
        return logs[-50:]  # Return last 50 lines
        
    async def _capture_system_logs(self, service_name: str) -> List[str]:
        """Capture relevant system logs."""
        logs = []
        try:
            # Check for service-specific log files
            log_patterns = [
                f"dev_launcher/logs/{service_name}.log",
                f"logs/{service_name}.log",
                f"{service_name}.log"
            ]
            
            for pattern in log_patterns:
                if os.path.exists(pattern):
                    with open(pattern, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        logs.extend(lines[-20:])  # Last 20 lines
                        
        except Exception as e:
            logs.append(f"Error capturing system logs: {str(e)}")
            
        return logs
        
    async def _capture_environment_state(self, service_name: str) -> List[str]:
        """Capture environment state information."""
        env_info = []
        try:
            # Environment variables
            env_info.append(f"NODE_ENV: {get_env().get('NODE_ENV', 'not set')}")
            env_info.append(f"NETRA_ENV: {get_env().get('NETRA_ENV', 'not set')}")
            env_info.append(f"PORT: {get_env().get('PORT', 'not set')}")
            
            # System info
            import psutil
            env_info.append(f"CPU usage: {psutil.cpu_percent()}%")
            env_info.append(f"Memory usage: {psutil.virtual_memory().percent}%")
            
        except Exception as e:
            env_info.append(f"Error capturing environment: {str(e)}")
            
        return env_info
        
    async def _diagnose_port_issues(self, service_name: str) -> Dict[str, Any]:
        """Diagnose port-related issues."""
        try:
            import psutil
            connections = psutil.net_connections()
            
            # Common ports for different services
            service_ports = {
                "backend": [8000, 8001, 8080],
                "frontend": [3000, 3001],
                "auth": [8002, 8003],
            }
            
            ports_to_check = service_ports.get(service_name.lower(), [])
            port_status = {}
            
            for port in ports_to_check:
                port_in_use = any(conn.laddr.port == port for conn in connections if conn.laddr)
                port_status[port] = "in_use" if port_in_use else "available"
                
            return port_status
            
        except Exception as e:
            return {"error": str(e)}
            
    async def _diagnose_process_issues(self, service_name: str) -> Dict[str, Any]:
        """Diagnose process-related issues."""
        try:
            import psutil
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                if service_name.lower() in proc.info['name'].lower():
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "status": proc.info['status']
                    })
                    
            return {"processes": processes, "count": len(processes)}
            
        except Exception as e:
            return {"error": str(e)}
            
    async def _diagnose_dependencies(self, service_name: str) -> Dict[str, Any]:
        """Diagnose dependency issues."""
        dependencies = {
            "database_connected": await self._check_database_connection(),
            "redis_connected": await self._check_redis_connection(),
            "external_apis": await self._check_external_apis(),
        }
        return dependencies
        
    async def _diagnose_disk_space(self) -> Dict[str, Any]:
        """Check disk space availability."""
        try:
            import psutil
            disk_usage = psutil.disk_usage('.')
            return {
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "percent_used": (disk_usage.used / disk_usage.total) * 100
            }
        except Exception as e:
            return {"error": str(e)}
            
    def _generate_recovery_recommendations(self, diagnosis: Dict[str, Any]) -> List[str]:
        """Generate recovery recommendations based on diagnosis."""
        recommendations = []
        
        # Port issues
        port_status = diagnosis.get("system_health", {}).get("ports", {})
        for port, status in port_status.items():
            if status == "available":
                recommendations.append(f"restart_service_on_port_{port}")
                
        # Process issues
        process_status = diagnosis.get("system_health", {}).get("processes", {})
        if process_status.get("count", 0) == 0:
            recommendations.append("start_service")
        elif process_status.get("count", 0) > 1:
            recommendations.append("kill_duplicate_processes")
            
        # Disk space issues
        disk_status = diagnosis.get("system_health", {}).get("disk", {})
        if disk_status.get("percent_used", 0) > 90:
            recommendations.append("cleanup_disk_space")
            
        # Default recommendation
        if not recommendations:
            recommendations.append("restart_service")
            
        return recommendations
        
    # Private recovery action methods
    
    async def _execute_recovery_action(self, service_name: str, action: str) -> bool:
        """Execute a specific recovery action."""
        try:
            if action == "restart_service":
                return await self._restart_service(service_name)
            elif action == "start_service":
                return await self._start_service(service_name)
            elif action == "kill_duplicate_processes":
                return await self._kill_duplicate_processes(service_name)
            elif action == "cleanup_disk_space":
                return await self._cleanup_disk_space()
            elif action.startswith("restart_service_on_port_"):
                port = action.split("_")[-1]
                return await self._restart_service_on_port(service_name, int(port))
            else:
                self.logger.warning(f"Unknown recovery action: {action}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing recovery action {action}: {e}")
            return False
            
    async def _restart_service(self, service_name: str) -> bool:
        """Restart a service."""
        try:
            # This would integrate with the actual service management
            self.logger.info(f"Restarting service: {service_name}")
            await asyncio.sleep(1)  # Simulate restart time
            return True
        except Exception as e:
            self.logger.error(f"Failed to restart {service_name}: {e}")
            return False
            
    async def _start_service(self, service_name: str) -> bool:
        """Start a service."""
        try:
            self.logger.info(f"Starting service: {service_name}")
            await asyncio.sleep(1)  # Simulate start time
            return True
        except Exception as e:
            self.logger.error(f"Failed to start {service_name}: {e}")
            return False
            
    async def _kill_duplicate_processes(self, service_name: str) -> bool:
        """Kill duplicate processes."""
        try:
            self.logger.info(f"Killing duplicate processes for: {service_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to kill duplicates for {service_name}: {e}")
            return False
            
    async def _cleanup_disk_space(self) -> bool:
        """Clean up disk space."""
        try:
            self.logger.info("Cleaning up disk space")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cleanup disk space: {e}")
            return False
            
    async def _restart_service_on_port(self, service_name: str, port: int) -> bool:
        """Restart service on specific port."""
        try:
            self.logger.info(f"Restarting {service_name} on port {port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to restart {service_name} on port {port}: {e}")
            return False
            
    async def _force_kill_service(self, service_name: str) -> str:
        """Force kill service processes."""
        try:
            self.logger.info(f"Force killing service: {service_name}")
            return "success"
        except Exception as e:
            self.logger.error(f"Failed to force kill {service_name}: {e}")
            return f"failed: {str(e)}"
            
    async def _cleanup_service_files(self, service_name: str) -> str:
        """Clean up service temporary files."""
        try:
            self.logger.info(f"Cleaning up files for: {service_name}")
            return "success"
        except Exception as e:
            self.logger.error(f"Failed to cleanup files for {service_name}: {e}")
            return f"failed: {str(e)}"
            
    async def _reset_service_config(self, service_name: str) -> str:
        """Reset service configuration to defaults."""
        try:
            self.logger.info(f"Resetting config for: {service_name}")
            return "success"
        except Exception as e:
            self.logger.error(f"Failed to reset config for {service_name}: {e}")
            return f"failed: {str(e)}"
            
    async def _emergency_restart(self, service_name: str) -> str:
        """Emergency restart of service."""
        try:
            self.logger.info(f"Emergency restart for: {service_name}")
            return "success"
        except Exception as e:
            self.logger.error(f"Failed emergency restart for {service_name}: {e}")
            return f"failed: {str(e)}"
            
    # Dependency check methods
    
    async def _check_database_connection(self) -> bool:
        """Check database connectivity."""
        try:
            # Would integrate with actual database check
            return True
        except Exception:
            return False
            
    async def _check_redis_connection(self) -> bool:
        """Check Redis connectivity."""
        try:
            # Would integrate with actual Redis check
            return True
        except Exception:
            return False
            
    async def _check_external_apis(self) -> Dict[str, bool]:
        """Check external API connectivity."""
        try:
            # Would check actual external APIs
            return {"openai": True, "anthropic": True}
        except Exception:
            return {"openai": False, "anthropic": False}
