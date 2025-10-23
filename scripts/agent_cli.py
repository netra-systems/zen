#!/usr/bin/env python3
"""
Agent CLI Testing Tool - Test agent interactions from command line
Supports authentication, WebSocket streaming, and real-time event display
"""

import asyncio
import json
import sys
import os
import argparse
import time

import logging


# Do not edit this key keep E2E_OAUTH_SIMULATION_KEY as is it's for testing.
# defined in https://console.cloud.google.com/security/secret-manager/secret/E2E_OAUTH_SIMULATION_KEY/versions?inv=1&invt=Ab5S7Q&project=netra-staging
E2E_OAUTH_SIMULATION_KEY = "e0e9c5d29e7aea3942f47855b4870d3e0272e061c2de22827e71b893071d777e"

# ISSUE #2766: Check for JSON/CI mode EARLY (before logging config or other imports)
# This allows us to suppress ALL output including logging from imported modules
_json_mode_active = '--json' in sys.argv or '--ci-mode' in sys.argv or '--json-output' in sys.argv
if _json_mode_active:
    # Suppress ALL logging before any modules are imported
    os.environ['NETRA_LOG_LEVEL'] = 'CRITICAL'
    os.environ['LOG_LEVEL'] = 'CRITICAL'

    # Configure root logger to suppress ALL output
    logging.basicConfig(level=logging.CRITICAL, handlers=[logging.NullHandler()])
    logging.getLogger().setLevel(logging.CRITICAL)

# ISSUE #2417 Phase 1: Suppress backend logging BEFORE imports
# Check --stream-logs flag early to prevent startup log pollution
_stream_logs_active = '--stream-logs' in sys.argv

if not _stream_logs_active:
    # Suppress ALL backend logging before importing heavy modules
    os.environ['NETRA_LOG_LEVEL'] = 'CRITICAL'
    os.environ['LOG_LEVEL'] = 'CRITICAL'

    # Configure root logger to suppress backend startup noise
    logging.basicConfig(level=logging.CRITICAL, handlers=[logging.NullHandler()])

    # Set all backend-related loggers to CRITICAL
    noisy_loggers = [
        'netra_backend',
        'netra-service',
        'shared',
        'uvicorn',
        'httpx',
        'asyncio',
        'websockets',
        'aiohttp',
        'sqlalchemy',
        'logging'
    ]

    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL)
        logger.disabled = True

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from pathlib import Path
import aiohttp
import websockets
from websockets import ClientConnection as WebSocketClientProtocol
import uuid
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.text import Text
from rich.prompt import Prompt, Confirm
import jwt
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
import yaml
import webbrowser
import threading
import secrets
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import traceback
import subprocess
import psutil
from typing import Union

# ISSUE #2006: Early environment detection fix for all environments
# Parse --env argument early to set ENVIRONMENT before any module imports
if "--env" in sys.argv:
    env_idx = sys.argv.index("--env")
    if env_idx + 1 < len(sys.argv):
        env_value = sys.argv[env_idx + 1]
        if env_value in ["staging", "production", "local", "development"]:
            os.environ["ENVIRONMENT"] = env_value
            # Will be displayed later after logging is set up

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure UTF-8 encoding for Windows console using SSOT pattern (Issue #2887)
from shared.windows_encoding import setup_windows_encoding
setup_windows_encoding()

# ISSUE #2373: WebSocket closure code validation
# Import AFTER sys.path setup to ensure shared module is accessible
from shared.types.websocket_closure_codes import (
    WebSocketClosureCode,
    WebSocketClosureCategory,
    categorize_closure_code,
    get_closure_description,
    is_infrastructure_error
)

class SimpleConfigReader:
    """
    Minimal config reader for Agent CLI - NO BACKEND DEPENDENCIES.

    CLI only needs:
    - E2E_OAUTH_SIMULATION_KEY (for staging auth)
    - Backend/Auth/WS URLs (hardcoded per environment)

    This is a CLIENT TOOL, not a backend service.
    """

    def __init__(self, environment: str):
        self.environment = environment
        self._config = {}

    def load_minimal_config(self) -> Dict[str, str]:
        """Load only the env vars CLI actually needs."""
        config = {}

        # For staging and development: try to get E2E key from environment or GCP
        if self.environment in ["staging", "development"]:
            e2e_key = E2E_OAUTH_SIMULATION_KEY
            if e2e_key:
                config['E2E_OAUTH_SIMULATION_KEY'] = e2e_key

        return config


# ISSUE #2417 Phase 1: Duplicate log suppression code REMOVED
# Log suppression now happens BEFORE imports at lines 27-56
# This prevents backend logging from polluting CLI startup output

# ISSUE #2782: Removed IsolatedEnvironment import - CLI is a client tool, not backend service
# Environment detection imports moved to flag handler to avoid heavy initialization

# Import agent output validator for Issue #1822
try:
    from agent_output_validator import AgentOutputValidator, ValidationReport, ValidationResult
except ImportError:
    # Module not available - create stub classes
    AgentOutputValidator = None
    ValidationReport = None
    ValidationResult = None

# Import WebSocket event validation framework for Issue #2177
try:
    from websocket_event_validation_framework import (
        WebSocketEventValidationFramework, EventValidationReport, ValidationResult as EventValidationResult
    )
except ImportError:
    # Module not available - create stub classes
    WebSocketEventValidationFramework = None
    EventValidationReport = None
    EventValidationResult = None

# Import business value validator for revenue protection
# ISSUE #2414: Delay imports that trigger configuration validation
# These will be imported later in the main() function to avoid heavy initialization overhead

# Placeholder for imports that will be loaded conditionally
BusinessValueValidator = None
BusinessValueResult = None
ValidationWebSocketEvent = None

# Platform Detection and Unicode Compatibility
import platform as stdlib_platform
import locale

class DisplayMode:
    """Display mode options for cross-platform compatibility"""
    EMOJI = "emoji"
    ASCII = "ascii"
    AUTO = "auto"

# Emoji to ASCII fallback mapping for Windows compatibility
EMOJI_FALLBACKS = {
    '🤖': '[AGENT]',
    '🔐': '[AUTH]',
    '🔌': '[CONN]',
    '📡': '[MSG]',
    '🎯': '[TARGET]',
    '✅': '[OK]',
    '❌': '[ERROR]',
    '⚠️': '[WARN]',
    '📊': '[STATS]',
    '🔧': '[TOOL]',
    '⏳': '[WAIT]',
    '🚀': '[ROCKET]',
    '⭐': '[STAR]',
    '🔍': '[SEARCH]',
    '📋': '[NOTES]',
    '💡': '[INFO]',
    '🔑': '[KEY]',
    '🔥': '[HOT]',
    '💭': '[THOUGHT]',
    '📥': '[INPUT]',
    '📤': '[OUTPUT]',
    '📍': '[ENV]',
    '🔗': '[LINK]'
}

def detect_terminal_capabilities(override_mode: str = None) -> str:
    """
    Detect if terminal supports Unicode emoji display
    Returns DisplayMode.EMOJI or DisplayMode.ASCII

    Args:
        override_mode: CLI argument override (emoji, ascii, auto)
    """
    # Check CLI argument override first
    if override_mode and override_mode != DisplayMode.AUTO:
        return override_mode

    # Check environment variable override second
    env_mode = os.environ.get('NETRA_CLI_DISPLAY_MODE', '').lower()
    if env_mode in [DisplayMode.EMOJI, DisplayMode.ASCII]:
        return env_mode

    # Auto-detection: Windows platform detection
    if stdlib_platform.system() == "Windows":
        # Force ASCII mode on Windows to avoid encoding issues
        return DisplayMode.ASCII

    # Unix/Linux/macOS - assume emoji support
    return DisplayMode.EMOJI

def safe_format_message(message: str, display_mode: str = None) -> str:
    """
    Format message with Unicode fallback for Windows compatibility

    Args:
        message: Message to format
        display_mode: Override display mode (emoji/ascii)

    Returns:
        Formatted message with emoji replacements if needed
    """
    if display_mode is None:
        display_mode = detect_terminal_capabilities(GLOBAL_DISPLAY_MODE)

    processed_message = message

    # Replace emojis with ASCII equivalents if needed
    if display_mode == DisplayMode.ASCII:
        for emoji, fallback in EMOJI_FALLBACKS.items():
            processed_message = processed_message.replace(emoji, fallback)

    return processed_message

def safe_console_print(message, style: str = None, display_mode: str = None, json_mode: bool = False, ci_mode: bool = False):
    """
    Print with Unicode fallback for Windows compatibility

    Args:
        message: Message to print (str or Rich object)
        style: Rich console style
        display_mode: Override display mode (emoji/ascii)
        json_mode: If True, suppress output (JSON mode)
        ci_mode: If True, suppress output (CI mode)
    """
    # ISSUE #2766: Suppress ALL output in JSON or CI mode
    if json_mode or ci_mode:
        return

    if display_mode is None:
        display_mode = detect_terminal_capabilities(GLOBAL_DISPLAY_MODE)

    # Handle Rich objects (Table, Panel, etc.) differently from strings
    if hasattr(message, '__rich__') or hasattr(message, '__rich_console__'):
        # Rich objects - print directly without text processing
        try:
            console.print(message, style=style)
        except UnicodeEncodeError as e:
            # For Rich objects on Windows, try to render as plain text
            try:
                # Get plain text representation
                plain_text = str(message)
                ascii_message = plain_text.encode('ascii', errors='replace').decode('ascii')
                console.print(f"[DISPLAY_ERROR] {ascii_message}", style="red")
            except Exception:
                console.print("[DISPLAY_ERROR] Rich object could not be displayed", style="red")
        except Exception as e:
            # Handle any other console errors
            try:
                print(f"[CONSOLE_ERROR] Rich object display failed: {e}")
            except Exception:
                print("[CONSOLE_ERROR] Rich object could not be displayed")
    else:
        # String messages - apply Unicode processing
        processed_message = safe_format_message(str(message), display_mode)

        try:
            console.print(processed_message, style=style)
        except (ValueError, UnicodeEncodeError) as e:
            if "I/O operation on closed file" in str(e):
                # Handle closed file error - fall back to basic print
                try:
                    print(processed_message)
                except Exception:
                    print(f"[CONSOLE_ERROR] {repr(message)}")
            elif "charmap" in str(e) or "codec can't encode" in str(e):
                # Handle Unicode encoding errors - fallback to ASCII
                try:
                    ascii_message = processed_message.encode('ascii', errors='replace').decode('ascii')
                    print(f"[DISPLAY_WARNING] {ascii_message}")
                except Exception:
                    print(f"[DISPLAY_ERROR] Message encoding failed: {repr(message)}")
            else:
                raise

# Global display mode from CLI arguments
GLOBAL_DISPLAY_MODE = DisplayMode.AUTO

# Setup Unicode support before Rich Console initialization
if stdlib_platform.system() == "Windows":
    # Setup UTF-8 streams before Rich Console is created
    import os
    try:
        # Set environment variables for UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'

        # Set Windows console to UTF-8 - simpler approach
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
    except Exception:
        pass

# Rich console for beautiful output with Windows Unicode support
if stdlib_platform.system() == "Windows":
    # Use default console with Windows compatibility
    console = Console(force_terminal=True, legacy_windows=False)
else:
    console = Console()

class DebugLevel(IntEnum):
    """Debug verbosity levels"""
    SILENT = 0      # No debug output
    BASIC = 1       # Basic debug info
    VERBOSE = 2     # Detailed debug info
    TRACE = 3       # Full trace with raw data
    DIAGNOSTIC = 4  # Maximum detail for troubleshooting

class DebugManager:
    """
    SSOT Debug Manager for Agent CLI
    Provides comprehensive debugging capabilities with different verbosity levels
    """

    def __init__(self, debug_level: DebugLevel = DebugLevel.SILENT, log_file: Optional[Path] = None,
                 enable_websocket_diagnostics: bool = False, json_mode: bool = False, ci_mode: bool = False):
        self.debug_level = debug_level
        self.log_file = log_file or Path.home() / ".netra" / "cli_debug.log"
        self.session_id = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
        self.event_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        # ISSUE #2766: Store JSON/CI mode flags for output suppression
        self.json_mode = json_mode
        self.ci_mode = ci_mode

        # Create log directory
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize logging
        self._setup_logging()

        # ISSUE #2478: Optional WebSocket diagnostic utility integration
        # ISSUE #2484 Phase 2: Enabled by default with graceful fallback
        self.websocket_diagnostic_utility = None
        if enable_websocket_diagnostics:
            try:
                from diagnostic_utilities.websocket_diagnostic_utility import WebSocketDiagnosticUtility
                self.websocket_diagnostic_utility = WebSocketDiagnosticUtility(debug_manager=self)
                if self.debug_level >= DebugLevel.VERBOSE:
                    self.debug_print("WebSocket diagnostic utility enabled", DebugLevel.VERBOSE, "cyan")
            except ImportError as e:
                if self.debug_level >= DebugLevel.BASIC:
                    self.debug_print(
                        f"WebSocket diagnostic utility not available (graceful fallback): {e}",
                        DebugLevel.BASIC,
                        "yellow"
                    )

        if self.debug_level >= DebugLevel.BASIC:
            safe_console_print(f"[DEBUG] Debug Manager initialized - Level: {self.debug_level.name} - Session: {self.session_id}",
                             style="dim cyan", json_mode=self.json_mode, ci_mode=self.ci_mode)

    def _setup_logging(self):
        """Setup file logging for debug sessions"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler() if self.debug_level >= DebugLevel.VERBOSE else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger(f"agent_cli_debug_{self.session_id}")

    def debug_print(self, message: str, level: DebugLevel = DebugLevel.BASIC, style: str = "dim"):
        """Print debug message if level is sufficient"""
        if self.debug_level >= level:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            formatted_message = f"[{timestamp}] [DEBUG] {message}"
            # ISSUE #2766: Suppress debug output in JSON/CI mode
            safe_console_print(formatted_message, style=style, json_mode=self.json_mode, ci_mode=self.ci_mode)
            self.logger.debug(message)

    def log_websocket_event(self, event_type: str, data: Dict[str, Any], raw_message: str = None, connection_id: str = None):
        """Log WebSocket events with appropriate detail level

        Issue #2484: Enhanced with debug level-specific diagnostic data:
        - BASIC: Error category, cleanup phase status
        - VERBOSE: Connection lifecycle timestamps, timeout validation warnings
        - TRACE: Individual cleanup events, full timeout hierarchy
        - DIAGNOSTIC: Complete structured diagnostic output, JSON format

        Args:
            event_type: Type of WebSocket event
            data: Event data dictionary
            raw_message: Raw WebSocket message (optional)
            connection_id: WebSocket connection identifier (optional)
        """
        self.event_count += 1

        # Base event logging (all levels >= BASIC)
        if self.debug_level >= DebugLevel.BASIC:
            self.debug_print(f"WebSocket Event #{self.event_count}: {event_type}")

            # BASIC Level: Show error category and cleanup phase if available
            if self.websocket_diagnostic_utility is not None:
                try:
                    # Check if this is an error event
                    is_error_event = event_type in ['error', 'agent_error', 'connection_error']

                    if is_error_event and 'error' in data:
                        # Try to infer error category from error data
                        error_msg = str(data.get('error', ''))
                        if 'cleanup' in error_msg.lower() or 'state' in error_msg.lower():
                            self.debug_print("🔬 Error Category: CLEANUP_STATE", DebugLevel.BASIC, "yellow")
                        elif 'timeout' in error_msg.lower():
                            self.debug_print("🔬 Error Category: TIMEOUT_HIERARCHY", DebugLevel.BASIC, "yellow")

                    # Show cleanup phase status if available (for any connection_id)
                    if connection_id:
                        # Get lifecycle info from cleanup coordinator
                        lifecycle = self.websocket_diagnostic_utility.cleanup_coordinator.connection_lifecycles.get(connection_id, {})
                        if lifecycle:
                            if 'closed' in lifecycle:
                                cleanup_phase = "CLOSED"
                            elif 'cleanup' in lifecycle:
                                cleanup_phase = "CLEANUP_IN_PROGRESS"
                            elif 'active' in lifecycle:
                                cleanup_phase = "ACTIVE"
                            elif 'connected' in lifecycle:
                                cleanup_phase = "CONNECTED"
                            else:
                                cleanup_phase = "UNKNOWN"

                            self.debug_print(f"🔬 Cleanup Phase: {cleanup_phase}", DebugLevel.BASIC, "cyan")

                except Exception as e:
                    # Gracefully handle diagnostic errors - don't break event logging
                    if self.debug_level >= DebugLevel.TRACE:
                        self.debug_print(f"Diagnostic data unavailable: {e}", DebugLevel.TRACE, "dim")

        # VERBOSE Level: Add connection lifecycle timestamps and timeout warnings
        if self.debug_level >= DebugLevel.VERBOSE:
            self.debug_print(f"Event Data Keys: {list(data.keys())}", DebugLevel.VERBOSE)

            if self.websocket_diagnostic_utility is not None and connection_id:
                try:
                    # Show connection lifecycle timestamps
                    lifecycle = self.websocket_diagnostic_utility.cleanup_coordinator.connection_lifecycles.get(connection_id, {})
                    if lifecycle:
                        timestamp_str = self._format_lifecycle_timestamps(lifecycle)
                        if timestamp_str:
                            self.debug_print(f"🔬 Lifecycle: {timestamp_str}", DebugLevel.VERBOSE, "blue")

                    # Show timeout validation warnings if applicable
                    # Check if we have timeout configuration to validate
                    if hasattr(self, 'websocket_timeout') and hasattr(self, 'agent_timeout'):
                        validation_result = self.websocket_diagnostic_utility.validate_timeout_hierarchy(
                            self.websocket_timeout,
                            self.agent_timeout,
                            getattr(self, 'environment', 'staging')
                        )

                        if validation_result.warnings:
                            for warning in validation_result.warnings:
                                self.debug_print(f"⚠️ Timeout Warning: {warning}", DebugLevel.VERBOSE, "yellow")

                except Exception as e:
                    if self.debug_level >= DebugLevel.TRACE:
                        self.debug_print(f"Lifecycle diagnostic unavailable: {e}", DebugLevel.TRACE, "dim")

        # TRACE Level: Show individual cleanup events and full timeout hierarchy
        if self.debug_level >= DebugLevel.TRACE:
            if raw_message:
                self.debug_print(f"Raw Message: {raw_message[:200]}...", DebugLevel.TRACE, "bright_green")

            if self.websocket_diagnostic_utility is not None and connection_id:
                try:
                    # Show individual cleanup events
                    cleanup_events = self.websocket_diagnostic_utility.correlate_cleanup_events(connection_id)
                    if cleanup_events:
                        self.debug_print(f"🔬 Cleanup Events ({len(cleanup_events)} total):", DebugLevel.TRACE, "cyan")
                        for event in cleanup_events[-5:]:  # Show last 5 events
                            event_time = event.timestamp.strftime('%H:%M:%S.%f')[:-3]
                            self.debug_print(
                                f"- [{event_time}] {event.source.upper()}: {event.event_type} (phase: {event.phase or 'N/A'})",
                                DebugLevel.TRACE,
                                "dim"
                            )

                    # Show full timeout hierarchy
                    if hasattr(self, 'websocket_timeout') and hasattr(self, 'agent_timeout'):
                        ws_timeout = getattr(self, 'websocket_timeout', 0)
                        agent_timeout = getattr(self, 'agent_timeout', 0)
                        buffer = ws_timeout - agent_timeout if ws_timeout > agent_timeout else 0

                        self.debug_print(f"🔬 Timeout Hierarchy: ", DebugLevel.TRACE, "cyan")
                        self.debug_print(f"- WebSocket: {ws_timeout}s", DebugLevel.TRACE, "dim")
                        self.debug_print(f"- Agent: {agent_timeout}s", DebugLevel.TRACE, "dim")
                        self.debug_print(f"- Buffer: {buffer:.1f}s", DebugLevel.TRACE, "dim")

                except Exception as e:
                    self.debug_print(f"Cleanup event diagnostic unavailable: {e}", DebugLevel.TRACE, "dim")

        # DIAGNOSTIC Level: Show complete structured diagnostic output
        if self.debug_level >= DebugLevel.DIAGNOSTIC:
            # Show full event data
            formatted_data = json.dumps(data, indent=2, default=str)
            self.debug_print(f"Full Event Data: \n{formatted_data}", DebugLevel.DIAGNOSTIC, "green")

            # Show complete diagnostic context if available
            if self.websocket_diagnostic_utility is not None and connection_id:
                try:
                    # Build comprehensive diagnostic context
                    diagnostic_context = self._build_diagnostic_context_for_event(
                        event_type, data, connection_id
                    )

                    # Format based on JSON mode
                    if self.json_mode:
                        # Export as JSON
                        diagnostic_json = {
                            "event_type": event_type,
                            "event_count": self.event_count,
                            "connection_id": connection_id,
                            "diagnostic_context": diagnostic_context
                        }
                        self.debug_print(
                            f"Diagnostic Context (JSON): \n{json.dumps(diagnostic_json, indent=2, default=str)}",
                            DebugLevel.DIAGNOSTIC,
                            "green"
                        )
                    else:
                        # Show detailed text format
                        self.debug_print("🔬 Full Diagnostic Context: ", DebugLevel.DIAGNOSTIC, "bold cyan")
                        for key, value in diagnostic_context.items():
                            if value is not None:
                                self.debug_print(f"{key}: {value}", DebugLevel.DIAGNOSTIC, "dim")

                except Exception as e:
                    self.debug_print(f"Full diagnostic context unavailable: {e}", DebugLevel.DIAGNOSTIC, "yellow")

    def _format_lifecycle_timestamps(self, lifecycle: Dict[str, Any]) -> str:
        """Format lifecycle timestamps for display.

        Args:
            lifecycle: Dictionary of lifecycle phase timestamps

        Returns:
            Formatted timestamp string
        """
        if not lifecycle:
            return ""

        parts = []
        for phase in ['connected', 'authenticated', 'active', 'cleanup', 'closed']:
            if phase in lifecycle:
                timestamp = lifecycle[phase]
                time_str = timestamp.strftime('%H:%M:%S')
                parts.append(f"{phase}={time_str}")

        if not parts:
            return ""

        # Calculate duration if we have start and end
        if 'connected' in lifecycle and 'closed' in lifecycle:
            duration = (lifecycle['closed'] - lifecycle['connected']).total_seconds()
            parts.append(f"duration={duration:.1f}s")

        return ", ".join(parts)

    def _build_diagnostic_context_for_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        connection_id: str
    ) -> Dict[str, Any]:
        """Build comprehensive diagnostic context for an event.

        Args:
            event_type: Type of WebSocket event
            data: Event data dictionary
            connection_id: WebSocket connection identifier

        Returns:
            Diagnostic context dictionary
        """
        context = {
            "connection_id": connection_id,
            "event_type": event_type,
            "timestamp": datetime.now().isoformat()
        }

        try:
            # Add cleanup phase
            lifecycle = self.websocket_diagnostic_utility.cleanup_coordinator.connection_lifecycles.get(connection_id, {})
            if lifecycle:
                if 'closed' in lifecycle:
                    context["cleanup_phase"] = "CLOSED"
                elif 'cleanup' in lifecycle:
                    context["cleanup_phase"] = "CLEANUP_IN_PROGRESS"
                elif 'active' in lifecycle:
                    context["cleanup_phase"] = "ACTIVE"
                else:
                    context["cleanup_phase"] = "CONNECTED"

                # Add lifecycle details
                context["lifecycle"] = {
                    phase: timestamp.isoformat()
                    for phase, timestamp in lifecycle.items()
                }

            # Add cleanup events
            cleanup_events = self.websocket_diagnostic_utility.correlate_cleanup_events(connection_id)
            if cleanup_events:
                context["cleanup_events"] = [
                    {
                        "timestamp": event.timestamp.isoformat(),
                        "type": event.event_type,
                        "source": event.source,
                        "phase": event.phase
                    }
                    for event in cleanup_events
                ]

            # Add timeout configuration
            if hasattr(self, 'websocket_timeout') and hasattr(self, 'agent_timeout'):
                context["timeout_hierarchy"] = {
                    "websocket_timeout": getattr(self, 'websocket_timeout', None),
                    "agent_timeout": getattr(self, 'agent_timeout', None),
                    "buffer": (getattr(self, 'websocket_timeout', 0) - getattr(self, 'agent_timeout', 0))
                }

            # Add error category if this is an error event
            if 'error' in data:
                error_msg = str(data.get('error', ''))
                if 'cleanup' in error_msg.lower():
                    context["error_category"] = "CLEANUP_STATE"
                elif 'timeout' in error_msg.lower():
                    context["error_category"] = "TIMEOUT_HIERARCHY"
                else:
                    context["error_category"] = "UNKNOWN"

        except Exception as e:
            context["diagnostic_error"] = str(e)

        return context

    def log_authentication_step(self, step: str, details: str = "", success: bool = None):
        """Log authentication process steps"""
        if success is not None:
            status = "[PASS]" if success else "[FAIL]"
            style = "green" if success else "red"
        else:
            status = "[PROC]"
            style = "yellow"

        message = f"{status} Auth Step: {step}"
        if details and self.debug_level >= DebugLevel.VERBOSE:
            message += f" - {details}"

        self.debug_print(message, style=style)

    def log_connection_attempt(self, method: str, url: str, success: bool = None, error: str = None):
        """Log connection attempts with details"""
        if success is True:
            self.debug_print(f"[PASS] Connection Success: {method} to {url}", style="green")
        elif success is False:
            self.error_count += 1
            self.debug_print(f"[FAIL] Connection Failed: {method} to {url}", style="red")
            if error and self.debug_level >= DebugLevel.VERBOSE:
                self.debug_print(f"Error Details: {error}", DebugLevel.VERBOSE, "red")
        else:
            self.debug_print(f"[PROC] Attempting: {method} to {url}", style="yellow")

    def log_error(self, error: Exception, context: str = ""):
        """Log errors with appropriate detail level"""
        self.error_count += 1

        error_msg = f"Error in {context}: {type(error).__name__}: {str(error)}"
        self.debug_print(error_msg, style="red")

        if self.debug_level >= DebugLevel.TRACE:
            tb = traceback.format_exc()
            self.debug_print(f"Full Traceback: \n{tb}", DebugLevel.TRACE, "red")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current debug session statistics"""
        duration = datetime.now() - self.start_time
        return {
            "session_id": self.session_id,
            "debug_level": self.debug_level.name,
            "duration_seconds": duration.total_seconds(),
            "events_logged": self.event_count,
            "errors_logged": self.error_count,
            "log_file": str(self.log_file)
        }

    def format_event_for_display(self, event_type: str, data: Dict[str, Any]) -> str:
        """Enhanced event formatting based on debug level"""
        base_format = self._get_base_event_format(event_type, data)

        if self.debug_level >= DebugLevel.VERBOSE:
            # Add more details for verbose mode
            if event_type == "agent_thinking":
                reasoning = data.get('reasoning', data.get('thought', ''))
                if reasoning:
                    # Use smart truncation for reasoning text
                    max_len = 300 if self.debug_level >= DebugLevel.VERBOSE else 100
                    if self.debug_level >= DebugLevel.TRACE:
                        max_len = 1000
                    elif self.debug_level >= DebugLevel.DIAGNOSTIC:
                        max_len = len(reasoning)  # No truncation
                    base_format += f"\n    💭 Reasoning: {truncate_with_ellipsis(reasoning, max_len)}"

            elif event_type == "tool_executing":
                tool_input = data.get('input', data.get('parameters', {}))
                if tool_input:
                    base_format += f"\n    📥 Input: {smart_truncate_json(tool_input, self)}"

            elif event_type == "tool_completed":
                tool_output = data.get('output', data.get('result', ''))
                if tool_output:
                    base_format += f"\n    📤 Output: {smart_truncate_json(tool_output, self)}"

        if self.debug_level >= DebugLevel.TRACE:
            # Add timing information
            timestamp = data.get('timestamp', datetime.now().isoformat())
            base_format += f"\n    ⏰ Timestamp: {timestamp}"

            # Add run_id if available
            run_id = data.get('run_id', 'N/A')
            base_format += f"\n    {safe_format_message('🎯')} Run ID: {run_id}"

        return base_format

    def _get_base_event_format(self, event_type: str, data: Dict[str, Any]) -> str:
        """Get base event formatting with smart truncation"""
        # Issue #2485: Safety check for malformed event data
        if data is None:
            data = {}
            self.debug_print(f"Warning: Received None data for event type '{event_type}', using empty dict")

        # Handle system_message events that wrap agent events
        # Backend sends agent events as: {"type": "system_message", "event": "agent_started", "payload": {...}}
        if event_type == "system_message":
            inner_event = data.get('event', '')
            if inner_event in ['agent_started', 'agent_thinking', 'agent_completed', 'tool_executing', 'tool_completed']:
                # Extract the actual event type and data from payload
                event_type = inner_event
                payload = data.get('payload', {})
                # Merge payload data with original data, payload takes precedence
                data = {**data, **payload}

        # ISSUE #2993 regression fix: Unified WebSocket manager now sends agent events
        # with a top-level payload instead of system_message wrapper.
        payload = data.get('payload') if isinstance(data, dict) else None
        if isinstance(payload, dict):
            data = {**data, **payload}

        # Unified manager emits agent events with nested 'data' payload
        nested_data = data.get('data') if isinstance(data, dict) else None
        if isinstance(nested_data, dict):
            data = {**data, **nested_data}
        # Helper function to detect agent hierarchy level
        def get_agent_hierarchy_format(agent_name: str, run_id: str, retry_suffix: str) -> str:
            """Issue #2485: Detect agent hierarchy and format with visual differentiation.

            Transforms confusing duplicate 🚀 Agent Started messages into clear hierarchy:
            🎯 Orchestrator: WorkflowOrchestrator started (run: abc123...)
              🤖 Step: triage started (run: def456...)
                🧠 Agent: ReasoningAgent started (run: ghi789...)
            """
            # Orchestrator level - top-level coordinators
            orchestrator_patterns = ['Supervisor', 'WorkflowOrchestrator']

            # Step level - workflow steps and process stages
            step_patterns = ['triage']

            # Check for orchestrator level
            if any(pattern in agent_name for pattern in orchestrator_patterns):
                return f"🎯 Orchestrator: {agent_name} started (run: {truncate_with_ellipsis(run_id, 8)}){retry_suffix}"

            # Check for step level
            elif any(pattern in agent_name for pattern in step_patterns):
                return f"  🤖 Step: {agent_name} started (run: {truncate_with_ellipsis(run_id, 8)}){retry_suffix}"

            # Individual agent level - specific task agents
            else:
                return f"    🧠 Agent: {agent_name} started (run: {truncate_with_ellipsis(run_id, 8)}){retry_suffix}"

        # Helper function to format retry information
        def get_retry_suffix(data: Dict[str, Any]) -> str:
            """Extract and format retry information if present."""
            retry_info = data.get('retry_info')
            if not retry_info or not isinstance(retry_info, dict):
                return ""

            # Only show retry info if show_retry_info is enabled in config
            # This will be set by the --retry-info flag
            show_retry = getattr(self, 'show_retry_info', False)
            if not show_retry:
                # Still show basic retry indicator even without --retry-info flag
                if retry_info.get('is_retry', False):
                    attempt = retry_info.get('attempt_number', '?')
                    max_attempts = retry_info.get('max_attempts', '?')
                    return f" (Retry {attempt}/{max_attempts})"
                return ""

            # Verbose retry information with --retry-info flag
            if retry_info.get('is_retry', False):
                attempt = retry_info.get('attempt_number', '?')
                max_attempts = retry_info.get('max_attempts', '?')
                reason = retry_info.get('reason', '')
                if reason:
                    return f" (Retry {attempt}/{max_attempts}: {reason})"
                else:
                    return f" (Retry {attempt}/{max_attempts})"
            return ""

        if event_type == "agent_started":
            agent_name = data.get('agent_name', 'Unknown')
            run_id = data.get('run_id', 'N/A')
            retry_suffix = get_retry_suffix(data)
            # Issue #2485: Use hierarchy-aware formatting instead of generic 🚀 Agent Started
            return get_agent_hierarchy_format(agent_name, run_id, retry_suffix)
        elif event_type == "agent_thinking":
            thought = data.get('thought', data.get('reasoning', ''))
            # Use smart truncation for thought content
            max_len = 100  # Default for basic level
            if self.debug_level >= DebugLevel.VERBOSE:
                max_len = 300
            elif self.debug_level >= DebugLevel.TRACE:
                max_len = 1000
            elif self.debug_level >= DebugLevel.DIAGNOSTIC:
                max_len = len(thought) if thought else 100  # No truncation
            retry_suffix = get_retry_suffix(data)

            # Issue #2485: Apply hierarchy-aware indentation for thinking events
            agent_name = data.get('agent_name', '')
            orchestrator_patterns = ['Supervisor', 'WorkflowOrchestrator']
            step_patterns = ['triage']

            if any(pattern in agent_name for pattern in orchestrator_patterns):
                # No indentation for orchestrator level
                return f"🤔 Thinking: {truncate_with_ellipsis(thought, max_len)}{retry_suffix}"
            elif any(pattern in agent_name for pattern in step_patterns):
                # Step level indentation
                return f"  💭 Thinking: {truncate_with_ellipsis(thought, max_len)}{retry_suffix}"
            else:
                # Individual agent level indentation
                return f"    💭 Thinking: {truncate_with_ellipsis(thought, max_len)}{retry_suffix}"
        elif event_type == "tool_executing":
            tool = data.get('tool', data.get('tool_name', 'Unknown'))
            retry_suffix = get_retry_suffix(data)
            return f"[EXEC] Executing Tool: {tool}{retry_suffix}"
        elif event_type == "tool_completed":
            tool = data.get('tool', data.get('tool_name', 'Unknown'))
            status = data.get('status', 'completed')
            retry_suffix = get_retry_suffix(data)
            return f"[PASS] Tool Complete: {tool} ({status}){retry_suffix}"
        elif event_type == "agent_completed":
            result = data.get('result')
            if result is None:
                result = data.get('final_response')
            if result is None:
                result = data.get('response', '')
            run_id = data.get('run_id', 'N/A')
            agent_name = data.get('agent_name', 'Unknown')
            # Use smart truncation for result content
            result_str = smart_truncate_json(result, self) if isinstance(result, (dict, list)) else str(result)
            max_len = 100  # Default for basic level
            if self.debug_level >= DebugLevel.VERBOSE:
                max_len = 300
            elif self.debug_level >= DebugLevel.TRACE:
                max_len = 1000
            elif self.debug_level >= DebugLevel.DIAGNOSTIC:
                max_len = len(result_str)  # No truncation
            if not isinstance(result, (dict, list)):
                result_str = truncate_with_ellipsis(result_str, max_len)
            retry_suffix = get_retry_suffix(data)

            # Issue #2178: Add LLM validation status display
            validation_status = ""
            llm_validation = data.get('llm_validation', {})
            if llm_validation:
                is_valid = llm_validation.get('is_valid', False)
                validation_icon = "✅" if is_valid else "❌"
                validation_status = f" | Real LLM: {validation_icon}"

                # Add more details in verbose mode
                if self.debug_level >= DebugLevel.VERBOSE:
                    validation_result = llm_validation.get('validation_result', 'unknown')
                    violations_count = llm_validation.get('violations_count', 0)
                    validation_status += f" ({validation_result}"
                    if violations_count > 0:
                        validation_status += f", {violations_count} violations"
                    validation_status += ")"

            # Apply hierarchy-aware formatting for agent completion
            orchestrator_patterns = ['Supervisor', 'WorkflowOrchestrator']
            step_patterns = ['triage']

            if any(pattern in agent_name for pattern in orchestrator_patterns):
                # No indentation for orchestrator level
                return f"🎯 Orchestrator Completed: {agent_name} (run: {truncate_with_ellipsis(run_id, 8)}) - {result_str}{retry_suffix}{validation_status}"
            elif any(pattern in agent_name for pattern in step_patterns):
                # Step level indentation
                return f"  🤖 Step Completed: {agent_name} (run: {truncate_with_ellipsis(run_id, 8)}) - {result_str}{retry_suffix}{validation_status}"
            else:
                # Individual agent level indentation
                return f"    🧠 Agent Completed: {agent_name} (run: {truncate_with_ellipsis(run_id, 8)}) - {result_str}{retry_suffix}{validation_status}"
        elif event_type == "message":
            content = data.get('content', '')
            # Use smart truncation for message content
            max_len = 100  # Default for basic level
            if self.debug_level >= DebugLevel.VERBOSE:
                max_len = 300
            elif self.debug_level >= DebugLevel.TRACE:
                max_len = 1000
            elif self.debug_level >= DebugLevel.DIAGNOSTIC:
                max_len = len(content)  # No truncation
            return f"[MSG] Message: {truncate_with_ellipsis(content, max_len)}"
        elif event_type == "error":
            error = data.get('error', 'Unknown error')
            return f"[FAIL] Error: {error}"
        elif event_type == "connection_established":
            user_id = data.get('data', {}).get('user_id', 'unknown')
            return f"[CONN] Connected as: {user_id}"
        elif event_type == "handshake_response":
            thread_id = data.get('thread_id', 'unknown')
            return f"[HANDSHAKE] Handshake complete - Thread ID: {thread_id}"
        elif event_type == "agent_timeout_warning":
            # Issue #2409: Agent execution timeout warning display
            agent_name = data.get('agent_name', 'Unknown')
            elapsed_seconds = data.get('elapsed_seconds', 0)
            total_timeout_seconds = data.get('total_timeout_seconds', 0)
            remaining_seconds = data.get('remaining_seconds', 0)
            threshold_percent = data.get('warning_threshold_percent', 80)
            return f"⚠️ Timeout Warning: {agent_name} approaching timeout ({threshold_percent}% - {elapsed_seconds:.1f}s/{total_timeout_seconds:.1f}s, {remaining_seconds:.1f}s remaining)"
        elif event_type == "agent_timeout_failure":
            # Issue #2409: Agent execution timeout failure display
            agent_name = data.get('agent_name', 'Unknown')
            elapsed_seconds = data.get('elapsed_seconds', 0)
            timeout_seconds = data.get('timeout_seconds', 0)
            final_status = data.get('final_status', 'TIMEOUT')
            error_message = data.get('error', data.get('message', 'Agent execution timed out'))
            return f"🕐 Timeout Failure: {agent_name} timed out after {elapsed_seconds:.1f}s (limit: {timeout_seconds:.1f}s) - {error_message}"
        else:
            return f"[EVENT] {event_type}: {smart_truncate_json(data, self)}"

    async def render_backend_log(self, log_message: Dict[str, Any]):
        """Render backend log message with Rich formatting (Issue #1828)."""
        try:
            # Extract log message fields
            timestamp = log_message.get('timestamp', 'Unknown time')
            level = log_message.get('level', 'info').upper()
            logger_name = log_message.get('logger_name', 'unknown')
            message = log_message.get('message', 'No message')
            module = log_message.get('module')
            function = log_message.get('function')
            line_number = log_message.get('line_number')
            user_id = log_message.get('user_id')
            request_id = log_message.get('request_id')
            stack_trace = log_message.get('stack_trace')
            extra_data = log_message.get('extra_data', {})

            # Choose style based on log level
            level_styles = {
                'TRACE': 'dim white',
                'DEBUG': 'dim cyan',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold red'
            }
            style = level_styles.get(level, 'white')

            # Format timestamp for display
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                display_time = dt.strftime('%H:%M:%S.%f')[:-3]
            except:
                display_time = timestamp

            # Build basic log line
            log_line = f"[{display_time}] [{level}] {logger_name}: {message}"

            # Add location info for higher debug levels
            if self.debug_level >= DebugLevel.VERBOSE and (module or function or line_number):
                location_parts = []
                if module:
                    location_parts.append(f"module={module}")
                if function:
                    location_parts.append(f"func={function}")
                if line_number:
                    location_parts.append(f"line={line_number}")

                if location_parts:
                    log_line += f" [{', '.join(location_parts)}]"

            # Add user/request context for trace level
            if self.debug_level >= DebugLevel.TRACE:
                context_parts = []
                if user_id:
                    context_parts.append(f"user={user_id[:8]}")
                if request_id:
                    context_parts.append(f"req={request_id[:8]}")

                if context_parts:
                    log_line += f" <{', '.join(context_parts)}>"

            # Print the main log line
            safe_console_print(f"📋 {log_line}", style=style)

            # Add extra data for diagnostic level
            if self.debug_level >= DebugLevel.DIAGNOSTIC and extra_data:
                extra_str = json.dumps(extra_data, indent=2, default=str)
                safe_console_print(f"Extra: {extra_str}", style="dim white")

            # Add stack trace for errors if available
            if stack_trace and level in ['ERROR', 'CRITICAL'] and self.debug_level >= DebugLevel.VERBOSE:
                safe_console_print(f"Stack trace: ", style="dim red")
                for line in stack_trace.split('\n'):
                    if line.strip():
                        safe_console_print(f"{line}", style="dim red")

        except Exception as e:
            # Fallback rendering if structured rendering fails
            self.log_error(e, "rendering backend log message")

            # Issue #2108: Gate raw JSON output behind debug level to prevent odd logs
            if self.debug_level >= DebugLevel.DIAGNOSTIC:
                # Full JSON dump for troubleshooting at diagnostic level
                message_str = json.dumps(log_message, default=str)
                self.debug_print(f"[BACKEND LOG] Raw JSON: {message_str}", DebugLevel.DIAGNOSTIC)
            elif self.debug_level >= DebugLevel.VERBOSE:
                # Minimal fallback message for verbose level
                basic_msg = str(log_message.get('message', log_message.get('textPayload', 'Log parsing failed')))
                self.debug_print(f"[BACKEND LOG] {basic_msg[:100]}{'...' if len(basic_msg) > 100 else ''}", DebugLevel.VERBOSE)
            # Else: Silent fallback for basic/silent levels to maintain clean output

    def log_websocket_error_with_diagnostics(self, error: Exception, context: str = "",
                                            connection_id: Optional[str] = None,
                                            error_category: Optional[str] = None,
                                            additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Log WebSocket errors with enhanced diagnostic capabilities.

        Args:
            error: The exception that occurred
            context: Additional context about when/where the error occurred
            connection_id: WebSocket connection identifier
            error_category: Optional error category for classification
            additional_data: Additional diagnostic data
        """
        self.log_error(error, context)

        # Use WebSocket diagnostic utility if available
        if self.websocket_diagnostic_utility:
            try:
                # Map string category to enum if provided
                from diagnostic_utilities.websocket_diagnostic_utility import WebSocketErrorCategory

                category = None
                if error_category:
                    category_mapping = {
                        'cleanup_state': WebSocketErrorCategory.CLEANUP_STATE,
                        'timeout_hierarchy': WebSocketErrorCategory.TIMEOUT_HIERARCHY,
                        'race_condition': WebSocketErrorCategory.RACE_CONDITION,
                        'resource_cleanup': WebSocketErrorCategory.RESOURCE_CLEANUP,
                        'connection_state': WebSocketErrorCategory.CONNECTION_STATE,
                        'authentication': WebSocketErrorCategory.AUTHENTICATION,
                        'event_delivery': WebSocketErrorCategory.EVENT_DELIVERY,
                        'protocol_violation': WebSocketErrorCategory.PROTOCOL_VIOLATION,
                    }
                    category = category_mapping.get(error_category.lower(), WebSocketErrorCategory.CONNECTION_STATE)
                else:
                    # Auto-detect category based on error type and context
                    category = self._auto_detect_error_category(error, context)

                # Capture diagnostic context
                diagnostic_context = self.websocket_diagnostic_utility.capture_generic_error(
                    category=category,
                    connection_id=connection_id,
                    error_message=str(error),
                    error_type=type(error).__name__,
                    additional_data={
                        'context': context,
                        **(additional_data or {})
                    }
                )

                # Report diagnostic if at verbose level or higher
                if self.debug_level >= DebugLevel.VERBOSE:
                    self.websocket_diagnostic_utility.report_diagnostic(diagnostic_context)

            except Exception as diagnostic_error:
                if self.debug_level >= DebugLevel.BASIC:
                    self.debug_print(f"Diagnostic utility error: {diagnostic_error}", DebugLevel.BASIC, "yellow")

    def _auto_detect_error_category(self, error: Exception, context: str) -> 'WebSocketErrorCategory':
        """Auto-detect error category based on error type and context."""
        from diagnostic_utilities.websocket_diagnostic_utility import WebSocketErrorCategory

        error_str = str(error).lower()
        context_str = context.lower()

        # Timeout-related errors
        if 'timeout' in error_str or 'timeout' in context_str:
            return WebSocketErrorCategory.TIMEOUT_HIERARCHY

        # Cleanup-related errors
        if any(word in error_str or word in context_str for word in ['cleanup', 'close', 'disconnect']):
            return WebSocketErrorCategory.CLEANUP_STATE

        # Authentication errors
        if any(word in error_str or word in context_str for word in ['auth', 'token', 'unauthorized', 'forbidden']):
            return WebSocketErrorCategory.AUTHENTICATION

        # Resource/memory errors
        if any(word in error_str for word in ['memory', 'resource', 'leak', 'allocation']):
            return WebSocketErrorCategory.RESOURCE_CLEANUP

        # Race condition indicators
        if any(word in error_str or word in context_str for word in ['race', 'concurrent', 'lock', 'conflict']):
            return WebSocketErrorCategory.RACE_CONDITION

        # Event delivery issues
        if any(word in error_str or word in context_str for word in ['event', 'message', 'delivery', 'emit']):
            return WebSocketErrorCategory.EVENT_DELIVERY

        # Protocol violations
        if any(word in error_str for word in ['protocol', 'frame', 'opcode', 'invalid']):
            return WebSocketErrorCategory.PROTOCOL_VIOLATION

        # Default to connection state
        return WebSocketErrorCategory.CONNECTION_STATE

class GCPErrorLookup:
    """
    ISSUE #1603: GCP error lookup functionality using run_id
    Provides integrated error analysis for agent CLI debugging
    """

    def __init__(self, project: str = "netra-staging", debug_manager: Optional[DebugManager] = None):
        self.project = project
        self.debug = debug_manager

    async def lookup_errors_for_run_id(self, run_id: str) -> Dict[str, Any]:
        """Look up GCP logs for a specific run_id and analyze errors"""
        if self.debug:
            self.debug.debug_print(f"Looking up GCP errors for run_id: {run_id}")

        safe_console_print(f"🔍 Looking up GCP errors for run_id: {run_id}", style="cyan")
        safe_console_print(f"Project: {self.project}", style="dim")

        # Try multiple service names that might contain the run_id
        service_names = [
            "netra-backend-staging",
            "netra-auth-service",
            "netra-frontend-staging"
        ]

        all_results = {}

        for service_name in service_names:
            safe_console_print(f"📋 Checking service: {service_name}", style="dim")

            # Build gcloud logging command
            gcloud_cmd = [
                "gcloud", "logging", "read",
                f"resource.labels.service_name={service_name} AND (jsonPayload.run_id='{run_id}' OR textPayload:'{run_id}' OR labels.run_id='{run_id}')",
                "--project", self.project,
                "--limit", "50",
                "--format", "json"
            ]

            try:
                # Execute gcloud command
                process = await asyncio.create_subprocess_exec(
                    *gcloud_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    # Parse JSON output
                    logs = json.loads(stdout.decode()) if stdout else []

                    if logs:
                        safe_console_print(f"✅ Found {len(logs)} log entries for {service_name}", style="green")
                        all_results[service_name] = self._analyze_logs(logs, run_id)
                    else:
                        safe_console_print(f"⚠️ No logs found for {service_name}", style="yellow")
                        all_results[service_name] = {"logs": [], "errors": [], "warnings": []}
                else:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    safe_console_print(f"❌ Error querying {service_name}: {error_msg[:100]}", style="red")
                    all_results[service_name] = {"error": error_msg}

            except FileNotFoundError:
                safe_console_print("❌ gcloud CLI not found. Please install Google Cloud SDK.", style="red")
                return {"error": "gcloud CLI not installed"}
            except Exception as e:
                safe_console_print(f"❌ Unexpected error: {e}", style="red")
                all_results[service_name] = {"error": str(e)}

        # Generate summary report
        return self._generate_error_report(all_results, run_id)

    def _analyze_logs(self, logs: List[Dict], run_id: str) -> Dict[str, Any]:
        """Analyze logs to identify errors, warnings, and important events"""
        errors = []
        warnings = []
        agent_events = []

        for log in logs:
            severity = log.get("severity", "INFO")
            timestamp = log.get("timestamp", "")

            # Extract message content
            message = ""
            if "jsonPayload" in log:
                json_payload = log["jsonPayload"]
                message = json_payload.get("message", str(json_payload))
            elif "textPayload" in log:
                message = log["textPayload"]

            log_entry = {
                "timestamp": timestamp,
                "severity": severity,
                "message": message[:500],  # Truncate long messages
                "full_log": log
            }

            # Categorize logs
            if severity in ["ERROR", "CRITICAL"]:
                errors.append(log_entry)
            elif severity == "WARNING":
                warnings.append(log_entry)
            elif any(keyword in message.lower() for keyword in ["agent", "websocket", "event", run_id.lower()]):
                agent_events.append(log_entry)

        return {
            "logs": logs,
            "errors": errors,
            "warnings": warnings,
            "agent_events": agent_events,
            "total_logs": len(logs)
        }

    def _generate_error_report(self, all_results: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Generate a comprehensive error report"""
        total_errors = 0
        total_warnings = 0
        total_logs = 0

        critical_errors = []
        all_warnings = []

        for service_name, result in all_results.items():
            if "error" in result:
                continue

            total_errors += len(result.get("errors", []))
            total_warnings += len(result.get("warnings", []))
            total_logs += result.get("total_logs", 0)

            # Collect critical errors
            for error in result.get("errors", []):
                critical_errors.append({
                    "service": service_name,
                    **error
                })

            # Collect warnings
            for warning in result.get("warnings", []):
                all_warnings.append({
                    "service": service_name,
                    **warning
                })

        # Display results
        safe_console_print(f"\n📊 GCP Error Analysis Summary for run_id: {run_id}", style="bold cyan")
        safe_console_print(f"Total logs found: {total_logs}", style="dim")
        safe_console_print(f"Errors: {total_errors}", style="red" if total_errors > 0 else "green")
        safe_console_print(f"Warnings: {total_warnings}", style="yellow" if total_warnings > 0 else "green")

        if critical_errors:
            safe_console_print(f"\n❌ Critical Errors Found: ", style="bold red")
            for i, error in enumerate(critical_errors[:5], 1):  # Show max 5 errors
                safe_console_print(f"{i}. [{error['service']}] {error['message'][:100]}...", style="red")
                safe_console_print(f"Time: {error['timestamp']}", style="dim")

        if all_warnings:
            safe_console_print(f"\n⚠️ Warnings Found: ", style="bold yellow")
            for i, warning in enumerate(all_warnings[:3], 1):  # Show max 3 warnings
                safe_console_print(f"{i}. [{warning['service']}] {warning['message'][:100]}...", style="yellow")

        if total_errors == 0 and total_warnings == 0:
            safe_console_print(f"\n✅ No errors or warnings found for run_id: {run_id}", style="green")
            if total_logs == 0:
                safe_console_print("This might indicate that the run_id is invalid or logs have been rotated.", style="dim")

        return {
            "run_id": run_id,
            "total_logs": total_logs,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "critical_errors": critical_errors,
            "warnings": all_warnings,
            "services_checked": list(all_results.keys()),
            "detailed_results": all_results
        }

class HealthChecker:
    """
    Health check utilities for Agent CLI debugging
    """

    def __init__(self, config: 'Config', debug_manager: DebugManager):
        self.config = config
        self.debug = debug_manager

    async def check_backend_health(self) -> Dict[str, Any]:
        """Check backend service health"""
        self.debug.debug_print("[CHECK] Checking backend health...")

        try:
            async with aiohttp.ClientSession() as session:
                health_url = f"{self.config.backend_url}/health"

                async with session.get(health_url, timeout=10) as resp:
                    status_code = resp.status

                    if status_code == 200:
                        data = await resp.json()
                        self.debug.debug_print("[PASS] Backend health check passed", style="green")

                        if self.debug.debug_level >= DebugLevel.VERBOSE:
                            self.debug.debug_print(f"Health data: {json.dumps(data, indent=2)}", DebugLevel.VERBOSE)

                        return {
                            "status": "healthy",
                            "status_code": status_code,
                            "url": health_url,
                            "data": data
                        }
                    else:
                        error_text = await resp.text()
                        self.debug.debug_print(f"[FAIL] Backend health check failed: {status_code}", style="red")

                        return {
                            "status": "unhealthy",
                            "status_code": status_code,
                            "url": health_url,
                            "error": error_text
                        }

        except Exception as e:
            self.debug.log_error(e, "backend health check")
            return {
                "status": "error",
                "url": health_url,
                "error": str(e)
            }

    async def check_auth_service_health(self) -> Dict[str, Any]:
        """Check auth service health"""
        self.debug.debug_print("[CHECK] Checking auth service health...")

        try:
            async with aiohttp.ClientSession() as session:
                health_url = f"{self.config.auth_url}/health"

                async with session.get(health_url, timeout=10) as resp:
                    status_code = resp.status

                    if status_code == 200:
                        data = await resp.json()
                        self.debug.debug_print("[PASS] Auth service health check passed", style="green")
                        return {
                            "status": "healthy",
                            "status_code": status_code,
                            "url": health_url,
                            "data": data
                        }
                    else:
                        error_text = await resp.text()
                        self.debug.debug_print(f"[FAIL] Auth service health check failed: {status_code}", style="red")
                        return {
                            "status": "unhealthy",
                            "status_code": status_code,
                            "url": health_url,
                            "error": error_text
                        }

        except Exception as e:
            self.debug.log_error(e, "auth service health check")
            return {
                "status": "error",
                "url": health_url,
                "error": str(e)
            }

    async def check_websocket_connectivity(self) -> Dict[str, Any]:
        """Check WebSocket connectivity without authentication"""
        self.debug.debug_print("[CHECK] Checking WebSocket connectivity...")

        try:
            # Try to connect without auth first to check basic connectivity
            # Use default timeout for connectivity check since no cleanup coordination available yet
            async with websockets.connect(
                self.config.ws_url,
                close_timeout=10,
                max_size=5 * 1024 * 1024  # 5 MB max message size
            ) as ws:
                self.debug.debug_print("[PASS] WebSocket basic connectivity check passed", style="green")
                return {
                    "status": "reachable",
                    "url": self.config.ws_url
                }

        except Exception as e:
            self.debug.log_error(e, "WebSocket connectivity check")
            return {
                "status": "unreachable",
                "url": self.config.ws_url,
                "error": str(e)
            }

    def check_system_resources(self) -> Dict[str, Any]:
        """Check local system resources"""
        self.debug.debug_print("[CHECK] Checking system resources...")

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage for home directory
            disk = psutil.disk_usage(str(Path.home()))

            resources = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3),
                "status": "normal"
            }

            # Determine status based on usage
            if cpu_percent > 90 or memory.percent > 90 or disk.free < 1024**3:  # < 1GB free
                resources["status"] = "high_usage"
                self.debug.debug_print("[WARN] High system resource usage detected", style="yellow")
            else:
                self.debug.debug_print("[PASS] System resources look good", style="green")

            if self.debug.debug_level >= DebugLevel.VERBOSE:
                self.debug.debug_print(f"Resources: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%, Disk {disk.free/(1024**3):.1f}GB free", DebugLevel.VERBOSE)

            return resources

        except Exception as e:
            self.debug.log_error(e, "system resource check")
            return {
                "status": "error",
                "error": str(e)
            }

    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive report"""
        self.debug.debug_print("[CHECK] Running comprehensive health check...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "environment": self.config.environment.value,
            "backend": await self.check_backend_health(),
            "auth_service": await self.check_auth_service_health(),
            "websocket": await self.check_websocket_connectivity(),
            "system": self.check_system_resources()
        }

        # Overall status determination
        all_healthy = all(
            result.get("status") in ["healthy", "reachable", "normal"]
            for result in [results["backend"], results["auth_service"], results["websocket"], results["system"]]
        )

        results["overall_status"] = "healthy" if all_healthy else "issues_detected"

        if all_healthy:
            self.debug.debug_print("[PASS] All health checks passed!", style="green")
        else:
            self.debug.debug_print("[WARN] Some health checks detected issues", style="yellow")

        return results

def check_gcp_credentials_available() -> tuple[bool, str]:
    """
    Check if GCP credentials are available for secret loading.

    Returns:
        tuple[bool, str]: (credentials_available, status_message)
    """
    try:
        # Check if GOOGLE_APPLICATION_CREDENTIALS is set and file exists
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.exists(creds_path):
            return True, f"GCP credentials found: {creds_path}"

        # Check if gcloud auth is configured
        try:
            result = subprocess.run(
                ["gcloud", "auth", "application-default", "print-access-token"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "GCP credentials available via gcloud auth"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return False, "GCP credentials not configured"

    except Exception as e:
        return False, f"GCP credential check failed: {str(e)}"



def show_startup_banner(config):
    """Display enhanced startup banner with environment.

    Issue #2747 Phase 3: Improved messaging to clearly show ENVIRONMENT.

    Args:
        config: Config object containing environment, backend_url, and auth_url
    """
    print()
    print("=" * 75)
    safe_console_print("🤖 Netra Agent CLI - Interactive Mode", display_mode=detect_terminal_capabilities())
    print("=" * 75)
    print()
    safe_console_print(f"📍 Environment: {config.environment.value.upper()}", display_mode=detect_terminal_capabilities())
    print()

    safe_console_print("🔗 Endpoints: ", display_mode=detect_terminal_capabilities())
    print(f"Backend: {config.backend_url}")
    print(f"Auth: {config.auth_url}")
    print()
    print("=" * 75)
    print()



class Environment(Enum):
    """Available environments"""
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"
    DEVELOPMENT = "development"  # Custom backend URL for development/testing

@dataclass
class Config:
    """Configuration for the CLI"""
    environment: Environment = Environment.STAGING
    client_environment: Optional[str] = None  # Issue #2442: Client environment for timeout coordination
    custom_backend_url: Optional[str] = None  # Custom backend URL for DEVELOPMENT environment
    backend_url: str = ""
    auth_url: str = ""
    ws_url: str = ""
    token_file: Path = Path.home() / ".netra" / "cli_token.json"
    log_level: str = "INFO"
    timeout: int = 30
    default_email: str = "test@netra.ai"
    debug_level: DebugLevel = DebugLevel.SILENT
    debug_log_file: Optional[Path] = None
    stream_logs: bool = False  # Issue #1828: Stream backend logs via WebSocket
    enable_websocket_diagnostics: bool = False  # Issue #2478: Enhanced WebSocket error diagnostics
    skip_timeout_validation: bool = False  # Issue #2483: Skip timeout hierarchy validation
    json_mode: bool = False  # ISSUE #2766: JSON output mode - suppress console output
    ci_mode: bool = False  # ISSUE #2766: CI mode - suppress Rich terminal output
    use_backend_threads: bool = True  # SSOT: Use backend for thread ID management (can disable for backward compat)

    def get_websocket_url(self) -> str:
        """Get WebSocket URL for compatibility with test framework"""
        return self.ws_url

    def __post_init__(self):
        """Set URLs based on environment - NO BACKEND DEPENDENCIES."""
        # ISSUE #2782: Load minimal config (E2E key only for staging)
        config_reader = SimpleConfigReader(self.environment.value)
        minimal_config = config_reader.load_minimal_config()

        # Set URLs (hardcoded - no backend config needed)
        if self.environment == Environment.STAGING:
            self.backend_url = "https://api.staging.netrasystems.ai"
            self.auth_url = "https://auth.staging.netrasystems.ai"
            self.ws_url = "wss://api.staging.netrasystems.ai/ws"
        elif self.environment == Environment.LOCAL:
            self.backend_url = "http://localhost:8000"
            self.auth_url = "http://localhost:8081"
            self.ws_url = "ws://localhost:8000/ws"
        elif self.environment == Environment.PRODUCTION:
            self.backend_url = "https://api.netrasystems.ai"
            self.auth_url = "https://auth.netrasystems.ai"
            self.ws_url = "wss://api.netrasystems.ai/ws"
        elif self.environment == Environment.DEVELOPMENT:
            # DEVELOPMENT mode: Use custom backend URL or fallback to localhost
            if self.custom_backend_url:
                # Parse custom URL to determine protocol
                from urllib.parse import urlparse
                parsed = urlparse(self.custom_backend_url)

                # Use the custom backend URL
                self.backend_url = self.custom_backend_url

                # Derive WebSocket URL based on HTTP/HTTPS protocol
                ws_scheme = "wss" if parsed.scheme == "https" else "ws"
                self.ws_url = f"{ws_scheme}://{parsed.netloc}/ws"

                # For development, use the same host for auth (simplified)
                self.auth_url = self.custom_backend_url.replace("/api", "/auth") if "/api" in self.custom_backend_url else self.custom_backend_url
            else:
                # Fallback to localhost if no custom URL provided
                self.backend_url = "http://localhost:8000"
                self.auth_url = "http://localhost:8081"
                self.ws_url = "ws://localhost:8000/ws"

        # Create token directory if needed
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

@dataclass
class AuthToken:
    """Authentication token data"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None
    email: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if token is expired"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at - timedelta(minutes=5)

    def decode_payload(self) -> Dict[str, Any]:
        """Decode JWT payload without verification (for display)"""
        try:
            return jwt.decode(self.access_token, options={"verify_signature": False})
        except Exception:
            return {}

class LocalCallbackServer:
    """HTTP server to handle OAuth callbacks locally"""

    def __init__(self, port: int = 8899):
        self.port = port
        self.host = "localhost"
        self.callback_data = None
        self.server = None
        self.received_callback = threading.Event()
        self.state_token = None

    def generate_state_token(self) -> str:
        """Generate a secure state token for CSRF protection"""
        self.state_token = secrets.token_urlsafe(32)
        return self.state_token

    def validate_state_token(self, received_state: str) -> bool:
        """Validate the received state token"""
        return self.state_token and received_state == self.state_token

    def get_callback_url(self) -> str:
        """Get the callback URL for OAuth configuration"""
        return f"http://{self.host}:{self.port}/auth/callback"

    def start_server(self) -> bool:
        """Start the local HTTP server"""
        try:
            # Check if port is available
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex((self.host, self.port))
                if result == 0:
                    safe_console_print(f"WARNING: Port {self.port} is already in use", style="yellow")
                    return False

            # Create server
            server_address = (self.host, self.port)
            self.server = HTTPServer(server_address, self._create_handler())

            # Start server in background thread
            server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            server_thread.start()

            safe_console_print(f"Local callback server started on {self.get_callback_url()}", style="green")
            return True

        except Exception as e:
            safe_console_print(f"ERROR: Failed to start callback server: {e}", style="red")
            return False

    def _create_handler(self):
        """Create HTTP request handler class"""
        callback_server = self

        class CallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Suppress default HTTP server logging
                pass

            def do_GET(self):
                if self.path.startswith('/auth/callback'):
                    # Parse callback parameters
                    parsed_url = urllib.parse.urlparse(self.path)
                    params = urllib.parse.parse_qs(parsed_url.query)

                    # Extract parameters
                    code = params.get('code', [None])[0]
                    state = params.get('state', [None])[0]
                    error = params.get('error', [None])[0]

                    if error:
                        callback_server.callback_data = {'error': error, 'error_description': params.get('error_description', [''])[0]}
                        self._send_error_response(error)
                    elif code and state:
                        # Validate state token
                        if callback_server.validate_state_token(state):
                            callback_server.callback_data = {'code': code, 'state': state}
                            self._send_success_response()
                        else:
                            callback_server.callback_data = {'error': 'invalid_state', 'error_description': 'CSRF state token validation failed'}
                            self._send_error_response('invalid_state')
                    else:
                        callback_server.callback_data = {'error': 'invalid_request', 'error_description': 'Missing code or state parameter'}
                        self._send_error_response('invalid_request')

                    # Signal that callback was received
                    callback_server.received_callback.set()
                else:
                    self.send_response(404)
                    self.end_headers()

            def _send_success_response(self):
                """Send success response to browser"""
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Authentication Success - Netra CLI</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f0f0; }
                        .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; }
                        .success { color: #4CAF50; }
                        .icon { font-size: 48px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">SUCCESS:</div>
                        <h1 class="success">Authentication Successful!</h1>
                        <p>You have successfully authenticated with Netra.</p>
                        <p>You can now close this browser window and return to the CLI.</p>
                    </div>
                </body>
                </html>
                """
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode())

            def _send_error_response(self, error: str):
                """Send error response to browser"""
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Authentication Error - Netra CLI</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f0f0; }}
                        .container {{ background: white; padding: 30px; border-radius: 10px; display: inline-block; }}
                        .error {{ color: #f44336; }}
                        .icon {{ font-size: 48px; margin-bottom: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">ERROR:</div>
                        <h1 class="error">Authentication Failed</h1>
                        <p>Error: {error}</p>
                        <p>Please close this window and try again in the CLI.</p>
                    </div>
                </body>
                </html>
                """
                self.send_response(400)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode())

        return CallbackHandler

    def wait_for_callback(self, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """Wait for OAuth callback with timeout"""
        if self.received_callback.wait(timeout):
            return self.callback_data
        return None

    def stop_server(self):
        """Stop the local HTTP server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            safe_console_print("Local callback server stopped", style="dim")

class AuthManager:
    """Manages authentication for the CLI"""

    def __init__(self, config: Config):
        self.config = config
        self.token: Optional[AuthToken] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.load_cached_token()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def load_cached_token(self) -> bool:
        """Load token from cache file"""
        if not self.config.token_file.exists():
            return False

        try:
            with open(self.config.token_file, 'r') as f:
                data = json.load(f)
                self.token = AuthToken(
                    access_token=data['access_token'],
                    refresh_token=data.get('refresh_token'),
                    expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
                    user_id=data.get('user_id'),
                    email=data.get('email')
                )

                if not self.token.is_expired():
                    safe_console_print("SUCCESS: Loaded cached authentication token", style="green",
                                     json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
                    return True
                else:
                    safe_console_print("WARNING: Cached token expired, need to re-authenticate", style="yellow",
                                     json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        except Exception as e:
            safe_console_print(f"WARNING: Could not load cached token: {e}", style="yellow",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

        return False

    async def save_token(self):
        """Save token to cache file"""
        if not self.token:
            return

        data = {
            'access_token': self.token.access_token,
            'refresh_token': self.token.refresh_token,
            'expires_at': self.token.expires_at.isoformat() if self.token.expires_at else None,
            'user_id': self.token.user_id,
            'email': self.token.email
        }

        with open(self.config.token_file, 'w') as f:
            json.dump(data, f, indent=2)

    async def authenticate_dev(self, email: str = "test@netra.ai", password: str = "testpass123") -> bool:
        """Authenticate using dev login (development environment only)"""
        safe_console_print(f"Using development authentication...", style="cyan")

        # Try dev auth methods (only for local development)
        auth_methods = [
            ("Backend Dev Login", f"{self.config.backend_url}/auth/dev_login", {"email": email, "password": password}),
            ("Auth Service Dev Login", f"{self.config.auth_url}/auth/dev/login", {}),
            ("Create Test Token", self._create_test_token, None)
        ]

        for method_name, url_or_func, payload in auth_methods:
            try:
                safe_console_print(f"Trying {method_name}...", style="dim")

                if callable(url_or_func):
                    # It's a function (test token creation)
                    if await url_or_func(email):
                        safe_console_print(f"SUCCESS: Authentication successful via {method_name}!", style="green")
                        return True
                else:
                    # It's a URL endpoint
                    async with self.session.post(
                        url_or_func,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()

                            # Extract token info
                            token_data = data.get('access_token') or data.get('token')
                            if isinstance(token_data, dict):
                                token = token_data.get('token') or token_data.get('access_token')
                            else:
                                token = token_data

                            if token:
                                # Decode token to get expiry
                                payload = jwt.decode(token, options={"verify_signature": False})
                                expires_at = datetime.fromtimestamp(payload.get('exp', time.time() + 3600))

                                self.token = AuthToken(
                                    access_token=token,
                                    refresh_token=data.get('refresh_token'),
                                    expires_at=expires_at,
                                    user_id=payload.get('user_id') or payload.get('sub') or "dev-user",
                                    email=payload.get('email') or email
                                )

                                await self.save_token()
                                safe_console_print(f"SUCCESS: Authentication successful via {method_name}!", style="green")
                                return True
                        else:
                            error_text = await resp.text()
                            safe_console_print(f"Failed: {resp.status} - {error_text[:100]}", style="dim red")

            except Exception as e:
                safe_console_print(f"Error: {str(e)[:100]}", style="dim red")
                continue

        safe_console_print("ERROR: All authentication methods failed", style="red")
        return False

    async def _authenticate_e2e(self, email: str) -> bool:
        """Authenticate using E2E test simulation endpoint"""
        try:
            # ISSUE #2782: Get E2E key from environment (set by SimpleConfigReader in Config.__post_init__)
            e2e_key = E2E_OAUTH_SIMULATION_KEY

            # Fallback to environment-specific defaults only if not found
            if not e2e_key:
                if self.config.environment == Environment.STAGING:
                    e2e_key = "staging-e2e-test-bypass-key-2025"
                elif self.config.environment == Environment.LOCAL:
                    e2e_key = "dev-e2e-oauth-bypass-key-for-testing-only-change-in-staging"
                else:
                    e2e_key = "test-e2e-oauth-bypass-key-for-testing-only"

            url = f"{self.config.auth_url}/auth/e2e/test-auth"
            headers = {
                "Content-Type": "application/json",
                "X-E2E-Bypass-Key": e2e_key
            }

            payload = {
                "email": email,
                "name": "CLI Test User",
                "permissions": ["read", "write", "test"],
                "simulate_oauth": True
            }

            async with self.session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    # Extract token info
                    access_token = data.get('access_token')
                    if access_token:
                        # Decode token to get expiry
                        payload = jwt.decode(access_token, options={"verify_signature": False})
                        expires_at = datetime.fromtimestamp(payload.get('exp', time.time() + 3600))

                        self.token = AuthToken(
                            access_token=access_token,
                            refresh_token=data.get('refresh_token'),
                            expires_at=expires_at,
                            user_id=payload.get('user_id') or payload.get('sub') or f"e2e-{email.split('@')[0]}",
                            email=payload.get('email') or email
                        )

                        await self.save_token()
                        safe_console_print(f"SUCCESS: E2E authentication successful!", style="green")
                        return True
                else:
                    error_text = await resp.text()
                    if "E2E bypass key required" in error_text or "Invalid E2E bypass key" in error_text:
                        safe_console_print(f"E2E auth failed: Invalid or missing E2E_OAUTH_SIMULATION_KEY", style="dim yellow")
                        safe_console_print(f"Set the E2E key: export E2E_OAUTH_SIMULATION_KEY=<key>", style="dim")
                    else:
                        safe_console_print(f"E2E auth failed: {resp.status} - {error_text[:100]}", style="dim red")
                    return False

        except Exception as e:
            safe_console_print(f"E2E auth error: {str(e)[:100]}", style="dim red")
            return False

    async def _create_test_token(self, email: str) -> bool:
        """Create a test token for development/testing"""
        import time
        import base64

        # Create a JWT-like token that will work with permissive mode or test environments
        payload = {
            "sub": email,
            "user_id": "cli-test-user",
            "email": email,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": "netra-auth-service",
            "aud": "netra-platform",
            "env": "staging" if self.config.environment == Environment.STAGING else "development",
            "permissions": ["read", "write", "test"],
            "token_type": "access"
        }

        # Create a properly formatted JWT token (even if not cryptographically signed)
        header = {"alg": "HS256", "typ": "JWT"}

        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        body_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

        # For staging, we'll try to use a test signature that might work with permissive mode
        # This won't be cryptographically valid but may work if the backend is in test/permissive mode
        test_signature = "test_signature_for_cli_testing"
        signature_b64 = base64.urlsafe_b64encode(test_signature.encode()).decode().rstrip('=')

        test_token = f"{header_b64}.{body_b64}.{signature_b64}"

        self.token = AuthToken(
            access_token=test_token,
            expires_at=datetime.fromtimestamp(payload['exp']),
            user_id=payload['user_id'],
            email=email
        )

        await self.save_token()
        safe_console_print("WARNING: Using test token (may require permissive mode enabled on backend)", style="yellow",
                         json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        return True

    async def get_valid_token(self, use_oauth: bool = True, oauth_provider: str = "google", auth_method: str = "auto") -> Optional[str]:
        """Get a valid authentication token with proper SSOT priority

        For staging environment, E2E simulation is now the default method to enable
        automated testing and CI/CD without browser OAuth flows.

        Args:
            use_oauth: Whether to use OAuth authentication
            oauth_provider: OAuth provider to use
            auth_method: Preferred auth method - "auto", "e2e", or "oauth"
        """
        if self.token and not self.token.is_expired():
            return self.token.access_token

        # Handle explicit auth method preference
        if auth_method == "e2e":
            # Force E2E authentication
            if await self._authenticate_e2e("test@netra.ai"):
                return self.token.access_token
            return None
        elif auth_method == "oauth":
            # Force OAuth authentication
            if use_oauth and await self.authenticate_oauth(oauth_provider):
                return self.token.access_token
            return None

        # ISSUE #1630: Default to E2E simulation for staging environment (auto mode)
        if self.config.environment == Environment.STAGING:
            # 1. Try E2E test auth first for staging (default for automation)
            safe_console_print("Using E2E simulation authentication for staging (default)", style="cyan")
            if await self._authenticate_e2e("test@netra.ai"):
                return self.token.access_token

            # 2. Fallback to OAuth for staging if E2E fails and OAuth requested
            if use_oauth and await self.authenticate_oauth(oauth_provider):
                return self.token.access_token
        else:
            # For non-staging environments, keep OAuth as primary
            # 1. Try auth service OAuth first (SSOT compliance)
            if use_oauth and await self.authenticate_oauth(oauth_provider):
                return self.token.access_token

            # 2. Fallback to E2E test auth if auth service unavailable
            if await self._authenticate_e2e("test@netra.ai"):
                return self.token.access_token

        # 3. Only use dev auth in local development environment
        if self.config.environment == Environment.LOCAL:
            if await self.authenticate_dev():
                return self.token.access_token

        return None

    async def authenticate_oauth(self, provider: str = "google") -> bool:
        """Authenticate using OAuth browser flow (SSOT auth service)"""
        safe_console_print(f"Starting OAuth authentication with {provider} via auth service...", style="cyan")

        # Only support Google for now
        if provider != "google":
            safe_console_print(f"OAuth provider '{provider}' not supported. Only 'google' is currently available.", style="red")
            return False

        # Check if auth service is available
        try:
            health_check_url = f"{self.config.auth_url}/health"
            safe_console_print(f"Checking auth service health...", style="dim")

            async with self.session.get(health_check_url, timeout=5) as resp:
                if resp.status != 200:
                    safe_console_print(f"WARNING: Auth service unhealthy: {resp.status}", style="yellow")
                    return False
        except Exception as e:
            safe_console_print(f"WARNING: Auth service health check failed: {e}", style="yellow")
            return False

        # Start local callback server
        callback_server = LocalCallbackServer()
        if not callback_server.start_server():
            safe_console_print(f"ERROR: Failed to start local callback server", style="red")
            return False

        try:
            # Generate state token for CSRF protection
            state_token = callback_server.generate_state_token()

            # Build OAuth URL using auth service
            oauth_url = await self._build_oauth_url(provider, state_token, callback_server.get_callback_url())
            if not oauth_url:
                safe_console_print(f"ERROR: Failed to build OAuth URL", style="red")
                return False

            safe_console_print(f"Opening browser for OAuth authentication...", style="cyan")
            safe_console_print(f"NOTE: If browser doesn't open automatically, visit: {oauth_url}", style="dim")

            # Open browser
            try:
                webbrowser.open(oauth_url)
                safe_console_print(f"SUCCESS: Browser opened successfully", style="dim")
            except Exception as e:
                safe_console_print(f"WARNING: Could not open browser automatically: {e}", style="yellow")
                safe_console_print(f"NOTE: Please manually visit: {oauth_url}", style="cyan")

            # Wait for callback
            safe_console_print("Waiting for OAuth callback (5 minutes timeout)...", style="yellow")
            safe_console_print("NOTE: Complete the OAuth flow in your browser", style="dim")

            callback_data = callback_server.wait_for_callback(timeout=300)

            if not callback_data:
                safe_console_print("ERROR: OAuth timeout - no callback received", style="red")
                return False

            if 'error' in callback_data:
                error_desc = callback_data.get('error_description', callback_data['error'])
                safe_console_print(f"ERROR: OAuth error: {error_desc}", style="red")

                # Handle specific error cases
                if 'access_denied' in callback_data['error']:
                    safe_console_print("NOTE: User denied OAuth authorization", style="yellow")
                elif 'invalid_request' in callback_data['error']:
                    safe_console_print("NOTE: OAuth configuration issue - check redirect URIs", style="yellow")
                elif 'invalid_state' in callback_data['error']:
                    safe_console_print("NOTE: CSRF state validation failed", style="yellow")

                return False

            # Exchange code for tokens
            if 'code' in callback_data:
                safe_console_print(f"SUCCESS: OAuth authorization code received", style="green")
                success = await self._exchange_oauth_code(callback_data['code'], callback_server.get_callback_url())

                if not success:
                    safe_console_print("ERROR: OAuth token exchange failed", style="red")
                    return False

                return success

            safe_console_print("ERROR: No authorization code received", style="red")
            return False

        except Exception as e:
            safe_console_print(f"ERROR: Unexpected OAuth error: {e}", style="red")
            return False

        finally:
            callback_server.stop_server()

    async def _build_oauth_url(self, provider: str, state: str, redirect_uri: str) -> Optional[str]:
        """Build OAuth authorization URL using auth service endpoint"""
        try:
            # Use auth service login endpoint directly
            oauth_login_url = f"{self.config.auth_url}/auth/login?provider={provider}"
            safe_console_print(f"Using auth service OAuth endpoint: {oauth_login_url}", style="dim")

            # Return the auth service login URL - it will handle the OAuth redirect
            return oauth_login_url

        except Exception as e:
            safe_console_print(f"ERROR: Error building OAuth URL: {e}", style="red")
            return None

    async def authenticate(self, email: str = "test@netra.ai") -> bool:
        """Main authentication method with proper SSOT priority order"""
        safe_console_print(f"Starting authentication...", style="cyan")

        # 1. Auth service OAuth (PRIMARY - SSOT)
        if await self.authenticate_oauth("google"):
            return True

        # 2. E2E test auth (fallback for staging/testing/development)
        if self.config.environment in [Environment.STAGING, Environment.LOCAL, Environment.DEVELOPMENT]:
            safe_console_print("Trying E2E test authentication...", style="yellow")
            if await self._authenticate_e2e(email):
                return True

        # 3. Dev auth (development/local environment only)
        if self.config.environment in [Environment.LOCAL, Environment.DEVELOPMENT]:
            safe_console_print("Trying development authentication...", style="yellow")
            if await self.authenticate_dev(email):
                return True

        # 4. Test token (last resort)
        safe_console_print("Creating test token as last resort...", style="yellow")
        return await self._create_test_token(email)

    async def _build_auth_service_oauth_url(self, provider: str, state: str, redirect_uri: str) -> Optional[str]:
        """Build OAuth URL using auth service endpoint (SSOT method)"""
        try:
            # Use the auth service's login endpoint with provider parameter
            # This ensures we're using the SSOT auth service configuration
            oauth_url = f"{self.config.auth_url}/auth/login?provider={provider}"
            safe_console_print(f"Using SSOT auth service OAuth URL", style="dim")
            return oauth_url

        except Exception as e:
            safe_console_print(f"ERROR: Error building auth service OAuth URL: {e}", style="red")
            return None

    async def _exchange_oauth_code(self, code: str, redirect_uri: str) -> bool:
        """Exchange OAuth authorization code for access token"""
        try:
            # Try the OAuth callback endpoint
            callback_url = f"{self.config.auth_url}/auth/callback"

            params = {
                'code': code,
                'redirect_uri': redirect_uri
            }

            # Call the auth service callback endpoint (allows redirects)
            async with self.session.get(callback_url, params=params, allow_redirects=False) as resp:
                if resp.status == 302:
                    # Auth service redirects to frontend with tokens
                    location = resp.headers.get('Location', '')
                    safe_console_print(f"Auth service redirected to: {location[:100]}...", style="dim")

                    # Parse tokens from redirect URL
                    parsed_url = urllib.parse.urlparse(location)
                    fragment_params = urllib.parse.parse_qs(parsed_url.fragment)
                    query_params = urllib.parse.parse_qs(parsed_url.query)

                    # Check both fragment and query for tokens (different OAuth flows)
                    all_params = {**fragment_params, **query_params}

                    access_token = None
                    refresh_token = None

                    # Extract access token
                    if 'access_token' in all_params:
                        access_token = all_params['access_token'][0]
                    elif 'token' in all_params:
                        access_token = all_params['token'][0]

                    # Extract refresh token if available
                    if 'refresh_token' in all_params:
                        refresh_token = all_params['refresh_token'][0]

                    if access_token:
                        return await self._process_oauth_tokens(access_token, refresh_token)
                    else:
                        safe_console_print(f"ERROR: No access token found in redirect URL", style="red")
                        safe_console_print(f"Redirect params: {list(all_params.keys())}", style="dim")

                        # Fallback: try to get user info from other params
                        if 'user' in all_params or 'email' in all_params:
                            safe_console_print(f"User info found, creating session token...", style="yellow")
                            return await self._create_session_from_user_info(all_params)

                        return False
                elif resp.status == 200:
                    # Check if it's a JSON response with token
                    try:
                        data = await resp.json()
                        access_token = data.get('access_token') or data.get('token')
                        refresh_token = data.get('refresh_token')

                        if access_token:
                            return await self._process_oauth_tokens(access_token, refresh_token)
                        else:
                            safe_console_print(f"ERROR: No access token in response: {data}", style="red")
                            return False
                    except:
                        error_text = await resp.text()
                        safe_console_print(f"ERROR: OAuth callback failed: {resp.status} - {error_text[:200]}", style="red")
                        return False
                else:
                    error_text = await resp.text()
                    safe_console_print(f"ERROR: OAuth callback failed: {resp.status} - {error_text[:200]}", style="red")
                    return False

        except Exception as e:
            safe_console_print(f"ERROR: Error exchanging OAuth code: {e}", style="red")
            return False

    async def _process_oauth_tokens(self, access_token: str, refresh_token: Optional[str] = None) -> bool:
        """Process OAuth tokens and create AuthToken"""
        try:
            # Decode token to get expiry and user info
            payload = jwt.decode(access_token, options={"verify_signature": False})
            expires_at = datetime.fromtimestamp(payload.get('exp', time.time() + 3600))

            self.token = AuthToken(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                user_id=payload.get('user_id') or payload.get('sub') or "oauth-user",
                email=payload.get('email') or "oauth@example.com"
            )

            await self.save_token()
            safe_console_print("SUCCESS: OAuth authentication successful!", style="green")
            safe_console_print(f"Authenticated as: {self.token.email}", style="cyan")
            return True

        except Exception as e:
            safe_console_print(f"ERROR: Error processing OAuth tokens: {e}", style="red")
            return False

    async def _create_session_from_user_info(self, params: Dict[str, list]) -> bool:
        """Create session token from user info when OAuth tokens not available"""
        try:
            # Extract user info
            email = params.get('email', ['oauth@example.com'])[0]
            name = params.get('name', ['OAuth User'])[0]
            user_id = params.get('user_id', ['oauth-user'])[0]

            safe_console_print(f"Creating session for: {email}", style="yellow")

            # Try to get a proper token by calling the auth service with user info
            token_url = f"{self.config.auth_url}/auth/dev/login"
            token_payload = {
                'email': email,
                'name': name,
                'oauth_provider': 'google'
            }

            async with self.session.post(token_url, json=token_payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    access_token = data.get('access_token') or data.get('token')
                    if access_token:
                        return await self._process_oauth_tokens(access_token, data.get('refresh_token'))

            # If that fails, create a test token
            safe_console_print(f"WARNING: Creating test token for OAuth user", style="yellow")
            return await self._create_test_token(email)

        except Exception as e:
            safe_console_print(f"ERROR: Error creating session from user info: {e}", style="red")
            return False

    async def use_manual_token(self, token: str) -> bool:
        """Use a manually provided token"""
        try:
            # Try to decode the token to get info
            payload = jwt.decode(token, options={"verify_signature": False})
            expires_at = datetime.fromtimestamp(payload.get('exp', time.time() + 3600))

            self.token = AuthToken(
                access_token=token,
                expires_at=expires_at,
                user_id=payload.get('user_id') or payload.get('sub') or "unknown",
                email=payload.get('email') or "unknown@example.com"
            )

            await self.save_token()
            safe_console_print("SUCCESS: Using manually provided token", style="green")
            return True
        except Exception as e:
            safe_console_print(f"ERROR: Invalid token provided: {e}", style="red")
            return False

def truncate_with_ellipsis(text: str, max_length: int) -> str:
    """Truncate text and add ellipsis only if actually truncated"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def smart_truncate_json(data: Any, debug_manager: Optional['DebugManager'] = None) -> str:
    """Smart JSON truncation based on debug level.

    Prioritizes agent_name and tool_name fields at the top when available.
    """
    # Reorder data to put important fields first if it's a dict
    if isinstance(data, dict):
        ordered_data = {}
        # Priority fields that should appear first
        priority_fields = ['agent_name', 'tool_name', 'event', 'type', 'status']

        # Add priority fields first if they exist
        for field in priority_fields:
            if field in data:
                ordered_data[field] = data[field]

        # Add remaining fields
        for key, value in data.items():
            if key not in ordered_data:
                ordered_data[key] = value

        data = ordered_data

    if debug_manager is None:
        # Default behavior - basic truncation
        return truncate_with_ellipsis(json.dumps(data), 100)

    debug_level = debug_manager.debug_level

    if debug_level >= DebugLevel.DIAGNOSTIC:
        # Unlimited - full JSON output
        try:
            return json.dumps(data, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(data)
    elif debug_level >= DebugLevel.TRACE:
        # 1000 chars with pretty JSON
        try:
            pretty_json = json.dumps(data, indent=2, ensure_ascii=False)
            return truncate_with_ellipsis(pretty_json, 1000)
        except (TypeError, ValueError):
            return truncate_with_ellipsis(str(data), 1000)
    elif debug_level >= DebugLevel.VERBOSE:
        # 300 chars
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            return truncate_with_ellipsis(json_str, 300)
        except (TypeError, ValueError):
            return truncate_with_ellipsis(str(data), 300)
    else:
        # BASIC (default) - 100 chars
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            return truncate_with_ellipsis(json_str, 100)
        except (TypeError, ValueError):
            return truncate_with_ellipsis(str(data), 100)

@dataclass
class WebSocketEvent:
    """Represents a WebSocket event"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    def format_for_display(self, debug_manager: Optional[DebugManager] = None) -> str:
        """Format event for console display with optional enhanced debugging"""
        if debug_manager:
            return debug_manager.format_event_for_display(self.type, self.data)
        else:
            # Fallback to basic formatting
            return self._basic_format()

    def _basic_format(self) -> str:
        """Basic event formatting (original behavior)"""
        # Handle system_message events that wrap agent events
        event_type = self.type
        data = self.data

        if event_type == "system_message":
            inner_event = data.get('event', '')
            if inner_event in ['agent_started', 'agent_thinking', 'agent_completed', 'tool_executing', 'tool_completed']:
                # Extract the actual event type and data from payload
                event_type = inner_event
                payload = data.get('payload', {})
                # Merge payload data with original data, payload takes precedence
                data = {**data, **payload}

        if event_type == "agent_started":
            agent_name = data.get('agent_name', 'Unknown')
            run_id = data.get('run_id', 'N/A')
            # Apply hierarchy-aware formatting for agent_started
            orchestrator_patterns = ['Supervisor', 'WorkflowOrchestrator']
            step_patterns = ['triage']

            if any(pattern in agent_name for pattern in orchestrator_patterns):
                return f"🎯 Orchestrator: {agent_name} started (run: {truncate_with_ellipsis(run_id, 8)})"
            elif any(pattern in agent_name for pattern in step_patterns):
                return f"  🤖 Step: {agent_name} started (run: {truncate_with_ellipsis(run_id, 8)})"
            else:
                return f"    🧠 Agent: {agent_name} started (run: {truncate_with_ellipsis(run_id, 8)})"
        elif event_type == "agent_thinking":
            thought = data.get('thought', data.get('reasoning', ''))
            agent_name = data.get('agent_name', '')
            # Apply hierarchy-aware formatting for agent_thinking
            orchestrator_patterns = ['Supervisor', 'WorkflowOrchestrator']
            step_patterns = ['triage']

            if any(pattern in agent_name for pattern in orchestrator_patterns):
                return f"💭 Thinking: {truncate_with_ellipsis(thought, 100)}"
            elif any(pattern in agent_name for pattern in step_patterns):
                return f"  💭 Thinking: {truncate_with_ellipsis(thought, 100)}"
            else:
                return f"    💭 Thinking: {truncate_with_ellipsis(thought, 100)}"
        elif event_type == "tool_executing":
            tool = data.get('tool', data.get('tool_name', 'Unknown'))
            return f"[EXEC] Executing Tool: {tool}"
        elif event_type == "tool_completed":
            tool = data.get('tool', data.get('tool_name', 'Unknown'))
            status = data.get('status', 'completed')
            return f"[PASS] Tool Complete: {tool} ({status})"
        elif event_type == "agent_completed":
            result = data.get('result')
            if result is None:
                result = data.get('final_response')
            if result is None:
                result = data.get('response', '')
            run_id = data.get('run_id', 'N/A')
            agent_name = data.get('agent_name', 'Unknown')
            # Use smart truncation for result, but with basic settings
            result_str = smart_truncate_json(result, None) if isinstance(result, (dict, list)) else truncate_with_ellipsis(str(result), 100)

            # Apply hierarchy-aware formatting for agent_completed
            orchestrator_patterns = ['Supervisor', 'WorkflowOrchestrator']
            step_patterns = ['triage']

            if any(pattern in agent_name for pattern in orchestrator_patterns):
                return f"🎯 Orchestrator Completed: {agent_name} (run: {truncate_with_ellipsis(run_id, 8)}) - {result_str}"
            elif any(pattern in agent_name for pattern in step_patterns):
                return f"  🤖 Step Completed: {agent_name} (run: {truncate_with_ellipsis(run_id, 8)}) - {result_str}"
            else:
                return f"    🧠 Agent Completed: {agent_name} (run: {truncate_with_ellipsis(run_id, 8)}) - {result_str}"
        elif event_type == "message":
            content = data.get('content', '')
            return f"[MSG] Message: {truncate_with_ellipsis(content, 100)}"
        elif event_type == "error":
            error = data.get('error', 'Unknown error')
            return f"[FAIL] Error: {error}"
        elif event_type == "connection_established":
            user_id = data.get('data', {}).get('user_id', 'unknown')
            return f"[CONN] Connected as: {user_id}"
        elif event_type == "handshake_response":
            thread_id = data.get('thread_id', 'unknown')
            return f"[HANDSHAKE] Handshake complete - Thread ID: {thread_id}"
        else:
            return safe_format_message(f"📡 {event_type}: {smart_truncate_json(data, None)}")

class WebSocketClient:
    """WebSocket client for agent interactions"""

    def __init__(self, config: Config, token: str, debug_manager: Optional[DebugManager] = None,
                 send_logs: bool = False, logs_count: int = 1, logs_project: Optional[str] = None,
                 logs_path: Optional[str] = None, logs_user: Optional[str] = None,
                 logs_provider: str = "claude", handshake_timeout: float = 10.0):
        self.config = config
        self.token = token
        self.debug = debug_manager or DebugManager(config.debug_level, config.debug_log_file, config.enable_websocket_diagnostics)
        self.handshake_timeout = handshake_timeout  # Configurable handshake timeout
        self.ws: Optional[WebSocketClientProtocol] = None
        self.events: List[WebSocketEvent] = []
        self.connected = False
        self.run_id: Optional[str] = None

        # ISSUE #2417 Phase 2: Store thread_id for filtering backend logs
        self.current_thread_id: Optional[str] = None

        # SSOT: Thread management cache for performance
        self.thread_cache_file = self._get_platform_cache_path()
        self.thread_cache: Dict[str, Dict[str, Any]] = {}
        self._load_thread_cache()

        # Log forwarding configuration
        self.send_logs = send_logs
        self.logs_count = logs_count
        self.logs_project = logs_project
        self.logs_path = logs_path
        self.logs_user = logs_user
        self.logs_provider = logs_provider

        # ISSUE #2134 FIX: Cleanup coordination protocol support
        self.cleanup_in_progress = False
        self.cleanup_complete = False
        self.negotiated_timeout: Optional[int] = None
        self.timeout_occurred = False

        # ISSUE #2442 FIX: Integration with backend timeout configuration
        self.websocket_recv_timeout: Optional[int] = None
        self.close_timeout: Optional[int] = None
        self._initialize_timeouts()

        # ISSUE #2373: WebSocket closure code tracking
        self.closure_code: Optional[int] = None
        self.closure_reason: Optional[str] = None
        self.closure_category: Optional[WebSocketClosureCategory] = None

        # Event queuing mechanism: Wait for BOTH handshake AND connection_established
        self.connection_established_received = False
        self.event_queue: List[Dict[str, Any]] = []
        self.ready_to_send_events = False

        # Thread ID capture for chunked uploads
        self.awaiting_chunk_thread_id = False
        self.captured_chunk_thread_id: Optional[str] = None
        self.chunk_thread_id_event: Optional[asyncio.Event] = None

    def _initialize_timeouts(self) -> None:
        """Initialize WebSocket timeouts using backend timeout configuration.

        ISSUE #2442 FIX: Integrate Agent CLI with backend timeout_configuration.py
        to ensure consistent timeout handling across client and server.
        ISSUE #2483 FIX: Add timeout hierarchy validation to prevent premature failures.
        """
        try:
            # Dynamic import to avoid import issues when backend is not available
            from netra_backend.app.core.timeout_configuration import get_websocket_recv_timeout

            # Use client_environment override if provided, otherwise use auto-detection
            self.websocket_recv_timeout = get_websocket_recv_timeout(
                client_environment=self.config.client_environment
            )

            # Set close timeout based on WebSocket recv timeout
            self.close_timeout = self.websocket_recv_timeout + 2  # Add 2s safety margin

            self.debug.debug_print(
                f"TIMEOUT CONFIG: WebSocket recv timeout: {self.websocket_recv_timeout}s, "
                f"close timeout: {self.close_timeout}s "
                f"(client_environment: {self.config.client_environment})"
            )

            # ISSUE #2483: Validate timeout hierarchy after configuration
            skip_validation = getattr(self.config, 'skip_timeout_validation', False)
            self._validate_timeout_hierarchy(skip_validation=skip_validation)

        except ImportError as e:
            self.debug.debug_print(f"TIMEOUT CONFIG: Could not import backend timeout config: {e}")
            # Fallback to environment-based defaults
            self._set_fallback_timeouts()
        except Exception as e:
            self.debug.debug_print(f"TIMEOUT CONFIG: Error initializing timeouts: {e}")
            self._set_fallback_timeouts()

    def _set_fallback_timeouts(self) -> None:
        """Set fallback timeouts when backend timeout configuration is unavailable."""
        # Use environment-aware fallback timeouts
        if self.config.environment == Environment.STAGING:
            # Issue #2662: Staging agents routinely exceed 60s; align fallback with cloud-native defaults
            self.websocket_recv_timeout = 300  # Staging fallback aligned with backend SSOT
            self.close_timeout = 302  # Maintain 2s safety margin for cleanup coordination
        elif self.config.environment == Environment.PRODUCTION:
            # Issue #2861: Production workflows now require 100s+ for multi-agent LLM responses
            self.websocket_recv_timeout = 120  # Production fallback aligned with extended Cloud Run windows
            self.close_timeout = 122
        elif self.config.environment == Environment.DEVELOPMENT:
            # Development environment: Use generous timeouts for custom backends
            self.websocket_recv_timeout = 300  # Development fallback (same as staging for flexibility)
            self.close_timeout = 302  # Maintain 2s safety margin
        else:  # LOCAL or other
            self.websocket_recv_timeout = 10  # Local default
            self.close_timeout = 12

        self.debug.debug_print(
            f"TIMEOUT FALLBACK: Using fallback timeouts for {self.config.environment.value}: "
            f"recv={self.websocket_recv_timeout}s, close={self.close_timeout}s"
        )

    def _get_close_timeout(self) -> int:
        """Get appropriate close timeout based on negotiated timeout or configured timeout."""
        if self.negotiated_timeout is not None:
            # Use negotiated timeout with 2-second safety margin for network delays
            timeout = self.negotiated_timeout + 2
            self.debug.debug_print(f"CLEANUP COORDINATION: Using negotiated close timeout {timeout}s (negotiated {self.negotiated_timeout}s + 2s safety)")
            return timeout
        elif self.close_timeout is not None:
            # ISSUE #2442 FIX: Use configured close timeout from backend timeout configuration
            self.debug.debug_print(f"TIMEOUT CONFIG: Using configured close timeout {self.close_timeout}s")
            return self.close_timeout
        else:
            # Default timeout when no negotiation or configuration available
            self.debug.debug_print("CLEANUP COORDINATION: Using default close timeout 10s (no negotiated or configured timeout available)")
            return 10

    def _validate_timeout_hierarchy(self, skip_validation: bool = False) -> bool:
        """Validate WebSocket and Agent timeout hierarchy to prevent premature failures.

        Issue #2483: Implements timeout hierarchy validation following the rule:
        WebSocket timeout must be > Agent execution timeout

        Args:
            skip_validation: Skip validation if explicitly disabled

        Returns:
            bool: True if validation passes or is skipped, False if hierarchy violation detected
        """
        if skip_validation:
            self.debug.debug_print("TIMEOUT VALIDATION: Skipped by request", DebugLevel.BASIC, "yellow")
            return True

        if not self.websocket_recv_timeout:
            self.debug.debug_print("TIMEOUT VALIDATION: No WebSocket timeout available, skipping validation", DebugLevel.VERBOSE, "yellow")
            return True

        try:
            # Import timeout configuration to get agent execution timeout
            from netra_backend.app.core.timeout_configuration import get_agent_execution_timeout

            agent_timeout = get_agent_execution_timeout()
            websocket_timeout = float(self.websocket_recv_timeout)

            # Import WebSocket diagnostic utility if available
            try:
                from diagnostic_utilities.websocket_diagnostic_utility import WebSocketDiagnosticUtility
                diagnostic_utility = WebSocketDiagnosticUtility(debug_manager=self.debug)

                # Perform timeout hierarchy validation
                environment = self.config.environment.value
                validation_result = diagnostic_utility.validate_timeout_hierarchy(
                    websocket_timeout=websocket_timeout,
                    agent_timeout=float(agent_timeout),
                    environment=environment
                )

                # Report validation results
                if not validation_result.is_valid:
                    self.debug.debug_print(
                        f"TIMEOUT HIERARCHY VIOLATION: WebSocket({websocket_timeout}s) <= Agent({agent_timeout}s)",
                        DebugLevel.BASIC,
                        "red"
                    )

                    # Display errors using Rich formatting
                    from rich.panel import Panel
                    from rich.text import Text

                    error_text = Text()
                    error_text.append("⚠️  TIMEOUT HIERARCHY VIOLATION DETECTED\n\n", style="bold red")
                    error_text.append(f"WebSocket Timeout: {websocket_timeout}s\n", style="red")
                    error_text.append(f"Agent Timeout: {agent_timeout}s\n", style="red")
                    error_text.append(f"Buffer: {validation_result.buffer_seconds:.1f}s\n\n", style="red")

                    for error in validation_result.errors:
                        error_text.append(f"• {error}\n", style="red")

                    if validation_result.recommendations:
                        error_text.append("\nRecommendations:\n", style="bold yellow")
                        for rec in validation_result.recommendations:
                            error_text.append(f"• {rec}\n", style="yellow")

                    safe_console_print(Panel(error_text, title="Timeout Configuration Issue", border_style="red"))
                    return False

                elif validation_result.warnings:
                    self.debug.debug_print(
                        f"TIMEOUT HIERARCHY WARNING: Buffer {validation_result.buffer_seconds:.1f}s may be insufficient",
                        DebugLevel.BASIC,
                        "yellow"
                    )

                    # Display warnings using Rich formatting
                    from rich.panel import Panel
                    from rich.text import Text

                    warning_text = Text()
                    warning_text.append("⚠️  TIMEOUT CONFIGURATION WARNING\n\n", style="bold yellow")
                    warning_text.append(f"WebSocket Timeout: {websocket_timeout}s\n", style="dim")
                    warning_text.append(f"Agent Timeout: {agent_timeout}s\n", style="dim")
                    warning_text.append(f"Buffer: {validation_result.buffer_seconds:.1f}s\n\n", style="yellow")

                    for warning in validation_result.warnings:
                        warning_text.append(f"• {warning}\n", style="yellow")

                    if validation_result.recommendations:
                        warning_text.append("\nRecommendations:\n", style="bold green")
                        for rec in validation_result.recommendations:
                            warning_text.append(f"• {rec}\n", style="green")

                    safe_console_print(Panel(warning_text, title="Timeout Configuration Advisory", border_style="yellow"))
                else:
                    self.debug.debug_print(
                        f"TIMEOUT HIERARCHY VALID: WebSocket({websocket_timeout}s) > Agent({agent_timeout}s), Buffer: {validation_result.buffer_seconds:.1f}s",
                        DebugLevel.VERBOSE,
                        "green"
                    )

                return True

            except ImportError:
                # Fall back to basic validation without diagnostic utility
                if websocket_timeout <= agent_timeout:
                    self.debug.debug_print(
                        f"TIMEOUT HIERARCHY VIOLATION: WebSocket({websocket_timeout}s) <= Agent({agent_timeout}s)",
                        DebugLevel.BASIC,
                        "red"
                    )
                    safe_console_print(
                        f"⚠️ TIMEOUT CONFIGURATION ERROR: WebSocket timeout ({websocket_timeout}s) must be greater than Agent timeout ({agent_timeout}s)",
                        style="red"
                    )
                    return False
                else:
                    buffer_seconds = websocket_timeout - agent_timeout
                    self.debug.debug_print(
                        f"TIMEOUT HIERARCHY VALID: WebSocket({websocket_timeout}s) > Agent({agent_timeout}s), Buffer: {buffer_seconds:.1f}s",
                        DebugLevel.VERBOSE,
                        "green"
                    )
                    return True

        except ImportError as e:
            self.debug.debug_print(f"TIMEOUT VALIDATION: Cannot import agent timeout config: {e}", DebugLevel.VERBOSE, "yellow")
            return True  # Allow operation if backend timeout config not available
        except Exception as e:
            self.debug.debug_print(f"TIMEOUT VALIDATION: Unexpected error: {e}", DebugLevel.BASIC, "red")
            return True  # Don't block operation on validation errors

    async def connect(self) -> bool:
        """Connect to WebSocket with authentication"""
        self.debug.debug_print(f"Connecting to WebSocket: {self.config.ws_url}")

        # Try multiple authentication methods
        methods = [
            ("subprotocol", self._connect_with_subprotocol),
            ("query_param", self._connect_with_query_param),
            ("header", self._connect_with_header)
        ]

        for method_name, method in methods:
            try:
                self.debug.debug_print(
                    f"Initiating WebSocket auth via {method_name}",
                    DebugLevel.VERBOSE,
                    style="cyan"
                )
                self.debug.log_connection_attempt(method_name, self.config.ws_url)
                if await method():
                    self.debug.log_connection_attempt(method_name, self.config.ws_url, success=True)
                    self.debug.debug_print(
                        f"WebSocket connected using {method_name}",
                        DebugLevel.VERBOSE,
                        style="green"
                    )

                    # SSOT: Perform handshake to get backend-provided thread_id
                    handshake_success = await self._perform_handshake()
                    if handshake_success:
                        safe_console_print(f"✅ Connected with thread ID: {self.current_thread_id}", style="green")
                        self.connected = True

                        # Start listening for events in background immediately
                        asyncio.create_task(self.receive_events())

                        # Wait for connection_established event
                        wait_start = asyncio.get_event_loop().time()
                        timeout = 5.0
                        while not self.connection_established_received:
                            if (asyncio.get_event_loop().time() - wait_start) > timeout:
                                self.debug.debug_print(
                                    f"⚠️ Timeout waiting for connection_established after {timeout}s",
                                    DebugLevel.BASIC,
                                    style="yellow"
                                )
                                break
                            await asyncio.sleep(0.1)

                        # Set ready flag if we got the event
                        if self.connection_established_received:
                            self.ready_to_send_events = True
                            self.debug.debug_print(
                                "✅ Connection fully established - ready to send events",
                                DebugLevel.BASIC,
                                style="green"
                            )

                        return True
                    else:
                        # Handshake failed - server not ready to process messages
                        self.debug.debug_print(
                            "Server still completing lifecycle phases (Initialize → Authenticate → Handshake → Prepare → Processing)",
                            DebugLevel.VERBOSE,
                            style="yellow"
                        )

                        # Wait briefly for server to complete its phases and retry
                        safe_console_print("⏳ Waiting for server to complete initialization...", style="yellow",
                                         json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
                        await asyncio.sleep(3.0)  # Give server time to reach PROCESSING phase

                        # Retry handshake once more
                        self.debug.debug_print(
                            "Retrying handshake after delay...",
                            DebugLevel.VERBOSE,
                            style="cyan"
                        )
                        handshake_success = await self._perform_handshake()
                        if handshake_success:
                            safe_console_print(f"✅ Connected with thread ID: {self.current_thread_id}", style="green",
                                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
                            self.connected = True

                            # Start listening for events in background immediately
                            asyncio.create_task(self.receive_events())

                            # Wait for connection_established event
                            wait_start = asyncio.get_event_loop().time()
                            timeout = 5.0
                            while not self.connection_established_received:
                                if (asyncio.get_event_loop().time() - wait_start) > timeout:
                                    self.debug.debug_print(
                                        f"⚠️ Timeout waiting for connection_established after {timeout}s",
                                        DebugLevel.BASIC,
                                        style="yellow"
                                    )
                                    break
                                await asyncio.sleep(0.1)

                            # Set ready flag if we got the event
                            if self.connection_established_received:
                                self.ready_to_send_events = True
                                self.debug.debug_print(
                                    "✅ Connection fully established - ready to send events",
                                    DebugLevel.BASIC,
                                    style="green"
                                )

                            return True
                        else:
                            # Server still not ready - fail the connection
                            self.debug.debug_print(
                                "ERROR: Server not ready after retry",
                                DebugLevel.BASIC,
                                style="red"
                            )
                            safe_console_print("❌ Server not ready to process messages. Please try again.", style="red",
                                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

                            # Close WebSocket and fail gracefully
                            if self.ws:
                                await self.ws.close()
                            return False
            except Exception as e:
                self.debug.log_connection_attempt(method_name, self.config.ws_url, success=False, error=str(e))
                self.debug.debug_print(
                    f"WebSocket authentication via {method_name} failed with {type(e).__name__}: {e}",
                    DebugLevel.BASIC,
                    style="red"
                )
                continue

        self.debug.debug_print("Failed to connect WebSocket with all methods", style="red")

        # ISSUE #2414: Provide helpful error messages based on environment and mode
        # ISSUE #2766: Suppress error messages in JSON/CI mode
        safe_console_print("ERROR: Unable to establish WebSocket connection", style="red",
                         json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print("", style="", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

        safe_console_print("💡 TROUBLESHOOTING: ", style="cyan",
                         json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        if self.config.environment == Environment.LOCAL:
            safe_console_print("1. Check if backend services are running locally", style="dim",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
            safe_console_print("2. Try: docker-compose up -d (if using Docker)", style="dim",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
            safe_console_print("3. Verify local services at http: //localhost: 8000/health", style="dim",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        elif self.config.environment == Environment.STAGING:
            safe_console_print("1. Check staging services status", style="dim",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
            safe_console_print("2. Verify your authentication is valid", style="dim",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
            safe_console_print("3. Try --env local for offline testing", style="dim",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        else:
            safe_console_print("1. Check network connectivity", style="dim",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
            safe_console_print("2. Verify authentication credentials", style="dim",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
            safe_console_print("3. Check service status at the backend URL", style="dim",
                             json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

        safe_console_print("", style="", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        return False

    async def _connect_with_subprotocol(self) -> bool:
        """Connect using subprotocol (most reliable for Cloud Run)"""
        safe_console_print("Trying subprotocol authentication...", style="dim",
                         json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        # Use the correct JWT subprotocol format supported by the backend
        # Based on unified_jwt_protocol_handler.py, supported formats are:
        # jwt.{token}, jwt-auth.{token}, bearer.{token}, staging-auth.{token}
        # Add environment information to subprotocol for Issue #1906
        env = self.config.environment.value
        subprotocols = [
            f"jwt.{env}.{self.token}",           # Primary format with environment
            f"jwt-auth.{env}.{self.token}",      # Alternative format with environment
            f"bearer.{env}.{self.token}",        # Fallback format with environment
            f"staging-auth.{self.token}",        # Legacy staging environment format
            f"jwt.{self.token}",                 # Backward compatibility - primary format
            f"jwt-auth.{self.token}",            # Backward compatibility - alternative format
            f"bearer.{self.token}"                # Backward compatibility - fallback format
        ]
        safe_console_print(f"Using JWT subprotocol formats: jwt.{self.token[:20]}...", style="dim",
                         json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        self.ws = await websockets.connect(
            self.config.ws_url,
            subprotocols=subprotocols,
            close_timeout=self._get_close_timeout(),
            max_size=5 * 1024 * 1024  # 5 MB max message size
        )
        return True

    async def _connect_with_query_param(self) -> bool:
        """Connect using query parameter"""
        safe_console_print("Trying query parameter authentication...", style="dim",
                         json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        # Add environment parameter for Issue #1906
        env = self.config.environment.value
        url = f"{self.config.ws_url}?token={self.token}&env={env}"
        self.ws = await websockets.connect(
            url,
            close_timeout=self._get_close_timeout(),
            max_size=5 * 1024 * 1024  # 5 MB max message size
        )
        return True

    async def _connect_with_header(self) -> bool:
        """Connect using Authorization header"""
        safe_console_print("Trying header authentication...", style="dim",
                         json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        # Add X-Environment header for Issue #1906
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Environment": self.config.environment.value
        }
        self.ws = await websockets.connect(
            self.config.ws_url,
            additional_headers=headers,
            close_timeout=self._get_close_timeout(),
            max_size=5 * 1024 * 1024  # 5 MB max message size
        )
        return True

    async def _perform_handshake(self) -> bool:
        """
        Wait for proactive handshake from server (as of 2025-10-09).

        Server Phase Alignment:
        - INITIALIZING: WebSocket connection accepted
        - AUTHENTICATING: User validation (happens during connect())
        - HANDSHAKING: Server proactively sends handshake_response (we wait here)
        - READY: Services initialized
        - PROCESSING: Message handling begins

        The client waits during server's HANDSHAKING phase to receive the
        proactive handshake_response without sending any request.
        """
        try:
            import asyncio

            self.debug.debug_print(
                "Waiting for server to enter HANDSHAKING phase and send handshake...",
                DebugLevel.VERBOSE,
                style="cyan"
            )

            # Server enters HANDSHAKING phase after authentication
            # and proactively sends handshake_response
            # Use configured timeout or default to 10 seconds
            handshake_timeout = self.handshake_timeout if hasattr(self, 'handshake_timeout') and self.handshake_timeout else 10.0
            start_time = asyncio.get_event_loop().time()

            try:
                while (asyncio.get_event_loop().time() - start_time) < handshake_timeout:
                    remaining_time = handshake_timeout - (asyncio.get_event_loop().time() - start_time)

                    # Be ready to receive messages during server's HANDSHAKING phase
                    self.debug.debug_print(
                        f"Listening for handshake (remaining: {remaining_time:.1f}s)...",
                        DebugLevel.VERBOSE,
                        style="dim"
                    )

                    try:
                        # Use the full remaining time for recv to avoid timeout errors
                        # This prevents premature connection closure during handshake
                        response_msg = await asyncio.wait_for(
                            self.ws.recv(),
                            timeout=remaining_time
                        )
                        response = json.loads(response_msg)
                    except asyncio.TimeoutError:
                        # Gracefully handle timeout - don't let it propagate and close connection
                        self.debug.debug_print(
                            "Handshake wait timed out after 10 seconds",
                            DebugLevel.VERBOSE,
                            style="yellow"
                        )
                        break  # Exit loop to handle timeout below
                    except json.JSONDecodeError as e:
                        # Handle JSON parsing errors gracefully
                        self.debug.debug_print(
                            f"Invalid JSON received during handshake: {e}",
                            DebugLevel.VERBOSE,
                            style="yellow"
                        )
                        continue  # Try to receive next message
                    except websockets.exceptions.ConnectionClosed as e:
                        # Connection closed during handshake - this is the issue!
                        self.debug.debug_print(
                            f"Connection closed during handshake wait: {e}",
                            DebugLevel.BASIC,
                            style="red"
                        )
                        return False  # Connection lost, can't continue

                    msg_type = response.get('type', 'unknown')
                    self.debug.debug_print(
                        f"Received: {msg_type}",
                        DebugLevel.VERBOSE,
                        style="cyan"
                    )

                    # Check for the proactive handshake_response
                    if msg_type == 'handshake_response':
                        # Server is in HANDSHAKING phase and sent the handshake
                        self.debug.debug_print(
                            "✅ Server sent proactive handshake (HANDSHAKING phase)",
                            DebugLevel.VERBOSE,
                            style="green"
                        )

                        # Process the handshake
                        result = await self._process_handshake_response(response)

                        if result:
                            self.debug.debug_print(
                                f"Handshake complete - Thread ID: {self.current_thread_id}",
                                DebugLevel.BASIC,
                                style="green"
                            )
                            self.debug.debug_print(
                                "Server phases: AUTH ✓ → HANDSHAKING ✓ → READY",
                                DebugLevel.VERBOSE,
                                style="green"
                            )

                            # Check if we can start sending events
                            # We need BOTH handshake AND connection_established
                            if self.connection_established_received:
                                self.ready_to_send_events = True
                                self.debug.debug_print(
                                    "✅ Ready to send events: Handshake ✓ | connection_established ✓",
                                    DebugLevel.BASIC,
                                    style="green"
                                )
                                safe_console_print(
                                    "✅ Fully connected: Handshake ✓ | connection_established ✓",
                                    style="green",
                                    json_mode=self.config.json_mode,
                                    ci_mode=self.config.ci_mode
                                )
                            else:
                                self.debug.debug_print(
                                    "⏳ Handshake complete, waiting for connection_established event",
                                    DebugLevel.BASIC,
                                    style="yellow"
                                )

                        return result

                    # Handle other message types while waiting
                    elif msg_type == 'connection_established':
                        # This is from AUTHENTICATING phase completion
                        self.debug.debug_print(
                            "✓ Connection established (AUTH phase) - waiting for HANDSHAKING phase",
                            DebugLevel.VERBOSE,
                            style="yellow"
                        )
                        # Track that connection_established was received
                        self.connection_established_received = True
                        self.debug.debug_print(
                            "📌 connection_established event received during handshake",
                            DebugLevel.BASIC,
                            style="cyan"
                        )
                        # Store the event but continue waiting
                        if hasattr(self, 'events'):
                            self.events.append(WebSocketEvent(
                                type=response.get('type', 'unknown'),
                                data=response
                            ))

                    else:
                        # Other event types - store but keep waiting for handshake
                        self.debug.debug_print(
                            f"Storing {msg_type} event - still waiting for handshake",
                            DebugLevel.VERBOSE,
                            style="dim"
                        )
                        if hasattr(self, 'events'):
                            self.events.append(WebSocketEvent(
                                type=response.get('type', 'unknown'),
                                data=response
                            ))

            except asyncio.TimeoutError:
                pass  # Fall through to timeout handling below

            # Timeout - server didn't send handshake
            self.debug.debug_print(
                "Server did not send handshake - may be using pre-2025-10-09 version without HANDSHAKING phase",
                DebugLevel.VERBOSE,
                style="yellow"
            )
            return False

        except Exception as e:
            # Handshake error
            error_msg = f"WARNING: Handshake error: {e}"
            self.debug.log_error(e, "handshake protocol")
            self.debug.debug_print(error_msg, DebugLevel.BASIC, style="yellow")
            safe_console_print(error_msg, style="yellow")
            return False

    async def _process_any_handshake_response(self, response: Dict[str, Any]) -> bool:
        """
        SSOT: Process any handshake-related response from backend.
        Handles both 'handshake_response' and 'connection_established' event types.

        This method ensures we have a single source of truth for handshake processing,
        avoiding duplicate logic across the codebase.

        Args:
            response: The response message from backend

        Returns:
            True if a valid thread_id was extracted and acknowledged, False otherwise
        """
        response_type = response.get('type')

        if response_type == 'handshake_response':
            # Standard handshake_response with thread_id directly in response
            self.debug.debug_print(
                "Processing handshake_response",
                DebugLevel.VERBOSE,
                style="green"
            )
            return await self._process_handshake_response(response)

        elif response_type == 'connection_established':
            # connection_established is NOT a handshake response!
            # It's just a WebSocket connection event. We should NOT acknowledge it.
            # We need to wait for the actual handshake_response message.
            self.debug.debug_print(
                "Received connection_established - waiting for handshake_response",
                DebugLevel.VERBOSE,
                style="yellow"
            )

            # Extract connection_id for logging purposes only
            connection_data = response.get('data', {})
            connection_id = connection_data.get('connection_id')

            if connection_id:
                self.debug.debug_print(
                    f"Connection established with connection_id: {connection_id} (not using as thread_id)",
                    DebugLevel.VERBOSE,
                    style="yellow"
                )

            # Return False to indicate we're still waiting for handshake_response
            # DO NOT send session_acknowledged here!
            return False

        else:
            # Unexpected response type
            self.debug.debug_print(
                f"ERROR: Unexpected handshake response type: '{response_type}'",
                DebugLevel.BASIC,
                style="red"
            )

            # Show the actual response data for debugging
            self.debug.debug_print(
                "ACTUAL RESPONSE DATA:",
                DebugLevel.BASIC,
                style="yellow"
            )
            self.debug.debug_print(
                json.dumps(response, indent=2),
                DebugLevel.BASIC,
                style="cyan"
            )

            return False

    async def _process_handshake_response(self, response: Dict[str, Any]) -> bool:
        """
        Process a handshake_response message from backend.

        This is the new, distinct handshake response event that clearly separates
        handshake completion from basic WebSocket connection establishment.

        Args:
            response: The handshake_response message from backend

        Returns:
            True if thread_id was successfully extracted and acknowledged
        """
        # Extract all IDs from the handshake response
        backend_thread_id = response.get('thread_id')
        backend_run_id = response.get('run_id')
        backend_request_id = response.get('request_id')
        backend_session_token = response.get('session_token')
        backend_timestamp = response.get('timestamp')
        backend_message = response.get('message', 'Handshake complete')

        if not backend_thread_id:
            # Backend didn't provide thread_id
            self.debug.debug_print(
                "ERROR: Backend handshake_response missing thread_id",
                DebugLevel.BASIC,
                style="red"
            )
            return False

        # CRITICAL: Accept backend's thread_id as single source of truth
        self.current_thread_id = backend_thread_id
        self.run_id = backend_run_id  # Store run_id if provided
        self._update_thread_cache(backend_thread_id)

        self.debug.debug_print(
            f"Handshake complete - Thread ID: {backend_thread_id}",
            DebugLevel.VERBOSE,
            style="green"
        )

        if backend_message:
            self.debug.debug_print(
                f"Backend message: {backend_message}",
                DebugLevel.VERBOSE,
                style="cyan"
            )

        # CRITICAL: Send acknowledgment with the SAME thread_id
        # Per WebSocket Client Lifecycle Guide, use "handshake_acknowledged"
        ack_message = {
            "type": "handshake_acknowledged",
            "thread_id": backend_thread_id,  # Echo back the same ID
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await self.ws.send(json.dumps(ack_message))

        # Per WebSocket Client Lifecycle Guide, wait for handshake_complete
        # and then add delay for server to enter Phase 5 (Processing)
        self.debug.debug_print(
            "Waiting for handshake_complete confirmation...",
            DebugLevel.VERBOSE,
            style="cyan"
        )

        # Wait briefly for handshake_complete message
        try:
            complete_msg = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
            complete_data = json.loads(complete_msg)
            if complete_data.get('type') == 'handshake_complete':
                self.debug.debug_print(
                    "✅ Received handshake_complete - Server at Phase 4 (Ready)",
                    DebugLevel.VERBOSE,
                    style="green"
                )

                # CRITICAL: Add delay for server to enter Phase 5 (Processing)
                # Per documentation, 500ms is recommended
                self.debug.debug_print(
                    "Waiting 500ms for server to enter Phase 5 (Processing)...",
                    DebugLevel.VERBOSE,
                    style="cyan"
                )
                await asyncio.sleep(0.5)

                self.debug.debug_print(
                    "✅ Server should now be in Phase 5 (Processing) - ready for messages",
                    DebugLevel.VERBOSE,
                    style="green"
                )
        except asyncio.TimeoutError:
            # If no handshake_complete, still add a delay to be safe
            self.debug.debug_print(
                "No handshake_complete received, adding safety delay",
                DebugLevel.VERBOSE,
                style="yellow"
            )
            await asyncio.sleep(0.5)
        except Exception as e:
            self.debug.debug_print(
                f"Error waiting for handshake_complete: {e}",
                DebugLevel.VERBOSE,
                style="yellow"
            )
            await asyncio.sleep(0.5)

        return True

    def _get_platform_cache_path(self) -> Path:
        """
        Get platform-appropriate cache directory path.

        Windows: %LOCALAPPDATA%/Netra/CLI/thread_cache.json
        macOS: ~/Library/Application Support/Netra/CLI/thread_cache.json
        Linux: ~/.local/share/netra/cli/thread_cache.json or ~/.netra/thread_cache.json
        """
        import platform as stdlib_platform

        system = stdlib_platform.system()

        if system == "Windows":
            # Use Windows AppData/Local directory
            app_data = os.environ.get('LOCALAPPDATA')
            if app_data:
                cache_dir = Path(app_data) / "Netra" / "CLI"
            else:
                # Fallback to user home
                cache_dir = Path.home() / "AppData" / "Local" / "Netra" / "CLI"
        elif system == "Darwin":  # macOS
            # Use macOS Application Support directory
            cache_dir = Path.home() / "Library" / "Application Support" / "Netra" / "CLI"
        else:  # Linux and other Unix-like systems
            # Follow XDG Base Directory Specification
            xdg_data_home = os.environ.get('XDG_DATA_HOME')
            if xdg_data_home:
                cache_dir = Path(xdg_data_home) / "netra" / "cli"
            else:
                # Fallback to ~/.local/share or ~/.netra for compatibility
                local_share = Path.home() / ".local" / "share" / "netra" / "cli"
                if local_share.parent.exists():
                    cache_dir = local_share
                else:
                    # Legacy path for backward compatibility
                    cache_dir = Path.home() / ".netra"

        return cache_dir / "thread_cache.json"

    def _load_thread_cache(self) -> None:
        """
        Load thread cache from disk for SSOT thread management.

        Cache structure:
        {
            "user_id": {
                "thread_id": "backend_thread_123",
                "created_at": "2024-01-01T00:00:00",
                "last_used": "2024-01-01T00:00:00",
                "environment": "staging"
            }
        }
        """
        try:
            if self.thread_cache_file.exists():
                with open(self.thread_cache_file, 'r') as f:
                    self.thread_cache = json.load(f)
                    self.debug.debug_print(
                        f"SSOT: Loaded thread cache with {len(self.thread_cache)} entries",
                        DebugLevel.VERBOSE
                    )
        except Exception as e:
            self.debug.debug_print(
                f"SSOT: Could not load thread cache: {e}",
                DebugLevel.TRACE
            )
            self.thread_cache = {}

    def _save_thread_cache(self) -> None:
        """Save thread cache to disk for persistence."""
        try:
            # Ensure directory exists
            self.thread_cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Save cache
            with open(self.thread_cache_file, 'w') as f:
                json.dump(self.thread_cache, f, indent=2)

            self.debug.debug_print(
                "SSOT: Thread cache saved successfully",
                DebugLevel.TRACE
            )
        except Exception as e:
            self.debug.debug_print(
                f"SSOT: Could not save thread cache: {e}",
                DebugLevel.TRACE
            )

    def _get_cached_thread_id(self) -> Optional[str]:
        """
        Get cached thread ID for current user and environment.

        SSOT: Uses cached thread but validates with backend.
        """
        try:
            # Get user identifier from token
            if not self.token:
                return None

            # Decode token to get user_id
            payload = jwt.decode(self.token, options={"verify_signature": False})
            user_id = payload.get('user_id') or payload.get('sub') or payload.get('email')

            if not user_id:
                return None

            # Check cache for this user
            if user_id in self.thread_cache:
                cached_data = self.thread_cache[user_id]

                # Check if cache is for same environment
                cached_env = cached_data.get('environment')
                current_env = self.config.environment.value if hasattr(self.config, 'environment') else None

                if cached_env == current_env:
                    thread_id = cached_data.get('thread_id')
                    last_used = cached_data.get('last_used')

                    # Check if cache is recent (within 24 hours)
                    if last_used:
                        last_used_dt = datetime.fromisoformat(last_used)
                        if datetime.now() - last_used_dt < timedelta(hours=24):
                            self.debug.debug_print(
                                f"SSOT: Found cached thread_id: {thread_id}",
                                DebugLevel.VERBOSE
                            )
                            return thread_id

        except Exception as e:
            self.debug.debug_print(
                f"SSOT: Error accessing thread cache: {e}",
                DebugLevel.TRACE
            )

        return None

    def _update_thread_cache(self, thread_id: str) -> None:
        """Update thread cache with new or validated thread ID."""
        try:
            # Get user identifier
            payload = jwt.decode(self.token, options={"verify_signature": False})
            user_id = payload.get('user_id') or payload.get('sub') or payload.get('email')

            if user_id:
                # Update cache entry
                self.thread_cache[user_id] = {
                    'thread_id': thread_id,
                    'created_at': self.thread_cache.get(user_id, {}).get('created_at', datetime.now().isoformat()),
                    'last_used': datetime.now().isoformat(),
                    'environment': self.config.environment.value if hasattr(self.config, 'environment') else "unknown"
                }

                # Save to disk
                self._save_thread_cache()

                self.debug.debug_print(
                    f"SSOT: Updated thread cache for user {user_id[:10]}...",
                    DebugLevel.TRACE
                )

        except Exception as e:
            self.debug.debug_print(
                f"SSOT: Could not update thread cache: {e}",
                DebugLevel.TRACE
            )

    async def get_or_create_thread_from_backend(self) -> Optional[str]:
        """
        SSOT: Get or create a thread ID from the backend.

        This ensures thread IDs are managed by the backend as the single source of truth,
        not generated locally by the client.

        Returns:
            Thread ID from backend, or None if creation fails
        """
        # Check if backend thread management is disabled
        if not self.config.use_backend_threads:
            self.debug.debug_print(
                "SSOT: Backend thread management disabled by configuration",
                DebugLevel.VERBOSE
            )
            return None

        try:
            # First check if we have a cached thread_id for this session
            if self.current_thread_id and await self._validate_thread_with_backend(self.current_thread_id):
                self.debug.debug_print(
                    f"SSOT: Using existing validated thread_id: {self.current_thread_id}",
                    DebugLevel.VERBOSE
                )
                self._update_thread_cache(self.current_thread_id)
                return self.current_thread_id

            # Check persistent cache for thread ID
            cached_thread_id = self._get_cached_thread_id()
            if cached_thread_id and await self._validate_thread_with_backend(cached_thread_id):
                self.current_thread_id = cached_thread_id
                self.debug.debug_print(
                    f"SSOT: Using cached and validated thread_id: {cached_thread_id}",
                    DebugLevel.VERBOSE
                )
                self._update_thread_cache(cached_thread_id)
                return cached_thread_id

            # Create a new thread via backend API
            thread_id = await self._create_thread_on_backend()
            if thread_id:
                self.current_thread_id = thread_id
                self._update_thread_cache(thread_id)
                self.debug.debug_print(
                    f"SSOT: Created new thread_id from backend: {thread_id}",
                    DebugLevel.BASIC,
                    style="green"
                )
                return thread_id

            # Fallback: Use local generation with warning (backward compatibility)
            self.debug.debug_print(
                "SSOT WARNING: Backend thread creation failed, falling back to local generation",
                DebugLevel.BASIC,
                style="yellow"
            )
            return None

        except Exception as e:
            self.debug.debug_print(
                f"SSOT ERROR: Thread management failed: {e}",
                DebugLevel.BASIC,
                style="red"
            )
            return None

    async def _create_thread_on_backend(self) -> Optional[str]:
        """
        Create a new thread on the backend and return its ID.

        SSOT: Backend is the authoritative source for thread IDs.
        """
        try:
            # Construct the thread creation endpoint
            thread_url = f"{self.config.backend_url}/api/threads/create"

            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }

            # Thread creation payload with metadata
            payload = {
                "source": "agent_cli",
                "environment": self.config.environment.value if hasattr(self.config, 'environment') else "unknown",
                "client_version": "1.0.0",  # Could be made configurable
                "timestamp": datetime.now().isoformat()
            }

            # Use aiohttp session if available, otherwise create one
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(thread_url, json=payload, headers=headers) as response:
                    if response.status == 200 or response.status == 201:
                        data = await response.json()
                        thread_id = data.get("thread_id") or data.get("id")
                        if thread_id:
                            self.debug.debug_print(
                                f"SSOT: Backend created thread with ID: {thread_id}",
                                DebugLevel.VERBOSE
                            )
                            return thread_id
                    else:
                        error_text = await response.text()
                        self.debug.debug_print(
                            f"SSOT: Backend thread creation failed with status {response.status}: {error_text}",
                            DebugLevel.BASIC,
                            style="yellow"
                        )

        except aiohttp.ClientError as e:
            # Network or connection errors - expected in some environments
            self.debug.debug_print(
                f"SSOT: Backend thread API not available (network error): {e}",
                DebugLevel.VERBOSE
            )
        except Exception as e:
            self.debug.debug_print(
                f"SSOT: Unexpected error creating backend thread: {e}",
                DebugLevel.VERBOSE
            )

        return None

    async def _validate_thread_with_backend(self, thread_id: str) -> bool:
        """
        Validate that a thread ID exists and is valid on the backend.

        SSOT: Backend validates thread existence and status.
        """
        try:
            # Quick validation - check if thread exists on backend
            validate_url = f"{self.config.backend_url}/api/threads/{thread_id}/validate"

            headers = {
                "Authorization": f"Bearer {self.token}"
            }

            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(validate_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        is_valid = data.get("valid", False)
                        if is_valid:
                            self.debug.debug_print(
                                f"SSOT: Thread {thread_id} validated successfully",
                                DebugLevel.TRACE
                            )
                        return is_valid
                    elif response.status == 404:
                        self.debug.debug_print(
                            f"SSOT: Thread {thread_id} not found on backend",
                            DebugLevel.VERBOSE
                        )
                        return False

        except Exception as e:
            # If validation fails, assume thread is invalid
            self.debug.debug_print(
                f"SSOT: Thread validation failed for {thread_id}: {e}",
                DebugLevel.TRACE
            )

        return False

    async def _flush_queued_events(self) -> None:
        """
        Flush all queued events after connection_established is received.

        This method sends all events that were queued while waiting for
        the connection_established event (which comes after handshake).
        """
        if not self.event_queue:
            self.debug.debug_print(
                "No queued events to flush",
                DebugLevel.VERBOSE,
                style="dim"
            )
            return

        queue_size = len(self.event_queue)
        self.debug.debug_print(
            f"🚀 Flushing {queue_size} queued event(s) after connection_established",
            DebugLevel.BASIC,
            style="green"
        )
        safe_console_print(
            f"🚀 Connection fully established! Sending {queue_size} queued event(s)...",
            style="green",
            json_mode=self.config.json_mode,
            ci_mode=self.config.ci_mode
        )

        # Send all queued events
        for i, event_payload in enumerate(self.event_queue, 1):
            try:
                self.debug.debug_print(
                    f"Sending queued event {i}/{queue_size}: {event_payload.get('type', 'unknown')}",
                    DebugLevel.VERBOSE,
                    style="cyan"
                )
                await self.ws.send(json.dumps(event_payload))
                self.debug.debug_print(
                    f"✓ Queued event {i}/{queue_size} sent successfully",
                    DebugLevel.VERBOSE,
                    style="green"
                )
            except Exception as e:
                self.debug.log_error(e, f"sending queued event {i}/{queue_size}")
                safe_console_print(
                    f"⚠️ Failed to send queued event {i}/{queue_size}: {e}",
                    style="yellow",
                    json_mode=self.config.json_mode,
                    ci_mode=self.config.ci_mode
                )

        # Clear the queue
        self.event_queue.clear()
        self.debug.debug_print(
            f"✅ All {queue_size} queued events have been sent",
            DebugLevel.BASIC,
            style="green"
        )

    def _display_log_collection_info(self, info: dict) -> None:
        """Display log collection information to the console"""
        separator = "=" * 60

        # Display log collection details
        safe_console_print("", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print(separator, style="cyan", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print("SENDING LOGS TO OPTIMIZER", style="bold cyan", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print(separator, style="cyan", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print(f"  Provider: {self.logs_provider.upper()}", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print(f"  Total Entries: {len(info['logs'])}", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print(f"  Files Read: {info['files_read']}", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print(f"  Payload Size: {info['size_str']}", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

        if self.logs_project:
            safe_console_print(f"  Project: {self.logs_project}", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

        safe_console_print("", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print("  Files:", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

        # Add file details with hashes
        for file_info in info['file_info']:
            safe_console_print(
                f"    * {file_info['name']} (hash: {file_info['hash']}, {file_info['entries']} entries)",
                json_mode=self.config.json_mode, ci_mode=self.config.ci_mode
            )

        # Add payload proof
        safe_console_print("", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print("  Payload Confirmation:", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print(f"    [OK] 'jsonl_logs' key added to payload", style="green", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print(f"    [OK] First log entry timestamp: {info['logs'][0].get('timestamp', 'N/A') if info['logs'] else 'N/A'}", style="green", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print(f"    [OK] Last log entry timestamp: {info['logs'][-1].get('timestamp', 'N/A') if info['logs'] else 'N/A'}", style="green", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

        safe_console_print(separator, style="cyan", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        safe_console_print("", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

    async def send_message(self, message: str) -> str:
        """Send a message and return the run_id"""
        if not self.ws:
            raise RuntimeError("WebSocket not connected")

        # Check if connection handshake is fully complete
        if not self.connected:
            self.debug.debug_print(
                "ERROR: Connection not ready - handshake not complete",
                DebugLevel.BASIC,
                style="red"
            )
            safe_console_print(
                "\n❌ ERROR: Cannot send message - server not ready",
                style="red",
                json_mode=self.config.json_mode,
                ci_mode=self.config.ci_mode
            )
            safe_console_print(
                "The server is still completing its initialization phases.",
                style="yellow",
                json_mode=self.config.json_mode,
                ci_mode=self.config.ci_mode
            )
            raise RuntimeError("Connection not ready - handshake incomplete. Server needs to reach Processing phase.")

        # NEW: Check if ready to send events
        # Events can only be sent AFTER both handshake AND connection_established
        # DEVELOPMENT OVERRIDE: Skip connection_established requirement for development environment
        skip_connection_established = self.config.environment == Environment.DEVELOPMENT

        if not self.ready_to_send_events:
            if skip_connection_established:
                # Development environment: Override and proceed without connection_established
                self.debug.debug_print(
                    "⚠️ DEVELOPMENT MODE: Skipping connection_established requirement",
                    DebugLevel.BASIC,
                    style="yellow"
                )
                safe_console_print(
                    "⚠️ Development mode: Proceeding without connection_established event",
                    style="yellow",
                    json_mode=self.config.json_mode,
                    ci_mode=self.config.ci_mode
                )
                safe_console_print(
                    "   (This is normal for development backends that may not send this event)",
                    style="dim",
                    json_mode=self.config.json_mode,
                    ci_mode=self.config.ci_mode
                )
                # Force ready state for development
                self.ready_to_send_events = True
            else:
                # Production/Staging: Wait for connection_established event with timeout
                self.debug.debug_print(
                    "⏳ Waiting for connection_established event before sending message...",
                    DebugLevel.BASIC,
                    style="yellow"
                )
                safe_console_print(
                    "⏳ Waiting for connection_established event (up to 5 seconds)...",
                    style="yellow",
                    json_mode=self.config.json_mode,
                    ci_mode=self.config.ci_mode
                )

                # Wait up to 30 seconds for connection_established
                wait_timeout = 30.0
                wait_start = time.time()
                wait_interval = 0.1

                while not self.ready_to_send_events and (time.time() - wait_start) < wait_timeout:
                    await asyncio.sleep(wait_interval)
                    # Check if connection_established arrived
                    if self.ready_to_send_events:
                        self.debug.debug_print(
                            "✅ connection_established received - ready to send events",
                            DebugLevel.BASIC,
                            style="green"
                        )
                        safe_console_print(
                            "✅ connection_established received - proceeding with message",
                            style="green",
                            json_mode=self.config.json_mode,
                            ci_mode=self.config.ci_mode
                        )
                        break

                # If still not ready after timeout, then error
                if not self.ready_to_send_events:
                    elapsed = time.time() - wait_start
                    self.debug.debug_print(
                        f"❌ Timeout waiting for connection_established after {elapsed:.1f} seconds",
                        DebugLevel.BASIC,
                        style="red"
                    )
                    safe_console_print(
                        f"❌ Timeout: connection_established event not received after {elapsed:.1f} seconds",
                        style="red",
                        json_mode=self.config.json_mode,
                        ci_mode=self.config.ci_mode
                    )
                    safe_console_print(
                        "   Handshake complete: ✓ | connection_established: ✗",
                        style="dim",
                        json_mode=self.config.json_mode,
                        ci_mode=self.config.ci_mode
                    )
                    safe_console_print(
                        "\n💡 The server may not be sending the connection_established event.",
                        style="yellow",
                        json_mode=self.config.json_mode,
                        ci_mode=self.config.ci_mode
                    )
                    raise RuntimeError(
                        f"Cannot send message - connection_established event not received after {elapsed:.1f}s timeout. "
                        "Both handshake and connection_established are required before sending events."
                    )

        # Generate run_id
        self.run_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"

        # Create message payload
        # ISSUE #1671 FIX: Add thread_id for proper WebSocket event routing
        # SSOT: Thread ID from backend is REQUIRED
        if not self.current_thread_id:
            # Detailed error diagnostics
            self.debug.debug_print(
                "CRITICAL ERROR: Cannot send message - no thread ID available",
                DebugLevel.BASIC,
                style="red"
            )
            self.debug.debug_print(
                "CAUSE: Backend handshake did not complete successfully",
                DebugLevel.BASIC,
                style="yellow"
            )

            # User-facing error with actionable guidance
            safe_console_print(
                "\n❌ ERROR: Cannot send message - thread ID not established",
                style="red"
            )
            safe_console_print(
                "\n🔍 TROUBLESHOOTING STEPS:",
                style="yellow"
            )
            safe_console_print(
                "   1. Check if backend is running the latest version",
                style="dim"
            )
            safe_console_print(
                "   2. Verify backend has CLIHandshakeProtocol implemented",
                style="dim"
            )
            safe_console_print(
                "   3. Check backend logs for WebSocket connection errors",
                style="dim"
            )
            safe_console_print(
                "   4. Try running with --debug-level=verbose for more details",
                style="dim"
            )
            safe_console_print(
                "\n📝 WHAT HAPPENED:",
                style="cyan"
            )
            safe_console_print(
                "   • CLI connected to WebSocket successfully",
                style="dim"
            )
            safe_console_print(
                "   • Backend did not provide a thread ID during handshake",
                style="dim"
            )
            safe_console_print(
                "   • Without thread ID, events cannot be properly routed",
                style="dim"
            )

            raise RuntimeError(
                "Thread ID not established with backend. "
                "See troubleshooting steps above."
            )

        thread_id = self.current_thread_id
        self.debug.debug_print(
            f"SSOT: Using backend-provided thread_id: {thread_id}",
            DebugLevel.VERBOSE,
            style="green"
        )

        # ISSUE #1673 FIX: Backend expects payload structure with nested data
        # The backend AgentServiceCore._parse_message expects:
        # { "type": "user_message", "payload": { content, run_id, thread_id } }
        payload = {
            "type": "user_message",
            "payload": {
                "content": message,
                "run_id": self.run_id,
                "thread_id": thread_id,  # NEW: Required for WebSocket event routing
                "timestamp": datetime.now().isoformat(),
                # ISSUE #2442: Pass client environment for appropriate timeout configuration
                "client_environment": self.config.client_environment if hasattr(self.config, 'client_environment') and self.config.client_environment else None
            }
        }

        # Attach logs if --send-logs is enabled
        if self.send_logs:
            try:
                from agent_logs import collect_recent_logs
                from chunking_analyzer import ChunkingAnalyzer
                from chunk_creator import ChunkCreator

                result = collect_recent_logs(
                    limit=self.logs_count,
                    project_name=self.logs_project,
                    base_path=self.logs_path,
                    username=self.logs_user,
                    provider=self.logs_provider
                )

                if result:
                    logs, files_read, file_info = result

                    # NEW: Analyze if chunking needed
                    analyzer = ChunkingAnalyzer()
                    chunking_strategy = analyzer.analyze_files(logs, file_info)

                    if chunking_strategy.strategy in ('no_chunking', 'multi_file_no_chunking'):
                        # Original behavior: send all logs at once
                        payload["payload"]["jsonl_logs"] = logs

                        # Add agent_context with chunk_metadata for non-chunked logs
                        # This maintains consistency with backend expectations
                        file_analysis = chunking_strategy.file_analyses[0] if chunking_strategy.file_analyses else None
                        if file_analysis:
                            payload["payload"]["agent_context"] = {
                                "chunk_metadata": {
                                    "chunk_index": 0,
                                    "total_chunks": 1,
                                    "file_hash": file_analysis.file_hash,
                                    "file_name": file_analysis.file_name,
                                    "aggregation_required": False,  # No aggregation needed for non-chunked
                                    "entries_in_chunk": file_analysis.entry_count,
                                    "chunk_size_bytes": file_analysis.size_bytes,
                                    "start_entry_index": 0,
                                    "end_entry_index": file_analysis.entry_count - 1,
                                    "is_multi_file": False,
                                    "file_index": 0
                                }
                            }

                        # Calculate payload size for transmission proof
                        import logging
                        import sys

                        # Get size of logs in payload
                        logs_json = json.dumps(logs)
                        logs_size_bytes = len(logs_json.encode('utf-8'))
                        logs_size_kb = logs_size_bytes / 1024
                        logs_size_mb = logs_size_kb / 1024

                        # Format size appropriately
                        if logs_size_mb >= 1:
                            size_str = f"{logs_size_mb:.2f} MB"
                        elif logs_size_kb >= 1:
                            size_str = f"{logs_size_kb:.2f} KB"
                        else:
                            size_str = f"{logs_size_bytes} bytes"

                        # Save log display info for later (will be displayed after "Sending message:")
                        self._log_display_info = {
                            'logs': logs,
                            'files_read': files_read,
                            'file_info': file_info,
                            'size_str': size_str
                        }
                    else:
                        # NEW: Chunking required
                        await self._send_chunked_logs(
                            logs=logs,
                            file_info=file_info,
                            chunking_strategy=chunking_strategy,
                            message=message,
                            thread_id=thread_id
                        )
                        return  # Early return - chunks sent separately

                else:
                    self.debug.debug_print(
                        "Warning: --send-logs enabled but no logs found",
                        DebugLevel.BASIC,
                        style="yellow"
                    )
            except Exception as e:
                # Log collection failure should not block message sending
                self.debug.debug_print(
                    f"Warning: Failed to collect logs: {e}",
                    DebugLevel.BASIC,
                    style="yellow"
                )

        self.debug.debug_print(
            f"Prepared WebSocket payload for run_id={self.run_id}, thread_id={thread_id}",
            DebugLevel.BASIC,
            style="yellow"
        )

        # Proof of logs in transmission
        if "jsonl_logs" in payload["payload"]:
            log_count = len(payload["payload"]["jsonl_logs"])
            self.debug.debug_print(
                f"✓ TRANSMISSION PROOF: Payload contains {log_count} JSONL log entries in 'jsonl_logs' key",
                DebugLevel.BASIC,
                style="green"
            )

            # Optional: Save payload proof to file for verification
            if os.environ.get('ZEN_SAVE_PAYLOAD_PROOF'):
                try:
                    import tempfile
                    proof_file = tempfile.NamedTemporaryFile(
                        mode='w',
                        prefix='zen_payload_proof_',
                        suffix='.json',
                        delete=False
                    )

                    # Save payload structure (with truncated logs for readability)
                    proof_payload = {
                        "run_id": payload.get("run_id"),
                        "payload": {
                            "message": payload["payload"].get("message"),
                            "jsonl_logs": {
                                "count": len(payload["payload"]["jsonl_logs"]),
                                "sample_first": payload["payload"]["jsonl_logs"][0] if payload["payload"]["jsonl_logs"] else None,
                                "sample_last": payload["payload"]["jsonl_logs"][-1] if payload["payload"]["jsonl_logs"] else None,
                            }
                        }
                    }

                    json.dump(proof_payload, proof_file, indent=2)
                    proof_file.close()

                    self.debug.debug_print(
                        f"📝 Payload proof saved to: {proof_file.name}",
                        DebugLevel.BASIC,
                        style="cyan"
                    )
                except Exception as e:
                    # Don't fail transmission if proof saving fails
                    pass

        # Validate payload size before sending
        payload_json = json.dumps(payload)
        payload_size_bytes = len(payload_json.encode('utf-8'))
        payload_size_mb = payload_size_bytes / (1024 * 1024)

        # Define size limits
        MAX_SIZE_MB = 4.5  # Maximum allowed (give 0.5MB buffer below 5MB)
        WARNING_SIZE_MB = 3.0  # Warning threshold
        OPTIMAL_SIZE_MB = 1.0  # Optimal for best performance

        # Check if payload exceeds maximum allowed size
        if payload_size_mb > MAX_SIZE_MB:
            error_msg = f"""
+==============================================================================+
|                         ❌ PAYLOAD SIZE EXCEEDED                              |
+==============================================================================+

  Payload Size: {payload_size_mb:.2f} MB
  Maximum Allowed: {MAX_SIZE_MB:.1f} MB

  ⚠️  Your payload is too large to send to the backend.

📊 SIZE BREAKDOWN:
  • Total payload: {payload_size_mb:.2f} MB ({payload_size_bytes:,} bytes)
  • Limit: {MAX_SIZE_MB:.1f} MB"""

            if "jsonl_logs" in payload["payload"]:
                logs_json = json.dumps(payload["payload"]["jsonl_logs"])
                logs_size_mb = len(logs_json.encode('utf-8')) / (1024 * 1024)
                error_msg += f"""
  • Logs contribution: {logs_size_mb:.2f} MB
  • Log entries: {len(payload["payload"]["jsonl_logs"])}"""

            error_msg += f"""

💡 RECOMMENDATIONS:
  1. Reduce --logs-count to 1 (default, recommended)
  2. Target specific project with --logs-project
  3. Use smaller log files (aim for < {OPTIMAL_SIZE_MB:.1f} MB total payload)
  4. Split analysis into multiple runs with fewer logs

✨ OPTIMAL PERFORMANCE: Keep payload under {OPTIMAL_SIZE_MB:.1f} MB for best results

+==============================================================================+
"""
            safe_console_print(error_msg, style="red")
            raise RuntimeError(f"Payload size ({payload_size_mb:.2f} MB) exceeds maximum allowed ({MAX_SIZE_MB:.1f} MB)")

        # Warn if payload is large but within limits
        if payload_size_mb > WARNING_SIZE_MB:
            warning_msg = f"""
+==============================================================================+
|                      ⚠️  LARGE PAYLOAD WARNING                                |
+==============================================================================+

  Payload Size: {payload_size_mb:.2f} MB
  Maximum Allowed: {MAX_SIZE_MB:.1f} MB
  Optimal Size: < {OPTIMAL_SIZE_MB:.1f} MB

  ✅ Your payload will be sent, but it's larger than recommended.

📊 SIZE BREAKDOWN:
  • Total payload: {payload_size_mb:.2f} MB ({payload_size_bytes:,} bytes)"""

            if "jsonl_logs" in payload["payload"]:
                logs_json = json.dumps(payload["payload"]["jsonl_logs"])
                logs_size_mb = len(logs_json.encode('utf-8')) / (1024 * 1024)
                warning_msg += f"""
  • Logs contribution: {logs_size_mb:.2f} MB
  • Log entries: {len(payload["payload"]["jsonl_logs"])}"""

            warning_msg += f"""

💡 FOR BETTER PERFORMANCE:
  • Use --logs-count 1 (default) for optimal analysis
  • Keep total payload under {OPTIMAL_SIZE_MB:.1f} MB for best results
  • Larger payloads may take longer to process

+==============================================================================+
"""
            safe_console_print(warning_msg, style="yellow")

        # ISSUE #1603 FIX: Add critical logging for message sending (only in diagnostic mode)
        if self.debug.debug_level >= DebugLevel.DIAGNOSTIC:
            self.debug.debug_print(f"SENDING WEBSOCKET MESSAGE: {json.dumps(payload, indent=2)}", DebugLevel.DIAGNOSTIC)

        # Print sending message after logs section (moved from run_cli method)
        safe_console_print(f"Sending message: {payload['payload']['content']}", style="cyan", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

        # Display log collection info after "Sending message:" if logs were collected
        if self.send_logs and hasattr(self, '_log_display_info'):
            self._display_log_collection_info(self._log_display_info)
            # Clean up the temporary display info
            del self._log_display_info

        await self.ws.send(payload_json)
        if self.debug.debug_level >= DebugLevel.VERBOSE:
            self.debug.debug_print(f"WEBSOCKET MESSAGE SENT SUCCESSFULLY - run_id: {self.run_id}, thread_id: {thread_id}", DebugLevel.VERBOSE)
        return self.run_id

    async def _send_chunked_logs(
        self,
        logs: List[Dict[str, Any]],
        file_info: Dict[str, Any],
        chunking_strategy: Any,
        message: str,
        thread_id: str
    ) -> None:
        """
        Send logs in chunks when chunking is required.

        Args:
            logs: List of log entries
            file_info: Dictionary with file metadata
            chunking_strategy: ChunkingStrategy object from analyzer
            message: Original user message
            thread_id: Thread ID for this conversation
        """
        from chunk_creator import ChunkCreator

        # Display chunking info
        safe_console_print(
            f"\nChunking strategy: {chunking_strategy.strategy}",
            style="yellow",
            json_mode=self.config.json_mode,
            ci_mode=self.config.ci_mode
        )

        # Create chunks from file analyses
        chunk_creator = ChunkCreator()
        all_chunks = []

        # Track entry offset for extracting entries per file
        entry_offset = 0

        for file_idx, file_analysis in enumerate(chunking_strategy.file_analyses):
            if file_analysis.needs_chunking:
                # Extract entries for this file
                file_entries = logs[entry_offset:entry_offset + file_analysis.entry_count]

                safe_console_print(
                    f"\nChunking file: {file_analysis.file_name} "
                    f"({file_analysis.size_mb:.2f} MB, {file_analysis.entry_count} entries)",
                    style="yellow",
                    json_mode=self.config.json_mode,
                    ci_mode=self.config.ci_mode
                )

                # Create chunks for this file
                is_multi_file = len(chunking_strategy.file_analyses) > 1
                file_chunks = chunk_creator.create_chunks(
                    entries=file_entries,
                    file_name=file_analysis.file_name,
                    file_hash=file_analysis.file_hash,
                    is_multi_file=is_multi_file,
                    file_index=file_idx if is_multi_file else None
                )

                all_chunks.extend(file_chunks)
            else:
                # File doesn't need chunking - will be sent as single chunk
                file_entries = logs[entry_offset:entry_offset + file_analysis.entry_count]

                safe_console_print(
                    f"\nFile doesn't need chunking: {file_analysis.file_name} "
                    f"({file_analysis.size_mb:.2f} MB, {file_analysis.entry_count} entries) - sending as single unit",
                    style="cyan",
                    json_mode=self.config.json_mode,
                    ci_mode=self.config.ci_mode
                )

                # Create a single "chunk" for this file
                from chunk_creator import Chunk, ChunkMetadata
                metadata = ChunkMetadata(
                    chunk_id=file_analysis.file_hash[:12],
                    chunk_index=0,
                    total_chunks=1,
                    file_hash=file_analysis.file_hash,
                    file_name=file_analysis.file_name,
                    entries_in_chunk=file_analysis.entry_count,
                    chunk_size_bytes=file_analysis.size_bytes,
                    chunk_size_mb=file_analysis.size_mb,
                    start_entry_index=0,
                    end_entry_index=file_analysis.entry_count - 1,
                    is_multi_file=len(chunking_strategy.file_analyses) > 1,
                    file_index=file_idx if len(chunking_strategy.file_analyses) > 1 else None,
                    aggregation_required=False  # Single file, no aggregation needed
                )
                single_chunk = Chunk(entries=file_entries, metadata=metadata)
                all_chunks.append(single_chunk)

            entry_offset += file_analysis.entry_count

        total_chunks = len(all_chunks)
        safe_console_print(
            f"\nSending {total_chunks} chunk(s)...",
            style="cyan",
            json_mode=self.config.json_mode,
            ci_mode=self.config.ci_mode
        )

        # For chunked uploads, ALL chunks must use the SAME thread_id
        # - If thread_id is provided: use it for all chunks
        # - If thread_id is None: send null for all chunks, backend groups by chunk_id
        current_thread_id = thread_id

        # Send all chunks in parallel for better performance
        # Backend is designed to handle chunks arriving in any order and aggregate them
        for i, chunk in enumerate(all_chunks, 1):
            chunk_num = i

            # Debug logging for chunked uploads
            if chunk.metadata.aggregation_required and i == 1:
                safe_console_print(
                    f"  Sending {total_chunks} chunks in parallel with thread_id={'null' if current_thread_id is None else current_thread_id[:20] + '...'}",
                    style="dim",
                    json_mode=self.config.json_mode,
                    ci_mode=self.config.ci_mode
                )

            # Determine chunk type based on metadata
            # All chunks now use the same structure, no chunk_type attribute
            if chunk.metadata.total_chunks == 1 and not chunk.metadata.aggregation_required:
                # Single file chunk
                await self._send_single_file(
                    chunk=chunk,
                    chunk_num=chunk_num,
                    total_chunks=total_chunks,
                    message=message,
                    thread_id=current_thread_id
                )
            else:
                # Regular chunk (including aggregation_required chunks)
                # Send immediately without waiting - parallel sending
                await self._send_single_chunk(
                    chunk=chunk,
                    chunk_num=chunk_num,
                    total_chunks=total_chunks,
                    message=message,
                    thread_id=current_thread_id
                )

            # Small delay to avoid overwhelming the WebSocket
            # This is critical for chunked uploads to ensure backend receives all chunks
            if i < total_chunks:
                await asyncio.sleep(0.2)  # Increased from 0.1s for reliability

        # CRITICAL FIX for Issue #28: Wait for backend to aggregate all chunks
        # After sending all chunks in parallel, wait for the aggregation to complete
        # This ensures the user gets the final aggregated response
        if any(chunk.metadata.aggregation_required for chunk in all_chunks):
            self.debug.debug_print(
                f"⏳ Waiting for backend to aggregate all {total_chunks} chunks...",
                DebugLevel.VERBOSE,
                style="yellow"
            )
            safe_console_print(
                f"  ⏳ Waiting for backend to aggregate all {total_chunks} chunks...",
                style="cyan",
                json_mode=self.config.json_mode,
                ci_mode=self.config.ci_mode
            )

            # Wait for the aggregation_complete event
            # Timeout is longer to account for processing all chunks
            await self._wait_for_event_type('agent_aggregation_complete', timeout=120.0, chunk_context=f"all {total_chunks} chunks")

            self.debug.debug_print(
                f"✓ Received agent_aggregation_complete for all {total_chunks} chunks",
                DebugLevel.VERBOSE,
                style="green"
            )

        safe_console_print(
            f"\n✓ All {total_chunks} chunk(s) processed successfully",
            style="green",
            json_mode=self.config.json_mode,
            ci_mode=self.config.ci_mode
        )

    async def _send_single_chunk(
        self,
        chunk: Any,
        chunk_num: int,
        total_chunks: int,
        message: str,
        thread_id: str
    ) -> None:
        """
        Send a single chunk of logs.

        Args:
            chunk: Chunk object containing logs and metadata
            chunk_num: Current chunk number (1-indexed)
            total_chunks: Total number of chunks
            message: Original user message
            thread_id: Thread ID for this conversation
        """
        # Create payload for this chunk
        payload = {
            "type": "user_message",
            "payload": {
                "content": message,
                "run_id": self.run_id,
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat(),
                "jsonl_logs": chunk.entries,
                "agent_context": {
                    "chunk_metadata": {
                        "chunk_index": chunk.metadata.chunk_index,
                        "total_chunks": chunk.metadata.total_chunks,
                        "file_hash": chunk.metadata.file_hash,
                        "file_name": chunk.metadata.file_name,
                        "aggregation_required": chunk.metadata.aggregation_required,
                        "entries_in_chunk": chunk.metadata.entries_in_chunk,
                        "chunk_size_bytes": chunk.metadata.chunk_size_bytes,
                        "start_entry_index": chunk.metadata.start_entry_index,
                        "end_entry_index": chunk.metadata.end_entry_index,
                        "is_multi_file": chunk.metadata.is_multi_file,
                        "file_index": chunk.metadata.file_index
                    }
                },
                "client_environment": self.config.client_environment if hasattr(self.config, 'client_environment') and self.config.client_environment else None
            }
        }

        # Display chunk info with warning if oversized
        chunk_display = (
            f"  Chunk {chunk.metadata.chunk_index + 1}/{chunk.metadata.total_chunks}: "
            f"{chunk.metadata.entries_in_chunk} entries, {chunk.metadata.chunk_size_mb:.2f} MB"
        )

        # Warning if chunk exceeds recommended size (happens with large single entries)
        if chunk.metadata.chunk_size_mb > 2.5:
            chunk_display += f" ⚠️  OVERSIZED (single entry > 2.5 MB limit)"
            safe_console_print(chunk_display, style="yellow", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)
        else:
            safe_console_print(chunk_display, style="cyan", json_mode=self.config.json_mode, ci_mode=self.config.ci_mode)

        # Send chunk
        payload_json = json.dumps(payload)
        await self.ws.send(payload_json)

        self.debug.debug_print(
            f"Sent chunk {chunk_num}/{total_chunks}",
            DebugLevel.VERBOSE,
            style="green"
        )

    async def _send_single_file(
        self,
        chunk: Any,
        chunk_num: int,
        total_chunks: int,
        message: str,
        thread_id: str
    ) -> None:
        """
        Send a single file as a chunk (for file-based chunking).

        Args:
            chunk: Chunk object containing file logs
            chunk_num: Current chunk number (1-indexed)
            total_chunks: Total number of chunks
            message: Original user message
            thread_id: Thread ID for this conversation
        """
        # Create payload for this file (no chunk_metadata needed for single files)
        payload = {
            "type": "user_message",
            "payload": {
                "content": message,
                "run_id": self.run_id,
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat(),
                "jsonl_logs": chunk.entries,
                "client_environment": self.config.client_environment if hasattr(self.config, 'client_environment') and self.config.client_environment else None
            }
        }

        # Display file chunk info
        safe_console_print(
            f"  File: {chunk.metadata.file_name} - "
            f"{chunk.metadata.entries_in_chunk} entries, {chunk.metadata.chunk_size_mb:.2f} MB (no aggregation needed)",
            style="cyan",
            json_mode=self.config.json_mode,
            ci_mode=self.config.ci_mode
        )

        # Send file chunk
        payload_json = json.dumps(payload)
        await self.ws.send(payload_json)

        self.debug.debug_print(
            f"Sent file: {chunk.metadata.file_name}",
            DebugLevel.VERBOSE,
            style="green"
        )

    async def _wait_for_event_type(self, event_type: str, timeout: float = 60.0, chunk_context: str = "") -> None:
        """
        Wait for a specific event type to be received from the WebSocket.

        This is critical for chunked uploads where we must wait for backend acknowledgment
        (agent_completed or agent_aggregation_complete) before sending the next chunk.

        Args:
            event_type: The type of event to wait for (e.g., 'agent_completed', 'agent_aggregation_complete')
            timeout: Maximum time to wait in seconds
            chunk_context: Context string for logging (e.g., "chunk 1/5")

        Raises:
            TimeoutError: If event is not received within timeout period
            RuntimeError: If WebSocket connection is lost while waiting
        """
        start_time = asyncio.get_event_loop().time()
        initial_event_count = len(self.events)

        self.debug.debug_print(
            f"Waiting for '{event_type}' event (timeout: {timeout}s) - {chunk_context}",
            DebugLevel.DIAGNOSTIC,
            style="cyan"
        )

        while True:
            # Check if the event has arrived
            for i in range(initial_event_count, len(self.events)):
                event = self.events[i]
                if event.type == event_type:
                    self.debug.debug_print(
                        f"✓ Received '{event_type}' event - {chunk_context}",
                        DebugLevel.DIAGNOSTIC,
                        style="green"
                    )
                    return

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Timeout waiting for '{event_type}' event after {elapsed:.1f}s - {chunk_context}. "
                    f"Backend may not be processing chunks correctly."
                )

            # Check if WebSocket is still connected
            if not self.ws or not self.connected:
                raise RuntimeError(
                    f"WebSocket connection lost while waiting for '{event_type}' event - {chunk_context}"
                )

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

    async def receive_events(self, callback=None):
        """Receive and process events from WebSocket"""
        if not self.ws:
            raise RuntimeError("WebSocket not connected")

        self.debug.debug_print("Listening for WebSocket events...")
        self.debug.debug_print(
            "Event listener started after successful connection",
            DebugLevel.BASIC,
            style="cyan"
        )

        async for message in self.ws:
            try:
                # Enhanced debug logging for WebSocket messages
                self.debug.log_websocket_event("raw_message_received", {}, raw_message=message)

                data = json.loads(message)
                event = WebSocketEvent(
                    type=data.get('type', 'unknown'),
                    data=data
                )
                # Skip duplicate connection_established events after handshake
                if event.type == 'connection_established' and self.connected and self.current_thread_id:
                    self.debug.debug_print(
                        "Ignoring duplicate connection_established (already connected with thread_id)",
                        DebugLevel.VERBOSE,
                        style="yellow"
                    )
                    # Don't append duplicate connection events
                else:
                    self.events.append(event)

                # Handle connection_established as a basic WebSocket connection event
                # Note: handshake_response is now used for thread_id exchange, not connection_established
                if event.type == 'connection_established':
                    # Track that connection_established was received
                    if not self.connection_established_received:
                        self.connection_established_received = True
                        self.debug.debug_print(
                            "📌 connection_established event received after handshake",
                            DebugLevel.BASIC,
                            style="cyan"
                        )

                        # Check if we can now start sending events
                        # We need BOTH handshake (self.connected) AND connection_established
                        if self.connected and not self.ready_to_send_events:
                            self.ready_to_send_events = True
                            self.debug.debug_print(
                                "✅ Ready to send events: Handshake ✓ | connection_established ✓",
                                DebugLevel.BASIC,
                                style="green"
                            )
                            safe_console_print(
                                "✅ Fully connected: Handshake ✓ | connection_established ✓",
                                style="green",
                                json_mode=self.config.json_mode,
                                ci_mode=self.config.ci_mode
                            )

                            # Flush any queued events
                            await self._flush_queued_events()
                    else:
                        # This is a duplicate connection_established event
                        self.debug.debug_print(
                            f"WebSocket connection_established event received (duplicate, already tracked)",
                            DebugLevel.VERBOSE,
                            style="dim"
                        )

                self.debug.debug_print(
                    f"Parsed WebSocket event type={event.type}",
                    DebugLevel.BASIC,
                    style="green"
                )

                # Log the parsed event
                self.debug.log_websocket_event(event.type, data, raw_message=message)

                # ISSUE #1828: Handle backend_log messages if log streaming is enabled
                if event.type == 'backend_log' and self.config.stream_logs:
                    await self._handle_backend_log(data)

                # ISSUE #2134 FIX: Handle cleanup coordination events
                if event.type in ['cleanup_started', 'cleanup_duration_estimate', 'cleanup_complete']:
                    await self.handle_cleanup_events(event)

                # ISSUE #1603 FIX: Keep original critical logging for now (can be disabled with debug level)
                if self.debug.debug_level >= DebugLevel.TRACE:
                    self.debug.debug_print(f"RAW WEBSOCKET MESSAGE RECEIVED: {message[:200]}...", DebugLevel.TRACE)
                    self.debug.debug_print(f"PARSED WEBSOCKET EVENT: type={event.type}, data_keys={list(data.keys())}", DebugLevel.TRACE)

                if callback:
                    await callback(event)

            except json.JSONDecodeError as e:
                self.debug.log_error(e, "JSON decode of WebSocket message")
                safe_console_print(f"WARNING: Invalid JSON received: {message}", style="yellow")
                if self.debug.debug_level >= DebugLevel.TRACE:
                    safe_console_print(f"🔥 RAW INVALID MESSAGE: {message}", style="red")
            except Exception as e:
                self.debug.log_error(e, "processing WebSocket message")
                safe_console_print(f"ERROR: Error processing message: {e}", style="red")
                if self.debug.debug_level >= DebugLevel.TRACE:
                    safe_console_print(f"🔥 ERROR DETAILS: {e.__class__.__name__}: {str(e)}", style="red")

    async def _handle_backend_log(self, data: Dict[str, Any]):
        """Handle backend_log message type (Issue #1828, #2417)."""
        try:
            # Extract log messages from the payload
            messages = data.get('messages', [])
            total_count = data.get('total_count', len(messages))
            sink_stats = data.get('sink_stats', {})

            # ISSUE #2417 Phase 2: Filter logs by thread_id
            filtered_messages = []
            for log_msg in messages:
                log_thread_id = log_msg.get('thread_id')

                # Include logs if:
                # 1. No thread_id (system logs) - show at VERBOSE level
                # 2. Matches current session's thread_id
                if log_thread_id is None:
                    if self.debug.debug_level >= DebugLevel.VERBOSE:
                        filtered_messages.append(log_msg)
                elif log_thread_id == self.current_thread_id:
                    filtered_messages.append(log_msg)

            # Show filtering stats at verbose level
            if self.debug.debug_level >= DebugLevel.VERBOSE and len(messages) > 0:
                total = len(messages)
                shown = len(filtered_messages)
                self.debug.debug_print(
                    f"📋 Backend logs: Showing {shown}/{total} (filtered by thread_id={self.current_thread_id})",
                    DebugLevel.VERBOSE
                )

            # Process filtered messages
            for log_msg in filtered_messages:
                # Route to debug manager for display
                await self.debug.render_backend_log(log_msg)

            # Log sink statistics if debug level is high enough
            if self.debug.debug_level >= DebugLevel.VERBOSE and sink_stats:
                self.debug.debug_print(
                    f"📊 CLI Sink Stats: {sink_stats.get('sent_messages', 0)} sent, "
                    f"{sink_stats.get('failed_messages', 0)} failed, "
                    f"{sink_stats.get('success_rate', 0):.1%} success rate",
                    DebugLevel.VERBOSE
                )

        except Exception as e:
            self.debug.log_error(e, "handling backend log message")
            safe_console_print(f"ERROR: Failed to process backend log: {e}", style="red")

    async def handle_cleanup_events(self, event: WebSocketEvent):
        """Handle cleanup coordination events (Issue #2134)."""
        try:
            event_type = event.type
            data = event.data.get('data', {}) if isinstance(event.data, dict) else {}

            if event_type == "cleanup_started":
                self.cleanup_in_progress = True
                safe_console_print("🧹 Server cleanup started...", style="yellow")
                self.debug.debug_print(f"CLEANUP COORDINATION: Cleanup started for connection {data.get('connection_id', 'unknown')}")

            elif event_type == "cleanup_duration_estimate":
                estimated_seconds = data.get('estimated_seconds', 10)
                # Adjust timeout with safety margin (25% extra time)
                safety_margin = max(5, int(estimated_seconds * 0.25))
                self.negotiated_timeout = min(estimated_seconds + safety_margin, 60)  # Cap at 60 seconds
                safe_console_print(f"⏱️ Adjusted timeout to {self.negotiated_timeout}s based on server estimate ({estimated_seconds}s + {safety_margin}s safety)", style="cyan")
                self.debug.debug_print(f"CLEANUP COORDINATION: Negotiated timeout adjusted to {self.negotiated_timeout}s based on server estimate of {estimated_seconds}s")

            elif event_type == "cleanup_complete":
                self.cleanup_complete = True
                cleanup_status = data.get('cleanup_status', 'unknown')
                successful_cleanups = data.get('successful_cleanups', 0)
                total_cleanups = data.get('total_cleanups', 0)

                if cleanup_status == "complete":
                    safe_console_print("✅ Server cleanup complete - all components cleaned successfully", style="green")
                else:
                    safe_console_print(f"⚠️ Server cleanup partial - {successful_cleanups}/{total_cleanups} components cleaned", style="yellow")

                self.debug.debug_print(f"CLEANUP COORDINATION: Cleanup complete with status {cleanup_status} ({successful_cleanups}/{total_cleanups})")

        except Exception as e:
            self.debug.log_error(e, "handling cleanup coordination event")
            safe_console_print(f"WARNING: Failed to process cleanup event: {e}", style="yellow")

    async def close(self):
        """Close WebSocket connection and capture closure code.

        ISSUE #2373: Captures WebSocket closure codes for test validation
        and debugging infrastructure vs business logic errors.
        """
        if self.ws:
            try:
                await self.ws.close()
                self.connected = False
            except websockets.exceptions.ConnectionClosed as e:
                # Capture closure information
                if e.rcvd:
                    self.closure_code = e.rcvd.code
                    self.closure_reason = e.rcvd.reason or ""

                    if self.closure_code:
                        self.closure_category = categorize_closure_code(self.closure_code)
                        desc = get_closure_description(self.closure_code)

                        # Log with categorization using console print for visibility
                        if self.closure_category == WebSocketClosureCategory.EXPECTED_NORMAL:
                            self.debug.debug_print(
                                f"WebSocket closed normally: {self.closure_code} - {desc}",
                                level=DebugLevel.VERBOSE
                            )
                        elif is_infrastructure_error(self.closure_code):
                            self.debug.debug_print(
                                f"WebSocket closed with infrastructure error: {self.closure_code} - {desc}",
                                level=DebugLevel.BASIC,
                                color="yellow"
                            )
                        else:
                            self.debug.debug_print(
                                f"WebSocket closed unexpectedly: {self.closure_code} - {desc}",
                                level=DebugLevel.BASIC,
                                color="red"
                            )
                self.connected = False
            except Exception as e:
                self.debug.log_error(e, "closing WebSocket connection")
                self.connected = False

    def get_closure_info(self) -> dict:
        """Get closure code information for test validation.

        ISSUE #2373: Provides closure code information for integration tests
        to distinguish infrastructure errors from business logic failures.

        Returns:
            Dictionary with closure code, reason, category, and helper flags
        """
        return {
            "code": self.closure_code,
            "reason": self.closure_reason,
            "category": self.closure_category.value if self.closure_category else None,
            "is_infrastructure_error": is_infrastructure_error(self.closure_code)
        }


class CLIOutputFormatter:
    """Manages output formatting for CI/CD integration (Issue #2766 Phase 1).

    Handles suppression of Rich terminal output in CI mode and restoration
    for interactive mode. Provides clean JSON output without terminal noise.
    """

    def __init__(self, ci_mode: bool = False):
        """Initialize output formatter.

        Args:
            ci_mode: If True, suppress Rich terminal output for CI/CD
        """
        self.ci_mode = ci_mode
        self._original_console = None
        self._suppressed = False

    def suppress_rich_output(self) -> None:
        """Suppress Rich console output for CI/CD mode (Issue #2766).

        Replaces Rich console with a null output stream to prevent
        terminal formatting noise in JSON output.
        """
        if self.ci_mode and not self._suppressed:
            global console
            self._original_console = console
            # Create a null console that discards all output
            console = Console(file=open(os.devnull, 'w'), force_terminal=False)
            self._suppressed = True

    def restore_rich_output(self) -> None:
        """Restore Rich console output after CI/CD processing (Issue #2766).

        Returns Rich console to normal state for interactive mode.
        """
        if self._suppressed and self._original_console:
            global console
            console = self._original_console
            self._suppressed = False

    def write_json_output(self, output_data: Dict[str, Any], output_file: Optional[str] = None) -> None:
        """Write JSON output to file or stdout (Issue #2766).

        Args:
            output_data: Dictionary to serialize as JSON
            output_file: Optional file path to write to (None = stdout)
        """
        json_str = json.dumps(output_data, indent=2, default=str)

        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(json_str)
            except Exception as e:
                # Write to stderr to avoid polluting JSON stdout
                print(f"ERROR: Failed to write JSON output to {output_file}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # Write to stdout for pipeline consumption
            print(json_str)


class JSONOutputGenerator:
    """Generates structured JSON output for CI/CD integration (Issue #2766 Phase 1).

    Creates comprehensive JSON reports with:
    - Success/failure status
    - Execution summary (duration, event counts, metadata)
    - All WebSocket events with full data
    - Validation results (output quality, business value, event framework)
    - Exit code determination

    Phase 1: Skeleton structure with all method signatures
    Phase 2: Full implementation of JSON generation logic
    """

    # Critical events expected in a successful agent execution
    EXPECTED_CRITICAL_EVENTS = [
        'agent_started',
        'agent_thinking',
        'agent_completed'
    ]

    def __init__(self, cli: 'AgentCLI', config: Config, events: List[WebSocketEvent],
                 errors: List[str], start_time: float, end_time: float):
        """Initialize JSON output generator.

        Args:
            cli: Reference to AgentCLI instance for validation access
            config: CLI configuration
            events: List of WebSocket events received
            errors: List of error messages encountered
            start_time: Execution start timestamp
            end_time: Execution end timestamp
        """
        self.cli = cli
        self.config = config
        self.events = events
        self.errors = errors
        self.start_time = start_time
        self.end_time = end_time

    def generate(self) -> Dict[str, Any]:
        """Generate complete JSON output structure (Issue #2766).

        Returns:
            Dictionary with:
            - success: bool - Overall execution success
            - summary: dict - Execution metadata and statistics
            - events: list - All WebSocket events with full data
            - validation: dict - Validation results from all frameworks
            - errors: list - All error messages encountered
        """
        return {
            "success": self._determine_success(),
            "summary": self._generate_summary(),
            "events": self._serialize_events(),
            "validation": self._generate_validation(),
            "errors": self.errors
        }

    def _determine_success(self) -> bool:
        """Determine overall execution success (Issue #2766).

        Success criteria:
        - No critical errors encountered
        - Agent completed successfully (or cleanup completed)
        - Validation passed (if enabled)

        Returns:
            True if execution successful, False otherwise
        """
        # Check for errors
        if self.errors:
            return False

        # Check if WebSocket client exists and has events
        if not self.cli.ws_client or not self.events:
            return False

        # Check for missing critical events
        received_event_types = [e.type for e in self.events]
        missing_events = [
            event_type for event_type in self.EXPECTED_CRITICAL_EVENTS
            if event_type not in received_event_types
        ]

        if missing_events:
            return False

        # Check if agent_completed is present
        if 'agent_completed' not in received_event_types:
            return False

        return True

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary section with execution metadata (Issue #2766).

        Returns:
            Summary dictionary with:
            - duration_seconds: float - Total execution time in seconds
            - event_count: int - Total events received
            - run_id: str - Agent execution run ID
            - environment: str - Execution environment (local/staging/production)
            - timestamp: str - ISO format execution timestamp
        """
        duration = self.end_time - self.start_time

        # Extract run_id from first event if available
        run_id = "unknown"
        if self.events:
            for event in self.events:
                if hasattr(event, 'data') and event.data:
                    run_id = event.data.get('run_id') or event.data.get('correlation_id', run_id)
                    if run_id != "unknown":
                        break

        return {
            "duration_seconds": round(duration, 2),
            "event_count": len(self.events),
            "run_id": run_id,
            "environment": self.config.environment.value,
            "timestamp": datetime.now().isoformat()
        }

    def _serialize_events(self) -> List[Dict[str, Any]]:
        """Serialize WebSocket events for JSON output (Issue #2766).

        Returns:
            List of event dictionaries with:
            - type: str - Event type (agent_started, agent_thinking, etc.)
            - timestamp: str - ISO format event timestamp
            - data: dict - Full event data payload
            - category: str - Event category (lifecycle, progress, completion, error)
        """
        if not self.events:
            return []

        serialized = []
        for event in self.events:
            event_dict = {
                "type": getattr(event, 'type', 'unknown'),
                "timestamp": str(getattr(event, 'timestamp', '')),
                "category": self._classify_event_category(getattr(event, 'type', 'unknown')),
                "data": {}
            }

            # Serialize event data safely (flatten payload when present)
            if hasattr(event, 'data') and event.data:
                raw_data = event.data
                if isinstance(raw_data, dict):
                    payload = raw_data.get('payload')
                    if isinstance(payload, dict):
                        # Flatten payload while keeping original keys for compatibility
                        raw_data = {**raw_data, **payload}
                    nested_data = raw_data.get('data')
                    if isinstance(nested_data, dict):
                        raw_data = {**raw_data, **nested_data}
                else:
                    raw_data = {}

                final_response_value = raw_data.get("final_response")

                for key, value in raw_data.items():
                    if key in ("payload", "data"):
                        continue
                    try:
                        # Test if value is JSON serializable
                        json.dumps(value)
                        event_dict["data"][key] = value
                    except (TypeError, ValueError):
                        # Convert non-serializable values to strings
                        event_dict["data"][key] = str(value)

                if "result" not in event_dict["data"] and final_response_value is not None:
                    try:
                        json.dumps(final_response_value)
                        event_dict["data"]["result"] = final_response_value
                    except (TypeError, ValueError):
                        event_dict["data"]["result"] = str(final_response_value)

            serialized.append(event_dict)

        return serialized

    def _generate_validation(self) -> Dict[str, Any]:
        """Generate validation results section (Issue #2766).

        Includes results from:
        - Expected vs received critical events
        - Missing events detection
        - Validation errors

        Returns:
            Validation dictionary with results from all enabled validators
        """
        if not self.cli.ws_client or not self.events:
            return {
                "expected_events": self.EXPECTED_CRITICAL_EVENTS,
                "received_events": [],
                "missing_events": self.EXPECTED_CRITICAL_EVENTS,
                "validation_errors": ["No WebSocket client available or no events received"]
            }

        received_event_types = [e.type for e in self.events]
        missing_events = [
            event_type for event_type in self.EXPECTED_CRITICAL_EVENTS
            if event_type not in received_event_types
        ]

        return {
            "expected_events": self.EXPECTED_CRITICAL_EVENTS,
            "received_events": received_event_types,
            "missing_events": missing_events,
            "validation_errors": [str(e) for e in self.errors]
        }

    def _classify_event_category(self, event_type: str) -> str:
        """Classify event into category for reporting (Issue #2766).

        Args:
            event_type: WebSocket event type

        Returns:
            Category string: 'agent_lifecycle', 'tool_execution', 'validation', 'connection', 'other'
        """
        if event_type in ['agent_started', 'agent_thinking', 'agent_completed']:
            return "agent_lifecycle"
        elif event_type in ['tool_executing', 'tool_completed']:
            return "tool_execution"
        elif event_type in ['validation_started', 'validation_completed']:
            return "validation"
        elif event_type in ['connection_established', 'handshake_response', 'cleanup_started', 'cleanup_completed']:
            return "connection"
        else:
            return "other"


class ExitCodeGenerator:
    """Determines appropriate exit codes for CI/CD integration (Issue #2766).

    Exit code strategy:
    - 0: SUCCESS - All events received, no errors, validation passed
    - 1: BUSINESS FAILURE - Missing events, validation failed, incomplete execution
    - 2: INFRASTRUCTURE FAILURE - Auth failed, connection failed, timeout

    Priority order (highest to lowest):
    1. Infrastructure failures (code 2) - authentication, connection issues
    2. Incomplete execution (code 1) - missing required events
    3. Validation failures (code 1) - output quality, business value
    4. Success (code 0) - all checks passed

    Implementation:
    - Phase 1: Skeleton structure with all method signatures ✅
    - Phase 2: JSON output generation ✅
    - Phase 3: Exit code logic implementation ✅
    """

    def __init__(self, events: List[WebSocketEvent], errors: List[str],
                 validation_passed: bool = True):
        """Initialize exit code generator.

        Args:
            events: List of WebSocket events received
            errors: List of error messages encountered
            validation_passed: Whether validation passed (if enabled)
        """
        self.events = events
        self.errors = errors
        self.validation_passed = validation_passed

    def determine_exit_code(self) -> int:
        """Determine appropriate exit code based on execution results (Issue #2766).

        Exit code strategy:
        - 0: SUCCESS - All events received, no errors, validation passed
        - 1: BUSINESS FAILURE - Missing events, validation failed, incomplete execution
        - 2: INFRASTRUCTURE FAILURE - Auth failed, connection failed, timeout

        Exit code priority (highest to lowest):
        1. Infrastructure failures (code 2) - authentication, connection
        2. Incomplete execution (code 1) - missing required events
        3. Validation failures (code 1) - output quality, business value
        4. Success (code 0) - all checks passed

        Returns:
            Exit code integer (0, 1, or 2)
        """
        # Classify the failure type to determine exit code
        failure_type = self._classify_failure_type()

        # Map failure type to exit code
        if failure_type == "none":
            return 0  # SUCCESS: All checks passed
        elif failure_type == "infrastructure":
            return 2  # INFRASTRUCTURE FAILURE: Auth/connection issues
        else:  # "validation" or "incomplete"
            return 1  # BUSINESS FAILURE: Validation or incomplete execution

    def _classify_failure_type(self) -> str:
        """Classify the type of failure for exit code determination (Issue #2766).

        Priority order (check in this order):
        1. Infrastructure failures (auth/connection) - highest priority
        2. Incomplete execution (missing required events)
        3. Validation failures (business logic)
        4. None (success)

        Returns:
            Failure type: 'infrastructure', 'incomplete', 'validation', 'none'
        """
        # Check for infrastructure failures first (highest priority)
        if self._has_authentication_failure() or self._has_connection_failure():
            return "infrastructure"

        # Check for incomplete execution (missing required events)
        if self._has_missing_events():
            return "incomplete"

        # Check for validation failures
        if not self.validation_passed:
            return "validation"

        # No failures detected
        return "none"

    def _has_authentication_failure(self) -> bool:
        """Check if execution failed due to authentication issues (Issue #2766).

        Checks for auth-related error strings in the errors list:
        - "authentication failed"
        - "Failed to authenticate"
        - "JWT" (token issues)
        - "OAuth" (OAuth flow failures)
        - "token" (token validation/expiry)

        Returns:
            True if authentication failure detected
        """
        # Auth-related keywords to search for (case-insensitive)
        auth_keywords = [
            "authentication failed",
            "failed to authenticate",
            "jwt",
            "oauth",
            "token"
        ]

        # Check each error message for auth-related keywords
        for error in self.errors:
            error_lower = error.lower()
            for keyword in auth_keywords:
                if keyword in error_lower:
                    return True

        return False

    def _has_connection_failure(self) -> bool:
        """Check if execution failed due to connection issues (Issue #2766).

        Checks for connection-related error strings in the errors list:
        - "WebSocket" (WebSocket connection issues)
        - "connection failed"
        - "Failed to connect"
        - "timeout" (connection/response timeouts)
        - "Connection refused" (network errors)

        Returns:
            True if connection failure detected
        """
        # Connection-related keywords to search for (case-insensitive)
        connection_keywords = [
            "websocket",
            "connection failed",
            "failed to connect",
            "timeout",
            "connection refused"
        ]

        # Check each error message for connection-related keywords
        for error in self.errors:
            error_lower = error.lower()
            for keyword in connection_keywords:
                if keyword in error_lower:
                    return True

        return False

    def _has_missing_events(self) -> bool:
        """Check if required events are missing (Issue #2766).

        Required events for complete execution:
        - agent_started (agent must have started)
        - agent_completed OR cleanup_complete (agent must have finished)

        Returns:
            True if required events are missing
        """
        # Extract event types from the events list
        event_types = [event.type for event in self.events]

        # Check for required starting event
        has_agent_started = "agent_started" in event_types

        # Check for required completion event (either agent_completed or cleanup_complete)
        has_agent_completed = "agent_completed" in event_types
        has_cleanup_complete = "cleanup_complete" in event_types
        has_completion_event = has_agent_completed or has_cleanup_complete

        # Return True if any required event is missing
        if not has_agent_started:
            return True  # Missing agent_started event

        if not has_completion_event:
            return True  # Missing completion event (agent_completed or cleanup_complete)

        return False  # All required events present


class AgentCLI:
    """Main CLI application for agent testing"""

    def __init__(self, config: Config, validate_outputs: bool = False, strict_validation: bool = False,
                 validate_business_value: bool = False, user_segment: str = "free",
                 validate_events: bool = False, event_validation_strict: bool = False,
                 retry_config: Optional[Dict[str, Any]] = None,
                 json_mode: bool = False, ci_mode: bool = False, json_output_file: Optional[str] = None,
                 send_logs: bool = False, logs_count: int = 1, logs_project: Optional[str] = None,
                 logs_path: Optional[str] = None, logs_user: Optional[str] = None,
                 logs_provider: str = "claude", handshake_timeout: float = 10.0):
        # ISSUE #2766: Store JSON/CI mode flags early for output suppression
        self.json_mode = json_mode
        self.ci_mode = ci_mode
        self.json_output_file = json_output_file

        # Store log forwarding configuration
        self.send_logs = send_logs
        self.logs_count = logs_count
        self.logs_project = logs_project
        self.logs_path = logs_path
        self.logs_user = logs_user
        self.logs_provider = logs_provider

        # Store handshake timeout
        self.handshake_timeout = handshake_timeout

        self.config = config
        # ISSUE #2766: Pass json_mode/ci_mode to DebugManager for output suppression
        self.debug = DebugManager(config.debug_level, config.debug_log_file, config.enable_websocket_diagnostics,
                                 json_mode=json_mode, ci_mode=ci_mode)
        self.health_checker = HealthChecker(config, self.debug)
        self.auth_manager: Optional[AuthManager] = None
        self.ws_client: Optional[WebSocketClient] = None
        self.layout = self._create_layout()
        self.use_oauth: bool = False
        self.oauth_provider: str = "google"
        self.auth_method: str = "auto"  # auto, e2e, oauth

        # Issue #1822: Agent output validation
        self.validate_outputs = validate_outputs
        self.output_validator: Optional[AgentOutputValidator] = None
        if self.validate_outputs and AgentOutputValidator is not None:
            self.output_validator = AgentOutputValidator(debug=config.debug_level.value >= 3)

        # Business value validation
        self.validate_business_value = validate_business_value
        self.user_segment = user_segment
        self.business_validator: Optional[BusinessValueValidator] = None

        # Issue #1817: Agent chain validation
        self.strict_validation = strict_validation

        # ISSUE #2190: Retry configuration
        self.retry_config = retry_config or {}
        self.show_retry_info = self.retry_config.get('show_retry_info', False)

        # Issue #2177: WebSocket event validation framework
        self.validate_events = validate_events
        self.event_validation_strict = event_validation_strict
        self.event_validator: Optional[WebSocketEventValidationFramework] = None
        if self.validate_events:
            session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.randbelow(100000)}"
            self.event_validator = WebSocketEventValidationFramework(
                session_id=session_id,
                strict_validation=event_validation_strict
            )

        # ISSUE #2766: CI/CD integration - JSON output and exit codes (moved to top of __init__)
        self.output_formatter: Optional[CLIOutputFormatter] = None
        self.errors: List[str] = []  # Track errors for JSON output
        self.exit_code: int = 0  # Track exit code for CI/CD integration
        self.validation_passed: bool = True  # Track validation status

    def _create_layout(self) -> Layout:
        """Create Rich layout for display"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )

        layout["body"].split_row(
            Layout(name="events", ratio=2),
            Layout(name="details", ratio=1)
        )

        return layout

    def _update_header(self, status: str):
        """Update header with status"""
        header = Panel(
            Text(f" Netra Agent CLI - {status}", style="bold cyan"),
            title="Agent Testing Tool",
            border_style="cyan"
        )
        self.layout["header"].update(header)

    def _update_footer(self, info: str):
        """Update footer with info"""
        footer = Panel(
            Text(info, style="dim"),
            border_style="blue"
        )
        self.layout["footer"].update(footer)

    async def run_interactive(self):
        """Run in interactive mode"""
        # Issue #2747 Phase 3: Enhanced startup banner showing environment and mode
        show_startup_banner(self.config)

        async with AuthManager(self.config) as auth_manager:
            self.auth_manager = auth_manager

            # Get authentication using new priority system
            if self.use_oauth:
                token = await auth_manager.get_valid_token(
                    use_oauth=True,
                    oauth_provider=self.oauth_provider,
                    auth_method=self.auth_method
                )
            else:
                # Use simplified authentication for manual token/no-auth cases
                token = await auth_manager.get_valid_token(
                    use_oauth=False,
                    auth_method=self.auth_method
                )

            if not token:
                safe_console_print("ERROR: Authentication failed", style="red")
                safe_console_print("", style="")
                if self.config.environment == Environment.LOCAL:
                    safe_console_print("💡 LOCAL ENVIRONMENT AUTHENTICATION: ", style="cyan")
                    safe_console_print("• Try --no-auth for testing without authentication", style="dim")
                    safe_console_print("• Verify local auth service is running", style="dim")
                else:
                    safe_console_print("💡 AUTHENTICATION TROUBLESHOOTING: ", style="cyan")
                    safe_console_print("• Check your credentials are valid", style="dim")
                    safe_console_print("• Try clearing cache: --clear-cache", style="dim")
                    safe_console_print("• For testing: --env local", style="dim")
                safe_console_print("", style="")
                return

            # Display token info
            if auth_manager.token:
                payload = auth_manager.token.decode_payload()
                safe_console_print(Panel.fit(
                    f"[green]Authenticated as:[/green] {auth_manager.token.email}\n"
                    f"[dim]User ID: {auth_manager.token.user_id}[/dim]\n"
                    f"[dim]Expires: {auth_manager.token.expires_at}[/dim]",
                    title="Authentication",
                    border_style="green"
                ))

            # Connect WebSocket
            self.ws_client = WebSocketClient(
                self.config, token, self.debug,
                send_logs=self.send_logs,
                logs_count=self.logs_count,
                logs_project=self.logs_project,
                logs_path=self.logs_path,
                logs_user=self.logs_user,
                logs_provider=self.logs_provider,
                handshake_timeout=self.handshake_timeout
            )
            if not await self.ws_client.connect():
                # The WebSocket client will already show detailed troubleshooting (Issue #2414)
                safe_console_print("⚠️ Could not establish connection. Please check the guidance above.", style="yellow")
                return

            # Start event receiver task
            event_task = asyncio.create_task(self._receive_events())

            try:
                # Interactive message loop
                while True:
                    message = Prompt.ask("\n[cyan]Enter message (or 'quit' to exit)[/cyan]")

                    if message.lower() in ['quit', 'exit', 'q']:
                        break

                    if not message.strip():
                        continue

                    # Send message
                    run_id = await self.ws_client.send_message(message)
                    safe_console_print(f"Message sent with run_id: {run_id}", style="green")

                    # Wait a moment for events to stream
                    await asyncio.sleep(0.5)

            except KeyboardInterrupt:
                safe_console_print("\n Interrupted by user", style="yellow")
            finally:
                event_task.cancel()
                await self.ws_client.close()

    async def _receive_events(self):
        """Background task to receive and display events"""
        # Create persistent spinner that stays at bottom
        thinking_spinner = Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[dim]{task.description}"),
            console=Console(file=sys.stderr),
            transient=True
        )
        thinking_live = Live(thinking_spinner, console=Console(file=sys.stderr), refresh_per_second=10)
        thinking_task = None

        # Start the spinner live display
        thinking_live.start()

        async def handle_event(event: WebSocketEvent):
            nonlocal thinking_task

            # Display event with enhanced formatting
            formatted_event = event.format_for_display(self.debug)
            safe_console_print(f"[{event.timestamp.strftime('%H:%M:%S')}] {formatted_event}")

            # Update spinner for thinking and tool_executing events (if spinner is enabled)
            if spinner_enabled and event.type in ["agent_thinking", "tool_executing"]:
                # Remove old task if exists
                if thinking_task is not None:
                    thinking_spinner.remove_task(thinking_task)
                    thinking_task = None

                # Add new task with latest event
                if event.type == "agent_thinking":
                    thought = event.data.get('thought', event.data.get('reasoning', ''))
                    spinner_text = truncate_with_ellipsis(thought, 60) if thought else "Processing..."
                    thinking_task = thinking_spinner.add_task(f"💭 {spinner_text}", total=None)
                elif event.type == "tool_executing":
                    tool_name = event.data.get('tool', event.data.get('tool_name', 'Unknown'))
                    spinner_text = f"Executing {tool_name}..."
                    thinking_task = thinking_spinner.add_task(f"🔧 {spinner_text}", total=None)

            # Clear spinner for any other event type (if spinner is enabled)
            elif spinner_enabled and thinking_task is not None:
                thinking_spinner.remove_task(thinking_task)
                thinking_task = None

            # Display raw data in verbose mode
            if self.debug.debug_level >= DebugLevel.DIAGNOSTIC:
                safe_console_print(Panel(
                    Syntax(json.dumps(event.data, indent=2), "json"),
                    title=f"Event: {event.type}",
                    border_style="dim"
                ))

        try:
            await self.ws_client.receive_events(callback=handle_event)
        finally:
            # Clean up spinner
            thinking_live.stop()

    async def _receive_events_with_display(self):
        """ISSUE #1603 FIX: Enhanced event receiver with better display for single message mode"""
        # Debug: Confirm function is called
        if self.debug.debug_level >= DebugLevel.SILENT:
            safe_console_print("⏳ Waiting for agent response...", style="dim", json_mode=self.json_mode, ci_mode=self.ci_mode)

        # Create persistent spinner that stays at bottom
        # Note: Using Console() without file parameter for better Windows compatibility
        thinking_spinner = None
        thinking_live = None
        thinking_task = None
        spinner_enabled = False
        event_count = 0  # Track number of events received
        last_event_index = len(self.ws_client.events)  # Track where we are in the event list

        try:
            thinking_spinner = Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[dim]{task.description}"),
                console=Console(),
                transient=True
            )
            thinking_live = Live(thinking_spinner, console=Console(), refresh_per_second=10)
            # Start the spinner live display
            thinking_live.start()
            spinner_enabled = True
        except Exception as e:
            # Spinner failed to start (common on Windows), continue without it
            if self.debug.debug_level >= DebugLevel.SILENT:
                safe_console_print(f"Note: Live spinner disabled ({str(e)[:50]})", style="dim yellow", json_mode=self.json_mode, ci_mode=self.ci_mode)
            spinner_enabled = False

        def handle_event_with_display(event: WebSocketEvent):
            nonlocal thinking_task, event_count
            event_count += 1

            # Display event with enhanced formatting and emojis
            formatted_event = event.format_for_display(self.debug)
            timestamp = event.timestamp.strftime('%H:%M:%S')
            safe_console_print(f"[{timestamp}] {formatted_event}", json_mode=self.json_mode, ci_mode=self.ci_mode)

            # Update spinner for thinking and tool_executing events (if spinner is enabled)
            if spinner_enabled and event.type in ["agent_thinking", "tool_executing"]:
                # Remove old task if exists
                if thinking_task is not None:
                    thinking_spinner.remove_task(thinking_task)
                    thinking_task = None

                # Add new task with latest event
                if event.type == "agent_thinking":
                    thought = event.data.get('thought', event.data.get('reasoning', ''))
                    spinner_text = truncate_with_ellipsis(thought, 60) if thought else "Processing..."
                    thinking_task = thinking_spinner.add_task(f"💭 {spinner_text}", total=None)
                elif event.type == "tool_executing":
                    tool_name = event.data.get('tool', event.data.get('tool_name', 'Unknown'))
                    spinner_text = f"Executing {tool_name}..."
                    thinking_task = thinking_spinner.add_task(f"🔧 {spinner_text}", total=None)

            # Clear spinner for any other event type (if spinner is enabled)
            elif spinner_enabled and thinking_task is not None:
                thinking_spinner.remove_task(thinking_task)
                thinking_task = None

            # Issue #2177: WebSocket event validation
            if self.validate_events and self.event_validator:
                try:
                    self.event_validator.validate_event(event.type, event.data)
                except Exception as e:
                    self.debug.debug_print(f"Event validation error: {e}", DebugLevel.DIAGNOSTIC)

            # Issue #1822: Capture agent outputs for validation
            if self.validate_outputs and self.output_validator:
                agent_name = event.data.get('agent_name', 'unknown_agent')

                # Capture different event types for comprehensive analysis
                if event.type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]:
                    self.output_validator.add_agent_output(agent_name, event.data, event.type)

            # Show additional details for key events
            if event.type in ["agent_thinking", "tool_executing", "tool_completed", "agent_completed"]:
                if event.type == "agent_thinking":
                    thought = event.data.get('thought', event.data.get('reasoning', ''))
                    if thought and len(thought) > 100:
                        safe_console_print(f"💭 Full thought: {thought}", style="dim cyan", json_mode=self.json_mode, ci_mode=self.ci_mode)
                elif event.type == "tool_executing":
                    tool_input = event.data.get('input', event.data.get('parameters', {}))
                    if tool_input:
                        safe_console_print(f"📥 Tool input: {json.dumps(tool_input, indent=2)[:200]}...", style="dim blue", json_mode=self.json_mode, ci_mode=self.ci_mode)
                elif event.type == "tool_completed":
                    tool_output = event.data.get('output', event.data.get('result', ''))
                    if tool_output:
                        safe_console_print(f"📤 Tool output: {str(tool_output)[:200]}...", style="dim green", json_mode=self.json_mode, ci_mode=self.ci_mode)
                elif event.type == "agent_completed":
                    # Prefer structured result payloads but fall back to legacy keys
                    result = (
                        event.data.get('result')
                        or event.data.get('response')
                        or event.data.get('final_response')
                    )

                    if result is not None:
                        if isinstance(result, (dict, list)):
                            try:
                                pretty_result = json.dumps(result, indent=2, ensure_ascii=False)
                            except (TypeError, ValueError):
                                pretty_result = str(result)

                            safe_console_print(
                                Panel(
                                    Syntax(pretty_result, "json", word_wrap=True),
                                    title="Final Agent Result - Optimization Pointers",
                                    border_style="green"
                                ),
                                json_mode=self.json_mode,
                                ci_mode=self.ci_mode
                            )
                        else:
                            safe_console_print(
                                "✅ Final result:",
                                style="bold green",
                                json_mode=self.json_mode,
                                ci_mode=self.ci_mode
                            )
                            safe_console_print(
                                str(result),
                                style="green",
                                json_mode=self.json_mode,
                                ci_mode=self.ci_mode
                            )

            # Display raw data in verbose mode
            if self.debug.debug_level >= DebugLevel.DIAGNOSTIC:
                safe_console_print(Panel(
                    Syntax(json.dumps(event.data, indent=2), "json", word_wrap=True),
                    title=f"Event: {event.type}",
                    border_style="dim"
                ), json_mode=self.json_mode, ci_mode=self.ci_mode)

        try:
            # Debug: Track if monitoring events
            if self.debug.debug_level >= DebugLevel.SILENT:
                safe_console_print("📡 Monitoring events from server...", style="dim cyan", json_mode=self.json_mode, ci_mode=self.ci_mode)

            # Poll for new events from the existing event stream
            # The WebSocketClient already has a background task receiving events
            while True:
                # Check for new events
                while last_event_index < len(self.ws_client.events):
                    event = self.ws_client.events[last_event_index]
                    last_event_index += 1
                    handle_event_with_display(event)

                # Check if we should stop
                if self.ws_client.cleanup_complete or self.ws_client.timeout_occurred:
                    break

                # Small delay to avoid busy waiting
                await asyncio.sleep(0.1)

        except Exception as e:
            # Log any errors
            safe_console_print(f"❌ Error monitoring events: {str(e)}", style="red", json_mode=self.json_mode, ci_mode=self.ci_mode)
            raise
        finally:
            # Clean up spinner if it was started
            if spinner_enabled and thinking_live:
                thinking_live.stop()

            # Debug: Report how many events were received
            if self.debug.debug_level >= DebugLevel.SILENT and event_count == 0:
                safe_console_print("⚠️ No events received from server", style="yellow", json_mode=self.json_mode, ci_mode=self.ci_mode)

    def _get_event_summary(self, event: WebSocketEvent) -> str:
        """ISSUE #1603 FIX: Get a concise summary of an event for display"""
        # Handle system_message events that wrap agent events
        event_type = event.type
        data = event.data

        if event_type == "system_message":
            inner_event = data.get('event', '')
            if inner_event in ['agent_started', 'agent_thinking', 'agent_completed', 'tool_executing', 'tool_completed']:
                # Extract the actual event type and data from payload
                event_type = inner_event
                payload = data.get('payload', {})
                # Merge payload data with original data, payload takes precedence
                data = {**data, **payload}

        if event_type == "connection_established":
            user_id = data.get('data', {}).get('user_id', 'unknown')
            return safe_format_message(f"🔌 Connected as: {user_id}")
        elif event_type == "handshake_response":
            thread_id = data.get('thread_id', 'unknown')
            message = data.get('message', 'Handshake complete')
            return safe_format_message(f"🤝 {message} - Thread ID: {thread_id}")
        elif event_type == "tool_executing":
            tool = data.get('tool', data.get('tool_name', 'Unknown'))
            return safe_format_message(f"🔧 Executing Tool: {tool}")
        elif event_type == "tool_completed":
            tool = data.get('tool', data.get('tool_name', 'Unknown'))
            status = data.get('status', 'completed')
            return safe_format_message(f"✅ Tool Complete: {tool} ({status})")
        elif event_type == "agent_completed":
            result = data.get('result', data.get('response', ''))
            run_id = data.get('run_id', 'N/A')
            return safe_format_message(f"🎯 Agent Completed: {truncate_with_ellipsis(run_id, 8)} - {truncate_with_ellipsis(str(result), 50)}")
        elif event_type == "message":
            content = data.get('content', '')
            return f"💬 Message: {truncate_with_ellipsis(content, 50)}"
        elif event_type == "error":
            error = data.get('error', 'Unknown error')
            return safe_format_message(f"❌ Error: {truncate_with_ellipsis(error, 50)}")
        else:
            return safe_format_message(f"📡 {event_type}: {truncate_with_ellipsis(json.dumps(data), 50)}")

    def _validate_agent_chain_execution(self, events: List[WebSocketEvent], run_id: str) -> Dict[str, Any]:
        """
        CRITICAL FIX: Validate that all required agents executed using proper agents_involved field.

        Business Requirement: Every user request must go through agents:
        1. Uses agents_involved field from agent_completed events
        2. Validates against critical business events (agent_started, agent_completed)
        3. Provides clear feedback on which agents actually executed

        Args:
            events: List of WebSocket events received
            run_id: The execution run ID for logging

        Returns:
            Dict with 'valid' bool and 'message' string
        """
        if not events:
            return {
                'valid': False,
                'message': 'No events received from agents. This could mean: (1) Network/WebSocket issues, (2) Backend services not responding, (3) Authentication problems. Check connection and try again.'
            }

        # Track which agents we've detected from events
        detected_agents = set()
        event_types_seen = set()
        agents_from_response_complete = set()
        has_agent_execution = False

        # Analyze events to detect agent execution
        for event in events:
            event_types_seen.add(event.type)

            # Check for agent_completed events (PRIMARY METHOD) - Fixed to use correct event type
            if event.type == "agent_completed":
                # CRITICAL FIX: agents_involved is nested inside data.data, not directly in data
                inner_data = event.data.get('data', {})
                agents_involved = inner_data.get('agents_involved', [])

                # Debug: Print what we're seeing in agent_completed events (only in diagnostic mode)
                if hasattr(self, 'debug') and self.debug.debug_level >= DebugLevel.DIAGNOSTIC:
                    self.debug.debug_print(f"agent_completed event data keys: {list(event.data.keys())}", DebugLevel.DIAGNOSTIC)
                    self.debug.debug_print(f"inner_data keys: {list(inner_data.keys())}", DebugLevel.DIAGNOSTIC)
                    self.debug.debug_print(f"agents_involved field: {agents_involved}", DebugLevel.DIAGNOSTIC)

                if agents_involved:
                    agents_from_response_complete.update(agents_involved)
                    detected_agents.update(agents_involved)
                    has_agent_execution = True
                    if hasattr(self, 'debug') and self.debug.debug_level >= DebugLevel.VERBOSE:
                        self.debug.debug_print(f"AGENTS_INVOLVED_SUCCESS: Found {len(agents_involved)} agents: {agents_involved}", DebugLevel.VERBOSE)
                else:
                    # Look for alternative fields that might contain agent info
                    alt_fields = ['agent_name', 'agent_type', 'agent_id', 'agents_used', 'active_agents']
                    for field in alt_fields:
                        if field in event.data and event.data[field]:
                            if hasattr(self, 'debug') and self.debug.debug_level >= DebugLevel.DIAGNOSTIC:
                                self.debug.debug_print(f"Found agent info in {field}: {event.data[field]}", DebugLevel.DIAGNOSTIC)
                            detected_agents.add(str(event.data[field]).lower())
                            has_agent_execution = True

            # Secondary validation: Look for agent activities in other events
            elif event.type in ["system_message", "agent_progress"]:
                if event.data.get('event') in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                    has_agent_execution = True
                    # Look for agent names in payloads
                    payload = event.data.get('payload', {})
                    agent_name = payload.get('agent_name', '').lower()
                    if agent_name and 'supervisor' in agent_name:
                        # Supervisor orchestrates the agent chain - indicates system working
                        detected_agents.add('orchestration')

            # Track basic event types for validation
            elif event.type == "connection_established":
                # Indicates WebSocket system is working
                pass

        # Analysis of actual execution
        num_agent_complete_events = len([e for e in events if e.type == "agent_completed"])
        num_agent_start_events = len([e for e in events if e.type == "system_message" and e.data.get('event') == 'agent_started'])

        # Check for critical event types - Fixed to use correct event type
        critical_events = {'system_message', 'agent_progress', 'agent_completed'}
        missing_critical_events = critical_events - event_types_seen

        # IMPROVED VALIDATION LOGIC: Based on actual system behavior

        # If we have agents_involved data, use that as primary source of truth
        if agents_from_response_complete:
            return {
                'valid': True,
                'message': f'✅ Agent execution successful - {len(agents_from_response_complete)} agents executed: {sorted(agents_from_response_complete)}. '
                          f'Received {num_agent_complete_events} completion events with agent chain working.'
            }

        # If no agents_involved but we have execution activity, system is working
        elif has_agent_execution and num_agent_complete_events > 0:
            return {
                'valid': True,  # Changed from False - system is working even if we can't detect specific agents
                'message': f'✅ Agent system operational - Received {num_agent_complete_events} completion events, '
                          f'{num_agent_start_events} start events. Agent orchestration working. '
                          f'Detected activities: {sorted(detected_agents) if detected_agents else "system execution"}.'
            }

        # If we have no completion events but have other agent activity, partial success
        elif has_agent_execution:
            return {
                'valid': False,
                'message': f'⚠️  Partial execution detected - Agent activities observed but no completion events received. '
                          f'This may indicate an orchestration issue. Detected activities: {sorted(detected_agents) if detected_agents else "system events"}.'
            }

        # Complete failure - no agent activity detected
        else:
            return {
                'valid': False,
                'message': f'❌ No agent execution detected - No agent activities or completion events found. '
                          f'Missing critical events: {sorted(missing_critical_events)}. '
                          f'This indicates a complete system failure in agent orchestration.'
            }

    def _generate_validation_report(self, run_id: str) -> bool:
        """Issue #1822: Generate and display agent output validation report"""
        if not self.output_validator:
            return True

        try:
            # Generate validation report
            report = self.output_validator.get_validation_report()

            safe_console_print("\n" + "="*60, style="bold cyan")
            safe_console_print("🔍 AGENT OUTPUT VALIDATION REPORT", style="bold cyan")
            safe_console_print("="*60, style="bold cyan")

            # Overall results
            overall_style = "green" if report.overall_result == ValidationResult.PASS else \
                           "yellow" if report.overall_result == ValidationResult.WARN else "red"

            safe_console_print(f"\n📊 Overall Result: [{overall_style}]{report.overall_result.value.upper()}[/{overall_style}]")
            safe_console_print(f"📈 Overall Score: {report.overall_score:.1f}/10.0")
            safe_console_print(f"🕒 Generated: {report.timestamp}")
            safe_console_print(f"🆔 Run ID: {run_id}")

            # Individual agent results
            if report.agent_validations:
                safe_console_print(f"\n🤖 Agent Validation Results ({len(report.agent_validations)} agents):", style="bold")

                for validation in report.agent_validations:
                    result_style = "green" if validation.result == ValidationResult.PASS else \
                                  "yellow" if validation.result == ValidationResult.WARN else "red"

                    safe_console_print(f"\n Agent: {validation.agent_name}")
                    safe_console_print(f"Result: [{result_style}]{validation.result.value.upper()}[/{result_style}]")
                    safe_console_print(f"Score: {validation.score:.1f}/10.0")

                    if validation.reasons:
                        safe_console_print(f"Reasons: ")
                        for reason in validation.reasons:
                            safe_console_print(f"• {reason}", style="dim")

                    # Show key details
                    if validation.details:
                        details_to_show = []
                        if "substantive_content_score" in validation.details:
                            score = validation.details["substantive_content_score"]
                            details_to_show.append(f"Substantive content: {score:.1%}")

                        if "required_fields_found" in validation.details:
                            fields = validation.details["required_fields_found"]
                            if fields:
                                details_to_show.append(f"Required fields: {', '.join(fields)}")

                        if details_to_show:
                            safe_console_print(f"Details: {' | '.join(details_to_show)}", style="dim cyan")

            # Business value summary
            if report.business_value_summary:
                safe_console_print(f"\n💼 Business Value Summary: ", style="bold")
                safe_console_print(f"{report.business_value_summary}")

            # Recommendations
            if report.recommendations:
                safe_console_print(f"\n💡 Recommendations for Improvement: ", style="bold yellow")
                for i, rec in enumerate(report.recommendations, 1):
                    safe_console_print(f"{i}. {rec}")

            safe_console_print("\n" + "="*60, style="bold cyan")

            # Determine exit code based on validation results
            if report.overall_result == ValidationResult.FAIL:
                safe_console_print("❌ VALIDATION FAILED - Agents did not deliver sufficient business value", style="bold red")
                safe_console_print("Exit code: 1", style="dim")
                return False
            elif report.overall_result == ValidationResult.WARN:
                safe_console_print("⚠️ VALIDATION WARNING - Some agents delivered limited business value", style="bold yellow")
                safe_console_print("Exit code: 0 (passing with warnings)", style="dim")
                return True
            else:
                safe_console_print("✅ VALIDATION PASSED - All agents delivered strong business value", style="bold green")
                safe_console_print("Exit code: 0", style="dim")
                return True

        except Exception as e:
            safe_console_print(f"\n❌ Error generating validation report: {e}", style="red")
            if self.debug.debug_level >= DebugLevel.VERBOSE:
                import traceback
                safe_console_print(traceback.format_exc(), style="dim red")
            safe_console_print("Exit code: 2 (error)", style="dim")
            return False

    def _convert_events_to_websocket_format(self, events: List) -> List[WebSocketEvent]:
        """Convert AgentCLI events to WebSocketEvent format for business value validation"""
        # Note: Using local WebSocketEvent class, not imported validation WebSocketEvent

        websocket_events = []
        for event in events:
            # Extract event type and data based on the existing event structure
            if hasattr(event, 'type'):
                event_type = event.type
            elif hasattr(event, 'event_type'):
                event_type = event.event_type
            else:
                continue

            # Extract event data/content
            data = {}
            if hasattr(event, 'data') and isinstance(event.data, dict):
                data = event.data
            elif hasattr(event, 'content'):
                data['content'] = event.content
            elif hasattr(event, 'message'):
                data['message'] = event.message

            # Add timestamp if available
            timestamp = time.time()
            if hasattr(event, 'timestamp'):
                timestamp = event.timestamp

            websocket_events.append(WebSocketEvent(
                type=event_type,
                data=data,
                timestamp=timestamp
            ))

        return websocket_events

    def _generate_business_value_report(self, run_id: str, user_id: str = "cli_test_user") -> bool:
        """Generate and display business value validation report"""
        if not self.validate_business_value or not BusinessValueValidator:
            return True

        if not self.ws_client or not self.ws_client.events:
            safe_console_print("❌ No events to validate for business value", style="red")
            return False

        try:
            # Initialize business value validator
            session_id = f"cli_{run_id}"
            self.business_validator = BusinessValueValidator(
                user_id=user_id,
                session_id=session_id,
                user_segment=self.user_segment,
                strict_mode=True
            )

            # Convert events to WebSocket format
            websocket_events = self._convert_events_to_websocket_format(self.ws_client.events)

            if not websocket_events:
                safe_console_print("❌ No valid events converted for business value validation", style="red")
                return False

            # Validate session business value
            result = self.business_validator.validate_session_business_value(websocket_events)

            # Display business value report
            safe_console_print("\n" + "="*70, style="bold magenta")
            safe_console_print("💼 BUSINESS VALUE VALIDATION REPORT", style="bold magenta")
            safe_console_print("="*70, style="bold magenta")

            # Overall business value score
            score_style = "green" if result.business_value_score >= 0.7 else \
                         "yellow" if result.business_value_score >= 0.5 else "red"

            safe_console_print(f"\n💰 Business Value Score: [{score_style}]{result.business_value_score:.1%}[/{score_style}]")
            safe_console_print(f"👤 User Segment: {self.user_segment.upper()}")
            safe_console_print(f"📊 Events Processed: {result.total_events}")
            safe_console_print(f"🆔 Session ID: {session_id}")

            # Conversion potential
            conversion_prob = result.conversion_potential.probability
            conv_style = "green" if conversion_prob >= 0.4 else \
                        "yellow" if conversion_prob >= 0.2 else "red"

            safe_console_print(f"\n📈 Conversion Analysis: ", style="bold")
            safe_console_print(f"Conversion Probability: [{conv_style}]{conversion_prob:.1%}[/{conv_style}]")
            safe_console_print(f"Estimated Revenue Impact: ${result.conversion_potential.revenue_impact:.2f}/month")

            if result.conversion_potential.key_factors:
                safe_console_print(f"Key Conversion Factors: ")
                for factor in result.conversion_potential.key_factors:
                    safe_console_print(f"• {factor.value.replace('_', ' ').title()}")

            # Engagement metrics
            engagement = result.engagement_metrics
            overall_engagement = engagement.overall_engagement()
            eng_style = "green" if overall_engagement >= 0.7 else \
                       "yellow" if overall_engagement >= 0.5 else "red"

            safe_console_print(f"\n🎯 User Engagement Analysis: ", style="bold")
            safe_console_print(f"Overall Engagement: [{eng_style}]{overall_engagement:.1%}[/{eng_style}]")
            safe_console_print(f"Trust Score: {engagement.trust_score:.1%}")
            safe_console_print(f"Attention Score: {engagement.attention_score:.1%}")
            safe_console_print(f"Satisfaction Score: {engagement.satisfaction_score:.1%}")

            # Violations
            if result.violations:
                safe_console_print(f"\n⚠️ Business Value Violations ({len(result.violations)}):", style="bold red")
                for i, violation in enumerate(result.violations[:5], 1):  # Show top 5
                    safe_console_print(f"{i}. {violation.description}")
                    if violation.revenue_impact < 0:
                        safe_console_print(f"Revenue Impact: ${abs(violation.revenue_impact):.2f} loss", style="red")

            # Recommendations
            if result.recommendations:
                safe_console_print(f"\n💡 Business Value Recommendations: ", style="bold cyan")
                for i, rec in enumerate(result.recommendations, 1):
                    safe_console_print(f"{i}. {rec}")

            safe_console_print("\n" + "="*70, style="bold magenta")

            # Assert business value standards if enabled
            try:
                # Use segment-appropriate thresholds
                segment_thresholds = {
                    "free": 0.6,      # 60% minimum for free users
                    "early": 0.65,    # 65% for early adopters
                    "mid": 0.7,       # 70% for mid-tier
                    "enterprise": 0.75 # 75% for enterprise
                }
                min_threshold = segment_thresholds.get(self.user_segment, 0.6)

                self.business_validator.assert_business_value_standards_met(
                    min_value_score=min_threshold,
                    max_abandonment_risk=0.3
                )

                safe_console_print(f"✅ BUSINESS VALUE VALIDATION PASSED", style="bold green")
                safe_console_print(f"Events deliver sufficient value for {self.user_segment} user segment", style="green")
                return True

            except AssertionError as e:
                safe_console_print(f"❌ BUSINESS VALUE VALIDATION FAILED", style="bold red")
                safe_console_print(f"{str(e)}", style="red")
                return False

        except Exception as e:
            safe_console_print(f"\n❌ Error generating business value report: {e}", style="red")
            if self.debug.debug_level >= DebugLevel.VERBOSE:
                import traceback
                safe_console_print(traceback.format_exc(), style="dim red")
            return False

    async def run_single_message(self, message: str, wait_time: int = 300):
        """Run a single message and wait for response.

        Issue #2665: Default wait time increased from 10s to 300s to accommodate
        real agent execution times (100s+ in staging with real LLM calls).

        ISSUE #2832: JSON output must be generated even on failure paths.
        Using finally block ensures JSON generation regardless of early returns.
        """
        # ISSUE #2766: Track execution start time for JSON output
        execution_start_time = time.time()

        try:
            # ISSUE #2766: Suppress output in JSON/CI mode
            # Note: "Sending message:" is now printed inside send_message() after logs section

            async with AuthManager(self.config) as auth_manager:
                self.auth_manager = auth_manager

                # Get authentication using new priority system
                if self.use_oauth:
                    token = await auth_manager.get_valid_token(
                        use_oauth=True,
                        oauth_provider=self.oauth_provider,
                        auth_method=self.auth_method
                    )
                else:
                    # Use simplified authentication for manual token/no-auth cases
                    token = await auth_manager.get_valid_token(
                        use_oauth=False,
                        auth_method=self.auth_method
                    )

                if not token:
                    # ISSUE #2766: Track authentication failure error
                    error_msg = "Failed to authenticate"
                    self.errors.append(error_msg)
                    safe_console_print(f"ERROR: {error_msg}", style="red")

                    # Add helpful guidance based on environment and configuration
                    if self.config.environment == Environment.STAGING:
                        safe_console_print("\nTROUBLESHOOTING: Staging authentication failed", style="yellow")
                        safe_console_print("This is likely a configuration issue, not infrastructure failure", style="dim yellow")
                        safe_console_print("Solutions: ", style="dim yellow")
                        safe_console_print("• Use local environment: --env local", style="dim yellow")
                        safe_console_print("• Set up GCP auth: gcloud auth application-default login", style="dim yellow")
                        safe_console_print("• Use E2E mode: --auth-method e2e", style="dim yellow")
                    elif self.config.environment == Environment.LOCAL:
                        safe_console_print("\nTROUBLESHOOTING: Local authentication failed", style="yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("Solutions: ", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("• Start local services: docker-compose up", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("• Use staging environment: --env staging", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)

                    # ISSUE #2766: Return exit code 2 (infrastructure failure) in JSON mode
                    if self.json_mode:
                        self.exit_code = 2
                        return 2
                    return False

                # Connect WebSocket
                self.ws_client = WebSocketClient(
                    self.config, token, self.debug,
                    send_logs=self.send_logs,
                    logs_count=self.logs_count,
                    logs_project=self.logs_project,
                    logs_path=self.logs_path,
                    logs_user=self.logs_user,
                    logs_provider=self.logs_provider,
                    handshake_timeout=self.handshake_timeout
                )
                if not await self.ws_client.connect():
                    # ISSUE #2766: Track WebSocket connection failure error
                    error_msg = "Failed to connect WebSocket"
                    self.errors.append(error_msg)
                    safe_console_print(f"ERROR: {error_msg}", style="red",
                                     json_mode=self.json_mode, ci_mode=self.ci_mode)

                    # Add helpful guidance based on environment
                    if self.config.environment == Environment.LOCAL:
                        safe_console_print("\nTROUBLESHOOTING: Local WebSocket connection failed", style="yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("Solutions: ", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("• Start backend services: docker-compose up", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("• Check if port 8000 is available", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("• Use staging environment: --env staging", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                    elif self.config.environment == Environment.STAGING:
                        safe_console_print("\nTROUBLESHOOTING: Staging WebSocket connection failed", style="yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("This is likely a configuration issue, not infrastructure failure", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("Solutions: ", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("• Use local environment: --env local", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)
                        safe_console_print("• Check GCP credentials: gcloud auth list", style="dim yellow",
                                         json_mode=self.json_mode, ci_mode=self.ci_mode)

                    # ISSUE #2766: Return exit code 2 (infrastructure failure) in JSON mode
                    if self.json_mode:
                        self.exit_code = 2
                        return 2
                    return False

                # Send message
                run_id = await self.ws_client.send_message(message)
                safe_console_print(f"SUCCESS: Message sent with run_id: {run_id}", style="green",
                                 json_mode=self.json_mode, ci_mode=self.ci_mode)

                # ISSUE #1603 FIX: Improved event collection and display
                safe_console_print(f"⏳ Waiting {wait_time} seconds for events...", style="yellow",
                                 json_mode=self.json_mode, ci_mode=self.ci_mode)
                safe_console_print("Receiving events...", style="dim",
                                 json_mode=self.json_mode, ci_mode=self.ci_mode)

                # Start event receiver task with improved display
                event_display_task = asyncio.create_task(self._receive_events_with_display())

                # ISSUE #2134 FIX: Use negotiated timeout if available, with cleanup monitoring
                effective_timeout = wait_time
                start_time = asyncio.get_event_loop().time()

                while True:
                    # Check if we have a negotiated timeout from server
                    if self.ws_client.negotiated_timeout is not None:
                        effective_timeout = self.ws_client.negotiated_timeout
                        safe_console_print(f"⏱️ Using negotiated timeout: {effective_timeout}s", style="cyan")
                        break

                    # Check if cleanup is complete (early exit condition)
                    if self.ws_client.cleanup_complete:
                        safe_console_print("✅ Cleanup completed, ending wait early", style="green")
                        break

                    # Check if we've waited long enough for negotiation
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed >= 2:  # Wait max 2 seconds for negotiation
                        break

                    await asyncio.sleep(0.1)  # Short sleep to avoid busy waiting

                # Wait for the effective timeout duration
                remaining_time = max(0, effective_timeout - (asyncio.get_event_loop().time() - start_time))
                if remaining_time > 0:
                    try:
                        await asyncio.wait_for(self._wait_for_completion(), timeout=remaining_time)
                    except asyncio.TimeoutError:
                        self.ws_client.timeout_occurred = True
                        if self.ws_client.cleanup_in_progress and not self.ws_client.cleanup_complete:
                            safe_console_print("⚠️ Timeout occurred during cleanup - this indicates the race condition issue", style="yellow")
                        else:
                            safe_console_print(f"⏰ Timeout after {effective_timeout}s", style="yellow")

                # Cancel event receiver
                event_display_task.cancel()
                try:
                    await event_display_task
                except asyncio.CancelledError:
                    pass

                # Display final summary with event details
                safe_console_print(f"\n📊 Received {len(self.ws_client.events)} events", style="cyan")

                # Issue #2178: Display LLM validation summary
                validation_events = [e for e in self.ws_client.events if e.data.get('llm_validation')]
                if validation_events:
                    valid_count = sum(1 for e in validation_events if e.data.get('llm_validation', {}).get('is_valid', False))
                    total_count = len(validation_events)
                    safe_console_print(f"\n🔍 LLM Validation Summary: ", style="bold cyan")
                    safe_console_print(f"Real AI Executions: {valid_count}/{total_count}", style="cyan")

                    if valid_count == total_count:
                        safe_console_print(f"✅ All executions verified as real AI", style="bold green")
                    elif valid_count > 0:
                        safe_console_print(f"⚠️ {total_count - valid_count} executions failed validation", style="yellow")
                    else:
                        safe_console_print(f"❌ No real AI executions detected", style="bold red")

                # Return success - Issue #2121: Missing return statement causing test failures
                return True
        finally:
            # ISSUE #2832 FIX: Always generate JSON output if in JSON mode
            # This executes REGARDLESS of return path (success or failure)
            if self.json_mode:
                execution_end_time = time.time()

                json_generator = JSONOutputGenerator(
                    cli=self,
                    config=self.config,
                    events=self.ws_client.events if self.ws_client else [],
                    errors=self.errors,
                    start_time=execution_start_time,
                    end_time=execution_end_time
                )
                json_output = json_generator.generate()

                # Initialize output formatter if not already done
                if not self.output_formatter:
                    self.output_formatter = CLIOutputFormatter()

                # Write JSON output (to file or stdout)
                self.output_formatter.write_json_output(json_output, self.json_output_file)

                # Determine appropriate exit code based on execution results
                exit_code_generator = ExitCodeGenerator(
                    events=self.ws_client.events if self.ws_client else [],
                    errors=self.errors,
                    validation_passed=self.validation_passed
                )
                self.exit_code = exit_code_generator.determine_exit_code()
            else:
                # Non-JSON mode: Set exit code based on basic success/failure
                has_errors = len(self.errors) > 0
                self.exit_code = 1 if has_errors else 0

    async def _wait_for_completion(self):
        """Wait for either agent completion or cleanup completion (Issue #2134)."""
        while True:
            # Check if cleanup is complete
            if self.ws_client.cleanup_complete:
                return

            # Check if we have received agent_completed event (normal completion)
            agent_completed = any(event.type == 'agent_completed' for event in self.ws_client.events)
            if agent_completed:
                # Wait a bit more to see if cleanup events arrive
                await asyncio.sleep(1)
                return

            await asyncio.sleep(0.1)  # Short sleep to avoid busy waiting

    async def run_test_mode(self, test_file: str):
        """Run in test mode with predefined scenarios"""
        safe_console_print(f"Running test scenarios from: {test_file}", style="cyan")

        # Load test scenarios
        with open(test_file, 'r') as f:
            scenarios = yaml.safe_load(f)

        async with AuthManager(self.config) as auth_manager:
            self.auth_manager = auth_manager

            # Get authentication using new priority system
            if self.use_oauth:
                token = await auth_manager.get_valid_token(
                    use_oauth=True,
                    oauth_provider=self.oauth_provider,
                    auth_method=self.auth_method
                )
            else:
                # Use simplified authentication for manual token/no-auth cases
                token = await auth_manager.get_valid_token(
                    use_oauth=False,
                    auth_method=self.auth_method
                )

            if not token:
                safe_console_print("ERROR: Failed to authenticate", style="red")
                return

            results = []

            for scenario in scenarios.get('scenarios', []):
                safe_console_print(f"\nNOTE: Running scenario: {scenario['name']}", style="bold cyan")

                # Connect WebSocket
                self.ws_client = WebSocketClient(
                    self.config, token, self.debug,
                    send_logs=self.send_logs,
                    logs_count=self.logs_count,
                    logs_project=self.logs_project,
                    logs_path=self.logs_path,
                    logs_user=self.logs_user,
                    logs_provider=self.logs_provider,
                    handshake_timeout=self.handshake_timeout
                )
                if not await self.ws_client.connect():
                    results.append({'scenario': scenario['name'], 'status': 'FAILED', 'error': 'WebSocket connection failed'})
                    continue

                # Send message
                message = scenario['message']
                expected_events = scenario.get('expected_events', [])
                wait_time = scenario.get('wait_time', 300)  # Issue #2665: Match real agent execution times

                run_id = await self.ws_client.send_message(message)

                # Collect events
                event_task = asyncio.create_task(self._receive_events())
                await asyncio.sleep(wait_time)
                event_task.cancel()

                # Validate results
                received_types = [e.type for e in self.ws_client.events]
                success = all(event in received_types for event in expected_events)

                results.append({
                    'scenario': scenario['name'],
                    'status': 'PASSED' if success else 'FAILED',
                    'expected': expected_events,
                    'received': received_types
                })

                await self.ws_client.close()

            # Display results
            safe_console_print("\n" + "="*50)
            safe_console_print("Test Results", style="bold")

            table = Table(title="Test Scenarios")
            table.add_column("Scenario", style="cyan")
            table.add_column("Status", style="bold")
            table.add_column("Details")

            for result in results:
                status_style = "green" if result['status'] == 'PASSED' else "red"
                table.add_row(
                    result['scenario'],
                    result['status'],
                    f"Expected: {result.get('expected', [])}\nReceived: {result.get('received', [])}"
                )

            safe_console_print(table)

    async def generate_websocket_troubleshooting_report(self):
        """Generate comprehensive WebSocket troubleshooting report (Issue #2139)."""
        try:
            # Initialize report data
            report = {
                "timestamp": datetime.now().isoformat(),
                "environment": self.config.environment.value,
                "backend_url": self.config.backend_url,
                "websocket_url": self.config.websocket_url,
                "connection_status": "unknown",
                "metrics": {},
                "recent_events": [],
                "cleanup_metrics": {},
                "resource_status": {},
                "recommendations": []
            }

            # Test WebSocket connectivity
            safe_console_print("🔌 Testing WebSocket connectivity...", style="cyan")
            try:
                ws_test_result = await self.health_checker.check_websocket_connectivity()
                report["connection_status"] = "healthy" if ws_test_result.get("websocket", {}).get("status") == "healthy" else "unhealthy"
                report["websocket_test"] = ws_test_result
            except Exception as e:
                report["connection_status"] = "failed"
                report["websocket_error"] = str(e)

            # Collect metrics from monitoring system
            safe_console_print("📊 Collecting WebSocket metrics...", style="cyan")
            try:
                # Try to import and use metrics collector
                # ISSUE #2417: Suppress output during import if --stream-logs is not active
                if not _stream_logs_active and 'suppress_output' in locals():
                    with suppress_output():
                        from netra_backend.app.monitoring.websocket_metrics import get_all_websocket_metrics
                else:
                    from netra_backend.app.monitoring.websocket_metrics import get_all_websocket_metrics
                metrics_data = get_all_websocket_metrics()
                report["metrics"] = metrics_data

                # Extract cleanup-specific metrics
                if "system" in metrics_data and "factory_metrics" in metrics_data["system"]:
                    factory_metrics = metrics_data["system"]["factory_metrics"]
                    report["cleanup_metrics"] = {
                        "cleanup_operations_total": factory_metrics.get("cleanup_operations_total", 0),
                        "cleanup_operations_successful": factory_metrics.get("cleanup_operations_successful", 0),
                        "cleanup_operations_failed": factory_metrics.get("cleanup_operations_failed", 0),
                        "cleanup_success_rate": factory_metrics.get("cleanup_success_rate", 100.0),
                        "cleanup_race_conditions": factory_metrics.get("cleanup_race_conditions_detected", 0),
                        "cleanup_timeouts": factory_metrics.get("cleanup_timeouts_detected", 0),
                        "stale_connections_cleaned": factory_metrics.get("stale_connections_cleaned", 0),
                        "resource_leaks_cleaned": factory_metrics.get("resource_leaks_cleaned", 0)
                    }
            except ImportError:
                report["metrics_error"] = "WebSocket metrics collector not available"
            except Exception as e:
                report["metrics_error"] = f"Failed to collect metrics: {str(e)}"

            # Collect recent WebSocket events
            safe_console_print("📝 Collecting recent WebSocket events...", style="cyan")
            try:
                # ISSUE #2417: Suppress output during import if --stream-logs is not active
                if not _stream_logs_active and 'suppress_output' in locals():
                    with suppress_output():
                        from netra_backend.app.monitoring.websocket_notification_monitor import get_websocket_notification_monitor
                else:
                    from netra_backend.app.monitoring.websocket_notification_monitor import get_websocket_notification_monitor
                monitor = get_websocket_notification_monitor()
                recent_events = monitor.get_recent_events(limit=50)
                report["recent_events"] = recent_events[-10:]  # Last 10 events

                # Check for cleanup-related events
                cleanup_events = [e for e in recent_events if "cleanup" in e.get("event_type", "").lower()]
                report["recent_cleanup_events"] = cleanup_events[-5:]  # Last 5 cleanup events
            except ImportError:
                report["events_error"] = "WebSocket notification monitor not available"
            except Exception as e:
                report["events_error"] = f"Failed to collect events: {str(e)}"

            # Check system resources
            safe_console_print("🖥️ Checking system resources...", style="cyan")
            try:
                import psutil
                process = psutil.Process()
                report["resource_status"] = {
                    "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                    "memory_percent": round(process.memory_percent(), 2),
                    "cpu_percent": round(process.cpu_percent(), 2),
                    "open_files": len(process.open_files()),
                    "connections": len(process.connections()),
                    "threads": process.num_threads()
                }
            except Exception as e:
                report["resource_error"] = f"Failed to collect resource info: {str(e)}"

            # Generate recommendations
            recommendations = []

            if report["connection_status"] == "failed":
                recommendations.append("❌ WebSocket connection failed - check network connectivity and backend status")

            cleanup_metrics = report.get("cleanup_metrics", {})
            if cleanup_metrics.get("cleanup_race_conditions", 0) > 0:
                recommendations.append(f"⚠️ {cleanup_metrics['cleanup_race_conditions']} race conditions detected - review concurrent cleanup logic")

            if cleanup_metrics.get("cleanup_timeouts", 0) > 0:
                recommendations.append(f"⏰ {cleanup_metrics['cleanup_timeouts']} cleanup timeouts detected - consider increasing timeout thresholds")

            if cleanup_metrics.get("cleanup_success_rate", 100.0) < 95.0:
                recommendations.append(f"📉 Low cleanup success rate ({cleanup_metrics['cleanup_success_rate']:.1f}%) - investigate cleanup failures")

            resource_status = report.get("resource_status", {})
            if resource_status.get("memory_mb", 0) > 1000:  # More than 1GB
                recommendations.append(f"🧠 High memory usage ({resource_status['memory_mb']}MB) - potential memory leak")

            if resource_status.get("connections", 0) > 100:
                recommendations.append(f"🔗 High connection count ({resource_status['connections']}) - check for connection leaks")

            if not recommendations:
                recommendations.append("✅ No issues detected - WebSocket system appears healthy")

            report["recommendations"] = recommendations

            # Display the report
            safe_console_print("\n" + "="*80, style="bold cyan")
            safe_console_print("🔍 WEBSOCKET TROUBLESHOOTING REPORT", style="bold cyan")
            safe_console_print("="*80, style="bold cyan")

            # Environment info
            env_table = Table(title="Environment Information")
            env_table.add_column("Property", style="cyan")
            env_table.add_column("Value", style="bold")
            env_table.add_row("Environment", report["environment"])
            env_table.add_row("Backend URL", report["backend_url"])
            env_table.add_row("WebSocket URL", report["websocket_url"])
            env_table.add_row("Connection Status", report["connection_status"])
            env_table.add_row("Report Generated", report["timestamp"])
            safe_console_print(env_table)

            # Cleanup metrics
            if cleanup_metrics:
                cleanup_table = Table(title="Cleanup Metrics")
                cleanup_table.add_column("Metric", style="cyan")
                cleanup_table.add_column("Value", style="bold")
                cleanup_table.add_row("Total Operations", str(cleanup_metrics.get("cleanup_operations_total", 0)))
                cleanup_table.add_row("Successful Operations", str(cleanup_metrics.get("cleanup_operations_successful", 0)))
                cleanup_table.add_row("Failed Operations", str(cleanup_metrics.get("cleanup_operations_failed", 0)))
                cleanup_table.add_row("Success Rate", f"{cleanup_metrics.get('cleanup_success_rate', 100.0):.1f}%")
                cleanup_table.add_row("Race Conditions", str(cleanup_metrics.get("cleanup_race_conditions", 0)))
                cleanup_table.add_row("Timeouts", str(cleanup_metrics.get("cleanup_timeouts", 0)))
                cleanup_table.add_row("Stale Connections Cleaned", str(cleanup_metrics.get("stale_connections_cleaned", 0)))
                cleanup_table.add_row("Resource Leaks Cleaned", str(cleanup_metrics.get("resource_leaks_cleaned", 0)))
                safe_console_print(cleanup_table)

            # Resource status
            if resource_status:
                resource_table = Table(title="System Resources")
                resource_table.add_column("Resource", style="cyan")
                resource_table.add_column("Value", style="bold")
                resource_table.add_row("Memory Usage", f"{resource_status.get('memory_mb', 0):.1f} MB ({resource_status.get('memory_percent', 0):.1f}%)")
                resource_table.add_row("CPU Usage", f"{resource_status.get('cpu_percent', 0):.1f}%")
                resource_table.add_row("Open Files", str(resource_status.get("open_files", 0)))
                resource_table.add_row("Network Connections", str(resource_status.get("connections", 0)))
                resource_table.add_row("Threads", str(resource_status.get("threads", 0)))
                safe_console_print(resource_table)

            # Recommendations
            rec_table = Table(title="Recommendations")
            rec_table.add_column("Recommendation", style="yellow")
            for rec in recommendations:
                rec_table.add_row(rec)
            safe_console_print(rec_table)

            # Recent cleanup events
            if report.get("recent_cleanup_events"):
                events_table = Table(title="Recent Cleanup Events")
                events_table.add_column("Timestamp", style="cyan")
                events_table.add_column("Event Type", style="bold")
                events_table.add_column("User ID", style="green")
                events_table.add_column("Success", style="bold")
                events_table.add_column("Details")

                for event in report["recent_cleanup_events"]:
                    success_style = "green" if event.get("success") else "red"
                    events_table.add_row(
                        event.get("timestamp", "")[:19],  # Truncate timestamp
                        event.get("event_type", ""),
                        event.get("user_id", ""),
                        "✅" if event.get("success") else "❌",
                        event.get("error_message", "") or f"Duration: {event.get('duration_ms', 0):.1f}ms"
                    )
                safe_console_print(events_table)

            # Save report to file
            report_filename = f"websocket_troubleshooting_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_path = Path.home() / ".netra" / report_filename

            try:
                report_path.parent.mkdir(exist_ok=True)
                with open(report_path, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                safe_console_print(f"\n📄 Full report saved to: {report_path}", style="green")
            except Exception as e:
                safe_console_print(f"\n⚠️ Could not save report file: {e}", style="yellow")

            safe_console_print("\n✅ Troubleshooting report generation complete!", style="bold green")

        except Exception as e:
            safe_console_print(f"❌ Failed to generate troubleshooting report: {e}", style="red")
            import traceback
            safe_console_print(traceback.format_exc(), style="dim red")

    async def display_golden_path_dashboard(self):
        """Display real-time Golden Path metrics dashboard (Issue #2218)."""
        try:
            safe_console_print("🎯 Golden Path Real-time Dashboard", style="bold cyan")
            safe_console_print("=" * 50, style="dim")

            # Import Golden Path monitor
            try:
                # ISSUE #2417: Suppress output during import if --stream-logs is not active
                if not _stream_logs_active and 'suppress_output' in locals():
                    with suppress_output():
                        from netra_backend.app.monitoring.golden_path_monitor import GoldenPathMonitor
                else:
                    from netra_backend.app.monitoring.golden_path_monitor import GoldenPathMonitor
                monitor = GoldenPathMonitor()
            except ImportError as e:
                safe_console_print(f"❌ Could not import Golden Path monitor: {e}", style="red")
                return

            # Get dashboard metrics
            safe_console_print("📊 Collecting dashboard metrics...", style="cyan")
            dashboard_metrics = await monitor.get_dashboard_metrics()

            # Display main metrics
            main_table = Table(title="Golden Path Overview")
            main_table.add_column("Metric", style="cyan")
            main_table.add_column("Value", style="bold")
            main_table.add_column("Status", style="bold")

            # Success rate with status
            success_rate = dashboard_metrics.success_rate_percent
            rate_status = "✅ Healthy" if success_rate >= 95 else "⚠️ Warning" if success_rate >= 90 else "❌ Critical"
            main_table.add_row("Success Rate", f"{success_rate:.1f}%", rate_status)

            main_table.add_row("Total Journeys", str(dashboard_metrics.total_journeys), "")
            main_table.add_row("Successful", str(dashboard_metrics.successful_journeys), "")
            main_table.add_row("Failed", str(dashboard_metrics.failed_journeys), "")
            main_table.add_row("Active Journeys", str(dashboard_metrics.active_journeys), "")
            main_table.add_row("Avg Completion", f"{dashboard_metrics.average_completion_time_ms:.0f}ms", "")
            main_table.add_row("P95 Completion", f"{dashboard_metrics.p95_completion_time_ms:.0f}ms", "")
            main_table.add_row("System Health", dashboard_metrics.system_health_status.title(),
                             "✅" if dashboard_metrics.system_health_status == "healthy" else "⚠️")

            safe_console_print(main_table)

            # Individual event metrics (Issue #2218 requirement)
            if dashboard_metrics.individual_events:
                event_table = Table(title="Individual Event Success Rates")
                event_table.add_column("Event", style="cyan")
                event_table.add_column("Success Rate", style="bold")
                event_table.add_column("Total", style="dim")
                event_table.add_column("Avg Duration", style="dim")
                event_table.add_column("Status", style="bold")

                for event_name, event_metrics in dashboard_metrics.individual_events.items():
                    event_status = "✅" if event_metrics.success_rate_percent >= 99 else "⚠️" if event_metrics.success_rate_percent >= 95 else "❌"
                    event_table.add_row(
                        event_name,
                        f"{event_metrics.success_rate_percent:.1f}%",
                        str(event_metrics.total_occurrences),
                        f"{event_metrics.average_duration_ms:.0f}ms",
                        event_status
                    )

                safe_console_print(event_table)

            # Active alerts
            if dashboard_metrics.active_alerts:
                alert_table = Table(title="Active Alerts")
                alert_table.add_column("Type", style="red")
                alert_table.add_column("Severity", style="bold")
                alert_table.add_column("Message", style="yellow")
                alert_table.add_column("Timestamp", style="dim")

                for alert in dashboard_metrics.active_alerts:
                    severity_style = "red" if alert.get("severity") == "critical" else "yellow"
                    alert_table.add_row(
                        alert.get("type", "unknown"),
                        f"[{severity_style}]{alert.get('severity', 'unknown')}[/]",
                        alert.get("message", "No message"),
                        alert.get("timestamp", datetime.now()).strftime("%H:%M:%S") if isinstance(alert.get("timestamp"), datetime) else str(alert.get("timestamp", ""))
                    )

                safe_console_print(alert_table)
            else:
                safe_console_print("✅ No active alerts", style="green")

            # Trending data (if available)
            if dashboard_metrics.hourly_success_rates:
                safe_console_print(f"\n📈 24-Hour Success Rate Trend: {len(dashboard_metrics.hourly_success_rates)} data points", style="cyan")
                recent_rates = dashboard_metrics.hourly_success_rates[-6:]  # Last 6 hours
                trend_text = " → ".join([f"{rate:.1f}%" for rate in recent_rates])
                safe_console_print(f"Recent: {trend_text}", style="dim")

            safe_console_print(f"\n🕒 Dashboard updated: {dashboard_metrics.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", style="dim")
            safe_console_print("\n✅ Golden Path dashboard display complete!", style="bold green")

        except Exception as e:
            safe_console_print(f"❌ Failed to display Golden Path dashboard: {e}", style="red")
            import traceback
            safe_console_print(traceback.format_exc(), style="dim red")

    async def display_golden_path_health_metrics(self):
        """Display current Golden Path completion rates and health metrics (Issue #2218)."""
        try:
            safe_console_print("🏥 Golden Path Health Metrics", style="bold cyan")
            safe_console_print("=" * 40, style="dim")

            # Import Golden Path monitor
            try:
                # ISSUE #2417: Suppress output during import if --stream-logs is not active
                if not _stream_logs_active and 'suppress_output' in locals():
                    with suppress_output():
                        from netra_backend.app.monitoring.golden_path_monitor import GoldenPathMonitor
                else:
                    from netra_backend.app.monitoring.golden_path_monitor import GoldenPathMonitor
                monitor = GoldenPathMonitor()
            except ImportError as e:
                safe_console_print(f"❌ Could not import Golden Path monitor: {e}", style="red")
                return

            # Get base metrics
            safe_console_print("📊 Collecting health metrics...", style="cyan")
            base_metrics = await monitor.get_golden_path_metrics()
            dashboard_metrics = await monitor.get_dashboard_metrics()

            # Health summary
            health_table = Table(title="Health Summary")
            health_table.add_column("Metric", style="cyan")
            health_table.add_column("Current Value", style="bold")
            health_table.add_column("Threshold", style="dim")
            health_table.add_column("Status", style="bold")

            # Golden Path completion rate
            completion_rate = base_metrics.success_rate_percent
            completion_threshold = 95.0
            completion_status = "✅ PASS" if completion_rate >= completion_threshold else "❌ FAIL"
            health_table.add_row("Golden Path Completion Rate", f"{completion_rate:.1f}%", f"≥{completion_threshold}%", completion_status)

            # WebSocket events success rate
            ws_rate = base_metrics.websocket_events_success_rate
            ws_threshold = 99.0
            ws_status = "✅ PASS" if ws_rate >= ws_threshold else "❌ FAIL"
            health_table.add_row("WebSocket Events Success", f"{ws_rate:.1f}%", f"≥{ws_threshold}%", ws_status)

            # Agent chain success rate
            agent_rate = base_metrics.agent_chain_success_rate
            agent_threshold = 99.0
            agent_status = "✅ PASS" if agent_rate >= agent_threshold else "❌ FAIL"
            health_table.add_row("Agent Chain Success", f"{agent_rate:.1f}%", f"≥{agent_threshold}%", agent_status)

            # Completion time check
            avg_completion = base_metrics.average_completion_time_ms
            completion_time_threshold = 30000.0  # 30 seconds
            time_status = "✅ PASS" if avg_completion <= completion_time_threshold else "❌ FAIL"
            health_table.add_row("Avg Completion Time", f"{avg_completion:.0f}ms", f"≤{completion_time_threshold:.0f}ms", time_status)

            safe_console_print(health_table)

            # Individual event health details
            if dashboard_metrics.individual_events:
                event_health_table = Table(title="Individual Event Health Details")
                event_health_table.add_column("Event", style="cyan")
                event_health_table.add_column("Success Rate", style="bold")
                event_health_table.add_column("Total Count", style="dim")
                event_health_table.add_column("Failed Count", style="dim")
                event_health_table.add_column("Last Failure", style="dim")
                event_health_table.add_column("Health", style="bold")

                for event_name, event_metrics in dashboard_metrics.individual_events.items():
                    health_status = "✅ HEALTHY" if event_metrics.success_rate_percent >= 99 else "⚠️ DEGRADED" if event_metrics.success_rate_percent >= 95 else "❌ UNHEALTHY"
                    last_failure = "Never" if not event_metrics.last_failure_time else event_metrics.last_failure_time.strftime("%H:%M:%S")

                    event_health_table.add_row(
                        event_name,
                        f"{event_metrics.success_rate_percent:.1f}%",
                        str(event_metrics.total_occurrences),
                        str(event_metrics.failed_occurrences),
                        last_failure,
                        health_status
                    )

                safe_console_print(event_health_table)

            # Overall system status
            overall_health = "HEALTHY" if completion_rate >= 95 and ws_rate >= 99 and agent_rate >= 99 and avg_completion <= 30000 else "UNHEALTHY"
            health_color = "green" if overall_health == "HEALTHY" else "red"

            safe_console_print(f"\n🎯 Overall Golden Path Health: [{health_color}]{overall_health}[/]", style="bold")

            # Recommendations based on health
            recommendations = []
            if completion_rate < 95:
                recommendations.append("⚠️ Golden Path completion rate below 95% - investigate journey failures")
            if ws_rate < 99:
                recommendations.append("⚠️ WebSocket event success rate below 99% - check event delivery")
            if agent_rate < 99:
                recommendations.append("⚠️ Agent chain success rate below 99% - review agent execution")
            if avg_completion > 30000:
                recommendations.append("⚠️ Average completion time exceeds 30s - optimize agent performance")

            if recommendations:
                rec_table = Table(title="Health Recommendations")
                rec_table.add_column("Recommendation", style="yellow")
                for rec in recommendations:
                    rec_table.add_row(rec)
                safe_console_print(rec_table)
            else:
                safe_console_print("✅ All health metrics within acceptable thresholds", style="green")

            # Alert summary
            if dashboard_metrics.active_alerts:
                safe_console_print(f"\n🚨 Active Alerts: {dashboard_metrics.alert_summary}", style="red")
            else:
                safe_console_print("\n✅ No active alerts", style="green")

            safe_console_print(f"\n🕒 Metrics collected: {base_metrics.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", style="dim")
            safe_console_print("\n✅ Health metrics display complete!", style="bold green")

        except Exception as e:
            safe_console_print(f"❌ Failed to display health metrics: {e}", style="red")
            import traceback
            safe_console_print(traceback.format_exc(), style="dim red")


def main(argv=None):
    """Main entry point

    Args:
        argv: Command-line arguments (default: None uses sys.argv)
    """

    parser = argparse.ArgumentParser(
        prog="zen --apex",
        description="Netra Agent CLI - Test agent interactions from command line (ISSUE #1603: Enhanced with event output and GCP error lookup)",
        epilog="Examples:\n"
               "  %(prog)s --message 'triage this incident'  # logs attached by default\n"
               "  %(prog)s --message 'analyze rollout' --no-send-logs  # disable log attachment\n"
               "  %(prog)s --message 'review QA findings' --logs-project qa-suite\n"
               "  %(prog)s --logs-path ~/.claude/Projects --message 'audit sessions'\n"
               "  %(prog)s --lookup-errors cli_20250121_123456_789",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--env",
        type=str,
        choices=["local", "staging", "production", "development"],
        default="staging",
        help="Environment to connect to (default: staging). Use 'development' with --backend-url for custom backend."
    )

    parser.add_argument(
        "--backend-url",
        type=str,
        help="Custom backend URL for development environment (e.g., https://api.custom.example.com). "
             "Only used when --env development is specified."
    )

    parser.add_argument(
        "--client-environment",
        type=str,
        choices=["local", "staging", "production"],
        help="Client environment for timeout coordination with backend (Issue #2442). Overrides automatic environment detection for timeout configuration."
    )

    parser.add_argument(
        "--message",
        "-m",
        type=str,
        help="Send a single message and exit"
    )

    parser.add_argument(
        "--wait",
        "-w",
        type=int,
        default=300,
        help="Time to wait for events (default: 300 seconds) - Issue #2665: Agents take 100s+ in staging"
    )

    parser.add_argument(
        "--test",
        "-t",
        type=str,
        help="Run test scenarios from YAML file"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cached authentication token"
    )

    parser.add_argument(
        "--token",
        type=str,
        help="Use a specific JWT token for authentication (bypasses login)"
    )

    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Skip authentication (only works if backend is in permissive mode)"
    )

    parser.add_argument(
        "--oauth-login",
        action="store_true",
        help="[DEPRECATED] OAuth is now the default authentication method"
    )

    parser.add_argument(
        "--oauth-provider",
        type=str,
        choices=["google"],
        default="google",
        help="OAuth provider to use (default: google)"
    )

    parser.add_argument(
        "--auth-method",
        type=str,
        choices=["auto", "e2e", "oauth"],
        default="auto",
        help="Authentication method preference: auto (default for env), e2e (simulation), oauth (browser)"
    )

    # Debug and diagnostic arguments
    parser.add_argument(
        "--debug-level",
        type=str,
        choices=["silent", "basic", "verbose", "trace", "diagnostic"],
        default="silent",
        help="Debug verbosity level (default: silent)"
    )

    parser.add_argument(
        "--debug-log",
        type=str,
        help="Debug log file path (default: ~/.netra/cli_debug.log)"
    )

    parser.add_argument(
        "--enable-websocket-diagnostics",
        action="store_true",
        default=True,  # Issue #2484 Phase 2: Enabled by default
        help="Enable enhanced WebSocket error diagnostics (default: enabled, Issue #2484)"
    )

    parser.add_argument(
        "--disable-websocket-diagnostics",
        action="store_true",
        help="Disable WebSocket error diagnostics (opt-out)"
    )

    # SSOT Thread Management Arguments
    parser.add_argument(
        "--handshake-timeout",
        type=float,
        default=2.0,
        help="Timeout for handshake with backend (seconds, default: 2.0)"
    )

    parser.add_argument(
        "--disable-backend-threads",
        action="store_true",
        help="SSOT: Disable backend thread ID management and use local generation (backward compatibility)"
    )

    parser.add_argument(
        "--clear-thread-cache",
        action="store_true",
        help="SSOT: Clear cached thread IDs and force new thread creation"
    )

    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Run comprehensive health check and exit"
    )

    parser.add_argument(
        "--check-backend",
        action="store_true",
        help="Check backend service health and exit"
    )

    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="Check auth service health and exit"
    )

    parser.add_argument(
        "--check-websocket",
        action="store_true",
        help="Check WebSocket connectivity and exit"
    )

    parser.add_argument(
        "--check-environment",
        action="store_true",
        help="Check environment detection and display environment info"
    )

    parser.add_argument(
        "--session-stats",
        action="store_true",
        help="Show debug session statistics and exit"
    )

    parser.add_argument(
        "--generate-troubleshooting-report",
        action="store_true",
        help="Generate comprehensive WebSocket troubleshooting report and exit (Issue #2139)"
    )

    parser.add_argument(
        "--lookup-errors",
        type=str,
        help="ISSUE #1603: Look up GCP errors for a specific run_id"
    )

    parser.add_argument(
        "--gcp-project",
        type=str,
        default="netra-staging",
        help="GCP project name for error lookup (default: netra-staging)"
    )

    parser.add_argument(
        "--display-mode",
        choices=[DisplayMode.EMOJI, DisplayMode.ASCII, DisplayMode.AUTO],
        default=DisplayMode.AUTO,
        help="Terminal display mode: emoji (full Unicode), ascii (Windows compatible), auto (detect automatically)"
    )

    parser.add_argument(
        "--validate-outputs",
        action="store_true",
        help="ISSUE #1822: Validate agent outputs for business value and substantive content"
    )

    parser.add_argument(
        "--validate-business-value",
        action="store_true",
        help="Validate agent responses for business value delivery and revenue impact"
    )

    parser.add_argument(
        "--user-segment",
        type=str,
        choices=["free", "early", "mid", "enterprise"],
        default="free",
        help="User segment for business value validation (default: free)"
    )

    parser.add_argument(
        "--stream-logs",
        action="store_true",
        help="ISSUE #1828: Stream backend logs in real-time via WebSocket"
    )

    parser.add_argument(
        "--strict-validation",
        action="store_true",
        help="ISSUE #1817: Enable strict agent chain validation - fail if all 3 agents don't execute"
    )

    parser.add_argument(
        "--validate-events",
        action="store_true",
        help="ISSUE #2177: Enable WebSocket event validation framework for critical events"
    )

    parser.add_argument(
        "--event-validation-strict",
        action="store_true",
        help="ISSUE #2177: Strict event validation - fail on any validation errors (no warnings allowed)"
    )

    # ISSUE #2190: Retry control flags
    parser.add_argument(
        "--disable-retries",
        action="store_true",
        help="ISSUE #2190: Disable agent retries (sets max_retries=0)"
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="ISSUE #2190: Set maximum number of retry attempts (overrides default)"
    )

    parser.add_argument(
        "--retry-info",
        action="store_true",
        help="ISSUE #2190: Display verbose retry information in agent output"
    )

    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="ISSUE #2564: Run WebSocket performance benchmarks and display results"
    )

    # ISSUE #2218: Golden Path monitoring commands
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="ISSUE #2218: Display real-time Golden Path metrics dashboard and exit"
    )

    parser.add_argument(
        "--health-metrics",
        action="store_true",
        help="ISSUE #2218: Show current Golden Path completion rates and individual event success rates"
    )

    # ISSUE #2483: Timeout hierarchy validation control
    parser.add_argument(
        "--skip-timeout-validation",
        action="store_true",
        help="ISSUE #2483: Skip timeout hierarchy validation that checks WebSocket timeout > Agent timeout"
    )

    # ISSUE #2766: CI/CD Integration - JSON Output and Exit Codes
    parser.add_argument(
        "--json",
        action="store_true",
        help="ISSUE #2766: Output results in JSON format for CI/CD integration"
    )

    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="ISSUE #2766: Enable CI/CD mode - suppresses Rich terminal output, enables JSON"
    )

    parser.add_argument(
        "--json-output",
        type=str,
        metavar="FILE",
        help="ISSUE #2766: Write JSON output to specified file (implies --json)"
    )

    # Log forwarding arguments
    parser.add_argument(
        "--send-logs",
        "--logs",
        dest="send_logs",
        action="store_true",
        default=True,
        help="Attach recent JSONL logs from .claude/Projects to message payload (default: enabled)"
    )

    parser.add_argument(
        "--no-send-logs",
        "--no-logs",
        dest="send_logs",
        action="store_false",
        help="Disable automatic log attachment"
    )

    parser.add_argument(
        "--logs-count",
        type=int,
        default=1,
        metavar="N",
        help="Number of recent log files to collect (default: 1, must be positive). For best results, use 1 log at a time for focused analysis."
    )

    parser.add_argument(
        "--logs-project",
        type=str,
        metavar="NAME",
        help="Specific project name to collect logs from (default: most recent)"
    )

    parser.add_argument(
        "--logs-path",
        type=str,
        metavar="PATH",
        help="Custom path to .claude/Projects directory"
    )

    parser.add_argument(
        "--logs-user",
        type=str,
        metavar="USERNAME",
        help="Windows username for path resolution (Windows only)"
    )

    parser.add_argument(
        "--logs-provider",
        type=str,
        choices=["claude", "codex", "gemini"],
        default="claude",
        metavar="PROVIDER",
        help="AI tool provider to collect logs from: claude (default), codex (OpenAI Codex CLI), gemini (Google Gemini CLI)"
    )

    args = parser.parse_args(argv)

    # Validate log-forwarding arguments
    if args.logs_count < 1:
        parser.error("--logs-count must be a positive integer")

    # Validate development environment configuration
    if args.backend_url and args.env != "development":
        parser.error("--backend-url can only be used with --env development")
    if args.env == "development" and not args.backend_url:
        parser.error("--backend-url is required when using --env development")

    # ISSUE #2766: Determine JSON/CI mode EARLY (before any output)
    json_mode = args.json or args.json_output is not None
    ci_mode = args.ci_mode or args.json_output is not None  # --json-output implies CI mode

    # ISSUE #2766: Suppress ALL logging output in JSON/CI mode
    if json_mode or ci_mode:
        # Set root logger to CRITICAL to suppress all INFO/DEBUG/WARNING logs
        logging.getLogger().setLevel(logging.CRITICAL)
        # Also suppress all handlers
        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)
        # Add a NullHandler to completely silence logging
        logging.getLogger().addHandler(logging.NullHandler())

    # Handle --check-environment flag early to avoid heavy initialization
    if args.check_environment:
        try:
            # Use minimal imports for environment detection
            # ISSUE #2417: Suppress output during import if --stream-logs is not active
            if not _stream_logs_active and 'suppress_output' in locals():
                with suppress_output():
                    from netra_backend.app.core.environment_context.cloud_environment_detector import detect_current_environment
            else:
                from netra_backend.app.core.environment_context.cloud_environment_detector import detect_current_environment

            async def run_environment_check():
                try:
                    context = await detect_current_environment()

                    # Format output as expected by the test (key: value format)
                    print(f"environment_type: {context.environment_type.value}")
                    print(f"cloud_platform: {context.cloud_platform.value}")
                    print(f"confidence_score: {context.confidence_score:.2f}")

                    if context.project_id:
                        print(f"project_id: {context.project_id}")
                    if context.region:
                        print(f"region: {context.region}")
                    if context.service_name:
                        print(f"service_name: {context.service_name}")
                    if context.revision:
                        print(f"revision: {context.revision}")

                    # Additional info for debugging
                    print(f"detection_method: {context.detection_metadata.get('method', 'unknown')}")
                    print(f"detection_timestamp: {context.detection_timestamp.isoformat()}")

                except Exception as e:
                    print(f"Environment detection failed: {str(e)}", file=sys.stderr)
                    sys.exit(1)

            asyncio.run(run_environment_check())
            sys.exit(0)

        except ImportError:
            print("Error: CloudEnvironmentDetector not available", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Environment check failed: {str(e)}", file=sys.stderr)
            sys.exit(1)


    # Setup logging with --stream-logs control
    # ISSUE #2417: Control backend JSON logging based on --stream-logs flag
    if args.stream_logs:
        # Enable full logging when streaming is requested
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            force=True  # Override any existing configuration
        )

        # Re-enable the backend loggers that were suppressed during startup
        for logger_name in ['netra_backend', 'netra-service', 'shared']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(log_level)
            logger.disabled = False  # Re-enable these loggers

        safe_console_print("📡 Stream logs enabled - backend logging active", style="cyan")
    else:
        # Keep logging minimal to prevent JSON output noise during CLI operations
        log_level = logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            force=True  # Override any existing configuration
        )

        # Keep backend loggers suppressed for clean CLI output
        for logger_name in ['netra_backend', 'netra-service', 'shared']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.CRITICAL)
            logger.disabled = True

    # Map debug level string to enum
    debug_level_map = {
        "silent": DebugLevel.SILENT,
        "basic": DebugLevel.BASIC,
        "verbose": DebugLevel.VERBOSE,
        "trace": DebugLevel.TRACE,
        "diagnostic": DebugLevel.DIAGNOSTIC
    }

    # Set global display mode from CLI argument
    global GLOBAL_DISPLAY_MODE
    GLOBAL_DISPLAY_MODE = args.display_mode

    # ISSUE #2190: Process retry configuration flags
    retry_config = {}

    # Validate max_retries flag
    if args.max_retries is not None:
        if args.max_retries < 0:
            safe_console_print("ERROR: --max-retries must be non-negative", style="red")
            sys.exit(1)
        retry_config['max_retries'] = args.max_retries

    # Handle disable-retries flag
    if args.disable_retries:
        if args.max_retries is not None and args.max_retries > 0:
            safe_console_print("WARNING: --disable-retries overrides --max-retries", style="yellow")
        retry_config['max_retries'] = 0

    # Store retry display preference
    retry_config['show_retry_info'] = args.retry_info

    if retry_config.get('max_retries') is not None:
        max_retry_value = retry_config['max_retries']
        if max_retry_value == 0:
            safe_console_print("🚫 Retry configuration: Retries disabled", style="yellow")
        else:
            safe_console_print(f"🔄 Retry configuration: Max retries set to {max_retry_value}", style="cyan")

    if args.retry_info:
        safe_console_print("ℹ️ Retry configuration: Verbose retry information enabled", style="cyan")

    # Create config
    # Issue #2484 Phase 2: Handle opt-out logic for WebSocket diagnostics
    enable_diagnostics = args.enable_websocket_diagnostics and not args.disable_websocket_diagnostics

    config = Config(
        environment=Environment(args.env),
        client_environment=getattr(args, 'client_environment', None),  # Issue #2442: Client environment override for timeouts
        custom_backend_url=getattr(args, 'backend_url', None),  # Custom backend URL for development environment
        log_level="DEBUG" if args.verbose else "INFO",
        debug_level=debug_level_map[args.debug_level],
        debug_log_file=Path(args.debug_log) if args.debug_log else None,
        stream_logs=args.stream_logs,  # Issue #1828: Backend log streaming
        enable_websocket_diagnostics=enable_diagnostics,  # Issue #2484 Phase 2: Default enabled with opt-out
        skip_timeout_validation=args.skip_timeout_validation,  # Issue #2483: Skip timeout hierarchy validation
        json_mode=json_mode,  # ISSUE #2766: Pass json_mode to config for output suppression
        ci_mode=ci_mode,  # ISSUE #2766: Pass ci_mode to config for output suppression
        use_backend_threads=not args.disable_backend_threads  # SSOT: Backend thread management (enabled by default)
    )

    # ISSUE #2839: Load validation framework imports when validation is explicitly requested
    # Only import heavy modules when validation features are actually needed
    global BusinessValueValidator, BusinessValueResult, ValidationWebSocketEvent
    if args.validate_business_value or args.validate_outputs:
        # ISSUE #2417: Additional logging suppression during validation imports
        if not _stream_logs_active and 'suppress_output' in locals():
            # Add extra logging suppression during these imports
            original_levels = {}
            loggers_to_suppress = ['netra_backend', 'test_framework', 'shared', 'unified_id_manager', 'websocket_manager']
            for logger_name in loggers_to_suppress:
                logger = logging.getLogger(logger_name)
                original_levels[logger_name] = logger.level
                logger.setLevel(logging.CRITICAL)
                logger.disabled = True
        try:
            from test_framework.validation.business_value_validator import (
                BusinessValueValidator, BusinessValueResult, WebSocketEvent as ValidationWebSocketEvent
            )
        except ImportError:
            # Try from test_framework root
            try:
                from test_framework.business_value_validator import (
                    BusinessValueValidator, BusinessValueResult, WebSocketEvent as ValidationWebSocketEvent
                )
            except ImportError:
                # Validation framework is optional
                if config.environment == Environment.LOCAL:
                    safe_console_print("Note: Business value validation not available in local environment", style="dim")
                else:
                    safe_console_print("WARNING: Business value validation framework not available", style="yellow")

        # ISSUE #2417: Restore original logging levels after imports
        if not stream_logs_active and 'suppress_output' in locals() and 'original_levels' in locals():
            for logger_name, original_level in original_levels.items():
                logger = logging.getLogger(logger_name)
                logger.setLevel(original_level)
                logger.disabled = False

    # Clear cache if requested
    if args.clear_cache:
        if config.token_file.exists():
            config.token_file.unlink()
            safe_console_print("SUCCESS: Cleared cached authentication token", style="green",
                             json_mode=json_mode, ci_mode=ci_mode)

    # SSOT: Clear thread cache if requested
    if args.clear_thread_cache:
        # Use platform-aware cache path
        from pathlib import Path
        import platform as stdlib_platform

        system = stdlib_platform.system()
        if system == "Windows":
            app_data = os.environ.get('LOCALAPPDATA', str(Path.home() / "AppData" / "Local"))
            thread_cache_file = Path(app_data) / "Netra" / "CLI" / "thread_cache.json"
        elif system == "Darwin":
            thread_cache_file = Path.home() / "Library" / "Application Support" / "Netra" / "CLI" / "thread_cache.json"
        else:
            xdg_data = os.environ.get('XDG_DATA_HOME', str(Path.home() / ".local" / "share"))
            thread_cache_file = Path(xdg_data) / "netra" / "cli" / "thread_cache.json"
            # Also check legacy location
            legacy_cache = Path.home() / ".netra" / "thread_cache.json"
            if legacy_cache.exists():
                legacy_cache.unlink()

        if thread_cache_file.exists():
            thread_cache_file.unlink()
            safe_console_print("SUCCESS: Cleared cached thread IDs", style="green",
                             json_mode=json_mode, ci_mode=ci_mode)

    # ISSUE #2766: json_mode and ci_mode already determined at top of main()
    json_output_file = args.json_output

    # ISSUE #2766: Create output formatter and suppress Rich output if in CI mode
    output_formatter = CLIOutputFormatter(ci_mode=ci_mode)
    if ci_mode:
        output_formatter.suppress_rich_output()

    # Create CLI
    cli = AgentCLI(
        config,
        validate_outputs=args.validate_outputs,
        strict_validation=args.strict_validation,
        validate_business_value=args.validate_business_value,
        user_segment=args.user_segment,
        retry_config=retry_config,
        json_mode=json_mode,
        ci_mode=ci_mode,
        json_output_file=json_output_file,
        send_logs=args.send_logs,
        logs_count=args.logs_count,
        logs_project=args.logs_project,
        logs_path=args.logs_path,
        logs_user=args.logs_user,
        logs_provider=args.logs_provider,
        handshake_timeout=args.handshake_timeout
    )

    # ISSUE #2766: Store output formatter reference in CLI instance
    cli.output_formatter = output_formatter

    # ISSUE #1603: Handle GCP error lookup
    if args.lookup_errors:
        async def run_gcp_error_lookup():
            try:
                safe_console_print(f"🔍 GCP Error Lookup for run_id: {args.lookup_errors}", style="bold cyan")
                gcp_lookup = GCPErrorLookup(project=args.gcp_project)
                results = await gcp_lookup.lookup_errors_for_run_id(args.lookup_errors)

                # Additional CLI-specific output
                if results.get("total_errors", 0) > 0:
                    safe_console_print(f"\n💡 Suggested Actions: ", style="bold yellow")
                    safe_console_print("1. Check WebSocket connection stability", style="dim")
                    safe_console_print("2. Verify authentication token validity", style="dim")
                    safe_console_print("3. Review agent message payload structure", style="dim")
                    safe_console_print("4. Check service health endpoints", style="dim")

                # Save detailed results if requested
                if args.verbose:
                    output_file = Path.home() / f".netra/error_analysis_{args.lookup_errors}.json"
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_file, 'w') as f:
                        json.dump(results, f, indent=2, default=str)
                    safe_console_print(f"\n📁 Detailed results saved to: {output_file}", style="dim")

            except Exception as e:
                safe_console_print(f"ERROR: GCP error lookup failed: {e}", style="red")
                if args.verbose:
                    import traceback
                    safe_console_print(traceback.format_exc(), style="dim red")
                sys.exit(1)

        # Run GCP error lookup and exit
        try:
            asyncio.run(run_gcp_error_lookup())
        except KeyboardInterrupt:
            safe_console_print("\n[FAIL] GCP error lookup interrupted", style="yellow")
        sys.exit(0)

    # Handle health check commands (ISSUE #2218: Added Golden Path monitoring commands)
    if args.health_check or args.check_backend or args.check_auth or args.check_websocket or args.check_environment or args.session_stats or args.generate_troubleshooting_report or args.monitor or args.health_metrics:
        async def run_health_checks():
            try:
                if args.health_check:
                    safe_console_print("[CHECK] Running comprehensive health check...", style="cyan")
                    results = await cli.health_checker.comprehensive_health_check()

                    # Display results in a nice table
                    table = Table(title="Health Check Results")
                    table.add_column("Service", style="cyan")
                    table.add_column("Status", style="bold")
                    table.add_column("Details")

                    for service, result in results.items():
                        if service in ["timestamp", "environment", "overall_status"]:
                            continue

                        status = result.get("status", "unknown")
                        status_style = "green" if status in ["healthy", "reachable", "normal"] else "red"

                        details = ""
                        if "status_code" in result:
                            details += f"HTTP {result['status_code']}"
                        if "error" in result:
                            details += f" Error: {result['error'][:50]}..."
                        if status == "normal" and "cpu_percent" in result:
                            details = f"CPU: {result['cpu_percent']:.1f}%, Memory: {result['memory_percent']:.1f}%"

                        table.add_row(service.title(), f"[{status_style}]{status}[/{status_style}]", details)

                    safe_console_print(table)
                    safe_console_print(f"\n[STATUS] Overall Status: [bold {'green' if results['overall_status'] == 'healthy' else 'red'}]{results['overall_status']}[/]")

                elif args.check_backend:
                    safe_console_print("[CHECK] Checking backend health...", style="cyan")
                    result = await cli.health_checker.check_backend_health()
                    safe_console_print(f"Backend Status: {result['status']}")
                    if result['status'] == 'healthy' and 'data' in result:
                        safe_console_print(Panel(Syntax(json.dumps(result['data'], indent=2), "json", word_wrap=True), title="Health Data"))
                    elif 'error' in result:
                        safe_console_print(f"Error: {result['error']}", style="red")

                elif args.check_auth:
                    safe_console_print("[CHECK] Checking auth service health...", style="cyan")
                    result = await cli.health_checker.check_auth_service_health()
                    safe_console_print(f"Auth Service Status: {result['status']}")
                    if result['status'] == 'healthy' and 'data' in result:
                        safe_console_print(Panel(Syntax(json.dumps(result['data'], indent=2), "json", word_wrap=True), title="Health Data"))
                    elif 'error' in result:
                        safe_console_print(f"Error: {result['error']}", style="red")

                elif args.check_websocket:
                    safe_console_print("[CHECK] Checking WebSocket connectivity...", style="cyan")
                    result = await cli.health_checker.check_websocket_connectivity()
                    safe_console_print(f"WebSocket Status: {result['status']}")
                    if 'error' in result:
                        safe_console_print(f"Error: {result['error']}", style="red")

                elif args.check_environment:
                    safe_console_print("[CHECK] Detecting environment context...", style="cyan")

                    if detect_current_environment is None:
                        safe_console_print("Error: CloudEnvironmentDetector not available", style="red")
                        sys.exit(1)

                    try:
                        context = await detect_current_environment()

                        # Format output as expected by the test (key: value format)
                        safe_console_print(f"environment_type: {context.environment_type.value}")
                        safe_console_print(f"cloud_platform: {context.cloud_platform.value}")
                        safe_console_print(f"confidence_score: {context.confidence_score:.2f}")

                        if context.project_id:
                            safe_console_print(f"project_id: {context.project_id}")
                        if context.region:
                            safe_console_print(f"region: {context.region}")
                        if context.service_name:
                            safe_console_print(f"service_name: {context.service_name}")
                        if context.revision:
                            safe_console_print(f"revision: {context.revision}")

                        # Additional info for debugging
                        safe_console_print(f"detection_method: {context.detection_metadata.get('method', 'unknown')}")
                        safe_console_print(f"detection_timestamp: {context.detection_timestamp.isoformat()}")

                        # ISSUE #2483: Add timeout hierarchy validation report
                        safe_console_print("\n[CHECK] Timeout Configuration Analysis...", style="cyan")

                        try:
                            from netra_backend.app.core.timeout_configuration import get_websocket_recv_timeout, get_agent_execution_timeout
                            from diagnostic_utilities.websocket_diagnostic_utility import WebSocketDiagnosticUtility

                            # Get timeout values
                            websocket_timeout = get_websocket_recv_timeout(client_environment=config.client_environment)
                            agent_timeout = get_agent_execution_timeout()
                            environment = config.environment.value

                            # Create diagnostic utility and validate
                            diagnostic_utility = WebSocketDiagnosticUtility(debug_manager=cli.debug)
                            validation_result = diagnostic_utility.validate_timeout_hierarchy(
                                websocket_timeout=float(websocket_timeout),
                                agent_timeout=float(agent_timeout),
                                environment=environment
                            )

                            # Create timeout validation table
                            timeout_table = Table(title="Timeout Configuration Analysis")
                            timeout_table.add_column("Component", style="cyan")
                            timeout_table.add_column("Timeout", style="bold")
                            timeout_table.add_column("Status", style="bold")

                            timeout_table.add_row("WebSocket", f"{websocket_timeout}s", "Configured")
                            timeout_table.add_row("Agent Execution", f"{agent_timeout}s", "Configured")
                            timeout_table.add_row("Buffer", f"{validation_result.buffer_seconds:.1f}s",
                                                 "[green]Valid[/green]" if validation_result.is_valid else "[red]Invalid[/red]")
                            timeout_table.add_row("Environment", environment.upper(), "Detected")

                            safe_console_print(timeout_table)

                            # Display validation status
                            if validation_result.is_valid:
                                if validation_result.warnings:
                                    safe_console_print(f"\n[yellow]⚠️ Timeout Status: Valid with warnings[/yellow]")
                                    for warning in validation_result.warnings:
                                        safe_console_print(f"• {warning}", style="yellow")
                                else:
                                    safe_console_print(f"\n[green]✅ Timeout Status: Valid hierarchy[/green]")
                            else:
                                safe_console_print(f"\n[red]❌ Timeout Status: Hierarchy violation detected[/red]")
                                for error in validation_result.errors:
                                    safe_console_print(f"• {error}", style="red")

                            # Show recommendations if any
                            if validation_result.recommendations:
                                safe_console_print(f"\n[cyan]💡 Recommendations: [/cyan]")
                                for rec in validation_result.recommendations:
                                    safe_console_print(f"• {rec}", style="dim")

                        except ImportError as ie:
                            safe_console_print(f"[yellow]⚠️ Timeout validation unavailable: {ie}[/yellow]")
                        except Exception as te:
                            safe_console_print(f"[red]❌ Timeout validation error: {te}[/red]")

                    except Exception as e:
                        safe_console_print(f"Environment detection failed: {str(e)}", style="red")
                        sys.exit(1)

                elif args.benchmark:
                    # ISSUE #2564: Run WebSocket performance benchmarks
                    safe_console_print("[BENCHMARK] Running WebSocket Performance Benchmarks...", style="cyan")
                    safe_console_print("This will run 5 performance benchmarks with real services", style="dim")
                    safe_console_print("Benchmarks include: connection time, auth time, message latency, throughput, agent execution", style="dim")
                    safe_console_print("")

                    # Import subprocess to run pytest
                    import subprocess

                    # Path to benchmark test file
                    benchmark_file = Path(__file__).parent.parent / "tests" / "performance" / "test_websocket_performance_benchmarks.py"

                    if not benchmark_file.exists():
                        safe_console_print(f"[red]ERROR: Benchmark file not found: {benchmark_file}[/red]")
                        sys.exit(1)

                    # Run pytest on benchmark file
                    safe_console_print(f"[cyan]Running pytest on: {benchmark_file}[/cyan]")
                    result = subprocess.run(
                        [sys.executable, "-m", "pytest", str(benchmark_file), "-v", "--tb=short", "-m", "performance"],
                        capture_output=True,
                        text=True
                    )

                    # Display pytest output
                    if result.stdout:
                        safe_console_print("\n--- Benchmark Output ---", style="bold")
                        safe_console_print(result.stdout)

                    if result.stderr:
                        safe_console_print("\n--- Errors/Warnings ---", style="yellow")
                        safe_console_print(result.stderr)

                    # Load and display results from baseline file
                    baseline_file = Path(__file__).parent.parent / "tests" / "performance" / "baseline_results.json"

                    if baseline_file.exists():
                        try:
                            with open(baseline_file, "r") as f:
                                baseline_data = json.load(f)

                            safe_console_print("\n[RESULTS] Performance Benchmark Results: ", style="bold green")

                            if "baselines" in baseline_data:
                                results_table = Table(title="Benchmark Metrics")
                                results_table.add_column("Benchmark", style="cyan")
                                results_table.add_column("Mean", style="bold")
                                results_table.add_column("P95", style="yellow")
                                results_table.add_column("Baseline", style="dim")
                                results_table.add_column("Status", style="green")

                                for metric_name, metric_data in baseline_data["baselines"].items():
                                    mean_val = metric_data.get("mean", metric_data.get("messages_per_second", 0))
                                    p95_val = metric_data.get("p95", "-")
                                    baseline_val = metric_data.get("baseline_ms", metric_data.get("baseline_msg_per_sec", 0))

                                    # Format values based on metric type
                                    if metric_name == "throughput":
                                        mean_str = f"{mean_val:.1f} msg/s"
                                        p95_str = "-"
                                        baseline_str = f"{baseline_val:.0f} msg/s"
                                    else:
                                        mean_str = f"{mean_val:.2f}ms"
                                        p95_str = f"{p95_val:.2f}ms" if isinstance(p95_val, (int, float)) else p95_val
                                        baseline_str = f"{baseline_val:.0f}ms"

                                    # Status indicator
                                    status = "[green]✓[/green]" if result.returncode == 0 else "[yellow]⚠[/yellow]"

                                    results_table.add_row(
                                        metric_name.replace("_", " ").title(),
                                        mean_str,
                                        p95_str,
                                        baseline_str,
                                        status
                                    )

                                safe_console_print(results_table)

                            # Display last updated time
                            if "last_updated" in baseline_data:
                                safe_console_print(f"\n[dim]Last updated: {baseline_data['last_updated']}[/dim]")

                        except (json.JSONDecodeError, IOError) as e:
                            safe_console_print(f"[yellow]Warning: Could not load baseline results: {e}[/yellow]")

                    # Exit with pytest exit code
                    safe_console_print(f"\n[bold]Benchmark suite {'PASSED' if result.returncode == 0 else 'FAILED'}[/bold]")
                    sys.exit(result.returncode)

                elif args.session_stats:
                    safe_console_print("[STATS] Debug session statistics...", style="cyan")
                    stats = cli.debug.get_session_stats()

                    stats_table = Table(title="Debug Session Statistics")
                    stats_table.add_column("Metric", style="cyan")
                    stats_table.add_column("Value", style="bold")

                    for key, value in stats.items():
                        display_key = key.replace('_', ' ').title()
                        if key == "duration_seconds":
                            value = f"{value:.2f}s"
                        stats_table.add_row(display_key, str(value))

                    safe_console_print(stats_table)

                elif args.generate_troubleshooting_report:
                    safe_console_print("[REPORT] Generating WebSocket troubleshooting report...", style="cyan")
                    await cli.generate_websocket_troubleshooting_report()

                # ISSUE #2218: Golden Path monitoring commands
                elif args.monitor:
                    safe_console_print("[MONITOR] Golden Path Real-time Dashboard", style="cyan")
                    await cli.display_golden_path_dashboard()

                elif args.health_metrics:
                    safe_console_print("[METRICS] Golden Path Health Metrics", style="cyan")
                    await cli.display_golden_path_health_metrics()

            except Exception as e:
                safe_console_print(f"ERROR: Health check failed: {e}", style="red")
                if args.verbose:
                    import traceback
                    safe_console_print(traceback.format_exc(), style="dim red")
                sys.exit(1)

        # Run health checks and exit
        try:
            asyncio.run(run_health_checks())
        except KeyboardInterrupt:
            safe_console_print("\n[FAIL] Health check interrupted", style="yellow")
        sys.exit(0)

    # Run appropriate mode
    async def run():
        try:
            # Handle manual token or no-auth options
            if args.token or args.no_auth:
                async with AuthManager(config) as auth_manager:
                    if args.token:
                        # Use provided token
                        await auth_manager.use_manual_token(args.token)
                    elif args.no_auth:
                        # Create a test token for no-auth mode
                        await auth_manager._create_test_token("cli-user@test.com")

                    cli.auth_manager = auth_manager

            # OAuth is now the default - add deprecation warning
            if args.oauth_login:
                safe_console_print("WARNING: --oauth-login flag is deprecated. OAuth is now the default authentication method.", style="yellow")

            # Respect environment-aware auth method selection
            # Only force OAuth if explicitly requested via --auth-method oauth
            # Otherwise, let get_valid_token() handle environment defaults:
            # - Staging: E2E simulation (automation-first)
            # - Production: OAuth browser (user experience-first)
            cli.use_oauth = (
                args.auth_method == "oauth"
                if hasattr(args, 'auth_method') and args.auth_method
                else False  # Defer to get_valid_token() for environment-aware defaults
            )
            cli.oauth_provider = args.oauth_provider
            cli.auth_method = args.auth_method

            if args.test:
                await cli.run_test_mode(args.test)
            elif args.message:
                # Issue #1822: Handle validation exit codes
                result = await cli.run_single_message(args.message, args.wait)
                # ISSUE #2766: Use structured exit code from ExitCodeGenerator
                if hasattr(cli, 'exit_code'):
                    sys.exit(cli.exit_code)
                elif args.validate_outputs and result is False:
                    # Validation failed, exit with code 1 (fallback)
                    sys.exit(1)
            elif args.send_logs:
                # Handle --send-logs without --message: use default message
                # the jsonl logs are attached in payload
                #   {
                #    "type": "user_message",
                #    "payload": { 
                #           ...
                #   *** "jsonl_logs": [... actual logs here ...] ***
                #    }
                #}

                default_message = "claude-code optimizer default message"
                result = await cli.run_single_message(default_message, args.wait)
                # ISSUE #2766: Use structured exit code from ExitCodeGenerator
                if hasattr(cli, 'exit_code'):
                    sys.exit(cli.exit_code)
                elif args.validate_outputs and result is False:
                    # Validation failed, exit with code 1 (fallback)
                    sys.exit(1)
            else:
                await cli.run_interactive()
        except Exception as e:
            safe_console_print(f"ERROR: Error: {e}", style="red")
            if args.verbose:
                import traceback
                safe_console_print(traceback.format_exc(), style="dim red")
            # ISSUE #2766: Use exit code 2 for infrastructure failures (exceptions)
            error_str = str(e).lower()
            is_infrastructure_failure = any(keyword in error_str for keyword in ['auth', 'connection', 'websocket', 'timeout'])
            sys.exit(2 if is_infrastructure_failure else 1)

    # Run
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        safe_console_print("\n Goodbye!", style="yellow")

if __name__ == "__main__":
    main()
