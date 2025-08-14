"""Context-Aware Fallback Response Service

Backward compatibility module that imports from the new modular structure.
This service provides intelligent, context-aware fallback responses when AI generation
fails or produces low-quality output, replacing generic error messages with helpful alternatives.
"""

from .fallback_response import (
    FallbackResponseService,
    FailureReason,
    FallbackContext
)
# Backward compatibility - create instance of the modularized service
_fallback_service = FallbackResponseService()

# Export the same interface as before
async def generate_fallback(*args, **kwargs):
    """Generate a context-aware fallback response"""
    return await _fallback_service.generate_fallback(*args, **kwargs)

async def generate_batch_fallbacks(*args, **kwargs):
    """Generate fallback responses for multiple contexts"""
    return await _fallback_service.generate_batch_fallbacks(*args, **kwargs)

def get_fallback_for_json_error(*args, **kwargs):
    """Generate fallback for JSON parsing errors"""
    return _fallback_service.get_fallback_for_json_error(*args, **kwargs)

# For backward compatibility, also provide the class directly
class FallbackResponseService(FallbackResponseService):
    """Backward compatibility wrapper"""
    pass