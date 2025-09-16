# GCP Backend Service Logs - Last 1 Hour

**Collection Time:** 2025-09-15 15:48:58 
**Time Range:** 2025-09-15 21:48:55 UTC to 2025-09-15 22:48:55 UTC
**Total Logs:** 160

## Summary by Severity
- **ERROR:** 50 entries
- **WARNING:** 50 entries
- **NOTICE:** 10 entries
- **INFO:** 50 entries

## ERROR Logs (50 entries)

### ERROR Entry #1

```
=== ERROR - 2025-09-15T22:48:44.774655+00:00 ===
Insert ID: 68c897cc000bd9f46a1ccc2c
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #2

```
=== ERROR - 2025-09-15T22:48:44.104425+00:00 ===
Insert ID: 68c897cc000197e9f192554c
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/home/netra/.local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/home/netra/.local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File...

```

### ERROR Entry #3

```
=== ERROR - 2025-09-15T22:48:44.104329+00:00 ===
Insert ID: 68c897cc00019789ee66b605
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #4

```
=== ERROR - 2025-09-15T22:48:44.104287+00:00 ===
Insert ID: 68c897cc0001975fe80b6aa6
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #5

```
=== ERROR - 2025-09-15T22:48:44.102653+00:00 ===
Insert ID: 68c897cc000190fd4126f942
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #6

```
=== ERROR - 2025-09-15T22:48:44.101356+00:00 ===
Insert ID: 68c897cc00018becc17d6edd
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #7

```
=== ERROR - 2025-09-15T22:48:37.593403+00:00 ===
Insert ID: 68c897cc00095f50b5efd7a9
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 6.897052056s

```

### ERROR Entry #8

```
=== ERROR - 2025-09-15T22:48:37.454981+00:00 ===
Insert ID: 68c897c50006f8c41c484e8c
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #9

```
=== ERROR - 2025-09-15T22:48:37.327893+00:00 ===
Insert ID: 68c897c5000508211b5b67af
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #10

```
=== ERROR - 2025-09-15T22:48:37.204098+00:00 ===
Insert ID: 68c897c5000322f916048b1e
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #11

```
=== ERROR - 2025-09-15T22:48:37.077873+00:00 ===
Insert ID: 68c897c500013744f4afac4d
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #12

```
=== ERROR - 2025-09-15T22:48:36.956435+00:00 ===
Insert ID: 68c897c4000e9e2eb24baeef
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #13

```
=== ERROR - 2025-09-15T22:48:36.833417+00:00 ===
Insert ID: 68c897c4000cbcf779a744d6
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #14

```
=== ERROR - 2025-09-15T22:48:36.698004+00:00 ===
Insert ID: 68c897c4000aac36746c3fa2
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #15

```
=== ERROR - 2025-09-15T22:48:36.574833+00:00 ===
Insert ID: 68c897c40008cb5ff61f8a6e
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #16

```
=== ERROR - 2025-09-15T22:48:36.442523+00:00 ===
Insert ID: 68c897c40006c894eb46a583
Service: netra-backend-staging
Text Payload:
  The request failed because the instance could not start successfully.
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 500
  user_agent: python-httpx/0.28.1
  latency: 0s

```

### ERROR Entry #17

```
=== ERROR - 2025-09-15T22:48:35.645709+00:00 ===
Insert ID: 68c897c30009da4d30655709
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/home/netra/.local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/home/netra/.local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File...

```

### ERROR Entry #18

```
=== ERROR - 2025-09-15T22:48:35.645620+00:00 ===
Insert ID: 68c897c30009d9f42d6c2b0a
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #19

```
=== ERROR - 2025-09-15T22:48:35.645580+00:00 ===
Insert ID: 68c897c30009d9cc6b202fe6
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #20

```
=== ERROR - 2025-09-15T22:48:35.643980+00:00 ===
Insert ID: 68c897c30009d38cf61d1d93
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #21

```
=== ERROR - 2025-09-15T22:48:35.636870+00:00 ===
Insert ID: 68c897c30009b7c68f028934
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #22

```
=== ERROR - 2025-09-15T22:48:29.401671+00:00 ===
Insert ID: 68c897c400027308c961b894
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 6.650359988s

```

### ERROR Entry #23

```
=== ERROR - 2025-09-15T22:48:28.815873+00:00 ===
Insert ID: 68c897bc000c7301314cc109
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/home/netra/.local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/home/netra/.local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File...

```

### ERROR Entry #24

```
=== ERROR - 2025-09-15T22:48:28.815777+00:00 ===
Insert ID: 68c897bc000c72a1d186660f
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #25

```
=== ERROR - 2025-09-15T22:48:28.815739+00:00 ===
Insert ID: 68c897bc000c727b62719395
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #26

```
=== ERROR - 2025-09-15T22:48:28.814516+00:00 ===
Insert ID: 68c897bc000c6db434309e47
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #27

```
=== ERROR - 2025-09-15T22:48:28.807983+00:00 ===
Insert ID: 68c897bc000c542f32cf9c51
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #28

```
=== ERROR - 2025-09-15T22:48:26.137775+00:00 ===
Insert ID: 68c897bd00041bba2be5dc4d
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/ws
  status: 503
  user_agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36
  latency: 3.126440s

```

### ERROR Entry #29

```
=== ERROR - 2025-09-15T22:48:22.746630+00:00 ===
Insert ID: 68c897bd0004382bc010f87c
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 6.415314552s

```

### ERROR Entry #30

```
=== ERROR - 2025-09-15T22:48:22.165922+00:00 ===
Insert ID: 68c897b6000288224f5e5cfd
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/home/netra/.local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/home/netra/.local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File...

```

### ERROR Entry #31

```
=== ERROR - 2025-09-15T22:48:22.165854+00:00 ===
Insert ID: 68c897b6000287de3194a4ce
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #32

```
=== ERROR - 2025-09-15T22:48:22.165822+00:00 ===
Insert ID: 68c897b6000287be42b4eb03
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #33

```
=== ERROR - 2025-09-15T22:48:22.165751+00:00 ===
Insert ID: 68c897b600028777895937ba
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #34

```
=== ERROR - 2025-09-15T22:48:22.156694+00:00 ===
Insert ID: 68c897b6000264169dc838af
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #35

```
=== ERROR - 2025-09-15T22:48:16.196400+00:00 ===
Insert ID: 68c897b60009516f30564350
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 6.319634200s

```

### ERROR Entry #36

```
=== ERROR - 2025-09-15T22:48:15.627187+00:00 ===
Insert ID: 68c897af000991f38d5fb3ff
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/home/netra/.local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/home/netra/.local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File...

```

### ERROR Entry #37

```
=== ERROR - 2025-09-15T22:48:15.627128+00:00 ===
Insert ID: 68c897af000991b8d71a3dec
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #38

```
=== ERROR - 2025-09-15T22:48:15.627100+00:00 ===
Insert ID: 68c897af0009919c5238ff8b
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #39

```
=== ERROR - 2025-09-15T22:48:15.625810+00:00 ===
Insert ID: 68c897af00098c92b89bc50c
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #40

```
=== ERROR - 2025-09-15T22:48:15.620612+00:00 ===
Insert ID: 68c897af00097844b0c72f08
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #41

```
=== ERROR - 2025-09-15T22:48:09.779350+00:00 ===
Insert ID: 68c897b00000fac6671d2ac7
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 6.179352618s

```

### ERROR Entry #42

```
=== ERROR - 2025-09-15T22:48:09.646302+00:00 ===
Insert ID: 68c897a90009e5d49eba6fff
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 0.000709665s

```

### ERROR Entry #43

```
=== ERROR - 2025-09-15T22:48:09.066789+00:00 ===
Insert ID: 68c897a9000104e55101ed0e
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/home/netra/.local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/home/netra/.local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File...

```

### ERROR Entry #44

```
=== ERROR - 2025-09-15T22:48:09.066732+00:00 ===
Insert ID: 68c897a9000104ac03c556d0
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #45

```
=== ERROR - 2025-09-15T22:48:09.066705+00:00 ===
Insert ID: 68c897a900010491b80fcc7a
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #46

```
=== ERROR - 2025-09-15T22:48:09.066011+00:00 ===
Insert ID: 68c897a9000101dbbd0dee44
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/home/netra/.local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/home/netra/.local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File...

```

### ERROR Entry #47

```
=== ERROR - 2025-09-15T22:48:09.065966+00:00 ===
Insert ID: 68c897a9000101ae06e83c16
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #48

```
=== ERROR - 2025-09-15T22:48:09.065944+00:00 ===
Insert ID: 68c897a9000101984d3e5d60
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #49

```
=== ERROR - 2025-09-15T22:48:09.065219+00:00 ===
Insert ID: 68c897a90000fec3e7631b68
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #50

```
=== ERROR - 2025-09-15T22:48:09.064757+00:00 ===
Insert ID: 68c897a90000fcf5b7e625be
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

## WARNING Logs (50 entries)

### WARNING Entry #1

```
=== WARNING - 2025-09-15T22:48:51.969988+00:00 ===
Insert ID: 68c897d3000ecd04e094fb64
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.969016Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.969016Z
    traceback: 

```

### WARNING Entry #2

```
=== WARNING - 2025-09-15T22:48:44.039199+00:00 ===
Insert ID: 68c897cc0000991fc27ff785
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #3

```
=== WARNING - 2025-09-15T22:48:42.941099+00:00 ===
Insert ID: 68c897ca000e5c2b8f3efc55
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.940370Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.940370Z
    traceback: 

```

### WARNING Entry #4

```
=== WARNING - 2025-09-15T22:48:41.434805+00:00 ===
Insert ID: 68c897c90006a27542e16bff
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:41.433529Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:41.433529Z
    traceback: 

```

### WARNING Entry #5

```
=== WARNING - 2025-09-15T22:48:35.567912+00:00 ===
Insert ID: 68c897c30008aa68a5a0d498
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #6

```
=== WARNING - 2025-09-15T22:48:34.498677+00:00 ===
Insert ID: 68c897c200079bf55badf070
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:34.496756Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:34.496756Z
    traceback: 

```

### WARNING Entry #7

```
=== WARNING - 2025-09-15T22:48:33.049544+00:00 ===
Insert ID: 68c897c10000c1888c0a1686
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:33.047545Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:33.047545Z
    traceback: 

```

### WARNING Entry #8

```
=== WARNING - 2025-09-15T22:48:28.753388+00:00 ===
Insert ID: 68c897bc000b7eecbf65b545
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #9

```
=== WARNING - 2025-09-15T22:48:27.636399+00:00 ===
Insert ID: 68c897bb0009b5ef252faa03
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:27.634708Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:27.634708Z
    traceback: 

```

### WARNING Entry #10

```
=== WARNING - 2025-09-15T22:48:26.225643+00:00 ===
Insert ID: 68c897ba0003716b882f4378
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:26.223853Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:26.223853Z
    traceback: 

```

### WARNING Entry #11

```
=== WARNING - 2025-09-15T22:48:22.101633+00:00 ===
Insert ID: 68c897b600018d018e063701
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #12

```
=== WARNING - 2025-09-15T22:48:21.041804+00:00 ===
Insert ID: 68c897b50000a34c3c1b2c94
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:21.040003Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:21.040003Z
    traceback: 

```

### WARNING Entry #13

```
=== WARNING - 2025-09-15T22:48:19.630880+00:00 ===
Insert ID: 68c897b30009a0605f1f19e3
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:19.628702Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:19.628702Z
    traceback: 

```

### WARNING Entry #14

```
=== WARNING - 2025-09-15T22:48:15.571214+00:00 ===
Insert ID: 68c897af0008b74ecf801d57
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #15

```
=== WARNING - 2025-09-15T22:48:14.563895+00:00 ===
Insert ID: 68c897ae00089ab798a47307
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:14.561833Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:14.561833Z
    traceback: 

```

### WARNING Entry #16

```
=== WARNING - 2025-09-15T22:48:13.205801+00:00 ===
Insert ID: 68c897ad000323e963d5f927
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:13.203592Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:13.203592Z
    traceback: 

```

### WARNING Entry #17

```
=== WARNING - 2025-09-15T22:48:09.606218+00:00 ===
Insert ID: 68c897a900094078aad446c8
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #18

```
=== WARNING - 2025-09-15T22:48:09.014756+00:00 ===
Insert ID: 68c897a9000039a43127dd3c
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #19

```
=== WARNING - 2025-09-15T22:48:09.008247+00:00 ===
Insert ID: 68c897a900002037911e7718
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #20

```
=== WARNING - 2025-09-15T22:48:07.955788+00:00 ===
Insert ID: 68c897a7000e958cf2902985
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:07.955020Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:07.955020Z
    traceback: 

```

### WARNING Entry #21

```
=== WARNING - 2025-09-15T22:48:07.948297+00:00 ===
Insert ID: 68c897a7000e7849565c0973
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:07.946161Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:07.946161Z
    traceback: 

```

### WARNING Entry #22

```
=== WARNING - 2025-09-15T22:48:06.565035+00:00 ===
Insert ID: 68c897a600089f2b364b4622
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:06.563664Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:06.563664Z
    traceback: 

```

### WARNING Entry #23

```
=== WARNING - 2025-09-15T22:48:06.540179+00:00 ===
Insert ID: 68c897a600083e131810007f
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:06.537793Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:06.537793Z
    traceback: 

```

### WARNING Entry #24

```
=== WARNING - 2025-09-15T22:48:02.269246+00:00 ===
Insert ID: 68c897a200041bbebfbb06be
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #25

```
=== WARNING - 2025-09-15T22:48:01.147075+00:00 ===
Insert ID: 68c897a100023e830ece76c0
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:01.140438Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:01.140438Z
    traceback: 

```

### WARNING Entry #26

```
=== WARNING - 2025-09-15T22:47:59.631871+00:00 ===
Insert ID: 68c8979f0009a43ff42bbc2b
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:59.630520Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:47:59.630520Z
    traceback: 

```

### WARNING Entry #27

```
=== WARNING - 2025-09-15T22:47:55.024009+00:00 ===
Insert ID: 68c8979b00005dc98b9d7e07
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #28

```
=== WARNING - 2025-09-15T22:47:53.975258+00:00 ===
Insert ID: 68c89799000ee19a12e1e853
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:53.974112Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:47:53.974112Z
    traceback: 

```

### WARNING Entry #29

```
=== WARNING - 2025-09-15T22:47:52.569276+00:00 ===
Insert ID: 68c897980008afbc42057af3
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:52.567824Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:47:52.567824Z
    traceback: 

```

### WARNING Entry #30

```
=== WARNING - 2025-09-15T22:47:47.578629+00:00 ===
Insert ID: 68c897930008d47d59fa1b50
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #31

```
=== WARNING - 2025-09-15T22:47:46.974566+00:00 ===
Insert ID: 68c89792000edee673ac42bb
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #32

```
=== WARNING - 2025-09-15T22:47:45.935296+00:00 ===
Insert ID: 68c89791000e458035187a82
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:45.933938Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:47:45.933938Z
    traceback: 

```

### WARNING Entry #33

```
=== WARNING - 2025-09-15T22:47:44.506192+00:00 ===
Insert ID: 68c897900007b950a4da0dbb
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:44.504629Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:47:44.504629Z
    traceback: 

```

### WARNING Entry #34

```
=== WARNING - 2025-09-15T22:47:38.584490+00:00 ===
Insert ID: 68c8978a0008eb663348a63a
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #35

```
=== WARNING - 2025-09-15T22:47:37.956148+00:00 ===
Insert ID: 68c89789000e96f4751fce18
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #36

```
=== WARNING - 2025-09-15T22:47:36.945010+00:00 ===
Insert ID: 68c89788000e6b721bdf0438
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:36.943595Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:47:36.943595Z
    traceback: 

```

### WARNING Entry #37

```
=== WARNING - 2025-09-15T22:47:35.527763+00:00 ===
Insert ID: 68c8978700080d93587bea08
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:35.526034Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:47:35.526034Z
    traceback: 

```

### WARNING Entry #38

```
=== WARNING - 2025-09-15T22:47:27.634608+00:00 ===
Insert ID: 68c8977f0009af29255478ec
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #39

```
=== WARNING - 2025-09-15T22:47:26.988897+00:00 ===
Insert ID: 68c8977e000f16e13513096e
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #40

```
=== WARNING - 2025-09-15T22:47:25.983037+00:00 ===
Insert ID: 68c8977d000efffdb6f510ed
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:25.981776Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:47:25.981776Z
    traceback: 

```

### WARNING Entry #41

```
=== WARNING - 2025-09-15T22:47:24.592217+00:00 ===
Insert ID: 68c8977c00090959b55b08cd
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:24.590782Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:47:24.590782Z
    traceback: 

```

### WARNING Entry #42

```
=== WARNING - 2025-09-15T22:47:20.040561+00:00 ===
Insert ID: 68c8977800009e71b43ab747
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #43

```
=== WARNING - 2025-09-15T22:47:18.957806+00:00 ===
Insert ID: 68c89776000e9d6ef9c6887f
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:18.956707Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:47:18.956707Z
    traceback: 

```

### WARNING Entry #44

```
=== WARNING - 2025-09-15T22:47:17.500718+00:00 ===
Insert ID: 68c897750007a3ee3aa8052f
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:17.499492Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:47:17.499492Z
    traceback: 

```

### WARNING Entry #45

```
=== WARNING - 2025-09-15T22:47:10.502201+00:00 ===
Insert ID: 68c8976e0007a9e45c3e539a
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #46

```
=== WARNING - 2025-09-15T22:47:09.899038+00:00 ===
Insert ID: 68c8976d000db7deeeaaec93
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #47

```
=== WARNING - 2025-09-15T22:47:08.853660+00:00 ===
Insert ID: 68c8976c000d069cdeaf8173
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:08.852635Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:47:08.852635Z
    traceback: 

```

### WARNING Entry #48

```
=== WARNING - 2025-09-15T22:47:07.454113+00:00 ===
Insert ID: 68c8976b0006ede14d19b5af
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:47:07.452815Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:47:07.452815Z
    traceback: 

```

### WARNING Entry #49

```
=== WARNING - 2025-09-15T22:47:00.295997+00:00 ===
Insert ID: 68c897640004846d5ce18a1c
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #50

```
=== WARNING - 2025-09-15T22:46:59.661672+00:00 ===
Insert ID: 68c89763000a18a871fd2ceb
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

## NOTICE Logs (10 entries)

### NOTICE Entry #1

```
=== NOTICE - 2025-09-15T22:25:49.123130+00:00 ===
Insert ID: qyecomdbhfu
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #2

```
=== NOTICE - 2025-09-15T22:24:27.919036+00:00 ===
Insert ID: 1km32i1dbi1v
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #3

```
=== NOTICE - 2025-09-15T22:20:17.075481+00:00 ===
Insert ID: 1ji2dq5dcxpl
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #4

```
=== NOTICE - 2025-09-15T22:19:49.725315+00:00 ===
Insert ID: 1oslj9odho3h
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #5

```
=== NOTICE - 2025-09-15T22:14:31.169947+00:00 ===
Insert ID: csn7x2db9eo
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #6

```
=== NOTICE - 2025-09-15T22:12:47.779847+00:00 ===
Insert ID: 1kxuzx8dbtog
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #7

```
=== NOTICE - 2025-09-15T21:58:12.208738+00:00 ===
Insert ID: 1gqwyvhd9nfz
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #8

```
=== NOTICE - 2025-09-15T21:57:31.645125+00:00 ===
Insert ID: kl3wc3daxbd
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #9

```
=== NOTICE - 2025-09-15T21:51:46.690675+00:00 ===
Insert ID: 1b6ofvcdayqm
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #10

```
=== NOTICE - 2025-09-15T21:51:12.211870+00:00 ===
Insert ID: u8uhs3d9yj8
Service: netra-backend-staging
JSON Payload:
  error:

```

## INFO Logs (50 entries)

### INFO Entry #1

```
=== INFO - 2025-09-15T22:48:52.001563+00:00 ===
Insert ID: 68c897d40000061bdd951bc0
Service: netra-backend-staging
JSON Payload:
  message: Configuration loaded and cached for environment: staging
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:52.000724Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:52.000724Z
    traceback: 

```

### INFO Entry #2

```
=== INFO - 2025-09-15T22:48:52.001152+00:00 ===
Insert ID: 68c897d400000480b49f348c
Service: netra-backend-staging
JSON Payload:
  message: PASS:  All configuration requirements validated for staging
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:52.000299Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:52.000299Z
    traceback: 

```

### INFO Entry #3

```
=== INFO - 2025-09-15T22:48:52.001018+00:00 ===
Insert ID: 68c897d4000003fa76cfe983
Service: netra-backend-staging
JSON Payload:
  message: Database configuration: Using component-based configuration for staging environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:52.000114Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:52.000114Z
    traceback: 

```

### INFO Entry #4

```
=== INFO - 2025-09-15T22:48:52.000505+00:00 ===
Insert ID: 68c897d4000001f99004aca7
Service: netra-backend-staging
JSON Payload:
  message: Validating configuration requirements for staging environment (readiness verified)
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.999421Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.999421Z
    traceback: 

```

### INFO Entry #5

```
=== INFO - 2025-09-15T22:48:51.969161+00:00 ===
Insert ID: 68c897d3000ec9c9169a7784
Service: netra-backend-staging
JSON Payload:
  message: Database URL (staging/Cloud SQL): postgresql+asyncpg://***@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.968328Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.968328Z
    traceback: 

```

### INFO Entry #6

```
=== INFO - 2025-09-15T22:48:51.968347+00:00 ===
Insert ID: 68c897d3000ec69b3ebcb6b6
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_SECRET configured: True
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.967591Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.967591Z
    traceback: 

```

### INFO Entry #7

```
=== INFO - 2025-09-15T22:48:51.968328+00:00 ===
Insert ID: 68c897d3000ec68826590bf3
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID configured: True
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.967467Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.967467Z
    traceback: 

```

### INFO Entry #8

```
=== INFO - 2025-09-15T22:48:51.968224+00:00 ===
Insert ID: 68c897d3000ec62072b929f0
Service: netra-backend-staging
JSON Payload:
  message: Loaded FERNET_KEY from environment
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.967329Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.967329Z
    traceback: 

```

### INFO Entry #9

```
=== INFO - 2025-09-15T22:48:51.968082+00:00 ===
Insert ID: 68c897d3000ec5923882a847
Service: netra-backend-staging
JSON Payload:
  message: Loaded SECRET_KEY from environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.967170Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.967170Z
    traceback: 

```

### INFO Entry #10

```
=== INFO - 2025-09-15T22:48:51.967808+00:00 ===
Insert ID: 68c897d3000ec4806017b585
Service: netra-backend-staging
JSON Payload:
  message: Loaded JWT_SECRET_KEY from environment
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.967024Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.967024Z
    traceback: 

```

### INFO Entry #11

```
=== INFO - 2025-09-15T22:48:51.967691+00:00 ===
Insert ID: 68c897d3000ec40b7070abe2
Service: netra-backend-staging
JSON Payload:
  message: Loaded SERVICE_ID from environment
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.966868Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.966868Z
    traceback: 

```

### INFO Entry #12

```
=== INFO - 2025-09-15T22:48:51.967582+00:00 ===
Insert ID: 68c897d3000ec39eb7588daf
Service: netra-backend-staging
JSON Payload:
  message: Loaded SERVICE_SECRET from environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.966693Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.966693Z
    traceback: 

```

### INFO Entry #13

```
=== INFO - 2025-09-15T22:48:51.967460+00:00 ===
Insert ID: 68c897d3000ec324f8cc0663
Service: netra-backend-staging
JSON Payload:
  message: Creating StagingConfig for environment: staging
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.966435Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.966435Z
    traceback: 

```

### INFO Entry #14

```
=== INFO - 2025-09-15T22:48:51.967439+00:00 ===
Insert ID: 68c897d3000ec30feb1ed808
Service: netra-backend-staging
JSON Payload:
  message: Loading unified configuration
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.966247Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.966247Z
    traceback: 

```

### INFO Entry #15

```
=== INFO - 2025-09-15T22:48:51.911241+00:00 ===
Insert ID: 68c897d3000de78901e211d5
Service: netra-backend-staging
JSON Payload:
  message: BackgroundTaskManager initialized
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.910262Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.910262Z
    traceback: 

```

### INFO Entry #16

```
=== INFO - 2025-09-15T22:48:51.901082+00:00 ===
Insert ID: 68c897d3000dbfda0b39143c
Service: netra-backend-staging
JSON Payload:
  message: ErrorRecoveryManager initialized
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.900191Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.900191Z
    traceback: 

```

### INFO Entry #17

```
=== INFO - 2025-09-15T22:48:51.900340+00:00 ===
Insert ID: 68c897d3000dbcf492a77ced
Service: netra-backend-staging
JSON Payload:
  message: ErrorRecoveryManager initialized
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:51.899289Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:51.899289Z
    traceback: 

```

### INFO Entry #18

```
=== INFO - 2025-09-15T22:48:46.967967+00:00 ===
Insert ID: 68c897ce000ec51f1e065bcf
Service: netra-backend-staging
Text Payload:
  Starting new instance. Reason: MANUAL_OR_CUSTOMER_MIN_INSTANCE - Instance started because of customer-configured min-instances or manual scaling.

```

### INFO Entry #19

```
=== INFO - 2025-09-15T22:48:44.090928+00:00 ===
Insert ID: 68c897cc00016330e2cf1cd7
Service: netra-backend-staging
JSON Payload:
  message: Creating enhanced WebSocket exclusion middleware inline (Issue #449 fallback)
  error:

```

### INFO Entry #20

```
=== INFO - 2025-09-15T22:48:44.084225+00:00 ===
Insert ID: 68c897cc0001490125103ad9
Service: netra-backend-staging
JSON Payload:
  message: uvicorn-compatible SessionMiddleware configured for staging (Issue #449)
  error:

```

### INFO Entry #21

```
=== INFO - 2025-09-15T22:48:44.083869+00:00 ===
Insert ID: 68c897cc0001479d87595702
Service: netra-backend-staging
JSON Payload:
  message: uvicorn-compatible SessionMiddleware installed (Issue #449)
  error:

```

### INFO Entry #22

```
=== INFO - 2025-09-15T22:48:44.083590+00:00 ===
Insert ID: 68c897cc00014686bdc8c8d4
Service: netra-backend-staging
JSON Payload:
  message: Using config.secret_key for staging (length: 51)
  error:

```

### INFO Entry #23

```
=== INFO - 2025-09-15T22:48:44.075245+00:00 ===
Insert ID: 68c897cc000125eda7019b50
Service: netra-backend-staging
JSON Payload:
  message: AuthServiceClient initialized - Service ID: netra-backend, Service Secret=REDACTED True
  error:

```

### INFO Entry #24

```
=== INFO - 2025-09-15T22:48:44.075234+00:00 ===
Insert ID: 68c897cc000125e2a23ca3ea
Service: netra-backend-staging
JSON Payload:
  message: TracingManager initialized
  error:

```

### INFO Entry #25

```
=== INFO - 2025-09-15T22:48:44.074616+00:00 ===
Insert ID: 68c897cc0001237865d48c99
Service: netra-backend-staging
JSON Payload:
  message: Tracer initialized: default
  error:

```

### INFO Entry #26

```
=== INFO - 2025-09-15T22:48:44.074326+00:00 ===
Insert ID: 68c897cc00012256bab9fb1d
Service: netra-backend-staging
JSON Payload:
  message: AuthCircuitBreakerManager initialized with UnifiedCircuitBreaker
  error:

```

### INFO Entry #27

```
=== INFO - 2025-09-15T22:48:44.074153+00:00 ===
Insert ID: 68c897cc000121a9a766fa4d
Service: netra-backend-staging
JSON Payload:
  message: AuthClientCache initialized with default TTL: 300s and user isolation
  error:

```

### INFO Entry #28

```
=== INFO - 2025-09-15T22:48:44.068789+00:00 ===
Insert ID: 68c897cc00010cb59194dd1b
Service: netra-backend-staging
JSON Payload:
  message: AuthServiceClient initialized - Service ID: netra-backend, Service Secret=REDACTED True
  error:

```

### INFO Entry #29

```
=== INFO - 2025-09-15T22:48:44.068706+00:00 ===
Insert ID: 68c897cc00010c62c7d26492
Service: netra-backend-staging
JSON Payload:
  message: TracingManager initialized
  error:

```

### INFO Entry #30

```
=== INFO - 2025-09-15T22:48:44.068692+00:00 ===
Insert ID: 68c897cc00010c5413b986da
Service: netra-backend-staging
JSON Payload:
  message: Tracer initialized: default
  error:

```

### INFO Entry #31

```
=== INFO - 2025-09-15T22:48:44.068304+00:00 ===
Insert ID: 68c897cc00010ad039b53ba6
Service: netra-backend-staging
JSON Payload:
  message: AuthCircuitBreakerManager initialized with UnifiedCircuitBreaker
  error:

```

### INFO Entry #32

```
=== INFO - 2025-09-15T22:48:44.068274+00:00 ===
Insert ID: 68c897cc00010ab2510e84e7
Service: netra-backend-staging
JSON Payload:
  message: AuthClientCache initialized with default TTL: 300s and user isolation
  error:

```

### INFO Entry #33

```
=== INFO - 2025-09-15T22:48:44.039267+00:00 ===
Insert ID: 68c897cc000099637536e695
Service: netra-backend-staging
JSON Payload:
  message: Starting enhanced middleware setup with WebSocket exclusion support...
  error:

```

### INFO Entry #34

```
=== INFO - 2025-09-15T22:48:44.039188+00:00 ===
Insert ID: 68c897cc00009914203b7a05
Service: netra-backend-staging
JSON Payload:
  message: OpenTelemetry automatic instrumentation initialized successfully
  error:

```

### INFO Entry #35

```
=== INFO - 2025-09-15T22:48:44.039169+00:00 ===
Insert ID: 68c897cc000099016242c980
Service: netra-backend-staging
JSON Payload:
  message: OpenTelemetry automatic instrumentation initialized for netra-backend-staging in staging
  error:

```

### INFO Entry #36

```
=== INFO - 2025-09-15T22:48:43.191774+00:00 ===
Insert ID: 68c897cb0002ed1e80c59e35
Service: netra-backend-staging
JSON Payload:
  message: Telemetry enabled but no exporters configured - traces will not be exported. To enable tracing, either set OTEL_EXPORTER_OTLP_ENDPOINT or install google-cloud-trace package.
  error:

```

### INFO Entry #37

```
=== INFO - 2025-09-15T22:48:42.974191+00:00 ===
Insert ID: 68c897ca000edd6f63d747ae
Service: netra-backend-staging
JSON Payload:
  message: Configuration loaded and cached for environment: staging
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.973551Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.973551Z
    traceback: 

```

### INFO Entry #38

```
=== INFO - 2025-09-15T22:48:42.973791+00:00 ===
Insert ID: 68c897ca000edbdf9844488b
Service: netra-backend-staging
JSON Payload:
  message: PASS:  All configuration requirements validated for staging
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.973123Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.973123Z
    traceback: 

```

### INFO Entry #39

```
=== INFO - 2025-09-15T22:48:42.973617+00:00 ===
Insert ID: 68c897ca000edb31a94198de
Service: netra-backend-staging
JSON Payload:
  message: Database configuration: Using component-based configuration for staging environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.972938Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.972938Z
    traceback: 

```

### INFO Entry #40

```
=== INFO - 2025-09-15T22:48:42.973091+00:00 ===
Insert ID: 68c897ca000ed923fbf9ee63
Service: netra-backend-staging
JSON Payload:
  message: Validating configuration requirements for staging environment (readiness verified)
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.972235Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.972235Z
    traceback: 

```

### INFO Entry #41

```
=== INFO - 2025-09-15T22:48:42.940401+00:00 ===
Insert ID: 68c897ca000e5971ee6cee12
Service: netra-backend-staging
JSON Payload:
  message: Database URL (staging/Cloud SQL): postgresql+asyncpg://***@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.939652Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.939652Z
    traceback: 

```

### INFO Entry #42

```
=== INFO - 2025-09-15T22:48:42.939541+00:00 ===
Insert ID: 68c897ca000e56158760d067
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_SECRET configured: True
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.938881Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.938881Z
    traceback: 

```

### INFO Entry #43

```
=== INFO - 2025-09-15T22:48:42.939524+00:00 ===
Insert ID: 68c897ca000e5604e17fefa8
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID configured: True
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.938750Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.938750Z
    traceback: 

```

### INFO Entry #44

```
=== INFO - 2025-09-15T22:48:42.939507+00:00 ===
Insert ID: 68c897ca000e55f3080a645f
Service: netra-backend-staging
JSON Payload:
  message: Loaded FERNET_KEY from environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.938603Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.938603Z
    traceback: 

```

### INFO Entry #45

```
=== INFO - 2025-09-15T22:48:42.939226+00:00 ===
Insert ID: 68c897ca000e54da38c963d8
Service: netra-backend-staging
JSON Payload:
  message: Loaded SECRET_KEY from environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.938438Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.938438Z
    traceback: 

```

### INFO Entry #46

```
=== INFO - 2025-09-15T22:48:42.939062+00:00 ===
Insert ID: 68c897ca000e54368636cbd5
Service: netra-backend-staging
JSON Payload:
  message: Loaded JWT_SECRET_KEY from environment
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.938272Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.938272Z
    traceback: 

```

### INFO Entry #47

```
=== INFO - 2025-09-15T22:48:42.938889+00:00 ===
Insert ID: 68c897ca000e53897880fb7f
Service: netra-backend-staging
JSON Payload:
  message: Loaded SERVICE_ID from environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.938104Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.938104Z
    traceback: 

```

### INFO Entry #48

```
=== INFO - 2025-09-15T22:48:42.938631+00:00 ===
Insert ID: 68c897ca000e528745141940
Service: netra-backend-staging
JSON Payload:
  message: Loaded SERVICE_SECRET from environment
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.937942Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.937942Z
    traceback: 

```

### INFO Entry #49

```
=== INFO - 2025-09-15T22:48:42.938594+00:00 ===
Insert ID: 68c897ca000e52626c8cad81
Service: netra-backend-staging
JSON Payload:
  message: Creating StagingConfig for environment: staging
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.937705Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.937705Z
    traceback: 

```

### INFO Entry #50

```
=== INFO - 2025-09-15T22:48:42.938577+00:00 ===
Insert ID: 68c897ca000e5251842ac64b
Service: netra-backend-staging
JSON Payload:
  message: Loading unified configuration
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T22:48:42.937513Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T22:48:42.937513Z
    traceback: 

```
