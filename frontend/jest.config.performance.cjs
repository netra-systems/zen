const nextJest = require('next/jest.js');
const os = require('os');

const createJestConfig = nextJest({
  dir: './',
});

// Calculate optimal worker count based on CPU cores
const cpuCount = os.cpus().length;
const optimalWorkers = Math.max(1, Math.floor(cpuCount * 0.75)); // Use 75% of cores

const config = {
  // Performance optimizations
  maxWorkers: optimalWorkers,
  maxConcurrency: 10,
  
  // Caching optimizations
  cache: true,
  cacheDirectory: '<rootDir>/.jest-cache',
  
  // Coverage optimizations (disable during regular test runs)
  collectCoverage: false,
  coverageProvider: 'v8',
  
  // Test environment optimizations
  testEnvironment: 'jest-environment-jsdom',
  testEnvironmentOptions: {
    // Reduce jsdom resource usage
    resources: 'usable',
    runScripts: 'dangerously',
    pretendToBeVisual: false,
  },
  
  // Faster test discovery
  testMatch: [
    '**/__tests__/**/*.test.[jt]s?(x)',
    '**/__tests__/**/*.spec.[jt]s?(x)',
  ],
  
  // Reduce test timeout for faster failure detection
  testTimeout: 10000, // 10 seconds instead of default 30
  
  // Setup optimizations
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  
  // Module resolution optimizations
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
  },
  
  // Transform optimizations - Comprehensive ESM pattern
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-.*|rehype-.*|unified|micromark.*|mdast-.*|hast-.*|unist-.*|vfile|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|is-plain-obj|trough|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|estree-util-.*|devlop|zwitch|longest-streak|markdown-table|trim-lines|ccount|escape-string-regexp|html-void-elements|web-namespaces|estree-walker)/)',
  ],
  
  // Disable watch plugins for CI/performance testing
  watchPlugins: [],
  
  // Clear mocks automatically between tests for consistency
  clearMocks: true,
  
  // Restore mocks automatically
  restoreMocks: true,
  
  // Reset modules for test isolation (can be disabled for even more speed)
  resetModules: false,
  
  // Bail on first test failure (optional - speeds up CI)
  bail: false,
  
  // Faster reporter for CI
  reporters: [
    ['default', { summaryThreshold: 10 }]
  ],
  
  // Disable source maps in tests for speed (handled in transform config above)
  
  // Uncomment below to use projects (currently disabled for simpler setup)
  // projects: [
  //   {
  //     displayName: 'unit',
  //     testMatch: [
  //       '**/__tests__/components/**/*.test.[jt]s?(x)',
  //       '**/__tests__/hooks/**/*.test.[jt]s?(x)',
  //       '**/__tests__/services/**/*.test.[jt]s',
  //       '**/__tests__/store/**/*.test.[jt]s',
  //       '**/__tests__/auth/**/*.test.[jt]s',
  //     ],
  //     maxWorkers: optimalWorkers,
  //   },
  //   {
  //     displayName: 'integration',
  //     testMatch: [
  //       '**/__tests__/integration/**/*.test.[jt]s?(x)',
  //       '**/__tests__/chat/**/*.test.[jt]s?(x)',
  //       '**/__tests__/system/**/*.test.[jt]s?(x)',
  //     ],
  //     maxWorkers: Math.max(1, Math.floor(optimalWorkers / 2)),
  //   },
  //   {
  //     displayName: 'imports',
  //     testMatch: [
  //       '**/__tests__/imports/**/*.test.[jt]s?(x)',
  //     ],
  //     maxWorkers: 1,
  //   },
  // ],
};

module.exports = createJestConfig(config);