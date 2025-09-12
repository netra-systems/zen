"""
Service availability checker for dev launcher.

Intelligently checks if local services are installed and available,
automatically falling back to shared services when needed.
"""

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from shared.isolated_environment import get_env

from dev_launcher.service_config import ResourceMode, ServicesConfiguration
from dev_launcher.unicode_utils import get_emoji, safe_print

logger = logging.getLogger(__name__)


class ServiceAvailabilityResult:
    """Result of service availability check."""
    
    def __init__(self, service_name: str, available: bool, 
                 recommended_mode: ResourceMode, reason: str = "",
                 docker_available: bool = False):
        self.service_name = service_name
        self.available = available
        self.recommended_mode = recommended_mode
        self.reason = reason
        self.docker_available = docker_available
        

class ServiceAvailabilityChecker:
    """
    Checks availability of local services and recommends configuration.
    
    Provides intelligent fallback recommendations when local services
    aren't available, ensuring smooth cold start experience.
    """
    
    def __init__(self, use_emoji: bool = True):
        self.use_emoji = use_emoji
        self.check_cache: Dict[str, bool] = {}
        self.docker_available = self._check_docker_availability()
        self._windows_postgres_paths = self._get_windows_postgres_paths()
    
    def check_all_services(self, config: ServicesConfiguration) -> Dict[str, ServiceAvailabilityResult]:
        """
        Check availability of all services and recommend modes.
        
        Returns:
            Dictionary mapping service names to availability results
        """
        results = {}
        
        # Check Redis
        if config.redis.mode == ResourceMode.LOCAL:
            redis_available = self._check_redis_availability()
            docker_redis = self.docker_available and self._check_redis_docker_option()
            
            if redis_available:
                results['redis'] = ServiceAvailabilityResult(
                    'redis', True, ResourceMode.LOCAL, "Local Redis available"
                )
            elif docker_redis:
                results['redis'] = ServiceAvailabilityResult(
                    'redis', False, ResourceMode.LOCAL, 
                    "Local Redis not installed, but Docker available - will start Redis container",
                    docker_available=True
                )
            else:
                # Check if shared Redis is actually accessible before falling back
                if self._check_shared_redis_accessibility():
                    results['redis'] = ServiceAvailabilityResult(
                        'redis', False, ResourceMode.SHARED, 
                        "Local Redis not available, falling back to shared Redis"
                    )
                else:
                    results['redis'] = ServiceAvailabilityResult(
                        'redis', False, ResourceMode.DISABLED, 
                        "Redis services unavailable - local/Docker not running and shared services not accessible"
                    )
        
        # Check ClickHouse
        if config.clickhouse.mode == ResourceMode.LOCAL:
            clickhouse_available = self._check_clickhouse_availability()
            docker_clickhouse = self.docker_available and self._check_clickhouse_docker_option()
            
            if clickhouse_available:
                results['clickhouse'] = ServiceAvailabilityResult(
                    'clickhouse', True, ResourceMode.LOCAL, "Local ClickHouse available"
                )
            elif docker_clickhouse:
                results['clickhouse'] = ServiceAvailabilityResult(
                    'clickhouse', False, ResourceMode.LOCAL,
                    "Local ClickHouse not installed, but Docker available - will start ClickHouse container",
                    docker_available=True
                )
            else:
                results['clickhouse'] = ServiceAvailabilityResult(
                    'clickhouse', False, ResourceMode.SHARED,
                    "Local ClickHouse not available, falling back to shared ClickHouse"
                )
        
        # Check PostgreSQL
        if config.postgres.mode == ResourceMode.LOCAL:
            postgres_available = self._check_postgres_availability()
            docker_postgres = self.docker_available and self._check_postgres_docker_option()
            
            if postgres_available:
                results['postgres'] = ServiceAvailabilityResult(
                    'postgres', True, ResourceMode.LOCAL, "Local PostgreSQL available"
                )
            elif docker_postgres:
                results['postgres'] = ServiceAvailabilityResult(
                    'postgres', False, ResourceMode.LOCAL,
                    "Local PostgreSQL not accessible, but Docker available - will start PostgreSQL container",
                    docker_available=True
                )
            else:
                # Check if shared PostgreSQL is actually accessible before falling back
                if self._check_shared_postgres_accessibility():
                    results['postgres'] = ServiceAvailabilityResult(
                        'postgres', False, ResourceMode.SHARED,
                        "Local PostgreSQL not available, falling back to shared PostgreSQL"
                    )
                else:
                    results['postgres'] = ServiceAvailabilityResult(
                        'postgres', False, ResourceMode.DISABLED,
                        "PostgreSQL services unavailable - local/Docker not running and shared services not accessible"
                    )
        
        # Check API keys for LLM services
        if config.llm.mode == ResourceMode.SHARED:
            api_keys_valid = self._check_api_keys_availability()
            if api_keys_valid:
                results['llm'] = ServiceAvailabilityResult(
                    'llm', True, ResourceMode.SHARED, "API keys configured"
                )
            else:
                # Keep LLM in shared mode even without API keys - just show warning
                # This ensures LLM shows as "On" (shared mode) instead of "Off" (disabled)
                results['llm'] = ServiceAvailabilityResult(
                    'llm', True, ResourceMode.SHARED,
                    "API keys not configured - LLM services will use mock mode for development"
                )
        
        return results
    
    def apply_recommendations(self, config: ServicesConfiguration, 
                            results: Dict[str, ServiceAvailabilityResult]) -> bool:
        """
        Apply recommended service modes based on availability results.
        
        Returns:
            True if any changes were made to the configuration
        """
        changes_made = False
        
        for service_name, result in results.items():
            if not result.available:
                service = getattr(config, service_name)
                old_mode = service.mode
                
                # Handle Docker fallback for local services
                if result.docker_available and result.recommended_mode == ResourceMode.LOCAL:
                    # Keep local mode but mark as Docker-based
                    service.mode = ResourceMode.LOCAL
                    # Add Docker flag to local_config (which is mutable)
                    service.local_config['docker'] = True
                    changes_made = True
                    self._print_fallback_message(service_name, old_mode, ResourceMode.LOCAL, 
                                                f"{result.reason} (Docker mode)")
                elif result.recommended_mode != old_mode:
                    # Apply the recommendation
                    service.mode = result.recommended_mode
                    changes_made = True
                    self._print_fallback_message(service_name, old_mode, result.recommended_mode, result.reason)
        
        return changes_made
    
    def _check_redis_availability(self) -> bool:
        """Check if Redis is available locally."""
        if 'redis' in self.check_cache:
            return self.check_cache['redis']
        
        # Check if redis-cli is available
        available = self._check_command_availability(['redis-cli', '--version'])
        
        # If redis-cli is available, check if Redis server is running
        if available:
            available = self._check_redis_connection()
        
        self.check_cache['redis'] = available
        return available
    
    def _check_redis_connection(self) -> bool:
        """Check if Redis server is actually running and accessible."""
        try:
            # Try to ping Redis server
            result = subprocess.run(
                ['redis-cli', 'ping'], 
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0 and 'PONG' in result.stdout.upper()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False
    
    def _check_clickhouse_availability(self) -> bool:
        """Check if ClickHouse is available locally."""
        if 'clickhouse' in self.check_cache:
            return self.check_cache['clickhouse']
        
        # Check if clickhouse-client is available
        available = self._check_command_availability(['clickhouse-client', '--version'])
        
        # If client is available, check if server is running
        if available:
            available = self._check_clickhouse_connection()
        
        self.check_cache['clickhouse'] = available
        return available
    
    def _check_clickhouse_connection(self) -> bool:
        """Check if ClickHouse server is actually running and accessible."""
        try:
            # Try to connect to ClickHouse server
            result = subprocess.run(
                ['clickhouse-client', '--query', 'SELECT 1'], 
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0 and '1' in result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False
    
    def _check_postgres_availability(self) -> bool:
        """Check if PostgreSQL is available locally."""
        if 'postgres' in self.check_cache:
            return self.check_cache['postgres']
        
        # Enhanced PostgreSQL detection for Windows
        available = False
        
        # First try standard PATH lookup
        if self._check_command_availability(['psql', '--version']):
            available = self._check_postgres_connection()
        
        # On Windows, try specific PostgreSQL installation paths
        if not available and platform.system() == 'Windows':
            for postgres_path in self._windows_postgres_paths:
                psql_path = postgres_path / 'psql.exe'
                if psql_path.exists():
                    try:
                        # Test if psql works
                        result = subprocess.run(
                            [str(psql_path), '--version'],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            # Add to PATH for this session
                            env_manager = get_env()
                            current_path = env_manager.get('PATH', '')
                            if str(postgres_path) not in current_path:
                                env_manager.set('PATH', f"{postgres_path};{current_path}", "service_availability_checker")
                            
                            # Check connection
                            available = self._check_postgres_connection_with_path(str(psql_path))
                            if available:
                                logger.info(f"Found PostgreSQL at: {postgres_path}")
                                break
                    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                        continue
        
        self.check_cache['postgres'] = available
        return available
    
    def _check_postgres_connection(self) -> bool:
        """Check if PostgreSQL server is actually running and accessible."""
        return self._check_postgres_connection_with_path('psql')
    
    def _check_postgres_connection_with_path(self, psql_path: str) -> bool:
        """Check PostgreSQL connection with specific psql path."""
        try:
            # Try to connect to PostgreSQL server
            # Use connection parameters from config
            isolated_env = get_env()
            env = isolated_env.get_subprocess_env()
            env['PGPASSWORD'] = ''  # Use empty password for dev setup
            
            result = subprocess.run(
                [psql_path, '-h', 'localhost', '-p', '5433', '-U', 'postgres', '-d', 'postgres', '-c', 'SELECT 1;'], 
                capture_output=True, text=True, timeout=5, env=env
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False
    
    def _check_api_keys_availability(self) -> bool:
        """Check if API keys are properly configured for LLM services."""
        # Check for common API key environment variables
        api_keys = [
            'ANTHROPIC_API_KEY',
            'OPENAI_API_KEY', 
            'GEMINI_API_KEY',
            'GOOGLE_API_KEY'
        ]
        
        valid_keys = []
        
        for key_name in api_keys:
            isolated_env = get_env()
            key_value = isolated_env.get(key_name, '')
            if key_value and not self._is_placeholder_key(key_value):
                valid_keys.append(key_name)
        
        # Return True if at least one valid API key is found
        return len(valid_keys) > 0
    
    def _check_docker_availability(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return False
            
            # Check if Docker daemon is running
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False
    
    def _check_redis_docker_option(self) -> bool:
        """Check if Redis can be started via Docker."""
        return True  # Docker is available, so Redis can be started
    
    def _check_clickhouse_docker_option(self) -> bool:
        """Check if ClickHouse can be started via Docker."""
        return True  # Docker is available, so ClickHouse can be started
    
    def _check_postgres_docker_option(self) -> bool:
        """Check if PostgreSQL can be started via Docker."""
        return True  # Docker is available, so PostgreSQL can be started
    
    def _get_windows_postgres_paths(self) -> List[Path]:
        """Get common PostgreSQL installation paths on Windows."""
        if platform.system() != 'Windows':
            return []
        
        paths = []
        
        # Common PostgreSQL installation directories
        base_paths = [
            Path('C:/Program Files/PostgreSQL'),
            Path('C:/Program Files (x86)/PostgreSQL'),
            Path(os.path.expanduser('~/AppData/Local/Programs/PostgreSQL')),
        ]
        
        for base_path in base_paths:
            if base_path.exists():
                try:
                    # Look for version directories (e.g., 12, 13, 14, 15, 16, 17)
                    for version_dir in base_path.iterdir():
                        if version_dir.is_dir():
                            bin_path = version_dir / 'bin'
                            if bin_path.exists():
                                paths.append(bin_path)
                except (PermissionError, FileNotFoundError, OSError):
                    # Skip paths we can't access
                    continue
        
        return paths
    
    def _is_placeholder_key(self, api_key: str) -> bool:
        """Check if an API key is a placeholder value."""
        placeholder_patterns = [
            'your-api-key',
            'placeholder', 
            'example',
            'dummy',
            'test',
            'fake',
            'sk-xxx',
            'sk-placeholder'
        ]
        
        api_key_lower = api_key.lower()
        return any(pattern in api_key_lower for pattern in placeholder_patterns) or len(api_key.strip()) < 10
    
    def _check_command_availability(self, command: List[str]) -> bool:
        """Check if a command is available in the system PATH."""
        try:
            result = subprocess.run(
                command, 
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False
    
    def _check_shared_redis_accessibility(self) -> bool:
        """Check if shared Redis service is actually accessible."""
        try:
            import socket
            # Try to connect to the shared Redis host with a short timeout
            # This is from the shared_config in service_config.py
            host = "redis-17593.c305.ap-south-1-1.ec2.redns.redis-cloud.com"
            port = 17593
            
            with socket.create_connection((host, port), timeout=2):
                return True
        except (socket.timeout, socket.error, OSError, ImportError):
            return False
    
    def _check_shared_postgres_accessibility(self) -> bool:
        """Check if shared PostgreSQL service is actually accessible."""
        try:
            import socket
            # Check if we can resolve DNS and connect to a known shared PostgreSQL service
            # Using Google's public DNS to test network connectivity
            with socket.create_connection(("8.8.8.8", 53), timeout=2):
                # If we can reach DNS, we likely have internet access for shared services
                # But for now, let's be conservative and return False to use disabled mode
                # This prevents hanging on unreachable cloud services
                return False
        except (socket.timeout, socket.error, OSError, ImportError):
            return False
    
    def _print_fallback_message(self, service_name: str, old_mode: ResourceMode, 
                               new_mode: ResourceMode, reason: str):
        """Print a user-friendly fallback message."""
        service_emoji = {
            'redis': get_emoji('database'),
            'clickhouse': get_emoji('chart'),
            'postgres': get_emoji('database'),
            'llm': get_emoji('robot')
        }.get(service_name, get_emoji('gear'))
        
        mode_emoji = {
            ResourceMode.LOCAL: get_emoji('computer'),
            ResourceMode.SHARED: get_emoji('cloud'),
            ResourceMode.DOCKER: get_emoji('test_tube'),
            ResourceMode.DISABLED: get_emoji('x')
        }
        
        safe_print(f"{service_emoji} {service_name.upper()}: {old_mode.value}  ->  {new_mode.value} ({reason})")
    
    def print_availability_summary(self, results: Dict[str, ServiceAvailabilityResult]):
        """Print a summary of service availability checks."""
        if not results:
            return
        
        print("\n" + "="*60)
        safe_print(f"{get_emoji('magnifying_glass')} Service Availability Check Results")
        print("="*60)
        
        for service_name, result in results.items():
            status_emoji = get_emoji('check') if result.available else get_emoji('x')
            mode_emoji = {
                ResourceMode.LOCAL: get_emoji('computer'),
                ResourceMode.SHARED: get_emoji('cloud'),
                ResourceMode.DOCKER: get_emoji('test_tube'),
                ResourceMode.DISABLED: get_emoji('x')
            }.get(result.recommended_mode, get_emoji('gear'))
            
            safe_print(f"  {status_emoji} {service_name.upper():12} : {mode_emoji} {result.recommended_mode.value:8} - {result.reason}")
        
        print("="*60)
    
    def print_api_key_guidance(self):
        """Print guidance for setting up API keys."""
        print("\n" + "="*60)
        safe_print(f"{get_emoji('key')} API Key Setup Guidance")
        print("="*60)
        print("\nTo enable AI features, set up at least one API key:")
        print("\n1. Anthropic Claude (Recommended):")
        print("   [U+2022] Visit: https://console.anthropic.com/")
        print("   [U+2022] Create API key and set: ANTHROPIC_API_KEY=your-key")
        print("\n2. OpenAI GPT:")
        print("   [U+2022] Visit: https://platform.openai.com/api-keys")
        print("   [U+2022] Create API key and set: OPENAI_API_KEY=your-key")
        print("\n3. Google Gemini:")
        print("   [U+2022] Visit: https://aistudio.google.com/")
        print("   [U+2022] Create API key and set: GEMINI_API_KEY=your-key")
        print("\nExample .env file entry:")
        print("ANTHROPIC_API_KEY=sk-ant-api03-...")
        print("\nWithout API keys, the platform will run in mock mode with limited AI functionality.")
        print("="*60)


def check_and_configure_services(config: ServicesConfiguration, 
                                use_emoji: bool = True, 
                                interactive: bool = True) -> Tuple[ServicesConfiguration, List[str]]:
    """
    Check service availability and configure optimal service modes.
    
    Args:
        config: Current service configuration
        use_emoji: Whether to use emoji in output
        interactive: Whether to show interactive prompts
    
    Returns:
        Tuple of (updated config, list of warnings)
    """
    checker = ServiceAvailabilityChecker(use_emoji)
    results = checker.check_all_services(config)
    warnings = []
    
    # Apply recommendations automatically
    changes_made = checker.apply_recommendations(config, results)
    
    # Start Docker services if needed
    docker_warnings = _start_docker_services_if_needed(config, results)
    warnings.extend(docker_warnings)
    
    if changes_made and interactive:
        checker.print_availability_summary(results)
    
    # Check if we need to show API key guidance
    llm_result = results.get('llm')
    if llm_result and not llm_result.available and interactive:
        checker.print_api_key_guidance()
        warnings.append("API keys not configured - running in mock LLM mode")
    
    # Generate warnings for services that fell back
    for service_name, result in results.items():
        if not result.available:
            warnings.append(f"{service_name.upper()} service using {result.recommended_mode.value} mode: {result.reason}")
    
    return config, warnings


def _start_docker_services_if_needed(config: ServicesConfiguration, 
                                   results: Dict[str, ServiceAvailabilityResult]) -> List[str]:
    """Start Docker services if they are configured to use Docker fallback - SSOT UnifiedDockerManager."""
    warnings = []
    
    # Check if any services need Docker containers started
    docker_services_needed = []
    for service_name, result in results.items():
        if result.docker_available and not result.available:
            service_config = getattr(config, service_name, None)
            if service_config and service_config.get_config().get('docker', False):
                docker_services_needed.append(service_name)
    
    if docker_services_needed:
        try:
            # Import SSOT Docker management
            from test_framework.unified_docker_manager import UnifiedDockerManager
            import asyncio
            
            # Use UnifiedDockerManager for all Docker operations
            docker_manager = UnifiedDockerManager()
            
            # Start services using async manager
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                success = loop.run_until_complete(
                    docker_manager.start_services_smart(docker_services_needed, wait_healthy=True)
                )
                
                if success:
                    for service_name in docker_services_needed:
                        warnings.append(f" PASS:  Started {service_name} Docker container via UnifiedDockerManager")
                else:
                    warnings.append(f" FAIL:  Failed to start some Docker services: {docker_services_needed}")
                    
            finally:
                loop.close()
                
        except ImportError as e:
            warnings.append(f" FAIL:  Could not import UnifiedDockerManager: {e}")
            # Fallback to legacy Docker management
            try:
                from dev_launcher.docker_services import DockerServiceManager
                docker_manager = DockerServiceManager()
                
                for service_name in docker_services_needed:
                    if service_name == 'redis':
                        success, message = docker_manager.start_redis_container()
                        if success:
                            warnings.append(f" PASS:  Started Redis Docker container (legacy)")
                        else:
                            warnings.append(f" FAIL:  Failed to start Redis Docker container: {message}")
                    
                    elif service_name == 'clickhouse':
                        success, message = docker_manager.start_clickhouse_container()
                        if success:
                            warnings.append(f" PASS:  Started ClickHouse Docker container (legacy)")
                        else:
                            warnings.append(f" FAIL:  Failed to start ClickHouse Docker container: {message}")
                    
                    elif service_name == 'postgres':
                        success, message = docker_manager.start_postgres_container()
                        if success:
                            warnings.append(f" PASS:  Started PostgreSQL Docker container (legacy)")
                        else:
                            warnings.append(f" FAIL:  Failed to start PostgreSQL Docker container: {message}")
            
            except ImportError:
                warnings.append(" WARNING: [U+FE0F]  Docker services module not available")
        except Exception as e:
            warnings.append(f" WARNING: [U+FE0F]  Error starting Docker services: {str(e)}")
    
    return warnings