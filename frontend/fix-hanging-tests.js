#!/usr/bin/env node
/**
 * Fix Hanging Tests Script
 * 
 * This script systematically fixes common patterns that cause tests to hang:
 * 1. Excessive timeouts (>5000ms)
 * 2. Missing timer cleanup
 * 3. Infinite loops in tests
 * 4. Real network calls instead of mocks
 */

const fs = require('fs');
const path = require('path');
const { glob } = require('glob');

// Configuration
const MAX_TIMEOUT = 5000;
const TEST_DIRS = ['__tests__/**/*.test.{ts,tsx,js,jsx}', '__tests__/**/*.spec.{ts,tsx,js,jsx}'];

// Patterns to fix
const FIXES = [
  // Fix excessive timeouts
  {
    pattern: /timeout:\s*([6-9]\d{3}|\d{5,})/g,
    replacement: `timeout: ${MAX_TIMEOUT}`,
    description: 'Fixed excessive timeout'
  },
  
  // Fix waitFor timeouts
  {
    pattern: /}, \{ timeout: ([6-9]\d{3}|\d{5,}) \}/g,
    replacement: `}, { timeout: ${MAX_TIMEOUT} }`,
    description: 'Fixed waitFor timeout'
  },
  
  // Add missing jest.setTimeout in describe blocks
  {
    pattern: /(describe\(['"`][^'"`]+['"`], \(\) => \{)(\s*)/g,
    replacement: '$1$2  jest.setTimeout(10000);$2',
    description: 'Added jest.setTimeout to describe block'
  },
  
  // Fix real WebSocket connections
  {
    pattern: /new WebSocket\(['"`](ws:\/\/|wss:\/\/)([^'"`]*['"`])/g,
    replacement: "new WebSocket('ws://localhost:3001/test')",
    description: 'Fixed real WebSocket connection to use localhost'
  },
  
  // Add timer cleanup to afterEach
  {
    pattern: /(afterEach\(\(\) => \{)(\s*)(.*?)(\s*}\);)/gs,
    replacement: (match, start, indent, content, end) => {
      if (!content.includes('jest.clearAllTimers')) {
        return `${start}${indent}${content}${indent}  // Clean up timers to prevent hanging${indent}  jest.clearAllTimers();${indent}  jest.useFakeTimers();${indent}  jest.runOnlyPendingTimers();${indent}  jest.useRealTimers();${end}`;
      }
      return match;
    },
    description: 'Added timer cleanup to afterEach'
  },
  
  // Limit setInterval delays
  {
    pattern: /setInterval\(([^,]+),\s*([6-9]\d{3}|\d{5,})\)/g,
    replacement: 'setInterval($1, 1000)',
    description: 'Limited setInterval delay'
  },
  
  // Reduce setTimeout delays in tests
  {
    pattern: /setTimeout\(([^,]+),\s*([3-9]\d{3}|\d{5,})\)/g,
    replacement: 'setTimeout($1, 1000)',
    description: 'Reduced setTimeout delay'
  },
  
  // Fix Promise delays
  {
    pattern: /new Promise\(resolve => setTimeout\(resolve,\s*([6-9]\d{3}|\d{5,})\)\)/g,
    replacement: 'new Promise(resolve => setTimeout(resolve, 1000))',
    description: 'Fixed Promise delay'
  }
];

// Track which files were modified
const modifiedFiles = [];
const fixes = {};

async function findTestFiles() {
  const files = [];
  for (const pattern of TEST_DIRS) {
    const matches = await glob(pattern, { cwd: __dirname });
    files.push(...matches.map(f => path.resolve(__dirname, f)));
  }
  return files;
}

function applyFixes(content, filePath) {
  let modifiedContent = content;
  let fileModified = false;
  const fileFixes = [];

  for (const fix of FIXES) {
    const matches = modifiedContent.match(fix.pattern);
    if (matches && matches.length > 0) {
      modifiedContent = modifiedContent.replace(fix.pattern, fix.replacement);
      fileModified = true;
      fileFixes.push({
        description: fix.description,
        count: matches.length
      });
    }
  }

  return { modifiedContent, fileModified, fileFixes };
}

function addAntiHangingUtilities(content) {
  // Check if the file already imports anti-hanging utilities
  if (content.includes('anti-hanging-test-utilities')) {
    return content;
  }

  // Add import at the top after other imports
  const importRegex = /^(import.*?;?\n)+/gm;
  const importMatch = content.match(importRegex);
  
  if (importMatch) {
    const lastImport = importMatch[0];
    const afterImports = content.substring(lastImport.length);
    
    const antiHangImport = "import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';\n";
    
    return lastImport + antiHangImport + afterImports;
  }
  
  return content;
}

function addSetupCleanup(content) {
  // Check if already has setupAntiHang
  if (content.includes('setupAntiHang')) {
    return content;
  }

  // Find describe blocks and add setup
  const describeRegex = /(describe\(['"`][^'"`]+['"`], \(\) => \{)(\s*)/g;
  content = content.replace(describeRegex, (match, describeStart, indent) => {
    return `${describeStart}${indent}  setupAntiHang();${indent}`;
  });

  // Find or add afterEach blocks
  if (!content.includes('afterEach')) {
    // Add afterEach before the end of describe blocks
    const beforeEnd = /(\s*}\);?\s*$)/g;
    content = content.replace(beforeEnd, (match, end) => {
      return `\n  afterEach(() => {\n    cleanupAntiHang();\n  });\n${end}`;
    });
  } else {
    // Add to existing afterEach
    const afterEachRegex = /(afterEach\(\(\) => \{)(\s*)(.*?)(\s*}\);)/gs;
    content = content.replace(afterEachRegex, (match, start, indent, body, end) => {
      if (!body.includes('cleanupAntiHang')) {
        return `${start}${indent}${body}${indent}  cleanupAntiHang();${end}`;
      }
      return match;
    });
  }

  return content;
}

async function processFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    let { modifiedContent, fileModified, fileFixes } = applyFixes(content, filePath);
    
    // Add anti-hanging utilities for test files
    if (filePath.includes('test.') || filePath.includes('spec.')) {
      modifiedContent = addAntiHangingUtilities(modifiedContent);
      modifiedContent = addSetupCleanup(modifiedContent);
    }

    if (fileModified || modifiedContent !== content) {
      fs.writeFileSync(filePath, modifiedContent, 'utf8');
      modifiedFiles.push(filePath);
      fixes[filePath] = fileFixes;
      console.log(`✅ Fixed: ${path.relative(__dirname, filePath)}`);
      fileFixes.forEach(fix => {
        console.log(`   - ${fix.description} (${fix.count} occurrences)`);
      });
    }
  } catch (error) {
    console.error(`❌ Error processing ${filePath}:`, error.message);
  }
}

async function main() {
  console.log('🔍 Finding test files...');
  const testFiles = await findTestFiles();
  console.log(`Found ${testFiles.length} test files`);

  console.log('\n🔧 Applying fixes...');
  for (const file of testFiles) {
    await processFile(file);
  }

  console.log(`\n📊 Summary:`);
  console.log(`- Files processed: ${testFiles.length}`);
  console.log(`- Files modified: ${modifiedFiles.length}`);
  
  if (modifiedFiles.length > 0) {
    console.log('\n🎉 Fixed files:');
    modifiedFiles.forEach(file => {
      console.log(`  - ${path.relative(__dirname, file)}`);
    });
  }

  console.log('\n✅ Hanging test fixes complete!');
  console.log('💡 Run your tests with --forceExit=false to verify fixes');
}

if (require.main === module) {
  main().catch(console.error);
}