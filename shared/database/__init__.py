"""
Shared Database Utilities

This module provides shared database utilities that can be used across all services
to eliminate duplication and provide a single source of truth for database operations.
"""

from shared.database.core_database_manager import CoreDatabaseManager

__all__ = ["CoreDatabaseManager"]