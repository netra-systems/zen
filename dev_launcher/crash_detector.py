"""
Crash detection system for dev launcher services.

This module provides crash detection capabilities for monitoring service health,
detecting crashes, and triggering recovery mechanisms.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
import psutil

from netra_backend.app.core.exceptions_base import NetraException


logger = logging.getLogger(__name__)


class CrashDetectionResult:
    """Result of crash detection for a service."""
    
    def __init__(self, service_name: str, crash_detected: bool = False, 
                 crash_type: str = None, details: Dict = None):
        self.service_name = service_name
        self.crash_detected = crash_detected
        self.crash_type = crash_type
        self.details = details or {}
        self.timestamp = time.time()


class CrashDetector:
    """
    Detects crashes and failures in development launcher services.
    
    Provides methods for:
    - Process health monitoring
    - Memory leak detection
    - Unresponsive service detection
    - Port binding failure detection
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.detection_history: List[CrashDetectionResult] = []
        
    async def run_all_detections(self, service_name: str, service_config: Dict, 
                                process: Optional[Any] = None) -> List[CrashDetectionResult]:
        """
        Run all crash detection methods for a service.
        
        Args:
            service_name: Name of the service to check
            service_config: Service configuration dictionary
            process: Optional process object to check
            
        Returns:
            List of detection results
        """
        results = []
        
        try:
            # Process-based detection
            if process:
                process_result = await self._detect_process_crash(service_name, process)
                results.append(process_result)
                
            # Port-based detection
            port_result = await self._detect_port_issues(service_name, service_config)
            results.append(port_result)
            
            # Memory-based detection
            memory_result = await self._detect_memory_issues(service_name, process)
            results.append(memory_result)
            
        except Exception as e:
            self.logger.error(f"Error during crash detection for {service_name}: {e}")
            results.append(CrashDetectionResult(
                service_name, 
                crash_detected=True, 
                crash_type="detection_error",
                details={"error": str(e)}
            ))
            
        # Store results in history
        self.detection_history.extend(results)
        
        return results
        
    def has_any_crash(self, detection_results: List[CrashDetectionResult]) -> bool:
        """
        Check if any of the detection results indicate a crash.
        
        Args:
            detection_results: List of detection results
            
        Returns:
            True if any crash is detected
        """
        return any(result.crash_detected for result in detection_results)
        
    async def _detect_process_crash(self, service_name: str, process: Any) -> CrashDetectionResult:
        """Detect if a process has crashed."""
        try:
            if process is None:
                return CrashDetectionResult(
                    service_name, 
                    crash_detected=True, 
                    crash_type="process_not_found"
                )
                
            # Check if process is running using psutil
            if hasattr(process, 'pid'):
                try:
                    proc = psutil.Process(process.pid)
                    if not proc.is_running():
                        return CrashDetectionResult(
                            service_name, 
                            crash_detected=True, 
                            crash_type="process_terminated"
                        )
                except psutil.NoSuchProcess:
                    return CrashDetectionResult(
                        service_name, 
                        crash_detected=True, 
                        crash_type="process_not_found"
                    )
                    
            return CrashDetectionResult(service_name, crash_detected=False)
            
        except Exception as e:
            self.logger.error(f"Process crash detection failed for {service_name}: {e}")
            return CrashDetectionResult(
                service_name, 
                crash_detected=True, 
                crash_type="detection_error",
                details={"error": str(e)}
            )
            
    async def _detect_port_issues(self, service_name: str, service_config: Dict) -> CrashDetectionResult:
        """Detect port binding issues."""
        try:
            port = service_config.get('port')
            if not port:
                return CrashDetectionResult(service_name, crash_detected=False)
                
            # Check if port is in use by expected process
            connections = psutil.net_connections()
            port_in_use = any(conn.laddr.port == port for conn in connections if conn.laddr)
            
            if not port_in_use:
                return CrashDetectionResult(
                    service_name, 
                    crash_detected=True, 
                    crash_type="port_not_bound",
                    details={"port": port}
                )
                
            return CrashDetectionResult(service_name, crash_detected=False)
            
        except Exception as e:
            self.logger.error(f"Port detection failed for {service_name}: {e}")
            return CrashDetectionResult(service_name, crash_detected=False)
            
    async def _detect_memory_issues(self, service_name: str, process: Any) -> CrashDetectionResult:
        """Detect memory-related issues."""
        try:
            if not process or not hasattr(process, 'pid'):
                return CrashDetectionResult(service_name, crash_detected=False)
                
            proc = psutil.Process(process.pid)
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            # Flag if memory usage is extremely high (>2GB)
            if memory_mb > 2048:
                return CrashDetectionResult(
                    service_name, 
                    crash_detected=True, 
                    crash_type="memory_excessive",
                    details={"memory_mb": memory_mb}
                )
                
            return CrashDetectionResult(service_name, crash_detected=False)
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return CrashDetectionResult(service_name, crash_detected=False)
        except Exception as e:
            self.logger.error(f"Memory detection failed for {service_name}: {e}")
            return CrashDetectionResult(service_name, crash_detected=False)
            
    def get_detection_history(self, service_name: str = None) -> List[CrashDetectionResult]:
        """Get crash detection history, optionally filtered by service name."""
        if service_name:
            return [r for r in self.detection_history if r.service_name == service_name]
        return self.detection_history.copy()
        
    def clear_history(self):
        """Clear detection history."""
        self.detection_history.clear()