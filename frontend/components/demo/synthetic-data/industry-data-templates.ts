import { IndustryTemplate } from './types'

const createFinancialTemplate = (): Record<string, unknown> => ({
  transaction_id: `TXN-${Date.now()}`,
  amount: (Math.random() * 10000).toFixed(2),
  merchant: ['Amazon', 'Walmart', 'Target', 'BestBuy'][Math.floor(Math.random() * 4)],
  risk_score: (Math.random() * 100).toFixed(1),
  fraud_probability: (Math.random() * 0.1).toFixed(3),
  user_segment: ['Premium', 'Standard', 'Basic'][Math.floor(Math.random() * 3)],
  location: { lat: 40.7128, lng: -74.0060, country: 'US' },
  device_fingerprint: `DEV-${Math.random().toString(36).substr(2, 9)}`
})

const createFinancialMLFeatures = () => ({
  velocity_check: Math.random() > 0.5,
  pattern_match: (Math.random() * 100).toFixed(1),
  anomaly_score: (Math.random() * 10).toFixed(2)
})

const createHealthcareTemplate = (): Record<string, unknown> => ({
  patient_id: `PAT-${Date.now()}`,
  diagnosis_code: ['E11.9', 'I10', 'J45.909', 'M79.3'][Math.floor(Math.random() * 4)]
})

const createHealthcareVitals = () => ({
  heart_rate: 60 + Math.floor(Math.random() * 40),
  blood_pressure: `${110 + Math.floor(Math.random() * 30)}/${70 + Math.floor(Math.random() * 20)}`,
  temperature: (36.5 + Math.random() * 2).toFixed(1),
  oxygen_saturation: 95 + Math.floor(Math.random() * 5)
})

const createHealthcareLabResults = () => ({
  glucose: 70 + Math.floor(Math.random() * 50),
  cholesterol: 150 + Math.floor(Math.random() * 100),
  hemoglobin: (12 + Math.random() * 4).toFixed(1)
})

const createHealthcarePrediction = () => ({
  readmission_risk: (Math.random() * 0.3).toFixed(2),
  treatment_recommendation: ['Medication A', 'Therapy B', 'Surgery C'][Math.floor(Math.random() * 3)],
  confidence: (0.7 + Math.random() * 0.3).toFixed(2)
})

const createEcommerceTemplate = (): Record<string, unknown> => ({
  session_id: `SES-${Date.now()}`,
  user_id: `USR-${Math.floor(Math.random() * 100000)}`,
  products_viewed: Math.floor(Math.random() * 20),
  cart_value: (Math.random() * 500).toFixed(2)
})

const createEcommerceRecommendations = () => [
  { product_id: `PRD-${Math.floor(Math.random() * 10000)}`, score: (Math.random()).toFixed(3) },
  { product_id: `PRD-${Math.floor(Math.random() * 10000)}`, score: (Math.random()).toFixed(3) },
  { product_id: `PRD-${Math.floor(Math.random() * 10000)}`, score: (Math.random()).toFixed(3) }
]

const createEcommerceBehavior = () => ({
  bounce_probability: (Math.random() * 0.5).toFixed(2),
  conversion_likelihood: (Math.random()).toFixed(2),
  lifetime_value: (Math.random() * 10000).toFixed(2)
})

const createEcommercePersonalization = () => ({
  segment: ['High-Value', 'Regular', 'New', 'Churning'][Math.floor(Math.random() * 4)],
  preferred_categories: ['Electronics', 'Fashion', 'Home'][Math.floor(Math.random() * 3)]
})

const createTechnologyTemplate = (): Record<string, unknown> => ({
  request_id: `REQ-${Date.now()}`,
  service: ['auth-service', 'api-gateway', 'ml-inference', 'data-pipeline'][Math.floor(Math.random() * 4)],
  latency_ms: Math.floor(Math.random() * 500),
  status_code: [200, 201, 400, 500][Math.floor(Math.random() * 4)]
})

const createTechnologyTrace = () => ({
  span_id: `SPAN-${Math.random().toString(36).substr(2, 9)}`,
  parent_id: `PARENT-${Math.random().toString(36).substr(2, 9)}`,
  duration_ms: Math.floor(Math.random() * 1000)
})

const createTechnologyMLMetrics = () => ({
  model_version: `v${Math.floor(Math.random() * 10)}.${Math.floor(Math.random() * 10)}`,
  inference_time: Math.floor(Math.random() * 100),
  confidence_score: (Math.random()).toFixed(3),
  tokens_processed: Math.floor(Math.random() * 1000)
})

const createTechnologyOptimization = () => ({
  cache_hit: Math.random() > 0.3,
  batch_size: [1, 8, 16, 32][Math.floor(Math.random() * 4)],
  gpu_utilization: (Math.random() * 100).toFixed(1)
})

const buildFinancialData = (): Record<string, unknown> => {
  const base = createFinancialTemplate()
  const mlFeatures = createFinancialMLFeatures()
  return { ...base, ml_features: mlFeatures }
}

const buildHealthcareData = (): Record<string, unknown> => {
  const base = createHealthcareTemplate()
  const vitals = createHealthcareVitals()
  const labResults = createHealthcareLabResults()
  const prediction = createHealthcarePrediction()
  return { ...base, vital_signs: vitals, lab_results: labResults, prediction }
}

const buildEcommerceData = (): Record<string, unknown> => {
  const base = createEcommerceTemplate()
  const recommendations = createEcommerceRecommendations()
  const behavior = createEcommerceBehavior()
  const personalization = createEcommercePersonalization()
  return { ...base, recommendations, user_behavior: behavior, personalization }
}

const buildTechnologyData = (): Record<string, unknown> => {
  const base = createTechnologyTemplate()
  const trace = createTechnologyTrace()
  const mlMetrics = createTechnologyMLMetrics()
  const optimization = createTechnologyOptimization()
  return { ...base, trace, ml_metrics: mlMetrics, optimization }
}

export const industryTemplates: IndustryTemplate = {
  'Financial Services': buildFinancialData(),
  'Healthcare': buildHealthcareData(),
  'E-commerce': buildEcommerceData(),
  'Technology': buildTechnologyData()
}

export const getIndustryTemplate = (industry: string): Record<string, unknown> => {
  if (industry === 'Financial Services') return buildFinancialData()
  if (industry === 'Healthcare') return buildHealthcareData()
  if (industry === 'E-commerce') return buildEcommerceData()
  if (industry === 'Technology') return buildTechnologyData()
  return buildTechnologyData()
}