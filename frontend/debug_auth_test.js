const { render } = require('@testing-library/react');
const React = require('react');

// Simple test to debug
console.log('Starting debug test...');

// Mock localStorage
global.localStorage = {
  getItem: jest.fn(() => null),
  removeItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn()
};

// Mock window
global.window = {
  location: { pathname: '/protected' }
};

console.log('localStorage mock setup complete');
console.log('localStorage.getItem:', global.localStorage.getItem());

