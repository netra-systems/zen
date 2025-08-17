import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface CostItem {
  label: string
  amount: string
}

interface SavingsItem {
  period: string
  savings: string
}

function getCostBreakdown(): CostItem[] {
  return [
    { label: 'Compute', amount: '$12,500/mo' },
    { label: 'Storage', amount: '$2,300/mo' },
    { label: 'Network', amount: '$1,800/mo' },
    { label: 'API Calls', amount: '$8,400/mo' }
  ]
}

function getSavingsTimeline(): SavingsItem[] {
  return [
    { period: 'Month 1', savings: '+$15,000' },
    { period: 'Month 3', savings: '+$45,000' },
    { period: 'Month 6', savings: '+$90,000' },
    { period: 'Year 1', savings: '+$180,000' }
  ]
}

function CostBreakdownCard() {
  const costItems = getCostBreakdown()
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Cost Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {costItems.map((item, idx) => (
            <div key={idx} className="flex justify-between items-center">
              <span className="text-sm">{item.label}</span>
              <span className="text-sm font-semibold">{item.amount}</span>
            </div>
          ))}
          <div className="border-t pt-3 flex justify-between items-center">
            <span className="text-sm font-medium">Total Optimized</span>
            <span className="text-lg font-bold text-green-600">$25,000/mo</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function SavingsTimelineCard() {
  const savingsItems = getSavingsTimeline()
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Savings Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {savingsItems.map((item, idx) => (
            <div key={idx} className="flex justify-between items-center">
              <span className="text-sm">{item.period}</span>
              <span className="text-sm font-semibold text-green-600">{item.savings}</span>
            </div>
          ))}
          <div className="border-t pt-3 flex justify-between items-center">
            <span className="text-sm font-medium">3-Year Total</span>
            <span className="text-lg font-bold text-green-600">+$540,000</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function CostTab() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <CostBreakdownCard />
      <SavingsTimelineCard />
    </div>
  )
}