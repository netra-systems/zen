from shared.isolated_environment import get_env
"""
Database Connection Validation Module
Tests REAL database connections for PostgreSQL and ClickHouse.

**UPDATED**: Now uses DatabaseURLBuilder for centralized URL construction.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg
import clickhouse_connect
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database_url_builder import DatabaseURLBuilder


class DatabaseValidator:
    """Database connectivity validation logic."""
    
    def __init__(self):
        """Initialize database validator."""
        # Load environment variables
        load_dotenv()
        
        self.postgres_config = self._parse_postgres_config()
        self.clickhouse_config = self._parse_clickhouse_config()
        
    async def validate_all_databases(self) -> Dict[str, Any]:
        """Validate all database connections."""
        results = {
            "status": "success",
            "databases": {},
            "summary": "",
            "recommendations": []
        }
        
        await self._test_postgres_connection(results)
        await self._test_clickhouse_connection(results)
        self._update_database_status(results)
        
        return results
    
    def _parse_postgres_config(self) -> Dict[str, str]:
        """Parse PostgreSQL configuration using DatabaseURLBuilder."""
        # Build environment variables dict
        env_vars = {
            "ENVIRONMENT": get_env().get("ENVIRONMENT", "development"),
            "DATABASE_URL": get_env().get("DATABASE_URL", ""),
            "POSTGRES_HOST": get_env().get("POSTGRES_HOST"),
            "POSTGRES_PORT": get_env().get("POSTGRES_PORT"),
            "POSTGRES_DB": get_env().get("POSTGRES_DB"),
            "POSTGRES_USER": get_env().get("POSTGRES_USER"),
            "POSTGRES_PASSWORD": get_env().get("POSTGRES_PASSWORD"),
        }
        
        # Create builder
        builder = DatabaseURLBuilder(env_vars)
        
        # Get configuration details
        config_info = builder.debug_info()
        
        # Return parsed configuration if available
        if config_info.get('has_tcp_config') or config_info.get('has_cloud_sql'):
            # Extract from environment variables if set
            return {
                "host": env_vars.get("POSTGRES_HOST", "localhost"),
                "port": int(env_vars.get("POSTGRES_PORT", "5432")),
                "database": env_vars.get("POSTGRES_DB", "netra_dev"),
                "username": env_vars.get("POSTGRES_USER", "postgres"),
                "password": env_vars.get("POSTGRES_PASSWORD", "")
            }
        elif env_vars.get("DATABASE_URL"):
            # Parse from #removed-legacyusing builder's parsing logic
            try:
                from urllib.parse import urlparse
                parsed = urlparse(env_vars["DATABASE_URL"])
                return {
                    "host": parsed.hostname or "localhost",
                    "port": parsed.port or 5432,
                    "database": parsed.path.lstrip("/") if parsed.path else "netra_dev",
                    "username": parsed.username or "postgres",
                    "password": parsed.password or ""
                }
            except:
                return {}
        else:
            return {}
    
    def _parse_clickhouse_config(self) -> Dict[str, Any]:
        """Parse ClickHouse configuration from environment."""
        host = get_env().get("CLICKHOUSE_HOST", "localhost")
        
        return {
            "host": host,
            "port": int(get_env().get("CLICKHOUSE_PORT", "8123")),
            "user": get_env().get("CLICKHOUSE_USER", "default"),
            "password": get_env().get("CLICKHOUSE_PASSWORD", ""),
            "database": get_env().get("CLICKHOUSE_DB", "default"),
            "secure": "localhost" not in host  # Use HTTPS for cloud instances
        }
    
    async def _test_postgres_connection(self, results: Dict[str, Any]) -> None:
        """Test PostgreSQL database connection."""
        db_result = {
            "type": "PostgreSQL",
            "status": "unknown",
            "connection_time": None,
            "version": None,
            "error": None
        }
        
        database_url = get_env().get("DATABASE_URL", "")
        if not database_url:
            db_result["status"] = "error"
            db_result["error"] = "#removed-legacynot configured"
            results["databases"]["postgresql"] = db_result
            return
        
        await self._attempt_postgres_connection(db_result, database_url)
        results["databases"]["postgresql"] = db_result
    
    async def _attempt_postgres_connection(self, db_result: Dict[str, Any], database_url: str) -> None:
        """Attempt PostgreSQL connection with timing."""
        start_time = datetime.now()
        
        try:
            # Use DatabaseURLBuilder to ensure correct URL format
            env_vars = {
                "ENVIRONMENT": get_env().get("ENVIRONMENT", "development"),
                "DATABASE_URL": database_url,
            }
            builder = DatabaseURLBuilder(env_vars)
            
            # Get the sync URL for asyncpg (it uses postgresql:// not postgresql+asyncpg://)
            connection_string = builder.get_url_for_environment(sync=True)
            if not connection_string:
                connection_string = database_url.replace("postgresql+asyncpg://", "postgresql://")
            
            conn = await asyncpg.connect(connection_string, timeout=10)
            
            # Test basic query
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            
            db_result["status"] = "success"
            db_result["version"] = version.split(" ")[1] if version else "unknown"
            db_result["connection_time"] = (datetime.now() - start_time).total_seconds()
            
        except Exception as e:
            db_result["status"] = "error"
            db_result["error"] = str(e)
            db_result["connection_time"] = (datetime.now() - start_time).total_seconds()
    
    def _build_postgres_connection_string(self) -> str:
        """Build PostgreSQL connection string using DatabaseURLBuilder."""
        if not self.postgres_config:
            return ""
        
        # Build environment variables dict
        env_vars = {
            "ENVIRONMENT": get_env().get("ENVIRONMENT", "development"),
            "POSTGRES_HOST": self.postgres_config.get('host', 'localhost'),
            "POSTGRES_PORT": str(self.postgres_config.get('port', 5432)),
            "POSTGRES_DB": self.postgres_config.get('database', 'netra_dev'),
            "POSTGRES_USER": self.postgres_config.get('username', 'postgres'),
            "POSTGRES_PASSWORD": self.postgres_config.get('password', ''),
        }
        
        # Create builder
        builder = DatabaseURLBuilder(env_vars)
        
        # Get sync URL
        url = builder.get_url_for_environment(sync=True)
        return url or ""
    
    async def _test_clickhouse_connection(self, results: Dict[str, Any]) -> None:
        """Test ClickHouse database connection."""
        db_result = {
            "type": "ClickHouse",
            "status": "unknown",
            "connection_time": None,
            "version": None,
            "error": None
        }
        
        await self._attempt_clickhouse_connection(db_result)
        results["databases"]["clickhouse"] = db_result
    
    async def _attempt_clickhouse_connection(self, db_result: Dict[str, Any]) -> None:
        """Attempt ClickHouse connection with timing."""
        start_time = datetime.now()
        
        try:
            # Use asyncio.to_thread for blocking ClickHouse client
            await asyncio.to_thread(self._test_clickhouse_sync, db_result, start_time)
            
        except Exception as e:
            db_result["status"] = "error"
            db_result["error"] = str(e)
            db_result["connection_time"] = (datetime.now() - start_time).total_seconds()
    
    def _test_clickhouse_sync(self, db_result: Dict[str, Any], start_time: datetime) -> None:
        """Synchronous ClickHouse connection test."""
        config = self.clickhouse_config
        
        try:
            client = clickhouse_connect.get_client(
                host=config["host"],
                port=config["port"],
                username=config["user"],
                password=config["password"],
                database=config["database"],
                secure=config["secure"],
                connect_timeout=10
            )
            
            # Test basic query
            result = client.query("SELECT version()")
            version = result.result_rows[0][0] if result.result_rows else "unknown"
            
            client.close()
            
            db_result["status"] = "success"
            db_result["version"] = version
            db_result["connection_time"] = (datetime.now() - start_time).total_seconds()
            
        except Exception as e:
            db_result["status"] = "error"
            db_result["error"] = str(e)
            db_result["connection_time"] = (datetime.now() - start_time).total_seconds()
    
    def _update_database_status(self, results: Dict[str, Any]) -> None:
        """Update overall database validation status."""
        database_results = results["databases"]
        success_count = sum(1 for db in database_results.values() if db["status"] == "success")
        total_count = len(database_results)
        
        if success_count == total_count:
            results["status"] = "success"
            results["summary"] = f"All {total_count} databases connected successfully"
        elif success_count == 0:
            results["status"] = "error"
            results["summary"] = "No database connections successful"
            self._add_database_recommendations(results)
        else:
            results["status"] = "warning"
            results["summary"] = f"{success_count}/{total_count} databases connected"
            self._add_database_recommendations(results)
    
    def _add_database_recommendations(self, results: Dict[str, Any]) -> None:
        """Add recommendations for failed database connections."""
        for db_name, db_result in results["databases"].items():
            if db_result["status"] == "error":
                if "connection refused" in db_result.get("error", "").lower():
                    results["recommendations"].append(f"Start {db_result['type']} service")
                elif "authentication" in db_result.get("error", "").lower():
                    results["recommendations"].append(f"Check {db_result['type']} credentials")
                else:
                    results["recommendations"].append(f"Verify {db_result['type']} configuration")
