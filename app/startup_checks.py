import os
import sys
import time
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import psutil

from app.logging_config import central_logger
from app.config import settings
from app.schemas import AppConfig
from app.redis_manager import RedisManager
from app.db.clickhouse_base import ClickHouseDatabase
from app.llm.llm_manager import LLMManager
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import Assistant

logger = central_logger.get_logger(__name__)

class StartupCheckResult:
    """Result of a startup check"""
    def __init__(self, name: str, success: bool, message: str, 
                 critical: bool = True, duration_ms: float = 0):
        self.name = name
        self.success = success
        self.message = message
        self.critical = critical
        self.duration_ms = duration_ms


class StartupChecker:
    """Comprehensive startup check orchestrator"""
    
    def __init__(self, app):
        self.app = app
        self.results: List[StartupCheckResult] = []
        self.start_time = time.time()
        
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all startup checks and return results"""
        checks = [
            self.check_environment_variables,
            self.check_configuration,
            self.check_file_permissions,
            self.check_database_connection,
            self.check_redis,
            self.check_clickhouse,
            self.check_llm_providers,
            self.check_memory_and_resources,
            self.check_network_connectivity,
            self.check_or_create_assistant,
        ]
        
        for check in checks:
            try:
                start = time.time()
                await check()
                duration = (time.time() - start) * 1000
                # Update duration for last result
                if self.results:
                    self.results[-1].duration_ms = duration
            except Exception as e:
                logger.error(f"Check {check.__name__} failed unexpectedly: {e}")
                self.results.append(StartupCheckResult(
                    name=check.__name__,
                    success=False,
                    message=f"Unexpected error: {e}",
                    critical=True
                ))
        
        total_duration = (time.time() - self.start_time) * 1000
        failed_critical = [r for r in self.results if not r.success and r.critical]
        failed_non_critical = [r for r in self.results if not r.success and not r.critical]
        
        return {
            "success": len(failed_critical) == 0,
            "total_checks": len(self.results),
            "passed": len([r for r in self.results if r.success]),
            "failed_critical": len(failed_critical),
            "failed_non_critical": len(failed_non_critical),
            "duration_ms": total_duration,
            "results": self.results,
            "failures": failed_critical + failed_non_critical
        }
    
    async def check_environment_variables(self):
        """Check required environment variables are set"""
        # In development/staging mode, DATABASE_URL and SECRET_KEY might be set differently
        environment = os.getenv("ENVIRONMENT", "development").lower()
        is_dev_mode = environment == "development"
        is_staging = environment == "staging" or os.getenv("K_SERVICE")  # Cloud Run indicator
        
        required_vars = []
        # Only require these in production
        if environment == "production":
            required_vars = [
                "DATABASE_URL",
                "SECRET_KEY",
            ]
        
        optional_vars = [
            "REDIS_URL",
            "CLICKHOUSE_URL",
            "ANTHROPIC_API_KEY",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET"
        ]
        
        missing_required = []
        missing_optional = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
        
        for var in optional_vars:
            if not os.getenv(var):
                missing_optional.append(var)
        
        if missing_required:
            self.results.append(StartupCheckResult(
                name="environment_variables",
                success=False,
                message=f"Missing required environment variables: {', '.join(missing_required)}",
                critical=True
            ))
        else:
            msg = "All required environment variables are set"
            if is_dev_mode:
                msg = "Development mode - using default configs"
            if missing_optional:
                msg += f" (Optional missing: {', '.join(missing_optional)})"
            self.results.append(StartupCheckResult(
                name="environment_variables",
                success=True,
                message=msg,
                critical=True
            ))
    
    async def check_configuration(self):
        """Validate application configuration"""
        try:
            # Configuration is already loaded via pydantic validation
            # Just verify critical settings
            if not settings.database_url:
                raise ValueError("DATABASE_URL is not configured")
            
            # In dev mode, allow the default secret key
            if settings.environment not in ["development", "testing"]:
                if not settings.secret_key or len(settings.secret_key) < 32:
                    raise ValueError("SECRET_KEY must be at least 32 characters")
            
            # Check if we're in the right environment
            if settings.environment not in ["development", "testing", "staging", "production"]:
                raise ValueError(f"Invalid environment: {settings.environment}")
            
            self.results.append(StartupCheckResult(
                name="configuration",
                success=True,
                message=f"Configuration valid for {settings.environment} environment",
                critical=True
            ))
        except Exception as e:
            self.results.append(StartupCheckResult(
                name="configuration",
                success=False,
                message=str(e),
                critical=True
            ))

    async def check_file_permissions(self):
        """Check file system permissions for required directories"""
        required_dirs = [
            "logs",
            "uploads",
            "temp"
        ]
        
        issues = []
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            try:
                # Create directory if it doesn't exist
                dir_path.mkdir(exist_ok=True)
                
                # Test write permission
                test_file = dir_path / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                issues.append(f"{dir_name}: {e}")
        
        if issues:
            self.results.append(StartupCheckResult(
                name="file_permissions",
                success=False,
                message=f"Permission issues: {'; '.join(issues)}",
                critical=False
            ))
        else:
            self.results.append(StartupCheckResult(
                name="file_permissions",
                success=True,
                message="All required directories are accessible",
                critical=False
            ))
    
    async def check_database_connection(self):
        """Check PostgreSQL database connection and schema"""
        try:
            async with self.app.state.db_session_factory() as db:
                # Test basic connectivity
                result = await db.execute(text("SELECT 1"))
                result.scalar_one()
                
                # Check if critical tables exist
                critical_tables = [
                    'assistants', 'threads', 'messages', 'userbase'
                ]
                
                for table in critical_tables:
                    result = await db.execute(
                        text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table)"),
                        {"table": table}
                    )
                    exists = result.scalar_one()
                    if not exists:
                        raise ValueError(f"Critical table '{table}' does not exist")
                
                self.results.append(StartupCheckResult(
                    name="database_connection",
                    success=True,
                    message="PostgreSQL connected and schema valid",
                    critical=True
                ))
        except Exception as e:
            self.results.append(StartupCheckResult(
                name="database_connection",
                success=False,
                message=f"Database check failed: {e}",
                critical=True
            ))
    
    async def check_redis(self):
        """Check Redis connection"""
        try:
            redis_manager = self.app.state.redis_manager
            await redis_manager.connect()
            
            # Test write/read
            test_key = "startup_check_test"
            test_value = str(time.time())
            await redis_manager.set(test_key, test_value, expire=10)
            retrieved = await redis_manager.get(test_key)
            
            if retrieved != test_value:
                raise ValueError("Redis read/write test failed")
            
            await redis_manager.delete(test_key)
            
            self.results.append(StartupCheckResult(
                name="redis_connection",
                success=True,
                message="Redis connected and operational",
                critical=(os.getenv("ENVIRONMENT", "development").lower() == "production")
            ))
        except Exception as e:
            critical = settings.environment == "production"
            self.results.append(StartupCheckResult(
                name="redis_connection",
                success=False,
                message=f"Redis connection failed: {e}",
                critical=critical
            ))
            if not critical:
                logger.warning("Redis not available - caching disabled")

    async def check_clickhouse(self):
        """Check ClickHouse connection"""
        try:
            from app.db.clickhouse import get_clickhouse_client
            async with get_clickhouse_client() as client:
                # Test connectivity
                client.ping()
                
                # Verify tables exist
                result = await client.execute_query(
                    "SELECT name FROM system.tables WHERE database = currentDatabase()"
                )
                tables = [row.get('name', row) if isinstance(row, dict) else row[0] for row in result]
                
                required_tables = ['workload_events']
                missing_tables = [t for t in required_tables if t not in tables]
                
                if missing_tables:
                    raise ValueError(f"Missing ClickHouse tables: {missing_tables}")
                
                self.results.append(StartupCheckResult(
                    name="clickhouse_connection",
                    success=True,
                    message=f"ClickHouse connected with {len(tables)} tables",
                    critical=False
                ))
        except Exception as e:
            critical = settings.environment == "production"
            self.results.append(StartupCheckResult(
                name="clickhouse_connection",
                success=False,
                message=f"ClickHouse check failed: {e}",
                critical=critical
            ))
            if not critical:
                logger.warning("ClickHouse not available - analytics features limited")

    async def check_llm_providers(self):
        """Check LLM provider configuration and connectivity"""
        try:
            llm_manager = self.app.state.llm_manager
            available_providers = []
            failed_providers = []
            
            for llm_name in settings.llm_configs:
                try:
                    llm = llm_manager.get_llm(llm_name)
                    
                    # Check if LLM was successfully initialized
                    if llm is not None:
                        available_providers.append(llm_name)
                    else:
                        # LLM was skipped (no API key for optional provider)
                        logger.info(f"LLM '{llm_name}' not available (optional provider without key)")
                        
                except Exception as e:
                    # Only fail for Google/Gemini providers
                    config = settings.llm_configs.get(llm_name)
                    if config and config.provider == "google":
                        failed_providers.append(f"{llm_name}: {e}")
                    else:
                        logger.info(f"Optional LLM '{llm_name}' not available: {e}")
            
            if not available_providers:
                self.results.append(StartupCheckResult(
                    name="llm_providers",
                    success=False,
                    message="No LLM providers available",
                    critical=True
                ))
            elif failed_providers:
                self.results.append(StartupCheckResult(
                    name="llm_providers",
                    success=True,
                    message=f"LLM providers: {len(available_providers)} available, {len(failed_providers)} failed",
                    critical=False
                ))
            else:
                self.results.append(StartupCheckResult(
                    name="llm_providers",
                    success=True,
                    message=f"All {len(available_providers)} LLM providers configured",
                    critical=False
                ))
        except Exception as e:
            self.results.append(StartupCheckResult(
                name="llm_providers",
                success=False,
                message=f"LLM check failed: {e}",
                critical=(os.getenv("ENVIRONMENT", "development").lower() == "production")
            ))
    
    async def check_memory_and_resources(self):
        """Check system resources"""
        try:
            # Memory check
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            available_gb = memory.available / (1024**3)
            
            # Disk check
            disk = psutil.disk_usage('/')
            disk_free_gb = disk.free / (1024**3)
            
            # CPU check
            cpu_count = psutil.cpu_count()
            
            warnings = []
            if available_gb < 1:
                warnings.append(f"Low memory: {available_gb:.1f}GB available")
            if disk_free_gb < 5:
                warnings.append(f"Low disk space: {disk_free_gb:.1f}GB free")
            if cpu_count < 2:
                warnings.append(f"Low CPU count: {cpu_count} cores")
            
            if warnings:
                self.results.append(StartupCheckResult(
                    name="system_resources",
                    success=True,
                    message=f"Resource warnings: {'; '.join(warnings)}",
                    critical=False
                ))
            else:
                self.results.append(StartupCheckResult(
                    name="system_resources",
                    success=True,
                    message=f"Resources OK: {available_gb:.1f}GB RAM, {disk_free_gb:.1f}GB disk, {cpu_count} CPUs",
                    critical=False
                ))
        except Exception as e:
            self.results.append(StartupCheckResult(
                name="system_resources",
                success=True,  # Don't fail on resource check errors
                message=f"Could not check resources: {e}",
                critical=False
            ))
    
    async def check_network_connectivity(self):
        """Check network connectivity to critical services"""
        import socket
        
        endpoints = [
            ("postgresql", settings.database_url.split('@')[1].split('/')[0] if '@' in settings.database_url else "localhost:5432"),
            ("redis", f"{settings.redis.host}:{settings.redis.port}" if settings.redis else "localhost:6379"),
        ]
        
        failed = []
        for service, endpoint in endpoints:
            try:
                if ':' in endpoint:
                    host, port = endpoint.split(':')
                    port = int(port)
                else:
                    host = endpoint
                    port = 80
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result != 0:
                    failed.append(f"{service} ({endpoint})")
            except Exception as e:
                failed.append(f"{service} ({endpoint}): {e}")
        
        if failed:
            self.results.append(StartupCheckResult(
                name="network_connectivity",
                success=False,
                message=f"Cannot reach: {', '.join(failed)}",
                critical=False
            ))
        else:
            self.results.append(StartupCheckResult(
                name="network_connectivity",
                success=True,
                message="All network endpoints reachable",
                critical=False
            ))

    async def check_or_create_assistant(self):
        """Check if Netra assistant exists, create if not"""
        try:
            async with self.app.state.db_session_factory() as db:
                # Check if assistant already exists
                result = await db.execute(
                    select(Assistant).where(Assistant.id == "netra-assistant")
                )
                assistant = result.scalar_one_or_none()
                
                if not assistant:
                    # Create the assistant
                    assistant = Assistant(
                        id="netra-assistant",
                        object="assistant",
                        created_at=int(time.time()),
                        name="Netra AI Optimization Assistant",
                        description="The world's best AI workload optimization assistant",
                        model="gpt-4",
                        instructions="You are Netra AI Workload Optimization Assistant. You help users optimize their AI workloads for cost, performance, and quality.",
                        tools=[
                            {"type": "data_analysis"},
                            {"type": "optimization"},
                            {"type": "reporting"}
                        ],
                        file_ids=[],
                        metadata_={
                            "version": "1.0",
                            "capabilities": [
                                "workload_analysis",
                                "cost_optimization",
                                "performance_optimization",
                                "quality_optimization",
                                "model_selection",
                                "supply_catalog_management"
                            ]
                        }
                    )
                    db.add(assistant)
                    await db.commit()
                    
                    self.results.append(StartupCheckResult(
                        name="netra_assistant",
                        success=True,
                        message="Netra assistant created successfully",
                        critical=False
                    ))
                else:
                    self.results.append(StartupCheckResult(
                        name="netra_assistant",
                        success=True,
                        message="Netra assistant already exists",
                        critical=False
                    ))
        except Exception as e:
            self.results.append(StartupCheckResult(
                name="netra_assistant",
                success=False,
                message=f"Failed to check/create assistant: {e}",
                critical=False
            ))

async def run_startup_checks(app):
    """Run all startup checks with improved error handling and reporting"""
    checker = StartupChecker(app)
    results = await checker.run_all_checks()
    
    # Log results
    logger.info(f"Startup checks completed in {results['duration_ms']:.0f}ms")
    logger.info(f"Results: {results['passed']}/{results['total_checks']} passed")
    
    if results['failed_critical'] > 0:
        logger.error("Critical startup checks failed:")
        for failure in results['failures']:
            if failure.critical:
                logger.error(f"  - {failure.name}: {failure.message}")
        raise RuntimeError(f"Startup failed: {results['failed_critical']} critical checks failed")
    
    if results['failed_non_critical'] > 0:
        logger.warning("Non-critical startup checks failed:")
        for failure in results['failures']:
            if not failure.critical:
                logger.warning(f"  - {failure.name}: {failure.message}")
    
    return results
