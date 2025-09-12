"""
Critical Failure Reproduction Helpers

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable accurate reproduction of P1 critical failures
- Value Impact: Ensure fixes address root causes, not symptoms
- Strategic Impact: Platform reliability - prevent regression of $120K+ MRR critical functionality

MISSION: Provide comprehensive platform detection, error logging, and debugging
utilities specifically designed for reproducing critical failures identified
in staging deployment testing.

This module supports reproduction tests that must FAIL before fixes are applied
to validate that remediation actually resolves the underlying issues.
"""

import platform
import asyncio
import time
import json
import traceback
import threading
import psutil
import sys
import os
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timezone
from dataclasses import dataclass
from contextlib import contextmanager
import logging


@dataclass 
class PlatformInfo:
    """Comprehensive platform information for failure reproduction"""
    system: str
    version: str
    architecture: tuple
    processor: str
    python_version: str
    is_windows: bool
    is_linux: bool
    is_macos: bool
    asyncio_loop_type: Optional[str] = None
    thread_id: Optional[int] = None
    process_id: Optional[int] = None
    
    @classmethod
    def detect(cls) -> 'PlatformInfo':
        """Detect current platform information"""
        system = platform.system()
        
        info = cls(
            system=system,
            version=platform.version(),
            architecture=platform.architecture(),
            processor=platform.processor(),
            python_version=platform.python_version(),
            is_windows=system.lower() == "windows",
            is_linux=system.lower() == "linux", 
            is_macos=system.lower() == "darwin",
            thread_id=threading.get_ident(),
            process_id=os.getpid()
        )
        
        # Detect asyncio loop type if available
        try:
            loop = asyncio.get_running_loop()
            info.asyncio_loop_type = type(loop).__name__
        except RuntimeError:
            # No running loop
            info.asyncio_loop_type = None
            
        return info
    
    def is_windows_iocp(self) -> bool:
        """Check if running Windows with IOCP event loop (deadlock-prone)"""
        return (
            self.is_windows and 
            self.asyncio_loop_type and
            "Windows" in self.asyncio_loop_type
        )
    
    def supports_concurrent_asyncio(self) -> bool:
        """Check if platform supports reliable concurrent asyncio operations"""
        # Windows IOCP has known limitations with concurrent operations
        return not self.is_windows_iocp()


@dataclass
class FailureReproductionContext:
    """Context information for failure reproduction attempts"""
    test_name: str
    expected_failure_type: str
    platform_info: PlatformInfo
    start_time: float
    timeout_seconds: int
    reproduction_successful: bool = False
    actual_failure_type: Optional[str] = None
    failure_details: Dict[str, Any] = None
    progress_markers: List[Dict[str, Any]] = None
    error_messages: List[str] = None
    
    def __post_init__(self):
        if self.failure_details is None:
            self.failure_details = {}
        if self.progress_markers is None:
            self.progress_markers = []
        if self.error_messages is None:
            self.error_messages = []
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since reproduction started"""
        return time.time() - self.start_time
    
    def mark_progress(self, stage: str, details: Optional[Dict[str, Any]] = None):
        """Mark progress through reproduction attempt"""
        marker = {
            "stage": stage,
            "timestamp": time.time(),
            "elapsed": self.elapsed_time,
            "details": details or {}
        }
        self.progress_markers.append(marker)
    
    def record_error(self, error: Union[str, Exception], context: Optional[str] = None):
        """Record error encountered during reproduction"""
        if isinstance(error, Exception):
            error_msg = f"{type(error).__name__}: {str(error)}"
        else:
            error_msg = str(error)
            
        if context:
            error_msg = f"[{context}] {error_msg}"
            
        self.error_messages.append({
            "message": error_msg,
            "timestamp": time.time(),
            "elapsed": self.elapsed_time
        })
    
    def analyze_reproduction_success(self) -> bool:
        """
        Analyze if reproduction was successful based on expected vs actual failure
        
        For reproduction tests, "success" means reproducing the expected failure.
        """
        if self.actual_failure_type is None:
            return False
            
        # Check if actual failure matches expected failure pattern
        if self.expected_failure_type.lower() in self.actual_failure_type.lower():
            self.reproduction_successful = True
            return True
            
        return False


class CriticalFailureReproducer:
    """
    Manager for reproducing critical failures with comprehensive logging
    
    This class provides structured failure reproduction with detailed
    platform detection, progress tracking, and error analysis.
    """
    
    def __init__(self, test_name: str, expected_failure: str, timeout: int = 300):
        self.context = FailureReproductionContext(
            test_name=test_name,
            expected_failure_type=expected_failure,
            platform_info=PlatformInfo.detect(),
            start_time=time.time(),
            timeout_seconds=timeout
        )
        
        # Configure logging for reproduction
        self.logger = logging.getLogger(f"reproduction.{test_name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    async def __aenter__(self):
        self.logger.info(f" SEARCH:  Starting reproduction of {self.context.expected_failure_type}")
        self.logger.info(f" SEARCH:  Platform: {self.context.platform_info.system} {self.context.platform_info.version}")
        self.logger.info(f" SEARCH:  Asyncio: {self.context.platform_info.asyncio_loop_type}")
        self.logger.info(f" SEARCH:  Windows IOCP: {self.context.platform_info.is_windows_iocp()}")
        
        self.context.mark_progress("reproduction_started", {
            "platform": self.context.platform_info.system,
            "asyncio_loop": self.context.platform_info.asyncio_loop_type
        })
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is asyncio.TimeoutError:
            self.context.actual_failure_type = "asyncio_timeout"
            self.context.failure_details = {
                "timeout_reached": True,
                "duration": self.context.elapsed_time,
                "progress_markers": len(self.context.progress_markers),
                "platform": self.context.platform_info.system
            }
            self.logger.info(" PASS:  Timeout occurred - analyzing reproduction success...")
            
        elif exc_type is not None:
            self.context.actual_failure_type = exc_type.__name__
            self.context.failure_details = {
                "exception": str(exc_val),
                "traceback": traceback.format_exc(),
                "duration": self.context.elapsed_time
            }
            self.logger.info(f" SEARCH:  Exception occurred: {exc_type.__name__}")
            
        self._log_reproduction_analysis()
    
    def mark_progress(self, stage: str, details: Optional[Dict[str, Any]] = None):
        """Mark progress through reproduction attempt"""
        self.context.mark_progress(stage, details)
        self.logger.info(f" SEARCH:  Progress: {stage} (elapsed: {self.context.elapsed_time:.1f}s)")
    
    def record_error(self, error: Union[str, Exception], context: Optional[str] = None):
        """Record error encountered during reproduction"""
        self.context.record_error(error, context)
        if isinstance(error, Exception):
            self.logger.error(f" FAIL:  Error in {context or 'reproduction'}: {error}")
        else:
            self.logger.error(f" FAIL:  {context or 'Error'}: {error}")
    
    def is_windows_deadlock_pattern(self) -> bool:
        """
        Check if failure pattern matches Windows asyncio deadlock
        
        SESSION5 indicators:
        - Long timeout (300s)
        - Windows platform with IOCP
        - Minimal progress (stuck at event loop level)
        """
        if not self.context.platform_info.is_windows_iocp():
            return False
            
        if self.context.actual_failure_type != "asyncio_timeout":
            return False
            
        duration = self.context.elapsed_time
        progress_count = len(self.context.progress_markers)
        
        # SESSION5 pattern: ~300s timeout with very limited progress
        return duration >= 290 and progress_count <= 5
    
    def is_sessionmiddleware_pattern(self) -> bool:
        """
        Check if failure pattern matches SessionMiddleware error
        
        SESSION5 indicators:
        - WebSocket 1011 internal error
        - Connection established but processing fails
        - "SessionMiddleware must be installed" error
        """
        if self.context.actual_failure_type and "connection" in self.context.actual_failure_type.lower():
            error_messages = " ".join(str(msg) for msg in self.context.error_messages)
            return any(phrase in error_messages.lower() for phrase in [
                "1011", "internal error", "sessionmiddleware", "session middleware"
            ])
        return False
    
    def _log_reproduction_analysis(self):
        """Log comprehensive analysis of reproduction attempt"""
        self.logger.info("\n" + "="*50)
        self.logger.info("CRITICAL FAILURE REPRODUCTION ANALYSIS")
        self.logger.info("="*50)
        
        self.logger.info(f"Test: {self.context.test_name}")
        self.logger.info(f"Expected failure: {self.context.expected_failure_type}")
        self.logger.info(f"Actual failure: {self.context.actual_failure_type}")
        self.logger.info(f"Duration: {self.context.elapsed_time:.1f}s")
        self.logger.info(f"Progress markers: {len(self.context.progress_markers)}")
        self.logger.info(f"Error messages: {len(self.context.error_messages)}")
        
        # Platform-specific analysis
        if self.is_windows_deadlock_pattern():
            self.logger.info(" PASS:  WINDOWS DEADLOCK PATTERN CONFIRMED")
            self.logger.info(" PASS:  Matches SESSION5 asyncio deadlock indicators")
            
        elif self.is_sessionmiddleware_pattern():
            self.logger.info(" PASS:  SESSIONMIDDLEWARE PATTERN CONFIRMED") 
            self.logger.info(" PASS:  Matches SESSION5 WebSocket internal error indicators")
            
        else:
            self.logger.info(" SEARCH:  Pattern analysis:")
            self.logger.info(f"  Windows IOCP: {self.context.platform_info.is_windows_iocp()}")
            self.logger.info(f"  Timeout: {self.context.actual_failure_type == 'asyncio_timeout'}")
            self.logger.info(f"  Duration: {self.context.elapsed_time:.1f}s")
            
        # Success determination
        reproduction_success = self.context.analyze_reproduction_success() or \
                              self.is_windows_deadlock_pattern() or \
                              self.is_sessionmiddleware_pattern()
                              
        if reproduction_success:
            self.logger.info(" PASS:  REPRODUCTION SUCCESSFUL")
            self.logger.info(" PASS:  Critical failure pattern reproduced accurately")
        else:
            self.logger.info(" FAIL:  REPRODUCTION FAILED") 
            self.logger.info(" FAIL:  Could not reproduce expected failure pattern")


class WindowsAsyncioMonitor:
    """
    Monitor for Windows-specific asyncio issues
    
    This detects the specific patterns that cause deadlocks on Windows
    IOCP event loops, as identified in SESSION5 failures.
    """
    
    def __init__(self):
        self.platform_info = PlatformInfo.detect()
        self.monitoring_active = False
        self.concurrent_operations = 0
        self.event_loop_blocks = []
        
    @contextmanager 
    def monitor_concurrent_operation(self, operation_name: str):
        """Monitor a concurrent asyncio operation for Windows issues"""
        if not self.platform_info.is_windows_iocp():
            # Only monitor on Windows IOCP
            yield
            return
            
        self.concurrent_operations += 1
        operation_start = time.time()
        
        try:
            if self.concurrent_operations > 3:
                print(f" WARNING: [U+FE0F] WARNING: {self.concurrent_operations} concurrent asyncio operations on Windows IOCP")
                print(" WARNING: [U+FE0F] This may trigger GetQueuedCompletionStatus deadlock")
                
            yield
            
        finally:
            operation_duration = time.time() - operation_start
            self.concurrent_operations -= 1
            
            if operation_duration > 10:  # Suspiciously long operation
                self.event_loop_blocks.append({
                    "operation": operation_name,
                    "duration": operation_duration,
                    "concurrent_ops": self.concurrent_operations + 1,
                    "timestamp": time.time()
                })
                print(f" SEARCH:  Long operation detected: {operation_name} took {operation_duration:.1f}s")
    
    def get_deadlock_risk_assessment(self) -> Dict[str, Any]:
        """Assess risk of Windows asyncio deadlock based on monitoring"""
        if not self.platform_info.is_windows_iocp():
            return {"risk": "none", "reason": "Not Windows IOCP"}
            
        long_operations = len(self.event_loop_blocks)
        max_concurrent = max([0] + [block["concurrent_ops"] for block in self.event_loop_blocks])
        
        risk = "low"
        reasons = []
        
        if max_concurrent > 5:
            risk = "high"
            reasons.append(f"High concurrency: {max_concurrent} operations")
            
        elif max_concurrent > 3:
            risk = "medium" 
            reasons.append(f"Medium concurrency: {max_concurrent} operations")
            
        if long_operations > 2:
            risk = "high"
            reasons.append(f"Multiple long operations: {long_operations}")
            
        elif long_operations > 0:
            if risk == "low":
                risk = "medium"
            reasons.append(f"Long operations detected: {long_operations}")
        
        return {
            "risk": risk,
            "reasons": reasons,
            "max_concurrent_operations": max_concurrent,
            "long_operations": long_operations,
            "platform": self.platform_info.system,
            "asyncio_loop": self.platform_info.asyncio_loop_type
        }


def create_session5_reproduction_environment() -> Dict[str, Any]:
    """
    Create environment information that matches SESSION5 failure conditions
    
    This helps ensure reproduction tests run under similar conditions
    to those that caused the original failures.
    """
    platform_info = PlatformInfo.detect()
    
    environment = {
        "platform": {
            "system": platform_info.system,
            "version": platform_info.version,
            "python_version": platform_info.python_version,
            "asyncio_loop": platform_info.asyncio_loop_type,
            "is_windows_iocp": platform_info.is_windows_iocp()
        },
        "process": {
            "pid": platform_info.process_id,
            "thread_id": platform_info.thread_id,
            "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024
        },
        "reproduction_config": {
            "timeout_seconds": 300,  # Match SESSION5 timeout
            "expected_windows_deadlock": platform_info.is_windows_iocp(),
            "concurrent_operation_limit": 3 if platform_info.is_windows else 10,
            "enable_detailed_logging": True
        },
        "session5_indicators": {
            "windows_iocp_deadlock_risk": platform_info.is_windows_iocp(),
            "sessionmiddleware_failure_possible": True,  # All platforms can have this
            "websocket_event_delivery_risk": platform_info.is_windows_iocp()
        }
    }
    
    return environment


def validate_reproduction_test_requirements(test_name: str, duration: float, minimum: float = 0.2) -> bool:
    """
    Validate reproduction test meets requirements for accurate failure reproduction
    
    Reproduction tests must:
    1. Take real time (make actual network calls)
    2. Run on appropriate platform for the failure type
    3. Use appropriate timeout values
    4. Provide detailed error information
    """
    if duration < minimum:
        raise AssertionError(
            f" ALERT:  INVALID REPRODUCTION TEST: {test_name} completed in {duration:.3f}s "
            f"(minimum: {minimum}s). Reproduction tests must make real network calls "
            f"and allow sufficient time for failures to manifest!"
        )
        
    platform_info = PlatformInfo.detect()
    
    # Validate platform-specific requirements
    if "windows" in test_name.lower() and not platform_info.is_windows:
        print(f" WARNING: [U+FE0F] WARNING: Windows-specific test {test_name} running on {platform_info.system}")
        print(" WARNING: [U+FE0F] May not reproduce Windows-specific failure patterns")
        
    elif "asyncio" in test_name.lower() and not platform_info.asyncio_loop_type:
        print(f" WARNING: [U+FE0F] WARNING: Asyncio test {test_name} but no asyncio loop detected")
        
    return True


# Export main classes and functions for use in reproduction tests
__all__ = [
    'PlatformInfo',
    'FailureReproductionContext', 
    'CriticalFailureReproducer',
    'WindowsAsyncioMonitor',
    'create_session5_reproduction_environment',
    'validate_reproduction_test_requirements'
]


if __name__ == "__main__":
    # Demo/validation of reproduction helpers
    print("=" * 70)
    print("CRITICAL FAILURE REPRODUCTION HELPERS - DEMO")
    print("=" * 70)
    
    platform_info = PlatformInfo.detect()
    print(f"Platform: {platform_info.system} {platform_info.version}")
    print(f"Python: {platform_info.python_version}")
    print(f"Asyncio Loop: {platform_info.asyncio_loop_type}")
    print(f"Windows IOCP: {platform_info.is_windows_iocp()}")
    print(f"Supports Concurrent Asyncio: {platform_info.supports_concurrent_asyncio()}")
    
    environment = create_session5_reproduction_environment()
    print(f"\nReproduction Environment:")
    print(f"  Windows deadlock risk: {environment['session5_indicators']['windows_iocp_deadlock_risk']}")
    print(f"  SessionMiddleware failure possible: {environment['session5_indicators']['sessionmiddleware_failure_possible']}")
    print(f"  Timeout config: {environment['reproduction_config']['timeout_seconds']}s")
    
    print("=" * 70)