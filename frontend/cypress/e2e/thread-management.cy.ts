/**
 * Thread Management Test Suite Index
 * Modular thread management tests split into focused areas
 * Business Value: Growth segment - validates conversation management workflows
 * 
 * Architecture: Split 420-line monolith into 4 focused modules ≤300 lines each
 * - Thread test helpers: Common utilities and mocks
 * - Basic operations: Display, switching, creation
 * - Management operations: Search, delete, rename, export  
 * - Message operations: Pagination and loading
 */

// Import all modular thread test suites
import './thread-basic-operations.cy';
import './thread-management-operations.cy';
import './thread-message-operations.cy';

// Note: thread-test-helpers.ts contains shared utilities imported by test modules
// This architecture ensures:
// - Each module ≤300 lines
// - All functions ≤8 lines  
// - Grouped by operation type
// - Reusable test utilities
// - Maintained thread coverage
// - Follows thread patterns