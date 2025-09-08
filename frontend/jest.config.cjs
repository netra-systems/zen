const nextJest = require('next/jest.js');

const createJestConfig = nextJest({
  dir: './',
});

// Common configuration shared across all projects
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
};

// Helper function to create project configurations
const createProject = (displayName, testMatch, options = {}) => ({
  displayName,
  testMatch,
  ...commonConfig,
  ...options,
});

const config = {
  coverageProvider: 'v8',
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/__tests__/setup/',
    '.*\\.playwright\\.test\\.[jt]sx?$',
  ],
  testMatch: [
    '<rootDir>/__tests__/**/*.test.[jt]s?(x)',
    '<rootDir>/__tests__/**/*.spec.[jt]s?(x)',
  ],
  // Project configurations for category-based testing
  projects: [
    // Core test suites
    createProject('components', ['<rootDir>/__tests__/components/**/*.test.[jt]s?(x)']),
    createProject('hooks', ['<rootDir>/__tests__/hooks/**/*.test.[jt]s?(x)']),
    createProject('store', ['<rootDir>/__tests__/store/**/*.test.[jt]s?(x)']),
    createProject('services', ['<rootDir>/__tests__/services/**/*.test.[jt]s?(x)']),
    createProject('lib', ['<rootDir>/__tests__/lib/**/*.test.[jt]s?(x)']),
    createProject('utils', ['<rootDir>/__tests__/utils/**/*.test.[jt]s?(x)']),
    createProject('auth', ['<rootDir>/__tests__/auth/**/*.test.[jt]s?(x)']),
    createProject('chat', ['<rootDir>/__tests__/chat/**/*.test.[jt]s?(x)']),
    createProject('agents', ['<rootDir>/__tests__/agents/**/*.test.[jt]s?(x)']),
    
    // Integration and specialized tests
    createProject('integration', ['<rootDir>/__tests__/integration/**/*.test.[jt]s?(x)']),
    createProject('critical', ['<rootDir>/__tests__/critical/**/*.test.[jt]s?(x)']),
    createProject('regression', ['<rootDir>/__tests__/regression/**/*.test.[jt]s?(x)']),
    createProject('bugs', ['<rootDir>/__tests__/bugs/**/*.test.[jt]s?(x)']),
    createProject('providers', ['<rootDir>/__tests__/providers/**/*.test.[jt]s?(x)']),
    createProject('websocket', ['<rootDir>/__tests__/websocket/**/*.test.[jt]s?(x)']),
    createProject('bug_reproduction', ['<rootDir>/__tests__/bug_reproduction/**/*.test.[jt]s?(x)']),
    createProject('unit', ['<rootDir>/__tests__/unit/**/*.test.[jt]s?(x)']),
    createProject('a11y', ['<rootDir>/__tests__/a11y/**/*.test.[jt]s?(x)']),
    
    // Platform-specific tests
    createProject('mobile', ['<rootDir>/__tests__/mobile/**/*.test.[jt]s?(x)']),
    createProject('visual', ['<rootDir>/__tests__/visual/**/*.test.[jt]s?(x)']),
    createProject('cross-browser', ['<rootDir>/__tests__/cross-browser/**/*.test.[jt]s?(x)']),
    createProject('performance', ['<rootDir>/__tests__/performance/**/*.test.[jt]s?(x)']),
    createProject('staging', ['<rootDir>/__tests__/staging/**/*.test.[jt]s?(x)']),
    
    // System and infrastructure tests
    createProject('system', ['<rootDir>/__tests__/system/**/*.test.[jt]s?(x)']),
    createProject('startup', ['<rootDir>/__tests__/startup/**/*.test.[jt]s?(x)']),
    createProject('types', ['<rootDir>/__tests__/types/**/*.test.[jt]s?(x)']),
    createProject('shared', ['<rootDir>/__tests__/shared/**/*.test.[jt]s?(x)']),
    
    // Special configurations
    createProject('imports', ['<rootDir>/__tests__/imports/**/*.test.[jt]s?(x)'], { 
      maxWorkers: 1 // Run sequentially to avoid import conflicts
    }),
    createProject('e2e', ['<rootDir>/__tests__/e2e/**/*.test.[jt]s?(x)'], { 
      testPathIgnorePatterns: ['.*\\.playwright\\.test\\.[jt]sx?$'] // Exclude Playwright
    }),
  ],
  ...commonConfig,
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
  
  // Add transform to each project
  const projectsWithTransform = nextJestConfig.projects.map(project => ({
    ...project,
    transform,
  }));
  
  return {
    ...nextJestConfig,
    projects: projectsWithTransform,
    transform,
    testPathIgnorePatterns: [
      ...nextJestConfig.testPathIgnorePatterns || [],
      '/node_modules/',
      '/__tests__/setup/',
      '.*\\.playwright\\.test\\.[jt]sx?$',
    ],
  };
};