/**
 * DemoChat Message Utilities
 * Module: Message creation and processing functions
 * Lines: <300, Functions: ≤8 lines each
 */

import { generateUniqueId } from '@/lib/utils'
import { Message, OptimizationMetrics } from './DemoChat.types'

export const createWelcomeMessage = (industry: string): Message => ({
  id: '1',
  role: 'system',
  content: `Welcome to the Netra AI Optimization Demo! I've loaded industry-specific optimization scenarios for **${industry}**. Select a template below or describe your specific AI workload challenge.`,
  timestamp: new Date()
})

export const createUserMessage = (content: string): Message => ({
  id: generateUniqueId('msg'),
  role: 'user',
  content,
  timestamp: new Date()
})

export const createSystemMessage = (content: string): Message => ({
  id: generateUniqueId('msg'),
  role: 'system', 
  content,
  timestamp: new Date()
})

const calculateProcessingTime = (): number => 
  2500 + Math.random() * 1500

const calculateTokensUsed = (): number => 
  1500 + Math.floor(Math.random() * 1000)

const calculateCostSaved = (): number => 
  15000 + Math.floor(Math.random() * 35000)

const getRandomOptimizationType = (): string => {
  const types = ['Model Compression', 'Batch Optimization', 'Caching Strategy', 'Infrastructure Scaling', 'Pipeline Parallelization']
  return types[Math.floor(Math.random() * types.length)]
}

export const createResponseMessage = (
  content: string,
  metrics?: OptimizationMetrics
): Message => ({
  id: generateUniqueId('msg'),
  role: 'assistant',
  content,
  timestamp: new Date(),
  metadata: {
    processingTime: metrics?.processing_time || calculateProcessingTime(),
    tokensUsed: metrics?.tokens_used || calculateTokensUsed(),
    costSaved: metrics?.estimated_annual_savings 
      ? Math.round(metrics.estimated_annual_savings / 12)
      : calculateCostSaved(),
    optimizationType: getRandomOptimizationType()
  }
})

const generateRequestVolume = (): number => 
  Math.floor(10 + Math.random() * 90)

const generateLatency = (): number => 
  Math.floor(200 + Math.random() * 300)

const generateMonthlyCost = (): number => 
  50000 + Math.random() * 100000

const generateLatencyReduction = (): number => 
  Math.floor(40 + Math.random() * 30)

const generateThroughputImprovement = (): number => 
  Math.floor(2 + Math.random() * 2)

const generateBatchingPercentage = (): number => 
  Math.floor(60 + Math.random() * 30)

const generateCacheHitRate = (): number => 
  Math.floor(85 + Math.random() * 10)

const generateROIMonths = (): number => 
  Math.floor(2 + Math.random() * 3)

const generateSLACompliance = (): number => 
  99.9 + Math.random() * 0.09

const generateOverheadReduction = (): number => 
  Math.floor(30 + Math.random() * 30)

export const generateFallbackResponse = (
  industry: string,
  optimizationType: string,
  costSaved: number
): string => {
  const requestVolume = generateRequestVolume()
  const latency = generateLatency()
  const monthlyCost = generateMonthlyCost()
  const latencyReduction = generateLatencyReduction()
  const throughputImprovement = generateThroughputImprovement()
  const batchingPercentage = generateBatchingPercentage()
  const cacheHitRate = generateCacheHitRate()
  const roiMonths = generateROIMonths()
  const slaCompliance = generateSLACompliance()
  const overheadReduction = generateOverheadReduction()

  return `Based on my analysis of your ${industry.toLowerCase()} workload, I've identified significant optimization opportunities:

**Current State Analysis:**
- Processing ${requestVolume}M requests/month
- Average latency: ${latency}ms
- Current cost: $${monthlyCost.toFixed(0)}/month

**Optimization Strategy: ${optimizationType}**
- Reduce latency by ${latencyReduction}%
- Improve throughput by ${throughputImprovement}x
- Cost savings: $${costSaved.toLocaleString()}/month

**Implementation Plan:**
1. Deploy intelligent request routing
2. Implement adaptive batching for ${batchingPercentage}% of workloads
3. Enable multi-model caching with ${cacheHitRate}% hit rate
4. Optimize resource allocation using predictive scaling

**Expected Results:**
- ROI within ${roiMonths} months
- ${slaCompliance.toFixed(1)}% SLA compliance
- ${overheadReduction}% reduction in operational overhead

Would you like me to generate a detailed implementation roadmap or explore specific optimization techniques?`
}