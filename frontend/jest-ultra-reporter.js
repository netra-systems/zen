class UltraFastReporter {
  constructor(globalConfig, options) {
    this._globalConfig = globalConfig;
    this._options = options;
    this.startTime = Date.now();
    this.testResults = [];
    this.currentTestFile = null;
  }

  onRunStart() {
    this.startTime = Date.now();
    if (!process.env.JEST_ULTRA_SILENT) {
      // console output removed: console.log('🚀 Ultra Test Execution Starting...');
    }
  }

  onTestFileStart(test) {
    this.currentTestFile = test.path;
    this.fileStartTime = Date.now();
  }

  onTestFileResult(test, testResult) {
    const duration = Date.now() - this.fileStartTime;
    const failed = testResult.numFailingTests > 0;
    
    if (failed || duration > 1000 || !process.env.JEST_ULTRA_SILENT) {
      const status = failed ? '❌' : '✅';
      const fileName = test.path.split('/').pop();
      const timing = duration > 1000 ? ` (${duration}ms)` : '';
      
      if (failed) {
        // console output removed: console.log(`${status} ${fileName}${timing}`);
        testResult.testResults
          .filter(tr => tr.status === 'failed')
          .forEach(tr => {
            // console output removed: console.log(`   ↳ ${tr.fullName}`);
            if (tr.failureMessages?.length > 0) {
              // console output removed: console.log(`     ${tr.failureMessages[0].split('\n')[0]}`);
            }
          });
      } else if (!process.env.JEST_ULTRA_SILENT) {
        // console output removed: console.log(`${status} ${fileName}${timing}`);
      }
    }
    
    this.testResults.push({
      path: test.path,
      duration,
      failed,
      numTests: testResult.numPassingTests + testResult.numFailingTests,
    });
  }

  onRunComplete(contexts, results) {
    const totalTime = Date.now() - this.startTime;
    const totalTests = results.numTotalTests;
    const passedTests = results.numPassedTests;
    const failedTests = results.numFailedTests;
    const skippedTests = results.numTotalTests - results.numPassedTests - results.numFailedTests;
    
    // Calculate performance metrics
    const testsPerSecond = Math.round(totalTests / (totalTime / 1000));
    const slowFiles = this.testResults
      .filter(result => result.duration > 1000)
      .sort((a, b) => b.duration - a.duration)
      .slice(0, 5);
    
    // console output removed: console.log('\n' + '='.repeat(60));
    // console output removed: console.log('🚀 ULTRA TEST RESULTS');
    // console output removed: console.log('='.repeat(60));
    
    if (failedTests > 0) {
      // console output removed: console.log(`❌ ${failedTests} failed, ✅ ${passedTests} passed`);
    } else {
      // console output removed: console.log(`✅ All ${passedTests} tests passed!`);
    }
    
    if (skippedTests > 0) {
      // console output removed: console.log(`⏭️  ${skippedTests} skipped`);
    }
    
    // console output removed: console.log(`⚡ ${totalTime}ms total (${testsPerSecond} tests/sec)`);
    
    if (slowFiles.length > 0) {
      // console output removed: console.log('\n📊 Performance Analysis:');
      slowFiles.forEach(file => {
        const fileName = file.path.split('/').pop();
        // console output removed: console.log(`   ${fileName}: ${file.duration}ms (${file.numTests} tests)`);
      });
    }
    
    // Memory usage if available
    if (process.memoryUsage) {
      const memory = process.memoryUsage();
      const usedMB = Math.round(memory.heapUsed / 1024 / 1024);
      // console output removed: console.log(`💾 Memory: ${usedMB}MB heap used`);
    }
    
    // Performance recommendations
    if (totalTime > 10000) {
      // console output removed: console.log('\n⚠️  Performance Tips:');
      // console output removed: console.log('   • Use --maxWorkers for better parallelization');
      // console output removed: console.log('   • Consider test sharding for CI/CD');
      // console output removed: console.log('   • Mock heavy dependencies');
    }
    
    // console output removed: console.log('='.repeat(60));
    
    // Exit with proper code
    if (failedTests > 0) {
      process.exit(1);
    }
  }

  getLastError() {
    return null;
  }
}

module.exports = UltraFastReporter;