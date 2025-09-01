// Implementation Roadmap Utils
// Module: Utility functions for roadmap functionality
// Max 300 lines, all functions ≤8 lines

import { ExportData, ExportFormat, Phase, SupportOption, RiskMitigation } from './roadmap-types'

// Create export data (≤8 lines)
export const createExportData = (
  industry: string,
  completedSteps: string[],
  phases: Phase[],
  supportOptions: SupportOption[],
  riskMitigations: RiskMitigation[]
): ExportData => {
  return {
    industry,
    completedSteps,
    phases,
    supportOptions,
    riskMitigations,
    exportDate: new Date().toISOString(),
    estimatedSavings: '$540,000/year',
    implementationCost: '$50,000 one-time'
  }
}

// Generate filename (≤8 lines)
export const generateFilename = (format: ExportFormat): string => {
  const timestamp = Date.now()
  const base = 'netra-implementation-roadmap'
  return `${base}-${timestamp}.${format}`
}

// Create blob from data (≤8 lines)
export const createDataBlob = (
  data: ExportData, 
  format: ExportFormat
): Blob => {
  const jsonString = JSON.stringify(data, null, 2)
  return new Blob([jsonString], { type: 'application/json' })
}

// Create download link (≤8 lines)
export const createDownloadLink = (blob: Blob): string => {
  return URL.createObjectURL(blob)
}

// Trigger download (≤8 lines)
export const triggerDownload = (
  url: string, 
  filename: string
): void => {
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
}

// Handle JSON export (≤8 lines)
export const handleJsonExport = (
  data: ExportData,
  filename: string
): void => {
  const blob = createDataBlob(data, 'json')
  const url = createDownloadLink(blob)
  triggerDownload(url, filename)
}

// Handle unsupported formats (≤8 lines)
export const handleUnsupportedExport = (format: ExportFormat): void => {
  const message = `Export to ${format.toUpperCase()} would be implemented with appropriate libraries`
  alert(message)
}

// Main export handler (≤8 lines)
export const handleExportData = (
  exportData: ExportData,
  format: ExportFormat,
  onExport?: () => void
): void => {
  if (format === 'json') {
    const filename = generateFilename(format)
    handleJsonExport(exportData, filename)
  } else {
    handleUnsupportedExport(format)
  }
  
  if (onExport) {
    onExport()
  }
}