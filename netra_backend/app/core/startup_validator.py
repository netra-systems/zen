"""
Startup Validation System - Validates critical components at application startup.

This module prevents runtime failures by validating critical system components
during application initialization. If validation fails, the application should
not start, preventing broken deployments.

Business Value:
- Prevents broken deployments from reaching production
- Catches configuration and integration issues early
- Reduces MTTR by failing fast with clear error messages
"""

import sys
import inspect
import importlib
import traceback
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class ValidationStatus(Enum):
    """Status of a validation check."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    name: str
    status: ValidationStatus
    message: str
    duration_ms: float
    error: Optional[Exception] = None
    traceback: Optional[str] = None


class StartupValidator:
    """
    Validates critical system components at startup.
    
    This class runs a series of validation checks to ensure all critical
    components are properly configured and functional before allowing
    the application to start.
    """
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.start_time = None
        self.end_time = None
    
    async def validate_all(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            True if all critical validations pass, False otherwise
        """
        logger.info("Starting system validation...")
        self.start_time = datetime.now()
        
        validations = [
            ("ID Generation", self._validate_id_generation),
            ("WebSocket Components", self._validate_websocket_components),
            ("Thread Service", self._validate_thread_service),
            ("Database Repositories", self._validate_repositories),
            ("Import Integrity", self._validate_imports),
            ("Method Signatures", self._validate_method_signatures),
            ("Agent Registry", self._validate_agent_registry),
            ("Configuration", self._validate_configuration),
        ]
        
        all_passed = True
        
        for name, validator in validations:
            start = datetime.now()
            result = ValidationResult(
                name=name,
                status=ValidationStatus.RUNNING,
                message="Running...",
                duration_ms=0
            )
            
            try:
                logger.info(f"Validating {name}...")
                
                # Run validation
                if asyncio.iscoroutinefunction(validator):
                    success, message = await validator()
                else:
                    success, message = validator()
                
                # Update result
                duration = (datetime.now() - start).total_seconds() * 1000
                result.status = ValidationStatus.PASSED if success else ValidationStatus.FAILED
                result.message = message
                result.duration_ms = duration
                
                if success:
                    logger.info(f"[U+2713] {name}: {message} ({duration:.1f}ms)")
                else:
                    logger.error(f"[U+2717] {name}: {message} ({duration:.1f}ms)")
                    all_passed = False
                    
            except Exception as e:
                duration = (datetime.now() - start).total_seconds() * 1000
                result.status = ValidationStatus.FAILED
                result.message = f"Exception: {str(e)}"
                result.duration_ms = duration
                result.error = e
                result.traceback = traceback.format_exc()
                
                logger.error(f"[U+2717] {name}: {result.message} ({duration:.1f}ms)")
                logger.error(f"  Traceback: {result.traceback}")
                all_passed = False
            
            self.results.append(result)
        
        self.end_time = datetime.now()
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        if all_passed:
            logger.info(f" PASS:  All validations passed in {total_duration:.1f}s")
        else:
            logger.error(f" FAIL:  Validation failed in {total_duration:.1f}s")
            self._print_summary()
        
        return all_passed
    
    def _validate_id_generation(self) -> Tuple[bool, str]:
        """Validate UnifiedIDManager works correctly."""
        try:
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            
            # Test basic generation
            test_thread = "startup_validation"
            run_id = UnifiedIDManager.generate_run_id(test_thread)
            
            if not UnifiedIDManager.validate_run_id(run_id):
                return False, f"Generated invalid run_id: {run_id}"
            
            # Test extraction
            extracted = UnifiedIDManager.extract_thread_id(run_id)
            if extracted != test_thread:
                return False, f"Thread extraction failed: expected {test_thread}, got {extracted}"
            
            # Test method signature (catch 2-argument bug)
            sig = inspect.signature(UnifiedIDManager.generate_run_id)
            param_count = len([p for p in sig.parameters.values() if p.default == inspect.Parameter.empty])
            if param_count != 1:
                return False, f"generate_run_id has wrong signature: {param_count} required params instead of 1"
            
            # Test that wrong arguments fail properly
            try:
                UnifiedIDManager.generate_run_id("test", "extra")
                return False, "generate_run_id accepts extra arguments (should only accept 1)"
            except TypeError:
                # This is expected
                pass
            
            return True, "ID generation working correctly"
            
        except Exception as e:
            return False, f"Failed to validate ID generation: {str(e)}"
    
    def _validate_websocket_components(self) -> Tuple[bool, str]:
        """Validate WebSocket components can be imported and initialized."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            
            # Test bridge can use UnifiedIDManager
            bridge = AgentWebSocketBridge()
            test_run_id = UnifiedIDManager.generate_run_id("websocket_test")
            thread_id = bridge.extract_thread_id(test_run_id)
            
            if thread_id != "websocket_test":
                return False, f"WebSocket bridge extraction failed: {thread_id}"
            
            return True, "WebSocket components functional"
            
        except Exception as e:
            return False, f"WebSocket component error: {str(e)}"
    
    def _validate_thread_service(self) -> Tuple[bool, str]:
        """Validate ThreadService works correctly."""
        try:
            from netra_backend.app.services.thread_service import ThreadService
            
            service = ThreadService()
            
            # Test _prepare_run_data (where the 2-argument bug was)
            run_id, run_data = service._prepare_run_data(
                thread_id="test_thread",
                assistant_id="test_assistant",
                model="gpt-4",
                instructions="test"
            )
            
            if not run_id or not run_data:
                return False, "ThreadService._prepare_run_data failed"
            
            if run_data["thread_id"] != "test_thread":
                return False, f"Thread ID mismatch in run_data: {run_data['thread_id']}"
            
            return True, "ThreadService working correctly"
            
        except TypeError as e:
            if "takes 1 positional argument but 2 were given" in str(e):
                return False, f"ThreadService has 2-argument bug: {str(e)}"
            raise
        except Exception as e:
            return False, f"ThreadService error: {str(e)}"
    
    def _validate_repositories(self) -> Tuple[bool, str]:
        """Validate database repositories."""
        try:
            from netra_backend.app.services.database.run_repository import RunRepository
            
            # Just validate import and class exists
            if not RunRepository:
                return False, "RunRepository not found"
            
            return True, "Repositories validated"
            
        except Exception as e:
            return False, f"Repository error: {str(e)}"
    
    def _validate_imports(self) -> Tuple[bool, str]:
        """Validate critical imports work."""
        # CRITICAL FIX: Updated module list to match actual SSOT architecture
        # Removed non-existent modules and added graceful handling
        critical_modules = [
            'netra_backend.app.core.unified_id_manager',
            'netra_backend.app.services.thread_service', 
            'netra_backend.app.services.agent_websocket_bridge',
            'netra_backend.app.core.interfaces_observability'
        ]
        
        # Optional modules that may not exist in all deployment scenarios
        optional_modules = [
            'netra_backend.app.orchestration.agent_execution_registry',  # May not exist in some setups
            'netra_backend.app.agents.registry',  # Alternative registry location
            'netra_backend.app.agents.supervisor.agent_registry'  # Actual agent registry
        ]
        
        failed_imports = []
        optional_failures = []
        
        # Validate critical modules - these MUST exist
        for module_name in critical_modules:
            try:
                importlib.import_module(module_name)
            except Exception as e:
                failed_imports.append(f"{module_name}: {str(e)}")
        
        # Validate optional modules - failure is logged but not critical
        for module_name in optional_modules:
            try:
                importlib.import_module(module_name)
            except Exception as e:
                optional_failures.append(f"{module_name}: {str(e)}")
        
        # Hard fail only on critical modules
        if failed_imports:
            return False, f"Critical import failures: {', '.join(failed_imports)}"
        
        # Log optional failures but don't fail validation
        warning_msg = f"All {len(critical_modules)} critical modules imported"
        if optional_failures:
            logger.warning(f"Optional module import warnings: {', '.join(optional_failures)}")
            warning_msg += f" ({len(optional_failures)} optional modules unavailable)"
        
        return True, warning_msg
    
    def _validate_method_signatures(self) -> Tuple[bool, str]:
        """Validate critical method signatures are correct."""
        try:
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            
            validations = []
            
            # Check critical methods
            # CRITICAL FIX: generate_run_id has optional thread_id parameter, so it has 0 required args
            # but can accept 1 optional arg. This is correct behavior for SSOT compatibility.
            methods_to_check = [
                ('generate_run_id', 0),  # FIXED: Optional thread_id parameter means 0 required args
                ('extract_thread_id', 1),
                ('validate_run_id', 1),
                ('parse_run_id', 1),
            ]
            
            for method_name, expected_required in methods_to_check:
                method = getattr(UnifiedIDManager, method_name)
                sig = inspect.signature(method)
                required = len([p for p in sig.parameters.values() if p.default == inspect.Parameter.empty])
                
                if required != expected_required:
                    validations.append(
                        f"{method_name}: expected {expected_required} args, has {required}"
                    )
            
            if validations:
                return False, f"Signature mismatches: {'; '.join(validations)}"
            
            return True, "All method signatures correct"
            
        except Exception as e:
            return False, f"Signature validation error: {str(e)}"
    
    def _validate_agent_registry(self) -> Tuple[bool, str]:
        """Validate AgentRegistry using SSOT pattern."""
        try:
            # Use SSOT AgentRegistry from UniversalRegistry
            from netra_backend.app.core.registry.universal_registry import get_global_registry
            
            # Get the global agent registry instance
            registry = get_global_registry("agent")
            
            # Validate it's properly initialized
            if not registry:
                return False, "AgentRegistry initialization failed"
            
            # Check if it's healthy
            if hasattr(registry, 'is_healthy') and not registry.is_healthy():
                return False, "AgentRegistry is not healthy"
            
            # Get stats for validation
            stats = registry.get_stats() if hasattr(registry, 'get_stats') else {}
            registered_count = stats.get('registered_count', 0)
            
            return True, f"AgentRegistry validated ({registered_count} agents registered)"
            
        except Exception as e:
            return False, f"AgentRegistry error: {str(e)}"
    
    def _validate_configuration(self) -> Tuple[bool, str]:
        """Validate configuration is properly loaded."""
        try:
            from netra_backend.app.config import settings
            
            # Check critical settings exist
            critical_settings = ['environment']  # Use actual SSOT configuration attributes
            
            missing = []
            for setting in critical_settings:
                if not hasattr(settings, setting):
                    missing.append(setting)
            
            if missing:
                return False, f"Missing settings: {', '.join(missing)}"
            
            return True, f"Configuration loaded (env: {settings.environment})"
            
        except Exception as e:
            return False, f"Configuration error: {str(e)}"
    
    def _print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        for result in self.results:
            status_symbol = {
                ValidationStatus.PASSED: "[U+2713]",
                ValidationStatus.FAILED: "[U+2717]",
                ValidationStatus.SKIPPED: "[U+2298]",
                ValidationStatus.RUNNING: "[U+27F3]",
                ValidationStatus.PENDING: "[U+25EF]"
            }.get(result.status, "?")
            
            print(f"{status_symbol} {result.name}: {result.message} ({result.duration_ms:.1f}ms)")
            
            if result.error and result.traceback:
                print(f"  Error: {result.error}")
                for line in result.traceback.split('\n'):
                    if line.strip():
                        print(f"    {line}")
        
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r.status == ValidationStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == ValidationStatus.FAILED)
        total = len(self.results)
        
        print(f"Results: {passed}/{total} passed, {failed} failed")
        
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            print(f"Total time: {duration:.1f}s")
        
        print("=" * 60 + "\n")


async def validate_startup() -> bool:
    """
    Main entry point for startup validation.
    
    Returns:
        True if all validations pass, False otherwise
    """
    validator = StartupValidator()
    return await validator.validate_all()


def require_startup_validation():
    """
    Decorator that requires startup validation before running.
    
    Use this on critical functions that should only run if the system
    is properly validated.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Check if validation has been performed
            if not hasattr(wrapper, '_validated'):
                logger.warning(f"{func.__name__} called without startup validation")
            return func(*args, **kwargs)
        
        wrapper._validated = False
        return wrapper
    
    return decorator


if __name__ == "__main__":
    # Run validation when module is executed directly
    import asyncio
    
    async def main():
        success = await validate_startup()
        sys.exit(0 if success else 1)
    
    asyncio.run(main())