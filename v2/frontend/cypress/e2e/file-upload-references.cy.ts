import { Message, WebSocketMessage } from '@/types';

describe('File Upload and Reference Management', () => {
  beforeEach(() => {
    // Setup authenticated state
    cy.window().then((win) => {
      win.localStorage.setItem('jwt_token', 'test-jwt-token');
    });

    // Mock references endpoint
    cy.intercept('GET', '/api/references', {
      statusCode: 200,
      body: []
    }).as('getReferences');

    cy.visit('/chat');
  });

  it('should upload a file and create a reference', () => {
    // Open references panel - use a more generic selector
    cy.get('button').contains('References').click({ timeout: 10000 });
    
    // Verify empty state
    cy.contains('No references uploaded yet').should('be.visible');
    
    // Create test file
    const fileName = 'optimization-guide.pdf';
    const fileContent = 'LLM Optimization Best Practices';
    const file = new File([fileContent], fileName, { type: 'application/pdf' });

    // Mock file upload endpoint
    cy.intercept('POST', '/api/references/upload', {
      statusCode: 201,
      body: {
        id: 'ref-1',
        filename: fileName,
        content_type: 'application/pdf',
        size: fileContent.length,
        status: 'processing',
        created_at: new Date().toISOString()
      }
    }).as('uploadFile');

    // Mock processing status
    cy.intercept('GET', '/api/references/ref-1/status', {
      statusCode: 200,
      body: {
        id: 'ref-1',
        status: 'completed',
        metadata: {
          page_count: 10,
          word_count: 5000,
          embeddings_generated: true
        }
      }
    }).as('getProcessingStatus');

    // Upload file using file input
    cy.get('input[type="file"]').selectFile({
      contents: Cypress.Buffer.from(fileContent),
      fileName: fileName,
      mimeType: 'application/pdf'
    }, { force: true });

    cy.wait('@uploadFile');

    // Verify upload in progress
    cy.contains('Uploading optimization-guide.pdf').should('be.visible');
    cy.get('[role="progressbar"]').should('be.visible');

    // Wait for processing to complete
    cy.wait('@getProcessingStatus');

    // Mock updated references list
    cy.intercept('GET', '/api/references', {
      statusCode: 200,
      body: [
        {
          id: 'ref-1',
          filename: fileName,
          content_type: 'application/pdf',
          size: fileContent.length,
          status: 'completed',
          created_at: new Date().toISOString(),
          metadata: {
            page_count: 10,
            word_count: 5000,
            embeddings_generated: true
          }
        }
      ]
    }).as('getUpdatedReferences');

    cy.wait('@getUpdatedReferences');

    // Verify file appears in references list
    cy.contains(fileName).should('be.visible');
    cy.contains('10 pages').should('be.visible');
    cy.contains('5000 words').should('be.visible');
  });

  it('should use uploaded references in chat', () => {
    // Mock existing references
    cy.intercept('GET', '/api/references', {
      statusCode: 200,
      body: [
        {
          id: 'ref-1',
          filename: 'architecture.md',
          content_type: 'text/markdown',
          size: 15000,
          status: 'completed',
          created_at: new Date().toISOString()
        },
        {
          id: 'ref-2',
          filename: 'performance-data.csv',
          content_type: 'text/csv',
          size: 25000,
          status: 'completed',
          created_at: new Date().toISOString()
        }
      ]
    }).as('getReferences');

    // Open references panel
    cy.get('button').contains('References').click({ timeout: 10000 });

    // Select references to use
    cy.get('input[type="checkbox"][value="ref-1"]').check();
    cy.get('input[type="checkbox"][value="ref-2"]').check();

    // Close references panel
    cy.get('button[aria-label="Close references"]').click();

    // Verify selected references indicator
    cy.contains('2 references selected').should('be.visible');

    // Send message with references
    const messageWithRefs = 'Analyze the architecture and performance data';
    cy.get('input[placeholder*="message"]', { timeout: 10000 }).type(messageWithRefs);
    
    // Mock message send with references
    cy.intercept('POST', '/api/messages', (req) => {
      expect(req.body.references).to.deep.equal(['ref-1', 'ref-2']);
      req.reply({
        statusCode: 201,
        body: {
          id: 'msg-1',
          content: messageWithRefs,
          type: 'user',
          references: ['ref-1', 'ref-2'],
          created_at: new Date().toISOString()
        }
      });
    }).as('sendMessageWithRefs');

    cy.get('button').contains('Send').click();
    cy.wait('@sendMessageWithRefs');

    // Verify message shows attached references
    cy.get('.bg-blue-50').should('contain', messageWithRefs);
    cy.get('.bg-blue-50').should('contain', 'References:');
    cy.get('.bg-blue-50').should('contain', 'architecture.md');
    cy.get('.bg-blue-50').should('contain', 'performance-data.csv');

    // Simulate agent response using references
    cy.window().then((win) => {
      const agentResponse: WebSocketMessage = {
        type: 'message',
        payload: {
          id: 'msg-2',
          created_at: new Date().toISOString(),
          content: 'Based on the architecture.md and performance-data.csv files, I can see that your system has the following characteristics...',
          type: 'agent',
          sub_agent_name: 'DataSubAgent',
          displayed_to_user: true,
          references_used: ['ref-1', 'ref-2']
        } as Message
      };
      // @ts-ignore
      win.ws.onmessage({ data: JSON.stringify(agentResponse) });
    });

    cy.contains('Based on the architecture.md and performance-data.csv').should('be.visible');
  });

  it('should handle multiple file uploads and batch processing', () => {
    // Open references panel
    cy.get('button').contains('References').click({ timeout: 10000 });

    // Create multiple test files
    const files = [
      { name: 'doc1.txt', content: 'Document 1 content', type: 'text/plain' },
      { name: 'doc2.pdf', content: 'Document 2 content', type: 'application/pdf' },
      { name: 'doc3.json', content: '{"key": "value"}', type: 'application/json' }
    ];

    // Mock batch upload endpoint
    cy.intercept('POST', '/api/references/batch-upload', {
      statusCode: 201,
      body: {
        uploads: files.map((file, index) => ({
          id: `ref-${index + 1}`,
          filename: file.name,
          content_type: file.type,
          size: file.content.length,
          status: 'processing',
          created_at: new Date().toISOString()
        }))
      }
    }).as('batchUpload');

    // Select multiple files
    const fileInputs = files.map(f => ({
      contents: Cypress.Buffer.from(f.content),
      fileName: f.name,
      mimeType: f.type
    }));

    cy.get('input[type="file"][multiple]').selectFile(fileInputs, { force: true });
    cy.wait('@batchUpload');

    // Verify batch upload progress
    cy.contains('Uploading 3 files').should('be.visible');
    
    // Mock batch status check
    cy.intercept('GET', '/api/references/batch-status', {
      statusCode: 200,
      body: {
        total: 3,
        completed: 3,
        failed: 0,
        processing: 0,
        files: files.map((file, index) => ({
          id: `ref-${index + 1}`,
          filename: file.name,
          status: 'completed'
        }))
      }
    }).as('batchStatus');

    cy.wait('@batchStatus');

    // Verify all files uploaded successfully
    cy.contains('All files uploaded successfully').should('be.visible');
    files.forEach(file => {
      cy.contains(file.name).should('be.visible');
    });
  });

  it('should delete references', () => {
    // Mock existing references
    cy.intercept('GET', '/api/references', {
      statusCode: 200,
      body: [
        {
          id: 'ref-1',
          filename: 'old-document.pdf',
          content_type: 'application/pdf',
          size: 10000,
          status: 'completed',
          created_at: new Date().toISOString()
        }
      ]
    }).as('getReferences');

    // Open references panel
    cy.get('button').contains('References').click({ timeout: 10000 });

    // Hover over reference to show delete button
    cy.contains('old-document.pdf').parent().trigger('mouseenter');
    
    // Click delete button
    cy.get('button[aria-label="Delete reference"]').click();

    // Confirm deletion
    cy.contains('Are you sure you want to delete this reference?').should('be.visible');
    
    // Mock delete endpoint
    cy.intercept('DELETE', '/api/references/ref-1', {
      statusCode: 204
    }).as('deleteReference');

    // Mock updated references list (empty)
    cy.intercept('GET', '/api/references', {
      statusCode: 200,
      body: []
    }).as('getEmptyReferences');

    // Confirm deletion
    cy.get('button').contains('Delete').click();
    cy.wait('@deleteReference');
    cy.wait('@getEmptyReferences');

    // Verify reference is removed
    cy.contains('old-document.pdf').should('not.exist');
    cy.contains('No references uploaded yet').should('be.visible');
  });

  it('should search and filter references', () => {
    // Mock references with various types
    cy.intercept('GET', '/api/references', {
      statusCode: 200,
      body: [
        {
          id: 'ref-1',
          filename: 'optimization-guide.pdf',
          content_type: 'application/pdf',
          size: 50000,
          status: 'completed',
          created_at: new Date().toISOString()
        },
        {
          id: 'ref-2',
          filename: 'performance-metrics.csv',
          content_type: 'text/csv',
          size: 25000,
          status: 'completed',
          created_at: new Date().toISOString()
        },
        {
          id: 'ref-3',
          filename: 'config.json',
          content_type: 'application/json',
          size: 5000,
          status: 'completed',
          created_at: new Date().toISOString()
        },
        {
          id: 'ref-4',
          filename: 'architecture.pdf',
          content_type: 'application/pdf',
          size: 75000,
          status: 'completed',
          created_at: new Date().toISOString()
        }
      ]
    }).as('getAllReferences');

    // Open references panel
    cy.get('button').contains('References').click({ timeout: 10000 });

    // Search for PDF files
    cy.get('input[placeholder="Search references..."]').type('pdf');
    
    // Verify filtered results
    cy.contains('optimization-guide.pdf').should('be.visible');
    cy.contains('architecture.pdf').should('be.visible');
    cy.contains('performance-metrics.csv').should('not.exist');
    cy.contains('config.json').should('not.exist');

    // Clear search and filter by type
    cy.get('input[placeholder="Search references..."]').clear();
    cy.get('select[aria-label="Filter by type"]').select('text/csv');

    // Verify type filter
    cy.contains('performance-metrics.csv').should('be.visible');
    cy.contains('optimization-guide.pdf').should('not.exist');
    cy.contains('config.json').should('not.exist');

    // Reset filters
    cy.get('button').contains('Clear filters').click();
    
    // All references should be visible
    cy.contains('optimization-guide.pdf').should('be.visible');
    cy.contains('performance-metrics.csv').should('be.visible');
    cy.contains('config.json').should('be.visible');
    cy.contains('architecture.pdf').should('be.visible');
  });

  it('should preview reference content', () => {
    // Mock reference with content
    cy.intercept('GET', '/api/references', {
      statusCode: 200,
      body: [
        {
          id: 'ref-1',
          filename: 'sample.txt',
          content_type: 'text/plain',
          size: 1000,
          status: 'completed',
          created_at: new Date().toISOString()
        }
      ]
    }).as('getReferences');

    // Mock content preview endpoint
    cy.intercept('GET', '/api/references/ref-1/preview', {
      statusCode: 200,
      body: {
        content: 'This is a sample text file content that can be previewed. It contains information about LLM optimization strategies.',
        preview_type: 'text',
        truncated: false
      }
    }).as('getPreview');

    // Open references panel
    cy.get('button').contains('References').click({ timeout: 10000 });

    // Click preview button
    cy.contains('sample.txt').parent().find('button[aria-label="Preview"]').click();
    cy.wait('@getPreview');

    // Verify preview modal
    cy.contains('Preview: sample.txt').should('be.visible');
    cy.contains('This is a sample text file content').should('be.visible');
    cy.contains('LLM optimization strategies').should('be.visible');

    // Close preview
    cy.get('button[aria-label="Close preview"]').click();
    cy.contains('Preview: sample.txt').should('not.exist');
  });

  it('should handle file upload errors gracefully', () => {
    // Open references panel
    cy.get('button').contains('References').click({ timeout: 10000 });

    // Mock upload failure
    cy.intercept('POST', '/api/references/upload', {
      statusCode: 413,
      body: {
        error: 'File too large',
        message: 'The uploaded file exceeds the maximum size limit of 10MB'
      }
    }).as('uploadError');

    // Try to upload large file
    const largeContent = 'x'.repeat(11 * 1024 * 1024); // 11MB
    cy.get('input[type="file"]').selectFile({
      contents: Cypress.Buffer.from(largeContent),
      fileName: 'large-file.pdf',
      mimeType: 'application/pdf'
    }, { force: true });

    cy.wait('@uploadError');

    // Verify error message
    cy.contains('File too large').should('be.visible');
    cy.contains('exceeds the maximum size limit').should('be.visible');

    // Error should be dismissible
    cy.get('button[aria-label="Dismiss error"]').click();
    cy.contains('File too large').should('not.exist');

    // Mock unsupported file type
    cy.intercept('POST', '/api/references/upload', {
      statusCode: 415,
      body: {
        error: 'Unsupported file type',
        message: 'Only PDF, TXT, CSV, JSON, and Markdown files are supported'
      }
    }).as('unsupportedType');

    // Try unsupported file
    cy.get('input[type="file"]').selectFile({
      contents: Cypress.Buffer.from('binary content'),
      fileName: 'file.exe',
      mimeType: 'application/x-msdownload'
    }, { force: true });

    cy.wait('@unsupportedType');

    // Verify error message
    cy.contains('Unsupported file type').should('be.visible');
    cy.contains('Only PDF, TXT, CSV, JSON, and Markdown files').should('be.visible');
  });

  it('should handle reference processing status updates', () => {
    // Open references panel
    cy.get('button').contains('References').click({ timeout: 10000 });

    // Mock initial upload
    cy.intercept('POST', '/api/references/upload', {
      statusCode: 201,
      body: {
        id: 'ref-processing',
        filename: 'complex-document.pdf',
        content_type: 'application/pdf',
        size: 5000000,
        status: 'processing',
        created_at: new Date().toISOString()
      }
    }).as('uploadFile');

    // Upload file
    cy.get('input[type="file"]').selectFile({
      contents: Cypress.Buffer.from('content'),
      fileName: 'complex-document.pdf',
      mimeType: 'application/pdf'
    }, { force: true });

    cy.wait('@uploadFile');

    // Mock processing stages
    const stages = [
      { status: 'extracting_text', progress: 25, message: 'Extracting text from document...' },
      { status: 'generating_embeddings', progress: 50, message: 'Generating embeddings...' },
      { status: 'indexing', progress: 75, message: 'Indexing content...' },
      { status: 'completed', progress: 100, message: 'Processing complete!' }
    ];

    // Simulate WebSocket updates for processing stages
    cy.window().then((win) => {
      stages.forEach((stage, index) => {
        setTimeout(() => {
          const statusUpdate: WebSocketMessage = {
            type: 'reference_status',
            payload: {
              reference_id: 'ref-processing',
              status: stage.status,
              progress: stage.progress,
              message: stage.message
            }
          };
          // @ts-ignore
          if (win.ws) {
            // @ts-ignore
            win.ws.onmessage({ data: JSON.stringify(statusUpdate) });
          }
        }, index * 1000);
      });
    });

    // Verify each processing stage
    cy.contains('Extracting text from document').should('be.visible');
    cy.contains('25%').should('be.visible');

    cy.contains('Generating embeddings').should('be.visible');
    cy.contains('50%').should('be.visible');

    cy.contains('Indexing content').should('be.visible');
    cy.contains('75%').should('be.visible');

    cy.contains('Processing complete!').should('be.visible');
    cy.contains('100%').should('be.visible');

    // Verify file is ready to use
    cy.contains('complex-document.pdf').parent().should('not.have.class', 'opacity-50');
    cy.get('input[type="checkbox"][value="ref-processing"]').should('not.be.disabled');
  });
});