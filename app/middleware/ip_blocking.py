"""IP blocking middleware for Cloud Run."""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Set
import ipaddress
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

def load_blocked_ips() -> tuple[Set[str], Set[ipaddress.IPv4Network]]:
    """Load blocked IPs from config file."""
    config_path = Path(__file__).parent.parent.parent / "config" / "blocked_ips.json"
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            
        blocked_ips = set(config.get("blocked_ips", []))
        blocked_networks = set()
        
        for network_str in config.get("blocked_networks", []):
            try:
                blocked_networks.add(ipaddress.IPv4Network(network_str))
            except ipaddress.AddressValueError:
                logger.error(f"Invalid network format: {network_str}")
                
        return blocked_ips, blocked_networks
    except Exception as e:
        logger.error(f"Error loading blocked IPs config: {e}")
        # Fallback to hardcoded values
        return {"138.197.191.87"}, set()

BLOCKED_IPS, BLOCKED_NETWORKS = load_blocked_ips()


async def ip_blocking_middleware(request: Request, call_next):
    """Block requests from specific IPs."""
    # Get client IP from Cloud Run headers
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
    )
    
    # Check if IP is blocked
    if client_ip in BLOCKED_IPS:
        logger.warning(f"Blocked request from IP: {client_ip}")
        return JSONResponse(
            status_code=403,
            content={"detail": "Access denied"}
        )
    
    # Check if IP is in blocked network ranges
    try:
        ip_addr = ipaddress.IPv4Address(client_ip)
        for network in BLOCKED_NETWORKS:
            if ip_addr in network:
                logger.warning(f"Blocked request from network: {client_ip}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied"}
                )
    except ipaddress.AddressValueError:
        pass  # Invalid IP format, let it through
    
    response = await call_next(request)
    return response