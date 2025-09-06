"""Comprehensive helper functions for Quality Gate Service tests - Main Index Module"""

# Import all helper functions from focused modules to maintain backwards compatibility
from netra_backend.tests.helpers.assertion_helpers import (
    assert_complete_workflow_metrics,
    assert_complete_workflow_quality,
    assert_complete_workflow_scores,
    assert_improvement_cycle_comparison,
    assert_optimization_workflow_metrics,
    assert_optimization_workflow_no_retry,
    assert_optimization_workflow_passed,
    assert_optimization_workflow_quality_indicators,
    assert_poor_content_failure,
)
from netra_backend.tests.helpers.metrics_helpers import (
    add_metrics_to_memory_limit,
    add_quality_distribution_metrics,
    add_recent_metrics_overflow,
    create_all_issues_metrics,
    create_all_penalties_metrics,
    create_all_specific_checks_metrics,
    create_borderline_action_plan_metrics,
    create_borderline_optimization_metrics,
    create_high_hallucination_metrics,
    create_prompt_adjustment_metrics,
)
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services
from netra_backend.tests.helpers.mock_helpers import (
    create_metrics_storage_error,
    setup_quality_service_with_large_cache,
    setup_quality_service_with_redis_error,
    setup_redis_mock_with_error,
    setup_redis_mock_with_large_cache,
    setup_slow_validation_mock,
    setup_threshold_error_patch,
    setup_validation_error_patch,
)
from netra_backend.tests.helpers.setup_helpers import (
    create_claims_with_evidence_content,
    create_context_with_data_source,
    create_excessive_acronyms_content,
    create_high_overlap_content,
    create_multiple_impossible_claims_content,
    create_nested_parentheses_content,
    create_very_long_sentence,
    setup_actionability_test_content,
    setup_code_block_content,
    setup_completeness_general_content,
    setup_completeness_report_content,
    setup_improved_content_after_adjustments,
    setup_large_optimization_content,
    setup_poor_content_for_improvement,
    setup_quantification_patterns_content,
    setup_relevance_test_context,
    setup_specificity_test_content,
)
from netra_backend.tests.helpers.workflow_helpers import (
    combine_optimization_content,
    create_mixed_content_batch,
    setup_complete_optimization_workflow_content,
    setup_optimization_outcomes_content,
    setup_optimization_strategy_content,
    setup_optimization_workflow_context,
)

# Re-export all functions for backwards compatibility
__all__ = [
    # Setup helpers
    'setup_large_optimization_content',
    'setup_specificity_test_content',
    'setup_actionability_test_content',
    'setup_code_block_content',
    'setup_quantification_patterns_content',
    'setup_relevance_test_context',
    'setup_completeness_report_content',
    'setup_completeness_general_content',
    'setup_poor_content_for_improvement',
    'setup_improved_content_after_adjustments',
    'create_very_long_sentence',
    'create_excessive_acronyms_content',
    'create_nested_parentheses_content',
    'create_high_overlap_content',
    'create_multiple_impossible_claims_content',
    'create_claims_with_evidence_content',
    'create_context_with_data_source',
    
    # Mock helpers
    'setup_redis_mock_with_error',
    'setup_redis_mock_with_large_cache',
    'setup_quality_service_with_redis_error',
    'setup_quality_service_with_large_cache',
    'setup_validation_error_patch',
    'setup_threshold_error_patch',
    'setup_slow_validation_mock',
    'create_metrics_storage_error',
    
    # Metrics helpers
    'create_all_penalties_metrics',
    'create_all_specific_checks_metrics',
    'create_all_issues_metrics',
    'create_prompt_adjustment_metrics',
    'create_borderline_optimization_metrics',
    'create_borderline_action_plan_metrics',
    'create_high_hallucination_metrics',
    'add_quality_distribution_metrics',
    'add_recent_metrics_overflow',
    'add_metrics_to_memory_limit',
    
    # Assertion helpers
    'assert_complete_workflow_metrics',
    'assert_complete_workflow_scores',
    'assert_complete_workflow_quality',
    'assert_optimization_workflow_passed',
    'assert_optimization_workflow_metrics',
    'assert_optimization_workflow_quality_indicators',
    'assert_optimization_workflow_no_retry',
    'assert_poor_content_failure',
    'assert_improvement_cycle_comparison',
    
    # Workflow helpers
    'create_mixed_content_batch',
    'setup_complete_optimization_workflow_content',
    'setup_optimization_strategy_content',
    'setup_optimization_outcomes_content',
    'setup_optimization_workflow_context',
    'combine_optimization_content',
]