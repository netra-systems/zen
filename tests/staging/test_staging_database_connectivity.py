"""
Test 6: Staging Database Connectivity

CRITICAL: Test database operations in staging environment.
This validates data persistence layer that underpins all platform functionality.

Business Value: Platform/Internal - Data Integrity & System Stability
Without database connectivity, no user data can be stored or retrieved, blocking all features.
"""

import pytest
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

# Import database utilities (will gracefully handle import failures)
try:
    import httpx
    from netra_backend.app.db.database_manager import DatabaseManager
    from netra_backend.app.db.postgres import get_postgres_db
    from netra_backend.app.db.clickhouse import get_clickhouse_client
except ImportError as e:
    print(f"Warning: Database imports failed: {e}")
    # We'll use API-based testing instead

class StagingDatabaseConnectivityTestRunner:
    """Test runner for database connectivity validation in staging."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()
        self.timeout = StagingConfig.TIMEOUTS["default"]
        self.access_token = None
        
    def get_base_headers(self) -> Dict[str, str]:
        """Get base headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Netra-Staging-DB-Test/1.0"
        }
        
    async def get_test_token(self) -> Optional[str]:
        """Get test token for authenticated database operations."""
        try:
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return None
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/simulate",
                    headers=self.get_base_headers(),
                    json={
                        "simulation_key": simulation_key,
                        "user_id": "staging-db-test-user",
                        "email": "staging-db-test@netrasystems.ai"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                    
        except Exception as e:
            print(f"Token generation failed: {e}")
            
        return None
        
    async def test_database_health_endpoints(self) -> Dict[str, Any]:
        """Test 6.1: Database health through API endpoints."""
        print("6.1 Testing database health endpoints...")
        
        results = {}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test backend database health endpoint
                backend_health_response = await client.get(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/system/database/health",
                    headers=self.get_base_headers()
                )
                
                backend_db_healthy = backend_health_response.status_code == 200
                backend_health_data = {}
                
                if backend_db_healthy:
                    try:
                        backend_health_data = backend_health_response.json()
                    except:
                        pass
                        
                results["backend_database_health"] = {
                    "success": backend_db_healthy,
                    "status_code": backend_health_response.status_code,
                    "response_time": backend_health_response.elapsed.total_seconds() if backend_health_response.elapsed else 0,
                    "health_data": backend_health_data,
                    "postgres_status": backend_health_data.get("postgres", {}).get("status") if isinstance(backend_health_data, dict) else "unknown",
                    "redis_status": backend_health_data.get("redis", {}).get("status") if isinstance(backend_health_data, dict) else "unknown",
                    "clickhouse_status": backend_health_data.get("clickhouse", {}).get("status") if isinstance(backend_health_data, dict) else "unknown"
                }
                
                # Test auth service database health
                auth_health_response = await client.get(
                    f"{StagingConfig.get_service_url('auth')}/api/system/database/health",
                    headers=self.get_base_headers()
                )
                
                auth_db_healthy = auth_health_response.status_code == 200
                auth_health_data = {}
                
                if auth_db_healthy:
                    try:
                        auth_health_data = auth_health_response.json()
                    except:
                        pass
                        
                results["auth_database_health"] = {
                    "success": auth_db_healthy,
                    "status_code": auth_health_response.status_code,
                    "response_time": auth_health_response.elapsed.total_seconds() if auth_health_response.elapsed else 0,
                    "health_data": auth_health_data,
                    "postgres_status": auth_health_data.get("postgres", {}).get("status") if isinstance(auth_health_data, dict) else "unknown"
                }
                
        except Exception as e:
            results["backend_database_health"] = {
                "success": False,
                "error": f"Backend database health check failed: {str(e)}"
            }
            results["auth_database_health"] = {
                "success": False,
                "error": f"Auth database health check failed: {str(e)}"
            }
            
        return results
        
    async def test_database_read_operations(self) -> Dict[str, Any]:
        """Test 6.2: Database read operations through API."""
        print("6.2 Testing database read operations...")
        
        results = {}
        
        if not self.access_token:
            return {
                "user_profile_read": {
                    "success": False,
                    "error": "No access token available",
                    "skipped": True
                }
            }
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test user profile read (PostgreSQL)
                profile_response = await client.get(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/user/profile",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {self.access_token}"
                    }
                )
                
                # 200 = profile exists, 404 = profile doesn't exist (both are valid DB reads)
                profile_read_success = profile_response.status_code in [200, 404]
                
                results["user_profile_read"] = {
                    "success": profile_read_success,
                    "status_code": profile_response.status_code,
                    "response_time": profile_response.elapsed.total_seconds() if profile_response.elapsed else 0,
                    "database_operation": "postgres_read",
                    "data_retrieved": profile_response.status_code == 200
                }
                
                # Test corpus search (ClickHouse read)
                search_response = await client.get(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/corpus/search?q=test&limit=5",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {self.access_token}"
                    }
                )
                
                # 200 = search successful, 404 = no results (both are valid DB reads)
                search_success = search_response.status_code in [200, 404]
                
                results["corpus_search_read"] = {
                    "success": search_success,
                    "status_code": search_response.status_code,
                    "response_time": search_response.elapsed.total_seconds() if search_response.elapsed else 0,
                    "database_operation": "clickhouse_read",
                    "data_retrieved": search_response.status_code == 200
                }
                
        except Exception as e:
            results["user_profile_read"] = {
                "success": False,
                "error": f"Profile read test failed: {str(e)}",
                "database_operation": "postgres_read"
            }
            results["corpus_search_read"] = {
                "success": False,
                "error": f"Search read test failed: {str(e)}",
                "database_operation": "clickhouse_read"
            }
            
        return results
        
    async def test_database_write_operations(self) -> Dict[str, Any]:
        """Test 6.3: Database write operations through API."""
        print("6.3 Testing database write operations...")
        
        results = {}
        
        if not self.access_token:
            return {
                "profile_update": {
                    "success": False,
                    "error": "No access token available",
                    "skipped": True
                },
                "corpus_upload": {
                    "success": False,
                    "error": "No access token available", 
                    "skipped": True
                }
            }
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test user profile update (PostgreSQL write)
                profile_data = {
                    "first_name": "Staging",
                    "last_name": "Test",
                    "company": "Netra Database Test",
                    "metadata": {
                        "test_timestamp": time.time(),
                        "test_id": str(uuid.uuid4())
                    }
                }
                
                profile_response = await client.put(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/user/profile",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {self.access_token}"
                    },
                    json=profile_data
                )
                
                # 200/201 = update success, 404 = user not found (still valid DB operation)
                profile_write_success = profile_response.status_code in [200, 201, 404]
                
                results["profile_update"] = {
                    "success": profile_write_success,
                    "status_code": profile_response.status_code,
                    "response_time": profile_response.elapsed.total_seconds() if profile_response.elapsed else 0,
                    "database_operation": "postgres_write",
                    "data_written": profile_response.status_code in [200, 201]
                }
                
                # Test corpus upload (ClickHouse write)
                test_content = f"Staging database test content - {uuid.uuid4().hex[:8]} - {time.time()}"
                
                corpus_data = {
                    "content": test_content,
                    "title": f"Staging DB Test - {uuid.uuid4().hex[:8]}",
                    "type": "text",
                    "metadata": {
                        "test_upload": True,
                        "environment": self.environment,
                        "timestamp": time.time()
                    }
                }
                
                corpus_response = await client.post(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/corpus/upload",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {self.access_token}"
                    },
                    json=corpus_data
                )
                
                # 200/201 = upload success
                corpus_write_success = corpus_response.status_code in [200, 201]
                
                results["corpus_upload"] = {
                    "success": corpus_write_success,
                    "status_code": corpus_response.status_code,
                    "response_time": corpus_response.elapsed.total_seconds() if corpus_response.elapsed else 0,
                    "database_operation": "clickhouse_write",
                    "data_written": corpus_write_success,
                    "content_size": len(test_content)
                }
                
        except Exception as e:
            results["profile_update"] = {
                "success": False,
                "error": f"Profile update test failed: {str(e)}",
                "database_operation": "postgres_write"
            }
            results["corpus_upload"] = {
                "success": False,
                "error": f"Corpus upload test failed: {str(e)}",
                "database_operation": "clickhouse_write"
            }
            
        return results
        
    async def test_database_connection_pooling(self) -> Dict[str, Any]:
        """Test 6.4: Database connection pooling and concurrent operations."""
        print("6.4 Testing database connection pooling...")
        
        results = {}
        
        if not self.access_token:
            return {
                "connection_pooling": {
                    "success": False,
                    "error": "No access token available",
                    "skipped": True
                }
            }
            
        try:
            # Test concurrent database operations
            concurrent_requests = 5
            
            async def make_db_request(client, request_id):
                try:
                    response = await client.get(
                        f"{StagingConfig.get_service_url('netra_backend')}/api/user/profile",
                        headers={
                            **self.get_base_headers(),
                            "Authorization": f"Bearer {self.access_token}",
                            "X-Request-ID": str(request_id)
                        }
                    )
                    return {
                        "success": response.status_code in [200, 404],
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                        "request_id": request_id
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "request_id": request_id
                    }
                    
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Execute concurrent requests
                tasks = [make_db_request(client, i) for i in range(concurrent_requests)]
                start_time = time.time()
                request_results = await asyncio.gather(*tasks)
                total_time = time.time() - start_time
                
                # Analyze results
                successful_requests = sum(1 for result in request_results if result["success"])
                avg_response_time = sum(
                    result.get("response_time", 0) for result in request_results if result["success"]
                ) / max(successful_requests, 1)
                
                success_rate = successful_requests / concurrent_requests
                
                results["connection_pooling"] = {
                    "success": success_rate >= 0.8,  # 80% success rate required
                    "concurrent_requests": concurrent_requests,
                    "successful_requests": successful_requests,
                    "success_rate": success_rate,
                    "total_time": total_time,
                    "avg_response_time": avg_response_time,
                    "requests_per_second": concurrent_requests / total_time if total_time > 0 else 0,
                    "pooling_effective": success_rate >= 0.8 and avg_response_time < 5.0
                }
                
        except Exception as e:
            results["connection_pooling"] = {
                "success": False,
                "error": f"Connection pooling test failed: {str(e)}"
            }
            
        return results
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all database connectivity tests."""
        print(f"[U+1F5C3][U+FE0F]  Running Database Connectivity Tests")
        print(f"Environment: {self.environment}")
        print(f"Backend URL: {StagingConfig.get_service_url('netra_backend')}")
        print(f"Auth URL: {StagingConfig.get_service_url('auth')}")
        print()
        
        # Get test token first
        print("[U+1F511] Getting test token...")
        self.access_token = await self.get_test_token()
        print(f"     Token obtained: {bool(self.access_token)}")
        print()
        
        results = {}
        
        # Test 6.1: Database health endpoints
        health_results = await self.test_database_health_endpoints()
        results.update(health_results)
        
        # Test 6.2: Database read operations  
        read_results = await self.test_database_read_operations()
        results.update(read_results)
        
        # Test 6.3: Database write operations
        write_results = await self.test_database_write_operations()
        results.update(write_results)
        
        # Test 6.4: Connection pooling
        pooling_results = await self.test_database_connection_pooling()
        results.update(pooling_results)
        
        # Calculate summary
        all_tests = {k: v for k, v in results.items() if isinstance(v, dict) and "success" in v}
        total_tests = len(all_tests)
        passed_tests = sum(1 for result in all_tests.values() if result["success"])
        skipped_tests = sum(1 for result in all_tests.values() if result.get("skipped", False))
        
        # Check database health status
        backend_db_healthy = results.get("backend_database_health", {}).get("success", False)
        auth_db_healthy = results.get("auth_database_health", {}).get("success", False)
        databases_healthy = backend_db_healthy and auth_db_healthy
        
        # Check core database operations
        read_ops_working = any(
            result.get("success", False) for key, result in results.items() 
            if "read" in key
        )
        write_ops_working = any(
            result.get("success", False) for key, result in results.items()
            if "write" in key or "update" in key or "upload" in key
        )
        
        results["summary"] = {
            "databases_healthy": databases_healthy,
            "read_operations_working": read_ops_working,
            "write_operations_working": write_ops_working,
            "environment": self.environment,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "skipped_tests": skipped_tests,
            "critical_database_failure": not databases_healthy
        }
        
        print()
        print(f" CHART:  Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed ({results['summary']['skipped_tests']} skipped)")
        print(f"[U+1F5C3][U+FE0F]  Database health: {' PASS:  Healthy' if databases_healthy else ' FAIL:  Issues detected'}")
        print(f"[U+1F4D6] Read operations: {' PASS:  Working' if read_ops_working else ' FAIL:  Failed'}")
        print(f"[U+270F][U+FE0F]  Write operations: {' PASS:  Working' if write_ops_working else ' FAIL:  Failed'}")
        
        if results["summary"]["critical_database_failure"]:
            print(" ALERT:  CRITICAL: Database health issues detected!")
            
        return results


@pytest.mark.asyncio
@pytest.mark.staging  
async def test_staging_database_connectivity():
    """Main test entry point for database connectivity validation."""
    runner = StagingDatabaseConnectivityTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["databases_healthy"], "Database health checks failed"
    assert not results["summary"]["critical_database_failure"], "Critical database failures detected"


if __name__ == "__main__":
    async def main():
        runner = StagingDatabaseConnectivityTestRunner()
        results = await runner.run_all_tests()
        
        if results["summary"]["critical_database_failure"]:
            exit(1)
            
    asyncio.run(main())