# Health monitoring test fixtures
"""Health monitoring test fixtures for test framework"""

class AdaptiveHealthMonitor:
    """Test fixture for adaptive health monitoring."""
    
    def __init__(self):
        """Initialize the adaptive health monitor test fixture."""
        self.health_status = "healthy"
        self.checks_performed = []
        self.alerts = []
    
    def perform_health_check(self, component: str) -> bool:
        """Perform a health check on a component."""
        self.checks_performed.append(component)
        return True
    
    def get_health_status(self) -> str:
        """Get current health status."""
        return self.health_status
    
    def set_health_status(self, status: str) -> None:
        """Set health status for testing."""
        self.health_status = status
    
    def trigger_alert(self, message: str) -> None:
        """Trigger a health alert for testing."""
        self.alerts.append(message)
    
    def get_alerts(self) -> list:
        """Get all triggered alerts."""
        return self.alerts
    
    def reset(self) -> None:
        """Reset the health monitor state."""
        self.health_status = "healthy"
        self.checks_performed.clear()
        self.alerts.clear()