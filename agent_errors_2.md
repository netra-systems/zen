[BACKEND] 2025-08-15 13:31:16.458 | INFO     | app.core.request_context:log_request_details:68 | Request: GET /health/live | Status: 200 | Duration: 0.00ms | Trace: 4f936eca-f893-4f5a-8310-ea9ec3d04458
[BACKEND] 2025-08-15 13:31:16.458 | INFO     | logging:handle:1028 | 127.0.0.1:59519 - "GET /health/live HTTP/1.1" 200
[BACKEND] ❌ 2025-08-15 13:31:30.781 | ERROR    | app.routes.websockets:_handle_general_exception:206 | Error in WebSocket connection: 'WebSocketManager' object has no attribute 'connection_manager'
13:31:46 | DEBUG | Starting new HTTP connection (1): localhost:55410
13:31:48 | DEBUG | http://localhost:55410 "GET /health/live HTTP/1.1" 200 50
[BACKEND] 2025-08-15 13:31:48.510 | INFO     | app.core.request_context:log_request_details:68 | Request: GET /health/live | Status: 200 | Duration: 0.99ms | Trace: 265c1678-4ba4-4d16-85ea-4e23c8589d4a