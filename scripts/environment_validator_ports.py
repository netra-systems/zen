"""
Port Availability Validation Module
Checks availability of required ports for development services.
"""

import socket
import asyncio
from typing import Dict, List, Any, Tuple
from contextlib import asynccontextmanager


class PortValidator:
    """Port availability validation logic."""
    
    def __init__(self):
        """Initialize port validator."""
        self.required_ports = self._define_required_ports()
        
    async def validate_required_ports(self) -> Dict[str, Any]:
        """Validate all required port availability."""
        results = {
            "status": "success",
            "ports": {},
            "conflicts": [],
            "recommendations": []
        }
        
        await self._check_all_ports(results)
        self._analyze_port_conflicts(results)
        self._update_port_status(results)
        
        return results
    
    def _define_required_ports(self) -> Dict[int, Dict[str, Any]]:
        """Define required ports with service information."""
        return {
            3000: {
                "service": "Frontend (Next.js)",
                "description": "React frontend development server",
                "critical": True,
                "alternatives": [3001, 3002, 3010]
            },
            8000: {
                "service": "Backend (FastAPI)",
                "description": "Python API server",
                "critical": True,
                "alternatives": [8001, 8002, 8080]
            },
            5432: {
                "service": "PostgreSQL",
                "description": "Main database server",
                "critical": True,
                "alternatives": [5433, 5434]
            },
            5433: {
                "service": "PostgreSQL Dev",
                "description": "Development database server",
                "critical": False,
                "alternatives": [5432, 5434]
            },
            8443: {
                "service": "ClickHouse HTTPS",
                "description": "Analytics database (secure)",
                "critical": False,
                "alternatives": [8123, 9000]
            },
            6379: {
                "service": "Redis",
                "description": "Cache and session store",
                "critical": False,
                "alternatives": [6380, 6381]
            },
            9000: {
                "service": "ClickHouse Native",
                "description": "Analytics database (native)",
                "critical": False,
                "alternatives": [8443, 8123]
            }
        }
    
    async def _check_all_ports(self, results: Dict[str, Any]) -> None:
        """Check availability of all required ports."""
        port_tasks = [
            self._check_port_availability(port, config)
            for port, config in self.required_ports.items()
        ]
        
        port_results = await asyncio.gather(*port_tasks, return_exceptions=True)
        
        for (port, config), result in zip(self.required_ports.items(), port_results):
            if isinstance(result, Exception):
                results["ports"][port] = self._create_error_result(port, config, result)
            else:
                results["ports"][port] = result
    
    async def _check_port_availability(self, port: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check if specific port is available."""
        port_result = {
            "port": port,
            "service": config["service"],
            "available": False,
            "listening": False,
            "process_info": None,
            "alternatives": config.get("alternatives", []),
            "critical": config.get("critical", False)
        }
        
        await self._test_port_binding(port_result)
        await self._check_port_listener(port_result)
        
        return port_result
    
    async def _test_port_binding(self, port_result: Dict[str, Any]) -> None:
        """Test if port can be bound (is available)."""
        port = port_result["port"]
        
        try:
            # Test both IPv4 and IPv6
            for family in [socket.AF_INET, socket.AF_INET6]:
                sock = socket.socket(family, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                
                try:
                    host = "127.0.0.1" if family == socket.AF_INET else "::1"
                    sock.bind((host, port))
                    port_result["available"] = True
                    break
                except OSError:
                    continue
                finally:
                    sock.close()
                    
        except Exception:
            port_result["available"] = False
    
    async def _check_port_listener(self, port_result: Dict[str, Any]) -> None:
        """Check if something is already listening on port."""
        port = port_result["port"]
        
        try:
            # Attempt connection to see if service is listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            result = sock.connect_ex(("127.0.0.1", port))
            port_result["listening"] = (result == 0)
            
            sock.close()
            
        except Exception:
            port_result["listening"] = False
    
    def _create_error_result(self, port: int, config: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Create error result for port check failure."""
        return {
            "port": port,
            "service": config["service"],
            "available": False,
            "listening": False,
            "error": str(error),
            "alternatives": config.get("alternatives", []),
            "critical": config.get("critical", False)
        }
    
    def _analyze_port_conflicts(self, results: Dict[str, Any]) -> None:
        """Analyze port conflicts and suggest solutions."""
        for port, port_result in results["ports"].items():
            if not port_result["available"] and port_result["critical"]:
                results["conflicts"].append({
                    "port": port,
                    "service": port_result["service"],
                    "alternatives": port_result["alternatives"]
                })
    
    def _update_port_status(self, results: Dict[str, Any]) -> None:
        """Update overall port validation status."""
        critical_conflicts = [c for c in results["conflicts"] if self._is_critical_conflict(c)]
        
        if critical_conflicts:
            results["status"] = "error"
            results["summary"] = f"{len(critical_conflicts)} critical port conflicts"
            self._add_port_recommendations(results, critical_conflicts)
        elif results["conflicts"]:
            results["status"] = "warning"
            results["summary"] = f"{len(results['conflicts'])} port conflicts (non-critical)"
            self._add_port_recommendations(results, results["conflicts"])
        else:
            results["status"] = "success"
            results["summary"] = "All required ports available"
    
    def _is_critical_conflict(self, conflict: Dict[str, Any]) -> bool:
        """Check if port conflict is critical."""
        port = conflict["port"]
        return self.required_ports.get(port, {}).get("critical", False)
    
    def _add_port_recommendations(self, results: Dict[str, Any], conflicts: List[Dict[str, Any]]) -> None:
        """Add recommendations for resolving port conflicts."""
        for conflict in conflicts:
            port = conflict["port"]
            service = conflict["service"]
            alternatives = conflict["alternatives"]
            
            results["recommendations"].append(f"Port {port} ({service}) in use")
            
            if alternatives:
                alt_list = ", ".join(map(str, alternatives[:3]))
                results["recommendations"].append(f"Try alternative ports: {alt_list}")
            
            results["recommendations"].append(f"Use --dynamic flag with dev_launcher.py")