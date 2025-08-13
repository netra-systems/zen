/**
 * Export Service for Reports and Data
 * Supports multiple formats: PDF, JSON, CSV, PowerPoint
 */

import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import Papa from 'papaparse';
import { logger } from '@/lib/logger';

export type ExportFormat = 'pdf' | 'json' | 'csv' | 'pptx' | 'markdown';

interface ExportOptions {
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

interface ReportData {
  title?: string;
  summary?: string;
  sections?: Array<{
    title: string;
    content: any;
    type?: 'text' | 'table' | 'chart' | 'metrics';
  }>;
  recommendations?: any[];
  metrics?: Record<string, any>;
  timestamp?: number;
}

export class ExportService {
  /**
   * Export report in specified format
   */
  static async exportReport(
    data: ReportData,
    options: ExportOptions
  ): Promise<void> {
    const filename = options.filename || this.generateFilename(data.title);
    
    switch (options.format) {
      case 'pdf':
        await this.exportPDF(data, filename, options);
        break;
      case 'json':
        this.exportJSON(data, filename, options);
        break;
      case 'csv':
        this.exportCSV(data, filename);
        break;
      case 'markdown':
        this.exportMarkdown(data, filename);
        break;
      case 'pptx':
        await this.exportPowerPoint(data, filename, options);
        break;
      default:
        throw new Error(`Unsupported export format: ${options.format}`);
    }
  }

  /**
   * Export as PDF
   */
  private static async exportPDF(
    data: ReportData,
    filename: string,
    options: ExportOptions
  ): Promise<void> {
    // Dynamic import for jsPDF to avoid SSR issues
    const { default: jsPDF } = await import('jspdf');
    const pdf = new jsPDF();
    
    let yPosition = 20;
    const pageHeight = pdf.internal.pageSize.getHeight();
    const pageWidth = pdf.internal.pageSize.getWidth();
    const margin = 20;
    const lineHeight = 10;

    // Add branding if provided
    if (options.customBranding?.companyName) {
      pdf.setFontSize(10);
      pdf.setTextColor(128, 128, 128);
      pdf.text(options.customBranding.companyName, margin, yPosition);
      yPosition += lineHeight * 2;
    }

    // Title
    if (data.title) {
      pdf.setFontSize(24);
      pdf.setTextColor(0, 0, 0);
      const titleLines = pdf.splitTextToSize(data.title, pageWidth - 2 * margin);
      pdf.text(titleLines, margin, yPosition);
      yPosition += titleLines.length * 12 + 10;
    }

    // Timestamp
    pdf.setFontSize(10);
    pdf.setTextColor(128, 128, 128);
    pdf.text(
      new Date(data.timestamp || Date.now()).toLocaleString(),
      margin,
      yPosition
    );
    yPosition += lineHeight * 2;

    // Summary
    if (data.summary) {
      pdf.setFontSize(12);
      pdf.setTextColor(0, 0, 0);
      const summaryLines = pdf.splitTextToSize(data.summary, pageWidth - 2 * margin);
      
      // Check if we need a new page
      if (yPosition + summaryLines.length * 6 > pageHeight - margin) {
        pdf.addPage();
        yPosition = margin;
      }
      
      pdf.text(summaryLines, margin, yPosition);
      yPosition += summaryLines.length * 6 + 10;
    }

    // Sections
    if (data.sections) {
      for (const section of data.sections) {
        // Check for new page
        if (yPosition > pageHeight - 50) {
          pdf.addPage();
          yPosition = margin;
        }

        // Section title
        pdf.setFontSize(14);
        pdf.setTextColor(16, 185, 129); // Emerald color
        pdf.text(section.title, margin, yPosition);
        yPosition += lineHeight;

        // Section content
        pdf.setFontSize(11);
        pdf.setTextColor(0, 0, 0);
        
        if (section.type === 'table' && Array.isArray(section.content)) {
          // Simple table rendering
          (pdf as any).autoTable({
            startY: yPosition,
            head: [Object.keys(section.content[0] || {})],
            body: section.content.map(row => Object.values(row)),
            margin: { left: margin },
            theme: 'striped'
          });
          yPosition = (pdf as any).lastAutoTable.finalY + 10;
        } else {
          const contentText = typeof section.content === 'string' 
            ? section.content 
            : JSON.stringify(section.content, null, 2);
          const contentLines = pdf.splitTextToSize(contentText, pageWidth - 2 * margin);
          
          if (yPosition + contentLines.length * 6 > pageHeight - margin) {
            pdf.addPage();
            yPosition = margin;
          }
          
          pdf.text(contentLines, margin, yPosition);
          yPosition += contentLines.length * 6 + 10;
        }
      }
    }

    // Recommendations
    if (data.recommendations && data.recommendations.length > 0) {
      if (yPosition > pageHeight - 50) {
        pdf.addPage();
        yPosition = margin;
      }

      pdf.setFontSize(14);
      pdf.setTextColor(16, 185, 129);
      pdf.text('Recommendations', margin, yPosition);
      yPosition += lineHeight;

      pdf.setFontSize(11);
      pdf.setTextColor(0, 0, 0);
      
      data.recommendations.forEach((rec: any, index: number) => {
        if (yPosition > pageHeight - 30) {
          pdf.addPage();
          yPosition = margin;
        }
        
        const recText = `${index + 1}. ${rec.title || rec}`;
        const recLines = pdf.splitTextToSize(recText, pageWidth - 2 * margin - 10);
        pdf.text(recLines, margin + 5, yPosition);
        yPosition += recLines.length * 6 + 5;
      });
    }

    // Footer on last page
    pdf.setFontSize(8);
    pdf.setTextColor(128, 128, 128);
    pdf.text(
      'Generated by Netra AI Optimization Platform',
      pageWidth / 2,
      pageHeight - 10,
      { align: 'center' }
    );

    // Save PDF
    pdf.save(`${filename}.pdf`);
  }

  /**
   * Export as JSON
   */
  private static exportJSON(
    data: ReportData,
    filename: string,
    options: ExportOptions
  ): void {
    const exportData = options.includeMetadata ? {
      metadata: {
        exportedAt: new Date().toISOString(),
        version: '1.0',
        format: 'json'
      },
      ...data
    } : data;

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });
    this.downloadBlob(blob, `${filename}.json`);
  }

  /**
   * Export as CSV
   */
  private static exportCSV(data: ReportData, filename: string): void {
    // Flatten data for CSV export
    const flatData: any[] = [];
    
    // Add metrics as rows
    if (data.metrics) {
      Object.entries(data.metrics).forEach(([key, value]) => {
        flatData.push({
          Category: 'Metrics',
          Key: key,
          Value: typeof value === 'object' ? JSON.stringify(value) : value
        });
      });
    }

    // Add recommendations
    if (data.recommendations) {
      data.recommendations.forEach((rec: any, index: number) => {
        flatData.push({
          Category: 'Recommendation',
          Key: `Recommendation ${index + 1}`,
          Value: rec.title || rec
        });
      });
    }

    // Add sections
    if (data.sections) {
      data.sections.forEach(section => {
        if (Array.isArray(section.content)) {
          section.content.forEach(item => {
            flatData.push({
              Category: section.title,
              ...item
            });
          });
        } else {
          flatData.push({
            Category: 'Section',
            Key: section.title,
            Value: section.content
          });
        }
      });
    }

    const csv = Papa.unparse(flatData);
    const blob = new Blob([csv], { type: 'text/csv' });
    this.downloadBlob(blob, `${filename}.csv`);
  }

  /**
   * Export as Markdown
   */
  private static exportMarkdown(data: ReportData, filename: string): void {
    let markdown = '';

    // Title
    if (data.title) {
      markdown += `# ${data.title}\n\n`;
    }

    // Metadata
    markdown += `*Generated: ${new Date(data.timestamp || Date.now()).toLocaleString()}*\n\n`;

    // Summary
    if (data.summary) {
      markdown += `## Executive Summary\n\n${data.summary}\n\n`;
    }

    // Sections
    if (data.sections) {
      data.sections.forEach(section => {
        markdown += `## ${section.title}\n\n`;
        
        if (section.type === 'table' && Array.isArray(section.content)) {
          // Create markdown table
          if (section.content.length > 0) {
            const headers = Object.keys(section.content[0]);
            markdown += `| ${headers.join(' | ')} |\n`;
            markdown += `| ${headers.map(() => '---').join(' | ')} |\n`;
            
            section.content.forEach(row => {
              markdown += `| ${Object.values(row).join(' | ')} |\n`;
            });
          }
        } else if (typeof section.content === 'string') {
          markdown += `${section.content}\n`;
        } else {
          markdown += `\`\`\`json\n${JSON.stringify(section.content, null, 2)}\n\`\`\`\n`;
        }
        
        markdown += '\n';
      });
    }

    // Recommendations
    if (data.recommendations && data.recommendations.length > 0) {
      markdown += `## Recommendations\n\n`;
      data.recommendations.forEach((rec: any, index: number) => {
        markdown += `${index + 1}. ${rec.title || rec}\n`;
        if (rec.description) {
          markdown += `   ${rec.description}\n`;
        }
      });
      markdown += '\n';
    }

    // Metrics
    if (data.metrics) {
      markdown += `## Metrics\n\n`;
      Object.entries(data.metrics).forEach(([key, value]) => {
        markdown += `- **${key}**: ${typeof value === 'object' ? JSON.stringify(value) : value}\n`;
      });
    }

    // Footer
    markdown += '\n---\n*Generated by Netra AI Optimization Platform*';

    const blob = new Blob([markdown], { type: 'text/markdown' });
    this.downloadBlob(blob, `${filename}.md`);
  }

  /**
   * Export as PowerPoint (stub - requires additional library)
   */
  private static async exportPowerPoint(
    data: ReportData,
    filename: string,
    options: ExportOptions
  ): Promise<void> {
    // This would require a library like PptxGenJS
    logger.warn('PowerPoint export not yet implemented, falling back to JSON', {
      component: 'ExportService',
      action: 'powerpoint_export_fallback',
      metadata: { filename, format: options.format }
    });
    // For now, export as formatted JSON
    this.exportJSON(data, filename, options);
  }

  /**
   * Generate filename with timestamp
   */
  private static generateFilename(title?: string): string {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const baseTitle = title ? title.replace(/[^a-z0-9]/gi, '_').toLowerCase() : 'report';
    return `${baseTitle}_${timestamp}`;
  }

  /**
   * Download blob as file
   */
  private static downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /**
   * Export element as image
   */
  static async exportElementAsImage(
    elementId: string,
    filename?: string
  ): Promise<void> {
    const element = document.getElementById(elementId);
    if (!element) {
      throw new Error(`Element with id ${elementId} not found`);
    }

    const canvas = await html2canvas(element);
    const blob = await new Promise<Blob>((resolve) => {
      canvas.toBlob((blob) => resolve(blob!), 'image/png');
    });

    this.downloadBlob(blob, `${filename || 'export'}.png`);
  }
}