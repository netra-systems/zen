import { API_BASE_URL } from './apiConfig'

export interface DemoChatRequest {
  message: string
  industry: string
  session_id?: string
  context?: Record<string, any>
}

export interface DemoChatResponse {
  response: string
  agents_involved: string[]
  optimization_metrics: Record<string, any>
  session_id: string
}

export interface ROICalculationRequest {
  current_spend: number
  request_volume: number
  average_latency: number
  industry: string
}

export interface ROICalculationResponse {
  current_annual_cost: number
  optimized_annual_cost: number
  annual_savings: number
  savings_percentage: number
  roi_months: number
  three_year_tco_reduction: number
  performance_improvements: Record<string, number>
}

export interface IndustryTemplate {
  industry: string
  name: string
  description: string
  prompt_template: string
  optimization_scenarios: Array<Record<string, any>>
  typical_metrics: Record<string, any>
}

export interface DemoMetrics {
  latency_reduction: number
  throughput_increase: number
  cost_reduction: number
  accuracy_improvement: number
  timestamps: string[]
  values: Record<string, number[]>
}

export interface ExportReportRequest {
  session_id: string
  format: 'pdf' | 'docx' | 'html'
  include_sections: string[]
}

export interface SessionStatus {
  session_id: string
  progress: number
  completed_steps: string[]
  remaining_actions: string[]
  last_interaction: string
}

class DemoService {
  private baseUrl: string

  constructor() {
    this.baseUrl = API_BASE_URL
  }

  private async fetchWithAuth(url: string, options: RequestInit = {}) {
    const token = localStorage.getItem('token')
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    }

    const response = await fetch(`${this.baseUrl}${url}`, {
      ...options,
      headers,
    })

    if (!response.ok && response.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/auth/login'
      throw new Error('Unauthorized')
    }

    return response
  }

  async sendChatMessage(request: DemoChatRequest): Promise<DemoChatResponse> {
    const response = await this.fetchWithAuth('/api/demo/chat', {
      method: 'POST',
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Failed to send demo chat message: ${response.statusText}`)
    }

    return response.json()
  }

  async calculateROI(request: ROICalculationRequest): Promise<ROICalculationResponse> {
    const response = await this.fetchWithAuth('/api/demo/roi/calculate', {
      method: 'POST',
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Failed to calculate ROI: ${response.statusText}`)
    }

    return response.json()
  }

  async getIndustryTemplates(industry: string): Promise<IndustryTemplate[]> {
    const response = await this.fetchWithAuth(`/api/demo/industry/${encodeURIComponent(industry)}/templates`)

    if (!response.ok) {
      throw new Error(`Failed to get industry templates: ${response.statusText}`)
    }

    return response.json()
  }

  async getSyntheticMetrics(scenario: string = 'standard', durationHours: number = 24): Promise<DemoMetrics> {
    const params = new URLSearchParams({
      scenario,
      duration_hours: durationHours.toString(),
    })

    const response = await this.fetchWithAuth(`/api/demo/metrics/synthetic?${params}`)

    if (!response.ok) {
      throw new Error(`Failed to get synthetic metrics: ${response.statusText}`)
    }

    return response.json()
  }

  async exportReport(request: ExportReportRequest): Promise<{ status: string; report_url: string; expires_at: string }> {
    const response = await this.fetchWithAuth('/api/demo/export/report', {
      method: 'POST',
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Failed to export report: ${response.statusText}`)
    }

    return response.json()
  }

  async getSessionStatus(sessionId: string): Promise<SessionStatus> {
    const response = await this.fetchWithAuth(`/api/demo/session/${encodeURIComponent(sessionId)}/status`)

    if (!response.ok) {
      throw new Error(`Failed to get session status: ${response.statusText}`)
    }

    return response.json()
  }

  async submitFeedback(sessionId: string, feedback: Record<string, any>): Promise<{ status: string; message: string }> {
    const response = await this.fetchWithAuth(`/api/demo/session/${encodeURIComponent(sessionId)}/feedback`, {
      method: 'POST',
      body: JSON.stringify(feedback),
    })

    if (!response.ok) {
      throw new Error(`Failed to submit feedback: ${response.statusText}`)
    }

    return response.json()
  }

  async getAnalyticsSummary(days: number = 30): Promise<Record<string, any>> {
    const params = new URLSearchParams({ days: days.toString() })
    const response = await this.fetchWithAuth(`/api/demo/analytics/summary?${params}`)

    if (!response.ok) {
      throw new Error(`Failed to get analytics summary: ${response.statusText}`)
    }

    return response.json()
  }
}

export const demoService = new DemoService()