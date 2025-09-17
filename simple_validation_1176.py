try:
    from netra_backend.app.websocket_core.standardized_factory_interface import get_standardized_websocket_manager_factory
    factory = get_standardized_websocket_manager_factory()
    print("SUCCESS: Standardized factory created")
    print(f"Factory type: {type(factory)}")
    print(f"Supports isolation: {factory.supports_user_isolation()}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()