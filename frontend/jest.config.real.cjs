const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

// Configuration for real service testing
const config = {
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.real.js'],
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
  },
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-.*|rehype-.*|unified|micromark.*|mdast-.*|hast-.*|unist-.*|vfile|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|is-plain-obj|trough|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|estree-util-.*|devlop|zwitch|longest-streak|markdown-table|trim-lines|ccount|escape-string-regexp|html-void-elements|web-namespaces|estree-walker)/)',
  ],
  testTimeout: 30000, // 30 seconds for real service tests
  testPathIgnorePatterns: [
    '/node_modules/',
    '/__tests__/setup/',
    '.*\\.playwright\\.test\\.[jt]sx?$',
  ],
  testMatch: [
    '<rootDir>/__tests__/**/*.test.[jt]s?(x)',
    '<rootDir>/__tests__/**/*.spec.[jt]s?(x)',
  ],
  globals: {
    'ts-jest': {
      tsconfig: {
        jsx: 'react-jsx',
        esModuleInterop: true,
        allowSyntheticDefaultImports: true,
      },
      isolatedModules: true,
    },
  },
  // Environment variables for real service testing
  testEnvironmentOptions: {
    env: {
      USE_REAL_SERVICES: process.env.USE_REAL_SERVICES || 'true',
      USE_DOCKER_SERVICES: process.env.USE_DOCKER_SERVICES || 'false',
      USE_REAL_LLM: process.env.USE_REAL_LLM || 'false',
      BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
      AUTH_SERVICE_URL: process.env.AUTH_SERVICE_URL || 'http://localhost:8081',
      WEBSOCKET_URL: process.env.WEBSOCKET_URL || 'ws://localhost:8000',
    },
  },
};

module.exports = createJestConfig(config);