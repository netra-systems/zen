#!/usr/bin/env python3
import json

with open('gcp_logs_raw_20250915_174624.json', 'r') as f:
    data = json.load(f)

print('=== ERROR ENTRIES SAMPLE ===')
for i, error in enumerate(data.get('ERROR', [])[:10]):
    print(f'Entry {i+1}:')
    print(f'  Timestamp: {error.get("timestamp")}')
    print(f'  Text Payload: {error.get("text_payload")}')
    print(f'  JSON Payload: {error.get("json_payload")}')
    if error.get("http_request") and any(error.get("http_request").values()):
        print(f'  HTTP Request: {error.get("http_request")}')
    print('---')

print(f'\n=== WARNING ENTRIES SAMPLE ===')
for i, warning in enumerate(data.get('WARNING', [])[:5]):
    print(f'Entry {i+1}:')
    print(f'  Timestamp: {warning.get("timestamp")}')
    print(f'  Text Payload: {warning.get("text_payload")}')
    print(f'  JSON Payload: {warning.get("json_payload")}')
    print('---')

print(f'\n=== SUMMARY ===')
print(f'Total ERROR entries: {len(data.get("ERROR", []))}')
print(f'Total WARNING entries: {len(data.get("WARNING", []))}')
print(f'Total INFO entries: {len(data.get("INFO", []))}')
print(f'Total NOTICE entries: {len(data.get("NOTICE", []))}')

# Check for non-empty payloads
error_with_content = [e for e in data.get('ERROR', []) if e.get('text_payload') or e.get('json_payload')]
warning_with_content = [w for w in data.get('WARNING', []) if w.get('text_payload') or w.get('json_payload')]

print(f'\nERROR entries with content: {len(error_with_content)}')
print(f'WARNING entries with content: {len(warning_with_content)}')

if error_with_content:
    print('\nFirst ERROR with content:')
    error = error_with_content[0]
    print(f'  Timestamp: {error.get("timestamp")}')
    print(f'  Text: {error.get("text_payload")}')
    print(f'  JSON: {error.get("json_payload")}')

if warning_with_content:
    print('\nFirst WARNING with content:')
    warning = warning_with_content[0]
    print(f'  Timestamp: {warning.get("timestamp")}')
    print(f'  Text: {warning.get("text_payload")}')
    print(f'  JSON: {warning.get("json_payload")}')