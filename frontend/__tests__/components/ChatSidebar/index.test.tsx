/**
 * ChatSidebar Tests - Modular Index
 * 
 * This file imports and re-exports all the modular test suites to maintain compatibility
 * with the original ChatSidebar.test.tsx structure while keeping tests organized
 * and under 300 lines per file.
 */

// Import all test modules
import './setup'; // Setup utilities only
import './basic.test';
import './interaction.test';
import './edge-cases.test';

// This file serves as the main entry point for all ChatSidebar tests.
// Each test module is imported above, which ensures all tests are included when
// this file is run by Jest.

// The original file structure is preserved by importing all the modular components,
// ensuring that existing test runners and CI/CD pipelines continue to work without
// modification while providing better organization and maintainability.

export * from './setup';