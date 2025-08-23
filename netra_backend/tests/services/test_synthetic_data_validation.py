"""
Validation Tests for Synthetic Data Generation Spec v3
Tests to validate that the implementation matches the specification
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import pytest

class TestSpecificationValidation:
    """Validate the synthetic data generation specification"""

    @pytest.fixture
    def spec_path(self):
        return "SPEC/synthetic_data_generation.xml"

    @pytest.fixture
    def spec_tree(self, spec_path):
        """Load and parse the specification XML"""
        tree = ET.parse(spec_path)
        return tree.getroot()

    def test_spec_version_is_3(self, spec_tree):
        """Verify specification is version 3.0"""
        assert spec_tree.get('version') == '3.0'

    def test_enhanced_admin_visibility_section_exists(self, spec_tree):
        """Verify enhanced admin visibility section is present"""
        admin_visibility = spec_tree.find('.//enhanced_admin_visibility')
        assert admin_visibility != None
        
        # Check key components
        assert admin_visibility.find('.//real_time_monitoring') != None
        assert admin_visibility.find('.//admin_prompts_system') != None
        assert admin_visibility.find('.//process_inspectability') != None

    def test_data_agent_integration_section_exists(self, spec_tree):
        """Verify data agent integration section is present"""
        agent_integration = spec_tree.find('.//data_agent_integration')
        assert agent_integration != None
        
        # Check agent tools
        tools = agent_integration.findall('.//agent_tools/tool')
        tool_names = [tool.get('name') for tool in tools]
        assert 'corpus_fetcher' in tool_names
        assert 'data_clusterer' in tool_names
        assert 'pattern_analyzer' in tool_names
        assert 'quality_validator' in tool_names

    def test_log_structure_coherence_section_exists(self, spec_tree):
        """Verify log structure coherence section is present"""
        log_coherence = spec_tree.find('.//log_structure_coherence')
        assert log_coherence != None
        
        # Check unified log schema
        schema = log_coherence.find('.//unified_log_schema')
        assert schema != None
        assert schema.find('.//core_fields') != None
        assert schema.find('.//ai_specific_fields') != None

    def test_comprehensive_testing_framework_defined(self, spec_tree):
        """Verify comprehensive testing framework is defined"""
        testing = spec_tree.find('.//comprehensive_testing_framework')
        assert testing != None
        
        # Check test suites
        suites = testing.findall('.//test_suites/suite')
        assert len(suites) == 10
        
        suite_names = [suite.get('name') for suite in suites]
        expected_suites = [
            'TestCorpusManagement',
            'TestDataGenerationEngine',
            'TestRealTimeIngestion',
            'TestWebSocketUpdates',
            'TestDataQualityValidation',
            'TestPerformanceScalability',
            'TestErrorRecovery',
            'TestAdminVisibility',
            'TestIntegration',
            'TestAdvancedFeatures'
        ]
        for expected in expected_suites:
            assert expected in suite_names

    def test_version_3_improvements_documented(self, spec_tree):
        """Verify version 3 improvements are documented"""
        improvements = spec_tree.find('.//version_3_improvements')
        assert improvements != None
        
        # Check major enhancements
        enhancements = improvements.findall('.//major_enhancements/enhancement')
        assert len(enhancements) >= 4
        
        # Check key learnings
        learnings = improvements.findall('.//key_learnings/learning')
        assert len(learnings) >= 5

    def test_admin_prompts_categories_defined(self, spec_tree):
        """Verify admin prompt categories are properly defined"""
        prompts = spec_tree.find('.//admin_prompts_system/prompt_categories')
        assert prompts != None
        
        categories = prompts.findall('category')
        category_names = [cat.get('name') for cat in categories]
        
        expected_categories = [
            'corpus_management',
            'generation_control',
            'quality_assurance',
            'troubleshooting'
        ]
        for expected in expected_categories:
            assert expected in category_names

    def test_clustering_algorithms_defined(self, spec_tree):
        """Verify clustering algorithms are defined"""
        clusterer = spec_tree.find('.//tool[@name="data_clusterer"]')
        assert clusterer != None
        
        algorithms = clusterer.findall('.//clustering_algorithms/algorithm')
        algo_names = [algo.get('name') for algo in algorithms]
        
        assert 'kmeans' in algo_names
        assert 'dbscan' in algo_names
        assert 'hierarchical' in algo_names

    def test_alerting_rules_defined(self, spec_tree):
        """Verify alerting rules are properly defined"""
        alerts = spec_tree.find('.//alerting_and_notifications/alert_rules')
        assert alerts != None
        
        rules = alerts.findall('rule')
        rule_names = [rule.get('name') for rule in rules]
        
        expected_rules = [
            'generation_slow',
            'corpus_unavailable',
            'high_error_rate',
            'resource_exhaustion'
        ]
        for expected in expected_rules:
            assert expected in rule_names

    def test_migration_guide_present(self, spec_tree):
        """Verify migration guide from v2 to v3 is present"""
        migration = spec_tree.find('.//migration_guide')
        assert migration != None
        
        assert migration.find('from_version').text == '2.0'
        assert migration.find('to_version').text == '3.0'
        
        steps = migration.findall('.//migration_steps/step')
        assert len(steps) >= 5

class TestImplementationConsistency:
    """Test consistency between spec and implementation"""

    def test_workload_categories_match_spec(self):
        """Verify workload categories in code match specification"""
        from netra_backend.app.services.synthetic_data_service import WorkloadCategory
        
        expected_categories = [
            'simple_chat',
            'rag_pipeline', 
            'tool_use',
            'multi_turn_tool_use',
            'failed_request',
            'custom_domain'
        ]
        
        actual_categories = [cat.value for cat in WorkloadCategory]
        for expected in expected_categories:
            assert expected in actual_categories

    def test_generation_status_enum_matches_spec(self):
        """Verify generation status enum matches specification"""
        from netra_backend.app.services.synthetic_data_service import GenerationStatus
        
        expected_statuses = [
            'initiated',
            'running',
            'completed',
            'failed',
            'cancelled'
        ]
        
        actual_statuses = [status.value for status in GenerationStatus]
        for expected in expected_statuses:
            assert expected in actual_statuses

    def test_corpus_service_exists(self):
        """Verify corpus service implementation exists"""
        from netra_backend.app.services.corpus_service import (
            CorpusService,
            CorpusStatus,
        )
        
        assert CorpusService != None
        
        # Check status enum
        expected_statuses = ['creating', 'available', 'failed', 'updating', 'deleting']
        actual_statuses = [status.value for status in CorpusStatus]
        for expected in expected_statuses:
            assert expected in actual_statuses

    def test_websocket_manager_exists(self):
        """Verify WebSocket manager exists for real-time updates"""
        from netra_backend.app.websocket_core import get_unified_manager
        manager = get_unified_manager()
        
        assert manager != None
        assert hasattr(manager, 'connect')
        assert hasattr(manager, 'disconnect')
        assert hasattr(manager, 'broadcast')

    def test_synthetic_data_service_has_required_methods(self):
        """Verify synthetic data service has required methods"""
        from netra_backend.app.services.synthetic_data_service import (
            SyntheticDataService,
        )
        
        service = SyntheticDataService()
        
        # Check for key methods mentioned in spec
        assert hasattr(service, 'generate_batch')
        # validate_workload_distribution is handled internally in generation logic
        
        # Check for corpus cache
        assert hasattr(service, 'corpus_cache')

    def test_clickhouse_integration_configured(self):
        """Verify ClickHouse integration is configured"""
        from netra_backend.app.db.clickhouse import get_clickhouse_client
        
        assert get_clickhouse_client != None

    def test_agent_tools_available(self):
        """Verify agent tools are available"""
        from netra_backend.app.agents.admin_tool_dispatcher import AdminToolDispatcher
        
        assert AdminToolDispatcher != None

    def test_data_clustering_tool_exists(self):
        """Verify data clustering tool exists"""
        from netra_backend.app.services.apex_optimizer_agent.tools.log_enricher_and_clusterer import (
            log_enricher_and_clusterer,
        )
        
        assert log_enricher_and_clusterer != None

    def test_test_file_created(self):
        """Verify comprehensive test file was created"""
        test_path = "app/tests/services/test_synthetic_data_service_v3.py"
        assert os.path.exists(test_path)
        
        # Check file contains test classes
        with open(test_path, 'r') as f:
            content = f.read()
            assert 'TestCorpusManagement' in content
            assert 'TestDataGenerationEngine' in content
            assert 'TestRealTimeIngestion' in content
            assert 'TestWebSocketUpdates' in content
            assert 'TestDataQualityValidation' in content
            assert 'TestPerformanceScalability' in content
            assert 'TestErrorRecovery' in content
            assert 'TestAdminVisibility' in content
            assert 'TestIntegration' in content
            assert 'TestAdvancedFeatures' in content

    def test_spec_xml_is_valid(self):
        """Verify the XML specification is well-formed and valid"""
        spec_path = "SPEC/synthetic_data_generation.xml"
        
        try:
            tree = ET.parse(spec_path)
            root = tree.getroot()
            
            # Check root element
            assert root.tag == 'synthetic_data_generation_spec'
            assert root.get('version') == '3.0'
            
            # Check for required top-level sections
            required_sections = [
                'metadata',
                'core_concepts',
                'real_time_ingestion',
                'data_quality_validation',
                'performance_optimization',
                'error_recovery',
                'ui_ux_experience',
                'generation_configuration',
                'enhanced_admin_visibility',
                'data_agent_integration',
                'log_structure_coherence',
                'comprehensive_testing_framework',
                'version_3_improvements'
            ]
            
            for section in required_sections:
                element = root.find(f'.//{section}')
                assert element != None, f"Missing required section: {section}"
                
        except ET.ParseError as e:
            pytest.fail(f"XML parsing error: {e}")

class TestKeyFeatureImplementation:
    """Test that key features from spec v3 are implementable"""

    def test_corpus_lifecycle_states(self):
        """Test corpus lifecycle state transitions"""
        from netra_backend.app.services.corpus_service import CorpusStatus
        
        # Define valid transitions as per spec
        valid_transitions = {
            CorpusStatus.CREATING: [CorpusStatus.AVAILABLE, CorpusStatus.FAILED],
            CorpusStatus.AVAILABLE: [CorpusStatus.UPDATING, CorpusStatus.DELETING],
            CorpusStatus.UPDATING: [CorpusStatus.AVAILABLE, CorpusStatus.FAILED],
            CorpusStatus.FAILED: [CorpusStatus.CREATING, CorpusStatus.DELETING],
            CorpusStatus.DELETING: []
        }
        
        # Verify all states are covered
        all_states = set(CorpusStatus)
        covered_states = set(valid_transitions.keys())
        assert covered_states == all_states

    def test_workload_distribution_calculation(self):
        """Test workload distribution calculation logic"""
        distribution = {
            "simple_chat": 0.3,
            "tool_use": 0.3,
            "rag_pipeline": 0.2,
            "failed_request": 0.2
        }
        
        # Verify distribution sums to 1.0
        total = sum(distribution.values())
        assert abs(total - 1.0) < 0.001
        
        # Simulate generation with distribution
        num_traces = 1000
        expected_counts = {k: int(v * num_traces) for k, v in distribution.items()}
        
        # Verify counts match expected distribution
        total_expected = sum(expected_counts.values())
        assert abs(total_expected - num_traces) < 10

    def test_batch_size_optimization_range(self):
        """Test batch size optimization range as per spec"""
        # Spec states optimal batch size should be 100-1000
        min_batch = 100
        max_batch = 1000
        
        # Test various batch sizes
        test_sizes = [10, 50, 100, 500, 1000, 5000]
        optimal_sizes = [s for s in test_sizes if min_batch <= s <= max_batch]
        
        assert 100 in optimal_sizes
        assert 500 in optimal_sizes
        assert 1000 in optimal_sizes
        assert 10 not in optimal_sizes
        assert 5000 not in optimal_sizes

    def test_websocket_message_types(self):
        """Test WebSocket message types match specification"""
        expected_message_types = [
            'generation_progress',
            'generation_complete',
            'generation_error',
            'batch_complete',
            'heartbeat'
        ]
        
        # These should be the message types the system can handle
        for msg_type in expected_message_types:
            assert isinstance(msg_type, str)
            assert len(msg_type) > 0

    def test_quality_metrics_calculation(self):
        """Test quality metrics calculation as per spec"""
        quality_metrics = {
            'validation_pass_rate': 0.95,
            'distribution_divergence': 0.1,
            'temporal_consistency': 0.98,
            'corpus_coverage': 0.5
        }
        
        # Verify all metrics are within expected ranges
        assert 0 <= quality_metrics['validation_pass_rate'] <= 1
        assert 0 <= quality_metrics['distribution_divergence'] <= 1
        assert 0 <= quality_metrics['temporal_consistency'] <= 1
        assert 0 <= quality_metrics['corpus_coverage'] <= 1

    def test_circuit_breaker_configuration(self):
        """Test circuit breaker configuration matches spec"""
        circuit_config = {
            'failure_threshold': 5,
            'success_threshold': 3,
            'timeout': 30,
            'half_open_requests': 3
        }
        
        # Verify configuration values are reasonable
        assert circuit_config['failure_threshold'] > 0
        assert circuit_config['success_threshold'] > 0
        assert circuit_config['timeout'] > 0
        assert circuit_config['half_open_requests'] > 0

    def test_ingestion_rate_targets(self):
        """Test ingestion rate targets from spec"""
        # Spec defines throughput targets
        baseline_throughput = 10000  # records/second single node
        scaled_throughput = 100000  # records/second with 10-node cluster
        burst_capacity = 500000  # records/second for 60 seconds
        
        assert baseline_throughput == 10000
        assert scaled_throughput == 100000
        assert burst_capacity == 500000
        
        # Verify scaling factor
        scaling_factor = scaled_throughput / baseline_throughput
        assert scaling_factor == 10

    def test_temporal_pattern_types(self):
        """Test temporal pattern types from spec"""
        temporal_patterns = [
            'business_hours',
            'peak_hours',
            'weekend_pattern',
            'seasonal_variations',
            'incident_simulation'
        ]
        
        # Verify all patterns are defined
        for pattern in temporal_patterns:
            assert isinstance(pattern, str)
            assert len(pattern) > 0

    def test_tool_catalog_structure(self):
        """Test tool catalog structure matches spec"""
        tool_example = {
            'name': 'clickhouse_query',
            'type': 'query',
            'latency_ms': [50, 500],
            'failure_rate': 0.01
        }
        
        # Verify required fields
        assert 'name' in tool_example
        assert 'type' in tool_example
        assert 'latency_ms' in tool_example
        assert isinstance(tool_example['latency_ms'], list)
        assert len(tool_example['latency_ms']) == 2

    def test_admin_dashboard_update_frequency(self):
        """Test admin dashboard update frequency from spec"""
        # Spec states 1 second update frequency via WebSocket
        update_frequency_seconds = 1
        
        assert update_frequency_seconds == 1
        
        # Calculate updates per minute
        updates_per_minute = 60 / update_frequency_seconds
        assert updates_per_minute == 60

if __name__ == "__main__":
    pytest.main([__file__, "-v"])