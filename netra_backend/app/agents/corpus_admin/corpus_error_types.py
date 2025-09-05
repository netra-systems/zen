"""
Corpus error types module.

Defines error types for corpus operations.
This module has been removed but tests still reference it.
"""


class CorpusErrorTypes:
    """
    Corpus error types enumeration.
    
    Defines various error types that can occur during corpus operations.
    """
    
    VALIDATION_ERROR = "validation_error"
    STORAGE_ERROR = "storage_error"
    INDEX_ERROR = "index_error"
    PERMISSION_ERROR = "permission_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    
    @classmethod
    def get_all_error_types(cls):
        """Get all available error types."""
        return [
            cls.VALIDATION_ERROR,
            cls.STORAGE_ERROR,
            cls.INDEX_ERROR,
            cls.PERMISSION_ERROR,
            cls.NETWORK_ERROR,
            cls.TIMEOUT_ERROR
        ]
    
    @classmethod
    def is_valid_error_type(cls, error_type):
        """Check if error type is valid."""
        return error_type in cls.get_all_error_types()