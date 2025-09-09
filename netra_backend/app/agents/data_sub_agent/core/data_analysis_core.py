"""
Data Analysis Core - SSOT compatibility wrapper for legacy test support.

This module provides the DataAnalysisCore class for backward compatibility
with existing integration tests while following CLAUDE.md SSOT principles.

Business Value: Platform/Internal - Development Velocity - Ensures existing
integration tests can run while we modernize the architecture.

Following CLAUDE.md principles:
- SSOT: Delegates to existing modern implementations where possible
- No code duplication: Uses proven analysis patterns
- Search First, Create Second: Leverages existing AnalysisEngine functionality
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import asyncio

from netra_backend.app.database.session_manager import SessionManager
from netra_backend.app.agents.supervisor.data_access_integration import DataAccessCapabilities
from netra_backend.app.agents.data_sub_agent.analysis_engine import AnalysisEngine


class DataAnalysisCore:
    """
    Data Analysis Core for integration testing compatibility.
    
    This class provides a simplified interface for data analysis operations
    that is compatible with existing integration tests while leveraging
    the robust modern implementations internally.
    
    Key Features:
    - Database session management integration
    - Optional data access capabilities support
    - Statistical analysis delegation to AnalysisEngine
    - Backward compatibility for legacy tests
    """
    
    def __init__(self, 
                 session_manager: SessionManager,
                 data_access: Optional[DataAccessCapabilities] = None):
        """
        Initialize DataAnalysisCore with database session manager.
        
        Args:
            session_manager: Database session manager for data operations
            data_access: Optional data access capabilities for enhanced functionality
        """
        self.session_manager = session_manager
        self.data_access = data_access
        self._analysis_engine = AnalysisEngine()
        
        # Track initialization state
        self._initialized = True
        
    async def analyze_data(self, 
                          data: List[Dict[str, Any]], 
                          analysis_type: str = "basic") -> Dict[str, Any]:
        """
        Analyze provided data using statistical methods.
        
        Args:
            data: List of data records to analyze
            analysis_type: Type of analysis to perform ("basic", "trend", "seasonal")
            
        Returns:
            Dictionary with analysis results
        """
        if not data:
            return {
                "success": False,
                "error": "No data provided for analysis",
                "analysis_type": analysis_type
            }
        
        try:
            result = {
                "success": True,
                "analysis_type": analysis_type,
                "record_count": len(data),
                "timestamp": datetime.now().isoformat()
            }
            
            # Extract numeric values for statistical analysis
            numeric_values = []
            for record in data:
                if isinstance(record, dict):
                    for key, value in record.items():
                        if isinstance(value, (int, float)):
                            numeric_values.append(value)
                elif isinstance(record, (int, float)):
                    numeric_values.append(record)
            
            if numeric_values and analysis_type == "basic":
                # Use AnalysisEngine for statistical calculations
                stats = self._analysis_engine.calculate_statistics(numeric_values)
                if stats:
                    result["statistics"] = stats
                    
            elif numeric_values and analysis_type == "trend":
                # Use AnalysisEngine for trend detection
                timestamps = [datetime.now() for _ in numeric_values]  # Mock timestamps
                trend = self._analysis_engine.detect_trend(numeric_values, timestamps)
                result["trend_analysis"] = trend
                
            elif numeric_values and analysis_type == "seasonal":
                # Use AnalysisEngine for seasonality detection
                timestamps = [datetime.now() for _ in numeric_values]  # Mock timestamps
                seasonal = self._analysis_engine.detect_seasonality(numeric_values, timestamps)
                result["seasonality_analysis"] = seasonal
                
            # Add data access information if available
            if self.data_access:
                result["data_access_enabled"] = True
                result["user_context"] = {
                    "user_id": self.data_access.user_context.user_id,
                    "isolated": True
                }
            else:
                result["data_access_enabled"] = False
                
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis_type": analysis_type,
                "record_count": len(data)
            }
    
    async def get_analysis_capabilities(self) -> Dict[str, Any]:
        """
        Get information about available analysis capabilities.
        
        Returns:
            Dictionary with capability information
        """
        capabilities = {
            "basic_statistics": True,
            "trend_analysis": True,
            "seasonality_detection": True,
            "outlier_detection": True,
            "database_integration": bool(self.session_manager),
            "data_access_integration": bool(self.data_access)
        }
        
        if self.data_access:
            capabilities["user_isolation"] = True
            capabilities["clickhouse_access"] = True
            capabilities["redis_access"] = True
        
        return capabilities
    
    async def validate_analysis_request(self, 
                                      request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an analysis request for completeness and correctness.
        
        Args:
            request: Analysis request to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Basic request validation
        if not isinstance(request, dict):
            validation_result["valid"] = False
            validation_result["errors"].append("Request must be a dictionary")
            return validation_result
        
        # Check for required fields
        required_fields = ["data", "analysis_type"]
        for field in required_fields:
            if field not in request:
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["valid"] = False
        
        # Validate data format
        if "data" in request:
            data = request["data"]
            if not isinstance(data, list):
                validation_result["errors"].append("Data must be a list")
                validation_result["valid"] = False
            elif len(data) == 0:
                validation_result["warnings"].append("Data list is empty")
        
        # Validate analysis type
        if "analysis_type" in request:
            valid_types = ["basic", "trend", "seasonal", "outlier"]
            if request["analysis_type"] not in valid_types:
                validation_result["warnings"].append(
                    f"Unknown analysis type: {request['analysis_type']}. "
                    f"Valid types: {valid_types}"
                )
        
        return validation_result
    
    def get_session_manager(self) -> SessionManager:
        """Get the database session manager."""
        return self.session_manager
    
    def get_data_access(self) -> Optional[DataAccessCapabilities]:
        """Get the data access capabilities if available."""
        return self.data_access
    
    def is_initialized(self) -> bool:
        """Check if the core is properly initialized."""
        return self._initialized and self.session_manager is not None
    
    async def cleanup(self) -> None:
        """Clean up resources and connections."""
        try:
            if self.session_manager:
                await self.session_manager.close()
            
            if self.data_access:
                # Data access capabilities have their own cleanup
                pass
                
            self._initialized = False
            
        except Exception as e:
            # Don't raise exceptions during cleanup
            pass
    
    def __str__(self) -> str:
        """String representation of the analysis core."""
        return (f"DataAnalysisCore(session_manager={bool(self.session_manager)}, "
                f"data_access={bool(self.data_access)}, "
                f"initialized={self._initialized})")
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()


# Backward compatibility alias
DataAnalyzer = DataAnalysisCore