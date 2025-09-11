"""
SSOT Logging Validation Tests - Unit Level

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Operational Excellence and Debug Capability
- Value Impact: Ensures single source of truth for logging prevents Golden Path debugging failures
- Strategic Impact: Critical for $500K+ ARR platform reliability - eliminates logging fragmentation preventing incident resolution

This test suite validates SSOT compliance for logging infrastructure.
Tests MUST FAIL initially to prove the existence of 5 competing logging configurations.

Tests validate:
1. Only ONE logging configuration exists (currently 5 exist - should FAIL)
2. No duplicate logger factories exist
3. Consistent log correlation ID formats across services  
4. Unified trace context propagation
5. No competing logging patterns

CRITICAL: These tests are designed to FAIL initially, proving SSOT violations exist.
After remediation, these same tests will PASS, validating SSOT compliance.
"""

import pytest
import logging
import sys
import os
from pathlib import Path
from typing import Set, List, Dict, Any
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestLoggingSSOTValidation(SSotBaseTestCase):
    """
    Unit tests to validate SSOT compliance for logging infrastructure.
    
    These tests MUST FAIL initially to prove 5 competing logging configurations exist.
    After SSOT remediation, these tests will PASS.
    """
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        # Clear any cached logging state
        logging.getLogger().handlers.clear()
        
        # Reset any module-level logging configuration
        if 'netra_backend.app.logging_config' in sys.modules:
            del sys.modules['netra_backend.app.logging_config']
        if 'netra_backend.app.core.logging_config' in sys.modules:
            del sys.modules['netra_backend.app.core.logging_config']
        if 'shared.logging.unified_logger_factory' in sys.modules:
            del sys.modules['shared.logging.unified_logger_factory']
        if 'analytics_service.analytics_core.utils.logging_config' in sys.modules:
            del sys.modules['analytics_service.analytics_core.utils.logging_config']
    
    def _is_ssot_compatibility_wrapper(self, file_path: Path) -> bool:
        """Check if a file is an SSOT compatibility wrapper."""
        try:
            content = file_path.read_text(encoding='utf-8')
            return 'SSOT_COMPATIBILITY_WRAPPER = True' in content
        except (UnicodeDecodeError, OSError):
            return False
    
    def test_single_logging_configuration_exists(self):
        """
        CRITICAL TEST: Validates only ONE logging configuration exists.
        
        CURRENT STATE: 5 logging configurations exist - TEST SHOULD FAIL
        AFTER SSOT REMEDIATION: Only 1 configuration - TEST WILL PASS
        
        Validates:
        - Only one logging_config.py file across all services
        - No duplicate logging initialization patterns
        - Single point of logging configuration truth
        """
        # Find all logging configuration files
        project_root = Path(__file__).parents[3]  # Go up to project root
        
        logging_config_files = []
        
        # Search for all logging_config.py files
        for config_file in project_root.rglob("**/logging_config.py"):
            # Skip test files and __pycache__
            if not any(skip in str(config_file) for skip in ['test', '__pycache__', '.git']):
                # Check if this is a compatibility wrapper
                if not self._is_ssot_compatibility_wrapper(config_file):
                    logging_config_files.append(str(config_file))
        
        # Search for logger factory files
        logger_factory_files = []
        for factory_file in project_root.rglob("**/*logger*factory*.py"):
            if not any(skip in str(factory_file) for skip in ['test', '__pycache__', '.git']):
                # Check if this is a compatibility wrapper
                if not self._is_ssot_compatibility_wrapper(factory_file):
                    logger_factory_files.append(str(factory_file))
        
        # Search for SSOT logging files
        ssot_logging_files = []
        for ssot_file in project_root.rglob("**/*logging*ssot*.py"):
            if not any(skip in str(ssot_file) for skip in ['test', '__pycache__', '.git']):
                ssot_logging_files.append(str(ssot_file))
        
        # Count actual logging configurations (excluding compatibility wrappers)
        total_actual_configs = len(logging_config_files) + len(logger_factory_files)
        
        # Count SSOT configurations (should be exactly 1)
        total_ssot_configs = len(ssot_logging_files)
        
        # Total effective configurations = actual configs + SSOT configs
        total_logging_configs = total_actual_configs + total_ssot_configs
        
        failure_message = f"""
SSOT LOGGING COMPLIANCE CHECK:

Found {total_logging_configs} total logging configurations:
- Actual Config Files: {total_actual_configs} (should be 0)
- SSOT Config Files: {total_ssot_configs} (should be exactly 1)

Active Logging Config Files ({len(logging_config_files)}):
{chr(10).join(f"  - {f}" for f in logging_config_files)}

Active Logger Factory Files ({len(logger_factory_files)}):
{chr(10).join(f"  - {f}" for f in logger_factory_files)}

SSOT Logging Files ({len(ssot_logging_files)}):
{chr(10).join(f"  - {f}" for f in ssot_logging_files)}

SSOT REQUIREMENT: Exactly 1 SSOT configuration file, 0 active configurations.
All other logging files should be compatibility wrappers with SSOT_COMPATIBILITY_WRAPPER = True.

BUSINESS IMPACT: Multiple active logging configurations prevent effective debugging
of Golden Path failures, impacting $500K+ ARR platform reliability.
"""
        
        # PASS if exactly 1 SSOT file and 0 active config files
        assert total_actual_configs == 0 and total_ssot_configs == 1, failure_message
    
    def test_no_duplicate_logger_factories(self):
        """
        Validates no duplicate logger factory patterns exist.
        
        EXPECTED TO FAIL: Multiple factory patterns currently exist
        """
        project_root = Path(__file__).parents[3]
        
        # Find all Python files with logger factory patterns
        factory_patterns = []
        
        for py_file in project_root.rglob("**/*.py"):
            if any(skip in str(py_file) for skip in ['test', '__pycache__', '.git']):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Check for various logger factory patterns
                patterns_found = []
                if 'class' in content and 'Logger' in content and 'Factory' in content:
                    patterns_found.append('class_logger_factory')
                if 'def get_logger' in content:
                    patterns_found.append('get_logger_function')
                if 'logging.getLogger' in content and 'def' in content:
                    patterns_found.append('direct_getlogger_function')
                if 'UnifiedLogger' in content and 'class' in content:
                    patterns_found.append('unified_logger_class')
                
                if patterns_found:
                    factory_patterns.append({
                        'file': str(py_file),
                        'patterns': patterns_found
                    })
                    
            except (UnicodeDecodeError, OSError):
                continue
        
        failure_message = f"""
DUPLICATE LOGGER FACTORY VIOLATION DETECTED!

Found {len(factory_patterns)} files with logger factory patterns:

{chr(10).join(f"  {item['file']}: {', '.join(item['patterns'])}" for item in factory_patterns)}

SSOT REQUIREMENT: Only ONE logger factory should exist across entire codebase.

REMEDIATION REQUIRED:
1. Consolidate all logger factory patterns into single SSOT factory
2. Remove duplicate get_logger functions
3. Eliminate service-specific logger creation patterns
4. Implement unified logger instantiation interface
"""
        
        # Should fail initially - only 1 factory pattern should exist
        assert len(factory_patterns) <= 1, failure_message
    
    def test_consistent_log_correlation_id_formats(self):
        """
        Validates consistent log correlation ID formats across all services.
        
        EXPECTED TO FAIL: Different correlation ID formats currently exist
        """
        project_root = Path(__file__).parents[3]
        
        correlation_patterns = {}
        
        # Search for correlation ID patterns in logging configurations
        for py_file in project_root.rglob("**/*logging*.py"):
            if any(skip in str(py_file) for skip in ['test', '__pycache__', '.git']):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                patterns = []
                # Look for various correlation ID patterns
                if 'request_id' in content:
                    patterns.append('request_id')
                if 'trace_id' in content:
                    patterns.append('trace_id')
                if 'correlation_id' in content:
                    patterns.append('correlation_id')
                if 'transaction_id' in content:
                    patterns.append('transaction_id')
                if 'event_id' in content:
                    patterns.append('event_id')
                    
                if patterns:
                    correlation_patterns[str(py_file)] = patterns
                    
            except (UnicodeDecodeError, OSError):
                continue
        
        # Check for inconsistent correlation ID formats
        all_patterns = set()
        for patterns in correlation_patterns.values():
            all_patterns.update(patterns)
        
        failure_message = f"""
INCONSISTENT CORRELATION ID FORMATS DETECTED!

Found {len(all_patterns)} different correlation ID patterns across {len(correlation_patterns)} files:

Patterns: {', '.join(sorted(all_patterns))}

Files with correlation patterns:
{chr(10).join(f"  {file}: {', '.join(patterns)}" for file, patterns in correlation_patterns.items())}

SSOT REQUIREMENT: All services must use identical correlation ID format.

REMEDIATION REQUIRED:
1. Standardize on single correlation ID format (recommend 'request_id')
2. Update all logging configurations to use consistent format
3. Implement unified correlation context propagation
4. Remove conflicting correlation ID patterns

BUSINESS IMPACT: Inconsistent correlation IDs prevent effective
distributed tracing and Golden Path debugging.
"""
        
        # Should fail initially - multiple correlation patterns exist
        assert len(all_patterns) <= 1, failure_message
    
    def test_unified_trace_context_propagation(self):
        """
        Validates unified trace context propagation across all logging configurations.
        
        EXPECTED TO FAIL: Multiple trace context implementations exist
        """
        project_root = Path(__file__).parents[3]
        
        trace_context_implementations = {}
        
        for py_file in project_root.rglob("**/*logging*.py"):
            if any(skip in str(py_file) for skip in ['test', '__pycache__', '.git']):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                context_patterns = []
                # Look for various trace context patterns
                if 'ContextVar' in content:
                    context_patterns.append('ContextVar')
                if 'context_processor' in content:
                    context_patterns.append('context_processor')
                if '_context' in content and 'def' in content:
                    context_patterns.append('context_function')
                if 'trace_context' in content:
                    context_patterns.append('trace_context')
                if 'request_context' in content:
                    context_patterns.append('request_context')
                    
                if context_patterns:
                    trace_context_implementations[str(py_file)] = context_patterns
                    
            except (UnicodeDecodeError, OSError):
                continue
        
        failure_message = f"""
MULTIPLE TRACE CONTEXT IMPLEMENTATIONS DETECTED!

Found trace context implementations in {len(trace_context_implementations)} files:

{chr(10).join(f"  {file}: {', '.join(patterns)}" for file, patterns in trace_context_implementations.items())}

SSOT REQUIREMENT: Only ONE trace context implementation should exist.

REMEDIATION REQUIRED:
1. Consolidate all trace context implementations into single SSOT module
2. Remove duplicate context propagation patterns
3. Implement unified trace context interface
4. Ensure consistent context propagation across all services

BUSINESS IMPACT: Multiple trace context implementations create
gaps in distributed tracing, preventing effective Golden Path debugging.
"""
        
        # Should fail initially - only 1 trace context implementation should exist
        assert len(trace_context_implementations) <= 1, failure_message
    
    def test_no_competing_logging_patterns(self):
        """
        Validates no competing logging initialization patterns exist.
        
        EXPECTED TO FAIL: Multiple logging initialization patterns currently exist
        """
        project_root = Path(__file__).parents[3]
        
        logging_patterns = {
            'basicConfig': [],
            'logging_getLogger': [],
            'custom_logger_class': [],
            'structlog_configure': [],
            'logger_factory_call': []
        }
        
        for py_file in project_root.rglob("**/*.py"):
            if any(skip in str(py_file) for skip in ['test', '__pycache__', '.git']):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                file_path = str(py_file)
                
                if 'logging.basicConfig' in content:
                    logging_patterns['basicConfig'].append(file_path)
                if 'logging.getLogger(' in content:
                    logging_patterns['logging_getLogger'].append(file_path)
                if 'class' in content and 'Logger' in content and 'def __init__' in content:
                    logging_patterns['custom_logger_class'].append(file_path)
                if 'structlog.configure' in content:
                    logging_patterns['structlog_configure'].append(file_path)
                if 'get_logger(' in content and 'def' not in content:
                    logging_patterns['logger_factory_call'].append(file_path)
                    
            except (UnicodeDecodeError, OSError):
                continue
        
        # Count total competing patterns
        total_patterns = sum(len(files) for files in logging_patterns.values())
        
        failure_message = f"""
COMPETING LOGGING PATTERNS DETECTED!

Found {total_patterns} instances of competing logging patterns:

basicConfig calls ({len(logging_patterns['basicConfig'])}):
{chr(10).join(f"  - {f}" for f in logging_patterns['basicConfig'][:5])}
{'  ... and more' if len(logging_patterns['basicConfig']) > 5 else ''}

logging.getLogger calls ({len(logging_patterns['logging_getLogger'])}):
{chr(10).join(f"  - {f}" for f in logging_patterns['logging_getLogger'][:5])}
{'  ... and more' if len(logging_patterns['logging_getLogger']) > 5 else ''}

Custom logger classes ({len(logging_patterns['custom_logger_class'])}):
{chr(10).join(f"  - {f}" for f in logging_patterns['custom_logger_class'][:5])}
{'  ... and more' if len(logging_patterns['custom_logger_class']) > 5 else ''}

structlog.configure calls ({len(logging_patterns['structlog_configure'])}):
{chr(10).join(f"  - {f}" for f in logging_patterns['structlog_configure'][:5])}
{'  ... and more' if len(logging_patterns['structlog_configure']) > 5 else ''}

Logger factory calls ({len(logging_patterns['logger_factory_call'])}):
{chr(10).join(f"  - {f}" for f in logging_patterns['logger_factory_call'][:5])}
{'  ... and more' if len(logging_patterns['logger_factory_call']) > 5 else ''}

SSOT REQUIREMENT: All logging should use unified SSOT pattern.

REMEDIATION REQUIRED:
1. Replace all logging.basicConfig with SSOT factory
2. Replace all logging.getLogger with SSOT factory
3. Remove custom logger classes (use SSOT)
4. Consolidate structlog.configure calls
5. Implement single logger factory interface

BUSINESS IMPACT: Competing logging patterns create inconsistent
log formats and missing correlation, preventing Golden Path debugging.
"""
        
        # Should fail initially - competing patterns exist
        # Allow minimal patterns for SSOT implementation
        assert total_patterns <= 5, failure_message
    
    def test_logging_environment_configuration_consistency(self):
        """
        Validates consistent environment-based logging configuration.
        
        EXPECTED TO FAIL: Different environment handling patterns exist
        """
        project_root = Path(__file__).parents[3]
        
        env_patterns = {}
        
        for py_file in project_root.rglob("**/*logging*.py"):
            if any(skip in str(py_file) for skip in ['test', '__pycache__', '.git']):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                patterns = []
                # Look for environment configuration patterns
                if 'os.environ' in content:
                    patterns.append('os_environ')
                if 'get_env()' in content:
                    patterns.append('get_env_function')
                if 'IsolatedEnvironment' in content:
                    patterns.append('isolated_environment')
                if 'ENVIRONMENT' in content and 'get' in content:
                    patterns.append('environment_var_access')
                if 'LOG_LEVEL' in content:
                    patterns.append('log_level_env')
                    
                if patterns:
                    env_patterns[str(py_file)] = patterns
                    
            except (UnicodeDecodeError, OSError):
                continue
        
        # Check for inconsistent environment access patterns
        all_env_patterns = set()
        for patterns in env_patterns.values():
            all_env_patterns.update(patterns)
        
        failure_message = f"""
INCONSISTENT ENVIRONMENT CONFIGURATION DETECTED!

Found {len(all_env_patterns)} different environment access patterns across {len(env_patterns)} files:

Environment Patterns: {', '.join(sorted(all_env_patterns))}

Files with environment patterns:
{chr(10).join(f"  {file}: {', '.join(patterns)}" for file, patterns in env_patterns.items())}

SSOT REQUIREMENT: All logging configurations must use consistent environment access.

REMEDIATION REQUIRED:
1. Standardize environment access through IsolatedEnvironment only
2. Remove direct os.environ access from logging configs
3. Implement unified environment-based logging level configuration
4. Consolidate LOG_LEVEL handling patterns

BUSINESS IMPACT: Inconsistent environment handling causes logging
configuration failures in different deployment environments.
"""
        
        # Should fail initially - multiple environment access patterns exist
        # SSOT should use only IsolatedEnvironment
        assert 'os_environ' not in all_env_patterns, failure_message
        assert len(all_env_patterns) <= 2, failure_message  # Allow isolated_environment + one other


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])