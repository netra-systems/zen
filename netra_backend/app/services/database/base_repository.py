"""Base Repository Pattern Implementation

Provides abstract base class for all repositories with common CRUD operations.
Refactored into modular components for better maintainability and adherence to 450-line limit.
"""

from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.services.database.base_crud import BaseCRUD

T = TypeVar('T')


class BaseRepository(BaseCRUD[T]):
    """Abstract base repository with common database operations
    
    This class inherits from BaseCRUD which provides all the core functionality
    through focused, modular components under 300 lines each.
    """
    
    def __init__(self, model: Type[T]):
        super().__init__(model)
    
    # All CRUD operations are inherited from BaseCRUD
    # The abstract find_by_user method is inherited and must be implemented by subclasses