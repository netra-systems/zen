import json

with open('test_reports/test_report_20250824_111916.json', 'r') as f:
    report = json.load(f)

backend_output = report['categories']['unit']['service_results']['backend']['output']
error_start = backend_output.find('ERROR collecting')
if error_start != -1:
    print(backend_output[error_start:error_start+1500])
else:
    print("No error found in backend")
    
# Also check auth
auth_output = report['categories']['unit']['service_results']['auth']['output']
auth_error_start = auth_output.find('ERROR collecting')
if auth_error_start != -1:
    print("\nAuth error:")
    print(auth_output[auth_error_start:auth_error_start+1500])
else:
    print("\nNo error found in auth")
    print("Auth output length:", len(auth_output))
    if len(auth_output) > 0:
        print("Auth output snippet:", auth_output[:500])