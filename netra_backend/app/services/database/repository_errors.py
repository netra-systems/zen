"""Repository Error Handling Module

Centralized error handling for database repository operations.
"""

from typing import Dict, Any, List
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.exceptions import (
    DatabaseError, RecordNotFoundError, ConstraintViolationError
)

logger = central_logger.get_logger(__name__)


class RepositoryErrorHandler:
    """Centralized error handling for repository operations"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
    
    def handle_integrity_error(self, e: IntegrityError, kwargs: Dict[str, Any]) -> ConstraintViolationError:
        """Handle integrity constraint violations."""
        logger.error(f"Integrity constraint violation creating {self.model_name}: {e}")
        return ConstraintViolationError(
            constraint=str(e.orig) if hasattr(e, 'orig') else "unknown",
            context={"repository": self.model_name, "data": kwargs}
        )
    
    def handle_sqlalchemy_error(self, e: SQLAlchemyError, kwargs: Dict[str, Any]) -> DatabaseError:
        """Handle SQLAlchemy database errors."""
        logger.error(f"Database error creating {self.model_name}: {e}")
        return DatabaseError(
            message=f"Failed to create {self.model_name}",
            context={"repository": self.model_name, "data": kwargs, "error": str(e)}
        )
    
    def handle_unexpected_error(self, e: Exception, kwargs: Dict[str, Any]) -> DatabaseError:
        """Handle unexpected errors during creation."""
        logger.error(f"Unexpected error creating {self.model_name}: {e}")
        return DatabaseError(
            message=f"Unexpected error creating {self.model_name}",
            context={"repository": self.model_name, "data": kwargs, "error": str(e)}
        )
    
    def handle_get_by_id_error(self, e: SQLAlchemyError, entity_id: str) -> DatabaseError:
        """Handle get by ID query errors."""
        logger.error(f"Error fetching {self.model_name} by id {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to fetch {self.model_name} by ID",
            context={"repository": self.model_name, "entity_id": entity_id, "error": str(e)}
        )
    
    def handle_get_all_error(self, e: SQLAlchemyError, filters: Dict[str, Any]) -> DatabaseError:
        """Handle get all query errors."""
        logger.error(f"Error fetching {self.model_name} list: {e}")
        return DatabaseError(
            message=f"Failed to fetch {self.model_name} list",
            context={"repository": self.model_name, "filters": filters, "error": str(e)}
        )
    
    def handle_update_error(self, e: SQLAlchemyError, entity_id: str, kwargs: Dict[str, Any]) -> DatabaseError:
        """Handle update operation errors."""
        logger.error(f"Error updating {self.model_name} {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to update {self.model_name}",
            context={"repository": self.model_name, "entity_id": entity_id, "data": kwargs, "error": str(e)}
        )
    
    def handle_delete_error(self, e: SQLAlchemyError, entity_id: str) -> DatabaseError:
        """Handle delete operation errors."""
        logger.error(f"Error deleting {self.model_name} {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to delete {self.model_name}",
            context={"repository": self.model_name, "entity_id": entity_id, "error": str(e)}
        )
    
    def handle_count_error(self, e: SQLAlchemyError, filters: Dict[str, Any]) -> DatabaseError:
        """Handle count operation errors."""
        logger.error(f"Error counting {self.model_name}: {e}")
        return DatabaseError(
            message=f"Failed to count {self.model_name}",
            context={"repository": self.model_name, "filters": filters, "error": str(e)}
        )
    
    def handle_exists_error(self, e: SQLAlchemyError, entity_id: str) -> DatabaseError:
        """Handle exists operation errors."""
        logger.error(f"Error checking existence of {self.model_name} {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to check existence of {self.model_name}",
            context={"repository": self.model_name, "entity_id": entity_id, "error": str(e)}
        )
    
    def handle_bulk_integrity_error(self, e: IntegrityError, data: List[Dict[str, Any]]) -> ConstraintViolationError:
        """Handle bulk create integrity errors."""
        logger.error(f"Integrity constraint violation bulk creating {self.model_name}: {e}")
        return ConstraintViolationError(
            constraint=str(e.orig) if hasattr(e, 'orig') else "unknown",
            context={"repository": self.model_name, "data_count": len(data)}
        )
    
    def handle_bulk_sqlalchemy_error(self, e: SQLAlchemyError, data: List[Dict[str, Any]]) -> DatabaseError:
        """Handle bulk create SQLAlchemy errors."""
        logger.error(f"Database error bulk creating {self.model_name}: {e}")
        return DatabaseError(
            message=f"Failed to bulk create {self.model_name}",
            context={"repository": self.model_name, "data_count": len(data), "error": str(e)}
        )
    
    def handle_bulk_unexpected_error(self, e: Exception, data: List[Dict[str, Any]]) -> DatabaseError:
        """Handle bulk create unexpected errors."""
        logger.error(f"Unexpected error bulk creating {self.model_name}: {e}")
        return DatabaseError(
            message=f"Unexpected error bulk creating {self.model_name}",
            context={"repository": self.model_name, "data_count": len(data), "error": str(e)}
        )
    
    def handle_get_many_error(self, e: SQLAlchemyError, ids: List[str]) -> DatabaseError:
        """Handle get many operation errors."""
        logger.error(f"Error fetching multiple {self.model_name}: {e}")
        return DatabaseError(
            message=f"Failed to fetch multiple {self.model_name}",
            context={"repository": self.model_name, "ids": ids, "error": str(e)}
        )
    
    def handle_soft_delete_error(self, e: SQLAlchemyError, entity_id: str) -> DatabaseError:
        """Handle soft delete operation errors."""
        logger.error(f"Error soft deleting {self.model_name} {entity_id}: {e}")
        return DatabaseError(
            message=f"Failed to soft delete {self.model_name}",
            context={"repository": self.model_name, "entity_id": entity_id, "error": str(e)}
        )
    
    def create_soft_delete_not_supported_error(self, entity_id: str) -> DatabaseError:
        """Create error for unsupported soft delete."""
        logger.warning(f"{self.model_name} does not support soft delete")
        return DatabaseError(
            message=f"{self.model_name} does not support soft delete",
            context={"repository": self.model_name, "entity_id": entity_id}
        )