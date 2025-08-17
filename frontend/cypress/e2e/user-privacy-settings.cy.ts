/**
 * User Privacy Settings E2E Tests
 * Split from user-profile-settings.cy.ts for 300-line compliance
 * 
 * BVJ: Enterprise segment - Privacy compliance (GDPR, CCPA) = Enterprise requirement
 * Value Impact: Data export/deletion compliance = regulatory requirement satisfaction
 */

describe('User Privacy Settings', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    cy.visit('/');
  });

  it('should request data export successfully', () => {
    // Navigate to privacy settings
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Request data export
    cy.get('button').contains('Export My Data').click();

    // Mock export request
    cy.intercept('POST', '/api/users/export-data', {
      statusCode: 202,
      body: {
        export_id: 'export-123',
        status: 'processing',
        message: 'Your data export has been initiated. You will receive an email when it is ready.'
      }
    }).as('requestExport');

    cy.wait('@requestExport');

    // Verify export initiated
    cy.contains('Your data export has been initiated').should('be.visible');
    cy.contains('You will receive an email when it is ready').should('be.visible');
  });

  it('should check export status and download', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Mock export status check
    cy.intercept('GET', '/api/users/export-data/export-123/status', {
      statusCode: 200,
      body: {
        export_id: 'export-123',
        status: 'completed',
        download_url: '/api/users/export-data/export-123/download',
        expires_at: new Date(Date.now() + 86400000).toISOString()
      }
    }).as('exportStatus');

    // Trigger status check
    cy.get('button').contains('Check Export Status').click();
    cy.wait('@exportStatus');

    // Verify download is available
    cy.contains('Your data export is ready').should('be.visible');
    cy.get('a').contains('Download Export').should('have.attr', 'href', '/api/users/export-data/export-123/download');

    // Verify expiration notice
    cy.contains('expires in 24 hours').should('be.visible');
  });

  it('should handle export processing status', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Mock export still processing
    cy.intercept('GET', '/api/users/export-data/export-456/status', {
      statusCode: 200,
      body: {
        export_id: 'export-456',
        status: 'processing',
        progress: 65,
        estimated_completion: new Date(Date.now() + 300000).toISOString()
      }
    }).as('exportProcessing');

    cy.get('button').contains('Check Export Status').click();
    cy.wait('@exportProcessing');

    // Verify processing status
    cy.contains('Export in progress: 65%').should('be.visible');
    cy.contains('Estimated completion: 5 minutes').should('be.visible');
  });

  it('should handle export errors', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Mock export error
    cy.intercept('POST', '/api/users/export-data', {
      statusCode: 429,
      body: {
        error: 'Export request limit exceeded. You can request one export per 24 hours.',
        retry_after: new Date(Date.now() + 3600000).toISOString()
      }
    }).as('exportError');

    cy.get('button').contains('Export My Data').click();
    cy.wait('@exportError');

    // Verify error message
    cy.contains('Export request limit exceeded').should('be.visible');
    cy.contains('You can request another export in 1 hour').should('be.visible');
  });

  it('should initiate account deletion with confirmation', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Test account deletion
    cy.get('button').contains('Delete My Account').click();

    // Verify warning modal
    cy.contains('This action cannot be undone').should('be.visible');
    cy.contains('All your data will be permanently deleted').should('be.visible');
    cy.contains('API keys will be revoked').should('be.visible');
    cy.contains('Chat history will be erased').should('be.visible');

    // Type confirmation
    cy.get('input[placeholder="Type DELETE to confirm"]').type('DELETE');

    // Verify confirmation button is enabled
    cy.get('button').contains('Delete Account').should('not.be.disabled');
  });

  it('should handle account deletion confirmation mismatch', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    cy.get('button').contains('Delete My Account').click();

    // Type incorrect confirmation
    cy.get('input[placeholder="Type DELETE to confirm"]').type('delete');

    // Verify button remains disabled
    cy.get('button').contains('Delete Account').should('be.disabled');

    // Type partial confirmation
    cy.get('input[placeholder="Type DELETE to confirm"]').clear().type('DEL');
    cy.get('button').contains('Delete Account').should('be.disabled');
  });

  it('should process account deletion successfully', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    cy.get('button').contains('Delete My Account').click();
    cy.get('input[placeholder="Type DELETE to confirm"]').type('DELETE');

    // Mock deletion endpoint
    cy.intercept('DELETE', '/api/users/account', {
      statusCode: 200,
      body: {
        success: true,
        message: 'Account scheduled for deletion'
      }
    }).as('deleteAccount');

    // Confirm deletion
    cy.get('button').contains('Delete Account').click();
    cy.wait('@deleteAccount');

    // Verify deletion scheduled
    cy.contains('Account scheduled for deletion').should('be.visible');
    cy.contains('You will be logged out shortly').should('be.visible');

    // Verify logout after deletion
    cy.wait(2000);
    cy.url().should('include', '/login');
  });

  it('should handle account deletion errors', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    cy.get('button').contains('Delete My Account').click();
    cy.get('input[placeholder="Type DELETE to confirm"]').type('DELETE');

    // Mock deletion error
    cy.intercept('DELETE', '/api/users/account', {
      statusCode: 400,
      body: {
        error: 'Cannot delete account with active subscriptions. Please cancel all subscriptions first.'
      }
    }).as('deleteAccountError');

    cy.get('button').contains('Delete Account').click();
    cy.wait('@deleteAccountError');

    // Verify error message
    cy.contains('Cannot delete account with active subscriptions').should('be.visible');
    cy.contains('Please cancel all subscriptions first').should('be.visible');
  });

  it('should display privacy policy and data usage information', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Verify privacy information is displayed
    cy.contains('Data Collection & Usage').should('be.visible');
    cy.contains('We collect the following data to provide our services:').should('be.visible');
    
    // Check data types listed
    cy.contains('Profile information (name, email)').should('be.visible');
    cy.contains('Chat messages and conversation history').should('be.visible');
    cy.contains('API usage and optimization metrics').should('be.visible');
    cy.contains('System logs and error reports').should('be.visible');

    // Verify privacy policy link
    cy.get('a').contains('Privacy Policy').should('have.attr', 'href').and('include', '/privacy');
    cy.get('a').contains('Terms of Service').should('have.attr', 'href').and('include', '/terms');
  });

  it('should handle data retention preferences', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Mock current retention settings
    cy.intercept('GET', '/api/users/data-retention', {
      statusCode: 200,
      body: {
        chat_history_retention: 'indefinite',
        logs_retention: '30_days',
        metrics_retention: '1_year'
      }
    }).as('getRetention');

    cy.get('button').contains('Data Retention').click();
    cy.wait('@getRetention');

    // Update retention preferences
    cy.get('select[name="chat_history_retention"]').select('1_year');
    cy.get('select[name="logs_retention"]').select('7_days');

    // Mock update endpoint
    cy.intercept('PATCH', '/api/users/data-retention', {
      statusCode: 200,
      body: {
        chat_history_retention: '1_year',
        logs_retention: '7_days',
        metrics_retention: '1_year'
      }
    }).as('updateRetention');

    cy.get('button').contains('Save Retention Settings').click();
    cy.wait('@updateRetention');

    // Verify success
    cy.contains('Data retention preferences updated').should('be.visible');
  });

  it('should allow data portability requests', () => {
    cy.visit('/settings');
    cy.get('button').contains('Privacy').click();

    // Request specific data types for export
    cy.get('button').contains('Custom Export').click();

    // Select data types
    cy.get('input[name="include_profile"]').check();
    cy.get('input[name="include_chat_history"]').check();
    cy.get('input[name="include_api_keys"]').uncheck();
    cy.get('input[name="include_metrics"]').check();

    // Select export format
    cy.get('select[name="export_format"]').select('json');

    // Mock custom export
    cy.intercept('POST', '/api/users/export-data/custom', {
      statusCode: 202,
      body: {
        export_id: 'custom-export-789',
        data_types: ['profile', 'chat_history', 'metrics'],
        format: 'json',
        status: 'processing'
      }
    }).as('customExport');

    cy.get('button').contains('Request Custom Export').click();
    cy.wait('@customExport');

    // Verify custom export initiated
    cy.contains('Custom export requested').should('be.visible');
    cy.contains('Selected data: Profile, Chat History, Metrics').should('be.visible');
  });
});