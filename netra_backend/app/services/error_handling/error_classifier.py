"""Error classifier service module.

Business Value: Provides error classification for error handling services.
SSOT: Re-exports ErrorClassifier from agents.base.error_classification.

This module serves as the service layer interface to the SSOT error classification
system while maintaining the expected import path for the test suite.
"""

# SSOT Import - Use existing error classification implementation
from netra_backend.app.agents.base.error_classification import (
    ErrorClassifier,
    ErrorClassification,
    ErrorCategory
)

# Re-export for service layer compatibility
__all__ = ['ErrorClassifier', 'ErrorClassification', 'ErrorCategory']