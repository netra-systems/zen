"""
Auth Service Database Interface

This module provides the database interface for the auth service,
following SSOT principles and maintaining service independence.

Business Value: Ensures consistent database access patterns across the auth service.
"""

from auth_service.auth_core.database import auth_db, get_db_session


def get_database():
    """
    Get the auth service database interface.
    
    This function provides access to the auth service database following SSOT patterns.
    
    Returns:
        The auth database interface
    """
    return auth_db


__all__ = ["get_database"]