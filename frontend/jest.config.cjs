const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

const config = {
  coverageProvider: 'v8',
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
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
    'node_modules/(?!(react-markdown|remark-gfm|remark-math|rehype-katex|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|hast-util-whitespace|space-separated-tokens|comma-separated-tokens|vfile|unist-|unified|bail|is-plain-obj|trough|micromark|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|hast-util-parse-selector|mdast-util-)/)',
  ],
};

module.exports = createJestConfig(config);