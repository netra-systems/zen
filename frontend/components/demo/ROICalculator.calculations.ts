/**
 * ROI Calculator Business Logic
 * Business Value: Core ROI computation for Enterprise justification
 */

import { demoService } from '@/services/demoService'
import { logger } from '@/lib/logger'
import { 
  Metrics, 
  Savings, 
  ROICalculationInput, 
  ROIApiResponse,
  INDUSTRY_MULTIPLIERS 
} from './ROICalculator.types'

const mapApiResponseToSavings = (data: ROIApiResponse, metrics: Metrics): Savings => {
  const annualSavingsDiff = data.current_annual_cost - data.optimized_annual_cost
  const monthlySavings = data.annual_savings / 12
  const infrastructureCost = (annualSavingsDiff / 12) * 0.7
  const operationalCost = (annualSavingsDiff / 12) * 0.2
  const performanceGain = (annualSavingsDiff / 12) * 0.1
  const threeYearROI = (data.three_year_tco_reduction / (metrics.currentMonthlySpend * 2)) * 100
  
  return {
    infrastructureCost,
    operationalCost,
    performanceGain,
    totalMonthlySavings: monthlySavings,
    totalAnnualSavings: data.annual_savings,
    paybackPeriod: data.roi_months,
    threeYearROI
  }
}

const calculateInfrastructureSavings = (metrics: Metrics, multiplier: number): number => {
  const infrastructureSavingsPercent = 0.45 + (Math.random() * 0.15)
  return metrics.currentMonthlySpend * infrastructureSavingsPercent * multiplier
}

const calculateOperationalSavings = (metrics: Metrics): number => {
  const operationalSavingsPercent = 0.25
  return (metrics.teamSize * 10000) * operationalSavingsPercent
}

const calculatePerformanceValue = (metrics: Metrics): number => {
  const latencyImprovement = 0.6 // 60% latency reduction
  return (metrics.requestsPerMonth / 1000000) * 500 * latencyImprovement
}

const calculatePaybackPeriod = (implementationCost: number, monthlySavings: number): number => {
  return implementationCost / monthlySavings
}

const calculateThreeYearROI = (annualSavings: number, implementationCost: number): number => {
  const threeYearSavings = annualSavings * 3
  return ((threeYearSavings - implementationCost) / implementationCost) * 100
}

const buildFallbackSavings = (metrics: Metrics, industry: string): Savings => {
  const multiplier = INDUSTRY_MULTIPLIERS[industry] || INDUSTRY_MULTIPLIERS.default
  const infrastructureCost = calculateInfrastructureSavings(metrics, multiplier)
  const operationalCost = calculateOperationalSavings(metrics)
  const performanceValue = calculatePerformanceValue(metrics)
  const totalMonthlySavings = infrastructureCost + operationalCost + performanceValue
  const totalAnnualSavings = totalMonthlySavings * 12
  const implementationCost = metrics.currentMonthlySpend * 2
  
  return {
    infrastructureCost,
    operationalCost,
    performanceGain: performanceValue,
    totalMonthlySavings,
    totalAnnualSavings,
    paybackPeriod: calculatePaybackPeriod(implementationCost, totalMonthlySavings),
    threeYearROI: calculateThreeYearROI(totalAnnualSavings, implementationCost)
  }
}

const buildCalculationInput = (metrics: Metrics, industry: string): ROICalculationInput => {
  return {
    current_spend: metrics.currentMonthlySpend,
    request_volume: metrics.requestsPerMonth,
    average_latency: metrics.averageLatency,
    industry: industry
  }
}

const logCalculationError = (error: Error, metrics: Metrics, industry: string): void => {
  logger.error('ROI calculation failed', error, {
    component: 'ROICalculator',
    action: 'calculate_roi_error',
    metadata: { metrics, industry }
  })
}

export const calculateROI = async (
  metrics: Metrics, 
  industry: string
): Promise<Savings> => {
  try {
    const input = buildCalculationInput(metrics, industry)
    const data = await demoService.calculateROI(input)
    return mapApiResponseToSavings(data, metrics)
  } catch (error) {
    logCalculationError(error as Error, metrics, industry)
    return buildFallbackSavings(metrics, industry)
  }
}