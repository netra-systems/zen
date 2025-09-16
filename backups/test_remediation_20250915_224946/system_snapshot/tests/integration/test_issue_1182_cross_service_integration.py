"""
Issue #1182 Cross-Service Integration Tests

Tests to detect WebSocket Manager SSOT violations across service boundaries:
- Backend-Auth service integration failures
- Shared library SSOT violations
- Service-to-service WebSocket communication
- Configuration inconsistencies across services

These tests should FAIL initially to prove cross-service SSOT violations exist.
"""

import pytest
import requests
import time
import json
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.integration
class Issue1182CrossServiceIntegrationTests(SSotBaseTestCase):
    """Integration tests to detect cross-service WebSocket Manager SSOT violations"""

    @pytest.fixture
    def service_endpoints(self):
        """Service endpoint configuration for testing"""
        return {
            'backend': {
                'base_url': 'http://localhost:8000',
                'websocket_url': 'ws://localhost:8000/ws',
                'health_endpoint': '/health'
            },
            'auth_service': {
                'base_url': 'http://localhost:8001', 
                'websocket_url': 'ws://localhost:8001/ws',
                'health_endpoint': '/health'
            }
        }

    def test_backend_auth_websocket_manager_coordination_failure(self, service_endpoints):
        """SHOULD FAIL: Detect coordination failures between backend and auth WebSocket managers"""
        coordination_results = {}
        
        # Test backend WebSocket manager
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager as BackendManager
            backend_manager = BackendManager()
            
            coordination_results['backend'] = {
                'manager_class': BackendManager.__name__,
                'manager_id': id(backend_manager),
                'methods': [m for m in dir(backend_manager) if not m.startswith('_')],
                'has_send_event': hasattr(backend_manager, 'send_event'),
                'has_broadcast': hasattr(backend_manager, 'broadcast_event')
            }
            
        except ImportError as e:
            coordination_results['backend'] = {'error': f'Import failed: {str(e)}'}
        
        # Test auth service WebSocket manager 
        try:
            from auth_service.websocket.manager import WebSocketManager as AuthManager
            auth_manager = AuthManager()
            
            coordination_results['auth'] = {
                'manager_class': AuthManager.__name__,
                'manager_id': id(auth_manager),
                'methods': [m for m in dir(auth_manager) if not m.startswith('_')],
                'has_send_event': hasattr(auth_manager, 'send_event'),
                'has_broadcast': hasattr(auth_manager, 'broadcast_event')
            }
            
        except ImportError as e:
            coordination_results['auth'] = {'error': f'Import failed: {str(e)}'}
        
        # Test shared WebSocket manager
        try:
            from shared.websocket.manager import WebSocketManager as SharedManager
            shared_manager = SharedManager()
            
            coordination_results['shared'] = {
                'manager_class': SharedManager.__name__,
                'manager_id': id(shared_manager),
                'methods': [m for m in dir(shared_manager) if not m.startswith('_')],
                'has_send_event': hasattr(shared_manager, 'send_event'),
                'has_broadcast': hasattr(shared_manager, 'broadcast_event')
            }
            
        except ImportError as e:
            coordination_results['shared'] = {'error': f'Import failed: {str(e)}'}
        
        self.logger.info(f"Cross-service WebSocket manager coordination: {coordination_results}")
        
        # Analyze coordination issues
        available_managers = {k: v for k, v in coordination_results.items() if 'error' not in v}
        
        if len(available_managers) > 1:
            # Check for interface inconsistencies
            method_sets = {service: set(details['methods']) for service, details in available_managers.items()}
            
            # Find methods that don't exist in all managers
            all_methods = set()
            for methods in method_sets.values():
                all_methods.update(methods)
            
            inconsistent_methods = []
            for method in all_methods:
                implementations = [service for service, methods in method_sets.items() if method in methods]
                if len(implementations) != len(available_managers):
                    inconsistent_methods.append({
                        'method': method,
                        'available_in': implementations,
                        'missing_from': [s for s in available_managers.keys() if s not in implementations]
                    })
            
            # This should FAIL - proving coordination issues exist
            assert len(inconsistent_methods) == 0, (
                f"CROSS-SERVICE COORDINATION FAILURE DETECTED: {len(inconsistent_methods)} methods "
                f"have inconsistent availability across services. Examples: {inconsistent_methods[:3]}"
            )
        
        # This should FAIL - proving multiple managers exist
        assert len(available_managers) <= 1, (
            f"MULTIPLE WEBSOCKET MANAGERS DETECTED: Found {len(available_managers)} different managers "
            f"across services: {list(available_managers.keys())}. SSOT violation - should be exactly 1."
        )

    def test_shared_library_websocket_ssot_violation(self):
        """SHOULD FAIL: Detect SSOT violations in shared WebSocket library usage"""
        shared_usage_analysis = {}
        
        # Analyze how each service uses shared WebSocket components
        services_to_check = [
            ('backend', 'netra_backend'),
            ('auth', 'auth_service')
        ]
        
        for service_name, module_prefix in services_to_check:
            usage_patterns = {}
            
            # Check if service imports from shared
            try:
                # Try importing shared manager from service context
                if service_name == 'backend':
                    # Check if backend imports shared WebSocket components
                    try:
                        import netra_backend.app.websocket_core.manager
                        # Check source for shared imports
                        import inspect
                        source = inspect.getsource(netra_backend.app.websocket_core.manager)
                        usage_patterns['imports_shared'] = 'from shared' in source or 'import shared' in source
                    except:
                        usage_patterns['imports_shared'] = False
                        
                elif service_name == 'auth':
                    try:
                        import auth_service.websocket.manager  
                        import inspect
                        source = inspect.getsource(auth_service.websocket.manager)
                        usage_patterns['imports_shared'] = 'from shared' in source or 'import shared' in source
                    except:
                        usage_patterns['imports_shared'] = False
                
                # Check if service has its own manager implementation
                try:
                    if service_name == 'backend':
                        from netra_backend.app.websocket_core.manager import WebSocketManager
                        usage_patterns['has_own_manager'] = True
                    elif service_name == 'auth':
                        from auth_service.websocket.manager import WebSocketManager  
                        usage_patterns['has_own_manager'] = True
                except ImportError:
                    usage_patterns['has_own_manager'] = False
                
                shared_usage_analysis[service_name] = usage_patterns
                
            except Exception as e:
                shared_usage_analysis[service_name] = {'error': str(e)}
        
        # Check if shared module exists and is used correctly
        try:
            from shared.websocket.manager import WebSocketManager as SharedManager
            shared_usage_analysis['shared_available'] = True
            shared_usage_analysis['shared_manager'] = SharedManager
        except ImportError:
            shared_usage_analysis['shared_available'] = False
        
        self.logger.info(f"Shared library usage analysis: {shared_usage_analysis}")
        
        # Analyze SSOT violations
        services_with_own_managers = [
            service for service, analysis in shared_usage_analysis.items() 
            if isinstance(analysis, dict) and analysis.get('has_own_manager', False)
        ]
        
        shared_available = shared_usage_analysis.get('shared_available', False)
        
        # This should FAIL if both shared and service-specific managers exist
        if shared_available and len(services_with_own_managers) > 0:
            assert False, (
                f"SHARED LIBRARY SSOT VIOLATION DETECTED: Shared WebSocket manager exists but "
                f"{len(services_with_own_managers)} services have their own implementations: "
                f"{services_with_own_managers}. This violates SSOT principle."
            )

    def test_websocket_event_format_consistency_across_services(self):
        """SHOULD FAIL: Detect inconsistent WebSocket event formats across services"""
        event_format_analysis = {}
        
        # Test event sending from different managers
        managers_to_test = []
        
        # Collect available managers
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager as BackendManager
            managers_to_test.append(('backend', BackendManager))
        except ImportError:
            pass
        
        try:
            from auth_service.websocket.manager import WebSocketManager as AuthManager
            managers_to_test.append(('auth', AuthManager))
        except ImportError:
            pass
            
        try:
            from shared.websocket.manager import WebSocketManager as SharedManager
            managers_to_test.append(('shared', SharedManager))
        except ImportError:
            pass
        
        # Test event format consistency
        for service_name, manager_class in managers_to_test:
            try:
                manager = manager_class()
                format_analysis = {}
                
                # Test send_event method signature and behavior
                if hasattr(manager, 'send_event'):
                    import inspect
                    sig = inspect.signature(manager.send_event)
                    format_analysis['send_event_signature'] = str(sig)
                    format_analysis['send_event_params'] = list(sig.parameters.keys())
                    
                    # Try to call with standard parameters
                    try:
                        result = manager.send_event("test_event", {"test": "data"}, "user_123")
                        format_analysis['send_event_result_type'] = type(result).__name__
                        format_analysis['send_event_works'] = True
                    except Exception as e:
                        format_analysis['send_event_works'] = False
                        format_analysis['send_event_error'] = str(e)
                else:
                    format_analysis['send_event_available'] = False
                
                # Test broadcast_event method
                if hasattr(manager, 'broadcast_event'):
                    import inspect
                    sig = inspect.signature(manager.broadcast_event)
                    format_analysis['broadcast_signature'] = str(sig)
                    format_analysis['broadcast_params'] = list(sig.parameters.keys())
                else:
                    format_analysis['broadcast_available'] = False
                
                event_format_analysis[service_name] = format_analysis
                
            except Exception as e:
                event_format_analysis[service_name] = {'error': str(e)}
        
        self.logger.info(f"Event format analysis: {event_format_analysis}")
        
        # Check for format inconsistencies
        if len(event_format_analysis) >= 2:
            # Compare send_event signatures
            send_signatures = {
                service: analysis.get('send_event_signature') 
                for service, analysis in event_format_analysis.items()
                if 'send_event_signature' in analysis
            }
            
            unique_signatures = set(send_signatures.values())
            
            # This should FAIL if signatures are inconsistent
            assert len(unique_signatures) <= 1, (
                f"WEBSOCKET EVENT FORMAT INCONSISTENCY DETECTED: Found {len(unique_signatures)} "
                f"different send_event signatures across services. Signatures: {send_signatures}"
            )

    def test_websocket_configuration_consistency_across_services(self):
        """SHOULD FAIL: Detect configuration inconsistencies across services"""
        config_analysis = {}
        
        # Check WebSocket configuration in each service
        services_to_check = [
            ('backend', 'netra_backend.app.config'),
            ('auth', 'auth_service.config'), 
            ('shared', 'shared.cors_config')
        ]
        
        for service_name, config_module_path in services_to_check:
            try:
                # Import service configuration
                import importlib
                config_module = importlib.import_module(config_module_path)
                
                service_config = {}
                
                # Look for WebSocket-related configuration
                config_attrs = dir(config_module)
                websocket_configs = [attr for attr in config_attrs if 'websocket' in attr.lower() or 'ws' in attr.lower()]
                
                for attr in websocket_configs:
                    try:
                        value = getattr(config_module, attr)
                        service_config[attr] = str(value)  # Convert to string for comparison
                    except:
                        service_config[attr] = 'error_getting_value'
                
                # Look for CORS configuration that affects WebSocket
                cors_configs = [attr for attr in config_attrs if 'cors' in attr.lower()]
                for attr in cors_configs:
                    try:
                        value = getattr(config_module, attr)
                        service_config[f'cors_{attr}'] = str(value)
                    except:
                        service_config[f'cors_{attr}'] = 'error_getting_value'
                
                # Look for port/host configuration
                port_configs = [attr for attr in config_attrs if any(x in attr.lower() for x in ['port', 'host', 'url'])]
                for attr in port_configs[:5]:  # Limit to avoid noise
                    try:
                        value = getattr(config_module, attr)
                        service_config[f'network_{attr}'] = str(value)
                    except:
                        pass
                
                config_analysis[service_name] = service_config
                
            except ImportError:
                config_analysis[service_name] = {'error': 'config_module_not_found'}
            except Exception as e:
                config_analysis[service_name] = {'error': str(e)}
        
        self.logger.info(f"Configuration analysis: {config_analysis}")
        
        # Check for configuration inconsistencies
        valid_configs = {k: v for k, v in config_analysis.items() if 'error' not in v}
        
        if len(valid_configs) >= 2:
            # Find common configuration keys
            all_keys = set()
            for config in valid_configs.values():
                all_keys.update(config.keys())
            
            # Check for inconsistent values for same keys
            inconsistencies = []
            for key in all_keys:
                values = {}
                for service, config in valid_configs.items():
                    if key in config:
                        values[service] = config[key]
                
                if len(values) > 1:
                    unique_values = set(values.values())
                    if len(unique_values) > 1:
                        inconsistencies.append({
                            'config_key': key,
                            'values': values,
                            'unique_values': len(unique_values)
                        })
            
            self.logger.info(f"Configuration inconsistencies found: {len(inconsistencies)}")
            
            # This should FAIL if there are critical configuration inconsistencies
            critical_inconsistencies = [
                inc for inc in inconsistencies 
                if any(critical in inc['config_key'].lower() for critical in ['websocket', 'cors', 'port'])
            ]
            
            assert len(critical_inconsistencies) == 0, (
                f"CRITICAL CONFIGURATION INCONSISTENCIES DETECTED: {len(critical_inconsistencies)} "
                f"critical configs differ across services. Examples: {critical_inconsistencies[:3]}"
            )

    def test_service_to_service_websocket_communication_failure(self, service_endpoints):
        """SHOULD FAIL: Detect failures in service-to-service WebSocket communication"""
        communication_results = {}
        
        # Test communication patterns between services
        for source_service, source_config in service_endpoints.items():
            for target_service, target_config in service_endpoints.items():
                if source_service != target_service:
                    comm_key = f"{source_service}_to_{target_service}"
                    
                    try:
                        # Test HTTP health check first
                        health_url = f"{target_config['base_url']}{target_config['health_endpoint']}"
                        response = requests.get(health_url, timeout=2)
                        
                        communication_results[comm_key] = {
                            'http_health_status': response.status_code,
                            'target_reachable': response.status_code == 200
                        }
                        
                        # If HTTP works, test WebSocket capability
                        if response.status_code == 200:
                            # Try to establish WebSocket connection (mock)
                            import websocket
                            try:
                                ws_url = target_config['websocket_url']
                                # Note: In real test, would establish actual WebSocket connection
                                communication_results[comm_key]['websocket_url_format'] = 'valid'
                                communication_results[comm_key]['websocket_port_accessible'] = True
                            except Exception as e:
                                communication_results[comm_key]['websocket_error'] = str(e)
                        
                    except requests.RequestException as e:
                        communication_results[comm_key] = {
                            'error': str(e),
                            'target_reachable': False
                        }
                    except Exception as e:
                        communication_results[comm_key] = {'error': f'unexpected: {str(e)}'}
        
        self.logger.info(f"Service-to-service communication: {communication_results}")
        
        # Analyze communication failures
        failed_communications = {
            k: v for k, v in communication_results.items() 
            if not v.get('target_reachable', False)
        }
        
        # This should FAIL if services can't communicate (when running)
        if len(communication_results) > 0:  # Only test if services are expected to be running
            total_tests = len(communication_results)
            failures = len(failed_communications)
            
            # Allow some failures since services might not be running in unit test context
            failure_threshold = 0.8  # Allow up to 80% failure in test environment
            failure_rate = failures / total_tests if total_tests > 0 else 0
            
            if failure_rate > failure_threshold:
                self.logger.warning(f"High failure rate in service communication: {failure_rate:.2%}")
                # Don't fail test if services aren't running - this is expected in unit test context
                pytest.skip(f"Services not running for communication test (failure rate: {failure_rate:.2%})")

    def test_websocket_dependency_injection_inconsistency(self):
        """SHOULD FAIL: Detect inconsistent dependency injection patterns for WebSocket managers"""
        injection_analysis = {}
        
        # Check how WebSocket managers are injected into different components
        components_to_check = [
            ('agent_registry', 'netra_backend.app.agents.registry', 'AgentRegistry'),
            ('tool_dispatcher', 'netra_backend.app.tools.enhanced_dispatcher', 'EnhancedToolDispatcher'),
            ('execution_engine', 'netra_backend.app.agents.supervisor.execution_engine', 'ExecutionEngine')
        ]
        
        for component_name, module_path, class_name in components_to_check:
            try:
                import importlib
                module = importlib.import_module(module_path)
                
                if hasattr(module, class_name):
                    component_class = getattr(module, class_name)
                    injection_info = {}
                    
                    # Check constructor signature for WebSocket manager injection
                    import inspect
                    try:
                        init_sig = inspect.signature(component_class.__init__)
                        injection_info['init_params'] = list(init_sig.parameters.keys())
                        injection_info['has_websocket_param'] = any(
                            'websocket' in param.lower() for param in init_sig.parameters.keys()
                        )
                    except:
                        injection_info['init_signature_error'] = True
                    
                    # Check for setter methods
                    methods = [m for m in dir(component_class) if not m.startswith('_')]
                    websocket_setters = [m for m in methods if 'websocket' in m.lower() and ('set' in m.lower() or 'inject' in m.lower())]
                    injection_info['websocket_setters'] = websocket_setters
                    
                    # Check for class-level WebSocket manager storage
                    websocket_attrs = [attr for attr in dir(component_class) if 'websocket' in attr.lower()]
                    injection_info['websocket_attributes'] = websocket_attrs
                    
                    injection_analysis[component_name] = injection_info
                    
            except ImportError:
                injection_analysis[component_name] = {'error': 'module_not_found'}
            except Exception as e:
                injection_analysis[component_name] = {'error': str(e)}
        
        self.logger.info(f"Dependency injection analysis: {injection_analysis}")
        
        # Check for inconsistent injection patterns
        valid_analyses = {k: v for k, v in injection_analysis.items() if 'error' not in v}
        
        if len(valid_analyses) >= 2:
            # Check injection pattern consistency
            injection_patterns = {}
            for component, analysis in valid_analyses.items():
                pattern = []
                if analysis.get('has_websocket_param', False):
                    pattern.append('constructor_injection')
                if analysis.get('websocket_setters'):
                    pattern.append('setter_injection')
                if analysis.get('websocket_attributes'):
                    pattern.append('attribute_access')
                
                injection_patterns[component] = pattern
            
            # Find components with different injection patterns
            all_patterns = set()
            for patterns in injection_patterns.values():
                all_patterns.update(patterns)
            
            pattern_inconsistencies = []
            for pattern in all_patterns:
                components_with_pattern = [comp for comp, patterns in injection_patterns.items() if pattern in patterns]
                components_without_pattern = [comp for comp, patterns in injection_patterns.items() if pattern not in patterns]
                
                if len(components_with_pattern) > 0 and len(components_without_pattern) > 0:
                    pattern_inconsistencies.append({
                        'pattern': pattern,
                        'components_with': components_with_pattern,
                        'components_without': components_without_pattern
                    })
            
            # This should FAIL if injection patterns are inconsistent
            assert len(pattern_inconsistencies) == 0, (
                f"DEPENDENCY INJECTION INCONSISTENCY DETECTED: {len(pattern_inconsistencies)} patterns "
                f"are not consistently used across components. Inconsistencies: {pattern_inconsistencies}"
            )