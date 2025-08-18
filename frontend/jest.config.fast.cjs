const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

const config = {
  // Use maximum parallelization
  maxWorkers: '50%', // Use 50% of available CPU cores
  
  // Performance settings
  cache: true,
  cacheDirectory: '<rootDir>/.jest-cache',
  collectCoverage: false,
  coverageProvider: 'v8',
  
  // Test environment
  testEnvironment: 'jest-environment-jsdom',
  
  // Faster test discovery - only look for .test files
  testMatch: [
    '**/__tests__/**/*.test.[jt]s?(x)',
  ],
  
  // Reduce timeout for faster failures
  testTimeout: 8000,
  
  // Use optimized setup
  setupFilesAfterEnv: ['<rootDir>/jest.setup.optimized.ts'],
  
  // Module mappings
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
  
  // Transform settings
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-.*|rehype-.*|unified|micromark.*|mdast-.*|hast-.*|unist-.*|vfile|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|is-plain-obj|trough|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|estree-util-.*|devlop|zwitch|longest-streak|markdown-table|trim-lines|ccount|escape-string-regexp|html-void-elements|web-namespaces|estree-walker)/)',
  ],
  
  // Fast cleanup
  clearMocks: true,
  restoreMocks: true,
  resetModules: false,
  
  // Bail on first failure for CI
  bail: 1,
  
  // Silent reporter for speed
  silent: true,
  verbose: false,
  
  // Disable watch mode plugins
  watchPlugins: [],
};

module.exports = createJestConfig(config);