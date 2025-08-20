const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

// Smoke test configuration - critical paths only
const config = {
  displayName: 'smoke-tests',
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testMatch: [
    '<rootDir>/__tests__/smoke/**/*.test.[jt]s?(x)',
    '<rootDir>/__tests__/critical/**/*.test.[jt]s?(x)',
  ],
  testTimeout: 10000,
  maxWorkers: 1,
  bail: true,
  verbose: false,
  silent: true,
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '\\.(css|less|scss|sass)$': '<rootDir>/__mocks__/styleMock.js',
    'react-markdown': '<rootDir>/__mocks__/react-markdown.tsx',
  },
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-.*|rehype-.*|micromark.*|mdast-.*|unist-.*|vfile.*|unified.*|bail|is-plain-obj|trough|zwitch)/)',
  ],
  coverageReporters: ['text-summary'],
  collectCoverage: false,
};

module.exports = createJestConfig(config);