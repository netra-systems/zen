/**
 * ROI Calculator Type Definitions
 * Business Value: Enterprise ROI justification interfaces
 */

export interface ROICalculatorProps {
  industry: string
  onComplete?: () => void
}

export interface Metrics {
  currentMonthlySpend: number
  requestsPerMonth: number
  averageLatency: number
  modelAccuracy: number
  teamSize: number
}

export interface Savings {
  infrastructureCost: number
  operationalCost: number
  performanceGain: number
  totalMonthlySavings: number
  totalAnnualSavings: number
  paybackPeriod: number
  threeYearROI: number
}

export interface ROICalculationInput {
  current_spend: number
  request_volume: number
  average_latency: number
  industry: string
}

export interface ROIApiResponse {
  current_annual_cost: number
  optimized_annual_cost: number
  annual_savings: number
  roi_months: number
  three_year_tco_reduction: number
}

export const INDUSTRY_MULTIPLIERS: Record<string, number> = {
  'Financial Services': 1.3,
  'Healthcare': 1.25,
  'E-commerce': 1.2,
  'Manufacturing': 1.15,
  'Technology': 1.35,
  'default': 1.0
}

export const DEFAULT_METRICS: Metrics = {
  currentMonthlySpend: 50000,
  requestsPerMonth: 10000000,
  averageLatency: 250,
  modelAccuracy: 92,
  teamSize: 5
}