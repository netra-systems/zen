"""Context-Aware Fallback Response Service

Backward compatibility module that imports from the new modular structure.
This service provides intelligent, context-aware fallback responses when AI generation
fails or produces low-quality output, replacing generic error messages with helpful alternatives.
"""

from typing import Dict, List, Any

# Import the actual implementation
from netra_backend.app.services.fallback_response import (
    FallbackResponseService as _OriginalFallbackResponseService,
    FailureReason,
    FallbackContext
)

# Backward compatibility - create instance of the modularized service
_fallback_service = _OriginalFallbackResponseService()

# Export the same interface as before with proper type hints
async def generate_fallback(
    context: 'FallbackContext',
    include_diagnostics: bool = True,
    include_recovery: bool = True
) -> Dict[str, Any]:
    """Generate a context-aware fallback response"""
    return await _fallback_service.generate_fallback(context, include_diagnostics, include_recovery)

async def generate_batch_fallbacks(contexts: List['FallbackContext']) -> List[Dict[str, Any]]:
    """Generate fallback responses for multiple contexts"""
    return await _fallback_service.generate_batch_fallbacks(contexts)

def get_fallback_for_json_error(
    agent_name: str,
    raw_response: str,
    expected_format: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate fallback for JSON parsing errors"""
    return _fallback_service.get_fallback_for_json_error(agent_name, raw_response, expected_format)

# For backward compatibility, also provide the class directly
class FallbackResponseService(_OriginalFallbackResponseService):
    """Backward compatibility wrapper that properly exposes all methods"""
    pass