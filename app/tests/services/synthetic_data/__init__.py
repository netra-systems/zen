"""
Test suite for SyntheticDataService

This module contains comprehensive tests split into focused test files:
- test_initialization.py: Service initialization and workload type selection
- test_tool_invocations.py: Tool invocation generation tests  
- test_content_generation.py: Content, timestamp, and metrics generation
- test_data_operations.py: Single record and batch generation
- test_table_operations.py: ClickHouse table operations
- test_main_workflow.py: Main generation workflow and worker
- test_job_management.py: Job management and preview generation
- test_advanced_generation.py: Advanced generation methods
- test_ingestion.py: Data ingestion with retry and transformation
- test_validation.py: Data validation and quality metrics
- test_error_handling.py: Error handling and circuit breaker
"""