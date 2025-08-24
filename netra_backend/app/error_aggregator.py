# Shim module for backward compatibility
from netra_backend.app.core.error_aggregation_core import ErrorAggregator, error_aggregation_system

# Create instance for backward compatibility
error_aggregator = error_aggregation_system
