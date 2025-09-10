"""
GCP Error Handling Integration Tests Package

This package contains comprehensive integration tests for GCP error message
creation and handling functionality. Tests validate the complete pipeline
from GCP Cloud Run log ingestion to structured error message processing.

Business Value:
- Validates $500K+ ARR platform error handling capabilities
- Ensures rapid incident detection and response
- Tests error correlation and automated alerting systems
- Validates compliance with operational SLAs

Test Coverage:
- Basic error message extraction from GCP logs
- Error type identification and classification  
- Error severity mapping and prioritization
- Error message formatting and structure validation
- Error timestamp and service identification
- Error correlation and grouping logic
- Error message persistence to database
- Error message retrieval and querying
- Error message duplicate detection and handling
- Error message cleanup and retention policies

All tests follow SSOT patterns and use real services for integration validation.
"""

__all__ = [
    "test_basic_error_message_creation"
]