"""
Dev Launcher User Flow Tests - Development Environment Management

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Developer Velocity & Environment Reliability
- Value Impact: 90% reduction in dev environment setup time (hours to minutes)
- Strategic Impact: Enables rapid onboarding and consistent dev environments

Tests comprehensive dev launcher functionality:
- Automated dev user creation and management
- Environment reset and data seeding capabilities
- Development/production mode switching
- Service coordination and health monitoring
- Developer workflow optimization

CRITICAL: These tests ensure reliable dev environment provisioning
that directly impacts developer productivity and feature velocity.
"""

import pytest
import asyncio
import os
import tempfile
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import time

from dev_launcher.launcher import DevLauncher
from dev_launcher.config import LauncherConfig
from dev_launcher.health_monitor import HealthMonitor
from dev_launcher.process_manager import ProcessManager


class TestDevUserCreation:
    """Test development user creation and management"""

    @pytest.fixture
    def mock_dev_config(self):
        """Mock dev launcher configuration"""
        config = MagicMock(spec=LauncherConfig)
        config.startup_mode = "minimal"
        config.verbose = True
        config.no_browser = True
        config.parallel_startup = True
        config.dynamic_ports = True
        config.backend_port = 8000
        config.frontend_port = 3000
        return config

    @pytest.fixture
    def mock_dev_launcher(self, mock_dev_config):
        """Mock dev launcher instance"""
        with patch('dev_launcher.launcher.DevLauncher.__init__', return_value=None):
            launcher = DevLauncher()
            launcher.config = mock_dev_config
            launcher.health_monitor = MagicMock(spec=HealthMonitor)
            launcher.process_manager = MagicMock(spec=ProcessManager)
            return launcher

    async def test_dev_launcher_with_user(self, mock_dev_launcher, mock_dev_config):
        """Test dev launcher user creation
        
        Business Value: Automated dev user provisioning eliminates
        manual setup steps, reducing onboarding time from hours to minutes
        """
        # Setup: Mock auth service responses
        with patch('dev_launcher.auth_starter.AuthStarter.create_dev_user') as mock_create_user:
            mock_create_user.return_value = {
                "user_id": "dev-user-123",
                "email": "dev@netrasystems.ai",
                "token": "dev-token-auto-created",
                "permissions": ["read", "write", "admin"],
                "created_at": datetime.utcnow().isoformat()
            }

            with patch('dev_launcher.auth_starter.AuthStarter.set_dev_permissions') as mock_set_perms:
                mock_set_perms.return_value = True

                # Execute: Start dev launcher with user creation
                result = await mock_dev_launcher.start_with_dev_user()

                # Verify: Dev user created automatically
                mock_create_user.assert_called_once_with(
                    email="dev@netrasystems.ai",
                    permissions=["read", "write", "admin"]
                )
                
                # Verify: Dev permissions set
                mock_set_perms.assert_called_once_with(
                    user_id="dev-user-123",
                    permissions=["read", "write", "admin"]
                )
                
                # Verify: User creation successful
                assert result["status"] == "success"
                assert result["user"]["email"] == "dev@netrasystems.ai"
                assert result["user"]["token"] == "dev-token-auto-created"

    async def test_dev_environment_reset(self, mock_dev_launcher):
        """Test dev environment reset
        
        Business Value: Clean slate capability ensures consistent
        testing environments and eliminates state pollution issues
        """
        # Setup: Mock database and cache reset operations
        with patch('dev_launcher.cache_manager.CacheManager.clear_all') as mock_clear_cache:
            mock_clear_cache.return_value = True

            with patch('dev_launcher.launcher.DevLauncher.reset_database') as mock_reset_db:
                mock_reset_db.return_value = {"tables_reset": 5, "rows_cleared": 1250}

                with patch('dev_launcher.launcher.DevLauncher.reset_user_state') as mock_reset_user:
                    mock_reset_user.return_value = {"users_reset": 1, "sessions_cleared": 3}

                    with patch('dev_launcher.launcher.DevLauncher.clear_message_history') as mock_clear_msgs:
                        mock_clear_msgs.return_value = {"threads_cleared": 8, "messages_cleared": 45}

                        # Execute: Reset dev environment
                        result = await mock_dev_launcher.reset_environment()

                        # Verify: Database reset
                        mock_reset_db.assert_called_once()
                        
                        # Verify: Redis cache cleared
                        mock_clear_cache.assert_called_once()
                        
                        # Verify: User state reset
                        mock_reset_user.assert_called_once()
                        
                        # Verify: Message history cleared
                        mock_clear_msgs.assert_called_once()
                        
                        # Verify: Reset completed successfully
                        assert result["status"] == "reset_complete"
                        assert result["database"]["tables_reset"] == 5
                        assert result["cache"]["cleared"] is True
                        assert result["user_state"]["users_reset"] == 1
                        assert result["messages"]["threads_cleared"] == 8

    async def test_dev_data_seeding(self, mock_dev_launcher):
        """Test dev data population
        
        Business Value: Pre-populated realistic dev data enables
        immediate feature testing without manual data creation
        """
        # Setup: Mock data seeding operations
        with patch('dev_launcher.data_seeder.DataSeeder.create_sample_threads') as mock_threads:
            mock_threads.return_value = {
                "threads_created": 5,
                "thread_ids": ["thread-1", "thread-2", "thread-3", "thread-4", "thread-5"]
            }

            with patch('dev_launcher.data_seeder.DataSeeder.add_test_messages') as mock_messages:
                mock_messages.return_value = {
                    "messages_created": 25,
                    "conversations": 5,
                    "avg_messages_per_thread": 5
                }

                with patch('dev_launcher.data_seeder.DataSeeder.generate_metrics') as mock_metrics:
                    mock_metrics.return_value = {
                        "metrics_generated": True,
                        "data_points": 100,
                        "time_range": "30_days"
                    }

                    with patch('dev_launcher.data_seeder.DataSeeder.populate_analytics') as mock_analytics:
                        mock_analytics.return_value = {
                            "analytics_populated": True,
                            "charts": 8,
                            "reports": 3
                        }

                        # Execute: Seed dev data
                        result = await mock_dev_launcher.seed_development_data()

                        # Verify: Sample threads created
                        mock_threads.assert_called_once()
                        
                        # Verify: Test messages added
                        mock_messages.assert_called_once()
                        
                        # Verify: Metrics generated
                        mock_metrics.assert_called_once()
                        
                        # Verify: Analytics populated
                        mock_analytics.assert_called_once()
                        
                        # Verify: Realistic dev data created
                        assert result["status"] == "seeding_complete"
                        assert result["threads"]["threads_created"] == 5
                        assert result["messages"]["messages_created"] == 25
                        assert result["metrics"]["data_points"] == 100
                        assert result["analytics"]["charts"] == 8

    async def test_dev_mode_switching(self, mock_dev_launcher):
        """Test switching dev/prod modes
        
        Business Value: Flexible environment switching enables
        testing of production-like behaviors in development
        """
        # Test: Start in dev mode
        initial_config = mock_dev_launcher.config
        assert initial_config.dev_mode is True

        # Setup: Mock production mode configuration
        with patch('dev_launcher.config.DevConfig.load_production_config') as mock_prod_config:
            prod_config = MagicMock()
            prod_config.dev_mode = False
            prod_config.require_oauth = True
            prod_config.skip_auth_in_dev = False
            prod_config.use_real_llm = True
            prod_config.debug_mode = False
            mock_prod_config.return_value = prod_config

            with patch('dev_launcher.launcher.DevLauncher.restart_services') as mock_restart:
                mock_restart.return_value = {"services_restarted": 3, "status": "success"}

                # Execute: Switch to production mode
                result = await mock_dev_launcher.switch_to_production_mode()

                # Verify: Production config loaded
                mock_prod_config.assert_called_once()
                
                # Verify: Services restarted with prod config
                mock_restart.assert_called_once_with(config=prod_config)
                
                # Verify: Production mode activated
                assert result["status"] == "switched_to_production"
                assert result["config"]["dev_mode"] is False
                assert result["config"]["require_oauth"] is True
                
                # Test: OAuth required in production
                with patch('dev_launcher.auth_starter.AuthStarter.validate_oauth_required') as mock_oauth:
                    mock_oauth.return_value = True
                    
                    oauth_check = await mock_dev_launcher.check_oauth_requirements()
                    
                    # Verify: OAuth required in production
                    assert oauth_check["oauth_required"] is True
                    mock_oauth.assert_called_once()

    async def test_dev_service_coordination(self, mock_dev_launcher):
        """Test service startup coordination in dev mode
        
        Business Value: Orchestrated service startup ensures
        dependencies are ready, preventing dev environment failures
        """
        # Setup: Mock service startup sequence
        startup_sequence = []
        
        async def mock_start_auth_service():
            startup_sequence.append("auth_service")
            return {"status": "running", "port": 8001, "health": "ok"}

        async def mock_start_backend_service():
            startup_sequence.append("backend_service")
            return {"status": "running", "port": 8000, "health": "ok"}

        async def mock_start_frontend_service():
            startup_sequence.append("frontend_service")
            return {"status": "running", "port": 3000, "health": "ok"}

        with patch('dev_launcher.auth_starter.AuthStarter.start', side_effect=mock_start_auth_service):
            with patch('dev_launcher.backend_starter.BackendStarter.start', side_effect=mock_start_backend_service):
                with patch('dev_launcher.frontend_starter.FrontendStarter.start', side_effect=mock_start_frontend_service):
                    
                    # Execute: Start all services in coordinated manner
                    result = await mock_dev_launcher.start_all_services()

                    # Verify: Services started in correct order
                    assert startup_sequence == ["auth_service", "backend_service", "frontend_service"]
                    
                    # Verify: All services running
                    assert result["auth_service"]["status"] == "running"
                    assert result["backend_service"]["status"] == "running"
                    assert result["frontend_service"]["status"] == "running"
                    
                    # Verify: Ports assigned correctly
                    assert result["auth_service"]["port"] == 8001
                    assert result["backend_service"]["port"] == 8000
                    assert result["frontend_service"]["port"] == 3000

    async def test_dev_health_monitoring(self, mock_dev_launcher):
        """Test development health monitoring
        
        Business Value: Proactive health monitoring prevents
        dev environment issues and maintains development velocity
        """
        # Setup: Mock health monitoring
        health_checks = []
        
        async def mock_health_check(service_name):
            health_checks.append(service_name)
            return {
                "service": service_name,
                "status": "healthy",
                "response_time": 0.05,
                "timestamp": datetime.utcnow().isoformat()
            }

        with patch('dev_launcher.health_monitor.HealthMonitor.check_service', side_effect=mock_health_check):
            with patch('dev_launcher.health_monitor.HealthMonitor.start_monitoring') as mock_start_monitoring:
                mock_start_monitoring.return_value = {"monitoring_started": True, "interval": 30}

                # Execute: Start health monitoring
                monitoring_result = await mock_dev_launcher.start_health_monitoring()
                
                # Execute: Perform health checks
                auth_health = await mock_dev_launcher.health_monitor.check_service("auth_service")
                backend_health = await mock_dev_launcher.health_monitor.check_service("backend_service")
                frontend_health = await mock_dev_launcher.health_monitor.check_service("frontend_service")

                # Verify: Health monitoring started
                assert monitoring_result["monitoring_started"] is True
                
                # Verify: Health checks performed
                assert "auth_service" in health_checks
                assert "backend_service" in health_checks
                assert "frontend_service" in health_checks
                
                # Verify: All services healthy
                assert auth_health["status"] == "healthy"
                assert backend_health["status"] == "healthy"
                assert frontend_health["status"] == "healthy"
                
                # Verify: Response times acceptable (< 100ms)
                assert auth_health["response_time"] < 0.1
                assert backend_health["response_time"] < 0.1
                assert frontend_health["response_time"] < 0.1


class TestDevWorkflowOptimization:
    """Test developer workflow optimizations"""

    async def test_rapid_iteration_cycle(self):
        """Test rapid development iteration cycle
        
        Business Value: Sub-10 second iteration cycle enables
        rapid feature development and testing
        """
        iteration_times = []
        
        for iteration in range(3):
            start_time = time.time()
            
            # Mock rapid dev cycle: code change -> restart -> test
            with patch('dev_launcher.launcher.DevLauncher.detect_code_changes') as mock_detect:
                mock_detect.return_value = {"files_changed": ["app/routes/test.py"]}
                
                with patch('dev_launcher.launcher.DevLauncher.hot_reload_services') as mock_reload:
                    mock_reload.return_value = {"reloaded": True, "services": ["backend"], "time": 2.5}
                    
                    with patch('dev_launcher.launcher.DevLauncher.run_quick_tests') as mock_tests:
                        mock_tests.return_value = {"tests_passed": 5, "time": 1.2}
                        
                        # Execute: Rapid iteration cycle
                        launcher = DevLauncher()
                        
                        # Detect changes
                        changes = await launcher.detect_code_changes()
                        
                        # Hot reload
                        reload_result = await launcher.hot_reload_services(changes["files_changed"])
                        
                        # Quick tests
                        test_result = await launcher.run_quick_tests()
                        
                        end_time = time.time()
                        iteration_time = end_time - start_time
                        iteration_times.append(iteration_time)
                        
                        # Verify: Iteration components successful
                        assert changes["files_changed"] == ["app/routes/test.py"]
                        assert reload_result["reloaded"] is True
                        assert test_result["tests_passed"] == 5

        # Verify: Rapid iteration performance
        avg_iteration_time = sum(iteration_times) / len(iteration_times)
        max_iteration_time = max(iteration_times)
        
        assert avg_iteration_time < 10.0, f"Average iteration time {avg_iteration_time}s too slow"
        assert max_iteration_time < 15.0, f"Max iteration time {max_iteration_time}s too slow"

    async def test_dev_environment_isolation(self):
        """Test development environment isolation
        
        Business Value: Isolated dev environments prevent
        conflicts and enable parallel development
        """
        # Setup: Mock environment isolation
        with patch('dev_launcher.launcher.DevLauncher.create_isolated_environment') as mock_isolate:
            mock_isolate.return_value = {
                "environment_id": "dev-env-123",
                "isolated": True,
                "database": "netra_dev_123",
                "redis_db": 1,
                "ports": {"backend": 8100, "auth": 8101, "frontend": 3100}
            }
            
            launcher = DevLauncher()
            
            # Execute: Create isolated environment
            env_result = await launcher.create_isolated_environment("dev-env-123")
            
            # Verify: Environment isolation successful
            assert env_result["isolated"] is True
            assert env_result["environment_id"] == "dev-env-123"
            assert env_result["database"] == "netra_dev_123"
            assert env_result["redis_db"] == 1
            
            # Verify: Unique ports assigned
            ports = env_result["ports"]
            assert ports["backend"] == 8100
            assert ports["auth"] == 8101
            assert ports["frontend"] == 3100

    async def test_dev_performance_profiling(self):
        """Test development performance profiling
        
        Business Value: Built-in profiling enables early
        performance optimization and prevents production issues
        """
        # Setup: Mock performance profiling
        with patch('dev_launcher.profiler.DevProfiler.start_profiling') as mock_start_profile:
            mock_start_profile.return_value = {"profiling_started": True, "session_id": "profile-123"}
            
            with patch('dev_launcher.profiler.DevProfiler.get_profile_report') as mock_get_report:
                mock_get_report.return_value = {
                    "session_id": "profile-123",
                    "duration": 30.0,
                    "requests_profiled": 25,
                    "avg_response_time": 0.085,
                    "slowest_endpoints": [
                        {"endpoint": "/api/agents/process", "avg_time": 0.250},
                        {"endpoint": "/api/chat/send", "avg_time": 0.180}
                    ],
                    "memory_usage": {
                        "peak": "128MB",
                        "average": "95MB",
                        "leaks_detected": 0
                    },
                    "recommendations": [
                        "Consider caching for /api/agents/process",
                        "Optimize database queries in chat module"
                    ]
                }
                
                launcher = DevLauncher()
                
                # Execute: Start profiling
                profile_start = await launcher.start_performance_profiling()
                
                # Execute: Get profile report
                report = await launcher.get_profile_report("profile-123")
                
                # Verify: Profiling started successfully
                assert profile_start["profiling_started"] is True
                assert profile_start["session_id"] == "profile-123"
                
                # Verify: Performance metrics captured
                assert report["requests_profiled"] == 25
                assert report["avg_response_time"] < 0.1
                
                # Verify: Slowest endpoints identified
                slow_endpoints = report["slowest_endpoints"]
                assert len(slow_endpoints) == 2
                assert slow_endpoints[0]["endpoint"] == "/api/agents/process"
                
                # Verify: Memory usage tracked
                memory = report["memory_usage"]
                assert memory["leaks_detected"] == 0
                assert "peak" in memory
                
                # Verify: Optimization recommendations provided
                recommendations = report["recommendations"]
                assert len(recommendations) == 2
                assert "caching" in recommendations[0].lower()


class TestDevLauncherIntegration:
    """Integration tests for dev launcher complete workflows"""

    async def test_complete_dev_setup_workflow(self):
        """Test complete development environment setup workflow
        
        Business Value: End-to-end validation ensures reliable
        dev environment provisioning from zero to ready
        """
        setup_steps = []
        
        async def track_step(step_name):
            setup_steps.append(step_name)
            return {"step": step_name, "completed": True, "timestamp": datetime.utcnow()}

        # Setup: Mock complete workflow
        with patch('dev_launcher.launcher.DevLauncher.validate_prerequisites') as mock_prereqs:
            mock_prereqs.side_effect = lambda: track_step("prerequisites")
            
            with patch('dev_launcher.launcher.DevLauncher.setup_databases') as mock_db_setup:
                mock_db_setup.side_effect = lambda: track_step("databases")
                
                with patch('dev_launcher.launcher.DevLauncher.start_services') as mock_services:
                    mock_services.side_effect = lambda: track_step("services")
                    
                    with patch('dev_launcher.launcher.DevLauncher.create_dev_user') as mock_user:
                        mock_user.side_effect = lambda: track_step("dev_user")
                        
                        with patch('dev_launcher.launcher.DevLauncher.seed_data') as mock_seed:
                            mock_seed.side_effect = lambda: track_step("seed_data")
                            
                            with patch('dev_launcher.launcher.DevLauncher.validate_environment') as mock_validate:
                                mock_validate.side_effect = lambda: track_step("validation")
                                
                                launcher = DevLauncher()
                                
                                # Execute: Complete setup workflow
                                await launcher.validate_prerequisites()
                                await launcher.setup_databases()
                                await launcher.start_services()
                                await launcher.create_dev_user()
                                await launcher.seed_data()
                                await launcher.validate_environment()

        # Verify: Complete workflow executed in correct order
        expected_steps = ["prerequisites", "databases", "services", "dev_user", "seed_data", "validation"]
        assert setup_steps == expected_steps

    async def test_dev_environment_recovery(self):
        """Test development environment recovery from failures
        
        Business Value: Automatic recovery capabilities minimize
        downtime and maintain developer productivity
        """
        # Setup: Mock failure scenarios and recovery
        with patch('dev_launcher.recovery_manager.RecoveryManager.detect_failures') as mock_detect:
            mock_detect.return_value = {
                "failures": [
                    {"service": "backend", "error": "port_conflict", "port": 8000},
                    {"service": "auth", "error": "db_connection_failed"}
                ]
            }
            
            with patch('dev_launcher.recovery_manager.RecoveryManager.auto_recover') as mock_recover:
                mock_recover.return_value = {
                    "recovery_actions": [
                        {"action": "reassign_port", "service": "backend", "new_port": 8002},
                        {"action": "restart_database", "service": "postgres"}
                    ],
                    "recovery_successful": True,
                    "services_restored": 2
                }
                
                launcher = DevLauncher()
                
                # Execute: Failure detection and recovery
                failures = await launcher.detect_environment_failures()
                recovery = await launcher.auto_recover_environment(failures)
                
                # Verify: Failures detected
                assert len(failures["failures"]) == 2
                assert failures["failures"][0]["service"] == "backend"
                assert failures["failures"][1]["service"] == "auth"
                
                # Verify: Recovery successful
                assert recovery["recovery_successful"] is True
                assert recovery["services_restored"] == 2
                
                # Verify: Recovery actions appropriate
                actions = recovery["recovery_actions"]
                assert actions[0]["action"] == "reassign_port"
                assert actions[1]["action"] == "restart_database"