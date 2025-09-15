"""SSOT Sentry Integration Module

**CRITICAL:** Single Source of Truth for Sentry error tracking and performance monitoring

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Proactive error detection and resolution
- Value Impact: +$50K ARR from improved system reliability and faster incident response
- Revenue Impact: Prevents customer churn due to undetected errors

**MANDATORY**: All Sentry integration MUST use this unified system.
Provides comprehensive error tracking, performance monitoring, and security filtering.

Architecture:
- SSOT configuration through unified config system
- Security-first design with PII filtering
- Environment-aware configuration
- Integration with existing observability stack
- FastAPI middleware integration
- Comprehensive error context and user tracking
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    sentry_sdk = None

from shared.isolated_environment import get_env
from netra_backend.app.schemas.config import AppConfig


class SentryIntegrationError(Exception):
    """Raised when Sentry integration encounters an error."""
    pass


class SentryManager:
    """SSOT Sentry Manager for error tracking and performance monitoring.
    
    Provides unified Sentry integration following SSOT patterns and enterprise security requirements.
    """
    
    def __init__(self, config: AppConfig):
        """Initialize Sentry manager with configuration.
        
        Args:
            config: Application configuration with Sentry settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._env = get_env()
        
        # Security patterns for PII detection
        self._pii_patterns = [
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 'email'),  # Email
            (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), 'ssn'),  # SSN
            (re.compile(r'\b\d{4}-\d{4}-\d{4}-\d{4}\b'), 'credit_card'),  # Credit card
            (re.compile(r'\bpassword[=:]\s*[^\s]+', re.IGNORECASE), 'password'),  # Password in URL/log format
            (re.compile(r'\bapi[_-]?key[=:]\s*[^\s]+', re.IGNORECASE), 'api_key'),  # API key in URL/log format
            (re.compile(r'\btoken[=:]\s*[^\s]+', re.IGNORECASE), 'token'),  # Token in URL/log format
        ]
        
        # Sensitive field names to redact (for dict keys)
        self._sensitive_fields = {
            'password', 'pass', 'pwd', 'secret', 'token', 'key', 'api_key', 'apikey', 
            'auth', 'authorization', 'credential', 'cred', 'private', 'priv'
        }
        
        # URL patterns to ignore for performance
        self._ignore_url_patterns = [
            re.compile(pattern) for pattern in [
                r'^/health/?$',
                r'^/metrics/?$',
                r'^/docs/?$',
                r'^/openapi\.json$',
                r'^/favicon\.ico$',
                r'^/static/',
                r'^/_internal/',
            ]
        ]
    
    def initialize(self) -> bool:
        """Initialize Sentry SDK with configuration.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._initialized:
            self.logger.debug("Sentry already initialized")
            return True
            
        if not SENTRY_AVAILABLE:
            self.logger.warning("Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking")
            return False
            
        if not self.config.sentry_enabled:
            self.logger.info("Sentry integration disabled by configuration")
            return False
            
        if not self.config.sentry_dsn:
            self.logger.warning("Sentry DSN not configured - error tracking disabled")
            return False
        
        try:
            # Configure Sentry integrations
            integrations = self._get_integrations()
            
            # Initialize Sentry SDK
            sentry_sdk.init(
                dsn=self.config.sentry_dsn,
                integrations=integrations,
                traces_sample_rate=self.config.sentry_traces_sample_rate,
                profiles_sample_rate=self.config.sentry_profiles_sample_rate,
                environment=self._get_environment(),
                release=self.config.sentry_release,
                server_name=self.config.sentry_server_name,
                attach_stacktrace=self.config.sentry_attach_stacktrace,
                send_default_pii=self.config.sentry_send_default_pii,
                max_breadcrumbs=self.config.sentry_max_breadcrumbs,
                debug=self.config.sentry_debug,
                before_send=self._before_send_filter,
                before_send_transaction=self._before_send_transaction_filter if self.config.sentry_before_send_transaction else None,
            )
            
            # Set global tags
            self._set_global_tags()
            
            self._initialized = True
            self.logger.info(f"Sentry initialized successfully (environment: {self._get_environment()})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Sentry: {e}")
            return False
    
    def _get_integrations(self) -> List[Any]:
        """Get Sentry integrations based on configuration.
        
        Returns:
            List of Sentry integration instances
        """
        integrations = []
        
        # FastAPI integration
        integrations.append(FastApiIntegration(
            auto_enable=True,
            failed_request_status_codes=[400, 401, 403, 404, 413, 429, 500, 502, 503, 504]
        ))
        
        # Database integration
        integrations.append(SqlalchemyIntegration())
        
        # Redis integration
        integrations.append(RedisIntegration())
        
        # Asyncio integration
        integrations.append(AsyncioIntegration())
        
        # Logging integration with filtering
        integrations.append(LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        ))
        
        return integrations
    
    def _get_environment(self) -> str:
        """Get environment for Sentry tagging.
        
        Returns:
            Environment string for Sentry
        """
        if self.config.sentry_environment:
            return self.config.sentry_environment
            
        # Auto-detect environment
        env_name = self.config.environment.lower()
        if env_name in ['production', 'prod']:
            return 'production'
        elif env_name in ['staging', 'stage']:
            return 'staging'
        elif env_name in ['development', 'dev']:
            return 'development'
        elif env_name in ['testing', 'test']:
            return 'testing'
        else:
            return env_name
    
    def _set_global_tags(self) -> None:
        """Set global Sentry tags for context."""
        try:
            sentry_sdk.set_tag("service", "netra-backend")
            sentry_sdk.set_tag("environment", self._get_environment())
            sentry_sdk.set_tag("app_name", self.config.app_name)
            
            # Add Cloud Run context if available
            if self.config.k_service:
                sentry_sdk.set_tag("cloud_run_service", self.config.k_service)
            if self.config.k_revision:
                sentry_sdk.set_tag("cloud_run_revision", self.config.k_revision)
                
            # Add PR context if available
            if self.config.pr_number:
                sentry_sdk.set_tag("pr_number", self.config.pr_number)
                
        except Exception as e:
            self.logger.warning(f"Failed to set Sentry global tags: {e}")
    
    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize data to remove PII and sensitive information.
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data with PII removed
        """
        if isinstance(data, str):
            sanitized = data
            for pattern, _ in self._pii_patterns:
                sanitized = pattern.sub('[REDACTED]', sanitized)
            return sanitized
        elif isinstance(data, dict):
            sanitized_dict = {}
            for k, v in data.items():
                # Check if key is sensitive
                if isinstance(k, str) and k.lower() in self._sensitive_fields:
                    sanitized_dict[k] = '[REDACTED]'
                else:
                    sanitized_dict[k] = self._sanitize_data(v)
            return sanitized_dict
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data
    
    def _before_send_filter(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter events before sending to Sentry.
        
        Args:
            event: Sentry event data
            hint: Additional context
            
        Returns:
            Filtered event or None to drop the event
        """
        try:
            # Check for ignored error types
            if 'exception' in event:
                for exc_info in event['exception'].get('values', []):
                    exc_type = exc_info.get('type', '')
                    if exc_type in self.config.sentry_ignore_errors:
                        return None
            
            # Sanitize PII
            if not self.config.sentry_send_default_pii:
                event = self._sanitize_data(event)
            
            # Add custom context
            event = self._add_custom_context(event)
            
            return event
            
        except Exception as e:
            self.logger.warning(f"Error in Sentry before_send filter: {e}")
            return event
    
    def _before_send_transaction_filter(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter transaction events before sending to Sentry.
        
        Args:
            event: Sentry transaction event
            hint: Additional context
            
        Returns:
            Filtered event or None to drop the transaction
        """
        try:
            # Get transaction name
            transaction_name = event.get('transaction', '')
            
            # Check ignore patterns
            for pattern in self._ignore_url_patterns:
                if pattern.search(transaction_name):
                    return None
            
            # Check configured ignore list
            for ignored in self.config.sentry_ignore_transactions:
                if ignored in transaction_name:
                    return None
            
            return event
            
        except Exception as e:
            self.logger.warning(f"Error in Sentry transaction filter: {e}")
            return event
    
    def _add_custom_context(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Add custom context to Sentry events.
        
        Args:
            event: Sentry event
            
        Returns:
            Event with additional context
        """
        try:
            # Add system context
            if 'contexts' not in event:
                event['contexts'] = {}
                
            event['contexts']['netra'] = {
                'service': 'netra-backend',
                'version': self.config.sentry_release or 'unknown',
                'environment': self._get_environment(),
            }
            
            # Add configuration context (sanitized)
            event['contexts']['config'] = {
                'redis_mode': self.config.redis_mode,
                'clickhouse_mode': self.config.clickhouse_mode,
                'llm_mode': self.config.llm_mode,
                'auth_service_enabled': self.config.auth_service_enabled,
                'otel_enabled': self.config.otel_enabled,
            }
            
            return event
            
        except Exception as e:
            self.logger.warning(f"Error adding custom context to Sentry event: {e}")
            return event
    
    def capture_exception(self, error: Exception, **kwargs) -> Optional[str]:
        """Capture an exception in Sentry.
        
        Args:
            error: Exception to capture
            **kwargs: Additional context
            
        Returns:
            Event ID if captured, None otherwise
        """
        if not self._initialized:
            return None
            
        try:
            with sentry_sdk.push_scope() as scope:
                # Add additional context
                for key, value in kwargs.items():
                    scope.set_extra(key, value)
                
                return sentry_sdk.capture_exception(error)
                
        except Exception as e:
            self.logger.warning(f"Failed to capture exception in Sentry: {e}")
            return None
    
    def capture_message(self, message: str, level: str = 'info', **kwargs) -> Optional[str]:
        """Capture a message in Sentry.
        
        Args:
            message: Message to capture
            level: Log level
            **kwargs: Additional context
            
        Returns:
            Event ID if captured, None otherwise
        """
        if not self._initialized:
            return None
            
        try:
            with sentry_sdk.push_scope() as scope:
                # Add additional context
                for key, value in kwargs.items():
                    scope.set_extra(key, value)
                
                return sentry_sdk.capture_message(message, level=level)
                
        except Exception as e:
            self.logger.warning(f"Failed to capture message in Sentry: {e}")
            return None
    
    def set_user_context(self, user_id: Optional[str] = None, email: Optional[str] = None, **kwargs) -> None:
        """Set user context for Sentry.
        
        Args:
            user_id: User identifier
            email: User email (will be sanitized if PII disabled)
            **kwargs: Additional user context
        """
        if not self._initialized:
            return
            
        try:
            user_data = {}
            
            if user_id:
                user_data['id'] = user_id
                
            if email and self.config.sentry_send_default_pii:
                user_data['email'] = email
            elif email:
                user_data['email'] = '[REDACTED]'
                
            user_data.update(kwargs)
            
            sentry_sdk.set_user(user_data)
            
        except Exception as e:
            self.logger.warning(f"Failed to set user context in Sentry: {e}")
    
    def set_tag(self, key: str, value: str) -> None:
        """Set a tag in Sentry.
        
        Args:
            key: Tag key
            value: Tag value
        """
        if not self._initialized:
            return
            
        try:
            sentry_sdk.set_tag(key, value)
        except Exception as e:
            self.logger.warning(f"Failed to set Sentry tag: {e}")
    
    def set_extra(self, key: str, value: Any) -> None:
        """Set extra context in Sentry.
        
        Args:
            key: Context key
            value: Context value
        """
        if not self._initialized:
            return
            
        try:
            sentry_sdk.set_extra(key, value)
        except Exception as e:
            self.logger.warning(f"Failed to set Sentry extra: {e}")
    
    @asynccontextmanager
    async def transaction(self, name: str, op: str = "request"):
        """Create a Sentry transaction context.
        
        Args:
            name: Transaction name
            op: Operation type
            
        Yields:
            Transaction context
        """
        if not self._initialized:
            yield None
            return
            
        try:
            with sentry_sdk.start_transaction(name=name, op=op) as transaction:
                yield transaction
        except Exception as e:
            self.logger.warning(f"Error in Sentry transaction: {e}")
            yield None
    
    def add_breadcrumb(self, message: str, category: str = 'default', level: str = 'info', **kwargs) -> None:
        """Add a breadcrumb to Sentry.
        
        Args:
            message: Breadcrumb message
            category: Breadcrumb category
            level: Log level
            **kwargs: Additional data
        """
        if not self._initialized:
            return
            
        try:
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=kwargs
            )
        except Exception as e:
            self.logger.warning(f"Failed to add Sentry breadcrumb: {e}")
    
    def is_initialized(self) -> bool:
        """Check if Sentry is initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
    
    def get_last_event_id(self) -> Optional[str]:
        """Get the last event ID from Sentry.
        
        Returns:
            Last event ID or None
        """
        if not self._initialized:
            return None
            
        try:
            return sentry_sdk.last_event_id()
        except Exception as e:
            self.logger.warning(f"Failed to get last Sentry event ID: {e}")
            return None


# SSOT Sentry Manager Instance
_sentry_manager: Optional[SentryManager] = None


def get_sentry_manager(config: Optional[AppConfig] = None) -> Optional[SentryManager]:
    """Get the SSOT Sentry manager instance.
    
    Args:
        config: Optional configuration (for initialization)
        
    Returns:
        Sentry manager instance or None if not available
    """
    global _sentry_manager
    
    if _sentry_manager is None and config is not None:
        _sentry_manager = SentryManager(config)
        _sentry_manager.initialize()
    
    return _sentry_manager


def initialize_sentry(config: AppConfig) -> bool:
    """Initialize SSOT Sentry integration.
    
    Args:
        config: Application configuration
        
    Returns:
        True if initialization successful, False otherwise
    """
    manager = get_sentry_manager(config)
    return manager.is_initialized() if manager else False


def capture_exception(error: Exception, **kwargs) -> Optional[str]:
    """Capture an exception using SSOT Sentry manager.
    
    Args:
        error: Exception to capture
        **kwargs: Additional context
        
    Returns:
        Event ID if captured, None otherwise
    """
    manager = get_sentry_manager()
    return manager.capture_exception(error, **kwargs) if manager else None


def capture_message(message: str, level: str = 'info', **kwargs) -> Optional[str]:
    """Capture a message using SSOT Sentry manager.
    
    Args:
        message: Message to capture
        level: Log level
        **kwargs: Additional context
        
    Returns:
        Event ID if captured, None otherwise
    """
    manager = get_sentry_manager()
    return manager.capture_message(message, level=level, **kwargs) if manager else None


def set_user_context(user_id: Optional[str] = None, email: Optional[str] = None, **kwargs) -> None:
    """Set user context using SSOT Sentry manager.
    
    Args:
        user_id: User identifier
        email: User email
        **kwargs: Additional user context
    """
    manager = get_sentry_manager()
    if manager:
        manager.set_user_context(user_id=user_id, email=email, **kwargs)


def add_breadcrumb(message: str, category: str = 'default', level: str = 'info', **kwargs) -> None:
    """Add a breadcrumb using SSOT Sentry manager.
    
    Args:
        message: Breadcrumb message
        category: Breadcrumb category
        level: Log level
        **kwargs: Additional data
    """
    manager = get_sentry_manager()
    if manager:
        manager.add_breadcrumb(message, category=category, level=level, **kwargs)