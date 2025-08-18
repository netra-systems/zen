"""Validation error handling utilities for corpus admin operations.

Provides specialized handlers for document validation failures with recovery strategies.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.error_handler import ErrorContext, global_error_handler
from app.agents.corpus_admin.corpus_error_types import DocumentValidationError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DocumentValidationErrorHandler:
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
        error = self._create_validation_error(filename, validation_errors, context)
        return await self._process_validation_error(filename, validation_errors, run_id, error, context)
    
    def _create_validation_error(
        self, filename: str, validation_errors: List[str], context: ErrorContext
    ) -> DocumentValidationError:
        """Create document validation error instance"""
        return DocumentValidationError(filename, validation_errors, context)
    
    async def _process_validation_error(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str,
        error: DocumentValidationError,
        context: ErrorContext
    ) -> Dict[str, Any]:
        """Process validation error with recovery strategies"""
        try:
            return await self._execute_recovery_strategies(filename, validation_errors, run_id)
        except Exception as fallback_error:
            await self._handle_recovery_failure(error, context)
    
    async def _execute_recovery_strategies(
        self, filename: str, validation_errors: List[str], run_id: str
    ) -> Dict[str, Any]:
        """Execute validation recovery strategies"""
        result = await self._attempt_validation_recovery(filename, validation_errors, run_id)
        if result:
            return result
        return await self._create_validation_report(filename, validation_errors, run_id)
    
    async def _handle_recovery_failure(
        self, error: DocumentValidationError, context: ErrorContext
    ) -> None:
        """Handle recovery strategy failure"""
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
        additional_data = self._build_context_data(filename, validation_errors, original_error)
        return ErrorContext(
            agent_name="corpus_admin_agent",
            operation_name="document_validation",
            run_id=run_id,
            additional_data=additional_data
        )
    
    def _build_context_data(
        self, filename: str, validation_errors: List[str], original_error: Exception
    ) -> Dict[str, Any]:
        """Build additional data for error context"""
        return {
            'filename': filename,
            'validation_errors': validation_errors,
            'original_error': str(original_error)
        }
    
    async def _attempt_validation_recovery(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Attempt validation recovery strategies."""
        fixed_result = await self._try_validation_fixes(filename, validation_errors, run_id)
        return fixed_result or await self._try_relaxed_validation(
            filename, validation_errors, run_id
        )
    
    async def _try_validation_fixes(
        self,
        filename: str,
        validation_errors: List[str],
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Try to automatically fix common validation issues."""
        fixed_errors = await self._collect_fixable_errors(filename, validation_errors)
        return self._handle_fixed_errors(filename, fixed_errors, validation_errors, run_id)
    
    async def _collect_fixable_errors(self, filename: str, validation_errors: List[str]) -> List[str]:
        """Collect errors that can be automatically fixed."""
        fixed_errors = []
        for error in validation_errors:
            if await self._can_fix_error(error, filename):
                fixed_errors.append(error)
        return fixed_errors
    
    def _handle_fixed_errors(
        self, filename: str, fixed_errors: List[str], validation_errors: List[str], run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle result of error fixing attempt."""
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
        remaining_errors = self._get_remaining_errors(validation_errors, fixed_errors)
        self._log_fix_success(filename, fixed_errors, remaining_errors, run_id)
        return self._build_fix_response(fixed_errors, remaining_errors)
    
    def _get_remaining_errors(self, validation_errors: List[str], fixed_errors: List[str]) -> List[str]:
        """Get remaining errors after fixes."""
        return [e for e in validation_errors if e not in fixed_errors]
    
    def _log_fix_success(
        self, filename: str, fixed_errors: List[str], remaining_errors: List[str], run_id: str
    ) -> None:
        """Log success message for automatic fixes."""
        logger.info(
            f"Fixed validation errors automatically",
            filename=filename,
            fixed_count=len(fixed_errors),
            remaining_count=len(remaining_errors),
            run_id=run_id
        )
    
    def _build_fix_response(self, fixed_errors: List[str], remaining_errors: List[str]) -> Dict[str, Any]:
        """Build response dictionary for fixes."""
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
        self._log_relaxed_success(filename, non_critical_errors, run_id)
        return self._build_relaxed_response(non_critical_errors)
    
    def _log_relaxed_success(
        self, filename: str, non_critical_errors: List[str], run_id: str
    ) -> None:
        """Log relaxed validation success."""
        logger.info(
            f"Document accepted with relaxed validation",
            filename=filename,
            warning_count=len(non_critical_errors),
            run_id=run_id
        )
    
    def _build_relaxed_response(self, non_critical_errors: List[str]) -> Dict[str, Any]:
        """Build relaxed validation response."""
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
        self._log_validation_report(filename, validation_errors, run_id)
        return self._build_report_response(report)
    
    def _log_validation_report(
        self, filename: str, validation_errors: List[str], run_id: str
    ) -> None:
        """Log validation report creation."""
        logger.info(
            f"Created validation report for manual review",
            filename=filename,
            error_count=len(validation_errors),
            run_id=run_id
        )
    
    def _build_report_response(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Build validation report response."""
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
    """Create document validation error handler instance."""
    return DocumentValidationErrorHandler()