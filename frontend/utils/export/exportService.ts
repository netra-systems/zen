/**
 * Export Service - Main orchestrator for all export operations
 * Coordinates between different export modules
 */

import { logger } from '@/lib/logger';
import { ReportData, ExportOptions, ExportFormat } from './types';
import { generateFilename, downloadBlob, createExportMetadata } from './exportUtils';
import { exportPDF } from './pdfExporter';
import { exportCSV } from './csvExporter';
import { exportMarkdown } from './markdownExporter';
import { exportElementAsImage } from './imageExporter';

export class ExportService {
  /**
   * Export report in specified format
   */
  static async exportReport(
    data: ReportData,
    options: ExportOptions
  ): Promise<void> {
    const filename = options.filename || generateFilename(data.title);
    
    try {
      await routeExportByFormat(data, options, filename);
    } catch (error) {
      logger.error('Export failed', {
        component: 'ExportService',
        action: 'export_report',
        error: error instanceof Error ? error.message : 'Unknown error',
        metadata: { format: options.format, filename }
      });
      throw error;
    }
  }

  /**
   * Export element as image (static method for backward compatibility)
   */
  static async exportElementAsImage(
    elementId: string,
    filename?: string
  ): Promise<void> {
    return exportElementAsImage(elementId, filename);
  }

  /**
   * Get supported export formats
   */
  static getSupportedFormats(): ExportFormat[] {
    return ['pdf', 'json', 'csv', 'markdown', 'pptx'];
  }

  /**
   * Validate export options
   */
  static validateExportOptions(options: ExportOptions): boolean {
    return this.getSupportedFormats().includes(options.format);
  }
}

/**
 * Route export to appropriate module based on format
 */
async function routeExportByFormat(
  data: ReportData,
  options: ExportOptions,
  filename: string
): Promise<void> {
  switch (options.format) {
    case 'pdf':
      await exportPDF(data, filename, options);
      break;
    case 'json':
      exportJSON(data, filename, options);
      break;
    case 'csv':
      exportCSV(data, filename);
      break;
    case 'markdown':
      exportMarkdown(data, filename);
      break;
    case 'pptx':
      await exportPowerPoint(data, filename, options);
      break;
    default:
      throw new Error(`Unsupported export format: ${options.format}`);
  }
}

/**
 * Export as JSON
 */
function exportJSON(
  data: ReportData,
  filename: string,
  options: ExportOptions
): void {
  const exportData = options.includeMetadata ? {
    metadata: createExportMetadata(options.format),
    ...data
  } : data;

  const blob = new Blob([JSON.stringify(exportData, null, 2)], {
    type: 'application/json'
  });
  downloadBlob(blob, `${filename}.json`);
}

/**
 * Export as PowerPoint (placeholder implementation)
 */
async function exportPowerPoint(
  data: ReportData,
  filename: string,
  options: ExportOptions
): Promise<void> {
  logger.warn('PowerPoint export not yet implemented, falling back to JSON', {
    component: 'ExportService',
    action: 'powerpoint_export_fallback',
    metadata: { filename, format: options.format }
  });
  // For now, export as formatted JSON
  exportJSON(data, filename, options);
}

// Re-export types and utilities for convenience
export * from './types';
export * from './exportUtils';
export { exportElementAsImage } from './imageExporter';