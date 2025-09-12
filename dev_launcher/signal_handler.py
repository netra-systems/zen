"""
Comprehensive signal handling and cleanup system for dev launcher.

Provides robust signal handling across all platforms with:
- Graceful shutdown on SIGINT, SIGTERM, SIGHUP
- Windows console event handling
- Resource cleanup coordination
- Timeout-based emergency cleanup
- Process tree termination management

Business Value: Platform/Internal - System Stability
Ensures 100% clean shutdown with no resource leaks across all platforms.
"""

import asyncio
import atexit
import logging
import signal
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class ShutdownPhase(Enum):
    """Shutdown phases for coordinated cleanup."""
    INITIATED = "initiated"
    STOPPING_SERVICES = "stopping_services"  
    CLEANING_PROCESSES = "cleaning_processes"
    CLEANING_RESOURCES = "cleaning_resources"
    EMERGENCY_CLEANUP = "emergency_cleanup"
    COMPLETED = "completed"


@dataclass
class CleanupHandler:
    """Cleanup handler registration."""
    name: str
    handler: Callable
    priority: int = 100  # Lower = higher priority
    timeout: float = 10.0  # Seconds
    critical: bool = False  # If True, failure stops shutdown


class SignalHandler:
    """
    Comprehensive signal handling and cleanup coordination system.
    
    Manages graceful shutdown across all platforms with proper resource cleanup,
    process termination, and emergency fallbacks.
    """
    
    def __init__(self, use_emoji: bool = False):
        """Initialize signal handler."""
        self.use_emoji = use_emoji
        self.is_windows = sys.platform == "win32"
        self.shutdown_initiated = False
        self.shutdown_phase = ShutdownPhase.INITIATED
        self.cleanup_handlers: List[CleanupHandler] = []
        self.emergency_timeout = 30.0  # Total emergency timeout
        self.shutdown_start_time: Optional[float] = None
        self._lock = threading.Lock()
        self._emergency_cleanup_running = False  # Prevent recursive emergency cleanup
        
        # Setup platform-specific signal handling
        self._setup_signal_handlers()
        
        # Register atexit handler as last resort
        atexit.register(self._atexit_cleanup)
        
        emoji = "[U+1F6E1][U+FE0F]" if self.use_emoji else ""
        logger.info(f"{emoji} Signal handler initialized for {sys.platform}")
    
    def register_cleanup_handler(
        self,
        name: str,
        handler: Callable,
        priority: int = 100,
        timeout: float = 10.0,
        critical: bool = False
    ) -> bool:
        """Register a cleanup handler."""
        with self._lock:
            cleanup_handler = CleanupHandler(
                name=name,
                handler=handler, 
                priority=priority,
                timeout=timeout,
                critical=critical
            )
            
            self.cleanup_handlers.append(cleanup_handler)
            # Keep handlers sorted by priority
            self.cleanup_handlers.sort(key=lambda x: x.priority)
            
            emoji = "[U+1F4DD]" if self.use_emoji else ""
            logger.debug(f"{emoji} Registered cleanup handler: {name} (priority: {priority})")
            return True
    
    def initiate_shutdown(self, signal_name: str = "UNKNOWN") -> None:
        """Initiate coordinated shutdown process."""
        with self._lock:
            if self.shutdown_initiated:
                logger.warning("Shutdown already initiated, ignoring duplicate signal")
                return
            
            self.shutdown_initiated = True
            self.shutdown_start_time = time.time()
            
            emoji = "[U+1F6D1]" if self.use_emoji else ""
            logger.info(f"{emoji} SHUTDOWN INITIATED by {signal_name}")
            print(f"\\n{emoji} Graceful shutdown initiated...")
        
        # Start shutdown process
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # Schedule shutdown task
            loop.create_task(self._async_shutdown_process(signal_name))
        except RuntimeError:
            # No event loop running, use sync shutdown
            self._sync_shutdown_process(signal_name)
    
    async def _async_shutdown_process(self, signal_name: str) -> None:
        """Asynchronous shutdown process."""
        try:
            await self._execute_cleanup_handlers()
            self._complete_shutdown(signal_name)
        except Exception as e:
            logger.error(f"Async shutdown failed: {e}")
            self._emergency_cleanup(signal_name)
    
    def _sync_shutdown_process(self, signal_name: str) -> None:
        """Synchronous shutdown process."""
        try:
            self._execute_cleanup_handlers_sync()
            self._complete_shutdown(signal_name)
        except Exception as e:
            logger.error(f"Sync shutdown failed: {e}")
            self._emergency_cleanup(signal_name)
    
    async def _execute_cleanup_handlers(self) -> None:
        """Execute all cleanup handlers asynchronously."""
        self.shutdown_phase = ShutdownPhase.STOPPING_SERVICES
        
        emoji = "[U+1F9F9]" if self.use_emoji else ""
        logger.info(f"{emoji} Executing {len(self.cleanup_handlers)} cleanup handlers...")
        
        for handler in self.cleanup_handlers:
            if self._is_emergency_timeout():
                logger.warning("Emergency timeout reached, switching to emergency cleanup")
                self._emergency_cleanup("TIMEOUT")
                return
            
            try:
                start_time = time.time()
                
                # Execute handler with timeout
                if asyncio.iscoroutinefunction(handler.handler):
                    await asyncio.wait_for(handler.handler(), timeout=handler.timeout)
                else:
                    # Run sync handler in executor
                    loop = asyncio.get_running_loop()
                    await asyncio.wait_for(
                        loop.run_in_executor(None, handler.handler),
                        timeout=handler.timeout
                    )
                
                duration = time.time() - start_time
                logger.debug(f"[U+2713] Cleanup handler '{handler.name}' completed in {duration:.2f}s")
                
            except asyncio.TimeoutError:
                logger.error(f"[U+2717] Cleanup handler '{handler.name}' timed out after {handler.timeout}s")
                if handler.critical:
                    logger.error("Critical handler failed, initiating emergency cleanup")
                    self._emergency_cleanup("CRITICAL_HANDLER_TIMEOUT")
                    return
                    
            except Exception as e:
                logger.error(f"[U+2717] Cleanup handler '{handler.name}' failed: {e}")
                if handler.critical:
                    logger.error("Critical handler failed, initiating emergency cleanup")  
                    self._emergency_cleanup("CRITICAL_HANDLER_ERROR")
                    return
    
    def _execute_cleanup_handlers_sync(self) -> None:
        """Execute all cleanup handlers synchronously."""
        self.shutdown_phase = ShutdownPhase.STOPPING_SERVICES
        
        emoji = "[U+1F9F9]" if self.use_emoji else ""
        logger.info(f"{emoji} Executing {len(self.cleanup_handlers)} cleanup handlers (sync)...")
        
        for handler in self.cleanup_handlers:
            if self._is_emergency_timeout():
                logger.warning("Emergency timeout reached, switching to emergency cleanup")
                self._emergency_cleanup("TIMEOUT")
                return
            
            try:
                start_time = time.time()
                
                # Execute sync handler directly
                if not asyncio.iscoroutinefunction(handler.handler):
                    handler.handler()
                else:
                    logger.warning(f"Skipping async handler '{handler.name}' in sync context")
                    continue
                
                duration = time.time() - start_time
                logger.debug(f"[U+2713] Cleanup handler '{handler.name}' completed in {duration:.2f}s")
                
            except Exception as e:
                logger.error(f"[U+2717] Cleanup handler '{handler.name}' failed: {e}")
                if handler.critical:
                    logger.error("Critical handler failed, initiating emergency cleanup")
                    self._emergency_cleanup("CRITICAL_HANDLER_ERROR")
                    return
    
    def _complete_shutdown(self, signal_name: str) -> None:
        """Complete the shutdown process."""
        self.shutdown_phase = ShutdownPhase.COMPLETED
        
        duration = time.time() - self.shutdown_start_time if self.shutdown_start_time else 0
        
        emoji = " PASS: " if self.use_emoji else ""
        logger.info(f"{emoji} Graceful shutdown completed in {duration:.2f}s (signal: {signal_name})")
        print(f"{emoji} Shutdown completed successfully.")
        
        # Exit cleanly
        sys.exit(0)
    
    def _emergency_cleanup(self, reason: str) -> None:
        """Emergency cleanup when graceful shutdown fails."""
        # Prevent recursive emergency cleanup calls
        if self._emergency_cleanup_running:
            print(f" Emergency cleanup already in progress, ignoring {reason}")
            return
        
        self._emergency_cleanup_running = True
        self.shutdown_phase = ShutdownPhase.EMERGENCY_CLEANUP
        
        emoji = " ALERT: " if self.use_emoji else ""
        logger.critical(f"{emoji} EMERGENCY CLEANUP initiated: {reason}")
        print(f"{emoji} Emergency cleanup in progress...")
        
        try:
            # Try to execute highest priority handlers only
            critical_handlers = [h for h in self.cleanup_handlers if h.critical]
            
            for handler in critical_handlers[:3]:  # Only first 3 critical handlers
                try:
                    if not asyncio.iscoroutinefunction(handler.handler):
                        handler.handler()
                    logger.debug(f"Emergency cleanup: {handler.name} executed")
                except Exception as e:
                    logger.error(f"Emergency cleanup failed for {handler.name}: {e}")
        
        except Exception as e:
            logger.critical(f"Emergency cleanup failed: {e}")
        
        finally:
            logger.critical("Emergency exit - some resources may not be cleaned up properly")
            print(f"{emoji} Emergency exit initiated.")
            sys.exit(1)
    
    def _is_emergency_timeout(self) -> bool:
        """Check if emergency timeout has been reached."""
        if not self.shutdown_start_time:
            return False
        
        elapsed = time.time() - self.shutdown_start_time
        return elapsed > self.emergency_timeout
    
    def _setup_signal_handlers(self) -> None:
        """Setup platform-specific signal handlers."""
        if self.is_windows:
            self._setup_windows_handlers()
        else:
            self._setup_unix_handlers()
    
    def _setup_windows_handlers(self) -> None:
        """Setup Windows-specific signal handlers."""
        # Basic signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Try to setup Windows console event handlers
        try:
            import win32api
            import win32con
            
            def console_ctrl_handler(ctrl_type):
                """Handle Windows console control events."""
                event_names = {
                    win32con.CTRL_C_EVENT: "CTRL_C",
                    win32con.CTRL_BREAK_EVENT: "CTRL_BREAK", 
                    win32con.CTRL_CLOSE_EVENT: "CTRL_CLOSE",
                    win32con.CTRL_LOGOFF_EVENT: "CTRL_LOGOFF",
                    win32con.CTRL_SHUTDOWN_EVENT: "CTRL_SHUTDOWN"
                }
                
                event_name = event_names.get(ctrl_type, f"CTRL_{ctrl_type}")
                logger.info(f"Windows console event: {event_name}")
                
                if ctrl_type in [win32con.CTRL_C_EVENT, win32con.CTRL_BREAK_EVENT, win32con.CTRL_CLOSE_EVENT]:
                    self.initiate_shutdown(event_name)
                    return True  # Handled
                
                return False  # Not handled
            
            win32api.SetConsoleCtrlHandler(console_ctrl_handler, True)
            
            emoji = "[U+1FA9F]" if self.use_emoji else ""
            logger.info(f"{emoji} Windows console event handlers registered")
            
        except ImportError:
            logger.debug("pywin32 not available, using basic Windows signal handling")
    
    def _setup_unix_handlers(self) -> None:
        """Setup Unix-like system signal handlers."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Additional Unix signals
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, self._signal_handler)
        if hasattr(signal, 'SIGUSR1'):
            signal.signal(signal.SIGUSR1, self._signal_handler)
        
        emoji = "[U+1F427]" if self.use_emoji else ""
        logger.info(f"{emoji} Unix signal handlers registered")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle received signals."""
        signal_names = {
            signal.SIGINT: "SIGINT",
            signal.SIGTERM: "SIGTERM",
        }
        
        if hasattr(signal, 'SIGHUP') and signum == signal.SIGHUP:
            signal_names[signum] = "SIGHUP"
        if hasattr(signal, 'SIGUSR1') and signum == signal.SIGUSR1:
            signal_names[signum] = "SIGUSR1"
        
        signal_name = signal_names.get(signum, f"SIGNAL_{signum}")
        
        logger.info(f"Received signal: {signal_name}")
        self.initiate_shutdown(signal_name)
    
    def _atexit_cleanup(self) -> None:
        """Last resort cleanup via atexit handler."""
        # Only trigger emergency cleanup if we actually have cleanup handlers registered
        # and shutdown wasn't initiated (indicates an abnormal exit)
        if not self.shutdown_initiated and self.cleanup_handlers and not self._emergency_cleanup_running:
            logger.warning("atexit cleanup triggered - shutdown was not properly initiated")
            self._emergency_cleanup("ATEXIT")
        else:
            logger.debug("atexit cleanup - shutdown already completed or no handlers registered")
    
    def force_shutdown(self, reason: str = "FORCE") -> None:
        """Force immediate shutdown - use only in emergencies."""
        logger.critical(f"FORCE SHUTDOWN: {reason}")
        self._emergency_cleanup(reason)
    
    def mark_clean_exit(self) -> None:
        """Mark that the application is exiting cleanly (no emergency cleanup needed)."""
        self.shutdown_initiated = True
        logger.debug("Clean exit marked - emergency cleanup will be skipped")
        
    def get_shutdown_status(self) -> Dict[str, any]:
        """Get current shutdown status."""
        return {
            "shutdown_initiated": self.shutdown_initiated,
            "shutdown_phase": self.shutdown_phase.value,
            "handlers_registered": len(self.cleanup_handlers),
            "elapsed_time": time.time() - self.shutdown_start_time if self.shutdown_start_time else 0,
            "emergency_timeout": self.emergency_timeout,
            "platform": sys.platform
        }
    
    def add_process_cleanup(self, process_manager, process_name: str) -> None:
        """Add process cleanup handler with proper priority."""
        def cleanup_process():
            try:
                if hasattr(process_manager, 'terminate_process'):
                    process_manager.terminate_process(process_name)
                elif hasattr(process_manager, 'kill_process'):
                    process_manager.kill_process(process_name)
                logger.debug(f"Process cleanup completed: {process_name}")
            except Exception as e:
                logger.error(f"Process cleanup failed for {process_name}: {e}")
        
        self.register_cleanup_handler(
            name=f"process_{process_name}",
            handler=cleanup_process,
            priority=50,  # High priority for process cleanup
            timeout=15.0,
            critical=True
        )
    
    def add_resource_cleanup(self, name: str, cleanup_func: Callable, critical: bool = False) -> None:
        """Add generic resource cleanup handler."""
        self.register_cleanup_handler(
            name=f"resource_{name}",
            handler=cleanup_func,
            priority=200,  # Lower priority for resource cleanup
            timeout=5.0,
            critical=critical
        )