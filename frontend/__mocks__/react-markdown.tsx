import React from 'react';

interface ReactMarkdownProps {
  children?: string;
  remarkPlugins?: any[];
  rehypePlugins?: any[];
  components?: any;
  className?: string;
  [key: string]: any;
}

const ReactMarkdown: React.FC<ReactMarkdownProps> = ({ children, className, ...props }) => {
  return (
    <div className={className} data-testid="react-markdown">
      {children}
    </div>
  );
};

export default ReactMarkdown;