#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class UltraConfigValidator {
  constructor() {
    this.results = {
      configurationLoad: false,
      setupLoad: false,
      reporterLoad: false,
      sampleTestExecution: false,
      performanceBaseline: null,
      errors: [],
    };
  }

  async validateAll() {
    console.log('🔍 Validating Ultra Test Configuration...\n');

    try {
      await this.validateConfigurationLoad();
      await this.validateSetupLoad();
      await this.validateReporterLoad();
      await this.validateSampleTestExecution();
      await this.performBaslineTest();
      
      this.printResults();
      return this.results.errors.length === 0;
    } catch (error) {
      console.error('❌ Validation failed:', error.message);
      return false;
    }
  }

  async validateConfigurationLoad() {
    console.log('📋 Validating Jest ultra configuration...');
    
    try {
      // Try to load the ultra config
      const configPath = path.join(__dirname, 'jest.config.ultra.cjs');
      if (!fs.existsSync(configPath)) {
        throw new Error('jest.config.ultra.cjs not found');
      }

      // Require the config to test loading
      delete require.cache[require.resolve('./jest.config.ultra.cjs')];
      const config = require('./jest.config.ultra.cjs');
      
      if (typeof config !== 'object') {
        throw new Error('Config did not return an object');
      }

      console.log('   ✅ Configuration loads successfully');
      console.log(`   📊 Projects: ${config.projects?.length || 'none'}`);
      console.log(`   💾 Cache directory: ${config.cacheDirectory || 'default'}`);
      
      this.results.configurationLoad = true;
    } catch (error) {
      console.log(`   ❌ Configuration load failed: ${error.message}`);
      this.results.errors.push(`Config load: ${error.message}`);
    }
  }

  async validateSetupLoad() {
    console.log('\n🛠️  Validating Jest ultra setup...');
    
    try {
      const setupPath = path.join(__dirname, 'jest.setup.ultra.ts');
      if (!fs.existsSync(setupPath)) {
        throw new Error('jest.setup.ultra.ts not found');
      }

      // Check that setup file has required optimizations
      const setupContent = fs.readFileSync(setupPath, 'utf8');
      const requiredOptimizations = [
        'TextEncoder',
        'IntersectionObserver',
        'ResizeObserver',
        'localStorage',
        'matchMedia',
        'crypto.randomUUID'
      ];

      const missingOptimizations = requiredOptimizations.filter(opt => 
        !setupContent.includes(opt)
      );

      if (missingOptimizations.length > 0) {
        throw new Error(`Missing optimizations: ${missingOptimizations.join(', ')}`);
      }

      console.log('   ✅ Setup file contains all required optimizations');
      console.log(`   🔧 Optimizations: ${requiredOptimizations.length} implemented`);
      
      this.results.setupLoad = true;
    } catch (error) {
      console.log(`   ❌ Setup validation failed: ${error.message}`);
      this.results.errors.push(`Setup: ${error.message}`);
    }
  }

  async validateReporterLoad() {
    console.log('\n📊 Validating ultra reporter...');
    
    try {
      const reporterPath = path.join(__dirname, 'jest-ultra-reporter.js');
      if (!fs.existsSync(reporterPath)) {
        throw new Error('jest-ultra-reporter.js not found');
      }

      // Try to require the reporter
      delete require.cache[require.resolve('./jest-ultra-reporter.js')];
      const Reporter = require('./jest-ultra-reporter.js');
      
      if (typeof Reporter !== 'function') {
        throw new Error('Reporter is not a constructor function');
      }

      // Test instantiation
      const reporter = new Reporter({}, {});
      if (!reporter.onRunStart || !reporter.onRunComplete) {
        throw new Error('Reporter missing required methods');
      }

      console.log('   ✅ Reporter loads and instantiates correctly');
      console.log('   📈 Performance tracking enabled');
      
      this.results.reporterLoad = true;
    } catch (error) {
      console.log(`   ❌ Reporter validation failed: ${error.message}`);
      this.results.errors.push(`Reporter: ${error.message}`);
    }
  }

  async validateSampleTestExecution() {
    console.log('\n🧪 Validating sample test execution...');
    
    try {
      // Create a minimal test file for validation
      const testContent = `
describe('Ultra Config Validation', () => {
  test('should run ultra-fast', () => {
    expect(1 + 1).toBe(2);
  });
  
  test('should have optimized environment', () => {
    expect(global.TextEncoder).toBeDefined();
    expect(global.IntersectionObserver).toBeDefined();
    expect(window.localStorage).toBeDefined();
  });
});
`;

      const testPath = path.join(__dirname, '__tests__', 'ultra-validation.test.js');
      const testDir = path.dirname(testPath);
      
      if (!fs.existsSync(testDir)) {
        fs.mkdirSync(testDir, { recursive: true });
      }
      
      fs.writeFileSync(testPath, testContent);

      // Run the test with ultra config
      const result = await this.runJestCommand([
        '--config', 'jest.config.ultra.cjs',
        '--testPathPattern', 'ultra-validation.test.js',
        '--silent'
      ]);

      // Clean up test file
      fs.unlinkSync(testPath);

      if (result.success) {
        console.log('   ✅ Sample test executed successfully');
        console.log(`   ⚡ Execution time: ${result.duration}ms`);
        this.results.sampleTestExecution = true;
      } else {
        throw new Error(`Test execution failed: ${result.error}`);
      }
    } catch (error) {
      console.log(`   ❌ Sample test execution failed: ${error.message}`);
      this.results.errors.push(`Sample test: ${error.message}`);
    }
  }

  async performBaslineTest() {
    console.log('\n⚡ Performing performance baseline test...');
    
    try {
      // Run a subset of existing tests with both configs to compare
      const ultraResult = await this.runJestCommand([
        '--config', 'jest.config.ultra.cjs',
        '--testPathPattern', 'components.*test',
        '--silent',
        '--passWithNoTests'
      ]);

      if (ultraResult.success) {
        console.log(`   ✅ Ultra config baseline: ${ultraResult.duration}ms`);
        
        this.results.performanceBaseline = {
          ultra: ultraResult.duration,
          timestamp: new Date().toISOString(),
        };

        // Provide performance feedback
        if (ultraResult.duration < 5000) {
          console.log('   🚀 Excellent performance (< 5s)');
        } else if (ultraResult.duration < 10000) {
          console.log('   ⚡ Good performance (< 10s)');
        } else {
          console.log('   ⚠️  Performance could be improved (> 10s)');
        }
      } else {
        throw new Error(`Baseline test failed: ${ultraResult.error}`);
      }
    } catch (error) {
      console.log(`   ❌ Baseline test failed: ${error.message}`);
      this.results.errors.push(`Baseline: ${error.message}`);
    }
  }

  async runJestCommand(args) {
    return new Promise((resolve) => {
      const startTime = Date.now();
      
      const jestProcess = spawn('npx', ['jest', ...args], {
        stdio: ['ignore', 'pipe', 'pipe'],
        shell: true,
      });

      let output = '';
      let errorOutput = '';

      jestProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      jestProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
      });

      jestProcess.on('close', (code) => {
        const duration = Date.now() - startTime;
        
        resolve({
          success: code === 0,
          duration,
          output,
          error: errorOutput,
        });
      });

      jestProcess.on('error', (error) => {
        resolve({
          success: false,
          duration: Date.now() - startTime,
          output: '',
          error: error.message,
        });
      });
    });
  }

  printResults() {
    console.log('\n' + '='.repeat(60));
    console.log('🏁 ULTRA CONFIGURATION VALIDATION RESULTS');
    console.log('='.repeat(60));

    const checks = [
      { name: 'Configuration Load', status: this.results.configurationLoad },
      { name: 'Setup Load', status: this.results.setupLoad },
      { name: 'Reporter Load', status: this.results.reporterLoad },
      { name: 'Sample Test Execution', status: this.results.sampleTestExecution },
    ];

    checks.forEach(check => {
      const status = check.status ? '✅ PASS' : '❌ FAIL';
      console.log(`${status} ${check.name}`);
    });

    if (this.results.performanceBaseline) {
      console.log(`\n⚡ Performance Baseline: ${this.results.performanceBaseline.ultra}ms`);
    }

    if (this.results.errors.length > 0) {
      console.log('\n❌ Errors found:');
      this.results.errors.forEach(error => {
        console.log(`   • ${error}`);
      });
      console.log('\n💡 Run the following to fix common issues:');
      console.log('   npm install');
      console.log('   npm run test:clear-cache');
    } else {
      console.log('\n🎉 All validations passed! Ultra configuration ready for use.');
      console.log('\n🚀 Quick start commands:');
      console.log('   npm run test:ultra          # Ultra-fast test execution');
      console.log('   npm run test:optimize       # Smart test optimization');
      console.log('   npm run test:shard          # Sharded parallel execution');
    }

    console.log('='.repeat(60));
  }
}

// CLI Interface
async function main() {
  const validator = new UltraConfigValidator();
  const success = await validator.validateAll();
  
  process.exit(success ? 0 : 1);
}

if (require.main === module) {
  main();
}

module.exports = UltraConfigValidator;