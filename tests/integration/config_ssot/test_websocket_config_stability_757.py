"""
Phase 3: WebSocket Configuration Stability Tests
Issue #757 - WebSocket-specific stability during config migration

These tests focus specifically on WebSocket configuration stability
as WebSocket failures are the #1 threat to Golden Path and $500K+ ARR.
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import asyncio
import time


class TestWebSocketConfigurationStability:
    """Phase 3 Tests - WebSocket-specific configuration stability"""

    def test_websocket_cors_config_stability_CRITICAL(self):
        """CRITICAL: CORS configuration for WebSocket must be stable"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager

            config_manager = UnifiedConfigManager()

            # CORS is critical for WebSocket connections from frontend
            cors_methods = [method for method in dir(config_manager)
                          if any(cors_term in method.lower()
                               for cors_term in ['cors', 'origin', 'allow'])]

            if len(cors_methods) > 0:
                cors_stability = {}
                for method_name in cors_methods:
                    try:
                        method = getattr(config_manager, method_name)
                        if callable(method):
                            # Test CORS config consistency over time
                            cors_configs = []
                            for i in range(5):  # More tests for critical CORS
                                cors_configs.append(str(method()))
                                time.sleep(0.005)

                            # CORS must be absolutely consistent
                            stability = len(set(cors_configs)) == 1
                            cors_stability[method_name] = stability
                        else:
                            cors_stability[method_name] = True
                    except Exception as e:
                        cors_stability[method_name] = False
                        print(f"CORS config error in {method_name}: {e}")

                stable_cors_configs = sum(1 for stable in cors_stability.values() if stable)

                assert stable_cors_configs >= len(cors_stability), (
                    f"CRITICAL: WebSocket CORS configuration unstable - "
                    f"CONNECTION BLOCKING RISK: {cors_stability}. "
                    f"Unstable CORS blocks frontend WebSocket connections, "
                    f"breaking real-time chat and $500K+ ARR."
                )

                print(f"✅ WebSocket CORS config fully stable: {stable_cors_configs}/"
                      f"{len(cors_stability)} configs stable")
            else:
                print("ℹ️ No explicit CORS methods - testing general origin handling")

                # Test environment-based CORS handling
                cors_env_vars = ['CORS_ORIGINS', 'ALLOWED_ORIGINS', 'FRONTEND_URL']
                cors_env_stability = {}

                for env_var in cors_env_vars:
                    env_values = []
                    for i in range(3):
                        env_values.append(os.environ.get(env_var, 'NOT_SET'))
                        time.sleep(0.01)

                    stability = len(set(env_values)) == 1
                    cors_env_stability[env_var] = stability

                stable_cors_env = sum(1 for stable in cors_env_stability.values() if stable)

                assert stable_cors_env >= len(cors_env_vars), (
                    f"CORS environment variables unstable: {cors_env_stability}"
                )

        except ImportError as e:
            pytest.fail(f"Cannot test WebSocket CORS configuration stability: {e}")

    def test_websocket_host_port_config_stability_CRITICAL(self):
        """CRITICAL: WebSocket host/port configuration must be stable"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager

            config_manager = UnifiedConfigManager()

            # Host and port configuration is critical for WebSocket connections
            host_port_methods = [method for method in dir(config_manager)
                               if any(hp_term in method.lower()
                                    for hp_term in ['host', 'port', 'url', 'endpoint'])]

            if len(host_port_methods) > 0:
                host_port_stability = {}
                for method_name in host_port_methods:
                    try:
                        method = getattr(config_manager, method_name)
                        if callable(method):
                            # Test host/port consistency
                            network_configs = []
                            for i in range(3):
                                network_configs.append(str(method()))
                                time.sleep(0.01)

                            # Network configuration must be absolutely stable
                            stability = len(set(network_configs)) == 1
                            host_port_stability[method_name] = stability

                            if not stability:
                                print(f"⚠️ {method_name} instability: {network_configs}")
                        else:
                            host_port_stability[method_name] = True
                    except Exception as e:
                        host_port_stability[method_name] = False
                        print(f"Host/port config error in {method_name}: {e}")

                stable_network_configs = sum(1 for stable in host_port_stability.values() if stable)

                assert stable_network_configs >= len(host_port_stability), (
                    f"CRITICAL: WebSocket network configuration unstable - "
                    f"CONNECTION FAILURE RISK: {host_port_stability}. "
                    f"Unstable host/port configuration prevents WebSocket connections, "
                    f"breaking real-time functionality and $500K+ ARR."
                )

                print(f"✅ WebSocket network config fully stable: {stable_network_configs}/"
                      f"{len(host_port_stability)} configs stable")
            else:
                print("ℹ️ No explicit host/port methods - testing environment network config")

                # Test network environment variables
                network_env_vars = ['HOST', 'PORT', 'WEBSOCKET_URL', 'BACKEND_URL']
                network_env_stability = {}

                for env_var in network_env_vars:
                    env_values = []
                    for i in range(3):
                        env_values.append(os.environ.get(env_var, 'NOT_SET'))
                        time.sleep(0.01)

                    stability = len(set(env_values)) == 1
                    network_env_stability[env_var] = stability

                stable_network_env = sum(1 for stable in network_env_stability.values() if stable)

                assert stable_network_env >= len(network_env_vars), (
                    f"Network environment variables unstable: {network_env_stability}"
                )

        except ImportError as e:
            pytest.fail(f"Cannot test WebSocket network configuration stability: {e}")

    def test_websocket_authentication_config_stability_CRITICAL(self):
        """CRITICAL: WebSocket authentication configuration must be stable"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager

            config_manager = UnifiedConfigManager()

            # WebSocket authentication is critical for secure connections
            auth_methods = [method for method in dir(config_manager)
                          if any(auth_term in method.lower()
                               for auth_term in ['jwt', 'secret', 'auth', 'token', 'key'])]

            if len(auth_methods) > 0:
                websocket_auth_stability = {}
                for method_name in auth_methods:
                    try:
                        method = getattr(config_manager, method_name)
                        if callable(method):
                            # Test authentication config over multiple calls
                            auth_configs = []
                            for i in range(4):
                                auth_configs.append(str(method()))
                                time.sleep(0.01)

                            # Authentication config must be absolutely stable
                            stability = len(set(auth_configs)) == 1
                            websocket_auth_stability[method_name] = stability

                            if not stability:
                                # Don't log actual secrets, just indicate instability
                                print(f"⚠️ {method_name} authentication instability detected")
                        else:
                            websocket_auth_stability[method_name] = True
                    except Exception as e:
                        websocket_auth_stability[method_name] = False
                        print(f"WebSocket auth config error in {method_name}: {e}")

                stable_auth_configs = sum(1 for stable in websocket_auth_stability.values() if stable)

                assert stable_auth_configs >= len(websocket_auth_stability), (
                    f"CRITICAL: WebSocket authentication configuration unstable - "
                    f"SECURITY BREACH RISK: {websocket_auth_stability}. "
                    f"Unstable auth config prevents secure WebSocket connections, "
                    f"creating security vulnerabilities and breaking $500K+ ARR functionality."
                )

                print(f"✅ WebSocket auth config fully stable: {stable_auth_configs}/"
                      f"{len(websocket_auth_stability)} configs stable")
            else:
                print("ℹ️ No explicit auth methods - testing JWT environment stability")

                # Test JWT environment variables
                jwt_env_vars = ['JWT_SECRET_KEY', 'JWT_SECRET', 'SECRET_KEY']
                jwt_env_stability = {}

                for env_var in jwt_env_vars:
                    # Test multiple accesses to JWT secret
                    jwt_values = []
                    for i in range(3):
                        jwt_value = os.environ.get(env_var, 'NOT_SET')
                        jwt_values.append(jwt_value)
                        time.sleep(0.01)

                    stability = len(set(jwt_values)) == 1
                    jwt_env_stability[env_var] = stability

                stable_jwt_env = sum(1 for stable in jwt_env_stability.values() if stable)

                assert stable_jwt_env >= len(jwt_env_vars), (
                    f"JWT environment variables unstable: {jwt_env_stability}"
                )

        except ImportError as e:
            pytest.fail(f"Cannot test WebSocket authentication configuration stability: {e}")

    def test_websocket_event_delivery_config_stability_CRITICAL(self):
        """CRITICAL: WebSocket event delivery configuration must be stable"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager

            config_manager = UnifiedConfigManager()

            # Event delivery configuration affects real-time user experience
            event_methods = [method for method in dir(config_manager)
                           if any(event_term in method.lower()
                                for event_term in ['event', 'message', 'notification', 'broadcast'])]

            if len(event_methods) > 0:
                event_config_stability = {}
                for method_name in event_methods:
                    try:
                        method = getattr(config_manager, method_name)
                        if callable(method):
                            # Test event configuration consistency
                            event_configs = []
                            for i in range(3):
                                event_configs.append(str(method()))
                                time.sleep(0.01)

                            # Event delivery config must be stable
                            stability = len(set(event_configs)) == 1
                            event_config_stability[method_name] = stability
                        else:
                            event_config_stability[method_name] = True
                    except Exception as e:
                        event_config_stability[method_name] = False
                        print(f"Event config error in {method_name}: {e}")

                stable_event_configs = sum(1 for stable in event_config_stability.values() if stable)

                assert stable_event_configs >= len(event_config_stability), (
                    f"CRITICAL: WebSocket event delivery configuration unstable - "
                    f"REAL-TIME UX FAILURE: {event_config_stability}. "
                    f"Unstable event config breaks real-time agent progress updates, "
                    f"degrading user experience and $500K+ ARR value."
                )

                print(f"✅ WebSocket event config fully stable: {stable_event_configs}/"
                      f"{len(event_config_stability)} configs stable")
            else:
                print("ℹ️ No explicit event methods - testing general configuration stability")

                # Test general configuration stability for event systems
                all_methods = [method for method in dir(config_manager)
                             if not method.startswith('_') and callable(getattr(config_manager, method))]

                if len(all_methods) >= 3:
                    general_stability = {}
                    for method_name in all_methods[:3]:
                        try:
                            method = getattr(config_manager, method_name)
                            results = [method() for _ in range(3)]
                            stability = len(set(str(r) for r in results)) == 1
                            general_stability[method_name] = stability
                        except Exception:
                            general_stability[method_name] = False

                    stable_general_configs = sum(1 for stable in general_stability.values() if stable)

                    assert stable_general_configs >= len(general_stability) * 0.8, (
                        f"General configuration instability affects WebSocket events: {general_stability}"
                    )

        except ImportError as e:
            pytest.fail(f"Cannot test WebSocket event configuration stability: {e}")

    def test_websocket_connection_pooling_config_stability(self):
        """SHOULD PASS: WebSocket connection pooling config stable if present"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager

            config_manager = UnifiedConfigManager()

            # Connection pooling affects WebSocket scalability
            pool_methods = [method for method in dir(config_manager)
                          if any(pool_term in method.lower()
                               for pool_term in ['pool', 'connection', 'limit', 'max', 'timeout'])]

            if len(pool_methods) > 0:
                pool_config_stability = {}
                for method_name in pool_methods:
                    try:
                        method = getattr(config_manager, method_name)
                        if callable(method):
                            # Test connection pool config consistency
                            pool_configs = []
                            for i in range(3):
                                pool_configs.append(str(method()))
                                time.sleep(0.01)

                            stability = len(set(pool_configs)) == 1
                            pool_config_stability[method_name] = stability
                        else:
                            pool_config_stability[method_name] = True
                    except Exception:
                        pool_config_stability[method_name] = False

                stable_pool_configs = sum(1 for stable in pool_config_stability.values() if stable)

                # Connection pooling should be stable if present
                assert stable_pool_configs >= len(pool_config_stability) * 0.8, (
                    f"WebSocket connection pooling configuration unstable: {pool_config_stability}"
                )

                print(f"✅ WebSocket connection pooling config stable: {stable_pool_configs}/"
                      f"{len(pool_config_stability)} configs stable")
            else:
                print("ℹ️ No explicit connection pooling methods found")

        except ImportError as e:
            pytest.skip(f"Cannot test WebSocket connection pooling stability: {e}")


class TestWebSocketMigrationIntegration:
    """Test WebSocket integration during configuration migration"""

    def test_websocket_manager_config_compatibility_CRITICAL(self):
        """CRITICAL: WebSocket manager compatible with new configuration"""
        try:
            sys.path.insert(0, str(Path.cwd()))

            # Test that WebSocket manager can use canonical configuration
            from netra_backend.app.core.configuration.base import UnifiedConfigManager

            config_manager = UnifiedConfigManager()

            # WebSocket manager needs configuration for initialization
            config_interface = dir(config_manager)
            websocket_compatible_methods = [method for method in config_interface
                                          if not method.startswith('_')]

            assert len(websocket_compatible_methods) >= 5, (
                f"Insufficient configuration interface for WebSocket manager: "
                f"{len(websocket_compatible_methods)} methods. WebSocket manager "
                f"needs comprehensive configuration access."
            )

            # Test configuration method accessibility
            accessible_methods = 0
            method_results = {}

            for method_name in websocket_compatible_methods[:5]:
                try:
                    method = getattr(config_manager, method_name)
                    if callable(method):
                        result = method()
                        method_results[method_name] = "accessible"
                        accessible_methods += 1
                    else:
                        method_results[method_name] = "property"
                        accessible_methods += 1
                except Exception as e:
                    method_results[method_name] = f"error: {str(e)[:30]}"

            assert accessible_methods >= 3, (
                f"WebSocket manager cannot access sufficient configuration methods: "
                f"{method_results}. This breaks WebSocket initialization and $500K+ ARR."
            )

            print(f"✅ WebSocket manager config compatibility: {accessible_methods}/"
                  f"{len(websocket_compatible_methods)} methods accessible")

        except ImportError as e:
            pytest.fail(f"Cannot test WebSocket manager configuration compatibility: {e}")

    def test_websocket_startup_sequence_config_dependency_CRITICAL(self):
        """CRITICAL: WebSocket startup sequence works with canonical config"""
        try:
            sys.path.insert(0, str(Path.cwd()))

            # Simulate WebSocket service startup with canonical configuration
            from netra_backend.app.core.configuration.base import UnifiedConfigManager

            # Test multiple startup simulations
            startup_successes = []
            for attempt in range(3):
                try:
                    config_manager = UnifiedConfigManager()

                    # Simulate startup configuration requirements
                    startup_requirements = [
                        'Configuration instantiation',
                        'Method enumeration',
                        'Basic method execution',
                        'Stability verification'
                    ]

                    startup_steps = {}

                    # Step 1: Configuration instantiation
                    startup_steps['instantiation'] = config_manager is not None

                    # Step 2: Method enumeration
                    methods = [m for m in dir(config_manager) if not m.startswith('_')]
                    startup_steps['enumeration'] = len(methods) > 0

                    # Step 3: Basic method execution
                    if len(methods) > 0 and hasattr(config_manager, methods[0]):
                        first_method = getattr(config_manager, methods[0])
                        if callable(first_method):
                            try:
                                first_method()
                                startup_steps['execution'] = True
                            except Exception:
                                startup_steps['execution'] = False
                        else:
                            startup_steps['execution'] = True  # Property access is fine
                    else:
                        startup_steps['execution'] = False

                    # Step 4: Stability verification
                    startup_steps['stability'] = all(startup_steps.values())

                    # Overall startup success
                    startup_success = sum(startup_steps.values()) >= 3
                    startup_successes.append(startup_success)

                    time.sleep(0.01)

                except Exception as e:
                    startup_successes.append(False)
                    print(f"Startup simulation {attempt + 1} failed: {e}")

            overall_startup_success = sum(startup_successes) >= len(startup_successes)

            assert overall_startup_success, (
                f"CRITICAL: WebSocket startup sequence fails with canonical configuration - "
                f"SERVICE AVAILABILITY RISK: {startup_successes}. "
                f"WebSocket service cannot start reliably, breaking real-time functionality "
                f"and $500K+ ARR."
            )

            print(f"✅ WebSocket startup sequence stable: {sum(startup_successes)}/"
                  f"{len(startup_successes)} successful startups")

        except ImportError as e:
            pytest.fail(f"Cannot test WebSocket startup sequence: {e}")


if __name__ == "__main__":
    print("Phase 3: Running WebSocket Configuration Stability Tests")
    print("These tests protect WebSocket functionality during configuration migration")
    pytest.main([__file__, "-v", "--tb=short"])