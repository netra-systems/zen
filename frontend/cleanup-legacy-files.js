#!/usr/bin/env node

/**
 * Script to clean up legacy, temporary, and redundant files
 * Run with: node cleanup-legacy-files.js
 * Use --dry-run flag to see what would be deleted without actually deleting
 */

const fs = require('fs');
const path = require('path');

const isDryRun = process.argv.includes('--dry-run');

console.log(`🧹 Frontend Legacy Files Cleanup${isDryRun ? ' (DRY RUN)' : ''}\n`);

// Files to be removed
const filesToRemove = [
  // Test debugging and fix scripts
  'fix-store-tests.py',
  'debug-test.js',
  'fix-hanging-tests.js',
  'fix-setup-antihang.js',
  'jest_auth_store_fix.js',
  'test-debug.js',
  'test-hang-fixes.js',
  
  // Test output and log files
  'test-output.log',
  'test-run-final.log',
  'frontend_output.log',
  'test-output.txt',
  
  // Backup files
  'hooks/useMCPTools.ts.backup',
  
  // Debug test files
  '__tests__/auth/debug-detailed-token-refresh.test.tsx',
  '__tests__/auth/debug-token-refresh.test.tsx',
  '__tests__/auth/debug-exception-token-refresh.test.tsx',
  '__tests__/components/chat/MessageInput/threadservice-fix-test.tsx',
  
  // Debug components
  'components/chat/overflow-panel/debug-export.ts',
  'components/chat/test-response-card.tsx',
  
  // Test utility scripts (keeping only essential ones)
  'run-jest.js',
  'run-test.js',
  'test-frontend-health.js',
  'test-improvement-summary.js',
  'test-navigation.js',
  'test-optimizer.js',
  'test-shard-runner.js',
  'test-suite-runner.js',
  'validate-critical-tests.js',
  
  // Redundant Jest configs (keeping main, optimized, and real)
  'jest.config.fast.cjs',
  'jest.config.integration.cjs',
  'jest.config.performance.cjs',
  'jest.config.simple.cjs',
  'jest.config.stable.cjs',
  'jest.config.unified.cjs',
  
  // Markdown test documentation
  'test-synthetic-data-cypress.md',
];

// Additional patterns to clean
const patternsToClean = [
  '**/*.log',
  '**/*.bak',
  '**/*.backup',
  '**/node_modules/**/*.bak',
];

let removedCount = 0;
let skippedCount = 0;
let errorCount = 0;

// Remove specific files
filesToRemove.forEach(file => {
  const fullPath = path.join(__dirname, file);
  
  try {
    if (fs.existsSync(fullPath)) {
      if (isDryRun) {
        console.log(`📄 Would remove: ${file}`);
      } else {
        fs.unlinkSync(fullPath);
        console.log(`✅ Removed: ${file}`);
      }
      removedCount++;
    } else {
      skippedCount++;
    }
  } catch (error) {
    console.error(`❌ Error removing ${file}: ${error.message}`);
    errorCount++;
  }
});

// Clean pattern-based files
const glob = require('glob');

patternsToClean.forEach(pattern => {
  const files = glob.sync(pattern, {
    cwd: __dirname,
    absolute: false,
    ignore: ['**/node_modules/**', '**/coverage/**', '**/dist/**', '**/.next/**']
  });
  
  files.forEach(file => {
    const fullPath = path.join(__dirname, file);
    
    try {
      if (fs.existsSync(fullPath)) {
        if (isDryRun) {
          console.log(`📄 Would remove (pattern): ${file}`);
        } else {
          fs.unlinkSync(fullPath);
          console.log(`✅ Removed (pattern): ${file}`);
        }
        removedCount++;
      }
    } catch (error) {
      console.error(`❌ Error removing ${file}: ${error.message}`);
      errorCount++;
    }
  });
});

// Summary
console.log('\n' + '='.repeat(50));
console.log('📊 Cleanup Summary:');
console.log(`   Files removed: ${removedCount}`);
console.log(`   Files skipped (not found): ${skippedCount}`);
console.log(`   Errors: ${errorCount}`);

if (isDryRun) {
  console.log('\n⚠️  This was a dry run. No files were actually deleted.');
  console.log('   Run without --dry-run flag to perform actual cleanup.');
} else {
  console.log('\n✨ Cleanup complete!');
  console.log('\n📝 Remaining Jest configs:');
  console.log('   - jest.config.cjs (main)');
  console.log('   - jest.config.optimized.cjs');
  console.log('   - jest.config.real.cjs');
  console.log('   - jest.setup.js');
  console.log('   - jest.setup.real.js');
  console.log('\n💡 These configs serve different testing scenarios and should be kept.');
}

// Check if glob is installed
try {
  require.resolve('glob');
} catch(e) {
  console.log('\n⚠️  Note: Install glob package for pattern-based cleanup:');
  console.log('   npm install --save-dev glob');
}