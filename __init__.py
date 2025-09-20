"""
ZEN - Multi-Instance Claude Orchestrator

A service for orchestrating multiple Claude Code instances in parallel.
Enhanced with comprehensive telemetry and observability.
"""

__version__ = "1.0.3"
__author__ = "Netra Systems"

# Import logging first to avoid NameError in except block
import logging

from .zen_orchestrator import ClaudeInstanceOrchestrator, InstanceConfig, InstanceStatus

# Initialize telemetry on import (respects ZEN_TELEMETRY_DISABLED)
try:
    from .telemetry import telemetry_manager
    import asyncio
    import threading

    logger = logging.getLogger(__name__)

    def _initialize_telemetry():
        """Initialize telemetry in background thread"""
        try:
            # Create new event loop for telemetry initialization
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Initialize telemetry
            success = loop.run_until_complete(telemetry_manager.initialize())

            if success:
                logger.debug("Zen telemetry initialized successfully")
            else:
                logger.debug("Zen telemetry disabled or failed to initialize")

        except Exception as e:
            logger.debug(f"Telemetry initialization error: {e}")
        finally:
            try:
                loop.close()
            except:
                pass

    # Initialize telemetry in background thread to avoid blocking import
    if telemetry_manager.get_config().enabled:
        init_thread = threading.Thread(target=_initialize_telemetry, daemon=True)
        init_thread.start()

except ImportError as e:
    # Telemetry dependencies not available
    logger = logging.getLogger(__name__)
    logger.debug(f"Telemetry not available: {e}")

__all__ = ["ClaudeInstanceOrchestrator", "InstanceConfig", "InstanceStatus"]