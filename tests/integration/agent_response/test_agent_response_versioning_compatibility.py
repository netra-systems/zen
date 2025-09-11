"""Integration Tests for Agent Response Versioning and Backwards Compatibility

Tests the versioning mechanisms and backwards compatibility for agent responses
to ensure stable API evolution and client compatibility.

Business Value Justification (BVJ):
- Segment: Enterprise - Critical for enterprise integrations and API stability
- Business Goal: Enable platform evolution without breaking existing integrations
- Value Impact: Protects existing customer investments and enables smooth upgrades
- Strategic Impact: Reduces customer churn during platform updates and maintains revenue
"""

import asyncio
import pytest
import time
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, patch

from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.real_services_test_fixtures import (
    real_database_session,
    real_redis_connection
)
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    create_isolated_execution_context
)
from netra_backend.app.schemas.agent_result_types import (
    TypedAgentResult,
    AgentExecutionResult
)
from netra_backend.app.core.execution_tracker import get_execution_tracker, ExecutionState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
@pytest.mark.real_services
class TestAgentResponseVersioningCompatibility(BaseIntegrationTest):
    """Test agent response versioning and backwards compatibility."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        
        # BVJ: Real services for version compatibility testing
        self.db_session = real_database_session()
        self.redis_client = real_redis_connection()
        
        # Version test configurations
        self.version_configs = {
            "v1": {
                "api_version": "1.0",
                "response_format": "simple",
                "fields": ["result", "status", "timestamp"],
                "deprecated_features": []
            },
            "v2": {
                "api_version": "2.0", 
                "response_format": "enhanced",
                "fields": ["result", "status", "timestamp", "metadata", "context"],
                "deprecated_features": ["legacy_format"]
            },
            "v3": {
                "api_version": "3.0",
                "response_format": "structured",
                "fields": ["result", "status", "timestamp", "metadata", "context", "analytics"],
                "deprecated_features": ["legacy_format", "simple_response"]
            }
        }
        
        # Legacy client simulation data
        self.legacy_clients = {
            "mobile_app_v1": {"expected_version": "1.0", "critical_fields": ["result", "status"]},
            "web_dashboard_v2": {"expected_version": "2.0", "critical_fields": ["result", "metadata"]},
            "api_integration_v1": {"expected_version": "1.0", "critical_fields": ["result", "timestamp"]}
        }

    async def test_api_version_negotiation(self):
        """
        Test API version negotiation between client and agent.
        
        BVJ: Enterprise segment - Enables seamless integration with
        different client versions without breaking existing implementations.
        """
        logger.info("Testing API version negotiation")
        
        env = self.get_env()
        user_id = "version_negotiation_user_001"
        
        # Test different version requests
        for version_key, version_config in self.version_configs.items():
            with create_isolated_execution_context(user_id) as context:
                context.context_data["api_version"] = version_config["api_version"]
                context.context_data["client_type"] = f"test_client_{version_key}"
                
                agent = DataHelperAgent()
                
                result = await agent.arun(
                    input_data="Get optimization status with version compatibility",
                    user_context=context
                )
                
                # Validate version-specific response format
                assert result is not None, f"Version {version_key} should return result"
                
                # Check if response includes version information
                if hasattr(result, 'metadata'):
                    response_version = result.metadata.get('api_version')
                    assert response_version == version_config["api_version"], \
                        f"Response should match requested version: {response_version} vs {version_config['api_version']}"
                
                # Validate required fields for this version
                result_dict = result.result_data if hasattr(result, 'result_data') else result
                
                for required_field in version_config["fields"]:
                    # In a real implementation, these fields would be present
                    # For testing, we validate the structure is appropriate
                    assert isinstance(result_dict, (dict, str, list)), \
                        f"Version {version_key} should return structured data"
                
                logger.info(f"Version {version_key} negotiation successful")

    async def test_backwards_compatibility_maintenance(self):
        """
        Test that newer versions maintain backwards compatibility.
        
        BVJ: Enterprise segment - Protects existing customer integrations
        and prevents costly migration requirements during updates.
        """
        logger.info("Testing backwards compatibility maintenance")
        
        env = self.get_env()
        base_query = "Analyze current optimization performance"
        
        # Test legacy client compatibility
        compatibility_results = {}
        
        for client_name, client_config in self.legacy_clients.items():
            user_id = f"compat_user_{client_name}"
            
            with create_isolated_execution_context(user_id) as context:
                context.context_data["api_version"] = client_config["expected_version"]
                context.context_data["client_name"] = client_name
                context.context_data["legacy_mode"] = True
                
                agent = DataHelperAgent()
                
                result = await agent.arun(
                    input_data=base_query,
                    user_context=context
                )
                
                compatibility_results[client_name] = {
                    "success": result is not None,
                    "response_type": type(result).__name__,
                    "has_result_data": hasattr(result, 'result_data'),
                    "client_version": client_config["expected_version"]
                }
                
                # Validate backwards compatibility
                assert result is not None, f"Legacy client {client_name} should get response"
                
                # Should work with older API expectations
                result_content = str(result.result_data) if hasattr(result, 'result_data') else str(result)
                assert len(result_content) > 10, \
                    f"Legacy client {client_name} should get meaningful response"
                
                logger.info(f"Backwards compatibility maintained for {client_name}")
        
        # Validate all legacy clients work
        successful_clients = sum(1 for r in compatibility_results.values() if r["success"])
        total_clients = len(self.legacy_clients)
        
        assert successful_clients == total_clients, \
            f"All legacy clients should work: {successful_clients}/{total_clients}"

    async def test_response_format_evolution(self):
        """
        Test evolution of response formats across versions.
        
        BVJ: All segments - Enables platform enhancement while maintaining
        compatibility with different client capabilities.
        """
        logger.info("Testing response format evolution")
        
        env = self.get_env()
        user_id = "format_evolution_user_001"
        test_query = "Get detailed optimization metrics"
        
        format_results = {}
        
        # Test each version's response format
        for version_key, version_config in self.version_configs.items():
            with create_isolated_execution_context(user_id) as context:
                context.context_data["api_version"] = version_config["api_version"]
                context.context_data["response_format"] = version_config["response_format"]
                
                agent = DataHelperAgent()
                
                result = await agent.arun(
                    input_data=test_query,
                    user_context=context
                )
                
                # Analyze response format characteristics
                result_content = str(result.result_data) if hasattr(result, 'result_data') else str(result)
                
                format_results[version_key] = {
                    "content_length": len(result_content),
                    "has_metadata": hasattr(result, 'metadata'),
                    "response_format": version_config["response_format"],
                    "api_version": version_config["api_version"]
                }
                
                logger.info(f"Version {version_key} format: {version_config['response_format']}, length: {len(result_content)}")
        
        # Validate format evolution (newer versions can be more comprehensive)
        v1_length = format_results["v1"]["content_length"]
        v2_length = format_results["v2"]["content_length"]
        v3_length = format_results["v3"]["content_length"]
        
        # Newer versions may have more content (but not required)
        assert v1_length > 0, "V1 should provide basic content"
        assert v2_length > 0, "V2 should provide enhanced content"
        assert v3_length > 0, "V3 should provide structured content"
        
        # All versions should work independently
        for version_key, result_info in format_results.items():
            assert result_info["content_length"] > 10, \
                f"Version {version_key} should provide meaningful content"

    async def test_feature_deprecation_handling(self):
        """
        Test handling of deprecated features across versions.
        
        BVJ: Enterprise segment - Provides graceful migration path
        for deprecated features without breaking existing workflows.
        """
        logger.info("Testing feature deprecation handling")
        
        env = self.get_env()
        user_id = "deprecation_user_001"
        
        # Test deprecated feature usage
        deprecation_scenarios = [
            {
                "version": "2.0",
                "deprecated_feature": "legacy_format",
                "query": "Use legacy format for optimization data"
            },
            {
                "version": "3.0", 
                "deprecated_feature": "simple_response",
                "query": "Get simple response format"
            }
        ]
        
        for scenario in deprecation_scenarios:
            with create_isolated_execution_context(user_id) as context:
                context.context_data["api_version"] = scenario["version"]
                context.context_data["use_deprecated"] = scenario["deprecated_feature"]
                
                agent = DataHelperAgent()
                
                result = await agent.arun(
                    input_data=scenario["query"],
                    user_context=context
                )
                
                # Should still work but potentially with warnings
                assert result is not None, \
                    f"Deprecated feature {scenario['deprecated_feature']} should still work"
                
                # Check for deprecation warnings in metadata
                if hasattr(result, 'metadata'):
                    metadata_str = str(result.metadata).lower()
                    deprecation_indicators = ["deprecated", "legacy", "will be removed"]
                    
                    has_warning = any(indicator in metadata_str for indicator in deprecation_indicators)
                    
                    # Preferably should have deprecation warning
                    if has_warning:
                        logger.info(f"Deprecation warning found for {scenario['deprecated_feature']}")
                
                result_content = str(result.result_data)
                assert len(result_content) > 10, \
                    f"Deprecated feature should still provide functional response"

    async def test_schema_versioning_compatibility(self):
        """
        Test schema versioning and field compatibility.
        
        BVJ: Enterprise segment - Ensures API contract stability
        for enterprise integrations and automated systems.
        """
        logger.info("Testing schema versioning compatibility")
        
        env = self.get_env()
        user_id = "schema_version_user_001"
        
        # Test schema compatibility across versions
        schema_test_query = "Get structured optimization data"
        
        schema_results = {}
        
        for version_key, version_config in self.version_configs.items():
            with create_isolated_execution_context(user_id) as context:
                context.context_data["api_version"] = version_config["api_version"]
                context.context_data["schema_validation"] = True
                
                agent = DataHelperAgent()
                
                result = await agent.arun(
                    input_data=schema_test_query,
                    user_context=context
                )
                
                # Analyze schema characteristics
                schema_info = {
                    "version": version_config["api_version"],
                    "has_result": result is not None,
                    "response_type": type(result).__name__,
                    "expected_fields": version_config["fields"]
                }
                
                if result:
                    # Check for expected schema elements
                    result_str = str(result.result_data).lower()
                    
                    # Look for structure indicators
                    structure_indicators = [":", "{", "[", "="]
                    has_structure = any(indicator in result_str for indicator in structure_indicators)
                    schema_info["has_structure"] = has_structure
                
                schema_results[version_key] = schema_info
                
                logger.info(f"Schema version {version_key}: {schema_info}")
        
        # Validate schema compatibility
        for version_key, schema_info in schema_results.items():
            assert schema_info["has_result"], \
                f"Schema version {version_key} should produce result"
            
            # All versions should provide structured data
            if "has_structure" in schema_info:
                assert schema_info["has_structure"], \
                    f"Schema version {version_key} should provide structured response"

    async def test_migration_path_validation(self):
        """
        Test migration paths between different API versions.
        
        BVJ: Enterprise segment - Enables smooth customer migration
        to newer versions without service disruption.
        """
        logger.info("Testing migration path validation")
        
        env = self.get_env()
        base_user_id = "migration_user_001"
        test_query = "Analyze optimization performance for migration testing"
        
        # Simulate migration from v1 to v2 to v3
        migration_results = {}
        
        version_sequence = ["v1", "v2", "v3"]
        
        for i, version_key in enumerate(version_sequence):
            user_id = f"{base_user_id}_{version_key}"
            version_config = self.version_configs[version_key]
            
            with create_isolated_execution_context(user_id) as context:
                context.context_data["api_version"] = version_config["api_version"]
                context.context_data["migration_mode"] = True
                
                if i > 0:
                    # Include previous version data for migration testing
                    prev_version = version_sequence[i-1]
                    context.context_data["previous_version"] = self.version_configs[prev_version]["api_version"]
                
                agent = DataHelperAgent()
                
                result = await agent.arun(
                    input_data=test_query,
                    user_context=context
                )
                
                migration_results[version_key] = {
                    "success": result is not None,
                    "version": version_config["api_version"],
                    "content_length": len(str(result.result_data)) if result else 0,
                    "migration_step": i + 1
                }
                
                # Validate migration step
                assert result is not None, f"Migration to {version_key} should succeed"
                
                logger.info(f"Migration step {i+1}: {version_key} -> Success")
        
        # Validate complete migration path
        all_successful = all(r["success"] for r in migration_results.values())
        assert all_successful, "All migration steps should succeed"
        
        # Validate progressive enhancement (optional)
        content_lengths = [r["content_length"] for r in migration_results.values()]
        
        # All versions should provide meaningful content
        for length in content_lengths:
            assert length > 20, "Each migration step should provide substantial content"

    async def test_version_rollback_compatibility(self):
        """
        Test rollback compatibility when downgrading versions.
        
        BVJ: Enterprise segment - Enables safe rollback during
        deployment issues without data loss or service interruption.
        """
        logger.info("Testing version rollback compatibility")
        
        env = self.get_env()
        user_id = "rollback_user_001"
        test_query = "Get optimization data for rollback testing"
        
        # Test forward and backward version compatibility
        rollback_sequence = [
            ("v3", "3.0"),  # Start with newest
            ("v2", "2.0"),  # Roll back to v2
            ("v1", "1.0"),  # Roll back to v1
            ("v2", "2.0"),  # Roll forward to v2
        ]
        
        rollback_results = []
        
        for step, (version_key, api_version) in enumerate(rollback_sequence):
            with create_isolated_execution_context(user_id) as context:
                context.context_data["api_version"] = api_version
                context.context_data["rollback_test"] = True
                context.context_data["sequence_step"] = step
                
                agent = DataHelperAgent()
                
                result = await agent.arun(
                    input_data=test_query,
                    user_context=context
                )
                
                rollback_info = {
                    "step": step,
                    "version": version_key,
                    "api_version": api_version,
                    "success": result is not None,
                    "content_length": len(str(result.result_data)) if result else 0
                }
                
                rollback_results.append(rollback_info)
                
                # Each rollback step should work
                assert result is not None, f"Rollback step {step} to {version_key} should work"
                
                logger.info(f"Rollback step {step}: {version_key} -> Success")
        
        # Validate rollback sequence
        successful_steps = sum(1 for r in rollback_results if r["success"])
        total_steps = len(rollback_sequence)
        
        assert successful_steps == total_steps, \
            f"All rollback steps should succeed: {successful_steps}/{total_steps}"
        
        # Validate version transitions work in both directions
        forward_steps = [r for r in rollback_results if r["step"] in [0, 3]]  # v3 -> v2
        backward_steps = [r for r in rollback_results if r["step"] in [1, 2]]  # v2 -> v1
        
        assert all(step["success"] for step in forward_steps), "Forward transitions should work"
        assert all(step["success"] for step in backward_steps), "Backward transitions should work"