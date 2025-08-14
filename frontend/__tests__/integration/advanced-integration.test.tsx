/**
 * Advanced Frontend Integration Tests - Compatibility Layer
 * 
 * This file now serves as a compatibility layer that imports all modular test components.
 * The original 1790-line file has been refactored into organized, maintainable modules
 * in the ./advanced-integration/ directory.
 * 
 * Test modules:
 * - setup.tsx: Shared utilities and test setup
 * - theme-preferences.test.tsx: Theme synchronization tests
 * - form-validation.test.tsx: Complex form validation tests  
 * - collaborative-features.test.tsx: Real-time collaboration tests
 * - offline-navigation.test.tsx: Offline mode and navigation tests
 * - search-ui-interactions.test.tsx: Search, drag/drop, infinite scroll, animation tests
 * - error-handling-edge-cases.test.tsx: Error boundaries, memory, i18n, WebSocket resilience
 * - end-to-end-journey.test.tsx: Complete user workflow tests
 * 
 * Each module is kept under 300 lines as per project requirements.
 * All original functionality is preserved.
 */

// Import all modular test suites
import './advanced-integration/index.test';

// The tests are now organized into focused, maintainable modules while preserving
// all original functionality and test coverage. This approach provides:
// 
// 1. Better maintainability (each file < 300 lines)
// 2. Improved organization by feature/concern
// 3. Shared utilities to reduce duplication
// 4. Full backward compatibility
// 5. Easier debugging and focused testing