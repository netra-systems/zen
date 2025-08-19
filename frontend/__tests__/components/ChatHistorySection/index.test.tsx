/**
 * ChatHistorySection Tests - Modular Index
 * 
 * This file imports and re-exports all the modular test suites to maintain compatibility
 * with the original ChatHistorySection.test.tsx structure while keeping tests organized
 * and under 300 lines per file.
 */

// Hoist all mocks to the top for proper Jest handling
const mockUseUnifiedChatStore = jest.fn();
const mockUseThreadStore = jest.fn();
const mockUseChatStore = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseThreadNavigation = jest.fn();
const mockUseAuthStore = jest.fn();

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: mockUseThreadStore
}));

jest.mock('@/store/chat', () => ({
  useChatStore: mockUseChatStore
}));

// AuthGate mock - always render children
jest.mock('@/components/auth/AuthGate', () => ({
  AuthGate: ({ children }: { children: React.ReactNode }) => children
}));

jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => React.createElement('div', props, children),
  },
  AnimatePresence: ({ children }: any) => children,
}));

// Import all test modules
import './basic.test';
import './interaction.test';
import './edge-cases.test';
import './performance-accessibility.test';

// This file serves as the main entry point for all ChatHistorySection tests.
// Each test module is imported above, which ensures all tests are included when
// this file is run by Jest.

// The original file structure is preserved by importing all the modular components,
// ensuring that existing test runners and CI/CD pipelines continue to work without
// modification while providing better organization and maintainability.