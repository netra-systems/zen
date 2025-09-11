"""
Docker Test Utility - SSOT Import Compatibility Module

This module provides SSOT import compatibility by re-exporting the DockerTestUtility
from its actual location in the SSOT docker module.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure Stability
- Business Goal: Reliable test execution prevents production failures
- Value Impact: Stable Docker testing enables confident deployments
- Strategic Impact: Protects customer experience through comprehensive testing
"""

# SSOT Import: Re-export DockerTestUtility from its actual location  
from test_framework.ssot.docker import (
    DockerTestUtility,
    DockerTestEnvironmentType,
    DockerTestMetrics,
    get_docker_test_utility
)

# Export for import compatibility
__all__ = [
    'DockerTestUtility',
    'DockerTestEnvironmentType',
    'DockerTestMetrics',
    'get_docker_test_utility'
]