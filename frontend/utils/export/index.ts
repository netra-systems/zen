/**
 * Export Module Index - Clean API for export functionality
 * Central export point for all export-related functionality
 */

// Main service class
export { ExportService } from './exportService';

// Type definitions
export type {
  ExportFormat,
  ExportOptions,
  ExportRecommendation,
  ExportSection,
  ExportSectionContent,
  ExportMetrics,
  ReportData,
  PDFLayout
} from './types';

// Utility functions
export {
  generateFilename,
  downloadBlob,
  createExportMetadata,
  formatTimestamp,
  validateExportData
} from './exportUtils';

// Individual exporters (for advanced use cases)
export { exportPDF } from './pdfExporter';
export { exportCSV } from './csvExporter';
export { exportMarkdown } from './markdownExporter';
export { 
  exportElementAsImage,
  exportMultipleElementsAsImages,
  exportElementWithOptions
} from './imageExporter';