#!/usr/bin/env pwsh
# PowerShell script to run Jest using npx
$NodePath = "C:\Program Files\nodejs"
$env:PATH = "$NodePath;$env:PATH"

& npx jest $args