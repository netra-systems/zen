"""
Base classes and enums for corpus management
"""

from enum import Enum


class CorpusStatus(Enum):
    """Corpus lifecycle status"""
    CREATING = "creating"
    AVAILABLE = "available"
    FAILED = "failed"
    UPDATING = "updating"
    DELETING = "deleting"


class ContentSource(Enum):
    """Source of corpus content"""
    UPLOAD = "upload"
    GENERATE = "generate"
    IMPORT = "import"


class CorpusBaseException(Exception):
    """Base exception for corpus operations"""
    pass


class CorpusNotFoundError(CorpusBaseException):
    """Raised when corpus is not found"""
    pass


class CorpusNotAvailableError(CorpusBaseException):
    """Raised when corpus is not in available state"""
    pass


class ValidationError(CorpusBaseException):
    """Raised when validation fails"""
    pass


class ClickHouseOperationError(CorpusBaseException):
    """Raised when ClickHouse operations fail"""
    pass