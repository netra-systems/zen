"""Database Test Helpers - SSOT for Database Testing Support

This module provides utility functions to help tests handle database connectivity
gracefully when Docker services are not available.

Business Value:
- Segment: Platform/Internal - Development Velocity  
- Business Goal: Enable testing without Docker dependency
- Value Impact: Reduces test setup friction, enables CI/local development flexibility
- Strategic Impact: Faster development cycles, better test reliability
"""

import logging
import pytest
from typing import Dict, Any, Optional
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

def require_database_or_skip(db_connection_info: Dict[str, Any], test_name: str = "test") -> None:
    """Skip test if database is not available with helpful message.
    
    Args:
        db_connection_info: Database connection info from real_postgres_connection fixture
        test_name: Name of the test for error reporting
        
    Raises:
        pytest.skip: If database is not available
    """
    if not db_connection_info.get("available", False):
        error = db_connection_info.get("error", "Database not available")
        guidance = db_connection_info.get("guidance", "Check Docker and database configuration")
        
        skip_message = f"{test_name} requires database connection - {error}. {guidance}"
        logger.info(f"Skipping {test_name}: {skip_message}")
        pytest.skip(skip_message)

def get_database_skip_marker():
    """Get pytest marker for database-dependent tests."""
    env = get_env()
    use_real_services = env.get("USE_REAL_SERVICES", "false").lower() == "true"
    
    if not use_real_services:
        return pytest.mark.skip(reason="Database tests require USE_REAL_SERVICES=true")
    
    return None

def check_database_availability() -> Dict[str, Any]:
    """Check if database services are available without starting them.
    
    Returns:
        Dict with availability status and guidance
    """
    import socket
    import subprocess
    
    result = {
        "docker_running": False,
        "database_port_open": False,
        "guidance": []
    }
    
    # Check Docker
    try:
        docker_check = subprocess.run(['docker', 'ps'], capture_output=True, timeout=5)
        result["docker_running"] = docker_check.returncode == 0
        if not result["docker_running"]:
            result["guidance"].append("Start Docker Desktop")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        result["guidance"].append("Install and start Docker")
    
    # Check database port
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            result["database_port_open"] = sock.connect_ex(("localhost", 5434)) == 0
    except Exception:
        pass
    
    if not result["database_port_open"] and result["docker_running"]:
        result["guidance"].append("Run: python tests/unified_test_runner.py --real-services")
    
    return result

class DatabaseTestContext:
    """Context manager for database-dependent tests."""
    
    def __init__(self, db_connection_info: Dict[str, Any], test_name: str = "test"):
        self.db_info = db_connection_info
        self.test_name = test_name
        self.db_session = None
        
    async def __aenter__(self):
        """Enter the context - check database availability."""
        require_database_or_skip(self.db_info, self.test_name)
        
        self.db_session = self.db_info.get("db") 
        if not self.db_session:
            pytest.fail(f"Database session not available for {self.test_name}")
            
        return self.db_session
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context - cleanup if needed."""
        if self.db_session:
            try:
                await self.db_session.rollback()
            except Exception as e:
                logger.warning(f"Failed to rollback database session in {self.test_name}: {e}")

# Pytest fixtures for easy database testing

@pytest.fixture(scope="session")
def database_availability_info():
    """Fixture providing database availability information."""
    return check_database_availability()

@pytest.fixture(scope="function")
def database_test_context():
    """Fixture providing database test context manager factory."""
    def _create_context(db_connection_info, test_name="test"):
        return DatabaseTestContext(db_connection_info, test_name)
    return _create_context