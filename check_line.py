with open('deploy-staging-automated.ps1', 'rb') as f:
    lines = f.readlines()
    line387 = lines[386]  # 0-indexed
    print(f"Line 387 bytes: {line387}")
    print(f"Line 387 hex: {line387.hex()}")
    
    # Check for various quote types
    if b'\xe2\x80\x9c' in line387:
        print("Found LEFT DOUBLE QUOTATION MARK")
    if b'\xe2\x80\x9d' in line387:
        print("Found RIGHT DOUBLE QUOTATION MARK")
    if b'\xe2\x80\x98' in line387:
        print("Found LEFT SINGLE QUOTATION MARK")
    if b'\xe2\x80\x99' in line387:
        print("Found RIGHT SINGLE QUOTATION MARK")