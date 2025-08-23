"""
Service availability checker for dev launcher.

Intelligently checks if local services are installed and available,
automatically falling back to shared services when needed.
"""

import logging
import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from dev_launcher.service_config import ResourceMode, ServicesConfiguration
from dev_launcher.unicode_utils import get_emoji, safe_print

logger = logging.getLogger(__name__)


class ServiceAvailabilityResult:
    """Result of service availability check."""
    
    def __init__(self, service_name: str, available: bool, 
                 recommended_mode: ResourceMode, reason: str = ""):
        self.service_name = service_name
        self.available = available
        self.recommended_mode = recommended_mode
        self.reason = reason
        

class ServiceAvailabilityChecker:
    """
    Checks availability of local services and recommends configuration.
    
    Provides intelligent fallback recommendations when local services
    aren't available, ensuring smooth cold start experience.
    """
    
    def __init__(self, use_emoji: bool = True):
        self.use_emoji = use_emoji
        self.check_cache: Dict[str, bool] = {}
    
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
            if redis_available:
                results['redis'] = ServiceAvailabilityResult(
                    'redis', True, ResourceMode.LOCAL, "Local Redis available"
                )
            else:
                results['redis'] = ServiceAvailabilityResult(
                    'redis', False, ResourceMode.SHARED, 
                    "Local Redis not available, falling back to shared Redis"
                )
        
        # Check ClickHouse
        if config.clickhouse.mode == ResourceMode.LOCAL:
            clickhouse_available = self._check_clickhouse_availability()
            if clickhouse_available:
                results['clickhouse'] = ServiceAvailabilityResult(
                    'clickhouse', True, ResourceMode.LOCAL, "Local ClickHouse available"
                )
            else:
                results['clickhouse'] = ServiceAvailabilityResult(
                    'clickhouse', False, ResourceMode.SHARED,
                    "Local ClickHouse not available, falling back to shared ClickHouse"
                )
        
        # Check PostgreSQL
        if config.postgres.mode == ResourceMode.LOCAL:
            postgres_available = self._check_postgres_availability()
            if postgres_available:
                results['postgres'] = ServiceAvailabilityResult(
                    'postgres', True, ResourceMode.LOCAL, "Local PostgreSQL available"
                )
            else:
                results['postgres'] = ServiceAvailabilityResult(
                    'postgres', False, ResourceMode.SHARED,
                    "Local PostgreSQL not available, falling back to shared PostgreSQL"
                )
        
        # Check API keys for LLM services
        if config.llm.mode == ResourceMode.SHARED:
            api_keys_valid = self._check_api_keys_availability()
            if api_keys_valid:
                results['llm'] = ServiceAvailabilityResult(
                    'llm', True, ResourceMode.SHARED, "API keys configured"
                )
            else:
                results['llm'] = ServiceAvailabilityResult(
                    'llm', False, ResourceMode.MOCK,
                    "API keys not configured, using mock LLM mode"
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
            if not result.available and result.recommended_mode != getattr(config, service_name).mode:
                # Apply the recommendation
                service = getattr(config, service_name)
                old_mode = service.mode
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
        
        # Check if psql is available
        available = self._check_command_availability(['psql', '--version'])
        
        # If psql is available, check if server is running
        if available:
            available = self._check_postgres_connection()
        
        self.check_cache['postgres'] = available
        return available
    
    def _check_postgres_connection(self) -> bool:
        """Check if PostgreSQL server is actually running and accessible."""
        try:
            # Try to connect to PostgreSQL server
            # Use connection parameters from config
            env = os.environ.copy()
            env['PGPASSWORD'] = ''  # Use empty password for dev setup
            
            result = subprocess.run(
                ['psql', '-h', 'localhost', '-p', '5433', '-U', 'postgres', '-d', 'postgres', '-c', 'SELECT 1;'], 
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
            key_value = os.environ.get(key_name, '')
            if key_value and not self._is_placeholder_key(key_value):
                valid_keys.append(key_name)
        
        # Return True if at least one valid API key is found
        return len(valid_keys) > 0
    
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
            ResourceMode.MOCK: get_emoji('test_tube')
        }
        
        safe_print(f"{service_emoji} {service_name.upper()}: {old_mode.value} → {new_mode.value} ({reason})")
    
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
                ResourceMode.MOCK: get_emoji('test_tube')
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
        print("   • Visit: https://console.anthropic.com/")
        print("   • Create API key and set: ANTHROPIC_API_KEY=your-key")
        print("\n2. OpenAI GPT:")
        print("   • Visit: https://platform.openai.com/api-keys")
        print("   • Create API key and set: OPENAI_API_KEY=your-key")
        print("\n3. Google Gemini:")
        print("   • Visit: https://aistudio.google.com/")
        print("   • Create API key and set: GEMINI_API_KEY=your-key")
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