import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Code } from 'lucide-react'
import { DataSample } from '../types'

interface ExplorerTabProps {
  dataSamples: DataSample[]
}

const truncateValue = (value: unknown): string => {
  if (typeof value === 'object') return '[Object]'
  return String(value).slice(0, 20)
}

const SamplePreview = ({ sample }: { sample: DataSample }) => (
  <Card>
    <CardContent className="p-4">
      <div className="flex items-center justify-between mb-2">
        <Badge>{sample.type}</Badge>
        <span className="text-xs text-muted-foreground">
          {sample.metadata.source}
        </span>
      </div>
      <SampleData data={sample.data} />
    </CardContent>
  </Card>
)

const SampleData = ({ data }: { data: Record<string, unknown> }) => (
  <div className="grid grid-cols-2 gap-2 text-xs">
    {Object.entries(data).slice(0, 4).map(([key, value]) => (
      <DataField key={key} fieldKey={key} value={value} />
    ))}
  </div>
)

const DataField = ({ 
  fieldKey, 
  value 
}: { 
  fieldKey: string
  value: unknown
}) => (
  <div className="flex justify-between">
    <span className="text-muted-foreground">{fieldKey}:</span>
    <span className="font-mono">
      {truncateValue(value)}
    </span>
  </div>
)

export default function ExplorerTab({ dataSamples }: ExplorerTabProps) {
  const previewSamples = dataSamples.slice(0, 3)
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Interactive Data Explorer</CardTitle>
        <CardDescription>
          Explore and filter synthetic data with advanced querying
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Alert className="mb-4">
          <Code className="h-4 w-4" />
          <AlertDescription>
            Use JSON path expressions to filter and transform data. Example: $.user_behavior.conversion_likelihood > 0.5
          </AlertDescription>
        </Alert>
        
        <div className="space-y-4">
          {previewSamples.map((sample) => (
            <SamplePreview key={sample.id} sample={sample} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}