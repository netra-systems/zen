"""
Session Leak Test Base - Base Class for Session Leak Detection Tests

This base class provides common functionality for all session leak detection tests,
including setup, teardown, and standardized leak detection patterns.

CRITICAL: Implements CLAUDE.md testing principles with real PostgreSQL and
fails hard when session leaks are detected.
"""

import asyncio
import pytest
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

from .session_leak_tracker import SessionLeakTracker, track_session_lifecycle
from .database_session_monitor import DatabaseSessionMonitor

logger = logging.getLogger(__name__)


class SessionLeakTestBase(SSotBaseTestCase, ABC):
    """
    Base class for all session leak detection tests.
    
    Provides:
    1. Session leak tracker setup/teardown
    2. Database session monitor integration
    3. Real PostgreSQL connection for testing
    4. Standardized leak detection assertions
    5. Authentication for E2E tests
    
    CRITICAL: Uses real PostgreSQL database as per CLAUDE.md:
    "Real Everything (LLM, Services) E2E > E2E > Integration > Unit"
    """
    
    # Class attributes for session leak testing components
    session_tracker: Optional[SessionLeakTracker] = None
    session_monitor: Optional[DatabaseSessionMonitor] = None
    test_engine: Optional[AsyncEngine] = None
    db_utility: Optional[DatabaseTestUtilities] = None
    auth_helper: Optional[E2EAuthHelper] = None
    
    async def setup_session_leak_testing(
        self,
        max_session_age_seconds: float = 10.0,
        monitoring_interval: float = 0.5
    ):
        """
        Set up session leak testing infrastructure.
        
        Args:
            max_session_age_seconds: Maximum allowed session age before leak detection
            monitoring_interval: Database pool monitoring interval
        """
        # Set up database connection for testing
        self.db_utility = DatabaseTestUtilities(service="netra_backend")
        await self.db_utility.initialize()
        self.test_engine = self.db_utility.async_engine
        
        # Initialize session leak tracker
        self.session_tracker = SessionLeakTracker(
            max_session_age_seconds=max_session_age_seconds
        )
        
        # Initialize database session monitor
        self.session_monitor = DatabaseSessionMonitor(
            engine=self.test_engine,
            monitoring_interval=monitoring_interval
        )
        
        # Start monitoring
        await self.session_monitor.start_monitoring()
        
        # Set up authentication for E2E tests
        self.auth_helper = E2EAuthHelper(environment="test")
        
        logger.info("Session leak testing infrastructure initialized")
    
    async def teardown_session_leak_testing(self):
        """Clean up session leak testing infrastructure."""
        try:
            # Check for leaks before cleanup
            if self.session_tracker:
                await self.session_tracker.check_for_leaks()
            
            # Stop monitoring
            if self.session_monitor:
                await self.session_monitor.stop_monitoring()
            
            # Clean up components
            if self.session_tracker:
                await self.session_tracker.cleanup()
            
            if self.session_monitor:
                await self.session_monitor.cleanup()
            
            # Clean up database utility
            if self.db_utility:
                await self.db_utility.cleanup()
                
        except Exception as e:
            logger.error(f"Error during session leak testing cleanup: {e}")
            raise
        finally:
            logger.info("Session leak testing infrastructure cleaned up")
    
    async def create_tracked_session(self) -> AsyncSession:
        """
        Create a database session with leak tracking enabled.
        
        Returns:
            AsyncSession with leak tracking
        """
        if not self.test_engine or not self.session_tracker:
            raise RuntimeError("Session leak testing not initialized")
        
        session = await self.db_utility.get_test_session()
        await self.session_tracker.track_session(session)
        return session
    
    async def get_authenticated_context(self, user_id: Optional[str] = None):
        """
        Get authenticated user context for E2E testing.
        
        Args:
            user_id: Optional user ID (auto-generated if not provided)
            
        Returns:
            StronglyTypedUserExecutionContext with authentication
        """
        if not self.auth_helper:
            raise RuntimeError("Authentication helper not initialized")
        
        return await create_authenticated_user_context(
            user_id=user_id,
            environment="test",
            permissions=["read", "write"],
            websocket_enabled=True
        )
    
    async def execute_thread_handler_with_tracking(
        self,
        handler_func,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a thread handler function with session leak tracking.
        
        Args:
            handler_func: Thread handler function to test
            *args: Arguments for handler function
            **kwargs: Keyword arguments for handler function
            
        Returns:
            Result from handler function
        """
        if not self.session_tracker:
            raise RuntimeError("Session tracker not initialized")
        
        # Create tracked session
        session = await self.create_tracked_session()
        
        try:
            # Execute handler with session tracking
            async with track_session_lifecycle(session, self.session_tracker):
                result = await handler_func(session, *args, **kwargs)
            
            # Mark transaction state based on session state
            if hasattr(session, '_transaction') and session._transaction:
                if session._transaction.is_active:
                    # Session has active transaction - need to commit or rollback
                    try:
                        await session.commit()
                        await self.session_tracker.mark_session_committed(session)
                    except Exception:
                        await session.rollback()
                        await self.session_tracker.mark_session_rolled_back(session)
            
            return result
            
        finally:
            # Ensure session is closed
            if not session.is_closed:
                await session.close()
            await self.session_tracker.mark_session_closed(session)
    
    async def assert_no_session_leaks(self, custom_message: Optional[str] = None):
        """
        Assert that no session leaks exist.
        
        Args:
            custom_message: Optional custom error message
        
        CRITICAL: Implements CLAUDE.md principle "Tests MUST raise errors"
        """
        if not self.session_tracker or not self.session_monitor:
            raise RuntimeError("Session leak detection not initialized")
        
        # Check tracker for leaks
        leaks_detected = await self.session_tracker.check_for_leaks()
        
        # Check monitor for pool issues
        pool_analysis = await self.session_monitor.detect_session_leaks()
        
        # Generate leak report
        tracker_report = await self.session_tracker.get_leak_report()
        monitor_report = await self.session_monitor.get_monitoring_report()
        
        # Fail if any leaks detected
        if leaks_detected or pool_analysis.get('leak_detected', False):
            error_message = custom_message or "SESSION LEAKS DETECTED!"
            
            detailed_report = (
                f"\n\n{error_message}\n\n"
                f"=== SESSION TRACKER REPORT ===\n"
                f"Total sessions tracked: {tracker_report['total_sessions_tracked']}\n"
                f"Active sessions: {tracker_report['active_sessions']}\n"
                f"Leak details: {tracker_report['leak_details']}\n\n"
                f"=== DATABASE POOL ANALYSIS ===\n"
                f"Leak detected: {pool_analysis.get('leak_detected', False)}\n"
                f"Leak indicators: {pool_analysis.get('leak_indicators', [])}\n"
                f"Checkout increase: {pool_analysis.get('checkout_increase', 0)}\n"
                f"Max utilization: {pool_analysis.get('max_utilization', 0):.1f}%\n\n"
                f"=== POOL MONITORING REPORT ===\n"
                f"Current checked out: {monitor_report.get('current_state', {}).get('checked_out', 0)}\n"
                f"Pool utilization: {monitor_report.get('current_state', {}).get('utilization_percent', 0):.1f}%\n\n"
                f"CRITICAL: Fix session management in thread handlers before deployment!\n"
                f"Session leaks cause database connection pool exhaustion in production."
            )
            
            raise AssertionError(detailed_report)
    
    @abstractmethod
    async def test_session_leak_scenario(self):
        """
        Abstract method that each test must implement to define specific leak scenarios.
        
        This method should:
        1. Execute specific thread handler operations
        2. Simulate conditions that could cause session leaks
        3. Call assert_no_session_leaks() to verify no leaks occurred
        """
        pass
    
    async def simulate_concurrent_requests(
        self,
        handler_func,
        request_count: int = 5,
        concurrent_limit: int = 3,
        *args,
        **kwargs
    ) -> List[Any]:
        """
        Simulate concurrent requests to detect session leaks under load.
        
        Args:
            handler_func: Thread handler function to test
            request_count: Total number of requests to simulate
            concurrent_limit: Maximum concurrent requests
            *args: Arguments for handler function
            **kwargs: Keyword arguments for handler function
            
        Returns:
            List of results from handler executions
        """
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def execute_with_semaphore():
            async with semaphore:
                return await self.execute_thread_handler_with_tracking(
                    handler_func, *args, **kwargs
                )
        
        # Execute concurrent requests
        tasks = [execute_with_semaphore() for _ in range(request_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for any exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        if exceptions:
            logger.error(f"Concurrent execution had {len(exceptions)} exceptions")
            for i, exc in enumerate(exceptions):
                logger.error(f"Exception {i+1}: {exc}")
        
        return results