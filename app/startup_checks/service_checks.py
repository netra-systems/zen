"""
Service Checks

Handles external service connectivity (Redis, ClickHouse, LLM providers).
Maintains 8-line function limit and focused responsibility.
"""

import os
import time
import asyncio
from typing import List
from app.config import settings
from app.logging_config import central_logger as logger
from app.schemas.llm_types import LLMProvider
from .models import StartupCheckResult


class ServiceChecker:
    """Handles external service connectivity checks"""
    
    def __init__(self, app):
        self.app = app
    
    @property
    def environment(self):
        """Get current environment from settings"""
        return settings.environment.lower()
    
    @property 
    def is_staging(self):
        """Check if running in staging environment"""
        return self.environment == "staging" or os.getenv("K_SERVICE")
    
    async def check_redis(self) -> StartupCheckResult:
        """Check Redis connection"""
        try:
            timeout = 5 if self.is_staging else 30
            
            redis_manager = self.app.state.redis_manager
            await asyncio.wait_for(redis_manager.connect(), timeout=timeout)
            
            await self._test_redis_operations(redis_manager)
            
            return StartupCheckResult(
                name="redis_connection",
                success=True,
                message="Redis connected and operational",
                critical=(self.environment == "production")
            )
        except Exception as e:
            critical = self.environment == "production"
            if not critical:
                logger.warning("Redis not available - caching disabled")
                
            return StartupCheckResult(
                name="redis_connection",
                success=False,
                message=f"Redis connection failed: {e}",
                critical=critical
            )
    
    async def check_clickhouse(self) -> StartupCheckResult:
        """Check ClickHouse connection"""
        try:
            timeout = 5 if self.is_staging else 30
            tables = await asyncio.wait_for(self._check_clickhouse_tables(), timeout=timeout)
            
            required_tables = ['workload_events']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                raise ValueError(f"Missing ClickHouse tables: {missing_tables}")
            
            return StartupCheckResult(
                name="clickhouse_connection",
                success=True,
                message=f"ClickHouse connected with {len(tables)} tables",
                critical=False
            )
        except Exception as e:
            critical = self.environment == "production"
            if not critical:
                logger.warning("ClickHouse not available - analytics features limited")
                
            return StartupCheckResult(
                name="clickhouse_connection",
                success=False,
                message=f"ClickHouse check failed: {e}",
                critical=critical
            )
    
    async def check_llm_providers(self) -> StartupCheckResult:
        """Check LLM provider configuration and connectivity"""
        try:
            llm_manager = self.app.state.llm_manager
            available_providers = []
            failed_providers = []
            
            for llm_name in settings.llm_configs:
                try:
                    llm = llm_manager.get_llm(llm_name)
                    if llm is not None:
                        available_providers.append(llm_name)
                    else:
                        logger.info(f"LLM '{llm_name}' not available (optional provider without key)")
                        
                except Exception as e:
                    # settings.llm_configs is a list, not a dict
                    failed_providers.append(f"{llm_name}: {e}")
                    logger.info(f"LLM '{llm_name}' failed: {e}")
            
            return self._create_llm_result(available_providers, failed_providers)
            
        except Exception as e:
            return StartupCheckResult(
                name="llm_providers",
                success=False,
                message=f"LLM check failed: {e}",
                critical=(self.environment == "production")
            )
    
    async def _test_redis_operations(self, redis_manager) -> None:
        """Test Redis read/write operations"""
        test_key = "startup_check_test"
        test_value = str(time.time())
        
        await redis_manager.set(test_key, test_value, expire=10)
        retrieved = await redis_manager.get(test_key)
        
        if retrieved != test_value:
            raise ValueError("Redis read/write test failed")
        
        await redis_manager.delete(test_key)
    
    async def _check_clickhouse_tables(self) -> List[str]:
        """Check ClickHouse tables"""
        from app.db.clickhouse import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            client.ping()
            
            result = client.execute(
                "SELECT name FROM system.tables WHERE database = currentDatabase()"
            )
            # Handle both sync and async result types
            if asyncio.iscoroutine(result):
                result = await result
            return [row.get('name', row) if isinstance(row, dict) else row[0] for row in result]
    
    def _create_llm_result(self, available_providers: List[str], failed_providers: List[str]) -> StartupCheckResult:
        """Create LLM providers check result"""
        if not available_providers:
            return self._create_no_providers_result()
        elif failed_providers:
            return self._create_partial_providers_result(available_providers, failed_providers)
        else:
            return self._create_all_providers_result(available_providers)
    
    def _create_no_providers_result(self) -> StartupCheckResult:
        """Create result when no providers are available"""
        return StartupCheckResult(
            name="llm_providers",
            success=False,
            message="No LLM providers available",
            critical=True
        )
    
    def _create_partial_providers_result(self, available_providers: List[str], failed_providers: List[str]) -> StartupCheckResult:
        """Create result when some providers failed"""
        message = f"LLM providers: {len(available_providers)} available, {len(failed_providers)} failed"
        return StartupCheckResult(
            name="llm_providers", success=True, message=message, critical=False
        )
    
    def _create_all_providers_result(self, available_providers: List[str]) -> StartupCheckResult:
        """Create result when all providers are available"""
        return StartupCheckResult(
            name="llm_providers",
            success=True,
            message=f"All {len(available_providers)} LLM providers configured",
            critical=False
        )