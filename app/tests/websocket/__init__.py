"""
WebSocket test module.

This module contains specialized WebSocket tests split into focused modules
following the 450-line architectural requirement.

Modules:
- test_concurrent_connections: Connection limits and pool management
- test_message_ordering: Message sequencing and binary data
- test_compression_auth: Compression and authentication features  
- test_memory_monitoring: Memory leak detection and performance
"""