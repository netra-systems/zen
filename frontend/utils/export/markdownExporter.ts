/**
 * Markdown Exporter - Handles Markdown export functionality
 * Converts data to formatted markdown text
 */

import { ReportData, ExportSection } from './types';
import { downloadBlob, formatTimestamp, createFooterText } from './exportUtils';

/**
 * Export data as Markdown
 */
export function exportMarkdown(data: ReportData, filename: string): void {
  let markdown = '';
  markdown += buildTitle(data);
  markdown += buildMetadata(data);
  markdown += buildSummary(data);
  markdown += buildSections(data);
  markdown += buildRecommendations(data);
  markdown += buildMetrics(data);
  markdown += buildFooter();
  
  const blob = new Blob([markdown], { type: 'text/markdown' });
  downloadBlob(blob, `${filename}.md`);
}

/**
 * Build title section
 */
function buildTitle(data: ReportData): string {
  return data.title ? `# ${data.title}\n\n` : '';
}

/**
 * Build metadata section
 */
function buildMetadata(data: ReportData): string {
  return `*Generated: ${formatTimestamp(data.timestamp)}*\n\n`;
}

/**
 * Build summary section
 */
function buildSummary(data: ReportData): string {
  return data.summary 
    ? `## Executive Summary\n\n${data.summary}\n\n` 
    : '';
}

/**
 * Build sections content
 */
function buildSections(data: ReportData): string {
  if (!data.sections) return '';
  return data.sections
    .map(section => buildSection(section))
    .join('');
}

/**
 * Build individual section
 */
function buildSection(section: ExportSection): string {
  let content = `## ${section.title}\n\n`;
  content += buildSectionContent(section);
  return content + '\n';
}

/**
 * Build section content based on type
 */
function buildSectionContent(section: ExportSection): string {
  if (section.type === 'table' && Array.isArray(section.content)) {
    return buildTableContent(section.content);
  }
  if (typeof section.content === 'string') {
    return `${section.content}\n`;
  }
  return `\`\`\`json\n${JSON.stringify(section.content, null, 2)}\n\`\`\`\n`;
}

/**
 * Build table content in markdown format
 */
function buildTableContent(content: any[]): string {
  if (content.length === 0) return '';
  const headers = Object.keys(content[0]);
  let table = `| ${headers.join(' | ')} |\n`;
  table += `| ${headers.map(() => '---').join(' | ')} |\n`;
  content.forEach(row => {
    table += `| ${Object.values(row).join(' | ')} |\n`;
  });
  return table;
}

/**
 * Build recommendations section
 */
function buildRecommendations(data: ReportData): string {
  if (!data.recommendations?.length) return '';
  let content = `## Recommendations\n\n`;
  data.recommendations.forEach((rec: any, index: number) => {
    content += `${index + 1}. ${rec.title || rec}\n`;
    if (rec.description) {
      content += `   ${rec.description}\n`;
    }
  });
  return content + '\n';
}

/**
 * Build metrics section
 */
function buildMetrics(data: ReportData): string {
  if (!data.metrics) return '';
  let content = `## Metrics\n\n`;
  Object.entries(data.metrics).forEach(([key, value]) => {
    const valueStr = typeof value === 'object' 
      ? JSON.stringify(value) 
      : value;
    content += `- **${key}**: ${valueStr}\n`;
  });
  return content;
}

/**
 * Build footer section
 */
function buildFooter(): string {
  return `\n---\n*${createFooterText()}*`;
}