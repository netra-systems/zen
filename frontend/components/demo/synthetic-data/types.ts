export interface SyntheticDataViewerProps {
  industry: string
}

export interface DataSample {
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

export interface DataStatistics {
  totalSamples: number
  avgProcessingTime: number
  totalDataPoints: number
  types: string[]
}

export interface IndustryTemplate {
  [key: string]: Record<string, unknown>
}