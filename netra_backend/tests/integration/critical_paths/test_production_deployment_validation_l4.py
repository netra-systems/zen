#!/usr/bin/env python3
"""
Comprehensive test to verify production deployment readiness:
1. Service health checks across all microservices
2. Database connectivity and migration status
3. Configuration validation and secrets management
4. API endpoints availability and versioning
5. WebSocket scaling and load balancing
6. Monitoring and alerting pipelines
7. Backup and recovery procedures
8. Performance benchmarks and SLOs

This test validates the complete production deployment lifecycle.
"""

from netra_backend.tests.test_utils import setup_test_path

setup_test_path()

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import pytest
import websockets
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuration for production-like environment
PROD_BACKEND_URL = os.getenv("PROD_BACKEND_URL", "https://api.netrasystems.ai")
PROD_FRONTEND_URL = os.getenv("PROD_FRONTEND_URL", "https://app.netrasystems.ai")
PROD_WEBSOCKET_URL = os.getenv("PROD_WEBSOCKET_URL", "wss://api.netrasystems.ai/websocket")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "https://auth.netrasystems.ai")
METRICS_URL = os.getenv("METRICS_URL", "https://metrics.netrasystems.ai")
CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "https://clickhouse.netrasystems.ai")
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@postgres.netrasystems.ai/netra")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis.netrasystems.ai:6379")

# Deployment configuration
DEPLOYMENT_CONFIG = {
    "min_replicas": 3,
    "max_replicas": 10,
    "cpu_limit": "2000m",
    "memory_limit": "4Gi",
    "health_check_interval": 30,
    "readiness_timeout": 300,
    "rollback_on_failure": True,
    "canary_percentage": 10,
    "blue_green_enabled": True
}

# SLO thresholds
SLO_THRESHOLDS = {
    "availability": 99.9,  # 99.9% uptime
    "latency_p50": 100,    # 100ms p50 latency
    "latency_p95": 500,    # 500ms p95 latency
    "latency_p99": 1000,   # 1s p99 latency
    "error_rate": 0.1,     # 0.1% error rate
    "throughput": 10000    # 10k requests per second
}


class ProductionDeploymentValidator:
    """Validate production deployment readiness."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.deployment_id: Optional[str] = None
        self.metrics_data: Dict[str, Any] = {}
        self.health_status: Dict[str, bool] = {}
        self.performance_results: Dict[str, float] = {}
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.session:
            await self.session.close()
            
    async def validate_service_health(self) -> bool:
        """Validate health of all microservices."""
        print("\n[HEALTH] STEP 1: Validating service health...")
        
        services = [
            ("Backend API", f"{PROD_BACKEND_URL}/api/v1/health"),
            ("Auth Service", f"{AUTH_SERVICE_URL}/health"),
            ("Frontend", f"{PROD_FRONTEND_URL}/health"),
            ("Metrics Service", f"{METRICS_URL}/health"),
            ("WebSocket Gateway", f"{PROD_BACKEND_URL}/ws/health")
        ]
        
        all_healthy = True
        for service_name, health_url in services:
            try:
                async with self.session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.health_status[service_name] = data.get("status") == "healthy"
                        print(f"[OK] {service_name}: {data}")
                    else:
                        self.health_status[service_name] = False
                        print(f"[ERROR] {service_name} unhealthy: {response.status}")
                        all_healthy = False
            except Exception as e:
                self.health_status[service_name] = False
                print(f"[ERROR] {service_name} check failed: {e}")
                all_healthy = False
                
        return all_healthy
        
    async def validate_database_connectivity(self) -> bool:
        """Validate database connectivity and migrations."""
        print("\n[DATABASE] STEP 2: Validating database connectivity...")
        
        try:
            # Check PostgreSQL
            async with self.session.get(
                f"{PROD_BACKEND_URL}/api/v1/admin/database/status",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    postgres_ok = data.get("postgres", {}).get("connected", False)
                    clickhouse_ok = data.get("clickhouse", {}).get("connected", False)
                    redis_ok = data.get("redis", {}).get("connected", False)
                    
                    print(f"[{'OK' if postgres_ok else 'ERROR'}] PostgreSQL: {data.get('postgres')}")
                    print(f"[{'OK' if clickhouse_ok else 'ERROR'}] ClickHouse: {data.get('clickhouse')}")
                    print(f"[{'OK' if redis_ok else 'ERROR'}] Redis: {data.get('redis')}")
                    
                    # Check migration status
                    migrations_current = data.get("postgres", {}).get("migrations_current", False)
                    print(f"[{'OK' if migrations_current else 'ERROR'}] Migrations: {'Current' if migrations_current else 'Pending'}")
                    
                    return postgres_ok and clickhouse_ok and redis_ok and migrations_current
                else:
                    print(f"[ERROR] Database status check failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Database connectivity check failed: {e}")
            return False
            
    async def validate_configuration(self) -> bool:
        """Validate configuration and secrets management."""
        print("\n[CONFIG] STEP 3: Validating configuration...")
        
        try:
            # Check configuration endpoint
            async with self.session.get(
                f"{PROD_BACKEND_URL}/api/v1/admin/config/validate",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Validate required configurations
                    required_configs = [
                        "database_url",
                        "redis_url",
                        "clickhouse_url",
                        "jwt_secret",
                        "encryption_key",
                        "api_keys_configured",
                        "oauth_providers_configured",
                        "monitoring_enabled",
                        "alerting_enabled"
                    ]
                    
                    all_configured = True
                    for config in required_configs:
                        is_set = data.get(config, False)
                        print(f"[{'OK' if is_set else 'ERROR'}] {config}: {'Configured' if is_set else 'Missing'}")
                        if not is_set:
                            all_configured = False
                            
                    # Check for exposed secrets
                    no_exposed_secrets = not data.get("exposed_secrets", False)
                    print(f"[{'OK' if no_exposed_secrets else 'CRITICAL'}] Secrets: {'Secure' if no_exposed_secrets else 'EXPOSED'}")
                    
                    return all_configured and no_exposed_secrets
                else:
                    print(f"[ERROR] Configuration validation failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Configuration check failed: {e}")
            return False
            
    async def validate_api_endpoints(self) -> bool:
        """Validate critical API endpoints."""
        print("\n[API] STEP 4: Validating API endpoints...")
        
        endpoints = [
            ("Auth Login", "POST", f"{AUTH_SERVICE_URL}/auth/login"),
            ("User Profile", "GET", f"{PROD_BACKEND_URL}/api/v1/user/profile"),
            ("Threads List", "GET", f"{PROD_BACKEND_URL}/api/v1/threads"),
            ("Agent Status", "GET", f"{PROD_BACKEND_URL}/api/v1/agents/status"),
            ("Metrics Export", "GET", f"{METRICS_URL}/metrics"),
            ("WebSocket Info", "GET", f"{PROD_BACKEND_URL}/api/v1/websocket/info")
        ]
        
        all_available = True
        for endpoint_name, method, url in endpoints:
            try:
                headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
                
                if method == "GET":
                    async with self.session.get(url, headers=headers, timeout=10) as response:
                        is_ok = response.status in [200, 401]  # 401 is ok for auth-required endpoints
                        print(f"[{'OK' if is_ok else 'ERROR'}] {endpoint_name}: {response.status}")
                        if not is_ok:
                            all_available = False
                            
            except Exception as e:
                print(f"[ERROR] {endpoint_name} failed: {e}")
                all_available = False
                
        return all_available
        
    async def validate_websocket_scaling(self) -> bool:
        """Validate WebSocket scaling and load balancing."""
        print("\n[WEBSOCKET] STEP 5: Validating WebSocket scaling...")
        
        try:
            # Test multiple concurrent connections
            num_connections = 10
            connections = []
            
            for i in range(num_connections):
                try:
                    ws = await websockets.connect(
                        PROD_WEBSOCKET_URL,
                        extra_headers={"Authorization": f"Bearer {self.auth_token}"}
                    )
                    connections.append(ws)
                    print(f"[OK] Connection {i+1}/{num_connections} established")
                except Exception as e:
                    print(f"[ERROR] Connection {i+1} failed: {e}")
                    
            # Test message broadcasting
            if connections:
                test_message = {"type": "ping", "timestamp": datetime.utcnow().isoformat()}
                
                # Send from first connection
                await connections[0].send(json.dumps(test_message))
                
                # Check if load balancing distributes connections
                server_ids = set()
                for ws in connections:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=2)
                        data = json.loads(response)
                        server_id = data.get("server_id")
                        if server_id:
                            server_ids.add(server_id)
                    except:
                        pass
                        
                print(f"[INFO] Connected to {len(server_ids)} different servers")
                
                # Close all connections
                for ws in connections:
                    await ws.close()
                    
                return len(connections) >= num_connections * 0.8  # 80% success rate
                
        except Exception as e:
            print(f"[ERROR] WebSocket scaling test failed: {e}")
            return False
            
    async def validate_monitoring_pipeline(self) -> bool:
        """Validate monitoring and alerting pipelines."""
        print("\n[MONITORING] STEP 6: Validating monitoring pipeline...")
        
        try:
            # Check Prometheus metrics
            async with self.session.get(f"{METRICS_URL}/metrics") as response:
                if response.status == 200:
                    metrics_text = await response.text()
                    
                    # Check for critical metrics
                    critical_metrics = [
                        "http_requests_total",
                        "http_request_duration_seconds",
                        "websocket_connections_active",
                        "database_connections_active",
                        "agent_executions_total",
                        "error_rate",
                        "cpu_usage_percent",
                        "memory_usage_bytes"
                    ]
                    
                    metrics_found = {}
                    for metric in critical_metrics:
                        metrics_found[metric] = metric in metrics_text
                        print(f"[{'OK' if metrics_found[metric] else 'WARN'}] {metric}: {'Present' if metrics_found[metric] else 'Missing'}")
                        
                    # Check alerting rules
                    async with self.session.get(f"{METRICS_URL}/api/v1/rules") as rules_response:
                        if rules_response.status == 200:
                            rules_data = await rules_response.json()
                            num_rules = len(rules_data.get("groups", []))
                            print(f"[OK] Alerting rules configured: {num_rules}")
                        else:
                            print(f"[WARN] Could not fetch alerting rules")
                            
                    return all(metrics_found.values())
                else:
                    print(f"[ERROR] Metrics endpoint unavailable: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Monitoring validation failed: {e}")
            return False
            
    async def validate_backup_recovery(self) -> bool:
        """Validate backup and recovery procedures."""
        print("\n[BACKUP] STEP 7: Validating backup and recovery...")
        
        try:
            # Check backup status
            async with self.session.get(
                f"{PROD_BACKEND_URL}/api/v1/admin/backup/status",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check last backup time
                    last_backup = data.get("last_backup_timestamp")
                    if last_backup:
                        backup_time = datetime.fromisoformat(last_backup)
                        hours_since_backup = (datetime.utcnow() - backup_time).total_seconds() / 3600
                        backup_recent = hours_since_backup < 24
                        print(f"[{'OK' if backup_recent else 'WARN'}] Last backup: {hours_since_backup:.1f} hours ago")
                    else:
                        print(f"[ERROR] No backup found")
                        return False
                        
                    # Check backup integrity
                    backup_verified = data.get("last_verification_passed", False)
                    print(f"[{'OK' if backup_verified else 'ERROR'}] Backup integrity: {'Verified' if backup_verified else 'Failed'}")
                    
                    # Check recovery procedures
                    recovery_tested = data.get("recovery_test_passed", False)
                    print(f"[{'OK' if recovery_tested else 'WARN'}] Recovery test: {'Passed' if recovery_tested else 'Not tested'}")
                    
                    return backup_recent and backup_verified
                else:
                    print(f"[ERROR] Backup status check failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Backup validation failed: {e}")
            return False
            
    async def validate_performance_benchmarks(self) -> bool:
        """Validate performance against SLOs."""
        print("\n[PERFORMANCE] STEP 8: Validating performance benchmarks...")
        
        try:
            # Run performance tests
            test_duration = 10  # seconds
            start_time = time.time()
            request_times = []
            errors = 0
            
            print(f"[INFO] Running {test_duration} second performance test...")
            
            while time.time() - start_time < test_duration:
                request_start = time.time()
                try:
                    async with self.session.get(
                        f"{PROD_BACKEND_URL}/api/v1/health",
                        timeout=5
                    ) as response:
                        if response.status == 200:
                            request_times.append((time.time() - request_start) * 1000)
                        else:
                            errors += 1
                except:
                    errors += 1
                    
                await asyncio.sleep(0.1)  # 10 requests per second
                
            # Calculate metrics
            if request_times:
                request_times.sort()
                total_requests = len(request_times) + errors
                
                self.performance_results = {
                    "throughput": total_requests / test_duration,
                    "error_rate": (errors / total_requests) * 100,
                    "latency_p50": request_times[int(len(request_times) * 0.50)],
                    "latency_p95": request_times[int(len(request_times) * 0.95)],
                    "latency_p99": request_times[int(len(request_times) * 0.99)] if len(request_times) > 100 else request_times[-1]
                }
                
                # Check against SLOs
                slo_passed = True
                for metric, value in self.performance_results.items():
                    threshold = SLO_THRESHOLDS.get(metric)
                    if threshold:
                        if metric == "error_rate":
                            passed = value <= threshold
                        elif metric == "throughput":
                            passed = value >= threshold
                        else:
                            passed = value <= threshold
                            
                        print(f"[{'OK' if passed else 'FAIL'}] {metric}: {value:.2f} (SLO: {threshold})")
                        if not passed:
                            slo_passed = False
                            
                return slo_passed
            else:
                print(f"[ERROR] No successful requests completed")
                return False
                
        except Exception as e:
            print(f"[ERROR] Performance validation failed: {e}")
            return False
            
    async def validate_deployment_rollout(self) -> bool:
        """Validate deployment rollout strategy."""
        print("\n[DEPLOYMENT] STEP 9: Validating deployment rollout...")
        
        try:
            # Check deployment configuration
            async with self.session.get(
                f"{PROD_BACKEND_URL}/api/v1/admin/deployment/config",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Validate deployment settings
                    checks = {
                        "Blue-Green Enabled": data.get("blue_green_enabled", False),
                        "Canary Deployment": data.get("canary_enabled", False),
                        "Rollback Configured": data.get("rollback_on_failure", False),
                        "Health Checks": data.get("health_check_enabled", False),
                        "Gradual Rollout": data.get("gradual_rollout_enabled", False),
                        "Circuit Breaker": data.get("circuit_breaker_enabled", False)
                    }
                    
                    all_configured = True
                    for check_name, is_enabled in checks.items():
                        print(f"[{'OK' if is_enabled else 'WARN'}] {check_name}: {'Enabled' if is_enabled else 'Disabled'}")
                        if not is_enabled and check_name in ["Rollback Configured", "Health Checks"]:
                            all_configured = False
                            
                    # Check replica count
                    replicas = data.get("current_replicas", 0)
                    min_replicas = DEPLOYMENT_CONFIG["min_replicas"]
                    print(f"[{'OK' if replicas >= min_replicas else 'ERROR'}] Replicas: {replicas} (min: {min_replicas})")
                    
                    return all_configured and replicas >= min_replicas
                else:
                    print(f"[ERROR] Deployment config check failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Deployment validation failed: {e}")
            return False
            
    async def validate_security_posture(self) -> bool:
        """Validate security configuration."""
        print("\n[SECURITY] STEP 10: Validating security posture...")
        
        try:
            # Security checks
            async with self.session.get(
                f"{PROD_BACKEND_URL}/api/v1/admin/security/audit",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    security_checks = {
                        "TLS Enabled": data.get("tls_enabled", False),
                        "CORS Configured": data.get("cors_configured", False),
                        "Rate Limiting": data.get("rate_limiting_enabled", False),
                        "JWT Validation": data.get("jwt_validation_enabled", False),
                        "SQL Injection Protection": data.get("sql_injection_protected", False),
                        "XSS Protection": data.get("xss_protected", False),
                        "CSRF Protection": data.get("csrf_protected", False),
                        "Audit Logging": data.get("audit_logging_enabled", False),
                        "Encryption at Rest": data.get("encryption_at_rest", False),
                        "Secrets Rotation": data.get("secrets_rotation_enabled", False)
                    }
                    
                    all_secure = True
                    for check_name, is_enabled in security_checks.items():
                        print(f"[{'OK' if is_enabled else 'ERROR'}] {check_name}: {'Enabled' if is_enabled else 'Disabled'}")
                        if not is_enabled:
                            all_secure = False
                            
                    return all_secure
                else:
                    print(f"[ERROR] Security audit failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Security validation failed: {e}")
            return False
            
    async def run_all_validations(self) -> Dict[str, bool]:
        """Run all production validation tests."""
        results = {}
        
        # Get admin token for validation
        self.auth_token = os.getenv("ADMIN_AUTH_TOKEN", "test-admin-token")
        
        # Run all validations
        results["service_health"] = await self.validate_service_health()
        results["database_connectivity"] = await self.validate_database_connectivity()
        results["configuration"] = await self.validate_configuration()
        results["api_endpoints"] = await self.validate_api_endpoints()
        results["websocket_scaling"] = await self.validate_websocket_scaling()
        results["monitoring_pipeline"] = await self.validate_monitoring_pipeline()
        results["backup_recovery"] = await self.validate_backup_recovery()
        results["performance_benchmarks"] = await self.validate_performance_benchmarks()
        results["deployment_rollout"] = await self.validate_deployment_rollout()
        results["security_posture"] = await self.validate_security_posture()
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4
async def test_production_deployment_validation():
    """Test production deployment readiness."""
    async with ProductionDeploymentValidator() as validator:
        results = await validator.run_all_validations()
        
        # Print comprehensive report
        print("\n" + "="*80)
        print("PRODUCTION DEPLOYMENT VALIDATION REPORT")
        print("="*80)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"Environment: {os.getenv('ENVIRONMENT', 'production')}")
        print("="*80)
        
        # Validation results
        print("\nVALIDATION RESULTS:")
        print("-"*40)
        for validation_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {validation_name:30} : {status}")
            
        # Health status details
        if validator.health_status:
            print("\nSERVICE HEALTH:")
            print("-"*40)
            for service, healthy in validator.health_status.items():
                status = "✓ Healthy" if healthy else "✗ Unhealthy"
                print(f"  {service:30} : {status}")
                
        # Performance metrics
        if validator.performance_results:
            print("\nPERFORMANCE METRICS:")
            print("-"*40)
            for metric, value in validator.performance_results.items():
                threshold = SLO_THRESHOLDS.get(metric, "N/A")
                print(f"  {metric:30} : {value:.2f} (SLO: {threshold})")
                
        print("="*80)
        
        # Calculate overall result
        total_validations = len(results)
        passed_validations = sum(1 for passed in results.values() if passed)
        success_rate = (passed_validations / total_validations) * 100
        
        print(f"\nOVERALL: {passed_validations}/{total_validations} validations passed ({success_rate:.1f}%)")
        
        # Deployment decision
        critical_validations = [
            "service_health",
            "database_connectivity",
            "configuration",
            "security_posture"
        ]
        
        critical_passed = all(results.get(v, False) for v in critical_validations)
        
        if critical_passed and success_rate >= 80:
            print("\n[✓] DEPLOYMENT APPROVED: System is ready for production")
        elif critical_passed:
            print("\n[⚠] DEPLOYMENT WARNING: System has non-critical issues")
        else:
            print("\n[✗] DEPLOYMENT BLOCKED: Critical validations failed")
            
        # Assert critical validations passed
        assert critical_passed, f"Critical validations failed: {results}"
        
        # Warn if success rate is low
        if success_rate < 80:
            print(f"\n[WARNING] Success rate {success_rate:.1f}% is below 80% threshold")


async def main():
    """Run the validation standalone."""
    print("="*80)
    print("PRODUCTION DEPLOYMENT VALIDATION")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Target Environment: {os.getenv('ENVIRONMENT', 'production')}")
    print("="*80)
    
    async with ProductionDeploymentValidator() as validator:
        results = await validator.run_all_validations()
        
        # Return exit code based on critical validations
        critical_validations = [
            "service_health",
            "database_connectivity", 
            "configuration",
            "security_posture"
        ]
        
        if all(results.get(v, False) for v in critical_validations):
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)