const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

// Visual regression test configuration  
const config = {
  displayName: 'visual-tests',
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testMatch: ['<rootDir>/__tests__/visual/**/*.test.[jt]s?(x)'],
  testTimeout: 60000,
  maxWorkers: 1, // Visual tests need to be sequential
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '\\.(css|less|scss|sass)$': '<rootDir>/__mocks__/styleMock.js',
    'react-markdown': '<rootDir>/__mocks__/react-markdown.tsx',
  },
  transformIgnorePatterns: [
    'node_modules/(?!(react-markdown|remark-.*|rehype-.*)/)',
  ],
  // Visual test specific settings
  globals: {
    'ts-jest': {
      tsconfig: {
        jsx: 'react-jsx',
      },
    },
  },
  coverageReporters: ['text-summary'],
  collectCoverage: false, // Visual tests don't need coverage
};

module.exports = createJestConfig(config);