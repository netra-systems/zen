'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Database,
  RefreshCw,
  Download,
  Code,
  BarChart3,
  FileJson,
  Clock,
  Layers,
  Eye,
  Copy,
  CheckCircle,
  Info
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface SyntheticDataViewerProps {
  industry: string
}

interface DataSample {
  id: string
  timestamp: string
  type: string
  data: Record<string, unknown>
  metadata: {
    source: string
    processingTime: number
    dataPoints: number
  }
}

export default function SyntheticDataViewer({ industry }: SyntheticDataViewerProps) {
  const [activeTab, setActiveTab] = useState('stream')
  const [isGenerating, setIsGenerating] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [dataSamples, setDataSamples] = useState<DataSample[]>([])
  const [selectedSample, setSelectedSample] = useState<DataSample | null>(null)

  const generateIndustryData = useCallback(() => {
    const industryTemplates: Record<string, Record<string, unknown>> = {
      'Financial Services': {
        transaction_id: `TXN-${Date.now()}`,
        amount: (Math.random() * 10000).toFixed(2),
        merchant: ['Amazon', 'Walmart', 'Target', 'BestBuy'][Math.floor(Math.random() * 4)],
        risk_score: (Math.random() * 100).toFixed(1),
        fraud_probability: (Math.random() * 0.1).toFixed(3),
        user_segment: ['Premium', 'Standard', 'Basic'][Math.floor(Math.random() * 3)],
        location: { lat: 40.7128, lng: -74.0060, country: 'US' },
        device_fingerprint: `DEV-${Math.random().toString(36).substr(2, 9)}`,
        ml_features: {
          velocity_check: Math.random() > 0.5,
          pattern_match: (Math.random() * 100).toFixed(1),
          anomaly_score: (Math.random() * 10).toFixed(2)
        }
      },
      'Healthcare': {
        patient_id: `PAT-${Date.now()}`,
        diagnosis_code: ['E11.9', 'I10', 'J45.909', 'M79.3'][Math.floor(Math.random() * 4)],
        vital_signs: {
          heart_rate: 60 + Math.floor(Math.random() * 40),
          blood_pressure: `${110 + Math.floor(Math.random() * 30)}/${70 + Math.floor(Math.random() * 20)}`,
          temperature: (36.5 + Math.random() * 2).toFixed(1),
          oxygen_saturation: 95 + Math.floor(Math.random() * 5)
        },
        lab_results: {
          glucose: 70 + Math.floor(Math.random() * 50),
          cholesterol: 150 + Math.floor(Math.random() * 100),
          hemoglobin: (12 + Math.random() * 4).toFixed(1)
        },
        prediction: {
          readmission_risk: (Math.random() * 0.3).toFixed(2),
          treatment_recommendation: ['Medication A', 'Therapy B', 'Surgery C'][Math.floor(Math.random() * 3)],
          confidence: (0.7 + Math.random() * 0.3).toFixed(2)
        }
      },
      'E-commerce': {
        session_id: `SES-${Date.now()}`,
        user_id: `USR-${Math.floor(Math.random() * 100000)}`,
        products_viewed: Math.floor(Math.random() * 20),
        cart_value: (Math.random() * 500).toFixed(2),
        recommendations: [
          { product_id: `PRD-${Math.floor(Math.random() * 10000)}`, score: (Math.random()).toFixed(3) },
          { product_id: `PRD-${Math.floor(Math.random() * 10000)}`, score: (Math.random()).toFixed(3) },
          { product_id: `PRD-${Math.floor(Math.random() * 10000)}`, score: (Math.random()).toFixed(3) }
        ],
        user_behavior: {
          bounce_probability: (Math.random() * 0.5).toFixed(2),
          conversion_likelihood: (Math.random()).toFixed(2),
          lifetime_value: (Math.random() * 10000).toFixed(2)
        },
        personalization: {
          segment: ['High-Value', 'Regular', 'New', 'Churning'][Math.floor(Math.random() * 4)],
          preferred_categories: ['Electronics', 'Fashion', 'Home'][Math.floor(Math.random() * 3)]
        }
      },
      'Technology': {
        request_id: `REQ-${Date.now()}`,
        service: ['auth-service', 'api-gateway', 'ml-inference', 'data-pipeline'][Math.floor(Math.random() * 4)],
        latency_ms: Math.floor(Math.random() * 500),
        status_code: [200, 201, 400, 500][Math.floor(Math.random() * 4)],
        trace: {
          span_id: `SPAN-${Math.random().toString(36).substr(2, 9)}`,
          parent_id: `PARENT-${Math.random().toString(36).substr(2, 9)}`,
          duration_ms: Math.floor(Math.random() * 1000)
        },
        ml_metrics: {
          model_version: `v${Math.floor(Math.random() * 10)}.${Math.floor(Math.random() * 10)}`,
          inference_time: Math.floor(Math.random() * 100),
          confidence_score: (Math.random()).toFixed(3),
          tokens_processed: Math.floor(Math.random() * 1000)
        },
        optimization: {
          cache_hit: Math.random() > 0.3,
          batch_size: [1, 8, 16, 32][Math.floor(Math.random() * 4)],
          gpu_utilization: (Math.random() * 100).toFixed(1)
        }
      }
    }

    return industryTemplates[industry] || industryTemplates['Technology']
  }, [industry])

  const generateDataSample = useCallback((): DataSample => {
    const types = ['inference', 'training', 'preprocessing', 'evaluation']
    const type = types[Math.floor(Math.random() * types.length)]
    
    return {
      id: `DATA-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
      timestamp: new Date().toISOString(),
      type,
      data: generateIndustryData(),
      metadata: {
        source: `${industry.toLowerCase().replace(' ', '-')}-pipeline`,
        processingTime: Math.floor(Math.random() * 1000),
        dataPoints: Math.floor(Math.random() * 10000)
      }
    }
  }, [industry, generateIndustryData])

  useEffect(() => {
    // Generate initial data samples
    const initialSamples = Array.from({ length: 5 }, () => generateDataSample())
    setDataSamples(initialSamples)
    setSelectedSample(initialSamples[0])
  }, [industry, generateDataSample])

  const handleGenerateData = async () => {
    setIsGenerating(true)
    
    // Simulate data generation
    for (let i = 0; i < 3; i++) {
      await new Promise(resolve => setTimeout(resolve, 500))
      const newSample = generateDataSample()
      setDataSamples(prev => [newSample, ...prev].slice(0, 10))
    }
    
    setIsGenerating(false)
  }

  const handleCopy = (data: Record<string, unknown>, id: string) => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleExport = () => {
    const exportData = {
      industry,
      samples: dataSamples,
      timestamp: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `synthetic-data-${industry.toLowerCase().replace(' ', '-')}-${Date.now()}.json`
    a.click()
  }

  const getDataStatistics = () => {
    const stats = {
      totalSamples: dataSamples.length,
      avgProcessingTime: dataSamples.reduce((acc, s) => acc + s.metadata.processingTime, 0) / dataSamples.length || 0,
      totalDataPoints: dataSamples.reduce((acc, s) => acc + s.metadata.dataPoints, 0),
      types: [...new Set(dataSamples.map(s => s.type))]
    }
    return stats
  }

  const stats = getDataStatistics()

  return (
    <div className="space-y-6">
      {/* Header */}
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

      {/* Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Total Samples</p>
                <p className="text-2xl font-bold">{stats.totalSamples}</p>
              </div>
              <Layers className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Avg Processing</p>
                <p className="text-2xl font-bold">{Math.floor(stats.avgProcessingTime)}ms</p>
              </div>
              <Clock className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Data Points</p>
                <p className="text-2xl font-bold">{(stats.totalDataPoints / 1000).toFixed(1)}K</p>
              </div>
              <BarChart3 className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Data Types</p>
                <p className="text-2xl font-bold">{stats.types.length}</p>
              </div>
              <FileJson className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Data Viewer */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="stream">Live Stream</TabsTrigger>
          <TabsTrigger value="explorer">Data Explorer</TabsTrigger>
          <TabsTrigger value="schema">Schema View</TabsTrigger>
        </TabsList>

        <TabsContent value="stream" className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Streaming synthetic {industry.toLowerCase()} data in real-time. Each sample represents production-like workload patterns.
            </AlertDescription>
          </Alert>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Sample List */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Data Samples</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {dataSamples.map((sample) => (
                      <Card
                        key={sample.id}
                        className={cn(
                          "cursor-pointer transition-all",
                          selectedSample?.id === sample.id && "border-primary"
                        )}
                        onClick={() => setSelectedSample(sample)}
                      >
                        <CardContent className="p-3">
                          <div className="flex items-center justify-between mb-2">
                            <Badge variant="outline" className="text-xs">
                              {sample.type}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {new Date(sample.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
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
                              <span>{sample.metadata.dataPoints.toLocaleString()}</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Selected Sample Detail */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Sample Details</CardTitle>
                  {selectedSample && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopy(selectedSample.data, selectedSample.id)}
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
          </div>
        </TabsContent>

        <TabsContent value="explorer" className="space-y-4">
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
                  Use JSON path expressions to filter and transform data. Example: $.user_behavior.conversion_likelihood 0.5 
                </AlertDescription>
              </Alert>
              
              <div className="space-y-4">
                {dataSamples.slice(0, 3).map((sample) => (
                  <Card key={sample.id}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <Badge>{sample.type}</Badge>
                        <span className="text-xs text-muted-foreground">
                          {sample.metadata.source}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {Object.entries(sample.data).slice(0, 4).map(([key, value]) => (
                          <div key={key} className="flex justify-between">
                            <span className="text-muted-foreground">{key}:</span>
                            <span className="font-mono">
                              {typeof value === 'object' ? '[Object]' : String(value).slice(0, 20)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="schema" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Data Schema</CardTitle>
              <CardDescription>
                Structure and validation rules for {industry} synthetic data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px]">
                <pre className="text-xs font-mono bg-muted p-4 rounded-lg">
                  {JSON.stringify({
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "title": `${industry} Synthetic Data Schema`,
                    "type": "object",
                    "properties": Object.keys(generateIndustryData()).reduce((acc, key) => {
                      const value = generateIndustryData()[key]
                      acc[key] = {
                        type: typeof value === 'object' ? 'object' : typeof value,
                        description: `${key} field for ${industry} data`,
                        example: value,
                        required: Math.random() > 0.3
                      }
                      return acc
                    }, {} as Record<string, { type: string; description: string; example: unknown; required: boolean }>),
                    "required": Object.keys(generateIndustryData()).filter(() => Math.random() > 0.5)
                  }, null, 2)}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}