#!/usr/bin/env python3
"""
Zen Telemetry Usage Examples

Demonstrates practical usage patterns for the Zen telemetry module.
"""

import asyncio
import time
from pathlib import Path

# Import zen (auto-initializes telemetry)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from zen.telemetry import traced, trace_performance, instrument_class, telemetry_manager


# Example 1: Basic function tracing
@traced("user_authentication")
def authenticate_user(username: str, password: str) -> bool:
    """Example function with basic tracing"""
    # Simulate authentication logic
    time.sleep(0.1)  # Simulate database lookup
    return username == "admin" and password == "secret"


# Example 2: Advanced function tracing with custom attributes
@traced(
    "data_processing",
    attributes={"component": "parser", "version": "1.0"},
    capture_args=True,
    capture_result=True
)
def process_data(data: dict) -> dict:
    """Example with advanced tracing configuration"""
    # Simulate data processing
    time.sleep(0.05)

    if not data:
        raise ValueError("Empty data provided")

    return {
        "processed": True,
        "count": len(data),
        "timestamp": time.time()
    }


# Example 3: Async function tracing
@traced("async_operation", {"operation.type": "network"})
async def fetch_external_data(url: str) -> dict:
    """Example async function with tracing"""
    # Simulate network request
    await asyncio.sleep(0.2)

    if "invalid" in url:
        raise ConnectionError("Invalid URL provided")

    return {"status": "success", "data": f"Response from {url}"}


# Example 4: Class instrumentation
@instrument_class(
    methods=["process", "validate"],
    prefix="data_pipeline"
)
class DataPipeline:
    """Example class with automatic method instrumentation"""

    def __init__(self, name: str):
        self.name = name
        self.processed_count = 0

    def process(self, items: list) -> list:
        """Process items with automatic tracing"""
        validated_items = self.validate(items)

        # Simulate processing
        time.sleep(0.01 * len(validated_items))

        self.processed_count += len(validated_items)
        return [f"processed_{item}" for item in validated_items]

    def validate(self, items: list) -> list:
        """Validate items with automatic tracing"""
        return [item for item in items if item is not None]


# Example 5: Manual span creation with performance tracking
def complex_operation():
    """Example of manual instrumentation for complex operations"""

    with trace_performance("database_setup") as span:
        # Simulate database connection
        time.sleep(0.05)
        span.set_attribute("db.connection_pool", "main")

    # Multiple database queries with individual tracking
    results = []
    for i in range(3):
        with telemetry_manager.create_span(f"database_query_{i}") as span:
            span.set_attribute("query.table", f"table_{i}")
            span.set_attribute("query.type", "SELECT")

            # Simulate query execution
            time.sleep(0.02)
            results.append(f"result_{i}")

    with trace_performance("data_aggregation", table_count=3):
        # Simulate data aggregation
        time.sleep(0.03)
        aggregated = {"total_results": len(results), "data": results}

    return aggregated


# Example 6: Error handling and exception recording
@traced("error_prone_operation")
def error_prone_operation(should_fail: bool = False):
    """Example of error handling in traced functions"""

    if should_fail:
        # This exception will be automatically recorded in the trace
        raise RuntimeError("Intentional failure for demonstration")

    return "Operation completed successfully"


# Example 7: Sensitive data handling
@traced("user_profile", capture_args=True, sanitize_data=True)
def process_user_profile(user_data: dict) -> dict:
    """Example showing automatic PII sanitization"""

    # This data contains PII that will be automatically sanitized
    user_info = {
        "username": user_data.get("username"),
        "email": user_data.get("email"),  # Will be sanitized
        "password": user_data.get("password"),  # Will be sanitized
        "phone": user_data.get("phone"),  # Will be sanitized
        "preferences": user_data.get("preferences", {})
    }

    # Process the user profile
    return {
        "profile_id": "safe_identifier",
        "preferences_updated": True,
        "last_updated": time.time()
    }


async def demonstrate_telemetry():
    """Demonstrate various telemetry features"""

    print("🔍 Zen Telemetry Usage Examples")
    print("=" * 50)

    # Check if telemetry is enabled
    print(f"Telemetry enabled: {telemetry_manager.is_enabled()}")
    print(f"Configuration: {telemetry_manager.get_config().level}")
    print()

    # Example 1: Basic tracing
    print("1. Basic function tracing...")
    result = authenticate_user("admin", "secret")
    print(f"   Authentication result: {result}")

    # Example 2: Advanced tracing
    print("2. Advanced tracing with attributes...")
    try:
        data = {"key1": "value1", "key2": "value2"}
        processed = process_data(data)
        print(f"   Processed data: {processed['count']} items")
    except Exception as e:
        print(f"   Error: {e}")

    # Example 3: Async tracing
    print("3. Async function tracing...")
    try:
        response = await fetch_external_data("https://api.example.com/data")
        print(f"   Response status: {response['status']}")
    except Exception as e:
        print(f"   Error: {e}")

    # Example 4: Class instrumentation
    print("4. Class method instrumentation...")
    pipeline = DataPipeline("example_pipeline")
    items = ["item1", "item2", None, "item3"]
    processed_items = pipeline.process(items)
    print(f"   Processed {len(processed_items)} items")

    # Example 5: Complex operation with manual spans
    print("5. Complex operation with manual spans...")
    results = complex_operation()
    print(f"   Complex operation completed: {results['total_results']} results")

    # Example 6: Error handling
    print("6. Error handling demonstration...")
    try:
        error_prone_operation(should_fail=False)
        print("   Operation succeeded")
    except Exception as e:
        print(f"   Expected error: {e}")

    try:
        error_prone_operation(should_fail=True)
    except Exception as e:
        print(f"   Caught and traced error: {e}")

    # Example 7: PII sanitization
    print("7. PII sanitization demonstration...")
    user_data = {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "secret123",
        "phone": "555-123-4567",
        "preferences": {"theme": "dark", "notifications": True}
    }

    profile_result = process_user_profile(user_data)
    print(f"   Profile processed: {profile_result['profile_id']}")

    print("\n✅ All examples completed!")
    print("Check Google Cloud Trace for distributed traces (if configured)")


def demonstrate_configuration():
    """Demonstrate configuration options"""

    print("\n📊 Configuration Examples")
    print("=" * 50)

    from zen.telemetry.config import TelemetryConfig

    config = TelemetryConfig.from_environment()
    print(f"Current configuration:")
    print(f"  Enabled: {config.enabled}")
    print(f"  Level: {config.level.value}")
    print(f"  Sample rate: {config.sample_rate}")
    print(f"  Service: {config.service_name} v{config.service_version}")
    print(f"  GCP project: {config.gcp_project or 'auto-detect'}")

    print(f"\nEnvironment variables for configuration:")
    print(f"  ZEN_TELEMETRY_DISABLED=true    # Disable telemetry")
    print(f"  ZEN_TELEMETRY_LEVEL=detailed   # Set telemetry level")
    print(f"  ZEN_TELEMETRY_SAMPLE_RATE=0.5  # 50% sampling")
    print(f"  ZEN_TELEMETRY_GCP_PROJECT=my-project")


def demonstrate_data_sanitization():
    """Demonstrate data sanitization capabilities"""

    print("\n🔒 Data Sanitization Examples")
    print("=" * 50)

    from zen.telemetry.sanitization import DataSanitizer

    # Example sensitive data
    sensitive_data = {
        "user_email": "user@example.com",
        "api_key": "sk-1234567890abcdef",
        "password": "secret123",
        "phone_number": "555-123-4567",
        "safe_data": "This is safe to include",
        "nested": {
            "token": "bearer_xyz789",
            "public_info": "Safe nested data"
        }
    }

    print("Original data (showing structure only):")
    print("  user_email: [CONTAINS EMAIL]")
    print("  api_key: [CONTAINS API KEY]")
    print("  password: [CONTAINS PASSWORD]")
    print("  phone_number: [CONTAINS PHONE]")
    print("  safe_data: This is safe to include")
    print("  nested.token: [CONTAINS TOKEN]")
    print("  nested.public_info: Safe nested data")

    # Sanitize the data
    sanitized = DataSanitizer.sanitize_value(sensitive_data)

    print(f"\nSanitized data:")
    for key, value in sanitized.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for nested_key, nested_value in value.items():
                print(f"    {nested_key}: {nested_value}")
        else:
            print(f"  {key}: {value}")


async def main():
    """Run all examples"""

    print("🚀 Starting Zen Telemetry Examples")
    print("=" * 60)

    # Initialize telemetry (normally done automatically)
    await telemetry_manager.initialize()

    # Run demonstrations
    await demonstrate_telemetry()
    demonstrate_configuration()
    demonstrate_data_sanitization()

    print("\n" + "=" * 60)
    print("📈 Examples completed!")
    print("\nNext steps:")
    print("1. Check Google Cloud Trace console for distributed traces")
    print("2. Configure your GCP project with ZEN_TELEMETRY_GCP_PROJECT")
    print("3. Set up zen_secrets with telemetry service account")
    print("4. Customize telemetry level and sampling rate")
    print("5. Add @traced decorators to your own functions")


if __name__ == "__main__":
    asyncio.run(main())