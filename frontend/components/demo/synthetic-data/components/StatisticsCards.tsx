import { Card, CardContent } from '@/components/ui/card'
import { 
  Clock,
  Layers,
  BarChart3,
  FileJson
} from 'lucide-react'
import { DataStatistics } from '../types'

interface StatisticsCardsProps {
  stats: DataStatistics
}

const formatDataPoints = (total: number): string => {
  return (total / 1000).toFixed(1) + 'K'
}

const StatisticCard = ({ 
  label, 
  value, 
  icon: Icon 
}: { 
  label: string
  value: string | number
  icon: React.ComponentType<{ className?: string }>
}) => (
  <Card>
    <CardContent className="p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
        <Icon className="w-8 h-8 text-muted-foreground" />
      </div>
    </CardContent>
  </Card>
)

export default function StatisticsCards({ stats }: StatisticsCardsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatisticCard
        label="Total Samples"
        value={stats.totalSamples}
        icon={Layers}
      />
      
      <StatisticCard
        label="Avg Processing"
        value={`${Math.floor(stats.avgProcessingTime)}ms`}
        icon={Clock}
      />
      
      <StatisticCard
        label="Data Points"
        value={formatDataPoints(stats.totalDataPoints)}
        icon={BarChart3}
      />
      
      <StatisticCard
        label="Data Types"
        value={stats.types.length}
        icon={FileJson}
      />
    </div>
  )
}