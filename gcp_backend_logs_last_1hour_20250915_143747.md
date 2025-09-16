# GCP Backend Service Logs - Last 1 Hour

**Collection Time:** 2025-09-15 14:37:47 
**Time Range:** 2025-09-15 20:37:44 UTC to 2025-09-15 21:37:44 UTC
**Total Logs:** 163

## Summary by Severity
- **ERROR:** 50 entries
- **WARNING:** 50 entries
- **NOTICE:** 13 entries
- **INFO:** 50 entries

## ERROR Logs (50 entries)

### ERROR Entry #1

```
=== ERROR - 2025-09-15T21:37:17.707975+00:00 ===
Insert ID: 68c8870d000acd87ab41bf3e
Service: netra-backend-staging
JSON Payload:
  message: Application startup failed. Exiting.
  error:

```

### ERROR Entry #2

```
=== ERROR - 2025-09-15T21:37:17.707244+00:00 ===
Insert ID: 68c8870d000acaacfbd8ae68
Service: netra-backend-staging
JSON Payload:
  message: uvicorn-compatible session middleware error: CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES...
  error: {'value': 'CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.', 'type': 'DeterministicStartupError', 'traceback': None}
  error:
    value: CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance ac...
    type: DeterministicStartupError
    traceback: None

```

### ERROR Entry #3

```
=== ERROR - 2025-09-15T21:37:17.687280+00:00 ===
Insert ID: 68c8870d000a7cb0ff2da060
Service: netra-backend-staging
JSON Payload:
  message: Traceback (most recent call last):\n  File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for\n    return fut.result()\n           ^^^^^^^^^^^^\n  File "/app/netra_backend/app/startup...
  error:

```

### ERROR Entry #4

```
=== ERROR - 2025-09-15T21:37:17.547789+00:00 ===
Insert ID: 68c8870d00085bcd9c5cd807
Service: netra-backend-staging
JSON Payload:
  message:  FAIL:  PHASE FAILED: DATABASE - Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL inst...
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### ERROR Entry #5

```
=== ERROR - 2025-09-15T21:37:17.546114+00:00 ===
Insert ID: 68c8870d000855427814bf3f
Service: netra-backend-staging
JSON Payload:
  message: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### ERROR Entry #6

```
=== ERROR - 2025-09-15T21:37:07.407582+00:00 ===
Insert ID: 68c887030006381e2c6c160c
Service: netra-backend-staging
JSON Payload:
  message: Failed to run migrations: (psycopg2.OperationalError) connection to server on socket "/cloudsql/netra-staging:us-central1:staging-shared-postgres/.s.PGSQL.5432" failed: server closed the connection un...
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### ERROR Entry #7

```
=== ERROR - 2025-09-15T21:37:05.973721+00:00 ===
Insert ID: 68c8870f000057b4e069710f
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 13.045507683s

```

### ERROR Entry #8

```
=== ERROR - 2025-09-15T21:37:00.640179+00:00 ===
Insert ID: 68c8870f0000558a37a2476c
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 18.378426784s

```

### ERROR Entry #9

```
=== ERROR - 2025-09-15T21:36:55.276285+00:00 ===
Insert ID: 68c8870f00005c919aebe68c
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 23.743715649s

```

### ERROR Entry #10

```
=== ERROR - 2025-09-15T21:36:50.022001+00:00 ===
Insert ID: 68c8870f0000574b534bd67e
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 28.996166841s

```

### ERROR Entry #11

```
=== ERROR - 2025-09-15T21:36:44.743802+00:00 ===
Insert ID: 68c8870f000056f4758264e4
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 34.273805341s

```

### ERROR Entry #12

```
=== ERROR - 2025-09-15T21:36:39.505109+00:00 ===
Insert ID: 68c8870f0000571168099a98
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 39.511846650s

```

### ERROR Entry #13

```
=== ERROR - 2025-09-15T21:36:34.273632+00:00 ===
Insert ID: 68c8870f00005759d31b05a9
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 44.741578100s

```

### ERROR Entry #14

```
=== ERROR - 2025-09-15T21:36:29.063851+00:00 ===
Insert ID: 68c8870f000056d3a1a53479
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 49.952255183s

```

### ERROR Entry #15

```
=== ERROR - 2025-09-15T21:36:23.841360+00:00 ===
Insert ID: 68c8870f00007bbbde57f4b0
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 55.024305314s

```

### ERROR Entry #16

```
=== ERROR - 2025-09-15T21:36:22.216925+00:00 ===
Insert ID: 68c886d600034f5dba22c3cc
Service: netra-backend-staging
JSON Payload:
  message: Application startup failed. Exiting.
  error:

```

### ERROR Entry #17

```
=== ERROR - 2025-09-15T21:36:22.216913+00:00 ===
Insert ID: 68c886d600034f5153650818
Service: netra-backend-staging
JSON Payload:
  message: uvicorn-compatible session middleware error: CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES...
  error: {'value': 'CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.', 'type': 'DeterministicStartupError', 'traceback': None}
  error:
    value: CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance ac...
    type: DeterministicStartupError
    traceback: None

```

### ERROR Entry #18

```
=== ERROR - 2025-09-15T21:36:22.192708+00:00 ===
Insert ID: 68c886d60002f0c48bee57cc
Service: netra-backend-staging
JSON Payload:
  message: Traceback (most recent call last):\n  File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for\n    return fut.result()\n           ^^^^^^^^^^^^\n  File "/app/netra_backend/app/startup...
  error:

```

### ERROR Entry #19

```
=== ERROR - 2025-09-15T21:36:22.052912+00:00 ===
Insert ID: 68c886d60000ceb005e8f264
Service: netra-backend-staging
JSON Payload:
  message:  FAIL:  PHASE FAILED: DATABASE - Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL inst...
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### ERROR Entry #20

```
=== ERROR - 2025-09-15T21:36:22.052775+00:00 ===
Insert ID: 68c886d60000ce2725f503c8
Service: netra-backend-staging
JSON Payload:
  message: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### ERROR Entry #21

```
=== ERROR - 2025-09-15T21:36:19.832364+00:00 ===
Insert ID: 68c886d70007840fb947c55a
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 3.658183038s

```

### ERROR Entry #22

```
=== ERROR - 2025-09-15T21:36:14.494627+00:00 ===
Insert ID: 68c886d70007844fbc69f07f
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 8.995500689s

```

### ERROR Entry #23

```
=== ERROR - 2025-09-15T21:36:11.725199+00:00 ===
Insert ID: 68c886cb000b10cf9b264073
Service: netra-backend-staging
JSON Payload:
  message: Failed to run migrations: (psycopg2.OperationalError) connection to server on socket "/cloudsql/netra-staging:us-central1:staging-shared-postgres/.s.PGSQL.5432" failed: server closed the connection un...
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### ERROR Entry #24

```
=== ERROR - 2025-09-15T21:36:09.233702+00:00 ===
Insert ID: 68c886d7000782b1c9f8650f
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 14.255626429s

```

### ERROR Entry #25

```
=== ERROR - 2025-09-15T21:36:03.972989+00:00 ===
Insert ID: 68c886d700078400562bef68
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 19.516417328s

```

### ERROR Entry #26

```
=== ERROR - 2025-09-15T21:35:58.709520+00:00 ===
Insert ID: 68c886d7000782a52d3f98e9
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 24.778704660s

```

### ERROR Entry #27

```
=== ERROR - 2025-09-15T21:35:53.483867+00:00 ===
Insert ID: 68c886d7000783f51810f5fa
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 30.004461262s

```

### ERROR Entry #28

```
=== ERROR - 2025-09-15T21:35:48.980787+00:00 ===
Insert ID: 68c886d70007827efb5816a2
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 34.506534031s

```

### ERROR Entry #29

```
=== ERROR - 2025-09-15T21:35:42.956765+00:00 ===
Insert ID: 68c886d70007829b7ad7875b
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 40.529951079s

```

### ERROR Entry #30

```
=== ERROR - 2025-09-15T21:35:37.692305+00:00 ===
Insert ID: 68c886d70007837056c9e133
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 45.794145507s

```

### ERROR Entry #31

```
=== ERROR - 2025-09-15T21:35:32.381262+00:00 ===
Insert ID: 68c886d700078513e5df2763
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 51.104782105s

```

### ERROR Entry #32

```
=== ERROR - 2025-09-15T21:35:27.138102+00:00 ===
Insert ID: 68c886d700078373a20ec9bb
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 56.347406840s

```

### ERROR Entry #33

```
=== ERROR - 2025-09-15T21:35:21.922040+00:00 ===
Insert ID: 68c886d7000782c5ebb450d3
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 61.562894911s

```

### ERROR Entry #34

```
=== ERROR - 2025-09-15T21:35:21.887707+00:00 ===
Insert ID: 68c88699000d8b9b01cafeba
Service: netra-backend-staging
JSON Payload:
  message: Traceback (most recent call last):\n  File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for\n    return fut.result()\n           ^^^^^^^^^^^^\n  File "/app/netra_backend/app/startup...
  error:

```

### ERROR Entry #35

```
=== ERROR - 2025-09-15T21:35:21.760304+00:00 ===
Insert ID: 68c88699000b99f001389adb
Service: netra-backend-staging
JSON Payload:
  message:  FAIL:  PHASE FAILED: DATABASE - Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL inst...
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### ERROR Entry #36

```
=== ERROR - 2025-09-15T21:35:21.757016+00:00 ===
Insert ID: 68c88699000b8d185c0ef7eb
Service: netra-backend-staging
JSON Payload:
  message: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### ERROR Entry #37

```
=== ERROR - 2025-09-15T21:35:16.243675+00:00 ===
Insert ID: 68c886d70007828db8a7a1b0
Service: netra-backend-staging
Text Payload:
  The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/docs/troubleshooting#malformed-response-or-connection-error
HTTP Request:
  method: GET
  url: https://api.staging.netrasystems.ai/health
  status: 503
  user_agent: python-httpx/0.28.1
  latency: 67.228814580s

```

### ERROR Entry #38

```
=== ERROR - 2025-09-15T21:35:11.599639+00:00 ===
Insert ID: 68c8868f00092657acb03503
Service: netra-backend-staging
JSON Payload:
  message: Failed to run migrations: (psycopg2.OperationalError) connection to server on socket "/cloudsql/netra-staging:us-central1:staging-shared-postgres/.s.PGSQL.5432" failed: server closed the connection un...
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### ERROR Entry #39

```
=== ERROR - 2025-09-15T21:34:14.497992+00:00 ===
Insert ID: 68c886560007994827ca677b
Service: netra-backend-staging
JSON Payload:
  message: Application startup failed. Exiting.
  error:

```

### ERROR Entry #40

```
=== ERROR - 2025-09-15T21:34:14.497902+00:00 ===
Insert ID: 68c88656000798ee6ce9a979
Service: netra-backend-staging
JSON Payload:
  message: uvicorn-compatible session middleware error: CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES...
  error: {'value': 'CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.', 'type': 'DeterministicStartupError', 'traceback': None}
  error:
    value: CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance ac...
    type: DeterministicStartupError
    traceback: None

```

### ERROR Entry #41

```
=== ERROR - 2025-09-15T21:34:14.467384+00:00 ===
Insert ID: 68c88656000721b84dbe25cd
Service: netra-backend-staging
JSON Payload:
  message: Traceback (most recent call last):\n  File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for\n    return fut.result()\n           ^^^^^^^^^^^^\n  File "/app/netra_backend/app/startup...
  error:

```

### ERROR Entry #42

```
=== ERROR - 2025-09-15T21:34:14.332169+00:00 ===
Insert ID: 68c88656000511893a29a80e
Service: netra-backend-staging
JSON Payload:
  message:  FAIL:  PHASE FAILED: DATABASE - Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL inst...
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### ERROR Entry #43

```
=== ERROR - 2025-09-15T21:34:14.332060+00:00 ===
Insert ID: 68c886560005111caff09627
Service: netra-backend-staging
JSON Payload:
  message: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### ERROR Entry #44

```
=== ERROR - 2025-09-15T21:34:04.135798+00:00 ===
Insert ID: 68c8864c000212760938eb42
Service: netra-backend-staging
JSON Payload:
  message: Failed to run migrations: (psycopg2.OperationalError) connection to server on socket "/cloudsql/netra-staging:us-central1:staging-shared-postgres/.s.PGSQL.5432" failed: server closed the connection un...
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### ERROR Entry #45

```
=== ERROR - 2025-09-15T21:33:11.739121+00:00 ===
Insert ID: 68c88617000b4731cbf4c805
Service: netra-backend-staging
JSON Payload:
  message: Application startup failed. Exiting.
  error:

```

### ERROR Entry #46

```
=== ERROR - 2025-09-15T21:33:11.738688+00:00 ===
Insert ID: 68c88617000b4580de58a2af
Service: netra-backend-staging
JSON Payload:
  message: uvicorn-compatible session middleware error: CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES...
  error: {'value': 'CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.', 'type': 'DeterministicStartupError', 'traceback': None}
  error:
    value: CRITICAL STARTUP FAILURE: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance ac...
    type: DeterministicStartupError
    traceback: None

```

### ERROR Entry #47

```
=== ERROR - 2025-09-15T21:33:11.724993+00:00 ===
Insert ID: 68c88617000b1001e211d48c
Service: netra-backend-staging
JSON Payload:
  message: Traceback (most recent call last):\n  File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for\n    return fut.result()\n           ^^^^^^^^^^^^\n  File "/app/netra_backend/app/startup...
  error:

```

### ERROR Entry #48

```
=== ERROR - 2025-09-15T21:33:11.590993+00:00 ===
Insert ID: 68c8861700090491b0851c4e
Service: netra-backend-staging
JSON Payload:
  message:  FAIL:  PHASE FAILED: DATABASE - Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL inst...
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### ERROR Entry #49

```
=== ERROR - 2025-09-15T21:33:11.590756+00:00 ===
Insert ID: 68c88617000903a4a7d88d6b
Service: netra-backend-staging
JSON Payload:
  message: Database initialization timeout after 25.0s in staging environment. This may indicate Cloud SQL connection issues. Check POSTGRES_HOST configuration and Cloud SQL instance accessibility.
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### ERROR Entry #50

```
=== ERROR - 2025-09-15T21:33:01.414140+00:00 ===
Insert ID: 68c8860d000651bc3c24593c
Service: netra-backend-staging
JSON Payload:
  message: Failed to run migrations: (psycopg2.OperationalError) connection to server on socket "/cloudsql/netra-staging:us-central1:staging-shared-postgres/.s.PGSQL.5432" failed: server closed the connection un...
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

## WARNING Logs (50 entries)

### WARNING Entry #1

```
=== WARNING - 2025-09-15T21:37:25.944365+00:00 ===
Insert ID: 68c88715000e68edad14db26
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #2

```
=== WARNING - 2025-09-15T21:37:24.844118+00:00 ===
Insert ID: 68c88714000ce1565c1cf79f
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:37:24.841813Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T21:37:24.841813Z
    traceback: 

```

### WARNING Entry #3

```
=== WARNING - 2025-09-15T21:37:23.488422+00:00 ===
Insert ID: 68c88713000773e6c60ced44
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:37:23.486030Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T21:37:23.486030Z
    traceback: 

```

### WARNING Entry #4

```
=== WARNING - 2025-09-15T21:37:07.428187+00:00 ===
Insert ID: 68c887030006889b093f8cd0
Service: netra-backend-staging
JSON Payload:
  message:    WARNING:  OAuth=REDACTED URI mismatch (non-critical in staging): https://app.staging.netra.ai/auth/callback vs https://app.staging.netrasystems.ai
  error:

```

### WARNING Entry #5

```
=== WARNING - 2025-09-15T21:37:07.408494+00:00 ===
Insert ID: 68c8870300063bae476b4a70
Service: netra-backend-staging
JSON Payload:
  message: Continuing without migrations
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### WARNING Entry #6

```
=== WARNING - 2025-09-15T21:36:30.321473+00:00 ===
Insert ID: 68c886de0004e7c187b7b7aa
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #7

```
=== WARNING - 2025-09-15T21:36:29.106584+00:00 ===
Insert ID: 68c886dd0001a0585a5c50ab
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:36:29.105231Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T21:36:29.105231Z
    traceback: 

```

### WARNING Entry #8

```
=== WARNING - 2025-09-15T21:36:27.768795+00:00 ===
Insert ID: 68c886db000bbb1bc6753259
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:36:27.761146Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T21:36:27.761146Z
    traceback: 

```

### WARNING Entry #9

```
=== WARNING - 2025-09-15T21:36:11.746670+00:00 ===
Insert ID: 68c886cb000b64aecab540aa
Service: netra-backend-staging
JSON Payload:
  message:    WARNING:  OAuth=REDACTED URI mismatch (non-critical in staging): https://app.staging.netra.ai/auth/callback vs https://app.staging.netrasystems.ai
  error:

```

### WARNING Entry #10

```
=== WARNING - 2025-09-15T21:36:11.725709+00:00 ===
Insert ID: 68c886cb000b12cd2c5e3925
Service: netra-backend-staging
JSON Payload:
  message: Continuing without migrations
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### WARNING Entry #11

```
=== WARNING - 2025-09-15T21:35:17.542385+00:00 ===
Insert ID: 68c88695000846b15ced4e19
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #12

```
=== WARNING - 2025-09-15T21:35:15.075801+00:00 ===
Insert ID: 68c8869300012819e5ac30a0
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:35:15.074518Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T21:35:15.074518Z
    traceback: 

```

### WARNING Entry #13

```
=== WARNING - 2025-09-15T21:35:12.516789+00:00 ===
Insert ID: 68c886900007e2b5cbc1b884
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:35:12.515284Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T21:35:12.515284Z
    traceback: 

```

### WARNING Entry #14

```
=== WARNING - 2025-09-15T21:35:11.617814+00:00 ===
Insert ID: 68c8868f00096d568e0e2c5d
Service: netra-backend-staging
JSON Payload:
  message:    WARNING:  OAuth=REDACTED URI mismatch (non-critical in staging): https://app.staging.netra.ai/auth/callback vs https://app.staging.netrasystems.ai
  error:

```

### WARNING Entry #15

```
=== WARNING - 2025-09-15T21:35:11.599660+00:00 ===
Insert ID: 68c8868f0009266c1bb089ed
Service: netra-backend-staging
JSON Payload:
  message: Continuing without migrations
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### WARNING Entry #16

```
=== WARNING - 2025-09-15T21:34:30.231602+00:00 ===
Insert ID: 68c88666000388b2645cf296
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #17

```
=== WARNING - 2025-09-15T21:34:28.508253+00:00 ===
Insert ID: 68c886640007c15d21e800c0
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:34:28.507859Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T21:34:28.507859Z
    traceback: 

```

### WARNING Entry #18

```
=== WARNING - 2025-09-15T21:34:26.576575+00:00 ===
Insert ID: 68c886620008cc3ffc0ed516
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:34:26.575971Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T21:34:26.575971Z
    traceback: 

```

### WARNING Entry #19

```
=== WARNING - 2025-09-15T21:34:15.933849+00:00 ===
Insert ID: 68c88657000e4059229a5908
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #20

```
=== WARNING - 2025-09-15T21:34:04.189990+00:00 ===
Insert ID: 68c8864c0002e6266f8be351
Service: netra-backend-staging
JSON Payload:
  message:    WARNING:  OAuth=REDACTED URI mismatch (non-critical in staging): https://app.staging.netra.ai/auth/callback vs https://app.staging.netrasystems.ai
  error:

```

### WARNING Entry #21

```
=== WARNING - 2025-09-15T21:34:04.136160+00:00 ===
Insert ID: 68c8864c000213e04c02e222
Service: netra-backend-staging
JSON Payload:
  message: Continuing without migrations
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### WARNING Entry #22

```
=== WARNING - 2025-09-15T21:33:23.227316+00:00 ===
Insert ID: 68c88623000377f42d76d250
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #23

```
=== WARNING - 2025-09-15T21:33:21.446204+00:00 ===
Insert ID: 68c886210006cefc1384f5ea
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:33:21.446012Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T21:33:21.446012Z
    traceback: 

```

### WARNING Entry #24

```
=== WARNING - 2025-09-15T21:33:19.825038+00:00 ===
Insert ID: 68c8861f000c96ce11d047da
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:33:19.824586Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T21:33:19.824586Z
    traceback: 

```

### WARNING Entry #25

```
=== WARNING - 2025-09-15T21:33:01.435541+00:00 ===
Insert ID: 68c8860d0006a5552ac4b72b
Service: netra-backend-staging
JSON Payload:
  message:    WARNING:  OAuth=REDACTED URI mismatch (non-critical in staging): https://app.staging.netra.ai/auth/callback vs https://app.staging.netrasystems.ai
  error:

```

### WARNING Entry #26

```
=== WARNING - 2025-09-15T21:33:01.414200+00:00 ===
Insert ID: 68c8860d000651f8523b5684
Service: netra-backend-staging
JSON Payload:
  message: Continuing without migrations
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### WARNING Entry #27

```
=== WARNING - 2025-09-15T21:32:20.021346+00:00 ===
Insert ID: 68c885e4000053629fed3462
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #28

```
=== WARNING - 2025-09-15T21:32:18.088174+00:00 ===
Insert ID: 68c885e20001586eea8a7de0
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:32:18.088010Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T21:32:18.088010Z
    traceback: 

```

### WARNING Entry #29

```
=== WARNING - 2025-09-15T21:32:16.291526+00:00 ===
Insert ID: 68c885e0000472c6573fbec4
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:32:16.290696Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T21:32:16.290696Z
    traceback: 

```

### WARNING Entry #30

```
=== WARNING - 2025-09-15T21:32:05.516830+00:00 ===
Insert ID: 68c885d50007e352f2b4dbe0
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #31

```
=== WARNING - 2025-09-15T21:31:53.815854+00:00 ===
Insert ID: 68c885c9000c72eee89465be
Service: netra-backend-staging
JSON Payload:
  message:    WARNING:  OAuth=REDACTED URI mismatch (non-critical in staging): https://app.staging.netra.ai/auth/callback vs https://app.staging.netrasystems.ai
  error:

```

### WARNING Entry #32

```
=== WARNING - 2025-09-15T21:31:53.794864+00:00 ===
Insert ID: 68c885c9000c20f00d5bfb47
Service: netra-backend-staging
JSON Payload:
  message: Continuing without migrations
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### WARNING Entry #33

```
=== WARNING - 2025-09-15T21:31:12.131034+00:00 ===
Insert ID: 68c885a00001ffda81aa9fba
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #34

```
=== WARNING - 2025-09-15T21:31:10.278859+00:00 ===
Insert ID: 68c8859e0004414b66cd96c3
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:31:10.278640Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T21:31:10.278640Z
    traceback: 

```

### WARNING Entry #35

```
=== WARNING - 2025-09-15T21:31:08.403257+00:00 ===
Insert ID: 68c8859c00062739892591b1
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:31:08.402718Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T21:31:08.402718Z
    traceback: 

```

### WARNING Entry #36

```
=== WARNING - 2025-09-15T21:30:58.644413+00:00 ===
Insert ID: 68c885920009d5afcf2ac450
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #37

```
=== WARNING - 2025-09-15T21:30:46.870521+00:00 ===
Insert ID: 68c88586000d4879546b15f5
Service: netra-backend-staging
JSON Payload:
  message:    WARNING:  OAuth=REDACTED URI mismatch (non-critical in staging): https://app.staging.netra.ai/auth/callback vs https://app.staging.netrasystems.ai
  error:

```

### WARNING Entry #38

```
=== WARNING - 2025-09-15T21:30:46.850453+00:00 ===
Insert ID: 68c88586000cfa159a7b5dff
Service: netra-backend-staging
JSON Payload:
  message: Continuing without migrations
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### WARNING Entry #39

```
=== WARNING - 2025-09-15T21:30:05.324929+00:00 ===
Insert ID: 68c8855d0004f541a2f0a7a9
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #40

```
=== WARNING - 2025-09-15T21:30:03.053460+00:00 ===
Insert ID: 68c8855b0000d0d4adbe0b90
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:30:03.053220Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T21:30:03.053220Z
    traceback: 

```

### WARNING Entry #41

```
=== WARNING - 2025-09-15T21:30:01.020960+00:00 ===
Insert ID: 68c88559000051e07c15443f
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:30:01.020479Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T21:30:01.020479Z
    traceback: 

```

### WARNING Entry #42

```
=== WARNING - 2025-09-15T21:29:50.901051+00:00 ===
Insert ID: 68c8854e000dc03d043f8f3e
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #43

```
=== WARNING - 2025-09-15T21:29:39.195004+00:00 ===
Insert ID: 68c885430002f9bc9e86b2e2
Service: netra-backend-staging
JSON Payload:
  message:    WARNING:  OAuth=REDACTED URI mismatch (non-critical in staging): https://app.staging.netra.ai/auth/callback vs https://app.staging.netrasystems.ai
  error:

```

### WARNING Entry #44

```
=== WARNING - 2025-09-15T21:29:39.180547+00:00 ===
Insert ID: 68c885430002c143e27bd14b
Service: netra-backend-staging
JSON Payload:
  message: Continuing without migrations
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### WARNING Entry #45

```
=== WARNING - 2025-09-15T21:28:58.899130+00:00 ===
Insert ID: 68c8851a000db83a9e22f620
Service: netra-backend-staging
JSON Payload:
  message: Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
  error:

```

### WARNING Entry #46

```
=== WARNING - 2025-09-15T21:28:57.278497+00:00 ===
Insert ID: 68c8851900043fe1cab46092
Service: netra-backend-staging
JSON Payload:
  message: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
  error: {'type': 'str', 'message': 'Missing field', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:28:57.276546Z', 'traceback': ''}
  logger: shared.logging.unified_logging_ssot
  error:
    type: str
    message: Missing field
    severity: ERROR
    timestamp: 2025-09-15T21:28:57.276546Z
    traceback: 

```

### WARNING Entry #47

```
=== WARNING - 2025-09-15T21:28:55.551078+00:00 ===
Insert ID: 68c88517000868a67a28c21e
Service: netra-backend-staging
JSON Payload:
  message: SSOT WARNING: Found other WebSocket Manager classes: ['netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager', 'netra_backend.app.websocket_core.websocket_manager.WebSocketManager...
  error: {'message': 'Missing field', 'type': 'str', 'severity': 'ERROR', 'timestamp': '2025-09-15T21:28:55.550509Z', 'traceback': ''}
  logger: netra_backend.app.websocket_core.websocket_manager
  error:
    message: Missing field
    type: str
    severity: ERROR
    timestamp: 2025-09-15T21:28:55.550509Z
    traceback: 

```

### WARNING Entry #48

```
=== WARNING - 2025-09-15T21:28:46.213539+00:00 ===
Insert ID: 68c8850e000342a03a50e42c
Service: netra-backend-staging
Text Payload:
  Container called exit(3).

```

### WARNING Entry #49

```
=== WARNING - 2025-09-15T21:28:34.637530+00:00 ===
Insert ID: 68c885020009ba5a7a240caa
Service: netra-backend-staging
JSON Payload:
  message:    WARNING:  OAuth=REDACTED URI mismatch (non-critical in staging): https://app.staging.netra.ai/auth/callback vs https://app.staging.netrasystems.ai
  error:

```

### WARNING Entry #50

```
=== WARNING - 2025-09-15T21:28:34.622823+00:00 ===
Insert ID: 68c88502000980e7448e9191
Service: netra-backend-staging
JSON Payload:
  message: Continuing without migrations
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

## NOTICE Logs (13 entries)

### NOTICE Entry #1

```
=== NOTICE - 2025-09-15T21:37:22.195561+00:00 ===
Insert ID: 4ztocmdb2fw
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #2

```
=== NOTICE - 2025-09-15T21:35:23.593650+00:00 ===
Insert ID: v2t2oodamro
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #3

```
=== NOTICE - 2025-09-15T21:35:23.546111+00:00 ===
Insert ID: 1ji2dq5dcqmp
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #4

```
=== NOTICE - 2025-09-15T21:33:44.423528+00:00 ===
Insert ID: 1ji2dq5dcqc9
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #5

```
=== NOTICE - 2025-09-15T21:33:41.055952+00:00 ===
Insert ID: 1ru7y82dauu2
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #6

```
=== NOTICE - 2025-09-15T21:17:39.433341+00:00 ===
Insert ID: 12b203vdagqc
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #7

```
=== NOTICE - 2025-09-15T21:16:41.994465+00:00 ===
Insert ID: 1h0hra3dar6m
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #8

```
=== NOTICE - 2025-09-15T21:14:00.152172+00:00 ===
Insert ID: v2t2oodajtl
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #9

```
=== NOTICE - 2025-09-15T21:13:08.048485+00:00 ===
Insert ID: kl3wc3darcd
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #10

```
=== NOTICE - 2025-09-15T21:06:04.257609+00:00 ===
Insert ID: 1ru7y82dare8
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #11

```
=== NOTICE - 2025-09-15T21:05:12.343841+00:00 ===
Insert ID: 17k9b87dajxe
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #12

```
=== NOTICE - 2025-09-15T20:38:51.653167+00:00 ===
Insert ID: w6w2grdbi92
Service: netra-backend-staging
JSON Payload:
  error:

```

### NOTICE Entry #13

```
=== NOTICE - 2025-09-15T20:38:01.857723+00:00 ===
Insert ID: 17m6246d9d4i
Service: netra-backend-staging
JSON Payload:
  error:

```

## INFO Logs (50 entries)

### INFO Entry #1

```
=== INFO - 2025-09-15T21:37:36.496956+00:00 ===
Insert ID: -saj75tdgn04
Service: netra-backend-staging
JSON Payload:
  error:

```

### INFO Entry #2

```
=== INFO - 2025-09-15T21:37:34.003312+00:00 ===
Insert ID: 68c8871e00000cf07a1f4d0d
Service: netra-backend-staging
Text Payload:
  Default STARTUP TCP probe succeeded after 1 attempt for container "netra-backend-staging-1" on port 8000.

```

### INFO Entry #3

```
=== INFO - 2025-09-15T21:37:34.002713+00:00 ===
Insert ID: 68c8871e00000a993f996ab6
Service: netra-backend-staging
Text Payload:
  Default STARTUP TCP probe succeeded after 1 attempt for container "netra-backend-staging-1" on port 8000.

```

### INFO Entry #4

```
=== INFO - 2025-09-15T21:37:32.886753+00:00 ===
Insert ID: 68c8871c000d87e16e30c816
Service: netra-backend-staging
JSON Payload:
  message: DatabaseIndexManager initialized
  context:
    name: netra_backend.app.db.index_optimizer
    service: netra-service
  error:

```

### INFO Entry #5

```
=== INFO - 2025-09-15T21:37:32.827050+00:00 ===
Insert ID: 68c8871c000c9eaae07440e0
Service: netra-backend-staging
JSON Payload:
  message:   [U+2713] Step 2.5: Environment context service initialized
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #6

```
=== INFO - 2025-09-15T21:37:32.826708+00:00 ===
Insert ID: 68c8871c000c9d548eaf1be2
Service: netra-backend-staging
JSON Payload:
  message: EnvironmentContextService initialized successfully with environment detection
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### INFO Entry #7

```
=== INFO - 2025-09-15T21:37:32.826452+00:00 ===
Insert ID: 68c8871c000c9c542c98e0cb
Service: netra-backend-staging
JSON Payload:
  message: EnvironmentContextService initialized successfully. Environment: staging, Platform: cloud_run
  context:
    service: netra-service
    name: netra_backend.app.core.environment_context.environment_context_service
  error:

```

### INFO Entry #8

```
=== INFO - 2025-09-15T21:37:32.825929+00:00 ===
Insert ID: 68c8871c000c9a49c83094c0
Service: netra-backend-staging
JSON Payload:
  message: ============================================================
  context:
    name: netra_backend.app.core.environment_context.cloud_environment_detector
    service: netra-service
  error:

```

### INFO Entry #9

```
=== INFO - 2025-09-15T21:37:32.825758+00:00 ===
Insert ID: 68c8871c000c999e1ea9eaa8
Service: netra-backend-staging
JSON Payload:
  message: Detection Method: environment_variables
  context:
    service: netra-service
    name: netra_backend.app.core.environment_context.cloud_environment_detector
  error:

```

### INFO Entry #10

```
=== INFO - 2025-09-15T21:37:32.825752+00:00 ===
Insert ID: 68c8871c000c9998529b0d75
Service: netra-backend-staging
JSON Payload:
  message: Service Name: netra-backend-staging
  context:
    service: netra-service
    name: netra_backend.app.core.environment_context.cloud_environment_detector
  error:

```

### INFO Entry #11

```
=== INFO - 2025-09-15T21:37:32.825746+00:00 ===
Insert ID: 68c8871c000c99927b6522e2
Service: netra-backend-staging
JSON Payload:
  message: Confidence Score: 0.90
  context:
    name: netra_backend.app.core.environment_context.cloud_environment_detector
    service: netra-service
  error:

```

### INFO Entry #12

```
=== INFO - 2025-09-15T21:37:32.825738+00:00 ===
Insert ID: 68c8871c000c998a92f38adc
Service: netra-backend-staging
JSON Payload:
  message: Cloud Platform: cloud_run
  context:
    name: netra_backend.app.core.environment_context.cloud_environment_detector
    service: netra-service
  error:

```

### INFO Entry #13

```
=== INFO - 2025-09-15T21:37:32.825731+00:00 ===
Insert ID: 68c8871c000c998355db3fc5
Service: netra-backend-staging
JSON Payload:
  message: Environment Type: staging
  context:
    service: netra-service
    name: netra_backend.app.core.environment_context.cloud_environment_detector
  error:

```

### INFO Entry #14

```
=== INFO - 2025-09-15T21:37:32.825720+00:00 ===
Insert ID: 68c8871c000c9978b953ee16
Service: netra-backend-staging
JSON Payload:
  message: ============================================================
  context:
    service: netra-service
    name: netra_backend.app.core.environment_context.cloud_environment_detector
  error:

```

### INFO Entry #15

```
=== INFO - 2025-09-15T21:37:32.823562+00:00 ===
Insert ID: 68c8871c000c910a8f1b2a73
Service: netra-backend-staging
JSON Payload:
  message: ENVIRONMENT DETECTION SUCCESS
  context:
    name: netra_backend.app.core.environment_context.cloud_environment_detector
    service: netra-service
  error:

```

### INFO Entry #16

```
=== INFO - 2025-09-15T21:37:32.823136+00:00 ===
Insert ID: 68c8871c000c8f602f76af8c
Service: netra-backend-staging
JSON Payload:
  message: ============================================================
  context:
    name: netra_backend.app.core.environment_context.cloud_environment_detector
    service: netra-service
  error:

```

### INFO Entry #17

```
=== INFO - 2025-09-15T21:37:32.813739+00:00 ===
Insert ID: 68c8871c000c6aab013ed9b5
Service: netra-backend-staging
JSON Payload:
  message: Starting comprehensive environment detection
  context:
    service: netra-service
    name: netra_backend.app.core.environment_context.cloud_environment_detector
  error:

```

### INFO Entry #18

```
=== INFO - 2025-09-15T21:37:32.813252+00:00 ===
Insert ID: 68c8871c000c68c4d7ab0a06
Service: netra-backend-staging
JSON Payload:
  message: Initializing EnvironmentContextService with environment detection
  context:
    name: netra_backend.app.core.environment_context.environment_context_service
    service: netra-service
  error:

```

### INFO Entry #19

```
=== INFO - 2025-09-15T21:37:32.391370+00:00 ===
Insert ID: 68c8871c0005f8ca4b8b46aa
Service: netra-backend-staging
JSON Payload:
  message:   [U+2713] Step 2: Environment validated
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #20

```
=== INFO - 2025-09-15T21:37:32.391073+00:00 ===
Insert ID: 68c8871c0005f7a117092cf4
Service: netra-backend-staging
JSON Payload:
  message: Validating environment configuration for: staging
  context:
    name: netra_backend.app.core.environment_validator
    service: netra-service
  error:

```

### INFO Entry #21

```
=== INFO - 2025-09-15T21:37:32.385778+00:00 ===
Insert ID: 68c8871c0005e2f2573d5848
Service: netra-backend-staging
JSON Payload:
  message:   PORT: 8000
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### INFO Entry #22

```
=== INFO - 2025-09-15T21:37:32.385760+00:00 ===
Insert ID: 68c8871c0005e2e03518f5d0
Service: netra-backend-staging
JSON Payload:
  message:   POSTGRES_HOST: /cloudsql/netra-staging:us-central1:staging-shared-postgres
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #23

```
=== INFO - 2025-09-15T21:37:32.385755+00:00 ===
Insert ID: 68c8871c0005e2db989a6526
Service: netra-backend-staging
JSON Payload:
  message:   SECRET_KEY: SET
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #24

```
=== INFO - 2025-09-15T21:37:32.385745+00:00 ===
Insert ID: 68c8871c0005e2d1d23658d7
Service: netra-backend-staging
JSON Payload:
  message:   JWT_SECRET_KEY: SET
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #25

```
=== INFO - 2025-09-15T21:37:32.384383+00:00 ===
Insert ID: 68c8871c0005dd7f8f036f7b
Service: netra-backend-staging
JSON Payload:
  message:   BYPASS_STARTUP_VALIDATION: true
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### INFO Entry #26

```
=== INFO - 2025-09-15T21:37:32.382997+00:00 ===
Insert ID: 68c8871c0005d81559823897
Service: netra-backend-staging
JSON Payload:
  message:   ENVIRONMENT: staging
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### INFO Entry #27

```
=== INFO - 2025-09-15T21:37:32.382873+00:00 ===
Insert ID: 68c8871c0005d799bb1982b2
Service: netra-backend-staging
JSON Payload:
  message: Environment validation - Critical variables status:
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### INFO Entry #28

```
=== INFO - 2025-09-15T21:37:32.382571+00:00 ===
Insert ID: 68c8871c0005d66b664673a8
Service: netra-backend-staging
JSON Payload:
  message:   [U+2713] Step 1: Logging initialized
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #29

```
=== INFO - 2025-09-15T21:37:32.382337+00:00 ===
Insert ID: 68c8871c0005d5816fe0e244
Service: netra-backend-staging
JSON Payload:
  message: PHASE 1: INIT - Foundation
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #30

```
=== INFO - 2025-09-15T21:37:32.382328+00:00 ===
Insert ID: 68c8871c0005d578fa2284f8
Service: netra-backend-staging
JSON Payload:
  message:    Started at: 1757972252.376s elapsed
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #31

```
=== INFO - 2025-09-15T21:37:32.381785+00:00 ===
Insert ID: 68c8871c0005d3591def5b59
Service: netra-backend-staging
JSON Payload:
  message:  CYCLE:  PHASE TRANSITION  ->  INIT
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### INFO Entry #32

```
=== INFO - 2025-09-15T21:37:32.381693+00:00 ===
Insert ID: 68c8871c0005d2fdedc54f81
Service: netra-backend-staging
JSON Payload:
  message: ============================================================
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #33

```
=== INFO - 2025-09-15T21:37:32.381321+00:00 ===
Insert ID: 68c8871c0005d18988f88c7f
Service: netra-backend-staging
JSON Payload:
  message: DETERMINISTIC STARTUP SEQUENCE INITIATED
  context:
    name: netra_backend.app.smd
    service: netra-service
  error:

```

### INFO Entry #34

```
=== INFO - 2025-09-15T21:37:32.381018+00:00 ===
Insert ID: 68c8871c0005d05a1c328922
Service: netra-backend-staging
JSON Payload:
  message: ============================================================
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #35

```
=== INFO - 2025-09-15T21:37:32.380543+00:00 ===
Insert ID: 68c8871c0005ce7f296db4dd
Service: netra-backend-staging
JSON Payload:
  message: Thread cleanup manager initialized for production environment
  context:
    service: netra-service
    name: netra_backend.app.smd
  error:

```

### INFO Entry #36

```
=== INFO - 2025-09-15T21:37:32.380372+00:00 ===
Insert ID: 68c8871c0005cdd46c3fba0d
Service: netra-backend-staging
JSON Payload:
  message: ThreadCleanupManager initialized for Issue #601 memory leak prevention
  error:

```

### INFO Entry #37

```
=== INFO - 2025-09-15T21:37:32.380151+00:00 ===
Insert ID: 68c8871c0005ccf73f141522
Service: netra-backend-staging
JSON Payload:
  message: Thread cleanup hooks installed for Issue #601 memory leak prevention
  error:

```

### INFO Entry #38

```
=== INFO - 2025-09-15T21:37:32.380022+00:00 ===
Insert ID: 68c8871c0005cc76fd4c579f
Service: netra-backend-staging
JSON Payload:
  message: Enhanced GCP WebSocket Readiness Middleware initialized (Issue #449) - Environment: staging, GCP: True, Cloud Run: True, Timeout: 90.0s, uvicorn-compatible: True
  context:
    service: netra-service
    name: netra_backend.app.middleware.gcp_websocket_readiness_middleware
  error:

```

### INFO Entry #39

```
=== INFO - 2025-09-15T21:37:32.379290+00:00 ===
Insert ID: 68c8871c0005c99af8073421
Service: netra-backend-staging
JSON Payload:
  message: FastAPIAuthMiddleware initialized with 27 excluded paths
  context:
    service: netra-service
    name: netra_backend.app.middleware.fastapi_auth_middleware
  error:

```

### INFO Entry #40

```
=== INFO - 2025-09-15T21:37:32.378006+00:00 ===
Insert ID: 68c8871c0005c496f4c4d4c6
Service: netra-backend-staging
JSON Payload:
  message: JWT=REDACTED 91 characters
  context:
    service: netra-service
    name: netra_backend.app.middleware.fastapi_auth_middleware
  error:

```

### INFO Entry #41

```
=== INFO - 2025-09-15T21:37:32.377840+00:00 ===
Insert ID: 68c8871c0005c3f03de00002
Service: netra-backend-staging
JSON Payload:
  message: STAGING JWT=REDACTED JWT_SECRET_STAGING (length: 91)
  error:

```

### INFO Entry #42

```
=== INFO - 2025-09-15T21:37:32.369884+00:00 ===
Insert ID: 68c8871c0005a4dceeeaa396
Service: netra-backend-staging
JSON Payload:
  message: UnifiedSecretsManager initialized
  error:

```

### INFO Entry #43

```
=== INFO - 2025-09-15T21:37:32.365840+00:00 ===
Insert ID: 68c8871c000595109a92f7f3
Service: netra-backend-staging
JSON Payload:
  message: Waiting for application startup.
  error:

```

### INFO Entry #44

```
=== INFO - 2025-09-15T21:37:32.365803+00:00 ===
Insert ID: 68c8871c000594eb6bf94b3f
Service: netra-backend-staging
JSON Payload:
  message: Started server process [13]
  error:

```

### INFO Entry #45

```
=== INFO - 2025-09-15T21:37:32.303126+00:00 ===
Insert ID: 68c8871c0004a016cd2726bc
Service: netra-backend-staging
JSON Payload:
  message: Complete GCP error reporting integration installed
  context:
    name: netra_backend.app.core.app_factory
  error:

```

### INFO Entry #46

```
=== INFO - 2025-09-15T21:37:32.302799+00:00 ===
Insert ID: 68c8871c00049ecf1b7fa016
Service: netra-backend-staging
JSON Payload:
  message: GCP Error Reporting middleware installed
  error:

```

### INFO Entry #47

```
=== INFO - 2025-09-15T21:37:31.463902+00:00 ===
Insert ID: 68c8871b0007141e3ffee8c6
Service: netra-backend-staging
JSON Payload:
  message: TracingManager initialized
  error:

```

### INFO Entry #48

```
=== INFO - 2025-09-15T21:37:31.463891+00:00 ===
Insert ID: 68c8871b000714138f354391
Service: netra-backend-staging
JSON Payload:
  message: Tracer initialized: default
  error:

```

### INFO Entry #49

```
=== INFO - 2025-09-15T21:37:31.370050+00:00 ===
Insert ID: 68c8871b0005a582fa4b2951
Service: netra-backend-staging
JSON Payload:
  message: Current asyncio policy: EventLoopPolicy
  context:
    service: netra-service
    name: netra_backend.app.core.windows_asyncio_safe
  error:

```

### INFO Entry #50

```
=== INFO - 2025-09-15T21:37:31.369785+00:00 ===
Insert ID: 68c8871b0005a4797c31ebf5
Service: netra-backend-staging
JSON Payload:
  message: [U+1F329][U+FE0F] Setting up cloud environment asyncio optimizations for Issue #128
  context:
    service: netra-service
    name: netra_backend.app.core.windows_asyncio_safe
  error:

```
