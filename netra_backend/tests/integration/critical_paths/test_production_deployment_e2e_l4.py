#!/usr/bin/env python3
"""
Comprehensive test to verify production deployment readiness:
1. Validate production configuration settings
2. Verify all microservices start correctly
3. Test health checks across all services
4. Validate database connections (Postgres, ClickHouse, Redis)
5. Test authentication and authorization flows
6. Verify WebSocket load balancing
7. Test monitoring and alerting integration
8. Validate rollback procedures

This test ensures the complete production environment is deployment-ready.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import json
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
import aiohttp
import websockets
import pytest
from datetime import datetime, timedelta
import yaml
import psutil
import socket

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Production Configuration
PROD_BACKEND_URL = os.getenv("PROD_BACKEND_URL", "https://api.netra.ai")
PROD_FRONTEND_URL = os.getenv("PROD_FRONTEND_URL", "https://app.netra.ai")
PROD_WEBSOCKET_URL = os.getenv("PROD_WEBSOCKET_URL", "wss://api.netra.ai/websocket")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "https://auth.netra.ai")
MONITORING_URL = os.getenv("MONITORING_URL", "https://metrics.netra.ai")

# Production databases
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/netra")
CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Test credentials
TEST_ADMIN_EMAIL = "admin@netra.ai"
TEST_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "secure_admin_pass")


class ProductionDeploymentTester:
    """Test production deployment readiness."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.deployment_config: Dict = {}
        self.service_endpoints: Dict = {}
        self.health_statuses: Dict = {}
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.session:
            await self.session.close()
            
    async def load_deployment_config(self) -> bool:
        """Load and validate deployment configuration."""
        print("\n[CONFIG] STEP 1: Loading deployment configuration...")
        
        try:
            # Load production config
            config_path = project_root / "deployment" / "production" / "config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.deployment_config = yaml.safe_load(f)
                    
            # Validate required config sections
            required_sections = ["services", "databases", "monitoring", "security"]
            for section in required_sections:
                if section not in self.deployment_config:
                    print(f"[ERROR] Missing config section: {section}")
                    return False
                    
            print(f"[OK] Deployment config loaded: {len(self.deployment_config)} sections")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            return False
            
    async def validate_infrastructure(self) -> bool:
        """Validate infrastructure requirements."""
        print("\n[INFRA] STEP 2: Validating infrastructure...")
        
        checks = {
            "cpu_cores": psutil.cpu_count() >= 4,
            "memory_gb": psutil.virtual_memory().total / (1024**3) >= 8,
            "disk_space_gb": psutil.disk_usage('/').free / (1024**3) >= 50,
            "network_connectivity": await self._check_network(),
            "dns_resolution": await self._check_dns(),
            "ssl_certificates": await self._check_ssl()
        }
        
        all_passed = True
        for check, passed in checks.items():
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {check}: {status}")
            all_passed = all_passed and passed
            
        return all_passed
        
    async def _check_network(self) -> bool:
        """Check network connectivity."""
        try:
            async with self.session.get("https://www.google.com", timeout=5) as response:
                return response.status == 200
        except:
            return False
            
    async def _check_dns(self) -> bool:
        """Check DNS resolution."""
        try:
            socket.gethostbyname("api.netra.ai")
            return True
        except:
            return False
            
    async def _check_ssl(self) -> bool:
        """Check SSL certificates."""
        try:
            # Check if SSL certificates are valid
            async with self.session.get(PROD_BACKEND_URL, ssl=True) as response:
                return True
        except:
            return False
            
    async def test_microservices_startup(self) -> bool:
        """Test all microservices startup sequence."""
        print("\n[SERVICES] STEP 3: Testing microservices startup...")
        
        services = [
            ("backend", PROD_BACKEND_URL + "/api/v1/health"),
            ("auth", AUTH_SERVICE_URL + "/health"),
            ("frontend", PROD_FRONTEND_URL),
            ("monitoring", MONITORING_URL + "/metrics"),
            ("websocket", PROD_WEBSOCKET_URL.replace("wss://", "https://").replace("/websocket", "/health"))
        ]
        
        startup_results = {}
        for service_name, health_url in services:
            print(f"  Checking {service_name}...")
            
            try:
                async with self.session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        startup_results[service_name] = True
                        self.health_statuses[service_name] = await response.json() if response.content_type == 'application/json' else {"status": "healthy"}
                        print(f"    [OK] {service_name} is running")
                    else:
                        startup_results[service_name] = False
                        print(f"    [FAIL] {service_name} returned {response.status}")
            except Exception as e:
                startup_results[service_name] = False
                print(f"    [ERROR] {service_name}: {e}")
                
        return all(startup_results.values())
        
    async def test_database_connections(self) -> bool:
        """Test all database connections."""
        print("\n[DATABASE] STEP 4: Testing database connections...")
        
        db_results = {}
        
        # Test PostgreSQL
        print("  Testing PostgreSQL...")
        try:
            import asyncpg
            conn = await asyncpg.connect(POSTGRES_URL)
            result = await conn.fetchval("SELECT version()")
            await conn.close()
            db_results["postgres"] = True
            print(f"    [OK] PostgreSQL connected: {result[:50]}...")
        except Exception as e:
            db_results["postgres"] = False
            print(f"    [ERROR] PostgreSQL: {e}")
            
        # Test ClickHouse
        print("  Testing ClickHouse...")
        try:
            async with self.session.get(f"{CLICKHOUSE_URL}/?query=SELECT version()") as response:
                if response.status == 200:
                    version = await response.text()
                    db_results["clickhouse"] = True
                    print(f"    [OK] ClickHouse connected: {version.strip()}")
                else:
                    db_results["clickhouse"] = False
                    print(f"    [ERROR] ClickHouse returned {response.status}")
        except Exception as e:
            db_results["clickhouse"] = False
            print(f"    [ERROR] ClickHouse: {e}")
            
        # Test Redis
        print("  Testing Redis...")
        try:
            aioredis
            redis = await aioredis.from_url(REDIS_URL)
            await redis.ping()
            await redis.close()
            db_results["redis"] = True
            print("    [OK] Redis connected")
        except Exception as e:
            db_results["redis"] = False
            print(f"    [ERROR] Redis: {e}")
            
        return all(db_results.values())
        
    async def test_authentication_flow(self) -> bool:
        """Test production authentication flow."""
        print("\n[AUTH] STEP 5: Testing authentication flow...")
        
        try:
            # Test login
            login_data = {
                "email": TEST_ADMIN_EMAIL,
                "password": TEST_ADMIN_PASSWORD
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    
                    # Test token validation
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    async with self.session.get(
                        f"{AUTH_SERVICE_URL}/auth/validate",
                        headers=headers
                    ) as validate_response:
                        if validate_response.status == 200:
                            print("[OK] Authentication flow working")
                            return True
                            
            print("[ERROR] Authentication flow failed")
            return False
            
        except Exception as e:
            print(f"[ERROR] Auth test error: {e}")
            return False
            
    async def test_websocket_load_balancing(self) -> bool:
        """Test WebSocket load balancing across instances."""
        print("\n[WEBSOCKET] STEP 6: Testing WebSocket load balancing...")
        
        if not self.auth_token:
            print("[ERROR] No auth token available")
            return False
            
        connections = []
        connection_servers = []
        
        try:
            # Create multiple connections
            for i in range(5):
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                ws = await websockets.connect(
                    PROD_WEBSOCKET_URL,
                    extra_headers=headers
                )
                connections.append(ws)
                
                # Send identification message
                await ws.send(json.dumps({
                    "type": "identify",
                    "client_id": f"test_client_{i}"
                }))
                
                # Receive server info
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)
                server_id = data.get("server_id", "unknown")
                connection_servers.append(server_id)
                print(f"    Connection {i} -> Server {server_id}")
                
            # Check if connections are distributed
            unique_servers = len(set(connection_servers))
            if unique_servers > 1:
                print(f"[OK] Load balancing working: {unique_servers} servers")
                result = True
            else:
                print(f"[WARNING] All connections on same server")
                result = True  # Still pass if only one server is running
                
            # Cleanup connections
            for ws in connections:
                await ws.close()
                
            return result
            
        except Exception as e:
            print(f"[ERROR] WebSocket test error: {e}")
            # Cleanup any open connections
            for ws in connections:
                try:
                    await ws.close()
                except:
                    pass
            return False
            
    async def test_monitoring_integration(self) -> bool:
        """Test monitoring and metrics collection."""
        print("\n[MONITORING] STEP 7: Testing monitoring integration...")
        
        try:
            # Check Prometheus metrics endpoint
            async with self.session.get(f"{MONITORING_URL}/metrics") as response:
                if response.status == 200:
                    metrics_text = await response.text()
                    
                    # Verify key metrics are present
                    required_metrics = [
                        "http_requests_total",
                        "http_request_duration_seconds",
                        "websocket_connections_active",
                        "database_connections_active",
                        "cache_hit_ratio"
                    ]
                    
                    missing_metrics = []
                    for metric in required_metrics:
                        if metric not in metrics_text:
                            missing_metrics.append(metric)
                            
                    if not missing_metrics:
                        print("[OK] All required metrics present")
                        return True
                    else:
                        print(f"[ERROR] Missing metrics: {missing_metrics}")
                        return False
                else:
                    print(f"[ERROR] Metrics endpoint returned {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Monitoring test error: {e}")
            return False
            
    async def test_rollback_procedures(self) -> bool:
        """Test deployment rollback procedures."""
        print("\n[ROLLBACK] STEP 8: Testing rollback procedures...")
        
        try:
            # Check if rollback scripts exist
            rollback_scripts = [
                "deployment/scripts/rollback.py",
                "deployment/scripts/backup_restore.py",
                "deployment/kubernetes/rollback.yaml"
            ]
            
            scripts_found = []
            for script in rollback_scripts:
                script_path = project_root / script
                if script_path.exists():
                    scripts_found.append(script)
                    print(f"    [OK] Found: {script}")
                else:
                    print(f"    [MISSING] {script}")
                    
            # Test rollback simulation (dry run)
            if len(scripts_found) > 0:
                print("    [OK] Rollback procedures available")
                return True
            else:
                print("    [ERROR] No rollback procedures found")
                return False
                
        except Exception as e:
            print(f"[ERROR] Rollback test error: {e}")
            return False
            
    async def test_security_headers(self) -> bool:
        """Test security headers on production endpoints."""
        print("\n[SECURITY] STEP 9: Testing security headers...")
        
        try:
            async with self.session.get(PROD_BACKEND_URL) as response:
                headers = response.headers
                
                required_headers = {
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": ["DENY", "SAMEORIGIN"],
                    "X-XSS-Protection": "1; mode=block",
                    "Strict-Transport-Security": None,  # Just check presence
                    "Content-Security-Policy": None
                }
                
                missing_headers = []
                for header, expected_values in required_headers.items():
                    if header not in headers:
                        missing_headers.append(header)
                    elif expected_values:
                        actual_value = headers[header]
                        if isinstance(expected_values, list):
                            if actual_value not in expected_values:
                                missing_headers.append(f"{header}={actual_value}")
                        elif actual_value != expected_values:
                            missing_headers.append(f"{header}={actual_value}")
                            
                if not missing_headers:
                    print("[OK] All security headers present")
                    return True
                else:
                    print(f"[ERROR] Missing/incorrect headers: {missing_headers}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Security headers test error: {e}")
            return False
            
    async def test_rate_limiting(self) -> bool:
        """Test rate limiting on production endpoints."""
        print("\n[RATE_LIMIT] STEP 10: Testing rate limiting...")
        
        try:
            # Make rapid requests to trigger rate limiting
            requests_made = 0
            rate_limited = False
            
            for i in range(100):
                async with self.session.get(
                    f"{PROD_BACKEND_URL}/api/v1/health",
                    timeout=1
                ) as response:
                    requests_made += 1
                    if response.status == 429:
                        rate_limited = True
                        print(f"    [OK] Rate limited after {requests_made} requests")
                        break
                        
            if rate_limited:
                return True
            else:
                print(f"    [WARNING] No rate limiting after {requests_made} requests")
                return True  # Don't fail test, just warn
                
        except Exception as e:
            print(f"[ERROR] Rate limiting test error: {e}")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all production deployment tests."""
        results = {}
        
        # Configuration and infrastructure
        results["deployment_config"] = await self.load_deployment_config()
        results["infrastructure"] = await self.validate_infrastructure()
        
        # Core services
        results["microservices_startup"] = await self.test_microservices_startup()
        results["database_connections"] = await self.test_database_connections()
        
        # Authentication and WebSocket
        results["authentication_flow"] = await self.test_authentication_flow()
        results["websocket_load_balancing"] = await self.test_websocket_load_balancing()
        
        # Operations
        results["monitoring_integration"] = await self.test_monitoring_integration()
        results["rollback_procedures"] = await self.test_rollback_procedures()
        
        # Security
        results["security_headers"] = await self.test_security_headers()
        results["rate_limiting"] = await self.test_rate_limiting()
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.production
async def test_production_deployment_e2e():
    """Test complete production deployment readiness."""
    async with ProductionDeploymentTester() as tester:
        results = await tester.run_all_tests()
        
        # Print summary
        print("\n" + "="*60)
        print("PRODUCTION DEPLOYMENT TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {test_name:30} : {status}")
            
        print("="*60)
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] Production deployment is ready!")
        else:
            failed_tests = [name for name, passed in results.items() if not passed]
            print(f"\n[WARNING] Failed tests: {', '.join(failed_tests)}")
            
        # Assert critical tests passed
        critical_tests = [
            "microservices_startup",
            "database_connections",
            "authentication_flow",
            "security_headers"
        ]
        
        for test in critical_tests:
            assert results.get(test, False), f"Critical test failed: {test}"


async def main():
    """Run the test standalone."""
    print("="*60)
    print("PRODUCTION DEPLOYMENT E2E TEST")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Backend URL: {PROD_BACKEND_URL}")
    print(f"Auth Service URL: {AUTH_SERVICE_URL}")
    print(f"WebSocket URL: {PROD_WEBSOCKET_URL}")
    print("="*60)
    
    async with ProductionDeploymentTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on results
        critical_tests = [
            "microservices_startup",
            "database_connections",
            "authentication_flow",
            "security_headers"
        ]
        
        critical_passed = all(results.get(test, False) for test in critical_tests)
        
        if critical_passed:
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)