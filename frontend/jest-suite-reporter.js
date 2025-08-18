const fs = require('fs');
const path = require('path');

class TestSuiteReporter {
  constructor(globalConfig, options) {
    this._globalConfig = globalConfig;
    this._options = options || {};
    this.suiteResults = {};
  }

  onRunStart(results, options) {
    // console output removed: console.log('\n🚀 Starting test suite execution...\n');
    this.startTime = Date.now();
  }

  onTestResult(test, testResult) {
    const suiteName = testResult.displayName || 'default';
    
    if (!this.suiteResults[suiteName]) {
      this.suiteResults[suiteName] = {
        passed: 0,
        failed: 0,
        skipped: 0,
        total: 0,
        duration: 0,
        files: []
      };
    }
    
    const suite = this.suiteResults[suiteName];
    suite.total += testResult.numTotalTests;
    suite.passed += testResult.numPassedTests;
    suite.failed += testResult.numFailedTests;
    suite.skipped += testResult.numPendingTests;
    suite.duration += testResult.perfStats.runtime;
    suite.files.push({
      path: testResult.testFilePath,
      passed: testResult.numPassedTests,
      failed: testResult.numFailedTests,
      duration: testResult.perfStats.runtime
    });
    
    const status = testResult.numFailedTests > 0 ? '❌' : '✅';
    const fileName = path.basename(testResult.testFilePath);
    // console output removed: console.log(`${status} [${suiteName}] ${fileName} (${testResult.perfStats.runtime}ms)`);
  }

  onRunComplete(contexts, results) {
    const duration = Date.now() - this.startTime;
    
    // console output removed: console.log('\n' + '='.repeat(80));
    // console output removed: console.log('📊 TEST SUITE SUMMARY');
    // console output removed: console.log('='.repeat(80) + '\n');
    
    Object.entries(this.suiteResults).forEach(([name, suite]) => {
      const passRate = ((suite.passed / suite.total) * 100).toFixed(1);
      const avgDuration = (suite.duration / suite.files.length).toFixed(0);
      
      // console output removed: console.log(`📦 ${name.toUpperCase()}`);
      // console output removed: console.log(`   ✅ Passed: ${suite.passed}/${suite.total} (${passRate}%)`);
      // console output removed: console.log(`   ❌ Failed: ${suite.failed}`);
      // console output removed: console.log(`   ⏭️  Skipped: ${suite.skipped}`);
      // console output removed: console.log(`   ⏱️  Duration: ${(suite.duration / 1000).toFixed(2)}s (avg: ${avgDuration}ms/file)`);
      // console output removed: console.log(`   📁 Files tested: ${suite.files.length}`);
      // console output removed: console.log('');
    });
    
    // console output removed: console.log('='.repeat(80));
    // console output removed: console.log(`Total Duration: ${(duration / 1000).toFixed(2)}s`);
    // console output removed: console.log(`Total Tests: ${results.numTotalTests}`);
    // console output removed: console.log(`Total Suites: ${results.numTotalTestSuites}`);
    // console output removed: console.log('='.repeat(80) + '\n');
    
    // Save results to file if configured
    if (this._options.outputDirectory) {
      const outputDir = this._options.outputDirectory.replace('<rootDir>', process.cwd());
      const outputFile = path.join(outputDir, this._options.outputName || 'suite-results.json');
      
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }
      
      const report = {
        timestamp: new Date().toISOString(),
        duration,
        suites: this.suiteResults,
        totals: {
          tests: results.numTotalTests,
          passed: results.numPassedTests,
          failed: results.numFailedTests,
          skipped: results.numPendingTests,
          suites: results.numTotalTestSuites
        }
      };
      
      fs.writeFileSync(outputFile, JSON.stringify(report, null, 2));
      // console output removed: console.log(`📄 Results saved to: ${outputFile}\n`);
    }
  }
}

module.exports = TestSuiteReporter;