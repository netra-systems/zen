import { DataSample, DataStatistics } from './types'
import { getIndustryTemplate } from './industry-data-templates'

const generateSampleId = (): string => {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substr(2, 5)
  return `DATA-${timestamp}-${random}`
}

const generateSampleType = (): string => {
  const types = ['inference', 'training', 'preprocessing', 'evaluation']
  const randomIndex = Math.floor(Math.random() * types.length)
  return types[randomIndex]
}

const generateMetadata = (industry: string) => ({
  source: `${industry.toLowerCase().replace(' ', '-')}-pipeline`,
  processingTime: Math.floor(Math.random() * 1000),
  dataPoints: Math.floor(Math.random() * 10000)
})

export const generateDataSample = (industry: string): DataSample => {
  const id = generateSampleId()
  const type = generateSampleType()
  const data = getIndustryTemplate(industry)
  const metadata = generateMetadata(industry)
  
  return {
    id,
    timestamp: new Date().toISOString(),
    type,
    data,
    metadata
  }
}

const calculateAvgProcessingTime = (samples: DataSample[]): number => {
  if (samples.length === 0) return 0
  const total = samples.reduce((acc, s) => acc + s.metadata.processingTime, 0)
  return total / samples.length
}

const calculateTotalDataPoints = (samples: DataSample[]): number => {
  return samples.reduce((acc, s) => acc + s.metadata.dataPoints, 0)
}

const extractUniqueTypes = (samples: DataSample[]): string[] => {
  const types = samples.map(s => s.type)
  return [...new Set(types)]
}

export const getDataStatistics = (samples: DataSample[]): DataStatistics => {
  const totalSamples = samples.length
  const avgProcessingTime = calculateAvgProcessingTime(samples)
  const totalDataPoints = calculateTotalDataPoints(samples)
  const types = extractUniqueTypes(samples)
  
  return {
    totalSamples,
    avgProcessingTime,
    totalDataPoints,
    types
  }
}

export const generateInitialSamples = (industry: string, count: number = 5): DataSample[] => {
  return Array.from({ length: count }, () => generateDataSample(industry))
}

export const copyToClipboard = async (data: Record<string, unknown>): Promise<void> => {
  const jsonString = JSON.stringify(data, null, 2)
  await navigator.clipboard.writeText(jsonString)
}

export const exportSamples = (industry: string, samples: DataSample[]): void => {
  const exportData = {
    industry,
    samples,
    timestamp: new Date().toISOString()
  }
  
  const jsonString = JSON.stringify(exportData, null, 2)
  const blob = new Blob([jsonString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  
  const fileName = `synthetic-data-${industry.toLowerCase().replace(' ', '-')}-${Date.now()}.json`
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
}