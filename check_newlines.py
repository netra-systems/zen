with open('deploy-staging-automated.ps1', 'rb') as f:
    content = f.read()
    
# Check line endings
crlf_count = content.count(b'\r\n')
lf_count = content.count(b'\n') - crlf_count  # Subtract CRLF occurrences
cr_count = content.count(b'\r') - crlf_count  # Subtract CRLF occurrences

print(f"CRLF endings: {crlf_count}")
print(f"LF only endings: {lf_count}")
print(f"CR only endings: {cr_count}")

# Check around line 387
lines = content.split(b'\n')
if len(lines) > 386:
    print(f"\nLine 386 ending: {repr(lines[385][-20:])}")
    print(f"Line 387: {repr(lines[386])}")
    if len(lines) > 387:
        print(f"Line 388: {repr(lines[387])}")