const { TextEncoder, TextDecoder } = require('util');
const { TransformStream, ReadableStream } = require('web-streams-polyfill');

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
global.TransformStream = TransformStream;
global.ReadableStream = ReadableStream;
global.Response = require('cross-fetch').Response;
global.Request = require('cross-fetch').Request;
global.fetch = require('cross-fetch').fetch;

// Mock BroadcastChannel
global.BroadcastChannel = function() {
  return {
    postMessage: function() {},
    close: function() {},
    onmessage: null,
    onmessageerror: null,
    addEventListener: function() {},
    removeEventListener: function() {},
    dispatchEvent: function() {},
  };
};