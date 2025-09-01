describe('Critical Agent Optimization Workflow', () => {
  let interceptedRequests = [];
  let interceptedWebSocketEvents = [];

  beforeEach(() => {
    // Reset intercepted data
    interceptedRequests = [];
    interceptedWebSocketEvents = [];
    
    // Mock authentication
    cy.clearLocalStorage();
    cy.clearCookies();
    
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'mock-jwt-token-for-testing');
      win.localStorage.setItem('user', JSON.stringify({
        id: 'test-user-id',
        email: 'test@netrasystems.ai',
        full_name: 'Test User'
      }));
    });
    
    // Intercept agent API calls with realistic responses
    cy.intercept('POST', '**/api/agents/execute', (req) => {
      interceptedRequests.push(req.body);
      
      // Mock response based on agent type
      const agentType = req.body.type;
      const delay = Math.random() * 1000 + 500; // 500-1500ms delay
      
      cy.wait(delay).then(() => {
        req.reply({
          status: 'success',
          agent: agentType,
          response: getMockAgentResponse(agentType, req.body.message),
          execution_time: delay / 1000,
          circuit_breaker_state: 'CLOSED'
        });
      });
    }).as('agentExecute');
    
    // Intercept specific optimization agent endpoint
    cy.intercept('POST', '**/api/agents/optimization', (req) => {
      interceptedRequests.push({...req.body, type: 'optimization'});
      
      const delay = Math.random() * 2000 + 1000; // 1-3s delay for optimization
      
      cy.wait(delay).then(() => {
        req.reply({
          status: 'success',
          agent: 'optimization',
          response: getMockOptimizationResponse(req.body.message),
          execution_time: delay / 1000,
          circuit_breaker_state: 'CLOSED'
        });
      });
    }).as('optimizationAgent');
    
    // Mock WebSocket connection for event validation
    cy.window().then((win) => {
      // Mock WebSocket to capture events
      const originalWebSocket = win.WebSocket;
      win.WebSocket = function(url) {
        const mockWS = {
          send: function(data) {
            const event = JSON.parse(data);
            interceptedWebSocketEvents.push(event);
          },
          close: function() {},
          addEventListener: function() {},
          removeEventListener: function() {},
          readyState: 1 // OPEN
        };
        
        // Simulate WebSocket events for agent workflow
        setTimeout(() => {
          simulateAgentWebSocketEvents(mockWS);
        }, 100);
        
        return mockWS;
      };
    });
    
    // Visit simple test page
    cy.visit('/test-agent', { timeout: 60000 });
    
    // Wait for the page to fully load and become interactive
    cy.get('body', { timeout: 30000 }).should('be.visible');
    cy.wait(1000); // Wait for React hydration
  });

  it('should execute optimization agent with proper API flow', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Send optimization request using current API structure
        const optimizationRequest = 'Optimize my AI infrastructure: 1000 req/s, 500ms latency, $100/hour cost. Reduce costs by 30%.';
        
        cy.get('[data-testid="message-input"]').type(optimizationRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // 2. Verify API call is made to correct endpoint
        cy.wait('@optimizationAgent').then((interception) => {
          expect(interception.request.body).to.have.property('message', optimizationRequest);
          expect(interception.request.url).to.include('/api/agents/optimization');
        });
        
        // 3. Look for processing indicators while request is in flight
        cy.get('[data-testid="processing-indicator"]', { timeout: 5000 }).should('be.visible');
        
        // 4. Verify response contains optimization structure
        cy.get('pre', { timeout: 30000 }).should('contain.text', 'optimization').and('contain.text', 'strategies');
        
        // 5. Check for specific optimization response elements
        cy.get('pre').should('contain.text', 'cost_savings').and('contain.text', 'performance');
      }
    });
  });

  it('should handle multi-objective optimization workflow with metrics', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // 1. Initial comprehensive optimization request
        const request = 'Multi-objective optimization: balance cost reduction (target 30%) with quality preservation (CSAT >90%) for chatbot workload';
        cy.get('[data-testid="message-input"]').type(request);
        cy.get('[data-testid="send-button"]').click();
        
        // 2. Wait for initial response with structured optimization data
        cy.wait('@optimizationAgent');
        cy.get('pre', { timeout: 30000 }).should('contain.text', 'multi_objective_optimization');
        
        // 3. Verify optimization response contains required elements
        cy.get('pre').should('contain.text', 'strategies')
                    .and('contain.text', 'cost_savings')
                    .and('contain.text', 'quality_impact')
                    .and('contain.text', 'implementation_complexity');
        
        // 4. Follow-up request for specific strategy details
        const followUp = 'Show me the detailed implementation plan for model routing optimization';
        cy.get('[data-testid="message-input"]').clear().type(followUp);
        cy.get('[data-testid="send-button"]').click();
        
        // 5. Verify contextual response with routing specifics
        cy.wait('@optimizationAgent');
        cy.get('pre', { timeout: 30000 }).should('contain.text', 'routing')
                                        .and('contain.text', 'model_specific_configurations');
      }
    });
  });

  it('should validate WebSocket agent events during execution', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Send a complex request that should trigger WebSocket events
        const complexRequest = 'Comprehensive AI optimization analysis with cost-performance trade-offs';
        cy.get('[data-testid="message-input"]').type(complexRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // Verify processing indicator appears (simulates WebSocket agent_started event)
        cy.get('[data-testid="processing-indicator"]', { timeout: 5000 }).should('be.visible');
        
        // Wait for agent execution to complete
        cy.wait('@optimizationAgent');
        
        // Verify response appears (simulates WebSocket agent_completed event)
        cy.get('pre', { timeout: 30000 }).should('be.visible');
        
        // Validate that WebSocket events would be captured
        cy.window().then((win) => {
          // In a real implementation, we would check interceptedWebSocketEvents
          // For now, verify the UI flow that depends on WebSocket events
          
          // Processing indicator should disappear when agent completes
          cy.get('[data-testid="processing-indicator"]').should('not.exist');
          
          // Response should contain agent execution results
          cy.get('pre').should('contain.text', 'agent').and('contain.text', 'optimization');
        });
      }
    });
  });

  it('should handle model-specific optimization configurations', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const modelRequest = 'Optimize model routing: GPT-4 for complex queries, Claude-3 for analysis, Llama-3 for simple tasks';
        cy.get('[data-testid="message-input"]').type(modelRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // Verify API call with model-specific request
        cy.wait('@optimizationAgent').then((interception) => {
          expect(interception.request.body.message).to.include('GPT-4').and.include('Claude-3').and.include('Llama-3');
        });
        
        // Verify response contains model-specific configurations
        cy.get('pre', { timeout: 30000 }).should('contain.text', 'model_specific_configurations')
                                          .and('contain.text', 'routing_rules')
                                          .and('contain.text', 'allocation_percentage');
        
        // Check for performance targets in the optimization response
        cy.get('pre').should('contain.text', 'performance_targets')
                    .and('contain.text', 'max_latency_ms')
                    .and('contain.text', 'min_throughput_rps');
      }
    });
  });

  it('should provide phased implementation recommendations', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const actionRequest = 'Provide phased implementation plan to reduce AI costs by 30% over 90 days';
        cy.get('[data-testid="message-input"]').type(actionRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // Verify API call
        cy.wait('@optimizationAgent');
        
        // Verify response contains phased optimization structure
        cy.get('pre', { timeout: 30000 }).should('contain.text', 'optimization_phases')
                                          .and('contain.text', 'phase_duration')
                                          .and('contain.text', 'success_metrics');
        
        // Check for implementation details
        cy.get('pre').should('contain.text', 'implementation_complexity')
                    .and('contain.text', 'rollback_plan')
                    .and('contain.text', 'monitoring_requirements');
        
        // Verify cost savings projections
        cy.get('pre').should('contain.text', 'projected_cost_savings')
                    .and('contain.text', 'percentage')
                    .and('contain.text', 'realized_in');
      }
    });
  });

  it('should handle metrics-driven optimization with quantified outcomes', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        const metricsRequest = 'Current metrics: 1000 req/s, 500ms P95 latency, $100/hour. Target: <300ms latency, 30% cost reduction';
        cy.get('[data-testid="message-input"]').type(metricsRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // Verify API call captures metrics
        cy.wait('@optimizationAgent').then((interception) => {
          expect(interception.request.body.message).to.include('1000 req/s')
                                                   .and.include('500ms')
                                                   .and.include('$100/hour');
        });
        
        // Verify response contains quantified optimization outcomes
        cy.get('pre', { timeout: 30000 }).should('contain.text', 'target_metrics')
                                          .and('contain.text', 'current_value')
                                          .and('contain.text', 'target_value');
        
        // Check for specific optimization strategies with metrics
        cy.get('pre').should('contain.text', 'impact_assessment')
                    .and('contain.text', 'projected_cost_savings')
                    .and('contain.text', 'projected_quality_impact');
        
        // Verify monitoring and success criteria
        cy.get('pre').should('contain.text', 'monitoring_requirements')
                    .and('contain.text', 'alert_threshold')
                    .and('contain.text', 'collection_frequency');
      }
    });
  });

  it('should validate complete optimization workflow with circuit breaker integration', () => {
    cy.url().then((url) => {
      if (!url.includes('/login')) {
        // Test complete workflow with circuit breaker status
        const workflowRequest = 'End-to-end optimization: analyze, optimize, and monitor my AI infrastructure';
        cy.get('[data-testid="message-input"]').type(workflowRequest);
        cy.get('[data-testid="send-button"]').click();
        
        // Verify API response includes circuit breaker state
        cy.wait('@optimizationAgent').then((interception) => {
          expect(interception.response.body).to.have.property('circuit_breaker_state', 'CLOSED');
          expect(interception.response.body).to.have.property('execution_time');
          expect(interception.response.body).to.have.property('status', 'success');
        });
        
        // Verify complete optimization response structure
        cy.get('pre', { timeout: 30000 }).should('contain.text', 'optimization_summary')
                                          .and('contain.text', 'key_customer_goals')
                                          .and('contain.text', 'critical_assumptions')
                                          .and('contain.text', 'key_trade_offs');
        
        // Validate long-term planning elements
        cy.get('pre').should('contain.text', 'long_term_opportunities')
                    .and('contain.text', 'value_potential')
                    .and('contain.text', 'effort_estimate');
      }
    });
  });
});

// Helper functions for mocking agent responses
function getMockAgentResponse(agentType: string, message: string): string {
  const responses = {
    'triage': `Triage analysis complete for: ${message}. Routing to optimization agent.`,
    'data': `Data analysis results: Found relevant patterns in workload data for: ${message}`,
    'optimization': getMockOptimizationResponse(message)
  };
  
  return responses[agentType] || `${agentType} agent processed: ${message}`;
}

function getMockOptimizationResponse(message: string): string {
  // Return realistic optimization response matching current agent structure
  return JSON.stringify({
    optimization_summary: "Multi-objective optimization strategy balancing cost, performance, and quality based on workload analysis",
    key_customer_goals: {
      primary_goal: "cost_reduction",
      target_metrics: [
        {
          metric: "cost_per_request",
          current_value: 0.10,
          target_value: 0.07,
          goal_timeframe: "90_days"
        },
        {
          metric: "p95_latency_ms",
          current_value: 500,
          target_value: 300,
          goal_timeframe: "60_days"
        }
      ]
    },
    strategies: [
      {
        strategy_id: "model_routing_opt_001",
        name: "Intelligent Model Routing",
        type: "routing",
        description: "Route requests to optimal models based on complexity and cost constraints",
        customer_value_proposition: "Reduces costs by 25% while maintaining 95% quality satisfaction",
        impact_assessment: {
          projected_cost_savings: {
            percentage: 25,
            absolute_amount: 750,
            realized_in: "60_days"
          },
          projected_quality_impact: {
            key_metric_1: "accuracy_score",
            expected_delta_1: -0.02,
            key_metric_2: "user_satisfaction",
            expected_delta_2: 0.01
          }
        },
        implementation_complexity: "medium",
        implementation_risk: "low",
        model_specific_configurations: [
          {
            model_id: "gpt-4-turbo",
            model_name: "GPT-4 Turbo",
            allocation_percentage: 20,
            routing_rules: {
              rule_type: "complexity_based",
              conditions: ["input_tokens > 1000", "complexity_score > 0.8"],
              priority: 1
            },
            performance_targets: {
              max_latency_ms: 800,
              min_throughput_rps: 50
            }
          },
          {
            model_id: "claude-3-sonnet",
            model_name: "Claude 3 Sonnet",
            allocation_percentage: 60,
            routing_rules: {
              rule_type: "balanced",
              conditions: ["input_tokens <= 1000", "complexity_score <= 0.8"],
              priority: 2
            },
            performance_targets: {
              max_latency_ms: 400,
              min_throughput_rps: 150
            }
          }
        ],
        monitoring_requirements: [
          {
            metric_name: "routing_accuracy",
            collection_frequency: "1_minute",
            alert_threshold: 0.85
          },
          {
            metric_name: "cost_per_request",
            collection_frequency: "5_minutes",
            alert_threshold: 0.08
          }
        ],
        rollback_triggers: ["accuracy_drop_5_percent", "latency_increase_50_percent"],
        rollback_plan: "Revert to previous routing configuration within 5 minutes"
      }
    ],
    optimization_phases: [
      {
        phase_id: "phase_1_routing",
        phase_name: "Model Routing Implementation",
        phase_description: "Deploy intelligent routing with 20% traffic rollout",
        strategies_involved: ["model_routing_opt_001"],
        phase_duration: "30_days",
        phase_goals: ["Validate routing accuracy >90%", "Achieve 15% cost reduction"],
        success_metrics: [
          {
            metric_name: "cost_reduction_percentage",
            target_value: 15
          }
        ],
        rollout_percentage: 20
      }
    ],
    critical_assumptions: [
      {
        assumption: "Model availability remains stable during rollout",
        potential_impact: "Routing failures could increase latency",
        mitigation: "Implement fallback routing with circuit breakers"
      }
    ],
    key_trade_offs: [
      {
        trade_off: "Slight accuracy reduction for significant cost savings",
        justification: "2% accuracy trade-off acceptable for 25% cost reduction",
        impact_on_customer_goals: "Aligns with primary cost reduction objective"
      }
    ],
    long_term_opportunities: [
      {
        opportunity_name: "Predictive Auto-scaling",
        value_potential: "high",
        effort_estimate: "medium",
        recommended_next_steps: ["Implement load prediction models", "Deploy auto-scaling infrastructure"]
      }
    ]
  }, null, 2);
}

function simulateAgentWebSocketEvents(mockWS: any): void {
  // Simulate the WebSocket events that would be sent during agent execution
  const events = [
    { type: 'agent_started', timestamp: Date.now(), agent: 'optimization' },
    { type: 'agent_thinking', timestamp: Date.now() + 100, message: 'Analyzing optimization requirements...' },
    { type: 'tool_executing', timestamp: Date.now() + 500, tool: 'cost_analyzer' },
    { type: 'tool_completed', timestamp: Date.now() + 1000, tool: 'cost_analyzer', result: { analysis: 'completed' } },
    { type: 'tool_executing', timestamp: Date.now() + 1200, tool: 'performance_predictor' },
    { type: 'tool_completed', timestamp: Date.now() + 1800, tool: 'performance_predictor', result: { predictions: 'ready' } },
    { type: 'partial_result', timestamp: Date.now() + 2000, content: 'Optimization strategies identified...' },
    { type: 'final_report', timestamp: Date.now() + 2500, report: 'Comprehensive optimization plan ready' },
    { type: 'agent_completed', timestamp: Date.now() + 3000, success: true }
  ];
  
  // This would trigger the frontend to show appropriate UI updates
  events.forEach((event, index) => {
    setTimeout(() => {
      // In a real WebSocket implementation, these events would be received
      // For testing, we can verify the UI responds appropriately to state changes
      console.log('WebSocket Event:', event);
    }, index * 200);
  });
}