"""
WebSocket SSOT Configuration Violation Tests

Tests for SSOT violations in WebSocket configuration management,
ensuring unified configuration across all WebSocket components.

Business Value: Platform/Internal - Prevent configuration drift and inconsistencies
Critical for reliable deployment and environment-specific behavior.

Test Status: DESIGNED TO FAIL with current code (detecting violations)
Expected Result: PASS after SSOT consolidation unifies configuration management
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Set

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketSSotConfigurationViolations(SSotBaseTestCase):
    """Test configuration SSOT violations."""
    
    def test_websocket_configuration_source_consistency(self):
        """
        Test that WebSocket configuration comes from single source after SSOT.
        
        CURRENT BEHAVIOR: Multiple configuration sources exist (VIOLATION)
        EXPECTED AFTER SSOT: Single configuration source
        """
        configuration_sources = {}
        config_violations = []
        
        # Test different configuration access patterns
        try:
            # Direct config access
            from netra_backend.app.config import get_config
            main_config = get_config()
            if hasattr(main_config, 'websocket_config') or 'websocket' in str(main_config.__dict__):
                configuration_sources['main_config'] = True
            else:
                configuration_sources['main_config'] = False
        except (ImportError, AttributeError):
            configuration_sources['main_config'] = False
        
        try:
            # WebSocket-specific config
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            # Check if manager has its own config
            manager = WebSocketManager()
            manager_config_attrs = [attr for attr in dir(manager) if 'config' in attr.lower()]
            configuration_sources['manager_config'] = len(manager_config_attrs) > 0
        except (ImportError, AttributeError):
            configuration_sources['manager_config'] = False
        
        try:
            # Factory config
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory = WebSocketManagerFactory()
            factory_config_attrs = [attr for attr in dir(factory) if 'config' in attr.lower()]
            configuration_sources['factory_config'] = len(factory_config_attrs) > 0
        except (ImportError, AttributeError):
            configuration_sources['factory_config'] = False
        
        try:
            # Environment variable access
            env_vars = [key for key in os.environ.keys() if 'websocket' in key.lower()]
            configuration_sources['direct_env_vars'] = len(env_vars) > 0
        except Exception:
            configuration_sources['direct_env_vars'] = False
        
        try:
            # Isolated environment access
            from shared.isolated_environment import IsolatedEnvironment
            isolated_env = IsolatedEnvironment()
            websocket_env_keys = [key for key in isolated_env.get_all_keys() if 'websocket' in key.lower()]
            configuration_sources['isolated_env'] = len(websocket_env_keys) > 0
        except (ImportError, AttributeError):
            configuration_sources['isolated_env'] = False
        
        working_config_sources = sum(configuration_sources.values())
        
        # Check for configuration drift (same setting in multiple places)
        config_drift_issues = []
        
        # Common WebSocket settings that might be duplicated
        common_settings = [
            'websocket_host',
            'websocket_port', 
            'websocket_timeout',
            'max_connections_per_user',
            'heartbeat_interval'
        ]
        
        for setting in common_settings:
            sources_with_setting = []
            
            # Check main config
            try:
                config = get_config()
                if hasattr(config, setting) or setting in str(config.__dict__):
                    sources_with_setting.append('main_config')
            except:
                pass
            
            # Check environment variables
            env_variations = [setting.upper(), setting.lower(), setting.replace('_', '-').upper()]
            for env_var in env_variations:
                if env_var in os.environ:
                    sources_with_setting.append(f'env_{env_var}')
            
            if len(sources_with_setting) > 1:
                config_drift_issues.append({
                    'setting': setting,
                    'sources': sources_with_setting
                })
        
        total_violations = len(config_drift_issues) + (working_config_sources - 1 if working_config_sources > 1 else 0)
        
        # CURRENT EXPECTATION: Multiple config sources exist (violation)
        # AFTER SSOT: Should have single unified configuration source
        self.assertGreater(working_config_sources, 1,
                          "SSOT VIOLATION DETECTED: Multiple WebSocket configuration sources found. "
                          f"Found {working_config_sources} sources: {configuration_sources}")
        
        self.logger.warning(f"WebSocket Configuration Violations: {working_config_sources} sources, {len(config_drift_issues)} drift issues")
        self.metrics.record_test_event("websocket_config_source_violation", {
            "working_sources": working_config_sources,
            "configuration_sources": configuration_sources,
            "config_drift_issues": config_drift_issues,
            "total_violations": total_violations
        })

    def test_websocket_default_configuration_consistency(self):
        """
        Test that WebSocket default configurations are consistent across components.
        
        CURRENT BEHAVIOR: Inconsistent defaults across components (VIOLATION)
        EXPECTED AFTER SSOT: Consistent defaults from single source
        """
        default_config_violations = []
        component_defaults = {}
        
        # Test default configurations in different components
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            # Check manager defaults
            manager = UnifiedWebSocketManager()
            manager_defaults = {}
            
            # Look for default values in manager
            for attr_name in dir(manager):
                if attr_name.startswith('_') and ('default' in attr_name.lower() or 'config' in attr_name.lower()):
                    try:
                        value = getattr(manager, attr_name)
                        manager_defaults[attr_name] = value
                    except:
                        pass
            
            component_defaults['unified_manager'] = manager_defaults
            
        except (ImportError, AttributeError):
            component_defaults['unified_manager'] = {}
        
        try:
            # Check factory defaults
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            
            factory = WebSocketManagerFactory()
            factory_defaults = {}
            
            for attr_name in dir(factory):
                if 'default' in attr_name.lower() or 'config' in attr_name.lower():
                    try:
                        value = getattr(factory, attr_name)
                        factory_defaults[attr_name] = value
                    except:
                        pass
            
            component_defaults['factory'] = factory_defaults
            
        except (ImportError, AttributeError):
            component_defaults['factory'] = {}
        
        try:
            # Check configuration module defaults
            from netra_backend.app.config import get_config
            
            config = get_config()
            config_defaults = {}
            
            # Look for WebSocket-related config attributes
            for attr_name in dir(config):
                if 'websocket' in attr_name.lower():
                    try:
                        value = getattr(config, attr_name)
                        config_defaults[attr_name] = value
                    except:
                        pass
            
            component_defaults['main_config'] = config_defaults
            
        except (ImportError, AttributeError):
            component_defaults['main_config'] = {}
        
        # Analyze default value consistency
        all_default_keys = set()
        for component_name, defaults in component_defaults.items():
            all_default_keys.update(defaults.keys())
        
        # Check for conflicts in default values
        for key in all_default_keys:
            values_for_key = {}
            
            for component_name, defaults in component_defaults.items():
                if key in defaults:
                    values_for_key[component_name] = defaults[key]
            
            # If same key exists in multiple components with different values
            if len(values_for_key) > 1:
                unique_values = set(str(v) for v in values_for_key.values())
                if len(unique_values) > 1:
                    default_config_violations.append({
                        'key': key,
                        'conflicting_values': values_for_key
                    })
        
        # Check for hardcoded values that should be configurable
        hardcoded_violations = []
        
        # Common hardcoded patterns to look for
        hardcoded_patterns = [
            ('max_connections', 100),
            ('timeout', 30),
            ('heartbeat_interval', 60),
            ('buffer_size', 8192)
        ]
        
        for component_name, defaults in component_defaults.items():
            for pattern_name, common_value in hardcoded_patterns:
                matching_keys = [k for k in defaults.keys() if pattern_name in k.lower()]
                for key in matching_keys:
                    if defaults[key] == common_value:
                        hardcoded_violations.append({
                            'component': component_name,
                            'key': key,
                            'hardcoded_value': common_value
                        })
        
        total_default_violations = len(default_config_violations) + len(hardcoded_violations)
        
        # CURRENT EXPECTATION: Default configuration inconsistencies exist (violation)
        # AFTER SSOT: Should have consistent defaults from single source
        self.assertGreater(total_default_violations, 0,
                          "SSOT VIOLATION DETECTED: WebSocket default configuration inconsistencies found. "
                          f"Conflicts: {len(default_config_violations)}, Hardcoded: {len(hardcoded_violations)}")
        
        self.logger.warning(f"Default Configuration Violations: {total_default_violations} total violations")
        self.metrics.record_test_event("websocket_default_config_violation", {
            "total_violations": total_default_violations,
            "conflict_violations": len(default_config_violations),
            "hardcoded_violations": len(hardcoded_violations),
            "component_defaults": {k: len(v) for k, v in component_defaults.items()},
            "violation_details": {
                "conflicts": default_config_violations[:5],  # Limit for metrics
                "hardcoded": hardcoded_violations[:5]
            }
        })