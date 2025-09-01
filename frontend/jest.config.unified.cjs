const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

// Common configuration shared across all test runs
const commonConfig = {
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
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
    'remark-gfm': '<rootDir>/__mocks__/remark-gfm.js',
    'remark-math': '<rootDir>/__mocks__/remark-math.js',
    'rehype-katex': '<rootDir>/__mocks__/rehype-katex.js',
  },
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-.*|rehype-.*|unified|micromark.*|mdast-.*|hast-.*|unist-.*|vfile|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|is-plain-obj|trough|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|estree-util-.*|devlop|zwitch|longest-streak|markdown-table|trim-lines|ccount|escape-string-regexp|html-void-elements|web-namespaces|estree-walker)/)',
  ],
  // Increase timeout for integration tests
  testTimeout: process.env.JEST_TIMEOUT ? parseInt(process.env.JEST_TIMEOUT) : 10000,
  // Control parallelization
  maxWorkers: process.env.MAX_WORKERS === '1' ? 1 : process.env.MAX_WORKERS === 'auto' ? '50%' : 4,
  // Bail on first failure if requested
  bail: process.env.BAIL === 'true' ? 1 : 0,
  // Update snapshots if requested
  updateSnapshot: process.env.UPDATE_SNAPSHOTS === 'true',
};

// Determine test suite based on environment
const getTestSuite = () => {
  const suite = process.env.TEST_SUITE;
  
  switch (suite) {
    case 'unit':
      return [
        '<rootDir>/__tests__/components/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/hooks/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/store/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/services/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/lib/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/utils/**/*.test.[jt]s?(x)',
      ];
    case 'integration':
      return ['<rootDir>/__tests__/integration/**/*.test.[jt]s?(x)'];
    case 'critical':
      return ['<rootDir>/__tests__/critical/**/*.test.[jt]s?(x)'];
    case 'chat':
      return ['<rootDir>/__tests__/chat/**/*.test.[jt]s?(x)'];
    case 'auth':
      return ['<rootDir>/__tests__/auth/**/*.test.[jt]s?(x)'];
    case 'visual':
      return ['<rootDir>/__tests__/visual/**/*.test.[jt]s?(x)'];
    default:
      // Run all tests by default
      return [
        '<rootDir>/__tests__/**/*.test.[jt]s?(x)',
        '<rootDir>/__tests__/**/*.spec.[jt]s?(x)',
      ];
  }
};

const config = {
  ...commonConfig,
  coverageProvider: 'v8',
  testPathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    '/__tests__/setup/',
    '.*\\.playwright\\.test\\.[jt]sx?$',
  ],
  testMatch: getTestSuite(),
  // Module resolution order to prevent Next.js build conflicts
  moduleDirectories: ['node_modules', '<rootDir>'],
  // Clear module cache between tests to avoid conflicts
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true,
};

// Create a custom Jest configuration that properly handles TypeScript
module.exports = async () => {
  const nextJestConfig = await createJestConfig(config)();
  
  // Transform configuration for TypeScript
  const transform = {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: {
        jsx: 'react-jsx',
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
      },
      useESM: false
    }],
    '^.+\\.(js|jsx)$': ['babel-jest', { presets: ['next/babel'] }],
  };
  
  return {
    ...nextJestConfig,
    transform,
    testPathIgnorePatterns: [
      ...nextJestConfig.testPathIgnorePatterns || [],
      '/node_modules/',
      '/.next/',
      '/__tests__/setup/',
      '.*\\.playwright\\.test\\.[jt]sx?$',
    ],
  };
};