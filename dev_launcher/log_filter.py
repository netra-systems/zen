"""
Log filtering system for clean startup output.

Implements smart log filtering based on startup mode as per spec v2.0.
"""

import time
from typing import Dict, Any
from .log_filter_core import LogFilter, StartupMode, LogLevel


class StartupProgressTracker:
    """
    Track and display startup progress in clean format.
    """
    
    def __init__(self, mode: StartupMode = StartupMode.MINIMAL):
        """Initialize progress tracker."""
        self.mode = mode
        self.services: Dict[str, Dict[str, Any]] = {}
        self.start_time = None
        
    def start(self):
        """Mark startup beginning."""
        self.start_time = time.time()
        if self.mode == StartupMode.MINIMAL:
            print("⚡ Starting Netra Apex Development Environment...")
        
    def service_starting(self, name: str):
        """Mark service as starting."""
        self.services[name] = {
            "status": "starting",
            "start_time": time.time(),
            "port": None
        }
        
    def service_started(self, name: str, port: int):
        """Mark service as started."""
        if name in self.services:
            duration = time.time() - self.services[name]["start_time"]
            self.services[name].update({
                "status": "started",
                "port": port,
                "duration": duration
            })
            
            if self.mode == StartupMode.MINIMAL:
                # Single line progress
                print(f"✅ {name:<15} [Port: {port:<5}] {duration:.1f}s")
            
    def service_failed(self, name: str, error: str):
        """Mark service as failed."""
        if name in self.services:
            self.services[name]["status"] = "failed"
            self.services[name]["error"] = error
            
            if self.mode == StartupMode.MINIMAL:
                print(f"❌ {name:<15} Failed: {error}")
    
    def complete(self):
        """Show completion summary."""
        if not self.start_time:
            return
            
        total_time = time.time() - self.start_time
        
        if self.mode == StartupMode.MINIMAL:
            print(f"\n🚀 System Ready ({total_time:.1f}s)")
            
            # Show service URLs
            for name, info in self.services.items():
                if info["status"] == "started" and info.get("port"):
                    url = f"http://localhost:{info['port']}"
                    print(f"   {name:<10} {url}")


# Additional filter presets for different scenarios
class FilterPresets:
    """Predefined filter configurations."""
    
    @staticmethod
    def get_development_filter() -> LogFilter:
        """Get filter optimized for development."""
        return LogFilter(StartupMode.MINIMAL)
    
    @staticmethod
    def get_ci_filter() -> LogFilter:
        """Get filter optimized for CI/CD."""
        return LogFilter(StartupMode.STANDARD)
    
    @staticmethod
    def get_production_filter() -> LogFilter:
        """Get filter optimized for production."""
        return LogFilter(StartupMode.SILENT)
    
    @staticmethod
    def get_debug_filter() -> LogFilter:
        """Get filter for debugging sessions."""
        return LogFilter(StartupMode.VERBOSE)


# Export main classes for backward compatibility
__all__ = [
    'LogFilter', 
    'StartupMode', 
    'LogLevel', 
    'StartupProgressTracker',
    'FilterPresets'
]