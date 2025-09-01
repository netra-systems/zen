describe('Critical Agent API Direct Tests', () => {
  const BACKEND_BASE_URL = 'http://localhost:8000';

  beforeEach(() => {
    // No frontend setup needed for direct API tests
  });

  it('should call agent API directly using the unified endpoint', () => {
    const agentRequest = {
      message: 'Help me optimize my LLM deployment for better performance and lower costs',
      user_id: 'test-user-id',
      agent_type: 'optimization'
    };

    cy.request({
      method: 'POST',
      url: `${BACKEND_BASE_URL}/api/agents/execute`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mock-jwt-token-for-testing'
      },
      body: agentRequest,
      timeout: 30000
    }).then((response) => {
      // Verify response structure matches current backend format
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('status');
      expect(response.body).to.have.property('result');
      expect(response.body).to.have.property('execution_time');
      expect(response.body).to.have.property('session_id');
      
      // Verify response contains optimization-related content
      if (response.body.result && response.body.result.content) {
        const responseText = response.body.result.content.toLowerCase();
        expect(responseText).to.match(/optimi[sz]e|performance|cost|deployment/);
      }
    });
  });

  it('should handle triage agent requests', () => {
    const triageRequest = {
      message: 'Analyze my current AI infrastructure and suggest improvements',
      user_id: 'test-user-id',
      agent_type: 'triage'
    };

    cy.request({
      method: 'POST',
      url: `${BACKEND_BASE_URL}/api/agents/execute`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mock-jwt-token-for-testing'
      },
      body: triageRequest,
      timeout: 30000
    }).then((response) => {
      // Verify response structure matches current backend format
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('status');
      expect(response.body).to.have.property('result');
      expect(response.body).to.have.property('session_id');
    });
  });

  it('should handle data analysis agent requests', () => {
    const dataRequest = {
      message: 'Compare optimization strategies for GPT-4 vs Claude vs Llama models',
      user_id: 'test-user-id',
      agent_type: 'data'
    };

    cy.request({
      method: 'POST',
      url: `${BACKEND_BASE_URL}/api/agents/execute`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mock-jwt-token-for-testing'
      },
      body: dataRequest,
      timeout: 30000
    }).then((response) => {
      // Verify response structure matches current backend format
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('status');
      expect(response.body).to.have.property('result');
      expect(response.body).to.have.property('session_id');
    });
  });

  it('should handle requests with specific metrics', () => {
    const metricsRequest = {
      message: 'My current setup: 1000 req/s, 500ms latency, $100/hour. How can I improve?',
      user_id: 'test-user-id',
      agent_type: 'optimization'
    };

    cy.request({
      method: 'POST',
      url: `${BACKEND_BASE_URL}/api/agents/execute`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mock-jwt-token-for-testing'
      },
      body: metricsRequest,
      timeout: 30000
    }).then((response) => {
      // Verify response structure and content
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('status');
      expect(response.body).to.have.property('result');
      
      // Should handle metrics in the response
      if (response.body.result && response.body.result.content) {
        const responseText = response.body.result.content.toLowerCase();
        expect(responseText).to.match(/improve|optimi[sz]e|reduce|increase|performance|cost/);
      }
    });
  });

  it('should provide actionable recommendations', () => {
    const actionRequest = {
      message: 'Give me specific steps to reduce my AI costs by 30%',
      user_id: 'test-user-id',
      agent_type: 'optimization'
    };

    cy.request({
      method: 'POST',
      url: `${BACKEND_BASE_URL}/api/agents/execute`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mock-jwt-token-for-testing'
      },
      body: actionRequest,
      timeout: 30000
    }).then((response) => {
      // Verify response structure
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('status');
      expect(response.body).to.have.property('execution_time');
      expect(response.body.execution_time).to.be.a('number');
      expect(response.body.execution_time).to.be.above(0);
      
      // Should contain actionable content
      if (response.body.result && response.body.result.content) {
        const responseText = response.body.result.content.toLowerCase();
        expect(responseText).to.match(/step|implement|action|recommendation|reduce|cost|30/);
      }
    });
  });

  it('should handle multi-step optimization workflow via API', () => {
    // First request
    const initialRequest = {
      message: 'Analyze my current AI infrastructure and suggest improvements',
      user_id: 'test-user-id',
      agent_type: 'optimization'
    };

    cy.request({
      method: 'POST',
      url: `${BACKEND_BASE_URL}/api/agents/execute`,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mock-jwt-token-for-testing'
      },
      body: initialRequest,
      timeout: 30000
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('status');
      
      // Follow-up request with session continuity
      const followUpRequest = {
        message: 'What specific caching strategies do you recommend?',
        user_id: 'test-user-id',
        agent_type: 'optimization',
        session_id: response.body.session_id
      };

      return cy.request({
        method: 'POST',
        url: `${BACKEND_BASE_URL}/api/agents/execute`,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer mock-jwt-token-for-testing'
        },
        body: followUpRequest,
        timeout: 30000
      });
    }).then((response) => {
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('status');
      
      // Should contain caching-related content
      if (response.body.result && response.body.result.content) {
        const responseText = response.body.result.content.toLowerCase();
        expect(responseText).to.match(/cache|caching|memory|redis|strategy/);
      }
    });
  });
});