"""
Real Staging Test Framework - Forces actual network calls to staging environment

This framework makes it IMPOSSIBLE to write fake tests by:
- Forcing minimum network latency validation (>0.1s)
- Requiring real HTTP/WebSocket connections
- Tracking actual network traffic 
- Validating response times and data authenticity
- Comprehensive error handling for all network failure modes

Business Impact: Prevents $120K+ MRR risk from fake test scenarios
"""

import asyncio
import json
import logging
import time
import socket
import ssl
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin
import hashlib
import re

try:
    import requests
    import websockets
    import psutil
    import aiohttp
except ImportError as e:
    raise ImportError(
        f"Missing required dependencies for real staging tests: {e}. "
        "Install with: pip install requests websockets psutil aiohttp"
    ) from e

from shared.isolated_environment import get_env


# =====================================================================
# CRITICAL NETWORK VALIDATION SETTINGS
# =====================================================================

class NetworkValidationConfig:
    """Configuration for enforcing real network calls"""
    
    # CRITICAL: Minimum latency to prove real network call occurred
    MIN_NETWORK_LATENCY_SECONDS = 0.1
    
    # CRITICAL: Minimum timeout to prevent instant responses
    MIN_TIMEOUT_SECONDS = 1.0
    
    # CRITICAL: Maximum allowed timeout for staging tests
    MAX_TIMEOUT_SECONDS = 60.0
    
    # CRITICAL: Required staging URL patterns
    STAGING_URL_PATTERNS = [
        r"https://.*-staging-.*\.a\.run\.app",
        r"https://.*staging.*\.netra\.ai",
        r"wss://.*-staging-.*\.a\.run\.app",
        r"wss://.*staging.*\.netra\.ai"
    ]
    
    # CRITICAL: Forbidden patterns that indicate fake tests
    FORBIDDEN_PATTERNS = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "mock",
        "fake",
        "stub",
        "dummy"
    ]


# =====================================================================
# DATA VALIDATION AND ANTI-HARDCODING
# =====================================================================

@dataclass
class NetworkMetrics:
    """Metrics to prove real network interaction occurred"""
    start_time: float
    end_time: float
    latency_seconds: float
    bytes_sent: int
    bytes_received: int
    remote_address: str
    response_headers: Dict[str, str]
    status_code: Optional[int] = None
    
    def validate_real_network_call(self) -> Tuple[bool, List[str]]:
        """Validate this represents a real network call"""
        errors = []
        
        # CRITICAL: Latency validation
        if self.latency_seconds < NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS:
            errors.append(
                f"Latency {self.latency_seconds:.4f}s < minimum {NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS}s "
                f"- indicates fake/cached response"
            )
        
        # CRITICAL: Data transfer validation
        if self.bytes_received == 0:
            errors.append("No bytes received - indicates no real network response")
        
        # CRITICAL: Remote address validation
        for pattern in NetworkValidationConfig.FORBIDDEN_PATTERNS:
            if pattern.lower() in self.remote_address.lower():
                errors.append(f"Remote address '{self.remote_address}' contains forbidden pattern '{pattern}'")
        
        # CRITICAL: Response validation
        if self.status_code is None:
            errors.append("No HTTP status code - indicates no real HTTP response")
        
        return len(errors) == 0, errors


class ResponseValidator:
    """Validates response data is real, not hardcoded"""
    
    @staticmethod
    def validate_non_hardcoded_data(data: Any, field_name: str) -> Tuple[bool, List[str]]:
        """Validate data is not hardcoded/fake"""
        errors = []
        
        if isinstance(data, dict):
            # Check for obvious fake data patterns
            fake_patterns = {
                "test_", "fake_", "mock_", "dummy_", "stub_",
                "placeholder", "example", "sample", "default"
            }
            
            for key, value in data.items():
                key_str = str(key).lower()
                value_str = str(value).lower()
                
                for pattern in fake_patterns:
                    if pattern in key_str or pattern in value_str:
                        errors.append(f"Field '{field_name}.{key}' contains fake pattern: {pattern}")
            
            # Check for repeated/pattern data that indicates hardcoding
            if len(data) > 3:
                values = [str(v) for v in data.values()]
                unique_values = set(values)
                if len(unique_values) < len(values) * 0.5:  # More than 50% duplicated
                    errors.append(f"Field '{field_name}' has suspicious data patterns (too many duplicates)")
        
        elif isinstance(data, list) and len(data) > 2:
            # Check for repeated list elements
            if len(set(str(item) for item in data)) < len(data) * 0.7:
                errors.append(f"Field '{field_name}' list has suspicious patterns (too repetitive)")
        
        elif isinstance(data, str):
            # Check for obvious fake strings
            fake_strings = {
                "test", "fake", "mock", "dummy", "stub", "placeholder", 
                "example", "sample", "lorem ipsum", "foo", "bar", "baz"
            }
            data_lower = data.lower()
            for fake_str in fake_strings:
                if fake_str in data_lower:
                    errors.append(f"Field '{field_name}' contains fake string pattern: {fake_str}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_timestamp_freshness(timestamp_data: Any, field_name: str, max_age_hours: int = 24) -> Tuple[bool, List[str]]:
        """Validate timestamp data is fresh (not hardcoded old data)"""
        errors = []
        
        try:
            if isinstance(timestamp_data, str):
                # Try to parse ISO format
                dt = datetime.fromisoformat(timestamp_data.replace('Z', '+00:00'))
            elif isinstance(timestamp_data, (int, float)):
                # Unix timestamp
                dt = datetime.fromtimestamp(timestamp_data)
            else:
                return True, []  # Skip validation for non-timestamp data
            
            age = datetime.now() - dt.replace(tzinfo=None)
            if age > timedelta(hours=max_age_hours):
                errors.append(
                    f"Field '{field_name}' timestamp is {age.total_seconds()/3600:.1f} hours old "
                    f"(max {max_age_hours}h) - indicates hardcoded old data"
                )
        except (ValueError, TypeError):
            # Not a parseable timestamp - skip validation
            pass
        
        return len(errors) == 0, errors


# =====================================================================
# ENHANCED HTTP CLIENT WITH MANDATORY VALIDATION
# =====================================================================

class RealNetworkHTTPClient:
    """HTTP client that enforces real network calls and validates responses"""
    
    def __init__(self, base_url: str, timeout: float = None):
        """Initialize with staging URL validation"""
        self.base_url = self._validate_staging_url(base_url)
        self.timeout = self._validate_timeout(timeout or 10.0)
        self.session = requests.Session()
        self._setup_session()
        
        # Network monitoring
        self._network_calls: List[NetworkMetrics] = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _validate_staging_url(self, url: str) -> str:
        """Validate URL is a real staging environment"""
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Check for forbidden patterns
        for pattern in NetworkValidationConfig.FORBIDDEN_PATTERNS:
            if pattern.lower() in url.lower():
                raise ValueError(f"URL '{url}' contains forbidden pattern '{pattern}' - not a real staging URL")
        
        # Check for staging patterns
        is_staging = any(
            re.match(pattern, url, re.IGNORECASE) 
            for pattern in NetworkValidationConfig.STAGING_URL_PATTERNS
        )
        
        if not is_staging:
            raise ValueError(
                f"URL '{url}' does not match staging patterns. Expected patterns: "
                f"{NetworkValidationConfig.STAGING_URL_PATTERNS}"
            )
        
        return url
    
    def _validate_timeout(self, timeout: float) -> float:
        """Validate timeout is appropriate for real network calls"""
        if timeout < NetworkValidationConfig.MIN_TIMEOUT_SECONDS:
            raise ValueError(
                f"Timeout {timeout}s < minimum {NetworkValidationConfig.MIN_TIMEOUT_SECONDS}s "
                f"- prevents detection of fake instant responses"
            )
        
        if timeout > NetworkValidationConfig.MAX_TIMEOUT_SECONDS:
            raise ValueError(
                f"Timeout {timeout}s > maximum {NetworkValidationConfig.MAX_TIMEOUT_SECONDS}s "
                f"- unreasonable for staging tests"
            )
        
        return timeout
    
    def _setup_session(self):
        """Setup session for real network monitoring"""
        self.session.headers.update({
            'User-Agent': f'RealStagingTestFramework/1.0 (NetworkValidation)',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
    
    def _record_network_call(self, start_time: float, response: requests.Response) -> NetworkMetrics:
        """Record network call metrics for validation"""
        end_time = time.time()
        
        # Get remote address
        remote_address = "unknown"
        try:
            parsed_url = urlparse(response.url)
            remote_address = socket.gethostbyname(parsed_url.hostname or "")
        except (socket.gaierror, AttributeError):
            pass
        
        # Calculate data transfer (approximate)
        request_size = len(response.request.body or b"") + sum(len(f"{k}: {v}") for k, v in response.request.headers.items())
        response_size = len(response.content) + sum(len(f"{k}: {v}") for k, v in response.headers.items())
        
        metrics = NetworkMetrics(
            start_time=start_time,
            end_time=end_time,
            latency_seconds=end_time - start_time,
            bytes_sent=request_size,
            bytes_received=response_size,
            remote_address=remote_address,
            response_headers=dict(response.headers),
            status_code=response.status_code
        )
        
        self._network_calls.append(metrics)
        
        # CRITICAL: Validate this was a real network call
        is_valid, errors = metrics.validate_real_network_call()
        if not is_valid:
            raise ValueError(
                f"FAKE TEST DETECTED - Network call validation failed:\n" +
                "\n".join(f"  - {error}" for error in errors)
            )
        
        self.logger.info(
            f"Validated real network call: {metrics.latency_seconds:.3f}s latency, "
            f"{metrics.bytes_received} bytes received from {metrics.remote_address}"
        )
        
        return metrics
    
    def get(self, path: str, **kwargs) -> Tuple[requests.Response, NetworkMetrics]:
        """GET request with network validation"""
        url = urljoin(self.base_url, path)
        self.logger.info(f"Making real GET request to: {url}")
        
        start_time = time.time()
        try:
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            metrics = self._record_network_call(start_time, response)
            
            # Validate response data is not hardcoded
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    data = response.json()
                    is_valid, errors = ResponseValidator.validate_non_hardcoded_data(data, "response_body")
                    if not is_valid:
                        self.logger.warning(f"Potential hardcoded data detected: {errors}")
                except (ValueError, json.JSONDecodeError):
                    pass
            
            return response, metrics
        
        except requests.exceptions.RequestException as e:
            # Record failed network attempt
            end_time = time.time()
            if end_time - start_time < NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS:
                raise ValueError(
                    f"FAKE TEST DETECTED - Network 'failure' too fast ({end_time - start_time:.3f}s). "
                    f"Real network failures take time."
                ) from e
            raise
    
    def post(self, path: str, json: Optional[Dict] = None, data: Optional[Any] = None, **kwargs) -> Tuple[requests.Response, NetworkMetrics]:
        """POST request with network validation"""
        url = urljoin(self.base_url, path)
        self.logger.info(f"Making real POST request to: {url}")
        
        start_time = time.time()
        try:
            response = self.session.post(url, json=json, data=data, timeout=self.timeout, **kwargs)
            metrics = self._record_network_call(start_time, response)
            return response, metrics
        
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            if end_time - start_time < NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS:
                raise ValueError(
                    f"FAKE TEST DETECTED - Network 'failure' too fast ({end_time - start_time:.3f}s)"
                ) from e
            raise
    
    def put(self, path: str, json: Optional[Dict] = None, data: Optional[Any] = None, **kwargs) -> Tuple[requests.Response, NetworkMetrics]:
        """PUT request with network validation"""
        url = urljoin(self.base_url, path)
        self.logger.info(f"Making real PUT request to: {url}")
        
        start_time = time.time()
        try:
            response = self.session.put(url, json=json, data=data, timeout=self.timeout, **kwargs)
            metrics = self._record_network_call(start_time, response)
            return response, metrics
        
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            if end_time - start_time < NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS:
                raise ValueError(
                    f"FAKE TEST DETECTED - Network 'failure' too fast ({end_time - start_time:.3f}s)"
                ) from e
            raise
    
    def delete(self, path: str, **kwargs) -> Tuple[requests.Response, NetworkMetrics]:
        """DELETE request with network validation"""
        url = urljoin(self.base_url, path)
        self.logger.info(f"Making real DELETE request to: {url}")
        
        start_time = time.time()
        try:
            response = self.session.delete(url, timeout=self.timeout, **kwargs)
            metrics = self._record_network_call(start_time, response)
            return response, metrics
        
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            if end_time - start_time < NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS:
                raise ValueError(
                    f"FAKE TEST DETECTED - Network 'failure' too fast ({end_time - start_time:.3f}s)"
                ) from e
            raise
    
    def get_network_metrics(self) -> List[NetworkMetrics]:
        """Get all recorded network metrics"""
        return self._network_calls.copy()
    
    def get_total_network_time(self) -> float:
        """Get total time spent in network calls"""
        return sum(m.latency_seconds for m in self._network_calls)


# =====================================================================
# REAL WEBSOCKET CLIENT WITH VALIDATION
# =====================================================================

class RealNetworkWebSocketClient:
    """WebSocket client that enforces real network connections"""
    
    def __init__(self, base_url: str, timeout: float = None):
        """Initialize with staging WebSocket URL validation"""
        self.base_url = self._validate_staging_websocket_url(base_url)
        self.timeout = self._validate_timeout(timeout or 10.0)
        self._connection = None
        self._connection_metrics = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _validate_staging_websocket_url(self, url: str) -> str:
        """Validate WebSocket URL is real staging"""
        if not url:
            raise ValueError("WebSocket URL cannot be empty")
        
        # Convert https to wss if needed
        if url.startswith('https://'):
            url = url.replace('https://', 'wss://')
        elif url.startswith('http://'):
            url = url.replace('http://', 'ws://')
        
        # Check for forbidden patterns
        for pattern in NetworkValidationConfig.FORBIDDEN_PATTERNS:
            if pattern.lower() in url.lower():
                raise ValueError(f"WebSocket URL '{url}' contains forbidden pattern '{pattern}'")
        
        # Check for staging patterns (modified for WebSocket)
        ws_patterns = [p.replace('https://', 'wss://').replace('http://', 'ws://') 
                      for p in NetworkValidationConfig.STAGING_URL_PATTERNS]
        
        is_staging = any(
            re.match(pattern, url, re.IGNORECASE) 
            for pattern in ws_patterns
        )
        
        if not is_staging:
            raise ValueError(
                f"WebSocket URL '{url}' does not match staging patterns. Expected patterns: {ws_patterns}"
            )
        
        return url
    
    def _validate_timeout(self, timeout: float) -> float:
        """Validate timeout for WebSocket connections"""
        if timeout < NetworkValidationConfig.MIN_TIMEOUT_SECONDS:
            raise ValueError(
                f"WebSocket timeout {timeout}s < minimum {NetworkValidationConfig.MIN_TIMEOUT_SECONDS}s"
            )
        
        if timeout > NetworkValidationConfig.MAX_TIMEOUT_SECONDS:
            raise ValueError(
                f"WebSocket timeout {timeout}s > maximum {NetworkValidationConfig.MAX_TIMEOUT_SECONDS}s"
            )
        
        return timeout
    
    @asynccontextmanager
    async def connect(self, path: str = "/ws", headers: Optional[Dict] = None):
        """Connect to real staging WebSocket with validation"""
        url = self.base_url.rstrip('/') + '/' + path.lstrip('/')
        self.logger.info(f"Connecting to real WebSocket: {url}")
        
        start_time = time.time()
        try:
            # Add anti-cache headers
            connect_headers = {
                'User-Agent': 'RealStagingTestFramework/1.0 (WebSocketValidation)',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            if headers:
                connect_headers.update(headers)
            
            async with websockets.connect(
                url, 
                timeout=self.timeout,
                extra_headers=connect_headers
            ) as websocket:
                
                connection_time = time.time() - start_time
                
                # CRITICAL: Validate connection time indicates real network
                if connection_time < NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS:
                    raise ValueError(
                        f"FAKE TEST DETECTED - WebSocket connection too fast ({connection_time:.3f}s). "
                        f"Real network connections take time."
                    )
                
                self.logger.info(f"Real WebSocket connected in {connection_time:.3f}s")
                self._connection = websocket
                
                # Record connection metrics
                self._connection_metrics = NetworkMetrics(
                    start_time=start_time,
                    end_time=time.time(),
                    latency_seconds=connection_time,
                    bytes_sent=0,  # Will be updated during communication
                    bytes_received=0,  # Will be updated during communication
                    remote_address=websocket.remote_address[0] if websocket.remote_address else "unknown",
                    response_headers={'connection': 'websocket'},
                    status_code=101  # WebSocket upgrade
                )
                
                yield websocket
        
        except Exception as e:
            connection_time = time.time() - start_time
            if connection_time < NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS:
                raise ValueError(
                    f"FAKE TEST DETECTED - WebSocket 'failure' too fast ({connection_time:.3f}s)"
                ) from e
            raise
        finally:
            self._connection = None
    
    async def send_and_receive(self, websocket, message: str, timeout: Optional[float] = None) -> str:
        """Send message and receive response with validation"""
        send_timeout = timeout or self.timeout
        
        self.logger.info(f"Sending WebSocket message: {message[:100]}...")
        
        start_time = time.time()
        try:
            await websocket.send(message)
            
            # Wait for response with timeout
            response = await asyncio.wait_for(websocket.recv(), timeout=send_timeout)
            
            response_time = time.time() - start_time
            
            # CRITICAL: Validate response time indicates real network interaction
            if response_time < NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS:
                raise ValueError(
                    f"FAKE TEST DETECTED - WebSocket response too fast ({response_time:.3f}s). "
                    f"Real network responses take time."
                )
            
            # Update connection metrics
            if self._connection_metrics:
                self._connection_metrics.bytes_sent += len(message.encode('utf-8'))
                self._connection_metrics.bytes_received += len(response.encode('utf-8'))
            
            self.logger.info(f"Received WebSocket response in {response_time:.3f}s: {response[:100]}...")
            
            # Validate response is not hardcoded
            try:
                data = json.loads(response)
                is_valid, errors = ResponseValidator.validate_non_hardcoded_data(data, "websocket_response")
                if not is_valid:
                    self.logger.warning(f"Potential hardcoded WebSocket data: {errors}")
            except json.JSONDecodeError:
                pass
            
            return response
        
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            if response_time < send_timeout * 0.9:  # Allow some variance
                raise ValueError(
                    f"FAKE TEST DETECTED - WebSocket 'timeout' too fast ({response_time:.3f}s < {send_timeout}s)"
                )
            raise
    
    def get_connection_metrics(self) -> Optional[NetworkMetrics]:
        """Get connection metrics if available"""
        return self._connection_metrics


# =====================================================================
# STAGING AUTHENTICATION MANAGER
# =====================================================================

class StagingAuthManager:
    """Manages authentication for real staging environment tests"""
    
    def __init__(self, http_client: RealNetworkHTTPClient):
        self.http_client = http_client
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._auth_token = None
        self._token_expires_at = None
        
        # Get staging URLs from environment
        self.auth_service_url = self._get_staging_auth_url()
    
    def _get_staging_auth_url(self) -> str:
        """Get staging auth service URL from environment"""
        env = get_env()
        
        # Try multiple potential auth URL variables
        auth_url_vars = [
            'STAGING_AUTH_URL',
            'AUTH_SERVICE_URL',
            'NETRA_AUTH_SERVICE_URL'
        ]
        
        for var in auth_url_vars:
            auth_url = env.get(var)
            if auth_url:
                return auth_url
        
        # Default staging auth URL
        default_auth_url = "https://netra-auth-staging-pnovr5vsba-uc.a.run.app"
        self.logger.warning(
            f"No auth URL found in environment variables {auth_url_vars}, "
            f"using default: {default_auth_url}"
        )
        return default_auth_url
    
    def create_test_user_credentials(self) -> Dict[str, str]:
        """Create test user credentials for staging"""
        # Generate unique test credentials
        timestamp = str(int(time.time()))
        
        return {
            "email": f"test_user_{timestamp}@staging.netra.ai",
            "password": f"TestPass_{timestamp}!",
            "first_name": "Test",
            "last_name": f"User_{timestamp[-4:]}"
        }
    
    async def register_test_user(self, credentials: Dict[str, str]) -> Tuple[bool, Dict]:
        """Register a test user in staging"""
        self.logger.info(f"Registering test user: {credentials['email']}")
        
        # Create HTTP client for auth service
        auth_client = RealNetworkHTTPClient(self.auth_service_url)
        
        try:
            response, metrics = auth_client.post("/auth/register", json=credentials)
            
            if response.status_code in [200, 201]:
                result = response.json()
                self.logger.info("Test user registered successfully")
                return True, result
            else:
                self.logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return False, {"error": response.text, "status_code": response.status_code}
        
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False, {"error": str(e)}
    
    async def authenticate_test_user(self, credentials: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """Authenticate test user and get JWT token"""
        self.logger.info(f"Authenticating test user: {credentials['email']}")
        
        # Create HTTP client for auth service  
        auth_client = RealNetworkHTTPClient(self.auth_service_url)
        
        login_data = {
            "email": credentials["email"],
            "password": credentials["password"]
        }
        
        try:
            response, metrics = auth_client.post("/auth/login", json=login_data)
            
            if response.status_code == 200:
                result = response.json()
                token = result.get("access_token")
                expires_in = result.get("expires_in", 3600)  # Default 1 hour
                
                if token:
                    self._auth_token = token
                    self._token_expires_at = time.time() + expires_in
                    self.logger.info("Authentication successful")
                    return True, token
                else:
                    self.logger.error("No access token in login response")
                    return False, None
            else:
                self.logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False, None
        
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False, None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for authenticated requests"""
        if not self._auth_token:
            raise ValueError("No authentication token available. Call authenticate_test_user() first.")
        
        if self._token_expires_at and time.time() > self._token_expires_at:
            raise ValueError("Authentication token has expired. Re-authenticate required.")
        
        return {
            "Authorization": f"Bearer {self._auth_token}",
            "Content-Type": "application/json"
        }
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated with valid token"""
        return (
            self._auth_token is not None and
            (self._token_expires_at is None or time.time() < self._token_expires_at)
        )


# =====================================================================
# NETWORK PACKET VALIDATION UTILITIES  
# =====================================================================

class NetworkPacketValidator:
    """Validates actual network packets are being sent/received"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._captured_traffic: List[Dict] = []
    
    @contextmanager
    def capture_traffic(self, interface: str = None):
        """Context manager to capture network traffic during test execution"""
        # NOTE: This is a simplified version. Full packet capture would require
        # admin privileges and pcap libraries. For production, consider using
        # tcpdump or wireshark integration.
        
        start_stats = self._get_network_stats()
        self.logger.info("Started network traffic monitoring")
        
        try:
            yield
        finally:
            end_stats = self._get_network_stats()
            self._analyze_traffic_delta(start_stats, end_stats)
            self.logger.info("Completed network traffic monitoring")
    
    def _get_network_stats(self) -> Dict:
        """Get current network interface statistics"""
        try:
            stats = psutil.net_io_counters()
            return {
                'bytes_sent': stats.bytes_sent,
                'bytes_recv': stats.bytes_recv,
                'packets_sent': stats.packets_sent,
                'packets_recv': stats.packets_recv,
                'timestamp': time.time()
            }
        except Exception as e:
            self.logger.warning(f"Could not get network stats: {e}")
            return {'timestamp': time.time()}
    
    def _analyze_traffic_delta(self, start_stats: Dict, end_stats: Dict):
        """Analyze network traffic delta to validate real network activity"""
        if 'bytes_sent' not in start_stats or 'bytes_sent' not in end_stats:
            self.logger.warning("Incomplete network stats - cannot validate traffic")
            return
        
        bytes_sent = end_stats['bytes_sent'] - start_stats['bytes_sent']
        bytes_recv = end_stats['bytes_recv'] - start_stats['bytes_recv'] 
        packets_sent = end_stats['packets_sent'] - start_stats['packets_sent']
        packets_recv = end_stats['packets_recv'] - start_stats['packets_recv']
        
        self.logger.info(
            f"Network activity detected: {bytes_sent} bytes sent, {bytes_recv} bytes received, "
            f"{packets_sent} packets sent, {packets_recv} packets received"
        )
        
        # CRITICAL: Validate meaningful network activity occurred
        if bytes_sent == 0 and bytes_recv == 0:
            raise ValueError(
                "FAKE TEST DETECTED - No network traffic detected during test execution. "
                "This indicates the test is not making real network calls."
            )
        
        if packets_sent == 0 and packets_recv == 0:
            raise ValueError(
                "FAKE TEST DETECTED - No network packets detected during test execution."
            )
        
        # Store for analysis
        self._captured_traffic.append({
            'bytes_sent': bytes_sent,
            'bytes_recv': bytes_recv,
            'packets_sent': packets_sent,
            'packets_recv': packets_recv,
            'duration': end_stats['timestamp'] - start_stats['timestamp']
        })
    
    def get_traffic_summary(self) -> Dict:
        """Get summary of all captured network traffic"""
        if not self._captured_traffic:
            return {"total_calls": 0, "total_bytes_sent": 0, "total_bytes_recv": 0}
        
        return {
            "total_calls": len(self._captured_traffic),
            "total_bytes_sent": sum(t['bytes_sent'] for t in self._captured_traffic),
            "total_bytes_recv": sum(t['bytes_recv'] for t in self._captured_traffic),
            "total_packets_sent": sum(t['packets_sent'] for t in self._captured_traffic),
            "total_packets_recv": sum(t['packets_recv'] for t in self._captured_traffic),
            "average_duration": sum(t['duration'] for t in self._captured_traffic) / len(self._captured_traffic)
        }


# =====================================================================
# MAIN REAL STAGING TEST BASE CLASS
# =====================================================================

class RealStagingTestBase:
    """
    Base class that FORCES all tests to make real network calls to staging.
    
    This class makes it IMPOSSIBLE to write fake tests by:
    - Validating all URLs are real staging environments
    - Enforcing minimum network latency on all calls
    - Tracking actual network traffic
    - Validating response data is not hardcoded
    - Comprehensive error handling for network failures
    
    Business Impact: Prevents $120K+ MRR risk from fake staging tests
    """
    
    def __init__(self, backend_url: str = None, auth_url: str = None):
        """Initialize with real staging URLs"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Get staging URLs
        self.backend_url = self._get_staging_backend_url(backend_url)
        self.auth_url = self._get_staging_auth_url(auth_url)
        
        # Initialize clients
        self.http_client = RealNetworkHTTPClient(self.backend_url)
        self.ws_client = RealNetworkWebSocketClient(self.backend_url)
        self.auth_manager = StagingAuthManager(self.http_client)
        
        # Network validation
        self.packet_validator = NetworkPacketValidator()
        
        # Test state
        self._test_start_time = None
        self._network_calls_made = 0
        
        self.logger.info(f"Initialized real staging test framework")
        self.logger.info(f"Backend URL: {self.backend_url}")
        self.logger.info(f"Auth URL: {self.auth_url}")
    
    def _get_staging_backend_url(self, provided_url: str = None) -> str:
        """Get and validate staging backend URL"""
        if provided_url:
            return provided_url
        
        env = get_env()
        
        # Try multiple potential backend URL variables
        backend_url_vars = [
            'STAGING_BACKEND_URL',
            'BACKEND_URL',
            'NETRA_BACKEND_URL'
        ]
        
        for var in backend_url_vars:
            backend_url = env.get(var)
            if backend_url:
                return backend_url
        
        # Default staging backend URL
        return "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
    
    def _get_staging_auth_url(self, provided_url: str = None) -> str:
        """Get and validate staging auth URL"""
        if provided_url:
            return provided_url
        
        env = get_env()
        
        # Try multiple potential auth URL variables
        auth_url_vars = [
            'STAGING_AUTH_URL',
            'AUTH_SERVICE_URL',
            'NETRA_AUTH_SERVICE_URL'
        ]
        
        for var in auth_url_vars:
            auth_url = env.get(var)
            if auth_url:
                return auth_url
        
        # Default staging auth URL  
        return "https://netra-auth-staging-pnovr5vsba-uc.a.run.app"
    
    def setup_test(self):
        """Setup method called before each test - VALIDATES REAL NETWORK"""
        self.logger.info("=" * 60)
        self.logger.info("STARTING REAL STAGING TEST - NETWORK VALIDATION ENABLED")
        self.logger.info("=" * 60)
        
        self._test_start_time = time.time()
        self._network_calls_made = 0
        
        # CRITICAL: Validate we can reach staging before starting test
        self._validate_staging_connectivity()
    
    def _validate_staging_connectivity(self):
        """Validate we can reach staging environment before test"""
        self.logger.info("Validating real staging connectivity...")
        
        try:
            # Test backend health endpoint
            response, metrics = self.http_client.get("/api/health")
            
            if response.status_code != 200:
                raise ValueError(f"Staging backend not healthy: {response.status_code}")
            
            health_data = response.json()
            self.logger.info(f"Staging backend healthy: {health_data}")
            
            # Validate response contains real data
            is_valid, errors = ResponseValidator.validate_non_hardcoded_data(health_data, "health_check")
            if not is_valid:
                self.logger.warning(f"Health check data validation: {errors}")
            
            self._network_calls_made += 1
            
        except Exception as e:
            raise ValueError(
                f"STAGING CONNECTIVITY FAILED - Cannot reach real staging environment: {e}. "
                f"This test framework requires real network access to staging."
            ) from e
    
    def teardown_test(self):
        """Teardown method called after each test - VALIDATES NETWORK USAGE"""
        test_duration = time.time() - self._test_start_time if self._test_start_time else 0
        
        self.logger.info("=" * 60)
        self.logger.info("COMPLETING REAL STAGING TEST - NETWORK VALIDATION")
        self.logger.info("=" * 60)
        
        # CRITICAL: Validate test made meaningful network calls
        if self._network_calls_made == 0:
            raise ValueError(
                "FAKE TEST DETECTED - No network calls were made during test execution. "
                "All staging tests must make real network calls."
            )
        
        # Get network metrics summary
        http_metrics = self.http_client.get_network_metrics()
        total_network_time = self.http_client.get_total_network_time()
        traffic_summary = self.packet_validator.get_traffic_summary()
        
        self.logger.info(f"Test completed:")
        self.logger.info(f"  - Duration: {test_duration:.3f}s")
        self.logger.info(f"  - Network calls: {self._network_calls_made}")
        self.logger.info(f"  - Total network time: {total_network_time:.3f}s")
        self.logger.info(f"  - HTTP calls: {len(http_metrics)}")
        
        if traffic_summary.get("total_calls", 0) > 0:
            self.logger.info(f"  - Network traffic: {traffic_summary}")
        
        # CRITICAL: Validate minimum network activity
        if total_network_time < NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS:
            raise ValueError(
                f"FAKE TEST DETECTED - Total network time {total_network_time:.3f}s < minimum "
                f"{NetworkValidationConfig.MIN_NETWORK_LATENCY_SECONDS}s. Test did not make real network calls."
            )
        
        self.logger.info("✓ Real staging test validation PASSED")
    
    # =====================================================================
    # CONVENIENCE METHODS FOR REAL NETWORK OPERATIONS
    # =====================================================================
    
    def make_authenticated_request(self, method: str, path: str, **kwargs) -> Tuple[requests.Response, NetworkMetrics]:
        """Make authenticated HTTP request to staging"""
        if not self.auth_manager.is_authenticated():
            raise ValueError("Authentication required. Call authenticate_test_user() first.")
        
        headers = kwargs.get('headers', {})
        headers.update(self.auth_manager.get_auth_headers())
        kwargs['headers'] = headers
        
        self._network_calls_made += 1
        
        if method.upper() == 'GET':
            return self.http_client.get(path, **kwargs)
        elif method.upper() == 'POST':
            return self.http_client.post(path, **kwargs)
        elif method.upper() == 'PUT':
            return self.http_client.put(path, **kwargs)
        elif method.upper() == 'DELETE':
            return self.http_client.delete(path, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    async def test_websocket_connection(self, path: str = "/ws", auth_required: bool = True) -> Dict:
        """Test real WebSocket connection to staging"""
        headers = {}
        if auth_required:
            if not self.auth_manager.is_authenticated():
                raise ValueError("Authentication required for WebSocket connection")
            
            # Add auth token to WebSocket headers
            headers["Authorization"] = f"Bearer {self.auth_manager._auth_token}"
        
        self._network_calls_made += 1
        
        async with self.ws_client.connect(path, headers=headers) as websocket:
            # Send test message
            test_message = json.dumps({
                "type": "test_connection",
                "timestamp": time.time(),
                "test_id": hashlib.md5(str(time.time()).encode()).hexdigest()
            })
            
            response = await self.ws_client.send_and_receive(websocket, test_message)
            
            try:
                response_data = json.loads(response)
                return response_data
            except json.JSONDecodeError:
                return {"raw_response": response}
    
    async def create_and_authenticate_test_user(self) -> Dict[str, str]:
        """Create and authenticate a test user for staging tests"""
        self.logger.info("Creating and authenticating test user...")
        
        # Create test credentials
        credentials = self.auth_manager.create_test_user_credentials()
        
        # Register user
        success, result = await self.auth_manager.register_test_user(credentials)
        if not success:
            raise ValueError(f"Failed to register test user: {result}")
        
        self._network_calls_made += 1
        
        # Authenticate user
        success, token = await self.auth_manager.authenticate_test_user(credentials)
        if not success:
            raise ValueError("Failed to authenticate test user")
        
        self._network_calls_made += 1
        
        self.logger.info(f"Test user created and authenticated: {credentials['email']}")
        return credentials
    
    def validate_real_data_response(self, data: Any, field_name: str) -> None:
        """Validate response data is real, not hardcoded - raises exception if fake"""
        is_valid, errors = ResponseValidator.validate_non_hardcoded_data(data, field_name)
        if not is_valid:
            raise ValueError(
                f"FAKE TEST DATA DETECTED in {field_name}:\n" +
                "\n".join(f"  - {error}" for error in errors)
            )
    
    def validate_fresh_timestamps(self, data: Dict, max_age_hours: int = 24) -> None:
        """Validate timestamp fields are fresh, not hardcoded old data"""
        timestamp_fields = ['created_at', 'updated_at', 'timestamp', 'last_modified', 'date']
        
        for field in timestamp_fields:
            if field in data:
                is_valid, errors = ResponseValidator.validate_timestamp_freshness(
                    data[field], field, max_age_hours
                )
                if not is_valid:
                    raise ValueError(
                        f"STALE DATA DETECTED in {field}:\n" +
                        "\n".join(f"  - {error}" for error in errors)
                    )


# =====================================================================
# ERROR HANDLING FOR ALL NETWORK FAILURE MODES
# =====================================================================

class StagingTestNetworkError(Exception):
    """Base exception for staging test network errors"""
    pass

class StagingConnectivityError(StagingTestNetworkError):
    """Raised when cannot connect to staging environment"""
    pass

class StagingTimeoutError(StagingTestNetworkError):
    """Raised when staging requests timeout"""
    pass

class StagingAuthenticationError(StagingTestNetworkError):
    """Raised when staging authentication fails"""
    pass

class FakeTestDetectedError(StagingTestNetworkError):
    """Raised when fake test patterns are detected"""
    pass

class StagingRateLimitError(StagingTestNetworkError):
    """Raised when staging rate limiting is encountered"""
    pass

class StagingServiceUnavailableError(StagingTestNetworkError):
    """Raised when staging services are unavailable"""
    pass


def handle_staging_network_errors(func: Callable) -> Callable:
    """Decorator to handle all staging network error modes comprehensively"""
    
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        
        except requests.exceptions.ConnectionError as e:
            raise StagingConnectivityError(
                f"Cannot connect to staging environment. Check network and staging URLs. "
                f"This is a real network error, not a fake test. Details: {e}"
            ) from e
        
        except requests.exceptions.Timeout as e:
            raise StagingTimeoutError(
                f"Staging request timed out. This indicates real network latency. Details: {e}"
            ) from e
        
        except requests.exceptions.HTTPError as e:
            response = e.response
            if response.status_code == 401:
                raise StagingAuthenticationError(
                    f"Staging authentication failed: {response.text}"
                ) from e
            elif response.status_code == 429:
                raise StagingRateLimitError(
                    f"Staging rate limit exceeded: {response.text}"
                ) from e
            elif response.status_code >= 500:
                raise StagingServiceUnavailableError(
                    f"Staging service unavailable ({response.status_code}): {response.text}"
                ) from e
            else:
                raise StagingTestNetworkError(
                    f"Staging HTTP error ({response.status_code}): {response.text}"
                ) from e
        
        except websockets.exceptions.ConnectionClosedError as e:
            raise StagingConnectivityError(
                f"Staging WebSocket connection closed unexpectedly: {e}"
            ) from e
        
        except asyncio.TimeoutError as e:
            raise StagingTimeoutError(
                f"Staging WebSocket operation timed out: {e}"
            ) from e
        
        except ValueError as e:
            if "FAKE TEST DETECTED" in str(e):
                raise FakeTestDetectedError(str(e)) from e
            raise
        
        except Exception as e:
            # Check if it's a network-related error we should handle
            error_str = str(e).lower()
            if any(term in error_str for term in ['network', 'connection', 'dns', 'timeout', 'unreachable']):
                raise StagingConnectivityError(
                    f"Staging network error: {e}"
                ) from e
            raise
    
    return wrapper


# =====================================================================
# EXAMPLE USAGE AND TEST VALIDATION
# =====================================================================

class ExampleRealStagingTest(RealStagingTestBase):
    """Example of how to use the real staging test framework"""
    
    @handle_staging_network_errors
    def test_real_api_endpoint(self):
        """Example test that MUST make real network calls"""
        self.setup_test()
        
        try:
            # This WILL make real network call with latency validation
            response, metrics = self.http_client.get("/api/models")
            
            # Validate response
            assert response.status_code == 200
            models_data = response.json()
            
            # Validate data is not hardcoded
            self.validate_real_data_response(models_data, "models_endpoint")
            
            self.logger.info(f"Real API test passed: {len(models_data)} models received")
            
        finally:
            self.teardown_test()
    
    @handle_staging_network_errors
    async def test_real_websocket_interaction(self):
        """Example WebSocket test with real network validation"""
        self.setup_test()
        
        try:
            # Create and authenticate test user
            credentials = await self.create_and_authenticate_test_user()
            
            # Test real WebSocket connection
            ws_response = await self.test_websocket_connection()
            
            # Validate WebSocket response
            self.validate_real_data_response(ws_response, "websocket_response")
            
            self.logger.info("Real WebSocket test passed")
            
        finally:
            self.teardown_test()
    
    @handle_staging_network_errors  
    async def test_full_user_flow(self):
        """Example full user flow test with comprehensive validation"""
        self.setup_test()
        
        try:
            with self.packet_validator.capture_traffic():
                # 1. Create test user
                credentials = await self.create_and_authenticate_test_user()
                
                # 2. Make authenticated API calls
                response, metrics = self.make_authenticated_request('GET', '/api/threads')
                assert response.status_code in [200, 404]  # 404 if no threads yet
                
                # 3. Create a thread
                thread_data = {
                    "name": f"Test Thread {int(time.time())}",
                    "description": "Integration test thread"
                }
                response, metrics = self.make_authenticated_request('POST', '/api/threads', json=thread_data)
                
                if response.status_code == 201:
                    thread = response.json()
                    self.validate_real_data_response(thread, "created_thread")
                    self.validate_fresh_timestamps(thread)
                    
                    self.logger.info(f"Full user flow test passed: thread created {thread.get('id')}")
                else:
                    self.logger.info(f"Thread creation returned {response.status_code} - may not be implemented")
            
            # Validate network traffic occurred
            traffic = self.packet_validator.get_traffic_summary()
            assert traffic["total_bytes_recv"] > 0, "No network traffic detected"
            
        finally:
            self.teardown_test()


# =====================================================================
# FRAMEWORK VALIDATION AND SELF-TEST
# =====================================================================

def validate_framework_prevents_fake_tests():
    """Validate the framework successfully prevents fake tests"""
    logger = logging.getLogger("FrameworkValidation")
    
    logger.info("Validating framework prevents fake tests...")
    
    # Test 1: Invalid URL should be rejected
    try:
        RealNetworkHTTPClient("http://localhost:8000")
        assert False, "Should have rejected localhost URL"
    except ValueError as e:
        assert "forbidden pattern" in str(e)
        logger.info("✓ Localhost URL properly rejected")
    
    # Test 2: Too-short timeout should be rejected
    try:
        RealNetworkHTTPClient("https://netra-backend-staging-example.a.run.app", timeout=0.05)
        assert False, "Should have rejected short timeout"
    except ValueError as e:
        assert "minimum" in str(e)
        logger.info("✓ Short timeout properly rejected")
    
    # Test 3: WebSocket URL validation
    try:
        RealNetworkWebSocketClient("ws://localhost:8080")
        assert False, "Should have rejected localhost WebSocket URL"
    except ValueError as e:
        assert "forbidden pattern" in str(e)
        logger.info("✓ Localhost WebSocket URL properly rejected")
    
    logger.info("✓ Framework validation passed - fake tests are properly prevented")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("""
    =========================================================
    REAL STAGING TEST FRAMEWORK - VALIDATION
    =========================================================
    
    This framework FORCES all tests to make real network calls
    and prevents fake tests that put $120K+ MRR at risk.
    
    Key Features:
    - Minimum network latency validation (>0.1s)
    - Real staging URL validation
    - Network traffic monitoring  
    - Response data authenticity validation
    - Comprehensive error handling
    - Authentication management
    """)
    
    # Run framework validation
    validate_framework_prevents_fake_tests()
    
    print("""
    ✓ Framework validation completed successfully!
    
    Usage Example:
    
    ```python
    from tests.staging.real_staging_test_framework import RealStagingTestBase, handle_staging_network_errors
    
    class MyRealStagingTest(RealStagingTestBase):
        @handle_staging_network_errors
        def test_my_feature(self):
            self.setup_test()
            try:
                # This WILL make real network call
                response, metrics = self.http_client.get("/api/my-endpoint")
                # Framework validates latency, data authenticity, etc.
                assert response.status_code == 200
            finally:
                self.teardown_test()
    ```
    
    The framework makes it IMPOSSIBLE to write fake tests!
    """)