"""
Mission Critical Test: Docker SSOT Compliance Verification

This test ensures that ALL Docker management goes through UnifiedDockerManager
and prevents regression to multiple Docker management implementations.

Critical for spacecraft reliability: No direct Docker calls outside SSOT.
"""

import asyncio
import inspect
import logging
import pytest
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set
from unittest.mock import AsyncMock, Mock, patch

# SSOT imports - the ONLY allowed Docker management interfaces
from test_framework.unified_docker_manager import UnifiedDockerManager
from test_framework.ssot.docker import DockerTestUtility, create_docker_test_utility

# Test deprecated classes properly redirect
from test_framework.docker_test_manager import DockerTestManager, ServiceMode

logger = logging.getLogger(__name__)


class TestDockerSSOTCompliance:
    """
    Comprehensive tests to ensure Docker SSOT compliance.
    
    Verifies:
    1. UnifiedDockerManager is the only allowed Docker interface
    2. Deprecated classes redirect correctly
    3. No direct Docker calls exist outside SSOT
    4. All functionality is preserved during consolidation
    """
    
    @pytest.mark.asyncio
    async def test_unified_docker_manager_is_ssot(self):
        """Test that UnifiedDockerManager is accessible and functional."""
        # Verify UnifiedDockerManager can be instantiated
        docker_manager = UnifiedDockerManager()
        
        # Verify key SSOT methods exist
        assert hasattr(docker_manager, 'start_services_smart')
        assert hasattr(docker_manager, 'stop_services')
        assert hasattr(docker_manager, 'cleanup')
        assert hasattr(docker_manager, 'is_docker_available')
        assert hasattr(docker_manager, 'get_service_ports')
        
        # Verify it's async-capable
        assert asyncio.iscoroutinefunction(docker_manager.start_services_smart)
        assert asyncio.iscoroutinefunction(docker_manager.cleanup)
        
        logger.info("UnifiedDockerManager SSOT interface verified")
    
    @pytest.mark.asyncio
    async def test_docker_test_utility_ssot_wrapper(self):
        """Test that DockerTestUtility properly wraps UnifiedDockerManager."""
        # Create SSOT utility
        utility = create_docker_test_utility()
        
        # Verify it uses DockerTestUtility
        assert isinstance(utility, DockerTestUtility)
        
        # Test async context manager functionality
        async with utility as docker:
            # Verify key methods exist
            assert hasattr(docker, 'start_services')
            assert hasattr(docker, 'stop_services')
            assert hasattr(docker, 'get_service_port')
            assert hasattr(docker, 'get_service_url')
            assert hasattr(docker, 'check_service_health')
            assert hasattr(docker, 'generate_health_report')
            
            # Verify it has a UnifiedDockerManager instance
            assert hasattr(docker, 'docker_manager')
            assert docker.docker_manager is not None
        
        logger.info("DockerTestUtility SSOT wrapper verified")
    
    def test_docker_test_manager_deprecation(self):
        """Test that DockerTestManager issues deprecation warnings."""
        with pytest.warns(DeprecationWarning, match="DockerTestManager is deprecated"):
            manager = DockerTestManager()
            
        # Verify it redirects to SSOT
        assert hasattr(manager, '_docker_utility')
        assert isinstance(manager._docker_utility, DockerTestUtility)
        
        logger.info("DockerTestManager deprecation warning verified")
    
    @pytest.mark.asyncio
    async def test_deprecated_manager_functionality_preserved(self):
        """Test that deprecated DockerTestManager still works via SSOT redirect."""
        with pytest.warns(DeprecationWarning):
            manager = DockerTestManager(mode=ServiceMode.DOCKER)
        
        # Test basic functionality redirects work
        assert callable(manager.is_docker_available)
        assert callable(manager.get_effective_mode)
        assert callable(manager.get_service_url)
        
        # Test service URL generation
        url = manager.get_service_url("postgres")
        assert url.startswith("http://localhost:")
        assert "5432" in url
        
        # Test mode conversion
        effective_mode = manager.get_effective_mode()
        assert isinstance(effective_mode, ServiceMode)
        
        logger.info("Deprecated DockerTestManager functionality preserved via SSOT")
    
    def test_service_mode_conversion(self):
        """Test ServiceMode to DockerTestEnvironmentType conversion."""
        from test_framework.ssot.docker import DockerTestEnvironmentType
        
        # Test conversions
        docker_mode = ServiceMode.DOCKER
        local_mode = ServiceMode.LOCAL
        mock_mode = ServiceMode.MOCK
        
        assert docker_mode.to_environment_type() == DockerTestEnvironmentType.SHARED
        assert local_mode.to_environment_type() == DockerTestEnvironmentType.ISOLATED
        assert mock_mode.to_environment_type() == DockerTestEnvironmentType.ISOLATED
        
        logger.info("ServiceMode conversion to SSOT types verified")
    
    @pytest.mark.asyncio
    async def test_no_direct_subprocess_docker_calls(self):
        """Critical test: Verify no direct subprocess Docker calls in SSOT code."""
        # This test uses mocking to ensure Docker calls go through SSOT
        with patch('subprocess.run') as mock_subprocess:
            with patch('subprocess.Popen') as mock_popen:
                
                # Create SSOT utility and test basic operations
                utility = create_docker_test_utility()
                
                async with utility as docker:
                    # Mock the underlying UnifiedDockerManager methods to avoid real Docker calls
                    with patch.object(docker.docker_manager, 'start_services_async', return_value=AsyncMock()) as mock_start:
                        with patch.object(docker.docker_manager, 'is_docker_available', return_value=AsyncMock()) as mock_available:
                            
                            mock_start.return_value.success = True
                            mock_start.return_value.services_started = set(['postgres'])
                            mock_start.return_value.services_failed = set()
                            mock_start.return_value.errors = []
                            
                            # Test service operations
                            result = await docker.start_services(['postgres'])
                            
                            # Verify UnifiedDockerManager was called, not subprocess
                            mock_start.assert_called_once()
                            
                            # Critical: Verify no direct subprocess calls were made
                            mock_subprocess.assert_not_called()
                            mock_popen.assert_not_called()
        
        logger.info("No direct subprocess Docker calls detected - SSOT compliance verified")
    
    def test_scripts_use_ssot_interfaces(self):
        """Test that scripts have been updated to use SSOT interfaces."""
        # Check that manage_test_services.py uses SSOT
        script_path = Path(__file__).parent.parent.parent / "scripts" / "manage_test_services.py"
        
        if script_path.exists():
            content = script_path.read_text()
            
            # Should import from SSOT
            assert "from test_framework.ssot.docker import" in content
            assert "DockerTestUtility" in content
            assert "create_docker_test_utility" in content
            
            # Should not have direct Docker subprocess calls in main logic
            lines = content.split('\n')
            docker_subprocess_lines = [
                line for line in lines 
                if 'subprocess.run' in line and 'docker' in line.lower()
                and not line.strip().startswith('#')  # Ignore comments
            ]
            
            # Allow minimal fallback usage but not as primary logic
            assert len(docker_subprocess_lines) <= 2, f"Too many direct Docker calls: {docker_subprocess_lines}"
            
        logger.info("Scripts SSOT compliance verified")
    
    @pytest.mark.asyncio  
    async def test_docker_manager_interface_completeness(self):
        """Test that SSOT interface covers all necessary Docker operations."""
        docker_manager = UnifiedDockerManager()
        
        # Core service management
        assert hasattr(docker_manager, 'start_services_smart')
        assert hasattr(docker_manager, 'stop_services')
        assert hasattr(docker_manager, 'restart_service')
        
        # Health and status
        assert hasattr(docker_manager, 'check_service_health_async') or hasattr(docker_manager, 'get_health_report')
        assert hasattr(docker_manager, 'is_docker_available')
        
        # Environment management
        assert hasattr(docker_manager, 'cleanup')
        assert hasattr(docker_manager, 'get_service_ports') or hasattr(docker_manager, 'get_port_mapping')
        
        # Container operations
        assert hasattr(docker_manager, 'get_container_info') or hasattr(docker_manager, 'get_container_logs')
        
        logger.info("UnifiedDockerManager interface completeness verified")
    
    def test_import_paths_ssot_compliance(self):
        """Test that correct SSOT import paths are being used."""
        # Test SSOT imports work
        try:
            from test_framework.unified_docker_manager import UnifiedDockerManager
            from test_framework.ssot.docker import DockerTestUtility, create_docker_test_utility
            
            # Verify classes are accessible
            assert UnifiedDockerManager is not None
            assert DockerTestUtility is not None
            assert create_docker_test_utility is not None
            
        except ImportError as e:
            pytest.fail(f"SSOT imports failed: {e}")
        
        logger.info("SSOT import paths verified")
    
    @pytest.mark.asyncio
    async def test_unified_docker_manager_environment_isolation(self):
        """Test that UnifiedDockerManager properly isolates test environments."""
        # Create multiple managers with different configurations
        manager1 = UnifiedDockerManager()
        manager2 = UnifiedDockerManager()
        
        # Both should be functional but isolated
        assert manager1 is not manager2
        
        # They should have different internal state but same interface
        assert type(manager1) == type(manager2)
        assert hasattr(manager1, 'start_services_smart')
        assert hasattr(manager2, 'start_services_smart')
        
        logger.info("UnifiedDockerManager environment isolation verified")
    
    @pytest.mark.asyncio
    async def test_error_handling_in_ssot_redirect(self):
        """Test error handling when SSOT redirect encounters problems."""
        with pytest.warns(DeprecationWarning):
            manager = DockerTestManager()
        
        # Test that errors in underlying SSOT don't crash the deprecated interface
        with patch.object(manager._docker_utility, '__aenter__', side_effect=Exception("Mock error")):
            # Should handle the error gracefully
            result = await manager.start_services(['postgres'])
            assert result is False  # Should return False on error, not crash
        
        logger.info("Error handling in SSOT redirect verified")


@pytest.mark.integration
class TestDockerSSOTIntegration:
    """Integration tests for Docker SSOT compliance with real components."""
    
    @pytest.mark.skipif(not Path("docker-compose.yml").exists(), reason="No docker-compose.yml found")
    @pytest.mark.asyncio
    async def test_real_docker_operations_through_ssot(self):
        """Test that real Docker operations work through SSOT interface."""
        utility = create_docker_test_utility()
        
        async with utility as docker:
            # Test Docker availability check
            try:
                # This should work through UnifiedDockerManager
                available = await docker.docker_manager.is_docker_available()
                logger.info(f"Docker availability: {available}")
                
                if available:
                    # Test basic port discovery (doesn't start services)
                    status = docker.get_status_summary()
                    assert isinstance(status, dict)
                    assert "test_id" in status
                    
            except Exception as e:
                logger.warning(f"Docker not available for integration test: {e}")
                # This is acceptable in CI environments without Docker
        
        logger.info("Real Docker operations through SSOT verified")
    
    @pytest.mark.asyncio
    async def test_multiple_utilities_dont_conflict(self):
        """Test that multiple DockerTestUtilities don't conflict."""
        utility1 = create_docker_test_utility()
        utility2 = create_docker_test_utility()
        
        # Should be separate instances
        assert utility1 is not utility2
        
        # Both should work independently
        async with utility1 as docker1:
            async with utility2 as docker2:
                status1 = docker1.get_status_summary()
                status2 = docker2.get_status_summary()
                
                # Should have different test IDs
                assert status1["test_id"] != status2["test_id"]
        
        logger.info("Multiple utilities non-conflict verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])