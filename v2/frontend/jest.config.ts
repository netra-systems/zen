import type { Config } from 'jest';
import nextJest from 'next/jest.js';

const createJestConfig = nextJest({
  dir: './',
});

const config: Config = {
  coverageProvider: 'v8',
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/components/(.*)$': '<rootDir>/app/components/$1',
    '^@/contexts/(.*)$': '<rootDir>/app/contexts/$1',
    '^@/hooks/(.*)$': '<rootDir>/app/hooks/$1',
    '^@/lib/(.*)$': '<rootDir>/app/lib/$1',
    '^@/mocks/(.*)$': '<rootDir>/mocks/$1',
    '^@/providers/(.*)$': '<rootDir>/app/providers/$1',
    '^@/services/(.*)$': '<rootDir>/app/services/$1',
    '^@/store/(.*)$': '<rootDir>/app/store/$1',
    '^@/types/(.*)$': '<rootDir>/app/types/$1',
    '^@/(.*)$': '<rootDir>/$1',
  },
};

export default createJestConfig(config);