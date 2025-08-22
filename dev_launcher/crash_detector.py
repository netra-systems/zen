"""
Crash Detection Module for Netra Development Services.

Provides multiple crash detection methods:
- Process monitoring via Process.poll() 
- Health endpoint checks with HTTP requests
- Log pattern analysis for FATAL/CRITICAL patterns

ARCHITECTURE COMPLIANCE:
- File size: ≤300 lines (currently under limit)
- Function size: ≤8 lines each (MANDATORY)
- Strong typing throughout
- Async patterns for all I/O operations
"""

import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import List, Optional

import requests

from dev_launcher.crash_recovery_models import DetectionMethod, DetectionResult

logger = logging.getLogger(__name__)


class CrashDetector:
    """Detects service crashes using multiple methods."""
    
    def __init__(self):
        """Initialize crash detector with fatal log patterns."""
        self.fatal_patterns = self._build_fatal_patterns()
    
    def _build_fatal_patterns(self) -> List[str]:
        """Build list of fatal error patterns for log analysis."""
        return [
            r"FATAL", r"CRITICAL ERROR", r"SEGMENTATION FAULT",
            r"OUT OF MEMORY", r"STACK OVERFLOW", r"ACCESS VIOLATION",
            r"ASSERTION FAILED", r"PANIC", r"ABORT"
        ]
    
    async def detect_process_crash(self, process: subprocess.Popen, name: str) -> DetectionResult:
        """Check if process has crashed via polling."""
        poll_result = process.poll()
        is_crashed = poll_result is not None
        error_msg = self._format_process_error(name, poll_result) if is_crashed else None
        metadata = {"pid": process.pid, "returncode": poll_result}
        return DetectionResult(
            method=DetectionMethod.PROCESS_MONITORING, is_crashed=is_crashed,
            error_message=error_msg, metadata=metadata
        )
    
    def _format_process_error(self, name: str, returncode: int) -> str:
        """Format process error message with return code."""
        if returncode == 0:
            return f"Process {name} exited normally"
        elif returncode > 0:
            return f"Process {name} exited with error code {returncode}"
        else:
            return f"Process {name} terminated by signal {-returncode}"
    
    async def detect_health_crash(self, url: str, timeout: int = 5) -> DetectionResult:
        """Check service health via HTTP endpoint."""
        try:
            response = await self._make_health_request(url, timeout)
            is_crashed = response.status_code != 200
            error_msg = f"Health check failed: HTTP {response.status_code}" if is_crashed else None
            metadata = {"status_code": response.status_code, "url": url}
        except Exception as e:
            is_crashed, error_msg = True, f"Health check exception: {str(e)}"
            metadata = {"url": url, "exception": str(e)}
        
        return DetectionResult(
            method=DetectionMethod.HEALTH_ENDPOINT, is_crashed=is_crashed,
            error_message=error_msg, metadata=metadata
        )
    
    async def _make_health_request(self, url: str, timeout: int):
        """Make HTTP health check request asynchronously."""
        return await asyncio.to_thread(requests.get, url, timeout=timeout)
    
    async def detect_log_crash(self, log_file: Path, lines_to_check: int = 50) -> DetectionResult:
        """Analyze logs for crash patterns."""
        if not log_file.exists():
            return self._create_log_not_found_result()
        
        try:
            last_lines = await self._get_last_log_lines(log_file, lines_to_check)
            crash_found, matching_pattern = self._scan_for_fatal_patterns(last_lines)
            error_msg = f"Fatal pattern detected: {matching_pattern}" if crash_found else None
            metadata = {"log_file": str(log_file), "lines_scanned": len(last_lines)}
        except Exception as e:
            crash_found, error_msg = False, f"Log analysis failed: {str(e)}"
            metadata = {"log_file": str(log_file), "error": str(e)}
        
        return DetectionResult(
            method=DetectionMethod.LOG_ANALYSIS, is_crashed=crash_found,
            error_message=error_msg, metadata=metadata
        )
    
    def _create_log_not_found_result(self) -> DetectionResult:
        """Create result for missing log file."""
        return DetectionResult(
            method=DetectionMethod.LOG_ANALYSIS, is_crashed=False,
            error_message="Log file not found", metadata={"log_exists": False}
        )
    
    async def _get_last_log_lines(self, log_file: Path, count: int) -> List[str]:
        """Get last N lines from log file asynchronously."""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                return lines[-count:] if len(lines) > count else lines
        except Exception as e:
            logger.warning(f"Failed to read log file {log_file}: {e}")
            return []
    
    def _scan_for_fatal_patterns(self, log_lines: List[str]) -> tuple[bool, Optional[str]]:
        """Scan log lines for fatal patterns."""
        for line in log_lines:
            for pattern in self.fatal_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return True, pattern
        return False, None
    
    async def run_all_detections(self, service_name: str, config: dict,
                               process: Optional[subprocess.Popen]) -> List[DetectionResult]:
        """Run all detection methods for a service."""
        results = []
        
        # Process monitoring
        if process:
            process_result = await self.detect_process_crash(process, service_name)
            results.append(process_result)
        
        # Health endpoint check
        if config.get('health_url'):
            health_result = await self.detect_health_crash(config['health_url'])
            results.append(health_result)
        
        # Log analysis
        log_file = self._get_log_file_path(service_name, config)
        log_result = await self.detect_log_crash(log_file)
        results.append(log_result)
        
        return results
    
    def _get_log_file_path(self, service_name: str, config: dict) -> Path:
        """Get log file path for service."""
        if config.get('log_file'):
            return Path(config['log_file'])
        return Path(f"dev_launcher/logs/{service_name}.log")
    
    def has_any_crash(self, detection_results: List[DetectionResult]) -> bool:
        """Check if any detection result indicates a crash."""
        return any(result.is_crashed for result in detection_results)
    
    def get_crash_summary(self, detection_results: List[DetectionResult]) -> str:
        """Get summary of crash detection results."""
        crashed_methods = [
            result.method.value for result in detection_results if result.is_crashed
        ]
        if not crashed_methods:
            return "No crashes detected"
        return f"Crashes detected via: {', '.join(crashed_methods)}"