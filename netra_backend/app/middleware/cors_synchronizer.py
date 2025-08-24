"""
CORS Synchronizer

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development velocity & system stability
- Value Impact: Ensures consistent CORS configuration across all services
- Strategic Impact: Prevents CORS mismatches that block frontend/backend communication

Implements CORS configuration synchronization and validation across services.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Pattern
from urllib.parse import urlparse

import httpx
from netra_backend.app.logging_config import central_logger
from netra_backend.app.config import get_config

logger = central_logger.get_logger(__name__)


@dataclass
class CORSConfig:
    """CORS configuration for a service."""
    service_name: str
    allowed_origins: List[str] = field(default_factory=list)
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allowed_headers: List[str] = field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    max_age: int = 86400  # 24 hours
    expose_headers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'service_name': self.service_name,
            'allowed_origins': self.allowed_origins,
            'allowed_methods': self.allowed_methods,
            'allowed_headers': self.allowed_headers,
            'allow_credentials': self.allow_credentials,
            'max_age': self.max_age,
            'expose_headers': self.expose_headers
        }


@dataclass
class SynchronizerConfig:
    """Configuration for CORS synchronizer."""
    sync_interval_seconds: int = 300  # 5 minutes
    validation_timeout_seconds: int = 10
    origin_pattern_validation: bool = True
    dynamic_origin_support: bool = True
    development_mode: bool = False


class CORSSynchronizer:
    """Synchronizes CORS configurations across services."""
    
    def __init__(self, config: Optional[SynchronizerConfig] = None):
        """Initialize CORS synchronizer."""
        self.config = config or SynchronizerConfig()
        
        # Service CORS configurations
        self.service_configs: Dict[str, CORSConfig] = {}
        self.origin_patterns: List[Pattern] = []
        
        # HTTP client for validation
        self.http_client = httpx.AsyncClient(timeout=10.0)
        
        # Sync task
        self._sync_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Statistics
        self.stats = {
            'configs_synchronized': 0,
            'validation_checks': 0,
            'validation_failures': 0,
            'origin_mismatches': 0,
            'dynamic_origins_resolved': 0
        }
        
        # Initialize configurations
        self._initialize_configs()
    
    def _initialize_configs(self) -> None:
        """Initialize CORS configurations from environment."""
        app_config = get_config()
        
        # Determine environment and base URLs
        environment = getattr(app_config, 'environment', 'development')
        self.config.development_mode = environment == 'development'
        
        # Base CORS configuration
        base_origins = self._get_base_origins(app_config, environment)
        
        # Backend service CORS
        self.service_configs['backend'] = CORSConfig(
            service_name='backend',
            allowed_origins=base_origins.copy(),
            allowed_headers=['*', 'Authorization', 'Content-Type', 'X-Requested-With', 'X-API-Key'],
            expose_headers=['X-Total-Count', 'X-Page-Count']
        )
        
        # Auth service CORS  
        self.service_configs['auth'] = CORSConfig(
            service_name='auth',
            allowed_origins=base_origins.copy(),
            allowed_headers=['*', 'Authorization', 'Content-Type'],
            expose_headers=['Set-Cookie']
        )
        
        # Frontend service CORS (if applicable)
        self.service_configs['frontend'] = CORSConfig(
            service_name='frontend',
            allowed_origins=base_origins.copy(),
            allowed_methods=['GET', 'POST', 'OPTIONS']
        )
        
        # Compile origin patterns for validation
        self._compile_origin_patterns()
        
        logger.info(f"Initialized CORS configs for {len(self.service_configs)} services")
    
    def _get_base_origins(self, config, environment: str) -> List[str]:
        """Get base allowed origins based on environment."""
        origins = []
        
        if environment == 'development':
            # Development origins
            origins.extend([
                'http://localhost:3000',    # Next.js default
                'http://localhost:3001',    # Alt frontend port  
                'http://127.0.0.1:3000',
                'http://127.0.0.1:3001'
            ])
            
            # Dynamic port support - allow localhost with any port
            if self.config.dynamic_origin_support:
                origins.extend([
                    'http://localhost:*',
                    'http://127.0.0.1:*'
                ])
                
        elif environment == 'staging':
            # Staging origins
            origins.extend([
                'https://app.staging.netrasystems.ai',
                'https://staging.netrasystems.ai'
            ])
            
        elif environment == 'production':
            # Production origins
            origins.extend([
                'https://app.netrasystems.ai',
                'https://www.netrasystems.ai',
                'https://netrasystems.ai'
            ])
        
        # Add any custom origins from config
        custom_origins = getattr(config, 'cors_allowed_origins', '')
        if custom_origins:
            if isinstance(custom_origins, str):
                origins.extend([origin.strip() for origin in custom_origins.split(',') if origin.strip()])
            elif isinstance(custom_origins, list):
                origins.extend(custom_origins)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_origins = []
        for origin in origins:
            if origin not in seen:
                seen.add(origin)
                unique_origins.append(origin)
        
        return unique_origins
    
    def _compile_origin_patterns(self) -> None:
        """Compile origin patterns for dynamic matching."""
        self.origin_patterns = []
        
        for service_config in self.service_configs.values():
            for origin in service_config.allowed_origins:
                if '*' in origin:
                    # Convert wildcard pattern to regex
                    pattern = origin.replace('*', r'[0-9]+').replace('.', r'\.')
                    try:
                        compiled_pattern = re.compile(f'^{pattern}$')
                        self.origin_patterns.append(compiled_pattern)
                    except re.error as e:
                        logger.warning(f"Invalid origin pattern {origin}: {e}")
    
    async def start(self) -> None:
        """Start CORS synchronizer."""
        if self._sync_task is None:
            self._sync_task = asyncio.create_task(self._sync_loop())
        
        # Perform initial synchronization
        await self._synchronize_all_services()
        
        logger.info("CORS synchronizer started")
    
    async def stop(self) -> None:
        """Stop CORS synchronizer."""
        self._shutdown = True
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        await self.http_client.aclose()
        logger.info("CORS synchronizer stopped")
    
    def validate_origin(self, origin: str) -> bool:
        """
        Validate if origin is allowed.
        
        Args:
            origin: Origin to validate
            
        Returns:
            True if origin is allowed
        """
        if not origin:
            return False
        
        # Check exact matches first
        for service_config in self.service_configs.values():
            if origin in service_config.allowed_origins:
                return True
        
        # Check pattern matches
        for pattern in self.origin_patterns:
            if pattern.match(origin):
                self.stats['dynamic_origins_resolved'] += 1
                return True
        
        # Special handling for development mode
        if self.config.development_mode:
            return self._validate_development_origin(origin)
        
        return False
    
    def _validate_development_origin(self, origin: str) -> bool:
        """Validate origin in development mode with relaxed rules."""
        try:
            parsed = urlparse(origin)
            
            # Allow localhost/127.0.0.1 with any port in development
            if parsed.hostname in ['localhost', '127.0.0.1']:
                # Only allow http in development
                if parsed.scheme == 'http':
                    self.stats['dynamic_origins_resolved'] += 1
                    return True
            
        except Exception as e:
            logger.warning(f"Failed to parse origin {origin}: {e}")
        
        return False
    
    def get_cors_headers(self, service_name: str, request_origin: Optional[str] = None) -> Dict[str, str]:
        """
        Get CORS headers for a service.
        
        Args:
            service_name: Name of the service
            request_origin: Origin from the request
            
        Returns:
            Dictionary of CORS headers
        """
        service_config = self.service_configs.get(service_name)
        if not service_config:
            logger.warning(f"No CORS config found for service {service_name}")
            return {}
        
        headers = {}
        
        # Access-Control-Allow-Origin
        if request_origin and self.validate_origin(request_origin):
            headers['Access-Control-Allow-Origin'] = request_origin
        elif service_config.allowed_origins:
            if len(service_config.allowed_origins) == 1 and '*' not in service_config.allowed_origins[0]:
                headers['Access-Control-Allow-Origin'] = service_config.allowed_origins[0]
            else:
                # Multiple origins or wildcards - need to validate against request origin
                headers['Access-Control-Allow-Origin'] = request_origin if request_origin and self.validate_origin(request_origin) else 'null'
        
        # Access-Control-Allow-Credentials
        if service_config.allow_credentials:
            headers['Access-Control-Allow-Credentials'] = 'true'
        
        # Access-Control-Allow-Methods
        if service_config.allowed_methods:
            headers['Access-Control-Allow-Methods'] = ', '.join(service_config.allowed_methods)
        
        # Access-Control-Allow-Headers
        if service_config.allowed_headers:
            if '*' in service_config.allowed_headers:
                headers['Access-Control-Allow-Headers'] = '*'
            else:
                headers['Access-Control-Allow-Headers'] = ', '.join(service_config.allowed_headers)
        
        # Access-Control-Expose-Headers
        if service_config.expose_headers:
            headers['Access-Control-Expose-Headers'] = ', '.join(service_config.expose_headers)
        
        # Access-Control-Max-Age
        headers['Access-Control-Max-Age'] = str(service_config.max_age)
        
        return headers
    
    def update_service_config(self, service_name: str, config_updates: Dict[str, Any]) -> bool:
        """
        Update CORS configuration for a service.
        
        Args:
            service_name: Name of the service
            config_updates: Configuration updates to apply
            
        Returns:
            True if update was successful
        """
        if service_name not in self.service_configs:
            logger.error(f"Service {service_name} not found")
            return False
        
        try:
            service_config = self.service_configs[service_name]
            
            # Apply updates
            for key, value in config_updates.items():
                if hasattr(service_config, key):
                    setattr(service_config, key, value)
                else:
                    logger.warning(f"Unknown config key {key} for service {service_name}")
            
            # Recompile patterns if origins changed
            if 'allowed_origins' in config_updates:
                self._compile_origin_patterns()
            
            logger.info(f"Updated CORS config for service {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update CORS config for {service_name}: {e}")
            return False
    
    async def _sync_loop(self) -> None:
        """Main synchronization loop."""
        while not self._shutdown:
            try:
                await self._synchronize_all_services()
                await asyncio.sleep(self.config.sync_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in CORS sync loop: {e}")
    
    async def _synchronize_all_services(self) -> None:
        """Synchronize CORS configurations for all services."""
        tasks = [
            self._validate_service_cors(service_name, config)
            for service_name, config in self.service_configs.items()
        ]
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_syncs = sum(1 for result in results if result is True)
            self.stats['configs_synchronized'] += successful_syncs
    
    async def _validate_service_cors(self, service_name: str, config: CORSConfig) -> bool:
        """
        Validate CORS configuration for a service.
        
        Args:
            service_name: Service name
            config: CORS configuration
            
        Returns:
            True if validation passed
        """
        self.stats['validation_checks'] += 1
        
        try:
            # For now, just validate the configuration structure
            # In a real implementation, you might check with the actual service
            
            # Validate origins
            for origin in config.allowed_origins:
                if not self._validate_origin_format(origin):
                    logger.warning(f"Invalid origin format in {service_name}: {origin}")
                    self.stats['validation_failures'] += 1
                    return False
            
            # Validate methods
            valid_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'}
            for method in config.allowed_methods:
                if method not in valid_methods:
                    logger.warning(f"Invalid HTTP method in {service_name}: {method}")
                    self.stats['validation_failures'] += 1
                    return False
            
            logger.debug(f"CORS validation passed for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"CORS validation error for {service_name}: {e}")
            self.stats['validation_failures'] += 1
            return False
    
    def _validate_origin_format(self, origin: str) -> bool:
        """Validate origin format."""
        if not origin:
            return False
        
        # Allow wildcard patterns
        if '*' in origin:
            return True
        
        try:
            parsed = urlparse(origin)
            # Must have scheme and hostname
            return bool(parsed.scheme and parsed.hostname)
        except Exception:
            return False
    
    def get_synchronizer_stats(self) -> Dict[str, Any]:
        """Get synchronizer statistics."""
        return {
            'services_configured': len(self.service_configs),
            'origin_patterns': len(self.origin_patterns),
            'development_mode': self.config.development_mode,
            **self.stats
        }
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get CORS configuration for a service."""
        config = self.service_configs.get(service_name)
        return config.to_dict() if config else None
    
    def get_all_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Get all CORS configurations."""
        return {
            service_name: config.to_dict()
            for service_name, config in self.service_configs.items()
        }
    
    async def check_origin_consistency(self) -> Dict[str, Any]:
        """Check for origin configuration inconsistencies across services."""
        inconsistencies = []
        
        # Get all unique origins across services
        all_origins = set()
        service_origins = {}
        
        for service_name, config in self.service_configs.items():
            service_origins[service_name] = set(config.allowed_origins)
            all_origins.update(config.allowed_origins)
        
        # Check for mismatches
        for service_name, origins in service_origins.items():
            missing_origins = all_origins - origins
            if missing_origins:
                inconsistencies.append({
                    'service': service_name,
                    'issue': 'missing_origins',
                    'missing': list(missing_origins)
                })
        
        if inconsistencies:
            self.stats['origin_mismatches'] += len(inconsistencies)
        
        return {
            'consistent': len(inconsistencies) == 0,
            'inconsistencies': inconsistencies,
            'total_origins': len(all_origins),
            'services_checked': len(self.service_configs)
        }


# Global CORS synchronizer instance
_cors_synchronizer: Optional[CORSSynchronizer] = None


def get_cors_synchronizer(config: Optional[SynchronizerConfig] = None) -> CORSSynchronizer:
    """Get global CORS synchronizer instance."""
    global _cors_synchronizer
    if _cors_synchronizer is None:
        _cors_synchronizer = CORSSynchronizer(config)
    return _cors_synchronizer


def validate_request_origin(origin: str) -> bool:
    """Convenience function to validate request origin."""
    synchronizer = get_cors_synchronizer()
    return synchronizer.validate_origin(origin)


def get_service_cors_headers(service_name: str, request_origin: Optional[str] = None) -> Dict[str, str]:
    """Convenience function to get CORS headers for a service."""
    synchronizer = get_cors_synchronizer()
    return synchronizer.get_cors_headers(service_name, request_origin)