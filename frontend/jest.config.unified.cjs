const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

// Common configuration shared across all test suites
const commonConfig = {
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  
  // Increased timeout and proper cleanup to prevent hanging tests
  testTimeout: process.env.JEST_TIMEOUT || 30000,
  
  // Module name mapping
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
  
  // Transform ignore patterns for ESM modules
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-.*|rehype-.*|unified|micromark.*|mdast-.*|hast-.*|unist-.*|vfile|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|is-plain-obj|trough|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|estree-util-.*|devlop|zwitch|longest-streak|markdown-table|trim-lines|ccount|escape-string-regexp|html-void-elements|web-namespaces|estree-walker)/)',
  ],
  
  // Transform patterns for ESM and TypeScript modules
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: {
        jsx: 'react-jsx',
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
      },
      useESM: false
    }],
  },
  
  // Improved error handling
  verbose: process.env.CI ? false : true,
  bail: process.env.BAIL ? parseInt(process.env.BAIL) : 0,
  
  // Coverage configuration
  collectCoverageFrom: [
    'components/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    'hooks/**/*.{js,jsx,ts,tsx}',
    'store/**/*.{js,jsx,ts,tsx}',
    'services/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/__tests__/**',
    '!**/__mocks__/**',
  ],
  
  // Caching for faster runs
  cache: true,
  cacheDirectory: '<rootDir>/.jest-cache',
};

// Test suite configurations by category
const testSuites = {
  // Unit tests - fast, isolated
  unit: {
    displayName: 'Unit Tests',
    testMatch: [
      '<rootDir>/__tests__/components/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/hooks/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/store/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/lib/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/utils/**/*.test.[jt]s?(x)',
    ],
    maxWorkers: '50%', // Use half of available CPU cores
  },
  
  // Integration tests - slower, more complex
  integration: {
    displayName: 'Integration Tests',
    testMatch: [
      '<rootDir>/__tests__/integration/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/services/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/auth/**/*.test.[jt]s?(x)',
    ],
    testTimeout: 60000, // 60 seconds for integration tests
    maxWorkers: 4, // Limit parallelism for resource-intensive tests
  },
  
  // Critical path tests
  critical: {
    displayName: 'Critical Path Tests',
    testMatch: [
      '<rootDir>/__tests__/critical/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/system/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/startup/**/*.test.[jt]s?(x)',
    ],
    maxWorkers: 2, // Run critical tests with limited parallelism
    testTimeout: 45000,
  },
  
  // Visual and UI tests
  visual: {
    displayName: 'Visual Tests',
    testMatch: [
      '<rootDir>/__tests__/visual/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/a11y/**/*.test.[jt]s?(x)',
    ],
    maxWorkers: 1, // Run visual tests sequentially
    updateSnapshot: process.env.UPDATE_SNAPSHOTS === 'true',
  },
  
  // Performance tests
  performance: {
    displayName: 'Performance Tests',
    testMatch: [
      '<rootDir>/__tests__/performance/**/*.test.[jt]s?(x)',
    ],
    testTimeout: 120000, // 2 minutes for performance tests
    maxWorkers: 2,
  },
  
  // All tests
  all: {
    displayName: 'All Tests',
    testMatch: [
      '<rootDir>/__tests__/**/*.test.[jt]s?(x)',
      '<rootDir>/__tests__/**/*.spec.[jt]s?(x)',
    ],
    maxWorkers: process.env.CI ? 4 : '50%',
  },
};

// Get test suite based on environment variable or default
const getTestSuite = () => {
  const suite = process.env.TEST_SUITE || 'all';
  return testSuites[suite] || testSuites.all;
};

// Main configuration
const config = {
  ...commonConfig,
  ...getTestSuite(),
  
  // Coverage provider
  coverageProvider: 'v8',
  
  // Test path ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/__tests__/setup/',
    '/__tests__/helpers/',
    '.*\\.playwright\\.test\\.[jt]sx?$',
  ],
  
  // Reporter configuration
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: './test-results',
        outputName: 'junit.xml',
        ancestorSeparator: ' › ',
        uniqueOutputName: 'false',
        suiteNameTemplate: '{filepath}',
        classNameTemplate: '{classname}',
        titleTemplate: '{title}',
      },
    ],
  ].filter(Boolean),
  
  // Watch plugins for better developer experience (only in watch mode)
  watchPlugins: process.argv.includes('--watch') ? [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname',
  ] : [],
  
  // Parallel execution settings - reduced for stability
  maxConcurrency: parseInt(process.env.MAX_CONCURRENCY || '3'),
  maxWorkers: process.env.MAX_WORKERS || (process.env.CI ? 2 : '25%'),
  
  // Performance optimizations and hanging prevention
  detectOpenHandles: process.env.DETECT_OPEN_HANDLES === 'true',
  forceExit: true, // Force exit to prevent hanging
  
  // Memory management
  workerIdleMemoryLimit: '500MB',
  maxWorkers: process.env.CI ? 2 : '25%', // Reduced worker count for stability
  
  // Error handling
  errorOnDeprecated: false,
};

// Export the configuration
module.exports = async () => {
  const nextJestConfig = await createJestConfig(config)();
  
  return {
    ...nextJestConfig,
    // Ensure proper timeout handling
    testTimeout: config.testTimeout,
    // Ensure proper worker configuration
    maxWorkers: config.maxWorkers,
    maxConcurrency: config.maxConcurrency,
  };
};