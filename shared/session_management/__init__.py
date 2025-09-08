"""Shared Session Management Module - SSOT Compliant

This module provides SSOT session management functionality for the entire Netra platform.
It resolves the SessionMetrics SSOT violation by providing business-focused naming and
unified interfaces for both system and user session management.

SSOT Compliance:
- SystemSessionAggregator: System-level database session tracking
- UserSessionTracker: User-level behavior and engagement tracking  
- UnifiedSessionMetricsProvider: Unified interface for all session metrics
- Compatibility aliases: Backward compatibility during migration

Key Components (New SSOT Architecture):
- SystemSessionAggregator: Database connection pool and system session lifecycle
- UserSessionTracker: User behavior analytics and engagement tracking
- UnifiedSessionMetricsProvider: Single interface for all session metrics
- SessionMetrics (compatibility): Legacy alias resolving SSOT violation

Legacy Components (Deprecated):
- UserSessionManager: Use UserSessionTracker instead
- UserSession: Use UserSessionInfo instead
- SessionMetrics from user_session_manager: Use UserEngagementMetrics instead

Usage (Recommended):
    # System-level metrics (database sessions, connection pools)
    from shared.session_management import get_system_session_aggregator
    aggregator = await get_system_session_aggregator()
    
    # User-level metrics (behavior, engagement)
    from shared.session_management import get_user_session_tracker
    tracker = get_user_session_tracker()
    
    # Unified access to all metrics
    from shared.session_management import get_unified_session_metrics_provider
    provider = get_unified_session_metrics_provider()
    
    # Legacy compatibility (resolves AttributeError)
    from shared.session_management import SessionMetrics
    metrics = SessionMetrics()  # Now has last_activity attribute

Migration Guide:
- Replace system SessionMetrics with SystemSessionAggregator
- Replace user SessionMetrics with UserSessionTracker  
- Use compatibility aliases during transition period
- All SessionMetrics instances now have last_activity attribute
"""

# New SSOT-compliant imports
from shared.session_management.system_session_aggregator import (
    SystemSessionAggregator,
    SystemSessionRecord,
    SystemConnectionPoolMetrics,
    SystemSessionState,
    get_system_session_aggregator,
    shutdown_system_session_aggregator
)

from shared.session_management.user_session_tracker import (
    UserSessionTracker,
    UserSessionInfo,
    UserEngagementMetrics,
    UserSessionTrackerError,
    get_user_session_tracker,
    initialize_user_session_tracker,
    shutdown_user_session_tracker
)

from shared.session_management.session_metrics_provider import (
    SessionMetricsProvider,
    UnifiedSessionMetrics,
    SessionMetricsType,
    SessionMetricsAdapter,
    UnifiedSessionMetricsProvider,
    get_unified_session_metrics_provider,
    get_session_metrics_with_last_activity
)

from shared.session_management.compatibility_aliases import (
    SessionMetrics,  # CRITICAL: This resolves the SSOT violation
    SystemSessionMetrics,
    UserSessionMetrics,
    create_system_session_metrics,
    create_user_session_metrics,
    get_migration_status
)

# Legacy imports for backward compatibility
from shared.session_management.user_session_manager import (
    UserSessionManager,
    UserSession,
    SessionMetrics as LegacySessionMetrics,  # Avoid naming conflict
    SessionManagerError,
    get_session_manager,
    initialize_session_manager,
    shutdown_session_manager,
    get_user_session,
    get_session_metrics
)

# CRITICAL: Export the compatibility SessionMetrics that fixes AttributeError
__all__ = [
    # New SSOT-compliant interface (Recommended)
    'SystemSessionAggregator',
    'SystemSessionRecord', 
    'SystemConnectionPoolMetrics',
    'SystemSessionState',
    'get_system_session_aggregator',
    'shutdown_system_session_aggregator',
    
    'UserSessionTracker',
    'UserSessionInfo',
    'UserEngagementMetrics', 
    'UserSessionTrackerError',
    'get_user_session_tracker',
    'initialize_user_session_tracker',
    'shutdown_user_session_tracker',
    
    'UnifiedSessionMetricsProvider',
    'UnifiedSessionMetrics',
    'SessionMetricsType',
    'SessionMetricsAdapter',
    'get_unified_session_metrics_provider',
    'get_session_metrics_with_last_activity',
    
    # CRITICAL: Compatibility aliases that resolve SSOT violation
    'SessionMetrics',  # This now works and has last_activity attribute
    'SystemSessionMetrics',
    'UserSessionMetrics',
    'create_system_session_metrics',
    'create_user_session_metrics',
    'get_migration_status',
    
    # Legacy interface (Backward compatibility)
    'UserSessionManager',
    'UserSession',
    'SessionManagerError', 
    'get_session_manager',
    'initialize_session_manager',
    'shutdown_session_manager',
    'get_user_session',
    'get_session_metrics'
]