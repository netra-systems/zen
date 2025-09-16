"""
Network Communication Handler for Netra Backend.

Provides comprehensive network communication management with:
- Dynamic CORS configuration with environment-specific rules
- DNS resolution with fallback mechanisms and caching
- SSL/TLS certificate handling and validation
- Connection timeout management with adaptive backoff
- WebSocket connection pooling and lifecycle management
- Network partition detection and recovery

Business Value Justification (BVJ):
- Segment: Platform/Internal (Network Infrastructure)
- Business Goal: Platform Stability & User Experience
- Value Impact: Ensures reliable communication between services and clients
- Revenue Impact: Network failures cause service unavailability and user disconnection, protecting entire platform availability
"""
import asyncio
import logging
import socket
import ssl
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse
import dns.resolver
import aiohttp
from aiohttp import web

try:
    from aiohttp_cors import setup as cors_setup
    import aiohttp_cors
    AIOHTTP_CORS_AVAILABLE = True
except ImportError:
    AIOHTTP_CORS_AVAILABLE = False

from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreaker,
    UnifiedCircuitConfig,
    get_unified_circuit_breaker_manager
)
from netra_backend.app.agents.agent_error_types import NetworkError
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.unified_logging import get_logger


class NetworkStatus(Enum):
    """Network connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    UNSTABLE = "unstable"
    PARTITIONED = "partitioned"


class SSLMode(Enum):
    """SSL/TLS configuration modes."""
    DISABLED = "disabled"
    OPTIONAL = "optional"
    REQUIRED = "required"
    STRICT = "strict"


@dataclass
class CORSConfig:
    """CORS configuration settings."""
    allow_origins: List[str] = field(default_factory=lambda: ["*"])
    allow_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allow_headers: List[str] = field(default_factory=lambda: ["*"])
    expose_headers: List[str] = field(default_factory=list)
    allow_credentials: bool = False
    max_age: int = 3600
    
    # Environment-specific overrides
    production_origins: List[str] = field(default_factory=list)
    staging_origins: List[str] = field(default_factory=list)
    development_origins: List[str] = field(default_factory=lambda: ["*"])


@dataclass
class ConnectionConfig:
    """Network connection configuration."""
    connect_timeout: float = 30.0
    read_timeout: float = 60.0
    write_timeout: float = 30.0
    total_timeout: float = 120.0
    keepalive_timeout: float = 30.0
    max_connections: int = 100
    max_connections_per_host: int = 30
    enable_compression: bool = True
    ssl_mode: SSLMode = SSLMode.OPTIONAL
    verify_ssl: bool = True
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None


@dataclass
class DNSConfig:
    """DNS resolution configuration."""
    nameservers: List[str] = field(default_factory=lambda: ["8.8.8.8", "1.1.1.1"])
    timeout: float = 5.0
    cache_ttl: int = 300  # 5 minutes
    max_cache_size: int = 1000
    enable_fallback: bool = True


@dataclass
class WebSocketConfig:
    """WebSocket connection configuration."""
    max_connections: int = 1000
    heartbeat_interval: float = 30.0
    connection_timeout: float = 30.0
    max_message_size: int = 1024 * 1024  # 1MB
    compression: bool = True
    auto_reconnect: bool = True
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = 5


@dataclass
class NetworkMetrics:
    """Network performance and reliability metrics."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    dns_cache_hit_rate: float = 0.0
    ssl_handshake_failures: int = 0
    websocket_connections: int = 0
    network_errors: int = 0
    partition_events: int = 0


class NetworkHandler:
    """
    Comprehensive network communication handler.
    
    Features:
    - Dynamic CORS configuration based on environment
    - DNS resolution with caching and fallbacks  
    - SSL/TLS certificate management and validation
    - Connection pooling and lifecycle management
    - WebSocket connection management
    - Network partition detection and recovery
    - Comprehensive metrics and monitoring
    - Adaptive timeout and retry mechanisms
    """
    
    def __init__(self,
                 environment: str = "development",
                 cors_config: Optional[CORSConfig] = None,
                 connection_config: Optional[ConnectionConfig] = None,
                 dns_config: Optional[DNSConfig] = None,
                 websocket_config: Optional[WebSocketConfig] = None):
        self.logger = get_logger(__name__)
        self.environment = environment.lower()
        
        # Configuration
        self.cors_config = cors_config or CORSConfig()
        self.connection_config = connection_config or ConnectionConfig()
        self.dns_config = dns_config or DNSConfig()
        self.websocket_config = websocket_config or WebSocketConfig()
        
        # Network state
        self.status = NetworkStatus.DISCONNECTED
        self.metrics = NetworkMetrics()
        self.connection_pool: Optional[aiohttp.ClientSession] = None
        
        # DNS cache
        self.dns_cache: Dict[str, Tuple[List[str], datetime]] = {}
        self.dns_resolver = dns.resolver.Resolver()
        self.dns_resolver.nameservers = self.dns_config.nameservers
        self.dns_resolver.timeout = self.dns_config.timeout
        
        # SSL context
        self.ssl_context: Optional[ssl.SSLContext] = None
        
        # WebSocket connections
        self.websocket_connections: Set[Any] = set()
        self.websocket_pools: Dict[str, List[Any]] = {}
        
        # Circuit breakers using unified implementation
        manager = get_unified_circuit_breaker_manager()
        
        dns_config = UnifiedCircuitConfig(
            name="dns_resolver",
            failure_threshold=5,
            recovery_timeout=60.0,
            timeout_seconds=self.dns_config.timeout,
            adaptive_threshold=True
        )
        self.dns_breaker = manager.create_circuit_breaker("dns_resolver", dns_config)
        
        ssl_config = UnifiedCircuitConfig(
            name="ssl_handler",  
            failure_threshold=3,
            recovery_timeout=120.0,
            timeout_seconds=30.0,
            adaptive_threshold=True
        )
        self.ssl_breaker = manager.create_circuit_breaker("ssl_handler", ssl_config)
        
        # Monitoring
        self.monitor_task: Optional[asyncio.Task] = None
        self.health_check_urls: List[str] = [
            "https://www.google.com",
            "https://1.1.1.1"
        ]
        
        self.logger.info("NetworkHandler initialized", extra={
            "environment": self.environment,
            "cors_origins": self._get_effective_cors_origins(),
            "ssl_mode": self.connection_config.ssl_mode.value
        })
    
    async def initialize(self) -> None:
        """Initialize network handler and start monitoring."""
        self.logger.info("Starting network handler initialization")
        
        # Initialize SSL context
        await self._initialize_ssl_context()
        
        # Create connection pool
        await self._create_connection_pool()
        
        # Start network monitoring
        self.monitor_task = asyncio.create_task(
            self._network_monitor_loop(),
            name="network-monitor"
        )
        
        # Initial network status check
        await self._check_network_status()
        
        self.logger.info("Network handler initialized", extra={
            "status": self.status.value,
            "ssl_enabled": self.ssl_context is not None
        })
    
    async def _initialize_ssl_context(self) -> None:
        """Initialize SSL context based on configuration."""
        if self.connection_config.ssl_mode == SSLMode.DISABLED:
            return
        
        try:
            self.ssl_context = ssl.create_default_context()
            
            # Configure SSL verification
            if not self.connection_config.verify_ssl:
                self.ssl_context.check_hostname = False
                self.ssl_context.verify_mode = ssl.CERT_NONE
            
            # Load custom CA certificates
            if self.connection_config.ca_cert_path:
                self.ssl_context.load_verify_locations(self.connection_config.ca_cert_path)
            
            # Load client certificates
            if self.connection_config.client_cert_path and self.connection_config.client_key_path:
                self.ssl_context.load_cert_chain(
                    self.connection_config.client_cert_path,
                    self.connection_config.client_key_path
                )
            
            self.logger.info("SSL context initialized", extra={
                "verify_ssl": self.connection_config.verify_ssl,
                "has_client_cert": bool(self.connection_config.client_cert_path)
            })
            
        except Exception as e:
            if self.connection_config.ssl_mode == SSLMode.REQUIRED:
                raise NetworkError(f"Failed to initialize SSL context: {e}")
            else:
                self.logger.warning("SSL initialization failed, continuing without SSL", extra={
                    "error": str(e)
                })
                self.ssl_context = None
    
    async def _create_connection_pool(self) -> None:
        """Create HTTP connection pool with configured settings."""
        timeout = aiohttp.ClientTimeout(
            total=self.connection_config.total_timeout,
            connect=self.connection_config.connect_timeout,
            sock_read=self.connection_config.read_timeout,
            sock_connect=self.connection_config.write_timeout
        )
        
        connector = aiohttp.TCPConnector(
            limit=self.connection_config.max_connections,
            limit_per_host=self.connection_config.max_connections_per_host,
            ttl_dns_cache=self.dns_config.cache_ttl,
            enable_cleanup_closed=True,
            ssl=self.ssl_context
        )
        
        self.connection_pool = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "Netra-Backend/1.0",
                "Accept-Encoding": "gzip, deflate" if self.connection_config.enable_compression else None
            }
        )
        
        self.logger.debug("Connection pool created", extra={
            "max_connections": self.connection_config.max_connections,
            "timeout": self.connection_config.total_timeout
        })
    
    def setup_cors(self, app: web.Application) -> None:
        """Setup CORS middleware for web application."""
        effective_origins = self._get_effective_cors_origins()
        
        if not AIOHTTP_CORS_AVAILABLE:
            self.logger.warning("aiohttp-cors not available, CORS setup skipped", extra={
                "origins": effective_origins
            })
            return
        
        cors = cors_setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_origins=effective_origins,
                allow_methods=self.cors_config.allow_methods,
                allow_headers=self.cors_config.allow_headers,
                expose_headers=self.cors_config.expose_headers,
                allow_credentials=self.cors_config.allow_credentials,
                max_age=self.cors_config.max_age
            )
        })
        
        # Add CORS to all routes
        for route in list(app.router.routes()):
            cors.add(route)
        
        self.logger.info("CORS configured", extra={
            "origins": effective_origins,
            "methods": self.cors_config.allow_methods,
            "credentials": self.cors_config.allow_credentials
        })
    
    def _get_effective_cors_origins(self) -> List[str]:
        """Get effective CORS origins based on environment."""
        if self.environment == "production":
            return self.cors_config.production_origins or ["https://netrasystems.ai"]
        elif self.environment == "staging":
            return self.cors_config.staging_origins or ["https://staging.netrasystems.ai"]
        else:
            return self.cors_config.development_origins
    
    async def resolve_dns(self, hostname: str, use_cache: bool = True) -> List[str]:
        """Resolve hostname to IP addresses with caching."""
        if use_cache and hostname in self.dns_cache:
            ips, cached_at = self.dns_cache[hostname]
            if datetime.now(timezone.utc) - cached_at < timedelta(seconds=self.dns_config.cache_ttl):
                self.metrics.dns_cache_hit_rate += 1
                return ips
        
        try:
            ips = await self.dns_breaker.call(self._resolve_dns_with_fallback, hostname)
            
            # Cache the result
            if len(self.dns_cache) >= self.dns_config.max_cache_size:
                # Remove oldest entry
                oldest = min(self.dns_cache.items(), key=lambda x: x[1][1])
                del self.dns_cache[oldest[0]]
            
            self.dns_cache[hostname] = (ips, datetime.now(timezone.utc))
            
            self.logger.debug("DNS resolution successful", extra={
                "hostname": hostname,
                "ips": ips,
                "cached": use_cache
            })
            
            return ips
                
        except Exception as e:
            self.logger.warning("DNS resolution failed", extra={
                "hostname": hostname,
                "error": str(e)
            })
            # Return cached result even if expired, as fallback
            if hostname in self.dns_cache:
                return self.dns_cache[hostname][0]
            raise NetworkError(f"Failed to resolve {hostname}: {e}")
    
    async def _resolve_dns_with_fallback(self, hostname: str) -> List[str]:
        """Resolve DNS with fallback nameservers."""
        for nameserver in self.dns_config.nameservers:
            try:
                self.dns_resolver.nameservers = [nameserver]
                result = self.dns_resolver.query(hostname, 'A')
                return [str(ip) for ip in result]
            except Exception as e:
                self.logger.debug("DNS query failed", extra={
                    "hostname": hostname,
                    "nameserver": nameserver,
                    "error": str(e)
                })
                continue
        
        # If all nameservers fail, try system resolution
        try:
            result = socket.getaddrinfo(hostname, None, socket.AF_INET)
            return [addr[4][0] for addr in result]
        except socket.gaierror as e:
            raise NetworkError(f"System DNS resolution failed for {hostname}: {e}")
    
    async def make_request(self, 
                          method: str, 
                          url: str, 
                          **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request with comprehensive error handling."""
        if not self.connection_pool:
            raise NetworkError("Connection pool not initialized")
        
        start_time = time.time()
        
        try:
            # Pre-resolve DNS if hostname is provided
            parsed_url = urlparse(url)
            if parsed_url.hostname:
                await self.resolve_dns(parsed_url.hostname)
            
            response = await self.connection_pool.request(method, url, **kwargs)
            
            # Update metrics
            response_time = time.time() - start_time
            self.metrics.total_requests += 1
            self._update_average_response_time(response_time)
            
            return response
            
        except Exception as e:
            self.metrics.failed_requests += 1
            self.metrics.network_errors += 1
            
            # Check for network partition
            if self._is_network_partition_error(e):
                await self._handle_network_partition()
            
            self.logger.error("HTTP request failed", extra={
                "method": method,
                "url": url,
                "error": str(e),
                "response_time": time.time() - start_time
            })
            raise NetworkError(f"Request failed: {e}")
    
    def _update_average_response_time(self, response_time: float) -> None:
        """Update average response time using exponential moving average."""
        if self.metrics.average_response_time == 0:
            self.metrics.average_response_time = response_time
        else:
            # Use exponential moving average with alpha = 0.1
            self.metrics.average_response_time = (
                0.9 * self.metrics.average_response_time + 
                0.1 * response_time
            )
    
    def _is_network_partition_error(self, error: Exception) -> bool:
        """Check if error indicates network partition."""
        error_str = str(error).lower()
        partition_indicators = [
            "connection refused",
            "network unreachable",
            "no route to host",
            "connection timed out",
            "temporary failure in name resolution"
        ]
        return any(indicator in error_str for indicator in partition_indicators)
    
    async def _handle_network_partition(self) -> None:
        """Handle detected network partition."""
        if self.status != NetworkStatus.PARTITIONED:
            self.status = NetworkStatus.PARTITIONED
            self.metrics.partition_events += 1
            
            self.logger.warning("Network partition detected", extra={
                "previous_status": self.status.value,
                "partition_events": self.metrics.partition_events
            })
            
            # Trigger recovery process
            asyncio.create_task(self._recovery_process())
    
    async def _recovery_process(self) -> None:
        """Attempt to recover from network partition."""
        recovery_attempts = 0
        max_attempts = 10
        
        while self.status == NetworkStatus.PARTITIONED and recovery_attempts < max_attempts:
            await asyncio.sleep(5 * (2 ** min(recovery_attempts, 5)))  # Exponential backoff
            
            try:
                await self._check_network_status()
                if self.status != NetworkStatus.PARTITIONED:
                    self.logger.info("Network partition recovery successful", extra={
                        "attempts": recovery_attempts + 1
                    })
                    break
            except Exception as e:
                self.logger.debug("Recovery attempt failed", extra={
                    "attempt": recovery_attempts + 1,
                    "error": str(e)
                })
            
            recovery_attempts += 1
        
        if self.status == NetworkStatus.PARTITIONED:
            self.logger.error("Network partition recovery failed", extra={
                "attempts": recovery_attempts
            })
    
    async def _network_monitor_loop(self) -> None:
        """Background network monitoring loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Update network status
                await self._check_network_status()
                
                # Clean up DNS cache
                await self._cleanup_dns_cache()
                
                # Monitor WebSocket connections
                await self._monitor_websocket_connections()
                
                # Update metrics
                self._update_connection_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in network monitor loop", extra={
                    "error": str(e)
                }, exc_info=True)
    
    async def _check_network_status(self) -> None:
        """Check network connectivity status."""
        successful_checks = 0
        total_checks = len(self.health_check_urls)
        
        for url in self.health_check_urls:
            try:
                async with self.connection_pool.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        successful_checks += 1
            except Exception:
                pass
        
        # Update status based on success rate
        success_rate = successful_checks / total_checks if total_checks > 0 else 0
        
        if success_rate >= 0.8:
            self.status = NetworkStatus.CONNECTED
        elif success_rate >= 0.5:
            self.status = NetworkStatus.UNSTABLE
        else:
            self.status = NetworkStatus.DISCONNECTED
    
    async def _cleanup_dns_cache(self) -> None:
        """Clean up expired DNS cache entries."""
        current_time = datetime.now(timezone.utc)
        expired_keys = []
        
        for hostname, (ips, cached_at) in self.dns_cache.items():
            if current_time - cached_at > timedelta(seconds=self.dns_config.cache_ttl * 2):
                expired_keys.append(hostname)
        
        for key in expired_keys:
            del self.dns_cache[key]
        
        if expired_keys:
            self.logger.debug("DNS cache cleanup", extra={
                "expired_entries": len(expired_keys)
            })
    
    async def _monitor_websocket_connections(self) -> None:
        """Monitor WebSocket connection health."""
        active_connections = 0
        stale_connections = []
        
        for connection in list(self.websocket_connections):
            try:
                if hasattr(connection, 'closed') and not connection.closed:
                    active_connections += 1
                else:
                    stale_connections.append(connection)
            except Exception:
                stale_connections.append(connection)
        
        # Remove stale connections
        for connection in stale_connections:
            self.websocket_connections.discard(connection)
        
        self.metrics.websocket_connections = active_connections
        
        if stale_connections:
            self.logger.debug("WebSocket cleanup", extra={
                "stale_connections": len(stale_connections),
                "active_connections": active_connections
            })
    
    def _update_connection_metrics(self) -> None:
        """Update connection pool metrics."""
        if self.connection_pool and hasattr(self.connection_pool.connector, '_conns'):
            self.metrics.active_connections = sum(
                len(conns) for conns in self.connection_pool.connector._conns.values()
            )
    
    def register_websocket_connection(self, connection: Any) -> None:
        """Register a WebSocket connection for monitoring."""
        self.websocket_connections.add(connection)
        
        # Enforce connection limits
        if len(self.websocket_connections) > self.websocket_config.max_connections:
            self.logger.warning("WebSocket connection limit exceeded", extra={
                "current_connections": len(self.websocket_connections),
                "limit": self.websocket_config.max_connections
            })
    
    def unregister_websocket_connection(self, connection: Any) -> None:
        """Unregister a WebSocket connection."""
        self.websocket_connections.discard(connection)
    
    async def cleanup(self) -> None:
        """Clean up network handler resources."""
        self.logger.info("Cleaning up network handler")
        
        # Cancel monitoring task
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket connections
        for connection in list(self.websocket_connections):
            try:
                if hasattr(connection, 'close'):
                    await connection.close()
            except Exception as e:
                self.logger.debug("Error closing WebSocket connection", extra={
                    "error": str(e)
                })
        
        # Close connection pool
        if self.connection_pool:
            await self.connection_pool.close()
        
        self.logger.info("Network handler cleanup completed")
    
    @asynccontextmanager
    async def network_context(self):
        """Context manager for network handler lifecycle."""
        try:
            await self.initialize()
            yield self
        finally:
            await self.cleanup()
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status."""
        return {
            "status": self.status.value,
            "metrics": {
                "active_connections": self.metrics.active_connections,
                "total_requests": self.metrics.total_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": (
                    (self.metrics.total_requests - self.metrics.failed_requests) / 
                    max(self.metrics.total_requests, 1)
                ) * 100,
                "average_response_time": self.metrics.average_response_time,
                "dns_cache_size": len(self.dns_cache),
                "dns_cache_hit_rate": self.metrics.dns_cache_hit_rate,
                "websocket_connections": self.metrics.websocket_connections,
                "network_errors": self.metrics.network_errors,
                "partition_events": self.metrics.partition_events
            },
            "configuration": {
                "environment": self.environment,
                "cors_origins": self._get_effective_cors_origins(),
                "ssl_mode": self.connection_config.ssl_mode.value,
                "max_connections": self.connection_config.max_connections,
                "dns_nameservers": self.dns_config.nameservers
            },
            "circuit_breakers": {
                "dns_breaker": self.dns_breaker.state.value,
                "ssl_breaker": self.ssl_breaker.state.value
            }
        }


# Global network handler instance
network_handler = NetworkHandler()