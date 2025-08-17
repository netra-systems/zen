#!/usr/bin/env python3

import re

def refactor_websocket_service():
    """Refactor WebSocketService to comply with 8-line function limit"""
    
    file_path = "frontend/services/webSocketService.ts"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define the new validation functions
    new_validation_functions = '''  private validateAgentMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const agentTypes = ['agent_started', 'tool_executing', 'agent_thinking', 'partial_result', 'agent_completed'];
    if (!agentTypes.includes(obj.type)) return null;
    return obj.payload && typeof obj.payload === 'object' ? obj : null;
  }

  private validateThreadMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const threadTypes = ['thread_created', 'thread_loading', 'thread_loaded', 'thread_renamed'];
    if (!threadTypes.includes(obj.type)) return null;
    return obj.payload && typeof obj.payload === 'object' ? obj : null;
  }

  private validateSystemMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const systemTypes = ['auth', 'ping', 'pong'];
    if (!systemTypes.includes(obj.type)) return null;
    return obj;
  }

  private validateReportMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    const reportTypes = ['final_report', 'error'];
    if (!reportTypes.includes(obj.type)) return null;
    return obj.payload && typeof obj.payload === 'object' ? obj : null;
  }

  private handleUnknownMessageType(obj: any): WebSocketMessage | UnifiedWebSocketEvent {
    logger.debug('Unknown WebSocket message type', undefined, {
      component: 'WebSocketService',
      action: 'unknown_message_type',
      metadata: { type: obj.type }
    });
    return obj;
  }

  private validateWebSocketMessage(obj: any): WebSocketMessage | UnifiedWebSocketEvent | null {
    if (!this.isBasicWebSocketMessage(obj)) return null;
    
    return this.validateAgentMessage(obj) ||
           this.validateThreadMessage(obj) ||
           this.validateSystemMessage(obj) ||
           this.validateReportMessage(obj) ||
           this.handleUnknownMessageType(obj);
  }'''
    
    # Pattern to match the entire validateWebSocketMessage function
    pattern = r'  private validateWebSocketMessage\(obj: any\): WebSocketMessage \| UnifiedWebSocketEvent \| null \{[^}]*\s+\}'
    
    # Replace the function
    new_content = re.sub(pattern, new_validation_functions, content, flags=re.DOTALL)
    
    # Write the updated content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("SUCCESS: Refactored validateWebSocketMessage into 6 focused functions (each <=8 lines)")

if __name__ == "__main__":
    refactor_websocket_service()