module.exports = {
  testEnvironment: 'jsdom',
  preset: undefined,
  testMatch: [
    '**/__tests__/integration/**/*.test.[jt]s?(x)'
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    '/dist/',
    '/build/'
  ],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '\\.(css|less|scss|sass)$': '<rootDir>/__mocks__/styleMock.js',
    '^.+\\.(svg|png|jpg|jpeg|gif)$': '<rootDir>/__mocks__/fileMock.js'
  },
  transform: {
    '^.+\\.(ts|tsx|js|jsx)$': ['@swc/jest', {
      jsc: {
        parser: {
          syntax: 'typescript',
          tsx: true,
          decorators: false,
          dynamicImport: true
        },
        transform: {
          react: {
            runtime: 'automatic'
          }
        }
      },
      module: {
        type: 'commonjs'
      }
    }]
  },
  transformIgnorePatterns: [
    'node_modules/(?!(uuid|nanoid|@tanstack|@radix-ui|react-markdown|remark|unified|bail|is-plain-obj|trough|vfile|unist-|mdast-|micromark|decode-named-character-reference|character-entities|property-information|hast-|estree-|periscopic|is-reference|comma-separated-tokens|markdown-|space-separated-tokens|ccount|escape-string-regexp|trim-lines|web-namespaces|hastscript|zwitch|html-void-elements|parse-entities)/)'
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  maxWorkers: 1,
  bail: true,
  testTimeout: 10000,
  silent: true
};