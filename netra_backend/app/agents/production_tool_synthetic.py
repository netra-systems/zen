"""Synthetic data tool execution handlers."""
from typing import Any, Dict, Optional

from netra_backend.app.core.reliability_utils import create_default_tool_result
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class SyntheticToolExecutor:
    """Executes synthetic data tools"""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
    
    async def execute(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute synthetic data tool if applicable"""
        synthetic_tools = {
            "generate_synthetic_data_batch": self._execute_synthetic_data_batch,
            "validate_synthetic_data": self._execute_validate_synthetic_data,
            "store_synthetic_data": self._execute_store_synthetic_data
        }
        if self.tool_name in synthetic_tools:
            return await synthetic_tools[self.tool_name](parameters)
        return None
    
    async def _execute_synthetic_data_batch(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synthetic data batch generation via real service"""
        try:
            batch_size = parameters.get("batch_size", 100)
            config = self._create_batch_config(batch_size)
            batch = await self._generate_batch(config, batch_size)
            return self._create_batch_success_response(batch, batch_size)
        except Exception as e:
            return self._create_batch_error_response(e)
    
    def _create_batch_config(self, batch_size: int) -> Any:
        """Create configuration for batch generation"""
        return type('Config', (), {'num_logs': batch_size})()
    
    async def _generate_batch(self, config: Any, batch_size: int) -> Any:
        """Generate batch using synthetic data service"""
        from netra_backend.app.services.synthetic_data import synthetic_data_service
        return await synthetic_data_service.generate_batch(config, batch_size)
    
    def _create_batch_success_response(self, batch: Any, batch_size: int) -> Dict[str, Any]:
        """Create success response for batch generation"""
        return {
            "success": True,
            "data": batch,
            "metadata": {"batch_size": batch_size, "tool": self.tool_name, "service": "synthetic_data"}
        }
    
    def _create_batch_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create error response for batch generation failure"""
        logger.error(f"Synthetic data batch generation failed: {error}")
        return create_default_tool_result(
            self.tool_name, False, 
            error=f"Failed to generate synthetic data: {str(error)}",
            metadata={"service": "synthetic_data"}
        )
    
    async def _execute_validate_synthetic_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate synthetic data"""
        try:
            data = parameters.get('data', [])
            validation = await self._validate_data(data)
            return self._create_validation_success_response(validation)
        except Exception as e:
            return self._create_validation_error_response(e)
    
    async def _validate_data(self, data: list) -> Any:
        """Validate data using synthetic data service"""
        from netra_backend.app.services.synthetic_data import validate_data
        return validate_data(data)
    
    def _create_validation_success_response(self, validation: Any) -> Dict[str, Any]:
        """Create success response for validation"""
        return {
            "success": True,
            "data": validation,
            "message": "Data validation completed",
            "metadata": {"tool": self.tool_name, "service": "synthetic_data"}
        }
    
    def _create_validation_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create error response for validation failure"""
        logger.error(f"Data validation failed: {error}")
        return {"success": False, "error": str(error), "metadata": {"tool": self.tool_name}}

    async def _execute_store_synthetic_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Store synthetic data"""
        try:
            data = parameters.get('data', [])
            table_name = parameters.get('table_name', 'synthetic_data')
            result = await self._store_data(data, table_name)
            return self._create_store_success_response(result)
        except Exception as e:
            return self._create_store_error_response(e)
    
    async def _store_data(self, data: list, table_name: str) -> Any:
        """Store data using synthetic data service"""
        from netra_backend.app.services.synthetic_data import synthetic_data_service
        return await synthetic_data_service.ingest_batch(data, table_name)
    
    def _create_store_success_response(self, result: Any) -> Dict[str, Any]:
        """Create success response for data storage"""
        return {
            "success": True,
            "data": result,
            "message": "Data stored successfully",
            "metadata": {"tool": self.tool_name, "service": "synthetic_data"}
        }
    
    def _create_store_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create error response for storage failure"""
        logger.error(f"Data storage failed: {error}")
        return {"success": False, "error": str(error), "metadata": {"tool": self.tool_name}}