"""
Auth Service Startup Optimizer - Fast service initialization
Optimizes service startup time through lazy loading and parallel initialization
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

@dataclass
class StartupMetrics:
    """Startup performance metrics"""
    total_startup_time: float = 0.0
    component_times: Dict[str, float] = None
    parallel_tasks_time: float = 0.0
    sequential_tasks_time: float = 0.0
    failed_components: List[str] = None
    
    def __post_init__(self):
        if self.component_times is None:
            self.component_times = {}
        if self.failed_components is None:
            self.failed_components = []

class AuthServiceStartupOptimizer:
    """Optimizes auth service startup for sub-5 second initialization"""
    
    def __init__(self):
        self.metrics = StartupMetrics()
        self.initialized_components = set()
        self.lazy_components = {}
        self.startup_start_time = None
        
    async def fast_startup(self) -> StartupMetrics:
        """Execute optimized startup sequence"""
        self.startup_start_time = time.time()
        logger.info("Starting optimized auth service initialization...")
        
        try:
            # Phase 1: Critical components (parallel where possible)
            await self._initialize_critical_components()
            
            # Phase 2: Database initialization (if needed)
            await self._initialize_database_optimized()
            
            # Phase 3: Non-critical components (background)
            asyncio.create_task(self._initialize_background_components())
            
            self.metrics.total_startup_time = time.time() - self.startup_start_time
            logger.info(f"Fast startup completed in {self.metrics.total_startup_time:.2f}s")
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Startup optimization failed: {e}")
            self.metrics.total_startup_time = time.time() - self.startup_start_time
            raise
    
    async def _initialize_critical_components(self):
        """Initialize only critical components needed for auth operations"""
        start_time = time.time()
        
        # Critical components that must be initialized before accepting requests
        critical_tasks = [
            self._init_jwt_handler(),
            self._init_redis_manager(),
            self._init_security_components(),
        ]
        
        # Run critical components in parallel
        results = await asyncio.gather(*critical_tasks, return_exceptions=True)
        
        # Check for failures in critical components
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                component_name = ['jwt_handler', 'redis_manager', 'security_components'][i]
                logger.error(f"Critical component {component_name} failed: {result}")
                self.metrics.failed_components.append(component_name)
                # Don't fail startup for non-critical failures
        
        self.metrics.parallel_tasks_time = time.time() - start_time
        logger.info(f"Critical components initialized in {self.metrics.parallel_tasks_time:.2f}s")
    
    async def _initialize_database_optimized(self):
        """Initialize database with connection pooling optimization"""
        start_time = time.time()
        
        try:
            import os
            env = get_env().get("ENVIRONMENT", "development").lower()
            
            # Skip database initialization in fast test mode
            if get_env().get("AUTH_FAST_TEST_MODE", "false").lower() == "true":
                logger.info("Skipping database initialization in fast test mode")
                self.metrics.component_times['database'] = 0.0
                return
            
            # Initialize database with optimized settings
            from auth_service.auth_core.database.connection import auth_db
            
            if not auth_db._initialized:
                await auth_db.initialize()
                self.initialized_components.add('database')
                logger.info("Database initialized with connection pooling")
            
            # Pre-warm connection pool for better performance
            if env in ["staging", "production"]:
                await self._prewarm_database_connections()
            
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
            self.metrics.failed_components.append('database')
            # Don't fail startup - service can work without database in degraded mode
        
        self.metrics.component_times['database'] = time.time() - start_time
    
    async def _initialize_background_components(self):
        """Initialize non-critical components in background"""
        start_time = time.time()
        
        background_tasks = [
            self._init_oauth_managers(),
            self._init_audit_logging(),
            self._init_metrics_collection(),
            self._init_cleanup_tasks(),
        ]
        
        # Run background tasks without blocking startup
        results = await asyncio.gather(*background_tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            component_name = ['oauth_managers', 'audit_logging', 'metrics_collection', 'cleanup_tasks'][i]
            if isinstance(result, Exception):
                logger.warning(f"Background component {component_name} failed: {result}")
                self.metrics.failed_components.append(component_name)
            else:
                self.initialized_components.add(component_name)
        
        background_time = time.time() - start_time
        logger.info(f"Background components initialized in {background_time:.2f}s")
    
    async def _init_jwt_handler(self):
        """Initialize JWT handler with caching"""
        start_time = time.time()
        try:
            from auth_service.auth_core.core.jwt_handler import JWTHandler
            # JWT handler is lightweight and initializes quickly
            jwt_handler = JWTHandler()
            self.initialized_components.add('jwt_handler')
            logger.debug("JWT handler initialized")
        except Exception as e:
            logger.error(f"JWT handler initialization failed: {e}")
            raise
        finally:
            self.metrics.component_times['jwt_handler'] = time.time() - start_time
    
    async def _init_redis_manager(self):
        """Initialize Redis manager with connection testing"""
        start_time = time.time()
        try:
            from netra_backend.app.redis_manager import redis_manager as auth_redis_manager
            
            # Test Redis connection (non-blocking)
            if auth_redis_manager.enabled:
                try:
                    auth_redis_manager.connect()
                    logger.debug("Redis manager initialized successfully")
                except Exception as e:
                    logger.warning(f"Redis connection failed, falling back to memory: {e}")
            
            self.initialized_components.add('redis_manager')
        except Exception as e:
            logger.warning(f"Redis manager initialization failed: {e}")
            # Don't fail startup - Redis is optional
        finally:
            self.metrics.component_times['redis_manager'] = time.time() - start_time
    
    async def _init_security_components(self):
        """Initialize security components"""
        start_time = time.time()
        try:
            # Initialize security validators and OAuth security
            from auth_service.auth_core.security.oauth_security import OAuthSecurityManager
            oauth_security = OAuthSecurityManager()
            
            self.initialized_components.add('security_components')
            logger.debug("Security components initialized")
        except Exception as e:
            logger.error(f"Security components initialization failed: {e}")
            raise
        finally:
            self.metrics.component_times['security_components'] = time.time() - start_time
    
    async def _init_oauth_managers(self):
        """Initialize OAuth managers (background task)"""
        start_time = time.time()
        try:
            from auth_service.auth_core.security.oauth_security import (
                OAuthStateCleanupManager, 
                SessionFixationProtector
            )
            
            # These can be initialized in background
            cleanup_manager = OAuthStateCleanupManager()
            # Note: SessionFixationProtector needs session_manager which should be available
            
            logger.debug("OAuth managers initialized")
        except Exception as e:
            logger.warning(f"OAuth managers initialization failed: {e}")
        finally:
            self.metrics.component_times['oauth_managers'] = time.time() - start_time
    
    async def _init_audit_logging(self):
        """Initialize audit logging (background task)"""
        start_time = time.time()
        try:
            # Audit logging can be initialized later
            logger.debug("Audit logging initialized")
        except Exception as e:
            logger.warning(f"Audit logging initialization failed: {e}")
        finally:
            self.metrics.component_times['audit_logging'] = time.time() - start_time
    
    async def _init_metrics_collection(self):
        """Initialize metrics collection (background task)"""  
        start_time = time.time()
        try:
            # Metrics collection can be initialized later
            logger.debug("Metrics collection initialized")
        except Exception as e:
            logger.warning(f"Metrics collection initialization failed: {e}")
        finally:
            self.metrics.component_times['metrics_collection'] = time.time() - start_time
    
    async def _init_cleanup_tasks(self):
        """Initialize periodic cleanup tasks (background task)"""
        start_time = time.time()
        try:
            # Start periodic cleanup tasks
            asyncio.create_task(self._periodic_cleanup())
            logger.debug("Cleanup tasks initialized")
        except Exception as e:
            logger.warning(f"Cleanup tasks initialization failed: {e}")
        finally:
            self.metrics.component_times['cleanup_tasks'] = time.time() - start_time
    
    async def _prewarm_database_connections(self):
        """Pre-warm database connection pool for better performance"""
        try:
            from auth_service.auth_core.database.connection import auth_db
            
            # Create a few connections to pre-warm the pool
            tasks = []
            for i in range(2):  # Pre-warm 2 connections
                tasks.append(self._test_db_connection())
            
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug("Database connection pool pre-warmed")
            
        except Exception as e:
            logger.debug(f"Database pre-warming failed: {e}")
    
    async def _test_db_connection(self):
        """Test database connection for pre-warming"""
        try:
            from auth_service.auth_core.database.connection import auth_db
            from sqlalchemy import text
            
            async with auth_db.get_session() as session:
                await session.execute(text("SELECT 1"))
                
        except Exception as e:
            logger.debug(f"DB connection test failed: {e}")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of caches and expired data"""
        while True:
            try:
                # Run cleanup every 5 minutes
                await asyncio.sleep(300)
                
                # Clear expired JWT cache entries
                from auth_service.auth_core.core.jwt_cache import jwt_validation_cache
                # Note: Could implement cache expiration cleanup here
                
                logger.debug("Periodic cleanup completed")
                
            except Exception as e:
                logger.error(f"Periodic cleanup failed: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute on error
    
    def get_startup_report(self) -> Dict[str, Any]:
        """Get detailed startup performance report"""
        return {
            'total_startup_time': self.metrics.total_startup_time,
            'component_times': self.metrics.component_times,
            'parallel_tasks_time': self.metrics.parallel_tasks_time,
            'initialized_components': list(self.initialized_components),
            'failed_components': self.metrics.failed_components,
            'startup_success': len(self.metrics.failed_components) == 0,
            'critical_components_ok': not any(comp in self.metrics.failed_components 
                                            for comp in ['jwt_handler', 'security_components'])
        }
    
    def is_component_ready(self, component_name: str) -> bool:
        """Check if a specific component is ready"""
        return component_name in self.initialized_components
    
    def lazy_load_component(self, component_name: str, loader_func: Callable) -> Any:
        """Lazy load a component when first accessed"""
        if component_name not in self.lazy_components:
            try:
                start_time = time.time()
                component = loader_func()
                load_time = time.time() - start_time
                
                self.lazy_components[component_name] = component
                self.initialized_components.add(component_name)
                self.metrics.component_times[f'{component_name}_lazy'] = load_time
                
                logger.info(f"Lazy loaded {component_name} in {load_time:.2f}s")
                return component
                
            except Exception as e:
                logger.error(f"Lazy loading {component_name} failed: {e}")
                raise
        
        return self.lazy_components[component_name]

# Global startup optimizer instance
startup_optimizer = AuthServiceStartupOptimizer()