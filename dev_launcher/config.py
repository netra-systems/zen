"""
Configuration management for the dev launcher.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from netra_backend.app.core.environment_constants import (
    Environment,
    EnvironmentVariables,
    get_current_environment,
    get_current_project_id,
)
from netra_backend.app.core.network_constants import HostConstants, ServicePorts

logger = logging.getLogger(__name__)

@dataclass
class LauncherConfig:
    """Configuration for the development launcher."""
    
    # Port configuration - FIX: Force dynamic ports by default to avoid conflicts
    backend_port: Optional[int] = None
    frontend_port: int = ServicePorts.FRONTEND_DEFAULT  # Will be dynamically allocated if conflicts
    dynamic_ports: bool = True  # Default to dynamic allocation
    enable_port_conflict_resolution: bool = True  # Auto-resolve port conflicts
    
    # Reload configuration (uses native reload)
    backend_reload: bool = False  # Default to no reload for performance
    frontend_reload: bool = True  # Next.js always has reload
    auth_reload: bool = False  # Auth service reload for performance
    
    # Secret management
    load_secrets: bool = True
    project_id: Optional[str] = None
    
    # UI configuration
    no_browser: bool = False
    verbose: bool = False
    non_interactive: bool = False  # Non-interactive mode for CI/automation
    
    # Performance optimizations
    parallel_startup: bool = True  # Enable parallel service startup by default
    
    # Build configuration
    use_turbopack: bool = False
    
    # Startup mode configuration
    startup_mode: str = "minimal"  # minimal, standard, or verbose
    
    # Visibility control flags
    verbose_background: bool = False  # Show background task logs
    verbose_tables: bool = False  # Show table check details
    
    # Phase 6 Integration: New optimization flags
    silent_mode: bool = False  # Silent logging with minimal output
    no_cache: bool = False  # Bypass all caching
    profile_startup: bool = False  # Show detailed performance metrics
    
    # Boundary monitoring configuration
    watch_boundaries: bool = False  # Real-time boundary monitoring
    boundary_check_interval: int = 30  # Check every 30 seconds
    fail_on_boundary_violations: bool = False  # Stop dev server on violations
    show_boundary_warnings: bool = True  # Show boundary warning messages
    
    # Environment configuration
    production: bool = False  # Default to development mode
    
    # Paths
    project_root: Path = field(default_factory=lambda: Path.cwd())
    log_dir: Optional[Path] = None
    
    # Environment variables
    env_overrides: Dict[str, str] = field(default_factory=dict)
    
    # Internal fields (not user-configurable)
    _services_config: Optional[Any] = field(default=None, init=False)
    _use_emoji: bool = field(default=True, init=False)
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.log_dir is None:
            self.log_dir = self.project_root / "logs"
        
        # Set project ID from environment if not provided
        if self.project_id is None:
            # Use centralized project ID determination
            self.project_id = get_current_project_id()
        
        # Validate configuration
        self._validate()
        
        # Initialize services config
        self._load_service_config()
    
    def _validate(self):
        """Validate configuration values."""
        # FIX: Enhanced port validation with conflict detection
        if self.backend_port and not (ServicePorts.DYNAMIC_PORT_MIN <= self.backend_port <= ServicePorts.DYNAMIC_PORT_MAX):
            if self.enable_port_conflict_resolution:
                logger.warning(f"Invalid backend port {self.backend_port}, will use dynamic allocation")
                self.backend_port = None
            else:
                raise ValueError(f"Invalid backend port: {self.backend_port}. Must be between {ServicePorts.DYNAMIC_PORT_MIN} and {ServicePorts.DYNAMIC_PORT_MAX}.")
        
        if not (1 <= self.frontend_port <= 65535):
            if self.enable_port_conflict_resolution:
                logger.warning(f"Invalid frontend port {self.frontend_port}, will use default")
                self.frontend_port = ServicePorts.FRONTEND_DEFAULT
            else:
                raise ValueError(f"Invalid frontend port: {self.frontend_port}. Must be between 1 and 65535.")
        
        # FIX: Check for port conflicts at validation time
        if self.enable_port_conflict_resolution:
            self._resolve_port_conflicts()
        
        # Validate project root exists
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")
        
        # Check for required directories - updated to correct path
        backend_dir = self.project_root / "netra_backend" / "app"
        frontend_dir = self.project_root / "frontend"
        
        if not backend_dir.exists():
            raise ValueError(f"Backend directory not found: {backend_dir}\nAre you running from the correct directory?")
        
        if not frontend_dir.exists():
            raise ValueError(f"Frontend directory not found: {frontend_dir}\nAre you running from the correct directory?")
    
    def _resolve_port_conflicts(self):
        """FIX: Resolve port conflicts using service discovery system."""
        try:
            from dev_launcher.service_discovery_system import service_discovery
            
            # Load existing service registrations
            service_discovery.load_discovery_file()
            
            # Check backend port
            if self.backend_port and not service_discovery.is_port_available(self.backend_port):
                logger.warning(f"Backend port {self.backend_port} is in use, enabling dynamic allocation")
                self.backend_port = None
                self.dynamic_ports = True
            
            # Check frontend port
            if not service_discovery.is_port_available(self.frontend_port):
                logger.warning(f"Frontend port {self.frontend_port} is in use, will find alternative")
                # Find alternative port using service discovery
                alt_port = service_discovery.find_available_port(
                    preferred_port=None, 
                    port_range=(3001, 3010)
                )
                if alt_port:
                    logger.info(f"Using alternative frontend port {alt_port}")
                    self.frontend_port = alt_port
                else:
                    logger.warning("No alternative frontend ports available, will use dynamic allocation")
                    self.dynamic_ports = True
                    
        except ImportError:
            logger.warning("Service discovery system not available, falling back to basic port checking")
            # Fallback to original implementation
            import socket
            
            def is_port_available(port):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(1)
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        sock.bind(('127.0.0.1', port))
                        return True
                except OSError:
                    return False
            
            if self.backend_port and not is_port_available(self.backend_port):
                self.backend_port = None
                self.dynamic_ports = True
            
            if not is_port_available(self.frontend_port):
                for alt_port in range(3001, 3010):
                    if is_port_available(alt_port):
                        self.frontend_port = alt_port
                        break
                else:
                    self.dynamic_ports = True
    
    @classmethod
    def from_args(cls, args) -> "LauncherConfig":
        """Create configuration from command-line arguments."""
        # Handle port configuration - default to dynamic ports unless explicitly disabled
        dynamic_ports = True  # Default to dynamic
        if hasattr(args, 'static') and args.static:
            dynamic_ports = False
        elif hasattr(args, 'dynamic'):
            dynamic_ports = args.dynamic
        
        # Handle reload flags
        if hasattr(args, 'dev') and args.dev:
            # Development mode: enable all hot reload
            backend_reload = True
            frontend_reload = True
            auth_reload = True
        elif hasattr(args, 'backend_reload') and args.backend_reload:
            # Explicit backend reload
            backend_reload = True
            frontend_reload = True
            auth_reload = False
        elif hasattr(args, 'no_reload') and args.no_reload:
            # No reload at all - disable for all services
            backend_reload = False
            frontend_reload = False  # Disable frontend reload for maximum performance
            auth_reload = False
        else:
            # Default: no backend reload for performance
            backend_reload = False
            frontend_reload = True
            auth_reload = False
        
        # Default to loading secrets unless --no-secrets is specified
        load_secrets = not args.no_secrets if hasattr(args, 'no_secrets') else True
        
        # Handle startup mode
        startup_mode = "minimal"  # Default
        if hasattr(args, 'verbose') and args.verbose:
            startup_mode = "verbose"
        elif hasattr(args, 'standard') and args.standard:
            startup_mode = "standard"
        elif hasattr(args, 'minimal') and args.minimal:
            startup_mode = "minimal"
        elif hasattr(args, 'mode'):
            startup_mode = args.mode
        
        # Handle visibility control flags
        verbose_background = hasattr(args, 'verbose_background') and args.verbose_background
        verbose_tables = hasattr(args, 'verbose_tables') and args.verbose_tables
        
        # Handle new optimization flags
        silent_mode = hasattr(args, 'silent') and args.silent
        no_cache = hasattr(args, 'no_cache') and args.no_cache
        profile_startup = hasattr(args, 'profile') and args.profile
        
        return cls(
            backend_port=args.backend_port,
            frontend_port=args.frontend_port,
            dynamic_ports=dynamic_ports,
            verbose=args.verbose,
            backend_reload=backend_reload,
            frontend_reload=frontend_reload,
            auth_reload=auth_reload,
            load_secrets=load_secrets,
            project_id=args.project_id if hasattr(args, 'project_id') else None,
            no_browser=args.no_browser,
            non_interactive=args.non_interactive if hasattr(args, 'non_interactive') else False,
            use_turbopack=not args.no_turbopack if hasattr(args, 'no_turbopack') else False,
            parallel_startup=not args.no_parallel if hasattr(args, 'no_parallel') else True,
            startup_mode=startup_mode,
            verbose_background=verbose_background,
            verbose_tables=verbose_tables,
            silent_mode=silent_mode,
            no_cache=no_cache,
            profile_startup=profile_startup,
            project_root=find_project_root()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "backend_port": self.backend_port,
            "frontend_port": self.frontend_port,
            "dynamic_ports": self.dynamic_ports,
            "backend_reload": self.backend_reload,
            "frontend_reload": self.frontend_reload,
            "auth_reload": self.auth_reload,
            "load_secrets": self.load_secrets,
            "project_id": self.project_id,
            "no_browser": self.no_browser,
            "verbose": self.verbose,
            "non_interactive": self.non_interactive,
            "use_turbopack": self.use_turbopack,
            "project_root": str(self.project_root),
            "log_dir": str(self.log_dir),
        }
    
    # ============================================================================
    # Configuration Management Methods (merged from ConfigManager)
    # ============================================================================
    
    def set_emoji_support(self, use_emoji: bool):
        """Set emoji support for display methods."""
        self._use_emoji = use_emoji
    
    @property
    def services_config(self):
        """Get services configuration."""
        return self._services_config
    
    def _load_service_config(self):
        """Load service configuration."""
        try:
            import sys

            from dev_launcher.service_config import load_or_create_config
            interactive = sys.stdin.isatty() and not self.non_interactive
            self._services_config = load_or_create_config(interactive=interactive)
        except ImportError:
            # Handle case where service_config is not available
            logger.warning("Service configuration not available")
            self._services_config = None
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        try:
            from dev_launcher.utils import print_with_emoji
            print_with_emoji(emoji, text, message, self._use_emoji)
        except ImportError:
            # Fallback for when utils are not available
            if self._use_emoji:
                print(f"{emoji} {text}: {message}")
            else:
                print(f"• {text}: {message}")
    
    def log_verbose_config(self):
        """Log verbose configuration information."""
        if not self.verbose:
            return
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Log directory: {self.log_dir}")
        self._log_service_config()
    
    def _log_service_config(self):
        """Log service configuration details."""
        if not self._services_config:
            return
        logger.info("Service configuration loaded:")
        self._log_redis_config()
        self._log_clickhouse_config()
        self._log_postgres_config()
        self._log_llm_config()
    
    def _log_redis_config(self):
        """Log Redis configuration."""
        if self._services_config:
            logger.info(f"  Redis: {self._services_config.redis.mode.value}")
    
    def _log_clickhouse_config(self):
        """Log ClickHouse configuration."""
        if self._services_config:
            logger.info(f"  ClickHouse: {self._services_config.clickhouse.mode.value}")
    
    def _log_postgres_config(self):
        """Log PostgreSQL configuration."""
        if self._services_config:
            logger.info(f"  PostgreSQL: {self._services_config.postgres.mode.value}")
    
    def _log_llm_config(self):
        """Log LLM configuration."""
        if self._services_config:
            logger.info(f"  LLM: {self._services_config.llm.mode.value}")
    
    def show_configuration(self):
        """Show configuration summary."""
        self._print("📝", "CONFIG", "Configuration:")
        self._print_service_modes()
        self._print_config_options()
    
    def _print_service_modes(self):
        """Print service mode configuration."""
        if not self._services_config:
            return
            
        try:
            from dev_launcher.service_config import ResourceMode
            
            # Print header
            self._print("🔧", "SERVICES", "Service Modes:")
            
            # Map modes to descriptive text and emojis
            mode_info = {
                ResourceMode.LOCAL: ("Local", "💻"),
                ResourceMode.SHARED: ("Cloud", "☁️"),
                ResourceMode.MOCK: ("Mock", "🧪"),
                ResourceMode.DISABLED: ("Off", "❌")
            }
            
            # Display each service mode
            services = [
                ("Redis", self._services_config.redis),
                ("ClickHouse", self._services_config.clickhouse),
                ("PostgreSQL", self._services_config.postgres),
                ("LLM", self._services_config.llm)
            ]
            
            for name, service in services:
                desc, emoji = mode_info.get(service.mode, (service.mode.value, "?"))
                config = service.get_config()
                
                # Build detail string based on mode
                detail = ""
                if service.mode == ResourceMode.LOCAL:
                    if 'host' in config and 'port' in config:
                        detail = f" ({config['host']}:{config['port']})"
                elif service.mode == ResourceMode.SHARED:
                    if 'host' in config:
                        host = config['host']
                        # Shorten long cloud URLs
                        if len(host) > 25:
                            detail = f" ({host[:22]}...)"
                        else:
                            detail = f" ({host})"
                
                if self._use_emoji:
                    print(f"  {emoji} {name:12}: {desc:6}{detail}")
                else:
                    print(f"  • {name:12}: {desc:6}{detail}")
            
            print()  # Add spacing after service modes
        except ImportError:
            logger.warning("Service configuration display not available")
    
    def _print_config_options(self):
        """Print configuration options."""
        self._print_port_and_reload_configs()
        self._print_feature_configs()
        print()
    
    def _print_port_and_reload_configs(self):
        """Print port and reload configuration options."""
        self._print_dynamic_ports_config()
        self._print_backend_reload_config()
        self._print_frontend_reload_config()
        self._print_logging_config()
    
    def _print_dynamic_ports_config(self):
        """Print dynamic ports configuration."""
        print(f"  • Dynamic ports: {'YES' if self.dynamic_ports else 'NO'}")
    
    def _print_backend_reload_config(self):
        """Print backend reload configuration."""
        reload_text = 'YES (uvicorn native)' if self.backend_reload else 'NO'
        print(f"  • Backend hot reload: {reload_text}")
    
    def _print_frontend_reload_config(self):
        """Print frontend reload configuration."""
        print(f"  • Frontend hot reload: YES (Next.js native)")
    
    def _print_logging_config(self):
        """Print logging configuration."""
        print(f"  • Real-time logging: YES")
    
    def _print_feature_configs(self):
        """Print feature configuration options."""
        self._print_turbopack_config()
        self._print_secrets_config()
        self._print_verbose_config()
    
    def _print_turbopack_config(self):
        """Print Turbopack configuration."""
        print(f"  • Turbopack: {'YES' if self.use_turbopack else 'NO'}")
    
    def _print_secrets_config(self):
        """Print secrets configuration."""
        print(f"  • Secret loading: {'YES' if self.load_secrets else 'NO'}")
    
    def _print_verbose_config(self):
        """Print verbose configuration."""
        print(f"  • Verbose output: {'YES' if self.verbose else 'NO'}")
    
    def show_env_var_debug_info(self):
        """Show debug information about environment variables."""
        print("\n" + "=" * 60)
        print("🔍 ENVIRONMENT VARIABLE DEBUG INFO")
        print("=" * 60)
        self._show_env_files_status()
        self._show_key_env_vars()
        print("=" * 60)
    
    def _show_env_files_status(self):
        """Show environment files status."""
        env_files = self._get_env_files_list()
        print("\n📁 Environment Files Status:")
        for filename, description in env_files:
            self._show_env_file_status(filename, description)
    
    def _get_env_files_list(self) -> list:
        """Get list of environment files."""
        return [
            (".env", "Base configuration"),
            (".env.development", "Development overrides"),
            (".env.development.local", "Terraform-generated"),
        ]
    
    def _show_env_file_status(self, filename: str, description: str):
        """Show individual environment file status."""
        filepath = self.project_root / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✅ {filename:25} - {description} ({size} bytes)")
        else:
            print(f"  ❌ {filename:25} - {description} (not found)")
    
    def _show_key_env_vars(self):
        """Show key environment variables."""
        print("\n🔑 Key Environment Variables (current state):")
        important_vars = self._get_important_env_vars()
        for var in important_vars:
            self._show_env_var_status(var)
    
    def _get_important_env_vars(self) -> list:
        """Get list of important environment variables."""
        return [
            "GOOGLE_CLIENT_ID", "GEMINI_API_KEY", "CLICKHOUSE_HOST",
            "DATABASE_URL", "REDIS_HOST", "JWT_SECRET_KEY", "ENVIRONMENT"
        ]
    
    def _show_env_var_status(self, var: str):
        """Show individual environment variable status."""
        value = os.environ.get(var)
        if value:
            masked = self._mask_env_var_value(value)
            print(f"  {var:30} = {masked}")
        else:
            print(f"  {var:30} = <not set>")
    
    def _mask_env_var_value(self, value: str) -> str:
        """Mask environment variable value."""
        if len(value) > 10:
            return value[:3] + "***" + value[-3:]
        return "***"


def find_project_root() -> Path:
    """Find the project root directory robustly."""
    current_file = Path(__file__).resolve()
    
    # Check if we're in dev_launcher directory
    if current_file.parent.name == 'dev_launcher':
        return current_file.parent.parent
    
    # Try to find project root by looking for key files/dirs
    for parent in current_file.parents:
        if (parent / 'frontend').exists() or (parent / 'app').exists() or (parent / 'requirements.txt').exists():
            return parent
    
    # Fallback to current working directory
    return Path.cwd()


def resolve_path(*parts, root: Optional[Path] = None, required: bool = False) -> Optional[Path]:
    """
    Resolve a path robustly, checking multiple locations.
    
    Args:
        *parts: Path components to join
        root: Root directory to search from
        required: Whether to raise an error if not found
    
    Returns:
        Resolved path or None if not found
    """
    if root is None:
        root = find_project_root()
    
    # Default search directories
    search_dirs = [
        Path.cwd(),  # Current working directory
        root,  # Project root
        Path(__file__).parent,  # Current directory
        Path(__file__).parent.parent,  # Parent directory
    ]
    
    # Try each search directory
    for base_dir in search_dirs:
        path = base_dir / Path(*parts)
        if path.exists():
            return path.resolve()
    
    # If required and not found, raise error
    if required:
        searched = ', '.join(str(d) for d in search_dirs)
        raise FileNotFoundError(f"Could not find {'/'.join(parts)} in any of: {searched}")
    
    # Return the path relative to root as fallback
    return root / Path(*parts)