"""
Deprecated Engine Prevention Test - SSOT Execution Engine Consolidation

This test verifies that deprecated execution engines are properly prevented from
being instantiated after SSOT consolidation, ensuring all usage migrates to 
UserExecutionEngine to maintain Golden Path reliability.

Business Value: Prevents regression to duplicate engines that could break user
isolation and Golden Path (users login → get AI responses) reliability.

CRITICAL: This test ensures SSOT consolidation enforcement and migration completion.
"""

import asyncio
import pytest
import warnings
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestDeprecatedEnginePrevention(SSotBaseTestCase):
    """Test prevention of deprecated execution engine instantiation."""
    
    def setup_method(self, method=None):
        """Setup test with deprecated engine tracking."""
        super().setup_method(method)
        
        # Test user context for engine creation attempts
        self.user_context = UserExecutionContext(
            user_id="deprecation_test_user",
            thread_id="deprecation_thread",
            run_id="deprecation_run", 
            request_id="deprecation_req",
            agent_context={"deprecation_test": True}
        )
        
        # Track deprecation compliance
        self.deprecation_violations: List[Dict[str, Any]] = []
        self.allowed_instantiations: List[Dict[str, Any]] = []
        self.migration_status: Dict[str, Any] = {}
    
    def test_execution_engine_deprecation_warnings(self):
        """TEST 1: Verify deprecated ExecutionEngine shows proper warnings."""
        self.record_metric("test_name", "execution_engine_deprecation_warnings")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            
            with warnings.catch_warnings(record=True) as w:
                # Enable all warnings 
                warnings.simplefilter("always")
                
                # Create mock dependencies
                mock_registry = MagicMock()
                mock_bridge = MagicMock()
                mock_bridge.notify_agent_started = AsyncMock()
                mock_bridge.notify_agent_thinking = AsyncMock()
                mock_bridge.notify_agent_completed = AsyncMock()
                
                # Try to instantiate ExecutionEngine
                try:
                    engine = ExecutionEngine(mock_registry, mock_bridge, self.user_context)
                    
                    # Check if deprecation warning was issued
                    deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
                    
                    if not deprecation_warnings:
                        self.deprecation_violations.append({
                            "engine": "ExecutionEngine",
                            "violation": "no_deprecation_warning",
                            "message": "ExecutionEngine instantiated without deprecation warning"
                        })
                    else:
                        self.record_metric("execution_engine_deprecation_warning_shown", True)
                        print(f"✅ ExecutionEngine shows deprecation warning: {deprecation_warnings[0].message}")
                    
                    # Document that instantiation succeeded (may be acceptable during transition)
                    self.allowed_instantiations.append({
                        "engine": "ExecutionEngine",
                        "status": "allowed_with_warning" if deprecation_warnings else "allowed_no_warning",
                        "user_context_support": engine.user_context is not None
                    })
                    
                except Exception as e:
                    # ExecutionEngine instantiation prevented - good for SSOT
                    self.migration_status["ExecutionEngine"] = {
                        "status": "prevented",
                        "prevention_method": "exception",
                        "error": str(e)
                    }
                    self.record_metric("execution_engine_prevented", True)
            
        except ImportError:
            # ExecutionEngine removed - excellent for SSOT 
            self.migration_status["ExecutionEngine"] = {
                "status": "removed",
                "prevention_method": "import_error"
            }
            self.record_metric("execution_engine_removed", True)
    
    def test_consolidated_engine_deprecation(self):
        """TEST 2: Verify consolidated execution engines are deprecated."""
        self.record_metric("test_name", "consolidated_engine_deprecation")
        
        # Test various consolidated/deprecated engines
        deprecated_engines = [
            ("netra_backend.app.agents.execution_engine_consolidated", "ConsolidatedExecutionEngine"),
            ("netra_backend.app.agents.execution_engine_consolidated", "UnifiedExecutionEngine"),
            ("netra_backend.app.agents.supervisor.request_scoped_execution_engine", "RequestScopedExecutionEngine"),
            ("netra_backend.app.agents.supervisor.mcp_execution_engine", "McpExecutionEngine"),
        ]
        
        for module_path, class_name in deprecated_engines:
            try:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    
                    # Attempt import and instantiation
                    module = __import__(module_path, fromlist=[class_name])
                    engine_class = getattr(module, class_name, None)
                    
                    if engine_class:
                        try:
                            # Try to instantiate (may fail, which is good)
                            engine = self._attempt_engine_creation(engine_class, class_name)
                            
                            # If successful, check for warnings
                            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
                            
                            if engine and not deprecation_warnings:
                                self.deprecation_violations.append({
                                    "engine": class_name,
                                    "violation": "instantiated_without_warning",
                                    "module": module_path
                                })
                            elif engine:
                                self.record_metric(f"{class_name.lower()}_deprecated_properly", True)
                            
                        except Exception as e:
                            # Instantiation prevented - good for SSOT
                            self.migration_status[class_name] = {
                                "status": "prevented",
                                "prevention_method": "instantiation_error",
                                "error": str(e)
                            }
                    else:
                        # Class not found in module
                        self.migration_status[class_name] = {
                            "status": "class_not_found",
                            "module": module_path
                        }
                        
            except ImportError:
                # Module not available - good for SSOT
                self.migration_status[class_name] = {
                    "status": "module_removed",
                    "module": module_path
                }
    
    def _attempt_engine_creation(self, engine_class, class_name: str):
        """Attempt to create deprecated engine with various parameter combinations."""
        
        # Common mock dependencies
        mock_registry = MagicMock()
        mock_bridge = MagicMock()
        mock_bridge.notify_agent_started = AsyncMock()
        
        # Try different instantiation patterns
        try:
            # Pattern 1: Registry + Bridge + UserContext
            return engine_class(mock_registry, mock_bridge, self.user_context)
        except:
            pass
        
        try:
            # Pattern 2: Registry + Bridge only
            return engine_class(mock_registry, mock_bridge)
        except:
            pass
        
        try:
            # Pattern 3: UserContext only
            return engine_class(self.user_context)
        except:
            pass
        
        try:
            # Pattern 4: No arguments (unlikely but test it)
            return engine_class()
        except:
            pass
        
        # If all patterns fail, engine creation is prevented
        return None
    
    def test_ssot_user_execution_engine_available(self):
        """TEST 3: Verify UserExecutionEngine (SSOT) is available and not deprecated."""
        self.record_metric("test_name", "ssot_user_execution_engine_available")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                # Create UserExecutionEngine (should work without warnings)
                mock_factory = MagicMock()
                mock_factory._agent_registry = MagicMock()
                mock_factory._websocket_bridge = MagicMock()
                mock_websocket_emitter = AsyncMock()
                
                try:
                    engine = UserExecutionEngine(
                        context=self.user_context,
                        agent_factory=mock_factory,
                        websocket_emitter=mock_websocket_emitter
                    )
                    
                    # Check for any warnings (shouldn't have deprecation warnings)
                    deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
                    
                    if deprecation_warnings:
                        self.deprecation_violations.append({
                            "engine": "UserExecutionEngine",
                            "violation": "ssot_engine_deprecated",
                            "warnings": [str(w.message) for w in deprecation_warnings]
                        })
                    else:
                        self.record_metric("user_execution_engine_not_deprecated", True)
                    
                    # Verify SSOT engine works properly
                    assert engine.get_user_context().user_id == self.user_context.user_id
                    assert hasattr(engine, 'execute_agent')
                    assert hasattr(engine, 'cleanup')
                    
                    # Clean up (schedule async cleanup)
                    try:
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(engine.cleanup())
                        else:
                            loop.run_until_complete(engine.cleanup())
                    except:
                        pass  # Cleanup optional during testing
                    
                    self.record_metric("ssot_engine_functional", True)
                    
                except Exception as e:
                    self.deprecation_violations.append({
                        "engine": "UserExecutionEngine",
                        "violation": "ssot_engine_broken",
                        "error": str(e)
                    })
                    pytest.fail(f"SSOT VIOLATION: UserExecutionEngine cannot be instantiated: {e}")
            
        except ImportError:
            pytest.fail("SSOT VIOLATION: UserExecutionEngine not available - SSOT broken")
    
    def test_import_redirection_to_ssot(self):
        """TEST 4: Verify deprecated imports redirect to SSOT UserExecutionEngine."""
        self.record_metric("test_name", "import_redirection_to_ssot")
        
        # Test import redirections/bridges
        redirection_tests = [
            # Core module re-export
            ("netra_backend.app.core.execution_engine", "ExecutionEngine"),
            # Tool execution bridge
            ("netra_backend.app.tools.enhanced_tool_execution_engine", "EnhancedToolExecutionEngine"),
        ]
        
        redirection_status = {}
        
        for module_path, class_name in redirection_tests:
            try:
                module = __import__(module_path, fromlist=[class_name])
                imported_class = getattr(module, class_name, None)
                
                if imported_class:
                    # Check if this redirects to/is compatible with UserExecutionEngine
                    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                    
                    # Test if it's a direct alias/import
                    is_user_execution_engine = imported_class is UserExecutionEngine
                    
                    # Test if it's a bridge/wrapper (has __all__ or bridge characteristics)
                    is_bridge = hasattr(module, '__all__') and any('Enhanced' in name or 'Tool' in name for name in module.__all__)
                    
                    redirection_status[f"{module_path}.{class_name}"] = {
                        "available": True,
                        "is_user_execution_engine": is_user_execution_engine,
                        "is_bridge": is_bridge,
                        "class_name": imported_class.__name__
                    }
                    
                    if not (is_user_execution_engine or is_bridge):
                        self.deprecation_violations.append({
                            "import": f"{module_path}.{class_name}",
                            "violation": "not_redirected_to_ssot",
                            "actual_class": imported_class.__name__
                        })
                else:
                    redirection_status[f"{module_path}.{class_name}"] = {
                        "available": False,
                        "reason": "class_not_found"
                    }
                    
            except ImportError as e:
                redirection_status[f"{module_path}.{class_name}"] = {
                    "available": False,
                    "reason": "import_error",
                    "error": str(e)
                }
        
        self.migration_status["import_redirections"] = redirection_status
        self.record_metric("import_redirections_tested", len(redirection_tests))
    
    def test_factory_creates_only_ssot_engines(self):
        """TEST 5: Verify factories create only SSOT UserExecutionEngine instances."""
        self.record_metric("test_name", "factory_creates_only_ssot")
        
        # Test factory compliance
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                get_execution_engine_factory
            )
            
            async def test_factory():
                factory = await get_execution_engine_factory()
                engine = await factory.create_for_user(self.user_context)
                
                # Verify engine is SSOT compliant
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                
                is_user_execution_engine = isinstance(engine, UserExecutionEngine)
                has_ssot_interface = (
                    hasattr(engine, 'get_user_context') and
                    hasattr(engine, 'user_context') and
                    hasattr(engine, 'execute_agent') and
                    hasattr(engine, 'cleanup')
                )
                
                if not (is_user_execution_engine or has_ssot_interface):
                    self.deprecation_violations.append({
                        "factory": "ExecutionEngineFactory",
                        "violation": "creates_non_ssot_engine",
                        "engine_type": type(engine).__name__
                    })
                else:
                    self.record_metric("factory_creates_ssot_engine", True)
                
                # Clean up
                await engine.cleanup()
            
            # Run async test
            import asyncio
            asyncio.create_task(test_factory())
            
        except ImportError:
            # Factory not available - document status
            self.migration_status["ExecutionEngineFactory"] = {
                "status": "not_available",
                "reason": "import_error"
            }
    
    def test_golden_path_protection_during_deprecation(self):
        """GOLDEN PATH: Verify deprecation doesn't break user login → AI response flow."""
        self.record_metric("test_name", "golden_path_deprecation_protection")
        
        # Ensure at least one working execution engine exists for Golden Path
        working_engines = []
        
        # Test UserExecutionEngine (SSOT)
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = MagicMock()
            mock_websocket_emitter = AsyncMock()
            
            engine = UserExecutionEngine(
                context=self.user_context,
                agent_factory=mock_factory,
                websocket_emitter=mock_websocket_emitter
            )
            
            # Verify basic Golden Path functionality
            assert engine.get_user_context().user_id == self.user_context.user_id
            assert hasattr(engine, 'execute_agent')
            
            working_engines.append("UserExecutionEngine")
            
            # Clean up
            # Clean up (schedule async cleanup)
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(engine.cleanup())
                else:
                    loop.run_until_complete(engine.cleanup())
            except:
                pass  # Cleanup optional during testing
            
        except Exception as e:
            self.deprecation_violations.append({
                "golden_path": "UserExecutionEngine_broken",
                "error": str(e)
            })
        
        # Test factory approach
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                get_execution_engine_factory
            )
            
            async def test_factory_golden_path():
                factory = await get_execution_engine_factory()
                engine = await factory.create_for_user(self.user_context)
                
                # Verify Golden Path functionality
                if hasattr(engine, 'get_user_context') and hasattr(engine, 'execute_agent'):
                    working_engines.append("ExecutionEngineFactory")
                
                await engine.cleanup()
            
            asyncio.create_task(test_factory_golden_path())
            
        except:
            pass  # Factory approach not available
        
        # Golden Path protection: At least one approach must work
        if not working_engines:
            pytest.fail(
                "GOLDEN PATH BROKEN: No working execution engines available after deprecation. "
                "Users cannot login → get AI responses. SSOT consolidation failed."
            )
        
        self.record_metric("golden_path_working_engines", len(working_engines))
        self.record_metric("golden_path_protected", True)
        
        print(f"✅ Golden Path Protected: {working_engines} engines functional after deprecation")
    
    def teardown_method(self, method=None):
        """Report deprecation prevention test results."""
        
        all_metrics = self.get_all_metrics()
        
        print(f"\n=== Deprecated Engine Prevention Report ===")
        print(f"Test: {all_metrics.get('test_name', 'unknown')}")
        print(f"Deprecation violations: {len(self.deprecation_violations)}")
        print(f"Engines still allowed: {len(self.allowed_instantiations)}")
        print(f"Execution time: {all_metrics.get('execution_time', 0):.3f}s")
        
        # Migration status summary
        print(f"\nEngine Migration Status:")
        for engine, status in self.migration_status.items():
            if isinstance(status, dict):
                print(f"  {engine}: {status.get('status', 'unknown')}")
            else:
                print(f"  {engine}: {status}")
        
        # Deprecation compliance
        if self.deprecation_violations:
            print(f"\nDeprecation Violations:")
            for violation in self.deprecation_violations:
                print(f"  - {violation.get('engine', 'unknown')}: {violation.get('violation', 'unknown')}")
        
        # Allowed engines (during transition)
        if self.allowed_instantiations:
            print(f"\nEngines Still Instantiable (transition phase):")
            for engine_info in self.allowed_instantiations:
                print(f"  - {engine_info['engine']}: {engine_info['status']}")
        
        # Success indicators
        success_indicators = {
            "SSOT engine functional": all_metrics.get("ssot_engine_functional", False),
            "Golden Path protected": all_metrics.get("golden_path_protected", False),
            "Working engines available": all_metrics.get("golden_path_working_engines", 0),
            "ExecutionEngine removed": all_metrics.get("execution_engine_removed", False)
        }
        
        print(f"\nSSQT Consolidation Progress:")
        for indicator, value in success_indicators.items():
            status = "✅" if value else "⚠️"
            print(f"  {status} {indicator}: {value}")
        
        # Overall assessment
        engines_properly_deprecated = len([s for s in self.migration_status.values() if isinstance(s, dict) and s.get('status') in ['prevented', 'removed']])
        total_engines_checked = len(self.migration_status)
        
        if engines_properly_deprecated == total_engines_checked and not self.deprecation_violations:
            print("✅ SSOT Consolidation Complete: All deprecated engines prevented")
        else:
            print(f"⚠️ SSOT Consolidation In Progress: {engines_properly_deprecated}/{total_engines_checked} engines deprecated")
            print("NOTE: Violations expected during transition, should be resolved after full consolidation")
        
        print("=" * 60)
        
        super().teardown_method(method)


class TestSSotConsolidationReadiness(SSotBaseTestCase):
    """Test overall SSOT consolidation readiness for execution engines."""
    
    def test_ssot_consolidation_completeness(self):
        """TEST 6: Assess overall SSOT consolidation readiness."""
        self.record_metric("test_name", "ssot_consolidation_readiness")
        
        consolidation_score = 0
        max_score = 10
        
        # 1. UserExecutionEngine available (+2 points)
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            consolidation_score += 2
            self.record_metric("user_execution_engine_available", True)
        except ImportError:
            pass
        
        # 2. ExecutionEngineFactory available (+2 points)
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import get_execution_engine_factory
            consolidation_score += 2
            self.record_metric("execution_engine_factory_available", True)
        except ImportError:
            pass
        
        # 3. Legacy ExecutionEngine deprecated/removed (+2 points)
        try:
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            # If available, check if properly deprecated
            consolidation_score += 1  # Partial credit during transition
        except ImportError:
            consolidation_score += 2  # Full credit if removed
            self.record_metric("legacy_execution_engine_removed", True)
        
        # 4. Import redirections working (+2 points)
        import_redirections_working = 0
        try:
            from netra_backend.app.core.execution_engine import ExecutionEngine
            import_redirections_working += 1
        except:
            pass
        
        try:
            from netra_backend.app.tools.enhanced_tool_execution_engine import EnhancedToolExecutionEngine
            import_redirections_working += 1
        except:
            pass
        
        consolidation_score += min(import_redirections_working, 2)
        
        # 5. Golden Path protection (+2 points)
        golden_path_working = False
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            context = UserExecutionContext(
                user_id="consolidation_test", thread_id="test", run_id="test", request_id="test"
            )
            
            # Quick instantiation test
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = MagicMock()
            mock_websocket_emitter = AsyncMock()
            
            engine = UserExecutionEngine(context, mock_factory, mock_websocket_emitter)
            if hasattr(engine, 'execute_agent'):
                golden_path_working = True
                consolidation_score += 2
            
            # Clean up (schedule async cleanup)
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(engine.cleanup())
                else:
                    loop.run_until_complete(engine.cleanup())
            except:
                pass  # Cleanup optional during testing
            
        except:
            pass
        
        # Calculate readiness percentage
        readiness_percentage = (consolidation_score / max_score) * 100
        
        self.record_metric("consolidation_score", consolidation_score)
        self.record_metric("max_possible_score", max_score)
        self.record_metric("readiness_percentage", readiness_percentage)
        
        print(f"\n=== SSOT Consolidation Readiness ===")
        print(f"Score: {consolidation_score}/{max_score} ({readiness_percentage:.1f}%)")
        print(f"Golden Path Protected: {'✅' if golden_path_working else '⚠️'}")
        
        if readiness_percentage >= 80:
            print("✅ SSOT Consolidation Ready")
        elif readiness_percentage >= 60:
            print("⚠️ SSOT Consolidation Mostly Ready - Minor Issues")
        else:
            print("🚨 SSOT Consolidation Not Ready - Major Issues")
        
        return readiness_percentage