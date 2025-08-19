/**
 * MainChat Loading States - Coordinated Test Suite
 * Coordinates focused test modules for comprehensive coverage
 * 
 * @compliance testing.xml - Component integration testing
 * @compliance conventions.xml - Under 300 lines, 8 lines per function
 * @prevents websocket-loading-state-transitions regression
 */

// Import focused test modules
import './MainChat.loading.basic.test';
import './MainChat.loading.transitions.test';

/**
 * This file coordinates the MainChat loading state tests
 * split across focused modules to maintain the 300-line limit.
 * 
 * Test Coverage:
 * - Basic loading states (MainChat.loading.basic.test.tsx)
 * - State transitions (MainChat.loading.transitions.test.tsx)
 * 
 * All modules use real MainChat component and only mock:
 * - Hook dependencies (useLoadingState, useWebSocket, etc.)
 * - External services (debug-logger)
 * - Store state
 * 
 * NO UI component mocks - testing real functionality
 */