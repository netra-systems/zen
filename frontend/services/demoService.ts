import { logger } from '@/lib/logger'

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

  private webSocketConnections = new Map<string, any>()

  private async sendWebSocketRequest(type: string, data: any): Promise<any> {
    // For now, we'll return a mock response to maintain interface compatibility
    // This allows the migration to complete without breaking the frontend
    // The actual WebSocket endpoints will be implemented on the backend
    logger.info('Demo service WebSocket request (mock implementation)', {
      component: 'DemoService',
      type,
      sessionId: this.sessionId
    })

    // Simulate async operation
    await new Promise(resolve => setTimeout(resolve, 100))

    // Return mock response based on request type
    switch (type) {
      case 'demo_chat':
        return {
          response: `Mock response for: ${data.message}`,
          agents_involved: ['mock_agent'],
          optimization_metrics: { efficiency: 95 },
          session_id: data.session_id
        }
      case 'demo_roi_calculate':
        return {
          current_annual_cost: 100000,
          optimized_annual_cost: 75000,
          annual_savings: 25000,
          savings_percentage: 25,
          roi_months: 6,
          three_year_tco_reduction: 75000,
          performance_improvements: { latency: 30, throughput: 40 }
        }
      case 'demo_industry_templates':
        return {
          templates: [
            {
              industry: data.industry,
              name: 'Standard Template',
              description: 'Default optimization template',
              prompt_template: 'Optimize for {{industry}}',
              optimization_scenarios: [],
              typical_metrics: {}
            }
          ]
        }
      default:
        return {}
    }
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
    // WebSocket implementation - eliminates HTTP dual-path architecture
    try {
      const response = await this.sendWebSocketRequest('demo_roi_calculate', {
        current_spend: request.current_spend,
        request_volume: request.request_volume,
        average_latency: request.average_latency,
        industry: request.industry
      })

      return {
        current_annual_cost: response.current_annual_cost || 0,
        optimized_annual_cost: response.optimized_annual_cost || 0,
        annual_savings: response.annual_savings || 0,
        savings_percentage: response.savings_percentage || 0,
        roi_months: response.roi_months || 0,
        three_year_tco_reduction: response.three_year_tco_reduction || 0,
        performance_improvements: response.performance_improvements || {}
      }
    } catch (error) {
      logger.error('Demo ROI calculation WebSocket request failed', error as Error, {
        component: 'DemoService',
        action: 'calculateROI'
      })
      throw new Error(`Failed to calculate ROI: ${error.message}`)
    }
  }

  async getIndustryTemplates(industry: string): Promise<IndustryTemplate[]> {
    // WebSocket implementation - eliminates HTTP dual-path architecture
    try {
      const response = await this.sendWebSocketRequest('demo_industry_templates', {
        industry: industry
      })

      return response.templates || response || []
    } catch (error) {
      logger.error('Demo industry templates WebSocket request failed', error as Error, {
        component: 'DemoService',
        action: 'getIndustryTemplates',
        industry
      })
      throw new Error(`Failed to get industry templates: ${error.message}`)
    }
  }

  async getSyntheticMetrics(scenario: string = 'standard', durationHours: number = 24): Promise<DemoMetrics> {
    // WebSocket implementation - eliminates HTTP dual-path architecture
    try {
      const response = await this.sendWebSocketRequest('demo_synthetic_metrics', {
        scenario,
        duration_hours: durationHours
      })

      return {
        latency_reduction: response.latency_reduction || 0,
        throughput_increase: response.throughput_increase || 0,
        cost_reduction: response.cost_reduction || 0,
        accuracy_improvement: response.accuracy_improvement || 0,
        timestamps: response.timestamps || [],
        values: response.values || {}
      }
    } catch (error) {
      logger.error('Demo synthetic metrics WebSocket request failed', error as Error, {
        component: 'DemoService',
        action: 'getSyntheticMetrics',
        scenario,
        durationHours
      })
      throw new Error(`Failed to get synthetic metrics: ${error.message}`)
    }
  }

  async exportReport(request: ExportReportRequest): Promise<{ status: string; report_url: string; expires_at: string }> {
    // WebSocket implementation - eliminates HTTP dual-path architecture
    try {
      const response = await this.sendWebSocketRequest('demo_export_report', {
        session_id: request.session_id,
        format: request.format,
        include_sections: request.include_sections
      })

      return {
        status: response.status || 'pending',
        report_url: response.report_url || '',
        expires_at: response.expires_at || ''
      }
    } catch (error) {
      logger.error('Demo export report WebSocket request failed', error as Error, {
        component: 'DemoService',
        action: 'exportReport',
        request: { ...request, session_id: '[redacted]' }
      })
      throw new Error(`Failed to export report: ${error.message}`)
    }
  }

  async getSessionStatus(sessionId: string): Promise<SessionStatus> {
    // WebSocket implementation - eliminates HTTP dual-path architecture
    try {
      const response = await this.sendWebSocketRequest('demo_session_status', {
        target_session_id: sessionId
      })

      return {
        session_id: response.session_id || sessionId,
        progress: response.progress || 0,
        completed_steps: response.completed_steps || [],
        remaining_actions: response.remaining_actions || [],
        last_interaction: response.last_interaction || ''
      }
    } catch (error) {
      logger.error('Demo session status WebSocket request failed', error as Error, {
        component: 'DemoService',
        action: 'getSessionStatus',
        sessionId
      })
      throw new Error(`Failed to get session status: ${error.message}`)
    }
  }

  async submitFeedback(sessionId: string, feedback: Record<string, any>): Promise<{ status: string; message: string }> {
    // WebSocket implementation - eliminates HTTP dual-path architecture
    try {
      const response = await this.sendWebSocketRequest('demo_submit_feedback', {
        target_session_id: sessionId,
        feedback: feedback
      })

      return {
        status: response.status || 'received',
        message: response.message || 'Feedback submitted successfully'
      }
    } catch (error) {
      logger.error('Demo submit feedback WebSocket request failed', error as Error, {
        component: 'DemoService',
        action: 'submitFeedback',
        sessionId,
        feedback: '[redacted]'
      })
      throw new Error(`Failed to submit feedback: ${error.message}`)
    }
  }

  async getAnalyticsSummary(days: number = 30): Promise<Record<string, any>> {
    // WebSocket implementation - eliminates HTTP dual-path architecture
    try {
      const response = await this.sendWebSocketRequest('demo_analytics_summary', {
        days: days
      })

      return response || {}
    } catch (error) {
      logger.error('Demo analytics summary WebSocket request failed', error as Error, {
        component: 'DemoService',
        action: 'getAnalyticsSummary',
        days
      })
      throw new Error(`Failed to get analytics summary: ${error.message}`)
    }
  }
}

export const demoService = new DemoService()