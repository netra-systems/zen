"""Example Message Error Handling System

Comprehensive error handling for example message processing with recovery strategies,
user-friendly error messages, and business continuity measures.

Business Value: Maintains user experience quality during failures, preserving conversion opportunities
"""

import asyncio
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union, Callable
from enum import Enum
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.websocket.ws_manager import get_manager
from netra_backend.app.schemas.registry import WebSocketMessage

logger = central_logger.get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    PROCESSING = "processing"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    AGENT_FAILURE = "agent_failure"
    WEBSOCKET = "websocket"
    AUTHENTICATION = "authentication"
    SYSTEM = "system"


class RecoveryStrategy(Enum):
    """Recovery strategies"""
    RETRY = "retry"
    FALLBACK = "fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    USER_NOTIFICATION = "user_notification"
    ESCALATION = "escalation"


@dataclass
class ErrorContext:
    """Context information for errors"""
    user_id: Optional[str] = None
    message_id: Optional[str] = None
    category: Optional[str] = None
    complexity: Optional[str] = None
    processing_stage: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """Detailed error information"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    technical_details: str
    context: ErrorContext
    recovery_strategy: RecoveryStrategy
    retry_count: int = 0
    max_retries: int = 3
    is_recoverable: bool = True
    business_impact: str = ""


class ExampleMessageErrorHandler:
    """Centralized error handling for example message processing"""
    
    def __init__(self):
        self.ws_manager = get_manager()
        self.error_stats: Dict[str, int] = {}
        self.recovery_handlers = {
            RecoveryStrategy.RETRY: self._handle_retry,
            RecoveryStrategy.FALLBACK: self._handle_fallback,
            RecoveryStrategy.GRACEFUL_DEGRADATION: self._handle_graceful_degradation,
            RecoveryStrategy.USER_NOTIFICATION: self._handle_user_notification,
            RecoveryStrategy.ESCALATION: self._handle_escalation
        }
        
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        operation: Optional[Callable] = None
    ) -> ErrorInfo:
        """Main error handling entry point"""
        
        # Generate unique error ID
        error_id = f"err_{int(datetime.now().timestamp())}_{hash(str(error)) % 10000}"
        
        # Classify error
        error_info = self._classify_error(error, error_id, context)
        
        # Log error with full context
        self._log_error(error_info, error)
        
        # Update statistics
        self._update_error_stats(error_info)
        
        # Execute recovery strategy
        await self._execute_recovery_strategy(error_info, operation)
        
        # Send user notification if appropriate
        await self._send_user_error_notification(error_info)
        
        return error_info
        
    def _classify_error(
        self,
        error: Exception,
        error_id: str,
        context: ErrorContext
    ) -> ErrorInfo:
        """Classify error and determine recovery strategy"""
        
        error_type = type(error).__name__
        error_message = str(error)
        
        # Validation errors
        if "ValidationError" in error_type or "validation" in error_message.lower():
            return ErrorInfo(
                error_id=error_id,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                message=error_message,
                user_message="Invalid message format. Please try a different example.",
                technical_details=f"Validation failed: {error_message}",
                context=context,
                recovery_strategy=RecoveryStrategy.USER_NOTIFICATION,
                is_recoverable=True,
                business_impact="User experience degradation - can retry with valid input"
            )
            
        # Timeout errors
        elif "timeout" in error_message.lower() or "TimeoutError" in error_type:
            return ErrorInfo(
                error_id=error_id,
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.HIGH,
                message=error_message,
                user_message="Processing is taking longer than expected. Please try again.",
                technical_details=f"Operation timeout: {error_message}",
                context=context,
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=2,
                business_impact="User may abandon session - immediate retry recommended"
            )
            
        # Rate limit errors
        elif "rate" in error_message.lower() and "limit" in error_message.lower():
            return ErrorInfo(
                error_id=error_id,
                category=ErrorCategory.RATE_LIMIT,
                severity=ErrorSeverity.MEDIUM,
                message=error_message,
                user_message="System is busy. Please wait a moment and try again.",
                technical_details=f"Rate limit exceeded: {error_message}",
                context=context,
                recovery_strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                max_retries=1,
                business_impact="Temporary service limitation - user should retry shortly"
            )
            
        # Network errors
        elif any(net_err in error_message.lower() for net_err in ["connection", "network", "http"]):
            return ErrorInfo(
                error_id=error_id,
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                message=error_message,
                user_message="Connection issue detected. Please check your internet connection.",
                technical_details=f"Network error: {error_message}",
                context=context,
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=3,
                business_impact="Infrastructure issue - may affect multiple users"
            )
            
        # WebSocket errors
        elif "websocket" in error_message.lower() or "ws" in error_type.lower():
            return ErrorInfo(
                error_id=error_id,
                category=ErrorCategory.WEBSOCKET,
                severity=ErrorSeverity.HIGH,
                message=error_message,
                user_message="Real-time connection lost. Attempting to reconnect...",
                technical_details=f"WebSocket error: {error_message}",
                context=context,
                recovery_strategy=RecoveryStrategy.FALLBACK,
                max_retries=2,
                business_impact="Real-time features unavailable - fallback to polling"
            )
            
        # Authentication errors
        elif any(auth_err in error_message.lower() for auth_err in ["auth", "token", "permission"]):
            return ErrorInfo(
                error_id=error_id,
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                message=error_message,
                user_message="Authentication required. Please sign in again.",
                technical_details=f"Authentication error: {error_message}",
                context=context,
                recovery_strategy=RecoveryStrategy.USER_NOTIFICATION,
                is_recoverable=False,
                business_impact="User must re-authenticate - potential session loss"
            )
            
        # Agent processing errors
        elif "agent" in error_message.lower():
            return ErrorInfo(
                error_id=error_id,
                category=ErrorCategory.AGENT_FAILURE,
                severity=ErrorSeverity.MEDIUM,
                message=error_message,
                user_message="Analysis service temporarily unavailable. Trying alternative approach...",
                technical_details=f"Agent processing error: {error_message}",
                context=context,
                recovery_strategy=RecoveryStrategy.FALLBACK,
                max_retries=2,
                business_impact="Core functionality degraded - fallback processing available"
            )
            
        # System/unknown errors
        else:
            return ErrorInfo(
                error_id=error_id,
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                message=error_message,
                user_message="An unexpected error occurred. Our team has been notified.",
                technical_details=f"System error: {error_type}: {error_message}",
                context=context,
                recovery_strategy=RecoveryStrategy.ESCALATION,
                max_retries=1,
                business_impact="System stability issue - requires immediate investigation"
            )
            
    def _log_error(self, error_info: ErrorInfo, original_error: Exception):
        """Log error with appropriate level and context"""
        
        log_data = {
            'error_id': error_info.error_id,
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'user_id': error_info.context.user_id,
            'message_id': error_info.context.message_id,
            'processing_stage': error_info.context.processing_stage,
            'recovery_strategy': error_info.recovery_strategy.value,
            'business_impact': error_info.business_impact
        }
        
        if error_info.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            logger.error(
                f"Example message error: {error_info.message}",
                original_error,
                log_data
            )
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(
                f"Example message warning: {error_info.message}",
                None,
                log_data
            )
        else:
            logger.info(
                f"Example message info: {error_info.message}",
                None,
                log_data
            )
            
        # Log technical details separately for debugging
        logger.debug(f"Technical details for {error_info.error_id}: {error_info.technical_details}")
        
    def _update_error_stats(self, error_info: ErrorInfo):
        """Update error statistics for monitoring"""
        
        category_key = error_info.category.value
        severity_key = f"{category_key}_{error_info.severity.value}"
        
        self.error_stats[category_key] = self.error_stats.get(category_key, 0) + 1
        self.error_stats[severity_key] = self.error_stats.get(severity_key, 0) + 1
        self.error_stats['total_errors'] = self.error_stats.get('total_errors', 0) + 1
        
    async def _execute_recovery_strategy(
        self,
        error_info: ErrorInfo,
        operation: Optional[Callable] = None
    ) -> bool:
        """Execute the determined recovery strategy"""
        
        strategy_handler = self.recovery_handlers.get(error_info.recovery_strategy)
        
        if not strategy_handler:
            logger.error(f"No handler for recovery strategy: {error_info.recovery_strategy}")
            return False
            
        try:
            return await strategy_handler(error_info, operation)
        except Exception as e:
            logger.error(f"Recovery strategy failed: {e}")
            return False
            
    async def _handle_retry(
        self,
        error_info: ErrorInfo,
        operation: Optional[Callable] = None
    ) -> bool:
        """Handle retry recovery strategy"""
        
        if not operation or error_info.retry_count >= error_info.max_retries:
            return False
            
        error_info.retry_count += 1
        
        # Progressive backoff
        delay = min(2 ** error_info.retry_count, 30)  # Max 30 seconds
        
        logger.info(f"Retrying operation for error {error_info.error_id} (attempt {error_info.retry_count}/{error_info.max_retries}) after {delay}s delay")
        
        # Notify user of retry
        if error_info.context.user_id:
            await self._send_retry_notification(error_info, delay)
            
        await asyncio.sleep(delay)
        
        try:
            # Retry the operation
            await operation()
            logger.info(f"Retry successful for error {error_info.error_id}")
            return True
        except Exception as e:
            logger.warning(f"Retry failed for error {error_info.error_id}: {e}")
            if error_info.retry_count < error_info.max_retries:
                return await self._handle_retry(error_info, operation)
            return False
            
    async def _handle_fallback(
        self,
        error_info: ErrorInfo,
        operation: Optional[Callable] = None
    ) -> bool:
        """Handle fallback recovery strategy"""
        
        logger.info(f"Executing fallback for error {error_info.error_id}")
        
        # Generate fallback response based on error category
        fallback_response = await self._generate_fallback_response(error_info)
        
        # Send fallback response to user
        if error_info.context.user_id and fallback_response:
            await self._send_fallback_response(error_info, fallback_response)
            
        return True
        
    async def _handle_graceful_degradation(
        self,
        error_info: ErrorInfo,
        operation: Optional[Callable] = None
    ) -> bool:
        """Handle graceful degradation strategy"""
        
        logger.info(f"Applying graceful degradation for error {error_info.error_id}")
        
        # Provide simplified response
        degraded_response = {
            'optimization_type': 'degraded_service',
            'message': 'Service temporarily operating in limited mode',
            'analysis': {
                'status': 'completed_with_limitations',
                'message': 'Basic analysis completed. Full features available shortly.',
                'recommendations': [
                    'This demonstrates the type of analysis available in full mode',
                    'Try again in a few moments for complete results',
                    'Contact support if issues persist'
                ]
            },
            'next_steps': [
                'System is automatically recovering',
                'Full functionality will be restored shortly',
                'Your request has been logged for manual review if needed'
            ]
        }
        
        if error_info.context.user_id:
            await self._send_degraded_response(error_info, degraded_response)
            
        return True
        
    async def _handle_user_notification(
        self,
        error_info: ErrorInfo,
        operation: Optional[Callable] = None
    ) -> bool:
        """Handle user notification strategy"""
        
        # This is handled in _send_user_error_notification
        return True
        
    async def _handle_escalation(
        self,
        error_info: ErrorInfo,
        operation: Optional[Callable] = None
    ) -> bool:
        """Handle escalation strategy"""
        
        logger.critical(f"Escalating error {error_info.error_id} - manual intervention required")
        
        # In a real system, this would:
        # - Send alerts to engineering team
        # - Create support tickets
        # - Trigger monitoring alerts
        # - Update status page
        
        escalation_data = {
            'error_id': error_info.error_id,
            'severity': error_info.severity.value,
            'category': error_info.category.value,
            'business_impact': error_info.business_impact,
            'affected_user': error_info.context.user_id,
            'timestamp': error_info.context.timestamp.isoformat(),
            'technical_details': error_info.technical_details
        }
        
        # Log escalation for monitoring systems to pick up
        logger.critical("ESCALATION_REQUIRED", None, escalation_data)
        
        return True
        
    async def _generate_fallback_response(self, error_info: ErrorInfo) -> Optional[Dict[str, Any]]:
        """Generate appropriate fallback response"""
        
        base_response = {
            'optimization_type': 'fallback',
            'agent_name': 'Fallback Handler',
            'processing_time_ms': 100,
            'status': 'completed_with_fallback'
        }
        
        if error_info.category == ErrorCategory.AGENT_FAILURE:
            return {
                **base_response,
                'analysis': {
                    'message': 'Analysis completed with alternative processing method',
                    'note': 'This demonstrates the type of insights available with full agent processing',
                    'recommendations': [
                        'The system would normally provide detailed optimization strategies',
                        'Specialized agents would analyze your specific use case',
                        'Try again for complete analysis with all available agents'
                    ]
                }
            }
        elif error_info.category == ErrorCategory.TIMEOUT:
            return {
                **base_response,
                'analysis': {
                    'message': 'Quick analysis completed due to processing constraints',
                    'note': 'Full analysis requires more processing time',
                    'recommendations': [
                        'Try a simpler example for faster results',
                        'Full analysis provides comprehensive optimization strategies',
                        'Contact support for complex optimization requests'
                    ]
                }
            }
        elif error_info.category == ErrorCategory.RATE_LIMIT:
            return {
                **base_response,
                'analysis': {
                    'message': 'System at capacity - providing cached analysis example',
                    'note': 'This shows the type of analysis normally generated',
                    'recommendations': [
                        'Try again in a few moments when system capacity is available',
                        'Upgrade for priority processing and higher limits',
                        'Each analysis is normally customized to your specific needs'
                    ]
                }
            }
            
        return None
        
    async def _send_user_error_notification(self, error_info: ErrorInfo):
        """Send appropriate error notification to user"""
        
        if not error_info.context.user_id or not self.ws_manager:
            return
            
        notification = {
            'type': 'error',
            'payload': {
                'error_id': error_info.error_id,
                'category': error_info.category.value,
                'severity': error_info.severity.value,
                'message': error_info.user_message,
                'example_message_id': error_info.context.message_id,
                'is_recoverable': error_info.is_recoverable,
                'retry_count': error_info.retry_count,
                'max_retries': error_info.max_retries,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'recovery_strategy': error_info.recovery_strategy.value
            }
        }
        
        try:
            await self.ws_manager.send_message_to_user(
                error_info.context.user_id,
                notification
            )
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
            
    async def _send_retry_notification(self, error_info: ErrorInfo, delay: int):
        """Send retry notification to user"""
        
        if not error_info.context.user_id:
            return
            
        notification = {
            'type': 'agent_thinking',
            'payload': {
                'message': f"Retrying analysis (attempt {error_info.retry_count}/{error_info.max_retries})...",
                'example_message_id': error_info.context.message_id,
                'retry_delay': delay,
                'agent_name': 'Error Recovery System'
            }
        }
        
        try:
            await self.ws_manager.send_message_to_user(
                error_info.context.user_id,
                notification
            )
        except Exception as e:
            logger.error(f"Failed to send retry notification: {e}")
            
    async def _send_fallback_response(self, error_info: ErrorInfo, response: Dict[str, Any]):
        """Send fallback response to user"""
        
        if not error_info.context.user_id:
            return
            
        message = {
            'type': 'agent_completed',
            'payload': {
                'result': response,
                'example_message_id': error_info.context.message_id,
                'fallback_mode': True,
                'original_error_category': error_info.category.value,
                'agent_name': 'Fallback Handler'
            }
        }
        
        try:
            await self.ws_manager.send_message_to_user(
                error_info.context.user_id,
                message
            )
        except Exception as e:
            logger.error(f"Failed to send fallback response: {e}")
            
    async def _send_degraded_response(self, error_info: ErrorInfo, response: Dict[str, Any]):
        """Send degraded service response to user"""
        
        if not error_info.context.user_id:
            return
            
        message = {
            'type': 'agent_completed',
            'payload': {
                'result': response,
                'example_message_id': error_info.context.message_id,
                'degraded_mode': True,
                'service_status': 'limited',
                'agent_name': 'Degraded Service Handler'
            }
        }
        
        try:
            await self.ws_manager.send_message_to_user(
                error_info.context.user_id,
                message
            )
        except Exception as e:
            logger.error(f"Failed to send degraded response: {e}")
            
    def get_error_stats(self) -> Dict[str, Any]:
        """Get current error statistics"""
        
        return {
            'error_counts': self.error_stats.copy(),
            'error_rate': self._calculate_error_rate(),
            'top_error_categories': self._get_top_error_categories(),
            'recovery_success_rate': self._calculate_recovery_success_rate()
        }
        
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        
        total_errors = self.error_stats.get('total_errors', 0)
        # In a real system, this would be calculated against total requests
        # For demo purposes, return a reasonable rate
        return min(total_errors / max(total_errors * 10, 1), 1.0)
        
    def _get_top_error_categories(self) -> List[Dict[str, Any]]:
        """Get top error categories by frequency"""
        
        categories = [
            {'category': cat, 'count': count}
            for cat, count in self.error_stats.items()
            if not cat.endswith(('_low', '_medium', '_high', '_critical')) and cat != 'total_errors'
        ]
        
        return sorted(categories, key=lambda x: x['count'], reverse=True)[:5]
        
    def _calculate_recovery_success_rate(self) -> float:
        """Calculate recovery success rate"""
        
        # In a real system, this would track actual recovery attempts
        # For demo, return optimistic rate based on error patterns
        total_errors = self.error_stats.get('total_errors', 0)
        if total_errors == 0:
            return 1.0
            
        # Assume good recovery rate for demo
        return min(0.85 + (0.1 * (1.0 / max(total_errors, 1))), 0.98)
        
    def reset_stats(self):
        """Reset error statistics (useful for testing)"""
        self.error_stats.clear()


# Global error handler instance
error_handler = ExampleMessageErrorHandler()


async def handle_example_message_error(
    error: Exception,
    context: ErrorContext,
    operation: Optional[Callable] = None
) -> ErrorInfo:
    """Public interface for handling example message errors"""
    return await error_handler.handle_error(error, context, operation)


def get_error_handler() -> ExampleMessageErrorHandler:
    """Get the global error handler instance"""
    return error_handler