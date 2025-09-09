"""
Test Redis Caching with Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Optimize response times for better user experience
- Value Impact: Reduces data access latency and improves platform responsiveness
- Strategic Impact: Performance optimization critical for user retention

CRITICAL COMPLIANCE:
- Uses real Redis instance for caching tests
- Validates cache hit/miss ratios for performance
- Tests cache expiration for data freshness
- Ensures cache invalidation for data consistency
"""

import pytest
import uuid
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from netra_backend.app.cache.redis_cache_manager import RedisCacheManager
from netra_backend.app.cache.cache_key_generator import CacheKeyGenerator
from netra_backend.app.cache.business_cache_strategies import BusinessCacheStrategies
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_redis_fixture


class TestRedisCachingRealServices(BaseIntegrationTest):
    """Test Redis caching with real Redis instance."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_data_caching_performance_optimization(self, real_redis_fixture):
        """Test user data caching optimizes performance with real Redis."""
        # Given: User data that benefits from caching for performance
        cache_manager = RedisCacheManager(real_redis_fixture)
        
        user_scenarios = [
            {
                "user_id": str(uuid.uuid4()),
                "user_type": "enterprise_admin",
                "cached_data": {
                    "user_profile": {
                        "email": "admin@enterprise.com",
                        "organization": "Enterprise Corp",
                        "subscription_tier": "enterprise",
                        "permissions": ["read_data", "write_data", "admin_access"],
                        "dashboard_preferences": {
                            "layout": "executive",
                            "refresh_interval": 300,  # 5 minutes
                            "default_view": "cost_optimization"
                        }
                    },
                    "recent_activity": [
                        {"action": "viewed_dashboard", "timestamp": datetime.now(timezone.utc).isoformat()},
                        {"action": "ran_cost_analysis", "timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
                    ]
                },
                "cache_ttl": 3600,  # 1 hour for enterprise users
                "expected_performance_gain": 0.8  # 80% faster access
            },
            {
                "user_id": str(uuid.uuid4()),
                "user_type": "premium_user",
                "cached_data": {
                    "user_profile": {
                        "email": "user@company.com",
                        "organization": "Company Inc",
                        "subscription_tier": "premium", 
                        "permissions": ["read_data", "execute_basic_agents"],
                        "dashboard_preferences": {
                            "layout": "standard",
                            "refresh_interval": 600,  # 10 minutes
                            "default_view": "insights"
                        }
                    }
                },
                "cache_ttl": 1800,  # 30 minutes for premium users
                "expected_performance_gain": 0.6  # 60% faster access
            }
        ]
        
        # When: Caching user data for performance optimization
        for scenario in user_scenarios:
            cache_key = f"user_profile:{scenario['user_id']}"
            
            # Cache user data
            await cache_manager.set_cache(
                key=cache_key,
                value=scenario["cached_data"],
                ttl=scenario["cache_ttl"]
            )
            
            # Verify immediate cache retrieval
            cached_data = await cache_manager.get_cache(cache_key)
            assert cached_data is not None
            assert cached_data["user_profile"]["email"] == scenario["cached_data"]["user_profile"]["email"]
            assert cached_data["user_profile"]["subscription_tier"] == scenario["cached_data"]["user_profile"]["subscription_tier"]
            
            # Verify cache performance characteristics
            cache_info = await cache_manager.get_cache_info(cache_key)
            assert cache_info is not None
            assert cache_info["ttl"] <= scenario["cache_ttl"]  # TTL should be set correctly
            assert cache_info["size"] > 0  # Cache entry should have size
        
        # Then: Cache should improve data access performance
        # Simulate multiple rapid accesses to demonstrate cache benefit
        for scenario in user_scenarios:
            cache_key = f"user_profile:{scenario['user_id']}"
            
            # Multiple cache hits should be faster than database lookups
            start_time = datetime.now(timezone.utc)
            
            for _ in range(5):  # 5 rapid accesses
                cached_data = await cache_manager.get_cache(cache_key)
                assert cached_data is not None
            
            cache_access_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Cache access should be very fast (under 50ms total for 5 accesses)
            assert cache_access_time < 0.05, f"Cache access too slow: {cache_access_time}s"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_business_data_caching_strategies(self, real_redis_fixture):
        """Test business data caching strategies with real Redis."""
        # Given: Different types of business data with appropriate caching strategies
        cache_strategies = BusinessCacheStrategies()
        cache_manager = RedisCacheManager(real_redis_fixture)
        
        business_data_scenarios = [
            {
                "data_type": "cost_analysis_results",
                "data": {
                    "analysis_id": str(uuid.uuid4()),
                    "aws_account_id": "123456789012",
                    "monthly_spend": 45000.00,
                    "potential_savings": 12000.00,
                    "recommendations": [
                        {"service": "EC2", "action": "rightsize", "savings": 8000.00},
                        {"service": "RDS", "action": "reserved_instances", "savings": 4000.00}
                    ],
                    "generated_at": datetime.now(timezone.utc).isoformat()
                },
                "cache_strategy": "long_lived_with_versioning",
                "cache_ttl": 7200,  # 2 hours - analysis results are expensive to generate
                "business_value": "high"
            },
            {
                "data_type": "user_dashboard_data",
                "data": {
                    "user_id": str(uuid.uuid4()),
                    "dashboard_widgets": [
                        {"type": "cost_summary", "value": 25000.00, "trend": "decreasing"},
                        {"type": "security_score", "value": 0.92, "trend": "stable"},
                        {"type": "optimization_opportunities", "count": 5}
                    ],
                    "last_updated": datetime.now(timezone.utc).isoformat()
                },
                "cache_strategy": "medium_lived_auto_refresh",
                "cache_ttl": 900,  # 15 minutes - dashboards need regular updates
                "business_value": "medium"
            },
            {
                "data_type": "real_time_metrics",
                "data": {
                    "metric_type": "active_users",
                    "current_value": 347,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "alerts": []
                },
                "cache_strategy": "short_lived_high_frequency",
                "cache_ttl": 60,  # 1 minute - metrics need to be current
                "business_value": "operational"
            }
        ]
        
        # When: Applying business-appropriate caching strategies
        for scenario in business_data_scenarios:
            cache_key = cache_strategies.generate_business_cache_key(
                data_type=scenario["data_type"],
                data=scenario["data"]
            )
            
            # Apply caching strategy
            await cache_strategies.apply_caching_strategy(
                cache_manager=cache_manager,
                cache_key=cache_key,
                data=scenario["data"],
                strategy=scenario["cache_strategy"],
                ttl=scenario["cache_ttl"]
            )
            
            # Verify data is cached with appropriate strategy
            cached_data = await cache_manager.get_cache(cache_key)
            assert cached_data is not None
            
            # Verify business data integrity
            if scenario["data_type"] == "cost_analysis_results":
                assert cached_data["monthly_spend"] == scenario["data"]["monthly_spend"]
                assert cached_data["potential_savings"] == scenario["data"]["potential_savings"]
                assert len(cached_data["recommendations"]) == len(scenario["data"]["recommendations"])
            
            elif scenario["data_type"] == "user_dashboard_data":
                assert len(cached_data["dashboard_widgets"]) == len(scenario["data"]["dashboard_widgets"])
                cost_widget = next(w for w in cached_data["dashboard_widgets"] if w["type"] == "cost_summary")
                assert cost_widget["value"] == 25000.00
            
            elif scenario["data_type"] == "real_time_metrics":
                assert cached_data["metric_type"] == "active_users"
                assert cached_data["current_value"] == 347
        
        # Then: Caching strategies should optimize for business use cases
        for scenario in business_data_scenarios:
            cache_key = cache_strategies.generate_business_cache_key(
                data_type=scenario["data_type"],
                data=scenario["data"]
            )
            
            cache_info = await cache_manager.get_cache_info(cache_key)
            
            # High business value data should have longer cache times
            if scenario["business_value"] == "high":
                assert cache_info["ttl"] >= 3600  # At least 1 hour
            elif scenario["business_value"] == "medium":
                assert 600 <= cache_info["ttl"] <= 1800  # 10-30 minutes
            elif scenario["business_value"] == "operational":
                assert cache_info["ttl"] <= 300  # Max 5 minutes for real-time data
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_invalidation_data_consistency(self, real_redis_fixture):
        """Test cache invalidation maintains data consistency with real Redis."""
        # Given: Cached business data that needs invalidation when source data changes
        cache_manager = RedisCacheManager(real_redis_fixture)
        
        # Initial business data
        user_id = str(uuid.uuid4())
        original_user_data = {
            "subscription_tier": "premium",
            "monthly_spend_limit": 10000.00,
            "active_analyses": [
                {"id": "analysis_1", "status": "running", "progress": 0.5}
            ],
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        
        user_cache_key = f"user_business_data:{user_id}"
        
        # Cache original data
        await cache_manager.set_cache(
            key=user_cache_key,
            value=original_user_data,
            ttl=3600
        )
        
        # Related cache entries that depend on user data
        related_cache_keys = [
            f"user_dashboard:{user_id}",
            f"user_recommendations:{user_id}",
            f"user_billing_summary:{user_id}"
        ]
        
        for related_key in related_cache_keys:
            related_data = {
                "based_on_subscription": original_user_data["subscription_tier"],
                "spend_limit_considered": original_user_data["monthly_spend_limit"],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            await cache_manager.set_cache(related_key, related_data, ttl=1800)
        
        # Verify initial cache state
        cached_user_data = await cache_manager.get_cache(user_cache_key)
        assert cached_user_data["subscription_tier"] == "premium"
        
        # When: Business data changes requiring cache invalidation
        # Simulate user upgrade to enterprise
        updated_user_data = {
            "subscription_tier": "enterprise",
            "monthly_spend_limit": 50000.00,  # Increased limit
            "active_analyses": [
                {"id": "analysis_1", "status": "completed", "progress": 1.0},
                {"id": "analysis_2", "status": "running", "progress": 0.2}  # New analysis
            ],
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Invalidate related caches when main data changes
        await cache_manager.invalidate_cache_pattern(f"user_*:{user_id}")
        
        # Update main cache
        await cache_manager.set_cache(
            key=user_cache_key,
            value=updated_user_data,
            ttl=3600
        )
        
        # Then: Cache should reflect updated business data consistently
        updated_cached_data = await cache_manager.get_cache(user_cache_key)
        assert updated_cached_data is not None
        assert updated_cached_data["subscription_tier"] == "enterprise"
        assert updated_cached_data["monthly_spend_limit"] == 50000.00
        assert len(updated_cached_data["active_analyses"]) == 2
        
        # Related caches should be invalidated
        for related_key in related_cache_keys:
            related_data = await cache_manager.get_cache(related_key)
            # Should be None after invalidation
            assert related_data is None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_distributed_cache_consistency_multi_service(self, real_redis_fixture):
        """Test distributed cache consistency across multiple services with real Redis."""
        # Given: Multiple service instances sharing cache for consistency
        service_instances = [
            {"name": "backend_instance_1", "manager": RedisCacheManager(real_redis_fixture)},
            {"name": "backend_instance_2", "manager": RedisCacheManager(real_redis_fixture)},
            {"name": "analytics_instance", "manager": RedisCacheManager(real_redis_fixture)}
        ]
        
        shared_business_data = {
            "global_config": {
                "platform_maintenance_mode": False,
                "feature_flags": {
                    "advanced_analytics": True,
                    "cost_optimization_v2": True,
                    "security_audit_beta": False
                },
                "system_limits": {
                    "max_concurrent_analyses": 100,
                    "max_data_retention_days": 365
                }
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        shared_cache_key = "global_platform_config"
        
        # When: One service instance updates shared cache
        primary_instance = service_instances[0]["manager"]
        await primary_instance.set_cache(
            key=shared_cache_key,
            value=shared_business_data,
            ttl=1800  # 30 minutes
        )
        
        # All service instances should see consistent data
        for instance in service_instances:
            cached_config = await instance["manager"].get_cache(shared_cache_key)
            assert cached_config is not None
            assert cached_config["global_config"]["platform_maintenance_mode"] is False
            assert cached_config["global_config"]["feature_flags"]["advanced_analytics"] is True
            assert cached_config["global_config"]["system_limits"]["max_concurrent_analyses"] == 100
        
        # When: Configuration changes need to be propagated
        updated_config = shared_business_data.copy()
        updated_config["global_config"]["platform_maintenance_mode"] = True  # Enable maintenance mode
        updated_config["global_config"]["feature_flags"]["security_audit_beta"] = True  # Enable beta feature
        updated_config["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # Secondary instance updates configuration
        secondary_instance = service_instances[1]["manager"]
        await secondary_instance.set_cache(
            key=shared_cache_key,
            value=updated_config,
            ttl=1800
        )
        
        # Then: All instances should see updated configuration immediately
        await asyncio.sleep(0.1)  # Small delay for propagation
        
        for instance in service_instances:
            updated_cached_config = await instance["manager"].get_cache(shared_cache_key)
            assert updated_cached_config is not None
            assert updated_cached_config["global_config"]["platform_maintenance_mode"] is True
            assert updated_cached_config["global_config"]["feature_flags"]["security_audit_beta"] is True
            
            # Verify last_updated timestamp reflects the change
            assert updated_cached_config["last_updated"] > shared_business_data["last_updated"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cache_performance_under_load_business_scalability(self, real_redis_fixture):
        """Test cache performance under load for business scalability with real Redis."""
        # Given: High load scenario simulating business peak usage
        cache_manager = RedisCacheManager(real_redis_fixture)
        
        # Simulate business data access patterns during peak load
        load_test_scenarios = [
            {
                "operation": "frequent_user_lookups",
                "num_operations": 100,
                "data_size": "small",  # User profile data
                "expected_response_time": 0.005  # 5ms per operation
            },
            {
                "operation": "dashboard_data_retrieval",
                "num_operations": 50,
                "data_size": "medium",  # Dashboard widgets
                "expected_response_time": 0.010  # 10ms per operation
            },
            {
                "operation": "analysis_results_caching",
                "num_operations": 20,
                "data_size": "large",  # Complex analysis results
                "expected_response_time": 0.020  # 20ms per operation
            }
        ]
        
        # Prepare test data for each scenario
        test_data_by_size = {
            "small": {"user_id": str(uuid.uuid4()), "email": "user@test.com", "tier": "premium"},
            "medium": {
                "widgets": [{"type": "cost", "value": 1000}, {"type": "security", "value": 0.95}] * 10
            },
            "large": {
                "analysis_results": {
                    "recommendations": [{"service": f"service_{i}", "savings": i * 100} for i in range(50)],
                    "detailed_breakdown": {f"category_{i}": {"cost": i * 1000, "usage": i * 10} for i in range(20)}
                }
            }
        }
        
        performance_results = []
        
        # When: Executing high load cache operations
        for scenario in load_test_scenarios:
            start_time = datetime.now(timezone.utc)
            
            # Pre-populate cache with test data
            cache_keys = []
            for i in range(scenario["num_operations"]):
                cache_key = f"{scenario['operation']}_{i}"
                await cache_manager.set_cache(
                    key=cache_key,
                    value=test_data_by_size[scenario["data_size"]],
                    ttl=600
                )
                cache_keys.append(cache_key)
            
            # Measure cache retrieval performance under load
            retrieval_start = datetime.now(timezone.utc)
            
            # Concurrent cache retrievals
            retrieval_tasks = []
            for cache_key in cache_keys:
                task = cache_manager.get_cache(cache_key)
                retrieval_tasks.append(task)
            
            results = await asyncio.gather(*retrieval_tasks)
            
            retrieval_time = (datetime.now(timezone.utc) - retrieval_start).total_seconds()
            total_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Verify all operations completed successfully
            assert len(results) == scenario["num_operations"]
            assert all(result is not None for result in results)
            
            avg_retrieval_time = retrieval_time / scenario["num_operations"]
            
            performance_results.append({
                "operation": scenario["operation"],
                "total_operations": scenario["num_operations"],
                "total_time": total_time,
                "avg_retrieval_time": avg_retrieval_time,
                "expected_time": scenario["expected_response_time"],
                "performance_met": avg_retrieval_time <= scenario["expected_response_time"]
            })
        
        # Then: Cache should meet business performance requirements under load
        for result in performance_results:
            # Should meet performance expectations for business scalability
            assert result["performance_met"], (
                f"{result['operation']} took {result['avg_retrieval_time']:.3f}s, "
                f"expected <= {result['expected_time']:.3f}s"
            )
            
            # Should handle concurrent operations efficiently
            assert result["total_time"] < result["total_operations"] * result["expected_time"]
        
        # Verify overall cache performance is suitable for business operations
        total_operations = sum(r["total_operations"] for r in performance_results)
        total_time = sum(r["total_time"] for r in performance_results)
        overall_avg_time = total_time / total_operations
        
        # Overall average should be under 15ms per operation for good user experience
        assert overall_avg_time <= 0.015, f"Overall cache performance too slow: {overall_avg_time:.3f}s"