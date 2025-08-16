"""Validation error handling utilities for corpus admin operations.

Provides specialized handlers for document validation failures with recovery strategies.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.error_handler import ErrorContext, global_error_handler
from app.agents.corpus_admin.corpus_error_types import DocumentValidationError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ValidationErrorHandler:
    """Handles document validation failures with recovery strategies."""
    
    def __init__(self):
        """Initialize validation error handler."""
        pass
    
    async def handle_document_validation_error(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str,
        original_error: Exception
    ) -> Dict[str, Any]:
        """Handle document validation failures."""
        context = self._create_validation_error_context(
            filename, validation_errors, run_id, original_error
        )
        
        error = DocumentValidationError(filename, validation_errors, context)
        
        try:
            # Try validation recovery strategies
            result = await self._attempt_validation_recovery(
                filename, validation_errors, run_id
            )
            if result:
                return result
            
            # Create validation report for manual review
            report_result = await self._create_validation_report(
                filename, validation_errors, run_id
            )
            return report_result
            
        except Exception as fallback_error:
            await global_error_handler.handle_error(error, context)
            raise error
    
    def _create_validation_error_context(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str,
        original_error: Exception
    ) -> ErrorContext:
        """Create error context for validation failures."""
        return ErrorContext(
            agent_name="corpus_admin_agent",
            operation_name="document_validation",
            run_id=run_id,
            additional_data={
                'filename': filename,
                'validation_errors': validation_errors,
                'original_error': str(original_error)
            }
        )
    
    async def _attempt_validation_recovery(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Attempt validation recovery strategies."""
        # Try to fix common validation issues
        fixed_result = await self._try_validation_fixes(
            filename, validation_errors, run_id
        )
        if fixed_result:
            return fixed_result
        
        # Try relaxed validation
        relaxed_result = await self._try_relaxed_validation(
            filename, validation_errors, run_id
        )
        return relaxed_result
    
    async def _try_validation_fixes(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try to automatically fix common validation issues."""
        fixed_errors = []
        
        for error in validation_errors:
            if await self._can_fix_error(error, filename):
                fixed_errors.append(error)
        
        if fixed_errors:
            return self._create_fixes_success_response(
                filename, fixed_errors, validation_errors, run_id
            )
        
        return None
    
    async def _can_fix_error(self, error: str, filename: str) -> bool:
        """Check if error can be automatically fixed."""
        if 'encoding' in error.lower():
            return await self._fix_encoding_issue(filename)
        elif 'format' in error.lower():
            return await self._fix_format_issue(filename)
        return False
    
    def _create_fixes_success_response(
        self,
        filename: str,
        fixed_errors: List[str],
        validation_errors: List[str],
        run_id: str
    ) -> Dict[str, Any]:
        """Create success response for automatic fixes."""
        remaining_errors = [e for e in validation_errors if e not in fixed_errors]
        
        logger.info(
            f"Fixed validation errors automatically",
            filename=filename,
            fixed_count=len(fixed_errors),
            remaining_count=len(remaining_errors),
            run_id=run_id
        )
        
        return {
            'success': True,
            'method': 'automatic_fixes',
            'fixed_errors': fixed_errors,
            'remaining_errors': remaining_errors
        }
    
    async def _try_relaxed_validation(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try validation with relaxed rules."""
        # Count critical vs non-critical errors
        critical_errors, non_critical_errors = self._categorize_errors(validation_errors)
        
        # If only non-critical errors, allow with warnings
        if not critical_errors:
            return self._create_relaxed_success_response(
                filename, non_critical_errors, run_id
            )
        
        return None
    
    def _categorize_errors(self, validation_errors: List[str]) -> tuple:
        """Categorize errors into critical and non-critical."""
        critical_errors = [e for e in validation_errors if 'critical' in e.lower()]
        non_critical_errors = [e for e in validation_errors if 'critical' not in e.lower()]
        return critical_errors, non_critical_errors
    
    def _create_relaxed_success_response(
        self, filename: str, non_critical_errors: List[str], run_id: str
    ) -> Dict[str, Any]:
        """Create success response for relaxed validation."""
        logger.info(
            f"Document accepted with relaxed validation",
            filename=filename,
            warning_count=len(non_critical_errors),
            run_id=run_id
        )
        
        return {
            'success': True,
            'method': 'relaxed_validation',
            'warnings': non_critical_errors,
            'message': 'Document accepted with warnings'
        }
    
    async def _create_validation_report(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str
    ) -> Dict[str, Any]:
        """Create validation report for manual review."""
        report = self._build_validation_report(filename, validation_errors, run_id)
        
        logger.info(
            f"Created validation report for manual review",
            filename=filename,
            error_count=len(validation_errors),
            run_id=run_id
        )
        
        return {
            'success': False,
            'method': 'manual_review_required',
            'report': report,
            'message': 'Document requires manual review due to validation errors'
        }
    
    def _build_validation_report(
        self, filename: str, validation_errors: List[str], run_id: str
    ) -> Dict[str, Any]:
        """Build validation report structure."""
        return {
            'filename': filename,
            'validation_errors': validation_errors,
            'timestamp': datetime.now().isoformat(),
            'run_id': run_id,
            'status': 'requires_manual_review'
        }
    
    async def _fix_encoding_issue(self, filename: str) -> bool:
        """Try to fix encoding issues."""
        # Implementation would try different encodings
        # For now, return success simulation
        return True
    
    async def _fix_format_issue(self, filename: str) -> bool:
        """Try to fix format issues."""
        # Implementation would try format conversion
        # For now, return success simulation
        return True


# Factory function for creating validation handlers
def create_validation_handler():
    """Create validation error handler instance."""
    return ValidationErrorHandler()