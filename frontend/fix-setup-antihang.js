#!/usr/bin/env node

/**
 * Bulk clean up incorrectly formatted setupAntiHang pattern fixes
 * This script cleans up the formatting issues from the previous bulk fix
 */

const fs = require('fs');
const path = require('path');

// Files to clean up
const filesToFix = [
  "__tests__/auth/auth-login.test.ts",
  "__tests__/auth/auth-logout.test.ts", 
  "__tests__/auth/auth-security.test.ts",
  "__tests__/auth/auth-token.test.ts",
  "__tests__/components/ui/IconButton.test.tsx",
  "__tests__/components/AuthGuard.test.tsx",
  "__tests__/components/InitializationProgress.test.tsx",
  "__tests__/hooks/useChatWebSocket.test.ts",
  "__tests__/hooks/useError.test.ts"
];

function cleanupSetupAntiHangPattern(filePath) {
  try {
    const fullPath = path.join(process.cwd(), filePath);
    
    if (!fs.existsSync(fullPath)) {
      console.log(`❌ File not found: ${filePath}`);
      return false;
    }

    let content = fs.readFileSync(fullPath, 'utf8');
    const originalContent = content;
    
    // Fix empty beforeEach/afterEach blocks
    content = content.replace(
      /beforeEach\(\(\) => \{\s*\n\s*\}\);\s*\n\s*afterEach\(\(\) => \{\s*cleanupAntiHang\(\);\s*\}\);jest\.setTimeout\(\d+\);/g,
      'beforeEach(() => {\n    setupAntiHang();\n  });\n\n  afterEach(() => {\n    cleanupAntiHang();\n  });'
    );
    
    // Remove duplicate jest.setTimeout
    content = content.replace(
      /jest\.setTimeout\(\d+\);\s*\n\s*beforeEach/g,
      'beforeEach'
    );
    
    // Clean up empty beforeEach blocks
    content = content.replace(
      /beforeEach\(\(\) => \{\s*\n\s*\}\);\s*\n/g,
      ''
    );

    if (content !== originalContent) {
      fs.writeFileSync(fullPath, content, 'utf8');
      console.log(`✅ Cleaned up ${filePath}`);
      return true;
    } else {
      console.log(`ℹ️  No cleanup needed in ${filePath}`);
      return false;
    }
    
  } catch (error) {
    console.error(`❌ Error processing ${filePath}:`, error.message);
    return false;
  }
}

console.log('🔧 Cleaning up setupAntiHang patterns in test files...\n');

let fixedCount = 0;
for (const file of filesToFix) {
  if (cleanupSetupAntiHangPattern(file)) {
    fixedCount++;
  }
}

console.log(`\n✨ Cleaned up ${fixedCount}/${filesToFix.length} files`);