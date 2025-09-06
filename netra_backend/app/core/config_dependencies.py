"""
Configuration Dependency Mapping System

This module provides a critical safety layer to prevent accidental deletion
or modification of essential configuration values during refactoring.
It maps dependencies between configuration keys and the services that require them.

IMPORTANT: This works in conjunction with shared.configuration.central_config_validator
for comprehensive configuration management and legacy variable tracking.
"""

from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConfigImpactLevel(Enum):
    """Impact levels for configuration changes"""
    CRITICAL = "CRITICAL"  # System will fail
    HIGH = "HIGH"  # Major functionality impaired
    MEDIUM = "MEDIUM"  # Some features affected
    LOW = "LOW"  # Minor impact


class ConfigDependencyMap:
    """
    Maps configuration dependencies to prevent breaking deletions.
    This is a CRITICAL component for preventing configuration regressions.
    """
    
    # Core dependencies that MUST exist for system operation
    CRITICAL_DEPENDENCIES: Dict[str, Dict[str, Any]] = {
        "DATABASE_URL": {
            "required_by": [
                "session_service",
                "state_persistence", 
                "auth_service",
                "user_service",
                "agent_registry",
                "corpus_admin"
            ],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_requires": ["migration_plan", "approval", "staged_rollout"],
            "deletion_impact": "CRITICAL - All database operations will fail",
            "alternatives": [],
            "validation": lambda x: x and x.startswith(("postgresql://", "postgres://")),
            # Legacy information
            "legacy_status": "DEPRECATED",
            "deprecation_date": "2025-12-01",
            "removal_version": "2.0.0",
            "replacement": ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"],
            "migration_guide": "Use component-based database configuration (POSTGRES_*) instead of single DATABASE_URL. System will construct URL internally from components.",
            "auto_construct": True
        },
        
        "JWT_SECRET_KEY": {
            "required_by": [
                "auth_service",
                "backend_auth", 
                "token_validation",
                "session_management"
            ],
            "shared_across": ["netra_backend", "auth_service"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_impact": "CRITICAL - All authentication will fail",
            "alternatives": ["JWT_SECRET"],
            "validation": lambda x: x and len(x) >= 32,
            # Legacy information
            "legacy_status": "CURRENT",
            "replacement": "JWT_SECRET (deprecated)",
            "migration_guide": "JWT_SECRET_KEY is the current standard. JWT_SECRET is deprecated."
        },
        
        "ENVIRONMENT": {
            "required_by": ["all_services"],
            "fallback_allowed": True,
            "fallback_value": "development",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - Environment detection will fail",
            "valid_values": ["development", "testing", "staging", "production"],
            "validation": lambda x: x in ["development", "testing", "staging", "production"]
        },
        
        "SECRET_KEY": {
            "required_by": ["session_service", "csrf_protection", "encryption"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_impact": "CRITICAL - Session security compromised",
            "alternatives": ["APP_SECRET_KEY"],
            "validation": lambda x: x and len(x) >= 32,
            # Legacy information
            "legacy_status": "CURRENT",
            "replacement": "APP_SECRET_KEY (deprecated)",
            "migration_guide": "SECRET_KEY is the current standard. APP_SECRET_KEY is deprecated."
        },
        
        "POSTGRES_HOST": {
            "required_by": [
                "session_service",
                "state_persistence",
                "auth_service", 
                "user_service",
                "corpus_admin"
            ],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_requires": ["migration_plan", "approval", "staged_rollout"],
            "deletion_impact": "CRITICAL - Database connection will fail",
            "paired_with": ["POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"],
            "validation": lambda x: x and isinstance(x, str) and len(x) > 0
        },
        
        "POSTGRES_PORT": {
            "required_by": [
                "session_service",
                "state_persistence",
                "auth_service",
                "user_service", 
                "corpus_admin"
            ],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_requires": ["migration_plan", "approval", "staged_rollout"],
            "deletion_impact": "CRITICAL - Database connection will fail",
            "paired_with": ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"],
            "validation": lambda x: x and (isinstance(x, int) or (isinstance(x, str) and x.isdigit())) and 1 <= int(x) <= 65535
        },
        
        "POSTGRES_DB": {
            "required_by": [
                "session_service",
                "state_persistence",
                "auth_service",
                "user_service",
                "corpus_admin"
            ],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_requires": ["migration_plan", "approval", "staged_rollout"],
            "deletion_impact": "CRITICAL - Database connection will fail",
            "paired_with": ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD"],
            "validation": lambda x: x and isinstance(x, str) and len(x) > 0
        },
        
        "POSTGRES_USER": {
            "required_by": [
                "session_service",
                "state_persistence",
                "auth_service",
                "user_service",
                "corpus_admin"
            ],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_requires": ["migration_plan", "approval", "staged_rollout"],
            "deletion_impact": "CRITICAL - Database authentication will fail",
            "paired_with": ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_PASSWORD"],
            "validation": lambda x: x and isinstance(x, str) and len(x) > 0
        },
        
        "POSTGRES_PASSWORD": {
            "required_by": [
                "session_service",
                "state_persistence",
                "auth_service",
                "user_service",
                "corpus_admin"
            ],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_requires": ["migration_plan", "approval", "staged_rollout"],
            "deletion_impact": "CRITICAL - Database authentication will fail",
            "paired_with": ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER"],
            "validation": lambda x: x and isinstance(x, str) and len(x) > 0
        },
        
        "AUTH_REDIRECT_URI": {
            "required_by": [
                "oauth_service",
                "auth_callbacks",
                "login_flow"
            ],
            "shared_across": ["netra_backend", "auth_service"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_impact": "CRITICAL - OAuth login flow will fail",
            "paired_with": ["AUTH_CALLBACK_URL"],
            "validation": lambda x: x and x.startswith(("http://", "https://"))
        },
        
        "AUTH_CALLBACK_URL": {
            "required_by": [
                "oauth_service", 
                "auth_callbacks",
                "login_flow"
            ],
            "shared_across": ["netra_backend", "auth_service"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_impact": "CRITICAL - OAuth callback handling will fail",
            "paired_with": ["AUTH_REDIRECT_URI"],
            "validation": lambda x: x and x.startswith(("http://", "https://"))
        },
        
        "FRONTEND_URL": {
            "required_by": [
                "cors_configuration",
                "redirect_handling",
                "auth_callbacks",
                "websocket_origins"
            ],
            "shared_across": ["netra_backend", "auth_service", "frontend"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_impact": "CRITICAL - Cross-service communication will fail",
            "paired_with": ["BACKEND_URL"],
            "validation": lambda x: x and x.startswith(("http://", "https://"))
        },
        
        "BACKEND_URL": {
            "required_by": [
                "api_calls",
                "service_discovery",
                "auth_integration",
                "websocket_connections"
            ],
            "shared_across": ["netra_backend", "auth_service", "frontend"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_impact": "CRITICAL - Cross-service communication will fail",
            "paired_with": ["FRONTEND_URL"],
            "validation": lambda x: x and x.startswith(("http://", "https://"))
        },
        
        # OAuth Redirect URI Configuration - CRITICAL SSOT
        # See: /OAUTH_REDIRECT_URI_SSOT_ARCHITECTURE.md for complete documentation
        "OAUTH_REDIRECT_URI": {
            "required_by": [],  # DEPRECATED - DO NOT USE
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_impact": "NONE - This is DEPRECATED and should NOT be used",
            "alternatives": [],
            "validation": lambda x: False,  # Always invalid - should not be used
            # Legacy information
            "legacy_status": "DEPRECATED",
            "deprecation_date": "2025-09-05",
            "removal_version": "2.0.0",
            "replacement": "GoogleOAuthProvider.get_redirect_uri() method",
            "migration_guide": "DO NOT SET THIS. Use GoogleOAuthProvider.get_redirect_uri() as SSOT. See /auth_service/auth_core/oauth/google_oauth.py:78",
            "auto_construct": False,
            "critical_note": "This caused redirect_uri_mismatch errors. NEVER use environment variables for OAuth redirect URIs."
        },
        
        "OAUTH_CALLBACK_URL": {
            "required_by": [],  # DEPRECATED - DO NOT USE
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_impact": "NONE - This is DEPRECATED and should NOT be used",
            "alternatives": [],
            "validation": lambda x: False,  # Always invalid - should not be used
            # Legacy information
            "legacy_status": "DEPRECATED",
            "deprecation_date": "2025-09-05",
            "removal_version": "2.0.0",
            "replacement": "GoogleOAuthProvider.get_redirect_uri() method",
            "migration_guide": "DO NOT SET THIS. Use GoogleOAuthProvider.get_redirect_uri() as SSOT. See /auth_service/auth_core/oauth/google_oauth.py:78",
            "auto_construct": False,
            "critical_note": "This violates SSOT principles. NEVER use environment variables for OAuth redirect URIs."
        },
        
        "GOOGLE_OAUTH_CLIENT_ID": {
            "required_by": [
                "auth_service.oauth",
                "google_oauth_provider",
                "user_authentication",
                "oauth_authorization"
            ],
            "shared_across": ["auth_service"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_requires": ["migration_plan", "alternative_auth"],
            "deletion_impact": "CRITICAL - Google OAuth authentication will fail (503 errors)",
            "paired_with": ["GOOGLE_OAUTH_CLIENT_SECRET", "AUTH_SERVICE_URL"],
            "validation": lambda x: x and x.endswith(".apps.googleusercontent.com"),
            # Legacy information
            "legacy_status": "DEPRECATED_CRITICAL",
            "deprecation_date": "2025-09-01",
            "removal_version": "1.3.0",
            "replacement": ["GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT", "GOOGLE_OAUTH_CLIENT_ID_TEST", "GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION"],
            "migration_guide": "CRITICAL SECURITY: Use environment-specific OAuth client IDs to prevent credential leakage. Each environment MUST have separate OAuth credentials.",
            "security_critical": True
        },
        
        "GOOGLE_OAUTH_CLIENT_SECRET": {
            "required_by": [
                "auth_service.oauth",
                "google_oauth_provider",
                "token_exchange",
                "user_verification"
            ],
            "shared_across": ["auth_service"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_requires": ["migration_plan", "alternative_auth"],
            "deletion_impact": "CRITICAL - OAuth token exchange will fail",
            "paired_with": ["GOOGLE_OAUTH_CLIENT_ID", "AUTH_SERVICE_URL"],
            "validation": lambda x: x and len(x) >= 20,
            # Legacy information
            "legacy_status": "DEPRECATED_CRITICAL",
            "deprecation_date": "2025-09-01",
            "removal_version": "1.3.0",
            "replacement": ["GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT", "GOOGLE_OAUTH_CLIENT_SECRET_TEST", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"],
            "migration_guide": "CRITICAL SECURITY: Use environment-specific OAuth client secrets. Never share credentials across environments.",
            "security_critical": True
        },
        
        "AUTH_SERVICE_URL": {
            "required_by": [
                "oauth_redirect_uri",
                "auth_service.oauth",
                "google_oauth_provider",
                "service_discovery"
            ],
            "shared_across": ["auth_service", "netra_backend"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.CRITICAL,
            "deletion_impact": "CRITICAL - OAuth redirect URI misconfiguration (must use auth.staging.netrasystems.ai)",
            "notes": "MUST use proper domain (e.g., auth.staging.netrasystems.ai) not Cloud Run app URL",
            "validation": lambda x: x and x.startswith(("http://", "https://"))
        }
    }
    
    # Important but not critical dependencies
    HIGH_PRIORITY_DEPENDENCIES: Dict[str, Dict[str, Any]] = {
        "REDIS_URL": {
            "required_by": [
                "cache_service",
                "session_store",
                "rate_limiter",
                "websocket_pubsub"
            ],
            "fallback_allowed": True,
            "fallback_warning": "Performance degradation - using in-memory cache",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - Caching and rate limiting disabled",
            "alternatives": ["REDIS_HOST", "REDIS_PORT"],
            "validation": lambda x: not x or x.startswith("redis://"),
            # Legacy information
            "legacy_status": "DEPRECATED",
            "deprecation_date": "2025-11-01",
            "removal_version": "2.0.0",
            "replacement": ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "REDIS_DB"],
            "migration_guide": "Use component-based Redis configuration for better flexibility and security.",
            "auto_construct": True
        },
        
        "CLICKHOUSE_URL": {
            "required_by": ["analytics_service", "metrics_collector"],
            "fallback_allowed": True,
            "fallback_warning": "Analytics disabled - using SQLite fallback",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Analytics functionality limited",
            "alternatives": ["CLICKHOUSE_HOST", "CLICKHOUSE_PORT"],
            "validation": lambda x: not x or "clickhouse" in x.lower()
        },
        
        "ANTHROPIC_API_KEY": {
            "required_by": ["llm_service", "agent_executors"],
            "fallback_allowed": True,
            "fallback_warning": "LLM features disabled - using mock responses",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - AI features unavailable",
            "alternatives": ["CLAUDE_API_KEY"],
            "validation": lambda x: not x or x.startswith("sk-")
        },
        
        "OPENAI_API_KEY": {
            "required_by": ["llm_service", "openai_agents", "gpt_fallback"],
            "fallback_allowed": True,
            "fallback_warning": "OpenAI LLM features disabled - using alternative providers",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - OpenAI-based AI features unavailable",
            "validation": lambda x: not x or x.startswith("sk-")
        },
        
        "PERPLEXITY_API_KEY": {
            "required_by": ["perplexity_service", "search_agents", "research_tools"],
            "fallback_allowed": True,
            "fallback_warning": "Perplexity search features disabled",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - Research and search capabilities limited",
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 20)
        },
        
        "SESSION_SECRET_KEY": {
            "required_by": ["session_management", "user_sessions", "auth_tokens"],
            "fallback_allowed": False,
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - Session management will fail",
            "alternatives": ["SECRET_KEY", "JWT_SECRET_KEY"],
            "validation": lambda x: x and len(x) >= 32,
            # Legacy information
            "legacy_status": "DEPRECATED",
            "deprecation_date": "2025-10-01",
            "removal_version": "1.6.0",
            "replacement": "SECRET_KEY",
            "migration_guide": "Consolidate to SECRET_KEY for all session management needs."
        },
        
        "SLACK_WEBHOOK_URL": {
            "required_by": ["notification_service", "error_reporting", "alerts"],
            "fallback_allowed": True,
            "fallback_warning": "Slack notifications disabled - using email fallback",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - Real-time notifications unavailable",
            "paired_with": ["SLACK_CHANNEL"],
            "validation": lambda x: not x or x.startswith("https://hooks.slack.com/")
        },
        
        "SLACK_CHANNEL": {
            "required_by": ["notification_service", "error_reporting", "alerts"],
            "fallback_allowed": True,
            "fallback_warning": "Slack channel notifications disabled",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Channel-specific notifications unavailable",
            "paired_with": ["SLACK_WEBHOOK_URL"],
            "validation": lambda x: not x or (isinstance(x, str) and x.startswith("#"))
        },
        
        "LANGSMITH_API_KEY": {
            "required_by": ["llm_tracing", "langchain_monitoring", "agent_analytics"],
            "fallback_allowed": True,
            "fallback_warning": "LangSmith tracing disabled - reduced observability",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - LLM call tracing and monitoring unavailable",
            "paired_with": ["LANGSMITH_PROJECT", "LANGSMITH_ENDPOINT"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 10)
        },
        
        "LANGSMITH_PROJECT": {
            "required_by": ["llm_tracing", "langchain_monitoring", "agent_analytics"],
            "fallback_allowed": True,
            "fallback_warning": "LangSmith project tracking disabled",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Project-specific LLM monitoring unavailable",
            "paired_with": ["LANGSMITH_API_KEY"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 0)
        },
        
        "LANGSMITH_ENDPOINT": {
            "required_by": ["llm_tracing", "langchain_monitoring"],
            "fallback_allowed": True,
            "fallback_warning": "Using default LangSmith endpoint",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Custom LangSmith endpoint unavailable",
            "paired_with": ["LANGSMITH_API_KEY"],
            "validation": lambda x: not x or x.startswith(("http://", "https://"))
        },
        
        "JIRA_API_TOKEN": {
            "required_by": ["jira_integration", "issue_tracking", "project_management"],
            "fallback_allowed": True,
            "fallback_warning": "JIRA integration disabled - manual issue tracking required",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - Automated issue tracking unavailable",
            "paired_with": ["JIRA_EMAIL", "JIRA_URL", "JIRA_PROJECT_KEY"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 10)
        },
        
        "JIRA_EMAIL": {
            "required_by": ["jira_integration", "issue_tracking"],
            "fallback_allowed": True,
            "fallback_warning": "JIRA email authentication disabled",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - JIRA user context unavailable",
            "paired_with": ["JIRA_API_TOKEN"],
            "validation": lambda x: not x or ("@" in x and "." in x)
        },
        
        "JIRA_URL": {
            "required_by": ["jira_integration", "issue_tracking"],
            "fallback_allowed": True,
            "fallback_warning": "JIRA URL not configured - integration disabled",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - JIRA instance connection unavailable",
            "paired_with": ["JIRA_API_TOKEN"],
            "validation": lambda x: not x or x.startswith(("http://", "https://"))
        },
        
        "JIRA_PROJECT_KEY": {
            "required_by": ["jira_integration", "issue_creation"],
            "fallback_allowed": True,
            "fallback_warning": "JIRA project key not set - issues may fail to create",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Project-specific issue creation unavailable",
            "paired_with": ["JIRA_API_TOKEN"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 0)
        },
        
        "MIXPANEL_PROJECT_TOKEN": {
            "required_by": ["analytics_service", "user_tracking", "event_analytics"],
            "fallback_allowed": True,
            "fallback_warning": "Mixpanel analytics disabled - reduced user insights",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - User behavior analytics unavailable",
            "paired_with": ["MIXPANEL_API_SECRET"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 20)
        },
        
        "MIXPANEL_API_SECRET": {
            "required_by": ["analytics_service", "mixpanel_exports", "user_tracking"],
            "fallback_allowed": True,
            "fallback_warning": "Mixpanel API secret not configured - export features disabled",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Advanced Mixpanel features unavailable",
            "paired_with": ["MIXPANEL_PROJECT_TOKEN"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 20)
        },
        
        "AWS_ACCESS_KEY_ID": {
            "required_by": ["file_storage", "s3_service", "document_uploads"],
            "fallback_allowed": True,
            "fallback_warning": "AWS S3 storage disabled - using local file storage",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - Cloud file storage unavailable",
            "paired_with": ["AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 10)
        },
        
        "AWS_SECRET_ACCESS_KEY": {
            "required_by": ["file_storage", "s3_service", "document_uploads"],
            "fallback_allowed": True,
            "fallback_warning": "AWS S3 authentication disabled",
            "impact_level": ConfigImpactLevel.HIGH,
            "deletion_impact": "HIGH - Cloud file storage authentication will fail",
            "paired_with": ["AWS_ACCESS_KEY_ID"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 20)
        },
        
        "AWS_S3_BUCKET": {
            "required_by": ["file_storage", "s3_service", "document_uploads"],
            "fallback_allowed": True,
            "fallback_warning": "S3 bucket not configured - file uploads disabled",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Specific S3 bucket operations unavailable",
            "paired_with": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 0)
        },
        
        "AWS_REGION": {
            "required_by": ["file_storage", "s3_service", "aws_services"],
            "fallback_allowed": True,
            "fallback_warning": "Using default AWS region (us-east-1)",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Region-specific AWS operations may fail",
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 5)
        }
    }
    
    # Service-specific dependencies
    SERVICE_SPECIFIC_DEPENDENCIES: Dict[str, Dict[str, Any]] = {
        "GOOGLE_CLIENT_ID": {
            "required_by": ["oauth_service"],
            "service": "auth_service",
            "fallback_allowed": True,
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Google OAuth login disabled",
            "paired_with": ["GOOGLE_CLIENT_SECRET"],
            "validation": lambda x: not x or len(x) > 20
        },
        
        "GITHUB_CLIENT_ID": {
            "required_by": ["github_oauth", "github_analyzer"],
            "service": "auth_service",
            "fallback_allowed": True,
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - GitHub integration disabled",
            "paired_with": ["GITHUB_CLIENT_SECRET"],
            "validation": lambda x: not x or len(x) == 20
        },
        
        "CORS_ORIGINS": {
            "required_by": ["cors_middleware", "api_security", "frontend_integration"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Using default CORS origins - may block frontend requests",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Frontend API requests may be blocked",
            "validation": lambda x: not x or isinstance(x, (str, list))
        },
        
        "ALLOWED_HOSTS": {
            "required_by": ["django_security", "host_validation", "deployment_security"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Using permissive host validation - security risk in production",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Host header attacks possible",
            "validation": lambda x: not x or isinstance(x, (str, list))
        },
        
        "EMAIL_HOST": {
            "required_by": ["email_service", "notification_system", "user_communication"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Email functionality disabled - notifications may fail",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Email notifications unavailable",
            "paired_with": ["EMAIL_PORT", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 0)
        },
        
        "EMAIL_PORT": {
            "required_by": ["email_service", "smtp_connection"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Using default email port (587)",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Email connection may fail",
            "paired_with": ["EMAIL_HOST"],
            "validation": lambda x: not x or (isinstance(x, (int, str)) and 1 <= int(x) <= 65535)
        },
        
        "EMAIL_HOST_USER": {
            "required_by": ["email_service", "smtp_authentication"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Email authentication disabled - may fail to send",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - SMTP authentication will fail",
            "paired_with": ["EMAIL_HOST", "EMAIL_HOST_PASSWORD"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 0)
        },
        
        "EMAIL_HOST_PASSWORD": {
            "required_by": ["email_service", "smtp_authentication"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Email password not set - authentication will fail",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - SMTP authentication will fail",
            "paired_with": ["EMAIL_HOST_USER"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 0)
        },
        
        "EMAIL_USE_TLS": {
            "required_by": ["email_service", "smtp_security"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Email TLS disabled - using insecure connection",
            "impact_level": ConfigImpactLevel.LOW,
            "deletion_impact": "LOW - Email security reduced",
            "validation": lambda x: not x or isinstance(x, bool)
        },
        
        "EMAIL_FROM_ADDRESS": {
            "required_by": ["email_service", "notification_system"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Using default from address - may be flagged as spam",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Email delivery may be impacted",
            "validation": lambda x: not x or ("@" in x and "." in x)
        },
        
        "SENTRY_DSN": {
            "required_by": ["error_tracking", "performance_monitoring", "crash_reporting"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Sentry error tracking disabled - reduced observability",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Error tracking and monitoring unavailable",
            "validation": lambda x: not x or x.startswith("https://")
        },
        
        "SENTRY_ENVIRONMENT": {
            "required_by": ["error_tracking", "deployment_monitoring"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Sentry environment not set - error grouping may be affected",
            "impact_level": ConfigImpactLevel.LOW,
            "deletion_impact": "LOW - Error environment tracking disabled",
            "paired_with": ["SENTRY_DSN"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 0)
        },
        
        "GOOGLE_CLIENT_SECRET": {
            "required_by": ["oauth_service", "google_authentication"],
            "service": "auth_service",
            "fallback_allowed": True,
            "fallback_warning": "Google OAuth disabled - Google login unavailable",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - Google OAuth authentication will fail",
            "paired_with": ["GOOGLE_CLIENT_ID"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 20)
        },
        
        "GITHUB_CLIENT_SECRET": {
            "required_by": ["github_oauth", "github_authentication"],
            "service": "auth_service",
            "fallback_allowed": True,
            "fallback_warning": "GitHub OAuth disabled - GitHub login unavailable",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - GitHub OAuth authentication will fail",
            "paired_with": ["GITHUB_CLIENT_ID"],
            "validation": lambda x: not x or (isinstance(x, str) and len(x) > 20)
        },
        
        "DEBUG": {
            "required_by": ["django_framework", "development_tools", "error_display"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Debug mode setting affects error handling",
            "impact_level": ConfigImpactLevel.LOW,
            "deletion_impact": "LOW - Debug behavior may change",
            "validation": lambda x: isinstance(x, bool)
        },
        
        "LOG_LEVEL": {
            "required_by": ["logging_system", "debug_tools", "monitoring"],
            "service": "all_services",
            "fallback_allowed": True,
            "fallback_warning": "Using default log level (INFO)",
            "impact_level": ConfigImpactLevel.LOW,
            "deletion_impact": "LOW - Logging verbosity may change",
            "valid_values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "validation": lambda x: not x or x.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        },
        
        "RATE_LIMIT_ENABLED": {
            "required_by": ["rate_limiter", "api_security", "ddos_protection"],
            "service": "netra_backend",
            "fallback_allowed": True,
            "fallback_warning": "Rate limiting disabled - API vulnerable to abuse",
            "impact_level": ConfigImpactLevel.MEDIUM,
            "deletion_impact": "MEDIUM - API rate limiting disabled",
            "validation": lambda x: isinstance(x, bool)
        }
    }
    
    @classmethod
    def can_delete_config(cls, config_key: str) -> Tuple[bool, str]:
        """
        Check if a configuration key can be safely deleted.
        
        Returns:
            (can_delete, reason_or_warning)
        """
        # Check critical dependencies
        if config_key in cls.CRITICAL_DEPENDENCIES:
            deps = cls.CRITICAL_DEPENDENCIES[config_key]
            if not deps.get("fallback_allowed", False):
                required_by = ", ".join(deps["required_by"])
                return False, f"BLOCKED: Cannot delete {config_key}. Required by: {required_by}. Impact: {deps['deletion_impact']}"
        
        # Check high priority dependencies
        if config_key in cls.HIGH_PRIORITY_DEPENDENCIES:
            deps = cls.HIGH_PRIORITY_DEPENDENCIES[config_key]
            warning = deps.get("fallback_warning", "Service degradation expected")
            required_by = ", ".join(deps["required_by"])
            return True, f"WARNING: Deleting {config_key} will affect: {required_by}. {warning}"
        
        # Check service-specific dependencies
        if config_key in cls.SERVICE_SPECIFIC_DEPENDENCIES:
            deps = cls.SERVICE_SPECIFIC_DEPENDENCIES[config_key]
            impact = deps.get("deletion_impact", "Feature will be disabled")
            return True, f"INFO: Deleting {config_key}. {impact}"
        
        return True, "No known dependencies"
    
    @classmethod
    def get_alternatives(cls, config_key: str) -> List[str]:
        """Get alternative configuration keys that could replace this one"""
        all_deps = {
            **cls.CRITICAL_DEPENDENCIES,
            **cls.HIGH_PRIORITY_DEPENDENCIES,
            **cls.SERVICE_SPECIFIC_DEPENDENCIES
        }
        
        if config_key in all_deps:
            return all_deps[config_key].get("alternatives", [])
        return []
    
    @classmethod
    def validate_config_value(cls, config_key: str, value: Any) -> Tuple[bool, str]:
        """
        Validate a configuration value against known constraints.
        
        Returns:
            (is_valid, validation_message)
        """
        all_deps = {
            **cls.CRITICAL_DEPENDENCIES,
            **cls.HIGH_PRIORITY_DEPENDENCIES,
            **cls.SERVICE_SPECIFIC_DEPENDENCIES
        }
        
        if config_key not in all_deps:
            return True, "No validation rules defined"
        
        deps = all_deps[config_key]
        
        # Check for validation function
        if "validation" in deps:
            try:
                if deps["validation"](value):
                    return True, "Validation passed"
                else:
                    return False, f"Validation failed for {config_key}"
            except Exception as e:
                return False, f"Validation error: {str(e)}"
        
        # Check for valid values list
        if "valid_values" in deps:
            if value in deps["valid_values"]:
                return True, "Value is in valid list"
            else:
                valid = ", ".join(deps["valid_values"])
                return False, f"Invalid value. Must be one of: {valid}"
        
        return True, "No specific validation required"
    
    @classmethod
    def get_required_configs(cls, service_name: Optional[str] = None) -> Dict[str, Dict]:
        """
        Get all required configurations, optionally filtered by service.
        
        Args:
            service_name: Optional service name to filter by
            
        Returns:
            Dictionary of required configuration keys and their metadata
        """
        required = {}
        
        # Collect from all dependency maps
        all_deps = {
            **cls.CRITICAL_DEPENDENCIES,
            **cls.HIGH_PRIORITY_DEPENDENCIES,
            **cls.SERVICE_SPECIFIC_DEPENDENCIES
        }
        
        for key, deps in all_deps.items():
            # Filter by service if specified
            if service_name:
                if service_name in deps.get("required_by", []):
                    required[key] = deps
                elif deps.get("service") == service_name:
                    required[key] = deps
            else:
                # Include if not fallback allowed or is critical
                if not deps.get("fallback_allowed", True):
                    required[key] = deps
                elif deps.get("impact_level") == ConfigImpactLevel.CRITICAL:
                    required[key] = deps
        
        return required
    
    @classmethod
    def get_impact_analysis(cls, config_key: str) -> Dict[str, Any]:
        """
        Get comprehensive impact analysis for modifying a configuration.
        
        Returns detailed information about what would be affected.
        """
        all_deps = {
            **cls.CRITICAL_DEPENDENCIES,
            **cls.HIGH_PRIORITY_DEPENDENCIES,
            **cls.SERVICE_SPECIFIC_DEPENDENCIES
        }
        
        if config_key not in all_deps:
            return {
                "key": config_key,
                "impact_level": ConfigImpactLevel.LOW,
                "affected_services": [],
                "deletion_allowed": True,
                "notes": "No documented dependencies"
            }
        
        deps = all_deps[config_key]
        
        return {
            "key": config_key,
            "impact_level": deps.get("impact_level", ConfigImpactLevel.LOW),
            "affected_services": deps.get("required_by", []),
            "shared_across": deps.get("shared_across", []),
            "deletion_allowed": deps.get("fallback_allowed", True),
            "deletion_impact": deps.get("deletion_impact", "Unknown impact"),
            "fallback_available": deps.get("fallback_allowed", False),
            "fallback_warning": deps.get("fallback_warning", None),
            "alternatives": deps.get("alternatives", []),
            "paired_configs": deps.get("paired_with", []),
            "validation_required": "validation" in deps
        }
    
    @classmethod
    def _validate_with_central_validator(cls, environment: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Validate configuration using the central SSOT validator.
        
        This delegates to the central configuration validator which is the
        Single Source of Truth for all configuration validation.
        
        Args:
            environment: Optional environment override for testing
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        from shared.configuration.central_config_validator import (
            CentralConfigurationValidator,
            LegacyConfigMarker
        )
        from shared.isolated_environment import get_env
        
        issues = []
        
        try:
            # Use central validator - the SSOT for configuration validation
            env = get_env()
            validator = CentralConfigurationValidator(env_getter_func=lambda key, default=None: env.get(key, default))
            
            # Attempt validation
            validator.validate_all_requirements()
            
            # Check for legacy configurations
            env_dict = env.as_dict() if hasattr(env, 'as_dict') else dict(env)
            legacy_warnings = LegacyConfigMarker.check_legacy_usage(env_dict)
            issues.extend(legacy_warnings)
            
            return (True, issues)
            
        except ValueError as e:
            # Parse validation errors from the central validator
            error_msg = str(e)
            if "Configuration validation failed" in error_msg:
                # Extract individual errors
                error_lines = error_msg.split('\n')
                for line in error_lines:
                    if line.strip().startswith('- '):
                        issues.append(f"Config dependency: {line.strip()[2:]}")
            else:
                issues.append(f"Config dependency: {error_msg}")
            
            return (False, issues)
        except Exception as e:
            logger.warning(f"Central validator unavailable, using fallback: {e}")
            # If central validator fails, fall back to basic dependency checking
            return cls._fallback_validation()
    
    @classmethod
    def _fallback_validation(cls) -> Tuple[bool, List[str]]:
        """Fallback validation when central validator is unavailable.
        
        This provides basic dependency checking based on our dependency map.
        It should only be used when the central validator cannot be accessed.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        from shared.isolated_environment import get_env
        
        issues = []
        env = get_env()
        
        # Check critical dependencies using our map
        for env_key, deps in cls.CRITICAL_DEPENDENCIES.items():
            if not deps.get("fallback_allowed", False):
                value = env.get(env_key)
                if not value:
                    # Check if this can be auto-constructed from components
                    if deps.get("auto_construct") and env_key == "DATABASE_URL":
                        # Check if components are present
                        components_present = all(
                            env.get(comp) for comp in deps.get("replacement", [])
                        )
                        if not components_present:
                            issues.append(f"CRITICAL: Missing required config {env_key}")
                    else:
                        issues.append(f"CRITICAL: Missing required config {env_key}")
        
        return (len(issues) == 0, issues)
    
    @classmethod
    def check_config_consistency(cls, configs: Any) -> List[str]:
        """
        Check for configuration inconsistencies using the central SSOT validator.
        
        This method delegates to the CentralConfigurationValidator which is the
        Single Source of Truth for all configuration validation in the platform.
        
        The ConfigDependencyMap focuses on dependency impact analysis (what breaks
        if a config is removed), while actual validation is handled by the central
        validator.
        
        Args:
            configs: Config object or dict (ignored - we check environment directly)
        
        Returns:
            List of warning/error messages from the central validator
        """
        # Always use the central validator for SSOT compliance
        is_valid, issues = cls._validate_with_central_validator()
        
        # For backward compatibility, also check our dependency-specific concerns
        # This focuses on impact analysis rather than validation
        if hasattr(configs, '__dict__') or isinstance(configs, dict):
            # Check for paired configurations that might cause issues
            paired_issues = cls._check_paired_dependencies(configs)
            issues.extend(paired_issues)
        
        return issues
    
    @classmethod
    def _check_paired_dependencies(cls, configs: Any) -> List[str]:
        """Check for paired configuration dependencies.
        
        This is specific to dependency impact analysis - checking if removing
        one config would break another that depends on it.
        
        Args:
            configs: Config object or dict
            
        Returns:
            List of warnings about missing paired configurations
        """
        from shared.isolated_environment import get_env
        
        issues = []
        env = get_env()
        
        # Check service-specific paired dependencies
        for key, deps in cls.SERVICE_SPECIFIC_DEPENDENCIES.items():
            if "paired_with" in deps:
                # Check if primary config exists
                primary_value = env.get(key)
                if primary_value:
                    # Check if paired configs are present
                    for paired_key in deps["paired_with"]:
                        if not env.get(paired_key):
                            issues.append(
                                f"WARNING: {key} is configured but paired config {paired_key} is missing. "
                                f"This may cause {', '.join(deps.get('required_by', []))} to fail."
                            )
        
        return issues
    
    @classmethod
    def check_legacy_configs(cls, configs: Dict[str, Any]) -> List[str]:
        """
        Check for usage of deprecated/legacy configuration variables.
        
        Returns:
            List of warnings about legacy configuration usage
        """
        warnings = []
        all_deps = {
            **cls.CRITICAL_DEPENDENCIES,
            **cls.HIGH_PRIORITY_DEPENDENCIES,
            **cls.SERVICE_SPECIFIC_DEPENDENCIES
        }
        
        for key, value in configs.items():
            if value and key in all_deps:
                deps = all_deps[key]
                legacy_status = deps.get("legacy_status")
                
                if legacy_status:
                    if legacy_status == "DEPRECATED_CRITICAL":
                        warnings.append(
                            f"CRITICAL SECURITY WARNING: '{key}' is deprecated for security reasons. "
                            f"{deps.get('migration_guide', 'Please migrate immediately.')}"
                        )
                    elif legacy_status == "DEPRECATED":
                        warnings.append(
                            f"WARNING: '{key}' is deprecated (removal: {deps.get('removal_version', 'TBD')}). "
                            f"{deps.get('migration_guide', 'Please migrate to replacement.')}"
                        )
        
        return warnings
    
    @classmethod
    def get_legacy_migration_plan(cls, config_key: str) -> Optional[Dict[str, Any]]:
        """
        Get migration plan for a legacy configuration variable.
        
        Returns:
            Migration information or None if not legacy
        """
        all_deps = {
            **cls.CRITICAL_DEPENDENCIES,
            **cls.HIGH_PRIORITY_DEPENDENCIES,
            **cls.SERVICE_SPECIFIC_DEPENDENCIES
        }
        
        if config_key in all_deps:
            deps = all_deps[config_key]
            if "legacy_status" in deps:
                return {
                    "status": deps["legacy_status"],
                    "deprecation_date": deps.get("deprecation_date"),
                    "removal_version": deps.get("removal_version"),
                    "replacement": deps.get("replacement"),
                    "migration_guide": deps.get("migration_guide"),
                    "auto_construct": deps.get("auto_construct", False),
                    "security_critical": deps.get("security_critical", False)
                }
        
        return None