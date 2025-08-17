'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Calculator } from 'lucide-react'
import { 
  ROICalculatorProps, 
  Metrics, 
  Savings, 
  DEFAULT_METRICS 
} from './ROICalculator.types'
import { exportReport } from './ROICalculator.utils'
import { calculateROI } from './ROICalculator.calculations'
import ROIInputForm from './ROICalculator.input'
import ROIResults from './ROICalculator.results'

export default function ROICalculator({ industry, onComplete }: ROICalculatorProps) {
  const [metrics, setMetrics] = useState<Metrics>(DEFAULT_METRICS)
  const [savings, setSavings] = useState<Savings | null>(null)
  const [calculated, setCalculated] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleCalculateROI = async (): Promise<void> => {
    setIsLoading(true)
    try {
      const result = await calculateROI(metrics, industry)
      setSavings(result)
      setCalculated(true)
      if (onComplete) {
        setTimeout(onComplete, 1500)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleExportReport = (): void => {
    exportReport(industry, metrics, savings)
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
          <ROIInputForm 
            metrics={metrics} 
            industry={industry} 
            onMetricsChange={setMetrics} 
          />

          <div className="flex justify-center pt-4">
            <Button 
              size="lg" 
              onClick={handleCalculateROI}
              disabled={isLoading}
              className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
            >
              <Calculator className="w-4 h-4 mr-2" />
              {isLoading ? 'Calculating...' : 'Calculate ROI'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {savings && (
        <ROIResults 
          savings={savings} 
          metrics={metrics} 
          calculated={calculated} 
          onExportReport={handleExportReport} 
        />
      )}
    </div>
  )
}