/**
 * ROI Calculator Utility Functions
 * Business Value: Enterprise data export and formatting utilities
 */

import { Metrics, Savings } from './ROICalculator.types'

export const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}

const createReportData = (industry: string, metrics: Metrics, savings: Savings | null) => {
  return {
    industry,
    currentMetrics: metrics,
    projectedSavings: savings,
    timestamp: new Date().toISOString()
  }
}

const createDownloadBlob = (data: object): Blob => {
  return new Blob([JSON.stringify(data, null, 2)], { 
    type: 'application/json' 
  })
}

const triggerDownload = (blob: Blob): void => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `netra-roi-report-${Date.now()}.json`
  a.click()
}

export const exportReport = (
  industry: string, 
  metrics: Metrics, 
  savings: Savings | null
): void => {
  const report = createReportData(industry, metrics, savings)
  const blob = createDownloadBlob(report)
  triggerDownload(blob)
}