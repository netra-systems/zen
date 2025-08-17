/**
 * ROI Calculator Results Display Component
 * Business Value: Enterprise ROI visualization and reporting
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  TrendingUp, 
  TrendingDown, 
  ArrowRight,
  Download,
  CheckCircle2
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Metrics, Savings } from './ROICalculator.types'
import { formatCurrency } from './ROICalculator.utils'

interface ROIResultsProps {
  savings: Savings
  metrics: Metrics
  calculated: boolean
  onExportReport: () => void
}

const SavingsCard = ({ title, amount, color }: { title: string; amount: number; color: string }) => (
  <Card>
    <CardHeader className="pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground">
        {title}
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className={`text-2xl font-bold ${color}`}>
        {formatCurrency(amount)}
      </div>
      <p className="text-xs text-muted-foreground mt-1">per month</p>
    </CardContent>
  </Card>
)

const MetricDisplay = ({ title, value, isGreen }: { title: string; value: string; isGreen?: boolean }) => (
  <div>
    <h4 className="text-sm font-medium text-muted-foreground mb-2">{title}</h4>
    <div className={`text-2xl font-bold ${isGreen ? 'text-green-600' : ''}`}>
      {value}
    </div>
  </div>
)

const CostComparison = ({ current, optimized }: { current: number; optimized: number }) => (
  <div className="space-y-3">
    <h4 className="text-sm font-medium">Cost Comparison</h4>
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm">Current Monthly Spend</span>
        <span className="font-medium">{formatCurrency(current)}</span>
      </div>
      <div className="flex items-center justify-between text-green-600">
        <span className="text-sm flex items-center gap-2">
          <TrendingDown className="w-4 h-4" />
          Optimized Monthly Spend
        </span>
        <span className="font-bold">
          {formatCurrency(optimized)}
        </span>
      </div>
    </div>
  </div>
)

export default function ROIResults({ savings, metrics, calculated, onExportReport }: ROIResultsProps) {
  return (
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
            <Badge variant="default" className="text-lg px-3 py-1">
              <CheckCircle2 className="w-4 h-4 mr-2" />
              {Math.round(savings.threeYearROI)}% ROI
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Monthly Savings Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SavingsCard 
            title="Infrastructure Savings" 
            amount={savings.infrastructureCost} 
            color="text-green-600" 
          />
          <SavingsCard 
            title="Operational Efficiency" 
            amount={savings.operationalCost} 
            color="text-blue-600" 
          />
          <SavingsCard 
            title="Performance Value" 
            amount={savings.performanceGain} 
            color="text-purple-600" 
          />
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
            
            <MetricDisplay 
              title="Annual Savings" 
              value={formatCurrency(savings.totalAnnualSavings)} 
            />
          </div>

          <div className="space-y-4">
            <MetricDisplay 
              title="Payback Period" 
              value={`${savings.paybackPeriod.toFixed(1)} months`} 
            />
            
            <MetricDisplay 
              title="3-Year ROI" 
              value={`${savings.threeYearROI.toFixed(0)}%`} 
              isGreen 
            />
          </div>
        </div>

        <Separator />

        <CostComparison 
          current={metrics.currentMonthlySpend}
          optimized={metrics.currentMonthlySpend - savings.totalMonthlySavings}
        />

        {/* Action Buttons */}
        <div className="flex justify-between items-center pt-4">
          <Button 
            variant="outline" 
            onClick={onExportReport}
          >
            <Download className="w-4 h-4 mr-2" />
            Export Report
          </Button>
          <Button 
            size="lg"
            className="bg-gradient-to-r from-emerald-600 to-purple-600 hover:from-emerald-700 hover:to-purple-700"
          >
            Schedule Executive Briefing
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}