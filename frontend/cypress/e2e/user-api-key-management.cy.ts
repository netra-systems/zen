describe('User API Key Management', () => {
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
  });

  it('should add new API key successfully', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock initial API keys
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: { keys: [] }
    }).as('getApiKeys');

    cy.wait('@getApiKeys');

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

  it('should validate API key input fields', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();
    cy.get('button').contains('Add API Key').click();

    // Test empty name validation
    cy.get('button').contains('Save Key').click();
    cy.contains('Key name is required').should('be.visible');

    // Test invalid key format validation
    cy.get('input[name="key_name"]').type('Test Key');
    cy.get('input[name="api_key"]').type('invalid-key-format');
    cy.get('button').contains('Save Key').click();
    cy.contains('Invalid API key format').should('be.visible');

    // Test OpenAI key format
    cy.get('select[name="provider"]').select('openai');
    cy.get('input[name="api_key"]').clear().type('sk-1234567890abcdef');
    cy.get('button').contains('Save Key').click();
    // Should not show format error for valid OpenAI key
    cy.contains('Invalid API key format').should('not.exist');
  });

  it('should test API key validation', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock existing key
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [{
          id: 'key-1',
          name: 'Test Key',
          provider: 'openai',
          last_used: null,
          created_at: '2024-01-01T00:00:00Z',
          masked_value: 'sk-...12345'
        }]
      }
    }).as('getApiKeys');

    cy.wait('@getApiKeys');

    // Test key validation
    cy.get('button').contains('Test Key').last().click();

    // Mock validation endpoint
    cy.intercept('POST', '/api/users/api-keys/key-1/validate', {
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

  it('should handle invalid API key validation', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock existing key
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [{
          id: 'key-1',
          name: 'Invalid Key',
          provider: 'openai',
          last_used: null,
          created_at: '2024-01-01T00:00:00Z',
          masked_value: 'sk-...invalid'
        }]
      }
    }).as('getApiKeys');

    cy.wait('@getApiKeys');

    // Test invalid key validation
    cy.get('button').contains('Test Key').click();

    // Mock validation failure
    cy.intercept('POST', '/api/users/api-keys/key-1/validate', {
      statusCode: 400,
      body: {
        valid: false,
        error: 'Invalid API key or insufficient permissions'
      }
    }).as('validateKeyFail');

    cy.wait('@validateKeyFail');

    // Verify validation failure
    cy.contains('Key validation failed').should('be.visible');
    cy.contains('Invalid API key or insufficient permissions').should('be.visible');
  });

  it('should delete API key with confirmation', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock existing key
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [{
          id: 'key-1',
          name: 'Test API Key',
          provider: 'openai',
          last_used: null,
          created_at: '2024-01-01T00:00:00Z',
          masked_value: 'sk-...12345'
        }]
      }
    }).as('getApiKeys');

    cy.wait('@getApiKeys');

    // Delete API key
    cy.contains('Test API Key').parent().find('button[aria-label="Delete key"]').click();
    
    // Confirm deletion
    cy.contains('Are you sure you want to delete this API key?').should('be.visible');

    // Mock delete endpoint
    cy.intercept('DELETE', '/api/users/api-keys/key-1', {
      statusCode: 204
    }).as('deleteApiKey');

    cy.get('button').contains('Delete').click();
    cy.wait('@deleteApiKey');

    // Verify key is removed
    cy.contains('Test API Key').should('not.exist');
    cy.contains('API key deleted successfully').should('be.visible');
  });

  it('should handle API key operations with rate limiting', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Test rate limiting on key validation
    cy.intercept('POST', '/api/users/api-keys/*/validate', {
      statusCode: 429,
      body: {
        error: 'Rate limit exceeded. Please try again in 60 seconds.'
      }
    }).as('rateLimitValidation');

    // Mock existing key
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [{
          id: 'key-1',
          name: 'Test Key',
          provider: 'openai',
          last_used: null,
          created_at: '2024-01-01T00:00:00Z',
          masked_value: 'sk-...12345'
        }]
      }
    }).as('getApiKeys');

    cy.wait('@getApiKeys');

    // Try to validate key
    cy.get('button').contains('Test Key').click();
    cy.wait('@rateLimitValidation');

    // Verify rate limit message
    cy.contains('Rate limit exceeded').should('be.visible');
    cy.contains('Please try again in 60 seconds').should('be.visible');
  });

  it('should display API key usage statistics', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock API keys with usage stats
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [{
          id: 'key-1',
          name: 'Production Key',
          provider: 'openai',
          last_used: '2024-12-01T10:00:00Z',
          created_at: '2024-11-01T00:00:00Z',
          masked_value: 'sk-...abc123',
          usage_stats: {
            requests_this_month: 15000,
            cost_this_month: 45.67,
            average_response_time: 1.2
          }
        }]
      }
    }).as('getApiKeysWithStats');

    cy.wait('@getApiKeysWithStats');

    // Verify usage statistics are displayed
    cy.contains('15,000 requests this month').should('be.visible');
    cy.contains('$45.67 cost this month').should('be.visible');
    cy.contains('1.2s avg response time').should('be.visible');
  });

  it('should support multiple provider types', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();
    cy.get('button').contains('Add API Key').click();

    // Test different provider options
    const providers = [
      { value: 'openai', label: 'OpenAI', keyFormat: 'sk-' },
      { value: 'anthropic', label: 'Anthropic', keyFormat: 'sk-ant-' },
      { value: 'cohere', label: 'Cohere', keyFormat: 'co-' },
      { value: 'huggingface', label: 'Hugging Face', keyFormat: 'hf_' }
    ];

    providers.forEach(provider => {
      cy.get('select[name="provider"]').select(provider.value);
      cy.get('select[name="provider"] option:selected').should('contain', provider.label);
      
      // Verify key format hint is updated
      cy.contains(`Key should start with ${provider.keyFormat}`).should('be.visible');
    });
  });

  it('should handle API key encryption and security', () => {
    cy.visit('/settings');
    cy.get('button').contains('API Keys').click();

    // Mock encrypted key storage
    cy.intercept('GET', '/api/users/api-keys', {
      statusCode: 200,
      body: {
        keys: [{
          id: 'key-1',
          name: 'Secure Key',
          provider: 'openai',
          last_used: '2024-12-01T10:00:00Z',
          created_at: '2024-11-01T00:00:00Z',
          masked_value: 'sk-...abc123',
          encrypted: true,
          last_rotated: '2024-11-15T00:00:00Z'
        }]
      }
    }).as('getSecureApiKeys');

    cy.wait('@getSecureApiKeys');

    // Verify security indicators
    cy.contains('🔒 Encrypted').should('be.visible');
    cy.contains('Last rotated: November 15, 2024').should('be.visible');

    // Test key rotation
    cy.get('button').contains('Rotate Key').click();
    cy.contains('This will generate a new key and invalidate the old one').should('be.visible');
  });
});
