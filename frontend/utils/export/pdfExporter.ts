/**
 * PDF Exporter - Handles PDF export functionality
 * Complex PDF generation with layout management
 */

import { ReportData, ExportOptions, ExportSection, ExportRecommendation } from './types';
import { formatTimestamp, createFooterText } from './exportUtils';
import { 
  createPDFLayout, 
  checkAndAddPage, 
  setPDFHeaderStyle, 
  setPDFBodyStyle, 
  setPDFMetadataStyle, 
  setPDFTitleStyle, 
  setPDFFooterStyle 
} from './pdfLayout';

/**
 * Export data as PDF
 */
export async function exportPDF(
  data: ReportData,
  filename: string,
  options: ExportOptions
): Promise<void> {
  const pdf = await initializePDF();
  const layout = createPDFLayout(pdf);
  let yPosition = 20;
  
  yPosition = addPDFBranding(pdf, layout, options, yPosition);
  yPosition = addPDFTitle(pdf, layout, data, yPosition);
  yPosition = addPDFTimestamp(pdf, layout, data, yPosition);
  yPosition = addPDFSummary(pdf, layout, data, yPosition);
  yPosition = addPDFSections(pdf, layout, data, yPosition);
  yPosition = addPDFRecommendations(pdf, layout, data, yPosition);
  addPDFFooter(pdf, layout);
  
  pdf.save(`${filename}.pdf`);
}

/**
 * Initialize PDF instance
 */
async function initializePDF(): Promise<any> {
  const { default: jsPDF } = await import('jspdf');
  return new jsPDF();
}

/**
 * Add PDF branding section
 */
function addPDFBranding(
  pdf: any, 
  layout: any, 
  options: ExportOptions, 
  yPosition: number
): number {
  if (!options.customBranding?.companyName) return yPosition;
  setPDFMetadataStyle(pdf);
  pdf.text(options.customBranding.companyName, layout.margin, yPosition);
  return yPosition + layout.lineHeight * 2;
}

/**
 * Add PDF title section
 */
function addPDFTitle(pdf: any, layout: any, data: ReportData, yPosition: number): number {
  if (!data.title) return yPosition;
  setPDFTitleStyle(pdf);
  const titleLines = pdf.splitTextToSize(data.title, layout.pageWidth - 2 * layout.margin);
  pdf.text(titleLines, layout.margin, yPosition);
  return yPosition + titleLines.length * 12 + 10;
}

/**
 * Add PDF timestamp section
 */
function addPDFTimestamp(pdf: any, layout: any, data: ReportData, yPosition: number): number {
  setPDFMetadataStyle(pdf);
  pdf.text(formatTimestamp(data.timestamp), layout.margin, yPosition);
  return yPosition + layout.lineHeight * 2;
}

/**
 * Add PDF summary section
 */
function addPDFSummary(pdf: any, layout: any, data: ReportData, yPosition: number): number {
  if (!data.summary) return yPosition;
  yPosition = checkAndAddPage(pdf, layout, yPosition, 50);
  setPDFBodyStyle(pdf);
  const summaryLines = pdf.splitTextToSize(data.summary, layout.pageWidth - 2 * layout.margin);
  pdf.text(summaryLines, layout.margin, yPosition);
  return yPosition + summaryLines.length * 6 + 10;
}

/**
 * Add PDF sections
 */
function addPDFSections(pdf: any, layout: any, data: ReportData, yPosition: number): number {
  if (!data.sections) return yPosition;
  for (const section of data.sections) {
    yPosition = addPDFSection(pdf, layout, section, yPosition);
  }
  return yPosition;
}

/**
 * Add single PDF section
 */
function addPDFSection(pdf: any, layout: any, section: ExportSection, yPosition: number): number {
  yPosition = checkAndAddPage(pdf, layout, yPosition, 50);
  yPosition = addSectionTitle(pdf, layout, section.title, yPosition);
  return addSectionContent(pdf, layout, section, yPosition);
}

/**
 * Add section title
 */
function addSectionTitle(pdf: any, layout: any, title: string, yPosition: number): number {
  setPDFHeaderStyle(pdf);
  pdf.text(title, layout.margin, yPosition);
  return yPosition + layout.lineHeight;
}

/**
 * Add section content
 */
function addSectionContent(pdf: any, layout: any, section: ExportSection, yPosition: number): number {
  setPDFBodyStyle(pdf);
  if (section.type === 'table' && Array.isArray(section.content)) {
    return addTableContent(pdf, layout, section.content, yPosition);
  }
  return addTextContent(pdf, layout, section.content, yPosition);
}

/**
 * Add table content to PDF
 */
function addTableContent(pdf: any, layout: any, content: any[], yPosition: number): number {
  (pdf as any).autoTable({
    startY: yPosition,
    head: [Object.keys(content[0] || {})],
    body: content.map(row => Object.values(row)),
    margin: { left: layout.margin },
    theme: 'striped'
  });
  return (pdf as any).lastAutoTable.finalY + 10;
}

/**
 * Add text content to PDF
 */
function addTextContent(pdf: any, layout: any, content: any, yPosition: number): number {
  const contentText = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
  const contentLines = pdf.splitTextToSize(contentText, layout.pageWidth - 2 * layout.margin);
  yPosition = checkAndAddPage(pdf, layout, yPosition, contentLines.length * 6);
  pdf.text(contentLines, layout.margin, yPosition);
  return yPosition + contentLines.length * 6 + 10;
}

/**
 * Add PDF recommendations
 */
function addPDFRecommendations(pdf: any, layout: any, data: ReportData, yPosition: number): number {
  if (!data.recommendations?.length) return yPosition;
  yPosition = checkAndAddPage(pdf, layout, yPosition, 50);
  yPosition = addRecommendationsHeader(pdf, layout, yPosition);
  return addRecommendationsList(pdf, layout, data.recommendations, yPosition);
}

/**
 * Add recommendations header
 */
function addRecommendationsHeader(pdf: any, layout: any, yPosition: number): number {
  setPDFHeaderStyle(pdf);
  pdf.text('Recommendations', layout.margin, yPosition);
  return yPosition + layout.lineHeight;
}

/**
 * Add recommendations list
 */
function addRecommendationsList(
  pdf: any, 
  layout: any, 
  recommendations: ExportRecommendation[], 
  yPosition: number
): number {
  setPDFBodyStyle(pdf);
  recommendations.forEach((rec, index) => {
    yPosition = checkAndAddPage(pdf, layout, yPosition, 30);
    yPosition = addSingleRecommendation(pdf, layout, rec, index, yPosition);
  });
  return yPosition;
}

/**
 * Add single recommendation
 */
function addSingleRecommendation(
  pdf: any, 
  layout: any, 
  rec: ExportRecommendation, 
  index: number, 
  yPosition: number
): number {
  const recText = `${index + 1}. ${rec.title}`;
  const recLines = pdf.splitTextToSize(recText, layout.pageWidth - 2 * layout.margin - 10);
  pdf.text(recLines, layout.margin + 5, yPosition);
  return yPosition + recLines.length * 6 + 5;
}

/**
 * Add PDF footer
 */
function addPDFFooter(pdf: any, layout: any): void {
  setPDFFooterStyle(pdf);
  pdf.text(
    createFooterText(),
    layout.pageWidth / 2,
    layout.pageHeight - 10,
    { align: 'center' }
  );
}