"""
Database Connection Validation Module
Tests REAL database connections for PostgreSQL and ClickHouse.
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg
import clickhouse_connect
from dotenv import load_dotenv


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
        """Parse PostgreSQL configuration from DATABASE_URL."""
        database_url = os.getenv("DATABASE_URL", "")
        
        if not database_url:
            return {}
        
        # Parse postgresql+asyncpg://user:pass@host:port/db
        try:
            url_parts = database_url.replace("postgresql+asyncpg://", "").split("/")
            host_info = url_parts[0]
            database = url_parts[1] if len(url_parts) > 1 else "netra_dev"
            
            if "@" in host_info:
                auth_part, host_part = host_info.split("@")
                host, port = host_part.split(":") if ":" in host_part else (host_part, "5432")
                
                if ":" in auth_part:
                    username, password = auth_part.split(":", 1)
                else:
                    username, password = auth_part, ""
            else:
                host, port = host_info.split(":") if ":" in host_info else (host_info, "5432")
                username, password = "postgres", ""
            
            return {
                "host": host,
                "port": int(port),
                "database": database,
                "username": username,
                "password": password
            }
        except Exception:
            return {}
    
    def _parse_clickhouse_config(self) -> Dict[str, Any]:
        """Parse ClickHouse configuration from environment."""
        host = os.getenv("CLICKHOUSE_HOST", "localhost")
        
        return {
            "host": host,
            "port": int(os.getenv("CLICKHOUSE_PORT", "8443")),
            "user": os.getenv("CLICKHOUSE_USER", "default"),
            "password": os.getenv("CLICKHOUSE_PASSWORD", ""),
            "database": os.getenv("CLICKHOUSE_DB", "default"),
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
        
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            db_result["status"] = "error"
            db_result["error"] = "DATABASE_URL not configured"
            results["databases"]["postgresql"] = db_result
            return
        
        await self._attempt_postgres_connection(db_result, database_url)
        results["databases"]["postgresql"] = db_result
    
    async def _attempt_postgres_connection(self, db_result: Dict[str, Any], database_url: str) -> None:
        """Attempt PostgreSQL connection with timing."""
        start_time = datetime.now()
        
        try:
            # Convert asyncpg URL to standard PostgreSQL URL
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
        """Build PostgreSQL connection string."""
        config = self.postgres_config
        auth_part = f"{config['username']}:{config['password']}" if config['password'] else config['username']
        
        return f"postgresql://{auth_part}@{config['host']}:{config['port']}/{config['database']}"
    
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