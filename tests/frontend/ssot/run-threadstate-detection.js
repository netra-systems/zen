/**
 * ThreadState SSOT Violation Detection Runner
 *
 * This script runs the SSOT violation detection logic directly in Node.js
 * to validate the test implementation and detect current violations.
 */

const fs = require('fs');
const path = require('path');

// Simple glob replacement using fs.readdirSync recursively
function findTypescriptFiles(dir, files = []) {
  const items = fs.readdirSync(dir, { withFileTypes: true });

  for (const item of items) {
    const fullPath = path.join(dir, item.name);

    // Skip ignored directories
    if (item.isDirectory() && !['node_modules', 'dist', 'build', '.next', '.git'].includes(item.name)) {
      findTypescriptFiles(fullPath, files);
    } else if (item.isFile() && item.name.endsWith('.ts') && !item.name.endsWith('.d.ts')) {
      files.push(path.relative(process.cwd(), fullPath));
    }
  }

  return files;
}

const projectRoot = process.cwd();
const canonicalPath = 'shared/types/frontend_types.ts';

console.log('🔍 ThreadState SSOT Violation Detection Starting...\n');
console.log(`Project root: ${projectRoot}`);
console.log(`Canonical path: ${canonicalPath}\n`);

async function scanForThreadStateDefinitions() {
  const definitions = [];

  // Find all TypeScript files
  const tsFiles = findTypescriptFiles(projectRoot);

  console.log(`📁 Scanning ${tsFiles.length} TypeScript files...\n`);

  for (const file of tsFiles) {
    const fullPath = path.resolve(projectRoot, file);
    if (!fs.existsSync(fullPath)) continue;

    const content = fs.readFileSync(fullPath, 'utf-8');
    const lines = content.split('\n');

    lines.forEach((line, index) => {
      // Match interface ThreadState or type ThreadState
      const interfaceMatch = line.match(/^\s*export\s+interface\s+ThreadState\s*({|\s*extends)/);
      const typeMatch = line.match(/^\s*export\s+type\s+ThreadState\s*=/);

      if (interfaceMatch || typeMatch) {
        const lineNumber = index + 1;
        const definitionType = interfaceMatch ? 'interface' : 'type';

        // Extract definition content (current line + next few lines for context)
        const contextLines = lines.slice(index, Math.min(index + 15, lines.length));
        const definitionContent = contextLines.join('\n');

        // Determine semantic meaning
        const semantic = determineSemanticMeaning(file, definitionContent);

        definitions.push({
          filePath: file,
          lineNumber,
          definitionType,
          content: definitionContent,
          semantic
        });

        console.log(`✅ Found ThreadState definition:`);
        console.log(`   File: ${file}:${lineNumber}`);
        console.log(`   Type: ${definitionType} | Semantic: ${semantic}`);
        console.log(`   Content Preview: ${line.trim()}`);
        console.log('');
      }
    });
  }

  return definitions;
}

function determineSemanticMeaning(filePath, content) {
  // Operation states (union type with string literals)
  if (content.includes("'idle'") || content.includes("'creating'") || content.includes("'switching'")) {
    return 'operation-states';
  }

  // Test utilities
  if (filePath.includes('__tests__') || filePath.includes('test') || filePath.includes('spec')) {
    return 'test-utility';
  }

  // Store actions (contains method signatures)
  if (content.includes('setActiveThread') || content.includes('setThreadLoading')) {
    return 'store-actions';
  }

  // Default: data structure interface
  return 'data-structure';
}

async function findImportViolations() {
  const violations = [];

  const tsFiles = findTypescriptFiles(projectRoot);

  for (const file of tsFiles) {
    const fullPath = path.resolve(projectRoot, file);
    if (!fs.existsSync(fullPath)) continue;

    const content = fs.readFileSync(fullPath, 'utf-8');
    const lines = content.split('\n');

    lines.forEach((line, index) => {
      // Match ThreadState imports
      const importMatch = line.match(/import.*ThreadState.*from\s+['"]([^'"]+)['"]/);
      if (importMatch) {
        const importPath = importMatch[1];

        // Check if import points to canonical source or operation states
        const isCanonicalImport = importPath.includes('shared/types/frontend_types') ||
                                importPath.includes('@/shared/types/frontend_types');
        const isOperationStatesImport = importPath.includes('thread-state-machine');

        if (!isCanonicalImport && !isOperationStatesImport) {
          violations.push({
            filePath: file,
            lineNumber: index + 1,
            importPath,
            importStatement: line.trim()
          });
        }
      }
    });
  }

  return violations;
}

async function runAnalysis() {
  console.log('==========================================');
  console.log('🧪 THREADSTATE SSOT VIOLATION ANALYSIS');
  console.log('==========================================\n');

  // Scan for definitions
  const definitions = await scanForThreadStateDefinitions();

  console.log('📊 SUMMARY OF FINDINGS:\n');
  console.log(`Total ThreadState definitions found: ${definitions.length}`);
  console.log('Expected after consolidation: 2 (canonical + operation states)\n');

  // Group by semantic meaning
  const bySemanticMap = {};
  definitions.forEach(def => {
    if (!bySemanticMap[def.semantic]) bySemanticMap[def.semantic] = [];
    bySemanticMap[def.semantic].push(def);
  });

  console.log('📋 DEFINITIONS BY SEMANTIC TYPE:\n');
  Object.entries(bySemanticMap).forEach(([semantic, defs]) => {
    console.log(`${semantic.toUpperCase()}: ${defs.length} definitions`);
    defs.forEach(def => {
      console.log(`  - ${def.filePath}:${def.lineNumber} (${def.definitionType})`);
    });
    console.log('');
  });

  // Check canonical exists (normalize path separators for Windows compatibility)
  const normalizedCanonicalPath = canonicalPath.replace(/\//g, path.sep);
  const canonicalFound = definitions.find(def => def.filePath.includes(normalizedCanonicalPath));
  console.log(`✅ Canonical definition found: ${canonicalFound ? 'YES' : 'NO'}`);
  console.log(`   Looking for: ${normalizedCanonicalPath}`);
  if (canonicalFound) {
    console.log(`   Location: ${canonicalFound.filePath}:${canonicalFound.lineNumber}`);
  } else {
    console.log('   Available paths:');
    definitions.filter(def => def.semantic === 'data-structure').forEach(def => {
      console.log(`     - ${def.filePath}`);
    });
  }
  console.log('');

  // Check for duplicates
  const dataStructureDefs = definitions.filter(def => def.semantic === 'data-structure');
  console.log(`🔍 Data structure definitions: ${dataStructureDefs.length}`);
  if (dataStructureDefs.length > 1) {
    console.log('   ❌ SSOT VIOLATION: Multiple data structure definitions found');
    console.log('   🎯 CONSOLIDATION REQUIRED:');
    dataStructureDefs.forEach(def => {
      if (def.filePath.includes(normalizedCanonicalPath)) {
        console.log(`      ✅ KEEP: ${def.filePath}:${def.lineNumber} (canonical)`);
      } else {
        console.log(`      ❌ REMOVE: ${def.filePath}:${def.lineNumber} (duplicate)`);
      }
    });
  } else if (dataStructureDefs.length === 1) {
    const singleDef = dataStructureDefs[0];
    if (singleDef.filePath.includes(normalizedCanonicalPath)) {
      console.log('   ✅ SSOT COMPLIANT: Single canonical data structure definition');
    } else {
      console.log('   ⚠️ ISSUE: Single definition but not in canonical location');
      console.log(`      Current: ${singleDef.filePath}:${singleDef.lineNumber}`);
      console.log(`      Expected: ${normalizedCanonicalPath}`);
    }
  } else {
    console.log('   ❌ ERROR: No data structure definitions found');
  }
  console.log('');

  // Check for import violations
  console.log('📥 CHECKING IMPORT VIOLATIONS...\n');
  const importViolations = await findImportViolations();

  if (importViolations.length === 0) {
    console.log('✅ No import violations found');
  } else {
    console.log(`❌ ${importViolations.length} import violations found:`);
    importViolations.forEach(violation => {
      console.log(`   ${violation.filePath}:${violation.lineNumber}`);
      console.log(`   Import: ${violation.importStatement}`);
      console.log(`   Problem: Should import from canonical source`);
      console.log('');
    });
  }

  // Final assessment
  console.log('==========================================');
  console.log('🎯 SSOT CONSOLIDATION ASSESSMENT');
  console.log('==========================================\n');

  const needsConsolidation = dataStructureDefs.length > 1 || importViolations.length > 0;

  if (needsConsolidation) {
    console.log('❌ SSOT CONSOLIDATION REQUIRED');
    console.log(`   - Duplicate definitions: ${dataStructureDefs.length - 1}`);
    console.log(`   - Import violations: ${importViolations.length}`);
    console.log('\n📋 RECOMMENDED ACTIONS:');

    // Remove duplicates
    const duplicates = dataStructureDefs.filter(def => !def.filePath.includes(canonicalPath));
    duplicates.forEach(dup => {
      console.log(`   1. REMOVE duplicate at ${dup.filePath}:${dup.lineNumber}`);
    });

    // Fix imports
    importViolations.forEach(violation => {
      console.log(`   2. FIX import in ${violation.filePath}:${violation.lineNumber} to use canonical source`);
    });

    // Handle special cases
    const storeActions = definitions.filter(def => def.semantic === 'store-actions');
    storeActions.forEach(store => {
      console.log(`   3. REFACTOR ${store.filePath}:${store.lineNumber} to extend canonical interface`);
    });

    const testUtilities = definitions.filter(def => def.semantic === 'test-utility');
    testUtilities.forEach(test => {
      console.log(`   4. UPDATE ${test.filePath}:${test.lineNumber} to import from canonical source`);
    });
  } else {
    console.log('✅ SSOT CONSOLIDATION COMPLETE');
    console.log('   All ThreadState definitions are properly consolidated');
  }

  // Preserve operation states
  const operationStates = definitions.filter(def => def.semantic === 'operation-states');
  if (operationStates.length > 0) {
    console.log('\n🟢 PRESERVED SEMANTIC DIFFERENCES:');
    operationStates.forEach(op => {
      console.log(`   ✅ KEEP ${op.filePath}:${op.lineNumber} (different semantic: operation states)`);
    });
  }

  console.log('\n==========================================');
  console.log('🧪 TEST RESULT SIMULATION');
  console.log('==========================================\n');

  // Simulate test results
  const testResults = {
    'should have minimal ThreadState definitions': definitions.length <= 2 ? 'PASS' : 'FAIL',
    'should have only one data-structure ThreadState': dataStructureDefs.length === 1 && dataStructureDefs[0]?.filePath.includes(normalizedCanonicalPath) ? 'PASS' : 'FAIL',
    'should have consistent imports': importViolations.length === 0 ? 'PASS' : 'FAIL',
    'should preserve operation states': operationStates.length >= 1 ? 'PASS' : 'FAIL',
    'should generate remediation report': !needsConsolidation ? 'PASS' : 'FAIL'
  };

  console.log('📊 SIMULATED TEST RESULTS:');
  Object.entries(testResults).forEach(([test, result]) => {
    const emoji = result === 'PASS' ? '✅' : '❌';
    console.log(`   ${emoji} ${test}: ${result}`);
  });

  const passedTests = Object.values(testResults).filter(result => result === 'PASS').length;
  const totalTests = Object.values(testResults).length;

  console.log(`\n🎯 OVERALL RESULT: ${passedTests}/${totalTests} tests would pass`);

  if (passedTests === totalTests) {
    console.log('✅ All tests would PASS - SSOT consolidation is complete');
  } else {
    console.log('❌ Some tests would FAIL - SSOT consolidation is required');
    console.log('   This is EXPECTED behavior - tests are designed to fail until consolidation');
  }

  return {
    definitions,
    importViolations,
    needsConsolidation,
    testResults
  };
}

// Run the analysis
runAnalysis().catch(console.error);