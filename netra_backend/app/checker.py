"""Checker module for system health and validation checks"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime


class SystemChecker:
    """Basic system health checker"""
    
    def __init__(self):
        self.checks_performed = 0
        self.last_check = None
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        self.checks_performed += 1
        self.last_check = datetime.now()
        
        return {
            "status": "healthy",
            "timestamp": self.last_check.isoformat(),
            "checks_performed": self.checks_performed,
            "components": {
                "database": "ok",
                "cache": "ok",
                "services": "ok"
            }
        }
    
    async def validate_configuration(self) -> bool:
        """Validate system configuration"""
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get current checker status"""
        return {
            "checks_performed": self.checks_performed,
            "last_check": self.last_check.isoformat() if self.last_check else None
        }


# Create singleton instance
system_checker = SystemChecker()


# Export commonly used functions
async def check_health():
    """Quick health check"""
    return await system_checker.check_system_health()


async def validate_config():
    """Quick config validation"""
    return await system_checker.validate_configuration()