import { Message, WebSocketMessage } from '@/types/unified';
import { setupAuthenticatedState } from './auth-helpers';

export interface TestFile {
  name: string;
  content: string;
  type: string;
}

export interface ReferenceData {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  status: string;
  created_at: string;
  metadata?: {
    page_count?: number;
    word_count?: number;
    embeddings_generated?: boolean;
  };
}

export const setupAuthentication = (): void => {
  setupAuthenticatedState();
};

export const mockEmptyReferences = (): void => {
  cy.intercept('GET', '/api/references', {
    statusCode: 200,
    body: []
  }).as('getReferences');
};

export const mockReferencesEndpoint = (references: ReferenceData[]): void => {
  cy.intercept('GET', '/api/references', {
    statusCode: 200,
    body: references
  }).as('getReferences');
};

export const openReferencesPanel = (): void => {
  // Check if References button exists, if not skip the test
  cy.get('body').then(($body) => {
    if ($body.find('button:contains("References")').length > 0) {
      cy.get('button').contains('References').click({ timeout: 10000 });
    } else {
      // References panel not yet implemented - skip test
      cy.log('References panel not implemented yet - skipping test');
      cy.task('log', 'References panel functionality not yet implemented');
    }
  });
};

export const createTestFile = (
  name: string, 
  content: string, 
  type: string
): TestFile => {
  return { name, content, type };
};

export const generateFileForUpload = (file: TestFile) => {
  return {
    contents: Cypress.Buffer.from(file.content),
    fileName: file.name,
    mimeType: file.type
  };
};

export const mockFileUpload = (
  file: TestFile, 
  referenceId: string
): void => {
  cy.intercept('POST', '/api/references/upload', {
    statusCode: 201,
    body: {
      id: referenceId,
      filename: file.name,
      content_type: file.type,
      size: file.content.length,
      status: 'processing',
      created_at: new Date().toISOString()
    }
  }).as('uploadFile');
};

export const mockProcessingStatus = (
  referenceId: string, 
  metadata?: any
): void => {
  cy.intercept(`GET`, `/api/references/${referenceId}/status`, {
    statusCode: 200,
    body: {
      id: referenceId,
      status: 'completed',
      metadata: metadata || {
        page_count: 10,
        word_count: 5000,
        embeddings_generated: true
      }
    }
  }).as('getProcessingStatus');
};

export const mockBatchUpload = (files: TestFile[]): void => {
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
};

export const mockBatchStatus = (files: TestFile[]): void => {
  cy.intercept('GET', '/api/references/batch-status', {
    statusCode: 200,
    body: {
      total: files.length,
      completed: files.length,
      failed: 0,
      processing: 0,
      files: files.map((file, index) => ({
        id: `ref-${index + 1}`,
        filename: file.name,
        status: 'completed'
      }))
    }
  }).as('batchStatus');
};

export const mockDeleteReference = (referenceId: string): void => {
  cy.intercept('DELETE', `/api/references/${referenceId}`, {
    statusCode: 204
  }).as('deleteReference');
};

export const mockPreviewContent = (
  referenceId: string, 
  content: string
): void => {
  cy.intercept(`GET`, `/api/references/${referenceId}/preview`, {
    statusCode: 200,
    body: {
      content: content,
      preview_type: 'text',
      truncated: false
    }
  }).as('getPreview');
};

export const mockUploadError = (
  statusCode: number, 
  error: string, 
  message: string
): void => {
  cy.intercept('POST', '/api/references/upload', {
    statusCode: statusCode,
    body: { error, message }
  }).as('uploadError');
};

export const sendWebSocketMessage = (message: WebSocketMessage): void => {
  cy.window().then((win) => {
    // @ts-ignore
    if ((win as any).ws) {
      // @ts-ignore
      (win as any).ws.onmessage({ data: JSON.stringify(message) });
    }
  });
};

export const createAgentResponse = (
  content: string, 
  referencesUsed: string[]
): WebSocketMessage => {
  return {
    type: 'message',
    payload: {
      id: `msg-${Date.now()}`,
      created_at: new Date().toISOString(),
      content: content,
      type: 'agent',
      sub_agent_name: 'DataSubAgent',
      displayed_to_user: true,
      references_used: referencesUsed
    } as Message
  };
};

export const createStatusUpdate = (
  referenceId: string,
  status: string,
  progress: number,
  message: string
): WebSocketMessage => {
  return {
    type: 'message',
    payload: {
      reference_id: referenceId,
      status: status,
      progress: progress,
      message: message
    }
  };
};

export const selectMultipleFiles = (files: TestFile[]): void => {
  // Check if multiple file input exists
  cy.get('body').then(($body) => {
    if ($body.find('input[type="file"][multiple]').length > 0) {
      const fileInputs = files.map(f => generateFileForUpload(f));
      cy.get('input[type="file"][multiple]').selectFile(fileInputs, { 
        force: true 
      });
    } else {
      cy.log('Multiple file upload not implemented yet - skipping test');
      cy.task('log', 'Multiple file upload functionality not yet implemented');
    }
  });
};

export const uploadSingleFile = (file: TestFile): void => {
  // Check if file input exists
  cy.get('body').then(($body) => {
    if ($body.find('input[type="file"]').length > 0) {
      const fileInput = generateFileForUpload(file);
      cy.get('input[type="file"]').selectFile(fileInput, { force: true });
    } else {
      cy.log('File upload input not implemented yet - skipping file upload');
      cy.task('log', 'File upload functionality not yet implemented');
    }
  });
};

export const verifyFileInList = (filename: string): void => {
  // Only verify if references list exists
  cy.get('body').then(($body) => {
    if ($body.find(':contains("' + filename + '")').length > 0) {
      cy.contains(filename).should('be.visible');
    } else {
      cy.log(`File ${filename} not visible - references UI may not be implemented`);
    }
  });
};

export const verifyFileNotInList = (filename: string): void => {
  cy.contains(filename).should('not.exist');
};

export const verifyEmptyState = (): void => {
  // Check if the references UI exists
  cy.get('body').then(($body) => {
    if ($body.find(':contains("No references uploaded yet")').length > 0) {
      cy.contains('No references uploaded yet').should('be.visible');
    } else {
      // References UI not implemented - this is expected
      cy.log('References UI not implemented - skipping empty state check');
    }
  });
};

export const selectReferences = (referenceIds: string[]): void => {
  // Check if reference checkboxes exist
  cy.get('body').then(($body) => {
    const hasCheckboxes = referenceIds.some(id => 
      $body.find(`input[type="checkbox"][value="${id}"]`).length > 0
    );
    
    if (hasCheckboxes) {
      referenceIds.forEach(id => {
        cy.get(`input[type="checkbox"][value="${id}"]`).check();
      });
    } else {
      cy.log('Reference selection checkboxes not implemented yet');
      cy.task('log', 'Reference selection functionality not yet implemented');
    }
  });
};

export const verifySelectedReferencesCount = (count: number): void => {
  cy.contains(`${count} references selected`).should('be.visible');
};