"""IP blocking middleware for Cloud Run."""
import ipaddress
import json
from pathlib import Path
from typing import Set

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from netra_backend.app.core.unified_logging import get_logger

logger = get_logger(__name__)

def load_blocked_ips() -> tuple[Set[str], Set[ipaddress.IPv4Network]]:
    """Load blocked IPs from config file."""
    config_path = _get_config_path()
    try:
        config = _load_config_file(config_path)
        return _parse_blocked_config(config)
    except Exception as e:
        return _handle_config_load_error(e)

def _get_config_path() -> Path:
    """Get path to blocked IPs config file."""
    return Path(__file__).parent.parent.parent / "config" / "blocked_ips.json"

def _load_config_file(config_path: Path) -> dict:
    """Load and parse config file."""
    with open(config_path, "r") as f:
        return json.load(f)

def _parse_blocked_config(config: dict) -> tuple[Set[str], Set[ipaddress.IPv4Network]]:
    """Parse blocked IPs and networks from config."""
    blocked_ips = set(config.get("blocked_ips", []))
    blocked_networks = _parse_blocked_networks(config)
    return blocked_ips, blocked_networks

def _parse_blocked_networks(config: dict) -> Set[ipaddress.IPv4Network]:
    """Parse blocked network ranges from config."""
    blocked_networks = set()
    for network_str in config.get("blocked_networks", []):
        network = _try_parse_network(network_str)
        if network:
            blocked_networks.add(network)
    return blocked_networks

def _try_parse_network(network_str: str) -> ipaddress.IPv4Network:
    """Try to parse network string, log error if invalid."""
    try:
        return ipaddress.IPv4Network(network_str)
    except ipaddress.AddressValueError:
        logger.error(f"Invalid network format: {network_str}")
        return None

def _handle_config_load_error(error: Exception) -> tuple[Set[str], Set[ipaddress.IPv4Network]]:
    """Handle config loading error with fallback."""
    logger.error(f"Error loading blocked IPs config: {error}")
    return {"138.197.191.87"}, set()

BLOCKED_IPS, BLOCKED_NETWORKS = load_blocked_ips()


async def ip_blocking_middleware(request: Request, call_next):
    """Block requests from specific IPs."""
    client_ip = _extract_client_ip(request)
    blocking_response = _check_all_ip_blocking(client_ip)
    if blocking_response:
        return blocking_response
    return await call_next(request)

def _check_all_ip_blocking(client_ip: str):
    """Check all IP blocking rules and return response if blocked."""
    ip_block_response = _check_ip_blocking(client_ip)
    network_block_response = _check_network_blocking(client_ip)
    return ip_block_response or network_block_response

def _extract_client_ip(request: Request) -> str:
    """Extract client IP from Cloud Run headers."""
    forwarded_ip = request.headers.get("X-Forwarded-For", "")
    if forwarded_ip:
        return forwarded_ip.split(",")[0].strip()
    return request.client.host

def _check_ip_blocking(client_ip: str) -> JSONResponse:
    """Check if IP is in blocked list."""
    if client_ip in BLOCKED_IPS:
        logger.warning(f"Blocked request from IP: {client_ip}")
        return _create_access_denied_response()
    return None

def _check_network_blocking(client_ip: str) -> JSONResponse:
    """Check if IP is in blocked network ranges."""
    try:
        ip_addr = ipaddress.IPv4Address(client_ip)
        return _check_networks_for_ip(ip_addr, client_ip)
    except ipaddress.AddressValueError:
        return None  # Invalid IP format, let it through

def _check_networks_for_ip(ip_addr: ipaddress.IPv4Address, client_ip: str) -> JSONResponse:
    """Check if IP address is in any blocked networks."""
    for network in BLOCKED_NETWORKS:
        if ip_addr in network:
            logger.warning(f"Blocked request from network: {client_ip}")
            return _create_access_denied_response()
    return None

def _create_access_denied_response() -> JSONResponse:
    """Create standardized access denied response."""
    return JSONResponse(
        status_code=403,
        content={"detail": "Access denied"}
    )