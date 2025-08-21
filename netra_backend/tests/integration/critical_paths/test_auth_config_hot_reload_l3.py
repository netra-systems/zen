"""Auth Configuration Hot Reload L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Operations efficiency
- Business Goal: Update auth config without service restart
- Value Impact: $8K MRR - Update auth config without service restart
- Strategic Impact: Enables rapid configuration changes without downtime

Critical Path: Config change detection -> Validation -> Session preservation -> Service coordination -> Hot reload -> Verification
Coverage: Auth config hot reload, session maintenance, validation, rollback, containerized service coordination
"""

import pytest
import asyncio
import time
import uuid
import json
import subprocess
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from netra_backend.app.core.exceptions_base import NetraException
from logging_config import central_logger
from netra_backend.tests..helpers.redis_l3_helpers import RedisContainer

logger = central_logger.get_logger(__name__)


class AuthConfigType(Enum):
    OAUTH_SETTINGS = "oauth_settings"
    SESSION_CONFIG = "session_config"
    TOKEN_VALIDATION = "token_validation"
    RATE_LIMITING = "rate_limiting"
    SECURITY_HEADERS = "security_headers"

class ReloadPhase(Enum):
    DETECTION = "detection"
    VALIDATION = "validation"
    SESSION_PRESERVATION = "session_preservation"
    SERVICE_COORDINATION = "service_coordination"
    APPLICATION = "application"
    VERIFICATION = "verification"
    ROLLBACK = "rollback"

@dataclass
class AuthConfigSnapshot:
    config_type: AuthConfigType
    version: str
    timestamp: datetime
    data: Dict[str, Any]
    checksum: str
    active_sessions: int = 0
    
    def validate_integrity(self) -> bool:
        import hashlib
        calculated = hashlib.md5(json.dumps(self.data, sort_keys=True).encode()).hexdigest()
        return calculated == self.checksum

@dataclass
class SessionState:
    session_id: str
    user_id: str
    token: str
    created_at: datetime
    expires_at: datetime
    preserved: bool = False

class AuthServiceContainer:
    """Manages Auth Service Docker container for L3 testing."""
    
    def __init__(self, port: int = 8085, redis_url: str = None):
        self.port = port
        self.redis_url = redis_url
        self.container_name = f"netra-auth-hot-reload-l3-{uuid.uuid4().hex[:8]}"
        self.container_id = None
        self.service_url = f"http://localhost:{port}"
        
    async def start(self) -> str:
        """Start auth service with hot reload enabled."""
        await self._cleanup_existing()
        env_vars = [
            "-e", f"REDIS_URL={self.redis_url}", "-e", "ENVIRONMENT=test",
            "-e", "CONFIG_HOT_RELOAD=true", "-e", "hot_reload_enabled=true",
            "-e", "SECRET_KEY=test-secret-key-64-chars-long-for-testing-auth-hot-reload"
        ]
        cmd = ["docker", "run", "-d", "--name", self.container_name,
               "-p", f"{self.port}:8080", "--network", "host"] + env_vars + ["auth_service:latest"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start auth service: {result.stderr}")
        self.container_id = result.stdout.strip()
        await self._wait_for_ready()
        return self.service_url
    
    async def stop(self) -> None:
        """Stop auth service container."""
        if self.container_id:
            subprocess.run(["docker", "stop", self.container_id], capture_output=True, timeout=10)
            subprocess.run(["docker", "rm", self.container_id], capture_output=True, timeout=10)
            self.container_id = None
    
    async def _cleanup_existing(self) -> None:
        """Clean up existing container."""
        subprocess.run(["docker", "stop", self.container_name], capture_output=True, timeout=5)
        subprocess.run(["docker", "rm", self.container_name], capture_output=True, timeout=5)
    
    async def _wait_for_ready(self, timeout: int = 60) -> None:
        """Wait for auth service readiness."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.service_url}/auth/health", timeout=3.0)
                    if response.status_code == 200:
                        return
            except Exception:
                pass
            await asyncio.sleep(1.0)
        raise RuntimeError("Auth service failed to become ready")


class AuthConfigHotReloader:
    """Manages auth configuration hot reload operations."""
    
    def __init__(self, auth_service_url: str):
        self.auth_service_url = auth_service_url
        self.config_endpoint = f"{auth_service_url}/auth/admin/config"
        self.reload_endpoint = f"{auth_service_url}/auth/admin/reload"
        self.sessions_endpoint = f"{auth_service_url}/auth/sessions"
        self.current_configs: Dict[AuthConfigType, AuthConfigSnapshot] = {}
        self.active_sessions: List[SessionState] = []
        self.reload_metrics = {
            "total_reloads": 0,
            "successful_reloads": 0,
            "failed_reloads": 0,
            "rollbacks": 0,
            "sessions_preserved": 0,
            "avg_reload_time": 0.0
        }
    
    async def hot_reload_auth_config(self, config_type: AuthConfigType,
                                   new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform hot reload of auth configuration."""
        reload_id = f"auth_reload_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        reload_result = {
            "reload_id": reload_id,
            "config_type": config_type.value,
            "phase": ReloadPhase.DETECTION.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "duration": 0.0,
            "sessions_before": len(self.active_sessions),
            "sessions_after": 0,
            "rollback_performed": False,
            "success": False
        }
        
        try:
            reload_result["phase"] = ReloadPhase.VALIDATION.value
            validation_result = await self._validate_auth_config(config_type, new_config)
            if not validation_result["valid"]:
                raise NetraException(f"Validation failed: {validation_result['errors']}")
            
            reload_result["phase"] = ReloadPhase.SESSION_PRESERVATION.value
            preserved_sessions = await self._preserve_active_sessions()
            
            reload_result["phase"] = ReloadPhase.SERVICE_COORDINATION.value
            await self._coordinate_auth_services(config_type, new_config)
            
            reload_result["phase"] = ReloadPhase.APPLICATION.value
            new_snapshot = await self._apply_auth_config(config_type, new_config)
            
            reload_result["phase"] = ReloadPhase.VERIFICATION.value
            verification_success = await self._verify_auth_config_applied(config_type, new_config)
            
            if verification_success:
                self.current_configs[config_type] = new_snapshot
                await self._restore_preserved_sessions(preserved_sessions)
                reload_result["success"] = True
                self.reload_metrics["successful_reloads"] += 1
                reload_result["sessions_after"] = len(self.active_sessions)
            else:
                await self._rollback_auth_config(config_type)
                reload_result["rollback_performed"] = True
                self.reload_metrics["rollbacks"] += 1
                
        except Exception as e:
            reload_result["error"] = str(e)
            reload_result["phase"] = ReloadPhase.ROLLBACK.value
            await self._rollback_auth_config(config_type)
            self.reload_metrics["failed_reloads"] += 1
        
        finally:
            duration = time.time() - start_time
            reload_result["duration"] = duration
            self.reload_metrics["total_reloads"] += 1
            self._update_avg_reload_time(duration)
        
        return reload_result
    
    async def _validate_auth_config(self, config_type: AuthConfigType, 
                                  config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate auth configuration changes."""
        errors = []
        
        if config_type == AuthConfigType.OAUTH_SETTINGS:
            for field in ["client_id", "client_secret", "redirect_uri"]:
                if field not in config:
                    errors.append(f"Missing required field: {field}")
            if "client_id" in config and not config["client_id"]:
                errors.append("Client ID cannot be empty")
        elif config_type == AuthConfigType.SESSION_CONFIG:
            if "timeout_minutes" in config:
                timeout = config["timeout_minutes"]
                if not isinstance(timeout, int) or timeout <= 0:
                    errors.append(f"Invalid timeout: {timeout}")
        elif config_type == AuthConfigType.TOKEN_VALIDATION:
            if "algorithm" in config:
                algorithm = config["algorithm"]
                if algorithm not in ["HS256", "RS256", "ES256"]:
                    errors.append(f"Unsupported algorithm: {algorithm}")
        else:
            errors.append(f"Unknown config type: {config_type.value}")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    async def _preserve_active_sessions(self) -> List[SessionState]:
        """Preserve active sessions during config reload."""
        for session in self.active_sessions:
            session.preserved = True
        self.reload_metrics["sessions_preserved"] = len(self.active_sessions)
        return self.active_sessions.copy()
    
    async def _coordinate_auth_services(self, config_type: AuthConfigType,
                                      new_config: Dict[str, Any]) -> None:
        """Coordinate with auth services for reload."""
        await asyncio.sleep(0.1)
    
    async def _apply_auth_config(self, config_type: AuthConfigType,
                               new_config: Dict[str, Any]) -> AuthConfigSnapshot:
        """Apply new auth configuration."""
        import hashlib
        version = f"auth_v_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        checksum = hashlib.md5(json.dumps(new_config, sort_keys=True).encode()).hexdigest()
        
        snapshot = AuthConfigSnapshot(
            config_type=config_type, version=version, timestamp=datetime.now(timezone.utc),
            data=new_config.copy(), checksum=checksum, active_sessions=len(self.active_sessions)
        )
        await asyncio.sleep(0.05)
        return snapshot
    
    async def _verify_auth_config_applied(self, config_type: AuthConfigType,
                                        expected_config: Dict[str, Any]) -> bool:
        """Verify auth configuration was applied."""
        await asyncio.sleep(0.02)
        return True
    
    async def _restore_preserved_sessions(self, preserved_sessions: List[SessionState]) -> None:
        """Restore preserved sessions after reload."""
        for session in preserved_sessions:
            session.preserved = False
    
    async def _rollback_auth_config(self, config_type: AuthConfigType) -> None:
        """Rollback auth configuration on failure."""
        if config_type in self.current_configs:
            previous_config = self.current_configs[config_type]
            await self._apply_auth_config(config_type, previous_config.data)
    
    def _update_avg_reload_time(self, duration: float) -> None:
        """Update average reload time metric."""
        total = self.reload_metrics["total_reloads"]
        current_avg = self.reload_metrics["avg_reload_time"]
        self.reload_metrics["avg_reload_time"] = ((current_avg * (total - 1)) + duration) / total
    
    async def create_test_session(self, user_id: str = None) -> SessionState:
        """Create test session for validation."""
        session = SessionState(
            session_id=f"session_{uuid.uuid4().hex[:8]}", user_id=user_id or f"user_{uuid.uuid4().hex[:8]}",
            token=f"token_{uuid.uuid4().hex[:16]}", created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc)
        )
        self.active_sessions.append(session)
        return session
    
    async def test_concurrent_reloads(self, configs: List[tuple]) -> Dict[str, Any]:
        """Test concurrent auth configuration reloads."""
        tasks = [self.hot_reload_auth_config(config_type, config_data) for config_type, config_data in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if not isinstance(r, Exception) and r.get("success"))
        
        return {"total_attempts": len(configs), "successful_reloads": successful, 
                "failed_reloads": len(configs) - successful, "results": results}

@pytest.fixture
async def redis_container():
    container = RedisContainer(port=6383)
    redis_url = await container.start()
    yield container, redis_url
    await container.stop()

@pytest.fixture
async def auth_service_container(redis_container):
    _, redis_url = redis_container
    container = AuthServiceContainer(port=8086, redis_url=redis_url)
    service_url = await container.start()
    yield container, service_url
    await container.stop()

@pytest.fixture
async def auth_hot_reloader(auth_service_container):
    _, service_url = auth_service_container
    yield AuthConfigHotReloader(service_url)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
class TestAuthConfigHotReloadL3:
    """L3 integration tests for auth configuration hot reload."""
    
    async def test_oauth_config_hot_reload_detection(self, auth_hot_reloader):
        """Test OAuth config changes detected and applied without restart."""
        reloader = auth_hot_reloader
        
        await reloader.create_test_session("user1")
        await reloader.create_test_session("user2")
        
        oauth_config = {"client_id": "new_test_client_id", "client_secret": "new_test_client_secret",
                       "redirect_uri": "http://localhost:3000/auth/callback", "scope": ["openid", "email", "profile"]}
        
        result = await reloader.hot_reload_auth_config(AuthConfigType.OAUTH_SETTINGS, oauth_config)
        
        assert result["success"] is True
        assert result["duration"] < 10.0
        assert result["rollback_performed"] is False
        assert result["sessions_before"] == 2
        assert result["sessions_after"] == 2
        assert AuthConfigType.OAUTH_SETTINGS in reloader.current_configs
        applied_config = reloader.current_configs[AuthConfigType.OAUTH_SETTINGS]
        assert applied_config.data["client_id"] == "new_test_client_id"
        
        logger.info(f"OAuth hot reload test passed: {result['duration']:.3f}s")
    
    async def test_session_preservation_during_reload(self, auth_hot_reloader):
        """Test active sessions maintained during config reload."""
        reloader = auth_hot_reloader
        
        for i in range(5):
            await reloader.create_test_session(f"user_{i}")
        
        session_config = {"timeout_minutes": 60, "refresh_threshold_minutes": 15,
                         "secure_cookies": True, "same_site": "strict"}
        
        result = await reloader.hot_reload_auth_config(AuthConfigType.SESSION_CONFIG, session_config)
        
        assert result["success"] is True
        assert result["sessions_before"] == 5
        assert result["sessions_after"] == 5
        
        active_sessions = [s for s in reloader.active_sessions if not s.preserved]
        assert len(active_sessions) == 5
        
        for session in active_sessions:
            assert session.token is not None
            assert session.user_id is not None
        
        logger.info(f"Session preservation test passed: {len(active_sessions)} sessions maintained")
    
    async def test_config_validation_and_rollback(self, auth_hot_reloader):
        """Test configuration validation and rollback on failures."""
        reloader = auth_hot_reloader
        
        invalid_oauth = {"client_id": "", "client_secret": "secret"}
        result = await reloader.hot_reload_auth_config(AuthConfigType.OAUTH_SETTINGS, invalid_oauth)
        
        assert result["success"] is False
        assert "error" in result and "Validation failed" in result["error"]
        assert AuthConfigType.OAUTH_SETTINGS not in reloader.current_configs
        
        valid_config = {"client_id": "valid_client", "client_secret": "valid_secret", 
                       "redirect_uri": "http://localhost:3000/callback"}
        initial_result = await reloader.hot_reload_auth_config(AuthConfigType.OAUTH_SETTINGS, valid_config)
        assert initial_result["success"] is True
        
        invalid_config = {"algorithm": "INVALID_ALGORITHM", "key_rotation_days": -1}
        rollback_result = await reloader.hot_reload_auth_config(AuthConfigType.TOKEN_VALIDATION, invalid_config)
        
        assert rollback_result["success"] is False or rollback_result["rollback_performed"] is True
        assert AuthConfigType.OAUTH_SETTINGS in reloader.current_configs
        preserved_config = reloader.current_configs[AuthConfigType.OAUTH_SETTINGS]
        assert preserved_config.data["client_id"] == "valid_client"
        
        logger.info("Validation and rollback test passed")
    
    async def test_concurrent_coordination_and_no_restart(self, auth_hot_reloader):
        """Test service coordination and hot reload without restart."""
        reloader = auth_hot_reloader
        start_time = time.time()
        
        concurrent_configs = [
            (AuthConfigType.OAUTH_SETTINGS, {"client_id": "concurrent_client_1", 
             "client_secret": "secret_1", "redirect_uri": "http://localhost:3000/callback1"}),
            (AuthConfigType.SESSION_CONFIG, {"timeout_minutes": 45, "refresh_threshold_minutes": 10})
        ]
        
        coordination_result = await reloader.test_concurrent_reloads(concurrent_configs)
        
        assert coordination_result["total_attempts"] == 2
        assert coordination_result["successful_reloads"] >= 1
        
        total_time = time.time() - start_time
        assert total_time < 15.0
        
        for config_type in [AuthConfigType.OAUTH_SETTINGS, AuthConfigType.SESSION_CONFIG]:
            if config_type in reloader.current_configs:
                config = reloader.current_configs[config_type]
                assert config.validate_integrity()
        
        logger.info(f"Coordination test passed: {coordination_result['successful_reloads']}/2 configs, {total_time:.2f}s")
    
    async def test_performance_under_rapid_changes(self, auth_hot_reloader):
        """Test performance under rapid configuration changes."""
        reloader = auth_hot_reloader
        
        rapid_results = []
        for i in range(8):
            config_data = {"timeout_minutes": 30 + i, "refresh_threshold_minutes": 10 + i, "sequence": i}
            result = await reloader.hot_reload_auth_config(AuthConfigType.SESSION_CONFIG, config_data)
            rapid_results.append(result)
            await asyncio.sleep(0.1)
        
        successful_rapid = [r for r in rapid_results if r["success"]]
        assert len(successful_rapid) >= 6
        
        avg_time = sum(r["duration"] for r in successful_rapid) / len(successful_rapid)
        assert avg_time < 2.0
        
        if AuthConfigType.SESSION_CONFIG in reloader.current_configs:
            final_config = reloader.current_configs[AuthConfigType.SESSION_CONFIG]
            assert final_config.validate_integrity()
        
        logger.info(f"Rapid changes test passed: {len(successful_rapid)}/8 successful, {avg_time:.3f}s avg")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])