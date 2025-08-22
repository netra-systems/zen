#!/usr/bin/env python
"""
Test Index Manager - Centralized test indexing and management
Maintains comprehensive test catalog and relationships
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


class TestIndexManager:
    """Manages test indexes and relationships"""
    
    def __init__(self):
        self.test_catalog = self._initialize_catalog()
        self.test_relationships = self._initialize_relationships()
        self.last_update = datetime.now().isoformat()
    
    def _initialize_catalog(self) -> Dict:
        """Initialize comprehensive test catalog"""
        return {
            "backend": {
                "unit": self._get_backend_unit_tests(),
                "integration": self._get_backend_integration_tests(),
                "critical": self._get_backend_critical_tests(),
                "smoke": self._get_backend_smoke_tests(),
                "agents": self._get_backend_agent_tests()
            },
            "frontend": {
                "unit": self._get_frontend_unit_tests(),
                "integration": self._get_frontend_integration_tests(),
                "components": self._get_frontend_component_tests(),
                "hooks": self._get_frontend_hook_tests(),
                "startup": self._get_frontend_startup_tests()
            },
            "e2e": {
                "cypress": self._get_cypress_tests(),
                "real_llm": self._get_real_llm_tests(),
                "mock": self._get_mock_e2e_tests()
            }
        }
    
    def _initialize_relationships(self) -> Dict:
        """Initialize test relationships and dependencies"""
        return {
            "dependencies": {
                "integration": ["unit", "smoke"],
                "e2e": ["integration", "unit"],
                "real_e2e": ["e2e", "integration"],
                "comprehensive": ["all"]
            },
            "coverage_mapping": {
                "auth": ["app/auth", "app/auth_integration"],
                "websocket": ["app/websocket", "frontend/hooks/useWebSocket"],
                "database": ["app/db", "app/repositories"],
                "agents": ["app/agents", "app/llm"]
            }
        }
    
    def _get_backend_unit_tests(self) -> List[str]:
        """Get backend unit test modules"""
        return [
            "test_auth_middleware",
            "test_websocket_manager",
            "test_database_operations",
            "test_llm_client",
            "test_agent_base",
            "test_repositories",
            "test_schemas",
            "test_core_utilities"
        ]
    
    def _get_backend_integration_tests(self) -> List[str]:
        """Get backend integration test modules"""
        return [
            "test_auth_flow",
            "test_websocket_integration",
            "test_agent_workflow",
            "test_database_integration",
            "test_api_endpoints",
            "test_service_integration"
        ]
    
    def _get_backend_critical_tests(self) -> List[str]:
        """Get backend critical path tests"""
        return [
            "test_critical_auth",
            "test_critical_data_flow",
            "test_critical_agent_execution",
            "test_critical_websocket"
        ]
    
    def _get_backend_smoke_tests(self) -> List[str]:
        """Get backend smoke tests"""
        return [
            "test_smoke_health",
            "test_smoke_database",
            "test_smoke_auth"
        ]
    
    def _get_backend_agent_tests(self) -> List[str]:
        """Get backend agent tests"""
        return [
            "test_triage_agent",
            "test_data_agent",
            "test_reporting_agent",
            "test_analyzer_agent",
            "test_executor_agent"
        ]
    
    def _get_frontend_unit_tests(self) -> List[str]:
        """Get frontend unit test modules"""
        return [
            "ChatInterface.test",
            "AuthProvider.test",
            "useWebSocket.test",
            "apiClient.test"
        ]
    
    def _get_frontend_integration_tests(self) -> List[str]:
        """Get frontend integration test modules"""
        return [
            "auth-flow.test",
            "collaboration-state.test",
            "tool-lifecycle.test",
            "comprehensive-integration.test"
        ]
    
    def _get_frontend_component_tests(self) -> List[str]:
        """Get frontend component tests"""
        return [
            "ChatHistorySection.test",
            "MessageList.test",
            "InputArea.test",
            "SettingsPanel.test"
        ]
    
    def _get_frontend_hook_tests(self) -> List[str]:
        """Get frontend hook tests"""
        return [
            "usePerformanceMetrics.test",
            "useAuth.test",
            "useChat.test"
        ]
    
    def _get_frontend_startup_tests(self) -> List[str]:
        """Get frontend startup tests"""
        return [
            "startup-environment.test",
            "startup-initialization.test",
            "startup-system.test"
        ]
    
    def _get_cypress_tests(self) -> List[str]:
        """Get Cypress E2E tests"""
        return [
            "user-journey.cy",
            "auth-flow.cy",
            "chat-interaction.cy"
        ]
    
    def _get_real_llm_tests(self) -> List[str]:
        """Get real LLM E2E tests"""
        return [
            "test_real_agent_workflow",
            "test_real_llm_integration",
            "test_real_service_integration"
        ]
    
    def _get_mock_e2e_tests(self) -> List[str]:
        """Get mock E2E tests"""
        return [
            "test_mock_e2e_flow",
            "test_mock_agent_interaction"
        ]
    
    def get_test_index(self) -> Dict:
        """Get complete test index"""
        return {
            "catalog": self.test_catalog,
            "relationships": self.test_relationships,
            "last_update": self.last_update,
            "statistics": self._calculate_statistics()
        }
    
    def _calculate_statistics(self) -> Dict:
        """Calculate test statistics"""
        stats = {
            "total_modules": 0,
            "by_category": {},
            "by_component": {}
        }
        
        for component, categories in self.test_catalog.items():
            component_total = 0
            for category, tests in categories.items():
                count = len(tests)
                component_total += count
                stats["by_category"][category] = stats["by_category"].get(category, 0) + count
            stats["by_component"][component] = component_total
            stats["total_modules"] += component_total
        
        return stats
    
    def export_index(self, output_path: Path) -> None:
        """Export test index to JSON file"""
        index = self.get_test_index()
        with open(output_path, 'w') as f:
            json.dump(index, f, indent=2)
    
    def find_tests_for_module(self, module_path: str) -> List[str]:
        """Find tests related to a specific module"""
        related_tests = []
        module_name = Path(module_path).stem.lower()
        
        for component, categories in self.test_catalog.items():
            for category, tests in categories.items():
                for test in tests:
                    if module_name in test.lower():
                        related_tests.append(f"{component}/{category}/{test}")
        
        return related_tests
    
    def get_test_dependencies(self, test_level: str) -> List[str]:
        """Get dependencies for a test level"""
        return self.test_relationships["dependencies"].get(test_level, [])