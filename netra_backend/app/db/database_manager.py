"""Database Manager - SSOT for Database Operations

Centralized database management with proper DatabaseURLBuilder integration.
This module uses DatabaseURLBuilder as the SINGLE SOURCE OF TRUTH for URL construction.

CRITICAL: ALL URL manipulation MUST go through DatabaseURLBuilder methods:
- format_url_for_driver() for driver-specific formatting
- normalize_url() for URL normalization
- NO MANUAL STRING REPLACEMENT OPERATIONS ALLOWED

See Also:
- shared/database_url_builder.py - The ONLY source for URL construction
- SPEC/database_connectivity_architecture.xml - Database connection patterns
- docs/configuration_architecture.md - Configuration system overview

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Unified database connection management
- Value Impact: Eliminates URL construction errors and ensures consistency
- Strategic Impact: Single source of truth for all database connection patterns
"""

import asyncio
import logging
import re
import time
import uuid
from typing import Dict, Any, Optional, List, Callable, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool, StaticPool
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import text

from netra_backend.app.core.config import get_config
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env

# Issue #374: Enhanced database exception handling
from netra_backend.app.db.transaction_errors import (
    DeadlockError, ConnectionError, TransactionError, TimeoutError, 
    PermissionError, SchemaError, classify_error, is_retryable_error
)

logger = logging.getLogger(__name__)


class CoordinationEventType(Enum):
    """Events for multi-layer coordination."""
    TRANSACTION_STARTED = "transaction_started"
    TRANSACTION_COMMITTED = "transaction_committed" 
    TRANSACTION_ROLLED_BACK = "transaction_rolled_back"
    COORDINATION_FAILED = "coordination_failed"
    LAYER_SYNC_ERROR = "layer_sync_error"
    WEBSOCKET_EVENT_QUEUED = "websocket_event_queued"
    WEBSOCKET_EVENT_SENT = "websocket_event_sent"


@dataclass
class RollbackNotification:
    """Notification sent when operations fail and rollback."""
    transaction_id: str
    failed_operation: str
    error_message: str
    affected_layers: List[str]
    recovery_actions: List[str]
    user_message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PendingWebSocketEvent:
    """WebSocket event queued for sending after transaction commit."""
    event_type: str
    event_data: Dict[str, Any]
    connection_id: Optional[str] = None
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    priority: int = 0  # Higher numbers = higher priority
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TransactionEventCoordinator:
    """Coordinates WebSocket events with database transaction boundaries.
    
    Business Value Justification (BVJ):
    - Segment: ALL (Free  ->  Enterprise) - Foundation for all real-time features
    - Business Goal: Prevent WebSocket events being sent before database commits
    - Value Impact: Eliminates data inconsistency in chat functionality
    - Strategic Impact: CRITICAL - Protects $500K+ ARR Golden Path reliability
    
    This coordinator ensures that WebSocket events are only sent AFTER database
    transactions have been successfully committed, preventing race conditions
    where users see updates before data is actually persisted.
    """
    
    def __init__(self, websocket_manager=None):
        """Initialize transaction event coordinator.
        
        Args:
            websocket_manager: Optional WebSocket manager for sending events
        """
        self.websocket_manager = websocket_manager
        self.pending_events: Dict[str, List[PendingWebSocketEvent]] = defaultdict(list)
        self.coordination_metrics: Dict[str, Any] = defaultdict(int)
        self._lock = asyncio.Lock()
        
        logger.info("[U+1F517] TransactionEventCoordinator initialized - ensuring WebSocket/DB coordination")
        
    def set_websocket_manager(self, websocket_manager):
        """Set or update the WebSocket manager reference."""
        self.websocket_manager = websocket_manager
        logger.debug(" CYCLE:  WebSocket manager linked to TransactionEventCoordinator")
        
    async def add_pending_event(self, transaction_id: str, event_type: str, event_data: Dict[str, Any], 
                               connection_id: Optional[str] = None, user_id: Optional[str] = None,
                               thread_id: Optional[str] = None, priority: int = 0):
        """Queue WebSocket event for sending after transaction commit.
        
        Args:
            transaction_id: Unique identifier for the database transaction
            event_type: Type of WebSocket event to send
            event_data: Data payload for the event
            connection_id: Optional WebSocket connection ID
            user_id: Optional user ID for event targeting
            thread_id: Optional thread ID for event context
            priority: Event priority (higher numbers sent first)
        """
        async with self._lock:
            event = PendingWebSocketEvent(
                event_type=event_type,
                event_data=event_data,
                connection_id=connection_id,
                user_id=user_id,
                thread_id=thread_id,
                priority=priority
            )
            
            self.pending_events[transaction_id].append(event)
            self.coordination_metrics["events_queued"] += 1
            
            logger.debug(f"[U+1F4E4] Queued WebSocket event '{event_type}' for transaction {transaction_id[:8]}... "
                        f"(user: {user_id}, priority: {priority})")
            
    async def on_transaction_commit(self, transaction_id: str) -> int:
        """Send all pending events after successful transaction commit.
        
        Args:
            transaction_id: ID of the committed transaction
            
        Returns:
            Number of events successfully sent
        """
        async with self._lock:
            events = self.pending_events.pop(transaction_id, [])
            
        if not events:
            logger.debug(f" CYCLE:  No pending events for committed transaction {transaction_id[:8]}...")
            return 0
            
        # Sort events by priority (highest first), then by creation time
        events.sort(key=lambda e: (-e.priority, e.created_at))
        
        sent_count = 0
        failed_count = 0
        
        logger.info(f"[U+1F4E4] Sending {len(events)} queued WebSocket events after transaction commit {transaction_id[:8]}...")
        
        for event in events:
            try:
                success = await self._send_websocket_event(event)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                logger.error(f" FAIL:  Failed to send WebSocket event '{event.event_type}' after commit: {e}")
                
        self.coordination_metrics["events_sent_after_commit"] += sent_count
        self.coordination_metrics["events_failed_after_commit"] += failed_count
        
        if failed_count > 0:
            logger.warning(f" WARNING: [U+FE0F] Transaction {transaction_id[:8]}... commit coordination: "
                          f"{sent_count} events sent, {failed_count} failed")
        else:
            logger.info(f" PASS:  Transaction {transaction_id[:8]}... commit coordination successful: "
                       f"{sent_count} events sent")
            
        return sent_count
            
    async def on_transaction_rollback(self, transaction_id: str, error_message: str = "") -> RollbackNotification:
        """Handle transaction rollback by clearing pending events and sending notification.
        
        Args:
            transaction_id: ID of the rolled back transaction
            error_message: Optional error message describing the failure
            
        Returns:
            RollbackNotification object describing the rollback
        """
        async with self._lock:
            events = self.pending_events.pop(transaction_id, [])
            
        affected_event_types = [e.event_type for e in events]
        affected_users = list(set(e.user_id for e in events if e.user_id))
        
        rollback_notification = RollbackNotification(
            transaction_id=transaction_id,
            failed_operation="database_transaction",
            error_message=error_message or "Database transaction failed and was rolled back",
            affected_layers=["database", "websocket"],
            recovery_actions=["Transaction rolled back", "WebSocket events cleared", "User notification sent"],
            user_message="Operation failed and has been rolled back. Please try again."
        )
        
        self.coordination_metrics["rollbacks_handled"] += 1
        self.coordination_metrics["events_cleared_on_rollback"] += len(events)
        
        logger.warning(f" CYCLE:  Transaction {transaction_id[:8]}... rolled back - cleared {len(events)} pending WebSocket events")
        logger.info(f"[U+1F4DD] Rollback affected {len(affected_users)} users and event types: {affected_event_types}")
        
        # Send rollback notification to affected users
        try:
            await self._send_rollback_notification(rollback_notification, affected_users)
        except Exception as e:
            logger.error(f" FAIL:  Failed to send rollback notification: {e}")
            
        return rollback_notification
        
    async def _send_websocket_event(self, event: PendingWebSocketEvent) -> bool:
        """Send a single WebSocket event using the configured manager.
        
        Args:
            event: Event to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.websocket_manager:
            logger.warning(f" WARNING: [U+FE0F] No WebSocket manager configured - cannot send event '{event.event_type}'")
            return False
            
        try:
            # Attempt to send the event using the WebSocket manager
            if hasattr(self.websocket_manager, 'send_to_connection') and event.connection_id:
                # Send to specific connection
                await self.websocket_manager.send_to_connection(
                    event.connection_id, event.event_type, event.event_data
                )
            elif hasattr(self.websocket_manager, 'send_to_user') and event.user_id:
                # Send to all user connections
                await self.websocket_manager.send_to_user(
                    event.user_id, event.event_type, event.event_data
                )
            elif hasattr(self.websocket_manager, 'send_event'):
                # Generic send method
                await self.websocket_manager.send_event(
                    event.event_type, event.event_data
                )
            else:
                logger.warning(f" WARNING: [U+FE0F] WebSocket manager missing compatible send methods for event '{event.event_type}'")
                return False
                
            logger.debug(f"[U+1F4E4] Successfully sent WebSocket event '{event.event_type}' (user: {event.user_id})")
            return True
            
        except Exception as e:
            logger.error(f" FAIL:  Failed to send WebSocket event '{event.event_type}': {type(e).__name__}: {e}")
            return False
            
    async def _send_rollback_notification(self, notification: RollbackNotification, affected_users: List[str]):
        """Send rollback notification to affected users.
        
        Args:
            notification: Rollback notification to send
            affected_users: List of user IDs to notify
        """
        if not self.websocket_manager or not affected_users:
            return
            
        rollback_event_data = {
            "type": "transaction_rollback",
            "transaction_id": notification.transaction_id,
            "message": notification.user_message,
            "error": notification.error_message,
            "timestamp": notification.timestamp.isoformat(),
            "recovery_actions": notification.recovery_actions
        }
        
        for user_id in affected_users:
            try:
                if hasattr(self.websocket_manager, 'send_to_user'):
                    await self.websocket_manager.send_to_user(
                        user_id, "transaction_rollback", rollback_event_data
                    )
                logger.debug(f"[U+1F4E4] Sent rollback notification to user {user_id}")
            except Exception as e:
                logger.error(f" FAIL:  Failed to send rollback notification to user {user_id}: {e}")
                
    def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get current coordination metrics for monitoring.
        
        Returns:
            Dictionary containing coordination statistics
        """
        return dict(self.coordination_metrics)
        
    def get_pending_events_count(self) -> int:
        """Get total number of pending events across all transactions.
        
        Returns:
            Total count of pending events
        """
        return sum(len(events) for events in self.pending_events.values())
        
    async def cleanup_stale_transactions(self, max_age_minutes: int = 30):
        """Clean up pending events for transactions that are older than max_age.
        
        Args:
            max_age_minutes: Maximum age of transactions to keep
        """
        cutoff_time = datetime.now(timezone.utc) - datetime.timedelta(minutes=max_age_minutes)
        stale_transactions = []
        
        async with self._lock:
            for transaction_id, events in list(self.pending_events.items()):
                if events and events[0].created_at < cutoff_time:
                    stale_transactions.append(transaction_id)
                    
            for transaction_id in stale_transactions:
                events = self.pending_events.pop(transaction_id, [])
                self.coordination_metrics["stale_transactions_cleaned"] += 1
                self.coordination_metrics["stale_events_cleared"] += len(events)
                
        if stale_transactions:
            logger.warning(f"[U+1F9F9] Cleaned up {len(stale_transactions)} stale transactions with pending events")
            
        return len(stale_transactions)


class DatabaseManager:
    """Centralized database connection and session management with comprehensive stability features.
    
    COMBINED FEATURES:
    - Transaction event coordination for WebSocket integration
    - Issue #414 remediation: Enhanced connection pool management to prevent pool exhaustion
    - User context session isolation to prevent data contamination
    - Transaction rollback safety for context errors
    - Session lifecycle tracking and cleanup
    """
    
    def __init__(self):
        self.config = get_config()
        self._engines: Dict[str, AsyncEngine] = {}
        self._initialized = False
        self._url_builder: Optional[DatabaseURLBuilder] = None
        
        # Initialize transaction event coordinator for WebSocket coordination
        self.transaction_coordinator = TransactionEventCoordinator()
        logger.debug("[U+1F517] DatabaseManager initialized with TransactionEventCoordinator")
        
        # ISSUE #414 FIX: Enhanced session tracking and pool management
        self._active_sessions: Dict[str, Dict[str, Any]] = {}  # Track active sessions per user
        self._session_lifecycle_callbacks: List[Callable] = []  # Session cleanup callbacks
        self._pool_stats = {
            'total_sessions_created': 0,
            'active_sessions_count': 0,
            'sessions_cleaned_up': 0,
            'pool_exhaustion_warnings': 0,
            'context_isolation_violations': 0
        }
    
    async def initialize(self):
        """Initialize database connections using DatabaseURLBuilder."""
        if self._initialized:
            logger.debug("DatabaseManager already initialized, skipping")
            return
        
        init_start_time = time.time()
        logger.info("[U+1F517] Starting DatabaseManager initialization...")
        
        try:
            # Get database URL using DatabaseURLBuilder as SSOT
            logger.debug("Constructing database URL using DatabaseURLBuilder SSOT")
            database_url = self._get_database_url()
            
            # ISSUE #414 FIX: Enhanced connection pool configuration
            echo = getattr(self.config, 'database_echo', False)
            # Increased pool sizes to handle concurrent user load and prevent exhaustion
            pool_size = getattr(self.config, 'database_pool_size', 25)  # Increased from 5 to 25
            max_overflow = getattr(self.config, 'database_max_overflow', 50)  # Increased from 10 to 50
            pool_timeout = getattr(self.config, 'database_pool_timeout', 30)  # 30 second timeout
            
            logger.info(f"[U+1F527] Enhanced database configuration (Issue #414): echo={echo}, pool_size={pool_size}, max_overflow={max_overflow}, timeout={pool_timeout}s")
            
            # Use appropriate pool class for async engines with enhanced configuration
            engine_kwargs = {
                "echo": echo,
                "pool_pre_ping": True,
                "pool_recycle": 1800,  # Reduced from 3600 to 1800s for faster recycling
                "pool_timeout": pool_timeout,  # Add timeout to prevent hanging
                "connect_args": {
                    "command_timeout": 30,  # 30 second query timeout
                    "server_settings": {
                        "application_name": "netra_backend_enhanced_pool"
                    }
                }
            }
            
            # Configure pooling for async engines with Issue #414 fixes
            if pool_size <= 0 or "sqlite" in database_url.lower():
                # Use NullPool for SQLite or disabled pooling
                engine_kwargs["poolclass"] = NullPool
                logger.info("[U+1F3CA] Using NullPool for SQLite or disabled pooling")
            else:
                # Use AsyncAdaptedQueuePool for better concurrent handling with async engines
                engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
                engine_kwargs["pool_size"] = pool_size
                engine_kwargs["max_overflow"] = max_overflow
                logger.info(f"[U+1F3CA] Using AsyncAdaptedQueuePool for enhanced async concurrency: pool_size={pool_size}, max_overflow={max_overflow}")
            
            logger.debug("Creating async database engine...")
            primary_engine = create_async_engine(
                database_url,
                **engine_kwargs
            )
            
            # Test initial connection
            logger.debug("Testing initial database connection...")
            async with primary_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            self._engines['primary'] = primary_engine
            self._initialized = True
            
            init_duration = time.time() - init_start_time
            logger.info(f" PASS:  DatabaseManager initialized successfully in {init_duration:.3f}s")
            
        except Exception as e:
            init_duration = time.time() - init_start_time
            logger.critical(f"[U+1F4A5] CRITICAL: DatabaseManager initialization failed after {init_duration:.3f}s: {e}")
            logger.error(f"Database connection failure details: {type(e).__name__}: {str(e)}")
            logger.error(f"This will prevent all database operations including user data persistence")
            raise
    
    def get_engine(self, name: str = 'primary') -> AsyncEngine:
        """Get database engine by name with auto-initialization safety.
        
        CRITICAL FIX: Auto-initializes if not initialized to prevent 
        "DatabaseManager not initialized" errors in staging.
        """
        if not self._initialized:
            # CRITICAL FIX: Auto-initialize on first access
            logger.warning("DatabaseManager accessed before initialization - auto-initializing now")
            import asyncio
            try:
                # Try to initialize synchronously if possible
                asyncio.create_task(self.initialize())
                # Give the initialization task a moment to complete
                # Note: In production, this should be handled by proper startup sequencing
                import time
                time.sleep(0.1)  # Brief pause for initialization
                
                if not self._initialized:
                    raise RuntimeError(
                        "DatabaseManager auto-initialization failed. "
                        "Ensure proper startup sequence calls await manager.initialize()"
                    )
            except Exception as init_error:
                logger.error(f"Auto-initialization failed: {init_error}")
                raise RuntimeError(
                    f"DatabaseManager not initialized and auto-initialization failed: {init_error}. "
                    "Fix: Call await manager.initialize() in startup sequence."
                ) from init_error
        
        if name not in self._engines:
            raise ValueError(f"Engine '{name}' not found")
        
        return self._engines[name]
    
    @asynccontextmanager
    async def get_session(self, engine_name: str = 'primary', user_context: Optional[Any] = None, operation_type: str = "unknown"):
        """Get async database session with Issue #374 enhanced exception handling and Issue #414 user isolation.
        
        COMBINED ISSUE #374 + #414 REMEDIATION:
        - Enhanced exception handling with specific error classification (Issue #374)
        - User context isolation to prevent cross-user contamination (Issue #414)
        - Enhanced session lifecycle tracking and cleanup
        - Connection pool monitoring and exhaustion prevention
        - Transaction rollback safety with enhanced error diagnostics
        
        Args:
            engine_name: Name of the engine to use (default: 'primary')
            user_context: UserExecutionContext for proper isolation (Issue #414 fix)
            operation_type: Type of operation for monitoring (e.g., "user_query", "admin_task")
            
        Yields:
            AsyncSession: Database session with automatic transaction management
            
        Raises:
            DeadlockError, ConnectionError, TransactionError: Enhanced database exceptions (Issue #374)
            Exception: Other database errors, rollback errors (original exception preserved)
        """
        session_start_time = time.time()
        
        # ISSUE #414 FIX: Extract user information from context for proper isolation
        user_id = None
        context_valid = False
        if user_context:
            try:
                user_id = getattr(user_context, 'user_id', None)
                thread_id = getattr(user_context, 'thread_id', None)
                request_id = getattr(user_context, 'request_id', None)
                context_valid = bool(user_id and thread_id)
                
                if not context_valid:
                    logger.warning(f"Invalid user context for session: user_id={user_id}, thread_id={thread_id}")
                    self._pool_stats['context_isolation_violations'] += 1
            except Exception as e:
                logger.error(f"Error extracting user context: {e}")
                self._pool_stats['context_isolation_violations'] += 1
        
        session_id = f"sess_{int(session_start_time * 1000)}_{hash(user_id or 'system') % 10000}"
        
        # ISSUE #414 FIX: Check for pool exhaustion before creating session
        current_active = self._pool_stats['active_sessions_count']
        pool_size = getattr(self.config, 'database_pool_size', 25)
        max_overflow = getattr(self.config, 'database_max_overflow', 50)
        total_capacity = pool_size + max_overflow
        
        if current_active >= total_capacity * 0.9:  # Warn at 90% capacity
            logger.warning(f" ALERT:  Database pool near exhaustion: {current_active}/{total_capacity} sessions active")
            self._pool_stats['pool_exhaustion_warnings'] += 1
        
        logger.debug(f" CYCLE:  Starting database session {session_id} for {operation_type} (user: {user_id or 'system'}, valid_context: {context_valid})")
        
        # CRITICAL FIX: Enhanced initialization safety
        if not self._initialized:
            logger.info(f"[U+1F527] Auto-initializing DatabaseManager for session access (operation: {operation_type})")
            await self.initialize()
        
        # ISSUE #414 FIX: Track active session for pool management
        session_metadata = {
            'session_id': session_id,
            'user_id': user_id,
            'user_context': user_context,
            'operation_type': operation_type,
            'start_time': session_start_time,
            'engine_name': engine_name,
            'context_valid': context_valid
        }
        
        self._active_sessions[session_id] = session_metadata
        self._pool_stats['total_sessions_created'] += 1
        self._pool_stats['active_sessions_count'] += 1
        
        engine = self.get_engine(engine_name)
        async with AsyncSession(engine) as session:
            original_exception = None
            transaction_start_time = time.time()
            logger.debug(f"[U+1F4DD] Transaction started for session {session_id}")
            
            try:
                yield session
                
                # Log successful commit
                commit_start_time = time.time()
                await session.commit()
                commit_duration = time.time() - commit_start_time
                session_duration = time.time() - session_start_time
                
                logger.info(f" PASS:  Session {session_id} committed successfully - Operation: {operation_type}, "
                           f"User: {user_id or 'system'}, Duration: {session_duration:.3f}s, Commit: {commit_duration:.3f}s")
                
            except (DeadlockError, ConnectionError) as e:
                # ISSUE #374 FIX: Handle specific transaction errors with enhanced context
                original_exception = classify_error(e)
                rollback_start_time = time.time()
                
                logger.critical(f"[U+1F4A5] SPECIFIC TRANSACTION FAILURE ({type(original_exception).__name__}) in session {session_id}")
                logger.error(f"Operation: {operation_type}, User: {user_id or 'system'}, Error: {str(original_exception)}")
                
                try:
                    await session.rollback()
                    rollback_duration = time.time() - rollback_start_time
                    logger.warning(f" CYCLE:  Rollback completed for session {session_id} in {rollback_duration:.3f}s")
                except Exception as rollback_error:
                    rollback_duration = time.time() - rollback_start_time
                    logger.critical(f"[U+1F4A5] ROLLBACK FAILED for session {session_id} after {rollback_duration:.3f}s: {rollback_error}")
                    logger.critical(f"DATABASE INTEGRITY AT RISK - Manual intervention may be required")
                
                session_duration = time.time() - session_start_time
                logger.error(f" FAIL:  Session {session_id} failed after {session_duration:.3f}s - Data loss possible for user {user_id or 'system'}")
                raise original_exception
                
            except Exception as e:
                # ISSUE #374 FIX: Handle general exceptions with enhanced error classification  
                original_exception = classify_error(e)
                rollback_start_time = time.time()
                
                logger.critical(f"[U+1F4A5] TRANSACTION FAILURE ({type(original_exception).__name__}) in session {session_id}")
                logger.error(f"Operation: {operation_type}, User: {user_id or 'system'}, Error: {str(original_exception)}")
                
                try:
                    await session.rollback()
                    rollback_duration = time.time() - rollback_start_time
                    logger.warning(f" CYCLE:  Rollback completed for session {session_id} in {rollback_duration:.3f}s")
                except Exception as rollback_error:
                    rollback_duration = time.time() - rollback_start_time
                    logger.critical(f"[U+1F4A5] ROLLBACK FAILED for session {session_id} after {rollback_duration:.3f}s: {rollback_error}")
                    logger.critical(f"DATABASE INTEGRITY AT RISK - Manual intervention may be required")
                    # Continue with original exception
                
                session_duration = time.time() - session_start_time
                logger.error(f" FAIL:  Session {session_id} failed after {session_duration:.3f}s - Data loss possible for user {user_id or 'system'}")
                raise original_exception
                
            finally:
                close_start_time = time.time()
                
                # ISSUE #414 FIX: Enhanced session cleanup and tracking
                try:
                    await session.close()
                    close_duration = time.time() - close_start_time
                    logger.debug(f"[U+1F512] Session {session_id} closed in {close_duration:.3f}s")
                except Exception as close_error:
                    close_duration = time.time() - close_start_time
                    logger.error(f" WARNING: [U+FE0F] Session close failed for {session_id} after {close_duration:.3f}s: {close_error}")
                    # Don't raise close errors - they shouldn't prevent completion
                
                # ISSUE #414 FIX: Remove session from active tracking and update stats
                try:
                    if session_id in self._active_sessions:
                        session_meta = self._active_sessions.pop(session_id)
                        self._pool_stats['active_sessions_count'] -= 1
                        self._pool_stats['sessions_cleaned_up'] += 1
                        
                        # Call lifecycle callbacks for user context cleanup
                        for callback in self._session_lifecycle_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(session_meta)
                                else:
                                    callback(session_meta)
                            except Exception as callback_error:
                                logger.warning(f"Session lifecycle callback failed: {callback_error}")
                        
                        total_session_time = time.time() - session_start_time
                        logger.debug(f"[U+1F9F9] Session {session_id} cleanup complete - Total time: {total_session_time:.3f}s, "
                                   f"User: {user_id or 'system'}, Active sessions: {self._pool_stats['active_sessions_count']}")
                    
                except Exception as cleanup_error:
                    logger.error(f"Session tracking cleanup failed for {session_id}: {cleanup_error}")
                    # Ensure counter is decremented even if cleanup fails
                    self._pool_stats['active_sessions_count'] = max(0, self._pool_stats['active_sessions_count'] - 1)
    
    def set_websocket_manager(self, websocket_manager):
        """Set WebSocket manager for transaction coordination.
        
        Args:
            websocket_manager: WebSocket manager instance for event coordination
        """
        self.transaction_coordinator.set_websocket_manager(websocket_manager)
        logger.info("[U+1F517] WebSocket manager linked to DatabaseManager transaction coordinator")
        
    @asynccontextmanager
    async def get_coordinated_session(self, engine_name: str = 'primary', user_id: Optional[str] = None, 
                                    operation_type: str = "unknown", 
                                    websocket_events: Optional[List[Dict[str, Any]]] = None):
        """Get database session with WebSocket event coordination.
        
        This method ensures that WebSocket events are only sent AFTER database
        transactions are successfully committed, preventing data inconsistency.
        
        Args:
            engine_name: Name of the engine to use
            user_id: User ID for session tracking
            operation_type: Type of operation for logging
            websocket_events: List of WebSocket events to send after commit
            
        Yields:
            tuple: (session, transaction_id) for database operations and event queuing
        """
        transaction_id = str(uuid.uuid4())
        session_start_time = time.time()
        session_id = f"coord_sess_{int(session_start_time * 1000)}_{hash(user_id or 'system') % 10000}"
        
        logger.info(f"[U+1F517] Starting coordinated database session {session_id} for {operation_type} "
                   f"(user: {user_id or 'system'}, transaction: {transaction_id[:8]}...)")
        
        # CRITICAL FIX: Enhanced initialization safety
        if not self._initialized:
            logger.info(f"[U+1F527] Auto-initializing DatabaseManager for coordinated session (operation: {operation_type})")
            await self.initialize()
        
        engine = self.get_engine(engine_name)
        async with AsyncSession(engine) as session:
            original_exception = None
            transaction_start_time = time.time()
            
            # Pre-queue any provided WebSocket events
            if websocket_events:
                for event in websocket_events:
                    await self.transaction_coordinator.add_pending_event(
                        transaction_id=transaction_id,
                        event_type=event.get('type', 'unknown'),
                        event_data=event.get('data', {}),
                        connection_id=event.get('connection_id'),
                        user_id=user_id,
                        priority=event.get('priority', 0)
                    )
                    
            logger.debug(f"[U+1F4DD] Coordinated transaction started for session {session_id} (transaction: {transaction_id[:8]}...)")
            
            try:
                yield session, transaction_id
                
                # Commit database transaction
                commit_start_time = time.time()
                await session.commit()
                commit_duration = time.time() - commit_start_time
                
                logger.debug(f" PASS:  Database commit successful for transaction {transaction_id[:8]}... in {commit_duration:.3f}s")
                
                # Send queued WebSocket events after successful commit
                events_sent = await self.transaction_coordinator.on_transaction_commit(transaction_id)
                
                session_duration = time.time() - session_start_time
                logger.info(f" PASS:  Coordinated session {session_id} completed successfully - "
                           f"Operation: {operation_type}, User: {user_id or 'system'}, "
                           f"Duration: {session_duration:.3f}s, Events sent: {events_sent}")
                
            except Exception as e:
                original_exception = e
                rollback_start_time = time.time()
                
                logger.critical(f"[U+1F4A5] COORDINATED TRANSACTION FAILURE in session {session_id}")
                logger.error(f"Operation: {operation_type}, User: {user_id or 'system'}, "
                           f"Transaction: {transaction_id[:8]}..., Error: {type(e).__name__}: {str(e)}")
                
                try:
                    await session.rollback()
                    rollback_duration = time.time() - rollback_start_time
                    logger.warning(f" CYCLE:  Database rollback completed for session {session_id} in {rollback_duration:.3f}s")
                    
                    # Handle rollback coordination and send notifications
                    rollback_notification = await self.transaction_coordinator.on_transaction_rollback(
                        transaction_id, str(e)
                    )
                    
                    logger.info(f"[U+1F4E4] Rollback notification sent for transaction {transaction_id[:8]}... "
                               f"affecting {len(rollback_notification.affected_layers)} layers")
                    
                except Exception as rollback_error:
                    rollback_duration = time.time() - rollback_start_time
                    logger.critical(f"[U+1F4A5] COORDINATED ROLLBACK FAILED for session {session_id} "
                                  f"after {rollback_duration:.3f}s: {rollback_error}")
                    logger.critical(f"DATABASE AND WEBSOCKET COORDINATION INTEGRITY AT RISK")
                
                session_duration = time.time() - session_start_time
                logger.error(f" FAIL:  Coordinated session {session_id} failed after {session_duration:.3f}s")
                raise original_exception
                
            finally:
                close_start_time = time.time()
                try:
                    await session.close()
                    close_duration = time.time() - close_start_time
                    logger.debug(f"[U+1F512] Coordinated session {session_id} closed in {close_duration:.3f}s")
                except Exception as close_error:
                    close_duration = time.time() - close_start_time
                    logger.error(f" WARNING: [U+FE0F] Coordinated session close failed for {session_id} "
                               f"after {close_duration:.3f}s: {close_error}")
                    
    async def queue_websocket_event(self, transaction_id: str, event_type: str, event_data: Dict[str, Any],
                                  connection_id: Optional[str] = None, user_id: Optional[str] = None,
                                  thread_id: Optional[str] = None, priority: int = 0):
        """Queue a WebSocket event to be sent after transaction commit.
        
        Args:
            transaction_id: ID of the database transaction
            event_type: Type of WebSocket event
            event_data: Event data payload
            connection_id: Optional WebSocket connection ID
            user_id: Optional user ID for targeting
            thread_id: Optional thread ID for context
            priority: Event priority (higher numbers sent first)
        """
        await self.transaction_coordinator.add_pending_event(
            transaction_id=transaction_id,
            event_type=event_type,
            event_data=event_data,
            connection_id=connection_id,
            user_id=user_id,
            thread_id=thread_id,
            priority=priority
        )
        
        logger.debug(f"[U+1F4E4] Queued WebSocket event '{event_type}' for transaction {transaction_id[:8]}... "
                    f"(user: {user_id}, priority: {priority})")
        
    def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get transaction coordination metrics for monitoring.
        
        Returns:
            Dictionary containing coordination statistics
        """
        return self.transaction_coordinator.get_coordination_metrics()
        
    async def cleanup_stale_coordination(self, max_age_minutes: int = 30) -> int:
        """Clean up stale transaction coordination data.
        
        Args:
            max_age_minutes: Maximum age of transactions to keep
            
        Returns:
            Number of stale transactions cleaned up
        """
        return await self.transaction_coordinator.cleanup_stale_transactions(max_age_minutes)

    async def health_check(self, engine_name: str = 'primary') -> Dict[str, Any]:
        """Perform health check on database connection with comprehensive logging.
        
        CRITICAL FIX: Ensures database manager is initialized before health check.
        Enhanced with detailed health monitoring for Golden Path operations.
        """
        health_check_start = time.time()
        logger.debug(f"[U+1F3E5] Starting database health check for engine: {engine_name}")
        
        try:
            # CRITICAL FIX: Ensure initialization before health check
            if not self._initialized:
                logger.info(f"[U+1F527] Initializing DatabaseManager for health check (engine: {engine_name})")
                await self.initialize()
            
            engine = self.get_engine(engine_name)
            
            # Test connection with timeout
            query_start = time.time()
            async with AsyncSession(engine) as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                health_result = result.fetchone()  # fetchone() is not awaitable
            
            query_duration = time.time() - query_start
            total_duration = time.time() - health_check_start
            
            logger.info(f" PASS:  Database health check PASSED for {engine_name} - "
                       f"Query: {query_duration:.3f}s, Total: {total_duration:.3f}s")
            
            return {
                "status": "healthy",
                "engine": engine_name,
                "connection": "ok",
                "query_duration_ms": round(query_duration * 1000, 2),
                "total_duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }
            
        except Exception as e:
            total_duration = time.time() - health_check_start
            logger.critical(f"[U+1F4A5] Database health check FAILED for {engine_name} after {total_duration:.3f}s")
            logger.error(f"Health check error details: {type(e).__name__}: {str(e)}")
            logger.error(f"This indicates database connectivity issues that will affect user operations")
            
            return {
                "status": "unhealthy",
                "engine": engine_name,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(total_duration * 1000, 2),
                "timestamp": time.time()
            }
    
    # ISSUE #414 FIX: Pool management and session cleanup methods
    
    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600):
        """Clean up sessions that have been active for too long (Issue #414 fix).
        
        Args:
            max_age_seconds: Maximum age for active sessions before cleanup
        """
        current_time = time.time()
        expired_sessions = []
        
        for session_id, metadata in self._active_sessions.items():
            session_age = current_time - metadata['start_time']
            if session_age > max_age_seconds:
                expired_sessions.append(session_id)
        
        if expired_sessions:
            logger.warning(f"[U+1F9F9] Cleaning up {len(expired_sessions)} expired database sessions (Issue #414 fix)")
            
            for session_id in expired_sessions:
                try:
                    session_meta = self._active_sessions.pop(session_id)
                    self._pool_stats['active_sessions_count'] -= 1
                    self._pool_stats['sessions_cleaned_up'] += 1
                    
                    logger.info(f"[U+1F9F9] Cleaned up expired session {session_id} for user {session_meta.get('user_id', 'unknown')}")
                except Exception as e:
                    logger.error(f"Failed to cleanup expired session {session_id}: {e}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current database pool statistics (Issue #414 monitoring)."""
        pool_size = getattr(self.config, 'database_pool_size', 25)
        max_overflow = getattr(self.config, 'database_max_overflow', 50)
        total_capacity = pool_size + max_overflow
        
        return {
            **self._pool_stats,
            'pool_configuration': {
                'pool_size': pool_size,
                'max_overflow': max_overflow,
                'total_capacity': total_capacity
            },
            'pool_utilization': {
                'utilization_percent': round((self._pool_stats['active_sessions_count'] / total_capacity) * 100, 2),
                'sessions_remaining': total_capacity - self._pool_stats['active_sessions_count']
            },
            'active_sessions_by_user': self._get_sessions_by_user()
        }
    
    def _get_sessions_by_user(self) -> Dict[str, int]:
        """Get count of active sessions per user (Issue #414 monitoring)."""
        user_counts = {}
        for metadata in self._active_sessions.values():
            user_id = metadata.get('user_id', 'unknown')
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        return user_counts
    
    def register_session_lifecycle_callback(self, callback: Callable):
        """Register callback for session lifecycle events (Issue #414 cleanup).
        
        Args:
            callback: Function to call on session cleanup, receives session metadata
        """
        if callback not in self._session_lifecycle_callbacks:
            self._session_lifecycle_callbacks.append(callback)
            logger.debug(f"Registered session lifecycle callback: {callback.__name__}")
    
    async def force_cleanup_user_sessions(self, user_id: str):
        """Force cleanup of all sessions for a specific user (Issue #414 isolation).
        
        Args:
            user_id: User ID to cleanup sessions for
        """
        user_sessions = [
            session_id for session_id, metadata in self._active_sessions.items()
            if metadata.get('user_id') == user_id
        ]
        
        if user_sessions:
            logger.info(f"[U+1F9F9] Force cleaning up {len(user_sessions)} sessions for user {user_id} (Issue #414 isolation)")
            
            for session_id in user_sessions:
                try:
                    session_meta = self._active_sessions.pop(session_id)
                    self._pool_stats['active_sessions_count'] -= 1
                    self._pool_stats['sessions_cleaned_up'] += 1
                    
                    # Call lifecycle callbacks
                    for callback in self._session_lifecycle_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(session_meta)
                            else:
                                callback(session_meta)
                        except Exception as callback_error:
                            logger.warning(f"Session lifecycle callback failed: {callback_error}")
                            
                except Exception as e:
                    logger.error(f"Failed to force cleanup session {session_id} for user {user_id}: {e}")
    
    async def close_all(self):
        """Close all database engines with comprehensive logging."""
        if not self._engines:
            logger.debug("No database engines to close")
            return
            
        logger.info(f"[U+1F512] Closing {len(self._engines)} database engines...")
        
        for name, engine in self._engines.items():
            close_start = time.time()
            try:
                await engine.dispose()
                close_duration = time.time() - close_start
                logger.info(f" PASS:  Closed database engine '{name}' in {close_duration:.3f}s")
            except Exception as e:
                close_duration = time.time() - close_start
                logger.error(f" FAIL:  Error closing engine '{name}' after {close_duration:.3f}s: {e}")
                logger.warning(f"Engine '{name}' may have active connections that were forcibly closed")
        
        engines_count = len(self._engines)
        self._engines.clear()
        self._initialized = False
        logger.info(f"[U+1F512] DatabaseManager shutdown complete - {engines_count} engines closed")
    
    def _get_database_url(self) -> str:
        """Get database URL using DatabaseURLBuilder as SSOT.
        
        Returns:
            Properly formatted database URL from DatabaseURLBuilder
        """
        env = get_env()
        
        # Create DatabaseURLBuilder instance if not exists
        if not self._url_builder:
            self._url_builder = DatabaseURLBuilder(env.as_dict())
        
        # Get URL for current environment
        database_url = self._url_builder.get_url_for_environment(sync=False)
        
        if not database_url:
            # Let the config handle the fallback if needed
            database_url = self.config.database_url
            if not database_url:
                raise ValueError(
                    "DatabaseURLBuilder failed to construct URL and no config fallback available. "
                    "Ensure proper POSTGRES_* environment variables are set."
                )
        
        # CRITICAL: Use DatabaseURLBuilder to format URL for asyncpg driver
        # NEVER use string.replace() or manual manipulation - DatabaseURLBuilder is SSOT
        # This handles all driver-specific formatting including postgresql:// -> postgresql+asyncpg://
        database_url = self._url_builder.format_url_for_driver(database_url, 'asyncpg')
        
        # Log safe connection info
        logger.info(self._url_builder.get_safe_log_message())
        
        return database_url
    
    @staticmethod
    def get_migration_url_sync_format() -> str:
        """Get database URL in sync format for Alembic migrations.
        
        Returns:
            Properly formatted sync database URL for migrations
        """
        env = get_env()
        url_builder = DatabaseURLBuilder(env.as_dict())
        
        # Get sync URL for migrations
        migration_url = url_builder.get_url_for_environment(sync=True)
        
        if not migration_url:
            raise ValueError("Could not determine migration database URL")
        
        # Ensure the URL is in sync format by removing async drivers
        if "postgresql+asyncpg://" in migration_url:
            migration_url = migration_url.replace("postgresql+asyncpg://", "postgresql://")
        
        return migration_url
    
    @classmethod
    @asynccontextmanager
    async def get_async_session(cls, name: str = 'primary', user_id: Optional[str] = None, operation_type: str = "legacy_access"):
        """
        Class method for backward compatibility with code expecting DatabaseManager.get_async_session().
        
        CRITICAL FIX: Enhanced with auto-initialization safety for staging environment.
        Enhanced with user context tracking for Golden Path operations.
        
        This method provides the expected static/class method interface while using
        the instance method internally for proper session management.
        
        Args:
            name: Engine name (default: 'primary')
            user_id: User ID for session tracking (Golden Path context)
            operation_type: Type of operation for logging context
            
        Yields:
            AsyncSession: Database session with automatic cleanup
            
        Note:
            This is a compatibility shim. New code should use:
            - netra_backend.app.database.get_db() for dependency injection
            - instance.get_session() for direct usage
        """
        logger.debug(f"[U+1F4DE] Legacy database session access: {operation_type} (user: {user_id or 'system'})")
        
        manager = get_database_manager()
        # CRITICAL FIX: Ensure initialization - manager should auto-initialize, but double-check
        if not manager._initialized:
            logger.info(f"[U+1F527] Ensuring DatabaseManager initialization for class method access ({operation_type})")
            await manager.initialize()
        
        async with manager.get_session(name, user_id=user_id, operation_type=operation_type) as session:
            yield session
    
    @staticmethod
    def create_application_engine() -> AsyncEngine:
        """Create a new application engine for health checks."""
        config = get_config()
        env = get_env()
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Get URL from builder
        database_url = builder.get_url_for_environment(sync=False)
        if not database_url:
            database_url = config.database_url
        
        # Use DatabaseURLBuilder to format URL for asyncpg driver - NO MANUAL STRING MANIPULATION
        database_url = builder.format_url_for_driver(database_url, 'asyncpg')
        
        return create_async_engine(
            database_url,
            echo=False,  # Don't echo in health checks
            poolclass=NullPool,  # Use NullPool for health check connections
            pool_pre_ping=True,
            pool_recycle=3600,
        )


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create global database manager instance with SSOT auto-initialization.
    
    CRITICAL FIX: Auto-initializes the database manager to prevent 
    "DatabaseManager not initialized" errors in staging environment.
    
    This hotfix ensures that the legacy DatabaseManager pattern works
    with SSOT compliance while we migrate to the canonical database module.
    """
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
        # CRITICAL FIX: Auto-initialize using SSOT pattern
        # This prevents "DatabaseManager not initialized" errors in staging
        try:
            import asyncio
            # Check if we're in an async context and have an event loop
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, we'll handle initialization on first async use
                logger.debug("No event loop available for immediate DatabaseManager initialization")
            
            if loop is not None:
                # We have an event loop, schedule initialization as a task
                try:
                    asyncio.create_task(_database_manager.initialize())
                    logger.debug("Scheduled DatabaseManager initialization as async task")
                except Exception as init_error:
                    logger.warning(f"Could not schedule immediate initialization: {init_error}")
                    # Still return the manager - it will auto-initialize on first async use
        except Exception as e:
            logger.warning(f"Auto-initialization setup failed, will initialize on first use: {e}")
            # This is safe - the manager will still work, just initialize on first async call
    
    return _database_manager


@asynccontextmanager
async def get_db_session(engine_name: str = 'primary'):
    """Helper to get database session."""
    manager = get_database_manager()
    async with manager.get_session(engine_name) as session:
        yield session