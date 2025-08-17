"""
Service startup coordination for development launcher.
"""

import logging
from typing import Optional, Tuple
import subprocess

from dev_launcher.config import LauncherConfig
from dev_launcher.log_streamer import LogStreamer, LogManager
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.backend_starter import BackendStarter
from dev_launcher.frontend_starter import FrontendStarter

logger = logging.getLogger(__name__)


class ServiceStartupCoordinator:
    """
    Coordinates startup of development services.
    
    Lightweight coordinator that delegates to specialized
    backend and frontend starter classes.
    """
    
    def __init__(self, config: LauncherConfig, services_config, 
                 log_manager: LogManager, service_discovery: ServiceDiscovery,
                 use_emoji: bool = True):
        """Initialize service startup coordinator."""
        self.config = config
        self.services_config = services_config
        self.log_manager = log_manager
        self.service_discovery = service_discovery
        self.use_emoji = use_emoji
        self._setup_starters()
    
    def _setup_starters(self):
        """Setup backend and frontend starters."""
        self.backend_starter = BackendStarter(
            self.config, self.services_config,
            self.log_manager, self.service_discovery,
            self.use_emoji
        )
        self.frontend_starter = FrontendStarter(
            self.config, self.services_config,
            self.log_manager, self.service_discovery,
            self.use_emoji
        )
    
    @property
    def backend_health_info(self):
        """Get backend health info."""
        return self.backend_starter.backend_health_info
    
    @property
    def frontend_health_info(self):
        """Get frontend health info."""
        return self.frontend_starter.frontend_health_info
    
    def start_backend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the backend server."""
        return self.backend_starter.start_backend()
    
    def start_frontend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the frontend server."""
        return self.frontend_starter.start_frontend()