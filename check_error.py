import json

with open('test_reports/test_report_20250824_111556.json', 'r') as f:
    report = json.load(f)

backend_output = report['categories']['unit']['service_results']['backend']['output']
error_start = backend_output.find('ERROR collecting')
if error_start != -1:
    print(backend_output[error_start:error_start+1500])
else:
    print("No error found")
    print(backend_output[:1000])