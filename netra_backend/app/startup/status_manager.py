"""
Startup Status Manager for Netra AI Platform.

Minimal implementation to unblock test collection.
This module provides basic status management functionality.
"""

import logging
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class StartupStatusManager:
    """
    Minimal startup status manager for test compatibility.
    
    This class provides basic status tracking functionality
    to support the startup module imports without breaking tests.
    """
    
    def __init__(self):
        """Initialize the status manager."""
        self.status: Dict[str, Any] = {
            "initialized": True,
            "components": {},
            "errors": []
        }
        self.logger = logger
    
    def update_status(self, component: str, status: str, details: Optional[Dict] = None) -> None:
        """
        Update status for a component.
        
        Args:
            component: Name of the component
            status: Status string (e.g., 'healthy', 'error', 'initializing')
            details: Optional details dictionary
        """
        self.status["components"][component] = {
            "status": status,
            "details": details or {}
        }
        self.logger.debug(f"Status updated for {component}: {status}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status.
        
        Returns:
            Dictionary containing current status information
        """
        return self.status.copy()
    
    def is_healthy(self) -> bool:
        """
        Check if all components are healthy.
        
        Returns:
            True if all components are healthy, False otherwise
        """
        for component_status in self.status["components"].values():
            if component_status.get("status") == "error":
                return False
        return len(self.status["errors"]) == 0
    
    def add_error(self, error: str, component: Optional[str] = None) -> None:
        """
        Add an error to the status.
        
        Args:
            error: Error message
            component: Optional component name where error occurred
        """
        error_entry = {"message": error, "component": component}
        self.status["errors"].append(error_entry)
        self.logger.error(f"Error added to status: {error}")


# Global instance for compatibility
startup_status_manager = StartupStatusManager()