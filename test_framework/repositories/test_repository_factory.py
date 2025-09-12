"""
TestRepositoryFactory - SSOT Database Access for Testing

This factory enforces Single Source of Truth (SSOT) principles for all test database access.
It provides type-safe repository creation, automatic session management, and compliance checking.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Prevents repository pattern violations and ensures consistent database access across all tests.

REQUIREMENTS:
- SSOT enforcement for all repository access
- Type-safe factory methods for all repository types
- Automatic session management with context managers
- Transaction rollback after each test
- Compliance checking to detect violations
- Real database testing (no mocks)

CRITICAL: This replaces ALL direct SQLAlchemy usage in tests.
"""

import asyncio
import hashlib
import logging
import threading
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List, Optional, Set, Type, TypeVar, Any, Union
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

# Import existing repository patterns
from netra_backend.app.db.repositories.base_repository import BaseRepository
from netra_backend.app.db.repositories.user_repository import (
    UserRepository, SecretRepository, ToolUsageRepository
)
from auth_service.auth_core.database.repository import (
    AuthUserRepository, AuthSessionRepository, AuthAuditRepository
)

# Import environment management
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RepositoryComplianceError(Exception):
    """Raised when repository pattern violations are detected."""
    pass


@dataclass
class DatabaseConnection:
    """Database connection configuration."""
    url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    engine_name: str = "test_db"


@dataclass
class ComplianceReport:
    """Repository compliance check results."""
    violations: List[str]
    warnings: List[str]
    direct_access_detected: bool
    session_leaks: List[str]
    unclosed_transactions: List[str]
    
    @property
    def is_compliant(self) -> bool:
        """Check if repository usage is compliant."""
        return (
            not self.violations and
            not self.direct_access_detected and
            not self.session_leaks and
            not self.unclosed_transactions
        )


class TestRepositoryFactory:
    """
    SSOT Factory for all test database repository access.
    
    Features:
    - Type-safe repository creation for all repository types
    - Automatic session management with context managers
    - Transaction rollback after each test
    - Compliance checking to detect violations
    - Database reset utilities
    - Test data factories
    - Real PostgreSQL container support
    
    CRITICAL: This is the ONLY way tests should access repositories.
    All direct SQLAlchemy usage in tests violates SSOT principles.
    """
    
    _instance: Optional['TestRepositoryFactory'] = None
    _lock = threading.RLock()
    
    def __new__(cls) -> 'TestRepositoryFactory':
        """Ensure singleton behavior with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the test repository factory."""
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized'):
            return
            
        with self._lock:
            if hasattr(self, '_initialized'):
                return
                
            self.env = IsolatedEnvironment.get_instance()
            self._engines: Dict[str, Any] = {}
            self._session_makers: Dict[str, Any] = {}
            self._active_sessions: Set[AsyncSession] = set()
            self._session_tracking: Dict[AsyncSession, Dict[str, Any]] = {}
            self._compliance_violations: List[str] = []
            self._transaction_stack: List[Dict[str, Any]] = []
            
            logger.info("TestRepositoryFactory initialized")
            self._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'TestRepositoryFactory':
        """Get the singleton instance."""
        return cls()
    
    def _get_database_url(self, service: str = "backend") -> str:
        """
        Get database URL for specified service.
        
        Args:
            service: Service name ("backend" or "auth")
            
        Returns:
            Database URL for the service
            
        Raises:
            RepositoryComplianceError: If database configuration is invalid
        """
        if service == "backend":
            # Use test database URL if available, otherwise construct from components
            db_url = self.env.get("TEST_DATABASE_URL")
            if db_url:
                return db_url
                
            # Construct from components
            host = self.env.get("POSTGRES_HOST", "localhost")
            port = self.env.get("POSTGRES_PORT", "5433")  # Dev/test port
            user = self.env.get("POSTGRES_USER", "postgres")
            password = self.env.get("POSTGRES_PASSWORD", "postgres")
            db_name = self.env.get("POSTGRES_DB", "netra_test")
            
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
            
        elif service == "auth":
            # Auth service database URL
            db_url = self.env.get("AUTH_TEST_DATABASE_URL")
            if db_url:
                return db_url
                
            # Construct auth database URL
            host = self.env.get("AUTH_POSTGRES_HOST", self.env.get("POSTGRES_HOST", "localhost"))
            port = self.env.get("AUTH_POSTGRES_PORT", self.env.get("POSTGRES_PORT", "5433"))
            user = self.env.get("AUTH_POSTGRES_USER", self.env.get("POSTGRES_USER", "postgres"))
            password = self.env.get("AUTH_POSTGRES_PASSWORD", self.env.get("POSTGRES_PASSWORD", "postgres"))
            db_name = self.env.get("AUTH_POSTGRES_DB", "auth_test")
            
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
        else:
            raise RepositoryComplianceError(f"Unknown service: {service}")
    
    async def _get_engine(self, service: str = "backend"):
        """Get or create database engine for service."""
        if service not in self._engines:
            db_url = self._get_database_url(service)
            
            # Create engine with test-optimized settings
            self._engines[service] = create_async_engine(
                db_url,
                echo=False,  # Set to True for SQL debugging
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_pre_ping=True,
                # Use StaticPool for SQLite in-memory databases if needed
                poolclass=StaticPool if "sqlite" in db_url else None,
                connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
            )
            
            logger.debug(f"Created database engine for {service}: {db_url}")
        
        return self._engines[service]
    
    async def _get_session_maker(self, service: str = "backend"):
        """Get or create session maker for service."""
        if service not in self._session_makers:
            engine = await self._get_engine(service)
            self._session_makers[service] = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Keep objects accessible after commit
                autoflush=True,
                autocommit=False
            )
            
            logger.debug(f"Created session maker for {service}")
        
        return self._session_makers[service]
    
    @asynccontextmanager
    async def get_test_session(self, service: str = "backend", rollback: bool = True) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a managed test database session with automatic cleanup.
        
        Args:
            service: Service name ("backend" or "auth")
            rollback: Whether to rollback transaction after test (default: True)
            
        Yields:
            AsyncSession: Database session for testing
            
        Example:
            async with factory.get_test_session() as session:
                user_repo = factory.create_user_repository(session)
                user = await user_repo.create(name="Test User", email="test@example.com")
                # Transaction automatically rolled back
        """
        session_maker = await self._get_session_maker(service)
        session = session_maker()
        
        # Track session for compliance monitoring
        session_info = {
            "service": service,
            "created_at": datetime.now(),
            "stack_trace": traceback.format_stack(),
            "rollback_enabled": rollback
        }
        
        self._active_sessions.add(session)
        self._session_tracking[session] = session_info
        
        try:
            # Begin transaction
            async with session.begin():
                logger.debug(f"Created test session for {service} (rollback: {rollback})")
                yield session
                
                if rollback:
                    # Rollback transaction to clean up test data
                    await session.rollback()
                    logger.debug(f"Rolled back test session for {service}")
                else:
                    # Commit if rollback is disabled
                    await session.commit()
                    logger.debug(f"Committed test session for {service}")
                    
        except Exception as e:
            # Always rollback on error
            await session.rollback()
            logger.error(f"Test session error, rolled back: {e}")
            raise
        finally:
            # Clean up session tracking
            self._active_sessions.discard(session)
            self._session_tracking.pop(session, None)
            
            # Close session
            await session.close()
            logger.debug(f"Closed test session for {service}")
    
    # Type-safe repository creation methods
    
    def create_user_repository(self, session: Optional[AsyncSession] = None) -> UserRepository:
        """
        Create UserRepository instance with session management.
        
        Args:
            session: Optional session (if None, must use get_test_session)
            
        Returns:
            UserRepository instance
            
        Example:
            async with factory.get_test_session() as session:
                user_repo = factory.create_user_repository(session)
                user = await user_repo.create(name="Test", email="test@example.com")
        """
        if session is None:
            raise RepositoryComplianceError(
                "Session required. Use: async with factory.get_test_session() as session"
            )
            
        self._validate_session_compliance(session)
        
        # UserRepository uses legacy pattern, adapt it
        repo = UserRepository()
        # Override session access methods to use provided session
        repo._get_session = lambda: session
        
        logger.debug("Created UserRepository with managed session")
        return repo
    
    def create_secret_repository(self, session: AsyncSession) -> SecretRepository:
        """Create SecretRepository instance with session management."""
        if session is None:
            raise RepositoryComplianceError(
                "Session required. Use: async with factory.get_test_session() as session"
            )
            
        self._validate_session_compliance(session)
        return SecretRepository(session)
    
    def create_tool_usage_repository(self, session: AsyncSession) -> ToolUsageRepository:
        """Create ToolUsageRepository instance with session management."""
        if session is None:
            raise RepositoryComplianceError(
                "Session required. Use: async with factory.get_test_session() as session"
            )
            
        self._validate_session_compliance(session)
        return ToolUsageRepository(session)
    
    # Auth service repositories
    
    async def create_auth_user_repository(self, service: str = "auth") -> AuthUserRepository:
        """
        Create AuthUserRepository with managed session.
        
        Returns:
            Contextual repository that manages its own session
        """
        session_maker = await self._get_session_maker(service)
        
        class ManagedAuthUserRepository(AuthUserRepository):
            """AuthUserRepository with managed session lifecycle."""
            
            def __init__(self, session_factory):
                self._session_factory = session_factory
                self._session = None
                
            async def __aenter__(self):
                self._session = self._session_factory()
                super().__init__(self._session)
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self._session:
                    if exc_type:
                        await self._session.rollback()
                    await self._session.close()
        
        return ManagedAuthUserRepository(session_maker)
    
    async def create_auth_session_repository(self, service: str = "auth") -> AuthSessionRepository:
        """Create AuthSessionRepository with managed session."""
        session_maker = await self._get_session_maker(service)
        
        class ManagedAuthSessionRepository(AuthSessionRepository):
            """AuthSessionRepository with managed session lifecycle."""
            
            def __init__(self, session_factory):
                self._session_factory = session_factory
                self._session = None
                
            async def __aenter__(self):
                self._session = self._session_factory()
                super().__init__(self._session)
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self._session:
                    if exc_type:
                        await self._session.rollback()
                    await self._session.close()
        
        return ManagedAuthSessionRepository(session_maker)
    
    async def create_auth_audit_repository(self, service: str = "auth") -> AuthAuditRepository:
        """Create AuthAuditRepository with managed session."""
        session_maker = await self._get_session_maker(service)
        
        class ManagedAuthAuditRepository(AuthAuditRepository):
            """AuthAuditRepository with managed session lifecycle."""
            
            def __init__(self, session_factory):
                self._session_factory = session_factory
                self._session = None
                
            async def __aenter__(self):
                self._session = self._session_factory()
                super().__init__(self._session)
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self._session:
                    if exc_type:
                        await self._session.rollback()
                    await self._session.close()
        
        return ManagedAuthAuditRepository(session_maker)
    
    # Compliance checking methods
    
    def _validate_session_compliance(self, session: AsyncSession) -> None:
        """Validate that session is properly managed."""
        if session not in self._session_tracking:
            self._compliance_violations.append(
                f"Session {id(session)} not created through TestRepositoryFactory"
            )
            raise RepositoryComplianceError(
                "Session must be created through TestRepositoryFactory.get_test_session()"
            )
    
    def validate_no_direct_access(self) -> ComplianceReport:
        """
        Validate that no direct SQLAlchemy access is being used.
        
        This method checks the call stack for direct SQLAlchemy usage patterns
        that bypass the repository pattern.
        
        Returns:
            ComplianceReport with violation details
        """
        violations = []
        warnings = []
        direct_access_detected = False
        session_leaks = []
        unclosed_transactions = []
        
        # Check for active sessions that weren't created through factory
        for session in self._active_sessions:
            if session not in self._session_tracking:
                session_leaks.append(f"Untracked session: {id(session)}")
                direct_access_detected = True
        
        # Check for unclosed transactions
        for session, info in self._session_tracking.items():
            if session.in_transaction():
                unclosed_transactions.append(
                    f"Session {id(session)} has unclosed transaction from {info['service']}"
                )
        
        # Add any accumulated violations
        violations.extend(self._compliance_violations)
        
        # Check call stack for direct SQLAlchemy imports
        import sys
        frame = sys._getframe()
        while frame:
            code = frame.f_code
            filename = code.co_filename
            
            # Skip internal frames
            if any(skip in filename for skip in ["sqlalchemy", "test_repository_factory", "__init__"]):
                frame = frame.f_back
                continue
                
            # Look for direct SQLAlchemy usage in test files
            if "test_" in filename or "tests/" in filename:
                local_vars = frame.f_locals
                if any(key.startswith("session") for key in local_vars if not key.startswith("_")):
                    # Check if it's our managed session
                    for var_name, var_value in local_vars.items():
                        if (isinstance(var_value, AsyncSession) and 
                            var_value not in self._session_tracking):
                            warnings.append(
                                f"Direct session usage detected in {filename}:{frame.f_lineno}"
                            )
            
            frame = frame.f_back
        
        return ComplianceReport(
            violations=violations,
            warnings=warnings,
            direct_access_detected=direct_access_detected,
            session_leaks=session_leaks,
            unclosed_transactions=unclosed_transactions
        )
    
    # Test utilities and helper functions
    
    async def reset_database(self, service: str = "backend") -> None:
        """
        Reset database to clean state for testing.
        
        DANGER: This truncates ALL tables. Only use in test environments.
        """
        if not self.env.get_environment_name() in ["test", "development"]:
            raise RepositoryComplianceError(
                f"Database reset not allowed in {self.env.get_environment_name()} environment"
            )
        
        async with self.get_test_session(service, rollback=False) as session:
            try:
                # Get all table names
                inspector = inspect(session.bind)
                table_names = await session.run_sync(inspector.get_table_names)
                
                if table_names:
                    # Disable foreign key constraints
                    await session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                    
                    # Truncate all tables
                    for table in table_names:
                        await session.execute(text(f"TRUNCATE TABLE {table}"))
                    
                    # Re-enable foreign key constraints
                    await session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                    
                    await session.commit()
                    logger.info(f"Reset {len(table_names)} tables in {service} database")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Database reset failed for {service}: {e}")
                raise
    
    async def create_test_data_factories(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Create test data factories for common test scenarios.
        
        Args:
            session: Database session for creating test data
            
        Returns:
            Dictionary of factory functions
        """
        factories = {}
        
        # User factory
        async def create_test_user(
            name: str = "Test User",
            email: Optional[str] = None,
            **kwargs
        ):
            if email is None:
                # Generate unique email
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                email = f"test_{timestamp}@example.com"
            
            user_repo = self.create_user_repository(session)
            return await user_repo.create_user(session, {
                "full_name": name,
                "email": email,
                **kwargs
            })
        
        factories["create_user"] = create_test_user
        
        # Add more factories as needed
        
        return factories
    
    # Pre-commit hook integration
    
    def generate_compliance_report(self) -> str:
        """
        Generate compliance report for pre-commit hooks.
        
        Returns:
            Formatted compliance report
        """
        report = self.validate_no_direct_access()
        
        output = ["TestRepositoryFactory Compliance Report"]
        output.append("=" * 45)
        
        if report.is_compliant:
            output.append(" PASS:  All repository access is compliant")
        else:
            output.append(" FAIL:  Repository compliance violations detected")
            
        if report.violations:
            output.append(f"\nViolations ({len(report.violations)}):")
            for violation in report.violations:
                output.append(f"  - {violation}")
                
        if report.warnings:
            output.append(f"\nWarnings ({len(report.warnings)}):")
            for warning in report.warnings:
                output.append(f"  - {warning}")
                
        if report.session_leaks:
            output.append(f"\nSession Leaks ({len(report.session_leaks)}):")
            for leak in report.session_leaks:
                output.append(f"  - {leak}")
                
        if report.unclosed_transactions:
            output.append(f"\nUnclosed Transactions ({len(report.unclosed_transactions)}):")
            for transaction in report.unclosed_transactions:
                output.append(f"  - {transaction}")
        
        output.append("")
        output.append("To fix violations:")
        output.append("1. Replace direct SQLAlchemy usage with TestRepositoryFactory")
        output.append("2. Use 'async with factory.get_test_session() as session'")
        output.append("3. Create repositories through factory methods")
        
        return "\n".join(output)
    
    async def cleanup_resources(self) -> None:
        """Clean up all database resources."""
        # Close all active sessions
        for session in list(self._active_sessions):
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
        
        self._active_sessions.clear()
        self._session_tracking.clear()
        
        # Close engines
        for service, engine in self._engines.items():
            try:
                await engine.dispose()
                logger.debug(f"Closed engine for {service}")
            except Exception as e:
                logger.warning(f"Error closing engine for {service}: {e}")
        
        self._engines.clear()
        self._session_makers.clear()
        
        logger.info("TestRepositoryFactory resources cleaned up")
    
    def log_violation(self, violation: str) -> None:
        """Log a compliance violation."""
        self._compliance_violations.append(violation)
        logger.warning(f"Repository compliance violation: {violation}")


# Singleton instance
_factory_instance = TestRepositoryFactory()


def get_test_repository_factory() -> TestRepositoryFactory:
    """Get the singleton TestRepositoryFactory instance."""
    return _factory_instance


# Convenience functions for common operations
async def get_test_session(service: str = "backend", rollback: bool = True):
    """Convenience function to get test session."""
    factory = get_test_repository_factory()
    return factory.get_test_session(service, rollback)


async def create_test_repositories(session: AsyncSession) -> Dict[str, Any]:
    """Create all common test repositories for a session."""
    factory = get_test_repository_factory()
    
    return {
        "user": factory.create_user_repository(session),
        "secret": factory.create_secret_repository(session),
        "tool_usage": factory.create_tool_usage_repository(session),
    }


def check_repository_compliance() -> ComplianceReport:
    """Check repository compliance across the application."""
    factory = get_test_repository_factory()
    return factory.validate_no_direct_access()


# Legacy compatibility warning
def _deprecated_direct_session_warning():
    """Warn about deprecated direct session usage."""
    logger.warning(
        "Direct SQLAlchemy session usage detected. "
        "Use TestRepositoryFactory.get_test_session() instead."
    )


# Monkey patch to detect direct session creation (for compliance)
original_sessionmaker = None

try:
    from sqlalchemy.ext.asyncio import async_sessionmaker
    original_async_sessionmaker = async_sessionmaker
    
    def patched_async_sessionmaker(*args, **kwargs):
        """Patched sessionmaker to detect direct usage in tests."""
        import inspect
        frame = inspect.currentframe()
        try:
            # Check if called from test context
            while frame:
                filename = frame.f_code.co_filename
                if "test_" in filename or "tests/" in filename:
                    if "test_repository_factory" not in filename:
                        get_test_repository_factory().log_violation(
                            f"Direct async_sessionmaker usage in {filename}:{frame.f_lineno}"
                        )
                        break
                frame = frame.f_back
        finally:
            del frame
        
        return original_async_sessionmaker(*args, **kwargs)
    
    # Apply patch only in test environments
    env = IsolatedEnvironment.get_instance()
    if env.is_test():
        async_sessionmaker = patched_async_sessionmaker
        logger.debug("Applied compliance monitoring patch for async_sessionmaker")
    
except ImportError:
    pass  # SQLAlchemy not available or version mismatch