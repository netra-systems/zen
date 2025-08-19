const baseConfig = require('./jest.config.cjs');

// Extended configurations for new test suites
const extendedProjects = [
  {
    displayName: 'integration',
    testEnvironment: 'jest-environment-jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
    testMatch: ['<rootDir>/__tests__/integration/**/*.test.[jt]s?(x)'],
    testTimeout: 30000,
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
    transformIgnorePatterns: [
      'node_modules/(?!(react-markdown|remark-.*|rehype-.*|unified|micromark.*|mdast-.*|hast-.*|unist-.*|vfile|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|is-plain-obj|trough|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|estree-util-.*|devlop|zwitch|longest-streak|markdown-table|trim-lines|ccount|escape-string-regexp|html-void-elements|web-namespaces|estree-walker)/)',
    ],
  },
  {
    displayName: 'e2e-unit',
    testEnvironment: 'jest-environment-jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
    testMatch: ['<rootDir>/__tests__/e2e/**/*.test.[jt]s?(x)'],
    testTimeout: 60000,
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
    transformIgnorePatterns: [
      'node_modules/(?!(react-markdown|remark-.*|rehype-.*|unified|micromark.*|mdast-.*|hast-.*|unist-.*|vfile|react-syntax-highlighter|refractor|parse-entities|character-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|is-plain-obj|trough|decode-named-character-reference|character-entities-html4|character-entities-legacy|hastscript|estree-util-.*|devlop|zwitch|longest-streak|markdown-table|trim-lines|ccount|escape-string-regexp|html-void-elements|web-namespaces|estree-walker)/)',
    ],
  },
  {
    displayName: 'performance',
    testEnvironment: 'jest-environment-jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
    testMatch: ['<rootDir>/__tests__/performance/**/*.test.[jt]s?(x)'],
    testTimeout: 120000,
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
  },
  {
    displayName: 'visual',
    testEnvironment: 'jest-environment-jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
    testMatch: ['<rootDir>/__tests__/visual/**/*.test.[jt]s?(x)'],
    testTimeout: 60000,
    moduleNameMapper: {
      '^@/(.*)$': '<rootDir>/$1',
      '\\.(css|less|scss|sass)$': '<rootDir>/__mocks__/styleMock.js',
    },
  },
  {
    displayName: 'mobile',
    testEnvironment: 'jest-environment-jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
    testMatch: ['<rootDir>/__tests__/mobile/**/*.test.[jt]s?(x)'],
    testTimeout: 45000,
    moduleNameMapper: {
      '^@/(.*)$': '<rootDir>/$1',
      '\\.(css|less|scss|sass)$': '<rootDir>/__mocks__/styleMock.js',
    },
  },
];

// Function to create extended configuration
const createExtendedConfig = async () => {
  const baseJestConfig = await baseConfig();
  
  return {
    ...baseJestConfig,
    projects: [
      ...baseJestConfig.projects,
      ...extendedProjects
    ],
    coverageThreshold: {
      global: {
        branches: 80,
        functions: 85,
        lines: 85,
        statements: 85,
      },
    },
    collectCoverageFrom: [
      'components/**/*.{ts,tsx}',
      'hooks/**/*.{ts,tsx}',
      'lib/**/*.{ts,tsx}',
      'services/**/*.{ts,tsx}',
      'store/**/*.{ts,tsx}',
      '!**/*.d.ts',
      '!**/*.stories.{ts,tsx}',
      '!**/__tests__/**',
      '!**/__mocks__/**',
    ],
  };
};

module.exports = createExtendedConfig;