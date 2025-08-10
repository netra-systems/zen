'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Calculator, 
  ArrowRight,
  Download,
  Info,
  CheckCircle2
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ROICalculatorProps {
  industry: string
  onComplete?: () => void
}

interface Metrics {
  currentMonthlySpend: number
  requestsPerMonth: number
  averageLatency: number
  modelAccuracy: number
  teamSize: number
}

interface Savings {
  infrastructureCost: number
  operationalCost: number
  performanceGain: number
  totalMonthlySavings: number
  totalAnnualSavings: number
  paybackPeriod: number
  threeYearROI: number
}

export default function ROICalculator({ industry, onComplete }: ROICalculatorProps) {
  const [metrics, setMetrics] = useState<Metrics>({
    currentMonthlySpend: 50000,
    requestsPerMonth: 10000000,
    averageLatency: 250,
    modelAccuracy: 92,
    teamSize: 5
  })

  const [savings, setSavings] = useState<Savings | null>(null)
  const [calculated, setCalculated] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const industryMultipliers: Record<string, number> = {
    'Financial Services': 1.3,
    'Healthcare': 1.25,
    'E-commerce': 1.2,
    'Manufacturing': 1.15,
    'Technology': 1.35,
    'default': 1.0
  }

  const calculateROI = async () => {
    setIsLoading(true)
    
    try {
      // Try to call the backend API first
      const response = await fetch('/api/demo/roi/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_spend: metrics.currentMonthlySpend,
          request_volume: metrics.requestsPerMonth,
          average_latency: metrics.averageLatency,
          industry: industry
        })
      })

      if (response.ok) {
        const data = await response.json()
        
        // Map API response to our Savings interface
        setSavings({
          infrastructureCost: (data.current_annual_cost - data.optimized_annual_cost) / 12 * 0.7,
          operationalCost: (data.current_annual_cost - data.optimized_annual_cost) / 12 * 0.2,
          performanceGain: (data.current_annual_cost - data.optimized_annual_cost) / 12 * 0.1,
          totalMonthlySavings: data.annual_savings / 12,
          totalAnnualSavings: data.annual_savings,
          paybackPeriod: data.roi_months,
          threeYearROI: (data.three_year_tco_reduction / (metrics.currentMonthlySpend * 2)) * 100
        })
      } else {
        // Fallback to local calculation if API fails
        const multiplier = industryMultipliers[industry] || industryMultipliers.default
        
        // Calculate infrastructure savings (40-60% reduction)
        const infrastructureSavingsPercent = 0.45 + (Math.random() * 0.15)
        const infrastructureCost = metrics.currentMonthlySpend * infrastructureSavingsPercent * multiplier
        
        // Calculate operational savings
        const operationalSavingsPercent = 0.25
        const operationalCost = (metrics.teamSize * 10000) * operationalSavingsPercent
        
        // Performance improvements value
        const latencyImprovement = 0.6 // 60% latency reduction
        const performanceValue = (metrics.requestsPerMonth / 1000000) * 500 * latencyImprovement
        
        // Total savings
        const totalMonthlySavings = infrastructureCost + operationalCost + performanceValue
        const totalAnnualSavings = totalMonthlySavings * 12
        
        // Implementation cost (one-time)
        const implementationCost = metrics.currentMonthlySpend * 2
        
        // Payback period in months
        const paybackPeriod = implementationCost / totalMonthlySavings
        
        // 3-year ROI
        const threeYearSavings = totalAnnualSavings * 3
        const threeYearROI = ((threeYearSavings - implementationCost) / implementationCost) * 100

        setSavings({
          infrastructureCost,
          operationalCost,
          performanceGain: performanceValue,
          totalMonthlySavings,
          totalAnnualSavings,
          paybackPeriod,
          threeYearROI
        })
      }
      
      setCalculated(true)
      if (onComplete) {
        setTimeout(onComplete, 1500)
      }
    } catch (error) {
      console.error('ROI calculation error:', error)
      // Fallback to local calculation
      const multiplier = industryMultipliers[industry] || industryMultipliers.default
      const infrastructureSavingsPercent = 0.45 + (Math.random() * 0.15)
      const infrastructureCost = metrics.currentMonthlySpend * infrastructureSavingsPercent * multiplier
      const operationalSavingsPercent = 0.25
      const operationalCost = (metrics.teamSize * 10000) * operationalSavingsPercent
      const latencyImprovement = 0.6
      const performanceValue = (metrics.requestsPerMonth / 1000000) * 500 * latencyImprovement
      const totalMonthlySavings = infrastructureCost + operationalCost + performanceValue
      const totalAnnualSavings = totalMonthlySavings * 12
      const implementationCost = metrics.currentMonthlySpend * 2
      const paybackPeriod = implementationCost / totalMonthlySavings
      const threeYearSavings = totalAnnualSavings * 3
      const threeYearROI = ((threeYearSavings - implementationCost) / implementationCost) * 100

      setSavings({
        infrastructureCost,
        operationalCost,
        performanceGain: performanceValue,
        totalMonthlySavings,
        totalAnnualSavings,
        paybackPeriod,
        threeYearROI
      })
      
      setCalculated(true)
      if (onComplete) {
        setTimeout(onComplete, 1500)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('en-US').format(value)
  }

  const exportReport = () => {
    const report = {
      industry,
      currentMetrics: metrics,
      projectedSavings: savings,
      timestamp: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `netra-roi-report-${Date.now()}.json`
    a.click()
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calculator className="w-5 h-5" />
            ROI Calculator
          </CardTitle>
          <CardDescription>
            Calculate your potential savings with Netra AI Optimization Platform
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Input Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="spend">Current Monthly AI Infrastructure Spend</Label>
                <div className="flex items-center space-x-2">
                  <DollarSign className="w-4 h-4 text-muted-foreground" />
                  <Input
                    id="spend"
                    type="number"
                    value={metrics.currentMonthlySpend}
                    onChange={(e) => setMetrics({...metrics, currentMonthlySpend: Number(e.target.value)})}
                    className="flex-1"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Include compute, storage, and API costs
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="requests">Monthly AI Requests</Label>
                <Input
                  id="requests"
                  type="number"
                  value={metrics.requestsPerMonth}
                  onChange={(e) => setMetrics({...metrics, requestsPerMonth: Number(e.target.value)})}
                />
                <p className="text-xs text-muted-foreground">
                  Total inference and training requests
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="team">AI/ML Team Size</Label>
                <div className="flex items-center space-x-4">
                  <Slider
                    id="team"
                    min={1}
                    max={50}
                    step={1}
                    value={[metrics.teamSize]}
                    onValueChange={(value) => setMetrics({...metrics, teamSize: value[0]})}
                    className="flex-1"
                  />
                  <span className="w-12 text-right font-medium">{metrics.teamSize}</span>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="latency">Average Latency (ms)</Label>
                <div className="flex items-center space-x-4">
                  <Slider
                    id="latency"
                    min={50}
                    max={1000}
                    step={10}
                    value={[metrics.averageLatency]}
                    onValueChange={(value) => setMetrics({...metrics, averageLatency: value[0]})}
                    className="flex-1"
                  />
                  <span className="w-16 text-right font-medium">{metrics.averageLatency}ms</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="accuracy">Model Accuracy (%)</Label>
                <div className="flex items-center space-x-4">
                  <Slider
                    id="accuracy"
                    min={70}
                    max={99}
                    step={1}
                    value={[metrics.modelAccuracy]}
                    onValueChange={(value) => setMetrics({...metrics, modelAccuracy: value[0]})}
                    className="flex-1"
                  />
                  <span className="w-12 text-right font-medium">{metrics.modelAccuracy}%</span>
                </div>
              </div>

              <Alert className="mt-4">
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Industry multiplier applied: <strong>{industry}</strong> ({((industryMultipliers[industry] || 1.0) - 1) * 100}% boost)
                </AlertDescription>
              </Alert>
            </div>
          </div>

          <div className="flex justify-center pt-4">
            <Button 
              size="lg" 
              onClick={calculateROI}
              disabled={isLoading}
              className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
            >
              <Calculator className="w-4 h-4 mr-2" />
              {isLoading ? 'Calculating...' : 'Calculate ROI'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results Section */}
      {savings && (
        <Card className={cn(
          "border-2 transition-all duration-500",
          calculated && "border-green-500 shadow-lg"
        )}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-600" />
                Projected Savings & ROI
              </span>
              {calculated && (
                <Badge variant="success" className="text-lg px-3 py-1">
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  {Math.round(savings.threeYearROI)}% ROI
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Monthly Savings Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Infrastructure Savings
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">
                    {formatCurrency(savings.infrastructureCost)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">per month</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Operational Efficiency
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-600">
                    {formatCurrency(savings.operationalCost)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">per month</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Performance Value
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-purple-600">
                    {formatCurrency(savings.performanceGain)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">per month</p>
                </CardContent>
              </Card>
            </div>

            <Separator />

            {/* Total Savings */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">Total Monthly Savings</h4>
                  <div className="text-3xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                    {formatCurrency(savings.totalMonthlySavings)}
                  </div>
                </div>
                
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">Annual Savings</h4>
                  <div className="text-2xl font-bold">
                    {formatCurrency(savings.totalAnnualSavings)}
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">Payback Period</h4>
                  <div className="text-2xl font-bold text-orange-600">
                    {savings.paybackPeriod.toFixed(1)} months
                  </div>
                </div>
                
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">3-Year ROI</h4>
                  <div className="text-2xl font-bold text-green-600">
                    {savings.threeYearROI.toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            {/* Comparison Chart */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium">Cost Comparison</h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Current Monthly Spend</span>
                  <span className="font-medium">{formatCurrency(metrics.currentMonthlySpend)}</span>
                </div>
                <div className="flex items-center justify-between text-green-600">
                  <span className="text-sm flex items-center gap-2">
                    <TrendingDown className="w-4 h-4" />
                    Optimized Monthly Spend
                  </span>
                  <span className="font-bold">
                    {formatCurrency(metrics.currentMonthlySpend - savings.totalMonthlySavings)}
                  </span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-between items-center pt-4">
              <Button 
                variant="outline" 
                onClick={exportReport}
              >
                <Download className="w-4 h-4 mr-2" />
                Export Report
              </Button>
              <Button 
                size="lg"
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              >
                Schedule Executive Briefing
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}