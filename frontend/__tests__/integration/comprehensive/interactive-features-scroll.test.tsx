import './interactive-features-scroll-basic.test';
import './interactive-features-scroll-advanced.test';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
tecture - Main coordinator ≤300 lines
 * 
 * This file serves as the main entry point for scroll tests.
 * Actual test implementations are split into smaller modules for compliance.
 */

// Import all scroll test modules
import './interactive-features-scroll-basic.test';
import './interactive-features-scroll-advanced.test';

// This file serves as a coordination point for the split scroll test modules
// Tests are automatically executed when these imports are processed