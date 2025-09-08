"""
SSOT Pytest Plugin for No-Docker Mode

This pytest plugin automatically applies no-docker mode detection to integration tests,
ensuring they skip gracefully when external services are unavailable.

Business Value: Platform/Internal - Enables seamless testing without Docker dependencies
"""

import logging
import re
from typing import List, Set, Dict, Any
from pathlib import Path

import pytest
from _pytest.config import Config
from _pytest.nodes import Item
from _pytest.python import Function

from test_framework.ssot.no_docker_mode_detector import get_no_docker_detector

logger = logging.getLogger(__name__)


class NoDocketModePlugin:
    """Pytest plugin that manages no-docker mode for integration tests."""
    
    def __init__(self, config: Config):
        self.config = config
        self.no_docker_detector = get_no_docker_detector()
        
        # Service dependency patterns for different test types
        self.service_patterns = {
            # Database integration tests
            r'.*clickhouse.*': ['clickhouse'],
            r'.*postgresql.*': ['postgresql'],
            r'.*postgres.*': ['postgresql'],
            r'.*redis.*': ['redis'],
            r'.*database.*': ['postgresql'],
            
            # Service integration tests  
            r'.*backend.*integration.*': ['backend'],
            r'.*auth.*integration.*': ['auth'],
            r'.*websocket.*integration.*': ['backend', 'websocket'],
            
            # Multi-service integration tests
            r'.*test_.*_integration.*': ['backend', 'postgresql'],  # Generic integration
            r'.*integration.*comprehensive.*': ['backend', 'auth', 'postgresql'],
            
            # Specific service combinations
            r'.*test_database_.*integration.*': ['postgresql', 'clickhouse'],
            r'.*test_.*service.*integration.*': ['backend', 'auth'],
        }
        
        # Test file patterns that should be checked for service dependencies
        self.integration_test_patterns = [
            r'.*/integration/.*\.py',
            r'.*test.*integration.*\.py',
            r'.*/tests/.*integration.*\.py',
        ]
        
        # Patterns for tests that should never be skipped (standalone integration tests)
        self.standalone_patterns = [
            r'.*test.*unit.*',
            r'.*test.*mock.*',
            r'.*test.*fake.*',
            r'.*test.*config.*validation.*',
            r'.*test.*startup.*',
        ]
    
    def pytest_collection_modifyitems(self, config: Config, items: List[Item]) -> None:
        """Modify test collection to add skip markers for no-docker mode."""
        if not self.no_docker_detector.is_no_docker_mode():
            return
            
        logger.info("No-Docker mode: Analyzing integration tests for service dependencies")
        
        skipped_count = 0
        analyzed_count = 0
        
        for item in items:
            if isinstance(item, Function):
                # Check if this is an integration test
                if self._is_integration_test(item):
                    analyzed_count += 1
                    
                    # Skip if it's a standalone test
                    if self._is_standalone_test(item):
                        continue
                    
                    # Determine required services
                    required_services = self._get_required_services(item)
                    
                    if required_services:
                        # Check if services are available
                        skip_msg = self.no_docker_detector.should_skip_service_dependent_test(required_services)
                        
                        if skip_msg:
                            # Add skip marker
                            item.add_marker(pytest.mark.skip(reason=skip_msg))
                            skipped_count += 1
                            logger.debug(f"Marked for skip: {item.name} (services: {required_services})")
        
        if analyzed_count > 0:
            logger.info(f"No-Docker mode: Analyzed {analyzed_count} integration tests, marked {skipped_count} for skip")
    
    def _is_integration_test(self, item: Function) -> bool:
        """Check if test item is an integration test."""
        test_file = str(item.fspath)
        test_name = item.name
        
        # Check file path patterns
        for pattern in self.integration_test_patterns:
            if re.search(pattern, test_file, re.IGNORECASE):
                return True
        
        # Check test name patterns
        if 'integration' in test_name.lower():
            return True
            
        return False
    
    def _is_standalone_test(self, item: Function) -> bool:
        """Check if test is standalone (doesn't require external services)."""
        test_file = str(item.fspath)
        test_name = item.name
        
        # Check standalone patterns
        for pattern in self.standalone_patterns:
            if re.search(pattern, test_file, re.IGNORECASE) or re.search(pattern, test_name, re.IGNORECASE):
                return True
        
        return False
    
    def _get_required_services(self, item: Function) -> List[str]:
        """Determine required services for a test item."""
        test_file = str(item.fspath)
        test_name = item.name
        
        required_services = set()
        
        # Check patterns for service dependencies
        for pattern, services in self.service_patterns.items():
            if re.search(pattern, test_file, re.IGNORECASE) or re.search(pattern, test_name, re.IGNORECASE):
                required_services.update(services)
        
        # Check for service requirements in decorators or markers
        service_requirements = self._extract_service_requirements_from_markers(item)
        if service_requirements:
            required_services.update(service_requirements)
        
        return list(required_services)
    
    def _extract_service_requirements_from_markers(self, item: Function) -> List[str]:
        """Extract service requirements from test markers."""
        services = []
        
        # Check for custom markers
        for marker in item.iter_markers():
            if marker.name.startswith('requires_'):
                service_name = marker.name.replace('requires_', '')
                if service_name in ['backend', 'auth', 'postgresql', 'clickhouse', 'redis', 'websocket']:
                    services.append(service_name)
            
            # Check for service dependency decorator metadata
            elif marker.name == 'service_requirements':
                if hasattr(marker, 'args') and marker.args:
                    services.extend(marker.args)
        
        # Check function attributes for service requirements  
        if hasattr(item.function, '_service_requirements'):
            from test_framework.service_dependencies import ServiceRequirement
            reqs = item.function._service_requirements
            if isinstance(reqs, list):
                for req in reqs:
                    if isinstance(req, ServiceRequirement):
                        services.append(req.service.value)
        
        return services


def pytest_configure(config: Config) -> None:
    """Configure the no-docker mode plugin."""
    # Register custom markers
    config.addinivalue_line(
        "markers", 
        "requires_backend: Test requires Backend service"
    )
    config.addinivalue_line(
        "markers",
        "requires_auth: Test requires Auth service" 
    )
    config.addinivalue_line(
        "markers",
        "requires_postgresql: Test requires PostgreSQL database"
    )
    config.addinivalue_line(
        "markers",
        "requires_clickhouse: Test requires ClickHouse database"
    )
    config.addinivalue_line(
        "markers",
        "requires_redis: Test requires Redis database"
    )
    config.addinivalue_line(
        "markers",
        "requires_websocket: Test requires WebSocket service"
    )
    config.addinivalue_line(
        "markers",
        "service_requirements: Test has specific service requirements"
    )
    
    # Register the plugin instance
    if get_no_docker_detector().is_no_docker_mode():
        plugin = NoDocketModePlugin(config)
        config.pluginmanager.register(plugin, "no_docker_mode")


def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption(
        "--analyze-service-deps",
        action="store_true",
        default=False,
        help="Analyze service dependencies without running tests"
    )


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Log no-docker mode status at session start."""
    detector = get_no_docker_detector()
    if detector.is_no_docker_mode():
        logger.info("=" * 60)
        logger.info("NO-DOCKER MODE ACTIVE")
        logger.info("Integration tests will skip if services unavailable")
        logger.info("=" * 60)


def pytest_sessionfinish(session, exitstatus):
    """Clean up after test session."""
    # Clear caches
    try:
        from test_framework.ssot.no_docker_mode_detector import clear_no_docker_cache
        clear_no_docker_cache()
    except ImportError:
        pass