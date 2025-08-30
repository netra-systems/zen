const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

// Stable configuration for problematic tests
const stableConfig = {
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  
  // Conservative timeouts and worker settings
  testTimeout: 45000, // 45 seconds - generous timeout
  maxWorkers: 1, // Single worker for maximum stability
  maxConcurrency: 1, // Run one test at a time
  
  // Aggressive cleanup settings
  forceExit: true,
  detectOpenHandles: true,
  
  // Memory management
  workerIdleMemoryLimit: '200MB',
  
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
  
  // Test path ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/__tests__/setup/',
    '/__tests__/helpers/',
    '.*\\.playwright\\.test\\.[jt]sx?$',
  ],
  
  // Minimal reporting for performance
  verbose: false,
  silent: true,
  
  // Coverage configuration - disabled for performance
  collectCoverage: false,
  
  // Cache settings - disabled to avoid issues
  cache: false,
};

// Export the configuration
module.exports = async () => {
  const nextJestConfig = await createJestConfig(stableConfig)();
  
  return {
    ...nextJestConfig,
    // Ensure our stable settings override Next.js defaults
    testTimeout: stableConfig.testTimeout,
    maxWorkers: stableConfig.maxWorkers,
    maxConcurrency: stableConfig.maxConcurrency,
    forceExit: stableConfig.forceExit,
    detectOpenHandles: stableConfig.detectOpenHandles,
    workerIdleMemoryLimit: stableConfig.workerIdleMemoryLimit,
  };
};