const { TextEncoder, TextDecoder } = require('util');
const { TransformStream } = require('web-streams-polyfill');
const { BroadcastChannel } = require('broadcast-channel');

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
global.TransformStream = TransformStream;
global.BroadcastChannel = BroadcastChannel;
global.Response = require('cross-fetch').Response;
global.Request = require('cross-fetch').Request;
global.fetch = require('cross-fetch').fetch;