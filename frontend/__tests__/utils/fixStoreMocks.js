#!/usr/bin/env node

/**
 * Script to systematically fix store mock references in test files
 * This updates old direct mock function references to use store instances
 */

const fs = require('fs');
const path = require('path');

// Mapping of old mock references to new store instance references
const replacements = [
  // Thread store
  { old: 'mockSetThreads', new: 'mockThreadStore.setThreads' },
  { old: 'mockSetCurrentThread', new: 'mockThreadStore.setCurrentThread' },
  { old: 'mockAddThread', new: 'mockThreadStore.addThread' },
  { old: 'mockUpdateThread', new: 'mockThreadStore.updateThread' },
  { old: 'mockDeleteThread', new: 'mockThreadStore.deleteThread' },
  { old: 'mockSetLoading', new: 'mockThreadStore.setLoading' },
  { old: 'mockSetError', new: 'mockThreadStore.setError' },
  
  // Chat store
  { old: 'mockClearMessages', new: 'mockChatStore.clearMessages' },
  { old: 'mockLoadMessages', new: 'mockChatStore.loadMessages' },
  { old: 'mockAddMessage', new: 'mockChatStore.addMessage' },
  { old: 'mockSetProcessing', new: 'mockChatStore.setProcessing' },
  { old: 'mockSetSubAgentStatus', new: 'mockChatStore.setSubAgentStatus' },
  
  // Auth store
  { old: 'mockSetUser', new: 'mockAuthStore.setUser' },
  { old: 'mockLogin', new: 'mockAuthStore.login' },
  { old: 'mockLogout', new: 'mockAuthStore.logout' },
];

function fixFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  let modified = false;
  
  replacements.forEach(({ old, new: newRef }) => {
    // Match references in expect statements and function calls
    const regex = new RegExp(`\\b${old}\\b`, 'g');
    if (regex.test(content)) {
      content = content.replace(regex, newRef);
      modified = true;
    }
  });
  
  if (modified) {
    fs.writeFileSync(filePath, content, 'utf8');
    // test debug removed: console.log(`Fixed: ${path.basename(filePath)}`);
    return true;
  }
  
  return false;
}

// Files to fix
const testFiles = [
  'C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/frontend/__tests__/components/ChatHistorySection.test.tsx',
  'C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/frontend/__tests__/chat/chatUIUXComprehensive.test.tsx',
  'C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/frontend/__tests__/components/chat/MessageInput.test.tsx',
  'C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/frontend/__tests__/chat/chatUIUXCore.test.tsx',
];

// test debug removed: console.log('Fixing store mock references in test files...\n');

let fixedCount = 0;
testFiles.forEach(file => {
  if (fs.existsSync(file)) {
    if (fixFile(file)) {
      fixedCount++;
    }
  } else {
    // test debug removed: console.log(`File not found: ${path.basename(file)}`);
  }
});

// test debug removed: console.log(`\nFixed ${fixedCount} files.`);