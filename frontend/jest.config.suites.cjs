const nextJest = require('next/jest.js');
const os = require('os');

const createJestConfig = nextJest({
  dir: './',
});

// Calculate optimal worker count based on CPU cores
const cpuCount = os.cpus().length;
const optimalWorkers = Math.max(1, Math.floor(cpuCount * 0.75));

const baseConfig = {
  cache: true,
  cacheDirectory: '<rootDir>/.jest-cache',
  collectCoverage: false,
  coverageProvider: 'v8',
  testEnvironment: 'jest-environment-jsdom',
  testEnvironmentOptions: {
    resources: 'usable',
    runScripts: 'dangerously',
    pretendToBeVisual: false,
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.optimized.ts'],
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
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-.*|rehype-.*|unified|micromark.*|mdast-.*|hast-.*|unist-.*|vfile|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|is-plain-obj|trough|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|estree-util-.*|devlop|zwitch|longest-streak|markdown-table|trim-lines|ccount|escape-string-regexp|html-void-elements|web-namespaces|estree-walker)/)',
  ],
  clearMocks: true,
  restoreMocks: true,
  resetModules: false,
  watchPlugins: [],
  testTimeout: 10000,
};

const config = async () => {
  const nextJestConfig = await createJestConfig(baseConfig)();
  
  // Extract only the necessary fields for each project
  const projectBase = {
    testEnvironment: nextJestConfig.testEnvironment,
    testEnvironmentOptions: nextJestConfig.testEnvironmentOptions,
    setupFilesAfterEnv: nextJestConfig.setupFilesAfterEnv,
    moduleNameMapper: nextJestConfig.moduleNameMapper,
    transform: nextJestConfig.transform,
    transformIgnorePatterns: nextJestConfig.transformIgnorePatterns,
    clearMocks: nextJestConfig.clearMocks,
    restoreMocks: nextJestConfig.restoreMocks,
    resetModules: nextJestConfig.resetModules,
  };
  
  return {
    ...nextJestConfig,
    projects: [
    // Components Unit Tests - Fast
    {
      ...projectBase,
      displayName: 'components',
      testMatch: [
        '**/__tests__/components/**/!(*.integration|*.e2e).test.[jt]s?(x)',
      ],
      maxWorkers: optimalWorkers,
      testTimeout: 5000,
    },
    
    // Chat Components Suite
    {
      ...projectBase,
      displayName: 'chat',
      testMatch: [
        '**/__tests__/components/chat/**/*.test.[jt]s?(x)',
        '**/__tests__/chat/**/*.test.[jt]s?(x)',
      ],
      maxWorkers: Math.max(1, Math.floor(optimalWorkers * 0.8)),
      testTimeout: 8000,
    },
    
    // Hooks Unit Tests
    {
      ...projectBase,
      displayName: 'hooks',
      testMatch: [
        '**/__tests__/hooks/**/*.test.[jt]s?(x)',
      ],
      maxWorkers: Math.max(1, Math.floor(optimalWorkers * 0.6)),
      testTimeout: 5000,
    },
    
    // Auth Tests
    {
      ...projectBase,
      displayName: 'auth',
      testMatch: [
        '**/__tests__/auth/**/*.test.[jt]s?(x)',
      ],
      maxWorkers: 2,
      testTimeout: 8000,
    },
    
    // Integration Tests - Basic
    {
      ...projectBase,
      displayName: 'integration-basic',
      testMatch: [
        '**/__tests__/integration/basic-*.test.[jt]s?(x)',
        '**/__tests__/integration/auth-*.test.[jt]s?(x)',
        '**/__tests__/integration/infrastructure*.test.[jt]s?(x)',
        '**/__tests__/integration/security-*.test.[jt]s?(x)',
        '**/__tests__/integration/collaboration-*.test.[jt]s?(x)',
      ],
      maxWorkers: Math.max(1, Math.floor(optimalWorkers * 0.5)),
      testTimeout: 15000,
    },
    
    // Integration Tests - Advanced
    {
      ...projectBase,
      displayName: 'integration-advanced',
      testMatch: [
        '**/__tests__/integration/advanced-integration/**/*.test.[jt]s?(x)',
        '**/__tests__/integration/advanced-*.test.[jt]s?(x)',
      ],
      maxWorkers: Math.max(1, Math.floor(optimalWorkers * 0.4)),
      testTimeout: 20000,
    },
    
    // Integration Tests - Comprehensive
    {
      ...projectBase,
      displayName: 'integration-comprehensive',
      testMatch: [
        '**/__tests__/integration/comprehensive/**/*.test.[jt]s?(x)',
        '**/__tests__/integration/comprehensive-*.test.[jt]s?(x)',
      ],
      maxWorkers: Math.max(1, Math.floor(optimalWorkers * 0.3)),
      testTimeout: 25000,
    },
    
    // Integration Tests - Critical
    {
      ...projectBase,
      displayName: 'integration-critical',
      testMatch: [
        '**/__tests__/integration/critical/**/*.test.[jt]s?(x)',
      ],
      maxWorkers: Math.max(1, Math.floor(optimalWorkers * 0.3)),
      testTimeout: 20000,
    },
    
    // System Tests
    {
      ...projectBase,
      displayName: 'system',
      testMatch: [
        '**/__tests__/system/**/*.test.[jt]s?(x)',
        '**/__tests__/integration/system-*.test.[jt]s?(x)',
      ],
      maxWorkers: 2,
      testTimeout: 15000,
    },
    
    // Import Tests - Sequential
    {
      ...projectBase,
      displayName: 'imports',
      testMatch: [
        '**/__tests__/imports/**/*.test.[jt]s?(x)',
      ],
      maxWorkers: 1,
      testTimeout: 5000,
    },
    
    // Unified/Core Tests
    {
      ...projectBase,
      displayName: 'core',
      testMatch: [
        '**/__tests__/unified-*.test.[jt]s?(x)',
      ],
      maxWorkers: 2,
      testTimeout: 10000,
    },
  ],
  
  // Global reporters
  reporters: [
    'default',
    ['<rootDir>/jest-suite-reporter.js', { 
      outputDirectory: '<rootDir>/test-results',
      outputName: 'suite-results.json'
    }]
  ],
  };
};

module.exports = config;