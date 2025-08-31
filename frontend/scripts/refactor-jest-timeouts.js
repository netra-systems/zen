#!/usr/bin/env node

/**
 * Script to refactor Jest timeout calls to use centralized configuration
 * This removes duplicate jest.setTimeout() calls and replaces them with
 * imports from the centralized test-timeouts.ts configuration
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Find all test files
const testFiles = glob.sync('**/*.test.{ts,tsx,js,jsx}', {
  cwd: path.join(__dirname, '..', '__tests__'),
  absolute: true,
  ignore: ['**/node_modules/**', '**/coverage/**', '**/dist/**']
});

console.log(`Found ${testFiles.length} test files to process`);

let filesModified = 0;
let timeoutsRemoved = 0;

testFiles.forEach(filePath => {
  let content = fs.readFileSync(filePath, 'utf8');
  const originalContent = content;
  
  // Track if we need to add imports
  let needsTimeoutImport = false;
  let hasAntiHangImport = content.includes('anti-hanging-test-utilities');
  
  // Remove duplicate jest.setTimeout calls in the same function/describe block
  // Pattern 1: Multiple jest.setTimeout in same describe block
  content = content.replace(/(\bdescribe\([^}]+\{[^}]*jest\.setTimeout\(\d+\)[^}]*)jest\.setTimeout\(\d+\);?/g, '$1');
  
  // Pattern 2: jest.setTimeout after setupAntiHang
  content = content.replace(/setupAntiHang\(\);?\s*jest\.setTimeout\(\d+\);?/g, 'setupAntiHang();');
  content = content.replace(/setupAntiHang\([^)]*\);?\s*jest\.setTimeout\(\d+\);?/g, (match) => {
    const antiHangMatch = match.match(/setupAntiHang\([^)]*\)/);
    return antiHangMatch ? antiHangMatch[0] + ';' : match;
  });
  
  // Pattern 3: Remove standalone jest.setTimeout calls and track if we need the import
  const timeoutMatches = content.match(/jest\.setTimeout\((\d+)\)/g);
  if (timeoutMatches) {
    // Find unique timeout values
    const timeoutValues = [...new Set(timeoutMatches.map(m => {
      const match = m.match(/jest\.setTimeout\((\d+)\)/);
      return match ? parseInt(match[1]) : 10000;
    }))];
    
    // Determine which timeout constant to use
    let timeoutConstant = 'TEST_TIMEOUTS.DEFAULT';
    if (timeoutValues.length === 1) {
      const value = timeoutValues[0];
      if (value === 5000) timeoutConstant = 'TEST_TIMEOUTS.UNIT';
      else if (value === 15000) timeoutConstant = 'TEST_TIMEOUTS.INTEGRATION';
      else if (value === 30000) timeoutConstant = 'TEST_TIMEOUTS.E2E';
      else if (value === 60000) timeoutConstant = 'TEST_TIMEOUTS.PERFORMANCE';
      else if (value === 10000) {
        // Check if it's a WebSocket test
        if (filePath.includes('websocket') || filePath.includes('WebSocket')) {
          timeoutConstant = 'TEST_TIMEOUTS.WEBSOCKET';
        } else {
          timeoutConstant = 'TEST_TIMEOUTS.DEFAULT';
        }
      }
    }
    
    // If file uses setupAntiHang, update the call to include timeout
    if (hasAntiHangImport) {
      // Update setupAntiHang() calls to include the timeout
      content = content.replace(/setupAntiHang\(\)/g, `setupAntiHang(${timeoutConstant})`);
      // Remove remaining jest.setTimeout calls
      content = content.replace(/\s*jest\.setTimeout\(\d+\);?/g, '');
      needsTimeoutImport = true;
    } else {
      // Replace first jest.setTimeout with setTestTimeout
      let replaced = false;
      content = content.replace(/jest\.setTimeout\(\d+\);?/, (match) => {
        if (!replaced) {
          replaced = true;
          needsTimeoutImport = true;
          return `setTestTimeout(${timeoutConstant});`;
        }
        return '';
      });
      // Remove remaining jest.setTimeout calls
      content = content.replace(/\s*jest\.setTimeout\(\d+\);?/g, '');
    }
  }
  
  // Add import if needed
  if (needsTimeoutImport && !content.includes('@/__tests__/config/test-timeouts')) {
    // Find the right place to add the import
    const importRegex = /^import .* from ['"].*['"];?$/m;
    const lastImportMatch = content.match(importRegex);
    
    if (lastImportMatch) {
      // Add after the last import
      const importStatement = hasAntiHangImport
        ? `import { TEST_TIMEOUTS } from '@/__tests__/config/test-timeouts';`
        : `import { TEST_TIMEOUTS, setTestTimeout } from '@/__tests__/config/test-timeouts';`;
      
      // Find position of last import
      let insertPos = content.lastIndexOf(lastImportMatch[0]) + lastImportMatch[0].length;
      content = content.slice(0, insertPos) + '\n' + importStatement + content.slice(insertPos);
    } else {
      // Add at the beginning of the file
      const importStatement = hasAntiHangImport
        ? `import { TEST_TIMEOUTS } from '@/__tests__/config/test-timeouts';\n\n`
        : `import { TEST_TIMEOUTS, setTestTimeout } from '@/__tests__/config/test-timeouts';\n\n`;
      content = importStatement + content;
    }
  }
  
  // Clean up multiple blank lines
  content = content.replace(/\n\n\n+/g, '\n\n');
  
  // Only write if content changed
  if (content !== originalContent) {
    fs.writeFileSync(filePath, content, 'utf8');
    filesModified++;
    
    // Count removed timeouts
    const originalTimeouts = (originalContent.match(/jest\.setTimeout/g) || []).length;
    const newTimeouts = (content.match(/jest\.setTimeout/g) || []).length;
    timeoutsRemoved += originalTimeouts - newTimeouts;
    
    console.log(`✓ Modified: ${path.relative(process.cwd(), filePath)}`);
  }
});

console.log(`\n✅ Refactoring complete!`);
console.log(`   Files modified: ${filesModified}`);
console.log(`   Timeout calls removed: ${timeoutsRemoved}`);
console.log(`\n💡 Remember to run your tests to ensure everything still works!`);