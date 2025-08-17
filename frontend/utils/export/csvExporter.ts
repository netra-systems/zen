/**
 * CSV Exporter - Handles CSV export functionality
 * Converts complex data structures to flat CSV format
 */

import Papa from 'papaparse';
import { ReportData, ExportSection, ExportMetrics, ExportRecommendation } from './types';
import { downloadBlob } from './exportUtils';

/**
 * Export data as CSV
 */
export function exportCSV(data: ReportData, filename: string): void {
  const flatData = createCSVFlatData(data);
  const csv = Papa.unparse(flatData);
  const blob = new Blob([csv], { type: 'text/csv' });
  downloadBlob(blob, `${filename}.csv`);
}

/**
 * Create flat data array for CSV export
 */
function createCSVFlatData(data: ReportData): Array<Record<string, string | number>> {
  const flatData: Array<Record<string, string | number>> = [];
  addMetricsToFlatData(flatData, data.metrics);
  addRecommendationsToFlatData(flatData, data.recommendations);
  addSectionsToFlatData(flatData, data.sections);
  return flatData;
}

/**
 * Add metrics to flat data
 */
function addMetricsToFlatData(
  flatData: Array<Record<string, string | number>>, 
  metrics?: ExportMetrics
): void {
  if (!metrics) return;
  Object.entries(metrics).forEach(([key, value]) => {
    flatData.push({
      Category: 'Metrics',
      Key: key,
      Value: typeof value === 'object' ? JSON.stringify(value) : value
    });
  });
}

/**
 * Add recommendations to flat data
 */
function addRecommendationsToFlatData(
  flatData: Array<Record<string, string | number>>, 
  recommendations?: ExportRecommendation[]
): void {
  if (!recommendations) return;
  recommendations.forEach((rec, index) => {
    flatData.push({
      Category: 'Recommendation',
      Key: `Recommendation ${index + 1}`,
      Value: rec.title
    });
  });
}

/**
 * Add sections to flat data
 */
function addSectionsToFlatData(
  flatData: Array<Record<string, string | number>>, 
  sections?: ExportSection[]
): void {
  if (!sections) return;
  sections.forEach(section => {
    processSectionForCSV(flatData, section);
  });
}

/**
 * Process individual section for CSV
 */
function processSectionForCSV(
  flatData: Array<Record<string, string | number>>, 
  section: ExportSection
): void {
  if (Array.isArray(section.content)) {
    addArrayContentToFlatData(flatData, section);
  } else {
    addSingleContentToFlatData(flatData, section);
  }
}

/**
 * Add array content to flat data
 */
function addArrayContentToFlatData(
  flatData: Array<Record<string, string | number>>, 
  section: ExportSection
): void {
  if (!Array.isArray(section.content)) return;
  section.content.forEach(item => {
    flatData.push({
      Category: section.title,
      ...item
    });
  });
}

/**
 * Add single content to flat data
 */
function addSingleContentToFlatData(
  flatData: Array<Record<string, string | number>>, 
  section: ExportSection
): void {
  flatData.push({
    Category: 'Section',
    Key: section.title,
    Value: section.content
  });
}