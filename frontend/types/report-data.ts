/**
 * Canonical ReportData Types - Single Source of Truth
 * Comprehensive type definitions for Netra Apex report data structures
 * Business Value: All segments - ensures type consistency across report components
 */

// ============================================
// Core Report Data Interface
// ============================================

export interface ReportData {
  finalReport?: {
    executive_summary?: string;
    cost_analysis?: {
      total_savings?: number;
      current_costs?: Record<string, number>;
      projected_costs?: Record<string, number>;
      monthly_savings?: number;
      total_current?: number;
      total_projected?: number;
    };
    performance_comparison?: {
      improvement_percentage?: number;
      response_time_current?: string | number;
      response_time_projected?: string | number;
      response_time_improvement?: string | number;
      throughput_current?: string | number;
      throughput_projected?: string | number;
      throughput_improvement?: string | number;
      quality_score_current?: number;
      quality_score_projected?: number;
      quality_improvement?: number;
      quality_current?: string | number;
      quality_projected?: string | number;
    };
    confidence_scores?: {
      overall?: number;
    };
    recommendations?: RecommendationItem[];
    actionPlan?: ActionPlanItem[];
    technical_details?: any;
  };
  completedAgents?: AgentTimelineItem[];
}

// ============================================
// Supporting Interfaces
// ============================================

export interface RecommendationItem {
  id?: string;
  title?: string;
  description?: string;
  impact?: 'high' | 'medium' | 'low';
  effort?: 'high' | 'medium' | 'low';
  category?: string;
  confidence_score?: number;
  implementation_steps?: string[];
  metrics?: {
    potential_savings?: number;
    latency_reduction?: number;
    throughput_increase?: number;
  };
}

export interface ActionPlanItem {
  id?: string;
  step_number?: number;
  description?: string;
  title?: string;
  command?: string;
  expected_outcome?: string;
  dependencies?: string[];
  estimated_duration?: string;
  effort_estimate?: string;
}

export interface AgentTimelineItem {
  agentName?: string;
  duration?: number;
  metrics?: {
    tokens_used?: number;
    tools_executed?: number;
    cache_hits?: number;
    cache_misses?: number;
  };
}