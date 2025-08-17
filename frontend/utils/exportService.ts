/**
 * Export Service - Backward compatibility wrapper
 * Re-exports the modular export functionality for existing imports
 */

// Re-export everything from the new modular structure
export * from './export';

// Default export for backward compatibility
export { ExportService as default } from './export/exportService';