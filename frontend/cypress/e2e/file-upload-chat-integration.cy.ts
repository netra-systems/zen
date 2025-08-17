import {
  setupAuthentication,
  mockReferencesEndpoint,
  openReferencesPanel,
  selectReferences,
  verifySelectedReferencesCount,
  createAgentResponse,
  sendWebSocketMessage,
  ReferenceData
} from '../support/file-upload-utilities';

describe('File Upload Chat Integration', () => {
  beforeEach(() => {
    setupAuthentication();
    setupMockReferences();
    cy.visit('/chat');
  });

  it('should use uploaded references in chat', () => {
    openReferencesPanel();
    selectReferences(['ref-1', 'ref-2']);
    closeReferencesPanel();

    verifySelectedReferencesCount(2);
    sendMessageWithReferences();
    verifyMessageWithReferences();
    simulateAgentResponse();
    verifyAgentUsedReferences();
  });

  it('should send message with single reference', () => {
    openReferencesPanel();
    selectReferences(['ref-1']);
    closeReferencesPanel();

    verifySelectedReferencesCount(1);

    const message = 'Analyze the architecture document';
    sendChatMessage(message);

    mockMessageEndpoint(['ref-1'], message);
    clickSendButton();
    cy.wait('@sendMessageWithRefs');

    verifyMessageDisplay(message, ['architecture.md']);
  });

  it('should clear reference selection', () => {
    openReferencesPanel();
    selectReferences(['ref-1', 'ref-2']);
    
    clearAllReferences();
    cy.contains('0 references selected').should('be.visible');
    
    closeReferencesPanel();
    verifyNoReferencesSelected();
  });

  it('should handle reference attachment in message', () => {
    openReferencesPanel();
    selectReferences(['ref-2']);
    closeReferencesPanel();

    const messageContent = 'What insights can you find in the data?';
    sendChatMessage(messageContent);

    mockMessageEndpoint(['ref-2'], messageContent);
    clickSendButton();
    cy.wait('@sendMessageWithRefs');

    verifyAttachedReferences(['performance-data.csv']);
    simulateDataAnalysisResponse();
  });

  it('should maintain reference selection across sessions', () => {
    openReferencesPanel();
    selectReferences(['ref-1']);
    closeReferencesPanel();

    cy.reload();
    setupAuthentication();

    verifySelectedReferencesCount(1);
    cy.get('input[type="checkbox"][value="ref-1"]').should('be.checked');
  });

  it('should show reference metadata in chat', () => {
    openReferencesPanel();
    selectReferences(['ref-1']);
    closeReferencesPanel();

    const message = 'Summarize the key points';
    sendChatMessage(message);

    mockMessageEndpoint(['ref-1'], message);
    clickSendButton();
    cy.wait('@sendMessageWithRefs');

    verifyReferenceMetadata();
  });
});

const setupMockReferences = (): void => {
  const references: ReferenceData[] = [
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
  ];
  
  mockReferencesEndpoint(references);
};

const closeReferencesPanel = (): void => {
  cy.get('button[aria-label="Close references"]').click();
};

const sendMessageWithReferences = (): void => {
  const message = 'Analyze the architecture and performance data';
  sendChatMessage(message);
  mockMessageEndpoint(['ref-1', 'ref-2'], message);
  clickSendButton();
  cy.wait('@sendMessageWithRefs');
};

const sendChatMessage = (message: string): void => {
  cy.get('input[placeholder*="message"]', { timeout: 10000 }).type(message);
};

const clickSendButton = (): void => {
  cy.get('button').contains('Send').click();
};

const mockMessageEndpoint = (
  references: string[], 
  content: string
): void => {
  cy.intercept('POST', '/api/messages', (req) => {
    expect(req.body.references).to.deep.equal(references);
    req.reply({
      statusCode: 201,
      body: {
        id: 'msg-1',
        content: content,
        type: 'user',
        references: references,
        created_at: new Date().toISOString()
      }
    });
  }).as('sendMessageWithRefs');
};

const verifyMessageWithReferences = (): void => {
  const message = 'Analyze the architecture and performance data';
  verifyMessageDisplay(message, ['architecture.md', 'performance-data.csv']);
};

const verifyMessageDisplay = (
  message: string, 
  referenceFilenames: string[]
): void => {
  cy.get('.bg-blue-50').should('contain', message);
  cy.get('.bg-blue-50').should('contain', 'References:');
  
  referenceFilenames.forEach(filename => {
    cy.get('.bg-blue-50').should('contain', filename);
  });
};

const simulateAgentResponse = (): void => {
  const response = createAgentResponse(
    'Based on the architecture.md and performance-data.csv files, I can see that your system has the following characteristics...',
    ['ref-1', 'ref-2']
  );
  
  sendWebSocketMessage(response);
};

const verifyAgentUsedReferences = (): void => {
  cy.contains(
    'Based on the architecture.md and performance-data.csv'
  ).should('be.visible');
};

const clearAllReferences = (): void => {
  cy.get('button').contains('Clear all').click();
};

const verifyNoReferencesSelected = (): void => {
  cy.contains('No references selected').should('be.visible');
};

const verifyAttachedReferences = (filenames: string[]): void => {
  filenames.forEach(filename => {
    cy.get('.bg-blue-50').should('contain', filename);
  });
};

const simulateDataAnalysisResponse = (): void => {
  const response = createAgentResponse(
    'Analyzing the performance data reveals several optimization opportunities...',
    ['ref-2']
  );
  
  sendWebSocketMessage(response);
  
  cy.contains(
    'Analyzing the performance data reveals'
  ).should('be.visible');
};

const verifyReferenceMetadata = (): void => {
  cy.get('.bg-blue-50').should('contain', 'architecture.md');
  cy.get('.bg-blue-50').should('contain', '15 KB');
};