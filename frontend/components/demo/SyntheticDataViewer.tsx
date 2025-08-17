'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Database,
  RefreshCw,
  Download
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { SyntheticDataViewerProps, DataSample } from './synthetic-data/types'
import { generateDataSample, generateInitialSamples, getDataStatistics, copyToClipboard, exportSamples } from './synthetic-data/data-generation'
import StatisticsCards from './synthetic-data/components/StatisticsCards'
import StreamTab from './synthetic-data/components/StreamTab'
import ExplorerTab from './synthetic-data/components/ExplorerTab'
import SchemaTab from './synthetic-data/components/SchemaTab'

export default function SyntheticDataViewer({ industry }: SyntheticDataViewerProps) {
  const [activeTab, setActiveTab] = useState('stream')
  const [isGenerating, setIsGenerating] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [dataSamples, setDataSamples] = useState<DataSample[]>([])
  const [selectedSample, setSelectedSample] = useState<DataSample | null>(null)

  const initializeSamples = () => {
    const initialSamples = generateInitialSamples(industry)
    setDataSamples(initialSamples)
    setSelectedSample(initialSamples[0])
  }

  useEffect(() => {
    initializeSamples()
  }, [industry])

  const simulateGeneration = async () => {
    const newSample = generateDataSample(industry)
    setDataSamples(prev => [newSample, ...prev].slice(0, 10))
    await new Promise(resolve => setTimeout(resolve, 500))
  }

  const handleGenerateData = async () => {
    setIsGenerating(true)
    for (let i = 0; i < 3; i++) {
      await simulateGeneration()
    }
    setIsGenerating(false)
  }

  const handleCopy = async (data: Record<string, unknown>, id: string) => {
    await copyToClipboard(data)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleExport = () => {
    exportSamples(industry, dataSamples)
  }

  const stats = getDataStatistics(dataSamples)

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Database className="w-5 h-5" />
                Synthetic Data Generation
              </CardTitle>
              <CardDescription>
                Production-grade synthetic data for {industry}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateData}
                disabled={isGenerating}
              >
                <RefreshCw className={cn("w-4 h-4 mr-1", isGenerating && "animate-spin")} />
                Generate
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
              >
                <Download className="w-4 h-4 mr-1" />
                Export
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      <StatisticsCards stats={stats} />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="stream">Live Stream</TabsTrigger>
          <TabsTrigger value="explorer">Data Explorer</TabsTrigger>
          <TabsTrigger value="schema">Schema View</TabsTrigger>
        </TabsList>

        <TabsContent value="stream" className="space-y-4">
          <StreamTab
            industry={industry}
            dataSamples={dataSamples}
            selectedSample={selectedSample}
            copiedId={copiedId}
            onSampleSelect={setSelectedSample}
            onCopy={handleCopy}
          />
        </TabsContent>

        <TabsContent value="explorer" className="space-y-4">
          <ExplorerTab dataSamples={dataSamples} />
        </TabsContent>

        <TabsContent value="schema" className="space-y-4">
          <SchemaTab industry={industry} />
        </TabsContent>
      </Tabs>
    </div>
  )
}