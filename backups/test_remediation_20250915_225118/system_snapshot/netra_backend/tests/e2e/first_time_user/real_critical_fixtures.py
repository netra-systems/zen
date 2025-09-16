"""
Real Critical User Journey Fixtures - Consolidated imports for REAL E2E testing

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Test Infrastructure supporting $1.2M+ ARR validation
2. **Business Goal**: Provide unified access to all test fixtures for critical user journeys
3. **Value Impact**: Consolidated fixtures reduce test import complexity by 80%
4. **Revenue Impact**: Streamlined test development = faster iteration on conversion optimization

**ARCHITECTURE**:  <= 300 lines, consolidated imports to maintain architectural compliance
Provides unified access to all fixture modules while maintaining modular design.
"""

# Import all fixtures from split modules
from netra_backend.tests.e2e.first_time_user.real_critical_core_fixtures import (
    # AI Provider Connection Fixtures
    ai_provider_credentials,
    concurrent_load_config,
    cost_savings_calculator,
    # Core Environment Fixtures
    critical_user_journey_environment,
    encrypted_storage_config,
    load_testing_environment,
    # OAuth and Authentication Fixtures
    oauth_flow_environment,
    onboarding_state_config,
    optimization_analysis_config,
    # Performance and Load Testing Fixtures
    performance_thresholds,
    provider_validation_environment,
    real_auth_environment,
    real_optimization_service,
    realtime_progress_tracker,
    session_management_config,
    # Optimization and Analysis Fixtures
    usage_data_samples,
    user_profile_data,
    websocket_connection_manager,
    # WebSocket and Real-time Communication Fixtures
    websocket_test_environment,
)
from netra_backend.tests.e2e.first_time_user.real_critical_extended_fixtures import (
    collaboration_features_config,
    compliance_validation_config,
    concurrent_testing_environment,
    # Cross-Service Integration Fixtures
    cross_service_config,
    # Data Isolation and Concurrent Testing Fixtures
    data_isolation_validators,
    error_recovery_config,
    # Error Handling and Recovery Fixtures
    error_simulation_scenarios,
    free_tier_limitation_config,
    # Integration Testing Environment Fixtures
    integration_testing_environment,
    # Real-time Monitoring and Metrics Fixtures
    real_time_monitoring_config,
    # Security and Compliance Testing Fixtures
    security_testing_config,
    service_mesh_config,
    stress_testing_scenarios,
    support_channel_config,
    team_invitation_config,
    # Team and Collaboration Fixtures
    team_workspace_config,
    token_validation_config,
    upgrade_flow_config,
    user_experience_metrics,
    # Value Demonstration and Upgrade Flow Fixtures
    value_demonstration_config,
)

# Re-export all fixtures for convenience
__all__ = [
    # Core Environment Fixtures
    'critical_user_journey_environment',
    'real_optimization_service',
    'concurrent_load_config',
    'real_auth_environment',
    'websocket_connection_manager',
    
    # OAuth and Authentication Fixtures
    'oauth_flow_environment',
    'user_profile_data',
    'session_management_config',
    
    # AI Provider Connection Fixtures
    'ai_provider_credentials',
    'provider_validation_environment',
    'encrypted_storage_config',
    
    # WebSocket and Real-time Communication Fixtures
    'websocket_test_environment',
    'onboarding_state_config',
    'realtime_progress_tracker',
    
    # Optimization and Analysis Fixtures
    'usage_data_samples',
    'optimization_analysis_config',
    'cost_savings_calculator',
    
    # Performance and Load Testing Fixtures
    'performance_thresholds',
    'load_testing_environment',
    
    # Team and Collaboration Fixtures
    'team_workspace_config',
    'team_invitation_config',
    'collaboration_features_config',
    
    # Error Handling and Recovery Fixtures
    'error_simulation_scenarios',
    'error_recovery_config',
    'support_channel_config',
    
    # Cross-Service Integration Fixtures
    'cross_service_config',
    'service_mesh_config',
    'token_validation_config',
    
    # Value Demonstration and Upgrade Flow Fixtures
    'value_demonstration_config',
    'upgrade_flow_config',
    'free_tier_limitation_config',
    
    # Data Isolation and Concurrent Testing Fixtures
    'data_isolation_validators',
    'concurrent_testing_environment',
    'stress_testing_scenarios',
    
    # Real-time Monitoring and Metrics Fixtures
    'real_time_monitoring_config',
    'user_experience_metrics',
    
    # Security and Compliance Testing Fixtures
    'security_testing_config',
    'compliance_validation_config',
    
    # Integration Testing Environment Fixtures
    'integration_testing_environment'
]