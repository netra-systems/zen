import { logger } from '@/lib/logger'
import { webSocketService } from './webSocketService'

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
  private sessionId: string | null = null

  constructor() {
    // WebSocket-only implementation - no HTTP base URL needed
    this.sessionId = this.generateSessionId()
  }

  private generateSessionId(): string {
    return `demo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  private getWebSocketUrl(): string {
    // Use the same logic as other WebSocket services
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const apiUrl = typeof window !== 'undefined' && process.env.NEXT_PUBLIC_API_URL || 'localhost:8000'
    const host = apiUrl.replace(/^https?:\/\//, '')
    return `${protocol}//${host}`
  }

  private async sendWebSocketRequest(type: string, data: any): Promise<any> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`WebSocket request timeout: ${type}`))
      }, 30000)

      const handleResponse = (message: any) => {
        if (message.type === `${type}_response`) {
          clearTimeout(timeout)
          resolve(message.data || message.payload)
        }
      }

      try {
        webSocketService.connect(this.getWebSocketUrl(), {
          onMessage: handleResponse,
          onError: (error) => {
            clearTimeout(timeout)
            reject(error)
          }
        })

        webSocketService.send({
          type,
          data: {
            ...data,
            session_id: this.sessionId,
            timestamp: Date.now()
          }
        })
      } catch (error) {
        clearTimeout(timeout)
        reject(error)
      }
    })
  }

  async sendChatMessage(request: DemoChatRequest): Promise<DemoChatResponse> {
    // SSOT WebSocket implementation - eliminates HTTP dual-path architecture
    try {
      const response = await this.sendWebSocketRequest('demo_chat', {
        message: request.message,
        industry: request.industry,
        session_id: request.session_id || this.sessionId,
        context: request.context || {}
      })

      return {
        response: response.response || response.message || '',
        agents_involved: response.agents_involved || [],
        optimization_metrics: response.optimization_metrics || {},
        session_id: response.session_id || request.session_id || this.sessionId
      }
    } catch (error) {
      logger.error('Demo chat WebSocket request failed', error as Error, {
        component: 'DemoService',
        action: 'sendChatMessage',
        request: { ...request, context: '[redacted]' }
      })
      throw new Error(`Failed to send demo chat message: ${error.message}`)
    }
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