/**
 * DemoChat Templates Module  
 * Module: Industry-specific optimization templates
 * Lines: <300, Functions: ≤8 lines each
 */

import React from 'react'
import { 
  Shield, TrendingUp, Activity, Brain, Heart, Database,
  Sparkles, Search, Package, Code, Server, Zap
} from 'lucide-react'
import { Template } from './DemoChat.types'

const createTemplate = (
  id: string, title: string, prompt: string, 
  icon: React.ReactNode, category: string
): Template => ({
  id, title, prompt, icon, category
})

const getFinancialTemplates = (): Template[] => [
  createTemplate(
    'fraud-1', 'Optimize Fraud Detection Pipeline',
    'Analyze and optimize our fraud detection ML pipeline that processes 10M transactions daily',
    <Shield className="w-4 h-4" />, 'Security'
  ),
  createTemplate(
    'risk-1', 'Risk Scoring Performance', 
    'Improve latency for real-time credit risk scoring models',
    <TrendingUp className="w-4 h-4" />, 'Analytics'
  ),
  createTemplate(
    'trading-1', 'Trading Algorithm Optimization',
    'Optimize high-frequency trading algorithms for lower latency', 
    <Activity className="w-4 h-4" />, 'Trading'
  )
]

const getHealthcareTemplates = (): Template[] => [
  createTemplate(
    'diagnostic-1', 'Medical Image Analysis',
    'Optimize diagnostic imaging AI for faster MRI/CT scan analysis',
    <Brain className="w-4 h-4" />, 'Diagnostics'
  ),
  createTemplate(
    'patient-1', 'Patient Risk Prediction',
    'Improve patient readmission prediction model performance',
    <Heart className="w-4 h-4" />, 'Patient Care'
  ),
  createTemplate(
    'drug-1', 'Drug Discovery Pipeline',
    'Optimize molecular simulation workloads for drug discovery',
    <Database className="w-4 h-4" />, 'Research'
  )
]

const getEcommerceTemplates = (): Template[] => [
  createTemplate(
    'rec-1', 'Recommendation Engine',
    'Optimize product recommendation system serving 100M users',
    <Sparkles className="w-4 h-4" />, 'Personalization'
  ),
  createTemplate(
    'search-1', 'Search Optimization',
    'Improve search relevance and reduce query latency',
    <Search className="w-4 h-4" />, 'Search'
  ),
  createTemplate(
    'inventory-1', 'Inventory Forecasting',
    'Optimize demand forecasting models for inventory management',
    <Package className="w-4 h-4" />, 'Operations'
  )
]

const getTechnologyTemplates = (): Template[] => [
  createTemplate(
    'code-1', 'Code Generation Pipeline',
    'Optimize AI code completion service for IDE integration',
    <Code className="w-4 h-4" />, 'Development'
  ),
  createTemplate(
    'devops-1', 'CI/CD Optimization',
    'Improve AI-powered test generation and deployment validation',
    <Server className="w-4 h-4" />, 'DevOps'
  ),
  createTemplate(
    'analytics-1', 'User Analytics AI',
    'Optimize real-time user behavior prediction models',
    <Activity className="w-4 h-4" />, 'Analytics'
  )
]

const getDefaultTemplates = (): Template[] => [
  createTemplate(
    'general-1', 'Analyze Current Workload',
    'Analyze my current AI workload and identify optimization opportunities',
    <Brain className="w-4 h-4" />, 'Analysis'
  ),
  createTemplate(
    'general-2', 'Cost Optimization',
    'Show me how to reduce AI infrastructure costs without impacting performance',
    <TrendingUp className="w-4 h-4" />, 'Cost'
  ),
  createTemplate(
    'general-3', 'Performance Tuning',
    'Optimize model inference latency for production workloads',
    <Zap className="w-4 h-4" />, 'Performance'
  )
]

const buildIndustryTemplates = (): Record<string, Template[]> => ({
  'Financial Services': getFinancialTemplates(),
  'Healthcare': getHealthcareTemplates(),
  'E-commerce': getEcommerceTemplates(),
  'Technology': getTechnologyTemplates()
})

export const getTemplatesForIndustry = (industry: string): Template[] => {
  const industryTemplates = buildIndustryTemplates()
  return industryTemplates[industry] || getDefaultTemplates()
}