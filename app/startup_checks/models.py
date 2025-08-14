"""
Startup Check Models

Data models for startup check results and configuration.
Maintains simple structure under 300-line limit.
"""


class StartupCheckResult:
    """Result of a startup check"""
    
    def __init__(self, name: str, success: bool, message: str, 
                 critical: bool = True, duration_ms: float = 0):
        self.name = name
        self.success = success
        self.message = message
        self.critical = critical
        self.duration_ms = duration_ms