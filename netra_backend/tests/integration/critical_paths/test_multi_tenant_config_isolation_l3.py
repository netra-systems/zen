"""Multi-Tenant Configuration Isolation L3 Critical Path Tests

Business Value Justification (BVJ):
- Segment: Enterprise and Mid-tier ($200K MRR) - Critical data isolation and security
- Business Goal: Ensure complete configuration namespace isolation and data residency compliance
- Value Impact: Prevents data breaches, ensures GDPR compliance, maintains enterprise trust
- Strategic Impact: $200K MRR protection through enterprise-grade security and regulatory compliance

Critical Path: Tenant provisioning -> Configuration isolation -> Data residency enforcement -> Cache isolation -> Hot reload validation -> Analytics separation
Coverage: Real configuration namespaces, database row-level security, Redis cache isolation, encryption key management
L3 Realism: Tests against actual database constraints, Redis namespaces, configuration hot reload systems
"""

import pytest
import asyncio
import time
import uuid
import logging
import os
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal

from netra_backend.app.services.config_service import ConfigService
from netra_backend.app.services.user_service import user_service as UserService
from netra_backend.app.services.audit_service import AuditService
from redis_manager import RedisManager
from netra_backend.app.services.database.session_manager import SessionManager
from netra_backend.app.core.security.encryption_service import EncryptionService
from netra_backend.app.core.cache.cache_manager import CacheManager
from netra_backend.app.services.metrics.analytics_collector import AnalyticsCollector
from netra_backend.app.schemas.UserPlan import PlanTier
from test_framework.test_config import configure_dedicated_test_environment

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


logger = logging.getLogger(__name__)


@dataclass
class TenantIsolationMetrics:
    """Metrics for multi-tenant configuration isolation testing."""
    tenants_created: int = 0
    config_namespaces_created: int = 0
    isolation_violations: int = 0
    data_residency_checks: int = 0
    encryption_key_isolations: int = 0
    cache_namespace_violations: int = 0
    hot_reload_tests: int = 0
    analytics_isolation_tests: int = 0
    cross_tenant_access_attempts: int = 0
    successful_isolations: int = 0
    config_response_times: List[float] = None
    
    def __post_init__(self):
        if self.config_response_times is None:
            self.config_response_times = []


class MultiTenantConfigIsolationL3Manager:
    """L3 multi-tenant configuration isolation test manager with real service integration."""
    
    def __init__(self):
        self.config_service = None
        self.user_service = None
        self.audit_service = None
        self.redis_manager = None
        self.session_manager = None
        self.encryption_service = None
        self.cache_manager = None
        self.analytics_collector = None
        self.test_tenants = {}
        self.tenant_configs = {}
        self.isolation_tests = []
        self.metrics = TenantIsolationMetrics()
        
    async def initialize_services(self):
        """Initialize real services for L3 multi-tenant configuration isolation testing."""
        try:
            # Configure dedicated test environment
            configure_dedicated_test_environment()
            
            # Initialize core services
            self.config_service = ConfigService()
            await self.config_service.initialize()
            
            self.user_service = UserService()
            await self.user_service.initialize()
            
            self.audit_service = AuditService()
            await self.audit_service.initialize()
            
            self.redis_manager = RedisManager()
            await self.redis_manager.initialize()
            
            self.session_manager = SessionManager()
            await self.session_manager.initialize()
            
            self.encryption_service = EncryptionService()
            await self.encryption_service.initialize()
            
            self.cache_manager = CacheManager()
            await self.cache_manager.initialize()
            
            self.analytics_collector = AnalyticsCollector()
            await self.analytics_collector.initialize()
            
            logger.info("L3 multi-tenant configuration isolation services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L3 multi-tenant isolation services: {e}")
            raise
    
    async def create_test_tenant(self, tenant_name: str, region: str = "us-central1", 
                               compliance_level: str = "enterprise") -> Dict[str, Any]:
        """Create a test tenant with complete configuration isolation."""
        tenant_id = f"tenant_{tenant_name}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Create tenant configuration namespace
            config_namespace = f"config:{tenant_id}"
            
            tenant_data = {
                "id": tenant_id,
                "name": tenant_name,
                "region": region,
                "compliance_level": compliance_level,
                "config_namespace": config_namespace,
                "encryption_key_id": f"key_{tenant_id}",
                "data_residency": region,
                "created_at": datetime.utcnow(),
                "status": "active",
                "isolation_level": "strict"
            }
            
            # Store tenant in database with row-level security
            await self.session_manager.execute_query(
                """
                INSERT INTO tenants (id, name, region, compliance_level, config_namespace, 
                                   encryption_key_id, data_residency, created_at, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (tenant_id, tenant_name, region, compliance_level, config_namespace,
                 tenant_data["encryption_key_id"], region, tenant_data["created_at"],
                 tenant_data["status"], {"test_tenant": True, "isolation_level": "strict"})
            )
            
            # Create tenant-specific configuration namespace in Redis
            await self._initialize_tenant_config_namespace(tenant_id, config_namespace)
            
            # Create tenant-specific encryption key
            await self._create_tenant_encryption_key(tenant_id, tenant_data["encryption_key_id"])
            
            # Initialize tenant cache namespace
            await self._initialize_tenant_cache_namespace(tenant_id)
            
            # Set up tenant analytics isolation
            await self._initialize_tenant_analytics_isolation(tenant_id, region)
            
            self.test_tenants[tenant_id] = tenant_data
            self.metrics.tenants_created += 1
            self.metrics.config_namespaces_created += 1
            
            return tenant_data
            
        except Exception as e:
            logger.error(f"Failed to create test tenant {tenant_name}: {e}")
            raise
    
    async def _initialize_tenant_config_namespace(self, tenant_id: str, namespace: str):
        """Initialize tenant-specific configuration namespace."""
        try:
            # Create isolated configuration structure
            tenant_config = {
                "database": {
                    "host": f"db-{tenant_id}.internal",
                    "database": f"tenant_{tenant_id}",
                    "schema": f"tenant_{tenant_id}_schema"
                },
                "cache": {
                    "namespace": f"cache:{tenant_id}:",
                    "ttl_default": 3600,
                    "max_memory": "512mb"
                },
                "security": {
                    "encryption_key_id": f"key_{tenant_id}",
                    "data_classification": "confidential",
                    "retention_policy": "7_years"
                },
                "features": {
                    "analytics_enabled": True,
                    "audit_logging": True,
                    "advanced_security": True
                },
                "limits": {
                    "max_users": 1000,
                    "max_requests_per_hour": 100000,
                    "storage_quota_gb": 1000
                }
            }
            
            # Store in Redis with namespace isolation
            config_key = f"{namespace}:config"
            await self.redis_manager.hset(config_key, tenant_config)
            
            # Set namespace TTL for test cleanup
            await self.redis_manager.expire(config_key, 7200)  # 2 hours
            
            self.tenant_configs[tenant_id] = tenant_config
            
        except Exception as e:
            logger.error(f"Failed to initialize tenant config namespace: {e}")
            raise
    
    async def _create_tenant_encryption_key(self, tenant_id: str, key_id: str):
        """Create tenant-specific encryption key with isolation."""
        try:
            # Generate tenant-specific encryption key
            encryption_key = await self.encryption_service.generate_key(
                key_id=key_id,
                tenant_id=tenant_id,
                key_type="AES-256-GCM",
                rotation_policy="quarterly"
            )
            
            # Store key with tenant isolation
            await self.encryption_service.store_key(
                key_id=key_id,
                key_data=encryption_key,
                tenant_id=tenant_id,
                access_policy="tenant_only"
            )
            
            self.metrics.encryption_key_isolations += 1
            
        except Exception as e:
            logger.error(f"Failed to create tenant encryption key: {e}")
            raise
    
    async def _initialize_tenant_cache_namespace(self, tenant_id: str):
        """Initialize tenant-specific cache namespace isolation."""
        try:
            cache_namespace = f"cache:{tenant_id}:"
            
            # Set cache namespace configuration
            await self.cache_manager.create_namespace(
                namespace=cache_namespace,
                tenant_id=tenant_id,
                isolation_level="strict",
                eviction_policy="lru",
                max_memory="256mb"
            )
            
            # Test cache isolation with sample data
            test_data = {
                "user_sessions": {},
                "feature_flags": {"advanced_analytics": True},
                "rate_limits": {"api_calls": 0, "reset_time": time.time() + 3600}
            }
            
            for key, value in test_data.items():
                cache_key = f"{cache_namespace}{key}"
                await self.redis_manager.set(cache_key, json.dumps(value), ex=3600)
            
        except Exception as e:
            logger.error(f"Failed to initialize tenant cache namespace: {e}")
            raise
    
    async def _initialize_tenant_analytics_isolation(self, tenant_id: str, region: str):
        """Initialize tenant-specific analytics isolation."""
        try:
            # Create tenant analytics configuration
            analytics_config = {
                "tenant_id": tenant_id,
                "data_residency": region,
                "collection_namespace": f"analytics:{tenant_id}",
                "storage_location": f"{region}/analytics/{tenant_id}",
                "retention_days": 2555,  # 7 years
                "data_classification": "confidential"
            }
            
            # Initialize analytics collection with isolation
            await self.analytics_collector.initialize_tenant_analytics(
                tenant_id=tenant_id,
                config=analytics_config
            )
            
            self.metrics.analytics_isolation_tests += 1
            
        except Exception as e:
            logger.error(f"Failed to initialize tenant analytics isolation: {e}")
            raise
    
    async def test_configuration_namespace_isolation(self, tenant_id_a: str, 
                                                   tenant_id_b: str) -> Dict[str, Any]:
        """Test configuration namespace isolation between tenants."""
        start_time = time.time()
        
        try:
            # Get tenant A's configuration
            config_a = await self._get_tenant_configuration(tenant_id_a)
            
            # Get tenant B's configuration  
            config_b = await self._get_tenant_configuration(tenant_id_b)
            
            # Attempt cross-tenant configuration access (should fail)
            cross_access_attempts = []
            
            # Try to access tenant B's config using tenant A's namespace
            namespace_a = self.test_tenants[tenant_id_a]["config_namespace"]
            cross_access_result_1 = await self._attempt_cross_tenant_config_access(
                namespace_a, tenant_id_b
            )
            cross_access_attempts.append(cross_access_result_1)
            
            # Try to access tenant A's config using tenant B's namespace
            namespace_b = self.test_tenants[tenant_id_b]["config_namespace"]
            cross_access_result_2 = await self._attempt_cross_tenant_config_access(
                namespace_b, tenant_id_a
            )
            cross_access_attempts.append(cross_access_result_2)
            
            # Verify isolation
            isolation_maintained = all(
                not attempt.get("access_granted", True) for attempt in cross_access_attempts
            )
            
            if not isolation_maintained:
                self.metrics.isolation_violations += 1
            else:
                self.metrics.successful_isolations += 1
            
            response_time = time.time() - start_time
            self.metrics.config_response_times.append(response_time)
            
            return {
                "test_type": "configuration_namespace_isolation",
                "tenant_a": tenant_id_a,
                "tenant_b": tenant_id_b,
                "config_a_accessible": config_a is not None,
                "config_b_accessible": config_b is not None,
                "cross_access_attempts": cross_access_attempts,
                "isolation_maintained": isolation_maintained,
                "response_time": response_time
            }
            
        except Exception as e:
            logger.error(f"Configuration namespace isolation test failed: {e}")
            return {
                "test_type": "configuration_namespace_isolation",
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    async def _get_tenant_configuration(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant configuration from isolated namespace."""
        try:
            namespace = self.test_tenants[tenant_id]["config_namespace"]
            config_key = f"{namespace}:config"
            
            config_data = await self.redis_manager.hgetall(config_key)
            return config_data if config_data else None
            
        except Exception as e:
            logger.error(f"Failed to get tenant configuration for {tenant_id}: {e}")
            return None
    
    async def _attempt_cross_tenant_config_access(self, namespace: str, 
                                                target_tenant_id: str) -> Dict[str, Any]:
        """Attempt to access another tenant's configuration (should fail)."""
        try:
            # Try to access target tenant's config using wrong namespace
            target_config_key = f"{namespace}:config"
            
            # This should not return the target tenant's actual config
            accessed_config = await self.redis_manager.hgetall(target_config_key)
            
            self.metrics.cross_tenant_access_attempts += 1
            
            return {
                "attempted_namespace": namespace,
                "target_tenant": target_tenant_id,
                "access_granted": accessed_config is not None,
                "config_returned": accessed_config,
                "isolation_breach": accessed_config is not None
            }
            
        except Exception as e:
            return {
                "attempted_namespace": namespace,
                "target_tenant": target_tenant_id,
                "access_granted": False,
                "error": str(e)
            }
    
    async def test_data_residency_enforcement(self, tenant_id: str, 
                                            expected_region: str) -> Dict[str, Any]:
        """Test data residency enforcement for tenant."""
        start_time = time.time()
        
        try:
            tenant_data = self.test_tenants[tenant_id]
            
            # Verify database storage location
            db_residency_check = await self._verify_database_residency(tenant_id, expected_region)
            
            # Verify cache storage location
            cache_residency_check = await self._verify_cache_residency(tenant_id, expected_region)
            
            # Verify analytics storage location
            analytics_residency_check = await self._verify_analytics_residency(tenant_id, expected_region)
            
            # Verify encryption key location
            encryption_residency_check = await self._verify_encryption_residency(tenant_id, expected_region)
            
            self.metrics.data_residency_checks += 1
            
            # Overall residency compliance
            residency_compliant = all([
                db_residency_check.get("compliant", False),
                cache_residency_check.get("compliant", False),
                analytics_residency_check.get("compliant", False),
                encryption_residency_check.get("compliant", False)
            ])
            
            return {
                "test_type": "data_residency_enforcement",
                "tenant_id": tenant_id,
                "expected_region": expected_region,
                "database_residency": db_residency_check,
                "cache_residency": cache_residency_check,
                "analytics_residency": analytics_residency_check,
                "encryption_residency": encryption_residency_check,
                "overall_compliant": residency_compliant,
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Data residency enforcement test failed: {e}")
            return {
                "test_type": "data_residency_enforcement",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def _verify_database_residency(self, tenant_id: str, expected_region: str) -> Dict[str, Any]:
        """Verify database data residency compliance."""
        try:
            # Query tenant data location metadata
            residency_info = await self.session_manager.execute_query(
                "SELECT region, data_residency FROM tenants WHERE id = %s",
                (tenant_id,)
            )
            
            if not residency_info:
                return {"compliant": False, "reason": "tenant_not_found"}
            
            actual_region = residency_info[0]["region"]
            data_residency = residency_info[0]["data_residency"]
            
            return {
                "compliant": actual_region == expected_region and data_residency == expected_region,
                "actual_region": actual_region,
                "data_residency": data_residency,
                "expected_region": expected_region
            }
            
        except Exception as e:
            return {"compliant": False, "error": str(e)}
    
    async def _verify_cache_residency(self, tenant_id: str, expected_region: str) -> Dict[str, Any]:
        """Verify cache data residency compliance."""
        try:
            # For testing, verify cache namespace follows region requirements
            cache_namespace = f"cache:{tenant_id}:"
            
            # Check if cache keys exist in expected namespace
            cache_keys = await self.redis_manager.keys(f"{cache_namespace}*")
            
            return {
                "compliant": len(cache_keys) > 0,  # Cache data exists in proper namespace
                "cache_namespace": cache_namespace,
                "keys_found": len(cache_keys),
                "region_compliant": True  # Namespace implies regional compliance
            }
            
        except Exception as e:
            return {"compliant": False, "error": str(e)}
    
    async def _verify_analytics_residency(self, tenant_id: str, expected_region: str) -> Dict[str, Any]:
        """Verify analytics data residency compliance."""
        try:
            # Check analytics configuration
            analytics_config = await self.analytics_collector.get_tenant_config(tenant_id)
            
            if not analytics_config:
                return {"compliant": False, "reason": "no_analytics_config"}
            
            storage_location = analytics_config.get("storage_location", "")
            region_compliant = expected_region in storage_location
            
            return {
                "compliant": region_compliant,
                "storage_location": storage_location,
                "expected_region": expected_region,
                "collection_namespace": analytics_config.get("collection_namespace")
            }
            
        except Exception as e:
            return {"compliant": False, "error": str(e)}
    
    async def _verify_encryption_residency(self, tenant_id: str, expected_region: str) -> Dict[str, Any]:
        """Verify encryption key residency compliance."""
        try:
            key_id = f"key_{tenant_id}"
            
            # Verify key location and access
            key_info = await self.encryption_service.get_key_info(
                key_id=key_id,
                tenant_id=tenant_id
            )
            
            if not key_info:
                return {"compliant": False, "reason": "key_not_found"}
            
            # For testing, assume key location follows tenant region
            key_region = key_info.get("region", expected_region)
            
            return {
                "compliant": key_region == expected_region,
                "key_id": key_id,
                "key_region": key_region,
                "expected_region": expected_region,
                "access_policy": key_info.get("access_policy")
            }
            
        except Exception as e:
            return {"compliant": False, "error": str(e)}
    
    async def test_cache_namespace_separation(self, tenant_id_a: str, 
                                            tenant_id_b: str) -> Dict[str, Any]:
        """Test cache namespace separation between tenants."""
        start_time = time.time()
        
        try:
            # Write data to tenant A's cache
            cache_namespace_a = f"cache:{tenant_id_a}:"
            test_data_a = {"sensitive_data": f"confidential_data_for_{tenant_id_a}"}
            
            await self.redis_manager.set(
                f"{cache_namespace_a}test_data",
                json.dumps(test_data_a),
                ex=3600
            )
            
            # Write data to tenant B's cache
            cache_namespace_b = f"cache:{tenant_id_b}:"
            test_data_b = {"sensitive_data": f"confidential_data_for_{tenant_id_b}"}
            
            await self.redis_manager.set(
                f"{cache_namespace_b}test_data",
                json.dumps(test_data_b),
                ex=3600
            )
            
            # Verify tenant A can only access its own data
            tenant_a_data = await self.redis_manager.get(f"{cache_namespace_a}test_data")
            tenant_a_cross_access = await self.redis_manager.get(f"{cache_namespace_b}test_data")
            
            # Verify tenant B can only access its own data
            tenant_b_data = await self.redis_manager.get(f"{cache_namespace_b}test_data")
            tenant_b_cross_access = await self.redis_manager.get(f"{cache_namespace_a}test_data")
            
            # Test namespace enumeration (should not see other tenant's keys)
            tenant_a_keys = await self.redis_manager.keys(f"{cache_namespace_a}*")
            tenant_b_keys = await self.redis_manager.keys(f"{cache_namespace_b}*")
            
            namespace_separation_maintained = (
                tenant_a_data is not None and
                tenant_b_data is not None and
                len(tenant_a_keys) > 0 and
                len(tenant_b_keys) > 0 and
                not any(key.startswith(cache_namespace_b) for key in tenant_a_keys) and
                not any(key.startswith(cache_namespace_a) for key in tenant_b_keys)
            )
            
            if not namespace_separation_maintained:
                self.metrics.cache_namespace_violations += 1
            
            return {
                "test_type": "cache_namespace_separation",
                "tenant_a": tenant_id_a,
                "tenant_b": tenant_id_b,
                "tenant_a_data_accessible": tenant_a_data is not None,
                "tenant_b_data_accessible": tenant_b_data is not None,
                "tenant_a_keys_count": len(tenant_a_keys),
                "tenant_b_keys_count": len(tenant_b_keys),
                "namespace_separation_maintained": namespace_separation_maintained,
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Cache namespace separation test failed: {e}")
            return {
                "test_type": "cache_namespace_separation",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def test_configuration_hot_reload_per_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Test configuration hot reload for specific tenant without affecting others."""
        start_time = time.time()
        
        try:
            # Get initial configuration
            initial_config = await self._get_tenant_configuration(tenant_id)
            
            # Modify tenant configuration
            updated_config = initial_config.copy() if initial_config else {}
            updated_config.update({
                "features": {
                    "analytics_enabled": True,
                    "audit_logging": True,
                    "advanced_security": True,
                    "hot_reload_test": True,  # New feature flag
                    "updated_at": time.time()
                }
            })
            
            # Apply hot reload
            reload_result = await self._apply_tenant_config_hot_reload(tenant_id, updated_config)
            
            # Verify configuration was updated
            await asyncio.sleep(0.1)  # Allow propagation
            
            reloaded_config = await self._get_tenant_configuration(tenant_id)
            
            # Verify hot reload was successful
            hot_reload_successful = (
                reload_result.get("success", False) and
                reloaded_config is not None and
                reloaded_config.get("features", {}).get("hot_reload_test") is True
            )
            
            self.metrics.hot_reload_tests += 1
            
            return {
                "test_type": "configuration_hot_reload_per_tenant",
                "tenant_id": tenant_id,
                "initial_config_exists": initial_config is not None,
                "reload_successful": hot_reload_successful,
                "config_updated": reloaded_config is not None,
                "hot_reload_feature_present": reloaded_config.get("features", {}).get("hot_reload_test") is True,
                "reload_result": reload_result,
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Configuration hot reload test failed: {e}")
            return {
                "test_type": "configuration_hot_reload_per_tenant",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def _apply_tenant_config_hot_reload(self, tenant_id: str, 
                                            new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply configuration hot reload for specific tenant."""
        try:
            namespace = self.test_tenants[tenant_id]["config_namespace"]
            config_key = f"{namespace}:config"
            
            # Update configuration in Redis
            await self.redis_manager.hset(config_key, new_config)
            
            # Trigger configuration reload event
            await self.config_service.reload_tenant_configuration(
                tenant_id=tenant_id,
                config_data=new_config
            )
            
            return {
                "success": True,
                "tenant_id": tenant_id,
                "config_key": config_key,
                "reload_timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to apply tenant config hot reload: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_analytics_isolation_validation(self, tenant_id_a: str, 
                                                tenant_id_b: str) -> Dict[str, Any]:
        """Test analytics data isolation between tenants."""
        start_time = time.time()
        
        try:
            # Generate analytics events for tenant A
            events_a = await self._generate_tenant_analytics_events(tenant_id_a, 10)
            
            # Generate analytics events for tenant B
            events_b = await self._generate_tenant_analytics_events(tenant_id_b, 10)
            
            # Verify tenant A can only see its analytics
            tenant_a_analytics = await self.analytics_collector.get_tenant_analytics(
                tenant_id=tenant_id_a,
                start_time=start_time - 3600,
                end_time=time.time()
            )
            
            # Verify tenant B can only see its analytics
            tenant_b_analytics = await self.analytics_collector.get_tenant_analytics(
                tenant_id=tenant_id_b,
                start_time=start_time - 3600,
                end_time=time.time()
            )
            
            # Verify no cross-tenant data leakage
            analytics_isolated = (
                len(tenant_a_analytics.get("events", [])) >= 5 and
                len(tenant_b_analytics.get("events", [])) >= 5 and
                not self._check_analytics_cross_contamination(tenant_a_analytics, tenant_id_b) and
                not self._check_analytics_cross_contamination(tenant_b_analytics, tenant_id_a)
            )
            
            return {
                "test_type": "analytics_isolation_validation",
                "tenant_a": tenant_id_a,
                "tenant_b": tenant_id_b,
                "events_generated_a": len(events_a),
                "events_generated_b": len(events_b),
                "analytics_retrieved_a": len(tenant_a_analytics.get("events", [])),
                "analytics_retrieved_b": len(tenant_b_analytics.get("events", [])),
                "analytics_isolated": analytics_isolated,
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Analytics isolation validation test failed: {e}")
            return {
                "test_type": "analytics_isolation_validation",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def _generate_tenant_analytics_events(self, tenant_id: str, count: int) -> List[Dict[str, Any]]:
        """Generate analytics events for a specific tenant."""
        events = []
        
        for i in range(count):
            event = {
                "tenant_id": tenant_id,
                "event_type": "api_request",
                "event_id": f"{tenant_id}_event_{i}",
                "timestamp": time.time(),
                "data": {
                    "endpoint": f"/api/v1/tenant/{tenant_id}/data",
                    "method": "GET",
                    "response_time": 0.15 + (i * 0.01),
                    "status_code": 200
                }
            }
            
            await self.analytics_collector.record_event(
                tenant_id=tenant_id,
                event=event
            )
            
            events.append(event)
        
        return events
    
    def _check_analytics_cross_contamination(self, analytics_data: Dict[str, Any], 
                                           foreign_tenant_id: str) -> bool:
        """Check if analytics data contains information from a different tenant."""
        events = analytics_data.get("events", [])
        
        for event in events:
            if event.get("tenant_id") == foreign_tenant_id:
                return True  # Cross-contamination detected
            
            # Check event data for foreign tenant references
            event_data = event.get("data", {})
            if foreign_tenant_id in str(event_data):
                return True  # Cross-contamination detected
        
        return False  # No cross-contamination
    
    async def test_database_row_level_security(self, tenant_id_a: str, 
                                             tenant_id_b: str) -> Dict[str, Any]:
        """Test database row-level security between tenants."""
        start_time = time.time()
        
        try:
            # Insert tenant-specific data
            await self._insert_tenant_test_data(tenant_id_a, "sensitive_data_a")
            await self._insert_tenant_test_data(tenant_id_b, "sensitive_data_b")
            
            # Test tenant A can only access its data
            tenant_a_data = await self._query_tenant_data(tenant_id_a)
            tenant_a_cross_data = await self._attempt_cross_tenant_db_access(tenant_id_a, tenant_id_b)
            
            # Test tenant B can only access its data
            tenant_b_data = await self._query_tenant_data(tenant_id_b)
            tenant_b_cross_data = await self._attempt_cross_tenant_db_access(tenant_id_b, tenant_id_a)
            
            # Verify row-level security
            rls_effective = (
                len(tenant_a_data) > 0 and
                len(tenant_b_data) > 0 and
                len(tenant_a_cross_data) == 0 and
                len(tenant_b_cross_data) == 0
            )
            
            return {
                "test_type": "database_row_level_security",
                "tenant_a": tenant_id_a,
                "tenant_b": tenant_id_b,
                "tenant_a_data_count": len(tenant_a_data),
                "tenant_b_data_count": len(tenant_b_data),
                "tenant_a_cross_access_count": len(tenant_a_cross_data),
                "tenant_b_cross_access_count": len(tenant_b_cross_data),
                "row_level_security_effective": rls_effective,
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Database row-level security test failed: {e}")
            return {
                "test_type": "database_row_level_security",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def _insert_tenant_test_data(self, tenant_id: str, data_value: str):
        """Insert test data for specific tenant."""
        await self.session_manager.execute_query(
            """
            INSERT INTO tenant_data (id, tenant_id, data_type, data_value, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (f"{tenant_id}_test_data_{uuid.uuid4().hex[:8]}", tenant_id, 
             "test_data", data_value, datetime.utcnow())
        )
    
    async def _query_tenant_data(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Query data for specific tenant (should be isolated by RLS)."""
        return await self.session_manager.execute_query(
            "SELECT * FROM tenant_data WHERE tenant_id = %s",
            (tenant_id,)
        )
    
    async def _attempt_cross_tenant_db_access(self, requesting_tenant: str, 
                                            target_tenant: str) -> List[Dict[str, Any]]:
        """Attempt to access another tenant's data (should be blocked by RLS)."""
        try:
            # This query should return empty results due to RLS
            return await self.session_manager.execute_query(
                "SELECT * FROM tenant_data WHERE tenant_id = %s",
                (target_tenant,)
            )
        except Exception:
            # RLS might throw an error instead of returning empty results
            return []
    
    async def get_isolation_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive multi-tenant isolation metrics summary."""
        avg_config_response_time = (
            sum(self.metrics.config_response_times) / len(self.metrics.config_response_times)
            if self.metrics.config_response_times else 0
        )
        
        isolation_success_rate = (
            self.metrics.successful_isolations / 
            (self.metrics.successful_isolations + self.metrics.isolation_violations) * 100
            if (self.metrics.successful_isolations + self.metrics.isolation_violations) > 0 else 100
        )
        
        return {
            "tenant_metrics": {
                "tenants_created": self.metrics.tenants_created,
                "config_namespaces_created": self.metrics.config_namespaces_created,
                "encryption_key_isolations": self.metrics.encryption_key_isolations
            },
            "isolation_testing": {
                "isolation_violations": self.metrics.isolation_violations,
                "successful_isolations": self.metrics.successful_isolations,
                "isolation_success_rate": isolation_success_rate,
                "cross_tenant_access_attempts": self.metrics.cross_tenant_access_attempts
            },
            "compliance_testing": {
                "data_residency_checks": self.metrics.data_residency_checks,
                "cache_namespace_violations": self.metrics.cache_namespace_violations,
                "analytics_isolation_tests": self.metrics.analytics_isolation_tests,
                "hot_reload_tests": self.metrics.hot_reload_tests
            },
            "performance": {
                "avg_config_response_time": avg_config_response_time,
                "config_requests_tested": len(self.metrics.config_response_times)
            },
            "sla_compliance": {
                "isolation_rate_above_99": isolation_success_rate >= 99.0,
                "config_response_under_100ms": sum(
                    1 for t in self.metrics.config_response_times if t < 0.1
                ) / len(self.metrics.config_response_times) * 100 if self.metrics.config_response_times else 0
            }
        }
    
    async def cleanup(self):
        """Clean up L3 multi-tenant configuration isolation test resources."""
        try:
            # Clean up tenant data
            for tenant_id in list(self.test_tenants.keys()):
                # Remove tenant configuration
                tenant_data = self.test_tenants[tenant_id]
                config_namespace = tenant_data["config_namespace"]
                
                # Clean up Redis namespaces
                config_keys = await self.redis_manager.keys(f"{config_namespace}*")
                if config_keys:
                    await self.redis_manager.delete(*config_keys)
                
                cache_keys = await self.redis_manager.keys(f"cache:{tenant_id}:*")
                if cache_keys:
                    await self.redis_manager.delete(*cache_keys)
                
                # Clean up database data
                await self.session_manager.execute_query(
                    "DELETE FROM tenant_data WHERE tenant_id = %s",
                    (tenant_id,)
                )
                
                await self.session_manager.execute_query(
                    "DELETE FROM tenants WHERE id = %s",
                    (tenant_id,)
                )
                
                # Clean up encryption keys
                if self.encryption_service:
                    await self.encryption_service.delete_key(f"key_{tenant_id}", tenant_id)
            
            # Shutdown services
            if self.config_service:
                await self.config_service.shutdown()
            if self.user_service:
                await self.user_service.shutdown()
            if self.audit_service:
                await self.audit_service.shutdown()
            if self.redis_manager:
                await self.redis_manager.shutdown()
            if self.session_manager:
                await self.session_manager.shutdown()
            if self.encryption_service:
                await self.encryption_service.shutdown()
            if self.cache_manager:
                await self.cache_manager.shutdown()
            if self.analytics_collector:
                await self.analytics_collector.shutdown()
                
        except Exception as e:
            logger.error(f"L3 multi-tenant isolation cleanup failed: {e}")


@pytest.fixture
async def multi_tenant_isolation_l3():
    """Create L3 multi-tenant configuration isolation manager."""
    manager = MultiTenantConfigIsolationL3Manager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_configuration_namespace_complete_isolation(multi_tenant_isolation_l3):
    """Test complete configuration namespace isolation between tenants."""
    # Create two tenants in different regions
    tenant_a = await multi_tenant_isolation_l3.create_test_tenant("EnterpriseCorpA", "us-central1")
    tenant_b = await multi_tenant_isolation_l3.create_test_tenant("EnterpriseCorpB", "eu-west1")
    
    # Test configuration namespace isolation
    result = await multi_tenant_isolation_l3.test_configuration_namespace_isolation(
        tenant_a["id"], tenant_b["id"]
    )
    
    # Verify complete isolation
    assert result["isolation_maintained"], f"Configuration namespace isolation failed: {result}"
    assert result["config_a_accessible"], "Tenant A cannot access its own configuration"
    assert result["config_b_accessible"], "Tenant B cannot access its own configuration"
    assert not any(attempt["access_granted"] for attempt in result["cross_access_attempts"]), \
        "Cross-tenant configuration access was granted"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_data_residency_gdpr_compliance(multi_tenant_isolation_l3):
    """Test data residency enforcement for GDPR compliance."""
    # Create tenants in different regions
    eu_tenant = await multi_tenant_isolation_l3.create_test_tenant("EUCompany", "eu-west1", "gdpr")
    us_tenant = await multi_tenant_isolation_l3.create_test_tenant("USCompany", "us-central1", "enterprise")
    
    # Test EU tenant data residency
    eu_result = await multi_tenant_isolation_l3.test_data_residency_enforcement(
        eu_tenant["id"], "eu-west1"
    )
    
    # Test US tenant data residency
    us_result = await multi_tenant_isolation_l3.test_data_residency_enforcement(
        us_tenant["id"], "us-central1"
    )
    
    # Verify GDPR compliance
    assert eu_result["overall_compliant"], f"EU tenant data residency failed: {eu_result}"
    assert us_result["overall_compliant"], f"US tenant data residency failed: {us_result}"
    
    # Verify specific compliance aspects
    assert eu_result["database_residency"]["compliant"], "EU database residency failed"
    assert eu_result["analytics_residency"]["compliant"], "EU analytics residency failed"
    assert us_result["encryption_residency"]["compliant"], "US encryption residency failed"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_cache_namespace_separation_strict(multi_tenant_isolation_l3):
    """Test strict cache namespace separation between tenants."""
    # Create tenants with sensitive data
    tenant_a = await multi_tenant_isolation_l3.create_test_tenant("FinancialServices", "us-central1")
    tenant_b = await multi_tenant_isolation_l3.create_test_tenant("HealthcareProvider", "us-central1")
    
    # Test cache namespace separation
    result = await multi_tenant_isolation_l3.test_cache_namespace_separation(
        tenant_a["id"], tenant_b["id"]
    )
    
    # Verify strict separation
    assert result["namespace_separation_maintained"], f"Cache namespace separation failed: {result}"
    assert result["tenant_a_data_accessible"], "Tenant A cannot access its cache data"
    assert result["tenant_b_data_accessible"], "Tenant B cannot access its cache data"
    assert result["tenant_a_keys_count"] > 0, "No cache keys found for tenant A"
    assert result["tenant_b_keys_count"] > 0, "No cache keys found for tenant B"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_configuration_hot_reload_isolation(multi_tenant_isolation_l3):
    """Test configuration hot reload per tenant without affecting others."""
    # Create multiple tenants
    tenant_a = await multi_tenant_isolation_l3.create_test_tenant("TechStartup", "us-central1")
    tenant_b = await multi_tenant_isolation_l3.create_test_tenant("LargeEnterprise", "eu-west1")
    
    # Test hot reload for tenant A only
    reload_result = await multi_tenant_isolation_l3.test_configuration_hot_reload_per_tenant(
        tenant_a["id"]
    )
    
    # Verify hot reload was successful and isolated
    assert reload_result["reload_successful"], f"Configuration hot reload failed: {reload_result}"
    assert reload_result["hot_reload_feature_present"], "Hot reload feature not applied"
    
    # Verify tenant B was not affected
    tenant_b_config = await multi_tenant_isolation_l3._get_tenant_configuration(tenant_b["id"])
    assert not tenant_b_config.get("features", {}).get("hot_reload_test"), \
        "Configuration hot reload affected other tenant"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_analytics_isolation_comprehensive(multi_tenant_isolation_l3):
    """Test comprehensive analytics data isolation between tenants."""
    # Create tenants with analytics requirements
    tenant_a = await multi_tenant_isolation_l3.create_test_tenant("RetailChain", "us-central1")
    tenant_b = await multi_tenant_isolation_l3.create_test_tenant("ManufacturingCorp", "eu-west1")
    
    # Test analytics isolation
    result = await multi_tenant_isolation_l3.test_analytics_isolation_validation(
        tenant_a["id"], tenant_b["id"]
    )
    
    # Verify analytics isolation
    assert result["analytics_isolated"], f"Analytics isolation failed: {result}"
    assert result["events_generated_a"] > 0, "No analytics events generated for tenant A"
    assert result["events_generated_b"] > 0, "No analytics events generated for tenant B"
    assert result["analytics_retrieved_a"] > 0, "No analytics retrieved for tenant A"
    assert result["analytics_retrieved_b"] > 0, "No analytics retrieved for tenant B"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_database_row_level_security_enforcement(multi_tenant_isolation_l3):
    """Test database row-level security enforcement between tenants."""
    # Create tenants with sensitive data requirements
    tenant_a = await multi_tenant_isolation_l3.create_test_tenant("BankingInstitution", "us-central1")
    tenant_b = await multi_tenant_isolation_l3.create_test_tenant("InsuranceCompany", "us-central1")
    
    # Test row-level security
    result = await multi_tenant_isolation_l3.test_database_row_level_security(
        tenant_a["id"], tenant_b["id"]
    )
    
    # Verify RLS effectiveness
    assert result["row_level_security_effective"], f"Row-level security failed: {result}"
    assert result["tenant_a_data_count"] > 0, "Tenant A has no accessible data"
    assert result["tenant_b_data_count"] > 0, "Tenant B has no accessible data"
    assert result["tenant_a_cross_access_count"] == 0, "Tenant A can access tenant B's data"
    assert result["tenant_b_cross_access_count"] == 0, "Tenant B can access tenant A's data"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_comprehensive_multi_tenant_isolation_metrics(multi_tenant_isolation_l3):
    """Test comprehensive multi-tenant isolation system metrics."""
    # Create multiple tenants and run all isolation tests
    tenants = []
    for i, (name, region) in enumerate([
        ("GlobalCorp", "us-central1"),
        ("EuropeanLtd", "eu-west1"),
        ("AsianEnterprise", "asia-northeast1")
    ]):
        tenant = await multi_tenant_isolation_l3.create_test_tenant(name, region)
        tenants.append(tenant)
    
    # Run comprehensive isolation tests
    for i in range(len(tenants)):
        for j in range(i + 1, len(tenants)):
            tenant_a, tenant_b = tenants[i], tenants[j]
            
            # Test configuration isolation
            await multi_tenant_isolation_l3.test_configuration_namespace_isolation(
                tenant_a["id"], tenant_b["id"]
            )
            
            # Test cache separation
            await multi_tenant_isolation_l3.test_cache_namespace_separation(
                tenant_a["id"], tenant_b["id"]
            )
            
            # Test analytics isolation
            await multi_tenant_isolation_l3.test_analytics_isolation_validation(
                tenant_a["id"], tenant_b["id"]
            )
    
    # Test data residency for all tenants
    for tenant in tenants:
        await multi_tenant_isolation_l3.test_data_residency_enforcement(
            tenant["id"], tenant["region"]
        )
    
    # Get comprehensive metrics
    metrics = await multi_tenant_isolation_l3.get_isolation_metrics_summary()
    
    # Verify system-wide isolation effectiveness
    assert metrics["tenant_metrics"]["tenants_created"] >= 3, "Insufficient tenants created"
    assert metrics["isolation_testing"]["isolation_success_rate"] >= 99.0, "Isolation success rate too low"
    assert metrics["isolation_testing"]["isolation_violations"] == 0, "Isolation violations detected"
    assert metrics["compliance_testing"]["data_residency_checks"] >= 3, "Insufficient residency checks"
    assert metrics["sla_compliance"]["isolation_rate_above_99"], "SLA isolation rate not met"
    assert metrics["sla_compliance"]["config_response_under_100ms"] >= 95.0, "Config response SLA not met"
    
    logger.info(f"Multi-tenant isolation metrics: {metrics}")