"""Configuration Validation Types

**CRITICAL: Enterprise-Grade Configuration Validation Types**

Shared types and constants for configuration validation.
Business Value: Ensures type consistency across validation modules.

Each function  <= 8 lines, file  <= 300 lines.
"""

from typing import List, NamedTuple


class ValidationResult(NamedTuple):
    """Configuration validation result."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    score: int  # 0-100 configuration health score