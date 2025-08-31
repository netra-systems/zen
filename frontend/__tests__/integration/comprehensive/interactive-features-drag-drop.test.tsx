import './interactive-features-drag-drop-basic.test';
import './interactive-features-drag-drop-advanced.test';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
itecture - Main coordinator ≤300 lines
 * 
 * This file serves as the main entry point for drag-drop tests.
 * Actual test implementations are split into smaller modules for compliance.
 */

// Import all drag-drop test modules
import './interactive-features-drag-drop-basic.test';
import './interactive-features-drag-drop-advanced.test';

// This file serves as a coordination point for the split drag-drop test modules
// Tests are automatically executed when these imports are processed