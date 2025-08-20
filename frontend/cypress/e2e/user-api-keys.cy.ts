/**
 * User API Keys & Credentials E2E Tests
 * Split from user-profile-settings.cy.ts for 450-line compliance
 * 
 * BVJ: Growth & Enterprise - API key management drives platform adoption
 * Value Impact: Secure credential management = customer trust
 */

describe('User API Keys & Credentials Management', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should manage API keys and credentials', () => {
    // Navigate to API settings
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock API keys endpoint
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [
          {
            id: 'key-1',
            name: 'Production Key',
            provider: 'openai',
            last_used: '2024-12-01T10:00:00Z',
            created_at: '2024-11-01T00:00:00Z',
            masked_value: 'sk-...abc123'
          },
          {
            id: 'key-2',
            name: 'Development Key',
            provider: 'anthropic',
            last_used: null,
            created_at: '2024-11-15T00:00:00Z',
            masked_value: 'sk-ant-...xyz789'
          }
        ]
      }
    }).as('getApiKeys');

    cy.wait('@getApiKeys');

    // Verify existing keys are displayed
    cy.contains('Production Key').should('be.visible');
    cy.contains('OpenAI').should('be.visible');
    cy.contains('sk-...abc123').should('be.visible');
    cy.contains('Last used: December 1, 2024').should('be.visible');

    cy.contains('Development Key').should('be.visible');
    cy.contains('Anthropic').should('be.visible');
    cy.contains('Never used').should('be.visible');

    // Add new API key
    cy.get('button').contains('Add API Key').click();
    
    // Fill in new key details
    cy.get('input[name="key_name"]').type('Test API Key');
    cy.get('select[name="provider"]').select('openai');
    cy.get('input[name="api_key"]').type('sk-test-key-12345');

    // Mock add key endpoint
    cy.intercept('POST', '/api/users/api-keys', {
      statusCode: 201,
      body: {
        id: 'key-3',
        name: 'Test API Key',
        provider: 'openai',
        last_used: null,
        created_at: new Date().toISOString(),
        masked_value: 'sk-...12345'
      }
    }).as('addApiKey');

    // Save new key
    cy.get('button').contains('Save Key').click();
    cy.wait('@addApiKey');

    // Verify success message
    cy.contains('API key added successfully').should('be.visible');

    // Verify new key appears in list
    cy.contains('Test API Key').should('be.visible');
  });

  it('should validate and test API keys', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock existing keys
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [{
          id: 'key-test',
          name: 'Test Key',
          provider: 'openai',
          last_used: null,
          created_at: new Date().toISOString(),
          masked_value: 'sk-...12345'
        }]
      }
    }).as('getTestKeys');

    cy.wait('@getTestKeys');

    // Test key validation
    cy.get('button').contains('Test Key').last().click();

    // Mock validation endpoint
    cy.intercept('POST', '/api/users/api-keys/key-test/validate', {
      statusCode: 200,
      body: {
        valid: true,
        model_access: ['gpt-4', 'gpt-3.5-turbo'],
        rate_limit: '10000 requests/day'
      }
    }).as('validateKey');

    cy.wait('@validateKey');

    // Verify validation result
    cy.contains('Key is valid').should('be.visible');
    cy.contains('Models: gpt-4, gpt-3.5-turbo').should('be.visible');
    cy.contains('Rate limit: 10000 requests/day').should('be.visible');
  });

  it('should handle invalid API keys', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Add invalid key
    cy.get('button').contains('Add API Key').click();
    cy.get('input[name="key_name"]').type('Invalid Key');
    cy.get('select[name="provider"]').select('openai');
    cy.get('input[name="api_key"]').type('invalid-key-format');

    // Mock validation error
    cy.intercept('POST', '/api/users/api-keys', {
      statusCode: 400,
      body: {
        error: 'Invalid API key format',
        field: 'api_key'
      }
    }).as('invalidKey');

    cy.get('button').contains('Save Key').click();
    cy.wait('@invalidKey');

    // Verify error message
    cy.contains('Invalid API key format').should('be.visible');
  });

  it('should delete API keys with confirmation', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock keys for deletion
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [{
          id: 'key-delete',
          name: 'Delete Me Key',
          provider: 'openai',
          last_used: null,
          created_at: new Date().toISOString(),
          masked_value: 'sk-...delete'
        }]
      }
    }).as('getDeleteKeys');

    cy.wait('@getDeleteKeys');

    // Delete API key
    cy.contains('Delete Me Key').parent().find('button[aria-label="Delete key"]').click();
    
    // Confirm deletion
    cy.contains('Are you sure you want to delete this API key?').should('be.visible');

    // Mock delete endpoint
    cy.intercept('DELETE', '/api/users/api-keys/key-delete', {
      statusCode: 204
    }).as('deleteApiKey');

    cy.get('button').contains('Delete').click();
    cy.wait('@deleteApiKey');

    // Verify key is removed
    cy.contains('Delete Me Key').should('not.exist');
    cy.contains('API key deleted successfully').should('be.visible');
  });

  it('should handle API key usage statistics', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock keys with usage stats
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [{
          id: 'key-stats',
          name: 'Stats Key',
          provider: 'openai',
          last_used: '2024-12-01T10:00:00Z',
          created_at: '2024-11-01T00:00:00Z',
          masked_value: 'sk-...stats',
          usage_stats: {
            requests_today: 150,
            requests_month: 4500,
            cost_month: 89.50
          }
        }]
      }
    }).as('getStatsKeys');

    cy.wait('@getStatsKeys');

    // View usage statistics
    cy.contains('Stats Key').parent().find('button').contains('Usage').click();

    // Verify stats display
    cy.contains('150 requests today').should('be.visible');
    cy.contains('4,500 requests this month').should('be.visible');
    cy.contains('$89.50 cost this month').should('be.visible');
  });

  it('should export API key list', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Export keys (excluding sensitive data)
    cy.get('button').contains('Export').click();

    // Mock export endpoint
    cy.intercept('GET', '/api/users/api-keys/export', {
      statusCode: 200,
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=api-keys.csv'
      },
      body: 'name,provider,created_at,last_used\nProduction Key,openai,2024-11-01,2024-12-01'
    }).as('exportKeys');

    cy.wait('@exportKeys');

    // Verify download initiated
    cy.contains('API keys exported successfully').should('be.visible');
  });
});