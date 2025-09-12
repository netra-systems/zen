"""
Summary display functionality for development launcher.
"""

import logging

from dev_launcher.utils import print_with_emoji

logger = logging.getLogger(__name__)


class SummaryDisplay:
    """
    Handles display of startup summaries and status information.
    
    Manages the display of success summaries, backend/frontend
    status, and commands information.
    """
    
    def __init__(self, config, service_discovery, use_emoji: bool = True):
        """Initialize summary display."""
        self.config = config
        self.service_discovery = service_discovery
        self.use_emoji = use_emoji
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def show_success_summary(self):
        """Show success summary."""
        print("\n" + "=" * 60)
        self._print("[U+2728]", "SUCCESS", "Development environment is running!")
        print("=" * 60)
        self._show_auth_summary()
        self._show_backend_summary()
        self._show_frontend_summary()
        self._show_commands_info()
    
    def _show_auth_summary(self):
        """Show auth service summary."""
        auth_info = self.service_discovery.read_auth_info()
        if auth_info:
            self._print("[U+1F510]", "AUTH", "")
            print(f"  URL: {auth_info['url']}")
            print(f"  Health: {auth_info['health']}")
            print(f"  Docs: {auth_info.get('docs', auth_info['url'] + '/docs')}")
            print(f"  Logs: Real-time streaming (cyan)")
    
    def _show_backend_summary(self):
        """Show backend summary."""
        backend_info = self.service_discovery.read_backend_info()
        if backend_info:
            self._print("[U+1F527]", "BACKEND", "")
            print(f"  API: {backend_info['api_url']}")
            print(f"  WebSocket: {backend_info['ws_url']}")
            print(f"  Logs: Real-time streaming (cyan)")
    
    def _show_frontend_summary(self):
        """Show frontend summary."""
        self._print("[U+1F310]", "FRONTEND", "")
        print(f"  URL: http://localhost:{self.config.frontend_port}")
        print(f"  Logs: Real-time streaming (magenta)")
    
    def _show_commands_info(self):
        """Show commands information."""
        print("\n[COMMANDS]:")
        print("  Press Ctrl+C to stop all services")
        print("  Logs are streamed in real-time with color coding")
        print(f"  Log files saved in: {self.config.log_dir}")
        print("-" * 60 + "\n")