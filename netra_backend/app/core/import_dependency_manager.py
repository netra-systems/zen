"""
Import Dependency Manager for Issue #1278

This module provides robust import dependency management to handle missing
modules and import failures in Cloud Run environments.

Critical Fix: Handles auth_service import failures during middleware setup
that were causing container exit code 3 failures.

Business Value: Prevents complete platform outages due to import dependency issues.
"""

import logging
import sys
import importlib
import time
from typing import Optional, Dict, Any, List, Callable, Tuple
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class ImportDependencyManager:
    """
    Manages import dependencies with graceful degradation for Issue #1278.

    Provides retry logic, fallback handling, and diagnostic information
    for import failures that can cause container startup failures.
    """

    def __init__(self):
        """Initialize import dependency manager."""
        self.failed_imports: Dict[str, Exception] = {}
        self.successful_imports: List[str] = []
        self.retry_counts: Dict[str, int] = {}
        self.import_times: Dict[str, float] = {}

    def safe_import(self, module_name: str, retry_count: int = 3,
                   retry_delay: float = 1.0) -> Tuple[Optional[Any], Optional[Exception]]:
        """
        Safely import a module with retry logic and error handling.

        Args:
            module_name: Name of module to import
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Tuple of (module, error) - module is None if import failed
        """
        start_time = time.time()

        for attempt in range(retry_count + 1):
            try:
                logger.debug(f"Attempting import of '{module_name}' (attempt {attempt + 1}/{retry_count + 1})")

                # Try to import the module
                module = importlib.import_module(module_name)

                # Record success
                import_time = time.time() - start_time
                self.successful_imports.append(module_name)
                self.import_times[module_name] = import_time
                self.retry_counts[module_name] = attempt

                logger.info(f"✅ Successfully imported '{module_name}' after {attempt} retries in {import_time:.2f}s")
                return module, None

            except Exception as e:
                logger.warning(f"❌ Import attempt {attempt + 1} failed for '{module_name}': {e}")

                if attempt < retry_count:
                    logger.debug(f"Retrying import of '{module_name}' in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    # Final failure
                    import_time = time.time() - start_time
                    self.failed_imports[module_name] = e
                    self.import_times[module_name] = import_time
                    self.retry_counts[module_name] = attempt + 1

                    logger.error(f"❌ Failed to import '{module_name}' after {retry_count} retries in {import_time:.2f}s: {e}")
                    return None, e

        return None, Exception("Unexpected retry loop exit")

    def import_with_fallback(self, primary_module: str, fallback_modules: List[str],
                           fallback_factory: Optional[Callable] = None) -> Tuple[Optional[Any], str]:
        """
        Import a module with fallback options for resilience.

        Args:
            primary_module: Primary module to try importing
            fallback_modules: List of fallback module names to try
            fallback_factory: Optional factory function to create fallback object

        Returns:
            Tuple of (imported_object, source_description)
        """
        # Try primary module first
        module, error = self.safe_import(primary_module)
        if module is not None:
            return module, f"primary:{primary_module}"

        logger.warning(f"Primary module '{primary_module}' failed, trying fallbacks...")

        # Try fallback modules
        for fallback_module in fallback_modules:
            module, error = self.safe_import(fallback_module)
            if module is not None:
                logger.info(f"✅ Using fallback module '{fallback_module}' for '{primary_module}'")
                return module, f"fallback:{fallback_module}"

        # Try fallback factory if provided
        if fallback_factory:
            try:
                fallback_object = fallback_factory()
                logger.info(f"✅ Using factory fallback for '{primary_module}'")
                return fallback_object, "factory:fallback"
            except Exception as factory_error:
                logger.error(f"❌ Fallback factory also failed for '{primary_module}': {factory_error}")

        # Complete failure
        logger.error(f"❌ All import options exhausted for '{primary_module}'")
        return None, "failed:all_options"

    @contextmanager
    def import_context(self, context_name: str):
        """
        Context manager for tracking import operations.

        Args:
            context_name: Name of the import context for logging
        """
        start_time = time.time()
        logger.debug(f"Starting import context: {context_name}")

        try:
            yield self
        except Exception as e:
            logger.error(f"Import context '{context_name}' failed: {e}")
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            logger.debug(f"Import context '{context_name}' completed in {duration:.2f}s")

    def get_import_diagnostics(self) -> Dict[str, Any]:
        """
        Get comprehensive import diagnostics for debugging.

        Returns:
            Dictionary with import statistics and failure information
        """
        total_imports = len(self.successful_imports) + len(self.failed_imports)
        success_rate = len(self.successful_imports) / total_imports if total_imports > 0 else 0

        return {
            "total_imports": total_imports,
            "successful_imports": len(self.successful_imports),
            "failed_imports": len(self.failed_imports),
            "success_rate": success_rate,
            "successful_modules": self.successful_imports.copy(),
            "failed_modules": list(self.failed_imports.keys()),
            "import_times": self.import_times.copy(),
            "retry_counts": self.retry_counts.copy(),
            "failure_details": {
                module: str(error) for module, error in self.failed_imports.items()
            }
        }

    def log_import_summary(self) -> None:
        """Log comprehensive import summary for debugging Issue #1278."""
        diagnostics = self.get_import_diagnostics()

        logger.info("=" * 60)
        logger.info("IMPORT DEPENDENCY SUMMARY - Issue #1278 Diagnostics")
        logger.info("=" * 60)
        logger.info(f"Total imports attempted: {diagnostics['total_imports']}")
        logger.info(f"Successful imports: {diagnostics['successful_imports']}")
        logger.info(f"Failed imports: {diagnostics['failed_imports']}")
        logger.info(f"Success rate: {diagnostics['success_rate']:.1%}")

        if diagnostics['successful_modules']:
            logger.info("✅ Successful modules:")
            for module in diagnostics['successful_modules']:
                import_time = diagnostics['import_times'].get(module, 0)
                retry_count = diagnostics['retry_counts'].get(module, 0)
                logger.info(f"  - {module} ({import_time:.2f}s, {retry_count} retries)")

        if diagnostics['failed_modules']:
            logger.warning("❌ Failed modules:")
            for module in diagnostics['failed_modules']:
                import_time = diagnostics['import_times'].get(module, 0)
                retry_count = diagnostics['retry_counts'].get(module, 0)
                error = diagnostics['failure_details'].get(module, "Unknown error")
                logger.warning(f"  - {module} ({import_time:.2f}s, {retry_count} retries): {error}")

        logger.info("=" * 60)


def resilient_import(module_name: str, fallback_modules: Optional[List[str]] = None,
                    fallback_factory: Optional[Callable] = None) -> Tuple[Optional[Any], str]:
    """
    Convenient function for resilient module importing.

    Args:
        module_name: Primary module to import
        fallback_modules: Optional list of fallback modules
        fallback_factory: Optional factory function for fallback

    Returns:
        Tuple of (imported_object, source_description)
    """
    manager = ImportDependencyManager()

    if fallback_modules or fallback_factory:
        return manager.import_with_fallback(
            module_name,
            fallback_modules or [],
            fallback_factory
        )
    else:
        module, error = manager.safe_import(module_name)
        if module is not None:
            return module, f"direct:{module_name}"
        else:
            return None, f"failed:{module_name}"


def import_auth_service_resilient():
    """
    Import auth_service components with Issue #1278 resilience.

    This function specifically handles the auth_service import issues
    that were causing container startup failures.

    Returns:
        Dictionary with auth_service components or fallbacks
    """
    logger.info("Attempting resilient auth_service import for Issue #1278...")

    manager = ImportDependencyManager()
    auth_components = {}

    # Try to import auth service core components
    auth_service_modules = [
        "auth_service.auth_core.config",
        "auth_service.auth_core.auth_environment",
        "auth_service.auth_core.services.auth_service",
    ]

    for module_name in auth_service_modules:
        with manager.import_context(f"auth_service_import:{module_name}"):
            module, error = manager.safe_import(module_name, retry_count=2, retry_delay=0.5)

            if module is not None:
                component_name = module_name.split(".")[-1]
                auth_components[component_name] = module
                logger.info(f"✅ Auth service component '{component_name}' imported successfully")
            else:
                logger.warning(f"❌ Auth service component '{module_name}' import failed: {error}")

    # Log diagnostics
    manager.log_import_summary()

    return {
        "components": auth_components,
        "diagnostics": manager.get_import_diagnostics(),
        "import_successful": len(auth_components) > 0,
    }


# Create global import manager instance
_global_import_manager = ImportDependencyManager()


def get_import_manager() -> ImportDependencyManager:
    """Get the global import dependency manager instance."""
    return _global_import_manager


def log_startup_import_diagnostics():
    """Log startup import diagnostics for Issue #1278 debugging."""
    global _global_import_manager
    _global_import_manager.log_import_summary()