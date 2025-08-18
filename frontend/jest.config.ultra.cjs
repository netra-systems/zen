const nextJest = require('next/jest.js');
const os = require('os');
const fs = require('fs');
const crypto = require('crypto');

const createJestConfig = nextJest({
  dir: './',
});

// Advanced CPU and memory optimization
const cpuCount = os.cpus().length;
const totalMemory = os.totalmem();
const freeMemory = os.freemem();
const memoryRatio = freeMemory / totalMemory;

// Dynamic worker allocation based on system resources
const calculateOptimalWorkers = () => {
  const baseCpuWorkers = Math.max(1, Math.floor(cpuCount * 0.8));
  const memoryWorkers = memoryRatio > 0.3 ? baseCpuWorkers : Math.floor(baseCpuWorkers * 0.6);
  return Math.min(baseCpuWorkers, memoryWorkers, 16); // Cap at 16 workers
};

// Intelligent test sharding configuration
const enableSharding = process.env.JEST_SHARD_TOTAL > 1;
const shardIndex = parseInt(process.env.JEST_SHARD_INDEX || '1', 10);
const shardTotal = parseInt(process.env.JEST_SHARD_TOTAL || '1', 10);

// Cache hash for cache invalidation
const getCacheHash = () => {
  const packageJsonPath = require.resolve('../package.json');
  const jestConfigPath = __filename;
  const packageContent = fs.readFileSync(packageJsonPath, 'utf8');
  const configContent = fs.readFileSync(jestConfigPath, 'utf8');
  return crypto.createHash('md5').update(packageContent + configContent).digest('hex').substring(0, 8);
};

const cacheHash = getCacheHash();

const config = {
  // Ultra performance settings
  maxWorkers: calculateOptimalWorkers(),
  maxConcurrency: 15,
  
  // Advanced caching with invalidation
  cache: true,
  cacheDirectory: `<rootDir>/.jest-cache-${cacheHash}`,
  
  // Memory and resource optimization
  testEnvironment: 'jest-environment-jsdom',
  testEnvironmentOptions: {
    resources: 'usable',
    runScripts: 'outside-only',
    pretendToBeVisual: false,
    // Reduce memory footprint
    html: '<!DOCTYPE html><html><body></body></html>',
  },
  
  // Ultra-fast test discovery
  testMatch: [
    '**/__tests__/**/*.test.[jt]s?(x)',
  ],
  
  // Aggressive test timeout
  testTimeout: 6000,
  
  // Ultra-optimized setup
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ultra.ts'],
  
  // Coverage disabled for maximum speed
  collectCoverage: false,
  
  // Memory management
  clearMocks: true,
  restoreMocks: true,
  resetModules: false, // Keep modules in memory
  
  // Fail fast for CI
  bail: enableSharding ? false : 3,
  
  // Silent mode for performance
  silent: true,
  verbose: false,
  
  // Disable file watchers
  watchPlugins: [],
  
  // Module resolution optimization
  moduleNameMapper: {
    '^@/contexts/(.*)$': '<rootDir>/contexts/$1',
    '^@/components/(.*)$': '<rootDir>/components/$1',
    '^@/lib/(.*)$': '<rootDir>/lib/$1',
    '^@/hooks/(.*)$': '<rootDir>/hooks/$1',
    '^@/store/(.*)$': '<rootDir>/store/$1',
    '^@/types/(.*)$': '<rootDir>/types/$1',
    '^@/auth/(.*)$': '<rootDir>/auth/$1',
    '^@/services/(.*)$': '<rootDir>/services/$1',
    '^@/providers/(.*)$': '<rootDir>/providers/$1',
    '^@/(.*)$': '<rootDir>/$1',
    '\\.(css|less|scss|sass)$': '<rootDir>/__mocks__/styleMock.js',
    'react-syntax-highlighter/dist/esm/styles/prism': '<rootDir>/__mocks__/prismStyleMock.js',
    'react-markdown': '<rootDir>/__mocks__/react-markdown.tsx',
  },
  
  // Optimized transform patterns
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-.*|rehype-.*|unified|micromark.*|mdast-.*|hast-.*|unist-.*|vfile|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|is-plain-obj|trough|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|estree-util-.*|devlop|zwitch|longest-streak|markdown-table|trim-lines|ccount|escape-string-regexp|html-void-elements|web-namespaces|estree-walker)/)',
  ],
  
  // Sharding configuration for CI
  ...(enableSharding && {
    shard: {
      shardIndex,
      shardTotal,
    },
  }),
  
  // Ultra-fast reporters
  reporters: [
    ['default', { 
      summaryThreshold: 0,
      silent: true,
    }],
    ['<rootDir>/jest-ultra-reporter.js'],
  ],
  
  // Advanced projects for parallel execution
  projects: [
    {
      displayName: 'unit-fast',
      testEnvironment: 'jest-environment-jsdom',
      testMatch: [
        '<rootDir>/__tests__/components/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/hooks/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/lib/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/utils/**/*.test.[jt]s?(x)',
      ],
      maxWorkers: Math.max(2, Math.floor(calculateOptimalWorkers() * 0.4)),
      setupFilesAfterEnv: ['<rootDir>/jest.setup.ultra.ts'],
      testTimeout: 5000,
    },
    {
      displayName: 'services',
      testEnvironment: 'jest-environment-jsdom',
      testMatch: [
        '<rootDir>/__tests__/services/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/store/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/auth/**/*.test.[jt]s?(x)',
      ],
      maxWorkers: Math.max(1, Math.floor(calculateOptimalWorkers() * 0.3)),
      setupFilesAfterEnv: ['<rootDir>/jest.setup.ultra.ts'],
      testTimeout: 8000,
    },
    {
      displayName: 'integration',
      testEnvironment: 'jest-environment-jsdom',
      testMatch: [
        '<rootDir>/__tests__/integration/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/chat/**/*.test.[jt]s?(x)',
      ],
      maxWorkers: Math.max(1, Math.floor(calculateOptimalWorkers() * 0.3)),
      setupFilesAfterEnv: ['<rootDir>/jest.setup.ultra.ts'],
      testTimeout: 15000,
    },
  ],
};

console.log(`🚀 Ultra Jest Config Initialized`);
console.log(`   CPU Cores: ${cpuCount} | Workers: ${calculateOptimalWorkers()}`);
console.log(`   Memory: ${Math.round(memoryRatio * 100)}% free | Cache: ${cacheHash}`);
if (enableSharding) {
  console.log(`   Sharding: ${shardIndex}/${shardTotal}`);
}

module.exports = createJestConfig(config);