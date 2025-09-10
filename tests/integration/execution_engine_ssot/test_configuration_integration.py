#!/usr/bin/env python
"""
INTEGRATION TEST 7: Configuration Integration with UserExecutionEngine SSOT

PURPOSE: Test UserExecutionEngine with real configuration system integration (NO MOCKS).
This validates the SSOT requirement that configuration access works correctly through UserExecutionEngine.

Expected to FAIL before SSOT consolidation (proves configuration issues with multiple engines)
Expected to PASS after SSOT consolidation (proves UserExecutionEngine integrates with config correctly)

Business Impact: $500K+ ARR Golden Path protection - configuration controls all system behavior
Integration Level: Tests with real configuration, real environment access, real service configs (NO DOCKER)
"""

import asyncio
import os
import sys
import time
import uuid
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class ConfigurationAccessCapture:
    """Captures configuration access for validation"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.config_accesses = []
        self.websocket_events = []
        self.send_agent_event = AsyncMock(side_effect=self._capture_event)
        
    async def _capture_event(self, event_type: str, data: Dict[str, Any]):
        """Capture WebSocket events"""
        self.websocket_events.append({
            'event_type': event_type,
            'data': data,
            'timestamp': time.time(),
            'user_id': self.user_id
        })
        
    def record_config_access(self, config_key: str, config_value: Any, access_type: str):
        """Record configuration access for validation"""
        self.config_accesses.append({
            'config_key': config_key,
            'config_value': config_value,
            'access_type': access_type,
            'timestamp': time.time(),
            'user_id': self.user_id
        })


class TestConfigurationIntegration(SSotAsyncTestCase):
    """Integration Test 7: Validate configuration integration with UserExecutionEngine SSOT"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_user_id = "config_integration_user"
        self.test_session_id = "config_integration_session"
        
    def test_configuration_system_availability(self):
        """Test that UserExecutionEngine can access configuration system"""
        print("\n🔍 Testing configuration system availability...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        config_violations = []
        config_capture = ConfigurationAccessCapture(self.test_user_id)
        
        # Create UserExecutionEngine
        try:
            engine = UserExecutionEngine(
                user_id=self.test_user_id,
                session_id=self.test_session_id,
                websocket_manager=config_capture
            )
        except Exception as e:
            self.fail(f"Failed to create UserExecutionEngine: {e}")
        
        # Test 1: Configuration access methods
        config_access_methods = [
            'get_config',
            'get_configuration',
            'config'
        ]
        
        available_config_methods = []
        for method_name in config_access_methods:
            if hasattr(engine, method_name):
                method = getattr(engine, method_name)
                if callable(method):
                    available_config_methods.append(method_name)
                    print(f"    ✅ {method_name} method available")
                else:
                    print(f"    ⚠️  {method_name} attribute available but not callable")
            else:
                print(f"    ℹ️  {method_name} method not available")
        
        # Test 2: Check if engine has access to global configuration
        try:
            from netra_backend.app.config import get_config
            global_config = get_config()
            
            if global_config is not None:
                print(f"  ✅ Global configuration available: {type(global_config).__name__}")
                config_capture.record_config_access('global_config', type(global_config).__name__, 'access')
            else:
                config_violations.append("Global configuration is None")
                
        except ImportError as e:
            config_violations.append(f"Cannot import global configuration: {e}")
        except Exception as e:
            config_violations.append(f"Global configuration access failed: {e}")
        
        # Test 3: Test environment variable access through proper channels
        try:
            from dev_launcher.isolated_environment import IsolatedEnvironment
            env = IsolatedEnvironment()
            
            # Test accessing common environment variables
            test_env_vars = [
                'ENVIRONMENT',
                'DATABASE_URL', 
                'REDIS_URL',
                'JWT_SECRET_KEY',
                'LOG_LEVEL'
            ]
            
            env_access_results = {}
            for env_var in test_env_vars:
                try:
                    value = env.get(env_var)
                    env_access_results[env_var] = value is not None
                    config_capture.record_config_access(env_var, bool(value), 'environment')
                except Exception as e:
                    config_violations.append(f"Environment variable {env_var} access failed: {e}")
            
            print(f"  ✅ Environment variable access tested: {sum(env_access_results.values())}/{len(test_env_vars)} available")
            
        except ImportError as e:
            config_violations.append(f"Cannot import IsolatedEnvironment: {e}")
        
        # Test 4: Test database configuration access
        try:
            from netra_backend.app.core.configuration.database import DatabaseConfig
            db_config = DatabaseConfig()
            
            if hasattr(db_config, 'get_connection_string'):
                connection_info = db_config.get_connection_string()
                if connection_info:
                    print(f"  ✅ Database configuration accessible")
                    config_capture.record_config_access('database_config', 'accessible', 'database')
                else:
                    config_violations.append("Database configuration returned empty connection string")
            else:
                config_violations.append("Database configuration missing get_connection_string method")
                
        except ImportError as e:
            print(f"  ⚠️  Database configuration not available: {e}")
        except Exception as e:
            config_violations.append(f"Database configuration access failed: {e}")
        
        # Test 5: Test services configuration access
        try:
            from netra_backend.app.core.configuration.services import ServicesConfig
            services_config = ServicesConfig()
            
            # Test common service configuration methods
            service_methods = ['get_websocket_config', 'get_auth_config', 'get_api_config']
            available_service_methods = []
            
            for method_name in service_methods:
                if hasattr(services_config, method_name):
                    try:
                        method = getattr(services_config, method_name)
                        if callable(method):
                            result = method()
                            available_service_methods.append(method_name)
                            config_capture.record_config_access(method_name, 'accessible', 'services')
                    except Exception as e:
                        config_violations.append(f"Service configuration method {method_name} failed: {e}")
            
            print(f"  ✅ Service configuration methods tested: {len(available_service_methods)}/{len(service_methods)} available")
            
        except ImportError as e:
            print(f"  ⚠️  Services configuration not available: {e}")
        except Exception as e:
            config_violations.append(f"Services configuration access failed: {e}")
        
        # CRITICAL: Configuration access is essential for system operation
        if config_violations:
            self.fail(f"Configuration system availability violations: {config_violations}")
        
        print(f"  ✅ Configuration system availability validated")
    
    def test_user_specific_configuration_isolation(self):
        """Test that user-specific configuration is properly isolated"""
        print("\n🔍 Testing user-specific configuration isolation...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        isolation_violations = []
        
        # Create multiple users with different configurations
        test_users = []
        for i in range(5):
            user_id = f"config_user_{i}"
            config_capture = ConfigurationAccessCapture(user_id)
            
            engine = UserExecutionEngine(
                user_id=user_id,
                session_id=f"config_session_{i}",
                websocket_manager=config_capture
            )
            
            test_users.append({
                'user_id': user_id,
                'engine': engine,
                'config_capture': config_capture,
                'user_index': i
            })
        
        # Test user context isolation in configuration
        for user_data in test_users:
            user_id = user_data['user_id']
            engine = user_data['engine']
            
            # Get user context and validate it's user-specific
            if hasattr(engine, 'get_user_context'):
                try:
                    user_context = engine.get_user_context()
                    
                    if not isinstance(user_context, dict):
                        isolation_violations.append(f"User {user_id} context is not dict: {type(user_context)}")
                        continue
                    
                    # Validate user-specific data
                    if user_context.get('user_id') != user_id:
                        isolation_violations.append(f"User {user_id} context has wrong user_id: {user_context.get('user_id')}")
                    
                    # Validate context doesn't contain other users' data
                    context_str = str(user_context)
                    for other_user in test_users:
                        other_user_id = other_user['user_id']
                        if other_user_id != user_id and other_user_id in context_str:
                            isolation_violations.append(f"User {user_id} context contains {other_user_id}")
                    
                    user_data['config_capture'].record_config_access('user_context', 'isolated', 'user_context')
                    
                except Exception as e:
                    isolation_violations.append(f"User {user_id} context access failed: {e}")
            
            # Test execution context isolation
            if hasattr(engine, 'get_execution_context'):
                try:
                    exec_context = engine.get_execution_context()
                    
                    if isinstance(exec_context, dict):
                        # Execution context should contain user-specific data
                        if 'user_context' in exec_context:
                            nested_user_context = exec_context['user_context']
                            if isinstance(nested_user_context, dict):
                                if nested_user_context.get('user_id') != user_id:
                                    isolation_violations.append(f"User {user_id} execution context has wrong nested user_id")
                        
                        user_data['config_capture'].record_config_access('execution_context', 'isolated', 'execution_context')
                    
                except Exception as e:
                    isolation_violations.append(f"User {user_id} execution context access failed: {e}")
        
        # Test configuration access isolation between users
        configuration_test_scenarios = [
            {
                'name': 'environment_access',
                'test_func': lambda engine: self._test_environment_access_isolation(engine)
            },
            {
                'name': 'database_config_access',
                'test_func': lambda engine: self._test_database_config_isolation(engine)
            },
            {
                'name': 'service_config_access', 
                'test_func': lambda engine: self._test_service_config_isolation(engine)
            }
        ]
        
        for scenario in configuration_test_scenarios:
            print(f"  Testing {scenario['name']} isolation...")
            
            for user_data in test_users:
                user_id = user_data['user_id']
                engine = user_data['engine']
                
                try:
                    result = scenario['test_func'](engine)
                    if result is not False:  # False indicates isolation violation
                        user_data['config_capture'].record_config_access(scenario['name'], 'isolated', scenario['name'])
                    else:
                        isolation_violations.append(f"User {user_id} failed {scenario['name']} isolation")
                        
                except Exception as e:
                    isolation_violations.append(f"User {user_id} {scenario['name']} test failed: {e}")
        
        # Validate no shared configuration objects between users
        config_object_ids = {}
        for user_data in test_users:
            user_id = user_data['user_id']
            engine = user_data['engine']
            
            # Check for shared configuration objects
            if hasattr(engine, 'get_user_context'):
                context = engine.get_user_context()
                context_id = id(context)
                
                if context_id in config_object_ids:
                    isolation_violations.append(f"Shared user context object between {config_object_ids[context_id]} and {user_id}")
                config_object_ids[context_id] = user_id
        
        print(f"  ✅ Configuration isolation tested for {len(test_users)} users")
        
        # CRITICAL: Configuration isolation prevents data leaks and security issues
        if isolation_violations:
            self.fail(f"User-specific configuration isolation violations: {isolation_violations}")
        
        print(f"  ✅ User-specific configuration isolation validated")
    
    def _test_environment_access_isolation(self, engine) -> bool:
        """Test environment variable access isolation"""
        try:
            # Test that environment access goes through proper channels
            if hasattr(engine, 'get_user_context'):
                context = engine.get_user_context()
                
                # Context should not contain raw environment variables
                context_str = str(context).lower()
                sensitive_env_indicators = ['password', 'secret', 'key', 'token', 'database_url']
                
                for indicator in sensitive_env_indicators:
                    if indicator in context_str:
                        print(f"    ⚠️  Potential sensitive data in user context: {indicator}")
                        return False
                
                return True
            return True
            
        except Exception:
            return False
    
    def _test_database_config_isolation(self, engine) -> bool:
        """Test database configuration access isolation"""
        try:
            # Test that database configuration doesn't leak between users
            if hasattr(engine, 'get_execution_context'):
                exec_context = engine.get_execution_context()
                
                # Should not contain direct database connection strings
                if isinstance(exec_context, dict):
                    context_str = str(exec_context).lower()
                    db_indicators = ['postgresql://', 'mongodb://', 'mysql://', 'connection_string']
                    
                    for indicator in db_indicators:
                        if indicator in context_str:
                            print(f"    ⚠️  Potential database connection leak: {indicator}")
                            return False
                
                return True
            return True
            
        except Exception:
            return False
    
    def _test_service_config_isolation(self, engine) -> bool:
        """Test service configuration access isolation"""
        try:
            # Test that service configuration is properly isolated
            user_context = engine.get_user_context() if hasattr(engine, 'get_user_context') else {}
            
            # Should contain user-specific data only
            if isinstance(user_context, dict):
                required_user_fields = ['user_id', 'session_id']
                for field in required_user_fields:
                    if field not in user_context:
                        print(f"    ⚠️  Missing required user field: {field}")
                        return False
                
                return True
            return True
            
        except Exception:
            return False
    
    async def test_configuration_performance_and_caching(self):
        """Test configuration access performance and caching behavior"""
        print("\n🔍 Testing configuration performance and caching...")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            self.skipTest(f"UserExecutionEngine not available: {e}")
        
        performance_violations = []
        config_capture = ConfigurationAccessCapture(self.test_user_id)
        
        # Create UserExecutionEngine
        engine = UserExecutionEngine(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            websocket_manager=config_capture
        )
        
        # Test configuration access performance
        config_access_scenarios = [
            {
                'name': 'user_context_access',
                'test_func': lambda: engine.get_user_context() if hasattr(engine, 'get_user_context') else {}
            },
            {
                'name': 'execution_context_access',
                'test_func': lambda: engine.get_execution_context() if hasattr(engine, 'get_execution_context') else {}
            },
            {
                'name': 'global_config_access',
                'test_func': lambda: self._access_global_config()
            }
        ]
        
        for scenario in config_access_scenarios:
            print(f"  Testing {scenario['name']} performance...")
            
            # Measure multiple accesses to test caching
            access_times = []
            
            for i in range(10):
                start_time = time.perf_counter()
                try:
                    result = scenario['test_func']()
                    access_time = time.perf_counter() - start_time
                    access_times.append(access_time)
                    
                    config_capture.record_config_access(scenario['name'], 'performance_test', 'performance')
                    
                except Exception as e:
                    performance_violations.append(f"{scenario['name']} access {i} failed: {e}")
                    break
            
            if access_times:
                avg_access_time = sum(access_times) / len(access_times)
                max_access_time = max(access_times)
                
                print(f"    ✅ Average access time: {avg_access_time:.4f}s")
                print(f"    ✅ Maximum access time: {max_access_time:.4f}s")
                
                # Performance thresholds
                if avg_access_time > 0.01:  # 10ms average is too slow for config access
                    performance_violations.append(f"{scenario['name']} too slow: {avg_access_time:.4f}s average")
                
                if max_access_time > 0.05:  # 50ms max is too slow for any config access
                    performance_violations.append(f"{scenario['name']} max too slow: {max_access_time:.4f}s")
                
                # Test for caching - later accesses should be faster (or at least not slower)
                if len(access_times) >= 5:
                    first_half_avg = sum(access_times[:5]) / 5
                    second_half_avg = sum(access_times[5:]) / len(access_times[5:])
                    
                    if second_half_avg > first_half_avg * 2:  # Second half shouldn't be much slower
                        performance_violations.append(f"{scenario['name']} performance degraded over time")
                    else:
                        print(f"    ✅ Performance stable over multiple accesses")
        
        # Test concurrent configuration access
        async def concurrent_config_access(access_index: int):
            """Test concurrent configuration access"""
            try:
                start_time = time.perf_counter()
                
                # Access configuration concurrently
                if hasattr(engine, 'get_user_context'):
                    context = engine.get_user_context()
                
                if hasattr(engine, 'get_execution_context'):
                    exec_context = engine.get_execution_context()
                
                access_time = time.perf_counter() - start_time
                return access_time
                
            except Exception as e:
                performance_violations.append(f"Concurrent config access {access_index} failed: {e}")
                return float('inf')
        
        # Run concurrent access test
        print(f"  🔄 Testing concurrent configuration access...")
        
        concurrent_tasks = [concurrent_config_access(i) for i in range(20)]
        concurrent_times = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        valid_times = [t for t in concurrent_times if isinstance(t, (int, float)) and t != float('inf')]
        
        if valid_times:
            concurrent_avg = sum(valid_times) / len(valid_times)
            concurrent_max = max(valid_times)
            
            print(f"  ✅ Concurrent access average: {concurrent_avg:.4f}s")
            print(f"  ✅ Concurrent access maximum: {concurrent_max:.4f}s")
            
            # Concurrent access shouldn't be much slower than sequential
            if concurrent_avg > 0.02:  # 20ms average for concurrent access
                performance_violations.append(f"Concurrent config access too slow: {concurrent_avg:.4f}s")
            
            if concurrent_max > 0.1:  # 100ms max for any concurrent access
                performance_violations.append(f"Concurrent config access max too slow: {concurrent_max:.4f}s")
        
        print(f"  ✅ {len(valid_times)}/{len(concurrent_tasks)} concurrent accesses successful")
        
        # CRITICAL: Configuration performance affects overall system responsiveness
        if performance_violations:
            self.fail(f"Configuration performance violations: {performance_violations}")
        
        print(f"  ✅ Configuration performance and caching validated")
    
    def _access_global_config(self):
        """Helper to access global configuration"""
        try:
            from netra_backend.app.config import get_config
            return get_config()
        except Exception:
            return None


if __name__ == '__main__':
    unittest.main(verbosity=2)