/**
 * ChatHistorySection Component Tests - Compatibility Layer
 * 
 * This file now serves as a compatibility layer that imports all modular test components.
 * The original 1741-line file has been refactored into organized, maintainable modules
 * in the ./ChatHistorySection/ directory.
 * 
 * Test modules:
 * - basic.test.tsx: Basic rendering, display, and thread highlighting tests
 * - interaction.test.tsx: Search, delete, pagination, and conversation switching tests
 * - edge-cases.test.tsx: Edge cases, error handling, and comprehensive scenarios
 * - performance-accessibility.test.tsx: Performance optimization and accessibility tests
 * 
 * Each module is kept under 300 lines as per project requirements.
 * All original functionality is preserved including:
 * 
 * - History item rendering with timestamps and highlighting
 * - Search functionality with filtering
 * - Delete conversation with confirmation dialogs
 * - Load more pagination for large thread lists
 * - Conversation switching and navigation
 * - Edge cases handling for malformed data
 * - Performance tests for large datasets
 * - Accessibility compliance testing
 * - Comprehensive error handling
 */

// Hoist all mocks to the top for proper Jest handling
const mockUseUnifiedChatStore = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseThreadNavigation = jest.fn();

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
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

// Import all modular test suites
import './ChatHistorySection/index.test';

// The tests are now organized into focused, maintainable modules while preserving
// all original functionality and test coverage. This approach provides:
// 
// 1. Better maintainability (each file < 300 lines)
// 2. Improved organization by functionality (basic, interaction, edge cases, etc.)
// 3. Shared utilities to reduce code duplication
// 4. Full backward compatibility with existing test infrastructure
// 5. Easier debugging and focused testing of specific functionality
// 6. Better separation of concerns for different types of tests