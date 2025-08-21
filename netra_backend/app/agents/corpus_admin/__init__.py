"""
Corpus Admin Sub-Agent Module

Provides corpus management and administration functionality with 
modular architecture under 450-line limit.
"""

from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent
from netra_backend.app.agents.corpus_admin.models import (
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
    CorpusStatistics
)
from netra_backend.app.agents.corpus_admin.operations import CorpusOperationHandler
from netra_backend.app.agents.corpus_admin.parsers import CorpusRequestParser
from netra_backend.app.agents.corpus_admin.validators import CorpusApprovalValidator

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