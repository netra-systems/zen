"""
Corpus Admin Sub-Agent Module

Provides corpus management and administration functionality with 
modular architecture under 450-line limit.
"""

from .agent import CorpusAdminSubAgent
from .models import (
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
    CorpusStatistics
)
from .operations import CorpusOperationHandler
from .parsers import CorpusRequestParser
from .validators import CorpusApprovalValidator

__all__ = [
    "CorpusAdminSubAgent",
    "CorpusOperation",
    "CorpusType", 
    "CorpusMetadata",
    "CorpusOperationRequest",
    "CorpusOperationResult",
    "CorpusStatistics",
    "CorpusOperationHandler",
    "CorpusRequestParser",
    "CorpusApprovalValidator"
]