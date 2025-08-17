/**
 * PDF Layout Utilities - Layout and page management for PDF generation
 * Handles page layout, positioning, and page breaks
 */

import { PDFLayout } from './types';

/**
 * Create PDF layout configuration
 */
export function createPDFLayout(pdf: any): PDFLayout {
  return {
    pageHeight: pdf.internal.pageSize.getHeight(),
    pageWidth: pdf.internal.pageSize.getWidth(),
    margin: 20,
    lineHeight: 10
  };
}

/**
 * Check and add new page if needed
 */
export function checkAndAddPage(
  pdf: any, 
  layout: PDFLayout, 
  yPosition: number, 
  requiredSpace: number
): number {
  if (yPosition + requiredSpace <= layout.pageHeight - layout.margin) {
    return yPosition;
  }
  pdf.addPage();
  return layout.margin;
}

/**
 * Set PDF font and color for headers
 */
export function setPDFHeaderStyle(pdf: any): void {
  pdf.setFontSize(14);
  pdf.setTextColor(16, 185, 129);
}

/**
 * Set PDF font and color for body text
 */
export function setPDFBodyStyle(pdf: any): void {
  pdf.setFontSize(11);
  pdf.setTextColor(0, 0, 0);
}

/**
 * Set PDF font and color for metadata
 */
export function setPDFMetadataStyle(pdf: any): void {
  pdf.setFontSize(10);
  pdf.setTextColor(128, 128, 128);
}

/**
 * Set PDF font and color for title
 */
export function setPDFTitleStyle(pdf: any): void {
  pdf.setFontSize(24);
  pdf.setTextColor(0, 0, 0);
}

/**
 * Set PDF font and color for footer
 */
export function setPDFFooterStyle(pdf: any): void {
  pdf.setFontSize(8);
  pdf.setTextColor(128, 128, 128);
}