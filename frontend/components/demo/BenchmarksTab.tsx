import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { CheckCircle } from 'lucide-react'
import { benchmarks } from './data'
import { Benchmark } from './types'

function calculatePercentile(percentile: number): number {
  return 100 - percentile
}

function BenchmarkRow({ benchmark }: { benchmark: Benchmark }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-medium">{benchmark.name}</span>
          <Badge variant="outline" className="ml-2 text-xs">
            {benchmark.category}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            Top {calculatePercentile(benchmark.percentile)}%
          </span>
          <Badge variant="default">
            {benchmark.score}/100
          </Badge>
        </div>
      </div>
      <Progress value={benchmark.score} className="h-2" />
    </div>
  )
}

function BenchmarksList() {
  return (
    <div className="space-y-4">
      {benchmarks.map((benchmark, idx) => (
        <BenchmarkRow key={idx} benchmark={benchmark} />
      ))}
    </div>
  )
}

function PerformanceSummary({ industry }: { industry: string }) {
  return (
    <div className="mt-6 p-4 bg-green-50 dark:bg-green-950 rounded-lg">
      <div className="flex items-center gap-2">
        <CheckCircle className="w-5 h-5 text-green-600" />
        <p className="text-sm font-medium">
          Your optimized system ranks in the top 5% for {industry} workloads
        </p>
      </div>
    </div>
  )
}

export function BenchmarksTab({ industry }: { industry: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Industry Benchmarks</CardTitle>
        <CardDescription>Performance compared to industry standards</CardDescription>
      </CardHeader>
      <CardContent>
        <BenchmarksList />
        <PerformanceSummary industry={industry} />
      </CardContent>
    </Card>
  )
}