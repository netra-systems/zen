#!/usr/bin/env node

const { spawn, exec } = require('child_process');
const os = require('os');
const fs = require('fs');
const path = require('path');

class TestOptimizer {
  constructor() {
    this.cpuCount = os.cpus().length;
    this.totalMemory = os.totalmem();
    this.freeMemory = os.freemem();
    this.platform = os.platform();
    this.testCategories = this.analyzeTestFiles();
    this.gitChanges = null;
  }

  async analyzeTestFiles() {
    const testDir = path.join(__dirname, '__tests__');
    const categories = {
      unit: { weight: 0.3, files: [], avgTime: 100 },
      integration: { weight: 0.7, files: [], avgTime: 500 },
      e2e: { weight: 1.0, files: [], avgTime: 2000 },
    };

    const analyzeDirectory = (dir, category = 'unit') => {
      if (!fs.existsSync(dir)) return;
      
      const files = fs.readdirSync(dir, { withFileTypes: true });
      files.forEach(file => {
        if (file.isDirectory()) {
          const subCategory = file.name.includes('integration') ? 'integration' :
                            file.name.includes('e2e') ? 'e2e' : category;
          analyzeDirectory(path.join(dir, file.name), subCategory);
        } else if (file.name.endsWith('.test.ts') || file.name.endsWith('.test.tsx')) {
          const filePath = path.join(dir, file.name);
          const fileSize = fs.statSync(filePath).size;
          
          // Estimate test category based on file size and path
          let detectedCategory = category;
          if (filePath.includes('integration')) detectedCategory = 'integration';
          if (filePath.includes('e2e')) detectedCategory = 'e2e';
          if (fileSize > 10000) detectedCategory = 'integration';
          if (fileSize > 50000) detectedCategory = 'e2e';
          
          categories[detectedCategory].files.push({
            path: filePath,
            size: fileSize,
            estimatedTime: this.estimateTestTime(filePath, fileSize),
          });
        }
      });
    };

    analyzeDirectory(testDir);
    return categories;
  }

  estimateTestTime(filePath, fileSize) {
    // Base estimation on file size and path indicators
    let baseTime = Math.max(50, fileSize / 100); // 1ms per 100 bytes minimum 50ms
    
    if (filePath.includes('integration')) baseTime *= 3;
    if (filePath.includes('websocket')) baseTime *= 2;
    if (filePath.includes('chat')) baseTime *= 1.5;
    if (filePath.includes('auth')) baseTime *= 1.3;
    
    return Math.round(baseTime);
  }

  async detectGitChanges() {
    return new Promise((resolve) => {
      exec('git diff --name-only HEAD~1 HEAD', (error, stdout) => {
        if (error) {
          resolve([]);
          return;
        }
        
        const changes = stdout.split('\n')
          .filter(line => line.trim())
          .filter(line => line.endsWith('.ts') || line.endsWith('.tsx') || line.endsWith('.js') || line.endsWith('.jsx'));
        
        resolve(changes);
      });
    });
  }

  calculateOptimalStrategy() {
    const memoryRatio = this.freeMemory / this.totalMemory;
    const isLowMemory = memoryRatio < 0.2;
    const isHighCpu = this.cpuCount >= 8;
    
    let strategy = {
      maxWorkers: Math.max(1, Math.floor(this.cpuCount * 0.75)),
      useSharding: false,
      prioritizeChanged: true,
      useProjects: true,
      cacheStrategy: 'aggressive',
    };

    // Adjust for low memory
    if (isLowMemory) {
      strategy.maxWorkers = Math.max(1, Math.floor(this.cpuCount * 0.5));
      strategy.cacheStrategy = 'minimal';
    }

    // Adjust for high CPU
    if (isHighCpu && !isLowMemory) {
      strategy.maxWorkers = Math.min(16, Math.floor(this.cpuCount * 0.9));
      strategy.useSharding = true;
    }

    // Platform-specific optimizations
    if (this.platform === 'win32') {
      strategy.maxWorkers = Math.min(strategy.maxWorkers, 8); // Windows process limits
    }

    return strategy;
  }

  async generateOptimizedTestPlan(options = {}) {
    const strategy = this.calculateOptimalStrategy();
    this.gitChanges = await this.detectGitChanges();
    
    const plan = {
      strategy,
      phases: [],
      estimatedTime: 0,
    };

    // Phase 1: Changed files (if any)
    if (this.gitChanges.length > 0 && strategy.prioritizeChanged) {
      const changedTests = this.findRelatedTests(this.gitChanges);
      if (changedTests.length > 0) {
        plan.phases.push({
          name: 'changed-files',
          description: 'Tests related to changed files',
          tests: changedTests,
          priority: 1,
          estimatedTime: changedTests.reduce((sum, test) => sum + test.estimatedTime, 0),
        });
      }
    }

    // Phase 2: Fast unit tests
    const fastTests = this.testCategories.unit.files
      .filter(test => test.estimatedTime < 200);
    
    if (fastTests.length > 0) {
      plan.phases.push({
        name: 'unit-fast',
        description: 'Fast unit tests',
        tests: fastTests,
        priority: 2,
        estimatedTime: fastTests.reduce((sum, test) => sum + test.estimatedTime, 0),
      });
    }

    // Phase 3: Remaining unit tests
    const remainingUnitTests = this.testCategories.unit.files
      .filter(test => test.estimatedTime >= 200);
      
    if (remainingUnitTests.length > 0) {
      plan.phases.push({
        name: 'unit-remaining',
        description: 'Remaining unit tests',
        tests: remainingUnitTests,
        priority: 3,
        estimatedTime: remainingUnitTests.reduce((sum, test) => sum + test.estimatedTime, 0),
      });
    }

    // Phase 4: Integration tests
    if (this.testCategories.integration.files.length > 0) {
      plan.phases.push({
        name: 'integration',
        description: 'Integration tests',
        tests: this.testCategories.integration.files,
        priority: 4,
        estimatedTime: this.testCategories.integration.files.reduce((sum, test) => sum + test.estimatedTime, 0),
      });
    }

    plan.estimatedTime = plan.phases.reduce((sum, phase) => sum + phase.estimatedTime, 0);
    
    return plan;
  }

  findRelatedTests(changedFiles) {
    const relatedTests = [];
    
    changedFiles.forEach(changedFile => {
      // Find direct test files
      const testFile = changedFile.replace(/\.(ts|tsx|js|jsx)$/, '.test.$1');
      const testPath = path.join(__dirname, '__tests__', testFile);
      
      if (fs.existsSync(testPath)) {
        relatedTests.push({
          path: testPath,
          reason: 'direct-test',
          estimatedTime: this.estimateTestTime(testPath, fs.statSync(testPath).size),
        });
      }

      // Find tests that might import this file
      Object.values(this.testCategories).forEach(category => {
        category.files.forEach(testFile => {
          try {
            const content = fs.readFileSync(testFile.path, 'utf8');
            const importPath = changedFile.replace(/\.(ts|tsx|js|jsx)$/, '');
            
            if (content.includes(importPath) || content.includes(changedFile)) {
              relatedTests.push({
                ...testFile,
                reason: 'imports-changed-file',
              });
            }
          } catch (error) {
            // Ignore read errors
          }
        });
      });
    });

    // Remove duplicates
    const uniqueTests = relatedTests.filter((test, index, array) => 
      array.findIndex(t => t.path === test.path) === index
    );

    return uniqueTests;
  }

  async executeOptimizedTests(options = {}) {
    const plan = await this.generateOptimizedTestPlan(options);
    
    // console output removed: console.log('🚀 Test Optimization Plan');
    // console output removed: console.log('='.repeat(60));
    // console output removed: console.log(`System: ${this.cpuCount} CPUs, ${Math.round(this.freeMemory / 1024 / 1024 / 1024)}GB free memory`);
    // console output removed: console.log(`Strategy: ${plan.strategy.maxWorkers} workers, ${plan.strategy.cacheStrategy} cache`);
    // console output removed: console.log(`Estimated time: ${Math.round(plan.estimatedTime / 1000)}s`);
    
    if (this.gitChanges.length > 0) {
      // console output removed: console.log(`Changed files: ${this.gitChanges.length}`);
    }
    
    // console output removed: console.log('='.repeat(60));

    let totalStartTime = Date.now();
    let totalTests = 0;
    let totalPassed = 0;
    let totalFailed = 0;

    for (const phase of plan.phases) {
      // console output removed: console.log(`\n📋 Phase: ${phase.description}`);
      // console output removed: console.log(`   Tests: ${phase.tests.length}, Priority: ${phase.priority}`);
      
      const phaseStartTime = Date.now();
      
      try {
        const result = await this.runTestPhase(phase, plan.strategy, options);
        totalTests += result.total;
        totalPassed += result.passed;
        totalFailed += result.failed;
        
        const phaseDuration = Date.now() - phaseStartTime;
        // console output removed: console.log(`   ✅ Completed in ${phaseDuration}ms`);
        
        // Fail fast if requested
        if (result.failed > 0 && options.bail) {
          // console output removed: console.log(`❌ Stopping due to failures (--bail)`);
          break;
        }
        
      } catch (error) {
        // console output removed: console.log(`   ❌ Phase failed: ${error.message}`);
        if (options.bail) break;
      }
    }

    const totalDuration = Date.now() - totalStartTime;
    
    // console output removed: console.log('\n' + '='.repeat(60));
    // console output removed: console.log('🏁 FINAL RESULTS');
    // console output removed: console.log('='.repeat(60));
    // console output removed: console.log(`Total: ${totalTests} tests in ${totalDuration}ms`);
    // console output removed: console.log(`Passed: ${totalPassed}, Failed: ${totalFailed}`);
    // console output removed: console.log(`Performance: ${Math.round(totalTests / (totalDuration / 1000))} tests/second`);
    // console output removed: console.log('='.repeat(60));

    return { totalTests, totalPassed, totalFailed, totalDuration };
  }

  async runTestPhase(phase, strategy, options) {
    return new Promise((resolve, reject) => {
      const jestArgs = [
        '--config', 'jest.config.ultra.cjs',
        '--maxWorkers', strategy.maxWorkers.toString(),
        '--silent',
      ];

      if (options.coverage) jestArgs.push('--coverage');
      if (options.updateSnapshots) jestArgs.push('--updateSnapshot');
      
      // Add test file patterns
      phase.tests.forEach(test => {
        jestArgs.push(test.path);
      });

      const jestProcess = spawn('npx', ['jest', ...jestArgs], {
        stdio: ['inherit', 'pipe', 'pipe'],
        shell: true,
      });

      let output = '';
      let errorOutput = '';

      jestProcess.stdout.on('data', (data) => {
        output += data.toString();
        if (!options.silent) {
          process.stdout.write(data);
        }
      });

      jestProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
        if (!options.silent) {
          process.stderr.write(data);
        }
      });

      jestProcess.on('close', (code) => {
        // Parse Jest output for results
        const results = this.parseJestOutput(output + errorOutput);
        
        if (code === 0) {
          resolve(results);
        } else {
          resolve({ ...results, failed: results.failed || 1 });
        }
      });

      jestProcess.on('error', (error) => {
        reject(error);
      });
    });
  }

  parseJestOutput(output) {
    // Simple parsing of Jest output
    const passedMatch = output.match(/(\d+) passed/);
    const failedMatch = output.match(/(\d+) failed/);
    const totalMatch = output.match(/Tests:\s+(\d+) total/);

    return {
      passed: passedMatch ? parseInt(passedMatch[1], 10) : 0,
      failed: failedMatch ? parseInt(failedMatch[1], 10) : 0,
      total: totalMatch ? parseInt(totalMatch[1], 10) : 0,
    };
  }
}

// CLI Interface
async function main() {
  const args = process.argv.slice(2);
  const options = {
    bail: args.includes('--bail'),
    coverage: args.includes('--coverage'),
    silent: args.includes('--silent'),
    updateSnapshots: args.includes('--updateSnapshot'),
  };

  if (args.includes('--help')) {
    // console output removed: console.log(`
Ultra Test Optimizer - Intelligent Jest Execution

Usage: node test-optimizer.js [options]

Options:
  --bail              Stop on first test failure
  --coverage          Generate coverage report
  --silent            Minimal output
  --updateSnapshot    Update snapshots
  --help              Show this help

Features:
  🚀 Automatic CPU/memory optimization
  📊 Intelligent test prioritization  
  🔍 Git change detection
  ⚡ Multi-phase execution strategy
  📈 Performance analysis
`);
    process.exit(0);
  }

  try {
    const optimizer = new TestOptimizer();
    const results = await optimizer.executeOptimizedTests(options);
    
    process.exit(results.totalFailed > 0 ? 1 : 0);
  } catch (error) {
    // console output removed: console.log('❌ Test optimization failed:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = TestOptimizer;