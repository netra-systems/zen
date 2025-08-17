import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Eye,
  Copy,
  CheckCircle,
  Info
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { DataSample } from '../types'

interface StreamTabProps {
  industry: string
  dataSamples: DataSample[]
  selectedSample: DataSample | null
  copiedId: string | null
  onSampleSelect: (sample: DataSample) => void
  onCopy: (data: Record<string, unknown>, id: string) => void
}

const formatTime = (timestamp: string): string => {
  return new Date(timestamp).toLocaleTimeString()
}

const formatNumber = (num: number): string => {
  return num.toLocaleString()
}

const SampleCard = ({ 
  sample, 
  isSelected, 
  onSelect 
}: { 
  sample: DataSample
  isSelected: boolean
  onSelect: () => void
}) => (
  <Card
    className={cn(
      "cursor-pointer transition-all",
      isSelected && "border-primary"
    )}
    onClick={onSelect}
  >
    <CardContent className="p-3">
      <div className="flex items-center justify-between mb-2">
        <Badge variant="outline" className="text-xs">
          {sample.type}
        </Badge>
        <span className="text-xs text-muted-foreground">
          {formatTime(sample.timestamp)}
        </span>
      </div>
      <SampleInfo sample={sample} />
    </CardContent>
  </Card>
)

const SampleInfo = ({ sample }: { sample: DataSample }) => (
  <div className="space-y-1">
    <div className="flex justify-between text-xs">
      <span className="text-muted-foreground">ID:</span>
      <span className="font-mono">{sample.id.slice(-8)}</span>
    </div>
    <div className="flex justify-between text-xs">
      <span className="text-muted-foreground">Processing:</span>
      <span>{sample.metadata.processingTime}ms</span>
    </div>
    <div className="flex justify-between text-xs">
      <span className="text-muted-foreground">Points:</span>
      <span>{formatNumber(sample.metadata.dataPoints)}</span>
    </div>
  </div>
)

const CopyButton = ({ 
  selectedSample, 
  copiedId, 
  onCopy 
}: { 
  selectedSample: DataSample
  copiedId: string | null
  onCopy: (data: Record<string, unknown>, id: string) => void
}) => (
  <Button
    variant="outline"
    size="sm"
    onClick={() => onCopy(selectedSample.data, selectedSample.id)}
  >
    {copiedId === selectedSample.id ? (
      <>
        <CheckCircle className="w-4 h-4 mr-1 text-green-600" />
        Copied
      </>
    ) : (
      <>
        <Copy className="w-4 h-4 mr-1" />
        Copy
      </>
    )}
  </Button>
)

const SampleDetail = ({ 
  selectedSample, 
  copiedId, 
  onCopy 
}: { 
  selectedSample: DataSample | null
  copiedId: string | null
  onCopy: (data: Record<string, unknown>, id: string) => void
}) => (
  <Card>
    <CardHeader>
      <div className="flex items-center justify-between">
        <CardTitle className="text-lg">Sample Details</CardTitle>
        {selectedSample && (
          <CopyButton 
            selectedSample={selectedSample} 
            copiedId={copiedId} 
            onCopy={onCopy} 
          />
        )}
      </div>
    </CardHeader>
    <CardContent>
      {selectedSample ? (
        <ScrollArea className="h-[400px]">
          <pre className="text-xs font-mono bg-muted p-4 rounded-lg overflow-x-auto">
            {JSON.stringify(selectedSample.data, null, 2)}
          </pre>
        </ScrollArea>
      ) : (
        <div className="flex items-center justify-center h-[400px] text-muted-foreground">
          <Eye className="w-8 h-8 mr-2" />
          Select a sample to view details
        </div>
      )}
    </CardContent>
  </Card>
)

export default function StreamTab({
  industry,
  dataSamples,
  selectedSample,
  copiedId,
  onSampleSelect,
  onCopy
}: StreamTabProps) {
  return (
    <div className="space-y-4">
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Streaming synthetic {industry.toLowerCase()} data in real-time. Each sample represents production-like workload patterns.
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Data Samples</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              <div className="space-y-2">
                {dataSamples.map((sample) => (
                  <SampleCard
                    key={sample.id}
                    sample={sample}
                    isSelected={selectedSample?.id === sample.id}
                    onSelect={() => onSampleSelect(sample)}
                  />
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <SampleDetail 
          selectedSample={selectedSample} 
          copiedId={copiedId} 
          onCopy={onCopy} 
        />
      </div>
    </div>
  )
}