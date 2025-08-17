/**
 * Export Service Types and Interfaces
 * Single source of truth for all export-related types
 */

export type ExportFormat = 'pdf' | 'json' | 'csv' | 'pptx' | 'markdown';

export interface ExportOptions {
  format: ExportFormat;
  filename?: string;
  includeMetadata?: boolean;
  includeCharts?: boolean;
  customBranding?: {
    logo?: string;
    companyName?: string;
    primaryColor?: string;
  };
}

export interface ExportRecommendation {
  id: string;
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  category: string;
  priority?: number;
}

export interface ExportSectionContent {
  text?: string;
  data?: Record<string, unknown>;
  rows?: Array<Record<string, unknown>>;
  value?: number | string;
}

export interface ExportSection {
  title: string;
  content: ExportSectionContent | string | Array<Record<string, unknown>>;
  type?: 'text' | 'table' | 'chart' | 'metrics';
}

export interface ExportMetrics {
  [key: string]: string | number | boolean;
}

export interface ReportData {
  title?: string;
  summary?: string;
  sections?: ExportSection[];
  recommendations?: ExportRecommendation[];
  metrics?: ExportMetrics;
  timestamp?: number;
}

export interface PDFLayout {
  pageHeight: number;
  pageWidth: number;
  margin: number;
  lineHeight: number;
}