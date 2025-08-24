"""
Service Checks

Handles external service connectivity (Redis, ClickHouse, LLM providers).
Maintains 25-line function limit and focused responsibility.
"""

import asyncio
import time
from typing import List

from netra_backend.app.core.configuration import unified_config_manager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.llm_types import LLMProvider
from netra_backend.app.startup_checks.models import StartupCheckResult


class ServiceChecker:
    """Handles external service connectivity checks"""
    
    def __init__(self, app):
        self.app = app
    
    @property
    def environment(self):
        """Get current environment from unified config"""
        config = unified_config_manager.get_config()
        return config.environment.lower()
    
    @property 
    def is_staging(self):
        """Check if running in staging environment"""
        config = unified_config_manager.get_config()
        return self.environment == "staging" or (hasattr(config, 'k_service') and config.k_service)
    
    async def check_redis(self) -> StartupCheckResult:
        """Check Redis connection"""
        try:
            await self._connect_and_test_redis()
            return self._create_redis_success_result()
        except Exception as e:
            return self._create_redis_failure_result(e)
    
    async def check_clickhouse(self) -> StartupCheckResult:
        """Check ClickHouse connection"""
        try:
            tables = await self._validate_clickhouse_tables()
            return self._create_clickhouse_success_result(tables)
        except Exception as e:
            return self._create_clickhouse_failure_result(e)
    
    async def check_llm_providers(self) -> StartupCheckResult:
        """Check LLM provider configuration and connectivity"""
        try:
            available_providers, failed_providers = await self._test_all_llm_providers()
            return self._create_llm_result(available_providers, failed_providers)
        except Exception as e:
            return self._create_llm_check_failure_result(e)
    
    async def _test_redis_operations(self, redis_manager) -> None:
        """Test Redis read/write operations"""
        test_data = self._prepare_redis_test_data()
        await self._execute_redis_test(redis_manager, test_data)
        await self._cleanup_redis_test(redis_manager, test_data["key"])
    
    def _prepare_redis_test_data(self) -> dict:
        """Prepare test data for Redis operations"""
        return {
            "key": "startup_check_test",
            "value": str(time.time())
        }
    
    async def _execute_redis_test(self, redis_manager, test_data: dict) -> None:
        """Execute Redis read/write test operations"""
        await redis_manager.set(test_data["key"], test_data["value"], expire=10)
        retrieved = await redis_manager.get(test_data["key"])
        if retrieved != test_data["value"]:
            raise ValueError("Redis read/write test failed")
    
    async def _cleanup_redis_test(self, redis_manager, test_key: str) -> None:
        """Clean up Redis test data"""
        await redis_manager.delete(test_key)
    
    async def _check_clickhouse_tables(self) -> List[str]:
        """Check ClickHouse tables"""
        from netra_backend.app.database import get_clickhouse_client
        
        async with get_clickhouse_client() as client:
            client.ping()
            result = await self._execute_table_query(client)
            return self._extract_table_names(result)
    
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
            critical=(self.environment == "production")
        )
    
    def _create_partial_providers_result(self, available_providers: List[str], failed_providers: List[str]) -> StartupCheckResult:
        """Create result when some providers failed"""
        message = f"LLM providers: {len(available_providers)} available, {len(failed_providers)} failed"
        return StartupCheckResult(
            name="llm_providers", success=True, message=message, critical=False
        )
    
    async def _connect_and_test_redis(self) -> None:
        """Connect to Redis and test operations"""
        timeout = 5 if self.is_staging else 30
        redis_manager = self.app.state.redis_manager
        await asyncio.wait_for(redis_manager.connect(), timeout=timeout)
        await self._test_redis_operations(redis_manager)
    
    def _create_redis_success_result(self) -> StartupCheckResult:
        """Create successful Redis check result"""
        return StartupCheckResult(
            name="redis_connection", success=True, critical=(self.environment == "production"),
            message="Redis connected and operational"
        )
    
    def _create_redis_failure_result(self, error: Exception) -> StartupCheckResult:
        """Create failed Redis check result"""
        critical = self.environment == "production"
        self._log_redis_warning_if_needed(critical)
        return StartupCheckResult(
            name="redis_connection", success=False, critical=critical,
            message=f"Redis connection failed: {error}"
        )
    
    async def _validate_clickhouse_tables(self) -> List[str]:
        """Validate ClickHouse connection and tables"""
        timeout = 5 if self.is_staging else 30
        tables = await asyncio.wait_for(self._check_clickhouse_tables(), timeout=timeout)
        self._validate_required_tables(tables)
        return tables
    
    def _create_clickhouse_success_result(self, tables: List[str]) -> StartupCheckResult:
        """Create successful ClickHouse check result"""
        return StartupCheckResult(
            name="clickhouse_connection", success=True, critical=False,
            message=f"ClickHouse connected with {len(tables)} tables"
        )
    
    def _create_clickhouse_failure_result(self, error: Exception) -> StartupCheckResult:
        """Create failed ClickHouse check result"""
        critical = self.environment == "production"
        self._log_clickhouse_warning_if_needed(critical)
        return StartupCheckResult(
            name="clickhouse_connection", success=False, critical=critical,
            message=f"ClickHouse check failed: {error}"
        )
    
    async def _test_all_llm_providers(self) -> tuple:
        """Test all LLM provider connections"""
        llm_manager = self.app.state.llm_manager
        available_providers, failed_providers = [], []
        config = unified_config_manager.get_config()
        llm_configs = getattr(config, 'llm_configs', {})
        for llm_name in llm_configs:
            available, failed = self._test_single_llm_provider(llm_manager, llm_name)
            self._process_llm_test_result(available_providers, failed_providers, available, failed)
        return available_providers, failed_providers
    
    def _test_single_llm_provider(self, llm_manager, llm_name: str) -> tuple:
        """Test single LLM provider connection"""
        try:
            llm = llm_manager.get_llm(llm_name)
            return self._handle_llm_test_result(llm, llm_name)
        except Exception as e:
            return self._handle_llm_test_failure(llm_name, e)
    
    def _handle_llm_test_result(self, llm, llm_name: str) -> tuple:
        """Handle LLM test result based on availability"""
        if llm is not None:
            return llm_name, None
        return self._handle_llm_unavailable(llm_name)
    
    def _handle_llm_unavailable(self, llm_name: str) -> tuple:
        """Handle unavailable LLM provider"""
        logger.info(f"LLM '{llm_name}' not available (optional provider without key)")
        return None, None
    
    def _handle_llm_test_failure(self, llm_name: str, error: Exception) -> tuple:
        """Handle LLM test failure"""
        failed_msg = f"{llm_name}: {error}"
        logger.info(f"LLM '{llm_name}' failed: {error}")
        return None, failed_msg
    
    def _create_llm_check_failure_result(self, error: Exception) -> StartupCheckResult:
        """Create failed LLM check result"""
        return StartupCheckResult(
            name="llm_providers", success=False, critical=(self.environment == "production"),
            message=f"LLM check failed: {error}"
        )
    
    async def _execute_table_query(self, client) -> list:
        """Execute ClickHouse table query"""
        result = client.execute(
            "SELECT name FROM system.tables WHERE database = currentDatabase()"
        )
        if asyncio.iscoroutine(result):
            result = await result
        return result
    
    def _extract_table_names(self, result: list) -> List[str]:
        """Extract table names from query result"""
        return [row.get('name', row) if isinstance(row, dict) else row[0] for row in result]
    
    def _create_all_providers_result(self, available_providers: List[str]) -> StartupCheckResult:
        """Create result when all providers are available"""
        return StartupCheckResult(
            name="llm_providers", success=True, critical=False,
            message=f"All {len(available_providers)} LLM providers configured"
        )
    
    def _log_redis_warning_if_needed(self, critical: bool) -> None:
        """Log Redis warning if not critical"""
        if not critical:
            logger.warning("Redis not available - caching disabled")
    
    def _validate_required_tables(self, tables: List[str]) -> None:
        """Validate required ClickHouse tables exist"""
        required_tables = ['workload_events']
        missing_tables = [t for t in required_tables if t not in tables]
        if missing_tables:
            raise ValueError(f"Missing ClickHouse tables: {missing_tables}")
    
    def _log_clickhouse_warning_if_needed(self, critical: bool) -> None:
        """Log ClickHouse warning if not critical"""
        if not critical:
            logger.warning("ClickHouse not available - analytics features limited")
    
    def _process_llm_test_result(self, available_providers: List[str], failed_providers: List[str], 
                                available: str, failed: str) -> None:
        """Process single LLM test result"""
        if available:
            available_providers.append(available)
        if failed:
            failed_providers.append(failed)