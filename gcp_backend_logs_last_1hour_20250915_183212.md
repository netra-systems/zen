# GCP Backend Service Logs - Last 1 Hour

**Collection Time:** 2025-09-15 18:32:12 
**Time Range:** 2025-09-16 00:32:09 UTC to 2025-09-16 01:32:09 UTC
**Total Logs:** 162

## Summary by Severity
- **ERROR:** 50 entries
- **WARNING:** 50 entries
- **NOTICE:** 12 entries
- **INFO:** 50 entries

## ERROR Logs (50 entries)

### ERROR Entry #1

```
=== ERROR - 2025-09-16T01:32:01.612800+00:00 ===
Insert ID: 68c8be11000959c0116a9b88
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #2

```
=== ERROR - 2025-09-16T01:32:01.612760+00:00 ===
Insert ID: 68c8be11000959985935598e
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #3

```
=== ERROR - 2025-09-16T01:32:01.612741+00:00 ===
Insert ID: 68c8be1100095985bd287cb5
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #4

```
=== ERROR - 2025-09-16T01:32:01.612673+00:00 ===
Insert ID: 68c8be110009594141a42d00
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #5

```
=== ERROR - 2025-09-16T01:32:01.607929+00:00 ===
Insert ID: 68c8be11000946b9da100dae
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #6

```
=== ERROR - 2025-09-16T01:31:53.167575+00:00 ===
Insert ID: 68c8be0900028e9740c4e32c
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #7

```
=== ERROR - 2025-09-16T01:31:53.167536+00:00 ===
Insert ID: 68c8be0900028e70da28fff9
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #8

```
=== ERROR - 2025-09-16T01:31:53.167518+00:00 ===
Insert ID: 68c8be0900028e5e7fee0587
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #9

```
=== ERROR - 2025-09-16T01:31:53.166140+00:00 ===
Insert ID: 68c8be09000288fcb897dcaf
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #10

```
=== ERROR - 2025-09-16T01:31:53.163866+00:00 ===
Insert ID: 68c8be090002801a2b7bc433
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #11

```
=== ERROR - 2025-09-16T01:31:43.839086+00:00 ===
Insert ID: 68c8be09000976d40601053d
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://netra-backend-staging-pnovr5vsba-uc.a.run.app/
  status: 503
  user_agent: python-requests/2.32.5
  latency: 9.649708414s

```

### ERROR Entry #12

```
=== ERROR - 2025-09-16T01:31:43.085948+00:00 ===
Insert ID: 68c8bdff00014fbcd3255849
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #13

```
=== ERROR - 2025-09-16T01:31:43.085891+00:00 ===
Insert ID: 68c8bdff00014f833ec90506
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #14

```
=== ERROR - 2025-09-16T01:31:43.085868+00:00 ===
Insert ID: 68c8bdff00014f6c68c7bff1
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #15

```
=== ERROR - 2025-09-16T01:31:43.084695+00:00 ===
Insert ID: 68c8bdff00014ad7ae4670ef
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #16

```
=== ERROR - 2025-09-16T01:31:43.082471+00:00 ===
Insert ID: 68c8bdff000142271ac96492
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #17

```
=== ERROR - 2025-09-16T01:31:38.694072+00:00 ===
Insert ID: 68c8bdff0007dd3b530123d4
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://netra-backend-staging-pnovr5vsba-uc.a.run.app/health
  status: 503
  user_agent: python-requests/2.32.5
  latency: 4.549385574s

```

### ERROR Entry #18

```
=== ERROR - 2025-09-16T01:31:32.290057+00:00 ===
Insert ID: 68c8bdf400046d0990226357
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #19

```
=== ERROR - 2025-09-16T01:31:32.290020+00:00 ===
Insert ID: 68c8bdf400046ce4294084f9
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #20

```
=== ERROR - 2025-09-16T01:31:32.290002+00:00 ===
Insert ID: 68c8bdf400046cd2267828dd
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #21

```
=== ERROR - 2025-09-16T01:31:32.289035+00:00 ===
Insert ID: 68c8bdf40004690b81eb1dfb
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #22

```
=== ERROR - 2025-09-16T01:31:32.286805+00:00 ===
Insert ID: 68c8bdf400046055a0e279f0
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #23

```
=== ERROR - 2025-09-16T01:31:24.040973+00:00 ===
Insert ID: 68c8bdec0000a00dfd711369
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #24

```
=== ERROR - 2025-09-16T01:31:24.040920+00:00 ===
Insert ID: 68c8bdec00009fd8fa9f3cb4
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
=== ERROR - 2025-09-16T01:31:24.040896+00:00 ===
Insert ID: 68c8bdec00009fc0599408c3
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
=== ERROR - 2025-09-16T01:31:24.039933+00:00 ===
Insert ID: 68c8bdec00009bfde4e4d989
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
=== ERROR - 2025-09-16T01:31:24.034870+00:00 ===
Insert ID: 68c8bdec00008836207b3c4f
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #28

```
=== ERROR - 2025-09-16T01:31:15.687144+00:00 ===
Insert ID: 68c8bde3000a7c28f8dea65f
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #29

```
=== ERROR - 2025-09-16T01:31:15.687086+00:00 ===
Insert ID: 68c8bde3000a7beeebdbb20d
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #30

```
=== ERROR - 2025-09-16T01:31:15.687062+00:00 ===
Insert ID: 68c8bde3000a7bd6e7d5e7c4
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #31

```
=== ERROR - 2025-09-16T01:31:15.686112+00:00 ===
Insert ID: 68c8bde3000a78209b794fd9
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #32

```
=== ERROR - 2025-09-16T01:31:15.684217+00:00 ===
Insert ID: 68c8bde3000a70b94ea256b6
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #33

```
=== ERROR - 2025-09-16T01:31:07.484926+00:00 ===
Insert ID: 68c8bddb0007663e3a0d74d4
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #34

```
=== ERROR - 2025-09-16T01:31:07.484886+00:00 ===
Insert ID: 68c8bddb00076616f8cbba7f
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #35

```
=== ERROR - 2025-09-16T01:31:07.484862+00:00 ===
Insert ID: 68c8bddb000765fe12263b43
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #36

```
=== ERROR - 2025-09-16T01:31:07.484062+00:00 ===
Insert ID: 68c8bddb000762de364ad4fe
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #37

```
=== ERROR - 2025-09-16T01:31:07.481890+00:00 ===
Insert ID: 68c8bddb00075a623665f876
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #38

```
=== ERROR - 2025-09-16T01:30:59.563180+00:00 ===
Insert ID: 68c8bdd3000897ec80eae241
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #39

```
=== ERROR - 2025-09-16T01:30:59.563137+00:00 ===
Insert ID: 68c8bdd3000897c113e97115
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #40

```
=== ERROR - 2025-09-16T01:30:59.563115+00:00 ===
Insert ID: 68c8bdd3000897ab19e17833
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

### ERROR Entry #41

```
=== ERROR - 2025-09-16T01:30:59.562101+00:00 ===
Insert ID: 68c8bdd3000893b5657a4bd8
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #42

```
=== ERROR - 2025-09-16T01:30:59.559756+00:00 ===
Insert ID: 68c8bdd300088a8cfe93a369
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #43

```
=== ERROR - 2025-09-16T01:30:51.637434+00:00 ===
Insert ID: 68c8bdcb0009b9fae58431f0
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #44

```
=== ERROR - 2025-09-16T01:30:51.637395+00:00 ===
Insert ID: 68c8bdcb0009b9d3cc59144e
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
=== ERROR - 2025-09-16T01:30:51.637376+00:00 ===
Insert ID: 68c8bdcb0009b9c0819c9071
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
=== ERROR - 2025-09-16T01:30:51.636447+00:00 ===
Insert ID: 68c8bdcb0009b61f692acbdc
Service: netra-backend-staging
JSON Payload:
  message: Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
  error: {'value': "No module named 'netra_backend.app.services.monitoring'", 'type': 'ModuleNotFoundError', 'traceback': None}
  error:
    value: No module named 'netra_backend.app.services.monitoring'
    type: ModuleNotFoundError
    traceback: None

```

### ERROR Entry #47

```
=== ERROR - 2025-09-16T01:30:51.634371+00:00 ===
Insert ID: 68c8bdcb0009ae03b1ef371c
Service: netra-backend-staging
JSON Payload:
  message: CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
  error:

```

### ERROR Entry #48

```
=== ERROR - 2025-09-16T01:30:43.775143+00:00 ===
Insert ID: 68c8bdc3000bd3e73fbd6093
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-packages/uvicorn/workers.py", line 75, in init_process
    super().init_process()
  File "/usr/local/lib...

```

### ERROR Entry #49

```
=== ERROR - 2025-09-16T01:30:43.775090+00:00 ===
Insert ID: 68c8bdc3000bd3b2fc19cd5b
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 799, in setup_middleware
    _add_websocket_exclusion_middleware(app)
  File "/app/netra_backend/app/core/middleware_setup.py", line 860, in _add_websocket_exclusion_middleware
    _create_enhanced_inli...

```

### ERROR Entry #50

```
=== ERROR - 2025-09-16T01:30:43.775067+00:00 ===
Insert ID: 68c8bdc3000bd39bfe178337
Service: netra-backend-staging
Text Payload:
  Traceback (most recent call last):
  File "/app/netra_backend/app/core/middleware_setup.py", line 852, in _add_websocket_exclusion_middleware
    from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
  File "/app/netra_backend/app/middleware/__init__.py", line 3, in <module>
    fr...

```

## WARNING Logs (50 entries)

### WARNING Entry #1

```
=== WARNING - 2025-09-16T01:32:02.118391+00:00 ===
Insert ID: 68c8be120001cf58105140ee
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #2

```
=== WARNING - 2025-09-16T01:32:01.544178+00:00 ===
Insert ID: 68c8be1100084db235acc9fa
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #3

```
=== WARNING - 2025-09-16T01:32:00.631063+00:00 ===
Insert ID: 68c8be100009a1176e91323d
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.630465Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.630465Z
    traceback: 

```

### WARNING Entry #4

```
=== WARNING - 2025-09-16T01:31:53.107832+00:00 ===
Insert ID: 68c8be090001a538bd1ec5d4
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #5

```
=== WARNING - 2025-09-16T01:31:51.989844+00:00 ===
Insert ID: 68c8be07000f1a94c690a11e
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:51.988336Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:31:51.988336Z
    traceback: 

```

### WARNING Entry #6

```
=== WARNING - 2025-09-16T01:31:43.013271+00:00 ===
Insert ID: 68c8bdff000033d7c670170d
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #7

```
=== WARNING - 2025-09-16T01:31:42.011260+00:00 ===
Insert ID: 68c8bdfe00002bfc9846a26f
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:42.008996Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:31:42.008996Z
    traceback: 

```

### WARNING Entry #8

```
=== WARNING - 2025-09-16T01:31:32.858745+00:00 ===
Insert ID: 68c8bdf4000d1ac6860a429b
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #9

```
=== WARNING - 2025-09-16T01:31:32.235510+00:00 ===
Insert ID: 68c8bdf4000397f62938edc3
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #10

```
=== WARNING - 2025-09-16T01:31:31.546324+00:00 ===
Insert ID: 68c8bdf3000856148a923e20
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:31.545576Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:31:31.545576Z
    traceback: 

```

### WARNING Entry #11

```
=== WARNING - 2025-09-16T01:31:24.565459+00:00 ===
Insert ID: 68c8bdec0008a0facda6cebb
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #12

```
=== WARNING - 2025-09-16T01:31:23.967189+00:00 ===
Insert ID: 68c8bdeb000ec21539e7abfd
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #13

```
=== WARNING - 2025-09-16T01:31:23.183190+00:00 ===
Insert ID: 68c8bdeb0002cb96f0b8c6fc
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:23.182652Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:31:23.182652Z
    traceback: 

```

### WARNING Entry #14

```
=== WARNING - 2025-09-16T01:31:16.129597+00:00 ===
Insert ID: 68c8bde40001fa6811269fad
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #15

```
=== WARNING - 2025-09-16T01:31:15.634047+00:00 ===
Insert ID: 68c8bde30009acbfd7aae170
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #16

```
=== WARNING - 2025-09-16T01:31:14.954980+00:00 ===
Insert ID: 68c8bde2000e926418619fa3
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:14.954415Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:31:14.954415Z
    traceback: 

```

### WARNING Entry #17

```
=== WARNING - 2025-09-16T01:31:07.952996+00:00 ===
Insert ID: 68c8bddb000e8ad850b934fe
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #18

```
=== WARNING - 2025-09-16T01:31:07.426936+00:00 ===
Insert ID: 68c8bddb000683b827e2f900
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #19

```
=== WARNING - 2025-09-16T01:31:06.801994+00:00 ===
Insert ID: 68c8bdda000c3cca7eb52b35
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:06.801574Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:31:06.801574Z
    traceback: 

```

### WARNING Entry #20

```
=== WARNING - 2025-09-16T01:31:00.091431+00:00 ===
Insert ID: 68c8bdd40001655c3cd3a66d
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #21

```
=== WARNING - 2025-09-16T01:30:59.506397+00:00 ===
Insert ID: 68c8bdd30007ba1d6bc00f79
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #22

```
=== WARNING - 2025-09-16T01:30:58.813243+00:00 ===
Insert ID: 68c8bdd2000c68bb25d4cc4e
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:30:58.812795Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:30:58.812795Z
    traceback: 

```

### WARNING Entry #23

```
=== WARNING - 2025-09-16T01:30:52.094038+00:00 ===
Insert ID: 68c8bdcc00016f8961033f34
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #24

```
=== WARNING - 2025-09-16T01:30:51.581942+00:00 ===
Insert ID: 68c8bdcb0008e13678194155
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #25

```
=== WARNING - 2025-09-16T01:30:50.939304+00:00 ===
Insert ID: 68c8bdca000e55280a52538f
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:30:50.938793Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:30:50.938793Z
    traceback: 

```

### WARNING Entry #26

```
=== WARNING - 2025-09-16T01:30:44.275045+00:00 ===
Insert ID: 68c8bdc4000432dbb690a751
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #27

```
=== WARNING - 2025-09-16T01:30:43.723472+00:00 ===
Insert ID: 68c8bdc3000b0a1061beaaa4
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #28

```
=== WARNING - 2025-09-16T01:30:43.101993+00:00 ===
Insert ID: 68c8bdc300018e69d7fdaefb
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:30:43.101480Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:30:43.101480Z
    traceback: 

```

### WARNING Entry #29

```
=== WARNING - 2025-09-16T01:30:36.382913+00:00 ===
Insert ID: 68c8bdbc0005d7f5541de001
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #30

```
=== WARNING - 2025-09-16T01:30:35.837946+00:00 ===
Insert ID: 68c8bdbb000cc93a9dc6aaab
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #31

```
=== WARNING - 2025-09-16T01:30:35.183662+00:00 ===
Insert ID: 68c8bdbb0002cd6ef01fde79
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:30:35.183132Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:30:35.183132Z
    traceback: 

```

### WARNING Entry #32

```
=== WARNING - 2025-09-16T01:30:28.048020+00:00 ===
Insert ID: 68c8bdb40000bbd5c4dccb9c
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #33

```
=== WARNING - 2025-09-16T01:30:27.497496+00:00 ===
Insert ID: 68c8bdb3000797584cb2d900
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #34

```
=== WARNING - 2025-09-16T01:30:26.869831+00:00 ===
Insert ID: 68c8bdb2000d45c782dd9135
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:30:26.869345Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:30:26.869345Z
    traceback: 

```

### WARNING Entry #35

```
=== WARNING - 2025-09-16T01:30:20.165811+00:00 ===
Insert ID: 68c8bdac000287f7d5b67e3e
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #36

```
=== WARNING - 2025-09-16T01:30:19.608211+00:00 ===
Insert ID: 68c8bdab000947d39a8111df
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #37

```
=== WARNING - 2025-09-16T01:30:18.941641+00:00 ===
Insert ID: 68c8bdaa000e5e49f7fcfa1a
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:30:18.941165Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:30:18.941165Z
    traceback: 

```

### WARNING Entry #38

```
=== WARNING - 2025-09-16T01:30:12.328510+00:00 ===
Insert ID: 68c8bda400050374f619f86c
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #39

```
=== WARNING - 2025-09-16T01:30:11.760626+00:00 ===
Insert ID: 68c8bda3000b9b322a97d80b
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #40

```
=== WARNING - 2025-09-16T01:30:11.037505+00:00 ===
Insert ID: 68c8bda3000092813a6041c8
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:30:11.036831Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:30:11.036831Z
    traceback: 

```

### WARNING Entry #41

```
=== WARNING - 2025-09-16T01:30:03.952550+00:00 ===
Insert ID: 68c8bd9b000e891b5fb62a54
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #42

```
=== WARNING - 2025-09-16T01:30:03.396915+00:00 ===
Insert ID: 68c8bd9b00060e7324abb937
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #43

```
=== WARNING - 2025-09-16T01:30:02.741891+00:00 ===
Insert ID: 68c8bd9a000b5203bf14a607
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:30:02.741324Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:30:02.741324Z
    traceback: 

```

### WARNING Entry #44

```
=== WARNING - 2025-09-16T01:29:56.026386+00:00 ===
Insert ID: 68c8bd940000675ae1360d0e
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #45

```
=== WARNING - 2025-09-16T01:29:55.474199+00:00 ===
Insert ID: 68c8bd9300073c57e5a4c724
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #46

```
=== WARNING - 2025-09-16T01:29:54.840234+00:00 ===
Insert ID: 68c8bd92000cd22a041a24cf
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:29:54.839751Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:29:54.839751Z
    traceback: 

```

### WARNING Entry #47

```
=== WARNING - 2025-09-16T01:29:41.257599+00:00 ===
Insert ID: 68c8bd850003eecc39988db7
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #48

```
=== WARNING - 2025-09-16T01:29:40.601643+00:00 ===
Insert ID: 68c8bd8400092e2bc49b5534
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #49

```
=== WARNING - 2025-09-16T01:29:39.000291+00:00 ===
Insert ID: 68c8bd83000001233666ec09
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:29:38.996285Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:29:38.996285Z
    traceback: 

```

### WARNING Entry #50

```
=== WARNING - 2025-09-16T01:29:29.563997+00:00 ===
Insert ID: 68c8bd7900089b5ffd759fdf
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

## NOTICE Logs (12 entries)

### NOTICE Entry #1

```
=== NOTICE - 2025-09-16T01:23:57.600777+00:00 ===
Insert ID: 167whd8dcs26
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #2

```
=== NOTICE - 2025-09-16T01:23:36.847900+00:00 ===
Insert ID: 1g60r8zdc18i
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #3

```
=== NOTICE - 2025-09-16T01:23:01.486570+00:00 ===
Insert ID: 1kxuzx8dcj4w
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #4

```
=== NOTICE - 2025-09-16T01:22:24.109526+00:00 ===
Insert ID: 7rvz0gdinoq
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #5

```
=== NOTICE - 2025-09-16T00:54:07.490095+00:00 ===
Insert ID: 148oicydfhtx
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #6

```
=== NOTICE - 2025-09-16T00:53:46.668212+00:00 ===
Insert ID: 1h1vyrfdbctm
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #7

```
=== NOTICE - 2025-09-16T00:52:21.275350+00:00 ===
Insert ID: 13f4nzydi03z
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #8

```
=== NOTICE - 2025-09-16T00:51:55.521099+00:00 ===
Insert ID: 1b721dxdbkxx
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #9

```
=== NOTICE - 2025-09-16T00:48:12.932456+00:00 ===
Insert ID: bnutoaddnpf
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #10

```
=== NOTICE - 2025-09-16T00:47:44.832545+00:00 ===
Insert ID: 16qadvwdb86i
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #11

```
=== NOTICE - 2025-09-16T00:46:15.567601+00:00 ===
Insert ID: 1ac96vwd9g1a
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #12

```
=== NOTICE - 2025-09-16T00:45:41.411450+00:00 ===
Insert ID: 5ucugydbjen
Service: netra-backend-staging
JSON Payload:
  error:

```

## INFO Logs (50 entries)

### INFO Entry #1

```
=== INFO - 2025-09-16T01:32:01.606882+00:00 ===
Insert ID: 68c8be11000942a229127db6
Service: netra-backend-staging
JSON Payload:
  message: Creating enhanced WebSocket exclusion middleware inline (Issue #449 fallback)
  error:

```

### INFO Entry #2

```
=== INFO - 2025-09-16T01:32:01.601853+00:00 ===
Insert ID: 68c8be1100092efd96953fdc
Service: netra-backend-staging
JSON Payload:
  message: uvicorn-compatible SessionMiddleware configured for staging (Issue #449)
  error:

```

### INFO Entry #3

```
=== INFO - 2025-09-16T01:32:01.601275+00:00 ===
Insert ID: 68c8be1100092cbb7b8b98e4
Service: netra-backend-staging
JSON Payload:
  message: uvicorn-compatible SessionMiddleware installed (Issue #449)
  error:

```

### INFO Entry #4

```
=== INFO - 2025-09-16T01:32:01.601261+00:00 ===
Insert ID: 68c8be1100092cadf26ff33c
Service: netra-backend-staging
JSON Payload:
  message: Using config.secret_key for staging (length: 51)
  error:

```

### INFO Entry #5

```
=== INFO - 2025-09-16T01:32:01.595976+00:00 ===
Insert ID: 68c8be1100091808a5e73080
Service: netra-backend-staging
JSON Payload:
  message: AuthServiceClient initialized - Service ID: netra-backend, Service Secret=REDACTED True
  error:

```

### INFO Entry #6

```
=== INFO - 2025-09-16T01:32:01.595818+00:00 ===
Insert ID: 68c8be110009176a3dec3726
Service: netra-backend-staging
JSON Payload:
  message: TracingManager initialized
  error:

```

### INFO Entry #7

```
=== INFO - 2025-09-16T01:32:01.595175+00:00 ===
Insert ID: 68c8be11000914e7f77bd99c
Service: netra-backend-staging
JSON Payload:
  message: Tracer initialized: default
  error:

```

### INFO Entry #8

```
=== INFO - 2025-09-16T01:32:01.595017+00:00 ===
Insert ID: 68c8be11000914495c4a3612
Service: netra-backend-staging
JSON Payload:
  message: AuthCircuitBreakerManager initialized with UnifiedCircuitBreaker
  error:

```

### INFO Entry #9

```
=== INFO - 2025-09-16T01:32:01.594518+00:00 ===
Insert ID: 68c8be11000912567c2b1471
Service: netra-backend-staging
JSON Payload:
  message: AuthClientCache initialized with default TTL: 300s and user isolation
  error:

```

### INFO Entry #10

```
=== INFO - 2025-09-16T01:32:01.592505+00:00 ===
Insert ID: 68c8be1100090a7954960043
Service: netra-backend-staging
JSON Payload:
  message: AuthServiceClient initialized - Service ID: netra-backend, Service Secret=REDACTED True
  error:

```

### INFO Entry #11

```
=== INFO - 2025-09-16T01:32:01.591603+00:00 ===
Insert ID: 68c8be11000906f3dad81230
Service: netra-backend-staging
JSON Payload:
  message: Circuit breaker 'auth_service' initialized: threshold=3
  error:

```

### INFO Entry #12

```
=== INFO - 2025-09-16T01:32:01.590602+00:00 ===
Insert ID: 68c8be110009030a962153b8
Service: netra-backend-staging
JSON Payload:
  message: TracingManager initialized
  error:

```

### INFO Entry #13

```
=== INFO - 2025-09-16T01:32:01.590200+00:00 ===
Insert ID: 68c8be1100090178b2cf53c5
Service: netra-backend-staging
JSON Payload:
  message: Tracer initialized: default
  error:

```

### INFO Entry #14

```
=== INFO - 2025-09-16T01:32:01.589755+00:00 ===
Insert ID: 68c8be110008ffbba1f1134e
Service: netra-backend-staging
JSON Payload:
  message: AuthCircuitBreakerManager initialized with UnifiedCircuitBreaker
  error:

```

### INFO Entry #15

```
=== INFO - 2025-09-16T01:32:01.589705+00:00 ===
Insert ID: 68c8be110008ff8923795e5b
Service: netra-backend-staging
JSON Payload:
  message: AuthClientCache initialized with default TTL: 300s and user isolation
  error:

```

### INFO Entry #16

```
=== INFO - 2025-09-16T01:32:01.583570+00:00 ===
Insert ID: 68c8be110008e7928895845b
Service: netra-backend-staging
JSON Payload:
  message: AuthClientConfigManager initialized
  error:

```

### INFO Entry #17

```
=== INFO - 2025-09-16T01:32:01.574557+00:00 ===
Insert ID: 68c8be110008c45d8d48052d
Service: netra-backend-staging
JSON Payload:
  message: AuthCircuitBreakerManager initialized with UnifiedCircuitBreaker
  error:

```

### INFO Entry #18

```
=== INFO - 2025-09-16T01:32:01.574520+00:00 ===
Insert ID: 68c8be110008c438c4258288
Service: netra-backend-staging
JSON Payload:
  message: AuthClientCache initialized with default TTL: 300s and user isolation
  error:

```

### INFO Entry #19

```
=== INFO - 2025-09-16T01:32:01.544807+00:00 ===
Insert ID: 68c8be11000850279a527ec3
Service: netra-backend-staging
JSON Payload:
  message: Starting enhanced middleware setup with WebSocket exclusion support...
  error:

```

### INFO Entry #20

```
=== INFO - 2025-09-16T01:32:01.544164+00:00 ===
Insert ID: 68c8be1100084da457e6a17e
Service: netra-backend-staging
JSON Payload:
  message: OpenTelemetry automatic instrumentation initialized successfully
  error:

```

### INFO Entry #21

```
=== INFO - 2025-09-16T01:32:01.544145+00:00 ===
Insert ID: 68c8be1100084d919c291aa0
Service: netra-backend-staging
JSON Payload:
  message: OpenTelemetry automatic instrumentation initialized for netra-backend-staging in staging
  error:

```

### INFO Entry #22

```
=== INFO - 2025-09-16T01:32:00.879015+00:00 ===
Insert ID: 68c8be10000d69a7fb7e5933
Service: netra-backend-staging
JSON Payload:
  message: Telemetry enabled but no exporters configured - traces will not be exported. To enable tracing, either set OTEL_EXPORTER_OTLP_ENDPOINT or install google-cloud-trace package.
  error:

```

### INFO Entry #23

```
=== INFO - 2025-09-16T01:32:00.655125+00:00 ===
Insert ID: 68c8be100009ff151da8953d
Service: netra-backend-staging
JSON Payload:
  message: Configuration loaded and cached for environment: staging
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.654171Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.654171Z
    traceback: 

```

### INFO Entry #24

```
=== INFO - 2025-09-16T01:32:00.654416+00:00 ===
Insert ID: 68c8be100009fc50cd096fe0
Service: netra-backend-staging
JSON Payload:
  message: PASS:  All configuration requirements validated for staging
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.653766Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.653766Z
    traceback: 

```

### INFO Entry #25

```
=== INFO - 2025-09-16T01:32:00.654134+00:00 ===
Insert ID: 68c8be100009fb36be461194
Service: netra-backend-staging
JSON Payload:
  message: Database configuration: Using component-based configuration for staging environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.653424Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.653424Z
    traceback: 

```

### INFO Entry #26

```
=== INFO - 2025-09-16T01:32:00.653424+00:00 ===
Insert ID: 68c8be100009f8709c1af3ba
Service: netra-backend-staging
JSON Payload:
  message: Validating configuration requirements for staging environment (readiness verified)
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.652603Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.652603Z
    traceback: 

```

### INFO Entry #27

```
=== INFO - 2025-09-16T01:32:00.630481+00:00 ===
Insert ID: 68c8be1000099ed1e28b0e0e
Service: netra-backend-staging
JSON Payload:
  message: Database URL (staging/Cloud SQL): postgresql+asyncpg://***@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.629872Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.629872Z
    traceback: 

```

### INFO Entry #28

```
=== INFO - 2025-09-16T01:32:00.629892+00:00 ===
Insert ID: 68c8be1000099c84c3b7fedf
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_SECRET configured: True
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.629296Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.629296Z
    traceback: 

```

### INFO Entry #29

```
=== INFO - 2025-09-16T01:32:00.629875+00:00 ===
Insert ID: 68c8be1000099c73d2a760f2
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID configured: True
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.629196Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.629196Z
    traceback: 

```

### INFO Entry #30

```
=== INFO - 2025-09-16T01:32:00.629860+00:00 ===
Insert ID: 68c8be1000099c64a2e94496
Service: netra-backend-staging
JSON Payload:
  message: Loaded FERNET_KEY from environment
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.629097Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.629097Z
    traceback: 

```

### INFO Entry #31

```
=== INFO - 2025-09-16T01:32:00.629782+00:00 ===
Insert ID: 68c8be1000099c16f4685667
Service: netra-backend-staging
JSON Payload:
  message: Loaded SECRET_KEY from environment
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.628958Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.628958Z
    traceback: 

```

### INFO Entry #32

```
=== INFO - 2025-09-16T01:32:00.629609+00:00 ===
Insert ID: 68c8be1000099b69a857c993
Service: netra-backend-staging
JSON Payload:
  message: Loaded JWT_SECRET_KEY from environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.628832Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.628832Z
    traceback: 

```

### INFO Entry #33

```
=== INFO - 2025-09-16T01:32:00.629544+00:00 ===
Insert ID: 68c8be1000099b2899232ac3
Service: netra-backend-staging
JSON Payload:
  message: Loaded SERVICE_ID from environment
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.628691Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.628691Z
    traceback: 

```

### INFO Entry #34

```
=== INFO - 2025-09-16T01:32:00.629162+00:00 ===
Insert ID: 68c8be10000999aa3462fa69
Service: netra-backend-staging
JSON Payload:
  message: Loaded SERVICE_SECRET from environment
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.628539Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.628539Z
    traceback: 

```

### INFO Entry #35

```
=== INFO - 2025-09-16T01:32:00.628911+00:00 ===
Insert ID: 68c8be10000998af1f1cf1f1
Service: netra-backend-staging
JSON Payload:
  message: Creating StagingConfig for environment: staging
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.628161Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.628161Z
    traceback: 

```

### INFO Entry #36

```
=== INFO - 2025-09-16T01:32:00.628446+00:00 ===
Insert ID: 68c8be10000996de8285dc06
Service: netra-backend-staging
JSON Payload:
  message: Loading unified configuration
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.627482Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.627482Z
    traceback: 

```

### INFO Entry #37

```
=== INFO - 2025-09-16T01:32:00.579273+00:00 ===
Insert ID: 68c8be100008d6c90aaf2112
Service: netra-backend-staging
JSON Payload:
  message: BackgroundTaskManager initialized
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.578463Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.578463Z
    traceback: 

```

### INFO Entry #38

```
=== INFO - 2025-09-16T01:32:00.563098+00:00 ===
Insert ID: 68c8be100008979a70b0261a
Service: netra-backend-staging
JSON Payload:
  message: ErrorRecoveryManager initialized
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.562420Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.562420Z
    traceback: 

```

### INFO Entry #39

```
=== INFO - 2025-09-16T01:32:00.562274+00:00 ===
Insert ID: 68c8be1000089462bcd1ab1f
Service: netra-backend-staging
JSON Payload:
  message: ErrorRecoveryManager initialized
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.561480Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.561480Z
    traceback: 

```

### INFO Entry #40

```
=== INFO - 2025-09-16T01:32:00.121959+00:00 ===
Insert ID: 68c8be100001dc6795f96850
Service: netra-backend-staging
JSON Payload:
  message: UnifiedIDManager initialized
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:32:00.117649Z', 'traceback': ''}
  logger: netra_backend.app.core.unified_id_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:32:00.117649Z
    traceback: 

```

### INFO Entry #41

```
=== INFO - 2025-09-16T01:31:59.473694+00:00 ===
Insert ID: 68c8be0f00073a5e73e5e490
Service: netra-backend-staging
JSON Payload:
  message: WebSocket Error Validator compatibility module loaded with SSOT imports
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:59.472489Z', 'traceback': ''}
  logger: netra_backend.app.services.websocket_error_validator
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:31:59.472489Z
    traceback: 

```

### INFO Entry #42

```
=== INFO - 2025-09-16T01:31:59.458231+00:00 ===
Insert ID: 68c8be0f0006fdf7a8c4258c
Service: netra-backend-staging
JSON Payload:
  message: WebSocket SSOT loaded - CRITICAL SECURITY MIGRATION: Factory pattern available, singleton vulnerabilities mitigated
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:59.457539Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:31:59.457539Z
    traceback: 

```

### INFO Entry #43

```
=== INFO - 2025-09-16T01:31:59.453714+00:00 ===
Insert ID: 68c8be0f0006ec52162243be
Service: netra-backend-staging
JSON Payload:
  message: Factory methods added to UnifiedWebSocketEmitter - Issue #582 remediation complete
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:59.452973Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.unified_emitter
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:31:59.452973Z
    traceback: 

```

### INFO Entry #44

```
=== INFO - 2025-09-16T01:31:59.418982+00:00 ===
Insert ID: 68c8be0f000664a611e7b30a
Service: netra-backend-staging
JSON Payload:
  message: Enhanced RedisManager initialized with automatic recovery
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:59.417895Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:31:59.417895Z
    traceback: 

```

### INFO Entry #45

```
=== INFO - 2025-09-16T01:31:59.381354+00:00 ===
Insert ID: 68c8be0f0005d1aa8bcb054f
Service: netra-backend-staging
JSON Payload:
  message: Built database URL from POSTGRES_* environment variables
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:59.380781Z', 'traceback': ''}
  logger: logging
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-16T01:31:59.380781Z
    traceback: 

```

### INFO Entry #46

```
=== INFO - 2025-09-16T01:31:59.381312+00:00 ===
Insert ID: 68c8be0f0005d180f6edb7b7
Service: netra-backend-staging
JSON Payload:
  message: Database URL (staging/Cloud SQL): postgresql+asyncpg://***@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-16T01:31:59.380585Z', 'traceback': ''}
  logger: logging
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-16T01:31:59.380585Z
    traceback: 

```

### INFO Entry #47

```
=== INFO - 2025-09-16T01:31:57.636121+00:00 ===
Insert ID: 68c8be0d0009b4d9fc887828
Service: netra-backend-staging
Text Payload:
  Default STARTUP TCP probe succeeded after 1 attempt for container "netra-backend-staging-1" on port 8000.

```

### INFO Entry #48

```
=== INFO - 2025-09-16T01:31:54.159595+00:00 ===
Insert ID: 68c8be0a00026f6b95532991
Service: netra-backend-staging
Text Payload:
  Starting new instance. Reason: MANUAL_OR_CUSTOMER_MIN_INSTANCE - Instance started because of customer-configured min-instances or manual scaling.

```

### INFO Entry #49

```
=== INFO - 2025-09-16T01:31:53.162984+00:00 ===
Insert ID: 68c8be0900027ca89ffaf0d4
Service: netra-backend-staging
JSON Payload:
  message: Creating enhanced WebSocket exclusion middleware inline (Issue #449 fallback)
  error:

```

### INFO Entry #50

```
=== INFO - 2025-09-16T01:31:53.158825+00:00 ===
Insert ID: 68c8be0900026c6929c5ff11
Service: netra-backend-staging
JSON Payload:
  message: uvicorn-compatible SessionMiddleware configured for staging (Issue #449)
  error:

```
