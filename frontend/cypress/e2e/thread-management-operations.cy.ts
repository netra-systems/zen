import {
  setupThreadTestEnvironment,
  openThreadSidebar,
  mockThreadSearch,
  mockThreadDeletion,
  mockThreadRename,
  mockThreadExport,
  mockThreadMessages,
  waitForThreadOperation,
  verifyThreadVisible,
  verifyThreadNotVisible,
  verifyMessageVisible,
  mockThreads
} from './thread-test-helpers';

/**
 * Thread Management Operations Tests
 * Tests for search, delete, rename, and export operations
 * Business Value: Growth segment - validates conversation management workflows
 */

describe('Thread Management Operations', () => {
  beforeEach(() => {
    setupThreadTestEnvironment();
  });

  it('should search and filter threads', () => {
    openThreadSidebar();
    performThreadSearch();
    verifySearchResults();
    clearSearchAndVerifyAll();
  });

  it('should delete a thread and update the list', () => {
    openThreadSidebar();
    initiateThreadDeletion();
    confirmDeletion();
    verifyThreadDeleted();
  });

  it('should rename a thread', () => {
    openThreadSidebar();
    initiateThreadRename();
    performRename();
    verifyThreadRenamed();
  });

  it('should export thread conversation', () => {
    loadThreadForExport();
    setupExportMock();
    performExport();
    verifyExportCompleted();
  });

  // Search operation helpers
  function performThreadSearch(): void {
    cy.get('input[placeholder="Search threads..."]').type('optimization');
    setupSearchMock();
    cy.get('button[aria-label="Search"]').click();
    waitForThreadOperation('searchThreads');
  }

  function setupSearchMock(): void {
    const filteredThreads = [mockThreads[0]]; // Only optimization thread
    mockThreadSearch('optimization', filteredThreads);
  }

  function verifySearchResults(): void {
    verifyThreadVisible('LLM Optimization Discussion');
    verifyThreadNotVisible('Cost Analysis Project');
    verifyThreadNotVisible('Performance Testing');
  }

  function clearSearchAndVerifyAll(): void {
    cy.get('input[placeholder="Search threads..."]').clear();
    cy.get('button[aria-label="Search"]').click();
    waitForThreadOperation('getThreads');
    verifyAllThreadsVisible();
  }

  function verifyAllThreadsVisible(): void {
    verifyThreadVisible('Cost Analysis Project');
    verifyThreadVisible('Performance Testing');
  }

  // Delete operation helpers
  function initiateThreadDeletion(): void {
    cy.contains('Performance Testing').parent().trigger('mouseenter');
    cy.get('button[aria-label="Delete thread"]').last().click();
    verifyDeleteConfirmation();
  }

  function verifyDeleteConfirmation(): void {
    cy.contains('Are you sure you want to delete this thread?').should('be.visible');
  }

  function confirmDeletion(): void {
    setupDeletionMocks();
    cy.get('button').contains('Delete').click();
    waitForThreadOperation('deleteThread');
    waitForThreadOperation('getUpdatedThreads');
  }

  function setupDeletionMocks(): void {
    mockThreadDeletion('thread-3');
    setupUpdatedThreadsList();
  }

  function setupUpdatedThreadsList(): void {
    const updatedThreads = mockThreads.slice(0, 2); // Remove third thread
    cy.intercept('GET', '/api/threads', {
      statusCode: 200,
      body: updatedThreads
    }).as('getUpdatedThreads');
  }

  function verifyThreadDeleted(): void {
    verifyThreadNotVisible('Performance Testing');
    verifyThreadVisible('LLM Optimization Discussion');
    verifyThreadVisible('Cost Analysis Project');
  }

  // Rename operation helpers
  function initiateThreadRename(): void {
    cy.contains('Cost Analysis Project').parent().trigger('mouseenter');
    cy.get('button[aria-label="Rename thread"]').first().click();
  }

  function performRename(): void {
    const newName = 'Updated Cost Analysis';
    cy.get('input[value="Cost Analysis Project"]').clear().type(newName);
    setupRenameMock(newName);
    cy.get('button[aria-label="Save thread name"]').click();
    waitForThreadOperation('renameThread');
  }

  function setupRenameMock(newName: string): void {
    const updatedThread = {
      ...mockThreads[1],
      title: newName,
      updated_at: new Date().toISOString()
    };
    mockThreadRename('thread-2', updatedThread);
  }

  function verifyThreadRenamed(): void {
    verifyThreadVisible('Updated Cost Analysis');
    verifyThreadNotVisible('Cost Analysis Project');
  }

  // Export operation helpers
  function loadThreadForExport(): void {
    openThreadSidebar();
    setupExportThreadMessages();
    cy.contains('LLM Optimization Discussion').click();
    waitForThreadOperation('getMessages');
  }

  function setupExportThreadMessages(): void {
    const exportMessages = [
      {
        id: 'msg-1',
        content: 'Test question',
        type: 'user' as const,
        created_at: new Date().toISOString()
      },
      {
        id: 'msg-2',
        content: 'Test response',
        type: 'agent' as const,
        created_at: new Date().toISOString()
      }
    ];
    mockThreadMessages('thread-1', exportMessages);
  }

  function setupExportMock(): void {
    const exportData = {
      thread: {
        id: 'thread-1',
        title: 'LLM Optimization Discussion'
      },
      messages: [
        { content: 'Test question', type: 'user' },
        { content: 'Test response', type: 'agent' }
      ]
    };
    mockThreadExport('thread-1', exportData);
  }

  function performExport(): void {
    cy.get('button[aria-label="Export conversation"]').click();
    cy.contains('Export as JSON').click();
    waitForThreadOperation('exportThread');
  }

  function verifyExportCompleted(): void {
    cy.get('@exportThread').should('have.been.called');
  }
});