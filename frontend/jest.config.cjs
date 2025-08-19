const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

const config = {
  coverageProvider: 'v8',
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/__tests__/setup/',  // Ignore setup files that are not actual tests
    '.*\\.playwright\\.test\\.[jt]sx?$',  // Exclude Playwright test files
  ],
  // Default test match patterns
  testMatch: [
    '<rootDir>/__tests__/**/*.test.[jt]s?(x)',
    '<rootDir>/__tests__/**/*.spec.[jt]s?(x)',
  ],
  // Project configurations for category-based testing
  projects: [
    {
      displayName: 'components',
      testEnvironment: 'jest-environment-jsdom',
      setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
      testMatch: ['<rootDir>/__tests__/components/**/*.test.[jt]s?(x)'],
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
      displayName: 'hooks',
      testEnvironment: 'jest-environment-jsdom',
      setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
      testMatch: ['<rootDir>/__tests__/hooks/**/*.test.[jt]s?(x)'],
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
      displayName: 'store',
      testEnvironment: 'jest-environment-jsdom',
      setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
      testMatch: ['<rootDir>/__tests__/store/**/*.test.[jt]s?(x)'],
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
      displayName: 'services',
      testEnvironment: 'jest-environment-jsdom',
      setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
      testMatch: ['<rootDir>/__tests__/services/**/*.test.[jt]s?(x)'],
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
      displayName: 'lib',
      testEnvironment: 'jest-environment-jsdom',
      setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
      testMatch: ['<rootDir>/__tests__/lib/**/*.test.[jt]s?(x)'],
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
      displayName: 'utils',
      testEnvironment: 'jest-environment-jsdom',
      setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
      testMatch: ['<rootDir>/__tests__/utils/**/*.test.[jt]s?(x)'],
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
      displayName: 'imports',
      testEnvironment: 'jest-environment-jsdom',
      setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
      testMatch: ['<rootDir>/__tests__/imports/**/*.test.[jt]s?(x)'],
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
      displayName: 'a11y',
      testEnvironment: 'jest-environment-jsdom',
      setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
      testMatch: ['<rootDir>/__tests__/a11y/**/*.test.[jt]s?(x)'],
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
  ],
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
};

// Create a custom Jest configuration that properly handles TypeScript
module.exports = async () => {
  const nextJestConfig = await createJestConfig(config)();
  
  // Add transform configuration to each project
  const projectsWithTransform = nextJestConfig.projects.map(project => ({
    ...project,
    transform: {
      '^.+\\.(ts|tsx)$': ['ts-jest', {
        tsconfig: {
          jsx: 'react-jsx',
          esModuleInterop: true,
          allowSyntheticDefaultImports: true,
        },
      }],
      '^.+\\.(js|jsx)$': ['babel-jest', { presets: ['next/babel'] }],
    },
  }));
  
  return {
    ...nextJestConfig,
    projects: projectsWithTransform,
    // Override transform to properly handle TypeScript files
    transform: {
      '^.+\\.(ts|tsx)$': ['ts-jest', {
        tsconfig: {
          jsx: 'react-jsx',
          esModuleInterop: true,
          allowSyntheticDefaultImports: true,
        },
      }],
      '^.+\\.(js|jsx)$': ['babel-jest', { presets: ['next/babel'] }],
    },
    // Add exclusion for Playwright test files
    testPathIgnorePatterns: [
      ...nextJestConfig.testPathIgnorePatterns || [],
      '/node_modules/',
      '/__tests__/setup/',
      '.*\\.playwright\\.test\\.[jt]sx?$',
    ],
  };
};