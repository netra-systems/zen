#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class TestShardRunner {
  constructor() {
    this.testFiles = [];
    this.shardConfig = {
      totalShards: parseInt(process.env.JEST_SHARD_TOTAL || '1', 10),
      currentShard: parseInt(process.env.JEST_SHARD_INDEX || '1', 10),
    };
  }

  async discoverTestFiles() {
    const testDir = path.join(__dirname, '__tests__');
    const testFiles = [];

    const scanDirectory = (dir) => {
      if (!fs.existsSync(dir)) return;
      
      const items = fs.readdirSync(dir, { withFileTypes: true });
      items.forEach(item => {
        if (item.isDirectory()) {
          scanDirectory(path.join(dir, item.name));
        } else if (item.name.match(/\.test\.[jt]sx?$/)) {
          const filePath = path.join(dir, item.name);
          const stats = fs.statSync(filePath);
          
          testFiles.push({
            path: filePath,
            relativePath: path.relative(testDir, filePath),
            size: stats.size,
            estimatedDuration: this.estimateTestDuration(filePath, stats.size),
            category: this.categorizeTest(filePath),
          });
        }
      });
    };

    scanDirectory(testDir);
    
    // Sort by estimated duration (longest first) for better load balancing
    testFiles.sort((a, b) => b.estimatedDuration - a.estimatedDuration);
    
    this.testFiles = testFiles;
    return testFiles;
  }

  estimateTestDuration(filePath, fileSize) {
    let duration = Math.max(100, fileSize / 50); // Base: 1ms per 50 bytes, min 100ms
    
    // Adjust based on file path indicators
    if (filePath.includes('integration')) duration *= 5;
    if (filePath.includes('e2e')) duration *= 10;
    if (filePath.includes('websocket')) duration *= 3;
    if (filePath.includes('auth')) duration *= 2;
    if (filePath.includes('chat')) duration *= 2;
    if (filePath.includes('comprehensive')) duration *= 4;
    if (filePath.includes('critical')) duration *= 3;
    
    return Math.round(duration);
  }

  categorizeTest(filePath) {
    if (filePath.includes('integration')) return 'integration';
    if (filePath.includes('e2e')) return 'e2e';
    if (filePath.includes('components')) return 'unit';
    if (filePath.includes('hooks')) return 'unit';
    if (filePath.includes('services')) return 'unit';
    if (filePath.includes('store')) return 'unit';
    return 'other';
  }

  distributeTestsAcrossShards() {
    if (this.shardConfig.totalShards === 1) {
      return this.testFiles;
    }

    // Advanced load balancing algorithm
    const shards = Array.from({ length: this.shardConfig.totalShards }, () => ({
      files: [],
      totalDuration: 0,
      totalSize: 0,
    }));

    // Distribute tests using "Longest Processing Time First" algorithm
    this.testFiles.forEach(testFile => {
      // Find shard with minimum total duration
      const targetShard = shards.reduce((min, shard, index) => 
        shard.totalDuration < shards[min].totalDuration ? index : min, 0
      );
      
      shards[targetShard].files.push(testFile);
      shards[targetShard].totalDuration += testFile.estimatedDuration;
      shards[targetShard].totalSize += testFile.size;
    });

    // Return files for current shard
    const currentShardIndex = this.shardConfig.currentShard - 1;
    const currentShardFiles = shards[currentShardIndex]?.files || [];

    console.log(`📊 Shard Distribution (${this.shardConfig.currentShard}/${this.shardConfig.totalShards}):`);
    shards.forEach((shard, index) => {
      const isCurrent = index === currentShardIndex;
      const marker = isCurrent ? '👉' : '  ';
      console.log(`${marker} Shard ${index + 1}: ${shard.files.length} files, ~${Math.round(shard.totalDuration / 1000)}s`);
    });

    return currentShardFiles;
  }

  generateShardedJestConfig(shardFiles) {
    const config = {
      displayName: `shard-${this.shardConfig.currentShard}`,
      testMatch: shardFiles.map(file => file.path),
      maxWorkers: '50%',
      cache: true,
      cacheDirectory: `<rootDir>/.jest-cache-shard-${this.shardConfig.currentShard}`,
      setupFilesAfterEnv: ['<rootDir>/jest.setup.ultra.ts'],
      testEnvironment: 'jest-environment-jsdom',
      testTimeout: 10000,
      silent: true,
      bail: false,
      reporters: [
        ['<rootDir>/jest-ultra-reporter.js'],
        ['jest-junit', {
          outputDirectory: './test-results',
          outputName: `shard-${this.shardConfig.currentShard}-results.xml`,
          suiteName: `Shard ${this.shardConfig.currentShard}`,
        }],
      ],
      coverageDirectory: `./coverage/shard-${this.shardConfig.currentShard}`,
    };

    return config;
  }

  async runShard(options = {}) {
    await this.discoverTestFiles();
    const shardFiles = this.distributeTestsAcrossShards();

    if (shardFiles.length === 0) {
      console.log(`⚠️  No tests allocated to shard ${this.shardConfig.currentShard}`);
      return { success: true, tests: 0 };
    }

    console.log(`🚀 Running Shard ${this.shardConfig.currentShard}/${this.shardConfig.totalShards}`);
    console.log(`📁 Files: ${shardFiles.length}`);
    console.log(`⏱️  Estimated: ~${Math.round(shardFiles.reduce((sum, f) => sum + f.estimatedDuration, 0) / 1000)}s`);
    console.log('='.repeat(60));

    const jestArgs = [
      '--config', await this.writeShardConfig(shardFiles),
      '--runInBand', // Better for sharded execution
    ];

    if (options.coverage) {
      jestArgs.push('--coverage');
    }

    if (options.bail) {
      jestArgs.push('--bail');
    }

    if (options.updateSnapshots) {
      jestArgs.push('--updateSnapshot');
    }

    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      const jestProcess = spawn('npx', ['jest', ...jestArgs], {
        stdio: 'inherit',
        shell: true,
        env: {
          ...process.env,
          JEST_SHARD_INDEX: this.shardConfig.currentShard.toString(),
          JEST_SHARD_TOTAL: this.shardConfig.totalShards.toString(),
          JEST_ULTRA_SILENT: options.silent ? 'true' : 'false',
        },
      });

      jestProcess.on('close', (code) => {
        const duration = Date.now() - startTime;
        
        console.log('\n' + '='.repeat(60));
        console.log(`🏁 Shard ${this.shardConfig.currentShard} completed in ${duration}ms`);
        console.log(`📊 Performance: ${Math.round(shardFiles.length / (duration / 1000))} files/second`);
        
        resolve({
          success: code === 0,
          duration,
          tests: shardFiles.length,
          shard: this.shardConfig.currentShard,
        });
      });

      jestProcess.on('error', (error) => {
        reject(error);
      });
    });
  }

  async writeShardConfig(shardFiles) {
    const config = this.generateShardedJestConfig(shardFiles);
    const configPath = path.join(__dirname, `jest.config.shard-${this.shardConfig.currentShard}.js`);
    
    const configContent = `
const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

const config = ${JSON.stringify(config, null, 2)};

module.exports = createJestConfig(config);
`;

    fs.writeFileSync(configPath, configContent);
    return configPath;
  }

  static async aggregateShardResults() {
    const resultsDir = path.join(__dirname, 'test-results');
    const coverageDir = path.join(__dirname, 'coverage');
    
    if (!fs.existsSync(resultsDir)) {
      console.log('⚠️  No shard results found');
      return;
    }

    console.log('📊 Aggregating shard results...');
    
    // Find all shard result files
    const resultFiles = fs.readdirSync(resultsDir)
      .filter(file => file.match(/^shard-\d+-results\.xml$/))
      .map(file => path.join(resultsDir, file));

    console.log(`📄 Found ${resultFiles.length} shard result files`);

    // Merge coverage if exists
    const shardCoverageDirs = fs.readdirSync(coverageDir, { withFileTypes: true })
      .filter(item => item.isDirectory() && item.name.startsWith('shard-'))
      .map(item => path.join(coverageDir, item.name));

    if (shardCoverageDirs.length > 0) {
      console.log('🔄 Merging coverage reports...');
      
      // Use nyc to merge coverage reports
      const nycArgs = [
        'merge',
        ...shardCoverageDirs.map(dir => path.join(dir, 'coverage-final.json')),
        path.join(coverageDir, 'merged-coverage.json'),
      ];

      try {
        await new Promise((resolve, reject) => {
          const nycProcess = spawn('npx', ['nyc', ...nycArgs], {
            stdio: 'inherit',
            shell: true,
          });

          nycProcess.on('close', (code) => {
            if (code === 0) {
              console.log('✅ Coverage reports merged successfully');
              resolve();
            } else {
              console.log('⚠️  Coverage merge failed');
              resolve(); // Don't fail the whole process
            }
          });

          nycProcess.on('error', reject);
        });
      } catch (error) {
        console.log('⚠️  Coverage merge error:', error.message);
      }
    }

    console.log('✅ Shard aggregation completed');
  }
}

// CLI Interface
async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('--help')) {
    console.log(`
Test Shard Runner - Parallel Jest Execution

Usage: node test-shard-runner.js [options]

Environment Variables:
  JEST_SHARD_TOTAL      Total number of shards (default: 1)
  JEST_SHARD_INDEX      Current shard index 1-based (default: 1)

Options:
  --coverage            Generate coverage report
  --bail                Stop on first failure
  --updateSnapshot      Update snapshots
  --silent              Minimal output
  --aggregate           Aggregate results from all shards
  --help                Show this help

Examples:
  # Run shard 1 of 4
  JEST_SHARD_INDEX=1 JEST_SHARD_TOTAL=4 node test-shard-runner.js
  
  # Run with coverage
  JEST_SHARD_INDEX=2 JEST_SHARD_TOTAL=4 node test-shard-runner.js --coverage
  
  # Aggregate results after all shards complete
  node test-shard-runner.js --aggregate
`);
    process.exit(0);
  }

  if (args.includes('--aggregate')) {
    await TestShardRunner.aggregateShardResults();
    process.exit(0);
  }

  const options = {
    coverage: args.includes('--coverage'),
    bail: args.includes('--bail'),
    updateSnapshots: args.includes('--updateSnapshot'),
    silent: args.includes('--silent'),
  };

  try {
    const runner = new TestShardRunner();
    const result = await runner.runShard(options);
    
    process.exit(result.success ? 0 : 1);
  } catch (error) {
    console.error('❌ Shard execution failed:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = TestShardRunner;