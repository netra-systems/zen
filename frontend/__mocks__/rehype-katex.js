/**
 * Mock for rehype-katex
 * 
 * Provides a mock implementation of the KaTeX plugin for rehype
 */

// Mock plugin function that rehype-katex exports as default
const rehypeKatex = () => {
  return (tree) => {
    // Mock transformer function - in real plugin, this would render math with KaTeX
    // For testing, we just return the tree unchanged
    return tree;
  };
};

// Mock plugin metadata
rehypeKatex.pluginId = 'rehype-katex';

module.exports = rehypeKatex;
module.exports.default = rehypeKatex;